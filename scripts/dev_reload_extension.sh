#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_DEV_BRIDGE_URL="http://127.0.0.1:17777"
ENV_BRIDGE_URL_SET=0
ENV_HOST_SSH_SET=0
ENV_HOST_EXTENSION_DIR_SET=0
[[ ${BRIDGE_URL+x} ]] && ENV_BRIDGE_URL_SET=1 && ENV_BRIDGE_URL="$BRIDGE_URL"
[[ ${BB_HOST_SSH+x} ]] && ENV_HOST_SSH_SET=1 && ENV_HOST_SSH="$BB_HOST_SSH"
[[ ${BB_HOST_EXTENSION_DIR+x} ]] && ENV_HOST_EXTENSION_DIR_SET=1 && ENV_HOST_EXTENSION_DIR="$BB_HOST_EXTENSION_DIR"
BRIDGE_URL="$DEFAULT_DEV_BRIDGE_URL"
HOST_SSH="${BB_HOST_SSH:-}"
HOST_EXTENSION_DIR=""

if [[ -f "$ROOT_DIR/.env.local" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env.local"
  if [[ "$ENV_BRIDGE_URL_SET" -eq 1 ]]; then
    BRIDGE_URL="$ENV_BRIDGE_URL"
  else
    BRIDGE_URL="$DEFAULT_DEV_BRIDGE_URL"
  fi
  if [[ "$ENV_HOST_SSH_SET" -eq 1 ]]; then
    HOST_SSH="$ENV_HOST_SSH"
  else
    HOST_SSH=""
  fi
  if [[ "$ENV_HOST_EXTENSION_DIR_SET" -eq 1 ]]; then
    HOST_EXTENSION_DIR="$ENV_HOST_EXTENSION_DIR"
  else
    HOST_EXTENSION_DIR=""
  fi
fi

if [[ -f "$ROOT_DIR/extension/manifest.dev.json" ]]; then
  echo "Generating manifest.json from manifest.dev.json..."
  cp "$ROOT_DIR/extension/manifest.dev.json" "$ROOT_DIR/extension/manifest.json"
fi

if [[ -n "$HOST_EXTENSION_DIR" ]]; then
  if [[ -n "$HOST_SSH" ]]; then
    ssh "$HOST_SSH" "mkdir -p '$HOST_EXTENSION_DIR'"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete --exclude '.DS_Store' "$ROOT_DIR/extension/" "$HOST_SSH:$HOST_EXTENSION_DIR/"
    else
      echo "rsync is required for SSH sync" >&2
      exit 1
    fi
  else
    mkdir -p "$HOST_EXTENSION_DIR"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete --exclude '.DS_Store' "$ROOT_DIR/extension/" "$HOST_EXTENSION_DIR/"
    else
      cp -a "$ROOT_DIR/extension/." "$HOST_EXTENSION_DIR/"
    fi
  fi
else
  echo "skip sync: set BB_HOST_EXTENSION_DIR explicitly to enable extension file sync" >&2
fi

echo "dev reload bridge: $BRIDGE_URL" >&2
curl --noproxy '*' -sS \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{"reloadPages":true}' \
  "$BRIDGE_URL/dev/reload-extension"
echo
