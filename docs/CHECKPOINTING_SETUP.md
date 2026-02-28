# LangGraph Checkpointing Setup Guide

## Quick Setup (5 minutes)

### Step 1: Install Package

```bash
cd backend
pip install langgraph-checkpoint-sqlite
```

### Step 2: Run Database Migration

```bash
# Option A: Use migration script
bash backend/scripts/run_migration.sh

# Option B: Manual SQL
sqlite3 backend/gamed_ai_v2.db < backend/migrations/add_checkpoint_id.sql

# Option C: Direct SQLite command
sqlite3 backend/gamed_ai_v2.db "ALTER TABLE stage_executions ADD COLUMN checkpoint_id VARCHAR(255); CREATE INDEX IF NOT EXISTS idx_stage_checkpoint ON stage_executions(run_id, checkpoint_id);"
```

### Step 3: Restart Backend

```bash
# Kill existing backend
lsof -ti:8000 | xargs kill -9

# Start backend (will use database checkpointer)
cd backend
source venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

### Step 4: Verify Setup

```bash
# Check checkpoint infrastructure
cd backend
PYTHONPATH=. python scripts/verify_retry_fixes.py --fix 2
```

**Expected**: All checks pass

---

## What Changed

### Backend Changes

1. **Graph Compilation**: Now uses `SqliteSaver` instead of `MemorySaver`
2. **Pipeline Execution**: Uses `astream_events` to capture checkpoints
3. **Stage Tracking**: `checkpoint_id` saved to `StageExecution` after each stage
4. **Retry Logic**: Finds and uses `checkpoint_id` to resume from checkpoint

### Database Changes

- New column: `stage_executions.checkpoint_id` (VARCHAR(255))
- New index: `idx_stage_checkpoint` on `(run_id, checkpoint_id)`

### API Changes

- `StageExecution` responses now include `checkpoint_id` field
- Retry endpoint uses checkpoint_id when available

---

## Verification

After setup, verify checkpointing works:

1. **Create a new pipeline run** (via UI or API)
2. **Check checkpoints are saved**:
   ```bash
   sqlite3 backend/gamed_ai_v2.db "SELECT stage_name, checkpoint_id FROM stage_executions WHERE checkpoint_id IS NOT NULL LIMIT 5;"
   ```
3. **Test retry from middle stage**:
   - Find a run with multiple completed stages
   - Retry from a middle stage
   - Verify only later stages execute

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'"

**Solution**: Install package: `pip install langgraph-checkpoint-sqlite`

### "Column checkpoint_id does not exist"

**Solution**: Run migration: `bash backend/scripts/run_migration.sh`

### Checkpoints not being saved

**Check**:
1. Verify checkpointer is initialized (check logs on startup)
2. Verify `astream_events` is being used (check logs during execution)
3. Check for errors in checkpoint saving (check logs)

---

**Last Updated**: 2026-01-24
