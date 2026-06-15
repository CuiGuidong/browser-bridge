import json
import os
import urllib.request


BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://127.0.0.1:17777")

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
