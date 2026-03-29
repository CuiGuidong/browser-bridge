import json
import sys

from bridge_client import workflow_run


def add_bookmark(url):
    workflow_data = workflow_run(
        "x",
        "add_bookmark",
        params={"url": url},
        timeout_seconds=25,
        timeout=35,
    )
    payload = workflow_data.get("data") or {}
    print(json.dumps({
        "ok": bool(payload.get("ok")),
        "url": url,
        "source": payload.get("source"),
        "changed": payload.get("changed"),
        "verified": payload.get("verified"),
        "before": payload.get("before"),
        "after": ((payload.get("debug") or {}).get("verify") or {}).get("after"),
        "data": payload,
    }, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing post URL"}))
        sys.exit(1)
    add_bookmark(sys.argv[1])
