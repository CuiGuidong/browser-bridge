import json
import sys
import urllib.parse

from bridge_client import open_and_activate, site_read
from image_utils import process_and_spawn_downloads
from x_item_utils import dedup_and_score


def search_x(keyword):
    search_url = f"https://x.com/search?q={urllib.parse.quote(keyword)}&src=typed_query"

    try:
        target_id, _ = open_and_activate(
            search_url,
            reuse_domain="x.com",
            reuse_existing_tab=True,
            timeout=40,
            expected_url_substring="/search",
        )
        if not target_id:
            print(json.dumps({"ok": False, "error": "Failed to open search page"}))
            return
        read_data = site_read(
            "x",
            "read_timeline",
            params={
                "waitForReady": True,
                "intervalSeconds": 1,
                "maxChars": 100000,
            },
            target_id=target_id,
            timeout_seconds=90,
            timeout=100,
        )
        timeline = (((read_data.get("data") or {}).get("content") or {}).get("timeline") or [])
        source = (read_data.get("data") or {}).get("source")

        if not timeline:
            fallback = (((read_data.get("data") or {}).get("content") or {}).get("primaryText") or "").strip()
            if fallback:
                fallback = process_and_spawn_downloads(fallback)
                print(json.dumps({
                    "ok": True,
                    "keyword": keyword,
                    "warning": "Failed to parse structured timeline, returned raw text",
                    "source": source,
                    "results": {
                        "raw_count": 1,
                        "deduped_count": 1,
                        "items": [{"text": fallback, "analysis": {"is_worth_reading": True, "score": 50}}],
                    },
                    "data": [{"text": fallback}],
                }))
                return

            print(json.dumps({"ok": False, "error": "No timeline data found.", "raw_debug": read_data}))
            return

        deduped = dedup_and_score(timeline)
        deduped = process_and_spawn_downloads(deduped)
        print(json.dumps({
            "ok": True,
            "keyword": keyword,
            "source": source,
            "results": {
                "raw_count": len(timeline),
                "deduped_count": len(deduped),
                "items": deduped,
            },
            "data": deduped,
        }))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing keyword parameter"}))
        sys.exit(1)
    search_x(sys.argv[1])
