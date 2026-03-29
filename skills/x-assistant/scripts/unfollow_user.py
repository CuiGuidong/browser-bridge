import json
import sys

from bridge_client import workflow_run
from x_targets import build_profile_url, extract_handle


def unfollow_user(target):
    handle = extract_handle(target)
    profile_url = build_profile_url(handle)
    if not handle or not profile_url:
        print(json.dumps({"ok": False, "error": "Invalid handle or profile URL"}))
        return

    workflow_data = workflow_run(
        "x",
        "unfollow_user",
        params={"handle": handle},
        timeout_seconds=25,
        timeout=35,
    )
    payload = workflow_data.get("data") or {}
    print(json.dumps({
        "ok": bool(payload.get("ok")),
        "handle": handle,
        "url": profile_url,
        "source": payload.get("source"),
        "changed": payload.get("changed"),
        "verified": payload.get("verified"),
        "before": payload.get("before"),
        "after": ((payload.get("debug") or {}).get("verify") or {}).get("after"),
        "data": payload,
    }, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing handle or profile URL"}))
        sys.exit(1)
    unfollow_user(sys.argv[1])
