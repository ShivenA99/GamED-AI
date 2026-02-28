"""
Game Design v3 Tools -- ReAct agent toolbox for game_designer_v3.

Five tools that give the game designer agent the ability to:
1. Analyze pedagogical context of a question (with domain knowledge injection)
2. Check frontend capabilities -- returns the FULL capability matrix
3. Retrieve example designs for few-shot inspiration
4. Validate a draft game design against schema + rules
5. Submit a final game design via Pydantic schema-as-tool

All tools are deterministic (no LLM calls) except analyze_pedagogy
which optionally enriches analysis with injected domain knowledge.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.tools.game_design_v3")


# ---------------------------------------------------------------------------
# Tool 1: analyze_pedagogy
# ---------------------------------------------------------------------------

async def analyze_pedagogy_impl(
    question: str,
    subject: str = "",
    blooms_level: str = "understand",
    learning_objectives: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyze the pedagogical requirements of a question.

    Injects domain_knowledge and canonical_labels from pipeline context
    (set via set_v3_tool_context) so the designer agent gets richer analysis.

    Returns Bloom's alignment, content type classification,
    recommended interaction patterns, and cognitive complexity.
    """
    from app.config.pedagogical_constants import (
        BLOOM_LEVELS,
        BLOOM_COMPLEXITY,
    )
    from app.config.interaction_patterns import INTERACTION_PATTERNS
    from app.tools.v3_context import get_v3_tool_context

    ctx = get_v3_tool_context()
    domain_knowledge = ctx.get("domain_knowledge", "")
    canonical_labels = ctx.get("canonical_labels", [])

    q_lower = question.lower()
    learning_objectives = learning_objectives or []

    # Enrich with context-injected labels if available
    if not learning_objectives and ctx.get("learning_objectives"):
        learning_objectives = ctx["learning_objectives"]

    # Content type detection
    content_type = "general"
    content_signals = {
        "anatomy": ["label", "identify", "parts", "organ", "anatomy", "body", "heart", "lung", "brain", "cell", "bone"],
        "process": ["flow", "cycle", "steps", "process", "sequence", "order", "path", "trace", "stage"],
        "comparison": ["compare", "contrast", "difference", "similar", "versus", "vs"],
        "hierarchy": ["hierarchy", "classify", "categories", "group", "tree", "branch", "level"],
        "functional_reasoning": ["function", "purpose", "why", "cause", "effect", "role", "how does"],
        "geography": ["map", "continent", "country", "region", "location", "geography"],
        "engineering": ["circuit", "engine", "machine", "component", "system", "diagram"],
    }
    for ctype, keywords in content_signals.items():
        if any(kw in q_lower for kw in keywords):
            content_type = ctype
            break

    # Bloom's validation and complexity
    if blooms_level not in BLOOM_LEVELS:
        blooms_level = "understand"
    cognitive_complexity = BLOOM_COMPLEXITY.get(blooms_level, 2)

    # Recommend interaction patterns based on content type + Bloom's
    recommended_patterns = []
    pattern_reasons = {}

    complexity_scores = {
        "low": 1, "low_to_medium": 1.5, "medium": 2,
        "medium_to_high": 2.5, "high": 3,
    }

    for pattern_id, pattern in INTERACTION_PATTERNS.items():
        if pattern.status.value == "deprecated":
            continue
        score = 0
        best_for = pattern.best_for or []
        if any(content_type in bf.lower() for bf in best_for):
            score += 3
        if any(q_lower_word in bf.lower() for bf in best_for for q_lower_word in q_lower.split()[:5]):
            score += 1
        pattern_complexity = pattern.complexity.value if pattern.complexity else "medium"
        if abs(complexity_scores.get(pattern_complexity, 2) - cognitive_complexity) <= 1:
            score += 1
        if score >= 2:
            recommended_patterns.append(pattern_id)
            pattern_reasons[pattern_id] = f"score={score}, complexity={pattern_complexity}"

    # drag_drop is available but NOT forced as a recommendation.
    # The game designer agent chooses mechanics based on content type,
    # pedagogical fit, and check_capabilities results.

    # Multi-scene suggestion
    multi_scene_suggested = (
        cognitive_complexity >= 3
        or content_type in ("process", "comparison", "functional_reasoning")
        or len(recommended_patterns) >= 3
    )

    # Scoring strategy recommendation
    scoring_strategy = "standard"
    if content_type == "process":
        scoring_strategy = "progressive"
    elif cognitive_complexity >= 4:
        scoring_strategy = "mastery"
    elif "timed_challenge" in recommended_patterns:
        scoring_strategy = "time_based"

    result: Dict[str, Any] = {
        "blooms_level": blooms_level,
        "cognitive_complexity": cognitive_complexity,
        "content_type": content_type,
        "subject": subject or ctx.get("subject", "general"),
        "recommended_patterns": recommended_patterns,
        "pattern_reasons": pattern_reasons,
        "multi_scene_suggested": multi_scene_suggested,
        "scoring_strategy": scoring_strategy,
        "learning_objectives": learning_objectives,
    }

    # Inject domain knowledge summary if available
    if domain_knowledge:
        dk_text = domain_knowledge if isinstance(domain_knowledge, str) else json.dumps(domain_knowledge)
        result["domain_knowledge_summary"] = dk_text[:1500]

    # Inject canonical labels if available
    if canonical_labels:
        result["canonical_labels"] = canonical_labels[:30]
        result["label_count"] = len(canonical_labels)

    return result


# ---------------------------------------------------------------------------
# Tool 2: check_capabilities (no args -- returns full matrix)
# ---------------------------------------------------------------------------

async def check_capabilities_impl() -> Dict[str, Any]:
    """
    Return the FULL capability matrix of all interaction mechanics.

    No arguments required. Returns every READY/PARTIAL mechanic with:
    - status, complexity, config schema, supported types, requirements

    Fix 2.12: Also returns data_requirements per mechanic indicating what
    upstream data each mechanic needs to function properly, and checks
    what data is currently available from the pipeline context.
    """
    from app.config.interaction_patterns import (
        INTERACTION_PATTERNS,
        PatternStatus,
    )
    from app.tools.v3_context import get_v3_tool_context

    ctx = get_v3_tool_context()

    # Check what upstream data is available (DK sub-fields may be under domain_knowledge dict)
    dk = ctx.get("domain_knowledge", {})
    dk_dict = dk if isinstance(dk, dict) else {}
    has_label_descriptions = bool(dk_dict.get("label_descriptions") or ctx.get("label_descriptions"))
    has_sequence_flow_data = bool(dk_dict.get("sequence_flow_data") or ctx.get("sequence_flow_data"))
    has_comparison_data = bool(dk_dict.get("comparison_data") or ctx.get("comparison_data"))
    canonical_labels = ctx.get("canonical_labels", [])

    # Per-mechanic data requirements and availability
    MECHANIC_DATA_NEEDS: Dict[str, Dict[str, Any]] = {
        "drag_drop": {
            "required_data": ["canonical_labels"],
            "optional_data": [],
            "data_available": True,  # Always available
            "readiness_note": "Fully ready - uses zone labels only",
        },
        "click_to_identify": {
            "required_data": ["canonical_labels"],
            "optional_data": ["label_descriptions"],
            "data_available": True,
            "readiness_note": "Ready. Better with label_descriptions for rich prompts"
                              + (" (available)" if has_label_descriptions else " (not available)"),
        },
        "trace_path": {
            "required_data": ["canonical_labels"],
            "optional_data": ["sequence_flow_data"],
            "data_available": True,
            "readiness_note": "Ready. Sequence data "
                              + ("available for waypoints" if has_sequence_flow_data else "not available - will use LLM to generate waypoints"),
        },
        "sequencing": {
            "required_data": ["canonical_labels"],
            "optional_data": ["sequence_flow_data"],
            "data_available": True,
            "readiness_note": "Ready. Sequence data "
                              + ("available for correct order" if has_sequence_flow_data else "not available - will need LLM"),
        },
        "description_matching": {
            "required_data": ["label_descriptions"],
            "optional_data": [],
            "data_available": has_label_descriptions,
            "readiness_note": "Label descriptions " + ("available" if has_label_descriptions else "NOT available - mechanic will have limited effectiveness"),
        },
        "sorting_categories": {
            "required_data": ["canonical_labels"],
            "optional_data": ["comparison_data"],
            "data_available": True,
            "readiness_note": "Ready. Comparison data "
                              + ("available with sorting categories" if has_comparison_data else "not available - will need manual categories"),
        },
        "memory_match": {
            "required_data": ["canonical_labels"],
            "optional_data": ["label_descriptions"],
            "data_available": True,
            "readiness_note": "Ready. Label descriptions "
                              + ("available for card backs" if has_label_descriptions else "not available - will use generic descriptions"),
        },
        "branching_scenario": {
            "required_data": ["canonical_labels"],
            "optional_data": [],
            "data_available": True,
            "readiness_note": "Ready but complex - needs careful scenario design",
        },
        "compare_contrast": {
            "required_data": ["canonical_labels"],
            "optional_data": ["comparison_data"],
            "data_available": True,
            "readiness_note": "Comparison data "
                              + ("available" if has_comparison_data else "not available - will need manual categorization"),
        },
    }

    mechanics = {}
    ready_types = []
    partial_types = []

    for pattern_id, pattern in INTERACTION_PATTERNS.items():
        status = pattern.status.value
        if status not in ("complete", "partial"):
            continue

        if status == "complete":
            ready_types.append(pattern_id)
        else:
            partial_types.append(pattern_id)

        data_needs = MECHANIC_DATA_NEEDS.get(pattern_id, {})

        mechanics[pattern_id] = {
            "name": pattern.name,
            "status": status.upper(),
            "complexity": pattern.complexity.value,
            "description": pattern.description[:200],
            "cognitive_demands": pattern.cognitive_demands,
            "best_for": pattern.best_for[:4],
            "supports_multi_scene": pattern.supports_multi_scene,
            "supports_timing": pattern.supports_timing,
            "supports_partial_credit": pattern.supports_partial_credit,
            "can_combine_with": pattern.can_combine_with,
            "configuration_schema": pattern.configuration_options,
            "frontend_component": pattern.frontend_component,
            "prerequisites": pattern.prerequisites,
            # Fix 2.12: Data availability info
            "data_requirements": data_needs.get("required_data", []),
            "data_available": data_needs.get("data_available", True),
            "readiness_note": data_needs.get("readiness_note", ""),
        }

    return {
        "ready_types": ready_types,
        "partial_types": partial_types,
        "total_available": len(mechanics),
        "mechanics": mechanics,
        # Fix 2.12: Pipeline data availability summary
        "pipeline_data_status": {
            "canonical_labels": len(canonical_labels),
            "label_descriptions_available": has_label_descriptions,
            "sequence_flow_data_available": has_sequence_flow_data,
            "comparison_data_available": has_comparison_data,
        },
    }


# ---------------------------------------------------------------------------
# Tool 3: get_example_designs
# ---------------------------------------------------------------------------

async def get_example_designs_impl(
    content_type: str = "anatomy",
    max_examples: int = 3,
) -> Dict[str, Any]:
    """
    Retrieve example game designs for few-shot inspiration.

    Returns exemplar designs matching the content type.
    """
    from app.config.example_game_designs import (
        get_example_for_content_type,
        get_multi_scene_examples,
        EXAMPLE_GAME_DESIGNS,
    )

    examples = []
    reasoning_patterns = []

    # Get content-type specific example
    try:
        primary = get_example_for_content_type(content_type)
        if primary:
            if isinstance(primary, list):
                examples.extend(primary[:max_examples])
            else:
                examples.append(primary)
    except Exception as e:
        logger.warning(f"get_example_for_content_type failed: {e}")

    # Get multi-scene examples
    try:
        multi = get_multi_scene_examples()
        if isinstance(multi, list):
            for ex in multi:
                if len(examples) < max_examples and ex not in examples:
                    examples.append(ex)
        elif isinstance(multi, dict):
            if len(examples) < max_examples:
                examples.append(multi)
    except Exception as e:
        logger.warning(f"get_multi_scene_examples failed: {e}")

    # Fill with any remaining examples
    if len(examples) < max_examples:
        for ex in EXAMPLE_GAME_DESIGNS:
            if len(examples) >= max_examples:
                break
            if ex not in examples:
                examples.append(ex)

    # Extract reasoning patterns from examples
    for ex in examples:
        if isinstance(ex, dict):
            pattern = ex.get("reasoning_pattern") or ex.get("pedagogical_approach", "")
            if pattern:
                reasoning_patterns.append(pattern)

    return {
        "examples": examples[:max_examples],
        "num_examples": len(examples[:max_examples]),
        "reasoning_patterns": reasoning_patterns,
        "content_type_requested": content_type,
    }


# ---------------------------------------------------------------------------
# Tool 4: validate_design
# ---------------------------------------------------------------------------

async def validate_design_impl(
    design: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate a draft game design against the GameDesignV3Slim schema and rules.

    Returns validation results with errors, warnings, and suggestions.
    """
    from app.agents.schemas.game_design_v3 import (
        GameDesignV3Slim,
        validate_slim_game_design,
        VALID_MECHANIC_TYPES,
    )

    errors = []
    warnings = []
    suggestions = []

    # Step 1: Pydantic schema validation
    try:
        parsed = GameDesignV3Slim.model_validate(design)
    except Exception as e:
        error_str = str(e)
        actionable_errors = []
        for line in error_str.split("\n"):
            line = line.strip()
            if not line or line.startswith("For further") or "validation error" in line.lower():
                continue
            actionable_errors.append(line)
        if len(actionable_errors) > 10:
            actionable_errors = actionable_errors[:10] + [f"... and {len(actionable_errors) - 10} more errors"]
        return {
            "valid": False,
            "errors": actionable_errors if actionable_errors else [f"Schema validation failed: {error_str[:500]}"],
            "warnings": [],
            "suggestions": [
                "Common fixes: 'theme' should be an object like {\"visual_tone\": \"educational\"}, not a string",
                "zone_labels should be a list of strings like [\"Left Atrium\", \"Right Ventricle\"]",
                "Each scene needs 'mechanics' as a list of objects with 'type' field",
                "Each scene needs scene_number, title, visual_description, zone_labels_in_scene",
            ],
            "alignment_score": 0.0,
        }

    # Step 2: Rule-based validation
    rule_issues = validate_slim_game_design(parsed)

    for issue in rule_issues:
        if "FATAL" in issue.upper() or "ERROR" in issue.upper():
            errors.append(issue)
        elif "WARNING" in issue.upper():
            warnings.append(issue)
        else:
            warnings.append(issue)

    # Step 3: Quality checks
    score = 1.0

    if len(parsed.scenes) == 0:
        errors.append("No scenes defined")
        score -= 0.3
    elif len(parsed.scenes) > 5:
        warnings.append(f"High scene count ({len(parsed.scenes)}). Consider keeping to 3-4 scenes.")
        score -= 0.05

    # Check mechanic diversity
    all_mechanic_types = set()
    for scene in parsed.scenes:
        for mech in scene.mechanics:
            all_mechanic_types.add(mech.type)

    if len(all_mechanic_types) == 0:
        errors.append("No mechanics defined in any scene")
        score -= 0.3
    elif len(all_mechanic_types) == 1 and len(parsed.scenes) > 1:
        warnings.append("All scenes use the same mechanic. Consider varying for engagement.")
        score -= 0.05

    # Check label coverage
    if parsed.labels:
        zone_labels = parsed.labels.zone_labels or []
        if len(zone_labels) < 3:
            warnings.append(f"Only {len(zone_labels)} zone labels. Educational games typically need 5+.")
            score -= 0.05

    # Apply rule-based issue deductions
    score -= len(errors) * 0.15
    score -= len(warnings) * 0.03
    score = max(0.0, min(1.0, score))

    valid = len(errors) == 0 and score >= 0.7

    # Generate suggestions
    if not valid and len(suggestions) == 0:
        if errors:
            suggestions.append("Fix the errors listed above and re-validate")
        if score < 0.7:
            suggestions.append("Add more detail to label definitions and mechanic types")

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "alignment_score": round(score, 3),
        "stats": {
            "scene_count": len(parsed.scenes),
            "mechanic_types": sorted(all_mechanic_types),
            "label_count": len(parsed.labels.zone_labels) if parsed.labels else 0,
        },
    }


# ---------------------------------------------------------------------------
# Tool 5: submit_game_design (Pydantic schema-as-tool)
# ---------------------------------------------------------------------------

async def submit_game_design_impl(**kwargs) -> Dict[str, Any]:
    """
    Submit the final game design for downstream processing.

    Parameters mirror the GameDesignV3Slim schema. On success, returns
    {status: "accepted", summary}. On failure, returns
    {status: "rejected", errors, hint}.

    Fix 2.3c: Tries GameDesignV3 (full) first for richer validation;
    falls back to GameDesignV3Slim if the full schema doesn't parse.
    """
    from app.agents.schemas.game_design_v3 import (
        GameDesignV3,
        GameDesignV3Slim,
        validate_slim_game_design,
        validate_game_design,
    )

    # Try full GameDesignV3 first for richer mechanic validation
    try:
        full_parsed = GameDesignV3.model_validate(kwargs)
        full_issues = validate_game_design(full_parsed)
        if not full_issues:
            logger.info("submit_game_design: Accepted via full GameDesignV3 schema")
            return {
                "status": "accepted",
                "summary": f"{len(full_parsed.scenes)}-scene game | {full_parsed.title}",
                "validation_level": "full",
            }
        else:
            # Full schema parsed but has rule issues -- log and continue to slim
            logger.info(f"submit_game_design: Full schema rule issues: {full_issues[:3]}. Trying slim.")
    except Exception:
        # Full schema didn't parse -- that's expected for slim designs
        pass

    # Fall back to slim validation
    try:
        parsed = GameDesignV3Slim.model_validate(kwargs)
    except Exception as e:
        error_str = str(e)
        actionable = []
        for line in error_str.split("\n"):
            line = line.strip()
            if not line or line.startswith("For further") or "validation error" in line.lower():
                continue
            actionable.append(line)
        return {
            "status": "rejected",
            "errors": actionable[:8] if actionable else [error_str[:500]],
            "hint": "Ensure title, scenes (with scene_number, mechanics, zone_labels_in_scene), and labels (with zone_labels) are present.",
        }

    # Rule-based validation
    issues = validate_slim_game_design(parsed)
    if issues:
        return {
            "status": "rejected",
            "errors": issues,
            "hint": "Fix the structural issues and resubmit.",
        }

    return {
        "status": "accepted",
        "summary": parsed.summary(),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_game_design_v3_tools() -> None:
    """Register all v3 game design tools in the tool registry."""
    from app.tools.registry import register_tool

    register_tool(
        name="analyze_pedagogy",
        description=(
            "Analyze the pedagogical requirements of an educational question. "
            "Returns Bloom's level alignment, content type, recommended interaction "
            "patterns, domain knowledge summary, canonical labels, and whether "
            "multi-scene is appropriate."
        ),
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The educational question text",
                },
                "subject": {
                    "type": "string",
                    "description": "Subject area (e.g., biology, physics)",
                },
                "blooms_level": {
                    "type": "string",
                    "description": "Bloom's taxonomy level",
                    "enum": ["remember", "understand", "apply", "analyze", "evaluate", "create"],
                },
                "learning_objectives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Expected learning outcomes",
                },
            },
            "required": ["question"],
        },
        function=analyze_pedagogy_impl,
    )

    register_tool(
        name="check_capabilities",
        description=(
            "Return the FULL capability matrix of all implemented interaction mechanics. "
            "No arguments required. Returns every READY and PARTIAL mechanic with its "
            "status, complexity, config schema, supported types, requirements, and "
            "combinability information."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=check_capabilities_impl,
    )

    register_tool(
        name="get_example_designs",
        description=(
            "Retrieve example game designs for few-shot inspiration. "
            "Returns exemplar designs matching the requested content type."
        ),
        parameters={
            "type": "object",
            "properties": {
                "content_type": {
                    "type": "string",
                    "description": "Content type to find examples for",
                    "enum": ["anatomy", "process", "comparison", "hierarchy", "general", "engineering", "geography"],
                },
                "max_examples": {
                    "type": "integer",
                    "description": "Maximum examples to return",
                    "default": 3,
                },
            },
            "required": ["content_type"],
        },
        function=get_example_designs_impl,
    )

    register_tool(
        name="validate_design",
        description=(
            "Validate a draft game design against the GameDesignV3Slim schema and "
            "pedagogical rules. Returns errors, warnings, suggestions, and an "
            "alignment score (0-1). Use this to check your design before submitting."
        ),
        parameters={
            "type": "object",
            "properties": {
                "design": {
                    "type": "object",
                    "description": "The game design JSON to validate",
                },
            },
            "required": ["design"],
        },
        function=validate_design_impl,
    )

    register_tool(
        name="submit_game_design",
        description=(
            "Submit the final game design for downstream processing. "
            "Pass the COMPLETE game design as the arguments to this tool. "
            "It validates against the GameDesignV3Slim schema. "
            "Returns {status: 'accepted', summary} on success, or "
            "{status: 'rejected', errors, hint} on failure."
        ),
        parameters={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Game title",
                },
                "pedagogical_reasoning": {
                    "type": "string",
                    "description": "Why this design is pedagogically effective",
                },
                "learning_objectives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What the student will learn",
                },
                "estimated_duration_minutes": {
                    "type": "integer",
                    "description": "Estimated play time in minutes",
                },
                "theme": {
                    "type": "object",
                    "description": "Visual theme config, e.g. {visual_tone: 'clinical_educational'}",
                },
                "labels": {
                    "type": "object",
                    "description": "Global label definitions: {zone_labels: [...], distractor_labels: [...]}",
                },
                "scenes": {
                    "type": "array",
                    "description": "List of scene objects with scene_number, title, visual_description, mechanics, zone_labels_in_scene",
                    "items": {"type": "object"},
                },
                "scene_transitions": {
                    "type": "array",
                    "description": "Transitions between scenes: [{from_scene, to_scene, trigger}]",
                    "items": {"type": "object"},
                },
                "difficulty": {
                    "type": "object",
                    "description": "Difficulty settings: {approach, initial_level, hint_enabled}",
                },
            },
            "required": ["title", "labels", "scenes"],
        },
        function=submit_game_design_impl,
    )

    logger.info("Registered 5 v3 game design tools")
