#!/bin/bash
# List all runs with their metadata

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
RUNS_DIR="$BACKEND_DIR/logs/runs"

echo "=== All Runs ==="
echo ""

if [ ! -d "$RUNS_DIR" ]; then
    echo "No runs directory found. Start the application first."
    exit 1
fi

# Get current run ID
CURRENT_RUN=""
if [ -L "$RUNS_DIR/current" ]; then
    CURRENT_RUN=$(readlink "$RUNS_DIR/current")
elif [ -f "$RUNS_DIR/current.txt" ]; then
    CURRENT_RUN=$(cat "$RUNS_DIR/current.txt")
fi

# List all run directories
for run_dir in "$RUNS_DIR"/20*; do
    if [ -d "$run_dir" ]; then
        run_name=$(basename "$run_dir")
        is_current=""
        if [ "$run_name" = "$CURRENT_RUN" ]; then
            is_current=" (CURRENT)"
        fi
        
        echo "Run: $run_name$is_current"
        
        # Show metadata if available
        if [ -f "$run_dir/metadata.json" ]; then
            echo "  Start: $(jq -r '.start_time // "N/A"' "$run_dir/metadata.json" 2>/dev/null || echo "N/A")"
            echo "  End:   $(jq -r '.end_time // "Running..."' "$run_dir/metadata.json" 2>/dev/null || echo "N/A")"
            echo "  PID:   $(jq -r '.pid // "N/A"' "$run_dir/metadata.json" 2>/dev/null || echo "N/A")"
        fi
        
        # Show log files
        log_count=$(find "$run_dir" -name "*.log" 2>/dev/null | wc -l | tr -d ' ')
        echo "  Log files: $log_count"
        echo ""
    fi
done


