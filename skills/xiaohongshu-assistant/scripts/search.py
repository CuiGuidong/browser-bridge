import json
import sys

from bridge_client import workflow_run


def search_xiaohongshu(keyword, limit=20):
    workflow_data = workflow_run(
        "xiaohongshu",
        "search",
        params={
            "keyword": keyword,
            "waitForReady": True,
            "intervalSeconds": 1,
        },
        timeout_seconds=90,
        timeout=100,
    )
    if "error" in workflow_data:
        print(json.dumps({"ok": False, "error": workflow_data["error"]}))
        return

    payload = workflow_data.get("data") or {}
    items = ((payload.get("content") or {}).get("items") or [])[:limit]
    print(json.dumps({
        "ok": bool(payload.get("ok")),
        "keyword": keyword,
        "workflow": payload.get("workflow"),
        "source": (payload.get("summary") or {}).get("source"),
        "pageType": (payload.get("summary") or {}).get("pageType"),
        "results": {
            "count": len(items),
            "items": items,
        },
        "data": items,
    }, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing keyword"}))
        sys.exit(1)
    limit = 20
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except Exception:
            limit = 20
    limit = max(1, min(limit, 100))
    search_xiaohongshu(sys.argv[1], limit=limit)
