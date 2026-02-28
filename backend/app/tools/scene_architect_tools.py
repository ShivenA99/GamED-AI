"""
Scene Architect v3 Tools -- ReAct agent toolbox for scene_architect_v3.

Four tools for building per-scene structural specifications:
1. get_zone_layout_guidance -- LLM-powered spatial hints for label placement
2. get_mechanic_config_schema -- Deterministic config schema lookup
3. validate_scene_spec -- Deterministic validation + cross-checks vs game_design_v3
4. submit_scene_specs -- Pydantic schema-as-tool for final submission
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.utils.logging_config import get_logger
from app.tools.v3_context import get_v3_tool_context

logger = get_logger("gamed_ai.tools.scene_architect")


# ---------------------------------------------------------------------------
# Tool 1: get_zone_layout_guidance (LLM-powered)
# ---------------------------------------------------------------------------

async def get_zone_layout_guidance_impl(
    visual_description: str,
    labels_list: List[str],
) -> Dict[str, Any]:
    """
    Get spatial layout guidance for zone placement on a diagram.

    Uses domain knowledge from pipeline context and an LLM call to produce
    position hints, shape recommendations, and difficulty ratings per label.
    """
    from app.tools.v3_context import get_v3_tool_context
    from app.services.llm_service import get_llm_service

    ctx = get_v3_tool_context()
    domain_knowledge = ctx.get("domain_knowledge", "")

    dk_section = ""
    if domain_knowledge:
        dk_text = domain_knowledge if isinstance(domain_knowledge, str) else json.dumps(domain_knowledge)
        dk_section = f"\n\nDomain knowledge:\n{dk_text[:1500]}"

    labels_str = ", ".join(labels_list)
    prompt = f"""You are an expert in educational diagram design. Given the following visual description and labels, provide spatial layout guidance for each label.

Visual description: {visual_description}

Labels to place: {labels_str}
{dk_section}

For EACH label, provide:
1. position_hint: A spatial description of where this element appears (e.g., "upper-left quadrant", "center of the diagram", "bottom-right near the base")
2. recommended_shape: The zone shape that best fits this element ("circle" for point-like structures, "polygon" for irregular regions, "rect" for rectangular areas)
3. difficulty: How difficult this label is to identify (1=easy/obvious, 2=moderate, 3=hard/similar to others, 4=very hard, 5=expert-level)

Respond with a JSON object:
{{
  "zones": [
    {{
      "label": "Label Name",
      "position_hint": "spatial description",
      "recommended_shape": "circle|polygon|rect",
      "difficulty": 1-5,
      "description": "Brief educational description of this structure"
    }}
  ],
  "layout_notes": "Overall layout observations"
}}"""

    system_prompt = "You are a diagram layout expert. Respond with valid JSON only."

    try:
        llm = get_llm_service()
        result = await llm.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            schema_hint="zones array with label, position_hint, recommended_shape, difficulty, description",
            model="gemini-2.5-flash",
        )
        if isinstance(result, dict):
            return result
        return {"zones": [], "layout_notes": "LLM returned non-dict", "error": str(result)}
    except Exception as e:
        logger.error(f"get_zone_layout_guidance LLM call failed: {e}")
        # Deterministic fallback: generate basic hints
        zones = []
        for i, label in enumerate(labels_list):
            zones.append({
                "label": label,
                "position_hint": "center region",
                "recommended_shape": "circle",
                "difficulty": 2,
                "description": f"The {label} structure",
            })
        return {
            "zones": zones,
            "layout_notes": f"Fallback guidance (LLM unavailable): {e}",
        }


# ---------------------------------------------------------------------------
# Tool 2: get_mechanic_config_schema (deterministic)
# ---------------------------------------------------------------------------

async def get_mechanic_config_schema_impl(
    mechanic_type: str,
) -> Dict[str, Any]:
    """
    Return the full config schema for a mechanic type from INTERACTION_PATTERNS.

    Deterministic lookup -- no LLM call. Returns configuration_options
    with defaults and descriptions.
    """
    from app.config.interaction_patterns import INTERACTION_PATTERNS

    pattern = INTERACTION_PATTERNS.get(mechanic_type)
    if not pattern:
        return {
            "found": False,
            "mechanic_type": mechanic_type,
            "error": f"Unknown mechanic type '{mechanic_type}'. Available: {sorted(INTERACTION_PATTERNS.keys())}",
        }

    return {
        "found": True,
        "mechanic_type": mechanic_type,
        "name": pattern.name,
        "status": pattern.status.value.upper(),
        "complexity": pattern.complexity.value,
        "configuration_options": pattern.configuration_options,
        "supports_multi_scene": pattern.supports_multi_scene,
        "supports_timing": pattern.supports_timing,
        "supports_partial_credit": pattern.supports_partial_credit,
        "can_combine_with": pattern.can_combine_with,
        "prerequisites": pattern.prerequisites,
        "frontend_component": pattern.frontend_component,
        "cognitive_demands": pattern.cognitive_demands,
    }


# ---------------------------------------------------------------------------
# Helper: compute grid size for memory match
# ---------------------------------------------------------------------------

def _compute_grid_size(num_pairs: int) -> str:
    """Compute a grid_size string for memory match based on number of pairs.

    Each pair = 2 cards. Grid must hold at least num_pairs * 2 cells.
    Finds the smallest cols x rows where cols * rows >= total_cards,
    cols <= 6, and the aspect ratio stays reasonable (cols >= rows).
    Returns a string like "4x3", "4x4", "5x4", etc.
    """
    import math

    total_cards = max(num_pairs * 2, 4)  # min 4 cards
    # Cap at 24 cards (6x4 max)
    total_cards = min(total_cards, 24)

    # Find best grid: prefer wider grids (cols >= rows), minimize wasted cells
    best = (6, 4)
    best_waste = 24
    for cols in range(2, 7):
        rows = math.ceil(total_cards / cols)
        if rows < 2:
            rows = 2
        if rows > cols:
            # Try swapping for wider layout
            cols, rows = rows, cols
        if cols > 6 or rows > 6:
            continue
        waste = cols * rows - total_cards
        if waste >= 0 and waste < best_waste:
            best = (cols, rows)
            best_waste = waste

    return f"{best[0]}x{best[1]}"


# ---------------------------------------------------------------------------
# Tool 2b: generate_mechanic_content (Fix 2.5 -- LLM-powered)
# ---------------------------------------------------------------------------

async def generate_mechanic_content_impl(
    mechanic_type: str,
    scene_number: int = 1,
    zone_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate populated mechanic-specific content from domain knowledge.

    Reads sequence_flow_data, label_descriptions, comparison_data from V3 context
    and produces mechanic config content (waypoints, prompts, descriptions, etc.)
    that gets embedded in the scene spec's mechanic_configs.

    This tool bridges the gap between domain knowledge and mechanic configuration.
    """
    from app.tools.v3_context import get_v3_tool_context
    from app.services.llm_service import get_llm_service

    ctx = get_v3_tool_context()
    zone_labels = zone_labels or ctx.get("canonical_labels", [])
    domain_knowledge = ctx.get("domain_knowledge", "")
    question = ctx.get("question", ctx.get("enhanced_question", ""))
    # DK sub-fields: try domain_knowledge dict first, then context root
    dk_dict = domain_knowledge if isinstance(domain_knowledge, dict) else {}
    label_descriptions = dk_dict.get("label_descriptions") or ctx.get("label_descriptions") or {}
    sequence_flow_data = dk_dict.get("sequence_flow_data") or ctx.get("sequence_flow_data")
    comparison_data = dk_dict.get("comparison_data") or ctx.get("comparison_data")

    result: Dict[str, Any] = {
        "mechanic_type": mechanic_type,
        "scene_number": scene_number,
        "generated": False,
        "config": {},
    }

    # For trace_path: generate waypoints from sequence_flow_data or LLM
    if mechanic_type == "trace_path":
        if sequence_flow_data and sequence_flow_data.get("sequence_items"):
            waypoints = [
                item.get("text", item.get("id", ""))
                for item in sequence_flow_data["sequence_items"]
            ]
            result["config"] = {
                "waypoints": waypoints,
                "path_type": sequence_flow_data.get("flow_type", "linear"),
                "drawing_mode": "click_waypoints",
                "particle_theme": "dots",
                "particle_speed": "medium",
                "color_transition_enabled": True,
                "show_direction_arrows": True,
                "show_waypoint_labels": True,
                "show_full_flow_on_complete": True,
            }
            result["generated"] = True
        else:
            # LLM fallback for trace_path
            try:
                llm = get_llm_service()
                prompt = f"""For the question "{question}", generate ordered waypoints for a trace_path mechanic using these labels: {json.dumps(zone_labels)}.

The waypoints define the PATH a student traces through the diagram (e.g., blood flow through the heart).
Order them in the biologically/scientifically correct sequence.

Return JSON: {{"waypoints": ["label1", "label2", ...], "path_type": "linear|cyclic|branching", "path_description": "brief description of what the path represents"}}"""
                llm_result = await llm.generate_json(
                    prompt=prompt,
                    system_prompt="Return valid JSON only.",
                    schema_hint="waypoints array and path_type",
                    model="gemini-2.5-flash",
                )
                if isinstance(llm_result, dict) and llm_result.get("waypoints"):
                    result["config"] = {
                        "waypoints": llm_result["waypoints"],
                        "path_type": llm_result.get("path_type", "linear"),
                        "drawing_mode": "click_waypoints",
                        "particle_theme": "dots",
                        "particle_speed": "medium",
                        "color_transition_enabled": True,
                        "show_direction_arrows": True,
                        "show_waypoint_labels": True,
                        "show_full_flow_on_complete": True,
                    }
                    result["generated"] = True
            except Exception as e:
                result["error"] = f"LLM waypoint generation failed: {e}"

    # For click_to_identify: generate structured prompts
    elif mechanic_type == "click_to_identify":
        prompts = []
        for label in zone_labels:
            desc = label_descriptions.get(label, "")
            if desc:
                prompts.append({
                    "zone_label": label,
                    "prompt_text": f"Click on the structure that {desc.lower().rstrip('.')}",
                })
            else:
                prompts.append({
                    "zone_label": label,
                    "prompt_text": f"Click on the {label}",
                })
        result["config"] = {
            "prompt_style": "functional" if label_descriptions else "naming",
            "highlight_on_hover": True,
            "highlight_style": "subtle",
            "selection_mode": "any_order",
            "prompts": prompts,
            "show_zone_count": True,
            "magnification_enabled": False,
        }
        result["generated"] = True

    # For sequencing: generate correct order from sequence_flow_data or LLM
    elif mechanic_type == "sequencing":
        if sequence_flow_data and sequence_flow_data.get("sequence_items"):
            items = []
            correct_order = []
            for idx, item in enumerate(sequence_flow_data["sequence_items"]):
                item_id = item.get("id", f"step_{idx}")
                items.append({
                    "id": item_id,
                    "text": item.get("text", ""),
                    "description": item.get("description", ""),
                    "order_index": idx,
                })
                correct_order.append(item_id)
            result["config"] = {
                "sequence_type": sequence_flow_data.get("flow_type", "linear"),
                "items": items,
                "correct_order": correct_order,
                "layout_mode": "horizontal_timeline",
                "interaction_pattern": "drag_reorder",
                "card_type": "text_only",
                "connector_style": "arrow",
                "show_position_numbers": True,
                "instructions": f"Arrange the stages in the correct order.",
            }
            result["generated"] = True
        else:
            try:
                llm = get_llm_service()
                prompt = f"""For the topic "{question}", create a sequencing exercise using these labels: {json.dumps(zone_labels)}.

Generate items that students must arrange in the correct order. Each item needs an id, text (concise name), description (1-2 sentences explaining why this position), and order_index (0-based correct position).

Return JSON: {{
  "items": [{{"id": "step_0", "text": "step name", "description": "why this is position 0", "order_index": 0}}, ...],
  "correct_order": ["step_0", "step_1", ...],
  "instructions": "Arrange ... in the correct order."
}}"""
                llm_result = await llm.generate_json(
                    prompt=prompt,
                    system_prompt="Return valid JSON only.",
                    schema_hint="items array and correct_order array",
                    model="gemini-2.5-flash",
                )
                if isinstance(llm_result, dict) and llm_result.get("items"):
                    result["config"] = {
                        "sequence_type": "linear",
                        "items": llm_result["items"],
                        "correct_order": llm_result.get("correct_order", [i["id"] for i in llm_result["items"]]),
                        "layout_mode": "horizontal_timeline",
                        "interaction_pattern": "drag_reorder",
                        "card_type": "text_only",
                        "connector_style": "arrow",
                        "show_position_numbers": True,
                        "instructions": llm_result.get("instructions", "Arrange the items in the correct order."),
                    }
                    result["generated"] = True
            except Exception as e:
                result["error"] = f"LLM sequencing generation failed: {e}"

    # For sorting_categories: generate from comparison_data or LLM
    elif mechanic_type == "sorting_categories":
        if comparison_data and comparison_data.get("sorting_categories"):
            categories = comparison_data["sorting_categories"]
            items = []
            for group in comparison_data.get("groups", []):
                cat_id = None
                group_name_lower = group.get("group_name", "").lower()
                for cat in categories:
                    cat_name_lower = cat.get("name", "").lower()
                    if cat_name_lower == group_name_lower or group_name_lower in cat_name_lower or cat_name_lower in group_name_lower:
                        cat_id = cat.get("id")
                        break
                if not cat_id and categories:
                    cat_id = categories[0].get("id")
                for member in group.get("members", []):
                    items.append({
                        "id": f"item_{member.lower().replace(' ', '_')[:30]}",
                        "text": member,
                        "correct_category_ids": [cat_id] if cat_id else [],
                    })
            result["config"] = {
                "categories": categories,
                "items": items,
                "sort_mode": "bucket",
                "submit_mode": "batch_submit",
                "show_category_hints": True,
                "instructions": f"Sort each item into the correct category.",
            }
            result["generated"] = True
        else:
            try:
                llm = get_llm_service()
                prompt = f"""For the topic "{question}", create a sorting exercise using these labels: {json.dumps(zone_labels)}.
Group these items into 2-4 categories. Each item must have correct_category_ids as a LIST of category IDs.

Return JSON: {{
  "categories": [{{"id": "cat_1", "name": "Category Name", "description": "what belongs here", "color": "#hex"}}, ...],
  "items": [{{"id": "item_1", "text": "label text", "correct_category_ids": ["cat_1"]}}, ...],
  "instructions": "Sort each item into the correct category."
}}"""
                llm_result = await llm.generate_json(
                    prompt=prompt,
                    system_prompt="Return valid JSON only.",
                    schema_hint="categories array and items array",
                    model="gemini-2.5-flash",
                )
                if isinstance(llm_result, dict) and llm_result.get("categories") and llm_result.get("items"):
                    # Normalize items to use correct_category_ids (list)
                    for item in llm_result["items"]:
                        if "correct_category" in item and "correct_category_ids" not in item:
                            item["correct_category_ids"] = [item.pop("correct_category")]
                    result["config"] = {
                        "categories": llm_result["categories"],
                        "items": llm_result["items"],
                        "sort_mode": "bucket",
                        "submit_mode": "batch_submit",
                        "show_category_hints": True,
                        "instructions": llm_result.get("instructions", "Sort each item into the correct category."),
                    }
                    result["generated"] = True
            except Exception as e:
                result["error"] = f"LLM sorting generation failed: {e}"

    # For description_matching: generate functional descriptions
    elif mechanic_type == "description_matching":
        if label_descriptions:
            descriptions = []
            for label in zone_labels:
                desc = label_descriptions.get(label)
                if desc:
                    descriptions.append({
                        "zone_label": label,
                        "description": desc,
                    })
            if descriptions:
                result["config"] = {
                    "mode": "match_to_zone",
                    "descriptions": descriptions,
                    "show_connecting_lines": True,
                    "description_panel_position": "right",
                }
                result["generated"] = True
        if not result["generated"]:
            try:
                llm = get_llm_service()
                prompt = f"""For the topic "{question}", write a 15-30 word FUNCTIONAL description for each label.
Labels: {json.dumps(zone_labels)}

Focus on WHAT EACH PART DOES or its ROLE, not what it looks like.
Example: "Left Ventricle" -> "Pumps oxygenated blood through the aorta to supply the entire body"

Also generate 2-3 distractor descriptions (plausible but don't match any label).

Return JSON: {{
  "descriptions": [{{"zone_label": "label", "description": "functional description"}}, ...],
  "distractor_descriptions": ["plausible wrong description 1", ...]
}}"""
                llm_result = await llm.generate_json(
                    prompt=prompt,
                    system_prompt="Return valid JSON only. Write functional descriptions, NOT appearance-based.",
                    schema_hint="descriptions array with zone_label and description",
                    model="gemini-2.5-flash",
                )
                if isinstance(llm_result, dict) and llm_result.get("descriptions"):
                    result["config"] = {
                        "mode": "match_to_zone",
                        "descriptions": llm_result["descriptions"],
                        "distractor_descriptions": llm_result.get("distractor_descriptions", []),
                        "show_connecting_lines": True,
                        "description_panel_position": "right",
                    }
                    result["generated"] = True
            except Exception as e:
                result["error"] = f"LLM description matching generation failed: {e}"

    # For memory_match: generate rich pairs from labels + descriptions
    elif mechanic_type == "memory_match":
        if label_descriptions and any(label_descriptions.values()):
            # Use label descriptions for term→definition pairs
            pairs = []
            for label in zone_labels[:10]:
                desc = label_descriptions.get(label, "")
                if desc:
                    pairs.append({
                        "id": f"pair_{label.lower().replace(' ', '_')[:20]}",
                        "term": label,
                        "definition": desc,
                        "front_type": "text",
                        "back_type": "text",
                        "explanation": f"{label}: {desc}",
                    })
            if pairs:
                result["config"] = {
                    "pairs": pairs,
                    "game_variant": "classic",
                    "match_type": "term_to_definition",
                    "grid_size": _compute_grid_size(len(pairs)),
                    "card_back_style": "pattern",
                    "matched_card_behavior": "fade",
                    "show_explanation_on_match": True,
                    "instructions": "Find all matching pairs by flipping cards.",
                }
                result["generated"] = True
        if not result["generated"]:
            # LLM fallback for memory_match
            try:
                llm = get_llm_service()
                prompt = f"""For the topic "{question}", create memory match pairs using these labels: {json.dumps(zone_labels[:10])}.

Each pair has a term (the label name) and a definition (what it does/is, 10-20 words).
Generate an explanation for each pair (shown when matched).

Return JSON: {{
  "pairs": [{{"id": "pair_1", "term": "label name", "definition": "functional description", "explanation": "educational note"}}, ...]
}}"""
                llm_result = await llm.generate_json(
                    prompt=prompt,
                    system_prompt="Return valid JSON only.",
                    schema_hint="pairs array with id, term, definition, explanation",
                    model="gemini-2.5-flash",
                )
                if isinstance(llm_result, dict) and llm_result.get("pairs"):
                    pairs = llm_result["pairs"]
                    result["config"] = {
                        "pairs": pairs,
                        "game_variant": "classic",
                        "match_type": "term_to_definition",
                        "grid_size": _compute_grid_size(len(pairs)),
                        "card_back_style": "pattern",
                        "matched_card_behavior": "fade",
                        "show_explanation_on_match": True,
                        "instructions": "Find all matching pairs by flipping cards.",
                    }
                    result["generated"] = True
            except Exception as e:
                result["error"] = f"LLM memory match generation failed: {e}"

    # For compare_contrast: generate from comparison_data or LLM fallback
    elif mechanic_type == "compare_contrast":
        if comparison_data:
            expected_categories = {}
            for group in comparison_data.get("groups", []):
                group_name = group.get("group_name", "")
                for member in group.get("members", []):
                    expected_categories[member] = group_name
            result["config"] = {
                "expected_categories": expected_categories,
                "highlight_matching": True,
                "similarities": comparison_data.get("similarities", []),
                "differences": comparison_data.get("differences", []),
            }
            result["generated"] = True
        else:
            # LLM fallback when comparison_data is not available
            try:
                llm = get_llm_service()
                prompt = f"""For the topic "{question}", create a compare-and-contrast exercise using these concepts: {json.dumps(zone_labels[:12])}.

Identify similarities and differences between the key structures/concepts.

Return JSON:
{{
  "expected_categories": [
    {{"name": "label text", "category": "similar|different|unique_a|unique_b", "explanation": "why"}}
  ],
  "similarities": ["shared trait 1", "shared trait 2"],
  "differences": ["difference 1", "difference 2"],
  "subjects": ["Subject A name", "Subject B name"],
  "instructions": "Compare the structures and categorize each as similar, different, or unique to one subject."
}}

Requirements:
- At least 4 categories
- Include both similarities and differences
- Each category must have a clear explanation
"""
                response = await llm.generate_json(
                    prompt=prompt,
                    system_prompt="You generate structured compare-and-contrast educational content.",
                    model=ctx.get("model"),
                )
                if response and isinstance(response, dict):
                    result["config"] = {
                        "expected_categories": response.get("expected_categories", []),
                        "highlight_matching": True,
                        "similarities": response.get("similarities", []),
                        "differences": response.get("differences", []),
                        "subjects": response.get("subjects", []),
                        "instructions": response.get("instructions", ""),
                    }
                    result["generated"] = True
            except Exception as e:
                result["error"] = f"LLM compare_contrast generation failed: {e}"

    # BG-FIX-2: For branching_scenario: generate decision tree from LLM
    elif mechanic_type == "branching_scenario":
        try:
            llm = get_llm_service()
            prompt = f"""For the topic "{question}", create a branching educational scenario using these concepts: {json.dumps(zone_labels[:8])}.

Generate a decision tree where students make choices and see consequences. Each node should test understanding of the topic.

Return JSON:
{{
  "nodes": [
    {{
      "id": "start",
      "text": "scenario description or question",
      "options": [
        {{"id": "opt_1", "text": "choice text", "nextNodeId": "node_2", "isCorrect": true, "consequence": "explanation of why"}}
      ]
    }}
  ],
  "startNodeId": "start"
}}

Requirements:
- 4-6 nodes minimum
- At least 2 options per node
- Mark correct/incorrect paths
- Include educational consequences for wrong choices
- End nodes should have no options array"""
            llm_result = await llm.generate_json(
                prompt=prompt,
                system_prompt="Return valid JSON only. Create educationally meaningful branching scenarios.",
                schema_hint="nodes array with id/text/options, startNodeId",
                model="gemini-2.5-flash",
            )
            if isinstance(llm_result, dict) and llm_result.get("nodes"):
                result["config"] = {
                    "nodes": llm_result["nodes"],
                    "startNodeId": llm_result.get("startNodeId", "start"),
                    "show_path_taken": True,
                    "allow_backtrack": True,
                }
                result["generated"] = True
        except Exception as e:
            result["error"] = f"LLM branching scenario generation failed: {e}"

    # For drag_drop: labels will use descriptions (set by blueprint assembler).
    # Image generation keeps text labels visible so user matches descriptions to them.
    elif mechanic_type == "drag_drop":
        result["config"] = {
            "shuffle_labels": True,
            "show_hints": True,
            "max_attempts": 3,
            "display_mode": "description",  # Blueprint assembler uses label_descriptions for label text
        }
        result["generated"] = True

    if not result["generated"]:
        result["note"] = (
            f"No upstream data available to generate content for '{mechanic_type}'. "
            f"Use default/static config. Available DK fields: "
            f"label_descriptions={'yes' if label_descriptions else 'no'}, "
            f"sequence_flow_data={'yes' if sequence_flow_data else 'no'}, "
            f"comparison_data={'yes' if comparison_data else 'no'}"
        )

    return result


# ---------------------------------------------------------------------------
# Tool 3: validate_scene_spec (deterministic)
# ---------------------------------------------------------------------------

async def validate_scene_spec_impl(
    scene_spec: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate a single scene spec against the SceneSpecV3 schema.

    Also cross-checks against game_design_v3 from pipeline context.
    """
    from app.agents.schemas.scene_spec_v3 import SceneSpecV3
    from app.tools.v3_context import get_v3_tool_context

    ctx = get_v3_tool_context()
    game_design = ctx.get("game_design_v3") or {}

    errors = []
    warnings = []

    # Pydantic validation
    try:
        parsed = SceneSpecV3.model_validate(scene_spec)
    except Exception as e:
        error_str = str(e)
        actionable = []
        for line in error_str.split("\n"):
            line = line.strip()
            if not line or line.startswith("For further") or "validation error" in line.lower():
                continue
            actionable.append(line)
        return {
            "valid": False,
            "errors": actionable[:8] if actionable else [error_str[:500]],
            "warnings": [],
        }

    # Internal checks
    if not parsed.zones:
        errors.append(f"Scene {parsed.scene_number}: no zones defined")
    if not parsed.mechanic_configs:
        errors.append(f"Scene {parsed.scene_number}: no mechanic_configs defined")
    if not parsed.image_description:
        warnings.append(f"Scene {parsed.scene_number}: empty image_description")

    for z in parsed.zones:
        if not z.position_hint:
            warnings.append(f"Scene {parsed.scene_number}, zone '{z.label}': missing position_hint")
        if not z.hint:
            warnings.append(f"Scene {parsed.scene_number}, zone '{z.label}': missing hint text")

    # Cross-check vs game_design_v3
    if game_design:
        design_scenes = game_design.get("scenes", [])
        design_scene = next(
            (s for s in design_scenes if s.get("scene_number") == parsed.scene_number),
            None,
        )
        if design_scene:
            # Check mechanic types match
            design_mechanics = design_scene.get("mechanics", [])
            design_types = set()
            for m in design_mechanics:
                if isinstance(m, dict):
                    design_types.add(m.get("type", ""))
                elif isinstance(m, str):
                    design_types.add(m)
            spec_types = {mc.type for mc in parsed.mechanic_configs}
            if design_types and design_types != spec_types:
                errors.append(
                    f"Scene {parsed.scene_number}: mechanic type mismatch. "
                    f"Design expects {sorted(design_types)}, spec has {sorted(spec_types)}"
                )

            # Check zone labels match
            design_zone_labels = set(design_scene.get("zone_labels_in_scene", []) or design_scene.get("zone_labels", []))
            spec_zone_labels = {z.label for z in parsed.zones}
            missing = design_zone_labels - spec_zone_labels
            if missing:
                warnings.append(
                    f"Scene {parsed.scene_number}: design labels missing from spec zones: {missing}"
                )

    # Auto-enrich empty mechanic configs for non-drag_drop mechanics.
    # The LLM often skips generate_mechanic_content, leaving configs empty.
    # We auto-populate here so downstream agents get usable data.
    enriched_spec = None
    enriched_mechanics = []
    _NEEDS_CONTENT = {
        "trace_path", "click_to_identify", "sequencing", "sorting_categories",
        "description_matching", "memory_match", "compare_contrast",
        "branching_scenario", "hierarchical",
    }
    _CONFIG_FIELD_MAP = {
        "trace_path": "path_config",
        "click_to_identify": "click_config",
        "sequencing": "sequence_config",
        "sorting_categories": "sorting_config",
        "branching_scenario": "branching_config",
        "compare_contrast": "compare_config",
        "memory_match": "memory_config",
        "description_matching": "description_match_config",
    }

    spec_dict = parsed.model_dump()
    zone_labels_in_spec = [z.label for z in parsed.zones]

    for i, mc in enumerate(parsed.mechanic_configs):
        if mc.type not in _NEEDS_CONTENT:
            continue
        # Check if typed config is populated
        typed_config = mc.get_typed_config()
        has_typed = typed_config is not None
        # Check if generic config dict has meaningful content (more than just defaults)
        has_generic = bool(mc.config) and len(mc.config) > 2  # {shuffle_labels, show_hints} = 2 defaults
        if has_typed or has_generic:
            continue
        # Config is empty — auto-generate
        try:
            generated = await generate_mechanic_content_impl(
                mechanic_type=mc.type,
                scene_number=parsed.scene_number,
                zone_labels=zone_labels_in_spec,
            )
            if generated.get("generated") and generated.get("config"):
                gen_config = generated["config"]
                # Update the spec dict's mechanic_configs entry
                spec_dict["mechanic_configs"][i]["config"] = gen_config
                # Also set the typed field if applicable
                field_name = _CONFIG_FIELD_MAP.get(mc.type)
                if field_name:
                    spec_dict["mechanic_configs"][i][field_name] = gen_config
                enriched_mechanics.append(mc.type)
                warnings.append(
                    f"Scene {parsed.scene_number}: auto-populated config for '{mc.type}' "
                    f"(was empty). Config keys: {sorted(gen_config.keys())[:5]}"
                )
        except Exception as e:
            warnings.append(
                f"Scene {parsed.scene_number}: failed to auto-populate '{mc.type}' config: {str(e)[:100]}"
            )

    if enriched_mechanics:
        enriched_spec = spec_dict

    valid = len(errors) == 0
    score = max(0.0, 1.0 - 0.15 * len(errors) - 0.05 * len(warnings))

    result = {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "score": round(score, 3),
    }
    if enriched_spec:
        result["enriched_spec"] = enriched_spec
        result["enriched_mechanics"] = enriched_mechanics
    return result


# ---------------------------------------------------------------------------
# Tool 4: submit_scene_specs (Pydantic schema-as-tool)
# ---------------------------------------------------------------------------

async def submit_scene_specs_impl(
    scene_specs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Submit all scene specs for downstream processing.

    Validates each spec via SceneSpecV3, then cross-checks the full set
    against game_design_v3 via validate_scene_specs().
    """
    from app.agents.schemas.scene_spec_v3 import SceneSpecV3, validate_scene_specs
    from app.tools.v3_context import get_v3_tool_context

    ctx = get_v3_tool_context()
    game_design = ctx.get("game_design_v3") or {}

    # Individual parse validation
    parse_errors = []
    parsed_specs = []
    for i, spec_dict in enumerate(scene_specs):
        try:
            parsed = SceneSpecV3.model_validate(spec_dict)
            parsed_specs.append(parsed)
        except Exception as e:
            parse_errors.append(f"Scene spec [{i}]: {str(e)[:300]}")

    if parse_errors:
        return {
            "status": "rejected",
            "errors": parse_errors[:5],
            "hint": "Fix schema errors in individual scene specs and resubmit.",
        }

    # Cross-stage validation
    spec_dicts = [p.model_dump() for p in parsed_specs]
    validation = validate_scene_specs(spec_dicts, game_design)

    if not validation.get("passed", False):
        return {
            "status": "rejected",
            "errors": validation.get("issues", []),
            "hint": "Fix cross-stage issues (label coverage, scene number alignment, mechanic matching) and resubmit.",
        }

    summaries = [p.summary() for p in parsed_specs]
    return {
        "status": "accepted",
        "scene_count": len(parsed_specs),
        "summaries": summaries,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_scene_architect_tools() -> None:
    """Register all scene architect v3 tools in the tool registry."""
    from app.tools.registry import register_tool

    register_tool(
        name="get_zone_layout_guidance",
        description=(
            "Get spatial layout guidance for zone placement on a diagram. "
            "Returns position hints, shape recommendations, and difficulty "
            "ratings per label. Uses LLM + domain knowledge."
        ),
        parameters={
            "type": "object",
            "properties": {
                "visual_description": {
                    "type": "string",
                    "description": "Description of the diagram/image for this scene",
                },
                "labels_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels that need zone placement in this scene",
                },
            },
            "required": ["visual_description", "labels_list"],
        },
        function=get_zone_layout_guidance_impl,
    )

    register_tool(
        name="get_mechanic_config_schema",
        description=(
            "Get the full configuration schema for a mechanic type. "
            "Returns all config options with defaults, compatibility info, "
            "prerequisites, and frontend component name. Deterministic."
        ),
        parameters={
            "type": "object",
            "properties": {
                "mechanic_type": {
                    "type": "string",
                    "description": "The mechanic type to look up (e.g., 'drag_drop', 'trace_path')",
                },
            },
            "required": ["mechanic_type"],
        },
        function=get_mechanic_config_schema_impl,
    )

    register_tool(
        name="generate_mechanic_content",
        description=(
            "Generate populated mechanic-specific content (waypoints, prompts, descriptions, "
            "sorting categories, etc.) from domain knowledge. Call this for EACH mechanic "
            "(including drag_drop) to get rich content that populates the mechanic config. "
            "Reads sequence_flow_data, label_descriptions, comparison_data from pipeline context."
        ),
        parameters={
            "type": "object",
            "properties": {
                "mechanic_type": {
                    "type": "string",
                    "description": "The mechanic type to generate content for",
                },
                "scene_number": {
                    "type": "integer",
                    "description": "Scene number (1-based) to generate content for",
                },
                "zone_labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Zone labels in this scene (optional, defaults to all canonical labels)",
                },
            },
            "required": ["mechanic_type"],
        },
        function=generate_mechanic_content_impl,
    )

    register_tool(
        name="validate_scene_spec",
        description=(
            "Validate a single scene spec against the SceneSpecV3 schema. "
            "Cross-checks against game_design_v3 for mechanic type and label "
            "consistency. Returns errors, warnings, and a score."
        ),
        parameters={
            "type": "object",
            "properties": {
                "scene_spec": {
                    "type": "object",
                    "description": "A single scene spec to validate",
                },
            },
            "required": ["scene_spec"],
        },
        function=validate_scene_spec_impl,
    )

    register_tool(
        name="submit_scene_specs",
        description=(
            "Submit ALL scene specs for downstream processing. "
            "Pass a list of complete scene spec objects. "
            "Each is validated against SceneSpecV3, then cross-checked "
            "against game_design_v3 for label coverage and mechanic matching. "
            "Returns {status: 'accepted'} on success or {status: 'rejected', errors} on failure."
        ),
        parameters={
            "type": "object",
            "properties": {
                "scene_specs": {
                    "type": "array",
                    "description": "List of scene spec objects, one per scene",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scene_number": {"type": "integer", "description": "Scene number (1-based)"},
                            "title": {"type": "string", "description": "Scene title"},
                            "image_description": {"type": "string", "description": "Description of the diagram for this scene"},
                            "image_requirements": {
                                "type": "array", "items": {"type": "string"},
                                "description": "Specific requirements for the image"
                            },
                            "image_style": {"type": "string", "description": "Image style (e.g., 'clean_educational')"},
                            "zones": {
                                "type": "array",
                                "description": "Zone specs with zone_id, label, position_hint, description, hint, difficulty",
                                "items": {"type": "object"},
                            },
                            "mechanic_configs": {
                                "type": "array",
                                "description": "Mechanic configs with type, zone_labels_used, config",
                                "items": {"type": "object"},
                            },
                            "zone_hierarchy": {
                                "type": "array",
                                "description": "Zone hierarchy groups: [{parent, children, reveal_trigger}]",
                                "items": {"type": "object"},
                            },
                        },
                        "required": ["scene_number", "zones", "mechanic_configs"],
                    },
                },
            },
            "required": ["scene_specs"],
        },
        function=submit_scene_specs_impl,
    )

    logger.info("Registered 5 scene architect v3 tools")
