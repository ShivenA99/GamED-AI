"""
SAM3 Prompt Generator Agent

Uses VLM to analyze the image and canonical labels, then generates
precise SAM3 text prompts for each label to enable accurate segmentation.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.services.vlm_service import label_zone_with_vlm, VLMError
from app.utils.logging_config import get_logger
from app.agents.instrumentation import InstrumentedAgentContext

logger = get_logger("gamed_ai.agents.sam3_prompt_generator")


async def sam3_prompt_generator_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    """
    Generate SAM3 text prompts for each canonical label using VLM.

    This agent analyzes the image and creates precise prompts that SAM3
    can use to segment each label accurately.
    """
    logger.info("=== SAM3 PROMPT GENERATOR STARTING ===")  # MUST appear in logs

    try:
        question_id = state.get("question_id", "unknown")
        template_type = state.get("template_selection", {}).get("template_type", "")

        logger.info("Starting SAM3 prompt generation",
                    question_id=question_id,
                    template_type=template_type,
                    agent_name="sam3_prompt_generator")

        if template_type != "INTERACTIVE_DIAGRAM":
            logger.info(f"Skipping SAM3 prompt generation: template_type={template_type}")
            return {**state, "current_agent": "sam3_prompt_generator"}

        # Get image path (prefer cleaned, fallback to original)
        cleaned_image_path = state.get("cleaned_image_path")
        diagram_image = state.get("diagram_image", {}) or {}
        image_url = diagram_image.get("image_url")

        if not cleaned_image_path and not image_url:
            logger.error("No image available for SAM3 prompt generation")
            return {
                **state,
                "current_agent": "sam3_prompt_generator",
                "current_validation_errors": ["No image available for SAM3 prompt generation"],
            }

        # Get canonical labels
        domain_knowledge = state.get("domain_knowledge", {}) or {}
        canonical_labels = domain_knowledge.get("canonical_labels", []) or []
        game_plan = state.get("game_plan", {}) or {}
        required_labels = game_plan.get("required_labels") or canonical_labels

        if not required_labels:
            logger.error("No canonical labels available for SAM3 prompt generation")
            return {
                **state,
                "current_agent": "sam3_prompt_generator",
                "current_validation_errors": ["No canonical labels available"],
            }

        logger.info("Generating SAM3 prompts",
                    labels_count=len(required_labels),
                    labels=required_labels[:10],
                    has_cleaned_image=bool(cleaned_image_path))

        # Load image bytes with proper validation
        try:
            if cleaned_image_path and Path(cleaned_image_path).exists():
                image_bytes = Path(cleaned_image_path).read_bytes()
                image_path_for_log = cleaned_image_path
                logger.info(f"Using cleaned image: {cleaned_image_path}")
            elif image_url:
                # Download from URL
                import httpx
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(image_url)
                    response.raise_for_status()
                    image_bytes = response.content
                image_path_for_log = image_url[:80]
                logger.info(f"Downloaded image from URL: {image_url[:60]}...")
            else:
                # CRITICAL FIX: Handle case where neither exists
                logger.error("No image available - no cleaned_image_path or image_url")
                return {
                    **state,
                    "sam3_prompts": {label: label for label in required_labels},
                    "current_agent": "sam3_prompt_generator",
                    "current_validation_errors": ["No image available for SAM3 prompts"],
                }

            logger.info("Image loaded for VLM analysis", image_path=image_path_for_log)
        except Exception as e:
            logger.error(f"SAM3 prompt generator image load FAILED: {e}", exc_info=True)
            # Return fallback prompts instead of crashing
            return {
                **state,
                "sam3_prompts": {label: label for label in required_labels},
                "current_agent": "sam3_prompt_generator",
                "current_validation_errors": [f"Image load failed: {e}"],
            }

        # Generate SAM3 prompts for each label using VLM
        sam3_prompts = {}
        vlm_success_count = 0
        vlm_failure_count = 0
        vlm_model = os.getenv("VLM_MODEL", "llava:latest")
        vlm_start_time = time.time()

        prompt_generation_prompt = """You are analyzing a diagram image to generate precise SAM3 (Segment Anything Model 3) text prompts.

SAM3 works best with SHORT NOUN PHRASES. Research shows simple, clear descriptions work better than long descriptions.

For each label provided, create a concise text prompt that SAM3 can use to accurately segment that specific part.

Guidelines (based on SAM3 best practices):
- Use SHORT noun phrases (1-3 words ideal, max 5 words)
- Examples that work well: "petal", "car", "person", "yellow school bus", "striped cat"
- Be specific but concise (e.g., "petal" or "flower petal" not "the petal of a flower")
- Avoid articles ("the", "a") unless necessary for clarity
- Focus on the object name itself
- If the label is already clear, use it as-is or with minimal modification

For the label "{label}", generate a SAM3 text prompt. Reply with ONLY the prompt text, nothing else. Keep it SHORT (1-3 words preferred)."""

        for label in required_labels:
            try:
                label_prompt = prompt_generation_prompt.format(label=label)

                response = await label_zone_with_vlm(
                    image_bytes=image_bytes,
                    candidate_labels=[label],  # Not used for prompt generation, but required
                    prompt=label_prompt,
                )

                # Clean response - extract just the prompt
                prompt_text = response.strip()
                # Remove quotes if present
                if prompt_text.startswith('"') and prompt_text.endswith('"'):
                    prompt_text = prompt_text[1:-1]
                elif prompt_text.startswith("'") and prompt_text.endswith("'"):
                    prompt_text = prompt_text[1:-1]

                sam3_prompts[label] = prompt_text
                vlm_success_count += 1

                logger.info("Generated SAM3 prompt for label",
                           label=label,
                           prompt=prompt_text[:50])

            except VLMError as e:
                vlm_failure_count += 1
                # Fallback: use label as prompt
                fallback_prompt = f"the {label}"
                sam3_prompts[label] = fallback_prompt

                logger.warning("VLM failed for label, using fallback prompt",
                              label=label,
                              error=str(e)[:100],
                              fallback_prompt=fallback_prompt)
            except Exception as e:
                vlm_failure_count += 1
                fallback_prompt = f"the {label}"
                sam3_prompts[label] = fallback_prompt

                logger.error("Unexpected error generating prompt for label",
                            label=label,
                            exc_info=True,
                            error=str(e),
                            fallback_prompt=fallback_prompt)

        # Calculate VLM latency and report metrics
        vlm_latency_ms = int((time.time() - vlm_start_time) * 1000)

        logger.info("SAM3 prompt generation completed",
                   total_labels=len(required_labels),
                   vlm_success_count=vlm_success_count,
                   vlm_failure_count=vlm_failure_count,
                   prompts_generated=len(sam3_prompts),
                   vlm_model=vlm_model,
                   vlm_latency_ms=vlm_latency_ms)

        # Report VLM metrics to instrumentation
        if ctx:
            ctx.set_llm_metrics(
                model=vlm_model,
                latency_ms=vlm_latency_ms
            )

        return {
            **state,
            "sam3_prompts": sam3_prompts,
            "current_agent": "sam3_prompt_generator",
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"SAM3 prompt generator CRASHED: {e}", exc_info=True)
        # Return fallback prompts instead of crashing
        required_labels = state.get("game_plan", {}).get("required_labels") or \
                         state.get("domain_knowledge", {}).get("canonical_labels", [])
        return {
            **state,
            "sam3_prompts": {label: label for label in (required_labels or [])},
            "current_agent": "sam3_prompt_generator",
            "current_validation_errors": [f"SAM3 prompt generator crashed: {e}"],
        }
