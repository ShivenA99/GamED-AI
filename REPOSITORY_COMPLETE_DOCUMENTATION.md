# GamED.AI v2 - Complete Repository Documentation

**Version:** 2.0.0  
**Last Updated:** February 2026  
**Status:** Production Ready with Multi-Agent LangGraph Pipeline  
**Platform:** Cross-platform (macOS, Linux, Windows)  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Overview](#project-overview)
3. [Architecture Overview](#architecture-overview)
4. [Technology Stack](#technology-stack)
5. [Repository Structure](#repository-structure)
6. [Installation & Setup](#installation--setup)
7. [Configuration Guide](#configuration-guide)
8. [Backend Architecture](#backend-architecture)
9. [Frontend Architecture](#frontend-architecture)
10. [API Documentation](#api-documentation)
11. [Database Schema](#database-schema)
12. [Agent Pipeline Details](#agent-pipeline-details)
13. [Game Templates](#game-templates)
14. [Advanced Features](#advanced-features)
15. [Development Workflow](#development-workflow)
16. [Deployment Guide](#deployment-guide)
17. [Troubleshooting](#troubleshooting)
18. [Performance Optimization](#performance-optimization)
19. [Security Considerations](#security-considerations)
20. [Contributing Guidelines](#contributing-guidelines)

---

## Executive Summary

**GamED.AI v2** is an AI-powered educational game generation platform that transforms plain text learning questions into interactive, engaging educational games. The system leverages a sophisticated multi-agent LangGraph architecture with 26+ specialized agents working in orchestrated pipelines to generate high-quality game content.

### Key Capabilities

- **Automated Game Generation**: Convert any educational question into a playable game in seconds
- **Multi-Agent Architecture**: 26+ specialized agents with role-based responsibilities
- **18+ Game Templates**: From simple matching games to complex algorithm visualizations
- **Advanced Diagram Pipeline**: Web search → image segmentation → zone labeling with VLM
- **Quality Assurance**: Schema, semantic, and pedagogical validation with auto-retry logic
- **Human-in-the-Loop**: Admin dashboard for reviewing low-confidence decisions
- **Plug-and-Play Models**: Easy switching between OpenAI, Anthropic, Groq, and local models
- **Cost Optimization**: Free tier support (Groq) with configurable model presets
- **Interactive Frontend**: Drag-and-drop game player with scoring, hints, and state tracking
- **Observable Pipeline**: Detailed agent execution graphs and stage-level observability

---

## Project Overview

### Problem Statement

Educational institutions need high-quality, engaging games to supplement learning but lack the resources (time, expertise, budget) to create them. Existing solutions are:
- Manual and time-consuming
- Expensive to produce
- Difficult to scale to diverse subject matter
- Limited in game type variety

### Solution

GamED.AI automates the entire game creation pipeline using AI, making it:
- **Fast**: Generate games in minutes instead of weeks
- **Scalable**: Handle hundreds of different subject areas
- **Affordable**: Free tier option available; pay-as-you-go for premium quality
- **Flexible**: 18+ game templates covering cognitive levels Bloom's levels 1-6
- **Verifiable**: Multi-stage validation ensures pedagogical correctness

### Target Users

- **K-12 Teachers**: Create supplementary learning games for their classes
- **EdTech Companies**: Rapidly generate game content at scale
- **Curriculum Developers**: Augment existing course materials
- **Content Creators**: Diversify engagement mechanisms
- **Corporate Training**: Generate interactive training scenarios

---

## Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GamED.AI v2 Complete System                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐         ┌──────────────────┐                         │
│  │  Frontend Layer  │         │   Admin Portal   │                         │
│  │  (Next.js React) │         │  (Human Review)  │                         │
│  │  - Game Player   │         │  - QA Dashboard  │                         │
│  │  - Game Gallery  │         │  - Model Config  │                         │
│  │  - Analytics     │         │  - Retry Logic   │                         │
│  └────────┬─────────┘         └────────┬─────────┘                         │
│           │                           │                                     │
│           └───────────────┬───────────┘                                     │
│                           │                                                 │
│                    ┌──────▼──────┐                                          │
│                    │  REST API   │ (FastAPI)                               │
│                    │  (Port 8000)│                                          │
│                    └──────┬──────┘                                          │
│                           │                                                 │
│              ┌────────────┼────────────┐                                    │
│              │            │            │                                    │
│         ┌────▼───┐   ┌───▼────┐   ┌──▼──────┐                             │
│         │ Routes │   │ Services│   │Database │                             │
│         │ Handler│   │ Layer   │   │(SQLite) │                             │
│         └────┬───┘   └───┬────┘   └──┬──────┘                             │
│              │            │           │                                     │
│              └────────────┼───────────┘                                     │
│                           │                                                 │
│              ┌────────────▼───────────┐                                    │
│              │   Agent Pipeline       │ (LangGraph)                        │
│              │  (26+ Specialized      │                                    │
│              │   Agents, 7 Topologies)│                                    │
│              └────────────┬───────────┘                                    │
│                           │                                                 │
│         ┌─────────────────┼─────────────────┐                             │
│         │                 │                 │                             │
│    ┌────▼────┐      ┌────▼────┐     ┌─────▼──┐                          │
│    │  LLM    │      │ External │     │  Image  │                          │
│    │ Providers│      │ Services │     │Processing                          │
│    │ (OpenAI,│      │ (Serper, │     │ (SAM,  │                          │
│    │ Claude, │      │ WebSearch)     │ VLM,   │                          │
│    │ Groq)   │      │          │     │ LLaVA) │                          │
│    └─────────┘      └──────────┘     └────────┘                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Execution Flow

```
Input Question
      │
      ▼
┌─────────────────┐
│ InputEnhancer   │ ─ Extract Bloom's level, subject, difficulty
└────────┬────────┘
         │
         ▼
┌──────────────────────────────┐
│ DomainKnowledgeRetriever     │ ─ Web search for canonical labels
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────┐
│ Router           │ ─ Select optimal game template
└────────┬─────────┘
         │
    ┌────┴────┐
    │          │
    ▼          ▼
LABEL_      OTHER
DIAGRAM     GAMES
    │          │
    ▼          ▼
[Pipeline Branches Continue...]
    │          │
    └────┬─────┘
         │
         ▼
    ┌──────────────┐
    │ GamePlanner  │ ─ Mechanics & scoring
    └────┬─────────┘
         │
         ▼
    ┌──────────────────┐
    │ SceneGenerator   │ ─ Visual design
    └────┬─────────────┘
         │
         ▼
    ┌───────────────────┐
    │ BlueprintGenerator│ ─ JSON blueprint (Template-specific)
    └────┬──────────────┘
         │
         ▼
    ┌─────────────────┐
    │ Validator       │ ─ Schema/Semantic/Pedagogical checks
    └────┬────────────┘
         │
    [Retry if failed, max 3 attempts]
         │
         ▼
    ┌──────────────────┐
    │ AssetGenerator   │ ─ Images/Audio synthesis
    └────┬─────────────┘
         │
         ▼
    COMPLETED GAME
```

---

## Technology Stack

### Backend Technologies

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Framework** | FastAPI | ≥0.104.1 | REST API server, async request handling |
| **Server** | Uvicorn | ≥0.24.0 | ASGI application server |
| **Agent Orchestration** | LangGraph | ≥0.2.40 | Multi-agent pipeline orchestration |
| **Language** | Python | 3.9+ | Primary backend language |
| **LLM Framework** | LangChain | ≥0.3.0 | LLM provider abstraction |
| **Type Validation** | Pydantic | ≥2.9.0 | Request/response validation |
| **Database** | SQLAlchemy | ≥2.0.0 | ORM layer for SQLite |
| **Migrations** | Alembic | ≥1.12.0 | Database schema management |
| **Checkpointing** | langgraph-checkpoint-sqlite | ≥0.1.0 | State persistence for retry logic |

### Frontend Technologies

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Framework** | Next.js | ^15.5.9 | React meta-framework, SSR |
| **UI Library** | React | ^18.3.1 | Component-based UI |
| **Styling** | Tailwind CSS | ^3.4.3 | Utility-first CSS |
| **Drag & Drop** | @dnd-kit | ^6.3.1+ | Drag-and-drop interactions |
| **Flow Graphs** | React Flow | ^11.11.4 | Pipeline visualization |
| **State Management** | Zustand | ^4.5.2 | Client-side state management |
| **Code Highlighting** | react-syntax-highlighter | ^16.1.0 | Code display in games |
| **Type Safety** | TypeScript | ^5.4.5 | Type-safe JavaScript |

### LLM Provider Integrations

| Provider | SDK | Models | Use Case |
|----------|-----|--------|----------|
| **OpenAI** | openai ≥1.3.5 | GPT-4, GPT-4o, GPT-3.5 | High-quality generation |
| **Anthropic** | anthropic ≥0.7.7 | Claude Opus, Sonnet, Haiku | Versatile, cost-effective |
| **Groq** | langchain-groq | Llama 3.3 70B | Fast, free tier (14,400 req/day) |
| **Ollama** | ollama | LLaVA, Mistral, Llama | Local inference, offline |

### External Services

| Service | Purpose | Provider | Cost |
|---------|---------|----------|------|
| **Web Search** | Domain knowledge retrieval | Serper API | Free tier, paid overage |
| **Image Retrieval** | Diagram image search | Serper Images API | Included with Serper |
| **Image Segmentation** | Zone detection in diagrams | SAM3 (local), SAM (local) | Free (local), $0.01/image (API) |
| **Vision Language Model** | Zone labeling | LLaVA (Ollama) | Free (local) |
| **Image Processing** | General CV tasks | OpenCV | Free |
| **Character Recognition** | OCR for labels | EasyOCR | Free |

### Image Generation (Optional)

| Component | Technology | Framework | Purpose |
|-----------|-----------|-----------|---------|
| **Inpainting** | LaMa / Stable Diffusion | Python packages | Smart image inpainting |
| **Object Detection** | YOLO / SAM2 | Local inference | Diagram element detection |
| **Segmentation** | SAM2 / SAM3 | MLX (Apple Silicon) | Zone segmentation for M1/M2 macs |

### Development Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **pytest** | ≥7.4.0 | Unit/integration testing |
| **pytest-asyncio** | ≥0.21.0 | Async test support |
| **Docker** | 20.10+ | Containerization |
| **Docker Compose** | 2.0+ | Multi-service orchestration |
| **Git** | 2.25+ | Version control |
| **npm** | 8.0+ | Node package management |

---

## Repository Structure

### Root Level

```
GamifyAssessment/
├── .cursorrules              # Cursor IDE configuration
├── .gitignore                # Git ignore rules
├── CLAUDE.md                 # Claude AI guidance for code
├── COMMANDS.md               # Quick command reference
├── README.md                 # Project README (559 lines)
├── docker-compose.yml        # Docker service orchestration
├── REPOSITORY_COMPLETE_DOCUMENTATION.md  # This file
├── backend/                  # Backend FastAPI server
├── frontend/                 # Next.js React frontend
├── docs/                     # Comprehensive documentation
├── sandbox/                  # Code verification sandbox
├── old/                      # Legacy/archived code
└── .git/                     # Git repository

```

### Backend Structure

```
backend/
├── .env                      # Environment variables (git ignored)
├── .env.example              # Template for .env
├── config.yaml               # Runtime configuration (models, topologies)
├── requirements.txt          # Python dependencies
├── START_TEST.sh             # Test initialization script
├── test_hierarchical_scene.py # Integration test
├── gamed_ai.db               # SQLite database (generated)
├── app/                      # Main application package
│   ├── __init__.py
│   ├── main.py               # FastAPI app initialization (40+ KB)
│   ├── agents/               # Agent implementations (26+ agents, 1000+ KB)
│   │   ├── __init__.py
│   │   ├── state.py          # State management for agents
│   │   ├── graph.py          # LangGraph pipeline construction
│   │   ├── topologies.py     # Topology definitions (T0-T7)
│   │   ├── blueprint_generator.py
│   │   ├── combined_label_detector.py
│   │   ├── diagram_image_retriever.py
│   │   ├── diagram_image_segmenter.py
│   │   ├── diagram_spec_generator.py
│   │   ├── diagram_svg_generator.py
│   │   ├── diagram_zone_labeler.py
│   │   ├── direct_structure_locator.py
│   │   ├── domain_knowledge_retriever.py
│   │   ├── evaluation.py
│   │   ├── game_planner.py
│   │   ├── image_label_classifier.py
│   │   ├── image_label_remover.py
│   │   ├── input_enhancer.py
│   │   ├── instrumentation.py
│   │   ├── playability_validator.py
│   │   ├── qwen_annotation_detector.py
│   │   ├── qwen_label_remover.py
│   │   ├── qwen_sam_zone_detector.py
│   │   ├── qwen_zone_detector.py
│   │   ├── router.py
│   │   ├── sam3_prompt_generator.py
│   │   ├── scene_generator.py
│   │   ├── scene_stage*.py   # Scene generation stages
│   │   ├── smart_inpainter.py
│   │   ├── smart_zone_detector.py
│   │   ├── story_generator.py
│   │   ├── schemas/          # Pydantic schemas (50+ files)
│   │   └── DEPRECATED.md     # Deprecated agents
│   ├── config/               # Configuration management
│   │   └── models/           # Model configuration presets
│   ├── db/                   # Database layer
│   │   ├── database.py       # SQLAlchemy setup
│   │   ├── models.py         # ORM models
│   │   └── seed_agent_registry.py
│   ├── routes/               # API route handlers
│   │   ├── generate.py       # Game generation endpoint
│   │   ├── observability.py  # Pipeline observability endpoints
│   │   ├── pipeline.py       # Pipeline management endpoints
│   │   ├── questions.py      # Question management endpoints
│   │   ├── review.py         # Human review endpoints
│   │   └── sessions.py       # Session management endpoints
│   ├── services/             # Business logic services
│   │   ├── clip_filtering_service.py
│   │   ├── clip_labeling_service.py
│   │   ├── image_retrieval.py
│   │   ├── inpainting_service.py
│   │   ├── json_repair.py
│   │   ├── lama_inpainting_service.py
│   │   ├── line_detection_service.py
│   │   ├── llm_service.py    # LLM provider abstraction
│   │   ├── mlx_sam3_segmentation.py
│   │   ├── qwen_vl_service.py
│   │   ├── sam3_mlx_service.py
│   │   ├── sam3_zone_service.py
│   │   ├── sam_guided_detection_service.py
│   │   ├── segmentation.py
│   │   ├── stable_diffusion_inpainting.py
│   │   ├── vlm_service.py    # Vision Language Model service
│   │   └── web_search.py     # Web search integration
│   ├── sandbox/              # Code execution sandbox
│   │   └── verification logic
│   └── utils/                # Utility functions
├── logs/                     # Application logs (generated)
├── migrations/               # Database migrations
│   └── add_checkpoint_id.sql
├── pipeline_outputs/         # Generated pipeline artifacts (6 JSON files)
│   ├── 606b1a08-970d-4e1c-b864-1435d168fb33.json
│   ├── hierarchical_scene_test.json
│   ├── T0_state_tracer_*.json
│   ├── T1_state_tracer_*.json
│   └── [other state traces]
├── prompts/                  # LLM prompt templates (100+ files)
│   ├── blueprint_bucket_sort.txt
│   ├── blueprint_label_diagram.txt
│   ├── blueprint_match_pairs.txt
│   ├── blueprint_parameter_playground.txt
│   └── [18+ more game templates]
├── scripts/                  # Development/test scripts
│   ├── demo_pipeline.py      # Single question demo
│   ├── test_all_topologies.py
│   ├── test_label_diagram.py
│   └── [other utility scripts]
├── tests/                    # Unit and integration tests
├── third_party/              # Third-party integrations
└── __pycache__/              # Python bytecode cache

```

### Frontend Structure

```
frontend/
├── .env.local                # Local environment variables
├── .gitignore                # Git ignore rules
├── package.json              # Dependencies and scripts
├── tsconfig.json             # TypeScript configuration
├── next.config.js            # Next.js configuration
├── postcss.config.js         # PostCSS configuration
├── tailwind.config.ts        # Tailwind CSS configuration
├── next-env.d.ts             # Next.js type definitions
├── .next/                    # Build output (generated)
├── node_modules/             # Dependencies (generated)
└── src/
    ├── app/                  # App router pages
    │   ├── page.tsx          # Home page
    │   ├── games/            # Games listing
    │   ├── pipeline/         # Pipeline visualization
    │   ├── layout.tsx        # Root layout
    │   └── [other routes]
    └── components/           # Reusable React components
        ├── GamePlayer.tsx    # Interactive game player
        ├── PipelineGraph.tsx # React Flow visualization
        ├── GameCard.tsx      # Game display card
        └── [other components]

```

### Documentation Structure

```
docs/
├── CHECKPOINTING_COMPLETE_SUMMARY.md          # Checkpointing implementation
├── CHECKPOINTING_IMPLEMENTATION_SUMMARY.md    # Implementation details
├── CHECKPOINTING_INTEGRATION_TEST_RESULTS.md  # Test results
├── CHECKPOINTING_SETUP.md                     # Setup guide
├── CHECKPOINTING_VERIFICATION.md              # Verification steps
├── Diagram_Labelling_Pipeline_Report.md       # Label diagram pipeline
├── GAME_ASSET_GENERATION_MODELS.md            # Asset generation details
├── LLM_DRIVEN_ASSET_GENERATION.md             # LLM-based generation
├── LOCAL_AI_MODELS_M4_RESEARCH.md             # M1/M2 optimization
├── MIGRATION_TESTING_SUMMARY.md               # Migration documentation
├── MODEL_SELECTION_CONFIGURATION_IMPLEMENTATION.md  # Model configuration
├── QUICK_VERIFICATION.md                      # Quick start verification
├── RETRY_FIXES_IMPLEMENTATION_SUMMARY.md      # Retry logic
├── RETRY_FUNCTIONALITY_ANALYSIS.md            # Retry analysis
├── RETRY_SEGMENTER_TEST_SUMMARY.md            # Segmenter retry tests
├── RETRY_SOLUTIONS_RESEARCH.md                # Retry solutions research
├── UPGRADE_AGENTS_MAX_QUALITY.md              # Agent quality upgrades
├── VERIFICATION_GUIDE.md                      # Verification procedures
├── VERIFICATION_SUMMARY.md                    # Verification summary
└── label_diagram/                             # Label diagram examples
    └── [SVG and image files]

```

### Sandbox Structure

```
sandbox/
├── Dockerfile                # Sandbox container definition
└── test-harness/             # Test execution environment
    └── [test execution scripts]

```

### Old/Legacy Structure

```
old/
├── ALL_PROMPTS.md            # Archive of all prompts
├── CLAUDE.md                 # Legacy Claude guidance
├── GAME_QUALITY_ANALYSIS.md  # Quality analysis
├── IMAGE_GENERATION_PLAN.md  # Image generation planning
├── IMPLEMENTATION_SUMMARY.md # Implementation notes
├── ISSUE_ANALYSIS.md         # Issue tracking
├── QUICK_START.md            # Legacy quick start
├── README.md                 # Legacy README
├── SESSION_SUMMARY.md        # Session notes
├── SETUP.md                  # Legacy setup
├── Technical_Documentation.md # Technical docs
├── backend/                  # Previous version backend
├── frontend/                 # Previous version frontend
└── Ashish_games/             # Legacy game files

```

---

## Installation & Setup

### Prerequisites

- **Python**: 3.9, 3.10, 3.11, or 3.12
- **Node.js**: 18.x or 20.x
- **npm**: 9.0+
- **Git**: 2.25+
- **macOS/Linux/Windows**: Tested on all platforms

### Step 1: Clone Repository

```bash
git clone https://github.com/shivena99/GamifyAssessment.git
cd GamifyAssessment
```

### Step 2: Backend Setup

```bash
# Navigate to backend
cd backend

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import langgraph; print(langgraph.__version__)"
```

### Step 3: Configure Environment

Create `backend/.env` file:

```bash
# LLM Provider Selection (choose one primary)
# Option 1: Groq (FREE - Recommended)
GROQ_API_KEY=gsk_your-groq-key-here
AGENT_CONFIG_PRESET=groq_free

# Option 2: OpenAI
OPENAI_API_KEY=sk-your-openai-key-here
AGENT_CONFIG_PRESET=balanced

# Option 3: Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
AGENT_CONFIG_PRESET=balanced

# External Services
SERPER_API_KEY=your-serper-key-here  # For web search

# Optional: Local Model Configuration
USE_LOCAL_MODELS=false
OLLAMA_BASE_URL=http://localhost:11434

# Optional: Image Generation
USE_IMAGE_DIAGRAMS=true
SAM_MODEL_PATH=/path/to/sam_vit_b.pth
VLM_MODEL=llava:latest

# Database
DATABASE_URL=sqlite:///./gamed_ai.db

# Server Configuration
ENVIRONMENT=development
DEBUG=true
```

**Get API Keys:**
- **Groq**: https://console.groq.com (free tier, 14,400 req/day)
- **OpenAI**: https://platform.openai.com/account/api-keys
- **Anthropic**: https://console.anthropic.com
- **Serper**: https://serper.dev

### Step 4: Frontend Setup

```bash
# Navigate to frontend
cd ../frontend

# Install dependencies
npm install

# Create local environment (optional)
cp .env.example .env.local

# Configure if needed
cat .env.local
# Should have: NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 5: Run Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Backend will start at: **http://localhost:8000**
- API Documentation: **http://localhost:8000/docs**
- Health Check: **http://localhost:8000/health**

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Frontend will start at: **http://localhost:3000**

### Step 6: Verify Installation

```bash
# Backend API
curl http://localhost:8000/health

# Generate test game
curl -X POST "http://localhost:8000/api/generate?question_text=Explain%20binary%20search"

# Frontend
open http://localhost:3000
```

### Using Docker Compose (Optional)

```bash
# Build and start all services
docker-compose up --build

# Services will be available at:
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## Configuration Guide

### Model Configuration

The system uses **Pydantic-based configuration** with presets for different use cases:

#### Preset Configurations

**`groq_free`** (Recommended - $0)
```yaml
Primary Model: Llama 3.3 70B (Groq)
Cost per Run: ~$0
Best For: Development, testing, cost-sensitive production
```

**`cost_optimized`** (~$0.01-0.02/run)
```yaml
Models: claude-haiku, gpt-4o-mini
Cost per Run: ~$0.01-0.02
Best For: Production, moderate quality requirements
```

**`balanced`** (~$0.05-0.10/run)
```yaml
Models: claude-sonnet, gpt-4-turbo
Cost per Run: ~$0.05-0.10
Best For: Production, high quality requirements
```

**`quality_optimized`** (~$0.20-0.50/run)
```yaml
Models: claude-opus, gpt-4o
Cost per Run: ~$0.20-0.50
Best For: Mission-critical content, maximum quality
```

**`anthropic_only`** (Claude models only)
**`openai_only`** (GPT models only)

#### Switch Presets

```bash
# Via environment variable
export AGENT_CONFIG_PRESET=groq_free
PYTHONPATH=. uvicorn app.main:app --reload

# Via .env
AGENT_CONFIG_PRESET=balanced
```

#### Per-Agent Override

```bash
# Override specific agents
export AGENT_MODEL_BLUEPRINT_GENERATOR=gpt-4o
export AGENT_MODEL_STORY_GENERATOR=claude-opus
export AGENT_TEMPERATURE_STORY_GENERATOR=0.9

# Temperature control (0.0-1.0)
export AGENT_TEMPERATURE_ROUTER=0.3  # More deterministic
export AGENT_TEMPERATURE_STORY_GENERATOR=0.9  # More creative
```

### Topology Configuration

Topologies define the pipeline structure:

```yaml
# config.yaml
topologies:
  T0:
    name: "Sequential Baseline"
    description: "Linear execution without verification"
    validation_loops: 0
    retry_enabled: false
    recommended: false

  T1:
    name: "Sequential Validated"
    description: "Linear with validators and retry"
    validation_loops: 1
    max_retries: 3
    retry_enabled: true
    recommended: true  # Production default

  T2:
    name: "Actor-Critic"
    description: "Generator + Evaluator with feedback"
    validation_loops: 1
    max_retries: 3
    recommended: false

  T4:
    name: "Self-Refine"
    description: "Iterative self-improvement"
    validation_loops: 3
    max_retries: 3
    recommended: false

  T5:
    name: "Multi-Agent Debate"
    description: "Multiple agents debate, judge selects"
    validation_loops: 2
    max_retries: 3
    recommended: false

  T7:
    name: "Reflection + Memory"
    description: "Learn from past failures"
    validation_loops: 2
    max_retries: 5
    memory_enabled: true
    recommended: false
```

#### Run with Specific Topology

```bash
export TOPOLOGY=T1
PYTHONPATH=. uvicorn app.main:app --reload

# Via API
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"question_text": "...", "topology": "T1"}'
```

---

## Backend Architecture

### Application Structure

```
FastAPI Application (main.py)
├── Middleware
│   ├── CORS handling
│   ├── Error handling
│   ├── Logging
│   └── Request tracking
├── Routes
│   ├── /api/generate (Game generation)
│   ├── /api/questions (Question CRUD)
│   ├── /api/games (Game retrieval)
│   ├── /api/pipeline (Pipeline ops)
│   ├── /api/observability (Observability)
│   ├── /api/review (Human review)
│   └── /health (Health check)
└── Services
    ├── LLM Service (Provider abstraction)
    ├── Pipeline Service (Graph orchestration)
    ├── Database Service (ORM operations)
    └── External Integrations (Serper, Ollama, etc.)
```

### Request Lifecycle

```
1. Client Request
   ↓
2. FastAPI Route Handler (/api/generate)
   ↓
3. Input Validation (Pydantic)
   ↓
4. Database Recording (pipeline_run created)
   ↓
5. Agent Pipeline Initialization
   ├─ Load topology configuration
   ├─ Initialize state object
   ├─ Build LangGraph from topology
   └─ Setup checkpointing
   ↓
6. Pipeline Execution
   ├─ Agent 1: InputEnhancer
   ├─ Agent 2: DomainKnowledgeRetriever
   ├─ Agent 3: Router
   ├─ Branch-specific agents...
   ├─ Validators (with retry on failure)
   └─ Output aggregation
   ↓
7. Checkpoint Saving (SQLite)
   ↓
8. Response Formatting
   ↓
9. Database Update (pipeline_run status)
   ↓
10. Response to Client
```

### Core Components

#### 1. **State Management** (`agents/state.py`)

Defines the shared state object passed through agent pipeline:

```python
class PipelineState(BaseModel):
    # Input
    question_text: str
    subject: str = None
    bloom_level: int = None
    difficulty: str = None
    
    # Router output
    selected_template: str = None
    template_confidence: float = None
    
    # Generator outputs
    blueprint: dict = None
    scene_spec: dict = None
    game_assets: dict = None
    
    # Validation results
    validation_passed: bool = False
    validation_errors: List[str] = []
    
    # Metadata
    pipeline_id: str
    timestamp: datetime
    agent_traces: List[dict] = []  # For observability
```

#### 2. **Graph Construction** (`agents/graph.py`)

Builds LangGraph pipeline:

```python
def build_graph(topology: str = "T1"):
    """Construct LangGraph based on topology"""
    graph = StateGraph(PipelineState)
    
    # Add nodes
    graph.add_node("input_enhancer", input_enhancer_agent)
    graph.add_node("router", router_agent)
    graph.add_node("game_planner", game_planner_agent)
    graph.add_node("blueprint_generator", blueprint_generator_agent)
    graph.add_node("validator", validator_agent)
    
    # Add edges (routing based on template)
    graph.add_edge("input_enhancer", "router")
    graph.add_conditional_edges(
        "router",
        route_by_template,
        {
            "label_diagram": "diagram_pipeline",
            "other": "game_planner"
        }
    )
    
    # Conditional edges for retry
    graph.add_conditional_edges(
        "validator",
        should_retry,
        {
            "retry": "blueprint_generator",
            "proceed": "asset_generator",
            "fail": "error_handler"
        }
    )
    
    return graph.compile(checkpointer=checkpointer)
```

#### 3. **Agent Orchestration** (`agents/topologies.py`)

Defines 7 topology patterns:

| Topology | Structure | Use Case |
|----------|-----------|----------|
| **T0** | Linear, no validation | Baseline, testing |
| **T1** | Linear + validators | Production default |
| **T2** | Generator → Critic → Feedback | Quality-critical |
| **T4** | Self-critique loop | Iterative refinement |
| **T5** | Multiple agents + judge | Consensus quality |
| **T7** | Feedback loop + memory | Learning from failure |

#### 4. **LLM Service** (`services/llm_service.py`)

Provider abstraction layer:

```python
class LLMService:
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.model = self._load_config(provider)
    
    async def generate(self, prompt: str) -> str:
        """Provider-agnostic generation"""
        if self.provider == "openai":
            return await self._call_openai(prompt)
        elif self.provider == "anthropic":
            return await self._call_anthropic(prompt)
        elif self.provider == "groq":
            return await self._call_groq(prompt)
        # ... other providers
    
    async def _call_openai(self, prompt: str) -> str:
        """OpenAI API call"""
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
```

### Database Layer

#### SQLAlchemy Models (`db/models.py`)

```python
class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    
    id: str = Column(String, primary_key=True)
    question_id: str = Column(String, ForeignKey("questions.id"))
    topology: str = Column(String)
    started_at: datetime = Column(DateTime)
    completed_at: datetime = Column(DateTime, nullable=True)
    status: str = Column(String)  # pending, running, completed, failed
    result: dict = Column(JSON)
    
    # Checkpointing for retry
    last_checkpoint_stage: str = Column(String)
    checkpoint_data: dict = Column(JSON)

class Question(Base):
    __tablename__ = "questions"
    
    id: str = Column(String, primary_key=True)
    text: str = Column(String)
    subject: str = Column(String)
    created_at: datetime = Column(DateTime)

class Game(Base):
    __tablename__ = "games"
    
    id: str = Column(String, primary_key=True)
    pipeline_run_id: str = Column(String, ForeignKey("pipeline_runs.id"))
    template: str = Column(String)
    blueprint: dict = Column(JSON)
    assets: dict = Column(JSON)
    created_at: datetime = Column(DateTime)
```

---

## Frontend Architecture

### Technology Stack

- **Framework**: Next.js 15 (App Router)
- **UI**: React 18 with TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand (minimal global state)
- **Visualization**: React Flow (pipeline graphs)
- **Interactions**: dnd-kit (drag-and-drop)

### Page Structure

#### 1. **Home Page** (`src/app/page.tsx`)

```
┌─────────────────────────────┐
│     GamED.AI Home          │
├─────────────────────────────┤
│  Welcome                    │
│  Quick Start Instructions   │
│  Feature Highlights         │
├─────────────────────────────┤
│  [Generate New Game Button] │
│  Question Input Field       │
│  Subject Selection          │
│  Difficulty Setting         │
└─────────────────────────────┘
```

**Features:**
- Question text input
- Subject/topic selection
- Difficulty level picker
- Template preference (optional)
- Generate button

#### 2. **Games Gallery** (`src/app/games/page.tsx`)

```
┌──────────────────────────────────┐
│     My Games                     │
├──────────────────────────────────┤
│  [Filter] [Sort] [Search]        │
├──────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐     │
│  │ Game 1   │  │ Game 2   │     │
│  │ Template │  │ Template │     │
│  │ Play ▶   │  │ Play ▶   │     │
│  └──────────┘  └──────────┘     │
│  ...                             │
└──────────────────────────────────┘
```

**Features:**
- Game cards with thumbnails
- Play button to load game
- Template indication
- Creation date
- Filtering/sorting

#### 3. **Game Player** (`src/components/GamePlayer.tsx`)

```
┌────────────────────────────────────┐
│  [Back] Game Title                 │
├────────────────────────────────────┤
│  ┌──────────────────────────────┐ │
│  │                              │ │
│  │     Interactive Game Area    │ │
│  │  (Template-specific UI)      │ │
│  │                              │ │
│  └──────────────────────────────┘ │
├────────────────────────────────────┤
│  Score: 100/100  [Hint] [Submit]   │
└────────────────────────────────────┘
```

**Supported Game Types:**
- Matching pairs (drag-and-drop)
- Multiple choice (click select)
- Bucket sort (drag items to categories)
- Code debugging (edit code blocks)
- Diagram labeling (click to label)
- True/False (toggle)
- Fill in the blank (text input)
- And 11+ more templates

#### 4. **Pipeline Visualization** (`src/app/pipeline/runs/[id]/page.tsx`)

```
┌──────────────────────────────────┐
│  Pipeline Run: {id}              │
├──────────────────────────────────┤
│  Status: Completed ✓             │
│  Duration: 12s                   │
│  Template: Label Diagram         │
├──────────────────────────────────┤
│  ┌────────────────────────────┐ │
│  │   React Flow Graph         │ │
│  │  (Agent DAG visualization) │ │
│  │                            │ │
│  │  InputEnhancer             │ │
│  │         ↓                  │ │
│  │      Router                │ │
│  │      ↙    ↘               │ │
│  │   Diagram  Other           │ │
│  │         ↘  ↙              │ │
│  │    GamePlanner             │ │
│  │         ↓                  │ │
│  │    Validator               │ │
│  └────────────────────────────┘ │
├──────────────────────────────────┤
│  Agent Details (click on node):  │
│  - Execution time               │
│  - Input/Output                 │
│  - Token usage                  │
│  - Error messages               │
└──────────────────────────────────┘
```

**Features:**
- Interactive React Flow graph
- Node click for detailed info
- Timeline view of execution
- Error highlighting
- Performance metrics

### Component Architecture

```
src/components/
├── GamePlayer.tsx           # Main game rendering
├── PipelineGraph.tsx        # React Flow visualization
├── GameCard.tsx             # Game list item
├── QuestionInput.tsx        # Question form
├── SubjectSelector.tsx      # Subject/topic picker
├── DifficultySlider.tsx     # Difficulty selector
├── TemplateSelector.tsx     # Game template picker
├── LoadingSpinner.tsx       # Loading animation
├── ErrorBoundary.tsx        # Error handling
├── Header.tsx               # Navigation header
├── Footer.tsx               # Page footer
├── Modal.tsx                # Dialog component
└── CodeHighlight.tsx        # Code display in games
```

### State Management (Zustand)

```typescript
// Global state for game playing
const useGameStore = create((set) => ({
  // Game state
  currentGame: null,
  gameScore: 0,
  userAnswers: [],
  
  // Actions
  loadGame: (gameId) => set({ currentGame: gameId }),
  updateScore: (score) => set({ gameScore: score }),
  submitAnswer: (answer) => set(state => ({
    userAnswers: [...state.userAnswers, answer]
  })),
  
  // Reset
  resetGame: () => set({
    currentGame: null,
    gameScore: 0,
    userAnswers: []
  })
}));
```

---

## API Documentation

### Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.gamed.ai` (configurable)

### Authentication

Currently no authentication required. Production deployment should add:
- JWT bearer tokens
- API key headers
- OAuth integration

### Endpoints

#### 1. **Health Check**

```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "2.0.0",
  "database": "connected",
  "timestamp": "2026-02-04T10:00:00Z"
}
```

---

#### 2. **Generate Game**

```http
POST /api/generate
Content-Type: application/json

{
  "question_text": "Explain how binary search works",
  "subject": "Computer Science",
  "bloom_level": 3,
  "difficulty": "intermediate",
  "template": null,
  "topology": "T1"
}
```

**Response (202 Accepted):**
```json
{
  "process_id": "uuid-here",
  "status": "queued",
  "estimated_time_seconds": 30,
  "created_at": "2026-02-04T10:00:00Z"
}
```

**Parameters:**
- `question_text` (required): Learning question/prompt
- `subject` (optional): Subject area
- `bloom_level` (optional): 1-6 cognitive level
- `difficulty` (optional): "easy", "intermediate", "hard"
- `template` (optional): Specific template to use
- `topology` (optional): T0, T1, T2, T4, T5, T7 (default: T1)

**Status Codes:**
- `202`: Request accepted, processing started
- `400`: Invalid input
- `500`: Server error

---

#### 3. **Check Generation Status**

```http
GET /api/generate/{process_id}/status
```

**Response:**
```json
{
  "process_id": "uuid-here",
  "status": "in_progress",
  "current_stage": "blueprint_generator",
  "progress_percent": 45,
  "stages_completed": ["input_enhancer", "router", "game_planner"],
  "current_stage_start": "2026-02-04T10:00:10Z",
  "estimated_time_remaining_seconds": 15
}
```

**Status Values:**
- `queued`: Waiting to start
- `in_progress`: Currently running
- `completed`: Successfully finished
- `failed`: Error occurred
- `cancelled`: User cancelled

---

#### 4. **Retrieve Generated Game**

```http
GET /api/generate/{process_id}/result
```

**Response:**
```json
{
  "game_id": "game-uuid",
  "question": "Explain how binary search works",
  "template": "algorithm_visualization",
  "blueprint": {
    "title": "Binary Search Walkthrough",
    "description": "Interactive algorithm visualization",
    "mechanics": {
      "interaction_type": "drag_and_drop",
      "objective": "Arrange steps in correct order"
    }
  },
  "assets": {
    "images": ["url1", "url2"],
    "audio": ["audio-url"],
    "interactive_elements": [...]
  },
  "metadata": {
    "created_at": "2026-02-04T10:00:30Z",
    "generation_time_ms": 30000,
    "model_used": "gpt-4-turbo",
    "cost_cents": 5
  }
}
```

---

#### 5. **List Games**

```http
GET /api/games?limit=10&offset=0&filter=recent
```

**Response:**
```json
{
  "games": [
    {
      "id": "game-uuid",
      "title": "Generated from question",
      "template": "matching_pairs",
      "created_at": "2026-02-04T10:00:30Z",
      "pipeline_run_id": "run-uuid"
    }
  ],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

---

#### 6. **Get Pipeline Run Details**

```http
GET /api/observability/runs/{run_id}
```

**Response:**
```json
{
  "id": "run-uuid",
  "question_id": "question-uuid",
  "topology": "T1",
  "status": "completed",
  "started_at": "2026-02-04T10:00:00Z",
  "completed_at": "2026-02-04T10:00:30Z",
  "stages": [
    {
      "name": "input_enhancer",
      "status": "completed",
      "duration_ms": 2000,
      "input": { "question": "..." },
      "output": { "subject": "CS", "bloom_level": 3 }
    },
    {
      "name": "router",
      "status": "completed",
      "duration_ms": 1500,
      "input": { ... },
      "output": { "template": "label_diagram", "confidence": 0.95 }
    }
  ],
  "total_duration_ms": 30000,
  "token_usage": {
    "prompt_tokens": 2000,
    "completion_tokens": 500,
    "total_tokens": 2500,
    "cost_cents": 5
  }
}
```

---

#### 7. **Retry from Failed Stage**

```http
POST /api/observability/runs/{run_id}/retry
Content-Type: application/json

{
  "from_stage": "blueprint_generator",
  "use_new_model": false
}
```

**Response:**
```json
{
  "new_run_id": "new-run-uuid",
  "status": "queued",
  "from_stage": "blueprint_generator",
  "message": "Retry queued, will resume from blueprint_generator"
}
```

---

#### 8. **Submit Human Review**

```http
POST /api/review/submit
Content-Type: application/json

{
  "run_id": "run-uuid",
  "approved": true,
  "feedback": "Game mechanics are clear",
  "suggested_changes": [
    "Increase difficulty level",
    "Add more hints"
  ]
}
```

**Response:**
```json
{
  "review_id": "review-uuid",
  "run_id": "run-uuid",
  "status": "saved",
  "timestamp": "2026-02-04T10:05:00Z"
}
```

---

### WebSocket Endpoints (Optional)

For real-time pipeline updates:

```javascript
// Connect
const ws = new WebSocket('ws://localhost:8000/ws/pipeline/{process_id}');

// Listen for updates
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  // {
  //   "event": "stage_completed",
  //   "stage": "input_enhancer",
  //   "progress": 20,
  //   "output": {...}
  // }
};
```

---

## Database Schema

### Tables

#### 1. **pipeline_runs**

Tracks all game generation pipeline executions.

```sql
CREATE TABLE pipeline_runs (
  id TEXT PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES questions(id),
  topology TEXT NOT NULL,  -- T0, T1, T2, T4, T5, T7
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  status TEXT NOT NULL,  -- pending, running, completed, failed
  result JSON,  -- Final game blueprint and metadata
  error_message TEXT,
  last_checkpoint_stage TEXT,  -- For resuming from failure
  checkpoint_data JSON,  -- Serialized pipeline state
  CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. **questions**

Stores user questions/prompts.

```sql
CREATE TABLE questions (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  subject TEXT,
  bloom_level INTEGER,  -- 1-6
  difficulty TEXT,  -- easy, intermediate, hard
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP
);
```

#### 3. **games**

Stores generated games.

```sql
CREATE TABLE games (
  id TEXT PRIMARY KEY,
  pipeline_run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
  template TEXT NOT NULL,
  blueprint JSON NOT NULL,  -- Game configuration
  assets JSON,  -- Images, audio, etc.
  metadata JSON,  -- Extra information
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. **pipeline_stages**

Detailed tracking of each stage in pipeline execution.

```sql
CREATE TABLE pipeline_stages (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
  stage_name TEXT NOT NULL,
  status TEXT NOT NULL,
  input_data JSON,
  output_data JSON,
  error_message TEXT,
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  duration_ms INTEGER,
  model_used TEXT,
  tokens_used INTEGER,
  cost_cents DECIMAL
);
```

#### 5. **human_reviews**

Tracks human review feedback.

```sql
CREATE TABLE human_reviews (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
  approved BOOLEAN,
  feedback TEXT,
  suggested_changes JSON,
  reviewer_id TEXT,  -- User who reviewed
  reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 6. **agent_registry**

Stores agent definitions for dynamic loading.

```sql
CREATE TABLE agent_registry (
  id TEXT PRIMARY KEY,
  agent_name TEXT NOT NULL UNIQUE,
  agent_type TEXT,  -- Generator, Validator, Router, etc.
  model_config JSON,
  is_active BOOLEAN DEFAULT TRUE,
  version TEXT,
  created_at TIMESTAMP
);
```

### Relationships

```
questions (1) ──→ (M) pipeline_runs
                      ├─→ (M) pipeline_stages
                      ├─→ (M) human_reviews
                      └─→ (1) games
```

### Indexes

```sql
-- Performance optimization
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_created ON pipeline_runs(created_at DESC);
CREATE INDEX idx_questions_subject ON questions(subject);
CREATE INDEX idx_games_template ON games(template);
CREATE INDEX idx_pipeline_stages_run_id ON pipeline_stages(run_id);
```

---

## Agent Pipeline Details

### Agent Inventory (26+ Agents)

#### Core Agents

| # | Agent Name | File | Purpose | Input | Output |
|---|-----------|------|---------|-------|--------|
| 1 | **InputEnhancer** | input_enhancer.py | Extract cognitive level, subject, difficulty | Question text | Enhanced metadata |
| 2 | **DomainKnowledgeRetriever** | domain_knowledge_retriever.py | Web search for domain knowledge | Subject, concepts | Domain labels, context |
| 3 | **Router** | router.py | Select optimal game template | Enhanced question | Template selection, confidence |
| 4 | **GamePlanner** | game_planner.py | Plan game mechanics | Template, subject | Mechanics, rules, scoring |
| 5 | **SceneGenerator** | scene_generator.py | Visual design specification | Mechanics, template | Scene layout spec |
| 6 | **BlueprintGenerator** | blueprint_generator.py | Template-specific JSON | Mechanics, scene | Game blueprint JSON |
| 7 | **BlueprintValidator** | evaluation.py | Validate blueprint | Blueprint JSON | Validation results, errors |
| 8 | **CodeGenerator** | (embedded in blueprint) | React component templates | Blueprint | Code snippets |
| 9 | **StoryGenerator** | story_generator.py | Narrative content | Mechanics, theme | Story script, dialogue |
| 10 | **AssetGenerator** | (embedded in pipeline) | Image/audio generation | Scene spec, blueprint | Asset URLs |

#### Diagram Pipeline Agents

| # | Agent Name | File | Purpose | Input | Output |
|----|-----------|------|---------|-------|--------|
| 11 | **DiagramImageRetriever** | diagram_image_retriever.py | Search for diagram images | Topic, query | Image URLs |
| 12 | **DiagramImageSegmenter** | diagram_image_segmenter.py | Extract zones from image | Image | Segmented zones, bounding boxes |
| 13 | **DiagramZoneLabeler** | diagram_zone_labeler.py | Identify labels for zones | Image + zones, VLM | Zone labels |
| 14 | **DiagramSpecGenerator** | diagram_spec_generator.py | SVG specification | Blueprint, zones, labels | SVG XML spec |
| 15 | **DiagramSpecValidator** | diagram_spec_generator.py | Validate SVG spec | SVG spec | Validation result |
| 16 | **DiagramSvgGenerator** | diagram_svg_generator.py | Render interactive SVG | SVG spec | SVG output, HTML |

#### Specialized Agents

| # | Agent Name | File | Purpose |
|----|-----------|------|---------|
| 17 | **QwenAnnotationDetector** | qwen_annotation_detector.py | Detect annotations with Qwen VLM |
| 18 | **QwenLabelRemover** | qwen_label_remover.py | Remove existing labels |
| 19 | **QwenZoneDetector** | qwen_zone_detector.py | Zone detection with Qwen |
| 20 | **QwenSamZoneDetector** | qwen_sam_zone_detector.py | Combined Qwen + SAM detection |
| 21 | **ImageLabelClassifier** | image_label_classifier.py | Classify detected labels |
| 22 | **ImageLabelRemover** | image_label_remover.py | Clean up image labels |
| 23 | **SmartZoneDetector** | smart_zone_detector.py | Intelligent zone detection |
| 24 | **SmartInpainter** | smart_inpainter.py | Smart image inpainting |
| 25 | **DirectStructureLocator** | direct_structure_locator.py | Locate structures directly |
| 26 | **Sam3PromptGenerator** | sam3_prompt_generator.py | Generate SAM3 prompts |
| 27 | **PlayabilityValidator** | playability_validator.py | Validate game playability |

### Agent Execution Order by Topology

#### T0 (Sequential Baseline)
```
InputEnhancer → DomainKnowledgeRetriever → Router → [Template Branch] → GamePlanner 
→ SceneGenerator → BlueprintGenerator → AssetGenerator → OUTPUT
```

#### T1 (Sequential Validated - **PRODUCTION DEFAULT**)
```
InputEnhancer → DomainKnowledgeRetriever → Router → [Template Branch] 
→ GamePlanner → SceneGenerator → BlueprintGenerator → [Validator]
                                                           ↓
                                                    [Retry up to 3x]
                                                           ↓
                                                    → AssetGenerator → OUTPUT
```

#### T2 (Actor-Critic)
```
InputEnhancer → Router → GamePlanner (Generator)
                         ↓
                 SceneGenerator
                 ↓
            BlueprintGenerator (Actor)
                 ↓
            Critic Agent → Feedback Loop
                 ↓
            OUTPUT
```

#### T4 (Self-Refine)
```
InputEnhancer → Router → GamePlanner → SceneGenerator 
→ BlueprintGenerator → SelfCritique → Refinement (Loop 3x) → OUTPUT
```

#### T5 (Multi-Agent Debate)
```
InputEnhancer → Router → [Proposer 1] → Blueprint A
                         [Proposer 2] → Blueprint B
                         [Proposer 3] → Blueprint C
                              ↓
                        Judge Agent → Select Best
                              ↓
                           OUTPUT
```

#### T7 (Reflection + Memory)
```
InputEnhancer → Router → GamePlanner → MemoryBank → SceneGenerator
            ↑                                            ↓
            └─── Learn from Past Failures ──← BlueprintGenerator → Validator
```

### Agent Configuration

Each agent has configurable:
- **Model**: Which LLM to use
- **Temperature**: Creativity level (0.0-1.0)
- **Max Tokens**: Output length limit
- **Retry Count**: How many times to retry on failure
- **Timeout**: Execution time limit

```python
# agents/schemas/agent_config.py
class AgentConfig(BaseModel):
    agent_id: str
    model: str  # e.g., "gpt-4-turbo", "claude-sonnet"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout_seconds: int = 60
    retry_count: int = 3
    system_prompt_template: str
    provider: str  # openai, anthropic, groq
```

### Instrumentation & Tracing

Each agent records:

```python
{
  "agent_name": "InputEnhancer",
  "started_at": "2026-02-04T10:00:00Z",
  "completed_at": "2026-02-04T10:00:02Z",
  "duration_ms": 2000,
  "input": {
    "question_text": "...",
    "word_count": 50
  },
  "output": {
    "bloom_level": 3,
    "subject": "Computer Science",
    "difficulty": "intermediate"
  },
  "model_used": "claude-sonnet",
  "tokens": {
    "prompt": 150,
    "completion": 80,
    "total": 230
  },
  "cost_cents": 0.5,
  "status": "success",
  "error": null
}
```

---

## Game Templates

### Overview

18+ templates covering Bloom's levels 1-6:

```
Level 1 (Remember):
├─ MultipleChoice
├─ TrueFalse
├─ MatchingPairs
└─ FillInTheBlank

Level 2 (Understand):
├─ Conceptual Mapping
├─ DiagramLabeling
└─ TermDefinition

Level 3 (Apply):
├─ ProblemSolving
├─ CodeDebugging
├─ AlgorithmVisualization
└─ DataStructureManipulation

Level 4 (Analyze):
├─ ComponentComparison
├─ CriticalAnalysis
└─ CauseEffectDiagram

Level 5 (Evaluate):
├─ DecisionMaking
├─ ArgumentAnalysis
└─ QualityJudgment

Level 6 (Create):
├─ DesignChallenge
├─ ParameterPlayground
└─ ProjectBuilding
```

### Template Schemas

Each template has a Pydantic schema (`agents/schemas/`):

#### 1. **MultipleChoice**

```python
class MultipleChoiceBlueprint(BaseModel):
    question: str
    options: List[str]
    correct_option_index: int
    explanation: str
    difficulty: str
    bloom_level: int
    
    class Config:
        template_name = "multiple_choice"
        file_name = "blueprint_multiple_choice.txt"
```

#### 2. **MatchingPairs**

```python
class MatchingPairsBlueprint(BaseModel):
    title: str
    pairs: List[Pair]
    shuffled_targets: List[str]
    num_columns: int = 2
    
    class Pair(BaseModel):
        source: str
        target: str
        explanation: str
```

#### 3. **DiagramLabeling**

```python
class DiagramLabelingBlueprint(BaseModel):
    title: str
    diagram_url: str
    zones: List[Zone]
    instructions: str
    feedback_type: str  # immediate, delayed, none
    
    class Zone(BaseModel):
        zone_id: str
        bounding_box: BoundingBox
        correct_labels: List[str]
        hints: List[str]
        explanation: str
```

#### 4. **CodeDebugging**

```python
class CodeDebuggingBlueprint(BaseModel):
    title: str
    buggy_code: str
    language: str
    bugs: List[Bug]
    test_cases: List[TestCase]
    hints: List[str]
    
    class Bug(BaseModel):
        line_number: int
        bug_description: str
        fix: str
        explanation: str
```

#### 5. **AlgorithmVisualization**

```python
class AlgorithmVisualizationBlueprint(BaseModel):
    title: str
    algorithm: str
    steps: List[Step]
    animation_config: AnimationConfig
    
    class Step(BaseModel):
        step_number: int
        description: str
        visualization_state: dict
        explanation: str
```

---

## Advanced Features

### 1. **Checkpointing & Retry Logic**

The pipeline supports resuming from failed stages:

```bash
# Automatic retry on validation failure
# Max 3 attempts per stage
# Saves checkpoint after each stage
```

**Implementation:**

```python
# langgraph-checkpoint-sqlite integration
checkpointer = SqliteSaver(db_path="backend/gamed_ai.db")

compiled_graph = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["validator"]  # Pause before validation
)

# Resume from checkpoint
config = {"configurable": {"thread_id": "run_123"}}
result = compiled_graph.invoke(state, config=config)
```

### 2. **Human-in-the-Loop Verification**

For low-confidence outputs:

```python
# If router confidence < 0.7, pause for review
if template_confidence < 0.7:
    graph.add_node("human_review", review_node)
    graph.add_conditional_edges(
        "router",
        lambda state: "human_review" if state.template_confidence < 0.7 else "next",
        {"human_review": "review", "next": "game_planner"}
    )
```

**Review Dashboard:**
- List low-confidence decisions
- Override agent decisions
- Approve/reject results
- Provide feedback for model improvement

### 3. **Cost Tracking**

Detailed cost analysis per run:

```python
# Track tokens and costs
run_costs = {
    "input_enhancer": {"tokens": 150, "cost_cents": 0.1},
    "router": {"tokens": 200, "cost_cents": 0.2},
    "game_planner": {"tokens": 500, "cost_cents": 0.5},
    "blueprint_generator": {"tokens": 800, "cost_cents": 1.0},
    "total": {
        "tokens": 1650,
        "cost_cents": 1.8
    }
}
```

### 4. **Multi-Language Support**

Pipeline can generate games in multiple languages:

```python
# Add language parameter
generate_game(
    question="Explain binary search",
    language="es",  # Spanish
    subject="Computer Science"
)
```

### 5. **Asset Generation**

Optional image/audio synthesis:

```python
# For diagram templates, retrieve images
service = ImageRetrievalService(api_key=SERPER_KEY)
images = service.search("binary search tree diagram")

# For story-driven games, generate audio
audio = TTS_Service.synthesize(text="Welcome to the game!")
```

### 6. **Analytics & Observability**

Detailed pipeline metrics:

```python
# Query pipeline statistics
GET /api/observability/stats?period=7d

{
  "total_runs": 450,
  "success_rate": 94.2,
  "average_duration_ms": 28000,
  "cost_per_run_cents": 2.1,
  "most_used_template": "matching_pairs",
  "most_used_model": "claude-sonnet",
  "errors_last_24h": 12
}
```

---

## Development Workflow

### Local Development Setup

```bash
# Clone and setup
git clone https://github.com/shivena99/GamifyAssessment.git
cd GamifyAssessment

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

# Start services
# Terminal 1
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

### Testing

#### Backend Tests

```bash
# Run all tests
cd backend
PYTHONPATH=. pytest tests/ -v

# Run specific test
PYTHONPATH=. pytest tests/test_input_enhancer.py -v

# Run with coverage
PYTHONPATH=. pytest tests/ --cov=app --cov-report=html

# Test specific topology
PYTHONPATH=. python scripts/test_all_topologies.py --topology T1
```

#### Frontend Tests

```bash
cd frontend

# Run tests (when configured)
npm test

# Type check
npx tsc --noEmit

# Lint
npm run lint
```

#### Integration Tests

```bash
# Test entire pipeline
cd backend
PYTHONPATH=. python scripts/demo_pipeline.py

# Test with real question
PYTHONPATH=. python -c "
from app.agents.graph import build_graph
from langchain_core.runnables import RunnableConfig

graph = build_graph('T1')
state = {
    'question_text': 'Explain binary search',
    'subject': 'Computer Science'
}
result = graph.invoke(state)
print(result)
"
```

### Code Organization

**Backend:**
- `agents/`: Core agent implementations
- `routes/`: FastAPI endpoints
- `services/`: Business logic, external integrations
- `db/`: Database models and access
- `config/`: Configuration management
- `tests/`: Test suite

**Frontend:**
- `src/app/`: Next.js pages
- `src/components/`: React components
- `src/styles/`: CSS and Tailwind config

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/agent-improvement

# Make changes
vim backend/app/agents/router.py

# Test locally
PYTHONPATH=. pytest tests/ -v

# Commit with descriptive message
git add backend/app/agents/router.py
git commit -m "feat(agents): improve router confidence scoring"

# Push and create PR
git push origin feature/agent-improvement
# Create PR on GitHub
```

### Configuration Management

Override configurations for development:

```bash
# Use groq_free for development
export AGENT_CONFIG_PRESET=groq_free
export GROQ_API_KEY=gsk_your_key

# Verbose logging
export LOG_LEVEL=DEBUG
export PYTHONUNBUFFERED=1

# Skip external APIs (use mocks)
export USE_REAL_APIS=false

# Start server
PYTHONPATH=. uvicorn app.main:app --reload
```

---

## Deployment Guide

### Docker Deployment

#### Build Docker Images

```bash
# Backend
docker build -t gamed-ai-backend:latest ./backend

# Frontend
docker build -t gamed-ai-frontend:latest ./frontend

# Tag for registry
docker tag gamed-ai-backend:latest myregistry/gamed-ai-backend:v2.0.0
docker tag gamed-ai-frontend:latest myregistry/gamed-ai-frontend:v2.0.0

# Push to registry
docker push myregistry/gamed-ai-backend:v2.0.0
docker push myregistry/gamed-ai-frontend:v2.0.0
```

#### Run with Docker Compose

```bash
# Production deployment
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down
```

### Cloud Deployment

#### Azure Container Instances

```bash
az container create \
  --resource-group myresourcegroup \
  --name gamed-ai-backend \
  --image myregistry/gamed-ai-backend:v2.0.0 \
  --ports 8000 \
  --environment-variables OPENAI_API_KEY=your_key
```

#### AWS ECS

```bash
# Create task definition
aws ecs register-task-definition \
  --family gamed-ai \
  --container-definitions '[...]'

# Create service
aws ecs create-service \
  --cluster my-cluster \
  --service-name gamed-ai-service \
  --task-definition gamed-ai:1 \
  --desired-count 1
```

#### Google Cloud Run

```bash
# Deploy backend
gcloud run deploy gamed-ai-backend \
  --image myregistry/gamed-ai-backend:v2.0.0 \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=your_key

# Deploy frontend
gcloud run deploy gamed-ai-frontend \
  --image myregistry/gamed-ai-frontend:v2.0.0 \
  --platform managed \
  --region us-central1
```

### Environment Configuration (Production)

Create `backend/.env.production`:

```bash
# Use production models
AGENT_CONFIG_PRESET=quality_optimized

# API Keys (from secrets manager)
OPENAI_API_KEY=${OPENAI_API_KEY_SECRET}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY_SECRET}
SERPER_API_KEY=${SERPER_API_KEY_SECRET}

# Database
DATABASE_URL=postgresql://user:pass@prod-db.com/gamed_ai

# Security
ENVIRONMENT=production
DEBUG=false
ALLOWED_ORIGINS=["https://gamed.ai", "https://www.gamed.ai"]

# Monitoring
SENTRY_DSN=https://key@sentry.io/project
LOG_LEVEL=INFO

# Rate limiting
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_PERIOD_MINUTES=1

# Async task queue (if using Celery)
REDIS_URL=redis://prod-redis.com:6379/0
```

---

## Troubleshooting

### Common Issues

#### 1. **API Key Not Found**

```
Error: OpenAI API key not configured
```

**Solution:**
```bash
# Check .env file
cat backend/.env | grep OPENAI_API_KEY

# Or set via environment
export OPENAI_API_KEY=sk_your_key
export GROQ_API_KEY=gsk_your_key

# Restart backend
kill -9 $(lsof -ti:8000)
PYTHONPATH=. uvicorn app.main:app --reload
```

#### 2. **Port Already in Use**

```
Error: Address already in use (:8000)
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
PYTHONPATH=. uvicorn app.main:app --port 8001
```

#### 3. **Database Connection Error**

```
Error: unable to open database file
```

**Solution:**
```bash
# Check database file exists and has permissions
ls -la backend/gamed_ai.db
chmod 644 backend/gamed_ai.db

# Or reset database
rm backend/gamed_ai.db
# Database will be recreated on next run

# Check SQLite integrity
sqlite3 backend/gamed_ai.db ".tables"
```

#### 4. **Pipeline Timeout**

```
Error: Pipeline exceeded timeout (60 seconds)
```

**Solution:**
```bash
# Increase timeout in agent config
export AGENT_TIMEOUT_SECONDS=120

# Or optimize agent
# - Use faster model (gpt-4o-mini instead of gpt-4)
# - Reduce max_tokens
# - Skip optional agents (e.g., story_generator)
```

#### 5. **Memory Issues**

```
Error: MemoryError: Unable to allocate ...
```

**Solution:**
```bash
# For large images/segmentation:
# 1. Reduce image size before processing
# 2. Use SAM instead of SAM2 (lighter)
# 3. Process images asynchronously

# Or increase Python memory limit
export PYTHONHASHSEED=0
python3 -u scripts/demo_pipeline.py
```

#### 6. **LLM API Rate Limiting**

```
Error: 429 - Too Many Requests
```

**Solution:**
```bash
# Implement exponential backoff (already done)
# OR reduce request rate:

# Option 1: Switch to free Groq tier
export AGENT_CONFIG_PRESET=groq_free

# Option 2: Add delay between requests
export API_REQUEST_DELAY_MS=100

# Option 3: Use local models
export USE_LOCAL_MODELS=true
export OLLAMA_BASE_URL=http://localhost:11434
```

#### 7. **Image Processing Errors**

```
Error: SAM segmentation failed: CUDA out of memory
```

**Solution:**
```bash
# Use CPU-optimized SAM3 for M1/M2 macs
export USE_MLX_SAM3=true

# Or use smaller SAM model
export SAM_MODEL=sam_vit_l

# Or disable image diagrams
export USE_IMAGE_DIAGRAMS=false
```

#### 8. **Frontend Build Error**

```
Error: next/image Error
```

**Solution:**
```bash
cd frontend

# Clear cache
rm -rf .next
rm -rf node_modules
npm install

# Rebuild
npm run build

# Check TypeScript
npx tsc --noEmit
```

### Debug Mode

Enable verbose logging:

```bash
# Backend
export LOG_LEVEL=DEBUG
export PYTHONUNBUFFERED=1
export LANGCHAIN_DEBUG=true

PYTHONPATH=. python -u -m uvicorn app.main:app --reload

# This will print:
# - All LLM calls and responses
# - Agent execution flow
# - Token usage
# - Latencies
# - Errors with full stack traces
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/api/db/status

# LLM provider status
curl http://localhost:8000/api/llm/status

# External service status
curl http://localhost:8000/api/external/status
```

---

## Performance Optimization

### Backend Optimization

#### 1. **Caching**

```python
# Cache domain knowledge retrievals
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_domain_knowledge(subject: str) -> dict:
    return web_search(subject)

# Cache agent responses
RESPONSE_CACHE = {}
cache_key = hash((agent_name, input_hash))
if cache_key in RESPONSE_CACHE:
    return RESPONSE_CACHE[cache_key]
```

#### 2. **Parallel Execution**

```python
# Run independent agents in parallel
import asyncio

async def parallel_agents(state):
    results = await asyncio.gather(
        input_enhancer_async(state),
        domain_knowledge_async(state),
        game_planner_async(state)
    )
    return combine_results(results)
```

#### 3. **Database Optimization**

```sql
-- Add indexes for common queries
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_created ON pipeline_runs(created_at DESC);
CREATE INDEX idx_games_created ON games(created_at DESC);

-- Batch inserts
INSERT INTO pipeline_stages (run_id, stage_name, ...)
VALUES 
  (...), 
  (...), 
  (...)
```

#### 4. **Model Selection**

```python
# Use faster models for less critical agents
FAST_MODELS = {
    "router": "gpt-4o-mini",  # Fast routing
    "input_enhancer": "gpt-4o-mini",
    "story_generator": "claude-sonnet",  # More important
    "blueprint_generator": "gpt-4-turbo"  # Most critical
}
```

### Frontend Optimization

#### 1. **Code Splitting**

```javascript
// Next.js automatic code splitting
import dynamic from 'next/dynamic';

const PipelineGraph = dynamic(
  () => import('../components/PipelineGraph'),
  { loading: () => <p>Loading...</p> }
);
```

#### 2. **Image Optimization**

```javascript
// Use Next.js Image component
import Image from 'next/image';

<Image
  src={gameImage}
  alt="Game preview"
  width={300}
  height={300}
  priority  // For above-fold images
/>
```

#### 3. **State Management**

```javascript
// Use Zustand for minimal state
const useGameStore = create((set) => ({
  // Only essential state, memoize selectors
  gameScore: 0,
  setGameScore: (score) => set({ gameScore: score })
}));

// Avoid unnecessary re-renders
const GameScore = React.memo(({ score }) => <div>{score}</div>);
```

### Cost Optimization

```python
# Cost-aware model selection
def select_model_by_cost(required_quality: float) -> str:
    if required_quality < 0.7:
        return "gpt-4o-mini"  # $0.00015/1K tokens
    elif required_quality < 0.85:
        return "gpt-4-turbo"  # $0.001/1K tokens
    else:
        return "gpt-4o"  # $0.003/1K tokens

# Use free tier where possible
PRIMARY_MODEL = "groq"  # Free 14,400 req/day
FALLBACK_MODEL = "openai"  # For overflow

# Batch requests
generate_games(
    questions=["Q1", "Q2", ..., "Q100"],
    batch_size=10,
    concurrent_requests=3
)
```

---

## Security Considerations

### API Security

1. **Authentication**
   ```python
   # Add JWT token validation
   from fastapi.security import HTTPBearer
   
   security = HTTPBearer()
   
   @app.post("/api/generate")
   async def generate(
       request: GenerateRequest,
       credentials: HTTPAuthCredentials = Depends(security)
   ):
       token = credentials.credentials
       user = verify_token(token)
       return process_request(request, user)
   ```

2. **Rate Limiting**
   ```python
   from slowapi import Limiter
   
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/api/generate")
   @limiter.limit("10/minute")
   async def generate(request: GenerateRequest):
       pass
   ```

3. **CORS Configuration**
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://gamed.ai"],
       allow_methods=["GET", "POST"],
       allow_credentials=True
   )
   ```

### Data Security

1. **Secret Management**
   ```bash
   # Use environment variables for secrets
   OPENAI_API_KEY=sk_xxx
   DATABASE_URL=postgresql://user:pass@host
   
   # Or use secrets manager
   # AWS Secrets Manager, Azure Key Vault, etc.
   ```

2. **Database Encryption**
   ```python
   # Encrypt sensitive data
   from cryptography.fernet import Fernet
   
   cipher = Fernet(key)
   encrypted = cipher.encrypt(api_key.encode())
   ```

3. **Input Validation**
   ```python
   # Validate all inputs
   from pydantic import BaseModel, validator
   
   class GenerateRequest(BaseModel):
       question_text: str
       
       @validator('question_text')
       def validate_question(cls, v):
           if len(v) < 5 or len(v) > 10000:
               raise ValueError('Invalid length')
           return v
   ```

### Output Security

1. **SQL Injection Prevention**
   ```python
   # Use parameterized queries (SQLAlchemy handles this)
   from sqlalchemy import text
   
   # Bad: f"SELECT * FROM users WHERE id={user_id}"
   # Good:
   result = db.execute(
       text("SELECT * FROM users WHERE id=:id"),
       {"id": user_id}
   )
   ```

2. **XSS Prevention**
   ```javascript
   // React prevents XSS by default
   // But be careful with dangerouslySetInnerHTML
   <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
   // Only use with trusted content
   ```

3. **CSRF Protection**
   ```python
   from fastapi.middleware import CORSMiddleware
   
   # FastAPI CSRF protection via SameSite cookies
   ```

---

## Contributing Guidelines

### Code Style

**Python:**
- PEP 8 compliance
- Type hints for all functions
- Docstrings using Google style

```python
def generate_game(question: str, subject: str) -> Game:
    """Generate a game from a question.
    
    Args:
        question: The learning question.
        subject: Subject area (e.g., "Computer Science").
    
    Returns:
        A Game object with all generated content.
    
    Raises:
        ValueError: If question is empty.
        TimeoutError: If generation exceeds timeout.
    """
    pass
```

**TypeScript:**
- Strict type checking
- Functional components with hooks
- PropTypes or TypeScript interfaces

```typescript
interface GameProps {
  gameId: string;
  onComplete?: (score: number) => void;
}

const GamePlayer: React.FC<GameProps> = ({
  gameId,
  onComplete
}) => {
  // Component implementation
};
```

### Commit Messages

```
feat(agents): add SAM3 segmentation support
^--^  ^----^  ^--------------------------^
|     |       |
|     |       └─→ Summary in present tense
|     |
|     └─→ Component affected
|
└─→ Type: feat, fix, docs, style, refactor, test, chore
```

**Detailed commit message format:**
```
feat(agents): add SAM3 segmentation support

- Integrated SAM3 model for faster segmentation
- Added MLX optimization for Apple Silicon
- Updated diagram pipeline to use SAM3 by default
- Added tests for SAM3 agent

Closes #123
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/description`
2. Make changes with clean commits
3. Add/update tests
4. Update documentation
5. Push to GitHub: `git push origin feature/description`
6. Create Pull Request with:
   - Clear title and description
   - Link to related issues
   - Testing notes
   - Any configuration changes

### Testing Requirements

- All new code must have tests
- Tests must pass locally: `pytest tests/ -v`
- Coverage must not decrease
- Integration tests for pipeline changes

---

## Summary

**GamED.AI v2** is a production-ready educational game generation platform with:

✅ **26+ specialized agents** working in orchestrated pipelines  
✅ **18+ game templates** spanning Bloom's cognitive levels  
✅ **Multi-model support** (OpenAI, Anthropic, Groq, local)  
✅ **Advanced features** like checkpointing, retry logic, human review  
✅ **Interactive frontend** with game player and pipeline visualization  
✅ **Comprehensive APIs** for game generation and management  
✅ **Production-ready** with Docker, monitoring, and security  

This documentation provides everything needed to understand, develop, deploy, and maintain the system.

---

**For Questions or Issues:**
- Check the [docs/](docs/) folder for detailed implementation guides
- Review [COMMANDS.md](COMMANDS.md) for quick command reference
- Consult [CLAUDE.md](CLAUDE.md) for AI-assisted development guidance
- Open an issue on GitHub for bugs or feature requests

**Last Updated:** February 4, 2026  
**Maintained by:** GamED.AI Development Team

