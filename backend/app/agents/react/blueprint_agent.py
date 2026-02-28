"""
Blueprint ReAct Agent (Redesigned)

This agent handles blueprint creation and validation:
- Generates the complete game blueprint JSON
- Validates blueprint against template requirements
- Fixes blueprint errors automatically

Split from blueprint_asset_agent (was 10 tools) to reduce cognitive load.
Research shows 20-40% quality degradation at 10 tools per agent.

Tools available (3 max):
- generate_blueprint
- validate_blueprint
- fix_blueprint
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response, merge_tool_results
from app.agents.state import AgentState
from app.services.llm_service import ToolCallingResponse
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.react.blueprint")


class BlueprintAgent(ReActAgent):
    """
    ReAct agent for blueprint creation and validation.

    This agent:
    1. Generates complete game blueprint JSON
    2. Validates blueprint structure and content
    3. Fixes errors automatically and re-validates

    Note: Asset generation and rendering are handled by asset_render_agent
    """

    def __init__(self):
        super().__init__(
            name="blueprint_agent",
            system_prompt="""You are a game blueprint engineer.

Your job is to create a valid, complete game blueprint:

1. GENERATE BLUEPRINT:
   - Create complete JSON following the INTERACTIVE_DIAGRAM template schema
   - Include all required fields: template, title, scenes, labels, diagram
   - Map zones to drop zones correctly
   - Include scoring configuration

2. VALIDATE BLUEPRINT:
   - Check schema compliance
   - Verify all required fields are present
   - Ensure label-zone mappings are correct
   - Check for missing or malformed data

3. FIX ERRORS:
   - Automatically repair validation errors
   - Re-validate until the blueprint passes
   - Maximum 3 fix attempts

Your blueprint must be:
- Valid JSON with no syntax errors
- Complete with all required fields
- Properly structured for INTERACTIVE_DIAGRAM template
- Ready for asset generation and rendering""",
            max_iterations=10,
            tool_timeout=60.0
        )

    def get_tool_names(self) -> List[str]:
        """Tools available to this agent (focused - 3 tools)."""
        return [
            "generate_blueprint",
            "validate_blueprint",
            "fix_blueprint",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build the task prompt from state."""
        question = state.get("question_text", "")
        game_plan = state.get("game_plan", {})
        scene_data = state.get("scene_data") or state.get("populated_scene", {})
        interactions = state.get("interactions", [])
        zones = state.get("diagram_zones", [])
        labels = state.get("diagram_labels", [])
        image_url = state.get("diagram_image_url", "")

        return f"""Create a valid game blueprint for this educational game:

QUESTION: {question}
TEMPLATE: INTERACTIVE_DIAGRAM
IMAGE URL: {image_url or "No image"}

GAME PLAN:
{json.dumps(game_plan, indent=2, default=str)[:800]}

SCENE DATA:
{json.dumps(scene_data, indent=2, default=str)[:800]}

INTERACTIONS:
{json.dumps(interactions, indent=2, default=str)[:400]}

ZONES: {len(zones)} detected
LABELS: {json.dumps(labels)}

Your task:
1. Use generate_blueprint to create the complete blueprint JSON
   - Combine game_plan, scene_data, and interactions
   - Include all {len(zones)} zones and {len(labels)} labels
2. Use validate_blueprint to check the blueprint
3. If validation fails, use fix_blueprint to repair issues
4. Repeat validation until it passes (max 3 attempts)

When complete, provide your final answer as JSON with:
{{
    "blueprint": {{
        "template": "INTERACTIVE_DIAGRAM",
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": "...",
        "diagram": {{
            "assetUrl": "{image_url}",
            "width": 800,
            "height": 600,
            "zones": [...]
        }},
        "labels": [...],
        "scenes": [...],
        "scoring": {{...}}
    }},
    "blueprint_valid": true,
    "validation_attempts": 1,
    "errors_fixed": []
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
            # Blueprint
            if "blueprint" in parsed:
                result["blueprint"] = parsed["blueprint"]

            if "blueprint_valid" in parsed:
                result["blueprint_valid"] = parsed["blueprint_valid"]

            if "validation_attempts" in parsed:
                result["blueprint_validation_attempts"] = parsed["validation_attempts"]

            if "errors_fixed" in parsed:
                result["blueprint_errors_fixed"] = parsed["errors_fixed"]

        # Also merge tool results
        tool_data = merge_tool_results(response.tool_results)

        # Extract from tools if not in parsed
        if "blueprint" in tool_data and "blueprint" not in result:
            result["blueprint"] = tool_data["blueprint"]

        if "fixed_blueprint" in tool_data and "blueprint" not in result:
            result["blueprint"] = tool_data["fixed_blueprint"]

        if "valid" in tool_data and "blueprint_valid" not in result:
            result["blueprint_valid"] = tool_data["valid"]

        # Ensure we have a blueprint
        if "blueprint" not in result:
            result["blueprint"] = self._construct_blueprint(state)

        return result

    def _construct_blueprint(self, state: AgentState) -> Dict[str, Any]:
        """Construct a minimal valid blueprint from state."""
        question = state.get("question_text", "Educational Game")
        scene_data = state.get("scene_data") or state.get("populated_scene", {})
        labels = state.get("diagram_labels", [])
        zones = state.get("diagram_zones", [])
        image_url = state.get("diagram_image_url", "")

        # Build label objects
        label_objects = [
            {
                "id": f"label_{i}",
                "text": label,
                "correctZoneId": f"zone_{i + 1}"
            }
            for i, label in enumerate(labels)
        ]

        # Build zone objects
        zone_objects = []
        for i, zone in enumerate(zones):
            center = zone.get("center", [50, 50])
            if isinstance(center, list) and len(center) >= 2:
                x, y = center[0], center[1]
            else:
                x, y = zone.get("x", 50), zone.get("y", 50)

            zone_objects.append({
                "id": zone.get("id", f"zone_{i + 1}"),
                "label": labels[i] if i < len(labels) else f"Zone {i + 1}",
                "x": x,
                "y": y,
                "radius": zone.get("radius", 8)
            })

        return {
            "template": "INTERACTIVE_DIAGRAM",
            "templateType": "INTERACTIVE_DIAGRAM",
            "title": question[:50] if question else "Label Diagram",
            "diagram": {
                "assetUrl": image_url,
                "width": 800,
                "height": 600,
                "zones": zone_objects
            },
            "labels": label_objects,
            "scenes": [
                {
                    "scene_id": "main",
                    "background": {
                        "type": "image",
                        "url": image_url
                    },
                    "elements": zone_objects
                }
            ],
            "scoring": {
                "pointsPerCorrect": 10,
                "penaltyPerIncorrect": -5,
                "bonusForPerfect": 50
            },
            "metadata": {
                "blooms_level": state.get("blooms_level", "understand"),
                "subject": state.get("subject", "general")
            }
        }


# Singleton instance for use in graph
_agent_instance = None


def get_blueprint_agent() -> BlueprintAgent:
    """Get singleton instance of the agent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BlueprintAgent()
    return _agent_instance


async def blueprint_agent(
    state: AgentState,
    ctx: Optional[Any] = None
) -> Dict[str, Any]:
    """Entry point function for the graph."""
    agent = get_blueprint_agent()
    return await agent.run(state, ctx)
