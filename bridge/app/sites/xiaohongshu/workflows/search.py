from urllib.parse import quote


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    keyword = ((params or {}).get("keyword") or "").strip()
    if not keyword:
        return {
            "ok": False,
            "site": "xiaohongshu",
            "workflow": "search",
            "error": "keyword is required",
        }

    url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}"
    opened = None
    resolved_target_id = target_id
    if resolved_target_id:
        opened = browser_runtime.navigate_tab(resolved_target_id, url)
        if not opened:
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "search",
                "error": "failed to open page",
            }
        resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
    else:
        opened = browser_runtime.open_or_reuse_url(
            url,
            reuse_existing_tab=False,
            reuse_domain="xiaohongshu.com",
        )
        if not opened:
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "search",
                "error": "failed to open page",
            }
        resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
    try:
        read_params = dict(params)
        read_params.pop("keyword", None)
        read_result = read_service.site_read(
            site="xiaohongshu",
            kind="search",
            params=read_params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not read_result:
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "search",
                "targetId": None if not opened.get("reused") else resolved_target_id,
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "xiaohongshu",
                "workflow": "search",
                "targetId": None if opened is not None and not opened.get("reused") else resolved_target_id,
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        actual_page_type = ((read_result.get("signals") or {}).get("pageType"))
        if actual_page_type != "search":
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "search",
                "targetId": None if not opened.get("reused") else resolved_target_id,
                "error": "unexpected page type",
                "expectedPageType": "search",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }

        result = {
            "ok": bool(read_result.get("ok")),
            "site": "xiaohongshu",
            "workflow": "search",
            "targetId": None if not opened.get("reused") else resolved_target_id,
            "summary": {
                "source": read_result.get("source"),
                "mode": read_result.get("mode"),
                "pageType": read_result.get("pageType"),
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
        return result
    finally:
        if opened is not None and not opened.get("reused") and resolved_target_id:
            try:
                browser_runtime.close_tab(resolved_target_id)
            except Exception:
                pass
