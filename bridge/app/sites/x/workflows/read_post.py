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
            reuse_existing_tab=True,
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
            "targetId": resolved_target_id,
            "error": "site read failed",
        }

    result = {
        "ok": bool(read_result.get("ok")),
        "site": "x",
        "workflow": "read_post",
        "targetId": resolved_target_id,
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
        "debug": read_result.get("debug") or {},
    }
    if opened is not None:
        result["debug"]["open"] = opened
    return result
