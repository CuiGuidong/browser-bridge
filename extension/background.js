// Background service worker for Browser Bridge Extension

const BRIDGE_URL = 'http://127.0.0.1:17777';

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
});

chrome.tabs.onActivated.addListener(() => {
  safeReportActivePage();
});
chrome.tabs.onUpdated.addListener((_tabId, changeInfo) => {
  if (changeInfo.status === 'complete') safeReportActivePage();
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
  const url = location.href;
  const title = document.title || '';
  const hostname = location.hostname;
  const text = (document.body?.innerText || '').trim();
  const isX = hostname.includes('x.com') || hostname.includes('twitter.com');
  const article = document.querySelector('article');
  const tweetText = document.querySelector('[data-testid="tweetText"]');
  const loginMask = !!document.querySelector('[data-testid="sheetDialog"], [role="dialog"]');
  const primaryText = (tweetText?.innerText || article?.innerText || '').trim();
  const isTweetDetail = /\/status\/\d+/.test(url);
  const ready = isX
    ? !!(isTweetDetail && article && primaryText.length > 20)
    : text.length > 120;
  return {
    site: isX ? 'x' : hostname,
    page: {
      url,
      title,
      hostname,
    },
    signals: {
      readyState: document.readyState,
      bodyTextLength: text.length,
      isX,
      isTweetDetail,
      articleFound: !!article,
      tweetTextFound: !!tweetText,
      loginMask,
      ready,
    },
    content: {
      primaryText: primaryText.slice(0, 4000),
    },
  };
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