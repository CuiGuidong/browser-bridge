import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bridge_client import workflow_run  # noqa: E402


def _clamp_comment_limit(value):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = 20
    return max(0, min(limit, 100))


def format_subject_result(workflow_payload, mode="default", comment_limit=20):
    if mode == "raw":
        return workflow_payload

    payload = workflow_payload or {}
    content = payload.get("content") or {}
    result = {
        "ok": bool(payload.get("ok")),
        "site": "douban",
        "schemaVersion": "douban.subject.v1",
        "subject": content.get("subject") or {},
        "rating": content.get("rating") or {},
        "interestStats": content.get("interestStats") or {},
        "viewerInterest": content.get("viewerInterest") or {},
        "comments": {
            "items": (content.get("comments") or [])[:comment_limit] if comment_limit else [],
            "limit": comment_limit,
            "total": content.get("commentsTotal"),
            "hasMore": content.get("commentsHasMore"),
        },
    }
    if not result["ok"]:
        result["error"] = payload.get("error") or "read_post failed"

    if mode == "debug":
        result["diagnostics"] = payload.get("diagnostics") or {}
        result["page"] = payload.get("page") or {}
        result["signals"] = payload.get("signals") or {}
    return result


def read_post(url, mode="default", comment_limit=20):
    comment_limit = _clamp_comment_limit(comment_limit)
    workflow_data = workflow_run(
        "douban",
        "read_post",
        params={
            "url": url,
            "commentLimit": comment_limit,
        },
        timeout_seconds=90,
        timeout=100,
    )
    if "error" in workflow_data and "data" not in workflow_data:
        return {"ok": False, "site": "douban", "error": workflow_data["error"]}
    payload = workflow_data.get("data") or workflow_data
    return format_subject_result(payload, mode=mode, comment_limit=comment_limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read a Douban subject through Browser Bridge")
    parser.add_argument("url")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--comment-limit", type=int, default=20)
    args = parser.parse_args()
    output_mode = "raw" if args.raw else "debug" if args.debug else "default"
    print(json.dumps(read_post(args.url, mode=output_mode, comment_limit=args.comment_limit), ensure_ascii=False))
