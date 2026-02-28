#!/usr/bin/env python3
"""
Test script for guided diffusion inpainting to clean diagram images.

This script tests different approaches for removing text labels and leader lines
from educational diagrams using diffusion models.

Approaches tested:
1. SD 1.5 Inpainting with EasyOCR-generated masks
2. InstructPix2Pix for instruction-guided editing
3. PowerPaint v2 (if available) for context-aware removal

Usage:
    PYTHONPATH=. python scripts/test_guided_inpainting.py --image path/to/diagram.jpg
    PYTHONPATH=. python scripts/test_guided_inpainting.py --test-sample
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path("pipeline_outputs/inpainting_tests")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def check_mps_availability() -> bool:
    """Check if MPS (Metal Performance Shaders) is available."""
    try:
        import torch
        if torch.backends.mps.is_available():
            logger.info("✓ MPS (Metal) backend available")
            return True
        else:
            logger.warning("✗ MPS not available, will use CPU")
            return False
    except ImportError:
        logger.error("PyTorch not installed")
        return False


def detect_text_regions_easyocr(image_path: str) -> Tuple[np.ndarray, list]:
    """
    Detect text regions using EasyOCR.

    Returns:
        Tuple of (mask image, list of detected text boxes)
    """
    import easyocr

    logger.info("Detecting text regions with EasyOCR...")

    # Initialize reader
    reader = easyocr.Reader(['en'], gpu=False)  # Use CPU for detection

    # Read image
    img = cv2.imread(image_path)
    h, w = img.shape[:2]

    # Detect text
    results = reader.readtext(image_path)

    # Create mask
    mask = np.zeros((h, w), dtype=np.uint8)

    boxes = []
    for (bbox, text, conf) in results:
        if conf > 0.3:  # Confidence threshold
            # bbox is list of 4 points
            pts = np.array(bbox, dtype=np.int32)

            # Expand bbox slightly to cover leader lines
            center = pts.mean(axis=0)
            pts_expanded = center + (pts - center) * 1.3
            pts_expanded = pts_expanded.astype(np.int32)

            cv2.fillPoly(mask, [pts_expanded], 255)
            boxes.append({
                'bbox': bbox,
                'text': text,
                'confidence': conf
            })

    logger.info(f"Detected {len(boxes)} text regions")
    return mask, boxes


def detect_leader_lines(image_path: str, text_boxes: list) -> np.ndarray:
    """
    Detect leader lines connecting text labels to diagram structures.
    Uses Hough Line Transform with filtering based on text box proximity.

    Returns:
        Mask of detected leader lines
    """
    logger.info("Detecting leader lines...")

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Detect lines
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)

    mask = np.zeros((h, w), dtype=np.uint8)

    if lines is None:
        return mask

    # Get text box centers
    text_centers = []
    for box in text_boxes:
        pts = np.array(box['bbox'])
        center = pts.mean(axis=0)
        text_centers.append(center)

    # Filter lines that are near text boxes (likely leader lines)
    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Check if line endpoint is near a text box
        for center in text_centers:
            dist1 = np.sqrt((x1 - center[0])**2 + (y1 - center[1])**2)
            dist2 = np.sqrt((x2 - center[0])**2 + (y2 - center[1])**2)

            # If either endpoint is within 100px of a text box, it's likely a leader line
            if min(dist1, dist2) < 100:
                # Draw thick line on mask
                cv2.line(mask, (x1, y1), (x2, y2), 255, thickness=8)
                break

    logger.info(f"Detected leader lines in mask")
    return mask


def create_combined_mask(text_mask: np.ndarray, line_mask: np.ndarray) -> np.ndarray:
    """Combine text and line masks."""
    combined = cv2.bitwise_or(text_mask, line_mask)

    # Dilate to ensure coverage
    kernel = np.ones((5, 5), np.uint8)
    combined = cv2.dilate(combined, kernel, iterations=2)

    return combined


def test_sd_inpainting(image_path: str, mask: np.ndarray) -> Optional[Image.Image]:
    """
    Test Stable Diffusion 1.5 inpainting.
    """
    logger.info("Testing SD 1.5 Inpainting...")

    try:
        import torch
        from diffusers import StableDiffusionInpaintPipeline

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        dtype = torch.float16 if device == "mps" else torch.float32

        logger.info(f"Loading SD inpainting pipeline on {device}...")

        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            "runwayml/stable-diffusion-inpainting",
            torch_dtype=dtype,
            safety_checker=None,
        ).to(device)

        # Enable memory optimizations
        pipe.enable_attention_slicing()

        # Load images
        init_image = Image.open(image_path).convert("RGB")
        mask_image = Image.fromarray(mask).convert("L")

        # Resize if too large
        max_size = 768
        if max(init_image.size) > max_size:
            ratio = max_size / max(init_image.size)
            new_size = (int(init_image.width * ratio), int(init_image.height * ratio))
            # Round to multiple of 8
            new_size = (new_size[0] // 8 * 8, new_size[1] // 8 * 8)
            init_image = init_image.resize(new_size, Image.Resampling.LANCZOS)
            mask_image = mask_image.resize(new_size, Image.Resampling.NEAREST)

        logger.info(f"Running inpainting at size {init_image.size}...")

        # Run inpainting - prompt for clean diagram
        result = pipe(
            prompt="clean educational diagram, botanical illustration, no text, no labels, seamless",
            negative_prompt="text, words, letters, labels, annotations, lines, arrows",
            image=init_image,
            mask_image=mask_image,
            num_inference_steps=30,
            guidance_scale=7.5,
        ).images[0]

        logger.info("✓ SD Inpainting complete")
        return result

    except Exception as e:
        logger.error(f"SD Inpainting failed: {e}")
        return None


def test_instructpix2pix(image_path: str) -> Optional[Image.Image]:
    """
    Test InstructPix2Pix for instruction-guided text removal.
    No mask needed - uses natural language instructions.
    """
    logger.info("Testing InstructPix2Pix...")

    try:
        import torch
        from diffusers import StableDiffusionInstructPix2PixPipeline

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        dtype = torch.float16 if device == "mps" else torch.float32

        logger.info(f"Loading InstructPix2Pix pipeline on {device}...")

        pipe = StableDiffusionInstructPix2PixPipeline.from_pretrained(
            "timbrooks/instruct-pix2pix",
            torch_dtype=dtype,
            safety_checker=None,
        ).to(device)

        pipe.enable_attention_slicing()

        # Load image
        image = Image.open(image_path).convert("RGB")

        # Resize if needed
        max_size = 768
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            new_size = (new_size[0] // 8 * 8, new_size[1] // 8 * 8)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        logger.info(f"Running InstructPix2Pix at size {image.size}...")

        # Instruction to remove text
        result = pipe(
            prompt="Remove all text labels, annotations, and leader lines from this diagram. Keep only the main diagram structure.",
            image=image,
            num_inference_steps=30,
            image_guidance_scale=1.5,  # How much to preserve original
            guidance_scale=7.5,  # How much to follow instruction
        ).images[0]

        logger.info("✓ InstructPix2Pix complete")
        return result

    except Exception as e:
        logger.error(f"InstructPix2Pix failed: {e}")
        return None


def test_powerpaint(image_path: str, mask: np.ndarray) -> Optional[Image.Image]:
    """
    Test PowerPaint v2 for context-aware object removal.
    PowerPaint has a dedicated removal mode.
    """
    logger.info("Testing PowerPaint v2...")

    try:
        import torch
        from diffusers import StableDiffusionInpaintPipeline

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        dtype = torch.float16 if device == "mps" else torch.float32

        # Check if PowerPaint is available
        model_id = "Sanster/PowerPaint-V1-stable-diffusion-inpainting"

        logger.info(f"Loading PowerPaint pipeline on {device}...")

        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            safety_checker=None,
        ).to(device)

        pipe.enable_attention_slicing()

        # Load images
        init_image = Image.open(image_path).convert("RGB")
        mask_image = Image.fromarray(mask).convert("L")

        # Resize if needed
        max_size = 768
        if max(init_image.size) > max_size:
            ratio = max_size / max(init_image.size)
            new_size = (int(init_image.width * ratio), int(init_image.height * ratio))
            new_size = (new_size[0] // 8 * 8, new_size[1] // 8 * 8)
            init_image = init_image.resize(new_size, Image.Resampling.LANCZOS)
            mask_image = mask_image.resize(new_size, Image.Resampling.NEAREST)

        logger.info(f"Running PowerPaint removal at size {init_image.size}...")

        # PowerPaint removal mode - empty prompt triggers context-aware fill
        result = pipe(
            prompt="",  # Empty for removal mode
            negative_prompt="text, words, labels, annotations",
            image=init_image,
            mask_image=mask_image,
            num_inference_steps=30,
            guidance_scale=7.5,
        ).images[0]

        logger.info("✓ PowerPaint complete")
        return result

    except Exception as e:
        logger.error(f"PowerPaint failed: {e}")
        return None


def download_test_image() -> str:
    """Download a sample flower diagram for testing."""
    import urllib.request

    # Use a simple test image URL (flower diagram with labels)
    test_image_path = OUTPUT_DIR / "test_flower_diagram.jpg"

    if test_image_path.exists():
        logger.info(f"Using existing test image: {test_image_path}")
        return str(test_image_path)

    # Check if there's an existing diagram in pipeline outputs
    existing = Path("pipeline_outputs/assets/test_run/diagram.jpg")
    if existing.exists():
        logger.info(f"Using existing pipeline diagram: {existing}")
        return str(existing)

    logger.info("No test image found. Please provide --image path")
    return None


def main():
    parser = argparse.ArgumentParser(description="Test guided diffusion inpainting")
    parser.add_argument("--image", type=str, help="Path to diagram image")
    parser.add_argument("--test-sample", action="store_true", help="Use sample test image")
    parser.add_argument("--method", choices=["all", "sd", "pix2pix", "powerpaint"], default="all")
    parser.add_argument("--skip-detection", action="store_true", help="Skip text detection, use existing mask")
    args = parser.parse_args()

    # Check MPS
    check_mps_availability()

    # Get image path
    if args.test_sample or not args.image:
        image_path = download_test_image()
        if not image_path:
            # Try to find any diagram in the assets folder
            for f in Path("pipeline_outputs").rglob("diagram.jpg"):
                image_path = str(f)
                break
            for f in Path("pipeline_outputs").rglob("diagram.png"):
                image_path = str(f)
                break
    else:
        image_path = args.image

    if not image_path or not Path(image_path).exists():
        logger.error(f"Image not found: {image_path}")
        logger.info("Run the pipeline first to generate a test diagram, or provide --image path")
        sys.exit(1)

    logger.info(f"Processing image: {image_path}")

    # Step 1: Detect text and leader lines
    if not args.skip_detection:
        text_mask, text_boxes = detect_text_regions_easyocr(image_path)
        line_mask = detect_leader_lines(image_path, text_boxes)
        combined_mask = create_combined_mask(text_mask, line_mask)

        # Save masks for inspection
        cv2.imwrite(str(OUTPUT_DIR / "mask_text.png"), text_mask)
        cv2.imwrite(str(OUTPUT_DIR / "mask_lines.png"), line_mask)
        cv2.imwrite(str(OUTPUT_DIR / "mask_combined.png"), combined_mask)
        logger.info(f"Saved masks to {OUTPUT_DIR}")
    else:
        # Load existing mask
        mask_path = OUTPUT_DIR / "mask_combined.png"
        if mask_path.exists():
            combined_mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        else:
            logger.error("No existing mask found. Run without --skip-detection first.")
            sys.exit(1)

    # Save original for comparison
    original = Image.open(image_path)
    original.save(OUTPUT_DIR / "original.png")

    results = {}

    # Step 2: Test different inpainting methods
    if args.method in ["all", "sd"]:
        start = time.time()
        result = test_sd_inpainting(image_path, combined_mask)
        if result:
            result.save(OUTPUT_DIR / "result_sd_inpainting.png")
            results["sd_inpainting"] = time.time() - start

    if args.method in ["all", "pix2pix"]:
        start = time.time()
        result = test_instructpix2pix(image_path)
        if result:
            result.save(OUTPUT_DIR / "result_instructpix2pix.png")
            results["instructpix2pix"] = time.time() - start

    if args.method in ["all", "powerpaint"]:
        start = time.time()
        result = test_powerpaint(image_path, combined_mask)
        if result:
            result.save(OUTPUT_DIR / "result_powerpaint.png")
            results["powerpaint"] = time.time() - start

    # Summary
    logger.info("\n" + "="*60)
    logger.info("RESULTS SUMMARY")
    logger.info("="*60)
    for method, duration in results.items():
        logger.info(f"  {method}: {duration:.1f}s")
    logger.info(f"\nOutputs saved to: {OUTPUT_DIR}")
    logger.info("Compare the results visually to determine best method.")


if __name__ == "__main__":
    main()
