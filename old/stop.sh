#!/bin/bash

# Stop script for AI Learning Platform
# Kills backend and frontend servers

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping AI Learning Platform servers...${NC}"

# Kill backend (uvicorn)
BACKEND_PIDS=$(pgrep -f "uvicorn app.main:app" || true)
if [ ! -z "$BACKEND_PIDS" ]; then
    echo -e "${GREEN}Stopping backend servers...${NC}"
    echo "$BACKEND_PIDS" | xargs kill 2>/dev/null || true
    sleep 1
    # Force kill if still running
    echo "$BACKEND_PIDS" | xargs kill -9 2>/dev/null || true
fi

# Kill frontend (next dev)
FRONTEND_PIDS=$(pgrep -f "next dev" || true)
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo -e "${GREEN}Stopping frontend servers...${NC}"
    echo "$FRONTEND_PIDS" | xargs kill 2>/dev/null || true
    sleep 1
    # Force kill if still running
    echo "$FRONTEND_PIDS" | xargs kill -9 2>/dev/null || true
fi

# Kill any node processes on port 3000
NODE_PIDS=$(lsof -ti:3000 2>/dev/null || true)
if [ ! -z "$NODE_PIDS" ]; then
    echo -e "${GREEN}Stopping processes on port 3000...${NC}"
    echo "$NODE_PIDS" | xargs kill 2>/dev/null || true
fi

# Kill any python processes on port 8000
PYTHON_PIDS=$(lsof -ti:8000 2>/dev/null || true)
if [ ! -z "$PYTHON_PIDS" ]; then
    echo -e "${GREEN}Stopping processes on port 8000...${NC}"
    echo "$PYTHON_PIDS" | xargs kill 2>/dev/null || true
fi

echo -e "${GREEN}✓ All servers stopped${NC}"

