// Content script - injected into all pages
// Owns page-level observation and reports structured signals to background.

console.log('[Browser Bridge] Content script loaded');

// Initialize global adapter registry
window.BrowserBridgeAdapters = window.BrowserBridgeAdapters || [];

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

function collectSnapshot() {
  const base = collectGenericSnapshot();
  // Find an adapter that matches the current domain
  const activeAdapter = getActiveAdapter();
  if (activeAdapter) {
    return activeAdapter.collect(base);
  }
  return base;
}

function getActiveAdapter() {
  return window.BrowserBridgeAdapters.find((adapter) => adapter.match()) || null;
}

function buildAdapterContext(baseSnapshot) {
  const adapter = getActiveAdapter();
  const pageType = adapter && typeof adapter.getPageType === 'function'
    ? adapter.getPageType({ baseSnapshot })
    : null;
  return {
    adapter,
    baseSnapshot,
    pageType,
    page: baseSnapshot.page,
  };
}

function normalizeBridgeRpcResult(result, fallbackSnapshot, extra = {}) {
  if (result && typeof result === 'object') {
    return {
      ok: true,
      source: 'extension-rpc',
      site: fallbackSnapshot.site,
      page: fallbackSnapshot.page,
      ...result,
      ...extra,
    };
  }
  return {
    ok: true,
    source: 'extension-rpc',
    site: fallbackSnapshot.site,
    page: fallbackSnapshot.page,
    data: result,
    ...extra,
  };
}

async function handleBridgeRpc(payload) {
  const method = payload?.method;
  const params = payload?.params || {};
  const baseSnapshot = collectGenericSnapshot();
  const context = buildAdapterContext(baseSnapshot);
  const adapter = context.adapter;

  if (!adapter) {
    return {
      ok: false,
      source: 'extension-rpc',
      error: 'No matching adapter',
      site: baseSnapshot.site,
      page: baseSnapshot.page,
      signals: baseSnapshot.signals,
      content: baseSnapshot.content,
    };
  }

  try {
    if (method === 'capabilities') {
      const capabilities = typeof adapter.capabilities === 'function'
        ? adapter.capabilities()
        : {};
      return normalizeBridgeRpcResult(
        {
          capabilities,
          pageType: context.pageType,
        },
        baseSnapshot,
      );
    }

    if (method === 'probe_ready') {
      if (typeof adapter.probeReady === 'function') {
        return normalizeBridgeRpcResult(
          await adapter.probeReady(context),
          baseSnapshot,
          { pageType: context.pageType },
        );
      }
      return normalizeBridgeRpcResult(collectSnapshot(), baseSnapshot, { pageType: context.pageType });
    }

    if (method === 'read') {
      if (typeof adapter.read === 'function') {
        return normalizeBridgeRpcResult(
          await adapter.read(params.kind, params, context),
          baseSnapshot,
          { pageType: context.pageType },
        );
      }
      return normalizeBridgeRpcResult(collectSnapshot(), baseSnapshot, { pageType: context.pageType });
    }

    if (method === 'act') {
      if (typeof adapter.act === 'function') {
        return normalizeBridgeRpcResult(
          await adapter.act(params.kind, params, context),
          baseSnapshot,
          { pageType: context.pageType },
        );
      }
      return {
        ok: false,
        source: 'extension-rpc',
        site: baseSnapshot.site,
        page: baseSnapshot.page,
        error: 'Adapter does not support act',
        pageType: context.pageType,
      };
    }

    if (method === 'verify') {
      if (typeof adapter.verify === 'function') {
        return normalizeBridgeRpcResult(
          await adapter.verify(params.kind, params, context, params.actionResult),
          baseSnapshot,
          { pageType: context.pageType },
        );
      }
      return {
        ok: false,
        source: 'extension-rpc',
        site: baseSnapshot.site,
        page: baseSnapshot.page,
        error: 'Adapter does not support verify',
        pageType: context.pageType,
      };
    }

    return {
      ok: false,
      source: 'extension-rpc',
      site: baseSnapshot.site,
      page: baseSnapshot.page,
      error: `Unknown method: ${method}`,
      pageType: context.pageType,
    };
  } catch (error) {
    return {
      ok: false,
      source: 'extension-rpc',
      site: baseSnapshot.site,
      page: baseSnapshot.page,
      error: error?.message || String(error),
      pageType: context.pageType,
    };
  }
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
let bridgeRpcPollStarted = false;
let bridgeRpcInFlight = false;

async function pollBridgeCommandOnce() {
  if (bridgeRpcInFlight) return;
  bridgeRpcInFlight = true;
  try {
    const response = await chrome.runtime.sendMessage({
      action: 'bridgePullOnce',
      pageUrl: location.href,
    });
    const command = response?.command;
    if (!command) return;
    const result = await handleBridgeRpc({
      method: command.method,
      params: command.params || {},
      commandId: command.id,
    });
    await chrome.runtime.sendMessage({
      action: 'bridgeSubmitResult',
      commandId: command.id,
      result,
    });
  } catch (error) {
    console.warn('[Browser Bridge] bridge rpc poll failed:', error?.message || String(error));
  } finally {
    bridgeRpcInFlight = false;
  }
}

function startBridgeRpcPolling() {
  if (bridgeRpcPollStarted) return;
  bridgeRpcPollStarted = true;
  void pollBridgeCommandOnce();
  setInterval(() => {
    void pollBridgeCommandOnce();
  }, 1000);
}

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

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === 'bridgeRpc') {
    handleBridgeRpc(request.payload).then(sendResponse);
    return true;
  }
});

document.dispatchEvent(new CustomEvent('browserBridgeReady', {
  detail: { version: '1.0.0' }
}));

reportSnapshot('initial');
startObservation();
startBridgeRpcPolling();
