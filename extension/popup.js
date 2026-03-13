// Popup script

const BRIDGE_URL = 'http://127.0.0.1:17777';

document.addEventListener('DOMContentLoaded', async () => {
  const statusEl = document.getElementById('status');
  const checkBtn = document.getElementById('checkBridge');
  
  async function checkBridge() {
    statusEl.textContent = 'Checking...';
    statusEl.className = 'status disconnected';
    
    try {
      const response = await fetch(`${BRIDGE_URL}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      
      if (response.ok) {
        const data = await response.json();
        statusEl.textContent = `Connected: ${data.data?.browser || 'Bridge OK'}`;
        statusEl.className = 'status connected';
      } else {
        statusEl.textContent = 'Bridge returned error';
        statusEl.className = 'status disconnected';
      }
    } catch (error) {
      statusEl.textContent = 'Not connected - Start bridge first';
      statusEl.className = 'status disconnected';
    }
  }
  
  checkBtn.addEventListener('click', checkBridge);
  
  // Auto-check on open
  checkBridge();
});