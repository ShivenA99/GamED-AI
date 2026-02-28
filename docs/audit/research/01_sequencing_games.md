# Sequencing Games: Components & Assets for Game-Like Assessment

## Purpose

This document defines what visual components, assets, interactions, and configurable properties are needed to make a **sequencing (ordering) mechanic** feel like a real, engaging assessment game -- not a sortable text list.

Scope: Only mechanic-specific components and assets. Excludes scoring strategies, hint systems, post-game review, combo/streak mechanics, and other game-wide features handled separately.

---

## 1. Reference Examples: What Makes Great Sequencing Games

### 1.1 Timeline (Asmodee Board Game)

The gold standard for sequencing-as-game. Players hold illustrated cards showing historical events (one side shows the event + image, the other reveals the date). Each turn, a player must **insert a card between** existing cards on a growing timeline. After placement, the card is flipped: if the date is correct relative to its neighbors, it stays; otherwise the player draws a replacement.

**Key design lessons:**
- **Insert-between mechanic**: The core interaction is not "reorder a full list" but "place one card into an existing sequence." This creates a fundamentally different cognitive load -- students evaluate relative position ("does this go before or after X?") rather than sorting an entire set.
- **Progressive difficulty**: As more cards are placed, the gaps between positions narrow, making each subsequent placement harder. The timeline literally gets tighter.
- **Rich item cards**: Each card is a self-contained mini-artifact with an illustration, title, and hidden answer. The two-sided card is essential -- the front is a question, the back is confirmation.
- **Spatial physicality**: Cards occupy real space on a track. The timeline is a visible, growing artifact.

### 1.2 H5P Image Sequencing

A free HTML5 content type where learners receive a set of image cards (each with an image and optional text description) in randomized order and must drag them into the correct sequence. Used widely in Moodle and WordPress LMS platforms.

**Key design lessons:**
- **Image-first cards**: Each item is primarily an image with a text label underneath, not a text string with an optional image. The image IS the content.
- **Horizontal track**: Items are arranged left-to-right in a horizontal strip, reinforcing the "sequence as timeline" metaphor.
- **Visual card identity**: Each card has a distinct visual identity through its image, making the set feel like a collection of artifacts rather than a list of strings.

### 1.3 Cell Mitosis Puzzle (Planeta42)

Students receive microscope images of cells in various stages of mitosis (prophase, metaphase, anaphase, telophase) and must drag them into labeled phase slots in the correct order.

**Key design lessons:**
- **Slot-based placement**: Instead of reordering a list, students drag items into distinct labeled slots/positions on a track. The slots exist before any items are placed, creating a clear spatial target.
- **Diagram context**: The ordering happens over or alongside a reference diagram, connecting abstract sequence knowledge to visual anatomy.
- **Image-centric items**: Each item is a microscope image, not a text label. The student must recognize the visual characteristics of each phase.

### 1.4 Physical Sequencing Cards (Spark Cards, etc.)

Commercial educational card sets (3-scene, 4-scene, 6-scene) with illustrated cards depicting steps in a process. Numbers on the back allow self-checking.

**Key design lessons:**
- **Card-as-object metaphor**: Each step is a physical card with borders, rounded corners, and an illustration. Not a row in a table.
- **Self-check by flip**: The answer (position number) is hidden on the back, revealed only after placement. This is the physical-world equivalent of test mode.
- **Small set sizes**: Effective sequencing uses 3-8 items, not 15+. Cognitive load matters.

---

## 2. Visual Components That Make Sequencing Game-Like

The current SequenceBuilder component is a vertical sortable list with plain text rows and a drag handle icon. Below is everything needed to transform it into a game-like experience.

### 2.1 Item Cards

The single most important upgrade. Each sequencing item should be rendered as a **card** -- a distinct visual object with borders, shadows, and internal layout -- not a list row.

#### Card Anatomy

```
+------------------------------------------+
|  [IMAGE AREA]                            |   <-- Optional: 40-60% of card height
|  (illustration, diagram, photo)          |
|------------------------------------------|
|  TITLE TEXT                              |   <-- Required: item name/label
|  Description text (1-2 lines)            |   <-- Optional: supporting context
|  [Icon] [Tag]                            |   <-- Optional: category badge, icon
+------------------------------------------+
```

#### Card Type Configurations

| Card Type | Image | Title | Description | Use Case |
|-----------|-------|-------|-------------|----------|
| `image_and_text` | Yes (top) | Yes | Yes | Science processes with visual stages |
| `image_only` | Yes (full) | Overlay | No | Visual recognition ordering |
| `text_only` | No | Yes | Yes | Abstract/historical sequences |
| `icon_and_text` | Icon (left) | Yes | Yes | Compact step sequences |
| `numbered_text` | No | Yes | No | Simple ordered lists |

#### Card Visual Properties

- **Border**: Rounded corners (8-12px), subtle shadow on idle, elevated shadow on drag
- **Background**: White or light gradient, distinct from track background
- **Drag state**: Card lifts (scale 1.03-1.05), shadow deepens, slight rotation (1-2 deg), opacity reduction on original position (ghost)
- **Placed state**: Card snaps into slot with a brief spring animation (100-200ms)
- **Size**: Cards should be substantial enough to feel like objects (min 120px wide for text-only, min 180px for image cards)

### 2.2 The Track / Sequence Lane

The surface on which cards are placed. This transforms "a list" into "a path."

#### Track Layout Modes

**Horizontal Timeline**
```
[Card 1] ----> [Card 2] ----> [Card 3] ----> [Card 4]
    1              2              3              4
```
Best for: chronological sequences, process steps, historical events. Reads left-to-right naturally. Works well with 3-8 items.

**Vertical Timeline**
```
   [Card 1]
      |
      v
   [Card 2]
      |
      v
   [Card 3]
```
Best for: top-down processes (water cycle, food chain), cause-and-effect chains, biological pathways. Scrollable for longer sequences.

**Circular / Cyclic**
```
        [Card 1]
       /         \
   [Card 4]    [Card 2]
       \         /
        [Card 3]
```
Best for: life cycles, repeating processes (water cycle, seasons, cell cycle). Items are arranged around a circle or ellipse with directional arrows showing flow.

**Flowchart / Branching**
```
   [Card 1]
      |
   [Card 2]
     / \
[Card 3] [Card 3a]
     \ /
   [Card 4]
```
Best for: decision processes, branching paths, conditional sequences. Requires additional configuration for branch points.

**Insert-Between (Timeline Game Style)**
```
Existing:  [Card A] ---- [Card C] ---- [Card E]
                    ^insert here?    ^or here?

Player hand: [Card B] [Card D]
```
Best for: assessment where students must determine relative position rather than absolute order. More challenging and more game-like than drag-to-reorder.

#### Track Visual Properties

- **Track background**: Subtle gradient or patterned lane (e.g., dashed line, rail marks, road texture)
- **Slot indicators**: Numbered circles, dotted outlines, or glowing rectangles showing where cards belong
- **Direction indicators**: Arrows, chevrons, or gradient showing flow direction
- **Track borders**: Start marker ("Begin" / "First") and end marker ("End" / "Last")

### 2.3 Connectors Between Placed Items

Once cards are placed in slots, visual connectors between them reinforce the sequence relationship.

#### Connector Styles

| Style | Visual | Best For |
|-------|--------|----------|
| `arrow` | Solid arrow line between cards | Linear processes, cause-effect |
| `dashed_arrow` | Dashed arrow line | Temporal sequences, "then..." |
| `numbered_circles` | Numbered circles on a rail between cards | Step-by-step procedures |
| `chevron` | Chevron/ribbon connecting cards | Progress/flow metaphor |
| `curved_path` | Curved SVG path between cards | Organic processes, biological flows |
| `none` | No connector (cards in slots only) | Simple ordering |

#### Connector Properties

- **Color**: Matches track theme or uses a configurable accent color
- **Animation**: Connectors can draw in progressively as cards are placed (line grows from placed card toward next slot)
- **Width**: 2-4px for lines, proportional for chevrons
- **Arrowhead**: Optional directional arrowhead at the destination end

### 2.4 Slots / Drop Targets

The positions where cards will be placed. Slots should look like invitation targets, not empty list gaps.

#### Slot Styles

| Style | Visual | Description |
|-------|--------|-------------|
| `outlined` | Dashed border rectangle matching card dimensions | Clear target, minimal visual weight |
| `numbered` | Circle with position number + outlined area | Shows explicit position numbering |
| `shadow` | Subtle card-shaped shadow/silhouette | Suggests "a card belongs here" |
| `labeled` | Slot with a label like "Step 1", "Phase 2" | Provides context for each position |
| `minimal` | Thin line or dot indicating drop point | For insert-between mode |
| `glowing` | Pulsing border highlight on hover/nearby drag | High affordance, gamified feel |

#### Slot Behavior

- **Idle**: Visible but understated (dashed outline or shadow)
- **Drag nearby**: Slot expands slightly and highlights, indicating it is a valid target
- **Hover over**: Slot border becomes solid, background color shifts, "snap zone" activates
- **Occupied**: Slot background fills, border becomes solid, card snaps into place
- **Locked**: After submission or in certain modes, placed cards become non-draggable with a locked icon

### 2.5 Item Source Area (Tray / Hand / Pool)

Where unplaced cards live before the student moves them to the track.

#### Source Area Configurations

| Mode | Visual | Description |
|------|--------|-------------|
| `card_tray` | Horizontal scrollable row below the track | Cards fan out like a hand of cards |
| `card_stack` | Stacked pile with only top card visible | Progressive reveal (one at a time) |
| `scattered_pool` | Cards scattered randomly in a bounded area | Feels more game-like, less list-like |
| `sidebar_column` | Vertical column alongside the track | Standard, space-efficient |

### 2.6 Position Indicators

Visual markers showing the sequence position along the track.

- **Numbered circles**: 1, 2, 3... at each slot position
- **Ordinal labels**: "First", "Second", "Third" or "Step 1", "Step 2"
- **Start/end markers**: Arrow or icon at the beginning and end of the track
- **Progress dots**: Small dots along the track rail, filled as cards are placed

---

## 3. Interaction Patterns

### 3.1 Drag-to-Reorder (Current Implementation)

The student sees all items in a vertical list and drags them up/down to rearrange. This is the simplest pattern and what the current SequenceBuilder implements.

**Strengths**: Simple to implement, familiar UX pattern, works for any number of items.
**Weaknesses**: Feels like a sortable todo list, not a game. No spatial metaphor. No sense of "placing" items.

**Micro-interactions needed:**
- Card lift animation on grab (scale up, shadow deepen)
- Other cards animate out of the way as dragged card moves between them (100ms smooth transition)
- Ghost card at original position during drag
- Snap animation on drop (spring ease, 150ms)
- Haptic feedback on mobile (if available)

### 3.2 Drag-to-Slots (Recommended Primary)

Items start in a source area (tray/pool). The student drags individual cards to numbered/labeled slots on a track. Each slot accepts one card.

**Strengths**: Spatial and visual. Clear separation between "available items" and "placed items." Feels like assembling a sequence. The track is a persistent visual artifact.
**Weaknesses**: Requires more screen real estate. Must handle slot swapping if student wants to change a placement.

**Micro-interactions needed:**
- Card picks up from tray with lift animation
- Valid slots highlight as card is dragged near them
- Card snaps into slot with alignment animation
- Connector line draws in after card is placed
- Slot-swap: if dragging a card over an occupied slot, the existing card returns to tray

### 3.3 Insert-Between (Timeline Game Style)

Inspired by the Timeline board game. A partial sequence is already placed (or grows as items are placed). The student takes one card at a time and must insert it at the correct position between existing cards.

**Strengths**: Most game-like. Tests relative ordering, which is a deeper cognitive skill. Inherently progressive -- each placement makes the next one harder. Feels like a strategy game.
**Weaknesses**: More complex to implement. Requires deciding whether to reveal correctness per placement or only at the end.

**Micro-interactions needed:**
- Insert indicators appear between each pair of placed cards and at both ends
- Insert indicators expand on hover/drag-near
- Placed cards animate apart to create space for the new card
- New card slides into the gap with a settling animation
- Remaining cards in hand/tray update count

### 3.4 Click-to-Place (Tap Sequential)

No dragging. The student clicks/taps items in the order they believe is correct. Each clicked item is appended to the next available slot on the track.

**Strengths**: Works perfectly on mobile/touch. Faster interaction. Accessible (no drag precision needed).
**Weaknesses**: Less spatial reasoning. Harder to correct mistakes mid-sequence (must undo or restart from a point).

**Micro-interactions needed:**
- Card highlights on hover indicating it is selectable
- On click, card animates flying from tray to next open slot on track
- "Undo last" button removes the most recent placement and returns it to tray
- Placed cards show their assigned position number

### 3.5 Reveal Modes

How items become available to the student.

| Mode | Description | Effect |
|------|-------------|--------|
| `all_at_once` | All items visible from the start | Standard for most assessments |
| `progressive` | Items revealed one at a time (from a draw pile) | Timeline game style, more suspenseful |
| `timed_reveal` | Items appear at intervals | Adds time pressure dimension |
| `category_groups` | Items grouped by category, one group at a time | For multi-stage processes |

---

## 4. Configurable Properties

### 4.1 Layout Configuration

```typescript
interface SequencingLayoutConfig {
  /** Track orientation and shape */
  layout_mode: 'horizontal_timeline' | 'vertical_timeline' | 'circular'
             | 'flowchart' | 'insert_between';

  /** How items are presented to the student */
  interaction_pattern: 'drag_to_reorder' | 'drag_to_slots'
                     | 'insert_between' | 'click_to_place';

  /** Where unplaced items live */
  source_area: 'card_tray' | 'card_stack' | 'scattered_pool' | 'sidebar_column';

  /** How items become available */
  reveal_mode: 'all_at_once' | 'progressive' | 'timed_reveal' | 'category_groups';

  /** Track direction (for horizontal/vertical) */
  direction: 'left_to_right' | 'right_to_left' | 'top_to_bottom' | 'bottom_to_top';

  /** Whether the track scrolls if items overflow */
  scrollable: boolean;
}
```

### 4.2 Item Card Configuration

```typescript
interface ItemCardConfig {
  /** Visual style of each item card */
  card_type: 'image_and_text' | 'image_only' | 'text_only'
           | 'icon_and_text' | 'numbered_text';

  /** Card dimensions */
  card_size: 'small' | 'medium' | 'large';

  /** Border and shadow style */
  card_style: 'flat' | 'elevated' | 'bordered' | 'glassmorphic';

  /** Whether cards have a colored category accent */
  show_category_accent: boolean;

  /** Image aspect ratio for image cards */
  image_aspect_ratio: '1:1' | '4:3' | '16:9' | '3:4';

  /** Whether to show item description text below title */
  show_description: boolean;
}
```

### 4.3 Connector Configuration

```typescript
interface ConnectorConfig {
  /** Visual style of connectors between placed items */
  connector_style: 'arrow' | 'dashed_arrow' | 'numbered_circles'
                 | 'chevron' | 'curved_path' | 'none';

  /** Connector color (CSS color or theme token) */
  connector_color: string;

  /** Whether connectors animate in as cards are placed */
  animate_connectors: boolean;

  /** Arrow/chevron size */
  connector_size: 'small' | 'medium' | 'large';
}
```

### 4.4 Slot Configuration

```typescript
interface SlotConfig {
  /** Visual style of drop target slots */
  slot_style: 'outlined' | 'numbered' | 'shadow' | 'labeled' | 'minimal' | 'glowing';

  /** Labels for slots (e.g., "Step 1", "Phase A") */
  slot_labels?: string[];

  /** Whether to show position numbers on slots */
  show_position_numbers: boolean;

  /** Whether to show start/end markers */
  show_endpoints: boolean;

  /** Endpoint labels */
  start_label?: string;  // e.g., "Begin", "First", "Start"
  end_label?: string;    // e.g., "End", "Last", "Finish"
}
```

### 4.5 Full Sequencing Mechanic Config

```typescript
interface SequencingMechanicConfig {
  layout: SequencingLayoutConfig;
  item_card: ItemCardConfig;
  connector: ConnectorConfig;
  slot: SlotConfig;

  /** Custom instruction text for the task */
  instruction_text: string;

  /** Whether the sequence is cyclic (last connects back to first) */
  is_cyclic: boolean;

  /** Sequence type label displayed to user (e.g., "Timeline", "Process Steps") */
  sequence_type_label?: string;

  /** Theme override for track area background */
  track_theme?: 'default' | 'timeline' | 'scientific' | 'historical' | 'flowchart';
}
```

---

## 5. Pipeline Data Requirements

### 5.1 Per-Item Data (What the Pipeline Must Generate)

Each item in the sequence must include:

```typescript
interface SequenceItem {
  /** Unique identifier for this item */
  item_id: string;

  /** Display title (required) -- short label for the card */
  text: string;

  /** Extended description (optional) -- 1-2 sentences of context */
  description?: string;

  /** Correct position in sequence (0-indexed) */
  order_index: number;

  /** Image specification (optional) */
  image?: {
    /** What to generate/retrieve: prompt or asset query */
    prompt: string;
    /** Alt text for accessibility */
    alt_text: string;
    /** Whether this is a diagram crop, photo, illustration, or icon */
    image_type: 'diagram_crop' | 'photo' | 'illustration' | 'icon';
  };

  /** Icon identifier if using icon_and_text card type */
  icon?: string;

  /** Category for grouping/color-coding (optional) */
  category?: string;

  /** Distractor flag -- item does NOT belong in the sequence */
  is_distractor?: boolean;
}
```

### 5.2 Sequence-Level Data

```typescript
interface SequenceDefinition {
  /** All items including distractors */
  items: SequenceItem[];

  /** Correct order as array of item_ids (excludes distractors) */
  correct_order: string[];

  /** Type of sequence for layout hinting */
  sequence_type: 'linear' | 'cyclic' | 'branching';

  /** The mechanic configuration */
  mechanic_config: SequencingMechanicConfig;

  /** Number of items (for validation) */
  item_count: number;

  /** Whether distractors are included */
  has_distractors: boolean;

  /** Number of distractor items */
  distractor_count: number;
}
```

### 5.3 Pipeline Generation Responsibilities

| Agent | Generates | Details |
|-------|-----------|---------|
| **Game Planner** | `sequence_type`, `item_count`, `has_distractors` | Decides what kind of sequence is appropriate for the question |
| **Interaction Designer** | `mechanic_config` (full) | Selects layout mode, card type, connector style, slot style based on content |
| **Scene Architect** | `items[]` with `text`, `description`, `order_index`, `category` | Creates the actual sequence items with correct ordering |
| **Asset Generator** | `items[].image` assets | Generates or retrieves images for each item card |
| **Blueprint Assembler** | Assembled `SequenceDefinition` | Combines all upstream data into the blueprint `sequenceConfig` |

---

## 6. What the Current Implementation Lacks

Comparing the research findings to the current `SequenceBuilder.tsx`:

| Feature | Current State | Target State |
|---------|--------------|--------------|
| **Item cards** | Plain text rows with drag handle icon | Rich cards with image, title, description, borders, shadows |
| **Layout** | Vertical list only | Horizontal timeline, vertical timeline, circular, flowchart, insert-between |
| **Track/lane** | No track -- items float in a div | Visual track with start/end markers, background lane, direction indicators |
| **Connectors** | None | Arrows, dashed lines, numbered circles, chevrons between placed items |
| **Slots** | No slots -- items are in a reorderable list | Distinct slot targets with outlines, numbers, labels, glow effects |
| **Source area** | Items start in the list (no separate source) | Card tray, card stack, scattered pool, or sidebar |
| **Interaction** | Drag-to-reorder only | Drag-to-slots, insert-between, click-to-place |
| **Card images** | Not supported | Image area per card with configurable aspect ratio |
| **Reveal mode** | All items visible immediately | Progressive, timed, category-grouped options |
| **Cyclic layout** | Not supported | Circular track layout with wrap-around connector |
| **Distractors** | Not supported | Extra items that don't belong in the sequence |
| **Micro-interactions** | Basic dnd-kit transform | Lift, snap, ghost, connector draw-in, slot highlight animations |

---

## 7. Recommended Implementation Priorities

### Phase A: Card Upgrade (Highest Impact, Lowest Effort)

Transform the SortableItem from a text row into a proper item card:
- Add image area (top of card, configurable aspect ratio)
- Add card border, shadow, rounded corners
- Add description text below title
- Add drag state animations (lift, shadow, rotation)
- Add snap animation on drop
- Support `card_type` prop to switch between image_and_text, text_only, icon_and_text

This single change transforms the feel from "sortable list" to "card game."

### Phase B: Track and Slots

Add a visual track behind the card positions:
- Track lane with background, start/end markers
- Slot indicators (outlined, numbered, or shadow) at each position
- Direction arrows or chevrons on the track
- Support horizontal and vertical layout modes

### Phase C: Connectors

Add visual connectors between placed items:
- SVG arrows/lines drawn between card positions
- Animate connector drawing in as cards are placed
- Support configurable styles (arrow, dashed, chevron, curved)

### Phase D: Interaction Patterns

Add drag-to-slots as the primary interaction:
- Separate source area (card tray) from target area (track with slots)
- Slot highlighting on drag-near
- Card flies from tray to slot on drop
- Slot-swap when dragging to an occupied slot

Add click-to-place as mobile-friendly alternative.

### Phase E: Advanced Layouts

- Circular/cyclic layout for life cycles and repeating processes
- Insert-between mode for Timeline-game-style assessment
- Progressive reveal mode (draw pile)
- Flowchart layout for branching sequences

---

## 8. Example Scenarios

### Scenario 1: Cell Division (Biology)
- **Layout**: Horizontal timeline
- **Card type**: image_and_text (microscope images of each phase)
- **Items**: Interphase, Prophase, Metaphase, Anaphase, Telophase, Cytokinesis
- **Connectors**: Arrows
- **Slots**: Labeled ("Phase 1", "Phase 2", ...)
- **Source**: Card tray below the track

### Scenario 2: Historical Events (History)
- **Layout**: Insert-between (Timeline game style)
- **Card type**: image_and_text (historical illustrations)
- **Items**: 6-8 events with dates hidden
- **Connectors**: Dashed arrows on a timeline
- **Slots**: Minimal insert indicators between existing cards
- **Source**: Card stack (progressive reveal)

### Scenario 3: Water Cycle (Earth Science)
- **Layout**: Circular
- **Card type**: icon_and_text
- **Items**: Evaporation, Condensation, Precipitation, Collection, Runoff
- **Connectors**: Curved arrows around the cycle
- **Slots**: Numbered positions on the circle
- **Source**: Scattered pool

### Scenario 4: Algorithm Steps (Computer Science)
- **Layout**: Vertical timeline / flowchart
- **Card type**: text_only
- **Items**: Steps of a sorting algorithm with distractors
- **Connectors**: Chevrons
- **Slots**: Outlined with "Step 1", "Step 2" labels
- **Source**: Sidebar column

### Scenario 5: Cooking Recipe (Life Skills)
- **Layout**: Horizontal timeline
- **Card type**: image_and_text (photos of each cooking step)
- **Items**: 5-7 steps in recipe order
- **Connectors**: Numbered circles
- **Slots**: Shadow silhouettes
- **Source**: Card tray

---

## 9. Key Design Principles

1. **Cards, not rows.** Every item should look like a distinct object you can pick up, not a line in a spreadsheet. Borders, shadows, images, and internal layout create the card-as-artifact feel.

2. **A track, not a container.** The sequence should exist on a visible path with direction, endpoints, and visual rhythm. The track is a persistent artifact that grows as items are placed.

3. **Connectors tell the story.** Lines or arrows between items reinforce that this is a sequence with flow and direction, not just a sorted set. Connectors should animate in to reward correct placement.

4. **Spatial affordance over list manipulation.** Moving a card from a source area to a slot on a track is fundamentally more game-like than reordering items in a list. The separation of "hand" and "board" creates the game metaphor.

5. **Configuration over hard-coding.** The same component should render a horizontal timeline with image cards and arrows for a biology sequence, or a circular layout with icons and curved paths for a life cycle, driven entirely by configuration.

6. **Keep it a test.** This is an assessment mechanic. The design should be engaging but not reveal answers. No "warm/cold" proximity indicators, no auto-correction during placement, no arrows pointing to correct slots. In test mode, feedback comes only after submission.

7. **Reasonable item counts.** The best sequencing games use 4-8 items. Beyond 10, cognitive load dominates and the interaction becomes tedious rather than engaging. If more steps are needed, split across multiple scenes/tasks.
