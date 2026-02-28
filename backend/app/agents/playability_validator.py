"""
Playability Validator Agent

Validates that generated games are actually completable by checking:
- All labels have valid target zones (INTERACTIVE_DIAGRAM)
- No overlapping zones that would confuse players
- Steps form valid completable sequence (SEQUENCE_BUILDER)
- All items have valid bucket mappings (BUCKET_SORT)
- All pairs are properly matched (MATCH_PAIRS)
- Code steps are executable (STATE_TRACER_CODE)

This is a rule-based validator that ensures games are playable before
they reach the player.

Inputs:
    blueprint: The game blueprint to validate
    template_selection: Template metadata

Outputs:
    playability_valid: Boolean indicating if game is playable
    playability_score: Float 0-1 score
    playability_issues: List of specific playability problems
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger
from app.config.pedagogical_constants import DEFAULT_SCORING

logger = get_logger("gamed_ai.agents.playability_validator")


async def playability_validator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Playability Validator Agent

    Validates that the generated game blueprint is actually playable.

    Args:
        state: Current agent state with blueprint
        ctx: Optional instrumentation context

    Returns:
        Updated state with playability validation results
    """
    logger.info("PlayabilityValidator: Checking game completability")

    blueprint = state.get("blueprint", {})
    template_type = blueprint.get("templateType", "UNKNOWN")

    # Run template-specific playability checks
    if template_type == "INTERACTIVE_DIAGRAM":
        valid, score, issues = _validate_interactive_diagram_playability(blueprint)
    elif template_type == "SEQUENCE_BUILDER":
        valid, score, issues = _validate_sequence_builder_playability(blueprint)
    elif template_type == "BUCKET_SORT":
        valid, score, issues = _validate_bucket_sort_playability(blueprint)
    elif template_type == "MATCH_PAIRS":
        valid, score, issues = _validate_match_pairs_playability(blueprint)
    elif template_type == "STATE_TRACER_CODE":
        valid, score, issues = _validate_state_tracer_playability(blueprint)
    elif template_type == "PARAMETER_PLAYGROUND":
        valid, score, issues = _validate_parameter_playground_playability(blueprint)
    elif template_type == "TIMELINE_ORDER":
        valid, score, issues = _validate_timeline_order_playability(blueprint)
    else:
        # Unknown template - basic structure check
        valid, score, issues = _validate_generic_playability(blueprint)

    # Check for multi-scene structure (game_sequence)
    if blueprint.get("game_sequence"):
        multi_valid, multi_score, multi_issues = _validate_multi_scene_playability(blueprint)
        # Combine results - multi-scene validation is important
        issues.extend(multi_issues)
        score = (score + multi_score) / 2
        valid = valid and multi_valid

    # Validate mode transitions at blueprint level (if present)
    blueprint_mode_transitions = blueprint.get("mode_transitions", [])
    if blueprint_mode_transitions:
        # Collect all mechanics from game_plan or blueprint
        all_mechanics = []
        game_plan = state.get("game_plan", {})
        if game_plan:
            for mechanic in game_plan.get("game_mechanics", []):
                if isinstance(mechanic, dict):
                    mech_type = mechanic.get("type") or mechanic.get("mechanic_type")
                    if mech_type:
                        all_mechanics.append(mech_type)

        mt_valid, mt_score, mt_issues = _validate_mode_transitions(
            blueprint_mode_transitions, all_mechanics
        )
        issues.extend(mt_issues)
        score = (score + mt_score) / 2
        valid = valid and mt_valid

    # Also validate scoring weights if game_plan is available
    game_plan = state.get("game_plan", {})
    if game_plan:
        weights_valid, weights_score, weights_issues = validate_scoring_weights(game_plan)
        # Combine results
        issues.extend(weights_issues)
        score = (score + weights_score) / 2  # Average the scores
        valid = valid and weights_valid

    if valid:
        logger.info(
            "PlayabilityValidator: Game is playable",
            metadata={"score": score, "template": template_type}
        )
    else:
        logger.warning(
            "PlayabilityValidator: Game has playability issues",
            metadata={"issues": issues[:3], "score": score}
        )

    return {
        "playability_valid": valid,
        "playability_score": score,
        "playability_issues": issues,
        "current_agent": "playability_validator",
    }


# =============================================================================
# MULTI-SCENE VALIDATION (Preset 2 - Advanced Label Diagram)
# =============================================================================

# Valid interaction modes
VALID_INTERACTION_MODES = {
    "drag_drop", "hierarchical", "click_to_identify", "trace_path",
    "description_matching", "sequencing", "compare_contrast",
    "sorting_categories", "branching_scenario", "memory_match", "timed_challenge"
}

# Valid progression types
VALID_PROGRESSION_TYPES = {"linear", "zoom_in", "depth_first", "branching"}

# Valid mode transition triggers
VALID_MODE_TRANSITION_TRIGGERS = {
    "all_zones_labeled", "score_threshold", "time_elapsed", "manual_trigger",
    "all_items_sorted", "sequence_complete", "accuracy_threshold"
}


def _validate_mode_transitions(
    mode_transitions: List[Dict],
    mechanics: List[str]
) -> Tuple[bool, float, List[str]]:
    """
    Validate mode transitions are achievable.

    Checks:
    - from_mode and to_mode are valid mechanics
    - triggers are valid (all_zones_labeled, score_threshold, etc.)
    - no circular transitions that could trap player

    Args:
        mode_transitions: List of transition dicts with from_mode, to_mode, trigger
        mechanics: List of valid mechanic names

    Returns:
        Tuple of (is_valid, score, issues_list)
    """
    issues = []
    score = 1.0

    if not mode_transitions:
        # No transitions defined - that's acceptable for single-mode games
        return True, 1.0, []

    mechanics_set = set(mechanics) if mechanics else set()

    # Build transition graph for cycle detection
    transition_graph: Dict[str, List[str]] = {}

    for idx, transition in enumerate(mode_transitions):
        if not isinstance(transition, dict):
            issues.append(f"Transition {idx} is not a valid dict")
            score -= 0.1
            continue

        from_mode = transition.get("from_mode")
        to_mode = transition.get("to_mode")
        trigger = transition.get("trigger")

        # Validate from_mode exists in mechanics
        if from_mode and mechanics_set and from_mode not in mechanics_set:
            issues.append(f"Transition {idx}: from_mode '{from_mode}' not in mechanics list")
            score -= 0.15

        # Validate to_mode exists in mechanics
        if to_mode and mechanics_set and to_mode not in mechanics_set:
            issues.append(f"Transition {idx}: to_mode '{to_mode}' not in mechanics list")
            score -= 0.15

        # Validate trigger is known
        if trigger and trigger not in VALID_MODE_TRANSITION_TRIGGERS:
            issues.append(f"Transition {idx}: unknown trigger '{trigger}'")
            score -= 0.1

        # Build graph for cycle detection
        if from_mode and to_mode:
            if from_mode not in transition_graph:
                transition_graph[from_mode] = []
            transition_graph[from_mode].append(to_mode)

    # Detect circular transitions using DFS
    def has_cycle_from(node: str, visited: set, rec_stack: set) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in transition_graph.get(node, []):
            if neighbor not in visited:
                if has_cycle_from(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    visited: set = set()
    for node in transition_graph:
        if node not in visited:
            if has_cycle_from(node, visited, set()):
                issues.append("FATAL: Circular mode transitions detected - player could get trapped")
                return False, 0.0, issues

    score = max(0.0, score)
    valid = score >= 0.6

    return valid, score, issues


def _validate_per_scene_mechanics(
    scene: Dict
) -> Tuple[bool, float, List[str]]:
    """
    Validate mechanics within a single scene.

    Checks:
    - scoring_weights sum to 1.0 (if present)
    - all mechanics have required fields
    - completion_criteria is achievable

    Args:
        scene: Scene dict containing mechanics, scoring_weights, completion_criteria

    Returns:
        Tuple of (is_valid, score, issues_list)
    """
    issues = []
    score = 1.0

    scene_id = scene.get("scene_id", "unknown")
    mechanics = scene.get("mechanics", [])
    scoring_weights = scene.get("scoring_weights", {})
    completion_criteria = scene.get("completion_criteria", {})

    # Validate scoring_weights sum to 1.0 if present
    if scoring_weights:
        total_weight = 0.0
        for mechanic_id, weight in scoring_weights.items():
            if isinstance(weight, (int, float)):
                total_weight += weight

                # Check for negative weights
                if weight < 0:
                    issues.append(f"Scene {scene_id}: negative weight for mechanic '{mechanic_id}'")
                    score -= 0.15

                # Check for weights > 1.0
                if weight > 1.0:
                    issues.append(f"Scene {scene_id}: weight > 1.0 for mechanic '{mechanic_id}'")
                    score -= 0.1

        # Check sum is approximately 1.0 (10% tolerance)
        if abs(total_weight - 1.0) > 0.1:
            issues.append(
                f"Scene {scene_id}: scoring_weights sum to {total_weight:.2f}, expected ~1.0"
            )
            score -= 0.2

    # Validate mechanics have required fields
    for idx, mechanic in enumerate(mechanics):
        if not isinstance(mechanic, dict):
            continue

        mechanic_type = mechanic.get("type") or mechanic.get("mechanic_type")
        if not mechanic_type:
            issues.append(f"Scene {scene_id}: mechanic {idx} missing type")
            score -= 0.1

    # Validate completion_criteria is achievable
    if completion_criteria:
        required_score = completion_criteria.get("min_score")
        required_accuracy = completion_criteria.get("min_accuracy")
        max_attempts = completion_criteria.get("max_attempts")

        # Check min_score is achievable (not > max possible)
        max_scene_score = scene.get("max_score", 100)
        if required_score is not None and required_score > max_scene_score:
            issues.append(
                f"Scene {scene_id}: completion requires {required_score} points but max is {max_scene_score}"
            )
            score -= 0.3

        # Check min_accuracy is in valid range
        if required_accuracy is not None:
            if required_accuracy < 0 or required_accuracy > 1.0:
                issues.append(f"Scene {scene_id}: min_accuracy {required_accuracy} not in [0, 1]")
                score -= 0.15
            elif required_accuracy > 0.95:
                issues.append(f"Scene {scene_id}: min_accuracy {required_accuracy} may be too strict")
                score -= 0.05  # Warning, not a hard failure

        # Check max_attempts is reasonable
        if max_attempts is not None and max_attempts < 1:
            issues.append(f"Scene {scene_id}: max_attempts must be at least 1")
            score -= 0.2

    score = max(0.0, score)
    valid = score >= 0.6

    return valid, score, issues


def _validate_scene_transitions_dag(
    scenes: List[Dict],
    scene_transitions: List[Dict]
) -> Tuple[bool, float, List[str]]:
    """
    Validate scene transitions form a valid DAG (Directed Acyclic Graph).

    Checks:
    - No cycles in transitions
    - All scenes reachable from scene 1
    - Terminal scenes have no outgoing transitions

    Args:
        scenes: List of scene dicts
        scene_transitions: List of transition dicts with from_scene, to_scene, condition

    Returns:
        Tuple of (is_valid, score, issues_list)
    """
    issues = []
    score = 1.0

    if not scenes:
        return True, 1.0, ["No scenes to validate"]

    # Build scene ID set
    scene_ids = set()
    scene_id_to_number = {}
    for scene in scenes:
        if isinstance(scene, dict):
            scene_id = scene.get("scene_id")
            scene_num = scene.get("scene_number", 0)
            if scene_id:
                scene_ids.add(scene_id)
                scene_id_to_number[scene_id] = scene_num

    if not scene_transitions:
        # No explicit transitions - assume linear progression
        # This is valid, just a simple game
        return True, 1.0, ["No explicit transitions - assuming linear progression"]

    # Build transition graph
    transition_graph: Dict[str, List[str]] = {}
    incoming_edges: Dict[str, int] = {sid: 0 for sid in scene_ids}

    for idx, transition in enumerate(scene_transitions):
        if not isinstance(transition, dict):
            issues.append(f"Transition {idx} is not a valid dict")
            score -= 0.1
            continue

        from_scene = transition.get("from_scene")
        to_scene = transition.get("to_scene")

        # Validate from_scene exists
        if from_scene and from_scene not in scene_ids:
            issues.append(f"Transition {idx}: from_scene '{from_scene}' not in scenes")
            score -= 0.15

        # Validate to_scene exists
        if to_scene and to_scene not in scene_ids:
            issues.append(f"Transition {idx}: to_scene '{to_scene}' not in scenes")
            score -= 0.15

        # Build graph
        if from_scene and to_scene:
            if from_scene not in transition_graph:
                transition_graph[from_scene] = []
            transition_graph[from_scene].append(to_scene)
            if to_scene in incoming_edges:
                incoming_edges[to_scene] += 1

    # Detect cycles using DFS
    def has_cycle_from(node: str, visited: set, rec_stack: set) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in transition_graph.get(node, []):
            if neighbor not in visited:
                if has_cycle_from(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    visited: set = set()
    for node in transition_graph:
        if node not in visited:
            if has_cycle_from(node, visited, set()):
                issues.append("FATAL: Cycle detected in scene transitions - game cannot complete")
                return False, 0.0, issues

    # Check all scenes reachable from scene 1 (or first scene)
    first_scene = None
    for scene in scenes:
        if isinstance(scene, dict):
            if scene.get("scene_number") == 1:
                first_scene = scene.get("scene_id")
                break

    if not first_scene and scenes:
        # Use first scene in list if no scene_number=1
        first_scene = scenes[0].get("scene_id") if isinstance(scenes[0], dict) else None

    if first_scene:
        # BFS to find reachable scenes
        reachable = set()
        queue = [first_scene]
        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            for neighbor in transition_graph.get(current, []):
                if neighbor not in reachable:
                    queue.append(neighbor)

        unreachable = scene_ids - reachable
        if unreachable:
            issues.append(f"Unreachable scenes from scene 1: {sorted(unreachable)}")
            score -= 0.2 * len(unreachable)

    # Check terminal scenes (no outgoing transitions)
    terminal_scenes = scene_ids - set(transition_graph.keys())
    if not terminal_scenes:
        issues.append("WARNING: No terminal scenes - game may not have clear ending")
        score -= 0.1

    score = max(0.0, score)
    valid = score >= 0.6 and not any("FATAL" in issue for issue in issues)

    if valid and not any("FATAL" in i or "WARNING" in i for i in issues):
        issues.append(f"Scene transitions form valid DAG with {len(terminal_scenes)} terminal scene(s)")

    return valid, score, issues


def _validate_multi_scene_playability(blueprint: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Validate multi-scene blueprint structure and consistency.

    Checks:
    - game_sequence object exists and is valid
    - Each scene has required fields
    - scene_number is sequential
    - interaction_mode is valid for each scene
    - Prerequisites form valid DAG (no cycles)
    - Each scene is individually playable
    - Mode transitions are valid (if present)
    - Per-scene mechanics are valid
    - Scene transitions form valid DAG
    """
    issues = []
    score = 1.0

    # Get game_sequence
    game_sequence = blueprint.get("game_sequence", {})
    if not game_sequence:
        issues.append("FATAL: Multi-scene blueprint has no game_sequence object")
        return False, 0.0, issues

    scenes = game_sequence.get("scenes", [])
    if not scenes:
        issues.append("FATAL: Multi-scene blueprint has no scenes in game_sequence")
        return False, 0.0, issues

    if len(scenes) < 2:
        issues.append("FATAL: Multi-scene game must have at least 2 scenes")
        return False, 0.0, issues

    # Track for validation
    seen_ids = set()
    seen_numbers = set()
    scene_id_to_number = {}
    all_mechanics: List[str] = []

    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", f"scene_{i}")
        scene_num = scene.get("scene_number", i + 1)

        # Check for duplicate IDs
        if scene_id in seen_ids:
            issues.append(f"Duplicate scene_id: {scene_id}")
            score -= 0.3
        seen_ids.add(scene_id)
        scene_id_to_number[scene_id] = scene_num

        # Check for duplicate numbers
        if scene_num in seen_numbers:
            issues.append(f"Duplicate scene_number: {scene_num}")
            score -= 0.3
        seen_numbers.add(scene_num)

        # Check required fields
        required_fields = ["scene_id", "title", "interaction_mode"]
        for field in required_fields:
            if not scene.get(field):
                issues.append(f"Scene {scene_num} missing required field: {field}")
                score -= 0.2

        # Validate interaction mode
        mode = scene.get("interaction_mode")
        if mode and mode not in VALID_INTERACTION_MODES:
            issues.append(f"Scene {scene_num} has invalid interaction_mode: {mode}")
            score -= 0.2

        # Collect mechanics for mode transition validation
        if mode:
            all_mechanics.append(mode)

        # Check zones and labels for zone-based modes
        zone_based_modes = {"drag_drop", "hierarchical", "click_to_identify", "description_matching"}
        if mode in zone_based_modes:
            zones = scene.get("zones", [])
            labels = scene.get("labels", [])

            if not zones:
                issues.append(f"Scene {scene_num} ({mode}) has no zones")
                score -= 0.15

            if not labels and mode in {"drag_drop", "hierarchical"}:
                issues.append(f"Scene {scene_num} ({mode}) has no labels")
                score -= 0.15

        # Validate prerequisite (must reference earlier scene)
        prereq = scene.get("prerequisite_scene")
        if prereq:
            if prereq not in scene_id_to_number:
                issues.append(f"Scene {scene_num} has invalid prerequisite: {prereq}")
                score -= 0.2
            elif scene_id_to_number.get(prereq, 0) >= scene_num:
                issues.append(f"Scene {scene_num} prerequisite '{prereq}' is not an earlier scene")
                score -= 0.2

        # Validate per-scene mechanics
        mech_valid, mech_score, mech_issues = _validate_per_scene_mechanics(scene)
        if not mech_valid:
            score -= (1.0 - mech_score) * 0.5  # Weight per-scene issues
        issues.extend(mech_issues)

    # Validate mode transitions within scenes
    for scene in scenes:
        if isinstance(scene, dict):
            mode_transitions = scene.get("mode_transitions", [])
            if mode_transitions:
                mt_valid, mt_score, mt_issues = _validate_mode_transitions(
                    mode_transitions, all_mechanics
                )
                if not mt_valid:
                    score -= (1.0 - mt_score) * 0.5
                issues.extend(mt_issues)

    # Validate scene transitions DAG
    scene_transitions = game_sequence.get("scene_transitions", [])
    dag_valid, dag_score, dag_issues = _validate_scene_transitions_dag(scenes, scene_transitions)
    if not dag_valid:
        score -= (1.0 - dag_score) * 0.5
    issues.extend(dag_issues)

    # Validate progression type
    prog_type = game_sequence.get("progression_type")
    if prog_type and prog_type not in VALID_PROGRESSION_TYPES:
        issues.append(f"Invalid progression_type: {prog_type}")
        score -= 0.15

    # Validate total_max_score is reasonable
    total_score = game_sequence.get("total_max_score", 0)
    if total_score <= 0:
        issues.append("total_max_score should be positive")
        score -= 0.1

    # Validate scene scores add up
    scene_scores = sum(s.get("max_score", 0) for s in scenes)
    if scene_scores > 0 and abs(scene_scores - total_score) > 1:
        issues.append(f"Scene max_scores ({scene_scores}) don't match total_max_score ({total_score})")
        score -= 0.1

    # Ensure score doesn't go below 0
    score = max(0.0, score)
    valid = score >= 0.6 and not any("FATAL" in issue for issue in issues)

    if valid:
        issues.append(f"Multi-scene validation passed: {len(scenes)} scenes, {prog_type} progression")

    return valid, score, issues


def _validate_interactive_diagram_playability(blueprint: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Validate INTERACTIVE_DIAGRAM is playable:
    - All labels have valid target zones
    - No overlapping zones (would confuse players)
    - Zones are within diagram bounds
    - At least one label to place
    - Multi-scene: validate each scene and progression
    """
    issues = []
    score = 1.0

    # Check if this is a multi-scene blueprint
    is_multi_scene = blueprint.get("is_multi_scene", False)
    if is_multi_scene:
        return _validate_multi_scene_playability(blueprint)

    diagram = blueprint.get("diagram", {})
    zones = diagram.get("zones", [])
    labels = blueprint.get("labels", [])

    # Check we have zones and labels
    if not zones:
        issues.append("FATAL: No zones defined - nothing to drop labels onto")
        return False, 0.0, issues

    if not labels:
        issues.append("FATAL: No labels defined - nothing to drag")
        return False, 0.0, issues

    # Build zone lookup
    zone_ids = {z.get("id") for z in zones if isinstance(z, dict)}
    zone_positions = {}
    for zone in zones:
        if isinstance(zone, dict):
            zone_id = zone.get("id")
            x = zone.get("x", 50)
            y = zone.get("y", 50)
            radius = zone.get("radius", 10)
            zone_positions[zone_id] = (x, y, radius)

    # Check all labels reference valid zones
    for label in labels:
        if not isinstance(label, dict):
            continue
        label_id = label.get("id", "unknown")
        correct_zone = label.get("correctZoneId")

        if not correct_zone:
            issues.append(f"Label '{label_id}' has no correctZoneId - cannot be placed")
            score -= 0.2
        elif correct_zone not in zone_ids:
            issues.append(f"Label '{label_id}' targets non-existent zone '{correct_zone}'")
            score -= 0.3

    # Check for overlapping zones (confuses players)
    zone_list = list(zone_positions.items())
    for i, (zone1_id, (x1, y1, r1)) in enumerate(zone_list):
        for zone2_id, (x2, y2, r2) in zone_list[i + 1:]:
            distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            min_distance = r1 + r2

            if distance < min_distance * 0.5:  # Significant overlap
                issues.append(
                    f"Zones '{zone1_id}' and '{zone2_id}' overlap significantly - may confuse players"
                )
                score -= 0.1

    # Check zones are within bounds
    for zone_id, (x, y, radius) in zone_positions.items():
        if x < 0 or x > 100 or y < 0 or y > 100:
            issues.append(f"Zone '{zone_id}' is outside diagram bounds")
            score -= 0.15

    # Check minimum label count for meaningful game
    if len(labels) < 2:
        issues.append("Only 1 label - game may be too trivial")
        score -= 0.1

    # Stricter minimum - games with fewer than 3 labels are not playable
    if len(labels) < 3:
        issues.append("FATAL: Fewer than 3 labels - game not meaningful")
        return False, 0.0, issues

    # Semantic coverage validation against canonical labels
    # This ensures the game actually covers the educational content
    domain_knowledge = blueprint.get("domain_knowledge", {})
    canonical_labels = domain_knowledge.get("canonical_labels", [])

    if canonical_labels and len(canonical_labels) >= 3:
        # Extract label texts for comparison
        label_texts = set()
        for label in labels:
            if isinstance(label, dict):
                text = label.get("text", "").lower().strip()
                if text:
                    label_texts.add(text)

        canonical_set = {c.lower().strip() for c in canonical_labels}

        # Calculate coverage
        matched = len(label_texts & canonical_set)
        coverage = matched / len(canonical_set) if canonical_set else 0

        if coverage < 0.3:
            issues.append(
                f"FATAL: Only {matched}/{len(canonical_set)} canonical labels present ({coverage:.0%} coverage)"
            )
            return False, 0.0, issues
        elif coverage < 0.6:
            issues.append(
                f"Low coverage: {matched}/{len(canonical_set)} canonical labels ({coverage:.0%})"
            )
            score -= 0.3

    # Ensure score doesn't go below 0
    score = max(0.0, score)
    valid = score >= 0.6 and not any("FATAL" in issue for issue in issues)

    return valid, score, issues


def _validate_sequence_builder_playability(blueprint: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Validate SEQUENCE_BUILDER is playable:
    - Steps have unique order indices
    - Order indices are sequential
    - At least 2 steps for a sequence
    """
    issues = []
    score = 1.0

    steps = blueprint.get("steps", [])

    if len(steps) < 2:
        issues.append("FATAL: Need at least 2 steps for a sequence")
        return False, 0.0, issues

    # Check order indices
    order_indices = []
    for step in steps:
        if isinstance(step, dict):
            idx = step.get("orderIndex")
            if idx is None:
                issues.append(f"Step '{step.get('id', 'unknown')}' missing orderIndex")
                score -= 0.2
            else:
                order_indices.append(idx)

    # Check for duplicates
    if len(order_indices) != len(set(order_indices)):
        issues.append("Duplicate orderIndex values - ambiguous correct order")
        score -= 0.3

    # Check for gaps in sequence
    if order_indices:
        sorted_indices = sorted(order_indices)
        expected = list(range(sorted_indices[0], sorted_indices[-1] + 1))
        if sorted_indices != expected:
            issues.append("Gaps in orderIndex sequence - may confuse players")
            score -= 0.1

    score = max(0.0, score)
    valid = score >= 0.6 and not any("FATAL" in issue for issue in issues)

    return valid, score, issues


def _validate_bucket_sort_playability(blueprint: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Validate BUCKET_SORT is playable:
    - All items have valid bucket mappings
    - Each bucket has at least one item
    - At least 2 buckets
    """
    issues = []
    score = 1.0

    buckets = blueprint.get("buckets", [])
    items = blueprint.get("items", [])

    if len(buckets) < 2:
        issues.append("FATAL: Need at least 2 buckets for sorting")
        return False, 0.0, issues

    if len(items) < 2:
        issues.append("FATAL: Need at least 2 items to sort")
        return False, 0.0, issues

    # Build bucket lookup
    bucket_ids = {b.get("id") for b in buckets if isinstance(b, dict)}
    bucket_item_counts = {bid: 0 for bid in bucket_ids}

    # Check all items reference valid buckets
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id", "unknown")
        correct_bucket = item.get("correctBucketId")

        if not correct_bucket:
            issues.append(f"Item '{item_id}' has no correctBucketId")
            score -= 0.2
        elif correct_bucket not in bucket_ids:
            issues.append(f"Item '{item_id}' targets non-existent bucket '{correct_bucket}'")
            score -= 0.3
        else:
            bucket_item_counts[correct_bucket] += 1

    # Check each bucket has at least one item
    empty_buckets = [bid for bid, count in bucket_item_counts.items() if count == 0]
    if empty_buckets:
        issues.append(f"Empty buckets (no items assigned): {empty_buckets}")
        score -= 0.15 * len(empty_buckets)

    score = max(0.0, score)
    valid = score >= 0.6 and not any("FATAL" in issue for issue in issues)

    return valid, score, issues


def _validate_match_pairs_playability(blueprint: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Validate MATCH_PAIRS is playable:
    - All pairs have both left and right items
    - At least 2 pairs
    """
    issues = []
    score = 1.0

    pairs = blueprint.get("pairs", [])

    if len(pairs) < 2:
        issues.append("FATAL: Need at least 2 pairs for matching")
        return False, 0.0, issues

    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        pair_id = pair.get("id", "unknown")

        left_item = pair.get("leftItem", {})
        right_item = pair.get("rightItem", {})

        if not left_item or not left_item.get("text"):
            issues.append(f"Pair '{pair_id}' missing left item text")
            score -= 0.2

        if not right_item or not right_item.get("text"):
            issues.append(f"Pair '{pair_id}' missing right item text")
            score -= 0.2

    score = max(0.0, score)
    valid = score >= 0.6 and not any("FATAL" in issue for issue in issues)

    return valid, score, issues


def _validate_state_tracer_playability(blueprint: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Validate STATE_TRACER_CODE is playable:
    - Code is present
    - Steps have expected variables
    - Tasks reference valid steps
    """
    issues = []
    score = 1.0

    code = blueprint.get("code", "")
    steps = blueprint.get("steps", [])
    tasks = blueprint.get("tasks", [])

    if not code or not code.strip():
        issues.append("FATAL: No code to trace")
        return False, 0.0, issues

    if not steps:
        issues.append("FATAL: No execution steps defined")
        return False, 0.0, issues

    # Check steps have expected variables
    for step in steps:
        if isinstance(step, dict):
            expected_vars = step.get("expectedVariables", {})
            if not expected_vars:
                issues.append(f"Step {step.get('index', 'unknown')} has no expected variables")
                score -= 0.1

    # Check task references
    max_step_index = max((s.get("index", 0) for s in steps if isinstance(s, dict)), default=0)
    for task in tasks:
        if isinstance(task, dict):
            step_idx = task.get("stepIndex")
            if step_idx is not None and step_idx > max_step_index:
                issues.append(f"Task references invalid step index {step_idx}")
                score -= 0.2

    score = max(0.0, score)
    valid = score >= 0.6 and not any("FATAL" in issue for issue in issues)

    return valid, score, issues


def _validate_parameter_playground_playability(blueprint: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Validate PARAMETER_PLAYGROUND is playable:
    - Parameters have valid ranges
    - Visualization is defined
    """
    issues = []
    score = 1.0

    parameters = blueprint.get("parameters", [])
    visualization = blueprint.get("visualization", {})

    if not parameters:
        issues.append("FATAL: No parameters to adjust")
        return False, 0.0, issues

    if not visualization:
        issues.append("No visualization defined - feedback unclear")
        score -= 0.3

    for param in parameters:
        if not isinstance(param, dict):
            continue
        param_id = param.get("id", "unknown")
        param_type = param.get("type", "input")

        if param_type == "slider":
            min_val = param.get("min")
            max_val = param.get("max")
            if min_val is None or max_val is None:
                issues.append(f"Slider '{param_id}' missing min/max range")
                score -= 0.2
            elif min_val >= max_val:
                issues.append(f"Slider '{param_id}' has invalid range (min >= max)")
                score -= 0.2

    score = max(0.0, score)
    valid = score >= 0.6 and not any("FATAL" in issue for issue in issues)

    return valid, score, issues


def _validate_timeline_order_playability(blueprint: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Validate TIMELINE_ORDER is playable:
    - Events have valid timestamps
    - Timeline has valid range
    - Events fall within timeline
    """
    issues = []
    score = 1.0

    events = blueprint.get("events", [])
    timeline = blueprint.get("timeline", {})

    if len(events) < 2:
        issues.append("FATAL: Need at least 2 events for timeline")
        return False, 0.0, issues

    start_time = timeline.get("startTime")
    end_time = timeline.get("endTime")

    if start_time is None or end_time is None:
        issues.append("Timeline missing start or end time")
        score -= 0.3
    elif start_time >= end_time:
        issues.append("Timeline has invalid range (start >= end)")
        score -= 0.3
    else:
        # Check events fall within timeline
        for event in events:
            if isinstance(event, dict):
                timestamp = event.get("timestamp")
                event_id = event.get("id", "unknown")
                if timestamp is not None:
                    if timestamp < start_time or timestamp > end_time:
                        issues.append(f"Event '{event_id}' outside timeline range")
                        score -= 0.15

    score = max(0.0, score)
    valid = score >= 0.6 and not any("FATAL" in issue for issue in issues)

    return valid, score, issues


def _validate_generic_playability(blueprint: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Generic playability check for unknown templates.
    """
    issues = []
    score = 1.0

    # Check basic structure
    if not blueprint.get("title"):
        issues.append("Missing title")
        score -= 0.1

    if not blueprint.get("tasks"):
        issues.append("No tasks defined")
        score -= 0.3

    if not blueprint.get("animationCues"):
        issues.append("No animation cues - no feedback for player")
        score -= 0.2

    score = max(0.0, score)
    valid = score >= 0.5

    return valid, score, issues


# =============================================================================
# SCORING WEIGHTS VALIDATION (Phase 4 - T1 Topology Fixes)
# =============================================================================

def validate_scoring_weights(game_plan: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Validate that mechanic weights sum to approximately 1.0 (100%).

    This ensures game_mechanics from game_planner have proper scoring weights
    that allow fair score distribution across mechanics.

    Args:
        game_plan: The game plan dict containing game_mechanics

    Returns:
        Tuple of (is_valid, score, issues_list)
    """
    issues = []
    score = 1.0

    game_mechanics = game_plan.get("game_mechanics", [])

    if not game_mechanics:
        # No mechanics to validate - this is acceptable
        return True, 1.0, ["No mechanics to validate weights"]

    # Calculate total weight
    total_weight = 0.0
    mechanics_with_weights = 0

    for mechanic in game_mechanics:
        if not isinstance(mechanic, dict):
            continue
        weight = mechanic.get("scoring_weight", 0)
        if isinstance(weight, (int, float)):
            total_weight += weight
            mechanics_with_weights += 1

    # If no mechanics have weights, that's acceptable (defaults will be used)
    if mechanics_with_weights == 0:
        issues.append("No mechanics have explicit weights - defaults will be used")
        return True, 0.8, issues

    # Check if weights sum to approximately 1.0 (allow 10% tolerance)
    if abs(total_weight - 1.0) > 0.1:
        issues.append(
            f"Mechanic weights sum to {total_weight:.2f}, expected ~1.0 (±10% tolerance)"
        )
        score -= 0.3

        # Severe deviation is a bigger issue
        if abs(total_weight - 1.0) > 0.3:
            issues.append("SEVERE: Weights are significantly off from 1.0")
            score -= 0.2

    # Check for negative weights
    negative_weights = [
        m.get("id", "unknown")
        for m in game_mechanics
        if isinstance(m, dict) and isinstance(m.get("scoring_weight"), (int, float)) and m.get("scoring_weight", 0) < 0
    ]
    if negative_weights:
        issues.append(f"Negative weights found in mechanics: {negative_weights}")
        score -= 0.2

    # Check for weights > 1.0 on individual mechanics
    overweight_mechanics = [
        m.get("id", "unknown")
        for m in game_mechanics
        if isinstance(m, dict) and isinstance(m.get("scoring_weight"), (int, float)) and m.get("scoring_weight", 0) > 1.0
    ]
    if overweight_mechanics:
        issues.append(f"Individual weights > 1.0 found: {overweight_mechanics}")
        score -= 0.15

    score = max(0.0, score)
    valid = score >= 0.6

    if valid and not issues:
        issues.append(f"Scoring weights valid (total: {total_weight:.2f})")

    return valid, score, issues


# =============================================================================
# Simple validation function for HAD output_tools
# =============================================================================

async def validate_playability(
    blueprint: Dict[str, Any],
    template_type: str,
) -> Tuple[bool, float, str]:
    """
    Simple playability validation function for HAD output_tools.

    This is a simplified wrapper around the template-specific validators
    for use when you don't have access to the full AgentState.

    Args:
        blueprint: The game blueprint to validate
        template_type: The template type (INTERACTIVE_DIAGRAM, etc.)

    Returns:
        Tuple of (is_valid, score, message)
    """
    # Run template-specific playability checks
    if template_type == "INTERACTIVE_DIAGRAM":
        valid, score, issues = _validate_interactive_diagram_playability(blueprint)
    elif template_type == "SEQUENCE_BUILDER":
        valid, score, issues = _validate_sequence_builder_playability(blueprint)
    elif template_type == "BUCKET_SORT":
        valid, score, issues = _validate_bucket_sort_playability(blueprint)
    elif template_type == "MATCH_PAIRS":
        valid, score, issues = _validate_match_pairs_playability(blueprint)
    elif template_type == "STATE_TRACER_CODE":
        valid, score, issues = _validate_state_tracer_playability(blueprint)
    elif template_type == "PARAMETER_PLAYGROUND":
        valid, score, issues = _validate_parameter_playground_playability(blueprint)
    elif template_type == "TIMELINE_ORDER":
        valid, score, issues = _validate_timeline_order_playability(blueprint)
    else:
        valid, score, issues = _validate_generic_playability(blueprint)

    # Check for multi-scene structure
    if blueprint.get("scenes"):
        multi_valid, multi_score, multi_issues = _validate_multi_scene_playability(blueprint)
        # Average the scores
        score = (score + multi_score) / 2
        issues.extend(multi_issues)
        valid = valid and multi_valid

    # Format message
    if valid:
        message = f"Playability validation passed (score: {score:.2f})"
    else:
        message = f"Playability validation failed: {'; '.join(issues[:3])}"

    return valid, score, message
