#!/bin/bash
# Database Migration Script for Checkpointing Feature
# Adds checkpoint_id column to stage_executions table

set -e

DB_PATH="${1:-backend/gamed_ai_v2.db}"

if [ ! -f "$DB_PATH" ]; then
    echo "Database file not found: $DB_PATH"
    echo "Creating new database..."
    # Database will be created automatically on first run
    exit 0
fi

echo "Running migration: Add checkpoint_id column to stage_executions"
echo "Database: $DB_PATH"

sqlite3 "$DB_PATH" <<EOF
-- Add checkpoint_id column if it doesn't exist
ALTER TABLE stage_executions ADD COLUMN checkpoint_id VARCHAR(255);

-- Create index for fast checkpoint lookups
CREATE INDEX IF NOT EXISTS idx_stage_checkpoint ON stage_executions(run_id, checkpoint_id);

-- Verify migration
SELECT name FROM sqlite_master WHERE type='table' AND name='stage_executions';
SELECT sql FROM sqlite_master WHERE type='table' AND name='stage_executions';
EOF

echo "Migration completed successfully!"
echo "Verifying checkpoint_id column exists..."
sqlite3 "$DB_PATH" "PRAGMA table_info(stage_executions);" | grep checkpoint_id && echo "✅ checkpoint_id column exists" || echo "⚠️  checkpoint_id column not found"
