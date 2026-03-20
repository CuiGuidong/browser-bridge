import asyncio
import json
import socket

import websockets

from .config import CDP_HOST_HEADER, CDP_TIMEOUT_SECONDS, CDP_WS_BASE_URL

# --- MONKEY PATCH SOCKET FOR WEBSOCKETS ---
# Edge CDP strictly rejects WS connections if the Host header is not 127.0.0.1/localhost.
# The websockets library generates the Host header based on the connection URI and doesn't allow cleanly overriding it without duplicates.
# So we tell websockets to connect to ws://127.0.0.1:9333, but at the TCP level we route it to host.orb.internal.
_orig_create_connection = socket.create_connection
def _patched_create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None, *args, **kwargs):
    host, port = address
    if host == "127.0.0.1" and port == 9333:
        host = "host.orb.internal"
    return _orig_create_connection((host, port), timeout, source_address, *args, **kwargs)
socket.create_connection = _patched_create_connection

# Asyncio uses a different create_connection internally
import asyncio.base_events
_orig_async_create_connection = asyncio.base_events.BaseEventLoop.create_connection
async def _patched_async_create_connection(self, protocol_factory, host=None, port=None, *args, **kwargs):
    if host == "127.0.0.1" and port == 9333:
        host = "host.orb.internal"
    return await _orig_async_create_connection(self, protocol_factory, host, port, *args, **kwargs)
asyncio.base_events.BaseEventLoop.create_connection = _patched_async_create_connection
# ------------------------------------------

class CdpWebSocketClientError(Exception):
    pass


class CdpWebSocketClient:
    def __init__(self, ws_base_url="ws://127.0.0.1:9333", host_header=CDP_HOST_HEADER, timeout=CDP_TIMEOUT_SECONDS):
        self.ws_base_url = ws_base_url.rstrip("/")
        self.host_header = host_header
        self.timeout = timeout

    def call(self, websocket_debugger_url, method, params=None):
        return asyncio.run(self._call(websocket_debugger_url, method, params or {}))

    async def _call(self, websocket_debugger_url, method, params):
        # We explicitly use 127.0.0.1 here. The monkey patch will redirect it to host.orb.internal at TCP level.
        ws_url = websocket_debugger_url.replace("ws://host.orb.internal:9333", "ws://127.0.0.1:9333")
        try:
            async with websockets.connect(
                ws_url,
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
