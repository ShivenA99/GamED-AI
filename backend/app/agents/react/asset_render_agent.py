"""
Asset & Render ReAct Agent (Redesigned)

This agent handles asset generation and final rendering:
- Plans required assets from the blueprint
- Generates or retrieves assets
- Creates diagram specifications
- Renders final SVG output

Split from blueprint_asset_agent (was 10 tools) to reduce cognitive load.
Research shows 20-40% quality degradation at 10 tools per agent.

Tools available (4 max):
- plan_assets
- generate_assets
- generate_diagram_spec
- render_svg
"""

import json
from typing import Dict, Any, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response, merge_tool_results
from app.agents.state import AgentState
from app.services.llm_service import ToolCallingResponse
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.react.asset_render")


class AssetRenderAgent(ReActAgent):
    """
    ReAct agent for asset generation and rendering.

    This agent:
    1. Plans required assets from the blueprint
    2. Generates or retrieves needed assets
    3. Creates diagram specifications
    4. Renders final SVG output

    Note: Blueprint creation is handled by blueprint_agent
    """

    def __init__(self):
        super().__init__(
            name="asset_render_agent",
            system_prompt="""You are a game asset and rendering specialist.

Your job is to produce the final, deployable game output:

1. PLAN ASSETS:
   - Identify all required assets from the blueprint
   - Determine which assets need generation vs retrieval
   - Plan optimal order for asset creation

2. GENERATE ASSETS:
   - Create or download each required asset
   - Ensure assets meet quality requirements
   - Track successful and failed generations

3. CREATE DIAGRAM SPEC:
   - Map zones to visual drop zone specifications
   - Position label chips appropriately
   - Define visual styling for interactive elements

4. RENDER SVG:
   - Generate the final SVG diagram
   - Include zone markers and styling
   - Create data URIs for embedding

Your output must include:
- All assets ready for use
- Complete diagram specification
- Final SVG content""",
            max_iterations=10,
            tool_timeout=90.0  # Longer timeout for asset generation
        )

    def get_tool_names(self) -> List[str]:
        """Tools available to this agent (focused - 4 tools)."""
        return [
            "plan_assets",
            "generate_assets",
            "generate_diagram_spec",
            "render_svg",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build the task prompt from state."""
        blueprint = state.get("blueprint", {})
        zones = state.get("diagram_zones", [])
        labels = state.get("diagram_labels", [])
        image_url = state.get("diagram_image_url", "")

        return f"""Produce the final game assets and rendering:

BLUEPRINT:
{json.dumps(blueprint, indent=2, default=str)[:1200]}

IMAGE URL: {image_url or "No image"}
ZONES: {len(zones)} zones
LABELS: {json.dumps(labels)}

Your task:
1. Use plan_assets to identify all required assets
2. Use generate_assets to create or download assets
3. Use generate_diagram_spec to create drop zone and label specifications
4. Use render_svg to produce the final SVG output

When complete, provide your final answer as JSON with:
{{
    "assets": {{
        "planned": [...],
        "generated": [...],
        "failed": []
    }},
    "diagram_spec": {{
        "canvas": {{"width": 800, "height": 600}},
        "background": {{}},
        "zones": [...],
        "legend": {{}}
    }},
    "svg_content": "<svg>...</svg>",
    "production_summary": {{
        "assets_generated": 0,
        "svg_size_bytes": 0,
        "render_success": true
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
            # Assets
            if "assets" in parsed:
                assets = parsed["assets"]
                result["planned_assets"] = assets.get("planned", [])
                result["generated_assets"] = assets.get("generated", [])
                result["failed_assets"] = assets.get("failed", [])

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
        if "planned_assets" in tool_data and "planned_assets" not in result:
            result["planned_assets"] = tool_data["planned_assets"]

        if "generated_assets" in tool_data and "generated_assets" not in result:
            result["generated_assets"] = tool_data["generated_assets"]

        if "diagram_spec" in tool_data and "diagram_spec" not in result:
            result["diagram_spec"] = tool_data["diagram_spec"]

        if "svg_content" in tool_data and "final_svg" not in result:
            result["final_svg"] = tool_data["svg_content"]
            result["diagram_svg"] = tool_data["svg_content"]

        # Ensure we have diagram_spec
        if "diagram_spec" not in result:
            result["diagram_spec"] = self._create_default_spec(state)

        # Create asset URLs
        image_url = state.get("diagram_image_url", "")
        if image_url:
            result["asset_urls"] = {"diagram": image_url}
        elif result.get("final_svg"):
            from urllib.parse import quote
            data_uri = f"data:image/svg+xml;utf8,{quote(result['final_svg'])}"
            result["asset_urls"] = {"diagram": data_uri}
        else:
            result["asset_urls"] = {}

        # Mark generation complete
        result["generation_complete"] = True

        return result

    def _create_default_spec(self, state: AgentState) -> Dict[str, Any]:
        """Create a default diagram specification from state."""
        zones = state.get("diagram_zones", [])
        labels = state.get("diagram_labels", [])
        blueprint = state.get("blueprint", {})

        diagram = blueprint.get("diagram", {})
        width = int(diagram.get("width", 800))
        height = int(diagram.get("height", 600))

        spec_zones = []
        for i, zone in enumerate(zones):
            label = labels[i] if i < len(labels) else f"Zone {i + 1}"
            center = zone.get("center", [50, 50])
            if isinstance(center, list) and len(center) >= 2:
                x, y = center[0], center[1]
            else:
                x, y = zone.get("x", 50), zone.get("y", 50)

            spec_zones.append({
                "id": zone.get("id", f"zone_{i + 1}"),
                "label": label,
                "x": float(x),
                "y": float(y),
                "radius": float(zone.get("radius", 8)),
                "color": "#3b82f6"
            })

        return {
            "canvas": {"width": width, "height": height},
            "background": {
                "style": "grid",
                "primary": "#f8fafc",
                "secondary": "#eef2ff"
            },
            "showLabels": False,
            "legend": {
                "title": "Labels",
                "items": [{"label": z["label"], "color": z["color"]} for z in spec_zones]
            },
            "zones": spec_zones,
            "decorations": []
        }


# Singleton instance for use in graph
_agent_instance = None


def get_asset_render_agent() -> AssetRenderAgent:
    """Get singleton instance of the agent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AssetRenderAgent()
    return _agent_instance


async def asset_render_agent(
    state: AgentState,
    ctx: Optional[Any] = None
) -> Dict[str, Any]:
    """Entry point function for the graph."""
    agent = get_asset_render_agent()
    return await agent.run(state, ctx)
