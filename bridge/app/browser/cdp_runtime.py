from ..cdp_service import BrowserBridgeService


class CdpRuntime:
    def __init__(self, service=None):
        self._service = service or BrowserBridgeService()

    def get_version(self):
        return self._service.get_version()

    def list_tabs(self):
        return self._service.list_tabs()

    def open_or_reuse_url(self, url, reuse_existing_tab=False, reuse_domain=None):
        return self._service.open_or_reuse_url(
            url,
            reuse_existing_tab=reuse_existing_tab,
            reuse_domain=reuse_domain,
        )

    def activate_tab(self, target_id):
        return self._service.activate_tab(target_id)

    def navigate_tab(self, target_id, url):
        return self._service.navigate_tab(target_id, url)

    def close_tab(self, target_id):
        return self._service.close_tab(target_id)

    def wait_for_page(self, target_id=None, timeout_seconds=10, interval_seconds=0.5):
        return self._service.wait_for_page(
            target_id=target_id,
            timeout_seconds=timeout_seconds,
            interval_seconds=interval_seconds,
        )

    def get_page_info(self, target_id=None):
        return self._service.get_page_info(target_id)

    def get_page_content(self, target_id=None, max_chars=4000):
        return self._service.get_page_content(target_id, max_chars=max_chars)

    def probe_page_readiness(self, target_id=None, timeout_seconds=15, interval_seconds=1, selector=None):
        return self._service.probe_page_readiness(
            target_id=target_id,
            timeout_seconds=timeout_seconds,
            interval_seconds=interval_seconds,
            selector=selector,
        )

    def capture_screenshot(self, target_id=None, fmt="png"):
        return self._service.capture_screenshot(target_id=target_id, fmt=fmt)

    def query_elements(self, selector, target_id=None, limit=20):
        return self._service.query_elements(selector, target_id=target_id, limit=limit)

    def execute_js(self, expression, target_id=None):
        return self._service.execute_js(expression, target_id=target_id)

    def set_file_input_files_by_selector(self, target_id, selector, files):
        return self._service.set_file_input_files_by_selector(
            target_id=target_id,
            selector=selector,
            files=files,
        )
