"""
Interaction Designer v3 -- ReAct Agent for Per-Scene Behavioral Specifications.

Defines scoring, feedback, misconception handling, animations, mechanic
transitions, and scene completion criteria for each scene. Reads upstream
outputs from game_designer_v3 and scene_architect_v3.

Tools: get_scoring_templates, generate_misconception_feedback,
       validate_interactions, submit_interaction_specs
Output: interaction_specs_v3 (list of InteractionSpecV3 dicts) in state
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response
from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.interaction_spec_v3 import InteractionSpecV3
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.interaction_designer_v3")


SYSTEM_PROMPT = """\
You are the Interaction Designer for GamED.AI. Your job: define scoring, \
feedback, misconception handling, animations, and mechanic transitions for \
each scene in a multi-scene, multi-mechanic interactive game.

## What You Produce (Per Scene)

For each scene, you produce an InteractionSpecV3 with:
1. **Scoring**: Per-mechanic scoring (strategy, points_per_correct, max_score, partial_credit, hint_penalty)
2. **Feedback**: Per-mechanic messages (on_correct, on_incorrect, on_completion, misconception_feedback)
3. **Distractor feedback**: Why each distractor label is wrong
4. **Mode transitions**: For multi-mechanic scenes, when/how to switch mechanics
5. **Scene completion**: Trigger and min_score_to_pass
6. **Animations**: Visual feedback (on_correct, on_incorrect, on_completion effect types)
7. **Scene transitions**: How to move between scenes

## Mechanic-Specific Scoring & Feedback

Different mechanics need different scoring strategies and feedback styles:

- **drag_drop**: Standard scoring (points per correct placement). Feedback explains \
  why a label belongs at a specific location.
- **click_to_identify**: Progressive scoring. Feedback names the region clicked and \
  explains its function. Use identification-specific language.
- **trace_path**: Path completion scoring with order dependency. Feedback explains \
  why each step in the path follows the previous one.
- **sequencing**: Position-based scoring with partial credit for items close to correct position. \
  Feedback explains the correct ordering logic.
- **sorting_categories**: Category-based scoring. Feedback explains why an item belongs \
  in a specific category, not just "correct/incorrect".
- **description_matching**: Match-based scoring. Feedback connects the functional \
  description to visual features of the structure.
- **memory_match**: Pair-based scoring with attempt tracking. Feedback reveals the \
  connection between matched terms when a pair is found.
- **branching_scenario**: Decision-based scoring with path analysis. Feedback explains \
  consequences of each choice and the reasoning behind correct decisions.
- **compare_contrast**: Categorization scoring. Feedback highlights specific similarities \
  and differences between compared subjects.
- **hierarchical**: Layer-based scoring. Feedback explains parent-child relationships.

## Design Process

For EACH scene:
1. `get_scoring_templates` -- Get recommended scoring strategy for each mechanic type
2. `enrich_mechanic_content` -- MANDATORY. Generates pedagogically enriched scoring rationale, \
   recommended scoring config, enriched feedback, and misconception triggers per mechanic
3. `generate_misconception_feedback` -- Get additional misconception triggers for the labels
4. Build interaction spec combining templates + enriched content + misconceptions
5. `validate_interactions` -- Check for errors, fix any issues

After ALL scenes:
6. `submit_interaction_specs` -- Submit ALL specs at once

CRITICAL: Do NOT skip step 2 (enrich_mechanic_content). It provides pedagogically grounded \
scoring and feedback instead of generic "Correct!/Try again." defaults.

CRITICAL: Your final action MUST be calling `submit_interaction_specs` with the \
complete list of interaction specs. Do NOT write specs as text in your response. \
Do NOT finish without calling `submit_interaction_specs`.

## Guidelines
- Every mechanic in every scene MUST have both scoring AND feedback
- Each scene should have at least 2 misconception feedbacks
- Multi-mechanic scenes need mode_transitions defining mechanic order and switch triggers
- Feedback must be pedagogically useful and mechanic-specific (not generic)
- Total max_score across all scenes should be 100-300 typically
"""


class InteractionDesignerV3(ReActAgent):
    """ReAct agent that creates per-scene behavioral specifications."""

    def __init__(self, model: Optional[str] = None):
        super().__init__(
            name="interaction_designer_v3",
            system_prompt=SYSTEM_PROMPT,
            max_iterations=15,
            tool_timeout=60.0,
            model=model,
            temperature=0.5,
        )

    def get_tool_names(self) -> List[str]:
        return [
            "get_scoring_templates",
            "generate_misconception_feedback",
            "enrich_mechanic_content",
            "validate_interactions",
            "submit_interaction_specs",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build task prompt from pipeline state."""
        game_design = state.get("game_design_v3") or {}
        scene_specs = state.get("scene_specs_v3") or []

        sections = []

        # Game design summary
        summary = game_design.get("_summary", "")
        if summary:
            sections.append(f"## Game Design Summary\n{summary}")

        # Labels (for misconception feedback)
        labels = game_design.get("labels", {})
        if isinstance(labels, dict):
            zone_labels = labels.get("zone_labels", [])
            distractor_labels = labels.get("distractor_labels", [])
            sections.append(f"## Zone Labels\n{json.dumps(zone_labels)}")
            if distractor_labels:
                distractor_info = []
                for dl in distractor_labels:
                    if isinstance(dl, dict):
                        distractor_info.append(f"{dl.get('text', '')}: {dl.get('explanation', '')}")
                    elif isinstance(dl, str):
                        distractor_info.append(dl)
                sections.append(f"## Distractor Labels\n" + "\n".join(f"- {d}" for d in distractor_info))

        # Scene specs summaries
        if scene_specs:
            spec_lines = []
            for spec in scene_specs:
                if isinstance(spec, dict):
                    sn = spec.get("scene_number", "?")
                    title = spec.get("title", "")
                    zones = spec.get("zones", [])
                    mechs = spec.get("mechanic_configs", [])
                    zone_labels_here = [z.get("label", "") for z in zones if isinstance(z, dict)]
                    mech_types = [m.get("type", "") for m in mechs if isinstance(m, dict)]
                    spec_lines.append(
                        f"Scene {sn}: '{title}'\n"
                        f"  Mechanics: {', '.join(mech_types)}\n"
                        f"  Zone labels: {json.dumps(zone_labels_here)}\n"
                        f"  Zone count: {len(zones)}"
                    )
            sections.append(f"## Scene Specs (from Scene Architect)\n" + "\n\n".join(spec_lines))

        # Difficulty info
        difficulty = game_design.get("difficulty", {})
        if isinstance(difficulty, dict):
            sections.append(f"## Difficulty Setting\n{json.dumps(difficulty)}")

        # Subject
        subject = game_design.get("_subject") or state.get("subject", "")
        if subject:
            sections.append(f"## Subject\n{subject}")

        # Domain knowledge injection — for pedagogically grounded enrichment
        dk = state.get("domain_knowledge", {})
        if isinstance(dk, dict):
            label_descs = dk.get("label_descriptions")
            if label_descs:
                sections.append(f"## Label Descriptions\n{json.dumps(label_descs, indent=2)[:2500]}")
            seq_data = dk.get("sequence_flow_data")
            if seq_data:
                sections.append(f"## Sequence/Flow Data\n{json.dumps(seq_data, indent=2)[:1500]}")
            comparison_data = dk.get("comparison_data")
            if comparison_data:
                sections.append(f"## Comparison Data\n{json.dumps(comparison_data, indent=2)[:1500]}")
            term_defs = dk.get("term_definitions")
            if term_defs:
                sections.append(f"## Term Definitions\n{json.dumps(term_defs, indent=2)[:1500]}")
            causal = dk.get("causal_relationships")
            if causal:
                sections.append(f"## Causal Relationships\n{json.dumps(causal, indent=2)[:1200]}")

        # Previous validation feedback (retry)
        validation = state.get("interaction_validation_v3")
        retry_count = state.get("_v3_interaction_retries", 0)
        if validation and not validation.get("passed", True) and retry_count > 0:
            issues = validation.get("issues", [])
            score = validation.get("score", 0)
            issues_str = "\n".join(f"- {issue}" for issue in issues)
            sections.append(f"""## IMPORTANT: Previous Interaction Specs Were Rejected (Attempt {retry_count})

Score: {score:.2f}/1.0. Fix these issues:

{issues_str}""")

        sections.append("""
## Your Task

Create a complete InteractionSpecV3 for EACH scene. For each scene:
1. Call `get_scoring_templates` for each mechanic type in the scene
2. Call `enrich_mechanic_content` for each mechanic -- generates enriched scoring, feedback, misconceptions
3. Call `generate_misconception_feedback` with the scene's zone labels
4. Build interaction spec: per-mechanic scoring + enriched feedback + misconceptions + transitions
5. Call `validate_interactions` to check for errors. Fix any issues.

Then call `submit_interaction_specs` with ALL interaction specs as your final action.

Each scoring entry: mechanic_type, strategy, points_per_correct, max_score, partial_credit, hint_penalty
Each feedback entry: mechanic_type, on_correct, on_incorrect, on_completion, misconception_feedback
Include distractor_feedback, mode_transitions (multi-mechanic), scene_completion, animations.

IMPORTANT: Call enrich_mechanic_content for EVERY mechanic, not just the first one.
""")

        return "\n\n".join(sections)

    def parse_final_result(
        self,
        response: Any,
        state: AgentState,
    ) -> Dict[str, Any]:
        """Parse the LLM's final response into state updates.

        Priority:
        1. If submit_interaction_specs was called successfully, extract from tool call args
        2. Fall back to JSON extraction from response text
        3. Reconstruct from tool results + scene_specs_v3
        """
        content = response.content if hasattr(response, "content") else str(response)
        tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []
        tool_results = response.tool_results if hasattr(response, "tool_results") else []

        logger.info(
            f"InteractionDesignerV3: Response content length={len(content)}, "
            f"tool_calls={len(tool_calls)}"
        )

        # Strategy 1: Check if submit_interaction_specs was called successfully
        for tc, tr in zip(tool_calls, tool_results):
            if not hasattr(tc, "name") or tc.name != "submit_interaction_specs":
                continue
            result_data = tr.result if hasattr(tr, "result") else {}
            if isinstance(result_data, dict) and result_data.get("status") == "accepted":
                logger.info(
                    f"InteractionDesignerV3: Specs accepted via submit_interaction_specs. "
                    f"Scenes: {result_data.get('scene_count', '?')}"
                )
                raw_specs = tc.arguments.get("interaction_specs", [])
                validated_specs = []
                for spec_dict in raw_specs:
                    try:
                        parsed = InteractionSpecV3.model_validate(spec_dict)
                        validated_specs.append(parsed.model_dump())
                    except Exception as e:
                        logger.warning(f"InteractionDesignerV3: Spec re-validation warning: {e}")
                        validated_specs.append(spec_dict)
                return {
                    "current_agent": "interaction_designer_v3",
                    "interaction_specs_v3": validated_specs,
                }

        # Strategy 2: Extract JSON from response text
        extracted = extract_json_from_response(content)
        if extracted:
            specs_list = []
            if isinstance(extracted, list):
                specs_list = extracted
            elif isinstance(extracted, dict):
                specs_list = extracted.get("interaction_specs", extracted.get("specs", [extracted]))

            valid_specs = []
            for s in specs_list:
                if isinstance(s, dict) and (s.get("scene_number") or s.get("scoring") or s.get("feedback")):
                    try:
                        parsed = InteractionSpecV3.model_validate(s)
                        valid_specs.append(parsed.model_dump())
                    except Exception:
                        valid_specs.append(s)
            if valid_specs:
                logger.info(f"InteractionDesignerV3: Extracted {len(valid_specs)} interaction specs from response text")
                return {
                    "current_agent": "interaction_designer_v3",
                    "interaction_specs_v3": valid_specs,
                }

        # Strategy 3: Recover interaction specs from validate_interactions tool call history.
        # Priority: enriched_spec from tool results > raw args from tool calls.
        # validate_interactions auto-enriches generic feedback, so the enriched
        # version in the tool result is preferred over the raw arguments.
        recovered_specs = []
        seen_scene_numbers = set()

        # First pass: look for enriched specs in tool results
        for tc, tr in zip(tool_calls, tool_results):
            tc_name = tc.name if hasattr(tc, "name") else ""
            if tc_name != "validate_interactions":
                continue
            result_data = tr.result if hasattr(tr, "result") else {}
            if isinstance(result_data, dict) and result_data.get("enriched_spec"):
                spec_data = result_data["enriched_spec"]
                if isinstance(spec_data, dict) and (spec_data.get("scoring") or spec_data.get("feedback")):
                    sn = spec_data.get("scene_number", len(recovered_specs) + 1)
                    if sn in seen_scene_numbers:
                        recovered_specs = [s for s in recovered_specs if s.get("scene_number") != sn]
                    seen_scene_numbers.add(sn)
                    try:
                        parsed = InteractionSpecV3.model_validate(spec_data)
                        recovered_specs.append(parsed.model_dump())
                    except Exception:
                        recovered_specs.append(spec_data)

        # Second pass: raw args from validate_interactions (for scenes not yet recovered)
        for tc in tool_calls:
            tc_name = tc.name if hasattr(tc, "name") else ""
            tc_args = tc.arguments if hasattr(tc, "arguments") else {}
            if tc_name == "validate_interactions" and isinstance(tc_args, dict):
                spec_data = tc_args.get("interaction_spec", tc_args)
                if isinstance(spec_data, dict) and (spec_data.get("scoring") or spec_data.get("feedback")):
                    sn = spec_data.get("scene_number", len(recovered_specs) + 1)
                    if sn in seen_scene_numbers:
                        continue  # Already have enriched version
                    seen_scene_numbers.add(sn)
                    try:
                        parsed = InteractionSpecV3.model_validate(spec_data)
                        recovered_specs.append(parsed.model_dump())
                    except Exception:
                        recovered_specs.append(spec_data)

            if tc_name == "submit_interaction_specs" and isinstance(tc_args, dict):
                raw_specs = tc_args.get("interaction_specs", [])
                for spec_data in raw_specs:
                    if isinstance(spec_data, dict):
                        sn = spec_data.get("scene_number", len(recovered_specs) + 1)
                        if sn not in seen_scene_numbers:
                            seen_scene_numbers.add(sn)
                            try:
                                parsed = InteractionSpecV3.model_validate(spec_data)
                                recovered_specs.append(parsed.model_dump())
                            except Exception:
                                recovered_specs.append(spec_data)

        if recovered_specs:
            recovered_specs.sort(key=lambda s: s.get("scene_number", 0))
            logger.info(
                f"InteractionDesignerV3: Recovered {len(recovered_specs)} interaction specs "
                f"from validate_interactions tool call history"
            )
            return {
                "current_agent": "interaction_designer_v3",
                "interaction_specs_v3": recovered_specs,
            }

        logger.error("InteractionDesignerV3: All extraction strategies failed")
        return {
            "current_agent": "interaction_designer_v3",
            "interaction_specs_v3": None,
            "_error": "Failed to extract interaction specs from response or text",
        }


# ---------------------------------------------------------------------------
# Agent function (LangGraph node interface)
# ---------------------------------------------------------------------------

_agent_instance: Optional[InteractionDesignerV3] = None


def _get_agent(model: Optional[str] = None) -> InteractionDesignerV3:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = InteractionDesignerV3(model=model)
    return _agent_instance


async def interaction_designer_v3_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Interaction Designer v3 Agent -- ReAct agent for per-scene behavioral specs.

    Reads: game_design_v3, scene_specs_v3, canonical_labels, domain_knowledge
    Writes: interaction_specs_v3 (list of InteractionSpecV3 dicts)
    """
    logger.info("InteractionDesignerV3: Starting interaction design")

    # Inject pipeline context for tool access
    from app.tools.v3_context import set_v3_tool_context
    set_v3_tool_context(state)

    model = state.get("_model_override")
    agent = _get_agent(model)

    result = await agent.run(state, ctx)

    return {
        **state,
        **result,
        "current_agent": "interaction_designer_v3",
    }
