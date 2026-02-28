# V3 Pipeline Stage Audit -- Per-Stage Inputs, Outputs, Data Shapes, and Gaps

**Date**: 2026-02-14
**Method**: Direct source code reading of all 11 V3 pipeline agents, schemas, tools, graph wiring, and state definitions.
**Scope**: The `create_v3_graph()` pipeline (12 nodes, 5 phases + context gathering).

---

## Table of Contents

1. [Graph Wiring Overview](#1-graph-wiring-overview)
2. [Stage 1: input_enhancer](#2-stage-1-input_enhancer)
3. [Stage 2: domain_knowledge_retriever](#3-stage-2-domain_knowledge_retriever)
4. [Stage 3: router](#4-stage-3-router)
5. [Stage 4: game_designer_v3](#5-stage-4-game_designer_v3)
6. [Stage 5: design_validator](#6-stage-5-design_validator)
7. [Stage 6: scene_architect_v3](#7-stage-6-scene_architect_v3)
8. [Stage 7: scene_validator](#8-stage-7-scene_validator)
9. [Stage 8: interaction_designer_v3](#9-stage-8-interaction_designer_v3)
10. [Stage 9: interaction_validator](#10-stage-9-interaction_validator)
11. [Stage 10: asset_generator_v3](#11-stage-10-asset_generator_v3)
12. [Stage 11: blueprint_assembler_v3](#12-stage-11-blueprint_assembler_v3)
13. [Cross-Stage Data Flow Summary](#13-cross-stage-data-flow-summary)
14. [Critical Gaps and Issues](#14-critical-gaps-and-issues)

---

## 1. Graph Wiring Overview

**Source**: `backend/app/agents/graph.py`, lines 1901-2016 (`create_v3_graph()`)

```
Entry Point
    |
    v
input_enhancer --> domain_knowledge_retriever --> router --> game_designer_v3
                                                                |
                                                                v
                                                         design_validator
                                                                |
                                              (retry up to 3 or pass)
                                                                |
                                                                v
                                                        scene_architect_v3
                                                                |
                                                                v
                                                          scene_validator
                                                                |
                                              (retry up to 3 or pass)
                                                                |
                                                                v
                                                    interaction_designer_v3
                                                                |
                                                                v
                                                    interaction_validator
                                                                |
                                              (retry up to 3 or pass)
                                                                |
                                                                v
                                                       asset_generator_v3
                                                                |
                                                                v
                                                   blueprint_assembler_v3
                                                                |
                                                                v
                                                               END
```

**Retry Routing Logic** (all in `graph.py`, lines 1862-1898):
- `_v3_design_validation_router`: If `design_validation_v3.passed` is True, go to `scene_architect_v3`. Else retry (max 3). After 3 retries, proceed anyway.
- `_v3_scene_validation_router`: If `scene_validation_v3.passed` is True, go to `interaction_designer_v3`. Else retry (max 3). After 3 retries, proceed anyway.
- `_v3_interaction_validation_router`: If `interaction_validation_v3.passed` is True, go to `asset_generator_v3`. Else retry (max 3). After 3 retries, proceed anyway.

**Key Graph Detail**: The comment in `create_v3_graph()` says "max 2 retries" in the diagram (lines 1914, 1920, 1926), but the actual router code checks `retry >= 3` (lines 1868, 1881, 1894). This means the real limit is 3 retries (4 total attempts), not 2.

---

## 2. Stage 1: input_enhancer

**Source**: `backend/app/agents/input_enhancer.py`
**Type**: Single LLM call (not ReAct)
**Model**: `gemini-2.5-flash-lite` (from `agent_models.py` line ~706, gemini_only preset)
**Temperature**: 0.3

### State Fields READ

| Field | Type | Source |
|-------|------|--------|
| `question_text` | `str` | Initial input |
| `question_options` | `Optional[List[str]]` | Initial input |
| `current_validation_errors` | `Optional[List[str]]` | From previous validator (if retry) |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `pedagogical_context` | `PedagogicalContext` | See below |
| `current_agent` | `str` | `"input_enhancer"` |

### Actual Data Shape Produced

```python
pedagogical_context = {
    "blooms_level": str,            # "remember"|"understand"|"apply"|"analyze"|"evaluate"|"create"
    "blooms_justification": str,    # 1-2 sentence explanation
    "learning_objectives": [str],   # List of 2-4 learning objectives
    "key_concepts": [str],          # List of key concepts
    "difficulty": str,              # "beginner"|"intermediate"|"advanced"
    "difficulty_justification": str,
    "subject": str,                 # e.g. "Biology", "Chemistry"
    "cross_cutting_subjects": [str],
    "common_misconceptions": [{"misconception": str, "correction": str}],
    "prerequisites": [str],
    "question_intent": str,         # e.g. "Label parts of..."
}
```

### Gaps

- **No gap**: This stage is straightforward and produces all fields the downstream stages consume.
- Has a fallback heuristic `_create_fallback_context()` if LLM fails, which sets `blooms_level="understand"`, `difficulty="intermediate"`, and basic defaults.

---

## 3. Stage 2: domain_knowledge_retriever

**Source**: `backend/app/agents/domain_knowledge_retriever.py`
**Type**: Multi-step procedural (web search + multiple LLM calls, NOT ReAct)
**Model**: `gemini-2.5-flash-lite`
**Temperature**: 0.2

### State Fields READ

| Field | Type | Source |
|-------|------|--------|
| `question_id` | `str` | Initial input |
| `question_text` | `str` | Initial input |
| `pedagogical_context` | `PedagogicalContext` | From `input_enhancer` |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `domain_knowledge` | `DomainKnowledge` | See below |
| `canonical_labels` | `List[str]` | Promoted copy of `domain_knowledge.canonical_labels` |
| `current_agent` | `str` | `"domain_knowledge_retriever"` |
| `current_validation_errors` | `List[str]` | Cleared to `[]` |

### Actual Data Shape Produced

```python
domain_knowledge = {
    "query": str,                       # Original search query derived from question
    "canonical_labels": [str],          # e.g. ["Stigma", "Anther", "Petal", ...]
    "acceptable_variants": {str: [str]},# {"Stigma": ["stigma tip", ...], ...}
    "hierarchical_relationships": [     # Parent-child zone relationships
        {"parent": str, "children": [str], "relationship_type": str}
    ],
    "sources": [{"title": str, "url": str, "snippet": str}],
    "retrieved_at": str,                # ISO timestamp
    "sequence_flow_data": {             # Only populated if intent.needs_sequence
        "sequence_type": str,           # "linear"|"cyclic"|"branching"
        "ordered_steps": [str],         # Correct sequence order
        "step_descriptions": {str: str},# Step -> description
        "connections": [{"from": str, "to": str, "label": str}],
        "process_name": str,
    },
    "content_characteristics": {        # Always populated
        "has_hierarchy": bool,
        "has_sequences": bool,
        "has_comparisons": bool,
        "primary_structure": str,       # "hierarchical"|"sequential"|"comparative"|"flat"
    },
    "label_descriptions": {str: str},   # Only populated if intent.needs_descriptions
    "comparison_data": {                # Only populated if intent.needs_comparison
        "groups": [{"name": str, "members": [str], "key_traits": [str]}],
        "comparison_criteria": [str],
        "differences": [{...}],
    },
}
```

### Gaps

1. **`query_intent` field**: The `DomainKnowledge` TypedDict in `state.py` defines `query_intent: Optional[str]`, but the retriever's `_detect_query_intent()` returns a dict (not a string) and this value is NOT written to the state. The internal intent dict with `needs_labels`, `needs_sequence`, `needs_comparison`, `sequence_type` is used locally but lost.
2. **`suggested_reveal_order` field**: Defined in `DomainKnowledge` TypedDict but never populated by the retriever.
3. **`scene_hints` field**: Defined in `DomainKnowledge` TypedDict but never populated by the retriever.
4. **Conditional population**: `sequence_flow_data`, `label_descriptions`, and `comparison_data` are only populated based on keyword-based intent detection (`_detect_query_intent()`). If the intent detection misclassifies the question, these fields will be empty even when needed.
5. **`comparison_data` not in state TypedDict**: The `DomainKnowledge` TypedDict in `state.py` does NOT have a `comparison_data` field. It is only present in the Pydantic schema. The retriever writes it anyway (TypedDict is `total=False`), but it is not formally declared.

---

## 4. Stage 3: router

**Source**: `backend/app/agents/router.py`
**Type**: Single LLM call
**Model**: `gemini-2.5-flash-lite`
**Temperature**: 0.1

### State Fields READ

| Field | Type | Source |
|-------|------|--------|
| `question_text` | `str` | Initial input |
| `question_options` | `Optional[List[str]]` | Initial input |
| `pedagogical_context` | `PedagogicalContext` | From `input_enhancer` |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `template_selection` | `TemplateSelection` | `{template_type, confidence, reasoning, alternatives, scores}` |
| `routing_confidence` | `float` | 0.0-1.0 |
| `current_agent` | `str` | `"router"` |

### Actual Data Shape Produced

```python
template_selection = {
    "template_type": str,         # e.g. "INTERACTIVE_DIAGRAM"
    "confidence": float,
    "reasoning": str,
    "alternatives": [{"type": str, "confidence": float, "reasoning": str}],
    "bloom_alignment_score": float,
    "subject_fit_score": float,
    "interaction_fit_score": float,
    "is_production_ready": bool,
    "requires_code_generation": bool,
}
```

### Gaps

1. **OUTPUT IS UNUSED IN V3**: The V3 graph directly wires `router -> game_designer_v3` (line 1974). There are no conditional edges from the router. The `template_selection` output is not read by any downstream V3 agent. The router exists only because it was reused from the legacy pipeline.
2. **No domain_knowledge consumed**: Unlike the legacy pipeline where the router can use DK data, the V3 router does not read `domain_knowledge` or `canonical_labels`.

---

## 5. Stage 4: game_designer_v3

**Source**: `backend/app/agents/game_designer_v3.py`
**Type**: ReAct agent (max_iterations=6)
**Model**: `gemini-2.5-pro` (from `agent_models.py` line 720)
**Temperature**: 0.7

### State Fields READ

Read via `build_task_prompt()` and `set_v3_tool_context()`:

| Field | Type | Source | How Read |
|-------|------|--------|----------|
| `question_text` | `str` | Input | `state.get("enhanced_question") or state.get("question_text")` |
| `pedagogical_context` | `PedagogicalContext` | `input_enhancer` | `.get("subject")`, `.get("blooms_level")` |
| `domain_knowledge` | `DomainKnowledge` | `domain_knowledge_retriever` | `.get("canonical_labels")`, `.get("sequence_flow_data")`, `.get("label_descriptions")`, `.get("comparison_data")`, `.get("content_characteristics")` |
| `canonical_labels` | `List[str]` | `domain_knowledge_retriever` | Direct read |
| `design_validation_v3` | `Dict` | `design_validator` | Only on retry (`_v3_design_retries > 0`) |
| `_v3_design_retries` | `int` | `design_validator` | Retry counter check |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `game_design_v3` | `Dict[str, Any]` | GameDesignV3Slim dict + `_summary` |
| `current_agent` | `str` | `"game_designer_v3"` |

### Actual Data Shape Produced

The agent outputs `GameDesignV3Slim` (defined in `schemas/game_design_v3.py`, line 1079):

```python
game_design_v3 = {
    "_summary": str,                # 1-2 sentence summary appended by parse_final_result
    "title": str,                   # Game title
    "total_scenes": int,            # Number of scenes (1-4)
    "difficulty": str,              # "beginner"|"intermediate"|"advanced"
    "estimated_duration_minutes": int,
    "_subject": str,                # Subject area
    "labels": {
        "zone_labels": [str],       # Labels to place as interactive zones
        "distractor_labels": [str], # Wrong answers / distractors
        "hierarchy": {              # Optional parent-child grouping
            "parent_label": ["child_label_1", "child_label_2"]
        }
    },
    "scenes": [                     # Per-scene breakdown
        {
            "scene_number": int,
            "title": str,
            "learning_goal": str,
            "visual_description": str,    # What the scene image should look like
            "mechanics": [
                {
                    "type": str,          # MechanicType enum string
                    "config_hint": {},    # Free-form config hints (NOT validated)
                    "zone_labels_used": [str]
                }
            ],
            "zone_labels_in_scene": [str]
        }
    ]
}
```

### Tools Available (5)

| Tool | Source | Purpose |
|------|--------|---------|
| `analyze_pedagogy` | `game_design_tools.py` (V3 section) | Returns pedagogical context + DK summary from v3_context |
| `check_capabilities` | `game_design_tools.py` (V3 section) | Returns supported mechanic types + readiness levels |
| `get_example_designs` | `game_design_tools.py` (V3 section) | Returns example game designs for reference |
| `validate_design` | `game_design_tools.py` (V3 section) | Validates against `GameDesignV3Slim` Pydantic model |
| `submit_game_design` | `game_design_tools.py` (V3 section) | Terminal tool -- validates + returns structured output |

### Gaps

1. **Slim schema drops mechanic configs**: `GameDesignV3Slim.SlimMechanicRef` only has `type`, `config_hint` (Dict), and `zone_labels_used`. The full `GameDesignV3.MechanicDesign` has per-mechanic typed fields (`path_config`, `click_config`, `sequence_config`, etc.) with detailed Pydantic models. The Slim version defers all mechanic-specific configuration to later stages, but `config_hint` is untyped and unvalidated.
2. **`config_hint` is a black box**: There is no schema or validation for what goes inside `config_hint`. The LLM may or may not include useful hints. Scene architect must interpret these hints without contract guarantees.
3. **No scoring/feedback**: By design, Slim defers scoring and feedback to the interaction designer. This is intentional, not a gap.
4. **`_summary` is fragile**: `parse_final_result()` manually appends `_summary` by concatenating title + scene summaries. If the LLM fails to call `submit_game_design` and fallback JSON extraction is used, `_summary` may be incomplete.

---

## 6. Stage 5: design_validator

**Source**: `backend/app/agents/design_validator.py`
**Type**: Deterministic (NO LLM calls)
**Model**: None

### State Fields READ

| Field | Type | Source |
|-------|------|--------|
| `game_design_v3` | `Dict[str, Any]` | `game_designer_v3` |
| `_v3_design_retries` | `int` | Self (previous iteration) |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `design_validation_v3` | `Dict` | `{"passed": bool, "score": float, "issues": [str]}` |
| `_v3_design_retries` | `int` | Incremented by 1 |
| `current_agent` | `str` | `"design_validator"` |

### Validation Logic

1. Parses `game_design_v3` against the **FULL** `GameDesignV3` Pydantic model (not Slim) via `GameDesignV3.model_validate()`.
2. Checks:
   - Title exists and length > 3
   - At least 1 scene
   - Label integrity: zone_labels non-empty, no overlap with distractor_labels, min count thresholds
   - Per-scene: has mechanics, mechanics have valid types (from `MechanicType` enum)
   - Mechanic-specific: `trace_path` needs `path_config.waypoints`, `click_to_identify` needs `click_config`, `sequencing` needs `sequence_config.correct_order`, `sorting_categories` needs `sorting_config.categories`, etc.
   - Hierarchy consistency
   - Label coverage across scenes >= 50%
3. Score = 1.0 - deductions per check category
4. Pass threshold: `score >= 0.7` AND no `FATAL:` prefixed issues

### Gaps

1. **Schema coercion mismatch**: The validator parses against `GameDesignV3` (full schema) but the game designer outputs `GameDesignV3Slim`. The full `GameDesignV3` model has `model_validator` methods that attempt to coerce Slim data into full format. If coercion fails, the validator catches `ValidationError` and scores 0.0. This means the mechanic-specific config checks (lines 109-164 in the validator) will mostly NOT fire because the Slim schema does not include `path_config`, `click_config`, etc. -- they are coerced to defaults by the Pydantic model.
2. **Silent pass on missing configs**: Because the full schema's `model_validator` provides defaults for missing mechanic configs, the validator sees them as present (with empty defaults) rather than missing. This means "trace_path has no path_config" is never flagged.

---

## 7. Stage 6: scene_architect_v3

**Source**: `backend/app/agents/scene_architect_v3.py`
**Type**: ReAct agent (max_iterations=15)
**Model**: `gemini-2.5-pro` (from `agent_models.py` line 721)
**Temperature**: 0.5

### State Fields READ

Read via `build_task_prompt()` and `set_v3_tool_context()`:

| Field | Type | Source | How Read |
|-------|------|--------|----------|
| `game_design_v3` | `Dict` | `game_designer_v3` | `._summary`, `.title`, `.labels`, `.scenes` (iterates scenes for mechanics, visual_description, zone_labels_in_scene) |
| `canonical_labels` | `List[str]` | `domain_knowledge_retriever` | Direct |
| `domain_knowledge` | `DomainKnowledge` | `domain_knowledge_retriever` | `.label_descriptions`, `.sequence_flow_data`, `.comparison_data`, `.get("term_definitions")`, `.get("causal_relationships")`, `.get("spatial_data")`, `.get("process_steps")`, `.get("hierarchical_data")`, `.content_characteristics` |
| `scene_validation_v3` | `Dict` | `scene_validator` | Only on retry |
| `_v3_scene_retries` | `int` | `scene_validator` | Retry counter check |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `scene_specs_v3` | `List[Dict[str, Any]]` | List of `SceneSpecV3` dicts (see below) |
| `current_agent` | `str` | `"scene_architect_v3"` |

### Actual Data Shape Produced

Each element in `scene_specs_v3` follows `SceneSpecV3` (from `schemas/scene_spec_v3.py`):

```python
scene_spec = {
    "scene_number": int,
    "title": str,
    "image_description": str,          # Detailed prompt for image generation
    "image_requirements": {            # Constraints for image
        "style": str,
        "must_include": [str],
        "must_exclude": [str],
        "resolution": str,
    },
    "image_style": str,                # "realistic"|"diagram"|"illustration"|...
    "zones": [
        {
            "zone_id": str,            # e.g. "zone_stigma"
            "label": str,              # "Stigma"
            "position_hint": str,      # "top-center", "left-third"
            "description": str,        # What this zone represents
            "hint": str,               # Educational hint
            "difficulty": int,         # 1-3
        }
    ],
    "mechanic_configs": [
        {
            "type": str,              # MechanicType string
            "zone_labels_used": [str],
            "config": {},             # Generic mechanic config dict
            # Plus typed optional fields:
            "path_config": {...},     # PathDesignConfig if trace_path
            "click_config": {...},    # ClickDesignConfig if click_to_identify
            "sequence_config": {...}, # SequenceDesignConfig if sequencing
            "sorting_config": {...},  # SortingDesignConfig if sorting_categories
            "branching_config": {...},# BranchingDesignConfig
            "compare_config": {...},  # CompareDesignConfig
            "memory_config": {...},   # MemoryMatchDesignConfig
            "timed_config": {...},    # TimedDesignConfig
            "description_match_config": {...}, # DescriptionMatchDesignConfig
        }
    ],
    "mechanic_data": {},              # Additional mechanic-specific data (free-form)
    "zone_hierarchy": {},             # Parent-child zone relationships
}
```

### Tools Available (5)

| Tool | Source | Purpose |
|------|--------|---------|
| `get_zone_layout_guidance` | `game_design_tools.py` | Returns layout guidance for zone positioning |
| `get_mechanic_config_schema` | `game_design_tools.py` | Returns the Pydantic schema for a specific mechanic type |
| `generate_mechanic_content` | `game_design_tools.py` | Generates mechanic-specific content (sequence orders, sorting categories, etc.) using DK data from v3_context |
| `validate_scene_spec` | `game_design_tools.py` | Validates scene spec + enriches with cross-references |
| `submit_scene_specs` | `game_design_tools.py` | Terminal tool -- validates + returns structured output |

### Gaps

1. **`generate_mechanic_content` quality depends on DK data**: If `domain_knowledge.sequence_flow_data` or `comparison_data` is empty (because the DK retriever's intent detection missed it), this tool generates content from scratch using only label names and question text. The content will be lower quality.
2. **`mechanic_data` is untyped**: The `mechanic_data` field is a free-form dict. There is no schema enforcing its structure. The scene validator does not deeply validate its contents.
3. **parse_final_result strategy 3**: If the LLM never calls `submit_scene_specs`, the agent falls back to extracting specs from the last `validate_scene_spec` call's history. This is fragile and may produce incomplete specs (enriched_spec from validation may differ from what the LLM intended to submit).

---

## 8. Stage 7: scene_validator

**Source**: `backend/app/agents/scene_validator.py`
**Type**: Deterministic (NO LLM calls)
**Model**: None

### State Fields READ

| Field | Type | Source |
|-------|------|--------|
| `scene_specs_v3` | `List[Dict]` | `scene_architect_v3` |
| `game_design_v3` | `Dict` | `game_designer_v3` |
| `_v3_scene_retries` | `int` | Self (previous iteration) |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `scene_validation_v3` | `Dict` | `{"passed": bool, "score": float, "issues": [str]}` |
| `_v3_scene_retries` | `int` | Incremented by 1 |
| `current_agent` | `str` | `"scene_validator"` |

### Validation Logic

Delegates to `validate_scene_specs()` in `schemas/scene_spec_v3.py`. Cross-stage checks:
1. Labels in scene specs match labels in `game_design_v3`
2. Scene numbers match (scene count)
3. Mechanic types match per-scene (type from scene_spec must exist in game_design scene)
4. Every zone has a `position_hint`
5. Every zone has a `hint`
6. `image_description` non-empty per scene
7. Mechanic-specific data requirements (e.g., sequencing needs `correct_order`, sorting needs `categories`)

### Gaps

1. **Shallow mechanic validation**: The validator checks for the EXISTENCE of mechanic-specific config keys but does not deeply validate their contents (e.g., does not check that `correct_order` has the right number of items, or that `categories` have member items).
2. **No image_requirements validation**: The `image_requirements` dict is not validated for completeness (style, must_include, etc.).

---

## 9. Stage 8: interaction_designer_v3

**Source**: `backend/app/agents/interaction_designer_v3.py`
**Type**: ReAct agent (max_iterations=15)
**Model**: `gemini-2.5-pro` (from `agent_models.py` line 722)
**Temperature**: 0.5

### State Fields READ

Read via `build_task_prompt()` and `set_v3_tool_context()`:

| Field | Type | Source | How Read |
|-------|------|--------|----------|
| `game_design_v3` | `Dict` | `game_designer_v3` | `._summary`, `.labels`, `.get("difficulty")`, `.get("_subject")` |
| `scene_specs_v3` | `List[Dict]` | `scene_architect_v3` | Iterates scenes for `.zones`, `.mechanic_configs` |
| `domain_knowledge` | `DomainKnowledge` | `domain_knowledge_retriever` | `.label_descriptions`, `.sequence_flow_data`, `.comparison_data`, `.get("term_definitions")`, `.get("causal_relationships")` |
| `interaction_validation_v3` | `Dict` | `interaction_validator` | Only on retry |
| `_v3_interaction_retries` | `int` | `interaction_validator` | Retry counter check |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `interaction_specs_v3` | `List[Dict[str, Any]]` | List of `InteractionSpecV3` dicts (see below) |
| `current_agent` | `str` | `"interaction_designer_v3"` |

### Actual Data Shape Produced

Each element in `interaction_specs_v3` follows `InteractionSpecV3` (from `schemas/interaction_spec_v3.py`):

```python
interaction_spec = {
    "scene_number": int,
    "scoring": [                      # One per mechanic in the scene
        {
            "mechanic_type": str,     # MechanicType string
            "strategy": str,          # "per_item"|"all_or_nothing"|"progressive"
            "points_per_correct": int,
            "max_score": int,
            "partial_credit": bool,
            "hint_penalty": float,    # 0.0-1.0
        }
    ],
    "feedback": [                     # One per mechanic in the scene
        {
            "mechanic_type": str,
            "on_correct": str,        # Feedback message
            "on_incorrect": str,
            "on_completion": str,
            "misconception_feedback": [
                {
                    "misconception": str,
                    "trigger": str,     # What action triggers this
                    "feedback": str,    # Corrective feedback
                    "severity": str,    # "low"|"medium"|"high"
                }
            ]
        }
    ],
    "distractor_feedback": {          # Feedback for wrong answers
        "label_name": "feedback message"
    },
    "mode_transitions": [            # For multi-mechanic scenes
        {
            "from_mode": str,
            "to_mode": str,
            "trigger": str,          # "completion"|"score_threshold"|"time"
            "trigger_value": Any,    # Depends on trigger type
        }
    ],
    "scene_completion": {
        "required_score": float,     # 0.0-1.0 (percentage)
        "celebration": str,          # Message on scene completion
    },
    "animations": {},                # Animation specs (free-form)
    "transition_to_next": {          # How to transition to next scene
        "type": str,                 # "auto"|"button"|"score_gate"
        "delay_ms": int,
    },
}
```

### Tools Available (5)

| Tool | Source | Purpose |
|------|--------|---------|
| `get_scoring_templates` | `game_design_tools.py` | Returns per-mechanic scoring template defaults |
| `generate_misconception_feedback` | `game_design_tools.py` | Generates misconception-based feedback using DK data + pedagogical context |
| `enrich_mechanic_content` | `game_design_tools.py` | Enriches mechanic-specific content with detailed feedback, hints, difficulty tuning |
| `validate_interactions` | `game_design_tools.py` | Validates interaction spec against scene specs |
| `submit_interaction_specs` | `game_design_tools.py` | Terminal tool -- validates + returns structured output |

### Gaps

1. **`animations` field is always empty/minimal**: No tool generates animation specs. The LLM may or may not populate this field. The blueprint assembler does not read it.
2. **`mode_transitions` quality**: The LLM must correctly specify transition triggers and ordering for multi-mechanic scenes. There is no tool that auto-generates correct mode transitions based on the mechanic list.
3. **Misconception quality**: The `generate_misconception_feedback` tool generates misconceptions based on DK data. If DK data is sparse, misconceptions will be generic.

---

## 10. Stage 9: interaction_validator

**Source**: `backend/app/agents/interaction_validator.py` (V3 path, line 608+)
**Type**: Deterministic (NO LLM calls)
**Model**: None

### State Fields READ

| Field | Type | Source |
|-------|------|--------|
| `interaction_specs_v3` | `List[Dict]` | `interaction_designer_v3` |
| `scene_specs_v3` | `List[Dict]` | `scene_architect_v3` |
| `game_design_v3` | `Dict` | `game_designer_v3` |
| `_v3_interaction_retries` | `int` | Self (previous iteration) |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `interaction_validation_v3` | `Dict` | `{"passed": bool, "score": float, "issues": [str]}` |
| `_v3_interaction_retries` | `int` | Incremented by 1 |
| `current_agent` | `str` | `"interaction_validator"` |

### Validation Logic

Delegates to `validate_interaction_specs()` in `schemas/interaction_spec_v3.py`. Cross-stage checks:
1. Every mechanic in every scene has a matching `scoring` entry
2. Every mechanic in every scene has a matching `feedback` entry
3. At least 2 misconception_feedback items per scene
4. Multi-mechanic scenes have `mode_transitions`
5. Mode transition triggers are valid (`trigger_value` present for score_threshold)
6. Mechanic-specific content presence (e.g., sequencing feedback references sequence order)
7. Total `max_score` across all scenes is in range 50-500
8. Distractor feedback exists for distractor labels

### Gaps

1. **No deep scoring validation**: Does not verify that `points_per_correct * item_count == max_score` or similar arithmetic consistency.
2. **No trigger_value range check**: A `score_threshold` trigger_value of 0.0 or 1.0 would be accepted.
3. **Distractor feedback coverage**: Only checks existence, not that every distractor label has feedback.

---

## 11. Stage 10: asset_generator_v3

**Source**: `backend/app/agents/asset_generator_v3.py`
**Type**: ReAct agent (max_iterations=15, tool_timeout=120s)
**Model**: `gemini-2.5-flash` (from `agent_models.py` line 723)
**Temperature**: 0.3

### State Fields READ

Read via `build_task_prompt()` and `set_v3_tool_context()`:

| Field | Type | Source | How Read |
|-------|------|--------|----------|
| `scene_specs_v3` | `List[Dict]` | `scene_architect_v3` | Iterates for `image_description`, `image_requirements`, `zones`, `mechanic_configs` |
| `game_design_v3` | `Dict` | `game_designer_v3` | `.get("title")`, `.get("scenes")` |
| `question_text` | `str` | Input | `state.get("enhanced_question") or state.get("question_text")` |
| `pedagogical_context` | `PedagogicalContext` | `input_enhancer` | `.get("subject")` |
| `canonical_labels` | `List[str]` | `domain_knowledge_retriever` | Direct |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `generated_assets_v3` | `Dict[str, Any]` | See below |
| `diagram_image` | `Dict[str, Any]` | Backward compat -- copied from scene 1's image |
| `diagram_zones` | `List[Dict]` | Backward compat -- copied from scene 1's zones |
| `current_agent` | `str` | `"asset_generator_v3"` |

### Actual Data Shape Produced

```python
generated_assets_v3 = {
    "scenes": {
        "1": {                            # Scene number as string key
            "diagram_image_url": str,     # URL of diagram image
            "diagram_image_path": str,    # Local file path
            "zones": [                    # Detected zones from vision model
                {
                    "id": str,            # e.g. "zone_0"
                    "label": str,         # Matched label name
                    "shape": str,         # "polygon"|"circle"|"rect"
                    "coordinates": {...}, # Shape-specific coordinates
                    "confidence": float,  # Detection confidence
                }
            ],
            "zone_detection_method": str, # "gemini_vlm"|"sam3"|"manual"
        },
        "2": {...},                       # Scene 2 if multi-scene
    },
    "metadata": {
        "source": str,                    # "v3_asset_generator"
        "scene_count": int,
        "scenes_with_images": int,
        "total_zones": int,
    }
}
```

### Tools Available (5)

| Tool | Source | Purpose |
|------|--------|---------|
| `search_diagram_image` | (asset tools) | Web search for diagram images |
| `generate_diagram_image` | (asset tools) | AI image generation |
| `detect_zones` | (asset tools) | Vision model zone detection on an image |
| `generate_animation_css` | (asset tools) | CSS animation generation |
| `submit_assets` | (asset tools) | Terminal tool -- validates + returns structured output |

### Gaps

1. **100% mechanic-agnostic**: The asset generator only handles diagram images and zone detection. It does NOT generate mechanic-specific assets (e.g., sequence item images, memory card images, sorting category icons). The state fields `sequence_item_images`, `sorting_item_images`, `sorting_category_icons`, `memory_card_images` (defined in `state.py`) are NEVER populated.
2. **No zone-to-label matching quality check**: Zone detection assigns labels via name matching, but if the vision model returns zones with generic labels (e.g., "region_1"), the matching may fail silently.
3. **`diagram_crop_regions` never populated**: Defined in state but no agent writes to it.
4. **`_reconstruct_from_tool_results()` fallback**: If the LLM never calls `submit_assets`, the agent reconstructs from individual tool call history. This may produce incomplete zone lists if `detect_zones` was called multiple times with different results.
5. **Backward compat fields**: `diagram_image` and `diagram_zones` are only populated from scene 1. Multi-scene games lose scene 2+ backward compat data.

---

## 12. Stage 11: blueprint_assembler_v3

**Source**: `backend/app/agents/blueprint_assembler_v3.py` (deterministic path, line 658+) + `backend/app/tools/blueprint_assembler_tools.py`
**Type**: Deterministic (NO LLM calls)
**Model**: None (despite `agent_models.py` assigning `gemini-2.5-flash`, the deterministic path is used)

### State Fields READ

Read via `set_v3_tool_context()` -> `v3_context.py`:

| Field | Type | Source |
|-------|------|--------|
| `game_design_v3` | `Dict` | `game_designer_v3` |
| `scene_specs_v3` | `List[Dict]` | `scene_architect_v3` |
| `interaction_specs_v3` | `List[Dict]` | `interaction_designer_v3` |
| `generated_assets_v3` | `Dict` | `asset_generator_v3` |

### State Fields WRITTEN

| Field | Type | Actual Shape |
|-------|------|-------------|
| `blueprint` | `Dict[str, Any]` | `InteractiveDiagramBlueprint` dict (see below) |
| `template_type` | `str` | `"INTERACTIVE_DIAGRAM"` |
| `generation_complete` | `bool` | `True` |
| `current_agent` | `str` | `"blueprint_assembler_v3"` |

### Actual Data Shape Produced

The blueprint is assembled by `assemble_blueprint_impl()` in `blueprint_assembler_tools.py`:

```python
blueprint = {
    "title": str,
    "diagramImage": str,              # URL/path of the primary diagram image
    "totalScenes": int,
    "difficulty": str,
    "estimatedDuration": int,
    "zones": [                        # ALL zones across all scenes
        {
            "id": str,                # "zone_0", "zone_1", ...
            "label": str,
            "shape": str,             # "polygon"|"circle"|"rect"
            "points": [[x, y], ...],  # Flattened for frontend (polygon)
            "center": [x, y],         # Computed center
            "hint": str,
            "difficulty": int,
            "scene_number": int,
        }
    ],
    "labels": [                       # Labels for drag-drop
        {
            "id": str,               # "label_0", ...
            "text": str,             # Display text
            "zone_id": str,          # Matching zone ID
            "scene_number": int,
        }
    ],
    "distractorLabels": [str],       # Wrong answer labels
    "mechanics": [                   # Per-scene mechanic configs
        {
            "scene_number": int,
            "mechanic_type": str,
            "zone_labels": [str],
            # Plus per-mechanic config fields (see below)
        }
    ],
    "scenes": [                      # Per-scene metadata
        {
            "scene_number": int,
            "title": str,
            "diagram_image": str,    # Per-scene image URL/path
            "learning_goal": str,
            "zone_ids": [str],       # Zone IDs in this scene
            "label_ids": [str],      # Label IDs in this scene
            "mechanics": [str],      # Mechanic types in this scene
        }
    ],
    "scoring": {                     # Merged from interaction_specs
        "mechanic_type": {           # Keyed by mechanic type
            "strategy": str,
            "points_per_correct": int,
            "max_score": int,
            "partial_credit": bool,
            "hint_penalty": float,
        }
    },
    "feedback": {                    # Merged from interaction_specs
        "mechanic_type": {
            "on_correct": str,
            "on_incorrect": str,
            "on_completion": str,
            "misconception_feedback": [...],
        }
    },
    "modeTransitions": [...],        # From interaction_specs
    "sceneTransitions": [...],
    "hierarchy": {},                 # From game_design labels.hierarchy

    # Per-mechanic config fields at blueprint root:
    "tracePathConfig": {...},         # If trace_path mechanic exists
    "paths": [...],                   # Path waypoints for trace_path
    "clickToIdentifyConfig": {...},   # If click_to_identify exists
    "identificationPrompts": [...],
    "sequenceConfig": {...},          # If sequencing exists
    "sortingConfig": {...},           # If sorting_categories exists
    "memoryMatchConfig": {...},       # If memory_match exists
    "branchingConfig": {...},         # If branching_scenario exists
    "compareConfig": {...},           # If compare_contrast exists
    "descriptionMatchingConfig": {...}, # If description_matching exists
    "dragDropConfig": {...},          # If drag_drop exists

    "narrativeIntro": str,            # Generated intro text
    "completionMessage": str,
}
```

### Assembly Flow

1. `assemble_blueprint_impl()` reads all upstream data from v3_context
2. Builds zone lookup with fuzzy matching (`_build_zone_lookup`)
3. Iterates scenes: for each scene, builds zones from `generated_assets_v3` zones matched to `scene_specs_v3` zone specs
4. Iterates mechanics: for each mechanic config in scene_specs, builds the appropriate config section (trace_path -> paths + tracePathConfig, etc.)
5. Converts `interaction_specs_v3.scoring` (List) to dict keyed by mechanic_type
6. Converts `interaction_specs_v3.feedback` (List) to dict keyed by mechanic_type
7. Runs `validate_blueprint_impl()` to check for issues
8. Runs `repair_blueprint_impl()` to fix common issues (max 2 iterations)

### Gaps

1. **Zone matching is the weakest link**: The fuzzy zone lookup (`_build_zone_lookup`) matches by normalized label. If the asset generator's vision model returns zones with labels that don't match the scene spec zone labels (different wording, abbreviations, or generic names), zones will be unmatched. Unmatched zones get placeholder coordinates.
2. **Scoring/feedback list-to-dict conversion**: `interaction_specs_v3.scoring` is a List of `{mechanic_type, ...}` dicts. The assembler converts to `{mechanic_type: {...}}` dict. If multiple scenes have the same mechanic_type, only the LAST scene's scoring is kept (overwrites earlier).
3. **Per-mechanic configs at blueprint root are FLAT**: All mechanic configs are placed at the blueprint root level (e.g., `sequenceConfig`, `sortingConfig`). If multiple scenes use the same mechanic type, only one config is kept. This is a limitation for multi-scene games with repeated mechanics.
4. **`repair_blueprint_impl()` scope**: Repair only handles:
   - Missing zone IDs in labels
   - Missing `points` in zones (generates placeholder rectangle)
   - Missing `center` in zones (computes from points)
   - Empty `hint` in zones (generates generic hint)
   - Missing `memoryMatchConfig.grid_size` (auto-calculates)
   - Missing `branchingConfig.scenarios` structure
   - Missing `compareConfig.categories` structure
   It does NOT repair missing mechanic content (e.g., empty `correct_order` in sequenceConfig).
5. **No animation data**: The `animations` field from interaction_specs is not forwarded to the blueprint. CSS animations from `generate_animation_css` tool are also not integrated.

---

## 13. Cross-Stage Data Flow Summary

```
                    question_text, question_options
                              |
                    [input_enhancer]
                              |
                    pedagogical_context
                              |
                [domain_knowledge_retriever]
                              |
            domain_knowledge, canonical_labels
                              |
                         [router]
                              |
                    template_selection (UNUSED)
                              |
                    [game_designer_v3]
                              |
              game_design_v3 (GameDesignV3Slim)
                              |
                    [design_validator]        <-- retries up to 3x
                              |
              design_validation_v3 {passed, score, issues}
                              |
                   [scene_architect_v3]
                              |
     scene_specs_v3 (zones, mechanic_configs, image_description)
                              |
                    [scene_validator]          <-- retries up to 3x
                              |
              scene_validation_v3 {passed, score, issues}
                              |
                [interaction_designer_v3]
                              |
   interaction_specs_v3 (scoring, feedback, transitions)
                              |
                 [interaction_validator]       <-- retries up to 3x
                              |
          interaction_validation_v3 {passed, score, issues}
                              |
                  [asset_generator_v3]
                              |
    generated_assets_v3 (images, detected zones per scene)
                              |
                [blueprint_assembler_v3]
                              |
           blueprint (InteractiveDiagramBlueprint)
                    + template_type
                    + generation_complete
```

### Which Fields Each Stage Reads From Previous Stages

| Stage | Reads from input_enhancer | Reads from DK retriever | Reads from game_designer | Reads from scene_architect | Reads from interaction_designer | Reads from asset_generator |
|-------|--------------------------|------------------------|--------------------------|---------------------------|-------------------------------|--------------------------|
| domain_knowledge_retriever | pedagogical_context | - | - | - | - | - |
| router | pedagogical_context | - | - | - | - | - |
| game_designer_v3 | pedagogical_context (subject, blooms_level) | domain_knowledge, canonical_labels | - | - | - | - |
| design_validator | - | - | game_design_v3 | - | - | - |
| scene_architect_v3 | - | domain_knowledge, canonical_labels | game_design_v3 | - | - | - |
| scene_validator | - | - | game_design_v3 | scene_specs_v3 | - | - |
| interaction_designer_v3 | - | domain_knowledge | game_design_v3 | scene_specs_v3 | - | - |
| interaction_validator | - | - | game_design_v3 | scene_specs_v3 | interaction_specs_v3 | - |
| asset_generator_v3 | pedagogical_context (subject) | canonical_labels | game_design_v3 | scene_specs_v3 | - | - |
| blueprint_assembler_v3 | - | - | game_design_v3 | scene_specs_v3 | interaction_specs_v3 | generated_assets_v3 |

---

## 14. Critical Gaps and Issues

### Severity: HIGH

| # | Gap | Location | Impact |
|---|-----|----------|--------|
| H1 | **Router output unused** | `graph.py:1974` | Router stage wastes ~2-4s of LLM time. `template_selection` is never consumed. |
| H2 | **Design validator validates Slim against Full schema** | `design_validator.py:309` | Full schema's model_validator provides defaults for missing mechanic configs, masking the fact that game_designer_v3 never produces them. Mechanic-specific validation checks never fire. |
| H3 | **Scoring/feedback dict overwrite for repeated mechanics** | `blueprint_assembler_tools.py:654-662` | Multi-scene games with the same mechanic type in multiple scenes lose scoring/feedback from earlier scenes. |
| H4 | **Asset generator is 100% mechanic-agnostic** | `asset_generator_v3.py` | `sequence_item_images`, `sorting_item_images`, `sorting_category_icons`, `memory_card_images` state fields are NEVER populated. Mechanics that need visual items (memory cards, sorting items) get no images. |
| H5 | **Zone matching fragility** | `blueprint_assembler_tools.py:74-80` | Fuzzy label matching between vision-detected zones and scene spec zones fails silently on wording mismatches. Unmatched zones get placeholder coordinates that may be off-screen. |
| H6 | **Flat mechanic configs at blueprint root** | `blueprint_assembler_tools.py` | Only one config per mechanic type at blueprint root. Multi-scene games with repeated mechanic types lose per-scene config differentiation. |
| H7 | **`comparison_data` not in DomainKnowledge TypedDict** | `state.py:321-337` | The retriever writes it, downstream agents read it via DK dict, but the field is not formally declared in the TypedDict. Works in practice (total=False) but violates type safety. |

### Severity: MEDIUM

| # | Gap | Location | Impact |
|---|-----|----------|--------|
| M1 | **DK intent detection is keyword-based** | `domain_knowledge_retriever.py` | `_detect_query_intent()` uses keyword matching ("sequence", "order", "compare", etc.). Edge cases where the question needs sequence data but doesn't use these keywords will miss it. |
| M2 | **`suggested_reveal_order` and `scene_hints` never populated** | `domain_knowledge_retriever.py` | Defined in state TypedDict but never written. Downstream agents cannot use them. |
| M3 | **`config_hint` in GameDesignV3Slim is untyped** | `schemas/game_design_v3.py:1089` | Free-form dict with no validation. Scene architect must interpret hints without contract guarantees. |
| M4 | **Graph comment says "max 2 retries" but code allows 3** | `graph.py:1914` vs `graph.py:1868` | Minor documentation inconsistency. Actual behavior: 3 retries (4 total attempts). |
| M5 | **`animations` field dropped** | `interaction_designer_v3.py` -> `blueprint_assembler_tools.py` | Interaction specs may include animation data that the blueprint assembler ignores. |
| M6 | **parse_final_result fallback strategies are fragile** | All ReAct agents | Strategy 2 (JSON extraction) and Strategy 3 (tool history reconstruction) produce lower quality outputs than the primary Strategy 1 (submit tool call args). |
| M7 | **No deep arithmetic validation** | `interaction_validator.py` | Does not check `points_per_correct * item_count <= max_score` or similar arithmetic consistency. |

### Severity: LOW

| # | Gap | Location | Impact |
|---|-----|----------|--------|
| L1 | **`diagram_crop_regions` never populated** | `state.py` vs all agents | Dead state field. |
| L2 | **Backward compat fields only from scene 1** | `asset_generator_v3.py` | `diagram_image` and `diagram_zones` at state root only reflect scene 1. |
| L3 | **`query_intent` written as dict but TypedDict says string** | `domain_knowledge_retriever.py` vs `state.py:333` | Internal intent dict is not persisted to state at all. The field remains None. |
| L4 | **`_summary` generation is fragile** | `game_designer_v3.py` | Manual string concatenation for summary. If title or scenes are malformed, summary may be useless. |

---

## Model Assignment Summary

| Agent | Model | Temperature | Type |
|-------|-------|-------------|------|
| `input_enhancer` | gemini-2.5-flash-lite | 0.3 | Single LLM call |
| `domain_knowledge_retriever` | gemini-2.5-flash-lite | 0.2 | Multi-step procedural |
| `router` | gemini-2.5-flash-lite | 0.1 | Single LLM call |
| `game_designer_v3` | gemini-2.5-pro | 0.7 | ReAct (max 6 iterations) |
| `design_validator` | None | N/A | Deterministic |
| `scene_architect_v3` | gemini-2.5-pro | 0.5 | ReAct (max 15 iterations) |
| `scene_validator` | None | N/A | Deterministic |
| `interaction_designer_v3` | gemini-2.5-pro | 0.5 | ReAct (max 15 iterations) |
| `interaction_validator` | None | N/A | Deterministic |
| `asset_generator_v3` | gemini-2.5-flash | 0.3 | ReAct (max 15 iterations) |
| `blueprint_assembler_v3` | None (deterministic path used) | N/A | Deterministic |

**Total LLM-calling stages**: 7 (3 lightweight in Phase 0, 3 heavy ReAct in Phases 1-3, 1 medium ReAct in Phase 4)
**Total deterministic stages**: 4 (3 validators + blueprint assembler)
**Total tools across ReAct agents**: 20 (5 + 5 + 5 + 5)
