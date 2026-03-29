def open_x_page(browser_runtime, url=None, target_id=None):
    opened = None
    resolved_target_id = target_id
    if resolved_target_id:
        if url:
            opened = browser_runtime.navigate_tab(resolved_target_id, url)
            if not opened:
                return None, None
            resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
        else:
            browser_runtime.activate_tab(resolved_target_id)
        return resolved_target_id, opened
    if not url:
        return None, None
    opened = browser_runtime.open_or_reuse_url(
        url,
        reuse_existing_tab=False,
        reuse_domain="x.com",
    )
    if not opened:
        return None, None
    resolved_target_id = opened.get("targetId") or opened.get("id")
    return resolved_target_id, opened


def response_target_id(opened, resolved_target_id):
    if opened is not None and not opened.get("reused"):
        return None
    return resolved_target_id


def close_temporary_tab(browser_runtime, opened, resolved_target_id):
    if opened is not None and not opened.get("reused") and resolved_target_id:
        try:
            browser_runtime.close_tab(resolved_target_id)
        except Exception:
            pass
