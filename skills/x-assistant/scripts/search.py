import sys
import json
import urllib.request
import urllib.parse
import time
import hashlib

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

def _fetch_timeline_from_extension_state():
    state = _get_json("/extension/state", timeout=30)
    if "error" in state: return []
    reports = (((state or {}).get("data") or {}).get("reports") or [])
    for report in reversed(reports):
        page_url = ((report.get("page") or {}).get("url") or "")
        if "/search" not in page_url:
            continue
        timeline = ((report.get("content") or {}).get("timeline") or [])
        if timeline:
            return timeline
    return []

def _fetch_raw_cdp_content(target_id):
    data = _get_json(f"/page-content?targetId={target_id}&maxChars=100000", timeout=30)
    if "error" in data: return ""
    return ((((data or {}).get("data")) or {}).get("content") or "").strip()

def analyze_item(item):
    text = (item.get("text") or "").strip()
    author_info = (item.get("authorInfo") or "").strip()
    
    is_ad = "Promoted" in text or "赞助" in text or "Ad" in author_info
    is_retweet = "RT @" in text or "Retweeted" in author_info or "转推了" in author_info
    
    score = 50
    score += min(len(text) // 10, 30)
    if "http" in text or "[Image:" in text or "[Video" in text: score += 10
    if len(text) < 20 and ("http" in text or "[Image:" in text): score -= 10 # slightly less penalty if it has image
        
    signal_type = "original"
    if is_ad:
        signal_type = "ad"
        score -= 100
    elif is_retweet:
        signal_type = "retweet"
        score -= 10
    elif len(text) < 15 and not ("http" in text or "[Image:" in text):
        signal_type = "low-info"
        score -= 30

    worth_reading = score > 40 and not is_ad
    
    return {
        "signal_type": signal_type,
        "score": score,
        "is_ad": is_ad,
        "is_worth_reading": worth_reading
    }

def dedup_and_score(items):
    seen_urls = set()
    seen_texts = set()
    deduped = []
    
    for item in items:
        url = (item.get("url") or "").strip()
        text = (item.get("text") or "").strip()
        
        if url and url in seen_urls:
            continue
        
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        if text_hash in seen_texts:
            continue
            
        if url: seen_urls.add(url)
        seen_texts.add(text_hash)
        
        item["analysis"] = analyze_item(item)
        deduped.append(item)
        
    deduped.sort(key=lambda x: x["analysis"]["score"], reverse=True)
    return deduped

def search_x(keyword):
    encoded_kw = urllib.parse.quote(keyword)
    search_url = f"https://x.com/search?q={encoded_kw}&src=typed_query"
    
    try:
        open_data = _post_json(
            "/open",
            {
                "url": search_url,
                "reuseExistingTab": True,
                "reuseDomain": "x.com"
            },
            timeout=40,
        )
        
        target_id = open_data.get("data", {}).get("id")
        if not target_id:
            print(json.dumps({"ok": False, "error": "Failed to open search page"}))
            return

        _post_json("/activate", {"targetId": target_id}, timeout=30)
        
        # Base wait for page rendering and extension
        time.sleep(1.5)

        read_data = {}
        timeline = []
        source = "read-page"
        
        # Try 3 times with 1.5s interval
        for attempt in range(3):
            read_data = _post_json(
                "/read-page",
                {"targetId": target_id, "waitForReady": True, "maxChars": 100000},
                timeout=90,
            )
            
            if "error" not in read_data:
                # Need to verify if the source is extension, CDP won't give timeline
                pref_source = read_data.get("data", {}).get("preferredContentSource")
                if pref_source == "extension":
                    timeline = read_data.get("data", {}).get("extensionHint", {}).get("content", {}).get("timeline", [])
                    if timeline:
                        break
            
            # Check extension state fallback
            timeline = _fetch_timeline_from_extension_state()
            if timeline:
                source = "extension-state"
                break
                
            if attempt < 2:
                time.sleep(1.5)
        
        if not timeline:
            fallback = (read_data.get("data", {}).get("preferredContent") or "").strip()
            if fallback:
                print(json.dumps({
                    "ok": True,
                    "keyword": keyword,
                    "warning": "Failed to parse structured timeline, returned raw text",
                    "source": "preferredContent",
                    "results": {
                        "raw_count": 1,
                        "deduped_count": 1,
                        "items": [{"text": fallback, "analysis": {"is_worth_reading": True, "score": 50}}],
                    },
                    "data": [{"text": fallback}],
                }))
                return
                
            cdp_text = _fetch_raw_cdp_content(target_id)
            if cdp_text:
                print(json.dumps({
                    "ok": True,
                    "keyword": keyword,
                    "warning": "No structured timeline; returned CDP raw text fallback",
                    "source": "cdp",
                    "results": {
                        "raw_count": 1,
                        "deduped_count": 1,
                        "items": [{"text": cdp_text, "analysis": {"is_worth_reading": True, "score": 50}}],
                    },
                    "data": [{"text": cdp_text}],
                }))
                return
                
            print(json.dumps({"ok": False, "error": "No timeline data found.", "raw_debug": read_data}))
            return

        deduped = dedup_and_score(timeline)
        
        print(json.dumps({
            "ok": True, 
            "keyword": keyword, 
            "source": source, 
            "results": {
                "raw_count": len(timeline),
                "deduped_count": len(deduped),
                "items": deduped
            },
            "data": deduped
        }))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing keyword parameter"}))
        sys.exit(1)
    search_x(sys.argv[1])
