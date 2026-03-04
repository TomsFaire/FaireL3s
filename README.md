# FaireL3s

**v0.0.2**

Generate Faire-style lower-third graphics (1920×1080 transparent PNGs) for video. Name + title on a light panel with accent bar.

## Requirements

- Python 3.9+
- [Pillow](https://pypi.org/project/Pillow/) (`pip install pillow`)

## Fonts (required for correct look)

**This repo does not include font files.** You must add Inter yourself; without it the script uses a system fallback and the lower thirds will not match the intended style.

### Easiest: unzip Google Fonts into an `Inter` folder

1. Download **[Inter from Google Fonts](https://fonts.google.com/specimen/Inter)** → click “Download family”.
2. Unzip the archive.
3. Rename the unzipped folder to **`Inter`** (if it isn’t already) and move it into this repo so it sits next to `generate_lowerthirds.py`.

Resulting layout (Google Fonts zip has a `static/` subfolder with the fonts):

```
FaireL3s/
  Inter/
    static/
      Inter_18pt-SemiBold.ttf
      Inter_18pt-Regular.ttf
      ... (other weights)
    OFL.txt
    ...
  generate_lowerthirds.py
  style.json
  ...
```

The script looks in `Inter/` and `Inter/static/` for the font files. No need to copy or rename individual files.

### Alternative: use `font/` or `fonts/`

If you prefer, put only the two needed files in a folder named **`font/`** or **`fonts/`** next to the script:

- Name line (bold): `Inter-SemiBold.ttf` or `Inter-Bold.ttf`
- Title line: `Inter-Regular.ttf`

### Verify

Run a single lower third. If the name is bold and the title is regular in Inter, fonts are set up correctly:

```bash
python3 generate_lowerthirds.py --name "Your Name" --title "Your Title" --out output/test.png
```

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

## Customization

Edit `style.json` to change layout and colors: panel size, margins, text sizes, accent bar, etc.

## Output

- **Size:** 1920×1080  
- **Format:** PNG with transparency  
- **Layout:** Lower-left panel, name (semi-bold) above title (regular)
