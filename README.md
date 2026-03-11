# FaireL3s

**v0.0.6**

Generate Faire-style lower-third graphics (1920×1080 transparent PNGs) for video. Name + title on a light panel with accent bar. Use the **desktop app** or the CLI.

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
- **Pillow** (image generation) and **PyYAML** (Companion config). Install via a virtual environment (recommended on macOS/Homebrew).

### Setup (avoid “externally-managed-environment” on macOS)

On macOS, system Python is often managed by Homebrew and blocks `pip install` system-wide. Use a virtual environment:

```bash
cd "/path/to/l3rd script"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then run any script with the same shell (or activate `.venv` in new terminals):

```bash
python3 generate_lowerthirds.py --name "Your Name" --title "Your Title" --out output/test.png
```

To leave the virtual environment: `deactivate`.

### Run as app (web UI)

No Tk required. From the repo directory with the venv activated:

```bash
python3 app.py
```

Your browser will open to **http://127.0.0.1:5150**. The page lets you:

- **Style** — Choose a theme from the dropdown (same as the table above).
- **Input** — **Single**: enter Name and Title. **CSV file**: choose a file with `name,title` headers.
- **Generate Companion page** — Check to write `l3.companionconfig` into the output folder (batch/CSV only).
- **Output folder** — Click “Select output folder…” to open your system folder picker; the chosen path is used for PNGs and the optional Companion config.
- **Fetch fonts** — Download Graphik from the Faire CDN into `font/` (requires network/VPN).
- **Generate** — Runs the same logic as the CLI and shows a status message.

Single mode writes one PNG (e.g. `lowerthird_jane_smith.png` or `lowerthird_jane_smith_dark.png`). CSV mode writes one PNG per row and, if “Generate Companion page” is checked, also writes `l3.companionconfig` into the output folder.

### Building a standalone app (PyInstaller)

To build a double-clickable app so you don’t need Python or the venv installed:

```bash
pip install pyinstaller
pyinstaller l3rd_app.spec
```

The executable is created in `dist/FaireL3s` (or `dist/FaireL3s.exe` on Windows). Place a `font/` folder next to it (or use “Fetch fonts” from the GUI if the app can reach the Faire CDN). If you use the Companion feature, ensure `template_l3.companionconfig` is in the same directory as the spec when building so it is included in the bundle.

## Fonts (required for correct look)

Faire uses two core brand typefaces:

- **Graphik** (sans-serif) for most product UI and general readability.
- **Nantes** (serif) for “brand voice” moments (e.g. marketing).

This script uses **Graphik** for both the name and title lines (SemiBold/Medium for the name, Regular for the title). The iOS codebase bundles Graphik (Regular, Medium, SemiBold) and Nantes (Regular, SemiBold).

**This repo does not include font files.** Use one of the options below.

### Option A: Brand fonts (Graphik) — internal

Faire hosts Graphik on the CDN for internal use. You can pull the fonts automatically so the script uses the real brand typeface.

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

1. **Use the project venv** (recommended; see [Setup](#setup-avoid-externally-managed-environment-on-macos) if you need to create it and install dependencies):
   ```bash
   cd "/path/to/l3rd script"
   source .venv/bin/activate
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

**Deploy from CSV (default):** one command generates PNGs and the Companion page config into the same folder. Use this for events:

```bash
python3 generate_lowerthirds.py --csv people.csv --out_dir output/ --companion
```

Add `--theme palette_teal` (or another theme) if you want. Then upload the PNGs to ATEM slots 35–60 (up to 26; pool ends at 60) and import `output/l3.companionconfig` into Companion (assign to any page; references use expressions so it works wherever you import it).

**One lower third:**

```bash
python3 generate_lowerthirds.py --name "Jane Smith" --title "Chief Executive Officer" --out output/lowerthird_jane_smith.png
```

**Batch from CSV only (no Companion):**

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

### Pre-built page: up to 26 L3 buttons

**`companion_l3_page.py`** builds a Companion page with up to **26** L3 buttons. Layout: row 0 cols 1–8, row 1 cols 1–8, row 2 cols 1–7, row 3 cols 1–3 (fits Stream Deck Studio and 32-button with reference buttons). Media pool slots 35–60. The repo includes **`template_l3.companionconfig`** (“Lower 3rds” page with this grid plus BAIL, Bug Me, HOME, and reference buttons); the script overwrites only the L3 positions and keeps the rest. The generated config works on **any** Companion page when imported (button references use expressions).

- **Buttons:** Text = “L3” then the person’s name (no theme in label), top-left aligned; black background, white text. Image = L3 graphic cropped to content (no transparent margins), aligned bottom-left.
- **Order:** Use **`--csv`** so button order matches CSV row order (PNGs matched by name). Without `--csv`, order is alphabetical by filename.
- **Output:** The Companion config is written into the **same directory as the PNGs** by default as `l3.companionconfig`; use `--out` to override.

**Full workflow (CSV → PNGs → Companion page)**

Use the one-command deploy (see [Usage](#usage) above):

```bash
python3 generate_lowerthirds.py --csv people.csv --out_dir output/ --companion
```

That writes all PNGs and `l3.companionconfig` into the same folder. Upload the PNGs to ATEM slots 35–60 (same order, up to 26), then import the config into Companion and assign it to whichever page you want.

**Two steps (optional):** if you prefer to run the generator and Companion script separately:

```bash
python3 generate_lowerthirds.py --csv people.csv --out_dir output/
python3 companion_l3_page.py --template template_l3.companionconfig --csv people.csv --png-dir output/
```

### Quick test guide: Companion

To test the Companion integration locally (scripts are in the repo but not committed to GitHub):

**1. Dependencies (once)** — create and activate a venv, then install (see [Setup](#setup-avoid-externally-managed-environment-on-macos)):

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Template page**

The repo includes **`template_l3.companionconfig`** (“Lower 3rds” page with 26 L3 positions plus BAIL, Bug Me, HOME, and reference buttons). Use it as `--template`; the script only overwrites the L3 positions and keeps the rest. To use your own layout, export a page from Companion that has one L3-style button (`mediaPlayerSource`), save it, and pass that file as `--template`.

**3. Generate a few L3 PNGs**

```bash
python3 generate_lowerthirds.py --csv example_people.csv --out_dir output/ --theme palette_teal
```

That fills `output/` with PNGs (e.g. `lowerthird_jane_smith_palette_teal.png`, …). Order in the Companion page will be **alphabetical by filename**.

**4. Build the Companion page**

```bash
python3 companion_l3_page.py --template template_l3.companionconfig --png-dir output/
```

Output is `output/l3.companionconfig` (same folder as the PNGs). The included template is `template_l3.companionconfig` in the repo root.

**5. Import into Companion**

In Companion: **Settings → Import** (or paste/load the page). Load `output/l3.companionconfig` and assign it to whichever page you want. The config uses expressions for button references, so it works on any page. You should see up to 26 buttons with labels from the PNG names and thumbnail backgrounds; each button triggers the corresponding media pool slot (35–60).

**6. Optional: inject thumbnails into an existing page (`companion_png64.py`)**

If you already have a Companion page with L3 buttons (row/column order fixed) and only want to refresh their thumbnails from a PNG folder:

```bash
python3 companion_png64.py path/to/your_page.companionconfig output/ --out path/to/your_page_with_previews.companionconfig
```

PNGs are assigned in **alphabetical order** to buttons that have a media pool source. Re-import the output file into Companion to see the new previews.

**Troubleshooting**

- **“Template page has no button with mediaPlayerSource”** — Export a page that has at least one button whose action is “set media pool still” (media player 1).
- **Wrong order of names on buttons** — Use `--csv` so button order matches your CSV row order (PNGs are matched by name). Without `--csv`, order is alphabetical by filename.
- **Buttons don’t fire the right still** — Media pool slots are 35–60 (26 slots; pool ends at 60). Load the same PNGs into those slots on the ATEM in the same order so indices match.

**Optional — ATEM media pool upload:**  
The script does **not** upload to the ATEM by default. Blackmagic doesn’t expose a simple REST API for still upload; options:

- **PyATEMAPI** ([GitHub](https://github.com/mackenly/PyATEMAPI)): run its server against your ATEM IP, then use its HTTP API to upload stills if supported.
- **atemlib MediaUpload** (e.g. `MediaUpload.exe [atem-ip] [slot] [filename]`): run this per PNG (e.g. in a small script loop) to push files into the media pool before or after generating the Companion page.

If you run an upload tool separately, use the same PNG order (CSV order if you used `--csv`, else alphabetical) and slots 35–60 so the Companion buttons stay in sync.
