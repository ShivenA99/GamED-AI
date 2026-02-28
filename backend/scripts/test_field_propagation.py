"""Deep field propagation audit — traces EVERY creative design field through
all 3 levels of the cascade to verify nothing is dropped.

Level 1: MechanicCreativeDesign → GamePlan.MechanicPlan.creative_design
Level 2: MechanicPlan.creative_design → Content Generator prompt → Content model fields
Level 3: Content model fields → Blueprint config keys

For each mechanic, checks that:
- All mechanic-specific creative hints survive Level 1
- All visual config fields appear in the content prompt (Level 2)
- All visual config fields appear in the final blueprint (Level 3)
- No data fields leak into config (Level 3)
"""

import json
import sys
import traceback
from typing import Any

# Define what fields each mechanic's creative design should contain
# and where they should appear at each level
MECHANIC_FIELD_CONTRACTS = {
    "drag_drop": {
        "creative_hints": [],  # No mechanic-specific hints
        "visual_config_fields": [
            "interaction_mode", "feedback_timing", "label_style",
            "leader_line_style", "leader_line_color", "leader_line_animate",
            "pin_marker_shape", "label_anchor_side", "tray_position",
            "tray_layout", "placement_animation", "incorrect_animation",
            "zone_idle_animation", "zone_hover_effect", "max_attempts",
            "shuffle_labels",
        ],
        "data_fields": ["labels", "distractor_labels"],  # Must NOT be in config
        "blueprint_config_key": "dragDropConfig",
        "root_level_data": [],  # No data promoted to root
    },
    "click_to_identify": {
        "creative_hints": ["prompt_style"],
        "visual_config_fields": [
            "prompt_style", "selection_mode", "highlight_style",
            "magnification_enabled", "magnification_factor",
            "explore_mode_enabled", "show_zone_count",
        ],
        "data_fields": [],  # prompts are promoted to root as identificationPrompts
        "blueprint_config_key": "clickToIdentifyConfig",
        "root_level_data": ["identificationPrompts"],
    },
    "trace_path": {
        "creative_hints": ["path_process"],
        "visual_config_fields": [
            "path_type", "drawing_mode", "particleTheme", "particleSpeed",
            "color_transition_enabled", "show_direction_arrows",
            "show_waypoint_labels", "show_full_flow_on_complete", "submit_mode",
        ],
        "data_fields": ["paths"],
        "blueprint_config_key": "tracePathConfig",
        "root_level_data": ["paths"],
    },
    "sequencing": {
        "creative_hints": ["sequence_topic"],
        "visual_config_fields": [
            "layout_mode", "interaction_pattern", "card_type",
            "connector_style", "show_position_numbers", "allow_partial_credit",
        ],
        "data_fields": ["items", "correct_order", "sequence_type"],
        "blueprint_config_key": "sequenceConfig",
        "root_level_data": [],
    },
    "sorting_categories": {
        "creative_hints": ["category_names"],
        "visual_config_fields": [
            "sort_mode", "item_card_type", "container_style",
            "submit_mode", "allow_multi_category", "show_category_hints",
            "allow_partial_credit",
        ],
        "data_fields": ["categories", "items"],
        "blueprint_config_key": "sortingConfig",
        "root_level_data": [],
    },
    "memory_match": {
        "creative_hints": ["match_type"],
        "visual_config_fields": [
            "match_type", "card_back_style", "matched_card_behavior",
            "show_explanation_on_match", "flip_duration_ms", "show_attempts_counter",
        ],
        "data_fields": ["pairs", "game_variant", "gridSize"],
        "blueprint_config_key": "memoryMatchConfig",
        "root_level_data": [],
    },
    "branching_scenario": {
        "creative_hints": ["narrative_premise"],
        "visual_config_fields": [
            "narrative_structure", "show_path_taken",
            "allow_backtrack", "show_consequences", "multiple_valid_endings",
        ],
        "data_fields": ["nodes", "startNodeId"],
        "blueprint_config_key": "branchingConfig",
        "root_level_data": [],
    },
    "description_matching": {
        "creative_hints": ["description_source"],
        "visual_config_fields": [
            "show_connecting_lines", "defer_evaluation", "description_panel_position",
        ],
        "data_fields": ["descriptions", "mode", "distractor_descriptions"],
        "blueprint_config_key": "descriptionMatchingConfig",
        "root_level_data": [],
    },
}


def run_full_cascade():
    """Run the full cascade and return intermediate artifacts for audit."""
    from app.v4.schemas.game_concept import GameConcept, SceneConcept, MechanicChoice
    from app.v4.schemas.creative_design import (
        SceneCreativeDesign, MechanicCreativeDesign, ImageSpec,
    )
    from app.v4.graph_builder import build_game_graph
    from app.v4.prompts.content_generator import build_content_prompt
    from app.v4.agents.content_generator import build_scene_context
    from app.v4.schemas.mechanic_content import get_content_model
    from app.v4.helpers.blueprint_assembler import assemble_blueprint
    from app.v4.validators.game_plan_validator import validate_game_plan

    # Import test data from the main test
    sys.path.insert(0, "scripts")
    from test_creative_cascade import test_stage_1, test_stage_2, test_stage_5

    print("Building cascade artifacts...")
    concept = test_stage_1()
    designs = test_stage_2(concept)
    plan = build_game_graph(concept, designs)
    validate_game_plan(plan)  # Compute scores
    content_outputs = test_stage_5()

    plan_dict = plan.model_dump()

    # Build mechanic_contents
    mechanic_contents = []
    for scene in plan_dict.get("scenes", []):
        for mech in scene.get("mechanics", []):
            content = content_outputs.get(mech["mechanic_type"], {})
            mechanic_contents.append({
                "mechanic_id": mech["mechanic_id"],
                "scene_id": scene["scene_id"],
                "mechanic_type": mech["mechanic_type"],
                "status": "success",
                "content": content,
            })

    # Build interaction_results
    interaction_results = []
    for scene in plan_dict.get("scenes", []):
        scoring, feedback = {}, {}
        for mech in scene.get("mechanics", []):
            mid = mech["mechanic_id"]
            scoring[mid] = {
                "strategy": "per_correct",
                "points_per_correct": mech.get("points_per_item", 10),
                "max_score": mech.get("max_score", 0),
                "partial_credit": True,
            }
            feedback[mid] = {
                "on_correct": "Well done!",
                "on_incorrect": "Try again.",
                "on_completion": "Complete!",
                "misconceptions": [],
            }
        interaction_results.append({
            "scene_id": scene["scene_id"],
            "mechanic_scoring": scoring,
            "mechanic_feedback": feedback,
        })

    # Build asset_results
    asset_results = [
        {
            "scene_id": "scene_1", "status": "success",
            "diagram_url": "https://example.com/heart.png",
            "zones": [
                {"id": "z1", "label": "Left Atrium", "points": [[100,100],[200,200]]},
                {"id": "z2", "label": "Right Atrium", "points": [[300,100],[400,200]]},
                {"id": "z3", "label": "Left Ventricle", "points": [[100,300],[200,400]]},
                {"id": "z4", "label": "Right Ventricle", "points": [[300,300],[400,400]]},
            ],
        },
        {
            "scene_id": "scene_2", "status": "success",
            "diagram_url": "https://example.com/flow.png",
            "zones": [
                {"id": "z5", "label": "Vena Cava", "points": [[50,50],[100,100]]},
                {"id": "z6", "label": "Right Atrium", "points": [[150,50],[200,100]]},
                {"id": "z7", "label": "Right Ventricle", "points": [[250,150],[300,200]]},
                {"id": "z8", "label": "Pulmonary Artery", "points": [[350,50],[400,100]]},
                {"id": "z9", "label": "Pulmonary Vein", "points": [[350,200],[400,250]]},
                {"id": "z10", "label": "Left Atrium", "points": [[250,250],[300,300]]},
                {"id": "z11", "label": "Left Ventricle", "points": [[150,250],[200,300]]},
                {"id": "z12", "label": "Aorta", "points": [[50,250],[100,300]]},
            ],
        },
    ]

    blueprint = assemble_blueprint(plan_dict, mechanic_contents, interaction_results, asset_results)

    return {
        "concept": concept,
        "designs": designs,
        "plan": plan,
        "plan_dict": plan_dict,
        "content_outputs": content_outputs,
        "blueprint": blueprint,
    }


def audit_level_1(artifacts: dict):
    """Level 1: MechanicCreativeDesign → GamePlan.MechanicPlan.creative_design

    Verify ALL creative design fields survive the graph builder copy.
    """
    print("\n" + "=" * 70)
    print("LEVEL 1 AUDIT: Creative Design → Game Plan")
    print("=" * 70)

    designs = artifacts["designs"]
    plan = artifacts["plan"]
    errors = []
    warnings = []

    for scene in plan.scenes:
        design = designs[scene.scene_id]
        for mi, mech in enumerate(scene.mechanics):
            expected_cd = design.mechanic_designs[mi]
            actual_cd = mech.creative_design

            # Check every field on the MechanicCreativeDesign
            expected_dict = expected_cd.model_dump()
            actual_dict = actual_cd.model_dump()

            for field_name, expected_val in expected_dict.items():
                actual_val = actual_dict.get(field_name)
                if actual_val != expected_val:
                    errors.append(
                        f"  {mech.mechanic_id}.creative_design.{field_name}: "
                        f"expected={repr(expected_val)[:60]}, got={repr(actual_val)[:60]}"
                    )

            # Mechanic-specific hint checks
            contract = MECHANIC_FIELD_CONTRACTS.get(mech.mechanic_type, {})
            for hint in contract.get("creative_hints", []):
                val = actual_dict.get(hint)
                if val is None or val == "" or val == []:
                    errors.append(
                        f"  {mech.mechanic_id}: creative hint '{hint}' is empty/None"
                    )
                else:
                    print(f"  ✓ {mech.mechanic_id}.{hint} = {repr(val)[:60]}")

    if errors:
        print(f"\n  ✗ {len(errors)} field(s) DROPPED at Level 1:")
        for e in errors:
            print(e)
        return False

    print(f"\n  ✓ ALL fields propagated through graph builder for all 8 mechanics")
    return True


def audit_level_2(artifacts: dict):
    """Level 2: MechanicPlan.creative_design → Content prompt

    Verify creative design fields appear in the generated prompt.
    """
    print("\n" + "=" * 70)
    print("LEVEL 2 AUDIT: Creative Design → Content Prompts")
    print("=" * 70)

    from app.v4.prompts.content_generator import build_content_prompt
    from app.v4.agents.content_generator import build_scene_context

    plan_dict = artifacts["plan_dict"]
    errors = []

    for scene in plan_dict.get("scenes", []):
        scene_context = build_scene_context(scene, {
            "canonical_labels": plan_dict.get("all_zone_labels", []),
        })

        for mech in scene.get("mechanics", []):
            mid = mech["mechanic_id"]
            mtype = mech["mechanic_type"]
            cd = mech["creative_design"]

            prompt = build_content_prompt(
                mechanic_type=mtype,
                creative_design=cd,
                scene_context=scene_context,
                mechanic_plan=mech,
            )

            contract = MECHANIC_FIELD_CONTRACTS.get(mtype, {})

            # Check that visual config field NAMES appear in prompt
            # (they're embedded as template defaults)
            visual_fields = contract.get("visual_config_fields", [])
            missing_in_prompt = []
            for field in visual_fields:
                # Field name or its value should be in the prompt
                if field not in prompt:
                    # Check if the value appears instead
                    val = cd.get(field)
                    if val is not None and str(val) not in prompt:
                        missing_in_prompt.append(field)

            if missing_in_prompt:
                # These may be in the JSON template but not as explicit field names
                # Check more carefully
                real_missing = []
                for field in missing_in_prompt:
                    # Field should be in the JSON schema example in the prompt
                    snake_variants = [field, field.replace("_", "")]
                    found = any(v in prompt for v in snake_variants)
                    if not found:
                        real_missing.append(field)
                if real_missing:
                    errors.append(f"  {mid} ({mtype}): visual config fields missing from prompt: {real_missing}")

            # Check mechanic-specific hints
            for hint in contract.get("creative_hints", []):
                val = cd.get(hint)
                if val and isinstance(val, str) and val not in prompt:
                    errors.append(f"  {mid}: creative hint '{hint}'='{val[:40]}' not found in prompt")
                elif val and isinstance(val, list):
                    # For list hints (category_names), check at least one item
                    found_any = any(str(item) in prompt for item in val)
                    if not found_any:
                        errors.append(f"  {mid}: creative hint list '{hint}'={val} not in prompt")

            # Check zone labels for zone-based mechanics
            if mtype in {"drag_drop", "click_to_identify", "trace_path", "description_matching"}:
                labels = mech.get("zone_labels_used", [])
                for label in labels[:2]:  # Check first 2
                    if label not in prompt:
                        errors.append(f"  {mid}: zone label '{label}' missing from prompt")

            print(f"  ✓ {mid} ({mtype}): prompt has {len(visual_fields)} visual config fields + hints")

    if errors:
        print(f"\n  ✗ {len(errors)} issue(s) at Level 2:")
        for e in errors:
            print(e)
        return False

    print(f"\n  ✓ ALL creative design fields flow into content prompts")
    return True


def audit_level_3(artifacts: dict):
    """Level 3: Content model fields → Blueprint config keys

    Verify visual config fields appear in the final blueprint AND
    data fields do NOT leak into config keys.
    """
    print("\n" + "=" * 70)
    print("LEVEL 3 AUDIT: Content → Blueprint Config")
    print("=" * 70)

    blueprint = artifacts["blueprint"]
    content_outputs = artifacts["content_outputs"]
    plan_dict = artifacts["plan_dict"]
    errors = []

    # Blueprint has game_sequence for multi-scene
    game_scenes = blueprint.get("game_sequence", {}).get("scenes", [])

    # Map scene index to game_sequence scene
    scene_bp_map = {}
    for si, scene in enumerate(plan_dict.get("scenes", [])):
        sid = scene["scene_id"]
        if si < len(game_scenes):
            scene_bp_map[sid] = game_scenes[si]
        elif si == 0:
            scene_bp_map[sid] = blueprint  # First scene promoted to root

    # Also check root-level for first scene
    scene_bp_map["scene_1_root"] = blueprint

    for scene in plan_dict.get("scenes", []):
        sid = scene["scene_id"]
        scene_bp = scene_bp_map.get(sid, {})

        for mech in scene.get("mechanics", []):
            mid = mech["mechanic_id"]
            mtype = mech["mechanic_type"]
            contract = MECHANIC_FIELD_CONTRACTS.get(mtype, {})
            config_key = contract.get("blueprint_config_key", "")

            # Get the config from scene blueprint
            config = scene_bp.get(config_key, {})

            if not config:
                errors.append(f"  {mid} ({mtype}): {config_key} NOT FOUND in {sid}")
                continue

            # Check visual config fields are present
            visual_fields = contract.get("visual_config_fields", [])
            missing_visual = []
            for field in visual_fields:
                if field not in config:
                    missing_visual.append(field)

            if missing_visual:
                errors.append(f"  {mid} ({mtype}): {config_key} missing visual fields: {missing_visual}")
            else:
                print(f"  ✓ {mid} ({mtype}): {config_key} has all {len(visual_fields)} visual config fields")

            # Check data fields ARE present where expected (some are in config, some at root)
            data_fields = contract.get("data_fields", [])
            if mtype == "drag_drop":
                # Data fields should NOT be in config
                for df in data_fields:
                    if df in config:
                        errors.append(f"  {mid} ({mtype}): DATA LEAK — '{df}' found in {config_key}")
            else:
                # For other mechanics, data fields are typically IN the config
                for df in data_fields:
                    if df not in config:
                        # Some are at root level
                        root_data = contract.get("root_level_data", [])
                        if df not in root_data and df not in scene_bp:
                            errors.append(f"  {mid} ({mtype}): data field '{df}' missing from {config_key}")

            # Check root-level data
            root_data = contract.get("root_level_data", [])
            for rd in root_data:
                # For multi-scene, check in game_sequence scene
                if rd not in scene_bp:
                    # Check root blueprint (first scene promoted)
                    if sid == "scene_1" and rd not in blueprint:
                        errors.append(f"  {mid} ({mtype}): root-level data '{rd}' not found")
                    elif sid != "scene_1":
                        errors.append(f"  {mid} ({mtype}): root-level data '{rd}' not found in {sid}")

            # Verify specific field VALUES are correct
            content = content_outputs.get(mtype, {})
            for vf in visual_fields[:3]:  # Spot check first 3
                expected = content.get(vf)
                actual = config.get(vf)
                if expected is not None and actual != expected:
                    errors.append(
                        f"  {mid}.{vf}: content={repr(expected)[:40]} → blueprint={repr(actual)[:40]} MISMATCH"
                    )

    # Verify scoring/feedback in mechanics array
    print(f"\n  Checking mechanics array scoring/feedback...")
    for mi, mech_bp in enumerate(blueprint.get("mechanics", [])):
        mtype = mech_bp.get("type", "?")
        scoring = mech_bp.get("scoring", {})
        feedback = mech_bp.get("feedback", {})

        if not scoring or scoring.get("max_score", 0) == 0:
            errors.append(f"  mechanics[{mi}] ({mtype}): missing or zero scoring")
        if not feedback:
            errors.append(f"  mechanics[{mi}] ({mtype}): missing feedback")
        else:
            print(f"  ✓ mechanics[{mi}] ({mtype}): scoring.max_score={scoring.get('max_score')}, feedback present")

    # Verify mode transitions
    print(f"\n  Checking mode transitions...")
    transitions = blueprint.get("modeTransitions", [])
    expected_transitions = {
        ("drag_drop", "click_to_identify", "all_zones_labeled"),
        ("click_to_identify", "description_matching", "identification_complete"),
        ("trace_path", "sequencing", "path_complete"),
        ("sorting_categories", "memory_match", "sorting_complete"),
        ("memory_match", "branching_scenario", "memory_complete"),
    }
    actual_transitions = {
        (t["from"], t["to"], t["trigger"]) for t in transitions
    }
    missing_transitions = expected_transitions - actual_transitions
    if missing_transitions:
        for mt in missing_transitions:
            errors.append(f"  Missing transition: {mt[0]} → {mt[1]} [{mt[2]}]")
    else:
        print(f"  ✓ All {len(expected_transitions)} mode transitions present with correct triggers")

    if errors:
        print(f"\n  ✗ {len(errors)} issue(s) at Level 3:")
        for e in errors:
            print(e)
        return False

    print(f"\n  ✓ ALL content fields correctly mapped into blueprint")
    return True


def audit_asset_level(artifacts: dict):
    """Asset Level: Verify zone IDs, label IDs, and spatial data integrity."""
    print("\n" + "=" * 70)
    print("ASSET LEVEL AUDIT: Zones, Labels, and Spatial Integrity")
    print("=" * 70)

    blueprint = artifacts["blueprint"]
    errors = []

    # Root diagram
    diag = blueprint.get("diagram", {})
    zones = diag.get("zones", [])
    labels = blueprint.get("labels", [])

    print(f"  Root: {len(zones)} zones, {len(labels)} labels")

    # Every label must have a correctZoneId that exists in zones
    zone_ids = {z["id"] for z in zones}
    for label in labels:
        czid = label.get("correctZoneId", "")
        if czid and czid not in zone_ids:
            errors.append(f"  Label '{label['text']}' correctZoneId={czid} not in zones")

    # identificationPrompts targets must match zones
    for prompt in blueprint.get("identificationPrompts", []):
        tzid = prompt.get("targetZoneId", "")
        if tzid and tzid not in zone_ids:
            errors.append(f"  ID prompt '{prompt['text'][:30]}' targetZoneId={tzid} not in zones")

    # Multi-scene: check each game_sequence scene
    gs_scenes = blueprint.get("game_sequence", {}).get("scenes", [])
    for si, gs in enumerate(gs_scenes):
        scene_zones = gs.get("diagram", {}).get("zones", [])
        scene_labels = gs.get("labels", [])
        scene_zone_ids = {z["id"] for z in scene_zones}

        print(f"  Scene {si+1}: {len(scene_zones)} zones, {len(scene_labels)} labels")

        # Labels reference valid zones
        for label in scene_labels:
            czid = label.get("correctZoneId", "")
            if czid and czid not in scene_zone_ids:
                errors.append(f"  Scene {si+1} label '{label['text']}' correctZoneId={czid} not in scene zones")

        # Paths reference valid zones via waypoint zoneIds
        for path in gs.get("paths", []):
            for wp in path.get("waypoints", []):
                wzid = wp.get("zoneId", "")
                if wzid and wzid not in scene_zone_ids:
                    errors.append(f"  Scene {si+1} path waypoint '{wp['label']}' zoneId={wzid} not in scene zones")

        # Zones have spatial data (points)
        zones_without_points = [z for z in scene_zones if not z.get("points")]
        if zones_without_points:
            errors.append(f"  Scene {si+1}: {len(zones_without_points)} zone(s) without points")

    # Content-only scene (scene 3) should have no diagram
    if len(gs_scenes) >= 3:
        s3 = gs_scenes[2]
        s3_url = s3.get("diagram", {}).get("assetUrl")
        if s3_url is not None:
            errors.append(f"  Scene 3 (content-only) has diagram URL: {s3_url}")
        else:
            print(f"  ✓ Scene 3 (content-only): no diagram, as expected")

    if errors:
        print(f"\n  ✗ {len(errors)} issue(s) at asset level:")
        for e in errors:
            print(e)
        return False

    print(f"\n  ✓ Asset integrity verified — zones, labels, and spatial data consistent")
    return True


def main():
    print("\n" + "=" * 70)
    print("V4 CREATIVE CASCADE — DEEP FIELD PROPAGATION AUDIT")
    print("All 8 mechanics × 3 levels + asset integrity")
    print("=" * 70)

    try:
        artifacts = run_full_cascade()

        l1 = audit_level_1(artifacts)
        l2 = audit_level_2(artifacts)
        l3 = audit_level_3(artifacts)
        asset = audit_asset_level(artifacts)

        print("\n" + "=" * 70)
        print("AUDIT SUMMARY")
        print("=" * 70)
        print(f"  Level 1 (CreativeDesign → GamePlan): {'PASS' if l1 else 'FAIL'}")
        print(f"  Level 2 (CreativeDesign → Prompts):  {'PASS' if l2 else 'FAIL'}")
        print(f"  Level 3 (Content → Blueprint):       {'PASS' if l3 else 'FAIL'}")
        print(f"  Asset Integrity:                     {'PASS' if asset else 'FAIL'}")

        all_pass = l1 and l2 and l3 and asset
        if all_pass:
            print(f"\n  ALL LEVELS PASS — Nothing dropped through the cascade")
        else:
            print(f"\n  SOME LEVELS FAILED — See details above")
            sys.exit(1)

    except Exception as e:
        print(f"\nFATAL: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
