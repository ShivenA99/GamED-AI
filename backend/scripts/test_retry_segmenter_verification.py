#!/usr/bin/env python3
"""
Test Retry from diagram_image_segmenter - Direct Database Approach

Creates a test scenario directly in the database, then tests retry
to verify fallback behavior (no checkpoint before early stage).
"""

import sys
import os
import uuid
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, init_db
from app.db.models import PipelineRun, StageExecution, Question, Process
from app.agents.instrumentation import save_stage_checkpoint
from app.routes.observability import reconstruct_state_before_stage


def create_test_run_with_segmenter():
    """Create a test run with diagram_image_segmenter stage"""
    db = SessionLocal()
    init_db()
    
    try:
        unique_id = f"test-segmenter-{uuid.uuid4().hex[:8]}"
        
        # Create test data
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
        # Simulate that early stages don't have checkpoints yet
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
        
        # Create stages WITHOUT checkpoints but WITH output snapshots
        # This simulates early pipeline where checkpoints aren't saved yet
        stage_outputs = {
            "input_enhancer": {"pedagogical_context": {"bloom_level": "application"}},
            "domain_knowledge_retriever": {"domain_knowledge": {"canonical_labels": ["nucleus", "mitochondria", "cell membrane"]}},
            "router": {"template_selection": {"template_type": "INTERACTIVE_DIAGRAM"}},
            "game_planner": {"game_plan": {"title": "Plant Cell Labeling"}},
            "scene_generator": {"scene_data": {"assets": []}},
            "diagram_image_retriever": {"diagram_image": {"image_url": "https://example.com/cell.jpg"}},
            "image_label_remover": {"cleaned_image_path": "/tmp/cleaned.jpg"},
            "sam3_prompt_generator": {"sam3_prompts": {"nucleus": "the central organelle", "mitochondria": "the energy-producing organelle"}},
        }
        
        for stage_name, stage_order in stages_before:
            stage = StageExecution(
                id=f"{unique_id}-stage-{stage_order}",
                run_id=run.id,
                stage_name=stage_name,
                stage_order=stage_order,
                status="success",
                checkpoint_id=None,  # No checkpoints before diagram_image_segmenter
                output_snapshot=stage_outputs.get(stage_name, {})
            )
            db.add(stage)
        
        # diagram_image_segmenter failed
        segmenter_stage = StageExecution(
            id=f"{unique_id}-stage-9",
            run_id=run.id,
            stage_name="diagram_image_segmenter",
            stage_order=9,
            status="failed",
            checkpoint_id=None,
            error_message="Test failure for retry verification"
        )
        db.add(segmenter_stage)
        db.commit()
        
        print(f"✅ Created test run: {run.id}")
        return run.id
        
    finally:
        db.close()


async def verify_retry_logic(run_id: str):
    """Verify retry logic finds checkpoint (or lack thereof)"""
    db = SessionLocal()
    try:
        # Check for checkpoint before diagram_image_segmenter
        segmenter_stage = db.query(StageExecution).filter(
            StageExecution.run_id == run_id,
            StageExecution.stage_name == "diagram_image_segmenter"
        ).first()
        
        if not segmenter_stage:
            print("❌ diagram_image_segmenter stage not found")
            return
        
        # Find checkpoint before target stage (same logic as retry function)
        previous_stage = db.query(StageExecution).filter(
            StageExecution.run_id == run_id,
            StageExecution.stage_order < segmenter_stage.stage_order,
            StageExecution.checkpoint_id.isnot(None)
        ).order_by(StageExecution.stage_order.desc()).first()
        
        if previous_stage:
            print(f"✅ Found checkpoint: {previous_stage.checkpoint_id[:40]}...")
            print(f"   From stage: {previous_stage.stage_name} (order={previous_stage.stage_order})")
            print("   Expected: Will use checkpoint for retry")
            return previous_stage.checkpoint_id
        else:
            print("⚠️  No checkpoint found before diagram_image_segmenter")
            print("   Expected: Will use fallback (full graph execution)")
            return None
        
    finally:
        db.close()


def main():
    print("=" * 70)
    print("Test: Retry from diagram_image_segmenter (Fallback Expected)")
    print("=" * 70)
    print()
    
    # Step 1: Create test scenario
    print("Step 1: Creating test scenario in database...")
    run_id = create_test_run_with_segmenter()
    print()
    
    # Step 2: Verify checkpoint logic
    print("Step 2: Checking for checkpoint before diagram_image_segmenter...")
    checkpoint_id = asyncio.run(verify_retry_logic(run_id))
    print()
    
    # Step 3: Test retry via API
    print("Step 3: Testing retry from diagram_image_segmenter via API...")
    import requests
    
    try:
        response = requests.post(
            f"http://localhost:8000/api/observability/runs/{run_id}/retry",
            json={"from_stage": "diagram_image_segmenter"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            new_run_id = result.get("new_run_id")
            print(f"✅ Retry started: {new_run_id}")
            print()
            print("Step 4: Check backend logs for:")
            if checkpoint_id:
                print("   - 'Resuming from checkpoint' message")
            else:
                print("   - 'No checkpoint available... using full graph execution' message (expected)")
            print()
            print(f"   View new run: http://localhost:3000/pipeline/runs/{new_run_id}")
            print()
            print("   Expected behavior:")
            if checkpoint_id:
                print("   - Only stages after diagram_image_segmenter should execute")
            else:
                print("   - Full graph execution (fallback mode)")
                print("   - All stages execute, but state is restored from previous stages")
        else:
            print(f"❌ Retry failed: {response.status_code}")
            print(f"   {response.text}")
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
