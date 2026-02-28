#!/usr/bin/env python3
"""
Test Retry from diagram_image_segmenter with Fallback

Creates a test run where diagram_image_segmenter failed, then tests retry
to verify fallback behavior (no checkpoint before this early stage).
"""

import sys
import os
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, init_db
from app.db.models import PipelineRun, StageExecution, Question, Process
from app.agents.instrumentation import save_stage_checkpoint

def create_test_scenario():
    """Create a test run with diagram_image_segmenter failed"""
    db = SessionLocal()
    init_db()
    
    try:
        # Create test data
        unique_id = f"test-segmenter-retry-{uuid.uuid4().hex[:8]}"
        
        question = Question(
            id=f"{unique_id}-q",
            text="Label the parts of a plant cell diagram",
            options=[]
        )
        db.add(question)
        
        process = Process(
            id=f"{unique_id}-p",
            question_id=question.id,
            status="processing",
            thread_id=f"{unique_id}-t"
        )
        db.add(process)
        
        run = PipelineRun(
            id=f"{unique_id}-run",
            process_id=process.id,
            run_number=1,
            topology="T1",
            status="failed",
            retry_depth=0,
            config_snapshot={
                "question_id": question.id,
                "question_text": question.text,
                "initial_state": {
                    "question_id": question.id,
                    "question_text": question.text,
                    "question_options": []
                }
            }
        )
        db.add(run)
        db.commit()
        
        # Create stages leading up to diagram_image_segmenter
        # Note: Early stages might not have checkpoints in real runs
        stages_before = [
            ("input_enhancer", 1),
            ("domain_knowledge_retriever", 2),
            ("router", 3),
            ("game_planner", 4),
            ("scene_generator", 5),
            ("diagram_image_retriever", 6),
            ("image_label_remover", 7),
            ("sam3_prompt_generator", 8),
        ]
        
        # Create stages WITHOUT checkpoints before diagram_image_segmenter
        # This simulates early pipeline stages that haven't saved checkpoints yet
        for i, (stage_name, stage_order) in enumerate(stages_before):
            # No checkpoints before diagram_image_segmenter (to test fallback)
            checkpoint_id = None
            
            stage = StageExecution(
                id=f"{unique_id}-stage-{stage_order}",
                run_id=run.id,
                stage_name=stage_name,
                stage_order=stage_order,
                status="success",
                checkpoint_id=checkpoint_id
            )
            db.add(stage)
            
            # If checkpoint exists, also save it properly
            if checkpoint_id:
                save_stage_checkpoint(
                    run_id=run.id,
                    stage_name=stage_name,
                    checkpoint_id=checkpoint_id,
                    db=db
                )
        
        # diagram_image_segmenter failed (no checkpoint saved for it)
        segmenter_stage = StageExecution(
            id=f"{unique_id}-stage-9",
            run_id=run.id,
            stage_name="diagram_image_segmenter",
            stage_order=9,
            status="failed",
            checkpoint_id=None,  # Failed before checkpoint could be saved
            error_message="Test failure for retry verification"
        )
        db.add(segmenter_stage)
        db.commit()
        
        print(f"✅ Created test run: {run.id}")
        print(f"   diagram_image_segmenter stage: failed (order=9)")
        return run.id
        
    finally:
        db.close()


def check_checkpoint_before_segmenter(run_id: str):
    """Check if checkpoint exists before diagram_image_segmenter"""
    db = SessionLocal()
    try:
        segmenter_stage = db.query(StageExecution).filter(
            StageExecution.run_id == run_id,
            StageExecution.stage_name == "diagram_image_segmenter"
        ).first()
        
        if not segmenter_stage:
            return None, None
        
        # Find checkpoint before segmenter
        previous_stage = db.query(StageExecution).filter(
            StageExecution.run_id == run_id,
            StageExecution.stage_order < segmenter_stage.stage_order,
            StageExecution.checkpoint_id.isnot(None)
        ).order_by(StageExecution.stage_order.desc()).first()
        
        if previous_stage:
            return previous_stage.checkpoint_id, previous_stage.stage_name
        return None, None
        
    finally:
        db.close()


def main():
    print("=" * 70)
    print("Test: Retry from diagram_image_segmenter (Fallback Expected)")
    print("=" * 70)
    print()
    
    # Create test scenario
    print("Step 1: Creating test scenario...")
    run_id = create_test_scenario()
    print()
    
    # Check for checkpoint
    print("Step 2: Checking for checkpoint before diagram_image_segmenter...")
    checkpoint_id, checkpoint_stage = check_checkpoint_before_segmenter(run_id)
    
    if checkpoint_id:
        print(f"✅ Found checkpoint: {checkpoint_id[:40]}...")
        print(f"   From stage: {checkpoint_stage}")
        print("   ⚠️  Unexpected: Should not have checkpoint (early stage)")
    else:
        print("⚠️  No checkpoint found before diagram_image_segmenter")
        print("   ✅ Expected: Early stage, no checkpoint available")
        print("   Expected behavior: Fallback to full graph execution")
    print()
    
    # Test retry via API
    print("Step 3: Testing retry from diagram_image_segmenter...")
    import requests
    
    try:
        response = requests.post(
            "http://localhost:8000/api/observability/runs/{}/retry".format(run_id),
            json={"from_stage": "diagram_image_segmenter"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            new_run_id = result.get("new_run_id")
            print(f"✅ Retry started: {new_run_id}")
            print()
            print("Step 4: Check backend logs for:")
            print("   - 'No checkpoint available... using full graph execution' (expected)")
            print("   - OR 'Resuming from checkpoint' (if checkpoint found)")
            print()
            print(f"   View new run: http://localhost:3000/pipeline/runs/{new_run_id}")
        else:
            print(f"❌ Retry failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error calling retry API: {e}")
        print()
        print("Manual test command:")
        print(f"  curl -X POST http://localhost:8000/api/observability/runs/{run_id}/retry \\")
        print(f"    -H 'Content-Type: application/json' \\")
        print(f"    -d '{{\"from_stage\": \"diagram_image_segmenter\"}}'")
    
    print()
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
