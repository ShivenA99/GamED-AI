"""Core asset generation service — orchestrates all generators.

This is the main entry point for spec-driven asset generation. Each method
implements a high-level workflow that combines search, generation, editing,
and storage into a single operation returning frontend-ready asset URLs.

Workflow:  Spec → Search reference → Gemini re-generate → Store → URL
"""

import asyncio
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image

from .gemini_image import GeminiImageEditor
from .imagen import ImagenGenerator
from .search import ImageSearcher
from .segmentation import LocalSegmentationService
from .storage import AssetStorage
from .svg_gen import SVGGenerator

logger = logging.getLogger("gamed_ai.asset_gen.core")


class AssetGenService:
    """Spec-based multi-media asset generation for interactive diagram games.

    All methods follow the pattern:
        search reference image → Gemini re-generate/edit → save to disk → return URL

    This ensures every asset is:
    - Original (not directly using web images)
    - Customized (Gemini generates from spec, not just cleans)
    - Cached (stored locally, served via /api/assets/)
    """

    def __init__(self):
        self.searcher = ImageSearcher()
        self.gemini = GeminiImageEditor()
        self.imagen = ImagenGenerator()
        self.svg = SVGGenerator()
        self.storage = AssetStorage()
        self.segmentation = LocalSegmentationService()

    # ─── Diagram Workflows ────────────────────────────────────────

    async def generate_diagram(
        self,
        game_id: str,
        subject: str,
        structures: list[str],
        style: str = "clean educational cross-section illustration",
        search_query: str | None = None,
    ) -> dict:
        """Generate a clean diagram image with detected zones.

        Workflow:
        1. Search for a labeled reference diagram
        2. Use Gemini to re-generate a clean, custom version
        3. Use Gemini vision to detect zone positions
        4. Save diagram + zones, return URLs

        Args:
            game_id: Unique game identifier for storage
            subject: What to draw (e.g., "human heart anatomy")
            structures: List of structures to detect as zones
            style: Visual style description
            search_query: Custom search query (auto-generated if None)

        Returns:
            {diagram_url, zones: [{id, label, x, y, radius, shape, description}]}
        """
        logger.info(f"Generating diagram for '{subject}' with {len(structures)} structures")

        # Step 1: Search for reference
        query = search_query or f"{subject} labeled diagram educational detailed"
        ref_result = await self.searcher.search_and_download_best(
            query,
            fallback_queries=[
                f"{subject} anatomy diagram labeled",
                f"{subject} diagram parts illustration",
            ],
        )

        # Step 2: Re-generate via Gemini (or generate from scratch via Imagen)
        if ref_result:
            ref_bytes, ref_meta = ref_result
            logger.info(f"Using reference from: {ref_meta.get('source_url', 'unknown')[:60]}")
            diagram_bytes = await self.gemini.regenerate_from_reference(
                ref_bytes,
                prompt=(
                    f"A {style} of {subject}, clearly showing: {', '.join(structures)}. "
                    f"Anatomically accurate, high contrast, white background, textbook quality."
                ),
            )
        else:
            logger.warning("No reference found, generating from scratch with Imagen")
            diagram_bytes = await self.imagen.generate_educational_diagram(
                subject=subject,
                structures=structures,
                style=style,
                include_labels=False,
            )

        # Step 3: Save diagram
        diagram_url = self.storage.save_image(game_id, "diagram.png", diagram_bytes)

        # Step 4: Detect zones — Gemini Box2d → SAM3 guided segmentation
        zones = []
        context = f"Educational diagram of {subject}"
        try:
            # Stage A: Gemini 3 Flash bounding box detection (semantic, ~3-7s)
            boxes = await self.gemini.detect_bounding_boxes(
                diagram_bytes, structures, context=context,
                model="gemini-3-flash-preview",
            )
            if boxes:
                # Build guide_boxes: first instance per label
                guide_boxes = {}
                for b in boxes:
                    label = b["label"]
                    if label not in guide_boxes:
                        guide_boxes[label] = {
                            "x": b["x"], "y": b["y"],
                            "width": b["width"], "height": b["height"],
                        }

                # Stage B: SAM3 pixel-precise segmentation with box guidance (~10-20s)
                sam_zones = await self.segmentation.detect_zones_guided(
                    diagram_bytes, structures, guide_boxes, context=context,
                )
                if sam_zones:
                    zones = sam_zones
                    logger.info(f"Box2d→SAM3: {len(zones)}/{len(structures)} zones")
                else:
                    logger.warning("SAM3 guided returned no zones, using Gemini boxes as fallback")
        except Exception as e:
            logger.warning(f"Box2d→SAM3 pipeline failed: {e}")

        # Fallback: Gemini text-based zone detection
        if not zones:
            logger.info("Falling back to Gemini text zone detection")
            zones = await self.gemini.detect_zones(
                diagram_bytes,
                expected_labels=structures,
                context=context,
            )

        # Save zones
        self.storage.save_json(game_id, "zones.json", {"zones": zones})

        logger.info(f"Diagram complete: {len(zones)} zones detected")
        return {
            "diagram_url": diagram_url,
            "zones": zones,
        }

    # ─── Item Illustration Workflows ──────────────────────────────

    async def generate_item_illustrations(
        self,
        game_id: str,
        items: list[dict],
        style: str = "scientific illustration",
        category: str = "biology",
        aspect_ratio: str = "1:1",
    ) -> dict[str, str]:
        """Generate a style-consistent set of item illustrations.

        Each item gets a unique illustration that matches the others in style.
        Workflow: Search references → Gemini multi-turn consistent set → save

        Args:
            game_id: Game identifier
            items: List of {name, description} dicts
            style: Visual style for all items
            category: Educational category context
            aspect_ratio: Image aspect ratio

        Returns:
            Dict mapping item name to URL path
        """
        logger.info(f"Generating {len(items)} item illustrations for {game_id}")

        # Use Gemini multi-turn chat for style consistency
        image_set = await self.gemini.generate_style_consistent_set(
            items=items,
            style_description=f"{style}, {category} theme",
            aspect_ratio=aspect_ratio,
        )

        urls = {}
        for i, item in enumerate(items):
            if i < len(image_set):
                filename = f"item_{i:03d}_{self._slugify(item['name'])}.png"
                url = self.storage.save_image(game_id, filename, image_set[i], subdir="items")
                urls[item["name"]] = url

        logger.info(f"Generated {len(urls)}/{len(items)} item illustrations")
        return urls

    async def generate_item_from_reference(
        self,
        game_id: str,
        item_name: str,
        search_query: str,
        regen_prompt: str,
        filename: str | None = None,
        subdir: str = "items",
        transparent: bool = False,
    ) -> str | None:
        """Search for a reference, re-generate via Gemini, save.

        This is the core search→regenerate→save pattern for a single item.

        Args:
            game_id: Game identifier
            item_name: Name for the item
            search_query: What to search for
            regen_prompt: Prompt for Gemini regeneration
            filename: Output filename (auto-generated if None)
            subdir: Storage subdirectory
            transparent: If True, remove white background to make transparent PNG

        Returns:
            URL path or None if failed
        """
        ref = await self.searcher.search_and_download_best(search_query)
        if not ref:
            logger.warning(f"No reference found for '{item_name}'")
            return None

        ref_bytes, _ = ref
        regen_bytes = await self.gemini.regenerate_from_reference(ref_bytes, regen_prompt)

        if transparent:
            regen_bytes = self._remove_background(regen_bytes)

        fname = filename or f"{self._slugify(item_name)}.png"
        return self.storage.save_image(game_id, fname, regen_bytes, subdir=subdir)

    @staticmethod
    def _remove_background(image_bytes: bytes, threshold: int = 240) -> bytes:
        """Remove near-white background from image, producing transparent PNG."""
        img = Image.open(BytesIO(image_bytes)).convert("RGBA")
        data = img.getdata()
        new_data = []
        for r, g, b, a in data:
            # If pixel is near-white, make transparent
            if r > threshold and g > threshold and b > threshold:
                new_data.append((r, g, b, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def generate_items_from_references(
        self,
        game_id: str,
        items: list[dict],
        search_template: str = "{name} {category} educational illustration",
        regen_template: str = "A clean scientific illustration of {name}. {description}. White background, no text.",
        category: str = "",
        subdir: str = "items",
        transparent: bool = False,
    ) -> dict[str, str]:
        """Generate multiple items by searching references and re-generating each.

        Args:
            game_id: Game identifier
            items: List of {name, description} dicts
            search_template: Search query template with {name}, {category}
            regen_template: Regeneration prompt template with {name}, {description}
            category: Educational category
            subdir: Storage subdirectory
            transparent: If True, remove white background for transparent PNGs

        Returns:
            Dict mapping item name to URL
        """
        sem = asyncio.Semaphore(2)  # Limit concurrency for API rate limits

        async def _gen_one(item):
            async with sem:
                query = search_template.format(name=item["name"], category=category)
                prompt = regen_template.format(
                    name=item["name"],
                    description=item.get("description", ""),
                )
                url = await self.generate_item_from_reference(
                    game_id, item["name"], query, prompt,
                    subdir=subdir, transparent=transparent,
                )
                return item["name"], url

        tasks = [_gen_one(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        urls = {}
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"Item generation failed: {r}")
                continue
            name, url = r
            if url:
                urls[name] = url

        logger.info(f"Generated {len(urls)}/{len(items)} items from references")
        return urls

    # ─── SVG Workflows ────────────────────────────────────────────

    async def generate_icon_set(
        self,
        game_id: str,
        icons: list[dict],
        style: str = "flat, modern, educational",
        size: int = 48,
    ) -> dict[str, str]:
        """Generate a consistent set of SVG icons.

        Args:
            game_id: Game identifier
            icons: List of {name, description} dicts
            style: Visual style
            size: Icon size

        Returns:
            Dict mapping icon name to URL path
        """
        svg_code_map = await self.svg.generate_icon_set(icons, size=size, style=style)

        urls = {}
        for name, code in svg_code_map.items():
            filename = f"{self._slugify(name)}.svg"
            url = self.storage.save_svg(game_id, filename, code, subdir="icons")
            urls[name] = url

        return urls

    async def generate_card_back(
        self,
        game_id: str,
        theme: str,
        colors: list[str] | None = None,
    ) -> str:
        """Generate an SVG card back pattern.

        Returns:
            URL path to the SVG file
        """
        svg_code = await self.svg.generate_card_back_pattern(theme, colors=colors)
        return self.storage.save_svg(game_id, "card_back.svg", svg_code, subdir="patterns")

    async def generate_connectors(
        self,
        game_id: str,
        count: int = 1,
        connector_type: str = "arrow",
        color: str = "#6366f1",
    ) -> list[str]:
        """Generate SVG connector arrows.

        Returns:
            List of URL paths
        """
        urls = []
        for i in range(count):
            svg_code = await self.svg.generate_connector_svg(
                connector_type=connector_type, color=color,
            )
            filename = f"connector_{i:02d}.svg"
            url = self.storage.save_svg(game_id, filename, svg_code, subdir="connectors")
            urls.append(url)
        return urls

    async def generate_particle_sprites(
        self,
        game_id: str,
        themes: list[str],
        colors: list[str] | None = None,
    ) -> dict[str, str]:
        """Generate particle effect sprites.

        Args:
            themes: List of sprite themes (e.g., ["sparkle", "droplet"])
            colors: Colors for each sprite (defaults to gold)

        Returns:
            Dict mapping theme to URL
        """
        colors = colors or ["#fbbf24"] * len(themes)
        urls = {}
        for theme, color in zip(themes, colors):
            svg_code = await self.svg.generate_particle_sprite(theme=theme, color=color)
            filename = f"particle_{self._slugify(theme)}.svg"
            url = self.storage.save_svg(game_id, filename, svg_code, subdir="particles")
            urls[theme] = url
        return urls

    # ─── Image Processing Workflows ───────────────────────────────

    async def generate_zoom_crops(
        self,
        game_id: str,
        diagram_bytes: bytes | None = None,
        zones: list[dict] | None = None,
        padding_pct: float = 15.0,
    ) -> dict[str, str]:
        """Generate pre-rendered zoom crops of diagram zones.

        If diagram_bytes not provided, loads from storage.

        Args:
            game_id: Game identifier
            diagram_bytes: Full diagram image bytes
            zones: Zone list with x, y, radius (0-100 percentages)
            padding_pct: Extra padding around zone center

        Returns:
            Dict mapping zone_id to crop URL
        """
        if diagram_bytes is None:
            diagram_path = self.storage.get_asset_path(game_id, "diagram.png")
            if not diagram_path.exists():
                logger.error(f"No diagram found for {game_id}")
                return {}
            diagram_bytes = diagram_path.read_bytes()

        if zones is None:
            zones_path = self.storage.get_asset_path(game_id, "zones.json")
            if zones_path.exists():
                import json
                zones = json.loads(zones_path.read_text()).get("zones", [])
            else:
                return {}

        img = Image.open(BytesIO(diagram_bytes))
        w, h = img.size
        urls = {}

        for zone in zones:
            zid = zone.get("id", f"zone_{zone.get('label', 'unknown')}")
            cx = zone["x"] / 100.0 * w
            cy = zone["y"] / 100.0 * h
            radius = zone.get("radius", 5) / 100.0 * w

            # Crop box with padding
            pad = padding_pct / 100.0 * w
            size = max(radius * 2 + pad * 2, w * 0.15)  # At least 15% of image
            x1 = max(0, cx - size / 2)
            y1 = max(0, cy - size / 2)
            x2 = min(w, cx + size / 2)
            y2 = min(h, cy + size / 2)

            crop = img.crop((int(x1), int(y1), int(x2), int(y2)))
            # Resize to standard size for consistency
            crop = crop.resize((400, 400), Image.Resampling.LANCZOS)

            buf = BytesIO()
            crop.save(buf, format="PNG")
            filename = f"{self._slugify(zid)}.png"
            url = self.storage.save_image(game_id, filename, buf.getvalue(), subdir="crops")
            urls[zid] = url

        logger.info(f"Generated {len(urls)} zoom crops")
        return urls

    # ─── Trace Path Workflow ──────────────────────────────────────

    async def generate_trace_path_data(
        self,
        game_id: str,
        path_description: str,
        waypoint_labels: list[str],
        diagram_bytes: bytes | None = None,
    ) -> dict:
        """Detect path waypoints and SVG path curves on a diagram.

        Args:
            game_id: Game identifier
            path_description: What path to trace
            waypoint_labels: Ordered list of waypoint names
            diagram_bytes: Diagram image bytes (loads from storage if None)

        Returns:
            {waypoints: [{label, x, y, svg_path_to_next}]}
        """
        if diagram_bytes is None:
            diagram_path = self.storage.get_asset_path(game_id, "diagram.png")
            diagram_bytes = diagram_path.read_bytes()

        waypoints = await self.gemini.trace_paths_on_diagram(
            diagram_bytes, path_description, waypoint_labels,
        )

        self.storage.save_json(game_id, "path_data.json", {
            "description": path_description,
            "waypoints": waypoints,
        })

        return {"waypoints": waypoints}

    # ─── Full Mechanic Asset Workflows ────────────────────────────

    async def build_drag_drop_assets(
        self,
        game_id: str,
        subject: str,
        labels: list[dict],
        style: str = "clean educational cross-section illustration",
    ) -> dict:
        """Complete asset generation for a drag_drop game.

        Generates: diagram, zones, per-label thumbnails, SVG icons, zoom crops.

        Args:
            subject: Diagram subject
            labels: [{name, description, category}]
            style: Visual style

        Returns:
            {diagram_url, zones, label_thumbnails, icons, zoom_crops}
        """
        # Diagram + zones
        diagram_result = await self.generate_diagram(
            game_id, subject,
            structures=[l["name"] for l in labels],
            style=style,
        )

        # Per-label thumbnail illustrations
        thumbnails = await self.generate_item_illustrations(
            game_id, labels,
            style="small anatomical illustration",
            category=subject,
            aspect_ratio="1:1",
        )

        # SVG icons per category
        categories = list({l.get("category", "General") for l in labels})
        cat_icons = await self.generate_icon_set(
            game_id,
            [{"name": c, "description": f"Icon for {c} category"} for c in categories],
        )

        # Zoom crops
        diagram_path = self.storage.get_asset_path(game_id, "diagram.png")
        zoom_crops = await self.generate_zoom_crops(
            game_id,
            diagram_bytes=diagram_path.read_bytes() if diagram_path.exists() else None,
            zones=diagram_result["zones"],
        )

        return {
            **diagram_result,
            "label_thumbnails": thumbnails,
            "category_icons": cat_icons,
            "zoom_crops": zoom_crops,
        }

    async def build_sequencing_assets(
        self,
        game_id: str,
        steps: list[dict],
        theme: str = "biology",
        style: str = "clean scientific illustration",
    ) -> dict:
        """Complete asset generation for a sequencing game.

        Generates: per-step illustrations, connector SVGs, timeline icon.

        Args:
            steps: [{name, description}]
            theme: Educational theme
            style: Visual style

        Returns:
            {step_images, connectors, icons}
        """
        # Style-consistent step illustrations
        step_images = await self.generate_item_illustrations(
            game_id, steps, style=style, category=theme, aspect_ratio="4:3",
        )

        # Connector arrows
        connectors = await self.generate_connectors(game_id, count=1, color="#6366f1")

        # Step icons
        icons = await self.generate_icon_set(
            game_id,
            [{"name": s["name"], "description": s.get("description", "")} for s in steps],
            style="flat, colorful, educational",
        )

        return {
            "step_images": step_images,
            "connectors": connectors,
            "icons": icons,
        }

    async def build_sorting_assets(
        self,
        game_id: str,
        items: list[dict],
        categories: list[dict],
        theme: str = "biology",
    ) -> dict:
        """Complete asset generation for a sorting/categories game.

        Generates: per-item images, category header icons, card back pattern.

        Args:
            items: [{name, description, category}]
            categories: [{name, color, description}]
            theme: Educational theme

        Returns:
            {item_images, category_icons, card_back}
        """
        # Item illustrations via search+regenerate
        item_images = await self.generate_items_from_references(
            game_id, items,
            search_template=f"{{name}} {theme} microscope illustration",
            regen_template=(
                "A clean scientific illustration of {name}. {description}. "
                "White background, detailed, textbook quality, no text."
            ),
            category=theme,
        )

        # Category header icons
        cat_icons = await self.generate_icon_set(
            game_id,
            [{"name": c["name"], "description": c.get("description", "")} for c in categories],
        )

        # Card back pattern
        card_back = await self.generate_card_back(
            game_id, theme=theme,
            colors=[c.get("color", "#6366f1") for c in categories],
        )

        return {
            "item_images": item_images,
            "category_icons": cat_icons,
            "card_back": card_back,
        }

    async def build_memory_match_assets(
        self,
        game_id: str,
        pairs: list[dict],
        theme: str = "human body systems",
    ) -> dict:
        """Complete asset generation for a memory match game.

        Generates: per-pair front images, card back SVG, celebration sprites.

        Args:
            pairs: [{name, description, explanation}]
            theme: Educational theme

        Returns:
            {pair_images, card_back, celebration_sprites}
        """
        # Per-pair front images
        pair_images = await self.generate_items_from_references(
            game_id, pairs,
            search_template=f"{{name}} {theme} educational illustration",
            regen_template=(
                "A clear educational illustration of {name}. {description}. "
                "Centered, white background, colorful, no text labels."
            ),
            category=theme,
            subdir="pairs",
        )

        # Card back pattern
        card_back = await self.generate_card_back(
            game_id, theme=theme, colors=["#6366f1", "#8b5cf6", "#a855f7"],
        )

        # Celebration particle sprites
        celebration = await self.generate_particle_sprites(
            game_id,
            themes=["sparkle", "star", "confetti"],
            colors=["#fbbf24", "#22c55e", "#6366f1"],
        )

        return {
            "pair_images": pair_images,
            "card_back": card_back,
            "celebration_sprites": celebration,
        }

    async def build_click_to_identify_assets(
        self,
        game_id: str,
        subject: str,
        structures: list[str],
        style: str = "clean educational cross-section illustration",
    ) -> dict:
        """Complete asset generation for click_to_identify.

        Generates: diagram, zones, zoom crops for magnification.

        Returns:
            {diagram_url, zones, zoom_crops}
        """
        diagram_result = await self.generate_diagram(
            game_id, subject, structures=structures, style=style,
        )

        diagram_path = self.storage.get_asset_path(game_id, "diagram.png")
        zoom_crops = await self.generate_zoom_crops(
            game_id,
            diagram_bytes=diagram_path.read_bytes() if diagram_path.exists() else None,
            zones=diagram_result["zones"],
        )

        return {
            **diagram_result,
            "zoom_crops": zoom_crops,
        }

    async def build_trace_path_assets(
        self,
        game_id: str,
        subject: str,
        waypoint_labels: list[str],
        path_description: str,
        style: str = "clean educational illustration",
    ) -> dict:
        """Complete asset generation for trace_path.

        Generates: diagram, zones, path data, particle sprites.

        Returns:
            {diagram_url, zones, path_data, particle_sprites}
        """
        # Diagram + zones (waypoints as zones)
        diagram_result = await self.generate_diagram(
            game_id, subject, structures=waypoint_labels, style=style,
        )

        # Path data with SVG curves
        diagram_path = self.storage.get_asset_path(game_id, "diagram.png")
        path_data = await self.generate_trace_path_data(
            game_id, path_description, waypoint_labels,
            diagram_bytes=diagram_path.read_bytes() if diagram_path.exists() else None,
        )

        # Particle sprites
        particles = await self.generate_particle_sprites(
            game_id,
            themes=["droplet", "cell", "bubble"],
            colors=["#8b4513", "#daa520", "#228b22"],  # brown → gold → green
        )

        return {
            **diagram_result,
            "path_data": path_data,
            "particle_sprites": particles,
        }

    # ─── Utilities ────────────────────────────────────────────────

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a filesystem-safe slug."""
        slug = text.lower().strip()
        slug = slug.replace(" ", "_").replace("-", "_")
        # Remove non-alphanumeric except underscores
        slug = "".join(c for c in slug if c.isalnum() or c == "_")
        return slug[:60]  # Limit length
