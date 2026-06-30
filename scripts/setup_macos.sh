#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="com.cuiguidong.browserbridge"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE_DIR="$ROOT_DIR/bridge"
VENV_DIR="$BRIDGE_DIR/.venv"
ENV_FILE="$ROOT_DIR/.env.local"
EXTENSION_ID=""
BROWSER="auto"
BRIDGE_HOST_VALUE=""
BRIDGE_PORT_VALUE=""
NON_INTERACTIVE=0
PYTHON_BIN="${PYTHON:-}"

usage() {
  cat <<'EOF'
Usage: ./scripts/setup_macos.sh [options]

Options:
  --extension-id <id>       Browser extension id from chrome://extensions or edge://extensions
  --browser <chrome|edge|both>
  --host <127.0.0.1|0.0.0.0>
  --port <port>
  --non-interactive         Do not prompt; requires enough options to complete native host install
  --help

Environment:
  PYTHON=/path/to/python3.12  Override Python interpreter used to create bridge/.venv
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --extension-id)
      EXTENSION_ID="${2:-}"
      shift 2
      ;;
    --browser)
      BROWSER="${2:-}"
      shift 2
      ;;
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

if [[ "$(uname)" != "Darwin" ]]; then
  echo "This setup script is for macOS. Use scripts/setup_wsl.sh on WSL." >&2
  exit 1
fi

has_chrome=0
has_edge=0
[[ -d "/Applications/Google Chrome.app" ]] && has_chrome=1
[[ -d "/Applications/Microsoft Edge.app" ]] && has_edge=1

choose_browser() {
  if [[ "$BROWSER" != "auto" ]]; then
    return
  fi
  if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
    if [[ "$has_chrome" -eq 1 && "$has_edge" -eq 1 ]]; then
      BROWSER="both"
    elif [[ "$has_chrome" -eq 1 ]]; then
      BROWSER="chrome"
    elif [[ "$has_edge" -eq 1 ]]; then
      BROWSER="edge"
    else
      echo "No Chrome or Edge installation found under /Applications." >&2
      exit 1
    fi
    return
  fi

  echo "Detected browsers:"
  [[ "$has_chrome" -eq 1 ]] && echo "  1) Google Chrome"
  [[ "$has_edge" -eq 1 ]] && echo "  2) Microsoft Edge"
  echo "  3) Both"
  read -r -p "Choose browser [default: both if available]: " choice
  case "$choice" in
    1) BROWSER="chrome" ;;
    2) BROWSER="edge" ;;
    3|"") BROWSER="both" ;;
    *) echo "Invalid browser choice: $choice" >&2; exit 1 ;;
  esac
}

validate_browser() {
  case "$BROWSER" in
    chrome)
      [[ "$has_chrome" -eq 1 ]] || { echo "Google Chrome not found." >&2; exit 1; }
      ;;
    edge)
      [[ "$has_edge" -eq 1 ]] || { echo "Microsoft Edge not found." >&2; exit 1; }
      ;;
    both)
      if [[ "$has_chrome" -ne 1 && "$has_edge" -ne 1 ]]; then
        echo "No Chrome or Edge installation found under /Applications." >&2
        exit 1
      fi
      ;;
    *)
      echo "Invalid --browser value: $BROWSER" >&2
      exit 1
      ;;
  esac
}

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

  echo "Python 3.10+ is required. Install Python 3.10+ or rerun with PYTHON=/path/to/python3.12." >&2
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
      echo "  1) 127.0.0.1 - local machine only"
      echo "  2) 0.0.0.0 - all local network interfaces"
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

install_manifest() {
  local dir="$1"
  local extension_id="$2"
  mkdir -p "$dir"
  local manifest_path="$dir/$HOST_NAME.json"
  cat > "$manifest_path" <<EOF
{
  "name": "$HOST_NAME",
  "description": "Browser Bridge native messaging host",
  "type": "stdio",
  "path": "$ROOT_DIR/bridge/app/native_host_shim_wrapper.sh",
  "allowed_origins": [
    "chrome-extension://$extension_id/"
  ]
}
EOF
  echo "Installed native host manifest: $manifest_path"
}

install_native_hosts() {
  local extension_id="$EXTENSION_ID"
  if [[ -z "$extension_id" && "$NON_INTERACTIVE" -eq 0 ]]; then
    echo
    echo "Load this extension directory in Chrome/Edge first:"
    echo "  $ROOT_DIR/extension"
    echo "Then copy the extension id from the browser extensions page."
    read -r -p "Extension id (leave empty to install later): " extension_id
  fi

  if [[ -z "$extension_id" ]]; then
    echo
    echo "Native host manifest was not installed because extension id is missing."
    echo "After loading the extension, rerun:"
    echo "  ./scripts/setup_macos.sh --browser $BROWSER --host $BRIDGE_HOST_VALUE --port $BRIDGE_PORT_VALUE --extension-id <extension-id>"
    return
  fi

  if [[ "$BROWSER" == "chrome" || "$BROWSER" == "both" ]]; then
    if [[ "$has_chrome" -eq 1 ]]; then
      install_manifest "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts" "$extension_id"
    fi
  fi
  if [[ "$BROWSER" == "edge" || "$BROWSER" == "both" ]]; then
    if [[ "$has_edge" -eq 1 ]]; then
      install_manifest "$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts" "$extension_id"
    fi
  fi
}

choose_browser
validate_browser
require_python
prompt_host_port
setup_venv
generate_manifest
chmod +x "$ROOT_DIR/bridge/app/native_host_shim.py" "$ROOT_DIR/bridge/app/native_host_shim_wrapper.sh"
write_env
install_native_hosts

echo
echo "Setup complete."
echo "Start Bridge:"
echo "  ./scripts/start_bridge.sh"
echo "Run diagnostics:"
echo "  ./scripts/doctor.sh"
