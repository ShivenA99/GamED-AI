"""
Image Label Remover Agent

Removes text labels from diagram images using InpaintingService.
This runs after image retrieval and before segmentation to ensure
clean images for better zone detection.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.inpainting_service import get_inpainting_service
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.image_label_remover")


async def _download_image(image_url: str, output_path: Path) -> None:
    """Download image from URL to local path"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        output_path.write_bytes(response.content)


async def image_label_remover_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    """
    Remove text labels from diagram image using InpaintingService.
    
    This agent:
    1. Downloads the image if not already downloaded
    2. Uses InpaintingService to detect and remove text labels
    3. Updates state with cleaned image path and removed labels
    """
    # Skip if not INTERACTIVE_DIAGRAM
    template_type = state.get("template_selection", {}).get("template_type", "")
    if template_type != "INTERACTIVE_DIAGRAM":
        return {
            **state,
            "current_agent": "image_label_remover",
            "last_updated_at": datetime.utcnow().isoformat()
        }
    
    # Get image info from diagram_image
    image_info = state.get("diagram_image")
    if not image_info or not image_info.get("image_url"):
        logger.warning("ImageLabelRemover: No diagram image available, skipping")
        return {
            **state,
            "current_agent": "image_label_remover",
            "last_updated_at": datetime.utcnow().isoformat()
        }
    
    question_id = state.get("question_id", "unknown")
    output_dir = Path(__file__).parent.parent.parent / "pipeline_outputs" / "assets" / question_id
    image_path = output_dir / "diagram.jpg"
    
    # Download image if not already present
    if not image_path.exists():
        try:
            logger.info(f"ImageLabelRemover: Downloading image from {image_info['image_url']}")
            await _download_image(image_info["image_url"], image_path)
        except Exception as e:
            logger.error(f"ImageLabelRemover: Failed to download image: {e}")
            return {
                **state,
                "current_agent": "image_label_remover",
                "current_validation_errors": [f"Image download failed: {e}"],
                "last_updated_at": datetime.utcnow().isoformat()
            }
    
    # Use InpaintingService to clean the image
    try:
        logger.info("Starting image cleaning", 
                   image_path=str(image_path),
                   agent_name="image_label_remover")
        service = get_inpainting_service()
        
        cleaned_output_dir = output_dir / "cleaned"
        logger.info("Calling inpainting service", 
                   input_image=str(image_path),
                   output_dir=str(cleaned_output_dir))
        
        result = await service.clean_diagram(
            str(image_path),
            str(cleaned_output_dir)
        )
        
        cleaned_image_path = result["cleaned_image_path"]
        removed_labels = result.get("removed_labels", [])
        text_regions_found = result.get("text_regions_found", 0)
        has_error = "error" in result
        
        # Check if fallback was used (cleaned path is same as original)
        is_fallback = cleaned_image_path == str(image_path) and text_regions_found > 0
        
        if has_error or is_fallback:
            logger.warning(
                "Image cleaning used fallback or had errors",
                fallback_used=True,
                primary_method="inpainting",
                fallback_method="original_image",
                reason=result.get("error", "cleaned_path_same_as_original"),
                text_regions_found=text_regions_found,
                removed_labels_count=len(removed_labels)
            )
        else:
            logger.info(
                "Image cleaning completed successfully",
                fallback_used=False,
                method="inpainting",
                cleaned_image_path=cleaned_image_path,
                text_regions_found=text_regions_found,
                removed_labels=removed_labels,
                removed_labels_count=len(removed_labels)
            )
        
        # Update diagram_segments to use cleaned image path
        # This ensures segmenter uses the cleaned image
        diagram_segments = state.get("diagram_segments", {})
        if not diagram_segments:
            diagram_segments = {
                "image_path": cleaned_image_path,
                "segments": [],
                "method": "pending",
                "generated_at": datetime.utcnow().isoformat()
            }
        else:
            diagram_segments = {
                **diagram_segments,
                "image_path": cleaned_image_path
            }
        
        return {
            **state,
            "cleaned_image_path": cleaned_image_path,
            "removed_labels": removed_labels,
            "diagram_segments": diagram_segments,
            "current_agent": "image_label_remover",
            "last_updated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Check if it's an EasyOCR import error
        is_easyocr_error = "EasyOCR" in error_msg or "easyocr" in error_msg.lower()
        
        if is_easyocr_error:
            logger.warning(
                "Image cleaning failed: EasyOCR not available, using fallback",
                fallback_used=True,
                primary_method="inpainting_with_easyocr",
                fallback_method="original_image",
                reason="EasyOCR not installed",
                error_type=error_type,
                error_message=error_msg,
                action_required="pip install easyocr"
            )
        else:
            logger.warning(
                "Image cleaning failed, using fallback",
                fallback_used=True,
                primary_method="inpainting",
                fallback_method="original_image",
                reason=error_msg,
                error_type=error_type
            )
        
        # If inpainting fails, continue with original image
        return {
            **state,
            "cleaned_image_path": str(image_path),  # Use original as fallback
            "removed_labels": [],
            "current_agent": "image_label_remover",
            "current_validation_errors": [f"Image cleaning failed: {e}"],
            "last_updated_at": datetime.utcnow().isoformat()
        }
