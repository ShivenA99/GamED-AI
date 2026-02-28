"""
Game Design ReAct Agent

This agent handles the design phase of game generation:
- Plans game mechanics aligned with learning objectives
- Designs scene structure and layout
- Populates scenes with assets
- Defines interactions between elements

Replaces 4 agents: game_planner, scene_stage1_structure,
scene_stage2_assets, scene_stage3_interactions
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response, merge_tool_results
from app.agents.state import AgentState
from app.services.llm_service import ToolCallingResponse
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.react.game_design")


class GameDesignAgent(ReActAgent):
    """
    ReAct agent for game design.

    This agent:
    1. Plans game mechanics based on pedagogical goals
    2. Designs the scene layout and visual structure
    3. Populates the scene with appropriate assets
    4. Defines interactions and feedback patterns
    """

    def __init__(self):
        super().__init__(
            name="game_design_agent",
            system_prompt="""You are an educational game designer.

Your job is to design an engaging, pedagogically-sound game experience:

1. PLAN MECHANICS:
   - Align mechanics with Bloom's taxonomy level
   - Design scoring that rewards learning
   - Plan feedback patterns (immediate vs delayed)
   - Set appropriate difficulty

2. DESIGN STRUCTURE:
   - Create clear visual hierarchy
   - Position interactive elements logically
   - Design intuitive layout

3. POPULATE ASSETS:
   - Place drop zones at diagram regions
   - Create label chips for answers
   - Add visual feedback elements

4. DEFINE INTERACTIONS:
   - Map labels to correct zones
   - Define drag-and-drop behavior
   - Set validation rules
   - Design feedback for correct/incorrect

The game should be:
- Engaging and motivating
- Clear and intuitive
- Pedagogically effective
- Visually appealing""",
            max_iterations=12,
            tool_timeout=45.0
        )

    def get_tool_names(self) -> List[str]:
        """Tools available to this agent."""
        return [
            "plan_mechanics",
            "validate_mechanics",
            "design_structure",
            "validate_layout",
            "populate_assets",
            "lookup_asset_library",
            "define_interactions",
            "validate_interactions",
            "validate_scene",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build the task prompt from state."""
        question = state.get("question_text") or state.get("enhanced_question", "")
        template = state.get("selected_template", "INTERACTIVE_DIAGRAM")
        blooms = state.get("blooms_level", "understand")
        subject = state.get("subject", "general")
        zones = state.get("diagram_zones", [])
        labels = state.get("diagram_labels", [])

        return f"""Design a complete educational game for this question:

QUESTION: {question}
TEMPLATE: {template}
BLOOM'S LEVEL: {blooms}
SUBJECT: {subject}
ZONES: {len(zones)} detected regions
LABELS: {json.dumps(labels)}

Your task:
1. Use plan_mechanics to design game mechanics aligned with {blooms} level
2. Use validate_mechanics to verify your mechanics design
3. Use design_structure to create the scene layout
4. Use validate_layout to verify the structure
5. Use populate_assets to place elements in the scene
6. Use lookup_asset_library if you need additional assets
7. Use define_interactions to map labels to zones
8. Use validate_interactions to verify the interactions
9. Use validate_scene for final comprehensive check

When complete, provide your final answer as JSON with:
{{
    "game_plan": {{
        "mechanics": {{
            "core_mechanic": "...",
            "interaction_type": "drag_drop|click|sequence",
            "scoring_rules": {{}},
            "feedback_patterns": {{}},
            "progression": {{}}
        }}
    }},
    "scene_structure": {{
        "layout_type": "...",
        "regions": [...],
        "visual_hierarchy": {{}}
    }},
    "populated_scene": {{
        "elements": [...],
        "background": {{}}
    }},
    "interactions": [
        {{
            "source": "label_id",
            "target": "zone_id",
            "validation": {{}},
            "feedback": {{}}
        }}
    ],
    "validation_results": {{
        "mechanics_valid": true,
        "layout_valid": true,
        "interactions_valid": true,
        "overall_score": 0.0-1.0
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
            # Game plan / mechanics
            if "game_plan" in parsed:
                result["game_plan"] = parsed["game_plan"]

            if "mechanics" in parsed:
                result["game_plan"] = {"mechanics": parsed["mechanics"]}

            # Scene structure
            if "scene_structure" in parsed:
                result["scene_structure"] = parsed["scene_structure"]

            # Populated scene
            if "populated_scene" in parsed:
                result["populated_scene"] = parsed["populated_scene"]

                # Extract scene data for blueprint
                result["scene_data"] = {
                    "elements": parsed["populated_scene"].get("elements", []),
                    "background": parsed["populated_scene"].get("background", {}),
                    "structure": result.get("scene_structure", {})
                }

            # Interactions
            if "interactions" in parsed:
                result["interactions"] = parsed["interactions"]

            # Validation results
            if "validation_results" in parsed:
                result["design_validation"] = parsed["validation_results"]

        # Also merge tool results
        tool_data = merge_tool_results(response.tool_results)

        # Extract from tools if not in parsed
        if "mechanics" in tool_data and "game_plan" not in result:
            result["game_plan"] = {"mechanics": tool_data["mechanics"]}

        if "structure" in tool_data and "scene_structure" not in result:
            result["scene_structure"] = tool_data["structure"]

        if "populated_structure" in tool_data and "populated_scene" not in result:
            result["populated_scene"] = tool_data["populated_structure"]

        if "interactions" in tool_data and "interactions" not in result:
            result["interactions"] = tool_data["interactions"]

        # Ensure we have scene_data for blueprint
        if "scene_data" not in result and "populated_scene" in result:
            result["scene_data"] = result["populated_scene"]

        return result


# Singleton instance for use in graph
_agent_instance = None


def get_game_design_agent() -> GameDesignAgent:
    """Get singleton instance of the agent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = GameDesignAgent()
    return _agent_instance


async def game_design_agent(
    state: AgentState,
    ctx: Optional[Any] = None
) -> Dict[str, Any]:
    """Entry point function for the graph."""
    agent = get_game_design_agent()
    return await agent.run(state, ctx)
