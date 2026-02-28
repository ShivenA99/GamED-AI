# GamED.AI v2 → Algorithm Gameification Integration Audit Report

**Date**: February 14, 2026  
**Status**: Complete Architectural Analysis  
**Scope**: Integrating algorithms.txt (Pathfinder/BFS-DFS, Merge Sort, Dijkstra/Prim MST, Knapsack DP) into existing pipeline  

---

## EXECUTIVE SUMMARY

### Current State
GamED.AI v2 has a robust **diagram-to-game pipeline** optimized for anatomy, circuits, and visual concept labeling. The system includes:
- **16 game templates** (7 active) with blueprint validation
- **Multi-agent orchestration** (59+ agents) with configurable LLM backends
- **Asset pipeline** (web search, VLM zone detection, SAM segmentation)
- **State management** via LangGraph + Pydantic schemas
- **Frontend**: React/Next.js with drag-drop, sequencing, and parameter playground mechanics

### The Challenge
Algorithms change the game fundamentally:
- **No visual diagram** → Requires abstract state visualization (queues, stacks, trees, graphs)
- **Player is the algorithm** → User makes moves that prove algorithmic understanding
- **Mechanical fidelity** → Illegal moves must be attempted and penalized, not prevented
- **Dynamic structures** → Zones/labels from diagrams don't apply; data structures are computational

### The Opportunity
The 4 algorithm families from algorithms.txt map cleanly to **4 new template types + 1 enhanced base**:

| Algorithm Family | Game Mechanic | New Template | Pedagogical Gain |
|---|---|---|---|
| **Pathfinding (BFS/DFS)** | Dungeon crawler + queue/stack visualization | `PATHFINDER` | Proof: player follows or violates FIFO/LIFO order |
| **Spatial Sorting (Merge Sort)** | Warehouse manager + recursive level tracking | `MERGE_MASTER` | Proof: player recognizes divide-and-conquer or wastes swaps |
| **Network Optimization (Dijkstra/Prim)** | Power grid builder + constraint enforcement | `GRAPH_ARCHITECT` | Proof: player picks greedy edge or learns through suboptimality |
| **Resource Management (Knapsack)** | Backpack packer + capacity feedback | `BALANCE_ACT` | Proof: player recognizes subproblem structure or picks greedily |

---

## PHASE 1: CURRENT STATE ASSESSMENT

### 1.1 Workflow Visualization: From Template to Playable Game

```
┌─────────────────────────────────────────────────────────────────┐
│                    GamED.AI v2 Pipeline                         │
└─────────────────────────────────────────────────────────────────┘

INPUT                                    ROUTING
  │                                         │
  ├─ Question Text ──┐              ┌─ Infer Bloom's lvl
  ├─ Domain Context │──InputEnhancer├─ Extract subject
  ├─ Desired Template│              ├─ Identify concepts
  └─ Optional Image  │              └─ Difficulty level
                     │
                     ▼
            DomainKnowledgeRetriever
                     │
         ┌───────────┴──────────────┐
         │                          │
      OUTPUT                     DESIGN PHASE
    Labels &                         │
    Relations                   GamePlanner
         │                    (mechanics → scenes)
         │                           │
         ▼                           ▼
    INTERNAL FLOW           InteractionDesigner
    (Template-Specific)     (scoring, hints, transitions)
         │                           │
         ├─ LABEL_DIAGRAM ──┬─ SceneGenerator
         │   (zones from       │   (visual assets)
         │    image +          │
         │    VLM)             ├─ BlueprintGenerator
         │                     │   (JSON schema)
         ├─ SEQUENCE_BUILDER ─┤
         ├─ BUCKET_SORT ───────┤
         └─ [Others] ─────────┘
                     │
                     ▼
               PRODUCTION
            BlueprintValidator (3x retry)
                     │
            ┌────────┴────────────┐
            │                     │
        Valid                 Invalid
            │                 (→ Fix & Retry)
            │
            ▼
      [OPTIONAL] Asset Pipeline
      - Retrieve/Generate Images
      - Create SVG Specs
      - Validate Playability
            │
            ▼
        Final Output: Game JSON
        ▼
    Frontend Renderer
    ┌─────────────────────────────┐
    │ React Game Component        │
    │ - Blueprint as props        │
    │ - State hooks (React)       │
    │ - Drag-drop / interactions  │
    │ - Scoring & feedback        │
    └─────────────────────────────┘
```

### 1.2 Pipeline Bottlenecks for Algorithm Games

#### **Bottleneck A: Diagram Dependency**
**Problem**: Entire pipeline designed around visual diagrams.
- **Input Enhancer**: Optimized for "label these anatomical structures"
- **Domain Knowledge Retriever**: Searches for visual diagrams with labels
- **Game Planner**: Assumes zones from images
- **Image Pipeline**: 60% of agent code for SAM, Qwen VL zone detection

**Why it breaks**: Algorithm games have NO diagram. Input is:
```json
{
  "question_text": "Implement BFS to find shortest path",
  "domain_context": "graph_algorithms",
  "data_input": {
    "graph": [[1,2], [2,3], [3,4]],
    "start_node": 0,
    "goal_node": 3
  }
}
```

**Impact**: 70% of the pipeline is irrelevant. Diagram retriever, image segmenter, VLM zone detector all fail gracefully but add latency.

#### **Bottleneck B: Static Zones → Dynamic Structures**
**Problem**: Blueprint expects fixed zones (from image) with positions and hierarchy.

Current INTERACTIVE_DIAGRAM schema:
```json
{
  "zones": [
    { "id": "zone_1", "label": "Part A", "x": 0.3, "y": 0.5, "radius": 10 },
    { "id": "zone_2", "label": "Part B", "x": 0.7, "y": 0.5, "radius": 12 }
  ]
}
```

Algorithm games need **stateful structures**:
```json
{
  "initialState": {
    "queue": [],
    "visited": [],
    "unvisited": [0, 1, 2, 3]
  },
  "currentState": {
    "queue": [0],
    "visited": [],
    "unvisited": [1, 2, 3]
  },
  "expectedNextState": {
    "queue": [1, 2],
    "visited": [0],
    "unvisited": [3]
  },
  "userAttempt": "queue=[1]"
}
```

**Impact**: BlueprintGenerator has 40+ hardcoded fallback zone positions; zone validation checks for area/radius; the entire DropZone component assumes static geometry.

#### **Bottleneck C: Single-Mode Interaction**
**Problem**: Current templates support 1 primary mechanic per game.

Existing mechanics:
- `drag_drop` (INTERACTIVE_DIAGRAM)
- `sequencing` (SEQUENCE_BUILDER)
- `matching` (MATCH_PAIRS)
- `parameter_adjustment` (BUCKET_SORT)

Algorithm games require **sequential, multi-phase interactions**:
- Phase 1: Initialize data structure (drag nodes into queue)
- Phase 2: Make moves (click next node to visit per BFS order)
- Phase 3: Verify state (system checks if queue/visited are correct)
- Phase 4: Get feedback (Sync meter updated, points awarded/deducted)

**Impact**: No template supports "make illegal moves, then get penalized." Current design prevents invalid states. Algorithm games need them.

#### **Bottleneck D: Scoring is Template-Hardcoded**
**Problem**: Every template hardcodes scoring formulas.

Examples (from frontend hooks):
```typescript
// useLabelDiagramState.ts line 334
state.score + 10  // Hardcoded base points

// ResultsPanel.tsx line 35-41
feedback >= 70% ? "Great!" : "Keep practicing!"  // Hardcoded threshold
```

Algorithm games need **algorithmic correctness scoring**:
```json
{
  "points": {
    "node_visited_correctly": 10,
    "node_visited_out_of_order": -5,
    "completed_bfs_without_violations": 50,
    "bonus_shortest_path": 20
  },
  "success_condition": "Completed BFS with >= 80% correctness"
}
```

**Impact**: Changing scoring requires modifying 7+ places in frontend + backend. New template types can't customize without code changes.

---

## PHASE 2: ALGORITHM EXPANSION STRATEGY

### 2.1 Logic-to-Mechanic Mapping

For each algorithm in algorithms.txt, here's how the **logical core** translates to **game mechanics**:

#### **FAMILY 1: Pathfinding (BFS/DFS)**

**Logical Core**: "Process neighbors in specific order (queue/stack) to explore from a start node"

**Game Mechanic — "The Pathfinder"**:

| Component | How It Works | Why It Teaches |
|-----------|-------------|---|
| **Data Structure Visualization** | Queue (FIFO) shown as horizontal stack, Stack (LIFO) as vertical stack | Player sees pending nodes in order; violating order shows instantly |
| **Player Move** | Click next node to "visit" | Forces explicit choice; illegal choice breaks Sync meter |
| **Illegal Move Detection** | If clicked node is not at front of queue, Sync drops 20% | Proof student doesn't understand FIFO |
| **Correct Move Reward** | +10 points, node moves to visited, queue recalculates | Reinforces algorithm step |
| **Completion Proof** | Reached goal with queue order maintained = algorithm understood | Student literally followed the algorithm |

**Blueprint Schema Addition**:
```json
{
  "templateType": "PATHFINDER",
  "algorithmType": "bfs" | "dfs",
  "graph": {
    "nodes": [0, 1, 2, 3],
    "edges": [[0,1], [0,2], [1,3], [2,3]],
    "start_node": 0,
    "goal_node": 3
  },
  "dataStructuresVisible": ["queue", "visited", "unvisited"],
  "success_condition": "Reached goal via BFS order with zero violations"
}
```

---

#### **FAMILY 2: Sorting (Merge Sort)**

**Logical Core**: "Recursively split into size-1 chunks, then merge sorted sublists in order"

**Game Mechanic — "Merge Master"**:

| Component | How It Works | Why It Teaches |
|-----------|-------------|---|
| **Visual Recursion Levels** | 3-5 colored tabs (Level 0 = whole array, Level 3 = size-1 chunks) | Player sees the pyramid structure; skipping a level is impossible |
| **Player Move** | On each level, merge two sublists by deciding "left or right first?" | Forces recognition of sorted nature; random choice → time loss |
| **Compare Visibility** | Left/Right sublists shown as columns; values highlighted when compared | Player actively sees "3 < 7, so left first" logic |
| **Constraint Enforcement** | Can only merge **sorted** sublists; if attempted on unsorted, game says "These aren't the same recursion level" | Mechanical fidelity: illegal move is attempted |
| **Efficiency Tracking** | Time to complete measures algorithm efficiency | O(n²) bubble sort vs O(n log n) merge sort becomes concrete |

**Blueprint Schema Addition**:
```json
{
  "templateType": "MERGE_MASTER",
  "algorithm": "merge_sort",
  "array": [5, 2, 8, 1, 9],
  "recursion_levels": 3,
  "tasks": [
    {
      "level": 0,
      "left": [5, 2],
      "right": [8, 1, 9],
      "instruction": "Merge these two sorted sublists by choosing left or right first"
    }
  ],
  "success_metrics": {
    "correctness": "All merges in order",
    "efficiency": "Completed in minimum moves"
  }
}
```

---

#### **FAMILY 3: Network Optimization (Dijkstra / Prim MST)**

**Logical Core**: "Greedily select minimum-cost edge from boundary to build shortest path / spanning tree"

**Game Mechanic — "Graph Architect"**:

| Component | How It Works | Why It Teaches |
|-----------|-------------|---|
| **Graph Visualization** | Cities as nodes, distances as edge labels, unvisited in gray, boundary in yellow, visited in green | Player sees the search frontier |
| **Player Move** | Click an edge from boundary to add to tree | Choice is visible; wrong choices make suboptimal tree |
| **Constraint: Greedy Rule** | Only edges from visited→unvisited are clickable (boundary edges only) | Mechanical fidelity: illegal edges are grayed out but visible |
| **Non-Penalty for Suboptimal** | If player picks higher-cost boundary edge, tree still grows but score lower | Proof through sub optimization, not failure |
| **Completion Proof** | All nodes connected with all minimum-cost edges = understood greedy selection | Comparison: optimal MST weight vs. player's MST weight |

**Blueprint Schema Addition**:
```json
{
  "templateType": "GRAPH_ARCHITECT",
  "algorithm": "prim_mst" | "dijkstra",
  "graph": {
    "nodes": ["CityA", "CityB", "CityC"],
    "edges": [
      {"from": "CityA", "to": "CityB", "weight": 5},
      {"from": "CityB", "to": "CityC", "weight": 3}
    ]
  },
  "dataStructuresVisible": ["tree_edges", "boundary_edges", "visited_nodes"],
  "success_condition": "All nodes connected with minimum total weight"
}
```

---

#### **FAMILY 4: Resource Management (0/1 Knapsack)**

**Logical Core**: "Decide include/exclude per item while respecting capacity constraint; current decision depends only on remaining capacity"

**Game Mechanic — "Balance Act"**:

| Component | How It Works | Why It Teaches |
|-----------|-------------|---|
| **Backpack Visual** | Capacity bar showing used/remaining; items shown as cards | Player sees real-time impact of each item choice |
| **Player Move** | Drag item into backpack or click "add" | Discrete choice; no fractional items (0/1 property) |
| **Constraint Feedback** | Real-time: "Item too heavy" or "Exceeds capacity" | Prevents illegal states; teaches constraint recognition |
| **Suboptimality Visibility** | After completion, game shows optimal value vs. player's value | Proof: if player was greedy (highest value/weight), they see the gap |
| **Recursive Insight** | Bonus unlock if player recognizes: "The choice for item 3 depends only on remaining capacity, not items 1-2" | Proof of subproblem understanding |

**Blueprint Schema Addition**:
```json
{
  "templateType": "BALANCE_ACT",
  "algorithm": "knapsack_0_1",
  "capacity": 20,
  "items": [
    { "id": "item_1", "weight": 5, "value": 10 },
    { "id": "item_2", "weight": 10, "value": 40 }
  ],
  "scoringStrategy": {
    "optimal_value": 50,
    "points_per_correct_choice": 5,
    "bonus_for_optimal": 50
  }
}
```

---

### 2.2 Template Modifications (Minimal Changes to Existing System)

#### **Step 1: Add 4 New Template Types to Registry**

File: `backend/app/config/template_registry.py` (new or extend existing)

```python
ALGORITHM_TEMPLATES = {
    "PATHFINDER": {
        "description": "BFS/DFS graph traversal with queue/stack visualization",
        "required_fields": [
            "algorithmType",  # "bfs" or "dfs"
            "graph",          # nodes, edges, start, goal
            "dataStructuresVisible"  # which state structures to show
        ],
        "supported_mechanics": ["queue_interaction", "stack_interaction", "node_selection"],
        "react_component": "PathfinderGame"
    },
    "MERGE_MASTER": {
        "description": "Merge sort with recursion level visualization",
        "required_fields": [
            "array",
            "recursion_levels",
            "tasks"
        ],
        "supported_mechanics": ["merge_decision", "level_navigation"],
        "react_component": "MergeMasterGame"
    },
    "GRAPH_ARCHITECT": {
        "description": "Dijkstra/Prim network optimization with edge selection",
        "required_fields": [
            "algorithm",
            "graph",
            "dataStructuresVisible"
        ],
        "supported_mechanics": ["edge_selection", "boundary_constraint"],
        "react_component": "GraphArchitectGame"
    },
    "BALANCE_ACT": {
        "description": "0/1 Knapsack with capacity constraints",
        "required_fields": [
            "capacity",
            "items",
            "scoringStrategy"
        ],
        "supported_mechanics": ["item_selection", "constraint_feedback"],
        "react_component": "BalanceActGame"
    }
}
```

#### **Step 2: Add Pydantic Schemas for Each**

File: `backend/app/agents/schemas/algorithm_blueprints.py` (new)

```python
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field

class PathfinderBlueprint(BaseModel):
    templateType: Literal["PATHFINDER"]
    algorithmType: Literal["bfs", "dfs"]
    title: str
    narrativeIntro: str
    
    graph: Dict[str, Any] = Field(
        description="Graph structure: nodes, edges, start, goal",
        example={
            "nodes": [0, 1, 2, 3],
            "edges": [[0, 1], [0, 2], [1, 3], [2, 3]],
            "start_node": 0,
            "goal_node": 3
        }
    )
    
    dataStructuresVisible: List[str] = Field(
        default=["queue", "visited", "unvisited"],
        description="Which runtime structures to display"
    )
    
    syncMeterConfig: Dict[str, Any] = Field(
        default={
            "violation_penalty": 0.2,
            "violation_message": "That violates BFS order"
        }
    )
    
    tasks: List[Dict[str, Any]] = Field(
        description="Interaction tasks for player"
    )

# Similar for MergeMasterBlueprint, GraphArchitectBlueprint, BalanceActBlueprint
```

---

## PHASE 3: IMPLEMENTATION ROADMAP

### 3.1 Backend Changes (New Endpoints & Logic Controllers)

#### **New RouteEndpoint: `/api/generate-algorithm`**

File: `backend/app/routes/algorithm_generator.py` (new)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()

class AlgorithmGameRequest(BaseModel):
    algorithm_type: str  # "bfs", "dfs", "merge_sort", "dijkstra", "knapsack"
    problem_input: Dict[str, Any]  # Graph, array, capacity, etc.
    difficulty: str  # "beginner" to "expert"
    bloom_level: Optional[str] = "understand"
    
@router.post("/generate-algorithm")
async def generate_algorithm_game(request: AlgorithmGameRequest):
    """
    Generate an algorithm game from problem specification.
    
    Flow:
    1. Validate algorithm type and problem input
    2. Route to appropriate game planner
    3. Generate algorithm-specific blueprint
    4. Validate blueprint
    5. Return JSON for rendering
    """
    process_id = generate_uuid()
    
    # Future: Use LangGraph to orchestrate:
    # - AlgorithmInputValidator (check graph/array/capacity valid)
    # - AlgorithmGamePlanner (create game plan with tasks)
    # - AlgorithmBlueprintGenerator (create JSON blueprint)
    # - AlgorithmValidator (validate correctness conditions)
    
    return {
        "process_id": process_id,
        "status": "processing",
        "estimated_seconds": 15
    }
```

#### **New Agent: `algorithm_game_planner.py`**

Analogous to existing `game_planner.py`, but for algorithms.

```python
async def algorithm_game_planner(
    algorithm_type: str,
    problem_input: Dict[str, Any],
    difficulty: str,
    bloom_level: str
) -> Dict[str, Any]:
    """
    Create a game plan for an algorithm game.
    
    Returns:
    {
      "game_title": "BFS Adventure",
      "learning_objectives": ["Apply BFS to find shortest path", ...],
      "phases": [
        {
          "name": "Explore the Graph",
          "instruction": "Visit each node in BFS order",
          "mechanical_constraints": {
            "must_follow_queue_order": True,
            "penalty_for_violation": "Sync meter -20%"
          }
        }
      ],
      "success_criteria": {
        "must_reach_goal": True,
        "must_follow_algorithm_order": True,
        "optional_bonus": "Reach in minimum moves"
      },
      "scoring": {
        "per_correct_step": 10,
        "per_violation": -5,
        "bonus_perfect": 50
      }
    }
    """
```

#### **New Validator: `algorithm_blueprint_validator.py`**

Checks algorithm-specific correctness:

```python
async def validate_algorithm_blueprint(
    blueprint: Dict[str, Any],
    problem_input: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate an algorithm blueprint.
    
    Checks:
    1. Graph/data structure well-formed
    2. Start/goal nodes exist in graph
    3. Success conditions are achievable
    4. Task sequence is logical
    5. Scoring strategy is sensible
    
    Returns:
    {
      "valid": True/False,
      "errors": [...],
      "warnings": [...],
      "expected_solution": {
        "visited_order": [0, 1, 2, 3],
        "final_score_optimal": 100
      }
    }
    """
```

#### **State Shape Addition: Algorithm State Container**

File: `backend/app/agents/state.py` (extend existing AgentState)

```python
class AlgorithmGameState(BaseModel):
    # Existing fields (template_type, question_text, etc.)
    # ... all existing fields ...
    
    # NEW: Algorithm-specific fields
    algorithm_type: Optional[str] = None  # "bfs", "dijkstra", etc.
    problem_input: Optional[Dict[str, Any]] = None  # Graph, array, etc.
    algorithm_game_plan: Optional[Dict[str, Any]] = None
    expected_solution: Optional[Dict[str, Any]] = None  # For validation
    algorithm_blueprint: Optional[Dict[str, Any]] = None
```

---

### 3.2 Frontend Changes (Algorithm Game Renderer Components)

#### **New Component: `frontend/src/components/templates/PathfinderGame/index.tsx`**

Example skeleton (detailed implementation in Phase 4):

```typescript
import React, { useState } from 'react';
import { PathfinderBlueprint } from '@/types/gameBlueprint';

interface PathfinderGameProps {
  blueprint: PathfinderBlueprint;
  onScoreChange?: (score: number) => void;
  onGameComplete?: (finalScore: number) => void;
}

export default function PathfinderGame({ blueprint, onScoreChange, onGameComplete }: PathfinderGameProps) {
  const [gameState, setGameState] = useState({
    queue: [] as number[],
    visited: [] as number[],
    currentNode: null as number | null,
    syncMeter: 100,  // 0-100 percentage
    score: 0
  });

  const handleNodeClick = (nodeId: number) => {
    // Validate: Is this node at the front of the queue?
    const queueFront = gameState.queue[0];
    
    if (nodeId === queueFront) {
      // Correct move
      setGameState(prev => ({
        ...prev,
        visited: [...prev.visited, nodeId],
        queue: prev.queue.slice(1),
        score: prev.score + 10
      }));
    } else {
      // Incorrect move - violates BFS order
      setGameState(prev => ({
        ...prev,
        syncMeter: Math.max(0, prev.syncMeter - 20),
        score: Math.max(0, prev.score - 5)
      }));
    }
  };

  // Render queue visualization, visited nodes, graph, task text, feedback
  return (
    <div className="pathfinder-game">
      <DataStructureVisualizer queue={gameState.queue} visited={gameState.visited} />
      <GraphCanvas graph={blueprint.graph} onNodeClick={handleNodeClick} />
      <SyncMeter value={gameState.syncMeter} />
      <ScoreDisplay score={gameState.score} />
    </div>
  );
}
```

#### **New Subcomponents**

Create in `frontend/src/components/enhanced/algorithm/`:

1. **DataStructureVisualizer.tsx** — Render queue, stack, visited array, priority queue
2. **GraphCanvas.tsx** — SVG graph with node colors (unvisited, visited, boundary)
3. **SyncMeter.tsx** — Bar showing BFS/DFS order compliance (0-100%)
4. **AlgorithmStateTracer.tsx** — Show current state vs. expected state
5. **MergeVisualizerLevels.tsx** — Recursion level tabs for merge sort
6. **EdgeSelector.tsx** — Prim/Dijkstra edge selection with boundary highlighting
7. **KnapsackPackDisplay.tsx** — Visual backpack with item cards and capacity indicator

#### **Type Definitions Addition**

File: `frontend/src/types/gameBlueprint.ts` (extend)

```typescript
// Add to union of blueprint types:

export interface PathfinderBlueprint {
  templateType: "PATHFINDER";
  algorithmType: "bfs" | "dfs";
  title: string;
  narrativeIntro: string;
  graph: {
    nodes: number[];
    edges: [number, number][];
    start_node: number;
    goal_node: number;
  };
  dataStructuresVisible: string[];
  syncMeterConfig: {
    violation_penalty: number;
    violation_message: string;
  };
  tasks: Array<{
    id: string;
    instruction: string;
    type: "navigation" | "verification";
  }>;
}

export interface MergeMasterBlueprint {
  templateType: "MERGE_MASTER";
  algorithm: "merge_sort";
  title: string;
  narrativeIntro: string;
  array: number[];
  recursion_levels: number;
  tasks: Array<{
    level: number;
    left: number[];
    right: number[];
    instruction: string;
  }>;
}

export interface GraphArchitectBlueprint {
  templateType: "GRAPH_ARCHITECT";
  algorithm: "prim_mst" | "dijkstra";
  title: string;
  narrativeIntro: string;
  graph: {
    nodes: string[];
    edges: Array<{ from: string; to: string; weight: number }>;
  };
  dataStructuresVisible: string[];
}

export interface BalanceActBlueprint {
  templateType: "BALANCE_ACT";
  algorithm: "knapsack_0_1";
  title: string;
  capacitor: number;  // Typo? Should be "capacity"
  items: Array<{
    id: string;
    weight: number;
    value: number;
  }>;
  tasks: Array<{
    id: string;
    instruction: string;
  }>;
}

// Update GameBlueprint union:
export type GameBlueprint = 
  | LabelDiagramBlueprint
  | SequenceBuilderBlueprint
  | BucketSortBlueprint
  | MatchPairsBlueprint
  | PathfinderBlueprint       // NEW
  | MergeMasterBlueprint      // NEW
  | GraphArchitectBlueprint   // NEW
  | BalanceActBlueprint;      // NEW
```

#### **Game Engine Router Update**

File: `frontend/src/components/GameEngine.tsx` (extend switch statement)

```typescript
export default function GameEngine({ blueprint, ...props }) {
  switch(blueprint.templateType) {
    case "LABEL_DIAGRAM":
      return <LabelDiagramGame {...props} />;
    case "SEQUENCE_BUILDER":
      return <SequenceBuilderGame {...props} />;
    
    // NEW ALGORITHMS:
    case "PATHFINDER":
      return <PathfinderGame {...props} />;
    case "MERGE_MASTER":
      return <MergeMasterGame {...props} />;
    case "GRAPH_ARCHITECT":
      return <GraphArchitectGame {...props} />;
    case "BALANCE_ACT":
      return <BalanceActGame {...props} />;
    
    default:
      return <UnsupportedTemplate templateType={blueprint.templateType} />;
  }
}
```

---

## PHASE 4: SUCCESS & LOGIC VERIFICATION

### 4.1 Define Success Criteria Per Algorithm

Each game must **programmatically verify** that the user understands the algorithm, not just that they reached the goal.

#### **BFS/DFS (PATHFINDER)**

**Success Condition 1: Reached Goal**
```json
{
  "test": "goal_reached",
  "logic": "finalState.visited includes goal_node",
  "proof": "Physical proof: user visited goal node"
}
```

**Success Condition 2: Followed Queue/Stack Order (CRITICAL)**
```json
{
  "test": "maintained_bfs_or_dfs_order",
  "logic": "visitedOrder == expectedBFSOrder (for BFS) || visitedOrder matches DFS backtracking pattern",
  "proof": "If violated, syncMeter < 100. Student cannot reach goal with high score without following order.",
  "implementation": [
    "Track every node click",
    "Compare against BFS order: queue processed FIFO",
    "Compare against DFS order: stack processed LIFO, backtrack on dead ends",
    "Score penalty: -5 per violation"
  ]
}
```

**Success Condition 3: Efficiency (Bonus)**
```json
{
  "test": "path_optimality",
  "logic": "number_of_steps_taken == shortest_bfs_path_length",
  "proof": "BFS guarantees shortest path; if player took longer, they didn't follow it",
  "bonus": "+20 points"
}
```

#### **Merge Sort (MERGE_MASTER)**

**Success Condition 1: Completed All Merges**
```json
{
  "test": "all_merges_complete",
  "logic": "sortedArray == expectedSortedArray",
  "proof": "Result is correctly sorted"
}
```

**Success Condition 2: Followed Divide-and-Conquer (CRITICAL)**
```json
{
  "test": "maintained_recursion_levels",
  "logic": "Each merge was between two sublists of the same recursion level",
  "proof": "Student understands divide into size-1, then merge upward",
  "implementation": [
    "On each merge, verify: left_sublist length == right_sublist length",
    "Verify: both come from same level in recursion tree",
    "Violation: Cannot merge out-of-order levels; game blocks with 'These are different levels'"
  ]
}
```

**Success Condition 3: Swap Efficiency**
```json
{
  "test": "swap_count_optimal",
  "logic": "swap_count == n * log(n) (approximately)",
  "proof": "O(n log n) vs O(n²) is palpable as time difference",
  "measurement": "Bonus points if completed in < 2.0x optimal time"
}
```

#### **Dijkstra/Prim (GRAPH_ARCHITECT)**

**Success Condition 1: All Nodes Connected**
```json
{
  "test": "all_nodes_reachable",
  "logic": "Tree has n-1 edges, all nodes in tree, no disconnected components",
  "proof": "Physical proof: can traverse from any node to any other"
}
```

**Success Condition 2: Followed Greedy Selection (CRITICAL)**
```json
{
  "test": "greedy_edge_selection",
  "logic": "At each step, player selected minimum-cost edge from boundary",
  "proof": "If user selected suboptimal edges, total_cost > optimal_cost",
  "implementation": [
    "Track each edge selection",
    "Compute: optimal_cost for MST using Prim's algorithm",
    "Compute: user_cost from their edge selections",
    "Score: max_points * (optimal_cost / user_cost), capped at 100",
    "If user_cost == optimal_cost: Perfect score + bonus"
  ]
}
```

**Success Condition 3 (Dijkstra variant): Shortest Path**
```json
{
  "test": "shortest_total_distance",
  "logic": "sumOfDistances(userPath) == sumOfDistances(optimalPath)",
  "proof": "Greedy selection of nearest unvisited guarantees shortest paths"
}
```

#### **Knapsack (BALANCE_ACT)**

**Success Condition 1: Respects Capacity**
```json
{
  "test": "total_weight <= capacity",
  "logic": "weight(selectedItems) <= capacity",
  "proof": "Cannot exceed backpack limit; prevents illegal state"
}
```

**Success Condition 2: Optimization (CRITICAL)**
```json
{
  "test": "achieved_maximum_value",
  "logic": "totalValue(userSelection) == totalValue(optimalSelection)",
  "proof": "User understands optimal subproblem structure",
  "scoring": {
    "points_awarded": 100 * (userValue / optimalValue),
    "capped_at": 100,
    "bonus_for_perfect": 50,
    "feedback": {
      "perfect": "You found the optimal packing! You understand subproblem structure.",
      "good_80plus": "Good value! Could you improve by reconsidering item pairs?",
      "suboptimal": `You packed value ${userValue}. Optimal is ${optimalValue}. Hint: Re-examine items X and Y.`
    }
  }
}
```

**Success Condition 3: Subproblem Recognition (Advanced)**
```json
{
  "test": "recognizes_subproblem_structure",
  "logic": "If players achieve optimal on first attempt, they likely recognize DP",
  "bonus": "+30 points for perfect first attempt"
}
```

---

### 4.2 Implementation Pattern: Algorithmic Validation in Blueprint

Every algorithm blueprint must include an **expected solution** that the frontend can validate against.

#### **Pattern: Validation Payload in Blueprint**

File: `backend/app/services/algorithm_validation_service.py` (new)

```python
async def compute_expected_solution(
    algorithm_type: str,
    problem_input: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute the ground-truth solution for an algorithm problem.
    
    This is used by the blueprint generator to attach to the blueprint
    so the frontend can validate user moves.
    """
    if algorithm_type == "bfs":
        return {
            "visited_order": bfs(problem_input["graph"], problem_input["start"]),
            "distances": compute_distances(problem_input["graph"], problem_input["start"]),
            "optimal_moves": len(nodes)  # BFS visits each node exactly once
        }
    elif algorithm_type == "merge_sort":
        return {
            "sorted_array": sorted(problem_input["array"]),
            "recursion_levels": compute_depth(len(problem_input["array"])),
            "expected_comparisons": compute_merge_sort_complexity(problem_input["array"])
        }
    elif algorithm_type == "prim_mst":
        return {
            "optimal_edges": prim_algorithm(problem_input["graph"]),
            "optimal_cost": sum(e.weight for e in prim_algorithm(...)),
            "greedy_selections": len(nodes) - 1
        }
    elif algorithm_type == "knapsack":
        return {
            "optimal_items": knapsack_0_1(problem_input["items"], problem_input["capacity"]),
            "optimal_value": sum(item.value for item in optimal_items),
            "item_combinations_to_try": generate_test_combinations(...)
        }
```

#### **Blueprint Attachment Pattern**

In `blueprint_generator.py` (algorithm branch):

```python
async def generate_algorithm_blueprint(
    algorithm_type: str,
    problem_input: Dict[str, Any],
    game_plan: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate and validate an algorithm blueprint."""
    
    # 1. Compute expected solution (ground truth)
    expected_solution = await compute_expected_solution(algorithm_type, problem_input)
    
    # 2. Create blueprint scaffold
    blueprint = {
        "templateType": template_name,
        "algorithm_type": algorithm_type,
        "problem_input": problem_input,
        "game_plan": game_plan,
        "expected_solution": expected_solution,  # Attached for frontend validation
        "validation_config": {
            "success_criteria": [
                {"name": "reached_goal", "required": True},
                {"name": "maintained_algorithm_order", "required": True},
                {"name": "optimization_bonus", "required": False}
            ],
            "penalties": {
                "wrong_move": -5,
                "out_of_order": -10,
                "capacity_exceeded": -50
            }
        }
    }
    
    # 3. Validate blueprint
    validation = await validate_algorithm_blueprint(blueprint, expected_solution)
    
    if not validation["valid"]:
        # Retry or raise
        pass
    
    return blueprint
```

---

## PHASE 5: DETAILED BACKEND & FRONTEND SPECIFICATIONS

### 5.1 New Backend Agents Specification

#### **Agent: `algorithm_input_validator`**

```python
class AlgorithmInputValidatorAgent:
    """Validates algorithm problem input."""
    
    async def execute(self, state: AlgorithmGameState) -> dict:
        """
        Validate:
        1. Graph is well-formed (no orphan nodes, no duplicate edges)
        2. Start/goal exist
        3. Graph is solvable (goal reachable from start)
        4. Array is reasonable length (not too large)
        5. Capacity is positive
        6. Items are well-formed
        """
```

#### **Agent: `algorithm_game_planner`**

```python
class AlgorithmGamePlannerAgent:
    """Creates a game plan specific to algorithm type."""
    
    async def execute(self, state: AlgorithmGameState) -> dict:
        """
        Outputs:
        {
          "title": "BFS Pathfinder Quest",
          "learning_objectives": [...],
          "phases": [...],
          "mechanical_constraints": {...},
          "success_criteria": {...},
          "scoring": {...}
        }
        """
```

#### **Agent: `algorithm_blueprint_generator`**

```python
class AlgorithmBlueprintGeneratorAgent:
    """Generates blueprint for algorithm game."""
    
    async def execute(self, state: AlgorithmGameState) -> dict:
        """
        Outputs:
        {
          "templateType": "PATHFINDER",
          "algorithm_type": "bfs",
          "graph": {...},
          "tasks": [...],
          "expected_solution": {...},  # Ground truth
          "validation_config": {...}
        }
        """
```

#### **Agent: `algorithm_solution_computer`**

```python
class AlgorithmSolutionComputerAgent:
    """Compute ground-truth solution."""
    
    async def execute(self, state: AlgorithmGameState) -> dict:
        """
        Runs the actual algorithm (BFS, Merge Sort, Prim, Knapsack)
        to compute expected output.
        
        Outputs:
        {
          "visited_order": [...],
          "optimal_value": 100,
          "step_by_step": [...],  # For hints
          "expected_metrics": {...}
        }
        """
```

#### **Agent: `algorithm_blueprint_validator`**

```python
class AlgorithmBlueprintValidatorAgent:
    """Validates that blueprint is solvable and well-formed."""
    
    async def execute(self, state: AlgorithmGameState) -> dict:
        """
        Validates:
        1. Blueprint schema matches template
        2. Expected solution is correct
        3. Success conditions are achievable
        4. Scoring is sensible
        5. No impossible tasks
        """
```

### 5.2 New Frontend Hooks & State Management

#### **Hook: `useAlgorithmGameState` (Base Hook)**

```typescript
export function useAlgorithmGameState(blueprint: AlgorithmBlueprint) {
  const [state, setState] = useState<AlgorithmGameStateType>({
    currentMove: 0,
    visited: [],
    current: null,
    queue: [],
    syncMeter: 100,
    score: 0,
    violations: 0,
    completed: false,
    finalScore: 0
  });

  const handleMove = (action: AlgorithmAction) => {
    // Validate against expectedSolution
    const isValid = validateMove(action, blueprint.expected_solution);
    
    if (isValid) {
      // Update state correctly
      setState(prev => updateState(prev, action));
    } else {
      // Penalize
      setState(prev => ({
        ...prev,
        syncMeter: prev.syncMeter - blueprint.validation_config.penalties.wrong_move,
        violations: prev.violations + 1
      }));
    }
  };

  return { state, handleMove, metrics: computeMetrics(state, blueprint) };
}
```

---

## PHASE 6: INTEGRATION CHECKLIST

### Backend Checklist
- [ ] Create `backend/app/routes/algorithm_generator.py`
- [ ] Create `backend/app/agents/algorithm_game_planner.py`
- [ ] Create `backend/app/agents/schemas/algorithm_blueprints.py`
- [ ] Create `backend/app/services/algorithm_validation_service.py`
- [ ] Add algorithm routes to `backend/app/main.py`
- [ ] Update `backend/app/agents/state.py` with AlgorithmGameState
- [ ] Create algorithm graph in `backend/app/agents/algorithm_graph.py`
- [ ] Add algorithm templates to registry
- [ ] Create algorithm solution computers (BFS, Merge, Dijkstra, Knapsack)
- [ ] Database: Add `algorithm_solutions` table (optional, for caching ground truth)

### Frontend Checklist
- [ ] Create `frontend/src/components/templates/PathfinderGame/index.tsx`
- [ ] Create `frontend/src/components/templates/MergeMasterGame/index.tsx`
- [ ] Create `frontend/src/components/templates/GraphArchitectGame/index.tsx`
- [ ] Create `frontend/src/components/templates/BalanceActGame/index.tsx`
- [ ] Create `frontend/src/components/enhanced/algorithm/DataStructureVisualizer.tsx`
- [ ] Create `frontend/src/components/enhanced/algorithm/GraphCanvas.tsx`
- [ ] Create algorithm-specific hooks in `frontend/src/hooks/`
- [ ] Update `frontend/src/types/gameBlueprint.ts` with algorithm types
- [ ] Update `frontend/src/components/GameEngine.tsx` with algorithm routes
- [ ] Update game rendering pipeline to handle algorithm blueprints

### Testing Checklist
- [ ] Unit tests for algorithm validators
- [ ] Integration test: BFS problem → blueprint → game → validation
- [ ] E2E test: Generate pathfinder game, play to completion, verify scoring
- [ ] Edge cases: Single-node graph, single-item knapsack, already-sorted array
- [ ] Accessibility: Keyboard navigation in pathfinder, screen reader for data structures

### Documentation Checklist
- [ ] Add algorithm template specs to README
- [ ] Create algorithm game creation guide
- [ ] Document validation mechanics per algorithm
- [ ] Update architecture docs with algorithm flow

---

## PHASE 7: HARDCODING FIXES (Enablement)

To **fully enable** algorithm games, resolve these hardcoding issues:

### Critical Fixes

1. **Scoring System** (Frontend): Move from hardcoded `+10` to blueprint-driven `scoringStrategy`
   - Files: `useLabelDiagramState.ts`, `ResultsPanel.tsx`
   - Impact: Allows per-template, per-difficulty customization

2. **Feedback Thresholds** (Frontend): Move from hardcoded 70%/100% to configurable
   - Files: `ResultsPanel.tsx`
   - Impact: Algorithm games can use custom thresholds

3. **Validator Mappings** (Backend): Move hardcoded Bloom's levels, difficulty multipliers to config
   - Files: `game_planner.py`, `interaction_designer.py`
   - Impact: New algorithms don't force predefined difficulty curves

4. **Template Fallbacks** (Backend): Remove hardcoded "PARAMETER_PLAYGROUND" fallback
   - Files: `router.py`, `blueprint_generator.py`
   - Impact: System fails explicitly instead of silently producing wrong game type

5. **Animation Config** (Backend + Frontend): Extract hardcoded animation timings to registry
   - Files: `asset_planner.py`, `interaction_designer.tsx`
   - Impact: Algorithm games can define custom animations

---

## SUMMARY & NEXT STEPS

### What This Report Delivers

1. **Current State Assessment**: Identified 5 pipeline bottlenecks that block algorithm games
2. **Algorithm Mapping**: Translated 4 algorithm families → 4 game mechanics with mechanical fidelity
3. **Schema Design**: Blueprint structures for Pathfinder, MergeMaster, GraphArchitect, BalanceAct
4. **Backend Roadmap**: 5 new agents, new validation service, problem input routing
5. **Frontend Roadmap**: 4 new game components, 6+ subcomponents, algorithm-specific hooks
6. **Success Verification**: Metrics for each algorithm proving student understanding
7. **Hardcoding Fixes**: 5 critical enablers to move from hardcoded defaults to config-driven

### Recommended Implementation Order

**Sprint 1** (Weeks 1-2): Foundation
- Create algorithm blueprint schemas
- Create algorithm game planner agent
- Create algorithm solution computer service
- Update database schema

**Sprint 2** (Weeks 3-4): Pathfinder (Simplest)
- Implement `PathfinderGame` React component
- Create `useAlgorithmGameState` hook
- Queue/Stack visualization subcomponents
- End-to-end test: Problem → Blueprint → Game → Validation

**Sprint 3** (Weeks 5-6): BalanceAct (Straightforward UX)
- Implement `BalanceActGame` React component
- Knapsack solver + solution computer
- Capacity feedback + item selection logic
- Scoring: value optimization tracking

**Sprint 4** (Weeks 7-8): MergeMaster (Visual Complexity)
- Implement `MergeMasterGame` React component
- Recursion level visualization
- Merge decision UI
- Swap counting + efficiency tracking

**Sprint 5** (Weeks 9-10): GraphArchitect (Constraint Complexity)
- Implement `GraphArchitectGame` React component
- Edge selector with boundary highlighting
- Greedy constraint enforcement
- MST/shortest path computation + scoring

**Sprint 6** (Weeks 11-12): Hardcoding Fixes + Polish
- Refactor scoring system to blueprint-driven
- Refactor animation timings
- Remove template fallbacks
- Accessibility audit & fixes

---

**This integration roadmap transforms GamED.AI v2 from a diagram labeling tool into an algorithmic problem-solving learning platform.**

