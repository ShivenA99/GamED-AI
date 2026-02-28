# =============================================================================
# EXPERIMENTAL: This agent is not in the production pipeline.
#   - Designed to work with combined_label_detector.py
#   - Production uses image_label_remover.py instead
#
# Kept for experimentation. Not included in the production pipeline graph.
# See DEPRECATED.md for details.
# =============================================================================

"""
Smart Inpainter Agent (EXPERIMENTAL)

Inpaints detected annotations using the best available method:
1. LaMa (via IOPaint) - Best quality/speed balance
2. Stable Diffusion - Highest quality (slow)
3. OpenCV - Fast fallback (lower quality)

The agent automatically selects the method based on availability and
configuration, with graceful fallback if the preferred method fails.

Inputs:
    diagram_image: Dict with 'local_path' to the original image
    detection_mask_path: Path to the binary mask from combined_label_detector

Outputs:
    cleaned_image_path: Path to the inpainted image
    inpainting_method: Method used ("lama", "stable_diffusion", or "opencv")
"""

from app.utils.logging_config import get_logger
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.lama_inpainting_service import (
    get_lama_service,
    get_sd_service,
    opencv_inpaint,
    get_inpainting_method
)

logger = get_logger("gamed_ai.agents.smart_inpainter")


async def smart_inpainter(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Inpaint detected annotations using the best available method.

    Method selection:
    - INPAINTING_METHOD=lama: Use LaMa (requires IOPaint running)
    - INPAINTING_METHOD=stable_diffusion: Use SD (slow but best quality)
    - INPAINTING_METHOD=opencv: Use OpenCV (fast but lower quality)

    Fallback chain: LaMa -> OpenCV if LaMa fails.
    """
    logger.info("=== SMART INPAINTER STARTING ===")
    start_time = time.time()

    # Skip if not INTERACTIVE_DIAGRAM template
    template_type = state.get("template_selection", {}).get("template_type", "")
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"Skipping inpainting: template_type={template_type}")
        return {
            "current_agent": "smart_inpainter",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    # Get image path
    diagram_image = state.get("diagram_image", {}) or {}
    image_path = diagram_image.get("local_path")

    if not image_path or not Path(image_path).exists():
        logger.error(f"No image available for inpainting: {image_path}")
        return {
            "cleaned_image_path": None,
            "inpainting_error": "No image available",
            "current_agent": "smart_inpainter",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    # Get mask path
    mask_path = state.get("detection_mask_path")

    if not mask_path or not Path(mask_path).exists():
        # No mask means nothing to inpaint - use original image
        logger.info("No detection mask - using original image")
        return {
            "cleaned_image_path": image_path,
            "inpainting_method": "none",
            "inpainting_note": "No annotations detected",
            "current_agent": "smart_inpainter",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    logger.info(f"Inpainting image: {image_path}")
    logger.info(f"Using mask: {mask_path}")

    # Determine output path
    image_dir = Path(image_path).parent
    output_dir = image_dir / "cleaned"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / f"{Path(image_path).stem}_cleaned.png")

    # Get configured method
    method = get_inpainting_method()
    logger.info(f"Configured inpainting method: {method}")

    fallback_used = False
    fallback_reason = None
    actual_method = method

    # Try inpainting with the configured method
    try:
        if method == "lama":
            cleaned_path = await _inpaint_with_lama(image_path, mask_path, output_path)
        elif method == "stable_diffusion":
            cleaned_path = await _inpaint_with_sd(image_path, mask_path, output_path)
        else:
            # OpenCV fallback
            cleaned_path = _inpaint_with_opencv(image_path, mask_path, output_path)
            actual_method = "opencv"

    except Exception as e:
        logger.warning(f"{method} inpainting failed: {e}")

        # Fallback to OpenCV
        if method != "opencv":
            logger.info("Falling back to OpenCV inpainting")
            try:
                cleaned_path = _inpaint_with_opencv(image_path, mask_path, output_path)
                actual_method = "opencv"
                fallback_used = True
                fallback_reason = f"{method} failed: {e}"
            except Exception as e2:
                logger.error(f"OpenCV fallback also failed: {e2}")
                return {
                    "cleaned_image_path": image_path,
                    "inpainting_error": f"All methods failed: {e}; {e2}",
                    "inpainting_method": "failed",
                    "_used_fallback": True,
                    "_fallback_reason": f"All inpainting methods failed",
                    "current_agent": "smart_inpainter",
                    "last_updated_at": datetime.utcnow().isoformat()
                }
        else:
            return {
                "cleaned_image_path": image_path,
                "inpainting_error": str(e),
                "inpainting_method": "failed",
                "current_agent": "smart_inpainter",
                "last_updated_at": datetime.utcnow().isoformat()
            }

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    logger.info(f"Inpainting complete in {latency_ms}ms using {actual_method}")
    logger.info(f"Cleaned image saved to: {cleaned_path}")

    # Track metrics if context available
    if ctx:
        ctx.set_llm_metrics(
            model=actual_method,
            latency_ms=latency_ms
        )
        if fallback_used:
            ctx.set_fallback_used(fallback_reason)

    result = {
        "cleaned_image_path": cleaned_path,
        "inpainting_method": actual_method,
        "current_agent": "smart_inpainter",
        "last_updated_at": datetime.utcnow().isoformat()
    }

    if fallback_used:
        result["_used_fallback"] = True
        result["_fallback_reason"] = fallback_reason

    return result


async def _inpaint_with_lama(
    image_path: str,
    mask_path: str,
    output_path: str
) -> str:
    """Inpaint using LaMa via IOPaint."""
    lama_service = get_lama_service()

    if not await lama_service.is_available():
        raise RuntimeError(
            "IOPaint/LaMa not available. Start with: "
            "iopaint start --model=lama --device=mps --port=8080"
        )

    logger.info("Using LaMa inpainting via IOPaint")
    return await lama_service.inpaint(image_path, mask_path, output_path)


async def _inpaint_with_sd(
    image_path: str,
    mask_path: str,
    output_path: str
) -> str:
    """Inpaint using Stable Diffusion."""
    sd_service = get_sd_service()

    if not await sd_service.is_available():
        raise RuntimeError(
            "Stable Diffusion not available. Install with: "
            "pip install diffusers transformers accelerate torch"
        )

    logger.info("Using Stable Diffusion inpainting")

    # Use a prompt that encourages clean diagram background
    prompt = os.getenv(
        "SD_INPAINT_PROMPT",
        "clean diagram background, seamless texture, educational illustration style"
    )

    return await sd_service.inpaint(image_path, mask_path, output_path, prompt=prompt)


def _inpaint_with_opencv(
    image_path: str,
    mask_path: str,
    output_path: str
) -> str:
    """Inpaint using OpenCV (fast fallback)."""
    logger.info("Using OpenCV inpainting (fast fallback)")

    method = os.getenv("OPENCV_INPAINT_METHOD", "NS")
    radius = int(os.getenv("OPENCV_INPAINT_RADIUS", "5"))

    return opencv_inpaint(image_path, mask_path, output_path, method=method, radius=radius)
