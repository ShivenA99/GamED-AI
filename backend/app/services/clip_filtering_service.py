"""
CLIP Filtering Service for distinguishing annotation elements from diagram content.

Uses CLIP (Contrastive Language-Image Pre-training) to semantically classify
regions of an image as either annotations (labels, leader lines, arrows) or
diagram content (anatomical structures, scientific diagrams, etc.).

This helps filter out false positives from Hough line detection by checking
if a detected line region looks like an annotation vs. diagram structure.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("gamed_ai.services.clip_filtering")


class CLIPAnnotationFilter:
    """
    Use CLIP to distinguish annotation elements from diagram content.

    This service loads a CLIP model and uses it to classify cropped regions
    of an image as either annotation (text, leader lines, arrows) or
    diagram content (anatomical structures, organs, etc.).
    """

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """
        Initialize the CLIP annotation filter.

        Args:
            model_name: HuggingFace model name for CLIP
        """
        self.model_name = os.getenv("CLIP_MODEL", model_name)
        self._model = None
        self._processor = None
        self._device = None
        logger.info(f"CLIPAnnotationFilter initialized with model: {self.model_name}")

    def _ensure_loaded(self):
        """Lazy load the CLIP model."""
        if self._model is not None:
            return

        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel

            logger.info(f"Loading CLIP model: {self.model_name}")

            self._model = CLIPModel.from_pretrained(self.model_name)
            self._processor = CLIPProcessor.from_pretrained(self.model_name)

            # Use MPS on Mac, CUDA if available, otherwise CPU
            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"

            self._model = self._model.to(self._device)
            logger.info(f"CLIP model loaded on device: {self._device}")

        except ImportError as e:
            logger.error(f"Failed to import transformers/torch: {e}")
            raise ImportError(
                "CLIP requires transformers and torch. Install with: "
                "pip install transformers torch"
            )

    def is_available(self) -> bool:
        """Check if CLIP is available and enabled."""
        if os.getenv("USE_CLIP_FILTER", "false").lower() != "true":
            return False

        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    def classify_region(
        self,
        image,
        crop_bbox: Tuple[int, int, int, int],
        annotation_labels: List[str] = None,
        content_labels: List[str] = None
    ) -> Dict[str, float]:
        """
        Classify a cropped region as annotation vs content.

        Args:
            image: PIL Image
            crop_bbox: (x1, y1, x2, y2) bounding box to crop
            annotation_labels: Labels describing annotations
            content_labels: Labels describing diagram content

        Returns:
            Dict with 'annotation_score', 'content_score', 'is_annotation' (bool)
        """
        from PIL import Image

        self._ensure_loaded()

        # Default labels
        if annotation_labels is None:
            annotation_labels = [
                "annotation label text pointer line arrow",
                "text label with line pointing to diagram",
                "educational annotation marker"
            ]

        if content_labels is None:
            content_labels = [
                "anatomical diagram organ tissue structure",
                "scientific diagram showing structure",
                "biological or scientific illustration"
            ]

        # Crop the region
        x1, y1, x2, y2 = crop_bbox
        # Ensure valid bounds
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(image.width, x2)
        y2 = min(image.height, y2)

        if x2 <= x1 or y2 <= y1:
            return {"annotation_score": 0.0, "content_score": 1.0, "is_annotation": False}

        crop = image.crop((x1, y1, x2, y2))

        # Ensure minimum size for CLIP
        if crop.width < 10 or crop.height < 10:
            # Too small to classify meaningfully
            return {"annotation_score": 0.5, "content_score": 0.5, "is_annotation": False}

        # Prepare inputs for CLIP
        all_labels = annotation_labels + content_labels
        inputs = self._processor(
            text=all_labels,
            images=crop,
            return_tensors="pt",
            padding=True
        )

        # Move to device
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        # Get similarities
        import torch
        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits_per_image
            probs = logits.softmax(dim=1)[0].cpu().numpy()

        # Calculate aggregate scores
        num_annotation = len(annotation_labels)
        annotation_score = float(probs[:num_annotation].sum())
        content_score = float(probs[num_annotation:].sum())

        # Normalize
        total = annotation_score + content_score
        if total > 0:
            annotation_score /= total
            content_score /= total

        return {
            "annotation_score": annotation_score,
            "content_score": content_score,
            "is_annotation": annotation_score > 0.5
        }

    def is_annotation(
        self,
        image,
        crop_bbox: Tuple[int, int, int, int],
        threshold: float = 0.6
    ) -> float:
        """
        Score if a cropped region is an annotation element.

        Args:
            image: PIL Image
            crop_bbox: (x1, y1, x2, y2) bounding box
            threshold: Threshold above which to consider as annotation

        Returns:
            Probability that the region is an annotation (0-1)
        """
        result = self.classify_region(image, crop_bbox)
        return result["annotation_score"]

    def filter_hough_lines(
        self,
        image_path: str,
        lines: List[Any],
        threshold: float = 0.6,
        padding: int = 15
    ) -> List[Any]:
        """
        Keep lines that CLIP scores as annotation elements.

        Args:
            image_path: Path to the image
            lines: List of Hough lines (each line is [[x1, y1, x2, y2]])
            threshold: Minimum annotation score to keep line
            padding: Padding around line for crop

        Returns:
            Filtered list of lines
        """
        from PIL import Image

        if not lines:
            return []

        self._ensure_loaded()
        image = Image.open(image_path)
        filtered = []

        logger.info(f"CLIP filtering {len(lines)} lines with threshold {threshold}")

        for i, line in enumerate(lines):
            x1, y1, x2, y2 = line[0]

            # Create bounding box around line with padding
            bbox = (
                min(x1, x2) - padding,
                min(y1, y2) - padding,
                max(x1, x2) + padding,
                max(y1, y2) + padding
            )

            score = self.is_annotation(image, bbox, threshold)

            if score > threshold:
                filtered.append(line)
                logger.debug(f"Line {i}: annotation_score={score:.2f} (KEPT)")
            else:
                logger.debug(f"Line {i}: annotation_score={score:.2f} (FILTERED)")

        logger.info(f"CLIP filter: {len(lines)} -> {len(filtered)} lines")
        return filtered

    def filter_text_regions(
        self,
        image_path: str,
        text_regions: List[Dict[str, Any]],
        threshold: float = 0.5,
        padding: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Filter text regions to keep only those that look like annotations.

        This can help remove false positives from OCR (e.g., text that's
        part of the diagram content rather than a label).

        Args:
            image_path: Path to the image
            text_regions: List of text regions with 'bbox' key
            threshold: Minimum annotation score to keep
            padding: Padding around text for crop

        Returns:
            Filtered list of text regions
        """
        from PIL import Image

        if not text_regions:
            return []

        self._ensure_loaded()
        image = Image.open(image_path)
        filtered = []

        for region in text_regions:
            bbox_dict = region.get("bbox", {})
            x = bbox_dict.get("x", 0)
            y = bbox_dict.get("y", 0)
            w = bbox_dict.get("width", 0)
            h = bbox_dict.get("height", 0)

            bbox = (
                x - padding,
                y - padding,
                x + w + padding,
                y + h + padding
            )

            score = self.is_annotation(image, bbox, threshold)

            if score > threshold:
                filtered.append(region)

        logger.info(f"CLIP text filter: {len(text_regions)} -> {len(filtered)} regions")
        return filtered


# Singleton instance
_clip_filter: Optional[CLIPAnnotationFilter] = None


def get_clip_filter() -> CLIPAnnotationFilter:
    """Get or create the CLIP filter singleton."""
    global _clip_filter
    if _clip_filter is None:
        _clip_filter = CLIPAnnotationFilter()
    return _clip_filter


def is_clip_filter_enabled() -> bool:
    """Check if CLIP filtering is enabled via environment variable."""
    return os.getenv("USE_CLIP_FILTER", "false").lower() == "true"
