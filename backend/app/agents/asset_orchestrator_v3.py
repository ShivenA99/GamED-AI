"""
Asset Orchestrator v3 — Manages asset generation from GameDesignV3 + AssetGraph.

NOT a ReAct agent — deterministic orchestration of spec building → worker dispatch.
No LLM call needed; the AssetGraph + AssetManifest fully determine what to generate.

Flow:
1. Build AssetManifest from GameDesignV3 + AssetGraph (asset_spec_builder)
2. Execute workers in dependency order (execute_manifest)
3. Collect results into state

Reads: game_design_v3, asset_graph_v3
Writes: asset_manifest_v3, generated_assets_v3, diagram_image, diagram_zones
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.asset_spec import AssetManifest, AssetType, WorkerType
from app.agents.schemas.asset_graph import AssetGraph
from app.agents.schemas.game_design_v3 import GameDesignV3
from app.agents.asset_spec_builder import build_asset_manifest
from app.agents.workflows.asset_workers import (
    WorkerContext,
    WorkerResult,
    execute_manifest,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.asset_orchestrator_v3")


def _build_asset_graph(state: AgentState) -> Optional[AssetGraph]:
    """Extract or build AssetGraph from state."""
    raw = state.get("asset_graph_v3")
    if raw is None:
        return None
    if isinstance(raw, AssetGraph):
        return raw
    if isinstance(raw, dict):
        return AssetGraph.model_validate(raw)
    return None


def _build_game_design(state: AgentState) -> Optional[GameDesignV3]:
    """Extract GameDesignV3 from state."""
    raw = state.get("game_design_v3")
    if raw is None:
        return None
    if isinstance(raw, GameDesignV3):
        return raw
    if isinstance(raw, dict):
        return GameDesignV3.model_validate(raw)
    return None


async def asset_orchestrator_v3_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Asset Orchestrator v3 — deterministic asset generation pipeline.

    Reads: game_design_v3, asset_graph_v3
    Writes: asset_manifest_v3, generated_assets_v3, diagram_image, diagram_zones
    """
    logger.info("AssetOrchestratorV3: Starting")

    design = _build_game_design(state)
    if not design:
        logger.error("AssetOrchestratorV3: No game_design_v3 in state")
        return {
            **state,
            "current_agent": "asset_orchestrator_v3",
            "generated_assets_v3": {},
            "_error": "No game_design_v3 in state",
        }

    graph = _build_asset_graph(state)
    if not graph:
        logger.warning("AssetOrchestratorV3: No asset_graph_v3, building from design")
        from app.agents.schemas.asset_graph import AssetGraph
        graph = AssetGraph.from_game_design(design)

    # Step 1: Build manifest
    if ctx:
        ctx.emit_live_step("thought", f"Building asset manifest from {len(design.scenes)} scenes")
    manifest = build_asset_manifest(design, graph)
    logger.info(
        f"AssetOrchestratorV3: Built manifest with {len(manifest.specs)} specs, "
        f"order={manifest.generation_order}"
    )
    if ctx:
        ctx.emit_live_step("observation", f"Manifest ready: {len(manifest.specs)} assets to generate")

    # Step 2: Create worker context
    run_id = state.get("_run_id") or state.get("process_id") or str(uuid.uuid4())[:8]
    output_dir = os.path.join("assets", run_id)
    os.makedirs(output_dir, exist_ok=True)

    worker_ctx = WorkerContext(
        run_id=run_id,
        output_dir=output_dir,
        base_url=f"/api/assets/{run_id}",
        existing_assets={},
        diagram_image_path=state.get("diagram_image"),
        config={"zone_data": {}},
    )

    # Step 3: Execute manifest with progress tracking
    if ctx:
        ctx.emit_live_step("action", f"Executing {len(manifest.specs)} workers in dependency order", tool="execute_manifest")

    # Progress callback for per-worker streaming
    async def _on_worker_progress(asset_id: str, status: str, detail: str = ""):
        if ctx:
            ctx.emit_live_step(
                "observation" if status == "complete" else "action",
                f"[{asset_id}] {status}: {detail}" if detail else f"[{asset_id}] {status}",
                tool=asset_id,
            )

    results = await execute_manifest(manifest, worker_ctx, on_progress=_on_worker_progress)

    # Step 4: Collect outputs
    generated_assets: Dict[str, Any] = {}
    diagram_image = state.get("diagram_image")
    diagram_zones = state.get("diagram_zones", [])

    for asset_id, result in results.items():
        spec = manifest.get_spec(asset_id)
        if not spec:
            continue

        entry = {
            "asset_id": asset_id,
            "success": result.success,
            "asset_type": spec.asset_type.value,
            "worker": spec.worker.value,
            "path": result.path,
            "url": result.url,
            "data": result.data,
            "error": result.error,
            "latency_ms": result.latency_ms,
            "cost_usd": result.cost_usd,
        }
        generated_assets[asset_id] = entry

        # Extract primary diagram image
        if result.success and spec.asset_type == AssetType.DIAGRAM and result.path:
            diagram_image = result.path

        # Extract zones
        if result.success and spec.asset_type == AssetType.ZONE_OVERLAY and result.data:
            zones = result.data.get("zones", [])
            if zones:
                diagram_zones = zones

    # Compute summary
    total = len(results)
    succeeded = sum(1 for r in results.values() if r.success)
    total_cost = sum(r.cost_usd for r in results.values())
    total_latency = sum(r.latency_ms for r in results.values())

    logger.info(
        f"AssetOrchestratorV3: Complete — "
        f"{succeeded}/{total} succeeded, "
        f"cost=${total_cost:.3f}, "
        f"time={total_latency:.0f}ms"
    )
    if ctx:
        ctx.emit_live_step(
            "decision",
            f"Asset generation complete: {succeeded}/{total} succeeded, cost=${total_cost:.3f}",
        )

    return {
        **state,
        "current_agent": "asset_orchestrator_v3",
        "asset_manifest_v3": manifest.model_dump(),
        "generated_assets_v3": generated_assets,
        "diagram_image": diagram_image,
        "diagram_zones": diagram_zones,
        "_asset_generation_summary": {
            "total": total,
            "succeeded": succeeded,
            "failed": total - succeeded,
            "cost_usd": round(total_cost, 4),
            "latency_ms": round(total_latency, 1),
        },
    }
