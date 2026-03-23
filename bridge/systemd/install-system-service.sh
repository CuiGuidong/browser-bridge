#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="browser-bridge.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_FILE="$SCRIPT_DIR/$SERVICE_NAME"
TARGET_FILE="/etc/systemd/system/$SERVICE_NAME"

if [[ ! -f "$UNIT_FILE" ]]; then
  echo "Missing unit file: $UNIT_FILE" >&2
  exit 1
fi

sudo install -m 0644 "$UNIT_FILE" "$TARGET_FILE"
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager

echo
echo "Installed and started: $SERVICE_NAME"
echo "Logs: sudo journalctl -u $SERVICE_NAME -n 200 --no-pager"
