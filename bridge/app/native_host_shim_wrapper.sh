#!/usr/bin/env bash
# Wrapper script for native messaging host.
# Runs the shim with the project-local virtualenv Python.
VENV_DIR="$(cd "$(dirname "$0")/../.venv" && pwd)"
SHIM="$(cd "$(dirname "$0")" && pwd)/native_host_shim.py"
PYTHON="$VENV_DIR/bin/python3"

if [[ ! -x "$PYTHON" ]]; then
  echo "Browser Bridge native host error: missing venv Python at $PYTHON. Run the setup script first." >&2
  exit 1
fi

exec "$PYTHON" "$SHIM" "$@"
