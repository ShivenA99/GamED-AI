# Commands Reference

Complete CLI commands, environment variables, and configuration reference for GamED.AI v2.

---

## Backend Development

```bash
# Navigate and activate virtual environment
cd backend && source venv/bin/activate

# Start backend server (development with hot reload)
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Run all tests
PYTHONPATH=. pytest tests/ -v

# Test specific topology
PYTHONPATH=. python scripts/test_all_topologies.py --topology T1

# Test label diagram pipeline
PYTHONPATH=. python scripts/test_label_diagram.py

# Demo single question
PYTHONPATH=. python scripts/demo_pipeline.py

# Stage-by-stage pipeline test
PYTHONPATH=. python scripts/stage_by_stage_test.py

# Test API providers
PYTHONPATH=. python scripts/test_api_providers.py

# Test Gemini diagram pipeline
PYTHONPATH=. python scripts/test_gemini_diagram_pipeline.py

# Verify agentic implementation
PYTHONPATH=. python scripts/verify_agentic_implementation.py
```

---

## Frontend Development

```bash
cd frontend

# Development server (port 3000)
npm run dev

# Production build
npm run build

# ESLint check
npm run lint

# TypeScript type check
npx tsc --noEmit
```

---

## Service Management

```bash
# Kill processes on ports
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend

# Check which process is using a port
lsof -i:8000
lsof -i:3000

# Check service health
curl http://localhost:8000/health

# View API documentation (Swagger UI)
curl http://localhost:8000/docs
```

---

## Database Management

```bash
# Reset database (tables auto-created on server restart)
rm backend/gamed_ai.db

# View SQLite database tables
sqlite3 backend/gamed_ai.db ".tables"

# View recent pipeline runs
sqlite3 backend/gamed_ai.db "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 5;"

# View all columns in a table
sqlite3 backend/gamed_ai.db ".schema pipeline_runs"
```

---

## Observability Dashboard API

```bash
# List recent pipeline runs
curl "http://localhost:8000/api/observability/runs?limit=10" | python3 -m json.tool

# Get specific run details
curl "http://localhost:8000/api/observability/runs/{run_id}" | python3 -m json.tool

# View run stages
curl "http://localhost:8000/api/observability/runs/{run_id}/stages" | python3 -m json.tool

# Stream run events (SSE)
curl "http://localhost:8000/api/observability/runs/{run_id}/stream"

# Retry from failed stage
curl -X POST "http://localhost:8000/api/observability/runs/{run_id}/retry" \
  -H "Content-Type: application/json" \
  -d '{"from_stage": "blueprint_generator"}'

# List agents
curl "http://localhost:8000/api/observability/agents" | python3 -m json.tool

# Pipeline graph structure
curl "http://localhost:8000/api/pipeline/graph" | python3 -m json.tool

# Compare pipeline runs
curl "http://localhost:8000/api/pipeline/compare?run_ids=id1,id2" | python3 -m json.tool
```

---

## Environment Variables

### Core API Keys (at least one required)

```bash
GROQ_API_KEY=gsk_...     # FREE - recommended for development
OPENAI_API_KEY=sk-...    # Paid
ANTHROPIC_API_KEY=sk-... # Paid
GEMINI_API_KEY=...       # Google Gemini
```

### Model Configuration

```bash
# Preset selection (determines default models for all agents)
AGENT_CONFIG_PRESET=groq_free  # groq_free | cost_optimized | balanced | quality_optimized

# Override model for a specific agent
AGENT_MODEL_<AGENT>=model-id           # e.g., AGENT_MODEL_BLUEPRINT_GENERATOR=gpt-4o
AGENT_TEMPERATURE_<AGENT>=0.7         # e.g., AGENT_TEMPERATURE_GAME_PLANNER=0.8
```

### Pipeline Preset

```bash
# Select pipeline architecture preset
PIPELINE_PRESET=default  # default | label_diagram_hierarchical | advanced_label_diagram | had
```

### Label Diagram Pipeline

```bash
SERPER_API_KEY=...                    # Web/image search (required for diagram image retrieval)
USE_IMAGE_DIAGRAMS=true               # Enable image retrieval pipeline
SAM2_MODEL_PATH=/path/to/sam2.pth     # SAM3 segmentation model path
OLLAMA_BASE_URL=http://localhost:11434 # Ollama server for local VLM
VLM_MODEL=llava:latest                # Vision-language model name
```

### Database

```bash
DATABASE_URL=sqlite:///./gamed_ai.db  # Default SQLite
# PostgreSQL alternative:
# DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### External Services

```bash
# Inpainting
IOPAINT_URL=http://localhost:8080     # IOPaint inpainting server

# Image generation
STABLE_DIFFUSION_URL=...             # Stable Diffusion endpoint
```

---

## Topology Options

Topologies control the validation and refinement strategy applied to the pipeline:

| Topology | Description | Use Case |
|----------|-------------|----------|
| **T0** | Sequential (no validation) | Testing, baseline, fastest |
| **T1** | Sequential + Validators | Production default |
| **T2** | Actor-Critic | Quality-critical generation |
| **T4** | Self-Refine | Iterative improvement loops |
| **T5** | Multi-Agent Debate | Diverse perspectives, highest quality |
| **T7** | Reflection + Memory | Learning from past failures |

Set topology via API request parameter or configuration.

---

## Pipeline Presets

| Preset | Config Key | Graph Function |
|--------|-----------|---------------|
| Default | `default` | `create_game_generation_graph()` |
| Hierarchical | `label_diagram_hierarchical` | `create_preset1_agentic_sequential_graph()` |
| Advanced | `advanced_label_diagram` | `create_preset1_react_graph()` |
| HAD | `had` | `create_had_graph()` |

Preset configuration files: `backend/app/config/presets/`
