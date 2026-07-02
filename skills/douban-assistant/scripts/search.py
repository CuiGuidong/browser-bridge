import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bridge_client import workflow_run  # noqa: E402


def _clamp_count(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 10
    return max(1, min(count, 50))


def search(keyword, count=10, raw=False):
    count = _clamp_count(count)
    workflow_data = workflow_run(
        "douban",
        "search",
        params={
            "keyword": keyword,
            "count": count,
        },
        timeout_seconds=90,
        timeout=100,
    )
    if raw:
        return workflow_data
    payload = workflow_data.get("data") or workflow_data
    content = payload.get("content") or {}
    return {
        "ok": bool(payload.get("ok")),
        "site": "douban",
        "query": keyword,
        "items": (content.get("items") or payload.get("items") or [])[:count],
        "filteredItems": content.get("filteredItems") or [],
        "error": payload.get("error"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search Douban subjects through Browser Bridge")
    parser.add_argument("keyword")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--raw", action="store_true")
    args = parser.parse_args()
    print(json.dumps(search(args.keyword, count=args.count, raw=args.raw), ensure_ascii=False))
