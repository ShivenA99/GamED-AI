# LangGraph Checkpointing Verification Guide

## Overview

This guide provides step-by-step instructions for verifying Fix 2: LangGraph Checkpointing implementation. This enables true resume from specific stages during retry, not just agent skipping.

---

## Prerequisites

1. **Install checkpoint package**:
   ```bash
   cd backend
   pip install langgraph-checkpoint-sqlite
   ```

2. **Run database migration**:
   ```bash
   sqlite3 backend/gamed_ai_v2.db < backend/migrations/add_checkpoint_id.sql
   ```

3. **Backend running**: `cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000`
4. **Frontend running**: `cd frontend && npm run dev`

---

## Terminal Verification

### Step 1: Verify Checkpoint Infrastructure

```bash
cd backend
PYTHONPATH=. python scripts/verify_retry_fixes.py --fix 2
```

**Expected Output:**
```
✅ checkpoint_id column exists in StageExecution
✅ get_checkpointer() function works
✅ save_stage_checkpoint() function exists
✅ Fix 2 PASSED: Checkpointing infrastructure implemented and ready
```

### Step 2: Run Pytest Tests

```bash
cd backend
PYTHONPATH=. pytest tests/test_retry_functionality.py::TestFix2Checkpointing -v
```

**Expected**: All tests pass

### Step 3: Verify Checkpoint Saving

1. Create a new pipeline run (via API or UI)
2. Wait for at least 2-3 stages to complete
3. Check database:

```bash
sqlite3 backend/gamed_ai_v2.db "SELECT stage_name, checkpoint_id FROM stage_executions WHERE run_id='<run_id>' AND checkpoint_id IS NOT NULL;"
```

**Expected**: checkpoint_id values are populated for completed stages

---

## Browser UI Verification

### Step 1: Verify Checkpoints are Saved

1. Navigate to a completed pipeline run: `/pipeline/runs/{run_id}`
2. Open browser DevTools → Network tab
3. Check API response for `/api/observability/runs/{run_id}/stages`
4. **Verify**: Stages have `checkpoint_id` field (may be null for old runs)

### Step 2: Test Retry from Middle Stage

1. Find a run that failed at a middle stage (e.g., `blueprint_generator`)
2. Check that previous stages have `checkpoint_id` set
3. Click "Retry" on the failed stage
4. **Verify**: 
   - New run is created
   - Only stages after the retry point execute
   - Check logs/API calls - no duplicate calls for stages before retry point

### Step 3: Verify Checkpoint Resume

1. Open browser DevTools Console
2. Run:

```javascript
// Get current run ID
const runId = window.location.pathname.split('/').pop()

// Check if stages have checkpoints
fetch(`/api/observability/runs/${runId}/stages`)
  .then(r => r.json())
  .then(data => {
    const stagesWithCheckpoints = data.stages.filter(s => s.checkpoint_id)
    console.log(`Stages with checkpoints: ${stagesWithCheckpoints.length}/${data.stages.length}`)
    stagesWithCheckpoints.forEach(s => {
      console.log(`  ${s.stage_name}: ${s.checkpoint_id}`)
    })
  })
```

**Expected**: Completed stages have checkpoint_id values

---

## API Verification (Using curl)

### Verify Checkpoints are Saved

```bash
# Get stages for a run
curl http://localhost:8000/api/observability/runs/{run_id}/stages | jq '.stages[] | {stage_name, checkpoint_id}'
```

**Expected**: checkpoint_id values for completed stages

### Test Retry with Checkpoint

```bash
# Retry from a middle stage
curl -X POST http://localhost:8000/api/observability/runs/{run_id}/retry \
  -H "Content-Type: application/json" \
  -d '{"from_stage": "blueprint_generator"}'
```

**Expected**: 
- Returns new_run_id
- Check logs - only stages after blueprint_generator should execute
- No duplicate API calls for earlier stages

---

## Database Verification

### Check checkpoint_id Column

```bash
# SQLite
sqlite3 backend/gamed_ai_v2.db "PRAGMA table_info(stage_executions);" | grep checkpoint_id

# Should show: checkpoint_id column exists
```

### Check Checkpoint Index

```bash
sqlite3 backend/gamed_ai_v2.db ".indices stage_executions" | grep idx_stage_checkpoint
```

### Verify Checkpoints are Stored

```bash
sqlite3 backend/gamed_ai_v2.db "SELECT stage_name, checkpoint_id FROM stage_executions WHERE checkpoint_id IS NOT NULL LIMIT 5;"
```

**Expected**: Returns stages with checkpoint_id values

---

## Performance Verification

### Measure Retry Performance

1. **Without Checkpointing** (old behavior):
   - Retry runs full graph
   - All agents execute (even if they skip work)
   - Time: ~X seconds

2. **With Checkpointing** (new behavior):
   - Retry resumes from checkpoint
   - Only target stage and beyond execute
   - Time: ~Y seconds (should be < X)

**Expected**: Checkpoint-based retry is faster and uses fewer API calls

### Verify No Duplicate Work

1. Create a pipeline run
2. Note which LLM API calls are made (check logs)
3. Retry from a middle stage
4. **Verify**: 
   - No API calls for stages before retry point
   - Only stages after retry point make API calls
   - Check LLM costs - should be lower

---

## Verification Checklist

### Infrastructure
- [ ] `langgraph-checkpoint-sqlite` package installed
- [ ] `checkpoint_id` column exists in `stage_executions` table
- [ ] Index `idx_stage_checkpoint` created
- [ ] `get_checkpointer()` function works
- [ ] `save_stage_checkpoint()` function works

### Checkpoint Saving
- [ ] New pipeline runs save checkpoints after each stage
- [ ] `checkpoint_id` appears in StageExecution API responses
- [ ] Database contains checkpoint_id values

### Retry Functionality
- [ ] Retry from middle stage uses checkpoint_id
- [ ] Only stages after retry point execute
- [ ] No duplicate API calls for earlier stages
- [ ] Retry from first stage works (no checkpoint, uses restored state)
- [ ] Old runs without checkpoints still work (backward compatible)

### Error Handling
- [ ] Missing checkpoint falls back gracefully
- [ ] Invalid checkpoint_id handled
- [ ] Logs show checkpoint usage

---

## Troubleshooting

### Checkpoints Not Being Saved

**Symptoms**: `checkpoint_id` is always null

**Solutions**:
1. Verify `langgraph-checkpoint-sqlite` is installed: `pip list | grep langgraph-checkpoint`
2. Check logs for checkpoint saving errors
3. Verify database checkpointer is initialized (check logs on startup)
4. Ensure `astream_events` is being used (not `ainvoke`)

### Retry Still Runs Full Graph

**Symptoms**: All stages execute during retry

**Solutions**:
1. Verify checkpoint_id is found before target stage
2. Check logs for "Resuming from checkpoint" message
3. Verify config includes `checkpoint_id` in configurable
4. Check if checkpoint exists in LangGraph storage

### Checkpoint Not Found Error

**Symptoms**: Error about checkpoint not found

**Solutions**:
1. Verify checkpoint_id is valid (exists in LangGraph storage)
2. Check thread_id matches between original and retry
3. Verify checkpointer is same instance (singleton)
4. Check logs for checkpoint retrieval errors

---

## Success Criteria

- [ ] Checkpoints saved after each stage execution
- [ ] checkpoint_id stored in StageExecution table
- [ ] Retry from middle stage only executes from that point
- [ ] No duplicate work for stages before retry point
- [ ] Backward compatible (works if checkpoint_id missing)
- [ ] Proper error handling if checkpoint not found
- [ ] Logging shows checkpoint usage

---

**Last Updated**: 2026-01-24  
**Status**: Ready for Verification
