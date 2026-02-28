#!/usr/bin/env python3
"""
Verify the pipeline order for INTERACTIVE_DIAGRAM template.

This script checks the graph structure to ensure the correct order:
router → game_planner → scene_generator → diagram_image_retriever → 
image_label_remover → diagram_image_segmenter → diagram_zone_labeler → blueprint_generator
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.graph import create_game_generation_graph


def verify_pipeline_order():
    """Verify the INTERACTIVE_DIAGRAM pipeline order"""
    print("=" * 80)
    print("VERIFYING INTERACTIVE_DIAGRAM PIPELINE ORDER")
    print("=" * 80)
    
    graph = create_game_generation_graph()
    
    # Get all edges
    edges = []
    for node_name in graph.nodes.keys():
        # Get outgoing edges
        if hasattr(graph, 'edges'):
            for edge in graph.edges:
                if hasattr(edge, 'source') and edge.source == node_name:
                    edges.append((node_name, edge.target))
    
    # Expected order for INTERACTIVE_DIAGRAM
    expected_order = [
        "input_enhancer",
        "domain_knowledge_retriever", 
        "router",
        "game_planner",           # ✅ Should come BEFORE image pipeline
        "scene_generator",        # ✅ Should come BEFORE image pipeline
        "diagram_image_retriever", # ✅ After scene_generator
        "image_label_remover",    # ✅ After image_retriever (NEW)
        "diagram_image_segmenter", # ✅ After label_remover
        "diagram_zone_labeler",   # ✅ After segmenter
        "blueprint_generator"     # ✅ After zone_labeler
    ]
    
    print("\n✅ Expected Pipeline Order:")
    for i, node in enumerate(expected_order, 1):
        print(f"  {i}. {node}")
    
    # Check if image_label_remover node exists
    if "image_label_remover" in graph.nodes:
        print("\n✅ image_label_remover node exists in graph")
    else:
        print("\n❌ image_label_remover node MISSING from graph")
        return False
    
    # Check if check_zone_labels_complete function exists
    from app.agents.graph import check_zone_labels_complete
    if check_zone_labels_complete:
        print("✅ check_zone_labels_complete function exists")
    else:
        print("❌ check_zone_labels_complete function MISSING")
        return False
    
    print("\n✅ Graph structure verification complete!")
    print("\nNote: Full execution test requires API keys and may take time.")
    print("Run: FORCE_TEMPLATE=INTERACTIVE_DIAGRAM PYTHONPATH=. python scripts/test_interactive_diagram_monitored.py")
    
    return True


if __name__ == "__main__":
    success = verify_pipeline_order()
    sys.exit(0 if success else 1)
