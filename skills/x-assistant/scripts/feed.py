import hashlib
import json
import sys
import time
from datetime import datetime, timezone

from bridge_client import open_and_activate, post_json, site_action, site_read
from image_utils import process_and_spawn_downloads
from x_item_utils import dedup_and_score


READ_INTERVAL_SECONDS = 1.6
SCROLL_INTERVAL_SECONDS = 2.8
MAX_SCROLL_ROUNDS_DEFAULT = 12
MAX_SCROLL_ROUNDS_CONTINUOUS = 30


def _normalize_feed_type(feed_type):
    val = (feed_type or "").strip().lower()
    if val in ["following", "正在关注", "follow", "关注"]:
        return "following"
    if val in ["for_you", "for-you", "for you", "为你推荐", "推荐", "foryou"]:
        return "for_you"
    if val in ["both", "all", "全部", "双流", "双"]:
        return "both"
    return "for_you"


def _open_home_target():
    target_id, _ = open_and_activate(
        "https://x.com/home",
        reuse_domain="x.com",
        reuse_existing_tab=True,
        timeout=40,
        expected_url_substring="/home",
    )
    if not target_id:
        raise RuntimeError("Failed to open home page")
    return target_id


def _scroll_script():
    return """(() => {
        window.scrollBy({ top: 950, left: 0, behavior: 'smooth' });
        return true;
    })()"""


def _read_page(target_id):
    return site_read(
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


def _collect_feed_items(target_id, desired_mode, target_count=20, continuous=False):
    seen = set()
    raw_collected = []
    last_read_data = {}
    switch_result = None
    scroll_rounds = 0
    mismatch_rounds = 0
    max_scroll_rounds = MAX_SCROLL_ROUNDS_CONTINUOUS if continuous else MAX_SCROLL_ROUNDS_DEFAULT
    consecutive_empty_reads = 0

    while True:
        read_data = _read_page(target_id)
        if "error" in read_data:
            time.sleep(READ_INTERVAL_SECONDS)
            continue

        last_read_data = read_data
        data = read_data.get("data", {})
        signals = data.get("signals", {}) or {}
        timeline = (data.get("content", {}) or {}).get("timeline", []) or []
        actual_mode = signals.get("feedMode")

        if not timeline:
            consecutive_empty_reads += 1
            if consecutive_empty_reads > 3:
                break
        else:
            consecutive_empty_reads = 0

        for item in timeline:
            url = (item.get("url") or "").strip()
            text = (item.get("text") or "").strip()
            key_base = url or text
            if not key_base:
                continue
            if not url:
                key_base = hashlib.sha1(key_base.encode("utf-8", errors="ignore")).hexdigest()
            if key_base in seen:
                continue
            seen.add(key_base)
            raw_collected.append(item)

        if not continuous and len(raw_collected) >= target_count and actual_mode == desired_mode:
            break
        if scroll_rounds >= max_scroll_rounds:
            break

        if actual_mode != desired_mode:
            mismatch_rounds += 1
            if mismatch_rounds > 5:
                break
            try:
                switch_result = site_action(
                    "x",
                    "switch_feed",
                    params={"mode": desired_mode},
                    target_id=target_id,
                    timeout_seconds=30,
                    timeout=40,
                )
            except Exception:
                pass
            time.sleep(READ_INTERVAL_SECONDS)
            continue
        mismatch_rounds = 0

        try:
            post_json("/evaluate", {"expression": _scroll_script(), "targetId": target_id}, timeout=30)
        except Exception:
            pass
        scroll_rounds += 1
        time.sleep(SCROLL_INTERVAL_SECONDS)

    deduped_items = dedup_and_score(raw_collected)
    final_items = deduped_items if continuous else deduped_items[:target_count]
    deduped_items = process_and_spawn_downloads(deduped_items)
    final_items = process_and_spawn_downloads(final_items)
    data = (last_read_data or {}).get("data", {}) or {}

    return {
        "raw_items": raw_collected,
        "deduped_items": deduped_items,
        "items": final_items,
        "source": data.get("source"),
        "signals": data.get("signals", {}) or {},
        "switch_result": (switch_result or {}).get("data"),
        "scroll_rounds": scroll_rounds,
    }


def _format_output(feed_type_raw, feed_type_normalized, target_id, result, target_count, continuous):
    now_iso = datetime.now(timezone.utc).isoformat()
    signals = result.get("signals", {})
    items = result.get("items", [])
    raw_items = result.get("raw_items", [])
    deduped_items = result.get("deduped_items", [])
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
            "source": result.get("source"),
            "raw_count": len(raw_items),
            "deduped_count": len(deduped_items),
            "returned_count": len(items),
            "scrollRounds": result.get("scroll_rounds"),
            "items": items,
        },
        "data": items,
    }


def read_home_feed(feed_type="both", target_count=20, continuous=False):
    try:
        target_id = _open_home_target()
        normalized = _normalize_feed_type(feed_type)

        if normalized == "both":
            for_you_result = _collect_feed_items(target_id, "for_you", target_count, continuous)
            time.sleep(READ_INTERVAL_SECONDS)
            following_result = _collect_feed_items(target_id, "following", target_count, continuous)
            now_iso = datetime.now(timezone.utc).isoformat()

            fy_formatted = _format_output("For you", "for_you", target_id, for_you_result, target_count, continuous)
            fl_formatted = _format_output("following", "following", target_id, following_result, target_count, continuous)

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

        result = _collect_feed_items(target_id, normalized, target_count, continuous)
        print(json.dumps(
            _format_output(feed_type, normalized, target_id, result, target_count, continuous),
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
