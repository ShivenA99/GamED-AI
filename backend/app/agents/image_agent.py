"""
Image Agent for Agentic Sequential Pipeline

Dedicated agent for the image acquisition pipeline:
1. Retrieves diagram images from web search
2. Generates images if retrieval fails
3. Detects zones/regions for labeling

This agent was split from the router to focus on image operations,
keeping the tool count per agent within safe limits (research shows
5-10 tools maximum for quality preservation).

Tools available:
- retrieve_diagram_image: Search for educational diagram images
- generate_diagram_image: Generate diagram using DALL-E/etc
- detect_zones: Detect labelable regions using vision models
"""

from typing import Dict, Any, Optional, List

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.image_agent")


async def image_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Image Agent - Handles diagram image acquisition and zone detection.

    This agent performs:
    1. Image retrieval from web search
    2. Image generation if retrieval fails
    3. Zone detection for label placement

    Inputs: question_text, pedagogical_context, domain_knowledge, diagram_labels
    Outputs: diagram_image_url, diagram_image, diagram_zones
    """
    logger.info("ImageAgent: Starting image acquisition phase")

    question_text = state.get("question_text", "")
    pedagogical_context = state.get("pedagogical_context", {})
    domain_knowledge = state.get("domain_knowledge", {})
    diagram_labels = state.get("diagram_labels", [])

    subject = pedagogical_context.get("subject", "general")

    result = {
        "diagram_image_url": None,
        "diagram_image": None,
        "diagram_zones": [],
        "current_agent": "image_agent"
    }

    try:
        # Step 1: Try to retrieve an existing diagram image
        image_retrieved = False
        image_url = None

        # Build search query
        search_query = f"{subject} {question_text} labeled diagram"
        logger.info(f"ImageAgent: Searching for image with query: {search_query[:100]}...")

        # Attempt image retrieval via tool (if wrapped with tools)
        # For standalone execution, use direct API
        try:
            from app.tools.research_tools import retrieve_diagram_image_impl

            search_result = await retrieve_diagram_image_impl(
                query=search_query,
                num_results=5,
                image_type="educational"
            )

            images = search_result.get("images", [])
            if images:
                # Select best image (first one that looks suitable)
                for img in images:
                    url = img.get("url", "")
                    if url and (url.endswith(".png") or url.endswith(".jpg") or
                               url.endswith(".jpeg") or url.endswith(".gif") or
                               "diagram" in url.lower() or "labeled" in url.lower()):
                        image_url = url
                        image_retrieved = True
                        break

                if not image_url and images:
                    # Fallback to first image
                    image_url = images[0].get("url", "")
                    if image_url:
                        image_retrieved = True

            logger.info(f"ImageAgent: Image retrieval {'successful' if image_retrieved else 'failed'}")

        except ImportError:
            logger.warning("ImageAgent: retrieve_diagram_image_impl not available")
        except Exception as e:
            logger.warning(f"ImageAgent: Image retrieval failed: {e}")

        # Step 2: Generate image if retrieval failed
        if not image_retrieved:
            logger.info("ImageAgent: Attempting image generation")

            try:
                from app.tools.vision_tools import generate_diagram_image_impl

                labels_str = ", ".join(diagram_labels[:10])
                generation_prompt = f"Educational {subject} diagram showing: {labels_str}. Clear labels, scientific accuracy."

                gen_result = await generate_diagram_image_impl(
                    prompt=generation_prompt,
                    style="educational",
                    include_labels=True
                )

                if gen_result.get("image_url"):
                    image_url = gen_result["image_url"]
                    image_retrieved = True
                    logger.info("ImageAgent: Image generation successful")
                elif gen_result.get("error"):
                    logger.warning(f"ImageAgent: Image generation failed: {gen_result['error']}")

            except ImportError:
                logger.warning("ImageAgent: generate_diagram_image_impl not available")
            except Exception as e:
                logger.warning(f"ImageAgent: Image generation failed: {e}")

        # Store image info
        if image_url:
            result["diagram_image_url"] = image_url
            result["diagram_image"] = {
                "image_url": image_url,
                "source": "generated" if not image_retrieved else "retrieved",
                "width": 800,
                "height": 600
            }

        # Step 3: Detect zones in the image
        if image_url:
            logger.info("ImageAgent: Starting zone detection")

            try:
                from app.tools.vision_tools import detect_zones_impl

                zone_result = await detect_zones_impl(
                    image_url=image_url,
                    labels=diagram_labels[:15],  # Limit for API
                    detection_method="vision_model"
                )

                zones = zone_result.get("zones", [])
                if zones:
                    result["diagram_zones"] = zones
                    logger.info(f"ImageAgent: Detected {len(zones)} zones")
                else:
                    # Create default zones based on labels
                    result["diagram_zones"] = _create_default_zones(diagram_labels)
                    logger.info(f"ImageAgent: Created {len(result['diagram_zones'])} default zones")

            except ImportError:
                logger.warning("ImageAgent: detect_zones_impl not available, using defaults")
                result["diagram_zones"] = _create_default_zones(diagram_labels)
            except Exception as e:
                logger.warning(f"ImageAgent: Zone detection failed: {e}, using defaults")
                result["diagram_zones"] = _create_default_zones(diagram_labels)

        else:
            # No image - create default zones anyway
            result["diagram_zones"] = _create_default_zones(diagram_labels)
            logger.info("ImageAgent: No image available, created default zones")

        # Track metrics
        if ctx:
            ctx.set_custom_metric("image_retrieved", image_retrieved)
            ctx.set_custom_metric("zones_detected", len(result["diagram_zones"]))

        return result

    except Exception as e:
        logger.error(f"ImageAgent: Failed: {e}", exc_info=True)
        result["error_message"] = f"ImageAgent failed: {str(e)}"
        # Still return default zones
        result["diagram_zones"] = _create_default_zones(diagram_labels)
        return result


def _create_default_zones(labels: List[str]) -> List[Dict[str, Any]]:
    """
    Create default zone positions for labels.

    Distributes zones in a grid pattern within the diagram area.
    """
    zones = []
    num_labels = len(labels) if labels else 4

    # Calculate grid dimensions
    cols = min(3, num_labels)
    rows = (num_labels + cols - 1) // cols

    for i, label in enumerate(labels[:15]):  # Limit to 15 zones
        row = i // cols
        col = i % cols

        # Position zones with padding from edges
        x = 20 + (col + 0.5) * (60 / cols)  # 20-80% horizontal
        y = 25 + (row + 0.5) * (50 / rows)  # 25-75% vertical

        zones.append({
            "id": f"zone_{i + 1}",
            "label": label,
            "x": x,
            "y": y,
            "center": [x, y],
            "radius": 5,
            "color": "#3b82f6",
            "confidence": 0.5  # Lower confidence for defaults
        })

    return zones
