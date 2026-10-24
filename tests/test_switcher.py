"""Test suite for Obsidian Citadel Switcher."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

pkg_dir = Path(__file__).parent.parent
if str(pkg_dir) not in sys.path:
    sys.path.insert(0, str(pkg_dir))


class TestConfigLoadSave(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test.toml"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_default_config(self):
        from switcher.config import load_config
        config = load_config()
        self.assertIn("Gaming", config.profiles)
        self.assertIn("Programming", config.profiles)
        self.assertTrue(len(config.services) > 0)

    def test_load_nonexistent_returns_defaults(self):
        from switcher.config import load_config
        config = load_config(path=Path("/nonexistent/path.toml"))
        self.assertIn("Gaming", config.profiles)

    def test_save_load_roundtrip(self):
        from switcher.config import load_config, save_config, ProfileConfig, TweakConfig
        original = load_config()
        original.profiles["TestProfile"] = ProfileConfig(
            name="TestProfile",
            description="Test profile",
            color="#ff0000",
            builtin=False,
            services={"docker.service": True},
            processes={},
            tweaks=TweakConfig(swappiness=50),
        )
        original.config_path = self.config_file
        save_config(original)
        self.assertTrue(self.config_file.exists())
        loaded = load_config(path=self.config_file)
        self.assertIn("TestProfile", loaded.profiles)
        self.assertEqual(loaded.profiles["TestProfile"].color, "#ff0000")


class TestBackendHardware(unittest.TestCase):

    @patch('switcher.backend.shutil.which')
    def test_detect_gpu_vendor_nvidia(self, mock_which):
        mock_which.return_value = "/usr/bin/nvidia-smi"
        import importlib
        import switcher.backend
        importlib.reload(switcher.backend)
        vendor = switcher.backend.detect_gpu_vendor()
        self.assertEqual(vendor, "nvidia")

    def test_get_swappiness_reads_proc(self):
        with patch('switcher.backend.Path') as mock_path:
            mock_file = MagicMock()
            mock_file.read_text.return_value = "30"
            mock_path.return_value = mock_file
            import switcher.backend
            swap = switcher.backend.get_swappiness()
            self.assertEqual(swap, 30)

    def test_get_swappiness_invalid_returns_default(self):
        with patch('switcher.backend.Path') as mock_path:
            mock_file = MagicMock()
            mock_file.read_text.side_effect = OSError
            mock_path.return_value = mock_file
            import switcher.backend
            swap = switcher.backend.get_swappiness()
            self.assertEqual(swap, 30)


class TestApplyScriptGeneration(unittest.TestCase):

    def test_build_script_basic_services(self):
        from switcher.backend import build_apply_script
        script = build_apply_script(
            services_to_start=["docker.service"],
            services_to_stop=[],
            services_to_freeze=[],
            processes_to_start=[],
            processes_to_kill=[],
            processes_to_freeze=[],
            swappiness=None,
            compositor_unredirect=None,
            gpu_performance=None,
            cpu_governor="performance",
            gpu_power_limit=None,
            thp_mode="madvise",
        )
        self.assertIn("docker.service", script)
        self.assertIn("systemctl start", script)

    def test_build_script_stops_services(self):
        from switcher.backend import build_apply_script
        script = build_apply_script(
            services_to_start=[],
            services_to_stop=["docker.service"],
            services_to_freeze=[],
            processes_to_start=[],
            processes_to_kill=[],
            processes_to_freeze=[],
            swappiness=None,
            compositor_unredirect=None,
            gpu_performance=None,
            cpu_governor="performance",
            gpu_power_limit=None,
            thp_mode="madvise",
        )
        self.assertIn("docker.service", script)
        self.assertIn("systemctl stop", script)

    def test_build_script_with_tweaks(self):
        from switcher.backend import build_apply_script
        from switcher.config import ProcessConfig
        script = build_apply_script(
            services_to_start=[],
            services_to_stop=[],
            services_to_freeze=[],
            processes_to_start=[ProcessConfig("test_proc", "Test", "", "test\\.py", "python3 test.py")],
            processes_to_kill=[],
            processes_to_freeze=[],
            swappiness=10,
            compositor_unredirect=None,
            gpu_performance=None,
            cpu_governor="performance",
            gpu_power_limit=None,
            thp_mode="always",
        )
        self.assertIn("vm.swappiness=10", script)
        self.assertIn("transparent_hugepage", script)
        self.assertIn("setsid bash -c 'python3 test.py'", script)
        # The "already running?" check uses the configured pattern, not the id
        self.assertIn("citadel_pids 'test\\.py'", script)

    def _script(self, **kw):
        from switcher.backend import build_apply_script
        args = dict(services_to_start=[], services_to_stop=[], services_to_freeze=[],
                    processes_to_start=[], processes_to_kill=[], processes_to_freeze=[])
        args.update(kw)
        return build_apply_script(**args)

    def test_corrective_script_skips_plugins(self):
        script = self._script(services_to_stop=["avahi-daemon.service"], swappiness=10, run_plugins=False)
        self.assertNotIn("CITADEL ORCHESTRATION STARTING", script)
        self.assertNotIn("sysctl", script)
        self.assertIn("citadel_stop_unit avahi-daemon.service", script)

    def test_stop_handles_socket_activation(self):
        script = self._script(services_to_stop=["docker.service"])
        self.assertIn("TriggeredBy", script)
        self.assertIn("systemctl mask --runtime", script)
        self.assertIn("systemctl unmask --runtime", script)  # start path lifts it

    def test_full_apply_has_no_destructive_commands(self):
        for stealth in (False, True):
            script = self._script(gpu_performance=True, stealth_mode=stealth, swappiness=10)
            for bad in ("drop_caches", "fstrim", "aa-enforce", "image prune", "apt-get clean",
                        "daemon-reload", "modprobe", "zfs snapshot", "zpool scrub", "remount,size",
                        "systemctl start tlp"):
                self.assertNotIn(bad, script, f"{bad!r} (stealth={stealth})")
            self.assertNotIn("set -e", script.splitlines())

    def test_usb_autosuspend_not_forced_outside_gaming(self):
        script = self._script(gpu_performance=False)
        self.assertFalse([l for l in script.splitlines() if "usb" in l and "echo auto" in l])

    def test_iptables_rules_do_not_stack(self):
        script = self._script(stealth_mode=True)
        for line in script.splitlines():
            if "iptables" in line and " -A " in line:
                self.assertIn(" -C ", line, line)
        leaving = self._script(stealth_mode=False)
        self.assertIn("while iptables -t nat -D OUTPUT", leaving)

    def test_compose_stacks_stop_before_docker(self):
        from switcher.config import DEFAULT_PROCESSES
        friday = next(p for p in DEFAULT_PROCESSES if p.id == "compose-friday-ai")
        script = self._script(services_to_stop=["docker.service"], processes_to_kill=[friday])
        self.assertLess(script.index("FRIDAY_AI/docker-compose.yml' stop"),
                        script.index("citadel_stop_unit docker.service"))

    def _run_with_fake_systemctl(self, script: str, fail_on: str):
        import subprocess
        tmp = Path(tempfile.mkdtemp())
        fake = tmp / "systemctl"
        fake.write_text(f'#!/bin/bash\n[ "$1" = "{fail_on}" ] && exit 1\nexit 0\n')
        fake.chmod(0o755)
        script_path = tmp / "apply.sh"
        script_path.write_text(script)
        env = dict(os.environ, PATH=f"{tmp}:{os.environ['PATH']}")
        return subprocess.run(["bash", str(script_path)], capture_output=True, text=True, env=env, timeout=30)

    def test_script_exit_code_reflects_failures(self):
        script = self._script(services_to_start=["fake.service"], run_plugins=False)
        ok = self._run_with_fake_systemctl(script, fail_on="never")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("RECONCILE_SUCCESS", ok.stdout)
        bad = self._run_with_fake_systemctl(script, fail_on="start")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("RECONCILE_FAILED", bad.stdout)
        self.assertIn("start fake.service", bad.stderr)


class TestProcessDetection(unittest.TestCase):

    def test_compose_stack_matched_against_container_names(self):
        import switcher.backend as backend
        with patch.object(backend, "get_running_containers", return_value={"poi-api-1", "friday-webui"}):
            self.assertTrue(backend.is_process_running("poi-api|poi-worker", "compose"))
            self.assertFalse(backend.is_process_running("app-plandex", "compose"))

    def test_finds_host_process_but_not_self(self):
        import subprocess
        import switcher.backend as backend
        marker = "citadel_test_marker_%d" % os.getpid()
        proc = subprocess.Popen(["bash", "-c", f"exec -a {marker} sleep 30"])
        try:
            import time
            time.sleep(0.2)
            self.assertIn(proc.pid, backend.find_process_pids(marker))
        finally:
            proc.kill()
            proc.wait()
        self.assertNotIn(os.getpid(), backend.find_process_pids("python"))

    def test_containerised_processes_ignored(self):
        import switcher.backend as backend
        with patch.object(backend, "_is_containerised", return_value=True):
            self.assertEqual(backend.find_process_pids("python"), [])

    def test_compose_kind_inferred_from_id(self):
        from switcher.config import load_config
        path = Path(tempfile.mkdtemp()) / "c.toml"
        path.write_text('[[process]]\nid = "compose-x"\ngrep = "x-web"\nstart_cmd = "true"\n'
                        '[[process]]\nid = "plain"\ngrep = "plain"\nstart_cmd = "true"\n')
        kinds = {p.id: p.kind for p in load_config(path).processes}
        self.assertEqual(kinds, {"compose-x": "compose", "plain": "process"})


class TestReconciler(unittest.TestCase):

    def _reconciler(self):
        from services.hub.reconciler import CitadelReconciler, DriftPlan
        from switcher.config import load_config
        rec = CitadelReconciler(load_config(Path("/nonexistent.toml")))
        rec.desired = rec.config.profiles["Gaming"]
        return rec, DriftPlan

    def test_gives_up_after_max_corrections(self):
        import asyncio
        rec, DriftPlan = self._reconciler()
        runs = []
        with patch.object(rec, "plan", return_value=DriftPlan(services_to_stop=["avahi-daemon.service"])), \
             patch("services.hub.reconciler.run_apply_script", side_effect=lambda s: runs.append(s) or (True, "")):
            for _ in range(6):
                asyncio.run(rec.reconcile())
        self.assertEqual(len(runs), rec.MAX_CORRECTIONS)
        self.assertIn("svc:avahi-daemon.service", rec._gave_up)
        # Drift passes never re-run the plugin stack
        self.assertTrue(all("CITADEL ORCHESTRATION STARTING" not in s for s in runs))

    def test_set_profile_runs_full_apply_and_resets_budget(self):
        import asyncio
        rec, DriftPlan = self._reconciler()
        rec._gave_up.add("svc:x")
        with patch.object(rec, "plan", return_value=DriftPlan()), \
             patch("services.hub.reconciler.run_apply_script", return_value=(False, "boom")) as run:
            ok, out = asyncio.run(rec.set_profile(rec.config.profiles["Programming"]))
        self.assertFalse(ok)
        self.assertEqual(out, "boom")
        self.assertEqual(rec._gave_up, set())
        self.assertIn("CITADEL ORCHESTRATION STARTING", run.call_args[0][0])


class TestHubProfileResolution(unittest.TestCase):

    def _controller(self):
        from services.hub.main import CitadelController
        with patch.dict(os.environ, {"CITADEL_CONFIG": "/nonexistent/citadel.toml"}):
            return CitadelController()

    def test_unknown_profile_without_overrides_fails(self):
        profile, notes = self._controller().resolve_profile("Nope", None)
        self.assertIsNone(profile)
        self.assertIn("Unknown profile", notes[0])

    def test_overrides_are_validated(self):
        from services.hub import citadel_pb2
        ctl = self._controller()
        ov = citadel_pb2.DesiredState(services={"docker.service": True, "evil; rm -rf /": True},
                                      cpu_governor="performance; reboot", thp_mode="never")
        profile, notes = ctl.resolve_profile("Gaming", ov)
        self.assertTrue(profile.services["docker.service"])
        self.assertNotIn("evil; rm -rf /", profile.services)
        self.assertEqual(profile.tweaks.cpu_governor, "performance")
        self.assertEqual(profile.tweaks.thp_mode, "never")
        self.assertEqual(len(notes), 2)
        # The shared default profile must not be mutated by overrides
        self.assertFalse(ctl.config.profiles["Gaming"].services["docker.service"])


class TestVectorTelemetry(unittest.TestCase):

    def test_vector_read_vitals_safe_when_missing_shm(self):
        from pkg.telemetry.vector import CitadelVector
        cv = CitadelVector(provider=False)
        data = cv.read_vitals()
        self.assertEqual(data["elapsed"], 0.0)
        self.assertEqual(data["cores"], 0)


if __name__ == '__main__':
    unittest.main()
