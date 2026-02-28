#!/usr/bin/env python3
"""
Clean test run specifically for image retrieval verification.
Monitors each step closely, especially the image-related agents.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.state import create_initial_state
from app.agents.graph import get_compiled_graph
from app.db.database import SessionLocal
from app.db.models import Process, Question
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_step(step_name: str, status: str = "✅", details: str = ""):
    """Print a formatted step status"""
    print(f"\n{'='*60}")
    print(f"{status} {step_name}")
    if details:
        print(f"   {details}")
    print(f"{'='*60}")


async def test_image_retrieval_clean():
    """Run a clean test focusing on image retrieval"""
    
    question_text = "Label the parts of a flower including the petal, sepal, stamen, pistil, ovary, and receptacle"
    
    print("\n" + "="*60)
    print("🧪 CLEAN IMAGE RETRIEVAL TEST")
    print("="*60)
    print(f"Question: {question_text}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    db = SessionLocal()
    process_id = None
    
    try:
        # Create question
        question_id = str(uuid.uuid4())
        question = Question(
            id=question_id,
            text=question_text,
            options=None,
            created_at=datetime.utcnow()
        )
        db.add(question)
        db.commit()
        
        # Create process
        process_id = str(uuid.uuid4())
        thread_id = f"thread_{process_id}"
        
        process = Process(
            id=process_id,
            question_id=question_id,
            status="processing",
            thread_id=thread_id,
            created_at=datetime.utcnow()
        )
        db.add(process)
        db.commit()
        
        print_step("Setup", "✅", f"Process ID: {process_id}")
        
        # Create initial state
        initial_state = create_initial_state(
            question_id=question_id,
            question_text=question_text,
            question_options=None
        )
        
        # Get graph
        graph = get_compiled_graph()
        config = {"configurable": {"thread_id": thread_id}}
        
        print_step("Starting Pipeline", "🚀", "Streaming execution with monitoring...")
        
        # Track image-related steps
        image_steps = {
            "diagram_image_retriever": False,
            "image_label_remover": False,
            "diagram_image_segmenter": False,
            "diagram_zone_labeler": False,
        }
        
        start_time = time.time()
        final_state = None
        step_count = 0
        
        # Run with streaming to monitor each step
        async for event in graph.astream(initial_state, config):
            for node_name, node_state in event.items():
                if node_state and isinstance(node_state, dict):
                    step_count += 1
                    elapsed = time.time() - start_time
                    
                    # Check if this is an image-related step
                    is_image_step = node_name in image_steps
                    
                    if is_image_step:
                        image_steps[node_name] = True
                        print_step(
                            f"Step {step_count}: {node_name}",
                            "🖼️",
                            f"Image processing step (Elapsed: {elapsed:.1f}s)"
                        )
                        
                        # Detailed inspection for image steps
                        if node_name == "diagram_image_retriever":
                            diagram_image = node_state.get("diagram_image")
                            if diagram_image:
                                print(f"   ✅ Image retrieved!")
                                print(f"   📷 Image URL: {diagram_image.get('image_url', 'N/A')[:80]}...")
                                print(f"   🔗 Source: {diagram_image.get('source_url', 'N/A')[:80]}...")
                                print(f"   📝 Title: {diagram_image.get('title', 'N/A')[:60]}")
                            else:
                                print(f"   ❌ No image retrieved!")
                                
                        elif node_name == "image_label_remover":
                            cleaned_path = node_state.get("cleaned_image_path")
                            removed_labels = node_state.get("removed_labels", [])
                            if cleaned_path:
                                print(f"   ✅ Image cleaned!")
                                print(f"   📁 Cleaned image: {cleaned_path}")
                                print(f"   🗑️  Removed labels: {len(removed_labels)} labels")
                            else:
                                print(f"   ⚠️  No cleaned image (may have been skipped)")
                                
                        elif node_name == "diagram_image_segmenter":
                            segments = node_state.get("diagram_segments")
                            if segments:
                                num_segments = len(segments.get("segments", [])) if isinstance(segments, dict) else 0
                                print(f"   ✅ Image segmented!")
                                print(f"   🎯 Number of segments: {num_segments}")
                            else:
                                print(f"   ❌ Segmentation failed!")
                                
                        elif node_name == "diagram_zone_labeler":
                            zones = node_state.get("diagram_zones", [])
                            labels = node_state.get("diagram_labels", [])
                            retry = node_state.get("retry_image_search", False)
                            print(f"   ✅ Zones labeled!")
                            print(f"   🏷️  Zones found: {len(zones)}")
                            print(f"   🏷️  Labels: {len(labels)}")
                            if retry:
                                print(f"   ⚠️  Retry flag set: {retry}")
                    else:
                        # Regular step
                        print(f"\n✅ Step {step_count}: {node_name} (Elapsed: {elapsed:.1f}s)")
                    
                    final_state = node_state
        
        # Final summary
        total_time = time.time() - start_time
        print_step("Pipeline Complete", "✅", f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        
        # Image step verification
        print("\n" + "="*60)
        print("🖼️  IMAGE RETRIEVAL VERIFICATION")
        print("="*60)
        for step_name, completed in image_steps.items():
            status = "✅" if completed else "❌"
            print(f"{status} {step_name}: {'Completed' if completed else 'Not executed'}")
        
        # Check final state
        if final_state:
            diagram_image = final_state.get("diagram_image")
            cleaned_path = final_state.get("cleaned_image_path")
            zones = final_state.get("diagram_zones", [])
            labels = final_state.get("diagram_labels", [])
            
            print("\n" + "="*60)
            print("📊 FINAL STATE SUMMARY")
            print("="*60)
            print(f"✅ Diagram Image: {'Yes' if diagram_image else 'No'}")
            if diagram_image:
                print(f"   URL: {diagram_image.get('image_url', 'N/A')[:100]}")
            print(f"✅ Cleaned Image: {'Yes' if cleaned_path else 'No'}")
            if cleaned_path:
                print(f"   Path: {cleaned_path}")
            print(f"✅ Zones: {len(zones)}")
            print(f"✅ Labels: {len(labels)}")
            print(f"✅ Generation Complete: {final_state.get('generation_complete', False)}")
            
            # Update process
            is_complete = final_state.get("generation_complete", False)
            process.status = "completed" if is_complete else "error"
            process.current_agent = final_state.get("current_agent")
            process.error_message = final_state.get("error_message")
            process.progress_percent = 100 if is_complete else process.progress_percent
            process.completed_at = datetime.utcnow() if is_complete else None
            db.commit()
            
            print("\n" + "="*60)
            print("🎮 GAME READY")
            print("="*60)
            print(f"Process ID: {process_id}")
            print(f"View game: http://localhost:3000/game/{process_id}")
            print(f"Status API: http://localhost:8000/api/generate/{process_id}/status")
            print("="*60)
            
            return process_id, final_state
        else:
            print("\n❌ No final state received")
            return None, None
            
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        if process_id:
            process = db.query(Process).filter(Process.id == process_id).first()
            if process:
                process.status = "error"
                process.error_message = str(e)
                db.commit()
        print(f"\n❌ ERROR: {e}")
        return None, None
    finally:
        db.close()


if __name__ == "__main__":
    process_id, final_state = asyncio.run(test_image_retrieval_clean())
    
    if process_id:
        print(f"\n✅ Test completed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Test failed")
        sys.exit(1)
