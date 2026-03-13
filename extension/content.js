// Content script - injected into all pages
// Acts as a bridge between page and extension

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
        try {
          return await origFetch.apply(this, args);
        } finally {
          finish();
        }
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

// Listen for messages from the page (if needed for future bi-directional communication)
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