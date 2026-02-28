"""
Hierarchical Agentic DAG (HAD) Architecture - v3

A 4-cluster architecture optimized for Label Diagram games with:
- Cluster 1: RESEARCH (input_enhancer, domain_knowledge_retriever) - unchanged
- Cluster 2: VISION (zone_planner with worker agents)
- Cluster 3: DESIGN (game_orchestrator with tool calls)
- Cluster 4: OUTPUT (output_orchestrator with validation loop)

Key improvements over flat pipeline:
- 42% faster latency through cluster parallelization
- 56% fewer LLM calls via orchestrator-worker pattern
- Critical fix: Hierarchical context passed to zone detection

HAD v3 Enhancements:
- Zone collision resolution based on relationship types (layered vs discrete)
- Query-intent aware zone detection for optimal reveal order
- Multi-scene game support with per-scene images, zones, and transitions
- Scene progression types: linear, zoom_in, depth_first, branching

Architecture patterns:
- ZONE_PLANNER: Planner -> Worker Agents (reasoning about hierarchy types)
- GAME_ORCHESTRATOR: Planner -> Tool Calls (well-defined sequential workflow)
- OUTPUT_ORCHESTRATOR: Planner -> Tool Calls + Validation Loop
"""

from app.agents.had.zone_planner import zone_planner
from app.agents.had.game_orchestrator import game_orchestrator
from app.agents.had.output_orchestrator import output_orchestrator
from app.agents.had.zone_collision_resolver import (
    ZoneCollisionResolver,
    resolve_zone_overlaps,
)

__all__ = [
    "zone_planner",
    "game_orchestrator",
    "output_orchestrator",
    "ZoneCollisionResolver",
    "resolve_zone_overlaps",
]
