import sys
import json
import urllib.request
import time

BRIDGE_URL = "http://127.0.0.1:17777"

def read_home_feed(feed_type="For you"):
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

        # 2. Switch tab if necessary
        is_following = feed_type.lower() in ["following", "正在关注"]
        tab_text1 = "正在关注" if is_following else "为你推荐"
        tab_text2 = "Following" if is_following else "For you"
        
        click_script = f'''(() => {{
            const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
            const target = tabs.find(el => el.innerText.includes("{tab_text1}") || el.innerText.includes("{tab_text2}"));
            if (target) {{
                target.click();
                return true;
            }}
            return false;
        }})()'''
        
        eval_req = urllib.request.Request(
            f"{BRIDGE_URL}/playwright/evaluate",
            data=json.dumps({"expression": click_script}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
             with urllib.request.urlopen(eval_req) as res:
                 json.loads(res.read())
             time.sleep(2) # Wait for feed to load after switching
        except Exception as e:
             # Ignore if evaluation fails, just proceed to read
             pass

        # 3. Read the page (Bridge will auto-scroll timelines to load ~20 results)
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

        print(json.dumps({"ok": True, "feed_type": feed_type, "data": timeline}))

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))

if __name__ == "__main__":
    feed_type = sys.argv[1] if len(sys.argv) > 1 else "For you"
    read_home_feed(feed_type)
