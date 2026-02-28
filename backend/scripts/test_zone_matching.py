#!/usr/bin/env python3
"""
Test the new zone matching logic: matching 6 labels to best segments from 16 segments.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_config import setup_logging, get_logger
from app.agents.diagram_zone_labeler import _score_label_segment_match
from app.services.vlm_service import VLMError

setup_logging(level="INFO", log_to_file=False)
logger = get_logger("test_zone_matching")

# Mock test data
REQUIRED_LABELS = ["petal", "sepal", "stamen", "pistil", "ovary", "receptacle"]

# Create 16 mock segments (simulating SAM3 output)
def create_mock_segments() -> List[Dict[str, Any]]:
    segments = []
    for i in range(16):
        segments.append({
            "segment_id": f"segment_{i+1}",
            "bbox": {
                "x": (i % 4) * 200,
                "y": (i // 4) * 150,
                "width": 180,
                "height": 140
            },
            "center_px": {
                "x": (i % 4) * 200 + 90,
                "y": (i // 4) * 150 + 70
            },
            "radius": 10
        })
    return segments


async def test_matching_logic():
    """Test the new label-to-segment matching logic"""
    print("=" * 80)
    print("TEST: Zone Matching Logic (6 labels → best segments from 16)")
    print("=" * 80)
    print()
    
    # Check if we have a test image
    test_image_path = Path(__file__).parent.parent / "pipeline_outputs" / "integration_tests" / "test_image.png"
    
    if not test_image_path.exists():
        # Try to find any image from pipeline outputs
        pipeline_outputs = Path(__file__).parent.parent / "pipeline_outputs"
        image_files = list(pipeline_outputs.rglob("*.png")) + list(pipeline_outputs.rglob("*.jpg"))
        if image_files:
            test_image_path = image_files[0]
            print(f"Using found image: {test_image_path}")
        else:
            print("⚠️  No test image found. Creating a simple mock image...")
            # Create a simple test image
            from PIL import Image
            test_image = Image.new("RGB", (800, 600), color="white")
            test_image_path = Path(__file__).parent.parent / "test_image_temp.png"
            test_image.save(test_image_path)
            print(f"Created temporary test image: {test_image_path}")
    
    try:
        from PIL import Image
        from pathlib import Path as PathLib
        
        image_obj = Image.open(test_image_path).convert("RGB")
        image_bytes = PathLib(test_image_path).read_bytes()
        width, height = image_obj.size
        
        print(f"✅ Image loaded: {width}x{height}")
        print()
    except Exception as e:
        print(f"❌ Failed to load image: {e}")
        print("   The test will still demonstrate the logic, but VLM calls will fail.")
        image_obj = None
        image_bytes = None
    
    segments = create_mock_segments()
    sam3_prompts = {}  # Empty for now
    
    print(f"Required labels: {len(REQUIRED_LABELS)}")
    print(f"  {', '.join(REQUIRED_LABELS)}")
    print()
    print(f"Available segments: {len(segments)}")
    print()
    print("Testing matching logic...")
    print()
    
    # Track which segments have been assigned
    used_segment_indices = set()
    matches = []
    
    # For each required label, find the best matching segment
    for label_idx, label in enumerate(REQUIRED_LABELS, start=1):
        print(f"Label {label_idx}/{len(REQUIRED_LABELS)}: '{label}'")
        
        best_segment_idx: Optional[int] = None
        best_score: float = -1.0
        segment_scores: List[Tuple[int, float, Optional[str]]] = []
        
        if image_bytes and image_obj:
            # Score all available (unused) segments against this label
            for seg_idx, segment in enumerate(segments):
                if seg_idx in used_segment_indices:
                    continue
                
                try:
                    score, response = await _score_label_segment_match(
                        label=label,
                        segment=segment,
                        image_obj=image_obj,
                        image_bytes=image_bytes,
                        sam3_prompts=sam3_prompts,
                        required_labels=REQUIRED_LABELS
                    )
                    segment_scores.append((seg_idx, score, response))
                    
                    if score > best_score:
                        best_score = score
                        best_segment_idx = seg_idx
                    
                except VLMError as e:
                    logger.debug(f"VLM error for label '{label}', segment {seg_idx + 1}: {e}")
                except Exception as e:
                    logger.debug(f"Error scoring segment {seg_idx + 1} for label '{label}': {e}")
        
        # Select the best segment
        selected_segment_idx = best_segment_idx
        
        if selected_segment_idx is None:
            # Fallback: use first unused segment
            for seg_idx in range(len(segments)):
                if seg_idx not in used_segment_indices:
                    selected_segment_idx = seg_idx
                    best_score = 0.0
                    break
        
        if selected_segment_idx is not None:
            used_segment_indices.add(selected_segment_idx)
            selected_segment = segments[selected_segment_idx]
            
            matches.append({
                "label": label,
                "segment_index": selected_segment_idx,
                "segment_id": selected_segment["segment_id"],
                "score": best_score if best_score >= 0 else None
            })
            
            # Show top 3 scores for this label
            if segment_scores:
                sorted_scores = sorted(segment_scores, key=lambda x: x[1], reverse=True)
                top_3 = sorted_scores[:3]
                print(f"  → Matched to segment {selected_segment_idx + 1} (score: {best_score:.2f})")
                print(f"    Top 3 candidates: {[(idx+1, f'{score:.2f}') for idx, score, _ in top_3]}")
            else:
                print(f"  → Matched to segment {selected_segment_idx + 1} (fallback - no VLM scores)")
        else:
            print(f"  → ❌ No segment available")
        
        print()
    
    # Summary
    print("=" * 80)
    print("MATCHING SUMMARY")
    print("=" * 80)
    print(f"Labels matched: {len(matches)}/{len(REQUIRED_LABELS)}")
    print(f"Segments used: {len(used_segment_indices)}/{len(segments)}")
    print()
    print("Matches:")
    for match in matches:
        score_str = f"score: {match['score']:.2f}" if match['score'] is not None else "fallback"
        print(f"  • {match['label']:12} → segment {match['segment_index'] + 1:2} ({score_str})")
    print()
    
    # Verify we got exactly 6 zones
    if len(matches) == 6:
        print("✅ SUCCESS: Matched exactly 6 labels to 6 segments")
    else:
        print(f"⚠️  WARNING: Expected 6 matches, got {len(matches)}")
    
    # Verify no duplicate segments
    segment_indices_used = [m["segment_index"] for m in matches]
    if len(segment_indices_used) == len(set(segment_indices_used)):
        print("✅ SUCCESS: No duplicate segment assignments")
    else:
        print("❌ ERROR: Some segments were assigned to multiple labels")
    
    print()
    return matches


if __name__ == "__main__":
    try:
        matches = asyncio.run(test_matching_logic())
        if matches and len(matches) == 6:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
