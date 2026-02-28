# GamED.AI — ACL 2026 System Demonstration Video

**Duration:** 2:30 (150 seconds)
**Format:** Screencast with audio narration

---

## S1: Introduction (0:00 – 0:12) — 12s

### Screen
| Time | Action |
|------|--------|
| 0:00 | Browser at `localhost:3000/acl-demo`. Hero visible: "Transform Questions into Interactive Learning Games." |
| 0:03 | Scroll to show Five Academic Domains cards. |
| 0:06 | Scroll to show 15 Game Mechanics pills. |
| 0:09 | Scroll to Three Education Levels. |

### Narration
> "GamED.AI transforms any educational question into a fully playable, interactive game. The system supports fifteen game mechanics across five academic domains and three education levels. Let's see it in action."

---

## S2: Using the Tool (0:12 – 0:30) — 18s

### Screen
| Time | Action |
|------|--------|
| 0:12 | Click "Try It" tab. |
| 0:14 | Click the "Label the parts of a plant cell and identify their functions" example card — text fills the input. |
| 0:17 | Show Pipeline selector: Sequential, ReAct, Hierarchical — "Hierarchical" selected. |
| 0:19 | Show Template selector: toggle to "Algorithm Game" briefly, back to "Interactive Diagram." |
| 0:22 | Show Model selector: Gemini selected, OpenAI and Local visible. |
| 0:25 | Pause — query and all selections clearly visible. |
| 0:27 | Click the generate button. Spinner appears. |
| 0:29 | Page transitions to observability dashboard. |

### Narration
> "We enter a question — 'Label the parts of a plant cell and identify their functions.' We select the Hierarchical DAG pipeline, the Interactive Diagram template, and Gemini as the model. The system also supports OpenAI and local open-source models. Hit generate."

---

## S3: Pipeline Observability (0:30 – 0:55) — 25s

### Screen
| Time | Action |
|------|--------|
| 0:30 | Observability dashboard loaded. 18 nodes across 6 phases, all green. Top bar shows query, token count, cost, time. |
| 0:33 | Click "Input Analyzer" in Phase 0 — side panel shows agent details. |
| 0:36 | Click "DK Retriever" in Phase 0 — both ran in parallel. |
| 0:39 | Click "Concept Designer" in Phase 1 — side panel shows ReAct agent details. |
| 0:42 | Click "QG1: Concept Validator" — side panel: PASSED, Deterministic. |
| 0:45 | Click "Content Gen (S1)" in Phase 3 — parallel workers visible (S1, S2, S3). |
| 0:48 | Click "QG3: Content Validator" — FOL predicates all passed, schema compliance shown. |
| 0:51 | Click "Blueprint Assembler" in Phase 5 — blueprint JSON visible with scenes and score contracts. |
| 0:54 | Click "Play Game" button. |

### Narration
> "The observability dashboard gives full visibility into the pipeline. We can see every agent across six phases, click any node to inspect its inputs, outputs, and execution time. Token consumption and cost are tracked per-agent. Each phase boundary has a deterministic Quality Gate — we can click one to see the validation predicates it checked. All phases passed — the game is ready. Let's play."

---

## S4: Gameplay — Plant Cell Drag & Drop (0:55 – 1:30) — 35s

### Screen
| Time | Action |
|------|--------|
| 0:55 | Mode selection screen: title, Biology badge, K-12, Drag & Drop, Bloom's level. Learn Mode / Test Mode toggle. |
| 0:58 | Learn Mode selected. Click "Start Game." |
| 1:00 | Game loads: plant cell diagram with zones. Labels in sidebar pool. |
| 1:03 | Drag "Cell Wall" to correct zone — green feedback with educational explanation. |
| 1:07 | Drag "Chloroplast" to correct zone — correct. |
| 1:10 | Drag "Nucleus" to wrong zone — red feedback + hint. |
| 1:13 | Drag "Nucleus" to correct zone — green feedback. |
| 1:16 | Rapidly place remaining labels (Mitochondria, Vacuole, Cell Membrane, ER, Golgi). |
| 1:23 | All labels placed. Completion animation. |
| 1:25 | If multi-scene: advance to next scene briefly. |
| 1:28 | Final results panel with score breakdown. |

### Narration
> "Each game has two modes — Learn and Test. We start in Learn Mode. The first mechanic is drag-and-drop — we drag labels onto the plant cell diagram. Correct placements show educational feedback. An incorrect placement gives a hint pointing to the right location. Now the second mechanic — click-to-identify. We click on each organelle as it's described. Both mechanics in one game, generated from a single question. And here are our results — score breakdown by scene and mechanic."

---

## S5: Mechanic Showcase Montage (1:30 – 2:00) — 30s

### Screen
Six 5-second clips, hard cuts. Each shows one mechanic with one visible interaction.

| Clip | Time | Mechanic | What's Shown |
|------|------|----------|-------------|
| 1 | 1:30–1:35 | Trace Path | Click waypoints on a heart diagram — animated particles flow along the traced path. |
| 2 | 1:35–1:40 | Memory Match | Flip two cards — matched pair animates together. |
| 3 | 1:40–1:45 | Sequencing | Drag an event card into the correct timeline position. |
| 4 | 1:45–1:50 | Sorting | Drag an organism into a category bucket. |
| 5 | 1:50–1:55 | State Tracer | Advance one step in bubble sort — predict the array state. |
| 6 | 1:55–2:00 | Bug Hunter | Highlight a code line — submit bug on the off-by-one error. |

### Narration
> "Here are six more mechanics from the library. Trace Path — trace blood flow through the heart. Memory Match — pair historical figures with contributions. Sequencing — order events on a timeline. Sorting — classify organisms by category. State Tracer — step through bubble sort. Bug Hunter — find the bug in binary search. All generated from a single natural language question each."

---

## S6: Setup & Running Locally (2:00 – 2:25) — 25s

### Screen
| Time | Action |
|------|--------|
| 2:00 | Click "Getting Started" tab. |
| 2:02 | Expand "Static Demo" section — show the three commands: git clone, npm install, npm run dev. |
| 2:06 | Expand "Full Setup" section — show backend setup: clone, venv, pip install, .env. |
| 2:10 | Show backend start: uvicorn command. |
| 2:12 | Show frontend start: npm run dev. |
| 2:15 | Expand "CLI Pipeline Usage" section — show the generate command with a single game ID. |
| 2:18 | Show the generate-all command. |
| 2:20 | Switch to "Try It" tab — show the input field, emphasizing any question works. |
| 2:23 | Type a new question (e.g., "Compare mitosis and meiosis") to show it accepts anything. |

### Narration
> "To try GamED.AI — clone the repo and run the frontend. The fifty demo games work with no backend. For full generation, start the backend with your API key and run from the command line or the web interface. The system works with any educational question — any domain, any level."

---

## S7: Closing (2:25 – 2:30) — 5s

### Screen
| Time | Action |
|------|--------|
| 2:25 | Home page hero visible. |
| 2:27 | Post-production overlay: |
|      | **GamED.AI — ACL 2026** |
|      | **15 mechanics | 5 domains | Open Source** |
|      | Repository URL + QR code |

### Narration
> "GamED.AI — fifteen mechanics, five domains, open-source. Code and games are publicly available."

---

## Complete Narration (read straight through)

**S1:**
"GamED.AI transforms any educational question into a fully playable, interactive game. The system supports fifteen game mechanics across five academic domains and three education levels. Let's see it in action."

**S2:**
"We enter a question — 'Label the parts of a plant cell and identify their functions.' We select the Hierarchical DAG pipeline, the Interactive Diagram template, and Gemini as the model. The system also supports OpenAI and local open-source models. Hit generate."

**S3:**
"The observability dashboard gives full visibility into the pipeline. We can see every agent across six phases, click any node to inspect its inputs, outputs, and execution time. Token consumption and cost are tracked per-agent. Each phase boundary has a deterministic Quality Gate — we can click one to see the validation predicates it checked. All phases passed — the game is ready. Let's play."

**S4:**
"Each game has two modes — Learn and Test. We start in Learn Mode. The first mechanic is drag-and-drop — we drag labels onto the plant cell diagram. Correct placements show educational feedback. An incorrect placement gives a hint pointing to the right location. Now the second mechanic — click-to-identify. We click on each organelle as it's described. Both mechanics in one game, generated from a single question. And here are our results — score breakdown by scene and mechanic."

**S5:**
"Here are six more mechanics from the library. Trace Path — trace blood flow through the heart. Memory Match — pair historical figures with contributions. Sequencing — order events on a timeline. Sorting — classify organisms by category. State Tracer — step through bubble sort. Bug Hunter — find the bug in binary search. All generated from a single natural language question each."

**S6:**
"To try GamED.AI — clone the repo and run the frontend. The fifty demo games work with no backend. For full generation, start the backend with your API key and run from the command line or the web interface. The system works with any educational question — any domain, any level."

**S7:**
"GamED.AI — fifteen mechanics, five domains, open-source. Code and games are publicly available."

---

## Timing Summary

| Section | Start | End | Duration | Content |
|---------|-------|-----|----------|---------|
| S1 — Introduction | 0:00 | 0:12 | 12s | Landing page, what it does |
| S2 — Using the Tool | 0:12 | 0:30 | 18s | Enter query, select options, generate |
| S3 — Pipeline | 0:30 | 0:55 | 25s | Observability dashboard walkthrough |
| S4 — Gameplay | 0:55 | 1:30 | 35s | Full plant cell game playthrough |
| S5 — Mechanic Montage | 1:30 | 2:00 | 30s | 6 mechanics, 5s each |
| S6 — Setup | 2:00 | 2:25 | 25s | Clone, install, run, CLI usage |
| S7 — Closing | 2:25 | 2:30 | 5s | Tagline + links |
| **Total** | | | **150s** | |

---

## Word Count

| Section | Words | Duration | WPS |
|---------|-------|----------|-----|
| S1 | 32 | 12s | 2.7 |
| S2 | 51 | 18s | 2.8 |
| S3 | 76 | 25s | 3.0 |
| S4 | 52 | 35s | 1.5 |
| S5 | 60 | 30s | 2.0 |
| S6 | 50 | 25s | 2.0 |
| S7 | 14 | 5s | 2.8 |
| **Total** | **335** | **150s** | **2.2** |

Comfortable pace throughout. S4 is slow — gameplay visuals carry the section.

---

## Recording Notes

### Setup
- Chrome, clean profile, no bookmarks bar
- 1920x1080, 100% zoom
- Close notifications

### Recording
- OBS or QuickTime at 1080p
- Record S1–S4 as one continuous take if possible (natural flow)
- Record S5 clips separately (one per game)
- Record S6 as one take

### Audio
- Record narration separately
- Natural pace, ~2.2 WPS

### Export
- MPEG4 (H.264), 1920x1080
- Upload to YouTube or submit as supplementary material
