# V3 Pipeline Agents Deep Audit

**Date**: 2026-02-14
**Scope**: Complete analysis of the V3 pipeline agents, tools, state fields, and data flow for multi-scene, multi-mechanic games.
**Goal**: Identify every point where the pipeline breaks for non-drag_drop mechanics.

---

## 1. Complete V3 Graph Topology

### Graph Definition
- **File**: `backend/app/agents/graph.py:1901-2016`
- **Function**: `create_v3_graph()`
- **Node count**: 12 nodes across 5 phases + context gathering
- **Entry point**: `input_enhancer`
- **Terminal**: `blueprint_assembler_v3 -> END`

### Nodes and Agents

| Node Name | Agent Function | Phase | Instrumented |
|---|---|---|---|
| `input_enhancer` | `input_enhancer_agent` | 0 | Yes |
| `domain_knowledge_retriever` | `domain_knowledge_retriever_agent` | 0 | Yes |
| `router` | `router_agent` | 0 | Yes |
| `game_designer_v3` | `game_designer_v3_agent` | 1 | Yes |
| `design_validator` | `design_validator_agent` | 1 | Yes |
| `scene_architect_v3` | `scene_architect_v3_agent` | 2 | Yes |
| `scene_validator` | `scene_validator_agent` | 2 | Yes |
| `interaction_designer_v3` | `interaction_designer_v3_agent` | 3 | Yes |
| `interaction_validator` | `interaction_validator_v3_agent` | 3 | Yes |
| `asset_generator_v3` | `asset_generator_v3_agent` | 4 | Yes |
| `blueprint_assembler_v3` | `deterministic_blueprint_assembler_agent` | 5 | Yes |

**CRITICAL**: Phase 5 uses `deterministic_blueprint_assembler_agent` (line 1964), NOT the ReAct `blueprint_assembler_v3_agent`. The ReAct version exists as legacy code in `blueprint_assembler_v3.py:408-648`.

### Edges

```
input_enhancer --> domain_knowledge_retriever --> router --> game_designer_v3
game_designer_v3 --> design_validator --> [conditional: game_designer_v3 | scene_architect_v3]
scene_architect_v3 --> scene_validator --> [conditional: scene_architect_v3 | interaction_designer_v3]
interaction_designer_v3 --> interaction_validator --> [conditional: interaction_designer_v3 | asset_generator_v3]
asset_generator_v3 --> blueprint_assembler_v3 --> END
```

### Conditional Routing (Retry Loops)

| Router Function | File:Line | Max Retries | Condition |
|---|---|---|---|
| `_v3_design_validation_router` | `graph.py:1862` | 3 | `design_validation_v3.passed == True` |
| `_v3_scene_validation_router` | `graph.py:1875` | 3 | `scene_validation_v3.passed == True` |
| `_v3_interaction_validation_router` | `graph.py:1888` | 3 | `interaction_validation_v3.passed == True` |

All three routers: if retries >= 3, proceed to next phase anyway (lines 1868-1870, 1881-1883, 1894-1896).

### Timeouts

| Agent | Timeout (sec) | File:Line |
|---|---|---|
| `game_designer_v3` | 120 | `graph.py:65` |
| `design_validator` | 30 | `graph.py:66` |
| `scene_architect_v3` | 90 | `graph.py:67` |
| `scene_validator` | 30 | `graph.py:68` |
| `interaction_designer_v3` | 90 | `graph.py:69` |
| `interaction_validator` | 30 | `graph.py:70` |
| `asset_generator_v3` | 600 | `graph.py:71` |
| `blueprint_assembler_v3` | 60 | `graph.py:72` |

---

## 2. Per-Agent Analysis

### 2.1 Game Designer V3 (Phase 1)

**File**: `backend/app/agents/game_designer_v3.py`
**Class**: `GameDesignerV3(ReActAgent)` (line 105)
**Model**: configurable, `max_iterations=6`, `temperature=0.7`

#### State Inputs Read
| Field | Source | Line |
|---|---|---|
| `enhanced_question` | input_enhancer | 129 |
| `question` | original input | 129 |
| `subject` | original input | 130 |
| `blooms_level` | input_enhancer | 131 |
| `domain_knowledge` | DK retriever | 132, 154 |
| `canonical_labels` | DK retriever | 133 |
| `learning_objectives` | input_enhancer | 134 |
| `pedagogical_context` | input_enhancer | 135 |
| `design_validation_v3` | design_validator (on retry) | build_task_prompt reads it |

#### State Outputs Written
| Field | Type | Line |
|---|---|---|
| `game_design_v3` | `Dict[str, Any]` (GameDesignV3Slim) | parse_final_result |
| `current_agent` | `str` | parse_final_result |

#### Tools (5)
| Tool | Implementation | File:Line |
|---|---|---|
| `analyze_pedagogy` | `analyze_pedagogy_impl` | `game_design_v3_tools.py` |
| `check_capabilities` | `check_capabilities_impl` | `game_design_v3_tools.py` |
| `get_example_designs` | `get_example_designs_impl` | `game_design_v3_tools.py` |
| `validate_design` | `validate_design_impl` | `game_design_v3_tools.py` |
| `submit_game_design` | schema-as-tool (GameDesignV3Slim) | `game_design_v3_tools.py` |

#### Mechanic Handling
- System prompt (lines 77-87) provides guidance for all 10 mechanic types
- Outputs `GameDesignV3Slim` with `SlimMechanicRef` per scene mechanic
- `SlimMechanicRef` fields: `type: str`, `config_hint: Dict[str, Any]`, `zone_labels_used: List[str]`
- `config_hint` is a freeform dict -- NOT a typed per-mechanic config (no PathDesign, SequenceDesign, etc.)
- The full `GameDesignV3` schema with `MechanicDesign` (typed configs) exists in `schemas/game_design_v3.py` but V3 pipeline uses the Slim variant

#### DK Field Injection
- `build_task_prompt` (lines 153-167) injects 4 DK sub-fields: `sequence_flow_data`, `label_descriptions`, `comparison_data`, `content_characteristics`
- These inform the LLM's mechanic choices but are NOT structured into the output schema

**BUG-GD-1**: The game designer has no way to pass rich mechanic config data to downstream agents because `SlimMechanicRef.config_hint` is a generic dict, not validated against any per-mechanic schema. Downstream scene architect must re-derive everything from domain knowledge.

**BUG-GD-2**: `check_capabilities_impl` returns a capability matrix showing which mechanics have data support, but the game designer's output schema cannot express whether data is available -- it only outputs `type` + `config_hint`. If the LLM ignores check_capabilities results, the wrong mechanic gets selected.

---

### 2.2 Scene Architect V3 (Phase 2)

**File**: `backend/app/agents/scene_architect_v3.py`
**Class**: `SceneArchitectV3(ReActAgent)` (line 126)
**Model**: configurable, `max_iterations=15`, `temperature=0.5`

#### State Inputs Read
| Field | Source | Line |
|---|---|---|
| `game_design_v3` | game_designer_v3 | 150 |
| `canonical_labels` | DK retriever | 151 |
| `domain_knowledge` | DK retriever | (via v3_context) |
| `scene_validation_v3` | scene_validator (on retry) | build_task_prompt reads it |

#### State Outputs Written
| Field | Type | Line |
|---|---|---|
| `scene_specs_v3` | `List[Dict[str, Any]]` (SceneSpecV3[]) | parse_final_result |
| `current_agent` | `str` | parse_final_result |

#### Tools (5)
| Tool | Implementation | File:Line |
|---|---|---|
| `get_zone_layout_guidance` | `get_zone_layout_guidance_impl` | `scene_architect_tools.py:26` |
| `get_mechanic_config_schema` | `get_mechanic_config_schema_impl` | `scene_architect_tools.py` |
| `generate_mechanic_content` | `generate_mechanic_content_impl` | `scene_architect_tools.py:187` |
| `validate_scene_spec` | `validate_scene_spec_impl` | `scene_architect_tools.py:663` |
| `submit_scene_specs` | schema-as-tool (SceneSpecV3[]) | `scene_architect_tools.py` |

#### Mechanic Handling
- `_MECHANIC_SCENE_GUIDANCE` dict (lines 68-123) provides per-mechanic config guidance for ALL 10 types
- System prompt (lines 47-56) MANDATES calling `generate_mechanic_content` for every non-drag_drop mechanic
- `generate_mechanic_content_impl` (line 187) handles all 10 mechanic types:

| Mechanic | Data Source | Fallback | Lines |
|---|---|---|---|
| `trace_path` | `sequence_flow_data.sequence_items` | LLM waypoint generation | 222-270 |
| `click_to_identify` | `label_descriptions` | Generic "Click on the {label}" | 272-296 |
| `sequencing` | `sequence_flow_data.sequence_items` | LLM sequence generation | 298-356 |
| `sorting_categories` | `comparison_data.sorting_categories` | LLM category generation | 358-420 |
| `description_matching` | `label_descriptions` | LLM description generation | 422-472 |
| `memory_match` | `label_descriptions` | LLM pair generation | 474-534 |
| `compare_contrast` | `comparison_data.groups` | LLM compare generation | 536-591 |
| `branching_scenario` | (none -- always LLM) | LLM decision tree | 593-636 |
| `drag_drop` | (static defaults) | N/A | 638-645 |

#### Auto-Enrichment Safety Net
- `validate_scene_spec_impl` (line 663) checks if mechanic_configs have empty configs
- If a mechanic has `config == {}`, the validator calls `generate_mechanic_content_impl` to auto-populate
- This is a safety net for when the LLM skips the `generate_mechanic_content` tool call
- Located at `scene_architect_tools.py:734+` (cross-check against game design mechanic types)

**BUG-SA-1**: `generate_mechanic_content_impl` reads `sequence_flow_data` from v3_context, but this field may be `None` if DK retriever did not produce it for the given topic. In that case, the LLM fallback is used, but LLM fallbacks operate on `zone_labels` which may not be appropriate for non-zone-based mechanics (sequencing, sorting, memory_match, branching_scenario).

**BUG-SA-2**: `compare_contrast` LLM fallback (lines 553-591) uses `ctx.get("model")` for the LLM model parameter, which reads the model from v3_context. The v3_context does NOT have a "model" key (see `v3_context.py:31-56`), so `ctx.get("model")` returns `None`, causing the LLM service to use its default model. This is inconsistent with all other mechanics that explicitly use `model="gemini-2.5-flash"`.

**BUG-SA-3**: For `description_matching`, the `descriptions` field in the config is a list of `{zone_label, description}` dicts (lines 425-439). But the blueprint assembler (line 684-717) expects EITHER a dict `{zoneId: description}` OR a list `[{zone_id, description}]`. The scene architect produces `{zone_label, description}` (keyed by label text), which the assembler converts using `zone_by_label` lookup. If zone labels don't exactly match (case, spacing, plurals), descriptions silently get dropped.

---

### 2.3 Interaction Designer V3 (Phase 3)

**File**: `backend/app/agents/interaction_designer_v3.py`
**Class**: `InteractionDesignerV3(ReActAgent)` (line 96)
**Model**: configurable, `max_iterations=15`, `temperature=0.5`

#### State Inputs Read
| Field | Source | Line |
|---|---|---|
| `game_design_v3` | game_designer_v3 | 120 |
| `scene_specs_v3` | scene_architect_v3 | 121 |
| `canonical_labels` | DK retriever | (via v3_context) |
| `domain_knowledge` | DK retriever | 175 |
| `interaction_validation_v3` | interaction_validator (on retry) | build_task_prompt reads it |

#### State Outputs Written
| Field | Type | Line |
|---|---|---|
| `interaction_specs_v3` | `List[Dict[str, Any]]` (InteractionSpecV3[]) | parse_final_result |
| `current_agent` | `str` | parse_final_result |

#### Tools (5)
| Tool | Implementation | File:Line |
|---|---|---|
| `get_scoring_templates` | `get_scoring_templates_impl` | `interaction_designer_tools.py` |
| `generate_misconception_feedback` | `generate_misconception_feedback_impl` | `interaction_designer_tools.py` |
| `enrich_mechanic_content` | `enrich_mechanic_content_impl` | `interaction_designer_tools.py:272` |
| `validate_interactions` | `validate_interactions_impl` | `interaction_designer_tools.py:690` |
| `submit_interaction_specs` | schema-as-tool (InteractionSpecV3[]) | `interaction_designer_tools.py` |

#### Mechanic Handling
- System prompt (lines 47-65) provides mechanic-specific scoring/feedback guidance for ALL 10 types
- `enrich_mechanic_content_impl` (line 272) uses `_build_mechanic_enrichment_prompt` (line 378) for tailored per-mechanic prompts
- Returns: `scoring_rationale`, `recommended_scoring`, `enriched_feedback`, `misconception_triggers`, `content_enrichments`

#### Per-Mechanic Enrichment Prompts
| Mechanic | Specific Enrichment | Lines |
|---|---|---|
| `drag_drop` | per_zone_feedback, hint_progression | 410-427 |
| `click_to_identify` | per_prompt_feedback, exploration_hints | 429-449 |
| `trace_path` | per_step_feedback, path_summary, wrong_step_feedback | 451-471+ |
| `sequencing` | per_item_feedback, why_this_order | (continued in prompt) |
| `sorting_categories` | per_category_feedback, per_item_feedback | (continued) |
| `description_matching` | per_description_feedback, confusion_pairs | (continued) |
| `memory_match` | per_pair_feedback, memory_strategy_hints | (continued) |
| `branching_scenario` | per_choice_feedback, consequence_explanations | (continued) |
| `compare_contrast` | per_category_feedback, insight_on_completion | (continued) |
| `hierarchical` | per_level_feedback, relationship_explanations | (continued) |

#### Auto-Enrichment Safety Net
- `validate_interactions_impl` (line 690) checks if scoring/feedback exists for all mechanics in the scene
- If missing, calls `enrich_mechanic_content_impl` to auto-populate
- Cross-checks against `scene_specs_v3` mechanic types (lines 745-763)

**BUG-ID-1**: The enrichment output (`content_enrichments`) from the LLM is NOT guaranteed to have consistent keys across mechanics. The LLM may produce `per_zone_feedback` for drag_drop but omit it for click_to_identify. There is no post-validation of the enrichment structure.

**BUG-ID-2**: The `enrich_mechanic_content_impl` reads `existing_config` from `scene_spec.mechanic_configs` (lines 316-319). If the scene architect's generate_mechanic_content failed for a specific mechanic and only produced `config: {}`, the enrichment prompt will have empty config context, degrading quality.

---

### 2.4 Asset Generator V3 (Phase 4)

**File**: `backend/app/agents/asset_generator_v3.py`
**Class**: `AssetGeneratorV3(ReActAgent)` (line 73)
**Model**: configurable, `max_iterations=15`, `tool_timeout=120.0`, `temperature=0.3`

#### State Inputs Read
| Field | Source | Line |
|---|---|---|
| `scene_specs_v3` | scene_architect_v3 | 97 |
| `game_design_v3` | game_designer_v3 | 98 |
| `enhanced_question` / `question_text` | input_enhancer | 99 |
| `subject` | original input | 100 |
| `canonical_labels` | DK retriever | 101 |

#### State Outputs Written
| Field | Type | Line |
|---|---|---|
| `generated_assets_v3` | `Dict[str, Any]` ({scenes: {num: {diagram_image_url, zones}}}) | 281 |
| `diagram_image` | `Dict[str, Any]` (backward compat) | 290-295 |
| `diagram_zones` | `List[Dict]` (backward compat) | 298-300 |
| `current_agent` | `str` | 280 |

#### Tools (5)
| Tool | Implementation |
|---|---|
| `search_diagram_image` | Image search + auto-clean pipeline |
| `generate_diagram_image` | AI image generation |
| `detect_zones` | Zone detection (gemini, SAM3, auto) |
| `generate_animation_css` | CSS animation generation |
| `submit_assets` | Schema-as-tool for per-scene assets |

#### Mechanic Handling
- System prompt (lines 40-47) lists mechanic-aware image requirements
- However, the agent is **100% zone/image focused** -- it generates ONE diagram image per scene and detects zones on it
- Does NOT generate per-mechanic assets:
  - No sequence step icons for `sequencing`
  - No sorting item images for `sorting_categories`
  - No memory card images for `memory_match`
  - No scene images for `branching_scenario`
  - No comparison subject images for `compare_contrast`

**BUG-AG-1**: The AgentState has per-mechanic asset fields (lines 477-481): `sequence_item_images`, `sorting_item_images`, `sorting_category_icons`, `memory_card_images`, `diagram_crop_regions`. These fields are NEVER written by `asset_generator_v3`. They exist in the TypedDict but no agent populates them.

**BUG-AG-2**: For mechanics that DON'T need a diagram image (`sequencing`, `sorting_categories`, `memory_match`, `branching_scenario` per mechanic_contracts.py `needs_diagram=False`), the asset generator still generates/searches for a diagram image. This is unnecessary work and may produce images irrelevant to the mechanic.

**BUG-AG-3**: `_reconstruct_from_tool_results` uses simple scene counter ("1", "2", "3") to key scenes. If tool calls are reordered or retried, scene numbering may be inconsistent with `scene_specs_v3` numbering.

**BUG-AG-4**: Backward compat writes (`diagram_image`, `diagram_zones`) only come from scene 1 (lines 284-300). Multi-scene games get scene 1's diagram as the root-level fallback, which is correct for backward compat but means legacy code paths only ever see scene 1 data.

---

### 2.5 Blueprint Assembler V3 (Phase 5)

**File**: `backend/app/agents/blueprint_assembler_v3.py` (agent)
**File**: `backend/app/tools/blueprint_assembler_tools.py` (assembly logic)
**Function**: `deterministic_blueprint_assembler_agent` (line 658)
**LLM**: NONE (deterministic)

#### State Inputs Read
| Field | Source | Line |
|---|---|---|
| `game_design_v3` | game_designer_v3 | `blueprint_assembler_tools.py:175` |
| `scene_specs_v3` | scene_architect_v3 | `blueprint_assembler_tools.py:176` |
| `interaction_specs_v3` | interaction_designer_v3 | `blueprint_assembler_tools.py:177` |
| `generated_assets_v3` | asset_generator_v3 | `blueprint_assembler_tools.py:178` |

#### State Outputs Written
| Field | Type | Line |
|---|---|---|
| `blueprint` | `Dict[str, Any]` (InteractiveDiagramBlueprint) | `blueprint_assembler_v3.py:764` |
| `template_type` | `"INTERACTIVE_DIAGRAM"` | `blueprint_assembler_v3.py:765` |
| `generation_complete` | `True` | `blueprint_assembler_v3.py:766` |
| `current_agent` | `str` | `blueprint_assembler_v3.py:763` |

#### Assembly Pipeline
1. `assemble_blueprint_impl()` -- Reads all upstream data, builds blueprint dict
2. `validate_blueprint_impl(blueprint)` -- Checks for issues
3. `repair_blueprint_impl(blueprint, issues)` -- Fixes issues (up to 2 iterations)
4. Returns final blueprint

#### Per-Mechanic Config Promotion
The assembler promotes per-mechanic config keys from `scene_spec.mechanic_configs[].config` to frontend-compatible keys on each scene:

| Mechanic | Config Key(s) | Assembly Lines |
|---|---|---|
| `trace_path` | `tracePathConfig` + `paths` | `blueprint_assembler_tools.py:586-613` |
| `click_to_identify` | `clickToIdentifyConfig` + `identificationPrompts` | `blueprint_assembler_tools.py:615-659` |
| `sequencing` | `sequenceConfig` | `blueprint_assembler_tools.py:661-680` |
| `description_matching` | `descriptionMatchingConfig` | `blueprint_assembler_tools.py:682-717` |
| `sorting_categories` | `sortingConfig` | `blueprint_assembler_tools.py:719-772` |
| `memory_match` | `memoryMatchConfig` | `blueprint_assembler_tools.py:774-805` |
| `branching_scenario` | `branchingConfig` | `blueprint_assembler_tools.py:807-821` |
| `compare_contrast` | `compareConfig` | `blueprint_assembler_tools.py:823-840` |
| `drag_drop` | `dragDropConfig` | `blueprint_assembler_tools.py:842-857` |

#### Multi-Scene Handling
- `is_multi = len(game_scenes) > 1` (line 1064)
- Multi-scene: wraps in `game_sequence` (lines 1066-1088), promotes first scene's configs to root (lines 1090-1103)
- Single-scene: flattens to root-level structure (lines 1125-1160)
- Per-mechanic configs promoted BOTH at mechanic level (line 1008-1014) AND at scene level (lines 1052-1060) AND at blueprint root (lines 1095-1103 or 1130-1141)

**BUG-BA-1**: `drag_drop` uses `if` instead of `elif` (line 843: `if mech_type == "drag_drop":`). All other mechanics use `elif`. This means for ALL mechanics, the code ALSO checks for drag_drop and adds `dragDropConfig` if the type matches. This is functionally correct but breaks the if/elif chain pattern -- the `mech_entry["config"] = mech_cfg` on line 859 executes for ALL mechanics including those that fell through to the drag_drop check.

**BUG-BA-2**: For `compare_contrast`, the assembler (line 825) checks `expected = mech_cfg.get("expected_categories", {})` and only creates `compareConfig` if `expected` is truthy. But `generate_mechanic_content_impl` for compare_contrast can return `expected_categories` as a dict mapping `{member: group_name}` (line 543) or as a list from the LLM fallback (line 582). If it is an empty dict or list, `compareConfig` is silently omitted.

**BUG-BA-3**: For `sequencing`, the assembler (line 664-666) checks `if items or correct_order:`. If both are empty (because generate_mechanic_content failed), `sequenceConfig` is silently omitted. No error or warning is raised.

**BUG-BA-4**: The scoring/feedback conversion (lines 462-479) converts `InteractionSpecV3.scoring` and `.feedback` from lists to lookup dicts keyed by `mechanic_type`. If the LLM produces scoring entries WITHOUT a `mechanic_type` key, they are silently dropped from the lookup.

---

## 3. State Field Map

### V3 Pipeline State Fields (from `state.py:455-485`)

| Field | Type | Written By | Read By |
|---|---|---|---|
| `game_design_v3` | `Optional[Dict[str, Any]]` | game_designer_v3 | scene_architect_v3, interaction_designer_v3, asset_generator_v3, blueprint_assembler_v3 |
| `design_validation_v3` | `Optional[Dict[str, Any]]` | design_validator | game_designer_v3 (retry), graph router |
| `_v3_design_retries` | `Optional[int]` | design_validator | graph router |
| `scene_specs_v3` | `Optional[List[Dict[str, Any]]]` | scene_architect_v3 | interaction_designer_v3, asset_generator_v3, blueprint_assembler_v3 |
| `scene_validation_v3` | `Optional[Dict[str, Any]]` | scene_validator | scene_architect_v3 (retry), graph router |
| `_v3_scene_retries` | `Optional[int]` | scene_validator | graph router |
| `interaction_specs_v3` | `Optional[List[Dict[str, Any]]]` | interaction_designer_v3 | blueprint_assembler_v3 |
| `interaction_validation_v3` | `Optional[Dict[str, Any]]` | interaction_validator | interaction_designer_v3 (retry), graph router |
| `_v3_interaction_retries` | `Optional[int]` | interaction_validator | graph router |
| `generated_assets_v3` | `Optional[Dict[str, Any]]` | asset_generator_v3 | blueprint_assembler_v3 |
| `sequence_item_images` | `Optional[Dict[str, str]]` | **NOBODY** | **NOBODY** |
| `sorting_item_images` | `Optional[Dict[str, str]]` | **NOBODY** | **NOBODY** |
| `sorting_category_icons` | `Optional[Dict[str, str]]` | **NOBODY** | **NOBODY** |
| `memory_card_images` | `Optional[Dict[str, str]]` | **NOBODY** | **NOBODY** |
| `diagram_crop_regions` | `Optional[Dict[str, Dict]]` | **NOBODY** | **NOBODY** |

### V3 Context Fields (from `v3_context.py:31-56`)

| Context Field | Source State Field | Used By Tools |
|---|---|---|
| `question` | `enhanced_question` / `question_text` | All tools (prompt context) |
| `subject` | `subject` | Asset tools (search queries) |
| `blooms_level` | `blooms_level` | Pedagogy analysis |
| `domain_knowledge` | `domain_knowledge` | All tools (content reference) |
| `canonical_labels` | `canonical_labels` | All tools (label lists) |
| `game_design_v3` | `game_design_v3` | Interaction tools, blueprint tools |
| `scene_specs_v3` | `scene_specs_v3` | Interaction tools, blueprint tools |
| `interaction_specs_v3` | `interaction_specs_v3` | Blueprint tools |
| `generated_assets_v3` | `generated_assets_v3` | Blueprint tools |
| `sequence_flow_data` | `domain_knowledge.sequence_flow_data` | generate_mechanic_content (trace_path, sequencing) |
| `label_descriptions` | `domain_knowledge.label_descriptions` | generate_mechanic_content (click, description, memory) |
| `comparison_data` | `domain_knowledge.comparison_data` | generate_mechanic_content (sorting, compare) |
| `term_definitions` | `domain_knowledge.term_definitions` | **NOT USED by any tool** |
| `causal_relationships` | `domain_knowledge.causal_relationships` | **NOT USED by any tool** |
| `spatial_data` | `domain_knowledge.spatial_data` | **NOT USED by any tool** |
| `process_steps` | `domain_knowledge.process_steps` | **NOT USED by any tool** |
| `hierarchical_data` | `domain_knowledge.hierarchical_data` | **NOT USED by any tool** |
| `content_characteristics` | `domain_knowledge.content_characteristics` | game_designer_v3 prompt only |
| `hierarchical_relationships` | `domain_knowledge.hierarchical_relationships` | **NOT USED by any tool** |

**BUG-SF-1**: 5 of 10 promoted DK context fields (`term_definitions`, `causal_relationships`, `spatial_data`, `process_steps`, `hierarchical_data`) are injected into v3_context but NEVER read by ANY tool. They are wasted context.

**BUG-SF-2**: `hierarchical_relationships` is injected but never read. The `hierarchical` mechanic has NO generate_mechanic_content handler -- it is completely absent from `generate_mechanic_content_impl`.

---

## 4. Mechanic Content Generation: What Is Actually Produced

### Per-Mechanic Data Flow Table

| Mechanic | DK Data Needed | generate_mechanic_content Output | enrich_mechanic_content Output | Blueprint Config Key | Config Populated? |
|---|---|---|---|---|---|
| `drag_drop` | (none) | `{shuffle_labels, show_hints, max_attempts}` | per_zone_feedback, hint_progression | `dragDropConfig` | Always |
| `click_to_identify` | `label_descriptions` | `{prompt_style, prompts: [{zone_label, prompt_text}], ...}` | per_prompt_feedback, exploration_hints | `clickToIdentifyConfig` + `identificationPrompts` | Always (fallback: "Click on {label}") |
| `trace_path` | `sequence_flow_data` | `{waypoints, path_type, drawing_mode, ...}` | per_step_feedback, path_summary | `tracePathConfig` + `paths` | Only if sequence_flow_data has items |
| `sequencing` | `sequence_flow_data` | `{items, correct_order, layout_mode, ...}` | per_item_feedback | `sequenceConfig` | Only if sequence_flow_data has items |
| `sorting_categories` | `comparison_data` | `{categories, items, sort_mode, ...}` | per_category_feedback | `sortingConfig` | Only if comparison_data has sorting_categories |
| `description_matching` | `label_descriptions` | `{mode, descriptions: [{zone_label, description}]}` | per_description_feedback | `descriptionMatchingConfig` | Only if label_descriptions populated |
| `memory_match` | `label_descriptions` | `{pairs: [{id, term, definition}], ...}` | per_pair_feedback | `memoryMatchConfig` | Only if label_descriptions populated |
| `compare_contrast` | `comparison_data` | `{expected_categories, similarities, differences}` | per_category_feedback | `compareConfig` | Only if comparison_data populated |
| `branching_scenario` | (none -- always LLM) | `{nodes, startNodeId, ...}` | per_choice_feedback | `branchingConfig` | Always (LLM-generated) |
| `hierarchical` | **NOT HANDLED** | **NOT GENERATED** | (generic) | (none defined) | **NEVER** |

### LLM Fallback Status

Every mechanic except `drag_drop` and `hierarchical` has an LLM fallback in `generate_mechanic_content_impl`. However:
- LLM fallbacks use `model="gemini-2.5-flash"` (cheap/fast) except `compare_contrast` which uses `ctx.get("model")` -> `None`
- LLM fallbacks operate on `zone_labels` which may be inappropriate for content-only mechanics (sequencing items are NOT zone labels)
- If LLM fails, the function returns `{generated: False, note: "No upstream data..."}` -- the config remains empty

---

## 5. Multi-Scene / Multi-Mechanic Flow

### What Works

1. **Multi-scene with drag_drop only**: Works well. Each scene gets its own diagram, zones, labels. The blueprint assembler creates a `game_sequence` wrapper with proper scene transitions.

2. **Single-scene multi-mechanic**: Works IF all mechanic configs are populated. The blueprint includes `mode_transitions` and each mechanic has its config promoted to the scene level.

3. **Scoring/feedback per mechanic**: The interaction designer creates per-mechanic scoring and feedback entries. The blueprint assembler correctly converts lists to dicts and attaches per-mechanic scoring/feedback to each mechanic entry.

### What Breaks

1. **Multi-scene with mixed mechanics (e.g., scene 1 = drag_drop, scene 2 = sequencing)**:
   - If DK lacks `sequence_flow_data`, scene 2's `sequenceConfig` is either LLM-generated (unreliable) or empty
   - Blueprint assembler silently omits `sequenceConfig` if `items` and `correct_order` are both empty (line 666)
   - Frontend receives a mechanic with `type: "sequencing"` but no `sequenceConfig` -- component crashes or shows empty state

2. **Mechanics without diagram needs**:
   - `sequencing`, `sorting_categories`, `memory_match`, `branching_scenario` are defined in mechanic_contracts.py with `needs_diagram=False`
   - But asset_generator_v3 generates diagram images for ALL scenes regardless
   - The generated diagram may be semantically wrong for a sorting exercise
   - No mechanism to skip image generation for content-only scenes

3. **Multi-mechanic scene with trace_path + drag_drop**:
   - Both mechanics share the same zones
   - `tracePathConfig.paths[].waypoints[].zoneId` references zone IDs built from `_make_id("zone", scene_num, label)`
   - If the waypoint label from `generate_mechanic_content` doesn't exactly match a zone label (case/spacing), the `zoneId` won't match any actual zone, and path rendering breaks

4. **Scene transition for non-zone mechanics**:
   - Transition triggers are `score_threshold` by default (line 905)
   - For `branching_scenario` or `memory_match`, the scoring model is different (per-decision vs per-pair)
   - No special transition logic for content-only mechanics

5. **Asset generation for compare_contrast**:
   - mechanic_contracts.py says `needs_second_diagram=True`
   - asset_generator_v3 has NO logic to generate two diagrams for one scene
   - It generates one diagram per scene, so compare_contrast can only compare structures within a single diagram

---

## 6. mechanic_contracts.py Usage

### Status: COMPLETELY UNUSED / DEAD CODE

**File**: `backend/app/config/mechanic_contracts.py` (458 lines)

The file defines:
- `MechanicContract` dataclass with per-stage contracts for all 10 mechanics
- `MECHANIC_CONTRACTS` registry with 10 entries
- `_ALIASES` for type normalization
- Helper functions: `get_contract()`, `get_contract_safe()`, `normalize_mechanic_type()`, `needs_image_pipeline()`, `get_frontend_config_key()`, `get_all_mechanic_types()`, `get_image_mechanics()`, `get_content_only_mechanics()`

### Import Analysis

Searching the entire `backend/` directory for imports of `mechanic_contracts`:
- **ZERO imports** in any V3 agent
- **ZERO imports** in any V3 tool
- **ZERO imports** in any route
- **ZERO imports** in any service
- Only references found: in a session continuation transcript file (`backend/2026-02-12-this-session-is-being-continued-from-a-previous-co.txt`) which contains proposed code changes that were never implemented

### Impact

The entire mechanic_contracts system was designed to be the source of truth for what each mechanic needs from each pipeline stage. It correctly defines:
- Which mechanics need diagram images and which don't (`needs_diagram`)
- Which DK fields each mechanic needs (`dk_fields`)
- What each stage should output (`required_output_fields`)
- The frontend config key (`frontend_config_key`)

None of this is consulted by any agent or tool. Instead, each agent hardcodes its own mechanic knowledge independently, leading to inconsistencies.

---

## 7. drag_drop Bias

### Every Hardcoded Default or Assumption Found

| Location | File:Line | Bias Description |
|---|---|---|
| 1 | `design_interpreter.py:402` | `_normalize_mechanic_type`: returns `"drag_drop"` for empty string |
| 2 | `design_interpreter.py:419-420` | `_normalize_mechanic_type`: defaults unknown types to `"drag_drop"` |
| 3 | `design_interpreter.py:463` | Primary mechanic type fallback: `drag_drop` |
| 4 | `design_interpreter.py:467` | Workflow mechanic type fallback: `drag_drop` |
| 5 | `design_interpreter.py:473` | Workflow mechanic type fallback: `drag_drop` |
| 6 | `design_interpreter.py:484` | Primary mechanic type fallback: `drag_drop` |
| 7 | `design_interpreter.py:487` | Workflow mechanic type fallback: `drag_drop` |
| 8 | `design_interpreter.py:493` | Workflow mechanic type fallback: `drag_drop` |
| 9 | `design_interpreter.py:508` | Interaction mode fallback: `drag_drop` |
| 10 | `design_interpreter.py:543` | Workflow mechanic type fallback: `drag_drop` |
| 11 | `design_interpreter.py:549` | Workflow mechanic type fallback: `drag_drop` |
| 12 | `design_interpreter.py:583` | `_infer_mechanic_from_description`: default return `drag_drop` |
| 13 | `design_interpreter.py:603` | `_infer_mechanic_from_description`: default return `drag_drop` |
| 14 | `design_interpreter.py:615` | `_create_default_scene`: hardcoded `drag_drop` |
| 15 | `design_interpreter.py:618` | `_create_default_scene`: hardcoded `drag_drop` |
| 16 | `design_interpreter.py:633-692` | `_create_fallback_plan`: all defaults to `drag_drop` |

**NOTE**: `design_interpreter.py` is NOT part of the V3 pipeline (it's used by earlier presets). However, if V3 router falls back to legacy pipelines, these biases re-emerge.

**In V3 Pipeline specifically**:

| Location | File:Line | Bias Description |
|---|---|---|
| 17 | `scene_architect_tools.py:638-645` | `generate_mechanic_content_impl` for drag_drop: produces static `{shuffle_labels, show_hints, max_attempts}` -- trivial config compared to all other mechanics |
| 18 | `blueprint_assembler_tools.py:843` | `if mech_type == "drag_drop":` uses `if` not `elif` -- always checked last regardless of mechanic chain |
| 19 | `blueprint_assembler_tools.py:1117` | Multi-scene root `interaction_mode` defaults to first mechanic type. If scene 1 is drag_drop, root mode is `drag_drop` even if scene 2 is something else |
| 20 | `blueprint_assembler_tools.py:931` | Fallback max_score calculation: `len(global_labels) * 10` -- assumes label-count scoring (drag_drop pattern), wrong for sequencing/sorting/memory |

---

## 8. Every Bug Found

### Critical Bugs (Will Cause Exceptions or Missing Data)

| ID | Severity | File:Line | Description |
|---|---|---|---|
| BUG-MC-1 | CRITICAL | `mechanic_contracts.py` (entire file) | mechanic_contracts.py is NOT imported or used by ANY V3 agent/tool. 458 lines of dead code that was intended to be the source of truth. |
| BUG-AG-1 | CRITICAL | `state.py:477-481` | Per-mechanic asset fields (`sequence_item_images`, `sorting_item_images`, `sorting_category_icons`, `memory_card_images`, `diagram_crop_regions`) are declared in AgentState but NEVER written by any agent. |
| BUG-SA-2 | HIGH | `scene_architect_tools.py:578` | `compare_contrast` LLM fallback uses `ctx.get("model")` which returns `None` (not in v3_context). All other mechanics use explicit `model="gemini-2.5-flash"`. |
| BUG-BA-3 | HIGH | `blueprint_assembler_tools.py:664-666` | `sequenceConfig` silently omitted if `items` and `correct_order` are both empty. No warning logged. Frontend gets `type: "sequencing"` with no config. |
| BUG-BA-2 | HIGH | `blueprint_assembler_tools.py:825-826` | `compareConfig` silently omitted if `expected_categories` is empty/falsy. Frontend gets `type: "compare_contrast"` with no config. |
| BUG-SF-2 | HIGH | `scene_architect_tools.py:187-656` | `hierarchical` mechanic has NO handler in `generate_mechanic_content_impl`. If game designer selects `hierarchical`, scene architect produces empty config, and NO enrichment happens. |
| BUG-AG-2 | MEDIUM | `asset_generator_v3.py:28-70` | Asset generator generates diagram images for ALL scenes, including content-only mechanics (sequencing, sorting, memory, branching) that don't need diagrams. |

### Logic Bugs (Will Produce Wrong Output)

| ID | Severity | File:Line | Description |
|---|---|---|---|
| BUG-SA-1 | HIGH | `scene_architect_tools.py:187-656` | LLM fallbacks for content-only mechanics operate on `zone_labels` instead of domain-specific items. For sequencing, labels like "Left Atrium" become sequence items, which is wrong -- sequence items should be process steps. |
| BUG-SA-3 | MEDIUM | `scene_architect_tools.py:425-439` | description_matching config uses `{zone_label, description}` keys. Blueprint assembler tries to match via `zone_by_label` lookup. Mismatched label text (case/spacing) causes descriptions to be silently dropped. |
| BUG-BA-4 | MEDIUM | `blueprint_assembler_tools.py:462-479` | Scoring/feedback entries without `mechanic_type` key are silently dropped from the lookup dict. LLM may omit this key. |
| BUG-GD-1 | MEDIUM | `game_designer_v3.py:105+` | GameDesignV3Slim uses `SlimMechanicRef.config_hint` (freeform dict) instead of typed per-mechanic schemas. Rich mechanic config data cannot be passed to downstream agents. |
| BUG-GD-2 | MEDIUM | `game_design_v3_tools.py` | `check_capabilities_impl` returns data availability info, but the game designer's output schema cannot express whether data is available. |
| BUG-ID-1 | MEDIUM | `interaction_designer_tools.py:272-376` | LLM enrichment output has no guaranteed key structure. `content_enrichments` keys vary by mechanic and LLM run. |
| BUG-ID-2 | MEDIUM | `interaction_designer_tools.py:308-319` | If scene architect's generate_mechanic_content failed, enrichment reads empty `existing_config`, degrading prompt quality. |
| BUG-BA-1 | LOW | `blueprint_assembler_tools.py:843` | `drag_drop` check uses `if` instead of `elif`, breaking the if/elif chain pattern. Functionally correct but confusing. |
| BUG-AG-3 | LOW | `asset_generator_v3.py:_reconstruct_from_tool_results` | Uses simple counter for scene keys. May mismatch scene numbering in edge cases. |
| BUG-AG-4 | LOW | `asset_generator_v3.py:284-300` | Backward compat writes only scene 1 data to root-level `diagram_image`/`diagram_zones`. |
| BUG-BA-5 | LOW | `blueprint_assembler_tools.py:931` | Fallback max_score uses `len(global_labels) * 10` -- assumes label-count scoring. Wrong for sequencing (item count), sorting (item count), memory (pair count), branching (node count). |

### Data Flow Gaps (Fields Injected But Never Read)

| ID | Severity | File:Line | Description |
|---|---|---|---|
| BUG-SF-1 | LOW | `v3_context.py:51-55` | 5 context fields never read by any tool: `term_definitions`, `causal_relationships`, `spatial_data`, `process_steps`, `hierarchical_data`. Also `hierarchical_relationships` (line 48). |

---

## 9. Proposed Fixes with Priority Ordering

### P0: Critical Blockers (Must Fix First)

**Fix 1: Wire mechanic_contracts.py into the pipeline**
- Import `get_contract()` and `needs_image_pipeline()` into `scene_architect_tools.py`, `asset_generator_v3.py`, and `blueprint_assembler_tools.py`
- Use `needs_image_pipeline()` in asset_generator_v3 to skip diagram generation for content-only mechanics
- Use `get_frontend_config_key()` in blueprint_assembler_tools.py instead of hardcoded if/elif chain
- Use `get_contract().dk_fields` in v3_context.py to validate DK field availability per mechanic
- **Impact**: All 10 mechanics get consistent treatment based on a single source of truth
- **Files**: `scene_architect_tools.py`, `asset_generator_v3.py`, `blueprint_assembler_tools.py`, `v3_context.py`

**Fix 2: Add `hierarchical` handler to generate_mechanic_content_impl**
- Add handler at `scene_architect_tools.py:638` (before the drag_drop handler)
- Read `hierarchical_relationships` or `hierarchical_data` from context
- Generate `zone_groups: [{parent_zone_id, child_zone_ids}]`
- **Impact**: `hierarchical` mechanic becomes functional in V3 pipeline
- **Files**: `scene_architect_tools.py`

**Fix 3: Add config emptiness warnings in blueprint assembler**
- For each mechanic, if the specific config key is empty/missing AND the mechanic type requires it, log a WARNING and optionally generate a minimal default
- Add to `blueprint_assembler_tools.py` after each per-mechanic config block (lines 571-857)
- **Impact**: Silent failures become visible; frontend gets at least minimal configs

### P1: High Priority (Fix for Reliable Non-drag_drop)

**Fix 4: Fix compare_contrast LLM model parameter**
- `scene_architect_tools.py:578`: Change `model=ctx.get("model")` to `model="gemini-2.5-flash"`
- **Impact**: compare_contrast LLM fallback uses correct model
- **Files**: `scene_architect_tools.py`

**Fix 5: Fix zone label matching in description_matching**
- In `blueprint_assembler_tools.py:684-717`, add fuzzy matching for `zone_label` -> `zone_by_label` lookup (case-insensitive, strip whitespace, handle plurals)
- The `_normalize_label()` helper already exists (used for zone lookup) -- extend to description matching
- **Impact**: description_matching descriptions don't silently drop when labels have minor formatting differences
- **Files**: `blueprint_assembler_tools.py`

**Fix 6: Separate zone-based and content-based mechanic handling in asset_generator_v3**
- Check mechanic type per scene. If ALL mechanics in a scene are content-only, skip image/zone generation
- If ANY mechanic needs zones, generate image + zones for that scene only
- Use `needs_image_pipeline()` from mechanic_contracts
- **Impact**: Content-only scenes don't get unnecessary/misleading diagram images
- **Files**: `asset_generator_v3.py`

**Fix 7: Fix scoring fallback for non-label-count mechanics**
- `blueprint_assembler_tools.py:930-933`: Use mechanic-appropriate fallback:
  - sequencing: `len(items) * 10`
  - sorting: `len(items) * 10`
  - memory_match: `len(pairs) * 10`
  - branching: `len(nodes) * 10`
  - Default: `len(labels) * 10`
- **Impact**: Correct max_score for all mechanic types
- **Files**: `blueprint_assembler_tools.py`

### P2: Medium Priority (Quality Improvements)

**Fix 8: Improve LLM fallback context for content-only mechanics**
- In `generate_mechanic_content_impl`, when the LLM fallback fires for sequencing/sorting/memory:
  - Pass the full DK text to the LLM (not just zone_labels)
  - For sequencing: extract process steps from DK even if sequence_flow_data is missing
  - For sorting: extract category hints from DK even if comparison_data is missing
- **Impact**: LLM fallbacks produce higher quality mechanic content
- **Files**: `scene_architect_tools.py`

**Fix 9: Validate enrichment output structure**
- In `enrich_mechanic_content_impl`, after LLM returns:
  - Validate that `scoring_rationale`, `recommended_scoring`, `enriched_feedback` exist
  - Fill defaults if missing
  - Validate `content_enrichments` has expected per-mechanic keys
- **Impact**: Consistent enrichment output regardless of LLM variability
- **Files**: `interaction_designer_tools.py`

**Fix 10: Add mechanic_type validation to scoring/feedback entries**
- In `blueprint_assembler_tools.py:468-479`, if a scoring/feedback entry lacks `mechanic_type`:
  - Try to infer from other keys (e.g., `strategy`, `points_per_correct` patterns)
  - Or assign to the first unmatched mechanic in the scene
- **Impact**: Scoring/feedback entries don't get silently dropped
- **Files**: `blueprint_assembler_tools.py`

### P3: Low Priority (Cleanup and Consistency)

**Fix 11: Clean up unused v3_context fields**
- Remove `term_definitions`, `causal_relationships`, `spatial_data`, `process_steps`, `hierarchical_data` from v3_context injection (or wire them to actual tool consumers)
- **Files**: `v3_context.py`

**Fix 12: Clean up per-mechanic asset state fields**
- Either wire `sequence_item_images`, `sorting_item_images`, etc. to asset_generator_v3, OR remove them from AgentState
- **Files**: `state.py`, optionally `asset_generator_v3.py`

**Fix 13: Fix drag_drop if/elif chain**
- Change `if mech_type == "drag_drop":` to `elif mech_type == "drag_drop":` at `blueprint_assembler_tools.py:843`
- Move it inside the elif chain with other mechanics
- **Files**: `blueprint_assembler_tools.py`

**Fix 14: Add dual-diagram support for compare_contrast**
- Extend asset_generator_v3 to detect when a scene uses compare_contrast
- Generate two diagram images for that scene
- Blueprint assembler creates `compareConfig.diagramA` and `compareConfig.diagramB`
- **Impact**: compare_contrast can actually show side-by-side diagrams
- **Files**: `asset_generator_v3.py`, `blueprint_assembler_tools.py`

---

## Summary

The V3 pipeline has solid architecture: 5 phases, proper ReAct agents with tool-calling, safety-net validators with auto-enrichment, and a deterministic blueprint assembler. The per-mechanic content generation tools (`generate_mechanic_content`, `enrich_mechanic_content`) handle 9 of 10 mechanics with both upstream-data-driven and LLM-fallback paths.

However, there are three fundamental issues preventing reliable multi-mechanic games:

1. **mechanic_contracts.py is dead code**: The carefully designed contract registry is never consulted. Each agent independently hardcodes mechanic knowledge, leading to inconsistencies (e.g., asset generator doesn't know which mechanics need diagrams).

2. **Silent config omission**: When mechanic content generation fails or produces empty configs, the blueprint assembler silently omits the frontend config key (sequenceConfig, compareConfig, etc.). The frontend receives a mechanic type with no config data, causing crashes.

3. **Content-only mechanics treated as zone-based**: sequencing, sorting, memory_match, and branching_scenario don't need diagram images or zones, but the asset generator processes them identically to drag_drop. The LLM fallbacks for these mechanics use zone_labels as input, which is semantically wrong.

Fixing these three root causes (P0 fixes 1-3) would make the pipeline reliably support all 10 mechanic types in multi-scene, multi-mechanic configurations.
