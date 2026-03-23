#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Avoid proxy side effects for local bridge/CDP traffic.
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY

cleanup_port_owner() {
  local port="$1"

  python3 - "$port" <<'PY'
import os
import signal
import sys
import time
from pathlib import Path

port = int(sys.argv[1])
listen_suffix = f":{port:04X}"


def listening_inodes():
    inodes = set()
    for proc_path in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(proc_path, "r", encoding="utf-8") as fh:
                next(fh, None)
                for line in fh:
                    parts = line.split()
                    if len(parts) < 10:
                        continue
                    local_address = parts[1]
                    state = parts[3]
                    inode = parts[9]
                    if state == "0A" and local_address.endswith(listen_suffix):
                        inodes.add(inode)
        except FileNotFoundError:
            continue
    return inodes


def pids_for_inodes(inodes):
    pids = set()
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        fd_dir = proc / "fd"
        try:
            for fd in fd_dir.iterdir():
                try:
                    link = os.readlink(fd)
                except OSError:
                    continue
                if link.startswith("socket:[") and link[8:-1] in inodes:
                    pids.add(int(proc.name))
                    break
        except (FileNotFoundError, PermissionError):
            continue
    return pids


def cmdline_for_pid(pid):
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        return " ".join(part.decode(errors="ignore") for part in raw if part)
    except Exception:
        return ""


def matches_bridge_process(pid):
    cmdline = cmdline_for_pid(pid)
    if not cmdline:
        return False
    return any(
        token in cmdline
        for token in (
            "bridge.py",
            "run_bridge.sh",
            "browser-bridge",
            "uvicorn",
        )
    )


inodes = listening_inodes()
if not inodes:
    sys.exit(0)

pids = sorted(pid for pid in pids_for_inodes(inodes) if matches_bridge_process(pid))
if not pids:
    sys.exit(0)

print(f"[browser-bridge] freeing port {port}: pid(s) {', '.join(map(str, pids))}", file=sys.stderr)
for pid in pids:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass

deadline = time.time() + 5
while time.time() < deadline:
    live = [pid for pid in pids if Path(f"/proc/{pid}").exists()]
    if not live:
        break
    time.sleep(0.2)

for pid in pids:
    if Path(f"/proc/{pid}").exists():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

deadline = time.time() + 3
while time.time() < deadline:
    live = [pid for pid in pids if Path(f"/proc/{pid}").exists()]
    if not live:
        break
    time.sleep(0.2)

live = [pid for pid in pids if Path(f"/proc/{pid}").exists()]
if live:
    print(
        f"[browser-bridge] failed to free port {port}: pid(s) still alive after SIGKILL: {', '.join(map(str, live))}",
        file=sys.stderr,
    )
    sys.exit(1)
PY
}

cleanup_port_owner "${BRIDGE_PORT:-17777}"

exec "$SCRIPT_DIR/.venv/bin/python" bridge.py
