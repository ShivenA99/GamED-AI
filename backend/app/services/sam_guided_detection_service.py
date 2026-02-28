"""
SAM-Guided Leader Line Detection Service.

Uses SAM3 with point prompts derived from text label positions to accurately
detect and segment leader lines. The approach:

1. Use EasyOCR to detect text labels
2. For each text label, compute likely leader line attachment points
3. Use SAM3 with these points as prompts to segment the leader line
4. Optionally use CLIP to verify the segmentation is an annotation

This is more accurate than Hough because:
- SAM3 understands visual boundaries (not just straight lines)
- Point prompts guide SAM to the exact leader line
- Can handle curved or angled leader lines
- CLIP verification reduces false positives
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("gamed_ai.services.sam_guided_detection")


class SAMGuidedLineDetector:
    """
    Detect leader lines using SAM3 with text-derived point prompts.

    Strategy:
    1. Detect text labels with EasyOCR
    2. For each text box, identify candidate attachment points (edges)
    3. Use SAM3 to segment from those points
    4. Filter segments that look like leader lines (thin, elongated)
    """

    def __init__(self, sam_model_path: str = None):
        """Initialize the SAM-guided detector."""
        self.sam_model_path = sam_model_path or os.getenv("SAM3_MODEL_PATH")
        self._sam = None
        self._predictor = None
        self._device = None
        logger.info("SAMGuidedLineDetector initialized")

    def _ensure_sam_loaded(self):
        """Lazy load SAM model."""
        if self._sam is not None:
            return

        if not self.sam_model_path or not Path(self.sam_model_path).exists():
            raise RuntimeError(
                f"SAM model not found at: {self.sam_model_path}. "
                "Download from: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
            )

        try:
            import torch
            from segment_anything import sam_model_registry, SamPredictor

            logger.info(f"Loading SAM model from: {self.sam_model_path}")

            # Choose device
            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"

            # Load model
            sam = sam_model_registry["vit_h"](checkpoint=self.sam_model_path)
            sam = sam.to(self._device)
            self._sam = sam
            self._predictor = SamPredictor(sam)

            logger.info(f"SAM model loaded on device: {self._device}")

        except ImportError as e:
            raise ImportError(
                "SAM requires segment-anything. Install with: pip install segment-anything"
            ) from e

    def _get_text_edge_points(
        self,
        text_box: Dict[str, Any],
        image_shape: Tuple[int, int],
        num_points: int = 3
    ) -> List[Tuple[int, int]]:
        """
        Get candidate attachment points along the edges of a text box.

        Leader lines typically attach to the left, right, or bottom edge
        of text labels in educational diagrams.
        """
        bbox = text_box.get("bbox", {})
        x = bbox.get("x", 0)
        y = bbox.get("y", 0)
        w = bbox.get("width", 0)
        h = bbox.get("height", 0)

        h_img, w_img = image_shape

        points = []

        # Left edge points (leader lines often come from the left)
        for i in range(num_points):
            py = y + (i + 1) * h // (num_points + 1)
            points.append((max(0, x - 5), py))

        # Right edge points
        for i in range(num_points):
            py = y + (i + 1) * h // (num_points + 1)
            points.append((min(w_img - 1, x + w + 5), py))

        # Bottom edge center (for vertical leader lines)
        points.append((x + w // 2, min(h_img - 1, y + h + 5)))

        # Top edge center
        points.append((x + w // 2, max(0, y - 5)))

        return points

    def _is_leader_line_segment(
        self,
        mask: np.ndarray,
        min_aspect_ratio: float = 3.0,
        max_area_ratio: float = 0.05
    ) -> bool:
        """
        Check if a segmented mask looks like a leader line.

        Leader lines are:
        - Thin and elongated (high aspect ratio)
        - Small relative to image (low area ratio)
        """
        # Find contours
        contours, _ = cv2.findContours(
            mask.astype(np.uint8) * 255,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return False

        # Get largest contour
        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)

        # Check area ratio
        image_area = mask.shape[0] * mask.shape[1]
        if area / image_area > max_area_ratio:
            return False

        # Check aspect ratio using rotated bounding box
        if len(contour) >= 5:
            rect = cv2.minAreaRect(contour)
            w, h = rect[1]
            if w > 0 and h > 0:
                aspect = max(w, h) / min(w, h)
                if aspect >= min_aspect_ratio:
                    return True

        return False

    def detect_leader_lines(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]],
        confidence_threshold: float = 0.5
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Detect leader lines using SAM with text-derived prompts.

        Args:
            image: RGB image as numpy array
            text_regions: List of text regions from EasyOCR
            confidence_threshold: Minimum SAM confidence to accept

        Returns:
            Tuple of (combined_mask, list_of_line_segments)
        """
        self._ensure_sam_loaded()

        h, w = image.shape[:2]
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        line_segments = []

        # Set image for SAM predictor
        self._predictor.set_image(image)

        for i, text_region in enumerate(text_regions):
            # Get candidate points along text box edges
            edge_points = self._get_text_edge_points(text_region, (h, w))

            for point in edge_points:
                px, py = point

                # Use SAM to segment from this point
                # Label 1 = foreground, 0 = background
                input_point = np.array([[px, py]])
                input_label = np.array([1])

                masks, scores, _ = self._predictor.predict(
                    point_coords=input_point,
                    point_labels=input_label,
                    multimask_output=True
                )

                # Check each mask
                for mask, score in zip(masks, scores):
                    if score < confidence_threshold:
                        continue

                    # Check if this looks like a leader line
                    if self._is_leader_line_segment(mask):
                        # Add to combined mask
                        combined_mask = np.maximum(combined_mask, mask.astype(np.uint8) * 255)

                        line_segments.append({
                            "text_region_idx": i,
                            "prompt_point": point,
                            "confidence": float(score),
                            "mask": mask
                        })

                        logger.debug(
                            f"Found leader line from text '{text_region.get('text', '')}' "
                            f"at point {point} with confidence {score:.2f}"
                        )

        logger.info(f"SAM detected {len(line_segments)} leader line segments")

        return combined_mask, line_segments

    def detect_with_negative_prompts(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]],
        diagram_center: Tuple[int, int] = None
    ) -> np.ndarray:
        """
        Detect leader lines using both positive (text edges) and negative
        (diagram center) prompts to better distinguish annotations from content.

        The negative prompt tells SAM "this area is NOT what I want" which
        helps it avoid segmenting diagram content.
        """
        self._ensure_sam_loaded()

        h, w = image.shape[:2]
        combined_mask = np.zeros((h, w), dtype=np.uint8)

        # Default diagram center
        if diagram_center is None:
            diagram_center = (w // 2, h // 2)

        self._predictor.set_image(image)

        for text_region in text_regions:
            edge_points = self._get_text_edge_points(text_region, (h, w))

            for point in edge_points:
                px, py = point

                # Positive point: edge of text (where leader line attaches)
                # Negative point: center of diagram (content, not annotation)
                input_points = np.array([[px, py], list(diagram_center)])
                input_labels = np.array([1, 0])  # 1=foreground, 0=background

                masks, scores, _ = self._predictor.predict(
                    point_coords=input_points,
                    point_labels=input_labels,
                    multimask_output=True
                )

                # Take best mask that looks like a leader line
                for mask, score in zip(masks, scores):
                    if score > 0.5 and self._is_leader_line_segment(mask):
                        combined_mask = np.maximum(combined_mask, mask.astype(np.uint8) * 255)
                        break

        return combined_mask


class SAMCLIPLineDetector:
    """
    Combines SAM segmentation with CLIP verification for robust leader line detection.

    1. SAM segments candidate regions from text edge points
    2. CLIP verifies each segment is an annotation (not diagram content)
    """

    def __init__(self, sam_model_path: str = None, clip_model: str = None):
        """Initialize SAM+CLIP detector."""
        self.sam_detector = SAMGuidedLineDetector(sam_model_path)
        self.clip_model = clip_model or os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
        self._clip = None
        self._processor = None
        self._device = None

    def _ensure_clip_loaded(self):
        """Lazy load CLIP model."""
        if self._clip is not None:
            return

        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel

            logger.info(f"Loading CLIP model: {self.clip_model}")

            self._clip = CLIPModel.from_pretrained(self.clip_model)
            self._processor = CLIPProcessor.from_pretrained(self.clip_model)

            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"

            self._clip = self._clip.to(self._device)
            logger.info(f"CLIP model loaded on device: {self._device}")

        except ImportError as e:
            raise ImportError(
                "CLIP requires transformers. Install with: pip install transformers"
            ) from e

    def _verify_annotation_with_clip(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        threshold: float = 0.5
    ) -> float:
        """
        Use CLIP to verify if a masked region is an annotation.

        Returns confidence score that this is an annotation (0-1).
        """
        import torch
        from PIL import Image

        self._ensure_clip_loaded()

        # Get bounding box of mask
        coords = np.where(mask)
        if len(coords[0]) == 0:
            return 0.0

        y_min, y_max = coords[0].min(), coords[0].max()
        x_min, x_max = coords[1].min(), coords[1].max()

        # Add padding
        padding = 10
        y_min = max(0, y_min - padding)
        y_max = min(image.shape[0], y_max + padding)
        x_min = max(0, x_min - padding)
        x_max = min(image.shape[1], x_max + padding)

        # Crop region
        crop = image[y_min:y_max, x_min:x_max]
        if crop.size == 0:
            return 0.0

        pil_crop = Image.fromarray(crop)

        # CLIP classification
        labels = [
            "annotation line pointer arrow label marker",
            "biological structure organ cell tissue diagram content"
        ]

        inputs = self._processor(
            text=labels,
            images=pil_crop,
            return_tensors="pt",
            padding=True
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._clip(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)[0]

        annotation_score = float(probs[0])
        return annotation_score

    def detect_leader_lines(
        self,
        image: np.ndarray,
        text_regions: List[Dict[str, Any]],
        clip_threshold: float = 0.5
    ) -> np.ndarray:
        """
        Detect leader lines with SAM and verify with CLIP.

        Args:
            image: RGB image
            text_regions: Text regions from EasyOCR
            clip_threshold: Minimum CLIP annotation score to accept

        Returns:
            Combined mask of verified leader lines
        """
        # Get SAM candidate segments
        _, segments = self.sam_detector.detect_leader_lines(image, text_regions)

        h, w = image.shape[:2]
        verified_mask = np.zeros((h, w), dtype=np.uint8)

        verified_count = 0
        for segment in segments:
            mask = segment["mask"]

            # Verify with CLIP
            clip_score = self._verify_annotation_with_clip(image, mask)

            if clip_score >= clip_threshold:
                verified_mask = np.maximum(verified_mask, mask.astype(np.uint8) * 255)
                verified_count += 1
                logger.debug(f"CLIP verified segment with score {clip_score:.2f}")
            else:
                logger.debug(f"CLIP rejected segment with score {clip_score:.2f}")

        logger.info(f"CLIP verified {verified_count}/{len(segments)} SAM segments")

        return verified_mask


# Singleton instances
_sam_guided_detector: Optional[SAMGuidedLineDetector] = None
_sam_clip_detector: Optional[SAMCLIPLineDetector] = None


def get_sam_guided_detector() -> SAMGuidedLineDetector:
    """Get or create the SAM-guided detector singleton."""
    global _sam_guided_detector
    if _sam_guided_detector is None:
        _sam_guided_detector = SAMGuidedLineDetector()
    return _sam_guided_detector


def get_sam_clip_detector() -> SAMCLIPLineDetector:
    """Get or create the SAM+CLIP detector singleton."""
    global _sam_clip_detector
    if _sam_clip_detector is None:
        _sam_clip_detector = SAMCLIPLineDetector()
    return _sam_clip_detector
