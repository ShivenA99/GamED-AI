"""
Research Agent for Agentic Sequential Pipeline

Merged agent that combines:
- input_enhancer: Question analysis and enhancement
- router: Template selection (hardcoded to INTERACTIVE_DIAGRAM)

This agent handles the initial research phase:
1. Analyzes the educational question
2. Extracts pedagogical context (Bloom's level, subject, concepts)
3. Retrieves domain knowledge
4. Sets template to INTERACTIVE_DIAGRAM (fixed for this pipeline)

Tools available:
- analyze_question: Extract pedagogical context from question
- get_domain_knowledge: Search for canonical terminology

The template selection is hardcoded because this pipeline is specifically
for Label Diagram games, reducing cognitive load on the agent.
"""

from typing import Dict, Any, Optional, List

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.research_agent")


async def research_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Research Agent - Combined input enhancement and template routing.

    This agent performs:
    1. Question analysis (Bloom's level, subject, concepts)
    2. Domain knowledge retrieval
    3. Template selection (hardcoded to INTERACTIVE_DIAGRAM)

    Inputs: question_text
    Outputs: pedagogical_context, domain_knowledge, diagram_labels, template_selection
    """
    logger.info("ResearchAgent: Starting research phase")

    question_text = state.get("question_text") or state.get("question", "")

    if not question_text:
        logger.warning("ResearchAgent: No question_text provided")
        return {
            "pedagogical_context": {},
            "domain_knowledge": {},
            "diagram_labels": [],
            "template_selection": {"template": "INTERACTIVE_DIAGRAM", "confidence": 1.0},
            "current_agent": "research_agent"
        }

    try:
        llm = get_llm_service()

        # Step 1: Analyze question for pedagogical context
        analysis_prompt = f"""Analyze this educational question for pedagogical characteristics:

Question: {question_text}

Extract and return as JSON:
{{
    "blooms_level": "remember|understand|apply|analyze|evaluate|create",
    "subject": "biology|chemistry|physics|mathematics|anatomy|general",
    "difficulty": "easy|medium|hard",
    "key_concepts": ["concept1", "concept2", ...],
    "question_type": "identification|labeling|comparison|explanation|process",
    "target_learning_outcome": "What should the learner understand after this?"
}}

Focus on accurate extraction - this informs game design."""

        pedagogical_context = await llm.generate_json(
            prompt=analysis_prompt,
            system_prompt="You are an educational assessment expert. Extract pedagogical characteristics accurately."
        )

        # Ensure defaults
        pedagogical_context.setdefault("blooms_level", "understand")
        pedagogical_context.setdefault("subject", "general")
        pedagogical_context.setdefault("difficulty", "medium")
        pedagogical_context.setdefault("key_concepts", [])
        pedagogical_context.setdefault("question_type", "identification")

        logger.info(f"ResearchAgent: Analyzed question - subject: {pedagogical_context.get('subject')}, "
                   f"level: {pedagogical_context.get('blooms_level')}")

        # Step 2: Retrieve domain knowledge
        subject = pedagogical_context.get("subject", "general")
        domain_prompt = f"""For this educational question in {subject}:

Question: {question_text}

Provide domain knowledge as JSON:
{{
    "canonical_labels": ["exact term 1", "exact term 2", ...],
    "definitions": {{
        "term1": "definition",
        "term2": "definition"
    }},
    "related_terms": ["term1", "term2", ...],
    "common_mistakes": ["mistake1", "mistake2"]
}}

IMPORTANT: canonical_labels should be the EXACT scientific/technical terms that would appear on a labeled diagram. Be precise - use proper terminology."""

        domain_knowledge = await llm.generate_json(
            prompt=domain_prompt,
            system_prompt=f"You are a {subject} expert. Provide accurate canonical terminology and definitions."
        )

        # Extract labels for diagram
        diagram_labels = domain_knowledge.get("canonical_labels", [])

        # Ensure defaults
        domain_knowledge.setdefault("canonical_labels", [])
        domain_knowledge.setdefault("definitions", {})
        domain_knowledge.setdefault("related_terms", [])

        logger.info(f"ResearchAgent: Found {len(diagram_labels)} canonical labels")

        # Step 3: Set template (hardcoded for Label Diagram pipeline)
        template_selection = {
            "template": "INTERACTIVE_DIAGRAM",
            "template_type": "INTERACTIVE_DIAGRAM",
            "confidence": 1.0,
            "reasoning": "Template is fixed to INTERACTIVE_DIAGRAM for this pipeline"
        }

        # Track metrics
        if ctx:
            ctx.set_custom_metric("labels_found", len(diagram_labels))
            ctx.set_custom_metric("concepts_extracted", len(pedagogical_context.get("key_concepts", [])))

        return {
            "pedagogical_context": pedagogical_context,
            "domain_knowledge": domain_knowledge,
            "diagram_labels": diagram_labels,
            "template_selection": template_selection,
            "blooms_level": pedagogical_context.get("blooms_level"),
            "subject": pedagogical_context.get("subject"),
            "key_concepts": pedagogical_context.get("key_concepts", []),
            "current_agent": "research_agent"
        }

    except Exception as e:
        logger.error(f"ResearchAgent: Failed: {e}", exc_info=True)
        return {
            "pedagogical_context": {
                "blooms_level": "understand",
                "subject": "general",
                "difficulty": "medium",
                "key_concepts": [],
                "question_type": "identification"
            },
            "domain_knowledge": {
                "canonical_labels": [],
                "definitions": {},
                "related_terms": []
            },
            "diagram_labels": [],
            "template_selection": {"template": "INTERACTIVE_DIAGRAM", "confidence": 1.0},
            "current_agent": "research_agent",
            "error_message": f"ResearchAgent failed: {str(e)}"
        }
