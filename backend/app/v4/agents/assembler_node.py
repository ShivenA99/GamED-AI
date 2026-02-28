"""Blueprint Assembler Node (V4).

100% deterministic — no LLM calls.
Filters failed contents, calls assemble_blueprint, validates, repairs.
Sets generation_complete = True (CRITICAL).

State writes: blueprint, assembly_warnings, generation_complete
"""

import time
from typing import Any

from app.utils.logging_config import get_logger
from app.v4.helpers.blueprint_assembler import assemble_blueprint
from app.v4.validators.blueprint_validator import validate_blueprint

logger = get_logger("gamed_ai.v4.assembler_node")


def assembler_node(state: dict) -> dict:
    """Assemble the final blueprint from all upstream outputs.

    Reads: game_plan, mechanic_contents, interaction_results, generated_assets
    Writes: blueprint, assembly_warnings, generation_complete

    This is a synchronous node — no LLM calls.
    """
    game_plan = state.get("game_plan")
    mechanic_contents = state.get("mechanic_contents") or []
    interaction_results = state.get("interaction_results") or []
    asset_results = state.get("generated_assets") or []
    domain_knowledge = state.get("domain_knowledge") or {}

    if not mechanic_contents:
        logger.warning("assembler_node: mechanic_contents is empty — upstream content generation may have failed")
    if not interaction_results:
        logger.warning("assembler_node: interaction_results is empty — upstream interaction design may have failed")
    if not asset_results:
        logger.info("assembler_node: no generated_assets — scenes may not need diagrams")
    is_degraded = state.get("is_degraded", False)
    sub_stages: list[dict[str, Any]] = []

    if not game_plan:
        logger.error("No game plan available for assembly")
        return {
            "blueprint": None,
            "generation_complete": False,
            "error_message": "Assembler: no game plan",
        }

    # Filter out failed mechanic contents
    valid_contents = [
        mc for mc in mechanic_contents
        if mc.get("status") != "failed"
    ]
    failed_count = len(mechanic_contents) - len(valid_contents)
    if failed_count > 0:
        logger.warning(f"Filtering out {failed_count} failed mechanic contents")

    warnings: list[str] = []

    if failed_count > 0:
        warnings.append(f"{failed_count} mechanic(s) failed content generation")

    # Check for missing assets
    scenes_needing_assets = [
        s for s in game_plan.get("scenes", [])
        if s.get("needs_diagram", False)
    ]
    asset_scene_ids = {a.get("scene_id") for a in asset_results if a.get("status") == "success"}
    missing_assets = [
        s["scene_id"] for s in scenes_needing_assets
        if s.get("scene_id") not in asset_scene_ids
    ]
    if missing_assets:
        warnings.append(f"Missing assets for scenes: {', '.join(missing_assets)}")

    # Assemble
    t_assemble = time.time()
    try:
        blueprint = assemble_blueprint(
            game_plan=game_plan,
            mechanic_contents=valid_contents,
            interaction_results=interaction_results,
            asset_results=asset_results,
            domain_knowledge=domain_knowledge,
        )
        assemble_ms = int((time.time() - t_assemble) * 1000)
        sub_stages.append({
            "id": "assembler_assemble",
            "name": "Blueprint assembly",
            "type": "assembly",
            "status": "success",
            "duration_ms": assemble_ms,
            "model": "deterministic",
            "output_summary": {
                "title": blueprint.get("title", "Untitled"),
                "template_type": blueprint.get("templateType"),
                "scene_count": len(blueprint.get("game_sequence", {}).get("scenes", [])),
                "mechanic_count": len(valid_contents),
            },
        })
    except Exception as e:
        assemble_ms = int((time.time() - t_assemble) * 1000)
        sub_stages.append({
            "id": "assembler_assemble",
            "name": "Blueprint assembly",
            "type": "assembly",
            "status": "failed",
            "duration_ms": assemble_ms,
            "model": "deterministic",
            "error": str(e)[:200],
            "output_summary": {},
        })
        logger.error(f"Blueprint assembly failed: {e}", exc_info=True)
        return {
            "blueprint": None,
            "generation_complete": False,
            "error_message": f"Assembly failed: {e}",
            "_sub_stages": sub_stages,
        }

    # Validate
    t_validate = time.time()
    validation = validate_blueprint(blueprint)
    validate_ms = int((time.time() - t_validate) * 1000)

    sub_stages.append({
        "id": "assembler_validate",
        "name": "Blueprint validation",
        "type": "validation",
        "status": "success" if validation.passed else "failed",
        "duration_ms": validate_ms,
        "model": "rule_based",
        "output_summary": {
            "passed": validation.passed,
            "error_count": len(validation.errors) if hasattr(validation, 'errors') else 0,
            "errors": [i.message for i in validation.errors][:5] if not validation.passed and hasattr(validation, 'errors') else [],
        },
    })

    if not validation.passed:
        error_messages = [i.message for i in validation.errors]
        logger.warning(f"Blueprint validation failed: {error_messages}")

        # Attempt repair
        t_repair = time.time()
        repaired = _attempt_repair(blueprint, validation)
        repair_ms = int((time.time() - t_repair) * 1000)

        if repaired:
            blueprint = repaired
            re_validation = validate_blueprint(blueprint)
            sub_stages.append({
                "id": "assembler_repair",
                "name": "Blueprint repair",
                "type": "repair",
                "status": "success" if re_validation.passed else "degraded",
                "duration_ms": repair_ms,
                "model": "heuristic",
                "output_summary": {
                    "repaired": True,
                    "re_validation_passed": re_validation.passed,
                    "remaining_errors": [i.message for i in re_validation.errors][:5] if not re_validation.passed else [],
                },
            })
            if re_validation.passed:
                logger.info("Blueprint repaired successfully")
                warnings.append("Blueprint required repair after initial assembly")
            else:
                remaining = [i.message for i in re_validation.errors]
                logger.warning(f"Blueprint still has issues after repair: {remaining}")
                warnings.extend(remaining)
                is_degraded = True
        else:
            sub_stages.append({
                "id": "assembler_repair",
                "name": "Blueprint repair",
                "type": "repair",
                "status": "skipped",
                "duration_ms": repair_ms,
                "model": "heuristic",
                "output_summary": {"repaired": False, "reason": "No applicable repairs found"},
            })
            warnings.extend(error_messages)
            is_degraded = True

    # Validate blueprint integrity
    diagram = blueprint.get("diagram") or {}
    bp_zones = diagram.get("zones") or []
    if not diagram.get("imageUrl") and not diagram.get("assetUrl"):
        warnings.append("Blueprint has no diagram image URL")
        is_degraded = True
    if not bp_zones:
        warnings.append("Blueprint has no zones defined")
        is_degraded = True
    else:
        empty_point_zones = [z.get("label", z.get("id", "?")) for z in bp_zones if not z.get("points")]
        if empty_point_zones:
            warnings.append(f"Zones with empty points: {', '.join(empty_point_zones[:5])}")

    # Add degraded warning
    if is_degraded:
        warnings.append("Game is degraded — some mechanics may not work")

    # Set generation_complete = True — CRITICAL
    # Without this, routes/generate.py marks the run as "error"
    blueprint["generation_complete"] = True

    logger.info(f"Assembly complete: {blueprint.get('title', 'Untitled')}, "
                f"template={blueprint.get('templateType')}, "
                f"max_score={blueprint.get('totalMaxScore', 0)}, "
                f"warnings={len(warnings)}")

    return {
        "blueprint": blueprint,
        "assembly_warnings": warnings,
        "generation_complete": True,
        "is_degraded": is_degraded,
        "_sub_stages": sub_stages,
    }


def _attempt_repair(blueprint: dict, validation: Any) -> dict | None:
    """Attempt to repair common blueprint issues.

    Returns repaired blueprint, or None if repair not possible.
    """
    repaired = dict(blueprint)
    made_changes = False

    for issue in validation.issues:
        if issue.severity != "error":
            continue

        msg = issue.message.lower()

        # Fix missing templateType
        if "templatetype" in msg:
            repaired["templateType"] = "INTERACTIVE_DIAGRAM"
            made_changes = True

        # Fix missing diagram
        if "diagram" in msg and "diagram" not in repaired:
            repaired["diagram"] = {"assetUrl": None, "zones": []}
            made_changes = True

        # Fix missing interactionMode
        if "interactionmode" in msg:
            # Set from first mechanic
            scenes = repaired.get("game_sequence", {}).get("scenes", [])
            if scenes and scenes[0].get("mechanics"):
                repaired["interactionMode"] = scenes[0]["mechanics"][0].get("mechanic_type", "drag_drop")
                made_changes = True
            elif any(k.endswith("Config") for k in repaired):
                # Infer from config keys
                config_keys = [k for k in repaired if k.endswith("Config")]
                if config_keys:
                    mode_map = {
                        "dragDropConfig": "drag_drop",
                        "clickToIdentifyConfig": "click_to_identify",
                        "tracePathConfig": "trace_path",
                        "sequenceConfig": "sequencing",
                        "sortingConfig": "sorting_categories",
                        "memoryMatchConfig": "memory_match",
                        "branchingConfig": "branching_scenario",
                        "descriptionMatchingConfig": "description_matching",
                    }
                    for ck in config_keys:
                        if ck in mode_map:
                            repaired["interactionMode"] = mode_map[ck]
                            made_changes = True
                            break

        # Fix missing animationCues
        if "animationcues" in msg:
            repaired["animationCues"] = {
                "correctPlacement": "pulse-green",
                "incorrectPlacement": "shake-red",
                "hintHighlight": "pulse-blue",
            }
            made_changes = True

    return repaired if made_changes else None
