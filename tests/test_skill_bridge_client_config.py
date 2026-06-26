import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SKILL_CLIENTS = [
    ROOT / "skills" / "x-assistant" / "scripts" / "bridge_client.py",
    ROOT / "skills" / "weibo-assistant" / "scripts" / "bridge_client.py",
    ROOT / "skills" / "xiaohongshu-assistant" / "scripts" / "bridge_client.py",
    ROOT / "skills" / "zhihu-assistant" / "scripts" / "bridge_client.py",
]


def import_module_from(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillBridgeClientConfigTest(unittest.TestCase):
    def test_skill_clients_do_not_read_project_env_local(self):
        for path in SKILL_CLIENTS:
            with self.subTest(path=path):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn(".env.local", source)
                self.assertNotIn("repo_root", source)
                self.assertNotIn("BRIDGE_HOST", source)
                self.assertNotIn("BRIDGE_PORT", source)

    def test_bridge_url_resolution_ignores_repo_env_local(self):
        source_path = SKILL_CLIENTS[0]
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            script_dir = repo / "skills" / "x-assistant" / "scripts"
            script_dir.mkdir(parents=True)
            client_path = script_dir / "bridge_client.py"
            client_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
            (repo / ".env.local").write_text("BRIDGE_URL=http://remote.example:17777\n", encoding="utf-8")

            with patch.dict(os.environ, {"BRIDGE_URL": ""}, clear=False):
                os.environ.pop("BRIDGE_URL", None)
                module = import_module_from(client_path, "bridge_client_default")
            self.assertEqual(module.BRIDGE_URL, "http://127.0.0.1:17777")

            (script_dir / ".env").write_text("BRIDGE_URL=http://skill.example:17777\n", encoding="utf-8")
            with patch.dict(os.environ, {"BRIDGE_URL": ""}, clear=False):
                os.environ.pop("BRIDGE_URL", None)
                module = import_module_from(client_path, "bridge_client_local_env")
            self.assertEqual(module.BRIDGE_URL, "http://skill.example:17777")

            with patch.dict(os.environ, {"BRIDGE_URL": "http://process.example:17777"}, clear=False):
                module = import_module_from(client_path, "bridge_client_process_env")
            self.assertEqual(module.BRIDGE_URL, "http://process.example:17777")


if __name__ == "__main__":
    unittest.main()
