# V3 Pipeline Complete Execution Graph Audit

**Date:** 2026-02-11
**Scope:** Complete V3 pipeline topology, all agents, all tools, ReAct internals, state flow

---

## 1. TOP-LEVEL GRAPH TOPOLOGY

```
                    ┌─────────────────────────────────────────┐
                    │  create_v3_graph() — graph.py:1901      │
                    └─────────────────────────────────────────┘

Entry: router
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 1: Game Design                                         │
│                                                              │
│   game_designer_v3 ──► design_validator ──┐                  │
│        ▲                                  │                  │
│        │     ┌────────────────────────────┘                  │
│        │     │  _v3_design_validation_router                 │
│        │     │  (graph.py:1862)                              │
│        │     │                                               │
│        └─────┤  IF !passed AND retries < 2 → RETRY          │
│              │  ELSE → scene_architect_v3                    │
│              └───────────────────────────────────────────►   │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 2: Scene Architecture                                  │
│                                                              │
│   scene_architect_v3 ──► scene_validator ──┐                 │
│        ▲                                   │                 │
│        │     ┌─────────────────────────────┘                 │
│        │     │  _v3_scene_validation_router                  │
│        │     │  (graph.py:1875)                              │
│        │     │                                               │
│        └─────┤  IF !passed AND retries < 2 → RETRY          │
│              │  ELSE → interaction_designer_v3               │
│              └───────────────────────────────────────────►   │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 3: Interaction Design                                  │
│                                                              │
│   interaction_designer_v3 ──► interaction_validator ──┐      │
│        ▲                                              │      │
│        │     ┌────────────────────────────────────────┘      │
│        │     │  _v3_interaction_validation_router             │
│        │     │  (graph.py:1888)                              │
│        │     │                                               │
│        └─────┤  IF !passed AND retries < 2 → RETRY          │
│              │  ELSE → asset_generator_v3                    │
│              └───────────────────────────────────────────►   │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 4: Asset Generation (NO VALIDATOR)                     │
│                                                              │
│   asset_generator_v3                                         │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ PHASE 5: Blueprint Assembly (NO VALIDATOR)                   │
│                                                              │
│   blueprint_assembler_v3 ──► END                             │
└──────────────────────────────────────────────────────────────┘
```

### Node Registration (graph.py:1949-1964)

| Node Name | Agent Function | Wrapped | Timeout |
|-----------|---------------|---------|---------|
| `game_designer_v3` | `game_designer_v3_agent` | Yes | 120s |
| `design_validator` | `design_validator_agent` | Yes | 30s |
| `scene_architect_v3` | `scene_architect_v3_agent` | Yes | 90s |
| `scene_validator` | `scene_validator_agent` | Yes | 30s |
| `interaction_designer_v3` | `interaction_designer_v3_agent` | Yes | 90s |
| `interaction_validator` | `interaction_validator_agent` | Yes | 30s |
| `asset_generator_v3` | `asset_generator_v3_agent` | Yes | 600s |
| `blueprint_assembler_v3` | `blueprint_assembler_v3_agent` | Yes | 60s |

### Edges (graph.py:1974-2013)

```
router → game_designer_v3                          (1974)
game_designer_v3 → design_validator                (1977)
design_validator → CONDITIONAL                     (1978-1987)
  ├─ game_designer_v3  (retry)
  └─ scene_architect_v3 (pass)
scene_architect_v3 → scene_validator               (1988)
scene_validator → CONDITIONAL                      (1989-1997)
  ├─ scene_architect_v3  (retry)
  └─ interaction_designer_v3 (pass)
interaction_designer_v3 → interaction_validator     (1999)
interaction_validator → CONDITIONAL                (2000-2008)
  ├─ interaction_designer_v3 (retry)
  └─ asset_generator_v3 (pass)
asset_generator_v3 → blueprint_assembler_v3        (2010)
blueprint_assembler_v3 → END                       (2013)
```

---

## 2. PER-AGENT DETAILED BREAKDOWN

### 2.1 game_designer_v3 (game_designer_v3.py — 370 lines)

| Property | Value |
|----------|-------|
| **Class** | `GameDesignerV3(ReActAgent)` |
| **max_iterations** | 6 |
| **tool_timeout** | 30s |
| **temperature** | 0.7 |
| **model** | gemini-2.5-pro (gemini_only preset) |
| **max_tokens** | 16384 |

**Tools (5):**
| Tool Name | Type | What It Does |
|-----------|------|-------------|
| `analyze_pedagogy` | Deterministic | Analyzes Bloom's level, content type, recommended mechanics |
| `check_capabilities` | Deterministic | Lists ready vs unsupported mechanics based on domain knowledge |
| `get_example_designs` | Deterministic | Returns few-shot example designs for similar questions |
| `validate_design` | Deterministic | Schema + rule validation, returns issues list |
| `submit_game_design` | Schema-as-tool | Accepts GameDesignV3Slim, validates and stores |

**build_task_prompt reads:**
- `enhanced_question` / `question` (150 chars)
- `subject`, `blooms_level`
- `domain_knowledge` (capped 2000 chars)
- `canonical_labels` (max 30)
- DK sub-fields: `sequence_flow_data`, `label_descriptions`, `comparison_data`, `content_characteristics`
- `learning_objectives`, `pedagogical_context`
- `design_validation_v3` + `_v3_design_retries` (retry feedback)

**parse_final_result strategies:**
1. `submit_game_design` tool call args (if status="accepted")
2. `extract_json_from_response()` from content
3. Error fallback

**Writes to state:**
- `game_design_v3` (GameDesignV3Slim dict with `_summary`)

---

### 2.2 design_validator (design_validator.py — 345 lines)

| Property | Value |
|----------|-------|
| **Type** | Deterministic (no LLM) |
| **Pass threshold** | score >= 0.7 AND no fatal issues |

**Validation checks:**
1. Title present (-0.2)
2. Scenes present (FATAL)
3. No label overlap (zone vs distractor)
4. >= 3 zone labels (-0.05)
5. Scene numbers sequential (FATAL)
6. Each scene has title + >= 1 mechanic
7. Mechanic types valid
8. Per-mechanic config checks (path_config, click_config, etc.)
9. Mechanics reference valid zone labels
10. >= 50% zone labels used
11. Hierarchy groups reference valid labels
12. Scene transitions reference valid scene numbers
13. Schema-level validation

**Writes to state:**
- `design_validation_v3` = `{passed: bool, score: float, issues: list}`
- `_v3_design_retries` (incremented)

---

### 2.3 scene_architect_v3 (scene_architect_v3.py — 414 lines)

| Property | Value |
|----------|-------|
| **Class** | `SceneArchitectV3(ReActAgent)` |
| **max_iterations** | 15 |
| **tool_timeout** | 60s |
| **temperature** | 0.5 |
| **model** | gemini-2.5-pro |

**Tools (5):**
| Tool Name | Type | What It Does |
|-----------|------|-------------|
| `get_zone_layout_guidance` | LLM call | Spatial position hints for zones |
| `get_mechanic_config_schema` | Deterministic | Returns JSON schema for mechanic config |
| `generate_mechanic_content` | LLM (some) | Populates mechanic-specific configs (waypoints, categories, etc.) |
| `validate_scene_spec` | Deterministic + auto-enrichment | Cross-checks zones, mechanics, hierarchy |
| `submit_scene_specs` | Schema-as-tool | Accepts List[SceneSpecV3] |

**build_task_prompt reads:**
- `game_design_v3._summary`, `.title`, `.labels`, `.scenes`
- `canonical_labels`
- `game_design_v3.difficulty`, `.labels.hierarchy`
- `scene_validation_v3` + `_v3_scene_retries` (retry feedback)

**parse_final_result strategies:**
1. `submit_scene_specs` tool call args (if status="accepted")
2. `extract_json_from_response()`
3. Recovery from tool call history:
   - First pass: enriched specs from `validate_scene_spec` tool results
   - Second pass: raw args from `validate_scene_spec` calls
   - Third pass: `submit_scene_specs` args (even if not accepted)

**Writes to state:**
- `scene_specs_v3` (List of SceneSpecV3 dicts)

---

### 2.4 scene_validator (scene_validator.py — 99 lines)

| Property | Value |
|----------|-------|
| **Type** | Deterministic (no LLM) |
| **Validation function** | `validate_scene_specs()` in scene_spec_v3.py |

**Cross-stage checks:**
1. Every game_design zone_label has a zone in scene_specs
2. Scene numbers match game_design scenes
3. Mechanic types match per scene
4. Zones have non-empty hints/descriptions
5. Image descriptions non-empty
6. Per-mechanic config requirements:
   - trace_path: waypoints
   - click_to_identify: prompts
   - sequencing: items + correct_order
   - sorting_categories: categories + items
   - description_matching: descriptions
   - memory_match: pairs
   - branching_scenario: nodes + start_node_id
   - compare_contrast: expected_categories

**Scoring:** `score = max(0, 1.0 - 0.15 * cross_issues - 0.05 * total_issues)`

**Writes to state:**
- `scene_validation_v3` = `{passed, score, issues}`
- `_v3_scene_retries` (incremented)

---

### 2.5 interaction_designer_v3 (interaction_designer_v3.py — 391 lines)

| Property | Value |
|----------|-------|
| **Class** | `InteractionDesignerV3(ReActAgent)` |
| **max_iterations** | 15 |
| **tool_timeout** | 60s |
| **temperature** | 0.5 |
| **model** | gemini-2.5-pro |

**Tools (5):**
| Tool Name | Type | What It Does |
|-----------|------|-------------|
| `get_scoring_templates` | Deterministic | Returns recommended scoring strategy per mechanic |
| `generate_misconception_feedback` | LLM | Generates misconception triggers for labels |
| `enrich_mechanic_content` | LLM | Generates enriched scoring, feedback, misconceptions per mechanic |
| `validate_interactions` | Deterministic + auto-enrichment | Checks scoring/feedback completeness |
| `submit_interaction_specs` | Schema-as-tool | Accepts List[InteractionSpecV3] |

**build_task_prompt reads:**
- `game_design_v3._summary`, `.labels`, `.scenes`
- `scene_specs_v3` (scene_number, title, zones, mechanic_configs)
- `game_design_v3.difficulty`, subject
- `interaction_validation_v3` + `_v3_interaction_retries` (retry feedback)

**parse_final_result strategies:**
Same 3-strategy pattern as scene_architect_v3.

**Writes to state:**
- `interaction_specs_v3` (List of InteractionSpecV3 dicts)

---

### 2.6 interaction_validator (interaction_validator.py — 713 lines)

| Property | Value |
|----------|-------|
| **Type** | Deterministic (no LLM) |
| **Validation function** | `validate_interaction_specs()` in interaction_spec_v3.py |

**Cross-stage checks:**
1. Every mechanic in every scene has scoring entry
2. Every mechanic has feedback (on_correct + on_incorrect)
3. >= 2 misconception feedbacks per scene
4. Mode transitions required for multi-mechanic scenes
5. Transition triggers valid per MECHANIC_TRIGGER_MAP
6. Mechanic-specific content (click prompts, descriptions, etc.)
7. Total max_score in range 50-500
8. Distractor feedback exists for all distractors

**Scoring:** `score = max(0, 1.0 - 0.1 * len(issues))`

**Writes to state:**
- `interaction_validation_v3` = `{passed, score, issues}`
- `_v3_interaction_retries` (incremented)

---

### 2.7 asset_generator_v3 (asset_generator_v3.py — 518 lines)

| Property | Value |
|----------|-------|
| **Class** | `AssetGeneratorV3(ReActAgent)` |
| **max_iterations** | 15 |
| **tool_timeout** | 120s |
| **temperature** | 0.3 |
| **model** | gemini-2.5-flash |

**Tools (5):**
| Tool Name | Type | What It Does |
|-----------|------|-------------|
| `search_diagram_image` | External (image retrieval) | Searches for reference image, auto-generates clean version |
| `generate_diagram_image` | External (Gemini Imagen) | AI-generates diagram from description |
| `detect_zones` | External (Qwen/Gemini/SAM3) | Detects interactive zones on clean image |
| `generate_animation_css` | Deterministic | Creates CSS animation specs |
| `submit_assets` | Deterministic | Accepts per-scene assets |

**build_task_prompt reads:**
- `scene_specs_v3`, `game_design_v3`
- `enhanced_question`, `subject`, `canonical_labels`
- Per-scene: image_description, image_requirements, zone labels, mechanic types

**parse_final_result strategies:**
1. `submit_assets` tool call args
2. `extract_json_from_response()`
3. Reconstruction from tool results (assigns images/zones to scenes by order)
4. Error fallback

**Writes to state:**
- `generated_assets_v3` = `{scenes: {"1": {diagram_image_url, zones, ...}}, metadata: {...}}`
- `diagram_image` (backward compat, from scene 1)
- `diagram_zones` (backward compat, from scene 1)

---

### 2.8 blueprint_assembler_v3 (blueprint_assembler_v3.py — 648 lines)

| Property | Value |
|----------|-------|
| **Class** | `BlueprintAssemblerV3(ReActAgent)` |
| **max_iterations** | 6 |
| **tool_timeout** | 30s |
| **temperature** | 0.2 |
| **model** | gemini-2.5-flash |

**Tools (4):**
| Tool Name | Type | What It Does |
|-----------|------|-------------|
| `assemble_blueprint` | Deterministic | Reads ALL upstream state, builds InteractiveDiagramBlueprint |
| `validate_blueprint` | Deterministic | Checks blueprint completeness |
| `repair_blueprint` | Deterministic | Fixes common issues (missing fields, coordinates, etc.) |
| `submit_blueprint` | Deterministic | Final submission, sets generation_complete |

**build_task_prompt reads:**
- `game_design_v3` (title, scenes count, labels)
- `scene_specs_v3` (total zones, mechanic configs)
- `interaction_specs_v3` (scoring/feedback counts)
- `generated_assets_v3` (scenes with images)

**Writes to state:**
- `blueprint` (InteractiveDiagramBlueprint JSON)
- `generation_complete` = True (CRITICAL for routes/generate.py)

---

## 3. REACT LOOP INTERNALS

### 3.1 ReActAgent Base Class (react_base.py — 444 lines)

```
ReActAgent.run(state, ctx)
  │
  ├─ get_tools() → registry.get(name) for each get_tool_names()
  ├─ build_full_system_prompt() → system_prompt + ReAct instructions + tool descriptions
  ├─ build_task_prompt(state) → task-specific prompt from state
  │
  ├─ llm.generate_with_tools_for_agent(
  │     agent_name, prompt, tools, system_prompt,
  │     max_iterations, mode="react", tool_timeout, step_callback
  │   )
  │   │
  │   └─ Returns ToolCallingResponse:
  │        content, model, tool_calls[], tool_results[],
  │        react_trace[], iterations, tokens, latency, stop_reason
  │
  ├─ _track_react_metrics(ctx, response)  [non-fatal]
  │
  └─ parse_final_result(response, state) → Dict[str, Any]
```

### 3.2 LLM Service ReAct Loop (llm_service.py)

```
_generate_with_tools_react(system_prompt, prompt, tools, max_iterations, tool_timeout)
  │
  FOR iteration = 1..max_iterations:
  │
  ├─ Call LLM with (system_prompt + accumulated_messages)
  │
  ├─ Extract THOUGHT from response
  │
  ├─ Extract TOOL CALL from response (if any)
  │     │
  │     ├─ IF no tool call → BREAK (final answer)
  │     │
  │     ├─ IF repeated tool call pattern (same tool+args 2x) → BREAK (no_progress)
  │     │
  │     └─ IF repeated thought → BREAK (thought_repetition)
  │
  ├─ Execute tool with timeout
  │     ├─ Lookup tool in registry
  │     ├─ Call tool function with arguments
  │     └─ Record result + latency
  │
  ├─ Append to trace (thought, action, observation)
  │
  └─ IF step_callback: emit LiveStepEvent
  │
  RETURN ToolCallingResponse
```

**Stop Conditions:**
1. No tool calls in response → final answer
2. Repeated tool call pattern (same tool+args twice) → no_progress
3. Repeated thought → thought_repetition
4. max_iterations reached → max_iterations

### 3.3 Key Dataclasses

```python
ToolCall:
  id: str
  name: str
  arguments: Dict[str, Any]

ToolResult:
  tool_call_id: str
  name: str
  result: Any
  status: SUCCESS | ERROR | TIMEOUT
  error: Optional[str]
  latency_ms: int

ReActStep:
  thought: str
  action: Optional[ToolCall]
  observation: Optional[str]
  iteration: int
```

---

## 4. TOOL IMPLEMENTATION DETAILS

### 4.1 Game Design Tools (game_design_v3_tools.py)

| Tool | Implementation | v3_context reads | Returns |
|------|---------------|------------------|---------|
| `analyze_pedagogy` | Deterministic heuristic | question, blooms_level, subject, content_characteristics | `{content_type, cognitive_demand, recommended_mechanics[], complexity}` |
| `check_capabilities` | Deterministic lookup | canonical_labels, sequence_flow_data, comparison_data, hierarchical_relationships | `{ready_types[], limited_types[], not_ready_types[], recommendation}` |
| `get_example_designs` | Deterministic | blooms_level, canonical_labels | `{examples: [{title, mechanics, scene_count, ...}]}` |
| `validate_design` | Deterministic | (reads from argument) | `{passed, score, issues[], suggestions[]}` |
| `submit_game_design` | Schema validation | (reads from argument) | `{status: "accepted", summary, scene_count}` |

### 4.2 Scene Architect Tools (scene_architect_tools.py)

| Tool | Implementation | v3_context reads | Returns |
|------|---------------|------------------|---------|
| `get_zone_layout_guidance` | LLM call | question, subject | `{positions: [{label, hint, rationale}]}` |
| `get_mechanic_config_schema` | Deterministic | (none) | `{mechanic_type, schema, defaults, example}` |
| `generate_mechanic_content` | LLM for some | game_design_v3, canonical_labels, sequence_flow_data | `{mechanic_type, config: {...populated...}}` |
| `validate_scene_spec` | Deterministic + auto-enrichment | game_design_v3 | `{passed, score, issues[], enriched_spec?}` |
| `submit_scene_specs` | Schema validation | (none) | `{status: "accepted", scene_count}` |

### 4.3 Interaction Designer Tools (interaction_designer_tools.py)

| Tool | Implementation | v3_context reads | Returns |
|------|---------------|------------------|---------|
| `get_scoring_templates` | Deterministic | (none) | `{mechanic_type, strategy, defaults}` |
| `generate_misconception_feedback` | LLM call | question, subject, canonical_labels | `{misconceptions: [{trigger, message}]}` |
| `enrich_mechanic_content` | LLM call | game_design_v3, scene_specs_v3 | `{scoring_rationale, recommended_scoring, enriched_feedback, misconceptions}` |
| `validate_interactions` | Deterministic + auto-enrichment | scene_specs_v3, game_design_v3 | `{passed, score, issues[], enriched_spec?}` |
| `submit_interaction_specs` | Schema validation | (none) | `{status: "accepted", scene_count}` |

### 4.4 Asset Generator Tools (asset_generator_tools.py)

| Tool | Implementation | v3_context reads | Returns |
|------|---------------|------------------|---------|
| `search_diagram_image` | External (image_retrieval + auto-clean) | subject, output_dir, run_id | `{image_url, local_path, cleaned, source}` |
| `generate_diagram_image` | External (Gemini Imagen) | output_dir, run_id | `{image_url, local_path, source: "generated"}` |
| `detect_zones` | External (Qwen/Gemini/SAM3) | (none) | `{zones: [{label, coordinates, shape}], method, count}` |
| `generate_animation_css` | Deterministic | (none) | `{animations: {...css specs...}}` |
| `submit_assets` | Deterministic + validation | game_design_v3 | `{status: "accepted", scenes, metadata}` |

### 4.5 Blueprint Assembler Tools (blueprint_assembler_tools.py)

| Tool | Implementation | v3_context reads | Returns |
|------|---------------|------------------|---------|
| `assemble_blueprint` | Deterministic (reads ALL state) | game_design_v3, scene_specs_v3, interaction_specs_v3, generated_assets_v3 | `{blueprint: InteractiveDiagramBlueprint, warnings[]}` |
| `validate_blueprint` | Deterministic | (from argument) | `{passed, score, issues[]}` |
| `repair_blueprint` | Deterministic | (from argument) | `{blueprint, repairs_made[]}` |
| `submit_blueprint` | Deterministic | (from argument) | `{status: "accepted", template_type}` |

---

## 5. STATE FIELD FLOW

```
PHASE 0 (Context Gathering — shared with other presets)
  input_enhancer → enhanced_question, subject, blooms_level
  domain_knowledge_retriever → domain_knowledge, canonical_labels
  router → template_type, _pipeline_preset

PHASE 1 (Game Design)
  game_designer_v3:
    READS: enhanced_question, subject, blooms_level, domain_knowledge,
           canonical_labels, learning_objectives, pedagogical_context,
           design_validation_v3 (retry), _v3_design_retries (retry)
    WRITES: game_design_v3

  design_validator:
    READS: game_design_v3
    WRITES: design_validation_v3, _v3_design_retries

PHASE 2 (Scene Architecture)
  scene_architect_v3:
    READS: game_design_v3, canonical_labels, domain_knowledge,
           scene_validation_v3 (retry), _v3_scene_retries (retry)
    WRITES: scene_specs_v3

  scene_validator:
    READS: scene_specs_v3, game_design_v3
    WRITES: scene_validation_v3, _v3_scene_retries

PHASE 3 (Interaction Design)
  interaction_designer_v3:
    READS: game_design_v3, scene_specs_v3, domain_knowledge, canonical_labels,
           interaction_validation_v3 (retry), _v3_interaction_retries (retry)
    WRITES: interaction_specs_v3

  interaction_validator:
    READS: interaction_specs_v3, scene_specs_v3, game_design_v3
    WRITES: interaction_validation_v3, _v3_interaction_retries

PHASE 4 (Asset Generation)
  asset_generator_v3:
    READS: game_design_v3, scene_specs_v3, interaction_specs_v3,
           domain_knowledge, canonical_labels, subject
    WRITES: generated_assets_v3, diagram_image (compat), diagram_zones (compat)

PHASE 5 (Blueprint Assembly)
  blueprint_assembler_v3:
    READS: game_design_v3, scene_specs_v3, interaction_specs_v3, generated_assets_v3
    WRITES: blueprint, generation_complete
```

---

## 6. CONTEXT INJECTION (v3_context.py)

`set_v3_tool_context(state)` copies these fields into contextvars:

| Context Key | Source State Field |
|-------------|-------------------|
| `question` | `enhanced_question` or `question_text` |
| `subject` | `subject` |
| `blooms_level` | `blooms_level` |
| `domain_knowledge` | `domain_knowledge` |
| `canonical_labels` | `canonical_labels` |
| `learning_objectives` | `learning_objectives` |
| `pedagogical_context` | `pedagogical_context` |
| `game_design_v3` | `game_design_v3` |
| `scene_specs_v3` | `scene_specs_v3` |
| `interaction_specs_v3` | `interaction_specs_v3` |
| `generated_assets_v3` | `generated_assets_v3` |
| `run_id` | `_run_id` |
| `output_dir` | `_output_dir` |
| `sequence_flow_data` | `domain_knowledge.sequence_flow_data` |
| `content_characteristics` | `domain_knowledge.content_characteristics` |
| `hierarchical_relationships` | `domain_knowledge.hierarchical_relationships` |
| `label_descriptions` | `domain_knowledge.label_descriptions` |
| `comparison_data` | `domain_knowledge.comparison_data` |

---

## 7. MODEL CONFIGURATION (agent_models.py)

### gemini_only preset (the V3 default)

| Agent | Model | Temperature | Max Tokens |
|-------|-------|-------------|------------|
| `game_designer_v3` | gemini-2.5-pro | 0.7 | 16384 |
| `scene_architect_v3` | gemini-2.5-pro | 0.5 (agent default) | - |
| `interaction_designer_v3` | gemini-2.5-pro | 0.5 (agent default) | - |
| `asset_generator_v3` | gemini-2.5-flash | 0.3 (agent default) | - |
| `blueprint_assembler_v3` | gemini-2.5-flash | 0.2 (agent default) | - |

---

## 8. INSTRUMENTATION REGISTRATION (instrumentation.py)

### Input Keys

| Agent | Registered Input Keys |
|-------|----------------------|
| `game_designer_v3` | enhanced_question, question, subject, blooms_level, domain_knowledge, canonical_labels, learning_objectives, pedagogical_context |
| `design_validator` | game_design_v3 |
| `scene_architect_v3` | game_design_v3, domain_knowledge, canonical_labels |
| `scene_validator` | scene_specs_v3, game_design_v3 |
| `interaction_designer_v3` | game_design_v3, scene_specs_v3, domain_knowledge, canonical_labels |
| `interaction_validator` | interaction_specs_v3, scene_specs_v3, game_design_v3 |
| `asset_generator_v3` | game_design_v3, scene_specs_v3, interaction_specs_v3, domain_knowledge, canonical_labels |
| `blueprint_assembler_v3` | game_design_v3, scene_specs_v3, interaction_specs_v3, generated_assets_v3 |

### Output Keys

| Agent | Registered Output Keys |
|-------|----------------------|
| `game_designer_v3` | game_design_v3 |
| `design_validator` | design_validation_v3 |
| `scene_architect_v3` | scene_specs_v3 |
| `scene_validator` | scene_validation_v3 |
| `interaction_designer_v3` | interaction_specs_v3 |
| `interaction_validator` | interaction_validation_v3 |
| `asset_generator_v3` | generated_assets_v3, diagram_image, diagram_zones |
| `blueprint_assembler_v3` | blueprint, template_type |

---

## 9. ARCHITECTURAL OBSERVATIONS

### No Validator After Phase 4 & 5
- `asset_generator_v3` → `blueprint_assembler_v3` → END
- No quality gate on generated assets or assembled blueprint
- If asset generation fails partially, blueprint assembler gets bad data

### Max Retries Exhausted = Silent Pass
- All three retry routers route to next phase when retries exhausted
- No error state — pipeline continues with potentially invalid data
- `design_validation_v3.passed` could be False when scene_architect starts

### Blueprint Assembler Has No Retry Loop
- If `assemble_blueprint` fails, there's `repair_blueprint` but no external retry
- If repair fails, pipeline ends with potentially broken blueprint

### Backward Compatibility Fields
- `diagram_image` and `diagram_zones` always populated from scene 1
- Multi-scene games only get scene 1 in these legacy fields
- Blueprint must handle multi-scene via `generated_assets_v3.scenes`

### Temperature Not Escalated on Retry
- Retry loops re-run the same agent with same temperature
- Could lead to repetitive failures (same model, same temp, slightly different prompt)
