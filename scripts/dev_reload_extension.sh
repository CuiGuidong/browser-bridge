#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE_URL="${BRIDGE_URL:-http://127.0.0.1:17777}"
HOST_SSH="${BB_HOST_SSH:-}"
HOST_EXTENSION_DIR="${BB_HOST_EXTENSION_DIR:-}"

if [[ -f "$ROOT_DIR/.env.local" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env.local"
  BRIDGE_URL="${BRIDGE_URL:-http://127.0.0.1:17777}"
  HOST_SSH="${BB_HOST_SSH:-}"
  HOST_EXTENSION_DIR="${BB_HOST_EXTENSION_DIR:-}"
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
  echo "skip sync: set BB_HOST_EXTENSION_DIR to enable extension file sync" >&2
fi

curl --noproxy '*' -sS \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{"reloadPages":true}' \
  "$BRIDGE_URL/dev/reload-extension"
echo
