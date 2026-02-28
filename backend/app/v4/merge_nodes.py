"""V4 Merge Nodes — deterministic fan-in synchronization points.

phase0_merge: joins parallel context-gathering results (input_analyzer + dk_retriever)
scene_design_merge: collects parallel scene designs, validates, deduplicates
content_merge: collects parallel content generator results, validates
interaction_merge: collects parallel interaction designer results
art_direction_merge: collects parallel art direction results
asset_merge: deduplicates Send-accumulated asset results by scene_id
"""

from typing import Any

from app.utils.logging_config import get_logger
from app.v4.schemas.creative_design import SceneCreativeDesign
from app.v4.validators.scene_design_validator import validate_scene_design

logger = get_logger("gamed_ai.v4.merge_nodes")


def phase0_merge(state: dict) -> dict:
    """Synchronize after parallel Phase 0 (input_analyzer + dk_retriever).

    Both outputs are already in state from parallel edges.
    This node is purely a synchronization barrier.
    """
    ped = state.get("pedagogical_context")
    dk = state.get("domain_knowledge")

    logger.info(
        f"Phase 0 merge: pedagogical={'yes' if ped else 'no'}, "
        f"dk={'yes' if dk else 'no'}"
    )

    # Return the fields so instrumentation can capture them in output_snapshot.
    # Since these are already in state, LangGraph treats re-writing them as a no-op.
    result = {}
    if ped:
        result["pedagogical_context"] = ped
    if dk:
        result["domain_knowledge"] = dk
    return result


def scene_design_merge(state: dict) -> dict:
    """Collect and validate parallel scene design results.

    Reads: scene_creative_designs_raw (accumulated via operator.add)
    Reads: game_concept (for validation alignment)
    Writes: scene_creative_designs (deduplicated), scene_design_validation,
            failed_scene_design_ids
    """
    raw = state.get("scene_creative_designs_raw") or []
    concept = state.get("game_concept")
    if not concept:
        logger.error("scene_design_merge: game_concept is missing from state")
    scenes = (concept or {}).get("scenes", [])

    if not raw:
        logger.info("Scene design merge: no raw designs")
        return {
            "scene_creative_designs": {},
            "scene_design_validation": {},
        }

    # Deduplicate by scene_id — keep latest
    by_scene: dict[str, dict] = {}
    for entry in raw:
        sid = entry.get("scene_id", "unknown")
        by_scene[sid] = entry

    designs: dict[str, Any] = {}
    validations: dict[str, Any] = {}
    failed_ids: list[str] = []

    for sid, entry in by_scene.items():
        if entry.get("status") != "success":
            failed_ids.append(sid)
            validations[sid] = {
                "passed": False,
                "issues": [{"severity": "error", "message": entry.get("error", "Unknown error")}],
            }
            continue

        design_raw = entry.get("design", {})
        scene_index = entry.get("scene_index", 0)

        # Validate against scene concept
        try:
            design = SceneCreativeDesign(**design_raw)
            scene_concept_mechanics = (
                scenes[scene_index].get("mechanics", [])
                if scene_index < len(scenes)
                else []
            )
            validation = validate_scene_design(design, scene_concept_mechanics)
            validations[sid] = validation.model_dump()

            if validation.passed:
                designs[sid] = design_raw
            else:
                failed_ids.append(sid)
                # Still keep the design for retry reference
                designs[sid] = design_raw
        except Exception as e:
            logger.error(f"Scene design validation error for {sid}: {e}")
            failed_ids.append(sid)
            validations[sid] = {
                "passed": False,
                "issues": [{"severity": "error", "message": str(e)}],
            }

    logger.info(
        f"Scene design merge: {len(designs)} designs, "
        f"{len(failed_ids)} failed"
    )

    result: dict[str, Any] = {
        "scene_creative_designs": designs,
        "scene_design_validation": validations,
    }
    if failed_ids:
        result["failed_scene_design_ids"] = failed_ids

    return result


def content_merge(state: dict) -> dict:
    """Collect and deduplicate parallel content generator results.

    Reads: mechanic_contents_raw (accumulated via operator.add)
    Writes: mechanic_contents (deduplicated list)
    """
    raw = state.get("mechanic_contents_raw") or []

    if not raw:
        logger.info("Content merge: no raw contents")
        return {"mechanic_contents": []}

    # Deduplicate by mechanic_id — keep latest
    by_mechanic: dict[str, dict] = {}
    for entry in raw:
        mid = entry.get("mechanic_id", "unknown")
        by_mechanic[mid] = entry

    all_contents = list(by_mechanic.values())
    successes = [c for c in all_contents if c.get("status") != "failed"]
    failures = [c for c in all_contents if c.get("status") == "failed"]

    logger.info(
        f"Content merge: {len(successes)} successes, {len(failures)} failures "
        f"(from {len(raw)} raw entries)"
    )

    result: dict[str, Any] = {"mechanic_contents": all_contents}
    if failures:
        result["failed_content_ids"] = [f.get("mechanic_id") for f in failures]
        result["is_degraded"] = True

    return result


def interaction_merge(state: dict) -> dict:
    """Collect parallel interaction designer results.

    Reads: interaction_results_raw (accumulated via operator.add)
    Writes: interaction_results (deduplicated list)
    """
    raw = state.get("interaction_results_raw") or []

    if not raw:
        logger.info("Interaction merge: no raw results")
        return {"interaction_results": []}

    # Deduplicate by scene_id — keep latest
    by_scene: dict[str, dict] = {}
    for entry in raw:
        sid = entry.get("scene_id", "unknown")
        by_scene[sid] = entry

    logger.info(f"Interaction merge: {len(by_scene)} scenes")
    return {"interaction_results": list(by_scene.values())}


def art_direction_merge(state: dict) -> dict:
    """Collect parallel art direction results.

    Reads: art_directed_manifests_raw (accumulated via operator.add)
    Writes: art_directed_manifests (deduplicated by scene_id)
    """
    raw = state.get("art_directed_manifests_raw") or []

    if not raw:
        logger.info("Art direction merge: no raw manifests")
        return {"art_directed_manifests": {}}

    by_scene: dict[str, dict] = {}
    failed_ids: list[str] = []

    for entry in raw:
        sid = entry.get("scene_id", "unknown")
        if entry.get("status") == "error":
            failed_ids.append(sid)
        else:
            by_scene[sid] = entry.get("manifest", entry)

    logger.info(
        f"Art direction merge: {len(by_scene)} manifests, {len(failed_ids)} failed"
    )

    result: dict[str, Any] = {"art_directed_manifests": by_scene}
    if failed_ids:
        result["failed_art_direction_ids"] = failed_ids
    return result


def asset_merge(state: dict) -> dict:
    """Deduplicate accumulated asset results from Send workers.

    Reads: generated_assets_raw (accumulated via operator.add from Send workers)
    Writes: generated_assets (deduplicated), asset_retry_count

    Deduplication: keep latest result per scene_id (handles retry accumulation —
    on retry, old results are still in generated_assets_raw, but the latest
    entry per scene_id wins).

    Note: Does NOT write failed_asset_scene_ids because that field uses
    operator.add reducer and would accumulate across retries. The retry
    router reads generated_assets to determine current failures instead.
    """
    raw = state.get("generated_assets_raw") or []
    current_retry = state.get("asset_retry_count", 0)

    if not raw:
        logger.info("Asset merge: no raw assets to process")
        return {
            "generated_assets": [],
            "asset_retry_count": current_retry + 1,
        }

    # Deduplicate by scene_id — keep latest (last in list)
    by_scene: dict[str, dict] = {}
    for asset in raw:
        sid = asset.get("scene_id", "unknown")
        by_scene[sid] = asset  # overwrites earlier entries

    all_deduped = list(by_scene.values())
    successes = [a for a in all_deduped if a.get("status") == "success"]
    failures = [a for a in all_deduped if a.get("status") != "success"]

    logger.info(
        f"Asset merge: {len(successes)} successes, {len(failures)} failures "
        f"(from {len(raw)} raw entries, retry_round={current_retry})"
    )

    return {
        "generated_assets": all_deduped,
        "asset_retry_count": current_retry + 1,
    }
