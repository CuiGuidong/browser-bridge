import json
import sys

from bridge_client import workflow_run
from zhihu_targets import extract_first_url, is_supported_zhihu_url


def read_profile(target):
    raw = (target or "").strip()
    url = extract_first_url(raw) if raw else None
    if not url or not is_supported_zhihu_url(url):
        print(json.dumps({"ok": False, "error": f"Unsupported zhihu URL: {raw}"}))
        return

    workflow_data = workflow_run(
        "zhihu",
        "read_profile_metrics",
        params={"url": url, "waitForReady": True, "intervalSeconds": 1},
        timeout_seconds=90,
        timeout=100,
    )
    if "error" in workflow_data:
        print(json.dumps({"ok": False, "error": workflow_data["error"]}))
        return

    payload = workflow_data.get("data") or {}
    content = payload.get("content") or {}
    print(json.dumps({
        "ok": bool(payload.get("ok")),
        "workflow": payload.get("workflow"),
        "source": (payload.get("summary") or {}).get("source"),
        "pageType": (payload.get("summary") or {}).get("pageType"),
        "profile": {
            "url": content.get("url") or url,
            "name": content.get("name"),
            "bio": content.get("bio"),
            "metrics": content.get("metrics") or {},
            "recentPosts": content.get("recentPosts") or [],
        },
        "data": payload,
    }, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing zhihu profile URL"}))
        sys.exit(1)
    read_profile(sys.argv[1])
