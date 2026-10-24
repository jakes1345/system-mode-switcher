"""
Citadel Reconciliation Engine — Borg/K8s Style System Controller.

A profile is applied once, in full (kernel/hardware tweaks + services), when it is
set. After that the loop only corrects service/process drift, and gives up on an
item after a few failed corrections instead of retrying it forever.
"""

import asyncio
from dataclasses import dataclass, field

from switcher.backend import (
    build_apply_script,
    is_process_frozen,
    is_process_running,
    is_service_active,
    is_service_frozen,
    is_service_installed,
    run_apply_script,
)
from switcher.config import ProcessConfig, ProfileConfig
from switcher.core.logger import logger


@dataclass
class DriftPlan:
    services_to_start: list[str] = field(default_factory=list)
    services_to_stop: list[str] = field(default_factory=list)
    services_to_freeze: list[str] = field(default_factory=list)
    processes_to_start: list[ProcessConfig] = field(default_factory=list)
    processes_to_kill: list[ProcessConfig] = field(default_factory=list)
    processes_to_freeze: list[ProcessConfig] = field(default_factory=list)

    def keys(self) -> set[str]:
        return (
            {f"svc:{s}" for s in self.services_to_start + self.services_to_stop + self.services_to_freeze}
            | {f"proc:{p.id}" for p in self.processes_to_start + self.processes_to_kill + self.processes_to_freeze}
        )

    def without(self, skip: set[str]) -> "DriftPlan":
        return DriftPlan(
            services_to_start=[s for s in self.services_to_start if f"svc:{s}" not in skip],
            services_to_stop=[s for s in self.services_to_stop if f"svc:{s}" not in skip],
            services_to_freeze=[s for s in self.services_to_freeze if f"svc:{s}" not in skip],
            processes_to_start=[p for p in self.processes_to_start if f"proc:{p.id}" not in skip],
            processes_to_kill=[p for p in self.processes_to_kill if f"proc:{p.id}" not in skip],
            processes_to_freeze=[p for p in self.processes_to_freeze if f"proc:{p.id}" not in skip],
        )

    def is_empty(self) -> bool:
        return not self.keys()


class CitadelReconciler:
    """The enterprise state-enforcer."""

    MAX_CORRECTIONS = 3   # per item, then give up until the profile is applied again
    INTERVAL_SECS = 10

    def __init__(self, config_repo):
        self.config = config_repo
        self.desired: ProfileConfig | None = None  # Idle until set_profile is called
        self._lock = asyncio.Lock()
        self._corrections: dict[str, int] = {}
        self._gave_up: set[str] = set()
        self._running = False

    @property
    def active_profile_name(self) -> str | None:
        return self.desired.name if self.desired else None

    def plan(self, profile: ProfileConfig) -> DriftPlan:
        """Compare desired vs actual state. Blocking (runs systemctl/docker)."""
        plan = DriftPlan()

        for svc_name, desired_state in profile.services.items():
            if not is_service_installed(svc_name):
                continue  # Skip services not installed on this host OS
            if isinstance(desired_state, bool):
                desired_state = "start" if desired_state else "stop"

            if desired_state == "start" and not is_service_active(svc_name):
                plan.services_to_start.append(svc_name)
            elif desired_state == "freeze" and not is_service_frozen(svc_name):
                plan.services_to_freeze.append(svc_name)
            elif desired_state == "stop" and is_service_active(svc_name):
                plan.services_to_stop.append(svc_name)

        for proc_id, desired_state in profile.processes.items():
            if isinstance(desired_state, bool):
                desired_state = "start" if desired_state else "stop"
            proc = next((p for p in self.config.processes if p.id == proc_id), None)
            if not proc:
                continue

            if desired_state == "start":
                if not is_process_running(proc.grep, proc.kind) or is_process_frozen(proc.id):
                    plan.processes_to_start.append(proc)
            elif desired_state == "freeze":
                if not is_process_frozen(proc.id):
                    plan.processes_to_freeze.append(proc)
            elif desired_state == "stop":
                if is_process_running(proc.grep, proc.kind):
                    plan.processes_to_kill.append(proc)

        return plan

    def _build_script(self, profile: ProfileConfig, plan: DriftPlan, full: bool) -> str:
        t = profile.tweaks
        stopped = set(plan.services_to_stop) | {s for s, on in profile.services.items() if on is False}
        return build_apply_script(
            services_to_start=plan.services_to_start,
            services_to_stop=plan.services_to_stop,
            services_to_freeze=plan.services_to_freeze,
            processes_to_start=plan.processes_to_start,
            processes_to_kill=plan.processes_to_kill,
            processes_to_freeze=plan.processes_to_freeze,
            swappiness=t.swappiness,
            compositor_unredirect=t.compositor_unredirect,
            gpu_performance=t.gpu_performance,
            cpu_governor=t.cpu_governor,
            gpu_power_limit=t.gpu_power_limit,
            thp_mode=t.thp_mode,
            stealth_mode=t.stealth_mode,
            gaming_audio=t.gaming_audio,
            cpu_shielding=t.cpu_shielding,
            wipe_ram=t.clear_ram_on_exit,
            dirty_ratio=t.dirty_ratio,
            dirty_background_ratio=t.dirty_background_ratio,
            run_plugins=full,
            services_to_unmask=[s.name for s in self.config.services if s.name not in stopped] if full else None,
        )

    async def set_profile(self, profile: ProfileConfig) -> tuple[bool, str]:
        """Apply a profile in full, once, and start enforcing it."""
        async with self._lock:
            self.desired = profile
            self._corrections.clear()
            self._gave_up.clear()

            plan = await asyncio.to_thread(self.plan, profile)
            script = self._build_script(profile, plan, full=True)
            logger.info("Reconciler", f"Applying profile '{profile.name}' ({len(plan.keys())} service/process changes)")
            ok, output = await asyncio.to_thread(run_apply_script, script)
            if ok:
                logger.info("Reconciler", f"Profile '{profile.name}' applied.")
            else:
                logger.error("Reconciler", f"Profile '{profile.name}' apply failed: {output}")
            return ok, output

    async def reconcile(self):
        """Perform a single drift-correction pass (services/processes only)."""
        if self._lock.locked():
            return  # a profile apply is in progress
        async with self._lock:
            profile = self.desired
            if not profile:
                return  # No profile set yet — wait for explicit SetProfile call

            plan = await asyncio.to_thread(self.plan, profile)
            drifting = plan.keys()

            # Items that converged get a fresh budget if they drift again later
            for key in list(self._corrections):
                if key not in drifting:
                    del self._corrections[key]

            for key in sorted(drifting - self._gave_up):
                self._corrections[key] = self._corrections.get(key, 0) + 1
                if self._corrections[key] > self.MAX_CORRECTIONS:
                    self._gave_up.add(key)
                    logger.error(
                        "Reconciler",
                        f"GIVING UP on {key}: still drifting after {self.MAX_CORRECTIONS} corrections. "
                        f"Re-apply the profile to retry.",
                    )

            plan = plan.without(self._gave_up)
            if plan.is_empty():
                return

            for key in sorted(plan.keys()):
                logger.warn("Reconciler", f"DRIFT: {key} (correction {self._corrections[key]}/{self.MAX_CORRECTIONS})")
            script = self._build_script(profile, plan, full=False)
            ok, output = await asyncio.to_thread(run_apply_script, script)
            if ok:
                logger.info("Reconciler", "Drift corrected.")
            else:
                logger.error("Reconciler", f"Drift correction failed: {output}")

    async def start(self):
        self._running = True
        logger.info("Reconciler", "State Reconciliation engine started.")
        while self._running:
            try:
                await self.reconcile()
            except Exception as e:
                logger.error("Reconciler", f"RECON_FAILED: {e}")

            await asyncio.sleep(self.INTERVAL_SECS)
