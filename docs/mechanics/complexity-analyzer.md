# Complexity Analyzer — Mechanic Specification

> **Status:** Frontend complete (8 demos, quiz-based). Backend generation not yet implemented.
> **Template type:** `ALGORITHM_GAME`
> **Entry point:** `frontend/src/components/templates/AlgorithmGame/ComplexityAnalyzerGame.tsx`

---

## 1. What It Does

Complexity Analyzer is a **Big-O analysis** mechanic where students determine the time complexity of algorithms through three challenge types:

1. **Identify from Code** — Read a code snippet and select the correct Big-O complexity
2. **Infer from Growth Data** — Analyze a table/chart of input sizes vs operation counts to deduce the growth rate
3. **Find Bottleneck** — Given multi-section code, identify which section dominates and determine the overall complexity

The student must:
1. Analyze code structure (loops, recursion, data structures)
2. Recognize growth patterns from empirical data
3. Compare complexities across code sections to find bottlenecks
4. Select the correct Big-O class from multiple options

**Bloom Level:** Analyze → Evaluate
**Naps Taxonomy Level:** Analyzing
**Compared to traditional complexity teaching:** Interactive analysis with immediate feedback, visual growth data, progressive hint system

---

## 2. Pedagogical Design

### 2.1 Why Three Challenge Types

Each challenge type targets a different complexity analysis skill:

- **Code analysis** builds the fundamental skill of mapping code patterns (nested loops, divide-and-conquer, traversals) to Big-O classes
- **Growth data inference** teaches students to recognize complexity empirically — the same skill used when profiling real applications
- **Bottleneck identification** teaches the practical skill of finding performance-critical code sections, essential for optimization work

### 2.2 Common Complexity Classes Covered

| Class | Pattern | Example |
|-------|---------|---------|
| O(1) | Constant — direct access | Hash table lookup |
| O(log n) | Halving — divide and conquer | Binary search |
| O(n) | Single traversal | Linear search, linked list reversal |
| O(n log n) | Divide + linear merge | Merge sort, Timsort |
| O(n²) | Nested traversal | Bubble sort, insertion sort (worst) |
| O(2ⁿ) | Exponential branching | Naive recursive Fibonacci |

### 2.3 Growth Data as Teaching Tool

Growth data challenges bypass code reading and focus on pattern recognition:
- **Linear**: operations scale 1:1 with input (100→100, 500→500)
- **Quadratic**: doubling n quadruples operations (10→45, 20→190)
- **Logarithmic**: operations grow by ~3 per 10x increase in n (10→4, 100→7, 1000→10)
- **Exponential**: each +5 in n multiplies operations by ~11x

Students learn to identify these patterns from data before seeing the code.

### 2.4 Bottleneck Analysis

Real-world complexity analysis requires identifying which part of a program dominates runtime. Bottleneck challenges teach:
- **Additive rule**: O(f) + O(g) = O(max(f, g))
- **Section independence**: Two O(n) sections are still O(n) overall
- **Preprocessing costs**: Sorting + searching = O(n log n) + O(log n) = O(n log n)

---

## 3. Blueprint Data Contract

```typescript
type ComplexityChallengeType =
  | 'identify_from_code'
  | 'infer_from_growth'
  | 'find_bottleneck';

interface CodeSection {
  sectionId: string;
  label: string;           // "Section A: Sort"
  startLine: number;
  endLine: number;
  complexity: string;       // "O(n log n)"
  isBottleneck: boolean;
}

interface ComplexityChallenge {
  challengeId: string;
  type: ComplexityChallengeType;
  title: string;
  description?: string;
  code?: string;            // For code-based challenges
  language?: string;        // "python"
  growthData?: {            // For growth-based challenges
    inputSizes: number[];
    operationCounts: number[];
  };
  codeSections?: CodeSection[];  // For bottleneck challenges
  correctComplexity: string;     // "O(n log n)"
  options: string[];             // ["O(1)", "O(log n)", "O(n)", ...]
  explanation: string;           // Shown after answer
  points: number;
  hints: [string, string, string];
}

interface ComplexityAnalyzerBlueprint {
  algorithmName: string;
  algorithmDescription: string;
  challenges: ComplexityChallenge[];
}
```

---

## 4. Scoring System

| Event | Points |
|-------|--------|
| Correct answer (no hints) | Full challenge points (100-150) |
| Correct with 1 hint | 70% of points |
| Correct with 2 hints | 40% of points |
| Correct with 3 hints | 10% of points |
| Incorrect answer | 0 |
| Bonus: All challenges perfect | +150 |
| Bonus: No hints used | +50 |

**Hint penalty**: 30% per hint tier, applied multiplicatively to base points.

**Max possible**: Sum of all challenge points + 200 (bonuses).

---

## 5. Validation Rules

- **Code challenges**: Selected answer must exactly match `correctComplexity`
- **Growth data challenges**: Selected answer must match `correctComplexity`
- **Bottleneck challenges**: Both the selected section (`selectedSection === bottleneck.sectionId`) AND the selected complexity must be correct
- **Single attempt per challenge**: No retry — answer is graded immediately, then student moves to next

---

## 6. Hint System

Uses the existing `HintSystem` component with per-challenge 3-tier progressive hints:

| Tier | Penalty | Typical Content |
|------|---------|-----------------|
| 1 — Nudge | -30% | General approach hint |
| 2 — Clue | -30% | Specific pattern identification |
| 3 — Answer | -30% | Near-direct answer |

Each challenge has its own hint set. Hints are cumulative (revealing tier 2 also shows tier 1).

---

## 7. State Machine

```
INIT → (START) → CHALLENGE → (SUBMIT) → FEEDBACK → (NEXT_CHALLENGE) →
  ├── more challenges → CHALLENGE
  └── all done → COMPLETED
```

### Phases

| Phase | Description |
|-------|-------------|
| `INIT` | Algorithm name, description, challenge count, start button |
| `CHALLENGE` | Code/growth panel + option grid + hints |
| `FEEDBACK` | Correct/incorrect indicator + explanation + next button |
| `COMPLETED` | Score circle, per-challenge breakdown, bonuses, play again |

### Actions

| Action | Trigger |
|--------|---------|
| `START` | Click "Start Analysis" |
| `SELECT_ANSWER` | Click a Big-O option |
| `SELECT_SECTION` | Click a code section (bottleneck type only) |
| `SUBMIT` | Click "Submit Answer" |
| `NEXT_CHALLENGE` | Click "Next Challenge" or "See Results" |
| `USE_HINT` | Request progressive hint |
| `CA_COMPLETE` | Force completion |
| `CA_RESET` | Click "Play Again" |

---

## 8. Visual Components

### Layout

```
┌──────────────────────────────────────────────────┐
│  Challenge 2/3        [Code Analysis]     Score: 150│
│  ═══════════════════════════════  (progress bar)   │
├──────────────────────────────────────────────────┤
│  Challenge Title                                   │
│  Description text                                  │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │  1  def binary_search(arr, target):         │  │
│  │  2      left, right = 0, len(arr) - 1       │  │
│  │  3      while left <= right:          [Sort] │  │
│  │  ...                                        │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  What is the time complexity?                      │
│  ┌────────┐ ┌────────┐ ┌──────────┐              │
│  │  O(1)  │ │O(log n)│ │   O(n)   │              │
│  └────────┘ └────────┘ └──────────┘              │
│  ┌──────────┐ ┌────────┐ ┌────────┐              │
│  │O(n log n)│ │ O(n²)  │ │ O(2ⁿ)  │              │
│  └──────────┘ └────────┘ └────────┘              │
│                                                    │
│  [Hints]                         [Submit Answer]   │
└──────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | File | Description |
|-----------|------|-------------|
| `ComplexityAnalyzerGame` | `ComplexityAnalyzerGame.tsx` | Main game — phase rendering, challenge progression |
| `ComplexityCodePanel` | `components/ComplexityCodePanel.tsx` | Code display with line numbers + section highlighting |
| `GrowthDataPanel` | `components/GrowthDataPanel.tsx` | SVG line chart + data table |
| `ComplexityOptionGrid` | `components/ComplexityOptionGrid.tsx` | Grid of Big-O option buttons with feedback states |
| `HintSystem` | `components/HintSystem.tsx` | Reused from State Tracer |

### Feedback Visualization

| State | Color | Meaning |
|-------|-------|---------|
| Selected | Blue ring | Currently selected option |
| Correct | Green ring | Right answer (shown in feedback) |
| Incorrect (selected) | Red ring | Wrong answer chosen |
| Dimmed | Gray | Unselected options during feedback |
| Bottleneck correct | Green background | Correctly identified bottleneck section |
| Bottleneck wrong | Red background | Wrong section selected |

---

## 9. Frontend Architecture

### File Tree

```
AlgorithmGame/
├── ComplexityAnalyzerGame.tsx              # Main game component
├── types.ts                                # Types (appended)
├── hooks/
│   └── useComplexityAnalyzerMachine.ts    # useReducer state machine
├── components/
│   ├── ComplexityCodePanel.tsx             # Code with section highlighting
│   ├── GrowthDataPanel.tsx                # SVG chart + table
│   ├── ComplexityOptionGrid.tsx           # Big-O option buttons
│   └── HintSystem.tsx                     # Reused from State Tracer
├── data/
│   ├── complexityAnalyzerBinarySearch.ts
│   ├── complexityAnalyzerBubbleSort.ts
│   ├── complexityAnalyzerBFS.ts
│   ├── complexityAnalyzerFibonacci.ts
│   ├── complexityAnalyzerLinkedList.ts
│   ├── complexityAnalyzerStack.ts
│   ├── complexityAnalyzerBST.ts
│   ├── complexityAnalyzerInsertionSort.ts
│   └── complexityAnalyzerIndex.ts         # Registry of all demos
└── (demo page at app/demo/complexity-analyzer/page.tsx)
```

### Challenge Flow

1. `useComplexityAnalyzerMachine` manages phase transitions and scoring
2. `ComplexityAnalyzerGame` renders the current challenge based on phase
3. For `identify_from_code`: shows `ComplexityCodePanel` + `ComplexityOptionGrid`
4. For `infer_from_growth`: shows `GrowthDataPanel` + `ComplexityOptionGrid`
5. For `find_bottleneck`: shows `ComplexityCodePanel` (with clickable sections) + `ComplexityOptionGrid`
6. On submit, the reducer grades the answer and transitions to FEEDBACK
7. FEEDBACK shows explanation + correct answer highlighting
8. After all challenges, bonuses computed and COMPLETED shown

---

## 10. Backend Generation Requirements

### Inputs
- Algorithm name or topic
- Target language (Python/JavaScript)
- Difficulty level (controls challenge types and complexity classes)

### Generation Pipeline

1. **Select algorithm** — Match to known algorithm or generate novel
2. **Write reference implementation** — Clean code with comments
3. **Determine complexity** — Analyze the code to compute correct Big-O
4. **Generate challenges** — 2-3 challenges per algorithm:
   - At least one `identify_from_code` with the main implementation
   - One `infer_from_growth` with computed operation counts
   - One `find_bottleneck` if the algorithm has distinct phases
5. **Generate growth data** — Run the algorithm on increasing input sizes, count operations
6. **Create hints** — 3-tier progressive hints per challenge
7. **Write explanations** — Educational explanations for each answer

### Quality Criteria

- [ ] Each challenge has exactly one correct answer
- [ ] Growth data is mathematically consistent with the stated complexity
- [ ] Code sections in bottleneck challenges have clearly different complexities
- [ ] Options include the correct answer plus 3-5 plausible alternatives
- [ ] Explanations teach the reasoning, not just state the answer
- [ ] Hints progress from general approach to specific pattern to near-answer

---

## 11. 8 Demo Games

| # | Algorithm | Challenges | Types | Max Points |
|---|-----------|-----------|-------|------------|
| 1 | Binary Search | 3 | code, growth, bottleneck | 550 |
| 2 | Bubble Sort | 3 | code (worst), growth, code (best) | 500 |
| 3 | BFS | 3 | code, growth (complete graph), bottleneck | 550 |
| 4 | Fibonacci (DP) | 3 | code (naive), code (DP), growth (naive) | 500 |
| 5 | Linked List Reversal | 3 | code, growth, bottleneck | 550 |
| 6 | Valid Parentheses | 3 | code, growth, bottleneck | 550 |
| 7 | BST Insert | 3 | code (avg), code (worst), growth | 500 |
| 8 | Insertion Sort | 3 | code (worst), code (best), growth | 500 |

### Example: Binary Search

**Challenge 1 — Code Analysis (100 pts):**
Shows `binary_search()` implementation. Student selects from O(1), O(log n), O(n), O(n log n), O(n²). Correct: O(log n).

**Challenge 2 — Growth Data (100 pts):**
Table: n=[10, 100, 1K, 10K, 100K, 1M], ops=[4, 7, 10, 14, 17, 20]. Student recognizes logarithmic growth.

**Challenge 3 — Bottleneck (150 pts):**
`search_with_sort()` has Section A (sort, O(n log n)) and Section B (binary search, O(log n)). Student must click Section A AND select O(n log n).

---

## 12. Comparison with Other Mechanics

| Aspect | State Tracer | Bug Hunter | Algorithm Builder | Complexity Analyzer |
|--------|-------------|------------|-------------------|---------------------|
| **Bloom Level** | Understand | Analyze | Apply → Create | Analyze → Evaluate |
| **Student Action** | Predict state | Find + fix bugs | Arrange blocks | Classify complexity |
| **Interaction** | Click/type | Click lines, fix | Drag-and-drop | Click options/sections |
| **Challenge types** | 1 (step-through) | 1 (bug finding) | 1 (ordering) | 3 (code/growth/bottleneck) |
| **Time per game** | 5-15 min | 3-10 min | 3-8 min | 3-8 min |
| **Backend complexity** | High (traces) | Medium (bugs) | Low (decompose) | Medium (growth data) |

---

## 13. Research Sources

- Cormen, T. et al. (2009). Introduction to Algorithms — Big-O notation, complexity analysis
- Sedgewick, R. & Wayne, K. (2011). Algorithms, 4th Ed — Growth rate analysis
- McConnell, J. (2001). Analysis of Algorithms — Empirical vs. analytical complexity
- CS Unplugged: Algorithmic thinking activities for complexity education
