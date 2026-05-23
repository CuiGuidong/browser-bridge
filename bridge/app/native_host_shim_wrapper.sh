#!/usr/bin/env bash
# Wrapper script for native messaging host.
# Activates the bridge venv and runs the shim.
VENV_DIR="$(cd "$(dirname "$0")/../.venv" && pwd)"
SHIM="$(cd "$(dirname "$0")" && pwd)/native_host_shim.py"
exec "$VENV_DIR/bin/python3" "$SHIM" "$@"
