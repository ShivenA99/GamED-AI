"""Prompt template for StateTracer scene content generation."""

import json


def build_state_tracer_prompt(scene_plan: dict, dk: dict) -> str:
    """Build LLM prompt for generating StateTracer content."""
    algorithm_name = dk.get("algorithm_name", "Algorithm")
    pseudocode = dk.get("pseudocode", "")
    python_impl = dk.get("language_implementations", {}).get("python", "")
    examples = dk.get("example_inputs", [])
    ds_used = dk.get("data_structures_used", ["array"])
    config_hints = scene_plan.get("config_hints", {})

    ds_type = config_hints.get("data_structure", ds_used[0] if ds_used else "array")
    pred_type = config_hints.get("prediction_type", "value")
    num_steps = config_hints.get("num_steps", 8)

    example_section = ""
    if examples:
        example_section = f"\n## Example inputs/outputs:\n{json.dumps(examples[:3], indent=2)}\n"

    return f"""You are an expert algorithm educator. Generate a complete StateTracer game scene.

## Algorithm: {algorithm_name}
## Primary Data Structure: {ds_type}
## Implementation:
```python
{python_impl or pseudocode or f'# No implementation provided for {algorithm_name}'}
```
{example_section}
## Scene: {scene_plan.get('title', 'Trace the Algorithm')}
## Learning Goal: {scene_plan.get('learning_goal', '')}

Generate a JSON StateTracer scene with {num_steps} execution steps.

Return JSON:
{{
    "algorithmName": "{algorithm_name}",
    "algorithmDescription": "<1-2 sentence description>",
    "narrativeIntro": "<engaging intro for the student>",
    "code": "<REAL working {algorithm_name} code in Python, 10-30 lines>",
    "language": "python",
    "steps": [
        {{
            "stepNumber": 1,
            "codeLine": <line number being executed (1-indexed)>,
            "description": "<what happens at this step>",
            "variables": {{"var_name": "value", ...}},
            "changedVariables": ["var_name"],
            "dataStructure": {{
                "type": "{ds_type}",
                // For array: "elements": [1,3,5,7,9], "highlights": [{{"index": 2, "color": "active"}}], "sortedIndices": []
                // For graph: "nodes": [{{"id":"A","label":"A","x":0,"y":0,"state":"unvisited"}}], "edges": [{{"from":"A","to":"B","state":"default"}}]
                // For tree: "nodes": [{{"id":"1","value":5,"left":"2","right":"3","state":"default"}}], "root": "1"
                // For dp_table: "cells": [[{{"value":null,"state":"empty"}}]], "rowLabels":[], "colLabels":[], "activeCell": [0,0]
                // For stack: "items": [{{"id":"s1","value":"(","state":"default"}}]
                // For linked_list: "nodes": [{{"id":"n1","value":1,"next":"n2","state":"default"}}], "head": "n1"
                // For heap: "elements": [1,3,5], "heapType": "min", "highlights": []
                // For hash_map: "buckets": [[{{"key":"a","value":1}}]], "capacity": 8, "highlights": []
            }},
            "prediction": {{
                // Use ONE of these prediction types:
                // value: {{"type":"value","prompt":"What is the value of X?","correctValue":"5","acceptableValues":["5"],"placeholder":"Enter value"}}
                // arrangement: {{"type":"arrangement","prompt":"What does the array look like after this step?","elements":[1,3,5,7,9],"correctArrangement":[1,3,5,7,9]}}
                // multiple_choice: {{"type":"multiple_choice","prompt":"Which element is compared next?","options":[{{"id":"a","label":"3"}},{{"id":"b","label":"5"}},{{"id":"c","label":"7"}}],"correctId":"b"}}
                // multi_select: {{"type":"multi_select","prompt":"Which nodes are in the frontier?","options":[{{"id":"a","label":"A"}},{{"id":"b","label":"B"}}],"correctIds":["a","b"]}}
                // null for auto-advance steps (no prediction needed)
            }},
            "explanation": "<why this step happens>",
            "hints": ["<nudge hint>", "<clue hint>", "<answer hint>"]
        }}
    ],
    "scoringConfig": {{
        "basePoints": 100,
        "streakThresholds": [{{"min":0,"multiplier":1}},{{"min":3,"multiplier":1.5}},{{"min":5,"multiplier":2}},{{"min":8,"multiplier":3}}],
        "hintPenalties": [0.1, 0.2, 0.3],
        "perfectRunBonus": 0.2
    }}
}}

Rules:
- Code must be REAL, WORKING {algorithm_name} code (not pseudocode)
- Each step must trace actual execution with correct variable values
- Data structure state must reflect the ACTUAL state at each step
- Include exactly {num_steps} steps with 60-80% requiring predictions
- Predictions should test understanding, not just memorization
- Hints should be progressively more helpful (nudge → clue → answer)
- Make 1-2 steps auto-advance (prediction: null) for setup/initialization
- dataStructure.type MUST be one of: array, graph, tree, dp_table, stack, linked_list, heap, hash_map, custom
- prediction.type MUST be one of: value, arrangement, multiple_choice, multi_select. Use null for auto-advance steps.
- hints MUST be an array of EXACTLY 3 strings [category_hint, approach_hint, specific_hint]
- elements in array type MUST be numbers (integers or floats), NOT strings
- codeLine values MUST be 1-indexed (first line = 1)
- CRITICAL: Return ONLY the JSON object. No markdown, no explanation, no code fences.
- Keep string values concise. Do not pad descriptions unnecessarily.
"""
