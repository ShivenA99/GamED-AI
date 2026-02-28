"""
SAM3 (Segment Anything Model) Zone Detection Service.

Uses Meta's Segment Anything Model to automatically detect and segment
distinct regions in educational diagrams without requiring point/box prompts.

The automatic mask generator detects all distinct regions, which are then
filtered and matched to canonical labels using CLIP or VLM.

Requires:
    pip install segment-anything
    # Download model:
    wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("gamed_ai.services.sam3_zone")


class SAM3ZoneDetector:
    """
    Auto-detect zones in diagrams using Segment Anything Model.

    This detector uses SAM's automatic mask generator to find all
    distinct regions in an image without requiring manual prompts.
    """

    def __init__(
        self,
        model_path: str = None,
        model_type: str = "vit_h",
        points_per_side: int = 32,
        pred_iou_thresh: float = 0.86,
        stability_score_thresh: float = 0.92,
        min_mask_region_area: int = 500
    ):
        """
        Initialize the SAM zone detector.

        Args:
            model_path: Path to SAM checkpoint file
            model_type: SAM model type ("vit_h", "vit_l", or "vit_b")
            points_per_side: Points per side for automatic mask generation
            pred_iou_thresh: Predicted IoU threshold
            stability_score_thresh: Stability score threshold
            min_mask_region_area: Minimum mask area in pixels
        """
        self.model_path = model_path or os.getenv("SAM3_MODEL_PATH")
        self.model_type = model_type
        self.points_per_side = points_per_side
        self.pred_iou_thresh = pred_iou_thresh
        self.stability_score_thresh = stability_score_thresh
        self.min_mask_region_area = min_mask_region_area

        self._model = None
        self._mask_generator = None
        self._device = None

        logger.info(f"SAM3ZoneDetector initialized: model_type={model_type}")

    def _ensure_loaded(self):
        """Lazy load the SAM model."""
        if self._model is not None:
            return

        if not self.model_path:
            raise ValueError(
                "SAM model path not set. Set SAM3_MODEL_PATH environment variable "
                "or download from: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
            )

        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"SAM model not found at: {self.model_path}")

        try:
            import torch
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

            logger.info(f"Loading SAM model from: {self.model_path}")

            # Choose device
            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"

            # Load model
            sam = sam_model_registry[self.model_type](checkpoint=self.model_path)
            sam = sam.to(self._device)
            self._model = sam

            # Create automatic mask generator
            self._mask_generator = SamAutomaticMaskGenerator(
                sam,
                points_per_side=self.points_per_side,
                pred_iou_thresh=self.pred_iou_thresh,
                stability_score_thresh=self.stability_score_thresh,
                min_mask_region_area=self.min_mask_region_area
            )

            logger.info(f"SAM model loaded on device: {self._device}")

        except ImportError as e:
            logger.error(f"Failed to import segment_anything/torch: {e}")
            raise ImportError(
                "SAM requires segment-anything and torch. Install with: "
                "pip install segment-anything torch"
            )

    async def is_available(self) -> bool:
        """Check if SAM is available."""
        if not self.model_path:
            return False

        try:
            import segment_anything  # noqa: F401
            import torch  # noqa: F401
            return Path(self.model_path).exists()
        except ImportError:
            return False

    def detect_zones(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Auto-detect all distinct zones/regions in an image.

        Args:
            image: RGB image as numpy array (H, W, 3)

        Returns:
            List of zones, each with:
                - id: Zone identifier
                - bbox: {x, y, width, height} bounding box
                - area: Area in pixels
                - confidence: Predicted IoU score
                - mask: Binary segmentation mask
        """
        self._ensure_loaded()

        logger.info(f"Running SAM automatic mask generation on image {image.shape}")

        # Generate masks
        masks = self._mask_generator.generate(image)

        logger.info(f"SAM generated {len(masks)} masks")

        # Convert to zone format
        zones = []
        for i, mask_data in enumerate(masks):
            # bbox is [x, y, w, h] in COCO format
            bbox = mask_data["bbox"]

            zones.append({
                "id": f"zone_{i+1}",
                "bbox": {
                    "x": int(bbox[0]),
                    "y": int(bbox[1]),
                    "width": int(bbox[2]),
                    "height": int(bbox[3])
                },
                "area": int(mask_data["area"]),
                "confidence": float(mask_data["predicted_iou"]),
                "stability_score": float(mask_data["stability_score"]),
                "mask": mask_data["segmentation"]  # Boolean array
            })

        # Sort by area (largest first)
        zones.sort(key=lambda z: z["area"], reverse=True)

        # Filter overlapping zones
        zones = self._filter_overlapping(zones)

        logger.info(f"After filtering: {len(zones)} zones")

        return zones

    def detect_zones_from_path(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect zones from an image file path.

        Args:
            image_path: Path to the image file

        Returns:
            List of detected zones
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        return self.detect_zones(image_rgb)

    def _filter_overlapping(
        self,
        zones: List[Dict[str, Any]],
        iou_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Filter out zones that significantly overlap with larger zones.

        Args:
            zones: List of zones sorted by area (largest first)
            iou_threshold: IoU threshold above which to filter

        Returns:
            Filtered list of zones
        """
        if not zones:
            return []

        keep = []
        for zone in zones:
            # Check if this zone overlaps significantly with any kept zone
            is_duplicate = False
            for kept in keep:
                iou = self._compute_bbox_iou(zone["bbox"], kept["bbox"])
                if iou > iou_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                keep.append(zone)

        return keep

    def _compute_bbox_iou(
        self,
        bbox1: Dict[str, int],
        bbox2: Dict[str, int]
    ) -> float:
        """Compute IoU between two bounding boxes."""
        x1_1, y1_1 = bbox1["x"], bbox1["y"]
        x2_1, y2_1 = x1_1 + bbox1["width"], y1_1 + bbox1["height"]

        x1_2, y1_2 = bbox2["x"], bbox2["y"]
        x2_2, y2_2 = x1_2 + bbox2["width"], y1_2 + bbox2["height"]

        # Intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i < x1_i or y2_i < y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # Union
        area1 = bbox1["width"] * bbox1["height"]
        area2 = bbox2["width"] * bbox2["height"]
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def filter_by_size(
        self,
        zones: List[Dict[str, Any]],
        image_shape: Tuple[int, int],
        min_ratio: float = 0.01,
        max_ratio: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Filter zones by size relative to image.

        Args:
            zones: List of zones
            image_shape: (height, width) of image
            min_ratio: Minimum area ratio
            max_ratio: Maximum area ratio

        Returns:
            Filtered zones
        """
        h, w = image_shape
        image_area = h * w

        filtered = []
        for zone in zones:
            ratio = zone["area"] / image_area
            if min_ratio <= ratio <= max_ratio:
                filtered.append(zone)

        logger.info(f"Size filter: {len(zones)} -> {len(filtered)} zones")
        return filtered


def create_grid_zones(
    image_shape: Tuple[int, int],
    rows: int = 3,
    cols: int = 3
) -> List[Dict[str, Any]]:
    """
    Create a simple grid of zones as fallback when SAM isn't available.

    Args:
        image_shape: (height, width) of image
        rows: Number of rows
        cols: Number of columns

    Returns:
        List of grid zones
    """
    h, w = image_shape
    cell_h = h // rows
    cell_w = w // cols

    zones = []
    zone_id = 1

    for row in range(rows):
        for col in range(cols):
            y = row * cell_h
            x = col * cell_w

            zones.append({
                "id": f"zone_{zone_id}",
                "bbox": {
                    "x": x,
                    "y": y,
                    "width": cell_w,
                    "height": cell_h
                },
                "area": cell_w * cell_h,
                "confidence": 0.5,
                "source": "grid_fallback"
            })
            zone_id += 1

    logger.info(f"Created {len(zones)} grid zones ({rows}x{cols})")
    return zones


def visualize_zones(
    image: np.ndarray,
    zones: List[Dict[str, Any]],
    output_path: Optional[str] = None,
    show_labels: bool = True
) -> np.ndarray:
    """
    Draw detected zones on an image for visualization.

    Args:
        image: BGR image
        zones: List of zones with bbox
        output_path: Optional path to save
        show_labels: Whether to show zone labels

    Returns:
        Image with zones drawn
    """
    vis = image.copy()

    # Colors for different zones (cycle through)
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (128, 0, 255), (255, 128, 0), (0, 128, 255)
    ]

    for i, zone in enumerate(zones):
        color = colors[i % len(colors)]
        bbox = zone["bbox"]

        x, y = bbox["x"], bbox["y"]
        w, h = bbox["width"], bbox["height"]

        # Draw rectangle
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)

        # Draw label
        if show_labels:
            label = zone.get("label", zone.get("id", f"Zone {i+1}"))
            confidence = zone.get("confidence", 0)
            text = f"{label} ({confidence:.0%})"

            # Background for text
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(vis, (x, y - text_h - 4), (x + text_w, y), color, -1)
            cv2.putText(vis, text, (x, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    if output_path:
        cv2.imwrite(output_path, vis)
        logger.info(f"Saved zone visualization to {output_path}")

    return vis


# Singleton instance
_sam_detector: Optional[SAM3ZoneDetector] = None


def get_sam_detector() -> SAM3ZoneDetector:
    """Get or create the SAM detector singleton."""
    global _sam_detector
    if _sam_detector is None:
        _sam_detector = SAM3ZoneDetector()
    return _sam_detector
