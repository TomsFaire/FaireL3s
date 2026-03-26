# Faire Lower 3rds

**v0.0.6**

Generate Faire-style lower-third graphics (1920×1080 transparent PNGs) for video: name and title on a panel with accent bar.

## How to run the app

**Option A — Mac .app (easiest)**  
Download **FaireL3s-macOS.zip** from the [latest release](https://github.com/TomsFaire/FaireL3s/releases). Unzip, then open **Faire Lower 3rds.app** (double-click or right-click → Open). Your browser opens to the app. Put a `font/` folder next to the app if you have Graphik (or use “Fetch fonts” in the app when on Faire network).  

If macOS says the app is **“damaged”** or won’t open: right-click the app → **Open** (and confirm), or in Terminal run:  
`xattr -cr "/path/to/Faire Lower 3rds.app"`

If the app doesn’t start (no browser, nothing in Activity Monitor): run it from Terminal to see the error:  
`"/path/to/Faire Lower 3rds.app/Contents/MacOS/FaireL3s"`  
Any crash after launch is also written to `~/Library/Logs/FaireL3s-crash.log`.

**Option B — From source (web app)**  
Clone the repo, then (use Python 3.9–3.13; 3.14 can have venv issues):

```bash
cd "/path/to/l3rd script"
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

If you don’t have `python3.13`, use `python3.12` or `python3` in the venv command. If your default `python3` is 3.14 and venv fails, create the venv with an explicit 3.13:  
`python3.13 -m venv .venv313 && source .venv313/bin/activate` then `pip install -r requirements.txt` and `python app.py`.

Your browser opens at http://127.0.0.1:5150.

## Using the app

- **Style** — Click a color swatch (Default, Dark, Bright, or any palette theme).
- **Single or CSV** — Enter one name and title, or upload a CSV with `name,title` columns.
- **Output folder** — Click “Select output folder…” and choose where to save PNGs.
- **Fetch fonts** — Downloads Graphik from Faire’s CDN into `font/` (needs Faire network/VPN). Do this once; the repo doesn’t include fonts.
- **Generate Companion page** — For CSV batch, check this to write `l3.companionconfig` into the output folder.
- **Generate** — Creates the PNGs (and Companion config if checked).

Single mode saves one file (e.g. `lowerthird_jane_smith.png`). CSV mode saves one PNG per row; with “Generate Companion page” checked, it also writes `l3.companionconfig` for Bitfocus Companion.

## Styles

The app shows a grid of style swatches. All layouts are the same; only colors change. Theme names for CLI use: `default`, `dark`, `dark_alt`, `bright`, `bright_insider`, `bright_warm`, `bright_info`, `palette_olive`, `palette_teal`, `palette_terracotta`, `palette_plum`, `palette_copper`, `palette_sage`. Sample images are in `output/example_*.png`.

## Fonts

The app uses **Graphik** for name and title. Use “Fetch fonts” in the app, or put Graphik (or [Inter](https://fonts.google.com/specimen/Inter)) in `font/` or `fonts/` next to the app or repo (e.g. `Graphik-Regular.otf`, `Graphik-Medium.otf`, `Graphik-SemiBold.otf`).

## Bitfocus Companion

For CSV batch, check “Generate Companion page” to write `l3.companionconfig` into the output folder. The page has up to 26 L3 buttons (media pool slots 35–60). Import the config into Companion and upload the same PNGs to ATEM slots 35–60 in the same order. You need `template_l3.companionconfig` in the repo (or next to the .app) for this to work. Button order follows your CSV order when you use a CSV.

To add thumbnails to an existing Companion page: `python3 companion_png64.py path/to/page.companionconfig path/to/l3/png/folder --out path/to/output.companionconfig`

## Command line

For scripts or automation:

```bash
# Single
python3 generate_lowerthirds.py --name "Jane Smith" --title "Chief Executive Officer" --out output/jane.png

# Batch + Companion
python3 generate_lowerthirds.py --csv people.csv --out_dir output/ --theme palette_teal --companion
```

CSV format: header `name,title`, one row per person. Use `--theme` with any style name from the list above.

## Output

1920×1080 PNG with transparency; lower-left panel, name (semi-bold) above title (regular). To change layout or colors, edit `style.json` (or `style_dark.json`, `style_palette_teal.json`, etc.).

## Requirements (when running from source)

Python 3.9+, Pillow, PyYAML, Flask. Install with `pip install -r requirements.txt` (use a venv on macOS/Homebrew).
