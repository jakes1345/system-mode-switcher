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
        script = build_apply_script(
            services_to_start=[],
            services_to_stop=[],
            services_to_freeze=[],
            processes_to_start=[("test_proc", "python3 test.py")],
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
        self.assertIn("nohup python3 test.py", script)


class TestVectorTelemetry(unittest.TestCase):

    def test_vector_read_vitals_safe_when_missing_shm(self):
        from pkg.telemetry.vector import CitadelVector
        cv = CitadelVector(provider=False)
        data = cv.read_vitals()
        self.assertEqual(data["elapsed"], 0.0)
        self.assertEqual(data["cores"], 0)


if __name__ == '__main__':
    unittest.main()
