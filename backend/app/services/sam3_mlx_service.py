"""
SAM3 MLX Service for leader line detection and zone segmentation.

Uses Meta's SAM3 (Segment Anything Model 3) with MLX optimization for Apple Silicon.
SAM3 supports TEXT PROMPTS which allows us to:

1. Segment "annotation", "leader line", "pointer" for label removal
2. Segment specific organelles by name for zone detection
3. Use VLM/CLIP to verify and label the segments

Key advantage over Hough: SAM3 understands semantics, not just geometry.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Add mlx_sam3 to path
MLX_SAM3_PATH = Path(__file__).parent.parent.parent / "third_party" / "mlx_sam3"
if str(MLX_SAM3_PATH) not in sys.path:
    sys.path.insert(0, str(MLX_SAM3_PATH))

logger = logging.getLogger("gamed_ai.services.sam3_mlx")


class SAM3MLXService:
    """
    SAM3 service using MLX for Apple Silicon optimization.

    Supports:
    - Text-based segmentation ("segment the leader lines")
    - Box-based segmentation (from EasyOCR text boxes)
    - Automatic segmentation for zone detection
    """

    def __init__(self):
        """Initialize the SAM3 service."""
        self._model = None
        self._processor = None
        self._loaded = False
        logger.info("SAM3MLXService initialized")

    def _ensure_loaded(self):
        """Lazy load SAM3 model."""
        if self._loaded:
            return

        try:
            import mlx.core as mx
            from sam3.model_builder import build_sam3_image_model
            from sam3.model.sam3_image_processor import Sam3Processor

            logger.info("Loading SAM3 model (will auto-download ~3.5GB on first run)...")
            self._model = build_sam3_image_model()
            self._processor = Sam3Processor(self._model, confidence_threshold=0.3)
            self._loaded = True
            logger.info("SAM3 model loaded successfully")

        except ImportError as e:
            logger.error(f"Failed to import MLX SAM3: {e}")
            raise ImportError(
                "SAM3 requires MLX. Install with: pip install mlx mlx-vlm"
            ) from e

    async def is_available(self) -> bool:
        """Check if SAM3 is available."""
        try:
            import mlx.core  # noqa: F401
            return True
        except ImportError:
            return False

    def segment_by_text(
        self,
        image,
        prompt: str,
        confidence_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Segment image regions using a text prompt.

        Args:
            image: PIL Image
            prompt: Text describing what to segment (e.g., "leader line", "annotation")
            confidence_threshold: Minimum confidence for detection

        Returns:
            Dict with masks, boxes, scores, and semantic_seg
        """
        self._ensure_loaded()

        # Set up image
        inference_state = self._processor.set_image(image)

        # Reset and set text prompt
        self._processor.reset_all_prompts(inference_state)
        inference_state = self._processor.set_text_prompt(
            state=inference_state,
            prompt=prompt
        )

        return {
            "masks": inference_state.get("masks", []),
            "boxes": inference_state.get("boxes", []),
            "scores": inference_state.get("scores", []),
            "semantic_seg": inference_state.get("semantic_seg")
        }

    def detect_leader_lines(
        self,
        image,
        prompts: List[str] = None
    ) -> np.ndarray:
        """
        Detect leader lines using SAM3 text prompts.

        Tries multiple prompts to catch different annotation styles.

        Args:
            image: PIL Image
            prompts: List of text prompts to try

        Returns:
            Combined binary mask of all detected leader lines
        """
        self._ensure_loaded()
        import mlx.core as mx

        if prompts is None:
            prompts = [
                "leader line",
                "annotation line",
                "pointer line",
                "label marker",
                "text annotation"
            ]

        h, w = image.size[1], image.size[0]
        combined_mask = np.zeros((h, w), dtype=np.uint8)

        for prompt in prompts:
            try:
                result = self.segment_by_text(image, prompt)

                if result["semantic_seg"] is not None:
                    seg_np = np.array(result["semantic_seg"])
                    if seg_np.ndim == 4:
                        seg_np = seg_np[0, 0]
                    elif seg_np.ndim == 3:
                        seg_np = seg_np[0]

                    # Sigmoid + threshold
                    seg_probs = 1 / (1 + np.exp(-seg_np))
                    seg_binary = (seg_probs > 0.5).astype(np.uint8) * 255

                    # Resize if needed
                    if seg_binary.shape != (h, w):
                        from PIL import Image as PILImage
                        mask_pil = PILImage.fromarray(seg_binary)
                        mask_pil = mask_pil.resize((w, h), PILImage.BILINEAR)
                        seg_binary = np.array(mask_pil)

                    combined_mask = np.maximum(combined_mask, seg_binary)
                    logger.info(f"Prompt '{prompt}' detected {np.sum(seg_binary > 0)} pixels")

            except Exception as e:
                logger.warning(f"Prompt '{prompt}' failed: {e}")

        return combined_mask

    def detect_zones_by_labels(
        self,
        image,
        canonical_labels: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Detect zones in a diagram by segmenting each canonical label.

        This uses SAM3's text prompt capability to segment each organelle/structure
        by its name, providing much more accurate zone detection than grid fallback.

        Args:
            image: PIL Image
            canonical_labels: List of labels to segment (e.g., ["nucleus", "mitochondria"])

        Returns:
            List of zones with id, label, bbox, mask, confidence
        """
        self._ensure_loaded()

        zones = []
        w, h = image.size

        for i, label in enumerate(canonical_labels):
            try:
                result = self.segment_by_text(image, label)

                # Check if we got a detection
                if result["boxes"] and len(result["boxes"]) > 0:
                    boxes = result["boxes"]
                    scores = result["scores"]
                    masks = result.get("masks", [])

                    # Take the highest confidence detection
                    if scores:
                        best_idx = np.argmax(scores)
                        box = boxes[best_idx]
                        score = float(scores[best_idx])

                        # Convert box format if needed (typically x1,y1,x2,y2)
                        if len(box) == 4:
                            x1, y1, x2, y2 = box
                            bbox = {
                                "x": int(x1),
                                "y": int(y1),
                                "width": int(x2 - x1),
                                "height": int(y2 - y1)
                            }

                            zone = {
                                "id": f"zone_{i+1}",
                                "label": label,
                                "label_confidence": score,
                                "confidence": score,
                                "bbox": bbox,
                                "source": "sam3_text"
                            }

                            if masks and len(masks) > best_idx:
                                zone["mask"] = masks[best_idx]

                            zones.append(zone)
                            logger.info(f"SAM3 detected '{label}' with confidence {score:.2f}")

                elif result["semantic_seg"] is not None:
                    # Fall back to semantic segmentation mask
                    seg_np = np.array(result["semantic_seg"])
                    if seg_np.ndim == 4:
                        seg_np = seg_np[0, 0]
                    elif seg_np.ndim == 3:
                        seg_np = seg_np[0]

                    seg_probs = 1 / (1 + np.exp(-seg_np))
                    seg_binary = seg_probs > 0.5

                    if np.any(seg_binary):
                        # Find bounding box of mask
                        coords = np.where(seg_binary)
                        y_min, y_max = coords[0].min(), coords[0].max()
                        x_min, x_max = coords[1].min(), coords[1].max()

                        # Scale to original image size
                        scale_x = w / seg_binary.shape[1]
                        scale_y = h / seg_binary.shape[0]

                        zone = {
                            "id": f"zone_{i+1}",
                            "label": label,
                            "label_confidence": 0.7,
                            "confidence": 0.7,
                            "bbox": {
                                "x": int(x_min * scale_x),
                                "y": int(y_min * scale_y),
                                "width": int((x_max - x_min) * scale_x),
                                "height": int((y_max - y_min) * scale_y)
                            },
                            "source": "sam3_semantic"
                        }
                        zones.append(zone)
                        logger.info(f"SAM3 semantic detected '{label}'")

            except Exception as e:
                logger.warning(f"Failed to segment '{label}': {e}")

        logger.info(f"SAM3 detected {len(zones)}/{len(canonical_labels)} zones")
        return zones

    def segment_all_objects(
        self,
        image,
        prompt: str = "objects"
    ) -> List[Dict[str, Any]]:
        """
        Segment all distinct objects in an image.

        Useful for automatic zone detection without knowing labels.
        """
        self._ensure_loaded()

        result = self.segment_by_text(image, prompt)

        objects = []
        if result["boxes"] and result["scores"]:
            for i, (box, score) in enumerate(zip(result["boxes"], result["scores"])):
                if len(box) == 4:
                    x1, y1, x2, y2 = box
                    objects.append({
                        "id": f"object_{i+1}",
                        "bbox": {
                            "x": int(x1),
                            "y": int(y1),
                            "width": int(x2 - x1),
                            "height": int(y2 - y1)
                        },
                        "confidence": float(score)
                    })

        return objects


# Singleton instance
_sam3_service: Optional[SAM3MLXService] = None


def get_sam3_mlx_service() -> SAM3MLXService:
    """Get or create the SAM3 MLX service singleton."""
    global _sam3_service
    if _sam3_service is None:
        _sam3_service = SAM3MLXService()
    return _sam3_service
