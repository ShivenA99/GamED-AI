"""
ReAct Agent Base for GamED.AI v2

Base class for ReAct (Reasoning and Acting) agents that implement
multi-step reasoning loops with tool calling.

The ReAct pattern:
1. THOUGHT: Agent reasons about what to do
2. ACTION: Agent calls a tool
3. OBSERVATION: Agent receives tool result
4. REPEAT until task complete

Usage:
    class MyReActAgent(ReActAgent):
        def __init__(self):
            super().__init__(
                name="my_agent",
                system_prompt="You are...",
                max_iterations=10
            )

        def get_tool_names(self) -> List[str]:
            return ["tool1", "tool2"]

    agent = MyReActAgent()
    result = await agent.run(state, ctx)
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import (
    get_llm_service,
    Tool,
    ToolCallingResponse,
    ReActStep
)
from app.tools.registry import get_tool_registry
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.react_base")


class ReActAgent(ABC):
    """
    Base class for ReAct agents.

    ReAct agents use a multi-step reasoning loop where they:
    1. Think about what to do
    2. Take an action (call a tool)
    3. Observe the result
    4. Repeat until they have a final answer

    Subclasses must implement:
    - get_tool_names(): List of tools this agent can use
    - build_task_prompt(state): Prompt for the specific task
    - parse_final_result(response, state): Extract state updates from result
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        max_iterations: int = 10,
        tool_timeout: float = 60.0,
        model: Optional[str] = None,
        temperature: float = 0.7
    ):
        """
        Initialize a ReAct agent.

        Args:
            name: Agent name (for logging and tool lookup)
            system_prompt: Base system prompt for the agent
            max_iterations: Maximum reasoning loop iterations
            tool_timeout: Timeout for tool execution in seconds
            model: Optional model override
            temperature: LLM temperature setting
        """
        self.name = name
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.tool_timeout = tool_timeout
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def get_tool_names(self) -> List[str]:
        """
        Return list of tool names this agent can use.

        Override in subclass to specify available tools.
        """
        pass

    @abstractmethod
    def build_task_prompt(self, state: AgentState) -> str:
        """
        Build the task-specific prompt from state.

        Args:
            state: Current agent state

        Returns:
            Task prompt string
        """
        pass

    @abstractmethod
    def parse_final_result(
        self,
        response: ToolCallingResponse,
        state: AgentState
    ) -> Dict[str, Any]:
        """
        Parse the final response into state updates.

        Args:
            response: Final response from ReAct loop
            state: Current state for context

        Returns:
            Dictionary of state updates
        """
        pass

    def get_tools(self) -> List[Tool]:
        """Get Tool objects for this agent."""
        registry = get_tool_registry()
        tool_names = self.get_tool_names()

        tools = []
        for name in tool_names:
            tool = registry.get(name)
            if tool:
                tools.append(tool)
            else:
                logger.warning(f"Tool '{name}' not found for agent '{self.name}'")

        return tools

    def build_full_system_prompt(self) -> str:
        """Build complete system prompt with ReAct instructions."""
        tools = self.get_tools()
        tool_descriptions = "\n".join([
            f"- {t.name}: {t.description}"
            for t in tools
        ])

        return f"""{self.system_prompt}

You operate using the ReAct (Reasoning and Acting) framework.

For each step:
1. THOUGHT: Explain your reasoning about what to do next
2. ACTION: Call a tool if you need information or to take action
3. OBSERVATION: Receive the result and incorporate it into your reasoning

Continue this cycle until you have gathered enough information to provide a complete answer.

When you're ready to give your final answer, respond WITHOUT calling any tools.
Include your final result as valid JSON.

Available tools:
{tool_descriptions}

Guidelines:
- Think step by step
- Call tools when you need information or to perform actions
- Verify results before proceeding
- If a tool fails, consider alternatives or report the issue
- Your final answer should be comprehensive and in JSON format
"""

    async def run(
        self,
        state: AgentState,
        ctx: Optional[InstrumentedAgentContext] = None
    ) -> Dict[str, Any]:
        """
        Execute the ReAct reasoning loop.

        Args:
            state: Current agent state
            ctx: Optional instrumentation context

        Returns:
            State update dictionary
        """
        logger.info(f"Starting ReAct agent '{self.name}'")

        tools = self.get_tools()
        if not tools:
            logger.warning(f"Agent '{self.name}' has no tools, returning empty result")
            return {}

        # Build prompts
        system_prompt = self.build_full_system_prompt()
        task_prompt = self.build_task_prompt(state)

        logger.debug(f"Agent '{self.name}' task prompt: {task_prompt[:200]}...")

        try:
            # Call LLM with ReAct mode
            llm = get_llm_service()

            # Get step callback for real-time streaming
            step_callback = ctx.get_step_callback() if ctx else None

            # Use agent-specific model config (respects AGENT_CONFIG_PRESET)
            response = await llm.generate_with_tools_for_agent(
                agent_name=self.name,
                prompt=task_prompt,
                tools=tools,
                system_prompt=system_prompt,
                max_iterations=self.max_iterations,
                mode="react",
                tool_timeout=self.tool_timeout,
                step_callback=step_callback,
            )

            # Log ReAct trace
            logger.info(
                f"Agent '{self.name}' completed: "
                f"{response.iterations} iterations, "
                f"{len(response.tool_calls)} tool calls, "
                f"stop_reason={response.stop_reason}"
            )

            # Track metrics
            if ctx:
                ctx.set_llm_metrics(
                    model=response.model,
                    prompt_tokens=response.total_input_tokens,
                    completion_tokens=response.total_output_tokens,
                    latency_ms=response.total_latency_ms
                )

                # Track ReAct-specific metrics (non-fatal if fails)
                try:
                    self._track_react_metrics(ctx, response)
                except Exception as metrics_err:
                    logger.warning(f"Agent '{self.name}' failed to track ReAct metrics: {metrics_err}")

            # Parse final result
            result = self.parse_final_result(response, state)

            # Add metadata
            result["_react_trace"] = self._serialize_trace(response.react_trace)
            result["_llm_metrics"] = {
                "model": response.model,
                "prompt_tokens": response.total_input_tokens,
                "completion_tokens": response.total_output_tokens,
                "latency_ms": response.total_latency_ms,
                "iterations": response.iterations,
                "tool_calls": len(response.tool_calls)
            }

            return result

        except Exception as e:
            logger.error(f"ReAct agent '{self.name}' failed: {e}", exc_info=True)
            return {
                "_error": str(e),
                "_agent": self.name
            }

    def _track_react_metrics(
        self,
        ctx: InstrumentedAgentContext,
        response: ToolCallingResponse
    ) -> None:
        """Track ReAct-specific metrics in instrumentation."""
        # Track tool calls
        if response.tool_calls:
            tool_metrics = []
            for tc, tr in zip(response.tool_calls, response.tool_results):
                tool_metrics.append({
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "status": tr.status.value if tr else "unknown",
                    "latency_ms": tr.latency_ms if tr else 0
                })
            ctx.set_tool_metrics(tool_metrics)

        # Track ReAct-specific data
        if hasattr(ctx, 'set_react_metrics'):
            ctx.set_react_metrics(
                iterations=response.iterations,
                tool_calls=len(response.tool_calls),
                reasoning_trace=[
                    {"thought": step.thought[:200], "action": step.action.name if step.action else None}
                    for step in response.react_trace
                ]
            )

    def _serialize_trace(self, trace: List[ReActStep]) -> List[Dict]:
        """Serialize ReAct trace for storage."""
        serialized = []
        for step in trace:
            serialized.append({
                "iteration": step.iteration,
                "thought": step.thought,
                "action": {
                    "name": step.action.name,
                    "arguments": step.action.arguments
                } if step.action else None,
                "observation": step.observation[:500] if step.observation else None
            })
        return serialized


# ============================================================================
# Helper Functions
# ============================================================================

def extract_json_from_response(content: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response content.

    Handles multiple formats:
    - Pure JSON string
    - Markdown code blocks (```json ... ```)
    - JSON embedded in narrative text
    - Nested brace matching

    Args:
        content: Response content that may contain JSON

    Returns:
        Parsed JSON dict/list or None
    """
    if not content:
        return None

    # 1. Try direct parse (pure JSON)
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # 2. Try markdown code block extraction (```json ... ``` or ``` ... ```)
    import re
    code_block_patterns = [
        r'```json\s*\n?(.*?)\n?\s*```',  # ```json ... ```
        r'```\s*\n?(.*?)\n?\s*```',       # ``` ... ```
    ]
    for pattern in code_block_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1).strip())
                logger.debug("Extracted JSON from markdown code block")
                return result
            except json.JSONDecodeError:
                pass

    # 3. Try balanced brace extraction (finds the largest valid JSON object)
    first_brace = content.find("{")
    if first_brace != -1:
        # Walk forward matching braces to find the complete JSON object
        depth = 0
        in_string = False
        escape_next = False
        for i in range(first_brace, len(content)):
            c = content[i]
            if escape_next:
                escape_next = False
                continue
            if c == '\\' and in_string:
                escape_next = True
                continue
            if c == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    json_str = content[first_brace:i + 1]
                    try:
                        result = json.loads(json_str)
                        logger.debug(f"Extracted JSON via balanced brace matching (len={len(json_str)})")
                        return result
                    except json.JSONDecodeError as e:
                        logger.debug(f"Balanced brace extraction found braces but JSON invalid: {e}")
                        break

    # 4. Fallback: try simple first-brace to last-brace (less reliable)
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # 5. Try JSON array
    try:
        start = content.find("[")
        end = content.rfind("]") + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    logger.warning(
        f"extract_json_from_response: No valid JSON found "
        f"(content_len={len(content)}, has_braces={'{' in content}, "
        f"has_code_block={'```' in content}, preview={content[:200]}...)"
    )
    return None


def merge_tool_results(tool_results: List[Any]) -> Dict[str, Any]:
    """
    Merge results from multiple tool calls.

    Args:
        tool_results: List of ToolResult objects

    Returns:
        Merged dictionary of all results
    """
    merged = {}

    for tr in tool_results:
        if hasattr(tr, 'result') and tr.result:
            result = tr.result
            if isinstance(result, dict):
                merged.update(result)
            else:
                # Store non-dict results under tool name
                merged[tr.name] = result

    return merged
