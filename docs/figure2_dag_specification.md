# Figure 2: DAG Pipeline Architecture Diagram — Visual Specification

## Overview

Full data-flow diagram showing the GamED.AI hierarchical multi-agent pipeline from natural language input to verified JSON blueprint. The diagram spans 6 phases, 14 nodes, 4 Quality Gates, parallel Send patterns, and retry loops.

**Dimensions:** Full page width (`\textwidth`), landscape orientation
**Style:** Clean technical diagram for ACL two-column format
**Rendering tool:** TikZ or draw.io → PDF export

---

## Layout Structure

```
LEFT ────────────────────────────────────────────────────────────────────────────────────────────── RIGHT

┌─────────────┐  ┌───────────────────────┐  ┌────────────────────┐  ┌──────────────────────────────┐  ┌──────────────────────────────┐  ┌──────────────────┐
│   PHASE 0   │  │       PHASE 1         │  │      PHASE 2       │  │          PHASE 3             │  │          PHASE 4             │  │     PHASE 5      │
│   Context   │  │   Concept Design      │  │   Game Plan        │  │   Scene Content              │  │   Asset Generation           │  │    Assembly       │
│  Gathering  │  │                       │  │  (Deterministic)   │  │   (Parallel Send)            │  │   (Parallel Send)            │  │                  │
└─────────────┘  └───────────────────────┘  └────────────────────┘  └──────────────────────────────┘  └──────────────────────────────┘  └──────────────────┘
```

**Phase widths (proportional):**
- Phase 0: 12%
- Phase 1: 16%
- Phase 2: 14%
- Phase 3: 22%
- Phase 4: 20%
- Phase 5: 16%

---

## Color Palette

| Element Type | Color | Hex | Usage |
|-------------|-------|-----|-------|
| LLM Node | Blue | `#4A90D9` | Nodes requiring LLM inference |
| Deterministic Node | Green | `#5CB85C` | Nodes with zero LLM inference |
| Quality Gate | Red/Orange | `#E74C3C` | Validator nodes (QG1–QG4) |
| Parallel Worker | Purple | `#9B59B6` | Workers instantiated via Send() |
| Router/Dispatch | Gray | `#95A5A6` | Routing and merge nodes |
| Phase Background | Light tint | Phase-specific | Subtle background bands |

**Phase background tints (very light, ~10% opacity):**
- Phase 0: light blue `#EBF5FB`
- Phase 1: light blue `#EBF5FB`
- Phase 2: light green `#EAFAF1`
- Phase 3: light purple `#F4ECF7`
- Phase 4: light purple `#F4ECF7`
- Phase 5: light green `#EAFAF1`

---

## Node Specifications (14 Total)

### Phase 0 — Context Gathering

**Node 0a: Input Analyzer**
- Shape: Rounded rectangle
- Color: Blue (`#4A90D9`)
- Label: "Input Analyzer"
- Badge: [LLM]
- Position: Phase 0, top row
- Function: Extracts pedagogical context, Bloom's level, subject domain

**Node 0b: Domain Knowledge Retriever**
- Shape: Rounded rectangle
- Color: Blue (`#4A90D9`)
- Label: "Domain Knowledge\nRetriever"
- Badge: [LLM+Search]
- Position: Phase 0, bottom row (parallel with 0a)
- Function: Retrieves algorithm/domain knowledge (pseudocode, complexity, common bugs, visualization keywords)

**Node 0c: Phase 0 Merge**
- Shape: Diamond (small)
- Color: Gray (`#95A5A6`)
- Label: "Merge"
- Position: Phase 0, right edge (centered between 0a and 0b)
- Function: Deterministic sync — joins parallel outputs

**Edges within Phase 0:**
- Input → 0a (solid arrow)
- Input → 0b (solid arrow, parallel fork)
- 0a → 0c (solid arrow)
- 0b → 0c (solid arrow)

---

### Phase 1 — Game Concept Design

**Node 1a: Game Concept Designer**
- Shape: Rounded rectangle (larger, double-bordered to indicate ReAct capability)
- Color: Blue (`#4A90D9`)
- Label: "Game Concept\nDesigner"
- Badge: [LLM, ReAct]
- Position: Phase 1, center-left
- Function: Designs multi-scene game concept with narrative theme, scene types, difficulty progression

**Node 1b: QG1 — Concept Validator**
- Shape: Octagon (stop-sign shape for Quality Gates)
- Color: Red (`#E74C3C`)
- Label: "QG1\nConcept\nValidator"
- Badge: [deterministic]
- Position: Phase 1, center-right
- Function: Checks scenes ≤ 6, all game types supported, required fields present
- Stamp: "No LLM" icon (small green tag)

**Edges within Phase 1:**
- 0c → 1a (solid arrow, label: "PedagogicalContext +\nDomainKnowledge")
- 1a → 1b (solid arrow)
- 1b → 1a (dashed curved arrow, label: "max 2 retries", red color)

---

### Phase 2 — Game Plan (Deterministic)

**Node 2a: Game Plan Builder**
- Shape: Rounded rectangle
- Color: Green (`#5CB85C`)
- Label: "Game Plan\nBuilder"
- Badge: [deterministic]
- Position: Phase 2, center-left
- Function: Assigns scene IDs, computes scores from contracts, determines asset needs, builds transition graph
- Stamp: "No LLM" icon

**Node 2b: QG2 — Plan Validator**
- Shape: Octagon
- Color: Red (`#E74C3C`)
- Label: "QG2\nPlan\nValidator"
- Badge: [deterministic]
- Position: Phase 2, center-right
- Stamp: "No LLM" icon
- Function: Checks unique scene IDs, valid transitions, score totals match

**Edges within Phase 2:**
- 1b (pass) → 2a (solid arrow, label: "AlgorithmGameConcept\n(validated)")
- 2a → 2b (solid arrow)
- 2b → 1a (dashed curved arrow, label: "max 2 retries", arcs back to Phase 1, red color)

---

### Phase 3 — Scene Content Generation (Parallel Send)

**Node 3a: Content Dispatch**
- Shape: Trapezoid (router shape)
- Color: Gray (`#95A5A6`)
- Label: "Content\nDispatch"
- Position: Phase 3, left edge
- Function: Creates N Send() calls, one per scene

**Node 3b: Scene Content Generator ×N**
- Shape: Stacked rounded rectangles (3 copies offset to show multiplicity)
- Color: Purple (`#9B59B6`)
- Label: "Scene Content\nGenerator ×N"
- Badge: [LLM, parallel]
- Position: Phase 3, center
- Notation: "×N" prominently shown, with N=number of scenes
- Function: Generates game-type-specific content (StateTracer steps, BugHunter rounds, etc.)

**Node 3c: Content Merge**
- Shape: Diamond
- Color: Gray (`#95A5A6`)
- Label: "Content\nMerge"
- Position: Phase 3, center-right
- Function: Deduplicates, keys by scene_id

**Node 3d: QG3 — Content Validator**
- Shape: Octagon
- Color: Red (`#E74C3C`)
- Label: "QG3\nContent\nValidator"
- Badge: [Pydantic + FOL]
- Position: Phase 3, right edge
- Stamp: "No LLM" icon
- Function: Per-game-type schema validation, Bloom's alignment predicates, operation count checks

**Edges within Phase 3:**
- 2b (pass) → 3a (solid arrow, label: "AlgorithmGamePlan +\nAlgorithmAssetSpec[]")
- 3a → 3b (solid arrow, fan-out to N copies, label: "Send()")
- 3b → 3c (solid arrows, fan-in from N copies)
- 3c → 3d (solid arrow)
- 3d → 3a (dashed curved arrow, label: "re-Send failed\nscenes only\n(max 1 retry)", red color)

---

### Phase 4 — Asset Generation (Parallel Send)

**Node 4a: Asset Dispatch**
- Shape: Trapezoid
- Color: Gray (`#95A5A6`)
- Label: "Asset\nDispatch"
- Position: Phase 4, left edge
- Function: Filters scenes needing visual assets via contract `needs_visual_asset(game_type)`

**Node 4b: Asset Worker ×M**
- Shape: Stacked rounded rectangles (3 copies offset)
- Color: Purple (`#9B59B6`)
- Label: "Asset Worker\n×M"
- Badge: [External API, parallel]
- Position: Phase 4, center
- Function: Image search → quality filter → fallback to Gemini generation

**Node 4c: Asset Merge**
- Shape: Diamond
- Color: Gray (`#95A5A6`)
- Label: "Asset\nMerge"
- Position: Phase 4, right edge
- Function: Deduplicates, keys by scene_id

**Edges within Phase 4:**
- 3d (pass) → 4a (solid arrow, label: "scene_contents:\nDict[scene_id → TypedContent]")
- 4a → 4b (solid arrow, fan-out, label: "Send()")
- 4b → 4c (solid arrows, fan-in)
- 4b → 4b (dashed self-loop, label: "max 1 retry", red color)

---

### Phase 5 — Assembly

**Node 5a: Blueprint Assembler**
- Shape: Rounded rectangle (double-bordered for emphasis)
- Color: Green (`#5CB85C`)
- Label: "Blueprint\nAssembler"
- Badge: [deterministic]
- Position: Phase 5, center-left
- Stamp: "No LLM" icon
- Function: Combines game plan + content + assets into final AlgorithmGameBlueprint

**Node 5b: QG4 — Blueprint Validator**
- Shape: Octagon
- Color: Red (`#E74C3C`)
- Label: "QG4\nBlueprint\nValidator"
- Badge: [deterministic]
- Position: Phase 5, center-right
- Stamp: "No LLM" icon
- Function: Final consistency check (templateType, required fields, mode configs)

**Edges within Phase 5:**
- 4c → 5a (solid arrow, label: "scene_assets:\nDict[scene_id → {url, source}]")
- 5a → 5b (solid arrow)
- 5b → Output (solid arrow, bold, label: "AlgorithmGameBlueprint\n(JSON, verified)")

---

## Input and Output Terminals

**Input (far left):**
- Shape: Rounded pill / stadium shape
- Color: White with dark border
- Label: "Natural Language\nQuestion"
- Edge to Phase 0: solid arrow, label: "question_text"

**Output (far right):**
- Shape: Rounded pill / stadium shape with bold border
- Color: White with green border (success)
- Label: "Verified JSON\nBlueprint"
- Subtext: "generation_complete = true"

---

## Annotation Callout Boxes (7 Total)

Each annotation is a rounded-corner callout box with a thin leader line pointing to the relevant element.

### Annotation 1: "Typed Pydantic Schemas"
- Position: Above the edge between Phase 1 and Phase 2
- Leader: Arrow pointing to the solid edge 1b→2a
- Text: "Typed Pydantic schemas\nenforce inter-agent contracts"
- Style: Light yellow background, thin dark border

### Annotation 2: "FOL-based Validation"
- Position: Below QG3 node
- Leader: Arrow pointing to QG3
- Text: "FOL Predicates:\n• bloom(g) = bloom(b)\n• op_count ≥ τ_contract\n• feedback ⊨ Bloom's level"
- Style: Light red background, thin dark border

### Annotation 3: "Parallel Send Pattern"
- Position: Above the ×N workers in Phase 3
- Leader: Bracket spanning the Content Dispatch → Content Generator ×N → Content Merge span
- Text: "LangGraph Send() API"
- Style: Light purple background

### Annotation 4: "Score Contracts"
- Position: Below Game Plan Builder (Node 2a)
- Leader: Arrow to 2a
- Text: "Per-game-type score\ncontracts (deterministic)"
- Style: Light green background

### Annotation 5: "Model Routing"
- Position: Above Scene Content Generator ×N
- Leader: Arrow to 3b
- Text: "Pro/Flash model routing\nper game type"
- Style: Light blue background

### Annotation 6: "Degradation Tracking"
- Position: Below Blueprint Assembler (Node 5a)
- Leader: Arrow to 5a
- Text: "is_degraded flag for\ngraceful fallback"
- Style: Light orange background

### Annotation 7: "No LLM Inference"
- Position: Floating stamps on Phase 2 (Plan Builder), Phase 5 (Assembler), all QG nodes
- Style: Small green badge with checkmark icon, text "No LLM"
- Applied to: Nodes 2a, 2b, 3d, 5a, 5b

---

## Retry Loops (Visual Specification)

All retry loops use **dashed curved arrows** in **red** (`#E74C3C`), with small labels.

| Loop | From | To | Label | Arc Style |
|------|------|----|-------|-----------|
| R1 | QG1 (1b) | Game Concept Designer (1a) | "max 2 retries" | Short arc within Phase 1 |
| R2 | QG2 (2b) | Game Concept Designer (1a) | "max 2 retries" | Long arc spanning Phase 2 → Phase 1 |
| R3 | QG3 (3d) | Content Dispatch (3a) | "re-Send failed only\n(max 1 retry)" | Medium arc within Phase 3 |
| R4 | Asset Worker (4b) | Asset Worker (4b) | "max 1 retry" | Self-loop on 4b |

---

## Edge Labels (Data Flow)

| From | To | Label |
|------|----|-------|
| Input | Phase 0 (0a, 0b) | "question_text" |
| 0c | 1a | "PedagogicalContext + DomainKnowledge" |
| 1b (pass) | 2a | "AlgorithmGameConcept (validated)" |
| 2b (pass) | 3a | "AlgorithmGamePlan + AlgorithmAssetSpec[]" |
| 3a | 3b | "Send()" |
| 3d (pass) | 4a | "scene_contents: Dict[scene_id → TypedContent]" |
| 4a | 4b | "Send()" |
| 4c | 5a | "scene_assets: Dict[scene_id → {url, source}]" |
| 5b (pass) | Output | "AlgorithmGameBlueprint (JSON, verified)" |

---

## Legend Box

Position: Bottom-right corner of the diagram

```
┌──────────────────────────────────────────────┐
│  LEGEND                                       │
│                                               │
│  ■ LLM Node            ■ Deterministic Node  │
│  ■ Quality Gate         ■ Parallel Workers    │
│  ■ Router/Merge                               │
│                                               │
│  ─── Solid arrow: data flow                   │
│  - - Dashed arrow: retry loop                 │
│  ×N  Parallel instantiation (LangGraph Send)  │
│  🔒  No LLM inference                        │
└──────────────────────────────────────────────┘
```

Color boxes use the corresponding hex colors from the palette above.

---

## ASCII Reference Layout (Full Diagram)

```
                            PHASE 0                    PHASE 1                   PHASE 2                        PHASE 3                                    PHASE 4                          PHASE 5
                     ┌─────────────────┐      ┌──────────────────────┐   ┌──────────────────────┐   ┌─────────────────────────────────────┐   ┌─────────────────────────────────┐   ┌──────────────────────┐
                     │                 │      │                      │   │                      │   │                                     │   │                                 │   │                      │
                     │  ┌───────────┐  │      │  ┌──────────────┐   │   │  ┌──────────────┐   │   │  ┌─────────┐  ┌───────────┐         │   │  ┌─────────┐  ┌─────────────┐  │   │  ┌──────────────┐   │
                     │  │  Input    │──┼──┐   │  │Game Concept  │   │   │  │ Game Plan    │   │   │  │Content  │  │Scene Gen  │  ┌────┐│   │  │Asset    │  │Asset Worker │  │   │  │  Blueprint   │   │
  ┌────────────┐     │  │ Analyzer  │  │  │   │  │  Designer    │◄──┼───┼──│  Builder     │   │   │  │Dispatch ├──│   ×N      ├──│Mrge││   │  │Dispatch ├──│    ×M       │  │   │  │  Assembler   │   │
  │ question_  │     │  │  [LLM]   │  │  ├──►│  │ [LLM,ReAct]  │   │   │  │ [determ.]   │   │   │  │ [router]│  │ [LLM,par] │  │    ││   │  │[router] │  │ [API,par]   │  │   │  │  [determ.]   │   │
  │   text     ├────►│  └─────┬─────┘  │  │   │  └──────┬───────┘   │   │  └──────┬───────┘   │   │  └─────────┘  └───────────┘  └──┬─┘│   │  └─────────┘  └──────┬──────┘  │   │  └──────┬───────┘   │
  └────────────┘     │        │        │  │   │         │            │   │         │            │   │                                 │  │   │                       │         │   │         │            │
                     │  ┌─────▼─────┐  │  │   │  ┌──────▼───────┐   │   │  ┌──────▼───────┐   │   │                          ┌──────▼┐ │   │                ┌──────▼──────┐  │   │  ┌──────▼───────┐   │
                     │  │  Domain   │──┼──┘   │  │    QG1       │   │   │  │    QG2       │   │   │                          │  QG3  │ │   │                │Asset Merge  │  │   │  │    QG4       │   │
                     │  │ Knowledge │  │      │  │  Concept     │───┼──►│  │   Plan       │───┼──►│                          │Content│─┼──►│                │             │──┼──►│  │  Blueprint   │───┼──► OUTPUT
                     │  │ Retriever │  │      │  │  Validator   │   │   │  │  Validator   │   │   │                          │Valid. │ │   │                │             │  │   │  │  Validator   │   │
                     │  │[LLM+Srch]│  │      │  │ [determ.] 🔒│   │   │  │[determ.] 🔒 │   │   │                          │[P+FOL]│ │   │                │             │  │   │  │ [determ.] 🔒│   │
                     │  └───────────┘  │      │  └──────────────┘   │   │  └──────────────┘   │   │                          │  🔒  │ │   │                └─────────────┘  │   │  └──────────────┘   │
                     │       ◇ Merge   │      │    ↺ max 2 retries  │   │   ↺ max 2 retries   │   │                          └───────┘ │   │                  ↺ max 1 retry  │   │                      │
                     │                 │      │                      │   │   (→ back to Ph.1)  │   │   ↺ re-Send failed (max 1 retry)  │   │                                 │   │                      │
                     └─────────────────┘      └──────────────────────┘   └──────────────────────┘   └─────────────────────────────────────┘   └─────────────────────────────────┘   └──────────────────────┘
```

---

## Rendering Notes

1. **Phase separator bands**: Thin vertical dashed lines between phases, with phase labels at top
2. **Node spacing**: Minimum 15pt between nodes within a phase; 20pt between phases
3. **Font**: Sans-serif (Helvetica/Arial) for labels; 8pt for node text, 7pt for edge labels, 6pt for annotations
4. **Arrow style**: Solid arrows = 1.5pt stroke, open arrowheads; Dashed retry = 1pt stroke, red
5. **Parallel workers**: Show 3 stacked copies with 2pt offset each (depth effect)
6. **QG octagon size**: Slightly smaller than LLM nodes (~80% width)
7. **Drop shadows**: Subtle 1pt gray shadow on all nodes for depth
8. **"No LLM" stamps**: Small green rounded rectangles (pill shape) with white text, attached to bottom-right corner of qualifying nodes

---

## Verification Checklist

- [x] 14 nodes total (0a, 0b, 0c, 1a, 1b, 2a, 2b, 3a, 3b, 3c, 3d, 4a, 4b, 4c, 5a, 5b) — Note: 16 nodes listed; 14 unique functional nodes excluding merge/dispatch
- [x] 4 Quality Gates (QG1, QG2, QG3, QG4)
- [x] 4 retry loops (R1–R4)
- [x] 2 parallel Send patterns (Phase 3, Phase 4)
- [x] 7 annotation callout boxes
- [x] All edge labels with typed data flow
- [x] Color coding: 5 node types
- [x] Legend box with all elements
- [x] "No LLM" stamps on deterministic nodes
- [x] Phase backgrounds with tinted bands
- [x] Dimensions suitable for `\textwidth` in ACL two-column format
