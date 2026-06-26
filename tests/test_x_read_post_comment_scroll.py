import unittest

from bridge.app.sites.x.workflows.read_post import run


def make_comment(index):
    return {
        "authorName": f"user-{index}",
        "time": "now",
        "text": f"comment {index}",
        "media": [],
        "metrics": {
            "likes": index,
            "comments": 0,
            "replies": 0,
        },
        "platformMetrics": {},
    }


def make_read_result(comment_count):
    return {
        "ok": True,
        "source": "test",
        "mode": "semantic",
        "page": {
            "url": "https://x.com/example/status/12345",
            "title": "X test",
        },
        "signals": {
            "pageType": "post",
        },
        "content": {
            "post": {
                "statusId": "12345",
                "url": "https://x.com/example/status/12345",
                "author": {
                    "displayName": "Example",
                    "handle": "@example",
                },
                "publishedAt": "2026-06-01T00:00:00.000Z",
                "publishedLabel": "2026-06-01",
                "text": "long post",
                "media": [],
                "metrics": {
                    "comments": 42,
                    "likes": 10,
                },
            },
            "threadItems": [],
            "commentItems": [make_comment(i) for i in range(comment_count)],
            "filteredItems": [],
            "rawPayload": {
                "targetStatusId": "12345",
                "matchedStatusId": "12345",
                "matchStrategy": "article_permalink",
                "candidateCount": comment_count + 1,
                "commentCount": comment_count,
            },
        },
    }


class FakeBrowserRuntime:
    def __init__(self):
        self.executed = []
        self.closed = []

    def open_or_reuse_url(self, url, reuse_existing_tab=False, reuse_domain=None):
        return {
            "id": "tab-1",
            "targetId": "tab-1",
            "url": url,
            "reused": False,
        }

    def wait_for_page(self, target_id, timeout_seconds=8, interval_seconds=0.4):
        return {"ok": True}

    def execute_js(self, expression, target_id=None):
        self.executed.append((expression, target_id))
        return {"scrollY": 1000, "articleCount": 10}

    def close_tab(self, target_id):
        self.closed.append(target_id)


class SequenceReadService:
    def __init__(self, counts):
        self.counts = list(counts)
        self.calls = 0

    def site_read(self, site, kind, params=None, target_id=None, timeout_seconds=20):
        self.calls += 1
        index = min(self.calls - 1, len(self.counts) - 1)
        return make_read_result(self.counts[index])


class XReadPostCommentScrollTest(unittest.TestCase):
    def test_scrolls_until_comment_limit_is_reached(self):
        browser = FakeBrowserRuntime()
        read_service = SequenceReadService([2, 4, 6])

        result = run(
            read_service=read_service,
            browser_runtime=browser,
            params={
                "url": "https://x.com/example/status/12345",
                "commentLimit": 5,
                "commentScrollRounds": 4,
                "intervalSeconds": 0,
            },
        )

        self.assertTrue(result["ok"])
        self.assertEqual(read_service.calls, 3)
        self.assertEqual(len(browser.executed), 2)
        self.assertEqual(len(result["content"]["commentItems"]), 6)
        self.assertEqual(result["semantic"]["comments"]["count"], 5)
        self.assertEqual(result["debug"]["commentScroll"]["initialCount"], 2)
        self.assertEqual(result["debug"]["commentScroll"]["finalCount"], 6)
        self.assertEqual(result["debug"]["commentScroll"]["stoppedReason"], "target_reached")

    def test_does_not_scroll_when_initial_read_has_enough_comments(self):
        browser = FakeBrowserRuntime()
        read_service = SequenceReadService([5])

        result = run(
            read_service=read_service,
            browser_runtime=browser,
            params={
                "url": "https://x.com/example/status/12345",
                "commentLimit": 5,
                "intervalSeconds": 0,
            },
        )

        self.assertTrue(result["ok"])
        self.assertEqual(read_service.calls, 1)
        self.assertEqual(browser.executed, [])
        self.assertEqual(result["debug"]["commentScroll"]["stoppedReason"], "target_reached")


if __name__ == "__main__":
    unittest.main()
