from ..common_workflows import run_account_status, run_search, run_url_read
from .models import ACTION_KINDS, READ_KINDS, SITE_ID, WORKFLOWS


class BilibiliSite:
    site_id = SITE_ID
    hosts = {"bilibili.com", "b23.tv"}
    home_url = "https://www.bilibili.com/"
    search_url_template = "https://search.bilibili.com/all?keyword={keyword}"

    def capabilities(self):
        return {
            "site": self.site_id,
            "read": READ_KINDS,
            "action": ACTION_KINDS,
            "workflow": WORKFLOWS,
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
                reuse_domain="bilibili.com",
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
                reuse_domain="bilibili.com",
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
                reuse_domain="bilibili.com",
            )
        return {
            "ok": False,
            "site": self.site_id,
            "workflow": workflow,
            "error": "workflow not supported",
        }
