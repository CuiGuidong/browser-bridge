import sys
import json
import urllib.request

BRIDGE_URL = "http://127.0.0.1:17777"

def read_single_post(url):
    try:
        open_req = urllib.request.Request(
            f"{BRIDGE_URL}/open",
            data=json.dumps({"url": url}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(open_req) as res:
            open_data = json.loads(res.read())
        
        target_id = open_data.get("data", {}).get("id")
        if not target_id:
            print(json.dumps({"ok": False, "error": "Failed to open post page"}))
            return

        read_req = urllib.request.Request(
            f"{BRIDGE_URL}/read-page",
            data=json.dumps({"targetId": target_id, "waitForReady": True, "maxChars": 100000}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(read_req) as res:
            read_data = json.loads(res.read())
            
        content = read_data.get("data", {}).get("preferredContent")
        
        if not content:
            print(json.dumps({"ok": False, "error": "No content found."}))
            return

        print(json.dumps({"ok": True, "url": url, "data": content}))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing URL parameter"}))
        sys.exit(1)
    read_single_post(sys.argv[1])
