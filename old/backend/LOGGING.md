# Backend Logging Guide

## Overview

The backend uses a comprehensive logging system with **per-run directory structure** that writes detailed logs to files for debugging purposes. Each time the application starts, a new run directory is created with a unique identifier, making it easy to track and debug specific application runs.

### Key Features
- **Per-run directories**: Each application run gets its own directory
- **Run metadata**: Each run includes metadata (start time, end time, PID)
- **Easy access**: Symlink/text file points to current run
- **Component separation**: Each logger writes to its own log file
- **Log rotation**: Individual log files rotate at 10MB with 5 backups

## Log File Location

Logs are stored in a **per-run directory structure** under `backend/logs/runs/`:

### Directory Structure
```
backend/logs/
├── runs/
│   ├── current -> 20251108_143022_a1b2c3d4/  (symlink to current run)
│   ├── current.txt                          (fallback for Windows)
│   ├── 20251108_143022_a1b2c3d4/            (run directory)
│   │   ├── metadata.json                    (run metadata)
│   │   ├── main.log                         (main application logs)
│   │   ├── ai_learning_platform.log       (platform logs)
│   │   ├── llm_service.log                 (LLM service logs)
│   │   └── ...                              (other component logs)
│   ├── 20251108_150145_e5f6g7h8/            (previous run)
│   └── ...
```

### Run Directory Naming
Each run directory is named with the pattern: `YYYYMMDD_HHMMSS_<uuid>`
- `YYYYMMDD_HHMMSS` - Timestamp when the run started
- `<uuid>` - Short UUID (8 chars) for uniqueness

### Run Metadata
Each run directory contains a `metadata.json` file with:
- `run_id`: Unique identifier for this run
- `start_time`: ISO timestamp when the run started
- `end_time`: ISO timestamp when the run ended (added on shutdown)
- `pid`: Process ID of the application

### Current Run Access
- **Symlink**: `logs/runs/current` points to the current run directory (Unix/Mac)
- **Text file**: `logs/runs/current.txt` contains the current run ID (Windows fallback)

## Log Levels

- **DEBUG**: Detailed information for debugging (function names, line numbers, data previews)
- **INFO**: General informational messages (API calls, pipeline steps, successful operations)
- **WARNING**: Warning messages (fallbacks, non-critical issues)
- **ERROR**: Error messages with full stack traces

## What Gets Logged

### API Endpoints
- All API requests and responses
- Request parameters and IDs
- Error details with stack traces

### Pipeline Processing
- Each step of the pipeline (Analysis → Story → HTML → Storage)
- Progress updates
- LLM API calls (OpenAI/Anthropic)
- Full request/response data
- Error details at each step

### LLM Service
- API calls to OpenAI/Anthropic
- Request details (model, temperature, message count)
- Response previews (first 500 chars)
- Token usage information
- Fallback attempts (OpenAI → Anthropic or vice versa)
- JSON parsing attempts and failures

### Document Parsing
- File uploads (filename, size, type)
- Parsing progress (pages, paragraphs)
- Extracted question and options
- Parsing errors

### Question Analysis
- Question text and options
- Analysis results (type, subject, difficulty)
- Full analysis JSON

### Story Generation
- Story generation requests
- Story data (title, context, question flow)
- Full story JSON

### HTML Generation
- HTML generation requests
- Generated HTML length and preview
- HTML extraction from code blocks

## Log Format

Each log entry includes:
```
YYYY-MM-DD HH:MM:SS | LEVEL     | logger_name | function:line | message
```

Example:
```
2025-01-08 14:23:45 | INFO      | llm_service | analyze_question:159 | Attempting question analysis with OpenAI...
2025-01-08 14:23:46 | DEBUG     | llm_service | _call_openai:52 | OpenAI Request - Messages count: 2
2025-01-08 14:23:47 | INFO      | llm_service | _call_openai:64 | OpenAI API call successful - Response length: 234 chars
```

## Viewing Logs

### View Current Run Logs
```bash
# Use the helper script (recommended)
cd backend
./scripts/view_current_run.sh

# Or manually access current run
tail -f logs/runs/current/main.log

# View run metadata
cat logs/runs/current/metadata.json
```

### Real-time Monitoring
```bash
# Watch current run logs in real-time (Linux/Mac)
tail -f backend/logs/runs/current/main.log

# Watch specific component logs
tail -f backend/logs/runs/current/llm_service.log
tail -f backend/logs/runs/current/orchestrator.log

# Windows PowerShell
Get-Content backend\logs\runs\current\main.log -Wait -Tail 50
```

### Search Current Run Logs
```bash
# Find all errors in current run
grep "ERROR" backend/logs/runs/current/*.log

# Find specific process ID
grep "process_id=abc123" backend/logs/runs/current/*.log

# Find all OpenAI calls
grep "OpenAI" backend/logs/runs/current/*.log
```

### Search All Runs
```bash
# Find errors across all runs
grep -r "ERROR" backend/logs/runs/*/

# Find specific process ID across all runs
grep -r "process_id=abc123" backend/logs/runs/*/

# List all runs
ls -la backend/logs/runs/
```

### Filter by Component
```bash
# LLM service logs (current run)
grep "llm_service" backend/logs/runs/current/*.log

# Pipeline logs (current run)
grep "PIPELINE" backend/logs/runs/current/*.log

# API endpoint logs (current run)
grep "\[API\]" backend/logs/runs/current/*.log
```

### Access Specific Run
```bash
# View a specific run's logs
tail -f backend/logs/runs/20251108_143022_a1b2c3d4/main.log

# View run metadata
cat backend/logs/runs/20251108_143022_a1b2c3d4/metadata.json
```

## Debugging Workflow

1. **Start the backend server** - A new run directory is created automatically
2. **Note the Run ID** - Check startup logs or `logs/runs/current/metadata.json`
3. **Reproduce the issue** - All actions are logged to the current run directory
4. **Check the log files** - Look for ERROR or WARNING entries in `logs/runs/current/`
5. **Follow the process ID** - Each pipeline run has a unique process_id
6. **Check LLM responses** - Full API responses are logged at DEBUG level
7. **Review run metadata** - Check `metadata.json` for run timing information

## Example Log Search Patterns

### Find a specific error:
```bash
grep -A 10 "PIPELINE ERROR" backend/logs/app_*.log
```

### Track a specific question processing:
```bash
grep "question_id=your-question-id" backend/logs/app_*.log
```

### See all API calls:
```bash
grep "Calling.*API" backend/logs/app_*.log
```

### Find fallback attempts:
```bash
grep "Falling back" backend/logs/app_*.log
```

## Log File Rotation

Each run creates its own directory. Log files within each run directory use rotation (10MB max, 5 backups per file).

### Cleanup Old Runs
```bash
# List all runs
ls -la backend/logs/runs/

# Remove runs older than 7 days
find backend/logs/runs -type d -name "20*" -mtime +7 -exec rm -rf {} \;

# Keep only last 10 runs
cd backend/logs/runs
ls -t | tail -n +11 | xargs rm -rf
```

### Archive Runs
```bash
# Archive a specific run
tar -czf run_20251108_143022.tar.gz backend/logs/runs/20251108_143022_a1b2c3d4/

# Archive all runs older than 30 days
find backend/logs/runs -type d -name "20*" -mtime +30 -exec tar -czf {}.tar.gz {} \;
```

## Log File Size

Log files can grow large with DEBUG level logging. To reduce size:
- Set log level to INFO in production
- Rotate logs daily
- Archive old logs

## Troubleshooting

### No logs appearing?
- Check that `backend/logs/` directory exists
- Verify file permissions
- Check that logger is initialized in main.py

### Too much logging?
- Adjust log levels in `backend/app/utils/logger.py`
- Change `logger.setLevel(logging.DEBUG)` to `logging.INFO`

### Need more detail?
- Ensure DEBUG level is enabled
- Check that `exc_info=True` is used in error logs

## Helper Scripts

### View Current Run
```bash
# Bash script (Unix/Mac)
cd backend
./scripts/view_current_run.sh

# Python script (Cross-platform)
cd backend
python scripts/view_current_run.py
```

### List All Runs
```bash
cd backend
./scripts/list_runs.sh
```

### Get Run Info via API
```bash
curl http://localhost:8000/api/run-info
```

## Benefits of Per-Run Logging

1. **Isolation**: Each run's logs are completely separate
2. **Easy Debugging**: Find logs for a specific run without searching through daily files
3. **Metadata Tracking**: Know exactly when each run started and ended
4. **Cleanup**: Easy to archive or delete old runs
5. **Comparison**: Compare logs between different runs
6. **No Interference**: Multiple restarts don't mix logs together
