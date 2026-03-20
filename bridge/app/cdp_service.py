from urllib.parse import quote
from urllib.parse import urlparse
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

    def open_or_reuse_url(self, url, reuse_existing_tab=False, reuse_domain=None):
        if reuse_existing_tab:
            reused = self._try_reuse_tab(url, reuse_domain=reuse_domain)
            if reused:
                return reused

        opened = self.open_url(url)
        opened["reused"] = False
        return opened

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

    def _try_reuse_tab(self, url, reuse_domain=None):
        tabs = self.list_tabs()
        if not tabs:
            return None

        target_host = (urlparse(url).hostname or "").lower()
        reuse_domain_norm = (reuse_domain or "").strip().lower()
        candidate = None
        for tab in tabs:
            tab_url = tab.get("url") or ""
            tab_host = (urlparse(tab_url).hostname or "").lower()
            if not tab_host:
                continue

            if reuse_domain_norm:
                if tab_host == reuse_domain_norm or tab_host.endswith(f".{reuse_domain_norm}"):
                    candidate = tab
                    break
            elif target_host and (tab_host == target_host or tab_host.endswith(f".{target_host}")):
                candidate = tab
                break

        if candidate is None:
            return None

        ws_url = candidate.get("webSocketDebuggerUrl")
        if not ws_url:
            return None

        try:
            self.ws_client.call(ws_url, "Page.enable", {})
            self.ws_client.call(ws_url, "Page.navigate", {"url": url})
            self.activate_tab(candidate["id"])
            time.sleep(0.4)
            updated = self.get_page_info(candidate["id"]) or candidate
            updated["reused"] = True
            return updated
        except Exception:
            return None

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

    def execute_js(self, expression, target_id=None):
        target = self.get_page_info(target_id)
        if target is None:
            return None
        result = self.ws_client.call(
            target["webSocketDebuggerUrl"],
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
        )
        return (result.get("result") or {}).get("value")

    def scroll_page(self, distance=500, behavior="smooth", target_id=None):
        """Scroll the page to trigger lazy loading."""
        expression = f'window.scrollBy({{ top: {int(distance)}, left: 0, behavior: "{behavior}" }})'
        self.execute_js(expression, target_id=target_id)
        time.sleep(1.0 if behavior == "smooth" else 0.2)
        return {"scrolled": True, "distance": distance}
    def get_page_content(self, target_id=None, max_chars=40000):
        target = self.get_page_info(target_id)
        if target is None:
            return None

        # Deep extraction expression that pierces Shadow DOM
        expression = f'''(() => {{
const extractText = (root) => {{
let text = "";
if (root.nodeType === Node.TEXT_NODE) return root.nodeValue;
if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE && root.nodeType !== Node.DOCUMENT_FRAGMENT_NODE) return "";

// Skip hidden elements and common noise
const style = window.getComputedStyle(root);
if (style && (style.display === "none" || style.visibility === "hidden")) return "";

if (root.tagName === "SCRIPT" || root.tagName === "STYLE" || root.tagName === "NOSCRIPT") return "";

for (const child of root.childNodes) {{
  text += extractText(child);
}}

if (root.shadowRoot) {{
  text += extractText(root.shadowRoot);
}}

return text + (root.nodeType === Node.ELEMENT_NODE ? "\\n" : "");
}};

const raw = extractText(document);
return raw.trim().slice(0, {int(max_chars)});
}})()'''
        result = self.ws_client.call(
            target["webSocketDebuggerUrl"],
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
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

    def read_page(self, target_id=None, max_chars=40000, wait_for_ready=False, timeout_seconds=15, interval_seconds=1, selector=None):
        target = self.get_page_info(target_id)
        if target is None:
            return None
        
        url = target.get("url") or ""
        is_x = "x.com" in url or "twitter.com" in url
        is_x_timeline = is_x and ("/home" in url or "/search" in url or "/explore" in url)
        is_x_post = is_x and ("/status/" in url)

        if is_x_post:
            # Try to expand long post if "Show more" button exists
            expand_expr = '''(() => {
                const btn = Array.from(document.querySelectorAll('div[role="button"]'))
                    .find(el => /显示更多|Show more/i.test(el.innerText));
                if (btn) {
                    btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    btn.click();
                    return true;
                }
                return false;
            })()'''
            self.execute_js(expand_expr, target_id=target["id"])
            time.sleep(3.0) # wait for expansion
            
        if is_x_timeline:
            # Execute "Light Scroll" to load a good batch of recent tweets (~20-30) without getting rate-limited
            for _ in range(3):
                self.scroll_page(distance=800, behavior="smooth", target_id=target["id"])
                time.sleep(1.5)

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
  const xHost = location.hostname.includes('x.com') || location.hostname.includes('twitter.com');
  const xTimeline = xHost && (location.pathname === '/home' || location.pathname.startsWith('/search') || location.pathname.startsWith('/explore'));
  const xPost = xHost && !xTimeline;
  const xArticle = document.querySelector('article');
  const xTweetText = document.querySelector('[data-testid="tweetText"]');
  const xPostReady = !!(xArticle && (xTweetText || (xArticle.innerText || '').trim().length > 80));
  const xTimelineReady = document.querySelectorAll('article').length >= 3 || document.querySelectorAll('[data-testid="cellInnerDiv"]').length >= 3;
  const title = document.title || '';
  const url = location.href;
  const readyState = document.readyState;
  const titleReady = !/^X$/.test(title) && title.trim().length > 3;
  const urlReady = !url.includes('/i/status/') || url.includes('/status/');
  const contentReady = contentLength > 120;
  const genericReady = readyState === 'complete' && titleReady && urlReady && contentReady && (selector ? !!selectorFound : true);
  const ready = xHost ? (readyState === 'complete' && titleReady && (xTimeline ? xTimelineReady : xPostReady)) : genericReady;
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
