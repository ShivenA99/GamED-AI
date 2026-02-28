"""Prompt template for BugHunter scene content generation."""

import json


def build_bug_hunter_prompt(scene_plan: dict, dk: dict) -> str:
    """Build LLM prompt for generating BugHunter content."""
    algorithm_name = dk.get("algorithm_name", "Algorithm")
    python_impl = dk.get("language_implementations", {}).get("python", "")
    common_bugs = dk.get("common_bugs", [])
    config_hints = scene_plan.get("config_hints", {})

    num_rounds = config_hints.get("num_rounds", 3)
    fix_mode = config_hints.get("fix_mode", "multiple_choice")

    bugs_section = ""
    if common_bugs:
        bugs_section = f"\n## Known common bugs:\n{json.dumps(common_bugs[:6], indent=2)}\n"

    return f"""You are an expert at creating educational debugging challenges for algorithms.

## Algorithm: {algorithm_name}
## Working Implementation:
```python
{python_impl or f'# Provide a correct {algorithm_name} implementation'}
```
{bugs_section}
## Scene: {scene_plan.get('title', 'Find the Bugs')}
## Learning Goal: {scene_plan.get('learning_goal', '')}

Generate {num_rounds} bug-hunting rounds. Each round has DIFFERENT bugs in the same algorithm.

Return JSON:
{{
    "algorithmName": "{algorithm_name}",
    "algorithmDescription": "<1-2 sentence description>",
    "narrativeIntro": "<engaging intro>",
    "language": "python",
    "rounds": [
        {{
            "roundId": "round_1",
            "title": "<round title describing the bug theme>",
            "buggyCode": "<COMPLETE buggy Python code, 10-30 lines>",
            "correctCode": "<COMPLETE correct Python code>",
            "bugs": [
                {{
                    "bugId": "bug_1",
                    "bugLines": [<line number(s) with the bug, 1-indexed>],
                    "buggyLinesText": ["<the buggy line text>"],
                    "correctLinesText": ["<the correct line text>"],
                    "bugType": "<off_by_one|wrong_operator|wrong_variable|missing_base_case|wrong_initialization|wrong_return|infinite_loop|boundary_error|logic_error>",
                    "difficulty": <1|2|3>,
                    "explanation": "<why this is a bug and why the fix works>",
                    "bugTypeExplanation": "<general explanation of this bug type>",
                    "fixOptions": [
                        {{"id": "fix_1", "codeText": "<correct fix>", "isCorrect": true, "feedback": "Correct!"}},
                        {{"id": "fix_2", "codeText": "<plausible wrong fix>", "isCorrect": false, "feedback": "<why this is wrong>"}},
                        {{"id": "fix_3", "codeText": "<another wrong fix>", "isCorrect": false, "feedback": "<why this is wrong>"}}
                    ],
                    "hints": ["<category hint: what TYPE of bug>", "<location hint: which section>", "<line hint: which exact line>"]
                }}
            ],
            "testCases": [
                {{
                    "id": "test_1",
                    "inputDescription": "<what input is tested>",
                    "expectedOutput": "<correct output>",
                    "buggyOutput": "<what the buggy code produces>",
                    "exposedBugs": ["bug_1"]
                }}
            ],
            "redHerrings": [
                {{
                    "lineNumber": <a line that looks suspicious but is correct>,
                    "feedback": "<why this line is actually correct>"
                }}
            ]
        }}
    ],
    "config": {{
        "revealSequentially": true,
        "showTestOutput": true,
        "showRunButton": true,
        "fixMode": "{fix_mode}",
        "maxWrongLineClicks": 3,
        "roundMode": true
    }}
}}

Rules:
- Each round must have AT LEAST 1-2 bugs and 2+ test cases
- Bugs must be REALISTIC errors students actually make
- The buggy code must be COMPLETE and runnable (except for the bugs)
- Bug types should vary across rounds (don't repeat the same type)
- Test cases should clearly expose the bugs (buggyOutput != expectedOutput)
- Red herrings should be lines that LOOK suspicious but are correct
- Fix options should include the correct fix AND 2 plausible wrong fixes
- Difficulty should progress: round 1 (easy) → round {num_rounds} (hard)
- fixMode MUST be one of: multiple_choice, free_text
- fixOptions MUST contain EXACTLY ONE option with isCorrect: true
- hints MUST be an array of EXACTLY 3 strings [category_hint, location_hint, line_hint]
- bugLines MUST be an array of integers, even for single-line bugs: [5] not 5
- CRITICAL: Return ONLY the JSON object. No markdown, no explanation, no code fences.
- Keep string values concise. Do not pad descriptions unnecessarily.
"""
