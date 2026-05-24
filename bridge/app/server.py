from fastapi import FastAPI, Query, HTTPException, Response, Request, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import time
import uvicorn
import os

from .upload_tokens import get_upload_token, remove_upload_token


from .application.action_service import ActionService
from .application.login_service import LoginService
from .application.read_service import ReadService
from .application.workflow_service import WorkflowService
from .browser.cdp_runtime import CdpRuntime
from .config import BRIDGE_HOST, BRIDGE_PORT
from .extension.extension_runtime import ExtensionRuntime
from .native_session_manager import NativeSessionManager
from .notifications import NotificationService
from .playwright_client import get_playwright_client, reset_playwright_client
from .schemas import fail, ok
from .sites.registry import SiteRegistry
from .sites.aibase.site import AibaseSite
from .sites.ali1688.site import Ali1688Site
from .sites.bilibili.site import BilibiliSite
from .sites.bloomberg.site import BloombergSite
from .sites.douban.site import DoubanSite
from .sites.douyin.site import DouyinSite
from .sites.eastmoney.site import EastmoneySite
from .sites.dianping.site import DianpingSite
from .sites.google.site import GoogleSite
from .sites.gov_cn.site import GovCnSite
from .sites.grok.site import GrokSite
from .sites.hackernews.site import HackerNewsSite
from .sites.hupu.site import HupuSite
from .sites.instagram.site import InstagramSite
from .sites.imdb.site import ImdbSite
from .sites.jd.site import JdSite
from .sites.linux_do.site import LinuxDoSite
from .sites.reddit.site import RedditSite
from .sites.site36kr.site import Site36krSite
from .sites.smzdm.site import SmzdmSite
from .sites.taobao.site import TaobaoSite
from .sites.tieba.site import TiebaSite
from .sites.v2ex.site import V2exSite
from .sites.weibo.site import WeiboSite
from .sites.weixin.site import WeixinSite
from .sites.wikipedia.site import WikipediaSite
from .sites.x.site import XSite
from .sites.xiaohongshu.site import XiaohongshuSite
from .sites.xianyu.site import XianyuSite
from .sites.xueqiu.site import XueqiuSite
from .sites.youtube.site import YoutubeSite
from .sites.zhihu.site import ZhihuSite


app = FastAPI(title="Browser Bridge API", version="1.0.0")
notification_service = NotificationService()
native_session_manager = NativeSessionManager()
site_registry = SiteRegistry()
browser_runtime = CdpRuntime(native_session_manager=native_session_manager, site_registry=site_registry)
extension_runtime = ExtensionRuntime(native_session_manager=native_session_manager, site_registry=site_registry)
site_registry.register("weibo", WeiboSite())
site_registry.register("x", XSite())
site_registry.register("xiaohongshu", XiaohongshuSite())
site_registry.register("zhihu", ZhihuSite())
site_registry.register("bilibili", BilibiliSite())
site_registry.register("douyin", DouyinSite())
site_registry.register("reddit", RedditSite())
site_registry.register("youtube", YoutubeSite())
site_registry.register("weixin", WeixinSite())
site_registry.register("douban", DoubanSite())
site_registry.register("hackernews", HackerNewsSite())
site_registry.register("instagram", InstagramSite())
site_registry.register("xueqiu", XueqiuSite())
site_registry.register("eastmoney", EastmoneySite())
site_registry.register("1688", Ali1688Site())
site_registry.register("36kr", Site36krSite())
site_registry.register("tieba", TiebaSite())
site_registry.register("aibase", AibaseSite())
site_registry.register("bloomberg", BloombergSite())
site_registry.register("dianping", DianpingSite())
site_registry.register("google", GoogleSite())
site_registry.register("gov.cn", GovCnSite())
site_registry.register("grok", GrokSite())
site_registry.register("hupu", HupuSite())
site_registry.register("imdb", ImdbSite())
site_registry.register("jd", JdSite())
site_registry.register("linux-do", LinuxDoSite())
site_registry.register("v2ex", V2exSite())
site_registry.register("smzdm", SmzdmSite())
site_registry.register("taobao", TaobaoSite())
site_registry.register("wikipedia", WikipediaSite())
site_registry.register("xianyu", XianyuSite())
read_service = ReadService(browser_runtime, extension_runtime, site_registry=site_registry)
action_service = ActionService(browser_runtime, extension_runtime, site_registry=site_registry)
workflow_service = WorkflowService(browser_runtime, extension_runtime, site_registry=site_registry)
workflow_service.bind_read_service(read_service)
workflow_service.bind_action_service(action_service)
login_service = LoginService(workflow_service, notification_service)
playwright_client = get_playwright_client()


# Request/Response models
class OpenRequest(BaseModel):
    url: str
    reuseExistingTab: bool = False
    reuseDomain: Optional[str] = None


class ActivateRequest(BaseModel):
    targetId: str


class ScreenshotRequest(BaseModel):
    targetId: Optional[str] = None
    format: str = "png"


class EvaluateRequest(BaseModel):
    expression: str
    targetId: Optional[str] = None



class SiteReadRequest(BaseModel):
    site: str
    kind: str
    params: Dict[str, Any] = {}
    targetId: Optional[str] = None
    timeoutSeconds: float = 20


class SiteActionRequest(BaseModel):
    site: str
    kind: str
    params: Dict[str, Any] = {}
    targetId: Optional[str] = None
    timeoutSeconds: float = 20


class WorkflowRunRequest(BaseModel):
    site: str
    workflow: str
    params: Dict[str, Any] = {}
    targetId: Optional[str] = None
    timeoutSeconds: float = 20


class LoginCheckRequest(BaseModel):
    site: Optional[str] = None
    sites: List[str] = []
    targetId: Optional[str] = None
    notify: bool = False
    timeoutSeconds: float = 20


class DevReloadExtensionRequest(BaseModel):
    reloadPages: bool = True
    targetIds: Optional[List[str]] = None
    siteHosts: List[str] = [
        "x.com",
        "twitter.com",
        "weibo.com",
        "m.weibo.cn",
        "xiaohongshu.com",
        "www.xiaohongshu.com",
        "zhihu.com",
        "www.zhihu.com",
        "bilibili.com",
        "www.bilibili.com",
        "douyin.com",
        "www.douyin.com",
        "reddit.com",
        "www.reddit.com",
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "mp.weixin.qq.com",
        "weixin.sogou.com",
        "douban.com",
        "www.douban.com",
        "news.ycombinator.com",
        "hn.algolia.com",
        "instagram.com",
        "www.instagram.com",
        "xueqiu.com",
        "eastmoney.com",
        "eastmoney.cn",
        "1688.com",
        "36kr.com",
        "tieba.baidu.com",
        "aibase.com",
        "bloomberg.com",
        "dianping.com",
        "google.com",
        "gov.cn",
        "grok.com",
        "x.ai",
        "hupu.com",
        "imdb.com",
        "jd.com",
        "360buy.com",
        "linux.do",
        "v2ex.com",
        "smzdm.com",
        "taobao.com",
        "tmall.com",
        "wikipedia.org",
        "goofish.com",
        "xianyu.taobao.com",
    ]
    timeoutSeconds: float = 5
    delaySeconds: float = 0.8


def _host_matches(url, hosts):
    hostname = (urlparse(url or "").hostname or "").lower()
    for host in hosts or []:
        host = (host or "").lower()
        if hostname == host or hostname.endswith(f".{host}"):
            return True
    return False


def _reload_dev_pages(target_ids=None, site_hosts=None):
    tabs = browser_runtime.list_tabs()
    selected = []
    target_id_set = set(target_ids or [])
    for tab in tabs:
        if target_id_set:
            if tab.get("id") in target_id_set:
                selected.append(tab)
            continue
        if _host_matches(tab.get("url"), site_hosts or []):
            selected.append(tab)

    results = []
    for tab in selected:
        result = browser_runtime.reload_tab(tab.get("id"))
        if result:
            results.append(result)
    return results


def _error_message(value):
    if isinstance(value, dict):
        return value.get("message") or value.get("error") or str(value)
    if value is None:
        return "unknown error"
    return str(value)


def _workflow_error_code(result):
    message = _error_message((result or {}).get("error")).lower()
    if "site not supported" in message:
        return "site_not_supported"
    if "workflow not supported" in message or "not supported" in message:
        return "capability_missing"
    if "login" in message:
        return "login_required"
    if "human" in message or "manual" in message or "confirm" in message:
        return "human_confirmation_required"
    return "workflow_failed"


def _workflow_failure_response(result, fallback_message="workflow failed"):
    result = result or {}
    message = _error_message(result.get("error") or fallback_message)
    detail = {
        key: value
        for key, value in result.items()
        if key not in {"ok", "error"}
    }
    return fail("workflow-run", _workflow_error_code(result), message, detail=detail)


def _capability_missing(action, site, kind, supported):
    return fail(
        action,
        "capability_missing",
        f"{kind} not supported",
        detail={
            "site": site,
            "kind": kind,
            "supported": supported,
        },
    )


def _site_not_supported(action, site):
    return fail(
        action,
        "site_not_supported",
        "site not supported",
        detail={
            "site": site,
            "supportedSites": site_registry.list_sites(),
        },
    )


def _site_error_code(result):
    message = _error_message((result or {}).get("error")).lower()
    if "site not supported" in message:
        return "site_not_supported"
    if "unsupported" in message or "not supported" in message or "no matching adapter" in message:
        return "capability_missing"
    if "login" in message:
        return "login_required"
    if "human" in message or "manual" in message or "confirm" in message:
        return "human_confirmation_required"
    return "workflow_failed"


def _site_failure_response(action, result, fallback_message):
    result = result or {}
    message = _error_message(result.get("error") or fallback_message)
    detail = {
        key: value
        for key, value in result.items()
        if key not in {"ok", "error"}
    }
    return fail(action, _site_error_code(result), message, detail=detail)


@app.get("/health")
def health():
    try:
        return ok("health", action_service.health())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/version")
def version():
    try:
        return ok("version", action_service.version())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tabs")
def tabs():
    try:
        return ok("tabs", action_service.tabs())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/open")
def open_url(req: OpenRequest):
    try:
        result = action_service.open_url(
            req.url,
            reuse_existing_tab=req.reuseExistingTab,
            reuse_domain=req.reuseDomain,
        )
        return ok("open", result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/activate")
def activate(req: ActivateRequest):
    try:
        return ok("activate", action_service.activate(req.targetId))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wait")
def wait(
    targetId: Optional[str] = Query(None),
    timeoutSeconds: float = Query(10),
    intervalSeconds: float = Query(0.5),
):
    try:
        result = action_service.wait(
            target_id=targetId,
            timeout_seconds=timeoutSeconds,
            interval_seconds=intervalSeconds,
        )
        return ok("wait", result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/page-info")
def page_info(targetId: Optional[str] = Query(None)):
    try:
        info = action_service.page_info(targetId)
        if info is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("page-info", info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/page-content")
def page_content(targetId: Optional[str] = Query(None), maxChars: int = Query(4000)):
    try:
        info = action_service.page_content(targetId, max_chars=maxChars)
        if info is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("page-content", info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/probe-readiness")
def probe_readiness(
    targetId: Optional[str] = Query(None),
    timeoutSeconds: float = Query(15),
    intervalSeconds: float = Query(1),
    selector: Optional[str] = Query(None),
    preferExtension: bool = Query(True),
):
    try:
        result = read_service.probe_readiness(
            target_id=targetId,
            timeout_seconds=timeoutSeconds,
            interval_seconds=intervalSeconds,
            selector=selector,
            prefer_extension=preferExtension,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("probe-readiness", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/extension/state")
def extension_get_state():
    try:
        return ok("extension-state", action_service.extension_state())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NativeSessionRegisterRequest(BaseModel):
    type: str = "extension"

class NativeSessionResultRequest(BaseModel):
    sessionId: str
    message: Dict[str, Any]

@app.post("/native/session/register")
async def native_session_register(req: NativeSessionRegisterRequest):
    session_id = native_session_manager.register_session()
    # Trigger all content scripts to re-report after new session connects
    import threading
    def _delayed_snapshot():
        import time
        import logging
        logger = logging.getLogger("bridge.server")
        time.sleep(2)  # Wait for shim to fully connect
        res = native_session_manager.send_command(session_id, "snapshot.all", timeout_seconds=15)
        if not res.get("ok"):
            logger.error(f"[SnapshotRecovery] snapshot.all failed to complete: {res.get('error')}")
        else:
            data = res.get("data") or {}
            if "error" in data:
                logger.warning(f"[SnapshotRecovery] snapshot.all returned diagnostic error: {data['error']}")
            else:
                logger.info(f"[SnapshotRecovery] snapshot.all succeeded: {data.get('reported')}/{data.get('total')} tabs reported")
    threading.Thread(target=_delayed_snapshot, daemon=True).start()
    return ok("native-session-register", {"sessionId": session_id})

@app.get("/native/session/pull")
async def native_session_pull(sessionId: str = Query(...), timeoutSeconds: int = Query(25)):
    import asyncio
    cmd = await asyncio.to_thread(native_session_manager.pull_command, sessionId, timeoutSeconds)
    return ok("native-session-pull", {"command": cmd})

@app.post("/native/session/result")
async def native_session_result(req: NativeSessionResultRequest):
    msg = req.message
    if msg.get("type") == "report":
        native_session_manager.store_report(req.sessionId, msg.get("payload", {}))
    elif "id" in msg:
        native_session_manager.store_result(msg["id"], msg)
    return ok("native-session-result", {"stored": True})

@app.get("/debug/extension-match")
def debug_extension_match(
    targetId: Optional[str] = Query(None),
    targetUrl: Optional[str] = Query(None),
):
    try:
        result = read_service.debug_extension_match(target_id=targetId, target_url=targetUrl)
        if result is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("debug-extension-match", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screenshot")
def screenshot(req: ScreenshotRequest):
    try:
        result = action_service.screenshot(target_id=req.targetId, fmt=req.format)
        if result is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("screenshot", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query")
def query(
    selector: str = Query(...),
    targetId: Optional[str] = Query(None),
    limit: int = Query(20),
):
    try:
        result = action_service.query(selector, target_id=targetId, limit=limit)
        if result is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("query", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate")
def evaluate(req: EvaluateRequest):
    try:
        result = action_service.evaluate(req.expression, target_id=req.targetId)
        if result is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("evaluate", {"result": result})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/site/capabilities")
def site_capabilities(
    site: Optional[str] = Query(None),
    targetId: Optional[str] = Query(None),
):
    try:
        result = read_service.site_capabilities(site=site, target_id=targetId)
        return ok("site-capabilities", result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/site/read")
def site_read(req: SiteReadRequest):
    try:
        site_module = site_registry.get(req.site)
        if site_module is None:
            return _site_not_supported("site-read", req.site)
        capabilities = site_module.capabilities()
        supported = capabilities.get("read") or []
        if req.kind not in supported:
            return _capability_missing("site-read", req.site, req.kind, supported)
        result = read_service.site_read(
            site=req.site,
            kind=req.kind,
            params=req.params,
            target_id=req.targetId,
            timeout_seconds=req.timeoutSeconds,
        )
        if not result:
            return _site_failure_response("site-read", result, "site read failed")
        if result.get("ok") is False:
            return _site_failure_response("site-read", result, "site read failed")
        return ok("site-read", result)
    except Exception as e:
        return fail(
            "site-read",
            "workflow_failed",
            str(e),
            detail={"site": req.site, "kind": req.kind},
        )


@app.post("/site/action")
def site_action(req: SiteActionRequest):
    try:
        site_module = site_registry.get(req.site)
        if site_module is None:
            return _site_not_supported("site-action", req.site)
        capabilities = site_module.capabilities()
        supported = capabilities.get("action") or []
        if req.kind not in supported:
            return _capability_missing("site-action", req.site, req.kind, supported)
        result = action_service.site_action(
            site=req.site,
            kind=req.kind,
            params=req.params,
            target_id=req.targetId,
            timeout_seconds=req.timeoutSeconds,
        )
        if not result:
            return _site_failure_response("site-action", result, "site action failed")
        if result.get("ok") is False:
            return _site_failure_response("site-action", result, "site action failed")
        return ok("site-action", result)
    except Exception as e:
        return fail(
            "site-action",
            "workflow_failed",
            str(e),
            detail={"site": req.site, "kind": req.kind},
        )


@app.post("/workflow/run")
def workflow_run(req: WorkflowRunRequest):
    try:
        result = workflow_service.run(
            site=req.site,
            workflow=req.workflow,
            params=req.params,
            target_id=req.targetId,
            timeout_seconds=req.timeoutSeconds,
        )
        if not result:
            return _workflow_failure_response(result)
        if result.get("ok") is False:
            return _workflow_failure_response(result)
        return ok("workflow-run", result)
    except Exception as e:
        return fail(
            "workflow-run",
            "workflow_failed",
            str(e),
            detail={"site": req.site, "workflow": req.workflow},
        )


@app.get("/login/status")
def login_status(
    site: str = Query(...),
    targetId: Optional[str] = Query(None),
    notify: bool = Query(False),
    timeoutSeconds: float = Query(20),
):
    try:
        result = login_service.status(
            site=site,
            target_id=targetId,
            notify=notify,
            timeout_seconds=timeoutSeconds,
        )
        status = result.get("status") or {}
        if status.get("ok") is False:
            return _workflow_failure_response(status)
        return ok("login-status", result)
    except Exception as e:
        return fail(
            "login-status",
            "workflow_failed",
            str(e),
            detail={"site": site},
        )


@app.post("/login/check")
def login_check(req: LoginCheckRequest):
    try:
        sites = req.sites or ([req.site] if req.site else site_registry.list_sites())
        if req.targetId and len(sites) != 1:
            return fail(
                "login-check",
                "workflow_failed",
                "targetId requires exactly one site",
                detail={"sites": sites},
            )
        if len(sites) == 1:
            result = login_service.status(
                site=sites[0],
                target_id=req.targetId,
                notify=req.notify,
                timeout_seconds=req.timeoutSeconds,
            )
        else:
            result = login_service.status_many(
                sites=sites,
                notify=req.notify,
                timeout_seconds=req.timeoutSeconds,
            )
        return ok("login-check", result)
    except Exception as e:
        return fail(
            "login-check",
            "workflow_failed",
            str(e),
            detail={"site": req.site, "sites": req.sites},
        )


@app.post("/dev/reload-extension")
def dev_reload_extension(req: DevReloadExtensionRequest):
    try:
        # 1. Pre-select target tabs to reload before the extension disconnects
        selected_tabs = []
        if req.reloadPages:
            tabs = browser_runtime.list_tabs()
            target_id_set = set(req.targetIds or [])
            for tab in tabs:
                if target_id_set:
                    if tab.get("id") in target_id_set:
                        selected_tabs.append(tab)
                    continue
                if _host_matches(tab.get("url"), req.siteHosts or []):
                    selected_tabs.append(tab)

        # 2. Send reload command via current active native session
        sid = native_session_manager.get_active_session()
        if sid:
            extension_result = native_session_manager.send_command(sid, "dev.reload", timeout_seconds=req.timeoutSeconds)
        else:
            extension_result = {"ok": False, "error": "no_active_session"}

        # 3. Wait for new session to reconnect after extension reload
        new_sid = None
        if sid and extension_result.get("ok"):
            start_time = time.time()
            while time.time() - start_time < 8.0:
                current_sid = native_session_manager.get_active_session()
                if current_sid and current_sid != sid:
                    new_sid = current_sid
                    break
                time.sleep(0.1)

        # Sleep buffer for extension startup/injections
        time.sleep(max(req.delaySeconds, 0.5))

        # 4. Reload those pre-selected tabs using the newly established session
        pages = []
        if selected_tabs:
            for tab in selected_tabs:
                result = browser_runtime.reload_tab(tab.get("id"))
                if result:
                    pages.append(result)

        return ok("dev-reload-extension", {
            "extension": extension_result.get("data", extension_result) if isinstance(extension_result, dict) else extension_result,
            "pages": pages,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.api_route("/dev/file/get", methods=["GET", "OPTIONS"])
def dev_file_get(
    request: Request,
    response: Response,
    id: Optional[str] = Query(None),
    x_browser_bridge_tab_id: Optional[str] = Header(None, alias="X-Browser-Bridge-Tab-Id"),
    x_browser_bridge_session_id: Optional[str] = Header(None, alias="X-Browser-Bridge-Session-Id"),
):
    # Set CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "X-Browser-Bridge-Tab-Id, X-Browser-Bridge-Session-Id"
    response.headers["Cache-Control"] = "no-store"

    if request.method == "OPTIONS":
        return Response(status_code=200)

    # 1. Check IP restriction (must be 127.0.0.1 or localhost loopback)
    client_host = request.client.host if request.client else None
    if client_host not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(status_code=403, detail="Forbidden: local loopback only")

    if not id:
        raise HTTPException(status_code=400, detail="Missing id parameter")

    # 2. Get upload token (Read-only validation first)
    token = get_upload_token(id)
    if not token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    # 3. Check 30 seconds TTL
    if time.time() - token["created_at"] > 30.0:
        remove_upload_token(id)
        raise HTTPException(status_code=410, detail="Token expired")

    # 4. Check Tab ID matching
    tab_id_bound = token["tab_id"]
    if str(tab_id_bound) != str(x_browser_bridge_tab_id):
        raise HTTPException(status_code=403, detail="Forbidden: Tab ID mismatch")

    # 5. Check Session ID matching
    session_id_bound = token["session_id"]
    if str(session_id_bound) != str(x_browser_bridge_session_id):
        raise HTTPException(status_code=403, detail="Forbidden: Session ID mismatch")

    # 6. Check Origin header matches expected_origin
    origin = request.headers.get("Origin") or ""
    expected_origin = token["expected_origin"]
    if origin.rstrip("/") != expected_origin.rstrip("/"):
        raise HTTPException(status_code=403, detail="Forbidden: Origin mismatch")

    # 7. Check file existence and safety rules (e.g. max size 50MB)
    file_path = token["path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        size = os.path.getsize(file_path)
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to read file size")

    if size > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    # 8. Check-before-consume atomicity:
    # Just before returning the file, destroy the token physically to prevent reuse.
    remove_upload_token(id)

    return FileResponse(
        path=file_path,
        media_type=token.get("mime") or "application/octet-stream",
        filename=os.path.basename(file_path),
    )


# === Playwright routes (Path C: complex page operations) ===

class PlaywrightConnectRequest(BaseModel):
    browserWsUrl: str  # WebSocket URL from CDP


class PlaywrightClickRequest(BaseModel):
    selector: str


class PlaywrightFillRequest(BaseModel):
    selector: str
    text: str


class PlaywrightEvaluateRequest(BaseModel):
    expression: str


@app.post("/playwright/connect")
def playwright_connect(req: PlaywrightConnectRequest):
    """Connect Playwright to existing browser via CDP WebSocket."""
    try:
        success = playwright_client.connect(req.browserWsUrl)
        if success:
            return ok("playwright-connect", {"connected": True})
        else:
            raise HTTPException(status_code=500, detail="Failed to connect")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playwright/disconnect")
def playwright_disconnect():
    """Disconnect Playwright from browser."""
    try:
        reset_playwright_client()
        return ok("playwright-disconnect", {"connected": False})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/playwright/pages")
def playwright_pages():
    """Get all pages from Playwright-connected browser."""
    try:
        pages = playwright_client.get_all_pages()
        return ok("playwright-pages", {"pages": pages})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playwright/click")
def playwright_click(req: PlaywrightClickRequest):
    """Click element using Playwright (more robust for complex pages)."""
    try:
        result = playwright_client.click(req.selector)
        return ok("playwright-click", result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playwright/fill")
def playwright_fill(req: PlaywrightFillRequest):
    """Fill element using Playwright (more robust for complex pages)."""
    try:
        result = playwright_client.fill(req.selector, req.text)
        return ok("playwright-fill", result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playwright/evaluate")
def playwright_evaluate(req: PlaywrightEvaluateRequest):
    """Execute JavaScript using Playwright."""
    try:
        result = playwright_client.evaluate(req.expression)
        return ok("playwright-evaluate", {"result": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/playwright/wait-selector")
def playwright_wait_selector(
    selector: str = Query(...),
    timeout: int = Query(5000),
):
    """Wait for selector using Playwright."""
    try:
        found = playwright_client.wait_for_selector(selector, timeout=timeout)
        return ok("playwright-wait-selector", {"found": found, "selector": selector})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run():
    uvicorn.run(app, host=BRIDGE_HOST, port=BRIDGE_PORT)
