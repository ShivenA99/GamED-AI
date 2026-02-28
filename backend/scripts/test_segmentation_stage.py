#!/usr/bin/env python3
"""
Integration Test: Segmentation Stage

Tests the diagram_image_segmenter agent independently.
Verifies SAM3/SAM segmentation on cleaned image.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_config import setup_logging, get_logger
from app.services.segmentation import sam_segment_image, fallback_segments

setup_logging(level="INFO", log_to_file=False)
logger = get_logger("test_segmentation_stage")

CANONICAL_LABELS = ["petal", "sepal", "stamen", "pistil", "ovary", "receptacle"]


async def test_segmentation():
    """Test image segmentation"""
    print("=" * 80)
    print("INTEGRATION TEST: Segmentation Stage")
    print("=" * 80)
    print()
    
    # Load previous stage results
    output_dir = Path(__file__).parent.parent / "pipeline_outputs" / "integration_tests"
    stage2_file = output_dir / "stage2_label_removal.json"
    stage2_5_file = output_dir / "stage2.5_sam3_prompts.json"
    
    if not stage2_file.exists():
        print("❌ Stage 2 result not found. Run test_image_label_removal_stage.py first")
        return None
    
    with open(stage2_file) as f:
        stage2_result = json.load(f)
    
    # Load SAM3 prompts if available
    sam3_prompts = None
    if stage2_5_file.exists():
        with open(stage2_5_file) as f:
            stage2_5_result = json.load(f)
            sam3_prompts = stage2_5_result.get("sam3_prompts")
            if sam3_prompts:
                print(f"✅ Loaded SAM3 prompts from Stage 2.5 ({len(sam3_prompts)} prompts)")
                print()
    
    # Prefer cleaned image, fallback to original
    image_path = stage2_result.get("cleaned_image_path") or stage2_result.get("original_image_path")
    
    if not Path(image_path).exists():
        print(f"❌ Image not found: {image_path}")
        return None
    
    print(f"Using image: {image_path}")
    print()
    
    # Test SAM segmentation
    try:
        if sam3_prompts:
            logger.info("Attempting MLX SAM3/SAM segmentation with prompts", 
                       image_path=image_path,
                       prompts_count=len(sam3_prompts))
            segments = sam_segment_image(image_path, text_prompts=sam3_prompts, labels=CANONICAL_LABELS)
        else:
            logger.info("Attempting SAM3/SAM segmentation (no prompts)", image_path=image_path)
            segments = sam_segment_image(image_path, labels=CANONICAL_LABELS)
        segmentation_method = "sam3_or_sam"
        logger.info("SAM segmentation successful", 
                   segments_count=len(segments),
                   method=segmentation_method)
        print(f"✅ Segmentation successful using SAM")
        print(f"   Method: {segmentation_method}")
        print(f"   Segments generated: {len(segments)}")
        print()
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        logger.warning("SAM unavailable, using fallback grid", 
                      error_type=error_type,
                      error=error_msg)
        print(f"⚠️ SAM segmentation failed: {error_msg}")
        print("   Using fallback grid segmentation")
        print()
        
        segments = fallback_segments(len(CANONICAL_LABELS))
        segmentation_method = "fallback-grid"
        logger.info("Fallback grid created", segments_count=len(segments))
    
    # Display segments
    print("Generated Segments:")
    for i, segment in enumerate(segments[:10], 1):  # Show first 10
        if "center_px" in segment:
            cx = segment["center_px"]["x"]
            cy = segment["center_px"]["y"]
            print(f"  {i}. Segment {segment.get('segment_id', i)}: center=({cx:.1f}, {cy:.1f})")
        else:
            x = segment.get("x", 0)
            y = segment.get("y", 0)
            print(f"  {i}. Segment {segment.get('segment_id', i)}: pos=({x:.1f}%, {y:.1f}%)")
    if len(segments) > 10:
        print(f"  ... and {len(segments) - 10} more")
    print()
    
    # Check if segments have label metadata (from SAM3 with prompts)
    segments_with_labels = sum(1 for s in segments if s.get("label"))
    if segments_with_labels > 0:
        print(f"✅ {segments_with_labels} segments have label metadata (from SAM3 prompts)")
        print()
    
    # Save result
    output_file = output_dir / "stage3_segmentation.json"
    result = {
        "stage": "segmentation",
        "timestamp": datetime.now().isoformat(),
        "image_path": image_path,
        "method": segmentation_method,
        "segments_count": len(segments),
        "segments": segments,
        "expected_labels": CANONICAL_LABELS,
        "used_sam3_prompts": bool(sam3_prompts),
        "prompts_count": len(sam3_prompts) if sam3_prompts else 0,
        "segments_with_labels": segments_with_labels
    }
    
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Result saved to: {output_file}")
    print()
    print("=" * 80)
    print("MANUAL VERIFICATION:")
    print("=" * 80)
    print("1. Check that segments align with actual image structures")
    print("2. Verify segment count matches expected labels count")
    print("3. If using fallback grid, note that zones are uniformly spaced")
    print("   (not semantically aligned - SAM3/SAM required for accuracy)")
    print()
    
    if segmentation_method == "fallback-grid":
        print("⚠️ WARNING: Using fallback grid. Install SAM3 for semantic segmentation:")
        print("   pip install sam3")
        print("   huggingface-cli login")
        print("   Or for Apple Silicon: ./scripts/setup_sam3_apple_silicon.sh")
        print()
    
    return result


if __name__ == "__main__":
    result = asyncio.run(test_segmentation())
    sys.exit(0 if result else 1)
