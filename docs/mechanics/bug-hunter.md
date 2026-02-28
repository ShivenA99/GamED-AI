# Bug Hunter — Mechanic Specification

> **Status:** Frontend implemented with 8 demos. Backend generation not yet wired.
> **Template type:** `BUG_HUNTER`
> **Entry point:** `frontend/src/components/templates/AlgorithmGame/BugHunterGame.tsx`
> **Demo page:** `/demo/bug-hunter`

---

## 1. What It Does

Bug Hunter presents the student with algorithm code containing **deliberate bugs**. The student must:

1. **Read** the buggy code and observe failing test cases
2. **Locate** the buggy line by clicking on it
3. **Diagnose** what type of bug it is
4. **Fix** it by selecting or typing the correct replacement
5. **Verify** the fix runs correctly on all test cases

Unlike State Tracer (which teaches "how does this algorithm work?"), Bug Hunter teaches **"what can go wrong and why?"** — the analytical/evaluative tier of Bloom's taxonomy.

The mechanic is algorithm-agnostic. The same React components render bugs in sorting algorithms, graph traversals, DP problems, etc. Only the blueprint data changes.

---

## 2. Pedagogical Design

### 2.1 Research-Backed Principles

These decisions are grounded in CS education research (see Section 10 for sources):

| Principle | Implementation | Source |
|-----------|---------------|--------|
| **Output-first framing** | Show failing test case BEFORE the code. Students learn to compare expected vs actual before reading code. | Python Tutor, Codecademy |
| **Constrained search** | Sequential bug reveal narrows focus to one bug at a time. Reduces cognitive load. | O'Rourke et al. scaffolding study |
| **Explanation requirement** | After clicking a line, student must pick WHY it's wrong (bug type) before fixing. Prevents lucky guessing. | Rubber duck debugging pedagogy |
| **Red herring feedback** | Clicking a correct line shows specific feedback ("This line is correct because...") — teaches through misconceptions. | Gidget design principles |
| **Productive failure** | Wrong fixes run and show their broken output. Seeing WHY a wrong fix fails is as educational as finding the right fix. | Productive failure research |
| **No time pressure** | Thinking > speed for debugging. No timer in standard mode. | Cognitive load theory |

### 2.2 Bug Type Difficulty Progression

| Level | Bug Type | Example | Cognitive Demand |
|-------|----------|---------|-----------------|
| 1 (Easy) | `off_by_one` | `i < n` vs `i <= n` | Pattern recognition |
| 1 (Easy) | `wrong_initialization` | `left = 1` vs `left = 0` | Value checking |
| 2 (Medium) | `wrong_operator` | `<` vs `<=`, `+` vs `-` | Semantic reasoning |
| 2 (Medium) | `wrong_variable` | Using `i` instead of `j` | Scope awareness |
| 2 (Medium) | `wrong_return` | Returning `left` vs `mid` | Flow tracing |
| 3 (Hard) | `missing_base_case` | Recursion without termination | Structural analysis |
| 3 (Hard) | `infinite_loop` | Missing increment / wrong exit condition | Execution modeling |
| 3 (Hard) | `logic_error` | Algorithm is wrong, not just a typo | Deep understanding |
| 3 (Hard) | `boundary_error` | Not handling empty input / single element | Edge case thinking |

---

## 3. Blueprint Data Contract

The backend must produce a single JSON object conforming to `BugHunterBlueprint`:

```typescript
interface BugHunterBlueprint {
  algorithmName: string;              // "Binary Search"
  algorithmDescription: string;       // One-liner
  narrativeIntro: string;             // Context: "This binary search has a subtle bug..."
  language: string;                   // "python"

  buggyCode: string;                  // Full source code WITH bugs (displayed to student)
  correctCode: string;                // Full correct code (used for verification display)

  bugs: BugDefinition[];              // Ordered by difficulty — revealed sequentially
  testCases: TestCase[];              // Input/output pairs demonstrating failures
  redHerrings: RedHerring[];          // Feedback for commonly-clicked wrong lines

  config: BugHunterConfig;
}
```

### 3.1 BugDefinition

Each bug represents one deliberate error in the code:

```typescript
interface BugDefinition {
  bugId: string;                      // Unique identifier, e.g. "bug-1"
  lineNumber: number;                 // 1-indexed line in buggyCode
  buggyLineText: string;             // The incorrect line (for display in fix panel)
  correctLineText: string;           // The correct replacement

  bugType: BugType;                   // Classification (see enum below)
  difficulty: 1 | 2 | 3;             // 1=easy, 2=medium, 3=hard

  explanation: string;                // WHY this is wrong, shown after correct fix
  bugTypeExplanation: string;         // What this bug type means in general

  fixOptions: FixOption[];            // 3-4 replacement line choices
  hints: [string, string, string];    // [category, location, line] — 3-tier
}

type BugType =
  | 'off_by_one'
  | 'wrong_operator'
  | 'wrong_variable'
  | 'missing_base_case'
  | 'wrong_initialization'
  | 'wrong_return'
  | 'infinite_loop'
  | 'boundary_error'
  | 'logic_error';

interface FixOption {
  id: string;                         // "fix-a", "fix-b", etc.
  codeText: string;                   // The replacement line
  isCorrect: boolean;                 // Is this the right fix?
  feedback: string;                   // Shown when selected: why right/wrong
}
```

**Fix option design rules:**
- Always 3-4 options
- Exactly 1 correct option
- Wrong options should be **plausible** — common mistakes or partial fixes
- Each wrong option's `feedback` explains WHY it doesn't work (educational)

### 3.2 TestCase

```typescript
interface TestCase {
  id: string;                         // "test-1"
  inputDescription: string;           // "arr = [1, 3, 5, 7, 9], target = 9"
  expectedOutput: string;             // "4"
  buggyOutput: string;                // "-1" (what the buggy code returns)
  exposedBugs: string[];              // ["bug-1"] — which bugs this test exposes
}
```

**Test case design rules:**
- At least 2 test cases per game
- At least 1 test case should PASS (buggy code works for some inputs) — this teaches that bugs are subtle
- At least 1 test case should FAIL per bug — the failing output demonstrates the bug
- `exposedBugs` links tests to bugs: when a bug is fixed, its exposed tests should turn green

### 3.3 RedHerring

```typescript
interface RedHerring {
  lineNumber: number;                 // Line the student might mistakenly click
  feedback: string;                   // "This line correctly computes mid. The issue is elsewhere."
}
```

**Red herring design rules:**
- Include 2-4 red herrings per game
- Focus on lines that LOOK suspicious but are correct (e.g., integer division, complex conditions)
- The `feedback` should be educational — explain WHY the line is correct

### 3.4 BugHunterConfig

```typescript
interface BugHunterConfig {
  revealSequentially: boolean;        // true = one bug at a time (recommended)
  showTestOutput: boolean;            // true = show expected vs buggy output
  showRunButton: boolean;             // true = let student "run" code mentally or see output
  fixMode: 'multiple_choice';        // Always MC for v1 (free_text deferred)
  maxWrongLineClicks: number;         // Max wrong clicks before penalty caps (default: 10)
}
```

For v1 we only implement `fixMode: 'multiple_choice'`. Free-text code entry requires AST normalization which is a later enhancement.

---

## 4. Scoring System

### 4.1 Per-Bug Scoring

```
Base points per bug:
  Correct line + correct fix, 1st attempt:  +150
  Correct line + correct fix, 2nd attempt:  +100
  Correct line + correct fix, 3rd+ attempt: +50

Difficulty multiplier:
  Easy (1):   1.0x
  Medium (2): 1.5x
  Hard (3):   2.0x

Penalties:
  Wrong line clicked:           -10 per click
  Wrong fix submitted:          -20 per wrong fix (per bug)
  Hint used (category):         -15% of bug points
  Hint used (location):         -30% of bug points
  Hint used (line):             -50% of bug points

Bonuses:
  All bugs found:               +100
  No wrong line clicks:         +50
  No hints used:                +75 (clean sweep bonus)

Final score = sum(bug_points * difficulty_multiplier) + bonuses
```

### 4.2 Scoring State

```typescript
interface BugHunterScoringState {
  totalScore: number;
  bugsFound: number;
  totalBugs: number;
  wrongLineClicks: number;
  wrongFixAttempts: number;
  hintsUsed: number;
  perBugScores: { bugId: string; points: number; attempts: number; hintsUsed: number }[];
  bonuses: { type: string; points: number }[];
}
```

---

## 5. Hint System

Per bug, 3 hints of increasing specificity. Unlike State Tracer's per-step hints, Bug Hunter's hints progressively narrow the search space:

| Tier | Name | Penalty | What It Reveals | Example |
|------|------|---------|-----------------|---------|
| 1 | Category | -15% | Bug type name | "This is an **off-by-one error**" |
| 2 | Location | -30% | Line range | "The bug is **between lines 3-6**" |
| 3 | Line | -50% | Exact line | "**Line 4** contains the bug" (student still needs to fix it) |

Even after tier 3, the student must still select the correct fix — so there's always a reasoning step.

---

## 6. State Machine

```
INIT
  │ Load blueprint
  ▼
READING_CODE
  │ Student reads code + test cases
  │ Clicks "Start Hunting"
  ▼
BUG_HUNTING  ◄─────────────────────────────┐
  │ Student clicks on a code line          │
  │                                        │
  ├── Wrong line → RED_HERRING_FEEDBACK ───┘
  │     (flash red, show feedback,
  │      -10 pts, return to hunting)
  │
  ├── Correct line ▼
  │
LINE_SELECTED
  │ Fix panel slides in
  │ Student selects a fix option
  │
  ├── Wrong fix → WRONG_FIX ───────────────┐
  │     (shake, show feedback,             │
  │      -20 pts, stay in fix panel)       │
  │     Can retry fix or click different   │
  │     line (returns to BUG_HUNTING)      │
  │                                        │
  ├── Correct fix ▼                        │
  │                                        │
BUG_FIXED                                  │
  │ Show explanation, animate fix          │
  │ Update bug counter                     │
  │                                        │
  ├── More bugs? ──────────────────────────┘
  │     (advance to next bug,
  │      return to BUG_HUNTING)
  │
  ├── All bugs found ▼
  │
VERIFICATION
  │ Run corrected code on all test cases
  │ Animate checkmarks/crosses
  ▼
COMPLETED
  │ Show final score, stats, play again
```

### 6.1 Phase Definitions

```typescript
type BugHunterPhase =
  | 'INIT'
  | 'READING_CODE'
  | 'BUG_HUNTING'
  | 'LINE_SELECTED'
  | 'WRONG_FIX'
  | 'BUG_FIXED'
  | 'VERIFICATION'
  | 'COMPLETED';
```

---

## 7. Visual Components

### 7.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Binary Search — Bug Hunter                    Bugs: [●][○][○] │
│  "Find 3 bugs in this binary search implementation"            │
├───────────────────────────────────────┬─────────────────────────┤
│                                       │                         │
│  Code Panel (clickable lines)         │  Test Case Panel        │
│  ┌─────────────────────────────────┐  │  ┌───────────────────┐  │
│  │  1  def binary_search(arr, t):  │  │  │ Test 1: ✗         │  │
│  │  2      left = 0               │  │  │ Input: [1,3,5,7,9]│  │
│  │  3      right = len(arr) - 1   │  │  │   target = 9      │  │
│  │ ►4      while left < right: ◄──│──│──│ Expected: 4       │  │
│  │  5          mid = (left+right)  │  │  │ Got: -1  ← WRONG  │  │
│  │             // 2                │  │  │                   │  │
│  │  6          if arr[mid] == t:   │  │  │ Test 2: ✓         │  │
│  │  7              return mid      │  │  │ Input: [1,3,5,7,9]│  │
│  │  8          elif arr[mid] < t:  │  │  │   target = 5      │  │
│  │  9              left = mid + 1  │  │  │ Expected: 2       │  │
│  │  10         else:               │  │  │ Got: 2   ← OK     │  │
│  │  11             right = mid - 1 │  │  └───────────────────┘  │
│  │  12     return -1               │  │                         │
│  └─────────────────────────────────┘  │  Score: 0               │
│                                       │  Wrong clicks: 0        │
│  ┌─ Fix Panel (slides in) ─────────┐  │                         │
│  │ Line 4: while left < right:     │  │                         │
│  │                                 │  │                         │
│  │ ○ while left < right:           │  │                         │
│  │   "This is the current code"    │  │                         │
│  │ ● while left <= right:          │  │                         │
│  │   "Correct! Checks the last..." │  │                         │
│  │ ○ while left != right:          │  │                         │
│  │   "Misses when left > right"    │  │                         │
│  │ ○ while left < right + 1:       │  │                         │
│  │   "Equivalent but non-standard" │  │                         │
│  │                            [Fix]│  │                         │
│  └─────────────────────────────────┘  │                         │
├───────────────────────────────────────┴─────────────────────────┤
│  [Hint: Category (-15%)] [Hint: Location (-30%)] [Hint: Line]  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Component Breakdown

| Component | Description | Reuses from State Tracer? |
|-----------|-------------|--------------------------|
| **ClickableCodePanel** | Code with clickable lines. Hover highlights line. Click selects. Fixed bugs show strikethrough + green replacement. | Extends `CodeDisplay` (adds click handler + line states) |
| **TestCasePanel** | Shows test input/output pairs. Pass=green check, Fail=red X. Diff between expected and buggy output highlighted. | NEW |
| **FixPanel** | Slide-in panel showing buggy line + fix options as radio buttons + submit. | Similar pattern to `PredictionPanel` MC mode |
| **BugCounter** | "Bugs: [filled][empty][empty]" — visual progress of bugs found. | NEW (simple) |
| **FeedbackToast** | Floating toast for wrong line clicks and wrong fixes. Auto-dismisses after 3s. | NEW |
| **VerificationPanel** | End-game: runs corrected code on all tests, shows animated checkmarks. | NEW |
| **HintBar** | 3 hint buttons with progressive reveal and cost display. | Adapts `HintSystem` |
| **ScoreDisplay** | Points, wrong clicks, bonuses. | Reuses `ScoreDisplay` |
| **CompletionScreen** | Final stats, accuracy, play again. | Reuses `CompletionScreen` pattern |

### 7.3 Animations

| Event | Animation |
|-------|-----------|
| **Hover on code line** | Line background subtly highlights (gray → lighter gray) |
| **Click correct line** | Line pulses gold for 400ms. Fix panel slides in from bottom with spring. |
| **Click wrong line** | Line flashes red for 300ms. Feedback toast slides in from top. -10 floats up. |
| **Select correct fix** | Fix option border turns green. Buggy line animates: red strikethrough → green replacement fades in. Bug counter fills one slot. "+150" floats up. |
| **Select wrong fix** | Fix panel shakes (translateX oscillation). Option border turns red briefly. Feedback text appears below. |
| **All bugs found** | All green replacement lines pulse simultaneously. Transition to verification. |
| **Verification pass** | Each test case gets animated checkmark sequentially (200ms stagger). |
| **Verification fail** | Red X on failing tests (shouldn't happen if bugs are correctly defined). |

---

## 8. Code Line States

Each line in the code panel has a visual state:

```typescript
type LineState =
  | 'default'           // Normal appearance
  | 'hover'             // Mouse hovering (subtle highlight)
  | 'selected'          // Currently clicked (gold border, fix panel open)
  | 'wrong_click'       // Just clicked but wrong (brief red flash)
  | 'fixed'             // Bug was here, now fixed (strikethrough + green replacement)
  | 'current_bug';      // (sequential mode) The bug being hunted (no visual indicator —
                        //  the student must find it. Used internally only.)
```

The `fixed` state is the most visually distinct — the old line shows with red text + strikethrough, and the new line appears below it in green.

---

## 9. Frontend Architecture

### 9.1 File Plan

```
frontend/src/components/templates/AlgorithmGame/
├── BugHunterGame.tsx                    # NEW — Main container (~300 lines)
├── types.ts                             # MODIFY — Add BugHunter types
├── hooks/
│   ├── useBugHunterMachine.ts           # NEW — State machine reducer
│   └── useBugHunterScoring.ts           # NEW — Scoring logic
├── components/
│   ├── ClickableCodePanel.tsx           # NEW — Code with clickable lines
│   ├── TestCasePanel.tsx                # NEW — Test case display
│   ├── FixPanel.tsx                     # NEW — Fix option selector
│   ├── BugCounter.tsx                   # NEW — Bug progress indicator
│   ├── FeedbackToast.tsx                # NEW — Floating feedback messages
│   ├── VerificationPanel.tsx            # NEW — End-game test verification
│   ├── HintSystem.tsx                   # REUSE — Same 3-tier system
│   ├── ScoreDisplay.tsx                 # REUSE
│   └── CompletionScreen.tsx             # REUSE (may need minor adaptation)
└── data/
    ├── bugHunterBinarySearch.ts         # NEW — Demo: off-by-one in binary search
    ├── bugHunterBubbleSort.ts           # NEW — Demo: wrong comparison + missing swap
    ├── bugHunterBFS.ts                  # NEW — Demo: not checking visited
    ├── bugHunterFibonacci.ts            # NEW — Demo: wrong base case + wrong recurrence
    ├── bugHunterLinkedList.ts           # NEW — Demo: lost pointer in reversal
    ├── bugHunterStack.ts                # NEW — Demo: pop before empty check
    ├── bugHunterBST.ts                  # NEW — Demo: wrong comparison direction
    ├── bugHunterInsertionSort.ts        # NEW — Demo: wrong inner loop boundary
    └── index.ts                         # MODIFY — Add BugHunter exports
```

**Total: ~12 new files, ~2 modified files**

### 9.2 Integration Points

**Game router** (`app/game/[id]/page.tsx`):
- Add `BUG_HUNTER` case to template type switch
- Lazy-load `BugHunterGame` via `dynamic()`

**Demo page** (`app/demo/state-tracer/page.tsx`):
- Rename to `app/demo/algorithm-games/page.tsx` (or add a separate `/demo/bug-hunter` page)
- Add Bug Hunter demo cards to the grid

**Types** (`types.ts`):
- Add `BugHunterBlueprint`, `BugDefinition`, `TestCase`, `RedHerring`, `FixOption`, `BugHunterConfig`, `BugHunterPhase`, `BugHunterScoringState` types

### 9.3 Shared Component Reuse

| Existing Component | How Bug Hunter Uses It |
|-------------------|----------------------|
| `CodeDisplay` | Extended into `ClickableCodePanel` — same syntax highlighting, add click handlers and line state styling |
| `HintSystem` | Reused with different tier labels ("Category" / "Location" / "Line" instead of "Nudge" / "Clue" / "Answer") |
| `ScoreDisplay` | Reused as-is — shows total score and streak info |
| `CompletionScreen` | Reused with adapted stats (bugs found, wrong clicks, accuracy instead of streak/predictions) |
| `StepControls` | NOT used — Bug Hunter is not step-based |

---

## 10. 8 Demo Games

| # | Algorithm | Bugs | Bug Types | Difficulty | Tests |
|---|-----------|------|-----------|------------|-------|
| 1 | **Binary Search** | 1 | off_by_one | Easy | 3 |
| 2 | **Bubble Sort** | 2 | wrong_operator, wrong_variable | Easy+Medium | 2 |
| 3 | **BFS** | 2 | missing visited check, wrong data structure (stack vs queue) | Medium | 2 |
| 4 | **Fibonacci DP** | 2 | wrong_initialization, wrong_operator | Easy+Medium | 3 |
| 5 | **Linked List Reversal** | 2 | wrong_variable, logic_error | Medium+Hard | 2 |
| 6 | **Stack (Valid Parens)** | 1 | boundary_error (no empty check before pop) | Medium | 3 |
| 7 | **BST Insert** | 2 | wrong_operator, wrong_return | Medium | 2 |
| 8 | **Insertion Sort** | 2 | off_by_one, wrong_variable | Easy+Medium | 2 |

### Demo 1: Binary Search Off-by-One (detailed)

**Buggy code:**
```python
def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    while left < right:            # BUG: should be <=
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**Bug:** Line 4 — `while left < right:` should be `while left <= right:`

**Test cases:**
- `binary_search([1,3,5,7,9], 9)` → Expected: `4`, Buggy: `-1` (exposes bug)
- `binary_search([1,3,5,7,9], 5)` → Expected: `2`, Buggy: `2` (passes — bug is subtle)
- `binary_search([1], 1)` → Expected: `0`, Buggy: `-1` (single element fails)

**Fix options:**
1. `while left < right:` — "This is the current (buggy) code. It skips the case where left == right."
2. `while left <= right:` — CORRECT. "When left equals right, there's still one element to check."
3. `while left != right:` — "This would miss cases where left jumps past right after an update."
4. `while left < right + 1:` — "Equivalent to <=, but unconventional. Technically works."

**Red herrings:**
- Line 5 (`mid = (left + right) // 2`): "This correctly computes the midpoint. For very large arrays, `(left + right)` could overflow in some languages, but this is fine for Python."
- Line 9 (`left = mid + 1`): "This correctly narrows the search to the right half. Moving left past mid avoids infinite loops."

**Hints:**
1. "This is an **off-by-one error** — a boundary is wrong by exactly 1."
2. "The bug is in the **loop condition** (lines 3-4)."
3. "**Line 4** has the wrong comparison operator."

### Demo 3: BFS Missing Visited Check (detailed)

**Buggy code:**
```python
def bfs(graph, start):
    queue = [start]
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)          # BUG 1: no visited check — causes duplicates
        for neighbor in graph[node]:
            queue.append(neighbor)   # BUG 2: should check "if neighbor not in visited"
    return order
```

**Bugs:**
- Bug 1 (Medium): Line 5-6 — missing `if node in visited: continue` + `visited.add(node)` before `order.append`. Fix: add visited set check.
- Bug 2 (Medium): Line 8 — should be `if neighbor not in visited: queue.append(neighbor)`.

**This demo shows bugs that are structural (missing code) rather than wrong code — the fix options offer different line insertions.**

---

## 11. Backend Generation Requirements

### 11.1 Inputs

- **Topic/question** from user
- **Algorithm selection** (inferred or explicit)
- **Difficulty level** (determines number and type of bugs)

### 11.2 Generation Pipeline

1. **Select algorithm** — get the correct reference implementation
2. **Choose bug injection points** — based on difficulty, select 1-3 lines to mutate
3. **Apply mutations** — use a taxonomy of bug types (off-by-one, wrong operator, etc.)
4. **Generate test cases** — create inputs that expose each bug (at least one passing, one failing per bug)
5. **Compute buggy outputs** — actually run the buggy code on test inputs to get the wrong output
6. **Generate fix options** — for each bug, create 3-4 plausible replacement lines (1 correct, others wrong-but-educational)
7. **Identify red herrings** — select 2-4 correct-but-suspicious-looking lines with explanations
8. **Generate hints** — 3-tier per bug (category, location, line)
9. **Generate explanations** — per bug, explain WHY it's wrong and what the correct behavior should be
10. **Assemble blueprint** — combine into `BugHunterBlueprint` JSON

### 11.3 Quality Criteria

- **Bug plausibility:** Bugs must be mistakes a real programmer could make, not random token replacements
- **Test case coverage:** At least 1 test must pass with the buggy code (proves the bug is subtle)
- **Fix option quality:** Wrong fix options must be plausible — common mistakes that students might try
- **Red herring quality:** Must target lines that genuinely LOOK suspicious
- **Output accuracy:** `buggyOutput` must be the actual result of running the buggy code on that input — never fabricated
- **Hint progression:** Each tier must be strictly more specific than the previous

---

## 12. Comparison with State Tracer

| Dimension | State Tracer | Bug Hunter |
|-----------|-------------|------------|
| **Core skill** | Predict algorithm behavior | Analyze incorrect code |
| **Bloom level** | Understand / Apply | Analyze / Evaluate |
| **Student action** | Predict next state | Click buggy line + select fix |
| **Data flow** | Sequential steps | Non-linear (click any line) |
| **Visualization** | Data structure viz (array/graph/tree/etc.) | Code panel + test case panel |
| **Replayability** | Low (same trace each time) | Medium (could randomize which bugs are injected) |
| **Time to complete** | 3-8 min | 2-5 min |
| **Backend complexity** | Simulate execution trace | Inject bugs + compute wrong outputs |

---

## 13. Research Sources

- **Gidget design principles** — Lee et al. (2014), 7 principles for debugging games
- **Code Defenders** — Mutation testing game, bug type taxonomy
- **Sojourner under Sabotage** — Debugging serious game, progressive level design
- **Python Tutor** — Visualization-aided debugging, 3.5M+ users
- **O'Rourke et al.** — Hint systems study (50K students), 4 scaffolding categories
- **Productive failure** — Educational Technology Journal (2022), learning through struggle
- **Cognitive load theory** — ACM Computing Education (2022), nested structures increase debugging difficulty
- **Rubber duck debugging** — Metacognitive articulation pedagogy
- **Parsons problems** — Leinonen et al., distractor blocks as debugging exercise variant
- **Code review serious game** — Ardic (2025), gamified code inspection skills
