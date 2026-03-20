import sys
import json
import urllib.request
import time
from datetime import datetime, timezone
import hashlib

BRIDGE_URL = "http://127.0.0.1:17777"

# Bypass system proxies for local bridge requests
proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(proxy_handler)

# Safety/risk-control defaults: intentionally conservative.
READ_INTERVAL_SECONDS = 1.6
SCROLL_INTERVAL_SECONDS = 2.8
MAX_SCROLL_ROUNDS_DEFAULT = 12
MAX_SCROLL_ROUNDS_CONTINUOUS = 30


def _post_json(path, payload, timeout=90):
    req = urllib.request.Request(
        f"{BRIDGE_URL}{path}",
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with opener.open(req, timeout=timeout) as res:
        return json.loads(res.read())


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
    try:
        open_data = _post_json(
            "/open",
            {
                "url": "https://x.com/home",
                "reuseExistingTab": True,
                "reuseDomain": "x.com"
            },
            timeout=40,
        )
        target_id = open_data.get("data", {}).get("id")
        if not target_id:
            raise RuntimeError("Failed to open home page")
        _post_json("/activate", {"targetId": target_id}, timeout=30)
        return target_id
    except Exception as e:
        raise RuntimeError(f"Failed to prepare home tab: {e}")


def _build_switch_script(desired_mode):
    is_following = desired_mode == "following"
    tab_text_zh = "正在关注" if is_following else "为你推荐"
    tab_text_en = "Following" if is_following else "For you"
    return f'''(() => {{
        const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
        const selected = tabs.find(el => el.getAttribute('aria-selected') === 'true') || null;
        const selectedText = selected ? (selected.innerText || '').trim() : null;
        const target = tabs.find(el => {{
            const txt = (el.innerText || '').trim();
            const lower = txt.toLowerCase();
            return txt.includes("{tab_text_zh}") || txt.includes("{tab_text_en}") || lower.includes("{tab_text_en}".toLowerCase());
        }});
        if (target) {{
            const beforeText = (target.innerText || '').trim();
            target.click();
            return {{
                clicked: true,
                targetText: beforeText || null,
                selectedText,
                allTabs: tabs.map(el => (el.innerText || '').trim()).filter(Boolean)
            }};
        }}
        return {{
            clicked: false,
            selectedText,
            allTabs: tabs.map(el => (el.innerText || '').trim()).filter(Boolean)
        }};
    }})()'''


def _scroll_script():
    return '''(() => {
        window.scrollBy({ top: 950, left: 0, behavior: 'smooth' });
        return true;
    })()'''


def _read_page(target_id):
    return _post_json(
        "/read-page",
        {"targetId": target_id, "waitForReady": True, "maxChars": 100000},
        timeout=90,
    )


def _collect_feed_items(target_id, desired_mode, target_count=20, continuous=False):
    seen = set()
    collected = []
    last_read_data = {}
    switch_result = None
    scroll_rounds = 0
    max_scroll_rounds = MAX_SCROLL_ROUNDS_CONTINUOUS if continuous else MAX_SCROLL_ROUNDS_DEFAULT

    while True:
        read_data = _read_page(target_id)
        last_read_data = read_data
        data = read_data.get("data", {})
        ext = data.get("extensionHint", {}) or {}
        signals = ext.get("signals", {}) or {}
        timeline = (ext.get("content", {}) or {}).get("timeline", []) or []
        actual_mode = signals.get("feedMode")

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
            collected.append(item)

        if not continuous and len(collected) >= target_count and actual_mode == desired_mode:
            break

        if scroll_rounds >= max_scroll_rounds:
            break

        # Mode mismatch: try switching before next read.
        if actual_mode != desired_mode:
            switch_script = _build_switch_script(desired_mode)
            try:
                switch_result = _post_json(
                    "/evaluate",
                    {"expression": switch_script, "targetId": target_id},
                    timeout=30,
                )
            except Exception:
                pass
            time.sleep(READ_INTERVAL_SECONDS)
            continue

        # Mode aligned but not enough items: controlled scroll (low frequency).
        try:
            _post_json("/evaluate", {"expression": _scroll_script(), "targetId": target_id}, timeout=30)
        except Exception:
            pass
        scroll_rounds += 1
        time.sleep(SCROLL_INTERVAL_SECONDS)

    data = (last_read_data or {}).get("data", {}) or {}
    ext = data.get("extensionHint", {}) or {}
    signals = ext.get("signals", {}) or {}
    source = data.get("preferredContentSource")
    return {
        "items": collected if continuous else collected[:target_count],
        "source": source,
        "signals": signals,
        "switch_result": ((switch_result or {}).get("data") or {}).get("result"),
        "last_read_data": last_read_data,
        "scroll_rounds": scroll_rounds,
    }


def _format_output(feed_type_raw, feed_type_normalized, target_id, result, target_count, continuous):
    now_iso = datetime.now(timezone.utc).isoformat()
    signals = result.get("signals", {})
    items = result.get("items", [])
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
        "result": {
            "targetId": target_id,
            "source": result.get("source"),
            "count": len(items),
            "switch": result.get("switch_result"),
            "scrollRounds": result.get("scroll_rounds"),
        },
        "items": items,
        "data": items,
    }


def read_home_feed(feed_type="both", target_count=20, continuous=False):
    try:
        target_id = _open_home_target()
        normalized = _normalize_feed_type(feed_type)

        if normalized == "both":
            for_you_result = _collect_feed_items(
                target_id=target_id,
                desired_mode="for_you",
                target_count=target_count,
                continuous=continuous,
            )
            time.sleep(READ_INTERVAL_SECONDS)
            following_result = _collect_feed_items(
                target_id=target_id,
                desired_mode="following",
                target_count=target_count,
                continuous=continuous,
            )
            now_iso = datetime.now(timezone.utc).isoformat()
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
                    "for_you": _format_output(
                        feed_type_raw="For you",
                        feed_type_normalized="for_you",
                        target_id=target_id,
                        result=for_you_result,
                        target_count=target_count,
                        continuous=continuous,
                    ),
                    "following": _format_output(
                        feed_type_raw="following",
                        feed_type_normalized="following",
                        target_id=target_id,
                        result=following_result,
                        target_count=target_count,
                        continuous=continuous,
                    ),
                },
            }
            # Backward-compatible alias: default output data points to "for_you" items.
            payload["data"] = payload["feeds"]["for_you"]["items"]
            print(json.dumps(payload, ensure_ascii=False))
            return

        result = _collect_feed_items(
            target_id=target_id,
            desired_mode=normalized,
            target_count=target_count,
            continuous=continuous,
        )
        print(json.dumps(
            _format_output(
                feed_type_raw=feed_type,
                feed_type_normalized=normalized,
                target_id=target_id,
                result=result,
                target_count=target_count,
                continuous=continuous,
            ),
            ensure_ascii=False,
        ))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

if __name__ == "__main__":
    # Usage:
    #   python3 feed.py
    #   python3 feed.py following
    #   python3 feed.py both 30
    #   python3 feed.py for_you 50 --continuous
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
    # Hard clamp for risk control.
    count = max(1, min(count, 200))
    read_home_feed(feed_type=feed_type, target_count=count, continuous=continuous)
