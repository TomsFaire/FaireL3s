#!/usr/bin/env bash
# Build FaireL3s.app locally. Requires: venv with pip install -r requirements.txt pyinstaller
set -e
cd "$(dirname "$0")"

echo "Building FaireL3s.app..."
pyinstaller -y l3rd_app_mac.spec

echo "Done. App is at dist/FaireL3s.app"
echo "Run: open dist/FaireL3s.app"
