# Hierarchical / Nested Mechanic Chaining in Educational Games

**Research Document for GamED.AI v2**
**Date:** 2026-02-11
**Status:** Research & Architecture Proposal

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State: Sequential Chaining](#2-current-state-sequential-chaining)
3. [Chaining Pattern Taxonomy](#3-chaining-pattern-taxonomy)
   - 3.1 Sequential
   - 3.2 Parallel Unlock
   - 3.3 Prerequisite Tree (AND/OR Gates)
   - 3.4 Nested / Hierarchical
   - 3.5 Conditional Branching
   - 3.6 Recursive Nesting
   - 3.7 Hub-and-Spoke
4. [Theoretical Foundations](#4-theoretical-foundations)
5. [State Management for Nested Mechanics](#5-state-management-for-nested-mechanics)
6. [Data Structures for Mechanic DAGs](#6-data-structures-for-mechanic-dags)
7. [Frontend Architecture for Nested Games](#7-frontend-architecture-for-nested-games)
8. [LangGraph / Pipeline Implications](#8-langgraph--pipeline-implications)
9. [Real-World Examples and Precedents](#9-real-world-examples-and-precedents)
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [References](#11-references)

---

## 1. Executive Summary

Our Interactive Diagram Game platform currently supports **sequential chaining** of mechanics: complete mechanic A, then unlock mechanic B, then mechanic C. This is modeled as a flat `ModeTransition[]` list with `from_mode` and `to_mode` pairs, and `MechanicTransitionSpec` objects in the V3 schemas.

This document researches and proposes **hierarchical/nested chaining patterns** that go beyond simple sequential ordering. These patterns enable richer educational experiences where:

- A parent mechanic (e.g., drag_drop on a whole-body diagram) spawns child mechanics (e.g., trace_path within each organ)
- Multiple mechanics can unlock in parallel, with AND/OR gates controlling progression
- Performance on one mechanic dynamically routes to different follow-up mechanics
- Mechanics can recursively contain other mechanics (e.g., a branching scenario where each decision node is itself a mini-game)
- A central hub diagram allows entry into sub-games per zone

**Key finding:** The existing `ModeTransition[]` model is a **linear linked list** masquerading as a graph. Upgrading to a true DAG (Directed Acyclic Graph) with typed nodes and edges is the fundamental architectural change needed to support all seven chaining patterns identified in this research.

---

## 2. Current State: Sequential Chaining

### Current Data Model

```
// Backend: game_plan_schemas.py
ModeTransition {
    from_mode: MechanicType
    to_mode: MechanicType
    trigger: TransitionTrigger  // all_zones_labeled, score_threshold, etc.
    trigger_value?: number
    animation: string
}

// Frontend: types.ts
ModeTransition {
    from: InteractionMode
    to: InteractionMode
    trigger: ModeTransitionTrigger
    triggerValue?: number | string[]
    animation?: 'fade' | 'slide' | 'zoom' | 'none'
    message?: string
}
```

### Current Transition Flow

```
  drag_drop ──(all_zones_labeled)──> trace_path ──(path_complete)──> sequencing
      |                                    |                              |
   [active]                            [locked]                       [locked]
```

### Limitations

1. **Strictly linear:** A -> B -> C. No branching, no parallelism.
2. **No parent-child:** Cannot express "complete drag_drop at organ level, then zoom into each organ for trace_path."
3. **No conditional routing:** Cannot express "score > 80% -> advanced mechanic, score < 50% -> remediation."
4. **No containment:** Cannot express "this branching_scenario node IS a drag_drop mini-game."
5. **No hub model:** Cannot express "central diagram, click any organ to enter its sub-game."
6. **Flat score model:** Score is a single number; no aggregation from child mechanics to parent.

---

## 3. Chaining Pattern Taxonomy

### 3.1 Sequential (Current)

**Pattern:** A -> B -> C (linear chain)

```
  +-----------+     +-----------+     +-----------+
  | drag_drop | --> | trace_path| --> | sequencing|
  +-----------+     +-----------+     +-----------+
    trigger:          trigger:          trigger:
    all_zones         path_complete     sequence
    _labeled                            _complete
```

**When to use:**
- Simple progressive assessments where each phase builds on the last
- Content with a natural linear order (e.g., "identify parts" -> "trace flow" -> "order steps")
- Bloom's taxonomy progression: remember (label) -> understand (trace) -> apply (sequence)

**Data structure needed:**

```typescript
// Current model is sufficient
interface SequentialChain {
  mechanics: MechanicNode[];  // ordered list
  transitions: ModeTransition[];  // from[i] -> to[i+1]
}
```

**Frontend rendering:** Current MechanicRouter + mode transition animation system handles this.

**Complexity vs value:** Low complexity, moderate value. Already implemented.

---

### 3.2 Parallel Unlock

**Pattern:** Complete A OR B (independently) to unlock C.

```
  +-----------+
  | drag_drop |---+
  +-----------+   |   (OR gate)    +-----------+
                  +----[  OR  ]--->| sequencing|
  +-----------+   |                +-----------+
  | trace_path|---+
  +-----------+
```

**Alternate (AND gate):** Complete BOTH A AND B to unlock C.

```
  +-----------+
  | drag_drop |---+
  +-----------+   |   (AND gate)   +-----------+
                  +----[ AND  ]--->| sequencing|
  +-----------+   |                +-----------+
  | trace_path|---+
  +-----------+
```

**When to use:**
- Content with independent knowledge domains that converge (e.g., "label the arteries" and "label the veins" -> "trace full circulation")
- Differentiated learning paths where students can choose which to tackle first
- Assessing breadth: student must demonstrate competence in multiple areas before synthesis
- OR gate: flexible pacing, student choice; AND gate: comprehensive mastery required

**Educational scenario:** "Label the parts of the plant cell AND the animal cell (independently), then compare/contrast them."

**Data structure:**

```typescript
interface ParallelUnlock {
  gate_type: 'AND' | 'OR';
  gate_id: string;
  prerequisites: string[];  // mechanic node IDs that feed into this gate
  unlocks: string;  // mechanic node ID unlocked when gate fires
  // For OR: fires when ANY prerequisite completes
  // For AND: fires when ALL prerequisites complete
  min_required?: number;  // For "N of M" gates (e.g., complete 2 of 3)
}
```

**Frontend rendering:**
- Show all parallel mechanics simultaneously (tabbed or split-screen)
- Gate visualization: a lock icon or progress bar showing "1/2 complete" for AND gates
- Optional: let student choose which to tackle first via a selection panel

**Complexity vs value:** Medium complexity, high value. Enables non-linear learning paths.

---

### 3.3 Prerequisite Tree (AND/OR Gates)

**Pattern:** General DAG with mixed AND/OR gates controlling progression.

```
  +-----------+     +-----------+
  | drag_drop |     |click_ident|
  +-----+-----+     +-----+-----+
        |                  |
        v                  v
  +-----------+     +-----------+
  | trace_path|     | sequencing|
  +-----+-----+     +-----+-----+
        |                  |
        +----[ AND ]-------+
                |
                v
        +-----------+
        | branching |
        | _scenario |
        +-----------+
```

**When to use:**
- Complex topics with genuine prerequisite dependencies (e.g., must understand structure AND function before analyzing scenarios)
- Skill tree-style progression: foundational skills branch into intermediate skills, which converge at advanced skills
- Multi-chapter assessment: each chapter has sub-tasks, chapters combine for final assessment

**Educational scenario:** "Label the heart chambers (drag_drop), identify each chamber's function (click_to_identify), trace blood flow through the heart (trace_path), and put the cardiac cycle steps in order (sequencing). Only after tracing AND sequencing are both complete can you attempt the clinical diagnosis branching scenario."

**Data structure:**

```typescript
type GateType = 'AND' | 'OR' | 'N_OF_M' | 'SCORE_THRESHOLD';

interface GateNode {
  node_type: 'gate';
  gate_id: string;
  gate_type: GateType;
  inputs: string[];  // IDs of prerequisite mechanic or gate nodes
  min_required?: number;  // For N_OF_M: how many inputs must complete
  score_threshold?: number;  // For SCORE_THRESHOLD: minimum score required
}

interface MechanicNode {
  node_type: 'mechanic';
  mechanic_id: string;
  mechanic_type: InteractionMode;
  config: Record<string, unknown>;
  zone_ids?: string[];
  label_ids?: string[];
}

type DAGNode = MechanicNode | GateNode;

interface DAGEdge {
  from: string;  // node ID
  to: string;    // node ID
  edge_type: 'unlock' | 'prerequisite' | 'conditional';
}

interface MechanicDAG {
  nodes: DAGNode[];
  edges: DAGEdge[];
  root_node_ids: string[];  // Nodes with no prerequisites (starting points)
}
```

**Frontend rendering:**
- Skill tree visualization: nodes connected by lines, completed nodes lit up, locked nodes grayed out
- Mini-map in corner showing overall DAG and current position
- Gate nodes rendered as diamond/hexagon shapes with progress indicators

**Complexity vs value:** High complexity, high value. The most flexible general model. Consider implementing this as the universal backend representation that all other patterns desugar into.

---

### 3.4 Nested / Hierarchical (Zone-Scoped Child Mechanics)

**Pattern:** Complete a parent mechanic on the whole diagram, then zoom into regions to perform child mechanics within each region.

```
  +=========================================+
  |  PARENT: drag_drop (whole diagram)      |
  |  "Label the major organs"               |
  |                                         |
  |  +--------+  +--------+  +--------+    |
  |  | Heart  |  | Lungs  |  | Liver  |    |
  |  +---+----+  +---+----+  +---+----+    |
  +======|============|============|========+
         |            |            |
         v            v            v
  +----------+  +----------+  +----------+
  | CHILD:   |  | CHILD:   |  | CHILD:   |
  | trace    |  | trace    |  | click    |
  | _path    |  | _path    |  | _identify|
  | (heart)  |  | (lungs)  |  | (liver)  |
  +----------+  +----------+  +----------+
```

**When to use:**
- Hierarchical content: whole system -> subsystems -> components
- Progressive depth: first understand the big picture, then dive into details
- Anatomy, geography, engineering diagrams, organizational charts, biological taxonomy
- Any content where zooming in reveals more detail to interact with

**Educational scenario:** "Label all organs on the human body diagram (drag_drop). Once the heart is correctly labeled, click it to zoom in and trace the blood flow path (trace_path). Once the lungs are labeled, zoom in to identify the alveoli (click_to_identify)."

**Data structure:**

```typescript
interface HierarchicalMechanic {
  // The parent mechanic operates on the full diagram
  parent: MechanicNode & {
    child_spawn_rules: ChildSpawnRule[];
  };
}

interface ChildSpawnRule {
  trigger_zone_id: string;  // Which zone in the parent triggers this child
  trigger_condition: 'zone_complete' | 'zone_clicked' | 'parent_all_complete';
  child_mechanic: MechanicNode & {
    // The child mechanic operates on a sub-region of the diagram
    viewport: {
      // Defines the sub-region to zoom into (percentage of parent)
      x: number;      // 0-100
      y: number;      // 0-100
      width: number;  // 0-100
      height: number; // 0-100
    };
    // Optional: separate image for the zoomed-in view
    child_diagram_url?: string;
    // Zones specific to this child mechanic
    child_zones: Zone[];
    child_labels: Label[];
  };
  zoom_animation: 'smooth_zoom' | 'slide_in' | 'fade_crossfade' | 'none';
  allow_return_to_parent: boolean;
}
```

**Frontend rendering approach:**
1. Render parent diagram with all parent zones
2. When a zone is completed (or clicked after parent completion), animate a zoom into that zone's bounding box
3. Swap the diagram image to the child's detailed image (or scale up the parent region)
4. Render child zones and labels within the zoomed viewport
5. Show breadcrumb: "Human Body > Heart > Blood Flow"
6. "Back" button or breadcrumb click returns to parent view with smooth zoom-out

**Key implementation details:**
- Use CSS `transform: scale()` + `transform-origin` for smooth zoom animation
- Child mechanic component is the same MechanicRouter, just with different props (zones, labels, config)
- Parent diagram stays in DOM but is hidden/scaled down; child overlays on top
- Score from child mechanics aggregates up to parent via callback

**Complexity vs value:** High complexity, very high value. This is the most educationally impactful pattern because it mirrors how learning actually works -- understanding the whole, then diving into parts. This should be the top priority for implementation.

---

### 3.5 Conditional Branching (Performance-Based Routing)

**Pattern:** Score on mechanic A determines which mechanic comes next.

```
                    +-----------+
                    | drag_drop |
                    +-----+-----+
                          |
                    [score check]
                    /     |      \
                   /      |       \
          score<50%  50-80%   score>80%
                 /        |         \
                v         v          v
        +-----------+ +-----------+ +-----------+
        | REMEDIATE | | STANDARD  | | ADVANCED  |
        | drag_drop | | trace     | | branching |
        | (simpler) | | _path    | | _scenario |
        +-----------+ +-----------+ +-----------+
```

**When to use:**
- Adaptive difficulty: struggling students get easier follow-up, strong students get harder challenges
- Formative assessment: use initial performance to diagnose and route appropriately
- Differentiated instruction: different learning paths based on demonstrated understanding
- Zone of Proximal Development (Vygotsky): keep the student in their optimal challenge zone

**Educational scenario:** "Label the cell organelles (drag_drop). If score > 80%, proceed to a branching scenario about cellular disease. If 50-80%, trace the protein synthesis pathway. If < 50%, redo labeling with hints enabled and fewer organelles."

**Data structure:**

```typescript
interface ConditionalBranch {
  node_type: 'branch';
  branch_id: string;
  source_mechanic_id: string;  // Which mechanic's result to evaluate
  condition_type: 'score_range' | 'specific_zones_correct' | 'time_taken' | 'attempts_count';
  branches: BranchPath[];
  default_branch: string;  // fallback mechanic ID if no condition matches
}

interface BranchPath {
  condition: {
    min?: number;  // inclusive
    max?: number;  // exclusive
    zones_required?: string[];
    operator?: 'gte' | 'lte' | 'eq' | 'between';
  };
  target_mechanic_id: string;
  message?: string;  // "Great job! Ready for the challenge?"
}
```

**Frontend rendering:**
- After mechanic A completes, show a brief transition screen with score + message
- Automatically route to the appropriate next mechanic
- Optionally show the student which path they took (for metacognition)
- Consider showing a simplified DAG mini-map so students see "you're on the advanced path"

**Complexity vs value:** Medium complexity, very high value. Adaptive difficulty is one of the most impactful features in educational technology. Research shows that students who played adaptively difficulty-adjusted games achieved significantly higher learning outcomes.

---

### 3.6 Recursive Nesting (Mechanics Containing Mechanics)

**Pattern:** A mechanic that CONTAINS other mechanics as part of its structure.

```
  +=============================================+
  |  branching_scenario                         |
  |                                             |
  |  "Patient presents with chest pain..."      |
  |                                             |
  |  Option A: "Check heart rate"               |
  |    +----> [EMBEDDED: memory_match           |
  |    |       "Match ECG patterns to           |
  |    |        conditions"]                    |
  |    |                                        |
  |  Option B: "Order blood test"               |
  |    +----> [EMBEDDED: sorting_categories     |
  |    |       "Sort blood markers into         |
  |    |        normal/abnormal"]               |
  |    |                                        |
  |  Option C: "Review imaging"                 |
  |    +----> [EMBEDDED: drag_drop              |
  |           "Label the X-ray findings"]       |
  +=============================================+
```

**When to use:**
- Complex problem-based learning where decision-making requires sub-skills
- Simulation-style games where each action triggers a mini-assessment
- Case studies where exploring each option requires domain-specific skills
- Advanced Bloom's taxonomy levels: analyze (branching) requires applying sub-skills (labeling, sorting, matching)

**Educational scenario:** "You are a doctor diagnosing a patient (branching_scenario). At each decision point, you must complete a mini-game to gather information. Check the heart? Play a memory match game with ECG patterns. Order blood work? Sort the lab values into normal/abnormal categories."

**Data structure:**

```typescript
interface RecursiveMechanicNode {
  node_type: 'mechanic';
  mechanic_id: string;
  mechanic_type: InteractionMode;
  config: Record<string, unknown>;

  // Recursive: embedded child mechanics within this mechanic's structure
  embedded_mechanics?: EmbeddedMechanic[];
}

interface EmbeddedMechanic {
  embed_id: string;
  // Where in the parent mechanic this is embedded
  embed_point: {
    type: 'decision_node' | 'zone_interaction' | 'sequence_step' | 'category_item';
    parent_element_id: string;  // e.g., decision node ID, zone ID, sequence step ID
  };
  // The child mechanic to render at this embed point
  child_mechanic: RecursiveMechanicNode;
  // How completion affects the parent
  completion_effect: {
    type: 'unlock_next' | 'provide_score' | 'reveal_info' | 'modify_parent_state';
    data?: Record<string, unknown>;
  };
  // Max nesting depth to prevent infinite recursion
  max_depth?: number;  // default: 3
}
```

**Frontend rendering:**
- Parent mechanic renders normally (e.g., branching scenario with decision nodes)
- When a decision option is selected that has an embedded mechanic, transition into the child mechanic view
- Child mechanic renders in a modal, slide-over panel, or inline expansion
- On child completion, return to parent with results injected
- Show nesting depth indicator: "Level 2 of 3"
- Enforce maximum recursion depth (recommend: 3 levels max)

**Complexity vs value:** Very high complexity, high value for specific use cases. This is the most architecturally challenging pattern. Recommend implementing only for `branching_scenario` as the parent mechanic initially, since it naturally has "decision points" that can host sub-games.

---

### 3.7 Hub-and-Spoke

**Pattern:** Central diagram serves as a hub; clicking zones enters sub-games that are self-contained.

```
                  +---------------------------+
                  |     CENTRAL HUB DIAGRAM   |
                  |                           |
                  |   [Heart]   [Lungs]       |
                  |      |         |          |
                  |   [Liver]  [Kidneys]      |
                  |      |         |          |
                  +------|---------|----------+
                         |         |
              +----------+    +----+--------+
              |               |             |
              v               v             v
        +-----------+  +-----------+  +-----------+
        | Heart     |  | Lungs     |  | Kidneys   |
        | Sub-Game  |  | Sub-Game  |  | Sub-Game  |
        | (3 tasks) |  | (2 tasks) |  | (4 tasks) |
        +-----------+  +-----------+  +-----------+
              |               |             |
              v               v             v
        [return to hub with zone marked complete]
```

**When to use:**
- Exploration-based learning: student chooses which topic to explore first
- Content without strict ordering: each zone is an independent knowledge area
- Assessment covering multiple topics: student must complete all sub-games
- "Choose your own adventure" style learning where student agency is prioritized

**Educational scenario:** "Here is a diagram of the human body. Click any organ to enter its sub-game. Each organ has its own set of activities (labeling, tracing, or sequencing). Complete all organs to finish the assessment."

**Data structure:**

```typescript
interface HubAndSpoke {
  hub: {
    diagram: DiagramSpec;
    zones: HubZone[];
    completion_requirement: 'all' | 'any_n';
    min_required?: number;
  };
  spokes: SpokeGame[];
}

interface HubZone {
  zone_id: string;
  spoke_game_id: string;  // Links to the sub-game for this zone
  status: 'locked' | 'available' | 'in_progress' | 'completed';
  // Optional: prerequisites (other spoke games that must be done first)
  prerequisites?: string[];
  // Visual cues
  completion_indicator: 'checkmark' | 'star' | 'color_change' | 'glow';
}

interface SpokeGame {
  spoke_id: string;
  title: string;
  // A spoke game is itself a mechanic chain (can be sequential, parallel, etc.)
  mechanic_graph: MechanicDAG;
  // Separate diagram for the spoke (zoomed view of the hub zone)
  diagram?: DiagramSpec;
  max_score: number;
}
```

**Frontend rendering:**
- Hub diagram is always the "home" view with clickable zones
- Completed zones show visual indicator (checkmark overlay, color change, glow effect)
- Clicking an available zone triggers a zoom-in transition to the spoke game
- Spoke game runs as a self-contained game (could itself be sequential or nested)
- On spoke completion, zoom-out transition back to hub
- Hub shows overall progress: "3 of 5 organs explored"
- Optional: lock/unlock spoke zones based on prerequisites

**Complexity vs value:** Medium-high complexity, very high value. This is the most natural pattern for diagram-based educational games. It maps directly to how students explore visual content -- clicking on interesting parts to learn more. Metroidvania-style game design uses this exact pattern, and research indicates it provides strong sense of agency and motivation.

---

## 4. Theoretical Foundations

### 4.1 Bloom's Taxonomy Alignment

Each chaining pattern maps to different levels of Bloom's taxonomy:

| Bloom's Level | Mechanic Type | Chaining Pattern |
|---|---|---|
| Remember | drag_drop, memory_match | Sequential (start here) |
| Understand | click_to_identify, description_matching | Sequential (second stage) |
| Apply | trace_path, sequencing | Prerequisite tree |
| Analyze | sorting_categories, compare_contrast | Parallel unlock |
| Evaluate | branching_scenario | Conditional branching |
| Create | (open-ended tasks) | Hub-and-spoke, recursive |

**Key insight:** Hierarchical chaining naturally mirrors Bloom's taxonomy hierarchy. Lower-level mechanics should be prerequisites for higher-level ones. The DAG structure can encode this pedagogical progression explicitly.

### 4.2 Zone of Proximal Development (ZPD) and Scaffolding

Vygotsky's ZPD describes the gap between what a learner can do alone and what they can do with guidance. Hierarchical chaining enables **dynamic scaffolding**:

- **Conditional branching** keeps students in their ZPD by routing high-performers to harder mechanics and low-performers to supportive remediation
- **Nested mechanics** provide scaffolding: the parent mechanic (labeling) is within the student's capability, while child mechanics (tracing, branching) stretch into the ZPD
- **Hub-and-spoke** lets students self-regulate by choosing which areas to explore, naturally gravitating toward their ZPD

Research on adaptive difficulty in educational games has found significantly higher learning outcomes when the game adjusts challenge level based on ongoing performance assessment.

### 4.3 Progressive Disclosure

Progressive disclosure is a UX principle where complexity is revealed gradually as the user demonstrates readiness. In educational games:

- **Sequential chaining** is simple progressive disclosure: each mechanic reveals the next
- **Hierarchical nesting** is **depth-based progressive disclosure**: completing a surface-level task reveals deeper interactions
- **Prerequisite trees** are **mastery-based progressive disclosure**: demonstrating competence unlocks new areas

The Duolingo platform exemplifies progressive disclosure through its path-based system, where skills unlock based on demonstrated mastery of prerequisite skills.

### 4.4 Hierarchical Task Decomposition

Educational task decomposition research supports breaking complex learning objectives into sub-tasks with explicit dependency relationships. The mechanic DAG directly encodes this decomposition:

- Each node is a learning sub-task
- Each edge is a pedagogical dependency ("you need to understand X before attempting Y")
- Gate nodes encode assessment checkpoints ("demonstrate mastery of A and B before attempting C")

---

## 5. State Management for Nested Mechanics

### 5.1 Tree-Structured State with Zustand

The current Zustand store uses a flat state model. For hierarchical mechanics, we need tree-structured state:

```typescript
// Current: flat state
interface GameState {
  score: number;
  placedLabels: PlacedLabel[];
  multiModeState?: MultiModeState;
  // ...
}

// Proposed: hierarchical state
interface HierarchicalGameState {
  // The mechanic DAG definition (from blueprint)
  mechanicGraph: MechanicDAG;

  // State for each node in the DAG
  nodeStates: Record<string, MechanicNodeState>;

  // Current navigation path (stack for nested mechanics)
  navigationStack: NavigationFrame[];

  // Aggregated scores
  totalScore: number;
  maxPossibleScore: number;
}

interface MechanicNodeState {
  node_id: string;
  status: 'locked' | 'available' | 'active' | 'completed' | 'skipped';
  score: number;
  max_score: number;
  started_at?: number;
  completed_at?: number;
  attempts: number;

  // Mechanic-specific state (varies by mechanic type)
  mechanicState: MechanicSpecificState;

  // For parent nodes: child completion tracking
  childCompletionMap?: Record<string, boolean>;
}

type MechanicSpecificState =
  | { type: 'drag_drop'; placedLabels: PlacedLabel[]; availableLabels: Label[] }
  | { type: 'trace_path'; pathProgress: PathProgress }
  | { type: 'sequencing'; sequencingProgress: SequencingProgress }
  | { type: 'sorting_categories'; sortingProgress: SortingProgress }
  | { type: 'memory_match'; memoryProgress: MemoryMatchProgress }
  | { type: 'branching_scenario'; branchingProgress: BranchingProgress }
  | { type: 'compare_contrast'; compareProgress: CompareProgress }
  | { type: 'click_to_identify'; identificationProgress: IdentificationProgress }
  | { type: 'description_matching'; descriptionState: DescriptionMatchingState };

interface NavigationFrame {
  node_id: string;
  parent_node_id?: string;
  viewport?: { x: number; y: number; width: number; height: number };
  entered_at: number;
}
```

### 5.2 Navigation Stack Pattern

For nested mechanics, maintain a **navigation stack** (like a browser history stack):

```
Stack:  [hub_diagram] -> [heart_subgame] -> [heart_trace_path]
                                                     ^
                                              current position

"Back" pops the stack and returns to parent view.
```

```typescript
interface NavigationActions {
  // Push a new mechanic onto the stack (enter child)
  pushMechanic: (nodeId: string, viewport?: Viewport) => void;

  // Pop the current mechanic (return to parent)
  popMechanic: () => void;

  // Replace current mechanic (lateral move, e.g., switching between
  // parallel unlocked mechanics)
  replaceMechanic: (nodeId: string) => void;

  // Get current mechanic info
  getCurrentFrame: () => NavigationFrame;

  // Get breadcrumb path
  getBreadcrumbs: () => Array<{ nodeId: string; title: string }>;
}
```

### 5.3 Score Aggregation (Composite Pattern)

Scores must aggregate from children to parents using the **Composite pattern**:

```typescript
function computeNodeScore(
  nodeId: string,
  nodeStates: Record<string, MechanicNodeState>,
  dag: MechanicDAG
): { score: number; maxScore: number } {
  const node = dag.nodes.find(n =>
    n.node_type === 'mechanic' && n.mechanic_id === nodeId
  );
  if (!node) return { score: 0, maxScore: 0 };

  const state = nodeStates[nodeId];

  // If node has no children, return its own score
  const childEdges = dag.edges.filter(
    e => e.from === nodeId && e.edge_type === 'contains'
  );

  if (childEdges.length === 0) {
    return { score: state?.score ?? 0, maxScore: state?.max_score ?? 0 };
  }

  // Aggregate child scores
  let totalScore = 0;
  let totalMaxScore = 0;
  for (const edge of childEdges) {
    const childResult = computeNodeScore(edge.to, nodeStates, dag);
    totalScore += childResult.score;
    totalMaxScore += childResult.maxScore;
  }

  // Add parent's own score (if it has direct interaction)
  totalScore += state?.score ?? 0;
  totalMaxScore += state?.max_score ?? 0;

  return { score: totalScore, maxScore: totalMaxScore };
}
```

### 5.4 XState / Statecharts Alternative

For very complex transition logic, consider XState's statechart model. Statecharts add three key features beyond flat state machines:

1. **Hierarchical (nested) states:** A state can contain sub-states. A "playing" state can have "labeling," "tracing," "sequencing" sub-states.
2. **Parallel (orthogonal) states:** Multiple state regions can be active simultaneously. "organ_A_subgame" and "organ_B_subgame" can run in parallel.
3. **History states:** When re-entering a compound state, resume where you left off.

```typescript
// XState machine sketch for hierarchical mechanic game
const gameMachine = createMachine({
  id: 'game',
  initial: 'hub',
  states: {
    hub: {
      on: {
        ENTER_HEART: 'heart_subgame',
        ENTER_LUNGS: 'lungs_subgame',
      },
    },
    heart_subgame: {
      initial: 'label',
      states: {
        label: {
          on: { COMPLETE: 'trace' },
        },
        trace: {
          on: { COMPLETE: 'done' },
        },
        done: { type: 'final' },
      },
      onDone: 'hub',  // Return to hub when subgame completes
    },
    lungs_subgame: {
      initial: 'identify',
      states: {
        identify: {
          on: { COMPLETE: 'done' },
        },
        done: { type: 'final' },
      },
      onDone: 'hub',
    },
  },
});
```

**Trade-off:** XState provides rigorous guarantees (no impossible states, clear transitions) but adds a dependency and requires refactoring the existing Zustand store. **Recommendation:** Use XState concepts (hierarchical states, parallel regions) but implement within the existing Zustand architecture using the navigation stack pattern. Migrate to XState only if state bugs become unmanageable.

### 5.5 Handling "Back to Parent" Navigation

When a student navigates from a child mechanic back to its parent:

1. **Preserve child state:** The child mechanic's progress is saved in `nodeStates[childId]`
2. **Update parent display:** Mark the zone that spawned the child as "completed" (with visual indicator)
3. **Re-evaluate parent gates:** Check if completing this child unlocks other children or completes the parent
4. **Animate transition:** Zoom-out animation from child viewport back to parent view
5. **Resume parent state:** Parent mechanic continues where the student left off

---

## 6. Data Structures for Mechanic DAGs

### 6.1 Core DAG Schema (Backend: Pydantic)

```python
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class DAGNodeType(str, Enum):
    MECHANIC = "mechanic"
    GATE = "gate"
    BRANCH = "branch"
    HUB = "hub"


class DAGEdgeType(str, Enum):
    UNLOCK = "unlock"           # Completion of A unlocks B
    PREREQUISITE = "prerequisite"  # A must be done before B can start
    CONTAINS = "contains"       # A is the parent of B (hierarchical)
    CONDITIONAL = "conditional" # A routes to B based on condition
    EMBEDS = "embeds"          # A has B embedded within it (recursive)


class GateType(str, Enum):
    AND = "AND"
    OR = "OR"
    N_OF_M = "N_OF_M"
    SCORE_THRESHOLD = "SCORE_THRESHOLD"


class MechanicDAGNode(BaseModel):
    """A node in the mechanic DAG."""
    node_id: str
    node_type: DAGNodeType
    title: str = ""

    # For MECHANIC nodes
    mechanic_type: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    zone_ids: List[str] = Field(default_factory=list)
    label_ids: List[str] = Field(default_factory=list)
    max_score: int = 0

    # For GATE nodes
    gate_type: Optional[GateType] = None
    min_required: Optional[int] = None
    score_threshold: Optional[float] = None

    # For BRANCH nodes
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    default_target: Optional[str] = None

    # For MECHANIC nodes with children (hierarchical)
    viewport: Optional[Dict[str, float]] = None  # {x, y, width, height}
    child_diagram_url: Optional[str] = None

    # For HUB nodes
    completion_requirement: Optional[str] = None  # "all" or "any_n"


class MechanicDAGEdge(BaseModel):
    """An edge in the mechanic DAG."""
    edge_id: str
    from_node: str
    to_node: str
    edge_type: DAGEdgeType

    # For CONDITIONAL edges
    condition: Optional[Dict[str, Any]] = None

    # For visual transitions
    animation: str = "fade"
    message: Optional[str] = None


class MechanicDAG(BaseModel):
    """
    Directed Acyclic Graph representing mechanic relationships.

    Replaces the flat ModeTransition[] list with a proper graph
    that can express sequential, parallel, hierarchical, conditional,
    recursive, and hub-and-spoke patterns.
    """
    dag_id: str
    nodes: List[MechanicDAGNode]
    edges: List[MechanicDAGEdge]
    root_node_ids: List[str] = Field(default_factory=list)

    def get_node(self, node_id: str) -> Optional[MechanicDAGNode]:
        return next((n for n in self.nodes if n.node_id == node_id), None)

    def get_children(self, node_id: str) -> List[str]:
        return [e.to_node for e in self.edges
                if e.from_node == node_id and e.edge_type == DAGEdgeType.CONTAINS]

    def get_prerequisites(self, node_id: str) -> List[str]:
        return [e.from_node for e in self.edges
                if e.to_node == node_id
                and e.edge_type in (DAGEdgeType.PREREQUISITE, DAGEdgeType.UNLOCK)]

    def topological_order(self) -> List[str]:
        """Return node IDs in topological order (dependencies first)."""
        visited = set()
        order = []

        def dfs(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            for prereq in self.get_prerequisites(node_id):
                dfs(prereq)
            order.append(node_id)

        for node in self.nodes:
            dfs(node.node_id)
        return order

    def validate_acyclic(self) -> bool:
        """Verify the graph has no cycles."""
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = {n.node_id: WHITE for n in self.nodes}

        def has_cycle(node_id):
            colors[node_id] = GRAY
            for edge in self.edges:
                if edge.from_node == node_id:
                    if colors[edge.to_node] == GRAY:
                        return True
                    if colors[edge.to_node] == WHITE and has_cycle(edge.to_node):
                        return True
            colors[node_id] = BLACK
            return False

        return not any(
            has_cycle(n.node_id)
            for n in self.nodes
            if colors[n.node_id] == WHITE
        )
```

### 6.2 Frontend DAG Schema (TypeScript)

```typescript
type DAGNodeType = 'mechanic' | 'gate' | 'branch' | 'hub';
type DAGEdgeType = 'unlock' | 'prerequisite' | 'contains' | 'conditional' | 'embeds';
type GateType = 'AND' | 'OR' | 'N_OF_M' | 'SCORE_THRESHOLD';

interface MechanicDAGNode {
  node_id: string;
  node_type: DAGNodeType;
  title: string;

  // MECHANIC nodes
  mechanic_type?: InteractionMode;
  config?: Record<string, unknown>;
  zone_ids?: string[];
  label_ids?: string[];
  max_score?: number;

  // GATE nodes
  gate_type?: GateType;
  min_required?: number;
  score_threshold?: number;

  // BRANCH nodes
  conditions?: Array<{
    min?: number;
    max?: number;
    target_node_id: string;
  }>;
  default_target?: string;

  // Hierarchical
  viewport?: { x: number; y: number; width: number; height: number };
  child_diagram_url?: string;

  // HUB
  completion_requirement?: 'all' | 'any_n';
}

interface MechanicDAGEdge {
  edge_id: string;
  from_node: string;
  to_node: string;
  edge_type: DAGEdgeType;
  condition?: Record<string, unknown>;
  animation?: string;
  message?: string;
}

interface MechanicDAG {
  dag_id: string;
  nodes: MechanicDAGNode[];
  edges: MechanicDAGEdge[];
  root_node_ids: string[];
}
```

### 6.3 Blueprint Schema Extension

The existing `InteractiveDiagramBlueprint` can be extended to include the DAG:

```typescript
interface InteractiveDiagramBlueprint {
  // ... existing fields ...

  // NEW: Mechanic DAG (replaces modeTransitions for complex games)
  mechanicGraph?: MechanicDAG;

  // PRESERVED: modeTransitions still works for simple sequential chains
  // (backward compatible -- if mechanicGraph is absent, fall back to modeTransitions)
  modeTransitions?: ModeTransition[];
}
```

### 6.4 Desugaring Sequential Chains to DAGs

For backward compatibility, the existing `ModeTransition[]` can be automatically converted to a `MechanicDAG`:

```typescript
function modeTransitionsToDAG(
  mechanics: Mechanic[],
  transitions: ModeTransition[]
): MechanicDAG {
  const nodes: MechanicDAGNode[] = mechanics.map((m, i) => ({
    node_id: `mechanic_${i}`,
    node_type: 'mechanic' as const,
    title: m.type,
    mechanic_type: m.type,
    config: m.config,
    max_score: m.scoring?.max_score ?? 0,
  }));

  const edges: MechanicDAGEdge[] = transitions.map((t, i) => {
    const fromIdx = mechanics.findIndex(m => m.type === t.from);
    const toIdx = mechanics.findIndex(m => m.type === t.to);
    return {
      edge_id: `edge_${i}`,
      from_node: `mechanic_${fromIdx}`,
      to_node: `mechanic_${toIdx}`,
      edge_type: 'unlock' as const,
      animation: t.animation ?? 'fade',
      message: t.message,
    };
  });

  return {
    dag_id: 'auto_sequential',
    nodes,
    edges,
    root_node_ids: [nodes[0]?.node_id].filter(Boolean),
  };
}
```

---

## 7. Frontend Architecture for Nested Games

### 7.1 Component Composition

```
<GameShell>
  <BreadcrumbNav path={navigationStack} onNavigate={popToFrame} />
  <ProgressMiniMap dag={mechanicGraph} nodeStates={nodeStates} />

  <MechanicViewport currentFrame={currentFrame}>
    {/* Renders the appropriate mechanic component based on current frame */}
    <MechanicRouter
      mechanic={currentMechanic}
      zones={currentZones}
      labels={currentLabels}
      config={currentConfig}
      onComplete={handleMechanicComplete}
      onEnterChild={handleEnterChild}
    />
  </MechanicViewport>

  <ScorePanel totalScore={totalScore} breakdown={scoreBreakdown} />
</GameShell>
```

### 7.2 MechanicViewport: Zoom Transitions

```typescript
interface MechanicViewportProps {
  currentFrame: NavigationFrame;
  previousFrame?: NavigationFrame;
  transitionType: 'zoom_in' | 'zoom_out' | 'slide' | 'fade' | 'none';
  children: React.ReactNode;
}

function MechanicViewport({
  currentFrame,
  previousFrame,
  transitionType,
  children,
}: MechanicViewportProps) {
  const [isTransitioning, setIsTransitioning] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (previousFrame && transitionType === 'zoom_in') {
      // Animate zoom from parent zone to full viewport
      const viewport = currentFrame.viewport;
      if (viewport && containerRef.current) {
        setIsTransitioning(true);
        // Start: show the zone area at parent scale
        containerRef.current.style.transform =
          `scale(${100 / viewport.width}) ` +
          `translate(-${viewport.x}%, -${viewport.y}%)`;
        containerRef.current.style.transformOrigin = 'top left';

        // Animate to: full viewport
        requestAnimationFrame(() => {
          containerRef.current!.style.transition = 'transform 0.6s ease-in-out';
          containerRef.current!.style.transform = 'scale(1) translate(0, 0)';
        });

        setTimeout(() => setIsTransitioning(false), 600);
      }
    }
  }, [currentFrame, previousFrame, transitionType]);

  return (
    <div
      ref={containerRef}
      className="mechanic-viewport"
      style={{ overflow: isTransitioning ? 'hidden' : 'visible' }}
    >
      {children}
    </div>
  );
}
```

### 7.3 Breadcrumb Navigation

```typescript
interface BreadcrumbNavProps {
  navigationStack: NavigationFrame[];
  mechanicGraph: MechanicDAG;
  onNavigate: (frameIndex: number) => void;
}

function BreadcrumbNav({ navigationStack, mechanicGraph, onNavigate }: BreadcrumbNavProps) {
  return (
    <nav className="flex items-center gap-1 text-sm text-gray-600 mb-2">
      {navigationStack.map((frame, index) => {
        const node = mechanicGraph.nodes.find(n => n.node_id === frame.node_id);
        const isLast = index === navigationStack.length - 1;
        return (
          <React.Fragment key={frame.node_id}>
            {index > 0 && <span className="text-gray-400">/</span>}
            <button
              onClick={() => !isLast && onNavigate(index)}
              className={
                isLast
                  ? 'font-semibold text-gray-900 cursor-default'
                  : 'text-blue-600 hover:underline cursor-pointer'
              }
              disabled={isLast}
            >
              {node?.title ?? frame.node_id}
            </button>
          </React.Fragment>
        );
      })}
    </nav>
  );
}
```

### 7.4 Progress Mini-Map

```typescript
interface ProgressMiniMapProps {
  dag: MechanicDAG;
  nodeStates: Record<string, MechanicNodeState>;
  currentNodeId: string;
  onNodeClick?: (nodeId: string) => void;
}

function ProgressMiniMap({ dag, nodeStates, currentNodeId, onNodeClick }: ProgressMiniMapProps) {
  // Render a simplified DAG visualization
  // - Completed nodes: green with checkmark
  // - Active node: blue with pulse animation
  // - Available nodes: white/outlined
  // - Locked nodes: gray
  // - Gate nodes: diamond shape

  return (
    <div className="fixed top-4 right-4 w-48 bg-white/90 rounded-lg shadow-lg p-3 z-50">
      <h4 className="text-xs font-semibold text-gray-500 mb-2">Progress</h4>
      <svg viewBox="0 0 200 300" className="w-full">
        {/* Render edges as lines */}
        {dag.edges.map(edge => (
          <line
            key={edge.edge_id}
            /* coordinates computed from layout algorithm */
            className={
              nodeStates[edge.from_node]?.status === 'completed'
                ? 'stroke-green-400'
                : 'stroke-gray-300'
            }
            strokeWidth={2}
          />
        ))}
        {/* Render nodes as circles/diamonds */}
        {dag.nodes.map(node => {
          const state = nodeStates[node.node_id];
          const isCurrent = node.node_id === currentNodeId;
          return (
            <g
              key={node.node_id}
              onClick={() => onNodeClick?.(node.node_id)}
              className="cursor-pointer"
            >
              {node.node_type === 'gate' ? (
                <polygon /* diamond shape */ />
              ) : (
                <circle
                  r={isCurrent ? 12 : 8}
                  className={getNodeColor(state?.status, isCurrent)}
                />
              )}
              <text className="text-[8px]">{node.title}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
```

### 7.5 Hub Diagram View

```typescript
interface HubDiagramProps {
  hubNode: MechanicDAGNode;
  spokeStates: Record<string, MechanicNodeState>;
  diagram: DiagramSpec;
  zones: Zone[];
  onZoneClick: (zoneId: string, spokeNodeId: string) => void;
}

function HubDiagram({ hubNode, spokeStates, diagram, zones, onZoneClick }: HubDiagramProps) {
  return (
    <div className="relative">
      <DiagramCanvas imageUrl={diagram.assetUrl} width={diagram.width} height={diagram.height}>
        {zones.map(zone => {
          const spokeEdge = /* find edge from hub to spoke for this zone */;
          const spokeState = spokeStates[spokeEdge?.to_node ?? ''];
          const status = spokeState?.status ?? 'available';

          return (
            <div
              key={zone.id}
              className="absolute cursor-pointer transition-all"
              style={{
                left: `${zone.x}%`,
                top: `${zone.y}%`,
                width: `${zone.width}%`,
                height: `${zone.height}%`,
              }}
              onClick={() => status !== 'locked' && onZoneClick(zone.id, spokeEdge.to_node)}
            >
              {/* Zone overlay with status indicator */}
              <div className={getZoneOverlayClass(status)}>
                {status === 'completed' && <CheckIcon />}
                {status === 'in_progress' && <ProgressRing percent={...} />}
                {status === 'locked' && <LockIcon />}
              </div>
              <span className="zone-label">{zone.label}</span>
            </div>
          );
        })}
      </DiagramCanvas>

      {/* Overall progress bar */}
      <div className="mt-4">
        <ProgressBar
          completed={Object.values(spokeStates).filter(s => s.status === 'completed').length}
          total={Object.keys(spokeStates).length}
        />
      </div>
    </div>
  );
}
```

---

## 8. LangGraph / Pipeline Implications

### 8.1 Generating Hierarchical Mechanic Structures

The pipeline must be extended to generate `MechanicDAG` structures instead of flat `ModeTransition[]` lists. This primarily affects three agents:

1. **game_planner / game_designer_v3**: Decides the overall game structure
2. **interaction_designer / interaction_designer_v3**: Designs mechanic transitions
3. **blueprint_assembler_v3**: Assembles the final blueprint with the DAG

#### Game Planner Changes

The game planner prompt should be extended with a decision framework:

```
When planning the game structure, consider:
1. Does the content have hierarchical structure? (e.g., system -> subsystems -> components)
   -> Use NESTED/HIERARCHICAL chaining
2. Are there independent knowledge areas that can be explored in any order?
   -> Use HUB-AND-SPOKE or PARALLEL UNLOCK
3. Does mastery of one concept enable understanding of another?
   -> Use PREREQUISITE TREE
4. Should struggling students get different content than advanced students?
   -> Use CONDITIONAL BRANCHING
5. Does a decision-making scenario require sub-skills?
   -> Use RECURSIVE NESTING
6. Is the content naturally linear (step 1, step 2, step 3)?
   -> Use SEQUENTIAL (default)
```

#### LangGraph Subgraph Architecture

LangGraph natively supports nested subgraphs, which maps well to hierarchical mechanic generation:

```python
# Parent graph generates the overall DAG structure
parent_graph = StateGraph(AgentState)

# Subgraph for generating each "spoke" or "child" mechanic
child_mechanic_graph = StateGraph(ChildMechanicState)

# Wire together
parent_graph.add_node("plan_hierarchy", plan_hierarchy_node)
parent_graph.add_node("generate_child_mechanics",
    child_mechanic_graph.compile())
```

For each node in the mechanic DAG, the pipeline may need to:
- Retrieve a separate diagram image (for nested/hub-spoke patterns)
- Generate zone annotations specific to that sub-region
- Create labels and configs specific to that mechanic context

This suggests a **Map-Reduce pattern** in LangGraph using the Send API:

```python
def fan_out_child_mechanics(state: AgentState):
    """Fan out to generate each child mechanic in parallel."""
    mechanic_dag = state.get("mechanic_dag", {})
    sends = []
    for node in mechanic_dag.get("nodes", []):
        if node["node_type"] == "mechanic" and node.get("needs_generation"):
            sends.append(
                Send("generate_child_mechanic", {
                    "parent_state": state,
                    "mechanic_node": node,
                })
            )
    return sends
```

### 8.2 When to Use Which Pattern

| Content Type | Recommended Pattern | Why |
|---|---|---|
| Anatomy: organ systems | Hub-and-spoke + Nested | Natural hierarchy: body -> organs -> internal structures |
| Biology: processes | Sequential + Conditional | Steps follow order; branch on comprehension |
| Chemistry: reactions | Prerequisite tree | Understanding reactants before products |
| History: timelines | Sequential | Chronological order |
| Geography: maps | Hub-and-spoke | Spatial exploration by region |
| Engineering: systems | Nested + Parallel | Subsystem independence with integration |
| Medical: diagnosis | Recursive nesting | Decision trees with embedded skill checks |
| Physics: forces | Prerequisite tree | Foundational concepts required for advanced |
| Language: grammar | Parallel unlock + Sequential | Some topics independent, some build on others |
| Math: problem-solving | Conditional branching | Adaptive difficulty based on performance |

### 8.3 Asset Generation for Nested Mechanics

Nested and hub-and-spoke patterns require **multiple diagram images** per game:

1. **Parent/hub diagram:** Overview image (e.g., full human body)
2. **Child/spoke diagrams:** Zoomed-in detail images (e.g., heart interior, lung cross-section)

The asset pipeline must handle this:

```python
class HierarchicalAssetNeeds(BaseModel):
    """Asset needs for hierarchical mechanic structure."""
    parent_image: AssetNeed  # Main overview diagram
    child_images: Dict[str, AssetNeed]  # node_id -> asset need for that node
    shared_assets: List[AssetNeed]  # Assets used across multiple nodes
```

Two approaches for child images:
1. **Crop and upscale:** Take the parent image, crop to the zone's bounding box, upscale with AI
2. **Generate separately:** Use image generation to create a detailed view of the sub-region
3. **SVG zoom:** If using SVG diagrams, simply change the viewBox to zoom into the region

Recommendation: Start with option 3 (SVG zoom) for simplicity, fall back to option 2 (separate generation) when photographic/raster diagrams are used.

---

## 9. Real-World Examples and Precedents

### 9.1 Game Design Precedents

**Zelda Dungeons (Nested + Hub-and-Spoke):**
Each dungeon is a hub with rooms (spokes). Within each room, puzzles must be solved (mechanics). Some rooms require keys from other rooms (prerequisite tree). The boss room requires completing most other rooms (AND gate).

**Metroidvania (Prerequisite Tree + Hub-and-Spoke):**
Abilities acquired in one area unlock access to other areas. The world map is a hub, areas are spokes. Within each area, challenges test the relevant ability. Backtracking with new abilities reveals previously inaccessible content.

**Super Mario World (Hub-and-Spoke + Conditional):**
The world map is a hub. Each level is a spoke. Some levels have secret exits (conditional branching based on performance). Star Road provides alternate paths (parallel unlock).

**Portal (Sequential + Nested):**
Test chambers progress sequentially, but each chamber contains sub-puzzles that must be solved (nested mechanics within a chamber).

### 9.2 Educational Platform Precedents

**Khan Academy Mastery System (Prerequisite Tree):**
Khan Academy previously used a knowledge map that was essentially a DAG of skills. Students progressed through levels: Attempted -> Familiar -> Proficient -> Mastered. Higher-level skills required mastery of prerequisite skills. The system was eventually replaced with a linear path for maintainability, but the underlying model remains a skill DAG.

**Duolingo Skill Tree (Sequential + Prerequisite Tree):**
Skills unlock in a structured path. Each skill has multiple crown levels (nested progression). The path is primarily linear but with some parallel skill availability. Practice sessions dynamically adapt to demonstrated weaknesses (conditional branching).

**PhET Simulations (Hub-and-Spoke):**
Interactive science simulations allow exploration of different parameters. Each parameter space is like a spoke from the central simulation. Multiple learning objectives can be assessed within a single simulation.

**Legends of Learning (Sequential + Conditional):**
Platform presents sequences of learning games with adaptive difficulty. Performance on earlier games affects which games are presented next. Teachers can configure prerequisite relationships between game sets.

### 9.3 Academic Research

**Scaffolding Theory (Vygotsky, Wood/Bruner/Ross 1976):**
The concept of scaffolding directly maps to hierarchical mechanics: initial support (parent mechanic) is gradually removed as the learner demonstrates competence (child mechanics become more challenging). Effective scaffolding is contingent -- it adapts based on the learner's demonstrated ability.

**Bloom's Taxonomy and Game Mechanics Mapping:**
Research by Arnab et al. (2015) maps learning mechanics to game mechanics at each level of Bloom's taxonomy. Lower-level mechanics (remembering, understanding) map to recognition-based games; higher-level mechanics (analyzing, evaluating) map to decision-making games. Hierarchical chaining naturally encodes this progression.

**Learning Mechanics-Game Mechanics (LM-GM) Model:**
The LM-GM model provides a framework for aligning game mechanics with learning objectives. In hierarchical chaining, each level of the hierarchy can target a different LM-GM alignment, creating a multi-layered learning experience.

**Adaptive Difficulty Research:**
Research on adaptive difficulty adjustment in educational games has found significantly higher learning outcomes when game difficulty adjusts to student performance, supporting the conditional branching pattern.

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Backend DAG Schema + Desugaring)

**Effort:** 2-3 days

1. Add `MechanicDAG`, `MechanicDAGNode`, `MechanicDAGEdge` Pydantic schemas to `backend/app/agents/schemas/`
2. Add `mechanic_graph` field to `IDBlueprint` and `InteractiveDiagramBlueprint` (frontend types)
3. Implement `modeTransitionsToDAG()` desugaring function (Python + TypeScript)
4. Update `blueprint_assembler_v3` to output `mechanic_graph` when `ModeTransition[]` is present
5. Update frontend to check `mechanicGraph` first, fall back to `modeTransitions`

**Value delivered:** Zero visible change, but the data model is ready for all patterns.

### Phase 2: DAG Engine (Frontend State + Navigation)

**Effort:** 3-4 days

1. Add `HierarchicalGameState` to Zustand store (alongside existing state, not replacing)
2. Implement `NavigationStack` with push/pop/replace
3. Implement `computeNodeScore()` score aggregation
4. Implement DAG traversal: `getAvailableNodes()`, `isNodeUnlocked()`, `evaluateGate()`
5. Add `BreadcrumbNav` component
6. Add `ProgressMiniMap` component

**Value delivered:** Engine is ready for all patterns; existing games continue to work.

### Phase 3: Hub-and-Spoke (First Hierarchical Pattern)

**Effort:** 3-4 days

1. Implement `HubDiagram` component with clickable zones showing spoke status
2. Implement zoom-in/zoom-out transitions between hub and spoke views
3. Update `game_planner` prompt to detect hub-and-spoke-suitable content
4. Update `blueprint_assembler_v3` to generate hub-and-spoke DAGs
5. Test with anatomy content: "Human body organs" hub with organ-specific sub-games

**Value delivered:** First hierarchical pattern visible to users.

### Phase 4: Conditional Branching (Adaptive Difficulty)

**Effort:** 2-3 days

1. Add `BRANCH` node type to DAG engine
2. Implement branch evaluation in frontend DAG traversal
3. Add transition UI: score display -> routing message -> next mechanic
4. Update `interaction_designer` to generate conditional branches
5. Test with varying-difficulty scenarios

**Value delivered:** Adaptive difficulty for multi-mechanic games.

### Phase 5: Parallel Unlock + AND/OR Gates

**Effort:** 2-3 days

1. Add `GATE` node type rendering in mini-map and main view
2. Implement parallel mechanic display (tabbed or selectable)
3. Add gate evaluation logic: AND (all inputs complete), OR (any input complete), N_OF_M
4. Update game planner to detect parallel-suitable content

**Value delivered:** Non-linear learning paths.

### Phase 6: Recursive Nesting (Advanced)

**Effort:** 4-5 days

1. Implement embedded mechanic rendering within branching_scenario nodes
2. Add depth tracking and max-depth enforcement
3. Handle score/state flow between embedded mechanic and parent
4. Test with medical diagnosis scenario: branching with mini-games at each decision

**Value delivered:** Most complex pattern; high impact for specific content types.

### Total Estimated Effort: 16-22 days

### Priority Recommendation

```
Phase 1 (Foundation)     ---- MUST HAVE ---- (enables everything else)
Phase 2 (DAG Engine)     ---- MUST HAVE ---- (core infrastructure)
Phase 3 (Hub-and-Spoke)  ---- HIGH VALUE ---- (most natural for diagram games)
Phase 4 (Conditional)    ---- HIGH VALUE ---- (adaptive difficulty)
Phase 5 (Parallel/Gates) ---- MEDIUM VALUE -- (nice-to-have for complex content)
Phase 6 (Recursive)      ---- LOW PRIORITY -- (specific use cases only)
```

---

## 11. References

### Academic and Research Sources

1. Vygotsky, L. S. (1978). *Mind in Society: Development of Higher Psychological Processes.* Harvard University Press.
2. Wood, D., Bruner, J. S., & Ross, G. (1976). The role of tutoring in problem solving. *Journal of Child Psychology and Psychiatry*, 17(2), 89-100.
3. Bloom, B. S. (1956). *Taxonomy of Educational Objectives.* David McKay Company.
4. Arnab, S., et al. (2015). Mapping learning and game mechanics for serious games analysis. *British Journal of Educational Technology*, 46(2), 391-411.
5. Lopes, R., & Bidarra, R. (2011). Adaptivity challenges in games and simulations: A survey. *IEEE Transactions on Computational Intelligence and AI in Games*, 3(2), 85-99.

### Game Design Sources

6. Nystrom, R. (2014). *Game Programming Patterns.* Genever Benning. https://gameprogrammingpatterns.com/
7. "Making Sense of Metroidvania Game Design." *Game Developer.* https://www.gamedeveloper.com/design/making-sense-of-metroidvania-game-design
8. "Typology." *The Level Design Book.* https://book.leveldesignbook.com/process/layout/typology
9. "Hub and Spoke Scenarios." *RPGnet.* https://www.rpg.net/columns/soap/soap155.phtml
10. "Design Patterns For Implementing Game Mechanics." University of Groningen. https://www.cs.rug.nl/search/uploads/Resources/PCI2016TR.pdf

### Technology Sources

11. XState Documentation. https://stately.ai/docs/states
12. Zustand GitHub Repository. https://github.com/pmndrs/zustand
13. LangGraph Subgraphs Documentation. https://docs.langchain.com/oss/python/langgraph/use-subgraphs
14. TypeScript Graph Library. https://segfaultx64.github.io/typescript-graph/
15. "Optimal Skill Tree Growth." https://tommyodland.com/articles/2020/optimal-skill-tree-growth/index.html

### Educational Platform Sources

16. Khan Academy Mastery System. https://support.khanacademy.org/hc/en-us/articles/5548760867853
17. "The Science Behind Duolingo's Home Screen Redesign." *Duolingo Blog.* https://blog.duolingo.com/new-duolingo-home-screen-design/
18. "Progressive Disclosure." *Nielsen Norman Group.* https://www.nngroup.com/articles/progressive-disclosure/
19. "Designing Mini-Games as Micro-Learning Resources." ERIC. https://files.eric.ed.gov/fulltext/EJ1296848.pdf
20. "The effectiveness of adaptive difficulty adjustments on students' motivation and learning in an educational computer game." *Computers & Education.* https://www.sciencedirect.com/science/article/abs/pii/S0360131513001711

---

## Appendix A: Pattern Summary Table

| Pattern | Complexity | Educational Value | Implementation Priority | Diagram-Game Fit |
|---|---|---|---|---|
| Sequential | Low | Medium | Already done | High |
| Parallel Unlock | Medium | High | Phase 5 | Medium |
| Prerequisite Tree | High | High | Phase 5 | Medium |
| Nested/Hierarchical | High | Very High | Phase 3 | Very High |
| Conditional Branching | Medium | Very High | Phase 4 | High |
| Recursive Nesting | Very High | High (niche) | Phase 6 | Medium |
| Hub-and-Spoke | Medium-High | Very High | Phase 3 | Very High |

## Appendix B: Mapping Current Mechanics to Patterns

| Mechanic | Best as Parent | Best as Child | Hub Zone? |
|---|---|---|---|
| drag_drop | Yes (label overview) | Yes (label sub-region) | Yes |
| click_to_identify | Moderate | Yes | Yes |
| trace_path | Moderate | Yes (trace within zone) | No |
| sequencing | No | Yes | No |
| sorting_categories | No | Yes | No |
| description_matching | No | Yes | Yes |
| memory_match | No | Yes | No |
| branching_scenario | Yes (decision hub) | No | Possible |
| compare_contrast | No | Yes | No |

**Key insight:** `drag_drop` and `branching_scenario` are natural parent mechanics. Most other mechanics work best as children or spokes. This guides the pipeline's decision-making about when to use hierarchical vs sequential chaining.

## Appendix C: Example DAG for "Heart Anatomy" Game

```
DAG for "Explore the Human Heart"

Nodes:
  hub_heart        [HUB]       "Heart Overview"
  m_label_chambers [MECHANIC]  drag_drop - "Label the 4 chambers"
  m_label_valves   [MECHANIC]  drag_drop - "Label the heart valves"
  gate_basic       [GATE:AND]  "Basic anatomy mastered"
  m_trace_blood    [MECHANIC]  trace_path - "Trace blood flow"
  m_sequence_cycle [MECHANIC]  sequencing - "Order the cardiac cycle"
  gate_flow        [GATE:AND]  "Blood flow understood"
  branch_assess    [BRANCH]    "Assessment routing"
  m_remediate      [MECHANIC]  drag_drop - "Review: label simplified heart"
  m_advanced       [MECHANIC]  branching_scenario - "Diagnose heart condition"

Edges:
  hub_heart        --[contains]--> m_label_chambers
  hub_heart        --[contains]--> m_label_valves
  m_label_chambers --[unlock]----> gate_basic
  m_label_valves   --[unlock]----> gate_basic
  gate_basic       --[unlock]----> m_trace_blood
  gate_basic       --[unlock]----> m_sequence_cycle
  m_trace_blood    --[unlock]----> gate_flow
  m_sequence_cycle --[unlock]----> gate_flow
  gate_flow        --[unlock]----> branch_assess
  branch_assess    --[conditional: score<60]--> m_remediate
  branch_assess    --[conditional: score>=60]--> m_advanced

Visual:

          +------------------+
          |   hub_heart      |
          | (Heart Overview) |
          +--------+---------+
                   |
          +--------+---------+
          |                  |
    [label_chambers]   [label_valves]
          |                  |
          +----[AND gate]----+
                   |
          +--------+---------+
          |                  |
    [trace_blood]     [sequence_cycle]
          |                  |
          +----[AND gate]----+
                   |
            [BRANCH: score?]
              /          \
         <60%            >=60%
          |                |
    [remediate]      [advanced_scenario]
```

This DAG encodes:
- Hub-and-spoke (hub_heart contains two labeling sub-games)
- Parallel unlock (label chambers and valves independently)
- AND gate (both must be done before tracing)
- Prerequisite tree (trace + sequence before assessment)
- Conditional branching (score determines remediation vs. advanced)

All seven patterns working together in a single coherent game.
