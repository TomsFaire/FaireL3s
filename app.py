#!/usr/bin/env python3
"""FaireL3s web app: generate lower thirds from a browser (style, single/CSV, output dir, Companion, Fetch fonts)."""
from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

# When not frozen, ensure generator is importable from this directory
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_lowerthirds as gen
from flask import Flask, request, render_template_string, jsonify

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB for CSV uploads

THEME_LABELS = {
    "default": "Default (light warm)",
    "dark": "Dark",
    "dark_alt": "Dark alt",
    "bright": "Bright (sage)",
    "bright_insider": "Bright Insider (teal)",
    "bright_warm": "Bright Warm (amber)",
    "bright_info": "Bright Info (slate)",
    "palette_olive": "Palette Olive",
    "palette_teal": "Palette Teal",
    "palette_terracotta": "Palette Terracotta",
    "palette_plum": "Palette Plum",
    "palette_copper": "Palette Copper",
    "palette_sage": "Palette Sage",
}

THEME_KEYS = list(gen.THEME_FILES)

CSV_ROW_LIMIT = 500


def _theme_swatches() -> list[dict]:
    """Load each theme's panel and accent colors for the swatch grid."""
    swatches = []
    for key in THEME_KEYS:
        try:
            style = gen.load_style(key)
            fill = style["panel"]["fill_rgba"]
            accent = style["accent_bar"]["rgb"]
            swatches.append({
                "key": key,
                "label": THEME_LABELS.get(key, key),
                "panel_rgb": f"rgb({fill[0]},{fill[1]},{fill[2]})",
                "accent_rgb": f"rgb({accent[0]},{accent[1]},{accent[2]})",
            })
        except Exception:
            swatches.append({"key": key, "label": THEME_LABELS.get(key, key), "panel_rgb": "#fff", "accent_rgb": "#999"})
    return swatches


def _pick_folder_native() -> str | None:
    """Open the OS folder picker; return the chosen path or None. No Tk required."""
    system = platform.system()
    try:
        if system == "Darwin":
            out = subprocess.run(
                ["osascript", "-e", "return POSIX path of (choose folder)"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if out.returncode != 0:
                return None
            return out.stdout.strip() or None
        if system == "Linux":
            out = subprocess.run(
                ["zenity", "--file-selection", "--directory", "--title=Select output folder"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if out.returncode != 0:
                return None
            return out.stdout.strip() or None
        if system == "Windows":
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "if ($f.ShowDialog() -eq 'OK') { $f.SelectedPath }"
            )
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if out.returncode != 0:
                return None
            return out.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug("Folder picker failed: %s", e)
        return None
    except subprocess.SubprocessError as e:
        logger.debug("Folder picker subprocess error: %s", e)
        return None
    return None


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Faire Lower 3rds {{ version }}</title>
  <style>
    :root {
      --bg: #f7f5f2;
      --card: #fff;
      --text: #2c2c2c;
      --text-muted: #6b6b6b;
      --accent: #8b7355;
      --accent-hover: #7a6449;
      --border: #e5e2de;
      --input-bg: #faf9f7;
      --success: #3d6b4f;
      --error: #9e4a3a;
      --radius: 8px;
      --shadow: 0 2px 12px rgba(0,0,0,0.06);
    }

    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      margin: 0;
      min-height: 100vh;
      padding: 2rem 1rem;
    }

    .container {
      max-width: 520px;
      margin: 0 auto;
    }

    .card {
      background: var(--card);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 2rem;
      margin-bottom: 1.5rem;
    }

    .header {
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
      margin-bottom: 1.75rem;
      padding-bottom: 1rem;
      border-bottom: 4px solid var(--accent);
    }
    .header h1 { margin: 0; font-size: 1.5rem; font-weight: 600; letter-spacing: -0.02em; }
    .version { font-size: 0.8rem; color: var(--text-muted); font-weight: 400; }

    .field { margin-bottom: 1.25rem; }
    .field:last-of-type { margin-bottom: 0; }
    .field label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
      margin-bottom: 0.4rem;
    }

    input[type="text"],
    input[type="file"],
    select {
      width: 100%;
      padding: 0.65rem 0.85rem;
      font-size: 0.95rem;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--input-bg);
      color: var(--text);
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    input:focus, select:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(139,115,85,0.15); }
    input[type="file"] { padding: 0.5rem; cursor: pointer; }
    input[type="file"]::file-selector-button {
      padding: 0.4rem 0.75rem;
      margin-right: 0.75rem;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: var(--card);
      font-size: 0.85rem;
      cursor: pointer;
    }

    .radio-group {
      display: flex;
      gap: 1.5rem;
      padding: 0.5rem 0;
    }
    .radio-group label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      font-size: 0.95rem;
      font-weight: 500;
      text-transform: none;
      letter-spacing: 0;
      color: var(--text);
    }
    .radio-group input[type="radio"] { width: auto; accent-color: var(--accent); }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      cursor: pointer;
      font-size: 0.9rem;
      font-weight: 500;
      color: var(--text);
    }
    .checkbox-label input { width: auto; accent-color: var(--accent); }

    .btn {
      display: inline-flex;
      align-items: center;
      padding: 0.6rem 1.1rem;
      font-size: 0.9rem;
      font-weight: 600;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: background 0.15s, transform 0.05s;
    }
    .btn:active { transform: scale(0.98); }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }
    .btn-secondary {
      background: var(--input-bg);
      color: var(--text);
      border: 1px solid var(--border);
    }
    .btn-secondary:hover:not(:disabled) { background: var(--border); }
    .btn-primary {
      background: var(--accent);
      color: #fff;
    }
    .btn-primary:hover:not(:disabled) { background: var(--accent-hover); }

    .btn-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }
    .btn-row .muted { font-size: 0.85rem; color: var(--text-muted); }

    #status {
      margin-top: 1.25rem;
      padding: 0.85rem 1rem;
      border-radius: 6px;
      font-size: 0.9rem;
      min-height: 2.5rem;
      line-height: 1.4;
    }
    #status:empty { display: none; }
    #status.ok { background: rgba(61,107,79,0.12); color: var(--success); }
    #status.error { background: rgba(158,74,58,0.12); color: var(--error); }
    #status:not(.ok):not(.error) { background: var(--input-bg); color: var(--text-muted); }

    .swatch-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 0.6rem;
      margin-bottom: 1.5rem;
    }
    .swatch {
      cursor: pointer;
      border-radius: 6px;
      overflow: hidden;
      border: 2px solid transparent;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .swatch:hover { border-color: var(--border); box-shadow: var(--shadow); }
    .swatch.selected { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(139,115,85,0.3); }
    .swatch-preview {
      height: 36px;
      display: flex;
    }
    .swatch-accent {
      width: 6px;
      flex-shrink: 0;
    }
    .swatch-panel {
      flex: 1;
      min-width: 0;
    }
    .swatch-name {
      font-size: 0.68rem;
      font-weight: 600;
      padding: 0.35rem 0.4rem;
      background: var(--card);
      color: var(--text);
      text-align: center;
      line-height: 1.2;
      word-break: break-word;
    }

    #csvRow { display: none; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <header class="header">
        <h1>Faire Lower 3rds</h1>
        <span class="version">v{{ version }}</span>
      </header>

      <div class="swatch-grid" id="swatchGrid">
        {% for s in swatches %}
        <div class="swatch {% if s.key == 'default' %}selected{% endif %}" data-theme="{{ s.key }}" title="{{ s.label }}">
          <div class="swatch-preview">
            <div class="swatch-accent" style="background: {{ s.accent_rgb }}"></div>
            <div class="swatch-panel" style="background: {{ s.panel_rgb }}"></div>
          </div>
          <div class="swatch-name">{{ s.label }}</div>
        </div>
        {% endfor %}
      </div>

      <form id="form">
        <input type="hidden" name="theme" id="theme" value="default">

        <div class="field">
          <label>Input</label>
          <div class="radio-group">
            <label><input type="radio" name="mode" value="single" checked> Single</label>
            <label><input type="radio" name="mode" value="csv"> CSV file</label>
          </div>
        </div>

        <div id="singleRow">
          <div class="field">
            <label>Name</label>
            <input type="text" name="name" id="name" placeholder="Jane Smith">
          </div>
          <div class="field">
            <label>Title</label>
            <input type="text" name="title" id="title" placeholder="Chief Executive Officer">
          </div>
        </div>

        <div id="csvRow">
          <div class="field">
            <label>CSV file</label>
            <input type="file" name="csv_file" id="csvFile" accept=".csv">
          </div>
        </div>

        <div class="field">
          <label class="checkbox-label">
            <input type="checkbox" name="companion" id="companion">
            Generate Companion page (batch/CSV only)
          </label>
        </div>

        <div class="field">
          <label>Media pool start slot</label>
          <input type="number" name="media_start" id="mediaStart" value="35" min="1" max="60" style="width:100px;">
        </div>

        <div class="field">
          <label>ATEM IP (optional — direct media pool upload)</label>
          <div class="btn-row">
            <input type="text" name="atem_ip" id="atemIp" placeholder="192.168.1.240" style="flex:1;">
            <button type="button" class="btn btn-secondary" id="uploadAtemBtn" title="Upload generated PNGs to ATEM media pool">Upload to ATEM</button>
          </div>
          <p class="muted" style="margin-top:0.35rem; font-size:0.85rem;">Generate L3 images first (button below). This uploads those PNGs to the ATEM. With CSV mode, if you enter an ATEM IP and click Generate, it will generate and upload in one step.</p>
        </div>

        <div class="field">
          <label>Output folder</label>
          <div class="btn-row">
            <button type="button" class="btn btn-secondary" id="pickOutputDir">Select folder...</button>
            <span class="muted" id="outputDirLabel">No folder chosen</span>
          </div>
          <input type="hidden" name="output_dir" id="outputDir">
        </div>

        <div class="field">
          <div class="btn-row">
            <button type="button" class="btn btn-secondary" id="fetchFonts">Fetch fonts</button>
            <span class="muted" id="fontStatus">Graphik from Faire CDN</span>
          </div>
        </div>

        <div class="field" style="margin-top: 1.5rem;">
          <button type="submit" class="btn btn-primary" id="generateBtn">Generate</button>
        </div>
      </form>

      <div id="status"></div>
    </div>

    <div style="text-align: center; margin-top: 0.5rem;">
      <button type="button" class="btn btn-secondary" id="quitBtn" style="font-size: 0.8rem; padding: 0.4rem 0.9rem; color: var(--text-muted);">Quit app</button>
    </div>
  </div>

  <script>
    const modeSingle = document.querySelector('input[name="mode"][value="single"]');
    const modeCsv = document.querySelector('input[name="mode"][value="csv"]');
    const singleRow = document.getElementById('singleRow');
    const csvRow = document.getElementById('csvRow');
    const companion = document.getElementById('companion');

    function setMode() {
      const isCsv = modeCsv.checked;
      singleRow.style.display = isCsv ? 'none' : 'block';
      csvRow.style.display = isCsv ? 'block' : 'none';
      companion.disabled = !isCsv;
    }
    modeSingle.addEventListener('change', setMode);
    modeCsv.addEventListener('change', setMode);
    setMode();

    document.getElementById('swatchGrid').addEventListener('click', (e) => {
      const swatch = e.target.closest('.swatch');
      if (!swatch) return;
      document.getElementById('theme').value = swatch.dataset.theme;
      document.querySelectorAll('.swatch').forEach(s => s.classList.remove('selected'));
      swatch.classList.add('selected');
    });
    document.getElementById('pickOutputDir').addEventListener('click', async () => {
      try {
        const r = await fetch('/pick-output-dir', { method: 'POST' });
        const j = await r.json();
        if (j.ok && j.path) {
          document.getElementById('outputDir').value = j.path;
          document.getElementById('outputDirLabel').textContent = j.path;
          document.getElementById('outputDirLabel').classList.remove('muted');
        } else {
          document.getElementById('outputDirLabel').textContent = j.message || 'No folder chosen';
          document.getElementById('outputDirLabel').classList.add('muted');
        }
      } catch (e) {
        document.getElementById('outputDirLabel').textContent = 'Error: ' + e.message;
        document.getElementById('outputDirLabel').classList.add('muted');
      }
    });

    document.getElementById('fetchFonts').addEventListener('click', async () => {
      document.getElementById('fontStatus').textContent = 'Fetching...';
      try {
        const r = await fetch('/fetch-fonts', { method: 'POST' });
        const j = await r.json();
        document.getElementById('fontStatus').textContent = j.message || (j.ok ? 'Fonts saved.' : 'Fetch failed.');
      } catch (e) {
        document.getElementById('fontStatus').textContent = 'Error: ' + e.message;
      }
    });

    const statusEl = document.getElementById('status');
    function setStatus(msg, state) {
      statusEl.textContent = msg;
      statusEl.className = state || '';
    }

    document.getElementById('form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const theme = document.getElementById('theme').value;
      const outputDir = document.getElementById('outputDir').value.trim();
      if (!outputDir) {
        setStatus('Please select an output folder.', 'error');
        return;
      }

      const isCsv = modeCsv.checked;
      const formData = new FormData();
      formData.set('theme', theme);
      formData.set('output_dir', outputDir);
      formData.set('companion', isCsv && companion.checked ? '1' : '0');
      formData.set('media_start', document.getElementById('mediaStart').value || '35');
      const atemIpVal = document.getElementById('atemIp').value.trim();
      if (atemIpVal) formData.set('atem_ip', atemIpVal);

      if (isCsv) {
        const file = document.getElementById('csvFile').files[0];
        if (!file) {
          setStatus('Please choose a CSV file.', 'error');
          return;
        }
        formData.set('csv_file', file);
      } else {
        const name = document.getElementById('name').value.trim();
        const title = document.getElementById('title').value.trim();
        if (!name || !title) {
          setStatus('Please enter name and title.', 'error');
          return;
        }
        formData.set('name', name);
        formData.set('title', title);
      }

      setStatus('Generating...', 'pending');
      document.getElementById('generateBtn').disabled = true;
      try {
        const r = await fetch('/generate', { method: 'POST', body: formData });
        const j = await r.json();
        setStatus(j.message || (j.ok ? 'Done.' : 'Error'), j.ok ? 'ok' : 'error');
      } catch (err) {
        setStatus('Error: ' + err.message, 'error');
      }
      document.getElementById('generateBtn').disabled = false;
    });

    document.getElementById('uploadAtemBtn').addEventListener('click', async () => {
      const atemIp = document.getElementById('atemIp').value.trim();
      const outputDir = document.getElementById('outputDir').value.trim();
      if (!atemIp) {
        setStatus('Please enter the ATEM IP address.', 'error');
        return;
      }
      if (!outputDir) {
        setStatus('Please select an output folder with generated PNGs first.', 'error');
        return;
      }
      document.getElementById('uploadAtemBtn').disabled = true;
      setStatus('Checking ATEM connection...', 'pending');
      try {
        const checkRes = await fetch('/check-atem', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ atem_ip: atemIp }),
        });
        const checkJson = await checkRes.json();
        if (!checkJson.ok) {
          setStatus(checkJson.message || 'ATEM not reachable.', 'error');
          document.getElementById('uploadAtemBtn').disabled = false;
          return;
        }
        setStatus('Uploading to ATEM...', 'pending');
        const mediaStart = parseInt(document.getElementById('mediaStart').value) || 35;
        const r = await fetch('/upload-atem', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ atem_ip: atemIp, output_dir: outputDir, media_start: mediaStart }),
        });
        const j = await r.json();
        setStatus(j.message || (j.ok ? 'Upload complete.' : 'Upload failed.'), j.ok ? 'ok' : 'error');
      } catch (err) {
        setStatus('Error: ' + err.message, 'error');
      }
      document.getElementById('uploadAtemBtn').disabled = false;
    });

    document.getElementById('quitBtn').addEventListener('click', async () => {
      if (!confirm('Quit Faire Lower 3rds?')) return;
      try { await fetch('/quit', { method: 'POST' }); } catch (e) {}
      document.body.innerHTML = '<p style="text-align:center;margin-top:4rem;font-family:system-ui;color:#6b6b6b;">App stopped. You can close this tab.</p>';
    });
  </script>
</body>
</html>
"""


@app.route("/")
def index() -> str:
    return render_template_string(
        HTML,
        version=gen.__version__,
        theme_keys=THEME_KEYS,
        theme_labels=THEME_LABELS,
        swatches=_theme_swatches(),
    )


@app.route("/pick-output-dir", methods=["POST"])
def pick_output_dir() -> tuple[dict, int]:
    """Run the OS folder picker and return the chosen path. Used by the 'Select output folder' button."""
    path = _pick_folder_native()
    if path:
        return jsonify({"ok": True, "path": path}), 200
    return jsonify({"ok": False, "message": "No folder chosen or picker not available."}), 200


@app.route("/fetch-fonts", methods=["POST"])
def fetch_fonts() -> tuple[dict, int]:
    try:
        d = gen.fetch_faire_fonts()
        return jsonify({"ok": True, "message": f"Fonts saved to {d}"}), 200
    except OSError as e:
        logger.debug("Font fetch I/O error: %s", e)
        return jsonify({"ok": False, "message": str(e)}), 500
    except Exception as e:
        logger.debug("Font fetch error: %s", e)
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/generate", methods=["POST"])
def generate() -> tuple[dict, int]:
    theme = (request.form.get("theme") or "default").strip()
    if theme not in gen.THEME_FILES:
        return jsonify({"ok": False, "message": f"Unknown theme: {theme}"}), 400

    output_dir = (request.form.get("output_dir") or "").strip()
    if not output_dir:
        return jsonify({"ok": False, "message": "Output folder is required."}), 400

    out_path = Path(output_dir)
    try:
        out_path = out_path.resolve()
    except Exception as e:
        return jsonify({"ok": False, "message": f"Invalid output path: {e}"}), 400

    csv_mode = request.files.get("csv_file") is not None and request.files.get("csv_file").filename
    write_companion = request.form.get("companion") == "1"
    atem_ip = (request.form.get("atem_ip") or "").strip() or None
    try:
        media_start = int(request.form.get("media_start") or 35)
    except (ValueError, TypeError):
        media_start = 35

    if csv_mode:
        f = request.files["csv_file"]
        if not f or not f.filename:
            return jsonify({"ok": False, "message": "Please upload a CSV file."}), 400

        # Read the uploaded data so we can validate before writing to disk
        csv_data = f.read()
        if not csv_data.strip():
            return jsonify({"ok": False, "message": "The uploaded CSV file is empty."}), 400

        # Validate CSV structure: check required columns and row limit
        import csv as csv_module
        import io
        try:
            text = csv_data.decode("utf-8-sig")
        except (UnicodeDecodeError, ValueError) as e:
            return jsonify({"ok": False, "message": f"CSV encoding error: {e}"}), 400

        try:
            reader = csv_module.DictReader(io.StringIO(text))
            fieldnames = reader.fieldnames
            if not fieldnames:
                return jsonify({"ok": False, "message": "CSV has no header row."}), 400
            missing = [col for col in ("name", "title") if col not in fieldnames]
            if missing:
                return jsonify({
                    "ok": False,
                    "message": f"CSV is missing required column(s): {', '.join(missing)}. Found: {list(fieldnames)}",
                }), 400
            rows = list(reader)
        except csv_module.Error as e:
            return jsonify({"ok": False, "message": f"Could not parse CSV: {e}"}), 400

        if len(rows) > CSV_ROW_LIMIT:
            return jsonify({
                "ok": False,
                "message": f"CSV has {len(rows)} rows; maximum allowed is {CSV_ROW_LIMIT}.",
            }), 400

        # Save uploaded file to a temp path; run_batch expects a path
        import tempfile
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
            tmp.write(csv_data)
            tmp_path = Path(tmp.name)
        try:
            count = gen.run_batch(
                tmp_path,
                out_path,
                theme,
                media_start=media_start,
                write_companion=write_companion,
                atem_ip=atem_ip,
            )
            msg = f"Saved {count} PNGs to {out_path}"
            if write_companion:
                msg += ". Companion config written."
            return jsonify({"ok": True, "message": msg}), 200
        except (FileNotFoundError, OSError) as e:
            logger.debug("Batch generation I/O error: %s", e)
            return jsonify({"ok": False, "message": f"File error: {e}"}), 500
        except ValueError as e:
            logger.debug("Batch generation value error: %s", e)
            return jsonify({"ok": False, "message": str(e)}), 400
        except Exception as e:
            logger.debug("Batch generation error: %s", e)
            return jsonify({"ok": False, "message": str(e)}), 500
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        name = (request.form.get("name") or "").strip()
        title = (request.form.get("title") or "").strip()
        if not name or not title:
            return jsonify({"ok": False, "message": "Name and title are required."}), 400
        try:
            style = gen.load_style(theme)
            base = f"lowerthird_{gen.slugify(name)}"
            if theme != "default":
                base = f"{base}_{theme}"
            out_file = out_path / f"{base}.png"
            out_path.mkdir(parents=True, exist_ok=True)
            gen.render_lowerthird(name, title, out_file, style)
            return jsonify({"ok": True, "message": f"Saved: {out_file}"}), 200
        except (FileNotFoundError, OSError) as e:
            logger.debug("Single generation I/O error: %s", e)
            return jsonify({"ok": False, "message": f"File error: {e}"}), 500
        except Exception as e:
            logger.debug("Single generation error: %s", e)
            return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/check-atem", methods=["POST"])
def check_atem() -> tuple[dict, int]:
    """Verify ATEM is reachable at the given IP before attempting uploads."""
    data = request.get_json(silent=True) or {}
    atem_ip = (data.get("atem_ip") or "").strip()
    if not atem_ip:
        return jsonify({"ok": False, "message": "ATEM IP address is required."}), 400
    import companion_l3_page as clp
    result = clp.check_atem_connection(atem_ip)
    status_code = 200 if result["ok"] else 503
    return jsonify(result), status_code


@app.route("/upload-atem", methods=["POST"])
def upload_atem() -> tuple[dict, int]:
    """Upload previously generated PNGs from output_dir to ATEM media pool."""
    data = request.get_json(silent=True) or {}
    atem_ip = (data.get("atem_ip") or "").strip()
    output_dir = (data.get("output_dir") or "").strip()

    if not atem_ip:
        return jsonify({"ok": False, "message": "ATEM IP address is required."}), 400
    if not output_dir:
        return jsonify({"ok": False, "message": "Output directory is required."}), 400

    out_path = Path(output_dir).resolve()
    if not out_path.is_dir():
        return jsonify({"ok": False, "message": f"Directory not found: {out_path}"}), 400

    png_paths = sorted(out_path.glob("*.png"))
    if not png_paths:
        return jsonify({"ok": False, "message": f"No PNGs found in {out_path}"}), 400

    try:
        media_start = int(data.get("media_start") or 35)
    except (ValueError, TypeError):
        media_start = 35

    import companion_l3_page as clp
    labels = [clp.filename_to_display_name(p.name) for p in png_paths]
    result = clp.upload_to_atem(png_paths, atem_ip, media_start=media_start, labels=labels)
    status_code = 200 if result["ok"] else 500
    return jsonify(result), status_code


@app.route("/quit", methods=["POST"])
def quit_app() -> tuple[dict, int]:
    """Shut down the Flask server and exit. Response is sent first, then process exits."""
    def _exit_after_response() -> None:
        time.sleep(0.3)  # let the response reach the client
        os._exit(0)

    threading.Thread(target=_exit_after_response, daemon=True).start()
    return jsonify({"ok": True}), 200


def _log_crash(exc: BaseException) -> None:
    """Write traceback to a log file so we can diagnose when the .app crashes on launch."""
    try:
        log_dir = Path(os.path.expanduser("~/Library/Logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "FaireL3s-crash.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n---\n")
            traceback.print_exc(file=f)
        print(f"FaireL3s crashed. See {log_file}", file=sys.stderr)
    except Exception:
        traceback.print_exc(file=sys.stderr)


def _wait_and_open_browser(url: str, timeout: float = 10.0) -> None:
    """Poll until the server is ready, then open the browser."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.1)


def _wait_and_signal_ready(url: str, port: int, timeout: float = 10.0) -> None:
    """Poll until the server is ready, then print a JSON ready signal to stdout."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5)
            print(json.dumps({"ready": True, "port": port}), flush=True)
            return
        except Exception:
            time.sleep(0.1)


def main() -> None:
    parser = argparse.ArgumentParser(description="FaireL3s lower-thirds generator")
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Start headless (don't open a browser window)",
    )
    args = parser.parse_args()

    # When frozen (.app), run with bundle as cwd so resource paths resolve
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys.executable).resolve().parent
        os.chdir(bundle_dir)

    port = 5150
    url = f"http://127.0.0.1:{port}"

    if args.no_browser:
        threading.Thread(target=_wait_and_signal_ready, args=(url, port), daemon=True).start()
    else:
        threading.Thread(target=_wait_and_open_browser, args=(url,), daemon=True).start()
    print(f"FaireL3s {gen.__version__} -- open {url}", file=sys.stderr)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _log_crash(e)
        raise
