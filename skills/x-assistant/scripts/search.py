import json
import sys
from pathlib import Path

from bridge_client import workflow_run
from x_item_utils import dedup_and_score


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def search_x(keyword):
    try:
        workflow_data = workflow_run(
            "x",
            "search",
            params={"keyword": keyword, "waitForReady": True, "intervalSeconds": 1},
            timeout_seconds=90,
            timeout=100,
        )
        payload = workflow_data.get("data") or {}
        timeline = (((payload.get("content") or {}).get("timeline")) or [])
        summary = payload.get("summary") or {}
        source = summary.get("source")

        if not timeline:
            fallback = (((payload.get("content") or {}).get("primaryText")) or "").strip()
            if fallback:
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

            print(json.dumps({"ok": False, "error": "No timeline data found.", "raw_debug": workflow_data}))
            return

        deduped = dedup_and_score(timeline)
        print(json.dumps({
            "ok": True,
            "keyword": keyword,
            "source": source,
            "pageType": summary.get("pageType"),
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
