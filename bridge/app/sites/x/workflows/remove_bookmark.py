from .common import close_temporary_tab, open_x_page, response_target_id


def run(action_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    url = (params or {}).get("url")
    if not url:
        return {
            "ok": False,
            "site": "x",
            "workflow": "remove_bookmark",
            "error": "url is required",
        }
    resolved_target_id, opened = open_x_page(
        browser_runtime,
        url="https://x.com/i/bookmarks",
        target_id=target_id,
    )
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "x",
            "workflow": "remove_bookmark",
            "error": "failed to open page",
        }
    try:
        action_result = action_service.site_action(
            "x",
            "remove_bookmark",
            params={"url": url},
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        action_result["workflow"] = "remove_bookmark"
        action_result["targetId"] = response_target_id(opened, resolved_target_id)
        action_result["debug"] = {
            "open": opened,
            **(action_result.get("debug") or {}),
        }
        return action_result
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
