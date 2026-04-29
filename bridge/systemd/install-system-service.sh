#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="browser-bridge.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_FILE="$SCRIPT_DIR/$SERVICE_NAME"
TARGET_FILE="/etc/systemd/system/$SERVICE_NAME"
BRIDGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_BRIDGE="$BRIDGE_DIR/run_bridge.sh"
TMP_UNIT="$(mktemp)"

if [[ ! -f "$UNIT_FILE" ]]; then
  echo "Missing unit file: $UNIT_FILE" >&2
  exit 1
fi

cleanup() {
  rm -f "$TMP_UNIT"
}
trap cleanup EXIT

sed \
  -e "s|__BRIDGE_WORKDIR__|$BRIDGE_DIR|g" \
  -e "s|__BRIDGE_EXECSTART__|$RUN_BRIDGE|g" \
  "$UNIT_FILE" >"$TMP_UNIT"

sudo install -m 0644 "$TMP_UNIT" "$TARGET_FILE"
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager

echo
echo "Installed and started: $SERVICE_NAME"
echo "Logs: sudo journalctl -u $SERVICE_NAME -n 200 --no-pager"
