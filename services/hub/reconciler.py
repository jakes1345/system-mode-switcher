"""
Citadel Reconciliation Engine — Borg/K8s Style System Controller.
Continuously enforces the 'Desired State' to eliminate configuration drift.
"""

import time
import asyncio
from switcher.backend import is_service_active, is_service_frozen, is_process_frozen, get_swappiness, build_apply_script, run_apply_script, is_process_running
from switcher.core.logger import logger

class CitadelReconciler:
    """The enterprise state-enforcer."""

    def __init__(self, config_repo):
        self.config = config_repo
        self.active_profile_name = None  # Idle until SetProfile is called explicitly
        self._running = False

    async def reconcile(self):
        """Perform a single reconciliation pass."""
        profile = self.config.profiles.get(self.active_profile_name) if self.active_profile_name else None
        if not profile:
            return  # No profile set yet — wait for explicit SetProfile call

        drift_detected = False
        
        services_to_start = []
        services_to_stop = []
        services_to_freeze = []
        
        # 1. Reconcile Services
        for svc_name, desired_state in profile.services.items():
            if isinstance(desired_state, bool):
                desired_state = "start" if desired_state else "stop"
                
            if desired_state == "start":
                current_active = is_service_active(svc_name)
                if not current_active:
                    logger.warn("Reconciler", f"DRIFT: Service '{svc_name}' should be ON. Current: OFF")
                    drift_detected = True
                    services_to_start.append(svc_name)
            elif desired_state == "freeze":
                frozen = is_service_frozen(svc_name)
                if not frozen:
                    logger.warn("Reconciler", f"DRIFT: Service '{svc_name}' should be FROZEN. Current: THAWED")
                    drift_detected = True
                    services_to_freeze.append(svc_name)
            elif desired_state == "stop":
                current_active = is_service_active(svc_name)
                if current_active:
                    logger.warn("Reconciler", f"DRIFT: Service '{svc_name}' should be OFF. Current: ON")
                    drift_detected = True
                    services_to_stop.append(svc_name)
                    
        procs_to_start = []
        procs_to_stop = []
        procs_to_freeze = []
        
        for proc_id, desired_state in profile.processes.items():
            if isinstance(desired_state, bool):
                desired_state = "start" if desired_state else "stop"
                
            proc = next((p for p in self.config.processes if p.id == proc_id), None)
            if not proc: continue
            
            if desired_state == "start":
                current_active = is_process_running(proc.grep)
                if not current_active:
                    logger.warn("Reconciler", f"DRIFT: Process '{proc_id}' should be ON. Current: OFF")
                    drift_detected = True
                    procs_to_start.append((proc.id, proc.start_cmd))
                elif is_process_frozen(proc.id):
                    logger.warn("Reconciler", f"DRIFT: Process '{proc_id}' should be ON. Current: FROZEN")
                    drift_detected = True
                    procs_to_start.append((proc.id, proc.start_cmd))
            elif desired_state == "freeze":
                frozen = is_process_frozen(proc.id)
                if not frozen:
                    logger.warn("Reconciler", f"DRIFT: Process '{proc_id}' should be FROZEN. Current: THAWED")
                    drift_detected = True
                    procs_to_freeze.append((proc.id, proc.grep))
            elif desired_state == "stop":
                current_active = is_process_running(proc.grep)
                if current_active:
                    logger.warn("Reconciler", f"DRIFT: Process '{proc_id}' should be OFF. Current: ON")
                    drift_detected = True
                    procs_to_stop.append((proc.id, proc.grep))
        
        # 2. Reconcile Kernel Tunables
        current_swappiness = get_swappiness()
        if current_swappiness != profile.tweaks.swappiness:
            logger.warn("Reconciler", f"DRIFT: Swappiness is {current_swappiness}, desired {profile.tweaks.swappiness}")
            drift_detected = True

        if drift_detected:
            logger.info("Reconciler", "Executing corrective action to restore system integrity...")
            script = build_apply_script(
                services_to_start=services_to_start,
                services_to_stop=services_to_stop,
                services_to_freeze=services_to_freeze,
                processes_to_start=procs_to_start,
                processes_to_kill=procs_to_stop,
                processes_to_freeze=procs_to_freeze,
                swappiness=profile.tweaks.swappiness,
                compositor_unredirect=profile.tweaks.compositor_unredirect,
                gpu_performance=profile.tweaks.gpu_performance,
                cpu_governor=profile.tweaks.cpu_governor,
                gpu_power_limit=profile.tweaks.gpu_power_limit,
                thp_mode=profile.tweaks.thp_mode,
                stealth_mode=profile.tweaks.stealth_mode,
                gaming_audio=profile.tweaks.gaming_audio,
                cpu_shielding=profile.tweaks.cpu_shielding,
                wipe_ram=profile.tweaks.clear_ram_on_exit,
                dirty_ratio=profile.tweaks.dirty_ratio,
                dirty_background_ratio=profile.tweaks.dirty_background_ratio
            )
            
            # Note: run_apply_script blocks and requires pkexec if sudo_password is None.
            # In a real background daemon running as root, this would just be executed directly.
            # Since this is a python process, we run it in a thread so we don't block the async loop.
            def run_script():
                ok, output = run_apply_script(script)
                if not ok:
                    logger.error("Reconciler", f"Failed to restore state: {output}")
                else:
                    logger.info("Reconciler", "System state successfully reconciled.")
            
            await asyncio.to_thread(run_script)


    async def start(self):
        self._running = True
        logger.info("Reconciler", "State Reconciliation engine started.")
        while self._running:
            try:
                await self.reconcile()
            except Exception as e:
                logger.error("Reconciler", f"RECON_FAILED: {e}")
            
            await asyncio.sleep(10) # Run every 10 seconds for minimal overhead
