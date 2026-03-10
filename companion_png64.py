#!/usr/bin/env python3
"""
Inject base64 thumbnails into a Bitfocus Companion page config so L3 buttons
show the corresponding lower-third image as their background.

Usage:
  python3 companion_png64.py path/to/page.companionconfig path/to/png/folder [--size 72] [--out path/to/output.companionconfig]

- Finds every button that has a mediaPlayerSource action (media pool) in its down actions.
- Assigns PNGs from the folder to buttons in row/column order. PNG order = alphabetical by filename (e.g. name 01_max.png, 02_jen.png so order matches your buttons).
- Resizes each PNG to --size x --size (default 72), encodes as base64, sets style.png64.
- Writes the updated config to --out (default: overwrites the input file with .png64_added backup).
"""

from __future__ import annotations

import argparse
import base64
import io
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    print("pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("pip install pillow", file=sys.stderr)
    sys.exit(1)

THUMB_SIZE = 72


def _find_media_source_in_actions(actions: list[dict]) -> Optional[int]:
    """Recursively find first mediaPlayerSource action and return its source id."""
    for a in actions:
        if a.get("definitionId") == "mediaPlayerSource":
            opts = a.get("options") or {}
            src = opts.get("source")
            if src is not None and opts.get("mediaplayer") == 1:
                return int(src) if isinstance(src, (int, str)) else None
        children = a.get("children") or {}
        for key in ("actions", "condition", "else_actions"):
            sub = children.get(key)
            if isinstance(sub, list):
                found = _find_media_source_in_actions(sub)
                if found is not None:
                    return found
    return None


def collect_l3_buttons(controls: dict) -> list[tuple[str, str]]:
    """Return list of (row, col) for buttons that have mediaPlayerSource (media pool) in down actions."""
    out: list[tuple[str, str]] = []
    for row in sorted(controls.keys(), key=lambda x: (x.isdigit(), int(x) if x.isdigit() else 0)):
        row_data = controls[row]
        if not isinstance(row_data, dict):
            continue
        for col in sorted(row_data.keys(), key=lambda x: (x.isdigit(), int(x) if x.isdigit() else 0)):
            ctrl = row_data[col]
            if not isinstance(ctrl, dict) or ctrl.get("type") != "button":
                continue
            steps = (ctrl.get("steps") or {}).get("0") or {}
            action_sets = steps.get("action_sets") or {}
            down = action_sets.get("down") or []
            if _find_media_source_in_actions(down) is not None:
                out.append((row, col))
    return out


def png_to_base64_thumbnail(path: Path, size: int = THUMB_SIZE) -> str:
    """Load PNG, resize to size x size, return base64 string (no data URL prefix)."""
    img = Image.open(path).convert("RGBA")
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> None:
    ap = argparse.ArgumentParser(description="Set Companion button png64 from folder of PNGs")
    ap.add_argument("config", type=Path, help="Path to .companionconfig page file")
    ap.add_argument("png_folder", type=Path, help="Folder of lower-third PNGs (order = alphabetical)")
    ap.add_argument("--size", type=int, default=THUMB_SIZE, help=f"Thumbnail size (default {THUMB_SIZE})")
    ap.add_argument("--out", type=Path, default=None, help="Output config path (default: same as config, backup as .bak)")
    args = ap.parse_args()

    config_path = args.config.resolve()
    png_folder = args.png_folder.resolve()
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")
    if not png_folder.is_dir():
        raise SystemExit(f"PNG folder not found: {png_folder}")

    pngs = sorted(png_folder.glob("*.png"))
    if not pngs:
        raise SystemExit(f"No .png files in {png_folder}")

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    page = data.get("page") or {}
    controls = page.get("controls") or {}
    buttons = collect_l3_buttons(controls)
    if not buttons:
        raise SystemExit("No buttons with mediaPlayerSource (media pool) found in this page.")

    if len(pngs) < len(buttons):
        print(f"Warning: only {len(pngs)} PNGs for {len(buttons)} buttons; extra buttons keep png64 null.", file=sys.stderr)

    for i, (row, col) in enumerate(buttons):
        if i >= len(pngs):
            break
        png_path = pngs[i]
        b64 = png_to_base64_thumbnail(png_path, args.size)
        if "style" not in controls[row][col]:
            controls[row][col]["style"] = {}
        controls[row][col]["style"]["png64"] = b64
        print(f"  {row}/{col} <- {png_path.name}")

    out_path = args.out.resolve() if args.out else config_path
    if out_path == config_path:
        config_path.rename(config_path.with_suffix(config_path.suffix + ".bak"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
