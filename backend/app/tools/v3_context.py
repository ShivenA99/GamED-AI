"""
V3 Pipeline Context Injection Layer

Uses contextvars to inject pipeline state into tool implementations
without passing it through the LLM. Each tool reads context via
get_v3_tool_context() to access upstream state fields.

Usage:
    # In agent wrapper (before running ReAct loop):
    set_v3_tool_context(state)

    # In tool implementation:
    ctx = get_v3_tool_context()
    domain_knowledge = ctx.get("domain_knowledge", "")
"""

from __future__ import annotations

import contextvars
from typing import Any, Dict, List, Optional

_v3_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "v3_tool_context", default={}
)


def set_v3_tool_context(state: Dict[str, Any]) -> None:
    """Set pipeline state for tool access. Called before each ReAct agent runs."""
    dk = state.get("domain_knowledge", "")
    dk_dict = dk if isinstance(dk, dict) else {}
    _v3_context.set({
        "question": state.get("enhanced_question") or state.get("question_text", ""),
        "subject": state.get("subject", ""),
        "blooms_level": state.get("blooms_level", "understand"),
        "domain_knowledge": dk,
        "canonical_labels": state.get("canonical_labels", []),
        "learning_objectives": state.get("learning_objectives", []),
        "pedagogical_context": state.get("pedagogical_context"),
        "game_design_v3": state.get("game_design_v3"),
        "scene_specs_v3": state.get("scene_specs_v3"),
        "interaction_specs_v3": state.get("interaction_specs_v3"),
        "generated_assets_v3": state.get("generated_assets_v3"),
        "run_id": state.get("_run_id", ""),
        "output_dir": state.get("_output_dir", ""),
        # Promoted mechanic-relevant DK fields for tool access
        "sequence_flow_data": dk_dict.get("sequence_flow_data"),
        "content_characteristics": dk_dict.get("content_characteristics"),
        "hierarchical_relationships": dk_dict.get("hierarchical_relationships"),
        "label_descriptions": dk_dict.get("label_descriptions"),
        "comparison_data": dk_dict.get("comparison_data"),
        "term_definitions": dk_dict.get("term_definitions"),
        "causal_relationships": dk_dict.get("causal_relationships"),
        "spatial_data": dk_dict.get("spatial_data"),
        "process_steps": dk_dict.get("process_steps"),
        "hierarchical_data": dk_dict.get("hierarchical_data"),
    })


def get_v3_tool_context() -> Dict[str, Any]:
    """Get pipeline context for tool implementations."""
    return _v3_context.get()
