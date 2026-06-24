import contextlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


def load_x_read_post_module():
    root = Path(__file__).resolve().parents[1]
    script_dir = root / "skills/x-assistant/scripts"
    script_path = script_dir / "read_post.py"
    sys.path.insert(0, str(script_dir))
    try:
        spec = importlib.util.spec_from_file_location("x_read_post_skill", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        try:
            sys.path.remove(str(script_dir))
        except ValueError:
            pass


class XReadPostSkillContractTest(unittest.TestCase):
    def test_default_output_accepts_media_only_semantic_post(self):
        module = load_x_read_post_module()
        payload = {
            "data": {
                "semantic": {
                    "ok": True,
                    "schemaVersion": "read_post.v1",
                    "contentItem": {
                        "text": "",
                        "media": [
                            {
                                "type": "image",
                                "url": "https://example.test/image.jpg",
                            }
                        ],
                    },
                },
                "summary": {
                    "source": "test",
                },
            }
        }

        out = io.StringIO()
        with patch.object(module, "workflow_run", return_value=payload), contextlib.redirect_stdout(out):
            module.read_single_post("https://x.com/example/status/1")

        result = json.loads(out.getvalue())
        self.assertTrue(result["ok"])
        self.assertEqual(result["contentItem"]["text"], "")
        self.assertEqual(result["contentItem"]["media"][0]["type"], "image")


if __name__ == "__main__":
    unittest.main()
