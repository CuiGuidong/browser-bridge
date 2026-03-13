from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
import uvicorn

from .config import BRIDGE_HOST, BRIDGE_PORT
from .cdp_service import BrowserBridgeService
from .playwright_client import get_playwright_client, reset_playwright_client
from .schemas import ok, fail


app = FastAPI(title="Browser Bridge API", version="1.0.0")
service = BrowserBridgeService()
playwright_client = get_playwright_client()


# Request/Response models
class OpenRequest(BaseModel):
    url: str


class ActivateRequest(BaseModel):
    targetId: str


class ScreenshotRequest(BaseModel):
    targetId: Optional[str] = None
    format: str = "png"


class ClickRequest(BaseModel):
    selector: str
    targetId: Optional[str] = None
    waitAfter: float = 0


class FillRequest(BaseModel):
    selector: str
    text: str
    targetId: Optional[str] = None


@app.get("/health")
def health():
    try:
        version = service.get_version()
        return ok("health", {
            "bridge": "alive",
            "cdp": "connected",
            "browser": version.get("Browser"),
            "protocolVersion": version.get("Protocol-Version"),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/version")
def version():
    try:
        version = service.get_version()
        return ok("version", version)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tabs")
def tabs():
    try:
        return ok("tabs", service.list_tabs())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/open")
def open_url(req: OpenRequest):
    try:
        return ok("open", service.open_url(req.url))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/activate")
def activate(req: ActivateRequest):
    try:
        return ok("activate", service.activate_tab(req.targetId))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wait")
def wait(
    targetId: Optional[str] = Query(None),
    timeoutSeconds: float = Query(10),
    intervalSeconds: float = Query(0.5),
):
    try:
        result = service.wait_for_page(
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
        info = service.get_page_info(targetId)
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
        info = service.get_page_content(targetId, max_chars=maxChars)
        if info is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("page-content", info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screenshot")
def screenshot(req: ScreenshotRequest):
    try:
        result = service.capture_screenshot(target_id=req.targetId, fmt=req.format)
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
        result = service.query_elements(selector, target_id=targetId, limit=limit)
        if result is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("query", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/click")
def click(req: ClickRequest):
    try:
        result = service.click_selector(
            req.selector,
            target_id=req.targetId,
            wait_after=req.waitAfter,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("click", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fill")
def fill(req: FillRequest):
    try:
        result = service.fill_selector(
            req.selector,
            req.text,
            target_id=req.targetId,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="page not found")
        return ok("fill", result)
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