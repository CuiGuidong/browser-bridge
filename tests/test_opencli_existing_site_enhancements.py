import unittest
from importlib import import_module
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OpenCliExistingSiteEnhancementsTest(unittest.TestCase):
    def test_existing_sites_gain_selected_read_only_workflows(self):
        expectations = {
            "weibo": {
                "class": "WeiboSite",
                "read": {
                    "read_home",
                    "read_hot_feed",
                    "read_hot_search",
                    "read_post",
                    "search",
                    "account_status",
                    "read_profile_metrics",
                },
                "workflow": {
                    "read_home",
                    "read_hot_feed",
                    "read_hot_search",
                    "read_post",
                    "search",
                    "account_status",
                    "read_profile_metrics",
                },
                "action": set(),
            },
            "zhihu": {
                "class": "ZhihuSite",
                "read": {"read_post", "read_profile_metrics", "search", "account_status", "read_hot"},
                "workflow": {"read_post", "read_profile_metrics", "search", "account_status", "read_hot"},
                "action": set(),
            },
            "bilibili": {
                "class": "BilibiliSite",
                "read": {"read_post", "read_profile_metrics", "search", "account_status", "read_hot"},
                "workflow": {"read_post", "read_profile_metrics", "search", "account_status", "read_hot"},
                "action": set(),
            },
            "reddit": {
                "class": "RedditSite",
                "read": {"read_post", "read_profile_metrics", "search", "account_status", "read_hot"},
                "workflow": {"read_post", "read_profile_metrics", "search", "account_status", "read_hot"},
                "action": set(),
            },
            "x": {
                "class": "XSite",
                "read": {
                    "read_post",
                    "read_timeline",
                    "read_trending",
                    "list_bookmarks",
                    "account_status",
                    "read_profile_metrics",
                },
                "workflow": {
                    "read_post",
                    "search",
                    "list_bookmarks",
                    "read_home",
                    "follow_user",
                    "unfollow_user",
                    "add_bookmark",
                    "remove_bookmark",
                    "account_status",
                    "read_profile_metrics",
                    "read_trending",
                },
                "action": {
                    "expand_post",
                    "switch_feed",
                    "add_bookmark",
                    "remove_bookmark",
                    "follow_user",
                    "unfollow_user",
                },
            },
        }

        for site, expected in expectations.items():
            with self.subTest(site=site):
                module = import_module(f"bridge.app.sites.{site}.site")
                site_class = getattr(module, expected["class"])
                capabilities = site_class().capabilities()

                self.assertTrue(expected["read"].issubset(set(capabilities["read"])))
                self.assertTrue(expected["workflow"].issubset(set(capabilities["workflow"])))
                self.assertEqual(set(capabilities["action"]), expected["action"])

    def test_media_adapter_declares_hot_page_semantics(self):
        source = (ROOT / "extension" / "adapters" / "media-adapters.js").read_text()

        self.assertIn("'read_hot'", source)
        self.assertNotIn("api.bilibili.com/x/web-interface/popular", source)
        self.assertIn("extractBilibiliHotItems", source)
        self.assertIn(".bili-video-card", source)
        self.assertIn("source: 'page-dom'", source)
        self.assertIn("path.startsWith('/hot')", source)
        self.assertIn("path.startsWith('/v/popular')", source)
        self.assertIn("path === '/hot/'", source)
        self.assertIn("videoContentParsed: false", source)

    def test_media_adapter_does_not_call_private_site_apis(self):
        source = (ROOT / "extension" / "adapters" / "media-adapters.js").read_text()

        private_api_fragments = [
            "hn.algolia.com/api/v1/search",
            "api.bilibili.com/x/web-interface/popular",
        ]
        for fragment in private_api_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def test_x_adapter_declares_profile_metrics_read(self):
        source = (ROOT / "extension" / "adapters" / "x-adapter.js").read_text()

        self.assertIn("'read_profile_metrics'", source)
        self.assertIn("'read_trending'", source)
        self.assertIn("extractXProfileMetrics", source)
        self.assertIn("extractXTrendingItems", source)
        self.assertIn("data-testid=\"trend\"", source)

    def test_weibo_adapter_declares_profile_metrics_read(self):
        source = (ROOT / "extension" / "adapters" / "weibo-adapter.js").read_text()

        self.assertIn("'read_profile_metrics'", source)
        self.assertIn("extractProfileMetrics", source)


if __name__ == "__main__":
    unittest.main()
