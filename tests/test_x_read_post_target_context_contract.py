import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class XReadPostTargetContextContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "extension" / "adapters" / "x-adapter.js").read_text()

    def test_adapter_declares_target_tweet_selection_helpers(self):
        expected_markers = [
            "getCurrentTargetStatusId",
            "getTweetCandidates",
            "selectTargetTweetArticle",
            "contextItems",
            "rawPayload",
            "targetStatusId",
        ]
        for marker in expected_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.source)

    def test_adapter_does_not_call_private_x_apis(self):
        private_api_markers = [
            "graphql",
            "/api/",
            "__NEXT_DATA__",
            "window.__INITIAL_STATE__",
        ]
        for marker in private_api_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.source)

    def test_read_post_returns_structured_content_and_compatibility_text(self):
        expected_markers = [
            "post:",
            "contextItems:",
            "primaryText:",
            "buildReadPostContent",
        ]
        for marker in expected_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.source)


if __name__ == "__main__":
    unittest.main()
