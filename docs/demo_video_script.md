# GamED.AI Demo Video — Narration Script (150 seconds)

## Recording Overview

| Property | Value |
|----------|-------|
| Total duration | 150 seconds (2:30) |
| Sections | 7 |
| Format | Screen recording + voiceover, edited together |
| Resolution | 1920×1080 (16:9) |
| Style | Professional, academic demo — clean transitions |

---

## Section 1: Hook + Problem Statement (0:00–0:20, 20s)

### Narration

> "Game-based learning improves outcomes by half a standard deviation — but building a single educational game takes 490 developer hours. Existing tools offer either manual authoring without pedagogical alignment, or AI generation that produces structurally invalid games. GamED.AI is a hierarchical multi-agent framework that generates validated educational games — 15 interaction mechanics, 5 subject domains — in under 60 seconds."

### Visual Cues

| Time | Visual |
|------|--------|
| 0:00–0:05 | Title card: "GamED.AI — Hierarchical Multi-Agent Educational Game Generation" with ACL 2026 badge |
| 0:05–0:10 | Split screen: manual game authoring (left, slow) vs. GamED.AI (right, fast) |
| 0:10–0:15 | Montage of 4 game screenshots (drag-drop, trace-path, state-tracer, memory-match) |
| 0:15–0:20 | Key stats overlay: "15 mechanics · 5 domains · 90% VPR · <60s" |

### Key Points to Cover
- Effect size: g = 0.49–0.78
- 490 dev hours per finished hour
- Existing tool limitations
- GamED.AI value proposition

---

## Section 2: Input Interface (0:20–0:40, 20s)

### Narration

> "An instructor opens the GamED.AI interface and enters a natural language question: 'Trace blood flow through the heart.' They select Biology as the domain, Undergraduate level, and the Interactive Algorithm template family. One click — Generate Game."

### Visual Cues

| Time | Visual |
|------|--------|
| 0:20–0:25 | Show the chat interface — clean, empty state |
| 0:25–0:30 | Type (or paste) the query into the text field: "Trace blood flow through the heart" |
| 0:30–0:34 | Click domain dropdown → select "Biology"; click level → select "Undergraduate" |
| 0:34–0:37 | Show Bloom's level selector briefly (optional), template toggle |
| 0:37–0:40 | Click "Generate Game" button — loading spinner appears |

### Screen Recording Instructions
- Start with browser focused on the GamED.AI input page
- Type the query naturally (not too fast)
- Deliberate, visible clicks on dropdowns
- Pause briefly after clicking Generate to show the loading state

---

## Section 3: Pipeline Observability (0:40–1:10, 30s)

### Narration

> "Behind the scenes, a six-phase DAG pipeline activates. Phase Zero gathers context in parallel — an input analyzer and domain knowledge retriever run simultaneously. Phase One: the game concept designer creates a multi-scene game plan, validated by Quality Gate One — a deterministic checker, no LLM inference."
>
> "Phase Two builds the game plan deterministically. Phase Three dispatches parallel workers — one per scene — using LangGraph's Send API. Quality Gate Three applies first-order logic predicates to verify Bloom's alignment."
>
> "Phase Four generates visual assets in parallel. Phase Five assembles the final blueprint — again, deterministic, zero LLM calls. Four Quality Gates total, nineteen thousand nine hundred tokens, forty-eight cents, under sixty seconds."

### Visual Cues

| Time | Visual |
|------|--------|
| 0:40–0:43 | Switch to observability dashboard — DAG view appears |
| 0:43–0:47 | Nodes light up sequentially: input_analyzer + dk_retriever (parallel, highlight) |
| 0:47–0:50 | game_concept_designer lights up → concept_validator turns green (checkmark) |
| 0:50–0:53 | game_plan_builder (green/deterministic color) → plan_validator green |
| 0:53–0:58 | content_dispatch fans out → 3 content_gen workers light up simultaneously (highlight "Parallel Send") |
| 0:58–1:02 | content_merge → content_validator: zoom in briefly to show "FOL Validation: PASSED" |
| 1:02–1:05 | asset_dispatch → 2 asset_workers light up in parallel |
| 1:05–1:08 | blueprint_assembler (green) → blueprint_validator (green checkmark) |
| 1:08–1:10 | Pan to token/cost bar chart: highlight "$0.48 total · 19.9K tokens · 47s" |

### Screen Recording Instructions
- If possible, replay or animate the pipeline execution in the observability dashboard
- Use mouse cursor to point at each phase as narration describes it
- Zoom into QG3 for the FOL validation callout
- End on the cost analytics panel

---

## Section 4: Blueprint Inspection (1:10–1:25, 15s)

### Narration

> "Every output is a verified contract, not just generated text. The blueprint specifies template type, algorithm name, scene array with typed content, and score contracts. Typed Pydantic schemas enforce validation at every phase boundary — ninety-eight point three percent schema compliance."

### Visual Cues

| Time | Visual |
|------|--------|
| 1:10–1:14 | Click on blueprint_assembler node in the DAG |
| 1:14–1:18 | Stage inspector expands showing JSON output — highlight: `templateType`, `algorithmName`, `scenes` array |
| 1:18–1:22 | Scroll down to show score contracts and mechanic configurations |
| 1:22–1:25 | Callout overlay: "Typed Pydantic Schemas — 98.3% compliance" |

### Screen Recording Instructions
- Click the blueprint_assembler node to open the stage inspector
- Slowly scroll through the JSON, pausing on key fields
- Use mouse cursor to point at templateType, scenes, scores

---

## Section 5: Gameplay — Heart Trace-Path (1:25–1:50, 25s)

### Narration

> "Now, the generated game. A heart diagram with nine anatomical zones. In Learn Mode, the student traces blood flow — clicking waypoints in sequence. Animated particles follow the traced path. Deoxygenated blood enters the vena cava, flows to the right atrium, right ventricle, through the pulmonary artery to the lungs."
>
> "Real-time scoring tracks progress — three of nine waypoints completed. A hint system guides struggling learners. Toggle to Test Mode for assessment without scaffolding. Multi-scene games compose up to four causally connected scenes with increasing Bloom's levels."

### Visual Cues

| Time | Visual |
|------|--------|
| 1:25–1:28 | Switch to game view — heart diagram loads with 9 labeled zones |
| 1:28–1:30 | Show "Learn Mode" indicator, instruction text at top |
| 1:30–1:38 | Click waypoints in sequence: Vena Cava → Right Atrium → Right Ventricle → Pulmonary Artery (animated particles flow along path) |
| 1:38–1:42 | Show progress bar updating: "4/9 waypoints" |
| 1:42–1:44 | Click hint button — hint appears for next waypoint |
| 1:44–1:47 | Toggle to "Test Mode" — UI changes (hints hidden, scaffolding removed) |
| 1:47–1:50 | Quick complete remaining waypoints → results panel appears with score breakdown |

### Screen Recording Instructions
- Play the game naturally — deliberate clicks, not rushed
- Let particles animate for at least 1 second before clicking next waypoint
- Visible cursor throughout
- Show the mode toggle clearly
- End on the results/score panel

---

## Section 6: Mechanic Showcase (1:50–2:20, 30s)

### Narration

> "GamED.AI supports fifteen interaction mechanics across two template families. Here are six in action."
>
> *[Clip 1]* "Drag-and-drop: place organelle labels on a plant cell diagram."
>
> *[Clip 2]* "Memory match: flip cards to pair historical figures with their contributions."
>
> *[Clip 3]* "Sequencing: arrange American Revolution events in chronological order."
>
> *[Clip 4]* "Sorting categories: classify organisms by trophic level."
>
> *[Clip 5]* "State tracer: predict the array state after each bubble sort swap."
>
> *[Clip 6]* "Bug hunter: find the off-by-one error in this binary search implementation."

### Visual Cues — Six 5-Second Clips

| Clip | Time | Game | Domain | Visual |
|------|------|------|--------|--------|
| 1 | 1:50–1:55 | Drag-and-drop | Biology | Plant cell diagram, drag "chloroplast" label to correct zone |
| 2 | 1:55–2:00 | Memory match | History | 3×4 card grid, flip two cards to reveal matching pair |
| 3 | 2:00–2:05 | Sequencing | History | Timeline with 6 event cards, drag "Declaration of Independence" into position |
| 4 | 2:05–2:10 | Sorting categories | Biology | Three bucket columns (Producer/Consumer/Decomposer), drag organism cards |
| 5 | 2:10–2:15 | State tracer | CS | Array `[5,3,1,4,2]`, step through bubble sort, predict state after swap |
| 6 | 2:15–2:20 | Bug hunter | CS | Binary search code with line numbers, highlight the `mid+1` bug |

### Transition Style
- Quick cuts (no fades) between clips for energy
- Each clip shows one clear interaction (drag, flip, click)
- Small label overlay in corner: "Drag-and-Drop", "Memory Match", etc.
- Domain badge: "Biology", "History", "CS"

### Screen Recording Instructions
- Record each clip separately against the real game
- Focus on one visible interaction per clip — don't try to complete the game
- Ensure the mechanic name is visible in the game UI or add as overlay
- Keep cursor visible and deliberate

---

## Section 7: Closing (2:20–2:30, 10s)

### Narration

> "GamED.AI: ninety percent validation pass rate, seventy-three percent token reduction, forty-eight cents per game. Fifteen mechanics, five domains, open-source. Try it live at our demo booth."

### Visual Cues

| Time | Visual |
|------|--------|
| 2:20–2:24 | Stats overlay on dark background: "90% VPR · 73% token reduction · $0.48/game" |
| 2:24–2:27 | "15 mechanics · 5 domains · Open Source" |
| 2:27–2:30 | Repository URL + QR code, "ACL 2026 · Demo Paper" badge, "Try it live at our booth" |

---

## Feature Coverage Matrix

Every feature mentioned in the paper should appear in at least one section of the video.

| Feature | Section(s) | Coverage |
|---------|-----------|----------|
| 2 template families (Diagram + Algorithm) | S1, S6 | S1 intro mentions "15 mechanics"; S6 shows both families |
| 15 interaction mechanics | S1, S6 | S1 stat overlay; S6 shows 6 of 15 |
| 5 subject domains | S2, S6 | S2 domain selector; S6 clips span Biology, History, CS |
| Bloom's Taxonomy alignment | S2, S4 | S2 level selector; S4 blueprint Bloom's field |
| 6-phase DAG architecture | S3 | Full walkthrough of all 6 phases |
| 4 Quality Gates (QG1–QG4) | S3 | Green checkmarks on each QG node |
| FOL-based validation | S3 | Explicit mention + zoom on QG3 |
| Typed Pydantic schemas | S4 | Blueprint inspection + "98.3% compliance" callout |
| Parallel Send pattern | S3 | Parallel content_gen + asset_worker highlighted |
| Deterministic vs LLM phases | S3 | Green (deterministic) vs blue (LLM) node colors |
| Token/cost analytics | S3, S7 | S3 bar chart; S7 closing stats |
| Plugin architecture (mechanic registry) | S6 | Implicit in mechanic dispatch |
| Zustand store (multi-mechanic) | S5 | Implicit in gameplay state |
| dnd-kit interaction primitives | S6 | Visible in drag-drop clip |
| Learn/Test dual modes | S5 | Mode toggle demonstrated |
| Multi-scene composition | S5 | Mentioned in narration |
| Score contracts | S4 | Shown in blueprint JSON |
| Degradation tracking | S3 | Brief mention during assembly |
| Real-time observability | S3 | Full dashboard walkthrough |
| 50 curated games library | S6 | Mentioned in mechanic showcase |
| <60 second generation | S3, S7 | S3 timer; S7 closing |
| $0.48 per game | S3, S7 | S3 cost display; S7 closing stat |
| 90% VPR | S7 | Closing stat |
| WCAG accessibility | S5 | Quick mention in gameplay |

---

## Timing Summary

| Section | Start | End | Duration | Content |
|---------|-------|-----|----------|---------|
| 1 | 0:00 | 0:20 | 20s | Hook + problem statement |
| 2 | 0:20 | 0:40 | 20s | Input interface demo |
| 3 | 0:40 | 1:10 | 30s | Pipeline observability walkthrough |
| 4 | 1:10 | 1:25 | 15s | Blueprint inspection |
| 5 | 1:25 | 1:50 | 25s | Heart trace-path gameplay |
| 6 | 1:50 | 2:20 | 30s | 6-mechanic rapid showcase |
| 7 | 2:20 | 2:30 | 10s | Closing stats + CTA |
| **Total** | | | **150s** | |

---

## Production Notes

### Recording Setup
- Use screen recording software (OBS or similar) at 1080p 60fps
- Browser should be Chrome, clean profile (no bookmarks bar, no extensions visible)
- Font size: 100% zoom or slight increase for readability
- Close all notifications and other apps

### Audio
- Record voiceover separately in a quiet environment
- Microphone: USB condenser or lapel mic
- Pace: ~2.5 words/second (natural academic presentation speed)
- Total word count: ~375 words

### Editing
- Smooth transitions between sections (0.3s crossfade)
- Section 6 uses hard cuts for energy
- Cursor highlight effect (subtle yellow circle) for visibility
- Add section titles as brief lower-third overlays
- Background music: subtle, royalty-free academic/tech track (low volume, -20dB under voice)

### Captions
- Add burned-in English subtitles for accessibility
- White text with semi-transparent dark background
- Position: bottom 10% of frame

### Export
- Format: MP4 (H.264)
- Resolution: 1920×1080
- Bitrate: 8–10 Mbps
- Also export as WebM for web embedding
