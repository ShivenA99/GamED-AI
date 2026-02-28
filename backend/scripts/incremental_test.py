"""
Incremental Agent Testing Script

Run agents one at a time to inspect outputs and debug the pipeline.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.input_enhancer import input_enhancer
from app.agents.domain_knowledge_retriever import domain_knowledge_retriever
from app.agents.router import router
from app.agents.game_planner import game_planner
from app.agents.diagram_image_retriever import diagram_image_retriever
from app.agents.image_label_classifier import image_label_classifier
from app.agents.qwen_annotation_detector import qwen_annotation_detector
from app.agents.image_label_remover import image_label_remover
from app.agents.qwen_sam_zone_detector import qwen_sam_zone_detector
from app.agents.direct_structure_locator import direct_structure_locator


def print_json(data, title="Output"):
    """Pretty print JSON data"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)
    print(json.dumps(data, indent=2, default=str))
    print()


async def run_step(step_num: int, state: dict) -> dict:
    """Run a specific step and return updated state"""

    if step_num == 1:
        print("\n🔹 STEP 1: Input Enhancer")
        print("   Extracting pedagogical context (Bloom's level, subject, etc.)")
        result = await input_enhancer(state)
        state.update(result)
        print_json(state.get("pedagogical_context"), "Pedagogical Context")

    elif step_num == 2:
        print("\n🔹 STEP 2: Domain Knowledge Retriever")
        print("   Searching for canonical labels via web search...")
        result = await domain_knowledge_retriever(state)
        state.update(result)
        print_json(state.get("domain_knowledge"), "Domain Knowledge")

    elif step_num == 3:
        print("\n🔹 STEP 3: Router")
        print("   Selecting game template...")
        result = await router(state)
        state.update(result)
        print_json(state.get("template_selection"), "Template Selection")

    elif step_num == 4:
        print("\n🔹 STEP 4: Game Planner")
        print("   Planning game mechanics...")
        result = await game_planner(state)
        state.update(result)
        print_json(state.get("game_plan"), "Game Plan")

    elif step_num == 5:
        print("\n🔹 STEP 5: Diagram Image Retriever")
        print("   Searching for diagram image...")
        result = await diagram_image_retriever(state)
        state.update(result)
        print_json(state.get("diagram_image"), "Diagram Image")

    elif step_num == 6:
        print("\n🔹 STEP 6: Image Label Classifier")
        print("   Classifying if diagram is labeled or unlabeled...")
        result = await image_label_classifier(state)
        state.update(result)
        classification = state.get("image_classification", {})
        print_json(classification, "Image Classification")
        print(f"   → Classification: {classification.get('classification', 'unknown')}")
        print(f"   → Confidence: {classification.get('confidence', 0):.2f}")

    elif step_num == 7:
        classification = state.get("image_classification", {}).get("classification", "labeled")

        if classification == "labeled":
            print("\n🔹 STEP 7a: Qwen Annotation Detector (LABELED PATH)")
            print("   Detecting text labels and leader lines...")
            result = await qwen_annotation_detector(state)
            state.update(result)
            print_json({
                "annotation_elements": state.get("annotation_elements"),
                "text_labels_found": state.get("text_labels_found"),
                "detection_mask_path": state.get("detection_mask_path"),
            }, "Annotation Detection")
        else:
            print("\n🔹 STEP 7b: Direct Structure Locator (UNLABELED PATH)")
            print("   Directly locating structures with Qwen VL...")
            result = await direct_structure_locator(state)
            state.update(result)
            print_json({
                "diagram_zones": state.get("diagram_zones"),
                "diagram_labels": state.get("diagram_labels"),
            }, "Direct Structure Location")

    elif step_num == 8:
        classification = state.get("image_classification", {}).get("classification", "labeled")

        if classification == "labeled":
            print("\n🔹 STEP 8: Image Label Remover")
            print("   Inpainting to remove detected annotations...")
            result = await image_label_remover(state)
            state.update(result)
            print_json({
                "cleaned_image_path": state.get("cleaned_image_path"),
                "removed_labels": state.get("removed_labels"),
            }, "Label Removal")
        else:
            print("\n🔹 STEP 8: SKIPPED (unlabeled path)")

    elif step_num == 9:
        classification = state.get("image_classification", {}).get("classification", "labeled")

        if classification == "labeled":
            print("\n🔹 STEP 9: Qwen SAM Zone Detector")
            print("   Creating zones from leader line endpoints using SAM3...")
            result = await qwen_sam_zone_detector(state)
            state.update(result)
            print_json({
                "diagram_zones": state.get("diagram_zones"),
                "diagram_labels": state.get("diagram_labels"),
                "zone_detection_method": state.get("zone_detection_method"),
            }, "Zone Detection")
        else:
            print("\n🔹 STEP 9: SKIPPED (unlabeled path - zones already detected)")

    return state


async def main():
    # Initial state
    question = "Label the parts of a flower"

    state = {
        "question_id": "test_flower_001",
        "question_text": question,
        "question_options": [],
        "auto_retry": True,
    }

    print("\n" + "="*60)
    print("  INCREMENTAL AGENT TESTING")
    print("="*60)
    print(f"\nQuestion: {question}")
    print(f"Template: INTERACTIVE_DIAGRAM")
    print("\nRunning agents step by step...")
    print("Press Enter to continue to next step, 'q' to quit, or enter step number")

    current_step = 1
    max_steps = 9

    while current_step <= max_steps:
        user_input = input(f"\n>>> Step {current_step}/{max_steps} (Enter/q/number): ").strip()

        if user_input.lower() == 'q':
            print("\nExiting...")
            break
        elif user_input.isdigit():
            current_step = int(user_input)
            if current_step < 1 or current_step > max_steps:
                print(f"Invalid step. Enter 1-{max_steps}")
                continue

        try:
            state = await run_step(current_step, state)
            current_step += 1
        except Exception as e:
            print(f"\n❌ Error in step {current_step}: {e}")
            import traceback
            traceback.print_exc()

            retry = input("\nRetry this step? (y/n): ").strip().lower()
            if retry != 'y':
                current_step += 1

    print("\n" + "="*60)
    print("  FINAL STATE SUMMARY")
    print("="*60)

    # Print key outputs
    summary = {
        "pedagogical_context": state.get("pedagogical_context"),
        "domain_knowledge": state.get("domain_knowledge"),
        "template_selection": state.get("template_selection"),
        "diagram_image": state.get("diagram_image"),
        "image_classification": state.get("image_classification"),
        "diagram_zones": state.get("diagram_zones"),
        "diagram_labels": state.get("diagram_labels"),
    }
    print_json(summary, "Key Outputs")

    # Save full state
    output_path = Path(__file__).parent / "incremental_test_state.json"
    with open(output_path, "w") as f:
        json.dump(state, f, indent=2, default=str)
    print(f"\nFull state saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
