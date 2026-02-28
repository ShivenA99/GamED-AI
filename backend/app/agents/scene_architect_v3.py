"""
Scene Architect v3 -- ReAct Agent for Per-Scene Structural Specification.

Creates detailed zone layouts, mechanic configurations, and image requirements
for each scene defined in the game_design_v3. Does NOT handle scoring, feedback,
or animations -- those are the interaction_designer_v3's responsibility.

Tools: get_zone_layout_guidance, get_mechanic_config_schema, validate_scene_spec,
       submit_scene_specs
Output: scene_specs_v3 (list of SceneSpecV3 dicts) in state
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response
from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.scene_spec_v3 import SceneSpecV3
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.scene_architect_v3")


SYSTEM_PROMPT = """\
You are the Scene Architect for GamED.AI. Your job: create detailed per-scene \
structural specifications for multi-scene, multi-mechanic interactive games.

You do NOT handle scoring, feedback, or animations -- those are configured by \
the Interaction Designer downstream.

## What You Produce (Per Scene)

For each scene in the game design, you produce a SceneSpecV3 with:
1. **Image requirements**: What the diagram image should show, its style, required elements
2. **Zones**: Interactive regions on the diagram (zone_id, label, position_hint, description, hint, difficulty)
3. **Mechanic configs**: POPULATED configuration for each mechanic in the scene
4. **Zone hierarchy**: Parent-child relationships if applicable

## Design Process

For EACH scene in the game design:
1. `get_zone_layout_guidance` -- Get spatial position hints for the scene's labels
2. `get_mechanic_config_schema` -- Look up config schema for each mechanic type
3. `generate_mechanic_content` -- MANDATORY for every non-drag_drop mechanic. \
   Generates populated configs (waypoints, prompts, descriptions, categories, pairs, nodes, etc.)
4. Build the scene spec: zones + mechanic_configs (with generated content) + image_requirements
5. `validate_scene_spec` -- Check for errors and fix

After ALL scenes are complete:
6. `submit_scene_specs` -- Submit ALL scene specs at once

CRITICAL: Do NOT skip step 3. Without generate_mechanic_content, downstream agents will \
lack the mechanic-specific data needed for scoring, feedback, and blueprint assembly.

CRITICAL: Your final action MUST be calling `submit_scene_specs` with the \
complete list of scene specs. Do NOT write scene specs as text in your response. \
Do NOT finish without calling `submit_scene_specs`. Every response you give \
should either be a tool call or lead to a tool call.

## Zone ID Convention
Generate zone_ids by snake_casing the label: "Left Atrium" -> "zone_left_atrium"
"""

# Per-mechanic config guidance — injected into task prompt for selected mechanics only
_MECHANIC_SCENE_GUIDANCE = {
    "drag_drop": (
        "**drag_drop**: Zones with positions for label placement. "
        "config = {shuffle_labels: true, show_hints: true, max_attempts: 3}. "
        "Image needs clear structures with distinct drop targets."
    ),
    "click_to_identify": (
        "**click_to_identify**: Zones + identification prompts per zone. "
        'config = {prompt_style: "name", highlight_on_hover: true, '
        "prompts: [{zone_label, prompt_text}]}. "
        "Image needs clear structures with distinct boundaries."
    ),
    "trace_path": (
        "**trace_path**: Zones + ordered waypoints defining the path. "
        'config = {drawing_mode: "click_waypoints", '
        'waypoints: [...ordered label ids...], path_type: "linear"}. '
        "Image MUST show pathways/connections between structures."
    ),
    "sequencing": (
        "**sequencing**: Items + correct order. "
        'config = {sequence_type: "linear", items: [{id, text}], '
        "correct_order: [...item ids...]}. "
        "Image should show stages/phases spatially separated."
    ),
    "sorting_categories": (
        "**sorting_categories**: Categories + items with assignments. "
        "config = {categories: [{id, name}], "
        "items: [{id, text, correct_category_id}]}. "
        "Image should show distinct items that can be categorized."
    ),
    "description_matching": (
        "**description_matching**: Zones + functional descriptions per zone. "
        'config = {mode: "match_to_zone", '
        "descriptions: [{zone_label, description}]}"
    ),
    "memory_match": (
        "**memory_match**: Term-definition pairs. "
        'config = {pairs: [{id, term, definition}], grid_size: "4x3"}'
    ),
    "branching_scenario": (
        "**branching_scenario**: Decision nodes with choices and consequences. "
        "config = {nodes: [{id, prompt, choices: [{text, next_node_id, is_correct}]}], "
        'start_node_id: "..."}'
    ),
    "compare_contrast": (
        "**compare_contrast**: Comparison categories for two subjects. "
        "config = {expected_categories: [{name, subject_a_value, subject_b_value}]}. "
        "Image should show two subjects side by side."
    ),
    "hierarchical": (
        "**hierarchical**: Zones + parent-child relationships. "
        'config = {reveal_trigger: "complete_parent", '
        "zone_groups: [{parent_zone_id, child_zone_ids: [...]}]}. "
        "Image should show nested/layered structures."
    ),
}


class SceneArchitectV3(ReActAgent):
    """ReAct agent that creates per-scene structural specifications."""

    def __init__(self, model: Optional[str] = None):
        super().__init__(
            name="scene_architect_v3",
            system_prompt=SYSTEM_PROMPT,
            max_iterations=15,
            tool_timeout=60.0,
            model=model,
            temperature=0.5,
        )

    def get_tool_names(self) -> List[str]:
        return [
            "get_zone_layout_guidance",
            "get_mechanic_config_schema",
            "generate_mechanic_content",
            "validate_scene_spec",
            "submit_scene_specs",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build task prompt from pipeline state."""
        game_design = state.get("game_design_v3") or {}
        canonical_labels = state.get("canonical_labels", [])

        sections = []

        # Game design summary
        summary = game_design.get("_summary", "")
        if summary:
            sections.append(f"## Game Design Summary\n{summary}")

        # Full game design (condensed)
        title = game_design.get("title", "Untitled")
        sections.append(f"## Game Title\n{title}")

        # Labels
        labels = game_design.get("labels", {})
        if isinstance(labels, dict):
            zone_labels = labels.get("zone_labels", [])
            distractor_labels = labels.get("distractor_labels", [])
            sections.append(f"## Zone Labels\n{json.dumps(zone_labels)}")
            if distractor_labels:
                distractor_texts = []
                for dl in distractor_labels:
                    if isinstance(dl, dict):
                        distractor_texts.append(dl.get("text", ""))
                    elif isinstance(dl, str):
                        distractor_texts.append(dl)
                sections.append(f"## Distractor Labels\n{json.dumps(distractor_texts)}")

        # Scenes from game design
        scenes = game_design.get("scenes", [])
        if scenes:
            scene_info_lines = []
            for scene in scenes:
                sn = scene.get("scene_number", "?")
                st = scene.get("title", "")
                sv = scene.get("visual_description", "")
                sm = scene.get("mechanics", [])
                mech_types = []
                for m in sm:
                    if isinstance(m, dict):
                        mech_types.append(m.get("type", "unknown"))
                    elif isinstance(m, str):
                        mech_types.append(m)
                szl = scene.get("zone_labels_in_scene", scene.get("zone_labels", []))
                scene_info_lines.append(
                    f"Scene {sn}: '{st}'\n"
                    f"  Visual: {sv}\n"
                    f"  Mechanics: {', '.join(mech_types)}\n"
                    f"  Zone labels: {json.dumps(szl)}"
                )
            sections.append(f"## Scenes from Game Design\n" + "\n\n".join(scene_info_lines))

            # Inject mechanic-specific guidance for only the mechanics in this game
            all_mech_types = set()
            for scene in scenes:
                for m in scene.get("mechanics", []):
                    mt = m.get("type", "") if isinstance(m, dict) else str(m)
                    if mt:
                        all_mech_types.add(mt)

            if all_mech_types:
                guidance_lines = []
                for mt in sorted(all_mech_types):
                    g = _MECHANIC_SCENE_GUIDANCE.get(mt)
                    if g:
                        guidance_lines.append(f"- {g}")
                if guidance_lines:
                    sections.append(
                        "## Mechanic Config Requirements (for this game)\n\n"
                        "You MUST call `generate_mechanic_content` for EVERY mechanic.\n"
                        "Here is what each mechanic needs:\n\n"
                        + "\n".join(guidance_lines)
                    )

        # Canonical labels from upstream
        if canonical_labels:
            sections.append(f"## Canonical Labels (from domain analysis)\n{', '.join(canonical_labels[:30])}")

        # Domain knowledge injection — rich data for mechanic content generation
        dk = state.get("domain_knowledge", {})
        if isinstance(dk, dict):
            label_descs = dk.get("label_descriptions")
            if label_descs:
                sections.append(f"## Label Descriptions\n{json.dumps(label_descs, indent=2)[:2500]}")
            seq_data = dk.get("sequence_flow_data")
            if seq_data:
                sections.append(f"## Sequence/Flow Data\n{json.dumps(seq_data, indent=2)[:2000]}")
            comparison_data = dk.get("comparison_data")
            if comparison_data:
                sections.append(f"## Comparison Data\n{json.dumps(comparison_data, indent=2)[:2000]}")
            term_defs = dk.get("term_definitions")
            if term_defs:
                sections.append(f"## Term Definitions\n{json.dumps(term_defs, indent=2)[:1500]}")
            causal = dk.get("causal_relationships")
            if causal:
                sections.append(f"## Causal Relationships\n{json.dumps(causal, indent=2)[:1500]}")
            spatial = dk.get("spatial_data")
            if spatial:
                sections.append(f"## Spatial Data\n{json.dumps(spatial, indent=2)[:1500]}")
            process_steps = dk.get("process_steps")
            if process_steps:
                sections.append(f"## Process Steps\n{json.dumps(process_steps, indent=2)[:1500]}")
            hierarchical_data = dk.get("hierarchical_data")
            if hierarchical_data:
                sections.append(f"## Hierarchical Data\n{json.dumps(hierarchical_data, indent=2)[:1500]}")
            content_chars = dk.get("content_characteristics")
            if content_chars:
                sections.append(f"## Content Characteristics\n{json.dumps(content_chars, indent=2)[:1000]}")

        # Difficulty
        difficulty = game_design.get("difficulty", {})
        if isinstance(difficulty, dict):
            sections.append(f"## Difficulty\n{json.dumps(difficulty)}")

        # Hierarchy
        if isinstance(labels, dict) and labels.get("hierarchy"):
            h = labels["hierarchy"]
            if isinstance(h, dict) and h.get("enabled"):
                sections.append(f"## Hierarchy\n{json.dumps(h)}")

        # Previous validation feedback (retry)
        validation = state.get("scene_validation_v3")
        retry_count = state.get("_v3_scene_retries", 0)
        if validation and not validation.get("passed", True) and retry_count > 0:
            issues = validation.get("issues", [])
            score = validation.get("score", 0)
            issues_str = "\n".join(f"- {issue}" for issue in issues)
            sections.append(f"""## IMPORTANT: Previous Scene Specs Were Rejected (Attempt {retry_count})

Score: {score:.2f}/1.0. Fix these issues:

{issues_str}""")

        sections.append("""
## Your Task

Create a complete SceneSpecV3 for EACH scene listed above. For each scene:
1. Call `get_zone_layout_guidance` with the visual description and labels
2. Call `get_mechanic_config_schema` for each mechanic type in the scene
3. For EVERY non-drag_drop mechanic, call `generate_mechanic_content` with the mechanic type, \
   zone labels, and scene context. This populates configs (waypoints, categories, descriptions, etc.)
4. Build the scene spec: zones + populated mechanic_configs + image_requirements
5. Call `validate_scene_spec` to check for errors. Fix any issues.

Then call `submit_scene_specs` with ALL scene specs as your final action.

Each zone needs: zone_id, label, position_hint, description, hint, difficulty
Each mechanic_config needs: type, zone_labels_used, config (populated from generate_mechanic_content)

IMPORTANT: Do NOT skip step 3. Do NOT use empty or default-only configs for non-drag_drop mechanics.
""")

        return "\n\n".join(sections)

    def parse_final_result(
        self,
        response: Any,
        state: AgentState,
    ) -> Dict[str, Any]:
        """Parse the LLM's final response into state updates.

        Priority:
        1. If submit_scene_specs was called successfully, extract from tool call args
        2. Fall back to JSON extraction from response text
        3. Reconstruct from tool results (guidance + config) + game_design_v3
        """
        content = response.content if hasattr(response, "content") else str(response)
        tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []
        tool_results = response.tool_results if hasattr(response, "tool_results") else []

        logger.info(
            f"SceneArchitectV3: Response content length={len(content)}, "
            f"tool_calls={len(tool_calls)}"
        )

        # Strategy 1: Check if submit_scene_specs was called successfully
        for tc, tr in zip(tool_calls, tool_results):
            if not hasattr(tc, "name") or tc.name != "submit_scene_specs":
                continue
            result_data = tr.result if hasattr(tr, "result") else {}
            if isinstance(result_data, dict) and result_data.get("status") == "accepted":
                logger.info(
                    f"SceneArchitectV3: Specs accepted via submit_scene_specs. "
                    f"Scenes: {result_data.get('scene_count', '?')}"
                )
                raw_specs = tc.arguments.get("scene_specs", [])
                validated_specs = []
                for spec_dict in raw_specs:
                    try:
                        parsed = SceneSpecV3.model_validate(spec_dict)
                        validated_specs.append(parsed.model_dump())
                    except Exception as e:
                        logger.warning(f"SceneArchitectV3: Spec re-validation warning: {e}")
                        validated_specs.append(spec_dict)
                return {
                    "current_agent": "scene_architect_v3",
                    "scene_specs_v3": validated_specs,
                }

        # Strategy 2: Extract JSON from response text
        extracted = extract_json_from_response(content)
        if extracted:
            specs_list = []
            if isinstance(extracted, list):
                specs_list = extracted
            elif isinstance(extracted, dict):
                specs_list = extracted.get("scene_specs", extracted.get("scenes", [extracted]))

            valid_specs = []
            for s in specs_list:
                if isinstance(s, dict) and (s.get("scene_number") or s.get("zones") or s.get("mechanic_configs")):
                    try:
                        parsed = SceneSpecV3.model_validate(s)
                        valid_specs.append(parsed.model_dump())
                    except Exception:
                        valid_specs.append(s)
            if valid_specs:
                logger.info(f"SceneArchitectV3: Extracted {len(valid_specs)} scene specs from response text")
                return {
                    "current_agent": "scene_architect_v3",
                    "scene_specs_v3": valid_specs,
                }

        # Strategy 3: Recover scene specs from validate_scene_spec tool call history.
        # Priority: enriched_spec from tool results > raw args from tool calls.
        # validate_scene_spec auto-enriches empty mechanic configs, so the enriched
        # version in the tool result is preferred over the raw arguments.
        recovered_specs = []
        seen_scene_numbers = set()

        # First pass: look for enriched specs in tool results
        for tc, tr in zip(tool_calls, tool_results):
            tc_name = tc.name if hasattr(tc, "name") else ""
            if tc_name != "validate_scene_spec":
                continue
            result_data = tr.result if hasattr(tr, "result") else {}
            if isinstance(result_data, dict) and result_data.get("enriched_spec"):
                spec_data = result_data["enriched_spec"]
                if isinstance(spec_data, dict) and spec_data.get("zones"):
                    sn = spec_data.get("scene_number", len(recovered_specs) + 1)
                    if sn in seen_scene_numbers:
                        recovered_specs = [s for s in recovered_specs if s.get("scene_number") != sn]
                    seen_scene_numbers.add(sn)
                    try:
                        parsed = SceneSpecV3.model_validate(spec_data)
                        recovered_specs.append(parsed.model_dump())
                    except Exception:
                        recovered_specs.append(spec_data)

        # Second pass: raw args from validate_scene_spec (for scenes not yet recovered)
        for tc in tool_calls:
            tc_name = tc.name if hasattr(tc, "name") else ""
            tc_args = tc.arguments if hasattr(tc, "arguments") else {}
            if tc_name == "validate_scene_spec" and isinstance(tc_args, dict):
                spec_data = tc_args.get("scene_spec", tc_args)
                if isinstance(spec_data, dict) and spec_data.get("zones"):
                    sn = spec_data.get("scene_number", len(recovered_specs) + 1)
                    if sn in seen_scene_numbers:
                        continue  # Already have enriched version
                    seen_scene_numbers.add(sn)
                    try:
                        parsed = SceneSpecV3.model_validate(spec_data)
                        recovered_specs.append(parsed.model_dump())
                    except Exception:
                        recovered_specs.append(spec_data)

            # Also check submit_scene_specs args (even if result wasn't "accepted")
            if tc_name == "submit_scene_specs" and isinstance(tc_args, dict):
                raw_specs = tc_args.get("scene_specs", [])
                for spec_data in raw_specs:
                    if isinstance(spec_data, dict) and spec_data.get("zones"):
                        sn = spec_data.get("scene_number", len(recovered_specs) + 1)
                        if sn not in seen_scene_numbers:
                            seen_scene_numbers.add(sn)
                            try:
                                parsed = SceneSpecV3.model_validate(spec_data)
                                recovered_specs.append(parsed.model_dump())
                            except Exception:
                                recovered_specs.append(spec_data)

        if recovered_specs:
            recovered_specs.sort(key=lambda s: s.get("scene_number", 0))
            logger.info(
                f"SceneArchitectV3: Recovered {len(recovered_specs)} scene specs "
                f"from validate_scene_spec tool call history"
            )
            return {
                "current_agent": "scene_architect_v3",
                "scene_specs_v3": recovered_specs,
            }

        logger.error("SceneArchitectV3: All extraction strategies failed")
        return {
            "current_agent": "scene_architect_v3",
            "scene_specs_v3": None,
            "_error": "Failed to extract scene specs from response or text",
        }


# ---------------------------------------------------------------------------
# Agent function (LangGraph node interface)
# ---------------------------------------------------------------------------

_agent_instance: Optional[SceneArchitectV3] = None


def _get_agent(model: Optional[str] = None) -> SceneArchitectV3:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = SceneArchitectV3(model=model)
    return _agent_instance


async def scene_architect_v3_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Scene Architect v3 Agent -- ReAct agent for per-scene structural specs.

    Reads: game_design_v3, canonical_labels, domain_knowledge
    Writes: scene_specs_v3 (list of SceneSpecV3 dicts)
    """
    logger.info("SceneArchitectV3: Starting scene architecture")

    # Inject pipeline context for tool access
    from app.tools.v3_context import set_v3_tool_context
    set_v3_tool_context(state)

    model = state.get("_model_override")
    agent = _get_agent(model)

    result = await agent.run(state, ctx)

    return {
        **state,
        **result,
        "current_agent": "scene_architect_v3",
    }
