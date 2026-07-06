import argparse
import json
import sys

from bridge_client import workflow_run
from zhihu_targets import classify_read_post_input


def _strip_media(semantic):
    clean_sem = dict(semantic)
    if "contentItem" in clean_sem and isinstance(clean_sem["contentItem"], dict):
        clean_sem["contentItem"] = dict(clean_sem["contentItem"])
        clean_sem["contentItem"].pop("media", None)
    if "thread" in clean_sem and isinstance(clean_sem["thread"], dict):
        clean_sem["thread"] = dict(clean_sem["thread"])
        if "items" in clean_sem["thread"] and isinstance(clean_sem["thread"]["items"], list):
            new_items = []
            for item in clean_sem["thread"]["items"]:
                if isinstance(item, dict):
                    c_item = dict(item)
                    c_item.pop("media", None)
                    new_items.append(c_item)
                else:
                    new_items.append(item)
            clean_sem["thread"]["items"] = new_items
    if "comments" in clean_sem and isinstance(clean_sem["comments"], dict):
        clean_sem["comments"] = dict(clean_sem["comments"])
        if "items" in clean_sem["comments"] and isinstance(clean_sem["comments"]["items"], list):
            new_items = []
            for item in clean_sem["comments"]["items"]:
                if isinstance(item, dict):
                    c_item = dict(item)
                    c_item.pop("media", None)
                    new_items.append(c_item)
                else:
                    new_items.append(item)
            clean_sem["comments"]["items"] = new_items
    return clean_sem


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
    else:
        semantic = _strip_media(semantic)
    print(json.dumps(semantic, ensure_ascii=False))


def read_post(target, mode="default", comment_limit=20):
    normalized = classify_read_post_input(target)
    if not normalized.get("ok"):
        print(json.dumps({"ok": False, "error": normalized.get("error")}))
        return

    workflow_data = workflow_run(
        "zhihu",
        "read_post",
        params={
            "url": normalized.get("url"),
            "waitForReady": True,
            "intervalSeconds": 1,
            "commentLimit": comment_limit,
        },
        timeout_seconds=90,
        timeout=100,
    )
    if "error" in workflow_data:
        print(json.dumps({"ok": False, "error": workflow_data["error"]}))
        return

    payload = workflow_data.get("data") or {}
    _print_payload(payload, mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read a Zhihu post through Browser Bridge")
    parser.add_argument("target")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--comment-limit", type=int, default=20)
    args = parser.parse_args()
    mode = "raw" if args.raw else "debug" if args.debug else "default"
    read_post(args.target, mode=mode, comment_limit=max(0, min(args.comment_limit, 100)))
