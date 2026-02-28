"""V4 Algorithm Pipeline Routers — conditional graph edges.

Routers:
  concept_router: Phase 1 retry loop
  plan_router: Phase 2 retry loop (routes back to concept designer)
  content_dispatch_router: Phase 3 parallel Send
  content_retry_router: Phase 3b retry failed scenes after validation
  asset_dispatch_router: Phase 4 parallel Send (scenes needing visuals)
  asset_retry_router: Phase 4 retry (reads failed_asset_ids from merge)
"""

from typing import Union

from langgraph.types import Send

from app.utils.logging_config import get_logger
from app.v4_algorithm.contracts import needs_visual_asset

logger = get_logger("gamed_ai.v4_algorithm.routers")

MAX_CONCEPT_RETRIES = 2
MAX_PLAN_RETRIES = 2
MAX_CONTENT_RETRIES = 1
MAX_ASSET_RETRIES = 1


# ── Phase 1: Concept Design ──────────────────────────────────────


def concept_router(state: dict) -> str:
    """Route after concept validation: retry or proceed to graph builder."""
    validation = state.get("concept_validation") or {}
    passed = validation.get("passed", False)
    retry_count = state.get("concept_retry_count", 0)

    if passed:
        logger.info("Concept validation passed, proceeding to graph builder")
        return "pass"

    if retry_count <= MAX_CONCEPT_RETRIES:
        logger.info(f"Concept validation failed, retrying ({retry_count}/{MAX_CONCEPT_RETRIES})")
        return "retry"

    logger.warning(f"Concept validation exhausted {MAX_CONCEPT_RETRIES} retries, proceeding with override")
    return "pass"


# ── Phase 2: Game Plan ───────────────────────────────────────────


def plan_router(state: dict) -> str:
    """Route after plan validation: retry concept or proceed to content generation.

    The graph builder is deterministic — same concept always produces same plan.
    On failure, route back to concept designer so a fresh concept can produce
    a different (hopefully valid) plan.
    """
    validation = state.get("plan_validation") or {}
    passed = validation.get("passed", False)
    retry_count = state.get("plan_retry_count", 0)

    if passed:
        logger.info("Plan validation passed, proceeding to content generation")
        return "pass"

    if retry_count <= MAX_PLAN_RETRIES:
        logger.info(
            f"Plan validation failed, re-generating concept ({retry_count}/{MAX_PLAN_RETRIES})"
        )
        return "retry"

    logger.warning(f"Plan validation exhausted {MAX_PLAN_RETRIES} retries, proceeding with override")
    return "pass"


# ── Phase 3: Content Generation (parallel Send) ──────────────────


def content_dispatch_router(state: dict) -> list[Send]:
    """Fan-out to parallel scene content generators.

    Dispatches one Send("algo_scene_content_gen", {...}) per scene in the game plan.
    """
    game_plan = state.get("game_plan")
    if not game_plan:
        logger.error("content_dispatch_router: game_plan is missing")
        return []

    scenes = game_plan.get("scenes", [])
    dk = state.get("domain_knowledge")

    sends = []
    for scene in scenes:
        send_payload = {
            "scene_plan": scene,
            "domain_knowledge": dk,
            "game_concept": state.get("game_concept"),
        }
        sends.append(Send("algo_scene_content_gen", send_payload))

    logger.info(f"Dispatching {len(sends)} scene content generators")
    return sends


# ── Phase 3b: Content Retry ──────────────────────────────────────


def content_retry_router(state: dict) -> Union[str, list[Send]]:
    """Route after content validation: retry failed scenes or proceed to assets.

    Re-dispatches only the scenes that failed validation. Each scene gets
    the full state context plus its scene plan from game_plan.
    """
    validation = state.get("content_validation") or {}
    retry_count = state.get("content_retry_count", 0)
    passed = validation.get("passed", True)

    if passed or retry_count > MAX_CONTENT_RETRIES:
        if not passed:
            logger.warning(
                f"Content retry limit reached ({retry_count}/{MAX_CONTENT_RETRIES}), "
                f"proceeding with degraded content"
            )
        return "asset_dispatch"

    # Identify failed scene IDs from validation issues
    failed_ids: set[str] = set()
    for issue in validation.get("issues", []):
        if issue.get("severity") == "error":
            msg = issue.get("message", "")
            # Issues are formatted as "scene_id: description"
            scene_id = msg.split(":")[0].strip() if ":" in msg else ""
            if scene_id:
                failed_ids.add(scene_id)

    if not failed_ids:
        return "asset_dispatch"

    game_plan = state.get("game_plan") or {}
    scenes = game_plan.get("scenes", [])
    scene_map = {s.get("scene_id"): s for s in scenes}
    dk = state.get("domain_knowledge")

    sends = []
    for sid in failed_ids:
        scene = scene_map.get(sid)
        if scene:
            send_payload = {
                "scene_plan": scene,
                "domain_knowledge": dk,
                "game_concept": state.get("game_concept"),
                "content_retry_count": retry_count + 1,
            }
            sends.append(Send("algo_scene_content_gen", send_payload))

    if sends:
        logger.info(f"Retrying {len(sends)} failed content scenes (retry {retry_count})")
        return sends

    return "asset_dispatch"


# ── Phase 4: Asset Generation (parallel Send — only visual scenes) ──


def asset_dispatch_router(state: dict) -> Union[str, list[Send]]:
    """Fan-out to asset workers for scenes needing visuals.

    Returns Send("algo_asset_worker", {...}) per scene needing assets,
    or "algo_blueprint_assembler" if no scenes need assets.
    """
    game_plan = state.get("game_plan")
    if not game_plan:
        logger.error("asset_dispatch_router: game_plan is missing")
        return "algo_blueprint_assembler"

    scenes = game_plan.get("scenes", [])
    run_id = state.get("_run_id")

    sends = []
    for scene in scenes:
        if scene.get("needs_asset", False):
            send_payload = {
                "scene_id": scene.get("scene_id", ""),
                "game_type": scene.get("game_type", ""),
                "asset_spec": scene.get("asset_spec"),
                "domain_knowledge": state.get("domain_knowledge"),
            }
            if run_id:
                send_payload["_run_id"] = run_id
            sends.append(Send("algo_asset_worker", send_payload))

    if not sends:
        logger.info("No scenes need visual assets, skipping to assembler")
        return "algo_blueprint_assembler"

    logger.info(f"Dispatching {len(sends)} asset workers")
    return sends


def asset_retry_router(state: dict) -> Union[str, list[Send]]:
    """Route after asset merge: retry failed assets or proceed to assembler.

    Reads failed_asset_ids from algo_asset_merge (not scene_assets_raw) to
    avoid the accumulator bug where raw entries from previous retries inflate
    the failure count.
    """
    failed_ids = state.get("failed_asset_ids") or []
    retry_count = state.get("asset_retry_count", 0)
    game_plan = state.get("game_plan")

    if not game_plan:
        return "algo_blueprint_assembler"

    if not failed_ids or retry_count > MAX_ASSET_RETRIES:
        if failed_ids:
            logger.warning(f"Asset retry limit reached, {len(failed_ids)} failed scenes")
        return "algo_blueprint_assembler"

    # Deduplicate failed_ids since the reducer accumulates across retries
    unique_failed = list(dict.fromkeys(failed_ids))

    scenes = game_plan.get("scenes", [])
    scene_map = {s.get("scene_id"): s for s in scenes}
    # Only retry scenes that are still failed (not in successful scene_assets)
    scene_assets = state.get("scene_assets") or {}
    still_failed = [sid for sid in unique_failed if sid not in scene_assets]

    run_id = state.get("_run_id")

    sends = []
    for sid in still_failed:
        scene = scene_map.get(sid)
        if scene:
            send_payload = {
                "scene_id": sid,
                "game_type": scene.get("game_type", ""),
                "asset_spec": scene.get("asset_spec"),
                "domain_knowledge": state.get("domain_knowledge"),
            }
            if run_id:
                send_payload["_run_id"] = run_id
            sends.append(Send("algo_asset_worker", send_payload))

    if sends:
        logger.info(f"Retrying {len(sends)} failed asset scenes (retry {retry_count})")
        return sends

    return "algo_blueprint_assembler"
