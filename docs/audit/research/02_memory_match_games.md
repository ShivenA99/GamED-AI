# Memory Match / Card Matching Games: Component & Asset Research

**Date:** 2026-02-11
**Scope:** Components, assets, interactions, and configurable properties that make memory match games feel like real, engaging assessment games. Focused on what the mechanic NEEDS -- not scoring, hints, combos, or post-game review.

---

## Table of Contents

1. [Best-in-Class Examples](#1-best-in-class-examples)
2. [Core Visual Components](#2-core-visual-components)
3. [Game Variations](#3-game-variations)
4. [Configurable Properties](#4-configurable-properties)
5. [Pipeline Generation: Per-Pair Data Model](#5-pipeline-generation-per-pair-data-model)
6. [Gap Analysis: Current Implementation vs. Target](#6-gap-analysis-current-implementation-vs-target)
7. [Recommended Component Architecture](#7-recommended-component-architecture)

---

## 1. Best-in-Class Examples

### 1.1 BookWidgets (Memory Game + Pair Matching Widgets)

BookWidgets offers **two distinct matching widgets** that serve different assessment purposes:

**Memory Game Widget:**
- Cards are laid face-down; students flip two at a time to find matching pairs
- Supports: Text-Text, Text-Image, Image-Image, Text-Audio pair types
- Configurable number of cards to match difficulty to student level
- Audio support via browser text-to-speech (auto-generated from card text or alt-text on images)
- Optional completion question upon finishing

**Pair Matching Widget (Column Match):**
- Two columns displayed side by side; students draw lines or drag to connect related items
- Not a memory/concentration game -- items are always visible
- Tests association without the memory component

**Key Takeaway:** BookWidgets separates "memory recall" (face-down concentration) from "visible association" (column matching). Both assess the same knowledge but test different cognitive skills. Our pipeline should support both as game variants.

### 1.2 Quizlet Match / Scatter

**Match Mode:**
- Shows 6 pairs per round; larger sets split into multiple rounds
- Tap a term, then tap its matching definition to clear the pair
- Score = completion time; each incorrect tap adds 1 second penalty
- Competitive leaderboard: students see how their time compares to peers on the same set
- Grid-based layout (Micromatch variant) -- cards arranged in a neat grid, click-to-match

**Scatter Mode (Legacy):**
- All terms and definitions scattered randomly across the screen
- Drag a term onto its matching definition to clear the pair
- Timer runs continuously; errors add penalty time
- More kinetic and chaotic than the grid-based Match

**Key Takeaway:** Quizlet Match proves that **time-based scoring** creates engagement even with simple matching. The "6 pairs per round" chunking is a proven UX pattern for keeping cognitive load manageable.

### 1.3 Educaplay (Memory Game Maker)

**Scoring System:**
- Players start at 0 points, can earn up to 100
- Penalty system: maximum score for a card is halved each time a player flips without matching (except the first time); after the fourth miss on a card, score drops to zero for that card
- Optional life system: lose a life on each mismatch (configurable number of lives)
- Optional time limit per screen

**Pair Types:**
- Text, Audio, Pictures, Animated GIFs, or combinations
- Flexible grid sizes based on number of pairs

**Key Takeaway:** Educaplay's **per-card score decay** is a compelling assessment mechanism -- it rewards first-attempt recall without making the game impossible. The life system adds stakes.

### 1.4 H5P (Memory Game Content Type)

**Content Structure:**
- Each pair consists of two images (required) plus optional text descriptions
- When a matching pair is found, a configurable text message is displayed
- Theme color for card outlines is customizable
- Custom card back image (replaces default "?")

**Key Takeaway:** H5P's "show message on match" pattern is the **explanation reveal** mechanism -- after a successful match, a brief educational note appears. This reinforces learning without giving away answers during play.

### 1.5 Memrise (Spaced Repetition Matching)

**Matching Mechanic:**
- Integrates card matching into a broader spaced repetition system
- Missed words reappear more frequently in future sessions
- Gamification: daily streaks, achievement badges, progress tracking
- Multiple study modes (Learn, Classic Review, Speed Review) with matching as one option

**Key Takeaway:** Memrise shows that matching works best as **one mode within a larger learning flow**, not always as a standalone. This aligns with our multi-mechanic scene architecture.

### 1.6 Classic Concentration (Traditional Card Game)

**Variants documented in literature:**
- **Standard Concentration:** Cards in neat rows, flip two per turn
- **Spaghetti/Chaos:** Cards strewn randomly (not in a grid) -- increases spatial memory demand
- **Zebra:** Pairs must match by rule (same rank, opposite color) -- adds a reasoning layer
- **Two Decks Duel:** Competitive variant with separate fields for each player
- **Progressive difficulty:** Games with 30 levels, each group having Standard/Challenging/Perfect variants (0 misses allowed)

**Key Takeaway:** The "Spaghetti" variant (random scatter) and progressive difficulty tiers are underutilized in educational tools but create genuine engagement variety.

---

## 2. Core Visual Components

### 2.1 Card Face Designs

The card face is what the student sees when a card is flipped. For assessment, it must convey content clearly without giving away the match.

| Face Type | Content | Best For | Example |
|-----------|---------|----------|---------|
| `text` | Term, definition, short phrase | Vocabulary, definitions, formulas | "Mitochondria" |
| `image` | Photo, illustration, icon | Visual recognition, anatomy, art | Photo of a cell organelle |
| `diagram_closeup` | Cropped/zoomed region of the main diagram | Anatomy, geography, circuits | Zoomed view of the heart's left ventricle |
| `mixed` | Image with text caption overlay | Complex associations | Diagram region + its function label |
| `equation` | LaTeX-rendered formula or equation | Math, chemistry, physics | `E = mc^2` |
| `audio_icon` | Play button + waveform (audio plays on flip) | Language, music, pronunciation | Audio of a spoken word |

**Diagram Closeup Pattern (Novel for our pipeline):**
When the game is part of an INTERACTIVE_DIAGRAM template, each card can show a **cropped region** of the source diagram. The student's task is to match the closeup to its correct label, definition, or function. This leverages our existing zone coordinates to calculate crop regions:

```
crop_region = {
  x: zone.x - padding,
  y: zone.y - padding,
  width: zone.width + 2*padding,
  height: zone.height + 2*padding
}
```

This is a powerful assessment pattern because it tests whether the student can recognize a structure in isolation (without surrounding context clues).

### 2.2 Card Back Designs

The card back is what the student sees when the card is face-down. It should be uniform across all cards (no information leakage) and visually appealing.

**Card Back Styles:**

| Style | Description | Configurable Properties |
|-------|-------------|------------------------|
| `solid_gradient` | Gradient from two colors | `primary_color`, `secondary_color`, `direction` |
| `pattern` | Repeating geometric pattern | `pattern_type` (dots, stripes, chevrons, hexagons), `color`, `density` |
| `themed` | Subject-specific illustration | `theme` (biology, chemistry, geography, music) |
| `question_mark` | Classic "?" symbol | `icon_size`, `color` |
| `numbered` | Sequential numbers on card backs | `show_numbers: true` -- useful for remote play (call out "Card 7") |
| `custom_image` | Uploaded or generated image | `image_url` |

**Design Principles for Card Backs:**
- Must be **symmetrical** -- card should look identical when rotated 180 degrees
- All card backs within a game must be **identical** to prevent information leakage
- Color palette should **complement** the card face content, not distract from it
- Subtle texture or pattern is preferred over blank solid color (provides visual polish)

### 2.3 Card Flip Animation

The flip animation is the signature interaction of memory match games. It must feel physical and satisfying.

**CSS 3D Transform Approach:**

Three-element structure: `scene > card > face/back`

```css
.card-container {
  perspective: 1000px;  /* Creates depth */
}

.card {
  transform-style: preserve-3d;
  transition: transform 0.6s ease-out;
}

.card.flipped {
  transform: rotateY(180deg);
}

.card-face, .card-back {
  backface-visibility: hidden;  /* Hides reverse side during flip */
  position: absolute;
  inset: 0;
}

.card-face {
  transform: rotateY(180deg);  /* Pre-rotated so it shows when card flips */
}
```

**Configurable Animation Properties:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `flip_duration_ms` | number | 600 | How long the flip animation takes |
| `flip_axis` | 'Y' \| 'X' | 'Y' | Horizontal or vertical flip |
| `flip_easing` | string | 'ease-out' | CSS easing function |
| `mismatch_flip_delay_ms` | number | 900 | How long mismatched cards stay visible before flipping back |
| `mismatch_flip_multiplier` | number | 1.5 | Multiplier on flip_duration for the flip-back animation |

### 2.4 Match Confirmation Animation

When two cards are correctly matched, a confirmation animation reinforces the success.

**Animation Sequence (on correct match):**
1. **Green border pulse** -- cards' borders flash green (200ms)
2. **Scale bump** -- cards briefly scale to 1.05x then back (150ms ease-out)
3. **Particle burst** (optional) -- small confetti/sparkle particles spawn from each card's center
4. **Fade/shrink to matched state** -- cards either:
   - Fade to 60% opacity and remain in place (keeps grid stable)
   - Shrink and collapse out of the grid (more dramatic, but reshuffles layout)
   - Slide to a "matched pairs" collection area

**Mismatch Animation (on incorrect match):**
1. **Red border flash** -- cards' borders flash red (150ms)
2. **Shake** -- horizontal shake animation (3 oscillations, 300ms total)
3. **Pause** -- cards stay face-up for `mismatch_flip_delay_ms` so student can study them
4. **Flip back** -- cards flip back to face-down state

### 2.5 Grid Layout

The grid must be responsive, centered, and sized to fit the viewport without scrolling.

**Grid Sizing Table:**

| Pair Count | Grid (cols x rows) | Total Cards | Aspect Ratio Target |
|------------|--------------------|-------------|---------------------|
| 3 | 3 x 2 | 6 | Works on mobile |
| 4 | 4 x 2 | 8 | Standard small |
| 6 | 4 x 3 | 12 | Standard medium |
| 8 | 4 x 4 | 16 | Standard large |
| 10 | 5 x 4 | 20 | Advanced |
| 12 | 6 x 4 | 24 | Maximum recommended |
| 15 | 6 x 5 | 30 | Expert difficulty |

**Layout Rules:**
- Cards use `aspect-ratio: 4/3` (landscape) or `3/4` (portrait, better for text-heavy content)
- Grid gap: 8-12px between cards (wider gap = easier spatial memory)
- Max grid width: 800px (prevents cards from being too far apart on large screens)
- On mobile: grid collapses to fewer columns; cards stack rather than shrink below readable size
- Minimum card size: 80px x 60px (below this, text becomes unreadable)

---

## 3. Game Variations

### 3.1 Classic Concentration (`classic`)

The traditional memory game. All cards face-down in a grid. Flip two at a time; if they match, they stay revealed. If not, they flip back.

**Properties:**
- `allow_rearrange: false` -- cards stay in their shuffled positions
- `matched_card_behavior: 'fade'` -- matched cards fade but remain in grid
- `max_flips_visible: 2` -- only two cards can be face-up at once

**Assessment strength:** Tests pure recall of card positions and content associations.

### 3.2 Column Matching (`column_match`)

Two columns displayed side-by-side: terms on the left, definitions on the right (both always visible). Students draw connections between matching items by clicking one on each side.

**Properties:**
- `left_column_label: string` -- header for left column (e.g., "Terms")
- `right_column_label: string` -- header for right column (e.g., "Definitions")
- `shuffle_sides: 'right' | 'both' | 'none'` -- which column(s) to randomize
- `connection_style: 'line' | 'highlight' | 'drag'` -- how connections are visualized

**Assessment strength:** Tests association without memory burden. Faster to complete, better for larger pair counts.

**Key Difference from Classic:** Cards/items are always visible. No memory component. This is a pure association test.

### 3.3 Timed Scatter (`scatter`)

All cards (terms and definitions) are scattered randomly across the play area (not in a grid). Students drag a term onto its matching definition to clear the pair. Timer runs continuously.

**Properties:**
- `scatter_mode: 'random' | 'clustered' | 'radial'` -- initial card placement pattern
- `card_overlap_allowed: boolean` -- whether cards can overlap each other
- `time_pressure: boolean` -- whether a visible countdown timer is shown
- `drag_snap_distance: number` -- how close cards must be dragged to snap as a match

**Assessment strength:** Tests association speed under pressure. The spatial randomness prevents systematic scanning strategies, forcing genuine recognition.

### 3.4 Progressive Unlock (`progressive`)

Game starts with a small subset of pairs (e.g., 3 pairs / 6 cards). After completing them, more pairs are added to the grid. Difficulty increases as the grid grows.

**Properties:**
- `initial_pairs: number` -- how many pairs to start with (default: 3)
- `pairs_per_round: number` -- how many new pairs to add each round (default: 2)
- `unlock_animation: 'slide_in' | 'fade_in' | 'flip_in'` -- how new cards appear
- `difficulty_curve: 'linear' | 'exponential'` -- rate at which new pairs are added
- `rounds: number` -- total number of unlock rounds

**Assessment strength:** Manages cognitive load. Students build confidence with easy rounds before facing harder content. Naturally creates a difficulty curve.

### 3.5 One-Card-Revealed (`peek`)

A hybrid variant where one side of each pair is always face-up (e.g., definitions are visible) and the student must find the matching term among face-down cards. Reduces the memory burden while still requiring recall.

**Properties:**
- `revealed_side: 'front' | 'back'` -- which side of the pair stays visible
- `revealed_position: 'top_bar' | 'sidebar' | 'in_grid'` -- where revealed cards appear
- `sequential_reveal: boolean` -- whether one prompt is shown at a time (queue) or all at once

**Assessment strength:** More scaffolded than classic concentration. Good for initial learning or younger students. Focuses on one-directional recall (e.g., "given the definition, find the term").

---

## 4. Configurable Properties

### 4.1 Top-Level Configuration Schema

```typescript
interface MemoryMatchConfig {
  // === Content ===
  pairs: MemoryMatchPair[];          // The match pairs (see Section 5)

  // === Layout ===
  grid_size: [number, number];       // [cols, rows] -- auto-calculated if omitted
  card_aspect_ratio: '4:3' | '3:4' | '1:1';  // Card shape
  card_gap_px: number;               // Gap between cards (default: 10)
  max_grid_width_px: number;         // Maximum grid width (default: 800)

  // === Game Variant ===
  game_variant: 'classic' | 'column_match' | 'scatter' | 'progressive' | 'peek';

  // === Card Face ===
  card_face_type: 'text_text' | 'text_image' | 'image_image'
                | 'image_text' | 'diagram_closeup_text' | 'mixed';

  // === Card Back ===
  card_back_style: 'solid_gradient' | 'pattern' | 'themed'
                 | 'question_mark' | 'numbered' | 'custom_image';
  card_back_config: {
    primary_color?: string;
    secondary_color?: string;
    pattern_type?: 'dots' | 'stripes' | 'chevrons' | 'hexagons' | 'crosshatch';
    theme?: 'biology' | 'chemistry' | 'geography' | 'mathematics' | 'language' | 'music';
    image_url?: string;
    show_numbers?: boolean;
  };

  // === Match Type ===
  match_type: 'identical'             // Find two identical cards
            | 'term_to_definition'     // Term card + definition card
            | 'image_to_label'         // Image card + text label card
            | 'concept_to_example'     // Abstract concept + concrete example
            | 'cause_to_effect'        // Cause card + effect card
            | 'part_to_whole'          // Component + system it belongs to
            | 'diagram_region_to_label'; // Cropped diagram region + text label

  // === Animation ===
  flip_duration_ms: number;           // Flip animation duration (default: 600)
  flip_axis: 'Y' | 'X';              // Flip direction (default: 'Y')
  mismatch_delay_ms: number;          // Time mismatched cards stay visible (default: 900)
  matched_card_behavior: 'fade' | 'shrink' | 'collect' | 'checkmark';
  show_match_particles: boolean;      // Particle effect on correct match (default: true)

  // === Difficulty ===
  mismatch_penalty: 'none' | 'score_decay' | 'life_loss' | 'time_penalty';
  lives: number | null;               // Number of lives (null = unlimited)
  time_limit_seconds: number | null;   // Time limit (null = untimed)
  show_attempts_counter: boolean;      // Show attempt count (default: true)

  // === Educational ===
  show_explanation_on_match: boolean;  // Show explanation text after a correct match
  explanation_display_ms: number;      // How long explanation is visible (default: 2000)

  // === Progressive Unlock (variant-specific) ===
  progressive_config?: {
    initial_pairs: number;
    pairs_per_round: number;
    unlock_animation: 'slide_in' | 'fade_in' | 'flip_in';
  };

  // === Column Match (variant-specific) ===
  column_config?: {
    left_label: string;
    right_label: string;
    shuffle_sides: 'right' | 'both' | 'none';
    connection_style: 'line' | 'highlight' | 'drag';
  };

  // === Scatter (variant-specific) ===
  scatter_config?: {
    scatter_mode: 'random' | 'clustered' | 'radial';
    card_overlap_allowed: boolean;
    drag_snap_distance: number;
  };

  // === Instructions ===
  instructions: string;               // Instruction text for the student
}
```

### 4.2 Property Defaults by Game Variant

| Property | Classic | Column Match | Scatter | Progressive | Peek |
|----------|---------|-------------|---------|-------------|------|
| `grid_size` | auto | N/A | N/A | auto (grows) | auto |
| `card_back_style` | `pattern` | N/A (visible) | `question_mark` | `pattern` | `pattern` |
| `flip_duration_ms` | 600 | N/A | 400 | 600 | 600 |
| `matched_card_behavior` | `fade` | `highlight` | `shrink` | `fade` | `collect` |
| `mismatch_penalty` | `none` | `none` | `time_penalty` | `score_decay` | `none` |
| `time_limit_seconds` | `null` | `null` | 60 | `null` | `null` |
| `show_explanation_on_match` | `true` | `true` | `false` | `true` | `true` |

---

## 5. Pipeline Generation: Per-Pair Data Model

### 5.1 MemoryMatchPair Schema

Each pair generated by the pipeline must include enough data to render both card faces, validate the match, and (optionally) teach after the match.

```typescript
interface MemoryMatchPair {
  // === Identity ===
  pair_id: string;                    // Unique identifier (e.g., "pair_mitochondria")

  // === Card A (Front) ===
  front_content: string;              // Text content or image URL for card A
  front_type: 'text' | 'image' | 'equation' | 'audio';
  front_label?: string;               // Accessibility label if front is non-text

  // === Card B (Back) ===
  back_content: string;               // Text content or image URL for card B
  back_type: 'text' | 'image' | 'equation' | 'audio';
  back_label?: string;                // Accessibility label if back is non-text

  // === Educational Metadata ===
  explanation: string;                 // Shown after successful match
  category?: string;                   // Grouping for progressive unlock or theming
  difficulty?: 1 | 2 | 3 | 4 | 5;    // Difficulty level of this specific pair

  // === Diagram Integration (when card_face_type includes diagram_closeup) ===
  zone_id?: string;                    // Links to a zone in the parent diagram
  crop_region?: {                      // Calculated from zone coordinates
    x: number;                         // % from left
    y: number;                         // % from top
    width: number;                     // % width
    height: number;                    // % height
    padding: number;                   // Extra padding around zone (%)
  };

  // === Distractor Metadata (for pipeline validation) ===
  common_misconception?: string;       // What students commonly confuse this with
  distractor_pair_id?: string;         // ID of a pair that students might confuse with this one
}
```

### 5.2 Pipeline Generation Flow

The pipeline must generate pairs from upstream agent outputs. The flow depends on the `match_type`:

**For `term_to_definition`:**
```
zone_labels (from zone detector) + label_descriptions (from DK retriever)
  --> pair.front_content = label.text
  --> pair.back_content = description
  --> pair.explanation = extended_description
```

**For `image_to_label`:**
```
zone_coordinates (from zone detector) + diagram_image (from image pipeline)
  --> pair.front_content = crop_image(diagram, zone.coordinates)
  --> pair.front_type = 'image'
  --> pair.back_content = label.text
  --> pair.back_type = 'text'
```

**For `concept_to_example`:**
```
domain_knowledge (from DK retriever) + game_design (from game designer)
  --> LLM generates example for each concept
  --> pair.front_content = concept
  --> pair.back_content = example
```

**For `diagram_region_to_label`:**
```
zones (from zone detector) + diagram_image
  --> pair.front_content = zoomed_crop_url(diagram, zone, padding=15%)
  --> pair.front_type = 'image'
  --> pair.back_content = zone.label
  --> pair.back_type = 'text'
  --> pair.zone_id = zone.id
  --> pair.crop_region = calculated from zone coordinates
```

### 5.3 Pair Count Guidelines

| Assessment Goal | Recommended Pairs | Grid Size | Estimated Time |
|-----------------|-------------------|-----------|----------------|
| Quick check (3-5 min) | 4-6 | 3x3 or 4x3 | 2-4 minutes |
| Standard assessment | 6-10 | 4x3 or 4x4 | 5-8 minutes |
| Comprehensive review | 10-15 | 5x4 or 6x5 | 10-15 minutes |
| Progressive unlock | 12-20 (in rounds of 3-4) | Grows from 3x2 to 5x4 | 8-12 minutes |

---

## 6. Gap Analysis: Current Implementation vs. Target

### 6.1 Current State (MemoryMatch.tsx)

The existing implementation at `frontend/src/components/templates/InteractiveDiagramGame/interactions/MemoryMatch.tsx` has:

**What exists:**
- Basic card grid with flip animation (opacity-based, not true 3D CSS transform)
- MatchPair interface with front/back content and type (text/image)
- Configurable grid size, flip duration, mismatch flip multiplier
- Attempt counter and matched count display
- Store integration props (storeProgress, onPairMatched, onAttemptMade)
- Reset functionality
- Score calculation based on attempts vs. perfect score

**What is missing (gaps):**

| Gap | Priority | Description |
|-----|----------|-------------|
| No 3D flip animation | HIGH | Current flip uses opacity toggle, not CSS 3D `rotateY`. Cards don't visually rotate. |
| No card back customization | MEDIUM | Card back is always a blue-purple gradient with "?" |
| No match confirmation animation | HIGH | No green pulse, scale bump, or particle effects on correct match |
| No mismatch shake animation | HIGH | No red flash or shake on incorrect match |
| No game variants | HIGH | Only classic concentration mode exists. No column match, scatter, progressive, or peek variants. |
| No diagram closeup support | MEDIUM | `card_face_type` limited to text/image. No crop region rendering. |
| No explanation reveal | MEDIUM | No `show_explanation_on_match` behavior -- matched cards just fade |
| No match_type awareness | MEDIUM | All pairs treated the same regardless of match_type |
| No progressive unlock | LOW | No ability to start with fewer pairs and add more |
| No mismatch penalty modes | LOW | No score decay, life loss, or time penalty options |
| No card aspect ratio config | LOW | Cards are always 4:3 aspect ratio |
| No numbered card backs | LOW | No option to show numbers on card backs for remote play |
| Backend pair generation is basic | MEDIUM | `scene_architect_tools.py` just maps labels to descriptions. No LLM enrichment, no crop regions, no difficulty classification. |

### 6.2 Backend Schema State

The backend `MemoryMatchDesign` in `game_design_v3.py` has:
- `pairs: List[Dict[str, str]]` -- just `{front, back}` dicts, no typing info
- `grid_size: Optional[List[int]]`
- `flip_duration_ms: int`

Missing from backend: `match_type`, `game_variant`, `card_back_style`, `card_face_type`, `explanation`, `category`, `difficulty`, `crop_region`, `mismatch_penalty`.

---

## 7. Recommended Component Architecture

### 7.1 Component Hierarchy

```
MemoryMatch (root)
  |-- MemoryMatchGrid (classic concentration layout)
  |     |-- CardSlot (grid position wrapper)
  |           |-- FlipCard (3D flip animation container)
  |                 |-- CardFace (front content renderer)
  |                 |     |-- TextFace / ImageFace / DiagramCloseupFace / EquationFace
  |                 |-- CardBack (back design renderer)
  |                       |-- GradientBack / PatternBack / ThemedBack / NumberedBack
  |
  |-- ColumnMatchView (side-by-side column layout, variant: column_match)
  |     |-- ColumnItem (term or definition item)
  |     |-- ConnectionLine (SVG line between matched items)
  |
  |-- ScatterView (random placement layout, variant: scatter)
  |     |-- DraggableCard (draggable card with physics)
  |
  |-- ProgressiveWrapper (adds unlock rounds, variant: progressive)
  |     |-- RoundIndicator (shows current round and upcoming pairs)
  |
  |-- ExplanationOverlay (appears after correct match)
  |-- MatchParticles (particle effect on correct match)
  |-- StatsBar (attempts, matched count, timer, lives)
```

### 7.2 Card Face Content Renderers

Each card face type needs its own renderer to handle content appropriately:

| Renderer | Input | Output |
|----------|-------|--------|
| `TextFace` | `content: string` | Centered text, auto-sized font, overflow ellipsis |
| `ImageFace` | `content: string (URL)` | `object-fit: contain` image, alt text |
| `DiagramCloseupFace` | `content: string (URL)`, `crop_region` | CSS `object-position` + `object-fit` to show cropped region of full diagram |
| `EquationFace` | `content: string (LaTeX)` | KaTeX-rendered equation |
| `MixedFace` | `image_url + caption` | Image with text overlay at bottom |

### 7.3 Animation Specifications

**Correct Match Sequence:**
```
t=0ms     : Border transitions to green (#22c55e), scale to 1.05
t=200ms   : Scale back to 1.0
t=300ms   : Particle burst (8-12 particles, random directions, fade over 600ms)
t=400ms   : If show_explanation_on_match, overlay fades in
t=400+explanation_display_ms : Overlay fades out
t=last    : Card transitions to matched state (opacity 0.6 or collected)
```

**Incorrect Match Sequence:**
```
t=0ms           : Border transitions to red (#ef4444)
t=0-300ms       : Horizontal shake (translateX: 0 -> -4px -> 4px -> -4px -> 0)
t=300ms         : Border fades back to neutral
t=mismatch_delay_ms : Cards flip back to face-down (over flip_duration_ms)
```

**Card Entrance (game start or progressive unlock):**
```
t=0ms     : Cards at scale(0.8), opacity(0)
t=stagger : Each card delayed by (index * 50ms)
t+300ms   : Cards at scale(1.0), opacity(1), with ease-out-back easing
```

### 7.4 Accessibility Requirements

| Requirement | Implementation |
|-------------|----------------|
| Keyboard navigation | Tab through cards, Enter/Space to flip, arrow keys within grid |
| Screen reader | `aria-label` on each card: "Card [position], [face-down/shows: content]" |
| Focus indicators | Visible focus ring (2px solid blue) on keyboard-focused card |
| Reduced motion | `prefers-reduced-motion: reduce` disables flip animation, uses instant swap |
| Color independence | Match/mismatch indicated by icon (checkmark/X) in addition to color |
| High contrast | Card borders meet 4.5:1 contrast ratio in all states |

---

## Summary of Findings

Memory match games succeed as assessment mechanics when they combine:

1. **Satisfying card physics** -- 3D CSS transforms with proper perspective, easing, and backface-visibility create the tactile feel that makes the game engaging rather than clinical.

2. **Clear visual feedback** -- Green pulse + particles for matches, red shake for mismatches. These are not decorative; they provide instant formative assessment feedback.

3. **Variant diversity** -- Classic concentration, column matching, timed scatter, progressive unlock, and peek modes each test different cognitive skills (memory, association speed, scaffolded recall). The pipeline should select the variant based on the assessment goal.

4. **Rich card face types** -- Text-only is the baseline. Image-to-text, diagram closeup-to-label, and equation-to-description pairs create genuinely interesting assessment challenges. The diagram closeup pattern is especially powerful for anatomy, geography, and circuit diagrams.

5. **Configurable difficulty** -- Grid size, pair count, time limits, mismatch penalties, and progressive unlock all serve as difficulty levers that the pipeline can tune based on the target audience and subject matter.

6. **Explanation reveal** -- Showing a brief educational note after each successful match turns the game from pure testing into a testing-plus-reinforcement loop, without giving away answers during active play.

The current codebase implementation covers the basic concentration variant with text/image support but lacks 3D animations, game variants, diagram integration, and backend pair enrichment. These gaps represent the work needed to bring memory match to the quality level of BookWidgets, Quizlet Match, and Educaplay.
