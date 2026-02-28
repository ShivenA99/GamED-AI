# Quick Verification Guide - Retry Functionality

Quick reference for verifying all retry functionality fixes.

---

## Terminal Verification (5 minutes)

### Run All Tests

```bash
cd backend

# Run verification script
PYTHONPATH=. python scripts/verify_retry_fixes.py

# Run pytest tests
PYTHONPATH=. pytest tests/test_retry_functionality.py -v
```

**Expected Output:**
```
✅ Fix 1 PASSED: initial_state stored in config_snapshot
✅ Fix 3 PASSED: Degraded stages included in reconstruction
✅ Fix 4 PASSED: State validation working correctly
✅ Fix 7 PASSED: Retry depth limit implemented
✅ Fix 11 PASSED: Snapshot truncation working
```

---

## Browser Console Verification (2 minutes)

1. Open browser: `http://localhost:3000`
2. Navigate to a pipeline run: `/pipeline/runs/{run_id}`
3. Open DevTools Console (F12)
4. Run:

```javascript
// Get current run ID from URL
const runId = window.location.pathname.split('/').pop()

// Run all verifications
await verifyRetryFixes.all(runId)
```

**Expected Output:**
```
🔍 Starting browser-based verification...
✅ Fix 1 PASSED: initial_state exists with required fields
✅ Fix 3 PASSED: Found 1 degraded stage(s)
✅ Fix 7 PASSED: retry_depth = 0 (within limit)
✅ Fix 10: Breadcrumb should display (depth: 0)
✅ Summary: 4 passed, 0 failed out of 5 checks
```

---

## Manual UI Checks (5 minutes)

### Fix 1: Initial State
- [ ] Open run detail page
- [ ] Check Network tab → API response
- [ ] Verify `config_snapshot.initial_state` exists

### Fix 5: Race Condition
- [ ] Click "Retry" button
- [ ] Immediately click again
- [ ] Verify second request returns 409 Conflict

### Fix 7: Retry Depth
- [ ] Create retry chain (original → retry1 → retry2 → retry3)
- [ ] Try to retry from depth 3
- [ ] Verify error: "Maximum retry depth (3) exceeded"

### Fix 9: Loading States
- [ ] Click "Retry" button
- [ ] Verify: Button disabled, spinner shows, text changes to "Retrying..."

### Fix 10: Breadcrumb
- [ ] View retry run detail page
- [ ] Verify breadcrumb shows: `Original Run #X → Retry #1 → Current`

---

## Database Verification (1 minute)

```bash
# Check retry_depth column
sqlite3 backend/gamed_ai_v2.db "PRAGMA table_info(pipeline_runs);" | grep retry_depth

# Check index
sqlite3 backend/gamed_ai_v2.db ".indices stage_executions" | grep idx_stage_run_status_order

# Check initial_state in config_snapshot
sqlite3 backend/gamed_ai_v2.db "SELECT json_extract(config_snapshot, '$.initial_state.question_id') FROM pipeline_runs LIMIT 1;"
```

---

## Quick Test Checklist

- [ ] Install checkpoint package: `pip install langgraph-checkpoint-sqlite`
- [ ] Run migration: `bash backend/scripts/run_migration.sh`
- [ ] Terminal tests pass: `python scripts/verify_retry_fixes.py`
- [ ] Browser console verification: `verifyRetryFixes.all(runId)`
- [ ] Manual UI checks completed
- [ ] Verify checkpoints saved: Check `checkpoint_id` in stage API responses
- [ ] Test retry: Verify only stages after retry point execute

**Total Time: ~20 minutes**

---

**For detailed verification steps, see**: `/docs/VERIFICATION_GUIDE.md`
