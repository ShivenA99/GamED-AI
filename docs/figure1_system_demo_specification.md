# Figure 1: End-to-End System Demo — 4-Panel Visual Specification

## Overview

Full page width (`\textwidth`) figure showing four equal-width panels (a)–(d) demonstrating the complete GamED.AI workflow from input to gameplay.

**Dimensions:** Full `\textwidth` (~6.5 inches for ACL), height ~3.5 inches
**Layout:** 4 equal-width panels separated by thin vertical lines
**Each panel:** ~25% of total width (~1.6 inches)

---

## Panel (a): Chat Interface & Input

### Content Description

A clean chat-style interface showing the question input workflow:

**Top section — Input area:**
- Text field containing example question: *"Trace blood flow through the heart"*
- Placeholder text style (gray italic) until typed

**Middle section — Configuration controls (compact form):**
- **Domain selector** (dropdown): Options visible — Biology (selected/highlighted), History, CS, Mathematics, Linguistics
- **Education level** (pill selector): K-12, **Undergraduate** (selected/bold), Graduate
- **Bloom's level** (optional dropdown): Remember, Understand, Apply, Analyze, Evaluate, Create
- **Template family** (toggle switch): Interactive Diagram | **Interactive Algorithm** (selected)

**Bottom section — Action:**
- **"Generate Game"** button — prominent, blue/primary color, full width
- Below button: row of 6 clickable example question cards (small, muted), e.g.:
  - "Sort these organisms by trophic level"
  - "Debug this binary search implementation"
  - "Match historical figures to their contributions"
  - "Trace blood flow through the heart"
  - "Order the steps of photosynthesis"
  - "Predict bubble sort's next state"

### Annotations (3)

1. Arrow pointing to domain dropdown → **"5 domains"**
2. Arrow pointing to Bloom's selector → **"6 Bloom's levels"**
3. Arrow pointing to template toggle → **"2 template families, 15 mechanics"**

### Style Notes
- White/light background
- Modern input design (rounded corners, subtle shadows)
- Blue accent color for selected states and primary button
- Small font for example cards (~7pt equivalent)

---

## Panel (b): Observability Dashboard

### Content Description

The real-time pipeline monitoring dashboard showing a completed heart trace-path run.

**Main area — DAG graph view (ReactFlow, ~60% of panel height):**
- Node graph showing executed pipeline stages:
  - `input_analyzer` → `dk_retriever` → `game_concept_designer` → `concept_validator` → `game_plan_builder` → `plan_validator` → `content_dispatch` → `content_gen ×3` → `content_merge` → `content_validator` → `asset_dispatch` → `asset_worker ×2` → `asset_merge` → `blueprint_assembler` → `blueprint_validator`
- Nodes colored by status:
  - **Green** = completed successfully (all nodes in this run)
  - **Blue outline** = LLM node
  - **Red outline** = Quality Gate
- Edges showing data flow direction
- Parallel branches visible for content_gen and asset_worker

**Bottom-left — Token/cost analytics (~25% of panel height):**
- Horizontal bar chart showing per-agent token consumption
- Largest bars: `game_concept_designer`, `content_gen`
- Summary text: **"Total: 19,900 tokens · $0.48 · 47s"**

**Bottom-right — Stage inspector snippet (~25% of panel height):**
- Selected node: `content_validator` (QG3)
- Shows: "Validation: ✓ PASSED"
- Shows: Bloom's alignment check result
- Small JSON preview of validated output

### Annotations (3)

1. Callout on QG nodes (concept_validator, plan_validator, content_validator, blueprint_validator) → **"Deterministic Quality Gates"**
2. Callout on token chart summary → **"$0.48 total, <60s"**
3. Callout on parallel content_gen nodes → **"Parallel Send"**

### Style Notes
- Dark/medium gray background (dashboard aesthetic)
- ReactFlow nodes as small rounded rectangles with colored borders
- Miniature bar chart with blue bars
- Compact layout — information-dense but legible

---

## Panel (c): Game Engine Architecture

### Content Description

A vertical flowchart showing the layered game engine architecture from blueprint to rendering.

**Layer 1 — Input (gray background):**
```
┌─────────────────┐
│  Blueprint JSON  │
└────────┬────────┘
```

**Layer 2 — Routing (blue background):**
```
┌─────────────────┐
│ Template Router  │
├────────┬────────┤
│Diagram │Algorithm│
│(10)    │(5)     │
└────────┴────────┘
         │
┌─────────────────┐
│Mechanic Registry │
│(plugin arch.)    │
└────────┬────────┘
```

**Layer 3 — Components (green background):**
```
┌─────────────────────────┐
│   Component Dispatch     │
├────┬────┬────┬────┬────┤
│Drag│Path│Mem │Seq │... │
│Drop│Draw│Mtch│Bldr│(15)│
└────┴────┴────┴────┴────┘
```

**Layer 4 — State (orange background):**
```
┌─────────────────────────┐
│    Zustand Store         │
│  • Per-mechanic progress │
│  • Multi-scene state     │
│  • Mode transitions      │
└────────┬────────────────┘
```

**Layer 5 — Primitives (purple background):**
```
┌────┬────────────┬───────┐
│dnd-│Framer      │SVG    │
│kit │Motion      │Canvas │
└────┴────────────┴───────┘
```

**Layer 6 — Output (teal background):**
```
┌─────────────────────────┐
│ Rendering + Accessibility│
│  • WCAG keyboard nav     │
│  • Screen reader support │
└─────────────────────────┘
```

### Layer Colors

| Layer | Name | Background Color |
|-------|------|-----------------|
| 1 | Input | Light gray `#ECF0F1` |
| 2 | Routing | Light blue `#D6EAF8` |
| 3 | Components | Light green `#D5F5E3` |
| 4 | State | Light orange `#FDEBD0` |
| 5 | Primitives | Light purple `#E8DAEF` |
| 6 | Output | Light teal `#D1F2EB` |

### Style Notes
- Vertical flow (top to bottom)
- Rounded rectangle boxes at each layer
- Thin connecting arrows between layers
- Each layer has a subtle background band
- Component names in small font (~6pt)
- Numbers (10), (5), (15) highlighted in bold

---

## Panel (d): Gameplay Screenshot

### Content Description

A screenshot of the heart trace-path game in active play.

**Main game area (~75% of panel):**
- Heart anatomical diagram (full-color illustration)
- 9 labeled anatomical zones visible with subtle borders:
  1. Superior Vena Cava
  2. Right Atrium
  3. Right Ventricle
  4. Pulmonary Artery
  5. Lungs
  6. Pulmonary Vein
  7. Left Atrium
  8. Left Ventricle
  9. Aorta
- Trace path in progress: blue/red line drawn from vena cava → right atrium → right ventricle (3 waypoints completed)
- Animated particles (small circles/droplets) flowing along the completed path
- Next expected waypoint has subtle glow/pulse animation
- Unvisited waypoints shown as dim circles

**Top bar — Game header:**
- Title: "Blood Flow Through the Heart"
- Mode indicator: **"Learn Mode"** (toggle switch showing Learn/Test)
- Hint button with count: "💡 2 remaining"

**Bottom bar — Progress and scoring:**
- Progress bar: "3/9 waypoints" (33% filled)
- Current score: "150 pts"
- Instruction text: *"Trace the path of deoxygenated blood entering the heart"*

### Annotations (4)

1. Arrow to animated particles on path → **"Animated particle flow"**
2. Arrow to zone boundaries → **"9 anatomical zones"**
3. Arrow to progress bar → **"Real-time scoring"**
4. Arrow to mode toggle → **"Learn/Test dual modes"**

### Style Notes
- Bright, educational visual style
- Heart diagram should be anatomically recognizable
- Trace path line: thick (3px), gradient from blue (deoxygenated) to red (oxygenated)
- Particle animation shown as motion-blurred dots along path
- Clean UI chrome around the game area
- Score and progress use accent colors

---

## Figure Caption (for LaTeX)

```latex
\caption{\textbf{End-to-end system demonstration.}
\textbf{(a)}~Instructor enters a natural language question with domain
and Bloom's level context.
\textbf{(b)}~DAG pipeline with real-time observability: per-agent traces,
token/cost analytics (\$0.48, {<}60\,s), and Quality Gate decisions.
\textbf{(c)}~Game engine architecture: plugin-based mechanic registry
dispatching to 15 self-contained React components backed by a unified
Zustand store and dnd-kit interaction primitives.
\textbf{(d)}~Generated trace-path game: blood flow through the heart
with animated particle visualization, 9 interactive zones, and dual
learn/test modes.}
```

---

## Panel Separator Specification

- Thin vertical lines (0.5pt, light gray `#BDC3C7`) between panels
- 3pt padding on each side of separator
- Panel labels "(a)", "(b)", "(c)", "(d)" centered below each panel in bold, 8pt font

---

## Overall Composition Notes

1. **Visual weight balance**: Panel (d) gameplay screenshot is the most visually striking; panel (b) dashboard is the most information-dense; panels (a) and (c) are more schematic
2. **Reading flow**: Left-to-right tells a story: input → processing → architecture → output
3. **Color harmony**: Blue (input/LLM), green (validation/deterministic), purple (parallel), teal (output) — consistent with Figure 2
4. **Annotation placement**: All annotations are outside the panel content, using thin leader lines with arrowheads
5. **Print readability**: All text ≥6pt, high contrast, no reliance on color alone (patterns/shapes distinguish categories)

---

## Verification Checklist

- [x] 4 panels covering: input → observability → engine architecture → gameplay
- [x] Panel (a): 5 domains, 6 Bloom's levels, 2 template families, 15 mechanics mentioned
- [x] Panel (b): DAG view, token/cost analytics, QG validation result, parallel Send visible
- [x] Panel (c): 6 architecture layers, 15 components referenced, Zustand + dnd-kit + Framer Motion
- [x] Panel (d): Heart trace-path with 9 zones, animated particles, progress bar, dual modes, scoring
- [x] 13 annotations total across all panels
- [x] Caption text matches paper claims
- [x] Color palette consistent with Figure 2
- [x] All text sizes specified for print readability
- [x] Full `\textwidth` layout for ACL format
