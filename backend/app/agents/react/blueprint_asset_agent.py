"""
Blueprint & Asset ReAct Agent

This agent handles the production phase of game generation:
- Generates the complete game blueprint
- Validates and fixes blueprint issues
- Plans and generates assets
- Creates diagram specifications
- Renders final SVG output

Replaces 7 agents: blueprint_generator, blueprint_validator, asset_planner,
asset_generator_orchestrator, asset_validator, diagram_spec_generator, diagram_svg_generator
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response, merge_tool_results
from app.agents.state import AgentState
from app.services.llm_service import ToolCallingResponse
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.react.blueprint_asset")


class BlueprintAssetAgent(ReActAgent):
    """
    ReAct agent for blueprint generation and asset production.

    This agent:
    1. Generates complete game blueprint JSON
    2. Validates blueprint and fixes errors
    3. Plans required assets
    4. Generates/retrieves assets
    5. Creates diagram specifications
    6. Renders final SVG output
    """

    def __init__(self):
        super().__init__(
            name="blueprint_asset_agent",
            system_prompt="""You are a game production engineer.

Your job is to produce the final, deployable game output:

1. GENERATE BLUEPRINT:
   - Create complete game JSON following template schema
   - Include all scenes, elements, and interactions
   - Ensure all required fields are present

2. VALIDATE & FIX:
   - Validate blueprint against template requirements
   - Fix any errors automatically
   - Retry validation until passing

3. PREPARE ASSETS:
   - Plan all required assets
   - Download or generate each asset
   - Validate asset availability

4. CREATE DIAGRAM SPEC:
   - Map zones to drop zones
   - Position label chips
   - Define visual styling

5. RENDER SVG:
   - Generate final SVG output
   - Include all interactive elements
   - Apply visual styling

Your output must be:
- Valid JSON blueprint
- All assets available
- Complete SVG ready for rendering""",
            max_iterations=15,
            tool_timeout=90.0  # Longer timeout for asset generation
        )

    def get_tool_names(self) -> List[str]:
        """Tools available to this agent."""
        return [
            "generate_blueprint",
            "validate_blueprint",
            "fix_blueprint",
            "plan_assets",
            "generate_assets",
            "validate_assets",
            "generate_diagram_spec",
            "validate_diagram_spec",
            "render_svg",
            "optimize_svg",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build the task prompt from state."""
        question = state.get("question_text", "")
        template = state.get("selected_template", "INTERACTIVE_DIAGRAM")
        game_plan = state.get("game_plan", {})
        scene_data = state.get("scene_data") or state.get("populated_scene", {})
        interactions = state.get("interactions", [])
        zones = state.get("diagram_zones", [])
        labels = state.get("diagram_labels", [])
        image_url = state.get("diagram_image_url", "")

        return f"""Produce the complete game output for this educational game:

QUESTION: {question}
TEMPLATE: {template}
IMAGE URL: {image_url or "No image"}

GAME PLAN:
{json.dumps(game_plan, indent=2, default=str)[:1000]}

SCENE DATA:
{json.dumps(scene_data, indent=2, default=str)[:1000]}

INTERACTIONS:
{json.dumps(interactions, indent=2, default=str)[:500]}

ZONES: {len(zones)} detected
LABELS: {json.dumps(labels)}

Your production pipeline:
1. First, assemble the game_plan, scene_data, and interactions into a valid blueprint
2. Use validate_blueprint to check the blueprint
3. If validation fails, use fix_blueprint to repair issues
4. Repeat validation until the blueprint passes
5. Use plan_assets to identify required assets
6. Use generate_assets to create/download assets
7. Use validate_assets to verify all assets are ready
8. Use generate_diagram_spec to create drop zone and label specs
9. Use validate_diagram_spec to verify the spec
10. Use render_svg to produce the final SVG
11. Optionally use optimize_svg to reduce file size

When complete, provide your final answer as JSON with:
{{
    "blueprint": {{
        "template": "{template}",
        "game_title": "...",
        "scenes": [...],
        ...
    }},
    "blueprint_valid": true,
    "assets": {{
        "generated": [...],
        "failed": [...]
    }},
    "diagram_spec": {{
        "drop_zones": [...],
        "label_chips": [...]
    }},
    "svg_content": "<svg>...</svg>",
    "production_summary": {{
        "validation_attempts": 1,
        "assets_generated": 0,
        "svg_size_bytes": 0
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
            # Blueprint
            if "blueprint" in parsed:
                result["blueprint"] = parsed["blueprint"]

            if "blueprint_valid" in parsed:
                result["blueprint_valid"] = parsed["blueprint_valid"]

            # Assets
            if "assets" in parsed:
                result["generated_assets"] = parsed["assets"].get("generated", [])
                result["failed_assets"] = parsed["assets"].get("failed", [])

            # Diagram spec
            if "diagram_spec" in parsed:
                result["diagram_spec"] = parsed["diagram_spec"]

            # SVG output
            if "svg_content" in parsed:
                result["final_svg"] = parsed["svg_content"]
                result["diagram_svg"] = parsed["svg_content"]

            # Production summary
            if "production_summary" in parsed:
                result["production_summary"] = parsed["production_summary"]

        # Also merge tool results
        tool_data = merge_tool_results(response.tool_results)

        # Extract from tools if not in parsed
        if "fixed_blueprint" in tool_data and "blueprint" not in result:
            result["blueprint"] = tool_data["fixed_blueprint"]

        if "valid" in tool_data and "blueprint_valid" not in result:
            result["blueprint_valid"] = tool_data["valid"]

        if "diagram_spec" in tool_data and "diagram_spec" not in result:
            result["diagram_spec"] = tool_data["diagram_spec"]

        if "svg_content" in tool_data and "final_svg" not in result:
            result["final_svg"] = tool_data["svg_content"]
            result["diagram_svg"] = tool_data["svg_content"]

        if "generated_assets" in tool_data:
            result["generated_assets"] = tool_data["generated_assets"]

        # Ensure we have core outputs
        if "blueprint" not in result:
            # Try to construct from state
            result["blueprint"] = self._construct_blueprint(state)

        if "diagram_spec" not in result and "diagram_zones" in state:
            result["diagram_spec"] = {
                "drop_zones": self._zones_to_drop_zones(
                    state.get("diagram_zones", []),
                    state.get("diagram_labels", [])
                ),
                "label_chips": self._labels_to_chips(
                    state.get("diagram_labels", [])
                )
            }

        return result

    def _construct_blueprint(self, state: AgentState) -> Dict[str, Any]:
        """Construct a minimal valid blueprint from state."""
        template = state.get("selected_template", "INTERACTIVE_DIAGRAM")
        question = state.get("question_text", "Educational Game")
        scene_data = state.get("scene_data") or state.get("populated_scene", {})
        labels = state.get("diagram_labels", [])
        zones = state.get("diagram_zones", [])

        # Build elements from zones and labels
        elements = []
        for i, zone in enumerate(zones):
            label = labels[i] if i < len(labels) else f"Zone {i+1}"
            elements.append({
                "id": f"drop_zone_{i}",
                "type": "drop_zone",
                "position": {
                    "x": zone.get("center", [0.5, 0.5])[0] if isinstance(zone.get("center"), list) else 0.5,
                    "y": zone.get("center", [0.5, 0.5])[1] if isinstance(zone.get("center"), list) else 0.5
                },
                "correct_label": label
            })

        return {
            "template": template,
            "game_title": question[:50] if question else "Educational Game",
            "scenes": [
                {
                    "scene_id": "main",
                    "background": {
                        "type": "image",
                        "url": state.get("diagram_image_url", "")
                    },
                    "elements": elements,
                    "labels": labels
                }
            ],
            "metadata": {
                "blooms_level": state.get("blooms_level", "understand"),
                "subject": state.get("subject", "general")
            }
        }

    def _zones_to_drop_zones(self, zones: List[Dict], labels: List[str]) -> List[Dict]:
        """Convert detected zones to drop zone specs."""
        drop_zones = []
        for i, zone in enumerate(zones):
            label = labels[i] if i < len(labels) else f"Zone {i+1}"
            center = zone.get("center", [0.5, 0.5])
            if isinstance(center, list) and len(center) >= 2:
                x, y = center[0], center[1]
            else:
                x, y = 0.5, 0.5

            drop_zones.append({
                "id": f"dropzone_{i}",
                "label": label,
                "position": {"x": x, "y": y},
                "size": {"width": 80, "height": 40}
            })
        return drop_zones

    def _labels_to_chips(self, labels: List[str]) -> List[Dict]:
        """Convert labels to label chip specs."""
        return [
            {
                "id": f"label_{i}",
                "text": label,
                "matched_zone": f"dropzone_{i}"
            }
            for i, label in enumerate(labels)
        ]


# Singleton instance for use in graph
_agent_instance = None


def get_blueprint_asset_agent() -> BlueprintAssetAgent:
    """Get singleton instance of the agent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BlueprintAssetAgent()
    return _agent_instance


async def blueprint_asset_agent(
    state: AgentState,
    ctx: Optional[Any] = None
) -> Dict[str, Any]:
    """Entry point function for the graph."""
    agent = get_blueprint_asset_agent()
    return await agent.run(state, ctx)
