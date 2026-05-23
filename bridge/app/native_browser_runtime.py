"""Native Browser Runtime.

Implements the same interface as CdpRuntime but routes all browser operations
through the Native Session Manager to the browser extension via Native Messaging.
"""
import time
from urllib.parse import urlparse


class NativeBrowserRuntime:
    def __init__(self, session_manager):
        self._sm = session_manager
        self._tab_limit = 30

    def _sid(self):
        return self._sm.get_active_session()

    def _cmd(self, method, params=None, timeout=30):
        sid = self._sid()
        if not sid:
            return {"ok": False, "error": {"code": "no_active_session", "message": "No native session connected"}}
        return self._sm.send_command_sync(sid, method, params, timeout_seconds=timeout)

    _RESTRICTED_PREFIXES = ("chrome://", "edge://", "chrome-extension://", "about:")

    def _resolve_native_tab_id(self, target_id=None):
        """Resolve target_id to a nativeTabId integer. Returns None if unresolvable."""
        if target_id is not None:
            try:
                return int(target_id)
            except (ValueError, TypeError):
                return None
        # No target_id: return first non-restricted page tab
        tabs_result = self._cmd("tabs.list", timeout=10)
        if not tabs_result.get("ok"):
            return None
        tabs = (tabs_result.get("data") or {}).get("tabs", [])
        for tab in tabs:
            if tab.get("type") != "page":
                continue
            url = tab.get("url") or ""
            if any(url.startswith(prefix) for prefix in self._RESTRICTED_PREFIXES):
                continue
            return tab.get("nativeTabId")
        return None

    def _find_tab_by_id(self, native_tab_id):
        """Find tab info from tabs.list by nativeTabId."""
        tabs_result = self._cmd("tabs.list", timeout=10)
        if not tabs_result.get("ok"):
            return None
        for tab in (tabs_result.get("data") or {}).get("tabs", []):
            if tab.get("nativeTabId") == native_tab_id:
                return tab
        return None

    def get_version(self):
        return {"Browser": "NativeMessaging/1.0", "Protocol-Version": "1.3", "browser": "native", "protocolVersion": "1.3"}

    def list_tabs(self):
        result = self._cmd("tabs.list", timeout=10)
        if not result.get("ok"):
            return []
        return (result.get("data") or {}).get("tabs", [])

    def open_or_reuse_url(self, url, reuse_existing_tab=False, reuse_domain=None):
        tabs = self.list_tabs()
        if reuse_existing_tab or len(tabs) >= self._tab_limit:
            reused = self._try_reuse_tab(url, reuse_domain=reuse_domain, tabs=tabs)
            if reused:
                return reused

        result = self._cmd("tabs.create", {"url": url, "active": True})
        if not result.get("ok"):
            return None
        tab = (result.get("data") or {}).get("tab")
        if tab:
            tab["reused"] = False
        return tab

    def _try_reuse_tab(self, url, reuse_domain=None, tabs=None):
        tabs = tabs or self.list_tabs()
        if not tabs:
            return None
        target_host = (urlparse(url).hostname or "").lower()
        reuse_domain_norm = (reuse_domain or "").strip().lower()
        candidate = None
        for tab in tabs:
            tab_host = (urlparse(tab.get("url") or "").hostname or "").lower()
            if not tab_host:
                continue
            if reuse_domain_norm:
                if tab_host == reuse_domain_norm or tab_host.endswith(f".{reuse_domain_norm}"):
                    candidate = tab
                    break
            elif target_host and (tab_host == target_host or tab_host.endswith(f".{target_host}")):
                candidate = tab
                break
        if not candidate:
            return None
        tab_id = candidate.get("nativeTabId")
        self._cmd("tabs.activate", {"tabId": tab_id})
        self._cmd("debugger.send", {"tabId": tab_id, "command": "Page.enable", "params_": {}})
        self._cmd("debugger.send", {"tabId": tab_id, "command": "Page.navigate", "params_": {"url": url}})
        self._wait_for_page_load(tab_id, timeout_seconds=15)
        updated = self._find_tab_by_id(tab_id) or candidate
        updated["reused"] = True
        return updated

    def activate_tab(self, target_id):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        result = self._cmd("tabs.activate", {"tabId": tab_id})
        if not result.get("ok"):
            return None
        return {"targetId": str(tab_id), "activated": True}

    def navigate_tab(self, target_id, url):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        # Enable Page events and navigate
        self._cmd("debugger.send", {"tabId": tab_id, "command": "Page.enable", "params_": {}})
        self._cmd("debugger.send", {"tabId": tab_id, "command": "Page.navigate", "params_": {"url": url}})
        self._cmd("tabs.activate", {"tabId": tab_id})
        # Wait for page load to complete
        self._wait_for_page_load(tab_id, timeout_seconds=15)
        updated = self._find_tab_by_id(tab_id)
        if updated:
            updated["reused"] = True
            updated["navigated"] = True
        return updated

    def _wait_for_page_load(self, tab_id, timeout_seconds=15):
        """Poll until page readyState is 'complete'."""
        start = time.time()
        while time.time() - start < timeout_seconds:
            result = self._cmd("debugger.send", {
                "tabId": tab_id,
                "command": "Runtime.evaluate",
                "params_": {"expression": "document.readyState", "returnByValue": True},
            }, timeout=5)
            state = ((result.get("data") or {}).get("result") or {}).get("value")
            if state == "complete":
                time.sleep(0.5)  # Extra settle time for content script injection
                return
            time.sleep(0.5)

    def reload_tab(self, target_id):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        tab = self._find_tab_by_id(tab_id)
        result = self._cmd("debugger.send", {"tabId": tab_id, "command": "Page.reload", "params_": {"ignoreCache": True}})
        if not result.get("ok"):
            return {"targetId": str(tab_id), "url": tab.get("url") if tab else None, "reloaded": False, "error": str(result.get("error"))}
        return {"targetId": str(tab_id), "url": tab.get("url") if tab else None, "reloaded": True}

    def close_tab(self, target_id):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        result = self._cmd("tabs.close", {"tabId": tab_id})
        if not result.get("ok"):
            return None
        return {"targetId": str(tab_id), "closed": True}

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
                        "targetId": str(page.get("nativeTabId", "")),
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
            "targetId": str(page.get("nativeTabId", "")) if page else str(target_id or ""),
            "title": page.get("title") if page else None,
            "url": page.get("url") if page else None,
            "stable": False,
            "elapsed": round(time.time() - start, 2),
        }

    def get_page_info(self, target_id=None):
        tabs = self.list_tabs()
        if not tabs:
            return None
        if target_id is not None:
            tab_id = self._resolve_native_tab_id(target_id)
            for tab in tabs:
                if tab.get("nativeTabId") == tab_id:
                    return tab
            return None
        return tabs[0] if tabs else None

    def get_page_content(self, target_id=None, max_chars=40000):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        tab = self._find_tab_by_id(tab_id)
        expression = f'''(() => {{
const extractText = (root) => {{
let text = "";
if (root.nodeType === Node.TEXT_NODE) return root.nodeValue;
if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE && root.nodeType !== Node.DOCUMENT_FRAGMENT_NODE) return "";
const style = window.getComputedStyle(root);
if (style && (style.display === "none" || style.visibility === "hidden")) return "";
if (root.tagName === "SCRIPT" || root.tagName === "STYLE" || root.tagName === "NOSCRIPT") return "";
for (const child of root.childNodes) {{ text += extractText(child); }}
if (root.shadowRoot) {{ text += extractText(root.shadowRoot); }}
return text + (root.nodeType === Node.ELEMENT_NODE ? "\\n" : "");
}};
const raw = extractText(document);
return raw.trim().slice(0, {int(max_chars)});
}})()'''
        result = self._cmd("debugger.send", {"tabId": tab_id, "command": "Runtime.evaluate", "params_": {"expression": expression, "returnByValue": True}})
        value = ((result.get("data") or {}).get("result") or {}).get("value")
        return {
            "targetId": str(tab_id),
            "title": tab.get("title") if tab else None,
            "url": tab.get("url") if tab else None,
            "content": value or "",
        }

    def capture_screenshot(self, target_id=None, fmt="png"):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        tab = self._find_tab_by_id(tab_id)
        self._cmd("debugger.send", {"tabId": tab_id, "command": "Page.enable", "params_": {}})
        result = self._cmd("debugger.send", {"tabId": tab_id, "command": "Page.captureScreenshot", "params_": {"format": fmt}})
        data = (result.get("data") or {}).get("data", "")
        return {
            "targetId": str(tab_id),
            "title": tab.get("title") if tab else None,
            "url": tab.get("url") if tab else None,
            "format": fmt,
            "data": data,
        }

    def query_elements(self, selector, target_id=None, limit=20):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        tab = self._find_tab_by_id(tab_id)
        safe_selector = selector.replace('\\', '\\\\').replace('"', '\\"')
        expression = f'''(() => {{
  const nodes = Array.from(document.querySelectorAll("{safe_selector}")).slice(0, {int(limit)});
  return nodes.map((el, index) => ({{
    index, tag: el.tagName, id: el.id || "", classes: el.className || "",
    text: (el.innerText || el.textContent || "").trim().slice(0, 200),
    href: el.href || "", value: ('value' in el ? el.value || "" : "")
  }}));
}})()'''
        result = self._cmd("debugger.send", {"tabId": tab_id, "command": "Runtime.evaluate", "params_": {"expression": expression, "returnByValue": True}})
        value = ((result.get("data") or {}).get("result") or {}).get("value") or []
        return {
            "targetId": str(tab_id),
            "title": tab.get("title") if tab else None,
            "url": tab.get("url") if tab else None,
            "selector": selector,
            "elements": value,
        }

    def probe_page_readiness(self, target_id=None, timeout_seconds=15, interval_seconds=1, selector=None):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        tab = self._find_tab_by_id(tab_id)
        start = time.time()
        last_signature = None
        stable_count = 0
        while time.time() - start < timeout_seconds:
            probe = self._collect_probe(tab_id, selector=selector)
            if probe.get("ready"):
                probe["elapsed"] = round(time.time() - start, 2)
                probe["targetId"] = str(tab_id)
                probe["title"] = probe.get("title") or (tab.get("title") if tab else None)
                probe["url"] = probe.get("url") or (tab.get("url") if tab else None)
                return probe
            signature = (probe.get("readyState"), probe.get("url"), probe.get("title"), probe.get("contentLengthBucket"), probe.get("selectorFound"))
            if signature == last_signature:
                stable_count += 1
                if stable_count >= 3:
                    probe["elapsed"] = round(time.time() - start, 2)
                    probe["targetId"] = str(tab_id)
                    probe["ready"] = False
                    return probe
            else:
                stable_count = 0
            last_signature = signature
            time.sleep(interval_seconds)
        return {
            "targetId": str(tab_id),
            "title": tab.get("title") if tab else None,
            "url": tab.get("url") if tab else None,
            "ready": False,
            "elapsed": round(time.time() - start, 2),
        }

    def _collect_probe(self, tab_id, selector=None):
        selector_check = ""
        if selector:
            safe = selector.replace('\\', '\\\\').replace('"', '\\"')
            selector_check = f'selectorFound: !!document.querySelector("{safe}"),'
        expression = f'''(() => {{
  const body = document.body;
  const text = body ? (body.innerText || "") : "";
  return {{
    readyState: document.readyState,
    url: location.href,
    title: document.title,
    contentLength: text.length,
    contentLengthBucket: text.length < 50 ? "empty" : text.length < 200 ? "short" : "normal",
    {selector_check}
  }};
}})()'''
        result = self._cmd("debugger.send", {"tabId": tab_id, "command": "Runtime.evaluate", "params_": {"expression": expression, "returnByValue": True}}, timeout=10)
        probe = (result.get("data") or {}).get("result") or {}
        value = probe.get("value") or {}
        value["ready"] = (
            value.get("readyState") == "complete"
            and value.get("contentLengthBucket") not in ("empty",)
        )
        if selector and not value.get("selectorFound"):
            value["ready"] = False
        return value

    def execute_js(self, expression, target_id=None):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        result = self._cmd("debugger.send", {"tabId": tab_id, "command": "Runtime.evaluate", "params_": {"expression": expression, "returnByValue": True}})
        return ((result.get("data") or {}).get("result") or {}).get("value")

    def set_file_input_files_by_selector(self, target_id, selector, files):
        tab_id = self._resolve_native_tab_id(target_id)
        if tab_id is None:
            return None
        tab = self._find_tab_by_id(tab_id)
        normalized_files = [str(path) for path in (files or []) if str(path).strip()]
        if not selector:
            raise ValueError("selector is required")
        if not normalized_files:
            raise ValueError("files is required")

        # Step 1-2: Enable Page and DOM
        self._cmd("debugger.send", {"tabId": tab_id, "command": "Page.enable", "params_": {}})
        self._cmd("debugger.send", {"tabId": tab_id, "command": "DOM.enable", "params_": {}})

        # Step 3: Get document root
        doc_result = self._cmd("debugger.send", {"tabId": tab_id, "command": "DOM.getDocument", "params_": {"depth": 1, "pierce": True}})
        root_node_id = ((doc_result.get("data") or {}).get("root") or {}).get("nodeId")
        if not root_node_id:
            return {"ok": False, "targetId": str(tab_id), "selector": selector, "error": "DOM.getDocument failed"}

        # Step 4: Query selector
        query_result = self._cmd("debugger.send", {"tabId": tab_id, "command": "DOM.querySelector", "params_": {"nodeId": root_node_id, "selector": selector}})
        node_id = (query_result.get("data") or {}).get("nodeId")
        if not node_id:
            return {"ok": False, "targetId": str(tab_id), "title": tab.get("title") if tab else None, "url": tab.get("url") if tab else None, "selector": selector, "files": normalized_files, "error": "file input not found"}

        # Step 5: Set files
        self._cmd("debugger.send", {"tabId": tab_id, "command": "DOM.setFileInputFiles", "params_": {"nodeId": node_id, "files": normalized_files}})

        # Step 6: Resolve node to objectId
        resolve_result = self._cmd("debugger.send", {"tabId": tab_id, "command": "DOM.resolveNode", "params_": {"nodeId": node_id}})
        object_id = (((resolve_result.get("data") or {}).get("object")) or {}).get("objectId")

        # Step 7: Dispatch events
        if object_id:
            self._cmd("debugger.send", {"tabId": tab_id, "command": "Runtime.callFunctionOn", "params_": {
                "objectId": object_id,
                "functionDeclaration": """function() {
                    this.dispatchEvent(new Event('input', { bubbles: true }));
                    this.dispatchEvent(new Event('change', { bubbles: true }));
                    return { fileCount: this.files ? this.files.length : 0, firstFileName: this.files && this.files[0] ? this.files[0].name : null };
                }""",
                "returnByValue": True,
            }})

        return {
            "ok": True,
            "targetId": str(tab_id),
            "title": tab.get("title") if tab else None,
            "url": tab.get("url") if tab else None,
            "selector": selector,
            "nodeId": node_id,
            "files": normalized_files,
        }
