"""Item Asset Worker (V4 Phase 2a+).

Enriches mechanic content items with locally-generated images using
Gemini's style-consistent set generation. All items in a mechanic share
a consistent visual style via multi-turn chat.

Runs between content_merge and interaction_dispatch.
Only processes mechanics where creative_design.needs_item_images is true.
If no items need images, returns immediately with no state changes.

Field name mapping (backend → frontend):
- sequencing: items[].image_description → items[].image (frontend: item.image)
- branching_scenario: nodes[].image_description → nodes[].imageUrl (frontend: node.imageUrl)
- memory_match: pairs[].front = description → pairs[].front = URL (frontend: card.content)
- sorting_categories: items[].image_description → items[].image (frontend: item.image)

State reads: mechanic_contents, game_plan, _run_id
State writes: mechanic_contents (enriched with image URLs)
"""

import asyncio
import time
from typing import Any

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.v4.item_asset_worker")

# Max concurrent image searches to avoid rate limits (fallback only)
_SEARCH_SEMAPHORE = asyncio.Semaphore(3)
_SEARCH_DELAY = 0.3  # seconds between searches


async def item_asset_worker(state: dict) -> dict:
    """Enrich mechanic content items with image URLs.

    Uses Gemini generate_style_consistent_set() to produce locally-stored
    images with a consistent visual style across all items in a mechanic.
    Falls back to Serper image search if Gemini generation fails.

    Returns immediately if no items need images.
    """
    mechanic_contents = state.get("mechanic_contents") or []
    game_plan = state.get("game_plan")
    run_id = state.get("_run_id") or ""
    sub_stages: list[dict[str, Any]] = []

    if not mechanic_contents or not game_plan:
        return {}

    # Build lookup: mechanic_id → creative_design from game_plan
    needs_images_map = _build_needs_images_map(game_plan)

    if not needs_images_map:
        logger.info("No mechanics need item images, skipping")
        return {}

    logger.info(
        f"Item asset worker: {len(needs_images_map)} mechanics need item images"
    )

    t0 = time.time()
    enriched_contents = []
    total_searched = 0
    total_found = 0

    for mc in mechanic_contents:
        mechanic_id = mc.get("mechanic_id", "")
        mechanic_type = mc.get("mechanic_type", "")

        if mechanic_id not in needs_images_map:
            enriched_contents.append(mc)
            continue

        if mc.get("status") == "failed":
            enriched_contents.append(mc)
            continue

        image_style = needs_images_map[mechanic_id]
        content = mc.get("content", {})

        searched, found = await _enrich_mechanic_content(
            mechanic_type, content, image_style, run_id
        )
        total_searched += searched
        total_found += found

        # Write back enriched content
        enriched_mc = dict(mc)
        enriched_mc["content"] = content
        enriched_contents.append(enriched_mc)

        sub_stages.append({
            "id": f"item_assets_{mechanic_id}",
            "name": f"Item images ({mechanic_id})",
            "type": "item_image_generation",
            "status": "success" if found > 0 else ("degraded" if searched > 0 else "skipped"),
            "duration_ms": 0,  # set below
            "model": "gemini-2.5-flash-image",
            "output_summary": {
                "searched": searched,
                "found": found,
                "mechanic_type": mechanic_type,
            },
        })

    elapsed_ms = int((time.time() - t0) * 1000)
    for ss in sub_stages:
        ss["duration_ms"] = elapsed_ms // max(len(sub_stages), 1)

    logger.info(
        f"Item asset worker done: {total_found}/{total_searched} images generated "
        f"in {elapsed_ms}ms"
    )

    result: dict[str, Any] = {
        "mechanic_contents": enriched_contents,
    }
    if sub_stages:
        result["_sub_stages"] = sub_stages
    return result


def _build_needs_images_map(game_plan: dict) -> dict[str, str]:
    """Build map of mechanic_id → item_image_style for mechanics needing images."""
    result: dict[str, str] = {}
    for scene in game_plan.get("scenes", []):
        for mech in scene.get("mechanics", []):
            creative = mech.get("creative_design", {})
            if isinstance(creative, dict) and creative.get("needs_item_images"):
                mid = mech.get("mechanic_id", "")
                style = creative.get("item_image_style", "educational illustration")
                if mid:
                    result[mid] = style
    return result


async def _enrich_mechanic_content(
    mechanic_type: str,
    content: dict,
    image_style: str,
    run_id: str,
) -> tuple[int, int]:
    """Enrich a mechanic's content dict with image URLs in-place.

    Returns (total_count, generated_count).
    """
    if mechanic_type == "sequencing":
        return await _enrich_sequencing(content, image_style, run_id)
    elif mechanic_type == "branching_scenario":
        return await _enrich_branching(content, image_style, run_id)
    elif mechanic_type == "memory_match":
        return await _enrich_memory_match(content, image_style, run_id)
    elif mechanic_type == "sorting_categories":
        return await _enrich_sorting(content, image_style, run_id)
    else:
        logger.info(f"Item images not supported for {mechanic_type}")
        return 0, 0


async def _fetch_reference_image(
    gen_items: list[dict],
    image_style: str,
    reference_hint: str = "diagram",
) -> bytes | None:
    """Fetch a single Serper reference image to ground the Gemini generation.

    Searches for a high-level image showing the overall concept
    (e.g. "prophase, metaphase, anaphase stages diagram") rather than
    individual items.

    Args:
        gen_items: Items whose names form the topic query.
        image_style: Style string (e.g. "educational illustration").
        reference_hint: Mechanic-specific suffix for the search query
            (e.g. "sequence stages diagram", "sorting categories chart").
    """
    try:
        from app.services.asset_gen.search import ImageSearcher

        searcher = ImageSearcher()

        # Build a topic-level query from the item names
        item_names = [gi["name"] for gi in gen_items[:5]]
        topic = ", ".join(item_names)
        query = f"{topic} {image_style} {reference_hint}"

        logger.info(f"Searching Serper for reference image: {query[:80]}")

        result = await searcher.search_and_download_best(
            query=query,
            num_results=5,
        )

        if result:
            ref_bytes, metadata = result
            logger.info(
                f"Found reference image ({len(ref_bytes)} bytes) "
                f"from {metadata.get('source_url', '?')[:60]}"
            )
            return ref_bytes

        logger.info("No suitable reference image found, proceeding without")
        return None

    except Exception as e:
        logger.warning(f"Reference image search failed: {e}")
        return None


async def _generate_item_images(
    gen_items: list[dict],
    image_style: str,
    run_id: str,
    aspect_ratio: str = "4:3",
    reference_hint: str = "diagram",
) -> list[str | None]:
    """Fetch a Serper reference, then generate a style-consistent set via Gemini.

    Flow:
    1. Search Serper for ONE reference image showing the overall concept
    2. Pass reference to Gemini generate_style_consistent_set() to ground the style
    3. Save each generated image locally via AssetStorage

    Args:
        gen_items: List of dicts with 'name', 'description', and 'item_id' keys.
        image_style: Style description for Gemini (e.g. "educational illustration").
        run_id: Pipeline run ID used as game_id for AssetStorage.
        aspect_ratio: Aspect ratio for generated images.
        reference_hint: Mechanic-specific suffix for the Serper reference query.

    Returns:
        List of local URL strings (or None for failed items), one per gen_item.
    """
    if not gen_items or not run_id:
        return [None] * len(gen_items)

    try:
        from app.services.asset_gen.gemini_image import GeminiImageEditor
        from app.services.asset_gen.storage import AssetStorage

        editor = GeminiImageEditor()
        storage = AssetStorage()

        # Step 1: Fetch a single Serper reference image for visual grounding
        reference_bytes = await _fetch_reference_image(
            gen_items, image_style, reference_hint
        )

        # Step 2: Generate style-consistent set with Gemini
        set_items = [
            {"name": gi["name"], "description": gi.get("description", "")}
            for gi in gen_items
        ]

        logger.info(
            f"Generating {len(set_items)} style-consistent images "
            f"(style={image_style!r}, ratio={aspect_ratio}, "
            f"reference={'yes' if reference_bytes else 'no'})"
        )

        image_bytes_list = await editor.generate_style_consistent_set(
            items=set_items,
            style_description=image_style,
            aspect_ratio=aspect_ratio,
            reference_image=reference_bytes,
        )

        # Step 3: Save each image locally
        urls: list[str | None] = []
        for idx, gi in enumerate(gen_items):
            if idx < len(image_bytes_list) and image_bytes_list[idx]:
                item_id = gi.get("item_id", f"item_{idx}")
                filename = f"{item_id}.png"
                url = storage.save_image(
                    game_id=run_id,
                    filename=filename,
                    data=image_bytes_list[idx],
                    subdir="items",
                )
                urls.append(url)
                logger.debug(f"Saved item image: {url}")
            else:
                urls.append(None)

        generated = sum(1 for u in urls if u is not None)
        logger.info(f"Generated {generated}/{len(gen_items)} item images via Gemini")
        return urls

    except Exception as e:
        logger.warning(f"Gemini batch generation failed: {e}", exc_info=True)
        return [None] * len(gen_items)


async def _enrich_sequencing(
    content: dict, image_style: str, run_id: str
) -> tuple[int, int]:
    """Enrich sequencing items: image_description → image (frontend field name).

    Uses Gemini style-consistent generation for all items at once.
    Falls back to Serper search for any items Gemini couldn't generate.
    """
    items = content.get("items", [])
    pending = []
    for item in items:
        desc = item.get("image_description")
        if desc and not item.get("image"):
            pending.append(item)

    if not pending:
        return 0, 0

    # Build generation request
    gen_items = [
        {
            "name": item.get("content", item.get("text", f"step {i+1}")),
            "description": item.get("image_description", ""),
            "item_id": item.get("id", f"s{i+1}"),
        }
        for i, item in enumerate(pending)
    ]

    urls = await _generate_item_images(
        gen_items, image_style, run_id, "4:3",
        reference_hint="sequence stages diagram",
    )

    found = 0
    for item, url in zip(pending, urls):
        if url:
            item["image"] = url
            found += 1
        else:
            # Fallback to Serper for this item
            fallback = await _search_image(
                item.get("image_description", ""), image_style
            )
            if fallback:
                item["image"] = fallback
                found += 1

    return len(pending), found


async def _enrich_branching(
    content: dict, image_style: str, run_id: str
) -> tuple[int, int]:
    """Enrich branching nodes: image_description → imageUrl (frontend field name).

    Uses Gemini style-consistent generation, falls back to Serper.
    """
    nodes = content.get("nodes", [])
    pending = []
    for node in nodes:
        desc = node.get("image_description")
        if desc and not node.get("imageUrl"):
            pending.append(node)

    if not pending:
        return 0, 0

    gen_items = [
        {
            "name": node.get("title", node.get("content", f"node {i+1}")),
            "description": node.get("image_description", ""),
            "item_id": node.get("id", f"b{i+1}"),
        }
        for i, node in enumerate(pending)
    ]

    urls = await _generate_item_images(
        gen_items, image_style, run_id, "4:3",
        reference_hint="decision tree branching scenario",
    )

    found = 0
    for node, url in zip(pending, urls):
        if url:
            node["imageUrl"] = url
            found += 1
        else:
            fallback = await _search_image(
                node.get("image_description", ""), image_style
            )
            if fallback:
                node["imageUrl"] = fallback
                found += 1

    return len(pending), found


async def _enrich_memory_match(
    content: dict, image_style: str, run_id: str
) -> tuple[int, int]:
    """Enrich memory match pairs where frontType='image'.

    Uses Gemini with 1:1 aspect ratio for square memory cards.
    Falls back to Serper for failed items.
    """
    pairs = content.get("pairs", [])
    pending = []
    for pair in pairs:
        if pair.get("frontType") == "image" and not pair.get("_image_resolved"):
            desc = pair.get("front", "")
            if desc:
                pending.append(pair)

    if not pending:
        return 0, 0

    gen_items = [
        {
            "name": pair.get("back", pair.get("front", f"card {i+1}")),
            "description": pair.get("front", ""),
            "item_id": f"mem{i+1}",
        }
        for i, pair in enumerate(pending)
    ]

    urls = await _generate_item_images(
        gen_items, image_style, run_id, "1:1",
        reference_hint="matching pairs memory cards",
    )

    found = 0
    for pair, url in zip(pending, urls):
        desc = pair.get("front", "")
        if url:
            pair["front_description"] = desc
            pair["front"] = url
            pair["_image_resolved"] = True
            found += 1
        else:
            fallback = await _search_image(desc, image_style)
            if fallback:
                pair["front_description"] = desc
                pair["front"] = fallback
                pair["_image_resolved"] = True
                found += 1

    return len(pending), found


async def _enrich_sorting(
    content: dict, image_style: str, run_id: str
) -> tuple[int, int]:
    """Enrich sorting items: image_description → image (frontend field name).

    Uses Gemini style-consistent generation, falls back to Serper.
    """
    items = content.get("items", [])
    pending = []
    for item in items:
        desc = item.get("image_description")
        if desc and not item.get("image"):
            pending.append(item)

    if not pending:
        return 0, 0

    gen_items = [
        {
            "name": item.get("content", item.get("text", f"item {i+1}")),
            "description": item.get("image_description", ""),
            "item_id": item.get("id", f"sort{i+1}"),
        }
        for i, item in enumerate(pending)
    ]

    urls = await _generate_item_images(
        gen_items, image_style, run_id, "4:3",
        reference_hint="sorting categories classification chart",
    )

    found = 0
    for item, url in zip(pending, urls):
        if url:
            item["image"] = url
            found += 1
        else:
            fallback = await _search_image(
                item.get("image_description", ""), image_style
            )
            if fallback:
                item["image"] = fallback
                found += 1

    return len(pending), found


async def _search_image(description: str, image_style: str) -> str | None:
    """Search for a single image matching the description (fallback path)."""
    async with _SEARCH_SEMAPHORE:
        try:
            from app.services.asset_gen.search import ImageSearcher

            searcher = ImageSearcher()
            query = f"{description} {image_style}"
            result = await searcher.search_and_download_best(
                query=query,
                num_results=5,
            )

            if result:
                _, metadata = result
                url = metadata.get("image_url")
                if url:
                    return url

            return None

        except Exception as e:
            logger.warning(f"Image search failed for '{description[:50]}': {e}")
            return None
        finally:
            await asyncio.sleep(_SEARCH_DELAY)
