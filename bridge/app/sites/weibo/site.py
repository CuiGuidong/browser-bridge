from .models import ACTION_KINDS, READ_KINDS, SITE_ID, WORKFLOWS
from ..common_workflows import run_account_status, run_url_read
from .workflows.read_home import run as run_read_home
from .workflows.read_hot_feed import run as run_read_hot_feed
from .workflows.read_hot_search import run as run_read_hot_search
from .workflows.read_post import run as run_read_post
from .workflows.search import run as run_search


class WeiboSite:
    site_id = SITE_ID
    hosts = {"weibo.com", "www.weibo.com", "s.weibo.com", "m.weibo.cn", "mapp.api.weibo.cn"}
    home_url = "https://weibo.com/"

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
        if workflow == "read_hot_feed":
            return run_read_hot_feed(
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "read_hot_search":
            return run_read_hot_search(
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
        if workflow == "read_profile_metrics":
            params = params or {}
            url = (params.get("url") or "").strip()
            user_id = (params.get("userId") or params.get("uid") or "").strip()
            screen_name = (params.get("screenName") or params.get("handle") or "").strip()
            if not url and user_id:
                url = f"https://weibo.com/u/{user_id}"
            if not url and screen_name:
                url = f"https://weibo.com/n/{screen_name}"
            return run_url_read(
                site=self.site_id,
                workflow=workflow,
                kind=workflow,
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params={"url": url},
                timeout_seconds=timeout_seconds,
                reuse_domain="weibo.com",
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
                reuse_domain="weibo.com",
            )
        return {
            "ok": False,
            "site": self.site_id,
            "workflow": workflow,
            "error": "workflow not supported",
        }
