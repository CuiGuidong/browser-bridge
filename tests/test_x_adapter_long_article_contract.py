import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class XAdapterLongArticleContractTest(unittest.TestCase):
    def test_javascript_syntax_and_long_article_helpers_presence(self):
        js_path = ROOT / "extension/adapters/x-adapter.js"
        self.assertTrue(js_path.exists())
        
        # Check syntax using node
        res = subprocess.run(["node", "--check", str(js_path)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"JS Syntax check failed: {res.stderr}")

        # Check that functions are present in text
        content = js_path.read_text(encoding="utf-8")
        self.assertIn("extractLongArticleTitle", content)
        self.assertIn("extractLongArticleCover", content)
        self.assertIn("isLongArticle", content)
        self.assertIn("title", content)
        self.assertIn("cover", content)

if __name__ == "__main__":
    unittest.main()
