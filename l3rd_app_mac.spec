# PyInstaller spec for macOS .app (one-dir). Used by GitHub Actions to build FaireL3s.app.
# Local build: pyinstaller l3rd_app_mac.spec
# Output: dist/FaireL3s/ (folder to be wrapped in FaireL3s.app by CI)

from pathlib import Path

block_cipher = None

BASE = Path(".").resolve()

style_jsons = [
    "style.json", "style_dark.json", "style_dark_alt.json", "style_bright.json",
    "style_bright_insider.json", "style_bright_warm.json", "style_bright_info.json",
    "style_palette_olive.json", "style_palette_teal.json", "style_palette_terracotta.json",
    "style_palette_plum.json", "style_palette_copper.json", "style_palette_sage.json",
]
datas = [(str(BASE / name), ".") for name in style_jsons if (BASE / name).exists()]
if (BASE / "template_l3.companionconfig").exists():
    datas.append((str(BASE / "template_l3.companionconfig"), "."))

hiddenimports = [
    "companion_l3_page",
    "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "yaml", "flask", "werkzeug",
]

a = Analysis(
    [str(BASE / "app.py")],
    pathex=[str(BASE)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FaireL3s",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FaireL3s",
)
