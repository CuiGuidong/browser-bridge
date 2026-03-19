import sys
import json
import urllib.request
import urllib.parse
import time

BRIDGE_URL = "http://127.0.0.1:17777"

def search_x(keyword):
    encoded_kw = urllib.parse.quote(keyword)
    # Using f=live for latest results, or remove for top results
    search_url = f"https://x.com/search?q={encoded_kw}&src=typed_query"
    
    try:
        # 1. Open the search URL
        open_req = urllib.request.Request(
            f"{BRIDGE_URL}/open",
            data=json.dumps({"url": search_url}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(open_req) as res:
            open_data = json.loads(res.read())
        
        target_id = open_data.get("data", {}).get("id")
        if not target_id:
            print(json.dumps({"ok": False, "error": "Failed to open search page"}))
            return

        # 2. Read the page (Bridge will auto-scroll timelines to load ~20 results)
        read_req = urllib.request.Request(
            f"{BRIDGE_URL}/read-page",
            data=json.dumps({"targetId": target_id, "waitForReady": True, "maxChars": 100000}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(read_req) as res:
            read_data = json.loads(res.read())
            
        timeline = read_data.get("data", {}).get("extensionHint", {}).get("content", {}).get("timeline", [])
        
        if not timeline:
             # Check if we got a raw fallback string instead
             fallback = read_data.get("data", {}).get("preferredContent")
             if fallback:
                 print(json.dumps({"ok": True, "keyword": keyword, "warning": "Failed to parse structured timeline, returned raw text", "data": [{"text": fallback}]}))
             else:
                 print(json.dumps({"ok": False, "error": "No timeline data found."}))
             return

        print(json.dumps({"ok": True, "keyword": keyword, "data": timeline}))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing keyword parameter"}))
        sys.exit(1)
    search_x(sys.argv[1])
