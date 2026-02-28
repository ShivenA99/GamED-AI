# Algorithmic Games — 12 Mechanic Specifications

**Date:** 2026-02-19
**Purpose:** Detailed specs for each of the 12 game mechanics. Each spec is complete enough to build a standalone demo game. Mechanics are algorithm-agnostic interaction primitives — they take algorithm-specific data as input.

---

## Table of Contents

1. [State Tracer](#1-state-tracer)
2. [Bug Hunter](#2-bug-hunter)
3. [Manual Execution](#3-manual-execution)
4. [Predict-the-Output](#4-predict-the-output)
5. [Algorithm Builder (Parsons)](#5-algorithm-builder-parsons)
6. [Optimization Race](#6-optimization-race)
7. [Pathfinder](#7-pathfinder)
8. [Pattern Matcher](#8-pattern-matcher)
9. [Constraint Puzzle](#9-constraint-puzzle)
10. [Code Completion](#10-code-completion)
11. [Test Case Designer](#11-test-case-designer)
12. [Complexity Analyzer](#12-complexity-analyzer)

---

## 1. State Tracer

### Overview
The player steps through an algorithm's execution one state at a time. At each step, they must **predict the next state** before it is revealed. This is the most universal mechanic — applicable to every algorithm.

**Engagement Level:** Responding → Changing (Naps taxonomy)
**Bloom Level:** Understand → Apply

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **Python Tutor** | https://pythontutor.com/visualize.html | Gold standard for code state visualization. Study: how they render heap/stack, how arrows show references, the forward/backward stepper UX, variable highlight on change. |
| **VisuAlgo** | https://visualgo.net/en/sorting | Study: how they sync code line highlighting with array animation, the "e-Lecture" mode that pauses and asks questions, the training/quiz mode. |
| **dpvis** | https://arxiv.org/html/2411.07705v1 | Study: the "self-test" mode — quizzes students on which DP table cells are read/written next. Frame-by-frame with prediction. This is exactly our mechanic. |
| **Sorting.at** | https://sorting.at/ | Study: clean step-by-step sorting visualization with comparison counters, swap counters, and current-line-of-code highlight. |
| **Algorithm Wiki** | https://thimbleby.gitlab.io/algorithm-wiki-site/ | Study: interactive algorithms running on a real interpreter with state inspection. |

### Core Interaction

**Player flow:**
1. See the algorithm's code panel (left) + data structure visualization (right)
2. Current line of code is highlighted
3. A **prediction prompt** appears: "What will the array look like after this step?" or "What is the value of `i` after this line executes?"
4. Player responds via:
   - **Array/structure prediction**: Drag elements into predicted arrangement, OR
   - **Value prediction**: Type a number/string into an input field, OR
   - **Multiple choice**: Select from 3-4 options showing different possible states
5. Player submits prediction
6. System reveals the actual next state with visual diff (correct elements glow green, wrong glow red)
7. Animation plays showing the state transition
8. Advance to next step. Repeat until algorithm completes.

**Input types:** Click (multiple choice), Drag (arrangement), Type (value entry)

### State Machine

```
INIT → SHOWING_STATE → AWAITING_PREDICTION → PREDICTION_SUBMITTED → REVEALING_RESULT → SHOWING_STATE → ... → COMPLETED
                                                      ↓
                                               (if hint requested)
                                              SHOWING_HINT → AWAITING_PREDICTION
```

States:
- `INIT`: Load algorithm, initial data, generate full execution trace
- `SHOWING_STATE`: Display current state (code line, variables, data structure)
- `AWAITING_PREDICTION`: Prediction prompt shown, waiting for player input
- `PREDICTION_SUBMITTED`: Player has committed an answer, locked in
- `REVEALING_RESULT`: Show correct answer with visual diff, animate transition
- `SHOWING_HINT`: Display a hint (costs points), return to awaiting prediction
- `COMPLETED`: All steps traced, show final score + summary

### Input Data Schema

```typescript
interface StateTracerData {
  // Algorithm identity
  algorithm_name: string;           // "bubble_sort", "dijkstra", "fibonacci"
  algorithm_description: string;    // Brief explanation shown at start

  // Code
  code: CodeBlock;                  // The algorithm's code to display
  language: "python" | "javascript" | "pseudocode";

  // Execution trace (pre-computed by AI or algorithm runner)
  steps: ExecutionStep[];

  // Configuration
  prediction_mode: "arrangement" | "value" | "multiple_choice" | "mixed";
  show_code_panel: boolean;         // Some games may hide code
  show_variables_panel: boolean;
  show_call_stack: boolean;         // For recursive algorithms
  steps_to_predict: number[] | "all"; // Which step indices require prediction (can skip trivial ones)
}

interface CodeBlock {
  source: string;                   // Full source code
  lines: CodeLine[];                // Parsed lines with metadata
  language: string;
}

interface CodeLine {
  line_number: number;
  text: string;
  is_executable: boolean;           // false for comments, blank lines
  indent_level: number;
}

interface ExecutionStep {
  step_number: number;
  code_line: number;                // Which line is executing
  action_description: string;       // "Compare arr[0]=5 with arr[1]=3"

  // State snapshots
  variables: Variable[];            // All variable values at this point
  data_structure: DataStructureState; // Visual state of the main structure
  call_stack?: StackFrame[];        // For recursive algorithms

  // Prediction question for this step
  prediction: PredictionQuestion;

  // Annotations
  highlights: HighlightSpec[];      // Which elements to highlight
  explanation: string;              // Shown after reveal
}

interface Variable {
  name: string;
  value: any;
  type: string;
  changed: boolean;                 // Did this variable change in this step?
}

interface DataStructureState {
  type: "array" | "graph" | "tree" | "table" | "linked_list" | "stack" | "queue" | "heap";
  data: any;                        // Type-specific state representation
  // Array example: { elements: [5, 3, 1, 4, 2], active_indices: [0, 1], sorted_indices: [4] }
  // Graph example: { nodes: [...], edges: [...], visited: ["A", "B"], current: "C", queue: ["D", "E"] }
  // Tree example: { root: {...}, highlighted_node: "node_3", path: ["root", "left", "right"] }
  // Table example: { rows: 5, cols: 5, cells: [[...]], active_cell: [2,3], filled_cells: [[0,0],[0,1],...] }
}

interface PredictionQuestion {
  prompt: string;                   // "What will the array look like after this swap?"
  type: "arrangement" | "value" | "multiple_choice" | "multi_select";

  // For arrangement: player arranges elements
  arrangement_options?: {
    elements: any[];                // Elements to arrange
    correct_arrangement: any[];     // Correct order
  };

  // For value: player types a value
  value_answer?: {
    correct_value: any;
    acceptable_tolerance?: number;  // For floating point
  };

  // For multiple choice
  choices?: {
    options: { id: string; display: any; }[];
    correct_id: string;
  };

  // For multi-select (e.g., "which nodes are in the queue?")
  multi_select?: {
    options: { id: string; display: any; }[];
    correct_ids: string[];
  };
}

interface HighlightSpec {
  target: string;                   // "array[0]", "node_A", "variable_i", "code_line_5"
  color: "active" | "comparing" | "swapping" | "sorted" | "error" | "success";
  animation?: "pulse" | "glow" | "bounce" | "none";
}

interface StackFrame {
  function_name: string;
  parameters: { name: string; value: any }[];
  local_variables: { name: string; value: any }[];
  return_address: number;           // Line to return to
}
```

### Scoring

```
Base points per correct prediction:     +100
Streak multiplier:                      1x (0-2 streak), 1.5x (3-4), 2x (5-7), 3x (8+)
Hint penalty:                           -30% of step's points per hint used
Partial credit (arrangement):           (correct_positions / total_positions) * base_points
Partial credit (multi-select):          (correct_selections - wrong_selections) / total_correct * base_points (min 0)
Time bonus:                             None (accuracy > speed for learning)
Perfect run bonus:                      +20% of total if zero mistakes

Final score = sum(step_scores) * (1 + perfect_bonus)
Max score = num_predicted_steps * 100 * max_streak_multiplier + perfect_bonus
```

### Validation Rules

- **Arrangement**: Exact match of element order. Partial credit = count of elements in correct position / total.
- **Value**: Exact match (strings: case-insensitive trim). Numbers: within tolerance if specified.
- **Multiple choice**: Exact match of selected option ID.
- **Multi-select**: Score = (|correct ∩ selected| - |selected - correct|) / |correct|, clamped to [0, 1].
- **Edge cases**: If step has no meaningful prediction (e.g., variable declaration), skip it (not in `steps_to_predict`).

### Visual Components

| Component | Description |
|-----------|-------------|
| **Code Panel** | Syntax-highlighted code with current line highlight (yellow bg), executed lines (light gray bg). Scrolls to keep current line visible. |
| **Variables Panel** | Table of variable names, types, values. Changed values flash/pulse with highlight color. Previous value shown in gray strikethrough. |
| **Data Structure Visualizer** | Algorithm-specific: Array (bars/blocks), Graph (force-directed), Tree (hierarchical), Table (grid). Active elements highlighted. |
| **Call Stack Panel** | (optional) Stack of frames growing downward. Each frame shows function name + local vars. Top frame = current. |
| **Prediction Input** | Floating panel over the data structure. Shows prompt + input method (drag area / text field / choices). Submit button. |
| **Step Counter** | "Step 5 of 23" with progress bar. |
| **Score Display** | Running score + streak counter with flame icon for active streak. |
| **Diff Overlay** | After reveal: green checkmarks on correct predictions, red X on incorrect, with correct values shown. |

### Animations & Feedback

- **On correct prediction**: Data structure animates to next state with smooth transition. Green flash on predicted elements. "+100" floating text. Streak counter increments with fire animation.
- **On incorrect prediction**: Red flash on wrong elements. Correct state morphs in with highlight showing what was different. Streak resets (streak counter shatters). Brief explanation text appears.
- **On step advance**: Code panel scrolls, new line highlights. Variables panel updates with change animations. Previous highlights fade.
- **On completion**: Summary overlay — total score, accuracy %, longest streak, most-missed step types.

### Hints

3-tier progressive hints per step:
1. **Nudge** (-10 pts): "Look at which line of code is executing and what operation it performs"
2. **Clue** (-30 pts): "The comparison at line 5 finds that arr[0] > arr[1], so..."
3. **Answer** (-50 pts): Shows the correct state with full explanation

### Demo Game: Bubble Sort on [5, 3, 1, 4, 2]

**Algorithm**: Bubble Sort
**Domain framing**: "Sort these student test scores from lowest to highest"

**Steps** (showing first 5 of ~20):

| Step | Code Line | Action | Array State | Prediction Prompt | Answer |
|------|-----------|--------|-------------|-------------------|--------|
| 1 | `if arr[0] > arr[1]:` | Compare 5 and 3 | `[5, 3, 1, 4, 2]` | "Is arr[0] > arr[1]?" (Y/N) | Yes |
| 2 | `arr[0], arr[1] = arr[1], arr[0]` | Swap | `[5, 3, 1, 4, 2]` | "What does the array look like after the swap?" (arrange) | `[3, 5, 1, 4, 2]` |
| 3 | `if arr[1] > arr[2]:` | Compare 5 and 1 | `[3, 5, 1, 4, 2]` | "Will a swap happen?" (Y/N) | Yes |
| 4 | `arr[1], arr[2] = arr[2], arr[1]` | Swap | `[3, 5, 1, 4, 2]` | "Arrange the array after swap" | `[3, 1, 5, 4, 2]` |
| 5 | `if arr[2] > arr[3]:` | Compare 5 and 4 | `[3, 1, 5, 4, 2]` | "What values are being compared?" (type two values) | 5, 4 |

---

## 2. Bug Hunter

### Overview
The player is presented with algorithm code that contains **deliberate bugs**. They must locate each bug, identify what's wrong, and select or type the fix. Bugs are injected at increasing difficulty — from syntax errors to subtle algorithmic mistakes.

**Engagement Level:** Analyzing → Evaluating (Naps taxonomy)
**Bloom Level:** Analyze → Evaluate

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **Gidget** | https://faculty.washington.edu/ajko/papers/Lee2014GidgetPrinciples.pdf | 7 design principles for debugging games. Study: 9-slide tutorial, keystroke-level feedback, progressively specific hints. 800+ participants learned conditionals/loops through debugging alone. |
| **Code Defenders** | https://code-defenders.org/ | Mutation testing game: attackers inject bugs, defenders write tests. Study: the taxonomy of mutation operators (they're exactly our bug types). |
| **Sojourner under Sabotage** | https://arxiv.org/abs/2504.19287 | Debugging serious game with spaceship narrative. Study: how they scaffold from easy to hard bugs, progressive level design. |
| **Python Tutor** | https://pythontutor.com/ | Study: how visualization helps locate bugs — seeing wrong variable values reveals the bug's location. |
| **Brilliant.org** | https://brilliant.org/ | Study: their "spot the error" exercises in algorithm courses — clean UI, immediate feedback, explanation of why it's wrong. |

### Core Interaction

**Player flow:**
1. See the buggy code (full screen or side-by-side with expected behavior)
2. Optionally: see a failing test case — "Input: [5,3,1] → Expected: [1,3,5] → Got: [1,5,3]"
3. Player can **run the code mentally** or use a "Run" button to see actual output on test input
4. Player clicks on the line they believe is buggy → line highlights as selected
5. **Fix panel** appears showing:
   - The current (buggy) line
   - Fix options: multiple choice of replacement lines, OR free-text entry
6. Player selects/types the fix and submits
7. System validates: if correct, bug is marked as found. If wrong, feedback explains why that's not the issue.
8. If multiple bugs: repeat for next bug
9. After all bugs found: show corrected code + run it on test cases to verify

**Input types:** Click (select buggy line), Click (select fix from options) or Type (write fix)

### State Machine

```
INIT → READING_CODE → BUG_HUNTING → LINE_SELECTED → FIX_SUBMITTED →
  ↓ (correct)              ↓ (incorrect)
BUG_FIXED → (more bugs?) → BUG_HUNTING    WRONG_FIX → BUG_HUNTING
  ↓ (all bugs found)
VERIFICATION → COMPLETED
```

States:
- `INIT`: Load buggy code, bug definitions, test cases
- `READING_CODE`: Player reads code and test case. Optional "Run" to see failure.
- `BUG_HUNTING`: Player scanning code for bugs. Can click any line.
- `LINE_SELECTED`: Player has clicked a line. Fix panel appears.
- `FIX_SUBMITTED`: Player submitted a fix.
- `BUG_FIXED`: Correct fix applied. Code updates. Move to next bug or verification.
- `WRONG_FIX`: Incorrect fix. Show feedback. Return to hunting.
- `VERIFICATION`: All bugs found. Run corrected code on all test cases.
- `COMPLETED`: Show results.

### Input Data Schema

```typescript
interface BugHunterData {
  algorithm_name: string;
  algorithm_description: string;

  // The correct code (reference)
  correct_code: CodeBlock;

  // The buggy version
  buggy_code: CodeBlock;

  // Bug definitions (ordered by difficulty)
  bugs: BugDefinition[];

  // Test cases to demonstrate the bug
  test_cases: TestCase[];

  // Configuration
  show_test_output: boolean;        // Show expected vs actual output
  allow_run: boolean;               // Let player run code on test input
  fix_mode: "multiple_choice" | "free_text" | "mixed";
  reveal_bugs_sequentially: boolean; // true = one at a time, false = find all at once
}

interface BugDefinition {
  bug_id: string;
  buggy_line: number;               // Line number with the bug
  buggy_code_text: string;          // The incorrect line
  correct_code_text: string;        // The correct line
  bug_type: BugType;
  difficulty: 1 | 2 | 3;           // 1=easy, 2=medium, 3=hard

  // Explanation shown after finding
  explanation: string;              // "The comparison should be '<=' not '<' because..."

  // Fix options (for multiple choice mode)
  fix_options?: FixOption[];

  // Common wrong guesses and their feedback
  red_herrings?: RedHerring[];
}

type BugType =
  | "off_by_one"           // i < n vs i <= n
  | "wrong_operator"       // < vs <=, + vs -, == vs !=
  | "wrong_variable"       // using i instead of j
  | "missing_base_case"    // recursion without termination
  | "wrong_initialization" // starting from 1 instead of 0
  | "wrong_return"         // returning wrong value
  | "infinite_loop"        // missing increment or wrong condition
  | "wrong_data_structure" // using stack instead of queue
  | "boundary_error"       // not handling empty input
  | "logic_error"          // correct syntax but wrong algorithm logic
  | "performance_bug";     // correct output but wrong complexity

interface FixOption {
  id: string;
  code_text: string;                // The replacement line
  is_correct: boolean;
  feedback: string;                 // Why this option is right/wrong
}

interface RedHerring {
  line_number: number;              // Line player might mistakenly click
  feedback: string;                 // "This line is actually correct because..."
}

interface TestCase {
  input_description: string;        // "Array: [5, 3, 1, 4, 2]"
  input_data: any;
  expected_output: any;
  buggy_output: any;                // What the buggy code produces
  highlights_bug: string[];         // Which bug_ids this test case exposes
}
```

### Scoring

```
Per bug found:
  Correct line + correct fix on first try:    +150
  Correct line + correct fix on 2nd try:      +100
  Correct line + correct fix on 3rd+ try:     +50
  Correct line but wrong fix (each attempt):  -20 (from that bug's pool)
  Wrong line clicked:                         -10 (per wrong click)

Difficulty multiplier:
  Easy bug (difficulty 1):     1.0x
  Medium bug (difficulty 2):   1.5x
  Hard bug (difficulty 3):     2.0x

Hint penalty: -30% of bug's points per hint
Time bonus: None (thinking > speed)
All bugs found bonus: +100

Final score = sum(bug_scores * difficulty_multiplier) + all_found_bonus
```

### Validation Rules

- **Line selection**: Exact match of line number. Player must click the specific buggy line.
- **Fix validation (multiple choice)**: Exact match of correct option ID.
- **Fix validation (free text)**: Normalize whitespace, compare AST-equivalent if possible. Fallback: exact string match after normalization.
- **Red herring handling**: If player clicks a non-buggy line, show specific feedback for known red herrings, or generic "This line is correct" for others.
- **Multiple bugs**: If `reveal_bugs_sequentially`, only accept the current bug's line. If not, accept any unfound bug's line.

### Visual Components

| Component | Description |
|-----------|-------------|
| **Code Editor** | Full code with line numbers. Clickable lines (hover highlight). Buggy lines NOT visually marked (player must find them). Fixed bugs shown with green strikethrough of old line + green new line. |
| **Test Case Panel** | Shows input, expected output, actual (buggy) output. Diff highlighted in red/green. |
| **Fix Panel** | Slide-in panel when line is clicked. Shows the line + fix options (radio buttons or text input). Submit button. |
| **Bug Counter** | "Bugs found: 1/3" with bug icons (grayed out → colored as found). |
| **Run Button** | (optional) Runs buggy code on test input, shows console-style output. |
| **Feedback Toast** | On correct: green toast with explanation. On incorrect: red toast with hint about why that's not the bug. |

### Animations & Feedback

- **On line click (correct line)**: Line pulses gold. Fix panel slides in from right.
- **On line click (wrong line)**: Brief red flash. Feedback toast: "This line is actually correct — [explanation]".
- **On correct fix**: Buggy line animates strikethrough (red), correct line fades in (green). Bug counter fills one slot. "+150" floating text.
- **On wrong fix**: Fix panel shakes. Red flash. Show why this fix doesn't work.
- **On all bugs found**: Code panel does a "clean sweep" animation — all green lines pulse. Verification runs with checkmarks on each test case.

### Hints

Per bug, 3-tier:
1. **Category hint** (-15 pts): "This is an off-by-one error" (reveals bug type)
2. **Location hint** (-30 pts): "The bug is between lines 5-10" (narrows to region)
3. **Line hint** (-50 pts): "Line 7 is incorrect" (reveals exact line, player still needs fix)

### Demo Game: Binary Search with Off-by-One Bug

**Algorithm**: Binary Search
**Bug**: `while left < right` should be `while left <= right` (misses single-element range)

**Buggy code:**
```python
def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    while left < right:          # BUG: should be <=
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**Test case**: `binary_search([1, 3, 5, 7, 9], 9)` → Expected: `4` → Got: `-1`

**Fix options:**
1. `while left < right:` → "This is the current code (still buggy)"
2. `while left <= right:` → CORRECT — "When left == right, there's one element left to check"
3. `while left < right + 1:` → "Equivalent to <=, but less readable. Technically correct but not conventional."
4. `while left != right:` → "This would miss the case where left > right after an update"

---

## 3. Manual Execution

### Overview
The player **becomes the algorithm** — physically performing each operation on the data structure. For sorting: they drag elements to swap them. For graphs: they click nodes in traversal order. For trees: they drag values to insert positions. The system validates each operation in real-time.

**Engagement Level:** Constructing (Naps taxonomy)
**Bloom Level:** Apply

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **Sort Attack** | https://ieeexplore.ieee.org/document/7295785/ | IEEE-published sorting game. Study: drag-drop UX for swaps, multi-modal feedback (visual + spatial + kinesthetic), incorrect-move feedback system. |
| **Advanced-ICT Sorting Games** | https://www.advanced-ict.info/interactive/bubble_sort.html | Study: how they enforce algorithm rules (only adjacent swaps for bubble sort), step counter, comparison counter. Also merge sort and insertion sort variants. |
| **OpenDSA/JSAV** | https://opendsa-server.cs.vt.edu/ | Study: proficiency exercises where students manipulate data structures. Auto-graded, randomized inputs. The JSAV framework for building these. |
| **TRAKLA2** | (academic, search "TRAKLA2 algorithm simulation") | Study: how they randomize exercises, auto-grade manipulation tasks, provide feedback at each step. |
| **Interactive Quicksort** | https://me.dt.in.th/page/Quicksort/ | Study: card-game metaphor for quicksort. Pivot is leftmost, cards flipped one by one. Clean, intuitive UX. |
| **VisuAlgo Training Mode** | https://visualgo.net/en/sorting?slide=1 | Study: training mode where you answer questions about the next operation. Not full manipulation but halfway there. |

### Core Interaction

**Player flow:**
1. See the data structure (array, graph, tree, etc.) with the algorithm's rules shown
2. Algorithm's current step is described: "Bubble Sort: Compare adjacent elements and swap if out of order"
3. Player performs the operation:
   - **Array**: Drag element A to element B's position to swap them
   - **Graph**: Click the next node to visit (system shows queue/stack)
   - **Tree**: Drag a value to the correct leaf position to insert
   - **Table (DP)**: Click a cell and type the value
   - **Heap**: Click parent/child pair to swap for sift-up/sift-down
4. System validates immediately:
   - **Correct**: Green flash, operation animates, advance
   - **Incorrect**: Red flash, "That's not the operation [algorithm] would perform next", undo
5. Counters update: comparisons, swaps, steps completed
6. Continue until algorithm completes
7. Summary: your execution vs optimal, accuracy, counter stats

**Input types:** Drag-and-drop (swaps, insertions), Click sequence (traversal), Click+Type (DP table)

### State Machine

```
INIT → AWAITING_ACTION → ACTION_PERFORMED →
  ↓ (correct)                    ↓ (incorrect)
ANIMATING_STEP → AWAITING_ACTION   INVALID_ACTION_FEEDBACK → AWAITING_ACTION
  ↓ (algorithm complete)
COMPLETED
```

### Input Data Schema

```typescript
interface ManualExecutionData {
  algorithm_name: string;
  algorithm_description: string;
  algorithm_rules: string[];        // Rules shown to player: ["Only swap adjacent elements", "Always start from the left"]

  // Initial data structure
  initial_state: DataStructureState;

  // Full execution trace (the "answer key")
  steps: ManualStep[];

  // What type of manipulation
  interaction_type: "swap" | "click_sequence" | "insert" | "cell_fill" | "edge_select" | "color_assign";

  // Configuration
  show_algorithm_rules: boolean;
  show_step_counter: boolean;
  show_comparison_counter: boolean;
  allow_undo: boolean;              // Let player undo last move
  max_wrong_moves: number | null;   // null = unlimited, 3 = three strikes

  // Optional code panel
  code?: CodeBlock;                 // Show algorithm code alongside
  highlight_code_line?: boolean;    // Highlight current code line as player works
}

interface ManualStep {
  step_number: number;
  action_type: "swap" | "visit" | "insert" | "fill" | "select_edge" | "assign_color" | "compare";

  // What the player should do
  expected_action: {
    // For swap:
    swap_indices?: [number, number];
    // For visit/click:
    target_node?: string;
    // For insert:
    insert_value?: any;
    insert_position?: string;       // "left_child_of_node_5"
    // For cell fill:
    cell_position?: [number, number]; // [row, col]
    cell_value?: any;
    // For edge select:
    edge?: [string, string];        // [from_node, to_node]
    // For color assign:
    node?: string;
    color?: string;
  };

  // State after this step completes
  state_after: DataStructureState;

  // Annotations
  explanation: string;
  code_line?: number;
}
```

### Scoring

```
Points per correct action:          +50
Consecutive correct streak:         1x (0-4), 1.5x (5-9), 2x (10+)
Wrong action penalty:               -25 (per incorrect attempt on a step)
Hint penalty:                       -40% of step's points
Undo used:                          No penalty (learning tool)
Efficiency bonus (end):             If player's total actions == optimal, +15% bonus

Final score = sum(step_scores * streak) * efficiency_modifier
```

### Validation Rules

- **Swap**: Check that the two indices match the expected swap. Order-insensitive (swap(i,j) == swap(j,i)).
- **Click sequence**: Check that the clicked node matches the expected next node. For BFS: must be the FIFO front of the queue. For DFS: must be the top of the stack or an unvisited neighbor.
- **Insert**: Check that the value is placed at the correct position in the structure.
- **Cell fill**: Check that the value entered matches the expected value (exact or within tolerance).
- **Edge select**: Check that the selected edge matches (order-insensitive for undirected graphs).
- **Color assign**: Check that the assigned color is valid (no same-color adjacent for graph coloring).

### Visual Components

| Component | Description |
|-----------|-------------|
| **Data Structure Canvas** | Interactive rendering of the data structure. Elements are draggable (for swap) or clickable (for traversal). |
| **Algorithm Rules Card** | Pinned card showing the algorithm's rules in plain language. |
| **Step Counter** | "Step 7 of 20" with progress bar. |
| **Operation Counters** | Comparisons: 12, Swaps: 5 — real-time counters like sorting visualizers. |
| **Code Panel** | (optional) Algorithm code with current line highlighted, synced to player's progress. |
| **Queue/Stack Panel** | (for graph algorithms) Shows the current BFS queue or DFS stack contents. |
| **Undo Button** | Reverts last action (if `allow_undo` is true). |

### Animations & Feedback

- **On correct swap**: Elements smoothly animate to new positions. Green glow. Step counter advances.
- **On incorrect swap**: Elements bounce back to original positions. Red flash. Shake animation. Brief text: "Bubble sort would compare arr[2] and arr[3] next, not arr[0] and arr[3]."
- **On node visit (correct)**: Node fills with color (BFS: level-based, DFS: discovery-time-based). Edge to parent highlights. Queue/stack updates.
- **On completion**: "Algorithm Complete!" overlay. Stats panel: accuracy, total moves, streak, comparison vs optimal.

### Demo Game: Merge Sort Merge Step on [1, 5, 8] and [2, 3, 7]

**Algorithm**: Merge Sort (merge phase only)
**Initial state**: Two sorted arrays: `[1, 5, 8]` and `[2, 3, 7]`, empty output: `[]`
**Interaction**: Click the smaller top element to place into output

| Step | Left | Right | Player clicks | Output |
|------|------|-------|---------------|--------|
| 1 | `[1, 5, 8]` | `[2, 3, 7]` | 1 (from left) | `[1]` |
| 2 | `[5, 8]` | `[2, 3, 7]` | 2 (from right) | `[1, 2]` |
| 3 | `[5, 8]` | `[3, 7]` | 3 (from right) | `[1, 2, 3]` |
| 4 | `[5, 8]` | `[7]` | 5 (from left) | `[1, 2, 3, 5]` |
| 5 | `[8]` | `[7]` | 7 (from right) | `[1, 2, 3, 5, 7]` |
| 6 | `[8]` | `[]` | 8 (from left) | `[1, 2, 3, 5, 7, 8]` |

---

## 4. Predict-the-Output

### Overview
Given an algorithm and its input, the player predicts the final output or a specific intermediate state. This is the gamified version of **code tracing** — a fundamental CS assessment. Unlike State Tracer (which steps through), this asks for the end result or a specific checkpoint.

**Engagement Level:** Responding (Naps taxonomy)
**Bloom Level:** Understand → Apply

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **ETH Zurich Program Tracing** | https://lec.inf.ethz.ch/ifmp/2019/dl/additional/handouts/ProgramTracing.html | Study: structured program tracing worksheets. "Having the basic skills of tracing existing code is prerequisite to writing original code — reading before writing." |
| **Brilliant.org Quizzes** | https://brilliant.org/ | Study: their prediction-style questions in algorithm courses. Clean multi-choice with visual options. Immediate explanation. |
| **CodingBat** | https://codingbat.com/ | Study: simple predict-the-output for Java/Python functions. Instant feedback. |
| **dpvis Self-Test** | https://arxiv.org/html/2411.07705v1 | Study: for DP specifically — predict which cell gets computed next and what value it gets. |

### Core Interaction

**Player flow:**
1. See the algorithm code + input data
2. Question prompt: "What does this function return for input [3, 1, 4, 1, 5]?" or "After 3 iterations, what is the array state?"
3. Player responds:
   - **Free text**: Type the answer (number, array, string)
   - **Multiple choice**: Select from visual options
   - **Arrangement**: Drag elements into predicted output order
   - **Selection**: Click elements that will be in the output (e.g., "which nodes are visited?")
4. Submit → Reveal correct answer with explanation
5. If multi-question: advance to next question about the same algorithm

**Input types:** Type (values), Click (multiple choice / selection), Drag (arrangement)

### State Machine

```
INIT → SHOWING_QUESTION → AWAITING_ANSWER → ANSWER_SUBMITTED → SHOWING_RESULT →
  ↓ (more questions)          ↓ (last question)
SHOWING_QUESTION             COMPLETED
```

### Input Data Schema

```typescript
interface PredictOutputData {
  algorithm_name: string;
  code: CodeBlock;
  language: string;

  // The questions about this algorithm
  questions: PredictionChallenge[];

  // Configuration
  show_code: boolean;
  allow_scratch_space: boolean;     // Give player a notepad to work out answers
  timed: boolean;
  time_per_question_seconds?: number;
}

interface PredictionChallenge {
  question_id: string;
  input_data: any;                  // The input to the algorithm
  input_display: string;            // "arr = [3, 1, 4, 1, 5], target = 4"

  prompt: string;                   // "What does binary_search return?"

  // Answer format
  answer_type: "text" | "number" | "array" | "multiple_choice" | "selection" | "boolean";

  correct_answer: any;
  answer_display: string;           // Human-readable correct answer

  // For multiple choice
  options?: { id: string; display: string; }[];

  // For selection (e.g., "which nodes are visited?")
  selectable_items?: { id: string; label: string; }[];
  correct_selection?: string[];

  // Explanation
  explanation: string;              // Shown after answer
  step_trace?: string;              // Optional: brief trace of how to get the answer

  difficulty: 1 | 2 | 3;
  points: number;
}
```

### Scoring

```
Correct answer:                     +points (defined per question, typically 100-200)
Partial credit (array):             (correct_elements / total) * points
Partial credit (selection):         (|correct ∩ selected| - |wrong|) / |correct| * points
Wrong answer:                       0 (no negative)
Hint used:                          -30% of question's points
Speed bonus (if timed):             +20% if answered in < 50% of allotted time

Final score = sum(question_scores)
```

### Visual Components

| Component | Description |
|-----------|-------------|
| **Code Panel** | Read-only code display with syntax highlighting. Input values shown in comment or header. |
| **Question Card** | Large prompt text with answer input below. |
| **Scratch Space** | (optional) Expandable notepad — player can type working-out notes. |
| **Answer Input** | Adaptive: text field, number spinner, sortable list, checkbox grid, or radio buttons. |
| **Timer** | (if timed) Countdown bar above the question. |
| **Result Overlay** | Shows correct answer, player's answer, diff, and explanation. |

### Demo Game: Quick Sort Partition Result

**Algorithm**: Quick Sort partition function
**Input**: `arr = [7, 2, 1, 6, 8, 5, 3, 4]`, pivot = arr[-1] = 4

**Questions:**
1. "After partitioning with pivot=4, what elements are to the LEFT of the pivot?" → `[2, 1, 3]`
2. "What is the final position (index) of the pivot?" → `3`
3. "What does the array look like after partition?" → `[2, 1, 3, 4, 8, 5, 7, 6]` (one valid partitioning)

---

## 5. Algorithm Builder (Parsons)

### Overview
The player constructs an algorithm by **dragging code blocks into the correct order**. Blocks may include distractors (wrong code that shouldn't be used). This is based on Parsons Problems research — shown to be as effective as code writing but taking 50% less time.

**Engagement Level:** Constructing (Naps taxonomy)
**Bloom Level:** Apply → Create

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **js-parsons** | https://js-parsons.github.io/ | The original Parsons Problem JS library. Study: drag-drop UX, indentation handling, distractor highlighting, grading algorithm. |
| **Runestone Interactive** | https://runestone.academy/ | Study: their Parsons problem integration in eTextbooks. Instant feedback, indent-aware grading. |
| **Parsons Problems Research** | https://dl.acm.org/doi/10.1145/3571785.3574127 | Key paper: 2D Parsons with distractors. Same learning, 50% less time than writing code. |
| **Google Blockly** | https://developers.google.com/blockly | Study: visual block programming UX. Snap-together blocks, toolbox palette, workspace. Though we use code lines not blocks. |
| **MakeSort** | https://avimegiddo.com/2025/01/11/makesort-drag-n-drop-sorting-games-maker-player/ | Study: drag-and-drop sorting games. Reordering mechanics in an educational context. |
| **Scratch** | https://scratch.mit.edu/ | Study: block snapping UX, visual feedback when blocks connect correctly. |

### Core Interaction

**Player flow:**
1. See a scrambled list of code blocks in a "source" area
2. See an empty "solution" area where the algorithm should be built
3. Read the problem description: "Build a binary search function"
4. Drag code blocks from source to solution area
5. Arrange blocks in correct order (and correct indentation for Python)
6. Optionally: identify and leave distractor blocks in the source (they shouldn't be used)
7. Submit solution
8. System grades: highlights correct blocks (green), misplaced blocks (orange), distractor usage (red)
9. Player can rearrange and resubmit

**Input types:** Drag-and-drop (reordering), optionally indentation adjustment (drag left/right)

### State Machine

```
INIT → BUILDING → SUBMITTED →
  ↓ (all correct)    ↓ (has errors)
COMPLETED           FEEDBACK_SHOWN → BUILDING
```

### Input Data Schema

```typescript
interface AlgorithmBuilderData {
  algorithm_name: string;
  problem_description: string;      // "Build a function that performs binary search on a sorted array"

  // The correct solution
  correct_order: ParsonsBlock[];

  // Distractor blocks (should NOT be used)
  distractors: ParsonsBlock[];

  // Configuration
  language: "python" | "javascript" | "pseudocode";
  indentation_matters: boolean;     // Python: yes, pseudocode: maybe not
  max_attempts: number | null;      // null = unlimited
  show_line_numbers: boolean;
  group_mode: "individual_lines" | "block_groups"; // Drag individual lines or groups

  // Hints
  hints: string[];                  // Progressive hints

  // Test cases (for verification after building)
  test_cases?: TestCase[];
}

interface ParsonsBlock {
  id: string;
  code: string;                     // The code text
  indent_level: number;             // Expected indentation (0, 1, 2, ...)
  is_distractor: boolean;
  distractor_explanation?: string;  // "This uses a for loop instead of while — wrong for binary search because..."
  group_id?: string;                // If multiple lines form one logical block
}
```

### Scoring

```
Perfect solution on first attempt:  +300
Correct but with resubmissions:     300 * (0.8 ^ (attempts - 1))   [diminishing returns]
Per-block scoring (if not perfect):
  Block in correct position:        +30
  Block in correct order but wrong indent: +15
  Distractor correctly excluded:    +20
  Distractor incorrectly included:  -30
Hint used:                          -40 per hint

Final score = max(per_block_score, attempt_score)
```

### Validation Rules

- **Order check**: Each block's position in the solution list must match the correct order.
- **Indentation check**: (if `indentation_matters`) Each block's indent level must match expected.
- **Distractor check**: All distractor blocks should remain in the source area.
- **Partial grading**: Count (blocks in correct position / total correct blocks).
- **Multiple correct solutions**: Some algorithms have flexible ordering (e.g., variable declarations). The schema can define `group_id` for interchangeable blocks.

### Visual Components

| Component | Description |
|-----------|-------------|
| **Source Area** | Left panel with scrambled blocks. Blocks are draggable cards with code text in monospace font. Distractors mixed in (visually identical). |
| **Solution Area** | Right panel (or below). Drop zone with numbered slots. Blocks snap into place. Indentation guides shown as vertical lines. |
| **Problem Description** | Top card with the problem statement. |
| **Indentation Controls** | (if applicable) Tab/shift-tab buttons or drag left/right to adjust indentation. |
| **Submit Button** | Grades the current arrangement. |
| **Feedback Overlay** | After submit: green border on correct blocks, orange on misplaced, red on distractors used. |
| **Attempt Counter** | "Attempt 2 of 5" or unlimited. |
| **Test Runner** | (optional) After correct solution: runs code on test cases with checkmarks. |

### Animations & Feedback

- **On drag**: Block lifts with shadow, source slot shows dotted outline.
- **On drop**: Block snaps into position with subtle bounce.
- **On submit (all correct)**: All blocks flash green in sequence top-to-bottom. Confetti. "Perfect!"
- **On submit (has errors)**: Correct blocks get green checkmark. Wrong blocks get orange highlight with "↕" arrows suggesting they need to move. Distractors used get red X with explanation tooltip.
- **Distractor feedback**: If player hovers over/clicks the red X, tooltip says why this block is wrong.

### Demo Game: Build Binary Search

**Problem**: "Build a binary search function that returns the index of `target` in sorted `arr`, or -1 if not found."

**Correct blocks (scrambled for player):**
1. `def binary_search(arr, target):` (indent 0)
2. `left, right = 0, len(arr) - 1` (indent 1)
3. `while left <= right:` (indent 1)
4. `mid = (left + right) // 2` (indent 2)
5. `if arr[mid] == target:` (indent 2)
6. `return mid` (indent 3)
7. `elif arr[mid] < target:` (indent 2)
8. `left = mid + 1` (indent 3)
9. `else:` (indent 2)
10. `right = mid - 1` (indent 3)
11. `return -1` (indent 1)

**Distractors:**
- `while left < right:` — "Missing the `=` means we skip checking when left == right"
- `mid = (left + right) / 2` — "Integer division (//) is needed, not float division (/)"
- `left = mid` — "Must be `mid + 1` to avoid infinite loop when arr[mid] < target"

---

## 6. Optimization Race

### Overview
The player's algorithm choice/execution is compared against a baseline in real-time. Two algorithms run side-by-side on the same input, visualized as a race. The player learns about algorithmic efficiency by **seeing and feeling** the speed difference.

**Engagement Level:** Evaluating (Naps taxonomy)
**Bloom Level:** Evaluate

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **Sorting Algorithm Animations** | https://www.toptal.com/developers/sorting-algorithms | Study: side-by-side sorting races on different input patterns (random, nearly sorted, reversed, few unique). Clean visualization showing why some sorts win on certain inputs. |
| **VisuAlgo Sorting Race** | https://visualgo.net/en/sorting | Study: run two sorting algorithms simultaneously, same input, watch them race. |
| **BigO Cheat Sheet** | https://www.bigocheatsheet.com/ | Study: the complexity comparison chart. Our race should make players FEEL what this chart shows. |
| **SortVision** | https://www.sortvision.com/ | Study: real-time performance metrics (comparisons, swaps, time) alongside visualization. The metrics dashboard. |
| **Algorithm Visualizer** | https://algorithm-visualizer.org/ | Study: how they show operation counts alongside visualization. Code + visual + metrics unified view. |

### Core Interaction

**Player flow:**
1. Choose two algorithms to race (or: player's choice vs system's optimal)
2. Choose or view the input characteristics (random, sorted, reverse-sorted, duplicates, size)
3. Press "Start Race"
4. Watch split-screen visualization of both algorithms processing the same input
5. Real-time counters show: comparisons, swaps/operations, memory used
6. After race: answer analysis questions — "Why did Algorithm A win?" (multiple choice)
7. **Scaling challenge**: Same algorithms, but double the input size. Watch the gap grow (or shrink).
8. Optional: Player can adjust input type to find scenarios where the "slower" algorithm wins

**Input types:** Click (algorithm selection, input config), Click (analysis answers)

### State Machine

```
INIT → CONFIGURING → RACING → RACE_COMPLETE → ANALYSIS_QUESTIONS →
  ↓ (more rounds)       ↓ (done)
CONFIGURING            COMPLETED
```

### Input Data Schema

```typescript
interface OptimizationRaceData {
  // Available algorithms to race
  algorithms: RaceAlgorithm[];

  // Pre-configured race scenarios (or let player configure)
  scenarios: RaceScenario[];

  // Analysis questions
  analysis_questions: AnalysisQuestion[];

  // Configuration
  player_picks_algorithms: boolean;
  player_picks_input: boolean;
  show_code: boolean;
  show_complexity_labels: boolean;  // Show O(n²), O(n log n) labels
  scaling_mode: boolean;            // Run on increasingly large inputs
}

interface RaceAlgorithm {
  id: string;
  name: string;                     // "Bubble Sort"
  complexity: string;               // "O(n²)"
  code?: CodeBlock;
  description: string;
  color: string;                    // Visual color in race
}

interface RaceScenario {
  scenario_id: string;
  input_type: "random" | "sorted" | "reverse_sorted" | "nearly_sorted" | "few_unique" | "custom";
  input_sizes: number[];            // [10, 50, 100, 500] for scaling mode
  input_data?: any;                 // For custom input
  algorithm_ids: [string, string];  // Which two algorithms race

  // Pre-computed results (for each input size)
  results: RaceResult[];
}

interface RaceResult {
  input_size: number;
  algorithm_results: {
    algorithm_id: string;
    comparisons: number;
    swaps: number;
    total_operations: number;
    execution_steps: any[];         // For animation playback
    finish_time_ms: number;         // Simulated time
  }[];
}

interface AnalysisQuestion {
  question_id: string;
  prompt: string;                   // "Why did merge sort beat bubble sort on this input?"
  options: { id: string; text: string; }[];
  correct_id: string;
  explanation: string;
  points: number;
}
```

### Scoring

```
Correct algorithm choice (if applicable):  +100
Per analysis question correct:             +points (defined per question)
Correct prediction of winner:              +50 per race
Scaling insight (answer about why gap grows): +150

Final score = sum(all question scores)
```

### Visual Components

| Component | Description |
|-----------|-------------|
| **Split-Screen Visualization** | Left: Algorithm A's execution. Right: Algorithm B's. Same data structure, different progress. |
| **Race Progress Bars** | Horizontal bars showing % completion. Algorithm colors. |
| **Metrics Dashboard** | Real-time counters: Comparisons, Swaps, Memory, Operations. Bar chart comparing the two. |
| **Complexity Graph** | (scaling mode) Plot of operations vs input size. Two curves growing. O(n²) visibly pulls away from O(n log n). |
| **Input Config Panel** | (if player configures) Sliders for input size, dropdown for input type. |
| **Algorithm Selector** | Cards for each available algorithm with name + complexity. Player picks two. |
| **Analysis Panel** | Post-race questions with multiple choice. |

### Demo Game: Bubble Sort vs Merge Sort

**Scenario**: Random array, sizes [10, 50, 100]

| Input Size | Bubble Sort Ops | Merge Sort Ops | Winner |
|------------|----------------|----------------|--------|
| 10 | 45 comparisons | 23 comparisons | Merge |
| 50 | 1,225 | 282 | Merge (4x faster) |
| 100 | 4,950 | 664 | Merge (7x faster) |

**Analysis question**: "As input size doubled from 50 to 100, bubble sort's operations grew by ~4x while merge sort's grew by ~2.3x. Why?" → "Bubble sort is O(n²) so doubling n quadruples operations. Merge sort is O(n log n) so doubling n slightly more than doubles operations."

---

## 7. Pathfinder

### Overview
The player navigates through a graph data structure following specific algorithm rules. They click nodes in the correct traversal order, draw shortest paths, or build spanning trees. The graph is the game board.

**Engagement Level:** Constructing (Naps taxonomy)
**Bloom Level:** Apply → Analyze

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **Red Blob Games** | https://www.redblobgames.com/pathfinding/a-star/introduction.html | THE gold standard for interactive graph algorithm tutorials. Study: their "scrubbing" interaction (drag to explore), step-by-step BFS/Dijkstra/A* with frontier visualization, grid-based graph rendering. |
| **Graph Algorithm Simulator** | https://adityapandey-dev.github.io/Graph-Algorithm-Simulator-DAA-Project/ | Study: BFS/DFS/Dijkstra with sound effects, node coloring states, adjacency list/matrix toggle. |
| **Dijkstra Game (Goldsmith's)** | https://www.doc.gold.ac.uk/goldplugins/index.php/2020/03/25/dijkstras-algorithm/ | Study: real metro maps (London, Tokyo, Paris, Delhi, Washington) as graph puzzles. Find shortest paths on real transit networks. |
| **iFlow** (SIGCSE 2025) | https://arxiv.org/abs/2411.10484 | Study: interactive max-flow/min-cut. User selects augmenting paths, updates residual graph. Detailed mistake feedback. Open-sourced. |
| **Graph Traversal Visualizer** | https://vastlywise.com/Graph-Traversal-Visualizer | Study: queue/stack preview panel showing upcoming nodes. Clean step-through with pause/play. |
| **Learn Graph Theory** | https://learngraphtheory.org/ | Study: 23+ interactive visualizations. Clean, modern UI for graph concepts. |

### Core Interaction

**Player flow (BFS/DFS):**
1. See a graph with nodes and edges. Source node is highlighted.
2. Algorithm panel shows the current queue (BFS) or stack (DFS) contents
3. Player clicks the next node to visit (must match algorithm's next choice)
4. If correct: node colors as "visited", neighbors added to queue/stack, edge to parent highlights
5. If incorrect: "BFS visits nodes in FIFO order — the next node should be [X]"
6. Continue until all reachable nodes visited

**Player flow (Dijkstra):**
1. See a weighted graph. Source node highlighted. Distance table shown.
2. Player selects the unvisited node with minimum tentative distance
3. Player then updates neighbor distances ("relaxation") by clicking neighbors
4. Continue until all nodes processed
5. Draw the shortest path by clicking nodes from source to target

**Player flow (MST):**
1. See a weighted graph. Player builds the spanning tree by clicking edges.
2. System validates: does this edge create a cycle? Is it the minimum-weight valid edge?
3. Continue until n-1 edges selected.

**Input types:** Click (node selection, edge selection), Drag (for rearranging graph layout)

### State Machine

```
INIT → AWAITING_NODE_CLICK → NODE_CLICKED →
  ↓ (correct)                      ↓ (incorrect)
NODE_VISITED → (update queue/distances) → AWAITING_NODE_CLICK
                                         WRONG_NODE_FEEDBACK → AWAITING_NODE_CLICK
  ↓ (all nodes visited)
PATH_DRAWING (optional) → COMPLETED
```

### Input Data Schema

```typescript
interface PathfinderData {
  algorithm_name: string;           // "bfs", "dfs", "dijkstra", "prim", "kruskal"
  algorithm_description: string;

  // Graph definition
  graph: GraphDefinition;

  // Algorithm-specific config
  source_node: string;              // Starting node
  target_node?: string;             // For shortest path problems

  // Execution trace
  steps: PathfinderStep[];

  // Final answer (for path-drawing phase)
  optimal_path?: string[];          // Node sequence for shortest path
  optimal_tree_edges?: [string, string][]; // For MST

  // Configuration
  graph_type: "directed" | "undirected";
  weighted: boolean;
  show_queue_stack: boolean;
  show_distance_table: boolean;
  allow_path_drawing: boolean;      // Final phase: draw the answer path
  layout: "force_directed" | "grid" | "circular" | "hierarchical" | "custom";
}

interface GraphDefinition {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface GraphNode {
  id: string;
  label: string;
  x?: number;                       // Custom position
  y?: number;
  metadata?: any;                   // Domain-specific data
}

interface GraphEdge {
  from: string;
  to: string;
  weight?: number;
  label?: string;
}

interface PathfinderStep {
  step_number: number;
  action: "visit_node" | "update_distance" | "add_edge" | "backtrack";

  // What the player should do
  expected_target: string;          // Node or edge ID

  // State after step
  visited: string[];
  queue_or_stack: string[];
  distances?: { [nodeId: string]: number };     // For Dijkstra
  tree_edges?: [string, string][];              // For MST
  current_node: string;

  explanation: string;
}
```

### Scoring

```
Correct node/edge selection:        +75
Correct distance update:            +50
Wrong selection:                    -20
Path drawing (final):               +200 if optimal, +100 if valid but not optimal, 0 if invalid
Hint used:                          -30 per hint

Final score = sum(step_scores) + path_score
```

### Visual Components

| Component | Description |
|-----------|-------------|
| **Graph Canvas** | Interactive graph rendering (force-directed or grid). Nodes are clickable circles. Edges are lines with optional weight labels. |
| **Node States** | Unvisited (white/gray), In-queue/stack (yellow), Visited (blue/green), Current (pulsing gold). |
| **Edge States** | Unvisited (gray), Tree edge (green/thick), Back edge (red dashed), Cross edge (purple). |
| **Queue/Stack Panel** | Side panel showing contents. BFS: queue (FIFO). DFS: stack (LIFO). Animated push/pop. |
| **Distance Table** | (Dijkstra) Table with columns: Node, Tentative Distance, Previous Node. Updates with animations. |
| **Path Overlay** | (drawing phase) Player clicks nodes to draw path. Thick colored line follows clicks. |

### Demo Game: BFS on a 7-node Graph

**Graph**:
```
    A --- B --- E
    |     |     |
    C --- D --- F
          |
          G
```
**Source**: A. **Player should visit**: A → B, C (any order) → D, E → F → G

---

## 8. Pattern Matcher

### Overview
The player identifies algorithms from their behavior, matches names to properties, or classifies algorithm characteristics. This tests recognition and conceptual understanding — the "reading" side of algorithm literacy.

**Engagement Level:** Responding (Naps taxonomy)
**Bloom Level:** Remember → Analyze

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **Sorting Algorithm Animations** | https://www.toptal.com/developers/sorting-algorithms | Study: how different sorts look visually distinct — bubble sort's characteristic left-to-right sweep, merge sort's recursive halving, quicksort's partition jumps. Watching an animation, you can ID the sort. |
| **VisuAlgo Quiz Mode** | https://visualgo.net/en/sorting?slide=18 | Study: their quiz "Which sorting algorithm is being shown?" with animation playback. |
| **Brilliant.org Matching** | https://brilliant.org/ | Study: their drag-to-match and select-the-correct-answer exercises. Clean, focused, immediate feedback. |

### Core Interaction

**Player flow (Identify-from-Animation):**
1. Watch a short animation of an algorithm executing on data
2. "Which algorithm is this?" → Select from 3-4 options
3. Feedback: correct name + explanation of the identifying characteristic

**Player flow (Property Matching):**
1. Left column: algorithm names. Right column: properties/characteristics.
2. Drag lines to connect each algorithm to its properties.
3. Properties: "O(n log n) worst case", "In-place", "Stable", "Comparison-based", etc.

**Player flow (Behavior Classification):**
1. See a description of algorithm behavior (without the name)
2. "This algorithm always picks the locally optimal choice at each step" → "Greedy"
3. Multiple choice or type answer

**Input types:** Click (multiple choice), Drag (matching lines), Type (classification)

### State Machine

```
INIT → SHOWING_CHALLENGE → AWAITING_ANSWER → ANSWER_REVEALED →
  ↓ (more challenges)        ↓ (done)
SHOWING_CHALLENGE           COMPLETED
```

### Input Data Schema

```typescript
interface PatternMatcherData {
  challenges: PatternChallenge[];
  mode: "identify" | "match" | "classify" | "mixed";
}

interface PatternChallenge {
  challenge_id: string;
  type: "identify_animation" | "match_properties" | "classify_behavior" | "name_complexity" | "compare_algorithms";

  // For identify_animation
  animation?: {
    algorithm_name: string;
    execution_steps: any[];         // Same as ManualStep[] for animation playback
    initial_state: DataStructureState;
  };

  // For match_properties
  matching?: {
    left_items: { id: string; text: string; }[];   // Algorithm names
    right_items: { id: string; text: string; }[];   // Properties
    correct_pairs: [string, string][];               // [left_id, right_id]
  };

  // For classify_behavior
  classification?: {
    description: string;            // "This algorithm divides the problem in half, solves each half, then combines..."
    options: { id: string; text: string; }[];
    correct_id: string;
  };

  // For name_complexity
  complexity?: {
    algorithm_name: string;
    code?: CodeBlock;
    options: { id: string; text: string; }[];  // "O(n)", "O(n log n)", "O(n²)", "O(2^n)"
    correct_id: string;
    case: "best" | "average" | "worst";
  };

  explanation: string;
  points: number;
}
```

### Scoring

```
Correct identification:             +points (per challenge)
Matching (per correct pair):        +50
Matching (per wrong pair):          -25
Speed bonus (optional):             +20% if answered in < 5 seconds
Hint used:                          -30% per hint

Final score = sum(challenge_scores)
```

### Demo Game: "Name That Sort"

**Challenge 1**: Watch an animation of an array being sorted. The animation shows:
- Picks last element as pivot
- Partitions remaining elements left/right
- Recursively processes each side
→ Answer: Quick Sort

**Challenge 2**: Match algorithms to properties:
| Algorithm | Property |
|-----------|----------|
| Merge Sort | Stable, O(n log n) worst case, requires O(n) extra space |
| Quick Sort | In-place, O(n²) worst case, O(n log n) average |
| Heap Sort | In-place, O(n log n) worst case, NOT stable |

---

## 9. Constraint Puzzle

### Overview
Algorithm-inspired puzzles where the player solves a problem that IS the algorithm. N-Queens IS backtracking. Knapsack IS dynamic programming. The player solves the puzzle, and in doing so, learns the algorithm — without necessarily seeing code.

**Engagement Level:** Constructing (Naps taxonomy)
**Bloom Level:** Apply → Create

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **CS Unplugged: Muddy City** | https://classic.csunplugged.org/minimal-spanning-trees/ | Study: MST as "pave roads in a muddy city" puzzle. No code, no math — just the algorithmic concept as a physical puzzle. Brilliant for intuition building. |
| **Chromagraph** | https://adam-rumpf.github.io/games/chromagraph/extras.html | Study: graph coloring as a puzzle game. Clean UX, progressive difficulty, level design. |
| **Human Resource Machine** | https://tomorrowcorporation.com/humanresourcemachine | Study: how they make low-level computation (assembly) feel like a puzzle. The constraint is the game. ~40 puzzle levels. |
| **Tower of Hanoi (Interactive)** | https://www.analog-clock.org/tools/tower-of-hanoi | Study: classic recursion puzzle UX. Disk drag-and-drop, move counter, minimum moves display. |
| **N-Queens Visualizer** | (many implementations) | Study: constraint highlighting — when you place a queen, immediately show all threatened squares. Visual constraint propagation. |
| **IFDB Knapsack Problem** | https://ifdb.org/viewgame?id=55xxh7ozya1u1yxx | Study: text-adventure optimization puzzle. Knapsack as narrative. |
| **Coin Change Interactive** | https://gallery.selfboot.cn/en/algorithms/dpcoin | Study: DP table visualization for coin change. Color-coded optimal decisions. |

### Core Interaction

**Player flow:**
1. See the puzzle setup (chessboard, backpack, timeline, map, etc.)
2. Read the constraint rules (no two queens threaten each other, weight limit, etc.)
3. Make moves: place pieces, select items, draw connections
4. System enforces constraints in real-time (invalid moves are blocked or highlighted)
5. Player can undo moves
6. Goal: satisfy all constraints (or optimize an objective)
7. After completion: reveal the algorithm connection — "You just performed backtracking!"

**The puzzle IS the algorithm. Player discovers the algorithm through gameplay.**

**Input types:** Click (placement), Drag (items), Toggle (include/exclude), Draw (connections)

### State Machine

```
INIT → PLAYING →
  ↓ (move)
VALIDATING_MOVE →
  ↓ (valid)           ↓ (invalid)
MOVE_APPLIED         MOVE_REJECTED (highlight conflict)
  ↓                    ↓
PLAYING              PLAYING
  ↓ (goal met)
PUZZLE_SOLVED → ALGORITHM_REVEAL → COMPLETED
```

### Input Data Schema

```typescript
interface ConstraintPuzzleData {
  puzzle_type: "n_queens" | "knapsack" | "coin_change" | "activity_selection" | "graph_coloring" | "mst_connect" | "sudoku" | "subset_sum" | "tower_of_hanoi";

  title: string;
  narrative: string;                // Story framing: "You're a treasure hunter..."
  rules: string[];                  // Constraint rules in plain language
  objective: string;                // "Maximize total value" or "Place all queens safely"

  // Puzzle-specific data (discriminated by puzzle_type)
  puzzle_data: PuzzleData;          // See below for each type

  // Solution(s)
  optimal_solution: any;            // The best solution (for scoring comparison)
  all_valid_solutions?: any[];      // All valid solutions (for acceptance checking)

  // Algorithm connection (revealed after solving)
  algorithm_name: string;
  algorithm_explanation: string;    // "You just used backtracking! Here's how..."

  // Configuration
  show_constraints_visually: boolean; // Highlight threats/conflicts
  show_optimality_score: boolean;   // Show "Your solution: 85% of optimal"
  allow_undo: boolean;
  hint_budget: number;
}

// N-Queens specific
interface NQueensPuzzleData {
  board_size: number;               // 4, 6, 8
  pre_placed?: { row: number; col: number }[]; // Starter queens
}

// Knapsack specific
interface KnapsackPuzzleData {
  capacity: number;
  items: { id: string; name: string; weight: number; value: number; icon?: string }[];
}

// Coin Change specific
interface CoinChangePuzzleData {
  target_amount: number;
  denominations: number[];
  unlimited_coins: boolean;
}

// Activity Selection specific
interface ActivitySelectionPuzzleData {
  activities: { id: string; name: string; start: number; end: number }[];
  num_rooms?: number;               // For multi-room variant
}

// Graph Coloring specific
interface GraphColoringPuzzleData {
  graph: GraphDefinition;
  available_colors: string[];
  max_colors?: number;              // Chromatic number challenge
}

// MST specific
interface MSTConnectPuzzleData {
  graph: GraphDefinition;           // Weighted graph
  budget?: number;                  // Optional total weight limit
}

// Tower of Hanoi specific
interface TowerOfHanoiPuzzleData {
  num_disks: number;
  num_pegs: number;                 // 3 (classic) or 4 (Frame-Stewart)
}
```

### Scoring

```
Puzzle solved:                      +200 base
Optimality ratio:                   solution_value / optimal_value * 200 bonus
  (For knapsack: value ratio. For N-Queens: 1.0 if solved, 0 if not.)
Minimum moves bonus (Hanoi):        +100 if solved in 2^n - 1 moves
Minimum colors bonus (coloring):    +100 if chromatic number achieved
No hints used:                      +50 bonus
Speed bonus:                        None (thinking > speed)

Final score = base + optimality_bonus + special_bonus + no_hint_bonus
```

### Demo Game: 0/1 Knapsack as "Treasure Packing"

**Narrative**: "You've found a treasure room! Your backpack holds 15 kg. Choose wisely."

| Item | Weight | Value |
|------|--------|-------|
| Gold Crown | 5 kg | $120 |
| Silver Goblet | 3 kg | $80 |
| Diamond Ring | 1 kg | $60 |
| Bronze Shield | 8 kg | $150 |
| Emerald Necklace | 4 kg | $100 |
| Ancient Scroll | 2 kg | $40 |

**Optimal**: Diamond Ring (1) + Gold Crown (5) + Emerald Necklace (4) + Silver Goblet (3) + Ancient Scroll (2) = 15 kg, $400
**Greedy (by value/weight)** would pick differently — teaching moment!

---

## 10. Code Completion

### Overview
A partial algorithm implementation with key lines or expressions missing. The player fills in the blanks. Difficulty scales by removing more code. This is the middle ground between reading code (Predict-Output) and writing code (Algorithm Builder).

**Engagement Level:** Constructing (Naps taxonomy)
**Bloom Level:** Apply → Create

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **JPLAS System** | https://ieeexplore.ieee.org/document/6669019/ | Study: graph-based blank element selection algorithm — selects blanks with unique, grammatically correct answers. Important for auto-generating good blanks. |
| **Exercism** | https://exercism.org/ | Study: their guided exercises that start with skeleton code + tests. The player fills in functions. Clean UX, test-driven feedback. |
| **LeetCode** | https://leetcode.com/ | Study: their code editor with pre-filled function signatures. The player completes the body. |
| **CodingBat** | https://codingbat.com/ | Study: fill-in-the-function with immediate test feedback. Simple, focused, effective. |

### Core Interaction

**Player flow:**
1. See partial code with blanks highlighted (grayed-out slots in the code)
2. Each blank has a prompt: "Fill in the comparison operator" or "Complete this line"
3. Player clicks a blank → input appears:
   - **Multiple choice**: Select from options
   - **Expression input**: Type a code expression
   - **Line input**: Type a full line of code
4. Fill all blanks and submit
5. System validates each blank independently
6. Optional: run completed code on test cases to verify

**Input types:** Click (multiple choice), Type (expressions/lines)

### State Machine

```
INIT → FILLING_BLANKS → BLANK_FOCUSED → INPUT_ENTERED → FILLING_BLANKS →
  ↓ (all blanks filled)
SUBMITTED → VALIDATING → RESULTS →
  ↓ (has errors)        ↓ (all correct)
RETRY                 COMPLETED (optional: run tests)
```

### Input Data Schema

```typescript
interface CodeCompletionData {
  algorithm_name: string;
  algorithm_description: string;

  // The template code with blanks
  code_template: CodeTemplate;

  // Configuration
  language: "python" | "javascript" | "pseudocode";
  input_mode: "multiple_choice" | "free_text" | "mixed";
  allow_resubmit: boolean;
  run_tests_after: boolean;

  // Test cases (for verification)
  test_cases?: TestCase[];
}

interface CodeTemplate {
  lines: TemplateLine[];
}

interface TemplateLine {
  line_number: number;
  text: string;                     // Full line with blank markers: "if arr[mid] __BLANK_1__ target:"
  blanks: BlankDefinition[];
  is_blank_line: boolean;           // true if the entire line is a blank
}

interface BlankDefinition {
  blank_id: string;
  placeholder: string;              // "__BLANK_1__" or "___"
  prompt: string;                   // "What comparison operator goes here?"

  correct_answer: string;           // "=="
  acceptable_alternatives?: string[]; // ["==", "is"] for Python

  // For multiple choice
  options?: { id: string; text: string; feedback: string; }[];
  correct_option_id?: string;

  // Metadata
  difficulty: 1 | 2 | 3;
  hint: string;
  explanation: string;              // Why this is correct

  // Validation
  validation_type: "exact" | "regex" | "ast_equivalent";
  validation_pattern?: string;      // Regex for flexible matching
}
```

### Scoring

```
Per blank correct on first fill:    +100 * difficulty_multiplier
Per blank correct on resubmit:      +50 * difficulty_multiplier
Per blank wrong:                    0
Hint used:                          -30% of blank's points
All blanks correct on first submit: +100 bonus
All tests pass:                     +100 bonus

difficulty_multiplier: easy=1.0, medium=1.5, hard=2.0
```

### Demo Game: Complete Dijkstra's Algorithm

```python
def dijkstra(graph, source):
    dist = {node: float('inf') for node in graph}
    dist[source] = ____BLANK_1____          # What's the distance from source to itself?
    visited = set()
    pq = [(0, source)]

    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            ____BLANK_2____                  # What should we do if already visited?
        visited.add(u)

        for v, weight in graph[u]:
            if v not in visited:
                new_dist = ____BLANK_3____   # How do we compute the new distance?
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    heapq.heappush(pq, ____BLANK_4____)  # What do we push?

    return dist
```

**Blanks:**
1. `0` — "Distance from source to itself is zero"
2. `continue` — "Skip already-processed nodes"
3. `d + weight` — "New distance = current distance + edge weight"
4. `(new_dist, v)` — "Push (distance, node) tuple to priority queue"

---

## 11. Test Case Designer

### Overview
The player creates inputs that expose specific algorithm behaviors — worst cases, edge cases, or inputs that break buggy code. This flips the typical paradigm: instead of running code on given input, the player **designs the input**.

**Engagement Level:** Creating (Naps taxonomy)
**Bloom Level:** Evaluate → Create

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **Code Defenders** | https://code-defenders.org/ | Study: mutation testing game where ATTACKERS design inputs that distinguish buggy code from correct code. This IS our mechanic. |
| **Codeforces Hacking** | https://codeforces.com/ | Study: during contest, you can "hack" others' solutions by providing counter-examples. The test case design as competitive element. |
| **LeetCode Custom Test Cases** | https://leetcode.com/ | Study: their custom test case runner. Type input → see output. Simple but effective. |
| **Property-Based Testing** (Hypothesis) | https://hypothesis.readthedocs.io/ | Study: how property-based testing generates adversarial inputs. The thinking behind "what input would break this?" is what we're teaching. |

### Core Interaction

**Player flow:**
1. See the challenge: "Design an input that causes quicksort to run in O(n²) time" or "Find an input where this buggy code gives wrong output"
2. Player constructs an input:
   - For arrays: type numbers or drag elements
   - For graphs: draw nodes and edges
   - For trees: build by inserting values
3. Press "Test" → System runs the algorithm on the player's input
4. System checks if the input achieves the goal:
   - "Your input caused 45 comparisons. O(n²) for n=10 would be ~100. Try a different input pattern."
   - "Your input produced the wrong output! Bug exposed!"
5. Player iterates until they find a satisfying input
6. After success: explanation of why this input triggers the behavior

**Input types:** Type (values), Drag (construction), Click (graph builder)

### State Machine

```
INIT → CONSTRUCTING_INPUT → INPUT_SUBMITTED → TESTING →
  ↓ (goal met)          ↓ (goal not met)
GOAL_ACHIEVED          TRY_AGAIN_FEEDBACK → CONSTRUCTING_INPUT
  ↓
EXPLANATION → COMPLETED
```

### Input Data Schema

```typescript
interface TestCaseDesignerData {
  challenge_type: "worst_case" | "break_buggy_code" | "best_case" | "distinguish_algorithms" | "edge_case";

  description: string;              // "Design an input array that causes quicksort to perform O(n²) comparisons"

  // Algorithm(s) involved
  algorithm: AlgorithmSpec;
  buggy_algorithm?: AlgorithmSpec;  // For "break buggy code" challenges

  // Input constraints
  input_schema: InputSchema;

  // Goal definition
  goal: TestGoal;

  // Hints
  hints: string[];

  // Explanation (shown after success)
  explanation: string;
  example_solution: any;            // One valid answer
}

interface AlgorithmSpec {
  name: string;
  code: CodeBlock;
  runner: string;                   // Function name to call
}

interface InputSchema {
  type: "array" | "graph" | "tree" | "string" | "number";
  constraints: {
    min_size?: number;
    max_size?: number;
    min_value?: number;
    max_value?: number;
    sorted?: boolean;
    unique?: boolean;
  };
}

interface TestGoal {
  type: "operation_count_exceeds" | "wrong_output" | "output_differs" | "specific_behavior";

  // For operation count
  operation_threshold?: number;     // Must exceed this many operations

  // For wrong output
  expected_output_fn?: string;      // Function that computes correct output for any input

  // For output differs (distinguish two algorithms)
  second_algorithm?: AlgorithmSpec;

  // For specific behavior
  behavior_check?: string;          // "The algorithm enters an infinite loop" or "Stack overflow"
}
```

### Scoring

```
Goal achieved on 1st attempt:      +300
Goal achieved on 2nd attempt:      +200
Goal achieved on 3rd+ attempt:     +100
Each failed attempt:                 0 (no penalty, learning through iteration)
Hint used:                          -50 per hint
Optimal input (minimal size):       +100 bonus

Final score = attempt_score + optimal_bonus - hint_penalties
```

### Demo Game: Break the Buggy Binary Search

**Challenge**: "This binary search has a bug. Design an input where it returns the WRONG answer."

**Buggy code** (uses `left < right` instead of `left <= right`):
```python
def buggy_search(arr, target):
    left, right = 0, len(arr) - 1
    while left < right:  # BUG
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**Player needs to find**: Any input where the target is at an index where `left == right` at some point. Example: `arr = [1, 3, 5], target = 5` → correct answer is `2`, buggy code returns `-1`.

---

## 12. Complexity Analyzer

### Overview
Given code or a visualization, the player identifies time/space complexity. They may watch the algorithm on growing inputs and infer the complexity class from the growth pattern. This teaches Big-O reasoning through empirical observation.

**Engagement Level:** Analyzing (Naps taxonomy)
**Bloom Level:** Analyze → Evaluate

### References & Inspiration

| Platform | URL | What to Learn |
|----------|-----|---------------|
| **Big-O Cheat Sheet** | https://www.bigocheatsheet.com/ | Study: the visual complexity comparison chart. Our game should make players construct this chart through observation. |
| **VisuAlgo Analysis** | https://visualgo.net/en/sorting | Study: how they show operation counts at different input sizes. The player can adjust n and see counts change. |
| **Brilliant.org Complexity** | https://brilliant.org/ | Study: their interactive complexity quizzes. "What's the complexity of this code?" with visual code annotation. |
| **Algorithm Visualizer** | https://algorithm-visualizer.org/ | Study: code with operation counter. As code runs, counter ticks up. |

### Core Interaction

**Player flow (Identify-from-Code):**
1. See algorithm code with loops highlighted
2. "What is the time complexity of this algorithm?" → Select O(1), O(log n), O(n), O(n log n), O(n²), O(2^n)
3. Feedback: correct answer with explanation pointing to the relevant loops/recursion

**Player flow (Infer-from-Growth):**
1. Algorithm runs on input sizes n=10, 50, 100, 500, 1000
2. Operation counts are plotted on a graph
3. Player observes the curve shape and selects the matching complexity class
4. System overlays the theoretical curve to confirm

**Player flow (Bottleneck-Finder):**
1. See code with multiple sections
2. "Which section is the bottleneck?" → Click on the loop/call that dominates
3. "What's its complexity?" → Select
4. "What's the overall complexity?" → Select

**Input types:** Click (multiple choice, line selection)

### State Machine

```
INIT → SHOWING_CHALLENGE → AWAITING_ANSWER →
  ↓ (correct)          ↓ (wrong)
ANSWER_CORRECT       ANSWER_WRONG → SHOWING_CHALLENGE (retry or next)
  ↓ (more challenges)
SHOWING_CHALLENGE → ... → COMPLETED
```

### Input Data Schema

```typescript
interface ComplexityAnalyzerData {
  challenges: ComplexityChallenge[];
}

interface ComplexityChallenge {
  challenge_id: string;
  type: "identify_from_code" | "infer_from_growth" | "find_bottleneck" | "compare_complexities";

  // For identify_from_code
  code?: CodeBlock;

  // For infer_from_growth
  growth_data?: {
    input_sizes: number[];
    operation_counts: number[];
  };

  // For find_bottleneck
  code_sections?: {
    section_id: string;
    start_line: number;
    end_line: number;
    complexity: string;
    is_bottleneck: boolean;
  }[];

  // Answer
  correct_complexity: string;       // "O(n log n)"
  options: string[];                // ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)", "O(n³)", "O(2^n)"]

  explanation: string;
  points: number;
  hints: string[];
}
```

### Scoring

```
Correct complexity identification:   +points (per challenge, typically 100-150)
Correct bottleneck line:            +100
Wrong answer:                        0
Hint used:                          -30% per hint
All challenges perfect:             +150 bonus
```

### Demo Game: Identify Complexities

**Challenge 1** (Easy):
```python
def find_max(arr):
    max_val = arr[0]
    for x in arr:        # Single loop over n elements
        if x > max_val:
            max_val = x
    return max_val
```
→ O(n)

**Challenge 2** (Medium):
```python
def has_pair_sum(arr, target):
    for i in range(len(arr)):           # Outer: n iterations
        for j in range(i+1, len(arr)):  # Inner: ~n/2 iterations
            if arr[i] + arr[j] == target:
                return True
    return False
```
→ O(n²)

**Challenge 3** (Hard — infer from data):
| n | Operations |
|---|-----------|
| 10 | 33 |
| 100 | 664 |
| 1,000 | 9,966 |
| 10,000 | 132,877 |

Plot shows slightly-better-than-linear growth → O(n log n)

---

## Appendix: Shared Type Definitions

Types referenced across multiple mechanics:

```typescript
// Shared across all mechanics
interface TestCase {
  input_description: string;
  input_data: any;
  expected_output: any;
  explanation?: string;
}

type AlgorithmCategory =
  | "sorting" | "searching" | "graph_traversal" | "shortest_path" | "mst"
  | "trees" | "dynamic_programming" | "greedy" | "backtracking"
  | "divide_and_conquer" | "string" | "hashing" | "recursion"
  | "network_flow" | "computational_geometry";

// Data structure state (polymorphic)
interface DataStructureState {
  type: "array" | "graph" | "tree" | "table" | "linked_list" | "stack" | "queue" | "heap" | "grid" | "chessboard";
  data: any;
}

// Array-specific state
interface ArrayState {
  type: "array";
  data: {
    elements: any[];
    active_indices: number[];       // Currently being compared/processed
    sorted_indices: number[];       // Already in final position
    highlight_groups?: { indices: number[]; color: string; label?: string; }[];
  };
}

// Graph-specific state
interface GraphState {
  type: "graph";
  data: {
    nodes: { id: string; label: string; x?: number; y?: number; state: "unvisited" | "in_frontier" | "visiting" | "visited"; }[];
    edges: { from: string; to: string; weight?: number; state: "default" | "tree_edge" | "back_edge" | "cross_edge" | "highlighted"; }[];
    queue_or_stack?: string[];
    distances?: { [nodeId: string]: number | "∞"; };
    current_node?: string;
  };
}

// Tree-specific state
interface TreeState {
  type: "tree";
  data: {
    root: TreeNode;
    highlighted_path?: string[];
    highlighted_nodes?: { id: string; color: string; }[];
  };
}

interface TreeNode {
  id: string;
  value: any;
  left?: TreeNode;
  right?: TreeNode;
  children?: TreeNode[];
  metadata?: { balance_factor?: number; color?: "red" | "black"; height?: number; };
}

// Table-specific state (DP)
interface TableState {
  type: "table";
  data: {
    rows: number;
    cols: number;
    row_headers?: string[];
    col_headers?: string[];
    cells: (number | string | null)[][];
    active_cell?: [number, number];
    filled_cells: [number, number][];
    dependency_arrows?: { from: [number, number]; to: [number, number]; }[];
  };
}

// Grid-specific state (Chessboard, Sudoku, etc.)
interface GridState {
  type: "grid";
  data: {
    rows: number;
    cols: number;
    cells: GridCell[][];
  };
}

interface GridCell {
  value: any;
  state: "empty" | "filled" | "blocked" | "highlighted" | "conflicting";
  color?: string;
  icon?: string;
}
```

---

## Appendix: Demo Game Summary

| # | Mechanic | Demo Algorithm | Demo Input | Key Interaction |
|---|----------|---------------|------------|-----------------|
| 1 | State Tracer | Bubble Sort | [5, 3, 1, 4, 2] | Predict array state after each swap |
| 2 | Bug Hunter | Binary Search | [1,3,5,7,9], target=9 | Find off-by-one in while condition |
| 3 | Manual Execution | Merge Sort (merge) | [1,5,8] + [2,3,7] | Click smaller top element to merge |
| 4 | Predict-Output | Quick Sort partition | [7,2,1,6,8,5,3,4] | Predict partition result |
| 5 | Algorithm Builder | Binary Search | (Parsons blocks) | Reorder scrambled binary search code |
| 6 | Optimization Race | Bubble vs Merge Sort | Random arrays 10-100 | Watch race, answer why merge wins |
| 7 | Pathfinder | BFS | 7-node graph | Click nodes in BFS order |
| 8 | Pattern Matcher | Sorting algorithms | (animations) | Identify sort from animation |
| 9 | Constraint Puzzle | 0/1 Knapsack | 6 items, 15kg limit | Pack backpack for max value |
| 10 | Code Completion | Dijkstra | (partial code) | Fill 4 blanks in Dijkstra's algorithm |
| 11 | Test Case Designer | Buggy Binary Search | (player-designed) | Design input that exposes the bug |
| 12 | Complexity Analyzer | Various | (code + growth data) | Identify Big-O from code/growth curve |
