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
      const start = () => {
        state.pending += 1;
        state.requestCount += 1;
        state.lastRequestStartedAt = Date.now();
      };
      const finish = () => {
        state.pending = Math.max(0, state.pending - 1);
        state.lastRequestFinishedAt = Date.now();
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
    })();
  `;
  (document.documentElement || document.head || document.body).appendChild(script);
  script.remove();
})();

function getRequestProbeState() {
  try {
    return window.__BROWSER_BRIDGE_PAGE_PROBE__?.getState?.() || null;
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

function collectXSnapshot(base) {
  const article = document.querySelector('article');
  const tweetText = document.querySelector('[data-testid="tweetText"]');
  const loginMask = !!document.querySelector('[role="dialog"], [data-testid="sheetDialog"]');
  const sensitiveGate = !!Array.from(document.querySelectorAll('span,div')).find((el) =>
    /显示|查看|敏感|sensitive/i.test((el.innerText || '').trim())
  );
  const primaryText = (tweetText?.innerText || article?.innerText || '').trim();
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