# CLAUDE.md

## Project Overview

GamED.AI v2 — AI-powered educational game generation using a multi-agent LangGraph pipeline (59+ agents). Transforms text questions into interactive games (label diagrams, trace paths, sequencing, PhET simulations, etc.).

**Stack:** Python/FastAPI backend, TypeScript/React frontend, LangGraph orchestration, SQLite DB.
**Frameworks:** LangGraph (pipeline), Pydantic (schemas), Next.js (frontend).
**State:** All agents read/write a shared `AgentState` TypedDict (160+ fields) — ensure fields match across all stages.

---

## Working Style

- When asked to implement a plan, confirm architecture and dependencies BEFORE writing code. Do not assume components or skip alignment.
- Never hardcode mechanic-specific or game-type-specific logic. Agents must generically consume upstream output rather than encoding assumptions about LABEL_DIAGRAM or any specific template.
- When asked to "test" something, run automated test scripts and headless pipeline runs — NOT interactive/manual testing — unless explicitly told otherwise.
- When asked for analysis or an audit, complete it FIRST and present for review. Do not jump into implementation until approved. Verify by reading actual code — never claim work is already done without checking.
- Fix root causes, not symptoms. Never increase retry counts, add fallbacks, or patch over failures to mask bugs. If a state field is missing, fix the TypedDict.
- Before parallelizing work with sub-agents, map task dependencies first. Verify sub-agent outputs, and ensure each subagent writes to a document. Often you run out of context before they can respond to you making the whole effort useless.

---

## Essential Commands

```bash
# Backend
cd backend && source venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
PYTHONPATH=. pytest tests/ -v

# Frontend
cd frontend && npm run dev          # Port 3000
cd frontend && npx tsc --noEmit     # Type check

# Kill ports
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Health check
curl http://localhost:8000/health
```

---

## Key Directories

| Directory                              | Purpose                                                                      |
| -------------------------------------- | ---------------------------------------------------------------------------- |
| `backend/app/agents/`                | LangGraph agents (59+), state, instrumentation                               |
| `backend/app/agents/schemas/`        | Pydantic schemas (blueprint, game_plan, label_diagram, phet, stages)         |
| `backend/app/agents/workflows/`      | Multi-mechanic workflow system (7 WorkflowTypes, 10 MechanicTypes)           |
| `backend/app/agents/had/`            | HAD v3 architecture (ReAct loops, zone planning, collision resolution)       |
| `backend/app/config/`                | Model registry, agent configs, presets, interaction patterns                 |
| `backend/app/tools/`                 | Structured tool framework (blueprint, game_design, vision, research, render) |
| `backend/app/routes/`                | FastAPI endpoints (generate, pipeline, observability, review, sessions)      |
| `backend/app/services/`              | External services (LLM, Qwen VL, Gemini, SAM3, inpainting, image retrieval)  |
| `backend/prompts/`                   | Template-specific prompt files                                               |
| `frontend/src/components/pipeline/`  | Observability UI (timeline, token charts, ReAct trace, cost breakdown)       |
| `frontend/src/components/templates/` | Game template React components (LabelDiagramGame, PhetSimulationGame)        |

---

## Architecture (High-Level)

See `docs/ARCHITECTURE.md` for full pipeline diagrams, 59+ agent table, and state field reference, it is not the latest one always check with latest code.

### Pipeline Presets

| Preset       | Key                            | Description                                                       |
| ------------ | ------------------------------ | ----------------------------------------------------------------- |
| Default      | `default`                    | Image classification + SAM segmentation (baseline)                |
| Hierarchical | `label_diagram_hierarchical` | AI diagram generation + Gemini zone detection                     |
| Advanced     | `advanced_label_diagram`     | Full agentic with game_designer, diagram_analyzer                 |
| HAD          | `had`                        | Hierarchical Agentic DAG with ReAct loops, 4-cluster architecture |

---

## Debugging Checklist

When debugging pipeline issues, always check these recurring failure categories:

1. **State field propagation** — Is the field in `AgentState` TypedDict? Is it being written by the upstream agent and read by the downstream agent?
2. **Graph wiring** — Is the agent node added in `graph.py`? Are edges connected correctly? Is `wrap_agent_with_instrumentation()` applied?
3. **Database path/schema consistency** — `gamed_ai.db` vs `gamed_ai_v2.db`, table existence
4. **ID field confusion** — `process_id` vs `question_id` vs `run_id` (they serve different purposes)
5. **Workflow mode** — Is `scene_breakdown` populated? Is `workflow_execution_plan` non-empty? Check logs for "Using workflow mode" vs "Legacy mode"
6. **Import paths** — Always use `PYTHONPATH=.` from `backend/` directory
7. **Preset pipeline selection** — Check `_pipeline_preset` state field and `should_use_preset_pipeline()` routing

---

## Agent Development (Quick Reference)

When adding a new agent, update these files:

| File                                                  | What to Add                                                                 |
| ----------------------------------------------------- | --------------------------------------------------------------------------- |
| `backend/app/agents/instrumentation.py`             | Input/output keys in `extract_input_keys()` and `extract_output_keys()` |
| `backend/app/agents/graph.py`                       | Node registration with `wrap_agent_with_instrumentation()`, edges         |
| `frontend/src/components/pipeline/PipelineView.tsx` | `AGENT_METADATA` entry, `GRAPH_LAYOUT` position, edge definitions       |
| `frontend/src/components/pipeline/StagePanel.tsx`   | Custom output renderer (optional)                                           |

See `docs/AGENT_DEVELOPMENT_GUIDE.md` for full patterns with code examples.

---

## Coding Standards

**Python:** `PYTHONPATH=.` always, type hints required, async/await for I/O, structured logging via `logging.getLogger("gamed_ai.agents.{name}")`, Pydantic schemas for outputs.

**TypeScript:** Strict mode (no untyped `any`), named exports, utility classes from `globals.css`.

**Validators** return: `tuple[bool, float, str]` — `(success, score, message)`.

---

## File Modification Summary

| Change Type      | Files to Update                                                                           |
| ---------------- | ----------------------------------------------------------------------------------------- |
| New Agent        | `instrumentation.py`, `graph.py`, `PipelineView.tsx`, optionally `StagePanel.tsx` |
| New Template     | `backend/prompts/blueprint_*.txt`, `frontend/src/components/templates/`               |
| New API Endpoint | `backend/app/routes/`, `frontend/src/app/api/`                                        |
| Schema Change    | `backend/app/agents/schemas/`, `backend/app/db/models.py`                             |
| Model Config     | `backend/app/config/models.py`, `backend/app/config/agent_models.py`                  |
| New Workflow     | `backend/app/agents/workflows/`, `backend/app/agents/schemas/game_plan_schemas.py`    |
| New Preset       | `backend/app/config/presets/`, `backend/app/agents/graph.py`                          |

---

## Reference Documentation

- **[Agent Development Guide](docs/AGENT_DEVELOPMENT_GUIDE.md)** — Full agent patterns, code examples, checklist
- **[Architecture](docs/ARCHITECTURE.md)** — Complete pipeline diagrams, 59+ agent table, state fields, presets
- **[Commands Reference](docs/COMMANDS_REFERENCE.md)** — All CLI commands, env vars, topology options
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** — Common issues and fixes
