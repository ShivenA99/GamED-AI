"""
ReAct Loop Implementation for HAD Orchestrators

Provides a reusable ReAct-style reasoning loop with:
- Step-by-step reasoning trace capture
- Tool execution with observation recording
- Configurable max iterations
- Structured trace output for UI visualization

Used by:
- zone_planner: Image acquisition + zone detection reasoning
- game_orchestrator: Game design decision reasoning
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import json

from pydantic import BaseModel, Field

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.had.react_loop")


# =============================================================================
# Trace Types
# =============================================================================

class StepType(str, Enum):
    """Types of steps in a ReAct trace."""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    DECISION = "decision"
    ERROR = "error"
    RESULT = "result"


class ReActStep(BaseModel):
    """A single step in the ReAct reasoning trace."""
    type: StepType
    content: str
    tool: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    duration_ms: Optional[int] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Optional[Dict[str, Any]] = None


class ReActTrace(BaseModel):
    """Complete trace of a ReAct reasoning session."""
    phase: str = Field(description="Phase name (e.g., 'image_acquisition', 'zone_detection')")
    iterations: int = 0
    max_iterations: int = 6
    steps: List[ReActStep] = Field(default_factory=list)
    final_result: Optional[Any] = None
    success: bool = False
    total_duration_ms: int = 0
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    def add_thought(self, content: str, metadata: Optional[Dict] = None) -> "ReActTrace":
        """Add a thought step to the trace."""
        self.steps.append(ReActStep(
            type=StepType.THOUGHT,
            content=content,
            metadata=metadata,
        ))
        return self

    def add_action(
        self,
        tool: str,
        tool_args: Dict[str, Any],
        content: Optional[str] = None,
    ) -> "ReActTrace":
        """Add an action step to the trace."""
        self.steps.append(ReActStep(
            type=StepType.ACTION,
            content=content or f"Calling {tool}",
            tool=tool,
            tool_args=tool_args,
        ))
        return self

    def add_observation(
        self,
        content: str,
        result: Any = None,
        duration_ms: int = 0,
        tool: Optional[str] = None,
    ) -> "ReActTrace":
        """Add an observation step to the trace."""
        self.steps.append(ReActStep(
            type=StepType.OBSERVATION,
            content=content,
            result=result,
            duration_ms=duration_ms,
            tool=tool,
        ))
        return self

    def add_decision(self, content: str, metadata: Optional[Dict] = None) -> "ReActTrace":
        """Add a decision step to the trace."""
        self.steps.append(ReActStep(
            type=StepType.DECISION,
            content=content,
            metadata=metadata,
        ))
        return self

    def add_error(self, content: str, metadata: Optional[Dict] = None) -> "ReActTrace":
        """Add an error step to the trace."""
        self.steps.append(ReActStep(
            type=StepType.ERROR,
            content=content,
            metadata=metadata,
        ))
        return self

    def add_result(self, content: str, result: Any = None) -> "ReActTrace":
        """Add a final result step to the trace."""
        self.steps.append(ReActStep(
            type=StepType.RESULT,
            content=content,
            result=result,
        ))
        self.final_result = result
        return self

    def complete(self, success: bool = True) -> "ReActTrace":
        """Mark the trace as complete."""
        self.success = success
        self.completed_at = datetime.utcnow().isoformat()
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for JSON serialization."""
        return {
            "phase": self.phase,
            "iterations": self.iterations,
            "max_iterations": self.max_iterations,
            "steps": [step.model_dump() for step in self.steps],
            "final_result": self.final_result,
            "success": self.success,
            "total_duration_ms": self.total_duration_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# =============================================================================
# Tool Registry
# =============================================================================

@dataclass
class ToolDefinition:
    """Definition of a tool available in the ReAct loop."""
    name: str
    description: str
    function: Callable
    input_schema: Optional[Dict[str, Any]] = None
    output_description: Optional[str] = None


class ToolRegistry:
    """Registry of tools available for ReAct reasoning."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        function: Callable,
        input_schema: Optional[Dict[str, Any]] = None,
        output_description: Optional[str] = None,
    ) -> "ToolRegistry":
        """Register a tool."""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            function=function,
            input_schema=input_schema,
            output_description=output_description,
        )
        return self

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def format_for_prompt(self) -> str:
        """Format tools for inclusion in an LLM prompt."""
        if not self._tools:
            return "No tools available."

        lines = ["Available Tools:"]
        for tool in self._tools.values():
            lines.append(f"\n- **{tool.name}**: {tool.description}")
            if tool.input_schema:
                lines.append(f"  Parameters: {json.dumps(tool.input_schema, indent=2)}")
            if tool.output_description:
                lines.append(f"  Returns: {tool.output_description}")

        return "\n".join(lines)

    async def execute(
        self,
        name: str,
        args: Dict[str, Any],
        trace: Optional[ReActTrace] = None,
    ) -> Any:
        """Execute a tool and optionally record in trace."""
        tool = self.get(name)
        if not tool:
            error_msg = f"Tool not found: {name}"
            if trace:
                trace.add_error(error_msg)
            raise ValueError(error_msg)

        start_time = time.time()

        try:
            # Execute tool (support both sync and async)
            if asyncio.iscoroutinefunction(tool.function):
                result = await tool.function(**args)
            else:
                result = tool.function(**args)

            duration_ms = int((time.time() - start_time) * 1000)

            # Record observation
            if trace:
                # Summarize result for display
                result_summary = _summarize_result(result)
                trace.add_observation(
                    content=result_summary,
                    result=result,
                    duration_ms=duration_ms,
                    tool=name,
                )

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Tool {name} failed: {str(e)}"

            if trace:
                trace.add_error(error_msg, metadata={"duration_ms": duration_ms})

            logger.error(error_msg, exc_info=True)
            raise


def _summarize_result(result: Any, max_length: int = 200) -> str:
    """Create a brief summary of a tool result for display."""
    if result is None:
        return "No result returned"

    if hasattr(result, 'success'):
        # Pydantic model with success field
        if hasattr(result, 'error') and result.error:
            return f"Failed: {result.error}"

        parts = [f"Success: {result.success}"]

        # Add key counts/summaries
        if hasattr(result, 'zones') and result.zones:
            parts.append(f"{len(result.zones)} zones detected")
        if hasattr(result, 'images') and result.images:
            parts.append(f"{len(result.images)} images found")
        if hasattr(result, 'selected_image_path') and result.selected_image_path:
            parts.append(f"Image: {result.selected_image_path}")

        return ", ".join(parts)

    if isinstance(result, dict):
        # Dictionary result
        keys = list(result.keys())[:5]
        return f"Dict with keys: {keys}"

    if isinstance(result, list):
        return f"List with {len(result)} items"

    if isinstance(result, str):
        if len(result) > max_length:
            return result[:max_length] + "..."
        return result

    # Default: convert to string and truncate
    s = str(result)
    if len(s) > max_length:
        return s[:max_length] + "..."
    return s


# =============================================================================
# ReAct Loop Runner
# =============================================================================

@dataclass
class ReActLoopConfig:
    """Configuration for a ReAct loop execution."""
    phase: str
    max_iterations: int = 6
    stop_on_success: bool = True
    log_steps: bool = True


async def run_react_loop(
    config: ReActLoopConfig,
    tools: ToolRegistry,
    initial_thought: str,
    decision_callback: Callable[[ReActTrace, int], Optional[Dict[str, Any]]],
) -> ReActTrace:
    """
    Run a ReAct-style reasoning loop.

    The decision_callback is called on each iteration and should return:
    - None: Stop the loop (success)
    - {"action": "tool_name", "args": {...}}: Execute a tool
    - {"thought": "reasoning..."}: Add a thought and continue

    Args:
        config: Loop configuration
        tools: Registry of available tools
        initial_thought: Starting thought for the reasoning
        decision_callback: Callback to decide next action based on trace

    Returns:
        Complete ReActTrace with all steps and results
    """
    trace = ReActTrace(
        phase=config.phase,
        max_iterations=config.max_iterations,
    )

    start_time = time.time()

    # Add initial thought
    trace.add_thought(initial_thought)

    if config.log_steps:
        logger.info(f"[{config.phase}] Starting ReAct loop: {initial_thought}")

    for iteration in range(config.max_iterations):
        trace.iterations = iteration + 1

        try:
            # Get next decision from callback
            decision = decision_callback(trace, iteration)

            if decision is None:
                # Success - stop loop
                if config.log_steps:
                    logger.info(f"[{config.phase}] Iteration {iteration + 1}: Decision complete")
                break

            if "thought" in decision:
                # Add thought and continue
                trace.add_thought(decision["thought"], decision.get("metadata"))
                if config.log_steps:
                    logger.info(f"[{config.phase}] Iteration {iteration + 1}: Thought - {decision['thought'][:100]}")
                continue

            if "action" in decision:
                # Execute tool
                tool_name = decision["action"]
                tool_args = decision.get("args", {})

                trace.add_action(tool_name, tool_args)

                if config.log_steps:
                    logger.info(f"[{config.phase}] Iteration {iteration + 1}: Action - {tool_name}")

                # Execute the tool
                result = await tools.execute(tool_name, tool_args, trace)

                # Check if this is a successful terminal result
                if config.stop_on_success and _is_success_result(result):
                    trace.add_result(
                        f"Successfully completed with {tool_name}",
                        result=result,
                    )
                    break

            if "decision" in decision:
                # Add a decision step
                trace.add_decision(decision["decision"], decision.get("metadata"))
                if config.log_steps:
                    logger.info(f"[{config.phase}] Iteration {iteration + 1}: Decision - {decision['decision'][:100]}")

        except Exception as e:
            trace.add_error(f"Iteration {iteration + 1} failed: {str(e)}")
            logger.error(f"[{config.phase}] Iteration {iteration + 1} error: {e}", exc_info=True)

            # Continue to next iteration unless it's a critical error
            if iteration >= config.max_iterations - 1:
                break

    # Complete the trace
    trace.total_duration_ms = int((time.time() - start_time) * 1000)
    trace.complete(success=trace.final_result is not None)

    if config.log_steps:
        logger.info(
            f"[{config.phase}] ReAct loop complete: "
            f"iterations={trace.iterations}, success={trace.success}, "
            f"duration={trace.total_duration_ms}ms"
        )

    return trace


def _is_success_result(result: Any) -> bool:
    """Check if a result indicates success."""
    if result is None:
        return False

    if hasattr(result, 'success'):
        return result.success

    if isinstance(result, dict):
        return result.get('success', False)

    return True


# =============================================================================
# Simplified Trace Builder (for non-LLM orchestrated flows)
# =============================================================================

class TraceBuilder:
    """
    Simple trace builder for capturing reasoning steps without full ReAct loop.

    Used when the orchestrator follows a fixed workflow but still wants to
    capture reasoning trace for observability.
    """

    def __init__(self, phase: str):
        self.trace = ReActTrace(phase=phase)
        self._start_time = time.time()

    def thought(self, content: str, **metadata) -> "TraceBuilder":
        """Record a thought/reasoning step."""
        self.trace.add_thought(content, metadata if metadata else None)
        return self

    def action(self, tool: str, args: Dict[str, Any], description: Optional[str] = None) -> "TraceBuilder":
        """Record an action being taken."""
        self.trace.add_action(tool, args, description)
        return self

    def observation(
        self,
        content: str,
        result: Any = None,
        tool: Optional[str] = None,
        duration_ms: int = 0,
    ) -> "TraceBuilder":
        """Record an observation from an action."""
        self.trace.add_observation(content, result, duration_ms, tool)
        return self

    def decision(self, content: str, **metadata) -> "TraceBuilder":
        """Record a decision made."""
        self.trace.add_decision(content, metadata if metadata else None)
        return self

    def error(self, content: str, **metadata) -> "TraceBuilder":
        """Record an error."""
        self.trace.add_error(content, metadata if metadata else None)
        return self

    def result(self, content: str, result: Any = None) -> "TraceBuilder":
        """Record the final result."""
        self.trace.add_result(content, result)
        return self

    def complete(self, success: bool = True) -> ReActTrace:
        """Complete and return the trace."""
        self.trace.total_duration_ms = int((time.time() - self._start_time) * 1000)
        self.trace.complete(success)
        return self.trace

    def to_dict(self) -> Dict[str, Any]:
        """Get trace as dictionary."""
        return self.trace.to_dict()
