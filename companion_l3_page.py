#!/usr/bin/env python3
"""
Generate a Bitfocus Companion page with up to 26 L3 buttons.
Layout: row 0 cols 1–8, row 1 cols 1–8, row 2 cols 1–7, row 3 cols 1–3 (fits Stream Deck Studio + 32-button with reference buttons).
Each button: text "\\nL3\\n<Name>" (no theme), black bg, white text, left:top; png64 = cropped thumbnail, left:bottom.
Button order: --csv for CSV row order; otherwise alphabetical. Config written to PNG dir as l3.companionconfig by default. Works on any Companion page when imported (references use expressions).
"""

from __future__ import annotations

import argparse
import base64
import copy
import csv
import gzip
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

# Layout: row 0 cols 1–8, row 1 cols 1–8, row 2 cols 1–7, row 3 cols 1–3 (26 buttons total).
# Matches Stream Deck Studio + 32-button layout with reference buttons for overflow.
L3_BUTTON_LAYOUT = (
    [("0", str(c)) for c in range(1, 9)]   # row 0: 1–8
    + [("1", str(c)) for c in range(1, 9)]  # row 1: 1–8
    + [("2", str(c)) for c in range(1, 8)]  # row 2: 1–7
    + [("3", str(c)) for c in range(1, 4)]  # row 3: 1–3
)
MAX_L3_BUTTONS = len(L3_BUTTON_LAYOUT)  # 26
# Media pool ends at 60; 26 buttons need slots 35–60.
MEDIA_POOL_START = 35
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
    """Name only, no theme: 35_lowerthird_jen_burke_palette_teal.png -> Jen Burke."""
    stem = Path(filename).stem
    stem = re.sub(r"^\d+_", "", stem)  # strip media-pool prefix (e.g. 35_)
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


# Match location_text that is a single page/row/col (e.g. "5/2/1") so we can make it page-agnostic.
_LOCATION_PAGE_ROW_COL_RE = re.compile(r"^(\d+)/(\d+)/(\d+)$")

# Reference/non-L3 buttons: do not change their location_text/location_expression (leave template as-is).
# Row 0 cols 8–16, row 1 cols 8–16, row 2 col 8, row 3 cols 4–8.
_PROTECTED_BUTTON_POSITIONS: frozenset[tuple[str, str]] = frozenset(
    [("0", str(c)) for c in range(8, 17)]
    + [("1", str(c)) for c in range(8, 17)]
    + [("2", "8")]
    + [("3", str(c)) for c in range(4, 9)]
)


def _fix_page_references(obj: Any, _path: tuple[Any, ...] = (), _skip_buttons: frozenset[tuple[str, str]] | None = None) -> None:
    """In-place: replace hardcoded page/row/col with expression for any-page. Skip buttons at protected positions."""
    if _skip_buttons is None:
        _skip_buttons = _PROTECTED_BUTTON_POSITIONS
    # If we're inside page.controls[row][col], path starts with ("page","controls",row,col,...)
    current_button: tuple[str, str] | None = None
    if len(_path) >= 4 and _path[0] == "page" and _path[1] == "controls":
        current_button = (str(_path[2]), str(_path[3]))
    if isinstance(obj, dict):
        opts = obj.get("options") or {}
        loc_text = (opts.get("location_text") or "").strip()
        if isinstance(loc_text, str) and (current_button is None or current_button not in _skip_buttons):
            m = _LOCATION_PAGE_ROW_COL_RE.match(loc_text)
            if m:
                _page, row, col = m.groups()
                opts["location_expression"] = f"concat($(this:page), '/', '{row}', '/', '{col}')"
        for k, v in obj.items():
            _fix_page_references(v, _path + (k,), _skip_buttons)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _fix_page_references(v, _path + (i,), _skip_buttons)


def _load_template(template_path: Path) -> dict:
    """Load template from JSON or YAML. Handles gzip-compressed export (Companion sometimes exports .companionconfig as gzip)."""
    raw_bytes = template_path.read_bytes()
    if raw_bytes[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw_bytes).decode("utf-8")
    else:
        raw = raw_bytes.decode("utf-8")
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
    """Build Companion page with one button per PNG; labels and png64 set; media pool 35–60 (26 slots)."""
    data = _load_template(template_path)

    template_btn = get_template_button(data)
    if not template_btn:
        raise SystemExit("Template page has no button with mediaPlayerSource (mediaplayer 1).")

    page = data.get("page") or {}
    # Start from template controls so other buttons (BAIL, HOME, etc.) are preserved
    template_controls = page.get("controls") or {}
    controls = copy.deepcopy(template_controls)
    n = min(len(png_paths), len(L3_BUTTON_LAYOUT))

    for i in range(n):
        row, col = L3_BUTTON_LAYOUT[i]
        # ATEM media pool source is 0-based; slot N in UI = index N-1
        source_id = (media_start + i) - 1
        label = labels[i] if i < len(labels) else filename_to_display_name(png_paths[i].name)
        # Button text: leading newline, then L3, then newline, then name (no theme)
        slot_num = media_start + i
        button_text = f"\nL3 #{slot_num}\n{label}"
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


def write_slot_manifest(
    png_paths: list[Path],
    labels: list[str],
    out_dir: Path,
    media_start: int = MEDIA_POOL_START,
) -> Path:
    """Write slot_manifest.csv mapping slot numbers to filenames and names."""
    manifest_path = out_dir / "slot_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["slot", "filename", "name"])
        for i, (png, label) in enumerate(zip(png_paths[:MAX_L3_BUTTONS], labels[:MAX_L3_BUTTONS])):
            writer.writerow([media_start + i, png.name, label])
    return manifest_path


try:
    import pyatem.transport as _pyatem_transport
    HAS_PYATEM = True
except ImportError:
    HAS_PYATEM = False


def _premultiply_alpha(img: "Image.Image") -> "Image.Image":
    """Premultiply RGBA channels by alpha for ATEM upload."""
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    r = r.point(lambda i: i)  # ensure mode
    from PIL import ImageMath
    r = ImageMath.eval("convert(a * c / 255, 'L')", a=a, c=r)
    g = ImageMath.eval("convert(a * c / 255, 'L')", a=a, c=g)
    b = ImageMath.eval("convert(a * c / 255, 'L')", a=a, c=b)
    return Image.merge("RGBA", (r, g, b, a))


def upload_to_atem(
    png_paths: list[Path],
    atem_ip: str,
    media_start: int,
    labels: list[str] | None = None,
    progress_callback: Any = None,
) -> dict:
    """Upload PNGs to ATEM media pool slots via pyatem.

    Returns dict with 'ok' bool, 'uploaded' count, 'errors' list, 'message' str.
    progress_callback(slot, label, i, total) is called per file if provided.
    """
    n = min(len(png_paths), MAX_L3_BUTTONS)
    if labels is None:
        labels = [filename_to_display_name(p.name) for p in png_paths]

    if not HAS_PYATEM:
        return {
            "ok": False,
            "uploaded": 0,
            "errors": ["pyatem not installed. Run: pip install pyatem"],
            "message": "pyatem not installed. Run: pip install pyatem",
        }

    import time as _time
    errors: list[str] = []
    uploaded = 0

    try:
        switcher = _pyatem_transport.UdpProtocol()
        switcher.connect(atem_ip)
        # Wait for connection handshake
        deadline = _time.time() + 10
        while not switcher.connected and _time.time() < deadline:
            switcher.loop()
            _time.sleep(0.05)
        if not switcher.connected:
            return {
                "ok": False,
                "uploaded": 0,
                "errors": [f"Could not connect to ATEM at {atem_ip} (timeout)"],
                "message": f"Could not connect to ATEM at {atem_ip} (timeout)",
            }
    except Exception as e:
        return {
            "ok": False,
            "uploaded": 0,
            "errors": [f"ATEM connection error: {e}"],
            "message": f"ATEM connection error: {e}",
        }

    for i in range(n):
        slot = media_start + i  # 1-based slot number
        slot_index = slot - 1   # 0-based index for pyatem
        label = labels[i] if i < len(labels) else f"L3 {i+1}"
        if progress_callback:
            progress_callback(slot, label, i, n)

        try:
            img = Image.open(png_paths[i]).convert("RGBA")
            # ATEM expects 1920x1080 RGBA premultiplied
            if img.size != (1920, 1080):
                img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            img = _premultiply_alpha(img)
            frame_data = img.tobytes()

            # Upload still to media pool
            switcher.upload_still(slot_index, frame_data, label)

            # Process upload packets
            upload_deadline = _time.time() + 30
            while _time.time() < upload_deadline:
                switcher.loop()
                _time.sleep(0.01)
                # Check if upload is complete (no pending transfers)
                if not hasattr(switcher, '_transfers') or not switcher._transfers:
                    break

            uploaded += 1
        except Exception as e:
            errors.append(f"Slot {slot} ({label}): {e}")
            # Retry once
            try:
                _time.sleep(0.5)
                switcher.loop()
                img = Image.open(png_paths[i]).convert("RGBA")
                if img.size != (1920, 1080):
                    img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
                img = _premultiply_alpha(img)
                frame_data = img.tobytes()
                switcher.upload_still(slot_index, frame_data, label)
                upload_deadline = _time.time() + 30
                while _time.time() < upload_deadline:
                    switcher.loop()
                    _time.sleep(0.01)
                    if not hasattr(switcher, '_transfers') or not switcher._transfers:
                        break
                uploaded += 1
                errors.pop()  # remove the error since retry succeeded
            except Exception as e2:
                errors.append(f"Slot {slot} ({label}) retry also failed: {e2}")

    try:
        switcher.disconnect()
    except Exception:
        pass

    ok = uploaded > 0 and len(errors) == 0
    parts = [f"Uploaded {uploaded}/{n} stills to ATEM at {atem_ip}."]
    if errors:
        parts.append(f" Errors: {'; '.join(errors)}")
    message = "".join(parts)

    return {"ok": ok, "uploaded": uploaded, "errors": errors, "message": message}


def build_setup_page(
    png_paths: list[Path],
    labels: list[str],
    media_start: int = MEDIA_POOL_START,
) -> dict:
    """Build a Companion 'Setup' page with upload buttons for each L3 still.

    Each button uses the ATEM module's mediaPoolUploadStill action to upload
    a specific PNG file to the correct media pool slot. An 'Upload All' master
    button chains all uploads sequentially.

    Requires ATEM Companion module with mediaPoolUploadStill action support.
    """
    n = min(len(png_paths), MAX_L3_BUTTONS)

    controls: dict[str, dict] = {}
    upload_action_ids: list[str] = []

    for i in range(n):
        row, col = L3_BUTTON_LAYOUT[i]
        slot = media_start + i
        slot_index = slot - 1  # 0-based for ATEM protocol
        label = labels[i] if i < len(labels) else f"L3 {i+1}"
        png_path = str(png_paths[i].resolve())

        action_id = _new_id()
        upload_action_ids.append(action_id)

        btn: dict[str, Any] = {
            "type": "button",
            "style": {
                "text": f"Upload #{slot}\n{label}",
                "size": "auto",
                "color": 16777215,      # white text
                "bgcolor": 1118481,     # dark blue: #111111
                "alignment": "center:center",
                "png64": None,
                "pngalignment": "center:center",
                "show_topbar": "default",
            },
            "options": {
                "relativeDelay": False,
                "rotaryActions": False,
                "stepAutoProgress": True,
            },
            "feedbacks": [],
            "steps": {
                "0": {
                    "action_sets": {
                        "down": [
                            {
                                "id": action_id,
                                "instance": "bmd-atem",
                                "definitionId": "mediaPoolUploadStill",
                                "options": {
                                    "slot": slot_index,
                                    "filepath": png_path,
                                    "name": label,
                                },
                            },
                            {
                                "id": _new_id(),
                                "instance": "internal",
                                "definitionId": "button_text",
                                "options": {
                                    "label": f"Done #{slot}\n{label}",
                                },
                            },
                        ],
                        "up": [],
                    },
                    "options": {"runWhileHeld": 0},
                },
            },
        }

        if row not in controls:
            controls[row] = {}
        controls[row][col] = btn

    # 'Upload All' master button at row 3, col 7 (bottom right area)
    master_row, master_col = "3", "7"
    master_down: list[dict] = []
    for i in range(n):
        row_ref, col_ref = L3_BUTTON_LAYOUT[i]
        master_down.append({
            "id": _new_id(),
            "instance": "internal",
            "definitionId": "button_press",
            "options": {
                "location_text": f"0/{row_ref}/{col_ref}",
                "location_expression": f"concat($(this:page), '/', '{row_ref}', '/', '{col_ref}')",
            },
        })
        # Small delay between uploads to avoid overwhelming the ATEM
        if i < n - 1:
            master_down.append({
                "id": _new_id(),
                "instance": "internal",
                "definitionId": "wait",
                "options": {"time": 2000},
            })
    master_down.append({
        "id": _new_id(),
        "instance": "internal",
        "definitionId": "button_text",
        "options": {"label": f"All Done\n({n} stills)"},
    })

    master_btn: dict[str, Any] = {
        "type": "button",
        "style": {
            "text": f"Upload All\n({n} stills)",
            "size": "auto",
            "color": 16777215,
            "bgcolor": 26214,       # blue: #006666
            "alignment": "center:center",
            "png64": None,
            "pngalignment": "center:center",
            "show_topbar": "default",
        },
        "options": {
            "relativeDelay": False,
            "rotaryActions": False,
            "stepAutoProgress": True,
        },
        "feedbacks": [],
        "steps": {
            "0": {
                "action_sets": {
                    "down": master_down,
                    "up": [],
                },
                "options": {"runWhileHeld": 0},
            },
        },
    }

    if master_row not in controls:
        controls[master_row] = {}
    controls[master_row][master_col] = master_btn

    page = {
        "name": "L3 Setup — Upload Stills",
        "controls": controls,
        "gridSize": {"minColumn": 0, "maxColumn": 8, "minRow": 0, "maxRow": 4},
    }

    return {
        "version": 4,
        "type": "page",
        "page": page,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=f"Generate Companion page with up to {MAX_L3_BUTTONS} L3 buttons (labels + png64, media pool 35–60). Layout: row 0–1 cols 1–8, row 2 cols 1–7, row 3 cols 1–3.")
    ap.add_argument("--template", type=Path, required=True, help="Existing Companion page config to clone button structure from")
    ap.add_argument("--png-dir", type=Path, default=None, help="Folder of L3 PNGs")
    ap.add_argument("--csv", type=Path, default=None, help="CSV with name,title rows; button order = CSV order (match PNGs by name)")
    ap.add_argument("--png-list", type=Path, nargs="+", default=None, help="Explicit list of PNG paths (overrides --png-dir)")
    ap.add_argument("--out", type=Path, default=None, help="Output .companionconfig path (default: same dir as PNGs, l3.companionconfig)")
    ap.add_argument("--media-start", type=int, default=MEDIA_POOL_START, help=f"First media pool index (default {MEDIA_POOL_START})")
    ap.add_argument("--thumb-size", type=int, default=THUMB_SIZE, help=f"Button thumbnail size (default {THUMB_SIZE})")
    ap.add_argument("--atem-ip", type=str, default=None, help="ATEM IP for optional upload (see README for setup)")
    args = ap.parse_args()

    if args.png_list:
        png_paths = [Path(p).resolve() for p in args.png_list]
        labels = [filename_to_display_name(p.name) for p in png_paths]
    elif args.csv and args.csv.exists() and args.png_dir and args.png_dir.is_dir():
        png_paths, labels = ordered_pngs_from_csv(args.csv.resolve(), args.png_dir)
        png_paths = png_paths[:MAX_L3_BUTTONS]
        labels = labels[:MAX_L3_BUTTONS]
    elif args.png_dir and args.png_dir.is_dir():
        png_paths = sorted(args.png_dir.resolve().glob("*.png"))[:MAX_L3_BUTTONS]
        labels = [filename_to_display_name(p.name) for p in png_paths]
    else:
        raise SystemExit("Provide --png-dir with optional --csv for order, or --png-list.")

    if not png_paths:
        raise SystemExit("No PNGs found.")

    labels = labels[: len(png_paths)]
    if args.out is None:
        # Default: write config next to the PNGs
        if args.png_dir and args.png_dir.is_dir():
            args.out = args.png_dir.resolve() / "l3.companionconfig"
        else:
            args.out = png_paths[0].resolve().parent / "l3.companionconfig"
    else:
        args.out = args.out.resolve()

    data = build_page(
        args.template.resolve(),
        png_paths,
        labels,
        media_start=args.media_start,
        thumb_size=args.thumb_size,
    )
    _fix_page_references(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Wrote {len(png_paths)} buttons to {args.out}")

    # Write slot manifest
    out_dir = args.out.parent
    manifest = write_slot_manifest(png_paths, labels, out_dir, args.media_start)
    print(f"Wrote slot manifest to {manifest}")

    # Write setup page
    setup_data = build_setup_page(png_paths, labels, args.media_start)
    setup_path = out_dir / "l3_setup.companionconfig"
    with setup_path.open("w", encoding="utf-8") as f:
        yaml.dump(setup_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Wrote setup page to {setup_path}")

    if args.atem_ip:
        result = upload_to_atem(png_paths, args.atem_ip, args.media_start, labels=labels)
        print(result["message"], file=sys.stderr)


if __name__ == "__main__":
    main()
