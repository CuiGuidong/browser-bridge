import json
import threading
import time
from pathlib import Path
from urllib.parse import urlparse


class ActionService:
    def __init__(self, browser_runtime, extension_runtime, site_registry=None):
        self.browser_runtime = browser_runtime
        self.extension_runtime = extension_runtime
        self.site_registry = site_registry
        self._state_change_actions = {
            ("x", "add_bookmark"),
            ("x", "remove_bookmark"),
            ("x", "follow_user"),
            ("x", "unfollow_user"),
        }
        self._last_state_change_at = {}
        self._state_change_interval_seconds = 2.5
        self._log_lock = threading.Lock()
        self._action_log_path = Path(__file__).resolve().parents[3] / "temp" / "x-state-actions.jsonl"

    def health(self):
        version = self.browser_runtime.get_version()
        return {
            "bridge": "alive",
            "cdp": "connected",
            "browser": version.get("Browser"),
            "protocolVersion": version.get("Protocol-Version"),
        }

    def version(self):
        return self.browser_runtime.get_version()

    def tabs(self):
        return self.browser_runtime.list_tabs()

    def open_url(self, url, reuse_existing_tab=False, reuse_domain=None):
        return self.browser_runtime.open_or_reuse_url(
            url,
            reuse_existing_tab=reuse_existing_tab,
            reuse_domain=reuse_domain,
        )

    def activate(self, target_id):
        return self.browser_runtime.activate_tab(target_id)

    def wait(self, target_id=None, timeout_seconds=10, interval_seconds=0.5):
        return self.browser_runtime.wait_for_page(
            target_id=target_id,
            timeout_seconds=timeout_seconds,
            interval_seconds=interval_seconds,
        )

    def page_info(self, target_id=None):
        return self.browser_runtime.get_page_info(target_id)

    def page_content(self, target_id=None, max_chars=4000):
        return self.browser_runtime.get_page_content(target_id, max_chars=max_chars)

    def screenshot(self, target_id=None, fmt="png"):
        return self.browser_runtime.capture_screenshot(target_id=target_id, fmt=fmt)

    def query(self, selector, target_id=None, limit=20):
        return self.browser_runtime.query_elements(selector, target_id=target_id, limit=limit)

    def evaluate(self, expression, target_id=None):
        return self.browser_runtime.execute_js(expression, target_id=target_id)

    def store_extension_report(self, report):
        return self.extension_runtime.store_report(report)

    def extension_state(self):
        return self.extension_runtime.get_state()

    def pull_extension_command(self, timeout_seconds=1, page_url=None):
        return self.extension_runtime.pull_command(
            timeout_seconds=timeout_seconds,
            page_url=page_url,
        )

    def store_extension_result(self, command_id, result):
        return self.extension_runtime.store_command_result(command_id, result)

    def _site_mismatch_result(self, site, page):
        page = page or {}
        return {
            "ok": False,
            "source": "bridge",
            "error": "No matching adapter",
            "site": page.get("site") or urlparse(page.get("url") or "").hostname,
            "requestedSite": site,
            "page": {
                "url": page.get("url"),
                "title": page.get("title"),
                "hostname": urlparse(page.get("url") or "").hostname,
            },
        }

    def _resolve_site_page(self, site_module, target_id=None):
        page = self.browser_runtime.get_page_info(target_id)
        if page is None or site_module is None:
            return page, False
        hostname = (urlparse(page.get("url") or "").hostname or "").lower()
        hosts = {host.lower() for host in getattr(site_module, "hosts", set())}
        matched = hostname in hosts or any(hostname.endswith(f".{host}") for host in hosts)
        return page, matched

    def _refresh_target_context(self, site_module, site, target_id=None):
        if not target_id:
            return {
                "page": None,
                "matched": True,
                "targetUrl": None,
                "mismatch": None,
            }
        self.browser_runtime.activate_tab(target_id)
        page, matched = self._resolve_site_page(site_module, target_id=target_id)
        mismatch = None
        if site_module and page and not matched:
            mismatch = self._site_mismatch_result(site, page)
        return {
            "page": page,
            "matched": matched,
            "targetUrl": (page or {}).get("url"),
            "mismatch": mismatch,
        }

    def _should_retry_runtime(self, runtime):
        if not runtime or runtime.get("ok"):
            return False
        error = (runtime.get("error") or "").strip()
        return error in {"extension command timed out", "No matching adapter"}

    def _is_state_changing(self, site, kind):
        return (site, kind) in self._state_change_actions

    def _throttle_state_change(self, site, kind):
        key = f"{site}:{kind}"
        now = time.time()
        last = self._last_state_change_at.get(key)
        if last is not None:
            remaining = self._state_change_interval_seconds - (now - last)
            if remaining > 0:
                time.sleep(remaining)
        self._last_state_change_at[key] = time.time()

    def _build_restore_hint(self, site, kind, params, result):
        if site == "x" and kind == "remove_bookmark":
            return {
                "kind": "add_bookmark",
                "url": (params or {}).get("url") or ((result or {}).get("before") or {}).get("url"),
            }
        if site == "x" and kind == "follow_user":
            return {
                "kind": "unfollow_user",
                "handle": (params or {}).get("handle"),
            }
        if site == "x" and kind == "unfollow_user":
            return {
                "kind": "follow_user",
                "handle": (params or {}).get("handle"),
            }
        return None

    def _log_state_change(self, site, kind, params, result, target_id=None):
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
            "site": site,
            "kind": kind,
            "targetId": target_id,
            "params": params or {},
            "result": {
                "ok": bool((result or {}).get("ok")),
                "source": (result or {}).get("source"),
                "changed": (result or {}).get("changed"),
                "verified": (result or {}).get("verified"),
                "page": (result or {}).get("page"),
                "before": (result or {}).get("before"),
                "after": (result or {}).get("after"),
                "error": (result or {}).get("error"),
            },
            "restoreHint": self._build_restore_hint(site, kind, params, result),
        }
        self._action_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_lock:
            with self._action_log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def site_action(self, site, kind, params=None, target_id=None, timeout_seconds=20):
        params = params or {}
        site_module = self.site_registry.get(site) if (self.site_registry and site) else None
        target_url = None
        if target_id:
            context = self._refresh_target_context(site_module, site, target_id=target_id)
            if site_module and context.get("page") and not context.get("matched"):
                return self._site_mismatch_result(site, context.get("page"))
            target_url = context.get("targetUrl")
        if self._is_state_changing(site, kind):
            self._throttle_state_change(site, kind)

        current_target_url = target_url
        if target_id:
            context = self._refresh_target_context(site_module, site, target_id=target_id)
            if site_module and context.get("page") and not context.get("matched"):
                return self._site_mismatch_result(site, context.get("page"))
            current_target_url = context.get("targetUrl")
        action_result = self.extension_runtime.invoke(
            "act",
            {"kind": kind, **params},
            timeout_seconds=timeout_seconds,
            target_url=current_target_url,
            target_id=target_id,
            site=site,
        )
        retried_act = False
        if target_id and self._should_retry_runtime(action_result):
            time.sleep(0.5)
            context = self._refresh_target_context(site_module, site, target_id=target_id)
            if site_module and context.get("page") and not context.get("matched"):
                mismatch_result = self._site_mismatch_result(site, context.get("page"))
                mismatch_result["debug"] = {
                    **(mismatch_result.get("debug") or {}),
                    "retriedAfterTargetRefresh": True,
                }
                return mismatch_result
            retry_target_url = context.get("targetUrl")
            action_result = self.extension_runtime.invoke(
                "act",
                {"kind": kind, **params},
                timeout_seconds=timeout_seconds,
                target_url=retry_target_url,
                target_id=target_id,
                site=site,
            )
            current_target_url = retry_target_url
            retried_act = True
        if action_result.get("ok"):
            verify_target_url = current_target_url
            if target_id:
                context = self._refresh_target_context(site_module, site, target_id=target_id)
                if site_module and context.get("page") and not context.get("matched"):
                    return self._site_mismatch_result(site, context.get("page"))
                verify_target_url = context.get("targetUrl")
            verify_result = self.extension_runtime.invoke(
                "verify",
                {
                    "kind": kind,
                    **params,
                    "actionResult": action_result,
                },
                timeout_seconds=timeout_seconds,
                target_url=verify_target_url,
                target_id=target_id,
                site=site,
            )
            retried_verify = False
            if target_id and self._should_retry_runtime(verify_result):
                time.sleep(0.5)
                context = self._refresh_target_context(site_module, site, target_id=target_id)
                if site_module and context.get("page") and not context.get("matched"):
                    mismatch_result = self._site_mismatch_result(site, context.get("page"))
                    mismatch_result["debug"] = {
                        **(mismatch_result.get("debug") or {}),
                        "retriedAfterTargetRefresh": retried_act,
                        "retriedVerifyAfterTargetRefresh": True,
                    }
                    return mismatch_result
                retry_target_url = context.get("targetUrl")
                verify_result = self.extension_runtime.invoke(
                    "verify",
                    {
                        "kind": kind,
                        **params,
                        "actionResult": action_result,
                    },
                    timeout_seconds=timeout_seconds,
                    target_url=retry_target_url,
                    target_id=target_id,
                    site=site,
                )
                retried_verify = True
            action_result["source"] = "extension-semantic"
            action_result["verified"] = verify_result.get("verified")
            action_result["after"] = verify_result.get("after") or action_result.get("after") or {}
            action_result["debug"] = {
                "verify": verify_result,
                "retriedAfterTargetRefresh": retried_act,
                "retriedVerifyAfterTargetRefresh": retried_verify,
            }
            final_result = action_result
        else:
            if retried_act:
                action_result["debug"] = {
                    **(action_result.get("debug") or {}),
                    "retriedAfterTargetRefresh": True,
                }
            final_result = action_result

        if self._is_state_changing(site, kind):
            self._log_state_change(site, kind, params, final_result, target_id=target_id)
        return final_result
