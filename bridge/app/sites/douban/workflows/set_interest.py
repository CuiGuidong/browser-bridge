import re
from urllib.parse import urlparse

from .common import close_temporary_tab, open_douban_page, response_target_id
from ..models import INTEREST_VALUES


def _is_subject_url(url):
    try:
        parsed = urlparse(url or "")
    except Exception:
        return False
    hostname = (parsed.hostname or "").lower()
    if hostname != "movie.douban.com":
        return False
    return re.fullmatch(r"/subject/\d+/?", parsed.path or "") is not None


def run(action_service, browser_runtime, target_id=None, params=None, timeout_seconds=20):
    params = params or {}
    url = str(params.get("url") or "").strip()
    interest = str(params.get("interest") or "").strip()
    if interest not in INTEREST_VALUES:
        return {
            "ok": False,
            "site": "douban",
            "workflow": "set_interest",
            "error": "invalid_interest",
        }
    if not url:
        return {
            "ok": False,
            "site": "douban",
            "workflow": "set_interest",
            "error": "url is required",
        }
    if not _is_subject_url(url):
        return {
            "ok": False,
            "site": "douban",
            "workflow": "set_interest",
            "error": "subject url is required",
        }
    if action_service is None:
        return {
            "ok": False,
            "site": "douban",
            "workflow": "set_interest",
            "error": "action service not bound",
        }

    resolved_target_id, opened = open_douban_page(browser_runtime, url=url or None, target_id=target_id)
    if not resolved_target_id:
        return {
            "ok": False,
            "site": "douban",
            "workflow": "set_interest",
            "error": "failed to open page",
        }
    try:
        action_result = action_service.site_action(
            "douban",
            "set_interest",
            params={"url": url, "interest": interest},
            target_id=resolved_target_id,
            timeout_seconds=timeout_seconds,
        )
        action_result["workflow"] = "set_interest"
        action_result["targetId"] = response_target_id(opened, resolved_target_id)
        action_result["debug"] = {
            "open": opened,
            **(action_result.get("debug") or {}),
        }
        return action_result
    finally:
        close_temporary_tab(browser_runtime, opened, resolved_target_id)
