#!/bin/bash
# ==============================================================
# Drawing Generator - Codespace Preview
# Runs the GUI app in a virtual display accessible via browser
# ==============================================================

set -e

# --- Install dependencies if missing ---
install_if_missing() {
    if ! dpkg -s "$1" &>/dev/null; then
        echo "Installing $1..."
        sudo apt-get install -y -qq "$1" 2>/dev/null
    fi
}

pip install -q customtkinter Pillow openpyxl pandas 2>/dev/null

# Fix broken apt repos (common in codespaces)
sudo rm -f /etc/apt/sources.list.d/yarn.list 2>/dev/null
sudo apt-get update -qq 2>/dev/null

install_if_missing xvfb
install_if_missing x11vnc
install_if_missing novnc
install_if_missing websockify
install_if_missing openbox

# --- Kill any previous preview session ---
pkill -9 -f "Xvfb :99" 2>/dev/null || true
pkill -9 -f "x11vnc" 2>/dev/null || true
pkill -9 -f "websockify.*6080" 2>/dev/null || true
pkill -9 -f "openbox" 2>/dev/null || true
sleep 1
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

# --- Start virtual display ---
Xvfb :99 -screen 0 1280x800x24 &
XVFB_PID=$!
export DISPLAY=:99
sleep 1

# --- Start window manager (required for proper rendering) ---
openbox &
WM_PID=$!
sleep 1

# --- Start VNC server ---
x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -forever &
VNC_PID=$!
sleep 1

# --- Start noVNC web proxy on port 6080 ---
websockify --web /usr/share/novnc/ 6080 localhost:5900 &
NOVNC_PID=$!

# --- Build the preview URL ---
PREVIEW_URL="https://${CODESPACE_NAME}-6080.app.github.dev/vnc.html?autoconnect=true&resize=scale"

echo ""
echo "======================================================"
echo "  Preview running!"
echo ""
echo "  URL: $PREVIEW_URL"
echo "======================================================"
echo ""

# --- Auto-open in VS Code Simple Browser ---
if command -v code &>/dev/null; then
    sleep 2
    code --goto "$PREVIEW_URL" 2>/dev/null || \
    code -r --command "simpleBrowser.show" "$PREVIEW_URL" 2>/dev/null || true
fi

# --- Launch the app ---
python3 gui.py

# --- Cleanup on exit ---
kill $XVFB_PID $VNC_PID $NOVNC_PID $WM_PID 2>/dev/null
