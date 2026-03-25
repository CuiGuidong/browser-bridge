import json
import time
import urllib.request
import urllib.parse


BRIDGE_URL = "http://127.0.0.1:17777"

_proxy_handler = urllib.request.ProxyHandler({})
_opener = urllib.request.build_opener(_proxy_handler)


def post_json(path, payload, timeout=90):
    try:
        req = urllib.request.Request(
            f"{BRIDGE_URL}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _opener.open(req, timeout=timeout) as res:
            return json.loads(res.read())
    except Exception as e:
        return {"error": str(e)}


def get_json(path, timeout=90):
    try:
        req = urllib.request.Request(f"{BRIDGE_URL}{path}", method="GET")
        with _opener.open(req, timeout=timeout) as res:
            return json.loads(res.read())
    except Exception as e:
        return {"error": str(e)}


def open_url(url, reuse_domain="x.com", reuse_existing_tab=True, timeout=40):
    return post_json(
        "/open",
        {
            "url": url,
            "reuseExistingTab": reuse_existing_tab,
            "reuseDomain": reuse_domain,
        },
        timeout=timeout,
    )


def activate(target_id, timeout=30):
    return post_json("/activate", {"targetId": target_id}, timeout=timeout)


def page_info(target_id, timeout=30):
    encoded = urllib.parse.quote(str(target_id), safe="")
    return get_json(f"/page-info?targetId={encoded}", timeout=timeout)


def wait_for_target_page(target_id, expected_url_substring=None, attempts=10, interval_seconds=0.5, timeout=30):
    last = {}
    for _ in range(max(attempts, 1)):
        last = page_info(target_id, timeout=timeout)
        data = last.get("data") or {}
        page_url = data.get("url") or ""
        if not expected_url_substring or expected_url_substring in page_url:
            return last
        time.sleep(interval_seconds)
    return last


def open_and_activate(
    url,
    reuse_domain="x.com",
    reuse_existing_tab=True,
    timeout=40,
    settle_seconds=1.5,
    expected_url_substring=None,
):
    open_data = open_url(
        url,
        reuse_domain=reuse_domain,
        reuse_existing_tab=reuse_existing_tab,
        timeout=timeout,
    )
    target_id = open_data.get("data", {}).get("id")
    if not target_id:
        return None, open_data
    activate(target_id, timeout=30)
    wait_for_target_page(
        target_id,
        expected_url_substring=expected_url_substring,
        attempts=max(1, int(max(settle_seconds, 1.0) / 0.5)) + 2,
        interval_seconds=0.5,
        timeout=30,
    )
    time.sleep(settle_seconds)
    return target_id, open_data


def workflow_run(site, workflow, params=None, target_id=None, timeout_seconds=90, timeout=100):
    payload = {
        "site": site,
        "workflow": workflow,
        "params": params or {},
        "timeoutSeconds": timeout_seconds,
    }
    if target_id:
        payload["targetId"] = target_id
    return post_json("/workflow/run", payload, timeout=timeout)


def site_read(site, kind, params=None, target_id=None, timeout_seconds=90, timeout=100):
    payload = {
        "site": site,
        "kind": kind,
        "params": params or {},
        "timeoutSeconds": timeout_seconds,
    }
    if target_id:
        payload["targetId"] = target_id
    return post_json("/site/read", payload, timeout=timeout)


def site_action(site, kind, params=None, target_id=None, timeout_seconds=30, timeout=40):
    payload = {
        "site": site,
        "kind": kind,
        "params": params or {},
        "timeoutSeconds": timeout_seconds,
    }
    if target_id:
        payload["targetId"] = target_id
    return post_json("/site/action", payload, timeout=timeout)
