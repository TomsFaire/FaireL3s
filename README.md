# FaireL3s

Generate Faire-style lower-third graphics (1920×1080 transparent PNGs) for video. Name + title on a light panel with accent bar.

## Requirements

- Python 3.9+
- [Pillow](https://pypi.org/project/Pillow/) (`pip install pillow`)

## Fonts (recommended)

Place Inter in a `font/` or `fonts/` folder next to the script:

- **Name line (bold):** `Inter-SemiBold.ttf` or `Inter-Bold.ttf`
- **Title line:** `Inter-Regular.ttf`

Download Inter from [Google Fonts](https://fonts.google.com/specimen/Inter) or [rsms.me/inter](https://rsms.me/inter/).  
If the script doesn’t find these files, it falls back to system fonts (e.g. Arial) so output is still readable.

## Usage

**One lower third:**

```bash
python generate_lowerthirds.py --name "Jane Smith" --title "Chief Executive Officer, Faire" --out output/lowerthird_jane_smith.png
```

**Batch from CSV:**

```bash
python generate_lowerthirds.py --csv example_people.csv --out_dir output/
```

CSV format: header row `name,title`, then one row per person. Use quotes for titles that contain commas.

```csv
name,title
Jane Smith,"Chief Executive Officer, Faire"
Alex Chen,"Chief Technology Officer, Faire"
```

## Customization

Edit `style.json` to change layout and colors: panel size, margins, text sizes, accent bar, etc.

## Output

- **Size:** 1920×1080  
- **Format:** PNG with transparency  
- **Layout:** Lower-left panel, name (semi-bold) above title (regular)
