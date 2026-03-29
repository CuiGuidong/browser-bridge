import time
from urllib.parse import urlparse


class ReadService:
    def __init__(self, browser_runtime, extension_runtime, site_registry=None):
        self.browser_runtime = browser_runtime
        self.extension_runtime = extension_runtime
        self.site_registry = site_registry

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

    def probe_readiness(
        self,
        target_id=None,
        timeout_seconds=15,
        interval_seconds=1,
        selector=None,
        prefer_extension=True,
    ):
        page = self.browser_runtime.get_page_info(target_id)
        if page is None:
            return None
        extension_hint = self.extension_runtime.get_hint(page.get("url")) if prefer_extension else None
        if extension_hint:
            return {
                "source": "extension",
                "ready": bool((extension_hint.get("signals") or {}).get("ready")),
                "page": extension_hint.get("page"),
                "signals": extension_hint.get("signals"),
                "content": extension_hint.get("content"),
            }
        result = self.browser_runtime.probe_page_readiness(
            target_id=target_id,
            timeout_seconds=timeout_seconds,
            interval_seconds=interval_seconds,
            selector=selector,
        )
        if result is None:
            return None
        result["source"] = "cdp"
        return result

    def debug_extension_match(self, target_id=None, target_url=None):
        page = None
        resolved_url = target_url
        if not resolved_url:
            page = self.browser_runtime.get_page_info(target_id)
            if page is None:
                return None
            resolved_url = page.get("url")

        hint, debug = self.extension_runtime.find_hint_with_debug(resolved_url)
        hint_preview = None
        if hint:
            hint_page = hint.get("page") or {}
            hint_signals = hint.get("signals") or {}
            hint_content = hint.get("content") or {}
            hint_preview = {
                "page": {
                    "url": hint_page.get("url"),
                    "title": hint_page.get("title"),
                },
                "signals": {
                    "ready": hint_signals.get("ready"),
                    "isX": hint_signals.get("isX"),
                    "isTweetDetail": hint_signals.get("isTweetDetail"),
                    "isTimeline": hint_signals.get("isTimeline"),
                },
                "content": {
                    "primaryTextLength": len(hint_content.get("primaryText") or ""),
                    "timelineLength": len(hint_content.get("timeline") or []),
                },
            }

        return {
            "targetId": target_id or ((page or {}).get("id")),
            "targetUrl": resolved_url,
            "debug": debug,
            "hintFound": bool(hint),
            "hintPreview": hint_preview,
        }

    def site_capabilities(self, site=None, target_id=None):
        site_module = self.site_registry.get(site) if (self.site_registry and site) else None
        target_url = None
        if target_id:
            self.browser_runtime.activate_tab(target_id)
            page, matched = self._resolve_site_page(site_module, target_id=target_id)
            if site_module and not matched:
                return {
                    "site": site,
                    "registry": site_module.capabilities(),
                    "runtime": self._site_mismatch_result(site, page),
                }
            target_url = page.get("url") if page else None
        runtime = self.extension_runtime.invoke("capabilities", {}, timeout_seconds=10, target_url=target_url)
        return {
            "site": site or runtime.get("site"),
            "registry": site_module.capabilities() if site_module else None,
            "runtime": runtime,
        }

    def site_read(self, site, kind, params=None, target_id=None, timeout_seconds=20):
        params = params or {}
        site_module = self.site_registry.get(site) if (self.site_registry and site) else None
        target_url = None
        if target_id:
            self.browser_runtime.activate_tab(target_id)
            page, matched = self._resolve_site_page(site_module, target_id=target_id)
            if site_module and not matched:
                return self._site_mismatch_result(site, page)
            target_url = page.get("url") if page else None
        wait_for_ready = params.get("waitForReady", True)
        interval_seconds = float(params.get("intervalSeconds", 1))
        last_probe = None
        ready_observed = not wait_for_ready
        if wait_for_ready:
            started = time.time()
            while time.time() - started < timeout_seconds:
                probe = self.extension_runtime.invoke(
                    "probe_ready",
                    params,
                    timeout_seconds=min(5, timeout_seconds),
                    target_url=target_url,
                )
                last_probe = probe
                if probe.get("ok") and ((probe.get("signals") or {}).get("ready") is True):
                    ready_observed = True
                    break
                time.sleep(interval_seconds)
        if not ready_observed:
            return {
                "ok": False,
                "source": "bridge",
                "site": site,
                "kind": kind,
                "error": "page not ready before timeout",
                "page": ((last_probe or {}).get("page") or {"url": target_url}),
                "signals": (last_probe or {}).get("signals") or {},
                "content": (last_probe or {}).get("content") or {},
                "debug": {
                    "lastProbe": last_probe,
                },
            }

        runtime = self.extension_runtime.invoke(
            "read",
            {"kind": kind, **params},
            timeout_seconds=timeout_seconds,
            target_url=target_url,
        )
        if runtime.get("ok"):
            runtime["source"] = "extension-semantic"
            runtime["fallbackUsed"] = False
            return runtime
        return runtime
