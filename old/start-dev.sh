#!/bin/bash

# Development startup script - Opens separate terminal windows
# For macOS using Terminal.app or iTerm2

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use osascript to open new terminal windows
    echo "Starting backend in new terminal..."
    osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/backend' && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000\""
    
    sleep 2
    
    echo "Starting frontend in new terminal..."
    osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/frontend' && npm run dev\""
    
    echo "✓ Both servers starting in separate terminals"
    echo "Backend: http://localhost:8000"
    echo "Frontend: http://localhost:3000"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - use gnome-terminal or xterm
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "cd '$SCRIPT_DIR/backend' && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; exec bash"
        sleep 2
        gnome-terminal -- bash -c "cd '$SCRIPT_DIR/frontend' && npm run dev; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -e "cd '$SCRIPT_DIR/backend' && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" &
        sleep 2
        xterm -e "cd '$SCRIPT_DIR/frontend' && npm run dev" &
    else
        echo "Please install gnome-terminal or xterm, or use ./start.sh instead"
        exit 1
    fi
else
    echo "Unsupported OS. Please use ./start.sh instead"
    exit 1
fi

