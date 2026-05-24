// Popup script

document.addEventListener('DOMContentLoaded', async () => {
  const statusEl = document.getElementById('status');
  const checkBtn = document.getElementById('checkBridge');

  async function checkBridge() {
    statusEl.textContent = 'Checking...';
    statusEl.className = 'status disconnected';

    try {
      const response = await chrome.runtime.sendMessage({ action: 'getStatus' });
      if (response?.connected) {
        statusEl.textContent = `Connected: ${response.browser || 'Bridge OK'}`;
        statusEl.className = 'status connected';
      } else {
        statusEl.textContent = 'Not connected';
        statusEl.className = 'status disconnected';
      }
    } catch (error) {
      statusEl.textContent = 'Extension not ready';
      statusEl.className = 'status disconnected';
    }
  }

  checkBtn.addEventListener('click', checkBridge);
  checkBridge();
});
