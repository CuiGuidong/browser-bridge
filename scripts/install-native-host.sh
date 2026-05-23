#!/usr/bin/env bash
set -euo pipefail

# Install Browser Bridge native messaging host manifest.
# Usage: ./scripts/install-native-host.sh <extension-id>
#
# Find your extension ID at edge://extensions or chrome://extensions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SHIM_PATH="$PROJECT_ROOT/bridge/app/native_host_shim.py"
HOST_NAME="com.cuiguidong.browserbridge"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <extension-id>"
  echo ""
  echo "Find your extension ID at edge://extensions or chrome://extensions"
  echo "(Click 'Details' on Browser Bridge Extension to see the ID)"
  exit 1
fi

EXTENSION_ID="$1"

# Determine install paths based on OS and browser
install_manifest() {
  local dir="$1"
  local label="$2"
  mkdir -p "$dir"
  local manifest_path="$dir/$HOST_NAME.json"
  cat > "$manifest_path" <<EOF
{
  "name": "$HOST_NAME",
  "description": "Browser Bridge native messaging host",
  "type": "stdio",
  "path": "$SHIM_PATH",
  "allowed_origins": [
    "chrome-extension://$EXTENSION_ID/"
  ]
}
EOF
  echo "  Installed: $manifest_path"
}

echo "Installing native host manifest..."
echo "  Shim path: $SHIM_PATH"
echo "  Extension ID: $EXTENSION_ID"
echo ""

# macOS
if [[ "$(uname)" == "Darwin" ]]; then
  install_manifest "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts" "Chrome (macOS)"
  install_manifest "$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts" "Edge (macOS)"
# Linux
elif [[ "$(uname)" == "Linux" ]]; then
  install_manifest "$HOME/.config/google-chrome/NativeMessagingHosts" "Chrome (Linux)"
  install_manifest "$HOME/.config/microsoft-edge/NativeMessagingHosts" "Edge (Linux)"
else
  echo "Unsupported OS: $(uname)"
  exit 1
fi

echo ""
echo "Done. Reload the Browser Bridge extension in your browser to connect."
