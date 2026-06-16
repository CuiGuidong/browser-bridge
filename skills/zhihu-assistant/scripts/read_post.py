import json
import sys

from bridge_client import workflow_run
from zhihu_targets import classify_read_post_input


def read_post(target):
    normalized = classify_read_post_input(target)
    if not normalized.get("ok"):
        print(json.dumps({"ok": False, "error": normalized.get("error")}))
        return

    workflow_data = workflow_run(
        "zhihu",
        "read_post",
        params={"url": normalized.get("url"), "waitForReady": True, "intervalSeconds": 1},
        timeout_seconds=90,
        timeout=100,
    )
    if "error" in workflow_data:
        print(json.dumps({"ok": False, "error": workflow_data["error"]}))
        return

    payload = workflow_data.get("data") or {}
    print(json.dumps({
        "ok": bool(payload.get("ok")),
        "workflow": payload.get("workflow"),
        "source": (payload.get("summary") or {}).get("source"),
        "pageType": (payload.get("summary") or {}).get("pageType"),
        "data": payload,
    }, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing zhihu URL"}))
        sys.exit(1)
    read_post(sys.argv[1])
