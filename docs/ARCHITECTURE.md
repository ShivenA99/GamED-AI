# GamED.AI Architecture

## Design Principles

1. **Pedagogical primacy** — Every game is bound to a Bloom's level before generation; mechanic selection follows learning objectives.
2. **Deterministic validation** — Every generative step is gated by a deterministic validator; LLM outputs are proposals subject to structural verification.
3. **Structure over retry** — Typed schemas and phase boundaries prevent errors rather than catching them downstream.
4. **Modularity** — New templates are registered via contract definition without modifying orchestration.

---

## Architectural Evolution

The current DAG architecture supersedes two prior designs:

**Sequential Pipeline** — A linear chain of agents where each stage passes output directly to the next without intermediate validation. The absence of Quality Gates allows structural errors to propagate silently across stages, compounding into invalid blueprints. Achieves 56.7% VPR at ~45,200 tokens/game.

**ReAct Agent** — A single ReAct agent with self-correction loops handles planning, generation, and validation within one cognitive loop. While self-correction improves over the Sequential Pipeline, it produces token inflation driven by exemplar-query similarity rather than genuine error recovery, and conflates generation with validation in the same reasoning trace. Achieves 72.5% VPR at ~73,500 tokens/game.

**Hierarchical DAG (current)** — Separates planning, generation, and validation into six deterministic phases, each bounded by a Quality Gate. Phase boundaries eliminate self-correction loops that inflate tokens and accumulate errors. Achieves 90.0% VPR at ~19,900 tokens/game ($0.48/game).

| Architecture | VPR | Tokens/Game |
|-------------|-----|-------------|
| Sequential Pipeline | 56.7% | ~45,200 |
| ReAct Agent | 72.5% | ~73,500 |
| **Hierarchical DAG** | **90.0%** | **~19,900** |

Architecture explains 87% of token consumption variance (η² = 0.87, F(2, 597) = 1,996, p < 0.001). The 73% token reduction from ReAct to DAG is structural: phase boundaries eliminate self-correction loops that inflate tokens and accumulate errors. The VPR gain of 17.5 percentage points over ReAct is confirmed significant (χ²(2, N=600) = 57.0, p < 0.001, Cramér's V = 0.31).

---

## DAG Pipeline Architecture

The system is a hierarchical DAG in LangGraph with six phases, each an independent sub-graph with typed I/O and a Quality Gate at its boundary. No agent in phase N receives input from phase N+1; no gate can be bypassed; invalid states cannot propagate.

```
Input Question
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 0: Context Gathering                                 │
│  ┌──────────────┐  ┌──────────────────────────┐             │
│  │Input Analyzer │  │Domain Knowledge Retriever│  (parallel) │
│  └──────┬───────┘  └────────────┬─────────────┘             │
│         └──────────┬────────────┘                           │
│                    ▼                                        │
│              Phase 0 Merge                                  │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Concept Design                                    │
│  ┌───────────────────────┐    ┌──────────────────┐          │
│  │Game Concept Designer  │───▶│ QG1: Concept     │          │
│  │(ReAct, Bloom's table) │◀───│ Validator        │ retry ≤2 │
│  └───────────────────────┘    └──────────────────┘          │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Game Plan (deterministic, no LLM)                 │
│  ┌──────────────────┐    ┌──────────────────────┐           │
│  │Game Plan Builder  │───▶│ QG2: Plan Validator  │           │
│  │(score contracts)  │◀───│                      │ retry ≤2  │
│  └──────────────────┘    └──────────────────────┘           │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Scene Content (parallel Send)                     │
│  ┌────────────┐  ┌────────────────┐  ┌────────────────────┐ │
│  │Content     │  │Scene Content   │  │ QG3: Content       │ │
│  │Dispatch    │─▶│Generator ×N    │─▶│ Validator (FOL)    │ │
│  │(router)    │  │(parallel LLM)  │  │ re-Send failed ≤2  │ │
│  └────────────┘  └────────────────┘  └────────────────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: Assets (parallel Send)                            │
│  ┌────────────┐  ┌────────────────┐                         │
│  │Asset       │  │Asset Worker ×M │                         │
│  │Dispatch    │─▶│(search/gen)    │  re-Send failed ≤1      │
│  └────────────┘  └────────────────┘                         │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 5: Assembly (deterministic, no LLM)                  │
│  ┌────────────────────┐    ┌──────────────────────┐         │
│  │Blueprint Assembler  │───▶│ QG4: Blueprint      │         │
│  │                     │    │ Validator            │         │
│  └────────────────────┘    └──────────────────────┘         │
└────────────────────┬────────────────────────────────────────┘
                     ▼
            Verified JSON Blueprint
```

---

## Phase Details

### Phase 0: Context Gathering

Two parallel LLM nodes:
- **Input Analyzer** — Parses subject domain, target audience, and difficulty level from the natural language question.
- **Domain Knowledge Retriever** — Grounds generation in curated sources (textbooks, curriculum standards, domain ontologies).

Outputs are merged before Phase 1, ensuring concept design operates on verified domain context rather than open-ended generation.

### Phase 1: Concept Design

Template selection is a **constrained inference**: the **Game Concept Designer** (ReAct agent) resolves input against a Bloom's-to-mechanic constraint table encoding valid competency evidence. The result is a **Game Blueprint** — a validated Pydantic document specifying learning objective, Bloom's level, template family, and mechanic contract — produced before content generation begins and certified by QG1. Each contract defines the interaction primitive, content types, valid Bloom's range, and completion conditions.

**QG1** validates: scenes ≤ 6, all game types supported, required fields present. Retry ≤ 2.

### Phase 2: Game Plan (Deterministic)

The **Game Plan Builder** assigns scene IDs, computes scores from per-game-type Score Contracts, determines asset needs, and builds the transition graph. No LLM inference.

**QG2** validates the full Game Plan against Score Contracts per game type: unique scene IDs, valid transitions, score totals match. Retry ≤ 2.

### Phase 3: Scene Content (Parallel)

**Content Dispatch** creates N `Send()` calls, one per scene. **Scene Content Generators** (LLM, parallel) produce game-type-specific content including interaction specifications (drag targets, click regions, sequence orders), instructional text (directions, hints, per-element feedback), and visual asset specifications. **Content Merge** deduplicates by scene_id.

**QG3** applies FOL-based Bloom's alignment predicates:
- `bloom(g) = bloom(b)` — generated Bloom's level matches blueprint
- `op_count(g) ≥ τ_contract` — sufficient interaction operations for the mechanic contract
- `feedback ⊨ Bloom's` — per-element feedback entails the target Bloom's level

All validation is deterministic with no LLM inference, ensuring constant cost and formal verifiability. Failed scenes trigger a bounded re-Send (max 2).

### Phase 4: Assets (Parallel)

**Asset Dispatch** filters scenes needing visual assets. **Asset Workers** (parallel) produce visual assets (SVG diagrams or text-synthesised visuals). Failed assets trigger re-Send (max 1).

### Phase 5: Assembly (Deterministic)

The **Blueprint Assembler** instantiates the selected template as a React component and injects validated content — the same orchestration layer produces all 15 mechanics through component swapping, not code regeneration. **QG4** performs final blueprint validation with `is_degraded` flag tracking. No LLM inference. Inter-agent communication achieves 98.3% Pydantic schema compliance.

Output: Verified JSON Blueprint (`generation_complete = true`).

---

## Quality Gates

| Gate | Phase Boundary | Validation Type | Key Checks |
|------|---------------|-----------------|------------|
| QG1 | Concept → Plan | Deterministic | Scene count, game type support, required fields |
| QG2 | Plan → Content | Deterministic | Unique scene IDs, valid transitions, Score Contract totals |
| QG3 | Content → Assets | FOL predicates | Bloom's alignment, operation counts, feedback entailment |
| QG4 | Assembly → Output | Deterministic | Schema compliance, is_degraded flag, template completeness |

All Quality Gates execute without LLM inference — constant cost and formal verifiability.

---

## Game Template Architecture

Two template families with 15 interaction mechanics:

### Interactive Diagram Games (10 mechanics)
Operate on spatial and relational content targeting visual and conceptual reasoning.

| Mechanic | Bloom's Level | Description |
|----------|--------------|-------------|
| Drag & Drop | Understand | Place labels onto diagram zones |
| Click to Identify | Remember | Click correct elements when described |
| Trace Path | Apply | Draw paths connecting waypoints in sequence |
| Description Matching | Understand | Match descriptions to diagram elements |
| Sequencing | Apply | Order items in correct sequence |
| Sorting | Analyze | Categorize items into groups |
| Memory Match | Remember | Match pairs by flipping cards |
| Branching Scenario | Evaluate | Make decisions at branch points |
| Compare/Contrast | Evaluate | Categorize attributes across subjects |
| Hierarchical | Analyze | Navigate multi-level taxonomies |

### Interactive Algorithm Games (5 mechanics)
Operate on procedural content targeting applying, analyzing, and creating objectives, grounded in algorithm visualization research and debugging-first pedagogy.

| Mechanic | Bloom's Level | Description |
|----------|--------------|-------------|
| State Tracer | Apply | Predict data structure state after each algorithm step |
| Bug Hunter | Analyze | Identify bugs in algorithm implementations |
| Algorithm Builder | Create | Construct algorithms from code blocks |
| Complexity Analyzer | Analyze | Determine time/space complexity of algorithms |
| Constraint Puzzle | Create | Solve optimization problems under constraints |

---

## Scene and Mechanic Composition

Templates span three structural configurations resolved automatically from Bloom's level and content complexity:

- **Single-scene, single-mechanic** — One interaction type, one content context (~35% of library)
- **Single-scene, multi-mechanic** — 2–3 interaction types within one content frame, validated through a state machine ensuring compatible I/O schemas (~40%)
- **Multi-scene, multi-mechanic** — 2–4 causally connected scenes with monotonically increasing Bloom's levels, bounded by cognitive load constraints (≤4 scenes, ≤3 mechanics/scene) (~25%)

---

## Modular Game Engine

The frontend implements a plugin architecture: each of the 15 mechanics is a self-contained React component registered by contract type, enabling extension through registration without modifying orchestration layers.

```
Blueprint JSON
     ↓
Template Router
  ├── Interactive Diagram (10 mechanics)
  └── Interactive Algorithm (5 mechanics)
     ↓
Mechanic Registry
     ↓
Component Dispatch → Self-contained React component
     ↓
State Management
  ├── Diagram Games: Zustand store (multi-mechanic coordination)
  └── Algorithm Games: Localised reducer hooks (step-through)
     ↓
Interaction Primitives
  ├── dnd-kit (drag, collision detection, keyboard/touch)
  ├── Framer Motion (animations)
  └── SVG Canvas (polygons, paths, zones)
```

Both template families share interaction primitives built on dnd-kit with custom collision detection and keyboard/touch support.

---

## Pipeline Observability

The system includes a real-time observability dashboard with three view modes:
- **Timeline** — Sequential execution trace
- **DAG Graph** — ReactFlow with execution-state highlighting
- **Cluster View** — Grouped by phase

Per-agent token and cost analytics show stage-level consumption with USD breakdown. A ReAct trace viewer displays the Thought → Action → Observation chain for tool-calling agents, and a stage inspector exposes inputs, outputs, and tool call history at every phase.

---

## Model Configuration

The orchestration layer is model-agnostic. A declarative preset system enables per-agent model selection across closed-source APIs (GPT-4, Gemini) and open-source models (Llama 3, Mistral, Qwen) without pipeline modification.

Default evaluation configuration: GPT-4-turbo-2024-04-09 (temp 0.3, seed 42) for planning/validation; gemini-1.5-pro-001 (temp 0.4) for asset generation. All runs logged via LangSmith with per-call granularity.
