"""
Design Validator Agent (v3)

Deterministic validation of GameDesignV3 output — NO LLM calls.
Checks schema completeness, internal consistency, label integrity,
mechanic validity, hierarchy soundness, and pedagogical alignment.

Wires into graph.py after game_designer_v3.
On failure: sets validation_issues for retry or human review.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.game_design_v3 import GameDesignV3, validate_game_design
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.design_validator")

# Valid mechanic types (must match frontend InteractionMode)
VALID_MECHANIC_TYPES = {
    "drag_drop", "trace_path", "click_to_identify", "hierarchical",
    "description_matching", "compare_contrast", "sequencing",
    "sorting_categories", "memory_match", "branching_scenario",
    "timed_challenge",
}


def validate_design(design: GameDesignV3) -> Tuple[bool, float, List[str]]:
    """
    Validate a GameDesignV3 instance.

    Returns:
        (is_valid, score, issues)
        - is_valid: True if score >= 0.7 and no fatal issues
        - score: 0.0-1.0 quality score
        - issues: list of issue strings (prefixed FATAL: or WARNING:)
    """
    issues: List[str] = []
    score = 1.0

    # ------------------------------------------------------------------
    # 1. Basic completeness
    # ------------------------------------------------------------------
    if not design.title:
        issues.append("FATAL: Missing game title")
        score -= 0.2

    if not design.scenes:
        issues.append("FATAL: No scenes defined")
        return False, 0.0, issues

    # ------------------------------------------------------------------
    # 2. Label integrity
    # ------------------------------------------------------------------
    if design.labels:
        zone_labels = set(design.labels.zone_labels or [])
        distractor_texts = set()
        if design.labels.distractor_labels:
            distractor_texts = {d.text for d in design.labels.distractor_labels}

        # Check for overlap between zone labels and distractors
        overlap = zone_labels & distractor_texts
        if overlap:
            issues.append(f"WARNING: Labels appear in both zone_labels and distractors: {overlap}")
            score -= 0.1

        # Check zone labels are non-empty
        if len(zone_labels) < 2:
            issues.append(f"WARNING: Only {len(zone_labels)} zone labels. Games need at least 3+.")
            score -= 0.05
    else:
        issues.append("WARNING: No global label design specified")
        score -= 0.1

    # ------------------------------------------------------------------
    # 3. Scene validation
    # ------------------------------------------------------------------
    scene_numbers = []
    all_scene_labels_used = set()

    for scene in design.scenes:
        sn = scene.scene_number
        scene_numbers.append(sn)

        # Must have a title
        if not scene.title:
            issues.append(f"WARNING: Scene {sn} missing title")
            score -= 0.05

        # Must have at least one mechanic
        if not scene.mechanics:
            issues.append(f"FATAL: Scene {sn} has no mechanics")
            score -= 0.2

        # Validate each mechanic
        for mech in scene.mechanics:
            if mech.type not in VALID_MECHANIC_TYPES:
                issues.append(
                    f"FATAL: Scene {sn} mechanic type '{mech.type}' "
                    f"not in valid types: {sorted(VALID_MECHANIC_TYPES)}"
                )
                score -= 0.15

            # Check mechanic-specific requirements
            if mech.type == "trace_path":
                if not mech.path_config:
                    issues.append(f"WARNING: Scene {sn} trace_path mechanic missing path_config")
                    score -= 0.1
                elif not mech.path_config.waypoints:
                    issues.append(f"WARNING: Scene {sn} trace_path needs path_config.waypoints")
                    score -= 0.1

            if mech.type == "click_to_identify":
                if not mech.click_config:
                    issues.append(f"WARNING: Scene {sn} click_to_identify mechanic missing click_config")
                    score -= 0.1
                elif not mech.click_config.prompts and not mech.click_config.click_options:
                    issues.append(f"WARNING: Scene {sn} click_to_identify needs prompts or click_options")
                    score -= 0.1

            if mech.type == "sequencing":
                if not mech.sequence_config:
                    issues.append(f"WARNING: Scene {sn} sequencing mechanic missing sequence_config")
                    score -= 0.1
                elif not mech.sequence_config.correct_order:
                    issues.append(f"WARNING: Scene {sn} sequencing needs sequence_config.correct_order")
                    score -= 0.1

            if mech.type == "description_matching":
                if not mech.description_match_config:
                    issues.append(f"WARNING: Scene {sn} description_matching missing description_match_config")
                    score -= 0.1
                elif not mech.description_match_config.descriptions:
                    issues.append(f"WARNING: Scene {sn} description_matching needs descriptions list")
                    score -= 0.1

            if mech.type == "sorting_categories":
                if not mech.sorting_config:
                    issues.append(f"WARNING: Scene {sn} sorting_categories missing sorting_config")
                    score -= 0.1
                elif not mech.sorting_config.categories or not mech.sorting_config.items:
                    issues.append(f"WARNING: Scene {sn} sorting_categories needs categories and items")
                    score -= 0.1

            if mech.type == "branching_scenario":
                if not mech.branching_config:
                    issues.append(f"WARNING: Scene {sn} branching_scenario missing branching_config")
                    score -= 0.1
                elif not mech.branching_config.nodes:
                    issues.append(f"WARNING: Scene {sn} branching_scenario needs nodes")
                    score -= 0.1

            if mech.type == "memory_match":
                if not mech.memory_config:
                    issues.append(f"WARNING: Scene {sn} memory_match missing memory_config")
                    score -= 0.1
                elif not mech.memory_config.pairs:
                    issues.append(f"WARNING: Scene {sn} memory_match needs pairs")
                    score -= 0.1

            if mech.type == "compare_contrast":
                if not mech.compare_config:
                    issues.append(f"WARNING: Scene {sn} compare_contrast missing compare_config")
                    score -= 0.1
                elif not mech.compare_config.expected_categories:
                    issues.append(f"WARNING: Scene {sn} compare_contrast needs expected_categories")
                    score -= 0.1

            if mech.type == "hierarchical":
                if not (design.labels and design.labels.hierarchy and design.labels.hierarchy.enabled):
                    issues.append(f"WARNING: Scene {sn} hierarchical but labels.hierarchy not enabled")
                    score -= 0.1

            # Track zone labels used
            if mech.zone_labels_used:
                all_scene_labels_used.update(mech.zone_labels_used)

        # Visual spec check
        if scene.visual and not scene.visual.description:
            issues.append(f"WARNING: Scene {sn} visual spec has no description")
            score -= 0.03

    # Scene number sequential check
    expected_numbers = list(range(1, len(design.scenes) + 1))
    if sorted(scene_numbers) != expected_numbers:
        issues.append(
            f"FATAL: Scene numbers not sequential. Got {sorted(scene_numbers)}, "
            f"expected {expected_numbers}"
        )
        score -= 0.2

    # ------------------------------------------------------------------
    # 4. Label-scene consistency
    # ------------------------------------------------------------------
    if design.labels and design.labels.zone_labels:
        zone_labels = set(design.labels.zone_labels)
        # Check that scene mechanics reference valid zone labels
        invalid_refs = all_scene_labels_used - zone_labels
        if invalid_refs:
            issues.append(
                f"WARNING: Mechanics reference labels not in global zone_labels: {invalid_refs}"
            )
            score -= 0.1

        # Check coverage — at least 50% of zone labels should be used
        if zone_labels:
            coverage = len(all_scene_labels_used & zone_labels) / len(zone_labels)
            if coverage < 0.5:
                issues.append(
                    f"WARNING: Only {coverage:.0%} of zone labels are used in mechanics. "
                    f"Unused: {zone_labels - all_scene_labels_used}"
                )
                score -= 0.05

    # ------------------------------------------------------------------
    # 5. Hierarchy validation (hierarchy lives under labels)
    # ------------------------------------------------------------------
    hierarchy = design.labels.hierarchy if design.labels else None
    if hierarchy and hierarchy.enabled:
        if not hierarchy.groups:
            issues.append("WARNING: Hierarchy enabled but no groups defined")
            score -= 0.1
        else:
            zone_labels = set(design.labels.zone_labels) if design.labels else set()
            group_only = set(design.labels.group_only_labels or []) if design.labels else set()
            all_valid_labels = zone_labels | group_only

            for group in hierarchy.groups:
                if group.parent not in all_valid_labels:
                    issues.append(
                        f"WARNING: Hierarchy group parent '{group.parent}' "
                        f"not in zone_labels or group_only_labels"
                    )
                    score -= 0.05
                for child in group.children:
                    if child not in all_valid_labels:
                        issues.append(
                            f"WARNING: Hierarchy child '{child}' "
                            f"not in zone_labels or group_only_labels"
                        )
                        score -= 0.05

    # ------------------------------------------------------------------
    # 6. Transition validation
    # ------------------------------------------------------------------
    if design.scene_transitions:
        valid_scene_nums = set(scene_numbers)
        for trans in design.scene_transitions:
            if trans.from_scene not in valid_scene_nums:
                issues.append(f"WARNING: Transition from non-existent scene {trans.from_scene}")
                score -= 0.05
            if trans.to_scene not in valid_scene_nums:
                issues.append(f"WARNING: Transition to non-existent scene {trans.to_scene}")
                score -= 0.05

    # ------------------------------------------------------------------
    # 7. Run schema-level validation
    # ------------------------------------------------------------------
    schema_issues = validate_game_design(design)
    for issue in schema_issues:
        if issue not in [i for i in issues]:
            issues.append(issue)
            score -= 0.05

    # Final score bounds
    score = max(0.0, min(1.0, score))
    has_fatal = any("FATAL:" in i for i in issues)
    is_valid = not has_fatal and score >= 0.7

    return is_valid, round(score, 3), issues


async def design_validator_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Design Validator Agent — deterministic validation of game_design_v3 output.

    Reads: game_design_v3 from state
    Writes: design_validation_v3 dict with {passed, score, issues}
    """
    logger.info("DesignValidator: Starting validation")

    # Increment retry counter so the graph router can terminate retry loops
    retries = state.get("_v3_design_retries", 0) + 1

    raw_design = state.get("game_design_v3")
    if not raw_design:
        logger.error("DesignValidator: No game_design_v3 in state")
        return {
            **state,
            "current_agent": "design_validator",
            "_v3_design_retries": retries,
            "design_validation_v3": {
                "passed": False,
                "score": 0.0,
                "issues": ["No game_design_v3 found in state"],
            },
        }

    # Parse design
    try:
        if isinstance(raw_design, dict):
            design = GameDesignV3.model_validate(raw_design)
        elif isinstance(raw_design, GameDesignV3):
            design = raw_design
        else:
            design = GameDesignV3.model_validate(raw_design)
    except Exception as e:
        logger.error(f"DesignValidator: Failed to parse game_design_v3: {e}")
        return {
            **state,
            "current_agent": "design_validator",
            "_v3_design_retries": retries,
            "design_validation_v3": {
                "passed": False,
                "score": 0.0,
                "issues": [f"Failed to parse game_design_v3: {e}"],
            },
        }

    # Run validation
    is_valid, score, issues = validate_design(design)

    logger.info(
        f"DesignValidator: {'PASSED' if is_valid else 'FAILED'} "
        f"(score={score}, issues={len(issues)})"
    )

    return {
        **state,
        "current_agent": "design_validator",
        "_v3_design_retries": retries,
        "design_validation_v3": {
            "passed": is_valid,
            "score": score,
            "issues": issues,
        },
    }
