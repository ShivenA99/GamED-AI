"""
Line Detection Service for detecting leader lines in educational diagrams.

Uses Hough Line Transform to detect straight lines and filters them based on
proximity to text regions to distinguish leader lines from diagram structure.

Key Features:
1. Probabilistic Hough Transform for line detection
2. Proximity filtering to keep only lines near text labels
3. Morphological mask creation with configurable line thickness
4. Canny edge detection preprocessing
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("gamed_ai.services.line_detection")


class HoughLineDetector:
    """
    Detect leader lines in diagrams using Probabilistic Hough Transform.

    Leader lines are the lines connecting text labels to diagram parts.
    This detector is designed to distinguish them from diagram structure lines.
    """

    def __init__(
        self,
        min_line_length: int = 30,
        max_line_gap: int = 10,
        proximity_threshold: int = 50,
        canny_low: int = 50,
        canny_high: int = 150,
        hough_threshold: int = 50
    ):
        """
        Initialize the Hough line detector.

        Args:
            min_line_length: Minimum line length in pixels (shorter = more lines, more noise)
            max_line_gap: Maximum gap between line segments to be connected
            proximity_threshold: Maximum distance from text box to consider line as leader
            canny_low: Lower threshold for Canny edge detection
            canny_high: Higher threshold for Canny edge detection
            hough_threshold: Accumulator threshold for Hough transform
        """
        self.min_line_length = int(os.getenv("HOUGH_MIN_LINE_LENGTH", str(min_line_length)))
        self.max_line_gap = int(os.getenv("HOUGH_MAX_LINE_GAP", str(max_line_gap)))
        self.proximity_threshold = int(os.getenv("HOUGH_PROXIMITY_THRESHOLD", str(proximity_threshold)))
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.hough_threshold = hough_threshold

        logger.info(
            f"HoughLineDetector initialized: min_line_length={self.min_line_length}, "
            f"max_line_gap={self.max_line_gap}, proximity_threshold={self.proximity_threshold}"
        )

    def detect_lines(self, image_path: str) -> Optional[np.ndarray]:
        """
        Detect straight lines using Probabilistic Hough Transform.

        Args:
            image_path: Path to the image file

        Returns:
            Array of lines, each as [[x1, y1, x2, y2]], or None if no lines found
        """
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Could not load image: {image_path}")
            return None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Canny edge detection
        edges = cv2.Canny(blurred, self.canny_low, self.canny_high, apertureSize=3)

        # Probabilistic Hough Line Transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap
        )

        if lines is not None:
            logger.info(f"Hough transform detected {len(lines)} lines")
        else:
            logger.info("No lines detected by Hough transform")

        return lines

    def _point_near_box(
        self,
        point: Tuple[int, int],
        box: Dict[str, Any],
        max_distance: int
    ) -> bool:
        """
        Check if a point is within max_distance pixels of a bounding box.

        Args:
            point: (x, y) coordinates
            box: Dict with 'x', 'y', 'width', 'height' keys
            max_distance: Maximum distance in pixels

        Returns:
            True if point is near the box
        """
        px, py = point
        bx = box.get("x", 0)
        by = box.get("y", 0)
        bw = box.get("width", 0)
        bh = box.get("height", 0)

        # Calculate distance from point to box edges
        # If point is inside the box, distance is 0
        dx = max(bx - px, 0, px - (bx + bw))
        dy = max(by - py, 0, py - (by + bh))

        distance = np.sqrt(dx**2 + dy**2)
        return distance <= max_distance

    def filter_lines_near_text(
        self,
        lines: Optional[np.ndarray],
        text_boxes: List[Dict[str, Any]],
        max_distance: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        Keep only lines within max_distance pixels of any text box.

        This filters out diagram structure lines by keeping only those
        that are likely to be leader lines (near text labels).

        Args:
            lines: Array of detected lines from Hough transform
            text_boxes: List of text bounding boxes with 'bbox' dict containing x, y, width, height
            max_distance: Maximum distance from text (defaults to proximity_threshold)

        Returns:
            List of filtered lines
        """
        if lines is None or len(lines) == 0:
            return []

        if not text_boxes:
            logger.warning("No text boxes provided for filtering - returning empty list")
            return []

        max_dist = max_distance or self.proximity_threshold
        filtered = []

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Check if either endpoint is near any text box
            for text_region in text_boxes:
                # Handle different bbox formats
                if "bbox" in text_region:
                    box = text_region["bbox"]
                else:
                    box = text_region

                if self._point_near_box((x1, y1), box, max_dist) or \
                   self._point_near_box((x2, y2), box, max_dist):
                    filtered.append(line)
                    break

        logger.info(f"Filtered {len(lines)} lines to {len(filtered)} lines near text")
        return filtered

    def filter_by_angle(
        self,
        lines: List[np.ndarray],
        allowed_angles: List[Tuple[float, float]] = None
    ) -> List[np.ndarray]:
        """
        Filter lines by their angle.

        Leader lines are typically nearly horizontal, vertical, or 45-degree diagonal.
        Lines at odd angles are likely diagram structure.

        Args:
            lines: List of lines to filter
            allowed_angles: List of (min, max) angle ranges in degrees.
                           Defaults to horizontal (0-20), vertical (70-90), diagonal (40-50)

        Returns:
            Filtered list of lines
        """
        if not lines:
            return []

        if allowed_angles is None:
            allowed_angles = [
                (0, 20),    # Nearly horizontal
                (70, 90),   # Nearly vertical
                (40, 50),   # Diagonal
            ]

        filtered = []

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Calculate angle in degrees (0-90 range)
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            if angle > 90:
                angle = 180 - angle

            # Check if angle falls within any allowed range
            for min_angle, max_angle in allowed_angles:
                if min_angle <= angle <= max_angle:
                    filtered.append(line)
                    break

        logger.info(f"Angle filter: {len(lines)} -> {len(filtered)} lines")
        return filtered

    def filter_by_length(
        self,
        lines: List[np.ndarray],
        image_shape: Tuple[int, int],
        min_length_ratio: float = 0.02,
        max_length_ratio: float = 0.15
    ) -> List[np.ndarray]:
        """
        Filter lines by length relative to image size.

        Leader lines are typically short (2-15% of image dimension).
        Very short lines are noise, very long lines are diagram structure.

        Args:
            lines: List of lines to filter
            image_shape: (height, width) of the image
            min_length_ratio: Minimum line length as ratio of image diagonal
            max_length_ratio: Maximum line length as ratio of image diagonal

        Returns:
            Filtered list of lines
        """
        if not lines:
            return []

        h, w = image_shape[:2]
        diagonal = np.sqrt(h**2 + w**2)
        min_length = diagonal * min_length_ratio
        max_length = diagonal * max_length_ratio

        filtered = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

            if min_length <= length <= max_length:
                filtered.append(line)

        logger.info(
            f"Length filter (min={min_length:.1f}, max={max_length:.1f}): "
            f"{len(lines)} -> {len(filtered)} lines"
        )
        return filtered

    def create_mask(
        self,
        image_shape: Tuple[int, ...],
        lines: List[np.ndarray],
        thickness: int = 8
    ) -> np.ndarray:
        """
        Create binary mask from detected lines.

        Args:
            image_shape: Shape of the image (height, width, ...)
            lines: List of lines to draw
            thickness: Line thickness for the mask

        Returns:
            Binary mask (255 where lines are, 0 elsewhere)
        """
        h, w = image_shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        if lines is None or len(lines) == 0:
            return mask

        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(mask, (x1, y1), (x2, y2), 255, thickness)

        logger.info(f"Created line mask with {len(lines)} lines, thickness={thickness}")
        return mask

    def detect_and_filter(
        self,
        image_path: str,
        text_boxes: List[Dict[str, Any]]
    ) -> Tuple[List[np.ndarray], np.ndarray]:
        """
        Complete pipeline: detect lines, filter by proximity and angle.

        Args:
            image_path: Path to the image
            text_boxes: List of text bounding boxes

        Returns:
            Tuple of (filtered_lines, line_mask)
        """
        # Load image for dimensions
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Could not load image: {image_path}")
            return [], np.zeros((1, 1), dtype=np.uint8)

        # Detect all lines
        lines = self.detect_lines(image_path)
        if lines is None:
            return [], np.zeros(img.shape[:2], dtype=np.uint8)

        # Filter by proximity to text
        filtered = self.filter_lines_near_text(lines, text_boxes)

        # Filter by length (exclude very short noise and very long structure lines)
        filtered = self.filter_by_length(filtered, img.shape)

        # Filter by angle (keep horizontal, vertical, diagonal)
        filtered = self.filter_by_angle(filtered)

        # Create mask
        mask = self.create_mask(img.shape, filtered)

        return filtered, mask

    def visualize_lines(
        self,
        image_path: str,
        lines: List[np.ndarray],
        output_path: Optional[str] = None,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw detected lines on the image for visualization.

        Args:
            image_path: Path to the original image
            lines: List of lines to draw
            output_path: Optional path to save the visualization
            color: BGR color for the lines
            thickness: Line thickness

        Returns:
            Image with lines drawn
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        vis = img.copy()

        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(vis, (x1, y1), (x2, y2), color, thickness)

        if output_path:
            cv2.imwrite(output_path, vis)
            logger.info(f"Saved line visualization to {output_path}")

        return vis


# Singleton instance
_line_detector: Optional[HoughLineDetector] = None


def get_line_detector() -> HoughLineDetector:
    """Get or create the line detector singleton."""
    global _line_detector
    if _line_detector is None:
        _line_detector = HoughLineDetector()
    return _line_detector
