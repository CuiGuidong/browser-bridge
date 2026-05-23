import json

from bridge_client import workflow_run


def account_status():
    workflow_data = workflow_run(
        "zhihu",
        "account_status",
        params={"waitForReady": True, "intervalSeconds": 1},
        timeout_seconds=30,
        timeout=40,
    )
    if "error" in workflow_data:
        print(json.dumps({"ok": False, "error": workflow_data["error"]}))
        return

    payload = workflow_data.get("data") or {}
    print(json.dumps({
        "ok": bool(payload.get("ok")),
        "workflow": payload.get("workflow"),
        "site": "zhihu",
        "loggedIn": (payload.get("summary") or {}).get("loggedIn"),
        "data": payload,
    }, ensure_ascii=False))


if __name__ == "__main__":
    account_status()
