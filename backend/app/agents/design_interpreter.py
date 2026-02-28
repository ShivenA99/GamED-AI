"""
Design Interpreter Agent — Creative-to-Structured Mapper

Maps the unconstrained GameDesign (from game_designer) into a structured GamePlan
that downstream pipeline agents can consume.

This is WHERE the creative-to-structured mapping happens using an LLM agent
that understands both the unconstrained design and the pipeline's structured
requirements.

Key Responsibilities:
- Classify natural language interaction descriptions → MechanicType values
- Infer asset needs from visual descriptions → structured asset_needs with workflows
- Map scoring descriptions → structured scoring_rubric
- Determine workflow assignments from asset descriptions
- ALWAYS populate scene_breakdown with per-scene mechanics[], asset_needs, focus_labels

Why LLM not code:
- "students trace the path of blood through the heart" → trace_path (requires understanding)
- "drag labels onto the correct parts" could be drag_drop or hierarchical (context-dependent)

Inputs: game_design, domain_knowledge, template_selection
Outputs: game_plan (structured), scene_breakdown, needs_multi_scene, workflow_execution_plan
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.state import AgentState
from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.workflows.types import MECHANIC_TO_WORKFLOW

logger = get_logger("gamed_ai.agents.design_interpreter")


# Valid mechanic types that map to frontend InteractionMode values
VALID_MECHANIC_TYPES = [
    "drag_drop", "click_to_identify", "trace_path", "hierarchical",
    "description_matching", "compare_contrast", "sequencing",
    "timed_challenge", "sorting_categories", "memory_match",
    "branching_scenario",
    # Also accept these aliases (mapped in normalization)
    "sorting", "comparison", "reveal", "hotspot",
]

# Alias normalization for mechanic types
MECHANIC_ALIASES = {
    "sorting": "sorting_categories",
    "comparison": "compare_contrast",
    "reveal": "hierarchical",
    "hotspot": "click_to_identify",
    "label": "drag_drop",
    "labeling": "drag_drop",
    "drag_and_drop": "drag_drop",
    "sequence": "sequencing",
    "order": "sequencing",
    "match": "memory_match",
    "matching": "memory_match",
    "branching": "branching_scenario",
    "timed": "timed_challenge",
    "identify": "click_to_identify",
}


DESIGN_INTERPRETER_PROMPT = """You are a game design interpreter. Your job is to take a creative game design and produce a structured game plan that the pipeline can execute.

=== CREATIVE GAME DESIGN ===
{game_design_json}

=== DOMAIN KNOWLEDGE ===
{domain_context}

=== TEMPLATE TYPE ===
{template_type}

=== VALID MECHANIC TYPES ===
These are the only valid mechanic type values:
- drag_drop: Drag labels onto diagram zones
- click_to_identify: Click on correct zones in response to prompts
- trace_path: Trace a path through connected waypoints
- hierarchical: Progressive reveal of parent-child zone hierarchies
- description_matching: Match descriptions to zones
- compare_contrast: Compare two diagrams side by side
- sequencing: Put items in correct order
- timed_challenge: Time-limited wrapper around another mechanic
- sorting_categories: Sort items into categories
- memory_match: Card-flip matching game
- branching_scenario: Decision tree navigation

=== VALID WORKFLOW TYPES ===
Workflows handle asset generation. Each mechanic maps to a workflow:
- labeling_diagram: Image retrieval + zone detection + label creation (for drag_drop, click_to_identify, hierarchical)
- trace_path: Zone-based path extraction (for trace_path)
- sequence_items: Sequence item extraction (for sequencing)
- sorting: Category/item extraction (for sorting_categories)
- memory_match: Pair generation (for memory_match)
- comparison_diagrams: Dual diagram retrieval (for compare_contrast)
- branching_scenario: Decision tree generation (for branching_scenario)

=== YOUR TASK ===

For each scene in the creative design, produce:
1. A classified mechanic type (from the valid list above)
2. Asset needs with workflow assignments
3. Focus labels (key terms for that scene)

=== RESPONSE FORMAT (JSON) ===
{{
    "learning_objectives": ["..."],
    "game_mechanics": [
        {{
            "id": "mechanic_1",
            "type": "<valid_mechanic_type>",
            "description": "<what this mechanic does>",
            "interaction_type": "<same as type>",
            "scoring_weight": 0.0-1.0
        }}
    ],
    "difficulty_progression": {{
        "initial_state": "guided",
        "progression_rules": "unlock_after_correct",
        "hints_available": true,
        "max_attempts": 3
    }},
    "feedback_strategy": {{
        "immediate_feedback": true,
        "feedback_on_correct": "Encouraging message about what was learned",
        "feedback_on_incorrect": "Helpful hint about common misconceptions",
        "misconception_targeting": true
    }},
    "scoring_rubric": {{
        "max_score": 100,
        "partial_credit": true,
        "time_bonus": false,
        "hint_penalty": 0.1,
        "criteria": []
    }},
    "estimated_duration_minutes": <number>,
    "prerequisite_skills": [],
    "required_labels": ["<canonical labels from domain knowledge>"],
    "hierarchy_info": {{
        "is_hierarchical": <true if parent-child relationships exist>,
        "parent_children": {{"<parent>": ["<child1>", "<child2>"]}},
        "recommended_mode": "<hierarchical or drag_drop>",
        "reveal_trigger": "<complete_parent or click_expand>"
    }},
    "scene_breakdown": [
        {{
            "scene_number": 1,
            "title": "<scene title>",
            "description": "<scene description>",
            "interaction_mode": "<primary mechanic type>",
            "focus_labels": ["<labels relevant to this scene>"],
            "mechanics": [
                {{
                    "type": "<valid_mechanic_type>",
                    "scoring_weight": 1.0,
                    "completion_criteria": "all_complete"
                }}
            ],
            "asset_needs": {{
                "primary": {{
                    "query": "<search query for image/asset>",
                    "type": "<asset type>",
                    "workflow": "<valid_workflow_type>",
                    "depends_on": []
                }}
            }}
        }}
    ]
}}

IMPORTANT:
- mechanic types must be from the valid list above
- workflow types must be from the valid list above
- required_labels should come from the domain knowledge canonical_labels
- hierarchy_info should reflect actual parent-child relationships from domain knowledge
- scene_breakdown must have at least 1 scene
- Each scene's asset_needs must include a "primary" entry with a workflow

Respond with ONLY valid JSON."""


async def design_interpreter_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Design Interpreter Agent — maps unconstrained GameDesign → structured GamePlan.

    Inputs: game_design, domain_knowledge, template_selection
    Outputs: game_plan, scene_breakdown, needs_multi_scene
    """
    question_id = state.get("question_id", "unknown")
    logger.info("Interpreting game design", question_id=question_id, agent_name="design_interpreter")

    game_design = state.get("game_design") or {}
    domain_knowledge = state.get("domain_knowledge") or {}
    template_selection = state.get("template_selection") or {}

    template_type = template_selection.get("template_type", "INTERACTIVE_DIAGRAM")

    # Format inputs for prompt
    game_design_json = json.dumps(game_design, indent=2, default=str)

    domain_context = _format_domain_context(domain_knowledge)

    prompt = DESIGN_INTERPRETER_PROMPT.format(
        game_design_json=game_design_json,
        domain_context=domain_context,
        template_type=template_type,
    )

    try:
        llm = get_llm_service()
        result = await llm.generate_json_for_agent(
            agent_name="design_interpreter",
            prompt=prompt,
            schema_hint="GamePlan with learning_objectives, game_mechanics, scoring_rubric, scene_breakdown",
        )

        # Extract LLM metrics
        llm_metrics = result.pop("_llm_metrics", None) if isinstance(result, dict) else None
        if llm_metrics and ctx:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms"),
            )

        if not isinstance(result, dict):
            result = {}

        # Normalize the structured plan
        game_plan = _normalize_game_plan(result, game_design, domain_knowledge, template_type)

        # Extract scene_breakdown as top-level state field too
        scene_breakdown = game_plan.get("scene_breakdown", [])
        needs_multi_scene = len(scene_breakdown) > 1

        logger.info(
            "Design interpretation complete",
            num_mechanics=len(game_plan.get("game_mechanics", [])),
            num_scenes=len(scene_breakdown),
            needs_multi_scene=needs_multi_scene,
        )

        return {
            "game_plan": game_plan,
            "scene_breakdown": scene_breakdown,
            "needs_multi_scene": needs_multi_scene,
            "current_agent": "design_interpreter",
        }

    except Exception as e:
        logger.error(
            "Design interpretation failed, using fallback",
            exc_info=True,
            error_type=type(e).__name__,
            error_message=str(e),
        )

        if ctx:
            ctx.set_fallback_used(f"Design interpretation failed: {str(e)}")

        fallback_plan = _create_fallback_plan(game_design, domain_knowledge, template_type)
        scene_breakdown = fallback_plan.get("scene_breakdown", [])

        return {
            "game_plan": fallback_plan,
            "scene_breakdown": scene_breakdown,
            "needs_multi_scene": len(scene_breakdown) > 1,
            "current_agent": "design_interpreter",
            "error_message": f"DesignInterpreter fallback: {str(e)}",
        }


def _normalize_game_plan(
    raw: Dict,
    game_design: Dict,
    domain_knowledge: Dict,
    template_type: str,
) -> Dict:
    """Normalize LLM output into a valid game_plan dict."""

    plan = {}

    # Learning objectives
    plan["learning_objectives"] = raw.get("learning_objectives") or \
        game_design.get("learning_objectives") or \
        ["Complete the interactive learning activity"]

    # Game mechanics — normalize types
    raw_mechanics = raw.get("game_mechanics", [])
    normalized_mechanics = []
    for m in raw_mechanics:
        if not isinstance(m, dict):
            continue
        mtype = _normalize_mechanic_type(m.get("type") or "")
        normalized_mechanics.append({
            "id": m.get("id", f"mechanic_{len(normalized_mechanics) + 1}"),
            "type": mtype,
            "description": m.get("description", ""),
            "interaction_type": mtype,
            "scoring_weight": float(m.get("scoring_weight", 1.0)),
        })

    if not normalized_mechanics:
        normalized_mechanics = [{
            "id": "mechanic_1",
            "type": "drag_drop",
            "description": "Drag labels onto diagram",
            "interaction_type": "drag_drop",
            "scoring_weight": 1.0,
        }]

    plan["game_mechanics"] = normalized_mechanics

    # Difficulty progression
    plan["difficulty_progression"] = raw.get("difficulty_progression") or {
        "initial_state": "guided",
        "progression_rules": "unlock_after_correct",
        "hints_available": True,
        "max_attempts": 3,
    }

    # Feedback strategy
    plan["feedback_strategy"] = raw.get("feedback_strategy") or {
        "immediate_feedback": True,
        "feedback_on_correct": "Correct!",
        "feedback_on_incorrect": "Try again",
        "misconception_targeting": True,
    }

    # Scoring rubric
    scoring = raw.get("scoring_rubric") or {}
    plan["scoring_rubric"] = {
        "max_score": int(scoring.get("max_score", 100)),
        "partial_credit": bool(scoring.get("partial_credit", True)),
        "time_bonus": bool(scoring.get("time_bonus", False)),
        "hint_penalty": float(scoring.get("hint_penalty", 0.1)),
        "criteria": scoring.get("criteria", []),
    }

    plan["estimated_duration_minutes"] = int(raw.get("estimated_duration_minutes") or
                                              game_design.get("estimated_duration_minutes") or 10)
    plan["prerequisite_skills"] = raw.get("prerequisite_skills") or []

    # Required labels — from LLM output or domain knowledge
    plan["required_labels"] = raw.get("required_labels") or \
        domain_knowledge.get("canonical_labels") or []

    # Hierarchy info
    hierarchy = raw.get("hierarchy_info") or {}
    relationships = domain_knowledge.get("hierarchical_relationships") or []
    if not hierarchy.get("is_hierarchical") and relationships:
        # Detect from domain knowledge
        parent_children = {}
        for rel in relationships:
            parent = rel.get("parent", "")
            children = rel.get("children", [])
            if parent and children:
                parent_children[parent] = children
        hierarchy = {
            "is_hierarchical": bool(parent_children),
            "parent_children": parent_children,
            "recommended_mode": "hierarchical" if parent_children else "drag_drop",
            "reveal_trigger": "complete_parent",
        }
    plan["hierarchy_info"] = hierarchy

    # Scene breakdown — always present
    raw_breakdown = raw.get("scene_breakdown", [])
    if not raw_breakdown:
        # Create from game_design scenes
        raw_breakdown = _create_breakdown_from_design(game_design, domain_knowledge, template_type)

    normalized_breakdown = []
    for scene in raw_breakdown:
        if not isinstance(scene, dict):
            continue
        normalized_breakdown.append(_normalize_scene_breakdown(scene, domain_knowledge, template_type))

    if not normalized_breakdown:
        normalized_breakdown = [_create_default_breakdown(domain_knowledge, template_type)]

    plan["scene_breakdown"] = normalized_breakdown

    # Recommended mode from primary mechanic
    if normalized_mechanics:
        plan["recommended_mode"] = normalized_mechanics[0]["type"]

    return plan


def _normalize_mechanic_type(raw_type: str) -> str:
    """Normalize a mechanic type string to a valid MechanicType value."""
    if not raw_type:
        return "drag_drop"

    raw_lower = raw_type.lower().strip()

    # Direct match
    if raw_lower in VALID_MECHANIC_TYPES:
        return raw_lower

    # Alias match
    if raw_lower in MECHANIC_ALIASES:
        return MECHANIC_ALIASES[raw_lower]

    # Fuzzy match
    for valid in VALID_MECHANIC_TYPES:
        if valid in raw_lower or raw_lower in valid:
            return valid

    logger.warning(f"Unknown mechanic type '{raw_type}', defaulting to drag_drop")
    return "drag_drop"


def _normalize_scene_breakdown(
    scene: Dict,
    domain_knowledge: Dict,
    template_type: str,
) -> Dict:
    """Normalize a single scene breakdown entry."""
    scene_num = int(scene.get("scene_number", 1))

    # Normalize mechanics
    raw_mechanics = scene.get("mechanics", [])
    normalized_mechanics = []
    for m in raw_mechanics:
        if not isinstance(m, dict):
            continue
        mtype = _normalize_mechanic_type(m.get("type") or "")
        normalized_mechanics.append({
            "type": mtype,
            "scoring_weight": float(m.get("scoring_weight", 1.0)),
            "completion_criteria": m.get("completion_criteria", "all_complete"),
        })

    if not normalized_mechanics:
        interaction_mode = _normalize_mechanic_type(scene.get("interaction_mode") or "")
        normalized_mechanics = [{
            "type": interaction_mode,
            "scoring_weight": 1.0,
            "completion_criteria": "all_complete",
        }]

    # Normalize asset_needs
    raw_asset_needs = scene.get("asset_needs", {})
    normalized_asset_needs = {}

    if isinstance(raw_asset_needs, dict):
        for key, need in raw_asset_needs.items():
            if not isinstance(need, dict):
                continue
            workflow = need.get("workflow", "")
            if not workflow:
                # Infer from mechanic type
                primary_mtype = normalized_mechanics[0]["type"] if normalized_mechanics else "drag_drop"
                # Map frontend mechanic to workflow mechanic name
                workflow_mtype = primary_mtype
                if primary_mtype in ("hierarchical", "description_matching"):
                    workflow_mtype = "drag_drop"
                elif primary_mtype == "compare_contrast":
                    workflow_mtype = "comparison"
                elif primary_mtype == "sorting_categories":
                    workflow_mtype = "sorting"
                elif primary_mtype == "timed_challenge":
                    workflow_mtype = "drag_drop"
                workflow = MECHANIC_TO_WORKFLOW.get(workflow_mtype, "labeling_diagram")
            normalized_asset_needs[key] = {
                "query": need.get("query"),
                "type": need.get("type"),
                "workflow": workflow,
                "depends_on": need.get("depends_on", []),
            }

    if not normalized_asset_needs:
        # Create default based on primary mechanic
        primary_mtype = normalized_mechanics[0]["type"] if normalized_mechanics else "drag_drop"
        workflow_mtype = primary_mtype
        if primary_mtype in ("hierarchical", "description_matching"):
            workflow_mtype = "drag_drop"
        elif primary_mtype == "compare_contrast":
            workflow_mtype = "comparison"
        elif primary_mtype == "sorting_categories":
            workflow_mtype = "sorting"
        elif primary_mtype == "timed_challenge":
            workflow_mtype = "drag_drop"
        workflow = MECHANIC_TO_WORKFLOW.get(workflow_mtype, "labeling_diagram")
        labels = domain_knowledge.get("canonical_labels", [])
        query = f"{' '.join(labels[:3])} diagram" if labels else "educational diagram"
        normalized_asset_needs["primary"] = {
            "query": query,
            "type": "diagram",
            "workflow": workflow,
            "depends_on": [],
        }

    return {
        "scene_number": scene_num,
        "title": scene.get("title", f"Scene {scene_num}"),
        "description": scene.get("description", ""),
        "interaction_mode": normalized_mechanics[0]["type"] if normalized_mechanics else "drag_drop",
        "focus_labels": scene.get("focus_labels") or [],
        "mechanics": normalized_mechanics,
        "asset_needs": normalized_asset_needs,
    }


def _create_breakdown_from_design(
    game_design: Dict,
    domain_knowledge: Dict,
    template_type: str,
) -> List[Dict]:
    """Create scene_breakdown from unconstrained game_design scenes."""
    scenes = game_design.get("scenes", [])
    if not scenes:
        return [_create_default_breakdown(domain_knowledge, template_type)]

    breakdown = []
    canonical_labels = domain_knowledge.get("canonical_labels") or []

    for scene in scenes:
        if not isinstance(scene, dict):
            continue

        # Infer mechanic from interaction_description
        interaction_desc = scene.get("interaction_description", "")
        mechanic_type = _infer_mechanic_from_description(interaction_desc)

        # Infer query from visual_needs
        visual_needs = scene.get("visual_needs", [])
        query = visual_needs[0] if visual_needs else None

        # Infer workflow
        workflow_mtype = mechanic_type
        if mechanic_type in ("hierarchical", "description_matching"):
            workflow_mtype = "drag_drop"
        elif mechanic_type == "compare_contrast":
            workflow_mtype = "comparison"
        elif mechanic_type == "sorting_categories":
            workflow_mtype = "sorting"
        elif mechanic_type == "timed_challenge":
            workflow_mtype = "drag_drop"
        workflow = MECHANIC_TO_WORKFLOW.get(workflow_mtype, "labeling_diagram")

        breakdown.append({
            "scene_number": scene.get("scene_number", len(breakdown) + 1),
            "title": scene.get("title", f"Scene {len(breakdown) + 1}"),
            "description": scene.get("description", ""),
            "interaction_mode": mechanic_type,
            "focus_labels": [],
            "mechanics": [{
                "type": mechanic_type,
                "scoring_weight": 1.0,
                "completion_criteria": "all_complete",
            }],
            "asset_needs": {
                "primary": {
                    "query": query,
                    "type": "diagram",
                    "workflow": workflow,
                    "depends_on": [],
                }
            },
        })

    return breakdown if breakdown else [_create_default_breakdown(domain_knowledge, template_type)]


def _infer_mechanic_from_description(description: str) -> str:
    """Infer mechanic type from natural language description (heuristic fallback)."""
    d = description.lower()

    if any(w in d for w in ["drag", "label", "place onto", "drop"]):
        if any(w in d for w in ["hierarchy", "expand", "reveal", "parent", "child"]):
            return "hierarchical"
        return "drag_drop"
    if any(w in d for w in ["trace", "follow the path", "flow", "route"]):
        return "trace_path"
    if any(w in d for w in ["order", "sequence", "arrange", "put in order", "steps in order"]):
        return "sequencing"
    if any(w in d for w in ["sort", "categorize", "classify", "group"]):
        return "sorting_categories"
    if any(w in d for w in ["click", "identify", "point to", "select the correct"]):
        return "click_to_identify"
    if any(w in d for w in ["compare", "contrast", "side by side", "difference"]):
        return "compare_contrast"
    if any(w in d for w in ["memory", "flip", "match pairs", "card"]):
        return "memory_match"
    if any(w in d for w in ["decision", "choose", "branch", "scenario", "what would happen"]):
        return "branching_scenario"
    if any(w in d for w in ["timed", "time limit", "countdown", "race"]):
        return "timed_challenge"
    if any(w in d for w in ["description", "match description", "read and match"]):
        return "description_matching"

    return "drag_drop"


def _create_default_breakdown(domain_knowledge: Dict, template_type: str) -> Dict:
    """Create a single default scene breakdown."""
    labels = domain_knowledge.get("canonical_labels") or []
    query = f"{' '.join(labels[:3])} diagram" if labels else "educational diagram"

    return {
        "scene_number": 1,
        "title": "Label the Diagram",
        "description": "Interactive labeling activity",
        "interaction_mode": "drag_drop",
        "focus_labels": labels[:10],
        "mechanics": [{
            "type": "drag_drop",
            "scoring_weight": 1.0,
            "completion_criteria": "all_complete",
        }],
        "asset_needs": {
            "primary": {
                "query": query,
                "type": "diagram",
                "workflow": "labeling_diagram",
                "depends_on": [],
            }
        },
    }


def _create_fallback_plan(
    game_design: Dict,
    domain_knowledge: Dict,
    template_type: str,
) -> Dict:
    """Create a complete fallback plan when LLM fails."""
    labels = domain_knowledge.get("canonical_labels") or []
    relationships = domain_knowledge.get("hierarchical_relationships") or []

    # Detect hierarchy
    parent_children = {}
    for rel in relationships:
        parent = rel.get("parent", "")
        children = rel.get("children", [])
        if parent and children:
            parent_children[parent] = children

    is_hierarchical = bool(parent_children)

    scene_breakdown = _create_breakdown_from_design(game_design, domain_knowledge, template_type)

    return {
        "learning_objectives": game_design.get("learning_objectives", ["Complete the learning activity"]),
        "game_mechanics": [{
            "id": "mechanic_1",
            "type": "drag_drop",
            "description": "Drag labels onto diagram",
            "interaction_type": "drag_drop",
            "scoring_weight": 1.0,
        }],
        "difficulty_progression": {
            "initial_state": "guided",
            "progression_rules": "unlock_after_correct",
            "hints_available": True,
            "max_attempts": 3,
        },
        "feedback_strategy": {
            "immediate_feedback": True,
            "feedback_on_correct": "Correct!",
            "feedback_on_incorrect": "Try again",
            "misconception_targeting": True,
        },
        "scoring_rubric": {
            "max_score": 100,
            "partial_credit": True,
            "time_bonus": False,
            "hint_penalty": 0.1,
            "criteria": [],
        },
        "estimated_duration_minutes": game_design.get("estimated_duration_minutes", 10),
        "prerequisite_skills": [],
        "required_labels": labels,
        "hierarchy_info": {
            "is_hierarchical": is_hierarchical,
            "parent_children": parent_children,
            "recommended_mode": "hierarchical" if is_hierarchical else "drag_drop",
            "reveal_trigger": "complete_parent",
        },
        "scene_breakdown": scene_breakdown,
        "recommended_mode": "hierarchical" if is_hierarchical else "drag_drop",
    }


def _format_domain_context(domain_knowledge: Dict) -> str:
    """Format domain knowledge for the interpreter prompt."""
    if not domain_knowledge:
        return "None available"

    parts = []

    labels = domain_knowledge.get("canonical_labels", [])
    if labels:
        parts.append(f"Canonical labels: {', '.join(labels[:15])}")

    relationships = domain_knowledge.get("hierarchical_relationships", [])
    if relationships:
        rel_parts = []
        for r in relationships[:5]:
            parent = r.get("parent", "?")
            children = ", ".join(r.get("children", [])[:5])
            rel_parts.append(f"{parent} → [{children}]")
        parts.append(f"Hierarchies: {'; '.join(rel_parts)}")

    seq_data = domain_knowledge.get("sequence_flow_data") or {}
    if seq_data.get("sequence_items"):
        items = seq_data["sequence_items"]
        texts = [i.get("text", str(i)) if isinstance(i, dict) else str(i) for i in items[:8]]
        parts.append(f"Sequence: {' → '.join(texts)}")

    content = domain_knowledge.get("content_characteristics") or {}
    flags = []
    if content.get("needs_labels"):
        flags.append("needs_labels")
    if content.get("needs_sequence"):
        flags.append("needs_sequence")
    if content.get("needs_comparison"):
        flags.append("needs_comparison")
    if flags:
        parts.append(f"Content: {', '.join(flags)}")

    return "\n".join(parts) if parts else "None available"
