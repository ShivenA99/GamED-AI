#!/usr/bin/env python3
"""
Integration Test: Image Retrieval Stage

Tests the diagram_image_retriever agent independently.
Verifies Serper API integration and image selection logic.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logging_config import setup_logging, get_logger
from app.services.image_retrieval import build_image_query, search_diagram_images, select_best_image

setup_logging(level="INFO", log_to_file=False)
logger = get_logger("test_image_retrieval_stage")

# Test question
TEST_QUESTION = "Label the parts of a flower including the petal, sepal, stamen, pistil, ovary, and receptacle."
CANONICAL_LABELS = ["petal", "sepal", "stamen", "pistil", "ovary", "receptacle"]


async def test_image_retrieval():
    """Test image retrieval via Serper API"""
    print("=" * 80)
    print("INTEGRATION TEST: Image Retrieval Stage")
    print("=" * 80)
    print()
    
    logger.info("Starting image retrieval test", question=TEST_QUESTION)
    
    # Build query
    query = build_image_query(TEST_QUESTION, CANONICAL_LABELS)
    logger.info("Built image search query", query=query)
    print(f"Search Query: {query}")
    print()
    
    # Search for images
    try:
        logger.info("Searching for diagram images via Serper API")
        results = await search_diagram_images(query, max_results=5)
        logger.info(f"Found {len(results)} image results", result_count=len(results))
        
        print(f"Found {len(results)} image results:")
        for i, result in enumerate(results, 1):
            image_url = result.get("imageUrl") or result.get("image", "N/A")
            title = result.get("title") or result.get("source", "N/A")
            print(f"  {i}. {title[:60]}")
            print(f"     URL: {image_url[:80]}...")
        print()
        
        # Select best image
        best_image = select_best_image(results)
        if not best_image:
            logger.error("No usable image selected")
            print("❌ No usable image found")
            return None
        
        image_url = best_image.get("image_url") or best_image.get("imageUrl", "N/A")
        source_url = best_image.get("source_url") or best_image.get("link", "N/A")
        title = best_image.get("title") or best_image.get("source", "N/A")
        
        logger.info("Selected best image", 
                   image_url=image_url[:80],
                   source_url=source_url[:80],
                   title=title)
        
        print("✅ Best Image Selected:")
        print(f"   Title: {title}")
        print(f"   Image URL: {image_url}")
        print(f"   Source: {source_url}")
        print()
        
        # Save result for next stage
        output_dir = Path(__file__).parent.parent / "pipeline_outputs" / "integration_tests"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "stage1_image_retrieval.json"
        
        result = {
            "stage": "image_retrieval",
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "results_count": len(results),
            "selected_image": {
                "image_url": image_url,
                "source_url": source_url,
                "title": title,
                "license": best_image.get("license", "unknown")
            }
        }
        
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"✅ Result saved to: {output_file}")
        print()
        print("=" * 80)
        print("MANUAL VERIFICATION:")
        print("=" * 80)
        print(f"1. Open image URL in browser: {image_url}")
        print("2. Verify image shows a flower diagram")
        print("3. Check if image has text labels (will be removed in next stage)")
        print("4. Verify image is appropriate for educational use")
        print()
        
        return result
        
    except Exception as e:
        logger.error("Image retrieval failed", exc_info=True, error=str(e))
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_image_retrieval())
    sys.exit(0 if result else 1)
