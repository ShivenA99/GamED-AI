"""Database Models for GamED.AI v2"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class Question(Base):
    """Uploaded question"""
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=generate_uuid)
    text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # List of options for MCQ
    source_file = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    processes = relationship("Process", back_populates="question")
    sessions = relationship("LearningSession", back_populates="question")


class Process(Base):
    """Game generation process tracking"""
    __tablename__ = "processes"

    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    status = Column(String(50), default="pending")  # pending, processing, completed, error, human_review
    current_agent = Column(String(100), nullable=True)
    progress_percent = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # LangGraph thread ID for resumption
    thread_id = Column(String, nullable=True)

    # Cost and token tracking (rolled up from pipeline runs)
    total_cost_usd = Column(Float, default=0.0)
    total_tokens = Column(Integer, default=0)
    total_llm_calls = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    question = relationship("Question", back_populates="processes")
    agent_executions = relationship("AgentExecution", back_populates="process")
    human_reviews = relationship("HumanReview", back_populates="process")
    visualization = relationship("Visualization", back_populates="process", uselist=False)


class AgentExecution(Base):
    """Track individual agent executions within a pipeline"""
    __tablename__ = "agent_executions"

    id = Column(String, primary_key=True, default=generate_uuid)
    process_id = Column(String, ForeignKey("processes.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    input_hash = Column(String(64), nullable=True)  # For caching
    output_hash = Column(String(64), nullable=True)
    status = Column(String(50), nullable=False)  # running, completed, failed
    execution_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    process = relationship("Process", back_populates="agent_executions")


class HumanReview(Base):
    """Track human-in-the-loop reviews"""
    __tablename__ = "human_reviews"

    id = Column(String, primary_key=True, default=generate_uuid)
    process_id = Column(String, ForeignKey("processes.id"), nullable=False)
    review_type = Column(String(100), nullable=False)  # template_routing, blueprint_validation, code_review, quality_gate
    artifact_type = Column(String(100), nullable=False)
    artifact_data = Column(JSON, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending, approved, rejected, modified
    reviewer_feedback = Column(Text, nullable=True)
    modified_data = Column(JSON, nullable=True)  # If reviewer made changes
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    process = relationship("Process", back_populates="human_reviews")


class Visualization(Base):
    """Generated game visualization"""
    __tablename__ = "visualizations"

    id = Column(String, primary_key=True, default=generate_uuid)
    process_id = Column(String, ForeignKey("processes.id"), nullable=False)
    template_type = Column(String(100), nullable=False)
    blueprint = Column(JSON, nullable=False)
    generated_code = Column(Text, nullable=True)  # For stub templates
    asset_urls = Column(JSON, nullable=True)
    pedagogical_context = Column(JSON, nullable=True)
    game_plan = Column(JSON, nullable=True)
    story_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    process = relationship("Process", back_populates="visualization")
    sessions = relationship("LearningSession", back_populates="visualization")


class LearningSession(Base):
    """Enhanced session tracking with learning analytics"""
    __tablename__ = "learning_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    visualization_id = Column(String, ForeignKey("visualizations.id"), nullable=False)
    user_identifier = Column(String(200), nullable=True)  # Anonymous or authenticated

    # Time tracking
    session_start = Column(DateTime, default=datetime.utcnow)
    session_end = Column(DateTime, nullable=True)
    total_time_seconds = Column(Integer, default=0)
    active_time_seconds = Column(Integer, default=0)  # Exclude idle time

    # Progress tracking
    current_question_index = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    hints_used = Column(Integer, default=0)

    # Scoring
    score_accuracy = Column(Float, default=0.0)  # 0-1
    score_efficiency = Column(Float, default=0.0)  # Based on time
    score_mastery = Column(Float, default=0.0)  # Bloom's taxonomy mapping
    raw_score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)

    # Learning analytics
    blooms_level_achieved = Column(String(50), nullable=True)
    concepts_mastered = Column(JSON, nullable=True)
    concepts_struggling = Column(JSON, nullable=True)

    # Status
    status = Column(String(50), default="active")  # active, completed, abandoned
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    question = relationship("Question", back_populates="sessions")
    visualization = relationship("Visualization", back_populates="sessions")
    attempts = relationship("AttemptRecord", back_populates="session")


class AttemptRecord(Base):
    """Individual question attempt"""
    __tablename__ = "attempt_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("learning_sessions.id"), nullable=False)
    question_index = Column(Integer, nullable=False)
    attempt_number = Column(Integer, nullable=False)
    selected_answer = Column(String(500), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_taken_seconds = Column(Integer, nullable=False)
    hints_viewed = Column(Integer, default=0)
    feedback_shown = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("LearningSession", back_populates="attempts")


# =============================================================================
# OBSERVABILITY MODELS - Pipeline Run Tracking & Agent Dashboard
# =============================================================================

class PipelineRun(Base):
    """
    Track individual pipeline runs with full observability.

    Each game generation creates a PipelineRun that tracks:
    - Which stages executed and their status
    - Timing and performance metrics
    - Configuration snapshot at run time
    - Retry lineage (if this run was a retry from another)
    """
    __tablename__ = "pipeline_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    process_id = Column(String, ForeignKey("processes.id"), nullable=True)  # Link to existing game

    # Run metadata
    run_number = Column(Integer, nullable=False, default=1)  # Version within same question
    topology = Column(String(50), nullable=False, default="T1")  # T0, T1, T2, etc.
    status = Column(String(50), nullable=False, default="pending")  # pending, running, success, failed, cancelled

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Cost and token tracking (rolled up from stage executions)
    total_cost_usd = Column(Float, default=0.0)
    total_tokens = Column(Integer, default=0)
    total_llm_calls = Column(Integer, default=0)

    # Configuration snapshot
    config_snapshot = Column(JSON, nullable=True)  # Model configs, env vars at run time

    # Final state (truncated for size)
    final_state_summary = Column(JSON, nullable=True)  # Key state values at end
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Retry tracking
    parent_run_id = Column(String, ForeignKey("pipeline_runs.id"), nullable=True)  # If this is a retry
    retry_from_stage = Column(String(100), nullable=True)  # Stage name if partial retry
    retry_depth = Column(Integer, nullable=False, default=0)  # Depth of retry chain (0 = original, 1 = first retry, etc.)

    # Relationships
    process = relationship("Process", backref="pipeline_runs")
    parent_run = relationship("PipelineRun", remote_side=[id], backref="child_runs")
    stage_executions = relationship("StageExecution", back_populates="run", cascade="all, delete-orphan")
    execution_logs = relationship("ExecutionLog", back_populates="run", cascade="all, delete-orphan")


class StageExecution(Base):
    """
    Track individual stage (agent) executions within a pipeline run.

    Captures:
    - Stage status and timing
    - Input/output state snapshots (truncated)
    - LLM metrics (model, tokens, cost)
    - Validation results for validator agents
    - Error details for debugging
    """
    __tablename__ = "stage_executions"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)

    # Stage identification
    stage_name = Column(String(100), nullable=False)  # e.g., "input_enhancer", "router"
    stage_order = Column(Integer, nullable=False)  # Execution order in this run

    # Status
    status = Column(String(50), nullable=False, default="pending")  # pending, running, success, failed, skipped

    # Timing
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Data (truncated snapshots for debugging)
    input_state_keys = Column(JSON, nullable=True)  # Which state keys were read
    output_state_keys = Column(JSON, nullable=True)  # Which state keys were written
    input_snapshot = Column(JSON, nullable=True)  # Relevant input data (truncated for size)
    output_snapshot = Column(JSON, nullable=True)  # Output data (truncated for size)

    # LLM metrics (if applicable)
    model_id = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    # Errors
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Validation (for validator agents)
    validation_passed = Column(Boolean, nullable=True)
    validation_score = Column(Float, nullable=True)
    validation_errors = Column(JSON, nullable=True)

    # LangGraph checkpointing (for retry from specific stage)
    checkpoint_id = Column(String(255), nullable=True)  # LangGraph checkpoint_id after this stage completes

    # Relationships
    run = relationship("PipelineRun", back_populates="stage_executions")
    logs = relationship("ExecutionLog", back_populates="stage_execution", cascade="all, delete-orphan")

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_stage_run_status_order', 'run_id', 'status', 'stage_order'),
        Index('idx_stage_checkpoint', 'run_id', 'checkpoint_id'),
    )


class ExecutionLog(Base):
    """
    Detailed execution logs for pipeline debugging.

    Captures structured log entries with metadata for:
    - Stage-level logging
    - LLM prompts/responses
    - Errors and warnings
    - Performance metrics
    """
    __tablename__ = "execution_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    stage_execution_id = Column(String, ForeignKey("stage_executions.id", ondelete="CASCADE"), nullable=True)

    # Log entry
    level = Column(String(20), nullable=False, default="info")  # debug, info, warn, error
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Structured metadata (JSON for flexibility)
    log_metadata = Column(JSON, nullable=True)

    # Relationships
    run = relationship("PipelineRun", back_populates="execution_logs")
    stage_execution = relationship("StageExecution", back_populates="logs")


class AgentRegistry(Base):
    """
    Static metadata about available agents.

    Used for:
    - Dashboard UI (display names, icons, colors)
    - Graph visualization (typical inputs/outputs)
    - Configuration defaults
    """
    __tablename__ = "agent_registry"

    id = Column(String(100), primary_key=True)  # e.g., "input_enhancer"
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # input, routing, generation, validation, etc.

    # Configuration defaults
    default_model = Column(String(100), nullable=True)
    default_temperature = Column(Float, nullable=True)
    default_max_tokens = Column(Integer, nullable=True)

    # Graph metadata
    typical_inputs = Column(JSON, nullable=True)  # State keys this agent reads
    typical_outputs = Column(JSON, nullable=True)  # State keys this agent writes

    # UI metadata
    icon = Column(String(50), nullable=True)  # Icon name (e.g., "cog", "search")
    color = Column(String(20), nullable=True)  # Hex color for node

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
