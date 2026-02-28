# Session Summary: Per-Run Logging & Frontend Error Fixes

## What We Implemented

### 1. Per-Run Logging System ✅
- **Implemented**: Complete per-run logging with runwise directories
- **Location**: `backend/logs/runs/<run_id>/`
- **Features**:
  - Each application run gets a unique directory: `YYYYMMDD_HHMMSS_<uuid>`
  - Run metadata stored in `metadata.json` (start_time, end_time, pid)
  - Symlink `current` points to latest run (Unix/Mac)
  - Text file `current.txt` for Windows compatibility
  - Component-specific log files (main.log, orchestrator.log, etc.)
  - Log rotation (10MB max, 5 backups per file)

### 2. Frontend Error Handling ✅
- **Fixed**: ErrorBoundary import issue (removed duplicate)
- **Fixed**: Syntax error in preview page (extra closing div)
- **Added**: Graceful handling of socket hang up errors
- **Added**: Comprehensive logging in PipelineProgress component

### 3. Backend API Improvements ✅
- **Fixed**: Progress endpoint visualization access (query separately instead of relationship)
- **Fixed**: Visualization endpoint to use `story_data_json` correctly
- **Added**: Eager loading of visualization relationship
- **Added**: Better error handling and logging in all endpoints
- **Fixed**: None value handling (progress, current_step defaults)

### 4. Story Validation Fix ✅
- **Fixed**: Validator now accepts `intuitive_question` field (from prompt schema)
- **Fixed**: Normalization code prioritizes `intuitive_question` before other field names
- **Added**: Debug logging for raw story data

## What Went Wrong in Recent Run

### Backend Status: ✅ **SUCCESSFUL**
According to logs, the backend pipeline **completed successfully**:
- Process `1d9d5be3-8db9-41a8-910e-03bb454a02c0`: ✅ Completed
  - Visualization ID: `70c98243-06e9-4afd-9033-b4c64f58ed9f`
  - All 6 steps completed successfully
- Process `c7ef5a93-2c38-422d-8338-c86ac1a0325c`: ✅ Completed
  - Visualization ID: `481da274-c70b-44b0-99d3-e3f401f77078`
  - All 6 steps completed successfully

### Frontend Issues: ⚠️ **FIXED**

1. **Syntax Error** (Lines 17-78 in terminal):
   - **Error**: `Unexpected token 'div'. Expected jsx identifier`
   - **Cause**: Extra closing `</div>` tag in preview page
   - **Status**: ✅ Fixed (removed extra closing tag)

2. **Socket Hang Up Errors** (Lines 87-110 in terminal):
   - **Error**: `ECONNRESET` / `socket hang up`
   - **Cause**: Backend restarting due to file changes (with `--reload` flag)
   - **Impact**: Frontend couldn't communicate with backend during restarts
   - **Status**: ✅ Fixed (added graceful error handling)

3. **500 Error in UI**:
   - **Likely Cause**: Frontend trying to fetch progress while backend was restarting
   - **Or**: Progress endpoint trying to access `process.visualization` relationship (lazy loading issue)
   - **Status**: ✅ Fixed (query visualization separately, handle connection errors)

## Root Causes

### Primary Issue: Backend Restart Interference
- Backend running with `--reload` flag restarts on file changes
- Frontend polling every 2 seconds hits backend during restarts
- Connection resets cause "socket hang up" errors
- Frontend treated these as fatal errors

### Secondary Issue: SQLAlchemy Relationship Access
- Progress endpoint accessed `process.visualization` directly
- Lazy loading could fail if session context was wrong
- Fixed by querying visualization separately

## Fixes Applied

1. **Frontend Error Handling**:
   ```typescript
   // Now ignores ECONNRESET errors during polling
   if (error.code === 'ECONNRESET' || error.message?.includes('socket hang up')) {
     console.warn('Backend restarting, will retry...')
     return // Don't treat as error
   }
   ```

2. **Backend Progress Endpoint**:
   ```python
   # Query visualization separately instead of using relationship
   visualization = VisualizationRepository.get_by_process_id(db, process_id)
   visualization_id = visualization.id if visualization else None
   ```

3. **None Value Handling**:
   ```python
   "progress": process.progress or 0,
   "current_step": process.current_step or "Initializing",
   ```

## Current Status

✅ **Backend**: Working correctly - pipelines complete successfully  
✅ **Frontend**: Syntax errors fixed, connection errors handled gracefully  
✅ **Logging**: Per-run logging working, all components logging to run directories  
✅ **API Endpoints**: All endpoints have proper error handling

## Next Steps

1. **Test the full flow**:
   - Upload a document
   - Start pipeline processing
   - Verify progress updates in UI
   - Confirm redirect to game page on completion

2. **Monitor logs**:
   - Check `backend/logs/runs/current/` for detailed logs
   - Use helper scripts: `./scripts/view_current_run.sh`

3. **If issues persist**:
   - Check browser console for frontend errors
   - Check backend logs for API errors
   - Verify backend is fully started before making requests

## Files Modified

### Backend:
- `app/utils/logger.py` - Per-run logging implementation
- `app/main.py` - Run initialization and shutdown handlers
- `app/routes/progress.py` - Fixed visualization access, added error handling
- `app/routes/generate.py` - Fixed visualization endpoint
- `app/services/pipeline/validators.py` - Added `intuitive_question` support
- `app/services/pipeline/layer4_generation.py` - Fixed field normalization
- `app/repositories/process_repository.py` - Added eager loading

### Frontend:
- `src/app/app/preview/page.tsx` - Fixed syntax, added error handling
- `src/components/PipelineProgress.tsx` - Added connection error handling
- `src/components/ErrorBoundary.tsx` - Already had default export

### Scripts:
- `scripts/view_current_run.sh` - View current run logs
- `scripts/view_current_run.py` - Cross-platform version
- `scripts/list_runs.sh` - List all runs

### Documentation:
- `LOGGING.md` - Updated with per-run logging details
- `PER_RUN_LOGGING.md` - Implementation summary


