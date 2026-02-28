"""Prompt template for ComplexityAnalyzer scene content generation."""

import json


def build_complexity_analyzer_prompt(scene_plan: dict, dk: dict) -> str:
    """Build LLM prompt for generating ComplexityAnalyzer content."""
    algorithm_name = dk.get("algorithm_name", "Algorithm")
    time_complexity = dk.get("time_complexity", {})
    space_complexity = dk.get("space_complexity", {})
    python_impl = dk.get("language_implementations", {}).get("python", "")
    config_hints = scene_plan.get("config_hints", {})

    num_challenges = config_hints.get("num_challenges", 3)
    complexity_dim = config_hints.get("complexity_dimension", "time")

    return f"""You are an expert at creating complexity analysis challenges for algorithm education.

## Algorithm: {algorithm_name}
## Known Time Complexity: {json.dumps(time_complexity)}
## Known Space Complexity: {json.dumps(space_complexity)}
## Implementation:
```python
{python_impl or f'# {algorithm_name} implementation'}
```

## Scene: {scene_plan.get('title', 'Analyze Complexity')}
## Learning Goal: {scene_plan.get('learning_goal', '')}

Generate {num_challenges} complexity analysis challenges of increasing difficulty.

Return JSON:
{{
    "algorithmName": "{algorithm_name}",
    "algorithmDescription": "<description>",
    "challenges": [
        {{
            "challengeId": "challenge_1",
            "type": "identify_from_code",
            "title": "<challenge title>",
            "description": "<what the student should analyze>",
            "code": "<Python code snippet to analyze, 5-20 lines>",
            "language": "python",
            "growthData": null,
            "codeSections": [
                {{
                    "sectionId": "sec_1",
                    "label": "<section name>",
                    "startLine": 1,
                    "endLine": 5,
                    "complexity": "<O(n)>",
                    "isBottleneck": false
                }}
            ],
            "correctComplexity": "<O(n log n)>",
            "options": ["O(1)", "O(n)", "O(n log n)", "O(n²)"],
            "explanation": "<detailed explanation of why this complexity>",
            "points": 100,
            "hints": ["<hint about the loop structure>", "<hint about nesting>", "<the answer with reasoning>"],
            "complexityDimension": "{complexity_dim}",
            "caseVariant": "worst"
        }},
        {{
            "challengeId": "challenge_2",
            "type": "infer_from_growth",
            "title": "<challenge title>",
            "description": "<analyze the growth pattern>",
            "code": null,
            "language": "python",
            "growthData": {{
                "inputSizes": [10, 100, 1000, 10000],
                "operationCounts": [<matching operation counts for the complexity>]
            }},
            "codeSections": [],
            "correctComplexity": "<O(n log n)>",
            "options": ["O(n)", "O(n log n)", "O(n²)", "O(2^n)"],
            "explanation": "<how to read the growth pattern>",
            "points": 100,
            "hints": ["<hint about the growth rate>", "<hint about the ratio>", "<the answer>"],
            "complexityDimension": "{complexity_dim}",
            "caseVariant": "average"
        }},
        {{
            "challengeId": "challenge_3",
            "type": "find_bottleneck",
            "title": "<challenge title>",
            "description": "<find the performance bottleneck>",
            "code": "<code with clearly marked sections>",
            "language": "python",
            "growthData": null,
            "codeSections": [
                {{
                    "sectionId": "sec_a",
                    "label": "Initialization",
                    "startLine": 1,
                    "endLine": 3,
                    "complexity": "O(n)",
                    "isBottleneck": false
                }},
                {{
                    "sectionId": "sec_b",
                    "label": "Main Loop",
                    "startLine": 4,
                    "endLine": 10,
                    "complexity": "O(n²)",
                    "isBottleneck": true
                }}
            ],
            "correctComplexity": "<overall complexity>",
            "options": ["O(n)", "O(n log n)", "O(n²)", "O(n³)"],
            "explanation": "<why this section is the bottleneck>",
            "points": 150,
            "hints": ["<which section to focus on>", "<how to count iterations>", "<the answer>"],
            "complexityDimension": "{complexity_dim}",
            "caseVariant": "worst"
        }}
    ],
    "complexity_dimension": "{complexity_dim}",
    "case_variants": "worst_only"
}}

Rules:
- Use 3 challenge types: identify_from_code (read code), infer_from_growth (read chart data), find_bottleneck (identify worst section)
- Growth data must have MATHEMATICALLY CORRECT operation counts for the stated complexity
  - O(n): [10, 100, 1000, 10000]
  - O(n log n): [33, 664, 9966, 132877]
  - O(n²): [100, 10000, 1000000, 100000000]
- Code snippets must be REAL code related to {algorithm_name}
- Options should include the correct answer and 3 plausible wrong answers
- Bottleneck challenges need codeSections with correct per-section complexities
- Points should be: 100 (easy), 100 (medium), 150 (hard)
- correctComplexity and ALL options[] values MUST use EXACTLY one of these formats: O(1), O(log n), O(sqrt(n)), O(n), O(n log n), O(n^2), O(n^3), O(2^n), O(n!). Use lowercase 'n' always.
- complexityDimension MUST be one of: time, space, both
- caseVariant MUST be one of: worst, best, average, amortized
- challenge.type MUST be one of: identify_from_code, infer_from_growth, find_bottleneck
- CRITICAL: Return ONLY the JSON object. No markdown, no explanation, no code fences.
- Keep string values concise. Do not pad descriptions unnecessarily.
"""
