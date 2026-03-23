#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="browser-bridge.service"
CMD="${1:-status}"

case "$CMD" in
  start)
    sudo systemctl start "$SERVICE_NAME"
    ;;
  stop)
    sudo systemctl stop "$SERVICE_NAME"
    ;;
  restart)
    sudo systemctl restart "$SERVICE_NAME"
    ;;
  enable)
    sudo systemctl enable "$SERVICE_NAME"
    ;;
  disable)
    sudo systemctl disable "$SERVICE_NAME"
    ;;
  status)
    sudo systemctl status "$SERVICE_NAME" --no-pager
    ;;
  logs)
    sudo journalctl -u "$SERVICE_NAME" -n "${2:-100}" --no-pager
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|enable|disable|status|logs [N]}" >&2
    exit 2
    ;;
esac
