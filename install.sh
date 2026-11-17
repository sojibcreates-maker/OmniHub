#!/usr/bin/env bash
set -e

echo "=========================================="
echo " OmniHub Cross-Platform Installer"
echo " Crafted by Md Sojib Hossain (SojibLabs)"
echo "=========================================="

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_TYPE="$(uname -s)"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$BIN_DIR"

echo "-> Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r "$APP_DIR/requirements.txt"

echo "-> Installing binary launcher..."
ln -sf "$APP_DIR/main.py" "$BIN_DIR/omnihub"
chmod +x "$BIN_DIR/omnihub"

if [ "$OS_TYPE" = "Linux" ]; then
    echo "-> Configuring Linux desktop integration..."
    ICON_DIR="$HOME/.local/share/icons"
    APP_DESKTOP_DIR="$HOME/.local/share/applications"
    mkdir -p "$ICON_DIR" "$APP_DESKTOP_DIR"

    if [ -d "$APP_DIR/assets" ]; then
        cp -f "$APP_DIR/assets/omnihub.png" "$ICON_DIR/omnihub.png" 2>/dev/null || true
        cp -f "$APP_DIR/assets/omnihub.svg" "$ICON_DIR/omnihub.svg" 2>/dev/null || true
    fi

    cat <<EOF > "$APP_DESKTOP_DIR/omnihub.desktop"
[Desktop Entry]
Type=Application
Name=OmniHub
GenericName=AI Gateway & System Studio
Comment=Precision AI Gateway, 1-Click OmniRoute Installer & System Studio
Exec=omnihub %U
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

elif [ "$OS_TYPE" = "Darwin" ]; then
    echo "-> macOS environment detected."
    echo "-> Created CLI alias at $BIN_DIR/omnihub"
fi

echo "=========================================="
echo " OmniHub installed successfully!"
echo " Run 'omnihub' in your terminal or launch via python3 main.py."
echo "=========================================="
