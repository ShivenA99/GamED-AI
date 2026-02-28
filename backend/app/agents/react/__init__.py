"""
ReAct Agents for GamED.AI v2

This package contains ReAct (Reasoning and Acting) agents that use
multi-step reasoning loops with tool calling.

## Architecture Variants

### Original (3 agents - not recommended for production)
1. research_routing_agent: Understanding phase (6 agents collapsed)
2. game_design_agent: Design phase (4 agents collapsed)
3. blueprint_asset_agent: Production phase (7 agents collapsed)

### Redesigned (4 agents - recommended)
Research shows 20-40% quality degradation at 10 tools per agent.
The redesigned architecture limits tools per agent:

1. research_image_agent: Research + image acquisition (5 tools)
2. game_design_agent: Game design phase (5 tools)
3. blueprint_agent: Blueprint creation (3 tools)
4. asset_render_agent: Asset generation + rendering (4 tools)
"""

# Original agents (backwards compatibility)
from app.agents.react.research_routing_agent import ResearchRoutingAgent
from app.agents.react.game_design_agent import GameDesignAgent
from app.agents.react.blueprint_asset_agent import BlueprintAssetAgent

# Redesigned agents (recommended)
from app.agents.react.research_image_agent import ResearchImageAgent
from app.agents.react.blueprint_agent import BlueprintAgent
from app.agents.react.asset_render_agent import AssetRenderAgent

__all__ = [
    # Original
    "ResearchRoutingAgent",
    "GameDesignAgent",
    "BlueprintAssetAgent",
    # Redesigned
    "ResearchImageAgent",
    "BlueprintAgent",
    "AssetRenderAgent",
]
