# Research vs Reality: Comprehensive Gap Analysis

**Date**: 2026-02-11
**Source**: 14 research documents (`docs/audit/research/01-14`) cross-referenced against current codebase
**Scope**: Every research recommendation mapped to current implementation status

---

## Executive Summary

The research documents define **~500+ specific requirements** across 10 existing mechanics + 10 new mechanics + hierarchical chaining. The current codebase implements **~25-35%** of these. The primary gaps:

1. **Agent prompts applied, tools partially done, configs partially done** — Phases 0-3 of the previous plan are mostly applied
2. **Frontend components exist but lack research-defined richness** — Each mechanic has a working component but with 10-30% of research-defined features
3. **Asset pipeline is diagram-only** — No dual images, per-item images, character sprites, scene backgrounds
4. **Blueprint assembler forwards configs but doesn't populate missing fields** — Per-mechanic configs ARE forwarded, but repair only covers 2/10 mechanics
5. **10 new mechanics completely missing** — No schemas, agents, tools, or components
6. **Hierarchical chaining completely missing** — No DAG engine, no navigation stack, no hub-and-spoke

---

## Section 1: Per-Mechanic Comparison (Existing 10 Mechanics)

### 1.1 DRAG_DROP

| Research Requirement | Status | Details |
|---|---|---|
| Leader lines (SVG overlay, 4 styles) | MISSING | No LeaderLineOverlay component. No SVG path rendering |
| Click-to-place interaction mode | MISSING | Only drag-drop exists. No `interaction_mode` config |
| Reverse mode (zone highlights, student picks label) | MISSING | No ReverseMode component |
| Label-from-bank / type-in mode | MISSING | No text input mode |
| 4 label card types (text, icon, thumbnail, description) | MISSING | Only text labels exist |
| 7 label states (idle, dragging, hover_over_zone, placed_correct, placed_incorrect, distractor_rejected, disabled) | PARTIAL | Has some states but not all 7 |
| Spring physics snap animation | MISSING | No physics-based animation |
| 4 tray layouts (horizontal, vertical, grid, grouped) | MISSING | Only horizontal tray |
| Zoom/pan canvas (react-zoom-pan-pinch) | MISSING | No zoom capability |
| Info panel (learn mode, structure details) | MISSING | No InfoPanel component |
| Distractor management (rejection mode, reveal style) | PARTIAL | Distractors exist but no configurable rejection/reveal |
| DragDropConfig (35+ fields) | MISSING | No DragDropConfig type in frontend or backend |
| Pin markers at zone anchor points | MISSING | No PinMarker component |
| Zone shape rendering (circle, polygon, rect, freeform) | PARTIAL | Has polygon/circle but no freeform |
| WCAG 2.5.7 keyboard alternative toggle | MISSING | No visible toggle for click-to-place |
| Backend: leader line anchor generation | MISSING | No post-processing step |
| Backend: DragDropConfig generation in pipeline | MISSING | No agent generates this config |

### 1.2 CLICK_TO_IDENTIFY

| Research Requirement | Status | Details |
|---|---|---|
| PromptBanner component (prompt + progress counter) | PARTIAL | HotspotManager has prompts but no dedicated banner |
| 6-state ZoneHighlightStateMachine | MISSING | Fixed highlight states, no configurable state machine |
| MagnificationLens (floating circular zoom) | MISSING | No magnification component |
| ExploreTestController (2-phase: explore then test) | MISSING | No explore-then-test mode |
| Sequential vs any_order selection modes | EXISTS | HotspotManager supports both |
| Zone highlight styles (subtle/outlined/invisible) | MISSING | Fixed highlight style |
| ClickToIdentifyConfig (18+ fields) | PARTIAL | Backend `ClickDesign` exists (8 fields). Frontend type MISSING |
| Backend: per-zone functional prompt generation | EXISTS | `generate_mechanic_content` handles click_to_identify |
| Backend: prompt_style naming vs functional | PARTIAL | Config has prompt_style but prompts are generic |
| Zone label leak in any_order mode | FIXED | Already patched in HotspotManager |

### 1.3 TRACE_PATH

| Research Requirement | Status | Details |
|---|---|---|
| SVG curved paths (not straight lines) | MISSING | PathDrawer uses straight lines between waypoints |
| AnimatedParticleSystem (5 themes: dots/arrows/droplets/cells/electrons) | MISSING | No particle system |
| ColorTransitionEngine (start_color → end_color per segment) | MISSING | No color transitions |
| DirectionalArrowOverlay (SVG markers along path) | MISSING | No direction arrows |
| Gate/valve waypoints with open/close animation | MISSING | No gate waypoint type |
| Freehand drawing mode | MISSING | Only click-waypoints mode |
| 3 path types (linear/branching/circular) | MISSING | Only linear paths |
| TracePathConfig (20+ fields) | PARTIAL | Backend `PathDesign` exists (8 fields). Frontend type MISSING |
| Backend: SVG path data generation | MISSING | No tool generates SVG curves |
| Backend: waypoint type (standard/gate/branch/terminus) | MISSING | All waypoints are standard |
| Waypoint states (unvisited/next/visited/gate) | PARTIAL | Has basic progress tracking |

### 1.4 SEQUENCING

| Research Requirement | Status | Details |
|---|---|---|
| 5 layout modes (horizontal/vertical/circular/flowchart/insert-between) | MISSING | Only vertical list with drag reorder |
| 5 card types (image_text, image_only, text_only, icon_text, numbered) | MISSING | Text-only cards |
| Item cards with image/icon/description | MISSING | Text-only items |
| Connecting arrows/connectors (6 styles) | MISSING | No connectors between placed items |
| Track/lane background with slot indicators | MISSING | No track/lane UI |
| 4 slot/drop target styles | MISSING | Basic drop zones |
| 4 item source area configurations | MISSING | Single list |
| 4 interaction patterns (drag_reorder, drag_to_slots, insert_between, click_to_place) | PARTIAL | Only drag-to-reorder |
| Progressive reveal (draw pile, one at a time) | MISSING | All items shown at once |
| Distractor items | MISSING | No distractor support in sequencing |
| Per-item images from pipeline | MISSING | No per-item image generation tool |
| SequencingConfig (25+ fields) | PARTIAL | Backend SequenceDesign has 10 fields (SequenceItem 8 fields). Frontend SequenceConfig has ~15 fields |
| Backend: instruction_text generation | MISSING | Not in generate_mechanic_content output |
| Kendall tau / longest subsequence scoring | MISSING | Basic position scoring only |

### 1.5 SORTING_CATEGORIES

| Research Requirement | Status | Details |
|---|---|---|
| 5 sort modes (bucket/venn_2/venn_3/matrix/column) | MISSING | Only bucket sort |
| VennDiagram (2/3 circle with SVG overlap regions) | MISSING | No Venn diagram component |
| MatrixGrid (Carroll diagram, 2D grid) | MISSING | No matrix component |
| 5 item card types (text/icon/image/rich_card) | MISSING | Text-only cards |
| Category icons/header images/colors | MISSING | Basic category headers only |
| 4 submit modes (batch/immediate/round_based/lock_on_place) | MISSING | Only batch submit |
| Multi-category items (Venn: item belongs to multiple) | MISSING | Single category only |
| Iterative correction (incorrect return to pool, re-sort) | MISSING | No round-based correction |
| Pool layouts (horizontal_tray/wrapped_grid/scattered/stacked_deck) | MISSING | Single grid pool |
| Per-item images from pipeline | MISSING | No per-item image generation |
| Per-category icons from pipeline | MISSING | No category icon generation |
| SortingConfig (25+ fields) | PARTIAL | Backend SortingDesign has ~10 fields. Frontend SortingConfig has ~15 fields |
| Backend: `correct_category_ids` as LIST (not single string) | FIXED | Already uses `correct_category_ids: List[str]` |
| Backend: matrix/Venn-specific fields | MISSING | No matrix or Venn config fields |

### 1.6 DESCRIPTION_MATCHING

| Research Requirement | Status | Details |
|---|---|---|
| 3 interaction modes (drag_to_zone/click_match/multiple_choice) | EXISTS | DescriptionMatcher supports all 3 |
| ConnectingLineRenderer (SVG curved lines, crossing minimization) | MISSING | No connecting lines between matches |
| 6-state DescriptionCardStateMachine | PARTIAL | Has some states but not all 6 |
| ZoneProximityHighlighter (glow when dragging near zone) | MISSING | No proximity highlighting |
| DeferredEvaluationController (submit-all mode) | MISSING | Only immediate evaluation |
| 4 description styles (functional/structural/process/clinical) | MISSING | Generic descriptions only |
| Distractor descriptions (plausible wrong descriptions) | MISSING | No distractor support |
| DescriptionMatchingConfig (15+ fields) | PARTIAL | Backend DescriptionMatchDesign has 7 fields. Frontend config is minimal |
| MC option re-shuffle bug | FIXED | Already memoized with useMemo |
| Backend: LLM-generated functional descriptions | EXISTS | generate_mechanic_content handles this |

### 1.7 MEMORY_MATCH

| Research Requirement | Status | Details |
|---|---|---|
| True 3D CSS flip (perspective + preserve-3d + rotateY + backface-visibility) | FIXED | Already patched |
| 5 game variants (classic/column_match/scatter/progressive/peek) | MISSING | Only classic grid |
| 7 match types (identical/term_definition/image_label/concept_example/cause_effect/part_whole/diagram_region) | MISSING | Only term_to_definition |
| 6 card back styles (solid_gradient/pattern/themed/question_mark/numbered/custom) | MISSING | Single default back style |
| 6 card face types (text/image/diagram_closeup/mixed/equation/audio) | MISSING | Text-only faces |
| Diagram closeup (crop from zone coordinates with padding) | MISSING | No crop region calculation |
| Explanation reveal on match | MISSING | No explanation popup |
| 4 matched card behaviors (fade/shrink/collect/checkmark) | MISSING | Single behavior |
| 4 mismatch penalty modes (none/score_decay/life_loss/time_penalty) | MISSING | No penalty modes |
| Progressive unlock (start with 3 pairs, add 2 per round) | MISSING | All pairs shown at once |
| Column match layout | MISSING | No column match component |
| Scatter layout | MISSING | No scatter component |
| Configurable flip duration/axis/easing | MISSING | Hardcoded flip animation |
| Per-card images from pipeline | MISSING | No card image generation |
| MemoryMatchConfig (30+ fields) | PARTIAL | Backend MemoryMatchDesign has ~9 fields. Frontend MemoryMatchConfig has ~15 fields |
| Backend: crop region calculation from zone coordinates | MISSING | No crop region tool |
| Backend: card_face_type/card_back_style/match_type | PARTIAL | Fields exist in schema but not populated by tools |

### 1.8 BRANCHING_SCENARIO

| Research Requirement | Status | Details |
|---|---|---|
| SceneBackgroundLayer (full-width background with transitions) | MISSING | No background images |
| CharacterSpriteLayer (1-3 characters with expression swapping) | MISSING | No character sprites |
| DialogueBox (4 modes: bottom_panel/speech_bubble/side_panel/overlay) | MISSING | No dialogue box component |
| StateDisplay (vital signs/resources/inventory/relationships) | MISSING | No state variable display |
| DecisionMinimap (fog_of_war/full/progressive/post_game_only) | MISSING | No minimap |
| ConsequenceOverlay (animated consequences) | MISSING | No consequence visualization |
| EndingScreen (4 types: optimal/acceptable/suboptimal/failure) | MISSING | No ending screen |
| 4 choice styles (buttons/cards/dialogue_options/action_list) | PARTIAL | Basic buttons only |
| 6 narrative structures (branch_and_bottleneck/foldback/gauntlet/time_cave/parallel/loop) | MISSING | No narrative structure support |
| 7 character expressions per character | MISSING | No character system |
| 5 transition effects (dissolve/crossfade/slide/fade_to_black/blur_refocus) | MISSING | No transition effects |
| State variables with threshold/icon/display_format | MISSING | No state variable system |
| 4-level decision quality (optimal/acceptable/suboptimal/harmful) | MISSING | Binary is_correct only |
| Consequence timing (immediate/delayed/hidden) | MISSING | All consequences immediate |
| BranchingConfig (40+ fields) | PARTIAL | Backend BranchingDesign has ~6 fields. Frontend BranchingConfig has ~10 fields |
| Backend: character sprite generation tool | MISSING | No character generation |
| Backend: scene background generation tool | MISSING | No background generation |
| Backend: state system generation tool | MISSING | No state system tool |
| Backend: decision tree DAG validation | MISSING | No DAG validation |

### 1.9 COMPARE_CONTRAST

| Research Requirement | Status | Details |
|---|---|---|
| 5 comparison modes (slider/side_by_side/overlay/venn/spot_difference) | MISSING | Only side-by-side categorization |
| ImageComparisonSlider (react-compare-slider) | MISSING | No slider component |
| OverlayTransparencyController | MISSING | No overlay mode |
| VennDiagramCategorizer (drag items into Venn regions) | MISSING | No Venn mode |
| SpotTheDifference (click to find differences) | MISSING | No spot-the-difference mode |
| SynchronizedZoomPanels (react-zoom-pan-pinch, synced) | MISSING | No zoom/pan |
| ZonePairingLines (SVG lines connecting corresponding zones) | MISSING | No pairing lines |
| ExplorePhaseOverlay (explore-then-categorize two-phase) | MISSING | No explore phase |
| Dual-diagram pipeline (TWO matched images) | MISSING | Single-image pipeline only |
| Zone pairing agent (match zones across two images) | MISSING | No zone pairing |
| State fields: diagram_image_b, zones_b, zone_pairings | MISSING | Not in AgentState |
| Category customization (custom types/labels/colors) | MISSING | 4 hardcoded categories |
| CompareConfig (20+ fields) | PARTIAL | Backend CompareDesign has ~9 fields. Frontend CompareConfig has ~10 fields |
| Anti-cheat click throttling (spot-the-difference) | MISSING | No throttling |
| Backend: generate_dual_diagram tool | MISSING | No dual-image tool |
| Backend: zone_pairing tool | MISSING | No pairing tool |

### 1.10 HIERARCHICAL

| Research Requirement | Status | Details |
|---|---|---|
| Zone hierarchy (parent-child reveal) | EXISTS | Supported in backend and frontend |
| reveal_trigger: complete_parent | EXISTS | Works in pipeline |
| Nested mechanic zooming (CSS transform) | MISSING | No zoom-into-zone support |
| Breadcrumb navigation | MISSING | No BreadcrumbNav |
| HierarchicalConfig | PARTIAL | Basic config exists |

---

## Section 2: Pipeline Stage Gap Matrix

### 2.1 Domain Knowledge Retriever

| Mechanic | DK Fields Used | DK Fields Available But Unused | Gap |
|---|---|---|---|
| drag_drop | canonical_labels | label_descriptions | LOW |
| click_to_identify | canonical_labels | label_descriptions (for functional prompts) | MEDIUM |
| trace_path | canonical_labels | sequence_flow_data, spatial_data | HIGH |
| sequencing | canonical_labels, sequence_flow_data | process_steps | MEDIUM |
| sorting_categories | canonical_labels | — (no sorting DK fields) | HIGH |
| description_matching | canonical_labels | label_descriptions | MEDIUM |
| memory_match | canonical_labels | term_definitions | HIGH |
| branching_scenario | canonical_labels | causal_relationships | HIGH |
| compare_contrast | canonical_labels | comparison_data | MEDIUM |

**Summary**: Only **~9.2%** of DK agent-field pairs are consumed. Biggest gap: no sorting/memory/branching-specific DK generation.

### 2.2 Game Designer v3

| Issue | Status | Detail |
|---|---|---|
| Bloom's level injection in task prompt (L131, L142-143) | EXISTS (BUG) | Still injects `blooms_level` section |
| `analyze_pedagogy` forces drag_drop (L108-112) | EXISTS (BUG) | "always available" insertion |
| Per-mechanic config data in design | APPLIED | Task prompt (L214-224) lists config requirements per mechanic |
| `check_capabilities` mandatory | APPLIED | Task prompt step 3 mandates it |
| DK sub-field injection (sequence_flow_data, label_descriptions, etc.) | APPLIED | Lines 153-167 inject 4 sub-fields |
| DK truncation to 2000 chars | EXISTS (BUG) | Line 147 limits DK text |
| Missing DK fields: process_steps, term_definitions, causal_relationships, hierarchical_data, spatial_data | MISSING | Only 4 of 13 DK fields injected |
| Content-to-mechanic fitness evaluation | MISSING | No systematic matching framework |
| 10 new mechanics from research doc 08 | MISSING | Not in system prompt or check_capabilities |

### 2.3 Scene Architect v3

| Issue | Status | Detail |
|---|---|---|
| System prompt covers all 10 mechanics | APPLIED | Lines 27-100 cover all mechanics |
| generate_mechanic_content mandatory | APPLIED | Steps 3 explicitly mandated |
| Per-mechanic config guidelines | APPLIED | Each mechanic has config example |
| DK injection in task prompt | MISSING | Only game_design summary + canonical_labels injected. No label_descriptions, sequence_flow_data, etc. |
| Config guidelines are minimal (1-line examples) | EXISTS (GAP) | Research requires 10-25 properties per mechanic |
| compare_contrast LLM fallback missing | EXISTS (BUG) | Tools audit: no LLM fallback when comparison_data missing |
| memory_match pair generation quality | EXISTS (GAP) | Generic fallback descriptions |
| branching node DAG validation | MISSING | No cycle detection or orphan checking |
| New mechanics from doc 08 | MISSING | Not supported |

### 2.4 Interaction Designer v3

| Issue | Status | Detail |
|---|---|---|
| Per-mechanic scoring strategy guidance | APPLIED | System prompt L27-93 has per-mechanic guidance |
| enrich_mechanic_content mandatory | APPLIED | Step 2 mandated |
| DK injection in task prompt | MISSING | No DK fields injected at all |
| Per-mechanic scoring FIELD validation | MISSING | Generic MechanicScoringV3 |
| Misconception feedback model is drag_drop-biased | EXISTS (BUG) | trigger_label + trigger_zone model |
| Per-mechanic enrichment quality | PARTIAL | enrich_mechanic_content has per-mechanic prompts but basic |
| validate_interactions content checks | MISSING for 4 | Missing: sorting, memory_match, branching, compare_contrast |
| New mechanics from doc 08 | MISSING | Not supported |

### 2.5 Asset Generator v3

| Issue | Status | Detail |
|---|---|---|
| Mechanic-aware system prompt | APPLIED | Lines 28-70 have mechanic-specific guidance |
| Mechanic-aware image hints | APPLIED | `_MECHANIC_IMAGE_HINTS` in tools |
| Dual-image pipeline (compare_contrast) | MISSING | 100% single-image pipeline |
| Per-item image generation (sequencing/sorting/memory) | MISSING | No per-item tool |
| Character sprite generation (branching) | MISSING | No character tool |
| Scene background generation (branching) | MISSING | No background tool |
| Card image generation (memory_match) | MISSING | No card image tool |
| Category icon generation (sorting) | MISSING | No icon tool |
| SVG path generation (trace_path) | MISSING | No SVG tool |
| submit_assets scene count validation | MISSING | No warning on incomplete scenes |

### 2.6 Blueprint Assembler v3

| Issue | Status | Detail |
|---|---|---|
| Per-mechanic config forwarding | APPLIED | tracePathConfig, clickToIdentifyConfig, sequenceConfig, sortingConfig, memoryMatchConfig, branchingConfig, compareConfig all forwarded |
| Scoring/feedback list→dict conversion | APPLIED | Properly done |
| Fuzzy label matching | APPLIED | _normalize_label + _build_zone_lookup |
| validate_blueprint covers all 9 mechanics | APPLIED | Checks required config fields |
| repair_blueprint covers all mechanics | PARTIAL | Only click_to_identify + trace_path. **Missing 6 mechanics** |
| mechanic_type at scene level | MISSING | Not set in frontend scene object |
| tasks field forwarding | MISSING | Not forwarded from interaction specs |
| mode_transitions forwarding | APPLIED | Forwarded properly |
| Dual-diagram support | MISSING | Single diagram per scene |
| Character/sprite/background references | MISSING | No branching visual assets |
| Per-item image URL forwarding | MISSING | No item images to forward |
| mechanicGraph (DAG) field | MISSING | No hierarchical chaining support |

### 2.7 Design Validator

| Issue | Status | Detail |
|---|---|---|
| Mechanic config validation severity | APPLIED | Penalties increased from -0.05 to -0.1 |
| compare_contrast validation | APPLIED | Added |
| hierarchical validation | APPLIED | Added |
| Config CONTENT validation (not just existence) | MISSING | Only checks existence, not field counts/quality |
| 10 new mechanics from doc 08 | MISSING | Not in VALID_MECHANIC_TYPES |

### 2.8 Scene Validator

| Issue | Status | Detail |
|---|---|---|
| Mechanic config presence checks | EXISTS | Checks all mechanics |
| Cross-mechanic zone coverage validation | MISSING | Doesn't verify zones referenced by configs actually exist |
| Config content quality checks | MISSING | Only presence, not quality |
| compare_contrast validation | APPLIED | Added |

### 2.9 Interaction Validator

| Issue | Status | Detail |
|---|---|---|
| Bloom's cognitive mapping (IV-1) | EXISTS (BUG) | Still uses blooms_cognitive dict |
| auto_fix_design defaults to drag_drop (IV-2) | EXISTS (BUG) | Still defaults unknown modes to drag_drop |
| Missing completion triggers (sorting, memory, branching, compare) | PARTIAL | Some added to MECHANIC_TRIGGER_MAP |

---

## Section 3: Frontend Component Gap Summary

| Component | Lines | Research Components Needed | Currently Has | Gap % |
|---|---|---|---|---|
| SequenceBuilder.tsx | 319 | 8 new components + 12 interaction patterns + 14 config properties | Drag-reorder list | ~90% |
| SortingCategories.tsx | 404 | 8 new components + 9 patterns + 11 config properties | Basic bucket sort | ~85% |
| MemoryMatch.tsx | 310 | 10 new components + 8 patterns + 13 config properties | Classic grid (flip fixed) | ~85% |
| BranchingScenario.tsx | 360 | 10 new components + 9 patterns + 10 config properties | Basic decision buttons | ~90% |
| CompareContrast.tsx | 301 | 9 new components + 10 patterns + 13 config properties | Side-by-side categorization | ~90% |
| HotspotManager.tsx | 296 | 7 new components + 8 patterns + 8 config properties | Click-to-identify (label leak fixed) | ~70% |
| PathDrawer.tsx | 397 | 9 new components + 11 patterns + 10 config properties | Click-waypoint straight lines | ~85% |
| DescriptionMatcher.tsx | 517 | 7 new components + 8 patterns + 10 config properties | 3 modes (MC fix applied) | ~65% |
| DiagramCanvas.tsx | 386 | 9 new components + 10 patterns + 10 config properties | Basic drag-drop | ~80% |

**Total**: ~63 new React components needed, ~85 new config properties across all interaction types.

---

## Section 4: Zustand Store Gaps

| Gap | Status | Detail |
|---|---|---|
| Score reset on mode transition (L1517: `score: 0`) | EXISTS (BUG) | Should preserve score |
| Score OVERWRITES in updatePathProgress/updateIdentificationProgress/recordDescriptionMatch | EXISTS (BUG) | Should ADD deltas |
| advanceToNextTask max_score = actual score | EXISTS (BUG) | Percentage always 100% |
| Mode transition setTimeout leak | EXISTS (BUG) | Timer never cleaned up |
| transitionToMode mutates modeHistory in-place | EXISTS (BUG) | Zustand immutability violation |
| _sceneToBlueprint missing config forwarding (click/trace/dragDrop) | EXISTS (BUG) | Doesn't forward 3 config types |
| Missing state: zoomLevel, panOffset | MISSING | No zoom/pan state |
| Missing state: explorationPhase | MISSING | No explore phase state |
| Missing state: stateVariables (branching) | MISSING | No branching state vars |
| Missing state: matchedPairVisualState | MISSING | No memory match visual state |
| Missing state: leaderLineConnections | MISSING | No leader line state |
| Missing actions: setZoomLevel, setPanOffset | MISSING | No zoom actions |
| Missing actions: startExplorationPhase, endExplorationPhase | MISSING | No explore actions |
| Missing actions: updateStateVariable | MISSING | No branching actions |
| Missing actions: setPlacementMode | MISSING | No placement mode switching |

---

## Section 5: New Mechanics (Research Doc 08) — Completely Missing

All 10 new mechanics have **ZERO** implementation:

| Mechanic | Priority | Backend Schema | Backend Tool | Frontend Component | Zustand State |
|---|---|---|---|---|---|
| predict_observe_explain | HIGH | MISSING | MISSING | MISSING | MISSING |
| spot_the_error | HIGH | MISSING | MISSING | MISSING | MISSING |
| cloze_fill_blank | HIGH | MISSING | MISSING | MISSING | MISSING |
| hotspot_multi_select | HIGH | MISSING | MISSING | MISSING | MISSING |
| cause_effect_chain | MEDIUM-HIGH | MISSING | MISSING | MISSING | MISSING |
| claim_evidence_reasoning | MEDIUM | MISSING | MISSING | MISSING | MISSING |
| process_builder | MEDIUM | MISSING | MISSING | MISSING | MISSING |
| measurement_reading | MEDIUM | MISSING | MISSING | MISSING | MISSING |
| elimination_grid | MEDIUM | MISSING | MISSING | MISSING | MISSING |
| annotation_drawing | MEDIUM | MISSING | MISSING | MISSING | MISSING |

---

## Section 6: Hierarchical Chaining (Research Doc 09) — Completely Missing

| Requirement | Status |
|---|---|
| MechanicDAG schema (backend Pydantic) | MISSING |
| MechanicDAG types (frontend TypeScript) | MISSING |
| DAG validation (acyclic, topological sort) | MISSING |
| Gate nodes (AND/OR/N_OF_M/SCORE_THRESHOLD) | MISSING |
| 7 chaining patterns (sequential/parallel/prerequisite/nested/conditional/recursive/hub_spoke) | MISSING — only sequential `modeTransitions` exists |
| NavigationStack (push/pop mechanic frames) | MISSING |
| BreadcrumbNav component | MISSING |
| ProgressMiniMap component | MISSING |
| MechanicViewport (zoom transitions between parent/child) | MISSING |
| HubDiagram component | MISSING |
| ScorePanel (composite aggregation) | MISSING |
| `mechanicGraph` field on blueprint | MISSING |
| `modeTransitionsToDAG()` desugaring | MISSING |
| Game planner chaining pattern selection | MISSING |
| Blueprint assembler DAG output | MISSING |
| Hierarchical asset generation | MISSING |

---

## Section 7: Remaining Bugs from Audit Docs 10-14

### CRITICAL (Must Fix)

| Bug | File | Detail |
|---|---|---|
| Bloom's level injection | game_designer_v3.py L131,142 | Still injected into task prompt |
| analyze_pedagogy forces drag_drop | game_design_v3_tools.py L108-112 | Inserts drag_drop if not present |
| Bloom's cognitive mapping | interaction_validator.py L129-136 | Uses Bloom's for mechanic compatibility |
| auto_fix_design defaults to drag_drop | interaction_validator.py L350 | Unknown modes → drag_drop |
| compare_contrast no LLM fallback | scene_architect_tools.py L383-396 | If comparison_data missing → generates NOTHING |
| misconception feedback drag_drop-biased model | interaction_designer_tools.py L140-170 | trigger_label + trigger_zone model |
| repair_blueprint missing 6 mechanics | blueprint_assembler_tools.py | Only click_to_identify + trace_path |
| Score reset on mode transition | useInteractiveDiagramState.ts ~L1517 | `score: 0` kills cumulative score |
| Score overwrites (3 locations) | useInteractiveDiagramState.ts L458,475,645 | Replace instead of delta-add |
| advanceToNextTask max_score bug | useInteractiveDiagramState.ts ~L1026 | max_score = actual → always 100% |
| _sceneToBlueprint missing 3 configs | useInteractiveDiagramState.ts | click/trace/dragDrop not forwarded |

### HIGH (Should Fix)

| Bug | File | Detail |
|---|---|---|
| DK truncation to 2000 chars | game_designer_v3.py L147 | Loses info for complex topics |
| DK: 5 of 13 fields used by game_designer | game_designer_v3.py | Missing 8 DK fields |
| scene_architect reads 1 of 13 DK fields | scene_architect_v3.py | Only canonical_labels |
| interaction_designer reads 0 of 13 DK fields | interaction_designer_v3.py | No DK injection |
| mechanic_type not set at scene level | blueprint_assembler_tools.py | Frontend can't determine mechanic per scene |
| tasks field not forwarded | blueprint_assembler_tools.py | Interaction spec tasks lost |
| setTimeout leak in mode transition | useInteractiveDiagramState.ts ~L858 | Timer never cleared |
| transitionToMode Zustand immutability violation | useInteractiveDiagramState.ts ~L874 | Mutates modeHistory in-place |
| `highlightMatching` dead field in CompareContrast | CompareContrast.tsx | Config field never read |
| Gemini diagram service flower-specific prompt | gemini_diagram_service.py | Hardcoded "flower illustration" |

---

## Section 8: What's Already Working

To be fair, here's what the previous implementation sessions DID fix:

| Fix | Status |
|---|---|
| Phase 0: V3 image serving route | DONE |
| Phase 0: Retry off-by-one (>=2 → >=3) | DONE |
| Phase 0: DomainKnowledge TypedDict fields (query_intent, suggested_reveal_order, scene_hints) | DONE |
| Phase 0: V3 agent output recording | DONE |
| Phase 0: Topology metadata fix | DONE |
| Phase 0: Bloom's softened to "informational context only" (comment) | DONE (but code still forces drag_drop) |
| Phase 1: Rich Pydantic schemas for all 10 mechanics | DONE |
| Phase 1: Frontend TypeScript types expanded | DONE |
| Phase 1: State fields for per-item images | DONE |
| Phase 2: generate_mechanic_content (all 10 mechanics) | DONE |
| Phase 2: enrich_mechanic_content (per-mechanic prompts) | DONE |
| Phase 2: misconception feedback mechanic-aware | DONE (but trigger model still biased) |
| Phase 3: Agent prompts rewritten (scene_architect, interaction_designer, game_designer, asset_generator) | DONE |
| Phase 3: check_capabilities readiness updated | DONE |
| Phase 4: Blueprint assembler expanded config forwarding (all 8 mechanics) | DONE |
| Phase 4: Blueprint validate + repair for memory/branching/compare | PARTIAL (repair missing 6) |
| Phase 5: Score reset fix | **NOT DONE** (still `score: 0`) |
| Phase 5: _sceneToBlueprint config forwarding | **NOT DONE** |
| Phase 5: correctCategoryIds | DONE |
| Phase 6: HotspotManager zone label leak | DONE |
| Phase 6: MemoryMatch CSS flip | DONE |
| Phase 6: DescriptionMatcher MC memoize | DONE |
| First successful V3 run (run e54e89f7) | DONE |

---

## Section 9: Priority Fix Order

### Tier 1: Critical Bugs (must fix for ANY mechanic to work reliably)

1. **Score reset on mode transition** — `score: 0` → `score: get().score`
2. **Score overwrites** (3 locations) — Replace → delta-add
3. **advanceToNextTask max_score** — Use config max_score, not actual
4. **_sceneToBlueprint missing configs** — Forward click/trace/dragDrop configs
5. **mechanic_type at scene level** — Set in blueprint assembler
6. **Bloom's drag_drop forcing** — Remove forced insertion in analyze_pedagogy
7. **Bloom's cognitive mapping** — Remove from interaction_validator
8. **auto_fix_design drag_drop default** — Remove fallback
9. **compare_contrast LLM fallback** — Add fallback in generate_mechanic_content
10. **repair_blueprint missing 6 mechanics** — Add repair logic for seq/sort/memory/desc/branch/compare

### Tier 2: Data Flow (needed for non-drag_drop quality)

11. **DK injection into scene_architect** — Inject label_descriptions, sequence_flow_data, etc.
12. **DK injection into interaction_designer** — Inject DK for pedagogical enrichment
13. **misconception feedback model** — Per-mechanic trigger models
14. **tasks field forwarding** — Forward from interaction specs to blueprint
15. **DK truncation** — Increase from 2000 chars or use structured extraction
16. **Zustand bugs** — setTimeout leak, modeHistory mutation, completion counting

### Tier 3: Frontend Richness (needed for quality games)

17-25. Per-mechanic component upgrades (leader lines, SVG paths, Venn diagrams, etc.)

### Tier 4: Asset Pipeline Expansion (needed for non-diagram mechanics)

26. Dual-image pipeline for compare_contrast
27. Per-item image generation for sequencing/sorting/memory
28. Character sprite generation for branching
29. Scene background generation for branching

### Tier 5: New Mechanics (Phase 8, deferred)

30-39. 10 new mechanics from research doc 08

### Tier 6: Hierarchical Chaining (Phase 7, deferred)

40-55. DAG engine, navigation, hub-and-spoke, etc.

---

## Appendix: File-Level Fix Map

| File | Fixes Needed |
|---|---|
| `backend/app/tools/game_design_v3_tools.py` | Remove drag_drop forcing (L108-112) |
| `backend/app/agents/game_designer_v3.py` | Remove Bloom's injection (L131,142-143), increase DK limit |
| `backend/app/agents/interaction_validator.py` | Remove Bloom's mapping (L129-136), remove drag_drop default (L350) |
| `backend/app/agents/scene_architect_v3.py` | Add DK injection to build_task_prompt |
| `backend/app/agents/interaction_designer_v3.py` | Add DK injection to build_task_prompt |
| `backend/app/tools/scene_architect_tools.py` | Fix compare_contrast LLM fallback |
| `backend/app/tools/interaction_designer_tools.py` | Fix misconception trigger model |
| `backend/app/tools/blueprint_assembler_tools.py` | Add repair for 6 mechanics, set mechanic_type, forward tasks |
| `frontend/.../hooks/useInteractiveDiagramState.ts` | Fix score reset, score overwrites, max_score bug, config forwarding, setTimeout leak, modeHistory mutation |
| `frontend/.../interactions/*.tsx` | Per-mechanic component upgrades (63 new components per research) |
