from urllib.parse import quote


def _open_url(browser_runtime, url, target_id=None, reuse_domain=None):
    if target_id:
        opened = browser_runtime.navigate_tab(target_id, url)
        if not opened:
            return None
        return opened
    return browser_runtime.open_or_reuse_url(
        url,
        reuse_existing_tab=False,
        reuse_domain=reuse_domain,
    )


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


def run_url_read(
    site,
    workflow,
    kind,
    read_service,
    browser_runtime,
    target_id=None,
    params=None,
    timeout_seconds=20,
    reuse_domain=None,
):
    params = params or {}
    url = (params.get("url") or "").strip()
    if not url:
        return {
            "ok": False,
            "site": site,
            "workflow": workflow,
            "error": "url is required",
        }

    opened = _open_url(browser_runtime, url, target_id=target_id, reuse_domain=reuse_domain)
    if not opened:
        return {
            "ok": False,
            "site": site,
            "workflow": workflow,
            "error": "failed to open page",
        }
    resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
    _wait_for_target_stable(browser_runtime, resolved_target_id)

    try:
        read_params = dict(params)
        read_params.pop("url", None)
        read_result = read_service.site_read(
            site=site,
            kind=kind,
            params=read_params,
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        if not read_result:
            return {
                "ok": False,
                "site": site,
                "workflow": workflow,
                "targetId": None if not opened.get("reused") else resolved_target_id,
                "error": "site read failed",
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "site": site,
                "workflow": workflow,
                "targetId": None if not opened.get("reused") else resolved_target_id,
                "debug": {
                    "open": opened,
                    **(read_result.get("debug") or {}),
                },
            }
        return {
            "ok": True,
            "site": site,
            "workflow": workflow,
            "targetId": None if not opened.get("reused") else resolved_target_id,
            "summary": {
                "source": read_result.get("source"),
                "mode": read_result.get("mode"),
                "pageType": read_result.get("pageType"),
            },
            "items": (read_result.get("content") or {}).get("items") or [],
            "checkpoint": {},
            "page": read_result.get("page") or {},
            "signals": read_result.get("signals") or {},
            "content": read_result.get("content") or {},
            "debug": {
                "open": opened,
                **(read_result.get("debug") or {}),
            },
        }
    finally:
        if opened is not None and not opened.get("reused") and resolved_target_id:
            try:
                browser_runtime.close_tab(resolved_target_id)
            except Exception:
                pass


def run_search(
    site,
    search_url_template,
    read_service,
    browser_runtime,
    target_id=None,
    params=None,
    timeout_seconds=20,
    reuse_domain=None,
):
    params = params or {}
    keyword = (params.get("keyword") or params.get("query") or "").strip()
    if not keyword:
        return {
            "ok": False,
            "site": site,
            "workflow": "search",
            "error": "keyword is required",
        }
    url = search_url_template.format(keyword=quote(keyword))
    return run_url_read(
        site=site,
        workflow="search",
        kind="search",
        read_service=read_service,
        browser_runtime=browser_runtime,
        target_id=target_id,
        params={"url": url, "keyword": keyword},
        timeout_seconds=timeout_seconds,
        reuse_domain=reuse_domain,
    )


def run_account_status(
    site,
    home_url,
    read_service,
    browser_runtime,
    target_id=None,
    params=None,
    timeout_seconds=20,
    reuse_domain=None,
):
    params = params or {}
    url = (params.get("url") or home_url or "").strip()
    return run_url_read(
        site=site,
        workflow="account_status",
        kind="account_status",
        read_service=read_service,
        browser_runtime=browser_runtime,
        target_id=target_id,
        params={"url": url},
        timeout_seconds=timeout_seconds,
        reuse_domain=reuse_domain,
    )
