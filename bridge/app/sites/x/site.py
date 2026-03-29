from .models import ACTION_KINDS, READ_KINDS, SITE_ID, WORKFLOWS
from .workflows.add_bookmark import run as run_add_bookmark
from .workflows.follow_user import run as run_follow_user
from .workflows.list_bookmarks import run as run_list_bookmarks
from .workflows.read_home import run as run_read_home
from .workflows.read_post import run as run_read_post
from .workflows.remove_bookmark import run as run_remove_bookmark
from .workflows.search import run as run_search
from .workflows.unfollow_user import run as run_unfollow_user


class XSite:
    site_id = SITE_ID
    hosts = {"x.com", "twitter.com"}

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
        if workflow == "list_bookmarks":
            return run_list_bookmarks(
                read_service=read_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "read_home":
            return run_read_home(
                read_service=read_service,
                action_service=action_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "follow_user":
            return run_follow_user(
                action_service=action_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "unfollow_user":
            return run_unfollow_user(
                action_service=action_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "add_bookmark":
            return run_add_bookmark(
                action_service=action_service,
                browser_runtime=browser_runtime,
                target_id=target_id,
                params=params,
                timeout_seconds=timeout_seconds,
            )
        if workflow == "remove_bookmark":
            return run_remove_bookmark(
                action_service=action_service,
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
