# GamED.AI v2

**AI-powered educational game generation platform** using a multi-agent LangGraph architecture with plug-and-play model configuration and human-in-the-loop verification.

## Features

- **Multi-Agent Pipeline**: 14+ specialized agents for game generation
- **Label Diagram Pipeline**: Advanced diagram labeling with web search, image segmentation (SAM2/SAM), and VLM-based zone labeling
- **Multiple Topologies**: T0 (sequential) to T7 (reflection+memory) configurations
- **Plug-and-Play Models**: Easy switching between OpenAI, Anthropic, and Groq (FREE!)
- **Quality Assurance**: Schema, semantic, and pedagogical validation with retry logic
- **Human-in-the-Loop**: Admin dashboard for reviewing low-confidence decisions
- **18 Game Templates**: From simple matching to complex algorithm visualizations
- **Interactive Frontend**: Drag-and-drop game player with scoring and hints

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/shivena99/GamifyAssessment.git
cd GamifyAssessment

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

### 2. Configure API Keys

Create `backend/.env`:

```bash
# RECOMMENDED: Groq (FREE - 14,400 requests/day!)
# Sign up at: https://console.groq.com
GROQ_API_KEY=gsk_your-groq-key-here
AGENT_CONFIG_PRESET=groq_free

# OR use paid APIs:
# OPENAI_API_KEY=sk-your-openai-key
# ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
# AGENT_CONFIG_PRESET=balanced

# Web search for domain knowledge (free tier via Serper)
SERPER_API_KEY=your-serper-key

# Diagram image pipeline (optional)
USE_IMAGE_DIAGRAMS=true
SAM_MODEL_PATH=/path/to/sam_vit_b.pth
VLM_MODEL=llava:latest
```

### 3. Run the Backend

```bash
cd backend
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

### 4. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser to access:
- **Home page**: Generate new games
- **My Games** (`/games`): View all games with pipeline run history
- **Pipeline Runs** (`/pipeline/runs/{id}`): Detailed agent execution view with React Flow graph

### 5. Test the API

```bash
# Generate a game
curl -X POST "http://localhost:8000/api/generate?question_text=Explain%20binary%20search"

# Check status
curl "http://localhost:8000/api/generate/{process_id}/status"
```

## Architecture

### Agent Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GamED.AI v2 Agent Pipeline                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Question  ──►  InputEnhancer  ──►  DomainKnowledgeRetriever              │
│                  (Bloom's, subject)  (web search for labels)               │
│                         │                                                   │
│                         ▼                                                   │
│                      Router  ───────────────────────────────────────┐      │
│                    (template)                                        │      │
│                         │                                            │      │
│              ┌──────────┴──────────┐                                │      │
│              │                     │                                │      │
│        LABEL_DIAGRAM          Other Templates                       │      │
│              │                     │                                │      │
│              ▼                     │                                │      │
│   DiagramImageRetriever            │      (confidence < 0.7)        │      │
│   (Serper Images API)              │             ▼                  │      │
│              │                     │        HumanReview ◄───────────┤      │
│              ▼                     │             │                  │      │
│   DiagramImageSegmenter            │             │                  │      │
│   (SAM2/SAM → zones)               │             │                  │      │
│              │                     │             │                  │      │
│              ▼                     │             │                  │      │
│   DiagramZoneLabeler               │             │                  │      │
│   (VLM/LLaVA)                      │             │                  │      │
│              │                     │             │                  │      │
│              └──────────┬──────────┘             │                  │      │
│                         ▼                        │                  │      │
│                    GamePlanner  ◄────────────────┘                  │      │
│                    (mechanics)                                      │      │
│                         │                                           │      │
│                         ▼                                           │      │
│   SceneGenerator  ──►  BlueprintGenerator  ──►  BlueprintValidator ┘      │
│   (visual design)      (JSON blueprint)        (retry loop, max 3)        │
│                                                      │                      │
│                                                      ▼                      │
│                           DiagramSpecGenerator ──► DiagramSpecValidator    │
│                           (SVG spec)               (retry loop, max 3)     │
│                                                      │                      │
│                                                      ▼                      │
│                           DiagramSvgGenerator  ──►  AssetGenerator         │
│                           (renders SVG)             (images/audio)         │
│                                                      │                      │
│                                                      ▼                      │
│                                                   OUTPUT                    │
│                                                   (Game!)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Agents

| Agent | Purpose | Default Model |
|-------|---------|---------------|
| **InputEnhancer** | Extracts Bloom's level, subject, difficulty, concepts | claude-sonnet |
| **DomainKnowledgeRetriever** | Web search for canonical labels (Serper API) | - |
| **Router** | Selects optimal game template with confidence score | claude-haiku |
| **GamePlanner** | Generates game mechanics, scoring rubric, difficulty | gpt-4-turbo |
| **SceneGenerator** | Plans visual design and interactions | claude-sonnet |
| **BlueprintGenerator** | Produces template-specific JSON blueprint | gpt-4o |
| **BlueprintValidator** | Schema + Semantic + Pedagogical validation | claude-haiku |
| **CodeGenerator** | Generates React components (stub templates) | gpt-4o |
| **AssetGenerator** | AI image/audio generation | - |

### Label Diagram Agents

| Agent | Purpose | Technology |
|-------|---------|------------|
| **DiagramImageRetriever** | Searches for diagram images online | Serper Images API |
| **DiagramImageSegmenter** | Segments image into labeled zones | SAM2 / SAM / Grid fallback |
| **DiagramZoneLabeler** | Identifies labels for each zone | VLM (Ollama + LLaVA) |
| **DiagramSpecGenerator** | Generates SVG specification from blueprint | LLM + Pydantic schema |
| **DiagramSpecValidator** | Validates SVG spec before rendering | Schema validation |
| **DiagramSvgGenerator** | Renders interactive SVG from spec | SVG XML generation |

### Topology Configurations

| Topology | Description | Best For |
|----------|-------------|----------|
| **T0** | Sequential (no validation) | Testing, baseline |
| **T1** | Sequential + Validators | Production default |
| **T2** | Actor-Critic | Quality-critical tasks |
| **T4** | Self-Refine | Iterative improvement |
| **T5** | Multi-Agent Debate | Diverse perspectives |
| **T7** | Reflection + Memory | Learning from failures |

## Model Configuration

### Presets

| Preset | Cost | Models Used |
|--------|------|-------------|
| `groq_free` | **$0** | Llama 3.3 70B (Groq free tier) |
| `cost_optimized` | ~$0.01-0.02/run | claude-haiku, gpt-4o-mini |
| `balanced` | ~$0.05-0.10/run | claude-sonnet, gpt-4-turbo |
| `quality_optimized` | ~$0.20-0.50/run | claude-opus, gpt-4o |
| `anthropic_only` | varies | Claude models only |
| `openai_only` | varies | GPT models only |

### Per-Agent Override

```bash
# Override specific agents
AGENT_MODEL_BLUEPRINT_GENERATOR=gpt-4o
AGENT_MODEL_STORY_GENERATOR=claude-opus
AGENT_TEMPERATURE_STORY_GENERATOR=0.9
```

## API Reference

### Game Generation

```bash
# Start generation
POST /api/generate?question_text=...&question_options=...

# Response: { "process_id": "...", "question_id": "...", "status": "started" }

# Check status
GET /api/generate/{process_id}/status

# Response: { "status": "completed", "progress_percent": 100, ... }

# Resume after human review
POST /api/generate/{process_id}/resume
```

### Questions

```bash
# List questions
GET /api/questions

# Get question details
GET /api/questions/{id}

# Upload document (extract questions)
POST /api/questions/upload
```

### Human Review

```bash
# Get pending reviews
GET /api/review/pending

# Approve/reject
POST /api/review/{id}/approve
POST /api/review/{id}/reject?feedback=...

# WebSocket for real-time updates
WS /api/review/ws
```

### Learning Sessions

```bash
# Create session
POST /api/sessions

# Record attempt
POST /api/sessions/{id}/attempts

# End session (get analytics)
POST /api/sessions/{id}/end
```

### Pipeline Observability

Real-time monitoring dashboard for agent pipelines (similar to n8n):

```bash
# List all pipeline runs
GET /api/observability/runs

# Get run details with stages
GET /api/observability/runs/{run_id}

# Get run stages
GET /api/observability/runs/{run_id}/stages

# Real-time SSE stream
GET /api/observability/runs/{run_id}/stream

# Retry from failed stage
POST /api/observability/runs/{run_id}/retry
Body: { "from_stage": "blueprint_generator" }

# List all registered agents
GET /api/observability/agents

# Analytics
GET /api/observability/analytics/runs
GET /api/observability/analytics/agents
```

**Frontend Dashboard**: Navigate to `http://localhost:3000/games` and expand any game to see its run history with visual agent pipeline graphs.

## Game Templates

18 game templates covering different learning styles:

### Interactive
- **PARAMETER_PLAYGROUND** - Adjust parameters, see effects
- **SEQUENCE_BUILDER** - Drag-drop step ordering
- **BUCKET_SORT** - Categorization with drag-drop

### Visual
- **LABEL_DIAGRAM** - Label parts of diagrams
- **IMAGE_HOTSPOT_QA** - Click hotspots to answer
- **GRAPH_SKETCHER** - Draw graphs/charts

### Temporal
- **TIMELINE_ORDER** - Chronological ordering
- **STATE_TRACER_CODE** - Step through code execution

### Matching
- **MATCH_PAIRS** - Connect related items
- **MATRIX_MATCH** - Row-column matching

### And 8 more...

## Project Structure

```
GamifyAssessment/
├── backend/
│   ├── app/
│   │   ├── agents/              # LangGraph agents
│   │   │   ├── graph.py         # Main state machine + topologies
│   │   │   ├── state.py         # State schema (TypedDict)
│   │   │   ├── input_enhancer.py
│   │   │   ├── router.py
│   │   │   ├── game_planner.py
│   │   │   ├── scene_generator.py
│   │   │   ├── story_generator.py
│   │   │   ├── blueprint_generator.py
│   │   │   ├── blueprint_validator.py
│   │   │   ├── evaluation.py              # LLM-as-Judge quality metrics
│   │   │   ├── domain_knowledge_retriever.py  # Web search for labels
│   │   │   ├── diagram_image_retriever.py     # Image search
│   │   │   ├── diagram_image_segmenter.py     # SAM2/SAM segmentation
│   │   │   ├── diagram_zone_labeler.py        # VLM zone labeling
│   │   │   ├── diagram_spec_generator.py      # SVG spec generation
│   │   │   ├── diagram_svg_generator.py       # SVG rendering
│   │   │   └── schemas/                       # Pydantic schemas
│   │   │       ├── label_diagram.py           # Label diagram types
│   │   │       └── domain_knowledge.py        # Domain knowledge types
│   │   ├── config/
│   │   │   ├── models.py        # Model registry (OpenAI, Anthropic, Groq)
│   │   │   └── agent_models.py  # Per-agent model configuration
│   │   ├── db/
│   │   │   ├── database.py      # SQLAlchemy setup
│   │   │   └── models.py        # Question, Process, Session models
│   │   ├── routes/
│   │   │   ├── generate.py      # Game generation endpoints
│   │   │   ├── questions.py     # Question management
│   │   │   ├── review.py        # Human review
│   │   │   └── sessions.py      # Learning sessions
│   │   ├── services/
│   │   │   ├── llm_service.py   # Multi-provider LLM service
│   │   │   ├── web_search.py    # Serper API integration
│   │   │   ├── image_retrieval.py   # Image search service
│   │   │   ├── segmentation.py      # SAM2/SAM integration
│   │   │   └── vlm_service.py       # Ollama VLM integration
│   │   └── sandbox/             # Docker code verification
│   ├── prompts/
│   │   ├── blueprint_*.txt      # Template-specific prompts
│   │   └── diagram_svg_spec_label_diagram.txt  # SVG spec prompt
│   ├── scripts/
│   │   ├── demo_pipeline.py     # End-to-end demo
│   │   ├── run_benchmark.py     # Topology comparison
│   │   └── test_label_diagram.py  # Label diagram pipeline test
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── templates/       # 18 game template components
│   │   │   │   └── LabelDiagramGame/  # Drag-and-drop diagram game
│   │   │   │       ├── index.tsx
│   │   │   │       ├── types.ts
│   │   │   │       ├── DiagramCanvas.tsx
│   │   │   │       ├── DraggableLabel.tsx
│   │   │   │       ├── DropZone.tsx
│   │   │   │       ├── LabelTray.tsx
│   │   │   │       ├── GameControls.tsx
│   │   │   │       ├── ResultsPanel.tsx
│   │   │   │       └── hooks/useLabelDiagramState.ts
│   │   │   └── admin/           # Review dashboard
│   │   ├── stores/              # Zustand state management
│   │   └── lib/
│   │       └── evaluation.ts    # Bloom's assessment
│   └── package.json
├── sandbox/                     # Docker sandbox for code verification
├── old/                         # v1 code (preserved)
└── docker-compose.yml
```

## Quality Metrics

The system uses LLM-as-Judge with a weighted rubric:

| Dimension | Weight | What it Measures |
|-----------|--------|------------------|
| Pedagogical Alignment | 30% | Bloom's level match, learning objectives |
| Game Engagement | 25% | Interactivity, feedback quality |
| Technical Quality | 25% | Schema validity, completeness |
| Narrative Quality | 15% | Story coherence, engagement |
| Asset Quality | 5% | Visual/audio appropriateness |

## Running Tests

```bash
# Unit tests
cd backend
PYTHONPATH=. pytest tests/

# Demo pipeline (single question)
PYTHONPATH=. python scripts/demo_pipeline.py

# Topology benchmark
PYTHONPATH=. python scripts/run_benchmark.py --topologies T0,T1,T2

# Test imports
PYTHONPATH=. python tests/test_imports.py
```

## Environment Variables

### Core API Keys

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key (FREE!) | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |

### Model Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_CONFIG_PRESET` | Model preset | `balanced` |
| `AGENT_MODEL_<AGENT>` | Override agent model | - |
| `AGENT_TEMPERATURE_<AGENT>` | Override temperature | - |

### Label Diagram Pipeline

| Variable | Description | Default |
|----------|-------------|---------|
| `SERPER_API_KEY` | Web/image search API key | Required |
| `SERPER_CACHE_TTL_SECONDS` | Search cache duration | `3600` |
| `SERPER_MAX_RESULTS` | Max search results | `10` |
| `USE_IMAGE_DIAGRAMS` | Enable image retrieval | `true` |
| `SAM2_MODEL_PATH` | Path to SAM2 model weights | - |
| `SAM2_MODEL_TYPE` | SAM2 model variant | `sam2_hiera_base_plus` |
| `SAM_MODEL_PATH` | Path to SAM v1 model | - |
| `OLLAMA_BASE_URL` | VLM server URL | `http://localhost:11434` |
| `VLM_MODEL` | Vision language model | `llava:latest` |

### Database

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection | `sqlite:///./gamed_ai.db` |

## Troubleshooting

### "No LLM client available"
Set at least one API key in `.env` (GROQ_API_KEY recommended - it's free!)

### "Model decommissioned" (Groq)
Update model IDs in `backend/app/config/models.py` to latest versions.

### Import errors
Run with `PYTHONPATH=.` prefix: `PYTHONPATH=. python script.py`

### Port already in use
```bash
lsof -ti:8000 | xargs kill -9
```

## Development Status

- [x] LangGraph agent pipeline
- [x] 14+ specialized agents implemented
- [x] Plug-and-play model configuration
- [x] Groq free tier support
- [x] Quality evaluation rubric
- [x] FastAPI backend with SQLite
- [x] Template-specific blueprint prompts
- [x] Label Diagram pipeline (web search, SAM segmentation, VLM labeling)
- [x] Frontend game player UI (drag-and-drop with dnd-kit)
- [x] SVG diagram generation
- [x] Validation retry loops with human review fallback
- [ ] Admin review dashboard
- [ ] Docker sandbox verification
- [ ] Complete test coverage

## Contributing

### Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `cd backend && PYTHONPATH=. pytest tests/`
5. Run TypeScript check: `cd frontend && npx tsc --noEmit`
6. Submit a pull request

### Adding a New Agent

When adding a new agent, you **MUST** complete these steps for proper observability:

1. **Backend: Define I/O Keys** (`backend/app/agents/instrumentation.py`)
   ```python
   # Add to extract_input_keys()
   "my_agent": ["input_key_1", "input_key_2"],

   # Add to extract_output_keys()
   "my_agent": ["output_key_1"],
   ```

2. **Frontend: Add Metadata** (`frontend/src/components/pipeline/PipelineView.tsx`)
   ```typescript
   my_agent: {
     name: 'My Agent',
     description: 'What it does',
     category: 'generation',  // input|routing|image|generation|validation|output
     toolOrModel: 'LLM (configurable)',
     color: '#8B5CF6',
     icon: '🔧'
   },
   ```

3. **Frontend: Add to Graph Layout** (same file)
   - Add agent to `GRAPH_LAYOUT` array
   - Add edges to `edgeDefinitions` array

4. **Backend: Register in Graph** (`backend/app/agents/graph.py`)
   ```python
   graph.add_node("my_agent", wrap_agent_with_instrumentation(my_agent, "my_agent"))
   ```

5. **Optional: Custom Output Renderer** (`frontend/src/components/pipeline/StagePanel.tsx`)

See `CLAUDE.md` for complete agent development checklist and coding standards.

### Documentation

| File | Purpose |
|------|---------|
| `CLAUDE.md` | AI assistant instructions, coding standards, agent checklist |
| `COMMANDS.md` | Quick command reference for development |
| `.cursorrules` | Cursor IDE integration rules |

## License

MIT

## Credits

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - API framework
- [Groq](https://groq.com/) - Free LLM inference
- [Anthropic Claude](https://anthropic.com/) - Premium LLM
- [OpenAI GPT-4](https://openai.com/) - Premium LLM
