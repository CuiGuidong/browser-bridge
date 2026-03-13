from urllib.parse import quote
import time

from .cdp_client import CdpHttpClient
from .cdp_ws_client import CdpWebSocketClient


class BrowserBridgeService:
    def __init__(self, client=None, ws_client=None):
        self.client = client or CdpHttpClient()
        self.ws_client = ws_client or CdpWebSocketClient()

    def get_version(self):
        return self.client.get_json("/json/version")

    def list_tabs(self):
        tabs = self.client.get_json("/json/list")
        if not isinstance(tabs, list):
            return []
        return [self._normalize_target(t) for t in tabs if isinstance(t, dict) and t.get("type") == "page"]

    def open_url(self, url):
        encoded = quote(url, safe=":/?&=#%+-_.~")
        target = self.client.put_json(f"/json/new?{encoded}")
        if isinstance(target, dict):
            return self._normalize_target(target)
        return {"url": url, "raw": target}

    def activate_tab(self, target_id):
        self.client.get_text(f"/json/activate/{target_id}")
        return {"targetId": target_id, "activated": True}

    def get_page_info(self, target_id=None):
        tabs = self.list_tabs()
        if not tabs:
            return None
        if target_id:
            for tab in tabs:
                if tab.get("id") == target_id:
                    return tab
            return None
        return tabs[0]

    def wait_for_page(self, target_id=None, timeout_seconds=10, interval_seconds=0.5):
        start = time.time()
        last = None
        stable_count = 0
        while time.time() - start < timeout_seconds:
            page = self.get_page_info(target_id)
            if page is None:
                time.sleep(interval_seconds)
                continue
            signature = (page.get("title"), page.get("url"))
            if signature == last:
                stable_count += 1
                if stable_count >= 2:
                    return {
                        "targetId": page.get("id"),
                        "title": page.get("title"),
                        "url": page.get("url"),
                        "stable": True,
                        "elapsed": round(time.time() - start, 2),
                    }
            else:
                stable_count = 0
            last = signature
            time.sleep(interval_seconds)
        page = self.get_page_info(target_id)
        return {
            "targetId": page.get("id") if page else target_id,
            "title": page.get("title") if page else None,
            "url": page.get("url") if page else None,
            "stable": False,
            "elapsed": round(time.time() - start, 2),
        }

    def get_page_content(self, target_id=None, max_chars=4000):
        target = self.get_page_info(target_id)
        if target is None:
            return None
        result = self.ws_client.call(
            target["webSocketDebuggerUrl"],
            "Runtime.evaluate",
            {"expression": f"document.body.innerText.slice(0, {int(max_chars)})", "returnByValue": True},
        )
        value = ((result.get("result") or {}).get("value"))
        return {
            "targetId": target["id"],
            "title": target.get("title"),
            "url": target.get("url"),
            "content": value or "",
        }

    def capture_screenshot(self, target_id=None, fmt="png"):
        target = self.get_page_info(target_id)
        if target is None:
            return None
        self.ws_client.call(target["webSocketDebuggerUrl"], "Page.enable", {})
        result = self.ws_client.call(
            target["webSocketDebuggerUrl"],
            "Page.captureScreenshot",
            {"format": fmt},
        )
        return {
            "targetId": target["id"],
            "title": target.get("title"),
            "url": target.get("url"),
            "format": fmt,
            "data": result.get("data", ""),
        }

    def query_elements(self, selector, target_id=None, limit=20):
        target = self.get_page_info(target_id)
        if target is None:
            return None
        safe_selector = selector.replace('\\', '\\\\').replace('"', '\\"')
        expression = f'''(() => {{
  const nodes = Array.from(document.querySelectorAll("{safe_selector}")).slice(0, {int(limit)});
  return nodes.map((el, index) => ({{
    index,
    tag: el.tagName,
    id: el.id || "",
    classes: el.className || "",
    text: (el.innerText || el.textContent || "").trim().slice(0, 200),
    href: el.href || "",
    value: ('value' in el ? el.value || "" : "")
  }}));
}})()'''
        result = self.ws_client.call(
            target["webSocketDebuggerUrl"],
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
        )
        value = ((result.get("result") or {}).get("value")) or []
        return {
            "targetId": target["id"],
            "title": target.get("title"),
            "url": target.get("url"),
            "selector": selector,
            "elements": value,
        }

    def click_selector(self, selector, target_id=None, wait_after=0):
        target = self.get_page_info(target_id)
        if target is None:
            return None
        before = {"title": target.get("title"), "url": target.get("url")}
        safe_selector = selector.replace('\\', '\\\\').replace('"', '\\"')
        expression = f'''(() => {{
  const el = document.querySelector("{safe_selector}");
  if (!el) return {{ ok: false, reason: "not found" }};
  el.click();
  return {{ ok: true, tag: el.tagName, text: (el.innerText || el.textContent || "").trim().slice(0, 200) }};
}})()'''
        result = self.ws_client.call(
            target["webSocketDebuggerUrl"],
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
        )
        value = ((result.get("result") or {}).get("value")) or {}
        after = None
        if wait_after and value.get("ok"):
            after = self.wait_for_page(target_id=target["id"], timeout_seconds=wait_after, interval_seconds=0.5)
        return {
            "targetId": target["id"],
            "title": target.get("title"),
            "url": target.get("url"),
            "selector": selector,
            "before": before,
            "result": value,
            "after": after,
        }

    def fill_selector(self, selector, text, target_id=None):
        target = self.get_page_info(target_id)
        if target is None:
            return None
        safe_selector = selector.replace('\\', '\\\\').replace('"', '\\"')
        safe_text = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        expression = f'''(() => {{
  const el = document.querySelector("{safe_selector}");
  if (!el) return {{ ok: false, reason: "not found" }};
  const canFill = ('value' in el) || el.isContentEditable;
  if (!canFill) return {{ ok: false, reason: "not fillable", tag: el.tagName }};
  el.focus();
  if ('value' in el) el.value = "{safe_text}";
  else el.textContent = "{safe_text}";
  el.dispatchEvent(new Event('input', {{ bubbles: true }}));
  el.dispatchEvent(new Event('change', {{ bubbles: true }}));
  return {{ ok: true, tag: el.tagName, value: ('value' in el ? el.value : el.textContent || '') }};
}})()'''
        result = self.ws_client.call(
            target["webSocketDebuggerUrl"],
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
        )
        value = ((result.get("result") or {}).get("value")) or {}
        return {
            "targetId": target["id"],
            "title": target.get("title"),
            "url": target.get("url"),
            "selector": selector,
            "text": text,
            "result": value,
        }

    def _normalize_target(self, target):
        return {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
            "type": target.get("type"),
            "webSocketDebuggerUrl": target.get("webSocketDebuggerUrl"),
        }
