"""
Tools package for GamED.AI v2

This package provides tool implementations for agentic workflows.
Tools are callable functions that agents can invoke to perform specific tasks.

Tool Categories:
- Research tools: Domain knowledge retrieval, web search
- Vision tools: Image analysis, zone detection (Gemini)
- Blueprint tools: Validation, spec generation
- Render tools: SVG generation, asset rendering
"""

from app.tools.registry import (
    ToolRegistry,
    get_tool_registry,
    AGENT_TOOL_MAPPING,
)

__all__ = [
    "ToolRegistry",
    "get_tool_registry",
    "AGENT_TOOL_MAPPING",
]
