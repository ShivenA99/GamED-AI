#!/bin/bash
# View logs from the current run

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
RUNS_DIR="$BACKEND_DIR/logs/runs"

if [ -L "$RUNS_DIR/current" ]; then
    CURRENT_RUN=$(readlink "$RUNS_DIR/current")
    echo "Current run: $CURRENT_RUN"
    echo "Run directory: $RUNS_DIR/$CURRENT_RUN"
    echo ""
    
    # Show metadata
    if [ -f "$RUNS_DIR/$CURRENT_RUN/metadata.json" ]; then
        echo "=== Run Metadata ==="
        cat "$RUNS_DIR/$CURRENT_RUN/metadata.json"
        echo ""
    fi
    
    # Show log files
    echo "=== Log Files ==="
    ls -lh "$RUNS_DIR/$CURRENT_RUN"/*.log 2>/dev/null || echo "No log files found"
    echo ""
    
    # Tail the main log
    if [ -f "$RUNS_DIR/$CURRENT_RUN/main.log" ]; then
        echo "=== Tailing main.log (Ctrl+C to exit) ==="
        tail -f "$RUNS_DIR/$CURRENT_RUN/main.log"
    else
        echo "main.log not found"
    fi
elif [ -f "$RUNS_DIR/current.txt" ]; then
    CURRENT_RUN=$(cat "$RUNS_DIR/current.txt")
    echo "Current run: $CURRENT_RUN"
    echo "Run directory: $RUNS_DIR/$CURRENT_RUN"
    echo ""
    
    if [ -f "$RUNS_DIR/$CURRENT_RUN/main.log" ]; then
        tail -f "$RUNS_DIR/$CURRENT_RUN/main.log"
    else
        echo "main.log not found"
    fi
else
    echo "No current run found. Start the application first."
    exit 1
fi


