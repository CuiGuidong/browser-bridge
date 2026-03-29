from .common import close_temporary_tab, open_x_page, response_target_id
from ....media.image_cache import process_and_spawn_downloads


def _infer_page_type(read_result):
    page = read_result.get("page") or {}
    url = page.get("url") or ""
    if "/i/bookmarks" in url:
        return "bookmarks"
    return None


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    resolved_target_id, opened = open_x_page(
        browser_runtime,
        url="https://x.com/i/bookmarks",
        target_id=target_id,
    )
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "x",
            "workflow": "list_bookmarks",
            "error": "failed to open page",
        }

    try:
        read_result = read_service.site_read(
            site="x",
            kind="list_bookmarks",
            params=params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not read_result:
            return {
                "ok": False,
                "site": "x",
                "workflow": "list_bookmarks",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "x",
                "workflow": "list_bookmarks",
                "targetId": response_target_id(opened, resolved_target_id),
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        actual_page_type = _infer_page_type(read_result)
        if actual_page_type != "bookmarks":
            return {
                "ok": False,
                "site": "x",
                "workflow": "list_bookmarks",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "unexpected page type",
                "expectedPageType": "bookmarks",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }
        return {
            "ok": bool(read_result.get("ok")),
            "site": "x",
            "workflow": "list_bookmarks",
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
                **(read_result.get("content") or {}),
                "timeline": process_and_spawn_downloads(((read_result.get("content") or {}).get("timeline")) or []),
            },
            "debug": {
                "open": opened,
                **(read_result.get("debug") or {}),
            },
        }
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
