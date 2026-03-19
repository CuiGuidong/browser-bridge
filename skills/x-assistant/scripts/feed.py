import sys
import json
import urllib.request
import time

BRIDGE_URL = "http://127.0.0.1:17777"

def read_home_feed():
    try:
        # 1. Open the home page
        open_req = urllib.request.Request(
            f"{BRIDGE_URL}/open",
            data=json.dumps({"url": "https://x.com/home"}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(open_req) as res:
            open_data = json.loads(res.read())
        
        target_id = open_data.get("data", {}).get("id")
        if not target_id:
            print(json.dumps({"ok": False, "error": "Failed to open home page"}))
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
             fallback = read_data.get("data", {}).get("preferredContent")
             if fallback:
                 print(json.dumps({"ok": True, "warning": "Failed to parse structured timeline", "data": [{"text": fallback}]}))
             else:
                 print(json.dumps({"ok": False, "error": "No timeline data found. Ensure you are logged in."}))
             return

        print(json.dumps({"ok": True, "data": timeline}))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

if __name__ == "__main__":
    read_home_feed()
