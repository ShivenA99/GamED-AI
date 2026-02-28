#!/usr/bin/env python3
"""
Zone Detection Method Comparison Test

Compares zone detection approaches on educational diagrams and generates
visual overlays + an inline HTML comparison viewer.

Methods tested:
  1. Gemini Text (gemini-2.5-flash) — text polygon estimation
  2. Gemini Text (gemini-2.5-pro) — text polygon estimation (stronger model)
  3. Gemini Mask (gemini-2.5-flash-image) — native segmentation masks
  4. SAM3 text-only — text prompt per label (no spatial guidance)
  5. Gemini → SAM3 guided — Gemini provides boxes, SAM3 segments precisely

Usage:
    cd backend && source venv/bin/activate
    PYTHONPATH=. python scripts/test_zone_detection.py
    PYTHONPATH=. python scripts/test_zone_detection.py --image /path/to/diagram.png
    PYTHONPATH=. python scripts/test_zone_detection.py --generate
    PYTHONPATH=. python scripts/test_zone_detection.py --skip-sam3  # skip slow SAM3 methods
"""

import argparse
import asyncio
import base64
import json
import logging
import math
import os
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_zone_compare")

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BACKEND_ROOT / "test_outputs"

DEFAULT_SUBJECT = "animal cell anatomy"
DEFAULT_LABELS = [
    "Nucleus",
    "Cell Membrane",
    "Mitochondria",
    "Endoplasmic Reticulum",
    "Golgi Apparatus",
    "Ribosome",
]

ZONE_COLORS = [
    (255, 59, 48),     # red
    (0, 122, 255),     # blue
    (52, 199, 89),     # green
    (255, 149, 0),     # orange
    (175, 82, 222),    # purple
    (255, 204, 0),     # yellow
    (88, 86, 214),     # indigo
    (0, 199, 190),     # teal
    (255, 45, 85),     # pink
    (162, 132, 94),    # brown
]

ZONE_COLORS_HEX = [
    '#ff3b30', '#007aff', '#34c759', '#ff9500', '#af52de',
    '#ffcc00', '#5856d6', '#00c7be', '#ff2d55', '#a2845e',
]


# ---------------------------------------------------------------------------
# Diagram generation
# ---------------------------------------------------------------------------

async def _generate_diagram(subject: str, labels: list[str]) -> bytes:
    from app.services.asset_gen.imagen import ImagenGenerator
    logger.info(f"Generating diagram via Imagen for '{subject}' ...")
    gen = ImagenGenerator()
    diagram_bytes = await gen.generate_educational_diagram(
        subject=subject, structures=labels,
        style="clean educational cross-section illustration",
        include_labels=False,
    )
    logger.info(f"Generated diagram: {len(diagram_bytes):,} bytes")
    return diagram_bytes


# ---------------------------------------------------------------------------
# Detection methods
# ---------------------------------------------------------------------------

async def detect_gemini_text(image_bytes: bytes, labels: list[str], context: str,
                              model: str = "gemini-2.5-flash") -> tuple[list[dict], float]:
    """Run Gemini text polygon detection with a specific model."""
    from app.services.asset_gen.gemini_image import GeminiImageEditor

    editor = GeminiImageEditor()
    # Temporarily override model
    original_model = editor.VISION_MODEL
    editor.VISION_MODEL = model
    try:
        t0 = time.time()
        zones = await editor._detect_zones_with_text(image_bytes, labels, context)
        elapsed = time.time() - t0
    finally:
        editor.VISION_MODEL = original_model
    return zones or [], elapsed


async def detect_gemini_mask(image_bytes: bytes, labels: list[str], context: str) -> tuple[list[dict], float]:
    from app.services.asset_gen.gemini_image import GeminiImageEditor
    editor = GeminiImageEditor()
    t0 = time.time()
    zones = await editor._detect_zones_with_masks(image_bytes, labels, context)
    elapsed = time.time() - t0
    return zones or [], elapsed


async def detect_sam3_text(image_bytes: bytes, labels: list[str], context: str) -> tuple[list[dict], float]:
    from app.services.asset_gen.segmentation import LocalSegmentationService
    svc = LocalSegmentationService()
    t0 = time.time()
    zones = await svc.detect_zones(image_bytes, labels, context=context)
    elapsed = time.time() - t0
    return zones or [], elapsed


async def detect_gemini_box2d(image_bytes: bytes, labels: list[str], context: str,
                               model: str = "gemini-2.5-flash") -> tuple[list[dict], float]:
    """Run Gemini native box_2d bounding box detection."""
    from app.services.asset_gen.gemini_image import GeminiImageEditor

    editor = GeminiImageEditor()
    t0 = time.time()
    boxes = await editor.detect_bounding_boxes(image_bytes, labels, context, model=model)
    elapsed = time.time() - t0

    # Convert box results to zone format for overlay display
    zones = []
    for b in boxes:
        ymin, xmin, ymax, xmax = b["box_2d"]
        points = [[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]]
        zones.append({
            "id": f"zone_{b['label'].lower().replace(' ', '_')}",
            "label": b["label"],
            "points": points,
            "x": b["x"], "y": b["y"],
            "radius": b["radius"],
            "center": {"x": b["x"], "y": b["y"]},
            "shape": "polygon",
            "description": "",
        })
    return zones, elapsed


async def detect_gemini_guided_sam3(image_bytes: bytes, labels: list[str], context: str,
                                      gemini_model: str = "gemini-2.5-flash") -> tuple[list[dict], float]:
    """Gemini box_2d provides bounding boxes → SAM3 segments precisely within each box."""
    from app.services.asset_gen.gemini_image import GeminiImageEditor
    from app.services.asset_gen.segmentation import LocalSegmentationService

    t0 = time.time()

    # Step 1: Get native bounding boxes from Gemini (NOT text polygon guessing)
    editor = GeminiImageEditor()
    boxes = await editor.detect_bounding_boxes(image_bytes, labels, context, model=gemini_model)

    if not boxes:
        return [], time.time() - t0

    # Step 2: Build guide boxes from box_2d results (top-left + size format)
    guide_boxes = {}
    for b in boxes:
        label = b["label"]
        if label not in guide_boxes:
            ymin, xmin, ymax, xmax = b["box_2d"]
            guide_boxes[label] = {
                "x": xmin,
                "y": ymin,
                "width": xmax - xmin,
                "height": ymax - ymin,
            }

    logger.info(f"Gemini box_2d: {len(guide_boxes)} boxes → SAM3 guided")

    # Step 3: SAM3 guided segmentation using proper bounding boxes
    svc = LocalSegmentationService()
    zones = await svc.detect_zones_guided(image_bytes, labels, guide_boxes, context=context)

    elapsed = time.time() - t0
    return zones or [], elapsed


# ---------------------------------------------------------------------------
# Overlay drawing
# ---------------------------------------------------------------------------

def _get_font(size: int = 14):
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_overlay(image_bytes: bytes, zones: list[dict], method_name: str, elapsed: float) -> Image.Image:
    base = Image.open(BytesIO(image_bytes)).convert("RGBA")
    img_w, img_h = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    label_font = _get_font(16)
    title_font = _get_font(22)

    for i, zone in enumerate(zones):
        color = ZONE_COLORS[i % len(ZONE_COLORS)]
        fill_color = color + (50,)
        outline_color = color + (220,)
        label = zone.get("label", f"zone_{i}")
        points = zone.get("points", [])

        if points and len(points) >= 3:
            pixel_pts = [(p[0] / 100.0 * img_w, p[1] / 100.0 * img_h) for p in points]
            draw.polygon(pixel_pts, fill=fill_color, outline=outline_color)
            for j in range(len(pixel_pts)):
                p1, p2 = pixel_pts[j], pixel_pts[(j + 1) % len(pixel_pts)]
                draw.line([p1, p2], fill=outline_color, width=3)
            cx = sum(p[0] for p in pixel_pts) / len(pixel_pts)
            cy = sum(p[1] for p in pixel_pts) / len(pixel_pts)
        else:
            cx_pct, cy_pct = zone.get("x", 50), zone.get("y", 50)
            r_pct = zone.get("radius", 5)
            cx, cy = cx_pct / 100.0 * img_w, cy_pct / 100.0 * img_h
            r = r_pct / 100.0 * min(img_w, img_h)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill_color, outline=outline_color, width=3)

        text = f"{i + 1}. {label}"
        bbox = label_font.getbbox(text)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        lx = max(4, min(cx - tw / 2, img_w - tw - 4))
        ly = max(4, min(cy - th - 8, img_h - th - 4))
        draw.rectangle([lx - 3, ly - 2, lx + tw + 3, ly + th + 2], fill=(0, 0, 0, 180))
        draw.text((lx, ly), text, fill=(255, 255, 255, 255), font=label_font)

    title_text = f"{method_name}  |  {len(zones)} zones  |  {elapsed:.1f}s"
    title_bbox = title_font.getbbox(title_text)
    title_tw = title_bbox[2] - title_bbox[0]
    title_th = title_bbox[3] - title_bbox[1]
    draw.rectangle([0, 0, img_w, title_th + 16], fill=(0, 0, 0, 200))
    draw.text(((img_w - title_tw) / 2, 6), title_text, fill=(255, 255, 255, 255), font=title_font)

    return Image.alpha_composite(base, overlay).convert("RGB")


# ---------------------------------------------------------------------------
# HTML comparison viewer generator
# ---------------------------------------------------------------------------

def generate_html_viewer(image_bytes: bytes, json_data: dict, output_path: Path):
    """Generate a self-contained HTML viewer with inlined image + zone data."""
    img_b64 = base64.b64encode(image_bytes).decode()
    zone_json = json.dumps(json_data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Zone Detection Comparison</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #1a1a2e; color: #eee; font-family: system-ui, sans-serif; }}
  h1 {{ text-align: center; padding: 16px; font-size: 1.3em; color: #e0e0ff; }}
  .controls {{ display: flex; justify-content: center; gap: 8px; padding: 8px 16px; flex-wrap: wrap; }}
  .controls button {{
    padding: 6px 16px; border: 2px solid #555; border-radius: 8px;
    background: #2a2a4a; color: #ccc; cursor: pointer; font-size: 0.85em;
    transition: all 0.2s;
  }}
  .controls button.active {{ border-color: #7c7cff; background: #3a3a6a; color: #fff; font-weight: 600; }}
  .controls button:hover {{ border-color: #9999ff; }}
  .viewer {{ display: flex; justify-content: center; padding: 16px; gap: 12px; flex-wrap: wrap; }}
  .panel {{ position: relative; flex: 0 0 auto; }}
  .panel canvas {{ border-radius: 6px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }}
  .legend {{ display: flex; justify-content: center; gap: 16px; padding: 8px; flex-wrap: wrap; }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 0.8em; }}
  .legend-swatch {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid #555; }}
  .stats {{ text-align: center; padding: 6px; font-size: 0.8em; color: #aaa; }}
  .mode-row {{ display: flex; justify-content: center; gap: 12px; padding: 4px; }}
  .mode-row label {{ cursor: pointer; font-size: 0.85em; }}
  table {{ margin: 16px auto; border-collapse: collapse; font-size: 0.85em; }}
  th, td {{ padding: 6px 12px; border: 1px solid #444; text-align: center; }}
  th {{ background: #2a2a4a; }}
  tr:hover {{ background: #252545; }}
  .good {{ color: #34c759; }} .warn {{ color: #ffcc00; }} .bad {{ color: #ff3b30; }}
</style>
</head>
<body>

<h1>Zone Detection Method Comparison</h1>

<div class="controls" id="buttons"></div>

<div class="mode-row">
  <label><input type="checkbox" id="showLabels" checked onchange="redraw()"> Labels</label>
  <label><input type="checkbox" id="showCenters" checked onchange="redraw()"> Centers</label>
  <label><input type="checkbox" id="fillZones" checked onchange="redraw()"> Fill</label>
  <label><input type="checkbox" id="showOutline" checked onchange="redraw()"> Outline</label>
</div>

<div class="legend" id="legend"></div>
<div id="summary"></div>
<div class="viewer" id="viewer"></div>

<script>
const COLORS = {json.dumps(ZONE_COLORS_HEX)};
const DATA = {zone_json};
const IMG_SRC = "data:image/png;base64,{img_b64}";

let sourceImg = null;
let currentView = 'side';
const methods = DATA.results;

// Build label→color map
const labelColors = {{}};
DATA.labels.forEach((l, i) => {{ labelColors[l] = COLORS[i % COLORS.length]; }});

// Build buttons
const btnDiv = document.getElementById('buttons');
const sideBtn = mkBtn('Side by Side', () => setView('side'), true);
btnDiv.appendChild(sideBtn);
methods.forEach((m, i) => {{
  btnDiv.appendChild(mkBtn(m.method, () => setView(i)));
}});
btnDiv.appendChild(mkBtn('All Overlaid', () => setView('overlay')));

function mkBtn(text, onClick, active) {{
  const b = document.createElement('button');
  b.textContent = text;
  if (active) b.classList.add('active');
  b.addEventListener('click', function() {{
    document.querySelectorAll('.controls button').forEach(x => x.classList.remove('active'));
    this.classList.add('active');
    onClick();
  }});
  return b;
}}

// Legend
document.getElementById('legend').innerHTML = DATA.labels.map(l =>
  `<span class="legend-item"><span class="legend-swatch" style="background:${{labelColors[l]}}"></span>${{l}}</span>`
).join('');

// Summary table
let tbl = '<table><tr><th>Method</th><th>Zones</th><th>Labels</th><th>Avg Pts</th><th>Time</th></tr>';
methods.forEach(m => {{
  const labels = [...new Set(m.zones.map(z => z.label))].length;
  const cls = labels >= DATA.labels.length ? 'good' : labels >= DATA.labels.length / 2 ? 'warn' : 'bad';
  const pts = m.zones.filter(z => z.points).map(z => z.points.length);
  const avgPts = pts.length ? (pts.reduce((a,b) => a+b, 0) / pts.length).toFixed(1) : '-';
  tbl += `<tr><td>${{m.method}}</td><td>${{m.num_zones}}</td><td class="${{cls}}">${{labels}}/${{DATA.labels.length}}</td><td>${{avgPts}}</td><td>${{m.elapsed.toFixed(1)}}s</td></tr>`;
}});
tbl += '</table>';
document.getElementById('summary').innerHTML = tbl;

// Load image
sourceImg = new Image();
sourceImg.onload = () => redraw();
sourceImg.src = IMG_SRC;

function setView(v) {{ currentView = v; redraw(); }}

function redraw() {{
  if (!sourceImg) return;
  const viewer = document.getElementById('viewer');
  viewer.innerHTML = '';
  const opts = {{
    showLabels: document.getElementById('showLabels').checked,
    showCenters: document.getElementById('showCenters').checked,
    fillZones: document.getElementById('fillZones').checked,
    showOutline: document.getElementById('showOutline').checked,
  }};
  const maxW = Math.min(window.innerWidth - 40, 1400);

  if (currentView === 'side') {{
    const cols = Math.min(methods.length, 3);
    const cw = Math.floor((maxW - (cols - 1) * 12) / cols);
    const ch = Math.floor(cw * (sourceImg.height / sourceImg.width));
    methods.forEach(m => viewer.appendChild(makePanel(cw, ch, m, opts)));
  }} else if (currentView === 'overlay') {{
    viewer.appendChild(makeOverlayPanel(maxW, methods, opts));
  }} else {{
    const m = methods[currentView];
    const ch = Math.floor(maxW * (sourceImg.height / sourceImg.width));
    viewer.appendChild(makePanel(maxW, ch, m, opts));
  }}
}}

function makePanel(w, h, method, opts) {{
  const wrap = document.createElement('div');
  wrap.className = 'panel';
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d');
  ctx.drawImage(sourceImg, 0, 0, w, h);
  drawZones(ctx, w, h, method.zones, opts, 0.3);
  // Title bar
  ctx.fillStyle = 'rgba(0,0,0,0.75)';
  ctx.fillRect(0, 0, w, 26);
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 12px system-ui';
  ctx.fillText(`${{method.method}} | ${{method.num_zones}} zones | ${{method.elapsed.toFixed(1)}}s`, 8, 17);
  wrap.appendChild(c);
  return wrap;
}}

function makeOverlayPanel(maxW, methods, opts) {{
  const wrap = document.createElement('div');
  wrap.className = 'panel';
  const w = maxW, h = Math.floor(w * (sourceImg.height / sourceImg.width));
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d');
  ctx.drawImage(sourceImg, 0, 0, w, h);
  const mColors = ['#ff4444','#44cc44','#4488ff','#ffaa00','#cc44ff','#00cccc','#ff6688','#88cc00'];
  const dashes = [[8,4],[3,3],[],[12,4],[6,2],[4,8],[2,6],[10,2]];
  methods.forEach((m, mi) => {{
    m.zones.forEach(z => {{
      const pts = (z.points || []).map(p => [p[0]/100*w, p[1]/100*h]);
      if (pts.length < 2) return;
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      pts.slice(1).forEach(p => ctx.lineTo(p[0], p[1]));
      ctx.closePath();
      ctx.strokeStyle = mColors[mi % mColors.length];
      ctx.lineWidth = 2.5;
      ctx.setLineDash(dashes[mi % dashes.length]);
      ctx.stroke();
      ctx.setLineDash([]);
    }});
  }});
  // Legend bar
  ctx.fillStyle = 'rgba(0,0,0,0.8)';
  ctx.fillRect(0, 0, w, 26);
  ctx.font = 'bold 11px system-ui';
  let lx = 10;
  methods.forEach((m, i) => {{
    ctx.fillStyle = mColors[i % mColors.length];
    ctx.fillText(`■ ${{m.method}}`, lx, 17);
    lx += ctx.measureText(`■ ${{m.method}}`).width + 20;
  }});
  wrap.appendChild(c);
  return wrap;
}}

function drawZones(ctx, w, h, zones, opts, alpha) {{
  zones.forEach((zone, i) => {{
    const color = labelColors[zone.label] || '#888';
    const pts = (zone.points || []).map(p => [p[0]/100*w, p[1]/100*h]);
    if (pts.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    pts.slice(1).forEach(p => ctx.lineTo(p[0], p[1]));
    ctx.closePath();
    if (opts.fillZones) {{ ctx.fillStyle = hexToRgba(color, alpha); ctx.fill(); }}
    if (opts.showOutline) {{ ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.stroke(); }}
    if (opts.showCenters) {{
      const cx = zone.x/100*w, cy = zone.y/100*h;
      ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI*2);
      ctx.fillStyle = color; ctx.fill();
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.stroke();
    }}
    if (opts.showLabels) {{
      const cx = zone.x/100*w, cy = zone.y/100*h;
      ctx.font = 'bold 11px system-ui';
      const tw = ctx.measureText(zone.label).width;
      ctx.fillStyle = 'rgba(0,0,0,0.75)';
      ctx.fillRect(cx-tw/2-3, cy-18, tw+6, 16);
      ctx.fillStyle = color;
      ctx.fillText(zone.label, cx-tw/2, cy-6);
    }}
  }});
}}

function hexToRgba(hex, a) {{
  const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return `rgba(${{r}},${{g}},${{b}},${{a}})`;
}}

window.addEventListener('resize', redraw);
</script>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    logger.info(f"HTML viewer: {output_path} ({len(html) // 1024}KB)")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary_table(results: list[dict], total_labels: int):
    print("\n" + "=" * 110)
    print("  ZONE DETECTION COMPARISON SUMMARY")
    print("=" * 110)
    header = f"{'Method':<35} {'Zones':>6} {'Labels':>7} {'Polygons':>9} {'Avg Pts':>8} {'Time':>8} {'Status':<10}"
    print(header)
    print("-" * 110)

    for r in results:
        zones = r["zones"]
        n_labels = len(set(z.get("label", "") for z in zones))
        n_poly = sum(1 for z in zones if z.get("shape") == "polygon")
        poly_points = [len(z.get("points", [])) for z in zones if z.get("points")]
        avg_pts = sum(poly_points) / len(poly_points) if poly_points else 0
        print(
            f"{r['method']:<35} {len(zones):>6} {n_labels:>7} {n_poly:>9} "
            f"{avg_pts:>8.1f} {r['elapsed']:>7.1f}s {r['status']:<10}"
        )

    print("-" * 110)
    for r in results:
        if r["status"] != "OK" or not r["zones"]:
            continue
        print(f"\n  {r['method']}:")
        for z in r["zones"]:
            pts = len(z.get("points", []))
            print(f"    {z.get('label', '?'):<28} pts={pts:>3}  center=({z.get('x',0):5.1f}, {z.get('y',0):5.1f})  r={z.get('radius',0):5.1f}")
    print("=" * 110)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Compare zone detection methods")
    parser.add_argument("--image", type=str, default=None, help="Path to diagram image")
    parser.add_argument("--generate", action="store_true", help="Force generate new diagram")
    parser.add_argument("--subject", type=str, default=DEFAULT_SUBJECT)
    parser.add_argument("--labels", type=str, default=None, help="Comma-separated labels")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--skip-sam3", action="store_true", help="Skip SAM3 methods (faster)")
    parser.add_argument("--skip-mask", action="store_true", help="Skip Gemini Mask method")
    args = parser.parse_args()

    labels = [l.strip() for l in args.labels.split(",")] if args.labels else DEFAULT_LABELS
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY not set"); sys.exit(1)

    # ── Step 1: Get diagram ──
    print("\n" + "=" * 70)
    print("  ZONE DETECTION METHOD COMPARISON")
    print("=" * 70)
    print(f"  Subject: {args.subject}")
    print(f"  Labels:  {labels}")
    print()

    if args.image:
        image_bytes = Path(args.image).read_bytes()
        image_source = args.image
    elif args.generate or not (output_dir / "source_diagram.png").exists():
        image_bytes = await _generate_diagram(args.subject, labels)
        (output_dir / "source_diagram.png").write_bytes(image_bytes)
        image_source = "Generated"
    else:
        image_bytes = (output_dir / "source_diagram.png").read_bytes()
        image_source = "Cached"

    img = Image.open(BytesIO(image_bytes))
    print(f"  Image: {img.size[0]}x{img.size[1]}, {len(image_bytes):,} bytes ({image_source})")
    print()

    context = f"Educational diagram of {args.subject}"

    # ── Step 2: Run methods ──
    results: list[dict] = []
    overlays: list[tuple[str, Image.Image]] = []

    async def run_method(name: str, coro):
        print(f"  [{name}] Running ...")
        try:
            zones, elapsed = await coro
            status = "OK" if zones else "NO ZONES"
            results.append({"method": name, "zones": zones, "elapsed": elapsed, "status": status})
            print(f"  [{name}] {len(zones)} zones, {len(set(z['label'] for z in zones))} labels in {elapsed:.1f}s")
            if zones:
                overlay_img = draw_overlay(image_bytes, zones, name, elapsed)
                slug = name.lower().replace(' ', '_').replace('→', '').replace('(', '').replace(')', '').replace('.', '')
                save_path = output_dir / f"zone_{slug}.png"
                overlay_img.save(str(save_path), "PNG")
                overlays.append((name, overlay_img))
        except Exception as e:
            results.append({"method": name, "zones": [], "elapsed": 0.0, "status": f"ERROR: {e}"})
            print(f"  [{name}] Error: {e}")
        print()

    # --- Gemini text polygon estimation (baseline) ---
    await run_method("Gemini Text (2.5-flash)", detect_gemini_text(image_bytes, labels, context, "gemini-2.5-flash"))

    # --- Gemini native box_2d detection (trained for spatial accuracy) ---
    await run_method("Gemini Box2d (2.5-flash)", detect_gemini_box2d(image_bytes, labels, context, "gemini-2.5-flash"))
    await run_method("Gemini Box2d (2.5-pro)", detect_gemini_box2d(image_bytes, labels, context, "gemini-2.5-pro"))
    await run_method("Gemini Box2d (3-flash)", detect_gemini_box2d(image_bytes, labels, context, "gemini-3-flash-preview"))

    if not args.skip_sam3:
        # SAM3 text-only (no spatial guidance — baseline)
        await run_method("SAM3 text-only", detect_sam3_text(image_bytes, labels, context))

        # Gemini box_2d → SAM3 guided (the target pipeline)
        await run_method("Box2d→SAM3 (2.5-flash)", detect_gemini_guided_sam3(image_bytes, labels, context, "gemini-2.5-flash"))
        await run_method("Box2d→SAM3 (3-flash)", detect_gemini_guided_sam3(image_bytes, labels, context, "gemini-3-flash-preview"))

    # ── Step 3: Save data + generate HTML viewer ──
    json_data = {
        "subject": args.subject,
        "labels": labels,
        "image_source": image_source,
        "image_size": list(img.size),
        "results": [
            {
                "method": r["method"],
                "status": r["status"],
                "elapsed": round(r["elapsed"], 2),
                "num_zones": len(r["zones"]),
                "zones": r["zones"],
            }
            for r in results
        ],
    }

    json_path = output_dir / "zone_comparison_data.json"
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    html_path = output_dir / "compare.html"
    generate_html_viewer(image_bytes, json_data, html_path)

    print_summary_table(results, len(labels))

    print(f"\nOutput files:")
    for f in sorted(output_dir.glob("zone_*")) + [html_path]:
        if f.exists():
            print(f"  {f.name:<50} {f.stat().st_size / 1024:>8.1f} KB")

    ok = sum(1 for r in results if r["status"] == "OK")
    print(f"\nDone. {ok}/{len(results)} methods succeeded.")
    print(f"Open: {html_path}")


if __name__ == "__main__":
    asyncio.run(main())
