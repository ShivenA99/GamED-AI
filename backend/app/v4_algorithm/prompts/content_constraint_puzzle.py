"""Prompt template for ConstraintPuzzle scene content generation."""

import json


def build_constraint_puzzle_prompt(scene_plan: dict, dk: dict) -> str:
    """Build LLM prompt for generating ConstraintPuzzle content."""
    algorithm_name = dk.get("algorithm_name", "Algorithm")
    algorithm_category = dk.get("algorithm_category", "")
    config_hints = scene_plan.get("config_hints", {})

    puzzle_type = config_hints.get("puzzle_type", "")
    board_type = config_hints.get("board_type", "item_selection")

    # Determine best puzzle type from algorithm
    if not puzzle_type:
        category_to_puzzle = {
            "dynamic_programming": "item_selection",
            "greedy": "item_selection",
            "backtracking": "grid_placement",
            "graph": "graph_interaction",
            "sorting": "sequence_building",
        }
        board_type = category_to_puzzle.get(algorithm_category, "item_selection")

    return f"""You are an expert at creating constraint optimization puzzles that teach algorithmic thinking.

## Algorithm: {algorithm_name}
## Category: {algorithm_category}

## Scene: {scene_plan.get('title', 'Solve the Puzzle')}
## Learning Goal: {scene_plan.get('learning_goal', '')}

Design a constraint puzzle that mirrors the problem {algorithm_name} solves.
Students solve it manually, then learn how the algorithm does it optimally.

Return JSON:
{{
    "title": "<puzzle title>",
    "narrative": "<story context for the puzzle>",
    "rules": ["<rule 1>", "<rule 2>", "<rule 3>"],
    "objective": "<what the student is trying to optimize/achieve>",
    "boardConfig": {{
        "boardType": "{board_type}",
        "items": [
            {{
                "id": "item_1",
                "label": "<item display name>",
                "properties": {{"weight": 5, "value": 10}},
                "icon": "<emoji or icon name>"
            }}
        ],
        "extra": {{
            // For item_selection: "capacity": 15
            // For grid_placement: "gridSize": 8
            // For multiset_building: "targetAmount": 36, "denominations": [1, 5, 10, 25]
            // For graph_interaction: "nodes": [...], "edges": [...]
            // For sequence_building: "items": [...]
        }},
        "showConstraintsVisually": true,
        "allowUndo": true,
        "capacity": <if applicable>,
        "gridSize": <if applicable>,
        "targetAmount": <if applicable>,
        "denominations": <if applicable>
    }},
    "constraints": [
        // Each constraint has "type", "description", and type-specific fields at TOP LEVEL (NOT nested in "params"):
        // Example: {{"type": "capacity", "property": "weight", "max": 15, "description": "Total weight cannot exceed 15kg"}}
        // See CONSTRAINT TYPE REFERENCE below for all valid types and their required fields.
    ],
    "scoringConfig": {{
        "method": "<ratio|count|binary|sum_property|inverse_count|weighted_sum>",
        "maxPoints": 400,
        // method-specific fields at TOP LEVEL (NOT nested in "params"):
        // ratio: requires "total": <number>
        // count: no extra fields
        // binary: requires "successValue": <number>
        // sum_property: requires "property": "<string>"
        // inverse_count: requires "numerator": <number>
        // weighted_sum: requires "valueProperty": "<string>", "weightProperty": "<string>"
    }},
    "optimalValue": <the best possible score/value>,
    "optimalSolutionDescription": "<describe the optimal solution>",
    "algorithmName": "{algorithm_name}",
    "algorithmExplanation": "<explain how {algorithm_name} solves this optimally, 2-4 sentences>",
    "hints": [
        "<general strategy hint>",
        "<specific approach hint>",
        "<near-solution hint>"
    ]
}}

## CONSTRAINT TYPE REFERENCE — Use ONLY these 9 types:
Each constraint object has "type", "description", and type-specific fields at the TOP LEVEL.
Do NOT nest fields inside a "params" object.

1. "capacity" — requires: "property": "<string>", "max": <number>
   Example: {{"type": "capacity", "property": "weight", "max": 15, "description": "Total weight cannot exceed 15kg"}}
2. "exact_target" — requires: "property": "<string>", "target": <number>
   Example: {{"type": "exact_target", "property": "total", "target": 100, "description": "Items must sum to exactly 100"}}
3. "no_overlap" — requires: "startProperty": "<string>", "endProperty": "<string>"
   Example: {{"type": "no_overlap", "startProperty": "start", "endProperty": "end", "description": "Time intervals must not overlap"}}
4. "no_conflict" — requires: "conflictRule": "<row_col_diagonal|row_col|adjacent>"
   Example: {{"type": "no_conflict", "conflictRule": "row_col_diagonal", "description": "No two queens can share a row, column, or diagonal"}}
5. "count_exact" — requires: "count": <number>
   Example: {{"type": "count_exact", "count": 5, "description": "Must select exactly 5 items"}}
6. "count_range" — requires at least one of: "min": <number>, "max": <number>
   Example: {{"type": "count_range", "min": 2, "max": 4, "description": "Select between 2 and 4 items"}}
7. "all_different" — requires: "scope": "<neighbors|row|col|all>"
   Example: {{"type": "all_different", "scope": "neighbors", "description": "Adjacent items must be different"}}
8. "all_assigned" — no extra fields required
   Example: {{"type": "all_assigned", "description": "All positions must be filled"}}
9. "connected" — no extra fields required
   Example: {{"type": "connected", "description": "Selected nodes must form a connected path"}}

CRITICAL: Do NOT use any constraint types other than these 9. Do NOT use "params" — put all fields at top level.

## SCORING METHOD REFERENCE — Use ONLY these 6 methods:
- "ratio" — requires "total": <number> at top level (not in params)
- "count" — no extra fields
- "binary" — requires "successValue": <number> at top level
- "sum_property" — requires "property": "<string>" at top level
- "inverse_count" — requires "numerator": <number> at top level
- "weighted_sum" — requires "valueProperty": "<string>", "weightProperty": "<string>" at top level

## BOARD TYPE — boardType MUST be one of: item_selection, grid_placement, multiset_building, graph_interaction, value_assignment, sequence_building

## ITEM FIELD NAMES — Use "label" (NOT "name") for the item display name.

Rules:
- The puzzle must be SOLVABLE by a human (not too complex)
- It should have 5-10 items/elements to work with
- The optimal solution should be non-trivial (not obvious)
- Constraints must be clearly stated in the rules
- The algorithm explanation should connect the puzzle to {algorithm_name}
- For knapsack-like: use realistic items with weight/value tradeoffs
- For scheduling-like: use time intervals with conflicts
- For placement-like: use grid with clear conflict rules
- CRITICAL: Return ONLY the JSON object. No markdown, no explanation, no code fences.
- Keep string values concise. Do not pad descriptions unnecessarily.
"""
