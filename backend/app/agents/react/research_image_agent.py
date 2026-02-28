"""
Research & Image ReAct Agent (Redesigned)

This agent handles the understanding phase of game generation:
- Analyzes the input question
- Retrieves domain knowledge
- Handles diagram image retrieval and zone detection

NOTE: Template selection has been removed because it's hardcoded to INTERACTIVE_DIAGRAM.
This reduces cognitive load and improves quality (research shows 5-10 tools max).

Replaces 5 agents: input_enhancer, domain_knowledge_retriever,
diagram_image_retriever, diagram_image_generator, gemini_zone_detector

Tools available (5 max):
- analyze_question
- get_domain_knowledge
- retrieve_diagram_image
- generate_diagram_image
- detect_zones
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response, merge_tool_results
from app.agents.state import AgentState
from app.services.llm_service import ToolCallingResponse
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.react.research_image")


class ResearchImageAgent(ReActAgent):
    """
    ReAct agent for research and image acquisition.

    This agent:
    1. Analyzes the educational question
    2. Searches for domain knowledge and canonical terminology
    3. Retrieves or generates a suitable diagram image
    4. Detects zones/regions for labeling

    Note: Template is fixed to INTERACTIVE_DIAGRAM (no selection needed)
    """

    def __init__(self):
        super().__init__(
            name="research_image_agent",
            system_prompt="""You are an educational content analyst and image specialist.

Your job is to thoroughly understand an educational question and acquire the
necessary visual content for game generation:

1. ANALYZE the question to extract:
   - Subject area (biology, chemistry, physics, etc.)
   - Bloom's taxonomy level (remember, understand, apply, analyze, evaluate, create)
   - Key concepts to be taught
   - Question type (identification, comparison, explanation, etc.)

2. RESEARCH domain knowledge:
   - Find canonical/authoritative terminology
   - Identify standard labels for diagrams
   - Gather related concepts

3. ACQUIRE DIAGRAM IMAGE:
   - First try to retrieve a suitable educational diagram
   - If retrieval fails, generate an appropriate diagram
   - Select images with clear structure suitable for labeling

4. DETECT ZONES:
   - Identify regions that should be labeled
   - Get zone positions and labels

The template is fixed to INTERACTIVE_DIAGRAM - focus on getting good image and zones.""",
            max_iterations=12,
            tool_timeout=60.0
        )

    def get_tool_names(self) -> List[str]:
        """Tools available to this agent (reduced from 6 to 5)."""
        return [
            "analyze_question",
            "get_domain_knowledge",
            "retrieve_diagram_image",
            "generate_diagram_image",
            "detect_zones",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build the task prompt from state."""
        question = state.get("question_text") or state.get("question", "")

        return f"""Analyze this educational question and prepare it for game generation:

QUESTION: {question}

NOTE: The template is FIXED to INTERACTIVE_DIAGRAM - you do not need to select a template.

Your task:
1. Use analyze_question to understand the pedagogical context
2. Use get_domain_knowledge to find authoritative terminology and labels
3. Use retrieve_diagram_image to find a suitable reference image
4. If no good image found, use generate_diagram_image to create one
5. Use detect_zones to identify regions that should be labeled

When complete, provide your final answer as JSON with:
{{
    "enhanced_question": "enriched version of the question",
    "blooms_level": "remember|understand|apply|analyze|evaluate|create",
    "subject": "subject area",
    "key_concepts": ["concept1", "concept2"],
    "domain_knowledge": {{
        "canonical_labels": ["label1", "label2"],
        "definitions": {{}},
        "related_terms": []
    }},
    "diagram_data": {{
        "image_url": "url or null",
        "zones": [...],
        "labels": [...]
    }}
}}"""

    def parse_final_result(
        self,
        response: ToolCallingResponse,
        state: AgentState
    ) -> Dict[str, Any]:
        """Parse the final response into state updates."""
        result = {}

        # Extract JSON from final answer
        parsed = extract_json_from_response(response.content)

        if parsed:
            # Map to state keys
            if "enhanced_question" in parsed:
                result["question_text"] = parsed["enhanced_question"]
                result["enhanced_question"] = parsed["enhanced_question"]

            if "blooms_level" in parsed:
                result["blooms_level"] = parsed["blooms_level"]

            if "subject" in parsed:
                result["subject"] = parsed["subject"]

            if "key_concepts" in parsed:
                result["key_concepts"] = parsed["key_concepts"]

            if "domain_knowledge" in parsed:
                result["domain_knowledge"] = parsed["domain_knowledge"]
                # Extract labels for convenience
                labels = parsed["domain_knowledge"].get("canonical_labels", [])
                if labels:
                    result["diagram_labels"] = labels

            if "diagram_data" in parsed:
                diagram_data = parsed["diagram_data"]
                if diagram_data.get("image_url"):
                    result["diagram_image_url"] = diagram_data["image_url"]
                if diagram_data.get("zones"):
                    result["diagram_zones"] = diagram_data["zones"]
                if diagram_data.get("labels"):
                    result["diagram_labels"] = diagram_data["labels"]

        # Also merge any tool results we got
        tool_data = merge_tool_results(response.tool_results)

        # Extract useful data from tools if not in parsed response
        if "canonical_labels" in tool_data and "diagram_labels" not in result:
            result["diagram_labels"] = tool_data["canonical_labels"]

        if "zones" in tool_data and "diagram_zones" not in result:
            result["diagram_zones"] = tool_data["zones"]

        if "image_url" in tool_data and "diagram_image_url" not in result:
            result["diagram_image_url"] = tool_data["image_url"]

        # Pedagogical context for downstream agents
        result["pedagogical_context"] = {
            "blooms_level": result.get("blooms_level", "understand"),
            "subject": result.get("subject", "general"),
            "key_concepts": result.get("key_concepts", [])
        }

        # Fixed template selection (INTERACTIVE_DIAGRAM is hardcoded)
        result["selected_template"] = "INTERACTIVE_DIAGRAM"
        result["template_selection"] = {
            "template": "INTERACTIVE_DIAGRAM",
            "template_type": "INTERACTIVE_DIAGRAM",
            "confidence": 1.0,
            "reasoning": "Template is fixed to INTERACTIVE_DIAGRAM for this pipeline"
        }

        return result


# Singleton instance for use in graph
_agent_instance = None


def get_research_image_agent() -> ResearchImageAgent:
    """Get singleton instance of the agent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ResearchImageAgent()
    return _agent_instance


async def research_image_agent(
    state: AgentState,
    ctx: Optional[Any] = None
) -> Dict[str, Any]:
    """Entry point function for the graph."""
    agent = get_research_image_agent()
    return await agent.run(state, ctx)
