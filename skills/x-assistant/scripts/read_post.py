import json
import sys
import time

from bridge_client import workflow_run
from image_utils import process_and_spawn_downloads
from x_targets import build_author_from_page_url, extract_status_id


def read_single_post(url):
    try:
        workflow_data = {}
        payload = {}
        content = ""
        canonical_url = url
        author = None
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
            page = payload.get("page") or {}
            canonical_url = page.get("url") or url
            author = build_author_from_page_url(canonical_url)
            if content:
                break
            if attempt == 0:
                time.sleep(1.0)

        if not content:
            print(json.dumps({
                "ok": False,
                "error": payload.get("error") or "No content found",
                "source": payload.get("source"),
            }))
            return

        content = process_and_spawn_downloads(content)

        print(json.dumps({
            "ok": True,
            "url": url,
            "canonicalUrl": canonical_url,
            "source": payload.get("source"),
            "workflow": payload.get("workflow"),
            "author": author,
            "post": {
                "url": canonical_url,
                "statusId": extract_status_id(canonical_url),
            },
            "results": {
                "text": content,
                "analysis": {
                    "length": len(content),
                    "is_worth_reading": len(content) > 10,
                },
            },
            "data": content,
        }))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing URL parameter"}))
        sys.exit(1)
    read_single_post(sys.argv[1])
