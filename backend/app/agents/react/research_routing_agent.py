"""
Research & Routing ReAct Agent

This agent handles the understanding phase of game generation:
- Analyzes the input question
- Retrieves domain knowledge
- Selects the appropriate game template
- Handles diagram image retrieval and zone detection

Replaces 6 agents: input_enhancer, domain_knowledge_retriever, router,
diagram_image_retriever, diagram_image_generator, gemini_zone_detector
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response, merge_tool_results
from app.agents.state import AgentState
from app.services.llm_service import ToolCallingResponse
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.react.research_routing")


class ResearchRoutingAgent(ReActAgent):
    """
    ReAct agent for research and routing.

    This agent:
    1. Analyzes the educational question
    2. Searches for domain knowledge and canonical terminology
    3. Selects the best game template
    4. For INTERACTIVE_DIAGRAM, handles image acquisition and zone detection
    """

    def __init__(self):
        super().__init__(
            name="research_routing_agent",
            system_prompt="""You are an educational content analyst and game router.

Your job is to thoroughly understand an educational question and prepare everything
needed for game generation:

1. ANALYZE the question to extract:
   - Subject area (biology, chemistry, physics, etc.)
   - Bloom's taxonomy level (remember, understand, apply, analyze, evaluate, create)
   - Key concepts to be taught
   - Question type (identification, comparison, explanation, etc.)

2. RESEARCH domain knowledge:
   - Find canonical/authoritative terminology
   - Identify standard labels for diagrams
   - Gather related concepts

3. SELECT the best game template:
   - INTERACTIVE_DIAGRAM: For labeling parts of diagrams
   - SEQUENCE_BUILDER: For ordering steps/processes
   - MATCHING_PAIRS: For matching related concepts
   - QUIZ: For multiple choice/true-false questions

4. If INTERACTIVE_DIAGRAM is selected:
   - Retrieve or generate a suitable diagram image
   - Detect zones/regions that should be labeled

Be thorough in your research. The quality of the game depends on accurate
domain knowledge and well-detected zones.""",
            max_iterations=15,
            tool_timeout=60.0
        )

    def get_tool_names(self) -> List[str]:
        """Tools available to this agent."""
        return [
            "analyze_question",
            "get_domain_knowledge",
            "select_template",
            "retrieve_diagram_image",
            "generate_diagram_image",
            "detect_zones",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build the task prompt from state."""
        question = state.get("question_text") or state.get("question", "")

        return f"""Analyze this educational question and prepare it for game generation:

QUESTION: {question}

Your task:
1. First, use analyze_question to understand the pedagogical context
2. Use get_domain_knowledge to find authoritative terminology and labels
3. Use select_template to choose the best game template
4. If INTERACTIVE_DIAGRAM is selected:
   - Use retrieve_diagram_image to find a suitable reference image
   - If no good image found, use generate_diagram_image to create one
   - Use detect_zones to identify regions that should be labeled

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
    "selected_template": "INTERACTIVE_DIAGRAM|SEQUENCE_BUILDER|MATCHING_PAIRS|QUIZ",
    "template_confidence": 0.0-1.0,
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

            if "selected_template" in parsed:
                result["selected_template"] = parsed["selected_template"]
                result["template_selection"] = {
                    "template": parsed["selected_template"],
                    "confidence": parsed.get("template_confidence", 0.8)
                }

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

        return result


# Singleton instance for use in graph
_agent_instance = None


def get_research_routing_agent() -> ResearchRoutingAgent:
    """Get singleton instance of the agent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ResearchRoutingAgent()
    return _agent_instance


async def research_routing_agent(
    state: AgentState,
    ctx: Optional[Any] = None
) -> Dict[str, Any]:
    """Entry point function for the graph."""
    agent = get_research_routing_agent()
    return await agent.run(state, ctx)
