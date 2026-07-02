import json
import unittest
from pathlib import Path

from bridge.app.sites.douban.site import DoubanSite


ROOT = Path(__file__).resolve().parents[1]


def _manifest(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _scripts_for(manifest, script_name):
    return [
        entry
        for entry in manifest.get("content_scripts", [])
        if entry.get("js") == [script_name]
    ]


class DoubanSiteContractTest(unittest.TestCase):
    def test_douban_capabilities_include_interest_action(self):
        capabilities = DoubanSite().capabilities()

        self.assertEqual(capabilities["site"], "douban")
        self.assertTrue(
            {"read_post", "read_profile_metrics", "search", "account_status"}.issubset(
                set(capabilities["read"])
            )
        )
        self.assertTrue(
            {"read_post", "read_profile_metrics", "search", "account_status", "set_interest"}.issubset(
                set(capabilities["workflow"])
            )
        )
        self.assertIn("set_interest", capabilities["action"])

    def test_douban_has_dedicated_adapter_and_not_media_adapter(self):
        adapter_source = (ROOT / "extension" / "adapters" / "douban-adapter.js").read_text(encoding="utf-8")
        self.assertIn("viewerInterest undetected", adapter_source)
        self.assertIn("!before.detected", adapter_source)
        self.assertIn("/doubanapp/dispatch", adapter_source)
        self.assertIn("comments?limit=", adapter_source)
        self.assertIn("commentsFetchAttempted", adapter_source)
        self.assertIn("el.closest('#interest_sect_level')", adapter_source)
        self.assertIn("if (controls[interest]) continue", adapter_source)
        self.assertIn("form.a_interest_form", adapter_source)
        self.assertIn('input[type="submit"][name="save"]', adapter_source)
        self.assertIn("before.value === interest", adapter_source)
        self.assertIn("changed: false", adapter_source)
        self.assertIn("const updated = after.value === interest", adapter_source)
        self.assertIn("ok: updated", adapter_source)
        self.assertIn("changed: before.value !== after.value", adapter_source)
        self.assertIn("interest state not updated", adapter_source)

        media_source = (ROOT / "extension" / "adapters" / "media-adapters.js").read_text(encoding="utf-8")
        self.assertNotIn("douban:", media_source)
        self.assertNotIn("site === 'douban'", media_source)

    def test_dev_and_prod_manifests_route_douban_to_dedicated_adapter(self):
        for manifest_name in ["manifest.dev.json", "manifest.prod.json"]:
            with self.subTest(manifest=manifest_name):
                manifest = _manifest(ROOT / "extension" / manifest_name)
                douban_scripts = _scripts_for(manifest, "adapters/douban-adapter.js")
                self.assertEqual(len(douban_scripts), 1)
                joined_douban_matches = "\n".join(douban_scripts[0].get("matches", []))
                self.assertIn("douban.com", joined_douban_matches)

                media_matches = []
                for entry in _scripts_for(manifest, "adapters/media-adapters.js"):
                    media_matches.extend(entry.get("matches", []))
                self.assertNotIn("douban.com", "\n".join(media_matches))


if __name__ == "__main__":
    unittest.main()
