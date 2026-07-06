from urllib.parse import urlparse
import time

from ....media.image_cache import normalize_image_tags
from ...read_post_semantics import (
    build_read_post_diagnostics,
    build_read_post_semantic,
    normalize_comment_limit,
)


def _build_note_url(params):
    url = (params or {}).get("url")
    if url:
        return url
    note_id = ((params or {}).get("noteId") or "").strip()
    if not note_id:
        return None
    return f"https://www.xiaohongshu.com/explore/{note_id}"


def _is_final_note_url(url):
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        parts = [p for p in parsed.path.split("/") if p]
        return (
            (host == "www.xiaohongshu.com" or host.endswith(".xiaohongshu.com"))
            and len(parts) >= 2
            and parts[0] == "explore"
        )
    except Exception:
        return False


def _wait_for_final_note_page(browser_runtime, target_id, timeout_seconds=20, interval_seconds=0.5):
    started = time.time()
    last_page = None
    while time.time() - started < timeout_seconds:
        page = browser_runtime.get_page_info(target_id)
        last_page = page
        if page and _is_final_note_url(page.get("url")):
            return page
        time.sleep(interval_seconds)
    return last_page


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    url = _build_note_url(params)
    if not url:
        return {
            "ok": False,
            "site": "xiaohongshu",
            "workflow": "read_post",
            "error": "url or noteId is required",
        }

    opened = None
    resolved_target_id = target_id
    if resolved_target_id:
        opened = browser_runtime.navigate_tab(resolved_target_id, url)
        if not opened:
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "read_post",
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
                "workflow": "read_post",
                "error": "failed to open page",
            }
        resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
    try:
        final_page = _wait_for_final_note_page(
            browser_runtime=browser_runtime,
            target_id=resolved_target_id,
            timeout_seconds=min(timeout_seconds, 20),
            interval_seconds=0.5,
        )
        if not final_page or not _is_final_note_url((final_page or {}).get("url")):
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "read_post",
                "targetId": None if not opened.get("reused") else resolved_target_id,
                "error": "failed to resolve final note url",
                "page": final_page or {},
            }
        read_params = dict(params)
        read_params.pop("url", None)
        read_params.pop("noteId", None)
        read_result = read_service.site_read(
            site="xiaohongshu",
            kind="read_post",
            params=read_params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not read_result:
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "read_post",
                "targetId": None if not opened.get("reused") else resolved_target_id,
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "xiaohongshu",
                "workflow": "read_post",
                "targetId": None if opened is not None and not opened.get("reused") else resolved_target_id,
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        actual_page_type = ((read_result.get("signals") or {}).get("pageType"))
        if actual_page_type != "post":
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "read_post",
                "targetId": None if not opened.get("reused") else resolved_target_id,
                "error": "unexpected page type",
                "expectedPageType": "post",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }

        result = {
            "ok": bool(read_result.get("ok")),
            "site": "xiaohongshu",
            "workflow": "read_post",
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
        content = result.get("content") or {}
        if content.get("text"):
            content["text"] = normalize_image_tags(content["text"])
        result["content"] = content
        comment_limit = normalize_comment_limit(params.get("commentLimit"))
        result["semantic"] = build_read_post_semantic("xiaohongshu", result, comment_limit=comment_limit)
        result["diagnostics"] = build_read_post_diagnostics("xiaohongshu", result)
        return result
    finally:
        if opened is not None and not opened.get("reused") and resolved_target_id:
            try:
                browser_runtime.close_tab(resolved_target_id)
            except Exception:
                pass
