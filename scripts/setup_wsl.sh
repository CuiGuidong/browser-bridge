#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE_DIR="$ROOT_DIR/bridge"
VENV_DIR="$BRIDGE_DIR/.venv"
ENV_FILE="$ROOT_DIR/.env.local"
BRIDGE_HOST_VALUE=""
BRIDGE_PORT_VALUE=""
NON_INTERACTIVE=0
PYTHON_BIN="${PYTHON:-}"

usage() {
  cat <<'EOF'
Usage: ./scripts/setup_wsl.sh [options]

Options:
  --host <127.0.0.1|0.0.0.0>
  --port <port>
  --non-interactive
  --help

Environment:
  PYTHON=/path/to/python3.12  Override Python interpreter used to create bridge/.venv
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      BRIDGE_HOST_VALUE="${2:-}"
      shift 2
      ;;
    --port)
      BRIDGE_PORT_VALUE="${2:-}"
      shift 2
      ;;
    --non-interactive)
      NON_INTERACTIVE=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! grep -qiE "microsoft|wsl" /proc/sys/kernel/osrelease 2>/dev/null; then
  echo "This setup script is intended for WSL." >&2
  exit 1
fi

python_version_ok() {
  "$1" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

require_python() {
  local candidates=()
  if [[ -n "$PYTHON_BIN" ]]; then
    candidates+=("$PYTHON_BIN")
  fi
  candidates+=(python3.13 python3.12 python3.11 python3.10 python3)

  local candidate
  for candidate in "${candidates[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1 && python_version_ok "$candidate"; then
      PYTHON_BIN="$(command -v "$candidate")"
      return
    fi
  done

  echo "Python 3.10+ is required inside WSL. Install Python 3.10+ or rerun with PYTHON=/path/to/python3.12." >&2
  if command -v python3 >/dev/null 2>&1; then
    echo "Current python3: $(python3 --version 2>&1)" >&2
  fi
  exit 1
}

prompt_host_port() {
  if [[ -z "$BRIDGE_HOST_VALUE" ]]; then
    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
      BRIDGE_HOST_VALUE="127.0.0.1"
    else
      echo "Bridge host:"
      echo "  1) 127.0.0.1 - Windows localhost forwarding usually reaches WSL services"
      echo "  2) 0.0.0.0 - listen on all WSL interfaces"
      read -r -p "Choose host [1]: " host_choice
      case "$host_choice" in
        ""|1) BRIDGE_HOST_VALUE="127.0.0.1" ;;
        2) BRIDGE_HOST_VALUE="0.0.0.0" ;;
        *) echo "Invalid host choice: $host_choice" >&2; exit 1 ;;
      esac
    fi
  fi
  if [[ "$BRIDGE_HOST_VALUE" != "127.0.0.1" && "$BRIDGE_HOST_VALUE" != "0.0.0.0" ]]; then
    echo "Unsupported host: $BRIDGE_HOST_VALUE" >&2
    exit 1
  fi

  if [[ -z "$BRIDGE_PORT_VALUE" ]]; then
    if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
      BRIDGE_PORT_VALUE="17777"
    else
      read -r -p "Bridge port [17777]: " port_input
      BRIDGE_PORT_VALUE="${port_input:-17777}"
    fi
  fi
  if ! [[ "$BRIDGE_PORT_VALUE" =~ ^[0-9]+$ ]]; then
    echo "Invalid port: $BRIDGE_PORT_VALUE" >&2
    exit 1
  fi
}

upsert_env() {
  local key="$1"
  local value="$2"
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$ENV_FILE" ]]; then
    if ! awk -v k="$key" -v v="$value" '
      BEGIN { done=0 }
      $0 ~ "^[[:space:]]*" k "=" { print k "=" v; done=1; next }
      { print }
      END { if (!done) print k "=" v }
    ' "$ENV_FILE" >"$tmp"; then
      rm -f "$tmp"
      return 1
    fi
  else
    if ! printf '%s=%s\n' "$key" "$value" >"$tmp"; then
      rm -f "$tmp"
      return 1
    fi
  fi
  mv "$tmp" "$ENV_FILE"
}

write_env() {
  local connect_host="$BRIDGE_HOST_VALUE"
  [[ "$connect_host" == "0.0.0.0" ]] && connect_host="127.0.0.1"
  upsert_env "BRIDGE_HOST" "$BRIDGE_HOST_VALUE"
  upsert_env "BRIDGE_PORT" "$BRIDGE_PORT_VALUE"
  upsert_env "BRIDGE_URL" "http://$connect_host:$BRIDGE_PORT_VALUE"
}

setup_venv() {
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python3" -m pip install --no-cache-dir -r "$ROOT_DIR/requirements.txt"
}

generate_manifest() {
  if [[ -f "$ROOT_DIR/extension/manifest.prod.json" ]]; then
    cp "$ROOT_DIR/extension/manifest.prod.json" "$ROOT_DIR/extension/manifest.json"
  else
    cp "$ROOT_DIR/extension/manifest.dev.json" "$ROOT_DIR/extension/manifest.json"
  fi
}

windows_path() {
  local path="$1"
  local converted=""
  if command -v wslpath >/dev/null 2>&1; then
    converted="$(wslpath -w "$path" 2>/dev/null || true)"
  fi
  if [[ -n "$converted" ]]; then
    echo "$converted"
  elif [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
    converted="\\\\wsl.localhost\\$WSL_DISTRO_NAME\\${path#/}"
    echo "${converted//\//\\}"
  else
    echo "<windows-path-for-$path>"
  fi
}

require_python
prompt_host_port
setup_venv
generate_manifest
chmod +x "$ROOT_DIR/bridge/app/native_host_shim.py" "$ROOT_DIR/bridge/app/native_host_shim_wrapper.sh"
write_env

EXTENSION_WIN_PATH="$(windows_path "$ROOT_DIR/extension")"
INSTALLER_WIN_PATH="$(windows_path "$ROOT_DIR/scripts/windows/install-native-host.ps1")"
CONNECT_HOST="$BRIDGE_HOST_VALUE"
[[ "$CONNECT_HOST" == "0.0.0.0" ]] && CONNECT_HOST="127.0.0.1"
BRIDGE_URL_VALUE="http://$CONNECT_HOST:$BRIDGE_PORT_VALUE"

echo
echo "WSL setup complete."
echo "Load this extension directory from Windows Chrome/Edge:"
echo "  $EXTENSION_WIN_PATH"
echo
echo "After copying the extension id from the browser that loaded the extension, run one command in Windows PowerShell:"
echo "  powershell -ExecutionPolicy Bypass -File \"$INSTALLER_WIN_PATH\" -ExtensionId <extension-id> -Browser edge -BridgeUrl \"$BRIDGE_URL_VALUE\""
echo "  powershell -ExecutionPolicy Bypass -File \"$INSTALLER_WIN_PATH\" -ExtensionId <extension-id> -Browser chrome -BridgeUrl \"$BRIDGE_URL_VALUE\""
echo "Use -Browser both only when both browsers load the same extension id."
echo
echo "Start Bridge inside WSL:"
echo "  ./scripts/start_bridge.sh"
echo "Run diagnostics inside WSL:"
echo "  ./scripts/doctor.sh"
