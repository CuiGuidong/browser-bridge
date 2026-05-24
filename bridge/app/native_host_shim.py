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

BRIDGE_URL = "http://127.0.0.1:17777"
SESSION_ID = None


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
    import os
    log_path = os.path.expanduser('~/.browser-bridge-shim.log')
    with open(log_path, 'a') as f:
        f.write(f'[shim] registering session...\n')
        f.flush()
    resp = post_json("/native/session/register", {"type": "extension"})
    with open(log_path, 'a') as f:
        f.write(f'[shim] register response: {resp}\n')
        f.flush()
    if resp and resp.get("ok"):
        SESSION_ID = resp["data"]["sessionId"]
        return True
    return False


def unregister_session():
    """Unregister this session with the bridge daemon."""
    if not SESSION_ID:
        return
    import os
    log_path = os.path.expanduser('~/.browser-bridge-shim.log')
    with open(log_path, 'a') as f:
        f.write(f'[shim] unregistering session {SESSION_ID}...\n')
        f.flush()
    resp = post_json(f"/native/session/unregister?sessionId={SESSION_ID}", {})
    with open(log_path, 'a') as f:
        f.write(f'[shim] unregister response: {resp}\n')
        f.flush()


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
    import os
    log_path = os.path.expanduser('~/.browser-bridge-shim.log')
    while True:
        try:
            cmd = pull_command()
            if cmd == "reregister":
                with open(log_path, 'a') as f:
                    f.write(f'[shim] session not found, re-registering\n')
                    f.flush()
                if not register_session():
                    import time
                    time.sleep(2)
                continue
            if cmd is None:
                import time
                time.sleep(1)
                continue
            write_native_message(cmd)
            with open(log_path, 'a') as f:
                f.write(f'[shim] wrote command to stdout: {cmd.get("method", "?")}\n')
                f.flush()
        except Exception as e:
            with open(log_path, 'a') as f:
                f.write(f'[shim] daemon_to_extension error: {e}\n')
                f.flush()
            import time
            time.sleep(2)


def main():
    import os
    log_path = os.path.expanduser('~/.browser-bridge-shim.log')
    with open(log_path, 'a') as f:
        f.write(f'[shim] main() started, pid={os.getpid()}\n')
        f.flush()

    if not register_session():
        with open(log_path, 'a') as f:
            f.write(f'[shim] registration failed, exiting\n')
            f.flush()
        return

    # Background thread: daemon → extension (commands via stdout)
    t = threading.Thread(target=daemon_to_extension, daemon=True)
    t.start()

    # Main thread: extension → daemon (results/reports via stdin)
    # Exit on stdin EOF — browser will launch a new shim on reconnect
    import select
    with open(log_path, 'a') as f:
        f.write(f'[shim] entering main loop, waiting for stdin data\n')
        f.flush()
    while True:
        try:
            ready, _, _ = select.select([sys.stdin.buffer], [], [], 5.0)
            if ready:
                msg = read_native_message()
                if msg is None:
                    # stdin EOF — extension disconnected, exit cleanly
                    with open(log_path, 'a') as f:
                        f.write(f'[shim] stdin EOF, exiting\n')
                        f.flush()
                    break
                post_result(msg)
        except Exception as e:
            with open(log_path, 'a') as f:
                f.write(f'[shim] main loop error: {e}\n')
                f.flush()
            import time
            time.sleep(2)


if __name__ == '__main__':
    import os
    log_path = os.path.expanduser('~/.browser-bridge-shim.log')
    with open(log_path, 'a') as f:
        f.write(f'[shim] started, pid={os.getpid()}\n')
        f.flush()
        try:
            main()
        except Exception as e:
            f.write(f'[shim] fatal: {e}\n')
            f.flush()
            import traceback
            traceback.print_exc(file=f)
        finally:
            unregister_session()
            f.write(f'[shim] exited\n')
            f.flush()
