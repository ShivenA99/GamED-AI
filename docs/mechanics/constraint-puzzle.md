# Constraint Puzzle — Mechanic Specification

> **Status:** Frontend complete (4 demos, 4 puzzle types). Backend generation not yet implemented.
> **Template type:** `ALGORITHM_GAME`
> **Entry point:** `frontend/src/components/templates/AlgorithmGame/ConstraintPuzzleGame.tsx`

---

## 1. What It Does

Constraint Puzzle is an **algorithm-as-puzzle** mechanic where students solve classic optimization problems by hand, then learn the algorithmic technique behind the optimal solution.

Four puzzle types:

1. **Knapsack** — Select items with weight/value to maximize value under a weight limit
2. **N-Queens** — Place queens on a chessboard so none threaten each other
3. **Coin Change** — Make exact change using the fewest coins possible
4. **Activity Selection** — Select the maximum number of non-overlapping activities

The student must:
1. Understand the constraints (capacity, conflicts, exactness, overlap)
2. Explore the solution space manually
3. Submit a valid solution
4. Compare their result to the optimal
5. Learn the algorithm (DP, backtracking, greedy) that solves it optimally

**Bloom Level:** Apply → Evaluate
**Naps Taxonomy Level:** Applying, Evaluating
**Pedagogical approach:** Experience the problem first, then learn the algorithm — builds intuition before formalization

---

## 2. Pedagogical Design

### 2.1 Problem-First Learning

Traditional algorithm teaching presents the algorithm first and problems second. Constraint Puzzle inverts this:

1. **Engage** — Student encounters a real-feeling optimization problem (packing a backpack, scheduling meetings)
2. **Explore** — Student solves it manually using intuition and trial-and-error
3. **Compare** — System reveals how close the student's solution is to optimal
4. **Learn** — Algorithm reveal explains the technique (DP, greedy, backtracking) and why it works
5. **Reflect** — Student sees the gap between intuition and optimal, motivating the algorithm

### 2.2 Puzzle Type → Algorithm Mapping

| Puzzle Type | Algorithm | Technique | Key Insight |
|------------|-----------|-----------|-------------|
| Knapsack | 0/1 Knapsack | Dynamic Programming | Optimal substructure: best with item i = max(without i, with i + best for remaining capacity) |
| N-Queens | N-Queens | Backtracking | Prune invalid branches early; constraint propagation reduces search space |
| Coin Change | Coin Change | Dynamic Programming | Build up from smallest amounts; greedy fails for non-standard denominations |
| Activity Selection | Activity Selection | Greedy | Always pick the activity that finishes earliest — provably optimal |

### 2.3 Optimality as Teaching Metric

Instead of binary correct/incorrect, Constraint Puzzle uses **optimality ratio**:
- `playerValue / optimalValue` expressed as a percentage
- 100% = optimal solution found
- 80% = good but suboptimal
- This teaches that algorithms exist specifically to find optimal solutions in NP-hard or complex search spaces

### 2.4 Constraint Visualization

Each puzzle type visually communicates constraints:
- **Knapsack**: Weight bar fills up as items are added, turns red at capacity
- **N-Queens**: Threatened squares highlighted, conflicting queens shown in red
- **Coin Change**: Running sum with progress bar toward target
- **Activity Selection**: Timeline with overlapping bars, selected activities highlighted

---

## 3. Blueprint Data Contract

```typescript
type ConstraintPuzzleType =
  | 'knapsack'
  | 'n_queens'
  | 'coin_change'
  | 'activity_selection';

interface KnapsackItem {
  id: string;
  name: string;
  weight: number;
  value: number;
  icon: string;           // Emoji icon
}

interface KnapsackPuzzleData {
  type: 'knapsack';
  capacity: number;
  items: KnapsackItem[];
}

interface NQueensPuzzleData {
  type: 'n_queens';
  boardSize: number;       // 4-8 typically
  prePlaced?: { row: number; col: number }[];  // Fixed queens for easier puzzles
}

interface CoinChangePuzzleData {
  type: 'coin_change';
  targetAmount: number;
  denominations: number[];
}

interface ActivitySelectionItem {
  id: string;
  name: string;
  start: number;
  end: number;
}

interface ActivitySelectionPuzzleData {
  type: 'activity_selection';
  activities: ActivitySelectionItem[];
}

type PuzzleData =
  | KnapsackPuzzleData
  | NQueensPuzzleData
  | CoinChangePuzzleData
  | ActivitySelectionPuzzleData;

interface ConstraintPuzzleBlueprint {
  puzzleType: ConstraintPuzzleType;
  title: string;                      // "Camping Trip Packing"
  narrative: string;                  // Story context
  rules: string[];                    // Constraint list
  objective: string;                  // One-line goal
  puzzleData: PuzzleData;
  optimalValue: number;               // Best achievable score
  optimalSolutionDescription: string; // Optimal solution explained
  algorithmName: string;              // "0/1 Knapsack (Dynamic Programming)"
  algorithmExplanation: string;       // Algorithm teaching text
  showConstraintsVisually: boolean;
  showOptimalityScore: boolean;
  allowUndo: boolean;
  hints: [string, string, string];
}
```

---

## 4. Scoring System

| Event | Points |
|-------|--------|
| Base score | `300 × min(optimalityRatio, 1)` |
| Optimal solution bonus | +100 |
| No hints used bonus | +50 |
| Hint penalty | -40 per hint tier |

**Max possible**: 300 + 100 + 50 = 450 points (optimal solution, no hints).

**Optimality ratio**: `playerValue / optimalValue`
- Knapsack: total value of selected items
- N-Queens: number of queens placed (must equal board size for valid solution)
- Coin Change: `targetAmount / numberOfCoins` (fewer coins = higher ratio)
- Activity Selection: number of non-overlapping activities selected

---

## 5. Validation Rules

### Knapsack
- Total weight of selected items must not exceed capacity
- At least one item must be selected
- Player value = sum of selected item values

### N-Queens
- Exactly N queens must be placed on an N×N board
- No two queens share a row, column, or diagonal
- Pre-placed queens cannot be moved

### Coin Change
- Sum of selected coins must exactly equal the target amount
- Coins can be reused (unlimited supply per denomination)
- Optimality measured by fewest coins used

### Activity Selection
- No two selected activities can overlap (start < previous end)
- At least one activity must be selected
- Activities sharing an endpoint (one ends when another starts) are allowed

---

## 6. Hint System

Uses the existing `HintSystem` component with 3-tier progressive hints:

| Tier | Penalty | Typical Content |
|------|---------|-----------------|
| 1 — Nudge | -40 | General strategy hint |
| 2 — Clue | -40 | Specific technique or observation |
| 3 — Answer | -40 | Near-complete solution description |

Maximum 3 hints per puzzle, -120 points total if all used.

---

## 7. State Machine

```
INIT → (CP_START) → PLAYING → (CHECK_SOLUTION) →
  ├── invalid → PLAYING (with error feedback)
  └── valid → PUZZLE_SOLVED → (REVEAL_ALGORITHM) → ALGORITHM_REVEAL
                            → (CP_COMPLETE) → COMPLETED
                └── (CP_COMPLETE) → COMPLETED (skip reveal)
```

### Phases

| Phase | Description |
|-------|-------------|
| `INIT` | Title, narrative, rules, objective, start button |
| `PLAYING` | Puzzle board + constraint visualization + hints + check button |
| `PUZZLE_SOLVED` | Optimality score, option to reveal algorithm or skip |
| `ALGORITHM_REVEAL` | Algorithm name, explanation, optimal solution description |
| `COMPLETED` | Score circle, optimality %, moves, hints, bonuses, play again |

### Actions

| Action | Trigger |
|--------|---------|
| `CP_START` | Click "Start Puzzle" |
| `TOGGLE_ITEM` | Click knapsack item (select/deselect) |
| `PLACE_QUEEN` | Click empty chess cell |
| `REMOVE_QUEEN` | Click cell with existing queen |
| `ADD_COIN` | Click a denomination coin |
| `REMOVE_COIN` | Click a selected coin to remove |
| `TOGGLE_ACTIVITY` | Click an activity (select/deselect) |
| `CP_UNDO` | Click "Reset Board" — clears all selections |
| `CHECK_SOLUTION` | Click "Check Solution" — validates and scores |
| `REVEAL_ALGORITHM` | Click "Reveal Algorithm" from solved state |
| `CP_USE_HINT` | Request progressive hint |
| `CP_COMPLETE` | Transition to final score |
| `CP_RESET` | Click "Play Again" |

---

## 8. Visual Components

### Knapsack Layout

```
┌──────────────────────────────────────────────┐
│  🎒 Camping Trip Packing                     │
│  Objective: Pack most value within 15 kg      │
├──────────────────────────────────────────────┤
│  Weight: 11/15  ██████████████░░░░░          │
│                               Value: 25       │
│                                               │
│  ┌──────┐  ┌──────┐  ┌──────┐               │
│  │ ⛺    │  │ 🛏️    │  │ 🔥    │               │
│  │ Tent  │  │ Sleep │  │ Stove │               │
│  │ W:7   │  │ W:5   │  │ W:3   │               │
│  │ V:10  │  │ V:8   │  │ V:6   │               │
│  │[SEL]  │  │       │  │[SEL]  │               │
│  └──────┘  └──────┘  └──────┘               │
│  ...                                          │
│  [Hints]  [Reset Board]  [Check Solution]     │
└──────────────────────────────────────────────┘
```

### N-Queens Layout

```
┌──────────────────────────────────────────────┐
│  ♛ 6-Queens Challenge          Queens: 4/6   │
├──────────────────────────────────────────────┤
│        ┌───┬───┬───┬───┬───┬───┐            │
│        │   │ ♛ │   │ · │   │ · │            │
│        ├───┼───┼───┼───┼───┼───┤            │
│        │ · │   │ · │ ♛ │ · │   │            │
│        ├───┼───┼───┼───┼───┼───┤            │
│        │   │ · │   │ · │   │ ♛ │            │
│        ├───┼───┼───┼───┼───┼───┤            │
│        │ ♛ │   │ · │   │ · │   │            │
│        ├───┼───┼───┼───┼───┼───┤            │
│        │ · │   │   │ · │   │ · │            │
│        ├───┼───┼───┼───┼───┼───┤            │
│        │   │ · │   │   │ · │   │            │
│        └───┴───┴───┴───┴───┴───┘            │
│  · = threatened square                        │
│  [Hints]  [Reset Board]  [Check Solution]     │
└──────────────────────────────────────────────┘
```

### Component Breakdown

| Component | File | Description |
|-----------|------|-------------|
| `ConstraintPuzzleGame` | `ConstraintPuzzleGame.tsx` | Main game — phase rendering, puzzle type dispatch |
| `KnapsackBoard` | `components/KnapsackBoard.tsx` | Item grid + weight/value bar |
| `NQueensBoard` | `components/NQueensBoard.tsx` | Chess grid with threat highlighting |
| `CoinChangeBoard` | `components/CoinChangeBoard.tsx` | Coin circles + sum progress |
| `ActivitySelectionBoard` | `components/ActivitySelectionBoard.tsx` | Timeline bars + list |
| `HintSystem` | `components/HintSystem.tsx` | Reused from State Tracer |

---

## 9. Frontend Architecture

### File Tree

```
AlgorithmGame/
├── ConstraintPuzzleGame.tsx               # Main game component
├── types.ts                               # Types (appended)
├── hooks/
│   └── useConstraintPuzzleMachine.ts     # useReducer state machine
├── components/
│   ├── KnapsackBoard.tsx                 # Knapsack puzzle board
│   ├── NQueensBoard.tsx                  # N-Queens chess board
│   ├── CoinChangeBoard.tsx              # Coin change board
│   ├── ActivitySelectionBoard.tsx        # Activity timeline board
│   └── HintSystem.tsx                   # Reused from State Tracer
├── data/
│   ├── constraintPuzzleKnapsack.ts
│   ├── constraintPuzzleNQueens.ts
│   ├── constraintPuzzleCoinChange.ts
│   ├── constraintPuzzleActivitySelection.ts
│   └── constraintPuzzleIndex.ts          # Registry of all demos
└── (demo page at app/demo/constraint-puzzle/page.tsx)
```

### Puzzle Type Dispatch

The main game component uses the discriminated union `PuzzleData.type` to render the correct board:

```typescript
{blueprint.puzzleData.type === 'knapsack' && <KnapsackBoard ... />}
{blueprint.puzzleData.type === 'n_queens' && <NQueensBoard ... />}
{blueprint.puzzleData.type === 'coin_change' && <CoinChangeBoard ... />}
{blueprint.puzzleData.type === 'activity_selection' && <ActivitySelectionBoard ... />}
```

The state machine stores all four state arrays (`selectedItemIds`, `queenPositions`, `selectedCoins`, `selectedActivityIds`) but only the relevant one is used per puzzle type. Validation in `CHECK_SOLUTION` switches on puzzle type to apply the correct constraint checks.

### Validation Helpers (in hook)

| Helper | Purpose |
|--------|---------|
| `knapsackValue()` | Sum values of selected items |
| `knapsackWeight()` | Sum weights of selected items |
| `queensConflict()` | Check row/col/diagonal conflicts across all queen pairs |
| `coinSum()` | Sum of selected coins |
| `activitiesOverlap()` | Check if any two selected activities overlap |

---

## 10. Backend Generation Requirements

### Inputs
- Puzzle type (knapsack, n_queens, coin_change, activity_selection)
- Difficulty level (controls item count, board size, denomination set, activity count)
- Theme/narrative (optional — "camping trip", "classroom scheduling")

### Generation Pipeline

1. **Select puzzle type** — From request or curriculum
2. **Generate puzzle data** — Create items/board/coins/activities with known optimal
3. **Compute optimal solution** — Run the actual algorithm (DP table, backtracking, greedy)
4. **Set optimal value** — The benchmark for scoring
5. **Write narrative** — Story context for the puzzle
6. **Generate rules** — Clear constraint list
7. **Generate hints** — 3-tier progressive hints
8. **Write algorithm explanation** — Educational text about the algorithm

### Quality Criteria

- [ ] Optimal solution is provably correct (verified by running the algorithm)
- [ ] Puzzle has a unique or near-unique optimal (multiple valid solutions OK for N-Queens)
- [ ] Difficulty is calibrated: knapsack has 6-10 items, N-Queens is 5-8, coin change has 4-6 denominations
- [ ] Distractors/traps exist (items with high value but high weight, greedy-fails cases)
- [ ] Algorithm explanation is educational and connects to the puzzle
- [ ] Narrative makes the abstract problem concrete and relatable

---

## 11. 4 Demo Games

| # | Puzzle Type | Title | Algorithm | Optimal | Difficulty |
|---|------------|-------|-----------|---------|------------|
| 1 | Knapsack | Camping Trip Packing | 0/1 Knapsack (DP) | 30 value in 15 kg | Medium |
| 2 | N-Queens | 6-Queens Challenge | Backtracking | 6 queens, no conflicts | Medium |
| 3 | Coin Change | Exact Change Challenge | Coin Change (DP) | 3 coins for 36¢ | Easy |
| 4 | Activity Selection | Conference Room Scheduling | Activity Selection (Greedy) | 4 meetings | Medium |

### Example: Camping Trip Packing (Knapsack)

**Setup:** 8 items with weight/value, backpack capacity = 15 kg.

| Item | Weight | Value | Icon |
|------|--------|-------|------|
| Tent | 7 | 10 | ⛺ |
| Sleeping Bag | 5 | 8 | 🛏️ |
| Camp Stove | 3 | 6 | 🔥 |
| Water Filter | 2 | 7 | 💧 |
| Food Pack | 4 | 5 | 🍞 |
| First Aid Kit | 1 | 4 | 🩹 |
| Lantern | 3 | 3 | 💡 |
| Folding Chair | 6 | 2 | 🪑 |

**Optimal**: Sleeping Bag + Water Filter + Camp Stove + Food Pack + First Aid Kit = 30 value, 15 kg exactly.

**Trap**: Tent has highest value (10) but 7 kg. Greedy by value picks Tent first, leaving only 8 kg for 4 items → suboptimal.

**Algorithm reveal**: DP table dp[i][w], backtrack to find optimal item set. O(n × W) time.

---

## 12. Comparison with Other Mechanics

| Aspect | State Tracer | Bug Hunter | Algorithm Builder | Complexity Analyzer | Constraint Puzzle |
|--------|-------------|------------|-------------------|---------------------|-------------------|
| **Bloom Level** | Understand | Analyze | Apply → Create | Analyze → Evaluate | Apply → Evaluate |
| **Student Action** | Predict state | Find + fix | Arrange blocks | Classify complexity | Solve optimization |
| **Interaction** | Click/type | Click lines | Drag-and-drop | Click options | Click items/cells |
| **Puzzle types** | 1 | 1 | 1 | 3 | 4 |
| **Algorithm reveal** | N/A | N/A | N/A | N/A | Yes (post-solve) |
| **Time per game** | 5-15 min | 3-10 min | 3-8 min | 3-8 min | 5-15 min |
| **Backend complexity** | High | Medium | Low | Medium | Medium (compute optimal) |

---

## 13. Research Sources

- Cormen, T. et al. (2009). Introduction to Algorithms — Knapsack, Activity Selection, N-Queens
- Skiena, S. (2008). The Algorithm Design Manual — Problem-first approach to algorithm teaching
- Computational Thinking Unplugged — Problem-solving activities for optimization
- Nisan, N. & Ronen, A. (1999). Mechanism Design — Game-theoretic optimization problems
- CS Unplugged: Bin packing and resource allocation activities
