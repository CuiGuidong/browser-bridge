import json
import sys
from pathlib import Path

from bridge_client import workflow_run
from x_item_utils import dedup_and_score


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def list_bookmarks(limit=20):
    workflow_data = workflow_run(
        "x",
        "list_bookmarks",
        params={"waitForReady": True, "intervalSeconds": 1},
        timeout_seconds=25,
        timeout=35,
    )
    payload = workflow_data.get("data") or {}
    timeline = ((payload.get("content") or {}).get("timeline") or [])
    deduped_items = dedup_and_score(timeline)
    items = deduped_items[:limit]

    print(json.dumps({
        "ok": bool(payload.get("ok")),
        "source": (payload.get("summary") or {}).get("source"),
        "pageType": (payload.get("summary") or {}).get("pageType"),
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
