"""V4 Algorithm Pipeline Graph — LangGraph StateGraph wiring.

6-Phase Architecture (14 nodes):

  Phase 0: START ──┬── input_analyzer ──┬── algo_phase0_merge
                   └── algo_dk_retriever ┘
  Phase 1: algo_game_concept_designer → algo_concept_validator ──[retry]──
  Phase 2: algo_graph_builder → algo_plan_validator ──[retry to concept]──
  Phase 3: ──[content_dispatch]── algo_scene_content_gen(s) → algo_content_merge
            → algo_content_validator ──[retry failed scenes]──
  Phase 4: ──[asset_dispatch]── algo_asset_worker(s) → algo_asset_merge ──[retry]──
  Phase 5: algo_blueprint_assembler (with blueprint validation) → END
"""

import inspect
from typing import Callable

from langgraph.graph import StateGraph, START, END

from app.agents.instrumentation import wrap_agent_with_instrumentation
from app.utils.logging_config import get_logger

# Phase 0
from app.v4.agents.input_analyzer import input_analyzer
from app.v4_algorithm.agents.dk_retriever import algo_dk_retriever
from app.v4_algorithm.merge_nodes import (
    algo_phase0_merge,
    algo_content_merge,
    algo_asset_merge,
)

# Phase 1
from app.v4_algorithm.agents.game_concept_designer import algo_game_concept_designer
from app.v4_algorithm.validators.concept_validator import algo_concept_validator

# Phase 2
from app.v4_algorithm.graph_builder import algo_graph_builder
from app.v4_algorithm.validators.plan_validator import algo_plan_validator

# Phase 3
from app.v4_algorithm.agents.scene_content_generator import algo_scene_content_gen
from app.v4_algorithm.validators.content_validator import algo_content_validator

# Phase 4
from app.v4_algorithm.agents.asset_worker import algo_asset_worker

# Phase 5
from app.v4_algorithm.agents.assembler_node import algo_blueprint_assembler

# Routers
from app.v4_algorithm.routers import (
    concept_router,
    plan_router,
    content_dispatch_router,
    content_retry_router,
    asset_dispatch_router,
    asset_retry_router,
)

from app.v4_algorithm.state import V4AlgorithmState

logger = get_logger("gamed_ai.v4_algorithm.graph")


# ── Instrumentation wrapper ───────────────────────────────────────


def _wrap(func: Callable, agent_name: str) -> Callable:
    """Wrap a node with instrumentation, handling sync/async."""
    if inspect.iscoroutinefunction(func):
        return wrap_agent_with_instrumentation(func, agent_name)

    async def async_wrapper(state: dict) -> dict:
        return func(state)

    async_wrapper.__name__ = getattr(func, "__name__", agent_name)
    async_wrapper.__doc__ = getattr(func, "__doc__", None)
    return wrap_agent_with_instrumentation(async_wrapper, agent_name)


async def _passthrough(state: dict) -> dict:
    """No-op passthrough node for dispatch points."""
    return {}


# ── Graph Construction ────────────────────────────────────────────


def create_v4_algorithm_graph(checkpointer=None):
    """Create and compile the V4 Algorithm pipeline graph.

    Args:
        checkpointer: Optional LangGraph checkpointer.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    builder = StateGraph(V4AlgorithmState)

    # ── Phase 0: Context Gathering (parallel from START) ──

    builder.add_node("input_analyzer", _wrap(input_analyzer, "v4a_input_analyzer"))
    builder.add_node("algo_dk_retriever", _wrap(algo_dk_retriever, "v4a_dk_retriever"))
    builder.add_node("algo_phase0_merge", _wrap(algo_phase0_merge, "v4a_phase0_merge"))

    builder.add_edge(START, "input_analyzer")
    builder.add_edge(START, "algo_dk_retriever")
    builder.add_edge("input_analyzer", "algo_phase0_merge")
    builder.add_edge("algo_dk_retriever", "algo_phase0_merge")

    # ── Phase 1: Game Concept Design (with retry loop) ──

    builder.add_node(
        "algo_game_concept_designer",
        _wrap(algo_game_concept_designer, "v4a_game_concept_designer"),
    )
    builder.add_node(
        "algo_concept_validator",
        _wrap(algo_concept_validator, "v4a_concept_validator"),
    )

    builder.add_edge("algo_phase0_merge", "algo_game_concept_designer")
    builder.add_edge("algo_game_concept_designer", "algo_concept_validator")
    builder.add_conditional_edges(
        "algo_concept_validator",
        concept_router,
        {"retry": "algo_game_concept_designer", "pass": "algo_graph_builder"},
    )

    # ── Phase 2: Graph Builder + Plan Validation (with retry loop) ──

    builder.add_node("algo_graph_builder", _wrap(algo_graph_builder, "v4a_graph_builder"))
    builder.add_node("algo_plan_validator", _wrap(algo_plan_validator, "v4a_plan_validator"))

    builder.add_edge("algo_graph_builder", "algo_plan_validator")
    builder.add_conditional_edges(
        "algo_plan_validator",
        plan_router,
        {"retry": "algo_game_concept_designer", "pass": "content_dispatch"},
    )

    # ── Phase 3: Content Generation (parallel Send per scene) ──

    builder.add_node("content_dispatch", _wrap(_passthrough, "v4a_content_dispatch"))
    builder.add_node("algo_scene_content_gen", _wrap(algo_scene_content_gen, "v4a_scene_content_gen"))
    builder.add_node("algo_content_merge", _wrap(algo_content_merge, "v4a_content_merge"))
    builder.add_node(
        "algo_content_validator",
        _wrap(algo_content_validator, "v4a_content_validator"),
    )

    builder.add_conditional_edges(
        "content_dispatch",
        content_dispatch_router,
        ["algo_scene_content_gen"],
    )
    builder.add_edge("algo_scene_content_gen", "algo_content_merge")
    builder.add_edge("algo_content_merge", "algo_content_validator")
    builder.add_conditional_edges(
        "algo_content_validator",
        content_retry_router,
        # Can route to: asset_dispatch passthrough, or Send back to content gen
        ["algo_scene_content_gen", "asset_dispatch"],
    )

    # ── Phase 4: Asset Generation (parallel Send — scenes needing visuals) ──

    builder.add_node("asset_dispatch", _wrap(_passthrough, "v4a_asset_dispatch"))
    builder.add_node("algo_asset_worker", _wrap(algo_asset_worker, "v4a_asset_worker"))
    builder.add_node("algo_asset_merge", _wrap(algo_asset_merge, "v4a_asset_merge"))

    builder.add_conditional_edges(
        "asset_dispatch",
        asset_dispatch_router,
        ["algo_asset_worker", "algo_blueprint_assembler"],
    )
    builder.add_edge("algo_asset_worker", "algo_asset_merge")
    builder.add_conditional_edges(
        "algo_asset_merge",
        asset_retry_router,
        ["algo_asset_worker", "algo_blueprint_assembler"],
    )

    # ── Phase 5: Blueprint Assembly → END ──

    builder.add_node(
        "algo_blueprint_assembler",
        _wrap(algo_blueprint_assembler, "v4a_blueprint_assembler"),
    )
    builder.add_edge("algo_blueprint_assembler", END)

    # ── Compile ──

    compiled = builder.compile(checkpointer=checkpointer)
    logger.info("V4 Algorithm graph compiled (6-phase, 14 nodes)")
    return compiled
