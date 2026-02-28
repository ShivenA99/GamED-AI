# Research Report: Click-to-Identify, Trace-Path, and Description-Matching Game Mechanics

**Date:** 2026-02-11
**Scope:** Components, assets, and interaction patterns that make these three mechanics feel like real, engaging assessment games. Focused on NEW components each mechanic needs -- not scoring, hints, combos, or post-game review. All assets are configurable and support future test/learn mode split.

---

## Table of Contents

1. [Click-to-Identify](#1-click-to-identify)
2. [Trace-Path](#2-trace-path)
3. [Description-Matching](#3-description-matching)
4. [Shared Zone Types](#4-shared-zone-types)
5. [Current Codebase Gap Analysis](#5-current-codebase-gap-analysis)
6. [Component Inventory Summary](#6-component-inventory-summary)

---

## 1. Click-to-Identify

### 1.1 Reference Products

| Product | What It Does Well |
|---------|-------------------|
| **Kenhub** | Progressive difficulty (basic identification -> advanced identification -> clinical scenarios). Spaced repetition algorithm that re-tests weak structures. Five question formats including pure identification and functional prompts. |
| **Visible Body** | 3D model manipulation (rotate, zoom, hide obscuring structures) before selecting. Structure turns blue on selection, then submission confirms. Joystick navigation for accessibility. |
| **H5P Image Hotspot Question** | Hotspot zones (circle, polygon, rectangle) on a 2D image. Correct/incorrect/missed feedback per zone. Author defines which hotspots are valid answers. |
| **Seterra** | Timed map identification. After several incorrect clicks, the correct region flashes red. Accuracy + speed scoring. Leaderboard and session tracking. |
| **ASU Skeleton Viewer** | Explore mode (hover/click to learn bone names) then test mode (identify bones from prompts). Two distinct phases on the same diagram. |

### 1.2 New Components Needed

#### 1.2.1 PromptBanner

A top-anchored banner that displays the current identification prompt. This is the core driver of the entire click-to-identify experience -- the user reads a prompt and must locate the matching structure on the diagram.

**Two prompt styles (configurable):**

| Style | Example Prompt | Assessment Target |
|-------|---------------|-------------------|
| `naming` | "Click on the mitochondria" | Tests whether student can locate a named structure |
| `functional` | "Click on the structure responsible for cellular energy production" | Tests whether student understands function-to-structure mapping |

The prompt banner must:
- Display the prompt text prominently with clear visual hierarchy
- Show a progress counter (e.g., "3 of 8")
- Support sequential and any-order selection modes (see 1.2.3)
- Never reveal the answer -- the prompt is the question, the diagram is the answer space

**Props:**
```typescript
interface PromptBannerProps {
  promptText: string;
  promptStyle: 'naming' | 'functional';
  currentIndex: number;
  totalCount: number;
  selectionMode: 'sequential' | 'any_order';
}
```

#### 1.2.2 Zone Highlight State Machine

Every clickable zone must cycle through a well-defined set of visual states. The current `HotspotManager` has a partial implementation (completed/target/highlighted) but lacks the full state set that makes identification games feel responsive and polished.

**Required states:**

| State | Visual Treatment | When Active |
|-------|-----------------|-------------|
| `default` | Invisible or very faint boundary (near-transparent). Zone should NOT be obviously outlined -- the student must know the anatomy, not just click the highlighted region. | Before any interaction with this zone |
| `hover` | Subtle boundary appears (light stroke, slight fill opacity increase). Cursor changes to pointer. On touch devices, no hover state -- zones respond on tap. | Mouse enters zone bounds |
| `selected` | Solid stroke, moderate fill opacity. Distinct from hover. Stays selected until evaluation. | User has clicked the zone but result not yet evaluated |
| `correct` | Green fill/stroke, checkmark icon overlay. Brief success animation (pulse or glow, 300-500ms). Zone remains in this state for the rest of the game. | After correct identification |
| `incorrect` | Red fill/stroke, brief shake animation (200-300ms). Returns to default state after animation. Zone does NOT stay red -- the student should be able to try again on other zones. | After incorrect click (transient, 500ms) |
| `disabled` | Greyed out, pointer-events-none. | Zone already correctly identified |

**Key design principle:** In test mode, zones must be nearly invisible by default. Visible zone outlines turn the assessment into a process-of-elimination click game rather than a genuine test of structural knowledge. The student must KNOW where the structure is, not just see an outlined region and guess.

**Props for configuration:**
```typescript
interface ZoneHighlightConfig {
  highlight_style: 'subtle' | 'outlined' | 'invisible';
  // 'subtle' = faint boundary on hover only (recommended for test mode)
  // 'outlined' = visible boundaries always (useful for learn mode)
  // 'invisible' = no visual indication at all (hardest mode)
  correct_color: string;     // default: '#22c55e' (green-500)
  incorrect_color: string;   // default: '#ef4444' (red-500)
  hover_color: string;       // default: '#3b82f6' (blue-500)
  selected_color: string;    // default: '#f59e0b' (amber-500)
  animation_duration_ms: number; // default: 300
}
```

#### 1.2.3 Selection Mode Controller

Controls the order in which zones must be identified. Two modes:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `sequential` | Prompts are presented in a fixed order. Student must identify structure #1 before seeing prompt #2. Only the current target zone accepts clicks. | Progressive difficulty ordering: easy structures first, hard structures last. Teacher-controlled sequence. |
| `any_order` | All prompts are visible or can be cycled through freely. Student clicks any valid remaining zone. Multiple prompts may be active simultaneously. | Exploratory assessment. Student chooses their own path. |

**Progressive difficulty ordering:** In sequential mode, prompts should be ordered by difficulty (zone.difficulty field, 1-5). This is critical for Kenhub-style adaptive assessment where easy identifications build confidence before harder ones. The ordering is defined at blueprint generation time, not at runtime.

#### 1.2.4 Magnification Lens

A floating circular lens that magnifies the area under the cursor. Essential for dense diagrams (e.g., cross-sections with many small structures, detailed anatomical drawings). Without magnification, clicking on small zones is frustrating and tests motor skill rather than knowledge.

**Implementation approach:**
- Render a circular clipping mask centered on the cursor position
- Inside the mask, render the same diagram image at 2x-3x scale, offset so the cursor position is centered
- The lens follows the cursor with a slight lag (transform with CSS transition, 50-100ms)
- On mobile/touch: lens activates on long-press and follows finger
- Lens size is configurable (default 120px diameter)
- Magnification factor is configurable (default 2.5x)

**Props:**
```typescript
interface MagnificationLensConfig {
  enabled: boolean;           // default: false
  diameter_px: number;        // default: 120
  magnification: number;      // default: 2.5
  border_color: string;       // default: '#1e293b' (slate-800)
  border_width_px: number;    // default: 2
  show_crosshair: boolean;    // default: true
  activation: 'always' | 'on_hold' | 'toggle_button';
  // 'always' = lens always visible
  // 'on_hold' = lens appears on long-press/right-click
  // 'toggle_button' = user clicks a toolbar button to enable/disable
}
```

**CSS implementation sketch:**
```css
.magnification-lens {
  position: absolute;
  pointer-events: none;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 0 0 2px var(--border-color), 0 4px 12px rgba(0,0,0,0.3);
  z-index: 50;
}
.magnification-lens__inner {
  transform-origin: center;
  transform: scale(var(--mag-factor));
}
```

#### 1.2.5 Explore-Then-Test Mode Controller

A two-phase game controller that splits the experience into an exploration phase and a test phase on the same diagram. This pattern is used by ASU Skeleton Viewer, Kenhub, and Visible Body.

**Phase 1 -- Explore:**
- All zones are visible with labels
- User can hover/click any zone to see its name and optional description
- No scoring, no prompts, no right/wrong feedback
- Timer counts time spent exploring (optional)
- User clicks "Ready to Test" when done

**Phase 2 -- Test:**
- Labels are hidden
- Prompts appear (naming or functional)
- Zone highlight style switches to `subtle` or `invisible`
- Standard click-to-identify scoring begins

This is NOT two separate games. It is a single game with a phase transition. The diagram, zones, and layout are identical in both phases -- only the interaction rules change.

**Props:**
```typescript
interface ExploreTestConfig {
  explore_mode_enabled: boolean;  // default: false
  explore_time_limit_seconds: number | null;  // null = unlimited
  show_labels_in_explore: boolean;  // default: true
  show_descriptions_in_explore: boolean;  // default: true
  transition_message: string;  // default: "Great! Now let's test your knowledge."
  allow_return_to_explore: boolean;  // default: false
}
```

### 1.3 Full Configuration Schema

```typescript
interface ClickToIdentifyConfig {
  // Prompt configuration
  prompt_style: 'naming' | 'functional';

  // Selection behavior
  selection_mode: 'sequential' | 'any_order';

  // Visual style
  highlight_style: 'subtle' | 'outlined' | 'invisible';

  // Magnification
  magnification_enabled: boolean;
  magnification_factor: number;  // 1.5 - 4.0
  magnification_diameter_px: number;
  magnification_activation: 'always' | 'on_hold' | 'toggle_button';

  // Explore-then-test
  explore_mode_enabled: boolean;
  explore_time_limit_seconds: number | null;
  show_labels_in_explore: boolean;
  show_descriptions_in_explore: boolean;
  allow_return_to_explore: boolean;

  // Zone behavior
  zone_click_tolerance_px: number;  // Extra hit area padding (default: 8)
  show_zone_count: boolean;  // Show "3 of 8" counter
  disable_completed_zones: boolean;  // Grey out correctly identified zones

  // Audio feedback (future)
  audio_enabled: boolean;
  correct_sound: string | null;
  incorrect_sound: string | null;
}
```

---

## 2. Trace-Path

### 2.1 Reference Products

| Product | What It Does Well |
|---------|-------------------|
| **PhET Circuit Construction Kit** | Drag-and-drop circuit building. Animated electrons flow along completed circuits. Current direction shown with moving dots. Color-coded wires. Real-time ammeter/voltmeter feedback. |
| **AHA Blood Flow Animation** | Animated blood flow through heart chambers. Color transitions (blue deoxygenated to red oxygenated) at lungs. Labeled waypoints at each chamber/valve. Continuous loop animation after path completion. |
| **USGS Water Cycle Interactive** | Multiple branching pathways a water droplet can take. Non-linear path with decision points (evaporation vs. runoff vs. infiltration). Clicking hotspots reveals information about each stage. |
| **Educaplay Blood Flow Map Quiz** | Sequential click ordering: user must click structures in the correct order of blood flow. Numbered waypoints appear as user progresses. |
| **PBS NOVA Heart Map** | Animated interactive heart exploration. Users can click on chambers to see blood flow direction. Directional arrows overlay the diagram. |

### 2.2 New Components Needed

#### 2.2.1 SVG Path Definition Layer

The current `PathDrawer` draws straight lines between waypoint centers. Real trace-path games need curved, anatomically accurate paths defined by SVG path data. A straight line from "Right Atrium" to "Right Ventricle" does not represent the actual flow path through valves and chambers.

**Path definition structure:**
```typescript
interface PathDefinition {
  id: string;
  // SVG path data string (e.g., "M 10,50 C 20,30 40,30 50,50")
  // If null, straight lines between waypoints are used (current behavior)
  svg_path_data: string | null;

  // Waypoints along the path (ordered)
  waypoints: PathWaypoint[];

  // Visual properties
  stroke_color: string;
  stroke_width: number;
  stroke_dasharray: string | null;  // null = solid line

  // Path metadata
  description: string;
  path_type: 'linear' | 'branching' | 'circular';
  requires_order: boolean;
}
```

**Path types explained:**

| Type | Description | Example |
|------|-------------|---------|
| `linear` | Single path from start to end. One correct sequence. | Food through digestive tract: mouth -> esophagus -> stomach -> small intestine -> large intestine |
| `branching` | Path splits at decision points. Multiple valid routes to completion. | Water cycle: evaporation -> cloud -> (rain OR snow) -> (river OR groundwater) -> ocean |
| `circular` | Path loops back to the starting point. No defined end. | Blood circulation: heart -> arteries -> capillaries -> veins -> heart |

#### 2.2.2 Animated Particle System

After a path segment is completed (two consecutive waypoints connected), animated particles should flow along that segment to reinforce the concept of movement/flow. This is the single most important visual element that distinguishes trace-path from generic sequencing.

**Particle behavior:**
- Small circles (4-8px diameter) move along the SVG path at configurable speed
- Multiple particles are staggered along the path (spacing configurable)
- Particles follow the SVG path curve, not a straight line
- Particle color can change along the path (see 2.2.3)
- Particles are rendered as SVG circles animated with `offset-path` or GSAP MotionPathPlugin
- Particle count per segment: 3-8 (configurable)
- Animation loops continuously once a segment is complete

**Implementation approach using CSS `offset-path`:**
```css
.path-particle {
  offset-path: path('M 10,50 C 20,30 40,30 50,50');
  offset-distance: 0%;
  animation: flow-along-path var(--duration) linear infinite;
}
@keyframes flow-along-path {
  from { offset-distance: 0%; }
  to { offset-distance: 100%; }
}
```

**Props:**
```typescript
interface ParticleConfig {
  particle_theme: 'dots' | 'arrows' | 'droplets' | 'cells' | 'electrons';
  // 'dots' = simple circles (default, works for any domain)
  // 'arrows' = directional chevrons (good for flow direction)
  // 'droplets' = teardrop shapes (water cycle)
  // 'cells' = round with nucleus (blood cells)
  // 'electrons' = small with glow (electrical circuits)
  particle_size_px: number;       // default: 6
  particle_count_per_segment: number;  // default: 5
  particle_speed: 'slow' | 'medium' | 'fast';  // maps to animation duration
  particle_opacity: number;       // default: 0.8
  stagger_delay_ms: number;       // delay between particles, default: 200
}
```

#### 2.2.3 Color Transition Engine

Many science paths involve a substance changing state as it moves through the system. Blood changes from blue (deoxygenated) to red (oxygenated) at the lungs. Water changes from liquid to gas during evaporation. This color change along the path is a powerful visual teaching tool.

**How it works:**
- Each path segment can define a `start_color` and `end_color`
- Particles interpolate between these colors as they traverse the segment
- The path stroke itself can also show a gradient between the two colors
- Color transition can happen at a specific waypoint (e.g., "at the lungs") or gradually along the entire segment

```typescript
interface ColorTransition {
  enabled: boolean;
  segments: Array<{
    from_waypoint_id: string;
    to_waypoint_id: string;
    start_color: string;  // hex
    end_color: string;    // hex
    transition_point: 'gradual' | 'at_midpoint' | 'at_destination';
  }>;
}
```

**Example for blood flow:**
```json
{
  "enabled": true,
  "segments": [
    {
      "from_waypoint_id": "right_ventricle",
      "to_waypoint_id": "lungs",
      "start_color": "#3b82f6",
      "end_color": "#3b82f6",
      "transition_point": "gradual"
    },
    {
      "from_waypoint_id": "lungs",
      "to_waypoint_id": "left_atrium",
      "start_color": "#3b82f6",
      "end_color": "#ef4444",
      "transition_point": "at_midpoint"
    }
  ]
}
```

#### 2.2.4 Directional Arrow Overlays

Arrows along the path indicate flow direction. These are distinct from the animated particles -- arrows are static visual cues that persist on the diagram, while particles are animated.

**Implementation:**
- SVG `<marker>` elements with arrowhead polygon at the end of each path segment
- Arrow spacing along curved paths: every N pixels along the path length
- Arrow color matches the path stroke color (or a contrasting color for visibility)
- Arrows can be shown/hidden via configuration

```typescript
interface DirectionArrowConfig {
  show_direction_arrows: boolean;  // default: true
  arrow_spacing_px: number;        // default: 60
  arrow_size: 'small' | 'medium' | 'large';
  arrow_color: string | 'match_path';  // default: 'match_path'
  arrow_style: 'chevron' | 'triangle' | 'line';
}
```

#### 2.2.5 Waypoint Zone Markers

Each waypoint on the path needs a distinct visual treatment. The current `PathZone` component uses circles with numbers, but real trace-path games use more contextual markers.

**Waypoint states:**

| State | Visual Treatment |
|-------|-----------------|
| `unvisited` | Faint circle or pulsing dot. In ordered paths, only the NEXT waypoint pulses. In unordered paths, all unvisited waypoints pulse. |
| `next` | Prominent pulsing ring, brighter color, optional bounce animation. This is the "click me next" indicator. |
| `visited` | Numbered badge (sequence number), solid fill, checkmark or number overlay. Connected to previous waypoint by animated path. |
| `gate` | Special waypoint that represents a valve, checkpoint, or transition point. Uses a distinct icon (gate/valve SVG icon). Briefly animates open when the user arrives. |

**Gate/Valve animations:** For anatomical paths (heart valves, sphincters) or mechanical paths (circuit switches, water valves), gate waypoints play a brief opening animation when the preceding waypoint is completed. This reinforces the concept that flow is controlled by these structures.

```typescript
interface WaypointConfig {
  type: 'standard' | 'gate' | 'branch_point' | 'terminus';
  // 'standard' = normal waypoint
  // 'gate' = valve/checkpoint with open/close animation
  // 'branch_point' = path splits here (user chooses which branch)
  // 'terminus' = start or end of path
  gate_animation: 'slide_open' | 'rotate_open' | 'fade_open' | null;
  gate_label: string | null;  // e.g., "Tricuspid Valve"
  icon: string | null;  // SVG icon name or URL
}
```

#### 2.2.6 Drawing Mode Controller

Controls HOW the user traces the path. Two modes:

| Mode | Interaction | Best For |
|------|-------------|----------|
| `click_waypoints` | User clicks waypoints in sequence. Path segments draw automatically between them. (Current implementation.) | Structured assessment. Unambiguous. Works well on both desktop and mobile. |
| `freehand` | User draws a line with mouse/finger. System evaluates whether the drawn path passes through (or near) required waypoints in the correct order. | Exploratory mode. More engaging. Tests spatial understanding of the path, not just sequence knowledge. |

**Freehand mode implementation notes:**
- Capture pointer events (pointerdown, pointermove, pointerup) on the SVG canvas
- Record drawn path as an array of [x, y] coordinates
- After drawing, evaluate: did the path pass within `proximity_threshold_px` of each waypoint in the correct order?
- Visual feedback: drawn path is displayed in a user-drawn style (slightly rough stroke), then morphs into the correct path on completion
- Tolerance for waypoint proximity is configurable (default: 30px)

```typescript
interface DrawingModeConfig {
  drawing_mode: 'click_waypoints' | 'freehand';
  freehand_stroke_color: string;    // default: '#6366f1' (indigo-500)
  freehand_stroke_width: number;    // default: 4
  freehand_proximity_threshold_px: number;  // default: 30
  show_drawn_path: boolean;         // Show the user's freehand path, default: true
  snap_to_correct_path: boolean;    // After completion, morph drawn path to correct path
}
```

### 2.3 Full Configuration Schema

```typescript
interface TracePathConfig {
  // Path type
  path_type: 'linear' | 'branching' | 'circular';

  // Drawing interaction
  drawing_mode: 'click_waypoints' | 'freehand';
  freehand_proximity_threshold_px: number;

  // Particle animation
  particle_theme: 'dots' | 'arrows' | 'droplets' | 'cells' | 'electrons';
  particle_speed: 'slow' | 'medium' | 'fast';
  particle_count_per_segment: number;
  particle_size_px: number;

  // Color transitions
  color_transition: ColorTransition;

  // Direction indicators
  show_direction_arrows: boolean;
  arrow_spacing_px: number;
  arrow_style: 'chevron' | 'triangle' | 'line';

  // Path rendering
  path_stroke_width: number;
  path_stroke_color: string;
  path_stroke_dasharray: string | null;
  show_svg_path: boolean;  // Show the full path outline before tracing (learn mode)

  // Waypoint behavior
  show_waypoint_labels: boolean;
  show_waypoint_numbers: boolean;
  allow_waypoint_skip: boolean;  // Can user skip ahead? (default: false)
  gate_animations_enabled: boolean;

  // Completion
  show_full_flow_on_complete: boolean;  // Play full particle animation loop on completion
  loop_animation_on_complete: boolean;  // Loop forever or play once
}
```

---

## 3. Description-Matching

### 3.1 Reference Products

| Product | What It Does Well |
|---------|-------------------|
| **H5P Drag and Drop** | Background image with drop zones. Supports one-to-one, one-to-many, many-to-one combinations. Draggables can be text or images. Visual feedback on drop (green/red border). |
| **H5P Image Pairing** | Pair matching with drag-and-drop or click. Visual card layout. Immediate feedback on match attempt. |
| **Quizlet Match** | Timed matching game. Six pairs per round. Click-to-match mode (tap term, tap definition) and drag mode. Wrong matches add time penalty. Grid layout. |
| **Anatomy Function Matching (various)** | Match structure names to functional descriptions. Descriptions are pedagogical (explain what the structure DOES, not what it IS). Distractor descriptions test common misconceptions. |
| **Articulate Storyline Matching** | Drag terms to definitions. Connecting lines drawn between matched pairs. Deferred evaluation (all matches submitted at once). |

### 3.2 New Components Needed

#### 3.2.1 Interaction Mode Router

The current `DescriptionMatcher` supports three modes (`click_zone`, `drag_description`, `multiple_choice`) but they are implemented as separate code paths within one component. Each mode needs distinct sub-components with clean interfaces.

**Three modes and their unique requirements:**

| Mode | How It Works | Components Needed |
|------|-------------|-------------------|
| `drag_to_zone` | Descriptions in a side panel. User drags a description card onto the correct zone on the diagram. | `DraggableDescriptionCard`, `DroppableZoneOverlay`, `DescriptionTray` |
| `click_match` | User clicks a description, then clicks the matching zone (or vice versa). Two-click selection pattern. Active selection highlighted. | `SelectableDescriptionList`, `SelectableZoneHighlight`, `SelectionIndicator` |
| `multiple_choice` | A zone is highlighted. Four descriptions shown (1 correct + 3 distractors). User picks the correct one. | `ZoneHighlighter`, `DescriptionChoicePanel`, `DistractorGenerator` |

#### 3.2.2 Connecting Lines (SVG)

When a match is made (in any mode), a visual line should connect the description to its matched zone on the diagram. This is a critical visual element that reinforces the spatial relationship between the abstract description and the physical structure.

**Line behavior:**
- Line is drawn from the description card/label to the center of the matched zone
- Line uses a curved path (quadratic bezier) to avoid overlapping other elements
- Line color indicates correctness (green for correct, red for incorrect in immediate-feedback mode; neutral blue in deferred mode)
- Lines should not cross each other unnecessarily -- a basic crossing-minimization layout should be applied
- Lines animate in with a drawing effect (stroke-dashoffset animation)
- On hover over a line, the connected description and zone both highlight

```typescript
interface ConnectingLineConfig {
  show_connecting_lines: boolean;  // default: true
  line_style: 'straight' | 'curved' | 'right_angle';
  line_color_correct: string;     // default: '#22c55e'
  line_color_incorrect: string;   // default: '#ef4444'
  line_color_pending: string;     // default: '#3b82f6'
  line_width: number;             // default: 2
  animate_draw: boolean;          // Animate line drawing, default: true
  show_on_hover_only: boolean;    // Only show lines when hovering, default: false
}
```

**SVG implementation:**
```typescript
interface MatchLine {
  id: string;
  from: { x: number; y: number };  // Description card position
  to: { x: number; y: number };    // Zone center position
  status: 'pending' | 'correct' | 'incorrect';
  label_text?: string;
}
```

#### 3.2.3 Description Cards

Each functional description is displayed as a card that the user interacts with. The card design matters because descriptions are longer than simple labels -- they are full sentences describing what a structure does.

**Card states:**

| State | Visual | When |
|-------|--------|------|
| `available` | White card, blue left border, readable text. In drag mode: grab cursor. | Before matching |
| `selected` | Blue background, elevated shadow, border highlight. | User has clicked/tapped this description (click_match mode) |
| `dragging` | Elevated, slight rotation, reduced opacity at original position. Drag overlay follows cursor. | Being dragged (drag_to_zone mode) |
| `matched_correct` | Green left border, green checkmark, text greyed slightly. Card moves to matched position or fades. | Successfully matched |
| `matched_incorrect` | Red left border, brief shake, returns to available state (immediate mode) or stays with red indicator (deferred mode). | Incorrectly matched |
| `used` | Fully greyed out, no pointer events. | Already correctly matched |

**Card content structure:**
```typescript
interface DescriptionCard {
  id: string;
  text: string;          // The functional description
  is_distractor: boolean; // If true, this description does not match any zone
  distractor_explanation?: string;  // Shown after game: why this was wrong
  difficulty: number;     // 1-5
  word_count: number;     // For layout -- longer descriptions need more height
}
```

#### 3.2.4 Zone Proximity Highlights

When the user is dragging a description card near a zone (within a proximity threshold), that zone should light up to indicate it is a valid drop target. This is critical UX -- without proximity highlighting, the user does not know where they can drop.

**Behavior:**
- Calculate distance between drag cursor and each zone center
- When distance < `proximity_threshold_px`, zone enters `droppable_active` state
- Zone shows a glowing border/fill to indicate it will accept the drop
- Only one zone should be highlighted at a time (the nearest valid zone)
- On mobile/touch, proximity detection uses the touch point

```typescript
interface ProximityHighlightConfig {
  proximity_threshold_px: number;  // default: 40
  highlight_color: string;         // default: '#60a5fa' (blue-400)
  highlight_animation: 'glow' | 'pulse' | 'scale' | 'none';
  show_zone_label_on_proximity: boolean;  // Show zone name when near
}
```

#### 3.2.5 Deferred vs. Immediate Evaluation Controller

Controls WHEN matches are evaluated. This has significant pedagogical implications.

| Mode | Behavior | Use Case |
|------|----------|----------|
| `immediate` | Each match is evaluated as soon as it is made. Correct/incorrect feedback shown instantly. Incorrect matches are rejected (description returns to pool). | Formative assessment. Learning mode. Provides immediate reinforcement. |
| `deferred` | All descriptions can be placed without feedback. User reviews their placements. A "Submit All" button triggers evaluation. Results shown for all matches simultaneously. Allows revision before final submission. | Summative assessment. Test mode. Closer to exam conditions. Student commits to all answers before seeing results. |

```typescript
interface EvaluationConfig {
  defer_evaluation: boolean;  // default: false (immediate)
  allow_revision_before_submit: boolean;  // In deferred mode, can user change placements? default: true
  show_submit_button: boolean;  // Only in deferred mode
  show_match_count: boolean;    // Show "4 of 8 placed" counter
}
```

#### 3.2.6 Distractor Descriptions

Distractor descriptions are incorrect descriptions that do not match any zone. They serve the same purpose as distractor answers in multiple-choice questions: they test whether the student truly understands the function, or is just guessing by elimination.

**Design principles for good distractors (from assessment research):**
- Each distractor must be plausible -- it should sound like it COULD describe a real structure
- Distractors should target common misconceptions (e.g., confusing the function of mitochondria with chloroplasts)
- Distractors should be approximately the same length and complexity as correct descriptions
- The number of distractors should be configurable (0-4 recommended)
- In drag_to_zone and click_match modes, distractors appear alongside correct descriptions in the pool
- In multiple_choice mode, distractors fill the non-correct options

```typescript
interface DistractorConfig {
  distractor_descriptions: Array<{
    id: string;
    text: string;
    explanation: string;  // Shown post-game: "This describes X, not Y"
    targets_misconception: string;  // Which misconception this tests
  }>;
  distractor_count: number;  // How many distractors to include (0 = none)
  shuffle_with_correct: boolean;  // Mix distractors into the description pool
}
```

#### 3.2.7 Description Style Variants

The wording style of descriptions significantly affects assessment difficulty and engagement.

| Style | Example | Tests |
|-------|---------|-------|
| `functional` | "This structure contracts to pump blood to the lungs" | Function knowledge |
| `structural` | "A thick-walled muscular chamber in the lower-right portion of the heart" | Anatomical knowledge |
| `process` | "Blood enters this chamber from the superior and inferior vena cava" | Process/pathway knowledge |
| `clinical` | "Failure of this structure leads to pulmonary edema and right-sided heart failure" | Clinical application |

```typescript
interface DescriptionStyleConfig {
  description_style: 'functional' | 'structural' | 'process' | 'clinical';
  description_length: 'brief' | 'standard' | 'detailed';
  // 'brief' = 5-15 words
  // 'standard' = 15-30 words
  // 'detailed' = 30-50 words
}
```

### 3.3 Full Configuration Schema

```typescript
interface DescriptionMatchingConfig {
  // Interaction mode
  match_mode: 'drag_to_zone' | 'click_match' | 'multiple_choice';

  // Visual feedback
  show_connecting_lines: boolean;
  line_style: 'straight' | 'curved' | 'right_angle';
  animate_connections: boolean;

  // Evaluation timing
  defer_evaluation: boolean;
  allow_revision_before_submit: boolean;

  // Description content
  description_style: 'functional' | 'structural' | 'process' | 'clinical';
  description_length: 'brief' | 'standard' | 'detailed';

  // Distractors
  distractor_count: number;
  shuffle_descriptions: boolean;

  // Zone interaction
  zone_proximity_threshold_px: number;
  show_zone_label_on_hover: boolean;
  highlight_matched_zones: boolean;

  // Layout
  description_panel_position: 'left' | 'right' | 'bottom';
  card_size: 'compact' | 'standard' | 'large';
}
```

---

## 4. Shared Zone Types

All three mechanics operate on the same zone system. Zones define the interactive regions on the diagram that the user can click, identify, trace through, or match descriptions to.

### 4.1 Zone Shape Types

| Shape | Definition | Hit Detection | Best For |
|-------|-----------|---------------|----------|
| `circle` | Center point (x, y) + radius. All values in 0-100 percentage coordinates. | Distance from click to center < radius. | Small, roughly circular structures (cells, organelles, organs in schematic diagrams). Simplest to define. |
| `polygon` | Array of [x, y] vertex pairs defining an arbitrary closed shape. Minimum 3 points. | Point-in-polygon test (ray casting algorithm). | Irregular shapes (countries on maps, anatomical regions with complex boundaries, cross-section layers). Most accurate for real anatomy. |
| `rectangle` | Center point (x, y) + width + height. All in percentage coordinates. | Point within axis-aligned bounding box. | Rectangular regions (text boxes, table cells, labeled sections of a schematic). |
| `point` | Center point (x, y) + configurable hit_radius. Visually rendered as a small dot or pin. | Distance from click to center < hit_radius. | Precise pinpoint locations (specific landmarks, pin-the-label targets, small features). The hit_radius makes the clickable area larger than the visible dot. |

### 4.2 Point Zone Hit Radius

The `point` zone type is special because it has no inherent size -- it is a single coordinate on the diagram. Without a configurable hit radius, users would need pixel-perfect accuracy to click it, which is impossible on touch devices and frustrating on desktop.

**Hit radius configuration:**
```typescript
interface PointZoneConfig {
  hit_radius_px: number;  // Clickable area radius in pixels (default: 20)
  visual_radius_px: number;  // Visible dot size (default: 6)
  // hit_radius should always be >= visual_radius
  // Recommended: hit_radius = 3-4x visual_radius

  // Accessibility minimums (WCAG):
  // Touch target: minimum 44px diameter (hit_radius >= 22)
  // Mouse target: minimum 24px diameter (hit_radius >= 12)
}
```

### 4.3 Zone Type in Current Codebase

The current `types.ts` defines:
```typescript
export type ZoneShape = 'circle' | 'polygon' | 'rect';
export type ZoneType = 'point' | 'area';
```

The `SVGZoneRenderer` handles `circle`, `polygon`, and `rect` shapes. The `point` type exists in the type system but is not distinguished from `circle` in rendering -- it uses the same radius-based rendering. The `point` type needs its own rendering logic: a small visible dot with a larger invisible hit area.

### 4.4 Recommended Zone Type Additions

```typescript
// Extend existing ZoneShape
export type ZoneShape = 'circle' | 'polygon' | 'rect' | 'point';

// Point-specific rendering
interface PointZoneRenderConfig {
  visual_style: 'dot' | 'pin' | 'crosshair' | 'ring';
  visual_color: string;
  hit_radius_px: number;
  show_hit_area_on_hover: boolean;  // Debug: show the actual clickable area
}
```

---

## 5. Current Codebase Gap Analysis

### 5.1 Click-to-Identify Gaps

| Component | Current State | Gap |
|-----------|--------------|-----|
| `HotspotManager.tsx` | Basic implementation with completed/target/highlighted states. | Missing: full 5-state highlight machine (default/hover/selected/correct/incorrect). Zones are always visible as circles -- no `invisible` or `subtle` mode. No state transitions for the `selected` interim state before evaluation. |
| Prompt banner | Exists but hardcodes prompt text display. | Missing: `prompt_style` configuration (naming vs functional). Banner always shows zone labels in any_order mode (leaks answers). |
| Magnification lens | Does not exist. | Entirely new component needed. |
| Explore-then-test | Does not exist. | Needs a phase controller that switches interaction rules on the same diagram. |
| Selection mode | `sequential` and `any_order` exist in types. | Implementation works but `any_order` mode leaks zone labels in the prompt display (line 227-230 of HotspotManager). Progressive difficulty ordering not enforced. |
| Zone highlight config | Hardcoded colors in className strings. | Not configurable. Colors/styles should come from blueprint config. |

### 5.2 Trace-Path Gaps

| Component | Current State | Gap |
|-----------|--------------|-----|
| `PathDrawer.tsx` | Click-waypoints mode with straight lines between zones. Arrow markers on lines. Visited/unvisited zone states. | Missing: SVG curved path support (only straight lines). No particle animation system. No color transitions. No gate/valve waypoint type. No freehand drawing mode. |
| `PathVisualizer` (inner component) | Renders dashed lines with arrowhead markers between visited waypoints. | Lines are straight-only. No SVG path data support. No animated particles. No gradient coloring. |
| Path types | `TracePath` type has `requiresOrder` boolean. | Missing: `path_type` (linear/branching/circular). No branching path support where user chooses between routes. No circular path that loops. |
| Particle system | Does not exist. | Entirely new component needed. Core missing feature that makes path tracing feel dynamic. |
| Color transition | Does not exist. | New component. Critical for blood flow (blue->red), water cycle (liquid->gas), etc. |
| Direction arrows | Basic SVG `<marker>` arrowhead on line endpoints. | Arrows only at endpoints, not distributed along the path. No spacing or style configuration. |
| Gate/valve animations | Does not exist. | New component for checkpoint waypoints (heart valves, circuit switches). |
| Freehand drawing | Does not exist. | New interaction mode with pointer event capture and path proximity evaluation. |

### 5.3 Description-Matching Gaps

| Component | Current State | Gap |
|-----------|--------------|-----|
| `DescriptionMatcher.tsx` | Three modes (click_zone, drag_description, multiple_choice). Basic functionality works. | Missing: connecting lines between matches. Zone proximity highlights during drag. Deferred evaluation mode. Distractor descriptions. Description style configuration. |
| Connecting lines | Does not exist in description matching. | SVG lines connecting descriptions to matched zones are a core visual element. |
| Zone proximity | No proximity detection during drag. | `isOver` from dnd-kit exists but no proximity threshold or approach highlighting. |
| Deferred evaluation | Not implemented. | All matches are evaluated immediately. No "submit all" workflow. |
| Distractors | `DistractorLabel` type exists in types.ts, but `DescriptionMatcher` does not use it. | Distractor descriptions need to be mixed into the description pool and handled in scoring. |
| Description cards | Basic styled divs. | Missing: proper state machine (available/selected/dragging/matched/used). No card design variation for different description styles. |
| Multiple-choice options | Randomly selects 3 distractors from other zone descriptions. | No dedicated distractor pool. Options re-shuffle on every render (unstable). |
| Description style | Not configurable. Uses zone.description as-is. | No support for different description styles (functional/structural/process/clinical). |

---

## 6. Component Inventory Summary

### 6.1 Click-to-Identify -- New Components

| # | Component | Type | Priority |
|---|-----------|------|----------|
| C1 | `PromptBanner` | UI Component | High |
| C2 | `ZoneHighlightStateMachine` | Logic + CSS | High |
| C3 | `MagnificationLens` | UI Component | Medium |
| C4 | `ExploreTestController` | State Controller | Medium |
| C5 | `SelectionModeController` | Logic | High (refactor existing) |
| C6 | `ZoneHighlightConfig` | Config Schema | High |

### 6.2 Trace-Path -- New Components

| # | Component | Type | Priority |
|---|-----------|------|----------|
| T1 | `SVGPathDefinitionLayer` | SVG Renderer | High |
| T2 | `AnimatedParticleSystem` | SVG Animation | High |
| T3 | `ColorTransitionEngine` | Animation Logic | Medium |
| T4 | `DirectionalArrowOverlay` | SVG Renderer | Medium |
| T5 | `WaypointZoneMarker` (enhanced) | UI Component | High (refactor existing `PathZone`) |
| T6 | `GateValveAnimation` | SVG Animation | Low |
| T7 | `FreehandDrawingCanvas` | Canvas/SVG Input | Low |
| T8 | `DrawingModeController` | State Controller | Low |

### 6.3 Description-Matching -- New Components

| # | Component | Type | Priority |
|---|-----------|------|----------|
| D1 | `ConnectingLineRenderer` | SVG Component | High |
| D2 | `DescriptionCardStateMachine` | UI + State | High (refactor existing) |
| D3 | `ZoneProximityHighlighter` | Drag Interaction | Medium |
| D4 | `DeferredEvaluationController` | State Controller | Medium |
| D5 | `DistractorPool` | Data + Logic | Medium |
| D6 | `DescriptionStyleConfig` | Config Schema | Low |
| D7 | `InteractionModeRouter` | Component Router | High (refactor existing) |

### 6.4 Shared Components

| # | Component | Type | Priority |
|---|-----------|------|----------|
| S1 | `PointZoneRenderer` | SVG Component | Medium |
| S2 | `ZoneHitDetector` (point-in-polygon, hit radius) | Logic | High |

### 6.5 Configuration Schemas (Backend)

| # | Schema | Where |
|---|--------|-------|
| B1 | `ClickToIdentifyConfig` | `backend/app/agents/schemas/interactive_diagram.py` |
| B2 | `TracePathConfig` | `backend/app/agents/schemas/interactive_diagram.py` |
| B3 | `DescriptionMatchingConfig` | `backend/app/agents/schemas/interactive_diagram.py` |
| B4 | `ZoneHighlightConfig` | Shared across all three |
| B5 | `ParticleConfig` | Trace-path specific |
| B6 | `ConnectingLineConfig` | Description-matching specific |

---

## Appendix A: Config Defaults Quick Reference

### Click-to-Identify Defaults
```json
{
  "prompt_style": "functional",
  "selection_mode": "sequential",
  "highlight_style": "subtle",
  "magnification_enabled": false,
  "magnification_factor": 2.5,
  "magnification_activation": "toggle_button",
  "explore_mode_enabled": false,
  "zone_click_tolerance_px": 8,
  "show_zone_count": true,
  "disable_completed_zones": true
}
```

### Trace-Path Defaults
```json
{
  "path_type": "linear",
  "drawing_mode": "click_waypoints",
  "particle_theme": "dots",
  "particle_speed": "medium",
  "particle_count_per_segment": 5,
  "color_transition": { "enabled": false },
  "show_direction_arrows": true,
  "arrow_spacing_px": 60,
  "path_stroke_width": 3,
  "show_waypoint_labels": true,
  "gate_animations_enabled": false,
  "show_full_flow_on_complete": true,
  "loop_animation_on_complete": false
}
```

### Description-Matching Defaults
```json
{
  "match_mode": "drag_to_zone",
  "show_connecting_lines": true,
  "line_style": "curved",
  "defer_evaluation": false,
  "description_style": "functional",
  "description_length": "standard",
  "distractor_count": 2,
  "shuffle_descriptions": true,
  "zone_proximity_threshold_px": 40,
  "description_panel_position": "left",
  "card_size": "standard"
}
```

---

## Appendix B: Research Sources

- [Kenhub Anatomy Quizzes](https://www.kenhub.com/en/get/anatomy-quizzes)
- [Kenhub Anatomy Games](https://www.kenhub.com/en/get/anatomy-games)
- [Visible Body Quiz Documentation](https://support.visiblebody.com/hc/en-us/articles/216842658-Take-Quizzes)
- [Visible Body Courseware 3.1 Quizzing Updates](https://www.visiblebody.com/blog/introducing-the-courseware-3.1-quizzing-updates)
- [H5P Image Hotspot Question](https://h5p.org/image-hotspot-question)
- [H5P Find Multiple Hotspots](https://h5p.org/find-multiple-hotspots)
- [Seterra Map Quiz](https://www.geoguessr.com/quiz/seterra)
- [ASU Skeleton Viewer Game](https://askabiologist.asu.edu/games-sims/skeleton-viewer-game/play.html)
- [PhET Circuit Construction Kit](https://phet.colorado.edu/en/simulations/circuit-construction-kit-dc)
- [AHA Blood Flow Animation](https://watchlearnlive.heart.org/CVML_Mobile.php?moduleSelect=bldflo)
- [PBS NOVA Heart Map](https://www.pbs.org/wgbh/nova/body/map-human-heart.html)
- [USGS Interactive Water Cycle](https://www.usgs.gov/special-topics/water-science-school/science/interactive-water-cycle-diagrams-kids)
- [Field Day Water Cycle Simulation](https://fielddaylab.wisc.edu/play/water-sim/)
- [H5P Drag and Drop](https://h5p.org/drag-and-drop)
- [H5P Image Pairing](https://h5p.org/image-pairing)
- [Quizlet Match Game Help](https://help.quizlet.com/hc/en-us/articles/360031183611-Playing-Match)
- [SVG Path Animation (Codrops)](https://tympanus.net/codrops/2022/01/19/animate-anything-along-an-svg-path/)
- [Interactive Guide to SVG Paths (Josh Comeau)](https://www.joshwcomeau.com/svg/interactive-guide-to-paths/)
- [SVG Path Animation Tutorial (SVG AI)](https://www.svgai.org/blog/svg-path-animation-tutorial)
- [Inspera Hotspot Question Types](https://support.inspera.com/hc/en-us/articles/360024297072-Question-type-Hotspot)
- [HTML Image Maps (W3Schools)](https://www.w3schools.com/html/html_images_imagemap.asp)
- [Accessible Target Sizes (Smashing Magazine)](https://www.smashingmagazine.com/2023/04/accessible-tap-target-sizes-rage-taps-clicks/)
- [interact.js Drag and Drop](https://interactjs.io/)
- [Distractor Plausibility Research (arXiv:2501.13125)](https://arxiv.org/html/2501.13125v2)
- [Distractor Analysis for Test Items (Assessment Systems)](https://assess.com/distractor-analysis-test-items/)
- [Immediate vs Deferred Feedback (UNI ScholarWorks)](https://scholarworks.uni.edu/grp/1766/)
- [Gamification as Assessment (MDPI Electronics 2025)](https://www.mdpi.com/2079-9292/14/8/1573)
