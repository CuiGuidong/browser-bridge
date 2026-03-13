// Background service worker for Browser Bridge Extension

const BRIDGE_URL = 'http://127.0.0.1:17777';

// Listen for messages from content script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getPageInfo') {
    handleGetPageInfo(sendResponse);
    return true; // Keep channel open for async
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
});

async function handleGetPageInfo(sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      sendResponse({ ok: false, error: 'No active tab' });
      return;
    }
    
    sendResponse({
      ok: true,
      title: tab.title,
      url: tab.url,
      id: tab.id,
    });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleGetPageContent(sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      sendResponse({ ok: false, error: 'No active tab' });
      return;
    }
    
    // Execute script in page to get content
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        return {
          title: document.title,
          text: document.body?.innerText?.slice(0, 8000) || '',
          url: location.href,
        };
      },
    });
    
    sendResponse({ ok: true, data: results[0]?.result });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleClickElement(selector, sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      sendResponse({ ok: false, error: 'No active tab' });
      return;
    }
    
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (sel) => {
        const el = document.querySelector(sel);
        if (!el) return { ok: false, error: 'Element not found' };
        el.click();
        return { ok: true, tag: el.tagName, text: el.innerText?.slice(0, 100) };
      },
      args: [selector],
    });
    
    sendResponse(results[0]?.result);
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleFillElement(selector, text, sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      sendResponse({ ok: false, error: 'No active tab' });
      return;
    }
    
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (sel, txt) => {
        const el = document.querySelector(sel);
        if (!el) return { ok: false, error: 'Element not found' };
        
        const canFill = ('value' in el) || el.isContentEditable;
        if (!canFill) return { ok: false, error: 'Not fillable', tag: el.tagName };
        
        el.focus();
        if ('value' in el) el.value = txt;
        else el.textContent = txt;
        
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        
        return { ok: true, tag: el.tagName };
      },
      args: [selector, text],
    });
    
    sendResponse(results[0]?.result);
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}

async function handleQueryElements(selector, sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      sendResponse({ ok: false, error: 'No active tab' });
      return;
    }
    
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (sel) => {
        const nodes = Array.from(document.querySelectorAll(sel)).slice(0, 20);
        return nodes.map((el, index) => ({
          index,
          tag: el.tagName,
          id: el.id || '',
          classes: el.className || '',
          text: (el.innerText || el.textContent || '').trim().slice(0, 200),
          href: el.href || '',
        }));
      },
      args: [selector],
    });
    
    sendResponse({ ok: true, elements: results[0]?.result });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
}