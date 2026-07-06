import subprocess
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import subprocess
import unittest
import tempfile
import shutil
import glob
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def find_node():
    # 1. Search PATH
    node_bin = shutil.which("node")
    if node_bin:
        return node_bin

    # 2. Search NVM in home directory
    nvm_dir = os.path.expanduser("~/.nvm/versions/node")
    if os.path.exists(nvm_dir):
        node_paths = glob.glob(os.path.join(nvm_dir, "v*", "bin", "node"))
        if node_paths:
            def get_version_tuple(p):
                parts = Path(p).parents[1].name.lstrip('v').split('.')
                try:
                    return tuple(map(int, parts))
                except ValueError:
                    return (0, 0, 0)
            node_paths.sort(key=get_version_tuple, reverse=True)
            return node_paths[0]

    return None

class XAdapterLongArticleContractTest(unittest.TestCase):
    def setUp(self):
        self.node_bin = find_node()

    def test_javascript_syntax_and_long_article_helpers_presence(self):
        if not self.node_bin:
            self.skipTest("Node.js not found in PATH or ~/.nvm/versions/node")
        js_path = ROOT / "extension/adapters/x-adapter.js"
        self.assertTrue(js_path.exists())

        # Check syntax using node
        res = subprocess.run([self.node_bin, "--check", str(js_path)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"JS Syntax check failed: {res.stderr}")

    def test_javascript_adapter_logic_via_node(self):
        if not self.node_bin:
            self.skipTest("Node.js not found in PATH or ~/.nvm/versions/node")
        js_path = ROOT / "extension/adapters/x-adapter.js"
        # Write temporary test runner script
        js_runner_code = f"""
        const fs = require('fs');
        const path = require('path');
        const assert = require('assert');

        const code = fs.readFileSync({repr(str(js_path))}, 'utf8');

        class MockNode {{
          constructor(nodeType, nodeName, nodeValue = '') {{
            this.nodeType = nodeType;
            this.nodeName = nodeName;
            this.nodeValue = nodeValue;
            this.childNodes = [];
            this.attributes = {{}};
          }}
          getAttribute(name) {{ return this.attributes[name] || null; }}
          setAttribute(name, val) {{ this.attributes[name] = val; }}
          walk(fn) {{
            if (fn(this)) return true;
            for (const child of this.childNodes) {{
              if (child.walk(fn)) return true;
            }}
            return false;
          }}
        }}

        class MockElement extends MockNode {{
          constructor(tagName) {{
            super(1, tagName.toUpperCase());
            this.innerTextVal = '';
          }}
          get tagName() {{ return this.nodeName; }}
          get innerText() {{
            if (this.innerTextVal) return this.innerTextVal;
            const texts = [];
            const walk = (n) => {{
              if (n.nodeType === 3) texts.push(n.nodeValue);
              for (const c of n.childNodes) walk(c);
            }};
            walk(this);
            return texts.join(' ');
          }}
          set innerText(val) {{
            this.innerTextVal = val;
          }}
          querySelector(selector) {{
            if (selector === '[data-testid="twitter-article-title"]') {{
              return this.find((n) => n.getAttribute && n.getAttribute('data-testid') === 'twitter-article-title');
            }}
            if (selector === '[data-testid="twitterArticleRichTextView"]') {{
              return this.find((n) => n.getAttribute && n.getAttribute('data-testid') === 'twitterArticleRichTextView');
            }}
            return null;
          }}
          querySelectorAll(selector) {{
            const results = [];
            this.walk((n) => {{
              if (selector === 'img' && n.nodeName === 'IMG') {{
                results.push(n);
              }}
              if (selector === 'span' && n.nodeName === 'SPAN') {{
                results.push(n);
              }}
            }});
            return results;
          }}
          contains(node) {{
            let p = node;
            while (p) {{
              if (p === this) return true;
              p = p.parentNode;
            }}
            return false;
          }}
          appendChild(node) {{
            node.parentNode = this;
            this.childNodes.push(node);
            return node;
          }}
          find(predicate) {{
            let found = null;
            this.walk((n) => {{
              if (predicate(n)) {{
                found = n;
                return true;
              }}
            }});
            return found;
          }}
        }}

        const mockDocument = {{
          querySelectorAll: () => [],
          querySelector: () => null
        }};
        const mockWindow = {{}};
        const mockChrome = {{ runtime: {{ sendMessage: () => {{}} }} }};

        const contextFn = new Function('window', 'document', 'chrome', 'Node', code + `
          return {{
            extractLongArticleTitle,
            extractLongArticleCover,
            extractTweetItem
          }};
        `);

        const NodeTypes = {{
          ELEMENT_NODE: 1,
          TEXT_NODE: 3
        }};

        const adapterExports = contextFn(mockWindow, mockDocument, mockChrome, NodeTypes);

        // Test 1: extractLongArticleTitle with title element
        {{
          const article = new MockElement('article');
          const titleEl = new MockElement('h1');
          titleEl.setAttribute('data-testid', 'twitter-article-title');
          titleEl.innerText = 'Test Title';
          article.appendChild(titleEl);

          const title = adapterExports.extractLongArticleTitle(article);
          assert.strictEqual(title, 'Test Title');
        }}

        // Test 2: extractLongArticleTitle returns null when title element is missing
        {{
          const article = new MockElement('article');
          const span = new MockElement('span');
          span.appendChild(new MockNode(3, '#text', 'This is a paragraph that used to be a fallback title'));
          article.appendChild(span);

          const title = adapterExports.extractLongArticleTitle(article);
          assert.strictEqual(title, null);
        }}

        // Test 3: extractLongArticleCover
        {{
          const article = new MockElement('article');
          const bodyContainer = new MockElement('div');
          bodyContainer.setAttribute('data-testid', 'twitterArticleRichTextView');
          article.appendChild(bodyContainer);

          const bodyImg = new MockElement('img');
          bodyImg.src = 'https://pbs.twimg.com/media/body.jpg';
          bodyContainer.appendChild(bodyImg);

          const coverImg = new MockElement('img');
          coverImg.src = 'https://pbs.twimg.com/media/cover.jpg';
          article.appendChild(coverImg);

          const cover = adapterExports.extractLongArticleCover(article);
          assert.strictEqual(cover, 'https://pbs.twimg.com/media/cover.jpg');
        }}

        // Test 4: extractTweetItem cover stripping (only first matching img tag stripped)
        {{
          const article = new MockElement('article');
          const titleEl = new MockElement('h1');
          titleEl.setAttribute('data-testid', 'twitter-article-title');
          titleEl.innerText = 'Test Title';
          article.appendChild(titleEl);

          const coverImg = new MockElement('img');
          coverImg.src = 'https://pbs.twimg.com/media/cover.jpg';
          article.appendChild(coverImg);

          const bodyContainer = new MockElement('div');
          bodyContainer.setAttribute('data-testid', 'twitterArticleRichTextView');
          article.appendChild(bodyContainer);

          const span1 = new MockElement('span');
          span1.appendChild(new MockNode(3, '#text', 'Body starts here'));
          bodyContainer.appendChild(span1);

          const bodyImgMatch = new MockElement('img');
          bodyImgMatch.src = 'https://pbs.twimg.com/media/cover.jpg';
          bodyContainer.appendChild(bodyImgMatch);

          const result = adapterExports.extractTweetItem(article, {{ isLongArticle: true }});
          assert.strictEqual(result.title, 'Test Title');

          // The first image (cover) is stripped, but the second one in body text remains
          assert.ok(result.text.includes('[Image: https://pbs.twimg.com/media/cover.jpg]'));
        }}

        console.log('All JS long article logic tests passed successfully!');
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.cjs', delete=False) as f:
            f.write(js_runner_code)
            temp_path = f.name

        try:
            res = subprocess.run([self.node_bin, temp_path], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"JS Logic check failed: {res.stderr}\\nStdout: {res.stdout}")
        finally:
            Path(temp_path).unlink()

if __name__ == "__main__":
    unittest.main()
