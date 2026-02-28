"""
Inpainting Service for removing text labels from diagram images.

Uses a tiered approach for best results:
1. Stable Diffusion inpainting (highest quality, GPU recommended)
2. LaMa via IOPaint (good quality, fast)
3. OpenCV inpainting (fallback, always available)

Text detection uses EasyOCR with fallback to VLM-based detection.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("gamed_ai.services.inpainting")

# Import advanced inpainting services
try:
    from app.services.lama_inpainting_service import (
        get_sd_service, get_lama_service, opencv_inpaint, get_inpainting_method
    )
    ADVANCED_INPAINTING_AVAILABLE = True
except ImportError:
    ADVANCED_INPAINTING_AVAILABLE = False
    logger.warning("Advanced inpainting services not available")


class InpaintingError(Exception):
    """Raised when inpainting operations fail."""
    pass


class InpaintingService:
    """
    Text detection + removal using EasyOCR + Inpaint Anything (SAM + LaMa).

    Workflow:
    1. Detect text regions using EasyOCR
    2. For each text region, use Inpaint Anything to remove it
    3. Return cleaned image path

    Environment Variables:
    - INPAINT_ANYTHING_PATH: Path to Inpaint Anything repo (default: ./third_party/Inpaint-Anything)
    - SAM_CKPT: SAM model checkpoint path
    - LAMA_CKPT: LaMa model checkpoint path
    - EASYOCR_GPU: Whether to use GPU for EasyOCR (default: true)
    """

    def __init__(self):
        self._reader = None
        self.inpaint_anything_path = Path(os.getenv(
            "INPAINT_ANYTHING_PATH",
            str(Path(__file__).parent.parent.parent / "third_party" / "Inpaint-Anything")
        ))
        self.sam_ckpt = os.getenv(
            "SAM_CKPT",
            str(Path(__file__).parent.parent.parent / "pretrained_models" / "sam_vit_h_4b8939.pth")
        )
        self.lama_ckpt = os.getenv(
            "LAMA_CKPT",
            str(Path(__file__).parent.parent.parent / "pretrained_models" / "big-lama")
        )
        self.use_gpu = os.getenv("EASYOCR_GPU", "true").lower() == "true"

    @property
    def reader(self):
        """Lazy load EasyOCR reader."""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(['en'], gpu=self.use_gpu)
            except ImportError:
                raise InpaintingError("EasyOCR not installed. Run: pip install easyocr")
        return self._reader

    async def detect_text_regions(self, image_path: str, min_confidence: float = 0.3) -> List[Dict[str, Any]]:
        """
        Use EasyOCR to find text bounding boxes and center points.
        Uses lower confidence threshold to catch more text.

        Args:
            image_path: Path to the image file
            min_confidence: Minimum confidence threshold (lower = more text detected)

        Returns:
            List of detected text regions with bbox, text, confidence, and center
        """
        logger.info(f"InpaintingService: Detecting text in {image_path} (min_confidence={min_confidence})")

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self.reader.readtext(image_path, detail=1)
        )

        regions = []
        for bbox, text, confidence in results:
            # Filter by confidence
            if confidence < min_confidence:
                continue
                
            # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]

            # Calculate center
            center_x = int(sum(x_coords) / 4)
            center_y = int(sum(y_coords) / 4)

            # Calculate bounding box
            x_min, x_max = int(min(x_coords)), int(max(x_coords))
            y_min, y_max = int(min(y_coords)), int(max(y_coords))

            regions.append({
                "bbox": {
                    "x": x_min,
                    "y": y_min,
                    "width": x_max - x_min,
                    "height": y_max - y_min
                },
                "polygon": bbox,
                "text": text,
                "confidence": confidence,
                "center": (center_x, center_y)
            })

        logger.info(f"InpaintingService: Found {len(regions)} text regions (min_confidence={min_confidence})")
        return regions

    async def detect_lines(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect horizontal and vertical lines in the image (label connectors).
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of line regions with bbox and type
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.warning("OpenCV not available for line detection")
            return []
        
        # Load image
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return []
        
        height, width = img.shape
        
        # Detect edges
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        
        # Detect horizontal lines
        horizontal_lines = cv2.HoughLinesP(
            edges, 1, np.pi/180, threshold=100,
            minLineLength=width * 0.1,  # At least 10% of image width
            maxLineGap=10
        )
        
        # Detect vertical lines
        vertical_lines = cv2.HoughLinesP(
            edges, 1, np.pi/180, threshold=100,
            minLineLength=height * 0.1,  # At least 10% of image height
            maxLineGap=10
        )
        
        line_regions = []
        line_thickness = 3  # Thickness for mask
        
        # Process horizontal lines
        if horizontal_lines is not None:
            for line in horizontal_lines:
                x1, y1, x2, y2 = line[0]
                # Create bbox around line
                x_min, x_max = min(x1, x2), max(x1, x2)
                y_min, y_max = min(y1, y2) - line_thickness, max(y1, y2) + line_thickness
                line_regions.append({
                    "bbox": {
                        "x": max(0, x_min),
                        "y": max(0, y_min),
                        "width": min(width, x_max) - max(0, x_min),
                        "height": min(height, y_max) - max(0, y_min)
                    },
                    "type": "horizontal"
                })
        
        # Process vertical lines
        if vertical_lines is not None:
            for line in vertical_lines:
                x1, y1, x2, y2 = line[0]
                # Create bbox around line
                x_min, x_max = min(x1, x2) - line_thickness, max(x1, x2) + line_thickness
                y_min, y_max = min(y1, y2), max(y1, y2)
                line_regions.append({
                    "bbox": {
                        "x": max(0, x_min),
                        "y": max(0, y_min),
                        "width": min(width, x_max) - max(0, x_min),
                        "height": min(height, y_max) - max(0, y_min)
                    },
                    "type": "vertical"
                })
        
        logger.info(f"InpaintingService: Detected {len(line_regions)} lines")
        return line_regions

    def _calculate_adaptive_dilation(
        self,
        text_regions: List[Dict[str, Any]],
        image_width: int,
        image_height: int
    ) -> int:
        """
        Calculate adaptive dilation based on text region sizes.

        Small text (< 20px): 10-15 dilation (avoid over-aggressive cleaning)
        Medium text (20-40px): 20-30 dilation
        Large text (> 40px): 35-50 dilation

        Also considers image resolution - larger images need more dilation.

        Args:
            text_regions: List of detected text regions with bbox info
            image_width: Image width in pixels
            image_height: Image height in pixels

        Returns:
            Adaptive dilation value in pixels
        """
        if not text_regions:
            return 20  # Default fallback

        # Calculate average text height
        heights = [r["bbox"]["height"] for r in text_regions if r.get("bbox")]
        if not heights:
            return 20

        avg_height = sum(heights) / len(heights)
        max_height = max(heights)
        min_height = min(heights)

        # Base dilation proportional to text size
        # Use 80% of average height as base, with min/max constraints
        base_dilation = int(avg_height * 0.8)

        # Adjust for image resolution (larger images need more dilation)
        # Use 1000px as baseline
        resolution_factor = max(0.7, min(1.5, max(image_width, image_height) / 1000.0))

        # Apply resolution scaling
        scaled_dilation = int(base_dilation * resolution_factor)

        # Apply final constraints
        # Min: 10px (avoid too small masks)
        # Max: 50px (avoid removing diagram features)
        final_dilation = max(10, min(50, scaled_dilation))

        logger.debug(
            f"Adaptive dilation: avg_height={avg_height:.1f}px, "
            f"base={base_dilation}px, scale={resolution_factor:.2f}, "
            f"final={final_dilation}px"
        )

        return final_dilation

    def _calculate_region_specific_dilation(
        self,
        region: Dict[str, Any],
        base_dilation: int,
        region_type: str = "text"
    ) -> int:
        """
        Calculate dilation for a specific region.

        Applies different dilation for text vs lines to preserve diagram structure.

        Args:
            region: The region dict with bbox
            base_dilation: Base dilation calculated for the image
            region_type: "text" or "line"

        Returns:
            Region-specific dilation value
        """
        if region_type == "line":
            # Lines need less dilation to preserve diagram structure
            return max(3, base_dilation // 3)

        # Text regions use full dilation
        bbox = region.get("bbox", {})
        region_height = bbox.get("height", 20)

        # Scale dilation based on region size relative to average
        # Smaller text gets slightly less dilation to avoid over-cleaning
        if region_height < 15:
            return max(8, int(base_dilation * 0.7))
        elif region_height > 40:
            return min(50, int(base_dilation * 1.2))

        return base_dilation

    async def create_text_mask(
        self,
        image_path: str,
        text_regions: List[Dict[str, Any]],
        dilation: int = None,  # Now optional - will be calculated adaptively
        include_lines: bool = True
    ) -> str:
        """
        Create a binary mask covering all text regions and connecting lines.

        Uses adaptive dilation based on text sizes to avoid over-aggressive
        cleaning on small text while ensuring complete coverage on large text.

        Args:
            image_path: Path to the source image
            text_regions: List of text regions from detect_text_regions
            dilation: Optional override for dilation (calculated adaptively if None)
            include_lines: Whether to also mask connecting lines

        Returns:
            Path to the mask image
        """
        try:
            from PIL import Image, ImageDraw
            import numpy as np
        except ImportError:
            raise InpaintingError("PIL not installed. Run: pip install Pillow")

        # Load image to get dimensions
        image = Image.open(image_path)
        width, height = image.size

        # Calculate adaptive dilation if not specified
        if dilation is None:
            dilation = self._calculate_adaptive_dilation(text_regions, width, height)
            logger.info(f"Using adaptive dilation: {dilation}px for {len(text_regions)} text regions")

        # Create black mask (0 = keep, 255 = inpaint)
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)

        # Mask text regions with region-specific dilation
        for region in text_regions:
            bbox = region["bbox"]
            x, y = bbox["x"], bbox["y"]
            w, h = bbox["width"], bbox["height"]

            # Calculate region-specific dilation
            region_dilation = self._calculate_region_specific_dilation(
                region, dilation, "text"
            )

            # Apply dilation (adaptive for better coverage)
            x1 = max(0, x - region_dilation)
            y1 = max(0, y - region_dilation)
            x2 = min(width, x + w + region_dilation)
            y2 = min(height, y + h + region_dilation)

            draw.rectangle([x1, y1, x2, y2], fill=255)

        # Mask connecting lines if enabled
        line_regions = []
        if include_lines:
            line_regions = await self.detect_lines(image_path)
            # Calculate line-specific dilation (less aggressive than text)
            line_dilation = self._calculate_region_specific_dilation(
                {"bbox": {"height": dilation}}, dilation, "line"
            )

            for line_region in line_regions:
                bbox = line_region["bbox"]
                x, y = bbox["x"], bbox["y"]
                w, h = bbox["width"], bbox["height"]

                # Check if line is near any text region (within 50 pixels)
                is_near_text = False
                for text_region in text_regions:
                    tx, ty = text_region["bbox"]["x"], text_region["bbox"]["y"]
                    tw, th = text_region["bbox"]["width"], text_region["bbox"]["height"]
                    tx_center = tx + tw / 2
                    ty_center = ty + th / 2
                    line_center_x = x + w / 2
                    line_center_y = y + h / 2

                    # Check proximity (scaled by image size for consistency)
                    proximity_threshold = max(80, min(width, height) * 0.1)
                    dist = np.sqrt((tx_center - line_center_x)**2 + (ty_center - line_center_y)**2)
                    if dist < proximity_threshold:
                        is_near_text = True
                        break

                if is_near_text:
                    # Mask the line with adaptive padding (less than text)
                    x1 = max(0, x - line_dilation)
                    y1 = max(0, y - line_dilation)
                    x2 = min(width, x + w + line_dilation)
                    y2 = min(height, y + h + line_dilation)
                    draw.rectangle([x1, y1, x2, y2], fill=255)

        # Save mask
        mask_path = str(Path(image_path).parent / f"{Path(image_path).stem}_mask.png")
        mask.save(mask_path)

        logger.info(f"InpaintingService: Created text+line mask at {mask_path} ({len(text_regions)} text regions, {len(line_regions) if include_lines else 0} lines)")
        return mask_path

    async def _inpaint_with_inpaint_anything(
        self,
        image_path: str,
        text_regions: List[Dict[str, Any]],
        output_dir: str
    ) -> str:
        """
        Remove text using Inpaint Anything's remove_anything.py script.
        Processes each text region iteratively for cleaner results.
        """
        if not self.inpaint_anything_path.exists():
            raise InpaintingError(
                f"Inpaint Anything not found at {self.inpaint_anything_path}. "
                "Clone from: https://github.com/geekyutao/Inpaint-Anything"
            )

        current_image = image_path

        for i, region in enumerate(text_regions):
            center_x, center_y = region["center"]

            # Build command
            cmd = [
                "python",
                str(self.inpaint_anything_path / "remove_anything.py"),
                "--input_img", current_image,
                "--coords_type", "key_in",
                "--point_coords", str(center_x), str(center_y),
                "--point_labels", "1",
                "--dilate_kernel_size", "15",
                "--output_dir", output_dir,
                "--sam_model_type", "vit_h",
                "--sam_ckpt", self.sam_ckpt,
                "--lama_config", str(self.inpaint_anything_path / "lama" / "configs" / "prediction" / "default.yaml"),
                "--lama_ckpt", self.lama_ckpt
            ]

            logger.info(f"InpaintingService: Removing text '{region['text']}' at ({center_x}, {center_y})")

            # Run command
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True)
            )

            if result.returncode != 0:
                logger.error(f"Inpaint Anything failed: {result.stderr}")
                raise InpaintingError(f"Inpaint Anything failed: {result.stderr}")

            # Output is saved as *_removed.png
            output_file = Path(output_dir) / f"{Path(current_image).stem}_removed.png"
            if output_file.exists():
                current_image = str(output_file)
            else:
                # Try alternative naming
                output_files = list(Path(output_dir).glob("*_removed*.png"))
                if output_files:
                    current_image = str(sorted(output_files)[-1])

        return current_image

    async def _inpaint_with_opencv(
        self,
        image_path: str,
        mask_path: str,
        output_path: str
    ) -> str:
        """
        Fallback inpainting using OpenCV's inpaint function.
        Less sophisticated than LaMa but always available.
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            raise InpaintingError("OpenCV not installed. Run: pip install opencv-python")

        # Load image and mask
        image = cv2.imread(image_path)
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

        # Inpaint using Navier-Stokes algorithm (better quality than TELEA)
        # INPAINT_NS produces sharper edges and better results for text removal
        inpainted = cv2.inpaint(image, mask, inpaintRadius=15, flags=cv2.INPAINT_NS)

        cv2.imwrite(output_path, inpainted)
        logger.info(f"InpaintingService: OpenCV inpainting saved to {output_path}")

        return output_path

    async def _inpaint_with_simple_diffusion(
        self,
        image_path: str,
        mask_path: str,
        output_path: str
    ) -> str:
        """
        Inpainting using simple-lama-inpainting or IOPaint if available.
        """
        # Try IOPaint first (simple HTTP API)
        iopaint_url = os.getenv("IOPAINT_URL")
        if iopaint_url:
            try:
                import httpx
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

                        logger.info(f"InpaintingService: IOPaint inpainting saved to {output_path}")
                        return output_path
            except Exception as e:
                logger.warning(f"IOPaint failed: {e}, falling back to OpenCV")

        # Fall back to OpenCV
        return await self._inpaint_with_opencv(image_path, mask_path, output_path)

    async def clean_diagram(
        self,
        image_path: str,
        output_dir: str,
        method: str = "auto"
    ) -> Dict[str, Any]:
        """
        Full pipeline: detect text -> remove all labels -> return clean image.

        Uses a tiered inpainting approach for best results:
        1. Stable Diffusion (highest quality)
        2. LaMa via IOPaint (good quality, fast)
        3. OpenCV (fallback, always available)

        Args:
            image_path: Path to the input diagram image
            output_dir: Directory to save output files
            method: Inpainting method - "auto", "stable_diffusion", "lama", "opencv"

        Returns:
            Dict with cleaned_image_path, removed_labels, text_regions_found
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 1. Detect text regions
        text_regions = await self.detect_text_regions(image_path, min_confidence=0.5)

        if not text_regions:
            logger.info("InpaintingService: No text found, returning original image")
            return {
                "cleaned_image_path": image_path,
                "removed_labels": [],
                "text_regions_found": 0
            }

        # 2. Create mask (includes text and connecting lines)
        mask_path = await self.create_text_mask(image_path, text_regions, include_lines=True)

        # 3. Determine inpainting method
        if method == "auto" and ADVANCED_INPAINTING_AVAILABLE:
            method = get_inpainting_method()  # From env var or default

        logger.info(f"InpaintingService: Using {method} for inpainting ({len(text_regions)} text regions)")

        # 4. Perform inpainting with fallback chain
        output_path = str(Path(output_dir) / f"{Path(image_path).stem}_cleaned.png")
        cleaned_path = None
        inpaint_method_used = None

        # Try Stable Diffusion first (highest quality)
        if method in ["auto", "stable_diffusion"] and ADVANCED_INPAINTING_AVAILABLE:
            try:
                sd_service = get_sd_service()
                if await sd_service.is_available():
                    logger.info("InpaintingService: Trying Stable Diffusion inpainting...")
                    cleaned_path = await sd_service.inpaint(
                        image_path, mask_path, output_path,
                        prompt="clean educational diagram background, seamless, no text, scientific illustration style"
                    )
                    inpaint_method_used = "stable_diffusion"
                    logger.info(f"InpaintingService: SD inpainting succeeded")
            except Exception as e:
                logger.warning(f"InpaintingService: SD inpainting failed: {e}, trying LaMa...")

        # Try LaMa via IOPaint (good quality, faster)
        if cleaned_path is None and method in ["auto", "lama", "iopaint"] and ADVANCED_INPAINTING_AVAILABLE:
            try:
                lama_service = get_lama_service()
                if await lama_service.is_available():
                    logger.info("InpaintingService: Trying LaMa inpainting...")
                    cleaned_path = await lama_service.inpaint(image_path, mask_path, output_path)
                    inpaint_method_used = "lama"
                    logger.info(f"InpaintingService: LaMa inpainting succeeded")
            except Exception as e:
                logger.warning(f"InpaintingService: LaMa inpainting failed: {e}, trying OpenCV...")

        # Fallback to OpenCV (always available)
        if cleaned_path is None:
            try:
                logger.info("InpaintingService: Using OpenCV inpainting (fallback)...")
                if ADVANCED_INPAINTING_AVAILABLE:
                    cleaned_path = opencv_inpaint(image_path, mask_path, output_path)
                else:
                    cleaned_path = await self._inpaint_with_opencv(image_path, mask_path, output_path)
                inpaint_method_used = "opencv"
            except Exception as e:
                logger.error(f"InpaintingService: All inpainting methods failed: {e}")
                return {
                    "cleaned_image_path": image_path,
                    "removed_labels": [],
                    "text_regions_found": len(text_regions),
                    "error": str(e)
                }

        return {
            "cleaned_image_path": cleaned_path,
            "removed_labels": [r["text"] for r in text_regions],
            "text_regions_found": len(text_regions),
            "inpaint_method": inpaint_method_used,
            "mask_path": mask_path
        }


# Singleton instance
_inpainting_service: Optional[InpaintingService] = None


def get_inpainting_service() -> InpaintingService:
    """Get or create the inpainting service singleton."""
    global _inpainting_service
    if _inpainting_service is None:
        _inpainting_service = InpaintingService()
    return _inpainting_service
