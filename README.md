<p align="center">
  <b>GamED.AI</b><br>
  <i>A Hierarchical Multi-Agent Framework for Automated Educational Game Generation</i>
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
    author = "Agarwal, Shiven and Shah, Yash and Shekhar, Ashish Raj and Bordoloi, Priyanuj and De, Sandipan and Gupta, Vivek",
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
    └── ARCHITECTURE.md         # Full pipeline diagrams and agent table
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

Mechanics covered: drag-and-drop, click-to-identify, trace-path, sequencing, sorting, memory-match, branching-scenario, compare-contrast, description-matching, state-tracer, bug-hunter, algorithm-builder, complexity-analyzer, constraint-puzzle, and hierarchical.

---

## 6. Architecture Overview

The GamED.AI pipeline is a hierarchical DAG in LangGraph with six phases, each an independent sub-graph with typed I/O and a Quality Gate at its boundary:

1. **Phase 0 — Context Gathering**: Parallel input analysis and domain knowledge retrieval grounded in curated sources.
2. **Phase 1 — Concept Design**: ReAct agent resolves input against a Bloom's-to-mechanic constraint table to produce a game concept with learning objective, template family, and mechanic contract.
3. **Phase 2 — Game Plan** (deterministic, no LLM): Assigns scene IDs, computes score contracts, determines asset needs, builds transition graph.
4. **Phase 3 — Scene Content** (parallel): N parallel `Send()` calls generate game-type-specific content per scene. FOL-based Bloom's alignment predicates at QG3.
5. **Phase 4 — Assets** (parallel): M parallel workers perform image search, quality filtering, and fallback generation.
6. **Phase 5 — Assembly** (deterministic, no LLM): Combines game plan + content + assets into a verified JSON blueprint.

Four Quality Gates (QG1–QG4) execute without LLM inference, providing constant cost and formal verifiability. The architecture achieves 90% validation pass rate with 73% token reduction over ReAct baselines ($0.48/game, ~19,900 tokens).

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full pipeline diagrams, phase details, and game template reference.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Copyright 2026 Shiven Agarwal, Yash Shah, Ashish Raj Shekhar, Priyanuj Bordoloi, Sandipan De, Vivek Gupta
