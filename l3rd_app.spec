# PyInstaller spec for FaireL3s desktop app.
# Build: pyinstaller l3rd_app.spec
# Run from repo root. Output: dist/FaireL3s/ (folder) or dist/FaireL3s.app (one-file on macOS).

from pathlib import Path

block_cipher = None

# Run PyInstaller from the repo root (directory containing this spec).
BASE = Path(".").resolve()

# All style JSONs and optional Companion template. Add template_l3.companionconfig to repo to bundle it.
style_jsons = [
    "style.json",
    "style_dark.json",
    "style_dark_alt.json",
    "style_bright.json",
    "style_bright_insider.json",
    "style_bright_warm.json",
    "style_bright_info.json",
    "style_palette_olive.json",
    "style_palette_teal.json",
    "style_palette_terracotta.json",
    "style_palette_plum.json",
    "style_palette_copper.json",
    "style_palette_sage.json",
]
datas = [(str(BASE / name), ".") for name in style_jsons if (BASE / name).exists()]
if (BASE / "template_l3.companionconfig").exists():
    datas.append((str(BASE / "template_l3.companionconfig"), "."))

# companion_l3_page and Flask for the web UI
hiddenimports = [
    "companion_l3_page",
    "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
    "yaml",
    "flask", "werkzeug",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="FaireL3s",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No terminal window on macOS/Windows
)
