#!/usr/bin/env python3
"""
Verify Retry from diagram_image_segmenter Stage

Checks existing runs or creates a test scenario to verify retry from
diagram_image_segmenter uses fallback behavior (since it's early in pipeline).
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import PipelineRun, StageExecution
from app.routes.observability import reconstruct_state_before_stage
import asyncio

async def verify_retry_from_segmenter():
    """Verify retry from diagram_image_segmenter stage"""
    print("=" * 70)
    print("Verifying Retry from diagram_image_segmenter Stage")
    print("=" * 70)
    print()
    
    db = SessionLocal()
    
    try:
        # Find a run with diagram_image_segmenter stage
        segmenter_stage = db.query(StageExecution).filter(
            StageExecution.stage_name == "diagram_image_segmenter"
        ).first()
        
        if not segmenter_stage:
            print("⚠️  No existing runs with diagram_image_segmenter stage found")
            print("   Creating test scenario...")
            
            # Create test scenario
            from app.db.models import Question, Process
            import uuid
            
            question = Question(
                id=f"test-segmenter-{uuid.uuid4().hex[:8]}",
                text="Label the parts of a plant cell",
                options=[]
            )
            db.add(question)
            
            process = Process(
                id=f"test-segmenter-p-{uuid.uuid4().hex[:8]}",
                question_id=question.id,
                status="processing",
                thread_id=f"test-segmenter-t-{uuid.uuid4().hex[:8]}"
            )
            db.add(process)
            
            run = PipelineRun(
                id=f"test-segmenter-run-{uuid.uuid4().hex[:8]}",
                process_id=process.id,
                run_number=1,
                topology="T1",
                status="failed",
                retry_depth=0
            )
            db.add(run)
            
            # Create stages leading up to diagram_image_segmenter
            stages = [
                ("input_enhancer", 1, "checkpoint-1"),
                ("domain_knowledge_retriever", 2, "checkpoint-2"),
                ("router", 3, "checkpoint-3"),
                ("game_planner", 4, "checkpoint-4"),
                ("scene_generator", 5, "checkpoint-5"),
                ("diagram_image_retriever", 6, "checkpoint-6"),
                ("image_label_remover", 7, "checkpoint-7"),
                ("sam3_prompt_generator", 8, "checkpoint-8"),
                ("diagram_image_segmenter", 9, None),  # This stage failed, no checkpoint
            ]
            
            for stage_name, stage_order, checkpoint_id in stages:
                stage = StageExecution(
                    id=f"test-segmenter-stage-{stage_order}",
                    run_id=run.id,
                    stage_name=stage_name,
                    stage_order=stage_order,
                    status="success" if checkpoint_id else "failed",
                    checkpoint_id=checkpoint_id
                )
                db.add(stage)
            
            db.commit()
            segmenter_stage = db.query(StageExecution).filter(
                StageExecution.run_id == run.id,
                StageExecution.stage_name == "diagram_image_segmenter"
            ).first()
            
            print(f"✅ Created test run: {run.id}")
        
        run_id = segmenter_stage.run_id
        print(f"Using run: {run_id}")
        print(f"Target stage: diagram_image_segmenter (order={segmenter_stage.stage_order})")
        print()
        
        # Check for checkpoint before diagram_image_segmenter
        print("Step 1: Checking for checkpoint before diagram_image_segmenter...")
        previous_stage = db.query(StageExecution).filter(
            StageExecution.run_id == run_id,
            StageExecution.stage_order < segmenter_stage.stage_order,
            StageExecution.checkpoint_id.isnot(None)
        ).order_by(StageExecution.stage_order.desc()).first()
        
        if previous_stage:
            print(f"✅ Found checkpoint: {previous_stage.checkpoint_id[:40]}...")
            print(f"   From stage: {previous_stage.stage_name} (order={previous_stage.stage_order})")
            print("   Expected: Should use checkpoint for retry")
        else:
            print("⚠️  No checkpoint found before diagram_image_segmenter")
            print("   Expected: Should use fallback (full graph execution)")
        print()
        
        # Test state reconstruction
        print("Step 2: Testing state reconstruction before diagram_image_segmenter...")
        try:
            state = await reconstruct_state_before_stage(
                run_id=run_id,
                from_stage="diagram_image_segmenter",
                db=db
            )
            
            if state:
                print("✅ State reconstruction successful")
                print(f"   State keys: {list(state.keys())[:10]}...")
                
                # Check required keys for diagram_image_segmenter
                required_keys = ["diagram_image", "sam3_prompts", "cleaned_image_path"]
                missing_keys = [k for k in required_keys if k not in state]
                
                if missing_keys:
                    print(f"⚠️  Missing required keys: {missing_keys}")
                else:
                    print("✅ All required keys present")
            else:
                print("❌ State reconstruction failed")
        except Exception as e:
            print(f"❌ Error in state reconstruction: {e}")
        print()
        
        # Simulate retry logic
        print("Step 3: Simulating retry logic...")
        if previous_stage and previous_stage.checkpoint_id:
            print(f"   Would use checkpoint: {previous_stage.checkpoint_id[:40]}...")
            print("   Config: {'configurable': {'thread_id': '<new_run_id>', 'checkpoint_id': '...'}}")
            print("   Expected: LangGraph resumes from checkpoint")
        else:
            print("   No checkpoint available")
            print("   Config: {'configurable': {'thread_id': '<new_run_id>'}}")
            print("   Expected: Full graph execution with restored state (fallback)")
        print()
        
        print("=" * 70)
        print("Verification Complete")
        print("=" * 70)
        print()
        print("Summary:")
        if previous_stage and previous_stage.checkpoint_id:
            print("✅ Checkpoint found - retry will use checkpoint resume")
        else:
            print("⚠️  No checkpoint - retry will use fallback (full graph)")
        print()
        print(f"To test actual retry, use:")
        print(f"  curl -X POST http://localhost:8000/api/observability/runs/{run_id}/retry \\")
        print(f"    -H 'Content-Type: application/json' \\")
        print(f"    -d '{{\"from_stage\": \"diagram_image_segmenter\"}}'")
        
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(verify_retry_from_segmenter())
