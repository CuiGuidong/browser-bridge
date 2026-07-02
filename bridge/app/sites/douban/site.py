from .models import ACTION_KINDS, READ_KINDS, SITE_ID, WORKFLOWS
from ..common_workflows import run_account_status, run_url_read
from .workflows.read_post import run as run_read_post
from .workflows.search import run as run_search
from .workflows.set_interest import run as run_set_interest


class DoubanSite:
    site_id = SITE_ID
    hosts = {"douban.com"}
    home_url = "https://www.douban.com/"
    search_url_template = "https://www.douban.com/search?q={keyword}"

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
        if workflow == "read_post":
            return run_read_post(
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "search":
            return run_search(
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "set_interest":
            return run_set_interest(
                action_service=action_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "read_profile_metrics":
            params = params or {}
            return run_url_read(
                site=self.site_id,
                workflow=workflow,
                kind=workflow,
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
                reuse_domain="douban.com",
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
                reuse_domain="douban.com",
            )
        return {
            "ok": False,
            "site": self.site_id,
            "workflow": workflow,
            "error": "workflow not supported",
        }
