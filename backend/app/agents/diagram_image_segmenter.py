"""
Diagram Image Segmenter Agent
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.segmentation import sam_segment_image
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.diagram_image_segmenter")


async def _download_image(image_url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        output_path.write_bytes(response.content)


async def diagram_image_segmenter_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")
    
    logger.info("Starting image segmentation", 
                question_id=question_id,
                template_type=template_type,
                agent_name="diagram_image_segmenter")
    
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"Skipping segmentation: template_type={template_type}")
        return {**state, "current_agent": "diagram_image_segmenter"}

    # Prefer cleaned image path if available (from image_label_remover)
    cleaned_image_path = state.get("cleaned_image_path")
    if cleaned_image_path and Path(cleaned_image_path).exists():
        logger.info("Using cleaned image for segmentation", 
                   cleaned_image_path=cleaned_image_path)
        image_path = Path(cleaned_image_path)
    else:
        # Fallback to downloading from diagram_image
        logger.info("No cleaned image found, downloading original image")
        image_info = state.get("diagram_image")
        if not image_info or not image_info.get("image_url"):
            logger.error("No diagram image available for segmentation")
            return {
                **state,
                "current_agent": "diagram_image_segmenter",
                "current_validation_errors": ["No diagram image available for segmentation"],
            }

        question_id = state.get("question_id", "unknown")
        output_dir = Path(__file__).parent.parent.parent / "pipeline_outputs" / "assets" / question_id
        image_path = output_dir / "diagram.jpg"

        try:
            logger.info("Downloading image for segmentation", 
                       image_url=image_info["image_url"][:80],
                       output_path=str(image_path))
            await _download_image(image_info["image_url"], image_path)
            logger.info("Image downloaded successfully", path=str(image_path))
        except Exception as e:
            logger.error("Image download failed", 
                        exc_info=True,
                        error_type=type(e).__name__,
                        image_url=image_info["image_url"][:80])
            return {
                **state,
                "current_agent": "diagram_image_segmenter",
                "current_validation_errors": [f"Image download failed: {e}"],
            }

    domain_knowledge = state.get("domain_knowledge", {}) or {}
    label_count = len(domain_knowledge.get("canonical_labels", []) or [])

    # Get SAM3 prompts from prompt generator agent
    sam3_prompts = state.get("sam3_prompts")
    game_plan = state.get("game_plan", {}) or {}
    required_labels = game_plan.get("required_labels") or domain_knowledge.get("canonical_labels", [])

    # CRITICAL: Check if SAM3 prompts are available
    if not sam3_prompts:
        logger.error("SAM3 prompts missing! sam3_prompt_generator may have been skipped.")
        logger.error("Check logs for '=== SAM3 PROMPT GENERATOR STARTING ===' message")
        # Fail instead of using grid fallback
        return {
            **state,
            "current_agent": "diagram_image_segmenter",
            "current_validation_errors": [
                "SAM3 prompts not generated - check sam3_prompt_generator logs. "
                "Segmentation cannot proceed without SAM3 prompts."
            ],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    logger.info("Starting segmentation",
               image_path=str(image_path),
               expected_labels=label_count,
               using_cleaned_image=cleaned_image_path is not None,
               has_sam3_prompts=bool(sam3_prompts),
               prompts_count=len(sam3_prompts) if sam3_prompts else 0)

    logger.info("Using SAM3 prompts for segmentation",
               prompts_count=len(sam3_prompts),
               labels=list(sam3_prompts.keys())[:5])

    try:
        logger.info("Attempting SAM3 segmentation (SAM3 ONLY - no SAM2/SAM v1 fallback)",
                   image_path=str(image_path))
        segments = sam_segment_image(
            str(image_path),
            text_prompts=sam3_prompts,
            labels=required_labels if isinstance(required_labels, list) else None
        )

        # SAM3 ONLY - always SAM3 when successful (no SAM2/SAM v1 fallbacks)
        segmentation_method = "sam3"

        logger.info(
            "SAM3 segmentation successful",
            fallback_used=False,
            method="sam3",
            segments_count=len(segments),
            image_path=str(image_path),
            prompts_used=list(sam3_prompts.keys())
        )
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)

        # SAM3 failed - fail the stage instead of using grid fallback
        logger.error(
            "SAM3 segmentation failed - no fallback available",
            error_type=error_type,
            error_message=error_msg,
            action_required="Check MLX SAM3 installation and USE_SAM3_MLX env var"
        )
        return {
            **state,
            "current_agent": "diagram_image_segmenter",
            "current_validation_errors": [
                f"SAM3 segmentation failed: {error_msg}. "
                f"Check MLX SAM3 installation and USE_SAM3_MLX environment variable."
            ],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    # Ensure image_path in segments uses cleaned image if available
    final_image_path = cleaned_image_path if cleaned_image_path else str(image_path)
    
    logger.info("Segmentation completed", 
               segments_count=len(segments),
               method=segmentation_method,
               final_image_path=final_image_path)

    return {
        **state,
        "diagram_segments": {
            "image_path": final_image_path,
            "segments": segments,
            "method": segmentation_method,
            "generated_at": datetime.utcnow().isoformat(),
        },
        "current_agent": "diagram_image_segmenter",
        "last_updated_at": datetime.utcnow().isoformat(),
    }
