from .common import close_temporary_tab, open_weibo_page, response_target_id
from ....media.image_cache import process_and_spawn_downloads


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    keyword = ((params or {}).get("keyword") or (params or {}).get("query") or "").strip()
    if not keyword:
        return {
            "ok": False,
            "site": "weibo",
            "workflow": "search",
            "error": "keyword is required",
        }

    resolved_target_id, opened = open_weibo_page(
        browser_runtime,
        url=f"https://s.weibo.com/weibo?q={keyword}",
        target_id=target_id,
    )
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "weibo",
            "workflow": "search",
            "error": "failed to open page",
        }

    try:
        read_params = dict(params)
        read_params.pop("keyword", None)
        read_result = read_service.site_read(
            site="weibo",
            kind="search",
            params=read_params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not read_result:
            return {
                "ok": False,
                "site": "weibo",
                "workflow": "search",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "weibo",
                "workflow": "search",
                "targetId": response_target_id(opened, resolved_target_id),
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        actual_page_type = ((read_result.get("signals") or {}).get("pageType"))
        if actual_page_type != "search":
            return {
                "ok": False,
                "site": "weibo",
                "workflow": "search",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "unexpected page type",
                "expectedPageType": "search",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }

        content = read_result.get("content") or {}
        items = process_and_spawn_downloads((content.get("items") or []))
        return {
            "ok": True,
            "site": "weibo",
            "workflow": "search",
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
                **content,
                "items": items,
            },
            "debug": {
                "open": opened,
                **(read_result.get("debug") or {}),
            },
        }
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
