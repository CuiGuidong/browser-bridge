#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_SSH="${BB_HOST_SSH:-}"
HOST_EXTENSION_DIR="${BB_HOST_EXTENSION_DIR:-}"

is_wsl() {
  grep -qiE "microsoft|wsl" /proc/sys/kernel/osrelease 2>/dev/null
}

if [[ -n "$HOST_EXTENSION_DIR" && -z "$HOST_SSH" && "$HOST_EXTENSION_DIR" == /Users/* ]] && is_wsl; then
  echo "Refuse to sync to macOS path from WSL without BB_HOST_SSH: $HOST_EXTENSION_DIR" >&2
  echo "Pass a real WSL/Windows-mounted path, run this script on macOS, or set BB_HOST_SSH for remote sync." >&2
  exit 2
fi

if [[ -f "$ROOT_DIR/extension/manifest.prod.json" ]]; then
  echo "Generating manifest.json from manifest.prod.json (Production Mode)..."
  cp "$ROOT_DIR/extension/manifest.prod.json" "$ROOT_DIR/extension/manifest.json"
fi

if [[ -n "$HOST_EXTENSION_DIR" ]]; then
  echo "Syncing production extension files to host..."
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
  echo "Production extension files successfully synced to $HOST_EXTENSION_DIR"
else
  echo "Skip host sync: set BB_HOST_EXTENSION_DIR in the command environment to enable extension sync."
fi
