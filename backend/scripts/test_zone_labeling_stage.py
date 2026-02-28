#!/usr/bin/env python3
"""
Integration Test: Zone Labeling Stage

Tests the diagram_zone_labeler agent independently.
Verifies VLM labeling of segments.
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from PIL import Image
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_config import setup_logging, get_logger
from app.services.vlm_service import label_zone_with_vlm, VLMError

setup_logging(level="INFO", log_to_file=False)
logger = get_logger("test_zone_labeling_stage")

REQUIRED_LABELS = ["petal", "sepal", "stamen", "pistil", "ovary", "receptacle"]


def _pick_label_from_response(response: str, candidates: list) -> str:
    """Extract label from VLM response"""
    lowered = response.lower()
    for label in candidates:
        if label.lower() in lowered:
            return label
    return None


async def test_zone_labeling():
    """Test zone labeling with VLM"""
    print("=" * 80)
    print("INTEGRATION TEST: Zone Labeling Stage")
    print("=" * 80)
    print()
    
    # Load previous stage result
    output_dir = Path(__file__).parent.parent / "pipeline_outputs" / "integration_tests"
    stage3_file = output_dir / "stage3_segmentation.json"
    
    if not stage3_file.exists():
        print("❌ Stage 3 result not found. Run test_segmentation_stage.py first")
        return None
    
    with open(stage3_file) as f:
        stage3_result = json.load(f)
    
    image_path = stage3_result["image_path"]
    segments = stage3_result["segments"]
    
    print(f"Using image: {image_path}")
    print(f"Segments to label: {len(segments)}")
    print(f"Required labels: {', '.join(REQUIRED_LABELS)}")
    print()
    
    # Load image
    try:
        image_obj = Image.open(image_path).convert("RGB")
        image_bytes = Path(image_path).read_bytes()
        width, height = image_obj.size
        print(f"✅ Image loaded: {width}x{height}")
        print()
    except Exception as e:
        logger.error("Failed to load image", exc_info=True, error=str(e))
        print(f"❌ Failed to load image: {e}")
        return None
    
    # Label each segment
    zones = []
    labels = []
    vlm_success_count = 0
    vlm_failure_count = 0
    fallback_count = 0
    used_labels = set()
    
    print("Labeling segments with VLM...")
    print()
    
    for idx, segment in enumerate(segments, start=1):
        label_choice = None
        labeling_method = "fallback"
        
        # Try VLM labeling
        if image_bytes:
            prompt = (
                "Identify the best matching label for this diagram part. "
                f"Choose only from: {', '.join(REQUIRED_LABELS)}. "
                "Reply with the exact label name only."
            )
            
            try:
                # Use full image or crop if bbox available
                zone_bytes = image_bytes
                if "bbox" in segment:
                    try:
                        bbox = segment["bbox"]
                        x, y = int(bbox.get("x", 0)), int(bbox.get("y", 0))
                        w, h = int(bbox.get("width", 0)), int(bbox.get("height", 0))
                        crop = image_obj.crop((x, y, x + w, y + h))
                        buffer = BytesIO()
                        crop.save(buffer, format="PNG")
                        zone_bytes = buffer.getvalue()
                    except Exception:
                        zone_bytes = image_bytes
                
                # Use llava:7b explicitly for testing
                vlm_model = os.getenv("VLM_MODEL", "llava:7b")
                response = await label_zone_with_vlm(
                    image_bytes=zone_bytes,
                    candidate_labels=REQUIRED_LABELS,
                    prompt=prompt,
                    model=vlm_model,
                )
                label_choice = _pick_label_from_response(response, REQUIRED_LABELS)
                
                if label_choice:
                    labeling_method = "vlm"
                    vlm_success_count += 1
                    print(f"  Segment {idx}: ✅ VLM labeled as '{label_choice}'")
                else:
                    vlm_failure_count += 1
                    print(f"  Segment {idx}: ⚠️ VLM response didn't match labels: {response[:50]}")
                    
            except VLMError as e:
                vlm_failure_count += 1
                error_msg = str(e)
                print(f"  Segment {idx}: ❌ VLM error: {error_msg[:100]}")
                if "404" in error_msg or "not found" in error_msg.lower():
                    pass  # Already printed
                elif "connection" in error_msg.lower():
                    pass  # Already printed
        
        # Fallback to sequential assignment
        if not label_choice:
            label_choice = next((l for l in REQUIRED_LABELS if l not in used_labels), REQUIRED_LABELS[0])
            fallback_count += 1
            labeling_method = "sequential-fallback"
            print(f"  Segment {idx}: ⚠️ Fallback assigned '{label_choice}'")
        
        used_labels.add(label_choice)
        
        # Calculate zone position
        if "center_px" in segment:
            cx = float(segment["center_px"]["x"])
            cy = float(segment["center_px"]["y"])
            x = round((cx / width) * 100, 2)
            y = round((cy / height) * 100, 2)
        else:
            x = float(segment.get("x", 50))
            y = float(segment.get("y", 50))
        
        radius = float(segment.get("radius", 10))
        
        # Generate unique zone ID (same logic as agent)
        def _slugify(value: str) -> str:
            import re
            return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        
        base_zone_id = _slugify(label_choice) or f"zone_{idx}"
        zone_id = base_zone_id
        zone_id_counter = 1
        existing_zone_ids = {z.get("id") for z in zones}
        while zone_id in existing_zone_ids:
            zone_id = f"{base_zone_id}_{zone_id_counter}"
            zone_id_counter += 1
        
        zones.append({
            "id": zone_id,
            "label": label_choice,
            "x": x,
            "y": y,
            "radius": radius,
        })
        labels.append({
            "id": f"label_{zone_id}",
            "text": label_choice,
            "correctZoneId": zone_id,
        })
    
    print()
    
    # Summary
    primary_method = "vlm" if vlm_success_count > 0 else "sequential-fallback"
    fallback_used = fallback_count > 0
    
    print("=" * 80)
    print("Labeling Summary")
    print("=" * 80)
    print(f"Total segments: {len(segments)}")
    print(f"VLM successful: {vlm_success_count}")
    print(f"VLM failed: {vlm_failure_count}")
    print(f"Fallback used: {fallback_count}")
    print(f"Primary method: {primary_method}")
    print(f"Fallback used: {fallback_used}")
    print()
    
    if fallback_used:
        print("⚠️ WARNING: Some segments used fallback labeling")
        print("   Install and start Ollama VLM for semantic verification:")
        print("   ./scripts/setup_ollama.sh")
        print()
    
    # Validate all labels found
    found_labels = {z["label"].lower() for z in zones}
    required_set = {l.lower() for l in REQUIRED_LABELS}
    missing_labels = required_set - found_labels
    
    if missing_labels:
        print(f"⚠️ Missing labels: {', '.join(missing_labels)}")
    else:
        print("✅ All required labels found")
    print()
    
    # Save result
    output_file = output_dir / "stage4_zone_labeling.json"
    result = {
        "stage": "zone_labeling",
        "timestamp": datetime.now().isoformat(),
        "image_path": image_path,
        "primary_method": primary_method,
        "fallback_used": fallback_used,
        "vlm_success_count": vlm_success_count,
        "vlm_failure_count": vlm_failure_count,
        "fallback_count": fallback_count,
        "zones": zones,
        "labels": labels,
        "required_labels": REQUIRED_LABELS,
        "missing_labels": list(missing_labels)
    }
    
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Result saved to: {output_file}")
    print()
    print("=" * 80)
    print("MANUAL VERIFICATION:")
    print("=" * 80)
    print("1. Check that zone labels match actual image regions")
    print("2. Verify labels are semantically correct (not just sequential)")
    print("3. If using fallback, labels may be incorrect")
    print()
    
    return result


if __name__ == "__main__":
    result = asyncio.run(test_zone_labeling())
    sys.exit(0 if result else 1)
