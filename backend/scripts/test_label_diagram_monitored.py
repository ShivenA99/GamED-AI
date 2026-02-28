#!/usr/bin/env python3
"""
Enhanced test script for INTERACTIVE_DIAGRAM template with detailed stage monitoring.

Uses LOCAL open-source models via Ollama (configured in .env).

Usage:
    # Uses .env configuration (USE_OLLAMA=true, AGENT_CONFIG_PRESET=local_only)
    FORCE_TEMPLATE=INTERACTIVE_DIAGRAM PYTHONPATH=. python scripts/test_interactive_diagram_monitored.py
    
    # Or override specific settings
    FORCE_TEMPLATE=INTERACTIVE_DIAGRAM USE_IMAGE_DIAGRAMS=true PYTHONPATH=. python scripts/test_interactive_diagram_monitored.py

Prerequisites:
    1. Run setup: ./scripts/setup_ollama.sh
    2. Ensure Ollama is running: ollama serve
    3. Models are pulled automatically by setup script
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.state import create_initial_state
from app.agents.topologies import TopologyType, create_topology

# Test question for INTERACTIVE_DIAGRAM
TEST_QUESTION = {
    "id": "biology_flower_parts",
    "text": "Label the parts of a flower including the petal, sepal, stamen, pistil, ovary, and receptacle.",
    "options": None
}


def _resolve_topology() -> TopologyType:
    topology = os.environ.get("TOPOLOGY", "T1").upper()
    if topology == "T1":
        return TopologyType.T1_SEQUENTIAL_VALIDATED
    return TopologyType.T0_SEQUENTIAL


def print_stage_header(stage_name: str, stage_num: int, total: int):
    """Print a formatted stage header"""
    print("\n" + "=" * 80)
    print(f"STAGE {stage_num}/{total}: {stage_name.upper()}")
    print("=" * 80)


def print_state_snapshot(state: Dict[str, Any], stage: str):
    """Print relevant state information for a stage"""
    print(f"\n[{stage}] State Snapshot:")
    
    # Template selection
    if state.get("template_selection"):
        ts = state["template_selection"]
        print(f"  Template: {ts.get('template_type')} (confidence: {ts.get('confidence', 0):.2f})")
    
    # Domain knowledge
    if state.get("domain_knowledge"):
        dk = state["domain_knowledge"]
        labels = dk.get("canonical_labels", [])
        print(f"  Canonical Labels: {len(labels)} labels - {labels[:5]}{'...' if len(labels) > 5 else ''}")
    
    # Game plan
    if state.get("game_plan"):
        gp = state["game_plan"]
        print(f"  Game Plan: {len(gp.get('game_mechanics', []))} mechanics")
        if gp.get("required_labels"):
            print(f"  Required Labels: {gp['required_labels']}")
    
    # Scene data
    if state.get("scene_data"):
        sd = state["scene_data"]
        print(f"  Scene: {sd.get('scene_title', 'N/A')}")
    
    # Diagram image
    if state.get("diagram_image"):
        di = state["diagram_image"]
        print(f"  Image URL: {di.get('image_url', 'N/A')[:60]}...")
    
    # Cleaned image
    if state.get("cleaned_image_path"):
        print(f"  Cleaned Image: {state['cleaned_image_path']}")
        if state.get("removed_labels"):
            print(f"  Removed Labels: {state['removed_labels']}")
    
    # Segments
    if state.get("diagram_segments"):
        ds = state["diagram_segments"]
        segments = ds.get("segments", [])
        print(f"  Segments: {len(segments)} found (method: {ds.get('method', 'N/A')})")
    
    # Zones
    if state.get("diagram_zones"):
        zones = state["diagram_zones"]
        print(f"  Zones: {len(zones)} zones")
        for zone in zones[:3]:
            print(f"    - {zone.get('id')}: {zone.get('label')} at ({zone.get('x')}, {zone.get('y')})")
    
    # Retry info
    if state.get("retry_image_search"):
        print(f"  ⚠️  RETRY FLAG SET: attempt {state.get('image_search_attempts', 0)}/{state.get('max_image_attempts', 3)}")
    
    # Errors
    if state.get("current_validation_errors"):
        print(f"  ❌ Errors: {state['current_validation_errors']}")
    
    # Current agent
    print(f"  Current Agent: {state.get('current_agent', 'N/A')}")


def check_ollama_running() -> bool:
    """Check if Ollama server is running"""
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


async def run_monitored_test():
    """Run the INTERACTIVE_DIAGRAM test with detailed stage monitoring"""
    print("=" * 80)
    print("INTERACTIVE_DIAGRAM PIPELINE TEST - MONITORED EXECUTION")
    print("=" * 80)
    print(f"\nQuestion: {TEST_QUESTION['text']}")
    print(f"Forced Template: {os.environ.get('FORCE_TEMPLATE', 'Not set')}")
    print(f"Use Image Diagrams: {os.environ.get('USE_IMAGE_DIAGRAMS', 'false')}")
    print(f"Topology: {os.environ.get('TOPOLOGY', 'T1')}")
    
    # Check configuration from .env
    from dotenv import load_dotenv
    load_dotenv()
    use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
    config_preset = os.getenv("AGENT_CONFIG_PRESET", "local_only")
    
    print(f"Model Config: {config_preset}")
    print(f"Use Ollama: {use_ollama}")
    
    if use_ollama or config_preset == "local_only":
        print("\n⚠️  Using LOCAL open-source models (Ollama)")
        if not check_ollama_running():
            print("\n❌ ERROR: Ollama server is not running!")
            print("\nPlease start Ollama:")
            print("  1. Run: ollama serve")
            print("  2. Or use: ./scripts/setup_ollama.sh")
            print("\nThen run this test again.")
            return None
        else:
            print("✅ Ollama server is running")
            print("   Required models: llama3.2, qwen2.5:7b, deepseek-coder:6.7b")
            print("   (Run ./scripts/setup_ollama.sh if models not pulled)")
    
    print("=" * 80)

    # Create topology
    topology = _resolve_topology()
    graph = create_topology(topology)
    compiled = graph.compile()

    # Create initial state
    initial_state = create_initial_state(
        question_id=TEST_QUESTION["id"],
        question_text=TEST_QUESTION["text"],
        question_options=TEST_QUESTION.get("options")
    )

    print("\n🚀 Starting pipeline execution...")
    print("Monitoring each stage...\n")
    start_time = datetime.now()

    # Track execution stages
    stages_seen = []
    last_agent = None

    try:
        # Use astream_events to monitor each step
        async for event in compiled.astream_events(initial_state, version="v2"):
            kind = event.get("event")
            
            if kind == "on_chain_start":
                # Agent/node starting
                name = event.get("name", "")
                if name and name not in ["__start__", "__end__"]:
                    if name != last_agent:
                        stages_seen.append(name)
                        stage_num = len(stages_seen)
                        print_stage_header(name, stage_num, 10)  # Estimate 10 stages
                        last_agent = name
            
            elif kind == "on_chain_end":
                # Agent/node completed
                name = event.get("name", "")
                if name and name not in ["__start__", "__end__"]:
                    output = event.get("data", {}).get("output", {})
                    if output and isinstance(output, dict):
                        print_state_snapshot(output, name)
            
            elif kind == "on_chain_error":
                # Error occurred
                name = event.get("name", "")
                error = event.get("error", {})
                print(f"\n❌ ERROR in {name}: {error}")
        
        # Get final state
        final_state = await compiled.ainvoke(initial_state)
        elapsed = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 80)
        print(f"\n⏱️  Total Time: {elapsed:.1f}s")
        print(f"\n📋 Execution Order ({len(stages_seen)} stages):")
        for i, stage in enumerate(stages_seen, 1):
            print(f"  {i}. {stage}")
        
        # Verify expected order for INTERACTIVE_DIAGRAM
        expected_order = [
            "input_enhancer",
            "domain_knowledge_retriever",
            "router",
            "game_planner",
            "scene_generator",
            "diagram_image_retriever",
            "image_label_remover",
            "diagram_image_segmenter",
            "diagram_zone_labeler",
            "blueprint_generator"
        ]
        
        print(f"\n✅ Order Verification:")
        order_correct = True
        for i, expected in enumerate(expected_order):
            if i < len(stages_seen):
                actual = stages_seen[i]
                status = "✓" if actual == expected else "✗"
                if actual != expected:
                    order_correct = False
                print(f"  {status} Stage {i+1}: Expected '{expected}', Got '{actual}'")
            else:
                print(f"  ✗ Stage {i+1}: Expected '{expected}', Missing")
                order_correct = False
        
        if order_correct:
            print("\n✅ Pipeline order is CORRECT!")
        else:
            print("\n⚠️  Pipeline order differs from expected")
        
        # Check key features
        print(f"\n🔍 Feature Verification:")
        
        # 1. Required labels in game plan
        if final_state.get("game_plan", {}).get("required_labels"):
            req_labels = final_state["game_plan"]["required_labels"]
            print(f"  ✅ Required labels in game_plan: {req_labels}")
        else:
            print(f"  ❌ Missing required_labels in game_plan")
        
        # 2. Cleaned image path
        if final_state.get("cleaned_image_path"):
            print(f"  ✅ Cleaned image created: {final_state['cleaned_image_path']}")
            if final_state.get("removed_labels"):
                print(f"  ✅ Removed {len(final_state['removed_labels'])} labels: {final_state['removed_labels']}")
        else:
            print(f"  ⚠️  No cleaned_image_path (may be skipped if no text found)")
        
        # 3. Zones created
        if final_state.get("diagram_zones"):
            zones = final_state["diagram_zones"]
            print(f"  ✅ Created {len(zones)} zones")
        else:
            print(f"  ❌ No zones created")
        
        # 4. Blueprint generated
        if final_state.get("blueprint"):
            bp = final_state["blueprint"]
            print(f"  ✅ Blueprint generated: {bp.get('title', 'N/A')}")
            if bp.get("diagram", {}).get("zones"):
                print(f"  ✅ Blueprint has {len(bp['diagram']['zones'])} zones")
        else:
            print(f"  ❌ No blueprint generated")
        
        # Save detailed results
        output_dir = Path(__file__).parent.parent / "pipeline_outputs"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"interactive_diagram_monitored_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, "w") as f:
            json.dump({
                "question": TEST_QUESTION,
                "execution_order": stages_seen,
                "elapsed_seconds": elapsed,
                "final_state": {
                    "template_selection": final_state.get("template_selection"),
                    "domain_knowledge": final_state.get("domain_knowledge"),
                    "game_plan": final_state.get("game_plan"),
                    "cleaned_image_path": final_state.get("cleaned_image_path"),
                    "removed_labels": final_state.get("removed_labels"),
                    "diagram_zones": final_state.get("diagram_zones"),
                    "diagram_labels": final_state.get("diagram_labels"),
                    "blueprint": final_state.get("blueprint"),
                }
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        return final_state

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(run_monitored_test())
