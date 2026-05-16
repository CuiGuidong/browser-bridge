from .models import ACTION_KINDS, READ_KINDS, SITE_ID, WORKFLOWS
from ..common_workflows import run_account_status
from .workflows.prepare_publish_post import run as run_prepare_publish_post
from .workflows.read_home import run as run_read_home
from .workflows.read_post_metrics import run as run_read_post_metrics
from .workflows.read_post import run as run_read_post
from .workflows.read_profile_metrics import run as run_read_profile_metrics
from .workflows.search import run as run_search


class XiaohongshuSite:
    site_id = SITE_ID
    hosts = {"xiaohongshu.com"}
    home_url = "https://www.xiaohongshu.com/"

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
        if workflow == "read_home":
            return run_read_home(
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
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
        if workflow == "prepare_publish_post":
            return run_prepare_publish_post(
                read_service=read_service,
                action_service=action_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "read_post_metrics":
            return run_read_post_metrics(
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "read_profile_metrics":
            return run_read_profile_metrics(
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
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
                reuse_domain="xiaohongshu.com",
            )
        return {
            "ok": False,
            "site": self.site_id,
            "workflow": workflow,
            "error": "workflow not supported",
        }
