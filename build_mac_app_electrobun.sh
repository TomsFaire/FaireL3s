#!/usr/bin/env bash
# Build FaireL3s as an Electrobun-wrapped macOS app.
# Usage: ./build_mac_app_electrobun.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Step 1: Install Python dependencies"
pip install -r requirements.txt pyinstaller

echo "==> Step 2: Build Python backend (PyInstaller one-folder)"
pyinstaller -y l3rd_backend.spec

echo "==> Step 3: Copy backend into Electrobun resources"
rm -rf electrobun/resources/python-backend
cp -R dist/FaireL3s/ electrobun/resources/python-backend/

echo "==> Step 4: Build Electrobun app"
cd electrobun
bun install
bun run build
cd ..

echo "==> Step 5: Zip for distribution"
# Electrobun outputs to electrobun/dist/ — locate the .app
APP_PATH="$(find electrobun/dist -name '*.app' -maxdepth 2 | head -1)"
if [ -z "$APP_PATH" ]; then
    echo "ERROR: Could not find .app in electrobun/dist/"
    exit 1
fi
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" FaireL3s-macOS.zip

echo "==> Done: FaireL3s-macOS.zip"
