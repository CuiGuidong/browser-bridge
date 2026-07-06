import contextlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def load_skill_module(skill_name):
    script_dir = ROOT / f"skills/{skill_name}-assistant/scripts"
    script_path = script_dir / "read_post.py"
    sys.path.insert(0, str(script_dir))
    try:
        spec = importlib.util.spec_from_file_location(f"{skill_name}_read_post", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        try:
            sys.path.remove(str(script_dir))
        except ValueError:
            pass

class SocialReadPostImageOutputContractTest(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "data": {
                "semantic": {
                    "ok": True,
                    "schemaVersion": "read_post.v1",
                    "contentItem": {
                        "text": "main content",
                        "media": [{"type": "image", "url": "https://example.test/main.jpg"}]
                    },
                    "thread": {
                        "items": [
                            {
                                "text": "thread reply",
                                "media": [{"type": "image", "url": "https://example.test/thread.jpg"}]
                            }
                        ]
                    },
                    "comments": {
                        "items": [
                            {
                                "text": "comment reply",
                                "media": [{"type": "image", "url": "https://example.test/comment.jpg"}]
                            }
                        ]
                    }
                },
                "summary": {"source": "test"},
                "diagnostics": {"adapterVersion": "test-v1"},
                "page": {"url": "https://example.test/post"}
            }
        }

    def test_weibo_read_post_modes(self):
        module = load_skill_module("weibo")

        # Test Default mode
        out = io.StringIO()
        with patch.object(module, "workflow_run", return_value=self.payload), contextlib.redirect_stdout(out):
            module.read_post("https://weibo.com/123/abc")
        res = json.loads(out.getvalue())
        self.assertTrue(res["ok"])
        self.assertNotIn("media", res["contentItem"])
        self.assertNotIn("media", res["thread"]["items"][0])
        self.assertNotIn("media", res["comments"]["items"][0])

        # Test Debug mode
        out = io.StringIO()
        with patch.object(module, "workflow_run", return_value=self.payload), contextlib.redirect_stdout(out):
            module.read_post("https://weibo.com/123/abc", mode="debug")
        res = json.loads(out.getvalue())
        self.assertTrue(res["ok"])
        self.assertEqual(res["contentItem"]["media"][0]["url"], "https://example.test/main.jpg")
        self.assertEqual(res["thread"]["items"][0]["media"][0]["url"], "https://example.test/thread.jpg")
        self.assertEqual(res["comments"]["items"][0]["media"][0]["url"], "https://example.test/comment.jpg")
        self.assertEqual(res["diagnostics"]["adapterVersion"], "test-v1")

    def test_xiaohongshu_read_post_modes(self):
        module = load_skill_module("xiaohongshu")

        # Test Default mode
        out = io.StringIO()
        with patch.object(module, "workflow_run", return_value=self.payload), contextlib.redirect_stdout(out):
            module.read_post("https://www.xiaohongshu.com/explore/abc")
        res = json.loads(out.getvalue())
        self.assertTrue(res["ok"])
        self.assertNotIn("media", res["contentItem"])

        # Test Debug mode
        out = io.StringIO()
        with patch.object(module, "workflow_run", return_value=self.payload), contextlib.redirect_stdout(out):
            module.read_post("https://www.xiaohongshu.com/explore/abc", mode="debug")
        res = json.loads(out.getvalue())
        self.assertTrue(res["ok"])
        self.assertEqual(res["contentItem"]["media"][0]["url"], "https://example.test/main.jpg")

    def test_zhihu_read_post_modes(self):
        module = load_skill_module("zhihu")

        # Test Default mode
        out = io.StringIO()
        with patch.object(module, "workflow_run", return_value=self.payload), contextlib.redirect_stdout(out):
            module.read_post("https://zhihu.com/question/123")
        res = json.loads(out.getvalue())
        self.assertTrue(res["ok"])
        self.assertNotIn("media", res["contentItem"])

        # Test Debug mode
        out = io.StringIO()
        with patch.object(module, "workflow_run", return_value=self.payload), contextlib.redirect_stdout(out):
            module.read_post("https://zhihu.com/question/123", mode="debug")
        res = json.loads(out.getvalue())
        self.assertTrue(res["ok"])
        self.assertEqual(res["contentItem"]["media"][0]["url"], "https://example.test/main.jpg")

if __name__ == "__main__":
    sys.exit(unittest.main())
