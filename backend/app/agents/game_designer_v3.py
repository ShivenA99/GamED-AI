"""
Game Designer v3 -- ReAct Agent for Educational Game Design.

Uses tool-calling to produce structured GameDesignV3Slim output through
pedagogical analysis, capability checking, example retrieval, iterative
self-validation, and final submission via submit_game_design.

Scope: GAME CONCEPT ONLY. Does NOT configure scoring, feedback, animations,
or asset generation -- those are handled by downstream agents
(scene_architect_v3, interaction_designer_v3).

Tools: analyze_pedagogy, check_capabilities, get_example_designs,
       validate_design, submit_game_design
Output: game_design_v3 (GameDesignV3Slim dict with _summary) in state
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response
from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.game_design_v3 import GameDesignV3Slim, validate_slim_game_design
from app.config.interaction_patterns import (
    format_patterns_for_prompt,
    format_scoring_strategies_for_prompt,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.game_designer_v3")


SYSTEM_PROMPT = """\
You are the Game Designer for GamED.AI, an AI-powered educational game platform.

Your job: Transform an educational question into a rich, multi-scene, multi-mechanic
interactive game design. You output a structured JSON game design document.

## Scope Limitation

You design the GAME CONCEPT only. You do NOT configure:
- Scoring rules (points, partial credit, streaks) -- handled by interaction_designer_v3
- Feedback messages (correct/incorrect/misconception) -- handled by interaction_designer_v3
- Animations or visual effects -- handled by interaction_designer_v3
- Asset generation or zone coordinates -- handled by scene_architect_v3

You DO define:
- Game title and pedagogical reasoning
- Learning objectives
- Label design (zone_labels, distractor_labels with explanations)
- Scene structure (number, titles, visual descriptions, which mechanics to use)
- Scene transitions
- Difficulty approach
- Theme/atmosphere

## Core Principles

1. **Pedagogical First**: Every mechanic choice must serve a learning objective.
   Don't add complexity for its own sake.

2. **Multi-Mechanic When Appropriate**: Simple questions -> 1 scene. Complex
   questions with multiple intents (label + trace + classify) -> multiple scenes
   with different mechanics.

3. **Progressive Difficulty**: Order scenes from recall -> understanding ->
   application. Each scene builds on what was learned.

4. **Distractor Quality**: Distractors should be plausible wrong answers, not
   obviously wrong. They should test real misconceptions.

## Mechanic Configuration Requirements

When choosing mechanics for scenes, be aware of what downstream agents need:

- **drag_drop**: Default mechanic. No special config needed from you.
- **click_to_identify**: Needs identification prompts (e.g. "Click on the structure that pumps blood"). Include a learning_goal in the scene.
- **trace_path**: Needs waypoint order (which labels to trace through). Include path hints in visual_description.
- **sequencing**: Needs correct ordering of items. If domain knowledge provides sequence_flow_data, reference it.
- **sorting_categories**: Needs category definitions. If domain knowledge provides comparison_data with sorting_categories, reference it.
- **description_matching**: Needs functional descriptions per label. If domain knowledge provides label_descriptions, this mechanic becomes viable.
- **memory_match**: Needs term-definition pairs from the labels.
- **branching_scenario**: Needs decision nodes and consequences.
- **compare_contrast**: Needs comparison categories. If domain knowledge provides comparison_data, this mechanic becomes viable.

Only choose mechanics for which the upstream data supports them. For example, don't choose sequencing unless there's a natural ordering, and don't choose description_matching unless label descriptions are available or can be inferred.

## Design Process

Use your tools in this order:
1. `analyze_pedagogy` -- Understand the question's cognitive demands
2. `get_example_designs` -- See how similar questions have been designed
3. `check_capabilities` -- See what mechanics are available
4. Design your game (in your reasoning)
5. `validate_design` -- Check your design against the schema
6. Fix any issues and re-validate if needed
7. `submit_game_design` -- Submit your final design

IMPORTANT: You MUST call `submit_game_design` with your complete design as your
final action. This is how your design gets accepted into the pipeline.
"""


class GameDesignerV3(ReActAgent):
    """ReAct agent that designs educational games using structured tools."""

    def __init__(self, model: Optional[str] = None):
        super().__init__(
            name="game_designer_v3",
            system_prompt=SYSTEM_PROMPT,
            max_iterations=6,
            tool_timeout=30.0,
            model=model,
            temperature=0.7,
        )

    def get_tool_names(self) -> List[str]:
        return [
            "analyze_pedagogy",
            "check_capabilities",
            "get_example_designs",
            "validate_design",
            "submit_game_design",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build task prompt from pipeline state."""
        question = state.get("enhanced_question") or state.get("question", "")
        subject = state.get("subject", "")
        blooms_level = state.get("blooms_level", "understand")
        domain_knowledge = state.get("domain_knowledge", "")
        canonical_labels = state.get("canonical_labels", [])
        learning_objectives = state.get("learning_objectives", [])
        pedagogical_context = state.get("pedagogical_context", {})

        sections = [f"## Question\n{question}"]

        if subject:
            sections.append(f"## Subject\n{subject}")

        # Bloom's level is informational context only — not injected into prompt
        # to avoid biasing mechanic selection

        if domain_knowledge:
            dk_text = domain_knowledge if isinstance(domain_knowledge, str) else json.dumps(domain_knowledge, indent=2)
            sections.append(f"## Domain Knowledge\n{dk_text[:4000]}")

        if canonical_labels:
            labels_str = ", ".join(canonical_labels[:30])
            sections.append(f"## Known Labels\nThese labels have been identified for this topic:\n{labels_str}")

        # Fix 2.3a: Inject domain knowledge mechanic-relevant fields
        dk = state.get("domain_knowledge", {})
        if isinstance(dk, dict):
            seq_data = dk.get("sequence_flow_data")
            if seq_data:
                sections.append(f"## Sequence/Flow Data\n{json.dumps(seq_data, indent=2)[:2000]}")
            label_descs = dk.get("label_descriptions")
            if label_descs:
                sections.append(f"## Label Descriptions\n{json.dumps(label_descs, indent=2)[:2000]}")
            comparison_data = dk.get("comparison_data")
            if comparison_data:
                sections.append(f"## Comparison Data\n{json.dumps(comparison_data, indent=2)[:2000]}")
            content_chars = dk.get("content_characteristics")
            if content_chars:
                sections.append(f"## Content Characteristics\n{json.dumps(content_chars, indent=2)[:1000]}")

        if learning_objectives:
            obj_str = "\n".join(f"- {obj}" for obj in learning_objectives)
            sections.append(f"## Learning Objectives\n{obj_str}")

        if pedagogical_context:
            pc_text = json.dumps(pedagogical_context, indent=2)
            sections.append(f"## Pedagogical Context\n{pc_text[:1000]}")

        # Add reference material
        sections.append(f"\n{format_patterns_for_prompt()}")

        # Check for previous validation feedback (retry scenario)
        validation = state.get("design_validation_v3")
        retry_count = state.get("_v3_design_retries", 0)
        if validation and not validation.get("passed", True) and retry_count > 0:
            issues = validation.get("issues", [])
            score = validation.get("score", 0)
            issues_str = "\n".join(f"- {issue}" for issue in issues)
            sections.append(f"""## IMPORTANT: Previous Design Was Rejected (Attempt {retry_count})

Your previous design was rejected by the validator with score {score:.2f}/1.0.
You MUST fix these specific issues:

{issues_str}

Focus on fixing these issues. Do not start from scratch -- adjust your previous approach
to address each issue listed above.""")

        sections.append("""
## Your Task

Design a complete educational game. Use your tools in this order:
1. Call `analyze_pedagogy` to understand cognitive demands and content type
2. Call `get_example_designs` for inspiration from similar questions
3. Call `check_capabilities` to see which mechanics are READY based on available data. \
   ONLY choose mechanics from the ready_types list. Do NOT choose unsupported mechanics.
4. Design your game using only ready mechanics
5. Call `validate_design` to check your design
6. Fix issues and re-validate if needed
7. Call `submit_game_design` with your final design

Your design must include:
- title, pedagogical_reasoning, learning_objectives
- labels (zone_labels, distractor_labels with text + explanation)
- scenes (each with scene_number, title, visual_description, mechanics)
- For each mechanic, include its type AND basic config data:
  - trace_path: path_config with waypoints order
  - sequencing: sequence_config with correct_order
  - sorting_categories: sorting_config with categories and items
  - description_matching: description_match_config with descriptions per label
  - click_to_identify: click_config with identification prompts
  - memory_match: memory_config with term-definition pairs
  - branching_scenario: branching_config with decision nodes
  - compare_contrast: compare_config with comparison categories
  - hierarchical: labels.hierarchy with parent-child relationships
  - drag_drop: no special config needed
- scene_transitions, theme, difficulty, estimated_duration_minutes

You MUST call submit_game_design as your final action.
""")

        return "\n\n".join(sections)

    def parse_final_result(
        self,
        response: Any,
        state: AgentState,
    ) -> Dict[str, Any]:
        """Parse the LLM's final response into state updates.

        Priority:
        1. If submit_game_design was called successfully, extract from tool call args
        2. Otherwise, fall back to extract_json_from_response + validate
        """
        content = response.content if hasattr(response, "content") else str(response)

        logger.info(
            f"GameDesignerV3: Response content length={len(content)}, "
            f"tool_calls={len(response.tool_calls) if hasattr(response, 'tool_calls') else 0}"
        )

        # Strategy 1: Check if submit_game_design was called successfully
        if hasattr(response, "tool_calls") and hasattr(response, "tool_results"):
            submit_calls = [
                (tc, tr)
                for tc, tr in zip(response.tool_calls, response.tool_results)
                if tc.name == "submit_game_design"
            ]
            if submit_calls:
                tc, tr = submit_calls[-1]  # Use the last submit call
                # Check the tool result for acceptance
                result_data = tr.result if hasattr(tr, "result") else {}
                if isinstance(result_data, dict) and result_data.get("status") == "accepted":
                    logger.info(
                        f"GameDesignerV3: Design accepted via submit_game_design. "
                        f"Summary: {result_data.get('summary', 'N/A')}"
                    )
                    design_dict = tc.arguments
                    # Validate to get the canonical form
                    try:
                        parsed = GameDesignV3Slim.model_validate(design_dict)
                        design_dict = parsed.model_dump()
                        design_dict["_summary"] = parsed.summary()
                        logger.info(
                            f"GameDesignerV3: Valid design -- "
                            f"title='{parsed.title}', "
                            f"scenes={len(parsed.scenes)}, "
                            f"labels={len(parsed.labels.zone_labels) if parsed.labels else 0}"
                        )
                    except Exception as e:
                        logger.warning(f"GameDesignerV3: Submit args re-validation warning: {e}")
                        design_dict["_summary"] = result_data.get("summary", "")
                    return {
                        "current_agent": "game_designer_v3",
                        "game_design_v3": design_dict,
                    }
                else:
                    logger.warning(
                        f"GameDesignerV3: submit_game_design was rejected: {result_data}. "
                        "Falling back to JSON extraction."
                    )

        # Strategy 2: Fall back to extract_json_from_response
        design_dict = extract_json_from_response(content)

        if not design_dict:
            logger.error(
                f"GameDesignerV3: Could not extract JSON from response "
                f"(length={len(content)}, has_braces={'{' in content})"
            )
            return {
                "current_agent": "game_designer_v3",
                "game_design_v3": None,
                "_error": "Failed to extract game design JSON from response",
            }

        # Validate against schema
        try:
            design = GameDesignV3Slim.model_validate(design_dict)
            design_dict = design.model_dump()
            design_dict["_summary"] = design.summary()
            logger.info(
                f"GameDesignerV3: Valid design (fallback) -- "
                f"title='{design.title}', "
                f"scenes={len(design.scenes)}, "
                f"labels={len(design.labels.zone_labels) if design.labels else 0}"
            )
        except Exception as e:
            logger.warning(
                f"GameDesignerV3: Design didn't fully validate: {e}. "
                "Using raw dict with empty summary."
            )
            design_dict["_summary"] = ""

        return {
            "current_agent": "game_designer_v3",
            "game_design_v3": design_dict,
        }


# ---------------------------------------------------------------------------
# Agent function (LangGraph node interface)
# ---------------------------------------------------------------------------

_agent_instance: Optional[GameDesignerV3] = None


def _get_agent(model: Optional[str] = None) -> GameDesignerV3:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = GameDesignerV3(model=model)
    return _agent_instance


async def game_designer_v3_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Game Designer v3 Agent -- ReAct agent for educational game design.

    Reads: enhanced_question, domain_knowledge, canonical_labels, blooms_level, subject
    Writes: game_design_v3 (GameDesignV3Slim dict with _summary)
    """
    logger.info("GameDesignerV3: Starting game design")

    # Inject pipeline context for tool access
    from app.tools.v3_context import set_v3_tool_context
    set_v3_tool_context(state)

    # Get model override from state if available
    model = state.get("_model_override")
    agent = _get_agent(model)

    result = await agent.run(state, ctx)

    # Merge result into state
    return {
        **state,
        **result,
        "current_agent": "game_designer_v3",
    }
