"""
Segmentation helpers for diagram images.

Uses MLX SAM3 (preferred for Apple Silicon) with text prompts for accurate
label-based segmentation. No fallback - fails if SAM3 is unavailable.

NOTE: SAM2, SAM v1, and grid fallbacks have been REMOVED. This module uses SAM3 exclusively.
"""

from __future__ import annotations

import logging
import math
import os
import platform
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("gamed_ai.services.segmentation")


def _grid_centers(count: int) -> List[Tuple[float, float]]:
    if count <= 0:
        return []
    rows = math.ceil(math.sqrt(count))
    cols = math.ceil(count / rows)
    x_step = 100 / (cols + 1)
    y_step = 100 / (rows + 1)
    centers = []
    for idx in range(count):
        row = idx // cols
        col = idx % cols
        centers.append((round((col + 1) * x_step, 2), round((row + 1) * y_step, 2)))
    return centers


def fallback_segments(label_count: int) -> List[Dict[str, Any]]:
    """Generate uniform grid segments as a fallback when SAM3 is unavailable."""
    centers = _grid_centers(label_count)
    segments = []
    for idx, (x, y) in enumerate(centers, start=1):
        segments.append({
            "segment_id": f"segment_{idx}",
            "x": x,
            "y": y,
            "radius": 10,
        })
    return segments


def sam_segment_image(
    image_path: str,
    text_prompts: Optional[Dict[str, str]] = None,
    labels: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Use MLX SAM3 for segmentation. SAM3 ONLY - no SAM2/SAM v1 fallback.

    Args:
        image_path: Path to image file
        text_prompts: Dict mapping label -> SAM3 prompt (from VLM prompt generator)
        labels: List of labels (used if text_prompts not provided)

    Priority:
    1. MLX SAM3 with text prompts (preferred)
    2. Raise error if SAM3 fails (no silent fallback to SAM2/SAM v1)

    Returns:
        List of segment dicts with bounding boxes and centers

    Raises:
        RuntimeError: If SAM3 segmentation fails or is unavailable
    """
    try:
        from PIL import Image
        import numpy as np
    except Exception as e:
        raise RuntimeError(f"Image dependencies not available: {e}") from e

    # Validate inputs
    if not text_prompts and not labels:
        raise RuntimeError("SAM3 requires text_prompts or labels. No generic segmentation available.")

    logger.info(f"SAM3 segmentation starting for {image_path}")
    logger.info(f"Text prompts: {list(text_prompts.keys()) if text_prompts else 'None'}")
    logger.info(f"Labels: {labels[:5] if labels else 'None'}...")

    # Check if MLX SAM3 should be used
    use_mlx = os.getenv("USE_SAM3_MLX", "auto").lower()
    is_apple_silicon = platform.processor() == "arm" or platform.machine() == "arm64"

    # ONLY use MLX SAM3 - no fallbacks to older SAM versions
    if use_mlx == "true" or (use_mlx == "auto" and is_apple_silicon):
        try:
            from app.services.mlx_sam3_segmentation import mlx_sam3_segment_image

            logger.info("Using MLX SAM3 for segmentation (Apple Silicon optimized)")
            segments = mlx_sam3_segment_image(image_path, text_prompts=text_prompts, labels=labels)

            if segments:
                logger.info(f"MLX SAM3 generated {len(segments)} segments successfully")
                return segments
            else:
                raise RuntimeError("MLX SAM3 returned no segments")

        except ImportError as e:
            logger.error(f"MLX SAM3 not installed: {e}")
            raise RuntimeError(
                f"MLX SAM3 segmentation failed: {e}. "
                f"Install with: pip install mlx-sam3 or check third_party/mlx_sam3 setup. "
                f"No fallback to SAM2/SAM v1."
            ) from e

        except Exception as e:
            logger.error(f"MLX SAM3 failed: {e}")
            raise RuntimeError(
                f"SAM3 segmentation failed: {e}. No fallback to SAM2/SAM v1."
            ) from e

    # If MLX is explicitly disabled, try official SAM3
    if use_mlx == "false":
        try:
            logger.info("Attempting official SAM3 segmentation")
            from sam3.model_builder import build_sam3_image_model  # type: ignore
            from sam3.model.sam3_image_processor import Sam3Processor  # type: ignore

            image = Image.open(image_path).convert("RGB")

            # Build model
            model = build_sam3_image_model()
            processor = Sam3Processor(model)

            # Set image
            inference_state = processor.set_image(image)

            # Segment with text prompts
            if text_prompts:
                all_segments = []
                segment_id_counter = 1

                for label, prompt_text in text_prompts.items():
                    try:
                        output = processor.set_text_prompt(state=inference_state, prompt=prompt_text)
                        masks = output.get("masks", [])
                        boxes = output.get("boxes", [])
                        scores = output.get("scores", [])

                        import numpy as np

                        for mask, box, score in zip(masks, boxes, scores):
                            if box is not None and len(box) >= 4:
                                x_min, y_min, x_max, y_max = box[0], box[1], box[2], box[3]
                                w = max(1, x_max - x_min)
                                h = max(1, y_max - y_min)
                                cx = x_min + w / 2
                                cy = y_min + h / 2
                            elif mask is not None:
                                mask_arr = np.array(mask) if not isinstance(mask, np.ndarray) else mask
                                ys, xs = np.where(mask_arr)
                                if len(xs) == 0 or len(ys) == 0:
                                    continue
                                x_min, x_max = int(xs.min()), int(xs.max())
                                y_min, y_max = int(ys.min()), int(ys.max())
                                w = max(1, x_max - x_min)
                                h = max(1, y_max - y_min)
                                cx = x_min + w / 2
                                cy = y_min + h / 2
                            else:
                                continue

                            all_segments.append({
                                "segment_id": f"segment_{segment_id_counter}",
                                "label": label,
                                "prompt_used": prompt_text,
                                "bbox": {"x": int(x_min), "y": int(y_min), "width": int(w), "height": int(h)},
                                "center_px": {"x": float(cx), "y": float(cy)},
                            })
                            segment_id_counter += 1
                    except Exception as e:
                        logger.warning(f"Failed to segment for label '{label}' with prompt '{prompt_text}': {e}")
                        continue

                if all_segments:
                    logger.info(f"Official SAM3 generated {len(all_segments)} segments")
                    return all_segments

            raise RuntimeError("Official SAM3 returned no segments")

        except ImportError as e:
            raise RuntimeError(
                f"SAM3 package not installed: {e}. "
                f"Install with: pip install sam3. No fallback to SAM2/SAM v1."
            ) from e

        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "huggingface" in error_msg.lower():
                raise RuntimeError(
                    f"SAM3 authentication required: {e}. "
                    f"Run: huggingface-cli login (or set HF_TOKEN env var)"
                ) from e
            raise RuntimeError(
                f"SAM3 segmentation failed: {e}. No fallback to SAM2/SAM v1."
            ) from e

    raise RuntimeError(
        f"SAM3 segmentation not available. USE_SAM3_MLX={use_mlx}, "
        f"is_apple_silicon={is_apple_silicon}. "
        f"Set USE_SAM3_MLX=true or USE_SAM3_MLX=auto on Apple Silicon."
    )
