"""Native Session Manager.

Manages extension sessions connected via Native Messaging host shim.
Supports HTTP long-poll transport: shim registers via /native/session/register,
polls via /native/session/pull, posts results via /native/session/result.

All methods are thread-safe. No asyncio.Queue dependency.
"""
import logging
import time
import uuid
import threading

logger = logging.getLogger(__name__)


class NativeSessionManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._sessions = {}  # session_id -> session info dict
        self._command_queues = {}  # session_id -> list of pending commands
        self._pending_results = {}  # command_id -> _ResultFuture
        self._report_cache = {}  # session_id -> last report payload

    def register_session(self):
        """Register a new session. Returns session_id."""
        session_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._sessions[session_id] = {"created": time.time(), "last_pull": time.time()}
            self._command_queues[session_id] = []
            self._cleanup_stale_sessions()
        logger.info(f"[NativeSession] session {session_id} registered, active: {len(self._sessions)}")
        return session_id

    def unregister_session(self, session_id):
        """Clean up a session."""
        with self._lock:
            self._sessions.pop(session_id, None)
            self._command_queues.pop(session_id, None)
            self._report_cache.pop(session_id, None)
        # Fail any pending commands for this session
        with self._lock:
            for cmd_id, rf in list(self._pending_results.items()):
                if rf.session_id == session_id and not rf.is_set():
                    rf.set_result({"ok": False, "error": {"code": "session_disconnected", "message": f"Session {session_id} disconnected"}})
        logger.info(f"[NativeSession] session {session_id} unregistered")

    def _cleanup_stale_sessions(self):
        """Remove sessions that haven't pulled in 60 seconds. Caller must hold _lock."""
        now = time.time()
        stale = [sid for sid, info in self._sessions.items()
                 if now - info.get("last_pull", info.get("created", 0)) > 60]
        for sid in stale:
            self._sessions.pop(sid, None)
            self._command_queues.pop(sid, None)
            self._report_cache.pop(sid, None)
            logger.info(f"[NativeSession] cleaned up stale session {sid}")

    def enqueue_command(self, session_id, method, params=None):
        """Enqueue a command for the shim to pull. Returns command_id."""
        cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
        cmd_msg = {"id": cmd_id, "method": method, "params": params or {}}
        with self._lock:
            q = self._command_queues.get(session_id)
            if q is not None:
                q.append(cmd_msg)
        return cmd_id

    def pull_command(self, session_id, timeout_seconds=25):
        """Long-pull: wait for next command from the queue. Thread-safe blocking."""
        with self._lock:
            if session_id not in self._sessions:
                return {"_error": "session_not_found"}
            self._sessions[session_id]["last_pull"] = time.time()

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            with self._lock:
                q = self._command_queues.get(session_id)
                if q is None:
                    return {"_error": "session_not_found"}
                if q:
                    return q.pop(0)
            time.sleep(0.1)

        return None  # Normal timeout, no commands available

    def store_result(self, command_id, result):
        """Store result from shim. Wakes up the waiting send_command caller."""
        with self._lock:
            rf = self._pending_results.pop(command_id, None)
        if rf and not rf.is_set():
            if "error" in result:
                rf.set_result({"ok": False, "error": result["error"]})
            else:
                rf.set_result({"ok": True, "data": result.get("result", {})})

    def store_report(self, session_id, payload):
        """Store page-state report from shim."""
        with self._lock:
            self._report_cache[session_id] = {
                "payload": payload,
                "timestamp": time.time(),
            }

    def send_command(self, session_id, method, params=None, timeout_seconds=30):
        """Send a command and wait for the result. Thread-safe blocking."""
        with self._lock:
            self._cleanup_stale_sessions()
            if session_id not in self._sessions:
                return {"ok": False, "error": {"code": "session_not_found", "message": f"Session {session_id} not found"}}

            # Create future BEFORE enqueueing to prevent race condition
            cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
            rf = _ResultFuture(session_id)
            self._pending_results[cmd_id] = rf

            # Enqueue command
            cmd_msg = {"id": cmd_id, "method": method, "params": params or {}}
            q = self._command_queues.get(session_id)
            if q is not None:
                q.append(cmd_msg)

        try:
            result = rf.wait(timeout_seconds)
            if result is None:
                self._pending_results.pop(cmd_id, None)
                return {"ok": False, "error": {"code": "timeout", "message": f"Command {method} timed out after {timeout_seconds}s"}}
            return result
        except Exception as e:
            self._pending_results.pop(cmd_id, None)
            return {"ok": False, "error": {"code": "send_failed", "message": str(e)}}

    # Alias for compatibility
    send_command_sync = send_command

    def get_active_session(self):
        """Return the most recently active session_id, or None."""
        with self._lock:
            self._cleanup_stale_sessions()
            if not self._sessions:
                return None
            return max(self._sessions, key=lambda sid: self._sessions[sid].get("last_pull", self._sessions[sid].get("created", 0)))

    def get_report(self, session_id=None):
        """Get the latest report for a session."""
        sid = session_id or self.get_active_session()
        if not sid:
            return None
        with self._lock:
            self._cleanup_stale_sessions()
            return self._report_cache.get(sid)

    @property
    def session_count(self):
        with self._lock:
            return len(self._sessions)


class _ResultFuture:
    """Thread-safe result future using threading.Event."""
    def __init__(self, session_id):
        self.session_id = session_id
        self._event = threading.Event()
        self._result = None

    def set_result(self, result):
        self._result = result
        self._event.set()

    def is_set(self):
        return self._event.is_set()

    def wait(self, timeout):
        """Wait for result. Returns result dict or None on timeout."""
        if self._event.wait(timeout):
            return self._result
        return None
