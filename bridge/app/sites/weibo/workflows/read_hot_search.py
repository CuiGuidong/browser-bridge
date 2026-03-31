from .common import close_temporary_tab, open_weibo_page, response_target_id


HOT_SEARCH_URL = "https://weibo.com/hot/search"


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    resolved_target_id, opened = open_weibo_page(
        browser_runtime,
        url=HOT_SEARCH_URL,
        target_id=target_id,
    )
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "weibo",
            "workflow": "read_hot_search",
            "error": "failed to open page",
        }

    try:
        browser_runtime.wait_for_page(
            target_id=resolved_target_id,
            timeout_seconds=min(timeout_seconds, 12),
            interval_seconds=0.5,
        )
        read_result = read_service.site_read(
            site="weibo",
            kind="read_hot_search",
            params=params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if (
            read_result
            and read_result.get("ok")
            and not (((read_result.get("content") or {}).get("items")) or [])
        ):
            browser_runtime.wait_for_page(
                target_id=resolved_target_id,
                timeout_seconds=3,
                interval_seconds=0.5,
            )
            read_result = read_service.site_read(
                site="weibo",
                kind="read_hot_search",
                params=params,
                target_id=resolved_target_id,
                timeout_seconds=timeout_seconds,
            )
        if not read_result:
            return {
                "ok": False,
                "site": "weibo",
                "workflow": "read_hot_search",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "weibo",
                "workflow": "read_hot_search",
                "targetId": response_target_id(opened, resolved_target_id),
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        actual_page_type = ((read_result.get("signals") or {}).get("pageType"))
        if actual_page_type != "hot_search":
            return {
                "ok": False,
                "site": "weibo",
                "workflow": "read_hot_search",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "unexpected page type",
                "expectedPageType": "hot_search",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }

        return {
            "ok": True,
            "site": "weibo",
            "workflow": "read_hot_search",
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
            "content": read_result.get("content") or {},
            "debug": {
                "open": opened,
                **(read_result.get("debug") or {}),
            },
        }
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
