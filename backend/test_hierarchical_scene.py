import asyncio
import json
from pathlib import Path
from app.agents.state import create_initial_state
from app.agents.scene_generator import scene_generator_agent

async def test_hierarchical():
    """Test the hierarchical scene generation"""

    # Create test state
    state = create_initial_state(
        question_id="test_hierarchical_1",
        question_text="Explain how binary search works on the sorted array [1, 3, 5, 7, 9, 11, 13]. Demonstrate finding the target value 7.",
        question_options=None
    )

    # Add required context
    state["pedagogical_context"] = {
        "blooms_level": "understand",
        "subject": "Computer Science",
        "difficulty": "intermediate",
        "learning_objectives": ["Understand binary search algorithm"],
        "key_concepts": ["sorted array", "divide and conquer", "logarithmic time"]
    }

    state["template_selection"] = {
        "template_type": "STATE_TRACER_CODE",
        "confidence": 0.9
    }

    state["game_plan"] = {
        "game_mechanics": [
            {
                "id": "step_through",
                "type": "step",
                "description": "Step through code execution line by line",
                "interaction_type": "click"
            },
            {
                "id": "predict_variables",
                "type": "predict",
                "description": "Predict variable values before execution",
                "interaction_type": "input"
            }
        ]
    }

    # Run scene generator
    print("Running hierarchical scene generation...")
    result = await scene_generator_agent(state)

    # Check results
    scene = result.get("scene_data")

    if scene:
        print("\n✅ SUCCESS: Scene generated")
        print(f"\nScene Title: {scene.get('scene_title')}")
        print(f"Visual Theme: {scene.get('visual_theme')}")
        print(f"Number of Assets: {len(scene.get('required_assets', []))}")
        print(f"Number of Animations: {len(scene.get('animation_sequences', []))}")
        print(f"Number of Interactions: {len(scene.get('asset_interactions', []))}")

        # Save scene_data to file for inspection
        output_dir = Path("pipeline_outputs")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "hierarchical_scene_test.json"
        with open(output_file, "w") as f:
            json.dump(scene, f, indent=2)
        print(f"\n💾 Scene data saved to: {output_file}")

        # Verify all required fields
        required_fields = [
            "visual_theme", "scene_title", "minimal_context",
            "required_assets", "asset_interactions", "layout_specification",
            "animation_sequences", "state_transitions", "visual_flow"
        ]

        missing = [f for f in required_fields if f not in scene]

        if missing:
            print(f"\n❌ MISSING FIELDS: {missing}")
        else:
            print("\n✅ All required fields present")

        # Check for asset reference validity
        asset_ids = {a.get("id") for a in scene.get("required_assets", [])}

        invalid_refs = []
        for interaction in scene.get("asset_interactions", []):
            asset_id = interaction.get("asset_id")
            if asset_id and asset_id not in asset_ids:
                invalid_refs.append(asset_id)

        if invalid_refs:
            print(f"\n❌ INVALID ASSET REFERENCES: {invalid_refs}")
        else:
            print("\n✅ All asset references valid")

    else:
        print("\n❌ FAILED: No scene_data in result")
        print(f"Error: {result.get('error_message')}")

if __name__ == "__main__":
    asyncio.run(test_hierarchical())