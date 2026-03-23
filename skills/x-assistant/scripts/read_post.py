import sys
import json
import urllib.request
import time
from urllib.parse import urlparse

BRIDGE_URL = "http://127.0.0.1:17777"

proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(proxy_handler)

def _post_json(path, payload, timeout=90):
    try:
        req = urllib.request.Request(
            f"{BRIDGE_URL}{path}",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with opener.open(req, timeout=timeout) as res:
            return json.loads(res.read())
    except Exception as e:
        return {"error": str(e)}

def _get_json(path, timeout=90):
    try:
        req = urllib.request.Request(f"{BRIDGE_URL}{path}", method='GET')
        with opener.open(req, timeout=timeout) as res:
            return json.loads(res.read())
    except Exception as e:
        return {"error": str(e)}

def _extract_status_id(url: str):
    try:
        parts = [p for p in urlparse(url).path.split("/") if p]
        if "status" in parts:
            idx = parts.index("status")
            if idx + 1 < len(parts):
                return parts[idx + 1]
    except Exception:
        pass
    return None

def _fetch_extension_primary_text(status_id: str):
    if not status_id:
        return None
    state = _get_json("/extension/state", timeout=30)
    if "error" in state: return None
    
    reports = (((state or {}).get("data") or {}).get("reports") or [])
    for report in reversed(reports):
        page_url = ((report.get("page") or {}).get("url") or "")
        if status_id in page_url:
            primary = ((report.get("content") or {}).get("primaryText") or "").strip()
            if primary:
                return primary
    return None

def _fetch_cdp_content(target_id: str):
    data = _get_json(f"/page-content?targetId={target_id}&maxChars=100000", timeout=30)
    if "error" in data: return ""
    return (((data or {}).get("data") or {}).get("content") or "").strip()

def _open_target(url: str, reuse_existing_tab: bool):
    open_data = _post_json(
        "/open",
        {
            "url": url,
            "reuseExistingTab": reuse_existing_tab,
            "reuseDomain": "x.com",
        },
        timeout=40,
    )
    target_id = open_data.get("data", {}).get("id")
    if not target_id:
        return None
    _post_json("/activate", {"targetId": target_id}, timeout=30)
    return target_id

def _attempt_read_with_target(target_id: str, status_id: str):
    # Base initial wait to let page load and extension run
    time.sleep(1.5)
    
    content = ""
    for attempt in range(3):
        read_data = _post_json(
            "/read-page",
            {"targetId": target_id, "waitForReady": True, "maxChars": 100000},
            timeout=90,
        )
        if "error" not in read_data:
            # Check if we got extension source
            source = read_data.get("data", {}).get("preferredContentSource")
            content = (read_data.get("data", {}).get("preferredContent") or "").strip()
            if source == "extension" and content:
                return content, "read-page-extension"
        
        # Fallback 1: check extension state history
        content = _fetch_extension_primary_text(status_id) or ""
        if content:
            return content, "extension-state-fallback"
            
        if attempt < 2:
             time.sleep(1.5)
             
    # If still nothing, return whatever we got from read_page (even if cdp)
    if "error" not in read_data:
         content = (read_data.get("data", {}).get("preferredContent") or "").strip()
         if content:
             return content, "read-page-cdp"
             
    return "", "none"

def read_single_post(url):
    try:
        status_id = _extract_status_id(url)
        target_id = _open_target(url, reuse_existing_tab=True)
        if not target_id:
            print(json.dumps({"ok": False, "error": "Failed to open post page"}))
            return

        content, source = _attempt_read_with_target(target_id, status_id)
        
        if not content:
            # Absolute last fallback
            content = _fetch_cdp_content(target_id)
            source = "pure-cdp-fallback"
        
        if not content:
            print(json.dumps({"ok": False, "error": "No content found after retries. Page might be restricted or loading failed."}))
            return

        print(json.dumps({
            "ok": True, 
            "url": url, 
            "source": source,
            "results": {
                "text": content,
                "analysis": {
                    "length": len(content),
                    "is_worth_reading": len(content) > 10
                }
            },
            "data": content
        }))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing URL parameter"}))
        sys.exit(1)
    read_single_post(sys.argv[1])
