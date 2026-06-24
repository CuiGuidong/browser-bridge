import argparse
import json
import sys
import time

from bridge_client import workflow_run


def _print_payload(payload, mode):
    if mode == "raw":
        print(json.dumps(payload, ensure_ascii=False))
        return

    semantic = payload.get("semantic")
    if not semantic:
        print(json.dumps({
            "ok": False,
            "error": "semantic payload missing",
            "workflow": payload.get("workflow"),
        }, ensure_ascii=False))
        return

    if mode == "debug":
        semantic = dict(semantic)
        semantic["diagnostics"] = payload.get("diagnostics") or {}
    print(json.dumps(semantic, ensure_ascii=False))


def read_single_post(url, mode="default", comment_limit=20):
    try:
        payload = {}
        for attempt in range(2):
            workflow_data = workflow_run(
                "x",
                "read_post",
                params={
                    "url": url,
                    "waitForReady": True,
                    "intervalSeconds": 1,
                    "maxChars": 100000,
                    "commentLimit": comment_limit,
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
            semantic = payload.get("semantic") or {}
            if mode == "raw" or semantic.get("ok"):
                break
            if attempt == 0:
                time.sleep(1.0)

        if mode != "raw" and not (payload.get("semantic") or {}).get("ok"):
            print(json.dumps({
                "ok": False,
                "error": payload.get("error") or "semantic payload missing",
                "source": (payload.get("summary") or {}).get("source"),
            }))
            return

        _print_payload(payload, mode)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read an X post through Browser Bridge")
    parser.add_argument("url")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--comment-limit", type=int, default=20)
    args = parser.parse_args()
    mode = "raw" if args.raw else "debug" if args.debug else "default"
    read_single_post(args.url, mode=mode, comment_limit=max(0, min(args.comment_limit, 100)))
