"""Algorithm game type literals and enums."""

from typing import Literal

ALGORITHM_GAME_TYPE = Literal[
    "state_tracer",
    "bug_hunter",
    "algorithm_builder",
    "complexity_analyzer",
    "constraint_puzzle",
]

ALGORITHM_CATEGORY = Literal[
    "sorting",
    "searching",
    "graph",
    "dynamic_programming",
    "string",
    "tree",
    "greedy",
    "backtracking",
    "divide_and_conquer",
    "linked_list",
    "stack_queue",
    "hashing",
    "math",
]

VISUALIZATION_TYPE = Literal[
    "data_structure",
    "flowchart",
    "comparison_chart",
    "board_layout",
    "none",
]

COMPLEXITY_DIMENSION = Literal["time", "space", "both"]
CASE_VARIANT = Literal["worst_only", "best_worst_avg"]

# Score defaults per game type
GAME_TYPE_DEFAULT_SCORES: dict[str, int] = {
    "state_tracer": 800,       # ~100 pts/step × 8 steps
    "bug_hunter": 600,         # ~200 pts/round × 3 rounds
    "algorithm_builder": 500,  # per-block scoring
    "complexity_analyzer": 300, # ~100 pts/challenge × 3
    "constraint_puzzle": 400,  # optimality-based
}
