from ..cdp_service import BrowserBridgeService
from ..config import BROWSER_RUNTIME


class CdpRuntime:
    def __init__(self, service=None, native_session_manager=None):
        self._service = service or BrowserBridgeService()
        self._native_session_manager = native_session_manager
        self._native_runtime = None

    def _use_native(self):
        """Check if we should use the native runtime."""
        if BROWSER_RUNTIME == "cdp_only":
            return False
        if BROWSER_RUNTIME == "native_only":
            return True
        # auto: prefer native if session available
        if self._native_session_manager and self._native_session_manager.get_active_session():
            return True
        return False

    def _get_native_runtime(self):
        if self._native_runtime is None:
            from ..native_browser_runtime import NativeBrowserRuntime
            self._native_runtime = NativeBrowserRuntime(self._native_session_manager)
        return self._native_runtime

    def _delegate(self, method_name, *args, **kwargs):
        if self._use_native():
            rt = self._get_native_runtime()
            return getattr(rt, method_name)(*args, **kwargs)
        return getattr(self._service, method_name)(*args, **kwargs)

    def get_version(self):
        if self._use_native():
            return self._get_native_runtime().get_version()
        return self._service.get_version()

    def list_tabs(self):
        return self._delegate("list_tabs")

    def open_or_reuse_url(self, url, reuse_existing_tab=False, reuse_domain=None):
        if self._use_native():
            return self._get_native_runtime().open_or_reuse_url(url, reuse_existing_tab=reuse_existing_tab, reuse_domain=reuse_domain)
        return self._service.open_or_reuse_url(url, reuse_existing_tab=reuse_existing_tab, reuse_domain=reuse_domain)

    def activate_tab(self, target_id):
        return self._delegate("activate_tab", target_id)

    def navigate_tab(self, target_id, url):
        return self._delegate("navigate_tab", target_id, url)

    def reload_tab(self, target_id):
        return self._delegate("reload_tab", target_id)

    def close_tab(self, target_id):
        return self._delegate("close_tab", target_id)

    def wait_for_page(self, target_id=None, timeout_seconds=10, interval_seconds=0.5):
        return self._delegate("wait_for_page", target_id, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)

    def get_page_info(self, target_id=None):
        return self._delegate("get_page_info", target_id)

    def get_page_content(self, target_id=None, max_chars=4000):
        return self._delegate("get_page_content", target_id, max_chars=max_chars)

    def probe_page_readiness(self, target_id=None, timeout_seconds=15, interval_seconds=1, selector=None):
        return self._delegate("probe_page_readiness", target_id, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds, selector=selector)

    def capture_screenshot(self, target_id=None, fmt="png"):
        return self._delegate("capture_screenshot", target_id, fmt=fmt)

    def query_elements(self, selector, target_id=None, limit=20):
        return self._delegate("query_elements", selector, target_id=target_id, limit=limit)

    def execute_js(self, expression, target_id=None):
        return self._delegate("execute_js", expression, target_id)

    def set_file_input_files_by_selector(self, target_id, selector, files):
        return self._delegate("set_file_input_files_by_selector", target_id, selector, files)
