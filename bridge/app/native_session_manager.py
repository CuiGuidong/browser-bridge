"""Native Session Manager.

Manages extension sessions connected via Native Messaging host shim.
Supports two transport modes:
- HTTP long-poll: shim registers via /native/session/register, polls via /native/session/pull
- WebSocket: shim connects to /native/ws (alternative, not required)
"""
import asyncio
import json
import logging
import time
import uuid

logger = logging.getLogger(__name__)


class NativeSessionManager:
    def __init__(self):
        self._sessions = {}  # session_id -> session info
        self._command_queues = {}  # session_id -> asyncio.Queue of commands
        self._pending_results = {}  # command_id -> asyncio.Future
        self._report_cache = {}  # session_id -> last report payload
        self._lock = asyncio.Lock()

    def register_session(self):
        """Register a new session (HTTP mode). Returns session_id."""
        session_id = str(uuid.uuid4())[:8]
        self._sessions[session_id] = {"created": time.time(), "last_pull": time.time()}
        self._command_queues[session_id] = asyncio.Queue()
        # Clean up stale sessions (no pull in 60 seconds)
        self._cleanup_stale_sessions()
        logger.info(f"[NativeSession] session {session_id} registered, active sessions: {len(self._sessions)}")
        return session_id

    def _cleanup_stale_sessions(self):
        """Remove sessions that haven't pulled in 60 seconds."""
        now = time.time()
        stale = [sid for sid, info in self._sessions.items()
                 if now - info.get("last_pull", info.get("created", 0)) > 60]
        for sid in stale:
            self.unregister_session(sid)
            logger.info(f"[NativeSession] cleaned up stale session {sid}")

    def unregister_session(self, session_id):
        """Clean up a session."""
        self._sessions.pop(session_id, None)
        self._command_queues.pop(session_id, None)
        self._report_cache.pop(session_id, None)
        # Fail any pending commands
        for cmd_id, future in list(self._pending_results.items()):
            if not future.done():
                future.set_result({"ok": False, "error": {"code": "session_disconnected", "message": f"Session {session_id} disconnected"}})
        logger.info(f"[NativeSession] session {session_id} unregistered")

    async def enqueue_command(self, session_id, method, params=None):
        """Enqueue a command for the shim to pull. Returns command_id."""
        cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
        cmd_msg = {"id": cmd_id, "method": method, "params": params or {}}
        q = self._command_queues.get(session_id)
        if q:
            await q.put(cmd_msg)
        return cmd_id

    async def pull_command(self, session_id, timeout_seconds=25):
        """Long-pull: wait for next command from the queue."""
        # Update last_pull timestamp
        if session_id in self._sessions:
            self._sessions[session_id]["last_pull"] = time.time()
        q = self._command_queues.get(session_id)
        if not q:
            return None
        try:
            cmd = await asyncio.wait_for(q.get(), timeout=timeout_seconds)
            return cmd
        except asyncio.TimeoutError:
            return None

    def store_result(self, command_id, result):
        """Store result from shim. Wakes up the waiting send_command caller."""
        future = self._pending_results.pop(command_id, None)
        if future and not future.done():
            if "error" in result:
                future.set_result({"ok": False, "error": result["error"]})
            else:
                future.set_result({"ok": True, "data": result.get("result", {})})

    def store_report(self, session_id, payload):
        """Store page-state report from shim."""
        self._report_cache[session_id] = {
            "payload": payload,
            "timestamp": time.time(),
        }

    async def send_command(self, session_id, method, params=None, timeout_seconds=30):
        """Send a command to a session and wait for the result."""
        if session_id not in self._sessions:
            return {"ok": False, "error": {"code": "session_not_found", "message": f"Session {session_id} not found"}}

        cmd_id = await self.enqueue_command(session_id, method, params)

        future = asyncio.get_event_loop().create_future()
        self._pending_results[cmd_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            self._pending_results.pop(cmd_id, None)
            return {"ok": False, "error": {"code": "timeout", "message": f"Command {method} timed out after {timeout_seconds}s"}}
        except Exception as e:
            self._pending_results.pop(cmd_id, None)
            return {"ok": False, "error": {"code": "send_failed", "message": str(e)}}

    def get_active_session(self):
        """Return the most recently registered session_id, or None."""
        if not self._sessions:
            return None
        # Return the session with the latest last_pull or created time
        return max(self._sessions, key=lambda sid: self._sessions[sid].get("last_pull", self._sessions[sid].get("created", 0)))

    def get_report(self, session_id=None):
        """Get the latest report for a session."""
        sid = session_id or self.get_active_session()
        if not sid:
            return None
        return self._report_cache.get(sid)

    @property
    def session_count(self):
        return len(self._sessions)
