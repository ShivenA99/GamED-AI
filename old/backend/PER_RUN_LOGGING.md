# Per-Run Logging Implementation

## Summary

Implemented per-run logging with runwise directories. Each time the application starts, a new directory is created for that specific run, keeping all logs organized and isolated.

## Implementation Details

### Directory Structure
```
backend/logs/runs/
├── current -> 20251108_143022_a1b2c3d4/  (symlink)
├── current.txt                            (Windows fallback)
├── 20251108_143022_a1b2c3d4/              (Run 1)
│   ├── metadata.json
│   ├── main.log
│   ├── ai_learning_platform.log
│   ├── llm_service.log
│   └── ...
└── 20251108_150145_e5f6g7h8/              (Run 2)
    └── ...
```

### Run ID Format
- Pattern: `YYYYMMDD_HHMMSS_<uuid>`
- Example: `20251108_143022_a1b2c3d4`
- Timestamp ensures chronological ordering
- UUID ensures uniqueness

### Files Created/Modified

1. **`backend/app/utils/logger.py`**
   - Added `initialize_run_logging()` function
   - Added `get_run_id()` and `get_run_dir()` helper functions
   - Modified `setup_logger()` to use run directories
   - Automatic initialization on first logger creation

2. **`backend/app/main.py`**
   - Initialize run logging at startup
   - Log run ID and directory on startup
   - Update metadata on shutdown
   - Added `/api/run-info` endpoint

3. **`backend/scripts/view_current_run.sh`**
   - Bash script to view current run logs
   - Shows metadata and tails main.log

4. **`backend/scripts/view_current_run.py`**
   - Cross-platform Python script
   - Same functionality as bash script

5. **`backend/scripts/list_runs.sh`**
   - Lists all runs with metadata
   - Shows which run is current

6. **`backend/LOGGING.md`**
   - Updated documentation with per-run logging details

## Usage

### View Current Run Logs
```bash
# Bash (Unix/Mac)
./backend/scripts/view_current_run.sh

# Python (Cross-platform)
python backend/scripts/view_current_run.py

# Direct access
tail -f backend/logs/runs/current/main.log
```

### List All Runs
```bash
./backend/scripts/list_runs.sh
```

### Get Run Info via API
```bash
curl http://localhost:8000/api/run-info
```

### Access Specific Run
```bash
# View specific run's logs
tail -f backend/logs/runs/20251108_143022_a1b2c3d4/main.log

# View run metadata
cat backend/logs/runs/20251108_143022_a1b2c3d4/metadata.json
```

## Benefits

1. **Isolation**: Each run's logs are completely separate
2. **Easy Debugging**: Find logs for a specific run instantly
3. **Metadata Tracking**: Know exactly when runs started/ended
4. **Cleanup**: Easy to archive or delete old runs
5. **Comparison**: Compare logs between different runs
6. **No Interference**: Multiple restarts don't mix logs

## Metadata File

Each run directory contains `metadata.json`:
```json
{
  "run_id": "20251108_143022_a1b2c3d4",
  "start_time": "2025-11-08T14:30:22.123456",
  "end_time": "2025-11-08T15:45:10.789012",
  "pid": 12345
}
```

## Automatic Features

- **Auto-initialization**: Run directory created automatically on first logger setup
- **Symlink creation**: `logs/runs/current` points to current run (Unix/Mac)
- **Windows fallback**: `logs/runs/current.txt` contains run ID (Windows)
- **Metadata tracking**: Start time logged on creation, end time on shutdown
- **Component separation**: Each logger writes to its own file in the run directory

## Backward Compatibility

- If run logging fails to initialize, falls back to `logs/` directory
- Existing log viewing scripts still work
- No breaking changes to logging API


