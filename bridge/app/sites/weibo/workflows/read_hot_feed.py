from .common import close_temporary_tab, collect_flow_items, open_weibo_page, response_target_id
from ....media.image_cache import normalize_image_tags


HOT_FEED_URL = "https://weibo.com/hot/weibo/102803"


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    target_count = int((params or {}).get("targetCount") or 20)
    scroll_rounds = int((params or {}).get("scrollRounds") or 2)
    resolved_target_id, opened = open_weibo_page(
        browser_runtime,
        url=HOT_FEED_URL,
        target_id=target_id,
    )
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "weibo",
            "workflow": "read_hot_feed",
            "error": "failed to open page",
        }

    try:
        collected = collect_flow_items(
            read_service=read_service,
            browser_runtime=browser_runtime,
            kind="read_hot_feed",
            target_id=resolved_target_id,
            params=params,
            timeout_seconds=timeout_seconds,
            target_count=target_count,
            scroll_rounds=scroll_rounds,
        )
        if collected.get("ok") is False:
            return {
                **collected,
                "site": "weibo",
                "workflow": "read_hot_feed",
                "targetId": response_target_id(opened, resolved_target_id),
                "debug": {
                    "open": opened,
                    **(collected.get("debug") or {}),
                },
            }

        read_result = collected.get("readResult") or {}
        actual_page_type = ((read_result.get("signals") or {}).get("pageType"))
        if actual_page_type != "hot_feed":
            return {
                "ok": False,
                "site": "weibo",
                "workflow": "read_hot_feed",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "unexpected page type",
                "expectedPageType": "hot_feed",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }

        items = normalize_image_tags(collected.get("items") or [])
        return {
            "ok": True,
            "site": "weibo",
            "workflow": "read_hot_feed",
            "targetId": response_target_id(opened, resolved_target_id),
            "summary": {
                "source": read_result.get("source"),
                "mode": read_result.get("mode"),
                "pageType": actual_page_type,
            },
            "items": [],
            "checkpoint": {},
            "page": read_result.get("page") or {},
            "signals": read_result.get("signals") or {},
            "content": {
                "items": items,
            },
            "debug": {
                "open": opened,
                "scrollRounds": collected.get("scrollRounds"),
                **(read_result.get("debug") or {}),
            },
        }
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
