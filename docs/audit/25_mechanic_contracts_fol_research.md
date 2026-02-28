# Research: Mechanic Contracts, FOL Game Engine, and Pipeline Bias Analysis

**Date**: 2026-02-12
**Scope**: V3 pipeline architecture research — bias analysis, token optimization, FOL game specification, mechanic contracts
**Status**: Complete

---

## Executive Summary

The V3 pipeline has a **systemic label/diagram bias** — not just 33 instances of `drag_drop` defaults, but a pipeline-wide architectural assumption that every game is an interactive diagram with zones and labels. This bias originates at the Domain Knowledge Retriever (unconditionally extracts canonical_labels) and cascades through every downstream agent, tool, schema, and frontend component. Non-label mechanics (branching_scenario, memory_match, sequencing, sorting_categories) are forced into this model and produce broken or degraded output.

Additionally, the pipeline consumes ~54,000 prompt tokens per run due to redundant reference material injection, full state serialization, and unscoped domain knowledge injection.

---

## Section 1: Label/Diagram Bias — Full Pipeline Trace

### 1.1 API Entry Point (`backend/app/routes/generate.py`)

| Bias | Location | Detail |
|------|----------|--------|
| Default preset is "interactive_diagram_hierarchical" | Line 389 | `pipeline_preset = body.pipeline_preset or config.pipeline_preset or "interactive_diagram_hierarchical"` |

If no preset is specified, the system automatically assumes an interactive diagram game.

### 1.2 Input Enhancer (`backend/app/agents/input_enhancer.py`)

**No bias found.** Input enhancer extracts pedagogical context (Bloom's level, subject, difficulty, learning objectives) without assuming game type. This is the ONE clean layer.

### 1.3 Domain Knowledge Retriever — CRITICAL BIAS SOURCE

**File**: `backend/app/agents/domain_knowledge_retriever.py`

| Bias | Lines | Detail |
|------|-------|--------|
| **Unconditionally extracts canonical_labels** | 527-591 | Prompt ALWAYS asks for "canonical_labels: exhaustive list of correct labels for the diagram" |
| **Requires minimum 4 labels** | 616-620 | `if label_count < 4: validation_errors.append(...)` — a branching_scenario with no diagram gets flagged |
| **Always generates label_descriptions** | 629-635 | Calls `_generate_label_descriptions()` even when mechanic doesn't need labels |
| **Promotes canonical_labels to top-level state** | 681-683 | `"canonical_labels": canonical_labels` — signals labels are pipeline-central |

**Schema confirmation** (`backend/app/agents/schemas/domain_knowledge.py` line 151):
```
canonical_labels: List[str] = Field(min_length=1)  # REQUIRED, min 1 label
```

**Impact**: A question like "Create a branching scenario about medical triage decisions" will:
1. Force extraction of "canonical_labels" (inventing labels from the topic)
2. Fail validation if fewer than 4 labels extracted
3. Generate label_descriptions that branching_scenario won't use
4. Pass these unwanted labels to all downstream agents

### 1.4 Router (`backend/app/agents/router.py`)

| Bias | Lines | Detail |
|------|-------|--------|
| Fallback to INTERACTIVE_DIAGRAM | 567-646 | `template_type = "INTERACTIVE_DIAGRAM"` as default |
| Template registry is diagram-centric | 75-89, 290-305 | Both INTERACTIVE_DIAGRAM definitions describe "label parts of a diagram" |

### 1.5 Game Planner (`backend/app/agents/game_planner.py`)

| Bias | Lines | Detail |
|------|-------|--------|
| Default mechanic is DRAG_DROP | 160 | `if not detected: detected = [(MechanicType.DRAG_DROP, 0.5)]` |

### 1.6 State TypedDict (`backend/app/agents/state.py`)

| Bias | Lines | Detail |
|------|-------|--------|
| ~30 fields for diagram/label/zone data | 357-410 | `diagram_image`, `sam3_prompts`, `diagram_segments`, `diagram_zones`, `diagram_labels`, `zone_groups`, `generated_diagram_path`, `image_classification` |
| ~5 fields for generic game mechanics | 456-485 | `game_design_v3`, `scene_specs_v3`, `interaction_specs_v3`, `generated_assets_v3` |

The state model itself has 6x more fields for diagrams than for generic game mechanics.

### 1.7 Game Designer V3 (`backend/app/agents/game_designer_v3.py`)

| Bias | Lines | Detail |
|------|-------|--------|
| Labels listed as mandatory output | 50-56 | "Label design (zone_labels, distractor_labels with explanations)" in "You DO define" section |
| Task prompt requires labels | 212 | "labels (zone_labels, distractor_labels with text + explanation)" |
| Memory_match guidance says "from the labels" | 84 | Suggests memory_match derives from zone labels, not independent pairs |
| Canonical_labels injected into prompt | 133-151 | `"## Known Labels\nThese labels have been identified..."` |

### 1.8 Game Design Schema (`backend/app/agents/schemas/game_design_v3.py`)

| Bias | Lines | Detail |
|------|-------|--------|
| LabelDesign is mandatory | 903 | `labels: LabelDesign = Field(default_factory=LabelDesign)` |
| Every scene has zone_labels | 859 | `zone_labels: List[str]` in SceneDesign |
| zone_labels_used mandatory per mechanic | 802 | ALL mechanics have `zone_labels_used: List[str]` |
| Validation requires min 3 zone_labels | 1165-1166 | `if len(all_zone_labels) < 3: issues.append(...)` |
| zone_labels_used validated against scene labels | 1242-1249 | Forces every mechanic to reference scene zone_labels |

**Impact**: A memory_match game with 10 term-definition pairs but 0 zone_labels **FAILS validation**.

### 1.9 Scene Architect V3 (`backend/app/agents/scene_architect_v3.py`)

| Bias | Lines | Detail |
|------|-------|--------|
| Always produces zones | 27-65 | "What You Produce" lists zones as mandatory output per scene |
| Zone ID convention assumes labels | 48 | "Generate zone_ids by snake_casing the label" |
| SceneSpecV3 requires zones | 145 | `zones: List[ZoneSpecV3]` (required field) |

### 1.10 Tools Layer — check_capabilities

**File**: `backend/app/tools/game_design_v3_tools.py`

| Bias | Lines | Detail |
|------|-------|--------|
| ALL mechanics list canonical_labels as required | 185-246 | `branching_scenario: {"required_data": ["canonical_labels"]}` |
| memory_match: canonical_labels required | 227 | Even though pairs are independent of labels |

**Impact**: The ReAct agent reads this tool output and believes ALL mechanics require labels.

### 1.11 Tools Layer — generate_mechanic_content

**File**: `backend/app/tools/scene_architect_tools.py`

| Bias | Lines | Detail |
|------|-------|--------|
| Branching uses zone_labels for concepts | 593-636 | `"create a branching educational scenario using these concepts: {json.dumps(zone_labels[:8])}"` |
| Falls back to empty when no labels | 647-655 | `result["generated"] = False` when zone_labels empty |

**Impact**: For a branching_scenario with no diagram, `generate_mechanic_content` returns empty config.

### 1.12 Tools Layer — misconception feedback

**File**: `backend/app/tools/interaction_designer_tools.py`

| Bias | Lines | Detail |
|------|-------|--------|
| Takes zone_labels as input | 114 | `zone_labels: List[str]` parameter |
| Misconception model is trigger_label + trigger_zone | 140-170 | Assumes misconceptions are about placing labels in wrong zones |

### 1.13 Tools Layer — blueprint assembler

**File**: `backend/app/tools/blueprint_assembler_tools.py`

| Bias | Lines | Detail |
|------|-------|--------|
| Unconditionally builds zones from labels | 302-350 | Loops over `scene_zone_labels` to create zone entries |
| Labels require correctZoneId | 422-435 | Every label maps to a zone — no concept of label-free mechanics |
| Empty zones/labels for non-diagram games | 326, 427 | Blueprint published with empty `zones[]` and `labels[]` |

### 1.14 Frontend Types

**File**: `frontend/src/components/templates/InteractiveDiagramGame/types.ts`

| Bias | Lines | Detail |
|------|-------|--------|
| Label requires correctZoneId | 213-223 | `correctZoneId: string` — assumes every label maps to a zone |
| labels[] is required on blueprint | 225 | Part of InteractiveDiagramBlueprint |

---

## Section 2: Which Mechanics Actually Need Labels

| Mechanic | Needs Labels/Zones? | Primary Data Type | Current State |
|----------|---------------------|-------------------|---------------|
| **drag_drop** | YES | zone_labels → zones | Works |
| **click_to_identify** | YES | zone_labels → zones + prompts | Works |
| **trace_path** | YES | zone_labels as waypoints → zones | Works |
| **description_matching** | YES | zone_labels → zones + descriptions | Works |
| **hierarchical** (as mode) | YES | zone_labels with parent-child | Works |
| **sequencing** | NO | `items: [{id, text}]` with `correct_order` | Forced into labels |
| **sorting_categories** | NO | `categories` + `items` with assignments | Forced into labels |
| **memory_match** | NO | `pairs: [{term, definition}]` | Forced into labels |
| **branching_scenario** | NO | `nodes: [{prompt, choices}]` | Forced into labels |
| **compare_contrast** | PARTIAL | Two subjects + categories | Forced into single-image labels |

5 of 10 mechanics DON'T need labels. They have their own entity types (items, pairs, nodes, categories). Yet the entire pipeline forces them through a label-centric model.

---

## Section 3: Token Optimization Analysis

### 3.1 Token Distribution (54K total across 4 agents)

| Category | Tokens | % |
|----------|--------|---|
| Core agent prompts (system + task + tools) × 4 | ~22,000 | 41% |
| Tool call results and iteration history | ~10,000 | 19% |
| Full state serialization and DK injection | ~10,000 | 19% |
| Tool implementations and registry data | ~5,000 | 9% |
| Retry loops, validation feedback | ~7,000 | 13% |

### 3.2 Per-Agent System Prompt Sizes

| Agent | Chars | Lines | Tokens |
|-------|-------|-------|--------|
| game_designer_v3 | 3,470 | 67 | ~868 |
| scene_architect_v3 | 1,933 | 38 | ~483 |
| interaction_designer_v3 | 3,744 | 66 | ~936 |
| asset_generator_v3 | 2,224 | 42 | ~556 |
| **Total** | **11,371** | **213** | **~2,843** |

### 3.3 Reference Material Sizes

| Component | Chars | Tokens | Used By |
|-----------|-------|--------|---------|
| `format_patterns_for_prompt()` (interaction_patterns.py) | 5,688 | ~1,422 | game_designer_v3 only |
| `format_scoring_strategies_for_prompt()` | 860 | ~215 | game_designer_v3 only |
| `format_animations_for_prompt()` | 1,374 | ~343 | game_designer_v3 only |
| `_MECHANIC_SCENE_GUIDANCE` dict (scene_architect_v3) | 2,505 | ~626 | scene_architect_v3 only |

### 3.4 Tool File Sizes (loaded for tool registry)

| File | Chars | Tokens |
|------|-------|--------|
| game_design_v3_tools.py | 27,893 | ~6,973 |
| scene_architect_tools.py | 44,192 | ~11,048 |
| interaction_designer_tools.py | 48,067 | ~12,016 |
| asset_generator_tools.py | 48,767 | ~12,191 |

### 3.5 Optimization Opportunities

| Optimization | Savings | Effort |
|-------------|---------|--------|
| Scoped DK injection (only mechanic-relevant fields) | 2,000-4,000 | Low |
| Remove reference material from downstream agents | 1,500-3,000 | Low |
| Compact tool schemas (minimal descriptions) | 2,000-4,000 | Medium |
| Selective state propagation (summaries not full JSON) | 3,000-5,000 | Medium |
| Reduce validation retry feedback to top 3-5 issues | 1,000-2,000 | Low |
| **Total potential** | **9,500-18,000** | |

---

## Section 4: Data Loss Map (Agent to Frontend)

| Agent | Fields Produced | % Lost | Critical Losses |
|---|---|---|---|
| **game_designer_v3** | 30+ | ~33% | learning_objectives, difficulty, theme narrative |
| **scene_architect_v3** | 25+ | ~20% | zone hints, reveal_trigger, timed_config |
| **interaction_designer_v3** | 30+ | ~50% | mode_transitions, animations, distractor_feedback, scene_completion, scoring strategy |
| **asset_generator_v3** | 10+ | ~18% | confidence, detection_method |

Root cause: `blueprint_assembler_tools.py` only maps fields in the old InteractiveDiagramBlueprint schema.

---

## Section 5: Hierarchical — Mode vs Mechanic

### Current State
- `HierarchyController` is a **standalone mechanic** owning its own DndContext
- It completely replaces drag_drop — not a wrapper, not composable
- Listed as a case in MechanicRouter switch, peer to drag_drop/trace_path/etc.

### Temporal Constraint System (Already Orthogonal)
- `updateVisibleZones()` in Zustand works across ALL mechanics
- Evaluates constraints: `before`, `after`, `mutex`, `concurrent`, `sequence`
- Zone groups with `revealTrigger` (`complete_parent`, `click_expand`, `hover_reveal`)
- This system ALREADY enables progressive zone reveal for ANY mechanic

### Proposed: Composable Mode
```typescript
// Instead of: case 'hierarchical': return <HierarchyController ... />
// Becomes: any mechanic can be wrapped with progressive reveal
const hasHierarchy = bp.zoneGroups?.length > 0;
const content = renderMechanic(mode);
return hasHierarchy
  ? <HierarchicalWrapper zoneGroups={bp.zoneGroups}>{content}</HierarchicalWrapper>
  : content;
```

### What This Enables
- `drag_drop + hierarchical` — zones reveal progressively as labels are placed
- `trace_path + hierarchical` — path waypoints reveal as parent structures are traced
- `sequencing + hierarchical` — sequence items appear in layers
- Any mechanic gets progressive reveal "for free"

---

## Section 6: Frontend Game Engine Architecture

### Current Architecture
- **Zustand store** (1679 lines): Single source of truth for all game state
- **MechanicRouter.tsx**: switch on `interactionMode` renders mechanic component
- **Mode transitions**: declarative `{from, to, trigger}` evaluated by `checkModeTransition()`
- **Per-mechanic progress**: tracked separately (sequencingProgress, sortingProgress, etc.)
- **Temporal constraints**: hierarchy DAG controls zone visibility across ALL mechanics

### Frontend Minimum Viable Fields Per Mechanic

| Mechanic | Required Config | Error If Missing |
|---|---|---|
| drag_drop | `diagram.zones`, `labels` | No (graceful) |
| click_to_identify | `identificationPrompts[]` | No (broken UX) |
| trace_path | `paths[].waypoints` | No (nothing clickable) |
| sequencing | `sequenceConfig.items + correctOrder` | No (falls back to labels) |
| sorting_categories | `sortingConfig.categories + items` | **MechanicConfigError** |
| description_matching | `descriptionMatchingConfig.descriptions` | No (generates from zone.description) |
| memory_match | `memoryMatchConfig.pairs` | **MechanicConfigError** |
| branching_scenario | `branchingConfig.nodes + startNodeId` | **MechanicConfigError** |
| compare_contrast | `compareConfig.diagramA + diagramB + expectedCategories` | No (single-image fallback) |
| hierarchical | `zoneGroups + labels` | No (flat zones) |

---

## Section 7: Architecture Vision — Incremental Game State Builder

### Current Flow (Blueprint Assembler Bottleneck)
```
game_designer → scene_architect → interaction_designer → asset_generator
         ↓              ↓                  ↓                   ↓
     game_design    scene_specs      interaction_specs    generated_assets
         ↓              ↓                  ↓                   ↓
                  blueprint_assembler_v3 (deterministic merge)
                             ↓
                    blueprint JSON (30% data loss)
                             ↓
                    Frontend Zustand store
```

### Proposed Flow (Incremental State Building)
```
game_designer → writes game skeleton to GameState
  ├─ scenes[], mechanic_types, entities, labels (only for label-based mechanics)
  ├─ VALIDATED against contract: "does each mechanic have required config seeds?"

scene_architect → populates per-scene structure in GameState
  ├─ zones[] (for label mechanics), mechanic_configs[], constraints[]
  ├─ VALIDATED: "does each mechanic_config have required output fields?"

interaction_designer → adds behavioral rules to GameState
  ├─ scoring_rules[], feedback_rules[], transition_rules[], completion_predicates[]
  ├─ VALIDATED: "does each mechanic have scoring + feedback + completion predicate?"

asset_generator → fills visual data in GameState
  ├─ diagram_urls[], zone_coordinates[] per scene
  ├─ VALIDATED: "does each scene have required visual assets?"

NO blueprint_assembler → The GameState IS the blueprint
  ├─ Each agent validated against mechanic contract as it writes
  ├─ Zero data loss — everything agents produce reaches frontend
  └─ Frontend consumes GameState directly
```

---

## Section 8: Per-Mechanic Contract Registry

### Contract Structure
```
MechanicContract {
  dk_fields: Set[str]           — Which DK sub-fields this mechanic uses
  game_designer: StageContract  — What game_designer must output
  scene_architect: StageContract — What scene_architect must output
  interaction_designer: StageContract — What interaction_designer must output
  asset_generator: StageContract — What asset_generator must output
  frontend_required: FrontendContract — Minimum viable blueprint fields
}
```

### Complete Contract Table

| Mechanic | DK Fields | Game Designer Output | Scene Architect Output | Interaction Designer Output | Asset Generator Output | Frontend Required |
|---|---|---|---|---|---|---|
| **drag_drop** | label_descriptions, spatial_data | zone_labels | zones + positions | scoring + feedback per zone | image + zone coords | `zones[]`, `labels[]` |
| **click_to_identify** | label_descriptions, spatial_data | click_config.prompts | zones + prompts per zone | progressive scoring + identification feedback | image + zone coords | `identificationPrompts[]` |
| **trace_path** | sequence_flow_data, process_steps | path_config.waypoints | zones + ordered waypoints | path scoring + step-by-step feedback | image with visible pathways | `paths[].waypoints[]` |
| **sequencing** | sequence_flow_data, process_steps | sequence_config.correct_order | items + correct_order | position-based scoring + ordering feedback | image with separated stages | `sequenceConfig.items + correctOrder` |
| **sorting_categories** | comparison_data, content_characteristics | sorting_config.categories+items | categories + item assignments | category scoring + per-item feedback | image with distinct items | `sortingConfig.categories + items` **ERROR** |
| **description_matching** | label_descriptions | description_match_config | zones + descriptions per zone | match scoring + description-visual feedback | image with identifiable structures | `descriptionMatchingConfig.descriptions` |
| **memory_match** | label_descriptions, term_definitions | memory_config.pairs | term-definition pairs | pair scoring + match explanation feedback | image with identifiable structures | `memoryMatchConfig.pairs` **ERROR** |
| **branching_scenario** | causal_relationships, process_steps | branching_config.nodes | decision nodes + choices + consequences | decision scoring + consequence feedback | scene-relevant image | `branchingConfig.nodes + startNodeId` **ERROR** |
| **compare_contrast** | comparison_data, content_characteristics | compare_config.subjects | comparison categories | categorization scoring + similarity/difference feedback | **TWO images** (one per subject) | `compareConfig.diagramA + diagramB` |
| **hierarchical** (as mode) | hierarchical_relationships | labels.hierarchy | zone_groups + reveal_trigger | layer-based scoring + parent-child feedback | layered/nested image | `zoneGroups[]` (mode flag) |

---

## Section 9: FOL / Declarative Game Engine Research

### 9.1 Research Scope

Evaluated 10 declarative game specification systems for suitability as the rule engine behind our AI-generated educational games. Each system assessed on: JSON serializability, browser runtime availability, React/TypeScript integration, LLM generation reliability, state machine support, rule evaluation capabilities, and performance.

### 9.2 Per-System Evaluation

#### 1. GDL (Game Description Language) — Stanford

Datalog-based logic programming with 5 core predicates: `init`, `legal`, `next`, `terminal`, `goal`.

| Dimension | Assessment |
|-----------|-----------|
| **Pros** | Mathematically complete; clean game logic / rendering separation; formal verification; strong academic foundation |
| **Cons** | No browser runtime (requires Prolog engine in JS); terrible LLM generation (2/10); no visual/interaction semantics; Datalog resolution is slow for real-time; flat state model (no hierarchy) |
| **Integration** | Very High cost, Low value. Would need custom Datalog interpreter in TypeScript + LLM fine-tuning |
| **LLM Reliability** | **2/10** — Brittle syntax, missing parens produce silent failures, no training data |

#### 2. VGDL (Video Game Description Language) — NYU

Describes 2D arcade games via SpriteSet, InteractionSet (pairwise collisions), LevelMapping, TerminationSet.

| Dimension | Assessment |
|-----------|-----------|
| **Pros** | Proven LLM generation for arcade games; pairwise interaction rules; composable termination conditions; open-source Python framework |
| **Cons** | Arcade-game-centric (collision physics); no browser runtime (Python-only); no ordered sequences, categories, hierarchies; flat entity model; no UI semantics |
| **Integration** | High cost, Medium-Low value. Needs TypeScript interpreter + extensions for educational mechanics |
| **LLM Reliability** | **5/10** — Good for Pac-Man, poor for our 10 mechanics |

#### 3. XState (Statecharts) — David Khourshid

Harel statecharts with hierarchical/parallel states, guards, actions, context, delayed transitions, invoked services. Fully JSON-serializable. `@xstate/react` provides native hooks. XState v5 is TypeScript-native.

| Dimension | Assessment |
|-----------|-----------|
| **Pros** | JSON-serializable machines; native React integration (`useMachine()`); hierarchical + parallel states; guards as rule evaluation; delayed transitions for temporal constraints; official visualizer (stately.ai); 25k+ GitHub stars; O(1) per transition |
| **Cons** | Not a rule engine (evaluating collections of conditional rules is verbose); LLM generation complexity for large nested machines (6/10); guard functions aren't pure JSON (need pre-registration); context mutations require `assign()` function references |
| **Integration** | Low-Medium cost, High value. Machines generated server-side as JSON, consumed by frontend |
| **LLM Reliability** | **6/10** — Simple machines reliable, complex hierarchical machines drop off |

#### 4. json-rules-engine — CacheControl

Lightweight JS/TS library. Rules as `{conditions: {all/any: [...]}, event: {type, params}, priority}`. Custom operators. Lazy fact resolution. 15KB minified, zero dependencies.

| Dimension | Assessment |
|-----------|-----------|
| **Pros** | Pure JSON rules (highly LLM-generatable); custom operators (`isCorrectPlacement`, `matchesCategory`); nested `all`/`any` conditions; priority ordering; lazy fact resolution; browser-native (15KB); event emission drives React state |
| **Cons** | No state machine semantics (no modes/phases); no temporal transitions; stateless evaluation (external state management needed); flat rule sets (no hierarchical rule groups); no TypeScript inference on rule content |
| **Workaround for hierarchical** | Multiple engine instances (one per mechanic/mode), switched based on game state |
| **Performance** | 100 rules: ~0.3ms, 500 rules: ~1.5ms, 1000 rules: ~4ms. Our use (20-50 rules): sub-millisecond |
| **Integration** | Low cost, High value. JSON generated by Python backend, consumed by TypeScript frontend |
| **LLM Reliability** | **8/10** — Simple `{conditions, event}` format, well-constrained, schema-validatable |

#### 5. Miniplex ECS (Entity-Component-System)

TypeScript ECS for browser games. Entities = IDs, Components = data, Systems = functions iterating entities.

| Dimension | Assessment |
|-----------|-----------|
| **Pros** | Clean data/logic separation; TypeScript-native; React integration via `@miniplex/react`; archetype-based queries |
| **Cons** | Systems are code, not data (LLM can't generate as JSON); no rule/state machine semantics; overkill for 5-20 entities; no serialization format; no transitions |
| **Integration** | Medium cost, Low value. Adds complexity without solving declarative rule specification |
| **LLM Reliability** | **3/10** — Can generate entity data, cannot reliably generate system logic |

#### 6. GDevelop Events

Open-source 2D game engine. Condition/action event pairs as JSON.

| Dimension | Assessment |
|-----------|-----------|
| **Pros** | JSON format; condition/action pattern; sub-event nesting; open source |
| **Cons** | Tightly coupled to GDevelop runtime (GDJS, 500KB+); 2D sprite assumptions; no TypeScript; internal format not designed for programmatic generation |
| **Integration** | Very High cost, Low value. Architecturally incompatible with React/Zustand |
| **LLM Reliability** | **3/10** — Internal format, poorly documented, minimal training data |

#### 7. Ludii Ludemes — Maastricht University

Composable typed "ludemes" (game building blocks) with S-expression syntax. 1000+ board games described. Java runtime.

| Dimension | Assessment |
|-----------|-----------|
| **Pros** | Composable typed primitives; rich academic foundation; formal semantics |
| **Cons** | Java-only runtime; board-game-centric (turn-based with pieces); S-expression syntax hostile to LLMs; no browser support; no interaction model |
| **Integration** | Very High cost, Low value. Ground-up reimplementation needed |
| **LLM Reliability** | **3/10** — S-expression syntax, domain-specific ludeme names, minimal training data |

#### 8. PuzzleScript

Minimalist grid-based puzzle language. Objects + pattern→replacement rules + win conditions.

| Dimension | Assessment |
|-----------|-----------|
| **Pros** | Extremely simple syntax; proven LLM generation for grid puzzles; browser JS runtime; self-contained |
| **Cons** | Grid-locked (no arbitrary positioning); no scoring (win/lose only); no rich state; only push/pull/move; pixel art rendering |
| **Integration** | Low cost for grid puzzles, Very Low value (wrong paradigm — 9/10 mechanics cannot be expressed) |
| **LLM Reliability** | **9/10 for grid puzzles, 0/10 for our mechanics** |

#### 9. PDDL (Planning Domain Definition Language)

AI planning standard. Domain (action schemas with preconditions/effects) + Problem (initial + goal state).

| Dimension | Assessment |
|-----------|-----------|
| **Pros** | Formal verification (solvability, difficulty); precondition/effect model maps to game actions; rich typing (PDDL 2.1+); solution verification |
| **Cons** | Planning, not gameplay (finds paths, doesn't evaluate actions); no browser runtime (C++/Java); no reactive semantics; no feedback model; verbose |
| **Integration** | Medium cost (backend only), Medium value (validation tool, not runtime engine) |
| **LLM Reliability** | **5/10** — Well-represented in training data, but correct action schemas require domain expertise |

#### 10. Business Rules Engines (json-logic, nools, Drools)

**json-logic**: Tiny spec for logic as JSON. Operators: `==`, `>`, `and`, `or`, `if`, `var`. 5KB runtime.
**nools**: Node.js Rete engine (unmaintained since 2017). **Drools**: Enterprise Java rules engine.

| Dimension | Assessment |
|-----------|-----------|
| **json-logic Pros** | Pure JSON; 5KB runtime; deterministic; browser-native; custom operations; wide adoption |
| **json-logic Cons** | Expression-level only (no rule sets/priorities/events); no side effects; limited built-in operators; completely stateless |
| **nools** | Unmaintained — not recommended |
| **Drools** | Java-only, extremely heavy — not recommended |
| **Integration** | Very Low cost, Medium value (as expression evaluator inside json-rules-engine conditions) |
| **LLM Reliability** | **json-logic: 9/10** — Simple constrained JSON |

### 9.3 Comparative Analysis

| Dimension | XState | json-rules-engine | json-logic | VGDL | GDL | PDDL | PuzzleScript | Miniplex |
|---|---|---|---|---|---|---|---|---|
| **JSON Serializable** | Yes | Yes | Yes | No | No | No | No | No |
| **Browser Runtime** | Excellent | Excellent | Excellent | None | None | None | Good (grid) | Good |
| **React Integration** | Native | Easy | Trivial | None | None | None | None | Yes |
| **TypeScript Types** | Native (v5) | Good | Weak | None | None | None | None | Native |
| **LLM Generation** | 6/10 | 8/10 | 9/10 | 5/10 | 2/10 | 5/10 | 9/10* | 3/10 |
| **State Machines** | Native | None | None | None | Implicit | None | None | None |
| **Rule Evaluation** | Guards only | Native | Expression only | Collision | Datalog | Preconditions | Pattern | None |
| **Hierarchical States** | Native | None | None | None | None | None | None | None |
| **Parallel States** | Native | None | None | None | None | None | None | None |
| **Temporal** | Delayed transitions | None | None | Frame | None | Durative | Tick | None |
| **Custom Operators** | Guards | Yes | Yes | No | No | No | No | Queries |
| **Performance** | O(1)/transition | <1ms/50 rules | <0.1ms/eval | N/A | N/A | N/A | Fast (grid) | Fast |
| **Maturity** | Very High (25k★) | High (2k★) | High (1.5k★) | Academic | Academic | Academic | Niche | Growing |

*PuzzleScript 9/10 only for grid-based puzzles; N/A for our mechanics.

### 9.4 XState vs json-rules-engine: Head-to-Head

**XState advantages:**
1. State machine semantics (knows what "mode" the game is in)
2. Transition control (prevents invalid state transitions by design)
3. Temporal transitions (native "show feedback for 2s then advance")
4. Parallel state (score, timer, UI mode evolve independently)
5. Visualization (stately.ai renders any machine as state diagram)
6. Full TypeScript inference on states, events, context

**json-rules-engine advantages:**
1. Simpler LLM generation (`{conditions, event}` vs nested state machines)
2. Dynamic rule sets (add/remove at runtime without rebuilding)
3. Custom operators (domain-specific predicates are first-class)
4. Priority ordering (built-in evaluation sequence)
5. Lazy fact resolution (compute only what's needed)
6. Pure evaluation (no side effects, highly testable)

**Verdict: They solve different problems.** XState manages game flow (modes, phases, transitions). json-rules-engine evaluates game rules (scoring, validation, feedback).

### 9.5 Recommended Architecture: XState + json-rules-engine Hybrid

```
┌─────────────────────────────────────────────────────┐
│                    XState Machine                     │
│  (Game Flow: modes, phases, transitions, timing)     │
│                                                       │
│  ┌───────────┐  ┌───────────┐  ┌──────────────────┐ │
│  │  LOADING   │→ │  PLAYING   │→ │    REVIEWING     │ │
│  └───────────┘  │            │  └──────────────────┘ │
│                  │ ┌────────┐ │                       │
│                  │ │per-move│ │  json-rules-engine    │
│                  │ │  rules │ │  evaluates:           │
│                  │ │  eval  │ │  - scoring rules      │
│                  │ └────────┘ │  - feedback rules     │
│                  └────────────┘  - completion check   │
│                                                       │
│  Context: { score, placements, timeElapsed, ... }    │
└─────────────────────────────────────────────────────┘
```

**How it works:**
1. **XState machine** defines game lifecycle: `idle → loading → instructions → playing → reviewing → complete`. Per-mechanic sub-states within `playing`. Parallel regions for timer + score. Delayed transitions for feedback duration.
2. **json-rules-engine** evaluates mechanic-specific rules within the `playing` state. On each user action, XState sends to json-rules-engine → evaluates scoring/feedback/completion → emits events back to XState.
3. **json-logic** (optional) serves as expression evaluator within json-rules-engine conditions.

**Data flow:**
```
User Action (drop label on zone)
  → XState event: { type: 'PLACE_LABEL', label: 'mitochondria', zone: 'zone_3' }
  → XState action: evaluate rules via json-rules-engine
  → json-rules-engine evaluates against facts:
    - Rule 1 (scoring): label matches zone → emit 'CORRECT_PLACEMENT'
    - Rule 2 (completion): all labels placed → emit 'ALL_PLACED'
  → Events → XState: score += points, transition to 'reviewing'
  → React re-renders via @xstate/react useMachine()
```

### 9.6 What the LLM Generates

The interaction_designer agent produces a `GameSpecification`:

```typescript
interface GameSpecification {
  stateMachine: {                    // XState machine (game flow)
    id: string;
    initial: string;
    context: Record<string, any>;
    states: Record<string, StateDefinition>;
  };
  ruleSets: {                        // json-rules-engine (per mechanic)
    [mechanicId: string]: {
      scoringRules: Rule[];
      feedbackRules: Rule[];
      completionRules: Rule[];
      transitionRules: Rule[];
    };
  };
  operators: {                       // Custom operators (mechanic-specific)
    [name: string]: {
      type: 'equality' | 'comparison' | 'containment' | 'spatial';
      description: string;
    };
  };
}
```

Validated at build-time with Zod schemas (frontend) and Pydantic (backend).

### 9.7 Concrete Examples

#### Example 1: drag_drop — Anatomy Label Placement

**XState machine**: `instructions → playing (parallel: interaction + timer) → reviewing → complete`. Interaction sub-states: `awaiting_drop → evaluating → showing_feedback` (1.5s delay). Timer: 5-minute timeout.

**json-rules-engine rules**:
- Scoring: `{fact: "correctMappings", operator: "containsEntry", value: {fact: "lastPlacement"}}` → emit `CORRECT_PLACEMENT` (+1 point)
- Completion: `{fact: "placedCount", operator: "greaterThanInclusive", value: {fact: "totalZones"}}` → emit `ALL_PLACED`
- Feedback: score >= 80% → "excellent"; score >= 50% → "good"

#### Example 2: sequencing — Mitosis Stages

**XState machine**: `instructions → playing (arranging → evaluating → showing_result/showing_hint) → reviewing → complete`. Supports hint requests (max 3).

**json-rules-engine rules**:
- Scoring: `{fact: "currentSequence", operator: "isExactSequence", value: {fact: "correctSequence"}}` → `PERFECT_SEQUENCE` (100 points). Partial credit via `correctPairCount`.
- Completion: attempts >= 1 AND exact sequence match → `SEQUENCE_COMPLETE`
- Feedback: detects specific adjacent-pair errors → targeted hints (e.g., "chromosomes condense before they line up")

Custom operator: `isExactSequence` compares student order against correct order.

#### Example 3: branching_scenario — Clinical Decision-Making

**XState machine**: Scene graph with branching transitions. `scene_1 → (CHOOSE_A: scene_2a, CHOOSE_B: scene_2b, CHOOSE_C: scene_2c [critical error])`. Each path leads to good/neutral/poor outcome. Recovery from critical errors.

**json-rules-engine rules**:
- Scoring: Per-scene, per-choice rules with `points`, `consequence` text, `reasoning` explanation
- Critical errors: `CHOOSE_C` at scene_1 → `CRITICAL_ERROR` (-5 points, flags error)
- Transition: `criticalMissedCount > 2` → `FORCE_REVIEW` (early termination)

XState naturally models branching scenarios — each scene is a state, each choice is a transition. The entire decision tree IS the state machine.

### 9.8 Key Insight: Zustand Coexistence

**Critical concern**: We already have a 1679-line Zustand store managing all game state. Adding XState creates a dual state management problem.

**Resolution options**:
1. **XState replaces Zustand for game logic** — Zustand remains for UI state only (sidebar open, theme, etc.). Game state lives in XState context.
2. **XState orchestrates, Zustand persists** — XState manages flow/transitions, Zustand stores the flat game data. XState actions dispatch to Zustand.
3. **json-rules-engine only** (no XState) — Keep Zustand as sole state manager. json-rules-engine evaluates rules against Zustand state as facts. Simpler but loses temporal transitions and parallel state.

**Recommendation for Phase A**: Option 3 (json-rules-engine only). Minimum disruption. Zustand handles state, json-rules-engine handles rule evaluation. XState added in Phase C when we need formal game flow orchestration.

### 9.9 Implementation Roadmap

| Phase | Timeline | What Changes |
|-------|----------|-------------|
| **Phase 1: Foundation** | Week 1-2 | Install json-rules-engine; define `GameSpecification` interface + Zod schema; implement custom operator registry for 10 mechanics; build `useRuleEvaluator()` hook |
| **Phase 2: LLM Integration** | Week 2-3 | Update interaction_designer Pydantic schema for rule output; add backend validation; embed rules in blueprint JSON; few-shot examples per mechanic |
| **Phase 3: Frontend Runtime** | Week 3-4 | Build `useRuleEvaluator()` hook; wire to Zustand fact providers; replace hardcoded scoring/feedback logic; action→event bridge |
| **Phase 4: Migration** | Week 4-5 | Migrate drag_drop first; validate generated specs; migrate remaining 9 mechanics; add playability_validator |
| **Phase 5: XState (Optional)** | Week 6-8 | Add XState for game flow orchestration; replace ad-hoc mode transition logic; parallel state for timer/score |

### 9.10 Summary Table

| System | Recommended | Role | Key Reason |
|--------|-------------|------|-----------|
| **json-rules-engine** | **Yes (Primary)** | Mechanic rule evaluation | JSON rules, custom operators, LLM-generatable (8/10), browser-performant |
| **XState** | **Yes (Phase C)** | Game flow orchestration | Hierarchical/parallel states, temporal transitions, React-native |
| **json-logic** | **Optional** | Expression evaluator | Ultra-simple JSON expressions for computed values inside rules |
| **Zod** | **Yes (Supporting)** | Spec validation | TypeScript-native schema validation for generated specs |
| GDL | No | — | No browser runtime, poor LLM generation |
| VGDL | No | — | Arcade-centric, no browser runtime |
| PuzzleScript | No | — | Grid-locked, wrong paradigm |
| Ludii | No | — | Java-only, board-game-centric |
| PDDL | Partial | Backend validation tool | Solvability verification, difficulty computation (not runtime) |
| Miniplex | No | — | Systems are code not data |
| GDevelop | No | — | Coupled to GDevelop runtime |
| Drools/nools | No | — | Java-only / unmaintained |

---

## Section 10: Remaining Gaps

### Gap 1: Unified GameState Schema
Currently 4 separate Pydantic schemas. Need one `GameState` that all agents incrementally populate.

### Gap 2: Frontend API Contract
Frontend expects `/api/status/{id}` to return a complete blueprint. Need to either: (a) keep blueprint format but build incrementally, or (b) change frontend to consume new format.

### Gap 3: json-rules-engine Integration
interaction_designer outputs prose. Need rule templates per mechanic + validation + frontend integration.

### Gap 4: compare_contrast Dual Image Pipeline
Asset generator needs `search_paired_images` tool. Frontend needs `compareConfig.diagramA/B`.

### Gap 5: Hierarchical Refactor
Extract HierarchyController into HierarchicalWrapper HOC. Remove from InteractionMode type.

### Gap 6: Backward Compatibility
Old pipeline presets use the old blueprint format. Need migration path.

### Gap 7: Mode Transition Rule Formalization
mode_transitions as `{from, to, trigger}` get LOST in blueprint assembly. Trigger conditions need formalization.

### Gap 8: Non-Label Mechanic Entity Model
Need independent entity types: `SequenceItem`, `SortingCategory`, `MemoryPair`, `BranchingNode` — not derived from zone_labels.

---

## Roadmap

### Phase A: Immediate Fixes (No Architecture Change)
1. Mechanic contract registry (`mechanic_contracts.py`)
2. Agent prompt hydration using contracts
3. Fix blueprint_assembler to pass ALL interaction_designer fields
4. Remove label bias from DK retriever, check_capabilities, generate_mechanic_content
5. Remove 33+ drag_drop bias instances
6. Paired image tool for compare_contrast
7. Contract-based output validation

### Phase B: Incremental State Building
1. Define unified GameState Pydantic model
2. Each agent writes to GameState directly (no blueprint assembler)
3. Contract-based validation at each agent checkpoint
4. Frontend consumes GameState format

### Phase C: Declarative Game Logic
1. Define rule templates per mechanic (json-rules-engine format)
2. interaction_designer outputs formal rules instead of prose
3. Frontend integrates json-rules-engine for game logic evaluation
4. MechanicRouter keeps rendering, rules handle logic

### Phase D: Hierarchical as Mode
1. Extract HierarchicalWrapper HOC from HierarchyController
2. Remove from InteractionMode union
3. Apply as composable wrapper to any zone-based mechanic
4. Backend outputs as property flag
