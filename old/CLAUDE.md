# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GamED.AI - An AI-powered gamified learning platform that transforms educational questions into interactive, story-based visualizations using AI. Built with a FastAPI backend and Next.js frontend.

## Commands

### Backend (from `backend/` directory)
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Initialize database manually
python -c "from app.db.database import init_db; init_db()"

# Run database migration
PYTHONPATH=$(pwd) python scripts/migrate_add_blueprint_id.py
```

### Frontend (from `frontend/` directory)
```bash
npm install        # Install dependencies
npm run dev        # Start development server (port 3000)
npm run build      # Production build
npm run lint       # Run ESLint
```

### Full Stack (from project root)
```bash
./start.sh         # Start both backend and frontend
./stop.sh          # Stop both servers
```

## Architecture

### 4-Layer Pipeline System

The backend processes questions through a 9-step pipeline orchestrated by `backend/app/services/pipeline/orchestrator.py`:

1. **Layer 1 - Input** (`layer1_input.py`): Document parsing & question extraction
2. **Layer 2 - Classification** (`layer2_classification.py`, `layer2_template_router.py`): Question analysis & template selection (routes to 1 of 18 game templates)
3. **Layer 3 - Strategy** (`layer3_strategy.py`): Gamification strategy & storyline generation
4. **Layer 4 - Generation** (`layer4_generation.py`): Story, blueprint, and asset generation

### Template System

18 fixed game templates defined in `backend/app/templates/*.json`. The LLM selects the best template based on question analysis. Each template has:
- Backend metadata JSON file
- Story supplement prompt (`backend/prompts/story_templates/`)
- Blueprint TypeScript interface (`backend/prompts/blueprint_templates/`)
- Frontend React component (`frontend/src/components/templates/`)

Template types: `LABEL_DIAGRAM`, `IMAGE_HOTSPOT_QA`, `SEQUENCE_BUILDER`, `TIMELINE_ORDER`, `BUCKET_SORT`, `MATCH_PAIRS`, `MATRIX_MATCH`, `PARAMETER_PLAYGROUND`, `GRAPH_SKETCHER`, `VECTOR_SANDBOX`, `STATE_TRACER_CODE`, `SPOT_THE_MISTAKE`, `CONCEPT_MAP_BUILDER`, `MICRO_SCENARIO_BRANCHING`, `DESIGN_CONSTRAINT_BUILDER`, `PROBABILITY_LAB`, `BEFORE_AFTER_TRANSFORMER`, `GEOMETRY_BUILDER`

### Blueprint System

Games are rendered from structured JSON blueprints (not HTML). Blueprint types defined in `frontend/src/types/gameBlueprint.ts`. The `GameEngine.tsx` component routes blueprints to the appropriate template component.

### State Management

Frontend uses Zustand stores in `frontend/src/stores/`:
- `questionStore.ts` - Question state
- `pipelineStore.ts` - Pipeline execution state
- `errorStore.ts` - Error handling

### Caching

Stories and blueprints are cached in `backend/cache/` using hash-based keys. Cache service in `backend/app/services/cache_service.py`.

### Special Games

Hardcoded HTML games for specific topics (Stack/Queue, BFS) bypass the AI pipeline. Located in `frontend/public/games/` and rendered by `SpecialGameViewer.tsx`.

## Key Files

- `backend/app/main.py` - FastAPI entry point with route registration
- `backend/app/services/llm_service.py` - OpenAI/Anthropic API integration
- `backend/app/services/pipeline/orchestrator.py` - Main pipeline orchestrator
- `frontend/src/components/GameEngine.tsx` - Template router component
- `frontend/src/types/gameBlueprint.ts` - Blueprint TypeScript definitions

## API Endpoints

- `POST /api/upload` - Upload document
- `GET /api/questions/{id}` - Get question
- `POST /api/process/{id}` - Start pipeline processing
- `GET /api/progress/{id}` - Get progress (includes cache indicators)
- `GET /api/visualization/{id}` - Get blueprint or HTML game

## Database

SQLite by default (`ai_learning_platform.db`), PostgreSQL supported via `DATABASE_URL` env var. Models in `backend/app/db/models.py`, repositories in `backend/app/repositories/`.

## Environment Variables

Backend `.env`:
```
OPENAI_API_KEY=...    # or ANTHROPIC_API_KEY
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000
```

Frontend `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
