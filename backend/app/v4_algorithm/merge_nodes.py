"""V4 Algorithm Pipeline Merge Nodes — deduplication + aggregation."""

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.v4_algorithm.merge")


async def algo_phase0_merge(state: dict) -> dict:
    """Merge input_analyzer + dk_retriever outputs.

    Both write directly to state fields, so this is a no-op passthrough
    that exists as a synchronization point.
    """
    dk = state.get("domain_knowledge")
    ctx = state.get("pedagogical_context")
    logger.info(
        f"Phase 0 merge: dk={'present' if dk else 'missing'}, "
        f"context={'present' if ctx else 'missing'}"
    )
    return {}


async def algo_content_merge(state: dict) -> dict:
    """Merge parallel scene content generator outputs.

    Reads scene_contents_raw (reducer accumulator) and deduplicates
    into scene_contents keyed by scene_id. Increments content_retry_count
    so the content_retry_router can track retry budget.
    """
    raw = state.get("scene_contents_raw") or []
    retry_count = state.get("content_retry_count", 0)
    logger.info(f"Content merge: {len(raw)} raw entries (retry={retry_count})")

    merged: dict = {}
    failed: list[str] = []

    for entry in raw:
        scene_id = entry.get("scene_id", "unknown")
        status = entry.get("status", "success")

        if status == "failed":
            failed.append(scene_id)
            continue

        # Last-writer-wins per scene_id (handles retries)
        merged[scene_id] = entry

    # Scenes that succeeded on retry should not remain in the failed list
    failed = [sid for sid in failed if sid not in merged]

    if failed:
        logger.warning(f"Content merge: {len(failed)} scenes failed: {failed}")

    logger.info(f"Content merge: {len(merged)} scenes succeeded")
    return {
        "scene_contents": merged,
        "failed_content_ids": failed,
        "content_retry_count": retry_count + 1,
    }


async def algo_asset_merge(state: dict) -> dict:
    """Merge parallel asset worker outputs.

    Reads scene_assets_raw (reducer accumulator) and deduplicates
    into scene_assets keyed by scene_id. Computes failed_asset_ids
    as a separate field for the retry router.
    """
    raw = state.get("scene_assets_raw") or []
    retry_count = state.get("asset_retry_count", 0)
    logger.info(f"Asset merge: {len(raw)} raw entries (retry={retry_count})")

    merged: dict = {}
    failed: list[str] = []

    for entry in raw:
        scene_id = entry.get("scene_id", "unknown")
        status = entry.get("status", "success")

        if status == "failed":
            failed.append(scene_id)
            continue

        merged[scene_id] = entry

    # Scenes that succeeded on retry should not remain in the failed list
    failed = [sid for sid in failed if sid not in merged]

    if failed:
        logger.warning(f"Asset merge: {len(failed)} scenes still failed: {failed}")

    logger.info(f"Asset merge: {len(merged)} scenes succeeded")
    return {
        "scene_assets": merged,
        "failed_asset_ids": failed,
        "asset_retry_count": retry_count + 1,
    }
