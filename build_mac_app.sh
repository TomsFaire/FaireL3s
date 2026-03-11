#!/usr/bin/env bash
# Build FaireL3s.app locally (same steps as GitHub Actions).
# Run from repo root. Requires: venv with pip install -r requirements.txt pyinstaller
set -e
cd "$(dirname "$0")"
VERSION="${1:-0.0.6}"

echo "Building one-dir bundle..."
pyinstaller -y l3rd_app_mac.spec

echo "Creating .app bundle..."
rm -rf FaireL3s.app
mkdir -p FaireL3s.app/Contents/MacOS
cp -R dist/FaireL3s/* FaireL3s.app/Contents/MacOS/
chmod +x FaireL3s.app/Contents/MacOS/FaireL3s

cat > FaireL3s.app/Contents/Info.plist << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>FaireL3s</string>
  <key>CFBundleIdentifier</key>
  <string>com.faire.lowerthirds</string>
  <key>CFBundleName</key>
  <string>Faire Lower 3rds</string>
  <key>CFBundleDisplayName</key>
  <string>Faire Lower 3rds</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>${VERSION}</string>
  <key>CFBundleVersion</key>
  <string>${VERSION}</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

echo "Done. FaireL3s.app is ready. Run: open FaireL3s.app"
echo "Optional: ditto -c -k --sequesterRsrc --keepParent FaireL3s.app FaireL3s-macOS.zip"
