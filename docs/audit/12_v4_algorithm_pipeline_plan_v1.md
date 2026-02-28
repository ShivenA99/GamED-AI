# V4 Algorithm Games Pipeline + Learn/Test Mode — Implementation Plan

## Context

We have a working V4 pipeline for **Interactive Diagram** games (zones, labels, diagrams). The frontend for **Algorithm Games** (6 types, 122 files) is COMPLETE but has ZERO backend support — no agents, no schemas, no pipeline. We need:

1. **Job 1**: V4 pipeline for algorithm games (E2E generation)
2. **Job 2**: Learn/Test mode for every mechanic in both templates
3. **Job 3**: Frontend fixes (routing, mode switching)

---

## Architecture Decision: SEPARATE Graph

Create `create_v4_algorithm_graph()` in `backend/app/v4_algorithm/`, activated via `pipeline_preset="v4_algorithm"`.

**Why separate**: The existing V4 graph is deeply tied to diagram concepts (zones, labels, images, asset workers). Algorithm games need CODE, execution traces, data structures, bugs, puzzles — none of which need image generation. Sharing a graph would force every agent to branch on template type (violating CLAUDE.md: "Never hardcode mechanic-specific logic"). We follow the SAME V4 patterns (parallel Send, Pydantic schemas, deterministic validators) with different agents.

---

## Pipeline Architecture

```
V4 Algorithm Pipeline (preset = "v4_algorithm")

Phase 0: START ──┬── input_analyzer (REUSE) ──┬── algo_phase0_merge
                 └── algo_dk_retriever ────────┘
                              │
Phase 1: algo_game_concept_designer → algo_concept_validator ──[retry]──┐
                 ↑                                                      │
                 └──────────────────────────────────────────────────────┘
                                                          "pass" ↓
Phase 2: algo_graph_builder → algo_plan_validator ──[retry]──┐
                 ↑                                           │
                 └───────────────────────────────────────────┘
                                                "pass" ↓
Phase 3: ──[content_dispatch_router]──
         ↙  algo_content_generator (parallel Send per game_type)  ↘
       algo_content_generator(s) → algo_content_merge
                              │
Phase 4: algo_blueprint_assembler → END
```

**Key differences from ID pipeline**:
- No asset_worker (no diagram images)
- No interaction_designer (scoring/feedback embedded in content generation)
- No scene_designer phase (algorithm scenes are simpler — no visual specs needed)
- Content generators dispatched per game_type (state_tracer, bug_hunter, etc.)

### Algorithm Game Types → V4 "Mechanic" Mapping

| Game Type | Mechanic ID | What It Generates |
|---|---|---|
| state_tracer | `state_tracer` | Execution traces with steps, predictions, data structure states |
| bug_hunter | `bug_hunter` | Buggy code, bugs, test cases, fix options |
| algorithm_builder | `algorithm_builder` | Parsons blocks (correct + distractors) with indentation |
| complexity_analyzer | `complexity_analyzer` | Code snippets with Big-O challenges |
| constraint_puzzle | `constraint_puzzle` | Board config, constraints, optimal solution |

ALL are content-only (no zones, no diagrams, no asset generation).

---

## Phase-by-Phase Agent Design

### Phase 0: Context Gathering
- **input_analyzer** (REUSE existing V4 agent as-is)
- **algo_dk_retriever** (NEW) — algorithm-specific knowledge:
  - `algorithm_name`, `pseudocode`, `time_complexity`, `space_complexity`
  - `common_bugs[]`, `common_misconceptions[]`, `data_structures_used[]`
  - `example_inputs[]`, `related_algorithms[]`
  - Uses web search: `"{algorithm} pseudocode complexity common bugs"`

### Phase 1: Game Concept Design
- **algo_game_concept_designer** (NEW, LLM) — designs multi-scene game:
  - Input: question_text, pedagogical_context, domain_knowledge
  - Output: `AlgorithmGameConcept` (title, algorithm_name, scenes[{game_types, learning_goal}])
  - Prompt includes capability matrix of 5 game types with Bloom's alignment guidance
- **algo_concept_validator** (deterministic) — validates structure, game type validity

### Phase 2: Graph Builder + Validator
- **algo_graph_builder** (deterministic) — assigns IDs, computes scores, builds connections
- **algo_plan_validator** (deterministic) — validates plan structure, score totals

### Phase 3: Content Generation (CRITICAL — parallel Send)
- **algo_content_generator** (NEW, LLM) — dispatched per game_type per scene
  - 5 different prompt templates (one per game type)
  - state_tracer: generates execution steps with DataStructure snapshots + Prediction objects
  - bug_hunter: generates buggy code rounds with bugs, test cases, fix options
  - algorithm_builder: generates Parsons blocks with correct order + distractors
  - complexity_analyzer: generates code snippets with O-notation challenges
  - constraint_puzzle: generates board config + constraints + optimal solution
  - All use gemini-2.5-pro (high complexity content)

### Phase 4: Blueprint Assembly (deterministic)
- **algo_blueprint_assembler** — maps game_plan + game_contents → AlgorithmGameBlueprint
  - Sets `templateType: "ALGORITHM_GAME"`, `algorithmGameType` sub-field
  - For single-game: populates matching blueprint field (stateTracerBlueprint, etc.)
  - For multi-scene: builds `scenes[]` array
  - Sets `generation_complete: True`

---

## Learn/Test Mode Design (Job 2)

### Design: Generate Once, Switch at Runtime
The backend generates ALL data needed for BOTH modes in a single pipeline run. The blueprint contains full hints, scaffolding data, strict scoring config, AND generous scoring config. The frontend reads `gameplay_mode` and dynamically shows/hides elements.

### Blueprint Fields
```python
# Per-mechanic/game-type scoring configs for both modes
learn_config: LearnModeConfig  # hints auto-reveal, partial credit, scaffolding
test_config: TestModeConfig    # hint penalties, strict scoring, no scaffolding
```
Added to BOTH `AlgorithmGameBlueprint` and `InteractiveDiagramBlueprint`. Frontend starts in `learn` mode by default with a toggle to switch.

### Per-Mode Behavior Matrix

| Aspect | Learn Mode | Test Mode |
|---|---|---|
| **Hints** | Auto-reveal tier 1 after delay; all 3 tiers free | 3-tier with score penalties per tier |
| **Scoring** | Generous partial credit (0.5x) | Strict; no partial credit by default |
| **Feedback** | Immediate; shows correct answer + explanation | Shows "incorrect" only; explanations after completion |
| **Time** | No time pressure | Optional timer per challenge |
| **Misconceptions** | Shown preemptively | Shown only after errors |
| **Scaffolding** | More hints, guided steps, pre-filled examples | No scaffolding |

### Per Game Type Specifics

| Game Type | Learn Mode Twist | Test Mode Twist |
|---|---|---|
| state_tracer | Auto-play first 2 steps with predictions pre-filled | Predict from step 1, no pre-fills |
| bug_hunter | Highlight suspicious region in code | No region hints |
| algorithm_builder | Show 1 correct block position as anchor | Full scramble, no anchors |
| complexity_analyzer | Show growth rate table by default | Growth data hidden until hint |
| constraint_puzzle | Show constraint violations in real-time | Check only on submit |
| drag_drop | Label descriptions visible; gentle nudges | No descriptions; strict placement |
| trace_path | Show next waypoint hint | No path hints |
| sequencing | Show 1-2 correct positions | Full scramble |

### Data Flow
1. Backend generates blueprint with ALL data for both modes (hints, scaffolding, strict scoring, etc.)
2. Blueprint includes `learn_config` and `test_config` at root
3. Frontend defaults to `learn` mode with a toggle switch
4. User can switch modes at runtime — no re-generation needed
5. Frontend components read current mode and show/hide elements accordingly

---

## Backend Schema Summary

### New Package Structure
```
backend/app/v4_algorithm/
├── __init__.py
├── state.py                          # V4AlgorithmState TypedDict
├── graph.py                          # create_v4_algorithm_graph()
├── routers.py                        # Concept/content dispatch routers
├── merge_nodes.py                    # Phase 0 merge, content merge
├── contracts.py                      # ALGORITHM_GAME_TYPES, model routing
├── graph_builder.py                  # Deterministic plan builder
├── schemas/
│   ├── __init__.py
│   ├── algorithm_game_types.py       # Literal types, enums
│   ├── game_concept.py               # AlgorithmGameConcept
│   ├── game_plan.py                  # AlgorithmGamePlan, MechanicPlan
│   ├── algorithm_content.py          # Per-game-type content models (5)
│   └── algorithm_blueprint.py        # AlgorithmGameBlueprint
├── agents/
│   ├── __init__.py
│   ├── dk_retriever.py               # Algorithm-aware DK
│   ├── game_concept_designer.py      # LLM concept design
│   ├── content_generator.py          # Per-game-type content (parallel Send)
│   └── assembler_node.py             # Blueprint assembly
├── prompts/
│   ├── __init__.py
│   ├── game_concept_designer.py      # Concept design prompt
│   └── content_generator.py          # 5 prompt templates
└── validators/
    ├── __init__.py
    ├── concept_validator.py
    ├── plan_validator.py
    └── blueprint_validator.py
```

### Key Schemas (must match frontend types.ts exactly)

**AlgorithmGameBlueprint** (root):
- `templateType: "ALGORITHM_GAME"`
- `algorithmGameType: "state_tracer" | "bug_hunter" | "algorithm_builder" | "complexity_analyzer" | "constraint_puzzle"`
- `gameplay_mode: "learn" | "test"`
- `title, subject, difficulty, narrativeIntro, totalMaxScore`
- `stateTracerBlueprint?`, `bugHunterBlueprint?`, `algorithmBuilderBlueprint?`, `complexityAnalyzerBlueprint?`, `constraintPuzzleBlueprint?`
- `scenes?` (for multi-scene)

---

## Files to Modify (Existing)

| File | Change |
|---|---|
| `backend/app/agents/graph.py` | Add `v4_algorithm` preset in `get_compiled_graph()` |
| `backend/app/routes/generate.py` | Add `"v4_algorithm"` to preset routing |
| `backend/app/agents/instrumentation.py` | Register v4_algorithm agent I/O keys |
| `frontend/src/app/game/[id]/page.tsx` | Fix algorithm game sub-type routing |
| `frontend/src/components/templates/AlgorithmGame/StateTracerGame.tsx` | Add `mode` prop |
| `frontend/src/components/templates/AlgorithmGame/BugHunterGame.tsx` | Add `mode` prop |
| `frontend/src/components/templates/AlgorithmGame/AlgorithmBuilderGame.tsx` | Add `mode` prop |
| `frontend/src/components/templates/AlgorithmGame/ComplexityAnalyzerGame.tsx` | Add `mode` prop |
| `frontend/src/components/templates/AlgorithmGame/ConstraintPuzzleGame.tsx` | Add `mode` prop |
| `frontend/src/components/templates/AlgorithmGame/components/HintSystem.tsx` | Mode-aware hints |
| `backend/app/v4/state.py` | Add `gameplay_mode` field |
| `backend/app/v4/helpers/blueprint_assembler.py` | Pass through `gameplay_mode` |

---

## Implementation Order

### Phase A: Foundation (Schema + State + Graph Shell)
1. Create `v4_algorithm/` directory structure
2. Define all Pydantic schemas for ALL 5 game types (matching frontend types.ts exactly)
3. Implement `V4AlgorithmState`
4. Wire empty graph shell in `create_v4_algorithm_graph()`
5. Register `v4_algorithm` preset in `graph.py` and `generate.py`

### Phase B: Phase 0 + Phase 1 (DK + Concept)
6. Implement `algo_dk_retriever` (algorithm-aware DK)
7. Implement `algo_game_concept_designer` + prompt (multi-scene aware from day 1)
8. Implement `algo_concept_validator`
9. Wire Phase 0 + 1 with retry loop

### Phase C: Phase 2 + 3 (Graph Builder + Content — ALL 5 types)
10. Implement `algo_graph_builder` (deterministic, multi-scene graph)
11. Implement `algo_plan_validator`
12. Implement `algo_content_generator` with ALL 5 prompt templates:
    - state_tracer, bug_hunter, algorithm_builder, complexity_analyzer, constraint_puzzle
13. Wire Phase 2 + 3 with parallel Send (one worker per game_type per scene)

### Phase D: Assembly + Multi-Scene + E2E (Phase 4)
14. Implement `algo_blueprint_assembler` (single + multi-scene output)
15. Wire Phase 4
16. Implement `AlgorithmMultiSceneGame.tsx` frontend orchestrator
17. E2E test: question → blueprint → frontend renders (single + multi-scene)

### Phase E: Frontend Routing + Learn/Test Mode
18. Fix `game/[id]/page.tsx` routing for all algorithm game types
19. Add `learn_config` / `test_config` to blueprint schemas and assembler
20. Add `mode` prop + toggle to all 5 algorithm game components
21. Add `mode` prop + toggle to InteractiveDiagramGame + all 10 mechanics
22. Adjust HintSystem, scoring, feedback per mode

### Phase F: Instrumentation + Polish
23. Add instrumentation for PipelineView observability
24. Full regression testing across all 5 game types × 2 modes
25. Multi-scene E2E: StateTracer → BugHunter → AlgorithmBuilder for same algorithm

---

## Testing Strategy

- **Schema tests**: All Pydantic schemas parse/serialize correctly, match frontend types
- **Graph builder tests**: Deterministic builder produces valid plans from concept
- **Validator tests**: Concept, plan, blueprint validators catch all edge cases
- **E2E tests per game type**:
  - "Explain binary search" → StateTracer
  - "Debug this bubble sort" → BugHunter
  - "Build a BFS algorithm" → AlgorithmBuilder
  - "Analyze merge sort complexity" → ComplexityAnalyzer
  - "Solve 0/1 knapsack" → ConstraintPuzzle
- **Frontend**: Snapshot tests with `mode="learn"` and `mode="test"` per component
- **Schema compat**: Generate backend blueprint → parse through frontend types

---

## Critical Reference Files

| Purpose | File |
|---|---|
| V4 graph pattern to follow | `backend/app/v4/graph.py` |
| V4 state pattern to follow | `backend/app/v4/state.py` |
| Frontend types (MUST match) | `frontend/src/components/templates/AlgorithmGame/types.ts` |
| Content model dispatch pattern | `backend/app/v4/schemas/mechanic_content.py` |
| Template routing to modify | `frontend/src/app/game/[id]/page.tsx` |
| Preset registration | `backend/app/agents/graph.py:get_compiled_graph()` |
| Contracts pattern | `backend/app/v4/contracts.py` |
