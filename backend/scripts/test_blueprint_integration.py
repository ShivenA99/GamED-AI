#!/usr/bin/env python3
"""
Integration Test: Blueprint Generation Stage

Tests blueprint generation with zones and labels from previous stages.
Verifies complete integration of image pipeline outputs.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_config import setup_logging, get_logger
from app.agents.blueprint_generator import blueprint_generator_agent
from app.agents.state import create_initial_state

setup_logging(level="INFO", log_to_file=False)
logger = get_logger("test_blueprint_integration")

TEST_QUESTION = {
    "id": "test_integration",
    "text": "Label the parts of a flower including the petal, sepal, stamen, pistil, ovary, and receptacle.",
    "options": None
}


async def test_blueprint_generation():
    """Test blueprint generation with integrated outputs"""
    print("=" * 80)
    print("INTEGRATION TEST: Blueprint Generation Stage")
    print("=" * 80)
    print()
    
    # Load all previous stage results
    output_dir = Path(__file__).parent.parent / "pipeline_outputs" / "integration_tests"
    
    stage1_file = output_dir / "stage1_image_retrieval.json"
    stage2_file = output_dir / "stage2_label_removal.json"
    stage3_file = output_dir / "stage3_segmentation.json"
    stage4_file = output_dir / "stage4_zone_labeling.json"
    
    if not all(f.exists() for f in [stage1_file, stage2_file, stage3_file, stage4_file]):
        print("❌ Previous stage results not found. Run all previous tests first:")
        print("   1. test_image_retrieval_stage.py")
        print("   2. test_image_label_removal_stage.py")
        print("   3. test_segmentation_stage.py")
        print("   4. test_zone_labeling_stage.py")
        return None
    
    # Load all results
    with open(stage1_file) as f:
        stage1 = json.load(f)
    with open(stage2_file) as f:
        stage2 = json.load(f)
    with open(stage3_file) as f:
        stage3 = json.load(f)
    with open(stage4_file) as f:
        stage4 = json.load(f)
    
    print("Loaded results from all previous stages")
    print()
    
    # Create state with all integrated data
    initial_state = create_initial_state(
        question_id=TEST_QUESTION["id"],
        question_text=TEST_QUESTION["text"],
        question_options=TEST_QUESTION.get("options")
    )
    
    # Add pedagogical context (required by blueprint generator)
    initial_state["pedagogical_context"] = {
        "bloom_level": "application",
        "subject": "Biology",
        "grade_level": "middle_school",
        "learning_objectives": ["Identify and label parts of a flower"]
    }
    
    # Add template selection
    initial_state["template_selection"] = {
        "template_type": "INTERACTIVE_DIAGRAM",
        "confidence": 0.95,
        "is_production_ready": True
    }
    
    # Add game plan (required)
    initial_state["game_plan"] = {
        "learning_objectives": ["Identify and label parts of a flower"],
        "game_mechanics": [],
        "estimated_duration_minutes": 10,
        "required_labels": ["petal", "sepal", "stamen", "pistil", "ovary", "receptacle"]
    }
    
    # Add image data
    initial_state["diagram_image"] = {
        "image_url": stage1["selected_image"]["image_url"],
        "source_url": stage1["selected_image"]["source_url"],
        "title": stage1["selected_image"]["title"]
    }
    
    # Add cleaned image
    if stage2.get("cleaned_image_path"):
        initial_state["cleaned_image_path"] = stage2["cleaned_image_path"]
        initial_state["removed_labels"] = stage2.get("removed_labels", [])
    
    # Add segments
    initial_state["diagram_segments"] = {
        "image_path": stage3["image_path"],
        "segments": stage3["segments"],
        "method": stage3["method"]
    }
    
    # Add zones and labels
    initial_state["diagram_zones"] = stage4["zones"]
    initial_state["diagram_labels"] = stage4["labels"]
    
    # Add domain knowledge
    initial_state["domain_knowledge"] = {
        "canonical_labels": ["petal", "sepal", "stamen", "pistil", "ovary", "receptacle"],
        "query": "flower parts diagram",
        "acceptable_variants": {},
        "sources": []
    }
    
    # Generate blueprint
    try:
        logger.info("Generating blueprint with integrated data")
        result_state = await blueprint_generator_agent(initial_state)
        
        blueprint = result_state.get("blueprint")
        if not blueprint:
            logger.error("No blueprint generated")
            print("❌ No blueprint generated")
            return None
        
        logger.info("Blueprint generated successfully",
                   template_type=blueprint.get("templateType"),
                   zones_count=len(blueprint.get("diagram", {}).get("zones", [])),
                   labels_count=len(blueprint.get("labels", [])))
        
        print("✅ Blueprint generated successfully")
        print(f"   Template: {blueprint.get('templateType')}")
        print(f"   Title: {blueprint.get('title')}")
        print(f"   Zones: {len(blueprint.get('diagram', {}).get('zones', []))}")
        print(f"   Labels: {len(blueprint.get('labels', []))}")
        print()
        
        # Verify zones and labels are used
        diagram_zones = blueprint.get("diagram", {}).get("zones", [])
        blueprint_labels = blueprint.get("labels", [])
        
        if len(diagram_zones) == len(stage4["zones"]):
            print("✅ Zones correctly integrated from zone_labeler")
        else:
            print(f"⚠️ Zone count mismatch: {len(diagram_zones)} vs {len(stage4['zones'])}")
        
        if len(blueprint_labels) == len(stage4["labels"]):
            print("✅ Labels correctly integrated from zone_labeler")
        else:
            print(f"⚠️ Label count mismatch: {len(blueprint_labels)} vs {len(stage4['labels'])}")
        print()
        
        # Save result
        output_file = output_dir / "stage5_blueprint.json"
        result = {
            "stage": "blueprint_generation",
            "timestamp": datetime.now().isoformat(),
            "blueprint": blueprint,
            "integration_summary": {
                "image_url": stage1["selected_image"]["image_url"],
                "cleaned_image_used": bool(stage2.get("cleaned_image_path")),
                "segmentation_method": stage3["method"],
                "zone_labeling_method": stage4["primary_method"],
                "fallback_used": stage4["fallback_used"],
                "zones_count": len(diagram_zones),
                "labels_count": len(blueprint_labels)
            }
        }
        
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"✅ Result saved to: {output_file}")
        print()
        print("=" * 80)
        print("MANUAL VERIFICATION:")
        print("=" * 80)
        print("1. Validate blueprint JSON structure")
        print("2. Check that zones match image structures")
        print("3. Verify labels are correctly mapped to zones")
        print("4. Test blueprint in frontend: http://localhost:3000")
        print()
        
        # Print blueprint summary
        print("=" * 80)
        print("BLUEPRINT SUMMARY:")
        print("=" * 80)
        print(json.dumps({
            "templateType": blueprint.get("templateType"),
            "title": blueprint.get("title"),
            "diagram": {
                "zones_count": len(diagram_zones),
                "assetUrl": blueprint.get("diagram", {}).get("assetUrl", "N/A")[:80]
            },
            "labels_count": len(blueprint_labels),
            "tasks_count": len(blueprint.get("tasks", []))
        }, indent=2))
        print()
        
        return result
        
    except Exception as e:
        logger.error("Blueprint generation failed", exc_info=True, error=str(e))
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_blueprint_generation())
    sys.exit(0 if result else 1)
