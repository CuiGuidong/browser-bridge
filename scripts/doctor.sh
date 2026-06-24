#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.local"
HOST_NAME="com.cuiguidong.browserbridge"
STATUS=0
ENV_BRIDGE_URL_SET=0
[[ ${BRIDGE_URL+x} ]] && ENV_BRIDGE_URL_SET=1 && EXPLICIT_BRIDGE_URL="$BRIDGE_URL"

info() {
  printf '[INFO] %s\n' "$*"
}

ok() {
  printf '[OK] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*"
}

fail() {
  printf '[FAIL] %s\n' "$*"
  STATUS=1
}

load_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    return
  fi
  while IFS= read -r line; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "$line" == \#* || "$line" != *=* ]] && continue
    local key="${line%%=*}"
    local value="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    case "$key" in
      BRIDGE_HOST|BRIDGE_PORT|BRIDGE_URL)
        export "$key=$value"
        ;;
    esac
  done <"$ENV_FILE"
}

http_get() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl --noproxy '*' -fsS "$url" 2>/dev/null
  else
    return 1
  fi
}

is_wsl() {
  grep -qiE "microsoft|wsl" /proc/sys/kernel/osrelease 2>/dev/null
}

check_file() {
  local path="$1"
  local label="$2"
  if [[ -e "$path" ]]; then
    ok "$label exists: $path"
  else
    fail "$label missing: $path"
  fi
}

check_macos_native_host() {
  local expected="$ROOT_DIR/bridge/app/native_host_shim_wrapper.sh"
  local paths=(
    "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/$HOST_NAME.json"
    "$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts/$HOST_NAME.json"
  )
  local found=0
  for path in "${paths[@]}"; do
    if [[ -f "$path" ]]; then
      found=1
      if grep -Fq "\"path\"" "$path" && grep -Fq "$expected" "$path"; then
        ok "Native Host manifest points to wrapper: $path"
      else
        fail "Native Host manifest path does not point to $expected: $path"
      fi
      if grep -Fq "chrome-extension://" "$path"; then
        ok "Native Host manifest has allowed_origins: $path"
      else
        fail "Native Host manifest missing allowed_origins: $path"
      fi
    fi
  done
  if [[ "$found" -eq 0 ]]; then
    warn "No macOS Native Host manifest found. Run ./scripts/setup_macos.sh after loading the extension."
  fi
}

check_wsl_native_host_hint() {
  local ps_path
  ps_path="$(wslpath -w "$ROOT_DIR/scripts/windows/install-native-host.ps1" 2>/dev/null || true)"
  ps_path="${ps_path:-<windows-path-to-install-native-host.ps1>}"

  info "WSL detected. Check Windows Native Host from PowerShell if native session is disconnected:"
  printf '  powershell -ExecutionPolicy Bypass -File "%s" -ExtensionId <extension-id> -Browser edge -BridgeUrl "%s"\n' \
    "$ps_path" \
    "$BRIDGE_URL"
  printf '  powershell -ExecutionPolicy Bypass -File "%s" -ExtensionId <extension-id> -Browser chrome -BridgeUrl "%s"\n' \
    "$ps_path" \
    "$BRIDGE_URL"
  info "Use the browser that actually loaded this extension. Use -Browser both only when both browsers load the same extension id."
}

load_env_file

BRIDGE_HOST="${BRIDGE_HOST:-127.0.0.1}"
BRIDGE_PORT="${BRIDGE_PORT:-17777}"
CONNECT_HOST="$BRIDGE_HOST"
[[ "$CONNECT_HOST" == "0.0.0.0" ]] && CONNECT_HOST="127.0.0.1"
if [[ "$ENV_BRIDGE_URL_SET" -eq 1 ]]; then
  BRIDGE_URL="$EXPLICIT_BRIDGE_URL"
elif is_wsl; then
  BRIDGE_URL="http://127.0.0.1:$BRIDGE_PORT"
else
  BRIDGE_URL="${BRIDGE_URL:-http://$CONNECT_HOST:$BRIDGE_PORT}"
fi

info "Browser Bridge doctor"
info "Project: $ROOT_DIR"
info "Bridge URL: $BRIDGE_URL"

check_file "$ROOT_DIR/bridge/.venv" "Python venv"
check_file "$ROOT_DIR/extension/manifest.json" "Extension manifest"
if [[ -f "$ENV_FILE" ]]; then
  ok ".env.local exists: $ENV_FILE"
else
  warn ".env.local missing. Defaults are BRIDGE_HOST=127.0.0.1 and BRIDGE_PORT=17777."
fi

if [[ ! -x "$ROOT_DIR/bridge/app/native_host_shim_wrapper.sh" ]]; then
  fail "Native Host wrapper is not executable: bridge/app/native_host_shim_wrapper.sh"
fi

health="$(http_get "$BRIDGE_URL/health")"
if [[ -n "${health:-}" ]]; then
  ok "Bridge health endpoint reachable"
  if printf '%s' "$health" | grep -Eq '"nativeSession"[[:space:]]*:[[:space:]]*"connected"'; then
    ok "Native session appears connected"
  else
    warn "Native session does not appear connected. Reload the extension or check Native Host manifest."
  fi
else
  fail "Bridge health endpoint is not reachable: $BRIDGE_URL/health"
  info "Start Bridge with: ./scripts/start_bridge.sh"
fi

state="$(http_get "$BRIDGE_URL/extension/state")"
if [[ -n "${state:-}" ]]; then
  ok "Extension state endpoint reachable"
else
  warn "Extension state endpoint not reachable. This is expected if Bridge is down."
fi

if [[ "$(uname)" == "Darwin" ]]; then
  check_macos_native_host
elif is_wsl; then
  check_wsl_native_host_hint
fi

if [[ "$STATUS" -eq 0 ]]; then
  ok "Doctor completed without blocking failures."
else
  fail "Doctor found blocking failures. Follow the messages above."
fi

exit "$STATUS"
