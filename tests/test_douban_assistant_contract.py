import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def import_module_from(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def workflow_payload():
    return {
        "ok": True,
        "site": "douban",
        "workflow": "read_post",
        "page": {"url": "https://movie.douban.com/subject/37523009/", "title": "金特务"},
        "signals": {"ready": True},
        "diagnostics": {"adapterVersion": "test"},
        "content": {
            "subject": {"id": "37523009", "title": "金特务：本色回归"},
            "rating": {"score": None, "ratingCount": 0},
            "interestStats": {"wish": 1, "do": 2, "collect": 3},
            "viewerInterest": {"value": None, "label": None, "detected": False},
            "comments": [{"text": "短评", "metrics": {"likes": 1}}],
            "commentsTotal": 326,
            "commentsHasMore": True,
        },
    }


class DoubanAssistantContractTest(unittest.TestCase):
    def test_bridge_client_uses_only_process_env_skill_env_and_default(self):
        source = (ROOT / "skills" / "douban-assistant" / "scripts" / "bridge_client.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn(".env.local", source)
        self.assertNotIn(".env_local", source)
        self.assertNotIn("repo_root", source)
        self.assertNotIn("BRIDGE_HOST", source)
        self.assertNotIn("BRIDGE_PORT", source)

    def test_read_post_formatter_outputs_douban_subject_v1_by_default(self):
        module = import_module_from(
            ROOT / "skills" / "douban-assistant" / "scripts" / "read_post.py",
            "douban_read_post_contract",
        )

        result = module.format_subject_result(workflow_payload(), mode="default", comment_limit=20)

        self.assertTrue(result["ok"])
        self.assertEqual(result["site"], "douban")
        self.assertEqual(result["schemaVersion"], "douban.subject.v1")
        self.assertEqual(result["subject"]["id"], "37523009")
        self.assertEqual(result["comments"]["limit"], 20)
        self.assertEqual(result["comments"]["total"], 326)

    def test_read_post_formatter_raw_and_debug_modes(self):
        module = import_module_from(
            ROOT / "skills" / "douban-assistant" / "scripts" / "read_post.py",
            "douban_read_post_contract_modes",
        )
        payload = workflow_payload()

        self.assertIs(module.format_subject_result(payload, mode="raw", comment_limit=20), payload)
        debug = module.format_subject_result(payload, mode="debug", comment_limit=20)

        self.assertEqual(debug["schemaVersion"], "douban.subject.v1")
        self.assertEqual(debug["diagnostics"], {"adapterVersion": "test"})
        self.assertEqual(debug["page"]["url"], "https://movie.douban.com/subject/37523009/")
        self.assertEqual(debug["signals"], {"ready": True})


if __name__ == "__main__":
    unittest.main()
