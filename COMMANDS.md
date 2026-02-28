# Quick Commands Reference

## Project Paths

```bash
# Set these in your shell or add to ~/.zshrc
export GAMED_ROOT="/Users/shivenagarwal/GamifyAssessment"
export GAMED_BACKEND="$GAMED_ROOT/backend"
export GAMED_FRONTEND="$GAMED_ROOT/frontend"
```

---

## Start Services

### Backend (FastAPI)

```bash
cd $GAMED_BACKEND
source venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Next.js)

```bash
cd $GAMED_FRONTEND
npm run dev
```

### Start Both (in separate terminals)

```bash
# Terminal 1 - Backend
cd /Users/shivenagarwal/GamifyAssessment/backend && source venv/bin/activate && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd /Users/shivenagarwal/GamifyAssessment/frontend && npm run dev
```

---

## Stop Services

```bash
# Kill backend (port 8000)
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Kill frontend (port 3000)
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Kill both
lsof -ti:8000,3000 | xargs kill -9 2>/dev/null
```

---

## Pipeline Testing

### Test Single Topology

```bash
cd /Users/shivenagarwal/GamifyAssessment/backend
source venv/bin/activate
PYTHONPATH=. python scripts/test_all_topologies.py --topology T1
```

### Test Multiple Topologies

```bash
cd /Users/shivenagarwal/GamifyAssessment/backend
source venv/bin/activate
PYTHONPATH=. python scripts/test_all_topologies.py --topology T0 --topology T1
```

### Test Label Diagram Pipeline

```bash
cd /Users/shivenagarwal/GamifyAssessment/backend
source venv/bin/activate
PYTHONPATH=. python scripts/test_label_diagram.py
```

### Demo Single Question

```bash
cd /Users/shivenagarwal/GamifyAssessment/backend
source venv/bin/activate
PYTHONPATH=. python scripts/demo_pipeline.py
```

### Test with Visible Logs

```bash
cd /Users/shivenagarwal/GamifyAssessment/backend
source venv/bin/activate
export PYTHONUNBUFFERED=1
PYTHONPATH=. python -u scripts/test_all_topologies.py --topology T1 2>&1 | tee test_output.log
```

---

## Observability API

### List Pipeline Runs

```bash
# Recent 10 runs
curl -s "http://localhost:8000/api/observability/runs?limit=10" | python3 -m json.tool

# Runs for specific process
curl -s "http://localhost:8000/api/observability/runs?process_id=YOUR_PROCESS_ID" | python3 -m json.tool

# Filter by topology
curl -s "http://localhost:8000/api/observability/runs?topology=T1" | python3 -m json.tool
```

### Get Run Details

```bash
# Full run with stages
curl -s "http://localhost:8000/api/observability/runs/{run_id}" | python3 -m json.tool

# Just stages
curl -s "http://localhost:8000/api/observability/runs/{run_id}/stages" | python3 -m json.tool

# Logs for a stage
curl -s "http://localhost:8000/api/observability/runs/{run_id}/logs?stage_id={stage_id}" | python3 -m json.tool
```

### Retry Failed Run

```bash
# Retry from specific stage
curl -X POST "http://localhost:8000/api/observability/runs/{run_id}/retry" \
  -H "Content-Type: application/json" \
  -d '{"from_stage": "blueprint_generator"}'
```

### Analytics

```bash
# Run analytics (last 7 days)
curl -s "http://localhost:8000/api/observability/analytics/runs?days=7" | python3 -m json.tool

# Agent analytics
curl -s "http://localhost:8000/api/observability/analytics/agents?days=7" | python3 -m json.tool
```

---

## Game Generation API

### Generate a Game

```bash
# Start generation
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"question_text": "Label the parts of a plant cell"}'

# Check status
curl -s "http://localhost:8000/api/generate/{process_id}/status" | python3 -m json.tool

# Get result
curl -s "http://localhost:8000/api/generate/{process_id}/result" | python3 -m json.tool
```

### List Games

```bash
curl -s "http://localhost:8000/api/games" | python3 -m json.tool
```

---

## Database Commands

### View SQLite Database

```bash
# List tables
sqlite3 /Users/shivenagarwal/GamifyAssessment/backend/gamed_ai.db ".tables"

# Recent pipeline runs
sqlite3 /Users/shivenagarwal/GamifyAssessment/backend/gamed_ai.db \
  "SELECT id, topology, status, duration_ms, started_at FROM pipeline_runs ORDER BY started_at DESC LIMIT 10;"

# Failed stages
sqlite3 /Users/shivenagarwal/GamifyAssessment/backend/gamed_ai.db \
  "SELECT stage_name, error_message FROM stage_executions WHERE status='failed' ORDER BY started_at DESC LIMIT 5;"

# Total cost by model
sqlite3 /Users/shivenagarwal/GamifyAssessment/backend/gamed_ai.db \
  "SELECT model_id, SUM(estimated_cost_usd) as total_cost FROM stage_executions WHERE model_id IS NOT NULL GROUP BY model_id;"
```

### Reset Database

```bash
rm /Users/shivenagarwal/GamifyAssessment/backend/gamed_ai.db
# Restart backend - tables auto-created
```

---

## Frontend Commands

### Development

```bash
cd /Users/shivenagarwal/GamifyAssessment/frontend
npm run dev          # Start dev server
npm run build        # Production build
npm run lint         # ESLint
npx tsc --noEmit     # TypeScript check
```

### Clean Build

```bash
cd /Users/shivenagarwal/GamifyAssessment/frontend
rm -rf node_modules .next
npm install
npm run dev
```

---

## Backend Commands

### Python Environment

```bash
cd /Users/shivenagarwal/GamifyAssessment/backend

# Activate venv
source venv/bin/activate

# Check which python
which python

# Install new dependency
pip install package-name
pip freeze > requirements.txt
```

### Unit Tests

```bash
cd /Users/shivenagarwal/GamifyAssessment/backend
source venv/bin/activate
PYTHONPATH=. pytest tests/ -v

# Specific test file
PYTHONPATH=. pytest tests/test_agents.py -v

# With coverage
PYTHONPATH=. pytest tests/ --cov=app --cov-report=html
```

### Syntax Check

```bash
cd /Users/shivenagarwal/GamifyAssessment/backend
python3 -m py_compile app/agents/instrumentation.py
```

---

## Service Status

```bash
# Check backend health
curl -s http://localhost:8000/health | python3 -m json.tool

# Check if ports are in use
lsof -i:8000
lsof -i:3000

# View backend API docs
open http://localhost:8000/docs
```

---

## Logs

### Tail Backend Logs

```bash
# If using log file
tail -f /Users/shivenagarwal/GamifyAssessment/backend/logs/app.log

# View recent uvicorn output
# (logs appear in terminal where uvicorn is running)
```

### View Test Output

```bash
tail -f /Users/shivenagarwal/GamifyAssessment/backend/test_output.log
```

---

## Git Commands

```bash
cd /Users/shivenagarwal/GamifyAssessment

# Status
git status

# View recent commits
git log --oneline -10

# Create feature branch
git checkout -b feature/my-feature

# Stage and commit
git add -p  # Interactive staging
git commit -m "feat: description"
```

---

## URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| My Games | http://localhost:3000/games |
| Pipeline Runs | http://localhost:3000/pipeline |
| Run Dashboard | http://localhost:3000/pipeline/runs/{id} |

---

## One-Liners

```bash
# Quick restart backend
lsof -ti:8000 | xargs kill -9 2>/dev/null; cd /Users/shivenagarwal/GamifyAssessment/backend && source venv/bin/activate && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Quick restart frontend
lsof -ti:3000 | xargs kill -9 2>/dev/null; cd /Users/shivenagarwal/GamifyAssessment/frontend && npm run dev

# Generate test game
curl -X POST "http://localhost:8000/api/generate" -H "Content-Type: application/json" -d '{"question_text": "Label the parts of a human heart"}'

# Watch for recent run completions
watch -n 2 'curl -s "http://localhost:8000/api/observability/runs?limit=3" | python3 -c "import sys,json; runs=json.load(sys.stdin)[\"runs\"]; [print(f\"{r[\"id\"][:8]}... {r[\"status\"]} {r.get(\"duration_ms\",\"?\")}ms\") for r in runs]"'
```

---

## Environment Setup

### Required Environment Variables

Create `/Users/shivenagarwal/GamifyAssessment/backend/.env`:

```bash
# LLM API (at least one required)
GROQ_API_KEY=gsk_...          # FREE - recommended
# OPENAI_API_KEY=sk-...       # Paid
# ANTHROPIC_API_KEY=sk-ant-...  # Paid

# Model preset
AGENT_CONFIG_PRESET=groq_free

# Label Diagram (optional)
SERPER_API_KEY=...
USE_IMAGE_DIAGRAMS=true
VLM_MODEL=llava:latest
OLLAMA_BASE_URL=http://localhost:11434
```

### Verify Setup

```bash
cd /Users/shivenagarwal/GamifyAssessment/backend
source venv/bin/activate

# Check imports
PYTHONPATH=. python -c "from app.agents.graph import create_graph; print('OK')"

# Check LLM service
PYTHONPATH=. python -c "from app.services.llm_service import llm_service; print(f'Provider: {llm_service.default_provider}')"
```
