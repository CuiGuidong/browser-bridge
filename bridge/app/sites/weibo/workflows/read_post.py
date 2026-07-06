import time
from urllib.parse import urlparse

from .common import close_temporary_tab, open_weibo_page, response_target_id
from ....media.image_cache import normalize_image_tags
from ...read_post_semantics import (
    build_read_post_diagnostics,
    build_read_post_semantic,
    normalize_comment_limit,
)


def _looks_like_post_url(url):
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        parts = [p for p in parsed.path.split("/") if p]
        if (host == "m.weibo.cn" or host.endswith(".m.weibo.cn")) and len(parts) >= 2 and parts[0] == "status":
            return True
        if host == "weibo.com" or host.endswith(".weibo.com"):
            if len(parts) >= 2 and parts[0].isdigit():
                return True
    except Exception:
        return False
    return False


def _wait_for_final_post_page(browser_runtime, target_id, timeout_seconds=20, interval_seconds=0.5):
    started = time.time()
    last_page = None
    while time.time() - started < timeout_seconds:
        page = browser_runtime.get_page_info(target_id)
        last_page = page
        if page and _looks_like_post_url(page.get("url")):
            return page
        time.sleep(interval_seconds)
    return last_page


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    url = ((params or {}).get("url") or "").strip()
    if not url:
        return {
            "ok": False,
            "site": "weibo",
            "workflow": "read_post",
            "error": "url is required",
        }

    resolved_target_id, opened = open_weibo_page(
        browser_runtime,
        url=url,
        target_id=target_id,
    )
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "weibo",
            "workflow": "read_post",
            "error": "failed to open page",
        }

    try:
        final_page = _wait_for_final_post_page(
            browser_runtime=browser_runtime,
            target_id=resolved_target_id,
            timeout_seconds=min(timeout_seconds, 20),
            interval_seconds=0.5,
        )
        if not final_page or not _looks_like_post_url((final_page or {}).get("url")):
            return {
                "ok": False,
                "site": "weibo",
                "workflow": "read_post",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "failed to resolve final post url",
                "page": final_page or {},
            }

        read_params = dict(params)
        read_params.pop("url", None)
        read_result = read_service.site_read(
            site="weibo",
            kind="read_post",
            params=read_params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not read_result:
            return {
                "ok": False,
                "site": "weibo",
                "workflow": "read_post",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "weibo",
                "workflow": "read_post",
                "targetId": response_target_id(opened, resolved_target_id),
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        actual_page_type = ((read_result.get("signals") or {}).get("pageType"))
        if actual_page_type != "post":
            return {
                "ok": False,
                "site": "weibo",
                "workflow": "read_post",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "unexpected page type",
                "expectedPageType": "post",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }

        content = dict(read_result.get("content") or {})
        if content.get("text"):
            content["text"] = normalize_image_tags(content["text"])
        result = {
            "ok": True,
            "site": "weibo",
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
            "content": content,
            "debug": {
                "open": opened,
                **(read_result.get("debug") or {}),
            },
        }
        comment_limit = normalize_comment_limit(params.get("commentLimit"))
        result["semantic"] = build_read_post_semantic("weibo", result, comment_limit=comment_limit)
        result["diagnostics"] = build_read_post_diagnostics("weibo", result)
        return result
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
