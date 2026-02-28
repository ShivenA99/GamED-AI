"""V4 Algorithm Graph Builder — deterministic plan construction.

Reads game_concept, assigns IDs, computes scores, determines asset needs.
No LLM call — purely deterministic transformation.
"""

from app.utils.logging_config import get_logger
from app.v4_algorithm.contracts import get_default_score, needs_visual_asset

logger = get_logger("gamed_ai.v4_algorithm.graph_builder")


async def algo_graph_builder(state: dict) -> dict:
    """Build AlgorithmGamePlan from AlgorithmGameConcept.

    Reads: game_concept, domain_knowledge
    Writes: game_plan, plan_retry_count
    """
    concept = state.get("game_concept")
    if not concept:
        logger.error("graph_builder: game_concept is missing")
        return {
            "game_plan": None,
            "phase_errors": [{"phase": "graph_builder", "message": "No game_concept"}],
        }

    scenes_raw = concept.get("scenes", [])
    retry_count = state.get("plan_retry_count", 0)

    scenes = []
    total_max_score = 0

    for i, scene_concept in enumerate(scenes_raw):
        scene_id = f"scene_{i + 1}"
        game_type = scene_concept.get("game_type", "state_tracer")
        max_score = get_default_score(game_type)
        total_max_score += max_score

        # Asset spec from concept hints
        wants_visual = scene_concept.get("needs_visualization", False)
        has_asset = wants_visual or needs_visual_asset(game_type)

        asset_spec = None
        if has_asset:
            viz_desc = scene_concept.get("visualization_description", "")
            viz_type = scene_concept.get("visualization_type", "none")
            asset_spec = {
                "scene_id": scene_id,
                "asset_type": _map_viz_type(viz_type),
                "search_queries": _build_search_queries(
                    concept.get("algorithm_name", ""),
                    viz_desc,
                ),
                "generation_prompt": viz_desc,
                "style": "clean_educational",
                "must_include": scene_concept.get("config_hints", {}).get("must_include", []),
            }

        scene_plan = {
            "scene_id": scene_id,
            "scene_number": i + 1,
            "title": scene_concept.get("title", f"Scene {i + 1}"),
            "game_type": game_type,
            "difficulty": scene_concept.get("difficulty", "intermediate"),
            "learning_goal": scene_concept.get("learning_goal", ""),
            "narrative_intro": scene_concept.get("narrative_intro", ""),
            "max_score": max_score,
            "config_hints": scene_concept.get("config_hints", {}),
            "needs_asset": has_asset,
            "asset_spec": asset_spec,
        }
        scenes.append(scene_plan)

    # Build transitions (linear by default)
    transitions = []
    for i in range(len(scenes) - 1):
        transitions.append({
            "from_scene": scenes[i]["scene_id"],
            "to_scene": scenes[i + 1]["scene_id"],
            "trigger": "completion",
        })

    game_plan = {
        "title": concept.get("title", "Algorithm Game"),
        "algorithm_name": concept.get("algorithm_name", ""),
        "algorithm_category": concept.get("algorithm_category", ""),
        "total_max_score": total_max_score,
        "scenes": scenes,
        "scene_transitions": transitions,
    }

    logger.info(
        f"Graph builder: {len(scenes)} scenes, total_max_score={total_max_score}, "
        f"assets_needed={sum(1 for s in scenes if s['needs_asset'])}"
    )

    return {
        "game_plan": game_plan,
        "plan_retry_count": retry_count + 1,
    }


def _map_viz_type(viz_type: str) -> str:
    """Map visualization_type to asset_type."""
    mapping = {
        "data_structure": "algorithm_illustration",
        "flowchart": "flowchart",
        "comparison_chart": "growth_chart",
        "board_layout": "board_illustration",
    }
    return mapping.get(viz_type, "algorithm_illustration")


def _build_search_queries(algorithm_name: str, viz_desc: str) -> list[str]:
    """Build image search queries from algorithm name and description."""
    queries = []
    if algorithm_name:
        queries.append(f"{algorithm_name} algorithm diagram educational")
        queries.append(f"{algorithm_name} visualization")
    if viz_desc:
        queries.append(viz_desc)
    return queries
