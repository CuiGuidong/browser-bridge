from .models import ACTION_KINDS, READ_KINDS, SITE_ID, WORKFLOWS
from .workflows.read_home import run as run_read_home
from .workflows.read_post import run as run_read_post
from .workflows.search import run as run_search


class XiaohongshuSite:
    site_id = SITE_ID
    hosts = {"xiaohongshu.com"}

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
        return {
            "ok": False,
            "site": self.site_id,
            "workflow": workflow,
            "error": "workflow not supported",
        }
