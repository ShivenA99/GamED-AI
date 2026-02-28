"""Algorithm Asset Worker — per-scene visual asset generation.

Runs as a parallel Send worker for scenes that need visual assets.
Uses existing image retrieval and media generation services.
"""

from typing import Any, Optional

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.v4_algorithm.agents.asset_worker")


async def algo_asset_worker(state: dict) -> dict:
    """Generate visual assets for a single scene.

    Receives Send payload: {scene_id, game_type, asset_spec, domain_knowledge}
    Writes to: scene_assets_raw (reducer)
    """
    scene_id = state.get("scene_id", "unknown")
    game_type = state.get("game_type", "")
    asset_spec = state.get("asset_spec") or {}
    dk = state.get("domain_knowledge") or {}

    logger.info(f"Asset worker: scene={scene_id}, type={game_type}")

    try:
        # Try image retrieval first (faster, cheaper)
        image_url = await _try_image_retrieval(asset_spec, dk)

        if not image_url:
            # Fall back to AI image generation
            image_url = await _try_image_generation(asset_spec, dk)

        return {
            "scene_assets_raw": [{
                "scene_id": scene_id,
                "status": "success" if image_url else "skipped",
                "image_url": image_url,
                "asset_type": asset_spec.get("asset_type", "algorithm_illustration"),
            }],
        }

    except Exception as e:
        logger.error(f"Asset worker failed for {scene_id}: {e}")
        return {
            "scene_assets_raw": [{
                "scene_id": scene_id,
                "status": "failed",
                "error": str(e),
            }],
        }


async def _try_image_retrieval(asset_spec: dict, dk: dict) -> Optional[str]:
    """Try to find a suitable image via web search."""
    search_queries = asset_spec.get("search_queries", [])
    if not search_queries:
        algorithm_name = dk.get("algorithm_name", "")
        if algorithm_name:
            search_queries = [
                f"{algorithm_name} algorithm diagram educational",
                f"{algorithm_name} visualization step by step",
            ]

    if not search_queries:
        return None

    try:
        from app.services.image_retrieval import search_diagram_images

        for query in search_queries[:2]:
            results = await search_diagram_images(
                query=query,
                num_results=3,
            )
            if results:
                # Return the first result with a valid URL
                for result in results:
                    url = result.get("url") or result.get("image_url") or result.get("link")
                    if url:
                        logger.info(f"Image retrieval found: {url[:80]}...")
                        return url

    except Exception as e:
        logger.warning(f"Image retrieval failed: {e}")

    return None


async def _try_image_generation(asset_spec: dict, dk: dict) -> Optional[str]:
    """Try AI image generation via Nanobanana/DALL-E."""
    generation_prompt = asset_spec.get("generation_prompt", "")
    if not generation_prompt:
        algorithm_name = dk.get("algorithm_name", "")
        must_include = asset_spec.get("must_include", [])
        generation_prompt = (
            f"Clean educational diagram of {algorithm_name} algorithm. "
            f"Simple, clear visualization with labeled components. "
            f"White background, textbook style."
        )
        if must_include:
            generation_prompt += f" Must include: {', '.join(must_include)}"

    try:
        from app.services.media_generation_service import MediaGenerationService

        service = MediaGenerationService()
        # Use the generate_image_dalle method for algorithm illustrations
        result = await service.generate_image_dalle(
            prompt=generation_prompt,
            size="1024x1024",
            quality="standard",
        )

        if result and result.get("url"):
            logger.info(f"Image generation succeeded: {result['url'][:80]}...")
            return result["url"]

    except Exception as e:
        logger.warning(f"Image generation failed: {e}")

    return None
