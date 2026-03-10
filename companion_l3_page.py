#!/usr/bin/env python3
"""
Generate a Bitfocus Companion page with 16 L3 buttons at 5/0/1–5/0/8 and 5/1/1–5/1/8.
Each button: text "\\nL3\\n<Name>" (no theme in label), black bg, white text, alignment left:top,
png64 = cropped thumbnail (content only, no transparent margins), pngalignment left:bottom.

Button order: use --csv to match CSV row order (PNGs matched by name); otherwise alphabetical.

Usage:
  python3 companion_l3_page.py --template template_page6_l3.companionconfig --png-dir Output2 --out output/page6_l3.companionconfig
  python3 companion_l3_page.py --template template_page6_l3.companionconfig --csv people.csv --png-dir Output2 --out output/page6_l3.companionconfig

Template can be JSON or YAML. Output is YAML. Optional: --atem-ip IP.
"""

from __future__ import annotations

import argparse
import base64
import copy
import csv
import io
import json
import random
import re
import string
import subprocess
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

# 16 buttons: row 0 cols 1–8, row 1 cols 1–8. Media pool 40–55.
DEFAULT_ROWS = 2
DEFAULT_COLS = 8
MEDIA_POOL_START = 40
THUMB_SIZE = 72


def _new_id() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=11)) + "_" + "".join(
        random.choices(string.ascii_letters + string.digits, k=10)
    )


def _clone_with_new_ids(obj: Any, id_map: dict[str, str]) -> Any:
    """Deep clone and replace every 'id' with a new unique id."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "id" and isinstance(v, str):
                if v not in id_map:
                    id_map[v] = _new_id()
                out[k] = id_map[v]
            else:
                out[k] = _clone_with_new_ids(v, id_map)
        return out
    if isinstance(obj, list):
        return [_clone_with_new_ids(x, id_map) for x in obj]
    return obj


def _set_media_source(actions: list[dict], source: int) -> None:
    """In-place: set mediaPlayerSource source to given value."""
    for a in actions:
        if a.get("definitionId") == "mediaPlayerSource" and (a.get("options") or {}).get("mediaplayer") == 1:
            a.setdefault("options", {})["source"] = source
            return
        for key in ("actions", "condition", "else_actions"):
            children = (a.get("children") or {}).get(key)
            if isinstance(children, list):
                _set_media_source(children, source)


def _set_button_label(actions: list[dict], label: str, only_last_in_list: bool = False) -> None:
    """In-place: set button_text label. In else_actions the first button_text is 'Too fast, try again!' (leave it); only the last one (restore) gets the label."""
    if only_last_in_list:
        indices = [i for i, a in enumerate(actions) if a.get("definitionId") == "button_text"]
        if indices:
            actions[indices[-1]].setdefault("options", {})["label"] = label
        for a in actions:
            for key in ("actions", "else_actions"):
                children = (a.get("children") or {}).get(key)
                if isinstance(children, list):
                    _set_button_label(children, label, only_last_in_list=(key == "else_actions"))
        return
    for a in actions:
        if a.get("definitionId") == "button_text":
            a.setdefault("options", {})["label"] = label
        for key in ("actions", "else_actions"):
            children = (a.get("children") or {}).get(key)
            if isinstance(children, list):
                _set_button_label(children, label, only_last_in_list=(key == "else_actions"))


def filename_to_label(filename: str) -> str:
    """e.g. lowerthird_jen_burke.png -> Jen Burke; lowerthird_max_rhodes.png -> Max Rhodes."""
    name = Path(filename).stem
    if name.lower().startswith("lowerthird_"):
        name = name[11:]
    return name.replace("_", " ").title()


# Theme suffixes from generate_lowerthirds.py (no suffix = default)
THEME_SUFFIX_RE = re.compile(
    r"_(palette_\w+|dark_alt|bright_insider|bright_warm|bright_info|dark|bright)$",
    re.IGNORECASE,
)


def filename_to_display_name(filename: str) -> str:
    """Name only, no theme: lowerthird_jen_burke_palette_teal.png -> Jen Burke."""
    stem = Path(filename).stem
    if stem.lower().startswith("lowerthird_"):
        stem = stem[11:]
    stem = THEME_SUFFIX_RE.sub("", stem)
    return stem.replace("_", " ").title()


def _display_name_match(png_name: str, csv_name: str) -> bool:
    """True if display name from PNG filename matches CSV name (normalized)."""
    a = filename_to_display_name(png_name).strip().lower()
    b = csv_name.strip().lower()
    return a == b


def ordered_pngs_from_csv(csv_path: Path, png_dir: Path) -> tuple[list[Path], list[str]]:
    """Return (png_paths, labels) in CSV row order. Labels = name column only."""
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "name" not in reader.fieldnames:
            raise SystemExit("CSV must have a 'name' column.")
        csv_rows = [row for row in reader if (row.get("name") or "").strip()]
    if not csv_rows:
        raise SystemExit("CSV has no name rows.")
    all_pngs = sorted(png_dir.resolve().glob("*.png"))
    if not all_pngs:
        raise SystemExit(f"No PNGs in {png_dir}")
    paths: list[Path] = []
    labels: list[str] = []
    used: set[Path] = set()
    for row in csv_rows:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        found = None
        for p in all_pngs:
            if p not in used and _display_name_match(p.name, name):
                found = p
                break
        if found is None:
            raise SystemExit(f"No PNG found for CSV name '{name}' in {png_dir}. Names from filenames: {[filename_to_display_name(p.name) for p in all_pngs]}")
        used.add(found)
        paths.append(found)
        labels.append(name)
    return paths, labels


def _crop_to_content(img: Image.Image) -> Image.Image:
    """Crop image to bounding box of non-transparent pixels (RGBA)."""
    img = img.convert("RGBA")
    alpha = img.split()[-1]
    # getbbox() returns bbox of non-zero pixels
    mask = alpha.point(lambda p: 255 if p > 0 else 0, mode="1")
    bbox = mask.getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def png_to_base64(path: Path, size: int = THUMB_SIZE) -> str:
    img = Image.open(path).convert("RGBA")
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def png_to_base64_cropped(path: Path, size: int = THUMB_SIZE) -> str:
    """Crop to content bbox (no transparent margins), then thumbnail and base64."""
    img = Image.open(path).convert("RGBA")
    img = _crop_to_content(img)
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _has_media_source(actions: list[dict]) -> bool:
    """Recursively check if any action is mediaPlayerSource with mediaplayer 1."""
    for a in actions:
        if a.get("definitionId") == "mediaPlayerSource" and (a.get("options") or {}).get("mediaplayer") == 1:
            return True
        for key in ("actions", "condition", "else_actions"):
            sub = (a.get("children") or {}).get(key)
            if isinstance(sub, list) and _has_media_source(sub):
                return True
    return False


def get_template_button(data: dict) -> Optional[dict]:
    """Get first button that has mediaPlayerSource (mediaplayer 1) from template page."""
    controls = (data.get("page") or {}).get("controls") or {}
    for row in sorted(controls.keys(), key=lambda x: (x.isdigit(), int(x) if x.isdigit() else 0)):
        for col in sorted((controls[row] or {}).keys(), key=lambda x: (x.isdigit(), int(x) if x.isdigit() else 0)):
            ctrl = (controls[row] or {}).get(col)
            if not isinstance(ctrl, dict) or ctrl.get("type") != "button":
                continue
            steps = (ctrl.get("steps") or {}).get("0") or {}
            down = (steps.get("action_sets") or {}).get("down") or []
            if _has_media_source(down):
                return ctrl
    return None


def _load_template(template_path: Path) -> dict:
    """Load template from JSON or YAML. Companion exports JSON (tabs); YAML disallows tabs."""
    raw = template_path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("{"):
        return json.loads(raw)
    return yaml.safe_load(raw)


def build_page(
    template_path: Path,
    png_paths: list[Path],
    labels: list[str],
    media_start: int = MEDIA_POOL_START,
    thumb_size: int = THUMB_SIZE,
) -> dict:
    """Build Companion page with one button per PNG; labels and png64 set; media pool 40, 41, ..."""
    data = _load_template(template_path)

    template_btn = get_template_button(data)
    if not template_btn:
        raise SystemExit("Template page has no button with mediaPlayerSource (mediaplayer 1).")

    page = data.get("page") or {}
    # Start from template controls so other buttons (BAIL, HOME, etc.) are preserved
    template_controls = page.get("controls") or {}
    controls = copy.deepcopy(template_controls)
    n = min(len(png_paths), 16)
    cols_per_row = 8

    for i in range(n):
        row = str(i // cols_per_row)
        col = str((i % cols_per_row) + 1)
        source_id = media_start + i
        label = labels[i] if i < len(labels) else filename_to_display_name(png_paths[i].name)
        # Button text: leading newline, then L3, then newline, then name (no theme)
        button_text = f"\nL3\n{label}"
        png64 = png_to_base64_cropped(png_paths[i], thumb_size)

        id_map: dict[str, str] = {}
        btn = _clone_with_new_ids(template_btn, id_map)
        style = btn.setdefault("style", {})
        style["text"] = button_text
        style["png64"] = png64
        style["alignment"] = "left:top"
        style["pngalignment"] = "left:bottom"
        style["color"] = 16777215   # white text
        style["bgcolor"] = 0        # black background
        steps = (btn.get("steps") or {}).get("0") or {}
        down = (steps.get("action_sets") or {}).get("down") or []
        _set_media_source(down, source_id)
        _set_button_label(down, button_text)

        if row not in controls:
            controls[row] = {}
        controls[row][col] = btn

    page["controls"] = controls
    data["page"] = page
    return data


def upload_to_atem(png_paths: list[Path], atem_ip: str, media_start: int) -> None:
    """Try to upload PNGs to ATEM media pool. Requires external tool or PyATEMAPI server."""
    # PyATEMAPI runs as a server; we could HTTP POST to it if running. Alternatively use atemlib MediaUpload.
    # Check for common tools:
    for i, path in enumerate(png_paths[:16]):
        slot = media_start + i
        # Try atemlib MediaUpload if on PATH (Windows/.exe or script)
        try:
            subprocess.run(
                ["MediaUpload", atem_ip, str(slot), str(path)],
                check=False,
                capture_output=True,
            )
        except FileNotFoundError:
            pass
    print("ATEM upload: use PyATEMAPI server (see README) or atemlib MediaUpload.exe to upload PNGs to the switcher.", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate Companion page with 16 L3 buttons (labels + png64 from files, media pool 40–55)")
    ap.add_argument("--template", type=Path, required=True, help="Existing Companion page config to clone button structure from")
    ap.add_argument("--png-dir", type=Path, default=None, help="Folder of L3 PNGs")
    ap.add_argument("--csv", type=Path, default=None, help="CSV with name,title rows; button order = CSV order (match PNGs by name)")
    ap.add_argument("--png-list", type=Path, nargs="+", default=None, help="Explicit list of PNG paths (overrides --png-dir)")
    ap.add_argument("--out", type=Path, default=None, help="Output .companionconfig path (default: same dir as PNGs, page6_l3.companionconfig)")
    ap.add_argument("--media-start", type=int, default=MEDIA_POOL_START, help=f"First media pool index (default {MEDIA_POOL_START})")
    ap.add_argument("--thumb-size", type=int, default=THUMB_SIZE, help=f"Button thumbnail size (default {THUMB_SIZE})")
    ap.add_argument("--atem-ip", type=str, default=None, help="ATEM IP for optional upload (see README for setup)")
    args = ap.parse_args()

    if args.png_list:
        png_paths = [Path(p).resolve() for p in args.png_list]
        labels = [filename_to_display_name(p.name) for p in png_paths]
    elif args.csv and args.csv.exists() and args.png_dir and args.png_dir.is_dir():
        png_paths, labels = ordered_pngs_from_csv(args.csv.resolve(), args.png_dir)
        png_paths = png_paths[:16]
        labels = labels[:16]
    elif args.png_dir and args.png_dir.is_dir():
        png_paths = sorted(args.png_dir.resolve().glob("*.png"))[:16]
        labels = [filename_to_display_name(p.name) for p in png_paths]
    else:
        raise SystemExit("Provide --png-dir with optional --csv for order, or --png-list.")

    if not png_paths:
        raise SystemExit("No PNGs found.")

    labels = labels[: len(png_paths)]
    if args.out is None:
        # Default: write config next to the PNGs
        if args.png_dir and args.png_dir.is_dir():
            args.out = args.png_dir.resolve() / "page6_l3.companionconfig"
        else:
            args.out = png_paths[0].resolve().parent / "page6_l3.companionconfig"
    else:
        args.out = args.out.resolve()

    data = build_page(
        args.template.resolve(),
        png_paths,
        labels,
        media_start=args.media_start,
        thumb_size=args.thumb_size,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Wrote {len(png_paths)} buttons to {args.out}")
    if args.atem_ip:
        upload_to_atem(png_paths, args.atem_ip, args.media_start)


if __name__ == "__main__":
    main()
