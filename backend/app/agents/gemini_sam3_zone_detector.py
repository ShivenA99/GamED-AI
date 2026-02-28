"""
Gemini + SAM 3 Zone Detector Agent

Combines Gemini's semantic understanding with SAM 3's pixel-precise segmentation
for academically accurate zone detection in educational diagrams.

Architecture:
    1. Gemini analyzes the image and generates optimal SAM 3 prompts for each label
    2. SAM 3 produces pixel-precise segmentation masks
    3. Masks are converted to smooth polygons using OpenCV
    4. Optional: Gemini validates the segmentation results

This approach achieves significantly better boundary precision than Gemini-only detection.

Research basis:
    - SAM 3 Agent with Gemini achieves 76.0 gIoU on ReasonSeg (+16.9% vs previous best)
    - "Gemini 2.5 and 3 Flash produce the best results" for SAM 3 Agent workflows
    - SAM 3 alone: 54.1 cgF1 vs Gemini 2.5 alone: 13.0 cgF1 on concept segmentation

Inputs:
    - generated_diagram_path OR cleaned_image_path OR diagram_image
    - canonical_labels: From domain_knowledge
    - hierarchical_relationships: From domain_knowledge

Outputs:
    - diagram_zones: List of zones with precise polygon boundaries
    - diagram_labels: Matching labels for zones
    - zone_groups: Hierarchical groupings for progressive reveal
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.interactive_diagram import normalize_zones, create_labels_from_zones
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.gemini_sam3_zone_detector")

# Output directory for zone detection results
OUTPUT_DIR = Path("pipeline_outputs/sam3_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Flag to track SAM availability
SAM_AVAILABLE = False
SAM_BACKEND = None  # 'ultralytics', 'sam3_pytorch', or None
sam_model = None

def _check_sam_availability():
    """
    Check if SAM is installed and available.

    Tries in order:
    1. Ultralytics SAM (works on CPU, CUDA, and Apple Silicon MPS)
    2. PyTorch SAM 3 (requires CUDA/triton)
    3. Falls back to Gemini-only
    """
    global SAM_AVAILABLE, SAM_BACKEND

    # Try Ultralytics SAM first (cross-platform)
    try:
        from ultralytics import SAM
        SAM_AVAILABLE = True
        SAM_BACKEND = "ultralytics"
        logger.info("SAM (Ultralytics) is available")
        return True
    except ImportError as e:
        logger.debug(f"Ultralytics SAM not available: {e}")

    # Try PyTorch SAM 3 (CUDA only)
    try:
        import torch
        from sam3 import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor
        SAM_AVAILABLE = True
        SAM_BACKEND = "sam3_pytorch"
        logger.info("SAM 3 (PyTorch/CUDA) is available")
        return True
    except ImportError as e:
        logger.debug(f"PyTorch SAM 3 not available: {e}")

    # No SAM available
    logger.warning(
        "SAM not available. Install with:\n"
        "  - pip install ultralytics (recommended, works on all platforms)\n"
        "  - pip install sam3 (requires CUDA)\n"
        "Using Gemini-only fallback for zone detection."
    )
    SAM_AVAILABLE = False
    SAM_BACKEND = None
    return False

def _initialize_sam():
    """Initialize SAM model (lazy loading)."""
    global sam_model, SAM_BACKEND
    if sam_model is not None:
        return sam_model

    if SAM_BACKEND == "ultralytics":
        try:
            from ultralytics import SAM

            logger.info("Initializing SAM (Ultralytics) model...")
            # Use SAM 2.1 base model - good balance of speed and accuracy
            sam_model = SAM("sam2.1_b.pt")
            logger.info(f"SAM (Ultralytics) initialized on device: {sam_model.device}")
            return sam_model
        except Exception as e:
            logger.error(f"Failed to initialize Ultralytics SAM: {e}")
            return None

    elif SAM_BACKEND == "sam3_pytorch":
        try:
            import torch
            from sam3 import build_sam3_image_model
            from sam3.model.sam3_image_processor import Sam3Processor

            logger.info("Initializing SAM 3 (PyTorch) model...")
            model = build_sam3_image_model()
            sam_model = Sam3Processor(model, confidence_threshold=0.3)
            logger.info("SAM 3 (PyTorch) model initialized successfully")
            return sam_model
        except Exception as e:
            logger.error(f"Failed to initialize PyTorch SAM 3: {e}")
            return None

    else:
        logger.warning("No SAM backend available")
        return None


# Legacy compatibility aliases
SAM3_AVAILABLE = SAM_AVAILABLE
SAM3_BACKEND = SAM_BACKEND
sam3_processor = sam_model

def _check_sam3_availability():
    """Legacy compatibility wrapper."""
    global SAM3_AVAILABLE, SAM3_BACKEND, sam3_processor
    result = _check_sam_availability()
    SAM3_AVAILABLE = SAM_AVAILABLE
    SAM3_BACKEND = SAM_BACKEND
    sam3_processor = sam_model
    return result

def _initialize_sam3():
    """Legacy compatibility wrapper."""
    global sam3_processor
    result = _initialize_sam()
    sam3_processor = sam_model
    return result


async def get_sam3_prompts_from_gemini(
    image: Image.Image,
    label: str,
    subject: str,
    all_labels: List[str],
    hierarchical_info: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Use Gemini to generate optimal SAM 3 prompts and bounding box for a label.

    Gemini analyzes the image semantically and provides:
    1. Simple noun phrases that SAM 3 can understand
    2. Approximate bounding box to help SAM 3 focus
    3. Visual description for validation

    Args:
        image: PIL Image of the diagram
        label: The anatomical/structural label to segment
        subject: Subject matter (e.g., "human heart")
        all_labels: All labels being detected (for context)
        hierarchical_info: Parent-child relationships

    Returns:
        Dict with prompts, bounding_box, and description
    """
    try:
        from google import genai
        from google.genai import types
        import io
        import base64

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not set")
            return {"prompts": [label], "error": "No API key"}

        client = genai.Client(api_key=api_key)

        # Build context about other structures
        other_labels = [l for l in all_labels if l != label]
        hierarchy_context = ""
        if hierarchical_info:
            hierarchy_context = f"\nHierarchy context: {json.dumps(hierarchical_info)}"

        prompt = f"""You are an expert anatomist analyzing a {subject} diagram for precise segmentation.

TASK: Generate optimal prompts for SAM 3 (Segment Anything Model 3) to precisely segment the "{label}" structure.

Other structures in this diagram: {', '.join(other_labels[:10])}
{hierarchy_context}

REQUIREMENTS:
1. Provide 1-3 simple noun phrases that describe the VISUAL appearance of "{label}"
   - Focus on color, texture, shape, and relative position
   - SAM 3 works best with concrete visual descriptions
   - Example: For "Right Ventricle" → ["right ventricle", "thick muscular chamber on right", "red-pink triangular cavity"]

2. Provide an approximate bounding box [x_min, y_min, x_max, y_max] as percentages (0-100)
   - This helps SAM 3 focus on the correct region
   - Be generous with the box (include some margin)

3. Provide a brief visual description for validation

CRITICAL FOR ACADEMIC ACCURACY:
- The "{label}" must be identified with ANATOMICAL PRECISION
- Consider the standard orientation of {subject} diagrams
- Distinguish "{label}" from nearby/overlapping structures

Return ONLY valid JSON in this exact format:
{{
  "prompts": ["prompt1", "prompt2"],
  "bounding_box": [x_min, y_min, x_max, y_max],
  "visual_description": "Brief description of what {label} looks like in this image",
  "confidence": 0.95
}}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )

        result = json.loads(response.text)
        result["label"] = label
        return result

    except Exception as e:
        logger.error(f"Gemini prompt generation failed for {label}: {e}")
        # Fallback: just use the label itself
        return {
            "prompts": [label, f"{label} in {subject}"],
            "bounding_box": [0, 0, 100, 100],
            "visual_description": f"The {label} structure",
            "confidence": 0.5,
            "error": str(e),
        }


def segment_with_sam(
    image_path: str,
    bounding_box: Optional[List[float]] = None,
    point: Optional[List[float]] = None,
) -> Optional[np.ndarray]:
    """
    Run SAM segmentation with bounding box or point prompt.

    Ultralytics SAM uses visual prompts (boxes, points) rather than text.
    Gemini provides the bounding box based on semantic understanding.

    Args:
        image_path: Path to the image file
        bounding_box: Optional [x_min, y_min, x_max, y_max] in pixels
        point: Optional [x, y] point coordinates in pixels

    Returns:
        Binary mask as numpy array, or None if failed
    """
    global SAM_BACKEND

    model = _initialize_sam()
    if model is None:
        return None

    try:
        if SAM_BACKEND == "ultralytics":
            # Ultralytics SAM API
            if bounding_box is not None:
                # Use bounding box prompt
                results = model(image_path, bboxes=[bounding_box])
            elif point is not None:
                # Use point prompt
                results = model(image_path, points=[point], labels=[1])
            else:
                # Auto-segment entire image
                results = model(image_path)

            if results and len(results) > 0:
                result = results[0]
                if result.masks is not None and len(result.masks.data) > 0:
                    # Get the mask with highest confidence
                    masks = result.masks.data.cpu().numpy()
                    if len(masks) > 0:
                        # Return the first (best) mask
                        mask = masks[0]
                        logger.debug(f"SAM segmentation successful, mask shape: {mask.shape}")
                        return mask

            logger.warning("SAM returned no masks")
            return None

        elif SAM_BACKEND == "sam3_pytorch":
            # PyTorch SAM 3 API
            from PIL import Image
            image = Image.open(image_path)
            inference_state = model.set_image(image)

            if bounding_box is not None:
                output = model.set_box_prompt(
                    state=inference_state,
                    box=bounding_box
                )
            elif point is not None:
                output = model.set_point_prompt(
                    state=inference_state,
                    points=[point],
                    labels=[1]
                )
            else:
                return None

            masks = output.get("masks")
            if masks is not None and len(masks) > 0:
                return masks[0]

            return None

        else:
            logger.warning(f"Unknown SAM backend: {SAM_BACKEND}")
            return None

    except Exception as e:
        logger.error(f"SAM segmentation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


# Legacy compatibility alias
def segment_with_sam3(
    image: Image.Image,
    prompts: List[str],
    bounding_box: Optional[List[float]] = None,
) -> Optional[np.ndarray]:
    """Legacy wrapper - converts to new API."""
    import tempfile

    # Save image to temp file for Ultralytics
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        image.save(f.name)
        temp_path = f.name

    try:
        # Convert percentage bounding box to pixels if provided
        if bounding_box is not None:
            w, h = image.size
            pixel_box = [
                bounding_box[0] * w / 100,  # x_min
                bounding_box[1] * h / 100,  # y_min
                bounding_box[2] * w / 100,  # x_max
                bounding_box[3] * h / 100,  # y_max
            ]
            return segment_with_sam(temp_path, bounding_box=pixel_box)
        else:
            # Use center point as fallback
            w, h = image.size
            center_point = [w / 2, h / 2]
            return segment_with_sam(temp_path, point=center_point)
    finally:
        # Cleanup temp file
        try:
            os.unlink(temp_path)
        except:
            pass


def mask_to_polygon(
    mask: np.ndarray,
    simplify_tolerance: float = 0.5,
    min_points: int = 8,
    max_points: int = 100,
) -> Optional[List[List[float]]]:
    """
    Convert binary mask to smooth polygon using OpenCV.

    Uses Douglas-Peucker algorithm for simplification while maintaining
    enough points for smooth curves.

    Args:
        mask: Binary mask as numpy array
        simplify_tolerance: Tolerance for Douglas-Peucker (lower = more points)
        min_points: Minimum number of polygon points
        max_points: Maximum number of polygon points

    Returns:
        List of [x, y] coordinate pairs as percentages (0-100)
    """
    try:
        import cv2
    except ImportError:
        logger.error("OpenCV not available for mask to polygon conversion")
        return None

    if mask is None or mask.size == 0:
        return None

    # Ensure mask is uint8
    if mask.dtype == bool:
        mask_uint8 = mask.astype(np.uint8) * 255
    else:
        mask_uint8 = (mask * 255).astype(np.uint8) if mask.max() <= 1 else mask.astype(np.uint8)

    # Find contours
    contours, _ = cv2.findContours(
        mask_uint8,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return None

    # Get largest contour
    largest_contour = max(contours, key=cv2.contourArea)

    if cv2.contourArea(largest_contour) < 100:  # Too small
        return None

    # Simplify contour with Douglas-Peucker algorithm
    # Start with a small epsilon and increase if too many points
    perimeter = cv2.arcLength(largest_contour, True)
    epsilon = simplify_tolerance * perimeter / 100

    simplified = cv2.approxPolyDP(largest_contour, epsilon, True)

    # If too many points, increase epsilon
    while len(simplified) > max_points and epsilon < perimeter / 10:
        epsilon *= 1.5
        simplified = cv2.approxPolyDP(largest_contour, epsilon, True)

    # If too few points, decrease epsilon
    while len(simplified) < min_points and epsilon > 0.1:
        epsilon *= 0.5
        simplified = cv2.approxPolyDP(largest_contour, epsilon, True)

    # Convert to percentage coordinates (0-100)
    h, w = mask.shape[:2]
    polygon = []
    for point in simplified:
        x_pct = round(float(point[0][0]) / w * 100, 1)
        y_pct = round(float(point[0][1]) / h * 100, 1)
        polygon.append([x_pct, y_pct])

    return polygon


def calculate_centroid(polygon: List[List[float]]) -> Dict[str, float]:
    """Calculate the centroid of a polygon."""
    if not polygon:
        return {"x": 50.0, "y": 50.0}

    x_coords = [p[0] for p in polygon]
    y_coords = [p[1] for p in polygon]

    return {
        "x": round(sum(x_coords) / len(x_coords), 1),
        "y": round(sum(y_coords) / len(y_coords), 1),
    }


def calculate_polygon_bounds(polygon: List[List[float]]) -> Dict[str, float]:
    """Calculate bounding box of a polygon."""
    if not polygon:
        return {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100}

    x_coords = [p[0] for p in polygon]
    y_coords = [p[1] for p in polygon]

    return {
        "min_x": min(x_coords),
        "min_y": min(y_coords),
        "max_x": max(x_coords),
        "max_y": max(y_coords),
    }


async def detect_single_zone_with_sam3(
    image: Image.Image,
    label: str,
    subject: str,
    all_labels: List[str],
    hierarchical_info: Optional[Dict] = None,
) -> Optional[Dict[str, Any]]:
    """
    Detect a single zone using Gemini + SAM 3 pipeline.

    Args:
        image: PIL Image
        label: Label to detect
        subject: Subject matter
        all_labels: All labels for context
        hierarchical_info: Hierarchy information

    Returns:
        Zone dict with polygon boundary, or None if failed
    """
    start_time = time.time()

    # Step 1: Get SAM 3 prompts from Gemini
    gemini_result = await get_sam3_prompts_from_gemini(
        image=image,
        label=label,
        subject=subject,
        all_labels=all_labels,
        hierarchical_info=hierarchical_info,
    )

    prompts = gemini_result.get("prompts", [label])
    bounding_box = gemini_result.get("bounding_box")

    logger.info(f"Gemini generated prompts for '{label}': {prompts}")

    # Step 2: Run SAM 3 segmentation
    mask = segment_with_sam3(image, prompts, bounding_box)

    if mask is None:
        logger.warning(f"SAM 3 segmentation failed for '{label}'")
        return None

    # Step 3: Convert mask to polygon
    polygon = mask_to_polygon(mask, simplify_tolerance=0.3, min_points=12, max_points=80)

    if polygon is None or len(polygon) < 3:
        logger.warning(f"Polygon conversion failed for '{label}'")
        return None

    # Calculate zone properties
    centroid = calculate_centroid(polygon)
    bounds = calculate_polygon_bounds(polygon)

    duration_ms = int((time.time() - start_time) * 1000)

    zone = {
        "id": f"zone_{label.lower().replace(' ', '_').replace('-', '_')}",
        "label": label,
        "zone_type": "area",
        "shape": "polygon",
        "points": polygon,
        "center": centroid,
        "x": centroid["x"],
        "y": centroid["y"],
        "confidence": gemini_result.get("confidence", 0.9),
        "visible": True,
        "source": "gemini_sam3",
        "detection_metadata": {
            "gemini_prompts": prompts,
            "visual_description": gemini_result.get("visual_description", ""),
            "polygon_points": len(polygon),
            "duration_ms": duration_ms,
        },
    }

    logger.info(f"Detected zone '{label}' with {len(polygon)} polygon points")

    return zone


async def fallback_gemini_only_detection(
    image_path: str,
    canonical_labels: List[str],
    subject: str,
    hierarchical_relationships: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Fallback to Gemini-only detection when SAM 3 is not available.

    This uses the existing Gemini zone detection with enhanced prompting
    for more polygon points.
    """
    from app.agents.gemini_zone_detector import detect_zones_with_gemini

    logger.info("Using Gemini-only fallback for zone detection")

    return await detect_zones_with_gemini(
        image_path=image_path,
        canonical_labels=canonical_labels,
        subject=subject,
        use_polygon_zones=True,
        hierarchy_depth=10,
        hierarchical_relationships=hierarchical_relationships,
        intelligent_zone_types=True,
    )


async def detect_zones_with_gemini_sam3(
    image_path: str,
    canonical_labels: List[str],
    subject: str = "",
    hierarchical_relationships: Optional[List[Dict]] = None,
    max_concurrent: int = 3,
) -> Dict[str, Any]:
    """
    Main zone detection function using Gemini + SAM 3 pipeline.

    Args:
        image_path: Path to diagram image
        canonical_labels: Labels to detect
        subject: Subject matter for context
        hierarchical_relationships: Parent-child relationships
        max_concurrent: Max concurrent detection tasks

    Returns:
        Dict with zones, metadata, and status
    """
    start_time = time.time()

    # Check SAM 3 availability
    if not _check_sam3_availability():
        logger.warning("SAM 3 not available, trying Gemini native mask detection")

        # Try native mask-based detection first (pixel-precise via Gemini segmentation API)
        try:
            from app.agents.gemini_zone_detector import detect_zones_with_gemini_masks
            mask_result = await detect_zones_with_gemini_masks(
                image_path=image_path,
                canonical_labels=canonical_labels,
                subject=subject,
                hierarchical_relationships=hierarchical_relationships,
            )
            if mask_result.get("success"):
                logger.info("Gemini native mask detection succeeded")
                return mask_result
            logger.warning(f"Gemini mask detection failed: {mask_result.get('error')}")
        except Exception as e:
            logger.warning(f"Gemini mask detection error: {e}")

        # Fall back to text-based polygon detection
        logger.info("Falling back to Gemini text-based polygon detection")
        return await fallback_gemini_only_detection(
            image_path=image_path,
            canonical_labels=canonical_labels,
            subject=subject,
            hierarchical_relationships=hierarchical_relationships,
        )

    # Load image
    try:
        image = Image.open(image_path)
        img_width, img_height = image.size
        logger.info(f"Loaded image: {img_width}x{img_height}")
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        return {
            "success": False,
            "error": f"Failed to load image: {e}",
            "zones": [],
        }

    # Build hierarchy info for context
    hierarchy_info = None
    if hierarchical_relationships:
        hierarchy_info = {"relationships": hierarchical_relationships}

    # Detect zones concurrently (with semaphore to limit concurrency)
    semaphore = asyncio.Semaphore(max_concurrent)

    async def detect_with_semaphore(label: str) -> Optional[Dict]:
        async with semaphore:
            return await detect_single_zone_with_sam3(
                image=image,
                label=label,
                subject=subject,
                all_labels=canonical_labels,
                hierarchical_info=hierarchy_info,
            )

    # Run detection for all labels
    tasks = [detect_with_semaphore(label) for label in canonical_labels]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect successful zones
    zones = []
    parts_not_found = []

    for label, result in zip(canonical_labels, results):
        if isinstance(result, Exception):
            logger.error(f"Detection failed for '{label}': {result}")
            parts_not_found.append(label)
        elif result is None:
            parts_not_found.append(label)
        else:
            zones.append(result)

    # Add hierarchy information to zones
    if hierarchical_relationships:
        zones = _add_hierarchy_to_zones(zones, hierarchical_relationships)
        zones = _subtract_child_polygons(zones)

    duration_ms = int((time.time() - start_time) * 1000)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"sam3_zones_{timestamp}.json"

    output_data = {
        "zones": zones,
        "image_analysis": {
            "subject": subject,
            "quality": "good",
            "dimensions": {"width": img_width, "height": img_height},
        },
        "parts_not_found": parts_not_found,
        "canonical_labels": canonical_labels,
        "duration_ms": duration_ms,
        "model": "gemini-2.5-flash + sam3",
        "use_polygon_zones": True,
    }

    try:
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Saved zone detection results to {output_file}")
    except Exception as e:
        logger.warning(f"Failed to save results: {e}")

    return {
        "success": True,
        "zones": zones,
        "parts_not_found": parts_not_found,
        "image_analysis": output_data["image_analysis"],
        "duration_ms": duration_ms,
        "model": "gemini-2.5-flash + sam3",
        "output_file": str(output_file),
    }


def _add_hierarchy_to_zones(
    zones: List[Dict],
    hierarchical_relationships: List[Dict],
) -> List[Dict]:
    """Add hierarchy level and parent info to zones."""
    # Build parent-child map
    parent_map = {}  # child_label -> parent_label
    for rel in hierarchical_relationships:
        parent = rel.get("parent", "")
        children = rel.get("children", []) or rel.get("members", [])
        for child in children:
            parent_map[child.lower()] = parent.lower()

    # Calculate hierarchy levels
    def get_hierarchy_level(label: str, visited: set = None) -> int:
        if visited is None:
            visited = set()
        label_lower = label.lower()
        if label_lower in visited:
            return 1  # Circular reference protection
        visited.add(label_lower)

        parent = parent_map.get(label_lower)
        if not parent:
            return 1
        return 1 + get_hierarchy_level(parent, visited)

    # Update zones
    for zone in zones:
        label = zone.get("label", "")
        label_lower = label.lower()

        zone["hierarchyLevel"] = get_hierarchy_level(label)

        parent = parent_map.get(label_lower)
        if parent:
            zone["parentZoneId"] = f"zone_{parent.replace(' ', '_')}"

    return zones


def _subtract_child_polygons(zones: List[Dict]) -> List[Dict]:
    """
    Subtract child zone polygons from parent zone polygons.

    SAM3 produces nested masks where parent zones fully encompass their children,
    causing ~80-90% overlap. This subtracts child polygons from parent polygons
    to create "donut" shapes so drop targets don't overlap.

    Uses Shapely for polygon difference operations.
    """
    try:
        from shapely.geometry import Polygon as ShapelyPolygon
        from shapely.ops import unary_union
    except ImportError:
        logger.warning("Shapely not available, skipping polygon subtraction")
        return zones

    # Build zone lookup by id
    zone_by_id = {z.get("id", ""): z for z in zones}

    # Build parent → children map
    parent_children: Dict[str, List[str]] = {}
    for zone in zones:
        parent_id = zone.get("parentZoneId")
        if parent_id:
            parent_children.setdefault(parent_id, []).append(zone.get("id", ""))

    # For each parent with children, subtract child polygons
    for parent_id, child_ids in parent_children.items():
        parent_zone = zone_by_id.get(parent_id)
        if not parent_zone or parent_zone.get("shape") != "polygon":
            continue

        parent_points = parent_zone.get("points", [])
        if len(parent_points) < 3:
            continue

        # Convert parent polygon to Shapely
        try:
            parent_poly = ShapelyPolygon([(p[0], p[1]) for p in parent_points])
            if not parent_poly.is_valid:
                parent_poly = parent_poly.buffer(0)  # Fix invalid geometry
        except Exception:
            continue

        # Collect valid child polygons
        child_polys = []
        for child_id in child_ids:
            child_zone = zone_by_id.get(child_id)
            if not child_zone or child_zone.get("shape") != "polygon":
                continue
            child_points = child_zone.get("points", [])
            if len(child_points) < 3:
                continue
            try:
                child_poly = ShapelyPolygon([(p[0], p[1]) for p in child_points])
                if not child_poly.is_valid:
                    child_poly = child_poly.buffer(0)
                child_polys.append(child_poly)
            except Exception:
                continue

        if not child_polys:
            continue

        # Subtract union of children from parent
        try:
            children_union = unary_union(child_polys)
            result = parent_poly.difference(children_union)

            if result.is_empty:
                logger.warning(f"Parent zone {parent_id} is empty after subtraction, keeping original")
                continue

            # If MultiPolygon, take the largest piece
            if result.geom_type == "MultiPolygon":
                result = max(result.geoms, key=lambda g: g.area)

            # Extract exterior coordinates back to percentage format
            new_points = [
                [round(x, 1), round(y, 1)]
                for x, y in result.exterior.coords[:-1]  # Exclude closing point
            ]

            if len(new_points) >= 3:
                parent_zone["points"] = new_points
                # Update centroid
                centroid = calculate_centroid(new_points)
                parent_zone["x"] = centroid["x"]
                parent_zone["y"] = centroid["y"]
                if "center" in parent_zone:
                    parent_zone["center"] = centroid
                logger.info(
                    f"Subtracted {len(child_polys)} child polygons from parent {parent_id}: "
                    f"{len(parent_points)} pts → {len(new_points)} pts"
                )

        except Exception as e:
            logger.warning(f"Polygon subtraction failed for {parent_id}: {e}")
            continue

    return zones


def create_zone_groups_from_hierarchy(
    hierarchical_relationships: Optional[List[Dict]],
    zones: List[Dict],
) -> List[Dict]:
    """Create zone groups from hierarchical relationships."""
    if not hierarchical_relationships:
        return []

    zone_id_map = {z.get("label", "").lower(): z.get("id") for z in zones}
    zone_groups = []

    for rel in hierarchical_relationships:
        parent_label = rel.get("parent", "")
        children = rel.get("children", []) or rel.get("members", [])

        parent_id = zone_id_map.get(parent_label.lower())
        if not parent_id:
            continue

        child_ids = []
        for child in children:
            child_id = zone_id_map.get(child.lower())
            if child_id:
                child_ids.append(child_id)

        if child_ids:
            zone_groups.append({
                "id": f"group_{parent_label.lower().replace(' ', '_')}",
                "parentZoneId": parent_id,
                "childZoneIds": child_ids,
                "revealTrigger": "complete_parent",
                "label": parent_label,
            })

    return zone_groups


# =============================================================================
# MAIN AGENT FUNCTION
# =============================================================================

async def gemini_sam3_zone_detector(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Gemini + SAM 3 Zone Detector Agent.

    Combines Gemini's semantic understanding with SAM 3's pixel-precise
    segmentation for academically accurate zone boundaries.

    This replaces the pure Gemini zone detector for better boundary precision.
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")

    logger.info(f"Starting Gemini + SAM 3 zone detection for {question_id}")

    # Check if this is a INTERACTIVE_DIAGRAM template
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.warning(f"gemini_sam3_zone_detector called for non-INTERACTIVE_DIAGRAM template: {template_type}")
        return {
            "current_agent": "gemini_sam3_zone_detector",
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    # Determine which image to use (priority: generated > cleaned > diagram_image)
    image_path = state.get("generated_diagram_path")
    if not image_path or not os.path.exists(image_path):
        image_path = state.get("cleaned_image_path")
    if not image_path or not os.path.exists(image_path):
        diagram_image = state.get("diagram_image", {})
        image_path = diagram_image.get("generated_path") or diagram_image.get("local_path")

    if not image_path or not os.path.exists(image_path):
        logger.error("No valid image path found for zone detection")
        return {
            "current_agent": "gemini_sam3_zone_detector",
            "current_validation_errors": ["No valid image path found for zone detection"],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    logger.info(f"Using image for zone detection: {image_path}")

    # Get domain knowledge
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    canonical_labels = list(domain_knowledge.get("canonical_labels", []) or [])
    hierarchical_relationships = domain_knowledge.get("hierarchical_relationships")

    if not canonical_labels:
        logger.warning("No canonical labels found, using question for label extraction")
        question_text = state.get("question_text", "")
        subject = question_text.replace("Label the parts of ", "").replace("Label ", "").strip()
        if subject.endswith("?"):
            subject = subject[:-1]
    else:
        subject = state.get("pedagogical_context", {}).get("subject", "")

    logger.info(f"Detecting zones for {len(canonical_labels)} labels using Gemini + SAM 3")

    # Convert hierarchical_relationships to list if needed
    hierarchy_list = None
    if hierarchical_relationships:
        if isinstance(hierarchical_relationships, list):
            hierarchy_list = hierarchical_relationships
        elif isinstance(hierarchical_relationships, dict):
            hierarchy_list = hierarchical_relationships.get("groups", [])

    # Detect zones with Gemini + SAM 3
    result = await detect_zones_with_gemini_sam3(
        image_path=image_path,
        canonical_labels=canonical_labels,
        subject=subject,
        hierarchical_relationships=hierarchy_list,
    )

    if not result.get("success"):
        error_msg = result.get("error", "Zone detection failed")
        logger.error(f"Gemini + SAM 3 zone detection failed: {error_msg}")

        if ctx:
            ctx.set_fallback_used(f"Detection failed: {error_msg}")

        return {
            "current_agent": "gemini_sam3_zone_detector",
            "current_validation_errors": [f"Zone detection failed: {error_msg}"],
            "last_updated_at": datetime.utcnow().isoformat(),
            "_used_fallback": True,
            "_fallback_reason": error_msg,
        }

    raw_zones = result.get("zones", [])
    logger.info(f"Detected {len(raw_zones)} zones with SAM 3 precision")

    # Normalize zones
    zones = normalize_zones(raw_zones)

    # Create labels from zones
    diagram_labels = create_labels_from_zones(zones)

    # Create zone groups
    zone_groups = create_zone_groups_from_hierarchy(hierarchy_list, zones)
    logger.info(f"Created {len(zone_groups)} zone groups")

    # Track metrics
    if ctx:
        ctx.set_llm_metrics(
            model=result.get("model", "gemini-2.5-flash + sam3"),
            latency_ms=result.get("duration_ms", 0),
        )

    # Check for missing labels
    parts_not_found = result.get("parts_not_found", [])
    if parts_not_found:
        logger.warning(f"Parts not found in image: {parts_not_found}")

    # Build entity registry
    from app.agents.gemini_zone_detector import zones_to_entity_registry
    current_scene = state.get("current_scene_number", 1) or 1
    existing_registry = state.get("entity_registry")

    entity_registry = zones_to_entity_registry(
        zones=zones,
        scene_number=current_scene,
        existing_registry=existing_registry,
    )

    return {
        "diagram_zones": zones,
        "diagram_labels": diagram_labels,
        "zone_groups": zone_groups,
        "zone_detection_method": "gemini_sam3",
        "entity_registry": entity_registry,
        "zone_detection_metadata": {
            "model": result.get("model"),
            "duration_ms": result.get("duration_ms"),
            "image_analysis": result.get("image_analysis", {}),
            "parts_not_found": parts_not_found,
            "output_file": result.get("output_file"),
            "detected_at": datetime.utcnow().isoformat(),
            "use_polygon_zones": True,
            "sam3_available": SAM3_AVAILABLE,
            "entity_registry_zones_count": len(entity_registry.get("zones", {})),
        },
        "current_agent": "gemini_sam3_zone_detector",
        "last_updated_at": datetime.utcnow().isoformat(),
    }
