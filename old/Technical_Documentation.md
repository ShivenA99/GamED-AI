# AI-Powered Gamified Learning Platform - Technical Documentation

## Executive Summary

This repository implements an **AI-powered educational transformation system** that converts static questions into interactive, story-based learning games. The platform uses a sophisticated 4-layer pipeline architecture with template-based game generation, leveraging LLMs (OpenAI GPT & Anthropic Claude) to analyze questions, select optimal game formats, and generate immersive learning experiences.

**Core Value Proposition**: Transform any educational question from documents (PDF, DOCX, TXT) into one of 18 pre-defined interactive game templates with AI-generated narratives and structured gameplay mechanics.

---

## 1. System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  (Next.js Frontend - Brilliant.org-inspired design)            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                              │
│                                                                  │
│  ┌───────────────────────────────────────────────────────┐    │
│  │              4-LAYER PIPELINE ORCHESTRATOR             │    │
│  │                                                         │    │
│  │  Layer 1: Input Processing                            │    │
│  │  ├─ Document Parser (PDF, DOCX, TXT)                  │    │
│  │  └─ Question Extractor                                │    │
│  │                                                         │    │
│  │  Layer 2: Analysis & Routing                          │    │
│  │  ├─ Question Classifier (type, subject, difficulty)   │    │
│  │  └─ Template Router (selects 1 of 18 game templates)  │    │
│  │                                                         │    │
│  │  Layer 3: Strategy                                     │    │
│  │  ├─ Gamification Strategy Creator                     │    │
│  │  └─ Storyline Generator                               │    │
│  │                                                         │    │
│  │  Layer 4: Generation                                   │    │
│  │  ├─ Story Generator (template-aware narrative)        │    │
│  │  ├─ Blueprint Generator (structured JSON)             │    │
│  │  ├─ Asset Planner (identifies required assets)        │    │
│  │  └─ Asset Generator (placeholder URLs)                │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────┐                    │
│  │  SQLite/Postgres│  │   LLM Services   │                    │
│  │  Database       │  │  OpenAI/Anthropic│                    │
│  └─────────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GAME ENGINE                                │
│  (Frontend - Renders 18 Template Components)                   │
│  ├─ Label Diagram         ├─ Parameter Playground              │
│  ├─ Image Hotspot QA      ├─ Graph Sketcher                   │
│  ├─ Sequence Builder      ├─ Vector Sandbox                   │
│  ├─ Timeline Order        ├─ State Tracer Code                │
│  ├─ Bucket Sort           ├─ Spot The Mistake                 │
│  ├─ Match Pairs           ├─ Concept Map Builder              │
│  ├─ Matrix Match          ├─ Micro Scenario Branching         │
│  ├─ Design Constraint     ├─ Probability Lab                  │
│  └─ Before/After          └─ Geometry Builder                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. End-to-End Workflow

### Complete Pipeline Flow

```
1. UPLOAD & INGESTION
   User uploads → Document file (PDF/DOCX/TXT)
                 ↓
2. LAYER 1: INPUT PROCESSING
   Document Parser → Extracts raw text
   Question Extractor → Identifies question + options
                 ↓
3. LAYER 2: ANALYSIS & ROUTING
   Classification → Determines question type, subject, difficulty
   Template Router → LLM selects optimal game template (1 of 18)
                 ↓
4. LAYER 3: STRATEGY
   Strategy Creator → Defines gamification approach
   Storyline Generator → Creates narrative framework
                 ↓
5. LAYER 4: GENERATION
   Story Generator → Generates template-specific narrative
   Blueprint Generator → Creates structured JSON blueprint
   Asset Planner → Identifies required visual assets
   Asset Generator → Generates asset URLs (placeholder)
                 ↓
6. STORAGE & DELIVERY
   Database → Stores question, analysis, story, blueprint
   API Response → Returns visualization_id
                 ↓
7. FRONTEND RENDERING
   Game Engine → Loads blueprint JSON
   Template Component → Renders interactive game
   Score Tracker → Monitors user progress
```

---

## 3. Pipeline Components - Deep Dive

### Layer 1: Input Processing

#### 3.1.1 Document Parser Service

**Purpose**: Extract structured text from various document formats

**Technologies**:
- `PyPDF2` - PDF parsing
- `python-docx` - Word document parsing
- `io.BytesIO` - In-memory file handling

**Function**: `DocumentParserService.parse_document()`

**Input**:
```python
{
    "file_content": bytes,
    "filename": "example.pdf"
}
```

**Output**:
```python
{
    "success": True,
    "data": {
        "text": "What is the time complexity of binary search?",
        "full_text": "...",
        "file_type": "pdf"
    },
    "validation": {
        "is_valid": True,
        "errors": [],
        "warnings": []
    }
}
```

**Implementation Approach**:
- Detects file type from extension
- Uses appropriate parser library
- Validates extracted content structure
- Returns structured data with metadata

**Key Code Location**: `backend/app/services/document_parser.py`

---

#### 3.1.2 Question Extractor Service

**Purpose**: Identify and structure questions with options from raw text

**Function**: `QuestionExtractorService.extract_question()`

**Input**:
```python
{
    "text": "Question: What is O(log n)?\nA) Linear\nB) Logarithmic\nC) Exponential",
    "filename": "quiz.txt"
}
```

**Output**:
```python
{
    "text": "What is O(log n)?",
    "options": ["Linear", "Logarithmic", "Exponential"],
    "file_type": "txt"
}
```

**Implementation**: Uses regex and heuristics to parse question patterns (numbered lists, bullet points, multiple choice formats)

---

### Layer 2: Analysis & Routing

#### 3.2.1 Classification Orchestrator

**Purpose**: Analyze question characteristics using LLM

**Components**:
- `QuestionTypeClassifier` - Identifies question type
- `SubjectIdentifier` - Determines subject/topic
- `ComplexityAnalyzer` - Assesses difficulty level

**Function**: `ClassificationOrchestrator.analyze_question()`

**Input**:
```python
{
    "question_text": "Implement a function to reverse a linked list",
    "options": ["Iterative", "Recursive", "Both", "Neither"]
}
```

**Output**:
```python
{
    "question_type": "coding",
    "subject": "Data Structures",
    "difficulty": "intermediate",
    "key_concepts": ["linked lists", "pointers", "iteration", "recursion"],
    "intent": "Test understanding of linked list manipulation"
}
```

**LLM Prompting Strategy**:
- System prompt: "You are a question classification expert"
- User prompt: Structured question + context
- Response format: JSON-only (parsed with error handling)
- Fallback: Anthropic Claude if OpenAI fails

**Key Code**: `backend/app/services/pipeline/layer2_classification.py`

---

#### 3.2.2 Template Router

**Purpose**: Select optimal game template from 18 options using LLM

**Why This is Critical**: This is the **core routing decision** that determines the entire game experience

**Available Templates** (18 total):
1. `LABEL_DIAGRAM` - Diagram labeling with drag-and-drop
2. `IMAGE_HOTSPOT_QA` - Interactive image with clickable hotspots
3. `SEQUENCE_BUILDER` - Order steps in correct sequence
4. `TIMELINE_ORDER` - Arrange events chronologically
5. `BUCKET_SORT` - Categorize items into buckets
6. `MATCH_PAIRS` - Match related pairs
7. `MATRIX_MATCH` - Match items across two dimensions
8. `PARAMETER_PLAYGROUND` - Interactive parameter manipulation
9. `GRAPH_SKETCHER` - Draw and manipulate graphs
10. `VECTOR_SANDBOX` - Vector operations visualization
11. `STATE_TRACER_CODE` - Step through code execution
12. `SPOT_THE_MISTAKE` - Identify errors in code/content
13. `CONCEPT_MAP_BUILDER` - Build concept relationships
14. `MICRO_SCENARIO_BRANCHING` - Interactive branching scenarios
15. `DESIGN_CONSTRAINT_BUILDER` - Design with constraints
16. `PROBABILITY_LAB` - Probability experiments
17. `BEFORE_AFTER_TRANSFORMER` - Visualize transformations
18. `GEOMETRY_BUILDER` - Geometric construction

**Function**: `TemplateRouter.route_template()`

**Input**:
```python
{
    "question_text": "Trace the execution of bubble sort on [5,2,8,1]",
    "analysis": {
        "question_type": "coding",
        "subject": "Algorithms",
        "difficulty": "beginner",
        "key_concepts": ["sorting", "iteration", "comparison"],
        "intent": "Visualize algorithm execution"
    }
}
```

**Output**:
```python
{
    "success": True,
    "data": {
        "templateType": "STATE_TRACER_CODE",
        "confidence": 0.92,
        "rationale": "This question requires step-by-step visualization of algorithm execution, making STATE_TRACER_CODE the optimal choice"
    }
}
```

**Routing Logic**:
- Loads system prompt from `prompts/template_router_system.txt`
- Analyzes question characteristics + analysis data
- LLM makes informed template selection
- Validates against allowed template list
- Falls back to `SEQUENCE_BUILDER` if invalid

**Key Innovation**: Template-aware routing ensures appropriate game mechanics match question intent

**Key Code**: `backend/app/services/pipeline/layer2_template_router.py`

---

### Layer 3: Strategy

#### 3.3.1 Strategy Orchestrator

**Purpose**: Define gamification approach and narrative framework

**Components**:
- `GameFormatSelector` - Selects interaction mechanics
- `StorylineGenerator` - Creates narrative context
- `InteractionDesigner` - Defines user interactions

**Function**: `StrategyOrchestrator.create_strategy()`

**Output**:
```python
{
    "game_format": "simulation",
    "storyline": {
        "title": "The Sorting Detective",
        "context": "Help Detective Ada solve cases by organizing evidence",
        "characters": ["Detective Ada", "Suspect List"],
        "setting": "Police headquarters evidence room"
    },
    "interactions": {
        "primary": "drag_and_compare",
        "secondary": "step_through",
        "feedback": "immediate_visual"
    },
    "prompt_template": "story_base.md + template_supplement"
}
```

**Key Code**: `backend/app/services/pipeline/layer3_strategy.py`

---

### Layer 4: Generation

#### 3.4.1 Story Generator

**Purpose**: Generate template-specific narrative content

**Function**: `StoryGenerator.generate()`

**Input**:
```python
{
    "question_data": {
        "text": "What is the time complexity of binary search?",
        "options": ["O(n)", "O(log n)", "O(n²)", "O(1)"]
    },
    "strategy": {...},
    "template_type": "PARAMETER_PLAYGROUND"
}
```

**Prompt Engineering**:
- Base prompt: `prompts/story_base.md` (universal narrative guidelines)
- Template supplement: `prompts/story_templates/{template_type}.txt` (template-specific guidance)
- Combined system prompt for context-aware generation

**Output**:
```python
{
    "success": True,
    "data": {
        "title": "The Search Algorithm Challenge",
        "narrative": "You're optimizing a search engine...",
        "objectives": ["Understand binary search efficiency", ...],
        "context": "Tech startup scenario",
        "tone": "professional yet engaging"
    }
}
```

**Key Code**: `backend/app/services/pipeline/layer4_generation.py`

---

#### 3.4.2 Blueprint Generator

**Purpose**: Generate structured JSON blueprint for frontend rendering

**Why Blueprints?**: Provides type-safe, validated game configurations instead of HTML strings

**Function**: `BlueprintGenerator.generate()`

**Input**:
```python
{
    "story_data": {...},
    "template_type": "SEQUENCE_BUILDER"
}
```

**Output Example** (SEQUENCE_BUILDER):
```json
{
    "templateType": "SEQUENCE_BUILDER",
    "title": "Algorithm Steps Challenge",
    "narrative": "Arrange the binary search steps...",
    "items": [
        {
            "id": "step_1",
            "content": "Calculate middle index",
            "correctPosition": 1
        },
        {
            "id": "step_2",
            "content": "Compare target with middle element",
            "correctPosition": 2
        },
        {
            "id": "step_3",
            "content": "Adjust search boundaries",
            "correctPosition": 3
        }
    ],
    "hints": ["Start with initialization", "Think about the comparison"],
    "successMessage": "Perfect! You understand binary search flow!",
    "scoring": {
        "maxScore": 100,
        "penaltyPerMistake": 10
    }
}
```

**Template-Specific Schemas**: Each template has unique blueprint structure defined in TypeScript interfaces

**Validation**: Uses `BlueprintValidator` to ensure schema compliance

**Key Code**: `backend/app/services/pipeline/layer4_generation.py` (lines 238-346)

---

#### 3.4.3 Asset Planner

**Purpose**: Identify required visual assets from blueprint

**Function**: `AssetPlanner.plan_assets()`

**Input**: Blueprint JSON

**Output**:
```python
[
    {
        "type": "image",
        "purpose": "diagram",
        "prompt": "Binary search tree visualization with highlighted nodes"
    },
    {
        "type": "image",
        "purpose": "visualization",
        "prompt": "Step-by-step array division diagram"
    }
]
```

**Logic**: Scans blueprint for `assetPrompt` fields in template-specific structures

**Key Code**: `backend/app/services/pipeline/layer4_generation.py` (lines 355-427)

---

#### 3.4.4 Asset Generator

**Purpose**: Generate asset URLs (currently placeholder implementation)

**Function**: `AssetGenerator.generate_assets()`

**Current Implementation**: Returns placeholder URLs
**Future Enhancement**: Integration with DALL-E, Stable Diffusion, or Midjourney APIs

**Output**:
```python
{
    "diagram": "https://placeholder.com/800x600?text=Binary+Search+Tree",
    "visualization": "https://placeholder.com/800x600?text=Array+Division"
}
```

**Injection**: `inject_asset_urls()` embeds URLs into blueprint's `assetUrl` fields

**Key Code**: `backend/app/services/pipeline/layer4_generation.py` (lines 428-486)

---

### Pipeline Orchestrator

**Purpose**: Coordinates all 9 pipeline steps with state management, error handling, and resumability

**Key Features**:
- **Sequential Execution**: Runs steps 1-9 in order
- **State Persistence**: Saves intermediate results to database
- **Resumability**: Can restart from last completed step on failure
- **Validation**: Validates each step output
- **Retry Logic**: Implements exponential backoff for transient failures

**Function**: `PipelineOrchestrator.execute_pipeline()`

**Pipeline Steps**:
```python
PIPELINE_STEPS = [
    {"name": "document_parsing", "number": 1, "layer": 1},
    {"name": "question_extraction", "number": 2, "layer": 1},
    {"name": "question_analysis", "number": 3, "layer": 2},
    {"name": "template_routing", "number": 4, "layer": 2},
    {"name": "strategy_creation", "number": 5, "layer": 3},
    {"name": "story_generation", "number": 6, "layer": 4},
    {"name": "blueprint_generation", "number": 7, "layer": 4},
    {"name": "asset_planning", "number": 8, "layer": 4},
    {"name": "asset_generation", "number": 9, "layer": 4},
]
```

**State Management**:
```python
pipeline_state = {
    "question_id": "uuid",
    "question_text": "...",
    "extracted_question": {...},
    "analysis": {...},
    "template_type": "SEQUENCE_BUILDER",
    "strategy": {...},
    "story": {...},
    "blueprint": {...},
    "asset_requests": [...],
    "assets": {...}
}
```

**Progress Tracking**: Updates database with current step and percentage (0-100%)

**Key Code**: `backend/app/services/pipeline/orchestrator.py`

---

## 4. Database Schema

### Entity-Relationship Model

```
┌─────────────┐
│  Question   │
│─────────────│
│ id (PK)     │
│ text        │
│ options     │──┐
│ file_type   │  │
│ created_at  │  │
└─────────────┘  │
                 │
      ┌──────────┴─────────────┬──────────────┬─────────────┐
      │                        │              │             │
      ▼                        ▼              ▼             ▼
┌──────────────┐    ┌───────────────┐  ┌──────────┐  ┌─────────────┐
│QuestionAnalys│    │    Story      │  │ Process  │  │GameBlueprint│
│──────────────│    │───────────────│  │──────────│  │─────────────│
│id (PK)       │    │id (PK)        │  │id (PK)   │  │id (PK)      │
│question_id FK│    │question_id FK │  │question  │  │question_id  │
│question_type │    │story_data JSON│  │status    │  │blueprint    │
│subject       │    │created_at     │  │progress  │  │template_type│
│difficulty    │    └───────────────┘  │current   │  │assets JSON  │
│key_concepts  │                       │_step     │  │created_at   │
│intent        │                       └────┬─────┘  └─────────────┘
└──────────────┘                            │
                                            ▼
                                    ┌──────────────┐
                                    │PipelineStep  │
                                    │──────────────│
                                    │id (PK)       │
                                    │process_id FK │
                                    │step_name     │
                                    │step_number   │
                                    │status        │
                                    │input_data    │
                                    │output_data   │
                                    │error_message │
                                    └──────────────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │Visualization │
                                    │──────────────│
                                    │id (PK)       │
                                    │question_id FK│
                                    │process_id FK │
                                    │blueprint_id  │
                                    │story_data    │
                                    │created_at    │
                                    └──────────────┘
```

### Key Models

**Question**:
- Stores uploaded questions
- Tracks file type and full text
- Central entity for relationships

**QuestionAnalysis**:
- Stores Layer 2 classification results
- One-to-one with Question
- Influences template routing

**Process**:
- Tracks pipeline execution state
- Stores progress percentage (0-100)
- Links to PipelineStep for granular tracking

**PipelineStep**:
- Stores individual step execution details
- Tracks input/output data (JSON)
- Enables resumability and debugging

**GameBlueprint**:
- Stores generated blueprint JSON
- Links to template type
- Contains asset URLs

**Visualization**:
- Final output entity
- Links question → blueprint → process
- Returned to frontend for rendering

**Key Code**: `backend/app/db/models.py`

---

## 5. Frontend Architecture

### Component Hierarchy

```
App (Next.js)
├── /app (Upload Page)
│   ├── Header
│   ├── Upload Zone
│   └── File Processor
│
├── /app/preview (Preview Page)
│   ├── Question Display
│   ├── Analysis Summary
│   ├── PipelineProgress (real-time polling)
│   └── Generate Game Button
│
└── /app/game (Game Page)
    ├── GameEngine (Router)
    │   ├── LabelDiagramGame
    │   ├── SequenceBuilderGame
    │   ├── StateTracerCodeGame
    │   ├── ... (18 total templates)
    │   └── Score Tracker
    └── Completion Screen
```

### GameEngine Component

**Purpose**: Routes blueprint to appropriate template component

**Implementation**: Switch statement on `blueprint.templateType`

**Key Code**: `frontend/src/components/GameEngine.tsx`

```typescript
export function GameEngine({ blueprint }: GameEngineProps) {
  switch (blueprint.templateType) {
    case 'LABEL_DIAGRAM':
      return <LabelDiagramGame blueprint={blueprint} />
    case 'SEQUENCE_BUILDER':
      return <SequenceBuilderGame blueprint={blueprint} />
    case 'STATE_TRACER_CODE':
      return <StateTracerCodeGame blueprint={blueprint} />
    // ... 15 more templates
    default:
      return <ErrorMessage />
  }
}
```

### Template Component Pattern

Each template follows consistent structure:

1. **State Management**: Track user interactions, score, completion
2. **Blueprint Parsing**: Extract template-specific data
3. **Interaction Handlers**: Drag-drop, click, input events
4. **Validation Logic**: Check correctness, provide feedback
5. **Score Calculation**: Award points, apply penalties
6. **Visual Feedback**: Animations, colors, success/error messages

**Example** (SequenceBuilderGame):
```typescript
export function SequenceBuilderGame({ blueprint }: Props) {
  const [items, setItems] = useState(blueprint.items)
  const [score, setScore] = useState(0)
  const [isComplete, setIsComplete] = useState(false)

  const handleDragEnd = (result: DropResult) => {
    // Reorder items
    // Check correctness
    // Update score
  }

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <Droppable droppableId="sequence">
        {items.map((item, index) => (
          <Draggable key={item.id} draggableId={item.id} index={index}>
            {/* Render item */}
          </Draggable>
        ))}
      </Droppable>
    </DragDropContext>
  )
}
```

**Key Directory**: `frontend/src/components/templates/`

---

### State Management (Zustand)

**Stores**:
- `questionStore` - Uploaded question data
- `pipelineStore` - Process ID, progress tracking
- `gameStore` - Game state, score, completion

**Example**:
```typescript
// frontend/src/stores/pipelineStore.ts
export const usePipelineStore = create<PipelineStore>((set) => ({
  processId: null,
  status: 'idle',
  progress: 0,
  currentStep: null,
  visualizationId: null,
  
  setProcessId: (id) => set({ processId: id }),
  setProgress: (progress) => set({ progress }),
  reset: () => set({ processId: null, progress: 0 })
}))
```

---

### Real-Time Progress Tracking

**Component**: `PipelineProgress.tsx`

**Implementation**:
- Polls `/api/progress/{processId}` every 2 seconds
- Displays current step (1-9) and percentage
- Shows step-by-step progress with animations
- Implements timeout safeguards (5 min max, 30s stuck detection)
- Handles completion → redirects to game

**API Response**:
```json
{
  "status": "processing",
  "progress": 66,
  "current_step": "blueprint_generation",
  "steps": [
    {"name": "document_parsing", "status": "completed"},
    {"name": "question_extraction", "status": "completed"},
    {"name": "question_analysis", "status": "completed"},
    {"name": "template_routing", "status": "completed"},
    {"name": "strategy_creation", "status": "completed"},
    {"name": "story_generation", "status": "completed"},
    {"name": "blueprint_generation", "status": "processing"},
    {"name": "asset_planning", "status": "pending"},
    {"name": "asset_generation", "status": "pending"}
  ],
  "visualization_id": null
}
```

---

## 6. API Endpoints

### Upload
- **POST** `/api/upload`
- Accepts: `multipart/form-data` (file)
- Returns: `{question_id, text, options}`

### Process
- **POST** `/api/process/{question_id}`
- Starts pipeline execution
- Returns: `{process_id}`

### Progress
- **GET** `/api/progress/{process_id}`
- Returns: Current pipeline status, progress, steps

### Visualization
- **GET** `/api/visualizations/{visualization_id}`
- Returns: Complete visualization data (story + blueprint + metadata)

### Questions
- **GET** `/api/questions/{question_id}`
- Returns: Question details + analysis

---

## 7. Technology Stack

### Backend

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **FastAPI** | 0.104+ | Web framework | Async support, automatic OpenAPI docs, fast performance |
| **SQLAlchemy** | 2.0+ | ORM | Type-safe database operations, relationship management |
| **OpenAI SDK** | 1.3.5+ | LLM integration | Primary LLM for classification, routing, generation |
| **Anthropic SDK** | 0.7.7+ | LLM fallback | Claude as backup for reliability |
| **PyPDF2** | 3.0+ | PDF parsing | Lightweight, reliable PDF extraction |
| **python-docx** | 1.1+ | DOCX parsing | Standard library for Word documents |
| **Pydantic** | 2.9+ | Data validation | Type-safe request/response models |
| **Uvicorn** | 0.24+ | ASGI server | Production-ready async server |
| **Alembic** | 1.12+ | Migrations | Database schema versioning |

### Frontend

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **Next.js** | 14+ | React framework | App Router, SSR, optimized routing |
| **TypeScript** | 5.3+ | Type safety | Prevents runtime errors, improves DX |
| **Tailwind CSS** | 3.3+ | Styling | Utility-first, rapid development |
| **Framer Motion** | 10.16+ | Animations | Smooth, declarative animations |
| **Zustand** | 4.4+ | State management | Lightweight, simple API |
| **Lucide React** | 0.294+ | Icons | Modern, customizable icons |
| **Axios** | 1.6+ | HTTP client | Promise-based, interceptor support |

---

## 8. Unique & Innovative Aspects

### 1. **Template-Based Blueprint System**
- **Innovation**: Fixed set of 18 game templates ensures consistent UX
- **Benefit**: Type-safe, predictable game mechanics vs. dynamic HTML generation
- **Trade-off**: Less flexibility, but higher quality and reliability

### 2. **4-Layer Pipeline Architecture**
- **Design Pattern**: Clear separation of concerns
- **Benefit**: Each layer has single responsibility, easy to test/debug
- **Extensibility**: Can add new templates without changing pipeline logic

### 3. **LLM-Driven Template Routing**
- **Innovation**: Uses AI to select optimal game format based on question analysis
- **Intelligence**: Goes beyond simple rule-based routing
- **Example**: Coding questions → STATE_TRACER_CODE, Timeline questions → TIMELINE_ORDER

### 4. **Template-Aware Story Generation**
- **Innovation**: Loads template-specific prompts to guide narrative generation
- **File Structure**: `prompts/story_base.md` + `prompts/story_templates/{template}.txt`
- **Benefit**: Stories optimized for game mechanics (e.g., detective narrative for SEQUENCE_BUILDER)

### 5. **Resumable Pipeline with State Persistence**
- **Resilience**: Stores intermediate results in database
- **Recovery**: Can resume from last completed step after crash
- **Implementation**: `PipelineStepRepository` tracks step-by-step progress

### 6. **Real-Time Progress Tracking with Polling Safeguards**
- **UX**: Users see live progress through 9 pipeline steps
- **Reliability**: Implements timeout detection (5 min max, 30s stuck threshold)
- **Error Handling**: Gracefully handles backend restarts, connection errors

### 7. **Brilliant.org-Inspired Design**
- **Aesthetic**: Clean, modern, professional UI matching educational gold standard
- **Animations**: Framer Motion for smooth transitions, engaging interactions
- **Typography**: Clear hierarchy, readable fonts, proper spacing

---

## 9. Configuration & Setup Requirements

### Environment Variables

**Backend** (`.env`):
```bash
# Required
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
DATABASE_URL=sqlite:///./ai_learning_platform.db
# Or PostgreSQL: postgresql://user:pass@localhost/dbname
LOG_LEVEL=INFO
```

**Frontend** (`next.config.js`):
```javascript
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}
```

### Installation Steps

**Backend**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head  # Run migrations
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev  # Runs on localhost:3000
```

### System Requirements
- Python 3.9+
- Node.js 18+
- 4GB RAM minimum (LLM API calls are memory-light)
- Internet connection (for OpenAI/Anthropic APIs)

### API Keys
- **OpenAI**: [platform.openai.com](https://platform.openai.com)
- **Anthropic**: [console.anthropic.com](https://console.anthropic.com)

---

## 10. Visual Architecture Diagram Suggestion

### Main Flowchart Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE DIAGRAM                         │
└─────────────────────────────────────────────────────────────────┘

1. USER JOURNEY FLOWCHART
   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Upload  │─→│ Preview │─→│ Process │─→│  Play   │
   │  File   │   │Question │   │Pipeline │   │  Game   │
   └─────────┘   └─────────┘   └─────────┘   └─────────┘

2. PIPELINE LAYERS DIAGRAM (Vertical)
   Layer 1: Input Processing ════════════════════════
   Layer 2: Analysis & Routing ═══════════════════════
   Layer 3: Strategy ═══════════════════════════════════
   Layer 4: Generation ══════════════════════════════════

3. TEMPLATE ROUTER DECISION TREE
   Question Analysis
         ├─ Coding? → STATE_TRACER_CODE / SPOT_THE_MISTAKE
         ├─ Timeline? → TIMELINE_ORDER
         ├─ Sorting? → BUCKET_SORT / SEQUENCE_BUILDER
         ├─ Visual? → LABEL_DIAGRAM / IMAGE_HOTSPOT_QA
         └─ Scenario? → MICRO_SCENARIO_BRANCHING

4. DATA FLOW DIAGRAM (Horizontal)
   Document → Text → Analysis → Template → Story → Blueprint → Game

5. DATABASE SCHEMA (ER Diagram)
   [See Section 4 for detailed relationships]

6. COMPONENT TREE (Frontend)
   App
   ├── Header (persistent)
   ├── Pages
   │   ├── Upload
   │   ├── Preview
   │   └── Game
   └── GameEngine
       └── [18 Template Components]
```

**Recommended Diagramming Tools**:
- Mermaid (Markdown-embedded diagrams)
- Excalidraw (hand-drawn style)
- Lucidchart (professional)
- PlantUML (code-based)

---

## 11. File Structure Overview

```
Claude_Hackathon/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── db/
│   │   │   ├── models.py              # SQLAlchemy models
│   │   │   ├── database.py            # DB connection
│   │   │   └── session.py             # Session management
│   │   ├── routes/
│   │   │   ├── upload.py              # POST /upload
│   │   │   ├── progress.py            # GET /progress/{id}
│   │   │   └── visualizations.py      # GET /visualizations/{id}
│   │   ├── services/
│   │   │   ├── llm_service.py         # OpenAI/Anthropic wrapper
│   │   │   ├── document_parser.py     # PDF/DOCX parser
│   │   │   └── pipeline/
│   │   │       ├── orchestrator.py    # Main pipeline controller
│   │   │       ├── layer1_input.py    # Document processing
│   │   │       ├── layer2_classification.py
│   │   │       ├── layer2_template_router.py
│   │   │       ├── layer3_strategy.py
│   │   │       └── layer4_generation.py
│   │   ├── repositories/              # Data access layer
│   │   └── utils/
│   │       └── logger.py              # Structured logging
│   ├── prompts/
│   │   ├── story_base.md              # Base story prompt
│   │   ├── blueprint_base.md          # Base blueprint prompt
│   │   └── story_templates/           # 18 template-specific prompts
│   ├── requirements.txt
│   └── alembic/                       # Database migrations
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Upload page
│   │   │   ├── preview/page.tsx       # Preview page
│   │   │   └── game/page.tsx          # Game page
│   │   ├── components/
│   │   │   ├── GameEngine.tsx         # Template router
│   │   │   ├── PipelineProgress.tsx   # Progress tracker
│   │   │   └── templates/             # 18 game components
│   │   │       ├── LabelDiagramGame.tsx
│   │   │       ├── SequenceBuilderGame.tsx
│   │   │       ├── StateTracerCodeGame.tsx
│   │   │       └── ... (15 more)
│   │   ├── stores/                    # Zustand state
│   │   │   ├── questionStore.ts
│   │   │   └── pipelineStore.ts
│   │   └── types/
│   │       └── gameBlueprint.ts       # TypeScript interfaces
│   ├── package.json
│   └── tailwind.config.ts
│
├── README.md                          # Quick start guide
├── SETUP.md                           # Detailed setup instructions
└── TECHNICAL_DOCUMENTATION.md         # This file
```

---

## 12. Performance Characteristics

### Latency Benchmarks (Estimated)

| Stage | Duration | Bottleneck |
|-------|----------|------------|
| Document Upload | 0.5-2s | File size, network |
| Layer 1 (Parsing) | 1-3s | Document complexity |
| Layer 2 (Analysis) | 3-8s | LLM API latency |
| Layer 2.5 (Routing) | 2-5s | LLM API latency |
| Layer 3 (Strategy) | 3-6s | LLM API latency |
| Layer 4 (Generation) | 8-15s | LLM API latency (story + blueprint) |
| **Total Pipeline** | **20-40s** | Cumulative LLM calls |

### Optimization Opportunities
1. **Parallel LLM calls** (Layer 2 classification + routing simultaneously)
2. **Caching** (Template routing for similar questions)
3. **Streaming** (Progressive blueprint generation)
4. **Queue system** (Celery/RQ for background processing)

---

## 13. Testing Strategy (Recommended)

### Unit Tests
- **Validators**: Test input/output validation logic
- **Parsers**: Test document extraction with sample files
- **Blueprint Generation**: Test template-specific schemas

### Integration Tests
- **Pipeline Flow**: Test end-to-end execution with mock LLMs
- **Database Operations**: Test CRUD operations, relationships
- **API Endpoints**: Test request/response with test client

### E2E Tests
- **User Flow**: Upload → Preview → Process → Play
- **Template Rendering**: Verify all 18 templates render correctly
- **Error Handling**: Test timeout, invalid files, API failures

---

## 14. Deployment Considerations

### Backend Deployment
- **Platform**: Railway, Render, Heroku, AWS ECS
- **Database**: PostgreSQL (prod) vs SQLite (dev)
- **Environment**: Load API keys from secure secrets management
- **Monitoring**: Sentry for error tracking, DataDog for metrics

### Frontend Deployment
- **Platform**: Vercel (optimized for Next.js), Netlify
- **Build**: Static export or SSR
- **CDN**: Automatic with Vercel/Netlify
- **Analytics**: Google Analytics, Mixpanel

### Scaling Strategy
- **Horizontal**: Multiple backend instances behind load balancer
- **Caching**: Redis for progress data, frequent queries
- **Queue**: Celery for async pipeline processing
- **CDN**: Serve static assets (game templates, images)

---

## 15. Future Enhancement Roadmap

### Phase 1: Asset Generation (High Priority)
- Integrate DALL-E 3 or Stable Diffusion for actual image generation
- Replace placeholder URLs with real assets
- Asset storage in S3/CloudFlare R2

### Phase 2: Advanced Templates
- Add 5-10 more templates (e.g., CIRCUIT_BUILDER, MOLECULE_ASSEMBLER)
- Interactive 3D visualizations (Three.js)
- Code execution sandbox (for STATE_TRACER_CODE)

### Phase 3: Personalization
- User accounts, progress tracking
- Adaptive difficulty based on performance
- Recommendation engine for similar questions

### Phase 4: Collaboration
- Multiplayer game modes
- Teacher dashboard for class management
- Question authoring tool (skip upload, direct input)

### Phase 5: Analytics
- Learning analytics dashboard
- A/B testing for template effectiveness
- Heatmaps for interaction patterns

---

## 16. Known Limitations & Trade-offs

### Limitations
1. **Fixed Templates**: Only 18 templates, not infinitely flexible
2. **Asset Generation**: Placeholder URLs, not real images
3. **LLM Costs**: Each question costs $0.05-0.15 in API fees
4. **Processing Time**: 20-40s latency may frustrate users
5. **No Real-Time Collaboration**: Single-player only

### Trade-offs
| Decision | Benefit | Cost |
|----------|---------|------|
| Fixed templates | Predictable, high-quality UX | Less flexibility |
| LLM-based routing | Intelligent, adaptive | Slower, more expensive |
| Blueprint JSON | Type-safe, validated | More complex than HTML strings |
| Sequential pipeline | Easier to debug, resume | Slower than parallel processing |

---

## 17. Troubleshooting Guide

### Common Issues

**Backend won't start**:
- Check `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` in `.env`
- Verify Python 3.9+ with `python --version`
- Install dependencies: `pip install -r requirements.txt`

**Upload fails**:
- Check file size < 10MB
- Verify supported format (PDF, DOCX, TXT)
- Check backend logs for parsing errors

**Pipeline stuck at 88%**:
- Check backend logs for LLM API errors
- Verify API keys have sufficient credits
- Restart backend to clear stuck processes

**Frontend doesn't connect**:
- Verify backend running on `localhost:8000`
- Check CORS settings in `backend/app/main.py`
- Verify Next.js proxy in `frontend/next.config.js`

---

## 18. Glossary

- **Blueprint**: Structured JSON configuration for game template
- **Layer**: Stage in 4-layer pipeline architecture
- **Template**: Pre-defined game format (1 of 18)
- **Orchestrator**: Central controller for pipeline execution
- **Process**: Single pipeline execution instance
- **Visualization**: Final output linking question → blueprint → game

---

## Conclusion

This platform represents a sophisticated fusion of AI, educational theory, and modern web development. The 4-layer pipeline with template-based routing ensures high-quality, predictable learning experiences while leveraging LLMs for intelligent content generation.

**Key Strengths**:
✅ Clean architecture with clear separation of concerns  
✅ Type-safe, validated game blueprints  
✅ Resumable pipeline with error recovery  
✅ 18 diverse, well-designed game templates  
✅ Professional UI inspired by Brilliant.org  

**Next Steps for Production**:
1. Integrate real asset generation (DALL-E)
2. Implement caching and queue system
3. Add comprehensive testing suite
4. Deploy to production infrastructure
5. Monitor performance and iterate

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-09  
**Author**: Technical Documentation Team  
**Repository**: [Claude_Hackathon](https://github.com/Mayank-glitch-cpu/Claude_Hackathon)
