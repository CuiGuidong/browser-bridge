// Background service worker for Browser Bridge Extension

const BRIDGE_URL = 'http://127.0.0.1:17777';

// ===== Native Messaging (阶段 1-3: 与 HTTP 轮询并行) =====
let nativePort = null;

function connectNative() {
  try {
    nativePort = chrome.runtime.connectNative('com.cuiguidong.browserbridge');
    nativePort.onMessage.addListener(handleNativeCommand);
    nativePort.onDisconnect.addListener(() => {
      console.warn('[Browser Bridge] Native disconnected:', chrome.runtime.lastError?.message);
      nativePort = null;
    });
    console.log('[Browser Bridge] Native Messaging connected');
  } catch (e) {
    console.warn('[Browser Bridge] connectNative failed:', e.message);
  }
}

connectNative();

function normalizeTab(tab) {
  return { id: String(tab.id), nativeTabId: tab.id, title: tab.title || '', url: tab.url || '', type: 'page' };
}

// attached tab cache for chrome.debugger
const attachedTabs = new Set();

async function ensureDebuggerAttached(tabId) {
  if (attachedTabs.has(tabId)) return;
  const debuggee = { tabId };
  try {
    await chrome.debugger.attach(debuggee, '1.3');
    attachedTabs.add(tabId);
  } catch (e) {
    const msg = e.message || '';
    if (msg.includes('already being debugged') || msg.includes('Another debugger')) {
      throw { code: 'debugger_already_attached', message: msg };
    }
    if (msg.includes('Cannot access') || msg.includes('restricted') || msg.includes('chrome://') || msg.includes('edge://')) {
      throw { code: 'debugger_restricted_domain', message: msg };
    }
    throw { code: 'debugger_attach_failed', message: msg };
  }
}

async function handleDebuggerCommand(method, params) {
  const debuggee = { tabId: params.tabId };
  if (method === 'debugger.attach') {
    if (attachedTabs.has(params.tabId)) return { attached: true, alreadyAttached: true };
    await ensureDebuggerAttached(params.tabId);
    return { attached: true };
  }
  if (method === 'debugger.detach') {
    try { await chrome.debugger.detach(debuggee); } catch (e) {}
    attachedTabs.delete(params.tabId);
    return { detached: true };
  }
  if (method === 'debugger.send') {
    await ensureDebuggerAttached(params.tabId);
    try {
      const result = await chrome.debugger.sendCommand(debuggee, params.command, params.params_ || {});
      return result || {};
    } catch (e) {
      if (e.message?.includes('detached') || e.message?.includes('not attached')) {
        attachedTabs.delete(params.tabId);
      }
      throw { code: 'command_failed', message: e.message };
    }
  }
}

chrome.tabs.onRemoved.addListener((tabId) => { attachedTabs.delete(tabId); });

async function handleNativeCommand(msg) {
  const { id, method, params } = msg;
  try {
    let result;
    if (method === 'ping') {
      result = { alive: true, timestamp: Date.now() };
    } else if (method === 'tabs.list') {
      const tabs = await chrome.tabs.query({});
      result = { tabs: tabs.map(normalizeTab) };
    } else if (method === 'tabs.create') {
      const tab = await chrome.tabs.create({ url: params.url, active: params.active !== false });
      result = { tab: normalizeTab(tab) };
    } else if (method === 'tabs.activate') {
      await chrome.tabs.update(params.tabId, { active: true });
      result = { activated: true };
    } else if (method === 'tabs.close') {
      await chrome.tabs.remove(params.tabId);
      result = { closed: true };
    } else if (method.startsWith('debugger.')) {
      result = await handleDebuggerCommand(method, params);
    } else if (method === 'semantic.invoke') {
      result = await handleSemanticInvoke(params);
    } else {
      result = { error: 'unknown method' };
    }
    nativePort.postMessage({ id, result });
  } catch (error) {
    nativePort.postMessage({ id, error: { code: error.code || 'unknown', message: error.message || String(error) } });
  }
}

async function handleSemanticInvoke(params) {
  const { tabId, method, params: semParams } = params;
  if (!tabId) return { error: { code: 'missing_tab_id', message: 'No tabId in semantic.invoke' } };
  // Forward to content script via chrome.tabs.sendMessage, reusing handleBridgeRpc
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { action: 'bridgeRpc', payload: { method, params: semParams, commandId: `native_${Date.now()}` } }, (response) => {
      if (chrome.runtime.lastError) {
        resolve({ error: { code: 'content_script_error', message: chrome.runtime.lastError.message } });
      } else {
        resolve(response || {});
      }
    });
  });
}

// ===== HTTP 轮询（阶段 1-3 保留，阶段 5 清理） =====
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extensionSnapshot') {
    postReport(request.payload).then((delivered) => sendResponse({ ok: true, delivered }));
    return true;
  }
  if (request.action === 'reloadExtension') {
    sendResponse({ ok: true, reloading: true });
    setTimeout(() => chrome.runtime.reload(), 50);
    return true;
  }
  if (request.action === 'bridgePullOnce') {
    handleBridgePullOnce(request, sender, sendResponse);
    return true;
  }
  if (request.action === 'bridgeSubmitResult') {
    handleBridgeSubmitResult(request.commandId, request.result, sendResponse);
    return true;
  }
});

async function postReport(payload) {
  try {
    await fetch(`${BRIDGE_URL}/extension/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return true;
  } catch (error) {
    console.warn('[Browser Bridge] report failed:', error.message);
    return false;
  }
}

async function fetchBridgeJson(path, init = {}) {
  const response = await fetch(`${BRIDGE_URL}${path}`, init);
  return await response.json();
}

async function pullBridgeCommand(timeoutSeconds = 1, pageUrl = '') {
  const qs = new URLSearchParams({
    timeoutSeconds: String(timeoutSeconds),
  });
  if (pageUrl) qs.set('pageUrl', pageUrl);
  const body = await fetchBridgeJson(`/extension/pull?${qs.toString()}`);
  return body?.data?.command || null;
}

async function postBridgeCommandResult(commandId, result) {
  await fetchBridgeJson('/extension/result', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ commandId, result }),
  });
}

async function handleBridgePullOnce(request, sender, sendResponse) {
  try {
    const command = await pullBridgeCommand(1, request.pageUrl || sender?.tab?.url || '');
    sendResponse({ ok: true, command });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleBridgeSubmitResult(commandId, result, sendResponse) {
  try {
    await postBridgeCommandResult(commandId, result);
    sendResponse({ ok: true });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleDevCommand(command) {
  if (!command || command.method !== 'dev_reload_extension') return false;
  await postBridgeCommandResult(command.id, {
    ok: true,
    source: 'extension-background',
    method: command.method,
    reloading: true,
  });
  setTimeout(() => chrome.runtime.reload(), 50);
  return true;
}

async function pollDevCommandOnce() {
  try {
    const command = await pullBridgeCommand(1, 'chrome-extension://browser-bridge/background');
    await handleDevCommand(command);
  } catch (error) {
    console.warn('[Browser Bridge] dev command poll failed:', error.message);
  }
}

void pollDevCommandOnce();
setInterval(() => {
  void pollDevCommandOnce();
}, 1000);

// Keep service worker alive: MV3 suspends workers after ~30s of inactivity.
chrome.alarms.create('keepalive', { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'keepalive') {
    if (!nativePort) connectNative();
    void pollDevCommandOnce();
  }
});
