# New Mechanic Research: Interactive Diagram Assessment Platform

**Date:** 2026-02-11
**Purpose:** Identify new game mechanics for the GamED.AI Interactive Diagram template that test cognitive skills not covered by the existing 9 mechanics.
**Scope:** Assessment-first mechanics that work within the Interactive Diagram Game architecture (visual content + zones + interactions).

---

## Table of Contents

1. [Current Mechanic Coverage Analysis](#1-current-mechanic-coverage-analysis)
2. [Proposed New Mechanics](#2-proposed-new-mechanics)
   - [2.1 Predict-Observe-Explain (POE)](#21-predict-observe-explain-poe)
   - [2.2 Spot-the-Error](#22-spot-the-error)
   - [2.3 Cloze / Fill-in-Blank on Diagrams](#23-cloze--fill-in-blank-on-diagrams)
   - [2.4 Process Builder](#24-process-builder)
   - [2.5 Cause-Effect Chain](#25-cause-effect-chain)
   - [2.6 Annotation / Drawing](#26-annotation--drawing)
   - [2.7 Measurement / Scale Reading](#27-measurement--scale-reading)
   - [2.8 Elimination / Deduction Grid](#28-elimination--deduction-grid)
   - [2.9 Hotspot Multi-Select](#29-hotspot-multi-select)
   - [2.10 Claim-Evidence-Reasoning (CER)](#210-claim-evidence-reasoning-cer)
3. [Cognitive Skill Gap Matrix](#3-cognitive-skill-gap-matrix)
4. [Implementation Priority Summary](#4-implementation-priority-summary)
5. [Architecture Impact Assessment](#5-architecture-impact-assessment)
6. [Sources](#6-sources)

---

## 1. Current Mechanic Coverage Analysis

The existing 9 mechanics and the primary cognitive skill each tests:

| # | Mechanic | Primary Cognitive Skill | Input Modality |
|---|----------|------------------------|----------------|
| 1 | `drag_drop` | Recognition + spatial mapping | Drag label to zone |
| 2 | `click_to_identify` | Recognition from prompt | Click on zone |
| 3 | `trace_path` | Sequential spatial reasoning | Click waypoints in order |
| 4 | `sequencing` | Temporal/procedural ordering | Reorder items |
| 5 | `sorting_categories` | Classification/categorization | Drag items to categories |
| 6 | `description_matching` | Comprehension + association | Match text to zone |
| 7 | `memory_match` | Working memory + association | Flip card pairs |
| 8 | `branching_scenario` | Decision-making under conditions | Choose options |
| 9 | `compare_contrast` | Analytical comparison | Categorize zone attributes |

**Cognitive skills NOT covered by the current 9:**

- **Free recall** (all current mechanics use recognition, not recall)
- **Error detection / critical evaluation** (no mechanic asks "what is wrong here?")
- **Prediction / hypothesis formation** (no mechanic asks "what will happen if...?")
- **Construction / assembly** (no mechanic asks "build this system from parts")
- **Causal reasoning** (sequencing tests order, not cause-effect relationships)
- **Spatial annotation / marking** (no freeform drawing or marking on diagrams)
- **Quantitative estimation** (no mechanic tests measurement or reading scales)
- **Deductive elimination** (no mechanic tests process-of-elimination reasoning)
- **Evidence-based argumentation** (no mechanic tests claim + evidence + reasoning)
- **Multi-select identification** (click_to_identify is single-select sequential)

---

## 2. Proposed New Mechanics

### 2.1 Predict-Observe-Explain (POE)

**Mechanic ID:** `predict_observe_explain`

#### Description

Students are shown a diagram in its initial state and asked to predict what will happen when a specific parameter or condition changes. After submitting their prediction, the diagram transitions to show the actual outcome. Students then explain the discrepancy (or confirmation) between their prediction and the observed result.

This is a three-phase interaction within a single mechanic:
1. **Predict phase**: Student selects or types what they expect to happen (e.g., "blood pressure will increase in the pulmonary artery")
2. **Observe phase**: The diagram animates or transitions to reveal the actual outcome
3. **Explain phase**: Student selects or writes an explanation for why the outcome occurred

#### Cognitive Skill Tested

**Hypothesis formation and metacognitive monitoring.** POE tests whether students can form mental models of systems and identify gaps between their intuitions and actual behavior. Research by White and Gunstone (1992) developed POE specifically to surface student misconceptions. Students with strong intuitions that do not match scientific accounts are revealed through their incorrect predictions, making this mechanic particularly effective at detecting and addressing misconceptions.

#### Examples

- **Circulatory system**: "What happens to blood flow if the aortic valve closes?" -- predict affected zones, observe animation, explain
- **Electrical circuit**: "What happens to brightness of Bulb B if Resistor A is removed?" -- predict, observe, explain
- **Ecosystem food web**: "What happens to the rabbit population if wolves are removed?" -- predict cascade effects

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `PredictionPanel` | React component | UI for submitting predictions (multi-select zones, slider for magnitude, text input) |
| `StateTransition` | Animation system | Before/after diagram states with interpolated transition animation |
| `ExplanationInput` | React component | Structured text area or multiple-choice explanation options |
| `PredictionMarker` | SVG overlay | Visual markers on zones showing predicted vs actual changes |
| `ConfidenceSlider` | React component | Optional: student rates confidence in their prediction (0-100%) |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Base diagram | Image/SVG | The diagram in its initial state |
| Altered state diagram(s) | Image/SVG or animation keyframes | The diagram after the parameter change |
| Parameter definition | JSON config | What changes and what effects it causes |
| Prediction options | JSON array | Valid prediction choices (zone IDs + expected change) |
| Explanation rubric | JSON array | Accepted explanations with scoring weights |

#### Configurable Properties

```typescript
interface POEConfig {
  // Parameter being changed
  parameter: {
    id: string;
    label: string;
    changeDescription: string;  // "Remove Resistor A from the circuit"
    affectedZoneIds: string[];  // Zones that change
  };
  // Prediction phase
  predictionType: 'select_zones' | 'select_outcomes' | 'free_text' | 'slider';
  predictionOptions?: Array<{
    id: string;
    text: string;
    isCorrect: boolean;
    partialCredit?: number;  // 0-1
  }>;
  // Observe phase
  transitionType: 'animate' | 'side_by_side' | 'overlay_diff';
  transitionDurationMs: number;
  // Explain phase
  explanationType: 'multiple_choice' | 'free_text' | 'structured_cer';
  explanationOptions?: Array<{
    id: string;
    text: string;
    isCorrect: boolean;
    misconception?: string;  // What misconception this wrong answer reveals
  }>;
  // Scoring
  predictionWeight: number;  // e.g., 0.3
  explanationWeight: number; // e.g., 0.7
  bonusForCorrectPrediction: number;
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: MEDIUM-HIGH. Requires a new 3-phase flow within the game state machine, plus diagram state transitions (which could reuse the existing `MotionPath` system for animation, or use simple image swaps).
- **Backend complexity**: MEDIUM. The pipeline already generates zone metadata; adding "parameter" and "altered state" data is a schema extension. The game_planner and interaction_designer agents would need POE-specific prompt instructions.
- **Asset generation**: MEDIUM. Requires generating two versions of a diagram (before/after), which maps well to the existing image pipeline if the parameter change produces a visually different diagram.
- **Scoring**: Auto-scorable for multiple-choice predictions and explanations. Free-text explanations would require LLM-based scoring or keyword matching.

#### Priority: **HIGH**

POE tests a fundamentally different cognitive skill (prediction/hypothesis) that no current mechanic covers. It has strong pedagogical backing in science education research and maps naturally to the diagram + zone architecture. The three-phase structure is novel but each phase individually resembles existing mechanics (select zones, observe animation, select explanation).

---

### 2.2 Spot-the-Error

**Mechanic ID:** `spot_the_error`

#### Description

Students are presented with a diagram that contains deliberate errors -- incorrect labels, misplaced structures, wrong connections, missing components, or incorrect quantities. Students must identify each error by clicking on the erroneous element and then selecting or providing the correct version.

This inverts the typical assessment pattern: instead of "label this correctly," the question becomes "find what is wrong and fix it." Research from IndiaBioscience demonstrates that students given flawed diagrams and asked to identify errors achieve deeper understanding than students learning from correct diagrams alone, provided they have baseline knowledge of the subject.

#### Cognitive Skill Tested

**Critical evaluation and error detection.** This tests a qualitatively different skill from recognition: students must have a strong internal model of correctness to detect violations. Unlike drag_drop (which provides the correct labels), spot-the-error forces students to generate correctness criteria internally and apply them analytically.

#### Examples

- **Cell biology diagram**: Mitochondria labeled as "chloroplast," nucleus drawn in cytoplasm with no membrane
- **Electrical circuit**: Ammeter connected in parallel (should be series), battery polarity reversed
- **Geography map**: Country borders drawn incorrectly, river flowing uphill, capital placed in wrong location
- **Chemistry structure**: Bond angles wrong, incorrect atom charges, molecular formula mismatch

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `ErrorMarker` | React component | Clickable overlay that students place on suspected errors |
| `CorrectionPanel` | React component | UI for specifying what the correct version should be (dropdown, text input, or drag replacement) |
| `ErrorManifest` | Data structure | List of all intentional errors with correct values and explanations |
| `DistractorZones` | Zone overlay | Valid (non-error) elements that students might mistakenly flag as errors |
| `ErrorCounter` | React component | Shows "X of Y errors found" progress |
| `FalsePositiveFeedback` | React component | Feedback when student flags a correct element as an error |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Error diagram | Image/SVG | The diagram with deliberate errors embedded |
| Error manifest | JSON | Array of `{ zoneId, errorType, incorrectValue, correctValue, explanation, difficulty }` |
| Correction options | JSON | Per-error: valid correction choices (if multiple-choice correction) |
| Correct diagram | Image/SVG | Optional: shown after completion for comparison |

#### Configurable Properties

```typescript
interface SpotTheErrorConfig {
  errors: Array<{
    id: string;
    zoneId: string;               // Zone containing the error
    errorType: 'wrong_label' | 'wrong_position' | 'wrong_connection' | 'missing_component' | 'extra_component' | 'wrong_value';
    incorrectValue: string;       // What is currently shown (wrong)
    correctValue: string;         // What it should be
    explanation: string;          // Why this is wrong
    difficulty: number;           // 1-5
    points: number;
  }>;
  correctionMode: 'select_from_options' | 'type_correction' | 'identify_only';
  allowFalsePositives: boolean;      // Whether flagging correct items loses points
  falsePositivePenalty: number;      // Points lost per false positive
  showErrorCount: boolean;           // Show "X errors to find" hint
  showCorrectDiagramAtEnd: boolean;  // Reveal correct version after completion
  partialCredit: boolean;            // Credit for finding error even if correction is wrong
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: MEDIUM. The core interaction (click on zone, provide correction) is similar to click_to_identify with an added correction step. The error manifest is a new data structure but straightforward.
- **Backend complexity**: MEDIUM. The pipeline needs to generate a diagram with intentional errors, which inverts the normal flow. The LLM agents can generate an error manifest alongside the diagram. The key challenge is ensuring errors are pedagogically meaningful rather than arbitrary.
- **Asset generation**: MEDIUM-HIGH. Generating a deliberately-incorrect diagram requires the image pipeline to either modify a correct diagram or generate one with embedded errors. For SVG diagrams this is straightforward; for photorealistic images, this may require inpainting or compositing.
- **Scoring**: Fully auto-scorable. Each error found + corrected = points. False positives can deduct points.

#### Priority: **HIGH**

Error detection is a fundamentally distinct cognitive skill from any of the current 9 mechanics. It has strong research backing for promoting deeper learning. The architecture maps well -- zones become error locations rather than label targets. The main challenge is asset generation (creating intentionally wrong diagrams), but for SVG-based diagrams this is highly feasible.

---

### 2.3 Cloze / Fill-in-Blank on Diagrams

**Mechanic ID:** `cloze_fill_blank`

#### Description

Students are shown a diagram where certain labels or values have been blanked out (removed or replaced with blank boxes). Instead of selecting from a provided list of labels (recognition), students must type the correct term from memory (recall). This is the diagram equivalent of a cloze deletion test.

The critical distinction from `drag_drop` is that drag_drop provides all correct answers in the label tray (recognition), while cloze_fill_blank requires students to produce the answer from memory (free recall). Research consistently shows that fill-in-the-blank tests assess deeper retention than multiple-choice or drag-and-drop because they require active retrieval from long-term memory rather than matching.

#### Cognitive Skill Tested

**Free recall / retrieval from memory.** Cloze tests demand that students generate the answer without any cues, which is cognitively harder than recognition tasks. This is the most direct test of whether a student has internalized terminology. Every current mechanic provides answer options; this is the only proposed mechanic where the student must produce the answer entirely from memory.

#### Examples

- **Anatomy diagram**: Heart diagram with chambers blanked out -- student types "left ventricle," "right atrium," etc.
- **Chemistry**: Periodic table section with element symbols removed -- student types "Na," "Cl," "Fe"
- **Geography**: Map with country/region names blanked -- student types the names
- **Biology**: Cell diagram with organelle names removed

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `BlankZoneInput` | React component | Text input field positioned over each blanked zone on the diagram |
| `FuzzyMatcher` | Utility | Levenshtein distance / phonetic matching for answer validation (handles typos, alternate spellings) |
| `AutocompleteHint` | React component | Optional: after N failed attempts, provide first letter or partial autocomplete |
| `AcceptedAnswers` | Data structure | Per-zone list of accepted answer variants (e.g., "left ventricle," "L. ventricle," "LV") |
| `SpellingFeedback` | React component | "Close! Check your spelling" vs "Incorrect" feedback |
| `RevealButton` | React component | Optional: reveal correct answer after max attempts |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Clean diagram | Image/SVG | The diagram with labels removed (blank zones visible) |
| Answer key | JSON | Array of `{ zoneId, acceptedAnswers: string[], caseSensitive: boolean, fuzzyThreshold: number }` |
| Hint progression | JSON | Optional: progressive hints per zone (first letter, syllable count, definition) |

#### Configurable Properties

```typescript
interface ClozeFillBlankConfig {
  blanks: Array<{
    id: string;
    zoneId: string;
    acceptedAnswers: string[];        // All valid answers (e.g., ["mitochondria", "mitochondrion"])
    caseSensitive: boolean;
    fuzzyMatchThreshold: number;      // 0-1, how close a typo must be (0.8 = allow 1-2 char difference)
    hintProgression?: string[];       // ["Starts with 'M'", "Has 12 letters", "Powerhouse of the cell"]
    points: number;
  }>;
  maxAttemptsPerBlank: number;        // 0 = unlimited
  showHintsAfterAttempts: number;     // Show first hint after N wrong attempts
  autocompleteAfterAttempts: number;  // 0 = never
  spellingTolerance: 'strict' | 'moderate' | 'lenient';
  showWordBank: boolean;             // If true, degrades to recognition (drag_drop equivalent)
  wordBankIncludesDistractors: boolean;
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: MEDIUM. The text input positioned over diagram zones is a new interaction pattern but straightforward. The fuzzy matcher is a well-solved problem (Levenshtein distance libraries exist). Autocomplete and hint progression add polish but are not required for MVP.
- **Backend complexity**: LOW-MEDIUM. The pipeline already generates zones with labels. Generating a "clean diagram" (labels removed) is already part of the image pipeline (the inpainting / label removal agents exist). The accepted answers list can be generated by the LLM agents based on domain knowledge.
- **Asset generation**: LOW. The existing `image_label_remover` and `smart_inpainter` agents already produce clean (unlabeled) diagrams. The blank zones are just the existing zone positions with input fields instead of drop targets.
- **Scoring**: Auto-scorable with fuzzy matching. Partial credit possible based on spelling closeness.

#### Priority: **HIGH**

This mechanic tests the only major cognitive skill (free recall) that is entirely absent from all 9 current mechanics. It has the lowest implementation cost of any proposed mechanic because it reuses the existing clean-diagram pipeline and zone positions. The fuzzy matcher is the only genuinely new component. The pedagogical value is extremely high: recognition (drag_drop) vs. recall (cloze) is the most fundamental distinction in memory testing.

---

### 2.4 Process Builder

**Mechanic ID:** `process_builder`

#### Description

Students are given a set of disconnected components (shapes, parts, nodes) in a palette and must assemble them into a functioning system by placing components on a canvas and drawing connections between them. This tests whether students understand not just the names of parts (tested by drag_drop) but how they relate to each other structurally.

Unlike `sequencing` (which orders pre-existing items linearly) or `sorting_categories` (which groups items), process_builder requires students to construct a graph/network from scratch -- placing nodes AND defining edges between them.

#### Cognitive Skill Tested

**Constructive synthesis and structural understanding.** Students must understand how components connect and interact, not merely what they are called. This tests system-level understanding: can the student build the system from parts? This is the constructive inverse of the analytical mechanics (drag_drop, click_to_identify).

#### Examples

- **Water cycle**: Given components (evaporation, condensation, precipitation, runoff, collection), connect them into a cycle diagram
- **Computer architecture**: Given CPU, RAM, bus, I/O controller, place them and draw data flow connections
- **Food web**: Given organisms, draw predator-prey arrows to form the correct food web
- **Electrical circuit**: Given battery, resistor, LED, wires, assemble a working circuit

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `ComponentPalette` | React component | Sidebar with draggable components (icons + labels) |
| `BuildCanvas` | React component | SVG canvas where components are placed and connected |
| `ConnectionDrawer` | SVG interaction | Click-and-drag to draw arrows/lines between component ports |
| `ConnectionValidator` | Logic | Validates whether connections match the correct graph structure |
| `SnapGrid` | Canvas feature | Optional grid snapping for clean layouts |
| `ComponentTooltip` | React component | Shows component description on hover |
| `GraphComparer` | Logic | Compares student-built graph against correct answer graph (topology, not position) |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Component sprites | SVG/PNG | Visual representation of each component |
| Background canvas | Image/SVG | Optional: background guide (e.g., body outline for organ placement) |
| Connection rules | JSON | Graph definition: `{ nodes: [...], edges: [{ from, to, label?, bidirectional? }] }` |
| Port definitions | JSON | Per-component: where connections can attach (top, bottom, left, right, or specific points) |
| Valid topologies | JSON | Optional: multiple valid arrangements if layout flexibility is allowed |

#### Configurable Properties

```typescript
interface ProcessBuilderConfig {
  components: Array<{
    id: string;
    label: string;
    description?: string;
    icon: string;               // SVG path or image URL
    maxInstances: number;       // How many of this component can be placed (usually 1)
    ports: Array<{
      id: string;
      position: 'top' | 'bottom' | 'left' | 'right' | { x: number; y: number };
      type: 'input' | 'output' | 'bidirectional';
    }>;
  }>;
  correctGraph: {
    edges: Array<{
      from: { componentId: string; portId?: string };
      to: { componentId: string; portId?: string };
      label?: string;           // e.g., "blood flow", "data bus"
      directed: boolean;
    }>;
  };
  // Scoring
  positionMatters: boolean;         // Whether component placement location is scored
  topologyOnly: boolean;            // Score only graph structure, ignore spatial layout
  partialCreditPerEdge: boolean;    // Credit for each correct connection
  includeDistractorComponents: boolean; // Extra components that should NOT be used
  distractorComponents?: Array<{ id: string; label: string; icon: string }>;
  // Canvas
  canvasBackground?: string;        // Background image URL
  snapToGrid: boolean;
  gridSize: number;
  showConnectionLabels: boolean;
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: HIGH. This is the most complex proposed mechanic. It requires a full graph editor with drag-and-drop placement, connection drawing (SVG path rendering between ports), and a graph comparison algorithm. Libraries like react-flow or custom SVG logic could accelerate development.
- **Backend complexity**: MEDIUM. The LLM agents need to generate component definitions and a correct graph structure. This is a natural extension of the existing game_planner and interaction_designer agents.
- **Asset generation**: MEDIUM. Component sprites can be generated by the existing image pipeline or use SVG icons. The background canvas is similar to existing diagram generation.
- **Scoring**: Auto-scorable. Graph isomorphism comparison (ignoring spatial layout) is a well-solved algorithmic problem. Partial credit per correct edge.

#### Priority: **MEDIUM**

The cognitive skill (constructive synthesis) is genuinely distinct and pedagogically valuable. However, the frontend complexity is significantly higher than other proposed mechanics. The graph editor interaction (drawing connections between nodes) is a substantial new UI paradigm. Recommended for Phase 2 after simpler mechanics are proven.

---

### 2.5 Cause-Effect Chain

**Mechanic ID:** `cause_effect_chain`

#### Description

Students are given a set of event cards describing causes and effects, and must arrange them into a causal chain (or causal graph). Unlike `sequencing` which tests temporal order ("what comes first, second, third"), cause-effect chain tests causal reasoning ("A causes B, and B causes C, but D is independent").

The key distinction from sequencing is that cause-effect chains can branch (one cause leading to multiple effects) and converge (multiple causes leading to one effect), forming a directed acyclic graph rather than a linear sequence.

#### Cognitive Skill Tested

**Causal reasoning and mechanistic understanding.** Students must understand WHY events are connected, not merely WHEN they happen. Research on causal reasoning shows it is fundamental to scientific literacy and distinct from temporal ordering. Prompting children to consider causal alternatives can scaffold both scientific inquiry and concept learning.

#### Examples

- **Climate science**: "Increased CO2 emissions" -> "Enhanced greenhouse effect" -> "Rising ocean temperatures" -> (branches to) "Coral bleaching" AND "Sea level rise"
- **Disease transmission**: "Virus enters host" -> "Viral replication" -> "Immune response" -> (branches to) "Recovery" OR "Chronic infection"
- **Economics**: "Central bank raises interest rates" -> "Borrowing costs increase" -> "Consumer spending decreases" -> "Economic growth slows"

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `EventCard` | React component | Draggable card with event description text |
| `ChainCanvas` | React component | Canvas where cards are arranged with causal arrows |
| `ArrowConnector` | SVG component | Directional arrows drawn between event cards |
| `BranchNode` | React component | Visual indicator where a chain branches into multiple effects |
| `ConvergeNode` | React component | Visual indicator where multiple causes merge |
| `ChainValidator` | Logic | Validates the directed graph structure against correct answer |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Event cards | JSON array | `{ id, text, description?, category?, isDistractor? }` |
| Correct chain | JSON graph | `{ edges: [{ cause: eventId, effect: eventId }] }` |
| Background diagram | Image/SVG | Optional: diagram that the causal chain relates to |

#### Configurable Properties

```typescript
interface CauseEffectChainConfig {
  events: Array<{
    id: string;
    text: string;
    description?: string;
    category?: string;        // For color-coding: "biological", "chemical", etc.
    isDistractor?: boolean;   // Events that don't belong in the chain
    isRootCause?: boolean;    // Hint: this is a starting event
    isFinalEffect?: boolean;  // Hint: this is an end event
  }>;
  correctChain: {
    edges: Array<{
      causeId: string;
      effectId: string;
      explanation?: string;   // Why this causal link exists
    }>;
  };
  chainType: 'linear' | 'branching' | 'converging' | 'complex';
  allowBranching: boolean;
  allowConverging: boolean;
  showStartingEvent: boolean;       // Reveal the root cause as a hint
  partialCreditPerEdge: boolean;
  includeDistractorEvents: boolean;
  showCausalExplanations: boolean;  // Show "why" after completion
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: MEDIUM-HIGH. Similar to process_builder but simpler because events are text-only cards (no sprites/ports). The arrow-drawing interaction between cards is the main challenge, but simpler than the full graph editor since cards have fixed connection points.
- **Backend complexity**: LOW-MEDIUM. LLM agents can naturally generate cause-effect chains from domain knowledge. The chain structure is a straightforward directed graph.
- **Asset generation**: LOW. Events are text-based. The optional background diagram uses the existing pipeline.
- **Scoring**: Auto-scorable. Compare student's directed graph edges against correct answer. Partial credit per correct edge.

#### Priority: **MEDIUM-HIGH**

Causal reasoning is a critical cognitive skill for science education, and is genuinely distinct from temporal sequencing. The frontend complexity is moderate -- simpler than process_builder but more complex than sequencing. The backend cost is low. This could be implemented as a first step toward the full process_builder.

---

### 2.6 Annotation / Drawing

**Mechanic ID:** `annotation_drawing`

#### Description

Students draw directly on a diagram to annotate, highlight, circle, or mark specific features. This tests whether students can identify and spatially locate relevant features without the scaffold of pre-defined zones.

Unlike `click_to_identify` (where zones are pre-defined and students click them), annotation_drawing requires students to define the regions themselves, demonstrating precise spatial knowledge. Unlike `drag_drop` (where positions are pre-determined), annotation_drawing tests whether students know WHERE something is, not just WHAT it is called.

Supported annotation types:
- **Circle/highlight a region**: Draw an ellipse around a structure
- **Draw an arrow**: Point from one structure to another (e.g., "draw an arrow showing blood flow direction")
- **Place a pin/marker**: Mark a specific point on the diagram
- **Freehand draw**: Trace an outline or boundary
- **Add text note**: Place a text annotation at a specific location

#### Cognitive Skill Tested

**Spatial precision and self-directed identification.** Without pre-defined zones as scaffolding, students must demonstrate that they know the exact location, shape, and boundaries of structures. This is the most demanding spatial assessment: instead of recognizing a zone boundary drawn for them, students must generate the boundary from their own knowledge.

#### Examples

- **Anatomy**: "Circle the region where gas exchange occurs in the lungs" (student must draw around the alveoli)
- **Geography**: "Draw the path of the Gulf Stream on this ocean map"
- **Physics**: "Draw arrows showing the direction of electric field lines between these two charges"
- **Cell biology**: "Highlight all organelles involved in protein synthesis"

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `DrawingToolbar` | React component | Tool selector: circle, arrow, pin, freehand, text, eraser |
| `DrawingCanvas` | HTML5 Canvas or SVG | Transparent overlay on diagram for drawing |
| `AnnotationLayer` | React component | Manages all user-drawn annotations as objects |
| `SpatialScorer` | Logic | Compares drawn regions against expected regions (IoU/overlap calculation) |
| `AnnotationPrompt` | React component | Shows the current instruction/prompt for what to annotate |
| `UndoRedoStack` | Logic | Undo/redo for drawing actions (can reuse existing UndoRedoConfig) |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Base diagram | Image/SVG | Clean diagram to annotate |
| Expected annotations | JSON | Per-prompt: `{ type: 'circle'|'arrow'|'pin', expectedRegion: { x, y, radius } or { path }, tolerance: number }` |
| Prompts | JSON array | `{ prompt: string, annotationType: string, expectedRegion: {...} }` |

#### Configurable Properties

```typescript
interface AnnotationDrawingConfig {
  prompts: Array<{
    id: string;
    prompt: string;                     // "Circle the mitochondria"
    annotationType: 'circle' | 'arrow' | 'pin' | 'freehand' | 'text';
    expectedRegion: {
      type: 'circle' | 'polygon' | 'path' | 'point';
      // For circle: center + radius
      center?: { x: number; y: number };
      radius?: number;
      // For polygon: points array
      points?: [number, number][];
      // For path/arrow: start + end points
      start?: { x: number; y: number };
      end?: { x: number; y: number };
      // For point/pin
      point?: { x: number; y: number };
    };
    tolerancePercent: number;           // How close the student's annotation must be (0-100)
    points: number;
  }>;
  availableTools: ('circle' | 'arrow' | 'pin' | 'freehand' | 'text' | 'eraser')[];
  showGridOverlay: boolean;
  strokeColor: string;
  strokeWidth: number;
  allowMultipleAnnotations: boolean;    // Multiple annotations per prompt
  showExpectedAfterSubmit: boolean;     // Overlay correct annotation after grading
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: HIGH. A drawing canvas overlay on top of the diagram image requires HTML5 Canvas or SVG path rendering, touch/mouse event handling, and spatial comparison algorithms (Intersection over Union for region overlap). This is a substantially new UI component.
- **Backend complexity**: LOW-MEDIUM. The agents need to define expected annotation regions, which maps to the existing zone coordinate system.
- **Asset generation**: LOW. The base diagram is the existing diagram. Expected regions are defined as zone-like coordinates.
- **Scoring**: MEDIUM complexity. Spatial overlap scoring (IoU) for regions, proximity scoring for points/arrows. This requires custom geometry algorithms but is deterministic.

#### Priority: **MEDIUM**

Spatial precision testing is genuinely unique and pedagogically valuable. However, the drawing canvas is a significant frontend investment. The scoring algorithm (spatial overlap) adds complexity. Consider implementing a simplified version first (pin placement only) and expanding to full drawing tools later.

---

### 2.7 Measurement / Scale Reading

**Mechanic ID:** `measurement_reading`

#### Description

Students interact with measuring instruments overlaid on or adjacent to a diagram and must read values, set parameters, or estimate quantities. This tests quantitative literacy and the ability to interpret visual representations of data.

Instrument types:
- **Ruler/scale bar**: Measure the length of a structure in the diagram
- **Thermometer/gauge**: Read a value from a scale indicator
- **Protractor**: Measure an angle between structures
- **Graph/chart reader**: Read a data point from an embedded chart
- **Slider calibration**: Set a parameter to the correct value using a slider

#### Cognitive Skill Tested

**Quantitative estimation and instrument literacy.** No current mechanic tests numerical reasoning or the ability to read measurement instruments. This is critical for STEM assessment where students must interpret scales, units, and magnitudes.

#### Examples

- **Biology microscopy**: "What is the approximate length of this cell? Use the scale bar." (student enters value in micrometers)
- **Physics**: "Read the voltage from the voltmeter in this circuit diagram"
- **Chemistry**: "What is the pH indicated by this litmus paper color?"
- **Geography**: "Estimate the distance between these two cities using the map scale"

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `MeasurementTool` | React component | Visual measuring instrument (ruler, thermometer, gauge) overlaid on diagram |
| `ValueInput` | React component | Numeric input with unit selector |
| `ScaleBar` | SVG component | Draggable/resizable ruler or scale reference |
| `ToleranceScorer` | Logic | Scores based on how close the student's answer is to correct (within tolerance range) |
| `UnitConverter` | Logic | Optional: accepts answers in different units with automatic conversion |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Diagram with scale | Image/SVG | Diagram that includes a scale bar or measurement context |
| Measurement definitions | JSON | `{ zoneId, correctValue: number, unit: string, tolerance: number, instrumentType }` |
| Instrument visuals | SVG | Ruler, thermometer, protractor graphics |

#### Configurable Properties

```typescript
interface MeasurementReadingConfig {
  measurements: Array<{
    id: string;
    zoneId?: string;                  // Zone being measured (optional)
    prompt: string;                    // "Measure the length of structure A"
    instrumentType: 'ruler' | 'thermometer' | 'protractor' | 'gauge' | 'slider' | 'graph_reader';
    correctValue: number;
    unit: string;                      // "cm", "mL", "degrees", "pH"
    tolerance: number;                 // Acceptable deviation (e.g., +/- 0.5)
    toleranceType: 'absolute' | 'percentage';
    minValue?: number;                 // Range for slider instruments
    maxValue?: number;
    stepSize?: number;                 // Slider step
    points: number;
  }>;
  showInstrumentOverlay: boolean;      // Show the measuring tool on the diagram
  allowUnitConversion: boolean;        // Accept answers in different units
  significantFigures?: number;         // Required precision
  partialCreditByProximity: boolean;   // Closer answers get more credit
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: MEDIUM. The main challenge is rendering interactive measurement tools (draggable ruler, readable gauge) as SVG overlays. Each instrument type is a separate component but they share a common interaction pattern (position tool -> read value -> enter answer).
- **Backend complexity**: LOW. The agents generate measurement prompts with correct values and tolerances, which is straightforward numerical data.
- **Asset generation**: LOW-MEDIUM. The diagram itself is standard. Instrument overlays are reusable SVG components that don't need per-question generation.
- **Scoring**: Fully auto-scorable. Numeric comparison with tolerance band. Partial credit by proximity is a simple calculation.

#### Priority: **MEDIUM**

Quantitative assessment is important for STEM subjects and not covered by any current mechanic. The implementation is moderate -- each instrument type is a standalone component. However, the use cases are narrower than mechanics like cloze or POE (measurement only makes sense for certain diagram types). Consider implementing as a specialized mechanic for science/math content.

---

### 2.8 Elimination / Deduction Grid

**Mechanic ID:** `elimination_grid`

#### Description

Students solve a logic puzzle where they must deduce the correct assignment of properties to elements using a set of clues and an elimination grid. The diagram provides visual context, and clues reference structures visible in the diagram.

The elimination grid is a classic logic puzzle format where rows and columns represent different property categories, and students mark cells as "yes" (confirmed match) or "no" (eliminated). Each clue eliminates possibilities until only one valid assignment remains.

#### Cognitive Skill Tested

**Deductive reasoning and systematic elimination.** This is the only proposed mechanic that tests formal logical deduction -- the ability to combine multiple constraints to derive conclusions. No current mechanic requires multi-step logical inference.

#### Examples

- **Chemistry**: "Four elements are in these test tubes. Clue 1: The element with the highest atomic number is not in tube A. Clue 2: Sodium is next to Chlorine..." -- deduce which element is in which tube.
- **Anatomy**: "Five doctors are specialists in different organs. Clue 1: The cardiologist is not Dr. Smith. Clue 2: The neurologist's office is between the cardiologist and the dermatologist..." -- match doctors to specialties.
- **Ecology**: "Four species occupy different niches in this ecosystem. Clue 1: The apex predator is not Species B..."

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `EliminationGrid` | React component | Matrix grid with clickable cells (empty / X / checkmark) |
| `CluePanel` | React component | Scrollable list of clues, with used/unused status |
| `DiagramReference` | React component | The diagram with labeled zones that clues reference |
| `DeductionValidator` | Logic | Validates the completed grid against the correct solution |
| `ClueHighlighter` | Logic | When hovering a clue, highlights relevant zones/rows/columns |
| `ContradictionDetector` | Logic | Optional: warns student if their marks create a logical contradiction |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Diagram | Image/SVG | Visual diagram that the puzzle references |
| Grid definition | JSON | Categories (rows, columns), grid dimensions |
| Clues | JSON array | `{ id, text, references: [zoneIds], eliminates: [{ row, col }] }` |
| Solution | JSON | Correct grid state: `{ assignments: [{ entity, property }] }` |

#### Configurable Properties

```typescript
interface EliminationGridConfig {
  categories: Array<{
    id: string;
    label: string;                     // e.g., "Elements", "Test Tubes"
    items: Array<{ id: string; label: string }>;
  }>;
  clues: Array<{
    id: string;
    text: string;
    difficulty: number;                // 1-5, affects hint ordering
    referencedZoneIds?: string[];      // Zones in the diagram this clue references
  }>;
  solution: Record<string, string>;    // entity -> property assignments
  showContradictionWarning: boolean;   // Warn on logical contradictions
  showClueUsedStatus: boolean;         // Track which clues have been "used"
  allowPartialSubmission: boolean;     // Can submit with incomplete grid
  partialCreditPerCorrectAssignment: boolean;
  gridType: '2_category' | '3_category' | '4_category';  // Number of property dimensions
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: MEDIUM. The elimination grid is a well-defined UI pattern (matrix of clickable cells). The main complexity is the optional contradiction detector, which requires constraint propagation logic.
- **Backend complexity**: MEDIUM. The LLM agents need to generate a consistent set of clues that uniquely determine the solution. This is a constrained generation task that the agents can handle with careful prompting.
- **Asset generation**: LOW. The grid is entirely UI-rendered. The diagram uses the existing pipeline.
- **Scoring**: Auto-scorable. Compare student grid against solution grid. Partial credit per correct assignment.

#### Priority: **MEDIUM**

Deductive reasoning is a distinct and important cognitive skill. The elimination grid is a well-known puzzle format that students enjoy. However, it is less naturally "diagram-centric" than other mechanics -- the diagram serves as context rather than being the primary interaction surface. Best suited for content where visual context enhances the puzzle (e.g., test tubes in a chemistry diagram, locations on a map).

---

### 2.9 Hotspot Multi-Select

**Mechanic ID:** `hotspot_multi_select`

#### Description

Students are given a question and must select ALL correct regions on a diagram that match the criteria. Unlike `click_to_identify` (which presents one prompt at a time and expects one zone per prompt), hotspot_multi_select asks a single question and requires students to identify all matching zones simultaneously.

This is modeled after the Hotspot question type used extensively in standardized testing platforms (SBAC, PARCC) and commercial assessment tools (Learnosity, Blackboard). Assessment platforms offer three hotspot shapes: point, rectangle, and polygon. Hotspot questions enable testing of a student's ability to recognize specific features of an image, with automatic grading based on selection accuracy.

#### Cognitive Skill Tested

**Exhaustive identification and category-based visual search.** Students must scan the entire diagram and identify ALL instances that match a criterion, testing completeness of knowledge. Missing one correct zone or selecting an incorrect zone both indicate gaps. This is different from click_to_identify, which guides students through zones one-at-a-time with specific prompts.

#### Examples

- **Biology**: "Select ALL organelles involved in protein synthesis" (must select ribosome, rough ER, Golgi apparatus -- missing any one is incomplete)
- **Geography**: "Select ALL countries that border the Mediterranean Sea"
- **Physics**: "Select ALL points in this circuit where the current is at maximum"
- **Chemistry**: "Select ALL functional groups in this organic molecule"

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `HotspotSelector` | React component | Click to toggle zones as selected/deselected (multi-select mode) |
| `SelectionCounter` | React component | Shows "X selected" count (optionally shows "X of Y correct") |
| `SubmitButton` | React component | Explicit submit to lock in selections |
| `PartialCreditIndicator` | React component | After submission, highlights correct selections, missed zones, and false positives |
| `QuestionPrompt` | React component | The single question that defines the selection criteria |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Diagram | Image/SVG | Standard diagram with defined zones |
| Questions | JSON array | `{ prompt: string, correctZoneIds: string[], distractorZoneIds: string[] }` |

#### Configurable Properties

```typescript
interface HotspotMultiSelectConfig {
  questions: Array<{
    id: string;
    prompt: string;                     // "Select ALL organelles involved in..."
    correctZoneIds: string[];           // All zones that should be selected
    distractorZoneIds?: string[];       // Zones that look plausible but are wrong
    scoringMode: 'all_or_nothing' | 'partial_credit' | 'penalty_for_wrong';
    penaltyPerWrongSelection?: number;  // Points deducted per incorrect selection
    points: number;
  }>;
  showSelectionCount: boolean;         // "X zones selected"
  showExpectedCount: boolean;          // "Select X zones" hint
  requireExplicitSubmit: boolean;      // Must click "Submit" vs auto-grade
  highlightOnHover: boolean;
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: LOW. This is essentially a multi-select variant of the existing `click_to_identify` component. The zone rendering and click handling infrastructure already exists. The main change is allowing multiple simultaneous selections and an explicit submit action.
- **Backend complexity**: LOW. The agents already generate zones. The question format (prompt + list of correct zone IDs) is trivially generated.
- **Asset generation**: NONE (reuses existing diagram and zone pipeline).
- **Scoring**: Fully auto-scorable. Set comparison (student selections vs correct zone set). Multiple scoring modes (all-or-nothing, partial credit, penalty for false positives) are simple calculations.

#### Priority: **HIGH**

Extremely low implementation cost (extends existing click_to_identify) while testing a genuinely different skill (exhaustive identification vs. guided sequential identification). This mechanic appears in virtually all standardized testing platforms (SBAC, PARCC, Learnosity) and is widely understood by educators. This should be one of the first new mechanics implemented.

---

### 2.10 Claim-Evidence-Reasoning (CER)

**Mechanic ID:** `claim_evidence_reasoning`

#### Description

Students engage in structured scientific argumentation by constructing a three-part response: (1) make a **claim** about a diagram feature, (2) cite **evidence** from the diagram to support it, and (3) provide **reasoning** that connects the evidence to the claim using scientific principles.

The CER framework is widely used in science education (NGSS alignment) and was developed from Toulmin's argumentation structure. This mechanic can be interactive: students click on diagram zones as evidence, select claims from options, and construct reasoning from building blocks.

#### Cognitive Skill Tested

**Evidence-based argumentation and reasoning justification.** This is the only proposed mechanic that tests the ability to construct logical arguments from visual evidence. No current mechanic requires students to justify WHY something is true using evidence from the diagram. The reasoning component (explaining the link between evidence and claim) is the most demanding, as it requires applying scientific principles.

#### Examples

- **Biology**: Claim: "The mitochondria is the organelle most critical for cellular respiration." Evidence: (click on mitochondria zone, click on ATP molecule zone). Reasoning: "Mitochondria contain the enzymes for the Krebs cycle and electron transport chain, which produce the majority of ATP."
- **Chemistry**: Claim: "This reaction is exothermic." Evidence: (point to energy diagram showing products lower than reactants). Reasoning: "The energy of the products is lower than reactants, meaning energy was released."
- **Earth Science**: Claim: "This rock layer is older than the one above it." Evidence: (click on two strata zones). Reasoning: "The principle of superposition states that in undisturbed strata, older layers are deposited first and are found at the bottom."

#### Components

| Component | Type | Description |
|-----------|------|-------------|
| `ClaimSelector` | React component | Select or construct a claim (multiple-choice or free text) |
| `EvidenceSelector` | React component | Click zones on diagram to cite as evidence (multi-select) |
| `ReasoningBuilder` | React component | Structured reasoning input: select scientific principles and connect them to evidence |
| `CERScaffold` | React component | Visual framework showing claim-evidence-reasoning structure |
| `ArgumentStrength` | React component | Visual indicator of argument quality after submission |
| `CounterargumentChallenge` | React component | Optional: present a counterargument for the student to refute |

#### Assets Required

| Asset | Format | Description |
|-------|--------|-------------|
| Diagram | Image/SVG | Standard diagram with zones |
| Claims | JSON array | `{ id, text, isCorrect, category }` |
| Evidence mapping | JSON | `{ claimId -> [validEvidenceZoneIds] }` |
| Reasoning rubric | JSON | `{ claimId -> { principles: string[], requiredConnections: [...] } }` |
| Scientific principles bank | JSON array | Domain-specific principles students can reference |

#### Configurable Properties

```typescript
interface CERConfig {
  claims: Array<{
    id: string;
    text: string;
    isCorrect: boolean;
    category?: string;          // Topic/concept category
  }>;
  evidenceRules: Record<string, {   // Keyed by claimId
    requiredZoneIds: string[];       // Zones that MUST be cited
    optionalZoneIds?: string[];      // Additional valid evidence
    irrelevantZoneIds?: string[];    // Zones that don't support this claim
  }>;
  reasoningOptions?: Array<{
    id: string;
    text: string;                     // A scientific principle
    validForClaims: string[];        // Which claims this principle supports
  }>;
  responseMode: 'structured' | 'free_text' | 'building_blocks';
  claimMode: 'select_from_options' | 'free_text';
  evidenceMode: 'click_zones' | 'select_from_list';
  reasoningMode: 'select_principles' | 'arrange_blocks' | 'free_text';
  scoringWeights: {
    claim: number;           // e.g., 0.2
    evidence: number;        // e.g., 0.3
    reasoning: number;       // e.g., 0.5
  };
  showCounterargument: boolean;
  instructions?: string;
}
```

#### Feasibility Assessment

- **Frontend complexity**: MEDIUM-HIGH. The CER scaffold is a multi-part form with diagram interaction. The evidence selection (clicking zones) reuses existing infrastructure. The reasoning builder (selecting principles and connecting them) is new but manageable.
- **Backend complexity**: MEDIUM. The agents need to generate claims, evidence mappings, and reasoning rubrics. This is LLM-friendly content generation. Free-text reasoning scoring would require LLM-based evaluation.
- **Asset generation**: LOW. Reuses existing diagrams and zones. Claims and principles are text-based.
- **Scoring**: Auto-scorable for structured modes (select claim + click evidence + select principles). Free-text reasoning requires LLM scoring or keyword matching.

#### Priority: **MEDIUM**

Evidence-based argumentation is pedagogically important and aligns with NGSS science standards. The structured mode (select claim, click evidence zones, select reasoning principles) is fully auto-scorable and maps naturally to the diagram architecture. However, it is more text-heavy than other mechanics and works best for science content where specific principles can be enumerated.

---

## 3. Cognitive Skill Gap Matrix

This matrix shows which cognitive skills are tested by existing mechanics (E) vs proposed new mechanics (N), confirming that each new mechanic fills a genuine gap:

| Cognitive Skill | Existing Mechanic | Proposed New Mechanic |
|----------------|-------------------|----------------------|
| Recognition (identifying from options) | drag_drop, click_to_identify, description_matching | -- |
| Sequential ordering | sequencing, trace_path | -- |
| Classification | sorting_categories | -- |
| Working memory | memory_match | -- |
| Decision-making | branching_scenario | -- |
| Analytical comparison | compare_contrast | -- |
| **Free recall** | NONE | **cloze_fill_blank** |
| **Error detection** | NONE | **spot_the_error** |
| **Prediction / hypothesis** | NONE | **predict_observe_explain** |
| **Constructive synthesis** | NONE | **process_builder** |
| **Causal reasoning** | NONE | **cause_effect_chain** |
| **Spatial precision** | NONE | **annotation_drawing** |
| **Quantitative estimation** | NONE | **measurement_reading** |
| **Deductive elimination** | NONE | **elimination_grid** |
| **Exhaustive identification** | NONE | **hotspot_multi_select** |
| **Evidence-based argumentation** | NONE | **claim_evidence_reasoning** |

Every proposed mechanic tests a skill that no existing mechanic covers, confirming there is no redundancy.

---

## 4. Implementation Priority Summary

| Priority | Mechanic | Justification | Frontend Cost | Backend Cost | Reuses Existing? |
|----------|----------|---------------|---------------|--------------|-----------------|
| **HIGH** | `hotspot_multi_select` | Lowest cost, extends click_to_identify, used in all standardized testing | LOW | LOW | Yes (zone infrastructure) |
| **HIGH** | `cloze_fill_blank` | Tests unique skill (recall), reuses clean diagram pipeline, widely understood | MEDIUM | LOW | Yes (label removal pipeline) |
| **HIGH** | `spot_the_error` | Tests unique skill (error detection), strong research backing, maps to zone architecture | MEDIUM | MEDIUM | Partially (zone system) |
| **HIGH** | `predict_observe_explain` | Tests unique skill (prediction), strong pedagogical backing (White & Gunstone), 3-phase design is novel | MEDIUM-HIGH | MEDIUM | Partially (animation system) |
| **MEDIUM-HIGH** | `cause_effect_chain` | Tests causal reasoning (distinct from sequencing), moderate complexity | MEDIUM-HIGH | LOW-MEDIUM | Partially (card-based) |
| **MEDIUM** | `claim_evidence_reasoning` | NGSS alignment, structured mode is auto-scorable | MEDIUM-HIGH | MEDIUM | Partially (zone clicks) |
| **MEDIUM** | `elimination_grid` | Tests deductive reasoning, well-known format, fully auto-scorable | MEDIUM | MEDIUM | Diagram as context |
| **MEDIUM** | `measurement_reading` | Tests quantitative skills, STEM-specific, reusable instruments | MEDIUM | LOW | Partially (overlays) |
| **MEDIUM** | `annotation_drawing` | Tests spatial precision, pedagogically valuable, high frontend cost | HIGH | LOW | Drawing is new |
| **MEDIUM** | `process_builder` | Tests constructive synthesis, highest value but highest cost | HIGH | MEDIUM | Graph editor is new |

**Recommended Implementation Phases:**

- **Phase A (Quick Wins):** `hotspot_multi_select`, `cloze_fill_blank` -- Both extend existing infrastructure. ~2-3 weeks total.
- **Phase B (High Impact):** `spot_the_error`, `predict_observe_explain` -- Both test critical skills. ~3-4 weeks total.
- **Phase C (Reasoning Depth):** `cause_effect_chain`, `claim_evidence_reasoning` -- Add depth of reasoning assessment. ~3-4 weeks total.
- **Phase D (Advanced):** `elimination_grid`, `measurement_reading` -- Specialized mechanics. ~3-4 weeks total.
- **Phase E (Construction):** `annotation_drawing`, `process_builder` -- Highest complexity, highest payoff. ~5-6 weeks total.

---

## 5. Architecture Impact Assessment

### 5.1 Schema Changes Required

All new mechanics require additions to the existing type system:

**Backend (`interactive_diagram.py`):**
- Add 10 new values to the `InteractionMode` Literal type
- Add 10 new `*Config` Pydantic models (one per mechanic)
- Add 10 new optional config fields to `InteractiveDiagramBlueprint`

**Frontend (`types.ts`):**
- Add 10 new values to the `InteractionMode` union type
- Add 10 new `*Config` TypeScript interfaces
- Add 10 new optional config fields to `InteractiveDiagramBlueprint`
- Add 10 new `*Progress` types for Zustand state tracking
- Add corresponding `ModeTransitionTrigger` values

### 5.2 New Shared Components

Several proposed mechanics share component needs:

| Shared Component | Used By | Description |
|-----------------|---------|-------------|
| **Arrow/Connection Drawer** | process_builder, cause_effect_chain, annotation_drawing | SVG path rendering between two points |
| **Text Input on Zone** | cloze_fill_blank, spot_the_error (correction mode) | Text input positioned over a diagram zone |
| **Fuzzy String Matcher** | cloze_fill_blank, spot_the_error | Levenshtein distance + phonetic matching |
| **Graph Validator** | process_builder, cause_effect_chain | Directed graph comparison (topology matching) |
| **Spatial Overlap Scorer** | annotation_drawing, hotspot_multi_select | IoU / region overlap calculation |
| **Multi-Phase Flow** | predict_observe_explain, claim_evidence_reasoning | State machine for multi-step interactions |
| **Numeric Value Input** | measurement_reading, cloze_fill_blank | Input with unit selector and tolerance scoring |
| **Elimination Grid** | elimination_grid | Matrix grid with tri-state cells |

### 5.3 Pipeline Agent Impact

The following agents would need updates to support new mechanics:

| Agent | Changes |
|-------|---------|
| `game_planner` | Expanded mechanic type selection; new mechanic descriptions in prompt |
| `interaction_designer_v3` | New `enrich_mechanic_content` tool variants for each mechanic |
| `scene_architect_v3` | New `generate_mechanic_content` tool variants |
| `blueprint_assembler_v3` | New config field assembly logic per mechanic |
| `design_validator` | New validation rules per mechanic config |
| `playability_validator` | New playability checks per mechanic |

### 5.4 Scoring Infrastructure

Three scoring tiers across proposed mechanics:

| Tier | Mechanics | Scoring Method |
|------|-----------|----------------|
| **Exact match** | hotspot_multi_select, elimination_grid, sequencing variants | Set/array comparison |
| **Fuzzy match** | cloze_fill_blank, measurement_reading | String distance, numeric tolerance |
| **Spatial match** | annotation_drawing | Intersection over Union (IoU) |
| **LLM-scored** | predict_observe_explain (explain phase), claim_evidence_reasoning (reasoning phase) | Optional; structured modes avoid this |

---

## 6. Sources

Research and examples referenced in this document:

- [LM-GM Framework for Serious Games Analysis (Arnab et al., 2015)](https://bera-journals.onlinelibrary.wiley.com/doi/abs/10.1111/bjet.12113)
- [Predict-Observe-Explain (POE) Assessment Resource Banks, NZCER](https://arbs.nzcer.org.nz/predict-observe-explain-poe)
- [Designing Interactive E-Books Based on POE Method (PMC, 2022)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9645743/)
- [POE Teaching Strategy (Science Education Research)](https://science-education-research.com/teaching-science/constructivist-pedagogy/predict-observe-explain/)
- [Deliberately Introduced Errors as Pedagogical Tool (IndiaBioscience)](https://indiabioscience.org/columns/education/deliberately-introduced-errors-as-a-teaching-technique)
- [Teaching Error Analysis for Critical Thinking (LearningFocused)](https://learningfocused.com/blogs/effective-teaching-strategies/teaching-students-error-analysis-a-pathway-to-critical-thinking)
- [Cloze Test (Wikipedia)](https://en.wikipedia.org/wiki/Cloze_test)
- [Recognition vs Recall (PsychCentral)](https://psychcentral.com/blog/always-learning/2010/01/recognition-vs-recall)
- [NandGame - Build a Computer from Scratch](https://nandgame.com/)
- [Causal Reasoning in Games (ScienceDirect, 2023)](https://www.sciencedirect.com/science/article/pii/S0004370223000656)
- [Counterfactual Reasoning and Scientific Reasoning (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0065240721000240)
- [Learnosity Question Types Overview](https://authorguide.learnosity.com/hc/en-us/articles/360000628997-Question-Types-Overview)
- [Technology-Enhanced Items (Learnosity)](https://learnosity.com/edtech-blog/what-are-technology-enhanced-items/)
- [TEI Types and Assessment (Assess.com)](https://assess.com/what-are-technology-enhanced-items/)
- [Hotspot Questions (Blackboard)](https://help.blackboard.com/Learn/Instructor/Ultra/Tests_Pools_Surveys/Question_Types/Hotspot_Questions)
- [Hotspot Question Type (Inspera)](https://support.inspera.com/hc/en-us/articles/360024297072-Question-type-Hotspot)
- [Annotation Assignments in Canvas (UChicago)](https://courses.uchicago.edu/2021/06/21/expanded-student-annotation-assignment-options-in-canvas/)
- [Adding Annotations to Assessments (Learnosity)](https://help.learnosity.com/hc/en-us/articles/12157800422173-Adding-Annotations-to-Assessments)
- [Claim-Evidence-Reasoning Framework (ModelTeaching)](https://www.modelteaching.com/education-articles/stem-steam/claim-evidence-reasoning-cer)
- [CER in Science Education (Sadler Science)](https://sadlerscience.com/cer-science/)
- [Game-Based Learning and Argumentation (Systematic Review)](https://edepot.wur.nl/523014)
- [Elimination Grids (Brilliant.org)](https://brilliant.org/wiki/elimination-grids/)
- [Deduction Board Game Mechanic](https://mechanicsbg.com/mechanics/deduction/)
- [Spatial Reasoning Activities (Math Engaged)](http://mathengaged.org/resources/recommended-books-games-and-puzzles/spatial-reasoning-activities/)
- [Developing Spatial Visualization with Puzzle Games (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0747563215302971)
- [Taxonomy of Game Elements for Gamification (IEEE)](https://ieeexplore.ieee.org/document/8820847/)
- [Gamification Taxonomy Analysis (Smart Learning Environments, Springer)](https://link.springer.com/article/10.1186/s40561-019-0106-1)
- [Gamification for Procedural Knowledge Assessment (MDPI, 2025)](https://www.mdpi.com/2079-9292/14/8/1573)
- [Common Core TEI Item Types (Learnosity)](https://learnosity.com/edtech-blog/common-core-item-types/)
