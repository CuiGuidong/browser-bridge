import json
import sys

from bridge_client import open_and_activate, site_action


def add_bookmark(url):
    target_id, _ = open_and_activate(url, reuse_domain="x.com", reuse_existing_tab=True, timeout=40)
    if not target_id:
        print(json.dumps({"ok": False, "error": "Failed to open post page"}))
        return

    action = site_action(
        "x",
        "add_bookmark",
        params={"url": url},
        target_id=target_id,
        timeout_seconds=25,
        timeout=35,
    )
    payload = action.get("data") or {}
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
