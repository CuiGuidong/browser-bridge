import json
import os
import urllib.request
from pathlib import Path


def _load_env_file(path):
    values = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                if key:
                    values[key] = value
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return values


def _resolve_bridge_url():
    if os.environ.get("BRIDGE_URL"):
        return os.environ["BRIDGE_URL"].rstrip("/")

    script_dir = Path(__file__).resolve().parent
    local_env = _load_env_file(script_dir / ".env")
    if local_env.get("BRIDGE_URL"):
        return local_env["BRIDGE_URL"].rstrip("/")

    return "http://127.0.0.1:17777"


BRIDGE_URL = _resolve_bridge_url()

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
