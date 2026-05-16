from .common_workflows import run_account_status, run_search, run_url_read


class OpenCliInspiredReadOnlySite:
    site_id = ""
    hosts = set()
    home_url = ""
    search_url_template = ""
    search_ready_selector = None

    def capabilities(self):
        return {
            "site": self.site_id,
            "read": [
                "read_post",
                "read_profile_metrics",
                "search",
                "account_status",
            ],
            "action": [],
            "workflow": [
                "read_post",
                "read_profile_metrics",
                "search",
                "account_status",
            ],
        }

    def run_workflow(
        self,
        workflow,
        params=None,
        target_id=None,
        timeout_seconds=20,
        browser_runtime=None,
        extension_runtime=None,
        read_service=None,
        action_service=None,
    ):
        if workflow in {"read_post", "read_profile_metrics"}:
            return run_url_read(
                site=self.site_id,
                workflow=workflow,
                kind=workflow,
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
                reuse_domain=self.reuse_domain,
                ready_selector=self.search_ready_selector,
            )
        if workflow == "search":
            return run_search(
                site=self.site_id,
                search_url_template=self.search_url_template,
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
                reuse_domain=self.reuse_domain,
            )
        if workflow == "account_status":
            return run_account_status(
                site=self.site_id,
                home_url=self.home_url,
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
                reuse_domain=self.reuse_domain,
            )
        return {
            "ok": False,
            "site": self.site_id,
            "workflow": workflow,
            "error": "workflow not supported",
        }

    @property
    def reuse_domain(self):
        return next(iter(sorted(self.hosts)), None)
