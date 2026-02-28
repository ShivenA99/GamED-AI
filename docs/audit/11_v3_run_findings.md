# V3 Pipeline Run Findings — Run `29d63bf9` (Feb 11, 2026)

**Question**: "Label the main parts of a flower including the petals, sepals, stamen, pistil, anther, and filament on the diagram."
**Pipeline**: v3 preset
**Result**: 15/15 stages "success" — but output is broken
**Duration**: 456.7s (~7.6 min)
**Cost**: $0.36 (242,905 tokens)
**Process ID**: `2420f35b-b629-47e1-83c0-c46fabd5005f`

---

## Executive Summary

The pipeline completes all 15 stages with "success" status, but the resulting game is **unplayable**:
- Broken diagram image (external URL, not cleaned)
- 2 of 4 Scene 1 zone positions are null (label matching failure)
- Scenes 2 and 3 have zero zone positions and no diagram images
- No mechanic-specific configs (description_matching, hierarchical)
- `mechanic_type` missing from all game scenes
- `generation_complete` flag not set

**Root causes**: scene_architect_v3 and interaction_designer_v3 both produce `null` output (twice each). Pipeline continues anyway, leaving asset_generator and blueprint_assembler flying blind.

---

## Full Execution Trace

### Stage 1: input_enhancer (3.2s, gemini-2.5-flash-lite, 2466 tokens)
- **Input**: Raw question text
- **Output**: Enhanced question
- **Verdict**: OK

### Stage 2: domain_knowledge_retriever (8.1s, gemini-2.5-flash-lite, 2595 tokens)
- **Output**:
  - 9 canonical labels: `[Petal, Sepal, Stamen, Pistil, Anther, Filament, Stigma, Style, Ovary]`
  - Added 3 extra labels (Stigma, Style, Ovary) not in original question — good pedagogical enrichment
  - Hierarchy: Stamen→[Anther, Filament], Pistil→[Stigma, Style, Ovary]
  - Label descriptions populated for all 9 labels
  - 4 web sources retrieved
- **Verdict**: OK — solid context gathering

### Stage 3: router (1.3s, gemini-2.5-flash-lite, 2246 tokens)
- **Output**: `INTERACTIVE_DIAGRAM` template, confidence 0.9
- **Verdict**: OK

### Stage 4: game_designer_v3 (64.9s, gemini-2.5-pro, 50268 tokens, $0.098)
- **Output**: 3-scene game "Anatomy of a Flower"
  - Scene 1 "The Outer Flower" — `drag_drop` [Petal, Sepal, Stamen, Pistil]
  - Scene 2 "Reproductive Structures" — `hierarchical` + `drag_drop` [Stamen, Pistil, Anther, Filament, Stigma, Style, Ovary]
  - Scene 3 "What Do They Do?" — `description_matching` [all 9 labels]
  - 4 distractor labels: Leaf, Stem, Pollen, Root
- **Issues found**:
  - **[GD-1]** `description_matching` mechanic has empty config `{}` — no descriptions provided
  - **[GD-2]** `hierarchical` mechanic config only has `reveal_trigger`, missing `zone_groups` structure
  - **[GD-3]** `drag_drop` mechanics have completely empty config `{}`
- **Verdict**: Partially OK — good creative design but mechanic configs are hollow shells

### Stage 5: design_validator (0ms, no LLM)
- **Output**: `passed=true, score=0.9`
- **Warnings**:
  - "Scene 3 description_matching missing description_match_config"
  - "Only 0% of zone labels are used in mechanics. Unused: {all 9 labels}"
- **Issues found**:
  - **[DV-1]** Validator PASSES despite detecting missing mechanic configs (should fail or at least score lower)
  - **[DV-2]** "0% of zone labels are used in mechanics" — critical validation failure treated as warning
- **Verdict**: BROKEN — validator is too lenient, critical issues pass as warnings

### Stage 6: scene_architect_v3 — Pass 1 (68.4s, gemini-2.5-pro, 39928 tokens)
- **Output**: `scene_specs_v3 = null` (empty output after 68 seconds)
- **Issues found**:
  - **[SA-1]** Consumed 40K tokens and 68 seconds but produced NOTHING
  - **[SA-2]** ReAct trace not captured in output_snapshot (empty)
  - **[SA-3]** Likely never called `submit_scene_specs` tool, or `parse_final_result` failed silently
- **Verdict**: FAILED — total waste of 68s and $0.05

### Stage 7: scene_validator (0ms)
- **Output**: `passed=false, score=0.0` — "No scene_specs_v3 found in state"
- **Verdict**: Correctly detected failure

### Stage 8: scene_architect_v3 — Pass 2/Retry (5.3s, gemini-2.5-pro, 3087 tokens)
- **Output**: `scene_specs_v3 = null` again
- **ReAct trace**: 1 iteration, 0 tool calls
  - Agent wrote "ACTION: `get_zone_layout_guidance`..." as TEXT instead of making an actual tool call
  - Observation: "[FINAL ANSWER]" — treated its text as the final answer
- **Issues found**:
  - **[SA-4]** Agent writes tool calls as text instead of using function calling. Fundamental ReAct framework bug
  - **[SA-5]** Retry receives no feedback about WHY it failed (validator just says "not found")
- **Verdict**: FAILED — same root cause, agent confused about tool calling format

### Stage 9: scene_validator (0ms)
- **Output**: `passed=false` again
- **Verdict**: Correctly detected failure, but pipeline proceeds anyway

### Stage 10: interaction_designer_v3 — Pass 1 (83.4s, gemini-2.5-pro, 46940 tokens)
- **Input**: `scene_specs_v3 = None` (upstream failure)
- **ReAct trace** (8 iterations, hit max):
  - iter 0: `get_scoring_templates` for description_matching (Scene 1) ← WRONG, Scene 1 is drag_drop in game design
  - iter 1: `enrich_mechanic_content` for description_matching scoring
  - iter 2: `generate_misconception_feedback` for Petal, Sepal, Stamen, Pistil
  - iter 3: `validate_interactions` → FAILED (animation must be string, not object)
  - iter 4: `validate_interactions` → PASSED (fixed animation)
  - iter 5: `get_scoring_templates` for drag_drop (Scene 2)
  - iter 6: `enrich_mechanic_content` for drag_drop scoring
  - iter 7: `generate_misconception_feedback` for Anther, Filament, etc.
  - **HIT MAX ITERATIONS** — never processed Scene 3, never called `submit_interaction_specs`
- **Output**: `interaction_specs_v3 = None`
- **Issues found**:
  - **[ID-1]** 8 max_iterations insufficient for 3 scenes (each needs 4-5 tool calls → needs 12-15)
  - **[ID-2]** Agent chose `description_matching` for Scene 1 despite game_design saying `drag_drop` — no scene_specs to guide it
  - **[ID-3]** Never calls `submit_interaction_specs` because it runs out of iterations
  - **[ID-4]** 83 seconds and $0.07 spent producing nothing usable
- **Verdict**: FAILED — max_iterations too low for multi-scene games

### Stage 11: interaction_validator (0ms)
- **Output**: `passed=false` — "No interaction_specs_v3 found"
- **Verdict**: Correctly detected failure

### Stage 12: interaction_designer_v3 — Pass 2/Retry (82.5s, gemini-2.5-pro, 45247 tokens)
- **Exact same pattern**: 8 iterations, same tool calls, ran out before submitting
- **Output**: `interaction_specs_v3 = None` again
- **Issues found**:
  - **[ID-5]** Retry doesn't adjust strategy (e.g., process fewer scenes to fit within limit)
  - **[ID-6]** No context about previous failure passed to retry
- **Verdict**: FAILED — same root cause

### Stage 13: interaction_validator (0ms)
- **Output**: `passed=false` again
- Pipeline continues to asset generation with NO interaction specs

### Stage 14: asset_generator_v3 (109.3s, gemini-2.5-flash, 41131 tokens)
- **Input**: `scene_specs_v3 = None`, `interaction_specs_v3 = None`
- **ReAct trace** (6 iterations):
  - iter 0: `search_diagram_image` → Found AMNH flower image, downloaded locally. **Auto-clean triggered** → called `generate_diagram_image` internally
  - Auto-clean: `generate_diagram_image` → Gemini Imagen called, **image generated successfully** (`gemini_diagram_20260211_004549.png`) BUT **discarded** due to key mismatch (`image_path` vs `generated_path`)
  - iter 1: Agent called `generate_diagram_image` manually → **same key mismatch**, image generated but discarded
  - iter 2: Agent called `generate_diagram_image` again → **same failure**, third generated image discarded
  - iter 3: `detect_zones` on ORIGINAL labeled AMNH image → found 6 zones with good polygon coords:
    - `petals` (42 polygon points), `sepals` (24 pts), `stamen` (40 pts), `pistil` (65 pts), `anther` (57 pts), `filament` (25 pts)
    - All lowercase labels, all with 0.95 confidence
    - Used `gemini_sam3` detection method
  - iter 4: `submit_assets` → **accepted** (1 scene, 6 zones)
  - iter 5: Final answer
- **Issues found**:
  - **[AG-1] CRITICAL**: `generate_diagram_image_impl` checks `result.get("image_path")` but `generate_with_gemini` returns `result["generated_path"]`. Three successfully generated images were discarded. **FIXED in this session.**
  - **[AG-2]** Only produced assets for Scene 1 of 3. With null scene_specs, agent only sees game_design which doesn't provide per-scene image specs
  - **[AG-3]** Zone detection ran on labeled reference image (text visible). Zones may be positioned around text labels rather than actual structures
  - **[AG-4]** Zone labels are lowercase plural: `petals`, `sepals` vs game design's `Petal`, `Sepal`
  - **[AG-5]** `submit_assets` accepted 1/3 scenes because no scene_specs to check completeness against
  - **[AG-6]** Auto-clean failed silently; agent's manual attempts also failed; no fallback strategy
- **Verdict**: Partially working — zones detected but image not cleaned, only 1 of 3 scenes covered

### Stage 15: blueprint_assembler_v3 (30.1s, gemini-2.5-flash, 8997 tokens)
- **Input**: game_design (3 scenes), scene_specs=None, interaction_specs=None, assets (1 scene)
- **ReAct trace** (2 iterations):
  - iter 0: `assemble_blueprint` → produced multi-scene blueprint
  - iter 1: Final answer (no validation or repair attempted)
- **Output Blueprint**:
  - `is_multi_scene: true`, 3 scenes in game_sequence
  - Scene 1 "The Outer Flower":
    - `diagram.assetUrl`: external AMNH URL (not cleaned, not proxied)
    - Zones: Petal (null coords), Sepal (null coords), Stamen (has coords), Pistil (has coords)
    - Labels: [Petal, Sepal, Stamen, Pistil]
    - mechanic_type: MISSING
  - Scene 2 "Reproductive Structures":
    - No diagram image
    - 7 zones, ALL with null coordinates
    - mechanic_type: MISSING
  - Scene 3 "What Do They Do?":
    - No diagram image
    - 9 zones, ALL with null coordinates
    - mechanic_type: MISSING
  - NO mechanic configs at any level (no descriptionMatchingConfig, no zoneGroups, etc.)
- **Issues found**:
  - **[BA-1]** Petal/Sepal zones have null coords because asset zones use `petals`/`sepals` (plural) but design uses `Petal`/`Sepal` (singular). **FIXED in this session** (fuzzy label matching).
  - **[BA-2]** `mechanic_type` not populated in game_sequence scenes — blueprint_assembler doesn't extract it from game_design
  - **[BA-3]** No mechanic-specific configs populated (descriptionMatchingConfig, zoneGroups for hierarchical, etc.) because interaction_specs were null
  - **[BA-4]** External image URL not proxied for CORS; multi-scene `diagram.assetUrl` proxying not implemented in generate.py
  - **[BA-5]** `generation_complete` not set in output — may cause routes/generate.py to mark run as "error"
  - **[BA-6]** No `validate_blueprint` or `repair_blueprint` tools called — went straight from assemble to final answer
  - **[BA-7]** Scenes 2 and 3 assembled with zero data — no images, no coords, no mechanic configs. Should at least warn/fail
- **Verdict**: BROKEN — produces a structurally correct but content-empty blueprint

---

## Game UI State (Screenshot Analysis)

What the user sees:
1. Tab bar with 3 scene tabs: "1. The Outer Fl...", "2. Reproductiv...", "3. What Do The..."
2. "Scene 1 of 1" displayed (incorrect — should say "Scene 1 of 3")
3. Broken image icon with alt text "Educational diagram: Interactive Diagram. Contains [N] labeled zones to identify."
4. Labels in tray: Pollen, Petal, Stamen, Stem, Pistil, Sepal, Leaf, Root (includes distractors)
5. Score: 0/40, 0/90 points, 0% complete
6. No visible drop zones (blue circles or polygons)

---

## Consolidated Bug List

### CRITICAL (Pipeline-breaking)

| ID | Bug | Component | Root Cause | Status |
|----|-----|-----------|------------|--------|
| SA-1 | scene_architect_v3 produces null output after 68s | scene_architect_v3 | Agent never calls submit tool or parse_final_result fails | OPEN |
| SA-4 | Agent writes tool calls as text instead of function calling | scene_architect_v3 / react_base | ReAct framework bug — model outputs "ACTION: tool_name" as text | OPEN |
| ID-1 | max_iterations=8 insufficient for 3-scene games | interaction_designer_v3 | Each scene needs 4-5 tool calls, 3 scenes need 12-15 | OPEN |
| AG-1 | generate_diagram_image discards successful images (key mismatch) | asset_generator_tools.py | `image_path` vs `generated_path` key name | **FIXED** |
| PIPE-1 | Pipeline continues after 2 failed validator passes | graph.py retry loop | Retry exhaustion doesn't halt pipeline | OPEN |

### HIGH (Feature-breaking)

| ID | Bug | Component | Root Cause | Status |
|----|-----|-----------|------------|--------|
| AG-2 | Only produces assets for 1/3 scenes | asset_generator_v3 | No scene_specs → only sees 1 scene | OPEN |
| BA-1 | Plural label mismatch (petals vs Petal) | blueprint_assembler_tools | No fuzzy matching in zone lookup | **FIXED** |
| BA-2 | mechanic_type missing from game_sequence scenes | blueprint_assembler_tools | Not extracted from game_design | OPEN |
| BA-3 | No mechanic configs in blueprint | blueprint_assembler_tools | interaction_specs null → nothing to populate | OPEN |
| BA-5 | generation_complete not set | blueprint_assembler_v3 | parse_final_result doesn't set flag | OPEN |
| GD-1 | description_matching mechanic has empty config | game_designer_v3 | submit_game_design schema doesn't require mechanic configs | OPEN |
| ID-2 | Agent picks wrong mechanic for Scene 1 | interaction_designer_v3 | No scene_specs to guide mechanic selection | OPEN |

### MEDIUM (Quality/UX)

| ID | Bug | Component | Root Cause | Status |
|----|-----|-----------|------------|--------|
| DV-1 | Validator passes with critical warnings | design_validator | Score 0.9 threshold too lenient | OPEN |
| AG-3 | Zone detection on labeled reference image | asset_generator_v3 | Auto-clean failed (AG-1 cascade) | OPEN (AG-1 fix may resolve) |
| AG-4 | Asset zone labels are lowercase plural | asset_generator_tools | detect_zones returns lowercase from Gemini | OPEN |
| BA-4 | Multi-scene image URLs not proxied | routes/generate.py | Only handles root diagram.assetUrl | OPEN |
| BA-6 | No validate/repair tools called | blueprint_assembler_v3 | Agent goes straight to final answer | OPEN |
| BA-7 | Scenes 2+3 assembled with zero data | blueprint_assembler_tools | No completeness check per scene | OPEN |
| SA-5 | Retry gets no failure feedback | scene_architect_v3 | Validator result not passed to retry prompt | OPEN |
| ID-5 | Retry doesn't adjust strategy | interaction_designer_v3 | No awareness of previous iteration count | OPEN |

### LOW

| ID | Bug | Component | Root Cause | Status |
|----|-----|-----------|------------|--------|
| AG-5 | submit_assets accepts 1/3 scenes | asset_generator_tools | No scene_specs to validate completeness | OPEN |
| SA-2 | ReAct trace not captured for pass 1 | instrumentation | Trace capture may have internal error | OPEN |
| ID-4 | 165 seconds wasted on 2 failed passes | interaction_designer_v3 | No early exit when iterations insufficient | OPEN |

---

## Fixes Applied in This Session

1. **AG-1 (CRITICAL)**: Fixed `generate_diagram_image_impl` to check both `generated_path` and `image_path` keys
2. **BA-1 (HIGH)**: Added `_normalize_label()` and `_build_zone_lookup()` for case+plural insensitive zone matching
3. **Asset Generator**: Added mechanic-aware image generation prompts (10 mechanic types)
4. **Asset Generator**: Integrated auto-clean into `search_diagram_image` (calls `generate_diagram_image` after download)
5. **Asset Generator**: `generate_diagram_image` now accepts `reference_image_path` parameter

---

## Architectural Issues Identified

### 1. ReAct Agent Iteration Limits
The current fixed `max_iterations` doesn't scale with game complexity. A 1-scene game needs ~5 iterations, a 3-scene game needs ~15. Either:
- Scale max_iterations based on scene count
- Use a planner pattern (plan first, execute per-scene)
- Use map-reduce (parallelize per-scene)

### 2. Upstream Failure Propagation
When scene_architect or interaction_designer fail, downstream agents receive `None` and produce garbage output that still gets marked "success". Need:
- Pipeline halt on critical upstream failures
- Or: fallback/default generation for missing specs

### 3. Single Agent Per Phase
One ReAct agent handling ALL scenes is a bottleneck. The v4 architecture research (docs/audit/09_agentic_frameworks_research.md) recommends:
- Planner agent → decomposes into per-scene tasks
- Orchestrator → dispatches to specialist workers
- Workers → per-scene, per-mechanic tool usage
- Quality gate → validates before proceeding

### 4. Image Pipeline
Current: search → (hope auto-clean works) → detect zones
Needed: search → validate → generate clean version → validate clean → detect zones → validate zones
Each step needs robust error handling and retry.

---

---

## Part 2: Validator Audit — Mechanic Support

### Validator Coverage Matrix

| Mechanic | design_validator | scene_validator | interaction_validator | blueprint_validator |
|----------|-----------------|-----------------|----------------------|-------------------|
| drag_drop | Implicit only | Implicit only | Scoring-only check | Unknown (delegates) |
| click_to_identify | Config checked | Config checked | Trigger + feedback | Unknown |
| trace_path | Config checked | Config checked | Trigger + feedback | Unknown |
| sequencing | Config checked | Config checked | Trigger + feedback | Unknown |
| description_matching | Config checked | Config checked | Trigger only | Unknown |
| sorting_categories | Config checked | Config checked | Trigger only | Unknown |
| memory_match | Config checked | Config checked | Trigger only | Unknown |
| branching_scenario | Config checked | Config checked | Trigger only | Unknown |
| **compare_contrast** | **NOT CHECKED** | **NOT CHECKED** | **NOT IN MAP** | Unknown |
| **hierarchical** | **NOT CHECKED** | **NOT CHECKED** | **NOT IN MAP** | Unknown |
| **timed_challenge** | **NOT CHECKED** | **NOT CHECKED** | **NOT IN MAP** | Unknown |

### design_validator.py Findings

- **Lines 24-29**: `VALID_MECHANIC_TYPES` defines 11 types (incl. timed_challenge)
- **Lines 109-163**: Mechanic-specific config checks — covers 7 of 11 mechanics
- **MISSING validation for**: `compare_contrast`, `hierarchical`, `timed_challenge`, `drag_drop`
- **Pass threshold**: score >= 0.7. Missing mechanic configs trigger WARNINGs (-0.05) not FATALs
- **[DV-AUDIT-1]**: Passes games with critical config gaps (e.g., description_matching with empty config scored 0.9)

### scene_validator.py Findings (in scene_spec_v3.py)

- **Lines 275-329**: If/elif chain for mechanic config presence — covers same 7 mechanics
- **MISSING**: compare_contrast, hierarchical, timed_challenge silently pass with no config checks
- **No per-mechanic image requirements** — doesn't validate trace_path needs sequential visuals, etc.
- **[SV-AUDIT-1]**: Unmapped mechanic types pass validation with zero config inspection

### interaction_validator.py Findings (in interaction_spec_v3.py)

- **Lines 245-254**: `MECHANIC_TRIGGER_MAP` covers 8 mechanics (missing compare_contrast, hierarchical, timed_challenge)
- **Lines 269-309**: Content-specific feedback checks only for 4 mechanics (click_to_identify, description_matching, trace_path, sequencing)
- **drag_drop**: Only checks "scoring exists" — no content quality checks for zone-specific feedback
- **6 mechanics have ZERO content validation**: drag_drop (content), sorting_categories, memory_match, branching_scenario, compare_contrast, hierarchical
- **Legacy auto_fix (Line 350)**: Falls back to `drag_drop` for unknown interaction modes
- **[IV-AUDIT-1]**: Most mechanics pass with generic "Correct!/Try again." feedback unchecked

### blueprint_validator.py Findings

- **Thin wrapper** — delegates entirely to `validate_blueprint()` from blueprint_generator.py
- Cannot assess mechanic coverage without auditing that function
- **Line 76-78**: Sets `generation_complete=True` only if valid — critical flag

---

## Part 3: Agent Audit — Drag_Drop-Only Assumptions

### Coverage Matrix: End-to-End Mechanic Support

| Mechanic | Designer | Scene Architect | Interaction | Asset Gen | Blueprint | **E2E** |
|----------|----------|-----------------|-------------|-----------|-----------|---------|
| drag_drop | Full | Full | Full | Full | Full | **WORKS** |
| trace_path | Prompt | Partial tool | Generic | Generic zones | Partial config | **DEGRADED** |
| click_to_identify | Prompt | Partial tool | Generic | Generic zones | Partial config | **DEGRADED** |
| sequencing | Prompt | Partial tool | Generic | No support | Partial config | **BROKEN** |
| description_matching | Prompt | No tool | Generic | No support | No config | **BROKEN** |
| sorting_categories | Prompt | No tool | Generic | No support | No config | **BROKEN** |
| memory_match | Prompt | No tool | No support | No support | No config | **BROKEN** |
| branching_scenario | Prompt | No tool | No support | No support | No config | **BROKEN** |
| compare_contrast | Prompt | No tool | No support | No support | No config | **BROKEN** |
| hierarchical | Prompt | No tool | No support | No support | No config | **BROKEN** |

### Per-Agent Findings

#### game_designer_v3.py
- **Line 77**: `drag_drop: Default mechanic. No special config needed` — only drag_drop gets this treatment
- **Lines 149-167**: Task prompt only reads `canonical_labels`, does NOT inject mechanic-specific data (`sequence_flow_data`, `label_descriptions`, `comparison_data`, `content_characteristics`)
- **parse_final_result**: Does NOT validate chosen mechanics have supporting upstream data
- **Impact**: Designer picks mechanics without feasibility checks

#### scene_architect_v3.py
- **System prompt (lines 68-75)**: Lists config examples for only 6 mechanics (missing memory_match, branching_scenario, compare_contrast, description_matching)
- **generate_mechanic_content tool**: Only handles 4 mechanics (trace_path, click_to_identify, sequencing, drag_drop). Returns failure for 6 other mechanics.
- **build_task_prompt**: Never mentions `generate_mechanic_content` tool — agent doesn't know it should call it
- **Impact**: Tool failures for 6 mechanics with no recovery

#### interaction_designer_v3.py
- **System prompt**: Completely generic — no mechanic-specific scoring/feedback guidance
- **enrich_mechanic_content tool**: Exists but NOT mentioned in system prompt or task prompt
- **Impact**: All mechanics get generic "correct/incorrect" feedback

#### asset_generator_v3.py
- **System prompt entirely diagram-focused**: "Generate visual assets (diagram images, zone overlays)"
- **No tools for**: sequencing items, memory cards, branching nodes, comparison graphics, sorting categories
- **Impact**: Complete asset generation failure for non-diagram mechanics

#### blueprint_assembler_v3.py / blueprint_assembler_tools.py
- **`_assemble_mechanics()` only handles**: trace_path, click_to_identify, sequencing (3 of 10)
- **Line 475**: Hardcoded default `mechanic_type = "drag_drop"` fallback
- **Line 326**: Scoring falls back to `len(global_labels) * 10` — wrong for sequencing, memory, branching
- **Line 572-573**: Only trace_path waypoints get frontend conversion
- **Impact**: 7 mechanic configs silently dropped from blueprint

#### react_base.py
- **max_iterations**: 6-8 per agent (insufficient for 3-scene multi-mechanic games)
- **No mechanic-specific JSON validation** after extraction
- **Impact**: Timeouts and malformed data

#### graph.py create_v3_graph()
- **Max 2 retries per validator** then proceeds anyway
- **No branching based on mechanic type** — all games use same agent pipeline
- **Impact**: Failed validations don't halt pipeline

---

## Part 4: Prompt Audit — Mechanic Coverage

### Coverage Table

| Component | drag_drop | click_id | trace | seq | sort | desc_match | memory | branch | compare | hier |
|-----------|-----------|----------|-------|-----|------|-----------|--------|--------|---------|------|
| game_designer SYSTEM | Named | Named | Named | Named | Named | Named | Named | Named | Named | Missing |
| game_designer TASK | Data | None | None | None | None | None | None | None | None | None |
| scene_architect SYSTEM | Config | Config | Config | Config | Config | Config | Missing | Missing | Missing | Config |
| scene_architect TASK | None | None | None | None | None | None | None | None | None | None |
| interaction_designer SYS | Generic | Generic | Generic | Generic | Generic | Generic | Generic | Generic | Generic | Generic |
| interaction_designer TASK | Generic | Generic | Generic | Generic | Generic | Generic | Generic | Generic | Generic | Generic |
| asset_generator SYSTEM | Diagram | Diagram | Diagram | Diagram | Diagram | Diagram | Diagram | Diagram | Diagram | Diagram |
| blueprint_assembler SYS | None | None | None | None | None | None | None | None | None | None |
| check_capabilities TOOL | Full | Full | Full | Full | Full | Full | Full | Full | Full | Missing |
| scoring_templates TOOL | Full | Full | Full | Full | Full | Full | Full | Full | Full | Missing |
| blueprint_prompt FILE | Full | Full | Full | Full | Full | Full | Missing | Missing | Full | Full |

### Key Root Causes

1. **Agent system prompts don't integrate with their own tools**
   - scene_architect has `generate_mechanic_content` tool but prompt never tells agent to call it
   - interaction_designer has `enrich_mechanic_content` tool but prompt never mentions it
   - game_designer has `check_capabilities` tool but prompt doesn't say "call this BEFORE designing"

2. **Task prompts (build_task_prompt) are step-by-step but incomplete**
   - scene_architect: mentions 5 tools but task prompt doesn't list step for `generate_mechanic_content`
   - interaction_designer: mentions 5 tools but task prompt doesn't list step for `enrich_mechanic_content`
   - game_designer: doesn't inject mechanic-specific data (`sequence_flow_data`, `comparison_data`) despite it being in context

3. **Mechanic handling treated as optional, not mandatory**
   - No prompt says "IF this mechanic is chosen, THEN you MUST populate its config"
   - Config population is in schema but not enforced in task workflow

4. **Hierarchical mechanic under-documented everywhere** — missing from 4/10 components

---

## Grand Summary: What's Actually Broken

### The V3 pipeline only produces playable games for `drag_drop`.

All other mechanics fail because:

1. **game_designer_v3** picks mechanics it can't support (no feasibility check)
2. **scene_architect_v3** can't populate configs (tools only support 4 mechanics, agent doesn't call them)
3. **interaction_designer_v3** produces generic scoring/feedback (8 iterations too few, doesn't call enrich tool)
4. **asset_generator_v3** only generates diagram-based assets (no sequencing items, memory cards, etc.)
5. **blueprint_assembler_v3** drops configs for 7 mechanics (only handles 3)
6. **Validators** let empty configs pass (3 mechanics completely unchecked)
7. **Pipeline** continues after upstream failures (retry exhaustion = silent proceed)

### What Needs to Happen

1. **Phase 0**: Fix pipeline halt on critical failures (don't continue with null data)
2. **Phase 1**: Fix prompts to integrate tools (tell agents to call their own tools)
3. **Phase 2**: Extend tool coverage (generate_mechanic_content for all 10, enrich for all 10)
4. **Phase 3**: Fix validators (add 3 missing mechanics, tighten thresholds)
5. **Phase 4**: Fix blueprint assembler (handle all 10 mechanic configs)
6. **Phase 5**: Asset generation architecture (planner + orchestrator + workers per scene)
7. **Phase 6**: Increase max_iterations (scale with scene count) or use planner pattern
