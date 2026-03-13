import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .config import BRIDGE_HOST, BRIDGE_PORT
from .cdp_service import BrowserBridgeService
from .routes import (
    handle_activate,
    handle_click,
    handle_fill,
    handle_health,
    handle_open,
    handle_page_content,
    handle_page_info,
    handle_query,
    handle_screenshot,
    handle_tabs,
    handle_version,
    handle_wait,
)


service = BrowserBridgeService()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            status, payload = handle_health(service)
            return self._send_json(status, payload)
        if parsed.path == "/version":
            status, payload = handle_version(service)
            return self._send_json(status, payload)
        if parsed.path == "/tabs":
            status, payload = handle_tabs(service)
            return self._send_json(status, payload)
        if parsed.path == "/wait":
            status, payload = handle_wait(service, parse_qs(parsed.query))
            return self._send_json(status, payload)
        if parsed.path == "/page-info":
            status, payload = handle_page_info(service, parse_qs(parsed.query))
            return self._send_json(status, payload)
        if parsed.path == "/page-content":
            status, payload = handle_page_content(service, parse_qs(parsed.query))
            return self._send_json(status, payload)
        if parsed.path == "/query":
            status, payload = handle_query(service, parse_qs(parsed.query))
            return self._send_json(status, payload)
        return self._send_json(404, {"ok": False, "action": "route", "message": "not found"})

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)).decode("utf-8")
        if self.path == "/open":
            status, payload = handle_open(service, body)
            return self._send_json(status, payload)
        if self.path == "/activate":
            status, payload = handle_activate(service, body)
            return self._send_json(status, payload)
        if self.path == "/screenshot":
            status, payload = handle_screenshot(service, body)
            return self._send_json(status, payload)
        if self.path == "/click":
            status, payload = handle_click(service, body)
            return self._send_json(status, payload)
        if self.path == "/fill":
            status, payload = handle_fill(service, body)
            return self._send_json(status, payload)
        return self._send_json(404, {"ok": False, "action": "route", "message": "not found"})

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


def run():
    server = HTTPServer((BRIDGE_HOST, BRIDGE_PORT), Handler)
    print(f"browser-bridge listening on http://{BRIDGE_HOST}:{BRIDGE_PORT}")
    server.serve_forever()
