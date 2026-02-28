# Pipeline Flow Analysis & Fixes

## Page Flow

1. **Upload Page** (`/app/page.tsx`)
   - User uploads a file
   - Backend processes and creates a question
   - `questionId` stored in `localStorage`
   - Navigate to `/app/preview`

2. **Preview Page** (`/app/preview/page.tsx`)
   - Fetches question details
   - User reviews question
   - User clicks "Start Interactive Game" button
   - Calls `/api/process/{questionId}` to start pipeline
   - Shows `PipelineProgress` component
   - When complete, shows "Go to Game" button
   - Navigate to `/app/game`

3. **Game Page** (`/app/game/page.tsx`)
   - Fetches visualization using `visualizationId` from `localStorage`
   - Renders the interactive game
   - User plays the game

## Issues Found & Fixed

### 1. **React Strict Mode Double Execution**
**Problem**: React Strict Mode in development causes `useEffect` to run twice, which could trigger duplicate pipeline starts.

**Fix**: 
- Changed `useEffect` dependencies from `[router, setQuestion, setLoading, resetPipeline]` to `[]` (run once on mount)
- Added logic to check for existing processes before resetting state
- Only reset state if no existing process or visualization exists

### 2. **Preview Page Resetting State on Remount**
**Problem**: When navigating back to preview page or component remounting, the `useEffect` would reset all state, including clearing `processId`, which could cause the pipeline to restart.

**Fix**:
- Check for existing `processId` and `visualizationId` before resetting
- If existing process found, preserve state and restore `processing`/`completed` flags
- Only reset if truly a new question (no existing process or visualization)

### 3. **Backend Creating Duplicate Processes**
**Problem**: If the frontend called `/api/process/{questionId}` multiple times (due to double-clicks, remounts, or React Strict Mode), the backend would create multiple processes for the same question.

**Fix**:
- Backend now checks for existing active processes before creating new ones
- If active process exists, returns the existing `process_id` instead of creating a duplicate
- Logs a warning when duplicate calls are detected

### 4. **Frontend Not Handling Existing Processes**
**Problem**: Frontend didn't handle the case where backend returns an existing process.

**Fix**:
- Frontend now checks for `existing: true` flag in response
- If existing process, reuses the `processId` and continues polling
- Logs appropriate messages for debugging

### 5. **Button Not Disabled During Processing**
**Problem**: Button could be clicked multiple times, causing duplicate API calls.

**Fix**:
- Added `disabled={processing}` to button
- Added guard in `handleStartGame` to prevent execution if already processing
- Set `processing` state immediately before API call

## Current Flow (After Fixes)

1. **User uploads question** → `questionId` stored in `localStorage`
2. **Navigate to preview** → `useEffect` runs once:
   - Checks for existing `processId` or `visualizationId`
   - If exists, preserves state (no reset)
   - If not, resets state for new question
   - Fetches question details
3. **User clicks "Start Interactive Game"**:
   - Button immediately disabled
   - Guard prevents duplicate clicks
   - Calls `/api/process/{questionId}`
   - Backend checks for existing active process:
     - If exists → returns existing `process_id`
     - If not → creates new process
   - Frontend sets `processId` and starts polling
4. **Pipeline runs** → Progress shown via `PipelineProgress` component
5. **Pipeline completes** → `visualizationId` stored in `localStorage`
6. **User clicks "Go to Game"** → Navigate to game page
7. **Game page** → Fetches visualization and renders game

## Prevention Mechanisms

1. **Frontend Guards**:
   - Button disabled during processing
   - Guard in `handleStartGame` function
   - State preservation on remount

2. **Backend Guards**:
   - Check for existing active processes
   - Return existing process instead of creating duplicate
   - Logging for debugging

3. **State Management**:
   - Zustand stores for persistent state
   - `localStorage` for cross-page persistence
   - Proper cleanup in `useEffect`

## Testing Recommendations

1. **Test React Strict Mode behavior**:
   - Verify pipeline only runs once even with double execution
   - Check console logs for duplicate detection

2. **Test navigation**:
   - Start pipeline, navigate away, come back
   - Verify pipeline continues (doesn't restart)
   - Verify state is preserved

3. **Test duplicate clicks**:
   - Rapidly click "Start Interactive Game" button
   - Verify only one process is created
   - Verify button is disabled after first click

4. **Test backend restart**:
   - Start pipeline, restart backend
   - Verify frontend handles gracefully
   - Verify no duplicate processes created

## Logging

All key operations are logged with prefixes:
- `[Preview]` - Preview page operations
- `[Start Game]` - Pipeline start operations
- `[PipelineProgress]` - Progress polling
- `[API]` - Backend API operations
- `[Background Task]` - Background pipeline execution

Check console logs and backend logs to track the flow and identify any issues.


