# Retry Functionality - Research Findings & Solution Options

This document contains research findings and solution options for each identified issue. **Please review and make decisions for each issue** before implementation.

---

## Issue 1: Missing Initial State in config_snapshot

### Problem

`config_snapshot` doesn't store `initial_state`, but retry code expects it at `config_snapshot.initial_state`.

### Research Findings

- State reconstruction requires complete initial state (question_id, question_text, question_options)
- Best practice: Store full state snapshots at critical points for recovery
- PostgreSQL/SQLite can handle JSON columns up to 1GB (with TOAST compression)

### Solution Options

**Option A: Store Full Initial State in config_snapshot** (Recommended)

- **Implementation**: Modify `create_pipeline_run()` to include `initial_state` in `config_snapshot`
- **Pros**: Simple, complete state available for reconstruction
- **Cons**: Slightly larger storage (but JSON is compressed)
- **Code Change**: `backend/app/routes/generate.py:166-171` - Add `initial_state` to snapshot

**Option B: Reconstruct Initial State from Question Table**

- **Implementation**: Query Question table using `question_id` from `config_snapshot`
- **Pros**: No storage overhead
- **Cons**: Requires Question record to exist, adds database query
- **Code Change**: `backend/app/routes/observability.py:1027` - Query Question instead of reading from snapshot

**Option C: Hybrid Approach**

- **Implementation**: Store initial_state in config_snapshot, but fallback to Question table if missing (backward compatibility)
- **Pros**: Works for new and old runs
- **Cons**: More complex logic

### Decision Required

- [X] Option A (Store in config_snapshot)
- [ ] Option B (Query Question table)
- [ ] Option C (Hybrid)
- [ ] Other: _______________

---

## Issue 2: Graph Runs from Beginning (Not from Specific Stage)

### Problem

LangGraph doesn't support starting from a specific node. Retry runs entire graph from `input_enhancer`, relying on agents to skip work.

### Research Findings

- **LangGraph Checkpointing**: LangGraph supports resuming from checkpoints using `checkpoint_id` in config
- **Breakpoints**: Can pause at specific nodes with `interrupt_before`/`interrupt_after`
- **Limitation**: No direct `start_from_node()` API for arbitrary resumption
- **Workaround**: Use conditional edges from START node, or use checkpointing

### Solution Options

**Option A: Use LangGraph Checkpointing** (Recommended for Long-term)

- **Implementation**:
  - Save checkpoint after each stage execution
  - On retry, load checkpoint from before target stage
  - Resume from that checkpoint
- **Pros**: Proper LangGraph way, supports true resume
- **Cons**: Requires checkpoint storage (database or file system), more complex
- **Code Change**:
  - Add checkpointer to graph compilation
  - Save checkpoint after each stage
  - Load checkpoint in retry function

**Option B: Build Custom Graph Starting from Target Stage**

- **Implementation**:
  - Create a subgraph starting from target stage
  - Only include nodes from target stage onward
  - Compile and run this subgraph
- **Pros**: Efficient, only runs needed stages
- **Cons**: Complex graph construction, must maintain graph structure
- **Code Change**: `backend/app/routes/observability.py:982` - Build subgraph dynamically

**Option C: Verify Agent Skip Behavior** (Short-term Fix)

- **Implementation**:
  - Add checks in each agent to skip if output already exists
  - Add logging to verify skip behavior
  - Add tests to ensure no duplicate work
- **Pros**: Quick fix, minimal changes
- **Cons**: Relies on agent discipline, still inefficient
- **Code Change**: Each agent file - Add skip logic

**Option D: Hybrid - Conditional Entry Point**

- **Implementation**:
  - Add conditional edge from START node
  - Check if retry and state is restored
  - Route directly to target stage
- **Pros**: Uses LangGraph features, efficient
- **Cons**: Requires graph modification, complex routing logic
- **Code Change**: `backend/app/agents/graph.py` - Add conditional entry routing

### Decision Required

- [X] Option A (LangGraph Checkpointing - long-term)
- [ ] Option B (Custom Subgraph)
- [ ] Option C (Verify Skip Behavior - short-term)
- [ ] Option D (Conditional Entry Point)
- [ ] Other: _______________

**Note**: Option C can be implemented immediately while planning Option A for future.

---

## Issue 3: State Reconstruction Only Uses Successful Stages

### Problem

Only stages with `status == "success"` are included in state reconstruction. Degraded/partial outputs are ignored.

### Research Findings

- Best practice: Include partial outputs when available, even from failed stages
- State reconstruction should be resilient to partial failures
- Distinguish between "no output" and "partial output"

### Solution Options

**Option A: Include Degraded Stages** (Recommended)

- **Implementation**: Filter stages with `status IN ("success", "degraded")` and check if `output_snapshot` exists
- **Pros**: Captures partial work, more resilient
- **Cons**: May include incomplete data
- **Code Change**: `backend/app/routes/observability.py:1030` - Update filter condition

**Option B: Include Any Stage with Output**

- **Implementation**: Include any stage that has `output_snapshot` regardless of status
- **Pros**: Maximum data preservation
- **Cons**: May include corrupted/incomplete data
- **Code Change**: `backend/app/routes/observability.py:1030` - Check for output_snapshot existence

**Option C: Smart Merging with Validation**

- **Implementation**:
  - Include degraded stages
  - Validate output_snapshot structure before merging
  - Log warnings for incomplete data
- **Pros**: Best of both worlds
- **Cons**: More complex validation logic
- **Code Change**: `backend/app/routes/observability.py:1036-1040` - Add validation before merge

### Decision Required

- [ ] Option A (Include Degraded)
- [ ] Option B (Include Any with Output)
- [X] Option C (Smart Merging)
- [ ] Other: _______________

---

## Issue 4: No Validation of Required State Keys

### Problem

No check that all required state keys are present before starting retry execution.

### Research Findings

- Schema validation best practice: Validate upfront before processing
- Use structured validation with clear error messages
- Distinguish between required and optional fields

### Solution Options

**Option A: Validate Against AgentState TypedDict** (Recommended)

- **Implementation**:
  - Use Pydantic model based on `AgentState` TypedDict
  - Validate required fields (question_id, question_text)
  - Check stage-specific requirements based on target stage
- **Pros**: Type-safe, clear errors
- **Cons**: Must maintain Pydantic model in sync with TypedDict
- **Code Change**:
  - Create Pydantic model for state validation
  - Add validation in `run_retry_pipeline()` before graph execution

**Option B: Stage-Specific Required Keys Map**

- **Implementation**:
  - Define required keys for each stage
  - Check required keys exist before starting
  - Return clear error if missing
- **Pros**: Simple, explicit
- **Cons**: Must maintain map manually
- **Code Change**: `backend/app/routes/observability.py:960` - Add validation function

**Option C: Minimal Validation**

- **Implementation**: Only validate core fields (question_id, question_text)
- **Pros**: Simple, quick
- **Cons**: May miss stage-specific requirements
- **Code Change**: `backend/app/routes/observability.py:960` - Add basic checks

### Decision Required

- [X] Option A (Pydantic Validation)
- [ ] Option B (Required Keys Map)
- [ ] Option C (Minimal Validation)
- [ ] Other: _______________

---

## Issue 5: Race Conditions - Concurrent Retries

### Problem

No locking mechanism prevents multiple concurrent retries of the same stage.

### Research Findings

- **SQLAlchemy SELECT FOR UPDATE**: Use `with_for_update()` to lock rows
- **Pessimistic Locking**: Lock at database level, not just application
- **Lock Duration**: Lock held until transaction commits/rolls back

### Solution Options

**Option A: Database-Level Locking with SELECT FOR UPDATE** (Recommended)

- **Implementation**:
  - Use `with_for_update()` when checking if retry already exists
  - Lock the original run row during retry creation
  - Check for existing retry runs for same stage
- **Pros**: Database-enforced, prevents all race conditions
- **Cons**: Requires transaction management
- **Code Change**: `backend/app/routes/observability.py:450` - Add `with_for_update()` to query

**Option B: Application-Level Flag**

- **Implementation**:
  - Add `retry_in_progress` boolean field to `PipelineRun`
  - Set flag when retry starts, clear when done
  - Check flag before allowing new retry
- **Pros**: Simple, no database locks
- **Cons**: Not atomic, race condition still possible
- **Code Change**:
  - Add field to `PipelineRun` model
  - Check/set flag in retry endpoint

**Option C: Unique Constraint + Retry Count**

- **Implementation**:
  - Add unique constraint on `(parent_run_id, retry_from_stage)`
  - Database prevents duplicate retries
  - Track retry count separately
- **Pros**: Database-enforced uniqueness
- **Cons**: Can't have multiple retries (may be desired for testing)
- **Code Change**:
  - Add unique constraint to database schema
  - Handle IntegrityError in retry endpoint

### Decision Required

- [X] Option A (SELECT FOR UPDATE)
- [ ] Option B (Application Flag)
- [ ] Option C (Unique Constraint)
- [ ] Other: _______________

---

## Issue 6: Database Transaction Handling in Background Tasks

### Problem

Background tasks use separate DB session. If retry fails mid-execution, partial state may be committed.

### Research Findings

- Background tasks need separate database sessions
- Use try/except/finally for proper cleanup
- Commit/rollback explicitly within background task
- Errors in background tasks can't affect HTTP response

### Solution Options

**Option A: Explicit Transaction Management** (Recommended)

- **Implementation**:
  - Wrap entire retry execution in try/except
  - Explicit commit only on success
  - Rollback on any error
  - Update run status in same transaction
- **Pros**: Clear transaction boundaries, safe
- **Cons**: Must be careful with commit timing
- **Code Change**: `backend/app/routes/observability.py:952-1007` - Improve error handling

**Option B: Savepoint/Checkpoint Pattern**

- **Implementation**:
  - Use database savepoints for nested transactions
  - Rollback to savepoint on error
  - Only commit final state
- **Pros**: Fine-grained control
- **Cons**: More complex, database-specific
- **Code Change**: Use SQLAlchemy savepoints

**Option C: Status-Based Recovery**

- **Implementation**:
  - Always update run status atomically
  - Use status to determine if retry is in progress
  - Background job can check status and recover
- **Pros**: Simple, status-driven
- **Cons**: Requires status polling/recovery mechanism
- **Code Change**: Ensure status updates are atomic

### Decision Required

- [X] Option A (Explicit Transactions)
- [ ] Option B (Savepoints)
- [ ] Option C (Status-Based)
- [ ] Other: _______________

---

## Issue 7: Retry Depth Limit

### Problem

No limit on retry depth. Can create infinite retry chains (retry of retry of retry...).

### Research Findings

- Best practice: Set maximum retry limit (typically 3-5)
- Prevent infinite loops
- Distinguish between transient and permanent errors

### Solution Options

**Option A: Count Retry Depth in Database** (Recommended)

- **Implementation**:
  - Add `retry_depth` field to `PipelineRun`
  - Increment depth when creating retry: `retry_depth = parent.retry_depth + 1`
  - Reject retry if `retry_depth >= MAX_RETRY_DEPTH` (e.g., 3)
- **Pros**: Clear tracking, prevents infinite chains
- **Cons**: Requires schema change
- **Code Change**:
  - Add `retry_depth` column to `PipelineRun`
  - Check depth in retry endpoint

**Option B: Count Parent Chain Length**

- **Implementation**:
  - Query parent chain: `parent_run_id -> parent_run_id -> ...`
  - Count chain length
  - Reject if chain length >= MAX_RETRY_DEPTH
- **Pros**: No schema change
- **Cons**: Requires recursive query, slower
- **Code Change**: `backend/app/routes/observability.py:450` - Add chain counting function

**Option C: Time-Based Limit**

- **Implementation**:
  - Reject retry if original run is older than X days
  - Prevents retrying very old runs
- **Pros**: Simple
- **Cons**: Doesn't prevent deep chains, just old retries
- **Code Change**: Check `started_at` timestamp

### Decision Required

- [X] Option A (Retry Depth Field)
- [ ] Option B (Chain Length Query)
- [ ] Option C (Time-Based)
- [ ] Other: _______________

**Also specify**: What should MAX_RETRY_DEPTH be? (Recommended: 3)

---

## Issue 8: Database Performance - Missing Indexes

### Problem

Queries in `reconstruct_state_before_stage()` may be slow on large runs without indexes.

### Research Findings

- Indexes on `(run_id, status, stage_order)` improve query performance
- Composite indexes support filtering and ordering
- SQLAlchemy supports index creation via `Index()` in models

### Solution Options

**Option A: Add Composite Index** (Recommended)

- **Implementation**:
  - Add `Index('idx_stage_run_status_order', StageExecution.run_id, StageExecution.status, StageExecution.stage_order)`
  - Improves `reconstruct_state_before_stage()` query
- **Pros**: Significant performance improvement
- **Cons**: Slight write overhead (minimal)
- **Code Change**: `backend/app/db/models.py:230` - Add Index definition

**Option B: Add Separate Indexes**

- **Implementation**: Add individual indexes on each column
- **Pros**: Simpler
- **Cons**: Less efficient than composite index
- **Code Change**: Add individual indexes

**Option C: No Index (Current)**

- **Implementation**: Keep as-is
- **Pros**: No changes needed
- **Cons**: Performance degrades with large runs
- **Code Change**: None

### Decision Required

- [X] Option A (Composite Index)
- [ ] Option B (Separate Indexes)
- [ ] Option C (No Index)
- [ ] Other: _______________

---

## Issue 9: Frontend Loading States

### Problem

No loading indicator during retry request. User may click multiple times.

### Research Findings

- React best practice: Disable button and show loading state during async operation
- Use `disabled` attribute with loading state
- Reset in `finally` block to ensure re-enable on error

### Solution Options

**Option A: Button Disabled + Loading Spinner** (Recommended)

- **Implementation**:
  - Add `isRetrying` state
  - Set `disabled={isRetrying}` on button
  - Show spinner icon when `isRetrying === true`
  - Reset in `finally` block
- **Pros**: Clear UX, prevents double-clicks
- **Cons**: None significant
- **Code Change**: `frontend/src/components/pipeline/StagePanel.tsx` - Add loading state

**Option B: Disable Only (No Spinner)**

- **Implementation**: Just disable button, no visual indicator
- **Pros**: Simple
- **Cons**: Less clear UX
- **Code Change**: Add `disabled` attribute only

**Option C: Debounce Handler**

- **Implementation**: Use debounce to prevent rapid clicks
- **Pros**: Prevents multiple calls
- **Cons**: Less clear than disabled state
- **Code Change**: Add debounce utility

### Decision Required

- [X] Option A (Disabled + Spinner)
- [ ] Option B (Disabled Only)
- [ ] Option C (Debounce)
- [ ] Other: _______________

---

## Issue 10: Display Retry Lineage in UI

### Problem

UI doesn't clearly show retry chain (parent run, retry depth, etc.).

### Research Findings

- Users need to understand retry relationships
- Breadcrumbs or tree view common patterns
- Show parent run link and retry depth

### Solution Options

**Option A: Breadcrumb Trail** (Recommended)

- **Implementation**:
  - Show: `Original Run → Retry #1 → Retry #2`
  - Each link navigates to that run
  - Show retry depth badge
- **Pros**: Clear navigation, shows chain
- **Cons**: Can get long with deep chains
- **Code Change**: `frontend/src/app/pipeline/runs/[id]/page.tsx` - Add breadcrumb component

**Option B: Sidebar with Retry Tree**

- **Implementation**:
  - Show retry tree in sidebar
  - Expandable tree view
  - Highlight current run
- **Pros**: Visual tree, good for deep chains
- **Cons**: More complex UI
- **Code Change**: Add new component

**Option C: Simple Parent Link**

- **Implementation**: Just show "Retried from Run #X" link
- **Pros**: Simple
- **Cons**: Doesn't show full chain
- **Code Change**: Add parent link (already partially exists)

### Decision Required

- [X] Option A (Breadcrumb Trail)
- [ ] Option B (Retry Tree)
- [ ] Option C (Parent Link)
- [ ] Other: _______________

---

## Issue 11: JSON Column Size Limits

### Problem

Large `input_snapshot`/`output_snapshot` may exceed database limits.

### Research Findings

- PostgreSQL: 1GB limit per JSON column (with TOAST compression)
- SQLite: No explicit limit, but practical limits exist
- Best practice: Truncate or compress large snapshots

### Solution Options

**Option A: Truncate Large Snapshots** (Recommended)

- **Implementation**:
  - Check snapshot size before storing
  - Truncate to max size (e.g., 100KB) if too large
  - Store metadata about truncation
- **Pros**: Prevents database issues
- **Cons**: May lose some data
- **Code Change**: `backend/app/agents/instrumentation.py` - Add truncation in snapshot functions

**Option B: Store in External Storage**

- **Implementation**:
  - Store large snapshots in S3/file system
  - Store reference in database
- **Pros**: No size limits
- **Cons**: More complex, requires external storage
- **Code Change**: Add storage service

**Option C: Compress Snapshots**

- **Implementation**:
  - Compress JSON before storing
  - Decompress when reading
- **Pros**: Reduces size
- **Cons**: Adds compression overhead
- **Code Change**: Add compression/decompression

**Option D: No Action (Current)**

- **Implementation**: Rely on database limits
- **Pros**: No changes
- **Cons**: Risk of hitting limits
- **Code Change**: None

### Decision Required

- [X] Option A (Truncate) max size based on max limit of our db, we can look into local filstores/cloud(production later)
- [ ] Option B (External Storage)
- [ ] Option C (Compress)
- [ ] Option D (No Action)
- [ ] Other: ___

**Also specify**: If Option A, what max size? (Recommended: 100KB per snapshot)

---

## Summary of Decisions Needed

Please review each issue above and make a decision. Once all decisions are made, we'll implement the solutions.

**Priority Order for Implementation:**

1. Issue 1 (Initial State) - CRITICAL
2. Issue 4 (State Validation) - CRITICAL
3. Issue 5 (Race Conditions) - CRITICAL
4. Issue 3 (Degraded Stages) - HIGH
5. Issue 7 (Retry Depth) - HIGH
6. Issue 2 (Graph Execution) - HIGH (can do Option C short-term, Option A long-term)
7. Issue 6 (Transaction Handling) - MEDIUM
8. Issue 8 (Database Indexes) - MEDIUM
9. Issue 9 (Frontend Loading) - MEDIUM
10. Issue 10 (Retry Lineage) - MEDIUM
11. Issue 11 (JSON Size) - LOW

---

**Document Version**: 1.0
**Last Updated**: 2026-01-24
**Status**: Awaiting User Decisions
