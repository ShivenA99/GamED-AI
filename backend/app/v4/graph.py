"""V4 Pipeline Graph — LangGraph StateGraph wiring.

3-Stage Creative Cascade Architecture (22 nodes, 7 phases):

  Phase 0: START ──┬── input_analyzer ──┬── phase0_merge
                   └── dk_retriever  ───┘
  Phase 1a: game_concept_designer → concept_validator ──[concept_router]──┐
                  ↑                                      "retry"          │
                  └───────────────────────────────────────────────────────┘
                                                         "pass" ↓
  Phase 1b: ──[scene_design_send_router]──
            ↙  Send(scene_designer)  ↘
          scene_designer(s) → scene_design_merge ──[scene_design_retry_router]──┐
                  ↑                                 Send retry                  │
                  └────────────────────────────────────────────────────────────┘
                                                    "graph_builder" ↓
  Graph Builder: graph_builder → game_plan_validator ──[design_router]──┐
                  ↑                                     "retry"         │
                  └────────────────────────────────────────────────────┘
                                                        "pass" ↓
  Phase 2a: ──[content_dispatch_router]──
            ↙  Send(content_generator)  ↘
          content_generator(s) → content_merge → item_asset_worker
                                                       ↓
  Phase 2b: ──[interaction_dispatch_router]──
            ↙  Send(interaction_designer)  ↘
          interaction_designer(s) → interaction_merge
                                        ↓
  Phase 3: ──[asset_send_router]──
           ↙  Send(asset_worker)  ↘  "blueprint_assembler" (no diagrams)
         asset_worker(s) → asset_merge ──[asset_retry_router]──┐
                  ↑                       Send retry            │
                  └────────────────────────────────────────────┘
                                     "blueprint_assembler" ↓
  Phase 4: blueprint_assembler → END

Nodes: input_analyzer, dk_retriever, phase0_merge,
       game_concept_designer, concept_validator,
       scene_designer, scene_design_merge,
       graph_builder, game_plan_validator,
       content_generator, content_merge, item_asset_worker,
       interaction_designer, interaction_merge,
       asset_worker, asset_merge,
       blueprint_assembler (17 node types, parallel Send workers)
"""

import inspect
from typing import Callable

from langgraph.graph import StateGraph, START, END

from app.agents.instrumentation import wrap_agent_with_instrumentation
from app.utils.logging_config import get_logger

# Phase 0
from app.v4.agents.input_analyzer import input_analyzer
from app.v4.agents.dk_retriever import dk_retriever
from app.v4.merge_nodes import (
    phase0_merge,
    scene_design_merge,
    content_merge,
    interaction_merge,
    asset_merge,
)

# Phase 1a
from app.v4.agents.game_concept_designer import game_concept_designer
from app.v4.validators.concept_validator import validate_game_concept

# Phase 1b
from app.v4.agents.scene_designer import scene_designer

# Graph builder
from app.v4.graph_builder import graph_builder_node
from app.v4.schemas.game_plan import GamePlan
from app.v4.validators.game_plan_validator import validate_game_plan

# Phase 2
from app.v4.agents.content_generator import content_generator
from app.v4.agents.item_asset_worker import item_asset_worker
from app.v4.agents.interaction_designer import interaction_designer

# Phase 3
from app.v4.agents.asset_dispatcher import asset_worker

# Phase 4
from app.v4.agents.assembler_node import assembler_node

# Routers
from app.v4.routers import (
    concept_router,
    scene_design_send_router,
    scene_design_retry_router,
    content_dispatch_router,
    interaction_dispatch_router,
    asset_send_router,
    asset_retry_router,
    design_router,
)

from app.v4.schemas.validation import ValidationIssue, ValidationResult
from app.v4.state import V4MainState

logger = get_logger("gamed_ai.v4.graph")


# ── Validator wrapper nodes (deterministic — no LLM) ──────────────


async def concept_validator_node(state: dict) -> dict:
    """Validate game concept after game_concept_designer.

    Reads: game_concept
    Writes: concept_validation
    """
    from app.v4.schemas.game_concept import GameConcept

    concept_raw = state.get("game_concept")
    if not concept_raw:
        return {
            "concept_validation": {
                "passed": False,
                "score": 0.0,
                "issues": [{"severity": "error", "message": "No game_concept in state"}],
            },
        }

    try:
        concept = GameConcept(**concept_raw)
        result = validate_game_concept(concept)
        return {"concept_validation": result.model_dump()}
    except Exception as e:
        logger.error(f"Concept validation error: {e}")
        return {
            "concept_validation": {
                "passed": False,
                "score": 0.0,
                "issues": [{"severity": "error", "message": f"Validation error: {e}"}],
            },
        }


async def game_plan_validator_node(state: dict) -> dict:
    """Validate game plan and compute max_score fields.

    Reads: game_plan
    Writes: game_plan (with computed scores), design_validation
    """
    game_plan_raw = state.get("game_plan")

    if not game_plan_raw:
        return {
            "design_validation": {
                "passed": False,
                "score": 0.0,
                "issues": [{"severity": "error", "message": "No game_plan in state"}],
            },
        }

    try:
        plan = GamePlan(**game_plan_raw)
        result = validate_game_plan(plan)

        return {
            "game_plan": plan.model_dump(),
            "design_validation": result.model_dump(),
        }
    except Exception as e:
        logger.error(f"Game plan validation error: {e}")
        return {
            "design_validation": {
                "passed": False,
                "score": 0.0,
                "issues": [{"severity": "error", "message": f"Validation error: {e}"}],
            },
        }


# ── V4 instrumentation wrapper ────────────────────────────────────


def _v4_wrap(func: Callable, agent_name: str) -> Callable:
    """Wrap a V4 node with instrumentation, handling sync/async."""
    if inspect.iscoroutinefunction(func):
        return wrap_agent_with_instrumentation(func, agent_name)

    # Convert sync → async for the instrumentation wrapper
    async def async_wrapper(state: dict) -> dict:
        return func(state)

    async_wrapper.__name__ = getattr(func, "__name__", agent_name)
    async_wrapper.__doc__ = getattr(func, "__doc__", None)
    return wrap_agent_with_instrumentation(async_wrapper, agent_name)


# ── Graph Construction ─────────────────────────────────────────────


def create_v4_graph(checkpointer=None):
    """Create and compile the V4 pipeline graph (3-stage creative cascade).

    Args:
        checkpointer: Optional LangGraph checkpointer (AsyncSqliteSaver, etc.)

    Returns:
        Compiled StateGraph ready for invocation.
    """
    builder = StateGraph(V4MainState)

    # ── Phase 0: Context Gathering (parallel fan-out from START) ──

    builder.add_node("input_analyzer", _v4_wrap(input_analyzer, "v4_input_analyzer"))
    builder.add_node("dk_retriever", _v4_wrap(dk_retriever, "v4_dk_retriever"))
    builder.add_node("phase0_merge", _v4_wrap(phase0_merge, "v4_phase0_merge"))

    builder.add_edge(START, "input_analyzer")
    builder.add_edge(START, "dk_retriever")
    builder.add_edge("input_analyzer", "phase0_merge")
    builder.add_edge("dk_retriever", "phase0_merge")

    # ── Phase 1a: Game Concept Design (with retry loop) ──

    builder.add_node(
        "game_concept_designer",
        _v4_wrap(game_concept_designer, "v4_game_concept_designer"),
    )
    builder.add_node(
        "concept_validator",
        _v4_wrap(concept_validator_node, "v4_concept_validator"),
    )

    builder.add_edge("phase0_merge", "game_concept_designer")
    builder.add_edge("game_concept_designer", "concept_validator")
    builder.add_conditional_edges(
        "concept_validator",
        concept_router,
        {"retry": "game_concept_designer", "pass": "scene_design_send"},
    )

    # ── Phase 1b: Scene Design (parallel Send + merge + retry) ──

    # scene_design_send is a passthrough that triggers the router
    builder.add_node("scene_design_send", _v4_wrap(_passthrough, "v4_scene_design_send"))
    builder.add_node("scene_designer", _v4_wrap(scene_designer, "v4_scene_designer"))
    builder.add_node(
        "scene_design_merge",
        _v4_wrap(scene_design_merge, "v4_scene_design_merge"),
    )

    # scene_design_send → Send(scene_designer, ...) per scene
    builder.add_conditional_edges(
        "scene_design_send",
        scene_design_send_router,
        ["scene_designer"],
    )
    builder.add_edge("scene_designer", "scene_design_merge")

    # scene_design_merge → retry or graph_builder
    builder.add_conditional_edges(
        "scene_design_merge",
        scene_design_retry_router,
        ["scene_designer", "graph_builder"],
    )

    # ── Graph Builder + Validation (with retry loop) ──

    builder.add_node("graph_builder", _v4_wrap(graph_builder_node, "v4_graph_builder"))
    builder.add_node(
        "game_plan_validator",
        _v4_wrap(game_plan_validator_node, "v4_game_plan_validator"),
    )

    builder.add_edge("graph_builder", "game_plan_validator")
    builder.add_conditional_edges(
        "game_plan_validator",
        design_router,
        {"retry": "graph_builder", "pass": "content_dispatch"},
    )

    # ── Phase 2a: Content Generation (parallel Send + merge) ──

    builder.add_node("content_dispatch", _v4_wrap(_passthrough, "v4_content_dispatch"))
    builder.add_node(
        "content_generator",
        _v4_wrap(content_generator, "v4_content_generator"),
    )
    builder.add_node("content_merge", _v4_wrap(content_merge, "v4_content_merge"))
    builder.add_node(
        "item_asset_worker",
        _v4_wrap(item_asset_worker, "v4_item_asset_worker"),
    )

    builder.add_conditional_edges(
        "content_dispatch",
        content_dispatch_router,
        ["content_generator"],
    )
    builder.add_edge("content_generator", "content_merge")
    builder.add_edge("content_merge", "item_asset_worker")

    # ── Phase 2b: Interaction Design (parallel Send + merge) ──

    builder.add_node(
        "interaction_designer",
        _v4_wrap(interaction_designer, "v4_interaction_designer"),
    )
    builder.add_node(
        "interaction_merge",
        _v4_wrap(interaction_merge, "v4_interaction_merge"),
    )

    builder.add_conditional_edges(
        "item_asset_worker",
        interaction_dispatch_router,
        ["interaction_designer", "interaction_merge"],
    )
    builder.add_edge("interaction_designer", "interaction_merge")

    # ── Phase 3: Asset Dispatch (parallel Send + merge + retry) ──

    builder.add_node("asset_worker", _v4_wrap(asset_worker, "v4_asset_worker"))
    builder.add_node("asset_merge", _v4_wrap(asset_merge, "v4_asset_merge"))

    builder.add_conditional_edges(
        "interaction_merge", asset_send_router,
        ["asset_worker", "blueprint_assembler"],
    )
    builder.add_edge("asset_worker", "asset_merge")
    builder.add_conditional_edges(
        "asset_merge", asset_retry_router,
        ["asset_worker", "blueprint_assembler"],
    )

    # ── Phase 4: Assembly → END ──

    builder.add_node(
        "blueprint_assembler", _v4_wrap(assembler_node, "v4_assembler"),
    )
    builder.add_edge("blueprint_assembler", END)

    # ── Compile ──

    compiled = builder.compile(checkpointer=checkpointer)
    logger.info("V4 graph compiled successfully (3-stage creative cascade)")
    return compiled


# ── Legacy 9-node graph (kept for backward compat) ─────────────────


def create_v4_graph_legacy(checkpointer=None):
    """Create the original 9-node V4 graph (pre-cascade).

    Kept for backward compatibility and A/B testing.
    Uses single game_designer + sequential content_build.
    """
    from app.v4.agents.game_designer import game_designer
    from app.v4.agents.content_builder import content_build_node

    builder = StateGraph(V4MainState)

    # Phase 0
    builder.add_node("input_analyzer", _v4_wrap(input_analyzer, "v4_input_analyzer"))
    builder.add_node("dk_retriever", _v4_wrap(dk_retriever, "v4_dk_retriever"))
    builder.add_node("phase0_merge", _v4_wrap(phase0_merge, "v4_phase0_merge"))
    builder.add_edge(START, "input_analyzer")
    builder.add_edge(START, "dk_retriever")
    builder.add_edge("input_analyzer", "phase0_merge")
    builder.add_edge("dk_retriever", "phase0_merge")

    # Phase 1
    builder.add_node("game_designer", _v4_wrap(game_designer, "v4_game_designer"))
    builder.add_node("game_plan_validator", _v4_wrap(game_plan_validator_node, "v4_game_plan_validator"))
    builder.add_edge("phase0_merge", "game_designer")
    builder.add_edge("game_designer", "game_plan_validator")
    builder.add_conditional_edges("game_plan_validator", design_router, {"retry": "game_designer", "pass": "content_build"})

    # Phase 2
    builder.add_node("content_build", _v4_wrap(content_build_node, "v4_content_builder"))

    # Phase 3
    builder.add_node("asset_worker", _v4_wrap(asset_worker, "v4_asset_worker"))
    builder.add_node("asset_merge", _v4_wrap(asset_merge, "v4_asset_merge"))
    from app.v4.routers import asset_send_router as legacy_asset_send, asset_retry_router as legacy_asset_retry
    builder.add_conditional_edges("content_build", legacy_asset_send, ["asset_worker", "blueprint_assembler"])
    builder.add_edge("asset_worker", "asset_merge")
    builder.add_conditional_edges("asset_merge", legacy_asset_retry, ["asset_worker", "blueprint_assembler"])

    # Phase 4
    builder.add_node("blueprint_assembler", _v4_wrap(assembler_node, "v4_assembler"))
    builder.add_edge("blueprint_assembler", END)

    compiled = builder.compile(checkpointer=checkpointer)
    logger.info("V4 legacy graph compiled (9-node)")
    return compiled


# ── Helpers ────────────────────────────────────────────────────────


async def _passthrough(state: dict) -> dict:
    """No-op passthrough node used as a dispatch point for conditional edges."""
    return {}
