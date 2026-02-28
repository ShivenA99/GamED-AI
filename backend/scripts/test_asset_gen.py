#!/usr/bin/env python3
"""
Test script for the Asset Generation Service.

Exercises every component with real API calls and shows clear input/output.

Usage:
    cd backend && source venv/bin/activate
    PYTHONPATH=. python scripts/test_asset_gen.py [--component COMPONENT]

Components: search, gemini, imagen, svg, core, all (default)
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from io import BytesIO
from pathlib import Path

from PIL import Image

# ─── Setup logging ────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_asset_gen")

# Suppress noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

TEST_GAME_ID = "test_asset_gen"
RESULTS_DIR = Path(__file__).parent.parent / "assets" / "demo" / TEST_GAME_ID
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def _subheader(title: str):
    print(f"\n--- {title} ---")


def _show_image_info(data: bytes, label: str = "Image"):
    """Show image dimensions and size."""
    try:
        img = Image.open(BytesIO(data))
        print(f"  {label}: {img.size[0]}x{img.size[1]} ({img.mode}), {len(data):,} bytes")
    except Exception:
        print(f"  {label}: {len(data):,} bytes (not a valid image)")


def _show_svg_info(svg_code: str, label: str = "SVG"):
    """Show SVG code summary."""
    lines = svg_code.strip().split("\n")
    print(f"  {label}: {len(svg_code):,} chars, {len(lines)} lines")
    # Show first and last line
    print(f"    First: {lines[0][:100]}")
    if len(lines) > 1:
        print(f"    Last:  {lines[-1][:100]}")


def _elapsed(start: float) -> str:
    return f"{time.time() - start:.1f}s"


# ─── Component Tests ─────────────────────────────────────────────

async def test_search():
    """Test 1: ImageSearcher — search + download."""
    from app.services.asset_gen.search import ImageSearcher

    _header("TEST 1: ImageSearcher")
    searcher = ImageSearcher()

    # --- 1a: Basic search ---
    _subheader("1a. Search for 'human heart anatomy diagram labeled educational'")
    t = time.time()
    results = await searcher.search("human heart anatomy diagram labeled educational", num_results=5)
    print(f"  Time: {_elapsed(t)}")
    print(f"  Results: {len(results)}")
    for i, r in enumerate(results):
        print(f"    [{i}] score={r['score']:.1f}  title=\"{r['title'][:60]}\"")
        print(f"        url={r['image_url'][:80]}...")
        print(f"        size={r.get('width', '?')}x{r.get('height', '?')}")

    # --- 1b: Search and download best ---
    _subheader("1b. Search and download best image")
    t = time.time()
    result = await searcher.search_and_download_best(
        "flower anatomy diagram educational",
        fallback_queries=["parts of a flower labeled diagram"],
    )
    print(f"  Time: {_elapsed(t)}")
    if result:
        img_bytes, meta = result
        _show_image_info(img_bytes, "Downloaded")
        print(f"  Source: {meta['source_url'][:80]}")
        print(f"  Score:  {meta['score']:.1f}")
        # Save for later tests
        (RESULTS_DIR / "test_reference.png").write_bytes(img_bytes)
        print(f"  Saved:  {RESULTS_DIR / 'test_reference.png'}")
    else:
        print("  FAILED: No image downloaded")
        return False

    # --- 1c: Multiple item search ---
    _subheader("1c. Search multiple items")
    t = time.time()
    items_result = await searcher.search_multiple_items(
        ["mitochondria", "nucleus", "chloroplast"],
        query_template="{item} cell organelle illustration educational",
        num_results=3,
    )
    print(f"  Time: {_elapsed(t)}")
    for name, val in items_result.items():
        if val:
            img_bytes, meta = val
            _show_image_info(img_bytes, f"  {name}")
        else:
            print(f"  {name}: FAILED")

    print("\n  ✓ ImageSearcher tests complete")
    return True


async def test_gemini():
    """Test 2: GeminiImageEditor — edit, regenerate, zones, paths."""
    from app.services.asset_gen.gemini_image import GeminiImageEditor

    _header("TEST 2: GeminiImageEditor")
    editor = GeminiImageEditor()

    # Load reference image from search test (or use a simple generated one)
    ref_path = RESULTS_DIR / "test_reference.png"
    if not ref_path.exists():
        # Create a small placeholder to test with
        print("  No reference image found, running search first...")
        from app.services.asset_gen.search import ImageSearcher
        searcher = ImageSearcher()
        result = await searcher.search_and_download_best("human heart diagram educational")
        if result:
            ref_path.write_bytes(result[0])
        else:
            print("  FAILED: Cannot get reference image")
            return False

    ref_bytes = ref_path.read_bytes()
    _show_image_info(ref_bytes, "Reference input")

    # --- 2a: Clean diagram (remove labels) ---
    _subheader("2a. Clean diagram — remove labels/annotations")
    print("  INPUT:  reference image + instructions='Remove all text labels, arrows, annotations'")
    t = time.time()
    try:
        cleaned = await editor.clean_diagram(ref_bytes)
        print(f"  Time: {_elapsed(t)}")
        _show_image_info(cleaned, "OUTPUT")
        (RESULTS_DIR / "test_cleaned.png").write_bytes(cleaned)
        print(f"  Saved: test_cleaned.png")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 2b: Regenerate from reference ---
    _subheader("2b. Regenerate from reference — create new original image")
    prompt = (
        "A clean educational cross-section illustration of a human heart, "
        "showing all four chambers, major valves, and great vessels. "
        "Anatomically accurate, high contrast, white background, textbook quality."
    )
    print(f"  INPUT:  reference image + prompt='{prompt[:80]}...'")
    t = time.time()
    try:
        regenerated = await editor.regenerate_from_reference(ref_bytes, prompt)
        print(f"  Time: {_elapsed(t)}")
        _show_image_info(regenerated, "OUTPUT")
        (RESULTS_DIR / "test_regenerated.png").write_bytes(regenerated)
        print(f"  Saved: test_regenerated.png")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 2c: Detect zones ---
    _subheader("2c. Detect zones — find structures on diagram")
    labels = ["Right Atrium", "Left Atrium", "Right Ventricle", "Left Ventricle", "Aorta"]
    # Use the regenerated image if available, else reference
    zone_img_path = RESULTS_DIR / "test_regenerated.png"
    if not zone_img_path.exists():
        zone_img_path = ref_path
    zone_bytes = zone_img_path.read_bytes()

    print(f"  INPUT:  diagram image + labels={labels}")
    t = time.time()
    try:
        zones = await editor.detect_zones(
            zone_bytes,
            expected_labels=labels,
            context="Cross-section of a human heart",
        )
        print(f"  Time: {_elapsed(t)}")
        print(f"  OUTPUT: {len(zones)} zones detected")
        for z in zones:
            print(f"    {z['id']}: ({z['x']:.1f}, {z['y']:.1f}) r={z['radius']:.1f} shape={z['shape']}")
            print(f"      desc: {z.get('description', 'N/A')[:60]}")
        # Save zones
        (RESULTS_DIR / "test_zones.json").write_text(json.dumps(zones, indent=2))
        print(f"  Saved: test_zones.json")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 2d: Style-consistent set ---
    _subheader("2d. Style-consistent set — generate matching illustrations")
    items = [
        {"name": "Heart", "description": "Human heart organ"},
        {"name": "Lungs", "description": "Pair of lungs"},
    ]
    print(f"  INPUT:  items={[i['name'] for i in items]}, style='medical illustration'")
    t = time.time()
    try:
        image_set = await editor.generate_style_consistent_set(
            items=items,
            style_description="medical illustration, organ anatomy",
            aspect_ratio="1:1",
        )
        print(f"  Time: {_elapsed(t)}")
        print(f"  OUTPUT: {len(image_set)} images generated")
        for i, img_bytes in enumerate(image_set):
            _show_image_info(img_bytes, f"  [{i}] {items[i]['name']}")
            (RESULTS_DIR / f"test_style_{items[i]['name'].lower()}.png").write_bytes(img_bytes)
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n  ✓ GeminiImageEditor tests complete")
    return True


async def test_imagen():
    """Test 3: ImagenGenerator — Imagen 4 image generation."""
    from app.services.asset_gen.imagen import ImagenGenerator

    _header("TEST 3: ImagenGenerator (Imagen 4)")
    gen = ImagenGenerator()

    # --- 3a: Basic text-to-image ---
    _subheader("3a. Basic text-to-image generation")
    prompt = (
        "A clean scientific illustration of a mitochondria, "
        "cross-section view showing inner membrane cristae, "
        "matrix, outer membrane. White background, no text, educational style."
    )
    print(f"  INPUT:  prompt='{prompt[:80]}...'")
    print(f"          model=standard, aspect_ratio=1:1, image_size=1K")
    t = time.time()
    try:
        images = await gen.generate(prompt, model="standard", aspect_ratio="1:1", image_size="1K")
        print(f"  Time: {_elapsed(t)}")
        print(f"  OUTPUT: {len(images)} image(s)")
        for i, img_bytes in enumerate(images):
            _show_image_info(img_bytes, f"  [{i}]")
            (RESULTS_DIR / f"test_imagen_{i}.png").write_bytes(img_bytes)
            print(f"  Saved: test_imagen_{i}.png")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 3b: Educational diagram ---
    _subheader("3b. Educational diagram generation")
    print(f"  INPUT:  subject='plant cell', structures=['Cell Wall', 'Nucleus', 'Chloroplast']")
    t = time.time()
    try:
        diagram = await gen.generate_educational_diagram(
            subject="plant cell cross-section",
            structures=["Cell Wall", "Nucleus", "Chloroplast", "Vacuole"],
            style="clean scientific illustration",
            include_labels=False,
        )
        print(f"  Time: {_elapsed(t)}")
        _show_image_info(diagram, "OUTPUT")
        (RESULTS_DIR / "test_imagen_diagram.png").write_bytes(diagram)
        print(f"  Saved: test_imagen_diagram.png")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 3c: Item illustration (fast model) ---
    _subheader("3c. Item illustration (fast model)")
    print(f"  INPUT:  item='Red Blood Cell', model=fast")
    t = time.time()
    try:
        item_img = await gen.generate_item_illustration(
            item_name="Red Blood Cell",
            context="Human blood components",
            style="scientific illustration",
        )
        print(f"  Time: {_elapsed(t)}")
        _show_image_info(item_img, "OUTPUT")
        (RESULTS_DIR / "test_imagen_item.png").write_bytes(item_img)
        print(f"  Saved: test_imagen_item.png")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n  ✓ ImagenGenerator tests complete")
    return True


async def test_svg():
    """Test 4: SVGGenerator — SVG code generation via Gemini text."""
    from app.services.asset_gen.svg_gen import SVGGenerator

    _header("TEST 4: SVGGenerator")
    gen = SVGGenerator()

    # --- 4a: Single SVG icon ---
    _subheader("4a. Single SVG icon")
    print(f"  INPUT:  description='A simple heart organ icon, red, anatomical'")
    t = time.time()
    try:
        svg = await gen.generate_svg(
            "A simple heart organ icon, red, anatomical",
            width=48, height=48,
            style_hints="Flat design, solid fills, no gradients",
        )
        print(f"  Time: {_elapsed(t)}")
        _show_svg_info(svg, "OUTPUT")
        (RESULTS_DIR / "test_icon_heart.svg").write_text(svg)
        print(f"  Saved: test_icon_heart.svg")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 4b: Icon set (consistent style) ---
    _subheader("4b. Icon set (3 consistent icons)")
    icons = [
        {"name": "chambers", "description": "Heart chambers icon"},
        {"name": "valves", "description": "Heart valves icon"},
        {"name": "vessels", "description": "Blood vessels icon"},
    ]
    print(f"  INPUT:  icons={[i['name'] for i in icons]}, style='flat, modern, educational'")
    t = time.time()
    try:
        icon_set = await gen.generate_icon_set(icons, size=48)
        print(f"  Time: {_elapsed(t)}")
        print(f"  OUTPUT: {len(icon_set)} icons generated")
        for name, code in icon_set.items():
            _show_svg_info(code, f"  {name}")
            (RESULTS_DIR / f"test_icon_{name}.svg").write_text(code)
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 4c: Card back pattern ---
    _subheader("4c. Card back pattern")
    print(f"  INPUT:  theme='biology cells', colors=['#6366f1', '#8b5cf6', '#a855f7']")
    t = time.time()
    try:
        pattern = await gen.generate_card_back_pattern(
            theme="biology cells",
            colors=["#6366f1", "#8b5cf6", "#a855f7"],
        )
        print(f"  Time: {_elapsed(t)}")
        _show_svg_info(pattern, "OUTPUT")
        (RESULTS_DIR / "test_card_back.svg").write_text(pattern)
        print(f"  Saved: test_card_back.svg")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 4d: Connector arrow ---
    _subheader("4d. Connector arrow SVG")
    print(f"  INPUT:  type='arrow', color='#6366f1', animated=True")
    t = time.time()
    try:
        connector = await gen.generate_connector_svg(
            connector_type="arrow", color="#6366f1", animated=True,
        )
        print(f"  Time: {_elapsed(t)}")
        _show_svg_info(connector, "OUTPUT")
        (RESULTS_DIR / "test_connector.svg").write_text(connector)
        print(f"  Saved: test_connector.svg")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 4e: Particle sprite ---
    _subheader("4e. Particle sprite")
    print(f"  INPUT:  theme='sparkle', size=24, color='#fbbf24'")
    t = time.time()
    try:
        particle = await gen.generate_particle_sprite(
            theme="sparkle", size=24, color="#fbbf24",
        )
        print(f"  Time: {_elapsed(t)}")
        _show_svg_info(particle, "OUTPUT")
        (RESULTS_DIR / "test_particle.svg").write_text(particle)
        print(f"  Saved: test_particle.svg")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n  ✓ SVGGenerator tests complete")
    return True


async def test_core():
    """Test 5: AssetGenService — full orchestrator workflows."""
    from app.services.asset_gen.core import AssetGenService

    _header("TEST 5: AssetGenService (Core Orchestrator)")
    svc = AssetGenService()

    # --- 5a: generate_diagram (search → regenerate → zone detect) ---
    _subheader("5a. generate_diagram — full diagram workflow")
    print(f"  INPUT:  subject='parts of a flower'")
    print(f"          structures=['Petal', 'Sepal', 'Anther', 'Stigma', 'Ovary']")
    t = time.time()
    try:
        result = await svc.generate_diagram(
            game_id="test_core_diagram",
            subject="parts of a flower",
            structures=["Petal", "Sepal", "Anther", "Stigma", "Ovary"],
            style="clean educational cross-section illustration",
        )
        print(f"  Time: {_elapsed(t)}")
        print(f"  OUTPUT:")
        print(f"    diagram_url: {result['diagram_url']}")
        print(f"    zones: {len(result['zones'])} detected")
        for z in result["zones"]:
            print(f"      {z['label']}: ({z['x']:.1f}, {z['y']:.1f}) r={z['radius']:.1f}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()

    # --- 5b: generate_item_illustrations (style-consistent set) ---
    _subheader("5b. generate_item_illustrations — style-consistent set")
    items = [
        {"name": "Heart", "description": "Human heart organ"},
        {"name": "Lungs", "description": "Pair of human lungs"},
    ]
    print(f"  INPUT:  items={[i['name'] for i in items]}")
    t = time.time()
    try:
        urls = await svc.generate_item_illustrations(
            game_id="test_core_items",
            items=items,
            style="medical illustration",
            category="human anatomy",
        )
        print(f"  Time: {_elapsed(t)}")
        print(f"  OUTPUT: {len(urls)} images")
        for name, url in urls.items():
            print(f"    {name}: {url}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()

    # --- 5c: generate_icon_set ---
    _subheader("5c. generate_icon_set — SVG icons")
    icons = [
        {"name": "easy", "description": "Easy difficulty star icon"},
        {"name": "hard", "description": "Hard difficulty lightning bolt icon"},
    ]
    print(f"  INPUT:  icons={[i['name'] for i in icons]}")
    t = time.time()
    try:
        urls = await svc.generate_icon_set(game_id="test_core_icons", icons=icons)
        print(f"  Time: {_elapsed(t)}")
        print(f"  OUTPUT: {len(urls)} icons")
        for name, url in urls.items():
            print(f"    {name}: {url}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- 5d: generate_zoom_crops ---
    _subheader("5d. generate_zoom_crops — crop zones from diagram")
    diagram_path = RESULTS_DIR.parent / "test_core_diagram" / "diagram.png"
    if diagram_path.exists():
        zones_path = RESULTS_DIR.parent / "test_core_diagram" / "zones.json"
        zones = json.loads(zones_path.read_text())["zones"] if zones_path.exists() else None
        print(f"  INPUT:  diagram from 5a + {len(zones) if zones else 0} zones")
        t = time.time()
        try:
            urls = await svc.generate_zoom_crops(
                game_id="test_core_diagram",
                diagram_bytes=diagram_path.read_bytes(),
                zones=zones,
            )
            print(f"  Time: {_elapsed(t)}")
            print(f"  OUTPUT: {len(urls)} crops")
            for zid, url in urls.items():
                print(f"    {zid}: {url}")
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print("  SKIPPED: No diagram from 5a")

    print("\n  ✓ AssetGenService tests complete")
    return True


# ─── Main ─────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Test Asset Generation Service")
    parser.add_argument(
        "--component", "-c",
        choices=["search", "gemini", "imagen", "svg", "core", "all"],
        default="all",
        help="Which component to test (default: all)",
    )
    args = parser.parse_args()

    # Check API keys
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY not set")
        sys.exit(1)
    if not os.getenv("SERPER_API_KEY"):
        print("WARNING: SERPER_API_KEY not set — search tests will fail")

    print(f"\nAsset Generation Service Tests")
    print(f"Output directory: {RESULTS_DIR}")
    print(f"Component: {args.component}")

    test_map = {
        "search": test_search,
        "gemini": test_gemini,
        "imagen": test_imagen,
        "svg": test_svg,
        "core": test_core,
    }

    if args.component == "all":
        # Run in order: search first (creates reference image), then rest
        for name, func in test_map.items():
            try:
                await func()
            except Exception as e:
                print(f"\n  ✗ {name} FAILED: {e}")
                import traceback; traceback.print_exc()
    else:
        await test_map[args.component]()

    print(f"\n{'='*60}")
    print(f"  All tests complete. Output at: {RESULTS_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
