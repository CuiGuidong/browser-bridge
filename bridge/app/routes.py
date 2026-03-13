import json

from .schemas import ok, fail


def handle_health(service):
    try:
        version = service.get_version()
        return 200, ok("health", {
            "bridge": "alive",
            "cdp": "connected",
            "browser": version.get("Browser"),
            "protocolVersion": version.get("Protocol-Version"),
        })
    except Exception as e:
        return 500, fail("health", str(e))


def handle_version(service):
    try:
        version = service.get_version()
        return 200, ok("version", version)
    except Exception as e:
        return 500, fail("version", str(e))


def handle_tabs(service):
    try:
        return 200, ok("tabs", service.list_tabs())
    except Exception as e:
        return 500, fail("tabs", str(e))


def handle_open(service, body):
    try:
        data = json.loads(body or "{}")
        url = data.get("url")
        if not url:
            return 400, fail("open", "missing url")
        return 200, ok("open", service.open_url(url))
    except Exception as e:
        return 500, fail("open", str(e))


def handle_activate(service, body):
    try:
        data = json.loads(body or "{}")
        target_id = data.get("targetId")
        if not target_id:
            return 400, fail("activate", "missing targetId")
        return 200, ok("activate", service.activate_tab(target_id))
    except Exception as e:
        return 500, fail("activate", str(e))


def handle_wait(service, query):
    try:
        target_id = query.get("targetId", [None])[0]
        timeout_seconds = float(query.get("timeoutSeconds", ["10"])[0])
        interval_seconds = float(query.get("intervalSeconds", ["0.5"])[0])
        result = service.wait_for_page(target_id=target_id, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)
        return 200, ok("wait", result)
    except Exception as e:
        return 500, fail("wait", str(e))


def handle_page_info(service, query):
    try:
        target_id = query.get("targetId", [None])[0]
        info = service.get_page_info(target_id)
        if info is None:
            return 404, fail("page-info", "page not found")
        return 200, ok("page-info", info)
    except Exception as e:
        return 500, fail("page-info", str(e))


def handle_page_content(service, query):
    try:
        target_id = query.get("targetId", [None])[0]
        max_chars_raw = query.get("maxChars", ["4000"])[0]
        max_chars = int(max_chars_raw)
        info = service.get_page_content(target_id, max_chars=max_chars)
        if info is None:
            return 404, fail("page-content", "page not found")
        return 200, ok("page-content", info)
    except Exception as e:
        return 500, fail("page-content", str(e))


def handle_screenshot(service, body):
    try:
        data = json.loads(body or "{}")
        target_id = data.get("targetId")
        fmt = data.get("format", "png")
        result = service.capture_screenshot(target_id=target_id, fmt=fmt)
        if result is None:
            return 404, fail("screenshot", "page not found")
        return 200, ok("screenshot", result)
    except Exception as e:
        return 500, fail("screenshot", str(e))


def handle_query(service, query):
    try:
        selector = query.get("selector", [None])[0]
        target_id = query.get("targetId", [None])[0]
        limit = int(query.get("limit", ["20"])[0])
        if not selector:
            return 400, fail("query", "missing selector")
        result = service.query_elements(selector, target_id=target_id, limit=limit)
        if result is None:
            return 404, fail("query", "page not found")
        return 200, ok("query", result)
    except Exception as e:
        return 500, fail("query", str(e))


def handle_click(service, body):
    try:
        data = json.loads(body or "{}")
        selector = data.get("selector")
        target_id = data.get("targetId")
        wait_after = float(data.get("waitAfter", 0))
        if not selector:
            return 400, fail("click", "missing selector")
        result = service.click_selector(selector, target_id=target_id, wait_after=wait_after)
        if result is None:
            return 404, fail("click", "page not found")
        return 200, ok("click", result)
    except Exception as e:
        return 500, fail("click", str(e))


def handle_fill(service, body):
    try:
        data = json.loads(body or "{}")
        selector = data.get("selector")
        text = data.get("text", "")
        target_id = data.get("targetId")
        if not selector:
            return 400, fail("fill", "missing selector")
        result = service.fill_selector(selector, text, target_id=target_id)
        if result is None:
            return 404, fail("fill", "page not found")
        return 200, ok("fill", result)
    except Exception as e:
        return 500, fail("fill", str(e))
