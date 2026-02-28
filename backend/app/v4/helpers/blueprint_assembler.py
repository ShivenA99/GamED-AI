"""Blueprint Assembler — transforms all upstream outputs into InteractiveDiagramBlueprint.

This is the most complex deterministic helper. It maps:
- GamePlan (design) + MechanicContents (content) + InteractionResults (scoring/feedback)
  + AssetResults (diagram/zones) -> InteractiveDiagramBlueprint dict

Key invariants:
- identificationPrompts[] and paths[] are AT ROOT (not inside config)
- All field names match frontend types exactly (front/back, question/options, etc.)
- Content-only scenes have diagram.assetUrl=null, zones=[], labels=[]
- Multi-scene games have game_sequence.scenes[] + is_multi_scene=true
"""

import logging
from typing import Any, Optional

from app.v4.contracts import (
    ZONE_BASED_MECHANICS, CONTENT_ONLY_MECHANICS,
    resolve_trigger,
)
from app.v4.helpers.utils import (
    generate_zone_id, generate_label_id, generate_mechanic_id,
    postprocess_zones, normalize_label_text,
)
from app.v4.helpers.zone_matcher import match_labels_to_zones

logger = logging.getLogger("gamed_ai.v4.blueprint_assembler")


def assemble_blueprint(
    game_plan: dict[str, Any],
    mechanic_contents: list[dict[str, Any]],
    interaction_results: list[dict[str, Any]],
    asset_results: list[dict[str, Any]],
    domain_knowledge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the final InteractiveDiagramBlueprint from all upstream outputs.

    Args:
        game_plan: GamePlan.model_dump()
        mechanic_contents: list of {mechanic_id, scene_id, mechanic_type, content: dict}
        interaction_results: list of SceneInteractionResult.model_dump()
        asset_results: list of AssetResult dicts (scene_id, diagram_url, zones, status)

    Returns:
        InteractiveDiagramBlueprint dict ready for frontend consumption.
    """
    scenes = game_plan.get("scenes", [])
    is_multi_scene = len(scenes) > 1

    # Index content/interaction/assets by scene_id
    content_by_scene = _index_by_scene(mechanic_contents)
    interaction_by_scene = {ir.get("scene_id"): ir for ir in interaction_results}
    assets_by_scene = {ar.get("scene_id"): ar for ar in asset_results}

    # Build per-scene blueprints
    scene_blueprints: list[dict[str, Any]] = []
    all_mechanics: list[dict[str, Any]] = []
    all_transitions: list[dict[str, Any]] = []

    for si, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", f"scene_{si + 1}")
        scene_number = si + 1

        scene_bp = _build_scene_blueprint(
            scene=scene,
            scene_number=scene_number,
            contents=content_by_scene.get(scene_id, []),
            interaction=interaction_by_scene.get(scene_id, {}),
            asset=assets_by_scene.get(scene_id),
            distractor_labels=game_plan.get("distractor_labels", []),
        )
        scene_blueprints.append(scene_bp)
        all_mechanics.extend(scene_bp.get("_mechanics", []))
        all_transitions.extend(scene_bp.get("_transitions", []))

    # Use first scene as root blueprint (backward compat)
    first = scene_blueprints[0] if scene_blueprints else {}

    blueprint: dict[str, Any] = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": game_plan.get("title", ""),
        "subject": game_plan.get("subject", ""),
        "difficulty": game_plan.get("difficulty", "intermediate"),
        "narrativeIntro": _build_narrative(game_plan),
        "narrativeTheme": game_plan.get("narrative_theme", ""),
        "completionMessage": game_plan.get("completion_message", ""),
        "estimatedDurationMinutes": game_plan.get("estimated_duration_minutes", 10),
        "diagram": first.get("diagram", {"assetUrl": None, "assetPrompt": "", "zones": []}),
        "labels": first.get("labels", []),
        "distractorLabels": [],  # Disabled — distractors cause confusion with zone-based mechanics
        "mechanics": all_mechanics,
        "modeTransitions": all_transitions,
        "interactionMode": all_mechanics[0]["type"] if all_mechanics else "drag_drop",
        "animationCues": {"correctPlacement": "pulse-green", "incorrectPlacement": "shake-red"},
        "scoringStrategy": {
            "type": "per_zone",
            "base_points_per_zone": _first_points_per_item(game_plan),
            "max_score": game_plan.get("total_max_score", 0),
        },
        "totalMaxScore": game_plan.get("total_max_score", 0),
        "generation_complete": True,
    }

    # Promote first scene's per-mechanic configs to root
    for key in _CONFIG_KEYS:
        if key in first:
            blueprint[key] = first[key]

    # identificationPrompts and paths at ROOT
    if "identificationPrompts" in first:
        blueprint["identificationPrompts"] = first["identificationPrompts"]
    if "paths" in first:
        blueprint["paths"] = first["paths"]

    # Timed handling
    timed_mechanic = _find_timed_mechanic(game_plan)
    if timed_mechanic:
        blueprint["timedChallengeWrappedMode"] = timed_mechanic.get("mechanic_type", "drag_drop")
        blueprint["timeLimitSeconds"] = timed_mechanic.get("time_limit_seconds", 60)

    # Multi-scene
    if is_multi_scene:
        blueprint["is_multi_scene"] = True
        import uuid as _uuid
        blueprint["game_sequence"] = {
            "sequence_id": game_plan.get("id") or str(_uuid.uuid4()),
            "sequence_title": game_plan.get("title", ""),
            "sequence_description": game_plan.get("description", ""),
            "scenes": [_scene_to_game_scene(sb, si) for si, sb in enumerate(scene_blueprints)],
            "total_scenes": len(scene_blueprints),
            "total_max_score": game_plan.get("total_max_score", 0),
            "estimated_duration_minutes": game_plan.get("estimated_duration_minutes", 10),
            "difficulty_level": game_plan.get("difficulty", "intermediate"),
            "progression_type": "linear",
        }

    # Clean up internal keys
    for sb in scene_blueprints:
        sb.pop("_mechanics", None)
        sb.pop("_transitions", None)
        sb.pop("_scene_number", None)
        sb.pop("_narrative_intro", None)
        sb.pop("_scene_max_score", None)

    # Enrich zones with hierarchy metadata from DK (for drag_drop / click_to_identify)
    dk = domain_knowledge or {}
    hierarchy = dk.get("hierarchical_relationships") or {}
    if hierarchy and isinstance(hierarchy, dict):
        _enrich_with_hierarchy(blueprint, hierarchy, dk.get("suggested_reveal_order"))

    # Fix overlapping sibling zones — offset the smaller one
    _fix_overlapping_siblings(blueprint)

    # Sanitize for Zod schema compatibility
    _sanitize_blueprint(blueprint)

    return blueprint


# ── Per-scene assembly ───────────────────────────────────────────

def _build_scene_blueprint(
    scene: dict[str, Any],
    scene_number: int,
    contents: list[dict[str, Any]],
    interaction: dict[str, Any],
    asset: Optional[dict[str, Any]],
    distractor_labels: list[str],
) -> dict[str, Any]:
    """Build blueprint fragment for a single scene."""
    mechanics_plans = scene.get("mechanics", [])
    zone_labels = scene.get("zone_labels", [])
    has_zone_mechanic = any(m.get("mechanic_type") in ZONE_BASED_MECHANICS for m in mechanics_plans)

    # Zone matching
    label_to_zone_id: dict[str, str] = {}
    zones: list[dict[str, Any]] = []

    if asset and asset.get("status") == "success" and asset.get("zones"):
        detected_zones = postprocess_zones(asset["zones"])
        label_to_zone_id = match_labels_to_zones(zone_labels, detected_zones, scene_number)
        zones = _build_zones(detected_zones, label_to_zone_id, zone_labels, scene_number)
    elif has_zone_mechanic:
        # No asset but needs zones — generate synthetic zone IDs
        for label in zone_labels:
            zid = generate_zone_id(scene_number, label)
            label_to_zone_id[label] = zid
        zones = [{"id": zid, "label": label, "points": []} for label, zid in label_to_zone_id.items()]

    # Diagram
    asset_url = asset.get("diagram_url") if asset else None
    diagram: dict[str, Any] = {
        "assetPrompt": scene.get("image_spec", {}).get("description", "") if scene.get("image_spec") else "",
        "zones": zones,
    }
    if asset_url:
        diagram["imageUrl"] = asset_url
        diagram["assetUrl"] = asset_url

    # Labels
    labels = _build_labels(zone_labels, label_to_zone_id, scene_number)

    # Distractor labels (only for scenes with zone-based mechanics)
    distractor_list: list[dict[str, Any]] = []
    if has_zone_mechanic and distractor_labels:
        for di, dl in enumerate(distractor_labels):
            dl_text = dl if isinstance(dl, str) else dl.get("text", str(dl))
            dl_explanation = dl.get("explanation", "") if isinstance(dl, dict) else f"This is not part of the diagram."
            distractor_list.append({
                "id": f"distractor_s{scene_number}_{di}",
                "text": dl_text,
                "explanation": dl_explanation,
                "isDistractor": True,
            })

    # Content-indexed by mechanic_id
    content_by_mech = {c.get("mechanic_id"): c.get("content", {}) for c in contents}

    # Scoring/feedback from interaction results
    scoring_by_mech = interaction.get("mechanic_scoring", {})
    feedback_by_mech = interaction.get("mechanic_feedback", {})

    # Build mechanics array
    built_mechanics: list[dict[str, Any]] = []
    for mp in mechanics_plans:
        mid = mp.get("mechanic_id", "")
        mtype = mp.get("mechanic_type", "")

        scoring = scoring_by_mech.get(mid)
        if scoring is None:
            logger.warning(
                f"No scoring from interaction_designer for {mid} ({mtype}), "
                f"using fallback from plan"
            )
            scoring = {
                "strategy": "per_correct",
                "points_per_correct": mp.get("points_per_item", 10),
                "max_score": mp.get("max_score", 0),
                "partial_credit": True,
            }

        feedback = feedback_by_mech.get(mid)
        if feedback is None:
            logger.warning(
                f"No feedback from interaction_designer for {mid} ({mtype}), "
                f"using generic fallback"
            )
            feedback = {
                "on_correct": "Correct!",
                "on_incorrect": "Try again.",
                "on_completion": "Well done!",
                "misconceptions": [],
            }

        mechanic_entry: dict[str, Any] = {
            "type": mtype,
            "config": {
                "instruction_text": mp.get("instruction_text", ""),
            },
            "scoring": scoring,
            "feedback": feedback,
        }
        built_mechanics.append(mechanic_entry)

    # Mode transitions — prefer interaction_designer's enriched transitions
    transitions = interaction.get("mode_transitions", [])
    if not transitions:
        transitions = _build_transitions(scene, mechanics_plans)
    else:
        # Interaction designer outputs mechanic IDs (s1_m0) for from/to,
        # but frontend expects mechanic types (drag_drop). Resolve here.
        mech_id_to_type = {m.get("mechanic_id"): m.get("mechanic_type") for m in mechanics_plans}
        transitions = _resolve_transition_types(transitions, mech_id_to_type)

    # Scene result
    result: dict[str, Any] = {
        "scene_id": scene.get("scene_id", ""),
        "title": scene.get("title", ""),
        "learning_goal": scene.get("learning_goal", ""),
        "diagram": diagram,
        "labels": labels,
        "distractorLabels": distractor_list,
        "_mechanics": built_mechanics,
        "_transitions": transitions,
        # Internal keys for _scene_to_game_scene (cleaned up after use)
        "_scene_number": scene_number,
        "_narrative_intro": scene.get("narrative_intro", ""),
        "_scene_max_score": scene.get("scene_max_score", 0),
    }

    # Per-mechanic configs at scene level
    _populate_mechanic_configs(result, mechanics_plans, content_by_mech, label_to_zone_id, zones, scene_number)

    return result


# ── Config population ────────────────────────────────────────────

_CONFIG_KEYS = [
    "dragDropConfig", "clickToIdentifyConfig", "tracePathConfig",
    "sequenceConfig", "sortingConfig", "memoryMatchConfig",
    "branchingConfig", "descriptionMatchingConfig", "compareConfig",
]


def _populate_mechanic_configs(
    scene_bp: dict[str, Any],
    mechanics_plans: list[dict[str, Any]],
    content_by_mech: dict[str, dict[str, Any]],
    label_to_zone_id: dict[str, str],
    zones: list[dict[str, Any]],
    scene_number: int,
) -> None:
    """Populate per-mechanic config fields on the scene blueprint.

    Content dicts now include ALL visual config fields (from content_generator
    using MechanicCreativeDesign), so we spread the entire content dict into
    the config, only overriding fields that need post-processing (zone ID
    resolution, ID generation, etc.).
    """
    for mp in mechanics_plans:
        mid = mp.get("mechanic_id", "")
        mtype = mp.get("mechanic_type", "")
        content = content_by_mech.get(mid, {})

        if mtype == "drag_drop":
            # Spread visual config fields from content, excluding data fields
            config: dict[str, Any] = {
                "leader_line_style": "curved",
                "tray_position": "bottom",
                "placement_animation": "snap",
                "show_distractors": False,
            }
            # Content has: interaction_mode, feedback_timing, label_style,
            # leader_line_style, leader_line_color, leader_line_animate,
            # pin_marker_shape, label_anchor_side, tray_position, tray_layout,
            # placement_animation, incorrect_animation, zone_idle_animation,
            # zone_hover_effect, max_attempts, shuffle_labels
            _DRAG_DROP_CONFIG_KEYS = {
                "interaction_mode", "feedback_timing", "label_style",
                "leader_line_style", "leader_line_color", "leader_line_animate",
                "pin_marker_shape", "label_anchor_side", "tray_position",
                "tray_layout", "placement_animation", "incorrect_animation",
                "zone_idle_animation", "zone_hover_effect", "max_attempts",
                "shuffle_labels",
            }
            if isinstance(content, dict):
                for key in _DRAG_DROP_CONFIG_KEYS:
                    if key in content:
                        config[key] = content[key]
            scene_bp["dragDropConfig"] = config

        elif mtype == "click_to_identify":
            config = {
                "highlight_style": "outline",
                "show_label_on_click": True,
            }
            # Content has: prompt_style, selection_mode, highlight_style,
            # magnification_enabled, magnification_factor, explore_mode_enabled,
            # show_zone_count
            for key in ("prompt_style", "selection_mode", "highlight_style",
                        "magnification_enabled", "magnification_factor",
                        "explore_mode_enabled", "show_zone_count"):
                if key in content:
                    config[key] = content[key]
            scene_bp["clickToIdentifyConfig"] = config

            # identificationPrompts AT ROOT
            prompts = content.get("prompts", [])
            scene_bp["identificationPrompts"] = [
                {
                    "id": f"prompt_s{scene_number}_{i}",
                    "text": p.get("text", ""),
                    "targetLabelId": _label_id_for(p.get("target_label", ""), label_to_zone_id, scene_number),
                    "targetZoneId": label_to_zone_id.get(p.get("target_label", ""), ""),
                    "explanation": p.get("explanation", ""),
                    "order": p.get("order", i),
                }
                for i, p in enumerate(prompts)
            ]

        elif mtype == "trace_path":
            config = {
                "particleSpeed": content.get("particleSpeed", "medium"),
                "showParticle": True,
                "pathStyle": "solid",
            }
            # Content has: path_type, drawing_mode, particleTheme, particleSpeed,
            # color_transition_enabled, show_direction_arrows,
            # show_waypoint_labels, show_full_flow_on_complete, submit_mode
            for key in ("path_type", "drawing_mode", "particleTheme",
                        "color_transition_enabled", "show_direction_arrows",
                        "show_waypoint_labels", "show_full_flow_on_complete",
                        "submit_mode"):
                if key in content:
                    config[key] = content[key]
            scene_bp["tracePathConfig"] = config

            # paths AT ROOT
            paths = content.get("paths", [])
            scene_bp["paths"] = [
                {
                    "id": f"path_s{scene_number}_{i}",
                    "label": p.get("label", ""),
                    "description": p.get("description", ""),
                    "color": p.get("color", "#4A90D9"),
                    "requiresOrder": p.get("requiresOrder", True),
                    "waypoints": [
                        {
                            "id": f"wp_s{scene_number}_{i}_{wi}",
                            "label": wp.get("label", ""),
                            "zoneId": label_to_zone_id.get(wp.get("label", ""), ""),
                            "order": wp.get("order", wi),
                        }
                        for wi, wp in enumerate(p.get("waypoints", []))
                    ],
                }
                for i, p in enumerate(paths)
            ]

        elif mtype == "sequencing":
            config = {
                "items": content.get("items", []),
                "correct_order": content.get("correct_order", []),
                "sequence_type": content.get("sequence_type", "ordered"),
                "layout_mode": content.get("layout_mode", "vertical_list"),
            }
            # Content has: interaction_pattern, card_type, connector_style,
            # show_position_numbers, allow_partial_credit
            for key in ("interaction_pattern", "card_type", "connector_style",
                        "show_position_numbers", "allow_partial_credit"):
                if key in content:
                    config[key] = content[key]
            scene_bp["sequenceConfig"] = config

        elif mtype == "sorting_categories":
            config = {
                "categories": content.get("categories", []),
                "items": content.get("items", []),
            }
            # Content has: sort_mode, item_card_type, container_style,
            # submit_mode, allow_multi_category, show_category_hints,
            # allow_partial_credit
            for key in ("sort_mode", "item_card_type", "container_style",
                        "submit_mode", "allow_multi_category",
                        "show_category_hints", "allow_partial_credit"):
                if key in content:
                    config[key] = content[key]
            scene_bp["sortingConfig"] = config

        elif mtype == "memory_match":
            config = {
                "pairs": content.get("pairs", []),
                "game_variant": content.get("game_variant", "classic"),
                "gridSize": content.get("gridSize") or _auto_grid(len(content.get("pairs", []))),
            }
            # Content has: match_type, card_back_style, matched_card_behavior,
            # show_explanation_on_match, flip_duration_ms, show_attempts_counter
            for key in ("match_type", "card_back_style", "matched_card_behavior",
                        "show_explanation_on_match", "flip_duration_ms",
                        "show_attempts_counter"):
                if key in content:
                    config[key] = content[key]
            scene_bp["memoryMatchConfig"] = config

        elif mtype == "branching_scenario":
            config = {
                "nodes": content.get("nodes", []),
                "startNodeId": content.get("startNodeId", ""),
            }
            # Content has: narrative_structure, show_path_taken,
            # allow_backtrack, show_consequences, multiple_valid_endings
            for key in ("narrative_structure", "show_path_taken",
                        "allow_backtrack", "show_consequences",
                        "multiple_valid_endings"):
                if key in content:
                    config[key] = content[key]
            scene_bp["branchingConfig"] = config

        elif mtype == "description_matching":
            descriptions = content.get("descriptions", {})
            # Re-key from label text -> zone_id (case-insensitive fallback)
            label_to_zone_lower = {k.strip().lower(): v for k, v in label_to_zone_id.items()}
            desc_by_zone: dict[str, str] = {}
            for label_text, desc in descriptions.items():
                zid = label_to_zone_id.get(label_text, "")
                if not zid:
                    zid = label_to_zone_lower.get(label_text.strip().lower(), "")
                if zid:
                    desc_by_zone[zid] = desc
                else:
                    logger.warning(f"description_matching: no zone found for key '{label_text}'")

            config = {
                "descriptions": desc_by_zone,
                "mode": content.get("mode", "click_zone"),
            }
            # Content has: distractor_descriptions, show_connecting_lines,
            # defer_evaluation, description_panel_position
            for key in ("distractor_descriptions", "show_connecting_lines",
                        "defer_evaluation", "description_panel_position"):
                if key in content:
                    config[key] = content[key]
            scene_bp["descriptionMatchingConfig"] = config

            # Also populate zones[].description for dual source (audit 41 DM-4)
            for zone in zones:
                zid = zone.get("id", "")
                if zid in desc_by_zone:
                    zone["description"] = desc_by_zone[zid]

        elif mtype == "compare_contrast":
            config = {}
            # Content has: subject_a, subject_b, expected_categories,
            # comparison_mode, highlight_matching, category_types,
            # category_labels, category_colors, exploration_enabled,
            # zoom_enabled
            if isinstance(content, dict):
                config.update(content)
            scene_bp["compareConfig"] = config


# ── Null-removal pass ────────────────────────────────────────────
#
# Zod's .optional() accepts undefined but rejects null. Pydantic serializes
# Optional[T] = None as JSON null. This pass strips nulls from the blueprint
# so the frontend Zod schemas don't reject valid optional-but-absent fields.
# Root-cause fixes are in the upstream schemas/prompts; this is defense-in-depth.

_VALID_LABEL_STYLES = {"text", "text_with_icon", "text_with_thumbnail", "text_with_description"}


def _sanitize_blueprint(bp: dict[str, Any]) -> None:
    """Strip null values and fix remaining LLM deviations from Zod enums."""
    # Strip nulls from dragDropConfig (Pydantic Optional[int]=None → null)
    ddc = bp.get("dragDropConfig")
    if isinstance(ddc, dict):
        for key in list(ddc.keys()):
            if ddc[key] is None:
                del ddc[key]
        # Defensive: LLM may still deviate from label_style enum
        ls = ddc.get("label_style")
        if ls and ls not in _VALID_LABEL_STYLES:
            logger.warning(f"Invalid label_style '{ls}', fixing to 'text'")
            ddc["label_style"] = "text"

    # Strip nulls from modeTransitions
    for trans in bp.get("modeTransitions", []):
        if isinstance(trans, dict):
            for key in list(trans.keys()):
                if trans[key] is None:
                    del trans[key]

    # Defensive: misconceptions "trigger" → "trigger_label" (in case LLM ignores prompt)
    for mech in bp.get("mechanics", []):
        fb = mech.get("feedback")
        if isinstance(fb, dict):
            for mc in fb.get("misconceptions", []):
                if isinstance(mc, dict) and "trigger" in mc and "trigger_label" not in mc:
                    mc["trigger_label"] = mc.pop("trigger")

    # Recurse into game_sequence scenes
    gs = bp.get("game_sequence")
    if isinstance(gs, dict):
        for scene in gs.get("scenes", []):
            if isinstance(scene, dict):
                _sanitize_blueprint(scene)


# ── Hierarchy enrichment ─────────────────────────────────────────

def _enrich_with_hierarchy(
    blueprint: dict[str, Any],
    hierarchy: dict[str, list[str]],
    suggested_reveal_order: list[str] | None = None,
) -> None:
    """Enrich zones with hierarchy metadata for progressive reveal.

    Only applies to drag_drop and click_to_identify mechanics.
    Sets hierarchyLevel, parentZoneId, childZoneIds on zones,
    and builds zoneGroups[] + temporalConstraints[] on the blueprint.

    Args:
        blueprint: The assembled blueprint dict (mutated in-place).
        hierarchy: DK hierarchical_relationships, e.g. {"Cytoplasm": ["Nucleus", "Vacuole"]}.
        suggested_reveal_order: Optional ordered list of labels (outermost first).
    """
    # Check if current mechanics include zone-based ones that benefit from hierarchy
    mechanics = blueprint.get("mechanics", [])
    zone_mechanic_types = {"drag_drop", "click_to_identify"}
    has_zone_mechanic = any(m.get("type") in zone_mechanic_types for m in mechanics)
    if not has_zone_mechanic:
        return

    zones = blueprint.get("diagram", {}).get("zones", [])
    if not zones:
        return

    # Build label→zone_id map from existing zones
    label_to_zone: dict[str, dict[str, Any]] = {}
    zone_by_id: dict[str, dict[str, Any]] = {}
    for z in zones:
        label = (z.get("label") or "").strip()
        if label:
            label_to_zone[label] = z
            label_to_zone[label.lower()] = z
        zone_by_id[z["id"]] = z

    # Build child→parent map (only for labels that exist as zones)
    child_to_parent: dict[str, str] = {}
    parent_to_children: dict[str, list[str]] = {}
    for parent_label, child_labels in hierarchy.items():
        parent_zone = label_to_zone.get(parent_label) or label_to_zone.get(parent_label.lower())
        if not parent_zone:
            continue
        parent_id = parent_zone["id"]
        if not isinstance(child_labels, list):
            continue
        for child_label in child_labels:
            child_zone = label_to_zone.get(child_label) or label_to_zone.get(child_label.lower())
            if not child_zone:
                continue
            child_id = child_zone["id"]
            child_to_parent[child_id] = parent_id
            parent_to_children.setdefault(parent_id, []).append(child_id)

    if not child_to_parent:
        logger.info("_enrich_with_hierarchy: no matching zone pairs found in hierarchy")
        return

    # Compute hierarchy levels via BFS from roots
    # Roots = zones that are parents but not children (among the detected zones)
    all_parents = set(parent_to_children.keys())
    all_children = set(child_to_parent.keys())
    roots = all_parents - all_children

    # Also add zones that appear in neither parent nor child (standalone, level 1)
    grouped_zone_ids = all_parents | all_children
    level_map: dict[str, int] = {}

    # BFS from roots
    queue: list[tuple[str, int]] = [(r, 1) for r in roots]
    while queue:
        zone_id, level = queue.pop(0)
        if zone_id in level_map:
            continue
        level_map[zone_id] = level
        for child_id in parent_to_children.get(zone_id, []):
            if child_id not in level_map:
                queue.append((child_id, level + 1))

    # Set zone properties
    for z in zones:
        zid = z["id"]
        if zid in level_map:
            z["hierarchyLevel"] = level_map[zid]
        else:
            z["hierarchyLevel"] = 1  # Not in hierarchy = root level

        if zid in child_to_parent:
            z["parentZoneId"] = child_to_parent[zid]

        if zid in parent_to_children:
            z["childZoneIds"] = parent_to_children[zid]

    # Build zoneGroups[]
    zone_groups: list[dict[str, Any]] = []
    for parent_id, children_ids in parent_to_children.items():
        parent_zone = zone_by_id.get(parent_id)
        group_id = f"group_{parent_id}"
        zone_groups.append({
            "id": group_id,
            "parentZoneId": parent_id,
            "childZoneIds": children_ids,
            "revealTrigger": "complete_parent",
            "label": parent_zone.get("label", "") if parent_zone else "",
        })

    blueprint["zoneGroups"] = zone_groups

    # Build temporalConstraints[] — child visible only after parent is labeled
    temporal_constraints: list[dict[str, Any]] = []
    for child_id, parent_id in child_to_parent.items():
        temporal_constraints.append({
            "constraint_type": "after",
            "zone_a": child_id,
            "zone_b": parent_id,
            "description": f"Zone {child_id} visible after {parent_id} is labeled",
        })

    blueprint["temporalConstraints"] = temporal_constraints

    # Build revealOrder from suggested_reveal_order or BFS level-order
    if suggested_reveal_order:
        reveal_order: list[str] = []
        for label in suggested_reveal_order:
            z = label_to_zone.get(label) or label_to_zone.get(label.lower())
            if z:
                reveal_order.append(z["id"])
        # Append any zones not in the suggested order
        for z in zones:
            if z["id"] not in reveal_order:
                reveal_order.append(z["id"])
        blueprint["revealOrder"] = reveal_order
    else:
        # BFS level-order
        ordered = sorted(zones, key=lambda z: (z.get("hierarchyLevel", 1), z.get("label", "")))
        blueprint["revealOrder"] = [z["id"] for z in ordered]

    logger.info(
        f"_enrich_with_hierarchy: {len(zone_groups)} groups, "
        f"{len(temporal_constraints)} constraints, "
        f"levels={set(level_map.values())}"
    )


# ── Sibling overlap fix ──────────────────────────────────────────

def _zone_bbox(zone: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Get (min_x, min_y, max_x, max_y) from zone points or x/y/radius."""
    pts = zone.get("points")
    if pts and len(pts) >= 3:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))
    x = zone.get("x")
    y = zone.get("y")
    r = zone.get("radius", 5)
    if x is not None and y is not None:
        return (x - r, y - r, x + r, y + r)
    return None


def _bbox_overlap_fraction(a: tuple, b: tuple) -> tuple[float, float]:
    """Return (overlap_as_fraction_of_a, overlap_as_fraction_of_b)."""
    x_overlap = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    y_overlap = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    overlap_area = x_overlap * y_overlap
    a_area = max((a[2] - a[0]) * (a[3] - a[1]), 0.01)
    b_area = max((b[2] - b[0]) * (b[3] - b[1]), 0.01)
    return (overlap_area / a_area, overlap_area / b_area)


def _fix_overlapping_siblings(blueprint: dict[str, Any]) -> None:
    """Detect sibling zones with >80% bbox overlap and offset the smaller one.

    Converts the smaller overlapping zone to a point zone placed at a clear
    offset from the larger zone's center.
    """
    zones = blueprint.get("diagram", {}).get("zones", [])
    if len(zones) < 2:
        return

    zone_by_id = {z["id"]: z for z in zones}

    # Group zones by parentZoneId (siblings share the same parent)
    siblings: dict[str | None, list[dict[str, Any]]] = {}
    for z in zones:
        parent = z.get("parentZoneId")
        siblings.setdefault(parent, []).append(z)

    fixed_count = 0
    for parent_id, group in siblings.items():
        if len(group) < 2:
            continue

        # Check all pairs
        checked: set[tuple[str, str]] = set()
        for i, za in enumerate(group):
            bbox_a = _zone_bbox(za)
            if not bbox_a:
                continue
            for j, zb in enumerate(group):
                if i >= j:
                    continue
                pair_key = (za["id"], zb["id"])
                if pair_key in checked:
                    continue
                checked.add(pair_key)

                bbox_b = _zone_bbox(zb)
                if not bbox_b:
                    continue

                frac_a, frac_b = _bbox_overlap_fraction(bbox_a, bbox_b)
                if frac_a < 0.8 and frac_b < 0.8:
                    continue

                # Overlap detected — convert the smaller one to a point zone
                area_a = (bbox_a[2] - bbox_a[0]) * (bbox_a[3] - bbox_a[1])
                area_b = (bbox_b[2] - bbox_b[0]) * (bbox_b[3] - bbox_b[1])
                larger, smaller = (za, zb) if area_a >= area_b else (zb, za)
                larger_bbox = _zone_bbox(larger)

                # Place the smaller zone as a point offset from the larger zone's edge
                lg_cx = (larger_bbox[0] + larger_bbox[2]) / 2
                lg_cy = (larger_bbox[1] + larger_bbox[3]) / 2
                lg_w = larger_bbox[2] - larger_bbox[0]

                # Offset to the right of the larger zone (or left if near the right edge)
                offset_x = lg_w * 0.6
                new_x = lg_cx + offset_x
                if new_x > 90:
                    new_x = lg_cx - offset_x
                new_y = lg_cy

                logger.info(
                    f"_fix_overlapping_siblings: '{smaller.get('label')}' overlaps "
                    f"'{larger.get('label')}' ({frac_a:.0%}/{frac_b:.0%}), "
                    f"offsetting to ({new_x:.1f}, {new_y:.1f})"
                )

                # Convert to point zone
                smaller["x"] = round(new_x, 1)
                smaller["y"] = round(new_y, 1)
                smaller["radius"] = 3
                smaller["shape"] = "circle"
                smaller["zone_type"] = "point"
                smaller.pop("points", None)
                smaller.pop("width", None)
                smaller.pop("height", None)
                if "center" in smaller:
                    smaller["center"] = {"x": new_x, "y": new_y}
                fixed_count += 1

    if fixed_count:
        logger.info(f"_fix_overlapping_siblings: fixed {fixed_count} overlapping zone(s)")


# ── Helpers ──────────────────────────────────────────────────────

def _index_by_scene(contents: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group mechanic contents by scene_id."""
    result: dict[str, list[dict[str, Any]]] = {}
    for c in contents:
        sid = c.get("scene_id", "")
        result.setdefault(sid, []).append(c)
    return result


def _build_narrative(game_plan: dict[str, Any]) -> str:
    """Build narrative intro from game plan fields."""
    # Prefer explicit narrative_intro from the 3-stage cascade
    narrative = game_plan.get("narrative_intro", "")
    if narrative:
        return narrative
    # Fallback: build from title + learning goals
    parts = [game_plan.get("title", "")]
    for scene in game_plan.get("scenes", []):
        goal = scene.get("learning_goal", "")
        if goal:
            parts.append(goal)
    return ". ".join(p for p in parts if p)


def _first_points_per_item(game_plan: dict[str, Any]) -> int:
    """Get points_per_item from the first mechanic (for scoringStrategy default)."""
    for scene in game_plan.get("scenes", []):
        for mech in scene.get("mechanics", []):
            return mech.get("points_per_item", 10)
    return 10


def _find_timed_mechanic(game_plan: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Find first timed mechanic in the game plan."""
    for scene in game_plan.get("scenes", []):
        for mech in scene.get("mechanics", []):
            if mech.get("is_timed"):
                return mech
    return None


def _build_zones(
    detected_zones: list[dict[str, Any]],
    label_to_zone_id: dict[str, str],
    zone_labels: list[str],
    scene_number: int,
) -> list[dict[str, Any]]:
    """Build zones array for blueprint from detected zones."""
    zones: list[dict[str, Any]] = []
    zone_id_set: set[str] = set()

    for zone in detected_zones:
        zone_label = zone.get("label") or zone.get("name") or ""
        zid = zone.get("id") or label_to_zone_id.get(zone_label) or generate_zone_id(scene_number, zone_label)

        if zid in zone_id_set:
            continue
        zone_id_set.add(zid)

        zone_entry: dict[str, Any] = {
            "id": zid,
            "label": zone_label,
            "points": zone.get("points", []),
        }
        # Only include numeric fields when they have actual values (Zod rejects null)
        for key in ("x", "y", "radius", "width", "height"):
            val = zone.get(key)
            if val is not None:
                zone_entry[key] = val

        # Preserve detection metadata (required for frontend polygon rendering).
        # shape: 'polygon'|'circle'|'rect' — DiagramCanvas uses z.shape==='polygon'
        #        to choose polygon SVG path vs circle/rect fallback.
        # center: {x, y} — centroid for label positioning.
        # description, hint, confidence — enrichment fields from detection.
        for key in ("shape", "center", "description", "hint", "confidence"):
            val = zone.get(key)
            if val is not None and val != "":
                zone_entry[key] = val

        zones.append(zone_entry)

    return zones


def _build_labels(
    zone_labels: list[str],
    label_to_zone_id: dict[str, str],
    scene_number: int,
) -> list[dict[str, Any]]:
    """Build labels array for blueprint."""
    return [
        {
            "id": generate_label_id(scene_number, i),
            "text": label,
            "correctZoneId": label_to_zone_id.get(label, generate_zone_id(scene_number, label)),
        }
        for i, label in enumerate(zone_labels)
    ]


def _label_id_for(target_label: str, label_to_zone_id: dict[str, str], scene_number: int) -> str:
    """Get label ID for a target_label in identification prompts."""
    # Labels are indexed by position in zone_labels
    # This is a best-effort lookup — assembler node can refine
    return label_to_zone_id.get(target_label, generate_zone_id(scene_number, target_label))


def _resolve_transition_types(
    transitions: list[dict[str, Any]],
    mech_id_to_type: dict[str, str],
) -> list[dict[str, Any]]:
    """Resolve mechanic IDs to mechanic types in transition from/to fields.

    Interaction designer outputs s1_m0/s1_m1 but frontend ModeTransition
    expects InteractionMode strings like drag_drop/description_matching.
    """
    resolved = []
    for t in transitions:
        resolved_t = dict(t)
        from_val = t.get("from", "")
        to_val = t.get("to", "")
        if from_val in mech_id_to_type:
            resolved_t["from"] = mech_id_to_type[from_val]
        if to_val in mech_id_to_type:
            resolved_t["to"] = mech_id_to_type[to_val]
        resolved.append(resolved_t)
    return resolved


def _build_transitions(
    scene: dict[str, Any],
    mechanics_plans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build modeTransitions from mechanic_connections."""
    connections = scene.get("mechanic_connections", [])
    mech_map = {m.get("mechanic_id"): m for m in mechanics_plans}
    transitions: list[dict[str, Any]] = []

    for conn in connections:
        from_mech = mech_map.get(conn.get("from_mechanic_id", ""))
        to_mech = mech_map.get(conn.get("to_mechanic_id", ""))
        if not from_mech or not to_mech:
            continue

        from_type = from_mech.get("mechanic_type", "")
        to_type = to_mech.get("mechanic_type", "")
        # MechanicConnection has "trigger" (already resolved by graph_builder)
        trigger = conn.get("trigger", "")
        if not trigger:
            # Fallback: resolve from trigger_hint if present (legacy compat)
            trigger_hint = conn.get("trigger_hint", "completion")
            trigger = resolve_trigger(trigger_hint, from_type)

        transition: dict[str, Any] = {
            "from": from_type,
            "to": to_type,
            "trigger": trigger,
            "animation": "fade",
        }
        # Only include optional fields when they have actual values (Zod rejects null)
        trigger_value = conn.get("trigger_value")
        if trigger_value is not None:
            transition["trigger_value"] = trigger_value
        message = conn.get("message")
        if message:
            transition["message"] = message
        transitions.append(transition)

    return transitions


def _scene_to_game_scene(scene_bp: dict[str, Any], index: int) -> dict[str, Any]:
    """Convert scene blueprint fragment to GameScene format for game_sequence.

    Must populate ALL fields the frontend GameScene interface requires:
    scene_number, narrative_intro, max_score, mechanics[], zones[],
    mode_transitions[], plus per-mechanic configs.
    """
    mechanics = scene_bp.get("_mechanics", [])
    transitions = scene_bp.get("_transitions", [])

    game_scene: dict[str, Any] = {
        "scene_id": scene_bp.get("scene_id", ""),
        "scene_number": scene_bp.get("_scene_number", index + 1),
        "title": scene_bp.get("title", ""),
        "narrative_intro": scene_bp.get("_narrative_intro", ""),
        "learning_goal": scene_bp.get("learning_goal", ""),
        "diagram": scene_bp.get("diagram", {}),
        "zones": scene_bp.get("diagram", {}).get("zones", []),
        "labels": scene_bp.get("labels", []),
        "distractorLabels": scene_bp.get("distractorLabels", []),
        "max_score": scene_bp.get("_scene_max_score", 0),
        "mechanics": mechanics,
        "mode_transitions": transitions,
        "tasks": [],
    }

    # Starting interaction mode from first mechanic
    if mechanics:
        game_scene["interaction_mode"] = mechanics[0].get("type", "drag_drop")

    # Copy mechanic configs (camelCase — frontend expects camelCase)
    for key in _CONFIG_KEYS:
        if key in scene_bp:
            game_scene[key] = scene_bp[key]

    if "identificationPrompts" in scene_bp:
        game_scene["identificationPrompts"] = scene_bp["identificationPrompts"]
    if "paths" in scene_bp:
        game_scene["paths"] = scene_bp["paths"]

    return game_scene


def _auto_grid(pair_count: int) -> list[int]:
    """Auto-calculate grid size for memory match."""
    total_cards = pair_count * 2
    if total_cards <= 8:
        return [2, total_cards // 2]
    if total_cards <= 12:
        return [3, total_cards // 3]
    if total_cards <= 16:
        return [4, 4]
    return [4, (total_cards + 3) // 4]
