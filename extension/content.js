// Content script - injected into all pages
// Owns page-level observation and reports structured signals to background.

console.log('[Browser Bridge] Content script loaded');

(function installRequestProbe() {
  if (window.__BROWSER_BRIDGE_REQUEST_PROBE_INSTALLED__) return;
  window.__BROWSER_BRIDGE_REQUEST_PROBE_INSTALLED__ = true;

  const script = document.createElement('script');
  script.textContent = `
    (() => {
      if (window.__BROWSER_BRIDGE_PAGE_PROBE__) return;
      const state = {
        pending: 0,
        lastRequestStartedAt: 0,
        lastRequestFinishedAt: 0,
        requestCount: 0,
      };
      const publish = () => {
        const payload = JSON.stringify({
          pending: state.pending,
          requestCount: state.requestCount,
          lastRequestStartedAt: state.lastRequestStartedAt,
          lastRequestFinishedAt: state.lastRequestFinishedAt,
          quietMs: state.lastRequestFinishedAt ? Date.now() - state.lastRequestFinishedAt : null,
        });
        document.documentElement?.setAttribute('data-browser-bridge-probe', payload);
      };
      const start = () => {
        state.pending += 1;
        state.requestCount += 1;
        state.lastRequestStartedAt = Date.now();
        publish();
      };
      const finish = () => {
        state.pending = Math.max(0, state.pending - 1);
        state.lastRequestFinishedAt = Date.now();
        publish();
      };

      const origFetch = window.fetch;
      window.fetch = async function(...args) {
        start();
        try { return await origFetch.apply(this, args); }
        finally { finish(); }
      };

      const origOpen = XMLHttpRequest.prototype.open;
      const origSend = XMLHttpRequest.prototype.send;
      XMLHttpRequest.prototype.open = function(...args) {
        this.__bb_tracked = true;
        return origOpen.apply(this, args);
      };
      XMLHttpRequest.prototype.send = function(...args) {
        if (this.__bb_tracked) {
          start();
          this.addEventListener('loadend', finish, { once: true });
        }
        return origSend.apply(this, args);
      };

      window.__BROWSER_BRIDGE_PAGE_PROBE__ = {
        getState() {
          return {
            pending: state.pending,
            requestCount: state.requestCount,
            lastRequestStartedAt: state.lastRequestStartedAt,
            lastRequestFinishedAt: state.lastRequestFinishedAt,
            quietMs: state.lastRequestFinishedAt ? Date.now() - state.lastRequestFinishedAt : null,
          };
        }
      };
      publish();
    })();
  `;
  (document.documentElement || document.head || document.body).appendChild(script);
  script.remove();
})();

function getRequestProbeState() {
  try {
    const attr = document.documentElement?.getAttribute('data-browser-bridge-probe');
    if (!attr) return null;
    const state = JSON.parse(attr);
    if (state.lastRequestFinishedAt) {
      state.quietMs = Date.now() - state.lastRequestFinishedAt;
    }
    return state;
  } catch {
    return null;
  }
}

function collectGenericSnapshot() {
  const text = (document.body?.innerText || '').trim();
  const network = getRequestProbeState();
  return {
    site: location.hostname,
    page: {
      url: location.href,
      title: document.title || '',
      hostname: location.hostname,
    },
    signals: {
      readyState: document.readyState,
      bodyTextLength: text.length,
      network,
      ready: text.length > 120 && document.readyState === 'complete',
    },
    content: {
      primaryText: text,
    },
  };
}

async function expandXLongPost() {
  const showMore = Array.from(document.querySelectorAll('div[role="button"]'))
    .find(el => /显示更多|Show more/i.test(el.innerText));
  if (showMore) {
    showMore.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await new Promise(r => setTimeout(r, 800));
    showMore.click();
    return true;
  }
  return false;
}

function cleanXPrimaryText(article, tweetText) {
  const container = article || document.querySelector('[data-testid="tweetText"]')?.closest('[role="article"]') || document.body;
  
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
  const fragments = [];
  const standaloneNoiseRegex = /^(主页|探索|通知|聊天|Grok|书签|更多|发帖|文章|对话|查看新帖子|订阅|分享|Home|Explore|Notifications|Messages|Bookmarks|More|Post|Articles|Subscribe|Share|什么是新鲜事|What’s happening)$/i;

  let node;
  while(node = walker.nextNode()) {
    const parent = node.parentElement;
    if (!parent) continue;
    
    const style = window.getComputedStyle(parent);
    if (style.display === 'none' || style.visibility === 'hidden') continue;
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'NAV', 'HEADER'].includes(parent.tagName)) continue;

    const text = node.nodeValue.trim();
    if (text.length < 2) continue;
    
    if (text.length < 20 && standaloneNoiseRegex.test(text)) continue;
    if (text.length < 15 && /^[\d\,\.]+([KMBkmb万亿]?)$/.test(text)) continue;
    if (text.length < 20 && /^(查看|显示)\s*(更多|回复|相关|此对话)/.test(text)) continue;

    fragments.push(text);
  }

  const filtered = [];
  for (let i = 0; i < fragments.length; i++) {
    if (i > 0 && fragments[i] === fragments[i-1]) continue;
    filtered.push(fragments[i]);
  }

  let result = filtered.join('\n\n').replace(/\n{4,}/g, '\n\n\n').trim();
  return result || tweetText?.innerText?.trim() || '';
}

function collectXSnapshot(base) {
  const article = document.querySelector('article');
  const tweetText = document.querySelector('[data-testid="tweetText"]');
  const loginMask = !!document.querySelector('[role="dialog"], [data-testid="sheetDialog"]');
  const sensitiveGate = /(敏感内容|sensitive content|age-restricted|成人内容|adult content)/i.test(document.body?.innerText || '');
  const primaryText = cleanXPrimaryText(article, tweetText);
  const network = getRequestProbeState();
  const networkQuiet = !network || (network.pending === 0 && (network.quietMs === null || network.quietMs > 800));
  const isTweetDetail = /\/status\/\d+/.test(location.href);
  const ready = !!(
    document.readyState === 'complete' &&
    isTweetDetail &&
    primaryText.length > 20 &&
    !loginMask &&
    networkQuiet
  );
  return {
    site: 'x',
    page: base.page,
    signals: {
      ...base.signals,
      isX: true,
      isTweetDetail,
      articleFound: !!article,
      tweetTextFound: !!tweetText,
      loginMask,
      sensitiveGate,
      networkQuiet,
      ready,
    },
    content: {
      primaryText: primaryText,
    },
  };
}

function collectSnapshot() {
  const base = collectGenericSnapshot();
  if (location.hostname.includes('x.com') || location.hostname.includes('twitter.com')) {
    return collectXSnapshot(base);
  }
  return base;
}

function reportSnapshot(kind = 'page-state') {
  const payload = {
    action: 'extensionSnapshot',
    payload: {
      source: 'extension',
      site: collectSnapshot().site,
      kind,
      ...collectSnapshot(),
    },
  };
  chrome.runtime.sendMessage(payload, () => void chrome.runtime.lastError);
}

let observer = null;
function startObservation() {
  if (observer) observer.disconnect();
  let lastReady = false;
  observer = new MutationObserver(() => {
    const snap = collectSnapshot();
    if (snap.signals.ready || snap.signals.bodyTextLength > 0) {
      reportSnapshot('mutation');
      if (snap.signals.ready && !lastReady) {
        lastReady = true;
      }
    }
  });
  observer.observe(document.documentElement || document.body, {
    childList: true,
    subtree: true,
    attributes: false,
  });

  let count = 0;
  const timer = setInterval(() => {
    count += 1;
    reportSnapshot('interval');
    const snap = collectSnapshot();
    if (snap.signals.ready || count >= 12) clearInterval(timer);
  }, 1500);
}

window.addEventListener('message', (event) => {
  if (event.source !== window) return;
  if (event.data.type && event.data.type === 'BROWSER_BRIDGE_REQUEST') {
    chrome.runtime.sendMessage(event.data.payload, (response) => {
      window.postMessage({
        type: 'BROWSER_BRIDGE_RESPONSE',
        id: event.data.id,
        response: response,
      }, '*');
    });
  }
});

document.dispatchEvent(new CustomEvent('browserBridgeReady', {
  detail: { version: '1.0.0' }
}));

reportSnapshot('initial');
startObservation();
