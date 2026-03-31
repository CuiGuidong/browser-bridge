import time
from urllib.parse import urlparse


READ_INTERVAL_SECONDS = 1.2
SCROLL_INTERVAL_SECONDS = 2.2
DEFAULT_SCROLL_ROUNDS = 2


def open_weibo_page(browser_runtime, url=None, target_id=None):
    opened = None
    resolved_target_id = target_id
    if resolved_target_id:
        if url:
            opened = browser_runtime.navigate_tab(resolved_target_id, url)
            if not opened:
                return None, None
            resolved_target_id = opened.get("targetId") or opened.get("id") or target_id
        else:
            browser_runtime.activate_tab(resolved_target_id)
        return resolved_target_id, opened
    if not url:
        return None, None
    reuse_domain = (urlparse(url).hostname or "").lower() or None
    opened = browser_runtime.open_or_reuse_url(
        url,
        reuse_existing_tab=False,
        reuse_domain=reuse_domain,
    )
    if not opened:
        return None, None
    resolved_target_id = opened.get("targetId") or opened.get("id")
    return resolved_target_id, opened


def response_target_id(opened, resolved_target_id):
    if opened is not None and not opened.get("reused"):
        return None
    return resolved_target_id


def close_temporary_tab(browser_runtime, opened, resolved_target_id):
    if opened is not None and not opened.get("reused") and resolved_target_id:
        try:
            browser_runtime.close_tab(resolved_target_id)
        except Exception:
            pass


def _scroll_script():
    return """(() => {
        window.scrollBy({ top: 1050, left: 0, behavior: 'smooth' });
        return true;
    })()"""


def _dedup_items(items):
    seen = set()
    result = []
    for item in items or []:
        key = (
            (item.get("url") or "").strip(),
            (item.get("author") or "").strip(),
            (item.get("text") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def collect_flow_items(
    read_service,
    browser_runtime,
    kind,
    target_id,
    params=None,
    timeout_seconds=20,
    target_count=20,
    scroll_rounds=DEFAULT_SCROLL_ROUNDS,
):
    params = dict(params or {})
    collected = []
    last_read = None
    rounds = max(0, int(scroll_rounds))
    performed_scrolls = 0

    for round_index in range(rounds + 1):
        read_result = read_service.site_read(
            site="weibo",
            kind=kind,
            params=params,
            target_id=target_id,
            timeout_seconds=timeout_seconds,
        )
        last_read = read_result
        if not read_result:
            return {
                "ok": False,
                "error": "site read failed",
                "items": collected,
                "scrollRounds": performed_scrolls,
            }
        if read_result.get("ok") is False:
            return {
                **read_result,
                "items": collected,
                "scrollRounds": performed_scrolls,
            }

        items = ((read_result.get("content") or {}).get("items")) or []
        collected.extend(items)
        deduped = _dedup_items(collected)
        collected = deduped
        if len(collected) >= max(1, int(target_count or 1)):
            break
        if round_index >= rounds:
            break

        browser_runtime.execute_js(_scroll_script(), target_id=target_id)
        performed_scrolls += 1
        time.sleep(SCROLL_INTERVAL_SECONDS)
        params["waitForReady"] = False
        params.setdefault("intervalSeconds", READ_INTERVAL_SECONDS)

    return {
        "ok": True,
        "items": collected,
        "readResult": last_read or {},
        "scrollRounds": performed_scrolls,
    }
