"""
MLX SAM3 Segmentation Service for Apple Silicon

Provides SAM3 segmentation using MLX (Apple Silicon optimized).
Supports text prompts for accurate label-based segmentation.

Based on research:
- Short noun phrases work best ("petal", "car", "person")
- Hybrid prompting (text + visual exemplars) improves accuracy
- Two-stage VLM approach validated for better results

API Reference (from mlx_sam3 repository):
- build_sam3_image_model() -> model
- Sam3Processor(model, confidence_threshold=0.5)
- processor.set_image(image) -> state
- processor.set_text_prompt(prompt, state) -> state (updates state)
- state["masks"], state["boxes"], state["scores"]
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import os
import sys


def mlx_sam3_segment_image(
    image_path: str,
    text_prompts: Optional[Dict[str, str]] = None,
    labels: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Segment image using MLX SAM3 with text prompts.
    
    Uses the correct MLX SAM3 API from third_party/mlx_sam3:
    - build_sam3_image_model() to create model
    - Sam3Processor with set_image() and set_text_prompt()
    
    Args:
        image_path: Path to image file
        text_prompts: Dict mapping label -> SAM3 prompt (from VLM)
        labels: List of labels to segment (if prompts not provided, uses labels as prompts)
    
    Returns:
        List of segments with bbox and center_px, each with label and prompt_used metadata
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError as e:
        raise RuntimeError(f"Image dependencies not available: {e}") from e
    
    # Try importing MLX SAM3 from third_party directory
    try:
        # Add third_party/mlx_sam3 to path if not already there
        mlx_sam3_path = Path(__file__).parent.parent.parent / "third_party" / "mlx_sam3"
        if mlx_sam3_path.exists() and str(mlx_sam3_path) not in sys.path:
            sys.path.insert(0, str(mlx_sam3_path))
        
        from sam3.model_builder import build_sam3_image_model  # type: ignore
        from sam3.model.sam3_image_processor import Sam3Processor  # type: ignore
        
        # Load model (will download from HuggingFace on first use)
        # Model: mlx-community/sam3-image (~3.5GB)
        import logging
        logger = logging.getLogger("gamed_ai.services.mlx_sam3_segmentation")
        logger.info("Loading MLX SAM3 model (this may take time on first run)")
        
        model = build_sam3_image_model()
        logger.info("✅ MLX SAM3 model loaded successfully")
        
        processor = Sam3Processor(model, confidence_threshold=0.5)
        logger.info("✅ SAM3Processor created")
        
        # Load and set image
        logger.info(f"Loading image: {image_path}")
        image = Image.open(image_path).convert("RGB")
        logger.info(f"Image loaded: {image.size}")
        
        logger.info("Setting image in processor (this may take 10-30 seconds)...")
        inference_state = processor.set_image(image)
        logger.info("✅ Image set in processor, starting segmentation")
        
        all_segments = []
        segment_id_counter = 1
        
        # If text_prompts provided, use them; otherwise use labels as prompts
        prompts_to_use = text_prompts or {}
        if not prompts_to_use and labels:
            # Use short noun phrases (research shows these work best)
            prompts_to_use = {label: label for label in labels}
        
        # Log input information
        import json
        logger.info(f"MLX SAM3 input - image shape: {image.shape if hasattr(image, 'shape') else 'unknown'}")
        logger.info(f"MLX SAM3 prompts being sent: {json.dumps(prompts_to_use, indent=2)}")
        logger.info(f"Total prompts: {len(prompts_to_use)}")
        
        # Segment for each prompt
        for idx, (label, prompt_text) in enumerate(prompts_to_use.items(), 1):
            try:
                logger.info(f"Segmenting label {idx}/{len(prompts_to_use)}: '{label}' with prompt '{prompt_text}'")
                
                # Reset prompts for each label (to avoid interference)
                processor.reset_all_prompts(inference_state)
                
                # Set text prompt and get results
                # API: set_text_prompt(prompt: str, state: Dict) -> Dict
                logger.info(f"Calling set_text_prompt for '{label}'...")
                inference_state = processor.set_text_prompt(prompt_text, inference_state)
                logger.info(f"✅ set_text_prompt completed for '{label}'")
                
                # Extract masks, boxes, and scores from state
                masks = inference_state.get("masks", [])
                boxes = inference_state.get("boxes", [])
                scores = inference_state.get("scores", [])
                
                # Log raw output for debugging
                logger.info(f"MLX SAM3 raw output for '{label}' - boxes: {len(boxes) if boxes else 0}, masks: {len(masks) if masks else 0}, scores: {scores if scores else []}")
                
                # Convert MLX arrays to numpy if needed
                if hasattr(masks, '__iter__') and not isinstance(masks, (list, tuple)):
                    # MLX array - convert to numpy
                    import mlx.core as mx
                    if isinstance(masks, mx.array):
                        masks = np.array(masks)
                    if isinstance(boxes, mx.array):
                        boxes = np.array(boxes)
                    if isinstance(scores, mx.array):
                        scores = np.array(scores)
                
                # Handle different output formats
                # Masks might be a single array or list of arrays
                if not isinstance(masks, (list, tuple)):
                    # Single mask array - convert to list
                    if masks.ndim == 3:  # [N, H, W]
                        masks = [masks[i] for i in range(masks.shape[0])]
                    elif masks.ndim == 2:  # [H, W]
                        masks = [masks]
                    else:
                        masks = []
                
                # Boxes format: [N, 4] where each box is [x0, y0, x1, y1] in pixel coordinates
                if not isinstance(boxes, (list, tuple)):
                    boxes = np.array(boxes)
                    if boxes.ndim == 2 and boxes.shape[1] == 4:
                        boxes = [boxes[i] for i in range(boxes.shape[0])]
                    elif boxes.ndim == 1 and len(boxes) == 4:
                        boxes = [boxes]
                    else:
                        boxes = []
                
                # Scores format: [N] array
                if not isinstance(scores, (list, tuple)):
                    scores = np.array(scores)
                    if scores.ndim == 1:
                        scores = scores.tolist()
                    else:
                        scores = []
                
                # Process each detected instance
                num_instances = max(len(masks), len(boxes), len(scores))
                
                for i in range(num_instances):
                    mask = masks[i] if i < len(masks) else None
                    box = boxes[i] if i < len(boxes) else None
                    score = scores[i] if i < len(scores) else 1.0
                    
                    # Extract bounding box
                    if box is not None:
                        box = np.array(box)
                        if len(box) >= 4:
                            # Box format: [x0, y0, x1, y1] in pixel coordinates
                            x0, y0, x1, y1 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                            w = max(1, x1 - x0)
                            h = max(1, y1 - y0)
                            cx = x0 + w / 2
                            cy = y0 + h / 2
                        else:
                            continue
                    elif mask is not None:
                        # Extract bbox from mask
                        mask_arr = np.array(mask) if not isinstance(mask, np.ndarray) else mask
                        # Handle boolean mask
                        if mask_arr.dtype == bool:
                            ys, xs = np.where(mask_arr)
                        else:
                            # Probability mask - threshold at 0.5
                            ys, xs = np.where(mask_arr > 0.5)
                        
                        if len(xs) == 0 or len(ys) == 0:
                            continue
                        x_min, x_max = int(xs.min()), int(xs.max())
                        y_min, y_max = int(ys.min()), int(ys.max())
                        w = max(1, x_max - x_min)
                        h = max(1, y_max - y_min)
                        x0, y0 = x_min, y_min
                        cx = x0 + w / 2
                        cy = y0 + h / 2
                    else:
                        continue
                    
                    all_segments.append({
                        "segment_id": f"segment_{segment_id_counter}",
                        "label": label,
                        "prompt_used": prompt_text,
                        "bbox": {"x": int(x0), "y": int(y0), "width": int(w), "height": int(h)},
                        "center_px": {"x": float(cx), "y": float(cy)},
                        "confidence": float(score) if score is not None else 1.0,
                    })
                    segment_id_counter += 1
                    
            except Exception as e:
                # If one prompt fails, continue with others
                import logging
                logger = logging.getLogger("gamed_ai.services.mlx_sam3_segmentation")
                logger.warning(f"Failed to segment for label '{label}' with prompt '{prompt_text}': {e}")
                continue
        
        if all_segments:
            logger.info(f"MLX SAM3 generated {len(all_segments)} segments from {len(prompts_to_use)} prompts")
            return all_segments
        else:
            logger.warning("MLX SAM3 returned empty results")
            logger.warning(f"Image dimensions: {image.shape if hasattr(image, 'shape') else 'unknown'}")
            logger.warning(f"Prompt format may be incompatible with MLX SAM3")
            logger.warning(f"MLX SAM3 may require point/box prompts instead of text prompts")
            raise RuntimeError("No segments generated from MLX SAM3")
            
    except ImportError as e:
        raise RuntimeError(
            f"MLX SAM3 not installed: {e}. "
            f"Install with: cd backend && git clone https://github.com/Deekshith-Dade/mlx_sam3.git third_party/mlx_sam3 && "
            f"cd third_party/mlx_sam3 && pip install -e ."
        ) from e
    except Exception as e:
        import logging
        logger = logging.getLogger("gamed_ai.services.mlx_sam3_segmentation")
        logger.error(f"MLX SAM3 segmentation failed: {e}", exc_info=True)
        raise RuntimeError(f"MLX SAM3 segmentation failed: {e}") from e
