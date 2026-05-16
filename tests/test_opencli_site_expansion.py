import unittest
import json
from importlib import import_module
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OpenCliSiteExpansionTest(unittest.TestCase):
    def test_selected_opencli_sites_declare_read_only_capabilities(self):
        selected_sites = [
            ("youtube", "YoutubeSite"),
            ("weixin", "WeixinSite"),
            ("douban", "DoubanSite"),
            ("hackernews", "HackerNewsSite"),
            ("instagram", "InstagramSite"),
            ("xueqiu", "XueqiuSite"),
            ("eastmoney", "EastmoneySite"),
        ]

        for site, class_name in selected_sites:
            with self.subTest(site=site):
                module = import_module(f"bridge.app.sites.{site}.site")
                site_class = getattr(module, class_name)
                site_capabilities = site_class().capabilities()

                self.assertEqual(site_capabilities["site"], site)
                self.assertEqual(site_capabilities["action"], [])
                self.assertIn("account_status", site_capabilities["read"])
                self.assertIn("account_status", site_capabilities["workflow"])
                self.assertIn("search", site_capabilities["workflow"])

    def test_selected_opencli_sites_are_registered_in_server_registry(self):
        from bridge.app.server import site_registry

        selected_sites = {
            "youtube",
            "weixin",
            "douban",
            "hackernews",
            "instagram",
            "xueqiu",
            "eastmoney",
        }

        self.assertTrue(selected_sites.issubset(set(site_registry.list_sites())))

    def test_selected_opencli_sites_are_present_in_extension_adapter(self):
        adapter_source = (ROOT / "extension" / "adapters" / "media-adapters.js").read_text()

        for site in [
            "youtube",
            "weixin",
            "douban",
            "hackernews",
            "instagram",
            "xueqiu",
            "eastmoney",
        ]:
            with self.subTest(site=site):
                self.assertIn(f"{site}:", adapter_source)

    def test_hackernews_search_uses_page_dom_not_private_api(self):
        adapter_source = (ROOT / "extension" / "adapters" / "media-adapters.js").read_text()

        self.assertNotIn("hn.algolia.com/api/v1/search", adapter_source)
        self.assertIn("extractHackernewsSearchItems", adapter_source)
        self.assertIn(".Story", adapter_source)
        self.assertIn("source: 'page-dom'", adapter_source)

    def test_manifest_injects_media_adapter_for_selected_hosts(self):
        manifest = json.loads((ROOT / "extension" / "manifest.json").read_text())
        media_matches = []
        for script in manifest["content_scripts"]:
            if script.get("js") == ["adapters/media-adapters.js"]:
                media_matches.extend(script.get("matches", []))

        expected_fragments = [
            "youtube.com",
            "mp.weixin.qq.com",
            "douban.com",
            "news.ycombinator.com",
            "instagram.com",
            "xueqiu.com",
            "eastmoney.com",
        ]
        joined_matches = "\n".join(media_matches)
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, joined_matches)


if __name__ == "__main__":
    unittest.main()
