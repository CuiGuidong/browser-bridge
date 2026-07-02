import unittest
import json
from importlib import import_module
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReferenceSiteExpansionTest(unittest.TestCase):
    requested_reference_sites = [
        ("1688", "ali1688", "Ali1688Site", ["1688.com"]),
        ("36kr", "site36kr", "Site36krSite", ["36kr.com"]),
        ("tieba", "tieba", "TiebaSite", ["tieba.baidu.com"]),
        ("aibase", "aibase", "AibaseSite", ["aibase.com"]),
        ("bloomberg", "bloomberg", "BloombergSite", ["bloomberg.com"]),
        ("dianping", "dianping", "DianpingSite", ["dianping.com"]),
        ("douyin", "douyin", "DouyinSite", ["douyin.com"]),
        ("google", "google", "GoogleSite", ["google.com"]),
        ("gov.cn", "gov_cn", "GovCnSite", ["gov.cn"]),
        ("grok", "grok", "GrokSite", ["grok.com", "x.ai"]),
        ("hupu", "hupu", "HupuSite", ["hupu.com"]),
        ("imdb", "imdb", "ImdbSite", ["imdb.com"]),
        ("jd", "jd", "JdSite", ["jd.com"]),
        ("linux-do", "linux_do", "LinuxDoSite", ["linux.do"]),
        ("v2ex", "v2ex", "V2exSite", ["v2ex.com"]),
        ("smzdm", "smzdm", "SmzdmSite", ["smzdm.com"]),
        ("taobao", "taobao", "TaobaoSite", ["taobao.com"]),
        ("wikipedia", "wikipedia", "WikipediaSite", ["wikipedia.org"]),
        ("xianyu", "xianyu", "XianyuSite", ["goofish.com", "xianyu.taobao.com"]),
    ]

    def test_shared_read_only_site_helper_uses_project_neutral_name(self):
        sites_dir = ROOT / "bridge" / "app" / "sites"

        self.assertFalse((sites_dir / "opencli_inspired.py").exists())
        self.assertTrue((sites_dir / "read_only_site.py").exists())
        module = import_module("bridge.app.sites.read_only_site")
        self.assertTrue(hasattr(module, "ReadOnlySite"))

        for site_file in sites_dir.glob("*/site.py"):
            with self.subTest(site_file=site_file):
                self.assertNotIn("opencli_inspired", site_file.read_text())

    def test_selected_reference_sites_declare_read_only_capabilities(self):
        selected_sites = [
            ("youtube", "YoutubeSite"),
            ("weixin", "WeixinSite"),
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

    def test_selected_reference_sites_are_registered_in_server_registry(self):
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

    def test_selected_reference_sites_are_present_in_extension_adapter(self):
        adapter_source = (ROOT / "extension" / "adapters" / "media-adapters.js").read_text()

        for site in [
            "youtube",
            "weixin",
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
            "news.ycombinator.com",
            "instagram.com",
            "xueqiu.com",
            "eastmoney.com",
        ]
        joined_matches = "\n".join(media_matches)
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, joined_matches)

    def test_douban_uses_dedicated_extension_adapter(self):
        adapter_source = (ROOT / "extension" / "adapters" / "douban-adapter.js").read_text()
        manifest = json.loads((ROOT / "extension" / "manifest.dev.json").read_text())
        douban_matches = []
        media_matches = []
        for script in manifest["content_scripts"]:
            if script.get("js") == ["adapters/douban-adapter.js"]:
                douban_matches.extend(script.get("matches", []))
            if script.get("js") == ["adapters/media-adapters.js"]:
                media_matches.extend(script.get("matches", []))

        self.assertIn("doubanAdapter", adapter_source)
        self.assertIn("douban.com", "\n".join(douban_matches))
        self.assertNotIn("douban.com", "\n".join(media_matches))

    def test_requested_reference_sites_declare_safe_read_only_capabilities(self):
        for site_id, module_name, class_name, _hosts in self.requested_reference_sites:
            with self.subTest(site=site_id):
                module = import_module(f"bridge.app.sites.{module_name}.site")
                site_class = getattr(module, class_name)
                site_capabilities = site_class().capabilities()

                self.assertEqual(site_capabilities["site"], site_id)
                self.assertEqual(site_capabilities["action"], [])
                self.assertIn("read_post", site_capabilities["read"])
                self.assertIn("read_profile_metrics", site_capabilities["read"])
                self.assertIn("search", site_capabilities["workflow"])
                self.assertIn("account_status", site_capabilities["workflow"])

    def test_requested_reference_sites_are_registered_in_server_registry(self):
        from bridge.app.server import site_registry

        registered_sites = set(site_registry.list_sites())
        for site_id, _module_name, _class_name, _hosts in self.requested_reference_sites:
            with self.subTest(site=site_id):
                self.assertIn(site_id, registered_sites)

    def test_requested_reference_sites_are_present_in_extension_and_manifest(self):
        adapter_source = (ROOT / "extension" / "adapters" / "media-adapters.js").read_text()
        manifest = json.loads((ROOT / "extension" / "manifest.json").read_text())
        media_matches = []
        for script in manifest["content_scripts"]:
            if script.get("js") == ["adapters/media-adapters.js"]:
                media_matches.extend(script.get("matches", []))
        joined_matches = "\n".join(media_matches)

        for site_id, _module_name, _class_name, host_fragments in self.requested_reference_sites:
            with self.subTest(site=site_id):
                self.assertTrue(
                    f"{site_id}:" in adapter_source or f"'{site_id}':" in adapter_source,
                    f"{site_id} missing from media adapter config",
                )
                for fragment in host_fragments:
                    self.assertIn(fragment, joined_matches)

    def test_requested_reference_sites_keep_private_api_out_of_adapter(self):
        adapter_source = (ROOT / "extension" / "adapters" / "media-adapters.js").read_text()

        private_api_markers = [
            "/api/",
            "mtop.",
            "h5api.m.",
            "graphql",
            "__NEXT_DATA__",
            "window.__INITIAL_STATE__",
        ]
        for marker in private_api_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, adapter_source)

    def test_media_adapter_treats_visible_blocking_notice_as_readable_state(self):
        adapter_source = (ROOT / "extension" / "adapters" / "media-adapters.js").read_text()

        self.assertIn("blockingNotice", adapter_source)
        self.assertIn("次数过多", adapter_source)
        self.assertIn("needsHumanAttention", adapter_source)


if __name__ == "__main__":
    unittest.main()
