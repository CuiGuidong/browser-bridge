#!/usr/bin/env python3
"""Native Messaging host shim for Browser Bridge.

Launched by the browser when the extension calls connectNative().
Bridges stdin/stdout (Native Messaging protocol) to Bridge daemon via HTTP long-poll.

Zero third-party dependencies — uses only Python stdlib.
"""
import struct
import sys
import json
import threading
import urllib.request
import os
from pathlib import Path


def _load_env_file(path):
    values = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                if key:
                    values[key] = value
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return values


def _resolve_bridge_url():
    if os.environ.get("BRIDGE_URL"):
        return os.environ["BRIDGE_URL"].rstrip("/")

    repo_root = Path(__file__).resolve().parents[2]
    env_values = _load_env_file(repo_root / ".env.local")
    if env_values.get("BRIDGE_URL"):
        return env_values["BRIDGE_URL"].rstrip("/")

    host = env_values.get("BRIDGE_HOST") or os.environ.get("BRIDGE_HOST") or "127.0.0.1"
    port = env_values.get("BRIDGE_PORT") or os.environ.get("BRIDGE_PORT") or "17777"
    connect_host = "127.0.0.1" if host == "0.0.0.0" else host
    return f"http://{connect_host}:{port}".rstrip("/")


BRIDGE_URL = _resolve_bridge_url()
SESSION_ID = None


def _log(message, exc_info=None):
    line = f"[shim] {message}\n"
    log_path = os.environ.get("BROWSER_BRIDGE_SHIM_LOG")
    if log_path:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line)
                if exc_info is not None:
                    import traceback
                    traceback.print_exception(type(exc_info), exc_info, exc_info.__traceback__, file=f)
                f.flush()
            return
        except Exception:
            pass
    sys.stderr.write(line)
    if exc_info is not None:
        import traceback
        traceback.print_exception(type(exc_info), exc_info, exc_info.__traceback__, file=sys.stderr)
    sys.stderr.flush()


def read_native_message():
    """Read one length-prefixed JSON message from stdin (blocking)."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length or len(raw_length) < 4:
        return None
    length = struct.unpack('<I', raw_length)[0]
    data = sys.stdin.buffer.read(length)
    if not data:
        return None
    return json.loads(data)


def write_native_message(msg):
    """Write one length-prefixed JSON message to stdout."""
    encoded = json.dumps(msg, ensure_ascii=False).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('<I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def post_json(path, payload, timeout=30):
    """POST JSON to bridge daemon."""
    try:
        req = urllib.request.Request(
            f"{BRIDGE_URL}{path}",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read())
    except Exception:
        return None


def get_json(path, timeout=30):
    """GET JSON from bridge daemon."""
    try:
        req = urllib.request.Request(f"{BRIDGE_URL}{path}")
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read())
    except Exception:
        return None


def register_session():
    """Register this shim as a native session with the bridge daemon."""
    global SESSION_ID
    _log("registering session...")
    resp = post_json("/native/session/register", {"type": "extension"})
    _log(f"register response: {resp}")
    if resp and resp.get("ok"):
        SESSION_ID = resp["data"]["sessionId"]
        return True
    return False


def unregister_session():
    """Unregister this session with the bridge daemon."""
    if not SESSION_ID:
        return
    _log(f"unregistering session {SESSION_ID}...")
    resp = post_json(f"/native/session/unregister?sessionId={SESSION_ID}", {})
    _log(f"unregister response: {resp}")


def pull_command():
    """Long-poll for next command from daemon. Returns command dict, None for timeout, or 'reregister' sentinel."""
    if not SESSION_ID:
        return None
    resp = get_json(f"/native/session/pull?sessionId={SESSION_ID}&timeoutSeconds=25", timeout=30)
    if resp and resp.get("ok"):
        cmd = resp.get("data", {}).get("command")
        if cmd and isinstance(cmd, dict) and cmd.get("_error") == "session_not_found":
            return "reregister"
        return cmd
    return None


def post_result(msg):
    """Send result or report back to daemon."""
    if not SESSION_ID:
        return
    post_json("/native/session/result", {"sessionId": SESSION_ID, "message": msg}, timeout=10)


def daemon_to_extension():
    """Thread: pull commands from daemon and write to stdout (extension)."""
    while True:
        try:
            cmd = pull_command()
            if cmd == "reregister":
                _log("session not found, re-registering")
                if not register_session():
                    import time
                    time.sleep(2)
                continue
            if cmd is None:
                import time
                time.sleep(1)
                continue
            write_native_message(cmd)
            _log(f"wrote command to stdout: {cmd.get('method', '?')}")
        except Exception as e:
            _log(f"daemon_to_extension error: {e}")
            import time
            time.sleep(2)


def main():
    import os
    _log(f"main() started, pid={os.getpid()}")

    if not register_session():
        _log("registration failed, exiting")
        return

    # Background thread: daemon → extension (commands via stdout)
    t = threading.Thread(target=daemon_to_extension, daemon=True)
    t.start()

    # Main thread: extension → daemon (results/reports via stdin)
    # Exit on stdin EOF — browser will launch a new shim on reconnect
    import select
    _log("entering main loop, waiting for stdin data")
    while True:
        try:
            ready, _, _ = select.select([sys.stdin.buffer], [], [], 5.0)
            if ready:
                msg = read_native_message()
                if msg is None:
                    # stdin EOF — extension disconnected, exit cleanly
                    _log("stdin EOF, exiting")
                    break
                post_result(msg)
        except Exception as e:
            _log(f"main loop error: {e}")
            import time
            time.sleep(2)


if __name__ == '__main__':
    import os
    _log(f"started, pid={os.getpid()}")
    try:
        main()
    except Exception as e:
        _log(f"fatal: {e}", exc_info=e)
    finally:
        unregister_session()
        _log("exited")
