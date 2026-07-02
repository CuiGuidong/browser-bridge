import unittest

from bridge.app.application.action_service import ActionService
from bridge.app.sites.douban.workflows.set_interest import _is_subject_url, run as run_set_interest


class DoubanActionServiceTest(unittest.TestCase):
    def test_douban_set_interest_is_state_changing_action(self):
        service = ActionService(browser_runtime=None, extension_runtime=None)

        self.assertTrue(service._is_state_changing("douban", "set_interest"))
        self.assertEqual(service._action_log_path.name, "state-actions.jsonl")

    def test_runtime_retry_check_accepts_structured_extension_errors(self):
        service = ActionService(browser_runtime=None, extension_runtime=None)

        self.assertFalse(
            service._should_retry_runtime(
                {"ok": False, "error": {"code": "invalid_target", "message": "target closed"}}
            )
        )

    def test_runtime_retry_check_retries_bfcache_channel_close(self):
        service = ActionService(browser_runtime=None, extension_runtime=None)

        self.assertTrue(
            service._should_retry_runtime(
                {
                    "ok": False,
                    "error": {
                        "code": "content_script_error",
                        "message": "The page keeping the extension port is moved into back/forward cache, so the message channel is closed.",
                    },
                }
            )
        )

    def test_douban_restore_hint_uses_previous_interest(self):
        service = ActionService(browser_runtime=None, extension_runtime=None)
        result = {
            "before": {
                "interest": "wish",
            },
        }

        hint = service._build_restore_hint(
            "douban",
            "set_interest",
            {"url": "https://movie.douban.com/subject/37523009/", "interest": "collect"},
            result,
        )

        self.assertEqual(
            hint,
            {
                "kind": "set_interest",
                "url": "https://movie.douban.com/subject/37523009/",
                "interest": "wish",
            },
        )

    def test_douban_restore_hint_requires_manual_restore_when_previous_interest_unknown(self):
        service = ActionService(browser_runtime=None, extension_runtime=None)

        hint = service._build_restore_hint(
            "douban",
            "set_interest",
            {"url": "https://movie.douban.com/subject/37523009/", "interest": "collect"},
            {"before": {"interest": None}},
        )

        self.assertEqual(
            hint,
            {
                "kind": "manual_restore",
                "url": "https://movie.douban.com/subject/37523009/",
                "reason": "previous interest state unknown",
            },
        )

    def test_douban_set_interest_rejects_non_subject_url_before_opening_page(self):
        class BrowserRuntime:
            def open_or_reuse_url(self, *args, **kwargs):
                raise AssertionError("non-subject URL should not be opened")

        result = run_set_interest(
            action_service=object(),
            browser_runtime=BrowserRuntime(),
            params={
                "url": "https://www.douban.com/search?q=test",
                "interest": "wish",
            },
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "subject url is required")

    def test_douban_set_interest_requires_real_movie_subject_url(self):
        self.assertTrue(_is_subject_url("https://movie.douban.com/subject/37523009/"))
        self.assertTrue(_is_subject_url("https://movie.douban.com/subject/37523009/?from=test"))
        self.assertFalse(_is_subject_url("https://movie.douban.com/subject/37523009/comments?status=F"))
        self.assertFalse(_is_subject_url("https://www.douban.com/search?q=movie.douban.com/subject/37523009/"))
        self.assertFalse(_is_subject_url("https://evil.example/?next=movie.douban.com/subject/37523009/"))


if __name__ == "__main__":
    unittest.main()
