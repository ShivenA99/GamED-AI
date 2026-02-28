<p align="center">
  <b>GamED.AI</b><br>
  <i>Automated Educational Game Generation via Hierarchical Multi-Agent AI</i>
</p>

<p align="center">
  <a href="https://ShivenA99.github.io/GamED-AI/">Live Demo</a> |
  <a href="docs/ARCHITECTURE.md">Architecture</a> |
  <a href="#citation">Citation</a> |
  <a href="#license">License</a>
</p>

---

GamED.AI is a hierarchical multi-agent framework that automatically transforms educational questions into interactive web-based games. Given any question — from "Label the parts of a plant cell" to "Trace through bubble sort" — the pipeline orchestrates specialized AI agents across 6 phases to produce fully playable games covering 15 mechanic types, 5 subject domains (Biology, Computer Science, History, Linguistics, Mathematics), and 3 education levels (K-12, Undergraduate, Graduate). The system demo includes 50 pre-generated games playable without any backend.

## Citation

```bibtex
@inproceedings{agarwal-etal-2026-gamedai,
    title = "{GamED.AI}: A Hierarchical Multi-Agent Framework for Automated Educational Game Generation",
    author = "Agarwal, Shiven and Sarkar, Ashish",
    booktitle = "Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics: System Demonstrations",
    month = aug,
    year = "2026",
    publisher = "Association for Computational Linguistics",
}
```

## Live Demo

Browse 50 pre-generated games at: **https://ShivenA99.github.io/GamED-AI/**

## Repository Structure

```
GamED-AI/
├── backend/                    # Python/FastAPI backend
│   ├── app/
│   │   ├── agents/             # LangGraph agents (59+)
│   │   ├── config/             # Model registry, presets
│   │   ├── routes/             # FastAPI endpoints
│   │   └── services/           # LLM, image, storage services
│   ├── prompts/                # Agent prompt templates
│   ├── scripts/                # CLI generation scripts
│   └── requirements.txt
├── frontend/                   # Next.js frontend
│   ├── src/
│   │   ├── app/acl-demo/       # Static demo pages
│   │   ├── components/         # React components + game templates
│   │   └── data/acl-demo/      # Pre-generated game data (50 games)
│   └── public/acl-demo/        # Static assets for demo games
└── docs/
    ├── ARCHITECTURE.md         # Full pipeline diagrams and agent table
    └── demo_video_script_final.md
```

---

## 0. Prerequisites

- Python 3.10+
- Node.js 18+
- API keys: `GOOGLE_API_KEY` (Gemini), `OPENAI_API_KEY`

---

## 1. Quick Start — Static Demo (No Backend Required)

Browse all 50 pre-generated games locally:

```bash
git clone https://github.com/ShivenA99/GamED-AI.git
cd GamED-AI/frontend
npm install
npm run dev
# Open http://localhost:3000 — redirects to /acl-demo
```

The demo runs entirely from static JSON files and local image assets — no API keys or backend needed.

---

## 2. Full Setup — Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create backend/.env with your API keys:
# GOOGLE_API_KEY=your_gemini_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here

PYTHONPATH=. uvicorn app.main:app --reload --port 8000
# Health check: curl http://localhost:8000/health
```

---

## 3. Full Setup — Frontend (with Backend)

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## 4. CLI Pipeline Usage

Generate a new game directly from the command line:

```bash
cd backend
PYTHONPATH=. python scripts/generate_acl_demo.py \
  --query "Label the parts of a plant cell" \
  --model gemini
```

Output is saved to `backend/assets/demo/` with the generated blueprint JSON and diagram images.

---

## 5. Game Library

The demo includes 50 pre-generated games spanning:

| Domain | K-12 | Undergraduate | Graduate |
|--------|------|---------------|---------|
| Biology | Plant cell, Mitosis, Food chains | Cardiovascular, DNA enzymes, Inheritance, Organelles | Cellular respiration, Clinical diagnosis, Evolution |
| Computer Science | Bubble sort, Computer parts, Network data | BFS, Binary search, Algorithm complexity, UML | DP complexity, Scheduling, TCP/UDP |
| History | American Revolution, Historical figures, Roman Empire | Ancient civilizations, Industrial Revolution, Revolutions, WWI causes | Cold War, Historiography, Versailles |
| Linguistics | Sentence parts, Sentence building, Word types | Language families, Morphemes, Phonology, Semantic roles | Language acquisition, Phonological processes, Syntax trees |
| Mathematics | Geometry, Linear equations, Number types | Calculus, Function types, Integration, Matrix ops | Numerical methods, Proof strategy, Vector spaces |

Mechanics covered: drag-and-drop, click-to-identify, trace-path, sequencing, sorting, memory-match, branching-scenario, compare-contrast, description-matching, state-tracer, bug-hunter, algorithm-builder, complexity-analyzer, constraint-puzzle, and interactive diagram.

---

## 6. Architecture Overview

The GamED.AI pipeline is a directed acyclic graph (DAG) of 59+ specialized agents organized into 6 phases with 4 Quality Gates:

1. **Phase 1 — Game Design** (`game_designer_v3`): Selects mechanic type, difficulty, and educational objectives using ReAct reasoning over the question domain.
2. **Phase 2 — Scene Architecture** (`scene_architect_v3`): Decomposes the game into scenes and tasks; generates mechanic-specific content schemas.
3. **Phase 3 — Interaction Design** (`interaction_designer_v3`): Enriches each scene with interaction logic, scoring rules, and feedback.
4. **Phase 4 — Asset Generation** (`asset_generator_v3`): Produces diagram images, zone coordinates, and icon assets in parallel.
5. **Phase 5 — Blueprint Assembly** (`blueprint_assembler_v3`): Assembles all outputs into a validated frontend-ready JSON blueprint.
6. **Quality Gates**: Validators at phases 1-3 enforce schema correctness with retry loops before proceeding.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full pipeline diagrams, the complete 59+ agent table, and state field reference.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Copyright 2026 Shiven Agarwal
