# V3 Pipeline Master Findings v2

> Consolidated from 15 research documents, 5 code audits, 1 mechanic redesign document, and V3 run analysis.
> Date: February 11, 2026

---

## 1. Executive Summary

The V3 pipeline produces **playable games for only 1 of 9 mechanics** (drag_drop). Run `29d63bf9` completed 15/15 stages as "success" but output was **unplayable** — empty mechanic configs, no scoring, no feedback, no visual assets beyond a single diagram image.

**Root cause:** The pipeline was designed around a "label the diagram" mental model. All agents, tools, schemas, and asset workflows assume one diagram image + zone detection. The 8 non-drag_drop mechanics need fundamentally different content (decision trees, card pairs, item illustrations, dual diagrams, SVG paths) that no agent generates.

**Scale of gaps identified:**
- **~206 schema field gaps** across 5 Pydantic model families
- **87 backend agent gaps** (26 CRITICAL)
- **22+ backend tool gaps** in 4 tiers
- **~63 new frontend components** needed
- **60+ missing TypeScript type fields**
- **18 graph/routes/services findings** (5 CRITICAL)
- **54 cataloged fixes** from mechanic redesign (T-1..19, A-1..6, P-1..7, V-1..3, S-1..4, FE-1..15)

**Priority mechanics (6):** drag_drop, sequencing, sorting_categories, memory_match, click_to_identify, trace_path.
**Deferred mechanics (3):** branching_scenario, compare_contrast, description_matching (require new asset workflows).

---

## 2. V3 Run Analysis (Run 29d63bf9)

### 2.1 Stage-by-Stage Findings

| Stage | Status | Issue |
|-------|--------|-------|
| input_enhancer | OK | — |
| domain_knowledge_retriever | OK | Rich data (65 fields) but only `canonical_labels` consumed downstream |
| router | OK | — |
| game_designer_v3 | PARTIAL | Produces `type` field only; no mechanic-specific configs |
| design_validator | PARTIAL | Missing configs treated as WARNING not FATAL (DV-1) |
| scene_architect_v3 | BROKEN | Null output twice (SA-1..5); didn't call generate_mechanic_content |
| scene_validator | N/A | Received null specs |
| interaction_designer_v3 | BROKEN | Hit max_iterations=8 twice (ID-1..6); didn't call enrich_mechanic_content |
| interaction_validator | N/A | Received empty specs |
| asset_generator_v3 | PARTIAL | Generated 3 images, discarded all due to key mismatch (AG-1, fixed) |
| blueprint_assembler_v3 | BROKEN | Content-empty blueprint (BA-1..7) |

### 2.2 Coverage Matrix

| Mechanic | Game Designer | Scene Architect | Interaction Designer | Asset Generator | Blueprint Assembler | Frontend |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| drag_drop | OK | OK | OK | OK | OK | NEEDS POLISH |
| click_to_identify | OK | PARTIAL | PARTIAL | OK | PARTIAL | NEEDS ENHANCEMENT |
| trace_path | OK | PARTIAL | PARTIAL | PARTIAL | PARTIAL | NEEDS ENHANCEMENT |
| sequencing | OK | BROKEN | BROKEN | BROKEN | PARTIAL | NEEDS ENHANCEMENT |
| sorting_categories | OK | BROKEN | BROKEN | BROKEN | PARTIAL | NEEDS ENHANCEMENT |
| description_matching | BROKEN | BROKEN | BROKEN | OK | BROKEN | NEEDS ENHANCEMENT |
| memory_match | BROKEN | BROKEN | BROKEN | BROKEN | BROKEN | NEEDS ENHANCEMENT |
| branching_scenario | BROKEN | BROKEN | BROKEN | BROKEN | BROKEN | NEEDS ENHANCEMENT |
| compare_contrast | BROKEN | BROKEN | BROKEN | BROKEN | BROKEN | NEEDS ENHANCEMENT |

### 2.3 Prompt Coverage Audit

| Agent | drag_drop | click_to_identify | trace_path | sequencing | sorting | description | memory | branching | compare |
|-------|-----------|-------------------|------------|------------|---------|-------------|--------|-----------|---------|
| System prompt | Generic | Generic | Generic | None | None | None | None | None | None |
| Task prompt | Generic | Generic | Generic | None | None | None | None | None | None |
| Tool guidance | Generic | None | None | None | None | None | None | None | None |

---

## 3. Root Causes (Consolidated)

| # | Root Cause | Impact | Fix Level |
|---|-----------|--------|-----------|
| RC-1 | Agent prompts don't mandate mechanic-specific tool calls | ALL non-drag_drop mechanics get empty configs | Prompt + architecture |
| RC-2 | No per-item image generation capability | sequencing, sorting, memory_match lack visual richness | New asset workflows |
| RC-3 | No scene/character image generation for branching | branching_scenario has no visual assets | New asset workflows |
| RC-4 | No dual-image generation for compare_contrast | compare_contrast can't produce 2 matched images | Architecture change |
| RC-5 | No functional description generation | click_to_identify, description_matching get generic prompts | New tool handlers |
| RC-6 | No pair/tree/category generation | memory_match, branching, sorting get no content | New tool handlers |
| RC-7 | Single ReAct agent handles all scenes sequentially | Context overload, no parallelism, fragile | Send API architecture |
| RC-8 | Asset generator is 100% diagram-centric | Only knows search→zones; no concept of per-mechanic asset types | 3-stage asset pipeline |
| RC-9 | GameDesignV3Slim has only `type: str` | Zero mechanic config flows through Phase 1 | Schema fix |
| RC-10 | Blueprint assembler drops scoring/feedback for 6/9 mechanics | Frontend gets empty configs | Blueprint tool fix |
| RC-11 | V3 image serving broken (no routes, ID mismatch) | Frontend can't display generated images | Route fixes |
| RC-12 | Retry count off-by-one | "Max 2 retries" = 1 actual retry | Graph wiring fix |
| RC-13 | DomainKnowledge TypedDict ↔ Pydantic mismatch | 3 fields lost in state propagation | State fix |
| RC-14 | Bloom's taxonomy drives mechanic selection | Forces drag_drop baseline, limits mechanic choice | Remove from selection |
| RC-15 | Validators too lenient | Missing mechanic configs = -0.05 WARNING, not FATAL | Increase severity |

---

## 4. Per-Mechanic Gap Analysis

### 4.1 drag_drop (Status: WORKS, needs polish)

**Backend:** Fully functional pipeline.

**Frontend gaps (from research/07):**
- No leader lines (SVG from label to zone) — P0
- No zoom/pan on diagram canvas — P1
- No spring physics snap animation — P0
- No contextual info panels on correct placement — P1
- No label grouping by category in tray — P2
- No reverse mode (zone highlights, pick label) — P2
- No progressive hint system with score penalty — P0

**Schema gaps:** None critical. `DragDropConfig` interface missing in types.ts (3 fields).

### 4.2 sequencing (Status: BROKEN)

**Backend gaps:**
- `generate_mechanic_content` handler exists but produces flat items with no images, no layout config, no instruction text
- No per-item illustration generation in asset pipeline
- Blueprint assembler maps items but no per-item images or layout mode

**Frontend gaps (from research/01):**
- Only DnD reorder list; no timeline/circular/flowchart layouts
- Items are text-only; no image/icon support
- No connector lines between items
- No slot-based placement
- No progressive reveal
- No cascade animation on completion
- Missing 14 config properties: layout_mode, interaction_pattern, card_type, connector_style, slot_style, etc.

**Schema gaps (from audit 12):**
- `SequenceDesign`: 4 fields exist / ~25 required
- Missing: layout_mode, interaction_pattern, item image/icon/category, connector config, slot config, distractor support, scoring algorithm (Kendall tau)

**Research-backed requirements:**
- Per-item illustration cards (image + text + description)
- 5 layout modes: horizontal_timeline, vertical_list, circular_cycle, flowchart, insert_between
- 4 interaction patterns: drag_reorder, drag_to_slots, click_to_swap, number_typing
- Connector lines that illuminate on correct ordering
- Cyclic sequence support (loops back)

### 4.3 sorting_categories (Status: BROKEN)

**Backend gaps:**
- `generate_mechanic_content` generates flat item/category lists; no images, no sort mode config
- Category matching uses fragile case-insensitive substring matching
- No Venn/matrix/column mode support
- `SortingItem.correctCategoryId` is SINGULAR — must be LIST for Venn modes

**Frontend gaps (from research/03):**
- Only bucket mode with batch submit
- No Venn diagram mode (2-circle or 3-circle)
- No matrix/Carroll diagram mode
- No column mode
- Items text-only; no image/icon cards
- Category containers have no icons, images, or themed styles
- No iterative correction (incorrect items bounce back)
- Missing 11 config properties

**Schema gaps (from audit 12):**
- `SortingDesign`: 4 fields exist / ~25 required
- `SortingConfig` (frontend): 23 missing fields
- Critical: `correctCategoryId: str` must become `correct_category_ids: List[str]`

**Research-backed requirements:**
- 5 sort modes: bucket, venn_2, venn_3, matrix, column
- 5 item card types: text_only, text_with_icon, image_with_caption, image_only, rich_card
- 6 container styles: bucket, labeled_bin, circle, cell, column, funnel
- 4 submit modes: batch_submit, immediate_feedback, round_based, lock_on_place
- SVG circle rendering for Venn with geometric hit-testing
- Multi-category items (essential for Venn)

### 4.4 memory_match (Status: BROKEN)

**Backend gaps:**
- `generate_mechanic_content` has NO handler for memory_match
- Fallback description is generic `f"A part of the {question[:30]}..."`
- No per-card image generation
- No diagram closeup cropping
- No difficulty variation

**Frontend gaps (from research/02):**
- CSS flip uses opacity toggle, NOT true 3D perspective + rotateY
- Only classic concentration; no column match, scatter, progressive, peek variants
- Cards are text-only; no image support
- No themed card back design
- No explanation-on-match educational popup
- No category color-coding
- `gridSize` prop accepted but ignored (auto-calculated)
- Missing 13 config properties

**Schema gaps (from audit 12):**
- `MemoryMatchDesign`: 4 fields exist / ~30 required
- `MemoryMatchConfig` (frontend): 24 missing fields
- Missing: game_variant, card_face_type, card_back_style, match_type, matched_card_behavior, mismatch_penalty, progressive/column/scatter configs

**Research-backed requirements:**
- 5 game variants: classic, column_match, scatter, progressive, peek
- 7 match types: identical, term_to_definition, image_to_label, concept_to_example, cause_to_effect, part_to_whole, diagram_region_to_label
- True 3D CSS flip with `perspective` + `transform-style: preserve-3d`
- Per-card images (illustrations OR diagram closeups using zone crop regions)
- Explanation reveal on match
- Diagram closeup pattern: each card shows cropped region of source diagram using zone coordinates

### 4.5 click_to_identify (Status: DEGRADED)

**Backend gaps:**
- Scene architect generates zones but no identification prompts per zone
- No functional description generation (only names)
- No explore-then-test mode data
- No magnification config

**Frontend gaps (from research/06):**
- Zones always visible as circles — no invisible/subtle mode for test
- `any_order` mode leaks zone labels in prompt display (HotspotManager L227-230)
- No 5-state zone highlight machine (default/hover/selected/correct/incorrect)
- No magnification lens
- No explore-then-test phase controller
- Hardcoded colors not configurable
- Missing 8 config properties

**Schema gaps:**
- `ClickToIdentifyConfig` interface MISSING entirely in types.ts
- Backend needs: prompt_style, selection_mode, highlight_style, magnification config, explore mode config

**Research-backed requirements:**
- 6 new components: PromptBanner, ZoneHighlightStateMachine, MagnificationLens, ExploreTestController, SelectionModeController, ZoneHighlightConfig
- Zones nearly invisible in test mode (tests knowledge, not process-of-elimination)
- Two prompt styles: naming ("Click on the mitochondria") vs functional ("Click the structure responsible for energy production")
- Progressive difficulty ordering
- Magnification lens essential for dense diagrams

### 4.6 trace_path (Status: DEGRADED)

**Backend gaps:**
- Scene architect generates waypoints but no SVG path data
- No particle animation config
- No color transition data
- No gate/valve waypoint types
- No branching/circular path types

**Frontend gaps (from research/06):**
- Only straight lines between waypoints — no SVG curved paths
- No animated particle system (THE defining visual feature)
- No color transitions (critical: blue→red blood flow)
- No gate/valve waypoint animations
- No freehand drawing mode
- No branching or circular path types
- Direction arrows only at endpoints, not distributed along path
- Missing 10 config properties

**Schema gaps:**
- `TracePathConfig` interface MISSING entirely in types.ts
- Backend needs: path_type (linear/branching/circular), drawing_mode, particle config, color transitions, gate animations, SVG path data

**Research-backed requirements:**
- 8 new components: SVGPathDefinitionLayer, AnimatedParticleSystem, ColorTransitionEngine, DirectionalArrowOverlay, WaypointZoneMarker, GateValveAnimation, FreehandDrawingCanvas, DrawingModeController
- SVG curved paths for anatomical accuracy
- Animated particles flowing along completed paths (PhET, AHA)
- Color transitions encoding state changes (blue→red blood, liquid→gas water)
- 3 path types: linear, branching, circular

### 4.7 description_matching (Status: BROKEN)

**Backend gaps:**
- No agent generates per-label functional descriptions
- `label_descriptions` context never populated
- No distractor description generation
- No matching mode config

**Frontend gaps (from research/06):**
- No connecting lines (SVG) between matched pairs
- No zone proximity highlighting during drag
- No deferred evaluation mode ("submit all")
- Distractors defined in types but not used in component
- Multiple-choice options re-shuffle every render (unstable UX bug)
- Missing 10 config properties

**Schema gaps:**
- `DescriptionMatchingConfig` needs: match_mode, connecting lines config, defer evaluation, distractor config, description style, panel position

**Research-backed requirements:**
- 7 new components: ConnectingLineRenderer, DescriptionCardStateMachine, ZoneProximityHighlighter, DeferredEvaluationController, DistractorPool, DescriptionStyleConfig, InteractionModeRouter
- 4 description styles: functional, structural, process, clinical
- Deferred evaluation critical for summative assessment

### 4.8 branching_scenario (Status: BROKEN — DEFERRED)

**Backend gaps:**
- `generate_mechanic_content` generates decision nodes via LLM but no visual assets
- No scene backgrounds, character sprites, state variables, DAG validation
- Most asset-intensive mechanic

**Frontend gaps (from research/04):**
- No scene background images (visual novel model)
- No character sprites with expression variants
- No state variable display (vitals, evidence)
- No decision tree minimap
- No multiple endings with scoring
- No narrative structure config
- Missing 10 config properties, 9 new components needed

**Research-backed requirements:**
- 3-6 scene background images per scenario (AI-generated)
- Character sprites with 4-6 expression variants
- Ending illustrations (good/neutral/bad)
- State variable system (inventory, vitals)
- Post-game debrief (optimal vs taken path)

### 4.9 compare_contrast (Status: BROKEN — DEFERRED)

**Backend gaps:**
- Architecture supports only 1 image per scene — needs TWO matched diagrams
- No dual-image generation pipeline
- No zone pairing across two images
- compare_contrast has NO LLM fallback (if no comparison_data, generates NOTHING)

**Frontend gaps (from research/05):**
- Only basic side-by-side with 4 hardcoded categories
- No image comparison slider mode
- No overlay/toggle mode
- No Venn diagram categorization mode
- No spot-the-difference mode
- No synchronized zoom
- No zone pairing lines
- Missing 13 config properties, 9 new components needed

**Research-backed requirements:**
- 5 comparison modes: side_by_side, slider, overlay_toggle, venn, spot_difference
- Dual-image pipeline: search/generate subject A → clean → detect zones A → repeat for B → compute zone pairings
- 6 new AgentState fields needed
- Graph wiring changes (Send API for parallel image pipelines)

---

## 5. Architecture Gaps

### 5.1 Current Architecture Limitations

| Limitation | Impact | Proposed Fix |
|-----------|--------|-------------|
| Single ReAct agent per phase handles all scenes sequentially | Context overload, max_iterations hit, fragile | Planner → Send API Workers → Aggregator (A-1..3) |
| 160+ field shared AgentState | Context pollution, impossible to debug | Isolated sub-graph state types (A-5) |
| No Quality Gate enforcement | LLM can skip validation, call submit prematurely | Graph-enforced sequences (A-4) |
| Asset pipeline = single diagram + zones | 5 mechanics need different asset workflows | Mechanic-aware asset dispatch (A-3) |
| No per-scene parallelism | Multi-scene games run N× slower | Send API fan-out (A-1..3) |

### 5.2 Proposed Architecture (from research/12_v3_mechanic_general_redesign.md)

**3-Stage Pattern for Phases 2, 3, 4:**
1. **ReAct Planner**: Reads upstream output, plans per-scene work items, self-corrects
2. **Parallel Workers via Send API**: Each worker handles one scene, calls mechanic-specific tools
3. **Aggregator**: Collects results, validates cross-scene consistency, submits

**5 Asset Sub-Workflows:**
1. DIAGRAM (drag_drop, click_to_identify, trace_path, description_matching): search → clean/generate → detect zones
2. PER-ITEM ILLUSTRATION (sequencing, sorting): per-item generate → background scene → category icons
3. CARD CONTENT (memory_match): per-pair generate → card illustrations → themed card back
4. BRANCHING SCENE (branching_scenario): per-location background → character sprites → ending illustrations
5. DUAL DIAGRAM (compare_contrast): subject A pipeline → subject B pipeline → zone pairing

### 5.3 Graph/Routes/Services Findings

| ID | Severity | Description |
|----|----------|-------------|
| R-1 | CRITICAL | Multi-scene image URLs not proxied — frontend gets local file paths |
| R-3 | CRITICAL | No route to serve V3-generated images from `pipeline_outputs/v3_assets/` |
| R-4 | CRITICAL | ID mismatch: routes use `question_id`, V3 saves by `run_id` |
| V-1 | CRITICAL | Retry count off-by-one: "max 2 retries" = 1 actual retry |
| R-2 | HIGH | `_build_agent_outputs()` does NOT record V3 agent outputs |
| R-6 | HIGH | Topology hardcoded "T1" even for V3 |
| M-6 | HIGH | Only gemini_only preset has V3 model configs |
| S-2 | HIGH | `clean_diagram()` hardcoded to flower-specific prompt |
| S-3 | HIGH | `get_gemini_service()` naming collision between two services |

---

## 6. Schema Gaps (Total: ~206 fields)

### 6.1 Backend Schema Gap Counts

| Schema | Existing Fields | Required Fields | Gap |
|--------|----------------|-----------------|-----|
| SequenceDesign (game_design_v3.py) | 4 | ~25 | ~21 |
| SortingDesign | 4 | ~25 | ~21 |
| BranchingDesign | 6 | ~40+ | ~34 |
| CompareDesign | 3 | ~20+ | ~17 |
| MemoryMatchDesign | 4 | ~30+ | ~26 |
| GameDesignV3Slim.SlimMechanicRef | 1 (type only) | ~3 | ~2 |
| DomainKnowledge TypedDict | missing 3 | — | 3 |
| **Total backend** | | | **~124** |

### 6.2 Frontend Schema Gap Counts

| Config Interface | Existing Fields | Required Fields | Gap |
|-----------------|----------------|-----------------|-----|
| SequenceConfig (types.ts) | ~5 | ~14 | ~9 |
| SortingConfig | ~4 | ~14 | ~10 |
| MemoryMatchConfig | ~3 | ~14 | ~11 |
| BranchingConfig | ~4 | ~14 | ~10 |
| CompareConfig | ~4 | ~14 | ~10 |
| DescriptionMatchingConfig | narrow | ~10 | ~7 |
| ClickToIdentifyConfig | MISSING | ~8 | ~8 |
| TracePathConfig | MISSING | ~10 | ~10 |
| DragDropConfig | MISSING | ~3 | ~3 |
| Base type fields (Label, SequenceItem, etc.) | — | ~16 | ~16 |
| **Total frontend** | | | **~94** |

### 6.3 State Field Gaps

| Category | Fields Needed |
|----------|--------------|
| Compare dual-image | diagram_image_b, diagram_image_b_url, zones_b, zone_pairings, comparison_visual_spec, is_comparison_mode |
| Branching assets | scene_backgrounds, character_sprites, ending_illustrations, branching_state_variables |
| Sequencing | sequence_item_images |
| Sorting | sorting_item_images, sorting_category_icons |
| Memory Match | memory_card_images, diagram_crop_regions |
| DomainKnowledge mismatch | query_intent, suggested_reveal_order, scene_hints |

---

## 7. Tool Gaps

### 7.1 Scene Architect Tools (`scene_architect_tools.py`)

| Tool | Mechanic | Status | Gap |
|------|----------|--------|-----|
| generate_mechanic_content | drag_drop | OK | — |
| generate_mechanic_content | click_to_identify | PARTIAL | No identification prompts |
| generate_mechanic_content | trace_path | PARTIAL | No SVG paths, no particle config |
| generate_mechanic_content | sequencing | PARTIAL | No per-item images, no layout |
| generate_mechanic_content | sorting_categories | PARTIAL | No sort_mode, no item images |
| generate_mechanic_content | description_matching | BROKEN | No functional descriptions |
| generate_mechanic_content | memory_match | MISSING | No handler at all |
| generate_mechanic_content | branching_scenario | PARTIAL | No visual assets |
| generate_mechanic_content | compare_contrast | BROKEN | No LLM fallback |

### 7.2 Interaction Designer Tools (`interaction_designer_tools.py`)

| Tool | Status | Gap |
|------|--------|-----|
| get_scoring_templates | OK | Complete for all 9 mechanics |
| generate_misconception_feedback | PARTIAL | drag_drop-biased model (trigger_label + trigger_zone) |
| enrich_mechanic_content | PARTIAL | Generic LLM enrichment; not structural |
| validate_interactions | PARTIAL | Presence checks only; no content validation |
| generate_mechanic_transitions | MISSING | Multi-mechanic scenes need this |
| generate_tasks | MISSING | Frontend needs tasks[] per scene |

### 7.3 Asset Generator Tools (`asset_generator_tools.py`)

| Mechanic | Assets Needed | Provided | Gap |
|----------|---------------|----------|-----|
| drag_drop | Diagram + zones | YES | NONE |
| click_to_identify | Diagram + zones + magnification | Partial | Magnification |
| trace_path | Diagram + zones + SVG overlays | Partial | SVG paths |
| sequencing | Per-item illustrations | Diagram only | **Per-item missing** |
| sorting_categories | Per-item illustrations + category icons | Diagram only | **Both missing** |
| description_matching | Diagram + zones | YES | NONE |
| memory_match | Per-card images (front/back) | Diagram only | **Card images missing** |
| branching_scenario | Scene backgrounds + character sprites | Diagram only | **Both missing** |
| compare_contrast | TWO matched diagrams + zones on BOTH | Single diagram | **CRITICAL: dual-diagram** |

### 7.4 Blueprint Assembler Tools (`blueprint_assembler_tools.py`)

| Mechanic | Config Assembly | Scoring/Feedback | Assets | Status |
|----------|----------------|-----------------|--------|--------|
| drag_drop | COMPLETE | COMPLETE | COMPLETE | OK |
| trace_path | Waypoints converted | DROPS | Partial | PARTIAL |
| click_to_identify | Good normalization | DROPS | OK | PARTIAL |
| sequencing | Functional | DROPS | No images | PARTIAL |
| description_matching | Good conversion | DROPS | OK | PARTIAL |
| sorting_categories | Good normalization | DROPS | No images | PARTIAL |
| memory_match | Functional | DROPS | No images | BROKEN |
| branching_scenario | Functional | DROPS | No assets | BROKEN |
| compare_contrast | Minimal | DROPS | No dual | BROKEN |

**Critical bug:** Scoring/feedback data is DROPPED for 6/9 mechanics at L654-662. Lists crash on `.get()`.

### 7.5 New Tools Needed

**Priority 1 (Critical):**
- `generate_item_illustration` — for sequencing/sorting/memory per-item images
- `generate_mechanic_transitions` — for multi-mechanic scene chaining
- `generate_tasks` — for frontend task progression

**Priority 2 (High):**
- `generate_svg_path` — for trace_path curved paths
- `generate_distractor_descriptions` — for description_matching
- `validate_decision_tree` — for branching DAG validation

**Priority 3 (Deferred):**
- `generate_dual_comparison_images` — for compare_contrast
- `generate_scene_background` — for branching_scenario
- `generate_character_sprite` — for branching_scenario
- `generate_card_pair_images` — for memory_match image cards
- `compute_zone_pairings` — for compare_contrast cross-diagram matching

---

## 8. Frontend Gaps (Total: ~63 new components)

### 8.1 Per-Component Summary

| Component | File | Lines | Missing Visual | Missing Interactions | Missing Config | New Components |
|-----------|------|-------|---------------|---------------------|---------------|---------------|
| SequenceBuilder | SequenceBuilder.tsx | 319 | 8 | 12 | 14 | 8 |
| SortingCategories | SortingCategories.tsx | 404 | 8 | 9 | 11 | 5 |
| MemoryMatch | MemoryMatch.tsx | 310 | 10 | 8 | 13 | 7 |
| BranchingScenario | BranchingScenario.tsx | 360 | 10 | 9 | 10 | 9 |
| CompareContrast | CompareContrast.tsx | 301 | 9 | 10 | 13 | 8 |
| HotspotManager | HotspotManager.tsx | 296 | 7 | 8 | 8 | 5 |
| PathDrawer | PathDrawer.tsx | 397 | 9 | 11 | 10 | 8 |
| DescriptionMatcher | DescriptionMatcher.tsx | 517 | 7 | 8 | 10 | 5 |
| DiagramCanvas | DiagramCanvas.tsx | 386 | 9 | 10 | 10 | 8 |

### 8.2 Critical Frontend Bugs

| Bug | File | Issue |
|-----|------|-------|
| MC option reshuffle | DescriptionMatcher.tsx ~L420-450 | Options `sort(() => Math.random() - 0.5)` in render = unstable on every re-render |
| Zone label leak | HotspotManager.tsx L227-230 | `any_order` mode leaks zone labels in prompt display |
| Score reset on transition | useInteractiveDiagramState.ts L1517 | `score: 0` on mode transition prevents cumulative scoring |
| CSS flip not 3D | MemoryMatch.tsx | Uses opacity toggle, not `perspective` + `transform-style: preserve-3d` |
| `highlightMatching` dead field | CompareContrast.tsx | Defined but never read |
| `_sceneToBlueprint` missing configs | useInteractiveDiagramState.ts | Doesn't forward new config types |

### 8.3 Zustand Store Gaps

| Category | Missing |
|----------|---------|
| State fields | zoomLevel, panOffset, explorationPhase, stateVariables, matchedPairVisualState, leaderLineConnections, peekPhaseActive, freehandPathData, particleAnimationState |
| Actions | setZoomLevel, setPanOffset, start/endExplorationPhase, updateStateVariable, start/endPeekPhase, updateFreehandPath, setPlacementMode |
| Persistence | No persistence for new mechanic states |

---

## 9. Domain Knowledge Utilization

**Current utilization: 9.2%** (6/65 agent-field pairs actually consumed).

DomainKnowledge contains 65 fields of rich educational data (canonical_labels, label_descriptions, process_sequences, causal_relationships, comparison_data, branching_scenario_data, etc.) but downstream V3 agents only read `canonical_labels`.

**Fields with high value if consumed:**
- `label_descriptions` → click_to_identify prompts, description_matching descriptions
- `process_sequences` → sequencing item generation
- `causal_relationships` → trace_path waypoints, cause-effect chains
- `comparison_data` → compare_contrast categories
- `categorization_data` → sorting categories + items
- `term_definition_pairs` → memory_match pairs

---

## 10. Hierarchical Chaining (from research/09)

### 10.1 Current: Sequential Only

Current `ModeTransition[]` is a **linear linked list masquerading as a graph**: A → B → C. Six limitations: no branching, no parent-child, no conditional routing, no containment, no hub model, flat score.

### 10.2 Seven Chaining Patterns Identified

| Pattern | Description | Complexity | Value |
|---------|-------------|-----------|-------|
| Sequential | A → B → C (current) | Implemented | Baseline |
| Parallel Unlock | Complete A OR B to unlock C | Medium | High |
| Prerequisite Tree | DAG with AND/OR/N-of-M gates | High | High |
| Nested/Hierarchical | Parent spawns child on zone completion | High | Very High |
| Conditional Branching | Score determines next mechanic | Medium | Very High |
| Recursive Nesting | Mechanic contains other mechanics | Very High | High |
| Hub-and-Spoke | Central diagram → spoke sub-games | Medium-High | Very High |

### 10.3 Proposed Data Structure: MechanicDAG

```
DAGNodeType: MECHANIC | GATE | BRANCH | HUB
DAGEdgeType: UNLOCK | PREREQUISITE | CONTAINS | CONDITIONAL | EMBEDS
GateType: AND | OR | N_OF_M | SCORE_THRESHOLD
```

- `MechanicDAGNode`: node_id, node_type, mechanic_type, config, zone_ids, gate_type, conditions, viewport
- `MechanicDAGEdge`: from_node, to_node, edge_type, condition, animation
- `MechanicDAG`: nodes[], edges[], root_node_ids[], `validate_acyclic()`, `topological_order()`
- Backward compatible: `modeTransitionsToDAG()` desugars existing ModeTransition[]

### 10.4 Frontend Components Needed

- GameShell (top-level wrapper)
- BreadcrumbNav (navigation stack path)
- ProgressMiniMap (SVG DAG visualization)
- MechanicViewport (zoom transitions)
- HubDiagram (clickable zone hub)
- NavigationStack state management

---

## 11. New Mechanic Candidates (from research/08)

### 11.1 Priority Ranking

| Priority | Mechanic | Cognitive Skill | Frontend Cost | Reuses Existing? |
|----------|----------|----------------|---------------|-----------------|
| HIGH | hotspot_multi_select | Exhaustive identification | LOW | Yes (zone infra) |
| HIGH | cloze_fill_blank | Free recall | MEDIUM | Yes (label removal) |
| HIGH | spot_the_error | Error detection | MEDIUM | Partially |
| HIGH | predict_observe_explain | Prediction/hypothesis | MEDIUM-HIGH | Partially |
| MEDIUM-HIGH | cause_effect_chain | Causal reasoning | MEDIUM-HIGH | Partially |
| MEDIUM | claim_evidence_reasoning | Evidence argumentation | MEDIUM-HIGH | Partially |
| MEDIUM | elimination_grid | Deductive elimination | MEDIUM | Diagram as context |
| MEDIUM | measurement_reading | Quantitative estimation | MEDIUM | Partially |
| MEDIUM | annotation_drawing | Spatial precision | HIGH | Drawing is new |
| MEDIUM | process_builder | Constructive synthesis | HIGH | Graph editor is new |

### 11.2 Quick Win: hotspot_multi_select

Extends existing click_to_identify with multi-select + explicit submit. Nearly zero new infrastructure:
- Student selects ALL correct zones simultaneously
- Explicit submit button
- Set comparison scoring (partial credit)
- ~LOW frontend cost, ~LOW backend cost

---

## 12. Cross-Cutting Themes

### 12.1 Card-as-Object Metaphor

ALL non-diagram mechanics (sequencing, sorting, memory_match, branching) need items rendered as rich cards with borders, shadows, images, internal layout. This is the single highest-impact visual upgrade across mechanics.

### 12.2 Configuration-Driven Rendering

All research documents propose extensive config schemas that drive visual rendering. Same component renders multiple modes based on config — not hard-coded mechanic-specific logic. Aligns with CLAUDE.md: "never hardcode mechanic-specific logic."

### 12.3 Animation as Core Game Feel

Every research doc specifies detailed animation sequences with specific timing (ms), easing functions, and CSS transforms. These transform "homework" into "game." Priority animations:
- Snap/bounce on placement (all drag mechanics)
- 3D card flip (memory_match)
- Animated particles along paths (trace_path)
- Staggered reveal cascades (sequencing, sorting)
- Confetti/celebration on completion (all)

### 12.4 Assessment Integrity

All mechanics must support both formative (immediate feedback) and summative (deferred evaluation) modes. Never reveal correct answers during active assessment. Shuffle must be truly random. Distractor items are valuable.

### 12.5 Accessibility Requirements (Universal)

| Requirement | Implementation |
|-------------|---------------|
| Keyboard navigation | Tab + Enter/Space for all interactions |
| Click-to-place alternative | For all drag-and-drop mechanics |
| Screen reader | aria-labels on all interactive elements |
| Reduced motion | `prefers-reduced-motion` disables animations |
| Color independence | Icons/patterns in addition to color for state |
| Touch targets | Minimum 44x44px |

---

## 13. Previously Applied Fixes (This Session)

| Fix | File | Status |
|-----|------|--------|
| max_iterations 8→15 | scene_architect_v3, interaction_designer_v3, asset_generator_v3 | APPLIED |
| max_iterations 4→6 | blueprint_assembler_v3 | APPLIED |
| System prompt rewrite (all 10 mechanics) | scene_architect_v3 | APPLIED |
| System prompt rewrite (scoring/feedback) | interaction_designer_v3 | APPLIED |
| Task prompt rewrite (check_capabilities) | game_designer_v3 | APPLIED |
| System+task prompt rewrite (mechanic-aware) | asset_generator_v3 | APPLIED |
| Validator: compare+hierarchical checks | design_validator | APPLIED |
| Validator: 3 missing trigger mechanics | interaction_spec_v3 | APPLIED |
| Validator: compare validation | scene_spec_v3 | APPLIED |
| Validator: penalties -0.05→-0.1 | design_validator | APPLIED |
| Asset submit: scene count warning | asset_generator_tools | APPLIED |
| Multi-scene URL proxying | routes/generate.py | APPLIED |
| Asset key mismatch fix | asset_generator_tools | APPLIED (earlier session) |
| Auto-clean in search_diagram_image | asset_generator_tools | APPLIED (earlier session) |
| Mechanic-aware image hints | asset_generator_tools | APPLIED (earlier session) |
| Fuzzy label matching | blueprint_assembler_tools | APPLIED (earlier session) |

---

## 14. Gap Count Summary

| Category | Count |
|----------|-------|
| Backend schema field gaps | ~124 |
| Frontend schema field gaps | ~94 |
| State field gaps | ~15 |
| Backend tool gaps | 22+ |
| New tools needed | 11 |
| Frontend component gaps | ~63 new components |
| Frontend bugs | 6 critical |
| Graph/routes/services findings | 18 (5 CRITICAL) |
| Architecture changes needed | 6 |
| Prompt rewrites needed | 7 (4 APPLIED) |
| Validator fixes needed | 3 (3 APPLIED) |
| **Total unique issues** | **~370+** |
