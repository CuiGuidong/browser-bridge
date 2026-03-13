from urllib.parse import quote
import time
import json

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

    def probe_page_readiness(self, target_id=None, timeout_seconds=15, interval_seconds=1, selector=None):
        target = self.get_page_info(target_id)
        if target is None:
            return None
        ws_url = target["webSocketDebuggerUrl"]
        start = time.time()
        last_signature = None
        stable_count = 0
        last_probe = None
        while time.time() - start < timeout_seconds:
            probe = self._collect_probe(ws_url, selector=selector)
            if probe.get("ready"):
                probe["elapsed"] = round(time.time() - start, 2)
                probe["targetId"] = target["id"]
                probe["title"] = probe.get("title") or target.get("title")
                probe["url"] = probe.get("url") or target.get("url")
                return probe
            signature = (
                probe.get("readyState"),
                probe.get("url"),
                probe.get("title"),
                probe.get("contentLengthBucket"),
                probe.get("selectorFound"),
                probe.get("xPostReady"),
            )
            if signature == last_signature:
                stable_count += 1
            else:
                stable_count = 0
            probe["stableCount"] = stable_count
            last_signature = signature
            last_probe = probe
            time.sleep(interval_seconds)
        if last_probe is None:
            last_probe = self._collect_probe(ws_url, selector=selector)
        last_probe["elapsed"] = round(time.time() - start, 2)
        last_probe["targetId"] = target["id"]
        last_probe["title"] = last_probe.get("title") or target.get("title")
        last_probe["url"] = last_probe.get("url") or target.get("url")
        return last_probe

    def read_page(self, target_id=None, max_chars=4000, wait_for_ready=False, timeout_seconds=15, interval_seconds=1, selector=None):
        target = self.get_page_info(target_id)
        if target is None:
            return None
        readiness = None
        if wait_for_ready:
            readiness = self.probe_page_readiness(
                target_id=target["id"],
                timeout_seconds=timeout_seconds,
                interval_seconds=interval_seconds,
                selector=selector,
            )
            target = self.get_page_info(target["id"]) or target
        content = self.get_page_content(target["id"], max_chars=max_chars)
        if content is None:
            return None
        content["readiness"] = readiness
        return content

    def _collect_probe(self, websocket_debugger_url, selector=None):
        safe_selector = json.dumps(selector) if selector else "null"
        expression = f'''(() => {{
  const selector = {safe_selector};
  const text = (document.body?.innerText || '').trim();
  const contentLength = text.length;
  const selectorFound = selector ? !!document.querySelector(selector) : null;
  const xPost = location.hostname.includes('x.com') || location.hostname.includes('twitter.com');
  const xArticle = document.querySelector('article');
  const xTweetText = document.querySelector('[data-testid="tweetText"]');
  const xPostReady = !!(xArticle && (xTweetText || (xArticle.innerText || '').trim().length > 80));
  const title = document.title || '';
  const url = location.href;
  const readyState = document.readyState;
  const titleReady = !/^X$/.test(title) && title.trim().length > 3;
  const urlReady = !url.includes('/i/status/') || url.includes('/status/');
  const contentReady = contentLength > 120;
  const genericReady = readyState === 'complete' && titleReady && urlReady && contentReady && (selector ? !!selectorFound : true);
  const ready = xPost ? (readyState === 'complete' && titleReady && urlReady && xPostReady) : genericReady;
  return {{
    ready,
    readyState,
    title,
    url,
    contentLength,
    contentLengthBucket: Math.floor(contentLength / 100),
    selector,
    selectorFound,
    xPost,
    xPostReady,
    signals: {{ titleReady, urlReady, contentReady }}
  }};
}})()'''
        result = self.ws_client.call(
            websocket_debugger_url,
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
        )
        return ((result.get("result") or {}).get("value")) or {}

    def _normalize_target(self, target):
        return {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
            "type": target.get("type"),
            "webSocketDebuggerUrl": target.get("webSocketDebuggerUrl"),
        }
