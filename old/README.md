# AI-Powered Gamified Learning Platform

Transform educational questions into interactive, story-based visualizations using AI. This platform follows the Brilliant.org design aesthetic and implements a complete template-based blueprint system with 18 game templates, intelligent caching, and special hardcoded games for specific topics.

## 🎯 Features

- **Brilliant.org-Inspired UI**: Modern, clean design with smooth animations
- **Document Upload**: Support for PDF, DOCX, TXT, and Markdown files
- **Template-Based Game System**: 18 fixed game templates automatically selected based on question analysis
- **AI-Powered Processing**: 
  - Question analysis and classification
  - Template routing (selects best game template)
  - Template-aware story generation
  - Blueprint generation (structured JSON, not HTML)
  - Asset planning and generation
- **Intelligent Caching**: Story and blueprint caching for repeated questions to speed up processing
- **Special Games**: Hardcoded HTML games for specific topics (Stack/Queue, BFS) that bypass AI generation
- **Real-time Progress Tracking**: Monitor processing through each pipeline step with visual cache indicators
- **Interactive Games**: Template-specific React components with rich interactions
- **Score Calculation**: Track performance and provide feedback

## 🏗️ Architecture

This application follows a **4-layer pipeline** with template routing:

### Layer 1: Input Processing
- Document parsing (PDF, DOCX, TXT)
- Question extraction

### Layer 2: Analysis & Routing
- Question analysis (type, subject, difficulty, key concepts, intent)
- **Template routing** - LLM selects best template from 18 options

### Layer 3: Strategy
- Gamification strategy creation
- Storyline generation (with caching support)

### Layer 4: Generation
- **Story generation** - Template-aware story with supplements (cached for repeated questions)
- **Blueprint generation** - Creates template-specific JSON blueprint (cached for repeated questions)
- **Asset planning** - Identifies required images/assets
- **Asset generation** - Generates asset URLs (currently placeholder)

### Frontend Rendering
- **GameEngine** - Routes to appropriate template component
- **18 Template Components** - Each implements specific game interactions
- **SpecialGameViewer** - Renders hardcoded HTML games in immersive full-screen mode
- TypeScript type safety with blueprint interfaces

## 🎮 18 Game Templates

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

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** and npm
- **Python 3.9+**
- **OpenAI API key** OR **Anthropic API key**

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment:**
   - **Windows**: `venv\Scripts\activate`
   - **Mac/Linux**: `source venv/bin/activate`

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create `.env` file** in `backend/` directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   # OR
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   
   BACKEND_PORT=8000
   FRONTEND_URL=http://localhost:3000
   
   # Optional: For PostgreSQL in production
   # DATABASE_URL=postgresql://user:password@localhost/dbname
   ```

6. **Initialize Database:**
   ```bash
   # The database will be automatically initialized on first run, but you can also run:
   python -c "from app.db.database import init_db; init_db(); print('Database initialized')"
   ```

7. **Start the backend server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create `.env.local` file** (optional, defaults to localhost:8000):
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

### Using Startup Scripts (Recommended)

**Start both backend and frontend together:**
```bash
# From project root
./start.sh
```

This script will:
- Check and create `.env` file if needed
- Initialize database
- Start both backend and frontend servers
- Show logs from both services

**Stop both servers:**
```bash
./stop.sh
```

## 📁 Repository Structure

```
Claude_Hackathon/
├── frontend/                      # Next.js frontend application
│   ├── src/
│   │   ├── app/                   # Next.js app router pages
│   │   │   ├── page.tsx           # Landing page with search bar
│   │   │   ├── app/
│   │   │   │   ├── page.tsx       # Main app page (question upload)
│   │   │   │   ├── preview/       # Question preview page
│   │   │   │   ├── game/          # Game page (interactive visualization)
│   │   │   │   └── score/         # Score/completion page
│   │   │   ├── layout.tsx         # Root layout
│   │   │   └── globals.css        # Global styles
│   │   ├── components/            # React components
│   │   │   ├── GameEngine.tsx     # Template router component
│   │   │   ├── PipelineProgress.tsx  # Progress bar with cache indicators
│   │   │   ├── SpecialGameViewer.tsx # HTML game viewer
│   │   │   ├── templates/         # 18 game template components
│   │   │   │   ├── ParameterPlaygroundGame.tsx
│   │   │   │   ├── LabelDiagramGame.tsx
│   │   │   │   └── ... (16 more)
│   │   │   └── Header.tsx        # Navigation header
│   │   ├── types/                 # TypeScript definitions
│   │   │   └── gameBlueprint.ts   # Blueprint type definitions
│   │   └── stores/                # Zustand state management
│   │       ├── questionStore.ts   # Question state
│   │       ├── pipelineStore.ts   # Pipeline state
│   │       └── errorStore.ts      # Error state
│   ├── public/
│   │   └── games/                 # Hardcoded HTML games
│   │       ├── stack_que.html     # Stack vs Queue game
│   │       └── bfs_dfs.html      # BFS visualization game
│   ├── package.json
│   └── next.config.js
│
├── backend/                       # FastAPI backend application
│   ├── app/
│   │   ├── main.py                # FastAPI app entry point
│   │   ├── db/                     # Database layer
│   │   │   ├── database.py        # Database initialization
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   └── session.py          # Database session management
│   │   ├── routes/                 # API endpoints
│   │   │   ├── upload.py           # Document upload endpoint
│   │   │   ├── questions.py        # Question CRUD endpoints
│   │   │   ├── analyze.py          # Question analysis endpoint
│   │   │   ├── generate.py         # Pipeline processing endpoint
│   │   │   ├── progress.py         # Progress tracking endpoint
│   │   │   └── visualizations.py   # Visualization retrieval
│   │   ├── services/               # Business logic
│   │   │   ├── llm_service.py      # LLM API integration
│   │   │   ├── cache_service.py    # Story/blueprint caching
│   │   │   ├── document_parser.py  # Document parsing
│   │   │   ├── template_registry.py # Template metadata
│   │   │   └── pipeline/           # Pipeline orchestration
│   │   │       ├── orchestrator.py # Main pipeline orchestrator
│   │   │       ├── steps/          # Individual pipeline steps
│   │   │       └── ...
│   │   ├── repositories/           # Data access layer
│   │   │   ├── question_repository.py
│   │   │   ├── story_repository.py
│   │   │   ├── game_blueprint_repository.py
│   │   │   ├── visualization_repository.py
│   │   │   ├── process_repository.py
│   │   │   └── pipeline_step_repository.py
│   │   ├── templates/              # 18 template metadata JSON files
│   │   │   ├── PARAMETER_PLAYGROUND.json
│   │   │   ├── LABEL_DIAGRAM.json
│   │   │   └── ... (16 more)
│   │   └── utils/
│   │       └── logger.py            # Logging utilities
│   ├── prompts/                    # LLM prompt templates
│   │   ├── story_base.md            # Base story prompt
│   │   ├── story_templates/        # 18 template-specific story supplements
│   │   ├── blueprint_base.md        # Base blueprint prompt
│   │   ├── blueprint_templates/     # 18 TypeScript interfaces for blueprints
│   │   └── template_router_system.txt  # Template selection prompt
│   ├── cache/                       # Cache directory (auto-created)
│   │   └── {hash}_story.json       # Cached story files
│   │   └── {hash}_blueprint.json   # Cached blueprint files
│   ├── logs/                        # Application logs
│   │   └── runs/                   # Per-run logs
│   ├── scripts/                     # Utility scripts
│   │   └── migrate_add_blueprint_id.py
│   ├── requirements.txt             # Python dependencies
│   └── .env                         # Environment variables (create this)
│
├── start.sh                         # Startup script (starts both servers)
├── stop.sh                          # Stop script (kills both servers)
└── README.md                        # This file
```

## 🔄 How It Works

### Normal Question Flow

1. **User uploads a document** (PDF/DOCX/TXT) via the landing page
2. **Question is extracted** and stored in the database
3. **User reviews question** on the preview page
4. **User clicks "Start Interactive Game"**:
   - Backend pipeline starts processing
   - Progress is tracked in real-time
5. **Pipeline executes 9 steps**:
   - Document parsing
   - Question extraction
   - Question analysis
   - Template routing (selects 1 of 18 templates)
   - Strategy creation
   - Story generation (cached if question was seen before)
   - Blueprint generation (cached if question was seen before)
   - Asset planning
   - Asset generation
6. **User navigates to game page** when processing completes
7. **GameEngine routes** to the appropriate template component
8. **User interacts** with the game and answers questions
9. **Score is calculated** and displayed on completion page

### Special Question Flow (Stack/Queue, BFS)

For two hardcoded questions:
- "Demonstrate entry and exit of elements in stacks and queues"
- "Show BFS in graph."

1. **User clicks suggestion button** on landing page
2. **Question is uploaded** normally
3. **User reviews question** on preview page
4. **User clicks "Start Interactive Game"**:
   - **Backend workflow is stopped** (no API call)
   - **200 OK is displayed** in UI
   - **Countdown timer** shows 20 seconds
5. **After 20 seconds**, user is automatically navigated to game page
6. **SpecialGameViewer loads** the corresponding HTML file:
   - `stack_que.html` for Stack/Queue question
   - `bfs_dfs.html` for BFS question
7. **HTML renders** in immersive full-screen mode with proper CSS
8. **User interacts** with the HTML game
9. **On submit**, "Great Page" is shown with trophy and navigation options

### Caching System

The platform implements intelligent caching for AI-generated content:

1. **Cache Key Generation**: Questions are hashed based on text and options
2. **Story Caching**: Generated stories are cached in `backend/cache/{hash}_story.json`
3. **Blueprint Caching**: Generated blueprints are cached in `backend/cache/{hash}_blueprint.json`
4. **Cache Detection**: When a cached item is found:
   - Processing time is significantly reduced
   - Progress bar shows ⚡ "Cached" badge
   - Progress bar color changes to yellow gradient
   - Step duration is shortened (1-2 seconds vs 10-12 seconds)

### Progress Tracking

- **Real-time Updates**: Frontend polls backend every 2 seconds for progress
- **Visual Indicators**: 
  - Green progress bar for normal steps
  - Yellow progress bar with ⚡ badge for cached steps
  - Step names and percentages displayed
- **Error Handling**: Gracefully handles backend restarts and connection errors

## 🛠️ Tech Stack

### Frontend
- **Next.js 14+** (App Router) with TypeScript
- **Tailwind CSS** for styling
- **Framer Motion** for animations
- **Lucide React** for icons
- **Zustand** for state management
- **Axios** for API calls

### Backend
- **FastAPI** (Python) - Modern async web framework
- **SQLAlchemy ORM** - Database abstraction (SQLite by default, PostgreSQL supported)
- **OpenAI/Anthropic** - LLM API integration
- **PyPDF2** and **python-docx** - Document parsing
- **Uvicorn** - ASGI server

## 📡 API Endpoints

### Core Endpoints

- `POST /api/upload` - Upload document (PDF/DOCX/TXT)
- `GET /api/questions/{id}` - Get question details
- `POST /api/process/{id}` - Start processing pipeline
- `GET /api/progress/{id}` - Get progress status (includes cache info)
- `GET /api/visualization/{id}` - Get visualization (returns blueprint or HTML)
- `POST /api/check-answer/{id}` - Check answer correctness

### Pipeline Endpoints

- `GET /api/pipeline/steps/{id}` - Get all steps for a process
- `POST /api/pipeline/retry/{step_id}` - Retry a failed step
- `GET /api/pipeline/history/{question_id}` - Get processing history

## 🗄️ Database Schema

- **questions**: Uploaded questions with text and options
- **question_analyses**: Analysis results (type, subject, difficulty, etc.)
- **stories**: Generated story data with template supplements
- **game_blueprints**: Template-specific game blueprints (JSON)
- **visualizations**: Links to blueprints or HTML content
- **processes**: Pipeline execution tracking
- **pipeline_steps**: Individual step tracking with cache flags

## 🎨 Key Features

### Template System
- 18 fixed game templates with metadata
- Automatic template selection via LLM
- Template-specific story generation
- TypeScript type safety for blueprints

### Blueprint System
- Structured JSON instead of HTML
- Template-specific schemas
- Asset planning and generation
- Validation against TypeScript interfaces

### Caching System
- Hash-based cache keys
- Story and blueprint caching
- Visual cache indicators in UI
- Automatic cache invalidation on question changes

### Special Games
- Hardcoded HTML games for specific topics
- Bypass AI generation for faster loading
- Immersive full-screen rendering
- Proper CSS injection and script execution

### Frontend Components
- GameEngine routes to correct template
- Each template has dedicated React component
- Rich interactions per template type
- Type-safe blueprint handling
- SpecialGameViewer for HTML games

## 🔧 Commands Reference

### Backend Commands

```bash
# Navigate to backend
cd backend

# Activate virtual environment
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Initialize database manually
python -c "from app.db.database import init_db; init_db(); print('Database initialized')"

# Run database migration
PYTHONPATH=$(pwd) python scripts/migrate_add_blueprint_id.py
```

### Frontend Commands

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint
```

### Combined Commands (from project root)

```bash
# Start both backend and frontend
./start.sh

# Stop both servers
./stop.sh
```

## 🌐 Environment Variables

### Backend (`.env` file in `backend/` directory)

```env
# Required: One of these API keys
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Server configuration
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000

# Optional: Database (defaults to SQLite)
# DATABASE_URL=postgresql://user:password@localhost/dbname

# Optional: Logging
LOG_LEVEL=INFO
```

### Frontend (`.env.local` file in `frontend/` directory)

```env
# Optional: Backend API URL (defaults to http://localhost:8000)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📊 User Flow

1. **Landing Page** → View the Brilliant.org-inspired homepage with search bar
2. **Upload Question** → Upload PDF/DOCX/TXT with questions OR use suggestion buttons
3. **Preview** → Review extracted question and analysis
4. **Start Game** → Click "Start Interactive Game" button
5. **Progress** → Watch real-time progress through pipeline:
   - Document parsing
   - Question extraction
   - Question analysis
   - Template routing (selects game template)
   - Strategy creation
   - Story generation (⚡ if cached)
   - Blueprint generation (⚡ if cached)
   - Asset planning
   - Asset generation
6. **Go to Game** → Click button when processing completes (or auto-navigate for special games)
7. **Play** → Interact with template-specific game component or HTML game
8. **Submit** → Answer questions and get feedback
9. **Score** → View results and performance on completion page

## 🐛 Troubleshooting

### Backend Issues

**Database errors:**
```bash
# Reinitialize database
cd backend
python -c "from app.db.database import init_db; init_db(); print('Database initialized')"
```

**Port already in use:**
```bash
# Kill process on port 8000
# Mac/Linux:
lsof -ti:8000 | xargs kill
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Missing dependencies:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Issues

**Port already in use:**
```bash
# Kill process on port 3000
# Mac/Linux:
lsof -ti:3000 | xargs kill
# Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

**Module not found:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Build errors:**
```bash
cd frontend
npm run build
# Check error messages and fix TypeScript/import issues
```

## 📝 Recent Updates

### Caching System
- Implemented intelligent caching for story and blueprint generation
- Cache keys based on question hash
- Visual indicators in progress bar (⚡ badge, yellow color)
- Faster processing for repeated questions

### Special Games
- Added hardcoded HTML games for Stack/Queue and BFS topics
- Bypass backend pipeline for these specific questions
- Immersive full-screen rendering with proper CSS
- Automatic navigation after 20-second countdown

### UI Improvements
- Added "Continue to Great Page" button instead of auto-navigation
- Improved progress bar with cache indicators
- Better error handling and user feedback

## 📄 License

MIT

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📧 Support

For issues, questions, or contributions, please open an issue on the repository.

---

**Built with ❤️ for interactive learning**
