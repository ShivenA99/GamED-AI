"""
Labeling Diagram Workflow - Produces cleaned diagram with zones and labels.

This workflow handles diagram asset generation for drag_drop, click_to_identify,
and hotspot mechanics.

Steps:
1. Retrieve diagram image (Serper multi-query search with robust download)
2. Generate clean diagram (Gemini Imagen with reference image)
3. Detect zones using Gemini+SAM3 / Gemini Vision / Qwen VL
4. Create labels from domain knowledge
"""
import logging
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from app.agents.workflows.base import (
    WorkflowContext, WorkflowResult, WorkflowRegistry, create_failed_result
)
from app.agents.workflows.types import DiagramZone, DiagramLabel

logger = logging.getLogger("gamed_ai.workflows.labeling_diagram")

# Output directory for workflow images
WORKFLOW_OUTPUT_DIR = Path("pipeline_outputs/workflow_images")
WORKFLOW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@WorkflowRegistry.register(
    name="labeling_diagram",
    description="Retrieves diagram image and detects zones for labeling mechanics",
    output_type="diagram"
)
async def labeling_diagram_workflow(context: WorkflowContext) -> WorkflowResult:
    """
    Complete workflow for labeling diagram asset generation.

    3-step pipeline:
    1. Retrieve reference diagram image (Serper multi-query search)
    2. Generate clean diagram (Gemini Imagen with reference)
    3. Detect zones (Gemini+SAM3 → Gemini-only → Qwen VL → placeholder)

    Inputs from context:
        - asset_spec.spec.query: Search query for diagram
        - domain_knowledge.canonical_labels: Expected labels

    Outputs:
        - diagram_image: URL/path to diagram
        - diagram_zones: List of detected zones
        - diagram_labels: Labels for zones
    """
    asset_id = context.asset_spec.get("id", "diagram")
    scene_number = context.scene_number
    started_at = datetime.utcnow().isoformat()

    try:
        # Step 1: Get diagram image
        query = context.get_spec_value("query", "educational diagram")
        canonical_labels = context.domain_knowledge.get("canonical_labels", [])

        logger.info(
            f"Starting labeling diagram workflow for scene {scene_number}, "
            f"query='{query[:50]}...', labels={len(canonical_labels)}"
        )

        image_result = await _retrieve_diagram_image(query, canonical_labels, context)

        if not image_result.get("success"):
            return create_failed_result(
                "labeling_diagram", asset_id, scene_number, "diagram",
                f"Failed to retrieve diagram: {image_result.get('error', 'Unknown error')}"
            )

        diagram_url = image_result.get("image_url")
        local_path = image_result.get("local_path")

        logger.info(f"Step 1 complete: Retrieved diagram image: {diagram_url[:80] if diagram_url else 'local'}")

        # Step 2: Generate clean diagram using Gemini Imagen
        gen_result = await _generate_clean_diagram(
            local_path=local_path,
            context=context,
            canonical_labels=canonical_labels,
        )

        # Decide which image to use for zone detection
        if gen_result.get("success"):
            zone_detection_image = gen_result["generated_path"]
            image_source = "generated"
            logger.info(f"Step 2 complete: Generated clean diagram: {zone_detection_image}")
        else:
            zone_detection_image = local_path
            image_source = "reference"
            logger.warning(
                f"Step 2 skipped/failed: {gen_result.get('error', 'unknown')}, "
                f"using reference image for zone detection"
            )

        # Step 3: Detect zones
        zones_result = await _detect_zones(
            image_path=zone_detection_image,
            image_url=diagram_url,
            canonical_labels=canonical_labels,
            context=context
        )

        zones = zones_result.get("zones", [])

        logger.info(f"Step 3 complete: Detected {len(zones)} zones")

        # Step 4: Create labels from zones and domain knowledge
        labels = _create_labels_from_zones(zones, context.domain_knowledge)

        logger.info(f"Created {len(labels)} labels")

        # Extract zone_groups if available (from SAM3 detection)
        zone_groups = zones_result.get("zone_groups", [])

        # Final image path: prefer generated, fall back to reference
        final_image_path = gen_result.get("generated_path") or local_path

        return WorkflowResult(
            success=True,
            workflow_name="labeling_diagram",
            asset_id=asset_id,
            scene_number=scene_number,
            output_type="diagram",
            data={
                "diagram_image": final_image_path or diagram_url,
                "diagram_image_local": final_image_path,
                "diagram_zones": zones,
                "diagram_labels": labels,
                "zone_groups": zone_groups,
                "zone_count": len(zones),
                "label_count": len(labels),
                "zone_detection_method": zones_result.get("method", "unknown"),
                "image_source": image_source,
            },
            metadata={
                "image_retrieval": {
                    "query": query,
                    "source": image_result.get("source"),
                    "attribution": image_result.get("attribution"),
                },
                "image_generation": {
                    "success": gen_result.get("success", False),
                    "generator": gen_result.get("generator"),
                    "duration_ms": gen_result.get("duration_ms"),
                    "error": gen_result.get("error"),
                },
                "zone_detection": {
                    "method": zones_result.get("method"),
                    "duration_ms": zones_result.get("duration_ms"),
                    "parts_not_found": zones_result.get("parts_not_found", []),
                },
            },
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Labeling diagram workflow failed: {e}", exc_info=True)
        return create_failed_result(
            "labeling_diagram", asset_id, scene_number, "diagram", str(e)
        )


async def _retrieve_diagram_image(
    query: str,
    canonical_labels: List[str],
    context: WorkflowContext
) -> Dict[str, Any]:
    """
    Retrieve diagram image using Serper image search.

    Uses multi-query strategy and top-N scoring for fallback robustness.
    Iterates through scored candidates until a valid image is downloaded.
    """
    try:
        from app.services.image_retrieval import (
            build_image_queries,
            search_diagram_images_multi,
            select_top_images_scored,
        )

        # Build multiple search queries for better coverage
        queries = build_image_queries(query, canonical_labels)

        logger.info(f"Searching for diagram with {len(queries)} queries")

        # Search with multi-query strategy
        results = await search_diagram_images_multi(
            queries=queries,
            max_results=5,
            max_queries=4,
            validate_quality=True
        )

        if not results:
            logger.warning("No image results from multi-query search")
            return {"success": False, "error": "No images found"}

        # Get top 5 scored images for fallback iteration
        top_images = select_top_images_scored(results, prefer_unlabeled=False, top_n=5)

        if not top_images:
            logger.warning("No suitable image found after scoring")
            return {"success": False, "error": "No suitable images found"}

        # Iterate through scored images, try download on each until one succeeds
        backup_images = []
        for i, candidate in enumerate(top_images):
            image_url = candidate.get("image_url")
            if not image_url:
                continue

            logger.info(f"Trying candidate {i+1}/{len(top_images)}: {image_url[:80]}")

            local_path = await _download_image(image_url)
            if local_path:
                # Save remaining candidates as backups
                backup_images = top_images[i+1:]
                return {
                    "success": True,
                    "image_url": image_url,
                    "local_path": local_path,
                    "source": "serper",
                    "attribution": candidate.get("attribution"),
                    "selection_score": candidate.get("selection_score"),
                    "backup_images": backup_images,
                }

            logger.warning(f"Candidate {i+1} download failed, trying next...")

        logger.warning("All candidate image downloads failed")
        return {"success": False, "error": "All candidate downloads failed"}

    except ImportError as e:
        logger.warning(f"Image retrieval service not available: {e}")
        return {"success": False, "error": f"Service not available: {e}"}
    except Exception as e:
        logger.warning(f"Image retrieval failed: {e}")
        return {"success": False, "error": str(e)}


async def _download_image(image_url: str) -> Optional[str]:
    """
    Download image to local path for processing.

    Validates:
    - Rejects SVG URLs before attempting download
    - Sends User-Agent and Accept headers to avoid 403s
    - Validates Content-Type header (rejects text/html, application/json)
    - Validates minimum image dimensions (100x100)
    - Calls img.verify() for integrity check
    """
    try:
        import httpx
        from PIL import Image
        import io

        # Reject SVG URLs before downloading — PIL/YOLO can't process SVGs
        url_lower = image_url.lower()
        if url_lower.endswith(".svg") or ".svg?" in url_lower or "/svg/" in url_lower:
            logger.warning(f"Rejecting SVG URL: {image_url[:80]}")
            return None

        output_dir = WORKFLOW_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_path = output_dir / f"diagram_{timestamp}.png"

        # Use browser-like headers to avoid 403 errors
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(image_url, headers=headers)
            response.raise_for_status()

            # Validate Content-Type header
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type or "application/json" in content_type:
                logger.warning(f"Response is {content_type}, not an image: {image_url[:80]}")
                return None

            # Reject SVG content type
            if "image/svg+xml" in content_type:
                logger.warning(f"Response is SVG, skipping: {image_url[:80]}")
                return None

            content = response.content

            # Verify image integrity with PIL
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()

                # Re-open after verify (verify closes the file)
                img = Image.open(io.BytesIO(content))
                width, height = img.size

                # Validate minimum dimensions
                if width < 100 or height < 100:
                    logger.warning(f"Image too small ({width}x{height}), skipping: {image_url[:80]}")
                    return None

            except Exception as e:
                logger.warning(f"Image validation failed: {e}")
                return None

            # Convert to RGB PNG for consistent format
            img = Image.open(io.BytesIO(content))
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(output_path, format="PNG")

            logger.info(f"Downloaded image ({width}x{height}) to {output_path}")
            return str(output_path)

    except Exception as e:
        logger.warning(f"Failed to download image: {e}")
        return None


async def _generate_clean_diagram(
    local_path: Optional[str],
    context: WorkflowContext,
    canonical_labels: List[str],
) -> Dict[str, Any]:
    """
    Generate a clean, unlabeled, scientifically accurate diagram using Gemini Imagen.

    Reuses functions from diagram_image_generator agent:
    - build_generation_prompt(): Builds prompt emphasizing academic accuracy, no text/labels
    - generate_with_gemini(): Calls gemini-2.5-flash-image with optional reference

    Args:
        local_path: Path to reference image from step 1 (or None)
        context: WorkflowContext with domain_knowledge
        canonical_labels: List of expected labels

    Returns:
        Dict with success, generated_path, generator, duration_ms, error
    """
    try:
        from app.agents.diagram_image_generator import (
            build_generation_prompt,
            generate_with_gemini,
        )

        # Check if GOOGLE_API_KEY is available
        if not os.environ.get("GOOGLE_API_KEY"):
            return {
                "success": False,
                "error": "GOOGLE_API_KEY not set, skipping generation",
            }

        domain_knowledge = context.domain_knowledge
        hierarchical_relationships = domain_knowledge.get("hierarchical_relationships")

        # Extract subject from domain_knowledge or parse from query
        subject = domain_knowledge.get("subject", "")
        if not subject:
            query = context.get_spec_value("query", "")
            subject = query.replace("Label the parts of ", "").replace("Label ", "").strip()
            if subject.startswith("a "):
                subject = subject[2:]
            if subject.startswith("an "):
                subject = subject[3:]
            if subject.endswith("?"):
                subject = subject[:-1]

        if not subject:
            subject = "educational diagram"

        # Build generation prompt
        prompt = build_generation_prompt(
            subject=subject,
            canonical_labels=canonical_labels,
            visual_theme="clean educational",
            style_directive="scientific illustration",
            hierarchical_relationships=hierarchical_relationships,
        )

        logger.info(f"Generating clean diagram for subject: {subject}")

        # Call Gemini Imagen with reference image
        result = await generate_with_gemini(
            prompt=prompt,
            reference_image_path=local_path,
        )

        if result.get("success"):
            logger.info(
                f"Diagram generation succeeded: {result.get('generated_path')} "
                f"({result.get('duration_ms', 0)}ms)"
            )
            return {
                "success": True,
                "generated_path": result["generated_path"],
                "generator": result.get("generator", "gemini"),
                "duration_ms": result.get("duration_ms"),
            }

        # Generation failed — log but don't fail the workflow
        error = result.get("error", "Unknown generation error")
        logger.warning(f"Diagram generation failed: {error}")

        # Try prompt-only generation (no reference) as last resort
        if local_path:
            logger.info("Retrying generation without reference image")
            result = await generate_with_gemini(prompt=prompt, reference_image_path=None)
            if result.get("success"):
                logger.info(f"Prompt-only generation succeeded: {result.get('generated_path')}")
                return {
                    "success": True,
                    "generated_path": result["generated_path"],
                    "generator": result.get("generator", "gemini"),
                    "duration_ms": result.get("duration_ms"),
                }

        return {
            "success": False,
            "error": error,
        }

    except ImportError as e:
        logger.warning(f"diagram_image_generator not available: {e}")
        return {"success": False, "error": f"Generator not available: {e}"}
    except Exception as e:
        logger.warning(f"Diagram generation error: {e}")
        return {"success": False, "error": str(e)}


async def _detect_zones(
    image_path: Optional[str],
    image_url: Optional[str],
    canonical_labels: List[str],
    context: WorkflowContext
) -> Dict[str, Any]:
    """
    Detect zones in diagram using available detection methods.

    Tries methods in order of preference:
    1. Gemini Vision (if GOOGLE_API_KEY is set)
    2. Qwen VL via Ollama (if available)
    3. Fallback to placeholder zones
    """
    start_time = time.time()

    # Need either a local path or downloadable URL
    if not image_path and image_url:
        image_path = await _download_image(image_url)

    if not image_path or not Path(image_path).exists():
        logger.warning("No valid image path for zone detection")
        return {
            "success": False,
            "zones": _create_placeholder_zones(canonical_labels),
            "method": "placeholder",
            "error": "No valid image path"
        }

    # Try Gemini Vision first (if available)
    if os.environ.get("GOOGLE_API_KEY"):
        gemini_result = await _detect_zones_gemini(image_path, canonical_labels, context)
        if gemini_result.get("success"):
            gemini_result["duration_ms"] = int((time.time() - start_time) * 1000)
            return gemini_result
        logger.warning(f"Gemini detection failed: {gemini_result.get('error')}")

    # Try Qwen VL via Ollama as fallback
    try:
        qwen_result = await _detect_zones_qwen(image_path, canonical_labels)
        if qwen_result.get("success"):
            qwen_result["duration_ms"] = int((time.time() - start_time) * 1000)
            return qwen_result
        logger.warning(f"Qwen detection failed: {qwen_result.get('error')}")
    except Exception as e:
        logger.warning(f"Qwen VL not available: {e}")

    # Fallback to placeholder zones
    logger.warning("Using placeholder zones as fallback")
    return {
        "success": True,
        "zones": _create_placeholder_zones(canonical_labels),
        "method": "placeholder",
        "duration_ms": int((time.time() - start_time) * 1000)
    }


async def _detect_zones_gemini(
    image_path: str,
    canonical_labels: List[str],
    context: WorkflowContext
) -> Dict[str, Any]:
    """
    Detect zones using Gemini + SAM3 for pixel-precise polygon boundaries.

    Falls back to Gemini-only if SAM3 is unavailable.
    """
    try:
        from app.agents.gemini_sam3_zone_detector import (
            detect_zones_with_gemini_sam3,
            create_zone_groups_from_hierarchy,
        )

        domain_knowledge = context.domain_knowledge
        subject = domain_knowledge.get("subject", "")
        hierarchical_relationships = domain_knowledge.get("hierarchical_relationships")

        # Normalize hierarchical_relationships to list format
        hierarchy_list = None
        if hierarchical_relationships:
            if isinstance(hierarchical_relationships, list):
                hierarchy_list = hierarchical_relationships
            elif isinstance(hierarchical_relationships, dict):
                hierarchy_list = hierarchical_relationships.get("groups", [])

        result = await detect_zones_with_gemini_sam3(
            image_path=image_path,
            canonical_labels=canonical_labels,
            subject=subject,
            hierarchical_relationships=hierarchy_list,
        )

        if result.get("success"):
            zones = result.get("zones", [])
            # Normalize to standard format
            zones = _normalize_zones(zones)

            # Build zone groups from hierarchy
            zone_groups = create_zone_groups_from_hierarchy(hierarchy_list, zones)

            return {
                "success": True,
                "zones": zones,
                "zone_groups": zone_groups,
                "method": result.get("model", "gemini_sam3"),
                "parts_not_found": result.get("parts_not_found", []),
                "duration_ms": result.get("duration_ms"),
            }

        # SAM3 failed, try fallback to basic Gemini service
        logger.warning(f"SAM3 detection failed: {result.get('error')}, trying Gemini-only fallback")

    except ImportError:
        logger.warning("gemini_sam3_zone_detector not available, trying Gemini-only fallback")
    except Exception as e:
        logger.warning(f"SAM3 detection error: {e}, trying Gemini-only fallback")

    # Fallback: basic Gemini service (rect-only zones)
    try:
        from app.services.gemini_diagram_service import get_gemini_service

        service = get_gemini_service()
        result = await service.detect_zones(image_path, canonical_labels)

        if result.get("success"):
            zones = _normalize_zones(result.get("zones", []))
            return {
                "success": True,
                "zones": zones,
                "zone_groups": [],
                "method": "gemini_vision",
                "parts_not_found": result.get("parts_not_found", []),
                "call_id": result.get("call_id"),
            }

        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "zones": []
        }

    except ImportError:
        return {"success": False, "error": "No zone detection service available", "zones": []}
    except Exception as e:
        return {"success": False, "error": str(e), "zones": []}


async def _detect_zones_qwen(
    image_path: str,
    canonical_labels: List[str]
) -> Dict[str, Any]:
    """Detect zones using Qwen VL via direct structure locator."""
    try:
        from app.agents.direct_structure_locator import DirectStructureLocator

        locator = DirectStructureLocator()

        if not await locator.is_qwen_available():
            return {"success": False, "error": "Qwen VL not available", "zones": []}

        result = await locator.locate_all_structures(image_path, canonical_labels)

        if result.get("method") != "error":
            zones = _normalize_zones(result.get("zones", []))

            return {
                "success": True,
                "zones": zones,
                "method": "qwen_vl",
                "found_count": result.get("found_count", 0),
                "missing_count": result.get("missing_count", 0),
            }

        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "zones": []
        }

    except Exception as e:
        return {"success": False, "error": str(e), "zones": []}


def _to_native(val):
    """Convert numpy types to native Python types for msgpack serialization."""
    if hasattr(val, 'item'):
        return val.item()
    return val


def _normalize_zones(raw_zones: List[Dict[str, Any]]) -> List[DiagramZone]:
    """
    Normalize zones to standard DiagramZone format.

    Handles different input formats from various detection methods.
    Converts numpy types to native Python types for LangGraph checkpoint serialization.
    """
    normalized = []

    for i, zone in enumerate(raw_zones):
        zone_id = zone.get("id", f"zone_{i}")
        label = zone.get("label", "")

        # Normalize coordinates to percentage (0-100), convert numpy → native float
        x = float(_to_native(zone.get("x", 50)))
        y = float(_to_native(zone.get("y", 50)))

        # Ensure coordinates are in valid range
        x = max(0, min(100, x))
        y = max(0, min(100, y))

        # Determine shape and dimensions
        shape = zone.get("shape", "circle")
        if shape not in ["circle", "polygon", "rect"]:
            shape = "circle"

        normalized_zone: DiagramZone = {
            "id": zone_id,
            "label": label,
            "x": x,
            "y": y,
            "shape": shape,
            "confidence": float(_to_native(zone.get("confidence", 0.8))),
            "scene_number": int(_to_native(zone.get("scene_number", 1))),
            "mechanic_roles": zone.get("mechanic_roles", {}),
        }

        # Add shape-specific fields (convert numpy → native)
        if shape == "circle":
            normalized_zone["radius"] = float(_to_native(zone.get("radius", 5)))
        elif shape == "rect":
            normalized_zone["width"] = float(_to_native(zone.get("width", 10)))
            normalized_zone["height"] = float(_to_native(zone.get("height", 10)))
        elif shape == "polygon":
            points = zone.get("points", [])
            if points and isinstance(points, list):
                # Convert nested numpy arrays/values to native Python floats
                normalized_zone["points"] = [
                    [float(_to_native(c)) for c in pt] if isinstance(pt, (list, tuple)) else pt
                    for pt in points
                ]

        # Hierarchy fields (from SAM3 _add_hierarchy_to_zones)
        if zone.get("parentZoneId"):
            normalized_zone["parentZoneId"] = zone["parentZoneId"]
        if zone.get("hierarchyLevel"):
            normalized_zone["hierarchyLevel"] = int(_to_native(zone["hierarchyLevel"]))
        if zone.get("childZoneIds"):
            normalized_zone["childZoneIds"] = zone["childZoneIds"]

        # Optional fields
        if zone.get("hint"):
            normalized_zone["hint"] = zone["hint"]
        if zone.get("difficulty"):
            normalized_zone["difficulty"] = zone["difficulty"]

        normalized.append(normalized_zone)

    return normalized


def _create_placeholder_zones(labels: List[str]) -> List[DiagramZone]:
    """
    Create placeholder zones when detection fails.

    Distributes zones in a grid pattern across the image.
    """
    zones = []
    n = len(labels) or 1

    # Calculate grid layout
    cols = min(n, 3)
    rows = (n + cols - 1) // cols

    for i, label in enumerate(labels):
        row = i // cols
        col = i % cols

        # Calculate position with padding
        x = 20 + (col * 60 / max(cols - 1, 1)) if cols > 1 else 50
        y = 20 + (row * 60 / max(rows - 1, 1)) if rows > 1 else 50

        zone: DiagramZone = {
            "id": f"zone_{label.lower().replace(' ', '_')}",
            "label": label,
            "x": x,
            "y": y,
            "shape": "circle",
            "radius": 5.0,
            "confidence": 0.3,
            "scene_number": 1,
            "mechanic_roles": {},
        }
        zones.append(zone)

    return zones


def _create_labels_from_zones(
    zones: List[DiagramZone],
    domain_knowledge: Dict[str, Any]
) -> List[DiagramLabel]:
    """
    Create labels from zones and domain knowledge.

    Enriches labels with canonical status and variants from domain knowledge.
    """
    labels = []
    canonical = domain_knowledge.get("canonical_labels", [])
    variants = domain_knowledge.get("acceptable_variants", {})

    # Create a set for efficient lookup
    canonical_set = set(label.lower() for label in canonical)

    for zone in zones:
        zone_label = zone.get("label", "")
        if not zone_label:
            continue

        label_id = f"label_{zone.get('id', '')}"

        # Check if this is a canonical label (case-insensitive)
        is_canonical = zone_label.lower() in canonical_set

        # Get variants for this label
        label_variants = variants.get(zone_label, [])

        # Also check with case variations
        if not label_variants:
            for key in variants:
                if key.lower() == zone_label.lower():
                    label_variants = variants[key]
                    break

        label: DiagramLabel = {
            "id": label_id,
            "text": zone_label,
            "zone_id": zone.get("id"),
            "is_canonical": is_canonical,
            "variants": label_variants,
        }

        # Add hint if available from zone
        if zone.get("hint"):
            label["hint"] = zone["hint"]

        labels.append(label)

    return labels
