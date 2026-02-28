"""
Pipeline Graph API Routes

Provides endpoints to get the actual pipeline graph structure based on
the current configuration (topology, preset, etc.).
"""
import os
from typing import List, Dict, Any
from fastapi import APIRouter
import logging

logger = logging.getLogger("gamed_ai.routes.pipeline_graph")
router = APIRouter()


def get_t1_hierarchical_graph() -> Dict[str, Any]:
    """
    Get the T1 hierarchical label diagram pipeline graph structure.

    This is the simplified 2-step Gemini pipeline:
    - diagram_image_retriever → diagram_image_generator → gemini_zone_detector
    """
    nodes = [
        {"id": "input_enhancer", "name": "Input Enhancer", "category": "input"},
        {"id": "domain_knowledge_retriever", "name": "Domain Knowledge", "category": "input"},
        {"id": "router", "name": "Template Router", "category": "routing"},
        {"id": "game_planner", "name": "Game Planner", "category": "generation"},
        {"id": "scene_stage1_structure", "name": "Scene Structure", "category": "generation"},
        {"id": "scene_stage2_assets", "name": "Scene Assets", "category": "generation"},
        {"id": "scene_stage3_interactions", "name": "Scene Interactions", "category": "generation"},
        {"id": "diagram_image_retriever", "name": "Diagram Retriever", "category": "image"},
        {"id": "diagram_image_generator", "name": "Diagram Generator", "category": "image"},
        {"id": "gemini_zone_detector", "name": "Gemini Zone Detector", "category": "image"},
        {"id": "blueprint_generator", "name": "Blueprint Generator", "category": "generation"},
        {"id": "blueprint_validator", "name": "Blueprint Validator", "category": "validation"},
        {"id": "diagram_spec_generator", "name": "Diagram Spec Generator", "category": "generation"},
        {"id": "diagram_spec_validator", "name": "Diagram Spec Validator", "category": "validation"},
        {"id": "diagram_svg_generator", "name": "SVG Generator", "category": "output"},
    ]

    edges = [
        {"from": "input_enhancer", "to": "domain_knowledge_retriever"},
        {"from": "domain_knowledge_retriever", "to": "router"},
        {"from": "router", "to": "game_planner"},
        {"from": "game_planner", "to": "scene_stage1_structure"},
        {"from": "scene_stage1_structure", "to": "scene_stage2_assets"},
        {"from": "scene_stage2_assets", "to": "scene_stage3_interactions"},
        {"from": "scene_stage3_interactions", "to": "diagram_image_retriever"},
        {"from": "diagram_image_retriever", "to": "diagram_image_generator"},
        {"from": "diagram_image_generator", "to": "gemini_zone_detector"},
        {"from": "gemini_zone_detector", "to": "blueprint_generator"},
        {"from": "blueprint_generator", "to": "blueprint_validator"},
        {"from": "blueprint_validator", "to": "diagram_spec_generator"},
        {"from": "diagram_spec_generator", "to": "diagram_spec_validator"},
        {"from": "diagram_spec_validator", "to": "diagram_svg_generator"},
    ]

    # Layout: columns for visualization (each array is a column)
    layout = [
        ["input_enhancer"],
        ["domain_knowledge_retriever"],
        ["router"],
        ["game_planner"],
        ["scene_stage1_structure"],
        ["scene_stage2_assets"],
        ["scene_stage3_interactions"],
        ["diagram_image_retriever"],
        ["diagram_image_generator"],
        ["gemini_zone_detector"],
        ["blueprint_generator"],
        ["blueprint_validator"],
        ["diagram_spec_generator"],
        ["diagram_spec_validator"],
        ["diagram_svg_generator"],
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "layout": layout,
        "pipeline_name": "T1 Hierarchical Label Diagram",
        "description": "2-step Gemini pipeline: retrieve reference → generate clean diagram → detect zones",
    }


@router.get("/graph")
async def get_pipeline_graph():
    """
    Get the current pipeline graph structure based on configuration.

    Returns the nodes, edges, and layout for visualization.
    """
    topology = os.getenv("TOPOLOGY", "T1")
    pipeline_preset = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")

    logger.info(f"Getting pipeline graph for topology={topology}, preset={pipeline_preset}")

    # For now, return the T1 hierarchical graph
    # In the future, this could return different graphs based on topology/preset
    graph = get_t1_hierarchical_graph()
    graph["topology"] = topology
    graph["preset"] = pipeline_preset

    return graph


@router.get("/graph/nodes")
async def get_pipeline_nodes():
    """Get just the list of nodes in the current pipeline."""
    graph = get_t1_hierarchical_graph()
    return {"nodes": graph["nodes"]}


@router.get("/graph/edges")
async def get_pipeline_edges():
    """Get just the edges (connections) in the current pipeline."""
    graph = get_t1_hierarchical_graph()
    return {"edges": graph["edges"]}
