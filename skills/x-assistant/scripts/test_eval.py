import sys
sys.path.append("/home/cuiguidong/.openclaw/workspace/projects/browser-bridge-project/bridge")
from app.cdp_service import BrowserBridgeService
import json

service = BrowserBridgeService()
target = service.list_tabs()[0]

script = """(() => {
  const cells = Array.from(document.querySelectorAll('[data-testid="cellInnerDiv"]'));
  const timeline = [];
  for (const cell of cells) {
    try {
      const tweetEl = cell.querySelector('[data-testid="tweet"]');
      if (!tweetEl) continue;
      const walker = document.createTreeWalker(tweetEl, NodeFilter.SHOW_TEXT, null, false);
      const fragments = [];
      let node;
      while(node = walker.nextNode()) {
        const parent = node.parentElement;
        if (!parent) continue;
        const style = window.getComputedStyle(parent);
        if (style.display === 'none' || style.visibility === 'hidden') continue;
        if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'NAV', 'HEADER'].includes(parent.tagName)) continue;
        const text = node.nodeValue.trim();
        if (text.length < 2) continue;
        if (text.length < 15 && /^[\d\,\.]+([KMBkmb万亿]?)$/.test(text)) continue;
        if (text.length < 20 && /^(查看|显示)\s*(更多|回复|相关|此对话|Show more)/i.test(text)) continue;
        fragments.push(text);
      }
      
      const timeEl = tweetEl.querySelector('time');
      const urlEl = timeEl ? timeEl.closest('a') : null;
      const url = urlEl ? urlEl.href : null;
      const authorEl = tweetEl.querySelector('[data-testid="User-Name"]');
      const authorInfo = authorEl ? authorEl.innerText.replace(/\\n/g, ' ') : '';
      
      const filtered = [];
      for (let i = 0; i < fragments.length; i++) {
        if (i > 0 && fragments[i] === fragments[i-1]) continue;
        filtered.push(fragments[i]);
      }
      
      const textContent = filtered.join('\\n\\n').replace(/\\n{4,}/g, '\\n\\n\\n').trim();
      if (textContent.length > 0) {
         timeline.push({ authorInfo, url, text: textContent });
      } else {
         timeline.push({ authorInfo, url, text: "EMPTY", debug: fragments });
      }
    } catch (err) {
      timeline.push({ error: err.toString() });
    }
  }
  return timeline;
})()"""

res = service.execute_js(script, "11259D25C488A7D39A28DEE828D88B20")
print(json.dumps(res, indent=2, ensure_ascii=False)[:2000])
