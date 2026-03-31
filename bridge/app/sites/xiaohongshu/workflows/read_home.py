def _wait_for_target_stable(browser_runtime, target_id, timeout_seconds=8, interval_seconds=0.4):
    if not target_id:
        return None
    try:
        return browser_runtime.wait_for_page(
            target_id=target_id,
            timeout_seconds=timeout_seconds,
            interval_seconds=interval_seconds,
        )
    except Exception:
        return None


def run(read_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    opened = None
    resolved_target_id = target_id
    if resolved_target_id:
        opened = browser_runtime.navigate_tab(resolved_target_id, "https://www.xiaohongshu.com/explore")
        if not opened:
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "read_home",
                "error": "failed to open page",
            }
        resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
    else:
        opened = browser_runtime.open_or_reuse_url(
            "https://www.xiaohongshu.com/explore",
            reuse_existing_tab=False,
            reuse_domain="xiaohongshu.com",
        )
        if not opened:
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "read_home",
                "error": "failed to open page",
            }
        resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
    _wait_for_target_stable(browser_runtime, resolved_target_id)
    try:
        read_result = read_service.site_read(
            site="xiaohongshu",
            kind="read_home",
            params=params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not read_result:
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "read_home",
                "targetId": None if not opened.get("reused") else resolved_target_id,
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": "xiaohongshu",
                "workflow": "read_home",
                "targetId": None if opened is not None and not opened.get("reused") else resolved_target_id,
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        actual_page_type = ((read_result.get("signals") or {}).get("pageType"))
        if actual_page_type != "home":
            return {
                "ok": False,
                "site": "xiaohongshu",
                "workflow": "read_home",
                "targetId": None if not opened.get("reused") else resolved_target_id,
                "error": "unexpected page type",
                "expectedPageType": "home",
                "actualPageType": actual_page_type,
                "page": read_result.get("page") or {},
            }

        result = {
            "ok": bool(read_result.get("ok")),
            "site": "xiaohongshu",
            "workflow": "read_home",
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
