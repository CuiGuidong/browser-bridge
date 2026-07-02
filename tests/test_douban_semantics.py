import unittest

from bridge.app.sites.read_post_semantics import build_read_post_semantic


def douban_workflow_payload():
    return {
        "ok": True,
        "site": "douban",
        "workflow": "read_post",
        "content": {
            "url": "https://movie.douban.com/subject/37523009/",
            "externalPostId": "37523009",
            "platformType": "douban_subject",
            "subject": {
                "id": "37523009",
                "title": "金特务：本色回归",
                "originalTitle": "김부장",
                "year": 2026,
                "category": "tv_series",
                "cover": "https://img3.doubanio.com/test.webp",
                "summary": "韩国动作剧。",
                "directors": [{"name": "李胜英", "url": "https://movie.douban.com/celebrity/1/"}],
                "writers": [{"name": "南大中"}],
                "actors": [{"name": "苏志燮"}],
                "genres": ["剧情", "动作"],
                "countries": ["韩国"],
                "languages": ["韩语"],
                "releaseDate": "2026-06-26",
                "releaseLabel": "2026-06-26(韩国)",
                "episodeCount": 10,
                "aka": ["金部长", "Agent Kim"],
                "imdb": "tt42127457",
            },
            "rating": {
                "score": None,
                "ratingCount": 0,
                "best": 10,
                "worst": 2,
                "starWeights": [],
            },
            "interestStats": {
                "wish": 10765,
                "do": 2129,
                "collect": 1057,
            },
            "viewerInterest": {
                "value": None,
                "label": None,
                "detected": False,
            },
            "metrics": {
                "comments": 326,
                "favorites": None,
            },
            "commentsTotal": 326,
            "comments": [
                {
                    "id": "4875068122",
                    "authorName": "朱威",
                    "author": {
                        "displayName": "朱威",
                        "profileUrl": "https://www.douban.com/people/225587603/",
                    },
                    "time": "2026-06-27 00:52:55",
                    "text": "很一般，节奏又乱又拖沓。",
                    "metrics": {
                        "likes": 66,
                        "comments": None,
                    },
                    "platformMetrics": {
                        "status": "collect",
                        "statusLabel": "看过",
                        "rating": 2,
                        "ratingLabel": "较差",
                        "location": "北京",
                    },
                }
            ],
        },
    }


class DoubanSemanticsTest(unittest.TestCase):
    def test_douban_read_post_semantic_is_shallow_compatibility(self):
        result = build_read_post_semantic("douban", douban_workflow_payload(), comment_limit=20)

        self.assertTrue(result["ok"])
        self.assertEqual(result["schemaVersion"], "read_post.v1")
        self.assertEqual(result["contentItem"]["id"], "37523009")
        self.assertEqual(result["contentItem"]["type"], "post")
        self.assertEqual(result["contentItem"]["platformType"], "douban_subject")
        self.assertIsNone(result["contentItem"]["author"])
        self.assertEqual(result["contentItem"]["published"]["at"], "2026-06-26")
        self.assertEqual(result["contentItem"]["published"]["label"], "2026-06-26(韩国)")
        self.assertEqual(result["contentItem"]["metrics"]["comments"], 326)
        self.assertIsNone(result["contentItem"]["metrics"]["favorites"])
        self.assertEqual(result["contentItem"]["platformMetrics"]["wish"], 10765)
        self.assertEqual(result["contentItem"]["platformMetrics"]["do"], 2129)
        self.assertEqual(result["contentItem"]["platformMetrics"]["collect"], 1057)
        self.assertEqual(result["contentItem"]["platformMetrics"]["ratingCount"], 0)
        self.assertEqual(
            result["platform"]["specific"]["douban"]["subjectRef"],
            {"id": "37523009", "schemaVersion": "douban.subject.v1"},
        )

    def test_douban_comments_keep_comment_metrics_and_platform_metrics(self):
        result = build_read_post_semantic("douban", douban_workflow_payload(), comment_limit=20)
        comment = result["comments"]["items"][0]

        self.assertEqual(comment["authorName"], "朱威")
        self.assertEqual(comment["time"], "2026-06-27 00:52:55")
        self.assertEqual(comment["text"], "很一般，节奏又乱又拖沓。")
        self.assertEqual(comment["metrics"]["likes"], 66)
        self.assertEqual(comment["platformMetrics"]["status"], "collect")
        self.assertEqual(comment["platformMetrics"]["rating"], 2)
        self.assertEqual(comment["platformMetrics"]["location"], "北京")

    def test_douban_comment_limit_zero_keeps_total(self):
        result = build_read_post_semantic("douban", douban_workflow_payload(), comment_limit=0)

        self.assertEqual(result["comments"]["items"], [])
        self.assertEqual(result["comments"]["limit"], 0)
        self.assertEqual(result["comments"]["count"], 0)
        self.assertEqual(result["comments"]["total"], 326)


if __name__ == "__main__":
    unittest.main()
