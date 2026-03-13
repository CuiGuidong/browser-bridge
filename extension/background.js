// Background service worker for Browser Bridge Extension
importScripts('site-adapters.js');

const BRIDGE_URL = 'http://127.0.0.1:17777';
const X_OBSERVE_WINDOW_MS = 15000;
const X_REPORT_INTERVAL_MS = 1500;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getPageInfo') {
    handleGetPageInfo(sendResponse);
    return true;
  }
  if (request.action === 'getPageContent') {
    handleGetPageContent(sendResponse);
    return true;
  }
  if (request.action === 'clickElement') {
    handleClickElement(request.selector, sendResponse);
    return true;
  }
  if (request.action === 'fillElement') {
    handleFillElement(request.selector, request.text, sendResponse);
    return true;
  }
  if (request.action === 'queryElements') {
    handleQueryElements(request.selector, sendResponse);
    return true;
  }
  if (request.action === 'reportActivePage') {
    handleReportActivePage(sendResponse);
    return true;
  }
  if (request.action === 'extensionSnapshot') {
    postReport(request.payload).then((delivered) => sendResponse({ ok: true, delivered }));
    return true;
  }
});

chrome.tabs.onActivated.addListener(() => {
  safeReportActivePage();
});
chrome.tabs.onUpdated.addListener((_tabId, changeInfo) => {
  if (changeInfo.status === 'complete') {
    safeReportActivePage();
  }
});

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function executeInActiveTab(func, args = []) {
  const tab = await getActiveTab();
  if (!tab) throw new Error('No active tab');
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func,
    args,
  });
  return { tab, result: results[0]?.result };
}

function collectPageSignals() {
  return collectActiveSiteSnapshot();
}

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

async function handleReportActivePage(sendResponse) {
  try {
    const { tab, result } = await executeInActiveTab(collectPageSignals);
    const payload = {
      source: 'extension',
      site: result.site,
      kind: 'page-state',
      page: { ...result.page, tabId: tab.id },
      signals: result.signals,
      content: result.content,
    };
    const delivered = await postReport(payload);
    sendResponse({ ok: true, delivered, payload });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function safeReportActivePage() {
  try {
    await new Promise((resolve) => {
      handleReportActivePage(() => resolve());
    });
  } catch {}
}

async function observeActivePageForReady(windowMs = X_OBSERVE_WINDOW_MS, intervalMs = X_REPORT_INTERVAL_MS) {
  const started = Date.now();
  while (Date.now() - started < windowMs) {
    try {
      const { result } = await executeInActiveTab(collectPageSignals);
      const delivered = await postReport({
        source: 'extension',
        site: result.site,
        kind: 'page-state',
        page: result.page,
        signals: result.signals,
        content: result.content,
      });
      if (result.signals?.ready) return { ok: true, delivered, ready: true };
    } catch (error) {
      console.warn('[Browser Bridge] observe failed:', error.message);
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return { ok: false, ready: false };
}

async function handleGetPageInfo(sendResponse) {
  try {
    const tab = await getActiveTab();
    if (!tab) return sendResponse({ ok: false, error: 'No active tab' });
    sendResponse({ ok: true, title: tab.title, url: tab.url, id: tab.id });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleGetPageContent(sendResponse) {
  try {
    const { result } = await executeInActiveTab(() => ({
      title: document.title,
      text: document.body?.innerText?.slice(0, 8000) || '',
      url: location.href,
    }));
    sendResponse({ ok: true, data: result });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleClickElement(selector, sendResponse) {
  try {
    const { result } = await executeInActiveTab((sel) => {
      const el = document.querySelector(sel);
      if (!el) return { ok: false, error: 'Element not found' };
      el.click();
      return { ok: true, tag: el.tagName, text: el.innerText?.slice(0, 100) };
    }, [selector]);
    sendResponse(result);
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleFillElement(selector, text, sendResponse) {
  try {
    const { result } = await executeInActiveTab((sel, txt) => {
      const el = document.querySelector(sel);
      if (!el) return { ok: false, error: 'Element not found' };
      const canFill = ('value' in el) || el.isContentEditable;
      if (!canFill) return { ok: false, error: 'Not fillable', tag: el.tagName };
      el.focus();
      if ('value' in el) el.value = txt; else el.textContent = txt;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return { ok: true, tag: el.tagName };
    }, [selector, text]);
    sendResponse(result);
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleQueryElements(selector, sendResponse) {
  try {
    const { result } = await executeInActiveTab((sel) => {
      const nodes = Array.from(document.querySelectorAll(sel)).slice(0, 20);
      return nodes.map((el, index) => ({
        index,
        tag: el.tagName,
        id: el.id || '',
        classes: el.className || '',
        text: (el.innerText || el.textContent || '').trim().slice(0, 200),
        href: el.href || '',
      }));
    }, [selector]);
    sendResponse({ ok: true, elements: result });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}