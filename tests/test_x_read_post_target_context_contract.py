import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class XReadPostTargetContextContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "extension" / "adapters" / "x-adapter.js").read_text()

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


if __name__ == "__main__":
    unittest.main()
