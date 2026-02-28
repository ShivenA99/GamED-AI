#!/usr/bin/env python3
"""
Test Retry from diagram_image_segmenter Stage

Creates a full pipeline run, waits for diagram_image_segmenter to complete,
then retries from that stage to verify fallback behavior (since it's early
in the image pipeline and may not have a checkpoint before it).
"""

import sys
import os
import time
import requests
import json
from pathlib import Path
from typing import Optional, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.db.models import PipelineRun, StageExecution

API_BASE = "http://localhost:8000"


def wait_for_stage(run_id: str, stage_name: str, timeout: int = 300) -> bool:
    """Wait for a specific stage to complete"""
    print(f"Waiting for stage '{stage_name}' to complete in run {run_id}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{API_BASE}/api/observability/runs/{run_id}/stages")
            if response.status_code == 200:
                data = response.json()
                stages = data.get("stages", [])
                
                for stage in stages:
                    if stage.get("stage_name") == stage_name:
                        status = stage.get("status")
                        print(f"  Stage '{stage_name}' status: {status}")
                        
                        if status in ["success", "failed", "degraded"]:
                            return True
                        elif status == "running":
                            print(f"  Stage is running...")
                
                print(f"  Stage '{stage_name}' not found yet, checking again in 5s...")
                time.sleep(5)
            else:
                print(f"  API returned {response.status_code}, retrying...")
                time.sleep(5)
        except Exception as e:
            print(f"  Error checking stage: {e}, retrying...")
            time.sleep(5)
    
    print(f"  Timeout waiting for stage '{stage_name}'")
    return False


def get_stage_checkpoint(run_id: str, stage_name: str) -> Optional[str]:
    """Get checkpoint_id for a specific stage"""
    try:
        response = requests.get(f"{API_BASE}/api/observability/runs/{run_id}/stages")
        if response.status_code == 200:
            data = response.json()
            stages = data.get("stages", [])
            
            for stage in stages:
                if stage.get("stage_name") == stage_name:
                    return stage.get("checkpoint_id")
    except Exception as e:
        print(f"Error getting checkpoint: {e}")
    return None


def check_checkpoint_before_stage(run_id: str, target_stage: str) -> Optional[str]:
    """Check if there's a checkpoint before the target stage"""
    db = SessionLocal()
    try:
        # Get target stage order
        target_stage_exec = db.query(StageExecution).filter(
            StageExecution.run_id == run_id,
            StageExecution.stage_name == target_stage
        ).first()
        
        if not target_stage_exec:
            return None
        
        # Find checkpoint before target stage
        previous_stage = db.query(StageExecution).filter(
            StageExecution.run_id == run_id,
            StageExecution.stage_order < target_stage_exec.stage_order,
            StageExecution.checkpoint_id.isnot(None)
        ).order_by(StageExecution.stage_order.desc()).first()
        
        if previous_stage:
            return previous_stage.checkpoint_id
        return None
    finally:
        db.close()


def main():
    print("=" * 70)
    print("Test: Retry from diagram_image_segmenter Stage")
    print("=" * 70)
    print()
    
    # Step 1: Create a new pipeline run
    print("Step 1: Creating new pipeline run...")
    question_text = "Label the parts of a plant cell diagram showing nucleus, mitochondria, and cell membrane"
    
    try:
        response = requests.post(
            f"{API_BASE}/api/generate",
            params={
                "question_text": question_text,
                "question_options": None
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create pipeline run: {response.status_code}")
            print(f"   Response: {response.text}")
            return
        
        result = response.json()
        run_id = result.get("run_id")
        process_id = result.get("process_id")
        
        if not run_id:
            print(f"❌ No run_id in response: {result}")
            return
        
        print(f"✅ Created pipeline run: {run_id}")
        print(f"   Process ID: {process_id}")
        print()
        
    except Exception as e:
        print(f"❌ Error creating pipeline run: {e}")
        return
    
    # Step 2: Wait for diagram_image_segmenter to complete
    print("Step 2: Waiting for diagram_image_segmenter stage to complete...")
    if not wait_for_stage(run_id, "diagram_image_segmenter", timeout=600):
        print("❌ Timeout waiting for diagram_image_segmenter")
        return
    
    print("✅ diagram_image_segmenter stage completed")
    print()
    
    # Step 3: Check checkpoint before diagram_image_segmenter
    print("Step 3: Checking for checkpoint before diagram_image_segmenter...")
    checkpoint_before = check_checkpoint_before_stage(run_id, "diagram_image_segmenter")
    
    if checkpoint_before:
        print(f"✅ Found checkpoint before diagram_image_segmenter: {checkpoint_before[:30]}...")
        print("   Expected: Should use checkpoint for retry")
    else:
        print("⚠️  No checkpoint found before diagram_image_segmenter")
        print("   Expected: Should use fallback (full graph execution)")
    print()
    
    # Step 4: Retry from diagram_image_segmenter
    print("Step 4: Retrying from diagram_image_segmenter stage...")
    try:
        retry_response = requests.post(
            f"{API_BASE}/api/observability/runs/{run_id}/retry",
            json={
                "from_stage": "diagram_image_segmenter"
            }
        )
        
        if retry_response.status_code != 200:
            print(f"❌ Retry failed: {retry_response.status_code}")
            print(f"   Response: {retry_response.text}")
            return
        
        retry_result = retry_response.json()
        new_run_id = retry_result.get("new_run_id")
        
        if not new_run_id:
            print(f"❌ No new_run_id in retry response: {retry_result}")
            return
        
        print(f"✅ Retry started: {new_run_id}")
        print(f"   Parent run: {run_id}")
        print()
        
    except Exception as e:
        print(f"❌ Error starting retry: {e}")
        return
    
    # Step 5: Monitor retry execution and check logs
    print("Step 5: Monitoring retry execution...")
    print("   Check backend logs for:")
    print("   - 'Resuming from checkpoint' (if checkpoint found)")
    print("   - 'No checkpoint available... using full graph execution' (if fallback)")
    print()
    
    # Wait a bit and check the new run status
    time.sleep(10)
    
    try:
        new_run_response = requests.get(f"{API_BASE}/api/observability/runs/{new_run_id}")
        if new_run_response.status_code == 200:
            new_run_data = new_run_response.json()
            status = new_run_data.get("status")
            print(f"   New run status: {status}")
            
            # Check stages in new run
            stages_response = requests.get(f"{API_BASE}/api/observability/runs/{new_run_id}/stages")
            if stages_response.status_code == 200:
                stages_data = stages_response.json()
                stages = stages_data.get("stages", [])
                
                # Find which stages have executed
                executed_stages = [s for s in stages if s.get("status") in ["success", "running", "failed"]]
                stage_names = [s.get("stage_name") for s in executed_stages]
                
                print(f"   Executed stages: {', '.join(stage_names[:10])}")
                
                # Check if early stages executed (would indicate fallback)
                early_stages = ["input_enhancer", "domain_knowledge_retriever", "router"]
                has_early_stages = any(stage in stage_names for stage in early_stages for stage_names in [stage_names])
                
                if any(s in stage_names for s in early_stages):
                    print("   ⚠️  Early stages executed - indicates fallback behavior (full graph)")
                else:
                    print("   ✅ Only later stages executed - indicates checkpoint resume")
        
    except Exception as e:
        print(f"   Error checking retry status: {e}")
    
    print()
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)
    print()
    print("Next steps:")
    print(f"1. Check backend logs for checkpoint usage messages")
    print(f"2. View run details: http://localhost:3000/pipeline/runs/{new_run_id}")
    print(f"3. Check database for checkpoint_id values")
    print()


if __name__ == "__main__":
    main()
