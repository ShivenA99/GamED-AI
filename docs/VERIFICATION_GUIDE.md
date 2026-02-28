# Retry Functionality Verification Guide

This guide provides step-by-step instructions for verifying all 10 implemented retry functionality fixes, both from terminal and browser UI.

---

## Prerequisites

1. **Backend running**: `cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000`
2. **Frontend running**: `cd frontend && npm run dev`
3. **Database initialized**: Tables should be created automatically on first run

---

## Terminal Verification

### Run All Verification Tests

```bash
cd backend
PYTHONPATH=. python scripts/verify_retry_fixes.py
```

### Run Specific Fix Verification

```bash
# Verify Fix 1 (Initial State)
PYTHONPATH=. python scripts/verify_retry_fixes.py --fix 1

# Verify Fix 3 (Degraded Stages)
PYTHONPATH=. python scripts/verify_retry_fixes.py --fix 3

# Verify Fix 4 (State Validation)
PYTHONPATH=. python scripts/verify_retry_fixes.py --fix 4

# Verify Fix 7 (Retry Depth)
PYTHONPATH=. python scripts/verify_retry_fixes.py --fix 7

# Verify Fix 11 (Snapshot Truncation)
PYTHONPATH=. python scripts/verify_retry_fixes.py --fix 11
```

### Run Pytest Tests

```bash
cd backend
PYTHONPATH=. pytest tests/test_retry_functionality.py -v
```

---

## Browser UI Verification

### Setup

1. Start backend: `cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser: `http://localhost:3000`
4. Open browser DevTools (F12 or Cmd+Option+I)

### Browser Console Verification

The frontend includes verification utilities that can be run in the browser console:

```javascript
// Verify all fixes for a run
await verifyRetryFixes.all('run-id-here')

// Verify specific fixes
await verifyRetryFixes.fix1('run-id-here')  // Initial state
await verifyRetryFixes.fix3('run-id-here')  // Degraded stages
await verifyRetryFixes.fix7('run-id-here')  // Retry depth
await verifyRetryFixes.fix10('run-id-here') // Breadcrumb
await verifyRetryFixes.fix11('run-id-here', 'stage-id-here') // Snapshot truncation
```

### Fix 1: Initial State Storage

**Steps:**
1. Navigate to `/games` page
2. Create a new game/question (or use existing)
3. Wait for pipeline to complete or fail
4. Navigate to pipeline run detail page: `/pipeline/runs/{run_id}`
5. Open browser DevTools → Network tab
6. Check API response for `/api/observability/runs/{run_id}`
7. **Verify**: `config_snapshot.initial_state` exists and contains `question_id`, `question_text`, `question_options`

**Expected Result:**
```json
{
  "config_snapshot": {
    "initial_state": {
      "question_id": "...",
      "question_text": "...",
      "question_options": [...]
    }
  }
}
```

---

### Fix 3: Degraded Stages Inclusion

**Steps:**
1. Create a pipeline run that has at least one stage with `status: "degraded"`
2. Navigate to run detail page
3. Click on a failed/degraded stage to open StagePanel
4. Check the stage's output snapshot
5. Try to retry from a stage after the degraded stage
6. **Verify**: Retry succeeds and includes data from degraded stage

**Expected Result:**
- Degraded stages appear in stage list
- Retry from stage after degraded stage includes degraded stage's output

---

### Fix 4: State Validation

**Steps:**
1. Navigate to a failed pipeline run
2. Open browser DevTools → Console
3. Try to retry from a stage that requires specific state keys (e.g., `blueprint_generator`)
4. If state is incomplete, **Verify**: Error message shows missing required keys

**Expected Result:**
- Clear error message: "Missing required state keys for stage 'blueprint_generator': game_plan, scene_data"
- Error is user-friendly and actionable

---

### Fix 5: Race Condition Prevention

**Steps:**
1. Navigate to a failed pipeline run
2. Open StagePanel for a failed stage
3. Open browser DevTools → Network tab
4. Click "Retry" button
5. **Immediately** click "Retry" button again (before first request completes)
6. **Verify**: Only one retry run is created, second request returns 409 Conflict

**Expected Result:**
- First retry request succeeds (201 Created)
- Second concurrent request returns 409 Conflict with message about existing retry

---

### Fix 6: Transaction Management

**Steps:**
1. Create a pipeline run that will fail during retry (e.g., missing required state)
2. Navigate to run detail page
3. Click retry on a failed stage
4. Check database/API for the new retry run
5. **Verify**: If retry fails, run status is "failed" with error message, no partial state

**Expected Result:**
- Failed retry runs have `status: "failed"` and `error_message` set
- No orphaned or partially completed retry runs

---

### Fix 7: Retry Depth Limit

**Steps:**
1. Create an original pipeline run (depth 0)
2. Retry from a failed stage (creates depth 1)
3. Retry from the retry run (creates depth 2)
4. Retry from depth 2 run (creates depth 3)
5. Try to retry from depth 3 run
6. **Verify**: Retry is rejected with error about max depth exceeded

**Expected Result:**
- Retries work up to depth 3
- Retry at depth 4 is rejected: "Maximum retry depth (3) exceeded"

---

### Fix 8: Database Index Performance

**Steps:**
1. Create a pipeline run with many stages (20+)
2. Navigate to run detail page
3. Open browser DevTools → Network tab
4. Check response time for `/api/observability/runs/{run_id}/stages`
5. **Verify**: Response is fast (< 500ms) even with many stages

**Expected Result:**
- Fast API response times
- No noticeable lag when loading stage data

---

### Fix 9: Frontend Loading States

**Steps:**
1. Navigate to a failed pipeline run
2. Open StagePanel for a failed stage
3. Click "Retry" button
4. **Verify**: 
   - Button becomes disabled immediately
   - Spinner icon appears
   - Button text changes to "Retrying..."
   - Button re-enables after request completes (success or error)

**Expected Result:**
- Button disabled during retry
- Visual loading indicator (spinner)
- No double-clicks possible

---

### Fix 10: Retry Lineage Breadcrumb

**Steps:**
1. Create a retry chain: Original → Retry #1 → Retry #2
2. Navigate to Retry #2's detail page
3. **Verify**: Breadcrumb shows: `Original Run #1 → Retry #1 → Retry #2 → Current Run #3`
4. Click on each link in breadcrumb
5. **Verify**: Each link navigates to the correct run page

**Expected Result:**
- Breadcrumb displays full retry chain
- Each link is clickable and navigates correctly
- Retry depth badge shows correct depth

---

### Fix 11: Snapshot Truncation

**Steps:**
1. Create a pipeline run with a stage that produces large output (>200KB)
2. Navigate to run detail page
3. Open StagePanel for that stage
4. Check output snapshot
5. **Verify**: If snapshot was large, it contains `_truncated: true` and `_original_size_kb` metadata

**Expected Result:**
- Large snapshots are truncated
- Truncation metadata is present
- Top-level keys are preserved

---

## API Verification (Using curl)

### Verify Fix 1: Check initial_state in config_snapshot

```bash
# Get run details
curl http://localhost:8000/api/observability/runs/{run_id} | jq '.config_snapshot.initial_state'
```

**Expected**: Returns initial_state object with question_id, question_text, etc.

### Verify Fix 5: Test concurrent retries

```bash
# First retry request (in background)
curl -X POST http://localhost:8000/api/observability/runs/{run_id}/retry \
  -H "Content-Type: application/json" \
  -d '{"from_stage": "blueprint_generator"}' &

# Second concurrent request (should fail)
curl -X POST http://localhost:8000/api/observability/runs/{run_id}/retry \
  -H "Content-Type: application/json" \
  -d '{"from_stage": "blueprint_generator"}'
```

**Expected**: Second request returns 409 Conflict

### Verify Fix 7: Test retry depth limit

```bash
# Try to retry from a depth 3 run
curl -X POST http://localhost:8000/api/observability/runs/{depth_3_run_id}/retry \
  -H "Content-Type: application/json" \
  -d '{"from_stage": "blueprint_generator"}'
```

**Expected**: Returns 400 Bad Request with message about max depth exceeded

---

## Database Verification

### Check retry_depth column exists

```bash
# SQLite
sqlite3 backend/gamed_ai_v2.db "PRAGMA table_info(pipeline_runs);" | grep retry_depth

# PostgreSQL
psql -d your_db -c "\d pipeline_runs" | grep retry_depth
```

### Check composite index exists

```bash
# SQLite
sqlite3 backend/gamed_ai_v2.db ".indices stage_executions" | grep idx_stage_run_status_order

# PostgreSQL
psql -d your_db -c "\d stage_executions" | grep idx_stage_run_status_order
```

### Verify initial_state in config_snapshot

```bash
# SQLite
sqlite3 backend/gamed_ai_v2.db "SELECT json_extract(config_snapshot, '$.initial_state.question_id') FROM pipeline_runs LIMIT 1;"
```

---

## Verification Checklist

Use this checklist to track verification progress:

### Terminal Tests
- [ ] Run `verify_retry_fixes.py` - All tests pass
- [ ] Run `pytest tests/test_retry_functionality.py` - All tests pass

### Browser UI Tests
- [ ] Fix 1: initial_state visible in API response
- [ ] Fix 3: Degraded stages included in retry
- [ ] Fix 4: Validation errors show clearly
- [ ] Fix 5: Concurrent retries prevented (409 error)
- [ ] Fix 6: Failed retries have proper error messages
- [ ] Fix 7: Retry depth limit enforced (max 3)
- [ ] Fix 8: Fast API response times
- [ ] Fix 9: Loading states work (button disabled, spinner)
- [ ] Fix 10: Breadcrumb shows retry chain
- [ ] Fix 11: Large snapshots truncated with metadata

### Database Verification
- [ ] `retry_depth` column exists
- [ ] Composite index `idx_stage_run_status_order` exists
- [ ] `initial_state` stored in `config_snapshot`

---

## Troubleshooting

### Tests fail with "Table does not exist"
**Solution**: Run `init_db()` or restart backend (tables auto-create)

### API returns 404 for retry endpoint
**Solution**: Check backend is running on port 8000 and route is registered

### Frontend shows errors
**Solution**: Check browser console for errors, verify frontend is running on port 3000

### Database migration needed
**Solution**: Run SQL migrations from implementation summary:
```sql
ALTER TABLE pipeline_runs ADD COLUMN retry_depth INTEGER NOT NULL DEFAULT 0;
CREATE INDEX idx_stage_run_status_order ON stage_executions(run_id, status, stage_order);
```

---

**Last Updated**: 2026-01-24  
**Status**: Ready for Verification
