import sys
import os

# Add bridge directory to path so we can import it
sys.path.append("/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/bridge")

from app.cdp_service import BrowserBridgeService
service = BrowserBridgeService()

script = """(() => {
  const cells = Array.from(document.querySelectorAll('[data-testid="cellInnerDiv"]'));
  const timeline = [];
  for (const cell of cells) {
    try {
      const tweetEl = cell.querySelector('[data-testid="tweet"]');
      if (!tweetEl) continue;
      const timeEl = tweetEl.querySelector('time');
      const urlEl = timeEl ? timeEl.closest('a') : null;
      const url = urlEl ? urlEl.href : null;
      const authorEl = tweetEl.querySelector('[data-testid="User-Name"]');
      const authorInfo = authorEl ? authorEl.innerText.replace(/\\n/g, ' ') : '';
      
      const walker = document.createTreeWalker(tweetEl, NodeFilter.SHOW_TEXT, null, false);
      let tCount = 0;
      while(walker.nextNode()) tCount++;
      
      timeline.push({ authorInfo, url, tCount });
    } catch(e) {
      timeline.push({ error: e.message });
    }
  }
  return timeline;
})()"""

res = service.execute_js(script)
import json
print(json.dumps(res, indent=2))
