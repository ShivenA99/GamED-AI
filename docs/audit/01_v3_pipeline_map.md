# Audit Doc 01: V3 Pipeline Map — Exhaustive Deep Audit

> **Generated:** 2026-02-10 | **Status:** Complete (Deep Audit v2) | **Scope:** Agent-by-agent V3 pipeline with per-line bug catalog
> **Total Bugs Found:** 77 across 15 components | **Method:** Line-by-line code review

---

## Overview

The V3 pipeline is a **5-phase ReAct architecture** for educational game generation (preset=`"v3"`). It uses **12 agents** across context gathering (Phase 0) and 5 production phases, with **retry loops** at Phases 1-3 and deterministic assembly in Phases 4-5.

**Total tools:** 22 across 5 ReAct agents
**Graph factory:** `create_v3_graph()` in `backend/app/agents/graph.py`
**Schema-as-tool pattern:** submit_* tools use Pydantic schema as input, enabling structured output

---

## Bug Severity Legend

| Severity | Description |
|----------|-------------|
| **CRITICAL** | Game won't work or data loss occurs |
| **HIGH** | Major feature broken, degraded quality, or silent data loss |
| **MEDIUM** | Incorrect behavior in edge cases, observability gaps |
| **LOW** | Code quality, minor inefficiency |

---

## Phase 0: Context Gathering

### 1. input_enhancer_agent

- **File:** `backend/app/agents/input_enhancer.py`
- **Type:** Simple LLM call (not ReAct)
- **Reads:** `question_text`, `question_options`, `question_id`
- **Writes:** `enhanced_question`, `current_agent`
- **Purpose:** Normalize and enhance raw question input

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| IE-1 | ~231 | HIGH | Silent early return when LLM fails — sets `enhanced_question` to original `question_text` with no `error_state` flag | Downstream agents don't know input wasn't actually enhanced. Domain knowledge retriever may generate poor labels from unstructured input. |
| IE-2 | ~309 | MEDIUM | Bloom's level normalization silently downgrades invalid values to "understand" | If pedagogical_context contains custom Bloom's like "create+evaluate", it's replaced with "understand" without logging. Affects mechanic recommendations. |
| IE-3 | ~245 | MEDIUM | `question_options` concatenated as comma-separated string in prompt | If options contain commas, the LLM sees ambiguous boundaries. Should use numbered list or JSON array. |
| IE-4 | ~260 | LOW | No validation that enhanced_question is actually different from input | Agent may return identical text, wasting an LLM call with no quality improvement. |

---

### 2. domain_knowledge_retriever_agent

- **File:** `backend/app/agents/domain_knowledge_retriever.py`
- **Type:** Simple LLM call (not ReAct)
- **Reads:** `enhanced_question` / `question_text`, `pedagogical_context`
- **Writes:** `domain_knowledge` (nested dict), `canonical_labels` (List[str]), `learning_objectives`
- **Purpose:** Retrieve educational context, canonical labels, sequence/flow data, content characteristics

**State Write Detail:**
```python
return {
    **state,
    "domain_knowledge": {
        **knowledge,
        "retrieved_at": datetime.utcnow().isoformat(),
        "sequence_flow_data": sequence_flow_data,
        "content_characteristics": content_characteristics,
    },
    "canonical_labels": canonical_labels,  # F1 fix: top-level promotion
    "current_agent": "domain_knowledge_retriever",
}
```

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| DK-1 | ~486 | HIGH | When LLM output is malformed JSON, fallback creates dict with `"raw_text"` key but NO `canonical_labels`, `sequence_flow_data`, or `content_characteristics` | All downstream V3 agents get empty labels. Game designer has no label guidance. Asset generator doesn't know what zones to detect. |
| DK-2 | ~493 | MEDIUM | Label count warning logged when `< 3` labels extracted, but no retry or fallback search | 2-label games pass validation (score 0.95 in design_validator) but create trivially easy games. Should retry with expanded query. |
| DK-3 | ~527 | HIGH | `content_characteristics` nested inside `domain_knowledge` dict, not promoted to top-level state | V3 agents reading `state.get("content_characteristics")` get None. Only accessible via `state["domain_knowledge"]["content_characteristics"]`. |
| DK-4 | ~510 | MEDIUM | `sequence_flow_data` only populated when `needs_sequence=True` (question contains flow/process/cycle keywords) | Questions like "stages of mitosis" may not trigger sequence detection if keywords don't match. Sequencing mechanic gets no data. |
| DK-5 | ~498 | HIGH | `hierarchical_relationships` nested in `domain_knowledge` but V3 agents never extract it | Hierarchy data (parent-child relationships) never reaches scene_architect or blueprint_assembler. Hierarchy as cross-cutting feature is data-starved. |
| DK-6 | ~515 | MEDIUM | `acceptable_variants` (alternative names for labels) nested in `domain_knowledge`, not in v3_context | Asset generator detect_zones can't use variants for fuzzy label matching. Zone detection misses labels with alternate spellings. |
| DK-7 | ~530 | LOW | `retrieved_at` timestamp uses `datetime.utcnow()` (deprecated in Python 3.12+) | Should use `datetime.now(timezone.utc)`. No functional impact currently. |

---

### 3. router_agent

- **File:** `backend/app/agents/router.py`
- **Type:** Simple LLM call
- **Reads:** `question_text`, `question_options`, `pedagogical_context`
- **Writes:** `template_selection` (Dict with `template_type`, `confidence`, `reasoning`)
- **Purpose:** Select game template type (V3 bypasses this — always INTERACTIVE_DIAGRAM)

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| RT-1 | ~445 | MEDIUM | `FORCE_TEMPLATE` override reads from environment/config, but no validation that template exists in TEMPLATE_REGISTRY | If FORCE_TEMPLATE="INVALID_TYPE", no error — downstream gets undefined template. |
| RT-2 | ~687 | LOW | `validate_routing_decision()` function exists but never called | Dead code. Validation logic (confidence check, template existence) wasted. |
| RT-3 | ~75 | HIGH | TEMPLATE_REGISTRY has `INTERACTIVE_DIAGRAM` key, but V3 graph still routes through router which outputs `LABEL_DIAGRAM` | V3 pipeline should hardcode template_type or router should detect V3 preset. Currently depends on downstream agents ignoring this field. |
| RT-4 | ~460 | LOW | Router confidence score not used by any downstream consumer | Observability data only. Not a bug but wasted computation. |

---

## Phase 1: Game Design (ReAct + Validator + Retry)

### 4. game_designer_v3_agent

- **File:** `backend/app/agents/game_designer_v3.py`
- **Class:** `GameDesignerV3(ReActAgent)`
- **Config:** `max_iterations=6`, `temperature=0.7`
- **Reads:** `enhanced_question`, `subject`, `blooms_level`, `domain_knowledge` (via context), `canonical_labels` (via context), `learning_objectives`, `pedagogical_context`, `design_validation_v3` (on retry), `_v3_design_retries`
- **Writes:** `game_design_v3` (GameDesignV3Slim dict), `current_agent`

**Tools (5):**

| Tool | Type | Input | Output |
|------|------|-------|--------|
| `analyze_pedagogy` | LLM+context | question, subject, blooms_level, learning_objectives | Bloom's alignment, content type, recommended mechanics |
| `check_capabilities` | Deterministic | (none) | Frontend capability matrix |
| `get_example_designs` | Deterministic | question_type, blooms_level, domain | 3-5 example game designs |
| `validate_design` | Deterministic | design_dict | {valid, score, issues} |
| `submit_game_design` | Schema-as-tool | Full GameDesignV3Slim dict | {status, summary} |

**GameDesignV3Slim schema:** title, pedagogical_reasoning, learning_objectives, labels (zone_labels + distractor_labels), scenes[] (scene_number, title, visual_description, mechanics[]), scene_transitions[], theme, difficulty, estimated_duration_minutes

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| GD-1 | ~149 | MEDIUM | Retry context includes `design_validation_v3` issues but NOT the previous `game_design_v3` dict | LLM knows what failed but can't compare to its previous design. May regenerate identical design or drift in wrong direction. |
| GD-2 | ~238 | HIGH | `parse_final_result()` checks submit_game_design result for `status=="accepted"` — if `status=="rejected"`, falls back to JSON extraction | JSON extraction may extract the same rejected design from conversation history -> infinite retry with same bad design. |
| GD-3 | ~251 | MEDIUM | `extract_json_from_response()` uses balanced brace matching; if LLM returns partial JSON, extraction may fail silently | `game_design_v3` set to None. Downstream design_validator receives None -> crashes or proceeds with missing design. |
| GD-4 | ~238-240 | HIGH | Re-validation of submit_game_design args: if Pydantic validation fails, design_dict used **as-is without schema guarantees** | Downstream agents may crash on missing required fields (e.g., no `scenes` array). |
| GD-5 | ~175 | MEDIUM | `check_capabilities` tool returns static capability matrix — doesn't reflect actual mechanic implementation status | Reports all 10 mechanic types as "supported" even though only drag_drop works end-to-end. LLM designs games with broken mechanics. |
| GD-6 | ~195 | LOW | `get_example_designs` returns examples that may not match current Pydantic schema version | If schema evolved but examples didn't, LLM may follow outdated patterns. |

---

### 5. design_validator_agent

- **File:** `backend/app/agents/design_validator.py`
- **Type:** Deterministic (no LLM)
- **Reads:** `game_design_v3`, `_v3_design_retries`
- **Writes:** `design_validation_v3` ({passed, score, issues}), `_v3_design_retries` (incremented)
- **Passing criteria:** Score >= 0.7 AND no "FATAL:" prefix in issues

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| DV-1 | ~48-50 | MEDIUM | Missing title -> -0.2 score deduction but can still pass (0.8+) | Frontend crashes trying to render game with no title. Should be FATAL. |
| DV-2 | ~52-54 | -- | No scenes -> immediate return with 0.0 score | Correct behavior. |
| DV-3 | ~72-74 | MEDIUM | Zone labels < 3 -> warning with -0.05 deduction | 2-label drag_drop passes (0.95 score). Trivially easy game. No pedagogical constraint based on Bloom's level. |
| DV-4 | ~100-167 | HIGH | Mechanic-specific validation incomplete: trace_path checks `path_config.waypoints` exist but doesn't validate waypoint labels are in zone_labels | Scene can reference non-existent zones. trace_path game may have waypoints pointing to nothing. |
| DV-5 | ~117-123 | HIGH | click_to_identify checks prompts/click_options exist but doesn't validate click_options are valid zone labels | Prompts like "Click on XYZ" where XYZ doesn't match any zone. |
| DV-6 | ~186-204 | MEDIUM | Label-scene consistency: checks invalid references but doesn't check if distractor_labels are ever used in scenes | Dead distractors add confusion without pedagogical purpose. |
| DV-7 | ~207-233 | MEDIUM | Hierarchy validation checks parent/child existence but **no cycle detection** | parent A -> child B and parent B -> child A causes frontend updateVisibleZones() to enter undefined behavior. |
| DV-8 | ~237-246 | MEDIUM | Transition validation only checks from_scene/to_scene exist — doesn't validate trigger/threshold values | `trigger="score_threshold", threshold=1000` when max_score=100 -> impossible transition. |
| DV-9 | ~258-259 | LOW | `has_fatal` check is case-sensitive: `any("FATAL:" in i for i in issues)` | If issue logged as "fatal:" (lowercase), not detected. Standardize issue prefixes. |

---

## Phase 2: Scene Architecture (ReAct + Validator + Retry)

### 6. scene_architect_v3_agent

- **File:** `backend/app/agents/scene_architect_v3.py`
- **Class:** `SceneArchitectV3(ReActAgent)`
- **Config:** `max_iterations=8`, `temperature=0.5`
- **Model:** MUST use `gemini-2.5-pro` (flash stops at 3 iterations without calling submit)
- **Reads:** `game_design_v3`, `domain_knowledge` (via context), `canonical_labels`, `scene_validation_v3` (on retry), `_v3_scene_retries`
- **Writes:** `scene_specs_v3` (List[SceneSpecV3 dict]), `current_agent`

**Tools (4):**

| Tool | Type | Input | Output |
|------|------|-------|--------|
| `get_zone_layout_guidance` | LLM | visual_description, labels_list | Zone positions, shapes, difficulty |
| `get_mechanic_config_schema` | Deterministic | mechanic_type | Config schema + example |
| `validate_scene_spec` | Deterministic | scene_spec_dict | {valid, score, issues} |
| `submit_scene_specs` | Schema-as-tool | List[SceneSpecV3] | {status, summary} |

**SceneSpecV3 schema:** scene_number, title, image_description, image_requirements, image_style, zones[] (zone_id, label, position_hint, description, hint, difficulty 1-5), mechanic_configs[] (type, zone_labels_used, config dict), mechanic_data (dict), zone_hierarchy[] (parent-child)

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| SA-1 | ~113-128 | LOW | Distractor label extraction: `if isinstance(dl, dict)` — if distractor_labels is list of Pydantic models (not dicts), nothing appended | Silent loss of distractors in prompt. LLM may not include distractors in scene design. |
| SA-2 | ~131-151 | MEDIUM | If mechanics list is empty, no error signal — agent told "Mechanics: []" | LLM may hallucinate mechanics or return empty specs. No validation pre-prompt. |
| SA-3 | ~170-180 | MEDIUM | Retry feedback includes issues but not previous scene specs | Agent can't compare to previous attempt. May regenerate identical failing specs. |
| SA-4 | ~231-239 | HIGH | `submit_scene_specs` re-validation: if Pydantic validation fails, spec_dict added **as-is** without schema guarantees | Downstream validators/agents may crash on malformed specs. Silent pass of invalid data. |
| SA-5 | ~268-274 | HIGH | All extraction strategies fail -> `scene_specs_v3` set to None. No retry loop in graph for this case | Graph proceeds to interaction_designer with None scene_specs -> crash. |

---

### 7. scene_validator_agent

- **File:** `backend/app/agents/scene_validator.py`
- **Type:** Deterministic
- **Reads:** `scene_specs_v3`, `game_design_v3`, `_v3_scene_retries`
- **Writes:** `scene_validation_v3` ({passed, score, issues}), `_v3_scene_retries` (incremented)

**Validation gaps (via `validate_scene_specs()` in `schemas/scene_spec_v3.py`):**

| # | Severity | Missing Check | Impact |
|---|----------|---------------|--------|
| SV-1 | HIGH | No validation that zone count matches expected labels from game_design_v3 | Scene with 3 zones for 10 labels passes — game unplayable. |
| SV-2 | HIGH | No validation that mechanic_configs have all required fields for their type | trace_path without waypoints, sequencing without correct_order pass silently. |
| SV-3 | MEDIUM | No validation that zones don't overlap excessively | Multiple zones at same coordinates. Frontend renders stacked, unclickable zones. |
| SV-4 | MEDIUM | No validation that image_description is non-empty | Asset generator gets blank query -> searches random image. |
| SV-5 | MEDIUM | No cross-scene zone ID uniqueness check | Two scenes with `zone_1` confuse blueprint assembler. |

---

## Phase 3: Interaction Design (ReAct + Validator + Retry)

### 8. interaction_designer_v3_agent

- **File:** `backend/app/agents/interaction_designer_v3.py`
- **Class:** `InteractionDesignerV3(ReActAgent)`
- **Config:** `max_iterations=8`, `temperature=0.5`
- **Model:** MUST use `gemini-2.5-pro`
- **Reads:** `game_design_v3`, `scene_specs_v3`, `domain_knowledge` (via context), `interaction_validation_v3` (on retry), `_v3_interaction_retries`
- **Writes:** `interaction_specs_v3` (List[InteractionSpecV3 dict]), `current_agent`

**Tools (4):**

| Tool | Type | Input | Output |
|------|------|-------|--------|
| `get_scoring_templates` | Deterministic | mechanic_type, difficulty_level | Scoring templates |
| `generate_misconception_feedback` | LLM | labels, subject, distractor_feedback_context | Misconception feedback |
| `validate_interactions` | Deterministic | interaction_spec_dict | {valid, score, issues} |
| `submit_interaction_specs` | Schema-as-tool | List[InteractionSpecV3] | {status, summary} |

**CRITICAL NOTE:** scoring_data and feedback_data are Lists from the LLM but MUST be converted to Dict keyed by mechanic_type in blueprint_assembler_tools.py

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| ID-1 | ~125-128 | LOW | Distractor info concatenated as "text: explanation" string instead of structured JSON | LLM may not parse reliably. Better to pass structured data. |
| ID-2 | ~129-136 | MEDIUM | Zone labels extraction: if zone dict lacks "label" field, empty string appended | Zone count may not match zone_labels in prompt. Silent mismatch. |
| ID-3 | ~152-160 | MEDIUM | Retry feedback includes validation issues but not previous interaction_specs_v3 | Same problem as GD-1 and SA-3: can't compare to previous attempt. |
| ID-4 | ~215-223 | HIGH | `submit_interaction_specs` re-validation lenient — fails validation -> added as-is | Same pattern as SA-4. Invalid specs pass silently. |
| ID-5 | ~240 | MEDIUM | Extracted specs checked for scene_number + scoring + feedback — partial specs (only scene_number) pass | Incomplete interaction specs reach blueprint assembler. |

---

### 9. interaction_validator_agent

- **File:** `backend/app/agents/interaction_validator.py`
- **Type:** Deterministic
- **Reads:** `interaction_specs_v3`, `scene_specs_v3`, `game_design_v3`, `_v3_interaction_retries`
- **Writes:** `interaction_validation_v3`, `_v3_interaction_retries`

**Validation gaps (via `validate_interaction_specs()` in `schemas/interaction_spec_v3.py`):**

| # | Severity | Missing Check | Impact |
|---|----------|---------------|--------|
| IV-1 | HIGH | No mechanic-specific feedback validation (every mechanic_type should have scoring AND feedback) | Mechanic with scoring but no feedback -> silent failures in frontend. |
| IV-2 | HIGH | No distractor feedback validation (each distractor label should have an explanation) | Distractors placed without educational feedback. |
| IV-3 | MEDIUM | No multi-mechanic mode_transitions validation for multi-mechanic scenes | Multi-mechanic scene without transitions -> stuck in first mechanic forever. |
| IV-4 | MEDIUM | Mechanic-aware completion trigger validation added (F3 fix) but not comprehensive | Only validates trigger names, not trigger_values (e.g., percentage=200 passes). |

---

## Phase 4: Asset Generation (ReAct, no validator)

### 10. asset_generator_v3_agent

- **File:** `backend/app/agents/asset_generator_v3.py`
- **Class:** `AssetGeneratorV3(ReActAgent)`
- **Config:** `max_iterations=8`, `temperature=0.3`, `tool_timeout=120.0`
- **Reads:** `scene_specs_v3`, `game_design_v3`, `enhanced_question`, `subject`, `domain_knowledge`, `canonical_labels`
- **Writes:** `generated_assets_v3` (Dict[scene_number -> asset bundle]), `diagram_image` (backward compat), `diagram_zones` (backward compat)

**Tools (5):**

| Tool | Type | Input | Output |
|------|------|-------|--------|
| `search_diagram_image` | Web search | query, style_hints, prefer_unlabeled | {success, image_url, local_path, source, is_labeled} |
| `generate_diagram_image` | Gemini Imagen | description, reference_image_url, style | {success, image_path, image_url} |
| `detect_zones` | Vision models | image_path_or_url, labels, detection_method | {success, zones[]} |
| `generate_animation_css` | Deterministic | animation_type, duration_ms | {css_class, keyframes} |
| `submit_assets` | Schema-as-tool | assets dict | {status, summary, issues} |

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| AG-1 | ~32-40 | HIGH | System prompt says "CLEAN UNLABELED" image required — but no validation that generated image is actually unlabeled | Generated image may have text labels -> frontend overlays drag-drop labels on top of existing text -> visual conflict. |
| AG-2 | ~56-62 | MEDIUM | Zone detection retry strategy described in prompt but no fallback if ALL methods miss 50%+ of labels | Silent partial zone detection — agent submits what it has. Blueprint has incomplete zones. |
| AG-3 | ~89-156 | MEDIUM | `build_task_prompt()` doesn't validate scene_specs format — assumes `scene_specs[i].get("zones", [])` returns list of dicts | If zones is None or Pydantic model, extraction fails. Silent empty zone_labels in prompt. |
| AG-4 | ~186-261 | HIGH | `parse_final_result()` Strategy 3 (`_reconstruct_from_tool_results`) hardcodes `current_scene = "1"` | For multi-scene games, ALL zones assigned to scene "1". Scenes 2+ have no zones. |
| AG-5 | ~231 | MEDIUM | Strategy 1 assumes `tc.arguments.get("scenes", {})` returns dict — if scenes is list, reconstruction fails silently | Multi-scene JSON from LLM may use array instead of dict. |
| AG-6 | ~243-244 | HIGH | First scene extraction: if `generated_assets` is empty, `diagram_image` and `diagram_zones` not set | Backward compat fields skipped -> blueprint_assembler may expect them and crash. |
| AG-7 | ~289-296 | MEDIUM | `submit_assets` tool: if status="rejected", still tries to use input scenes | No re-attempt or escalation on rejection. |
| AG-8 | -- | CRITICAL | **Only generates drag_drop assets.** No tools for waypoints (trace_path), sequence items (sequencing), identification prompts (click_to_identify), functional descriptions (description_matching) | All non-drag_drop mechanics get zero mechanic-specific assets. Games are unplayable for these mechanics. |

---

## Phase 5: Blueprint Assembly (ReAct, no validator)

### 11. blueprint_assembler_v3_agent

- **File:** `backend/app/agents/blueprint_assembler_v3.py`
- **Class:** `BlueprintAssemblerV3(ReActAgent)`
- **Reads:** `game_design_v3`, `scene_specs_v3`, `interaction_specs_v3`, `generated_assets_v3`
- **Writes:** `blueprint` (InteractiveDiagramBlueprint dict), `generation_complete: True`

**Tools (4):**

| Tool | Type | Input | Output |
|------|------|-------|--------|
| `assemble_blueprint` | Deterministic | (reads v3 context) | blueprint_dict |
| `validate_blueprint` | Deterministic | blueprint_dict | {valid, score, issues} |
| `repair_blueprint` | LLM fallback | blueprint_dict, issues | repaired blueprint |
| `submit_blueprint` | Schema-as-tool | blueprint | {status, summary} |

**CRITICAL:** `parse_final_result()` MUST set `generation_complete: True`, otherwise routes/generate.py marks run as "error".

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| BA-1 | ~252-269 | HIGH | Legacy assembler only uses `diagram_zones` (backward compat field for scene 1). Multi-scene games have zones silently dropped for scenes 2+ | Only scene 1 has zones. Scene 2+ blueprints have empty zone arrays. |
| BA-2 | ~87-90 | MEDIUM | `_assemble_zones()` builds detected_map keyed by label — if two zones have same label (parent-child hierarchy), map collision | Only one zone survives. Parent "Ventricle" and child "Ventricle" -> second lost. |
| BA-3 | ~100-104 | MEDIUM | Parent-child mapping only from hierarchy groups — group_only_labels parent-child relationships not established | If hierarchy is not from explicit groups, parent_map is empty. |
| BA-4 | ~106-119 | MEDIUM | group_only_labels assembled first, then zone_labels — ordering assumes no cross-reference | group_only parent_id won't match if parent is in zone_labels (assembled later). |
| BA-5 | ~122-137 | MEDIUM | Parent ID generation uses `_make_id(parent_label)` — if parent_label not in scene_labels, parent_id points to nonexistent zone | Frontend: child zone -> parent_zone_id -> lookup fails -> zone orphaned. |
| BA-6 | ~328-347 | HIGH | Post-assembly zone coordinate post-processing: assumes `coordinates` is dict — if None or list, points field not set | Frontend expects `zone.points` for polygons. If not set, polygon zones fail silently (fallback to circle). |
| BA-7 | ~325-327 | LOW | `total_max_score` fallback: if 0, defaults to `len(global_labels) * 10` — if label_count=0, total_max_score=0 | Broken scoring with zero labels. |
| BA-8 | ~349 | HIGH | Returned blueprint dict NOT validated against InteractiveDiagramBlueprint schema | Missing required fields -> frontend crash. No schema enforcement before writing to state. |

---

## Graph Wiring & Retry Loops

### 12. graph.py — `create_v3_graph()`

- **File:** `backend/app/agents/graph.py` (~lines 1896-2011)

**Graph Wiring Diagram:**
```
Phase 0:    input_enhancer -> domain_knowledge_retriever -> router
                                                             |
Phase 1:    game_designer_v3 <--retry--+                     |
                |                       |                    |
            design_validator ----------+                     |
                | (passed or retries>=2)                     |
Phase 2:    scene_architect_v3 <--retry--+                   |
                |                         |                  |
            scene_validator -------------+                   |
                | (passed or retries>=2)                     |
Phase 3:    interaction_designer_v3 <--retry--+              |
                |                              |             |
            interaction_validator -------------+             |
                | (passed or retries>=2)                     |
Phase 4:    asset_generator_v3                               |
                |                                            |
Phase 5:    blueprint_assembler_v3 -> END
```

**Bugs:**

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| GR-1 | ~1973-1980 | MEDIUM | Design retry loop: no mechanism to prevent exact same design re-generation | If game_designer_v3 produces identical design, wastes 2 LLM calls before max retries. |
| GR-2 | ~2008 | HIGH | blueprint_assembler_v3 -> END with NO validator after it | If blueprint is invalid (missing zones, bad scoring, schema mismatch), pipeline silently outputs broken blueprint. Should have blueprint_validator node. |
| GR-3 | ~1975,1986,1997 | MEDIUM | Retry routing functions — when retries maxed, proceeds to next phase with potentially bad data | Should signal error state or at minimum log WARNING that validation failed but proceeding. |
| GR-4 | -- | HIGH | No explicit "fail" or "escalate_to_human" terminal state | All retry exhaustions silently proceed. No mechanism to abort pipeline on critical validation failure. |

---

## Infrastructure

### 13. react_base.py — ReAct Loop Implementation

- **File:** `backend/app/agents/react_base.py`

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| RB-1 | ~278-287 | LOW | Tool metrics assumes `tr.status.value` is valid enum — if tr is None, crashes | Caught by outer try-except but observability lost. |
| RB-2 | ~290-298 | MEDIUM | `contextvars.ContextVar` persists across async boundaries but if tool creates new task, context may not propagate | Metrics lost in spawned tasks. |

---

### 14. v3_context.py — Context Injection Layer

- **File:** `backend/app/tools/v3_context.py`

| # | Line | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| VC-1 | ~30-43 | MEDIUM | Missing fields in context injection: `_v3_*_retries`, validation results | Tools can't access retry context to adapt behavior on retries. |
| VC-2 | ~34 | MEDIUM | `canonical_labels` injected but `hierarchical_relationships` and `acceptable_variants` NOT injected | Tools missing hierarchy and variant data. Asset generator can't use variants for fuzzy matching. |

---

## Schema Validation Gaps

### 15. Schema files — Cross-cutting issues

| # | File | Severity | Issue | Impact |
|---|------|----------|-------|--------|
| SC-1 | `game_design_v3.py` | MEDIUM | `LabelDesign.zone_labels: List[str]` — no uniqueness validation, no non-empty string validation | LLM may return `["", "Ventricle", " ", "Heart"]` — empty labels pass. |
| SC-2 | `game_design_v3.py` | MEDIUM | No validation that zone_labels_in_scene are subsets of global zone_labels | Scene can reference undefined zones. |
| SC-3 | `scene_spec_v3.py` | MEDIUM | ZoneSpecV3 coordinates: no range validation (0-100% for normalized coords) | Zones at (1000, 1000) -> off-screen. |
| SC-4 | `interaction_spec_v3.py` | LOW | MechanicFeedbackV3 fields not validated for non-empty strings | Feedback could be "" -> frontend shows empty message. |
| SC-5 | `blueprint_schemas.py` | MEDIUM | IDZone points: no validation of polygon closure (first point != last point) | Polygon may not render correctly. |

---

## V3-Specific AgentState Fields

| Field | Type | Writer | Reader(s) | Risk |
|-------|------|--------|-----------|------|
| `game_design_v3` | Dict/None | game_designer_v3 | design_validator, scene_architect_v3, interaction_designer_v3, blueprint_assembler_v3 | If None (extraction failed), all downstream crash |
| `design_validation_v3` | Dict/None | design_validator | game_designer_v3 (retry) | Retry gets validation but not previous design |
| `_v3_design_retries` | int | design_validator | validator, router | Counter only, no escalation on max |
| `scene_specs_v3` | List[Dict]/None | scene_architect_v3 | scene_validator, interaction_designer_v3, asset_generator_v3, blueprint_assembler_v3 | If None or malformed, 4 downstream agents fail |
| `scene_validation_v3` | Dict/None | scene_validator | scene_architect_v3 (retry) | Same retry issue |
| `_v3_scene_retries` | int | scene_validator | validator, router | Same |
| `interaction_specs_v3` | List[Dict]/None | interaction_designer_v3 | interaction_validator, blueprint_assembler_v3 | If None, blueprint assembly crashes |
| `interaction_validation_v3` | Dict/None | interaction_validator | interaction_designer_v3 (retry) | Same |
| `_v3_interaction_retries` | int | interaction_validator | validator, router | Same |
| `generated_assets_v3` | Dict/None | asset_generator_v3 | blueprint_assembler_v3 | Multi-scene assets lost in backward compat extraction |
| `canonical_labels` | List[str] | domain_knowledge_retriever | game_designer_v3, scene_architect_v3, asset_generator_v3 (via context) | If empty, all V3 agents lack label guidance |
| `content_characteristics` | -- | (nested in domain_knowledge) | NOT ACCESSIBLE top-level | V3 agents can't read it |
| `blueprint` | Dict/None | blueprint_assembler_v3 | routes/generate.py | Not validated against schema |
| `generation_complete` | bool | blueprint_assembler_v3 | routes/generate.py | MUST be True or run marked "error" |

---

## Silent Failure Catalog

| Failure | Trigger | Consequence | Detectable? |
|---------|---------|-------------|-------------|
| Empty canonical_labels | DK retriever returns malformed JSON | All V3 agents design without label guidance | Only via observability — no error signal |
| None game_design_v3 | Game designer JSON extraction fails | Scene architect crashes or proceeds with None | Crash visible in logs, but no graceful handler |
| Malformed scene_specs | Scene architect re-validation fails silently | Invalid specs pass to interaction designer | Not detectable — no error signal |
| Missing zones for scenes 2+ | Asset generator reconstructs all to scene "1" | Multi-scene games only have scene 1 assets | Frontend shows blank diagram for scenes 2+ |
| Blueprint not validated | No validator after blueprint_assembler_v3 | Invalid blueprint reaches frontend | Frontend crash — visible to user |
| generation_complete not set | parse_final_result logic error | Run marked as "error" by routes/generate.py | Visible in run status but confusing error message |
| Retry exhaustion | 2+ validation failures | Pipeline proceeds with bad data | No signal — looks like success but game is broken |

---

## Context Injection System

**File:** `backend/app/tools/v3_context.py`

All V3 tools read state via `get_v3_tool_context()` which is set by agents before running via `set_v3_tool_context()`.

**Injected fields:**
- `domain_knowledge`, `canonical_labels`, `subject`, `question_text`, `learning_objectives`
- `game_design_v3`, `scene_specs_v3`, `interaction_specs_v3`, `generated_assets_v3`

**Missing fields (should be injected):**
- `content_characteristics` (nested in domain_knowledge)
- `hierarchical_relationships` (nested in domain_knowledge)
- `acceptable_variants` (nested in domain_knowledge)
- `_v3_*_retries` (retry counters)
- `*_validation_v3` (validation results for tool adaptation)

---

## Critical Implementation Notes

1. **Model assignment:** scene_architect_v3 + interaction_designer_v3 MUST use gemini-2.5-pro. Flash doesn't follow multi-tool workflows.
2. **scoring_data/feedback_data:** Must be converted List->Dict keyed by mechanic_type before blueprint serialization. Lists crash on `.get()`.
3. **generation_complete flag:** Must be set True by blueprint_assembler_v3 in `parse_final_result()`, otherwise routes/generate.py marks run as "error".
4. **Zone coordinates:** Frontend expects `{x, y, radius}` (circle) or `{points: [[x,y],...]}` (polygon). Use `_normalize_coordinates()`.
5. **Retry limits:** Each phase allows max 2 retries. After 2 failures, forces proceeding with potentially bad data.
6. **ReAct loop:** Breaks when agent calls submit_* tool or reaches max_iterations.
7. **Re-validation pattern:** All ReAct agents have lenient re-validation (Pydantic fail -> use as-is). This is a systemic vulnerability.
8. **Backward compat fields:** `diagram_image` and `diagram_zones` only capture scene 1. Multi-scene games lose scenes 2+.

---

## Activation

```json
POST /generate
{
  "question_text": "...",
  "config": { "pipeline_preset": "v3" }
}
```

---

## Consolidated Bug Count

| Component | CRITICAL | HIGH | MEDIUM | LOW | Total |
|-----------|----------|------|--------|-----|-------|
| input_enhancer | 0 | 1 | 2 | 1 | 4 |
| domain_knowledge_retriever | 0 | 3 | 3 | 1 | 7 |
| router | 0 | 1 | 1 | 2 | 4 |
| game_designer_v3 | 0 | 2 | 3 | 1 | 6 |
| design_validator | 0 | 2 | 5 | 1 | 8 |
| scene_architect_v3 | 0 | 2 | 2 | 1 | 5 |
| scene_validator | 0 | 2 | 3 | 0 | 5 |
| interaction_designer_v3 | 0 | 1 | 3 | 1 | 5 |
| interaction_validator | 0 | 2 | 2 | 0 | 4 |
| asset_generator_v3 | 1 | 3 | 4 | 0 | 8 |
| blueprint_assembler_v3 | 0 | 3 | 4 | 1 | 8 |
| graph.py | 0 | 2 | 2 | 0 | 4 |
| react_base.py | 0 | 0 | 1 | 1 | 2 |
| v3_context.py | 0 | 0 | 2 | 0 | 2 |
| Schemas | 0 | 0 | 4 | 1 | 5 |
| **Total** | **1** | **24** | **41** | **11** | **77** |
