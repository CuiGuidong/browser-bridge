import json
import sys

from bridge_client import workflow_run


def prepare_publish(title, content, image_paths):
    workflow_data = workflow_run(
        "xiaohongshu",
        "prepare_publish_post",
        params={
            "title": title,
            "content": content,
            "imagePaths": image_paths,
        },
        timeout_seconds=120,
        timeout=130,
    )
    if "error" in workflow_data:
        print(json.dumps({"ok": False, "error": workflow_data["error"]}, ensure_ascii=False))
        return

    payload = workflow_data.get("data") or {}
    content_state = payload.get("content") or {}
    print(json.dumps({
        "ok": bool(payload.get("ok")),
        "workflow": payload.get("workflow"),
        "targetId": payload.get("targetId"),
        "summary": payload.get("summary") or {},
        "checkpoint": payload.get("checkpoint") or {},
        "state": {
            "pageType": content_state.get("pageType"),
            "activeTab": content_state.get("activeTab"),
            "titleLength": ((content_state.get("titleInput") or {}).get("length")),
            "contentLength": ((content_state.get("contentEditor") or {}).get("length")),
            "publishButton": content_state.get("publishButton") or {},
        },
        "data": payload,
    }, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(json.dumps({
            "ok": False,
            "error": "Usage: prepare_publish.py <title> <content> <image_path> [more_image_paths...]",
        }, ensure_ascii=False))
        sys.exit(1)
    prepare_publish(
        title=sys.argv[1],
        content=sys.argv[2],
        image_paths=sys.argv[3:],
    )
