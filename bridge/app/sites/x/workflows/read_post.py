import time

from .common import close_temporary_tab, response_target_id, wait_for_target_stable
from ....media.image_cache import normalize_image_tags
from ...read_post_semantics import (
    build_read_post_diagnostics,
    build_read_post_semantic,
    normalize_comment_limit,
)


DEFAULT_COMMENT_SCROLL_ROUNDS = 8
MAX_COMMENT_SCROLL_ROUNDS = 30


def _comment_scroll_script():
    return """
(() => {
  const step = Math.max(Math.floor(window.innerHeight * 0.85), 650);
  window.scrollBy({ top: step, left: 0, behavior: 'instant' });
  return {
    scrollY: Math.round(window.scrollY || 0),
    articleCount: document.querySelectorAll('article[role="article"]').length,
  };
})()
"""


def _infer_page_type(read_result):
    page = read_result.get("page") or {}
    url = page.get("url") or ""
    signals = read_result.get("signals") or {}
    if "/status/" in url:
        return "post"
    if signals.get("isTimeline"):
        return "timeline"
    return None


def _comment_count(read_result):
    content = read_result.get("content") if isinstance(read_result, dict) else {}
    comments = (content or {}).get("commentItems")
    return len(comments) if isinstance(comments, list) else 0


def _normalize_scroll_rounds(value):
    try:
        rounds = int(value)
    except (TypeError, ValueError):
        rounds = DEFAULT_COMMENT_SCROLL_ROUNDS
    return max(0, min(rounds, MAX_COMMENT_SCROLL_ROUNDS))


def _read_x_post(read_service, read_params, resolved_target_id, timeout_seconds):
    return read_service.site_read(
        site="x",
        kind="read_post",
        params=read_params,
        target_id=resolved_target_id,
        timeout_seconds=timeout_seconds,
    )


def _read_with_comment_scroll(
    read_service,
    browser_runtime,
    resolved_target_id,
    read_params,
    timeout_seconds,
    comment_limit,
):
    max_rounds = _normalize_scroll_rounds(read_params.get("commentScrollRounds"))
    try:
        interval_value = read_params.get("intervalSeconds")
        interval_seconds = float(interval_value) if interval_value is not None else 1.0
    except (TypeError, ValueError):
        interval_seconds = 1.0
    interval_seconds = max(0.0, interval_seconds)
    read_result = _read_x_post(read_service, read_params, resolved_target_id, timeout_seconds)
    debug = {
        "enabled": comment_limit > 0,
        "rounds": 0,
        "initialCount": _comment_count(read_result or {}),
        "finalCount": _comment_count(read_result or {}),
        "maxRounds": max_rounds,
        "stoppedReason": None,
    }

    if not read_result or read_result.get("ok") is False or comment_limit <= 0:
        debug["stoppedReason"] = "not_applicable"
        return read_result, debug

    previous_count = debug["initialCount"]
    stable_rounds = 0
    for _ in range(max_rounds):
        if previous_count >= comment_limit:
            debug["stoppedReason"] = "target_reached"
            break
        browser_runtime.execute_js(_comment_scroll_script(), target_id=resolved_target_id)
        debug["rounds"] += 1
        time.sleep(interval_seconds)
        next_result = _read_x_post(read_service, read_params, resolved_target_id, timeout_seconds)
        if not next_result or next_result.get("ok") is False:
            debug["stoppedReason"] = "read_failed_after_scroll"
            break
        next_count = _comment_count(next_result)
        read_result = next_result
        debug["finalCount"] = next_count
        if next_count <= previous_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
        previous_count = next_count
        if stable_rounds >= 2:
            debug["stoppedReason"] = "no_new_comments"
            break
    else:
        debug["stoppedReason"] = "max_rounds"

    if debug["stoppedReason"] is None:
        debug["stoppedReason"] = "target_reached"
    return read_result, debug


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    opened = None
    resolved_target_id = target_id

    if resolved_target_id:
        browser_runtime.activate_tab(resolved_target_id)
    else:
        url = params.get("url")
        if not url:
            return {
                "ok": False,
                "site": "x",
                "workflow": "read_post",
                "error": "url is required",
            }
        opened = browser_runtime.open_or_reuse_url(
            url,
            reuse_existing_tab=False,
            reuse_domain="x.com",
        )
        if not opened:
            return {
                "ok": False,
                "site": "x",
                "workflow": "read_post",
                "error": "failed to open page",
            }
        resolved_target_id = opened.get("targetId") or opened.get("id")
        wait_for_target_stable(browser_runtime, resolved_target_id)

    try:
        read_params = dict(params)
        read_params.pop("url", None)
        comment_limit = normalize_comment_limit(params.get("commentLimit"))
        read_result, comment_scroll_debug = _read_with_comment_scroll(
            read_service=read_service,
            browser_runtime=browser_runtime,
            resolved_target_id=resolved_target_id,
            read_params=read_params,
            timeout_seconds=timeout_seconds,
            comment_limit=comment_limit,
        )
        if not read_result:
            return {
                "ok": False,
                "site": "x",
                "workflow": "read_post",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "x",
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
                "site": "x",
                "workflow": "read_post",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "unexpected page type",
                "expectedPageType": "post",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }

        result = {
            "ok": bool(read_result.get("ok")),
            "site": "x",
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
                **(read_result.get("debug") or {}),
                "commentScroll": comment_scroll_debug,
            },
        }
        content = result.get("content") or {}
        post = content.get("post") if isinstance(content.get("post"), dict) else None
        if post and post.get("text"):
            post["text"] = normalize_image_tags(post["text"])
            content["primaryText"] = post["text"]
        elif content.get("primaryText"):
            content["primaryText"] = normalize_image_tags(content["primaryText"])
        result["content"] = content
        if opened is not None:
            result["debug"]["open"] = opened
        result["semantic"] = build_read_post_semantic("x", result, comment_limit=comment_limit)
        result["diagnostics"] = build_read_post_diagnostics("x", result)
        return result
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
