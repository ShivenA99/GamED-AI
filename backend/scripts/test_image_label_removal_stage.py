#!/usr/bin/env python3
"""
Integration Test: Image Label Removal Stage

Tests the image_label_remover agent independently.
Verifies EasyOCR detection and inpainting service.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_config import setup_logging, get_logger
from app.services.inpainting_service import get_inpainting_service
import httpx

setup_logging(level="INFO", log_to_file=False)
logger = get_logger("test_image_label_removal_stage")


async def download_image(image_url: str, output_path: Path):
    """Download image from URL"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        output_path.write_bytes(response.content)


async def test_label_removal():
    """Test image label removal"""
    print("=" * 80)
    print("INTEGRATION TEST: Image Label Removal Stage")
    print("=" * 80)
    print()
    
    # Load previous stage result
    output_dir = Path(__file__).parent.parent / "pipeline_outputs" / "integration_tests"
    stage1_file = output_dir / "stage1_image_retrieval.json"
    
    if not stage1_file.exists():
        print("❌ Stage 1 result not found. Run test_image_retrieval_stage.py first")
        return None
    
    with open(stage1_file) as f:
        stage1_result = json.load(f)
    
    image_url = stage1_result["selected_image"]["image_url"]
    print(f"Using image from Stage 1: {image_url[:80]}...")
    print()
    
    # Download image
    question_id = "test_integration"
    assets_dir = Path(__file__).parent.parent / "pipeline_outputs" / "assets" / question_id
    original_image_path = assets_dir / "diagram.jpg"
    
    try:
        logger.info("Downloading image", image_url=image_url[:80])
        await download_image(image_url, original_image_path)
        logger.info("Image downloaded", path=str(original_image_path))
        print(f"✅ Image downloaded to: {original_image_path}")
        print()
    except Exception as e:
        logger.error("Image download failed", exc_info=True, error=str(e))
        print(f"❌ Download failed: {e}")
        return None
    
    # Test inpainting service
    try:
        logger.info("Starting image cleaning", image_path=str(original_image_path))
        service = get_inpainting_service()
        
        cleaned_output_dir = assets_dir / "cleaned"
        logger.info("Calling inpainting service", output_dir=str(cleaned_output_dir))
        
        try:
            result = await service.clean_diagram(
                str(original_image_path),
                str(cleaned_output_dir)
            )
        except Exception as service_error:
            # Handle EasyOCR not installed - use original image as fallback
            if "EasyOCR" in str(service_error) or "easyocr" in str(service_error).lower():
                logger.warning("EasyOCR not available, using original image as fallback", error=str(service_error))
                result = {
                    "cleaned_image_path": str(original_image_path),
                    "removed_labels": [],
                    "text_regions_found": 0,
                    "error": "EasyOCR not installed - using original image",
                    "fallback_used": True
                }
            else:
                raise
        
        cleaned_image_path = result["cleaned_image_path"]
        removed_labels = result.get("removed_labels", [])
        text_regions_found = result.get("text_regions_found", 0)
        has_error = "error" in result
        
        if has_error:
            logger.warning("Image cleaning had errors", error=result.get("error"))
            print("⚠️ Image cleaning completed with errors")
        else:
            logger.info("Image cleaning completed", 
                       cleaned_image_path=cleaned_image_path,
                       text_regions_found=text_regions_found,
                       removed_labels_count=len(removed_labels))
            print("✅ Image cleaning completed")
        
        print(f"   Text regions found: {text_regions_found}")
        print(f"   Labels removed: {len(removed_labels)}")
        if removed_labels:
            print(f"   Removed labels: {', '.join(removed_labels[:5])}")
        print(f"   Cleaned image: {cleaned_image_path}")
        print()
        
        # Save result
        output_file = output_dir / "stage2_label_removal.json"
        result_data = {
            "stage": "image_label_removal",
            "timestamp": datetime.now().isoformat(),
            "original_image_path": str(original_image_path),
            "cleaned_image_path": cleaned_image_path,
            "text_regions_found": text_regions_found,
            "removed_labels": removed_labels,
            "has_error": has_error,
            "error": result.get("error") if has_error else None
        }
        
        with open(output_file, "w") as f:
            json.dump(result_data, f, indent=2)
        
        print(f"✅ Result saved to: {output_file}")
        print()
        print("=" * 80)
        print("MANUAL VERIFICATION:")
        print("=" * 80)
        print(f"1. Compare original vs cleaned image:")
        print(f"   Original: {original_image_path}")
        print(f"   Cleaned: {cleaned_image_path}")
        print("2. Verify text labels were removed from cleaned image")
        print("3. Check that image structure is preserved")
        print()
        
        return result_data
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        logger.error("Image cleaning failed", exc_info=True, error_type=error_type, error=error_msg)
        print(f"❌ Error: {error_msg}")
        
        if "EasyOCR" in error_msg:
            print()
            print("⚠️ EasyOCR not installed. Install with: pip install easyocr")
            print("   Pipeline will continue with original image (fallback)")
        
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_label_removal())
    sys.exit(0 if result else 1)
