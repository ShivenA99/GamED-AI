# Algorithmic Games Template — Deep Research Report

**Date:** 2026-02-19
**Purpose:** Comprehensive research to map all algorithm types to suitable game mechanics, catalog existing platforms, and design GamED.AI's 2nd template for interactive algorithm games.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Existing Platforms Landscape](#2-existing-platforms-landscape)
3. [Research Foundations](#3-research-foundations)
4. [Game Mechanic Types](#4-game-mechanic-types)
5. [Algorithm Taxonomy → Game Mapping](#5-algorithm-taxonomy--game-mapping)
6. [Task Types for Each Algorithm Category](#6-task-types-for-each-algorithm-category)
7. [Interaction Primitives & UI Components](#7-interaction-primitives--ui-components)
8. [Scoring & Progression Design](#8-scoring--progression-design)
9. [Novel Game Concepts (Our Innovations)](#9-novel-game-concepts-our-innovations)
10. [Architecture Recommendations](#10-architecture-recommendations)
11. [Named Game Designs Per Algorithm (Detailed)](#11-named-game-designs-per-algorithm-detailed)
12. [Implementation Priority Matrix](#12-implementation-priority-matrix)
13. [Cross-Cutting Design Principles (Research Synthesis)](#13-cross-cutting-design-principles-research-synthesis)
14. [References](#14-references)

---

## 1. Executive Summary

### The Opportunity
No platform today generates **personalized, interactive algorithm games from arbitrary algorithm questions**. The space is fragmented:
- **Visualizers** (VisuAlgo, Algorithm Visualizer) → passive viewing, no gamification
- **Competitive coding** (LeetCode, Codeforces) → text-based, no visual manipulation
- **Game-based** (CodeCombat, CodinGame) → fixed game worlds, not AI-generated
- **Academic tools** (OpenDSA/JSAV, TRAKLA2) → auto-graded exercises, but no game loop or AI generation

**Our unique value**: Take any algorithm question → AI generates a beautiful, interactive game that tests understanding of that specific algorithm, with multiple task types per game (state tracing, bug hunting, manual execution, optimization challenges).

### Key Research Findings
1. **Active engagement >> passive viewing** — Naps et al.'s engagement taxonomy (6 levels: No Viewing → Viewing → Responding → Changing → Constructing → Presenting) shows learning increases with engagement level. Games naturally push to "Responding" and "Changing" levels.
2. **Gamification effect size is moderate-to-strong** — Meta-analyses show Hedges's g ≈ 0.5–0.8 for gamified vs. non-gamified learning (Zeng 2024, Kurnaz 2025).
3. **Parsons problems** (reorder scrambled code lines) are as effective as writing code but take **half the time** — perfect for a game task type.
4. **dpvis** (SIGCSE 2025) pioneered interactive self-testing for DP — quiz students on which cells are read/written next. This "predict the next state" mechanic is generalizable to ALL algorithms.
5. **Shorter interventions > longer ones** for effect size — each game should be 5-15 minutes, not 60+.

---

## 2. Existing Platforms Landscape

### 2.1 Algorithm Visualization Platforms (Passive → Semi-Active)

| Platform | Algorithms | Interaction | Gamification | Weakness |
|----------|-----------|-------------|-------------|----------|
| **VisuAlgo** (NUS) | 24 categories (sorting, graphs, trees, DP, etc.) | Step-through, quiz mode, training mode | Minimal (online quiz) | Dated UI, no scoring/progression |
| **Algorithm Visualizer** | Backtracking, DP, graph, sorting, search, etc. | Code + visual side-by-side | None | Passive viewing only |
| **USF Galles Visualization** | BST, heap, graph, hash, sorting, DP | Click-driven with VCR controls | None | Java-applet era design |
| **Red Blob Games** | Pathfinding, A*, hex grids, procedural gen | Draggable interactive diagrams | None (but deeply engaging) | Narrow scope (game dev focus) |
| **SortVision** | 8 sorting algorithms | Speed/size controls, step-through | AI chatbot assistant | Sorting only |
| **csvistool** (GA Tech) | DS&A curriculum (BST, AVL, sorts, graphs) | Step-through animations | None | Academic only |
| **dpvis** (SIGCSE 2025) | Dynamic programming | Frame-by-frame + **self-test quiz** | Self-testing mode | DP only, Python library |

### 2.2 Gamified Learning Platforms (Active)

| Platform | Approach | Gamification Mechanics | Algorithm Depth |
|----------|----------|----------------------|-----------------|
| **Brilliant.org** | Interactive puzzles, learn-by-doing | XP, streaks, adaptive difficulty, sounds/haptics | Expanding (full DS&A by 2026) |
| **CodinGame** | Code controls visual game entities | Contests, leaderboards, AI battles | Deep (pathfinding, optimization, game theory) |
| **CodeCombat** | RPG where code commands hero | Narrative, character progression, equipment | Shallow (fundamentals only) |
| **Codewars** | Kata challenges with ranking | kyu/dan martial arts ranking, honor points | Full spectrum (community-created) |
| **LeetCode** | Coding challenges + contests | Streaks, badges, Elo contest rating | Comprehensive (3000+ problems) |
| **HackerRank** | Tracks + certifications | Badges, points, leaderboards, certifications | Broad (algorithms, DB, AI, etc.) |
| **Exercism** | Exercises + human mentorship | Reputation, badges, exercise unlocking | Language-specific, moderate |

### 2.3 Academic/Educational Tools (Research-Backed)

| Tool | Key Innovation | Engagement Level (Naps) |
|------|---------------|------------------------|
| **OpenDSA/JSAV** | Proficiency exercises — students manipulate visual data structures, auto-graded | Constructing |
| **TRAKLA2** | Randomized visual algorithm simulation with auto-grading | Changing |
| **JHAVE** | "Stop-and-think" pop-up questions during visualization | Responding |
| **ANIMAL** | 300+ pre-built algorithm animations with scripting | Viewing |
| **JFLAP** | Automata/formal language interactive construction | Constructing |
| **Python Tutor** | Code execution visualization (heap, stack, pointers) | Viewing/Responding |

### 2.4 Algorithm Puzzle Games (Entertainment)

| Game | What It Teaches | Core Mechanic |
|------|----------------|---------------|
| **Human Resource Machine** | Assembly language concepts | Drag-and-drop instruction programming |
| **7 Billion Humans** | Parallel algorithm execution | Multi-worker simultaneous programming |
| **while True: learn()** | ML/neural network concepts | Connect-the-nodes data flow puzzle |
| **Code Defenders** | Mutation testing / debugging | Attacker (inject bugs) vs Defender (write tests) |
| **Sojourner under Sabotage** | Unit testing + debugging | Spaceship narrative with progressive levels |
| **Tower of Hanoi** | Recursion | Classic constraint puzzle |
| **N-Queens puzzles** | Backtracking | Constraint placement puzzle |

---

## 3. Research Foundations

### 3.1 Naps Engagement Taxonomy (Foundational)
Six levels of engagement with algorithm visualizations:
1. **No Viewing** — no visualization
2. **Viewing** — passively watching animation
3. **Responding** — answering questions about what happens next
4. **Changing** — modifying input data or parameters
5. **Constructing** — building the algorithm solution manually
6. **Presenting** — explaining the algorithm to others

**Core finding (Hundhausen et al., 2002 meta-study):** *How* students use visualizations matters more than *what* they see. Active engagement is the key variable.

**Our design principle:** Every game task should be at minimum "Responding" level, with most tasks at "Changing" or "Constructing."

### 3.2 Bloom's Taxonomy Applied to Algorithms
Map algorithm tasks to cognitive levels:

| Bloom Level | Algorithm Task Example |
|-------------|----------------------|
| **Remember** | Name the algorithm shown in this animation |
| **Understand** | Explain why BFS visits nodes in this order |
| **Apply** | Execute merge sort on this array (manual step-through) |
| **Analyze** | Identify why this code runs in O(n²) instead of O(n log n) |
| **Evaluate** | Compare Dijkstra vs A* for this graph — which is better? |
| **Create** | Build a sorting algorithm using these primitive operations |

### 3.3 Parsons Problems Research
- Scrambled code lines that students reorder
- **Same learning effectiveness** as writing code, but **50% less time**
- Reduces cognitive load by constraining the problem space
- Perfect as one of our task types: "Reorder these algorithm steps"

### 3.4 Gamification Meta-Analyses

| Study | Effect Size | Key Insight |
|-------|------------|-------------|
| Zeng et al. (2024), 2008-2023 | g = 0.782 | Moderate-to-strong positive effect |
| General meta-analysis | d = 0.504 | Consistent positive impact |
| Kurnaz (2025), K-12 | g = 0.654 | High heterogeneity but positive |
| Shorter interventions | Higher effect | Brief gamified sessions > long ones |

### 3.5 Adaptive Difficulty Research
- Adaptive difficulty produces significantly higher learning outcomes than fixed progression
- Best when combined with stealth assessment (assess without interrupting flow)
- Reinforcement learning-based DDA maintains optimal challenge-skill balance
- Critical insight: ability to **revert to easier levels** when struggling

---

## 4. Game Mechanic Types

### 4.1 State Tracer / Step-Through Simulator
**What:** Player steps through algorithm execution, predicting the next state at each step.
**Interaction:** "What will the array look like after the next swap?" → multiple choice or drag arrangement
**Visual:** Variables panel, call stack, memory state, highlighted current line
**Best for:** ALL algorithms (universal mechanic)
**Inspiration:** Python Tutor, dpvis self-test mode
**Engagement level:** Responding/Changing

### 4.2 Bug Hunter / Code Debugger
**What:** Given broken algorithm code, find and fix the bug.
**Bug types:**
- Off-by-one errors in loops (`i < n` vs `i <= n`)
- Wrong comparison operators (`<` vs `<=`, `>` vs `>=`)
- Missing base cases in recursion
- Wrong variable updates (increment vs decrement)
- Incorrect initialization (wrong starting value)
- Infinite loops (missing update)
- Wrong data structure choice
**Interaction:** Highlight the buggy line, select the fix from options
**Best for:** All algorithms with code
**Inspiration:** Code Defenders, Sojourner under Sabotage
**Engagement level:** Analyzing/Evaluating

### 4.3 Manual Execution (Be-the-Algorithm)
**What:** Player manually performs algorithm operations on a visual data structure.
**Interaction:**
- Drag-and-drop array elements to perform swaps (sorting)
- Click nodes in correct BFS/DFS traversal order (graphs)
- Drag nodes to build a BST (trees)
- Fill in DP table cells (dynamic programming)
- Draw connections between nodes (MST)
**System validates each step in real-time.**
**Best for:** Sorting, graph traversal, tree operations, DP
**Inspiration:** OpenDSA/JSAV proficiency exercises, TRAKLA2
**Engagement level:** Constructing

### 4.4 Predict-the-Output
**What:** Given algorithm + input, predict the final output or intermediate state.
**Interaction:** Type answer, multiple choice, or arrange output
**Variants:**
- "What does this function return for input [3, 1, 4, 1, 5]?"
- "After 3 iterations of bubble sort, what is the array state?"
- "Which node does Dijkstra visit 4th?"
**Best for:** All algorithms
**Engagement level:** Responding

### 4.5 Algorithm Builder (Parsons-style)
**What:** Drag-and-drop code blocks or operation cards to construct an algorithm.
**Variants:**
- **Full Parsons:** All lines scrambled, reorder completely
- **Partial Parsons:** Some lines fixed, fill in gaps
- **Operation cards:** Abstract operations (compare, swap, recurse, return) rather than code
- **Distractor blocks:** Include wrong code lines that shouldn't be used
**Best for:** Algorithm construction understanding
**Inspiration:** Parsons problems, Scratch block programming
**Engagement level:** Constructing

### 4.6 Optimization Challenge / Race
**What:** Player's approach is evaluated against a baseline for efficiency.
**Interaction:**
- "Can you sort this faster than O(n²)?" — choose/configure algorithm
- Watch two algorithms race on growing input sizes
- Identify the bottleneck in code that makes it slow
**Visual:** Split-screen algorithm race, complexity graph growing in real-time
**Best for:** Comparing algorithms, understanding complexity
**Engagement level:** Evaluating

### 4.7 Pathfinder / Graph Explorer
**What:** Navigate through a graph following specific algorithm rules.
**Interaction:**
- Click nodes in correct BFS/DFS order
- Draw shortest path on weighted graph (Dijkstra)
- Connect cities with minimum cost (MST)
- Schedule tasks respecting dependencies (topological sort)
**Best for:** Graph algorithms specifically
**Inspiration:** Red Blob Games, Dijkstra underground puzzle
**Engagement level:** Constructing

### 4.8 Pattern Matcher / Algorithm Identifier
**What:** Identify which algorithm is being demonstrated, or match algorithms to properties.
**Interaction:**
- Watch animation → select correct algorithm name
- Match algorithm names to their time complexities
- "Is this BFS or DFS?" from a traversal animation
- Classify code snippets by algorithm paradigm (greedy, DP, D&C)
**Best for:** Algorithm recognition and classification
**Engagement level:** Responding/Analyzing

### 4.9 Constraint Puzzle
**What:** Algorithm-inspired puzzles where the player solves a problem that IS the algorithm.
**Examples:**
- N-Queens placement (backtracking)
- Sudoku (constraint satisfaction)
- Pack items in backpack to maximize value (knapsack)
- Make exact change with fewest coins (coin change)
- Connect cities with minimum road cost (MST)
- Schedule non-overlapping events (activity selection)
**Best for:** Backtracking, DP, greedy algorithms
**Engagement level:** Constructing

### 4.10 Code Completion / Fill-in-the-Blank
**What:** Partial algorithm implementation with key lines/expressions missing.
**Interaction:** Select correct code fragments for blanks
**Variants:**
- Single blank (choose comparison operator)
- Multiple blanks (fill in loop body)
- Progressive: more blanks = harder difficulty
**Best for:** Algorithm implementation details
**Engagement level:** Constructing

### 4.11 Test Case Designer
**What:** Create input that exposes a specific behavior or breaks a buggy implementation.
**Interaction:**
- "Design an input array that causes quicksort to run in O(n²)"
- "Create a graph where BFS and DFS visit nodes in different orders"
- "Find an input that makes this buggy binary search return wrong answer"
**Best for:** Deep algorithmic understanding
**Engagement level:** Creating/Evaluating

### 4.12 Complexity Analyzer
**What:** Given code or visualization, identify time/space complexity.
**Interaction:**
- Select O(n), O(n log n), O(n²), etc.
- Watch algorithm run on inputs of size 10, 100, 1000 → infer complexity from runtime growth
- Identify which loop/call causes the bottleneck
**Best for:** Algorithmic analysis skills
**Engagement level:** Analyzing

---

## 5. Algorithm Taxonomy → Game Mapping

### Master Mapping Table

| Algorithm Category | Primary Game Mechanics | Secondary Mechanics | Visual Theme |
|---|---|---|---|
| **Sorting** | Manual Execution, State Tracer | Race, Pattern Matcher, Bug Hunter | Array bars, card sorting |
| **Searching** | Manual Execution, Predict-Output | Bug Hunter, Complexity Analyzer | Number line, grid |
| **Graph Traversal** | Pathfinder, Manual Execution | Pattern Matcher, Predict-Output | City maps, mazes, networks |
| **Shortest Path** | Pathfinder, Constraint Puzzle | Optimization Race, State Tracer | City/subway maps |
| **MST** | Constraint Puzzle, Manual Execution | Optimization Race | City connections, cable networks |
| **Trees** | Manual Execution, State Tracer | Bug Hunter, Pattern Matcher | Tree diagrams, family trees |
| **Dynamic Programming** | State Tracer, Constraint Puzzle | Code Completion, Manual Execution (table fill) | Grid/table, backpack packing |
| **Greedy** | Constraint Puzzle, Manual Execution | Optimization Race, Pattern Matcher | Scheduling boards, coin stacks |
| **Backtracking** | Constraint Puzzle, State Tracer | Manual Execution, Bug Hunter | Chessboard, maze, coloring |
| **Divide & Conquer** | State Tracer, Algorithm Builder | Pattern Matcher, Manual Execution | Recursive tree, split-merge |
| **String** | State Tracer, Manual Execution | Bug Hunter, Pattern Matcher | Text highlighting, trie trees |
| **Hashing** | State Tracer, Manual Execution | Bug Hunter, Predict-Output | Hash tables, buckets |
| **Recursion** | State Tracer, Manual Execution | Bug Hunter, Complexity Analyzer | Call stack, tree |

---

## 6. Task Types for Each Algorithm Category

### 6.1 Sorting Algorithms

#### Bubble Sort
| Task Type | Description | Scoring |
|-----------|-------------|---------|
| **Be-the-Algorithm** | Drag elements to swap adjacent pairs in correct order | Points per correct swap, penalty per wrong |
| **State Tracer** | "After pass 3, what is the array?" | Correct = full points, partial credit for close |
| **Bug Hunter** | "This bubble sort has a bug — find it" (e.g., wrong comparison direction) | Speed + accuracy |
| **Race** | Watch bubble sort vs. merge sort on same data | Predict winner + explain why |
| **Parsons** | Reorder scrambled bubble sort code lines | Correctness + time |

#### Quick Sort
| Task Type | Description |
|-----------|-------------|
| **Pivot Selection** | "Choose the best pivot for this array" — see how partition changes |
| **Manual Partition** | Drag elements left/right of pivot |
| **Recursion Tree** | Click to expand recursive calls in correct order |
| **Bug Hunter** | Find the off-by-one in the partition function |

#### Merge Sort
| Task Type | Description |
|-----------|-------------|
| **Split-and-Merge Puzzle** | Visually split array, then merge sorted halves |
| **Merge Step** | Given two sorted halves, manually merge them |
| **Recursion Tracer** | Predict which subarray is processed next |

#### Heap Sort
| Task Type | Description |
|-----------|-------------|
| **Build-a-Heap** | Insert elements one by one into a visual binary heap (drag to correct position) |
| **Heapify** | Given a broken heap, fix it by performing swaps |
| **Extract-and-Sort** | Remove max repeatedly, place in sorted output |

### 6.2 Graph Algorithms

#### BFS/DFS
| Task Type | Description |
|-----------|-------------|
| **Traversal Order** | Click nodes in correct BFS or DFS order on a graph |
| **Which Is Which?** | Watch traversal animation → identify BFS vs DFS |
| **Maze Explorer** | Navigate a maze following BFS rules (visit all neighbors before going deeper) or DFS rules |
| **Bug Hunter** | DFS code visits nodes in wrong order — find the bug |

#### Dijkstra's Algorithm
| Task Type | Description |
|-----------|-------------|
| **Underground Puzzle** | Find shortest path through subway network (click nodes in Dijkstra order) |
| **Distance Table** | Fill in the distance table step by step |
| **Path Drawing** | Draw the shortest path after algorithm completes |
| **Negative Weight Trap** | "Why doesn't Dijkstra work here?" — identify negative edge |

#### MST (Kruskal/Prim)
| Task Type | Description |
|-----------|-------------|
| **City Connection** | Connect cities with minimum total cable cost (click edges in Kruskal order) |
| **Cycle Detection** | "Would adding this edge create a cycle?" |
| **Prim vs Kruskal** | Same graph, trace both — compare edge selection order |

#### Topological Sort
| Task Type | Description |
|-----------|-------------|
| **Task Scheduler** | Order courses/tasks respecting prerequisites (drag to reorder) |
| **Dependency Finder** | "Which tasks can run first?" (identify nodes with in-degree 0) |

### 6.3 Tree Algorithms

#### BST Operations
| Task Type | Description |
|-----------|-------------|
| **Build-a-BST** | Insert numbers into visual BST (drag to correct leaf position) |
| **Search Path** | Click nodes along the search path for a given key |
| **Delete Challenge** | Delete a node and restructure correctly |
| **Traversal Click** | Click nodes in in-order / pre-order / post-order |

#### AVL Rotations
| Task Type | Description |
|-----------|-------------|
| **Imbalance Detector** | After insert, identify which node is imbalanced |
| **Rotation Selector** | Choose correct rotation type (LL, RR, LR, RL) |
| **Perform Rotation** | Drag nodes to perform the rotation |

#### Trie Operations
| Task Type | Description |
|-----------|-------------|
| **Word Insertion** | Insert a word character by character into a trie |
| **Autocomplete** | Given a prefix, trace the trie to find all completions |
| **Word Search** | "Does this word exist in the trie?" — trace the path |

### 6.4 Dynamic Programming

#### Knapsack
| Task Type | Description |
|-----------|-------------|
| **Backpack Packing** | Select items to maximize value within weight limit (visual backpack) |
| **Table Fill** | Fill in DP table cells with correct values (predict next cell) |
| **Trace Back** | Given completed table, trace which items were selected |

#### LCS (Longest Common Subsequence)
| Task Type | Description |
|-----------|-------------|
| **Table Fill** | Fill LCS table step-by-step |
| **Subsequence Highlighter** | Highlight the common subsequence in both strings |
| **Edit Game** | Transform string A to B with minimum operations |

#### Coin Change
| Task Type | Description |
|-----------|-------------|
| **Make Change** | Select minimum coins to make a target amount |
| **Table Fill** | Fill the DP table for coin change |
| **Greedy vs DP** | "Greedy gives 4 coins, DP gives 3 — why?" |

#### General DP Pattern
| Task Type | Description |
|-----------|-------------|
| **Subproblem Identifier** | "What subproblems does this depend on?" (click cells in DP table) |
| **Recurrence Builder** | Construct the recurrence relation from options |
| **Base Case Finder** | Identify and fill in the base cases |
| **Memoization Tracer** | Trace which subproblems are computed vs cached |

### 6.5 Backtracking

#### N-Queens
| Task Type | Description |
|-----------|-------------|
| **Place Queens** | Place N queens on board with no conflicts |
| **Backtrack Tracer** | Step through the backtracking tree, predict next move |
| **Constraint Highlighter** | "Why can't a queen go here?" — show conflicting queen |

#### Sudoku
| Task Type | Description |
|-----------|-------------|
| **Solve with Backtracking** | Step through constraint propagation + backtracking |
| **Choice Point** | "Which cell should we fill next?" (most constrained variable) |

#### Graph Coloring
| Task Type | Description |
|-----------|-------------|
| **Color the Map** | Color graph nodes with minimum colors, no adjacent same color |
| **Chromatic Challenge** | "Can this graph be colored with K colors?" |

### 6.6 Greedy Algorithms

#### Activity Selection
| Task Type | Description |
|-----------|-------------|
| **Schedule Planner** | Select maximum non-overlapping events (visual timeline) |
| **Sort-then-Select** | "Why do we sort by end time?" — compare strategies |

#### Huffman Coding
| Task Type | Description |
|-----------|-------------|
| **Build Huffman Tree** | Repeatedly merge two smallest-frequency nodes |
| **Encode/Decode** | Encode a message using the tree, or decode a binary string |
| **Compression Calculator** | Compare Huffman vs fixed-length encoding sizes |

### 6.7 String Algorithms

#### Pattern Matching (KMP)
| Task Type | Description |
|-----------|-------------|
| **Failure Function Builder** | Fill in the failure function table for a pattern |
| **Match Tracer** | Step through text matching, predict when pattern shifts |
| **Naive vs KMP Race** | Watch both algorithms — count comparisons |

### 6.8 Recursion

#### General Recursion
| Task Type | Description |
|-----------|-------------|
| **Call Stack Builder** | Build the call stack for a recursive function |
| **Return Value Predictor** | "What does f(5) return?" — trace through calls |
| **Base Case Identifier** | "What's the base case? What happens without it?" |
| **Tower of Hanoi** | Classic game — solve with minimum moves |

---

## 7. Interaction Primitives & UI Components

### Required UI Components for the Template

| Component | Used By | Implementation |
|-----------|---------|----------------|
| **Array Visualizer** | Sorting, searching, DP | Horizontal bar chart with drag-to-swap, highlight active/compared/sorted |
| **Graph Visualizer** | BFS, DFS, Dijkstra, MST, topo sort | Force-directed layout with clickable nodes/edges, color states |
| **Tree Visualizer** | BST, AVL, heap, trie, Huffman | Animated node insertion/deletion/rotation, clickable nodes |
| **Table/Grid** | DP, LCS, edit distance, matrix chain | Click-to-fill cells, dependency arrows, color-coded states |
| **Code Panel** | Bug hunter, state tracer, Parsons | Syntax-highlighted code with line highlighting, draggable blocks |
| **Call Stack Panel** | Recursion, DFS, backtracking | Push/pop animation, variable values per frame |
| **Timeline** | Activity selection, scheduling | Horizontal timeline with draggable/selectable intervals |
| **Chessboard** | N-Queens, knight's tour | Grid with piece placement and constraint highlighting |
| **Comparison Counter** | Races, complexity analysis | Real-time counter showing operations performed |
| **Complexity Graph** | Complexity analyzer, race | Plot of operations vs input size growing in real-time |

### Interaction Types

| Interaction | Mouse/Touch Action | Used For |
|-------------|-------------------|----------|
| **Drag-and-Drop** | Drag element to new position | Array swaps, BST insertion, Parsons code reorder |
| **Click Sequence** | Click elements in order | BFS/DFS traversal, Dijkstra node selection |
| **Path Drawing** | Click/drag to draw path | Shortest path, trace path, graph edges |
| **Cell Fill** | Click cell → enter value | DP table, distance table |
| **Selection** | Click to select/deselect | Knapsack items, MST edges, activity selection |
| **Toggle/Color** | Click to cycle colors | Graph coloring |
| **Reorder** | Drag to rearrange list | Parsons problems, topological sort |
| **Speed Control** | Slider | Animation playback speed |
| **Step Controls** | Next/Prev/Play/Pause | State tracer, algorithm animation |

---

## 8. Scoring & Progression Design

### 8.1 Scoring Principles

**Delta-based scoring** (lessons from Interactive Diagram template):
- Score accumulates through correct actions, never overwrites
- Partial credit for partially correct states
- Time bonuses for fast completion (optional, configurable)
- Hint penalties (reduce max possible score per hint used)
- Streak bonuses for consecutive correct actions

### 8.2 Per-Task Scoring

| Task Type | Scoring Method |
|-----------|---------------|
| **State Tracer** | % of correct state predictions |
| **Bug Hunter** | Binary (found/not found) + time bonus |
| **Manual Execution** | % of steps performed correctly before first error |
| **Predict-Output** | Binary or partial credit for close answers |
| **Parsons** | % of lines in correct position |
| **Optimization Race** | Score = baseline_complexity / your_complexity |
| **Constraint Puzzle** | Binary (solved/not) + moves efficiency |
| **Code Completion** | % of blanks filled correctly |
| **Test Case Designer** | Binary (does input expose the behavior?) |
| **Complexity Analyzer** | Binary per question |

### 8.3 Difficulty Progression

Map to Bloom's taxonomy levels within a single game:

| Level | Bloom Level | Task Types | Example |
|-------|-------------|-----------|---------|
| **1: Recognize** | Remember/Understand | Pattern Matcher, Predict-Output (simple) | "Which algorithm is this?" |
| **2: Trace** | Apply | State Tracer, Manual Execution (guided) | "Execute merge sort step by step" |
| **3: Analyze** | Analyze | Bug Hunter, Complexity Analyzer | "Find the bug" / "What's the time complexity?" |
| **4: Construct** | Create/Evaluate | Algorithm Builder, Test Case Designer, Optimization | "Build a sort" / "Design worst-case input" |

### 8.4 Adaptive Difficulty
- Track correctness per task type → adjust subsequent task difficulty
- If player gets 3 state traces correct → escalate to bug hunting
- If player fails manual execution → drop back to guided state tracing
- Stealth assessment: infer understanding level from interaction patterns (hesitation time, backtrack count, hint requests)

---

## 9. Novel Game Concepts (Our Innovations)

### 9.1 "Algorithm Arena" — Multi-Phase Game Per Question
A single algorithm question generates a **4-phase game**:

**Phase 1: Understand** (60s)
- Watch the algorithm animation once
- Answer 2-3 "what happens next?" prediction questions

**Phase 2: Execute** (120s)
- Manually perform the algorithm on a data structure
- System validates each step in real-time
- Partial credit for how far you get correctly

**Phase 3: Debug** (90s)
- Given a buggy implementation of the same algorithm
- Find and fix the bug(s)
- Limited hint budget

**Phase 4: Master** (60s)
- One challenge from: test case design, Parsons reorder, complexity analysis, or optimization
- This phase varies based on algorithm type

### 9.2 "Algorithm Detective" — Forensic Code Analysis
- Show execution trace (sequence of states) without showing the code
- Player must identify which algorithm produced this trace
- Progressive difficulty: first 2-choice, then 4-choice, then open-ended
- Can be applied to ANY algorithm category

### 9.3 "Code Hospital" — Progressive Bug Fixing
- Algorithm has 3 bugs of increasing subtlety
- Fix one → unlock the next
- Bug 1: Obvious syntax/logic error
- Bug 2: Edge case failure (empty input, single element)
- Bug 3: Performance bug (correct output but wrong complexity)

### 9.4 "Race Track" — Algorithm Comparison
- Two or more algorithms visualized side-by-side on same input
- Player predicts which finishes first
- Input size slider — see how predictions change
- Graph of runtime vs input size builds in real-time
- Teaches O(n) vs O(n²) vs O(n log n) viscerally

### 9.5 "Build-a-Sort" — Algorithm Construction from Primitives
- Given primitive operations: compare(a,b), swap(i,j), split(arr), merge(a,b)
- Player assembles operations to build a working sort algorithm
- System tests their construction on sample inputs
- Multiple valid solutions (any correct sort accepted)
- Score based on efficiency of the algorithm built

### 9.6 "DP Table Challenge" — Interactive DP Learning
Inspired by dpvis:
- Show partially filled DP table
- Player must predict: (1) which cells are read next, (2) where result goes, (3) what the value is
- Each correct prediction earns points
- Animated dependency arrows show relationships
- Works for knapsack, LCS, edit distance, coin change, etc.

### 9.7 "The Sorting Hat" — Algorithm Selection Game
- Given a real-world scenario description (sort library books, rank search results, process streaming data)
- Player must select the most appropriate algorithm
- Justify the choice by selecting relevant properties (stable? in-place? worst-case guarantee?)
- Score based on appropriateness of choice + quality of justification

---

## 10. Architecture Recommendations

### 10.1 Template Structure

```
AlgorithmGame
├── Phases (1-4 per game, configured by AI)
│   ├── Phase 1: Understand (Predict-Output / Pattern Matcher)
│   ├── Phase 2: Execute (Manual Execution / State Tracer)
│   ├── Phase 3: Debug (Bug Hunter / Code Completion)
│   └── Phase 4: Master (Parsons / Test Case / Optimization)
├── Visual Components (composed per algorithm type)
│   ├── ArrayVisualizer
│   ├── GraphVisualizer
│   ├── TreeVisualizer
│   ├── TableVisualizer (DP)
│   ├── CodePanel
│   ├── CallStackPanel
│   └── ComparisonCounter
└── Game Engine
    ├── StepValidator (validates each player action)
    ├── AlgorithmSimulator (runs reference implementation)
    ├── ScoringEngine (delta-based scoring)
    ├── HintSystem (progressive hints with penalty)
    └── AdaptiveEngine (difficulty adjustment)
```

### 10.2 Data Model (What AI Pipeline Generates)

```typescript
interface AlgorithmGameBlueprint {
  // Metadata
  algorithm_type: AlgorithmCategory;    // sorting | graph | tree | dp | greedy | backtracking | ...
  algorithm_name: string;               // "merge_sort" | "dijkstra" | "knapsack" | ...
  difficulty: 1 | 2 | 3 | 4;           // Maps to Bloom levels

  // Visual configuration
  visualizer_type: "array" | "graph" | "tree" | "table" | "grid" | "timeline" | "chessboard";
  initial_data: any;                    // The data structure to operate on

  // Phases
  phases: Phase[];

  // Reference solution (for validation)
  algorithm_steps: AlgorithmStep[];     // Full execution trace
  reference_code: CodeBlock;            // Correct implementation
  buggy_code?: CodeBlock;               // Intentionally buggy version
  parsons_blocks?: ParsonsBlock[];      // Scrambled code blocks

  // Scoring
  max_score: number;
  time_limit_seconds?: number;
  hint_budget: number;
}

interface Phase {
  type: "predict" | "execute" | "debug" | "master";
  task_type: TaskType;                  // State_tracer | bug_hunter | manual_execution | ...
  instructions: string;
  data: any;                            // Phase-specific data
  validation_steps: ValidationStep[];
  max_score: number;
}

interface AlgorithmStep {
  step_number: number;
  action: string;                       // "compare(2,5)" | "swap(i,j)" | "visit(node_3)" | ...
  state_before: any;                    // Full data structure state
  state_after: any;
  highlighted_elements: string[];       // Which elements are active
  code_line?: number;                   // Which line of code is executing
  explanation: string;                  // Human-readable description
}
```

### 10.3 AI Generation Pipeline

The V3 pipeline should generate:
1. **Algorithm identification** — Classify the input question to algorithm category + specific algorithm
2. **Data generation** — Create appropriate initial data (array, graph, tree, etc.) with good pedagogical properties (not too easy, not too hard)
3. **Reference execution** — Run the algorithm and record every step (the "gold standard" trace)
4. **Phase generation** — Select 2-4 phase types appropriate for the algorithm
5. **Bug injection** — Intelligently introduce bugs into the reference code (for debug phases)
6. **Parsons scrambling** — Shuffle code lines and add distractors (for Parsons phases)
7. **Visual configuration** — Select appropriate visualizer type and configure layout
8. **Hint generation** — Create progressive hints for each phase

### 10.4 Frontend Component Architecture

Key insight from Interactive Diagram template: **Zustand store for game state, components for rendering**.

```
AlgorithmGameTemplate/
├── index.tsx                    # Main orchestrator
├── hooks/
│   ├── useAlgorithmGameState.ts # Zustand store (phases, score, current step)
│   ├── useStepValidator.ts      # Validates player actions against reference
│   └── useAlgorithmAnimator.ts  # Animation playback engine
├── visualizers/
│   ├── ArrayVisualizer.tsx      # Bars/blocks with swap animation
│   ├── GraphVisualizer.tsx      # Force-directed graph with traversal colors
│   ├── TreeVisualizer.tsx       # Animated tree with rotations
│   ├── TableVisualizer.tsx      # Grid for DP tables
│   ├── CodePanel.tsx            # Syntax-highlighted code with line tracking
│   └── CallStackPanel.tsx       # Stack frame visualization
├── tasks/
│   ├── StateTracer.tsx          # Step-through with prediction
│   ├── ManualExecution.tsx      # Be-the-algorithm task
│   ├── BugHunter.tsx            # Find-the-bug task
│   ├── ParsonsTask.tsx          # Code reordering task
│   ├── PredictOutput.tsx        # Output prediction task
│   ├── OptimizationRace.tsx     # Algorithm comparison
│   └── ComplexityAnalyzer.tsx   # Big-O identification
├── controls/
│   ├── PhaseProgress.tsx        # Phase navigation
│   ├── StepControls.tsx         # Play/Pause/Step/Speed
│   ├── HintButton.tsx           # Progressive hints
│   └── ScoreDisplay.tsx         # Running score
└── types.ts                     # TypeScript interfaces
```

---

## 11. Named Game Designs Per Algorithm (Detailed)

Concrete game concepts with narratives, mechanics, scoring, and 5-level difficulty scaling for the highest-priority algorithm categories.

### 11.1 Sorting

| # | Algorithm | Game Name | Core Mechanic | Key Interaction |
|---|-----------|-----------|---------------|-----------------|
| 1 | Bubble Sort | **Bubble Brawl** | Conveyor belt of crates rolling toward furnace; only adjacent swaps allowed | Tap to swap adjacent, green checkmark on settled elements |
| 2 | Merge Sort | **Divide & Conquer Kitchen** | Restaurant where ingredient cards are split and merged | Drag splitter at midpoint, click smaller top card during merge |
| 3 | Quick Sort | **Pivot Party** | Party guests arranged by height around a pivot | Pick pivot, drag guests left/right; pivot quality bonus |
| 4 | Heap Sort | **Royal Heap** | Medieval kingdom pyramid of subjects by rank | Sift-down/sift-up swaps; dual array+tree view |
| 5 | Radix Sort | **Postal Sorter** | Mail room sorting by digit into 10 mailboxes | Drag letter cards into digit buckets; collect in order |
| 6 | Sorting Races | **Algorithm Arena** | Split-screen race: manual vs. animated algorithm | Choose algorithms, choose input type, compare metrics |

**Bubble Brawl Difficulty Scaling:**
- L1: 4 elements, no timer, swap hints — L2: 6 elements, gentle timer — L3: 8 elements, strict timer — L4: 10+ nearly-sorted (testing early termination) — L5: Race against animated algorithm

**Pivot Party Scoring:**
- Correct partitioning points + pivot quality bonus (near-median = best)
- Penalty for worst pivot (min/max element)
- Recursion tree depth tracker (shallow = good pivots)

### 11.2 Graph Algorithms

| # | Algorithm | Game Name | Core Mechanic | Key Interaction |
|---|-----------|-----------|---------------|-----------------|
| 1 | BFS/DFS | **Maze Explorer** | Fog-of-war dungeon; BFS=frontier ring, DFS=deep path | Click next node in queue/stack order |
| 2 | Dijkstra | **Metro Navigator** | Delivery driver in weighted city map | Select min-distance node, relax neighbor edges |
| 3 | MST | **Cable Company** | Fiber optic cable executive connecting cities | Pick cheapest valid edge; reject cycle-creating edges |
| 4 | Topological Sort | **Project Planner** | Project manager scheduling tasks with dependencies | Click zero-in-degree tasks to schedule |
| 5 | Network Flow | **Pipeline Puzzle** | Water utility engineer maximizing pipe flow | Draw augmenting paths source→sink |
| 6 | Cycle Detection | **Loop Detective** | Detective inspecting directed graph via DFS coloring | Mark back edges when encountering gray nodes |

**Metro Navigator Difficulty Scaling:**
- L1: 5-node graph, guided relaxation — L2: 10-node city, manual priority queue — L3: Real metro map (20+ stations) — L4: Negative-weight traps (Dijkstra failure) — L5: Dijkstra vs. A* comparison

### 11.3 Tree Algorithms

| # | Algorithm | Game Name | Core Mechanic | Key Interaction |
|---|-----------|-----------|---------------|-----------------|
| 1 | BST Operations | **Binary Orchard** | Digital orchard; seeds planted by navigating left/right | Click go-left/go-right at each node |
| 2 | AVL Rotations | **Balance Master** | Unbalanced trees as "sick patients" needing rotation surgery | Identify rotation type (LL/RR/LR/RL), perform it |
| 3 | Tree Traversals | **Node Navigator** | Click nodes in correct traversal order | In/pre/post/level-order click sequence |
| 4 | Trie | **Word Weaver** | Word-building game growing a prefix tree | Type words → trie grows; autocomplete challenge |
| 5 | Heap Operations | **Emergency Room** | ER with patient severity = priority | Sift-up on insert, sift-down on extract-min |

**Binary Orchard Scoring:**
- Points per correct left/right decision during insertion
- Delete mode: points for choosing correct strategy (leaf/one-child/two-children)
- Tree health metric: current height vs. optimal (log n)

### 11.4 Dynamic Programming

| # | Algorithm | Game Name | Core Mechanic | Key Interaction |
|---|-----------|-----------|---------------|-----------------|
| 1 | Knapsack | **Treasure Packer** | Treasure hunter with limited backpack | Drag items in; DP table fills alongside |
| 2 | Coin Change | **Exact Change** | Vending machine requiring exact payment | Drag coins to slot; 1D DP array builds |
| 3 | LCS | **Sequence Sleuth** | Two spy coded messages; find common subsequence | Fill 2D DP table; trace back with arrows |
| 4 | Edit Distance | **Word Morph** | Transform one word to another with min operations | Apply insert/delete/substitute; compare to DP optimal |
| 5 | Matrix Chain | **Parenthesis Puzzle** | Sequence of matrices to multiply optimally | Place parentheses between matrices; cost calculator |

**DP Table as Central Game Board (cross-cutting mechanic):**
- **Flood Fill**: cells fill based on dependencies; player controls fill order
- **Tile Reveal**: cells start face-down; player flips, computes, writes value
- **Color Coding**: match=gold, skip=blue, backtrace=green
- **Speed Run**: time trial to fill entire DP table correctly

### 11.5 Backtracking

| # | Algorithm | Game Name | Core Mechanic | Key Interaction |
|---|-----------|-----------|---------------|-----------------|
| 1 | N-Queens | **Royal Placement** | Place queens safely on chessboard | Click cells per row; backtrack on dead-end |
| 2 | Sudoku | **Backtracking Coach** | Sudoku with algorithm visualization | Enter numbers; backtrack when stuck |
| 3 | Graph Coloring | **Chromatic Challenge** | Color map regions with minimum colors | Assign colors; avoid adjacent conflicts |
| 4 | Maze Gen/Solve | **Maze Architect** | Generate maze via DFS, then solve | Remove walls via DFS; solve via BFS/A* |
| 5 | Subset Sum | **Target Selector** | Select numbers summing to target | Toggle include/exclude; prune branches |

### 11.6 Greedy Algorithms

| # | Algorithm | Game Name | Core Mechanic | Key Interaction |
|---|-----------|-----------|---------------|-----------------|
| 1 | Activity Selection | **Event Planner** | Maximize non-overlapping events on timeline | Click events to select; greedy hint available |
| 2 | Huffman Coding | **Compression Station** | Telegraph operator encoding messages efficiently | Merge two smallest-frequency nodes repeatedly |
| 3 | Job Scheduling | **Deadline Dash** | Schedule jobs with deadlines for max profit | Drag jobs into time slots ≤ deadline |

### 11.7 Recursion

| # | Algorithm | Game Name | Core Mechanic | Key Interaction |
|---|-----------|-----------|---------------|-----------------|
| 1 | Tower of Hanoi | **Tower Transfer** | Classic puzzle with recursive strategy visualization | Drag disks; call stack + recursion tree shown |
| 2 | Fractal Drawing | **Recursive Artist** | Define recursive drawing rule, watch fractals grow | Set base shape, apply recursion levels |
| 3 | Call Stack | **Stack Diver** | Dive into recursive calls, pushing frames | Push/pop frames; predict return values |

### 11.8 String Algorithms

| # | Algorithm | Game Name | Core Mechanic | Key Interaction |
|---|-----------|-----------|---------------|-----------------|
| 1 | Pattern Matching | **Code Breaker** | Find hidden pattern in scrolling text | Slide pattern window; compare characters |
| 2 | KMP Failure Fn | **Prefix Matcher** | Build KMP failure function for a pattern | Enter prefix-suffix lengths per position |
| 3 | String Hashing | **Duplicate Detector** | Detect duplicates in string stream via hashing | Compute hash, check bucket, verify on collision |

---

## 12. Implementation Priority Matrix

### 12.1 Priority Rankings

| Priority | Category | Score | Rationale |
|----------|----------|-------|-----------|
| **P0** | Sorting Algorithms | 95 | Universal demand, excellent gamification fit, proven mechanics (Sort Attack, MakeSort) |
| **P0** | Graph Algorithms (BFS/DFS/Dijkstra/MST) | 93 | High demand, natural path-tracing mechanic, strong research (iFlow, Red Blob Games) |
| **P0** | Tree Algorithms (BST/AVL) | 90 | Core CS, proven game effectiveness (DS-Hacker: 87 vs 60 avg), construction mechanic |
| **P1** | Dynamic Programming | 88 | High demand, table-filling is natural game, **HUGE market gap** |
| **P1** | Recursion Patterns | 85 | Foundational concept, natural game metaphors (Tower of Hanoi), moderate gap |
| **P1** | Backtracking | 83 | Inherently puzzle-like, constraint satisfaction IS a game already |
| **P2** | Searching Algorithms | 80 | Universal demand, simple mechanics, partially served by existing tools |
| **P2** | Greedy Algorithms | 78 | Good gamification fit, significant market gap |
| **P2** | Divide and Conquer | 75 | Important meta-pattern, moderate gamification fit |
| **P3** | String Algorithms | 72 | Niche demand, moderate gamification fit, large gap |
| **P3** | Network/Flow Algorithms | 70 | Specialized demand, excellent fit (iFlow model) |
| **P3** | Hash-Based Algorithms | 68 | Moderate demand, good fit (Bloom filter visualizations exist) |
| **P4** | Computational Geometry | 60 | Niche demand, excellent visual fit but small audience |

### 12.2 Market Gap Analysis

**Well-served** (existing interactive tools exist):
- Sorting algorithms (Sort Attack, MakeSort, VisuAlgo, many others)
- Graph traversal and shortest path (VisuAlgo, Learn Graph Theory, iFlow)
- BST/AVL trees (VisuAlgo, DS-Hacker, AVL Tree Game, USF visualizations)
- Network flow (iFlow SIGCSE 2025, VisuAlgo)

**Underserved** (significant opportunity for GamED.AI):
- Dynamic programming — few interactive tools, mostly passive visualization
- String algorithms — almost no gamified tools
- Greedy algorithms — no dedicated games
- Backtracking — puzzles exist but not as algorithm-teaching tools
- Divide and conquer — meta-pattern poorly served
- Recursion — Tower of Hanoi only; deeper concepts neglected
- Hash tables beyond Bloom filters — limited interactivity
- Computational geometry — minimal gamification

### 12.3 Quick-Win Implementations (Highest ROI)

1. **Sorting Step-Through Predictor** — Predict next swap/comparison for any sorting algorithm. Minimal UI, maximum learning.
2. **Graph Path Tracer** — Draw BFS/DFS/Dijkstra paths on interactive graph. Click-based.
3. **BST Builder Game** — Insert values into BST; predict structure; perform AVL rotations.
4. **DP Table Filler** — Fill DP tables cell-by-cell with dependency arrows. Huge gap.
5. **Recursion Tree Explorer** — Expand recursion tree; identify repeated subproblems; toggle memoization.

---

## 13. Cross-Cutting Design Principles (Research Synthesis)

### 13.1 Seven Principles from Academic Literature

1. **Active engagement is non-negotiable.** Naps et al. (2002) conclusively showed that viewing visualizations without interaction produces minimal learning gains. Every mechanic must require prediction, manipulation, or construction — not just observation.

2. **Prediction before revelation.** The most powerful pattern across all mechanics: show state → ask player to predict next state → then reveal. This forces active cognitive processing. (dpvis, Python Tutor research)

3. **Progressive scaffolding removal.** Start with heavy scaffolding (many hints, partial algorithms, multiple choice) and gradually remove it (fewer hints, blank algorithms, free-form input). Parsons Problems research shows code reordering as stepping stone to code writing.

4. **Immediate, rich feedback.** Binary right/wrong is insufficient. Feedback must explain WHY an answer is wrong and guide toward correct understanding. But hint systems must be designed carefully to avoid "gaming the system" behaviors. (Gidget seven design principles; O'Rourke 2014 finding that hints may negatively impact performance if poorly designed)

5. **Multiple representations.** Same algorithm experienceable through code, visualization, manipulation, and narrative. Different students learn best through different modalities.

6. **Efficiency as a game mechanic.** Making time/space complexity a scoring dimension (not just correctness) naturally teaches algorithm analysis without requiring formal mathematical instruction.

7. **Self-constructed input.** Let learners choose their own inputs. This consistently produces better learning outcomes than experimenter-supplied inputs. (Hundhausen meta-study)

### 13.2 Standard Difficulty Framework

| Tier | Bloom Level | Player Action | Assessment |
|------|------------|---------------|------------|
| **Observer** | Remember + Understand | Watch animation, answer comprehension questions | Multiple choice, ordering |
| **Executor** | Apply | Execute algorithm steps on given input | Step-by-step correctness |
| **Analyst** | Analyze + Evaluate | Compare algorithms, find bugs, predict complexity | Open-ended analysis |
| **Designer** | Create | Design solutions for novel problems, optimize | Construction + explanation |

### 13.3 Interaction Primitive Matrix

| Mechanic | Drag-Drop | Click Seq | Drawing | Typing | Sliders | Selection | Reorder | Toggle |
|---|---|---|---|---|---|---|---|---|
| State Tracer | - | Next step | - | Predicted values | Step/speed | Predicted state | - | Breakpoints |
| Bug Hunter | Drag fix | Click buggy line | - | Type fix | - | Bug type | - | Hints |
| Manual Execution | Swap elements | Click nodes | Draw edges | Node values | Zoom/pan | Operation type | Array drag | Parent/child |
| Algorithm Builder | Block assembly | Connect blocks | Flow arrows | Parameters | - | Block palette | Parsons reorder | Enable/disable |
| Prediction Game | - | - | - | Output/value | - | Multiple choice | Predicted sequence | - |
| Optimization Race | - | Submit | - | Code | Speed/scale | Algorithm choice | - | Constraints |
| Pathfinder | Path waypoints | Traversal order | Draw paths | Edge weights | Anim speed | Algorithm type | - | Visited toggle |
| Pattern Matcher | Name→behavior | - | Match lines | - | - | Multiple choice | - | - |
| Constraint Puzzle | Items/pieces | Cell clicks | - | Solutions | - | Placement | - | Constraint display |
| Code Completion | Lines into blanks | Select blank | - | Missing code | - | Multiple choice | Scrambled lines | - |

### 13.4 Gamification Element Selection (Toda et al. TGEEE)

From the 21-element taxonomy, highest-impact for algorithm games:

| Element | Implementation |
|---------|---------------|
| **Points** | Per-step correctness + streak multipliers |
| **Progression** | 4-tier difficulty (Observer → Designer) |
| **Levels** | Algorithm-specific levels with star ratings |
| **Stats** | Accuracy %, operation count, hint usage, streak length |
| **Acknowledgement** | Algorithm mastery badges, "Perfect Run" achievements |
| **Competition** | Leaderboards by algorithm, time trials |
| **Puzzle** | Constraint puzzles as game core |
| **Novelty** | Different game framing per algorithm (kitchen, detective, hospital, etc.) |
| **Narrative** | Story-wrapped algorithm concepts (Robot Navigation = BFS, Potion Sorting = comparison sorts) |

### 13.5 Feedback Taxonomy (6 Types)

1. **Confirmatory** — "Correct!" / "Incorrect" — binary signal
2. **Explanatory** — "Wrong because bubble sort compares adjacent elements, not elements at distance 2"
3. **Corrective** — Shows the right answer after incorrect attempt
4. **Procedural** — "Try tracing step by step using the values given" — guides process
5. **Affirming** — "Great job! You correctly identified the O(n log n) pattern"
6. **Adaptive** — Adjusts detail based on learner model (experts get minimal, novices get rich explanations)

---

## 14. References

### Platforms & Tools
- [VisuAlgo](https://visualgo.net/en) — NUS algorithm visualization
- [Algorithm Visualizer](https://algorithm-visualizer.org/) — Open-source code + visual
- [Red Blob Games](https://www.redblobgames.com/) — Amit Patel's interactive tutorials
- [OpenDSA](https://opendsa-server.cs.vt.edu/) — Interactive DS&A eTextbook (JSAV)
- [Python Tutor](https://pythontutor.com/) — Code execution visualizer
- [SortVision](https://www.sortvision.com/) — Sorting algorithm visualizer
- [dpvis](https://github.com/itsdawei/dpvis) — DP visualization with self-test (SIGCSE 2025)
- [Brilliant.org](https://brilliant.org/) — Interactive learning platform
- [CodinGame](https://www.codingame.com/) — Coding games with visual environments
- [CodeCombat](https://codecombat.com/) — RPG coding game
- [Codewars](https://www.codewars.com/) — Martial arts-themed coding challenges
- [LeetCode](https://leetcode.com/) — Algorithm challenge platform
- [HackerRank](https://www.hackerrank.com/) — Skills platform with certifications
- [Exercism](https://exercism.org/) — Free coding exercises with mentorship
- [CS Unplugged](https://www.csunplugged.org/) — Physical algorithm activities
- [Code Defenders](https://code-defenders.org/) — Mutation testing game
- [Sojourner under Sabotage](https://arxiv.org/abs/2504.19287) — Debugging serious game
- [JFLAP](https://www.jflap.org/) — Automata visualization
- [Huffman Visualization](https://huffman.ooz.ie/) — Interactive Huffman tree builder
- [Dijkstra Underground Game](https://www.doc.gold.ac.uk/goldplugins/index.php/2020/03/25/dijkstras-algorithm/) — Subway pathfinding puzzle

### Games
- [Human Resource Machine](https://store.steampowered.com/app/375820/Human_Resource_Machine/) — Assembly language puzzle game
- [7 Billion Humans](https://store.steampowered.com/app/792100/7_Billion_Humans/) — Parallel programming puzzles
- [while True: learn()](https://store.steampowered.com/app/619150/while_True_learn/) — ML pipeline puzzle game
- [Potato Pirates](https://potatopirates.game/) — Unplugged coding card game

### Academic Research
- Naps et al. (2002) "Exploring the Role of Visualization and Engagement in CS Education" — Engagement taxonomy
- Hundhausen et al. (2002) "A Meta-Study of Algorithm Visualization Effectiveness" — Active engagement is key
- Zeng et al. (2024) "Exploring the impact of gamification on students' academic performance" — Meta-analysis g=0.782
- Kurnaz (2025) "A Meta-Analysis of Gamification's Impact on Student Motivation in K-12" — g=0.654
- Parsons & Haden (2006) "Parson's Programming Puzzles" — Code reordering exercises
- Ericson (2022) "Parsons Problems and Beyond: Systematic Literature Review" — 50% time savings
- dpvis (2024) "A Visual and Interactive Learning Tool for Dynamic Programming" — Self-testing mode
- "Bloom's for Computing: Enhancing Bloom's Revised Taxonomy" — ACM CS-specific taxonomy
- "Adaptive Difficulty and Stealth Assessment in Collaborative Game-Based Learning" (2025)
- "Effects of adaptive scaffolding on performance, cognitive load and engagement in game-based learning" (2024)
