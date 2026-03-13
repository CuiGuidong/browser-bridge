import asyncio
import json

import websockets

from .config import CDP_HOST_HEADER, CDP_TIMEOUT_SECONDS, CDP_WS_BASE_URL


class CdpWebSocketClientError(Exception):
    pass


class CdpWebSocketClient:
    def __init__(self, ws_base_url=CDP_WS_BASE_URL, host_header=CDP_HOST_HEADER, timeout=CDP_TIMEOUT_SECONDS):
        self.ws_base_url = ws_base_url.rstrip("/")
        self.host_header = host_header
        self.timeout = timeout

    def call(self, websocket_debugger_url, method, params=None):
        return asyncio.run(self._call(websocket_debugger_url, method, params or {}))

    async def _call(self, websocket_debugger_url, method, params):
        ws_url = websocket_debugger_url.replace("ws://127.0.0.1:9333", self.ws_base_url)
        try:
            async with websockets.connect(
                ws_url,
                additional_headers={"Host": self.host_header},
                open_timeout=self.timeout,
                close_timeout=self.timeout,
            ) as ws:
                await ws.send(json.dumps({"id": 1, "method": method, "params": params}))
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                    message = json.loads(raw)
                    if message.get("id") == 1:
                        if "error" in message:
                            raise CdpWebSocketClientError(str(message["error"]))
                        return message.get("result", {})
        except Exception as e:
            raise CdpWebSocketClientError(f"WebSocket CDP call failed: {method}: {e}") from e
