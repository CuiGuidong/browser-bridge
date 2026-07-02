import unittest
from pathlib import Path

from bridge.app.native_session_manager import NativeSessionManager


ROOT = Path(__file__).resolve().parents[1]


class NativeHostResilienceTest(unittest.TestCase):
    def test_pull_from_stale_native_host_session_is_adopted(self):
        manager = NativeSessionManager()

        result = manager.pull_command("stale1234", timeout_seconds=0)

        self.assertIsNone(result)
        self.assertEqual(manager.session_count, 1)
        self.assertEqual(manager.get_active_session(), "stale1234")

    def test_windows_launcher_reregisters_when_session_is_missing(self):
        source = (ROOT / "scripts" / "windows" / "install-native-host.ps1").read_text(encoding="utf-8")

        self.assertIn("IsSessionNotFoundCommand", source)
        self.assertIn("session not found, re-registering", source)
        self.assertIn("RegisterSession(bridgeUrl, logPath)", source)

    def test_dev_reload_script_fails_when_extension_reload_fails(self):
        source = (ROOT / "scripts" / "dev_reload_extension.sh").read_text(encoding="utf-8")

        self.assertIn("extension reload failed", source)
        self.assertIn("extension.get(\"ok\") is False", source)
        self.assertIn("sys.exit(1)", source)


if __name__ == "__main__":
    unittest.main()
