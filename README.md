# FaireL3s

**v0.0.4**

Generate Faire-style lower-third graphics (1920×1080 transparent PNGs) for video. Name + title on a light panel with accent bar.

## Pick a style 

Use the theme name with `--theme` when you run the script (e.g. `--theme dark`).

| Style | Theme name | Preview |
|-------|------------|---------|
| **Default** (light warm) | `default` | ![Default](output/example_lowerthird.png) |
| **Dark** (#333 panel) | `dark` | ![Dark](output/example_dark.png) |
| **Dark alt** (black panel) | `dark_alt` | ![Dark alt](output/example_dark_alt.png) |
| **Bright** (sage green) | `bright` | ![Bright](output/example_bright.png) |
| **Bright Insider** (teal) | `bright_insider` | ![Bright Insider](output/example_bright_insider.png) |
| **Bright Warm** (amber) | `bright_warm` | ![Bright Warm](output/example_bright_warm.png) |
| **Bright Info** (slate blue-gray) | `bright_info` | ![Bright Info](output/example_bright_info.png) |
| **Palette Olive** (mustard/olive) | `palette_olive` | ![Palette Olive](output/example_palette_olive.png) |
| **Palette Teal** (blue-green) | `palette_teal` | ![Palette Teal](output/example_palette_teal.png) |
| **Palette Terracotta** (dusty rose/terracotta) | `palette_terracotta` | ![Palette Terracotta](output/example_palette_terracotta.png) |
| **Palette Plum** (lavender/plum) | `palette_plum` | ![Palette Plum](output/example_palette_plum.png) |
| **Palette Copper** (warm orange/copper) | `palette_copper` | ![Palette Copper](output/example_palette_copper.png) |
| **Palette Sage** (cool sage green) | `palette_sage` | ![Palette Sage](output/example_palette_sage.png) |

## Requirements

- Python 3.9+
- [Pillow](https://pypi.org/project/Pillow/) (`pip install pillow`)

## Fonts (required for correct look)

Faire uses two core brand typefaces:

- **Graphik** (sans-serif) for most product UI and general readability.<sup>[1]</sup>
- **Nantes** (serif) for “brand voice” moments (e.g. marketing).<sup>[2]</sup>

This script uses **Graphik** for both the name and title lines (SemiBold/Medium for the name, Regular for the title). The iOS codebase bundles Graphik (Regular, Medium, SemiBold) and Nantes (Regular, SemiBold).<sup>[3]</sup>

**This repo does not include font files.** Use one of the options below.

### Option A: Brand fonts (Graphik) — internal

Faire hosts Graphik on the CDN for internal use.<sup>[4]</sup> You can pull the fonts automatically so the script uses the real brand typeface.

**Step 1 — Fetch the fonts**

From the repo directory (where `generate_lowerthirds.py` lives), run:

```bash
python3 generate_lowerthirds.py --fetch-fonts
```

This step:

- Downloads three font files from **cdn.faire.com** (Graphik Regular, Medium, SemiBold)
- Saves them into the **`font/`** folder as `Graphik-Regular.otf`, `Graphik-Medium.otf`, `Graphik-SemiBold.otf`
- Requires **network access** (and works only from environments that can reach Faire’s CDN)

The CDN may require you to be on Faire’s network or VPN; if the download fails (e.g. 403 or connection error), try from a Faire-connected machine or use [Option B](#option-b-inter-substitute-for-graphik) (Inter) instead. No separate login or credentials are used—access is typically governed by network/VPN.

You only need to run `--fetch-fonts` once per machine (or after deleting `font/`). The script does not generate any lower thirds in this step; it only downloads the fonts and then exits.

**Step 2 — Generate lower thirds**

After the fonts are in `font/`, run the script as usual (see [Usage](#usage)). It will use Graphik automatically.

If you already have the Graphik files from another source, put them in **`font/`** or **`fonts/`** with the same names; no need to run `--fetch-fonts`.

### Option B: Inter (substitute for Graphik)

Inter is a good stand-in for Graphik. Easiest: download **[Inter from Google Fonts](https://fonts.google.com/specimen/Inter)** → “Download family”, unzip, and put the unzipped folder next to the script as **`Inter`**. The script looks in `Inter/` and `Inter/static/` for the font files.

Or put only the two needed files in **`font/`** or **`fonts/`**:

- Name line: `Inter-SemiBold.ttf` or `Inter-Bold.ttf`
- Title line: `Inter-Regular.ttf`

### Verify

Run a single lower third. If the name is bold and the title is regular, fonts are set up correctly:

```bash
python3 generate_lowerthirds.py --name "Your Name" --title "Your Title" --out output/test.png
```

### Quick test guide (new palette themes)

To run a quick local test of the new palette colorways:

1. **Use the project venv** (recommended; has Pillow):
   ```bash
   cd /path/to/l3rd\ script
   source .venv/bin/activate   # or: .venv/bin/python below
   ```

2. **Single lower third** with a new theme (e.g. `palette_teal`):
   ```bash
   python3 generate_lowerthirds.py --name "Jane Smith" --title "Chief Executive Officer" --out output/test_palette_teal.png --theme palette_teal
   ```
   Open `output/test_palette_teal.png` to confirm. Swap `palette_teal` for `palette_olive`, `palette_sage`, `palette_terracotta`, `palette_plum`, or `palette_copper` to try others.

3. **Batch test** (all themes from a CSV into one folder):
   ```bash
   mkdir -p output
   python3 generate_lowerthirds.py --csv example_people.csv --out_dir output/ --theme palette_sage
   ```
   Output will be in `output/` with filenames like `lowerthird_jane_smith_palette_sage.png`.

Fonts must be present in `font/` (or `fonts/`) for correct rendering; see [Option A](#option-a-brand-fonts-graphik--internal) or [Option B](#option-b-inter-substitute-for-graphik) above.

## Usage

**One lower third:**

```bash
python3 generate_lowerthirds.py --name "Jane Smith" --title "Chief Executive Officer" --out output/lowerthird_jane_smith.png
```

**Batch from CSV:**

```bash
python3 generate_lowerthirds.py --csv example_people.csv --out_dir output/
```

Create the `output/` directory first if it doesn’t exist. CSV format: header row `name,title`, then one row per person. Use quotes for titles that contain commas.

**Note:** The script overwrites existing files. If a PNG with the same path already exists (e.g. `output/lowerthird_jane_smith.png`), it will be replaced. Use a different `--out` path or `--out_dir` if you want to keep previous output.

```csv
name,title
Jane Smith,Chief Executive Officer
Alex Chen,Chief Technology Officer
```

### Themes (Faire brand colorways)

Use `--theme` with the theme name from the table above. All colors come from the Faire design language.

**Examples:**

```bash
python3 generate_lowerthirds.py --name "Jane Smith" --title "Chief Executive Officer" --out output/jane_dark.png --theme dark
python3 generate_lowerthirds.py --csv example_people.csv --out_dir output/ --theme bright
```

Batch output filenames get a theme suffix when not default (e.g. `lowerthird_jane_smith_dark.png`) so you can generate multiple themes into the same folder.

## Customization

Edit `style.json` (or `style_dark.json`, `style_bright.json`, etc.) to change layout and colors: panel size, margins, text sizes, accent bar, etc.

## Output

- **Size:** 1920×1080  
- **Format:** PNG with transparency  
- **Layout:** Lower-left panel, name (semi-bold) above title (regular)

A sample lower third is included as **`output/example_lowerthird.png`** (Jane Smith, Chief Executive Officer) so you can see the result without running the script.

## Bitfocus Companion: button previews (png64)

If you use **Bitfocus Companion** with buttons that fire lower thirds from the media pool, you can fill each button’s background with a thumbnail of the corresponding L3 image (base64).

**One-time setup:** install PyYAML in the same environment as the main script (`pip install pyyaml`).

**Run:**

```bash
python3 companion_png64.py path/to/your_page.companionconfig path/to/folder/of/l3/pngs [--out path/to/output.companionconfig]
```

- The script finds every button on the page that has a **mediaPlayerSource** (media pool) action.
- It assigns PNGs from the folder to those buttons in **row/column order**. PNG order is **alphabetical by filename**—e.g. name files `01_max.png`, `02_jen.png` so the order matches your buttons.
- Each image is resized to a small thumbnail (default 72×72; use `--size 96` if needed), encoded as base64, and written into `style.png64` for each button.
- Import the **output** config (or overwrite the original; the script can back it up as `.bak`) into Companion so the buttons show the L3 previews.

Example (output to a new file so you don’t overwrite the original):

```bash
python3 companion_png64.py ~/Downloads/zoom_page5.companionconfig "/Users/tom/Documents/Lower 3rds/Output" --out ~/Downloads/zoom_page5_with_previews.companionconfig
```

### Pre-built page: 16 L3 buttons (5/0/1–5/0/8, 5/1/1–5/1/8)

**`companion_l3_page.py`** builds a Companion page with up to 16 L3 buttons (row 0 cols 1–8, row 1 cols 1–8), media pool slots 40–55. The repo includes **`template_page6_l3.companionconfig`** (page 6 “Lower 3rds” with L3 grid plus BAIL, Bug Me, HOME); the script overwrites only the 16 L3 slots and keeps the rest.

- **Buttons:** Text = “L3” then the person’s name (no theme in label), top-left aligned; black background, white text. Image = L3 graphic cropped to content (no transparent margins), aligned bottom-left.
- **Order:** Use **`--csv`** so button order matches CSV row order (PNGs matched by name). Without `--csv`, order is alphabetical by filename.
- **Output:** The Companion config is written into the **same directory as the PNGs** by default as `page6_l3.companionconfig`; use `--out` to override.

**Full workflow (CSV → PNGs → Companion page)**

1. **CSV** — `name,title` header; use `--theme` on the generator if you want (e.g. `palette_teal`).
2. **Generate L3 PNGs** — One folder for PNGs, Companion config, and (later) ATEM upload.
3. **Build Companion page** — Same folder as `--png-dir`; use `--csv` so button order = CSV row order. Config is written into that folder as `page6_l3.companionconfig` (use `--out` to override).
4. **Upload to ATEM** — Same PNGs into slots 40–55 in the same order.
5. **Import in Companion** — Import `page6_l3.companionconfig` from that folder.

```bash
# From the repo directory (activate venv first: source .venv/bin/activate)
python3 generate_lowerthirds.py --csv people.csv --out_dir output/
python3 companion_l3_page.py --template template_page6_l3.companionconfig --csv people.csv --png-dir output/
```

PNGs and `output/page6_l3.companionconfig` end up in `output/`. Replace `output/` with your path (e.g. `"/Users/tom/Documents/Lower 3rds/Output"`) if you use a different folder.

### Quick test guide: Companion

To test the Companion integration locally (scripts are in the repo but not committed to GitHub):

**1. Dependencies (once)**

```bash
source .venv/bin/activate   # or use system Python
pip install pyyaml pillow
```

**2. Template page**

The repo includes **`template_page6_l3.companionconfig`** (Companion page 6 “Lower 3rds” with 16 L3 slots plus BAIL, Bug Me, HOME). Use it as `--template`; the script only overwrites the 16 L3 positions and keeps the rest. To use your own layout, export a page from Companion that has one L3-style button (`mediaPlayerSource`), save it, and pass that file as `--template`.

**3. Generate a few L3 PNGs**

```bash
python3 generate_lowerthirds.py --csv example_people.csv --out_dir output/ --theme palette_teal
```

That fills `output/` with PNGs (e.g. `lowerthird_jane_smith_palette_teal.png`, …). Order in the Companion page will be **alphabetical by filename**.

**4. Build the Companion page**

```bash
python3 companion_l3_page.py --template template_page6_l3.companionconfig --png-dir output/
```

Output is `output/page6_l3.companionconfig` (same folder as the PNGs). The included template is `template_page6_l3.companionconfig` in the repo root.

**5. Import into Companion**

In Companion: **Settings → Import** (or paste/load the page). Load `output/page6_l3.companionconfig` and assign it to the target page (e.g. page 6). You should see up to 16 buttons with labels from the PNG names and thumbnail backgrounds; each button should trigger the corresponding media pool slot (40–55).

**6. Optional: inject thumbnails into an existing page (`companion_png64.py`)**

If you already have a Companion page with L3 buttons (row/column order fixed) and only want to refresh their thumbnails from a PNG folder:

```bash
python3 companion_png64.py path/to/your_page.companionconfig output/ --out path/to/your_page_with_previews.companionconfig
```

PNGs are assigned in **alphabetical order** to buttons that have a media pool source. Re-import the output file into Companion to see the new previews.

**Troubleshooting**

- **“Template page has no button with mediaPlayerSource”** — Export a page that has at least one button whose action is “set media pool still” (media player 1).
- **Wrong order of names on buttons** — Use `--csv` so button order matches your CSV row order (PNGs are matched by name). Without `--csv`, order is alphabetical by filename.
- **Buttons don’t fire the right still** — Media pool slots are 40–55 by default. Load the same PNGs into those slots on the ATEM (via Companion’s media pool UI or an upload tool) so indices match.

**Optional — ATEM media pool upload:**  
The script does **not** upload to the ATEM by default. Blackmagic doesn’t expose a simple REST API for still upload; options:

- **PyATEMAPI** ([GitHub](https://github.com/mackenly/PyATEMAPI)): run its server against your ATEM IP, then use its HTTP API to upload stills if supported.
- **atemlib MediaUpload** (e.g. `MediaUpload.exe [atem-ip] [slot] [filename]`): run this per PNG (e.g. in a small script loop) to push files into the media pool before or after generating the Companion page.

If you run an upload tool separately, use the same PNG order (CSV order if you used `--csv`, else alphabetical) and slots 40–55 so the Companion buttons stay in sync.

---

<sup>[1]</sup> [Faire Slack – Graphik](https://faire-wholesale.slack.com/archives/CC5448WAG/p1759868613384409)  
<sup>[2]</sup> [Faire Slack – Nantes](https://faire-wholesale.slack.com/archives/C07QYV5FQET/p1731709269836909)  
<sup>[3]</sup> [Faire iOS – UIFont+Faire](https://github.com/Faire/ios/blob/main/Modules/ViewCore/Sources/Extensions/UIFont+Faire.swift)  
<sup>[4]</sup> [Faire Slack – CDN fonts](https://faire-wholesale.slack.com/archives/C08H6DAB5TM/p1747315159424589) (Graphik on cdn.faire.com)
