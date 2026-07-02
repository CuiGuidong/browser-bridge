import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bridge_client import workflow_run  # noqa: E402


VALID_INTERESTS = {"wish", "do", "collect"}


def set_interest(url, interest, raw=False):
    if interest not in VALID_INTERESTS:
        return {
            "ok": False,
            "site": "douban",
            "action": "set_interest",
            "error": "invalid_interest",
        }
    workflow_data = workflow_run(
        "douban",
        "set_interest",
        params={
            "url": url,
            "interest": interest,
        },
        timeout_seconds=90,
        timeout=100,
    )
    if raw:
        return workflow_data
    payload = workflow_data.get("data") or workflow_data
    return {
        "ok": bool(payload.get("ok")),
        "site": "douban",
        "action": "set_interest",
        "changed": payload.get("changed"),
        "verified": payload.get("verified"),
        "before": payload.get("before"),
        "after": payload.get("after"),
        "page": payload.get("page"),
        "error": payload.get("error"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set Douban subject interest through Browser Bridge")
    parser.add_argument("url")
    parser.add_argument("interest", choices=sorted(VALID_INTERESTS))
    parser.add_argument("--raw", action="store_true")
    args = parser.parse_args()
    print(json.dumps(set_interest(args.url, args.interest, raw=args.raw), ensure_ascii=False))
