from .common import close_temporary_tab, response_target_id, wait_for_target_stable
from ....media.image_cache import process_and_spawn_downloads


def _infer_page_type(read_result):
    page = read_result.get("page") or {}
    url = page.get("url") or ""
    signals = read_result.get("signals") or {}
    if "/status/" in url:
        return "post"
    if signals.get("isTimeline"):
        return "timeline"
    return None


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
        read_result = read_service.site_read(
            site="x",
            kind="read_post",
            params=read_params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
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
            "debug": read_result.get("debug") or {},
        }
        content = result.get("content") or {}
        post = content.get("post") if isinstance(content.get("post"), dict) else None
        if post and post.get("text"):
            post["text"] = process_and_spawn_downloads(post["text"])
            content["primaryText"] = post["text"]
        elif content.get("primaryText"):
            content["primaryText"] = process_and_spawn_downloads(content["primaryText"])
        result["content"] = content
        if opened is not None:
            result["debug"]["open"] = opened
        return result
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
