"""
Interaction Designer v3 Tools -- ReAct agent toolbox for interaction_designer_v3.

Four tools for building per-scene behavioral specifications:
1. get_scoring_templates -- Deterministic scoring template lookup
2. generate_misconception_feedback -- LLM-powered misconception analysis
3. validate_interactions -- Deterministic validation + cross-checks
4. submit_interaction_specs -- Pydantic schema-as-tool for final submission
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.tools.interaction_designer")


# ---------------------------------------------------------------------------
# Tool 1: get_scoring_templates (deterministic)
# ---------------------------------------------------------------------------

async def get_scoring_templates_impl(
    mechanic_type: str,
    difficulty_level: str = "medium",
) -> Dict[str, Any]:
    """
    Return scoring templates for a mechanic type at a given difficulty level.

    Deterministic lookup from pedagogical_constants and interaction_patterns.
    Returns recommended scoring values with explanations.
    """
    from app.config.pedagogical_constants import (
        DEFAULT_SCORING,
        DEFAULT_THRESHOLDS,
        BLOOM_COMPLEXITY,
    )
    from app.config.interaction_patterns import SCORING_STRATEGIES

    # Difficulty multipliers
    difficulty_multipliers = {
        "easy": 0.8,
        "medium": 1.0,
        "hard": 1.2,
        "advanced": 1.5,
    }
    multiplier = difficulty_multipliers.get(difficulty_level, 1.0)

    # Base scoring from defaults
    base_points = DEFAULT_SCORING["base_points_per_zone"]
    adjusted_points = round(base_points * multiplier)

    # Build templates for each scoring strategy
    templates = {}
    for strategy_id, strategy in SCORING_STRATEGIES.items():
        strategy_base = strategy.get("base_points_per_zone", base_points)
        templates[strategy_id] = {
            "name": strategy["name"],
            "description": strategy["description"],
            "points_per_correct": round(strategy_base * multiplier),
            "partial_credit": strategy.get("partial_credit", True),
            "hint_penalty": strategy.get("hint_penalty_percentage", 20) / 100.0,
            "formula": strategy.get("formula", ""),
        }
        if strategy.get("time_bonus_enabled"):
            templates[strategy_id]["time_bonus_max"] = strategy.get("time_bonus_max", 50)
        if strategy.get("streak_multiplier"):
            templates[strategy_id]["streak_multiplier"] = strategy.get("streak_multiplier", 1.5)
            templates[strategy_id]["max_multiplier"] = strategy.get("max_multiplier", 3.0)

    # Recommend strategy based on mechanic type
    recommended_strategy = "standard"
    mechanic_strategy_map = {
        "drag_drop": "standard",
        "click_to_identify": "standard",
        "trace_path": "progressive",
        "hierarchical": "progressive",
        "sequencing": "progressive",
        "sorting_categories": "standard",
        "memory_match": "time_based",
        "branching_scenario": "mastery",
        "compare_contrast": "mastery",
        "timed_challenge": "time_based",
        "description_matching": "standard",
    }
    recommended_strategy = mechanic_strategy_map.get(mechanic_type, "standard")

    # Build recommended config
    rec_template = templates.get(recommended_strategy, templates.get("standard", {}))

    return {
        "mechanic_type": mechanic_type,
        "difficulty_level": difficulty_level,
        "recommended_strategy": recommended_strategy,
        "recommended_config": {
            "strategy": recommended_strategy,
            "points_per_correct": rec_template.get("points_per_correct", adjusted_points),
            "max_score": rec_template.get("points_per_correct", adjusted_points) * 10,
            "partial_credit": rec_template.get("partial_credit", True),
            "hint_penalty": rec_template.get("hint_penalty", 0.1),
        },
        "all_strategies": templates,
        "thresholds": DEFAULT_THRESHOLDS,
    }


# ---------------------------------------------------------------------------
# Tool 2: generate_misconception_feedback (LLM-powered)
# ---------------------------------------------------------------------------

async def generate_misconception_feedback_impl(
    zone_labels: List[str],
    distractor_labels: Optional[List[str]] = None,
    subject: str = "",
    mechanic_type: str = "drag_drop",
) -> Dict[str, Any]:
    """
    Generate targeted misconception feedback for zone and distractor labels.

    Uses LLM + domain knowledge from pipeline context to produce per-label
    misconception triggers with pedagogical messages. The misconception model
    adapts to the mechanic type (ordering errors for sequencing, category
    confusion for sorting, identification errors for click_to_identify, etc.).
    """
    from app.tools.v3_context import get_v3_tool_context
    from app.services.llm_service import get_llm_service

    ctx = get_v3_tool_context()
    domain_knowledge = ctx.get("domain_knowledge", "")
    subject = subject or ctx.get("subject", "")
    distractor_labels = distractor_labels or []

    dk_section = ""
    if domain_knowledge:
        dk_text = domain_knowledge if isinstance(domain_knowledge, str) else json.dumps(domain_knowledge)
        dk_section = f"\n\nDomain knowledge:\n{dk_text[:2500]}"

    zone_str = ", ".join(zone_labels)
    distractor_str = ", ".join(distractor_labels) if distractor_labels else "none"

    # Build mechanic-specific misconception prompt
    mechanic_guidance = _get_misconception_guidance(mechanic_type)

    prompt = f"""You are an expert educational assessment designer specializing in misconception-targeted feedback.

Subject: {subject or 'general'}
Mechanic type: {mechanic_type}
Labels: {zone_str}
Distractor labels: {distractor_str}
{dk_section}

{mechanic_guidance}

For each DISTRACTOR label, generate feedback explaining why it's not a valid answer.

Respond with JSON:
{{
  "misconception_feedback": [
    {{
      "trigger_label": "Label or item involved",
      "trigger_zone": "Wrong zone/position/category",
      "message": "Pedagogical explanation (2-3 sentences)"
    }}
  ],
  "distractor_feedback": [
    {{
      "distractor": "Wrong Label",
      "feedback": "This is not correct because..."
    }}
  ]
}}"""

    system_prompt = (
        "You are an educational misconception expert. Generate targeted, "
        "pedagogically sound feedback for common student errors. "
        "Respond with valid JSON only."
    )

    try:
        llm = get_llm_service()
        result = await llm.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            schema_hint="misconception_feedback array and distractor_feedback array",
            model="gemini-2.5-flash",
        )
        if isinstance(result, dict):
            return result
        return {"misconception_feedback": [], "distractor_feedback": [], "error": str(result)}
    except Exception as e:
        logger.error(f"generate_misconception_feedback LLM call failed: {e}")
        # Deterministic fallback
        misconceptions = []
        for i, label in enumerate(zone_labels):
            if len(zone_labels) > 1:
                wrong_zone = zone_labels[(i + 1) % len(zone_labels)]
                misconceptions.append({
                    "trigger_label": label,
                    "trigger_zone": f"zone_{wrong_zone.lower().replace(' ', '_')}",
                    "message": f"{label} is commonly confused with {wrong_zone}. Look carefully at the position and characteristics.",
                })
        distractor_fb = []
        for dl in distractor_labels:
            distractor_fb.append({
                "distractor": dl,
                "feedback": f"{dl} is not a correct answer for this diagram. Review the labeled structures.",
            })
        return {
            "misconception_feedback": misconceptions,
            "distractor_feedback": distractor_fb,
            "note": f"Fallback feedback (LLM unavailable): {e}",
        }


def _get_misconception_guidance(mechanic_type: str) -> str:
    """Return mechanic-specific guidance for misconception generation."""
    if mechanic_type in ("drag_drop", "description_matching"):
        return """For drag_drop/description_matching, generate label-zone PAIRING misconceptions:
- trigger_label: The label being placed/matched
- trigger_zone: The WRONG zone it might be placed on (use another label's zone)
- message: WHY the student confused these two structures"""

    elif mechanic_type in ("sequencing", "trace_path"):
        return """For sequencing/trace_path, generate ORDERING misconceptions:
- trigger_label: The item/waypoint being ordered
- trigger_zone: The wrong POSITION it's commonly placed at (e.g. "position_2" or the label that should go there)
- message: WHY students confuse the order of these steps (e.g. visually adjacent but functionally different)"""

    elif mechanic_type == "sorting_categories":
        return """For sorting, generate CATEGORY ASSIGNMENT misconceptions:
- trigger_label: The item being sorted
- trigger_zone: The WRONG category it's commonly placed in
- message: WHY students confuse which category this belongs to"""

    elif mechanic_type == "memory_match":
        return """For memory_match, generate ASSOCIATION misconceptions:
- trigger_label: A term that students struggle to match
- trigger_zone: The WRONG definition it's commonly paired with
- message: WHY students confuse this term with a similar-sounding or similar-looking concept"""

    elif mechanic_type == "click_to_identify":
        return """For click_to_identify, generate IDENTIFICATION misconceptions:
- trigger_label: The structure being asked about
- trigger_zone: The WRONG structure students commonly click (visually similar or adjacent)
- message: HOW to distinguish these two structures and why they look similar"""

    elif mechanic_type == "branching_scenario":
        return """For branching scenarios, generate DECISION misconceptions:
- trigger_label: The decision point/prompt
- trigger_zone: The WRONG choice commonly selected
- message: WHY students make this choice and what they misunderstand"""

    elif mechanic_type == "compare_contrast":
        return """For compare_contrast, generate CATEGORIZATION misconceptions:
- trigger_label: The attribute being categorized
- trigger_zone: The WRONG subject or category (similarity vs difference)
- message: WHY students confuse whether this is a similarity or difference"""

    else:
        return """Generate misconceptions relevant to this interaction:
- trigger_label: The element involved
- trigger_zone: The wrong target
- message: Pedagogical explanation"""


# ---------------------------------------------------------------------------
# Tool 2b: enrich_mechanic_content (Fix 2.7 -- LLM-powered)
# ---------------------------------------------------------------------------

async def enrich_mechanic_content_impl(
    mechanic_type: str,
    scene_number: int = 1,
) -> Dict[str, Any]:
    """
    Enrich mechanic content pedagogically using LLM.

    Reads scene_specs_v3 from V3 context to find the existing mechanic config
    for the specified scene, then uses LLM to add pedagogically rich scoring
    rationale, feedback messages, and misconception triggers.

    Each mechanic type gets a tailored prompt that references its upstream
    config data and asks for mechanic-specific enrichments (per-waypoint
    feedback, per-item feedback, per-category feedback, etc.).

    Returns:
        Dict with enriched scoring, feedback, content_enrichments, and misconception_triggers.
    """
    from app.tools.v3_context import get_v3_tool_context
    from app.services.llm_service import get_llm_service

    ctx = get_v3_tool_context()
    scene_specs = ctx.get("scene_specs_v3") or []
    domain_knowledge = ctx.get("domain_knowledge", "")
    # Label descriptions live under domain_knowledge dict
    dk_dict = domain_knowledge if isinstance(domain_knowledge, dict) else {}
    label_descriptions = dk_dict.get("label_descriptions") or ctx.get("label_descriptions") or {}
    question = ctx.get("question", ctx.get("enhanced_question", ""))

    # Find the scene spec
    scene_spec = None
    for spec in scene_specs:
        if isinstance(spec, dict) and spec.get("scene_number") == scene_number:
            scene_spec = spec
            break

    # Find existing mechanic config for this type
    existing_config = {}
    zone_labels_in_scene = []
    if scene_spec:
        zone_labels_in_scene = [
            z.get("label", "") for z in scene_spec.get("zones", [])
            if isinstance(z, dict) and z.get("label")
        ]
        for mc in scene_spec.get("mechanic_configs", []):
            if isinstance(mc, dict) and mc.get("type") == mechanic_type:
                existing_config = mc.get("config", {})
                break

    dk_section = ""
    if domain_knowledge:
        dk_text = domain_knowledge if isinstance(domain_knowledge, str) else json.dumps(domain_knowledge)
        dk_section = f"\nDomain knowledge:\n{dk_text[:2000]}"

    labels_str = ", ".join(zone_labels_in_scene[:20])
    config_str = json.dumps(existing_config, indent=2)[:800]

    llm = get_llm_service()

    # Build mechanic-specific prompt sections
    mechanic_prompt = _build_mechanic_enrichment_prompt(
        mechanic_type, existing_config, zone_labels_in_scene, label_descriptions
    )

    prompt = f"""You are an expert educational assessment designer specializing in interactive learning experiences.

Question: {question}
Mechanic type: {mechanic_type}
Scene: {scene_number}
Zone labels: {labels_str}
Existing config from scene architect: {config_str}
{dk_section}

{mechanic_prompt}

Return your response as valid JSON matching the schema described above.
Rules:
- Scoring should reflect the difficulty and cognitive demand of this specific mechanic
- ALL feedback must be specific to the subject matter ("{question}"), not generic
- Include at least 2-3 misconception triggers based on common student errors for this topic
- content_enrichments should contain mechanic-specific data (per-item, per-step, per-pair, etc.)
"""

    try:
        result = await llm.generate_json(
            prompt=prompt,
            system_prompt="You are an educational assessment expert. Return valid JSON only.",
            schema_hint="Enriched mechanic content with scoring, feedback, misconception_triggers, content_enrichments",
            model="gemini-2.5-flash",
        )
        if isinstance(result, dict):
            result["mechanic_type"] = mechanic_type
            result["scene_number"] = scene_number
            result["enriched"] = True
            return result
        return {
            "mechanic_type": mechanic_type,
            "scene_number": scene_number,
            "enriched": False,
            "error": "LLM returned non-dict",
        }
    except Exception as e:
        logger.error(f"enrich_mechanic_content LLM call failed: {e}")
        return _enrich_fallback(mechanic_type, scene_number, zone_labels_in_scene, existing_config)


def _build_mechanic_enrichment_prompt(
    mechanic_type: str,
    existing_config: Dict[str, Any],
    zone_labels: List[str],
    label_descriptions: Dict[str, str],
) -> str:
    """Build mechanic-specific prompt section for enrichment."""

    base_schema = """\
Generate enriched content as JSON:
{{
    "scoring_rationale": "Why this scoring approach fits this mechanic and content",
    "recommended_scoring": {{
        "strategy": "{strategy}",
        "points_per_correct": {ppc},
        "max_score": {max_score},
        "partial_credit": {partial},
        "hint_penalty": {hint_pen}
    }},
    "enriched_feedback": {{
        "on_correct": "Subject-specific correct message",
        "on_incorrect": "Helpful incorrect message guiding learning",
        "on_completion": "Encouraging completion message summarizing what was learned"
    }},
    "misconception_triggers": [
        {{"trigger_label": "...", "trigger_zone": "...", "message": "Pedagogical explanation (2-3 sentences)"}}
    ],
    "content_enrichments": {enrichments}
}}"""

    num_labels = len(zone_labels)

    if mechanic_type == "drag_drop":
        return base_schema.format(
            strategy="standard",
            ppc=10,
            max_score=num_labels * 10,
            partial="true",
            hint_pen=0.1,
            enrichments="""{
        "per_zone_feedback": {"zone_label": "Why this label belongs here (1 sentence)"},
        "hint_progression": ["vague hint", "moderate hint", "strong hint"]
    }""",
        ) + f"""

For drag_drop enrichment:
- per_zone_feedback: For each zone label ({', '.join(zone_labels[:8])}), write a 1-sentence explanation
  of why that label belongs in that location on the diagram.
- hint_progression: 3 hints from vague to specific for when students struggle.
- Misconception triggers: Common confusions between similar-looking structures."""

    elif mechanic_type == "click_to_identify":
        prompts = existing_config.get("prompts", [])
        prompts_str = json.dumps(prompts[:5]) if prompts else "[]"
        return base_schema.format(
            strategy="standard",
            ppc=10,
            max_score=num_labels * 10,
            partial="true",
            hint_pen=0.15,
            enrichments="""{
        "per_prompt_feedback": [{"zone_label": "...", "correct_feedback": "Why this is the right structure", "wrong_click_feedback": "What was actually clicked and how it differs"}],
        "exploration_hints": ["hint after first wrong click", "hint after second wrong click"]
    }""",
        ) + f"""

For click_to_identify enrichment:
- Existing prompts from scene architect: {prompts_str}
- per_prompt_feedback: For each identification prompt, write correct_feedback explaining WHY
  the structure matches, and wrong_click_feedback explaining the difference when a wrong zone is clicked.
- exploration_hints: Progressive hints to help students who keep clicking wrong zones.
- Misconceptions: Students confusing visually similar structures."""

    elif mechanic_type == "trace_path":
        waypoints = existing_config.get("waypoints", [])
        waypoints_str = json.dumps(waypoints[:10]) if waypoints else "[]"
        return base_schema.format(
            strategy="progressive",
            ppc=15,
            max_score=max(len(waypoints), num_labels) * 15,
            partial="true",
            hint_pen=0.1,
            enrichments="""{
        "per_step_feedback": [{"from": "step_label", "to": "next_step_label", "explanation": "Why flow goes here"}],
        "path_summary": "Complete explanation of the flow from start to end",
        "wrong_step_feedback": {"wrong_label": "Why this is not the next step"}
    }""",
        ) + f"""

For trace_path enrichment:
- Existing waypoints (ordered path): {waypoints_str}
- per_step_feedback: For each transition between consecutive waypoints, explain WHY the flow
  goes from one structure to the next (biological/physical/chemical reason).
- path_summary: A 2-3 sentence summary of the complete pathway.
- wrong_step_feedback: For likely wrong next-steps, explain why they're incorrect.
- Misconceptions: Common errors in understanding the flow order."""

    elif mechanic_type == "sequencing":
        items = existing_config.get("items", [])
        correct_order = existing_config.get("correct_order", [])
        items_str = json.dumps(items[:8]) if items else "[]"
        return base_schema.format(
            strategy="progressive",
            ppc=15,
            max_score=max(len(items), num_labels) * 15,
            partial="true",
            hint_pen=0.1,
            enrichments="""{
        "per_item_feedback": [{"item_id": "...", "position_rationale": "Why this comes at position N"}],
        "sequence_explanation": "Full explanation of the correct order and logic",
        "common_misordering": [{"swapped": ["item_a", "item_b"], "explanation": "Why students confuse these"}]
    }""",
        ) + f"""

For sequencing enrichment:
- Existing items: {items_str}
- Correct order: {json.dumps(correct_order[:10]) if correct_order else '[]'}
- per_item_feedback: For each item, explain WHY it comes at its position in the sequence.
- sequence_explanation: Complete explanation of the ordering logic.
- common_misordering: 2-3 pairs of items that are commonly swapped, with explanation.
- Use progressive scoring: earlier items easier, later items worth more."""

    elif mechanic_type == "sorting_categories":
        categories = existing_config.get("categories", [])
        items = existing_config.get("items", [])
        cats_str = json.dumps(categories[:5]) if categories else "[]"
        items_str = json.dumps(items[:8]) if items else "[]"
        return base_schema.format(
            strategy="standard",
            ppc=10,
            max_score=max(len(items), num_labels) * 10,
            partial="true",
            hint_pen=0.1,
            enrichments="""{
        "per_category_feedback": [{"category_id": "...", "category_name": "...", "description": "What belongs here and why"}],
        "per_item_feedback": [{"item_id": "...", "correct_category": "...", "rationale": "Why this belongs in this category"}],
        "cross_category_confusions": [{"item": "...", "wrong_category": "...", "explanation": "Why students put it here"}]
    }""",
        ) + f"""

For sorting_categories enrichment:
- Existing categories: {cats_str}
- Existing items: {items_str}
- per_category_feedback: Describe each category and what defines membership in it.
- per_item_feedback: For each item, explain WHY it belongs in its correct category.
- cross_category_confusions: Items that look like they belong in a different category.
- Scoring: Equal points per correctly sorted item."""

    elif mechanic_type == "description_matching":
        descriptions = existing_config.get("descriptions", [])
        desc_str = json.dumps(descriptions[:6]) if descriptions else "[]"
        return base_schema.format(
            strategy="standard",
            ppc=10,
            max_score=num_labels * 10,
            partial="true",
            hint_pen=0.15,
            enrichments="""{
        "per_match_feedback": [{"zone_label": "...", "description": "...", "match_rationale": "Why this description fits this structure"}],
        "distractor_analysis": [{"description": "distractor text", "why_wrong": "Why no zone matches this"}]
    }""",
        ) + f"""

For description_matching enrichment:
- Existing descriptions: {desc_str}
- per_match_feedback: For each zone-description pair, explain the connection between the
  functional description and the visual/structural features of the zone.
- distractor_analysis: For any distractor descriptions, explain why they don't match any zone.
- Misconceptions: Descriptions that could plausibly match multiple zones."""

    elif mechanic_type == "memory_match":
        pairs = existing_config.get("pairs", [])
        pairs_str = json.dumps(pairs[:6]) if pairs else "[]"
        return base_schema.format(
            strategy="time_based",
            ppc=10,
            max_score=max(len(pairs), num_labels) * 10,
            partial="false",
            hint_pen=0.0,
            enrichments="""{
        "per_pair_feedback": [{"pair_id": "...", "term": "...", "match_explanation": "Why this term matches its definition"}],
        "difficulty_ordering": ["easy_pair_id", "medium_pair_id", "hard_pair_id"],
        "memory_tips": ["Mnemonic or association tip for remembering pairs"]
    }""",
        ) + f"""

For memory_match enrichment:
- Existing pairs: {pairs_str}
- per_pair_feedback: For each term-definition pair, write a short explanation shown when
  the pair is successfully matched (educational reinforcement).
- difficulty_ordering: Order pair IDs from easiest to hardest to remember.
- memory_tips: 2-3 mnemonic tips or associations to help students remember the pairs.
- Use time-based scoring: bonus points for faster completion, no penalty for wrong flips."""

    elif mechanic_type == "branching_scenario":
        nodes = existing_config.get("nodes", [])
        nodes_str = json.dumps(nodes[:4]) if nodes else "[]"
        return base_schema.format(
            strategy="mastery",
            ppc=20,
            max_score=max(len(nodes), 4) * 20,
            partial="true",
            hint_pen=0.0,
            enrichments="""{
        "per_node_feedback": [{"node_id": "...", "correct_choice_rationale": "Why correct choice leads to best outcome", "wrong_choice_consequence": "What happens with wrong choices"}],
        "optimal_path_explanation": "Description of the ideal decision path and its educational value",
        "decision_principles": ["Key principle students should apply at decision points"]
    }""",
        ) + f"""

For branching_scenario enrichment:
- Existing decision nodes: {nodes_str}
- per_node_feedback: For each node, explain the correct choice rationale and consequences of wrong choices.
- optimal_path_explanation: Describe the best path through the scenario and what it teaches.
- decision_principles: 2-3 principles students should use when making decisions in this scenario.
- Use mastery scoring: points for reaching optimal outcomes, partial credit for sub-optimal paths."""

    elif mechanic_type == "compare_contrast":
        expected = existing_config.get("expected_categories", {})
        expected_str = json.dumps(expected)[:400] if expected else "{}"
        return base_schema.format(
            strategy="mastery",
            ppc=15,
            max_score=max(len(expected) if isinstance(expected, (list, dict)) else 4, 4) * 15,
            partial="true",
            hint_pen=0.1,
            enrichments="""{
        "per_category_feedback": [{"category": "...", "subject_a_value": "...", "subject_b_value": "...", "comparison_insight": "Why this difference/similarity matters"}],
        "summary_comparison": "Overall comparison summary highlighting key differences and similarities",
        "common_confusions": [{"category": "...", "confusion": "What students commonly get wrong"}]
    }""",
        ) + f"""

For compare_contrast enrichment:
- Existing comparison data: {expected_str}
- per_category_feedback: For each comparison category, explain WHY the difference or similarity
  matters (biological/functional significance).
- summary_comparison: 2-3 sentence overview of the key comparison insights.
- common_confusions: Categories where students commonly confuse the two subjects.
- Use mastery scoring: points for correct categorizations."""

    else:
        # Generic fallback for unknown mechanic types
        return base_schema.format(
            strategy="standard",
            ppc=10,
            max_score=num_labels * 10,
            partial="true",
            hint_pen=0.1,
            enrichments="{}",
        ) + f"""

For {mechanic_type}: Generate appropriate scoring and feedback.
- Misconceptions: Common student errors for this type of interaction."""


def _enrich_fallback(
    mechanic_type: str,
    scene_number: int,
    zone_labels: List[str],
    existing_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic fallback when LLM enrichment fails."""
    # Strategy mapping
    strategy_map = {
        "drag_drop": "standard",
        "click_to_identify": "standard",
        "trace_path": "progressive",
        "sequencing": "progressive",
        "sorting_categories": "standard",
        "description_matching": "standard",
        "memory_match": "time_based",
        "branching_scenario": "mastery",
        "compare_contrast": "mastery",
    }
    strategy = strategy_map.get(mechanic_type, "standard")

    # Points mapping
    ppc_map = {
        "trace_path": 15, "sequencing": 15, "branching_scenario": 20,
        "compare_contrast": 15,
    }
    ppc = ppc_map.get(mechanic_type, 10)
    num_items = len(zone_labels) or 10
    max_score = num_items * ppc

    return {
        "mechanic_type": mechanic_type,
        "scene_number": scene_number,
        "enriched": False,
        "recommended_scoring": {
            "strategy": strategy,
            "points_per_correct": ppc,
            "max_score": max_score,
            "partial_credit": mechanic_type != "memory_match",
            "hint_penalty": 0.0 if mechanic_type in ("memory_match", "branching_scenario") else 0.1,
        },
        "enriched_feedback": {
            "on_correct": "Correct! Well done.",
            "on_incorrect": "Not quite. Try again.",
            "on_completion": "Great work completing this section!",
        },
        "misconception_triggers": [],
        "content_enrichments": {},
        "error": "LLM unavailable, using deterministic fallback",
    }


# ---------------------------------------------------------------------------
# Tool 3: validate_interactions (deterministic)
# ---------------------------------------------------------------------------

async def validate_interactions_impl(
    interaction_spec: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate a single interaction spec against the InteractionSpecV3 schema.

    Cross-checks against scene_specs_v3 and game_design_v3 from pipeline context.
    """
    from app.agents.schemas.interaction_spec_v3 import InteractionSpecV3
    from app.tools.v3_context import get_v3_tool_context

    ctx = get_v3_tool_context()
    scene_specs = ctx.get("scene_specs_v3") or []
    game_design = ctx.get("game_design_v3") or {}

    errors = []
    warnings = []

    # Pydantic validation
    try:
        parsed = InteractionSpecV3.model_validate(interaction_spec)
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

    sn = parsed.scene_number

    # Check scoring exists for each mechanic
    if not parsed.scoring:
        errors.append(f"Scene {sn}: no scoring defined")
    if not parsed.feedback:
        errors.append(f"Scene {sn}: no feedback defined")

    # Check misconception count
    total_misconceptions = sum(len(f.misconception_feedback) for f in parsed.feedback)
    if total_misconceptions < 2:
        warnings.append(f"Scene {sn}: only {total_misconceptions} misconception feedbacks (recommend >= 2)")

    # Cross-check vs scene_specs_v3
    scene_spec = None
    for ss in scene_specs:
        if isinstance(ss, dict) and ss.get("scene_number") == sn:
            scene_spec = ss
            break

    if scene_spec:
        spec_mechs = set()
        for mc in scene_spec.get("mechanic_configs", []):
            if isinstance(mc, dict):
                spec_mechs.add(mc.get("type", ""))

        scored_mechs = {s.mechanic_type for s in parsed.scoring}
        missing_scoring = spec_mechs - scored_mechs
        if missing_scoring:
            errors.append(f"Scene {sn}: missing scoring for mechanics: {missing_scoring}")

        feedback_mechs = {f.mechanic_type for f in parsed.feedback}
        missing_feedback = spec_mechs - feedback_mechs
        if missing_feedback:
            errors.append(f"Scene {sn}: missing feedback for mechanics: {missing_feedback}")

        # Multi-mechanic scenes need mode transitions
        if len(spec_mechs) > 1 and not parsed.mode_transitions:
            warnings.append(f"Scene {sn}: multi-mechanic scene should have mode_transitions")

    # Cross-check vs game_design_v3
    if game_design:
        design_distractors = []
        labels = game_design.get("labels", {})
        if isinstance(labels, dict):
            for dl in labels.get("distractor_labels", []):
                if isinstance(dl, dict):
                    design_distractors.append(dl.get("text", ""))
                elif isinstance(dl, str):
                    design_distractors.append(dl)

        if design_distractors and not parsed.distractor_feedback:
            warnings.append(f"Scene {sn}: no distractor_feedback, but design has distractors")

    # Content checks: verify scoring configs are reasonable
    for sc in parsed.scoring:
        if sc.points_per_correct <= 0:
            warnings.append(f"Scene {sn}: {sc.mechanic_type} scoring has points_per_correct <= 0")
        if sc.max_score <= 0:
            warnings.append(f"Scene {sn}: {sc.mechanic_type} scoring has max_score <= 0")
        if sc.max_score < sc.points_per_correct:
            warnings.append(f"Scene {sn}: {sc.mechanic_type} max_score < points_per_correct")

    # Feedback content checks
    for fb in parsed.feedback:
        if fb.on_correct and len(fb.on_correct) < 5:
            warnings.append(f"Scene {sn}: {fb.mechanic_type} on_correct feedback too short")
        if fb.on_incorrect and len(fb.on_incorrect) < 5:
            warnings.append(f"Scene {sn}: {fb.mechanic_type} on_incorrect feedback too short")
        # Check for generic placeholders
        generic = {"correct", "incorrect", "try again", "well done"}
        if fb.on_correct and fb.on_correct.lower().strip("!. ") in generic:
            warnings.append(f"Scene {sn}: {fb.mechanic_type} on_correct is generic, make it subject-specific")

    # Auto-enrich: if scoring or feedback entries have generic/placeholder content,
    # call enrich_mechanic_content to populate richer pedagogical feedback.
    # This ensures the interaction specs are useful even when the LLM skips
    # the enrich_mechanic_content tool call.
    enriched_spec = None
    enriched_mechanics = []

    spec_dict = parsed.model_dump()

    # Identify mechanics that need enrichment
    all_scored_types = {s.mechanic_type for s in parsed.scoring}
    all_feedback_types = {f.mechanic_type for f in parsed.feedback}

    # Check for generic feedback that should be enriched
    generic_phrases = {"correct", "incorrect", "try again", "well done", "good job",
                       "that's right", "not quite", "keep trying"}
    needs_enrichment = set()
    for fb in parsed.feedback:
        if fb.on_correct and fb.on_correct.lower().strip("!. ") in generic_phrases:
            needs_enrichment.add(fb.mechanic_type)
        if not fb.misconception_feedback:
            needs_enrichment.add(fb.mechanic_type)

    # Also enrich mechanics with missing scoring or feedback
    if scene_spec:
        spec_mechs = set()
        for mc in scene_spec.get("mechanic_configs", []):
            if isinstance(mc, dict):
                spec_mechs.add(mc.get("type", ""))
        needs_enrichment |= (spec_mechs - all_scored_types)
        needs_enrichment |= (spec_mechs - all_feedback_types)

    for mtype in needs_enrichment:
        try:
            enriched = await enrich_mechanic_content_impl(
                mechanic_type=mtype,
                scene_number=sn,
            )
            if enriched.get("enriched") and isinstance(enriched, dict):
                # Merge enriched feedback into spec
                enriched_feedback = enriched.get("enriched_feedback") or enriched.get("feedback") or {}
                misconceptions = enriched.get("misconception_triggers") or []
                scoring_rationale = enriched.get("scoring_rationale", "")

                # Update feedback entries
                for i, fb_dict in enumerate(spec_dict.get("feedback", [])):
                    if fb_dict.get("mechanic_type") == mtype:
                        if enriched_feedback:
                            if isinstance(enriched_feedback, dict):
                                for key in ("on_correct", "on_incorrect", "on_completion"):
                                    if enriched_feedback.get(key) and len(enriched_feedback[key]) > len(fb_dict.get(key, "")):
                                        spec_dict["feedback"][i][key] = enriched_feedback[key]
                            # Add misconceptions
                            if misconceptions and not fb_dict.get("misconception_feedback"):
                                spec_dict["feedback"][i]["misconception_feedback"] = misconceptions[:3]

                # Add scoring for missing mechanics
                if mtype not in all_scored_types:
                    rec_scoring = enriched.get("recommended_scoring") or {}
                    if rec_scoring:
                        spec_dict.setdefault("scoring", []).append({
                            "mechanic_type": mtype,
                            "strategy": rec_scoring.get("strategy", "standard"),
                            "points_per_correct": rec_scoring.get("points_per_correct", 10),
                            "max_score": rec_scoring.get("max_score", 50),
                            "partial_credit": rec_scoring.get("partial_credit", True),
                            "hint_penalty": rec_scoring.get("hint_penalty", 0.2),
                        })

                enriched_mechanics.append(mtype)
                warnings.append(
                    f"Scene {sn}: auto-enriched feedback for '{mtype}'"
                )
        except Exception as e:
            warnings.append(
                f"Scene {sn}: failed to auto-enrich '{mtype}': {str(e)[:100]}"
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
# Tool 4: submit_interaction_specs (Pydantic schema-as-tool)
# ---------------------------------------------------------------------------

async def submit_interaction_specs_impl(
    interaction_specs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Submit all interaction specs for downstream processing.

    Validates each spec via InteractionSpecV3, then cross-checks the full set
    against scene_specs_v3 and game_design_v3 via validate_interaction_specs().
    """
    from app.agents.schemas.interaction_spec_v3 import (
        InteractionSpecV3,
        validate_interaction_specs,
    )
    from app.tools.v3_context import get_v3_tool_context

    ctx = get_v3_tool_context()
    scene_specs = ctx.get("scene_specs_v3") or []
    game_design = ctx.get("game_design_v3") or {}

    # Individual parse validation
    parse_errors = []
    parsed_specs = []
    for i, spec_dict in enumerate(interaction_specs):
        try:
            parsed = InteractionSpecV3.model_validate(spec_dict)
            parsed_specs.append(parsed)
        except Exception as e:
            parse_errors.append(f"Interaction spec [{i}]: {str(e)[:300]}")

    if parse_errors:
        return {
            "status": "rejected",
            "errors": parse_errors[:5],
            "hint": "Fix schema errors in individual interaction specs and resubmit.",
        }

    # Cross-stage validation
    spec_dicts = [p.model_dump() for p in parsed_specs]
    # Ensure scene_specs is list of dicts
    ss_dicts = []
    for ss in scene_specs:
        if isinstance(ss, dict):
            ss_dicts.append(ss)

    validation = validate_interaction_specs(spec_dicts, ss_dicts, game_design)

    if not validation.get("passed", False):
        return {
            "status": "rejected",
            "errors": validation.get("issues", []),
            "hint": "Fix cross-stage issues (scoring coverage, feedback coverage, misconception count) and resubmit.",
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

def register_interaction_designer_tools() -> None:
    """Register all interaction designer v3 tools in the tool registry."""
    from app.tools.registry import register_tool

    register_tool(
        name="get_scoring_templates",
        description=(
            "Get scoring templates for a mechanic type at a given difficulty level. "
            "Returns recommended scoring strategy, points_per_correct, max_score, "
            "and all available strategies with formulas. Deterministic."
        ),
        parameters={
            "type": "object",
            "properties": {
                "mechanic_type": {
                    "type": "string",
                    "description": "The mechanic type (e.g., 'drag_drop', 'trace_path')",
                },
                "difficulty_level": {
                    "type": "string",
                    "description": "Difficulty level",
                    "enum": ["easy", "medium", "hard", "advanced"],
                },
            },
            "required": ["mechanic_type"],
        },
        function=get_scoring_templates_impl,
    )

    register_tool(
        name="generate_misconception_feedback",
        description=(
            "Generate targeted misconception feedback for zone labels and distractors. "
            "Uses LLM + domain knowledge to produce per-label misconception triggers "
            "with pedagogical messages. Returns misconception_feedback and distractor_feedback arrays."
        ),
        parameters={
            "type": "object",
            "properties": {
                "zone_labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Correct zone labels",
                },
                "distractor_labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Distractor (wrong) labels",
                },
                "subject": {
                    "type": "string",
                    "description": "Subject area for better misconception generation",
                },
                "mechanic_type": {
                    "type": "string",
                    "description": "Mechanic type for tailored misconceptions (drag_drop, sequencing, sorting_categories, etc.)",
                },
            },
            "required": ["zone_labels"],
        },
        function=generate_misconception_feedback_impl,
    )

    register_tool(
        name="enrich_mechanic_content",
        description=(
            "Enrich a mechanic's interaction design with pedagogically rich content. "
            "Uses LLM + domain knowledge to generate tailored scoring rationale, "
            "feedback messages, and misconception triggers for a specific mechanic type. "
            "Call this for each mechanic to get high-quality, content-specific interactions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "mechanic_type": {
                    "type": "string",
                    "description": "The mechanic type to enrich (e.g., 'drag_drop', 'trace_path')",
                },
                "scene_number": {
                    "type": "integer",
                    "description": "Scene number (1-based) to enrich content for",
                },
            },
            "required": ["mechanic_type"],
        },
        function=enrich_mechanic_content_impl,
    )

    register_tool(
        name="validate_interactions",
        description=(
            "Validate a single interaction spec against the InteractionSpecV3 schema. "
            "Cross-checks against scene_specs_v3 for mechanic coverage and "
            "game_design_v3 for distractor coverage. Returns errors, warnings, and score."
        ),
        parameters={
            "type": "object",
            "properties": {
                "interaction_spec": {
                    "type": "object",
                    "description": "A single interaction spec to validate",
                },
            },
            "required": ["interaction_spec"],
        },
        function=validate_interactions_impl,
    )

    register_tool(
        name="submit_interaction_specs",
        description=(
            "Submit ALL interaction specs for downstream processing. "
            "Pass a list of complete interaction spec objects, one per scene. "
            "Each is validated against InteractionSpecV3, then cross-checked "
            "against scene_specs_v3 and game_design_v3. "
            "Returns {status: 'accepted'} on success or {status: 'rejected', errors} on failure."
        ),
        parameters={
            "type": "object",
            "properties": {
                "interaction_specs": {
                    "type": "array",
                    "description": "List of interaction spec objects, one per scene",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scene_number": {"type": "integer", "description": "Scene number (1-based)"},
                            "scoring": {
                                "type": "array",
                                "description": "Scoring configs per mechanic: [{mechanic_type, strategy, points_per_correct, max_score, partial_credit, hint_penalty}]",
                                "items": {"type": "object"},
                            },
                            "feedback": {
                                "type": "array",
                                "description": "Feedback configs per mechanic: [{mechanic_type, on_correct, on_incorrect, on_completion, misconception_feedback}]",
                                "items": {"type": "object"},
                            },
                            "distractor_feedback": {
                                "type": "array",
                                "description": "Feedback for distractor labels: [{distractor, feedback}]",
                                "items": {"type": "object"},
                            },
                            "mode_transitions": {
                                "type": "array",
                                "description": "Intra-scene mechanic transitions: [{from_mechanic, to_mechanic, trigger, animation, message}]",
                                "items": {"type": "object"},
                            },
                            "scene_completion": {
                                "type": "object",
                                "description": "Completion criteria: {trigger, show_results, min_score_to_pass}",
                            },
                            "animations": {
                                "type": "object",
                                "description": "Animation specs: {on_correct: {...}, on_incorrect: {...}, on_completion: {...}}",
                            },
                            "transition_to_next": {
                                "type": "object",
                                "description": "Inter-scene transition: {trigger, animation, message}",
                            },
                        },
                        "required": ["scene_number", "scoring", "feedback"],
                    },
                },
            },
            "required": ["interaction_specs"],
        },
        function=submit_interaction_specs_impl,
    )

    logger.info("Registered 5 interaction designer v3 tools")
