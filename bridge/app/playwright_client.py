"""
Playwright client for complex page operations.
Uses attach mode to connect to existing browser instance, not launch new ones.
"""

from playwright.sync_api import sync_playwright
from typing import Optional, Dict, Any, List


class PlaywrightClient:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
    
    def connect(self, cdp_url: str) -> bool:
        """
        Connect to existing browser via CDP.
        cdp_url format: ws://127.0.0.1:9333/devtools/browser/xxx
        """
        try:
            self.playwright = sync_playwright().start()
            # Connect to existing browser via CDP
            self.browser = self.playwright.chromium.connect_over_cdp(cdp_url)
            return True
        except Exception as e:
            print(f"Failed to connect via Playwright: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from browser."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.browser = None
        self.playwright = None
    
    def get_page(self, target_id: str, all_pages: List) -> Optional[Any]:
        """Get page by target ID."""
        if not self.browser:
            return None
        for p in self.browser.contexts[0].pages if self.browser.contexts else []:
            # Try to match by URL or title (CDP target_id not directly accessible)
            if hasattr(p, '_impl_obj'):
                # This is a best-effort match
                pass
        # For now, return first page
        return self.browser.contexts[0].pages[0] if self.browser.contexts and self.browser.contexts[0].pages else None
    
    def get_all_pages(self) -> List[Dict[str, str]]:
        """Get all pages from connected browser."""
        if not self.browser or not self.browser.contexts:
            return []
        
        pages = []
        for ctx in self.browser.contexts:
            for p in ctx.pages:
                try:
                    pages.append({
                        "url": p.url,
                        "title": p.title(),
                    })
                except:
                    pass
        return pages
    
    def evaluate(self, expression: str) -> Any:
        """Execute JavaScript in current page."""
        if not self.browser or not self.browser.contexts:
            return None
        # Execute in first page
        page = self.browser.contexts[0].pages[0]
        return page.evaluate(expression)
    
    def click(self, selector: str) -> Dict[str, Any]:
        """Click element by selector."""
        if not self.browser or not self.browser.contexts:
            return {"ok": False, "error": "not connected"}
        
        page = self.browser.contexts[0].pages[0]
        try:
            page.click(selector)
            return {
                "ok": True,
                "tag": "clicked",
                "url": page.url,
                "title": page.title(),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def fill(self, selector: str, text: str) -> Dict[str, Any]:
        """Fill input by selector."""
        if not self.browser or not self.browser.contexts:
            return {"ok": False, "error": "not connected"}
        
        page = self.browser.contexts[0].pages[0]
        try:
            page.fill(selector, text)
            return {
                "ok": True,
                "tag": "filled",
                "url": page.url,
                "title": page.title(),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def wait_for_selector(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for selector to appear."""
        if not self.browser or not self.browser.contexts:
            return False
        
        page = self.browser.contexts[0].pages[0]
        try:
            page.wait_for_selector(selector, timeout=timeout)
            return True
        except:
            return False
    
    def wait_for_load_state(self, state: str = "networkidle") -> bool:
        """Wait for page load state."""
        if not self.browser or not self.browser.contexts:
            return False
        
        page = self.browser.contexts[0].pages[0]
        try:
            page.wait_for_load_state(state)
            return True
        except:
            return False


# Global client instance
_client: Optional[PlaywrightClient] = None


def get_playwright_client() -> PlaywrightClient:
    """Get or create global Playwright client."""
    global _client
    if _client is None:
        _client = PlaywrightClient()
    return _client


def reset_playwright_client():
    """Reset global client."""
    global _client
    if _client:
        _client.disconnect()
    _client = None