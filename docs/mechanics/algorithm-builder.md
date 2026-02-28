# Algorithm Builder (Parsons Problems) — Mechanic Specification

> **Status:** Frontend complete (8 demos, DnD-based). Backend generation not yet implemented.
> **Template type:** `ALGORITHM_GAME`
> **Entry point:** `frontend/src/components/templates/AlgorithmGame/AlgorithmBuilderGame.tsx`

---

## 1. What It Does

Algorithm Builder is a **Parsons Problems** mechanic where students construct an algorithm by **dragging scrambled code blocks into the correct order**. Blocks include distractors (wrong code that should not be used) mixed in with the correct lines.

The student must:
1. Identify which blocks belong in the solution (exclude distractors)
2. Arrange them in the correct order
3. Set the correct indentation level for each block (Python)
4. Submit and receive per-block feedback

**Bloom Level:** Apply → Create
**Naps Taxonomy Level:** Constructing
**Compared to code writing:** Same learning outcomes, ~50% less time (Parsons Problems research)

---

## 2. Pedagogical Design

### 2.1 Parsons Problems Research

Parsons Problems (originally Parsons & Haden, 2006) present learners with scrambled code that must be reordered. Key findings:

- **2D Parsons** (order + indentation) are as effective as code writing but take half the time
- **Distractors** increase difficulty and promote deeper analysis — students must distinguish correct from plausible-but-wrong code
- **Indentation as learning** — Python's indentation represents scope; making students set it explicitly teaches code structure

### 2.2 Distractor Rationale

Each distractor is a plausible alternative that contains a common bug:
- Off-by-one errors (`while left < right:` vs `while left <= right:`)
- Wrong operator (`/` vs `//`, `>` vs `>=`)
- Wrong variable reference (`curr.next = curr` vs `curr.next = prev`)
- Missing guard checks (popping without empty check)

Distractors are visually identical to correct blocks — students must analyze semantics, not syntax.

---

## 3. Blueprint Data Contract

```typescript
interface AlgorithmBuilderBlueprint {
  algorithmName: string;           // "Binary Search"
  algorithmDescription: string;    // One-liner description
  problemDescription: string;      // Task prompt shown to student
  language: string;                // "python"
  correct_order: ParsonsBlock[];   // Blocks in correct order
  distractors: ParsonsBlock[];     // Wrong blocks to exclude
  config: AlgorithmBuilderConfig;
  hints: [string, string, string]; // 3-tier progressive hints
  test_cases?: AlgorithmBuilderTestCase[];
}

interface ParsonsBlock {
  id: string;
  code: string;                    // The code text
  indent_level: number;            // Expected indentation (0-3)
  is_distractor: boolean;
  distractor_explanation?: string; // Why this block is wrong
  group_id?: string;               // Interchangeable blocks share group_id
}

interface AlgorithmBuilderConfig {
  indentation_matters: boolean;    // Grade on indent (2D Parsons)
  max_attempts: number | null;     // null = unlimited
  show_line_numbers: boolean;      // Show numbers in solution panel
  allow_indent_adjustment: boolean; // Show indent +/- controls
}

interface AlgorithmBuilderTestCase {
  id: string;
  inputDescription: string;
  expectedOutput: string;
  explanation?: string;
}
```

---

## 4. Scoring System

| Event | Points |
|-------|--------|
| Perfect first attempt | 300 |
| With resubmissions | `300 * 0.8^(attempts-1)` |
| Block in correct position + indent | +30 |
| Block in correct position, wrong indent | +15 |
| Distractor correctly excluded | +20 |
| Distractor incorrectly included | -30 |
| Hint used | -40 per hint |
| Bonus: perfect first try | +50 |

**Final score** = `max(per_block_total, attempt_score) - hint_penalty + bonuses`

---

## 5. Validation Rules

- **Order check:** Each block's index in the solution must match `correct_order[i].id`
- **Indent check:** (if `indentation_matters`) Block's `indent_level` must match expected
- **Distractor check:** All distractor blocks should remain in the source panel
- **group_id interchangeability:** Blocks sharing the same `group_id` can occupy each other's positions
- **Partial grading:** Per-block feedback is always computed, even for incomplete solutions

---

## 6. Hint System

Uses the existing `HintSystem` component with 3-tier progressive hints:

| Tier | Penalty | Typical Content |
|------|---------|-----------------|
| 1 — Nudge | -40 | General structural hint |
| 2 — Clue | -40 | Specific section ordering |
| 3 — Answer | -40 | Full correct order description |

Maximum 3 hints per game, -120 points total if all used.

---

## 7. State Machine

```
INIT → (START_BUILDING) → BUILDING → (SUBMIT) →
  if all correct → COMPLETED
  if errors → FEEDBACK_SHOWN → (RETRY) → BUILDING
```

### Phases

| Phase | Description |
|-------|-------------|
| `INIT` | Show problem description, metadata, start button |
| `BUILDING` | Main DnD phase — drag blocks between source and solution |
| `FEEDBACK_SHOWN` | Per-block feedback displayed (green/orange/yellow/red) |
| `COMPLETED` | Score summary, bonuses, play again |

### Actions

| Action | Trigger |
|--------|---------|
| `START_BUILDING` | Click "Start Building" — shuffles and distributes blocks |
| `MOVE_BLOCK_TO_SOLUTION` | Drop block from source onto solution panel |
| `MOVE_BLOCK_TO_SOURCE` | Drop block from solution back to source |
| `REORDER_SOLUTION` | Reorder blocks within solution panel |
| `SET_INDENT` | Click +/- indent controls |
| `SUBMIT` | Click "Submit Solution" — grades and shows feedback |
| `RETRY` | Click "Try Again" from feedback view |
| `USE_HINT` | Request progressive hint |
| `RESET` | Click "Play Again" from completed view |

---

## 8. Visual Components

### Layout (two-column)

```
┌─────────────────────────────────────────────────┐
│  Algorithm Name — Algorithm Builder              │
│  Problem description text                        │
├────────────────────┬────────────────────────────┤
│  Available Blocks  │  Your Solution (N/M)       │
│  ┌──────────────┐  │  ┌──1  ─────────────────┐  │
│  │ code block   │  │  │ def func():          │  │
│  └──────────────┘  │  └─────────────────────┘  │
│  ┌──────────────┐  │  ┌──2  ─────────────────┐  │
│  │ distractor   │  │  │   body line      ←→  │  │
│  └──────────────┘  │  └─────────────────────┘  │
│  ...               │  (drag blocks here)        │
├────────────────────┴────────────────────────────┤
│  [Hints]                        [Submit Solution]│
└─────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | File | Description |
|-----------|------|-------------|
| `AlgorithmBuilderGame` | `AlgorithmBuilderGame.tsx` | Main game — DndContext, phase rendering |
| `SourcePanel` | `components/SourcePanel.tsx` | Left panel with available blocks |
| `SolutionPanel` | `components/SolutionPanel.tsx` | Right panel with drop zones + line numbers |
| `SortableCodeBlock` | `components/SortableCodeBlock.tsx` | Individual draggable code block |
| `IndentControls` | `components/IndentControls.tsx` | +/- buttons for indent adjustment |
| `HintSystem` | `components/HintSystem.tsx` | Reused from State Tracer |

### Feedback Visualization

| Status | Color | Icon | Meaning |
|--------|-------|------|---------|
| `correct` | Green | ✓ | Right block, right position, right indent |
| `wrong_position` | Orange | ↕ | Correct block but wrong position |
| `wrong_indent` | Yellow | ↔ | Right position but wrong indentation |
| `distractor_included` | Red | ✗ | Distractor used (with tooltip explanation) |
| `distractor_excluded` | Light green | ✓ | Correctly left in source |
| `missing` | Light red | ! | Correct block still in source |

---

## 9. Frontend Architecture

### File Tree

```
AlgorithmGame/
├── AlgorithmBuilderGame.tsx           # Main game component
├── types.ts                           # Types (appended)
├── hooks/
│   ├── useAlgorithmBuilderMachine.ts  # useReducer state machine
│   └── useAlgorithmBuilderScoring.ts  # Grading + score summary
├── components/
│   ├── SortableCodeBlock.tsx          # Draggable code block
│   ├── SourcePanel.tsx                # Available blocks container
│   ├── SolutionPanel.tsx              # Solution build container
│   ├── IndentControls.tsx             # Indent +/- buttons
│   └── HintSystem.tsx                 # Reused from State Tracer
├── data/
│   ├── algorithmBuilderBinarySearch.ts
│   ├── algorithmBuilderBubbleSort.ts
│   ├── algorithmBuilderBFS.ts
│   ├── algorithmBuilderFibonacci.ts
│   ├── algorithmBuilderLinkedList.ts
│   ├── algorithmBuilderStack.ts
│   ├── algorithmBuilderBST.ts
│   ├── algorithmBuilderInsertionSort.ts
│   └── algorithmBuilderIndex.ts       # Registry of all demos
└── (demo page at app/demo/algorithm-builder/page.tsx)
```

### DnD Wiring

- **Library:** `@dnd-kit/core` + `@dnd-kit/sortable` (already in package.json)
- **Approach:** Single `DndContext` wrapping two `SortableContext`s + `useDroppable` containers
- **Cross-container:** Detected in `onDragEnd` by comparing active vs over container
- **Same-container reorder:** `SortableContext` handles visual animation; `onDragEnd` commits reorder
- **DragOverlay:** Floating preview of the active block during drag
- **Sensors:** `PointerSensor` (5px activation distance) + `KeyboardSensor`

---

## 10. Backend Generation Requirements

### Inputs
- Algorithm name or topic
- Target language (Python/JavaScript/pseudocode)
- Difficulty level (controls number of distractors)

### Generation Pipeline

1. **Select algorithm** — Match to known algorithm or generate novel
2. **Decompose into blocks** — Split correct implementation into logical lines
3. **Assign indentation** — Set correct indent_level per block
4. **Create distractors** — Generate 2-3 plausible-but-wrong alternatives per algorithm
5. **Generate hints** — 3-tier progressive hints (structural → specific → answer)
6. **Create test cases** — Optional verification test cases

### Quality Criteria

- [ ] Each distractor targets a specific, common bug pattern
- [ ] Distractor explanations are educational (explain WHY it's wrong)
- [ ] Correct block count: 8-14 per algorithm
- [ ] Distractor count: 2-3 per algorithm
- [ ] Hints progress from vague to specific
- [ ] Code is syntactically valid (even distractors compile individually)

---

## 11. 8 Demo Games

| # | Algorithm | Correct | Distractors | Difficulty |
|---|-----------|---------|-------------|------------|
| 1 | Binary Search | 11 | 3 | Easy |
| 2 | Bubble Sort (optimized) | 11 | 2 | Easy |
| 3 | BFS | 14 | 3 | Medium |
| 4 | Fibonacci DP | 9 | 2 | Easy |
| 5 | Reverse Linked List | 9 | 2 | Medium |
| 6 | Valid Parentheses (Stack) | 11 | 2 | Medium |
| 7 | BST Insert | 8 | 2 | Medium |
| 8 | Insertion Sort | 9 | 2 | Easy |

### Example: Binary Search

**Problem:** "Build a binary search function that returns the index of target in a sorted array arr, or -1 if not found."

**Correct blocks (11):**
```python
def binary_search(arr, target):       # indent 0
    left, right = 0, len(arr) - 1     # indent 1
    while left <= right:               # indent 1
        mid = (left + right) // 2     # indent 2
        if arr[mid] == target:         # indent 2
            return mid                 # indent 3
        elif arr[mid] < target:        # indent 2
            left = mid + 1             # indent 3
        else:                          # indent 2
            right = mid - 1            # indent 3
    return -1                          # indent 1
```

**Distractors (3):**
- `while left < right:` — Missing `=` skips single-element check
- `mid = (left + right) / 2` — Float division, not integer
- `left = mid` — Causes infinite loop (must be mid+1)

---

## 12. Comparison with State Tracer & Bug Hunter

| Aspect | State Tracer | Bug Hunter | Algorithm Builder |
|--------|-------------|------------|-------------------|
| **Bloom Level** | Understand | Analyze | Apply → Create |
| **Student Action** | Predict next state | Find + fix bugs | Construct from blocks |
| **Interaction** | Click/type predictions | Click lines, fix code | Drag-and-drop, indent |
| **Time per game** | 5-15 min | 3-10 min | 3-8 min |
| **Backend complexity** | High (execution trace) | Medium (bug injection) | Low (decompose code) |
| **Distractors** | N/A | Red herrings | Wrong code blocks |
| **Feedback timing** | After each step | After each bug | After full submission |

---

## 13. Research Sources

- Parsons, D. & Haden, P. (2006). Parsons Programming Puzzles: A Fun and Effective Learning Tool
- Ericson, B. et al. (2022). 2D Parsons Problems with Distractors (ACM SIGCSE)
- js-parsons library: https://js-parsons.github.io/
- Runestone Interactive: https://runestone.academy/
- Google Blockly: https://developers.google.com/blockly
