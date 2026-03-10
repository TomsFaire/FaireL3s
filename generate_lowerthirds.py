#!/usr/bin/env python3
"""Generate Faire-style lower-third transparent PNGs (1920x1080).

Single render:
  python generate_lowerthirds.py --name "Max Rhodes" --title "Chief Executive Officer" --out lowerthird_max.png

Batch from CSV:
  python generate_lowerthirds.py --csv people.csv --out_dir out/

Batch + Companion page (one command):
  python generate_lowerthirds.py --csv people.csv --out_dir output/ --companion

CSV format:
  name,title
  Max Rhodes,Chief Executive Officer
  Thuan Pham,Chief Technology Officer

Fonts:
  Faire uses Graphik (sans) for UI; this script uses Graphik for name + title.
  If you have Graphik: put Graphik-SemiBold.ttf (or Medium) and Graphik-Regular.ttf
  in font/ or fonts/. Otherwise use Inter (unzip Google Fonts "Inter" folder
  here, or put Inter-SemiBold.ttf and Inter-Regular.ttf in font/ or fonts/).
  Falls back to system font if none found.
"""
from __future__ import annotations

__version__ = "0.0.5"

import argparse
import csv
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

# Faire CDN (internal use): Graphik fonts for lower thirds
FAIRE_GRAPHIK_FONTS = [
    ("https://cdn.faire.com/static/fonts/GraphikRegular.otf", "Graphik-Regular.otf"),
    ("https://cdn.faire.com/static/fonts/GraphikMedium.otf", "Graphik-Medium.otf"),
    ("https://cdn.faire.com/static/fonts/GraphikSemiBold.otf", "Graphik-SemiBold.otf"),
]

from PIL import Image, ImageDraw, ImageFont

THIS_DIR = Path(__file__).resolve().parent

# Faire brand typeface: Graphik (sans) for UI. Fallback: Inter. iOS bundles Graphik + Nantes.
SEMIBOLD_CANDIDATES = [
    "Graphik-SemiBold.ttf", "Graphik-SemiBold.otf", "Graphik-Medium.ttf", "Graphik-Medium.otf",
    "Inter_18pt-SemiBold.ttf", "Inter_24pt-SemiBold.ttf", "Inter_28pt-SemiBold.ttf",
    "Inter-SemiBold.ttf", "Inter-Bold.ttf", "InterSemiBold.ttf",
]
REGULAR_CANDIDATES = [
    "Graphik-Regular.ttf", "Graphik-Regular.otf",
    "Inter_18pt-Regular.ttf", "Inter_24pt-Regular.ttf", "Inter_28pt-Regular.ttf",
    "Inter-Regular.ttf", "InterRegular.ttf",
]


def _font_search_dirs() -> list[Path]:
    """Directories to search for font files. Order: Graphik folder, font/fonts, Inter folder."""
    out: list[Path] = []
    for child in THIS_DIR.iterdir():
        if not child.is_dir():
            continue
        name_lower = child.name.lower()
        if name_lower == "graphik":
            out.append(child)
            static = child / "static"
            if static.is_dir():
                out.append(static)
            break
    for name in ("font", "fonts"):
        d = THIS_DIR / name
        if d.is_dir():
            out.append(d)
            break
    for child in THIS_DIR.iterdir():
        if child.is_dir() and child.name.lower() == "inter":
            out.append(child)
            static = child / "static"
            if static.is_dir():
                out.append(static)
            break
    if not out:
        out.append(THIS_DIR / "fonts")
    return out


def _resolve_font(search_dirs: list[Path], candidates: list[str]) -> Optional[Path]:
    for d in search_dirs:
        if not d.exists():
            continue
        for name in candidates:
            p = d / name
            if p.exists():
                return p
        lower_map = {f.name.lower(): f for f in d.iterdir() if f.suffix.lower() in (".ttf", ".otf")}
        for name in candidates:
            if name.lower() in lower_map:
                return lower_map[name.lower()]
    return None


# When Inter isn't found, use a system TTF so text is full size (not PIL's tiny default)
_SYSTEM_BOLD = [
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/Library/Fonts/Arial Bold.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
]
_SYSTEM_REGULAR = [
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
]

def _system_font(for_bold: bool) -> Optional[Path]:
    for p in (_SYSTEM_BOLD if for_bold else _SYSTEM_REGULAR):
        if p.exists():
            return p
    for p in _SYSTEM_REGULAR + _SYSTEM_BOLD:
        if p.exists():
            return p
    return None


THEME_FILES = {
    "default": "style.json",
    "dark": "style_dark.json",
    "dark_alt": "style_dark_alt.json",
    "bright": "style_bright.json",
    "bright_insider": "style_bright_insider.json",
    "bright_warm": "style_bright_warm.json",
    "bright_info": "style_bright_info.json",
    "palette_olive": "style_palette_olive.json",
    "palette_teal": "style_palette_teal.json",
    "palette_terracotta": "style_palette_terracotta.json",
    "palette_plum": "style_palette_plum.json",
    "palette_copper": "style_palette_copper.json",
    "palette_sage": "style_palette_sage.json",
}


def load_style(theme: str = "default") -> dict:
    filename = THEME_FILES.get(theme, THEME_FILES["default"])
    style_path = THIS_DIR / filename
    if not style_path.exists():
        raise FileNotFoundError(f"Missing {filename} next to script: {style_path}")
    return json.loads(style_path.read_text())


def fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Optional[Path],
    start_size: int,
    max_width: int,
    min_size: int = 16,
    prefer_bold: bool = False,
) -> ImageFont.ImageFont:
    """Shrink font until text fits on one line. Uses system font if path missing (never tiny default)."""
    if font_path is None or not font_path.exists():
        font_path = _system_font(prefer_bold)
    if font_path is None or not font_path.exists():
        return ImageFont.load_default()

    size = start_size
    while size >= min_size:
        f = ImageFont.truetype(str(font_path), size=size)
        bbox = draw.textbbox((0, 0), text, font=f)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            return f
        size -= 2

    return ImageFont.truetype(str(font_path), size=min_size)


def rounded_rectangle(draw: ImageDraw.ImageDraw, xy: Tuple[int, int, int, int], radius: int, fill, outline=None, width: int = 1):
    """Compatibility wrapper."""
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    else:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)


def render_lowerthird(name: str, title: str, out_path: Path, style: dict) -> None:
    W, H = style["canvas"]["width"], style["canvas"]["height"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Panel layout
    panel_x = style["margins"]["left"]
    panel_y = H - style["margins"]["bottom"] - style["panel"]["height"]
    panel_w = style["panel"]["width"]
    panel_h = style["panel"]["height"]

    fill = tuple(style["panel"]["fill_rgba"])
    border = tuple(style["panel"]["border_rgb"] + [style["panel"]["border_alpha"]])

    rounded_rectangle(
        draw,
        (panel_x, panel_y, panel_x + panel_w, panel_y + panel_h),
        radius=style["panel"]["radius"],
        fill=fill,
        outline=border,
        width=style["panel"]["border_width"],
    )

    # Accent bar
    bar = style["accent_bar"]
    bar_x = panel_x + bar["x"]
    bar_y = panel_y + bar["y"]
    draw.rectangle(
        (bar_x, bar_y, bar_x + bar["width"], bar_y + bar["height"]),
        fill=tuple(bar["rgb"] + [bar["alpha"]]),
    )

    # Text positions
    text_x = panel_x + style["panel"]["padding_left"] + bar["width"] + style["text"]["gap_x_after_bar"]
    name_y = panel_y + style["text"]["name_y"]
    title_y = panel_y + style["text"]["title_y"]
    max_text_width = panel_x + panel_w - style["panel"]["padding_right"] - text_x

    # Fonts: look in Inter/ (and Inter/static/), then font/ or fonts/
    search_dirs = _font_search_dirs()
    semibold_path = _resolve_font(search_dirs, SEMIBOLD_CANDIDATES)
    regular_path = _resolve_font(search_dirs, REGULAR_CANDIDATES)
    if semibold_path is None and regular_path is not None:
        semibold_path = regular_path  # avoid falling back to default; at least use Inter for both

    name_font = fit_font(draw, name, semibold_path, style["text"]["name"]["size"], max_text_width, prefer_bold=True)
    title_font = fit_font(draw, title, regular_path, style["text"]["title"]["size"], max_text_width, prefer_bold=False)

    draw.text((text_x, name_y), name, font=name_font, fill=tuple(style["text"]["name"]["rgb"] + [style["text"]["name"]["alpha"]]))
    draw.text((text_x, title_y), title, font=title_font, fill=tuple(style["text"]["title"]["rgb"] + [style["text"]["title"]["alpha"]]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "lowerthird"


def fetch_faire_fonts() -> Path:
    """Download Graphik from Faire CDN into font/. For internal use."""
    d = THIS_DIR / "font"
    d.mkdir(exist_ok=True)
    for url, filename in FAIRE_GRAPHIK_FONTS:
        path = d / filename
        try:
            urllib.request.urlretrieve(url, path)
            print(f"  {filename}")
        except Exception as e:
            print(f"  {filename}: failed ({e})")
    print(f"Graphik fonts saved to: {d.resolve()}")
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", help="Name line")
    ap.add_argument("--title", help="Title line")
    ap.add_argument("--out", help="Output png path (single render)")
    ap.add_argument("--csv", help="CSV path with columns: name,title (batch render)")
    ap.add_argument("--out_dir", default="out", help="Directory for batch output")
    ap.add_argument("--theme", choices=list(THEME_FILES), default="default",
                    help="Colorway: default, dark, dark_alt, bright (sage), bright_insider (teal), bright_warm (amber), bright_info (slate)")
    ap.add_argument("--fetch-fonts", action="store_true",
                    help="Download Graphik from Faire CDN into font/ (internal use). Then exit.")
    ap.add_argument("--companion", action="store_true",
                    help="After batch from CSV, run companion_l3_page to write l3.companionconfig into out_dir (one-step deploy).")
    ap.add_argument("--companion-template", type=Path, default=None,
                    help="Companion template path for --companion (default: template_l3.companionconfig next to script).")
    ap.add_argument("--media-start", type=int, default=35,
                    help="First media pool slot (default 35). When batching from CSV, filenames are prefixed with slot number so Finder order matches CSV/upload order.")
    args = ap.parse_args()

    if args.fetch_fonts:
        print("Fetching Graphik from Faire CDN...")
        fetch_faire_fonts()
        return

    style = load_style(args.theme)

    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.is_absolute() and not csv_path.exists():
            csv_path = THIS_DIR / csv_path
        out_dir = Path(args.out_dir)
        if not csv_path.exists():
            raise FileNotFoundError(csv_path)

        media_start = getattr(args, "media_start", 35)
        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "name" not in reader.fieldnames or "title" not in reader.fieldnames:
                raise ValueError(f"CSV must have headers name,title. Found: {reader.fieldnames}")

            index = 0
            for row in reader:
                name = (row.get("name") or "").strip()
                title = (row.get("title") or "").strip()
                if not name or not title:
                    continue

                slot = media_start + index
                base = f"{slot}_lowerthird_{slugify(name)}"
                if args.theme != "default":
                    base = f"{base}_{args.theme}"
                out_path = out_dir / f"{base}.png"
                render_lowerthird(name, title, out_path, style)
                index += 1

        print(f"Done. Wrote PNGs to: {out_dir.resolve()}")

        if args.companion:
            companion_script = THIS_DIR / "companion_l3_page.py"
            if not companion_script.exists():
                raise FileNotFoundError(f"Companion script not found: {companion_script}. Run companion_l3_page.py separately.")
            template = args.companion_template or (THIS_DIR / "template_l3.companionconfig")
            template = template.resolve()
            if not template.exists():
                raise FileNotFoundError(f"Companion template not found: {template}")
            out_dir.mkdir(parents=True, exist_ok=True)
            csv_path = csv_path.resolve()
            subprocess.run(
                [
                    sys.executable,
                    str(companion_script),
                    "--template", str(template),
                    "--csv", str(csv_path),
                    "--png-dir", str(out_dir.resolve()),
                    "--media-start", str(media_start),
                ],
                check=True,
            )
            print(f"Companion config written to {out_dir.resolve() / 'l3.companionconfig'}")
        return

    if not (args.name and args.title and args.out):
        ap.error("Single render mode requires --name, --title, --out OR provide --csv for batch mode.")

    render_lowerthird(args.name.strip(), args.title.strip(), Path(args.out), style)
    print(f"Done. Wrote: {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
