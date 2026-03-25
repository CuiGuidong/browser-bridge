import json
import sys

from bridge_client import open_and_activate, site_read
from image_utils import process_and_spawn_downloads
from x_item_utils import dedup_and_score


def list_bookmarks(limit=20):
    target_id, _ = open_and_activate(
        "https://x.com/i/bookmarks",
        reuse_domain="x.com",
        reuse_existing_tab=True,
        timeout=40,
        expected_url_substring="/i/bookmarks",
    )
    if not target_id:
        print(json.dumps({"ok": False, "error": "Failed to open bookmarks page"}))
        return
    read_data = site_read(
        "x",
        "list_bookmarks",
        target_id=target_id,
        params={"waitForReady": True, "intervalSeconds": 1, "maxChars": 100000},
        timeout_seconds=25,
        timeout=35,
    )
    payload = read_data.get("data") or {}
    timeline = ((payload.get("content") or {}).get("timeline") or [])
    deduped_items = dedup_and_score(timeline)
    items = deduped_items[:limit]
    deduped_items = process_and_spawn_downloads(deduped_items)
    items = process_and_spawn_downloads(items)

    print(json.dumps({
        "ok": bool(payload.get("ok")),
        "source": payload.get("source"),
        "pageType": payload.get("pageType"),
        "results": {
            "raw_count": len(timeline),
            "deduped_count": len(deduped_items),
            "returned_count": len(items),
            "items": items,
        },
        "data": items,
    }, ensure_ascii=False))


if __name__ == "__main__":
    limit = 20
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except Exception:
            limit = 20
    limit = max(1, min(limit, 100))
    list_bookmarks(limit=limit)
