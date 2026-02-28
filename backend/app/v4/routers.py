"""V4 Router functions for conditional graph edges.

Each router reads state and returns either a string (node name) or
a list of Send objects for fan-out.

3-Stage Creative Cascade Routers:
  concept_router: Phase 1a retry loop
  scene_design_send_router: Phase 1b fan-out
  scene_design_retry_router: Phase 1b retry loop
  content_dispatch_router: Phase 2a fan-out
  interaction_dispatch_router: Phase 2b fan-out
  asset_send_router: Phase 3b fan-out
  asset_retry_router: Phase 3b retry
"""

from typing import Union

from langgraph.types import Send

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.v4.routers")


MAX_CONCEPT_RETRIES = 2
MAX_SCENE_DESIGN_RETRIES = 1
MAX_DESIGN_RETRIES = 2
MAX_ASSET_RETRIES = 1


# ── Phase 1a: Concept Design ──────────────────────────────────────


def concept_router(state: dict) -> str:
    """Route after concept validation: retry or proceed to scene design.

    Returns "retry" → game_concept_designer
    Returns "pass" → scene_design_send_router
    """
    validation = state.get("concept_validation") or {}
    passed = validation.get("passed", False)
    retry_count = state.get("concept_retry_count", 0)

    if passed:
        logger.info("Concept validation passed, proceeding to scene design")
        return "pass"

    if retry_count <= MAX_CONCEPT_RETRIES:
        logger.info(f"Concept validation failed, retrying (attempt {retry_count}/{MAX_CONCEPT_RETRIES})")
        return "retry"

    logger.warning(f"Concept validation failed after {MAX_CONCEPT_RETRIES} retries, proceeding with override")
    return "pass"


# ── Phase 1b: Scene Design (parallel Send) ────────────────────────


def scene_design_send_router(state: dict) -> list[Send]:
    """Fan-out to parallel scene designers.

    Reads game_concept.scenes and dispatches one Send("scene_designer", {...})
    per scene.
    """
    concept = state.get("game_concept")
    if not concept:
        logger.error("scene_design_send_router: game_concept is missing from state")
        return []
    scenes = concept.get("scenes", [])
    dk = state.get("domain_knowledge")
    pedagogy = state.get("pedagogical_context")
    narrative_theme = concept.get("narrative_theme", "")

    sends = []
    for si, scene in enumerate(scenes):
        send_payload = {
            "scene_concept": scene,
            "scene_index": si,
            "narrative_theme": narrative_theme,
            "domain_knowledge": dk,
            "pedagogical_context": pedagogy,
        }
        sends.append(Send("scene_designer", send_payload))

    logger.info(f"Dispatching {len(sends)} scene designers")
    return sends


def scene_design_retry_router(state: dict) -> Union[str, list[Send]]:
    """After scene_design_merge: retry failed scenes or proceed to graph_builder.

    Returns Send("scene_designer", {...}) for failed scenes, or "graph_builder".
    """
    validation = state.get("scene_design_validation") or {}
    retry_counts = state.get("scene_design_retry_counts") or {}
    concept = state.get("game_concept")
    if not concept:
        logger.error("scene_design_retry_router: game_concept is missing from state")
        return "graph_builder"
    scenes = concept.get("scenes", [])
    dk = state.get("domain_knowledge")
    pedagogy = state.get("pedagogical_context")
    narrative_theme = concept.get("narrative_theme", "")

    # Find failed scenes that can be retried
    sends = []
    for sid, val in validation.items():
        if not val.get("passed", True):
            current_retries = retry_counts.get(sid, 0)
            if current_retries <= MAX_SCENE_DESIGN_RETRIES:
                # Find the scene concept for this scene_id
                # scene_id is "scene_{index+1}", extract index
                scene_index = _extract_scene_index(sid)
                if scene_index is not None and scene_index < len(scenes):
                    # Include retry info (validation issues)
                    issues = val.get("issues", [])
                    retry_info = "; ".join(
                        i.get("message", "") for i in issues
                        if i.get("severity") == "error"
                    )
                    send_payload = {
                        "scene_concept": scenes[scene_index],
                        "scene_index": scene_index,
                        "narrative_theme": narrative_theme,
                        "domain_knowledge": dk,
                        "pedagogical_context": pedagogy,
                        "retry_info": retry_info,
                    }
                    sends.append(Send("scene_designer", send_payload))

    if sends:
        logger.info(f"Retrying {len(sends)} failed scene designs")
        return sends

    logger.info("All scene designs passed or retry limit reached, proceeding to graph builder")
    return "graph_builder"


# ── Phase 2a: Content Generation (parallel Send) ──────────────────


def content_dispatch_router(state: dict) -> list[Send]:
    """Fan-out to parallel content generators after graph_builder.

    Dispatches one Send("content_generator", {...}) per mechanic across all scenes.
    """
    from app.v4.agents.content_generator import build_scene_context

    game_plan = state.get("game_plan")
    if not game_plan:
        logger.error("content_dispatch_router: game_plan is missing from state")
        return []
    scenes = game_plan.get("scenes", [])
    dk = state.get("domain_knowledge")

    sends = []
    for scene in scenes:
        scene_context = build_scene_context(scene, dk)
        mechanics = scene.get("mechanics", [])
        for mech in mechanics:
            send_payload = {
                "mechanic_plan": mech,
                "scene_context": scene_context,
                "domain_knowledge": dk,
                "attempt": 1,
            }
            sends.append(Send("content_generator", send_payload))

    logger.info(f"Dispatching {len(sends)} content generators")
    return sends


# ── Phase 2b: Interaction Design (parallel Send) ──────────────────


def interaction_dispatch_router(state: dict) -> Union[str, list[Send]]:
    """Fan-out to parallel interaction designers after content_merge.

    Dispatches one Send("interaction_designer", {...}) per scene.
    If no contents succeeded, skip to asset dispatch.
    """
    game_plan = state.get("game_plan")
    if not game_plan:
        logger.error("interaction_dispatch_router: game_plan is missing from state")
        return "interaction_merge"
    scenes = game_plan.get("scenes", [])
    mechanic_contents = state.get("mechanic_contents") or []
    pedagogy = state.get("pedagogical_context")

    if not mechanic_contents:
        logger.warning("No mechanic contents, skipping interaction design")
        return "interaction_merge"

    # Group contents by scene_id
    contents_by_scene: dict[str, list[dict]] = {}
    for mc in mechanic_contents:
        if mc.get("status") != "failed":
            sid = mc.get("scene_id", "")
            contents_by_scene.setdefault(sid, []).append(mc)

    sends = []
    for scene in scenes:
        scene_id = scene.get("scene_id", "")
        scene_contents = contents_by_scene.get(scene_id, [])
        if not scene_contents:
            logger.info(f"Skipping interaction design for {scene_id}: no successful contents")
            continue
        send_payload = {
            "scene_plan": scene,
            "mechanic_contents": scene_contents,
            "pedagogical_context": pedagogy,
        }
        sends.append(Send("interaction_designer", send_payload))

    if not sends:
        logger.warning("No scenes with successful contents, skipping all interaction design")
        return "interaction_merge"

    logger.info(f"Dispatching {len(sends)} interaction designers")
    return sends


# ── Phase 3b: Asset Dispatch ──────────────────────────────────────


def asset_send_router(state: dict) -> Union[str, list[Send]]:
    """Route after interaction_merge: dispatch asset workers or skip to assembler.

    Returns Send("asset_worker", {...}) for each scene needing a diagram,
    or "blueprint_assembler" if no scenes need diagrams.
    """
    game_plan = state.get("game_plan")
    if not game_plan:
        logger.error("asset_send_router: game_plan is missing from state")
        return "blueprint_assembler"
    scenes = game_plan.get("scenes", [])
    scene_designs = state.get("scene_creative_designs") or {}
    question_text = state.get("question_text", "")
    run_id = state.get("_run_id")

    sends = []
    for scene in scenes:
        if scene.get("needs_diagram", False):
            scene_id = scene.get("scene_id", "unknown")
            # Use image_spec from creative design if available
            creative = scene_designs.get(scene_id, {})
            image_spec = creative.get("image_spec") or scene.get("image_spec") or {}

            send_payload = {
                "scene_id": scene_id,
                "image_spec": image_spec,
                "zone_labels": scene.get("zone_labels", []),
                "question_text": question_text,
            }
            if run_id:
                send_payload["_run_id"] = run_id
            sends.append(Send("asset_worker", send_payload))

    if not sends:
        logger.info("No scenes need diagrams, routing directly to assembler")
        return "blueprint_assembler"

    logger.info(f"Dispatching {len(sends)} asset workers")
    return sends


def asset_retry_router(state: dict) -> Union[str, list[Send]]:
    """Route after asset_merge: retry failed assets or proceed to assembler.

    Reads generated_assets (deduplicated by asset_merge) to find current failures.
    Returns Send for failed scenes (max 1 retry) or "blueprint_assembler".
    """
    generated = state.get("generated_assets") or []
    retry_count = state.get("asset_retry_count", 0)
    game_plan = state.get("game_plan")
    if not game_plan:
        logger.error("asset_retry_router: game_plan is missing from state")
        return "blueprint_assembler"
    scenes = game_plan.get("scenes", [])

    failed_ids = [a.get("scene_id") for a in generated if a.get("status") != "success"]

    if not failed_ids or retry_count > MAX_ASSET_RETRIES:
        if failed_ids:
            logger.warning(f"Asset retry limit reached, proceeding with {len(failed_ids)} failed scenes")
        else:
            logger.info("All assets successful, proceeding to assembler")
        return "blueprint_assembler"

    question_text = state.get("question_text", "")
    run_id = state.get("_run_id")
    scene_map = {s.get("scene_id"): s for s in scenes}
    sends = []
    for sid in failed_ids:
        scene = scene_map.get(sid)
        if scene:
            send_payload = {
                "scene_id": sid,
                "image_spec": scene.get("image_spec") or {},
                "zone_labels": scene.get("zone_labels", []),
                "question_text": question_text,
            }
            if run_id:
                send_payload["_run_id"] = run_id
            sends.append(Send("asset_worker", send_payload))

    if sends:
        logger.info(f"Retrying {len(sends)} failed asset scenes (retry round {retry_count})")
        return sends

    return "blueprint_assembler"


# ── Legacy compatibility ──────────────────────────────────────────


def design_router(state: dict) -> str:
    """Route after game plan validation: retry or pass (legacy 9-node graph).

    Kept for backward compatibility. New cascade uses concept_router instead.
    """
    validation = state.get("design_validation") or {}
    passed = validation.get("passed", False)
    retry_count = state.get("design_retry_count", 0)

    if passed:
        return "pass"
    if retry_count <= MAX_DESIGN_RETRIES:
        return "retry"
    return "pass"


# ── Helpers ───────────────────────────────────────────────────────


def _extract_scene_index(scene_id: str) -> int | None:
    """Extract scene index from scene_id like 'scene_1' → 0."""
    try:
        parts = scene_id.split("_")
        return int(parts[-1]) - 1
    except (ValueError, IndexError):
        return None
