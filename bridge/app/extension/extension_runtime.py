import threading
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse


class ExtensionRuntime:
    def __init__(self, native_session_manager=None, site_registry=None):
        self._state = {"lastReport": None, "reports": []}
        self._condition = threading.Condition()
        self._next_command_id = 1
        self._pending_commands = []
        self._command_results = {}
        self._native_sm = native_session_manager
        self._site_registry = site_registry

    def get_state(self) -> Dict[str, Any]:
        # Aggregate reports from native session manager
        if self._native_sm:
            native_report_entry = self._native_sm.get_report()
            if native_report_entry:
                payload = native_report_entry.get("payload")
                if payload:
                    self._state["lastReport"] = payload
                    if not self._state["reports"] or self._state["reports"][-1] is not payload:
                        self._state["reports"].append(payload)
                        self._state["reports"] = self._state["reports"][-120:]
        return self._state

    def store_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        self._state["lastReport"] = report
        self._state["reports"].append(report)
        self._state["reports"] = self._state["reports"][-120:]
        return {"accepted": True}

    def get_hint(self, target_url: Optional[str] = None):
        # Collect all available reports (native + legacy)
        candidates = list(self._state.get("reports") or [])
        if self._native_sm:
            native_entry = self._native_sm.get_report()
            if native_entry:
                native_payload = native_entry.get("payload")
                if native_payload and native_payload not in candidates:
                    candidates.append(native_payload)

        if not candidates:
            return None

        # If no target_url, return the latest report
        if not target_url:
            return candidates[-1]

        # Match by target_url using existing normalization
        # Search from newest to oldest
        for report in reversed(candidates):
            report_url = ((report or {}).get("page") or {}).get("url")
            if self._match_reason(report_url, target_url):
                return report

        # No match found — return None (caller should fall back to browser runtime probe)
        return None

    def _resolve_semantic_tab_id(self, target_id=None, target_url=None, site=None):
        """Resolve target to a nativeTabId via native session's tabs.list."""
        if not self._native_sm:
            return None
        sid = self._native_sm.get_active_session()
        if not sid:
            return None

        tabs_result = self._native_sm.send_command(sid, "tabs.list", timeout_seconds=10)
        if not tabs_result.get("ok"):
            return None
        tabs = (tabs_result.get("data") or {}).get("tabs", [])

        _RESTRICTED = ("chrome://", "edge://", "chrome-extension://", "about:")
        page_tabs = [t for t in tabs if t.get("type") == "page"
                     and not any((t.get("url") or "").startswith(p) for p in _RESTRICTED)]

        # Priority 1: target_id
        if target_id is not None:
            try:
                tid = int(target_id)
                for t in page_tabs:
                    if t.get("nativeTabId") == tid:
                        return tid
            except (ValueError, TypeError):
                pass
            return None

        # Priority 2: target_url (exact normalized match + X status_id)
        if target_url:
            norm_target = self._normalize_url(target_url)
            for t in page_tabs:
                tab_url = t.get("url") or ""
                if self._normalize_url(tab_url) == norm_target:
                    return t.get("nativeTabId")
            # X status_id match
            target_sid = self._extract_x_status_id(target_url)
            if target_sid:
                for t in page_tabs:
                    if self._extract_x_status_id(t.get("url")) == target_sid:
                        return t.get("nativeTabId")
            return None

        # Priority 3: site hosts filter
        if site and self._site_registry:
            site_module = self._site_registry.get(site)
            if site_module:
                hosts = {h.lower() for h in getattr(site_module, "hosts", set())}
                for t in page_tabs:
                    tab_host = (urlparse(t.get("url") or "").hostname or "").lower()
                    if tab_host and (tab_host in hosts or any(tab_host.endswith(f".{h}") for h in hosts)):
                        return t.get("nativeTabId")

        return None

    def invoke(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 20,
        target_url: Optional[str] = None,
        target_id: Optional[str] = None,
        site: Optional[str] = None,
    ):
        # Route through native session if available
        if self._native_sm and self._native_sm.get_active_session():
            tab_id = self._resolve_semantic_tab_id(target_id, target_url, site)
            if tab_id is None:
                return {"ok": False, "error": "tab_not_found", "target_id": target_id, "target_url": target_url}
            sid = self._native_sm.get_active_session()
            result = self._native_sm.send_command(
                sid, "semantic.invoke",
                params={"method": method, "params": params or {}, "tabId": tab_id},
                timeout_seconds=int(timeout_seconds),
            )
            return result.get("data") or result

        # Fallback: HTTP polling (legacy)
        command = self.enqueue_command(method, params=params, target_url=target_url)
        return self.wait_for_result(command["id"], timeout_seconds=timeout_seconds)

    def enqueue_command(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        target_url: Optional[str] = None,
    ):
        with self._condition:
            command = {
                "id": str(self._next_command_id),
                "method": method,
                "params": params or {},
                "targetUrl": target_url,
                "createdAt": round(time.time(), 3),
            }
            self._next_command_id += 1
            self._pending_commands.append(command)
            self._condition.notify_all()
            return command

    def pull_command(self, timeout_seconds: float = 1, page_url: Optional[str] = None):
        deadline = time.time() + max(timeout_seconds, 0)
        with self._condition:
            while True:
                for index, command in enumerate(self._pending_commands):
                    target_url = command.get("targetUrl")
                    if not target_url or self._match_reason(page_url, target_url):
                        return self._pending_commands.pop(index)
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                self._condition.wait(timeout=remaining)

    def store_command_result(self, command_id: str, result: Dict[str, Any]):
        with self._condition:
            self._command_results[str(command_id)] = result
            self._condition.notify_all()
        return {"accepted": True, "commandId": str(command_id)}

    def wait_for_result(self, command_id: str, timeout_seconds: float = 20):
        deadline = time.time() + max(timeout_seconds, 0)
        key = str(command_id)
        with self._condition:
            while key not in self._command_results:
                remaining = deadline - time.time()
                if remaining <= 0:
                    self._pending_commands = [
                        command for command in self._pending_commands
                        if str(command.get("id")) != key
                    ]
                    return {
                        "ok": False,
                        "error": "extension command timed out",
                        "commandId": key,
                    }
                self._condition.wait(timeout=remaining)
            return self._command_results.pop(key)

    def find_hint_with_debug(self, target_url: Optional[str] = None):
        report = self._state.get("lastReport")
        debug = {
            "targetUrl": target_url,
            "targetStatusId": self._extract_x_status_id(target_url),
            "lastReportUrl": ((report or {}).get("page") or {}).get("url"),
            "lastReportMatchReason": None,
            "reportsChecked": 0,
            "matchFound": False,
            "matchReason": None,
            "matchedReportIndexFromEnd": None,
        }
        if not report:
            return None, debug

        if not target_url:
            debug["matchFound"] = True
            debug["matchReason"] = "no_target_url_use_last_report"
            return report, debug

        reason = self._match_reason(((report.get("page") or {}).get("url")), target_url)
        debug["lastReportMatchReason"] = reason
        if reason:
            debug["matchFound"] = True
            debug["matchReason"] = reason
            debug["matchedReportIndexFromEnd"] = 0
            return report, debug

        reports = self._state.get("reports") or []
        checked = 0
        for idx, item in enumerate(reversed(reports), start=1):
            checked = idx
            item_page = item.get("page") or {}
            reason = self._match_reason(item_page.get("url"), target_url)
            if reason:
                debug["reportsChecked"] = checked
                debug["matchFound"] = True
                debug["matchReason"] = reason
                debug["matchedReportIndexFromEnd"] = idx - 1
                return item, debug

        debug["reportsChecked"] = checked
        return None, debug

    def _extract_x_status_id(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        try:
            parsed = urlparse(url)
            if "x.com" not in parsed.netloc and "twitter.com" not in parsed.netloc:
                return None
            parts = [p for p in parsed.path.split("/") if p]
            if "status" in parts:
                idx = parts.index("status")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        except Exception:
            return None
        return None

    def _normalize_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip("/")
            if not path:
                path = "/"
            query = f"?{parsed.query}" if parsed.query else ""
            return f"{parsed.scheme}://{parsed.netloc}{path}{query}"
        except Exception:
            return url

    def _match_reason(self, report_url: Optional[str], target_url: Optional[str]) -> Optional[str]:
        if not report_url or not target_url:
            return None
        if self._normalize_url(report_url) == self._normalize_url(target_url):
            return "exact_url"
        report_status_id = self._extract_x_status_id(report_url)
        target_status_id = self._extract_x_status_id(target_url)
        if report_status_id and target_status_id and report_status_id == target_status_id:
            return "x_status_id"
        return None
