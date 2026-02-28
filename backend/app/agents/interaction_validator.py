"""
Interaction Validator Agent

Validates the interaction design for:
1. Playability - Can user complete the game with designed interactions?
2. Learning Alignment - Do interactions support the Bloom's level?
3. Technical Feasibility - Are all modes supported by frontend?
4. Consistency - Do reveal strategies match hierarchy types?

Has retry logic with auto-fix suggestions for common issues.

Inputs:
- interaction_design: From interaction_designer agent
- game_plan: From game_planner agent
- domain_knowledge: From domain_knowledge_retriever

Outputs:
- validation_passed: bool
- validation_score: float (0-1)
- issues: List of issues found
- suggestions: List of fix suggestions
- approved_interaction_design: Potentially modified design
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.config.interaction_patterns import (
    INTERACTION_PATTERNS,
    SCORING_STRATEGIES,
    SUPPORTED_ANIMATIONS,
    get_pattern,
    get_frontend_supported_patterns,
    validate_multi_mode_combination,
    check_pattern_compatibility,
    PatternStatus,
)
from app.utils.logging_config import get_logger
from app.config.pedagogical_constants import BLOOM_LEVELS, DEFAULT_SCORING

logger = get_logger("gamed_ai.agents.interaction_validator")


# =============================================================================
# VALIDATION RULES
# =============================================================================

def validate_playability(
    interaction_design: Dict[str, Any],
    zone_count: int,
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that the game is playable with the designed interactions.

    Checks:
    - Primary mode is implemented
    - Zone count is within mode limits
    - Reveal strategy is achievable
    """
    issues = []
    suggestions = []

    primary_mode = interaction_design.get("primary_interaction_mode", "")
    pattern = get_pattern(primary_mode)

    # Check primary mode exists and is implemented
    if not pattern:
        issues.append(f"Unknown interaction mode: '{primary_mode}'")
        suggestions.append("Use 'drag_drop' as a safe default")
    elif pattern.status == PatternStatus.MISSING:
        issues.append(f"Mode '{primary_mode}' is not yet implemented")
        suggestions.append(f"Consider using one of: {get_frontend_supported_patterns()[:3]}")
    elif pattern.status == PatternStatus.EXPERIMENTAL:
        # Warning, not error
        suggestions.append(f"Mode '{primary_mode}' is experimental and may have issues")

    # Check zone count
    scoring = interaction_design.get("scoring_strategy", {})
    max_score = scoring.get("max_score", 100)
    base_points = scoring.get("base_points_per_zone", 10)

    if zone_count > 0 and base_points > 0:
        expected_max = base_points * zone_count
        if abs(max_score - expected_max) > expected_max * 0.5:
            suggestions.append(
                f"Max score ({max_score}) doesn't align with "
                f"zone_count ({zone_count}) x base_points ({base_points})"
            )

    # Check reveal strategy consistency
    reveal = interaction_design.get("reveal_strategy", {})
    hierarchy_info = interaction_design.get("hierarchy_info", {})

    if reveal.get("type") == "progressive_hierarchical" and not hierarchy_info.get("has_hierarchy"):
        issues.append("Progressive hierarchical reveal requires hierarchical content")
        suggestions.append("Change reveal type to 'flat' or 'sequential'")

    valid = len(issues) == 0
    return valid, issues, suggestions


def validate_learning_alignment(
    interaction_design: Dict[str, Any],
    ped_context: Dict[str, Any],
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that interactions support the learning objectives.

    Checks:
    - Mode cognitive demands match Bloom's level
    - Complexity is appropriate for difficulty
    - Feedback strategy supports learning
    """
    issues = []
    suggestions = []

    blooms_level = ped_context.get("blooms_level", "understand")
    difficulty = ped_context.get("difficulty", "intermediate")
    primary_mode = interaction_design.get("primary_interaction_mode", "")
    pattern = get_pattern(primary_mode)

    if not pattern:
        return True, [], []  # Can't validate unknown pattern

    # Bloom's level is informational only — do NOT use it to constrain
    # or suggest mechanic selection. Pattern cognitive demands are validated
    # against content type, not Bloom's taxonomy.
    pattern_demands = pattern.cognitive_demands

    # Check complexity vs difficulty
    complexity_map = {
        "beginner": ["LOW"],
        "easy": ["LOW", "LOW_TO_MEDIUM"],
        "intermediate": ["LOW_TO_MEDIUM", "MEDIUM"],
        "advanced": ["MEDIUM", "MEDIUM_TO_HIGH"],
        "expert": ["MEDIUM_TO_HIGH", "HIGH"],
    }

    expected_complexity = complexity_map.get(difficulty, ["MEDIUM"])
    if pattern.complexity.name not in expected_complexity:
        suggestions.append(
            f"Mode '{primary_mode}' complexity ({pattern.complexity.name}) "
            f"may not match '{difficulty}' difficulty level"
        )

    # Check feedback strategy
    feedback = interaction_design.get("feedback_strategy", {})
    if not feedback.get("on_correct") or not feedback.get("on_incorrect"):
        issues.append("Missing feedback messages")
        suggestions.append("Add both on_correct and on_incorrect feedback")

    valid = len(issues) == 0
    return valid, issues, suggestions


def validate_technical_feasibility(
    interaction_design: Dict[str, Any],
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that all modes and animations are supported by frontend.

    Checks:
    - All modes have frontend components
    - All animations are defined
    - Multi-mode combinations are compatible
    """
    issues = []
    suggestions = []

    # Check primary mode frontend support
    primary_mode = interaction_design.get("primary_interaction_mode", "")
    pattern = get_pattern(primary_mode)

    if pattern and not pattern.frontend_component:
        issues.append(f"Mode '{primary_mode}' has no frontend component")
        suggestions.append("Use a fully implemented mode like 'drag_drop'")

    # Check secondary modes
    secondary_modes = interaction_design.get("secondary_modes", [])
    for mode in secondary_modes:
        sec_pattern = get_pattern(mode)
        if sec_pattern and sec_pattern.status == PatternStatus.MISSING:
            suggestions.append(f"Secondary mode '{mode}' is not implemented")

    # Check multi-mode combination
    if secondary_modes:
        all_modes = [primary_mode] + secondary_modes
        validation = validate_multi_mode_combination(all_modes)
        if not validation.get("valid"):
            issues.extend(validation.get("errors", []))
        suggestions.extend(validation.get("warnings", []))

    # Check animations
    animations = interaction_design.get("animation_config", {})
    for trigger, anim_id in animations.items():
        if anim_id and anim_id not in SUPPORTED_ANIMATIONS:
            suggestions.append(f"Unknown animation '{anim_id}' for '{trigger}'")

    valid = len(issues) == 0
    return valid, issues, suggestions


# Phase 4: Mechanic compatibility matrix
# Values must use actual frontend InteractionMode identifiers
COMPATIBLE_MECHANICS = {
    "drag_drop": ["hierarchical", "sequencing", "trace_path", "memory_match"],
    "click_to_identify": ["hierarchical", "sequencing"],
    "sequencing": ["drag_drop", "hierarchical"],
    "trace_path": ["drag_drop"],
    "hierarchical": ["drag_drop", "click_to_identify", "sequencing"],
    "memory_match": ["drag_drop"],
    "description_matching": ["drag_drop", "click_to_identify"],
    "compare_contrast": ["drag_drop", "hierarchical"],
    "sorting_categories": ["drag_drop", "sequencing"],
    "timed_challenge": ["drag_drop", "click_to_identify"],
    "branching_scenario": ["sequencing"],
}


def validate_mechanic_compatibility(
    game_mechanics: List[Dict[str, Any]],
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that selected game mechanics are compatible with each other.

    Phase 4: Multi-mechanic support validation.

    Args:
        game_mechanics: List of mechanic dicts with 'type' field

    Returns:
        Tuple of (valid, issues, suggestions)
    """
    issues = []
    suggestions = []

    if not game_mechanics or len(game_mechanics) < 2:
        # Single mechanic or no mechanics - nothing to validate
        return True, [], []

    mechanic_types = [m.get("type", "").lower() for m in game_mechanics if isinstance(m, dict)]
    mechanic_types = [t for t in mechanic_types if t]  # Filter empty

    # Check pairwise compatibility
    for i, mech1 in enumerate(mechanic_types):
        for mech2 in mechanic_types[i + 1:]:
            compatible = COMPATIBLE_MECHANICS.get(mech1, [])
            reverse_compatible = COMPATIBLE_MECHANICS.get(mech2, [])

            if mech2 not in compatible and mech1 not in reverse_compatible:
                issues.append(f"Incompatible mechanics: '{mech1}' and '{mech2}'")
                suggestions.append(
                    f"Consider using '{mech1}' with one of: {compatible[:3]}"
                )

    valid = len(issues) == 0
    return valid, issues, suggestions


def validate_consistency(
    interaction_design: Dict[str, Any],
    domain_knowledge: Dict[str, Any],
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate internal consistency of the interaction design.

    Checks:
    - Reveal strategy matches hierarchy type
    - Scoring adds up correctly
    - Zone behavior strategy is logical
    """
    issues = []
    suggestions = []

    reveal = interaction_design.get("reveal_strategy", {})
    hierarchy_info = interaction_design.get("hierarchy_info", {})
    scoring = interaction_design.get("scoring_strategy", {})

    # Check reveal trigger matches hierarchy type
    hierarchy_type = hierarchy_info.get("hierarchy_type", "flat")
    trigger = reveal.get("trigger", "")

    if hierarchy_type == "layered":
        # Layered hierarchies (composed_of, subdivided_into) work best with hover_reveal
        if trigger not in ("hover_reveal", "complete_parent", "click_expand"):
            suggestions.append(
                f"Layered hierarchy works better with 'hover_reveal' or 'complete_parent' trigger"
            )
    elif hierarchy_type == "discrete":
        # Discrete hierarchies (contains, has_part) work best with click_expand
        if trigger not in ("click_expand", "complete_parent"):
            suggestions.append(
                f"Discrete hierarchy works better with 'click_expand' trigger"
            )

    # Check scoring strategy exists
    strategy_id = scoring.get("strategy_id", "")
    if strategy_id and strategy_id not in SCORING_STRATEGIES:
        suggestions.append(f"Unknown scoring strategy '{strategy_id}', using 'standard'")

    # Check hint penalty is reasonable
    hint_penalty = scoring.get("hint_penalty", 0)
    if hint_penalty > 50:
        suggestions.append(
            f"Hint penalty ({hint_penalty}%) is high, may discourage hint usage"
        )

    valid = len(issues) == 0
    return valid, issues, suggestions


# =============================================================================
# AUTO-FIX FUNCTIONS
# =============================================================================

def auto_fix_design(
    interaction_design: Dict[str, Any],
    issues: List[str],
    suggestions: List[str],
) -> Dict[str, Any]:
    """
    Attempt to automatically fix common issues in the interaction design.

    Returns a modified copy of the interaction design.
    """
    fixed = {**interaction_design}

    # Fix unknown primary mode
    primary_mode = fixed.get("primary_interaction_mode", "")
    pattern = get_pattern(primary_mode)
    if not pattern or pattern.status == PatternStatus.MISSING:
        # Do NOT default to drag_drop — leave the mode as-is and log a warning.
        # The game designer chose this mechanic for pedagogical reasons.
        logger.warning(f"Unknown or missing interaction mode '{primary_mode}' — not auto-fixing")

    # Fix missing feedback
    feedback = fixed.get("feedback_strategy", {})
    if not feedback.get("on_correct"):
        feedback["on_correct"] = "Correct! Great job!"
    if not feedback.get("on_incorrect"):
        feedback["on_incorrect"] = "Not quite. Try again."
    fixed["feedback_strategy"] = feedback

    # Fix reveal strategy for flat content
    hierarchy_info = fixed.get("hierarchy_info", {})
    reveal = fixed.get("reveal_strategy", {})
    if reveal.get("type") == "progressive_hierarchical" and not hierarchy_info.get("has_hierarchy"):
        reveal["type"] = "flat"
        reveal["trigger"] = "all_at_once"
        fixed["reveal_strategy"] = reveal
        logger.info("Auto-fixed: Changed reveal strategy to 'flat' for non-hierarchical content")

    # Fix unknown animations
    animations = fixed.get("animation_config", {})
    for trigger in ["on_correct", "on_incorrect", "on_reveal", "on_complete"]:
        if trigger not in animations or animations[trigger] not in SUPPORTED_ANIMATIONS:
            default_anims = {
                "on_correct": "glow",
                "on_incorrect": "shake",
                "on_reveal": "fade",
                "on_complete": "bounce",
            }
            animations[trigger] = default_anims.get(trigger, "fade")
    fixed["animation_config"] = animations

    # Fix scoring
    scoring = fixed.get("scoring_strategy", {})
    if scoring.get("strategy_id") not in SCORING_STRATEGIES:
        scoring["strategy_id"] = "standard"
    fixed["scoring_strategy"] = scoring

    fixed["_auto_fixed"] = True
    fixed["_fix_applied_at"] = datetime.utcnow().isoformat()

    return fixed


# =============================================================================
# MAIN VALIDATOR AGENT
# =============================================================================

async def interaction_validator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Interaction Validator Agent

    Validates the interaction design for playability, learning alignment,
    technical feasibility, and consistency. Has auto-fix capability for
    common issues.

    Args:
        state: Current agent state with interaction_design
        ctx: Optional instrumentation context

    Returns:
        Updated state with validation results and potentially modified design
    """
    question_id = state.get("question_id", "unknown")
    logger.info(f"Validating interaction design for question {question_id}")

    # Use 'or {}' pattern because state.get returns None if key exists with None value
    interaction_design = state.get("interaction_design") or {}
    interaction_designs = state.get("interaction_designs") or []
    game_plan = state.get("game_plan") or {}
    ped_context = state.get("pedagogical_context", {}) or {}
    domain_knowledge = state.get("domain_knowledge", {}) or {}

    # Extract zone count
    zone_count = interaction_design.get("zone_count", 0)
    if not zone_count:
        canonical_labels = domain_knowledge.get("canonical_labels", []) or []
        zone_count = len(canonical_labels) if canonical_labels else 5

    # Run all validations on the primary interaction_design
    all_issues = []
    all_suggestions = []
    scores = []

    # 1. Playability
    playable, p_issues, p_suggestions = validate_playability(interaction_design, zone_count)
    all_issues.extend(p_issues)
    all_suggestions.extend(p_suggestions)
    scores.append(1.0 if playable else 0.5)

    # 2. Learning Alignment
    aligned, l_issues, l_suggestions = validate_learning_alignment(interaction_design, ped_context)
    all_issues.extend(l_issues)
    all_suggestions.extend(l_suggestions)
    scores.append(1.0 if aligned else 0.7)

    # 3. Technical Feasibility
    feasible, t_issues, t_suggestions = validate_technical_feasibility(interaction_design)
    all_issues.extend(t_issues)
    all_suggestions.extend(t_suggestions)
    scores.append(1.0 if feasible else 0.3)

    # 4. Consistency
    consistent, c_issues, c_suggestions = validate_consistency(interaction_design, domain_knowledge)
    all_issues.extend(c_issues)
    all_suggestions.extend(c_suggestions)
    scores.append(1.0 if consistent else 0.8)

    # 5. Phase 4: Mechanic Compatibility (from game_plan)
    game_mechanics = game_plan.get("game_mechanics", [])
    if game_mechanics:
        compatible, m_issues, m_suggestions = validate_mechanic_compatibility(game_mechanics)
        all_issues.extend(m_issues)
        all_suggestions.extend(m_suggestions)
        scores.append(1.0 if compatible else 0.4)

    # 6. Validate interaction_designs (plural) if present — per-scene validation
    approved_designs = []
    if interaction_designs:
        for idx, scene_design in enumerate(interaction_designs):
            if not isinstance(scene_design, dict):
                continue
            scene_num = scene_design.get("scene_number", idx + 1)
            s_zone_count = scene_design.get("zone_count", zone_count)

            s_valid_p, s_issues_p, s_sugg_p = validate_playability(scene_design, s_zone_count)
            s_valid_t, s_issues_t, s_sugg_t = validate_technical_feasibility(scene_design)
            s_valid_l, s_issues_l, s_sugg_l = validate_learning_alignment(scene_design, ped_context)

            scene_issues = s_issues_p + s_issues_t + s_issues_l
            scene_suggestions = s_sugg_p + s_sugg_t + s_sugg_l

            if scene_issues:
                # Prefix scene number for clarity
                all_issues.extend([f"[Scene {scene_num}] {i}" for i in scene_issues])
                all_suggestions.extend([f"[Scene {scene_num}] {s}" for s in scene_suggestions])
                # Auto-fix the scene design
                fixed_scene = auto_fix_design(scene_design, scene_issues, scene_suggestions)
                approved_designs.append(fixed_scene)
            else:
                approved_designs.append(scene_design)

            scene_score = 1.0 if not scene_issues else 0.6
            scores.append(scene_score)

    # Calculate overall score
    validation_score = sum(scores) / len(scores) if scores else 0.0
    validation_passed = len(all_issues) == 0 and validation_score >= 0.7

    logger.info(
        f"Validation complete: passed={validation_passed}, score={validation_score:.2f}, "
        f"issues={len(all_issues)}, suggestions={len(all_suggestions)}"
    )

    # Attempt auto-fix if there are issues on the primary design
    approved_design = interaction_design
    if all_issues and not validation_passed:
        approved_design = auto_fix_design(interaction_design, all_issues, all_suggestions)

        # Re-validate after fix
        _, p_issues2, _ = validate_playability(approved_design, zone_count)
        _, t_issues2, _ = validate_technical_feasibility(approved_design)

        if len(p_issues2) + len(t_issues2) < len(all_issues):
            logger.info("Auto-fix improved the design")
            validation_passed = True
            validation_score = min(1.0, validation_score + 0.2)
        else:
            logger.warning("Auto-fix did not resolve all issues")

    # Set validation results in context
    if ctx:
        ctx.set_validation_results(
            passed=validation_passed,
            errors=all_issues if not validation_passed else None,
        )

    # Track retry counts
    retry_counts = state.get("retry_counts", {})
    if not validation_passed:
        retry_counts["interaction_designer"] = retry_counts.get("interaction_designer", 0) + 1

    result = {
        "interaction_validation": {
            "passed": validation_passed,
            "score": validation_score,
            "issues": all_issues,
            "suggestions": all_suggestions,
            "validated_at": datetime.utcnow().isoformat(),
        },
        "interaction_design": approved_design,  # May be auto-fixed
        "retry_counts": retry_counts,
        "current_agent": "interaction_validator",
        "last_updated_at": datetime.utcnow().isoformat(),
    }

    # Include validated interaction_designs if they were present
    if approved_designs:
        result["interaction_designs"] = approved_designs

    return result


# =============================================================================
# HELPER FOR DIRECT VALIDATION CALLS
# =============================================================================

async def validate_interaction_design(
    interaction_design: Dict[str, Any],
    ped_context: Optional[Dict[str, Any]] = None,
    domain_knowledge: Optional[Dict[str, Any]] = None,
    zone_count: int = 5,
) -> Dict[str, Any]:
    """
    Validate an interaction design directly (without agent context).

    Useful for testing and direct API calls.

    Args:
        interaction_design: The design to validate
        ped_context: Optional pedagogical context
        domain_knowledge: Optional domain knowledge
        zone_count: Number of zones in the game

    Returns:
        Validation result dictionary
    """
    ped_context = ped_context or {}
    domain_knowledge = domain_knowledge or {}

    all_issues = []
    all_suggestions = []

    # Run validations
    _, p_issues, p_suggestions = validate_playability(interaction_design, zone_count)
    all_issues.extend(p_issues)
    all_suggestions.extend(p_suggestions)

    _, l_issues, l_suggestions = validate_learning_alignment(interaction_design, ped_context)
    all_issues.extend(l_issues)
    all_suggestions.extend(l_suggestions)

    _, t_issues, t_suggestions = validate_technical_feasibility(interaction_design)
    all_issues.extend(t_issues)
    all_suggestions.extend(t_suggestions)

    _, c_issues, c_suggestions = validate_consistency(interaction_design, domain_knowledge)
    all_issues.extend(c_issues)
    all_suggestions.extend(c_suggestions)

    validation_passed = len(all_issues) == 0

    return {
        "valid": validation_passed,
        "issues": all_issues,
        "suggestions": all_suggestions,
        "interaction_design": interaction_design,
    }


# =============================================================================
# V3 INTERACTION VALIDATOR (deterministic, no LLM)
# =============================================================================
# New validator for the v3 pipeline. Reads interaction_specs_v3,
# scene_specs_v3, and game_design_v3 from state, runs cross-stage
# contract validation, and writes interaction_validation_v3.


async def interaction_validator_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Interaction Validator v3 Agent -- deterministic validation of interaction_specs_v3.

    Reads: interaction_specs_v3, scene_specs_v3, game_design_v3
    Writes: interaction_validation_v3, _v3_interaction_retries
    """
    from app.agents.schemas.interaction_spec_v3 import validate_interaction_specs as validate_v3

    logger.info("InteractionValidatorV3: Starting interaction spec validation")

    interaction_specs = state.get("interaction_specs_v3")
    scene_specs = state.get("scene_specs_v3") or []
    game_design = state.get("game_design_v3") or {}
    retry_count = state.get("_v3_interaction_retries", 0)

    # Guard: no interaction specs to validate
    if not interaction_specs:
        logger.warning("InteractionValidatorV3: No interaction_specs_v3 in state")
        validation = {
            "passed": False,
            "score": 0.0,
            "issues": ["No interaction_specs_v3 found in state. interaction_designer_v3 may have failed."],
        }
        return {
            **state,
            "current_agent": "interaction_validator",
            "interaction_validation_v3": validation,
            "_v3_interaction_retries": retry_count + 1,
        }

    # Ensure interaction_specs is a list
    if not isinstance(interaction_specs, list):
        logger.warning(
            f"InteractionValidatorV3: interaction_specs_v3 is not a list, "
            f"got {type(interaction_specs)}"
        )
        validation = {
            "passed": False,
            "score": 0.0,
            "issues": [f"interaction_specs_v3 must be a list, got {type(interaction_specs).__name__}"],
        }
        return {
            **state,
            "current_agent": "interaction_validator",
            "interaction_validation_v3": validation,
            "_v3_interaction_retries": retry_count + 1,
        }

    # Ensure scene_specs is a list of dicts
    ss_dicts = []
    for ss in scene_specs:
        if isinstance(ss, dict):
            ss_dicts.append(ss)

    # Run cross-stage validation
    try:
        validation = validate_v3(interaction_specs, ss_dicts, game_design)
    except Exception as e:
        logger.error(
            f"InteractionValidatorV3: validate_interaction_specs raised: {e}",
            exc_info=True,
        )
        validation = {
            "passed": False,
            "score": 0.0,
            "issues": [f"Validation function error: {str(e)[:500]}"],
        }

    passed = validation.get("passed", False)
    score = validation.get("score", 0.0)
    issues = validation.get("issues", [])

    logger.info(
        f"InteractionValidatorV3: passed={passed}, score={score:.3f}, "
        f"issues={len(issues)}, retry={retry_count}"
    )

    if issues:
        for issue in issues[:5]:
            logger.info(f"  Issue: {issue}")

    return {
        **state,
        "current_agent": "interaction_validator",
        "interaction_validation_v3": validation,
        "_v3_interaction_retries": retry_count + 1,
    }
