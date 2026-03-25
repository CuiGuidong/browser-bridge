from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn

from .application.action_service import ActionService
from .application.read_service import ReadService
from .application.workflow_service import WorkflowService
from .browser.cdp_runtime import CdpRuntime
from .config import BRIDGE_HOST, BRIDGE_PORT
from .extension.extension_runtime import ExtensionRuntime
from .playwright_client import get_playwright_client, reset_playwright_client
from .schemas import ok
from .sites.registry import SiteRegistry
from .sites.x.site import XSite


app = FastAPI(title="Browser Bridge API", version="1.0.0")
browser_runtime = CdpRuntime()
extension_runtime = ExtensionRuntime()
site_registry = SiteRegistry()
site_registry.register("x", XSite())
read_service = ReadService(browser_runtime, extension_runtime, site_registry=site_registry)
action_service = ActionService(browser_runtime, extension_runtime, site_registry=site_registry)
workflow_service = WorkflowService(browser_runtime, extension_runtime, site_registry=site_registry)
workflow_service.bind_read_service(read_service)
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


class ExtensionReportRequest(BaseModel):
    source: str = "extension"
    site: Optional[str] = None
    kind: str = "page-state"
    page: Dict[str, Any]
    signals: Dict[str, Any] = {}
    content: Dict[str, Any] = {}


class ExtensionCommandResultRequest(BaseModel):
    commandId: str
    result: Dict[str, Any]


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


@app.post("/extension/report")
def extension_report(req: ExtensionReportRequest):
    try:
        result = action_service.store_extension_report(req.model_dump())
        return ok("extension-report", result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/extension/state")
def extension_get_state():
    try:
        return ok("extension-state", action_service.extension_state())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/extension/pull")
def extension_pull(
    timeoutSeconds: float = Query(1),
    pageUrl: Optional[str] = Query(None),
):
    try:
        command = action_service.pull_extension_command(timeout_seconds=timeoutSeconds, page_url=pageUrl)
        return ok("extension-pull", {"command": command})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extension/result")
def extension_result(req: ExtensionCommandResultRequest):
    try:
        result = action_service.store_extension_result(req.commandId, req.result)
        return ok("extension-result", result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        result = read_service.site_read(
            site=req.site,
            kind=req.kind,
            params=req.params,
            target_id=req.targetId,
            timeout_seconds=req.timeoutSeconds,
        )
        if not result:
            raise HTTPException(status_code=404, detail="site read failed")
        return ok("site-read", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/site/action")
def site_action(req: SiteActionRequest):
    try:
        result = action_service.site_action(
            site=req.site,
            kind=req.kind,
            params=req.params,
            target_id=req.targetId,
            timeout_seconds=req.timeoutSeconds,
        )
        if not result:
            raise HTTPException(status_code=404, detail="site action failed")
        return ok("site-action", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            raise HTTPException(status_code=404, detail="workflow failed")
        return ok("workflow-run", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
