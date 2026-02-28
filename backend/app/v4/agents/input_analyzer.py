"""Input Analyzer Agent (V4).

Analyzes raw questions and extracts pedagogical context.
~70% reused from V3 input_enhancer.py.

State writes: pedagogical_context
Model: gemini-2.5-flash (via agent config)
"""

from typing import Any, List, Optional

from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.v4.input_analyzer")


BLOOM_LEVELS = [
    "remember", "understand", "apply", "analyze", "evaluate", "create",
]

INPUT_ANALYZER_PROMPT = """\
You are an expert educational content analyst. Analyze the following question \
and extract pedagogical metadata.

## Question to Analyze:
{question_text}

## Answer Options (if any):
{question_options}

## Analysis Instructions:

1. **Bloom's Taxonomy Level**: Exactly one of: remember, understand, apply, analyze, evaluate, create
2. **Learning Objectives**: 2-4 specific, measurable objectives
3. **Key Concepts**: 3-6 key concepts, each with a functional description and importance level
4. **Difficulty**: Exactly one of: beginner, intermediate, advanced
5. **Subject Area**: Primary subject and cross-cutting areas
6. **Common Misconceptions**: 2-4 misconceptions with corrections and reasoning
7. **Prerequisites**: 2-4 prerequisite concepts or skills the learner needs
8. **Question Intent**: What this question is really testing

## Response Format (JSON):
Return EXACTLY this structure with no extra keys:
{{
    "blooms_level": "<exactly one of: remember|understand|apply|analyze|evaluate|create>",
    "blooms_justification": "<1-2 sentence explanation of why this Bloom's level>",
    "learning_objectives": [
        "<specific measurable objective starting with a verb>"
    ],
    "key_concepts": [
        {{
            "concept": "<concept name>",
            "description": "<1-2 sentence functional description of this concept>",
            "importance": "<exactly one of: primary|supporting>"
        }}
    ],
    "difficulty": "<exactly one of: beginner|intermediate|advanced>",
    "difficulty_justification": "<1-2 sentence explanation>",
    "subject": "<primary subject area>",
    "cross_cutting_subjects": ["<related subject 1>"],
    "common_misconceptions": [
        {{
            "misconception": "<what students commonly think incorrectly>",
            "correction": "<the correct understanding>",
            "why_common": "<why students develop this misconception>"
        }}
    ],
    "prerequisites": ["<prerequisite knowledge or skill>"],
    "question_intent": "<what this question is designed to assess>"
}}

Rules:
- blooms_level MUST be exactly one of the six values listed (lowercase)
- difficulty MUST be exactly one of the three values listed (lowercase)
- key_concepts MUST be objects with concept/description/importance — NOT plain strings
- Respond with ONLY valid JSON, no markdown wrapping"""


async def input_analyzer(state: dict) -> dict:
    """Analyze input question and extract pedagogical context.

    Args:
        state: V4MainState dict with question_text.

    Returns:
        Dict with pedagogical_context to merge into state.
    """
    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])

    logger.info(f"Analyzing question: {question_text[:80]}...")

    if not question_text:
        logger.error("No question text provided")
        return {
            "pedagogical_context": _create_fallback_context(question_text, question_options),
            "error_message": "Input analyzer: no question text provided",
        }

    options_str = "\n".join(f"- {opt}" for opt in question_options) if question_options else "None"
    prompt = INPUT_ANALYZER_PROMPT.format(
        question_text=question_text,
        question_options=options_str,
    )

    try:
        llm = get_llm_service()
        result = await llm.generate_json_for_agent(
            agent_name="input_analyzer",
            prompt=prompt,
            schema_hint="PedagogicalContext JSON with blooms_level, subject, difficulty",
        )
        llm_metrics = result.pop("_llm_metrics", None)

        # Use LLM output directly — prompt is precise about format
        pedagogical_context = result

        logger.info(
            f"Extracted — Bloom's: {pedagogical_context.get('blooms_level')}, "
            f"Subject: {pedagogical_context.get('subject')}, "
            f"Difficulty: {pedagogical_context.get('difficulty')}"
        )

        out: dict = {"pedagogical_context": pedagogical_context}
        if llm_metrics:
            out["_llm_metrics"] = llm_metrics
        return out

    except Exception as e:
        logger.error(f"LLM call failed: {e}", exc_info=True)
        return {
            "pedagogical_context": _create_fallback_context(question_text, question_options),
            "error_message": f"Input analyzer fallback: {str(e)}",
        }



def _create_fallback_context(
    question_text: str,
    question_options: Optional[List[str]],
) -> dict:
    """Create heuristic fallback context when LLM fails."""
    text_lower = (question_text or "").lower()

    # Guess Bloom's level
    if any(w in text_lower for w in ("define", "list", "name", "what is")):
        blooms_level = "remember"
    elif any(w in text_lower for w in ("explain", "describe", "summarize")):
        blooms_level = "understand"
    elif any(w in text_lower for w in ("calculate", "solve", "apply", "use")):
        blooms_level = "apply"
    elif any(w in text_lower for w in ("compare", "contrast", "analyze")):
        blooms_level = "analyze"
    elif any(w in text_lower for w in ("evaluate", "judge", "critique")):
        blooms_level = "evaluate"
    elif any(w in text_lower for w in ("design", "create", "develop")):
        blooms_level = "create"
    else:
        blooms_level = "understand"

    # Guess subject
    if any(w in text_lower for w in ("algorithm", "code", "programming")):
        subject = "Computer Science"
    elif any(w in text_lower for w in ("equation", "calculate", "number")):
        subject = "Mathematics"
    elif any(w in text_lower for w in ("cell", "organism", "dna", "species")):
        subject = "Biology"
    elif any(w in text_lower for w in ("atom", "molecule", "element")):
        subject = "Chemistry"
    elif any(w in text_lower for w in ("force", "energy", "motion")):
        subject = "Physics"
    else:
        subject = "General Science"

    return {
        "blooms_level": blooms_level,
        "blooms_justification": "Fallback heuristic analysis",
        "learning_objectives": [f"Understand: {question_text[:50]}..."],
        "key_concepts": [],
        "difficulty": "intermediate",
        "difficulty_justification": "Default difficulty",
        "subject": subject,
        "cross_cutting_subjects": [],
        "common_misconceptions": [],
        "prerequisites": [],
        "question_intent": "General understanding",
    }
