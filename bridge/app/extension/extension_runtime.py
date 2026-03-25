import threading
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse


class ExtensionRuntime:
    def __init__(self):
        self._state = {"lastReport": None, "reports": []}
        self._condition = threading.Condition()
        self._next_command_id = 1
        self._pending_commands = []
        self._command_results = {}

    def get_state(self) -> Dict[str, Any]:
        return self._state

    def store_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        self._state["lastReport"] = report
        self._state["reports"].append(report)
        self._state["reports"] = self._state["reports"][-120:]
        return {"accepted": True}

    def get_hint(self, target_url: Optional[str] = None):
        report, _ = self.find_hint_with_debug(target_url)
        return report

    def invoke(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 20,
        target_url: Optional[str] = None,
    ):
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
            return f"{parsed.scheme}://{parsed.netloc}{path}"
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
