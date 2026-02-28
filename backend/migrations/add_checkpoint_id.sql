-- Migration: Add checkpoint_id column to stage_executions table
-- This enables LangGraph checkpointing for retry functionality
-- Run this migration before using the checkpointing feature

-- SQLite
ALTER TABLE stage_executions ADD COLUMN checkpoint_id VARCHAR(255);

-- Create index for fast checkpoint lookups
CREATE INDEX IF NOT EXISTS idx_stage_checkpoint ON stage_executions(run_id, checkpoint_id);

-- Note: For PostgreSQL, use:
-- ALTER TABLE stage_executions ADD COLUMN checkpoint_id VARCHAR(255);
-- CREATE INDEX idx_stage_checkpoint ON stage_executions(run_id, checkpoint_id);
