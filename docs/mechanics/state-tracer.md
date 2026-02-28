# State Tracer — Mechanic Specification

> **Status:** Frontend complete (8 demos, 6 visualizers). Backend generation not yet implemented.
> **Template type:** `ALGORITHM_GAME`
> **Entry point:** `frontend/src/components/templates/AlgorithmGame/StateTracerGame.tsx`

---

## 1. What It Does

State Tracer is a **step-through algorithm visualization** mechanic. The student sees:

- Syntax-highlighted code with a line marker
- A data structure visualization that updates each step
- A variable tracker sidebar showing current values
- A **prediction prompt** at key steps — the student must predict what happens next before the algorithm advances

It supports **any algorithm and any data structure** — the mechanic is fully data-driven. The same React components render Bubble Sort on arrays, BFS on graphs, Fibonacci on DP tables, etc. The only thing that changes is the blueprint data.

---

## 2. Blueprint Data Contract

The backend must produce a single JSON object conforming to `StateTracerBlueprint`:

```typescript
interface StateTracerBlueprint {
  algorithmName: string;          // Display title, e.g. "Bubble Sort"
  algorithmDescription: string;   // One-liner shown in metadata
  narrativeIntro: string;         // Context paragraph shown in header
  code: string;                   // Full source code displayed (Python, JS, etc.)
  language: string;               // Syntax highlighting language ("python", "javascript")
  steps: ExecutionStep[];         // Ordered execution trace — THE CORE DATA
  scoringConfig?: ScoringConfig;  // Optional, defaults provided
}
```

### 2.1 ExecutionStep (per step)

Each step represents one meaningful moment in the algorithm's execution:

```typescript
interface ExecutionStep {
  stepNumber: number;
  codeLine: number;                                                     // 1-indexed line to highlight
  description: string;                                                  // "Compare arr[0]=5 with arr[1]=3"
  variables: Record<string, number | string | boolean | number[] | null>;  // All variable values at this point
  changedVariables: string[];                                           // Which keys changed from previous step
  dataStructure: DataStructure;                                         // Visualization state (see Section 3)
  prediction: Prediction | null;                                        // null = auto-advance, no question
  explanation: string;                                                  // Shown after prediction reveal
  hints: [string, string, string];                                      // [nudge, clue, answer] — 3-tier
}
```

**Key design rules:**
- Steps with `prediction: null` auto-advance (no student interaction). Use these for setup, transitions, or steps that are obvious.
- Steps with a prediction pause the game and wait for student input.
- `codeLine` is 1-indexed, matching the `code` string's line numbers.
- `variables` is the **complete** variable snapshot, not a delta. The frontend diffs against the previous step's variables to highlight changes.
- `changedVariables` tells the VariableTracker which entries to highlight yellow.
- `hints` must always be a 3-tuple. Use `['', '', '']` for auto-advance steps.

### 2.2 Typical Step Count

| Algorithm Complexity | Steps | Predictions | Duration |
|---------------------|-------|-------------|----------|
| Simple (Binary Search) | 8-12 | 6-9 | ~3 min |
| Medium (Bubble Sort, BFS) | 15-20 | 10-15 | ~5 min |
| Complex (DP, multi-pass sorts) | 20-30 | 15-20 | ~8 min |

---

## 3. Data Structure Types

The `dataStructure` field in each step is a discriminated union on the `type` field. The frontend routes to the correct visualizer automatically.

### 3.1 Array (`type: 'array'`)

```typescript
interface ArrayDataStructure {
  type: 'array';
  elements: number[];
  highlights: ArrayHighlight[];     // Which indices to color
  sortedIndices?: number[];         // Indices in their final position (shown green)
}

interface ArrayHighlight {
  index: number;
  color: 'active' | 'comparing' | 'swapping' | 'sorted' | 'success' | 'error';
}
```

**Visualizer:** Bar chart (height = value) + colored value cells below + index labels.

**When to use:** Sorting algorithms, searching algorithms, any array manipulation.

**Highlight color meanings:**
| Color | Meaning | Visual |
|-------|---------|--------|
| `active` | Current focus element or search range | Blue |
| `comparing` | Being compared against another element | Yellow |
| `swapping` | Being moved/swapped | Purple (pulsing) |
| `sorted` | In its final sorted position | Green |
| `success` | Target found / goal achieved | Emerald |
| `error` | Wrong position / failed check | Red |

### 3.2 Graph (`type: 'graph'`)

```typescript
interface GraphDataStructure {
  type: 'graph';
  nodes: GraphNode[];
  edges: GraphEdge[];
  auxiliary?: { label: string; items: string[] };  // Queue/stack display below graph
}

interface GraphNode {
  id: string;          // Unique identifier, e.g. "A"
  label: string;       // Display text inside node circle
  x: number;           // X coordinate (deterministic layout, NOT force-directed)
  y: number;           // Y coordinate
  state: 'unvisited' | 'in_frontier' | 'current' | 'visited';
}

interface GraphEdge {
  from: string;        // Source node id
  to: string;          // Target node id
  weight?: number;     // Optional edge weight (shown on hover)
  state: 'default' | 'exploring' | 'visited' | 'in_result';
  directed?: boolean;  // Default true. Set false for undirected display.
}
```

**Visualizer:** SVG with circles (nodes), lines with arrowheads (edges), auxiliary panel below for queue/stack contents.

**When to use:** BFS, DFS, Dijkstra, topological sort, any graph traversal.

**IMPORTANT — Node positions must be predefined.** The frontend does NOT run a layout algorithm. The backend must supply `x, y` coordinates that produce a readable layout. Recommended approach:
- Hierarchical/tree-like graphs: root at top, children below
- Grid graphs: regular grid positions
- General graphs: pre-compute with a layout algorithm server-side, or use hand-tuned positions

**Auxiliary panel:** Shows queue/stack contents as horizontal badges. Set `label` to "Queue" for BFS, "Stack" for DFS, "Priority Queue" for Dijkstra.

### 3.3 Tree (`type: 'tree'`)

```typescript
interface TreeDataStructure {
  type: 'tree';
  nodes: TreeNode[];
  root: string;                // ID of root node
  highlightPath?: string[];    // Node IDs forming the active path (edges turn blue)
}

interface TreeNode {
  id: string;
  value: number;
  left?: string;     // ID of left child
  right?: string;    // ID of right child
  state: 'default' | 'comparing' | 'path' | 'found' | 'inserted';
}
```

**Visualizer:** SVG hierarchical tree. Layout is computed automatically by the frontend using recursive positioning (root at top center, spread halves per level). No `x, y` needed — unlike graphs.

**When to use:** BST insert/search/delete, tree traversals, heap operations, AVL rotations.

**Progressive building:** For insertion algorithms, each step should only include the nodes that exist at that point. New nodes get a spring scale-in animation when their state is `'inserted'`.

### 3.4 DP Table (`type: 'dp_table'`)

```typescript
interface DPTableDataStructure {
  type: 'dp_table';
  cells: DPCell[][];               // 2D array (use single-row for 1D problems)
  rowLabels?: string[];            // Y-axis labels
  colLabels?: string[];            // X-axis labels
  activeCell?: [number, number];   // [row, col] currently being computed
  dependencies?: DPDependency[];   // Arrows from source cells to active cell
}

interface DPCell {
  value: number | string | null;   // null = not yet computed (shows "?")
  state: 'empty' | 'filled' | 'computing' | 'read' | 'optimal';
}

interface DPDependency {
  from: [number, number];   // [row, col] of source cell
  to: [number, number];     // [row, col] of target cell
}
```

**Visualizer:** SVG grid of cells with colored borders, dependency arrows, hover tooltips.

**When to use:** Fibonacci, LCS, knapsack, edit distance, any DP problem.

**1D vs 2D:** For 1D DP (like Fibonacci), use a single-row 2D array: `cells: [[ cell0, cell1, ..., cellN ]]`.

**Cell state progression:** `empty` (not computed) → `computing` (being calculated now, yellow) → `filled` (done, gray). Source cells being read show `read` (orange). Cells on the optimal solution path show `optimal` (green).

### 3.5 Stack (`type: 'stack'`)

```typescript
interface StackDataStructure {
  type: 'stack';
  items: StackItem[];       // Bottom-to-top order (last item = top of stack)
  capacity?: number;        // Optional max size (shows fill bar)
}

interface StackItem {
  id: string;               // Unique ID for animation tracking
  value: string;            // Display text
  state: 'default' | 'pushing' | 'popping' | 'top' | 'matched';
}
```

**Visualizer:** Vertical LIFO stack rendered top-to-bottom. Push/pop animations via framer-motion AnimatePresence.

**When to use:** Parentheses matching, expression evaluation, undo operations, DFS stack.

**Item ordering:** The `items` array is in **insertion order** (first item = bottom of stack). The visualizer reverses it for display.

**State meanings:**
| State | When to use |
|-------|-------------|
| `pushing` | Item is being added this step |
| `popping` | Item is being removed this step |
| `top` | Item is at the top (auto-applied to last item if state is `default`) |
| `matched` | Item was just matched/consumed (flash green, then remove) |

### 3.6 Linked List (`type: 'linked_list'`)

```typescript
interface LinkedListDataStructure {
  type: 'linked_list';
  nodes: LLNode[];
  head: string | null;        // ID of head node (visualizer starts drawing from here)
  pointers?: LLPointer[];     // Named pointer labels below nodes
}

interface LLNode {
  id: string;
  value: number | string;
  next: string | null;        // ID of next node, or null for tail
  state: 'default' | 'current' | 'prev' | 'done';
}

interface LLPointer {
  name: string;               // "prev", "curr", "next", "head", "tail"
  target: string | null;      // Node ID this pointer points to
  color: string;              // CSS color, e.g. "#ef4444"
}
```

**Visualizer:** Horizontal chain of rectangle nodes (value + pointer section). Named pointer arrows below nodes.

**When to use:** Linked list reversal, insertion, deletion, merge operations.

**Head management during reversal:** During in-place reversal, keep `head` pointing to the original head until the final step (so the visualizer can find all nodes). The visualizer walks from `head` following `next` pointers, then adds any orphan nodes from the `nodes` array.

---

## 4. Prediction Types

The `prediction` field on each step is one of 4 types (or `null` for auto-advance):

### 4.1 Arrangement (drag-and-drop)

```typescript
interface ArrangementPrediction {
  type: 'arrangement';
  prompt: string;                    // "What does the array look like after this swap?"
  elements: number[];                // Starting arrangement shown to student
  correctArrangement: number[];      // Correct answer
}
```

**Frontend:** Drag-and-drop reorderable list. Student rearranges elements and submits.

**Scoring:** Partial credit — each element in the correct position earns proportional points.

**Best for:** "Show the array after this operation", "Arrange these in sorted order".

### 4.2 Value (text input)

```typescript
interface ValuePrediction {
  type: 'value';
  prompt: string;                   // "What is mid = (0 + 6) // 2?"
  correctValue: string;             // "3"
  acceptableValues?: string[];      // ["3", "three"] — alternative accepted answers
  placeholder?: string;             // Input placeholder text
}
```

**Frontend:** Text input field + submit button. Enter key also submits.

**Scoring:** Binary — correct or incorrect (case-insensitive, trimmed).

**Best for:** "What value is computed?", "What is returned?", "What is the stack size?".

### 4.3 Multiple Choice (single select)

```typescript
interface MultipleChoicePrediction {
  type: 'multiple_choice';
  prompt: string;                              // "Is arr[3] equal to, less than, or greater than target?"
  options: { id: string; label: string }[];    // 2-4 options
  correctId: string;                           // ID of correct option
}
```

**Frontend:** Vertical list of buttons. Clicking submits immediately (no separate submit button).

**Scoring:** Binary — correct or incorrect.

**Best for:** "Which direction?", "Push or pop?", "Does the loop continue?", "Left or right child?".

### 4.4 Multi-Select (checkboxes)

```typescript
interface MultiSelectPrediction {
  type: 'multi_select';
  prompt: string;                              // "Which elements are in the sorted portion?"
  options: { id: string; label: string }[];    // Options with checkboxes
  correctIds: string[];                        // All correct option IDs
}
```

**Frontend:** Checkbox list + submit button. Student selects 1+ options, then clicks submit.

**Scoring:** Partial credit — `(correct_selections - wrong_selections) / total_correct`. Capped at 0.

**Best for:** "Which nodes are in the queue?", "Which elements shift?", "Which cells does this depend on?".

---

## 5. Scoring System

### 5.1 Configuration

```typescript
interface ScoringConfig {
  basePoints: number;                                   // Points per correct answer (default: 100)
  streakThresholds: { min: number; multiplier: number }[];  // Streak multiplier tiers
  hintPenalties: [number, number, number];              // Cumulative % penalty per hint tier
  perfectRunBonus: number;                              // % bonus for zero incorrect (default: 0.20)
}
```

**Defaults:**
```
basePoints: 100
streakThresholds: [0→1x, 3→1.5x, 5→2x, 8→3x]
hintPenalties: [10%, 20%, 30%]  (cumulative: tier1=10%, tier2=30%, tier3=60%)
perfectRunBonus: 20%
```

### 5.2 Per-Step Score Formula

```
stepScore = basePoints * partialCredit * streakMultiplier * (1 - hintPenalty)
```

- `partialCredit`: 1.0 for correct, 0.0 for wrong (value/MC), or proportional (arrangement/multi-select)
- `streakMultiplier`: Based on consecutive correct count
- `hintPenalty`: Cumulative from hints used on this step

### 5.3 Final Score

```
finalScore = totalScore * (1 + perfectRunBonus)   // if zero incorrect
finalScore = totalScore                            // otherwise
```

### 5.4 Scoring State (tracked per game)

```typescript
interface ScoringState {
  totalScore: number;
  streak: number;              // Current consecutive correct
  maxStreak: number;           // Best streak achieved
  correctCount: number;
  incorrectCount: number;
  totalPredictions: number;    // Number of steps with predictions
  hintsUsed: number;           // Total hints requested
  stepScores: number[];        // Score earned per prediction step
  hintPenaltiesApplied: number[];  // Hint tier used per prediction step
}
```

---

## 6. Hint System

Each step provides 3 hints of increasing specificity:

| Tier | Name | Penalty | Example |
|------|------|---------|---------|
| 1 | Nudge | -10% | "Think about what an opening parenthesis means." |
| 2 | Clue | -20% | "Opening parens are stored on the stack to be matched later." |
| 3 | Answer | -30% | "Push — we push '(' onto the stack." |

Penalties are **cumulative** (using all 3 = 60% penalty). Hints are only available during `AWAITING_PREDICTION` phase.

**Backend generation guidance:**
- Tier 1 (nudge): General direction, no specifics. "Consider the comparison result."
- Tier 2 (clue): Narrow it down. "5 > 3, so what happens in bubble sort when the left element is larger?"
- Tier 3 (answer): Direct answer without giving away the format. "They swap — the array becomes [3, 5, ...]."

---

## 7. Frontend Architecture

### 7.1 Component Tree

```
StateTracerGame.tsx (398 lines)
│
├── useStateTracerMachine (state machine hook)
│     └── useReducer with 6 phases, 9 action types
│
├── useScoring (scoring logic hook)
│     └── streak multipliers, hint penalties, partial credit
│
├── CodeDisplay (shared component)
│     └── Props: code, language, currentLine, executedLines, theme
│
├── DataStructureVisualizer (router)
│     ├── ArrayVisualizer
│     ├── GraphVisualizer
│     ├── TreeVisualizer
│     ├── DPTableVisualizer
│     ├── StackVisualizer
│     └── LinkedListVisualizer
│
├── PredictionPanel
│     ├── ArrangementPrediction (drag-and-drop)
│     ├── ValueInput (text field)
│     ├── MultipleChoiceInput (radio buttons)
│     └── MultiSelectInput (checkboxes)
│
├── DiffOverlay (correct vs player answer)
├── HintSystem (3-tier progressive hints)
├── ScoreDisplay (total, streak, multiplier)
├── VariableTracker (shared component)
├── StepControls (shared component)
└── CompletionScreen (final stats)
```

### 7.2 State Machine Phases

```
INIT
  │ goToStep(0)
  ▼
SHOWING_STATE
  │ if step has prediction → setTimeout(400ms)
  ▼
AWAITING_PREDICTION  ←── USE_HINT (stays in this phase)
  │ player submits answer
  ▼
PREDICTION_SUBMITTED
  │ setTimeout(300ms)
  ▼
REVEALING_RESULT
  │ player clicks "Continue"
  ▼
SHOWING_STATE (next step)  ──or──  COMPLETED (if last step)
```

Steps with `prediction: null` go directly from `SHOWING_STATE` → next `SHOWING_STATE`, no pause.

### 7.3 File Locations

```
frontend/src/
├── components/templates/AlgorithmGame/
│   ├── StateTracerGame.tsx          # Main container (398 lines)
│   ├── types.ts                     # All TypeScript types (307 lines)
│   ├── hooks/
│   │   ├── useStateTracerMachine.ts # State machine reducer (159 lines)
│   │   └── useScoring.ts           # Scoring logic (93 lines)
│   ├── components/
│   │   ├── DataStructureVisualizer.tsx  # Router to sub-visualizers
│   │   ├── PredictionPanel.tsx          # All 4 prediction type UIs
│   │   ├── ArrangementPrediction.tsx    # Drag-and-drop
│   │   ├── DiffOverlay.tsx             # Result comparison
│   │   ├── HintSystem.tsx              # 3-tier hints
│   │   ├── ScoreDisplay.tsx            # Score bar
│   │   ├── CompletionScreen.tsx        # End-game stats
│   │   └── visualizers/
│   │       ├── ArrayVisualizer.tsx      # Bar chart + cells
│   │       ├── GraphVisualizer.tsx      # SVG nodes + edges
│   │       ├── TreeVisualizer.tsx       # Hierarchical BST
│   │       ├── DPTableVisualizer.tsx    # Grid cells + deps
│   │       ├── StackVisualizer.tsx      # Vertical LIFO
│   │       └── LinkedListVisualizer.tsx # Horizontal chain
│   └── data/
│       ├── index.ts                    # Re-exports all demos
│       ├── bubbleSortDemo.ts           # Array, 20 steps
│       ├── binarySearchDemo.ts         # Array, 10 steps
│       ├── insertionSortDemo.ts        # Array, 15 steps
│       ├── bfsDemo.ts                  # Graph, 12 steps
│       ├── bstInsertDemo.ts            # Tree, 12 steps
│       ├── fibonacciDPDemo.ts          # DP Table, 11 steps
│       ├── validParenthesesDemo.ts     # Stack, 10 steps
│       └── reverseLinkedListDemo.ts    # Linked List, 11 steps
├── components/templates/
│   ├── CodeDisplay.tsx                 # Shared — syntax-highlighted code
│   ├── VariableTracker.tsx             # Shared — variable state sidebar
│   └── StepControls.tsx                # Shared — prev/next/play/pause/speed
└── app/
    ├── demo/state-tracer/page.tsx      # Demo hub page (algorithm selector grid)
    └── game/[id]/page.tsx              # Game router (templateType === 'ALGORITHM_GAME')
```

### 7.4 Routing

The game page at `/game/[id]` fetches a blueprint from the backend. When `blueprint.templateType === 'ALGORITHM_GAME'`, it renders `StateTracerGame` with the blueprint data and the current theme.

The demo page at `/demo/state-tracer` shows a grid of 8 algorithm cards. Clicking a card loads the hardcoded demo data directly (no backend call).

---

## 8. Backend Generation Requirements

To generate a `StateTracerBlueprint` for an arbitrary algorithm, the backend needs to:

### 8.1 Inputs

- **Topic/question text** from the user (e.g., "Teach me how BFS works")
- **Algorithm selection** (could be inferred from topic, or explicitly chosen)
- **Difficulty level** (determines step count and prediction density)

### 8.2 Generation Pipeline

1. **Select algorithm template** — code string, data structure type, variable names
2. **Generate input data** — appropriate test case for the algorithm (e.g., a graph for BFS, an array for sorting)
3. **Simulate execution** — run the algorithm step-by-step, capturing:
   - Variable state snapshots at each step
   - Data structure state (elements, highlights, node states, etc.)
   - Which code line is executing
4. **Insert predictions** — at pedagogically interesting steps:
   - Comparison results → multiple choice
   - Computed values → value prediction
   - Array state after operation → arrangement
   - "Which elements are affected?" → multi-select
5. **Generate hints** — 3-tier per prediction step (nudge → clue → answer)
6. **Generate explanations** — per step, explaining what happened and why
7. **Assemble blueprint** — combine into `StateTracerBlueprint` JSON

### 8.3 Quality Criteria for Generated Data

- **Step count:** 8-25 steps depending on algorithm complexity
- **Prediction density:** ~60-80% of steps should have predictions (rest are auto-advance for setup/transitions)
- **Prediction type mix:** At least 2 different prediction types per game. Value and MC should dominate; arrangement and multi-select at key moments.
- **Variable tracking:** Must capture ALL relevant variables. `changedVariables` must be accurate — the frontend uses it for highlight animations.
- **Data structure states:** Must accurately reflect algorithm state at each step. Highlights/node states must match what the step describes.
- **Code line accuracy:** `codeLine` must point to the actual line being executed in the `code` string.
- **Hint quality:** Tier 1 should be vague, tier 2 should narrow it down, tier 3 should essentially give the answer.
- **Graph node positions:** Must be pre-computed. The frontend does NOT auto-layout graphs.

---

## 9. Existing Demo Data (Reference)

The 8 demo files serve as gold-standard examples for backend generation:

| Demo | File | DS Type | Steps | Predictions | Line Count |
|------|------|---------|-------|-------------|------------|
| Bubble Sort | `bubbleSortDemo.ts` | array | 20 | 16 | 633 |
| Binary Search | `binarySearchDemo.ts` | array | 10 | 9 | 380 |
| Insertion Sort | `insertionSortDemo.ts` | array | 15 | 13 | 545 |
| BFS | `bfsDemo.ts` | graph | 12 | 9 | 577 |
| BST Insert | `bstInsertDemo.ts` | tree | 12 | 10 | 439 |
| Fibonacci DP | `fibonacciDPDemo.ts` | dp_table | 11 | 9 | 442 |
| Valid Parens | `validParenthesesDemo.ts` | stack | 10 | 8 | 328 |
| Reverse LL | `reverseLinkedListDemo.ts` | linked_list | 11 | 9 | 433 |

These files are the most authoritative reference for the expected data format. When building backend generation, use them as test fixtures — the generated output should be structurally identical.
