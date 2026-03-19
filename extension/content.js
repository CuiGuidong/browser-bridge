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
      primaryText: text.slice(0, 4000),
    },
  };
}

function cleanXPrimaryText(article, tweetText) {
  const clone = article?.cloneNode(true);
  if (!clone) {
    return tweetText?.innerText?.trim() || '';
  }

  const noiseSelectors = [
    'button', 'nav', 'aside', 'svg', '[aria-hidden="true"]',
    '[data-testid="caret"]', '[data-testid="reply"]', '[data-testid="retweet"]',
    '[data-testid="like"]', '[data-testid="bookmark"]', '[data-testid="AppTabBar_Explore_Link"]'
  ];
  clone.querySelectorAll(noiseSelectors.join(', ')).forEach((el) => el.remove());

  let text = (clone.innerText || '').trim();
  const lines = text.split('\n').map((s) => s.trim()).filter(Boolean);
  const filtered = [];
  
  for (const line of lines) {
    if (/^(主页|探索|通知|聊天|Grok|书签|更多|发帖|文章|对话|查看新帖子|订阅|分享)$/i.test(line)) continue;
    if (/^(Home|Explore|Notifications|Messages|Bookmarks|More|Post|Articles|Subscribe|Share)$/i.test(line)) continue;
    if (/^[\d\,\.]+([KMBkmb万亿]?)$/.test(line)) continue;
    if (/^(查看|显示)\s*(更多|回复|相关|此对话)/.test(line)) continue;
    if (/^Show (more|replies|this thread)/i.test(line)) continue;
    if (/^\s*回复\s*/.test(line)) continue;
    if (/^Replying to\s+/i.test(line)) continue;
    if (/点击\s*订阅\s*到/i.test(line)) continue; // Filter "点击 订阅 到 xxx"
    if (/^\d+[\d\,\.]*[KMBkmb万亿]?\s*(查看|Views?)$/i.test(line)) continue; // Filter "583 查看" or "583 Views"
    filtered.push(line);
  }
  
  let result = filtered.join('\n').replace(/\n{3,}/g, '\n\n').trim();
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
    article &&
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
      primaryText: primaryText.slice(0, 4000),
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