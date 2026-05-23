// Background service worker for Browser Bridge Extension

const BRIDGE_URL = 'http://127.0.0.1:17777';
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
// chrome.alarms wakes the worker from suspension, keeping the polling loop running.
chrome.alarms.create('keepalive', { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'keepalive') {
    void pollDevCommandOnce();
  }
});
