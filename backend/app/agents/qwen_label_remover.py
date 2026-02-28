# =============================================================================
# DEPRECATED: This agent has been superseded by:
#   - image_label_remover.py (for text-only removal)
#   - qwen_annotation_detector.py (for annotation detection)
#
# Kept for reference. Not included in the production pipeline graph.
# See DEPRECATED.md for details.
# =============================================================================

"""
Qwen2.5-VL Label Remover Agent (DEPRECATED)

Detects and removes text labels AND leader lines from diagram images using
Qwen2.5-VL for detection and LaMa/IOPaint for high-quality inpainting.

This agent replaces the original image_label_remover which only detected text
(missing leader lines) and used lower-quality OpenCV inpainting.

Key improvements:
1. Detects BOTH text labels AND connecting leader lines
2. Uses VLM for more accurate annotation detection
3. Supports LaMa/IOPaint for cleaner inpainting results
4. Falls back to OpenCV inpainting if LaMa unavailable
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.qwen_vl_service import get_qwen_vl_service, QwenVLError
from app.services.inpainting_service import get_inpainting_service
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.qwen_label_remover")


async def _download_image(image_url: str, output_path: Path) -> None:
    """Download image from URL to local path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        output_path.write_bytes(response.content)


async def _inpaint_with_stable_diffusion_or_fallback(
    image_path: str,
    mask_path: str,
    output_path: str
) -> str:
    """
    Inpaint image using Stable Diffusion if available, otherwise fall back to LaMa/OpenCV.
    
    Args:
        image_path: Path to source image
        mask_path: Path to mask image (white=inpaint, black=keep)
        output_path: Path for output image
        
    Returns:
        Path to inpainted image
    """
    # Try Stable Diffusion first (best quality)
    try:
        from app.services.stable_diffusion_inpainting import get_stable_diffusion_service
        sd_service = get_stable_diffusion_service()
        if sd_service.is_available():
            logger.info("Using Stable Diffusion for inpainting (best quality)")
            return await sd_service.inpaint(
                image_path, mask_path, output_path,
                prompt="clean diagram background, seamless inpainting, preserve diagram structure",
                num_inference_steps=25,
                guidance_scale=7.5
            )
    except Exception as e:
        logger.warning(f"Stable Diffusion failed: {e}, falling back to LaMa/OpenCV")
    
    # Fall back to LaMa/OpenCV
    return await _inpaint_with_lama_or_opencv(image_path, mask_path, output_path)


async def _inpaint_with_lama_or_opencv(
    image_path: str,
    mask_path: str,
    output_path: str
) -> str:
    """
    Inpaint image using LaMa/IOPaint if available, otherwise fall back to OpenCV.

    Args:
        image_path: Path to source image
        mask_path: Path to mask image (white=inpaint, black=keep)
        output_path: Path for output image

    Returns:
        Path to inpainted image
    """
    import cv2
    import numpy as np

    # Try IOPaint/LaMa first
    iopaint_url = os.getenv("IOPAINT_URL")
    if iopaint_url:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                with open(image_path, "rb") as img_f, open(mask_path, "rb") as mask_f:
                    response = await client.post(
                        f"{iopaint_url}/inpaint",
                        files={
                            "image": img_f,
                            "mask": mask_f
                        }
                    )
                    response.raise_for_status()

                    with open(output_path, "wb") as out_f:
                        out_f.write(response.content)

                    logger.info(f"IOPaint inpainting saved to {output_path}")
                    return output_path
        except Exception as e:
            logger.warning(f"IOPaint failed: {e}, falling back to OpenCV")

    # Fall back to OpenCV inpainting
    image = cv2.imread(image_path)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

    if image is None or mask is None:
        raise ValueError(f"Could not load image or mask: {image_path}, {mask_path}")

    # Calculate adaptive inpaint radius based on mask and image size
    # Research: radius should be proportional to mask size and image resolution
    # For line removal, we need larger radius to properly blend thin line regions
    h, w = image.shape[:2]
    image_diagonal = np.sqrt(w**2 + h**2)
    
    # Calculate average mask region size
    mask_area = np.sum(mask > 0)
    if mask_area > 0:
        # Estimate average mask region dimension
        # For thin lines, we need to account for their narrow width
        num_components, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if num_components > 1:
            # Calculate average width of mask regions (for lines, this will be small)
            widths = [stats[i, cv2.CC_STAT_WIDTH] for i in range(1, num_components)]
            heights = [stats[i, cv2.CC_STAT_HEIGHT] for i in range(1, num_components)]
            avg_width = np.mean(widths) if widths else 0
            avg_height = np.mean(heights) if heights else 0
            avg_dimension = max(avg_width, avg_height)
            
            # For thin lines (narrow regions), use larger radius to ensure proper blending
            # For wider regions (text), use proportional radius
            if avg_dimension < 50:  # Likely thin lines
                adaptive_radius = max(15, min(35, int(image_diagonal * 0.03)))
            else:  # Text or larger regions
                adaptive_radius = max(12, min(30, int(avg_dimension * 0.15)))
        else:
            # Fallback calculation
            avg_mask_size = np.sqrt(mask_area / max(1, mask_area / (w * h)))
            adaptive_radius = max(12, min(30, int(avg_mask_size * 0.15)))
    else:
        # Fallback: use image-relative radius
        adaptive_radius = max(15, min(30, int(image_diagonal * 0.025)))
    
    # Use Navier-Stokes inpainting (better edge preservation than TELEA)
    # Research shows NS is better for text removal as it preserves boundary continuity
    # Increased iterations for better quality (OpenCV uses internal iterations)
    inpainted = cv2.inpaint(image, mask, inpaintRadius=adaptive_radius, flags=cv2.INPAINT_NS)

    cv2.imwrite(output_path, inpainted)
    logger.info(f"OpenCV inpainting saved to {output_path} (adaptive radius: {adaptive_radius})")

    return output_path


async def qwen_label_remover_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Detect and remove text labels AND leader lines using Qwen2.5-VL + LaMa.

    This agent:
    1. Uses Qwen2.5-VL to detect ALL annotations (text, lines, arrows)
    2. Creates a comprehensive mask covering all detected elements
    3. Uses high-quality inpainting (LaMa/IOPaint preferred, OpenCV fallback)
    4. Returns clean diagram suitable for zone detection

    Inputs:
        diagram_image: Dict with image_url and/or local_path

    Outputs:
        cleaned_image_path: Path to the cleaned image
        removed_annotations: List of detected annotations
        qwen_mask_path: Path to the generated mask
    """
    logger.info("=== LABEL REMOVER STARTING (OCR + Line Detection) ===")

    # Skip if not INTERACTIVE_DIAGRAM
    template_type = state.get("template_selection", {}).get("template_type", "")
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"Skipping label removal: template_type={template_type}")
        return {
            "current_agent": "qwen_label_remover",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    # Get image info
    image_info = state.get("diagram_image") or {}
    image_url = image_info.get("image_url")
    local_path = image_info.get("local_path")

    if not image_url and not local_path:
        logger.warning("No diagram image available, skipping label removal")
        return {
            "cleaned_image_path": None,
            "removed_annotations": [],
            "current_agent": "qwen_label_remover",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    # Ensure image is downloaded locally
    question_id = state.get("question_id", "unknown")
    output_dir = Path(__file__).parent.parent.parent / "pipeline_outputs" / "assets" / question_id
    output_dir.mkdir(parents=True, exist_ok=True)

    if local_path and Path(local_path).exists():
        image_path = str(local_path)
    else:
        image_path = str(output_dir / "diagram.jpg")
        if not Path(image_path).exists():
            try:
                logger.info(f"Downloading image from {image_url}")
                await _download_image(image_url, Path(image_path))
            except Exception as e:
                logger.error(f"Failed to download image: {e}")
                return {
                    "cleaned_image_path": None,
                    "removed_annotations": [],
                    "label_removal_error": f"Image download failed: {e}",
                    "current_agent": "qwen_label_remover",
                    "last_updated_at": datetime.utcnow().isoformat()
                }

    start_time = time.time()

    try:
        # Phase 1: Use VLM (Qwen VL) for context-aware detection (PRIMARY METHOD)
        # VLM can distinguish leader lines from diagram structure lines
        qwen_service = get_qwen_vl_service()
        
        if await qwen_service.is_available():
            # Use per-word approach: detect all words first, then detect leader line for each
            logger.info("Using Qwen2.5-VL per-word approach: detect all text labels, then detect leader line for each")
            
            detection_result = await qwen_service.detect_labels_and_lines_per_word(image_path)
            annotations = detection_result.get("annotations", [])
            mask_path = detection_result.get("mask_path")
            
            # Track metrics
            if ctx:
                ctx.set_llm_metrics(
                    model=detection_result.get("model", "qwen2.5vl"),
                    latency_ms=detection_result.get("latency_ms")
                )
            
            if not annotations:
                logger.info("No annotations detected, returning original image")
                return {
                    "cleaned_image_path": image_path,
                    "removed_annotations": [],
                    "current_agent": "qwen_label_remover",
                    "last_updated_at": datetime.utcnow().isoformat()
                }
            
            # Separate text and lines from VLM annotations
            text_regions = []
            line_regions = []
            
            import cv2
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image: {image_path}")
            img_height, img_width = img.shape[:2]
            
            for ann in annotations:
                ann_type = ann.get("type", "")
                if ann_type == "text":
                    bbox = ann.get("bbox", [])
                    if len(bbox) == 4:
                        # Convert from normalized 0-1000 to pixel coordinates
                        x1 = int(bbox[0] * img_width / 1000)
                        y1 = int(bbox[1] * img_height / 1000)
                        x2 = int(bbox[2] * img_width / 1000)
                        y2 = int(bbox[3] * img_height / 1000)
                        text_regions.append({
                            "bbox": {
                                "x": x1,
                                "y": y1,
                                "width": x2 - x1,
                                "height": y2 - y1
                            },
                            "text": ann.get("content", ""),
                            "confidence": 0.9
                        })
                elif ann_type == "line":
                    # Line annotations are already in correct format
                    line_regions.append(ann)
            
            logger.info(
                f"Qwen VL detected {len(text_regions)} text labels and {len(line_regions)} leader lines "
                f"(total: {len(annotations)} annotations)"
            )
            
            # mask_path is already created by detect_labels_and_lines_per_word
            if not mask_path:
                raise ValueError("Qwen VL should have created mask_path but didn't")
            
            # Convert annotations to standard format for consistency
            # Annotations are already in correct format from per-word detection
            
        else:
            # Fallback: Use EasyOCR + Line Detection
            logger.warning("Qwen VL not available, falling back to EasyOCR + OpenCV")
            
            inpainting_service = get_inpainting_service()
            
            # Detect text regions with lower confidence to catch more text
            text_regions = await inpainting_service.detect_text_regions(
                image_path, min_confidence=0.3  # Lower threshold for better coverage
            )
            
            # Detect leader lines using text-anchored approach
            line_regions = await inpainting_service.detect_leader_lines_from_text(
                image_path, text_regions
            )
            
            # Create mask using EasyOCR + text-anchored line detection
            import cv2
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image: {image_path}")
            img_height, img_width = img.shape[:2]
            
            mask_path = await inpainting_service.create_text_mask(
                image_path, text_regions, dilation=25, include_lines=True
            )
            
            # Convert to annotation format
            annotations = []
            for r in text_regions:
                bbox_dict = r.get("bbox", {})
                x = bbox_dict.get("x", 0)
                y = bbox_dict.get("y", 0)
                w = bbox_dict.get("width", 0)
                h = bbox_dict.get("height", 0)
                
                # Normalize to 0-1000 scale
                x1_norm = int((x / img_width) * 1000)
                y1_norm = int((y / img_height) * 1000)
                x2_norm = int(((x + w) / img_width) * 1000)
                y2_norm = int(((y + h) / img_height) * 1000)
                
                annotations.append({
                    "type": "text",
                    "content": r.get("text", ""),
                    "bbox": [x1_norm, y1_norm, x2_norm, y2_norm]
                })
            
            for r in line_regions:
                bbox_dict = r.get("bbox", {})
                x = bbox_dict.get("x", 0)
                y = bbox_dict.get("y", 0)
                w = bbox_dict.get("width", 0)
                h = bbox_dict.get("height", 0)
                
                # Normalize to 0-1000 scale
                x1_norm = int((x / img_width) * 1000)
                y1_norm = int((y / img_height) * 1000)
                x2_norm = int(((x + w) / img_width) * 1000)
                y2_norm = int(((y + h) / img_height) * 1000)
                
                line_ann = {
                    "type": "line",
                    "bbox": [x1_norm, y1_norm, x2_norm, y2_norm]
                }
                if "points" in r:
                    # Convert points to normalized coordinates
                    pt1, pt2 = r["points"]
                    line_ann["start"] = [int(pt1[0] * 1000 / img_width), int(pt1[1] * 1000 / img_height)]
                    line_ann["end"] = [int(pt2[0] * 1000 / img_width), int(pt2[1] * 1000 / img_height)]
                annotations.append(line_ann)
            
            logger.info(
                f"EasyOCR detected {len(text_regions)} text regions and {len(line_regions)} leader lines "
                f"(total: {len(annotations)} annotations)"
            )
        
        # Check if we have any annotations to process
        if not annotations and not text_regions and not line_regions:
            logger.info("No text or lines detected, returning original image")
            return {
                "cleaned_image_path": image_path,
                "removed_annotations": [],
                "current_agent": "qwen_label_remover",
                "last_updated_at": datetime.utcnow().isoformat()
            }
        
        # mask_path should already be set by Qwen VL or EasyOCR path
        if not mask_path:
            raise ValueError("mask_path should have been created but wasn't")
        
        # Ensure annotations list is populated (for VLM path, it's already set)
        if not annotations:
            # Build annotations from text_regions and line_regions (fallback path)
            annotations = []
            for r in text_regions:
                bbox_dict = r.get("bbox", {})
                if isinstance(bbox_dict, dict):
                    x = bbox_dict.get("x", 0)
                    y = bbox_dict.get("y", 0)
                    w = bbox_dict.get("width", 0)
                    h = bbox_dict.get("height", 0)
                    
                    # Normalize to 0-1000 scale
                    x1_norm = int((x / img_width) * 1000)
                    y1_norm = int((y / img_height) * 1000)
                    x2_norm = int(((x + w) / img_width) * 1000)
                    y2_norm = int(((y + h) / img_height) * 1000)
                    
                    annotations.append({
                        "type": "text",
                        "content": r.get("text", ""),
                        "bbox": [x1_norm, y1_norm, x2_norm, y2_norm]
                    })
            
            for r in line_regions:
                if isinstance(r, dict):
                    bbox = r.get("bbox", [])
                    if isinstance(bbox, list) and len(bbox) == 4:
                        annotations.append({
                            "type": "line",
                            "bbox": bbox,
                            "start": r.get("start", []),
                            "end": r.get("end", [])
                        })

        # Annotations are already set correctly by VLM path
        # For fallback path, they're built in the if not annotations block above

        # Phase 2: Inpaint using Stable Diffusion (if available) or LaMa/OpenCV
        cleaned_dir = output_dir / "cleaned"
        cleaned_dir.mkdir(exist_ok=True)
        output_path = str(cleaned_dir / f"{Path(image_path).stem}_cleaned.png")

        cleaned_path = await _inpaint_with_stable_diffusion_or_fallback(
            image_path, mask_path, output_path
        )

        total_latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Label removal complete in {total_latency_ms}ms. "
            f"Removed {len(annotations)} annotations. "
            f"Cleaned image: {cleaned_path}"
        )

        result = {
            "cleaned_image_path": cleaned_path,
            "removed_annotations": annotations,
            "qwen_mask_path": mask_path,
            "current_agent": "qwen_label_remover",
            "last_updated_at": datetime.utcnow().isoformat()
        }

        return result

    except Exception as e:
        logger.error(f"Label removal failed: {e}", exc_info=True)
        # Return original image as fallback
        return {
            "cleaned_image_path": image_path,
            "removed_annotations": [],
            "label_removal_error": str(e),
            "_used_fallback": False,
            "_fallback_reason": f"Label removal failed: {e}",
            "current_agent": "qwen_label_remover",
            "last_updated_at": datetime.utcnow().isoformat()
        }


async def _fallback_to_easyocr(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext],
    image_path: str,
    output_dir: Path,
    error_reason: str
) -> dict:
    """Fallback to EasyOCR-based label removal if Qwen fails."""
    logger.warning(f"Falling back to EasyOCR: {error_reason}")

    try:
        import cv2
        inpainting_service = get_inpainting_service()
        
        # Get image dimensions for coordinate normalization
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        img_height, img_width = img.shape[:2]
        
        # Detect text regions
        text_regions = await inpainting_service.detect_text_regions(
            image_path, min_confidence=0.5
        )
        
        if not text_regions:
            logger.info("No text regions detected in fallback, returning original image")
            return {
                "cleaned_image_path": image_path,
                "removed_annotations": [],
                "qwen_mask_path": None,
                "_used_fallback": True,
                "_fallback_reason": f"EasyOCR fallback: {error_reason} (no text found)",
                "current_agent": "qwen_label_remover",
                "last_updated_at": datetime.utcnow().isoformat()
            }
        
        # Create mask
        cleaned_dir = output_dir / "cleaned"
        cleaned_dir.mkdir(exist_ok=True)
        mask_path = await inpainting_service.create_text_mask(
            image_path, text_regions, dilation=35, include_lines=True
        )
        
        # Inpaint
        output_path = str(cleaned_dir / f"{Path(image_path).stem}_cleaned.png")
        cleaned_path = await _inpaint_with_lama_or_opencv(
            image_path, mask_path, output_path
        )
        
        # Convert text regions to annotation format with proper bbox
        annotations = []
        for r in text_regions:
            bbox_dict = r.get("bbox", {})
            x = bbox_dict.get("x", 0)
            y = bbox_dict.get("y", 0)
            w = bbox_dict.get("width", 0)
            h = bbox_dict.get("height", 0)
            
            # Normalize to 0-1000 scale
            x1_norm = int((x / img_width) * 1000)
            y1_norm = int((y / img_height) * 1000)
            x2_norm = int(((x + w) / img_width) * 1000)
            y2_norm = int(((y + h) / img_height) * 1000)
            
            annotations.append({
                "type": "text",
                "content": r.get("text", ""),
                "bbox": [x1_norm, y1_norm, x2_norm, y2_norm]
            })

        if ctx:
            ctx.set_fallback_used(f"EasyOCR fallback: {error_reason}")

        return {
            "cleaned_image_path": cleaned_path,
            "removed_annotations": annotations,
            "qwen_mask_path": mask_path,
            "_used_fallback": True,
            "_fallback_reason": f"EasyOCR fallback: {error_reason}",
            "current_agent": "qwen_label_remover",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    except Exception as e2:
        logger.error(f"EasyOCR fallback also failed: {e2}")
        return {
            "cleaned_image_path": image_path,
            "removed_annotations": [],
            "qwen_mask_path": None,
            "label_removal_error": f"Both Qwen and EasyOCR failed: {error_reason}; {e2}",
            "_used_fallback": True,
            "_fallback_reason": f"All methods failed",
            "current_agent": "qwen_label_remover",
            "last_updated_at": datetime.utcnow().isoformat()
        }
