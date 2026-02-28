"""
Input Enhancer Agent

Analyzes raw questions and extracts pedagogical context:
- Bloom's taxonomy level
- Learning objectives
- Key concepts
- Difficulty level
- Subject area
- Common misconceptions

This is the first stage in the game generation pipeline.
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.state import AgentState, PedagogicalContext
from app.services.llm_service import get_llm_service, LLMService
from app.agents.schemas.stages import get_pedagogical_context_schema
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.input_enhancer")


BLOOM_LEVELS = [
    "remember",      # Recall facts and basic concepts
    "understand",    # Explain ideas or concepts
    "apply",         # Use information in new situations
    "analyze",       # Draw connections among ideas
    "evaluate",      # Justify a decision or course of action
    "create"         # Produce new or original work
]

SUBJECTS = [
    "Mathematics",
    "Computer Science",
    "Physics",
    "Chemistry",
    "Biology",
    "History",
    "Geography",
    "Language Arts",
    "Economics",
    "Psychology",
    "Engineering",
    "General Science"
]


INPUT_ENHANCER_PROMPT = """You are an expert educational content analyst. Analyze the following question and extract pedagogical metadata.

## Question to Analyze:
{question_text}

## Answer Options (if any):
{question_options}

## Few-Shot Examples:

### Example 1: Algorithm Question (Binary Search)
**Question**: "Explain how binary search works on a sorted array. Demonstrate the algorithm finding the number 7 in the array [1, 3, 5, 7, 9, 11, 13]."

**Analysis**:
```json
{{
    "blooms_level": "understand",
    "blooms_justification": "Question asks to explain and demonstrate - requires understanding of how the algorithm works, not just recall",
    "learning_objectives": [
        "Understand the divide-and-conquer strategy of binary search",
        "Trace binary search execution step-by-step on a sorted array",
        "Explain why binary search requires sorted input",
        "Calculate time complexity of binary search"
    ],
    "key_concepts": [
        {{"concept": "Binary Search", "description": "Search algorithm that finds position of target by repeatedly dividing search space in half", "importance": "primary"}},
        {{"concept": "Sorted Array", "description": "Array where elements are in ascending or descending order", "importance": "primary"}},
        {{"concept": "Divide and Conquer", "description": "Algorithmic paradigm that breaks problem into smaller subproblems", "importance": "supporting"}},
        {{"concept": "Time Complexity", "description": "O(log n) efficiency of binary search", "importance": "supporting"}},
        {{"concept": "Array Indexing", "description": "Accessing elements by position in array", "importance": "supporting"}}
    ],
    "difficulty": "intermediate",
    "difficulty_justification": "Requires understanding of algorithm logic and ability to trace execution, but not advanced optimization",
    "subject": "Computer Science",
    "cross_cutting_subjects": ["Mathematics"],
    "common_misconceptions": [
        {{
            "misconception": "Binary search works on any array",
            "correction": "Binary search requires sorted input array",
            "why_common": "Students confuse binary search with linear search which works on unsorted arrays"
        }},
        {{
            "misconception": "Binary search always finds the element",
            "correction": "Binary search returns -1 or None if element not found",
            "why_common": "Students focus on successful cases and forget edge cases"
        }},
        {{
            "misconception": "Mid calculation uses (low + high) / 2",
            "correction": "Should use (low + high) // 2 for integer division to avoid floating point",
            "why_common": "Students apply general math formula without considering integer arithmetic"
        }}
    ],
    "prerequisites": [
        "Understanding of arrays and indexing",
        "Basic knowledge of search algorithms",
        "Familiarity with logarithmic functions"
    ],
    "question_intent": "Tests understanding of binary search algorithm mechanics and ability to trace execution through iterations"
}}
```

### Example 2: Sequence Question
**Question**: "Arrange the steps of photosynthesis in correct order: Light absorption, Electron transport, Carbon fixation, Oxygen release."

**Analysis**:
```json
{{
    "blooms_level": "remember",
    "blooms_justification": "Requires recall of factual sequence of steps",
    "learning_objectives": [
        "Recall the order of photosynthesis steps",
        "Identify the sequence of events in photosynthesis"
    ],
    "key_concepts": [
        {{"concept": "Photosynthesis", "description": "Process by which plants convert light energy to chemical energy", "importance": "primary"}},
        {{"concept": "Light Reactions", "description": "First stage involving light absorption", "importance": "primary"}},
        {{"concept": "Calvin Cycle", "description": "Second stage involving carbon fixation", "importance": "primary"}}
    ],
    "difficulty": "beginner",
    "difficulty_justification": "Basic recall of sequence, no complex reasoning required",
    "subject": "Biology",
    "cross_cutting_subjects": [],
    "common_misconceptions": [
        {{
            "misconception": "Oxygen is released first",
            "correction": "Oxygen is a byproduct released during electron transport, not the first step",
            "why_common": "Students confuse byproduct with initial step"
        }}
    ],
    "prerequisites": ["Basic understanding of plant biology"],
    "question_intent": "Tests recall of photosynthesis process sequence"
}}
```

## Analysis Instructions:

1. **Bloom's Taxonomy Level**: Determine which cognitive level this question targets:
   - remember: Recall facts and basic concepts (define, list, memorize)
   - understand: Explain ideas or concepts (describe, explain, summarize)
   - apply: Use information in new situations (execute, implement, solve)
   - analyze: Draw connections among ideas (compare, contrast, examine)
   - evaluate: Justify a decision or course of action (critique, judge, defend)
   - create: Produce new or original work (design, construct, develop)

2. **Learning Objectives**: What should a student be able to do after mastering this?
   - Write 2-4 specific, measurable learning objectives
   - Use action verbs aligned with Bloom's level

3. **Key Concepts**: What core concepts does this question test?
   - List 3-6 key concepts with brief descriptions
   - Include both primary and supporting concepts

4. **Difficulty Level**: Rate the difficulty:
   - beginner: Basic knowledge, straightforward application
   - intermediate: Requires synthesis of multiple concepts
   - advanced: Complex reasoning, expert-level understanding

5. **Subject Area**: Primary subject and any cross-cutting areas

6. **Common Misconceptions**: What mistakes do students typically make?
   - List 2-4 common misconceptions related to this topic
   - Include why students make these mistakes

7. **Prerequisites**: What should students already know?
   - List 2-4 prerequisite concepts or skills

## Response Format (JSON):
{{
    "blooms_level": "<level>",
    "blooms_justification": "<brief explanation>",
    "learning_objectives": [
        "<objective 1>",
        "<objective 2>"
    ],
    "key_concepts": [
        {{
            "concept": "<name>",
            "description": "<brief description>",
            "importance": "primary|supporting"
        }}
    ],
    "difficulty": "beginner|intermediate|advanced",
    "difficulty_justification": "<brief explanation>",
    "subject": "<primary subject>",
    "cross_cutting_subjects": ["<other relevant subjects>"],
    "common_misconceptions": [
        {{
            "misconception": "<what students often think>",
            "correction": "<correct understanding>",
            "why_common": "<why this mistake happens>"
        }}
    ],
    "prerequisites": [
        "<prerequisite 1>",
        "<prerequisite 2>"
    ],
    "question_intent": "<what reasoning or intuition this problem tests>"
}}

Respond with ONLY valid JSON."""


async def input_enhancer_agent(state: AgentState, ctx=None) -> AgentState:
    """
    Input Enhancer Agent

    Analyzes a question and extracts pedagogical context to inform
    downstream agents (router, game planner, story generator).

    Args:
        state: Current agent state with question_text

    Returns:
        Updated state with pedagogical_context populated
    """
    logger.info(f"InputEnhancer: Processing question {state.get('question_id', 'unknown')}")

    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])

    if not question_text:
        logger.error("InputEnhancer: No question text provided")
        return {
            **state,
            "current_agent": "input_enhancer",
            "error_message": "No question text provided"
        }

    # Build prompt
    options_str = "\n".join(f"- {opt}" for opt in question_options) if question_options else "None"
    prev_errors = state.get("current_validation_errors", [])
    error_context = "\n".join(f"- {err}" for err in prev_errors) if prev_errors else "None"
    prompt = INPUT_ENHANCER_PROMPT.format(
        question_text=question_text,
        question_options=options_str
    )
    if prev_errors:
        prompt += f"\n\n## Previous Validation Errors (fix these):\n{error_context}"

    try:
        llm = get_llm_service()
        # Use agent-specific model configuration (plug-and-play)
        result = await llm.generate_json_for_agent(
            agent_name="input_enhancer",
            prompt=prompt,
            schema_hint="PedagogicalContext JSON with blooms_level, subject, difficulty, key_concepts",
            json_schema=get_pedagogical_context_schema()
        )

        # Extract LLM metrics if present (added by LLM service for instrumentation)
        llm_metrics = result.pop("_llm_metrics", None)
        if ctx and llm_metrics:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms")
            )

        # Validate and normalize result
        pedagogical_context = _normalize_context(result)

        logger.info(
            f"InputEnhancer: Extracted - Bloom's: {pedagogical_context['blooms_level']}, "
            f"Subject: {pedagogical_context['subject']}, "
            f"Difficulty: {pedagogical_context['difficulty']}"
        )

        result_state = {
            **state,
            "pedagogical_context": pedagogical_context,
            "current_agent": "input_enhancer"
        }
        
        # Complete instrumentation
        if ctx:
            ctx.complete(result_state)
        
        return result_state

    except Exception as e:
        logger.error(f"InputEnhancer: LLM call failed: {e}", exc_info=True)

        # Return fallback context
        fallback_context = _create_fallback_context(question_text, question_options)

        return {
            **state,
            "pedagogical_context": fallback_context,
            "current_agent": "input_enhancer",
            "error_message": f"InputEnhancer fallback: {str(e)}"
        }


def _normalize_context(result: Dict[str, Any]) -> PedagogicalContext:
    """Normalize and validate the LLM response into PedagogicalContext"""

    # Validate Bloom's level
    blooms_level = result.get("blooms_level", "understand").lower()
    if blooms_level not in BLOOM_LEVELS:
        blooms_level = "understand"

    # Validate difficulty
    difficulty = result.get("difficulty", "intermediate").lower()
    if difficulty not in ["beginner", "intermediate", "advanced"]:
        difficulty = "intermediate"

    # Extract key concepts (handle both formats)
    key_concepts = []
    raw_concepts = result.get("key_concepts", [])
    for c in raw_concepts:
        if isinstance(c, dict):
            key_concepts.append(c.get("concept", str(c)))
        else:
            key_concepts.append(str(c))

    # Extract misconceptions
    misconceptions = []
    raw_misconceptions = result.get("common_misconceptions", [])
    for m in raw_misconceptions:
        if isinstance(m, dict):
            misconceptions.append({
                "misconception": m.get("misconception", ""),
                "correction": m.get("correction", ""),
                "why_common": m.get("why_common", "")
            })
        elif isinstance(m, str):
            misconceptions.append({
                "misconception": m,
                "correction": "",
                "why_common": ""
            })

    return {
        "blooms_level": blooms_level,
        "blooms_justification": result.get("blooms_justification", ""),
        "learning_objectives": result.get("learning_objectives", []),
        "key_concepts": key_concepts,
        "difficulty": difficulty,
        "difficulty_justification": result.get("difficulty_justification", ""),
        "subject": result.get("subject", "General"),
        "cross_cutting_subjects": result.get("cross_cutting_subjects", []),
        "common_misconceptions": misconceptions,
        "prerequisites": result.get("prerequisites", []),
        "question_intent": result.get("question_intent", "")
    }


def _create_fallback_context(
    question_text: str,
    question_options: Optional[List[str]]
) -> PedagogicalContext:
    """Create a basic fallback context when LLM fails"""

    # Simple heuristics for fallback
    text_lower = question_text.lower()

    # Guess Bloom's level from keywords
    if any(word in text_lower for word in ["define", "list", "name", "what is"]):
        blooms_level = "remember"
    elif any(word in text_lower for word in ["explain", "describe", "summarize"]):
        blooms_level = "understand"
    elif any(word in text_lower for word in ["calculate", "solve", "apply", "use"]):
        blooms_level = "apply"
    elif any(word in text_lower for word in ["compare", "contrast", "analyze"]):
        blooms_level = "analyze"
    elif any(word in text_lower for word in ["evaluate", "judge", "critique"]):
        blooms_level = "evaluate"
    elif any(word in text_lower for word in ["design", "create", "develop"]):
        blooms_level = "create"
    else:
        blooms_level = "understand"

    # Guess subject from keywords
    if any(word in text_lower for word in ["algorithm", "code", "programming", "function", "variable"]):
        subject = "Computer Science"
    elif any(word in text_lower for word in ["equation", "calculate", "number", "graph"]):
        subject = "Mathematics"
    elif any(word in text_lower for word in ["cell", "organism", "dna", "species"]):
        subject = "Biology"
    elif any(word in text_lower for word in ["atom", "molecule", "element", "reaction"]):
        subject = "Chemistry"
    elif any(word in text_lower for word in ["force", "energy", "motion", "wave"]):
        subject = "Physics"
    elif any(word in text_lower for word in ["history", "war", "century", "revolution"]):
        subject = "History"
    else:
        subject = "General Science"

    return {
        "blooms_level": blooms_level,
        "blooms_justification": "Fallback heuristic analysis",
        "learning_objectives": [f"Understand the concept presented in: {question_text[:50]}..."],
        "key_concepts": [],
        "difficulty": "intermediate",
        "difficulty_justification": "Default difficulty",
        "subject": subject,
        "cross_cutting_subjects": [],
        "common_misconceptions": [],
        "prerequisites": [],
        "question_intent": "General understanding"
    }


# Validator for input enhancement
async def validate_pedagogical_context(context: PedagogicalContext) -> Dict[str, Any]:
    """
    Validate the pedagogical context.

    Returns:
        Dict with 'valid' bool and 'errors' list
    """
    errors = []

    # Required fields
    if not context.get("blooms_level"):
        errors.append("Missing Bloom's taxonomy level")

    if context.get("blooms_level") not in BLOOM_LEVELS:
        errors.append(f"Invalid Bloom's level: {context.get('blooms_level')}")

    if not context.get("subject"):
        errors.append("Missing subject area")

    if not context.get("learning_objectives"):
        errors.append("Missing learning objectives")

    if context.get("difficulty") not in ["beginner", "intermediate", "advanced"]:
        errors.append(f"Invalid difficulty: {context.get('difficulty')}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "context": context
    }
