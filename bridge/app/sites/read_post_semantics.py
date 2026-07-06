import re

from ..media.image_cache import normalize_image_tags, normalize_media_items


SCHEMA_VERSION = "read_post.v1"
ALLOWED_GENERAL_METRICS = {
    "views",
    "likes",
    "comments",
    "shares",
    "reposts",
    "quotes",
    "favorites",
}

COMMENT_METRICS = {
    "likes",
    "comments",
    "replies",
}

PLATFORM_TYPE_BY_SITE = {
    "x": "tweet",
    "weibo": "weibo_post",
    "xiaohongshu": "xhs_note",
    "zhihu": "zhihu_answer",
    "douban": "douban_subject",
    "reddit": "reddit_post",
    "bilibili": "bilibili_video",
    "youtube": "youtube_video",
}

CONTENT_TYPE_BY_SITE = {
    "x": "post",
    "weibo": "post",
    "xiaohongshu": "note",
    "zhihu": "answer",
    "douban": "post",
    "reddit": "discussion",
    "bilibili": "video",
    "youtube": "video",
}

PLATFORM_LABELS_BY_SITE = {
    "x": {
        "like": "Like",
        "repost": "Repost",
        "quote": "Quote",
        "bookmark": "Bookmark",
    },
    "weibo": {
        "like": "赞",
        "repost": "转发",
        "comment": "评论",
    },
    "xiaohongshu": {
        "like": "点赞",
        "favorite": "收藏",
        "comment": "评论",
    },
    "zhihu": {
        "like": "赞同",
        "favorite": "收藏",
        "comment": "评论",
    },
    "douban": {
        "wish": "想看",
        "do": "在看",
        "collect": "看过",
        "comment": "短评",
    },
    "bilibili": {
        "like": "点赞",
        "favorite": "收藏",
        "coin": "投币",
        "danmaku": "弹幕",
    },
    "reddit": {
        "score": "score",
        "comment": "comments",
    },
}

PLATFORM_METRIC_DEFINITIONS = {
    "coins": {
        "label": "投币",
        "description": "B 站用户对视频的投币数，是 B 站特有的支持类互动，不等同于点赞或收藏。",
    },
    "danmaku": {
        "label": "弹幕",
        "description": "B 站视频播放过程中叠加显示的实时评论数量，不等同于普通评论数。",
    },
    "score": {
        "label": "score",
        "description": "Reddit、HackerNews 等平台的投票聚合分，不等同于点赞数。",
    },
    "upvoteRatio": {
        "label": "upvote ratio",
        "description": "Reddit 顶赞比例，是平台特有投票指标，不等同于点赞数。",
    },
    "thanks": {
        "label": "感谢",
        "description": "平台特有的感谢类互动，不等同于点赞或收藏。",
    },
    "bookmarks": {
        "label": "书签",
        "description": "X 等平台的书签指标。仅当页面公开显示数量时使用，不代表当前用户是否已收藏。",
    },
}

METRIC_ALIASES = {
    "readCount": "views",
    "playCount": "views",
    "viewCount": "views",
    "like": "likes",
    "liked": "likes",
    "comment": "comments",
    "commentCount": "comments",
    "share": "shares",
    "shareCount": "shares",
    "repost": "reposts",
    "repostCount": "reposts",
    "retweets": "reposts",
    "quote": "quotes",
    "quoteCount": "quotes",
    "favorite": "favorites",
    "favoriteCount": "favorites",
    "collect": "favorites",
    "collects": "favorites",
}


def parse_count(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value)
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    match = re.search(r"([\d.]+)\s*([万亿kKmMbB]?)", text)
    if not match:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    unit = match.group(2)
    if unit == "万":
        number *= 10_000
    elif unit == "亿":
        number *= 100_000_000
    elif unit in {"k", "K"}:
        number *= 1_000
    elif unit in {"m", "M"}:
        number *= 1_000_000
    elif unit in {"b", "B"}:
        number *= 1_000_000_000
    return round(number)


def split_metrics(site, raw_metrics):
    raw_metrics = raw_metrics or {}
    general = {key: None for key in sorted(ALLOWED_GENERAL_METRICS)}
    platform_metrics = {}

    for raw_key, raw_value in raw_metrics.items():
        key = METRIC_ALIASES.get(raw_key, raw_key)
        parsed = parse_count(raw_value)
        value = parsed if parsed is not None else raw_value
        if key in ALLOWED_GENERAL_METRICS:
            general[key] = value
        elif raw_value is not None:
            platform_metrics[raw_key] = value

    return general, platform_metrics


def normalize_author(raw_author):
    if isinstance(raw_author, str):
        return {
            "id": None,
            "displayName": raw_author or None,
            "handle": None,
            "profileUrl": None,
            "verified": None,
        }
    raw_author = raw_author or {}
    display_name = (
        raw_author.get("displayName")
        or raw_author.get("nickname")
        or raw_author.get("name")
        or raw_author.get("author")
    )
    return {
        "id": raw_author.get("id"),
        "displayName": display_name,
        "handle": raw_author.get("handle"),
        "profileUrl": raw_author.get("profileUrl") or raw_author.get("authorProfileUrl"),
        "verified": raw_author.get("verified"),
    }


def normalize_author_name(raw_author):
    if isinstance(raw_author, dict):
        return (
            raw_author.get("displayName")
            or raw_author.get("nickname")
            or raw_author.get("name")
            or raw_author.get("handle")
        )
    return raw_author


def normalize_text(text):
    if not text:
        return None
    return normalize_image_tags(str(text).strip()) or None


def media_from_urls(urls, media_type, placement):
    result = []
    for url in urls or []:
        if isinstance(url, dict):
            item = dict(url)
            item.setdefault("type", media_type)
        else:
            item = {
                "type": media_type,
                "url": url,
            }
        item.setdefault("placement", placement)
        result.append(item)
    return result


def normalize_media(raw_media, placement_default="after_text"):
    normalized = []
    for raw_item in raw_media or []:
        if isinstance(raw_item, str):
            raw_item = {
                "type": "image",
                "url": raw_item,
            }
        if not isinstance(raw_item, dict):
            continue
        media_type = raw_item.get("type") or raw_item.get("mediaType") or "unknown"
        if media_type == "photo":
            media_type = "image"
        if media_type == "card":
            media_type = "link_card"
        normalized.append({
            "type": media_type,
            "url": raw_item.get("url") or raw_item.get("src"),
            "localPath": raw_item.get("localPath"),
            "order": raw_item.get("order"),
            "placement": raw_item.get("placement") or placement_default,
            "alt": raw_item.get("alt"),
            "title": raw_item.get("title"),
            "source": raw_item.get("source"),
        })

    for index, item in enumerate(normalized, start=1):
        item["order"] = item.get("order") or index
    return normalize_media_items(normalized)


def normalize_comment(raw_comment):
    raw_comment = raw_comment or {}
    raw_metrics = raw_comment.get("metrics") or {}
    metrics = {}
    for key in sorted(COMMENT_METRICS):
        metrics[key] = parse_count(raw_metrics.get(key))
    text = normalize_text(raw_comment.get("text"))
    author_name = raw_comment.get("authorName") or normalize_author_name(raw_comment.get("author"))
    return {
        "authorName": author_name,
        "time": raw_comment.get("time")
        or raw_comment.get("publishedLabel")
        or raw_comment.get("publishedAt"),
        "text": text,
        "media": normalize_media(raw_comment.get("media") or [], placement_default="inline"),
        "metrics": metrics,
        "platformMetrics": raw_comment.get("platformMetrics") or {},
    }


def normalize_filtered_item(raw_item):
    if not isinstance(raw_item, dict):
        return {
            "reason": "unknown",
            "textPreview": str(raw_item)[:120],
        }
    author_name = raw_item.get("authorName") or normalize_author_name(raw_item.get("author"))
    return {
        "reason": raw_item.get("reason") or "unknown",
        "statusId": raw_item.get("statusId"),
        "authorName": author_name,
        "textPreview": raw_item.get("textPreview") or (raw_item.get("text") or "")[:120],
    }


def normalize_cover(raw_cover):
    if not raw_cover:
        return None
    if isinstance(raw_cover, str):
        return {
            "type": "image",
            "url": raw_cover.strip(),
            "alt": None
        }
    if isinstance(raw_cover, dict):
        return {
            "type": raw_cover.get("type") or "image",
            "url": (raw_cover.get("url") or raw_cover.get("src") or "").strip(),
            "alt": raw_cover.get("alt") or None,
            "title": raw_cover.get("title") or None,
            "source": raw_cover.get("source") or None,
            "role": raw_cover.get("role") or "cover",
            "placement": raw_cover.get("placement") or "cover",
        }
    return None


def collect_raw_media(content, placement_default):
    media = []
    media.extend(content.get("media") or [])
    media.extend(media_from_urls(content.get("images") or [], "image", placement_default))
    media.extend(media_from_urls(content.get("videos") or [], "video", placement_default))
    raw_cover = content.get("cover") or content.get("post", {}).get("cover")
    if raw_cover:
        if isinstance(raw_cover, str):
            media.append({
                "type": "image",
                "url": raw_cover.strip(),
                "placement": "cover",
                "role": "cover",
            })
        elif isinstance(raw_cover, dict):
            item = dict(raw_cover)
            item.setdefault("type", "image")
            item.setdefault("placement", "cover")
            item.setdefault("role", "cover")
            media.append(item)
    return media


def content_payload_for_site(site, workflow_payload):
    content = workflow_payload.get("content") or {}
    if site == "x" and isinstance(content.get("post"), dict):
        return content.get("post") or {}
    return content


def raw_metrics_for_site(site, content):
    metrics = dict(content.get("metrics") or {})
    if content.get("engagement"):
        metrics.update(content.get("engagement") or {})
    return metrics


def normalize_douban_content_item(workflow_payload):
    content = workflow_payload.get("content") or {}
    subject = content.get("subject") or {}
    raw_metrics = dict(content.get("metrics") or {})
    if raw_metrics.get("comments") is None:
        raw_metrics["comments"] = content.get("commentsTotal")
    raw_metrics["favorites"] = None
    metrics, _ = split_metrics("douban", raw_metrics)
    rating = content.get("rating") or {}
    interest_stats = content.get("interestStats") or {}
    viewer_interest = content.get("viewerInterest") or {}
    platform_metrics = {}
    if rating.get("score") is not None:
        platform_metrics["ratingScore"] = rating.get("score")
    if rating.get("ratingCount") is not None:
        platform_metrics["ratingCount"] = rating.get("ratingCount")
    for key in ["wish", "do", "collect"]:
        if interest_stats.get(key) is not None:
            platform_metrics[key] = parse_count(interest_stats.get(key))
    if viewer_interest:
        platform_metrics["viewerInterest"] = viewer_interest

    media = []
    if subject.get("cover"):
        media.append({
            "type": "image",
            "url": subject.get("cover"),
            "placement": "cover",
        })

    return {
        "id": subject.get("id") or content.get("externalPostId"),
        "url": content.get("url") or (workflow_payload.get("page") or {}).get("url"),
        "type": "post",
        "platformType": content.get("platformType") or "douban_subject",
        "title": subject.get("title"),
        "cover": normalize_cover(subject.get("cover")),
        "author": None,
        "published": {
            "at": subject.get("releaseDate"),
            "label": subject.get("releaseLabel") or subject.get("releaseDate"),
            "location": None,
            "source": None,
        },
        "text": None,
        "summary": normalize_text(subject.get("summary")),
        "tags": subject.get("genres") or [],
        "media": normalize_media(media, "cover"),
        "metrics": metrics,
        "platformMetrics": platform_metrics,
    }


def normalize_content_item(site, workflow_payload):
    content = workflow_payload.get("content") or {}
    if site == "douban" and isinstance(content.get("subject"), dict):
        return normalize_douban_content_item(workflow_payload)
    content = content_payload_for_site(site, workflow_payload)
    raw_metrics = raw_metrics_for_site(site, content)
    metrics, platform_metrics = split_metrics(site, raw_metrics)
    platform_type = content.get("platformType") or PLATFORM_TYPE_BY_SITE.get(site) or f"{site}_post"
    content_type = content.get("type") or CONTENT_TYPE_BY_SITE.get(site) or "post"
    text = normalize_text(content.get("text"))
    summary = normalize_text(content.get("summary") or content.get("description"))
    placement_default = "inline" if text and "[Image" in text else "after_text"
    cover = normalize_cover(content.get("cover") or content.get("post", {}).get("cover"))

    return {
        "id": content.get("id")
        or content.get("statusId")
        or content.get("externalPostId")
        or content.get("postId"),
        "url": content.get("url") or (workflow_payload.get("page") or {}).get("url"),
        "type": content_type,
        "platformType": platform_type,
        "title": content.get("title"),
        "cover": cover,
        "author": normalize_author(content.get("author") or {
            "displayName": content.get("authorName") or content.get("nickname"),
            "profileUrl": content.get("authorProfileUrl"),
        }),
        "published": {
            "at": content.get("publishedAt"),
            "label": content.get("publishedLabel") or content.get("publishedAt"),
            "location": content.get("publishedLocation") or content.get("location"),
            "source": content.get("publishedSource") or content.get("source"),
        },
        "text": text,
        "summary": summary,
        "tags": content.get("tags") or [],
        "media": normalize_media(collect_raw_media(content, placement_default), placement_default),
        "metrics": metrics,
        "platformMetrics": platform_metrics,
    }


def normalize_thread_item(site, raw_item):
    raw_item = raw_item or {}
    metrics, platform_metrics = split_metrics(site, raw_item.get("metrics") or {})
    text = normalize_text(raw_item.get("text"))
    return {
        "id": raw_item.get("id") or raw_item.get("statusId") or raw_item.get("externalPostId"),
        "url": raw_item.get("url"),
        "type": raw_item.get("type") or CONTENT_TYPE_BY_SITE.get(site) or "post",
        "platformType": raw_item.get("platformType") or PLATFORM_TYPE_BY_SITE.get(site) or f"{site}_post",
        "title": raw_item.get("title"),
        "author": normalize_author(raw_item.get("author") or raw_item.get("authorName")),
        "published": {
            "at": raw_item.get("publishedAt"),
            "label": raw_item.get("publishedLabel") or raw_item.get("publishedAt"),
            "location": raw_item.get("publishedLocation") or raw_item.get("location"),
            "source": raw_item.get("publishedSource") or raw_item.get("source"),
        },
        "text": text,
        "summary": normalize_text(raw_item.get("summary") or raw_item.get("description")),
        "tags": raw_item.get("tags") or [],
        "media": normalize_media(raw_item.get("media") or [], "inline" if text and "[Image" in text else "after_text"),
        "metrics": metrics,
        "platformMetrics": platform_metrics,
        "relation": raw_item.get("relation") or "unknown",
    }


def raw_thread_items(site, workflow_payload):
    content = workflow_payload.get("content") or {}
    items = content.get("threadItems")
    if items is None and site == "x":
        items = []
        for item in content.get("contextItems") or []:
            if (item or {}).get("relation") == "visible_context":
                items.append({
                    **item,
                    "relation": "unknown",
                })
    return items or []


def raw_comment_items(workflow_payload):
    content = workflow_payload.get("content") or {}
    return content.get("commentItems") or content.get("comments") or []


def raw_filtered_items(workflow_payload):
    content = workflow_payload.get("content") or {}
    return content.get("filteredItems") or content.get("filtered") or []


def derive_partial_and_missing(site, workflow_payload, comment_limit):
    content = workflow_payload.get("content") or {}
    partial = bool(workflow_payload.get("partial") or content.get("partial"))
    missing = list(workflow_payload.get("missing") or content.get("missing") or [])
    comments = raw_comment_items(workflow_payload)
    comments_unavailable = (
        content.get("commentsUnavailableReason")
        or content.get("commentsUnsupportedReason")
        or content.get("commentsNotLoadedReason")
    )
    if comment_limit and not comments and comments_unavailable and "comments" not in missing:
        partial = True
        missing.append("comments")
    return partial, missing


def normalize_comment_limit(value, default=20, minimum=0, maximum=100):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = default
    return min(max(limit, minimum), maximum)


def build_read_post_semantic(site, workflow_payload, comment_limit=20):
    workflow_payload = workflow_payload or {}
    content = workflow_payload.get("content") or {}
    comments = [normalize_comment(item) for item in raw_comment_items(workflow_payload)]
    filtered = [normalize_filtered_item(item) for item in raw_filtered_items(workflow_payload)]
    thread_items = [normalize_thread_item(site, item) for item in raw_thread_items(site, workflow_payload)]
    partial, missing = derive_partial_and_missing(site, workflow_payload, comment_limit)
    relation = "none"
    if thread_items:
        relation = thread_items[0].get("relation") or "unknown"

    result = {
        "ok": bool(workflow_payload.get("ok")),
        "site": site,
        "schemaVersion": SCHEMA_VERSION,
        "contentItem": normalize_content_item(site, workflow_payload),
        "thread": {
            "items": thread_items,
            "relation": relation,
            "complete": content.get("threadComplete"),
        },
        "comments": {
            "items": comments[:comment_limit] if comment_limit else [],
            "limit": comment_limit,
            "count": min(len(comments), comment_limit) if comment_limit else 0,
            "total": content.get("commentsTotal"),
            "hasMore": content.get("commentsHasMore"),
            "nextCursor": content.get("commentsNextCursor"),
            "sort": content.get("commentsSort") or "platform_default",
            "filtered": filtered,
        },
        "platform": {
            "labels": PLATFORM_LABELS_BY_SITE.get(site, {}),
            "metricDefinitions": {},
            "specific": {},
        },
    }

    metric_definitions = {}
    for key in result["contentItem"]["platformMetrics"]:
        if key in PLATFORM_METRIC_DEFINITIONS:
            metric_definitions[key] = PLATFORM_METRIC_DEFINITIONS[key]
    result["platform"]["metricDefinitions"] = metric_definitions

    platform_specific = {}
    if content.get("questionDescription"):
        platform_specific["questionDescription"] = content.get("questionDescription")
    if content.get("community"):
        platform_specific["community"] = content.get("community")
    if content.get("videoContentParsed") is not None:
        platform_specific["videoContentParsed"] = content.get("videoContentParsed")
    if site == "douban" and isinstance(content.get("subject"), dict):
        subject = content.get("subject") or {}
        platform_specific["douban"] = {
            "subjectRef": {
                "id": subject.get("id") or content.get("externalPostId"),
                "schemaVersion": "douban.subject.v1",
            },
        }
    result["platform"]["specific"] = platform_specific

    if partial:
        result["partial"] = True
        result["missing"] = missing
    return result


def build_read_post_diagnostics(site, workflow_payload):
    workflow_payload = workflow_payload or {}
    content = workflow_payload.get("content") or {}
    raw_payload = content.get("rawPayload") or workflow_payload.get("rawPayload") or {}
    page = workflow_payload.get("page") or {}
    semantic = workflow_payload.get("semantic") or {}
    diagnostics = {
        "site": site,
        "page": {
            "url": page.get("url"),
            "title": page.get("title"),
        },
        "targetId": workflow_payload.get("targetId"),
        "targetStatusId": raw_payload.get("targetStatusId") or raw_payload.get("targetId"),
        "matchedStatusId": raw_payload.get("matchedStatusId") or raw_payload.get("matchedId"),
        "matchStrategy": raw_payload.get("matchStrategy") or workflow_payload.get("matchStrategy"),
        "candidateCount": raw_payload.get("candidateCount") or raw_payload.get("adapterCandidateCount"),
        "filteredCount": len(raw_filtered_items(workflow_payload)),
        "missing": semantic.get("missing") or workflow_payload.get("missing") or content.get("missing") or [],
        "partial": bool(semantic.get("partial") or workflow_payload.get("partial") or content.get("partial")),
        "adapterVersion": raw_payload.get("adapterVersion") or content.get("adapterVersion"),
    }
    return diagnostics
