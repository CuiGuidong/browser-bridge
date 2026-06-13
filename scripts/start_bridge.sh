#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE_DIR="$ROOT_DIR/bridge"
VENV_PYTHON="$BRIDGE_DIR/.venv/bin/python3"
ENV_FILE="$ROOT_DIR/.env.local"
HOST_OVERRIDE=""
PORT_OVERRIDE=""
WRITE_ENV=0

usage() {
  cat <<'EOF'
Usage: ./scripts/start_bridge.sh [options]

Options:
  --host <127.0.0.1|0.0.0.0>
  --port <port>
  --write-env       Persist --host/--port to .env.local
  --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST_OVERRIDE="${2:-}"
      shift 2
      ;;
    --port)
      PORT_OVERRIDE="${2:-}"
      shift 2
      ;;
    --write-env)
      WRITE_ENV=1
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

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing venv Python: $VENV_PYTHON" >&2
  echo "Run ./scripts/setup_macos.sh or ./scripts/setup_wsl.sh first." >&2
  exit 1
fi

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

load_env_file

if [[ -n "$HOST_OVERRIDE" ]]; then
  export BRIDGE_HOST="$HOST_OVERRIDE"
fi
if [[ -n "$PORT_OVERRIDE" ]]; then
  export BRIDGE_PORT="$PORT_OVERRIDE"
fi

export BRIDGE_HOST="${BRIDGE_HOST:-127.0.0.1}"
export BRIDGE_PORT="${BRIDGE_PORT:-17777}"

if [[ "$WRITE_ENV" -eq 1 ]]; then
  connect_host="$BRIDGE_HOST"
  [[ "$connect_host" == "0.0.0.0" ]] && connect_host="127.0.0.1"
  upsert_env "BRIDGE_HOST" "$BRIDGE_HOST"
  upsert_env "BRIDGE_PORT" "$BRIDGE_PORT"
  upsert_env "BRIDGE_URL" "http://$connect_host:$BRIDGE_PORT"
fi

cd "$BRIDGE_DIR"
exec "$VENV_PYTHON" -m app.server
