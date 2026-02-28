#!/usr/bin/env python3
"""
Test Inpainting Methods

Compare different inpainting methods for removing labels and leader lines:
1. OpenCV NS (Navier-Stokes) - fast, lower quality
2. OpenCV Telea (Fast Marching) - fast, slightly better
3. LaMa (via IOPaint) - balanced quality/speed
4. Stable Diffusion - highest quality, slow

Usage:
    # Start IOPaint first for LaMa:
    iopaint start --model=lama --device=mps --port=8080

    PYTHONPATH=. python scripts/test_inpainting_methods.py \
        --image /path/to/heart_diagram.png \
        --mask /path/to/combined_mask.png \
        --output-dir /tmp/inpaint_tests
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import cv2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_inpainting")


def test_opencv_ns(image_path: str, mask_path: str, output_path: str):
    """Test OpenCV Navier-Stokes inpainting."""
    from app.services.lama_inpainting_service import opencv_inpaint

    logger.info("Testing OpenCV NS inpainting...")
    result = opencv_inpaint(image_path, mask_path, output_path, method="NS", radius=5)
    logger.info(f"Saved to {result}")
    return result


def test_opencv_telea(image_path: str, mask_path: str, output_path: str):
    """Test OpenCV Telea (Fast Marching) inpainting."""
    from app.services.lama_inpainting_service import opencv_inpaint

    logger.info("Testing OpenCV Telea inpainting...")
    result = opencv_inpaint(image_path, mask_path, output_path, method="TELEA", radius=5)
    logger.info(f"Saved to {result}")
    return result


async def test_lama(image_path: str, mask_path: str, output_path: str):
    """Test LaMa inpainting via IOPaint."""
    from app.services.lama_inpainting_service import get_lama_service

    logger.info("Testing LaMa inpainting via IOPaint...")
    service = get_lama_service()

    if not await service.is_available():
        raise RuntimeError(
            "IOPaint not available. Start with: "
            "iopaint start --model=lama --device=mps --port=8080"
        )

    result = await service.inpaint(image_path, mask_path, output_path)
    logger.info(f"Saved to {result}")
    return result


async def test_stable_diffusion(image_path: str, mask_path: str, output_path: str):
    """Test Stable Diffusion inpainting."""
    from app.services.lama_inpainting_service import get_sd_service

    logger.info("Testing Stable Diffusion inpainting...")
    service = get_sd_service()

    if not await service.is_available():
        raise RuntimeError(
            "SD not available. Install with: "
            "pip install diffusers transformers accelerate torch"
        )

    result = await service.inpaint(
        image_path, mask_path, output_path,
        prompt="clean diagram background, seamless texture"
    )
    logger.info(f"Saved to {result}")
    return result


def compute_quality_metrics(original_path: str, inpainted_path: str, mask_path: str):
    """Compute quality metrics for inpainting result."""
    original = cv2.imread(original_path)
    inpainted = cv2.imread(inpainted_path)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

    if original is None or inpainted is None or mask is None:
        return None

    # Ensure same size
    if inpainted.shape != original.shape:
        inpainted = cv2.resize(inpainted, (original.shape[1], original.shape[0]))
    if mask.shape[:2] != original.shape[:2]:
        mask = cv2.resize(mask, (original.shape[1], original.shape[0]))

    # Create inverted mask (non-inpainted regions)
    inv_mask = cv2.bitwise_not(mask)

    # Compute PSNR on non-inpainted regions (should be unchanged)
    mse_unchanged = ((original.astype(float) - inpainted.astype(float)) ** 2)
    mse_unchanged = (mse_unchanged * (inv_mask / 255.0)[:, :, None]).mean()

    # Compute smoothness in inpainted regions (lower variance = smoother)
    inpainted_gray = cv2.cvtColor(inpainted, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(inpainted_gray, cv2.CV_64F)
    masked_laplacian = laplacian * (mask / 255.0)
    smoothness = abs(masked_laplacian).mean()

    return {
        "mse_unchanged": mse_unchanged,
        "smoothness": smoothness
    }


async def main():
    parser = argparse.ArgumentParser(description="Test inpainting methods")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--mask", required=True, help="Path to binary mask")
    parser.add_argument("--output-dir", default="/tmp/inpaint_tests", help="Output directory")
    args = parser.parse_args()

    if not Path(args.image).exists():
        logger.error(f"Image not found: {args.image}")
        sys.exit(1)

    if not Path(args.mask).exists():
        logger.error(f"Mask not found: {args.mask}")
        sys.exit(1)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    logger.info(f"Testing inpainting methods on: {args.image}")
    logger.info(f"Using mask: {args.mask}")
    logger.info(f"Output directory: {output}")

    results = {}

    # Test 1: OpenCV NS
    logger.info("\n=== Test 1: OpenCV NS ===")
    try:
        results["opencv_ns"] = test_opencv_ns(
            args.image, args.mask, str(output / "1_opencv_ns.png")
        )
    except Exception as e:
        logger.error(f"OpenCV NS failed: {e}")

    # Test 2: OpenCV Telea
    logger.info("\n=== Test 2: OpenCV Telea ===")
    try:
        results["opencv_telea"] = test_opencv_telea(
            args.image, args.mask, str(output / "2_opencv_telea.png")
        )
    except Exception as e:
        logger.error(f"OpenCV Telea failed: {e}")

    # Test 3: LaMa
    logger.info("\n=== Test 3: LaMa (IOPaint) ===")
    try:
        results["lama"] = await test_lama(
            args.image, args.mask, str(output / "3_lama.png")
        )
    except Exception as e:
        logger.warning(f"LaMa failed (is IOPaint running?): {e}")

    # Test 4: Stable Diffusion
    logger.info("\n=== Test 4: Stable Diffusion ===")
    try:
        results["stable_diffusion"] = await test_stable_diffusion(
            args.image, args.mask, str(output / "4_stable_diffusion.png")
        )
    except Exception as e:
        logger.warning(f"Stable Diffusion failed: {e}")

    # Compute quality metrics
    logger.info("\n=== Quality Metrics ===")
    for name, path in results.items():
        metrics = compute_quality_metrics(args.image, path, args.mask)
        if metrics:
            logger.info(f"{name}: MSE(unchanged)={metrics['mse_unchanged']:.4f}, "
                        f"Smoothness={metrics['smoothness']:.4f}")

    logger.info(f"\n=== Results saved to {output} ===")
    logger.info("Compare visually:")
    logger.info("  - 1_opencv_ns.png (fast, lower quality)")
    logger.info("  - 2_opencv_telea.png (fast, slightly better)")
    logger.info("  - 3_lama.png (balanced)")
    logger.info("  - 4_stable_diffusion.png (best quality, slow)")


if __name__ == "__main__":
    asyncio.run(main())
