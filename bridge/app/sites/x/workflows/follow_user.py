from .common import close_temporary_tab, open_x_page, response_target_id


def run(action_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    handle = ((params or {}).get("handle") or "").strip().lstrip("@")
    if not handle:
        return {
            "ok": False,
            "site": "x",
            "workflow": "follow_user",
            "error": "handle is required",
        }
    resolved_target_id, opened = open_x_page(
        browser_runtime,
        url=f"https://x.com/{handle}",
        target_id=target_id,
    )
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "x",
            "workflow": "follow_user",
            "error": "failed to open page",
        }
    try:
        action_result = action_service.site_action(
            "x",
            "follow_user",
            params={"handle": handle},
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        action_result["workflow"] = "follow_user"
        action_result["targetId"] = response_target_id(opened, resolved_target_id)
        action_result["debug"] = {
            "open": opened,
            **(action_result.get("debug") or {}),
        }
        return action_result
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
