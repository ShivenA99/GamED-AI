# Quick Start Guide - Template-Based Blueprint System

## Backend Setup

1. **Activate virtual environment**:
   ```bash
   cd backend
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies** (if not already done):
   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` file** in `backend/` directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   # OR
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   
   # Optional: For PostgreSQL in production
   # DATABASE_URL=postgresql://user:password@localhost/dbname
   ```

4. **Initialize Database**:
   ```bash
   # Database auto-initializes on first run, but you can manually run:
   python -c "from app.db.database import init_db; init_db(); print('Database initialized')"
   ```

5. **Run Migration** (if upgrading from old version):
   ```bash
   # If you see "no such column: visualizations.blueprint_id" errors:
   PYTHONPATH=$(pwd) python scripts/migrate_add_blueprint_id.py
   ```

6. **Start the server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   **OR use the startup script** (recommended):
   ```bash
   # From project root - starts both backend and frontend
   ./start.sh
   ```

   The database will be automatically initialized on startup (SQLite by default).

## Frontend Setup

1. **Install dependencies** (if not already done):
   ```bash
   cd frontend
   npm install
   ```

2. **Create `.env.local`** (optional, defaults to localhost:8000):
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

   **OR use the startup script** (recommended):
   ```bash
   # From project root - starts both backend and frontend
   ./start.sh
   ```

4. **Open browser**: http://localhost:3000

## Startup Scripts

### Quick Start (Single Terminal)
```bash
./start.sh
```
- Starts both backend and frontend
- Shows combined logs
- Handles all setup automatically

### Development Mode (Separate Terminals)
```bash
./start-dev.sh
```
- Opens backend in one terminal
- Opens frontend in another terminal
- Better for development with separate log views

### Stop Servers
```bash
./stop.sh
```
- Kills all running servers
- Cleans up ports

## What's New - Template Blueprint System

### Template-Based Architecture
- **18 Fixed Templates**: Each question is automatically routed to the best template
- **Template Routing**: LLM analyzes question and selects appropriate template
- **Blueprint Generation**: Creates structured JSON instead of generic HTML
- **Template Components**: Each template has dedicated React component

### New Pipeline Steps
1. **Template Routing** (Layer 2.5) - Selects game template
2. **Template-Aware Story Generation** - Uses template-specific supplements
3. **Blueprint Generation** - Creates template-specific JSON
4. **Asset Planning** - Identifies required images/assets
5. **Asset Generation** - Generates asset URLs

### Database Changes
- **GameBlueprint Model**: Stores template-specific blueprints
- **Visualization.blueprint_id**: Links visualizations to blueprints
- **Migration Required**: Run migration script if upgrading

### Frontend Changes
- **GameEngine Component**: Routes to correct template component
- **18 Template Components**: Each implements specific interactions
- **TypeScript Types**: Full type safety for all blueprints
- **Manual Navigation**: "Go to Game" button instead of auto-redirect

## Template System Overview

### Template Files Structure
Each of the 18 templates has:
- **Metadata JSON**: `backend/app/templates/{TEMPLATE}.json`
  - Description, domains, required fields, HTML contract
- **Story Supplement**: `backend/prompts/story_templates/{TEMPLATE}.txt`
  - Template-specific guidance for story generation
- **TypeScript Interface**: `backend/prompts/blueprint_templates/{TEMPLATE}.ts.txt`
  - Exact schema for blueprint generation
- **React Component**: `frontend/src/components/templates/{Template}Game.tsx`
  - Interactive game implementation

### Template Selection
The system automatically:
1. Analyzes question (type, subject, difficulty, concepts, intent)
2. Routes to best template using LLM
3. Generates template-specific story
4. Creates blueprint matching template schema
5. Renders with appropriate React component

## API Endpoints

### Core Endpoints
- `POST /api/upload` - Upload document
- `GET /api/questions/{id}` - Get question details
- `POST /api/process/{id}` - Start processing pipeline
- `GET /api/progress/{id}` - Get processing progress
- `GET /api/visualization/{id}` - Get visualization (blueprint or HTML)

### New Endpoints
- `GET /api/visualizations/{id}` - Get visualization with blueprint support
- `GET /api/pipeline/steps/{process_id}` - Get all steps for a process
- `POST /api/pipeline/retry/{step_id}` - Retry a failed step
- `GET /api/pipeline/history/{question_id}` - Get processing history

## Troubleshooting

### Database Issues
- **"no such column: visualizations.blueprint_id"**: Run migration script
  ```bash
  cd backend
  source venv/bin/activate
  PYTHONPATH=$(pwd) python scripts/migrate_add_blueprint_id.py
  ```
- **Database not found**: Delete `backend/ai_learning_platform.db` and restart (will auto-create)
- **SQLite foreign keys**: Automatically enabled via event listener

### Template Loading Issues
- **"Template not found"**: Ensure all 18 JSON files exist in `backend/app/templates/`
- **"Failed to load prompt"**: Check file paths (should be 4 levels up from pipeline services)
- **Template registry empty**: Check logs for template loading errors

### Path Errors
- **"No such file or directory: prompts/..."**: 
  - Ensure paths use `.parent.parent.parent.parent` (4 levels)
  - Check that prompt files exist in `backend/prompts/`

### Frontend Build Errors
- **TypeScript errors**: Run `npm run build` to see all errors
- **ESLint errors**: Fix unescaped entities (`'` → `&apos;`)
- **Missing types**: Ensure `gameBlueprint.ts` has all template interfaces

### Import Errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` to ensure all dependencies are installed
- Check Python path for migration scripts: `PYTHONPATH=$(pwd)`

### API Key Issues
- Ensure `.env` file exists in `backend/` directory
- Check that API key is valid
- Server will log which API keys are found on startup
- System tries OpenAI first, falls back to Anthropic

### Game Not Rendering
- Check browser console for errors
- Verify `visualizationId` exists in localStorage
- Ensure blueprint data is valid JSON
- Check that GameEngine receives correct `templateType`

## Development Workflow

### Testing a New Question
1. Upload document via frontend
2. Review question on preview page
3. Click "Start Interactive Game"
4. Watch progress through pipeline steps
5. Click "Go to Game" when complete
6. Interact with template-specific game

### Debugging Pipeline
- Check backend logs for each step
- Use `/api/pipeline/steps/{process_id}` to see step details
- Retry failed steps via `/api/pipeline/retry/{step_id}`
- Check database for stored blueprints

### Adding Template Support
See [SETUP.md](./SETUP.md) for detailed instructions on adding new templates.

## Key Differences from Old System

| Old System | New System |
|------------|------------|
| Generic HTML generation | Template-specific blueprints |
| Single visualization type | 18 template types |
| HTML stored in database | JSON blueprints stored |
| Static HTML rendering | Interactive React components |
| Manual template selection | Automatic LLM routing |
| No asset system | Asset planning & generation |

## Next Steps

1. **Complete Template Components**: Many templates are placeholders - implement full interactions
2. **Asset Generation**: Integrate actual image generation API (currently placeholder URLs)
3. **Task System**: Implement task display and evaluation across all templates
4. **Feedback System**: Add comprehensive feedback for all interactions
5. **Path Tracking**: Implement for MICRO_SCENARIO_BRANCHING and similar path-based templates
