"""
Game Designer Agent — Unified Unconstrained Game Design

The game_designer is the CREATIVE BRAIN of the pipeline. It produces a free-form
GameDesign describing WHAT the game should be, without being constrained by
MechanicType enums, WorkflowType enums, or fixed schema structures.

Key Principles:
- CONTENT drives interaction choice, not Bloom's level
- Multiple patterns can be COMBINED in a single game
- Agent REASONS about pedagogy using the capability manifest
- Bloom's level is ONE INPUT, not the determinant
- Frontend capabilities are presented as INSPIRATION, not a fixed menu

Inputs: question_text, pedagogical_context, domain_knowledge, template_selection
Outputs: game_design (unconstrained GameDesign)

Downstream: design_interpreter maps game_design → structured game_plan
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.state import AgentState
from app.agents.schemas.game_plan_schemas import GameDesign, SceneDesign
from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.agents.instrumentation import InstrumentedAgentContext
from app.config.interaction_patterns import (
    format_patterns_for_prompt,
    get_implemented_patterns,
)
from app.config.example_game_designs import format_examples_for_prompt

logger = get_logger("gamed_ai.agents.game_designer")


GAME_DESIGN_PROMPT = """You are an expert educational game designer. Design an optimal interactive learning game for this educational question.

=== CONTEXT ===

**Question**: {question_text}
{options_text}

**Learning Analysis**:
- Bloom's Level: {blooms_level} (INFORMATIONAL — do not let this restrict your choices)
- Subject: {subject}
- Difficulty: {difficulty}
- Learning Objectives: {learning_objectives}
- Key Concepts: {key_concepts}
- Common Misconceptions: {misconceptions}

**Domain Knowledge** (retrieved from web):
{domain_context}

=== AVAILABLE INTERACTION MODES ===

These are the interaction modes the frontend can render. Use them as INSPIRATION — describe what you want in natural language and the system will map to the right mode.

{interaction_patterns}

=== EXAMPLE GAME DESIGNS ===

{example_designs}

=== DESIGN PRINCIPLES ===

1. **CONTENT drives interaction choice**, not Bloom's level
   - A "remember" question might benefit from trace_path if it involves a process
   - An "analyze" question might use drag_drop if the content is straightforward

2. **Multiple interaction modes can be COMBINED** across scenes
   - "Label X AND show how Y flows" → Scene 1: drag labels, Scene 2: trace the flow
   - Multi-part questions deserve multi-scene games

3. **Consider LEARNING EFFECTIVENESS and ENGAGEMENT**
   - Start with foundational activities (labeling, identifying)
   - Build to more complex interactions (tracing, sequencing, decision-making)
   - End with mastery checks if appropriate

4. **Don't over-engineer simple questions**
   - "Label the parts of a flower" → Single labeling scene is sufficient
   - Only add scenes when pedagogically justified

5. **Always produce at least one scene**

=== YOUR TASK ===

Design a game. For each scene, describe:
- What the learner does (in natural language)
- What visuals are needed
- How scoring should work
- What learning goal it serves

=== RESPONSE FORMAT (JSON) ===
{{
    "title": "<game title>",
    "learning_objectives": ["By the end, the learner will...", "..."],
    "pedagogical_reasoning": "<explain your design approach and why>",
    "scenes": [
        {{
            "scene_number": 1,
            "title": "<scene title>",
            "description": "<what happens in this scene>",
            "learning_goal": "<what this scene teaches>",
            "interaction_description": "<describe what the student does — e.g. 'drag labels onto diagram parts', 'trace the path of blood flow', 'put the steps in correct order'>",
            "visual_needs": ["<what visuals this scene needs — e.g. 'anatomical diagram of the heart', 'flow arrows between chambers'>"],
            "scoring_approach": "<how to score — e.g. 'points per correct label', 'all-or-nothing sequence order'>"
        }}
    ],
    "progression_type": "<single|linear|zoom_in|branching>",
    "estimated_duration_minutes": <number>,
    "difficulty_approach": "<how difficulty is managed>"
}}

Respond with ONLY valid JSON."""


async def game_designer_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Unified Game Designer Agent — produces unconstrained GameDesign.

    Runs for ALL pipeline presets (replaces preset-specific game_designer + game_planner).

    Inputs: question_text, pedagogical_context, domain_knowledge, template_selection
    Outputs: game_design
    """
    question_id = state.get("question_id", "unknown")
    logger.info("Designing game", question_id=question_id, agent_name="game_designer")

    question_text = state.get("question_text", "")
    question_options = state.get("question_options") or []
    ped_context = state.get("pedagogical_context") or {}
    domain_knowledge = state.get("domain_knowledge") or {}
    template_selection = state.get("template_selection") or {}

    # Format options text
    options_text = ""
    if question_options:
        options_text = f"\n**Answer Options**: {', '.join(question_options)}"

    # Format domain context
    domain_context = _format_domain_context(domain_knowledge)

    # Format pedagogical details
    learning_objectives = ped_context.get("learning_objectives", [])
    key_concepts = ped_context.get("key_concepts", [])
    misconceptions = ped_context.get("common_misconceptions", [])

    misconceptions_text = "None identified"
    if misconceptions:
        misconceptions_text = "; ".join(
            m.get("misconception", str(m)) if isinstance(m, dict) else str(m)
            for m in misconceptions[:5]
        )

    # Get interaction patterns for prompt
    patterns_str = format_patterns_for_prompt()

    # Get example designs for few-shot learning
    examples_str = format_examples_for_prompt(max_examples=3)

    # Build prompt
    prompt = GAME_DESIGN_PROMPT.format(
        question_text=question_text,
        options_text=options_text,
        blooms_level=ped_context.get("blooms_level", "understand"),
        subject=ped_context.get("subject", "General"),
        difficulty=ped_context.get("difficulty", "intermediate"),
        learning_objectives=", ".join(learning_objectives) if learning_objectives else "Not specified",
        key_concepts=", ".join(key_concepts) if key_concepts else "Not specified",
        misconceptions=misconceptions_text,
        domain_context=domain_context,
        interaction_patterns=patterns_str,
        example_designs=examples_str,
    )

    try:
        llm = get_llm_service()

        # Use Pydantic schema for guided decoding
        game_design_schema = GameDesign.model_json_schema()

        result = await llm.generate_json_for_agent(
            agent_name="game_designer",
            prompt=prompt,
            schema_hint="GameDesign with title, learning_objectives, pedagogical_reasoning, scenes[], progression_type",
            json_schema=game_design_schema,
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

        # Normalize result — handle wrapper key
        if isinstance(result, dict) and "game_design" in result:
            result = result["game_design"]

        # Validate with Pydantic
        try:
            game_design = GameDesign.model_validate(result)
            game_design_dict = game_design.model_dump()
        except Exception as val_err:
            logger.warning(f"Pydantic validation failed, using raw dict: {val_err}")
            game_design_dict = _normalize_raw_design(result, question_text)

        # Ensure at least one scene
        if not game_design_dict.get("scenes"):
            game_design_dict["scenes"] = [_create_default_scene(question_text, domain_knowledge)]

        logger.info(
            "Game design complete",
            num_scenes=len(game_design_dict.get("scenes", [])),
            progression=game_design_dict.get("progression_type"),
        )

        return {
            "game_design": game_design_dict,
            "current_agent": "game_designer",
        }

    except Exception as e:
        logger.error(
            "Game design failed, using fallback",
            exc_info=True,
            error_type=type(e).__name__,
            error_message=str(e),
        )

        if ctx:
            ctx.set_fallback_used(f"Game design failed: {str(e)}")

        fallback = _create_fallback_design(question_text, ped_context, domain_knowledge)

        return {
            "game_design": fallback,
            "current_agent": "game_designer",
            "error_message": f"GameDesigner fallback: {str(e)}",
        }


def _format_domain_context(domain_knowledge: Dict) -> str:
    """Format domain knowledge for prompt."""
    if not domain_knowledge:
        return "None available"

    parts = []

    canonical_labels = domain_knowledge.get("canonical_labels", [])
    if canonical_labels:
        parts.append(f"Key terms/labels: {', '.join(canonical_labels[:12])}")

    relationships = domain_knowledge.get("hierarchical_relationships", [])
    if relationships:
        rel_summary = []
        for r in relationships[:5]:
            parent = r.get("parent", "?")
            children = ", ".join(r.get("children", [])[:4])
            rel_type = r.get("relationship_type", "contains")
            rel_summary.append(f"{parent} ({rel_type}) → [{children}]")
        parts.append(f"Relationships: {'; '.join(rel_summary)}")

    seq_data = domain_knowledge.get("sequence_flow_data") or {}
    if seq_data.get("sequence_items"):
        items = seq_data["sequence_items"]
        item_texts = [i.get("text", str(i)) if isinstance(i, dict) else str(i) for i in items[:8]]
        flow_type = seq_data.get("flow_type", "linear")
        parts.append(f"Sequence ({flow_type}): {' → '.join(item_texts)}")

    content_chars = domain_knowledge.get("content_characteristics") or {}
    if content_chars:
        flags = []
        if content_chars.get("needs_labels"):
            flags.append("needs labeling")
        if content_chars.get("needs_sequence"):
            flags.append("has sequence/process")
        if content_chars.get("needs_comparison"):
            flags.append("involves comparison")
        if flags:
            parts.append(f"Content type: {', '.join(flags)}")

    return "\n".join(parts) if parts else "None available"


def _normalize_raw_design(raw: Any, question_text: str) -> Dict:
    """Normalize raw LLM output into a valid GameDesign dict."""
    if not isinstance(raw, dict):
        raw = {}

    design = {
        "title": raw.get("title", f"Interactive Game: {question_text[:50]}"),
        "learning_objectives": raw.get("learning_objectives", ["Complete the interactive learning activity"]),
        "pedagogical_reasoning": raw.get("pedagogical_reasoning", ""),
        "progression_type": raw.get("progression_type", "single"),
        "estimated_duration_minutes": raw.get("estimated_duration_minutes", 10),
        "difficulty_approach": raw.get("difficulty_approach", ""),
    }

    scenes = raw.get("scenes", [])
    normalized_scenes = []
    for i, s in enumerate(scenes):
        if not isinstance(s, dict):
            continue
        normalized_scenes.append({
            "scene_number": s.get("scene_number", i + 1),
            "title": s.get("title", f"Scene {i + 1}"),
            "description": s.get("description", ""),
            "learning_goal": s.get("learning_goal", ""),
            "interaction_description": s.get("interaction_description", "Interactive activity"),
            "visual_needs": s.get("visual_needs", []),
            "scoring_approach": s.get("scoring_approach", "standard"),
            "builds_on": s.get("builds_on"),
        })

    design["scenes"] = normalized_scenes
    return design


def _create_default_scene(question_text: str, domain_knowledge: Dict) -> Dict:
    """Create a default scene when LLM produces none."""
    labels = domain_knowledge.get("canonical_labels", [])
    visual_desc = f"Educational diagram for: {question_text[:100]}"

    return {
        "scene_number": 1,
        "title": "Label the Diagram",
        "description": "Drag the correct labels onto the diagram to identify each part.",
        "learning_goal": "Identify and name the key parts or components",
        "interaction_description": "Students drag labels from a label tray onto the correct positions on the diagram",
        "visual_needs": [visual_desc],
        "scoring_approach": "Points per correct label placement",
    }


def _create_fallback_design(question_text: str, ped_context: Dict, domain_knowledge: Dict) -> Dict:
    """Create fallback design when LLM fails entirely."""
    q_lower = question_text.lower()

    # Detect likely interaction type from question text
    if any(w in q_lower for w in ["trace", "flow", "path", "journey", "circulation"]):
        interaction_desc = "Trace the path or flow through the diagram by clicking waypoints in order"
        scene_title = "Trace the Path"
    elif any(w in q_lower for w in ["order", "sequence", "steps", "stages", "arrange"]):
        interaction_desc = "Put the steps in the correct order by dragging them into position"
        scene_title = "Order the Steps"
    elif any(w in q_lower for w in ["compare", "contrast", "difference"]):
        interaction_desc = "Compare two diagrams side-by-side and categorize features as similar or different"
        scene_title = "Compare and Contrast"
    elif any(w in q_lower for w in ["sort", "categorize", "group", "classify"]):
        interaction_desc = "Sort items into the correct categories by dragging them"
        scene_title = "Sort into Categories"
    else:
        interaction_desc = "Drag the correct labels onto the diagram to identify each part"
        scene_title = "Label the Diagram"

    return {
        "title": f"Interactive Game: {question_text[:60]}",
        "learning_objectives": ["Complete the interactive learning activity"],
        "pedagogical_reasoning": "Fallback design using content-based interaction detection",
        "scenes": [{
            "scene_number": 1,
            "title": scene_title,
            "description": f"Interactive activity for: {question_text[:100]}",
            "learning_goal": "Demonstrate understanding of the topic",
            "interaction_description": interaction_desc,
            "visual_needs": [f"Educational diagram for: {question_text[:80]}"],
            "scoring_approach": "standard",
        }],
        "progression_type": "single",
        "estimated_duration_minutes": 10,
        "difficulty_approach": ped_context.get("difficulty", "intermediate"),
    }
