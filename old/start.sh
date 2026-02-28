#!/bin/bash

# Start script for AI Learning Platform
# Runs both backend and frontend servers

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AI Learning Platform - Startup${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if .env file exists for backend
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}Warning: backend/.env file not found${NC}"
    echo -e "${YELLOW}Creating template .env file...${NC}"
    cat > backend/.env << EOF
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000
EOF
    echo -e "${YELLOW}Please edit backend/.env and add your API keys${NC}"
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup SIGINT SIGTERM

# Start Backend
echo -e "\n${GREEN}Starting Backend Server...${NC}"
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing backend dependencies...${NC}"
    pip install -r requirements.txt
fi

# Initialize database if needed
echo -e "${BLUE}Initializing database...${NC}"
python -c "from app.db.database import init_db; init_db(); print('Database ready')" 2>/dev/null || echo -e "${YELLOW}Database already initialized${NC}"

# Run migration if needed
if [ -f "scripts/migrate_add_blueprint_id.py" ]; then
    echo -e "${BLUE}Checking database migration...${NC}"
    PYTHONPATH=$(pwd) python scripts/migrate_add_blueprint_id.py 2>/dev/null || echo -e "${YELLOW}Migration already applied${NC}"
fi

# Start backend server in background
echo -e "${GREEN}Starting backend on http://localhost:8000${NC}"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 3

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Backend failed to start. Check logs/backend.log${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Start Frontend
echo -e "\n${GREEN}Starting Frontend Server...${NC}"
cd ../frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

# Start frontend server in background
echo -e "${GREEN}Starting frontend on http://localhost:3000${NC}"
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait a bit for frontend to start
sleep 5

# Check if frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Frontend failed to start. Check logs/frontend.log${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"

# Create logs directory if it doesn't exist
mkdir -p ../logs

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Both servers are running!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Backend:${NC}  http://localhost:8000"
echo -e "${GREEN}Frontend:${NC} http://localhost:3000"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}\n"

# Tail logs
tail -f ../logs/backend.log ../logs/frontend.log 2>/dev/null || {
    # If tail fails, just wait
    while kill -0 $BACKEND_PID 2>/dev/null && kill -0 $FRONTEND_PID 2>/dev/null; do
        sleep 1
    done
}

