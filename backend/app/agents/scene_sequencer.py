"""
Scene Sequencer Agent

Detects if a multi-scene game is needed and plans the scene structure.
This agent analyzes the question, domain knowledge, and hierarchy info
to determine if the content requires multiple scenes (zoom-in, depth-first,
linear progressions, or branching).

Multi-scene triggers:
- "zoom" / "detail" / "deeper" keywords in question
- Hierarchy depth > 2 levels
- Geographic scale transitions (continent -> country -> state)
- Temporal progressions (era -> period -> event)
- Process decomposition (system -> subsystem -> component)

Inputs:
- question_text: The question to analyze
- domain_knowledge: Domain knowledge with hierarchical_relationships
- game_plan: The game plan with hierarchy_info
- diagram_type: The classified diagram type

Outputs:
- needs_multi_scene: Whether multi-scene is needed
- num_scenes: Number of scenes planned
- scene_progression_type: Type of progression (linear, zoom_in, depth_first, branching)
- scene_breakdown: List of scene definitions with scope and focus
"""

import json

from app.utils.logging_config import get_logger
import os
import re
from typing import Dict, Any, Optional, List

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service

logger = get_logger("gamed_ai.agents.scene_sequencer")


# Keywords that suggest multi-scene content
ZOOM_KEYWORDS = [
    "zoom", "detail", "deeper", "closer", "inside", "within",
    "breakdown", "decompose", "explore", "drill down"
]

SCALE_KEYWORDS = [
    "levels", "layers", "stages", "phases", "steps",
    "from", "to", "starting", "ending"
]

GEOGRAPHIC_SCALE_PATTERNS = [
    (r"world|globe|earth", r"continent|region", r"country|nation"),
    (r"continent", r"country|nation", r"state|province|region"),
    (r"country|nation", r"state|province", r"city|town|county"),
]

ANATOMICAL_SCALE_PATTERNS = [
    (r"system|body", r"organ|structure", r"tissue|part"),
    (r"organ", r"tissue|structure", r"cell|component"),
    (r"cell", r"organelle|part", r"molecule|protein"),
]


SCENE_SEQUENCER_PROMPT = """You are an expert educational game designer analyzing a question to determine if it requires a multi-scene game.

## Question:
{question_text}

## Domain Knowledge:
{domain_knowledge}

## Hierarchy Information:
{hierarchy_info}

## Diagram Type: {diagram_type}

## Analysis Task:
Analyze whether this content needs a multi-scene game. Multi-scene is appropriate when:
1. Content spans multiple scale levels (e.g., continent -> country -> city)
2. There's a clear progression from overview to detail
3. Hierarchy depth is 3+ levels
4. User would benefit from zooming into specific areas
5. Content naturally divides into distinct stages or chapters

## Response Format (JSON):
{{
    "needs_multi_scene": true/false,
    "reasoning": "Brief explanation of why multi-scene is or isn't needed",
    "num_scenes": 1-5,
    "progression_type": "linear" | "zoom_in" | "depth_first" | "branching",
    "scene_breakdown": [
        {{
            "scene_number": 1,
            "title": "Scene title",
            "scope": "What this scene covers",
            "focus_labels": ["label1", "label2"],
            "parent_scene": null,
            "unlock_condition": "how this scene becomes available"
        }}
    ]
}}

If multi-scene is not needed, set num_scenes to 1 and provide a single scene in scene_breakdown.

Respond with ONLY valid JSON."""


async def scene_sequencer_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Scene Sequencer Agent (Preset 2 Only)

    Detects if multi-scene game is needed and plans scene structure.

    CRITICAL: This agent is ONLY used when PIPELINE_PRESET=advanced_interactive_diagram.
    Preset 1 (interactive_diagram_hierarchical) MUST remain completely untouched.

    Args:
        state: Current agent state with question_text, domain_knowledge, game_plan

    Returns:
        Updated state with scene_sequence information
    """
    # CRITICAL: Only run for Preset 2 (advanced_interactive_diagram)
    # Preset 1 must NOT run this agent to preserve original behavior
    preset = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")
    if preset != "advanced_interactive_diagram":
        logger.info(f"Skipping scene_sequencer - preset is '{preset}', not 'advanced_interactive_diagram'")
        # Return minimal state to indicate skipped (not an error)
        return {
            "needs_multi_scene": False,
            "num_scenes": 1,
            "scene_progression_type": "linear",
            "scene_breakdown": [{
                "scene_number": 1,
                "title": "Main Diagram",
                "scope": "All labels and structures",
                "focus_labels": [],
                "parent_scene": None,
                "unlock_condition": None
            }],
            "scene_sequencer_skipped": True,
            "current_agent": "scene_sequencer"
        }

    question_id = state.get('question_id', 'unknown')
    logger.info("Processing question", question_id=question_id, agent_name="scene_sequencer")

    question_text = state.get("question_text", "")
    domain_knowledge = state.get("domain_knowledge", {})
    game_plan = state.get("game_plan", {})
    diagram_type = state.get("diagram_type", "anatomy")

    # Extract hierarchy info from game_plan
    hierarchy_info = game_plan.get("hierarchy_info", {})

    # Phase 1: Quick heuristic check
    quick_result = _quick_multi_scene_check(
        question_text=question_text,
        domain_knowledge=domain_knowledge,
        hierarchy_info=hierarchy_info
    )

    # If heuristics clearly indicate single-scene, skip LLM call
    if not quick_result.get("likely_multi_scene"):
        scene_breakdown = [{
            "scene_number": 1,
            "title": "Main Diagram",
            "scope": "All labels and structures",
            "focus_labels": [],  # All labels
            "parent_scene": None,
            "unlock_condition": None
        }]
        result = {
            # Store in dedicated state fields
            "needs_multi_scene": False,
            "num_scenes": 1,
            "scene_progression_type": "linear",
            "scene_breakdown": scene_breakdown,
            # Also keep legacy format for backward compat
            "scene_sequence_reasoning": quick_result.get("reasoning", "Single scene sufficient"),
            "current_agent": "scene_sequencer",
        }

        logger.info(
            "Quick check determined single-scene game",
            reasoning=quick_result.get("reasoning")
        )

        if ctx:
            ctx.complete(result)

        return result

    # Phase 2: LLM-based detailed analysis
    try:
        llm = get_llm_service()

        prompt = SCENE_SEQUENCER_PROMPT.format(
            question_text=question_text,
            domain_knowledge=json.dumps(domain_knowledge, indent=2) if domain_knowledge else "None",
            hierarchy_info=json.dumps(hierarchy_info, indent=2) if hierarchy_info else "None",
            diagram_type=diagram_type
        )

        llm_result = await llm.generate_json_for_agent(
            agent_name="scene_sequencer",
            prompt=prompt,
            schema_hint="Scene sequence analysis with num_scenes, progression_type, and scene_breakdown"
        )

        # Extract LLM metrics
        llm_metrics = llm_result.pop("_llm_metrics", None) if isinstance(llm_result, dict) else None
        if llm_metrics and ctx:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms")
            )

        # Normalize result
        normalized = _normalize_scene_sequence(llm_result)

        # Build result with dedicated state fields
        result = {
            "needs_multi_scene": normalized.get("needs_multi_scene", False),
            "num_scenes": normalized.get("num_scenes", 1),
            "scene_progression_type": normalized.get("scene_progression_type", "linear"),
            "scene_breakdown": normalized.get("scene_breakdown", []),
            "scene_sequence_reasoning": normalized.get("scene_sequence_reasoning", ""),
            "current_agent": "scene_sequencer",
        }

        logger.info(
            f"Scene sequencer completed: {result['num_scenes']} scenes, {result['scene_progression_type']} progression",
            num_scenes=result["num_scenes"],
            progression=result["scene_progression_type"]
        )

        if ctx:
            ctx.complete(result)

        return result

    except Exception as e:
        logger.error(f"Scene sequencer LLM call failed: {e}", exc_info=True)

        # Fallback to heuristic-based multi-scene if likely
        fallback = _create_fallback_scene_sequence(
            question_text=question_text,
            hierarchy_info=hierarchy_info,
            quick_result=quick_result
        )

        # Build result with dedicated state fields
        result = {
            "needs_multi_scene": fallback.get("needs_multi_scene", False),
            "num_scenes": fallback.get("num_scenes", 1),
            "scene_progression_type": fallback.get("scene_progression_type", "linear"),
            "scene_breakdown": fallback.get("scene_breakdown", []),
            "scene_sequence_reasoning": fallback.get("scene_sequence_reasoning", ""),
            "scene_sequence_error": str(e),
            "current_agent": "scene_sequencer",
        }

        if ctx:
            ctx.set_fallback_used(f"Scene sequencer fallback: {str(e)}")
            ctx.complete(result)

        return result


def _quick_multi_scene_check(
    question_text: str,
    domain_knowledge: Dict[str, Any],
    hierarchy_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Quick heuristic check for multi-scene likelihood.

    Returns dict with:
    - likely_multi_scene: bool
    - reasoning: str
    - suggested_num_scenes: int
    """
    question_lower = question_text.lower()
    reasons = []

    # Check for zoom/detail keywords
    zoom_matches = [kw for kw in ZOOM_KEYWORDS if kw in question_lower]
    if zoom_matches:
        reasons.append(f"Contains zoom/detail keywords: {zoom_matches}")

    # Check for scale keywords
    scale_matches = [kw for kw in SCALE_KEYWORDS if kw in question_lower]
    if len(scale_matches) >= 2:
        reasons.append(f"Contains scale transition keywords: {scale_matches}")

    # Check hierarchy depth
    if hierarchy_info:
        parent_children = hierarchy_info.get("parent_children", {})
        if parent_children:
            # Check for nested hierarchy (children that are also parents)
            all_children = set()
            for children in parent_children.values():
                all_children.update(children)

            nested_parents = set(parent_children.keys()) & all_children
            if nested_parents:
                reasons.append(f"Nested hierarchy detected: {len(nested_parents)} intermediate levels")

            # Check total depth
            if len(parent_children) >= 3:
                reasons.append(f"Large hierarchy: {len(parent_children)} parent-child groups")

    # Check domain knowledge for hierarchical relationships
    if domain_knowledge:
        relationships = domain_knowledge.get("hierarchical_relationships", [])
        if len(relationships) >= 3:
            reasons.append(f"{len(relationships)} hierarchical relationships")

    # Check for geographic/anatomical scale patterns
    for patterns in GEOGRAPHIC_SCALE_PATTERNS:
        pattern_matches = sum(1 for p in patterns if re.search(p, question_lower))
        if pattern_matches >= 2:
            reasons.append("Geographic scale progression detected")
            break

    for patterns in ANATOMICAL_SCALE_PATTERNS:
        pattern_matches = sum(1 for p in patterns if re.search(p, question_lower))
        if pattern_matches >= 2:
            reasons.append("Anatomical scale progression detected")
            break

    # Determine result
    likely_multi_scene = len(reasons) >= 2 or any(
        "zoom/detail" in r or "Nested hierarchy" in r or "scale progression" in r
        for r in reasons
    )

    suggested_scenes = 1
    if likely_multi_scene:
        if any("Nested hierarchy" in r for r in reasons):
            suggested_scenes = 3
        elif any("scale progression" in r for r in reasons):
            suggested_scenes = 3
        else:
            suggested_scenes = 2

    return {
        "likely_multi_scene": likely_multi_scene,
        "reasoning": "; ".join(reasons) if reasons else "No multi-scene indicators found",
        "suggested_num_scenes": suggested_scenes,
        "indicators": reasons
    }


def _normalize_scene_sequence(llm_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize LLM result to consistent scene sequence format.
    """
    if not llm_result or not isinstance(llm_result, dict):
        return {
            "needs_multi_scene": False,
            "num_scenes": 1,
            "scene_progression_type": "linear",
            "scene_breakdown": [{
                "scene_number": 1,
                "title": "Main Diagram",
                "scope": "All labels",
                "focus_labels": [],
                "parent_scene": None,
                "unlock_condition": None
            }],
            "scene_sequence_reasoning": "Invalid LLM result, defaulting to single scene"
        }

    needs_multi = llm_result.get("needs_multi_scene", False)
    num_scenes = llm_result.get("num_scenes", 1)

    # Ensure reasonable bounds
    num_scenes = max(1, min(5, int(num_scenes)))

    progression_type = llm_result.get("progression_type", "linear")
    valid_progressions = ["linear", "zoom_in", "depth_first", "branching"]
    if progression_type not in valid_progressions:
        progression_type = "linear"

    scene_breakdown = llm_result.get("scene_breakdown", [])
    if not scene_breakdown:
        scene_breakdown = [{
            "scene_number": 1,
            "title": "Main Diagram",
            "scope": "All labels",
            "focus_labels": [],
            "parent_scene": None,
            "unlock_condition": None
        }]

    # Normalize each scene
    normalized_scenes = []
    for i, scene in enumerate(scene_breakdown[:num_scenes]):
        normalized_scenes.append({
            "scene_number": scene.get("scene_number", i + 1),
            "title": scene.get("title", f"Scene {i + 1}"),
            "scope": scene.get("scope", ""),
            "focus_labels": scene.get("focus_labels", []),
            "parent_scene": scene.get("parent_scene"),
            "unlock_condition": scene.get("unlock_condition")
        })

    return {
        "needs_multi_scene": needs_multi and num_scenes > 1,
        "num_scenes": num_scenes,
        "scene_progression_type": progression_type,
        "scene_breakdown": normalized_scenes,
        "scene_sequence_reasoning": llm_result.get("reasoning", "")
    }


def _create_fallback_scene_sequence(
    question_text: str,
    hierarchy_info: Dict[str, Any],
    quick_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create fallback scene sequence when LLM fails.
    """
    likely_multi = quick_result.get("likely_multi_scene", False)
    suggested_scenes = quick_result.get("suggested_num_scenes", 1)

    if not likely_multi:
        return {
            "needs_multi_scene": False,
            "num_scenes": 1,
            "scene_progression_type": "linear",
            "scene_breakdown": [{
                "scene_number": 1,
                "title": "Main Diagram",
                "scope": "All labels and structures",
                "focus_labels": [],
                "parent_scene": None,
                "unlock_condition": None
            }],
            "scene_sequence_reasoning": "Fallback: single scene"
        }

    # Create multi-scene based on hierarchy
    scenes = []
    if hierarchy_info:
        parent_children = hierarchy_info.get("parent_children", {})
        parents = list(parent_children.keys())

        # Scene 1: Overview with parent labels
        scenes.append({
            "scene_number": 1,
            "title": "Overview",
            "scope": "Main structures and systems",
            "focus_labels": parents[:6],  # Top-level parents
            "parent_scene": None,
            "unlock_condition": None
        })

        # Scene 2+: Detail scenes for each major parent
        for i, parent in enumerate(parents[:3]):  # Max 3 detail scenes
            children = parent_children.get(parent, [])
            scenes.append({
                "scene_number": i + 2,
                "title": f"{parent.title()} Detail",
                "scope": f"Components of {parent}",
                "focus_labels": children[:8],
                "parent_scene": 1,
                "unlock_condition": f"Complete {parent} in Scene 1"
            })
    else:
        # Generic multi-scene
        scenes = [
            {
                "scene_number": 1,
                "title": "Overview",
                "scope": "Main structures",
                "focus_labels": [],
                "parent_scene": None,
                "unlock_condition": None
            },
            {
                "scene_number": 2,
                "title": "Details",
                "scope": "Detailed components",
                "focus_labels": [],
                "parent_scene": 1,
                "unlock_condition": "Complete Scene 1"
            }
        ]

    return {
        "needs_multi_scene": True,
        "num_scenes": len(scenes),
        "scene_progression_type": "zoom_in",
        "scene_breakdown": scenes,
        "scene_sequence_reasoning": f"Fallback multi-scene: {quick_result.get('reasoning', '')}"
    }
