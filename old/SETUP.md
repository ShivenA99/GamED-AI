# Setup Guide - Template-Based Blueprint System

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- OpenAI API key OR Anthropic API key

## Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
```

3. Activate virtual environment:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create `.env` file in backend directory:
```env
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000

# Optional: For PostgreSQL in production
# DATABASE_URL=postgresql://user:password@localhost/dbname
```

6. **Initialize Database**:
```bash
# The database will be automatically initialized on first run, but you can also run:
python -c "from app.db.database import init_db; init_db(); print('Database initialized')"
```

7. **Run Database Migration** (if upgrading from old schema):
```bash
# If you have an existing database without blueprint_id column:
PYTHONPATH=/path/to/backend python scripts/migrate_add_blueprint_id.py
```

8. Run the backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**OR use the startup script** (recommended):
```bash
# From project root
./start.sh
```

This will:
- Check and create `.env` file if needed
- Initialize database
- Run migrations
- Start both backend and frontend servers
- Show logs from both services

## Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local` file (optional, defaults to localhost:8000):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Run the development server:
```bash
npm run dev
```

**OR use the startup script** (recommended):
```bash
# From project root - starts both backend and frontend
./start.sh
```

5. Open http://localhost:3000 in your browser

## Quick Start Scripts

The project includes convenient startup scripts:

### `./start.sh` - Start both servers (Recommended)
- Automatically checks dependencies
- Initializes database if needed
- Runs migrations
- Starts backend and frontend in same terminal
- Shows combined logs
- Press Ctrl+C to stop both

### `./stop.sh` - Stop all servers
- Kills backend and frontend processes
- Cleans up ports 3000 and 8000

### `./start-dev.sh` - Start in separate terminals (macOS/Linux)
- Opens backend in one terminal window
- Opens frontend in another
- Useful for development with separate log views

## Database Schema

The system uses SQLite by default (or PostgreSQL in production). Key tables:

- **questions**: Uploaded questions
- **question_analyses**: Analysis results (type, subject, difficulty, concepts)
- **stories**: Generated story data
- **game_blueprints**: Template-specific game blueprints (NEW)
- **visualizations**: Links to blueprints or HTML content
- **processes**: Pipeline execution tracking
- **pipeline_steps**: Individual step tracking

### Database Migration

If upgrading from an older version, run the migration script:
```bash
cd backend
source venv/bin/activate
PYTHONPATH=$(pwd) python scripts/migrate_add_blueprint_id.py
```

## Template System

The platform now uses **18 fixed game templates**:

1. **LABEL_DIAGRAM** - Diagram labeling with draggable labels
2. **IMAGE_HOTSPOT_QA** - Interactive image with clickable hotspots
3. **SEQUENCE_BUILDER** - Order steps in correct sequence
4. **TIMELINE_ORDER** - Arrange events chronologically
5. **BUCKET_SORT** - Categorize items into buckets
6. **MATCH_PAIRS** - Match related pairs
7. **MATRIX_MATCH** - Match items across dimensions
8. **PARAMETER_PLAYGROUND** - Interactive parameter manipulation
9. **GRAPH_SKETCHER** - Draw and manipulate graphs
10. **VECTOR_SANDBOX** - Vector operations visualization
11. **STATE_TRACER_CODE** - Step through code execution
12. **SPOT_THE_MISTAKE** - Identify errors in code/content
13. **CONCEPT_MAP_BUILDER** - Build concept relationships
14. **MICRO_SCENARIO_BRANCHING** - Interactive branching scenarios
15. **DESIGN_CONSTRAINT_BUILDER** - Design with constraints
16. **PROBABILITY_LAB** - Probability experiments
17. **BEFORE_AFTER_TRANSFORMER** - Visualize transformations
18. **GEOMETRY_BUILDER** - Geometric construction

Each template has:
- Metadata JSON (`backend/app/templates/{TEMPLATE}.json`)
- Story generation supplement (`backend/prompts/story_templates/{TEMPLATE}.txt`)
- TypeScript interface (`backend/prompts/blueprint_templates/{TEMPLATE}.ts.txt`)
- React component (`frontend/src/components/templates/{Template}Game.tsx`)

## Pipeline Architecture

The system uses a **4-layer pipeline** with template routing:

### Layer 1: Input Processing
- Document parsing (PDF, DOCX, TXT)
- Question extraction

### Layer 2: Analysis & Routing
- Question analysis (type, subject, difficulty, concepts)
- **Template routing** (NEW) - Selects appropriate game template

### Layer 3: Strategy
- Gamification strategy creation
- Storyline generation

### Layer 4: Generation
- **Story generation** (template-aware)
- **Blueprint generation** (NEW) - Creates template-specific JSON
- **Asset planning** (NEW) - Identifies required images/assets
- **Asset generation** (NEW) - Generates image URLs (placeholder)

## Usage Flow

1. **Landing Page**: Visit the homepage
2. **Get Started**: Click "Get started" button
3. **Upload**: Upload a PDF, DOCX, or TXT file containing a question
4. **Preview**: Review the extracted question and analysis
5. **Start Game**: Click "Start Interactive Game" to begin processing
6. **Progress**: Watch the progress indicator as the system:
   - Analyzes the question
   - Routes to appropriate template
   - Generates a template-specific story
   - Creates a game blueprint
   - Plans and generates assets
7. **Go to Game**: Click "Go to Game" button when processing completes
8. **Play**: Interact with the template-specific game component
9. **Score**: View your final score and results

## API Endpoints

### Core Endpoints
- `POST /api/upload` - Upload a document
- `GET /api/questions/{question_id}` - Get question details
- `POST /api/process/{question_id}` - Start processing pipeline
- `GET /api/progress/{process_id}` - Get processing progress
- `GET /api/visualization/{visualization_id}` - Get visualization (blueprint or HTML)
- `POST /api/check-answer/{visualization_id}` - Check answer correctness

### Pipeline Endpoints
- `GET /api/pipeline/steps/{process_id}` - Get all steps for a process
- `POST /api/pipeline/retry/{step_id}` - Retry a failed step
- `GET /api/pipeline/history/{question_id}` - Get processing history

### Visualization Endpoints
- `GET /api/visualizations/{visualization_id}` - Get visualization with blueprint support

## Project Structure

```
Claude_Hackathon/
├── backend/
│   ├── app/
│   │   ├── db/
│   │   │   ├── models.py              # Database models (includes GameBlueprint)
│   │   │   ├── database.py            # DB engine & initialization
│   │   │   └── session.py             # Session management
│   │   ├── repositories/
│   │   │   ├── game_blueprint_repository.py  # NEW - Blueprint CRUD
│   │   │   ├── question_repository.py
│   │   │   ├── visualization_repository.py
│   │   │   └── ...
│   │   ├── routes/
│   │   │   ├── generate.py            # Updated for blueprint support
│   │   │   ├── visualizations.py      # NEW - Blueprint endpoints
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── template_registry.py   # NEW - Template metadata loader
│   │   │   ├── pipeline/
│   │   │   │   ├── layer2_template_router.py  # NEW - Template routing
│   │   │   │   ├── layer4_generation.py       # Updated - Blueprint generation
│   │   │   │   ├── orchestrator.py             # Updated pipeline
│   │   │   │   └── ...
│   │   │   └── ...
│   │   ├── templates/                 # NEW - 18 template metadata JSON files
│   │   │   ├── LABEL_DIAGRAM.json
│   │   │   ├── SEQUENCE_BUILDER.json
│   │   │   └── ... (18 total)
│   │   └── ...
│   ├── prompts/
│   │   ├── story_base.md              # Base story generation prompt
│   │   ├── story_templates/           # NEW - 18 template-specific supplements
│   │   │   ├── LABEL_DIAGRAM.txt
│   │   │   └── ... (18 total)
│   │   ├── blueprint_base.md         # NEW - Base blueprint generation prompt
│   │   ├── blueprint_templates/       # NEW - 18 TypeScript interfaces
│   │   │   ├── LABEL_DIAGRAM.ts.txt
│   │   │   └── ... (18 total)
│   │   ├── template_router_system.txt # NEW - Template routing prompt
│   │   └── ...
│   ├── scripts/
│   │   └── migrate_add_blueprint_id.py  # NEW - Database migration
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       │   └── app/
│       │       ├── page.tsx           # Upload page
│       │       ├── preview/page.tsx    # Preview with "Go to Game" button
│       │       └── game/page.tsx       # Game page with GameEngine
│       ├── components/
│       │   ├── GameEngine.tsx         # NEW - Template router component
│       │   └── templates/              # NEW - 18 template game components
│       │       ├── LabelDiagramGame.tsx
│       │       ├── SequenceBuilderGame.tsx
│       │       └── ... (18 total)
│       ├── types/
│       │   └── gameBlueprint.ts       # NEW - TypeScript type definitions
│       └── ...
└── README.md
```

## Troubleshooting

### Backend Issues

**Database Errors:**
- If you see "no such column: visualizations.blueprint_id", run the migration:
  ```bash
  cd backend
  source venv/bin/activate
  PYTHONPATH=$(pwd) python scripts/migrate_add_blueprint_id.py
  ```
- To reset database: Delete `backend/ai_learning_platform.db` and restart server

**Template Loading Errors:**
- Ensure all 18 template JSON files exist in `backend/app/templates/`
- Check that template registry loads on startup (check logs)

**Path Errors:**
- If you see "No such file or directory" for prompts, ensure paths use `.parent.parent.parent.parent` (4 levels up from pipeline services)

**Import Errors:**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` to ensure all dependencies are installed

**API Key Issues:**
- Ensure `.env` file exists in `backend/` directory
- Check that API key is valid
- Server will log which API keys are found on startup

### Frontend Issues

**Build Errors:**
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Fix ESLint errors (unescaped entities, etc.)
- Check TypeScript types match backend schemas

**Runtime Errors:**
- Check that backend is running on port 8000
- Verify Next.js version: `npx next --version`
- Check browser console for API errors

**Game Not Rendering:**
- Ensure visualizationId exists in localStorage
- Check that blueprint data is valid JSON
- Verify GameEngine receives correct blueprint type

### LLM API Issues

- Verify API keys are correct
- Check API rate limits
- Ensure sufficient API credits
- System will try OpenAI first, fallback to Anthropic

## Development Notes

### Adding a New Template

1. Create template metadata: `backend/app/templates/{TEMPLATE}.json`
2. Create story supplement: `backend/prompts/story_templates/{TEMPLATE}.txt`
3. Create TS interface: `backend/prompts/blueprint_templates/{TEMPLATE}.ts.txt`
4. Add to TemplateRegistry.TEMPLATE_TYPES
5. Create React component: `frontend/src/components/templates/{Template}Game.tsx`
6. Add to GameEngine switch statement
7. Add TypeScript interface to `gameBlueprint.ts`

### Database Migrations

For schema changes:
1. Update `backend/app/db/models.py`
2. Create migration script in `backend/scripts/`
3. Run migration before deploying

### Testing

- Test each template with sample questions
- Verify blueprint validation works
- Check that all required HTML contract IDs/classes are present
- Test error handling and retry logic
