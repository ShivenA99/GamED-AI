# Retry from Stage Functionality - Comprehensive Analysis & Verification Plan

## Executive Summary

This document provides a comprehensive analysis of the retry-from-stage functionality, identifying all potential issues, bugs, corner cases, and verification requirements across backend, frontend, and database layers.

---

## Current Implementation Overview

### Backend Flow
1. **Endpoint**: `POST /api/observability/runs/{run_id}/retry`
2. **Request Body**: `{ "from_stage": "stage_name" }`
3. **Validation**:
   - Verifies run exists
   - Verifies stage exists in run
   - Allows retry if: run is `failed`/`cancelled` OR stage is `failed`/`degraded`
4. **Execution**:
   - Creates new `PipelineRun` with `parent_run_id` and `retry_from_stage`
   - Calls `run_retry_pipeline()` in background
   - Reconstructs state from `config_snapshot.initial_state` + successful stage outputs
   - Runs **full graph** from beginning with restored state
   - Agents expected to skip work if outputs already exist

### Frontend Flow
1. **UI**: Retry button in `StagePanel` for failed/degraded stages
2. **API Call**: `POST /api/observability/runs/{run_id}` (Next.js proxy)
3. **Error Handling**: Catches errors and displays in UI
4. **Navigation**: Redirects to new run page on success

### Database Schema
- `PipelineRun`: `parent_run_id`, `retry_from_stage`, `config_snapshot`
- `StageExecution`: `input_snapshot`, `output_snapshot`, `status`

---

## Critical Issues Identified

### 🔴 CRITICAL: Missing Initial State in config_snapshot

**Issue**: `config_snapshot` does NOT store `initial_state` (question_id, question_text, question_options).

**Location**: 
- `backend/app/routes/generate.py:166-171` - Only stores metadata
- `backend/app/routes/observability.py:1027` - Tries to read `config_snapshot.initial_state` which doesn't exist

**Impact**: State reconstruction will fail or produce incomplete state.

**Evidence**:
```python
# generate.py - What's stored
config_snapshot={
    "question_id": question.id,
    "question_text": question_text[:200],  # Truncated!
    "topology": topology,
    "thread_id": process.thread_id
    # NO initial_state!
}

# observability.py - What's expected
state = run.config_snapshot.get("initial_state", {})  # Returns {} - empty!
```

**Fix Required**: Store full `initial_state` in `config_snapshot` when creating pipeline run.

---

### 🔴 CRITICAL: Graph Runs from Beginning, Not from Specific Stage

**Issue**: LangGraph doesn't support starting from a specific node. The retry runs the **entire graph** from `input_enhancer`, relying on agents to skip work.

**Location**: `backend/app/routes/observability.py:982-985`

**Impact**: 
- Inefficient: Re-executes all agents before target stage
- Risk: Agents may not properly skip work, causing duplicate API calls/costs
- No guarantee: Agents may overwrite existing outputs

**Evidence**:
```python
# observability.py:982
# Note: LangGraph doesn't directly support starting from a specific node,
# so we need to implement custom logic here or use checkpointing

# For now, we'll run the full pipeline with the restored state
# The agents should be smart enough to skip work if outputs already exist
graph = get_compiled_graph()
final_state = await graph.ainvoke(restored_state, config)  # Starts from input_enhancer!
```

**Fix Required**: 
- Option A: Use LangGraph checkpointing to resume from specific node
- Option B: Build custom graph that starts from target stage
- Option C: Verify all agents properly skip work when outputs exist

---

### 🟡 HIGH: State Reconstruction Only Uses Successful Stages

**Issue**: `reconstruct_state_before_stage()` only merges outputs from stages with `status == "success"`.

**Location**: `backend/app/routes/observability.py:1030-1033`

**Impact**: 
- If a stage partially succeeded (has output but marked failed), its output is lost
- If a stage before target failed but produced partial output, it's ignored

**Evidence**:
```python
stages = db.query(StageExecution).filter(
    StageExecution.run_id == run_id,
    StageExecution.status == "success"  # Only successful!
).order_by(StageExecution.stage_order).all()
```

**Fix Required**: Consider including stages with partial outputs even if status is not "success".

---

### 🟡 HIGH: No Validation of Required State Keys

**Issue**: No check that all required state keys are present before starting retry.

**Location**: `backend/app/routes/observability.py:960-971`

**Impact**: Retry may fail mid-execution with cryptic errors if required state is missing.

**Fix Required**: Validate state completeness before starting graph execution.

---

### 🟡 HIGH: Race Conditions - Multiple Concurrent Retries

**Issue**: No locking mechanism prevents multiple retries of the same stage simultaneously.

**Location**: `backend/app/routes/observability.py:436-506`

**Impact**: 
- Multiple retry runs created for same stage
- Database inconsistencies
- Wasted resources

**Fix Required**: Add database-level or application-level locking.

---

### 🟡 MEDIUM: Database Transaction Handling

**Issue**: Background task uses separate DB session. If retry fails mid-execution, partial state may be committed.

**Location**: `backend/app/routes/observability.py:951-1007`

**Impact**: Inconsistent database state if retry crashes.

**Fix Required**: Better error handling and rollback mechanisms.

---

### 🟡 MEDIUM: Frontend Doesn't Handle Nested Retries

**Issue**: UI doesn't clearly indicate if retrying a retry (child run of a retry).

**Location**: `frontend/src/app/pipeline/runs/[id]/page.tsx`

**Impact**: User confusion about retry lineage.

**Fix Required**: Display retry chain in UI.

---

### 🟡 MEDIUM: No Verification Agents Skip Work

**Issue**: No test/verification that agents actually skip work when outputs exist.

**Location**: All agent implementations

**Impact**: Duplicate API calls, increased costs, potential overwrites.

**Fix Required**: Add tests or logging to verify skip behavior.

---

### 🟢 LOW: Frontend Error Handling Edge Cases

**Issue**: Some edge cases in error handling:
- Network timeout not handled
- Partial response parsing failures
- Navigation race conditions

**Location**: `frontend/src/app/pipeline/runs/[id]/page.tsx:74-109`

**Fix Required**: More robust error handling.

---

## Corner Cases

### 1. Retry from First Stage (input_enhancer)
- **Scenario**: Retry from very first stage
- **Issue**: No previous stages to reconstruct from
- **Expected**: Should work if `config_snapshot.initial_state` exists (but it doesn't!)
- **Status**: ❌ Will fail

### 2. Retry from Middle Stage with Failed Dependencies
- **Scenario**: Retry from `blueprint_generator` but `game_planner` failed
- **Issue**: Missing required state from `game_plan`
- **Expected**: Should fail gracefully with clear error
- **Status**: ⚠️ May fail with cryptic error

### 3. Retry from Validator Stage
- **Scenario**: Retry from `blueprint_validator` (validator stage)
- **Issue**: Validator doesn't produce outputs, only validation results
- **Expected**: Should retry from previous generator stage
- **Status**: ⚠️ May not work correctly

### 4. Retry While Original Run Still Running
- **Scenario**: User retries a failed stage while original run is still `running`
- **Issue**: Original run may complete and change state
- **Expected**: Should be prevented or handled gracefully
- **Status**: ⚠️ Not prevented

### 5. Retry from Degraded Stage
- **Scenario**: Retry from stage with `status == "degraded"`
- **Issue**: Degraded stage may have partial output
- **Expected**: Should include degraded stage output in reconstruction
- **Status**: ⚠️ May not include degraded outputs

### 6. Retry with Missing config_snapshot
- **Scenario**: Old run without `config_snapshot` (backward compatibility)
- **Issue**: `reconstruct_state_before_stage()` returns empty state
- **Expected**: Should fail gracefully or reconstruct from stages only
- **Status**: ⚠️ May produce incomplete state

### 7. Retry from Stage That Never Executed
- **Scenario**: Retry from stage that was skipped/never ran
- **Issue**: Stage doesn't exist in `StageExecution` table
- **Expected**: Should return 400 error (already handled)
- **Status**: ✅ Handled

### 8. Retry from Successful Stage
- **Scenario**: User tries to retry successful stage
- **Issue**: Should be prevented
- **Expected**: Frontend prevents, backend also validates
- **Status**: ✅ Handled (frontend + backend)

### 9. Concurrent Retries of Same Stage
- **Scenario**: Multiple users/requests retry same stage simultaneously
- **Issue**: Race condition creates multiple retry runs
- **Expected**: Should prevent or queue
- **Status**: ❌ Not prevented

### 10. Retry with Circular Dependencies
- **Scenario**: Retry creates child run, then retry child run from same stage
- **Issue**: Infinite retry chain possible
- **Expected**: Should limit retry depth
- **Status**: ⚠️ No limit

---

## Database Issues

### 1. Foreign Key Constraints
- **Issue**: `parent_run_id` references `pipeline_runs.id` with CASCADE
- **Impact**: Deleting parent run deletes all child retries
- **Status**: ⚠️ May be intentional, but should be documented

### 2. Index Performance
- **Issue**: Queries for `reconstruct_state_before_stage()` may be slow on large runs
- **Location**: `backend/app/routes/observability.py:1030-1033`
- **Fix**: Add index on `(run_id, status, stage_order)`

### 3. JSON Column Size
- **Issue**: `input_snapshot` and `output_snapshot` are JSON columns
- **Impact**: Large snapshots may exceed database limits
- **Status**: ⚠️ Should truncate or compress large snapshots

---

## Frontend Issues

### 1. Loading State During Retry
- **Issue**: No loading indicator while retry request is in flight
- **Location**: `frontend/src/components/pipeline/StagePanel.tsx`
- **Status**: ⚠️ User may click multiple times

### 2. Navigation Timing
- **Issue**: Navigation happens immediately after retry starts, but new run may not be visible yet
- **Location**: `frontend/src/app/pipeline/runs/[id]/page.tsx:86`
- **Status**: ⚠️ May show 404 briefly

### 3. Error Message Display
- **Issue**: Long error messages may overflow UI
- **Location**: `frontend/src/components/pipeline/StagePanel.tsx`
- **Status**: ⚠️ Should truncate or scroll

---

## Verification Plan

### Phase 1: Backend API Verification

#### Test 1.1: Basic Retry Flow
- [ ] Create a failed pipeline run
- [ ] Identify failed stage
- [ ] Call retry API with `from_stage`
- [ ] Verify new run created with `parent_run_id`
- [ ] Verify `retry_from_stage` is set
- [ ] Verify new run executes

#### Test 1.2: State Reconstruction
- [ ] Verify `config_snapshot.initial_state` exists (currently fails)
- [ ] Verify successful stage outputs are merged correctly
- [ ] Verify state keys are complete before graph execution
- [ ] Check for missing required keys

#### Test 1.3: Validation Rules
- [ ] Test retry from failed stage (should work)
- [ ] Test retry from degraded stage (should work)
- [ ] Test retry from successful stage (should fail with 400)
- [ ] Test retry from non-existent stage (should fail with 400)
- [ ] Test retry from non-existent run (should fail with 404)

#### Test 1.4: Edge Cases
- [ ] Retry from first stage (input_enhancer)
- [ ] Retry from validator stage
- [ ] Retry with missing config_snapshot
- [ ] Retry while original run still running
- [ ] Concurrent retries (race condition test)

### Phase 2: Database Verification

#### Test 2.1: Data Integrity
- [ ] Verify `parent_run_id` foreign key works
- [ ] Verify cascade delete behavior (if applicable)
- [ ] Verify `run_number` increments correctly
- [ ] Verify no orphaned runs

#### Test 2.2: State Snapshot Storage
- [ ] Verify `input_snapshot` and `output_snapshot` are stored
- [ ] Verify JSON serialization/deserialization works
- [ ] Test with large snapshots (size limits)
- [ ] Verify snapshot truncation if implemented

#### Test 2.3: Query Performance
- [ ] Test `reconstruct_state_before_stage()` with many stages
- [ ] Check query execution time
- [ ] Verify indexes are used

### Phase 3: Frontend Verification

#### Test 3.1: UI Flow
- [ ] Verify retry button appears for failed/degraded stages
- [ ] Verify retry button hidden for successful stages
- [ ] Test retry confirmation dialog
- [ ] Verify error messages display correctly
- [ ] Verify navigation to new run page

#### Test 3.2: Error Handling
- [ ] Test network timeout
- [ ] Test 400 error (invalid retry)
- [ ] Test 404 error (run not found)
- [ ] Test 500 error (server error)
- [ ] Verify error messages are user-friendly

#### Test 3.3: Edge Cases
- [ ] Test retrying a retry (nested retries)
- [ ] Test rapid clicking (prevent double-submit)
- [ ] Test navigation during retry
- [ ] Test browser back button behavior

### Phase 4: End-to-End Verification

#### Test 4.1: Complete Retry Flow
- [ ] Create pipeline run that fails at specific stage
- [ ] Use UI to retry from failed stage
- [ ] Verify new run executes from correct point
- [ ] Verify final output is correct
- [ ] Verify no duplicate work performed

#### Test 4.2: Agent Skip Behavior
- [ ] Verify agents skip work when outputs exist
- [ ] Check LLM API calls are not duplicated
- [ ] Verify costs are not duplicated
- [ ] Check logs for skip messages

#### Test 4.3: State Completeness
- [ ] Verify all required state keys present after reconstruction
- [ ] Verify state matches original run at retry point
- [ ] Test with complex state (nested objects, arrays)

---

## Recommended Fixes (Priority Order)

### P0 - Critical (Must Fix)
1. **Store `initial_state` in `config_snapshot`** when creating pipeline run
2. **Implement proper state reconstruction** that includes initial state
3. **Add state validation** before graph execution
4. **Add locking mechanism** to prevent concurrent retries

### P1 - High (Should Fix)
5. **Include degraded/partial outputs** in state reconstruction
6. **Add retry depth limit** to prevent infinite chains
7. **Improve error messages** for missing state
8. **Add database indexes** for performance

### P2 - Medium (Nice to Have)
9. **Use LangGraph checkpointing** for proper resume from stage
10. **Add frontend loading states** during retry
11. **Display retry lineage** in UI
12. **Add tests** for agent skip behavior

### P3 - Low (Future)
13. **Compress large snapshots** in database
14. **Add retry queue** for concurrent requests
15. **Add retry analytics** (success rate, common failure points)

---

## Testing Checklist

### Manual Testing
- [ ] Test retry from each stage type (input, routing, generation, validation)
- [ ] Test retry with different failure scenarios
- [ ] Test retry UI with various error conditions
- [ ] Test retry with large state snapshots
- [ ] Test concurrent retries (race conditions)

### Automated Testing
- [ ] Unit tests for `reconstruct_state_before_stage()`
- [ ] Unit tests for retry validation logic
- [ ] Integration tests for retry API endpoint
- [ ] E2E tests for complete retry flow
- [ ] Performance tests for state reconstruction

### Database Testing
- [ ] Test foreign key constraints
- [ ] Test cascade delete behavior
- [ ] Test query performance with indexes
- [ ] Test JSON column size limits

---

## Success Criteria

### Functional
- ✅ Retry creates new run with correct parent relationship
- ✅ State is correctly reconstructed from original run
- ✅ New run executes from correct point
- ✅ No duplicate work is performed
- ✅ Final output is correct

### Non-Functional
- ✅ Retry completes within reasonable time
- ✅ Database queries are performant
- ✅ UI provides clear feedback
- ✅ Errors are handled gracefully
- ✅ No race conditions or data corruption

---

## Next Steps

1. **Immediate**: Fix critical issues (P0)
2. **Short-term**: Implement high-priority fixes (P1)
3. **Medium-term**: Add comprehensive tests
4. **Long-term**: Consider LangGraph checkpointing for proper resume

---

## Appendix: Code Locations

### Backend
- Retry endpoint: `backend/app/routes/observability.py:436-506`
- State reconstruction: `backend/app/routes/observability.py:1010-1042`
- Retry execution: `backend/app/routes/observability.py:936-1007`
- Config snapshot creation: `backend/app/routes/generate.py:166-171`

### Frontend
- Retry handler: `frontend/src/app/pipeline/runs/[id]/page.tsx:74-109`
- API proxy: `frontend/src/app/api/observability/runs/[id]/route.ts:35-67`
- UI component: `frontend/src/components/pipeline/StagePanel.tsx`
- Pipeline view: `frontend/src/components/pipeline/PipelineView.tsx`

### Database
- Models: `backend/app/db/models.py:186-285`
- Schema: `PipelineRun`, `StageExecution`

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-24  
**Author**: AI Assistant  
**Status**: Draft - Pending Verification
