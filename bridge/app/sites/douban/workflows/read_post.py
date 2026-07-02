from .common import close_temporary_tab, open_douban_page, response_target_id
from ...read_post_semantics import (
    build_read_post_diagnostics,
    build_read_post_semantic,
    normalize_comment_limit,
)


def _infer_page_type(read_result):
    signals = read_result.get("signals") or {}
    page_type = read_result.get("pageType") or signals.get("pageType")
    if page_type:
        return page_type
    page = read_result.get("page") or {}
    if "/subject/" in (page.get("url") or ""):
        return "post"
    return None


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    url = (params.get("url") or "").strip()
    if not url and not target_id:
        return {
            "ok": False,
            "site": "douban",
            "workflow": "read_post",
            "error": "url is required",
        }
    comment_limit = normalize_comment_limit(params.get("commentLimit"))
    resolved_target_id, opened = open_douban_page(browser_runtime, url=url or None, target_id=target_id)
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "douban",
            "workflow": "read_post",
            "error": "failed to open page",
        }

    try:
        read_params = dict(params)
        read_params.pop("url", None)
        read_params["commentLimit"] = comment_limit
        read_result = read_service.site_read(
            site="douban",
            kind="read_post",
            params=read_params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not read_result:
            return {
                "ok": False,
                "site": "douban",
                "workflow": "read_post",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "douban",
                "workflow": "read_post",
                "targetId": response_target_id(opened, resolved_target_id),
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        actual_page_type = _infer_page_type(read_result)
        if actual_page_type != "post":
            return {
                "ok": False,
                "site": "douban",
                "workflow": "read_post",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "unexpected page type",
                "expectedPageType": "post",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }

        result = {
            "ok": bool(read_result.get("ok")),
            "site": "douban",
            "workflow": "read_post",
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
        result["semantic"] = build_read_post_semantic("douban", result, comment_limit=comment_limit)
        result["diagnostics"] = build_read_post_diagnostics("douban", result)
        return result
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
