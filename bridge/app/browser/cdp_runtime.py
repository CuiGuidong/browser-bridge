from ..native_browser_runtime import NativeBrowserRuntime


class CdpRuntime:
    """Browser runtime facade. Delegates all operations to NativeBrowserRuntime."""

    def __init__(self, native_session_manager=None, site_registry=None):
        self._native_sm = native_session_manager
        self._site_registry = site_registry
        self._native_runtime = None

    def _get_native_runtime(self):
        if self._native_runtime is None:
            self._native_runtime = NativeBrowserRuntime(self._native_sm, site_registry=self._site_registry)
        return self._native_runtime

    def get_version(self):
        return self._get_native_runtime().get_version()

    def list_tabs(self):
        return self._get_native_runtime().list_tabs()

    def open_or_reuse_url(self, url, reuse_existing_tab=False, reuse_domain=None):
        return self._get_native_runtime().open_or_reuse_url(url, reuse_existing_tab=reuse_existing_tab, reuse_domain=reuse_domain)

    def open_new_url(self, url):
        return self._get_native_runtime().open_new_url(url)

    def activate_tab(self, target_id):
        return self._get_native_runtime().activate_tab(target_id)

    def navigate_tab(self, target_id, url):
        return self._get_native_runtime().navigate_tab(target_id, url)

    def reload_tab(self, target_id):
        return self._get_native_runtime().reload_tab(target_id)

    def close_tab(self, target_id):
        return self._get_native_runtime().close_tab(target_id)

    def wait_for_page(self, target_id=None, timeout_seconds=10, interval_seconds=0.5):
        return self._get_native_runtime().wait_for_page(target_id, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)

    def get_page_info(self, target_id=None):
        return self._get_native_runtime().get_page_info(target_id)

    def get_page_content(self, target_id=None, max_chars=4000):
        return self._get_native_runtime().get_page_content(target_id, max_chars=max_chars)

    def probe_page_readiness(self, target_id=None, timeout_seconds=15, interval_seconds=1, selector=None):
        return self._get_native_runtime().probe_page_readiness(target_id, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds, selector=selector)

    def capture_screenshot(self, target_id=None, fmt="png"):
        return self._get_native_runtime().capture_screenshot(target_id, fmt=fmt)

    def query_elements(self, selector, target_id=None, limit=20):
        return self._get_native_runtime().query_elements(selector, target_id=target_id, limit=limit)

    def execute_js(self, expression, target_id=None):
        return self._get_native_runtime().execute_js(expression, target_id)

    def set_file_input_files_by_selector(self, target_id, selector, files):
        return self._get_native_runtime().set_file_input_files_by_selector(target_id, selector, files)
