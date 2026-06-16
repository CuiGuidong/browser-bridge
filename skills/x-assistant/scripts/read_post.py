import json
import sys
import time

from bridge_client import workflow_run


def read_single_post(url):
    try:
        workflow_data = {}
        payload = {}
        content = ""
        for attempt in range(2):
            workflow_data = workflow_run(
                "x",
                "read_post",
                params={
                    "url": url,
                    "waitForReady": True,
                    "intervalSeconds": 1,
                    "maxChars": 100000,
                },
                timeout_seconds=90,
                timeout=100,
            )
            if "error" in workflow_data:
                if attempt == 1:
                    print(json.dumps({"ok": False, "error": workflow_data["error"]}))
                    return
                time.sleep(1.0)
                continue

            payload = workflow_data.get("data") or {}
            content = (((payload.get("content") or {}).get("primaryText")) or "").strip()
            if content:
                break
            if attempt == 0:
                time.sleep(1.0)

        if not content:
            print(json.dumps({
                "ok": False,
                "error": payload.get("error") or "No content found",
                "source": (payload.get("summary") or {}).get("source"),
            }))
            return

        print(json.dumps({
            "ok": True,
            "workflow": payload.get("workflow"),
            "source": (payload.get("summary") or {}).get("source"),
            "pageType": (payload.get("summary") or {}).get("pageType"),
            "data": payload,
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing URL parameter"}))
        sys.exit(1)
    read_single_post(sys.argv[1])
