#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/feeling-traker.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Feeling Traker Widget
Exec=/bin/bash -lc '$BASE_DIR/scripts/start_all.sh'
X-GNOME-Autostart-enabled=true
Terminal=false
DESKTOP

echo "installed: $AUTOSTART_DIR/feeling-traker.desktop"
