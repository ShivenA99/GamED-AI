"""
Tool Registry for GamED.AI v2

Manages tool registration and provides agent-to-tool mappings for different
architecture variants (Agentic Sequential and ReAct).

Usage:
    registry = get_tool_registry()
    tools = registry.get_tools_for_agent("blueprint_generator", "agentic_sequential")
"""

from typing import Dict, List, Optional, Callable, Any, Awaitable
from dataclasses import dataclass

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.tools.registry")


# Import Tool from llm_service to avoid circular imports
# We'll use a forward reference and import at runtime
def _get_tool_class():
    from app.services.llm_service import Tool
    return Tool


# ============================================================================
# Agent-Tool Mappings
# ============================================================================

# =============================================================================
# AGENTIC SEQUENTIAL TOOLS (Redesigned: 8 agents, max 3 tools per agent)
# =============================================================================
# Research shows that 5-10 tools per agent is the safe maximum.
# We split blueprint_generator (was 6 tools) into blueprint_generator (2) + output_renderer (1)
# And merge input_enhancer + router → research_agent since template is hardcoded

AGENTIC_SEQUENTIAL_TOOLS = {
    # research_agent: Merged input_enhancer + router (template is fixed to INTERACTIVE_DIAGRAM)
    # Handles question analysis and domain knowledge retrieval
    "research_agent": [
        "analyze_question",
        "get_domain_knowledge",
    ],

    # image_agent: Dedicated image pipeline (retrieval → generation → zone detection)
    "image_agent": [
        "retrieve_diagram_image",
        "generate_diagram_image",
        "detect_zones",
    ],

    # game_planner: Game mechanics design with self-validation
    "game_planner": [
        "validate_mechanics",
    ],

    # scene_stage1_structure: Scene layout design with self-validation
    "scene_stage1_structure": [
        "validate_layout",
    ],

    # scene_stage2_assets: Asset population with library lookup
    "scene_stage2_assets": [
        "lookup_asset_library",
    ],

    # scene_stage3_interactions: Interaction design with self-validation
    "scene_stage3_interactions": [
        "validate_interactions",
    ],

    # blueprint_generator: Blueprint creation (REDUCED from 6 to 2 tools)
    "blueprint_generator": [
        "generate_blueprint",
        "validate_blueprint",
    ],

    # output_renderer: Final rendering (NEW - split from blueprint_generator)
    "output_renderer": [
        "generate_diagram_spec",
        "render_svg",
    ],

    # playability_validator: Final validation check (no tools needed)
    "playability_validator": [],

    # Legacy agent names for backwards compatibility
    "input_enhancer": ["get_domain_knowledge"],
    "router": ["retrieve_diagram_image", "generate_diagram_image", "detect_zones"],
}

# =============================================================================
# REACT TOOLS (Redesigned: 4 agents, max 5 tools per agent)
# =============================================================================
# Research shows 20-40% quality degradation at 10 tools per agent.
# We split blueprint_asset_agent (was 10 tools) → blueprint_agent (3) + asset_render_agent (4)
# And removed select_template since template is hardcoded to INTERACTIVE_DIAGRAM

REACT_TOOLS = {
    # research_image_agent: Research + Image phase (merged, no template selection)
    # Replaces: input_enhancer, domain_knowledge_retriever, diagram_image_retriever,
    #           diagram_image_generator, gemini_zone_detector
    "research_image_agent": [
        "analyze_question",
        "get_domain_knowledge",
        "retrieve_diagram_image",
        "generate_diagram_image",
        "detect_zones",
    ],

    # game_design_agent: Design phase (5 tools - validation removed for self-verification)
    # Replaces: game_planner, scene_stage1_structure, scene_stage2_assets, scene_stage3_interactions
    "game_design_agent": [
        "plan_mechanics",
        "design_structure",
        "populate_assets",
        "define_interactions",
        "validate_scene",
    ],

    # blueprint_agent: Blueprint creation (3 tools - focused)
    # Handles blueprint generation and validation
    "blueprint_agent": [
        "generate_blueprint",
        "validate_blueprint",
        "fix_blueprint",
    ],

    # asset_render_agent: Asset and rendering (4 tools - split from blueprint_asset_agent)
    # Handles asset generation, diagram spec, and final rendering
    "asset_render_agent": [
        "plan_assets",
        "generate_assets",
        "generate_diagram_spec",
        "render_svg",
    ],

    # v3: Game designer with pedagogical analysis, design validation, and submission tools
    "game_designer_v3": [
        "analyze_pedagogy",
        "check_capabilities",
        "get_example_designs",
        "validate_design",
        "submit_game_design",
    ],

    # v3: Scene architect with zone layout guidance and scene spec submission
    "scene_architect_v3": [
        "get_zone_layout_guidance",
        "get_mechanic_config_schema",
        "validate_scene_spec",
        "submit_scene_specs",
    ],

    # v3: Interaction designer with scoring templates and feedback generation
    "interaction_designer_v3": [
        "get_scoring_templates",
        "generate_misconception_feedback",
        "validate_interactions",
        "submit_interaction_specs",
    ],

    # v3: Asset generator with image search, generation, zone detection, and submission
    "asset_generator_v3": [
        "search_diagram_image",
        "generate_diagram_image",
        "detect_zones",
        "generate_animation_css",
        "submit_assets",
    ],

    # v3: Blueprint assembler with assembly, validation, repair, and submission tools
    "blueprint_assembler_v3": [
        "assemble_blueprint",
        "validate_blueprint",
        "repair_blueprint",
        "submit_blueprint",
    ],

    # Legacy agent name for backwards compatibility
    "research_routing_agent": [
        "analyze_question",
        "get_domain_knowledge",
        "retrieve_diagram_image",
        "generate_diagram_image",
        "detect_zones",
    ],
    "blueprint_asset_agent": [
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
    ],
}

# Combined mapping for easy lookup
AGENT_TOOL_MAPPING = {
    "agentic_sequential": AGENTIC_SEQUENTIAL_TOOLS,
    "react": REACT_TOOLS,
}


# ============================================================================
# Tool Registry
# ============================================================================

class ToolRegistry:
    """
    Singleton registry for managing tools.

    Provides:
    - Tool registration by name
    - Tool lookup for agents by variant
    - Tool validation
    """

    _instance: Optional["ToolRegistry"] = None
    _tools: Dict[str, Any]  # Tool objects keyed by name

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info("ToolRegistry initialized")

    def register(self, tool: Any) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool object with name, description, parameters, function
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def register_all(self, tools: List[Any]) -> None:
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Optional[Any]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_tools_for_agent(self, agent_name: str, variant: str) -> List[Any]:
        """
        Get all tools available to a specific agent in a specific variant.

        Args:
            agent_name: Name of the agent (e.g., "blueprint_generator")
            variant: Architecture variant ("agentic_sequential" or "react")

        Returns:
            List of Tool objects
        """
        if variant not in AGENT_TOOL_MAPPING:
            logger.warning(f"Unknown variant: {variant}, returning empty tool list")
            return []

        tool_names = AGENT_TOOL_MAPPING[variant].get(agent_name, [])

        tools = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                tools.append(tool)
            else:
                logger.warning(f"Tool '{name}' not found for agent '{agent_name}'")

        return tools

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def list_tools_for_variant(self, variant: str) -> List[str]:
        """List all unique tool names used in a variant."""
        if variant not in AGENT_TOOL_MAPPING:
            return []

        all_tools = set()
        for tools in AGENT_TOOL_MAPPING[variant].values():
            all_tools.update(tools)

        return sorted(all_tools)

    def is_registered(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def clear(self) -> None:
        """Clear all registered tools (useful for testing)."""
        self._tools.clear()
        logger.debug("Tool registry cleared")


# ============================================================================
# Singleton accessor
# ============================================================================

_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the singleton tool registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


# ============================================================================
# Tool Registration Helper
# ============================================================================

def create_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    function: Callable[..., Awaitable[Any]]
) -> Any:
    """
    Factory function to create a Tool instance.

    Args:
        name: Unique identifier for the tool
        description: Human-readable description
        parameters: JSON Schema for parameters
        function: Async callable that executes the tool

    Returns:
        Tool instance
    """
    Tool = _get_tool_class()
    return Tool(
        name=name,
        description=description,
        parameters=parameters,
        function=function
    )


def register_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    function: Callable[..., Awaitable[Any]]
) -> Any:
    """
    Create and register a tool in one step.

    Args:
        name: Unique identifier for the tool
        description: Human-readable description
        parameters: JSON Schema for parameters
        function: Async callable that executes the tool

    Returns:
        Tool instance
    """
    tool = create_tool(name, description, parameters, function)
    get_tool_registry().register(tool)
    return tool


# ============================================================================
# Initialize tools when module is imported
# ============================================================================

def initialize_tools() -> None:
    """
    Initialize and register all tools.

    This should be called at application startup to ensure all tools
    are available before agents need them.
    """
    logger.info("Initializing tool registry...")

    # Import and register tools from each category
    try:
        from app.tools.research_tools import register_research_tools
        register_research_tools()
        logger.info("Research tools registered")
    except ImportError as e:
        logger.warning(f"Could not import research_tools: {e}")

    try:
        from app.tools.vision_tools import register_vision_tools
        register_vision_tools()
        logger.info("Vision tools registered")
    except ImportError as e:
        logger.warning(f"Could not import vision_tools: {e}")

    try:
        from app.tools.blueprint_tools import register_blueprint_tools
        register_blueprint_tools()
        logger.info("Blueprint tools registered")
    except ImportError as e:
        logger.warning(f"Could not import blueprint_tools: {e}")

    try:
        from app.tools.render_tools import register_render_tools
        register_render_tools()
        logger.info("Render tools registered")
    except ImportError as e:
        logger.warning(f"Could not import render_tools: {e}")

    try:
        from app.tools.game_design_tools import register_game_design_tools
        register_game_design_tools()
        logger.info("Game design tools registered")
    except ImportError as e:
        logger.warning(f"Could not import game_design_tools: {e}")

    try:
        from app.tools.game_design_v3_tools import register_game_design_v3_tools
        register_game_design_v3_tools()
        logger.info("Game design v3 tools registered")
    except ImportError as e:
        logger.warning(f"Could not import game_design_v3_tools: {e}")

    try:
        from app.tools.scene_architect_tools import register_scene_architect_tools
        register_scene_architect_tools()
        logger.info("Scene architect v3 tools registered")
    except ImportError as e:
        logger.warning(f"Could not import scene_architect_tools: {e}")

    try:
        from app.tools.interaction_designer_tools import register_interaction_designer_tools
        register_interaction_designer_tools()
        logger.info("Interaction designer v3 tools registered")
    except ImportError as e:
        logger.warning(f"Could not import interaction_designer_tools: {e}")

    try:
        from app.tools.asset_generator_tools import register_asset_generator_tools
        register_asset_generator_tools()
        logger.info("Asset generator v3 tools registered")
    except ImportError as e:
        logger.warning(f"Could not import asset_generator_tools: {e}")

    try:
        from app.tools.blueprint_assembler_tools import register_blueprint_assembler_tools
        register_blueprint_assembler_tools()
        logger.info("Blueprint assembler v3 tools registered")
    except ImportError as e:
        logger.warning(f"Could not import blueprint_assembler_tools: {e}")

    registry = get_tool_registry()
    logger.info(f"Tool registry initialized with {len(registry.list_tools())} tools")
