"""
Asset Generator v3 Tools — ReAct agent toolbox for asset_generator_v3.

Five tools that give the asset generator agent the ability to:
1. Search for educational diagram images on the web
2. Generate diagram images using AI (Gemini Imagen)
3. Detect interactive zones in diagram images
4. Generate CSS animations for game interactions
5. Submit and validate the final per-scene asset bundle

All async tools read pipeline context via get_v3_tool_context() so that
upstream state fields (scene_specs, domain knowledge, run_id, etc.) are
available without passing them through the LLM.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.logging_config import get_logger
from app.tools.v3_context import get_v3_tool_context

logger = get_logger("gamed_ai.tools.asset_generator")


# ============================================================================
# Helpers
# ============================================================================

def _slugify(value: str) -> str:
    """Convert a string to a slug suitable for zone IDs."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _ensure_output_dir(run_id: str) -> Path:
    """Create and return an output directory for this run."""
    base = Path("pipeline_outputs") / "v3_assets" / (run_id or "unknown")
    base.mkdir(parents=True, exist_ok=True)
    return base


# ============================================================================
# Tool 1: search_diagram_image
# ============================================================================

async def search_diagram_image_impl(
    query: str,
    style_hints: str = "",
    prefer_unlabeled: bool = True,
) -> Dict[str, Any]:
    """
    Search the web for an educational diagram image.

    Uses the image retrieval service to find high-quality diagrams.
    Enriches the query with subject/domain info from pipeline context.

    Returns:
        Dict with success, image_url, local_path, source, is_labeled
    """
    ctx = get_v3_tool_context()
    subject = ctx.get("subject", "")
    domain_knowledge = ctx.get("domain_knowledge", "")

    # Enrich query with subject context
    enriched_query = query
    if subject and subject.lower() not in query.lower():
        enriched_query = f"{subject} {query}"
    if style_hints:
        enriched_query = f"{enriched_query} {style_hints}"

    logger.info(f"search_diagram_image: query='{enriched_query}', prefer_unlabeled={prefer_unlabeled}")

    # Try the full image retrieval service pipeline
    try:
        from app.services.image_retrieval import (
            search_diagram_images_multi,
            build_image_queries,
            select_best_image_scored,
        )

        # Build multiple search queries from the enriched query
        canonical_labels = ctx.get("canonical_labels", [])
        queries = build_image_queries(enriched_query, canonical_labels)

        # Search with multiple queries
        raw_results = await search_diagram_images_multi(
            queries=queries,
            max_results=5,
            max_queries=3,
            validate_quality=True,
        )

        if not raw_results:
            logger.warning("search_diagram_image: No results from multi-query search")
            return {
                "success": False,
                "reason": "No images found for query",
                "query_used": enriched_query,
            }

        # Score and select best image
        best = select_best_image_scored(raw_results, prefer_unlabeled=prefer_unlabeled)

        if not best:
            return {
                "success": False,
                "reason": "No images passed quality scoring",
                "query_used": enriched_query,
                "raw_count": len(raw_results),
            }

        image_url = best.get("image_url", "")
        source_url = best.get("source_url", "")
        title = best.get("title", "")

        # Infer labeled/unlabeled from metadata
        combined_text = f"{title} {best.get('snippet', '')}".lower()
        labeled_terms = ["labeled", "labelled", "annotated", "with labels"]
        unlabeled_terms = ["blank", "unlabeled", "unlabelled", "worksheet", "without labels"]
        is_labeled = any(t in combined_text for t in labeled_terms)
        if any(t in combined_text for t in unlabeled_terms):
            is_labeled = False

        # Attempt to download the image locally
        local_path = ""
        try:
            from app.agents.diagram_image_generator import download_and_validate_image

            run_id = ctx.get("run_id", "")
            out_dir = _ensure_output_dir(run_id)
            filename = f"search_{_slugify(query)[:40]}_{int(time.time())}.png"
            dest = str(out_dir / filename)

            success = await download_and_validate_image(image_url, dest)
            if success:
                local_path = dest
                logger.info(f"search_diagram_image: Downloaded to {local_path}")
            else:
                logger.warning("search_diagram_image: Download/validation failed, returning URL only")
        except Exception as dl_err:
            logger.warning(f"search_diagram_image: Download failed: {dl_err}")

        # --- Auto-clean: generate a mechanic-aware clean version ---
        # Most searched images are labeled. Generate a clean version using
        # the downloaded image as reference, with mechanic-aware prompting.
        cleaned_path = ""
        if local_path:
            try:
                logger.info("search_diagram_image: Auto-generating clean version from reference")
                clean_result = await generate_diagram_image_impl(
                    description=f"{title or query} — clean educational diagram",
                    style="clean educational illustration matching the reference",
                    reference_image_path=local_path,
                )
                if clean_result.get("success") and clean_result.get("generated_path"):
                    cleaned_path = clean_result["generated_path"]
                    logger.info(f"search_diagram_image: Clean version at {cleaned_path}")
                else:
                    logger.warning(
                        f"search_diagram_image: Auto-clean failed: "
                        f"{clean_result.get('reason', 'unknown')}"
                    )
            except Exception as clean_err:
                logger.warning(f"search_diagram_image: Auto-clean error: {clean_err}")

        return {
            "success": True,
            "image_url": image_url,
            "local_path": cleaned_path or local_path,
            "reference_path": local_path if cleaned_path else "",
            "cleaned": bool(cleaned_path),
            "source": source_url,
            "is_labeled": is_labeled,
            "title": title,
            "selection_score": best.get("selection_score", 0),
        }

    except ImportError as ie:
        logger.warning(f"search_diagram_image: Image retrieval service not available: {ie}")
        return {
            "success": False,
            "reason": "Image retrieval service not configured",
            "details": str(ie),
        }
    except Exception as e:
        logger.error(f"search_diagram_image: Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "reason": f"Search failed: {e}",
        }


# ============================================================================
# Tool 2: generate_diagram_image
# ============================================================================

def _get_mechanic_types_from_context() -> List[str]:
    """Extract mechanic types from scene_specs_v3 in tool context."""
    ctx = get_v3_tool_context()
    scene_specs = ctx.get("scene_specs_v3") or []
    mechanic_types: List[str] = []
    for spec in scene_specs:
        if not isinstance(spec, dict):
            continue
        for mc in spec.get("mechanic_configs", []):
            if isinstance(mc, dict):
                mtype = mc.get("type") or mc.get("mechanic_type", "")
                if mtype and mtype not in mechanic_types:
                    mechanic_types.append(mtype)
    # Also check game_design_v3 scenes
    if not mechanic_types:
        game_design = ctx.get("game_design_v3") or {}
        for scene in game_design.get("scenes", []):
            if isinstance(scene, dict):
                for mc in scene.get("mechanics", []):
                    if isinstance(mc, dict):
                        mtype = mc.get("type", "")
                        if mtype and mtype not in mechanic_types:
                            mechanic_types.append(mtype)
    return mechanic_types


# Mechanic-specific prompt additions for image generation
_MECHANIC_IMAGE_HINTS: Dict[str, str] = {
    "drag_drop": (
        "The diagram MUST KEEP all text labels, names, and annotations visible on the image. "
        "The labels should be clearly readable. Users will match functional descriptions "
        "to the labeled parts on the diagram, so the text labels ARE the visual anchors. "
        "Each part must be visually distinct with clear boundaries and colors."
    ),
    "click_to_identify": (
        "The diagram must have NO text labels. Each region must be visually "
        "distinct and clearly separated so users can click on individual parts. "
        "Use contrasting colors and clear outlines between regions."
    ),
    "trace_path": (
        "The diagram should show the structures/components clearly but should NOT "
        "show directional arrows, flow routes, or numbered sequences between them. "
        "Users must figure out the correct path order themselves. "
        "Keep text labels visible. Show the structures in their spatial positions "
        "without revealing the flow direction or order."
    ),
    "sequencing": (
        "Show the different stages/phases clearly separated. Each stage should be "
        "visually distinct and identifiable. Use visual progression cues (e.g. "
        "different colors per stage, spatial arrangement). NO text labels."
    ),
    "sorting_categories": (
        "Show the items to be sorted clearly and distinctly. Each item should be "
        "visually recognizable. Include visual category regions or groupings "
        "where items can be sorted into. NO text labels."
    ),
    "description_matching": (
        "Each structure/part should be clearly visible and distinguishable. "
        "Use detailed rendering so that functional descriptions can be matched "
        "to visual features. NO text labels."
    ),
    "compare_contrast": (
        "Show both subjects side by side for comparison. Highlight similarities "
        "and differences through visual features (color, shape, presence/absence "
        "of structures). NO text labels."
    ),
    "memory_match": (
        "Render each structure clearly and distinctly. Each element should be "
        "visually memorable and distinguishable from others. Use bold colors "
        "and clear shapes. NO text labels."
    ),
    "branching_scenario": (
        "Show the main subject/scenario clearly. Include visual elements that "
        "relate to decision points. The image should provide context for the "
        "branching decisions. NO text labels."
    ),
    "hierarchical": (
        "Show clear hierarchical structure with parent-child relationships "
        "visible. Use nesting, layering, or spatial arrangement to convey "
        "hierarchy. Sub-structures should be visually contained within or "
        "clearly connected to parent structures. NO text labels."
    ),
}


async def generate_diagram_image_impl(
    description: str,
    style: str = "clean educational illustration",
    reference_image_path: str = "",
) -> Dict[str, Any]:
    """
    Generate a mechanic-aware diagram image using AI (Gemini Imagen).

    Reads mechanic types from scene_specs_v3 in context and tailors the
    generation prompt accordingly. If a reference_image_path is provided
    (e.g. from search_diagram_image), Gemini uses it as a visual reference
    to produce a clean version optimized for the target mechanic.

    Returns:
        Dict with success, generated_path, method, duration_ms
    """
    ctx = get_v3_tool_context()
    run_id = ctx.get("run_id", "")
    subject = ctx.get("subject", "")
    canonical_labels = ctx.get("canonical_labels", [])

    logger.info(f"generate_diagram_image: description='{description[:80]}...', style='{style}'")
    start_time = time.time()

    # Get mechanic types from context for tailored generation
    mechanic_types = _get_mechanic_types_from_context()
    mechanic_hint = ""
    if mechanic_types:
        hints = []
        for mt in mechanic_types:
            hint = _MECHANIC_IMAGE_HINTS.get(mt, "")
            if hint:
                hints.append(hint)
        if hints:
            mechanic_hint = "\n" + " ".join(hints)
        logger.info(f"generate_diagram_image: Mechanic-aware generation for: {mechanic_types}")

    # Determine whether labels should be kept on the image.
    # drag_drop uses description-based labels: student matches descriptions to
    # labeled parts on the diagram, so text labels MUST be visible.
    # All other mechanics need a clean/unlabeled diagram.
    keep_labels = "drag_drop" in mechanic_types

    # Build a detailed prompt
    label_hint = ""
    if canonical_labels:
        labels_str = ", ".join(canonical_labels[:15])
        if keep_labels:
            label_hint = (
                f"\nThe diagram MUST include clear, readable text labels for these "
                f"structures/parts: {labels_str}. The labels are essential for the "
                f"interactive game — users will match descriptions to them."
            )
        else:
            label_hint = (
                f"\nThe diagram should clearly show these structures/parts "
                f"(DO NOT add text labels): {labels_str}"
            )

    ref_hint = ""
    if reference_image_path:
        if keep_labels:
            ref_hint = (
                "\nIMPORTANT: A reference image is provided. Generate a CLEAN version "
                "of this reference — same subject matter and layout. KEEP all text "
                "labels and part names visible and readable. Remove only clutter "
                "(watermarks, excess annotations, sourcing info). The output should "
                "be a clean educational diagram with labeled components."
            )
        else:
            ref_hint = (
                "\nIMPORTANT: A reference image is provided. Generate a CLEAN version "
                "of this reference — same subject matter and layout, but with ALL text "
                "labels, annotations, arrows, numbers, and captions REMOVED. The output "
                "must be a clean educational diagram suitable for interactive overlays."
            )

    if keep_labels:
        prompt = (
            f"Generate a {style} diagram showing: {description}. "
            f"The image should be a detailed, scientifically accurate "
            f"educational diagram suitable for an interactive game. "
            f"KEEP all text labels and component names clearly visible and readable. "
            f"Use clear visual distinctions (color, shading, boundaries) between parts."
            f"{label_hint}{mechanic_hint}{ref_hint}"
        )
    else:
        prompt = (
            f"Generate a {style} diagram showing: {description}. "
            f"The image should be a clean, detailed, scientifically accurate "
            f"educational diagram suitable for an interactive game. "
            f"DO NOT include any text, labels, or annotations on the image. "
            f"Use clear visual distinctions (color, shading, boundaries) so that "
            f"each part can be identified separately."
            f"{label_hint}{mechanic_hint}{ref_hint}"
        )

    out_dir = _ensure_output_dir(run_id)
    filename = f"generated_{_slugify(description)[:40]}_{int(time.time())}.png"
    dest_path = str(out_dir / filename)

    # Try Gemini Imagen generation
    try:
        from app.agents.diagram_image_generator import generate_with_gemini

        # Use reference image if provided (e.g. from search_diagram_image)
        ref_path = reference_image_path if reference_image_path and os.path.exists(reference_image_path) else None
        if ref_path:
            logger.info(f"generate_diagram_image: Using reference image: {ref_path}")

        result = await generate_with_gemini(
            prompt=prompt,
            reference_image_path=ref_path,
            dimensions={"width": 1024, "height": 768},
        )

        duration_ms = int((time.time() - start_time) * 1000)

        if result.get("success") and (result.get("generated_path") or result.get("image_path")):
            generated_path = result.get("generated_path") or result["image_path"]
            logger.info(f"generate_diagram_image: Generated at {generated_path} in {duration_ms}ms")
            return {
                "success": True,
                "generated_path": generated_path,
                "method": result.get("generator", "gemini-imagen"),
                "duration_ms": duration_ms,
            }
        else:
            error = result.get("error", "Unknown generation error")
            logger.warning(f"generate_diagram_image: Generation failed: {error}")
            return {
                "success": False,
                "reason": f"Image generation failed: {error}",
                "method": result.get("generator", "gemini-imagen"),
                "duration_ms": duration_ms,
            }

    except ImportError as ie:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"generate_diagram_image: Generator not available: {ie}")
        return {
            "success": False,
            "reason": "Image generation not configured",
            "details": str(ie),
            "method": "none",
            "duration_ms": duration_ms,
            "prompt_used": prompt[:500],
        }
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"generate_diagram_image: Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "reason": f"Generation failed: {e}",
            "method": "error",
            "duration_ms": duration_ms,
        }


# ============================================================================
# Tool 3: detect_zones
# ============================================================================

async def detect_zones_impl(
    image_path: str,
    expected_labels: List[str],
    detection_method: str = "auto",
) -> Dict[str, Any]:
    """
    Detect interactive zones in a diagram image.

    Tries multiple detection methods in order of preference:
    - gemini_sam3: Gemini vision + SAM3 segmentation (best quality)
    - gemini: Gemini vision only (faster, no SAM dependency)
    - qwen: Qwen VL per-label detection (fallback)
    - auto: Try gemini_sam3 → gemini → qwen

    All zone coordinates are normalized to 0-100 percentage scale.

    Returns:
        Dict with success, zones, method_used, labels_found, labels_missing, confidence
    """
    logger.info(
        f"detect_zones: image_path='{image_path}', "
        f"labels={expected_labels}, method='{detection_method}'"
    )

    if not image_path or not os.path.exists(image_path):
        return {
            "success": False,
            "reason": f"Image not found: {image_path}",
            "zones": [],
            "method_used": "none",
            "labels_found": [],
            "labels_missing": expected_labels,
            "confidence": 0.0,
        }

    ctx = get_v3_tool_context()
    subject = ctx.get("subject", "")
    domain_knowledge = ctx.get("domain_knowledge")
    hierarchical_relationships = None
    if isinstance(domain_knowledge, dict):
        hierarchical_relationships = domain_knowledge.get("hierarchical_relationships")
    elif isinstance(domain_knowledge, str):
        # domain_knowledge may be serialized string in some pipelines
        pass

    # Determine method order
    if detection_method == "auto":
        methods = ["gemini_sam3", "gemini"]
    elif detection_method in ("gemini_sam3", "gemini", "qwen"):
        methods = [detection_method]
    else:
        logger.warning(f"detect_zones: Unknown method '{detection_method}', using auto")
        methods = ["gemini_sam3", "gemini"]

    last_error = ""

    for method in methods:
        try:
            raw_result = await _run_zone_detection(
                method=method,
                image_path=image_path,
                expected_labels=expected_labels,
                subject=subject,
                hierarchical_relationships=hierarchical_relationships,
            )

            if not raw_result or not raw_result.get("success", False):
                last_error = raw_result.get("error", "Detection returned no results") if raw_result else "No result"
                logger.warning(f"detect_zones: Method '{method}' failed: {last_error}")
                continue

            # Normalize zones to standard format with 0-100% coordinates
            raw_zones = raw_result.get("zones", [])
            normalized_zones = _normalize_zones_to_percent(raw_zones, image_path)

            # Check label coverage
            found_labels = [z.get("label", "") for z in normalized_zones if z.get("label")]
            found_labels_lower = {lbl.lower() for lbl in found_labels}
            missing_labels = [
                lbl for lbl in expected_labels
                if lbl.lower() not in found_labels_lower
            ]

            # Calculate aggregate confidence
            confidences = [z.get("confidence", 0.5) for z in normalized_zones]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            coverage = len(found_labels) / len(expected_labels) if expected_labels else 1.0
            overall_confidence = avg_confidence * coverage

            logger.info(
                f"detect_zones: Method '{method}' found {len(found_labels)}/{len(expected_labels)} labels, "
                f"confidence={overall_confidence:.2f}"
            )

            return {
                "success": True,
                "zones": normalized_zones,
                "method_used": method,
                "labels_found": found_labels,
                "labels_missing": missing_labels,
                "confidence": round(overall_confidence, 3),
                "zone_count": len(normalized_zones),
            }

        except ImportError as ie:
            last_error = f"Method '{method}' not available: {ie}"
            logger.warning(f"detect_zones: {last_error}")
            continue
        except Exception as e:
            last_error = f"Method '{method}' error: {e}"
            logger.error(f"detect_zones: {last_error}", exc_info=True)
            continue

    # All methods failed
    return {
        "success": False,
        "reason": f"All detection methods failed. Last error: {last_error}",
        "zones": [],
        "method_used": "none",
        "labels_found": [],
        "labels_missing": expected_labels,
        "confidence": 0.0,
    }


async def _run_zone_detection(
    method: str,
    image_path: str,
    expected_labels: List[str],
    subject: str = "",
    hierarchical_relationships: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Dispatch to the appropriate zone detection backend.

    Returns the raw result dict from the detector.
    """
    if method == "gemini_sam3":
        from app.agents.gemini_sam3_zone_detector import detect_zones_with_gemini_sam3
        return await detect_zones_with_gemini_sam3(
            image_path=image_path,
            canonical_labels=expected_labels,
            subject=subject,
            hierarchical_relationships=hierarchical_relationships,
        )

    elif method == "gemini":
        from app.agents.gemini_zone_detector import detect_zones_with_gemini
        return await detect_zones_with_gemini(
            image_path=image_path,
            canonical_labels=expected_labels,
            subject=subject,
            hierarchical_relationships=hierarchical_relationships,
        )

    elif method == "qwen":
        # Qwen zone detector is deprecated but kept as fallback
        from app.agents.qwen_zone_detector import qwen_zone_detector_agent
        # Build a minimal state for the legacy agent interface
        minimal_state = {
            "cleaned_image_path": image_path,
            "generated_diagram_path": None,
            "diagram_image": {"local_path": image_path},
            "domain_knowledge": {
                "canonical_labels": expected_labels,
                "hierarchical_relationships": hierarchical_relationships,
            },
            "pedagogical_context": {"subject": subject},
        }
        result_state = await qwen_zone_detector_agent(minimal_state, ctx=None)
        zones = result_state.get("diagram_zones", [])
        if zones:
            return {"success": True, "zones": zones}
        return {"success": False, "error": "Qwen detector returned no zones"}

    else:
        return {"success": False, "error": f"Unknown method: {method}"}


def _normalize_zones_to_percent(
    raw_zones: List[Dict[str, Any]],
    image_path: str,
) -> List[Dict[str, Any]]:
    """
    Normalize zone coordinates to 0-100 percentage scale.

    Detectors may return coordinates in pixel space or already normalized.
    This function ensures a consistent format for downstream consumers.

    Output zone format:
        {
            id: str, label: str, shape: str,
            x: float, y: float, radius: float,
            points: [[x, y], ...],
            confidence: float
        }
    """
    # Try to get image dimensions for pixel→percent conversion
    img_width, img_height = 1000, 1000  # defaults (assume 1000x1000 if we can't read)
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            img_width, img_height = img.size
    except Exception:
        logger.warning(f"Could not read image dimensions from {image_path}, using defaults")

    normalized = []
    for zone in raw_zones:
        label = zone.get("label", "unknown")
        zone_id = zone.get("id") or f"zone_{_slugify(label)}"
        shape = zone.get("shape", "circle")
        confidence = zone.get("confidence", 0.5)

        # Extract x, y — handle multiple formats
        x = _extract_coord(zone, "x", "cx", "center_x")
        y = _extract_coord(zone, "y", "cy", "center_y")
        radius = zone.get("radius", 5.0)

        # Detect if coordinates are in pixel space (> 100)
        # and convert to percentage
        if x > 100 or y > 100:
            x = (x / img_width) * 100.0
            y = (y / img_height) * 100.0
            if radius > 100:
                radius = (radius / max(img_width, img_height)) * 100.0

        # Clamp to valid range
        x = max(0.0, min(100.0, x))
        y = max(0.0, min(100.0, y))
        radius = max(1.0, min(50.0, radius))

        # Handle points for polygon shapes
        points = zone.get("points", [])
        if points and isinstance(points, list):
            normalized_points = []
            for pt in points:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    px, py = float(pt[0]), float(pt[1])
                    if px > 100 or py > 100:
                        px = (px / img_width) * 100.0
                        py = (py / img_height) * 100.0
                    normalized_points.append([
                        round(max(0.0, min(100.0, px)), 2),
                        round(max(0.0, min(100.0, py)), 2),
                    ])
                elif isinstance(pt, dict):
                    px = float(pt.get("x", 0))
                    py = float(pt.get("y", 0))
                    if px > 100 or py > 100:
                        px = (px / img_width) * 100.0
                        py = (py / img_height) * 100.0
                    normalized_points.append([
                        round(max(0.0, min(100.0, px)), 2),
                        round(max(0.0, min(100.0, py)), 2),
                    ])
            points = normalized_points
        else:
            # Generate circle points as fallback for frontend compatibility
            import math
            points = []
            num_pts = 8
            for i in range(num_pts):
                angle = 2 * math.pi * i / num_pts
                px = x + radius * math.cos(angle)
                py = y + radius * math.sin(angle)
                points.append([
                    round(max(0.0, min(100.0, px)), 2),
                    round(max(0.0, min(100.0, py)), 2),
                ])

        normalized.append({
            "id": zone_id,
            "label": label,
            "shape": shape,
            "x": round(x, 2),
            "y": round(y, 2),
            "radius": round(radius, 2),
            "points": points,
            "confidence": round(confidence, 3),
        })

    return normalized


def _extract_coord(zone: Dict, *keys: str) -> float:
    """Extract a coordinate from a zone dict, trying multiple key names."""
    for key in keys:
        val = zone.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    # Try nested coordinates dict
    coords = zone.get("coordinates", {})
    if isinstance(coords, dict):
        for key in keys:
            val = coords.get(key)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
    return 50.0  # fallback center


# ============================================================================
# Tool 4: generate_animation_css
# ============================================================================

# Pre-defined CSS animation templates
_CSS_ANIMATIONS: Dict[str, Dict[str, str]] = {
    "pulse": {
        "keyframes": (
            "@keyframes {class_name} {{\n"
            "  0% {{ transform: scale(1); opacity: 1; }}\n"
            "  50% {{ transform: scale({scale}); opacity: 0.8; }}\n"
            "  100% {{ transform: scale(1); opacity: 1; }}\n"
            "}}"
        ),
        "defaults": {"scale": "1.15", "duration": "1.5s"},
    },
    "shake": {
        "keyframes": (
            "@keyframes {class_name} {{\n"
            "  0%, 100% {{ transform: translateX(0); }}\n"
            "  20% {{ transform: translateX(-4px); }}\n"
            "  40% {{ transform: translateX(4px); }}\n"
            "  60% {{ transform: translateX(-3px); }}\n"
            "  80% {{ transform: translateX(3px); }}\n"
            "}}"
        ),
        "defaults": {"duration": "0.5s"},
    },
    "confetti": {
        "keyframes": (
            "@keyframes {class_name} {{\n"
            "  0% {{ transform: translateY(0) rotate(0deg); opacity: 1; }}\n"
            "  25% {{ transform: translateY(-20px) rotate(90deg); opacity: 1; }}\n"
            "  50% {{ transform: translateY(-35px) rotate(180deg); opacity: 0.8; }}\n"
            "  75% {{ transform: translateY(-20px) rotate(270deg); opacity: 0.5; }}\n"
            "  100% {{ transform: translateY(0) rotate(360deg); opacity: 0; }}\n"
            "}}"
        ),
        "defaults": {"duration": "2s"},
    },
    "fade": {
        "keyframes": (
            "@keyframes {class_name} {{\n"
            "  0% {{ opacity: 0; }}\n"
            "  100% {{ opacity: 1; }}\n"
            "}}"
        ),
        "defaults": {"duration": "0.6s"},
    },
    "bounce": {
        "keyframes": (
            "@keyframes {class_name} {{\n"
            "  0%, 100% {{ transform: translateY(0); }}\n"
            "  25% {{ transform: translateY(-12px); }}\n"
            "  50% {{ transform: translateY(0); }}\n"
            "  75% {{ transform: translateY(-6px); }}\n"
            "}}"
        ),
        "defaults": {"duration": "0.8s"},
    },
    "glow": {
        "keyframes": (
            "@keyframes {class_name} {{\n"
            "  0% {{ box-shadow: 0 0 5px {color}40; }}\n"
            "  50% {{ box-shadow: 0 0 20px {color}80, 0 0 40px {color}40; }}\n"
            "  100% {{ box-shadow: 0 0 5px {color}40; }}\n"
            "}}"
        ),
        "defaults": {"color": "#4CAF50", "duration": "2s"},
    },
    "scale": {
        "keyframes": (
            "@keyframes {class_name} {{\n"
            "  0% {{ transform: scale(0); opacity: 0; }}\n"
            "  60% {{ transform: scale(1.1); opacity: 1; }}\n"
            "  100% {{ transform: scale(1); opacity: 1; }}\n"
            "}}"
        ),
        "defaults": {"duration": "0.4s"},
    },
}


async def generate_animation_css_impl(
    animation_type: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate CSS keyframe animations for game interactions.

    Deterministic: no LLM calls. Produces ready-to-use CSS from templates.

    Supported animation_type values:
        pulse, shake, confetti, fade, bounce, glow, scale

    Config options:
        color (str): CSS color for glow/highlight effects (default: #4CAF50)
        duration (str): Animation duration (default varies by type)
        target (str): CSS selector target (used in class name)
        scale (str): Scale factor for pulse (default: 1.15)

    Returns:
        Dict with success, css_keyframes, class_name
    """
    config = config or {}
    anim_type = animation_type.lower().strip()

    logger.info(f"generate_animation_css: type='{anim_type}', config={config}")

    template = _CSS_ANIMATIONS.get(anim_type)
    if not template:
        supported = ", ".join(sorted(_CSS_ANIMATIONS.keys()))
        return {
            "success": False,
            "reason": f"Unknown animation type '{anim_type}'. Supported: {supported}",
        }

    # Build class name
    target = config.get("target", anim_type)
    target_slug = _slugify(target)
    class_name = f"gamed-anim-{target_slug}"

    # Merge defaults with provided config
    params = dict(template["defaults"])
    params.update({k: str(v) for k, v in config.items() if v is not None})
    params["class_name"] = class_name

    # Generate keyframes from template
    try:
        css_keyframes = template["keyframes"].format(**params)
    except KeyError as e:
        # Missing a template variable — fill with default
        logger.warning(f"generate_animation_css: Missing param {e}, using fallback")
        params.setdefault(str(e).strip("'"), "inherit")
        css_keyframes = template["keyframes"].format(**params)

    # Build the full CSS rule (keyframes + class)
    duration = params.get("duration", "1s")
    full_css = (
        f"{css_keyframes}\n\n"
        f".{class_name} {{\n"
        f"  animation: {class_name} {duration} ease-in-out;\n"
        f"}}"
    )

    return {
        "success": True,
        "css_keyframes": full_css,
        "class_name": class_name,
        "animation_type": anim_type,
        "duration": duration,
    }


# ============================================================================
# Tool 5: submit_assets
# ============================================================================

async def submit_assets_impl(
    scenes: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate and submit per-scene asset results.

    Schema per scene:
        {
            "diagram_image_url": str,
            "diagram_image_path": str,
            "zones": [
                {
                    "id": str, "label": str, "shape": str,
                    "x": float, "y": float,
                    "points": [[x, y], ...],
                    "confidence": float
                }
            ],
            "zone_detection_method": str
        }

    Validates:
    - Every scene has a diagram image (URL or local path)
    - Zones have required fields (id, label, x, y)
    - Zone labels match expected labels from scene_specs_v3 (via context)

    Returns:
        Dict with status (accepted/rejected), issues list
    """
    logger.info(f"submit_assets: Validating {len(scenes)} scene(s)")

    ctx = get_v3_tool_context()
    scene_specs = ctx.get("scene_specs_v3") or []

    issues: List[str] = []
    warnings: List[str] = []
    validated_scenes: Dict[str, Dict[str, Any]] = {}

    # Build expected labels per scene from scene_specs
    expected_labels_by_scene: Dict[str, List[str]] = {}
    for spec in scene_specs:
        scene_num = str(spec.get("scene_number", 1))
        zone_labels = spec.get("zone_labels", [])
        if not zone_labels:
            # Try extracting from zones list
            zones_list = spec.get("zones", [])
            zone_labels = [z.get("label", "") for z in zones_list if z.get("label")]
        expected_labels_by_scene[scene_num] = zone_labels

    # Check scene count matches expected from game_design
    game_design = ctx.get("game_design_v3") or {}
    expected_scene_count = len(game_design.get("scenes", []))
    if expected_scene_count > 0 and len(scenes) < expected_scene_count:
        missing = [str(i + 1) for i in range(expected_scene_count) if str(i + 1) not in scenes]
        warnings.append(
            f"Only {len(scenes)}/{expected_scene_count} scenes have assets. "
            f"Missing scene keys: {missing}"
        )

    if not scenes:
        return {
            "status": "rejected",
            "issues": ["No scenes provided"],
            "warnings": [],
        }

    for scene_key, scene_data in scenes.items():
        scene_num = str(scene_key)

        # Check diagram image
        image_url = scene_data.get("diagram_image_url", "")
        image_path = scene_data.get("diagram_image_path", "")
        if not image_url and not image_path:
            issues.append(f"Scene {scene_num}: Missing diagram image (no URL or local path)")
        elif image_path and not os.path.exists(image_path):
            warnings.append(f"Scene {scene_num}: Local image path does not exist: {image_path}")

        # Check zones
        zones = scene_data.get("zones", [])
        if not zones:
            issues.append(f"Scene {scene_num}: No zones defined")
            continue

        # Validate zone fields
        for i, zone in enumerate(zones):
            if not zone.get("id"):
                issues.append(f"Scene {scene_num}, zone {i}: Missing 'id'")
            if not zone.get("label"):
                issues.append(f"Scene {scene_num}, zone {i}: Missing 'label'")
            if zone.get("x") is None or zone.get("y") is None:
                issues.append(f"Scene {scene_num}, zone {i}: Missing x/y coordinates")

        # Check label coverage
        expected = expected_labels_by_scene.get(scene_num, [])
        if expected:
            found_labels = {z.get("label", "").lower() for z in zones if z.get("label")}
            for lbl in expected:
                if lbl.lower() not in found_labels:
                    warnings.append(f"Scene {scene_num}: Expected label '{lbl}' not found in zones")

        # Store validated scene
        validated_scenes[scene_num] = {
            "diagram_image_url": image_url,
            "diagram_image_path": image_path,
            "zones": zones,
            "zone_detection_method": scene_data.get("zone_detection_method", "unknown"),
            "zone_count": len(zones),
        }

    # Fix 2.9: Mechanic-aware zone validation warnings
    # Check that zones are appropriate for the mechanics being used in each scene
    for spec in scene_specs:
        scene_num = str(spec.get("scene_number", 1))
        mechanic_configs = spec.get("mechanic_configs", [])
        scene_data = scenes.get(scene_num, {})
        scene_zones = scene_data.get("zones", [])

        for mc in mechanic_configs:
            if not isinstance(mc, dict):
                continue
            mtype = mc.get("type") or mc.get("mechanic_type", "")

            # trace_path needs zones in a spatial sequence
            if mtype == "trace_path":
                waypoints = mc.get("config", {}).get("waypoints", [])
                if waypoints and scene_zones:
                    found_waypoint_labels = {z.get("label", "").lower() for z in scene_zones}
                    missing_waypoints = [
                        wp for wp in waypoints
                        if wp.lower() not in found_waypoint_labels
                    ]
                    if missing_waypoints:
                        warnings.append(
                            f"Scene {scene_num}: trace_path waypoints missing from zones: "
                            f"{missing_waypoints[:5]}"
                        )

            # click_to_identify needs zones that can be uniquely clicked
            if mtype == "click_to_identify":
                if scene_zones:
                    overlapping = []
                    for i, z1 in enumerate(scene_zones):
                        for z2 in scene_zones[i+1:]:
                            if (isinstance(z1, dict) and isinstance(z2, dict)
                                    and z1.get("x") is not None and z2.get("x") is not None):
                                dist = ((z1["x"] - z2["x"])**2 + (z1.get("y", 0) - z2.get("y", 0))**2)**0.5
                                if dist < 3:  # Very close zones
                                    overlapping.append(f"{z1.get('label', '?')} / {z2.get('label', '?')}")
                    if overlapping:
                        warnings.append(
                            f"Scene {scene_num}: click_to_identify has very close zones: "
                            f"{overlapping[:3]}. May be hard to click accurately."
                        )

            # sorting_categories needs the zones to map to categories
            if mtype == "sorting_categories":
                categories = mc.get("config", {}).get("categories", [])
                if not categories:
                    warnings.append(
                        f"Scene {scene_num}: sorting_categories mechanic has no categories defined"
                    )

    # Determine status
    if issues:
        status = "rejected"
    else:
        status = "accepted"

    result = {
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "scene_count": len(validated_scenes),
        "validated_scenes": validated_scenes,
    }

    if status == "accepted":
        logger.info(f"submit_assets: Accepted {len(validated_scenes)} scene(s)")
    else:
        logger.warning(f"submit_assets: Rejected — {len(issues)} issue(s): {issues}")

    return result


# ============================================================================
# Registration
# ============================================================================

def register_asset_generator_tools() -> None:
    """Register all 5 asset generator v3 tools in the tool registry."""
    from app.tools.registry import register_tool

    register_tool(
        name="search_diagram_image",
        description=(
            "Search the web for an educational diagram image and automatically "
            "generate a clean, mechanic-aware version using Gemini Imagen. "
            "Returns both the reference image and the cleaned version. "
            "The cleaned image has text labels, annotations, and arrows removed, "
            "optimized for the game's mechanic type (drag_drop, trace_path, etc.). "
            "Use the returned local_path (cleaned) for zone detection."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query for the diagram image, e.g. "
                        "'human heart anatomy diagram' or 'flower parts illustration'"
                    ),
                },
                "style_hints": {
                    "type": "string",
                    "description": (
                        "Optional style hints, e.g. 'colorful', 'scientific', "
                        "'clean illustration', 'realistic'"
                    ),
                },
                "prefer_unlabeled": {
                    "type": "boolean",
                    "description": (
                        "If true, prefer blank/unlabeled diagrams. "
                        "Default true (labels will be added by the game frontend)."
                    ),
                },
            },
            "required": ["query"],
        },
        function=search_diagram_image_impl,
    )

    register_tool(
        name="generate_diagram_image",
        description=(
            "Generate a clean, unlabeled diagram image using AI (Gemini Imagen). "
            "Use this AFTER search_diagram_image to produce a clean version of "
            "the found reference image (removing labels/annotations). Can also "
            "generate from scratch if no reference is available."
        ),
        parameters={
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": (
                        "Detailed description of the diagram to generate, e.g. "
                        "'A detailed cross-section of a human heart showing all four "
                        "chambers, valves, and major blood vessels'"
                    ),
                },
                "style": {
                    "type": "string",
                    "description": (
                        "Visual style, e.g. 'clean educational illustration', "
                        "'realistic medical diagram', 'colorful scientific poster'"
                    ),
                },
                "reference_image_path": {
                    "type": "string",
                    "description": (
                        "Local file path to a reference image (e.g. from "
                        "search_diagram_image). Gemini will use this as a visual "
                        "reference to produce a clean unlabeled version."
                    ),
                },
            },
            "required": ["description"],
        },
        function=generate_diagram_image_impl,
    )

    register_tool(
        name="detect_zones",
        description=(
            "Detect interactive zones (clickable regions) in a diagram image. "
            "Returns zone positions with coordinates in 0-100% scale. "
            "Tries multiple detection methods (Gemini+SAM3, Gemini, Qwen) "
            "and reports which expected labels were found or missing."
        ),
        parameters={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Local file path to the diagram image",
                },
                "expected_labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of labels to detect in the diagram, e.g. "
                        "['Left Atrium', 'Right Ventricle', 'Aorta']"
                    ),
                },
                "detection_method": {
                    "type": "string",
                    "description": (
                        "Detection method: 'auto' (try all), 'gemini_sam3', "
                        "'gemini', or 'qwen'. Default: 'auto'"
                    ),
                    "enum": ["auto", "gemini_sam3", "gemini", "qwen"],
                },
            },
            "required": ["image_path", "expected_labels"],
        },
        function=detect_zones_impl,
    )

    register_tool(
        name="generate_animation_css",
        description=(
            "Generate CSS keyframe animations for game interactions. "
            "Deterministic (no LLM calls). Supports: pulse, shake, confetti, "
            "fade, bounce, glow, scale. Returns ready-to-use CSS."
        ),
        parameters={
            "type": "object",
            "properties": {
                "animation_type": {
                    "type": "string",
                    "description": "Type of animation to generate",
                    "enum": ["pulse", "shake", "confetti", "fade", "bounce", "glow", "scale"],
                },
                "config": {
                    "type": "object",
                    "description": (
                        "Optional configuration: color (CSS color for glow), "
                        "duration (e.g. '1.5s'), target (CSS selector hint for class name), "
                        "scale (factor for pulse, default 1.15)"
                    ),
                    "properties": {
                        "color": {"type": "string"},
                        "duration": {"type": "string"},
                        "target": {"type": "string"},
                        "scale": {"type": "string"},
                    },
                },
            },
            "required": ["animation_type"],
        },
        function=generate_animation_css_impl,
    )

    register_tool(
        name="submit_assets",
        description=(
            "Submit and validate the final per-scene asset bundle. Validates that "
            "every scene has a diagram image and zones with required fields. "
            "Returns 'accepted' if valid, 'rejected' with issues if not. "
            "You MUST call this tool when you have gathered all assets for all scenes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "scenes": {
                    "type": "object",
                    "description": (
                        "Per-scene asset results, keyed by scene number as string (e.g. '1', '2'). "
                        "Each value is an object with: diagram_image_url (string), "
                        "diagram_image_path (string), zones (array of objects with "
                        "id, label, shape, x, y, points, confidence), "
                        "and zone_detection_method (string)."
                    ),
                },
            },
            "required": ["scenes"],
        },
        function=submit_assets_impl,
    )

    logger.info("Registered 5 asset generator v3 tools")
