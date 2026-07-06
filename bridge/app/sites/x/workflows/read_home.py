import time

from .common import close_temporary_tab, open_x_page, response_target_id
from ....media.image_cache import normalize_image_tags


READ_INTERVAL_SECONDS = 1.6
SCROLL_INTERVAL_SECONDS = 2.8
MAX_SCROLL_ROUNDS_DEFAULT = 12
MAX_SCROLL_ROUNDS_CONTINUOUS = 30


def _scroll_script():
    return """(() => {
        window.scrollBy({ top: 950, left: 0, behavior: 'smooth' });
        return true;
    })()"""


def _normalize_mode(mode):
    val = (mode or "").strip().lower()
    if val in {"following", "follow", "关注", "正在关注"}:
        return "following"
    return "for_you"


def _infer_page_type(result):
    signals = result.get("signals") or {}
    page = result.get("page") or {}
    url = page.get("url") or ""
    if "/home" in url:
        return "home"
    if signals.get("isTimeline"):
        return "timeline"
    return None


def _read_page(read_service, target_id):
    return read_service.site_read(
        site="x",
        kind="read_timeline",
        params={
            "waitForReady": True,
            "intervalSeconds": 1,
            "maxChars": 100000,
        },
        target_id=target_id,
        timeout_seconds=90,
    )


def _collect_feed(read_service, action_service, browser_runtime, target_id, desired_mode, target_count=20, continuous=False):
    seen = set()
    collected = []
    last_read = {}
    switch_result = None
    scroll_rounds = 0
    mismatch_rounds = 0
    max_scroll_rounds = MAX_SCROLL_ROUNDS_CONTINUOUS if continuous else MAX_SCROLL_ROUNDS_DEFAULT
    consecutive_empty_reads = 0

    while True:
        read_data = _read_page(read_service, target_id)
        if not read_data:
            time.sleep(READ_INTERVAL_SECONDS)
            continue
        if read_data.get("ok") is False:
            return {
                "ok": False,
                "source": read_data.get("source"),
                "signals": read_data.get("signals") or {},
                "page": read_data.get("page") or {},
                "content": read_data.get("content") or {},
                "debug": read_data.get("debug") or {},
                "error": read_data.get("error"),
            }

        last_read = read_data
        signals = read_data.get("signals") or {}
        timeline = ((read_data.get("content") or {}).get("timeline")) or []
        actual_mode = signals.get("feedMode")

        if not timeline:
            consecutive_empty_reads += 1
            if consecutive_empty_reads > 3:
                break
        else:
            consecutive_empty_reads = 0

        for item in timeline:
            key = (item.get("url") or item.get("text") or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            collected.append(item)

        if not continuous and len(collected) >= target_count and actual_mode == desired_mode:
            break
        if scroll_rounds >= max_scroll_rounds:
            break

        if actual_mode != desired_mode:
            mismatch_rounds += 1
            if mismatch_rounds > 5:
                break
            switch_data = action_service.site_action(
                "x",
                "switch_feed",
                params={"mode": desired_mode},
                target_id=target_id,
                timeout_seconds=30,
            )
            switch_result = switch_data
            time.sleep(READ_INTERVAL_SECONDS)
            continue

        mismatch_rounds = 0
        browser_runtime.execute_js(_scroll_script(), target_id=target_id)
        scroll_rounds += 1
        time.sleep(SCROLL_INTERVAL_SECONDS)

    return {
        "source": last_read.get("source"),
        "signals": last_read.get("signals") or {},
        "rawItems": collected,
        "switchResult": switch_result,
        "scrollRounds": scroll_rounds,
    }


def run(read_service, action_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    desired_mode = _normalize_mode((params or {}).get("mode") or "for_you")
    target_count = int((params or {}).get("targetCount") or 20)
    continuous = bool((params or {}).get("continuous"))
    resolved_target_id, opened = open_x_page(
        browser_runtime,
        url="https://x.com/home",
        target_id=target_id,
    )
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "x",
            "workflow": "read_home",
            "error": "failed to open page",
        }

    try:
        result = _collect_feed(
            read_service=read_service,
            action_service=action_service,
            browser_runtime=browser_runtime,
            target_id=resolved_target_id,
            desired_mode=desired_mode,
            target_count=target_count,
            continuous=continuous,
        )
        if result.get("ok") is False:
            return {
                **result,
                "site": "x",
                "workflow": "read_home",
                "targetId": response_target_id(opened, resolved_target_id),
                "debug": {
                    "open": opened,
                    **(result.get("debug") or {}),
                },
            }
        actual_page_type = _infer_page_type(result)
        if actual_page_type not in {"home", "timeline"}:
            return {
                "ok": False,
                "site": "x",
                "workflow": "read_home",
                "targetId": response_target_id(opened, resolved_target_id),
                "error": "unexpected page type",
                "expectedPageType": "home",
                "actualPageType": actual_page_type,
            }
        return {
            "ok": True,
            "site": "x",
            "workflow": "read_home",
            "targetId": response_target_id(opened, resolved_target_id),
            "summary": {
                "source": result.get("source"),
                "mode": "semantic",
                "pageType": actual_page_type,
            },
            "items": [],
            "checkpoint": {},
            "page": {"url": "https://x.com/home"},
            "signals": result.get("signals") or {},
            "content": {
                "timeline": normalize_image_tags(result.get("rawItems") or []),
            },
            "debug": {
                "open": opened,
                "scrollRounds": result.get("scrollRounds"),
                "switchResult": result.get("switchResult"),
            },
        }
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
