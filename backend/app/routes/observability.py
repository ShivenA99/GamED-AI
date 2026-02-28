"""
Pipeline Observability API Routes

Provides endpoints for:
- Listing and viewing pipeline runs
- Viewing stage executions within runs
- Viewing execution logs
- Real-time SSE streaming for live updates
- Retry from failed stages
- Agent registry information
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, distinct
from typing import Optional, List, Tuple
from pydantic import BaseModel
from datetime import datetime
import asyncio
import json
import logging

from app.db.database import get_db
from app.db.models import (
    PipelineRun, StageExecution, ExecutionLog, AgentRegistry,
    Process, Question, Visualization
)
from app.agents.instrumentation import (
    get_live_steps,
    clear_live_steps,
    AGENT_METADATA_REGISTRY,
    get_agent_metadata
)

logger = logging.getLogger("gamed_ai.routes.observability")
router = APIRouter(prefix="/observability", tags=["observability"])


# =============================================================================
# Pydantic Models for Request/Response
# =============================================================================

class RetryRequest(BaseModel):
    """Request to retry pipeline from a specific stage"""
    from_stage: str


class RunSummary(BaseModel):
    """Summary of a pipeline run"""
    id: str
    process_id: Optional[str]
    run_number: int
    topology: str
    status: str
    started_at: Optional[str]
    finished_at: Optional[str]
    duration_ms: Optional[int]
    error_message: Optional[str]
    retry_from_stage: Optional[str]
    parent_run_id: Optional[str]
    question_text: Optional[str] = None
    template_type: Optional[str] = None
    stages_completed: int = 0
    total_stages: int = 0


class StageDetail(BaseModel):
    """Details of a stage execution"""
    id: str
    stage_name: str
    stage_order: int
    status: str
    started_at: Optional[str]
    finished_at: Optional[str]
    duration_ms: Optional[int]
    model_id: Optional[str]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    estimated_cost_usd: Optional[float]
    latency_ms: Optional[int]
    error_message: Optional[str]
    validation_passed: Optional[bool]
    validation_score: Optional[float]
    retry_count: int = 0


class RunsListResponse(BaseModel):
    """Response for listing pipeline runs"""
    runs: List[RunSummary]
    total: int
    limit: int
    offset: int


class ChildRunSummary(BaseModel):
    """Summary of a child/retry run"""
    id: str
    run_number: int
    status: str
    retry_from_stage: Optional[str]
    started_at: Optional[str]


class StageFullDetail(StageDetail):
    """Full stage details including snapshots"""
    error_traceback: Optional[str] = None
    validation_errors: Optional[list] = None
    checkpoint_id: Optional[str] = None
    input_state_keys: Optional[List[str]] = None
    output_state_keys: Optional[List[str]] = None
    input_snapshot: Optional[dict] = None
    output_snapshot: Optional[dict] = None

    class Config:
        from_attributes = True


class RunDetailResponse(BaseModel):
    """Detailed response for a single pipeline run"""
    id: str
    process_id: Optional[str]
    run_number: int
    topology: str
    status: str
    started_at: Optional[str]
    finished_at: Optional[str]
    duration_ms: Optional[int]
    config_snapshot: Optional[dict]
    final_state_summary: Optional[dict]
    error_message: Optional[str]
    error_traceback: Optional[str]
    retry_from_stage: Optional[str]
    parent_run_id: Optional[str]
    question_text: Optional[str]
    template_type: Optional[str]
    total_cost_usd: float
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_retries: int
    stages_completed: int
    stages_failed: int
    total_stages: int
    stages: List[StageFullDetail]
    child_runs: List[ChildRunSummary]


class StagesListResponse(BaseModel):
    """Response for listing stages of a run"""
    run_id: str
    stages: List[StageFullDetail]


class LogEntry(BaseModel):
    """A single log entry"""
    id: str
    level: str
    message: str
    timestamp: Optional[str]
    stage_execution_id: Optional[str] = None
    metadata: Optional[dict] = None


class LogsResponse(BaseModel):
    """Response for fetching logs"""
    run_id: str
    logs: List[LogEntry]
    total: int


class GameSummary(BaseModel):
    """Summary of a game/process"""
    process_id: str
    question_text: str
    template_type: Optional[str]
    status: str
    created_at: str
    run_count: int
    latest_run_status: Optional[str]


class GamesListResponse(BaseModel):
    """Response for listing games"""
    games: List[GameSummary]
    total: int


# =============================================================================
# Pipeline Runs Endpoints
# =============================================================================

@router.get("/runs", response_model=RunsListResponse)
async def list_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status"),
    process_id: Optional[str] = Query(None, description="Filter by process ID"),
    db: Session = Depends(get_db)
):
    """
    List all pipeline runs with pagination.

    Returns runs sorted by start time (most recent first).
    """
    query = db.query(PipelineRun)

    if status:
        query = query.filter(PipelineRun.status == status)
    if process_id:
        query = query.filter(PipelineRun.process_id == process_id)

    total = query.count()
    runs = query.order_by(desc(PipelineRun.started_at)).offset(offset).limit(limit).all()

    result = []
    for run in runs:
        # Get question text and template type from process
        question_text = None
        template_type = None
        if run.process_id:
            process = db.query(Process).filter(Process.id == run.process_id).first()
            if process and process.question:
                question_text = process.question.text[:100] + "..." if len(process.question.text) > 100 else process.question.text
            viz = db.query(Visualization).filter(Visualization.process_id == run.process_id).first()
            if viz:
                template_type = viz.template_type

        # Count stages (include "degraded" as completed since they finished with fallback)
        stages = db.query(StageExecution).filter(StageExecution.run_id == run.id).all()
        stages_completed = len([s for s in stages if s.status in ["success", "degraded"]])

        result.append({
            "id": run.id,
            "process_id": run.process_id,
            "run_number": run.run_number,
            "topology": run.topology,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "duration_ms": run.duration_ms,
            "error_message": run.error_message,
            "retry_from_stage": run.retry_from_stage,
            "parent_run_id": run.parent_run_id,
            "question_text": question_text,
            "template_type": template_type,
            "stages_completed": stages_completed,
            "total_stages": len(stages)
        })

    return {
        "runs": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific pipeline run.

    Includes:
    - Run metadata (topology, status, timing)
    - Configuration snapshot
    - Final state summary
    - List of stage executions with status
    """
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        # Also try lookup by process_id (frontend games page links with process_id)
        run = db.query(PipelineRun).filter(
            PipelineRun.process_id == run_id
        ).order_by(PipelineRun.started_at.desc()).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Use the actual run_id for stage queries (in case we found by process_id)
    actual_run_id = run.id

    # Get stages
    stages = db.query(StageExecution).filter(
        StageExecution.run_id == actual_run_id
    ).order_by(StageExecution.stage_order).all()

    # Get question and template info
    question_text = None
    template_type = None
    if run.process_id:
        process = db.query(Process).filter(Process.id == run.process_id).first()
        if process and process.question:
            question_text = process.question.text
        viz = db.query(Visualization).filter(Visualization.process_id == run.process_id).first()
        if viz:
            template_type = viz.template_type

    # Get child runs (retries)
    child_runs = db.query(PipelineRun).filter(PipelineRun.parent_run_id == actual_run_id).all()

    # Calculate aggregated totals from stages
    total_cost = sum(float(s.estimated_cost_usd or 0) for s in stages)
    total_tokens = sum(s.total_tokens or 0 for s in stages)
    total_prompt_tokens = sum(s.prompt_tokens or 0 for s in stages)
    total_completion_tokens = sum(s.completion_tokens or 0 for s in stages)
    total_retries = sum(s.retry_count or 0 for s in stages)
    total_llm_calls = len([s for s in stages if s.model_id])
    stages_completed = len([s for s in stages if s.status in ('success', 'degraded')])
    stages_failed = len([s for s in stages if s.status == 'failed'])

    return {
        "id": run.id,
        "process_id": run.process_id,
        "run_number": run.run_number,
        "topology": run.topology,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_ms": run.duration_ms,
        "config_snapshot": run.config_snapshot,
        "final_state_summary": run.final_state_summary,
        "error_message": run.error_message,
        "error_traceback": run.error_traceback,
        "retry_from_stage": run.retry_from_stage,
        "parent_run_id": run.parent_run_id,
        "question_text": question_text,
        "template_type": template_type,
        # Aggregated totals
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_tokens,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_llm_calls": total_llm_calls,
        "total_retries": total_retries,
        "stages_completed": stages_completed,
        "stages_failed": stages_failed,
        "total_stages": len(stages),
        "stages": [
            {
                "id": s.id,
                "stage_name": s.stage_name,
                "stage_order": s.stage_order,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                "duration_ms": s.duration_ms,
                "model_id": s.model_id,
                "prompt_tokens": s.prompt_tokens,
                "completion_tokens": s.completion_tokens,
                "total_tokens": s.total_tokens,
                "estimated_cost_usd": s.estimated_cost_usd,
                "latency_ms": s.latency_ms,
                "error_message": s.error_message,
                "error_traceback": s.error_traceback,
                "validation_passed": s.validation_passed,
                "validation_score": s.validation_score,
                "validation_errors": s.validation_errors,
                "retry_count": s.retry_count,
                "checkpoint_id": s.checkpoint_id,  # LangGraph checkpoint_id for retry
                "input_state_keys": s.input_state_keys,
                "output_state_keys": s.output_state_keys,
                "input_snapshot": s.input_snapshot,
                "output_snapshot": s.output_snapshot
            }
            for s in stages
        ],
        "child_runs": [
            {
                "id": c.id,
                "run_number": c.run_number,
                "status": c.status,
                "retry_from_stage": c.retry_from_stage,
                "started_at": c.started_at.isoformat() if c.started_at else None
            }
            for c in child_runs
        ]
    }


@router.get("/runs/{run_id}/stages", response_model=StagesListResponse)
async def get_run_stages(
    run_id: str,
    db: Session = Depends(get_db)
):
    """Get all stage executions for a run"""
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    stages = db.query(StageExecution).filter(
        StageExecution.run_id == run_id
    ).order_by(StageExecution.stage_order).all()

    return {
        "run_id": run_id,
        "stages": [
            {
                "id": s.id,
                "stage_name": s.stage_name,
                "stage_order": s.stage_order,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                "duration_ms": s.duration_ms,
                "input_state_keys": s.input_state_keys,
                "output_state_keys": s.output_state_keys,
                "input_snapshot": s.input_snapshot,
                "output_snapshot": s.output_snapshot,
                "model_id": s.model_id,
                "prompt_tokens": s.prompt_tokens,
                "completion_tokens": s.completion_tokens,
                "total_tokens": s.total_tokens,
                "estimated_cost_usd": s.estimated_cost_usd,
                "latency_ms": s.latency_ms,
                "error_message": s.error_message,
                "error_traceback": s.error_traceback,
                "retry_count": s.retry_count,
                "validation_passed": s.validation_passed,
                "validation_score": s.validation_score,
                "validation_errors": s.validation_errors
            }
            for s in stages
        ]
    }


@router.get("/runs/{run_id}/logs", response_model=LogsResponse)
async def get_run_logs(
    run_id: str,
    stage_id: Optional[str] = Query(None, description="Filter by stage execution ID"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get execution logs for a run"""
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    query = db.query(ExecutionLog).filter(ExecutionLog.run_id == run_id)

    if stage_id:
        query = query.filter(ExecutionLog.stage_execution_id == stage_id)
    if level:
        query = query.filter(ExecutionLog.level == level)

    total = query.count()
    logs = query.order_by(desc(ExecutionLog.timestamp)).limit(limit).all()

    return {
        "run_id": run_id,
        "logs": [
            {
                "id": log.id,
                "stage_execution_id": log.stage_execution_id,
                "level": log.level,
                "message": log.message,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "metadata": log.log_metadata
            }
            for log in logs
        ],
        "total": total
    }


@router.get("/runs/{run_id}/stream")
async def stream_run_updates(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    SSE stream for real-time run updates.

    Streams:
    - 'update': Current stage status, progress, and metrics (tokens/cost)
    - 'live_step': Real-time reasoning steps from agents (thought, action, observation, decision)
    - 'complete': Final completion/failure event

    Update events include:
    - total_tokens: Aggregate token count across all stages
    - total_cost_usd: Aggregate cost across all stages
    - Per-stage tokens and cost in the stages array
    """
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        """Generate SSE events for run updates"""
        last_stage_count = 0
        last_live_step_check = 0

        while True:
            # Get fresh run data
            db_session = next(get_db())
            try:
                current_run = db_session.query(PipelineRun).filter(
                    PipelineRun.id == run_id
                ).first()

                if not current_run:
                    yield f"event: error\ndata: {json.dumps({'error': 'Run not found'})}\n\n"
                    break

                # Get stages with full metrics
                stages = db_session.query(StageExecution).filter(
                    StageExecution.run_id == run_id
                ).order_by(StageExecution.stage_order).all()

                current_stage = next(
                    (s for s in stages if s.status == "running"),
                    None
                )

                # Calculate progress (include "degraded" as completed since they finished with fallback)
                stages_completed = len([s for s in stages if s.status in ["success", "degraded"]])
                total_stages = max(len(stages), 15)  # Estimate 15 total if still running
                progress_percent = int((stages_completed / total_stages) * 100)

                # Calculate aggregate metrics from stages
                total_tokens = sum(s.total_tokens or 0 for s in stages)
                total_cost_usd = sum(float(s.estimated_cost_usd or 0) for s in stages)

                # Build update payload with enhanced metrics
                update_data = {
                    "run_id": run_id,
                    "status": current_run.status,
                    "current_stage": current_stage.stage_name if current_stage else None,
                    "stages_completed": stages_completed,
                    "total_stages": len(stages),
                    "progress_percent": progress_percent,
                    "duration_ms": current_run.duration_ms,
                    # Aggregate metrics
                    "total_tokens": total_tokens,
                    "total_cost_usd": round(total_cost_usd, 6),
                    # Per-stage data with metrics
                    "stages": [
                        {
                            "stage_name": s.stage_name,
                            "status": s.status,
                            "duration_ms": s.duration_ms,
                            # Per-stage metrics (NEW)
                            "tokens": s.total_tokens,
                            "cost": float(s.estimated_cost_usd) if s.estimated_cost_usd else None,
                            "model_id": s.model_id,
                        }
                        for s in stages
                    ]
                }

                yield f"event: update\ndata: {json.dumps(update_data)}\n\n"

                # Check for live steps from in-memory queue (real-time)
                new_live_steps = get_live_steps(run_id, from_index=last_live_step_check)
                for step_event in new_live_steps:
                    live_step_data = {
                        "type": "live_step",
                        "stage_name": step_event.get("stage_name", "unknown"),
                        "step": step_event.get("step", {})
                    }
                    yield f"event: live_step\ndata: {json.dumps(live_step_data)}\n\n"
                last_live_step_check += len(new_live_steps)

                # Fallback: Check for live steps from saved output snapshot
                # (for agents that don't use the new streaming API)
                if current_stage and current_stage.output_snapshot:
                    saved_steps = _extract_live_steps_from_stage(current_stage)
                    # Only emit saved steps that aren't in the queue
                    for step in saved_steps[last_live_step_check:]:
                        live_step_data = {
                            "type": "live_step",
                            "stage_name": current_stage.stage_name,
                            "step": step
                        }
                        yield f"event: live_step\ndata: {json.dumps(live_step_data)}\n\n"

                # Check if run is complete
                if current_run.status in ["success", "failed", "cancelled"]:
                    # Emit any remaining live steps before completion
                    final_steps = get_live_steps(run_id, from_index=last_live_step_check)
                    for step_event in final_steps:
                        live_step_data = {
                            "type": "live_step",
                            "stage_name": step_event.get("stage_name", "unknown"),
                            "step": step_event.get("step", {})
                        }
                        yield f"event: live_step\ndata: {json.dumps(live_step_data)}\n\n"

                    complete_data = {
                        "run_id": run_id,
                        "status": current_run.status,
                        "duration_ms": current_run.duration_ms,
                        "error_message": current_run.error_message,
                        # Include final metrics in complete event
                        "total_tokens": total_tokens,
                        "total_cost_usd": round(total_cost_usd, 6),
                    }
                    yield f"event: complete\ndata: {json.dumps(complete_data)}\n\n"

                    # Clean up in-memory queue
                    clear_live_steps(run_id)
                    break

                last_stage_count = len(stages)

            finally:
                db_session.close()

            await asyncio.sleep(1)  # Poll every second

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


def _extract_live_steps_from_stage(stage: StageExecution) -> List[dict]:
    """
    Extract live reasoning steps from a stage's output snapshot.

    Looks for ReAct trace data or tool metrics that contain step-by-step reasoning.
    Returns a list of step dictionaries with type, content, tool (if applicable), and timestamp.
    """
    steps = []

    if not stage.output_snapshot:
        return steps

    snapshot = stage.output_snapshot

    # Extract from ReAct metrics if present
    react_metrics = snapshot.get("_react_metrics", {})
    reasoning_trace = react_metrics.get("reasoning_trace", [])

    for trace_step in reasoning_trace:
        # Convert ReAct trace format to live_step format
        if trace_step.get("thought"):
            steps.append({
                "type": "thought",
                "content": trace_step["thought"],
                "timestamp": stage.started_at.isoformat() if stage.started_at else None
            })

        if trace_step.get("action"):
            action = trace_step["action"]
            steps.append({
                "type": "action",
                "content": f"Calling tool: {action.get('name', 'unknown')}",
                "tool": action.get("name"),
                "timestamp": stage.started_at.isoformat() if stage.started_at else None
            })

        if trace_step.get("observation"):
            steps.append({
                "type": "observation",
                "content": trace_step["observation"],
                "timestamp": stage.started_at.isoformat() if stage.started_at else None
            })

    # Extract from tool metrics if present (for agentic sequential agents)
    tool_metrics = snapshot.get("_tool_metrics", {})
    tool_calls = tool_metrics.get("tool_calls", [])

    for tool_call in tool_calls:
        steps.append({
            "type": "action",
            "content": f"Tool call: {tool_call.get('name', 'unknown')}",
            "tool": tool_call.get("name"),
            "timestamp": stage.started_at.isoformat() if stage.started_at else None
        })

        if tool_call.get("result"):
            result_preview = str(tool_call["result"])[:200]
            steps.append({
                "type": "observation",
                "content": result_preview,
                "timestamp": stage.started_at.isoformat() if stage.started_at else None
            })

    return steps


# =============================================================================
# Retry Operations
# =============================================================================

@router.post("/runs/{run_id}/retry")
async def retry_from_stage(
    run_id: str,
    retry_request: RetryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Retry a pipeline run from a specific failed stage.

    Creates a new PipelineRun as a child of the original,
    restoring state from the original run's successful stages.
    
    Uses SELECT FOR UPDATE to prevent concurrent retries of the same stage.
    """
    try:
        # Lock the original run row to prevent concurrent retries
        # This ensures only one retry can be created at a time for the same stage
        original_run = db.query(PipelineRun).filter(
            PipelineRun.id == run_id
        ).with_for_update().first()
        
        if not original_run:
            raise HTTPException(status_code=404, detail="Run not found")

        # Check for existing retry runs for the same stage
        existing_retry = db.query(PipelineRun).filter(
            PipelineRun.parent_run_id == run_id,
            PipelineRun.retry_from_stage == retry_request.from_stage,
            PipelineRun.status.in_(["pending", "running"])
        ).first()
        
        if existing_retry:
            logger.warning(
                f"Retry request rejected: A retry for stage '{retry_request.from_stage}' "
                f"is already in progress (run {existing_retry.id})"
            )
            raise HTTPException(
                status_code=409,  # Conflict
                detail=f"A retry for stage '{retry_request.from_stage}' is already in progress (run {existing_retry.id})"
            )

        # Verify the stage exists in this run
        target_stage = db.query(StageExecution).filter(
            StageExecution.run_id == run_id,
            StageExecution.stage_name == retry_request.from_stage
        ).first()

        if not target_stage:
            raise HTTPException(
                status_code=400,
                detail=f"Stage '{retry_request.from_stage}' not found in this run"
            )

        # Allow retry if:
        # 1. Run is failed/cancelled, OR
        # 2. The specific stage is failed or degraded (even if run succeeded)
        if original_run.status not in ["failed", "cancelled"]:
            if target_stage.status not in ["failed", "degraded"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Can only retry failed or degraded stages. Stage '{retry_request.from_stage}' has status '{target_stage.status}'"
                )

        # Check retry depth limit (MAX_RETRY_DEPTH = 3)
        MAX_RETRY_DEPTH = 3
        parent_retry_depth = getattr(original_run, 'retry_depth', 0)  # Default to 0 for old runs
        new_retry_depth = parent_retry_depth + 1
        
        logger.info(
            f"Checking retry depth: parent={parent_retry_depth}, new={new_retry_depth}, "
            f"max={MAX_RETRY_DEPTH}"
        )
        
        if new_retry_depth > MAX_RETRY_DEPTH:
            logger.warning(
                f"Retry request rejected: Maximum retry depth ({MAX_RETRY_DEPTH}) exceeded. "
                f"Parent depth: {parent_retry_depth}, attempted depth: {new_retry_depth}"
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Maximum retry depth ({MAX_RETRY_DEPTH}) exceeded. "
                    f"Current depth: {parent_retry_depth}, cannot create retry at depth {new_retry_depth}. "
                    f"Please retry from an earlier run in the chain."
                )
            )

        # Create new run as retry
        new_run = PipelineRun(
            process_id=original_run.process_id,
            run_number=original_run.run_number + 1,
            topology=original_run.topology,
            status="pending",
            parent_run_id=run_id,
            retry_from_stage=retry_request.from_stage,
            retry_depth=new_retry_depth,
            config_snapshot=original_run.config_snapshot
        )
        db.add(new_run)
        db.commit()
        db.refresh(new_run)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        db.rollback()
        raise
    except Exception as e:
        # Rollback on any other error
        db.rollback()
        logger.error(f"Error creating retry run: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create retry run: {str(e)}"
        )

    logger.info(f"Created retry run {new_run.id} from stage {retry_request.from_stage}")

    # Start pipeline from the specific stage in background
    background_tasks.add_task(
        run_retry_pipeline,
        new_run.id,
        run_id,
        retry_request.from_stage
    )

    return {
        "new_run_id": new_run.id,
        "parent_run_id": run_id,
        "retry_from_stage": retry_request.from_stage,
        "status": "started",
        "message": f"Retry started from stage {retry_request.from_stage}"
    }


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a running pipeline"""
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Can only cancel pending or running pipelines (current status: {run.status})"
        )

    run.status = "cancelled"
    run.finished_at = datetime.utcnow()
    if run.started_at:
        run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

    db.commit()

    logger.info(f"Cancelled run {run_id}")

    return {
        "run_id": run_id,
        "status": "cancelled",
        "message": "Pipeline cancelled"
    }


# =============================================================================
# Stage Details
# =============================================================================

@router.get("/stages/{stage_id}")
async def get_stage_details(
    stage_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific stage execution"""
    stage = db.query(StageExecution).filter(StageExecution.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    # Get associated logs
    logs = db.query(ExecutionLog).filter(
        ExecutionLog.stage_execution_id == stage_id
    ).order_by(ExecutionLog.timestamp).all()

    return {
        "id": stage.id,
        "run_id": stage.run_id,
        "stage_name": stage.stage_name,
        "stage_order": stage.stage_order,
        "status": stage.status,
        "started_at": stage.started_at.isoformat() if stage.started_at else None,
        "finished_at": stage.finished_at.isoformat() if stage.finished_at else None,
        "duration_ms": stage.duration_ms,
        "input_state_keys": stage.input_state_keys,
        "output_state_keys": stage.output_state_keys,
        "input_snapshot": stage.input_snapshot,
        "output_snapshot": stage.output_snapshot,
        "model_id": stage.model_id,
        "prompt_tokens": stage.prompt_tokens,
        "completion_tokens": stage.completion_tokens,
        "total_tokens": stage.total_tokens,
        "estimated_cost_usd": stage.estimated_cost_usd,
        "latency_ms": stage.latency_ms,
        "error_message": stage.error_message,
        "error_traceback": stage.error_traceback,
        "retry_count": stage.retry_count,
                "validation_passed": stage.validation_passed,
                "validation_score": stage.validation_score,
                "validation_errors": stage.validation_errors,
                "checkpoint_id": stage.checkpoint_id,  # LangGraph checkpoint_id for retry
                "logs": [
            {
                "id": log.id,
                "level": log.level,
                "message": log.message,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "metadata": log.log_metadata
            }
            for log in logs
        ]
    }


# =============================================================================
# Agent Registry
# =============================================================================

@router.get("/agents")
async def list_agents(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """List all registered agents with metadata"""
    query = db.query(AgentRegistry)

    if category:
        query = query.filter(AgentRegistry.category == category)

    agents = query.all()

    return {
        "agents": [
            {
                "id": a.id,
                "display_name": a.display_name,
                "description": a.description,
                "category": a.category,
                "default_model": a.default_model,
                "default_temperature": a.default_temperature,
                "default_max_tokens": a.default_max_tokens,
                "typical_inputs": a.typical_inputs,
                "typical_outputs": a.typical_outputs,
                "icon": a.icon,
                "color": a.color
            }
            for a in agents
        ]
    }


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Get details for a specific agent"""
    agent = db.query(AgentRegistry).filter(AgentRegistry.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "id": agent.id,
        "display_name": agent.display_name,
        "description": agent.description,
        "category": agent.category,
        "default_model": agent.default_model,
        "default_temperature": agent.default_temperature,
        "default_max_tokens": agent.default_max_tokens,
        "typical_inputs": agent.typical_inputs,
        "typical_outputs": agent.typical_outputs,
        "icon": agent.icon,
        "color": agent.color,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
    }


@router.get("/games", response_model=GamesListResponse)
async def list_games_from_runs(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get unique games from PipelineRuns, grouped by process_id.
    This is a fallback when /api/processes is not available.
    Returns the most recent run for each unique process_id.
    """
    # Get distinct process_ids with their most recent run
    subquery = (
        db.query(
            PipelineRun.process_id,
            func.max(PipelineRun.started_at).label('max_started_at')
        )
        .filter(PipelineRun.process_id.isnot(None))
        .group_by(PipelineRun.process_id)
        .subquery()
    )

    # Get the most recent run for each process
    runs = (
        db.query(PipelineRun)
        .join(
            subquery,
            (PipelineRun.process_id == subquery.c.process_id) &
            (PipelineRun.started_at == subquery.c.max_started_at)
        )
        .order_by(desc(PipelineRun.started_at))
        .limit(limit)
        .all()
    )

    games = []
    for run in runs:
        if not run.process_id:
            continue

        # Get question text and template type
        question_text = None
        template_type = None
        process = db.query(Process).filter(Process.id == run.process_id).first()
        if process and process.question:
            question_text = process.question.text
        elif run.question_text:
            question_text = run.question_text
        else:
            question_text = "Untitled question"

        viz = db.query(Visualization).filter(Visualization.process_id == run.process_id).first()
        if viz:
            template_type = viz.template_type
        elif run.template_type:
            template_type = run.template_type

        # Determine status from run
        status = run.status
        if status == 'success':
            status = 'completed'
        elif status == 'failed':
            status = 'error'
        elif status == 'running':
            status = 'processing'

        games.append({
            "process_id": run.process_id,
            "question_text": question_text[:200] + "..." if len(question_text) > 200 else question_text,
            "template_type": template_type,
            "status": status,
            "created_at": run.started_at.isoformat() if run.started_at else None
        })

    return {
        "games": games,
        "total": len(games)
    }


@router.get("/graph/structure")
async def get_graph_structure(
    topology: str = Query("T1", description="Topology type"),
    preset: Optional[str] = Query(None, description="Pipeline preset (default, interactive_diagram_hierarchical, advanced_interactive_diagram)"),
):
    """
    Get the ACTUAL graph structure for a given topology.

    This endpoint returns the real graph structure from the backend,
    including all conditional edges and routing functions.

    Returns:
        - nodes: List of agent nodes with metadata
        - edges: List of edges with type (direct/conditional) and conditions
        - conditionalFunctions: List of routing functions with their outcomes
    """
    import os

    # Set preset environment variable temporarily for graph structure extraction
    original_preset = os.environ.get("PIPELINE_PRESET")
    if preset:
        os.environ["PIPELINE_PRESET"] = preset

    try:
        # Use centralized agent metadata registry from instrumentation.py
        # This is the SINGLE SOURCE OF TRUTH for agent metadata

        # Define edges based on topology and preset
        # These match the actual graph.py implementation

        # Common nodes for all topologies
        common_edges = [
            # Linear start
            {"from": "input_enhancer", "to": "domain_knowledge_retriever", "type": "direct"},
        ]

        # Conditional edges from domain_knowledge_retriever
        conditional_edges = [
            {
                "from": "domain_knowledge_retriever",
                "to": "diagram_type_classifier",
                "type": "conditional",
                "condition": "should_use_advanced_preset",
                "conditionValue": "advanced"
            },
            {
                "from": "domain_knowledge_retriever",
                "to": "router",
                "type": "conditional",
                "condition": "should_use_advanced_preset",
                "conditionValue": "standard"
            },
            {"from": "diagram_type_classifier", "to": "router", "type": "direct"},

            # Router conditions
            {
                "from": "router",
                "to": "phet_simulation_selector",
                "type": "conditional",
                "condition": "requires_phet_simulation",
                "conditionValue": "phet_pipeline"
            },
            {
                "from": "router",
                "to": "check_routing_confidence_node",
                "type": "conditional",
                "condition": "requires_phet_simulation",
                "conditionValue": "standard_pipeline"
            },
            {
                "from": "check_routing_confidence_node",
                "to": "check_agentic_design_node",
                "type": "conditional",
                "condition": "check_routing_confidence",
                "conditionValue": "high"
            },
            {
                "from": "check_routing_confidence_node",
                "to": "human_review",
                "type": "conditional",
                "condition": "check_routing_confidence",
                "conditionValue": "low",
                "isEscalation": True
            },
            {
                "from": "check_agentic_design_node",
                "to": "diagram_analyzer",
                "type": "conditional",
                "condition": "should_use_agentic_design",
                "conditionValue": "agentic"
            },
            {
                "from": "check_agentic_design_node",
                "to": "game_planner",
                "type": "conditional",
                "condition": "should_use_agentic_design",
                "conditionValue": "standard"
            },

            # Agentic design flow
            {"from": "diagram_analyzer", "to": "game_designer", "type": "direct"},
            {"from": "game_designer", "to": "game_planner", "type": "direct"},
            {"from": "human_review", "to": "check_agentic_design_node", "type": "direct"},

            # Agentic interaction design pipeline (after game_planner)
            {"from": "game_planner", "to": "interaction_designer", "type": "direct"},
            {"from": "interaction_designer", "to": "interaction_validator", "type": "direct"},

            # After interaction validation, route to scene generation
            {
                "from": "interaction_validator",
                "to": "scene_sequencer",
                "type": "conditional",
                "condition": "should_use_scene_sequencer",
                "conditionValue": "sequencer"
            },
            {
                "from": "interaction_validator",
                "to": "scene_stage1_structure",
                "type": "conditional",
                "condition": "should_use_scene_sequencer",
                "conditionValue": "direct"
            },

            # Scene sequencer conditions
            {
                "from": "scene_sequencer",
                "to": "multi_scene_image_orchestrator",
                "type": "conditional",
                "condition": "should_use_multi_scene_orchestrator",
                "conditionValue": "multi_scene"
            },
            {
                "from": "scene_sequencer",
                "to": "scene_stage1_structure",
                "type": "conditional",
                "condition": "should_use_multi_scene_orchestrator",
                "conditionValue": "single_scene"
            },
            {"from": "multi_scene_image_orchestrator", "to": "blueprint_generator", "type": "direct"},

            # Scene stages
            {"from": "scene_stage1_structure", "to": "scene_stage2_assets", "type": "direct"},
            {"from": "scene_stage2_assets", "to": "scene_stage3_interactions", "type": "direct"},

            # Diagram image conditions
            {
                "from": "scene_stage3_interactions",
                "to": "diagram_image_retriever",
                "type": "conditional",
                "condition": "requires_diagram_image",
                "conditionValue": "use_image"
            },
            {
                "from": "scene_stage3_interactions",
                "to": "blueprint_generator",
                "type": "conditional",
                "condition": "requires_diagram_image",
                "conditionValue": "skip_image"
            },

            # Preset pipeline conditions
            {
                "from": "diagram_image_retriever",
                "to": "diagram_image_generator",
                "type": "conditional",
                "condition": "should_use_preset_pipeline",
                "conditionValue": "preset"
            },
            {
                "from": "diagram_image_retriever",
                "to": "image_label_classifier",
                "type": "conditional",
                "condition": "should_use_preset_pipeline",
                "conditionValue": "default"
            },

            # Preset pipeline (Gemini)
            {"from": "diagram_image_generator", "to": "gemini_zone_detector", "type": "direct"},
            {"from": "gemini_zone_detector", "to": "blueprint_generator", "type": "direct"},

            # Default pipeline - classification branch
            {
                "from": "image_label_classifier",
                "to": "direct_structure_locator",
                "type": "conditional",
                "condition": "check_image_labeled",
                "conditionValue": "unlabeled"
            },
            {
                "from": "image_label_classifier",
                "to": "image_label_remover",
                "type": "conditional",
                "condition": "check_image_labeled",
                "conditionValue": "labeled"
            },

            # Fast path for unlabeled
            {"from": "direct_structure_locator", "to": "blueprint_generator", "type": "direct"},

            # Standard path for labeled
            {"from": "image_label_remover", "to": "qwen_annotation_detector", "type": "direct"},
            {"from": "qwen_annotation_detector", "to": "qwen_sam_zone_detector", "type": "direct"},

            # Zone detector retry or continue
            {
                "from": "qwen_sam_zone_detector",
                "to": "diagram_image_retriever",
                "type": "conditional",
                "condition": "check_zone_labels_complete",
                "conditionValue": "retry_image",
                "isRetryEdge": True
            },
            {
                "from": "qwen_sam_zone_detector",
                "to": "blueprint_generator",
                "type": "conditional",
                "condition": "check_zone_labels_complete",
                "conditionValue": "continue"
            },

            # Blueprint validation
            {"from": "blueprint_generator", "to": "blueprint_validator", "type": "direct"},
            {
                "from": "blueprint_validator",
                "to": "check_post_blueprint_needs",
                "type": "conditional",
                "condition": "check_validation_result",
                "conditionValue": "valid"
            },
            {
                "from": "blueprint_validator",
                "to": "blueprint_generator",
                "type": "conditional",
                "condition": "check_validation_result",
                "conditionValue": "retry",
                "isRetryEdge": True
            },
            {
                "from": "blueprint_validator",
                "to": "human_review",
                "type": "conditional",
                "condition": "check_validation_result",
                "conditionValue": "fail",
                "isEscalation": True
            },

            # Post-blueprint needs check (PHASE 6: Conditional Routing)
            {
                "from": "check_post_blueprint_needs",
                "to": "asset_planner",
                "type": "conditional",
                "condition": "should_run_asset_pipeline",
                "conditionValue": "run_assets"
            },
            {
                "from": "check_post_blueprint_needs",
                "to": "check_diagram_spec_route",
                "type": "conditional",
                "condition": "should_run_asset_pipeline",
                "conditionValue": "skip_assets"
            },

            # Asset pipeline
            {"from": "asset_planner", "to": "asset_generator_orchestrator", "type": "direct"},
            {"from": "asset_generator_orchestrator", "to": "asset_validator", "type": "direct"},
            {"from": "asset_validator", "to": "check_diagram_spec_route", "type": "direct"},

            # Diagram spec routing (after assets or directly from needs check)
            {
                "from": "check_diagram_spec_route",
                "to": "diagram_spec_generator",
                "type": "conditional",
                "condition": "should_run_diagram_spec",
                "conditionValue": "run_diagram_spec"
            },
            {
                "from": "check_diagram_spec_route",
                "to": "check_template_status",
                "type": "conditional",
                "condition": "should_run_diagram_spec",
                "conditionValue": "skip_diagram_spec"
            },

            # Spec and SVG generation
            {"from": "diagram_spec_generator", "to": "diagram_spec_validator", "type": "direct"},
            {
                "from": "diagram_spec_validator",
                "to": "diagram_svg_generator",
                "type": "conditional",
                "condition": "check_diagram_spec_validation",
                "conditionValue": "valid"
            },
            {
                "from": "diagram_spec_validator",
                "to": "diagram_spec_generator",
                "type": "conditional",
                "condition": "check_diagram_spec_validation",
                "conditionValue": "retry",
                "isRetryEdge": True
            },
            {
                "from": "diagram_spec_validator",
                "to": "human_review",
                "type": "conditional",
                "condition": "check_diagram_spec_validation",
                "conditionValue": "fail",
                "isEscalation": True
            },

            # Check template status
            {"from": "diagram_svg_generator", "to": "check_template_status", "type": "direct"},
            {
                "from": "check_template_status",
                "to": "END",
                "type": "conditional",
                "condition": "is_stub_template",
                "conditionValue": "production"
            },
            {
                "from": "check_template_status",
                "to": "code_generator",
                "type": "conditional",
                "condition": "is_stub_template",
                "conditionValue": "stub"
            },

            # Code generation
            {"from": "code_generator", "to": "code_verifier", "type": "direct"},
            {
                "from": "code_verifier",
                "to": "END",
                "type": "conditional",
                "condition": "check_code_validation",
                "conditionValue": "valid"
            },
            {
                "from": "code_verifier",
                "to": "code_generator",
                "type": "conditional",
                "condition": "check_code_validation",
                "conditionValue": "retry",
                "isRetryEdge": True
            },
            {
                "from": "code_verifier",
                "to": "human_review",
                "type": "conditional",
                "condition": "check_code_validation",
                "conditionValue": "fail",
                "isEscalation": True
            },

            # PhET pipeline
            {"from": "phet_simulation_selector", "to": "phet_game_planner", "type": "direct"},
            {"from": "phet_game_planner", "to": "phet_assessment_designer", "type": "direct"},
            {"from": "phet_assessment_designer", "to": "phet_blueprint_generator", "type": "direct"},
            {"from": "phet_blueprint_generator", "to": "phet_blueprint_validator", "type": "direct"},
            {
                "from": "phet_blueprint_validator",
                "to": "phet_bridge_config_generator",
                "type": "conditional",
                "condition": "check_phet_blueprint_validation",
                "conditionValue": "valid"
            },
            {
                "from": "phet_blueprint_validator",
                "to": "phet_blueprint_generator",
                "type": "conditional",
                "condition": "check_phet_blueprint_validation",
                "conditionValue": "retry",
                "isRetryEdge": True
            },
            {
                "from": "phet_blueprint_validator",
                "to": "human_review",
                "type": "conditional",
                "condition": "check_phet_blueprint_validation",
                "conditionValue": "fail",
                "isEscalation": True
            },
            {"from": "phet_bridge_config_generator", "to": "END", "type": "direct"},
        ]

        all_edges = common_edges + conditional_edges

        # Decision/routing nodes that should be included with special visualization
        decision_nodes = {
            "check_routing_confidence_node",
            "check_agentic_design_node",
            "check_template_status",
            "check_post_blueprint_needs",
            "check_post_scene_needs",
            "check_multi_scene",
            "check_diagram_spec_route",
            "check_diagram_image"
        }

        # Collect nodes that appear in edges
        nodes_in_graph = set()
        for edge in all_edges:
            if edge["from"] != "END":
                nodes_in_graph.add(edge["from"])
            if edge["to"] != "END":
                nodes_in_graph.add(edge["to"])

        # Build nodes list using centralized registry
        # Include decision nodes but mark them with isDecisionNode flag
        nodes = []
        for node_id in nodes_in_graph:
            meta = get_agent_metadata(node_id)
            node_data = {
                "id": node_id,
                "name": meta["name"],
                "description": meta["description"],
                "category": meta["category"],
                "toolOrModel": meta["toolOrModel"],
                "icon": meta.get("icon", "🔧")
            }

            # Add decision node markers from metadata or known set
            if node_id in decision_nodes or meta.get("isDecisionNode", False):
                node_data["isDecisionNode"] = True
                node_data["outcomes"] = meta.get("outcomes", [])

            # Add orchestrator markers from metadata or by name pattern
            if meta.get("isOrchestrator", False) or meta.get("category") == "orchestrator" or "orchestrator" in node_id.lower():
                node_data["isOrchestrator"] = True

            nodes.append(node_data)

        # Include all edges - no longer filtering out decision nodes
        filtered_edges = all_edges

        # Conditional functions with descriptions
        conditional_functions = [
            {
                "name": "should_use_advanced_preset",
                "description": "Check if advanced preset (Preset 2) should be used",
                "outcomes": ["advanced", "standard"]
            },
            {
                "name": "requires_phet_simulation",
                "description": "Check if PHET_SIMULATION template is selected",
                "outcomes": ["phet_pipeline", "standard_pipeline"]
            },
            {
                "name": "check_routing_confidence",
                "description": "Check if router confidence >= 0.7",
                "outcomes": ["high", "low"]
            },
            {
                "name": "should_use_agentic_design",
                "description": "Check if agentic game design flow should be used (Preset 2)",
                "outcomes": ["agentic", "standard"]
            },
            {
                "name": "should_use_scene_sequencer",
                "description": "Check if scene sequencer should be used (Preset 2)",
                "outcomes": ["sequencer", "direct"]
            },
            {
                "name": "should_use_multi_scene_orchestrator",
                "description": "Check if multi-scene orchestration is needed",
                "outcomes": ["multi_scene", "single_scene"]
            },
            {
                "name": "requires_diagram_image",
                "description": "Check if INTERACTIVE_DIAGRAM template with images enabled",
                "outcomes": ["use_image", "skip_image"]
            },
            {
                "name": "should_use_preset_pipeline",
                "description": "Check if preset pipeline (diagram generation) should be used",
                "outcomes": ["preset", "default"]
            },
            {
                "name": "check_image_labeled",
                "description": "Check if diagram has existing text labels",
                "outcomes": ["labeled", "unlabeled"]
            },
            {
                "name": "check_zone_labels_complete",
                "description": "Check if zone labeling is complete or needs retry",
                "outcomes": ["retry_image", "continue"]
            },
            {
                "name": "check_validation_result",
                "description": "Check blueprint validation result",
                "outcomes": ["valid", "retry", "fail"]
            },
            {
                "name": "check_diagram_spec_validation",
                "description": "Check diagram spec validation result",
                "outcomes": ["valid", "retry", "fail"]
            },
            {
                "name": "is_stub_template",
                "description": "Check if template needs code generation",
                "outcomes": ["production", "stub"]
            },
            {
                "name": "check_code_validation",
                "description": "Check code verification result",
                "outcomes": ["valid", "retry", "fail"]
            },
            {
                "name": "check_phet_blueprint_validation",
                "description": "Check PhET blueprint validation result",
                "outcomes": ["valid", "retry", "fail"]
            },
            {
                "name": "should_run_asset_pipeline",
                "description": "Check if asset pipeline should run based on template type and scene data",
                "outcomes": ["run_assets", "skip_assets"]
            },
            {
                "name": "should_run_diagram_spec",
                "description": "Check if diagram spec generation is needed for visual templates",
                "outcomes": ["run_diagram_spec", "skip_diagram_spec"]
            },
            {
                "name": "should_use_multi_scene",
                "description": "Check if multi-scene orchestration is needed based on scene_breakdown",
                "outcomes": ["multi_scene", "single_scene"]
            },
        ]

        return {
            "topology": topology,
            "preset": preset or os.environ.get("PIPELINE_PRESET", "interactive_diagram_hierarchical"),
            "nodes": nodes,
            "edges": filtered_edges,
            "conditionalFunctions": conditional_functions
        }

    finally:
        # Restore original preset
        if original_preset is not None:
            os.environ["PIPELINE_PRESET"] = original_preset
        elif preset and "PIPELINE_PRESET" in os.environ:
            del os.environ["PIPELINE_PRESET"]


@router.get("/runs/{run_id}/execution-path")
async def get_execution_path(
    run_id: str = Path(..., description="The run ID"),
    db: Session = Depends(get_db)
):
    """
    Get the actual execution path taken in a run.

    Returns:
        - executedStages: Ordered list of stages that actually ran
        - edgesTaken: Which edges were actually traversed
        - conditionalDecisions: Which branch was taken at each conditional
        - retries: Which agents were retried and how many times
        - totals: Aggregated cost, tokens, duration, and retry count
    """
    # Get the run
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get all stages for this run
    stages = (
        db.query(StageExecution)
        .filter(StageExecution.run_id == run_id)
        .order_by(StageExecution.stage_order)
        .all()
    )

    # Build executed stages list
    executed_stages = []
    stage_execution_counts = {}

    for stage in stages:
        stage_name = stage.stage_name

        # Count executions per stage (for retry detection)
        stage_execution_counts[stage_name] = stage_execution_counts.get(stage_name, 0) + 1

        executed_stages.append({
            "stageName": stage_name,
            "stageOrder": stage.stage_order,
            "status": stage.status,
            "retryCount": stage.retry_count or 0,
            "executionNumber": stage_execution_counts[stage_name],
            "durationMs": stage.duration_ms,
            "tokens": stage.total_tokens or 0,
            "cost": float(stage.estimated_cost_usd) if stage.estimated_cost_usd else 0.0,
            "model": stage.model_id,
            "startedAt": stage.started_at.isoformat() if stage.started_at else None,
            "finishedAt": stage.finished_at.isoformat() if stage.finished_at else None,
        })

    # Build edges taken based on execution order
    edges_taken = []
    for i in range(len(stages) - 1):
        current_stage = stages[i]
        next_stage = stages[i + 1]

        # Determine if this was a conditional edge
        edge_type = "direct"
        condition = None

        # Detect conditional edges based on stage transitions
        conditional_transitions = {
            ("router", "human_review"): ("check_routing_confidence", "low"),
            ("router", "game_planner"): ("check_routing_confidence", "high"),
            ("router", "diagram_analyzer"): ("should_use_agentic_design", "agentic"),
            ("blueprint_validator", "blueprint_generator"): ("check_validation_result", "retry"),
            ("blueprint_validator", "asset_planner"): ("check_validation_result", "valid"),
            ("blueprint_validator", "human_review"): ("check_validation_result", "fail"),
            ("scene_stage3_interactions", "diagram_image_retriever"): ("requires_diagram_image", "use_image"),
            ("scene_stage3_interactions", "blueprint_generator"): ("requires_diagram_image", "skip_image"),
            ("image_label_classifier", "direct_structure_locator"): ("check_image_labeled", "unlabeled"),
            ("image_label_classifier", "image_label_remover"): ("check_image_labeled", "labeled"),
            ("diagram_spec_validator", "diagram_svg_generator"): ("check_diagram_spec_validation", "valid"),
            ("diagram_spec_validator", "diagram_spec_generator"): ("check_diagram_spec_validation", "retry"),
            ("qwen_sam_zone_detector", "blueprint_generator"): ("check_zone_labels_complete", "continue"),
            ("qwen_sam_zone_detector", "diagram_image_retriever"): ("check_zone_labels_complete", "retry_image"),
        }

        transition_key = (current_stage.stage_name, next_stage.stage_name)
        if transition_key in conditional_transitions:
            edge_type = "conditional"
            condition_func, condition_val = conditional_transitions[transition_key]
            condition = f"{condition_func} → {condition_val}"

        # Detect retry edges
        is_retry = (
            current_stage.stage_name == next_stage.stage_name or
            (current_stage.stage_name.endswith("_validator") and
             next_stage.stage_name == current_stage.stage_name.replace("_validator", "_generator"))
        )

        edges_taken.append({
            "from": current_stage.stage_name,
            "to": next_stage.stage_name,
            "type": edge_type,
            "condition": condition,
            "isRetryEdge": is_retry,
        })

    # Extract conditional decisions from stage outputs
    conditional_decisions = []
    for stage in stages:
        output = stage.output_snapshot or {}

        # Check for routing decisions
        if stage.stage_name == "router":
            template = output.get("template_selection", {})
            if template:
                conditional_decisions.append({
                    "function": "template_router",
                    "decision": template.get("template_type", "unknown"),
                    "confidence": template.get("confidence", 0),
                    "atStage": "router"
                })

        # Check for validation decisions
        if "_validator" in stage.stage_name:
            is_valid = stage.validation_passed
            conditional_decisions.append({
                "function": f"check_{stage.stage_name}_result",
                "decision": "valid" if is_valid else ("retry" if stage.retry_count < 3 else "fail"),
                "atStage": stage.stage_name
            })

        # Check for image classification
        if stage.stage_name == "image_label_classifier":
            classification = output.get("image_labeled_classification", "unknown")
            conditional_decisions.append({
                "function": "check_image_labeled",
                "decision": classification,
                "atStage": "image_label_classifier"
            })

    # Calculate totals
    total_cost = sum(float(s.estimated_cost_usd or 0) for s in stages)
    total_tokens = sum(s.total_tokens or 0 for s in stages)
    total_duration = sum(s.duration_ms or 0 for s in stages)
    total_retries = sum(s.retry_count or 0 for s in stages)

    # Count unique stages that had retries
    stages_with_retries = []
    for stage_name, count in stage_execution_counts.items():
        if count > 1:
            stages_with_retries.append({
                "stageName": stage_name,
                "executions": count
            })

    return {
        "runId": run_id,
        "runStatus": run.status,
        "executedStages": executed_stages,
        "edgesTaken": edges_taken,
        "conditionalDecisions": conditional_decisions,
        "stagesWithRetries": stages_with_retries,
        "totals": {
            "totalCost": round(total_cost, 6),
            "totalTokens": total_tokens,
            "totalDurationMs": total_duration,
            "retryCount": total_retries,
            "stagesExecuted": len(stages),
            "uniqueStages": len(stage_execution_counts)
        }
    }


# =============================================================================
# Analytics
# =============================================================================

@router.get("/analytics/runs")
async def get_run_analytics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get run statistics for the specified time period"""
    from datetime import timedelta
    from sqlalchemy import func

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Total runs
    total_runs = db.query(PipelineRun).filter(
        PipelineRun.started_at >= cutoff
    ).count()

    # Success rate
    successful_runs = db.query(PipelineRun).filter(
        PipelineRun.started_at >= cutoff,
        PipelineRun.status == "success"
    ).count()

    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

    # Average duration
    avg_duration = db.query(func.avg(PipelineRun.duration_ms)).filter(
        PipelineRun.started_at >= cutoff,
        PipelineRun.duration_ms.isnot(None)
    ).scalar() or 0

    # Runs by status
    status_counts = db.query(
        PipelineRun.status,
        func.count(PipelineRun.id)
    ).filter(
        PipelineRun.started_at >= cutoff
    ).group_by(PipelineRun.status).all()

    # Runs by topology
    topology_counts = db.query(
        PipelineRun.topology,
        func.count(PipelineRun.id)
    ).filter(
        PipelineRun.started_at >= cutoff
    ).group_by(PipelineRun.topology).all()

    return {
        "period_days": days,
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "success_rate_percent": round(success_rate, 1),
        "average_duration_ms": int(avg_duration),
        "runs_by_status": {status: count for status, count in status_counts},
        "runs_by_topology": {topology: count for topology, count in topology_counts}
    }


@router.get("/analytics/agents")
async def get_agent_analytics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get per-agent performance metrics"""
    from datetime import timedelta
    from sqlalchemy import func

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get runs from this period
    run_ids = db.query(PipelineRun.id).filter(
        PipelineRun.started_at >= cutoff
    ).subquery()

    # Get stage metrics grouped by agent
    metrics = db.query(
        StageExecution.stage_name,
        func.count(StageExecution.id).label("total_executions"),
        func.sum(
            func.case(
                (StageExecution.status == "success", 1),
                else_=0
            )
        ).label("successful"),
        func.avg(StageExecution.duration_ms).label("avg_duration_ms"),
        func.sum(StageExecution.total_tokens).label("total_tokens"),
        func.sum(StageExecution.estimated_cost_usd).label("total_cost")
    ).filter(
        StageExecution.run_id.in_(run_ids)
    ).group_by(StageExecution.stage_name).all()

    result = []
    for m in metrics:
        success_rate = (m.successful / m.total_executions * 100) if m.total_executions > 0 else 0
        result.append({
            "agent_name": m.stage_name,
            "total_executions": m.total_executions,
            "successful_executions": m.successful,
            "success_rate_percent": round(success_rate, 1),
            "average_duration_ms": int(m.avg_duration_ms or 0),
            "total_tokens": m.total_tokens or 0,
            "total_cost_usd": round(m.total_cost or 0, 4)
        })

    return {
        "period_days": days,
        "agents": sorted(result, key=lambda x: x["total_executions"], reverse=True)
    }


# =============================================================================
# Background Task Helpers
# =============================================================================

async def run_retry_pipeline(
    new_run_id: str,
    original_run_id: str,
    from_stage: str
):
    """
    Run a retry pipeline from a specific stage.

    Reconstructs state from original run's successful stages,
    then continues execution from the specified stage.
    
    Uses explicit transaction management to ensure atomic updates.
    """
    from app.db.database import SessionLocal
    from app.agents.graph import get_compiled_graph
    from app.agents.state import AgentState

    db = SessionLocal()
    run = None
    success = False
    
    try:
        # Get run and update status atomically
        run = db.query(PipelineRun).filter(PipelineRun.id == new_run_id).first()
        if not run:
            logger.error(f"Retry run {new_run_id} not found in database")
            return
        
        run.status = "running"
        if not run.started_at:
            run.started_at = datetime.utcnow()
        db.commit()

        # Reconstruct state from original run
        restored_state = await reconstruct_state_before_stage(
            original_run_id,
            from_stage,
            db
        )

        if not restored_state:
            run.status = "failed"
            run.error_message = "Failed to reconstruct state from original run"
            run.finished_at = datetime.utcnow()
            db.commit()
            return

        # Validate state before starting retry
        from app.agents.schemas.state_validation import validate_retry_state
        is_valid, error_message = validate_retry_state(restored_state, from_stage)
        
        if not is_valid:
            run.status = "failed"
            run.error_message = f"State validation failed: {error_message}"
            run.finished_at = datetime.utcnow()
            db.commit()
            logger.error(f"Retry validation failed for run {new_run_id}: {error_message}")
            return

        # Add run tracking info to state
        restored_state["_run_id"] = new_run_id

        # Find checkpoint_id from the stage before the target stage
        # This enables true resume from checkpoint, not just state restoration
        checkpoint_id = None
        try:
            target_stage_execution = db.query(StageExecution).filter(
                StageExecution.run_id == original_run_id,
                StageExecution.stage_name == from_stage
            ).first()
            
            if target_stage_execution:
                target_stage_order = target_stage_execution.stage_order
                
                # Find the stage before the target stage
                previous_stage = db.query(StageExecution).filter(
                    StageExecution.run_id == original_run_id,
                    StageExecution.stage_order < target_stage_order,
                    StageExecution.checkpoint_id.isnot(None)  # Only stages with checkpoints
                ).order_by(StageExecution.stage_order.desc()).first()
                
                if previous_stage and previous_stage.checkpoint_id:
                    checkpoint_id = previous_stage.checkpoint_id
                    logger.info(
                        f"Found checkpoint_id {checkpoint_id} from stage '{previous_stage.stage_name}' "
                        f"(order={previous_stage.stage_order}) for retry from '{from_stage}'"
                    )
                else:
                    logger.info(
                        f"No checkpoint found before target stage '{from_stage}'. "
                        f"This is likely a retry from the first stage or an old run without checkpoints. "
                        f"Will use restored state as initial input (backward compatible)."
                    )
            else:
                logger.warning(
                    f"Target stage '{from_stage}' not found in original run {original_run_id}. "
                    f"Will proceed with full graph execution."
                )
        except Exception as e:
            logger.error(
                f"Error finding checkpoint for retry: {e}. "
                f"Will fallback to full graph execution with restored state.",
                exc_info=True
            )
            # Continue with checkpoint_id = None (fallback mode)

        # Get compiled graph
        graph = get_compiled_graph()
        
        # Configure retry: use checkpoint_id if available, otherwise use restored_state as initial input
        try:
            if checkpoint_id:
                # Resume from checkpoint - LangGraph will only execute nodes after the checkpoint
                config = {
                    "configurable": {
                        "thread_id": new_run_id,
                        "checkpoint_id": checkpoint_id
                    }
                }
                logger.info(
                    f"Resuming from checkpoint {checkpoint_id} for retry run {new_run_id} "
                    f"from stage '{from_stage}'. Only stages after checkpoint will execute."
                )
                
                # When resuming from checkpoint, LangGraph uses the checkpoint state as base
                # We provide restored_state for any state updates needed
                # LangGraph will merge checkpoint state with provided updates
                final_state = await graph.ainvoke(restored_state, config)
            else:
                # No checkpoint available (first stage retry or old run without checkpoints)
                # Fallback to full graph execution with restored state
                # This is backward compatible with old runs
                config = {"configurable": {"thread_id": new_run_id}}
                logger.info(
                    f"No checkpoint available for retry from '{from_stage}'. "
                    f"Using full graph execution with restored state (backward compatible mode)."
                )
                final_state = await graph.ainvoke(restored_state, config)
        except Exception as checkpoint_error:
            # If checkpoint resume fails, try fallback to full graph
            logger.warning(
                f"Failed to resume from checkpoint {checkpoint_id}: {checkpoint_error}. "
                f"Falling back to full graph execution.",
                exc_info=True
            )
            config = {"configurable": {"thread_id": new_run_id}}
            final_state = await graph.ainvoke(restored_state, config)

        # Update run with result atomically
        run.status = "success" if final_state.get("generation_complete") else "failed"
        run.finished_at = datetime.utcnow()
        if run.started_at:
            run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
        run.error_message = final_state.get("error_message")
        db.commit()
        success = True

        logger.info(f"Retry run {new_run_id} completed with status: {run.status}")

    except Exception as e:
        logger.error(f"Retry pipeline failed for run {new_run_id}: {e}", exc_info=True)
        # Rollback any partial changes
        db.rollback()
        
        # Update run status to failed (in new transaction)
        try:
            if run:
                run.status = "failed"
                run.error_message = str(e)[:1000]  # Truncate long error messages
                run.finished_at = datetime.utcnow()
                if run.started_at:
                    run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
                db.commit()
            else:
                # Try to get run again if we lost the reference
                run = db.query(PipelineRun).filter(PipelineRun.id == new_run_id).first()
                if run:
                    run.status = "failed"
                    run.error_message = str(e)[:1000]
                    run.finished_at = datetime.utcnow()
                    db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update run status after error: {update_error}", exc_info=True)
            db.rollback()
    finally:
        # Always close the database session
        db.close()


async def reconstruct_state_before_stage(
    run_id: str,
    target_stage: str,
    db: Session
) -> Optional[dict]:
    """
    Rebuild state from successful stage outputs before the target stage.

    Goes through all successful stages in order and merges their
    output snapshots to reconstruct the state at that point.
    """
    # Get original run
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        return None

    # Start with initial state from config snapshot
    # Backward compatibility: if initial_state not in snapshot, try to reconstruct from question_id
    if run.config_snapshot and "initial_state" in run.config_snapshot:
        state = run.config_snapshot["initial_state"].copy()
    else:
        # Fallback for old runs: reconstruct from question_id if available
        state = {}
        if run.config_snapshot and "question_id" in run.config_snapshot:
            from app.db.models import Question
            question = db.query(Question).filter(Question.id == run.config_snapshot["question_id"]).first()
            if question:
                from app.agents.state import create_initial_state
                state = create_initial_state(
                    question_id=question.id,
                    question_text=question.text,
                    question_options=question.options
                )
        # If no question found, return empty state (will fail validation later)
        if not state:
            logger.warning(f"Could not reconstruct initial_state for run {run_id}, config_snapshot: {run.config_snapshot}")
            state = {}

    # Get all successful and degraded stages before target, ordered by execution
    # Include degraded stages to capture partial work
    stages = db.query(StageExecution).filter(
        StageExecution.run_id == run_id,
        StageExecution.status.in_(["success", "degraded"])
    ).order_by(StageExecution.stage_order).all()

    # Apply each stage's output until we reach the target
    # Validate outputs before merging to ensure data integrity
    for stage in stages:
        if stage.stage_name == target_stage:
            break
        
        if stage.output_snapshot:
            # Validate stage output before merging
            is_valid, validation_error = _validate_stage_output(stage.output_snapshot, stage.stage_name)
            
            if is_valid:
                state.update(stage.output_snapshot)
                if stage.status == "degraded":
                    logger.info(
                        f"Including degraded stage '{stage.stage_name}' output in state reconstruction "
                        f"for run {run_id}. Output validated successfully."
                    )
                else:
                    logger.debug(
                        f"Including successful stage '{stage.stage_name}' output in state reconstruction "
                        f"for run {run_id}"
                    )
            else:
                logger.warning(
                f"Skipping invalid output from stage '{stage.stage_name}' (status: {stage.status}) "
                f"in state reconstruction for run {run_id}: {validation_error}"
            )

    return state


def _validate_stage_output(output_snapshot: dict, stage_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a stage's output snapshot before merging into state.
    
    Args:
        output_snapshot: The output snapshot dictionary
        stage_name: Name of the stage that produced this output
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    logger.debug(f"Validating output snapshot for stage '{stage_name}'")
    
    if not isinstance(output_snapshot, dict):
        logger.warning(f"Stage '{stage_name}' output snapshot is not a dictionary (type: {type(output_snapshot)})")
        return False, f"Output snapshot is not a dictionary (type: {type(output_snapshot)})"
    
    if not output_snapshot:
        logger.warning(f"Stage '{stage_name}' output snapshot is empty")
        return False, "Output snapshot is empty"
    
    # Basic validation: check for common issues
    # Check for None values in critical fields (may indicate incomplete output)
    critical_none_count = sum(1 for v in output_snapshot.values() if v is None)
    total_keys = len(output_snapshot)
    
    # If more than 50% of values are None, consider it invalid
    if total_keys > 0 and critical_none_count / total_keys > 0.5:
        error_msg = f"Too many None values in output ({critical_none_count}/{total_keys})"
        logger.warning(f"Stage '{stage_name}' output validation failed: {error_msg}")
        return False, error_msg
    
    # Check for empty lists/dicts in expected non-empty fields
    # This is stage-specific, but we can do basic checks
    empty_collections = [
        k for k, v in output_snapshot.items()
        if isinstance(v, (list, dict)) and len(v) == 0
    ]
    
    # Log warning but don't fail - empty collections might be valid
    if empty_collections:
        logger.debug(
            f"Stage '{stage_name}' output contains empty collections: {empty_collections}. "
            "This may be expected for some stages."
        )
    
    logger.debug(f"Stage '{stage_name}' output snapshot validation passed")
    return True, None


# =============================================================================
# Analytics Endpoints - Cost & Token Metrics
# =============================================================================

class CostByTemplateItem(BaseModel):
    """Cost breakdown item for a template type"""
    template: str
    run_count: int
    total_cost: float
    avg_cost: float


class CostByTemplateResponse(BaseModel):
    """Response for cost by template analytics"""
    data: List[CostByTemplateItem]
    period_days: int


class MetricsSummaryResponse(BaseModel):
    """Response for aggregate metrics summary"""
    total_runs: int
    success_rate: float
    avg_duration_ms: Optional[float]
    total_cost_usd: float
    total_tokens: int
    runs_by_topology: dict
    runs_by_status: dict
    period_days: int


class CostTrendItem(BaseModel):
    """Daily cost trend item"""
    date: str
    cost: float
    runs: int
    tokens: int


class CostTrendResponse(BaseModel):
    """Response for cost trend over time"""
    data: List[CostTrendItem]
    period_days: int


@router.get("/analytics/cost-by-template", response_model=CostByTemplateResponse)
async def get_cost_by_template(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get cost breakdown by template type over a time period.

    Returns total cost, average cost per run, and run count for each template.
    """
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)

    # Query runs with their template type from config_snapshot
    results = db.query(
        func.json_extract(PipelineRun.config_snapshot, '$.template').label('template'),
        func.count(PipelineRun.id).label('run_count'),
        func.sum(PipelineRun.total_cost_usd).label('total_cost'),
        func.avg(PipelineRun.total_cost_usd).label('avg_cost'),
    ).filter(
        PipelineRun.started_at >= since,
        PipelineRun.status == 'success'
    ).group_by('template').all()

    data = []
    for r in results:
        template = r.template if r.template else "unknown"
        # Strip quotes from JSON extraction if present
        if isinstance(template, str):
            template = template.strip('"')
        data.append(CostByTemplateItem(
            template=template,
            run_count=r.run_count or 0,
            total_cost=float(r.total_cost or 0),
            avg_cost=float(r.avg_cost or 0)
        ))

    return CostByTemplateResponse(data=data, period_days=days)


@router.get("/analytics/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get aggregate metrics summary for a time period.

    Returns total runs, success rate, average duration, total cost, total tokens,
    and breakdowns by topology and status.
    """
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)

    # Total runs
    total_runs = db.query(func.count(PipelineRun.id)).filter(
        PipelineRun.started_at >= since
    ).scalar() or 0

    # Successful runs
    successful_runs = db.query(func.count(PipelineRun.id)).filter(
        PipelineRun.started_at >= since,
        PipelineRun.status == 'success'
    ).scalar() or 0

    # Success rate
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0.0

    # Average duration
    avg_duration = db.query(func.avg(PipelineRun.duration_ms)).filter(
        PipelineRun.started_at >= since,
        PipelineRun.duration_ms.isnot(None)
    ).scalar()

    # Total cost
    total_cost = db.query(func.sum(PipelineRun.total_cost_usd)).filter(
        PipelineRun.started_at >= since
    ).scalar() or 0.0

    # Total tokens
    total_tokens = db.query(func.sum(PipelineRun.total_tokens)).filter(
        PipelineRun.started_at >= since
    ).scalar() or 0

    # Runs by topology
    topology_results = db.query(
        PipelineRun.topology,
        func.count(PipelineRun.id)
    ).filter(
        PipelineRun.started_at >= since
    ).group_by(PipelineRun.topology).all()
    runs_by_topology = {r[0]: r[1] for r in topology_results}

    # Runs by status
    status_results = db.query(
        PipelineRun.status,
        func.count(PipelineRun.id)
    ).filter(
        PipelineRun.started_at >= since
    ).group_by(PipelineRun.status).all()
    runs_by_status = {r[0]: r[1] for r in status_results}

    return MetricsSummaryResponse(
        total_runs=total_runs,
        success_rate=round(success_rate, 2),
        avg_duration_ms=round(avg_duration, 2) if avg_duration else None,
        total_cost_usd=round(float(total_cost), 4),
        total_tokens=total_tokens,
        runs_by_topology=runs_by_topology,
        runs_by_status=runs_by_status,
        period_days=days
    )


@router.get("/analytics/cost-trend", response_model=CostTrendResponse)
async def get_cost_trend(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get daily cost trend over a time period.

    Returns cost, run count, and token usage per day.
    """
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)

    # Group by date
    results = db.query(
        func.date(PipelineRun.started_at).label('date'),
        func.sum(PipelineRun.total_cost_usd).label('cost'),
        func.count(PipelineRun.id).label('runs'),
        func.sum(PipelineRun.total_tokens).label('tokens'),
    ).filter(
        PipelineRun.started_at >= since
    ).group_by(func.date(PipelineRun.started_at)).order_by('date').all()

    data = []
    for r in results:
        date_str = str(r.date) if r.date else ""
        data.append(CostTrendItem(
            date=date_str,
            cost=float(r.cost or 0),
            runs=r.runs or 0,
            tokens=r.tokens or 0
        ))

    return CostTrendResponse(data=data, period_days=days)


class ErrorItem(BaseModel):
    """Error breakdown item"""
    stage_name: str
    error_count: int
    error_samples: List[str]


class ErrorAnalysisResponse(BaseModel):
    """Response for error analysis"""
    total_failed_runs: int
    total_failed_stages: int
    errors_by_stage: List[ErrorItem]
    errors_by_topology: dict
    period_days: int


@router.get("/analytics/errors", response_model=ErrorAnalysisResponse)
async def get_error_analysis(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get error analysis and categorization over a time period.

    Returns error counts by stage, topology, and sample error messages.
    """
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)

    # Total failed runs
    total_failed_runs = db.query(func.count(PipelineRun.id)).filter(
        PipelineRun.started_at >= since,
        PipelineRun.status == 'failed'
    ).scalar() or 0

    # Total failed stages
    total_failed_stages = db.query(func.count(StageExecution.id)).filter(
        StageExecution.status == 'failed'
    ).join(PipelineRun).filter(
        PipelineRun.started_at >= since
    ).scalar() or 0

    # Errors by stage
    stage_errors = db.query(
        StageExecution.stage_name,
        func.count(StageExecution.id).label('count')
    ).filter(
        StageExecution.status == 'failed'
    ).join(PipelineRun).filter(
        PipelineRun.started_at >= since
    ).group_by(StageExecution.stage_name).order_by(desc('count')).limit(10).all()

    errors_by_stage = []
    for stage_name, count in stage_errors:
        # Get sample error messages for this stage
        samples = db.query(StageExecution.error_message).filter(
            StageExecution.stage_name == stage_name,
            StageExecution.status == 'failed',
            StageExecution.error_message.isnot(None)
        ).join(PipelineRun).filter(
            PipelineRun.started_at >= since
        ).limit(3).all()

        errors_by_stage.append(ErrorItem(
            stage_name=stage_name,
            error_count=count,
            error_samples=[s[0][:200] if s[0] else "" for s in samples]  # Truncate to 200 chars
        ))

    # Errors by topology
    topology_errors = db.query(
        PipelineRun.topology,
        func.count(PipelineRun.id)
    ).filter(
        PipelineRun.started_at >= since,
        PipelineRun.status == 'failed'
    ).group_by(PipelineRun.topology).all()
    errors_by_topology = {r[0]: r[1] for r in topology_errors}

    return ErrorAnalysisResponse(
        total_failed_runs=total_failed_runs,
        total_failed_stages=total_failed_stages,
        errors_by_stage=errors_by_stage,
        errors_by_topology=errors_by_topology,
        period_days=days
    )
