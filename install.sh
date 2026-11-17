#!/usr/bin/env bash
set -e

echo "=========================================="
echo " OmniHub Installer - SojibLabs"
echo "=========================================="

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons"
APP_DESKTOP_DIR="$HOME/.local/share/applications"

mkdir -p "$BIN_DIR" "$ICON_DIR" "$APP_DESKTOP_DIR"

echo "-> Installing Python dependencies..."
python3 -m pip install -r "$APP_DIR/requirements.txt"

echo "-> Installing binary launcher..."
ln -sf "$APP_DIR/main.py" "$BIN_DIR/omnihub"
chmod +x "$BIN_DIR/omnihub"

echo "-> Installing icons..."
if [ -d "$APP_DIR/assets" ]; then
    cp -f "$APP_DIR/assets/omnihub.png" "$ICON_DIR/omnihub.png" 2>/dev/null || true
    cp -f "$APP_DIR/assets/omnihub.svg" "$ICON_DIR/omnihub.svg" 2>/dev/null || true
fi

echo "-> Installing desktop launcher..."
cat <<EOF > "$APP_DESKTOP_DIR/omnihub.desktop"
[Desktop Entry]
Type=Application
Name=OmniHub
GenericName=AI Gateway & System Studio
Comment=Precision AI Gateway, 1-Click OmniRoute Installer & System Studio
Exec=$BIN_DIR/omnihub %U
Icon=omnihub
Terminal=false
Categories=Development;Utility;System;Network;
Keywords=ai;gateway;omniroute;system;monitor;chat;llm;
StartupWMClass=omnihub
StartupNotify=true
SingleMainWindow=true
EOF

chmod +x "$APP_DESKTOP_DIR/omnihub.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DESKTOP_DIR" 2>/dev/null || true
fi

echo "=========================================="
echo " OmniHub installed successfully!"
echo " Run 'omnihub' in terminal or launch from app menu."
echo "=========================================="
