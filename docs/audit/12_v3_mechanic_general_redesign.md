# V3 Pipeline Mechanic-General Redesign

**Date**: 2026-02-11
**Scope**: Complete architectural redesign of the V3 pipeline to make every mechanic a first-class citizen with rich visual assets, engaging interactions, and full end-to-end data flow.
**Status**: ARCHITECTURAL REVIEW — awaiting sign-off before implementation

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Mechanic Inventory & Classification](#2-mechanic-inventory--classification)
3. [Per-Mechanic Rich Asset Requirements](#3-per-mechanic-rich-asset-requirements)
4. [Potential New Mechanics](#4-potential-new-mechanics)
5. [Current Pipeline Status Matrix](#5-current-pipeline-status-matrix)
6. [Root Cause Analysis](#6-root-cause-analysis)
7. [Architecture Redesign: Quality Gate + Send API](#7-architecture-redesign-quality-gate--send-api)
8. [Per-Phase Redesign Details](#8-per-phase-redesign-details)
9. [Frontend Component Enhancement Plan](#9-frontend-component-enhancement-plan)
10. [Multi-Mechanic Scene Chaining](#10-multi-mechanic-scene-chaining)
11. [Fix Catalog](#11-fix-catalog)
12. [Implementation Order](#12-implementation-order)
13. [Verification Plan](#13-verification-plan)

---

## 1. Design Principles

1. **Every mechanic is a first-class citizen.** No special preference to drag_drop. Every mechanic deserves rich visual assets, engaging interactions, and polished feedback — not just a data structure rendered as a list.

2. **Scene = unique image boundary.** Two scenes should NOT be planned unless they need completely different visual contexts. One scene can host multiple mechanics sequentially.

3. **Task = mechanic/phase within a scene.** A scene with multiple mechanics creates multiple tasks. Each task filters zones/labels to the relevant subset.

4. **Rich Minimum Viable Assets (MVA) per mechanic.** Every mechanic defines not just what data it needs, but what visual assets, animations, and interaction features make it feel like a *real game*, not homework. The pipeline must generate these assets.

5. **Mechanic-general agents, mechanic-specific tools.** Agents consume upstream output generically. Mechanic-specific logic lives in tools and schemas only. Agents never hardcode mechanic behavior.

6. **3-stage pattern with ReAct planners.** Complex phases use: ReAct Planner (self-correcting) → Parallel Workers via Send API → Aggregator. The planner is a ReAct agent (not pure logic) for self-correction benefits.

7. **Hierarchical is a MODE, not a mechanic.** It allows nesting/layering of other mechanics. Deferred for now — not in scope for this redesign.

8. **Zustand store tracks every task.** Multi-scene, multi-task, multi-mechanic game state flows through a single store with per-mechanic progress types, mode transitions, and task progression.

---

## 2. Mechanic Inventory & Classification

### 2.1 The 9 Active Mechanics

| # | Mechanic | Core Interaction | Bloom's Level | Needs Diagram? |
|---|----------|-----------------|---------------|----------------|
| 1 | **drag_drop** | Drag labels onto diagram zones | Remember/Apply | YES — clean diagram + zones |
| 2 | **click_to_identify** | Click correct structure when prompted | Remember/Apply | YES — diagram + hotspot zones |
| 3 | **trace_path** | Follow a flow/pathway through zones | Understand/Apply | YES — pathway diagram + waypoint zones |
| 4 | **sequencing** | Order items in correct sequence | Understand/Apply | YES — per-item illustrations + timeline layout |
| 5 | **sorting_categories** | Categorize items into groups | Analyze | YES — item illustrations + category visuals |
| 6 | **description_matching** | Match functional descriptions to structures | Understand/Analyze | YES — diagram + description cards |
| 7 | **memory_match** | Flip cards to find matching pairs | Remember | YES — image-based cards + themed design |
| 8 | **branching_scenario** | Navigate decision tree with consequences | Evaluate | YES — scene backgrounds + character art |
| 9 | **compare_contrast** | Categorize zones across two diagrams | Analyze | YES — TWO matched diagrams + zones |

**Critical change from previous design:** No mechanic is "config-only". Every mechanic deserves and needs visual assets to feel like a game. Sequencing without illustrations is homework. Memory match without themed cards is a quiz. Sorting without item images is a spreadsheet.

### 2.2 Deferred

- **hierarchical**: Mode/modifier that nests other mechanics with progressive zone reveal. Not a standalone mechanic. Will be implemented after core 9 are solid.
- **timed_challenge**: Wrapper mode that adds a countdown timer to any mechanic. Already implemented as `TimedChallengeWrapper`.

---

## 3. Per-Mechanic Rich Asset Requirements

### 3.1 drag_drop — Diagram Labeling

**What it is:** Drag text labels from a tray onto correct zones on a clean diagram image.

**What makes it feel like a REAL game (vs. basic):**
- Leader lines connecting placed labels to zone boundaries (SVG paths with animated draw-on)
- Progressive hint system (3 levels: category hint → proximity cue → first-letter hint, costing score)
- Zoom/pan on the diagram canvas for detail-dense images
- Contextual info panels on correct placement (structure name, function, fun fact)
- Animated snap feedback (spring physics on correct, shake+bounce-back on incorrect)
- Star rating at completion (3 stars for 90%+ no hints, 2 for 70%+, 1 for completion)
- Combo/streak multiplier for consecutive correct placements
- Post-game review mode (explore all zones with educational content)

**Minimum Viable Assets:**

| Asset | Source | Count |
|-------|--------|-------|
| Clean diagram image (no labels) | Image search + label removal OR AI generation | 1 per scene |
| Zone overlays (circle/polygon/rect) | Zone detection (Gemini/SAM3) | N zones |
| Labels with correctZoneId | LLM from domain knowledge | N correct + M distractors |
| Per-zone hint text (multi-level) | LLM generation | 2-3 hints per zone |
| Per-zone educational content | LLM from domain knowledge | 1 summary + 1 detail per zone |
| Leader line anchor points | Computed from zone geometry | N anchors |
| Scoring config | LLM/template | points, max_score, combo_enabled, star_thresholds |
| Per-zone feedback messages | LLM generation | on_correct + on_incorrect per zone |

**Frontend component status:** Functional but missing leader lines, progressive hints, zoom, info panels, snap animations, star ratings, combo streaks, review mode. See Section 9 for enhancement plan.

---

### 3.2 click_to_identify — Structure Identification

**What it is:** System prompts with a functional question, student clicks the correct zone.

**What makes it feel like a REAL game:**
- Explore-then-test mode: free exploration phase before scored identification
- Magnification lens on hover for detail-dense diagrams
- Information popup on correct identification (name, function, clinical significance)
- Progressive difficulty: major structures first, then sub-structures
- Hint escalation: first attempt = no hint, second = region highlight narrows, third = direct pointer
- Spaced retrieval: correctly identified structures reappear later at higher difficulty

**Minimum Viable Assets:**

| Asset | Source | Count |
|-------|--------|-------|
| Clean diagram image | Same as drag_drop | 1 per scene |
| Zone overlays | Zone detection | N zones |
| Identification prompts (FUNCTIONAL, not naming) | LLM generation | 1 per zone, ordered by difficulty |
| Per-zone educational content | LLM from DK | summary + detail per zone |
| Zone highlight states (hover, selected, correct, incorrect) | CSS/SVG | 4 states per zone |
| Selection mode config | Template | 'sequential' or 'any_order' |
| Difficulty ordering | LLM/computed | per-prompt difficulty score |

**Key asset gap:** Prompts must be FUNCTIONAL ("Click on the structure that pumps blood to the lungs") not NAMING ("Click on the right ventricle"). This requires the LLM to understand structure functions from domain knowledge.

---

### 3.3 trace_path — Flow/Pathway Tracing

**What it is:** Student traces a path through a diagram by clicking waypoints in the correct order.

**What makes it feel like a REAL game:**
- Animated particles flowing along completed path segments (blood cells, electrons, water molecules)
- Directional arrows on path segments showing flow direction
- Step-by-step highlighting: completed segments glow, current target pulses, upcoming segments dim
- Checkpoint information: at each waypoint, tooltip explains what happens at this stage
- Gate/valve animations at key transition points (heart valves opening, synaptic gap crossing)
- Color transitions along path encoding state changes (blue→red for oxygenation)
- Particle perspective narrative: "You are a red blood cell. Where do you go next?"
- Replay with speed control after completion

**Minimum Viable Assets:**

| Asset | Source | Count |
|-------|--------|-------|
| Pathway diagram image (showing connections between structures) | Image search with pathway-specific hints | 1 per scene |
| Waypoint zones on the diagram | Zone detection | N waypoints |
| SVG path definitions connecting waypoints | LLM + zone positions → computed paths | P paths |
| Ordered waypoint sequences per path | LLM from domain knowledge | per path |
| Per-waypoint checkpoint text | LLM generation | 1 explanation per waypoint |
| Directional arrow markers | SVG template | reusable |
| Particle sprite (themed: blood cell, electron, etc.) | SVG/CSS template per theme | 1 per path theme |
| Path color scheme (encoding state changes) | LLM/template | start_color → end_color per path |
| Gate/valve animation data (optional) | LLM identifies transition points | 0-3 per path |

**Key asset gap:** The image MUST show visual pathways/connections between structures. A static organ diagram with no visible routes between chambers is insufficient. Search queries must emphasize "blood flow diagram", "circuit diagram", "water cycle diagram".

---

### 3.4 sequencing — Process Ordering

**What it is:** Order items in the correct sequence (temporal, causal, or procedural).

**What makes it feel like a REAL game (not a sortable text list):**
- **Per-item illustration cards** — the single biggest differentiator. Each step gets its own image showing the state at that stage.
- Timeline/circular/flowchart layout with connecting arrows (not a vertical list)
- Connecting arrows that progressively illuminate as the sequence is built
- Insert-between mechanic (Timeline board game style): items added one at a time into growing sequence
- Progressive reveal: don't show all items at once; reveal in batches
- Snap-to-slot with physics feel (momentum, spring landing)
- Per-step feedback with explanation on correct placement
- Completion animation: full animated playthrough of the complete sequence
- Narrative framing: "You are a cell biologist verifying the division process"

**Minimum Viable Assets:**

| Asset | Source | Count |
|-------|--------|-------|
| Per-item illustration | AI image generation per step | N items (5-8 typical) |
| Background scene | Image search/generation (thematic: lab, microscope, etc.) | 1 per scene |
| Item text + description | LLM generation | per item |
| Correct order | LLM from domain knowledge | ordered ID list |
| Per-item feedback text | LLM generation | explanation per step |
| Slot/track layout config | Template | 'horizontal_timeline' / 'circular' / 'flowchart' |
| Connecting arrow SVGs | Template | reusable |
| Completion sequence animation data | Ordered item IDs + transition descriptions | 1 per game |

**Key asset gap:** Per-item illustrations are currently NOT generated. The pipeline treats sequencing as text-only. Must add image generation per sequence item (or image search per item).

---

### 3.5 sorting_categories — Classification

**What it is:** Categorize items into groups (buckets, Venn diagram regions).

**What makes it feel like a REAL game:**
- **Per-item illustrations** — items should have images, not just text labels
- **Themed category containers** — each category gets an icon, color scheme, and optional background texture
- **Venn diagram mode** for overlapping categories (items can belong to 2+ categories)
- Iterative correction loop (BrainPOP Sortify model): incorrect items bounce back for re-sorting
- Explanation reveal on submission: each item shows WHY it belongs in its category
- Post-game taxonomy/relationship visualization showing the full classification hierarchy
- Multi-level sorting: first sort into broad categories, then sub-sort within each
- Background scene contextualizing the activity (nature scene for biology, lab for chemistry)

**Minimum Viable Assets:**

| Asset | Source | Count |
|-------|--------|-------|
| Per-item illustration | AI image generation or search per item | N items (8-15 typical) |
| Background scene | Image search/generation (thematic) | 1 per scene |
| Category header icon/illustration | AI generation | 1 per category (2-5) |
| Category color theme | Template palette | per category |
| Category description text | LLM generation | per category |
| Items with text + correctCategoryId | LLM generation | N items |
| Per-item explanation | LLM generation | why it belongs in its category |
| Sorting mode config | Template | 'buckets' / 'venn_2' / 'venn_3' |
| Relationship/taxonomy diagram (post-game) | LLM + computed | 1 per game |

**Key asset gap:** Item illustrations and category visuals are NOT generated. Sorting is treated as text-only cards into plain boxes. Must add per-item image generation and themed category containers.

---

### 3.6 description_matching — Function-to-Structure Matching

**What it is:** Match functional descriptions to structures on a diagram.

**What makes it feel like a REAL game:**
- Three interaction modes: drag-description-to-zone, click-zone-then-click-description, multiple-choice-per-zone
- Connecting lines drawn between matched descriptions and zones (SVG animated)
- Zone highlights on proximity during drag
- Defer-evaluation: arrange ALL matches before checking (reduces anxiety)
- Partial credit with per-match specific feedback
- Visual connection persistence: matched lines stay visible, building a web of relationships
- Progressive difficulty: major structures first, then similar/nuanced structures

**Minimum Viable Assets:**

| Asset | Source | Count |
|-------|--------|-------|
| Clean diagram image | Same as drag_drop | 1 per scene |
| Zone overlays | Zone detection | N zones |
| Functional description per zone | LLM generation (NOT appearance-based) | N descriptions |
| Per-zone educational explanation | LLM from DK | per zone |
| Matching mode config | Template | 'drag_to_zone' / 'click_match' / 'multiple_choice' |
| Distractor descriptions (for MC mode) | LLM generation | 3 per zone in MC mode |
| Zone highlight states | CSS/SVG | hover, matched-correct, matched-incorrect |

**Key asset gap:** No agent generates per-label functional descriptions. `label_descriptions` context is never populated. Must add description generation to scene architect or interaction designer tools.

---

### 3.7 memory_match — Card Matching

**What it is:** Flip cards in a grid to find matching pairs (term↔definition, image↔label, concept↔example).

**What makes it feel like a REAL game:**
- **Image-based cards** — cards can have illustrations, diagram closeups, chemical structure images (not just text)
- Themed card back design matching the educational subject
- 3D CSS card flip animation with perspective
- Explanation-on-match: when a pair is found, show a brief educational popup explaining the relationship
- Category color-coding: card borders subtly coded by topic area
- Multiple game variations: classic concentration, column matching, timed scatter (Quizlet Match style)
- Progressive content reveal: start with easy pairs, unlock harder pairs
- Streak multiplier for consecutive correct matches
- Grid size difficulty scaling: 2x2 easy → 4x3 medium → 6x4 hard
- Spaced repetition: missed pairs reappear more frequently

**Minimum Viable Assets:**

| Asset | Source | Count |
|-------|--------|-------|
| Card back design (themed) | AI generation or template | 1 per game |
| Per-pair front content (text or image) | LLM + optional image generation | N pairs |
| Per-pair back content (text or image) | LLM + optional image generation | N pairs |
| Per-pair explanation text | LLM generation | per pair |
| Category color scheme (optional) | Template | per category |
| Grid size config | Template/LLM | rows × cols |
| Flip duration config | Template | milliseconds |
| Background theme | Template or AI generation | 1 per game |
| Card border/frame style | CSS template | per difficulty tier |

**Key asset gap:** No agent generates term-definition pairs OR image-based card content. `generate_mechanic_content` has NO handler for memory_match. Must add pair generation (with optional image generation per card face).

---

### 3.8 branching_scenario — Decision Tree Navigation

**What it is:** Navigate a decision tree with choices at each node, consequences for each decision, and multiple possible endings.

**What makes it feel like a REAL game:**
- **Scene background images per location** (exam room, lab, field, etc.) — the visual novel model
- **Character sprites with expression variants** (patient: neutral/pain/relief; mentor: approving/concerned)
- Consequence visualization: vitals monitor changing, environment state updates
- Decision tree minimap with fog-of-war (progressive reveal during play, full reveal at debrief)
- Foldback narrative structure: branches diverge but converge at critical learning points
- Inventory/evidence accumulation: collected test results, observations become usable tools
- Real-time state displays (vital signs, patient chart) that change based on decisions
- Post-game debrief: optimal path vs. taken path comparison with explanations at each divergence
- Breadcrumb trail showing decisions made

**Minimum Viable Assets:**

| Asset | Source | Count |
|-------|--------|-------|
| Scene background per unique location | AI image generation | 3-6 per scenario |
| Character sprite (main subject) with expression variants | AI image generation | 1 character × 4-6 expressions |
| Optional mentor/guide character | AI image generation | 1 character × 2-3 expressions |
| Decision nodes with question + options | LLM generation | 5-10 nodes |
| Per-option consequence text | LLM generation | per option |
| Ending illustrations (good/neutral/bad) | AI image generation | 2-4 endings |
| State display data (vitals, inventory, evidence) | LLM generation | per-node state changes |
| Decision tree structure | LLM generation | node graph with edges |
| Post-game debrief content | LLM generation | per-divergence explanation |

**Key asset gap:** No agent generates decision tree structures, scene images, or character art. `generate_mechanic_content` has NO handler for branching_scenario. This is the most asset-intensive mechanic. Must add: decision tree generation tool, scene image generation workflow, character sprite generation workflow.

---

### 3.9 compare_contrast — Dual-Diagram Comparison

**What it is:** Compare two diagrams/subjects by categorizing zones as similar, different, unique-to-A, or unique-to-B.

**What makes it feel like a REAL game:**
- **Image comparison slider** (drag divider between two overlaid images) for spatial exploration
- Toggle/overlay mode with transparency slider (composite both images, adjust opacity)
- Side-by-side mode with zone categorization (current implementation)
- Venn diagram mode as alternative view (drag zone labels into overlapping regions)
- Multi-phase progression: Explore (slider) → Categorize (zones) → Assess (quiz)
- Semantic zone pairing: matching lines between corresponding zones across diagrams
- Zoom capability for detail-dense diagrams
- Tooltips explaining WHY a zone is similar/different

**Minimum Viable Assets:**

| Asset | Source | Count |
|-------|--------|-------|
| Diagram A image | Image search/generation for subject A | 1 |
| Diagram B image (matched style/scale!) | Image search/generation for subject B | 1 |
| Zones on diagram A | Zone detection on image A | N_a zones |
| Zones on diagram B | Zone detection on image B | N_b zones |
| Zone pairings (A_zone ↔ B_zone) | LLM/computed from labels | paired zones |
| Expected categories per zone | LLM analysis | similar/different/unique_a/unique_b |
| Per-zone explanation | LLM generation | why this categorization |
| View modes config | Template | slider/toggle/side_by_side/venn |
| Comparison instructions | LLM generation | per phase |

**Key asset gap:** Architecture supports only 1 image per scene. Must add dual-image generation + dual-zone detection. Image style matching is critical — both diagrams must use consistent visual style for meaningful comparison.

---

## 4. Potential New Mechanics

Research identified 10 additional mechanics. Top 5 candidates for our Interactive Diagram Game template (must relate to visual educational content):

### 4.1 PREDICT_OBSERVE_EXPLAIN (Hypothesis Testing)
**What:** Student predicts what happens when a parameter changes, system reveals the outcome, student explains.
**Bloom's:** Analyze/Evaluate (4-5) — highest-order mechanic available.
**Assets:** Base diagram + parameterized before/after states + prediction UI + reveal animation.
**Feasibility:** Medium-high. Reuses diagram infrastructure. Needs parameter→visual-state mapping.
**Example:** "What happens to this plant cell in a hypertonic solution?" → Plasmolysis animation.
**Verdict:** HIGH PRIORITY — fills Evaluate gap, aligns perfectly with science education.

### 4.2 SPOT_THE_ERROR (Error Detection)
**What:** Diagram contains deliberate errors (mislabeled parts, wrong connections). Student finds and corrects them.
**Bloom's:** Evaluate (5) — requires correct mental model to detect incorrectness.
**Assets:** Same diagram infrastructure. Pipeline introduces N errors (swap labels, break paths, add wrong structures).
**Feasibility:** High. Reuses click_to_identify interaction with inverted logic.
**Example:** "This heart diagram has 3 errors. Find them." (pulmonary artery mislabeled, flow arrows reversed, valve missing).
**Verdict:** HIGH PRIORITY — inverts learning direction, proven more effective than correct-diagram study.

### 4.3 CLOZE_FILL (Fill-in-the-Blank on Diagram)
**What:** Diagram labels are blanked out; student types the correct terms (recall, not recognition).
**Bloom's:** Remember/Apply (1-3) — fills the recall gap (all current mechanics are recognition-based).
**Assets:** Same clean diagram. Label text removed (already have image_label_remover). Text input zones.
**Feasibility:** High. Render label zones as text inputs instead of drop zones. Fuzzy matching for validation.
**Example:** Neuron diagram with 6 blank labels → student types "axon", "dendrite", "myelin sheath", etc.
**Verdict:** MEDIUM-HIGH PRIORITY — fills recall gap, straightforward to implement.

### 4.4 PROCESS_BUILDER (System Assembly)
**What:** Given components, student assembles a system by placing and connecting them (build the diagram, not label it).
**Bloom's:** Create/Apply (3, 6) — the ONLY mechanic reaching Bloom's "Create" level.
**Assets:** Component sprites/icons (AI-generated SVGs), blank canvas, connection drawing (SVG arrows).
**Feasibility:** Medium. More complex than drag_drop but achievable with dnd-kit + SVG canvas.
**Example:** "Build a food web: place organisms and draw energy flow arrows between them."
**Verdict:** MEDIUM PRIORITY — unique and valuable but higher implementation effort. Consider for v2.

### 4.5 CAUSE_EFFECT_CHAIN (Causal Reasoning)
**What:** Arrange events into cause-and-effect chains, where each triggers the next. Supports branching/converging chains.
**Bloom's:** Analyze (4) — deeper than sequencing (causal, not just temporal).
**Assets:** Event cards (text + optional illustrations), arrow connectors, canvas.
**Feasibility:** Medium-high. Node-and-arrow graph builder, similar to branching but student-constructed.
**Example:** "Build the cause-effect chain for Type 2 diabetes: diet → resistance → overproduction → exhaustion → dysregulation."
**Verdict:** MEDIUM PRIORITY — valuable for science education. Could be a sequencing variant with branching.

### 4.6 Summary: Bloom's Coverage

| Bloom's Level | Current Mechanics | New Mechanics |
|---------------|------------------|---------------|
| Remember (1) | drag_drop, click_to_identify, memory_match | **cloze_fill** |
| Understand (2) | trace_path, sequencing, description_matching | |
| Apply (3) | drag_drop, sorting_categories | **process_builder** |
| Analyze (4) | compare_contrast, sorting_categories | **cause_effect_chain** |
| Evaluate (5) | branching_scenario | **predict_observe_explain**, **spot_the_error** |
| Create (6) | *(none)* | **process_builder** |

---

## 5. Current Pipeline Status Matrix

### 5.1 Status per Agent per Mechanic

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

### 5.2 What "BROKEN" Means per Agent

- **Game Designer BROKEN**: Produces `type` field only; no mechanic-specific config data (pairs, nodes, categories, descriptions)
- **Scene Architect BROKEN**: `generate_mechanic_content` has no handler for the mechanic type
- **Interaction Designer BROKEN**: `enrich_mechanic_content` has no handler; no scoring/feedback generation
- **Asset Generator BROKEN**: Generates 1 diagram image only; doesn't generate per-item images, card images, scene backgrounds, character sprites, or dual images
- **Blueprint Assembler BROKEN**: No upstream data to assemble; maps exist but receive null/empty configs

### 5.3 Frontend Status

All 9 components exist and work standalone. MechanicRouter dispatches correctly. Zustand store has all progress types. Mode transitions work. Task progression works.

**BUT**: Every component is at "basic functional" level. None have the rich features described in Section 3. See Section 9 for enhancement plan.

---

## 6. Root Cause Analysis

### 6.1 The Core Problem

The V3 pipeline was designed, tested, and optimized for `drag_drop` labeling only. Every agent's prompt, every tool's implementation, and every schema's validation was written with a "find diagram → detect zones → place labels" mental model.

### 6.2 Eight Root Causes

| # | Root Cause | Impact | Fix Level |
|---|-----------|--------|-----------|
| RC-1 | Agent prompts don't mandate mechanic-specific tool calls | ALL non-drag_drop mechanics get empty configs | Prompt + architecture |
| RC-2 | No per-item image generation capability | sequencing, sorting, memory_match lack visual richness | New asset workflows |
| RC-3 | No scene/character image generation for branching | branching_scenario has no visual assets | New asset workflows |
| RC-4 | No dual-image generation for compare_contrast | compare_contrast can't produce 2 matched images | Architecture change |
| RC-5 | No functional description generation | click_to_identify, description_matching get generic prompts | New tool handlers |
| RC-6 | No pair/tree/category generation | memory_match, branching, sorting get no content | New tool handlers |
| RC-7 | Single ReAct agent handles all scenes sequentially | Context overload, no parallelism, fragile | Send API architecture |
| RC-8 | Asset generator is 100% diagram-centric | Only knows: search image → detect zones. No concept of different asset types per mechanic | 3-stage asset pipeline |

### 6.3 The Asset Generation Gap (Most Critical)

The current asset generator knows ONE workflow:
```
search_diagram_image → generate_diagram_image → detect_zones → submit_assets
```

But different mechanics need fundamentally different asset workflows:

| Mechanic | Asset Workflow Needed |
|----------|---------------------|
| drag_drop / click_to_identify / description_matching | diagram image → zone detection (CURRENT) |
| trace_path | pathway diagram → zone detection + SVG path generation |
| sequencing | per-item illustration generation (N images) + background scene |
| sorting_categories | per-item illustration generation + category icon generation + background |
| memory_match | per-card image generation (text cards need themed design; image cards need illustrations) |
| branching_scenario | per-node scene background + character sprites with expressions + ending illustrations |
| compare_contrast | 2 matched diagrams → zone detection on BOTH + zone pairing |

This requires a complete redesign of the asset stage from a single ReAct agent into a **planner → orchestrator → aggregator** pipeline with mechanic-specific asset worker sub-workflows.

---

## 7. Architecture Redesign: Quality Gate + Send API

### 7.1 Key Architectural Patterns (from V4 Research)

**Quality Gate Pattern:** Replace monolithic ReAct agents with graph-enforced sequences. Each node is a separate LangGraph node — the LLM cannot skip validation or call submit prematurely.

**Send API (Map-Reduce):** `Send("node_name", {"scene": scene_data})` for dynamic fan-out. Parallel per-scene execution with automatic result collection. Pregel runtime manages supersteps.

**Hierarchical Meta-Graph:** Each phase is a compiled sub-graph with isolated state (10-20 fields, not 160+). Context isolation prevents pollution.

**ReAct Planner (User Requirement):** The planner in each phase is a ReAct agent (not pure logic) for self-correction. It can reason about what scenes need, adjust its plan, and handle edge cases.

**Fresh LLM Calls on Retry:** Each retry is a fresh call with summarized feedback, not accumulated chat history. Prevents "Yes-Man Loop".

**Contract-Based Communication:** Pydantic schemas at every phase boundary. Pure code validation at transitions.

### 7.2 Proposed Graph Architecture

```
PHASE 0: Context Gathering (UNCHANGED)
  input_enhancer → domain_knowledge_retriever → router

PHASE 1: Game Design (Quality Gate Sub-Graph)
  ┌─────────────────────────────────────────────┐
  │ gather_context (pure code: extract DK, labels)│
  │ → game_designer (ReAct: creative design)      │
  │ → design_validator (pure code: Pydantic)      │
  │ → [if valid → submit | if invalid → retry]    │
  └─────────────────────────────────────────────┘
  Output contract: GameDesignV3 (full, not Slim)

PHASE 2: Scene Architecture (Quality Gate + Send API)
  ┌─────────────────────────────────────────────┐
  │ scene_planner (ReAct: plan per-scene work)    │
  │ → Send("scene_worker", {scene}) per scene     │
  │   ┌─────────┐ ┌─────────┐ ┌─────────┐      │
  │   │ Scene 1 │ │ Scene 2 │ │ Scene 3 │      │
  │   │ worker  │ │ worker  │ │ worker  │      │
  │   └────┬────┘ └────┬────┘ └────┬────┘      │
  │ → scene_aggregator (pure code: merge+validate)│
  │ → scene_validator (pure code: Pydantic)       │
  │ → [if valid → submit | if invalid → retry]    │
  └─────────────────────────────────────────────┘
  Output contract: SceneSpecV3[]

PHASE 3: Interaction Design (Quality Gate + Send API)
  ┌─────────────────────────────────────────────┐
  │ interaction_planner (ReAct: plan per-scene)   │
  │ → Send("interaction_worker", {scene}) /scene  │
  │ → interaction_aggregator (merge+validate)     │
  │   Also generates: mechanic_transitions[]      │
  │   Also generates: tasks[] per scene           │
  │ → interaction_validator (pure code)           │
  │ → [if valid → submit | if invalid → retry]    │
  └─────────────────────────────────────────────┘
  Output contract: InteractionSpecV3[]

PHASE 4: Asset Generation (3-Stage + Send API)
  ┌─────────────────────────────────────────────┐
  │ asset_planner (ReAct: mechanic-aware planning)│
  │   Determines per-scene asset requirements:    │
  │   - Diagram scenes: image + zones             │
  │   - Per-item scenes: N item illustrations     │
  │   - Branching scenes: backgrounds + characters│
  │   - Compare scenes: 2 images + 2 zone sets    │
  │ → Send("asset_worker", {scene_task}) /scene   │
  │   ┌───────────┐ ┌───────────┐ ┌───────────┐ │
  │   │ Scene 1   │ │ Scene 2   │ │ Scene 3   │ │
  │   │ diagram   │ │ per-item  │ │ branching │ │
  │   │ workflow  │ │ workflow  │ │ workflow  │ │
  │   └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ │
  │ → asset_aggregator (merge + validate)         │
  └─────────────────────────────────────────────┘
  Output contract: GeneratedAssetsV3

PHASE 5: Blueprint Assembly (Quality Gate Sub-Graph)
  ┌─────────────────────────────────────────────┐
  │ blueprint_assembler (ReAct: assemble all)     │
  │ → blueprint_validator (pure code)             │
  │ → [if valid → submit | if invalid → retry]    │
  └─────────────────────────────────────────────┘
  Output contract: InteractiveDiagramBlueprint
```

### 7.3 Asset Worker Sub-Workflows

The asset worker dispatches to different sub-workflows based on what the scene's mechanics need:

```
DIAGRAM WORKFLOW (drag_drop, click_to_identify, trace_path, description_matching):
  search_diagram_image → clean/generate → detect_zones → validate_zones

PER-ITEM ILLUSTRATION WORKFLOW (sequencing, sorting_categories):
  For each item: generate_item_illustration(item_text, subject_context)
  Generate background_scene(theme)
  For sorting: generate_category_icons(categories)

CARD CONTENT WORKFLOW (memory_match):
  For each pair: generate_card_content(front, back, front_type, back_type)
  If image cards: generate_card_illustration per card
  Generate themed_card_back(subject)

BRANCHING SCENE WORKFLOW (branching_scenario):
  For each unique location: generate_scene_background(location_description)
  For each character: generate_character_sprite(character, expressions[])
  For ending nodes: generate_ending_illustration(ending_type)

DUAL DIAGRAM WORKFLOW (compare_contrast):
  search_diagram_image(subject_A) → clean → detect_zones_A
  search_diagram_image(subject_B) → clean → detect_zones_B
  compute_zone_pairings(zones_A, zones_B)
```

### 7.4 State Isolation

Each phase sub-graph has its own isolated state type:

```python
# Phase 1
class DesignerState(TypedDict):
    question: str
    subject: str
    domain_knowledge: Dict
    canonical_labels: List[str]
    game_design_v3: Optional[Dict]      # OUTPUT
    design_feedback: Optional[str]       # For retry

# Phase 2
class SceneArchState(TypedDict):
    game_design_v3: Dict                 # INPUT
    domain_knowledge: Dict
    scene_specs_v3: Optional[List[Dict]] # OUTPUT
    scene_feedback: Optional[str]

# Phase 4
class AssetState(TypedDict):
    scene_specs_v3: List[Dict]           # INPUT
    game_design_v3: Dict
    canonical_labels: List[str]
    generated_assets_v3: Optional[Dict]  # OUTPUT
    asset_feedback: Optional[str]
```

This reduces each sub-graph from 160+ fields to 5-10 fields, eliminating context pollution.

---

## 8. Per-Phase Redesign Details

### 8.1 Phase 1: Game Designer

**Architecture:** Quality Gate sub-graph (no Send API — single holistic output).

**Changes needed:**
1. `check_capabilities` MANDATORY before choosing mechanics — only pick from `ready_types`
2. Must produce per-mechanic config data (not just `type` field):
   - trace_path: waypoint zone_labels in order
   - sequencing: item texts + correct_order
   - sorting_categories: categories + items with assignments
   - description_matching: descriptions per label
   - click_to_identify: identification prompt themes
   - memory_match: pair definitions (term↔definition themes)
   - branching_scenario: scenario outline (node summaries, decision themes)
   - compare_contrast: two subject descriptions + expected comparison dimensions
3. Scene consolidation: don't create 2 scenes unless they need different visual contexts
4. Per-scene `mechanics[]` with ordering (which mechanic runs first, second, etc.)

### 8.2 Phase 2: Scene Architecture

**Architecture:** ReAct Planner → Send API Workers → Aggregator → Validator.

**Planner (ReAct):**
- Reads game_design_v3 and domain knowledge
- Plans per-scene work items: what zones to create, what mechanic configs to generate
- Self-corrects if scene breakdown doesn't match game design
- Tools: `analyze_scene_requirements`, `plan_scene_tasks`, `submit_scene_plan`

**Workers (per scene, parallel via Send API):**
- Each worker handles ONE scene
- For every mechanic in the scene: calls `generate_mechanic_content` to populate configs
- Generates zone layouts, image requirements, mechanic-specific data
- Tools: `get_zone_layout_guidance`, `get_mechanic_config_schema`, `generate_mechanic_content`, `validate_scene_spec`, `submit_scene_spec`

**Aggregator (pure code):**
- Merges all scene specs into `scene_specs_v3[]`
- Validates cross-scene consistency (no duplicate zones, labels unique, scene numbers correct)

**Missing tool handlers to add:**
- `generate_mechanic_content` for `memory_match` → generate term-definition pairs from DK
- `generate_mechanic_content` for `branching_scenario` → generate decision tree structure from topic
- `generate_mechanic_content` for `compare_contrast` → generate expected categories + dual descriptions
- Improve `description_matching` handler to generate functional descriptions even without `label_descriptions` context

### 8.3 Phase 3: Interaction Design

**Architecture:** ReAct Planner → Send API Workers → Aggregator → Validator.

**Planner (ReAct):**
- Reads scene_specs_v3 and game_design_v3
- Plans per-scene scoring strategies, feedback themes, mode transitions
- Tools: `analyze_interaction_needs`, `plan_interaction_design`, `submit_interaction_plan`

**Workers (per scene, parallel via Send API):**
- Each worker handles ONE scene's interaction design
- For every mechanic: calls `enrich_mechanic_content` for pedagogically grounded scoring + feedback
- Generates misconception triggers, hint escalation data
- For multi-mechanic scenes: generates `mechanic_transitions[]` (from_mechanic → to_mechanic with trigger)
- Generates `tasks[]` per scene (task_id, mechanic_type, zone_ids, label_ids, scoring_weight)
- Tools: `get_scoring_templates`, `enrich_mechanic_content`, `generate_misconception_feedback`, `generate_mechanic_transitions`, `validate_interactions`, `submit_interaction_spec`

**Aggregator (pure code):**
- Merges all interaction specs into `interaction_specs_v3[]`
- Validates: every mechanic has scoring + feedback, transitions are valid, tasks cover all mechanics

**Missing tool handlers to add:**
- `enrich_mechanic_content` for `memory_match`, `branching_scenario`, `compare_contrast`
- NEW: `generate_mechanic_transitions` tool — creates transition objects for multi-mechanic scenes
- NEW: `generate_tasks` tool — creates task definitions mapping mechanics to zone/label subsets

### 8.4 Phase 4: Asset Generation

**Architecture:** ReAct Planner → Send API Workers (mechanic-aware) → Aggregator.

**This is the most complex phase** because different mechanics need fundamentally different asset workflows.

**Planner (ReAct):**
- Reads scene_specs_v3, game_design_v3, interaction_specs_v3
- For each scene, determines required asset workflow based on mechanic types:
  - Diagram-zone workflow (drag_drop, click_to_identify, trace_path, description_matching)
  - Per-item illustration workflow (sequencing, sorting_categories)
  - Card content workflow (memory_match)
  - Branching scene workflow (branching_scenario)
  - Dual-diagram workflow (compare_contrast)
- Creates `asset_tasks[]` with workflow type, image hints, and expected outputs per scene
- Tools: `analyze_asset_requirements`, `plan_asset_tasks`, `submit_asset_plan`

**Workers (per scene, parallel via Send API):**
Each worker receives its scene's asset_task and dispatches to the appropriate workflow:

- **Diagram workflow**: `search_diagram_image` → `generate_diagram_image` (if needed) → `detect_zones` → `submit_scene_assets`
- **Per-item workflow**: For each item → `generate_item_illustration(item_text, context)` → `generate_background_scene(theme)` → `submit_scene_assets`
- **Card workflow**: For each pair → `generate_card_content(pair)` → `generate_card_back(theme)` → `submit_scene_assets`
- **Branching workflow**: For each location → `generate_scene_background(desc)` → For each character → `generate_character_sprite(char, expressions)` → `submit_scene_assets`
- **Dual-diagram workflow**: `search_diagram_image(A)` → `search_diagram_image(B)` → `detect_zones(A)` → `detect_zones(B)` → `compute_zone_pairings` → `submit_scene_assets`

**Aggregator (pure code):**
- Merges all per-scene assets into `generated_assets_v3`
- Validates: every scene has its required assets, all expected items/cards/nodes have images

**New tools needed:**
- `generate_item_illustration` — generates an image for a single sequence/sorting item
- `generate_card_content` — generates themed card face content (text styling or image)
- `generate_scene_background` — generates a scene/location background image
- `generate_character_sprite` — generates character art with expression variants
- `compute_zone_pairings` — matches corresponding zones across two diagrams
- `generate_card_back` — generates a themed card back design

### 8.5 Phase 5: Blueprint Assembly

**Architecture:** Quality Gate sub-graph (single agent, validates output).

**Key responsibilities:**
1. Assemble complete `InteractiveDiagramBlueprint` from all upstream data
2. Populate ALL per-mechanic config fields (sequenceConfig, sortingConfig, memoryMatchConfig, branchingConfig, compareConfig, paths, identificationPrompts, descriptionMatchingConfig)
3. Generate `mechanic_transitions[]` for multi-mechanic scenes (from interaction specs)
4. Generate `tasks[]` per scene (from interaction specs)
5. Set `mechanic_type` on each game_sequence scene
6. Handle dual-image assembly for compare_contrast (diagramA, diagramB in compareConfig)
7. Forward scoring/feedback to `mechanics[]` array (currently drops them)
8. Proxy all image URLs through `/api/assets/`

---

## 9. Frontend Component Enhancement Plan

### 9.1 Cross-Mechanic Enhancements (apply to all)

| Enhancement | Priority | Effort |
|-------------|----------|--------|
| Star rating at completion (1-3 stars based on accuracy/hints/time) | P0 | Low |
| Combo/streak multiplier display | P1 | Low |
| Post-game review/explore mode | P1 | Medium |
| Sound effects toggle (correct, incorrect, complete) | P2 | Low |
| Confetti/celebration on completion (already exists, ensure wired) | P0 | Low |

### 9.2 Per-Mechanic Enhancements

**drag_drop (DiagramCanvas, LabelTray, DropZone):**
| Enhancement | Priority | Impact |
|-------------|----------|--------|
| Leader lines (SVG from label to zone) | P0 | High |
| Progressive hint system (3-level with score penalty) | P0 | High |
| Animated snap feedback (spring physics) | P0 | High |
| Zoom/pan on diagram canvas | P1 | High |
| Contextual info panels on correct placement | P1 | Medium-High |
| Label tray grouping + color coding by category | P2 | Medium |
| Reverse mode variant (zone highlights, pick label) | P2 | Medium |

**click_to_identify (HotspotManager):**
| Enhancement | Priority | Impact |
|-------------|----------|--------|
| Explore-then-test mode toggle | P1 | High |
| Magnification lens on hover | P1 | High |
| Information popup on correct identification | P0 | Medium-High |
| Hint escalation (3 levels) | P1 | Medium |

**trace_path (PathDrawer):**
| Enhancement | Priority | Impact |
|-------------|----------|--------|
| Animated particles along completed paths | P0 | High |
| Directional arrows on path segments | P0 | High |
| Color transitions encoding state changes | P1 | Medium |
| Checkpoint information tooltips | P0 | Medium-High |
| Gate/valve animations at transition points | P2 | Medium |

**sequencing (SequenceBuilder):**
| Enhancement | Priority | Impact |
|-------------|----------|--------|
| Per-item illustration cards (image + text) | P0 | Critical |
| Timeline/circular/flowchart layout options | P0 | High |
| Connecting arrows that illuminate on correct | P0 | High |
| Insert-between mechanic (Timeline style) | P1 | High |
| Progressive reveal (items one at a time) | P1 | Medium |
| Completion animation (full sequence playthrough) | P1 | Medium |

**sorting_categories (SortingCategories):**
| Enhancement | Priority | Impact |
|-------------|----------|--------|
| Per-item illustration cards | P0 | Critical |
| Themed category containers (icon, color, texture) | P0 | High |
| Venn diagram mode for overlapping categories | P1 | High |
| Iterative correction loop (incorrect bounce back) | P1 | High |
| Explanation reveal on submission | P0 | Medium-High |
| Post-game taxonomy/relationship visualization | P2 | Medium |

**description_matching (DescriptionMatcher):**
| Enhancement | Priority | Impact |
|-------------|----------|--------|
| Connecting lines (SVG from card to zone, animated) | P0 | High |
| Zone highlights on proximity during drag | P0 | Medium |
| Defer-evaluation mode (arrange all, then check) | P1 | Medium |
| Visual connection persistence (lines stay) | P1 | Medium |

**memory_match (MemoryMatch):**
| Enhancement | Priority | Impact |
|-------------|----------|--------|
| Image-based card faces (illustrations, not just text) | P0 | Critical |
| Themed card back design | P0 | High |
| Explanation-on-match educational popup | P0 | High |
| Category color-coding on card borders | P1 | Medium |
| Streak multiplier for consecutive matches | P1 | Medium |
| Grid size difficulty scaling | P1 | Low |

**branching_scenario (BranchingScenario):**
| Enhancement | Priority | Impact |
|-------------|----------|--------|
| Scene background images per location | P0 | Critical |
| Character sprites with expression variants | P0 | Critical |
| Decision tree minimap with fog-of-war | P1 | High |
| State displays (vitals, evidence inventory) | P1 | High |
| Post-game debrief (optimal vs. taken path) | P0 | High |
| Breadcrumb trail | P1 | Medium |

**compare_contrast (CompareContrast):**
| Enhancement | Priority | Impact |
|-------------|----------|--------|
| Image comparison slider mode | P0 | Critical |
| Overlay/toggle mode with transparency | P1 | High |
| Semantic zone pairing lines | P0 | High |
| Zoom capability | P1 | Medium |
| Multi-phase progression (explore → categorize) | P1 | Medium |
| Venn diagram alternative view | P2 | Medium |

---

## 10. Multi-Mechanic Scene Chaining

### 10.1 Current State

**Frontend: 100% ready.** Zustand store has complete multi-mechanic orchestration:
- `MultiModeState` with `currentMode`, `completedModes`, `modeHistory`
- `checkModeTransition()` evaluates 13 trigger types
- `transitionToMode()` resets score, reinitializes per-mechanic progress
- `advanceToNextTask()` progresses through tasks within a scene
- `_sceneToBlueprint()` converts multi-mechanic scene + task into single-mechanic blueprint
- Implicit fallback: creates default task from first mechanic when backend doesn't provide tasks[]

**Backend: 50% there.** Blueprint assembler builds `mechanics[]` with config/scoring/feedback but does NOT generate:
- `mechanic_transitions[]` — transition definitions between mechanics in a scene
- `tasks[]` — task definitions mapping each mechanic to its zone/label subset

### 10.2 What Backend Must Generate

**mechanic_transitions (per multi-mechanic scene):**
```json
[
  {
    "from_mechanic": "drag_drop",
    "to_mechanic": "trace_path",
    "trigger": "all_zones_labeled",
    "trigger_value": null,
    "animation": "fade",
    "message": "Great! Now trace the blood flow path."
  }
]
```

**tasks (per multi-mechanic scene):**
```json
[
  {
    "task_id": "task_1_drag_drop",
    "title": "Label the heart chambers",
    "mechanic_type": "drag_drop",
    "zone_ids": ["zone_left_atrium", "zone_right_atrium", ...],
    "label_ids": ["label_left_atrium", "label_right_atrium", ...],
    "scoring_weight": 0.5
  },
  {
    "task_id": "task_2_trace_path",
    "title": "Trace the blood flow",
    "mechanic_type": "trace_path",
    "zone_ids": ["zone_ra", "zone_rv", "zone_pa", "zone_lungs", ...],
    "label_ids": [],
    "scoring_weight": 0.5
  }
]
```

### 10.3 Generation Responsibility

The **Interaction Designer** phase (Phase 3) generates transitions and tasks because it has full knowledge of:
- Which mechanics are in each scene (from scene_specs)
- Scoring weights per mechanic
- Completion triggers per mechanic type
- Which zones/labels each mechanic uses

The **Blueprint Assembler** (Phase 5) copies these into the final blueprint.

---

## 11. Fix Catalog

### 11.1 Tool Implementation Fixes

| Fix ID | File | Description |
|--------|------|-------------|
| T-1 | scene_architect_tools.py | Add `generate_mechanic_content` handler for `memory_match` — generate term-definition pairs |
| T-2 | scene_architect_tools.py | Add handler for `branching_scenario` — generate decision tree |
| T-3 | scene_architect_tools.py | Add handler for `compare_contrast` — generate dual descriptions + expected categories |
| T-4 | scene_architect_tools.py | Improve `description_matching` — generate functional descriptions via LLM |
| T-5 | interaction_designer_tools.py | Add `enrich_mechanic_content` handlers for memory_match, branching, compare |
| T-6 | interaction_designer_tools.py | NEW: `generate_mechanic_transitions` tool |
| T-7 | interaction_designer_tools.py | NEW: `generate_tasks` tool |
| T-8 | asset_generator_tools.py | NEW: `generate_item_illustration` tool |
| T-9 | asset_generator_tools.py | NEW: `generate_scene_background` tool |
| T-10 | asset_generator_tools.py | NEW: `generate_character_sprite` tool |
| T-11 | asset_generator_tools.py | NEW: `generate_card_content` tool |
| T-12 | asset_generator_tools.py | NEW: `compute_zone_pairings` tool |
| T-13 | asset_generator_tools.py | Support dual-image generation for compare_contrast |
| T-14 | asset_generator_tools.py | `submit_assets` scene count validation |
| T-15 | blueprint_assembler_tools.py | Populate `mechanic_type` in game_sequence scenes |
| T-16 | blueprint_assembler_tools.py | Handle dual-image assembly for compare_contrast |
| T-17 | blueprint_assembler_tools.py | Forward scoring/feedback to mechanics[] (currently drops them) |
| T-18 | blueprint_assembler_tools.py | Generate mechanic_transitions[] from interaction specs |
| T-19 | blueprint_assembler_tools.py | Generate tasks[] from interaction specs |

### 11.2 Architecture Fixes

| Fix ID | File | Description |
|--------|------|-------------|
| A-1 | scene_architect_v3.py | Convert to ReAct Planner + Send API Workers + Aggregator |
| A-2 | interaction_designer_v3.py | Convert to ReAct Planner + Send API Workers + Aggregator |
| A-3 | asset_generator_v3.py | Convert to ReAct Planner + mechanic-aware Send API Workers + Aggregator |
| A-4 | graph.py | Update `create_v3_graph()` with Quality Gate sub-graphs + Send API routing |
| A-5 | state.py | Add isolated sub-graph state types (DesignerState, SceneArchState, etc.) |
| A-6 | instrumentation.py | Add metadata for new planner/worker/aggregator nodes |

### 11.3 Prompt Fixes

| Fix ID | File | Description |
|--------|------|-------------|
| P-1 | game_designer_v3.py | Mandate check_capabilities, require per-mechanic configs |
| P-2 | scene_architect planner | Per-scene planning with mechanic-aware work items |
| P-3 | scene_architect worker | Per-scene execution with mandatory generate_mechanic_content |
| P-4 | interaction_designer planner | Per-scene interaction planning |
| P-5 | interaction_designer worker | Per-scene with mandatory enrich_mechanic_content + transitions |
| P-6 | asset_planner | Mechanic-aware asset planning |
| P-7 | asset_worker | Per-scene with mechanic-specific workflow dispatch |

### 11.4 Validator Fixes

| Fix ID | File | Description |
|--------|------|-------------|
| V-1 | design_validator.py | Add all missing mechanics, increase penalties |
| V-2 | scene_spec_v3.py | Add compare_contrast validation |
| V-3 | interaction_spec_v3.py | Add missing mechanics to MECHANIC_TRIGGER_MAP |

### 11.5 Schema Fixes

| Fix ID | File | Description |
|--------|------|-------------|
| S-1 | game_design_v3.py | Ensure MechanicDesign has all config fields |
| S-2 | scene_spec_v3.py | Mechanic validation covers all 9 types |
| S-3 | blueprint_schemas.py | All 9 mechanic frontend configs |
| S-4 | state.py | Per-scene asset types (item_illustrations, scene_backgrounds, etc.) |

### 11.6 Frontend Enhancement Fixes

| Fix ID | Component | Description |
|--------|-----------|-------------|
| FE-1 | DiagramCanvas | Leader lines, zoom/pan |
| FE-2 | DropZone | Animated snap feedback (spring physics) |
| FE-3 | LabelTray | Category grouping, color coding, remaining count |
| FE-4 | GameControls | Star rating, combo display |
| FE-5 | HotspotManager | Magnification lens, explore mode, info popups |
| FE-6 | PathDrawer | Animated particles, directional arrows, color transitions |
| FE-7 | SequenceBuilder | Illustration cards, timeline layout, illuminating connectors |
| FE-8 | SortingCategories | Item illustrations, themed containers, Venn mode, iterative correction |
| FE-9 | DescriptionMatcher | Connecting lines, proximity highlights, defer-evaluation |
| FE-10 | MemoryMatch | Image cards, themed backs, explanation-on-match |
| FE-11 | BranchingScenario | Scene backgrounds, character sprites, minimap, debrief |
| FE-12 | CompareContrast | Slider mode, overlay mode, zone pairing lines, zoom |
| FE-13 | ResultsPanel | Per-zone review, explore mode, star display |
| FE-14 | ALL | Progressive hints system (multi-level) |
| FE-15 | ALL | Post-game review/explore mode |

---

## 12. Implementation Order

### Phase A: Foundation (Backend Architecture)
*Must be done first — all other work depends on this.*

1. **A-4, A-5**: Update graph.py with Quality Gate sub-graphs + Send API routing + isolated state types
2. **A-1**: Convert scene_architect to planner→workers→aggregator
3. **A-2**: Convert interaction_designer to planner→workers→aggregator
4. **A-3**: Convert asset_generator to planner→workers→aggregator
5. **A-6**: Instrumentation metadata for new nodes

### Phase B: Tool Implementation (Parallel with Phase A)
*Backend tool handlers — no architecture dependency.*

6. **T-1 to T-4**: Missing `generate_mechanic_content` handlers (memory, branching, compare, description)
7. **T-5**: Missing `enrich_mechanic_content` handlers
8. **T-6, T-7**: New transition + task generation tools
9. **V-1 to V-3**: Validator fixes

### Phase C: Asset Pipeline (Depends on Phase A)
*New asset generation capabilities.*

10. **T-8 to T-12**: New asset tools (item illustrations, scene backgrounds, character sprites, card content, zone pairings)
11. **T-13**: Dual-image support for compare_contrast
12. **T-14**: Asset submit validation

### Phase D: Blueprint + Prompts (Depends on Phase B)
*Wire everything together.*

13. **P-1**: Game designer prompt rewrite
14. **P-2 to P-7**: All planner/worker prompts
15. **T-15 to T-19**: Blueprint assembler fixes
16. **S-1 to S-4**: Schema fixes

### Phase E: Frontend Enhancements (Parallel with Phases A-D)
*Can start immediately — no backend dependency.*

17. **FE-4**: Star rating + combo (cross-mechanic, high impact)
18. **FE-7**: SequenceBuilder illustration cards + timeline layout
19. **FE-8**: SortingCategories item illustrations + themed containers
20. **FE-10**: MemoryMatch image cards + themed design
21. **FE-11**: BranchingScenario scene backgrounds + character sprites
22. **FE-12**: CompareContrast slider mode + overlay
23. **FE-1, FE-2**: drag_drop leader lines + snap animations
24. **FE-5, FE-6**: click_to_identify + trace_path enhancements
25. **FE-9, FE-13, FE-14, FE-15**: Remaining component polish

### Phase F: End-to-End Testing
*After all phases complete.*

26. Per-mechanic test runs (see Section 13)
27. Multi-mechanic scene test runs
28. Performance and cost optimization

---

## 13. Verification Plan

### 13.1 Per-Mechanic Test Prompts

| Mechanic | Test Question | Expected Rich Assets |
|----------|--------------|---------------------|
| drag_drop | "Label the main parts of a human heart" | Diagram + zones + labels + leader lines + hints |
| click_to_identify | "Identify the functions of heart chambers" | Diagram + zones + functional prompts + info panels |
| trace_path | "Trace blood flow through the heart from vena cava to aorta" | Pathway diagram + ordered waypoints + animated particles |
| sequencing | "Arrange the stages of mitosis in order" | Per-stage illustrations + timeline layout + connecting arrows |
| sorting_categories | "Sort organisms into vertebrates and invertebrates" | Per-organism illustrations + themed category containers |
| description_matching | "Match each cell organelle to its function" | Diagram + zones + functional descriptions + connecting lines |
| memory_match | "Match element symbols to their names" | Themed card faces + explanations + image cards |
| branching_scenario | "Navigate a patient diagnosis scenario" | Scene backgrounds + character sprites + decision tree |
| compare_contrast | "Compare plant and animal cells" | 2 matched diagrams + zones on both + slider mode |

### 13.2 Multi-Mechanic Test

```
"Create a game about the human heart:
  First: Label the 4 chambers and major vessels (drag_drop)
  Then: Trace the path of blood flow (trace_path)
  Finally: Match each chamber to its function (description_matching)"
```

Expected: 1 scene, 3 mechanics chained, transitions between them, shared diagram image.

### 13.3 Verification Checklist per Run

1. All pipeline stages complete without errors
2. Game designer produces correct mechanic types with config data
3. Scene architect generates mechanic-specific configs (not empty)
4. Interaction designer produces per-mechanic scoring + feedback + transitions + tasks
5. Asset generator produces correct asset types per mechanic (not just diagram+zones for all)
6. Blueprint has all required frontend config fields populated
7. Frontend renders correct component without MechanicConfigError
8. Rich visual assets are present (illustrations, themed designs, etc.)
9. Game is playable with proper scoring and feedback
10. Multi-mechanic transitions work (mode switches correctly)

---

## Appendix A: Research Sources

### Per-Mechanic Research (8 research agents, Feb 2026)

**Sequencing:** Timeline board game, Nobel Prize Cell Cycle Game, H5P Image Sequencing, Mayer's multimedia principles, cognitive load scaffolding.
**Memory Match:** BookWidgets (10+ variations), Quizlet Match, Educaplay, Khan Academy, concentration variants, explanation-on-match pattern.
**Sorting:** BrainPOP Sortify, Shodor Venn Diagram, MakeSort, The Vortex, iterative correction loop, taxonomy visualization.
**Branching:** Body Interact, Oxford Medical Simulation, H5P Branching Scenario, Ren'Py visual novel model, foldback narrative, decision tree visualization (Haworth et al.).
**Compare/Contrast:** Lab AIDS Cell Simulation, Ask A Biologist Cell Viewer, react-compare-slider, Shodor, multi-phase progression pattern.
**Click/Trace/Description:** Kenhub adaptive model, Visible Body, PhET simulations, AHA blood flow animation, H5P Image Hotspot, H5P Drag and Drop.
**Drag_Drop Richness:** BioDigital Human, Complete Anatomy, Seterra, leader lines, progressive hints, zoom/pan, WCAG 2.5.7.
**New Mechanics:** LM-GM framework, Bloom's taxonomy mapping, predict_observe_explain, spot_the_error, cloze_fill, process_builder, cause_effect_chain.

### Architecture Research (V4 Agentic Frameworks)

Quality Gate pattern, LangGraph Send API (Map-Reduce), Hierarchical Meta-Graph, Contract-Based Communication, Fresh LLM on retry, Multi-Agent Debate, DSPy integration, Sherlock speculative execution. 43 academic papers referenced.
