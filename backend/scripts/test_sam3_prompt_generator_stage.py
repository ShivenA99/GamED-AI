#!/usr/bin/env python3
"""
Integration Test: SAM3 Prompt Generator Stage

Tests the sam3_prompt_generator agent independently.
Verifies VLM generates short, effective SAM3 prompts for each label.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_config import setup_logging, get_logger
from app.agents.sam3_prompt_generator import sam3_prompt_generator_agent
from app.agents.state import create_initial_state

setup_logging(level="INFO", log_to_file=False)
logger = get_logger("test_sam3_prompt_generator_stage")

TEST_QUESTION = {
    "id": "test_prompt_generator",
    "text": "Label the parts of a flower including the petal, sepal, stamen, pistil, ovary, and receptacle.",
    "options": None
}

CANONICAL_LABELS = ["petal", "sepal", "stamen", "pistil", "ovary", "receptacle"]


async def test_prompt_generation():
    """Test SAM3 prompt generation"""
    print("=" * 80)
    print("INTEGRATION TEST: SAM3 Prompt Generator Stage")
    print("=" * 80)
    print()
    
    # Load previous stage results
    output_dir = Path(__file__).parent.parent / "pipeline_outputs" / "integration_tests"
    stage1_file = output_dir / "stage1_image_retrieval.json"
    stage2_file = output_dir / "stage2_label_removal.json"
    
    if not stage1_file.exists():
        print("❌ Stage 1 result not found. Run test_image_retrieval_stage.py first")
        return None
    
    with open(stage1_file) as f:
        stage1_result = json.load(f)
    
    # Create state
    initial_state = create_initial_state(
        question_id=TEST_QUESTION["id"],
        question_text=TEST_QUESTION["text"],
        question_options=TEST_QUESTION.get("options")
    )
    
    # Add template selection
    initial_state["template_selection"] = {
        "template_type": "INTERACTIVE_DIAGRAM",
        "confidence": 0.95,
        "is_production_ready": True
    }
    
    # Add image data
    initial_state["diagram_image"] = {
        "image_url": stage1_result["selected_image"]["image_url"],
        "source_url": stage1_result["selected_image"]["source_url"],
        "title": stage1_result["selected_image"]["title"]
    }
    
    # Add cleaned image if available
    if stage2_file.exists():
        with open(stage2_file) as f:
            stage2_result = json.load(f)
        if stage2_result.get("cleaned_image_path"):
            initial_state["cleaned_image_path"] = stage2_result["cleaned_image_path"]
    
    # Add domain knowledge
    initial_state["domain_knowledge"] = {
        "canonical_labels": CANONICAL_LABELS,
        "query": "flower parts diagram",
        "acceptable_variants": {},
        "sources": []
    }
    
    # Add game plan
    initial_state["game_plan"] = {
        "required_labels": CANONICAL_LABELS
    }
    
    # Generate prompts
    try:
        logger.info("Generating SAM3 prompts with VLM")
        result_state = await sam3_prompt_generator_agent(initial_state)
        
        sam3_prompts = result_state.get("sam3_prompts")
        if not sam3_prompts:
            logger.error("No SAM3 prompts generated")
            print("❌ No SAM3 prompts generated")
            return None
        
        logger.info("SAM3 prompts generated successfully",
                   prompts_count=len(sam3_prompts),
                   labels=list(sam3_prompts.keys()))
        
        print("✅ SAM3 prompts generated successfully")
        print(f"   Prompts generated: {len(sam3_prompts)}")
        print()
        
        print("Generated Prompts:")
        for label, prompt in sam3_prompts.items():
            prompt_length = len(prompt.split())
            length_indicator = "✅" if prompt_length <= 3 else "⚠️"
            print(f"  {length_indicator} {label:12} → \"{prompt}\" ({prompt_length} words)")
        print()
        
        # Validate prompt length (should be short - 1-3 words ideal)
        short_prompts = sum(1 for p in sam3_prompts.values() if len(p.split()) <= 3)
        long_prompts = len(sam3_prompts) - short_prompts
        
        if long_prompts > 0:
            print(f"⚠️ Warning: {long_prompts} prompts are longer than 3 words")
            print("   SAM3 works best with short noun phrases (1-3 words)")
        else:
            print("✅ All prompts are short (≤3 words) - optimal for SAM3")
        print()
        
        # Save result
        output_file = output_dir / "stage2.5_sam3_prompts.json"
        result = {
            "stage": "sam3_prompt_generation",
            "timestamp": datetime.now().isoformat(),
            "sam3_prompts": sam3_prompts,
            "labels": CANONICAL_LABELS,
            "prompt_statistics": {
                "total": len(sam3_prompts),
                "short_prompts": short_prompts,
                "long_prompts": long_prompts,
                "avg_length": sum(len(p.split()) for p in sam3_prompts.values()) / len(sam3_prompts)
            }
        }
        
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"✅ Result saved to: {output_file}")
        print()
        print("=" * 80)
        print("MANUAL VERIFICATION:")
        print("=" * 80)
        print("1. Check that prompts are SHORT (1-3 words ideal)")
        print("2. Verify prompts are descriptive but concise")
        print("3. Ensure prompts match the intended labels")
        print("4. Example good prompts: 'petal', 'flower petal', 'stamen'")
        print("5. Example bad prompts: 'the petal of a flower', 'the stamen with anther'")
        print()
        
        return result
        
    except Exception as e:
        logger.error("SAM3 prompt generation failed", exc_info=True, error=str(e))
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_prompt_generation())
    sys.exit(0 if result else 1)
