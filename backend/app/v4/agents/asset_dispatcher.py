"""Asset Dispatcher (V4).

Worker node that receives a scene via Send API and:
1. Searches for a reference diagram image
2. Regenerates a clean version via Gemini (no text/labels/annotations)
3. Runs zone detection via Gemini on the clean image
4. Refines with SAM3 for pixel-precise polygon boundaries
5. Returns AssetResult dict

NEVER raises — always returns a status dict (audit 39 Finding 17).

State writes: generated_assets_raw (via Send accumulation)
Model: gemini-2.5-flash-image for regeneration, gemini-3-flash-preview for zone detection
"""

import time
from typing import Any

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.v4.asset_dispatcher")


async def asset_worker(state: dict) -> dict:
    """Process a single scene's asset needs.

    Receives via Send: {scene_id, image_spec, zone_labels, question_text, _run_id}
    Returns: {generated_assets_raw: [{scene_id, status, diagram_url, zones, match_quality}]}

    The return is wrapped in generated_assets_raw list because the state field
    uses Annotated[list, operator.add] for Send API accumulation.
    """
    scene_id = state.get("scene_id", "unknown")
    image_spec = state.get("image_spec") or {}
    zone_labels = state.get("zone_labels", [])
    question_text = state.get("question_text", "")
    run_id = state.get("_run_id", "")
    sub_stages: list[dict[str, Any]] = []

    logger.info(f"Asset worker starting for scene {scene_id}: "
                f"{len(zone_labels)} labels, spec={image_spec.get('description', 'N/A')[:50]}, "
                f"question={question_text[:50]}")

    try:
        # Step 1: Search for reference diagram image
        t0 = time.time()
        reference_url = await _search_image(image_spec, zone_labels, question_text)
        search_ms = int((time.time() - t0) * 1000)

        sub_stages.append({
            "id": f"asset_search_{scene_id}",
            "name": f"Image search ({scene_id})",
            "type": "image_search",
            "scene_id": scene_id,
            "status": "success" if reference_url else "failed",
            "duration_ms": search_ms,
            "model": "serper_image_api",
            "output_summary": {
                "found": bool(reference_url),
                "url": (reference_url[:80] + "...") if reference_url and len(reference_url) > 80 else reference_url,
            },
        })

        if not reference_url:
            logger.warning(f"No image found for scene {scene_id}, trying fallback")
            t1 = time.time()
            reference_url = await _fallback_image_search(image_spec)
            fallback_ms = int((time.time() - t1) * 1000)

            sub_stages.append({
                "id": f"asset_fallback_{scene_id}",
                "name": f"Fallback search ({scene_id})",
                "type": "image_search_fallback",
                "scene_id": scene_id,
                "status": "success" if reference_url else "failed",
                "duration_ms": fallback_ms,
                "model": "serper_image_api",
                "output_summary": {
                    "found": bool(reference_url),
                    "url": (reference_url[:80] + "...") if reference_url and len(reference_url) > 80 else reference_url,
                },
            })

        if not reference_url:
            result = _error_result(scene_id, "No diagram image found after search + fallback")
            result["_sub_stages"] = sub_stages
            return result

        # Filter out SVGs — they can't be processed by Gemini image gen
        if reference_url.lower().endswith(".svg") or ".svg?" in reference_url.lower():
            logger.warning(f"Image search returned SVG for {scene_id}, re-searching without SVG")
            reference_url = None
            # Try fallback search which may find a raster image
            t_resv = time.time()
            reference_url = await _fallback_image_search(image_spec)
            resv_ms = int((time.time() - t_resv) * 1000)
            sub_stages.append({
                "id": f"asset_svg_retry_{scene_id}",
                "name": f"SVG retry search ({scene_id})",
                "type": "image_search_svg_retry",
                "scene_id": scene_id,
                "status": "success" if reference_url else "failed",
                "duration_ms": resv_ms,
                "model": "serper_image_api",
            })
            if not reference_url or reference_url.lower().endswith(".svg"):
                result = _error_result(scene_id, "Only SVG images found — cannot process")
                result["_sub_stages"] = sub_stages
                return result

        logger.info(f"Asset worker {scene_id}: using reference URL: {reference_url[:100]}")

        # Step 2: Download reference + regenerate clean image via Gemini
        t_regen = time.time()
        clean_bytes, diagram_url = await _regenerate_clean_image(
            reference_url, image_spec, zone_labels, scene_id, run_id,
        )
        regen_ms = int((time.time() - t_regen) * 1000)

        sub_stages.append({
            "id": f"asset_regenerate_{scene_id}",
            "name": f"Image regeneration ({scene_id})",
            "type": "image_regeneration",
            "scene_id": scene_id,
            "status": "success" if clean_bytes else "degraded",
            "duration_ms": regen_ms,
            "model": "gemini-2.5-flash-image",
            "output_summary": {
                "regenerated": clean_bytes is not None,
                "diagram_url": diagram_url[:80] if diagram_url else None,
                "image_size_kb": len(clean_bytes) // 1024 if clean_bytes else 0,
            },
        })

        if not clean_bytes:
            # Regeneration failed — download reference directly as fallback
            logger.warning(f"Regeneration failed for {scene_id}, using reference image directly")
            clean_bytes = await _download_image(reference_url)
            if not clean_bytes:
                result = _error_result(scene_id, "Failed to download reference image")
                result["_sub_stages"] = sub_stages
                return result
            diagram_url = reference_url

        # Step 3: Zone detection (Gemini bboxes on clean image)
        t2 = time.time()
        zones = await _detect_zones(clean_bytes, zone_labels)
        detect_ms = int((time.time() - t2) * 1000)

        sub_stages.append({
            "id": f"asset_zone_detect_{scene_id}",
            "name": f"Zone detection ({scene_id})",
            "type": "zone_detection",
            "scene_id": scene_id,
            "status": "success" if zones else "failed",
            "duration_ms": detect_ms,
            "model": "gemini_flash",
            "output_summary": {
                "zone_count": len(zones),
                "detected_labels": [z.get("label", "") for z in zones][:10] if zones else [],
            },
        })

        if not zones:
            result = _error_result(scene_id, "Zone detection returned no zones")
            result["_sub_stages"] = sub_stages
            return result

        # Step 4: SAM3 polygon refinement (pixel-precise boundaries)
        t3 = time.time()
        original_zone_count = len(zones)
        zones = await _refine_with_sam3(clean_bytes, zone_labels, zones, scene_id=scene_id)
        sam3_ms = int((time.time() - t3) * 1000)

        # Check if SAM3 actually produced polygon zones (vs falling back to Gemini)
        sam3_polygon_count = sum(1 for z in zones if z.get("shape") == "polygon")
        sam3_refined = sam3_polygon_count > 0

        sub_stages.append({
            "id": f"asset_sam3_{scene_id}",
            "name": f"SAM3 refinement ({scene_id})",
            "type": "sam3_refinement",
            "scene_id": scene_id,
            "status": "success" if sam3_refined else "degraded",
            "duration_ms": sam3_ms,
            "model": "sam3",
            "output_summary": {
                "input_zones": original_zone_count,
                "output_zones": len(zones),
                "polygon_zones": sam3_polygon_count,
                "refined": sam3_refined,
            },
        })

        # Step 5: Quality validation
        detected_labels = {z.get("label", "").lower() for z in zones}
        expected_labels = {l.lower() for l in zone_labels}
        matched = detected_labels & expected_labels
        match_quality = len(matched) / max(len(expected_labels), 1)

        is_degraded = False
        if match_quality < 0.3:
            logger.warning(f"Low match quality for {scene_id}: {match_quality:.2f}")
            is_degraded = True

        logger.info(f"Asset worker done for {scene_id}: "
                    f"{len(zones)} zones, match={match_quality:.2f}, "
                    f"diagram_url={diagram_url[:60]}")

        result: dict[str, Any] = {
            "generated_assets_raw": [{
                "scene_id": scene_id,
                "status": "degraded" if is_degraded else "success",
                "diagram_url": diagram_url,
                "zones": zones,
                "match_quality": match_quality,
            }],
            "_sub_stages": sub_stages,
        }
        if is_degraded:
            result["is_degraded"] = True
        return result

    except Exception as e:
        logger.error(f"Asset worker failed for {scene_id}: {e}", exc_info=True)
        result = _error_result(scene_id, str(e))
        result["_sub_stages"] = sub_stages
        return result


def _error_result(scene_id: str, error: str) -> dict:
    """Return an error result — NEVER raise.

    Sets is_degraded=True so downstream nodes know the game quality is impacted.
    """
    return {
        "generated_assets_raw": [{
            "scene_id": scene_id,
            "status": "error",
            "error": error,
            "diagram_url": None,
            "zones": [],
            "match_quality": 0.0,
        }],
        "failed_asset_scene_ids": [scene_id],
        "is_degraded": True,
    }


async def _download_image(url: str) -> bytes | None:
    """Download image bytes from URL."""
    try:
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "image/*,*/*;q=0.8",
        }
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if not ct.startswith("image/") and len(resp.content) < 1000:
                logger.warning(f"Image download got non-image content-type: {ct}, size={len(resp.content)}")
                return None
            return resp.content
    except Exception as e:
        logger.warning(f"Image download failed for {url[:80]}: {e}")
        return None


async def _regenerate_clean_image(
    reference_url: str,
    image_spec: dict[str, Any],
    zone_labels: list[str],
    scene_id: str,
    run_id: str,
) -> tuple[bytes | None, str]:
    """Download reference image, regenerate a clean version via Gemini, store locally.

    Follows the V3 pattern: search → download → Gemini regenerate → save → URL.
    The regenerated image has NO text labels, NO annotations, NO watermarks.

    Returns:
        (clean_bytes, diagram_url) — bytes of the clean image + local serving URL.
        On failure: (None, reference_url) — caller should fall back to reference.
    """
    try:
        # Download reference
        ref_bytes = await _download_image(reference_url)
        if not ref_bytes:
            return None, reference_url

        # Build regeneration prompt from image_spec
        description = image_spec.get("description", "")
        structures = ", ".join(zone_labels[:15])
        subject = description or "educational diagram"

        regen_prompt = (
            f"A clean educational cross-section illustration of {subject}. "
            f"The diagram must clearly show these anatomical structures: {structures}. "
            f"CRITICAL: Do NOT include ANY text labels, annotations, arrows, leader lines, "
            f"captions, or text of any kind in the image. The image must be completely free "
            f"of text — only the illustration itself. "
            f"Anatomically accurate, high contrast, white background, "
            f"textbook quality illustration style."
        )

        from app.services.asset_gen.gemini_image import GeminiImageEditor
        editor = GeminiImageEditor()

        logger.info(f"[Regen:{scene_id}] Regenerating clean image from reference...")
        clean_bytes = await editor.regenerate_from_reference(
            reference_bytes=ref_bytes,
            prompt=regen_prompt,
        )

        # Store locally
        from app.services.asset_gen.storage import AssetStorage
        storage = AssetStorage()
        game_id = run_id or scene_id
        diagram_url = storage.save_image(game_id, f"diagram_{scene_id}.png", clean_bytes)

        logger.info(f"[Regen:{scene_id}] Clean image saved: {diagram_url} "
                    f"({len(clean_bytes) // 1024}KB)")
        return clean_bytes, diagram_url

    except Exception as e:
        logger.error(f"[Regen:{scene_id}] Image regeneration failed: {type(e).__name__}: {e}", exc_info=True)
        return None, reference_url


async def _search_image(
    image_spec: dict[str, Any],
    zone_labels: list[str],
    question_text: str = "",
) -> str | None:
    """Search for a diagram image using the image spec."""
    try:
        from app.services.image_retrieval import (
            build_image_queries,
            search_diagram_images_multi,
            select_best_image_scored,
        )

        description = image_spec.get("description", "")
        required = image_spec.get("must_include_structures", image_spec.get("required_elements", []))

        # Build search queries
        search_query = question_text or description
        if required:
            search_query += " " + " ".join(required[:5])

        queries = build_image_queries(search_query, zone_labels[:10])

        # Search
        results = await search_diagram_images_multi(
            queries=queries,
            max_results=5,
            max_queries=3,
        )

        if not results:
            return None

        # Select best
        best = select_best_image_scored(results)
        if best:
            url = best.get("image_url") or best.get("imageUrl")
            if url:
                logger.info(f"Found image: {url[:80]}...")
                return url

        return None

    except Exception as e:
        logger.warning(f"Image search failed: {e}")
        return None


async def _fallback_image_search(image_spec: dict[str, Any]) -> str | None:
    """Simplified fallback search with broader query."""
    try:
        from app.services.image_retrieval import (
            search_diagram_images,
            select_best_image_scored,
        )

        description = image_spec.get("description", "educational diagram")
        results = await search_diagram_images(
            query=f"{description} labeled diagram",
            max_results=5,
        )

        if not results:
            return None

        best = select_best_image_scored(results)
        return best.get("image_url") if best else None

    except Exception as e:
        logger.warning(f"Fallback image search failed: {e}")
        return None


async def _detect_zones(
    image_bytes: bytes,
    zone_labels: list[str],
) -> list[dict[str, Any]]:
    """Detect zones in the clean diagram image using Gemini vision.

    Takes image bytes directly (no URL download needed since we already
    have the regenerated image in memory).
    """
    try:
        from app.services.asset_gen.gemini_image import GeminiImageEditor

        editor = GeminiImageEditor()

        # Use bounding box detection (most accurate) then build zone dicts
        boxes = await editor.detect_bounding_boxes(
            image_bytes=image_bytes,
            expected_labels=zone_labels,
            context=f"Clean educational diagram showing: {', '.join(zone_labels[:10])}",
        )

        if not boxes:
            # Fallback to text-based polygon detection
            logger.info("Box detection returned no results, trying text polygon fallback")
            return await editor.detect_zones(
                image_bytes=image_bytes,
                expected_labels=zone_labels,
                context=f"Clean educational diagram showing: {', '.join(zone_labels[:10])}",
            )

        # Convert bounding boxes to zone dicts with polygon points
        zones: list[dict[str, Any]] = []
        for box in boxes:
            label = box.get("label", "")
            zone_id = f"zone_{label.lower().replace(' ', '_').replace('-', '_')}"

            # Convert bbox to 4-point polygon
            x = box.get("x", 50)
            y = box.get("y", 50)
            w = box.get("width", 10)
            h = box.get("height", 10)

            zone_dict: dict[str, Any] = {
                "id": zone_id,
                "label": label,
                "x": round(x, 1),
                "y": round(y, 1),
                "width": round(w, 1),
                "height": round(h, 1),
                "shape": "rect",
                "points": [
                    [round(x - w / 2, 1), round(y - h / 2, 1)],
                    [round(x + w / 2, 1), round(y - h / 2, 1)],
                    [round(x + w / 2, 1), round(y + h / 2, 1)],
                    [round(x - w / 2, 1), round(y + h / 2, 1)],
                ],
            }
            zones.append(zone_dict)

        return zones

    except Exception as e:
        logger.warning(f"Zone detection failed: {e}")
        return []


async def _refine_with_sam3(
    image_bytes: bytes,
    zone_labels: list[str],
    gemini_zones: list[dict[str, Any]],
    scene_id: str = "unknown",
) -> list[dict[str, Any]]:
    """Refine Gemini bounding boxes with SAM3 for pixel-precise polygon boundaries.

    Takes image bytes directly (already in memory from regeneration step).
    Uses Gemini zones as guide_boxes for SAM3's guided segmentation mode.
    Falls back to original Gemini zones if SAM3 is unavailable or fails.
    """
    try:
        from app.services.asset_gen.segmentation import LocalSegmentationService

        # Build guide_boxes from Gemini zone results: label → {x, y, radius/width/height}
        guide_boxes: dict[str, dict] = {}
        for zone in gemini_zones:
            label = zone.get("label", "")
            if not label:
                continue
            box: dict[str, Any] = {}
            if "points" in zone and zone["points"]:
                # Convert polygon to bounding box
                xs = [p[0] for p in zone["points"]]
                ys = [p[1] for p in zone["points"]]
                box = {
                    "x": min(xs),
                    "y": min(ys),
                    "width": max(xs) - min(xs),
                    "height": max(ys) - min(ys),
                }
            elif zone.get("x") is not None and zone.get("y") is not None:
                if zone.get("radius") is not None:
                    box = {"x": zone["x"], "y": zone["y"], "radius": zone["radius"]}
                elif zone.get("width") is not None:
                    box = {"x": zone["x"], "y": zone["y"], "width": zone["width"], "height": zone.get("height", zone["width"])}
            if box:
                guide_boxes[label] = box

        if not guide_boxes:
            logger.info("SAM3 refinement skipped: no guide boxes could be built")
            return gemini_zones

        # Run SAM3 guided segmentation with timeout to prevent Metal GPU hangs
        import asyncio
        seg_service = LocalSegmentationService()
        try:
            sam3_zones = await asyncio.wait_for(
                seg_service.detect_zones_guided(
                    image_bytes=image_bytes,
                    expected_labels=zone_labels,
                    guide_boxes=guide_boxes,
                    scene_id=scene_id,
                ),
                timeout=120,  # 2 minute max for SAM3
            )
        except asyncio.TimeoutError:
            logger.warning("SAM3 refinement timed out after 120s, keeping Gemini zones")
            return gemini_zones

        if sam3_zones and len(sam3_zones) > 0:
            # Post-processing: validate SAM3 polygon quality
            sam3_zones = _validate_sam3_zones(sam3_zones, gemini_zones, scene_id)
            logger.info(f"SAM3 refinement: {len(sam3_zones)}/{len(gemini_zones)} zones refined to pixel-precise polygons")
            return sam3_zones

        logger.info("SAM3 returned no zones, keeping Gemini zones")
        return gemini_zones

    except Exception as e:
        logger.warning(f"SAM3 refinement failed, keeping Gemini zones: {e}")
        return gemini_zones


def _polygon_area_pct(points: list[list[float]]) -> float:
    """Compute polygon area as percentage of total image (Shoelace formula).

    Points are in 0-100 percentage coordinates, so max possible area = 10000 (100x100).
    Returns 0-100 representing percentage of total image area.
    """
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0 / 100.0  # /10000 * 100 = /100


def _validate_sam3_zones(
    sam3_zones: list[dict[str, Any]],
    gemini_zones: list[dict[str, Any]],
    scene_id: str,
) -> list[dict[str, Any]]:
    """Validate SAM3 polygon zones and replace bad ones with Gemini bboxes.

    Rejects zones that:
    - Cover >60% of the image (SAM3 filled interior of boundary structure)
    - Cover <0.5% of the image (SAM3 found a tiny fragment)
    - Have fewer than 3 polygon points

    Rejected zones fall back to the Gemini bounding box for that label.
    """
    MAX_AREA_PCT = 60.0
    MIN_AREA_PCT = 0.5

    # Build Gemini fallback lookup by label (case-insensitive)
    gemini_by_label: dict[str, dict] = {}
    for gz in gemini_zones:
        label = gz.get("label", "").strip().lower()
        if label:
            gemini_by_label[label] = gz

    validated: list[dict[str, Any]] = []
    for zone in sam3_zones:
        label = zone.get("label", "")
        points = zone.get("points", [])

        if len(points) < 3:
            logger.warning(f"[Validate:{scene_id}] '{label}' has <3 points, using Gemini bbox")
            fallback = gemini_by_label.get(label.strip().lower())
            if fallback:
                validated.append(fallback)
            continue

        area = _polygon_area_pct(points)

        if area > MAX_AREA_PCT:
            logger.warning(
                f"[Validate:{scene_id}] '{label}' polygon covers {area:.1f}% of image "
                f"(>{MAX_AREA_PCT}%), using Gemini bbox instead"
            )
            fallback = gemini_by_label.get(label.strip().lower())
            if fallback:
                validated.append(fallback)
            continue

        if area < MIN_AREA_PCT:
            logger.warning(
                f"[Validate:{scene_id}] '{label}' polygon covers only {area:.1f}% of image "
                f"(<{MIN_AREA_PCT}%), using Gemini bbox instead"
            )
            fallback = gemini_by_label.get(label.strip().lower())
            if fallback:
                validated.append(fallback)
            continue

        # Zone is valid
        logger.info(f"[Validate:{scene_id}] '{label}' polygon OK: {area:.1f}% area, {len(points)} points")
        validated.append(zone)

    return validated
