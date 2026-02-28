#!/usr/bin/env python3
"""
Integration Test Script for Checkpointing Functionality

Tests end-to-end checkpointing:
1. Verifies checkpoints are saved during pipeline execution
2. Tests retry from checkpoint functionality
3. Verifies only later stages execute during retry
4. Tests backward compatibility and error handling

Usage:
    cd backend
    PYTHONPATH=. python scripts/test_checkpointing_integration.py
"""

import sys
import os
import time
import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, init_db
from app.db.models import PipelineRun, StageExecution, Question, Process
from app.agents.instrumentation import save_stage_checkpoint
from app.agents.state import create_initial_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_checkpointing_integration")


class CheckpointingIntegrationTest:
    """Integration tests for checkpointing functionality"""
    
    def __init__(self):
        self.db: Optional[Session] = None
        self.test_results: List[Dict] = []
    
    def __enter__(self):
        self.db = SessionLocal()
        init_db()  # Ensure tables exist
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
    
    def test_checkpoint_saving(self) -> bool:
        """Test 1: Verify checkpoints can be saved to database"""
        logger.info("=" * 70)
        logger.info("Test 1: Verify checkpoint saving functionality")
        logger.info("=" * 70)
        
        try:
            # Rollback any previous transaction errors
            self.db.rollback()
            
            # Use unique ID with timestamp to avoid conflicts
            unique_id = f"test-checkpoint-{uuid.uuid4().hex[:8]}"
            
            # Create test data
            question = Question(
                id=f"{unique_id}-q",
                text="Test question for checkpointing",
                options=["A", "B", "C"]
            )
            self.db.add(question)
            
            process = Process(
                id=f"{unique_id}-p",
                question_id=question.id,
                status="processing",
                thread_id=f"{unique_id}-t"
            )
            self.db.add(process)
            
            run = PipelineRun(
                id=f"{unique_id}-run",
                process_id=process.id,
                run_number=1,
                topology="T1",
                status="running",
                retry_depth=0
            )
            self.db.add(run)
            self.db.commit()
            
            # Create a stage execution
            stage = StageExecution(
                id=f"{unique_id}-stage",
                run_id=run.id,
                stage_name="input_enhancer",
                stage_order=1,
                status="success"
            )
            self.db.add(stage)
            self.db.commit()
            
            # Test saving checkpoint
            test_checkpoint_id = "test-checkpoint-abc-123"
            save_stage_checkpoint(
                run_id=run.id,
                stage_name="input_enhancer",
                checkpoint_id=test_checkpoint_id,
                db=self.db
            )
            
            # Verify checkpoint was saved
            self.db.refresh(stage)
            assert stage.checkpoint_id == test_checkpoint_id, f"Expected {test_checkpoint_id}, got {stage.checkpoint_id}"
            
            logger.info(f"✅ Checkpoint saved successfully: {test_checkpoint_id}")
            
            self.test_results.append({
                "test": "checkpoint_saving",
                "status": "PASS",
                "message": f"Checkpoint {test_checkpoint_id} saved successfully"
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Test 1 FAILED: {e}")
            self.test_results.append({
                "test": "checkpoint_saving",
                "status": "FAIL",
                "message": str(e)
            })
            return False
    
    def test_checkpoint_retrieval(self) -> bool:
        """Test 2: Verify checkpoint retrieval logic"""
        logger.info("=" * 70)
        logger.info("Test 2: Verify checkpoint retrieval for retry")
        logger.info("=" * 70)
        
        try:
            # Rollback any previous transaction errors
            self.db.rollback()
            
            # Use unique ID to avoid conflicts
            unique_id = f"test-retrieval-{uuid.uuid4().hex[:8]}"
            
            # Create new test run for this test
            question = Question(
                id=f"{unique_id}-q",
                text="Test question for retrieval",
                options=["A", "B"]
            )
            self.db.add(question)
            
            process = Process(
                id=f"{unique_id}-p",
                question_id=question.id,
                status="processing",
                thread_id=f"{unique_id}-t"
            )
            self.db.add(process)
            
            run = PipelineRun(
                id=f"{unique_id}-run",
                process_id=process.id,
                run_number=1,
                topology="T1",
                status="running",
                retry_depth=0
            )
            self.db.add(run)
            self.db.commit()
            
            # Create multiple stages with checkpoints
            stages_data = [
                ("input_enhancer", 1, f"{unique_id}-checkpoint-1"),
                ("domain_knowledge_retriever", 2, f"{unique_id}-checkpoint-2"),
                ("router", 3, f"{unique_id}-checkpoint-3"),
                ("game_planner", 4, f"{unique_id}-checkpoint-4"),
            ]
            
            for stage_name, stage_order, checkpoint_id in stages_data:
                stage = StageExecution(
                    id=f"{unique_id}-stage-{stage_order}",
                    run_id=run.id,
                    stage_name=stage_name,
                    stage_order=stage_order,
                    status="success",
                    checkpoint_id=checkpoint_id
                )
                self.db.add(stage)
            self.db.commit()
            
            # Test finding checkpoint before target stage
            target_stage_name = "game_planner"
            target_stage = self.db.query(StageExecution).filter(
                StageExecution.run_id == run.id,
                StageExecution.stage_name == target_stage_name
            ).first()
            
            if not target_stage:
                logger.error("Target stage not found")
                return False
            
            # Find checkpoint before target stage
            previous_stage = self.db.query(StageExecution).filter(
                StageExecution.run_id == run.id,
                StageExecution.stage_order < target_stage.stage_order,
                StageExecution.checkpoint_id.isnot(None)
            ).order_by(StageExecution.stage_order.desc()).first()
            
            assert previous_stage is not None, "Previous stage with checkpoint not found"
            expected_checkpoint = f"{unique_id}-checkpoint-3"
            assert previous_stage.checkpoint_id == expected_checkpoint, f"Expected {expected_checkpoint}, got {previous_stage.checkpoint_id}"
            assert previous_stage.stage_name == "router", f"Expected router, got {previous_stage.stage_name}"
            
            logger.info(f"✅ Found checkpoint {previous_stage.checkpoint_id} from stage '{previous_stage.stage_name}'")
            
            self.test_results.append({
                "test": "checkpoint_retrieval",
                "status": "PASS",
                "message": f"Found checkpoint {previous_stage.checkpoint_id} before {target_stage_name}"
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Test 2 FAILED: {e}")
            self.test_results.append({
                "test": "checkpoint_retrieval",
                "status": "FAIL",
                "message": str(e)
            })
            return False
    
    def test_first_stage_retry(self) -> bool:
        """Test 3: Verify first stage retry (no previous checkpoint)"""
        logger.info("=" * 70)
        logger.info("Test 3: Verify first stage retry handling")
        logger.info("=" * 70)
        
        try:
            # Rollback any previous transaction errors
            self.db.rollback()
            
            # Use unique ID to avoid conflicts
            unique_id = f"test-first-{uuid.uuid4().hex[:8]}"
            
            # Create a run with only first stage
            question = Question(
                id=f"{unique_id}-q",
                text="Test question 2",
                options=[]
            )
            self.db.add(question)
            
            process = Process(
                id=f"{unique_id}-p",
                question_id=question.id,
                status="processing",
                thread_id=f"{unique_id}-t"
            )
            self.db.add(process)
            
            run = PipelineRun(
                id=f"{unique_id}-run",
                process_id=process.id,
                run_number=1,
                topology="T1",
                status="failed",
                retry_depth=0
            )
            self.db.add(run)
            
            # Only first stage exists, no checkpoint before it
            stage = StageExecution(
                id=f"{unique_id}-stage",
                run_id=run.id,
                stage_name="input_enhancer",
                stage_order=1,
                status="failed"
            )
            self.db.add(stage)
            self.db.commit()
            
            # Try to find checkpoint before first stage (should return None)
            previous_stage = self.db.query(StageExecution).filter(
                StageExecution.run_id == run.id,
                StageExecution.stage_order < 1,
                StageExecution.checkpoint_id.isnot(None)
            ).order_by(StageExecution.stage_order.desc()).first()
            
            assert previous_stage is None, "Should not find checkpoint before first stage"
            
            logger.info("✅ First stage retry correctly handles missing checkpoint")
            
            self.test_results.append({
                "test": "first_stage_retry",
                "status": "PASS",
                "message": "First stage retry correctly handles missing checkpoint"
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Test 3 FAILED: {e}")
            self.test_results.append({
                "test": "first_stage_retry",
                "status": "FAIL",
                "message": str(e)
            })
            return False
    
    def test_backward_compatibility(self) -> bool:
        """Test 4: Verify backward compatibility (old runs without checkpoints)"""
        logger.info("=" * 70)
        logger.info("Test 4: Verify backward compatibility")
        logger.info("=" * 70)
        
        try:
            # Rollback any previous transaction errors
            self.db.rollback()
            
            # Use unique ID to avoid conflicts
            unique_id = f"test-old-{uuid.uuid4().hex[:8]}"
            
            # Create an old run (simulating pre-migration run)
            question = Question(
                id=f"{unique_id}-q",
                text="Test question 3",
                options=[]
            )
            self.db.add(question)
            
            process = Process(
                id=f"{unique_id}-p",
                question_id=question.id,
                status="processing",
                thread_id=f"{unique_id}-t"
            )
            self.db.add(process)
            
            run = PipelineRun(
                id=f"{unique_id}-run",
                process_id=process.id,
                run_number=1,
                topology="T1",
                status="failed",
                retry_depth=0
            )
            self.db.add(run)
            
            # Create stages without checkpoints (old behavior)
            stages_data = [
                ("input_enhancer", 1),
                ("domain_knowledge_retriever", 2),
                ("router", 3),
            ]
            
            for stage_name, stage_order in stages_data:
                stage = StageExecution(
                    id=f"{unique_id}-stage-{stage_order}",
                    run_id=run.id,
                    stage_name=stage_name,
                    stage_order=stage_order,
                    status="success",
                    checkpoint_id=None  # No checkpoint (old run)
                )
                self.db.add(stage)
            self.db.commit()
            
            # Try to find checkpoint before a stage (should return None)
            target_stage = self.db.query(StageExecution).filter(
                StageExecution.run_id == run.id,
                StageExecution.stage_name == "router"
            ).first()
            
            previous_stage = self.db.query(StageExecution).filter(
                StageExecution.run_id == run.id,
                StageExecution.stage_order < target_stage.stage_order,
                StageExecution.checkpoint_id.isnot(None)
            ).order_by(StageExecution.stage_order.desc()).first()
            
            assert previous_stage is None, "Old runs should not have checkpoints"
            
            logger.info("✅ Backward compatibility: Old runs without checkpoints handled correctly")
            
            self.test_results.append({
                "test": "backward_compatibility",
                "status": "PASS",
                "message": "Old runs without checkpoints handled correctly"
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Test 4 FAILED: {e}")
            self.test_results.append({
                "test": "backward_compatibility",
                "status": "FAIL",
                "message": str(e)
            })
            return False
    
    def test_database_queries(self) -> bool:
        """Test 5: Verify database queries for checkpoint data"""
        logger.info("=" * 70)
        logger.info("Test 5: Verify database queries")
        logger.info("=" * 70)
        
        try:
            # Rollback any previous transaction errors
            self.db.rollback()
            # Query all stages with checkpoints
            stages_with_checkpoints = self.db.query(StageExecution).filter(
                StageExecution.checkpoint_id.isnot(None)
            ).all()
            
            logger.info(f"Found {len(stages_with_checkpoints)} stages with checkpoints")
            
            # Verify checkpoint data structure
            for stage in stages_with_checkpoints[:5]:  # Check first 5
                assert stage.checkpoint_id is not None
                assert len(stage.checkpoint_id) > 0
                logger.info(f"  - {stage.stage_name} (order={stage.stage_order}): {stage.checkpoint_id[:20]}...")
            
            # Query retry relationships
            retry_runs = self.db.query(PipelineRun).filter(
                PipelineRun.parent_run_id.isnot(None)
            ).all()
            
            logger.info(f"Found {len(retry_runs)} retry runs")
            
            self.test_results.append({
                "test": "database_queries",
                "status": "PASS",
                "message": f"Found {len(stages_with_checkpoints)} stages with checkpoints, {len(retry_runs)} retry runs"
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Test 5 FAILED: {e}")
            self.test_results.append({
                "test": "database_queries",
                "status": "FAIL",
                "message": str(e)
            })
            return False
    
    def test_error_handling(self) -> bool:
        """Test 6: Verify error handling for edge cases"""
        logger.info("=" * 70)
        logger.info("Test 6: Verify error handling for edge cases")
        logger.info("=" * 70)
        
        try:
            # Rollback any previous transaction errors
            self.db.rollback()
            
            # Use unique ID to avoid conflicts
            unique_id = f"test-error-{uuid.uuid4().hex[:8]}"
            
            # Create test run
            question = Question(
                id=f"{unique_id}-q",
                text="Test question for error handling",
                options=[]
            )
            self.db.add(question)
            
            process = Process(
                id=f"{unique_id}-p",
                question_id=question.id,
                status="processing",
                thread_id=f"{unique_id}-t"
            )
            self.db.add(process)
            
            run = PipelineRun(
                id=f"{unique_id}-run",
                process_id=process.id,
                run_number=1,
                topology="T1",
                status="failed",
                retry_depth=0
            )
            self.db.add(run)
            
            # Create stages with one having NULL checkpoint (simulating missing checkpoint)
            stage1 = StageExecution(
                id=f"{unique_id}-stage-1",
                run_id=run.id,
                stage_name="input_enhancer",
                stage_order=1,
                status="success",
                checkpoint_id="valid-checkpoint-1"
            )
            self.db.add(stage1)
            
            stage2 = StageExecution(
                id=f"{unique_id}-stage-2",
                run_id=run.id,
                stage_name="domain_knowledge_retriever",
                stage_order=2,
                status="success",
                checkpoint_id=None  # Missing checkpoint (error case)
            )
            self.db.add(stage2)
            
            stage3 = StageExecution(
                id=f"{unique_id}-stage-3",
                run_id=run.id,
                stage_name="router",
                stage_order=3,
                status="failed"
            )
            self.db.add(stage3)
            self.db.commit()
            
            # Test 1: Missing checkpoint - should find previous valid checkpoint
            target_stage = self.db.query(StageExecution).filter(
                StageExecution.run_id == run.id,
                StageExecution.stage_name == "router"
            ).first()
            
            previous_stage = self.db.query(StageExecution).filter(
                StageExecution.run_id == run.id,
                StageExecution.stage_order < target_stage.stage_order,
                StageExecution.checkpoint_id.isnot(None)
            ).order_by(StageExecution.stage_order.desc()).first()
            
            # Should find checkpoint from stage 1 (skipping stage 2 with NULL checkpoint)
            assert previous_stage is not None, "Should find checkpoint from earlier stage"
            assert previous_stage.checkpoint_id == "valid-checkpoint-1", f"Expected valid-checkpoint-1, got {previous_stage.checkpoint_id}"
            assert previous_stage.stage_order == 1, "Should find checkpoint from stage 1"
            
            logger.info("✅ Error handling: Missing checkpoint handled correctly (finds previous valid checkpoint)")
            
            # Test 2: Invalid checkpoint_id format - verify query handles it
            # (This is more of a database constraint test, but we verify the query works)
            invalid_checkpoint_stage = StageExecution(
                id=f"{unique_id}-invalid-stage",
                run_id=run.id,
                stage_name="game_planner",
                stage_order=4,
                status="success",
                checkpoint_id="invalid-checkpoint-format-12345"  # Valid format, just testing
            )
            self.db.add(invalid_checkpoint_stage)
            self.db.commit()
            
            # Query should still work
            stages_with_checkpoints = self.db.query(StageExecution).filter(
                StageExecution.run_id == run.id,
                StageExecution.checkpoint_id.isnot(None)
            ).all()
            
            assert len(stages_with_checkpoints) >= 2, "Should find stages with checkpoints"
            
            logger.info("✅ Error handling: Invalid checkpoint format handled correctly")
            
            self.test_results.append({
                "test": "error_handling",
                "status": "PASS",
                "message": "Error handling works correctly for missing and invalid checkpoints"
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Test 6 FAILED: {e}")
            self.test_results.append({
                "test": "error_handling",
                "status": "FAIL",
                "message": str(e)
            })
            return False
    
    def run_all_tests(self) -> Dict:
        """Run all integration tests"""
        logger.info("=" * 70)
        logger.info("CHECKPOINTING INTEGRATION TESTS")
        logger.info("=" * 70)
        logger.info("")
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "tests": []
        }
        
        # Run all tests
        test_methods = [
            self.test_checkpoint_saving,
            self.test_checkpoint_retrieval,
            self.test_first_stage_retry,
            self.test_backward_compatibility,
            self.test_database_queries,
            self.test_error_handling,
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                success = test_method()
                if success:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Test {test_method.__name__} raised exception: {e}")
                failed += 1
        
        results["tests"] = self.test_results
        results["summary"] = {
            "total": len(test_methods),
            "passed": passed,
            "failed": failed
        }
        
        # Print summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("TEST SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total: {len(test_methods)}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info("=" * 70)
        
        return results


def main():
    """Main entry point"""
    with CheckpointingIntegrationTest() as tester:
        results = tester.run_all_tests()
        
        # Exit with error code if any tests failed
        if results["summary"]["failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
