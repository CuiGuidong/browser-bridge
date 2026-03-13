// Content script - injected into all pages
// Acts as a bridge between page and extension

console.log('[Browser Bridge] Content script loaded');

// Listen for messages from the page (if needed for future bi-directional communication)
window.addEventListener('message', (event) => {
  // Only accept messages from same origin
  if (event.source !== window) return;
  
  if (event.data.type && event.data.type === 'BROWSER_BRIDGE_REQUEST') {
    // Forward to background script
    chrome.runtime.sendMessage(event.data.payload, (response) => {
      window.postMessage({
        type: 'BROWSER_BRIDGE_RESPONSE',
        id: event.data.id,
        response: response,
      }, '*');
    });
  }
});

// Notify that extension is ready
document.dispatchEvent(new CustomEvent('browserBridgeReady', {
  detail: { version: '1.0.0' }
}));