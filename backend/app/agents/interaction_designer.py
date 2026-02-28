"""
Interaction Designer Agent

Designs custom interaction patterns for educational games based on:
- Bloom's taxonomy level
- Pedagogical context (subject, difficulty, learning objectives)
- Domain knowledge (hierarchical relationships, content structure)
- Game requirements (zone count, hierarchy depth)
- Scene breakdown from game_plan (multi-scene, multi-mechanic support)

This agent replaces hardcoded Bloom's→mode mappings with agentic reasoning.
It outputs a complete interaction_design that downstream agents use.

For multi-scene games, this agent:
1. Reads game_plan.scene_breakdown to get per-scene mechanics
2. Generates interaction_designs[] array (one per scene)
3. Creates mode_transitions for multi-mechanic scenes

Outputs:
- interaction_designs: List of per-scene interaction designs (new)
- interaction_design: Single design for backward compatibility (first scene)

Each interaction_design contains:
- scene_number: Which scene this design is for
- primary_interaction_mode: Main interaction pattern
- secondary_modes: Additional compatible patterns
- mode_transitions: Transitions between mechanics within the scene
- zone_behaviors: Per-zone type decisions (point vs area)
- reveal_strategy: Progressive reveal configuration
- feedback_strategy: Contextual feedback approach
- scoring_strategy: Dynamic scoring configuration
- animation_config: Appropriate animations for interactions
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.config.pedagogical_constants import DEFAULT_SCORING, DEFAULT_FEEDBACK, DEFAULT_THRESHOLDS, DIFFICULTY_LEVEL
from app.config.interaction_patterns import (
    INTERACTION_PATTERNS,
    SCORING_STRATEGIES,
    SUPPORTED_ANIMATIONS,
    format_patterns_for_prompt,
    format_scoring_strategies_for_prompt,
    format_animations_for_prompt,
    get_pattern,
    get_frontend_supported_patterns,
    suggest_secondary_modes,
    validate_multi_mode_combination,
    get_animations_for_use_case,
    PatternStatus,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.interaction_designer")


# =============================================================================
# INTERACTION DESIGNER PROMPT
# =============================================================================

INTERACTION_DESIGNER_PROMPT = """You are an expert educational interaction designer. Design optimal interaction patterns for a learning game based on the pedagogical context and content structure.

## Scene Context:
Scene Number: {scene_number}
Scene Title: {scene_title}
Scene Description: {scene_description}
Mechanics for this Scene: {scene_mechanics}

## Question to Gamify:
{question_text}

## Pedagogical Context:
- Bloom's Level: {blooms_level}
- Subject: {subject}
- Difficulty: {difficulty}
- Learning Objectives: {learning_objectives}
- Key Concepts: {key_concepts}

## Content Structure:
- Total Labels/Zones: {zone_count}
- Hierarchical Depth: {hierarchy_depth}
- Has Parent-Child Relationships: {has_hierarchy}
- Hierarchy Type: {hierarchy_type}

## Domain Knowledge:
{domain_knowledge_summary}

## Available Interaction Patterns:
{available_patterns}

## Available Scoring Strategies:
{scoring_strategies}

## Available Animations:
{available_animations}

## Design Task:

Design an interaction approach that:
1. **Matches Cognitive Level**: Bloom's '{blooms_level}' level requires appropriate cognitive engagement
2. **Supports Content Structure**: {zone_count} zones with {hierarchy_depth}-level depth
3. **Enables Learning**: Interaction should reinforce the learning objectives
4. **Considers Difficulty**: {difficulty} difficulty should inform challenge level

## Design Reasoning Guidelines:

**For "remember" level**: Simple identification/recall - click_to_identify or basic drag_drop
**For "understand" level**: Demonstrate comprehension - drag_drop with descriptions
**For "apply" level**: Use knowledge in context - description_matching, trace_path
**For "analyze" level**: Break down relationships - hierarchical, compare_contrast
**For "evaluate" level**: Judge and compare - compare_contrast, branching_scenario
**For "create" level**: Synthesize new - sequencing, open-ended tasks

**For hierarchical content**: Use progressive reveal with appropriate trigger
**For flat content**: Standard drag_drop or click_to_identify

## Response Format (JSON):
{{
    "primary_interaction_mode": "<mode_id from available patterns>",
    "secondary_modes": ["<optional additional compatible modes>"],
    "design_rationale": "<2-3 sentences explaining why this design fits the learning goals>",
    "zone_behavior_strategy": {{
        "default_zone_type": "circle|polygon",
        "use_point_zones_for": ["<criteria for point/dot zones, e.g., 'small structures', 'simple labels'>"],
        "use_area_zones_for": ["<criteria for polygon zones, e.g., 'large structures', 'complex boundaries'>"]
    }},
    "reveal_strategy": {{
        "type": "progressive_hierarchical|flat|sequential",
        "trigger": "complete_parent|click_expand|hover_reveal|all_at_once",
        "reveal_order": "hierarchy_based|difficulty_based|random|suggested_order"
    }},
    "feedback_strategy": {{
        "on_correct": "<contextual praise approach>",
        "on_incorrect": "<helpful correction approach>",
        "hint_progression": ["structural", "functional", "direct"],
        "use_misconception_feedback": true
    }},
    "scoring_strategy": {{
        "strategy_id": "<id from available strategies>",
        "base_points_per_zone": <number based on difficulty>,
        "partial_credit": true|false,
        "time_bonus": {{
            "enabled": true|false,
            "max_bonus": <number>
        }},
        "hint_penalty": <percentage 0-50>
    }},
    "animation_config": {{
        "on_correct": "<animation_id>",
        "on_incorrect": "<animation_id>",
        "on_reveal": "<animation_id>",
        "on_complete": "<animation_id>"
    }},
    "multi_mode_config": {{
        "enabled": false,
        "mode_sequence": [],
        "transition_trigger": "scene_complete|zone_count|manual"
    }},
    "mode_transitions": [
        {{
            "from_mode": "<mode_id>",
            "to_mode": "<mode_id>",
            "trigger": "all_zones_labeled|percentage_complete|user_choice|path_complete",
            "trigger_value": null,
            "animation": "fade_transition|slide|zoom"
        }}
    ]
}}

IMPORTANT for multi-mechanic scenes:
- If the scene has multiple mechanics (e.g., ["drag_drop", "trace_path"]), generate mode_transitions.
- The primary_interaction_mode should be the FIRST mechanic.
- secondary_modes should include the remaining mechanics.
- mode_transitions should define how players move from one mechanic to the next.

Respond with ONLY valid JSON. Choose from the available patterns and strategies listed above."""


def _build_domain_knowledge_summary(domain_knowledge: Dict[str, Any]) -> str:
    """Build a summary of domain knowledge for the prompt."""
    if not domain_knowledge:
        return "No domain knowledge available"

    lines = []

    # Canonical labels
    labels = domain_knowledge.get("canonical_labels", [])
    if labels:
        lines.append(f"Labels to include: {', '.join(labels[:10])}")
        if len(labels) > 10:
            lines.append(f"  (and {len(labels) - 10} more...)")

    # Hierarchical relationships
    relationships = domain_knowledge.get("hierarchical_relationships", [])
    if relationships:
        lines.append("Hierarchical relationships:")
        for rel in relationships[:5]:
            if isinstance(rel, dict):
                parent = rel.get("parent", "")
                children = rel.get("children", [])
                rel_type = rel.get("relationship_type", "contains")
                lines.append(f"  - {parent} ({rel_type}): {', '.join(children[:5])}")

    # Common misconceptions
    misconceptions = domain_knowledge.get("common_misconceptions", [])
    if misconceptions:
        lines.append("Common misconceptions to address:")
        for m in misconceptions[:3]:
            lines.append(f"  - {m}")

    # Suggested reveal order
    reveal_order = domain_knowledge.get("suggested_reveal_order", [])
    if reveal_order:
        lines.append(f"Suggested reveal order: {' -> '.join(reveal_order[:5])}")

    return "\n".join(lines) if lines else "Basic labeling task"


def _calculate_hierarchy_info(domain_knowledge: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate hierarchy information from domain knowledge."""
    relationships = domain_knowledge.get("hierarchical_relationships", []) or []

    if not relationships:
        return {
            "has_hierarchy": False,
            "hierarchy_depth": 1,
            "hierarchy_type": "flat",
            "parent_count": 0,
            "child_count": 0,
        }

    # Count parents and children
    parents = set()
    children = set()
    relationship_types = set()

    for rel in relationships:
        if isinstance(rel, dict):
            parent = rel.get("parent", "")
            if parent:
                parents.add(parent.lower())
            for child in rel.get("children", []):
                children.add(child.lower())
            rel_type = rel.get("relationship_type", "")
            if rel_type:
                relationship_types.add(rel_type)

    # Determine hierarchy type
    hierarchy_type = "discrete"  # default
    if "composed_of" in relationship_types or "subdivided_into" in relationship_types:
        hierarchy_type = "layered"
    elif "contains" in relationship_types or "has_part" in relationship_types:
        hierarchy_type = "discrete"

    # Estimate depth (simple approximation)
    depth = 2 if parents else 1
    nested_children = parents & children
    if nested_children:
        depth = 3

    return {
        "has_hierarchy": bool(parents),
        "hierarchy_depth": depth,
        "hierarchy_type": hierarchy_type,
        "parent_count": len(parents),
        "child_count": len(children),
        "relationship_types": list(relationship_types),
    }


async def interaction_designer(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Interaction Designer Agent

    Designs custom interaction patterns for educational games using agentic
    reasoning instead of hardcoded Bloom's→mode mappings.

    For multi-scene games with scene_breakdown, generates interaction_designs[]
    with one entry per scene, including per-scene mode_transitions.

    Args:
        state: Current agent state with game_plan and domain_knowledge
        ctx: Optional instrumentation context

    Returns:
        Updated state with interaction_designs (list) and interaction_design (first item for backward compat)
    """
    question_id = state.get("question_id", "unknown")
    logger.info(f"Designing interactions for question {question_id}")

    # Extract inputs
    question_text = state.get("question_text", "")
    ped_context = state.get("pedagogical_context", {}) or {}
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    game_plan = state.get("game_plan", {}) or {}
    template_type = state.get("template_selection", {}).get("template_type", "")

    # Calculate content structure
    canonical_labels = domain_knowledge.get("canonical_labels", []) or []
    zone_count = len(canonical_labels) if canonical_labels else 5
    hierarchy_info = _calculate_hierarchy_info(domain_knowledge)

    # Get scene_breakdown from game_plan for per-scene design
    scene_breakdown = game_plan.get("scene_breakdown", [])

    # If no scene_breakdown, create a single default scene
    if not scene_breakdown:
        # Pick a sensible default mechanic based on template_type
        template_selection = state.get("template_selection", {}) or {}
        ttype = template_selection.get("template_type", "").upper()
        _template_default_mechanic = {
            "INTERACTIVE_DIAGRAM": "drag_drop",
            "TRACE_PATH": "trace_path",
            "SEQUENCING": "sequencing",
            "SORTING": "sorting_categories",
            "COMPARE_CONTRAST": "compare_contrast",
            "MATCHING": "description_matching",
            "PHET_SIMULATION": "drag_drop",
            "MEMORY_MATCH": "memory_match",
            "TIMED_CHALLENGE": "timed_challenge",
            "BRANCHING_SCENARIO": "branching_scenario",
        }
        default_mechanic = _template_default_mechanic.get(ttype, "")
        scene_breakdown = [{
            "scene_number": 1,
            "title": "Main Scene",
            "description": "",
            "mechanics": [{"type": default_mechanic}],
            "asset_needs": {},
            "mode_transitions": []
        }]
        logger.debug(f"No scene_breakdown found, using single default scene with mechanic '{default_mechanic}' (template_type={ttype})")
    else:
        logger.info(f"Found {len(scene_breakdown)} scenes in game_plan.scene_breakdown")

    # Generate interaction design for each scene
    interaction_designs = []

    try:
        llm = get_llm_service()

        for scene_def in scene_breakdown:
            scene_number = scene_def.get("scene_number", len(interaction_designs) + 1)
            scene_title = scene_def.get("title", f"Scene {scene_number}")
            scene_description = scene_def.get("description", "")
            scene_mechanics = scene_def.get("mechanics", [])

            # Extract mechanic types from scene definition
            mechanic_types = [
                m.get("type") if isinstance(m, dict) else str(m)
                for m in scene_mechanics
            ]

            logger.debug(f"Designing interactions for scene {scene_number}: {scene_title}, mechanics={mechanic_types}")

            # Build per-scene prompt
            prompt = INTERACTION_DESIGNER_PROMPT.format(
                scene_number=scene_number,
                scene_title=scene_title,
                scene_description=scene_description or "No specific description",
                scene_mechanics=json.dumps(mechanic_types),
                question_text=question_text,
                blooms_level=ped_context.get("blooms_level", "understand"),
                subject=ped_context.get("subject", "General"),
                difficulty=ped_context.get("difficulty", "intermediate"),
                learning_objectives=json.dumps(ped_context.get("learning_objectives", [])),
                key_concepts=json.dumps(ped_context.get("key_concepts", [])),
                zone_count=zone_count,
                hierarchy_depth=hierarchy_info.get("hierarchy_depth", 1),
                has_hierarchy=hierarchy_info.get("has_hierarchy", False),
                hierarchy_type=hierarchy_info.get("hierarchy_type", "flat"),
                domain_knowledge_summary=_build_domain_knowledge_summary(domain_knowledge),
                available_patterns=format_patterns_for_prompt(),
                scoring_strategies=format_scoring_strategies_for_prompt(),
                available_animations=format_animations_for_prompt(),
            )

            result = await llm.generate_json_for_agent(
                agent_name="interaction_designer",
                prompt=prompt,
                schema_hint="InteractionDesign JSON with primary_interaction_mode, mode_transitions, scoring_strategy, etc.",
            )

            # Extract LLM metrics — aggregate across all scenes
            llm_metrics = result.pop("_llm_metrics", None) if isinstance(result, dict) else None
            if llm_metrics and ctx:
                if scene_number == 1:
                    # First scene: set initial metrics
                    ctx.set_llm_metrics(
                        model=llm_metrics.get("model"),
                        prompt_tokens=llm_metrics.get("prompt_tokens"),
                        completion_tokens=llm_metrics.get("completion_tokens"),
                        latency_ms=llm_metrics.get("latency_ms"),
                    )
                else:
                    # Subsequent scenes: accumulate token counts and latency
                    existing = getattr(ctx, '_llm_metrics', None)
                    if existing:
                        ctx.set_llm_metrics(
                            model=existing.get("model") or llm_metrics.get("model"),
                            prompt_tokens=(existing.get("prompt_tokens") or 0) + (llm_metrics.get("prompt_tokens") or 0),
                            completion_tokens=(existing.get("completion_tokens") or 0) + (llm_metrics.get("completion_tokens") or 0),
                            latency_ms=(existing.get("latency_ms") or 0) + (llm_metrics.get("latency_ms") or 0),
                        )
                    else:
                        ctx.set_llm_metrics(
                            model=llm_metrics.get("model"),
                            prompt_tokens=llm_metrics.get("prompt_tokens"),
                            completion_tokens=llm_metrics.get("completion_tokens"),
                            latency_ms=llm_metrics.get("latency_ms"),
                        )

            # Normalize and validate result for this scene
            scene_interaction_design = _normalize_interaction_design(
                result, ped_context, hierarchy_info, zone_count, scene_number, mechanic_types
            )

            interaction_designs.append(scene_interaction_design)

            logger.info(
                f"Designed interaction for scene {scene_number}: "
                f"primary={scene_interaction_design.get('primary_interaction_mode')}, "
                f"secondary={scene_interaction_design.get('secondary_modes')}, "
                f"transitions={len(scene_interaction_design.get('mode_transitions', []))}"
            )

        # Backward compatibility: also return single interaction_design as first item
        first_design = interaction_designs[0] if interaction_designs else _create_fallback_design(
            ped_context, hierarchy_info, zone_count, scene_number=1, mechanic_types=[]
        )

        return {
            "interaction_designs": interaction_designs,
            "interaction_design": first_design,  # Backward compatibility
            "current_agent": "interaction_designer",
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Interaction designer failed: {e}", exc_info=True)

        # Use fallback designs for each scene
        fallback_designs = []
        for scene_def in scene_breakdown:
            scene_number = scene_def.get("scene_number", len(fallback_designs) + 1)
            scene_mechanics = scene_def.get("mechanics", [])
            mechanic_types = [
                m.get("type") if isinstance(m, dict) else str(m)
                for m in scene_mechanics
            ]
            fallback = _create_fallback_design(
                ped_context, hierarchy_info, zone_count, scene_number, mechanic_types
            )
            fallback_designs.append(fallback)

        if ctx:
            ctx.set_fallback_used(f"Interaction designer failed: {str(e)}")

        first_fallback = fallback_designs[0] if fallback_designs else _create_fallback_design(
            ped_context, hierarchy_info, zone_count, scene_number=1, mechanic_types=[]
        )

        return {
            "interaction_designs": fallback_designs,
            "interaction_design": first_fallback,  # Backward compatibility
            "current_agent": "interaction_designer",
            "last_updated_at": datetime.utcnow().isoformat(),
            "_used_fallback": True,
            "_fallback_reason": str(e),
        }


def _normalize_interaction_design(
    result: Dict[str, Any],
    ped_context: Dict[str, Any],
    hierarchy_info: Dict[str, Any],
    zone_count: int,
    scene_number: int = 1,
    mechanic_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Normalize and validate the LLM interaction design result.

    Args:
        result: Raw LLM result
        ped_context: Pedagogical context
        hierarchy_info: Hierarchy information
        zone_count: Number of zones
        scene_number: Scene number this design is for
        mechanic_types: List of mechanic types from scene_breakdown

    Returns:
        Normalized interaction design with scene_number and mode_transitions
    """
    if not result or not isinstance(result, dict):
        result = {}

    mechanic_types = mechanic_types or []

    # Validate primary mode - prefer first mechanic from scene_breakdown
    primary_mode = result.get("primary_interaction_mode")
    if not primary_mode and mechanic_types:
        primary_mode = mechanic_types[0]
    elif not primary_mode:
        primary_mode = ""

    pattern = get_pattern(primary_mode) if primary_mode else None
    if not pattern or pattern.status == PatternStatus.MISSING:
        if primary_mode:
            logger.warning(f"Invalid primary mode '{primary_mode}', defaulting to first mechanic")
        primary_mode = mechanic_types[0] if mechanic_types else ""

    # Validate secondary modes - use remaining mechanics from scene_breakdown
    secondary_modes = result.get("secondary_modes", [])
    if not secondary_modes and len(mechanic_types) > 1:
        # Auto-populate secondary modes from scene mechanics
        secondary_modes = mechanic_types[1:]

    if secondary_modes:
        validation = validate_multi_mode_combination([primary_mode] + secondary_modes)
        if validation.get("warnings"):
            for warning in validation["warnings"]:
                logger.warning(f"Multi-mode warning: {warning}")

    # Normalize scoring strategy
    scoring = result.get("scoring_strategy", {})
    if not isinstance(scoring, dict):
        scoring = {}

    base_points = DEFAULT_SCORING["base_points_per_zone"]

    # Normalize reveal strategy
    reveal = result.get("reveal_strategy", {})
    if not isinstance(reveal, dict):
        reveal = {}

    # Auto-adjust reveal strategy based on hierarchy
    if hierarchy_info.get("has_hierarchy") and not reveal.get("type"):
        reveal["type"] = "progressive_hierarchical"
        reveal["trigger"] = "complete_parent"

    # Normalize feedback strategy
    feedback = result.get("feedback_strategy", {})
    if not isinstance(feedback, dict):
        feedback = {
            "on_correct": "Great job! You correctly identified the structure.",
            "on_incorrect": "Not quite. Look at the shape and position carefully.",
            "hint_progression": ["structural", "functional", "direct"],
            "use_misconception_feedback": True,
        }

    # Normalize animation config
    animations = result.get("animation_config", {})
    if not isinstance(animations, dict):
        animations = {}

    # Set default animations
    if not animations.get("on_correct"):
        animations["on_correct"] = "glow"
    if not animations.get("on_incorrect"):
        animations["on_incorrect"] = "shake"
    if not animations.get("on_reveal"):
        animations["on_reveal"] = "fade"
    if not animations.get("on_complete"):
        animations["on_complete"] = "confetti"

    # Get mode_transitions from LLM result or generate them
    llm_mode_transitions = result.get("mode_transitions", [])
    if llm_mode_transitions and isinstance(llm_mode_transitions, list):
        # Normalize LLM-provided transitions
        mode_transitions = _normalize_mode_transitions(llm_mode_transitions)
    else:
        # Generate mode transitions for multi-mode scenes
        mode_transitions = _generate_mode_transitions(
            primary_mode, secondary_modes, result.get("multi_mode_config", {})
        )

    return {
        "scene_number": scene_number,  # NEW: Which scene this design is for
        "primary_interaction_mode": primary_mode,
        "secondary_modes": secondary_modes,
        "design_rationale": result.get("design_rationale", ""),
        "zone_behavior_strategy": result.get("zone_behavior_strategy", {
            "default_zone_type": "circle",
            "use_point_zones_for": ["small structures", "simple labels"],
            "use_area_zones_for": ["large structures", "complex boundaries"],
        }),
        "reveal_strategy": {
            "type": reveal.get("type", "flat"),
            "trigger": reveal.get("trigger", "all_at_once"),
            "reveal_order": reveal.get("reveal_order", "suggested_order"),
        },
        "feedback_strategy": feedback,
        "scoring_strategy": {
            "strategy_id": scoring.get("strategy_id", "standard"),
            "base_points_per_zone": base_points,
            "partial_credit": bool(scoring.get("partial_credit", True)),
            "time_bonus": scoring.get("time_bonus", {"enabled": False, "max_bonus": 0}),
            "hint_penalty": int(scoring.get("hint_penalty", 20)),
            "max_score": base_points * zone_count,
        },
        "feedback_messages": DEFAULT_FEEDBACK,
        "thresholds": DEFAULT_THRESHOLDS,
        "animation_config": animations,
        "multi_mode_config": result.get("multi_mode_config", {
            "enabled": bool(secondary_modes),
            "mode_sequence": [primary_mode] + secondary_modes if secondary_modes else [primary_mode],
            "transition_trigger": "scene_complete",
        }),
        # Mode transitions for multi-mechanic scenes (per-scene scoped)
        "mode_transitions": mode_transitions,
        "hierarchy_info": hierarchy_info,
        "zone_count": zone_count,
        "designed_at": datetime.utcnow().isoformat(),
    }


def _normalize_mode_transitions(
    raw_transitions: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Normalize mode transitions from LLM response.

    Ensures transitions have the correct format expected by the frontend:
    - from_mode: Source interaction mode
    - to_mode: Target interaction mode
    - trigger: What triggers the transition
    - trigger_value: Optional value for the trigger
    - animation: Transition animation type

    Args:
        raw_transitions: Raw transitions from LLM response

    Returns:
        Normalized mode transitions list
    """
    normalized = []

    for trans in raw_transitions:
        if not isinstance(trans, dict):
            continue

        # Handle different key naming conventions
        from_mode = trans.get("from_mode") or trans.get("from") or ""
        to_mode = trans.get("to_mode") or trans.get("to") or ""

        if not from_mode or not to_mode:
            continue

        normalized_trans = {
            "from_mode": from_mode,
            "to_mode": to_mode,
            "trigger": trans.get("trigger", "all_zones_labeled"),
            "trigger_value": trans.get("trigger_value") or trans.get("triggerValue"),
            "animation": trans.get("animation", "fade_transition"),
        }

        # Add optional message if provided
        if trans.get("message"):
            normalized_trans["message"] = trans["message"]
        else:
            normalized_trans["message"] = f"Great job! Now let's {_get_mode_action_text(to_mode)}."

        normalized.append(normalized_trans)

    return normalized


def _generate_mode_transitions(
    primary_mode: str,
    secondary_modes: List[str],
    multi_mode_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate mode transitions for multi-mode games.

    Creates transition rules that the frontend uses to automatically
    switch between interaction modes based on triggers.
    """
    if not secondary_modes:
        return []

    transitions = []
    mode_sequence = [primary_mode] + secondary_modes
    transition_trigger = multi_mode_config.get("transition_trigger", "scene_complete")

    # Map transition trigger to frontend trigger types
    trigger_mapping = {
        "scene_complete": "all_zones_labeled",
        "zone_count": "percentage_complete",
        "manual": "user_choice",
        "all_labeled": "all_zones_labeled",
        "path_complete": "path_complete",
        "hierarchy_complete": "hierarchy_level_complete",
    }

    frontend_trigger = trigger_mapping.get(transition_trigger, "all_zones_labeled")

    # Create transitions between consecutive modes
    for i in range(len(mode_sequence) - 1):
        from_mode = mode_sequence[i]
        to_mode = mode_sequence[i + 1]

        # Determine appropriate trigger for mode pair
        if from_mode == "trace_path":
            trigger = "path_complete"
        elif from_mode == "hierarchical":
            trigger = "hierarchy_level_complete"
        else:
            trigger = frontend_trigger

        transition = {
            "from": from_mode,
            "to": to_mode,
            "trigger": trigger,
            "animation": "fade",
            "message": f"Great job! Now let's {_get_mode_action_text(to_mode)}.",
        }

        # Add trigger value for percentage-based transitions
        if trigger == "percentage_complete":
            transition["triggerValue"] = 80  # 80% completion

        transitions.append(transition)

    return transitions


def _get_mode_action_text(mode: str) -> str:
    """Get action text for mode transition messages."""
    action_texts = {
        "drag_drop": "label the remaining parts",
        "click_to_identify": "identify the parts when prompted",
        "trace_path": "trace the path through the system",
        "hierarchical": "explore the nested structures",
        "description_matching": "match the descriptions",
        "compare_contrast": "compare the structures",
        "sequencing": "arrange the steps in order",
        "timed_challenge": "complete the timed challenge",
    }
    return action_texts.get(mode, "continue with the next activity")


def _create_fallback_design(
    ped_context: Dict[str, Any],
    hierarchy_info: Dict[str, Any],
    zone_count: int,
    scene_number: int = 1,
    mechanic_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a fallback interaction design when LLM fails.

    Args:
        ped_context: Pedagogical context
        hierarchy_info: Hierarchy information
        zone_count: Number of zones
        scene_number: Scene number this design is for
        mechanic_types: List of mechanic types from scene_breakdown

    Returns:
        Fallback interaction design with scene_number
    """
    blooms_level = ped_context.get("blooms_level", "understand")
    difficulty = ped_context.get("difficulty", "intermediate")
    has_hierarchy = hierarchy_info.get("has_hierarchy", False)
    mechanic_types = mechanic_types or []

    # Use mechanics from scene_breakdown if provided
    if mechanic_types:
        primary_mode = mechanic_types[0]
        secondary = mechanic_types[1:] if len(mechanic_types) > 1 else []
    else:
        # Simple heuristic-based mode selection
        if has_hierarchy:
            primary_mode = "hierarchical"
        elif blooms_level in ("remember", "understand"):
            primary_mode = "drag_drop"
        elif blooms_level in ("apply", "analyze"):
            primary_mode = "click_to_identify"
        else:
            primary_mode = "drag_drop"

        # Suggest secondary modes
        secondary = suggest_secondary_modes(primary_mode, blooms_level)
        secondary = secondary[:1] if secondary else []

    base_points = DEFAULT_SCORING["base_points_per_zone"]

    return {
        "scene_number": scene_number,  # NEW: Which scene this design is for
        "primary_interaction_mode": primary_mode,
        "secondary_modes": secondary,
        "design_rationale": f"Fallback design for scene {scene_number}, {blooms_level} level with {zone_count} zones",
        "zone_behavior_strategy": {
            "default_zone_type": "circle",
            "use_point_zones_for": ["small structures"],
            "use_area_zones_for": ["large structures"],
        },
        "reveal_strategy": {
            "type": "progressive_hierarchical" if has_hierarchy else "flat",
            "trigger": "complete_parent" if has_hierarchy else "all_at_once",
            "reveal_order": "hierarchy_based" if has_hierarchy else "suggested_order",
        },
        "feedback_strategy": {
            "on_correct": DEFAULT_FEEDBACK["good"],
            "on_incorrect": DEFAULT_FEEDBACK["retry"],
            "hint_progression": ["structural", "functional", "direct"],
            "use_misconception_feedback": False,
        },
        "scoring_strategy": {
            "strategy_id": "standard",
            "base_points_per_zone": base_points,
            "partial_credit": True,
            "time_bonus": {"enabled": False, "max_bonus": 0},
            "hint_penalty": 20,
            "max_score": base_points * zone_count,
        },
        "feedback_messages": DEFAULT_FEEDBACK,
        "thresholds": DEFAULT_THRESHOLDS,
        "animation_config": {
            "on_correct": "glow",
            "on_incorrect": "shake",
            "on_reveal": "fade",
            "on_complete": "bounce",
        },
        "multi_mode_config": {
            "enabled": bool(secondary),
            "mode_sequence": [primary_mode] + secondary if secondary else [primary_mode],
            "transition_trigger": "scene_complete",
        },
        "mode_transitions": _generate_mode_transitions(
            primary_mode, secondary, {}
        ),
        "hierarchy_info": hierarchy_info,
        "zone_count": zone_count,
        "designed_at": datetime.utcnow().isoformat(),
        "_is_fallback": True,
    }
