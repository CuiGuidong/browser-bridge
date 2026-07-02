from urllib.parse import quote

from .common import close_temporary_tab, open_douban_page, response_target_id


def _infer_page_type(read_result):
    signals = read_result.get("signals") or {}
    page_type = read_result.get("pageType") or signals.get("pageType")
    if page_type:
        return page_type
    page = read_result.get("page") or {}
    if "/search" in (page.get("url") or ""):
        return "search"
    return None


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    keyword = (params.get("keyword") or params.get("query") or "").strip()
    if not keyword:
        return {
            "ok": False,
            "site": "douban",
            "workflow": "search",
            "error": "keyword is required",
        }

    url = f"https://www.douban.com/search?q={quote(keyword)}"
    resolved_target_id, opened = open_douban_page(browser_runtime, url=url, target_id=target_id)
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "douban",
            "workflow": "search",
            "error": "failed to open page",
        }

    try:
        read_params = dict(params)
        read_params.update({"keyword": keyword})
        read_result = read_service.site_read(
            site="douban",
            kind="search",
            params=read_params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not read_result:
            return {
                "ok": False,
                "site": "douban",
                "workflow": "search",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "douban",
                "workflow": "search",
                "targetId": response_target_id(opened, resolved_target_id),
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        actual_page_type = _infer_page_type(read_result)
        if actual_page_type != "search":
            return {
                "ok": False,
                "site": "douban",
                "workflow": "search",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "unexpected page type",
                "expectedPageType": "search",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }
        content = read_result.get("content") or {}
        return {
            "ok": bool(read_result.get("ok")),
            "site": "douban",
            "workflow": "search",
            "targetId": response_target_id(opened, resolved_target_id),
            "summary": {
                "source": read_result.get("source"),
                "mode": read_result.get("mode"),
                "pageType": actual_page_type,
            },
            "items": content.get("items") or [],
            "checkpoint": {},
            "page": read_result.get("page") or {},
            "signals": read_result.get("signals") or {},
            "content": content,
            "debug": {
                "open": opened,
                **(read_result.get("debug") or {}),
            },
        }
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
