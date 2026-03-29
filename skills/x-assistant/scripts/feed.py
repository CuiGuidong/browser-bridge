import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from bridge_client import workflow_run
from x_item_utils import dedup_and_score


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def _normalize_feed_type(feed_type):
    val = (feed_type or "").strip().lower()
    if val in ["following", "正在关注", "follow", "关注"]:
        return "following"
    if val in ["for_you", "for-you", "for you", "为你推荐", "推荐", "foryou"]:
        return "for_you"
    if val in ["both", "all", "全部", "双流", "双"]:
        return "both"
    return "for_you"


def _format_output(feed_type_raw, feed_type_normalized, target_id, result, target_count, continuous):
    now_iso = datetime.now(timezone.utc).isoformat()
    summary = result.get("summary") or {}
    signals = result.get("signals", {})
    raw_items = ((result.get("content") or {}).get("timeline")) or []
    deduped_items = dedup_and_score(raw_items)
    items = deduped_items if continuous else deduped_items[:target_count]
    warning = None
    if signals.get("feedMode") != feed_type_normalized:
        warning = f"requested {feed_type_normalized}, got {signals.get('feedMode')}"

    return {
        "ok": True,
        "warning": warning,
        "request": {
            "feedTypeRaw": feed_type_raw,
            "feedTypeNormalized": feed_type_normalized,
            "requestedAt": now_iso,
            "targetCount": target_count,
            "continuous": continuous,
        },
        "feed": {
            "mode": signals.get("feedMode"),
            "activeTabText": signals.get("activeFeedTabText"),
            "availableTabs": signals.get("feedTabTexts") or [],
        },
        "results": {
            "targetId": target_id,
            "source": summary.get("source"),
            "pageType": summary.get("pageType"),
            "raw_count": len(raw_items),
            "deduped_count": len(deduped_items),
            "returned_count": len(items),
            "scrollRounds": ((result.get("debug") or {}).get("scrollRounds")),
            "items": items,
        },
        "data": items,
    }


def read_home_feed(feed_type="both", target_count=20, continuous=False):
    try:
        normalized = _normalize_feed_type(feed_type)
        if normalized == "both":
            for_you_data = workflow_run(
                "x",
                "read_home",
                params={
                    "mode": "for_you",
                    "targetCount": target_count,
                    "continuous": continuous,
                },
                timeout_seconds=90,
                timeout=100,
            )
            following_data = workflow_run(
                "x",
                "read_home",
                params={
                    "mode": "following",
                    "targetCount": target_count,
                    "continuous": continuous,
                },
                timeout_seconds=90,
                timeout=100,
            )
            fy_payload = for_you_data.get("data") or {}
            fl_payload = following_data.get("data") or {}
            now_iso = datetime.now(timezone.utc).isoformat()
            fy_formatted = _format_output("For you", "for_you", fy_payload.get("targetId"), fy_payload, target_count, continuous)
            fl_formatted = _format_output("following", "following", fl_payload.get("targetId"), fl_payload, target_count, continuous)
            payload = {
                "ok": True,
                "request": {
                    "feedTypeRaw": feed_type,
                    "feedTypeNormalized": "both",
                    "requestedAt": now_iso,
                    "targetCount": target_count,
                    "continuous": continuous,
                },
                "feeds": {
                    "for_you": fy_formatted,
                    "following": fl_formatted,
                },
            }
            payload["data"] = payload["feeds"]["for_you"]["results"]["items"]
            print(json.dumps(payload, ensure_ascii=False))
            return

        workflow_data = workflow_run(
            "x",
            "read_home",
            params={
                "mode": normalized,
                "targetCount": target_count,
                "continuous": continuous,
            },
            timeout_seconds=90,
            timeout=100,
        )
        payload = workflow_data.get("data") or {}
        print(json.dumps(
            _format_output(feed_type, normalized, payload.get("targetId"), payload, target_count, continuous),
            ensure_ascii=False,
        ))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))


if __name__ == "__main__":
    raw_args = sys.argv[1:]
    continuous = "--continuous" in raw_args
    args = [a for a in raw_args if a != "--continuous"]
    feed_type = args[0] if len(args) > 0 else "both"
    count = 20
    if len(args) > 1:
        try:
            count = int(args[1])
        except Exception:
            count = 20
    count = max(1, min(count, 200))
    read_home_feed(feed_type=feed_type, target_count=count, continuous=continuous)
