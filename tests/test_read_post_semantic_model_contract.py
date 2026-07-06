import unittest
from pathlib import Path

from bridge.app.sites.common_workflows import run_url_read
from bridge.app.sites.read_post_semantics import (
    ALLOWED_GENERAL_METRICS,
    build_read_post_diagnostics,
    build_read_post_semantic,
)


RAW_FIELD_DENYLIST = {
    "targetId",
    "items",
    "checkpoint",
    "page",
    "signals",
    "debug",
    "rawPayload",
    "primaryText",
}
ALLOWED_METRICS = {
    "views",
    "likes",
    "comments",
    "shares",
    "reposts",
    "quotes",
    "favorites",
}


class FakeBrowserRuntime:
    def __init__(self):
        self.closed = []

    def open_or_reuse_url(self, url, reuse_existing_tab=False, reuse_domain=None):
        return {
            "id": "fake-tab",
            "targetId": "fake-tab",
            "url": url,
            "reused": False,
        }

    def wait_for_page(self, target_id, timeout_seconds=8, interval_seconds=0.4):
        return {"ok": True, "targetId": target_id}

    def close_tab(self, target_id):
        self.closed.append(target_id)


class FakeReadService:
    def site_read(self, site, kind, params=None, target_id=None, timeout_seconds=20):
        return {
            "ok": True,
            "source": "test",
            "mode": "semantic",
            "pageType": kind,
            "page": {
                "url": params.get("url") if params else "https://example.test/post",
                "title": "Test page",
            },
            "signals": {
                "pageType": kind,
            },
            "content": {
                "items": [
                    {
                        "title": "Result",
                        "url": "https://example.test/result",
                    }
                ],
            },
        }


def x_workflow_payload():
    return {
        "ok": True,
        "site": "x",
        "workflow": "read_post",
        "targetId": None,
        "summary": {
            "source": "extension-semantic",
            "mode": "semantic",
            "pageType": "post",
        },
        "items": [],
        "checkpoint": {},
        "page": {
            "url": "https://x.com/laobaishare/status/2068988425072697742",
            "title": "X test",
        },
        "signals": {},
        "content": {
            "primaryText": "compatibility text",
            "post": {
                "statusId": "2068988425072697742",
                "url": "https://x.com/laobaishare/status/2068988425072697742",
                "author": {
                    "displayName": "老白（每日干货分享）",
                    "handle": "@laobaishare",
                },
                "publishedAt": "2026-06-22T09:24:15.000Z",
                "publishedLabel": "下午5:24 · 2026年6月22日",
                "text": "牛逼，Obsidian 创始人下场。\n\n[Image: https://pbs.twimg.com/media/HLaF.jpg]",
                "media": [
                    {
                        "type": "image",
                        "url": "https://pbs.twimg.com/media/HLaF.jpg",
                    }
                ],
                "metrics": {
                    "views": "1.2万",
                    "likes": 123,
                    "comments": 45,
                    "reposts": 6,
                    "quotes": 7,
                    "bookmarks": 8,
                },
            },
            "threadItems": [
                {
                    "statusId": "2068988427673186426",
                    "url": "https://x.com/laobaishare/status/2068988427673186426",
                    "author": {
                        "displayName": "老白（每日干货分享）",
                        "handle": "@laobaishare",
                    },
                    "publishedAt": "2026-06-22T09:24:15.000Z",
                    "publishedLabel": "6月22日",
                    "text": "说白了，他是给 Claude Code、Codex、OpenCode 喂了一套 Obsidian 母语。",
                    "media": [],
                    "metrics": {
                        "likes": 11,
                    },
                    "relation": "same_thread",
                }
            ],
            "commentItems": [
                {
                    "authorName": "crypto-scholar",
                    "time": "6月22日",
                    "text": "@grok 整理这个帖子，他说了啥？",
                    "media": [],
                    "metrics": {
                        "likes": 3,
                        "comments": None,
                        "replies": 1,
                    },
                    "platformMetrics": {},
                }
            ],
            "filteredItems": [
                {
                    "reason": "ad",
                    "authorName": "Amazon",
                    "textPreview": "Shop Prime Day Top 100+ deals",
                }
            ],
            "rawPayload": {
                "targetStatusId": "2068988425072697742",
                "matchedStatusId": "2068988425072697742",
                "matchStrategy": "article_permalink",
                "candidateCount": 8,
            },
        },
        "debug": {
            "open": {
                "id": "fake-tab",
            },
        },
    }


def bilibili_workflow_payload():
    return {
        "ok": True,
        "site": "bilibili",
        "workflow": "read_post",
        "summary": {
            "pageType": "post",
        },
        "content": {
            "url": "https://www.bilibili.com/video/BV1xo7K6gEu4",
            "externalPostId": "BV1xo7K6gEu4",
            "title": "Bilibili video",
            "author": {
                "nickname": "up 主",
            },
            "text": None,
            "description": "视频简介",
            "mediaType": "video",
            "cover": "https://example.test/cover.jpg",
            "metrics": {
                "views": 1000,
                "likes": 200,
                "favorites": 30,
                "coins": 40,
                "danmaku": 50,
                "score": 60,
            },
            "rawPayload": {
                "pageType": "video",
            },
        },
    }


class ReadPostSemanticModelContractTest(unittest.TestCase):
    def test_allowed_general_metrics_constant_matches_contract(self):
        self.assertEqual(ALLOWED_GENERAL_METRICS, ALLOWED_METRICS)

    def test_image_tags_are_not_downloaded_and_no_localPath(self):
        result = build_read_post_semantic("x", x_workflow_payload(), comment_limit=20)
        content_item = result["contentItem"]

        # Verify text preserves remote tag
        self.assertEqual(content_item["text"], "牛逼，Obsidian 创始人下场。\n\n[Image: https://pbs.twimg.com/media/HLaF.jpg]")
        # Verify media list contains URL but no localPath
        self.assertEqual(content_item["media"][0]["url"], "https://pbs.twimg.com/media/HLaF.jpg")
        self.assertNotIn("localPath", content_item["media"][0])

    def test_cover_normalization(self):
        payload = x_workflow_payload()
        payload["content"]["post"]["cover"] = "https://example.test/cover.jpg"

        result = build_read_post_semantic("x", payload, comment_limit=20)
        self.assertEqual(
            result["contentItem"]["cover"],
            {"type": "image", "url": "https://example.test/cover.jpg", "alt": None}
        )

    def test_default_semantic_shape_excludes_raw_fields(self):
        result = build_read_post_semantic("x", x_workflow_payload(), comment_limit=20)

        self.assertTrue(result["ok"])
        self.assertEqual(result["site"], "x")
        self.assertEqual(result["schemaVersion"], "read_post.v1")
        for key in ["contentItem", "thread", "comments", "platform"]:
            self.assertIn(key, result)
        for key in RAW_FIELD_DENYLIST:
            self.assertNotIn(key, result)

    def test_metrics_keys_are_governed(self):
        result = build_read_post_semantic("bilibili", bilibili_workflow_payload(), comment_limit=20)
        content_item = result["contentItem"]

        self.assertLessEqual(set(content_item["metrics"].keys()), ALLOWED_METRICS)
        self.assertEqual(content_item["platformMetrics"]["coins"], 40)
        self.assertEqual(content_item["platformMetrics"]["danmaku"], 50)
        self.assertEqual(content_item["platformMetrics"]["score"], 60)
        self.assertIn("coins", result["platform"]["metricDefinitions"])
        self.assertIn("danmaku", result["platform"]["metricDefinitions"])
        self.assertIn("score", result["platform"]["metricDefinitions"])

    def test_default_comments_are_lightweight_objects(self):
        result = build_read_post_semantic("x", x_workflow_payload(), comment_limit=20)
        comments = result["comments"]["items"]

        self.assertEqual(len(comments), 1)
        self.assertEqual(
            set(comments[0].keys()),
            {"authorName", "time", "text", "media", "metrics", "platformMetrics"},
        )
        self.assertEqual(set(comments[0]["metrics"].keys()), {"likes", "comments", "replies"})

    def test_x_thread_comments_and_filtered_items_are_separated(self):
        result = build_read_post_semantic("x", x_workflow_payload(), comment_limit=20)
        diagnostics = build_read_post_diagnostics("x", {
            **x_workflow_payload(),
            "semantic": result,
        })

        self.assertEqual(result["thread"]["items"][0]["id"], "2068988427673186426")
        self.assertEqual(result["comments"]["items"][0]["authorName"], "crypto-scholar")
        self.assertEqual(result["comments"]["filtered"][0]["reason"], "ad")
        self.assertEqual(diagnostics["filteredCount"], 1)
        self.assertNotIn("crypto-scholar", result["thread"]["items"][0]["text"])
        self.assertNotIn("Amazon", result["comments"]["items"][0]["text"])

    def test_partial_success_requires_missing_fields(self):
        payload = x_workflow_payload()
        payload["content"]["commentItems"] = []
        payload["content"]["commentsUnavailableReason"] = "not_loaded"

        result = build_read_post_semantic("x", payload, comment_limit=20)

        self.assertTrue(result["ok"])
        self.assertTrue(result["partial"])
        self.assertIn("comments", result["missing"])

    def test_zero_visible_comments_without_unavailable_reason_is_complete(self):
        payload = x_workflow_payload()
        payload["content"]["commentItems"] = []
        payload["content"]["commentsUnavailableReason"] = None

        result = build_read_post_semantic("x", payload, comment_limit=20)

        self.assertTrue(result["ok"])
        self.assertNotIn("partial", result)
        self.assertNotIn("missing", result)
        self.assertEqual(result["comments"]["items"], [])

    def test_adapters_do_not_hard_code_twenty_comment_cap(self):
        root = Path(__file__).resolve().parents[1]
        adapter_paths = [
            root / "extension/adapters/weibo-adapter.js",
            root / "extension/adapters/xiaohongshu-adapter.js",
            root / "extension/adapters/media-adapters.js",
        ]

        for path in adapter_paths:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("comments.length >= 20", source)
                self.assertIn("commentLimit", source)

    def test_read_post_semantic_contract_is_not_added_to_non_read_post_workflows(self):
        result = run_url_read(
            site="youtube",
            workflow="search",
            kind="search",
            read_service=FakeReadService(),
            browser_runtime=FakeBrowserRuntime(),
            params={"url": "https://www.youtube.com/results?search_query=openai"},
        )

        self.assertTrue(result["ok"])
        self.assertNotIn("semantic", result)
        self.assertNotIn("diagnostics", result)


if __name__ == "__main__":
    unittest.main()
