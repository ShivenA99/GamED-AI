"""
Agentic Wrapper for GamED.AI v2

Wraps existing agents with tool calling capabilities for the Agentic Sequential variant.
This allows agents to invoke tools during their execution while maintaining the same
overall pipeline structure.

Usage:
    from app.agents.agentic_wrapper import wrap_agent_with_tools

    # In graph.py
    graph.add_node("blueprint_generator",
        wrap_agent_with_tools(blueprint_generator, "blueprint_generator")
    )
"""

import json
import functools
from typing import Callable, Optional, Any, Dict, List
import re

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service, Tool, ToolCallingResponse
from app.tools.registry import get_tool_registry
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.agentic_wrapper")


def _try_repair_json(json_str: str) -> Optional[Dict]:
    """
    Attempt to repair common JSON issues from LLM responses.

    Common issues:
    - Trailing commas
    - Unquoted keys
    - Single quotes instead of double quotes
    - Control characters

    Args:
        json_str: Potentially malformed JSON string

    Returns:
        Parsed dict if repair succeeded, None otherwise
    """
    repairs = [
        # Remove trailing commas before } or ]
        (r',(\s*[}\]])', r'\1'),
        # Replace single quotes with double quotes (careful with apostrophes)
        (r"'([^']+)':", r'"\1":'),
        # Remove control characters
        (r'[\x00-\x1f\x7f-\x9f]', ''),
    ]

    repaired = json_str
    for pattern, replacement in repairs:
        repaired = re.sub(pattern, replacement, repaired)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        # Try one more time with stricter cleaning
        try:
            # Extract just the content between outermost braces
            start = repaired.find("{")
            end = repaired.rfind("}")
            if start != -1 and end > start:
                inner = repaired[start:end+1]
                return json.loads(inner)
        except json.JSONDecodeError:
            pass

    return None


def wrap_agent_with_tools(
    agent_fn: Callable,
    agent_name: str,
    tool_mode: str = "single"
) -> Callable:
    """
    Wrap an existing agent function to add tool calling capability.

    This creates a new function that:
    1. Gets available tools for the agent
    2. Calls the LLM with tool definitions
    3. Executes any tool calls
    4. Returns the final result

    Args:
        agent_fn: The original agent function
        agent_name: Name of the agent (for tool lookup)
        tool_mode: "single" for one-shot tools, "react" for ReAct loop

    Returns:
        Wrapped async function with same signature
    """

    @functools.wraps(agent_fn)
    async def wrapped_agent(
        state: AgentState,
        ctx: Optional[InstrumentedAgentContext] = None
    ) -> dict:
        """Wrapped agent with tool calling support."""

        # Get tools for this agent
        registry = get_tool_registry()
        tools = registry.get_tools_for_agent(agent_name, "agentic_sequential")

        # If no tools available, fall back to original agent
        if not tools:
            logger.debug(f"Agent '{agent_name}' has no tools, using original implementation")
            return await agent_fn(state, ctx)

        logger.info(f"Agent '{agent_name}' has {len(tools)} tools available")

        # Build the prompt for tool-augmented generation
        try:
            prompt, system_prompt = _build_tool_augmented_prompt(
                agent_name=agent_name,
                state=state,
                tools=tools
            )

            # Call LLM with tools
            llm = get_llm_service()
            response = await llm.generate_with_tools_for_agent(
                agent_name=agent_name,
                prompt=prompt,
                tools=tools,
                system_prompt=system_prompt,
                mode=tool_mode
            )

            # Track metrics
            if ctx:
                ctx.set_llm_metrics(
                    model=response.model,
                    prompt_tokens=response.total_input_tokens,
                    completion_tokens=response.total_output_tokens,
                    latency_ms=response.total_latency_ms
                )

                # Track tool calls
                if response.tool_calls:
                    ctx.set_tool_metrics([
                        {
                            "name": tc.name,
                            "arguments": tc.arguments,
                            "result_status": tr.status.value if tr else "unknown"
                        }
                        for tc, tr in zip(response.tool_calls, response.tool_results)
                    ])

            # Parse the response into state update
            result = _parse_agent_response(
                agent_name=agent_name,
                response=response,
                tool_results=response.tool_results
            )

            return result

        except Exception as e:
            logger.error(f"Tool-augmented agent '{agent_name}' failed: {e}", exc_info=True)
            # Fall back to original agent on error
            logger.warning(f"Falling back to original '{agent_name}' implementation")
            return await agent_fn(state, ctx)

    return wrapped_agent


def _build_tool_augmented_prompt(
    agent_name: str,
    state: AgentState,
    tools: List[Tool]
) -> tuple[str, str]:
    """
    Build prompts for tool-augmented generation.

    Returns:
        Tuple of (user_prompt, system_prompt)
    """
    # Agent-specific prompt builders
    prompt_builders = {
        "input_enhancer": _build_input_enhancer_prompt,
        "router": _build_router_prompt,
        "game_planner": _build_game_planner_prompt,
        "scene_stage1_structure": _build_structure_prompt,
        "scene_stage2_assets": _build_assets_prompt,
        "scene_stage3_interactions": _build_interactions_prompt,
        "blueprint_generator": _build_blueprint_prompt,
    }

    builder = prompt_builders.get(agent_name, _build_default_prompt)
    return builder(state, tools)


def _build_default_prompt(state: AgentState, tools: List[Tool]) -> tuple[str, str]:
    """Default prompt builder."""
    tool_names = [t.name for t in tools]
    system = f"""You are an AI agent with access to these tools: {tool_names}.
Use the tools when needed to complete your task. Return your final answer as JSON."""

    user = f"State: {json.dumps(dict(state), default=str)[:2000]}"
    return user, system


def _build_input_enhancer_prompt(state: AgentState, tools: List[Tool]) -> tuple[str, str]:
    """Build prompt for input_enhancer agent."""
    system = """You are an educational content analyzer. Your task is to:
1. Analyze the input question
2. Use the get_domain_knowledge tool to find canonical terminology
3. Extract Bloom's taxonomy level and subject area
4. Return enhanced question with pedagogical context

Return JSON with: enhanced_question, blooms_level, subject, key_concepts, domain_knowledge"""

    question = state.get("question_text") or state.get("question", "")
    user = f"""Analyze and enhance this educational question:

Question: {question}

Use the get_domain_knowledge tool to find authoritative terminology for any diagrams or scientific concepts mentioned.

Return your analysis as JSON."""

    return user, system


def _build_router_prompt(state: AgentState, tools: List[Tool]) -> tuple[str, str]:
    """Build prompt for router agent with image handling tools."""
    system = """You are a game template router with vision capabilities. Your task is to:
1. Analyze the question and determine the best game template
2. If INTERACTIVE_DIAGRAM is selected, use vision tools to:
   - Call retrieve_diagram_image to find reference images
   - Call generate_diagram_image to create a clean diagram (if needed)
   - Call detect_zones to identify labelable regions
3. Return template selection with any diagram data

Available templates: INTERACTIVE_DIAGRAM, SEQUENCE_BUILDER, MATCHING_PAIRS, QUIZ

Return JSON with: selected_template, confidence, diagram_data (if applicable)"""

    question = state.get("question_text") or state.get("enhanced_question", "")
    domain = state.get("domain_knowledge", {})

    user = f"""Route this question to the appropriate game template:

Question: {question}
Domain Knowledge: {json.dumps(domain, default=str)[:1000]}

If this is a labeling question about a diagram, use the vision tools to prepare the diagram."""

    return user, system


def _build_game_planner_prompt(state: AgentState, tools: List[Tool]) -> tuple[str, str]:
    """Build prompt for game_planner agent."""
    system = """You are an educational game designer. Your task is to:
1. Design game mechanics aligned with learning objectives
2. Use validate_mechanics tool to verify your design
3. Plan scoring, feedback, and progression

Return JSON with: game_plan containing mechanics, scoring_rules, feedback_patterns"""

    question = state.get("question_text", "")
    template = state.get("selected_template", "INTERACTIVE_DIAGRAM")
    blooms = state.get("blooms_level", "understand")

    user = f"""Design game mechanics for:

Question: {question}
Template: {template}
Bloom's Level: {blooms}

Create engaging mechanics that support learning. Validate your design."""

    return user, system


def _build_structure_prompt(state: AgentState, tools: List[Tool]) -> tuple[str, str]:
    """Build prompt for scene_stage1_structure agent."""
    system = """You are a UI/UX designer for educational games. Your task is to:
1. Design the scene layout structure
2. Define regions for content, interactions, and feedback
3. Use validate_layout tool to verify your design

Return JSON with: scene_structure containing regions and visual_hierarchy"""

    game_plan = state.get("game_plan", {})
    zones = state.get("diagram_zones", [])

    user = f"""Design scene layout structure:

Game Plan: {json.dumps(game_plan, default=str)[:1000]}
Number of zones: {len(zones)}

Create a clear, engaging layout. Validate your design."""

    return user, system


def _build_assets_prompt(state: AgentState, tools: List[Tool]) -> tuple[str, str]:
    """Build prompt for scene_stage2_assets agent."""
    system = """You are an asset manager for educational games. Your task is to:
1. Populate the scene structure with specific assets
2. Use lookup_asset_library to find available assets
3. Assign assets to each region and element

Return JSON with: populated_scene containing all elements with asset assignments"""

    structure = state.get("scene_structure", {})
    zones = state.get("diagram_zones", [])
    labels = state.get("diagram_labels", [])

    user = f"""Populate this scene with assets:

Structure: {json.dumps(structure, default=str)[:1000]}
Zones: {len(zones)} detected
Labels: {labels}

Look up available assets and assign them appropriately."""

    return user, system


def _build_interactions_prompt(state: AgentState, tools: List[Tool]) -> tuple[str, str]:
    """Build prompt for scene_stage3_interactions agent."""
    system = """You are an interaction designer for educational games. Your task is to:
1. Define interactions between game elements
2. Specify validation rules and feedback
3. Use validate_interactions tool to verify your design

Return JSON with: interactions array defining all element interactions"""

    populated = state.get("populated_scene", {})
    mechanics = state.get("game_plan", {}).get("mechanics", {})

    user = f"""Define interactions for this scene:

Scene: {json.dumps(populated, default=str)[:1000]}
Mechanics: {json.dumps(mechanics, default=str)[:500]}

Create clear interaction rules. Validate your design."""

    return user, system


def _build_blueprint_prompt(state: AgentState, tools: List[Tool]) -> tuple[str, str]:
    """Build prompt for blueprint_generator agent with full output pipeline."""
    system = """You are a game blueprint generator with production capabilities. Your task is to:
1. Generate the complete game blueprint JSON
2. Use validate_blueprint tool and fix any errors
3. Use plan_assets and generate_assets to prepare all assets
4. Use validate_assets to verify asset generation
5. Use generate_diagram_spec to create diagram specifications
6. Use render_svg to produce final SVG output

You have a complete pipeline of tools to produce the final game. Use them in order.

Return JSON with: blueprint, diagram_spec, svg_content, validation_results"""

    scene = state.get("populated_scene", {})
    interactions = state.get("interactions", [])
    template = state.get("selected_template", "INTERACTIVE_DIAGRAM")
    zones = state.get("diagram_zones", [])
    labels = state.get("diagram_labels", [])

    user = f"""Generate complete game output:

Template: {template}
Scene: {json.dumps(scene, default=str)[:1000]}
Interactions: {json.dumps(interactions, default=str)[:500]}
Zones: {len(zones)}
Labels: {labels}

Generate blueprint, validate, create assets, and render final SVG."""

    return user, system


def _parse_agent_response(
    agent_name: str,
    response: ToolCallingResponse,
    tool_results: List[Any]
) -> dict:
    """
    Parse the LLM response into a state update dictionary.

    Args:
        agent_name: Name of the agent
        response: Response from tool-calling LLM
        tool_results: Results from tool executions

    Returns:
        State update dictionary
    """
    content = response.content

    # Try to parse JSON from content with improved error handling
    result = {}
    parse_error = None

    try:
        # Find JSON in response (look for outer-most braces)
        if content:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError as e:
                    # Try to repair common JSON issues
                    repaired = _try_repair_json(json_str)
                    if repaired:
                        result = repaired
                    else:
                        parse_error = str(e)
                        logger.warning(f"JSON parse failed for {agent_name}: {e}")
                        # Include partial data for debugging
                        result = {
                            "_parse_error": parse_error,
                            "_raw_response_preview": content[:500] if len(content) > 500 else content
                        }
            else:
                # No JSON found in response
                logger.warning(f"No JSON found in {agent_name} response")
                result = {
                    "_parse_error": "No JSON object found in response",
                    "_raw_response_preview": content[:500] if content and len(content) > 500 else content
                }
    except Exception as e:
        logger.error(f"Unexpected error parsing {agent_name} response: {e}")
        result = {
            "_parse_error": str(e),
            "_raw_response_preview": content[:500] if content and len(content) > 500 else content
        }

    # Merge tool results into state based on agent
    tool_data = _extract_tool_data(tool_results)

    # Agent-specific result mapping
    if agent_name == "input_enhancer":
        if "canonical_labels" in tool_data:
            result["domain_knowledge"] = tool_data
        if "enhanced_question" in result:
            result["question_text"] = result["enhanced_question"]

    elif agent_name == "router":
        if "zones" in tool_data:
            result["diagram_zones"] = tool_data["zones"]
        if "image_url" in tool_data:
            result["diagram_image_url"] = tool_data["image_url"]
        if "selected_template" in result:
            result["template_selection"] = {
                "template": result["selected_template"],
                "confidence": result.get("confidence", 0.8)
            }

    elif agent_name == "blueprint_generator":
        if "svg_content" in tool_data:
            result["final_svg"] = tool_data["svg_content"]
        if "diagram_spec" in tool_data:
            result["diagram_spec"] = tool_data["diagram_spec"]
        if "valid" in tool_data:
            result["blueprint_valid"] = tool_data["valid"]

    # Add LLM metrics
    result["_llm_metrics"] = {
        "model": response.model,
        "prompt_tokens": response.total_input_tokens,
        "completion_tokens": response.total_output_tokens,
        "latency_ms": response.total_latency_ms
    }

    # Add tool call summary
    if response.tool_calls:
        result["_tool_calls"] = [
            {"name": tc.name, "arguments": tc.arguments}
            for tc in response.tool_calls
        ]

    return result


def _extract_tool_data(tool_results: List[Any]) -> dict:
    """Extract useful data from tool results."""
    combined = {}

    for tr in tool_results:
        if hasattr(tr, 'result') and tr.result:
            result = tr.result
            if isinstance(result, dict):
                combined.update(result)

    return combined


# ============================================================================
# Utility Functions
# ============================================================================

def create_agentic_sequential_agents() -> dict:
    """
    Create all agents for the Agentic Sequential variant.

    Returns:
        Dictionary of agent_name -> wrapped_agent_function
    """
    # Import original agents
    from app.agents.input_enhancer import input_enhancer
    from app.agents.router import router
    from app.agents.game_planner import game_planner
    from app.agents.scene_stage1_structure import scene_stage1_structure
    from app.agents.scene_stage2_assets import scene_stage2_assets
    from app.agents.scene_stage3_interactions import scene_stage3_interactions
    from app.agents.blueprint_generator import blueprint_generator
    from app.agents.playability_validator import playability_validator

    agents = {
        "input_enhancer": wrap_agent_with_tools(input_enhancer, "input_enhancer"),
        "router": wrap_agent_with_tools(router, "router"),
        "game_planner": wrap_agent_with_tools(game_planner, "game_planner"),
        "scene_stage1_structure": wrap_agent_with_tools(scene_stage1_structure, "scene_stage1_structure"),
        "scene_stage2_assets": wrap_agent_with_tools(scene_stage2_assets, "scene_stage2_assets"),
        "scene_stage3_interactions": wrap_agent_with_tools(scene_stage3_interactions, "scene_stage3_interactions"),
        "blueprint_generator": wrap_agent_with_tools(blueprint_generator, "blueprint_generator"),
        "playability_validator": wrap_agent_with_tools(playability_validator, "playability_validator"),
    }

    return agents
