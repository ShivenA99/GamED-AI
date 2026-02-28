"""Prompt template for AlgorithmBuilder scene content generation."""

import json


def build_algorithm_builder_prompt(scene_plan: dict, dk: dict) -> str:
    """Build LLM prompt for generating AlgorithmBuilder (Parsons) content."""
    algorithm_name = dk.get("algorithm_name", "Algorithm")
    python_impl = dk.get("language_implementations", {}).get("python", "")
    pseudocode = dk.get("pseudocode", "")
    config_hints = scene_plan.get("config_hints", {})

    num_blocks = config_hints.get("num_blocks", 10)
    include_distractors = config_hints.get("include_distractors", True)

    return f"""You are an expert at creating Parsons problems (code block ordering puzzles) for algorithms.

## Algorithm: {algorithm_name}
## Reference Implementation:
```python
{python_impl or pseudocode or f'# Provide a {algorithm_name} implementation'}
```

## Scene: {scene_plan.get('title', 'Build the Algorithm')}
## Learning Goal: {scene_plan.get('learning_goal', '')}

Generate a Parsons problem where students arrange code blocks in the correct order.

Return JSON:
{{
    "algorithmName": "{algorithm_name}",
    "algorithmDescription": "<1-2 sentence description>",
    "problemDescription": "<what the student needs to build>",
    "language": "python",
    "correct_order": [
        {{
            "id": "block_1",
            "code": "<one line or small chunk of code>",
            "indent_level": <0-7, the correct indentation level>,
            "is_distractor": false,
            "distractor_explanation": "",
            "group_id": ""
        }}
    ],
    "distractors": [
        {{
            "id": "distractor_1",
            "code": "<plausible but wrong code line>",
            "indent_level": 0,
            "is_distractor": true,
            "distractor_explanation": "<why this line doesn't belong>",
            "group_id": ""
        }}
    ],
    "config": {{
        "indentation_matters": true,
        "max_attempts": null,
        "show_line_numbers": true,
        "allow_indent_adjustment": true,
        "indent_px_per_level": 24,
        "max_indent_level": 7
    }},
    "hints": [
        "<hint 1: what's the first step?>",
        "<hint 2: what's the overall structure?>",
        "<hint 3: here's the key insight>"
    ],
    "test_cases": [
        {{
            "id": "test_1",
            "inputDescription": "<test input>",
            "expectedOutput": "<expected result>",
            "explanation": "<why this tests the algorithm>"
        }}
    ]
}}

Rules:
- Include {num_blocks} correct blocks that form the COMPLETE algorithm
- Each block should be ONE logical line of code (not multiple statements)
- indent_level must be CORRECT for Python (0 for top-level, 1 for inside function, 2 for inside loop, etc.)
- {"Include 3-5 distractors (plausible wrong lines)" if include_distractors else "Do not include distractors"}
- Use group_id for INTERCHANGEABLE blocks (e.g., both "i += 1" and "i = i + 1" are valid)
- Blocks that can swap positions without changing correctness should share a group_id
- The blocks should form a WORKING Python function when assembled correctly
- Test cases should verify the assembled function works
- hints MUST be an array of EXACTLY 3 strings [structure_hint, logic_hint, detail_hint]
- CRITICAL: Return ONLY the JSON object. No markdown, no explanation, no code fences.
- Keep string values concise. Do not pad descriptions unnecessarily.
"""
