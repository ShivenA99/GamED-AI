# Compare & Contrast Games: Components, Assets & Interaction Research

**Date**: 2026-02-11
**Scope**: What NEW visual components, configurable assets, and interaction patterns make compare-and-contrast activities feel like real, engaging assessment games. Focused on testing whether students can identify similarities and differences WITHOUT revealing the categorization. Game-wide systems (scoring, hints, combos, post-game review) are out of scope.

---

## Table of Contents

1. [Reference Games & What They Do Right](#1-reference-games--what-they-do-right)
2. [Comparison Mode Taxonomy](#2-comparison-mode-taxonomy)
3. [Visual Components](#3-visual-components)
4. [Interaction Patterns](#4-interaction-patterns)
5. [Configurable Properties](#5-configurable-properties)
6. [Pipeline Data Model](#6-pipeline-data-model)
7. [Dual-Image Asset Pipeline](#7-dual-image-asset-pipeline)
8. [Animation & Game Feel](#8-animation--game-feel)
9. [Accessibility](#9-accessibility)
10. [Current Codebase Gap Analysis](#10-current-codebase-gap-analysis)

---

## 1. Reference Games & What They Do Right

### 1.1 Lab-Aids SGI Cell Simulation

The gold standard for educational compare-and-contrast assessment. The simulation (hosted at `labaids.s3.us-east-2.amazonaws.com/sgi-sims/cell/index.html`) has students build a typical animal cell and a typical plant cell by dragging 12 organelles and structures into position. Key design decisions:

- **Build-then-compare flow**: Students first construct each cell type by dragging organelles into the correct positions (learn mode). Then they drag organelle names onto a Venn diagram to categorize which are shared and which are unique (test mode). The construction phase provides context; the Venn phase tests understanding.
- **Error feedback on placement**: If you drag an organelle that does not belong to a cell type, you get an immediate error message. But the Venn diagram phase does NOT reveal answers until you click "Check Work" -- preserving assessment integrity.
- **Rollover information**: Hovering over any organelle shows its function description. This is the explore phase -- students can gather information before being tested.
- **Venn diagram as categorization UI**: The intersection region is a first-class drop target. Items that belong to both cells go in the overlap; items unique to one cell go in the appropriate circle. Items that belong to neither (if any) have no valid placement.
- **Check Work button**: Batch submission -- all placements are evaluated simultaneously. The count of correct placements is shown without revealing which specific ones are wrong, forcing students to re-examine their reasoning.

### 1.2 Ask A Biologist Cell Anatomy Viewer (ASU)

Interactive cell viewer at `askabiologist.asu.edu/games-sims/cell-viewer-game/play.html` that supports toggling between cell types:

- **Toggle buttons across cell types**: Buttons at the top let users switch between animal, plant, and bacteria cells. The same viewport shows different cell diagrams, enabling mental comparison. This is the simplest form of comparison UI -- toggle-and-remember.
- **Zoom capability**: A "Zoom In" button reveals detail-dense structures (e.g., chloroplast thylakoids, mitochondrial cristae) that are invisible at default zoom. Zoom is essential for compare-and-contrast when structures have subtle differences.
- **Inspect mode**: Clicking on any cell part in Inspect mode reveals a description. This is a guided exploration phase before assessment.
- **Game mode with timer**: After exploring, students switch to game mode where they race the clock to locate and identify parts. The exploration-then-test pattern is central to compare-and-contrast design.
- **Cross-cell comparison implicit**: By making switching instant and viewport-consistent, students naturally compare "where is the cell wall in the plant cell vs. what's in that same position in the animal cell?"

### 1.3 react-compare-slider (npm)

The most popular React library for before/after image comparison sliders. Key features relevant to educational compare-and-contrast:

- **Landscape and portrait orientation**: The slider can divide images vertically (left-right) or horizontally (top-bottom). For anatomical diagrams, vertical split is standard; for geological cross-sections or timeline comparisons, horizontal split may be more natural.
- **Any React component as content**: Not limited to images -- you can overlay SVG zones, annotations, or interactive elements on each side. This is critical for combining slider exploration with zone-based categorization.
- **Keyboard accessibility**: Built-in `keyboardIncrement` prop controls the percentage to move per arrow key press. Screen reader friendly with ARIA attributes.
- **Zero dependencies, tiny bundle**: Suitable for embedding in educational games without bloat.
- **onChange callback**: Fires with the current slider position percentage, enabling analytics (e.g., "student spent 80% of time examining the left diagram").
- **Custom handle component**: The slider handle can be styled or replaced entirely -- e.g., with a pulsing indicator that draws attention.

### 1.4 Legends of Learning: Plant vs. Animal Cells

A curated collection of educational games for cell comparison:

- **Multiple game formats for same content**: Some games use side-by-side labeling, others use Venn diagram categorization, others use quiz-based comparison. This validates the need for configurable comparison modes (slider, side-by-side, Venn, etc.) rather than a single hardcoded layout.
- **Build-to-compare**: One game has players choose organelles from a list and decide whether they fit in a plant or animal cell, building cells one organelle at a time. The act of construction forces comparison decisions.
- **Standards alignment**: Games are mapped to NGSS standards (LS1.A: Structure and Function), showing that compare-and-contrast is a first-class assessment target in science education.

### 1.5 Shodor Interactivate Venn Diagram Shape Sorter

Interactive sorting into overlapping Venn regions:

- **Overlap regions as first-class drop targets**: The intersection area between circles is a distinct droppable zone. A shape that is both "red" AND "has 4 sides" goes in the overlap, not either single circle.
- **Outside region**: Items that belong to NEITHER category go outside all circles. This tests exclusion reasoning -- a critical skill in compare-and-contrast ("this structure exists in neither cell type").
- **Rule discovery mode**: The computer sets secret sorting rules; the player must discover them by placing items and observing feedback. This inverts the standard assessment: instead of testing known categories, it tests the ability to INFER categories from observations.

### 1.6 Spot-the-Difference Genre

Classic puzzle format with educational potential:

- **Two nearly-identical images side by side**: Players tap/click on areas where they detect differences. The format is inherently engaging because it combines visual search with discovery satisfaction.
- **Circle/highlight on tap**: When a player identifies a difference, a circle or highlight appears confirming it. This provides immediate, localized feedback without revealing remaining differences.
- **Progress counter**: "Found 4 of 7 differences" maintains motivation and signals how much remains.
- **Anti-cheat click throttling**: In digital implementations, rapid random clicking is penalized (cooldown or score deduction), encouraging careful observation over guessing.
- **Educational adaptation**: Instead of arbitrary visual differences, the "differences" can be structural (cell wall present vs. absent), functional (photosynthesis vs. no photosynthesis), or proportional (large vacuole vs. small vacuole).

### 1.7 Histology Guide Virtual Microscopy

Interactive side-by-side tissue comparison:

- **Synchronized zoom and pan**: When you zoom into one tissue sample, the other sample zooms to the same region and magnification. This ensures the comparison is spatially aligned -- critical for anatomical comparisons.
- **Real-time zoom-and-pan**: Users can interactively explore large images, providing a sense of scale, proportion, and context that is impossible with static images.
- **Software-based virtual microscope**: Allows examination of large and small structures in the same specimen, mimicking real lab equipment.

---

## 2. Comparison Mode Taxonomy

The compare-and-contrast mechanic supports fundamentally different visual layouts and interaction models. Each mode changes how diagrams are presented and how categorization is performed.

### 2.1 Image Comparison Slider (`slider`)

The most engaging and interactive mode. Two images are overlaid and a draggable divider reveals one image on each side. The student explores by dragging the slider, then categorizes zones.

```
+---------------------------------------------------+
|                                                     |
|    Diagram A        |||||     Diagram B              |
|    (left half)      |||||     (right half)           |
|                     |||||                            |
|    [zone: cell wall]|||||     [no cell wall here]    |
|                     |||||                            |
|    [chloroplast]    |||||     [no chloroplast]       |
|                     |||||                            |
+---------------------------------------------------+
                      ^^^
                   drag handle
```

**When to use**: When two diagrams share the same spatial layout (e.g., plant cell vs. animal cell where organelles are in similar positions). The slider lets students see exactly what changes between the two.

**Implementation**: Use `react-compare-slider` as the base component. Overlay SVG zone indicators on each side. After exploration, switch to categorization mode where clicking a zone prompts a category selection.

**Assessment value**: Tests spatial awareness and structural correspondence. The student must mentally map "this region in Diagram A corresponds to this region in Diagram B."

### 2.2 Side-by-Side with Zone Categorization (`side_by_side`)

The default and most straightforward mode. Two diagrams are shown side by side. Each diagram has labeled zones. The student clicks zones and assigns categories.

```
+--------------------+    +--------------------+
|   Diagram A        |    |   Diagram B        |
|   "Plant Cell"     |    |   "Animal Cell"    |
|                    |    |                    |
|   [zone: wall]     |    |   [zone: membrane] |
|   [zone: chloro]   |    |   [zone: lysosome] |
|   [zone: nucleus]  |    |   [zone: nucleus]  |
|   [zone: vacuole]  |    |   [zone: vacuole]  |
+--------------------+    +--------------------+

Category buttons: [Similar] [Different] [Unique to A] [Unique to B]
```

**When to use**: When the two diagrams have different spatial layouts or different numbers of zones. Good for comparing systems that look visually different but have corresponding parts (e.g., frog heart vs. human heart).

**Assessment value**: Tests recognition and classification. The student must evaluate each structure and decide which category it belongs to.

### 2.3 Overlay / Toggle with Transparency Slider (`overlay`)

Both diagrams are layered on top of each other. A transparency slider (or toggle button) controls which diagram is visible. At 0% the student sees only Diagram A; at 100% only Diagram B; at 50% both are blended.

```
+---------------------------------------------------+
|                                                     |
|            [blended/overlaid view]                  |
|                                                     |
|   Diagram A elements shown in BLUE                  |
|   Diagram B elements shown in RED                   |
|   Shared elements shown in PURPLE                   |
|                                                     |
+---------------------------------------------------+

Transparency: [A ====|============ B]
              0%    current=30%     100%
```

**When to use**: When structures occupy the same spatial positions and the student needs to see how one structure "replaces" or "corresponds to" another. Excellent for before/after comparisons (e.g., healthy tissue vs. diseased tissue, embryonic stage 1 vs. stage 2).

**Implementation**: Use CSS `opacity` and `mix-blend-mode` on two stacked `<img>` elements. Color-code zone overlays by diagram source. A horizontal slider controls the opacity ratio.

**Assessment value**: Tests the ability to identify structural correspondence. When zones overlap spatially, the student must recognize "these are the same structure" vs. "these are different structures occupying the same space."

### 2.4 Venn Diagram Categorization (`venn`)

No side-by-side images. Instead, a Venn diagram with two (or three) overlapping circles is the primary UI. Labels/items are dragged from a pool into the appropriate region of the Venn diagram.

```
         +-------------+
        /   Only in A    \
       /                   \
      |       +------+------+------+
      |       |  In  |  A   |      |
       \      | Both | & B  |     /
        \     +------+------+    /
         +------|    Only in B  |
                +---------------+

Item pool: [cell wall] [nucleus] [chloroplast] [lysosome] [mitochondria]
```

**When to use**: When the comparison is conceptual rather than spatial. Good when both diagrams have already been explored (e.g., after a slider phase) and the student needs to synthesize their observations. Also effective as a standalone mode when the subject matter is text-based rather than image-based.

**Implementation**: Render Venn circles using SVG `<circle>` elements with `clip-path` for the intersection region. Use `dnd-kit` or native drag-and-drop for item placement. Drop target detection uses point-in-circle math with intersection logic.

**Assessment value**: Tests conceptual synthesis and classification. The student must recall information from both diagrams and make categorical judgments. The overlap region specifically tests understanding of shared features.

### 2.5 Spot-the-Difference (`spot_difference`)

Two nearly-identical images side by side. The student clicks/taps on areas where they detect differences. Each correctly identified difference is circled/highlighted.

```
+--------------------+    +--------------------+
|   Image A          |    |   Image B          |
|                    |    |                    |
|   [same]           |    |   [same]           |
|   [same]           |    |   [DIFFERENT!] (o) |
|   [same]           |    |   [same]           |
|   [DIFFERENT!] (o) |    |   [same]           |
+--------------------+    +--------------------+

Found: 2 / 5 differences       [Submit]
```

**When to use**: When the comparison is visual and spatial, and the differences are subtle. Good for trained observation (e.g., histology slides, geological strata, circuit diagrams). The student must carefully scan and compare rather than categorize.

**Implementation**: Define "difference zones" as rectangular or circular regions on each image. When the student clicks within a difference zone on either image, both the corresponding zones on Image A and Image B are highlighted. Clicks outside any difference zone are counted as misses (optional penalty).

**Assessment value**: Tests perceptual discrimination and attention to detail. Unlike categorization modes, this tests WHETHER the student can identify differences, not HOW they categorize them.

---

## 3. Visual Components

### 3.1 Image Comparison Slider

The most visually engaging component. A draggable divider splits two overlaid images.

**Subcomponents**:
- **SliderHandle**: Vertical bar with grip indicators (dots or lines). Should pulse or glow to invite interaction. Custom styling via `handleComponent` prop.
- **ClipMask**: CSS `clip-path` or `overflow: hidden` container that reveals only the appropriate portion of each image.
- **PositionIndicator**: Small label showing "A" and "B" on each side of the slider, or showing the diagram names.
- **ZoneOverlays**: SVG polygons or rectangles rendered on top of each image, clipped to the visible region. Zones on Diagram A are only visible when the slider reveals that region; zones on Diagram B likewise.

**Configuration props**:
| Prop | Type | Description |
|------|------|-------------|
| `orientation` | `'landscape' \| 'portrait'` | Horizontal or vertical split |
| `initialPosition` | `number` (0-100) | Starting slider position (default: 50) |
| `boundsPadding` | `number` | Pixel padding limiting slider range |
| `onlyHandleInteraction` | `boolean` | Only move via handle drag, not click |
| `showZoneOverlays` | `boolean` | Whether zone indicators appear during exploration |

### 3.2 Side-by-Side Diagram Panels

Two diagram images displayed in a responsive grid. Each panel contains zone overlays.

**Subcomponents**:
- **DiagramPanel**: Container for one image + its zones. Includes a header showing the diagram name.
- **ZoneOverlay**: Positioned absolutely over the image using percentage coordinates. Shows label text and category color after categorization.
- **ZonePairingLines**: SVG lines connecting corresponding zones across the two panels. When `zone_pairing_display` is enabled, dashed lines connect "nucleus in A" to "nucleus in B" to show structural correspondence.
- **CategoryBadge**: Small colored pill on each zone showing its assigned category (green = similar, red = different, blue = unique to A, purple = unique to B).

**Zone pairing line implementation**:
```
+--------------------+       +--------------------+
|   [nucleus] -------|-------|----> [nucleus]      |
|   [chloroplast]    |       |                     |
|   [cell wall] -----|-------|----> [cell membrane] |
|   [vacuole] -------|-------|----> [vacuole]      |
+--------------------+       +--------------------+
```
Lines are rendered in an SVG overlay that spans both panels. Line endpoints are computed from zone center coordinates. Lines are styled with:
- Solid green for confirmed "similar" pairings
- Dashed red for confirmed "different" pairings
- Dotted gray for unconfirmed/pending pairings
- No line for "unique" zones (they have no counterpart)

### 3.3 Overlay / Transparency Controller

Two images stacked with adjustable transparency.

**Subcomponents**:
- **TransparencySlider**: Horizontal range input controlling the top layer's opacity (0.0 to 1.0). Styled as a gradient bar from Diagram A's color to Diagram B's color.
- **ToggleButton**: Quick-switch button to jump between 100% A, 50/50, and 100% B. Provides discrete checkpoints for users who find continuous sliding imprecise.
- **ColorCodedZones**: Zones from Diagram A are tinted blue; zones from Diagram B are tinted red. When both are visible at partial transparency, overlapping zones appear purple, visually suggesting "shared."
- **DiagramLabel**: Floating label in the corner showing which diagram(s) are currently visible and at what opacity.

### 3.4 Venn Diagram Categorization UI

Interactive Venn diagram with draggable items.

**Subcomponents**:
- **VennCircles**: Two (or three) overlapping SVG circles with labeled headers ("Diagram A Only", "Both", "Diagram B Only").
- **IntersectionRegion**: The overlap area computed via SVG `clipPath` combining both circles. This is a first-class drop target with its own visual styling (lighter shade, hatched pattern).
- **OutsideRegion**: The area outside all circles. Items that belong to neither category are dropped here. This tests exclusion reasoning.
- **DraggableItem**: Each item (zone label) is a draggable chip/card. Shows the label text and optionally a small thumbnail of the zone from its source diagram.
- **ItemPool**: Container holding items not yet placed. Items are initially shuffled to prevent ordering bias.
- **PlacedItemStack**: Within each Venn region, placed items stack vertically with slight overlap to save space. Items can be re-dragged to change placement.

### 3.5 Spot-the-Difference Highlight System

Visual feedback for identified differences.

**Subcomponents**:
- **DifferenceCircle**: Animated circle that appears when a difference is correctly identified. Draws in with a growing-ring animation. Appears on BOTH images simultaneously to show the correspondence.
- **MissIndicator**: Brief red flash or X mark when the student clicks outside any difference zone. Fades after 500ms.
- **ProgressPips**: Row of small circles at the bottom (one per difference). Filled pips = found, empty = remaining. Does not reveal WHERE remaining differences are.
- **MagnifyingGlass** (optional): Cursor changes to a magnifying glass icon in spot-the-difference mode to reinforce the "searching" metaphor.

### 3.6 Synchronized Zoom Controller

Dual-panel zoom and pan with synchronized viewports.

**Subcomponents**:
- **ZoomControls**: +/- buttons and a zoom level indicator (e.g., "2.5x"). Can also zoom via scroll wheel or pinch gesture.
- **MiniMap**: Small overview thumbnail in the corner showing the current viewport position within the full image. Essential when zoomed in to maintain spatial orientation.
- **SyncLock**: Toggle button to enable/disable synchronized panning. When locked, panning one panel pans the other identically. When unlocked, panels pan independently (useful for comparing non-corresponding regions).
- **ViewportFrame**: In the minimap, a small rectangle shows the current visible area.

**Implementation**: Use `react-zoom-pan-pinch` (TransformWrapper + TransformComponent) for each panel. Share zoom/pan state between panels via a parent component that listens to `onTransformed` events from one panel and calls `setTransform` on the other.

### 3.7 Category Selection Panel

Shared across all comparison modes. Appears when a zone is selected.

**Subcomponents**:
- **CategoryButton**: Color-coded button for each category. The standard categories are:
  - **Similar in Both** (green): Structure exists in both diagrams with equivalent function
  - **Different** (red/orange): Structure exists in both but differs in form, size, or function
  - **Unique to A** (blue): Structure only exists in Diagram A
  - **Unique to B** (purple): Structure only exists in Diagram B
- **CategoryLegend**: Persistent legend showing all categories with their colors. Placed below or beside the diagrams.
- **SelectedZoneHighlight**: When a zone is selected for categorization, it gets a pulsing ring to indicate it is the active zone.

### 3.8 Exploration Phase Overlay

Pre-categorization exploration interface.

**Subcomponents**:
- **ExplorePrompt**: Banner at the top saying "Explore both diagrams before categorizing. Click zones to learn about each structure." Disappears when the student transitions to categorize phase.
- **InfoTooltip**: Click/hover on a zone during explore phase to see its description. In test mode, descriptions are hidden (zones only show labels). In learn mode, descriptions are shown to support discovery.
- **ExploreTimer** (optional): Visual indicator showing how much exploration time has elapsed. Not a countdown -- simply a "you have been exploring for 45 seconds" indicator to encourage thorough examination before committing to categorization.
- **ReadyButton**: "I'm ready to categorize" button that transitions from explore phase to categorize phase. Prevents premature categorization.

---

## 4. Interaction Patterns

### 4.1 Explore-Then-Categorize (Two-Phase Pattern)

The most pedagogically sound pattern for compare-and-contrast assessment.

**Phase 1 -- Explore**: The student interacts with the slider, toggles between diagrams, zooms into details, and clicks zones to learn about structures. No categorization is possible during this phase. The explore phase ensures the student has gathered information before making judgments.

**Phase 2 -- Categorize**: The explore tools remain available, but categorization buttons appear. The student clicks a zone, then selects a category. Progress is tracked ("5 of 12 categorized"). When all zones are categorized, the student can submit.

**Transition**: A prominent "Start Categorizing" button or automatic transition after a minimum explore time (configurable). The transition can be animated (e.g., category buttons slide in from the bottom).

**Assessment value**: Separating exploration from categorization prevents snap judgments and rewards thorough investigation.

### 4.2 Direct Categorization (Single-Phase)

For simpler comparisons or when students are already familiar with the subject matter.

The student sees both diagrams immediately with category buttons available. They can click any zone on either diagram and assign a category. No enforced explore phase.

**When to use**: Time-limited assessments, review activities where students already have domain knowledge, or when the diagrams are simple enough that exploration is unnecessary.

### 4.3 Spot-the-Difference Variant

The student's task is to FIND differences, not categorize them.

**Interaction**: Click/tap on areas of either diagram where you detect a difference from the other. The game confirms or denies each click. Students must find all N differences to complete the task.

**Scoring signals**:
- Correct click: difference circle appears on both images
- Incorrect click: brief miss indicator, optional penalty
- Progress: "Found 4 of 7 differences"

**When to use**: When the assessment goal is perceptual discrimination rather than conceptual categorization. Good for visual subjects (histology, geography, engineering diagrams).

### 4.4 Zone-by-Zone Guided Comparison

The game presents zones one at a time and asks the student to categorize each.

**Interaction**: A highlighted zone appears on one diagram. The student must find its counterpart (if any) on the other diagram and categorize the relationship. If the zone is unique, the student selects "Unique to A/B."

**Subinteraction**: When the student clicks "Find Match," the other diagram highlights potential matches (zones glow). The student clicks the matching zone or clicks "No Match."

**When to use**: For scaffolded assessment where students need guidance. Good for younger students or complex diagrams with many zones.

### 4.5 Semantic Zone Pairing

Before categorization, the student draws connections between corresponding zones.

**Interaction**: The student clicks a zone on Diagram A, then clicks the corresponding zone on Diagram B to create a pairing line. Unpaired zones are implicitly "unique." After all pairings are established, the student categorizes each pair as "similar" or "different."

**Visual**: Lines appear connecting paired zones across the two diagrams. The student can delete and re-draw pairings.

**Assessment value**: Tests structural correspondence identification as a separate skill from categorization. The student must first recognize WHICH structures correspond before deciding WHETHER they are similar or different.

---

## 5. Configurable Properties

### 5.1 Core Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `comparison_mode` | `'slider' \| 'side_by_side' \| 'overlay' \| 'venn' \| 'spot_difference'` | `'side_by_side'` | Primary visual layout for the comparison |
| `category_types` | `string[]` | `['similar', 'different', 'unique_a', 'unique_b']` | Available categories for zone classification. Can be customized (e.g., `['shared_structure', 'modified_structure', 'absent']`) |
| `category_labels` | `Record<string, string>` | `{similar: 'Similar in Both', ...}` | Display labels for each category |
| `category_colors` | `Record<string, string>` | `{similar: '#22c55e', ...}` | Color assignments for each category |
| `exploration_enabled` | `boolean` | `true` | Whether explore phase precedes categorization |
| `min_explore_time_seconds` | `number` | `0` | Minimum time in explore phase before categorize button appears |
| `zone_pairing_display` | `boolean` | `false` | Show lines connecting corresponding zones |
| `zone_pairing_mode` | `'auto' \| 'manual' \| 'none'` | `'auto'` | Whether zone pairings are pre-computed or student-drawn |

### 5.2 Slider-Specific Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `slider_orientation` | `'landscape' \| 'portrait'` | `'landscape'` | Horizontal or vertical slider |
| `slider_initial_position` | `number` | `50` | Starting slider position (0-100) |
| `slider_show_zones_during_explore` | `boolean` | `true` | Whether zone overlays are visible during slider exploration |
| `slider_handle_style` | `'bar' \| 'circle' \| 'arrows'` | `'bar'` | Visual style of the slider handle |

### 5.3 Overlay-Specific Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `overlay_initial_opacity` | `number` | `0.5` | Starting opacity of the top layer |
| `overlay_color_coding` | `boolean` | `true` | Color-code zones by source diagram |
| `overlay_toggle_steps` | `number[]` | `[0, 50, 100]` | Quick-toggle positions for the transparency slider |
| `overlay_blend_mode` | `string` | `'normal'` | CSS blend mode for overlaid images |

### 5.4 Venn-Specific Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `venn_circle_count` | `2 \| 3` | `2` | Number of Venn circles (3 for triple comparison) |
| `venn_show_outside` | `boolean` | `true` | Show "neither" region outside all circles |
| `venn_item_style` | `'chip' \| 'card' \| 'thumbnail'` | `'chip'` | Visual style of draggable items |
| `venn_show_thumbnails` | `boolean` | `false` | Show zone thumbnail on each item |
| `venn_shuffle_items` | `boolean` | `true` | Randomize item order in the pool |

### 5.5 Spot-the-Difference Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `spot_diff_count` | `number` | `5` | Number of differences to find |
| `spot_diff_penalty_on_miss` | `boolean` | `false` | Whether incorrect clicks incur a penalty |
| `spot_diff_highlight_style` | `'circle' \| 'glow' \| 'outline'` | `'circle'` | Visual style for identified differences |
| `spot_diff_click_cooldown_ms` | `number` | `500` | Cooldown between clicks to prevent spam |

### 5.6 Zoom Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `zoom_enabled` | `boolean` | `true` | Whether zoom/pan is available |
| `zoom_max_scale` | `number` | `4` | Maximum zoom level |
| `zoom_sync_panels` | `boolean` | `true` | Synchronized zoom/pan across panels |
| `zoom_show_minimap` | `boolean` | `false` | Show minimap for spatial orientation |

### 5.7 Zone Pairing Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `zone_pairings` | `Array<{zone_a_id, zone_b_id}>` | `[]` | Pre-defined zone correspondences |
| `pairing_line_style` | `'solid' \| 'dashed' \| 'dotted'` | `'dashed'` | Line style for pairing connections |
| `pairing_line_color_by_category` | `boolean` | `true` | Color lines based on assigned category |
| `show_unpaired_indicator` | `boolean` | `true` | Mark zones that have no pair |

---

## 6. Pipeline Data Model

### 6.1 Backend Schema: `CompareDesign` (Enhanced)

The current `CompareDesign` in `game_design_v3.py` is minimal (only `expected_categories`, `highlight_matching`, `instruction_text`). It must be expanded to support the full range of comparison modes:

```python
class CompareDesign(BaseModel):
    """compare_contrast mechanic config."""
    model_config = ConfigDict(extra="allow")

    # --- Core ---
    comparison_mode: str = "side_by_side"  # slider, side_by_side, overlay, venn, spot_difference
    expected_categories: Dict[str, str] = Field(default_factory=dict)
    # zone_id -> similar | different | unique_a | unique_b
    instruction_text: Optional[str] = None

    # --- Category customization ---
    category_types: List[str] = Field(
        default_factory=lambda: ["similar", "different", "unique_a", "unique_b"]
    )
    category_labels: Optional[Dict[str, str]] = None
    category_colors: Optional[Dict[str, str]] = None

    # --- Exploration ---
    exploration_enabled: bool = True
    min_explore_time_seconds: int = 0

    # --- Zone pairing ---
    zone_pairings: List[Dict[str, str]] = Field(default_factory=list)
    # [{zone_a_id: "...", zone_b_id: "..."}]
    zone_pairing_display: bool = False
    zone_pairing_mode: str = "auto"  # auto, manual, none

    # --- Zoom ---
    zoom_enabled: bool = True
    zoom_sync_panels: bool = True

    # --- Mode-specific ---
    slider_orientation: str = "landscape"
    slider_initial_position: int = 50
    overlay_initial_opacity: float = 0.5
    overlay_color_coding: bool = True
    venn_circle_count: int = 2
    venn_show_outside: bool = True
    spot_diff_count: Optional[int] = None
    spot_diff_penalty_on_miss: bool = False

    # --- Spot-the-difference zones ---
    difference_zones: List[Dict[str, Any]] = Field(default_factory=list)
    # [{zone_a_id, zone_b_id, description}]
```

### 6.2 Backend Schema: `ComparisonVisualSpec` (Enhanced)

The current `ComparisonVisualSpec` must carry enough information for the image pipeline to generate TWO matched diagrams:

```python
class ComparisonVisualSpec(BaseModel):
    """For compare_contrast mode -- two separate images."""
    model_config = ConfigDict(extra="allow")

    diagram_a_description: str = ""
    diagram_a_required_elements: List[str] = Field(default_factory=list)
    diagram_a_title: str = ""

    diagram_b_description: str = ""
    diagram_b_required_elements: List[str] = Field(default_factory=list)
    diagram_b_title: str = ""

    # Shared elements (exist in both diagrams)
    shared_elements: List[str] = Field(default_factory=list)

    # Style constraints for matched generation
    style_consistency: str = "matched"
    # matched: same art style, scale, orientation
    # independent: no style constraints
    spatial_alignment: str = "aligned"
    # aligned: corresponding structures in similar positions
    # free: no spatial constraints
```

### 6.3 Frontend Schema: `CompareConfig` (Enhanced)

The current frontend `CompareConfig` only has `diagramA`, `diagramB`, `expectedCategories`, `highlightMatching`, and `instructions`. It must be expanded:

```typescript
export interface CompareConfig {
  // --- Diagrams ---
  diagramA: CompareDiagram;
  diagramB: CompareDiagram;

  // --- Core ---
  comparisonMode: 'slider' | 'side_by_side' | 'overlay' | 'venn' | 'spot_difference';
  expectedCategories: Record<string, 'similar' | 'different' | 'unique_a' | 'unique_b'>;
  instructions?: string;

  // --- Categories ---
  categoryTypes?: string[];
  categoryLabels?: Record<string, string>;
  categoryColors?: Record<string, string>;

  // --- Exploration ---
  explorationEnabled?: boolean;
  minExploreTimeSeconds?: number;

  // --- Zone pairing ---
  zonePairings?: Array<{ zoneAId: string; zoneBId: string }>;
  zonePairingDisplay?: boolean;
  zonePairingMode?: 'auto' | 'manual' | 'none';

  // --- Zoom ---
  zoomEnabled?: boolean;
  zoomSyncPanels?: boolean;
  zoomMaxScale?: number;
  zoomShowMinimap?: boolean;

  // --- Mode-specific ---
  sliderOrientation?: 'landscape' | 'portrait';
  sliderInitialPosition?: number;
  overlayInitialOpacity?: number;
  overlayColorCoding?: boolean;
  vennCircleCount?: 2 | 3;
  vennShowOutside?: boolean;
  vennItemStyle?: 'chip' | 'card' | 'thumbnail';
  spotDiffCount?: number;
  spotDiffPenaltyOnMiss?: boolean;
  spotDiffHighlightStyle?: 'circle' | 'glow' | 'outline';

  // --- Spot-the-difference zones ---
  differenceZones?: Array<{ zoneAId: string; zoneBId: string; description?: string }>;
}

export interface CompareDiagram {
  id: string;
  name: string;
  imageUrl: string;
  zones: Array<{
    id: string;
    label: string;
    x: number;      // percentage
    y: number;      // percentage
    width: number;   // percentage
    height: number;  // percentage
    description?: string;  // shown during explore phase (learn mode only)
  }>;
}
```

### 6.4 Blueprint Output Structure

The blueprint generator must produce a compare-specific output section:

```json
{
  "compareConfig": {
    "comparisonMode": "slider",
    "diagramA": {
      "id": "plant_cell",
      "name": "Plant Cell",
      "imageUrl": "/assets/plant_cell_clean.png",
      "zones": [
        { "id": "za_wall", "label": "Cell Wall", "x": 5, "y": 10, "width": 90, "height": 5 },
        { "id": "za_chloro", "label": "Chloroplast", "x": 30, "y": 40, "width": 15, "height": 10 },
        { "id": "za_nucleus", "label": "Nucleus", "x": 45, "y": 45, "width": 20, "height": 20 }
      ]
    },
    "diagramB": {
      "id": "animal_cell",
      "name": "Animal Cell",
      "imageUrl": "/assets/animal_cell_clean.png",
      "zones": [
        { "id": "zb_membrane", "label": "Cell Membrane", "x": 5, "y": 10, "width": 90, "height": 5 },
        { "id": "zb_lysosome", "label": "Lysosome", "x": 60, "y": 30, "width": 10, "height": 10 },
        { "id": "zb_nucleus", "label": "Nucleus", "x": 45, "y": 45, "width": 20, "height": 20 }
      ]
    },
    "expectedCategories": {
      "za_wall": "unique_a",
      "za_chloro": "unique_a",
      "za_nucleus": "similar",
      "zb_membrane": "different",
      "zb_lysosome": "unique_b",
      "zb_nucleus": "similar"
    },
    "zonePairings": [
      { "zoneAId": "za_wall", "zoneBId": "zb_membrane" },
      { "zoneAId": "za_nucleus", "zoneBId": "zb_nucleus" }
    ],
    "explorationEnabled": true,
    "minExploreTimeSeconds": 30,
    "zoomEnabled": true,
    "zoomSyncPanels": true
  }
}
```

---

## 7. Dual-Image Asset Pipeline

This is the most critical and novel aspect of compare-and-contrast. Every other mechanic operates on a single diagram image. Compare-and-contrast requires TWO matched images with zones on BOTH.

### 7.1 Pipeline Flow

```
Question: "Compare plant and animal cells"
                |
                v
     +---------------------+
     | Game Designer (V3)   |  Produces ComparisonVisualSpec:
     |                     |  - diagram_a_description: "Plant cell cross-section"
     |                     |  - diagram_b_description: "Animal cell cross-section"
     |                     |  - shared_elements: ["nucleus", "mitochondria", "ER", "ribosomes"]
     |                     |  - diagram_a_required_elements: ["cell wall", "chloroplast", "large vacuole"]
     |                     |  - diagram_b_required_elements: ["lysosome", "centrioles", "small vacuoles"]
     +---------------------+
                |
                v
     +---------------------+
     | Scene Architect (V3) |  Emits TWO image search/generation requests:
     |                     |  - image_query_a: "clean educational plant cell cross-section diagram..."
     |                     |  - image_query_b: "clean educational animal cell cross-section diagram..."
     |                     |  - style_constraint: "matched style, same scale, same orientation"
     +---------------------+
                |
         +------+------+
         |             |
         v             v
   +-----------+  +-----------+
   | Image     |  | Image     |   Two parallel image retrievals/generations
   | Pipeline  |  | Pipeline  |   (search, classify, inpaint, SAM zone detection)
   | (Diag A)  |  | (Diag B)  |
   +-----------+  +-----------+
         |             |
         v             v
   +-----------+  +-----------+
   | Zone      |  | Zone      |   Zone detection runs independently on each image
   | Detection |  | Detection |
   | (Diag A)  |  | (Diag B)  |
   +-----------+  +-----------+
         |             |
         +------+------+
                |
                v
     +---------------------+
     | Zone Pairing Agent   |  NEW: Matches zones across the two images
     |                     |  Input: zones_a, zones_b, shared_elements, expected_categories
     |                     |  Output: zone_pairings [{zone_a_id, zone_b_id, relationship}]
     +---------------------+
                |
                v
     +---------------------+
     | Blueprint Assembler  |  Combines both diagrams + zones + pairings
     |                     |  into compareConfig
     +---------------------+
```

### 7.2 Dual Image Search/Generation Strategy

The key challenge is producing two images that are **stylistically consistent** and **structurally complementary**.

**Strategy 1: Search for matching pair**
- Search for "plant cell diagram" and "animal cell diagram" independently.
- Apply a style-matching filter: compare image dimensions, color palette, line style, and background. Score candidate pairs by visual similarity.
- Risk: hard to find perfectly matched educational diagrams in the wild.

**Strategy 2: Search one, generate the other**
- Search for the best available diagram for Diagram A.
- Use the found image as a style reference to generate Diagram B using image generation (e.g., DALL-E, Stable Diffusion with img2img).
- Prompt: "Generate a [Diagram B description] in the same art style, scale, and color palette as this reference image."
- Risk: generated image may not match quality of searched image.

**Strategy 3: Generate both**
- Generate both diagrams using the same prompt template with only the subject varying.
- Prompt template: "Clean educational cross-section diagram of a {subject}, neutral white background, no labels, consistent line weight, pastel colors for organelles."
- Generate Diagram A and Diagram B with the same seed/style parameters.
- Advantage: guaranteed style consistency.
- Risk: AI-generated diagrams may have anatomical inaccuracies.

**Strategy 4: Single source with variants** (for spot-the-difference)
- Start with one image.
- Apply targeted modifications to create the "different" version (e.g., remove cell wall, change vacuole size, add/remove structures).
- This ensures the images are nearly identical except for specific, controlled differences.
- Implementation: Use inpainting to modify specific zones.

### 7.3 Zone Detection Coordination

After generating/retrieving both images, zone detection must run on each independently. However, the results need to be coordinated:

1. **Run zone detection on Diagram A** -> produces `zones_a[]`
2. **Run zone detection on Diagram B** -> produces `zones_b[]`
3. **Zone pairing step**: Match zones across diagrams by:
   - Label text similarity (fuzzy matching: "cell wall" in A matches "cell wall" in B)
   - Spatial position similarity (nucleus at center in A likely corresponds to nucleus at center in B)
   - Domain knowledge from `shared_elements` list (the game designer already identified which elements are shared)
4. **Generate `zone_pairings`**: Each pairing is `{zone_a_id, zone_b_id}` or `null` for unique zones.
5. **Generate `expected_categories`**: Based on the pairing and the domain knowledge:
   - Paired zones with same label -> "similar"
   - Paired zones with different labels -> "different"
   - Unpaired zones -> "unique_a" or "unique_b"

### 7.4 State Field Requirements

New state fields needed in `AgentState`:

| Field | Type | Purpose |
|-------|------|---------|
| `diagram_image_b` | `str` | Base64 or URL of second diagram image |
| `diagram_image_b_url` | `str` | URL of second diagram image |
| `zones_b` | `list[dict]` | Zone detection results for Diagram B |
| `zone_pairings` | `list[dict]` | Cross-diagram zone correspondences |
| `comparison_visual_spec` | `dict` | The ComparisonVisualSpec from game designer |
| `is_comparison_mode` | `bool` | Flag to trigger dual-image pipeline |

### 7.5 Graph Wiring for Dual-Image Pipeline

The dual-image pipeline introduces a parallelization opportunity. After the game designer determines this is a compare_contrast mechanic:

1. **Fork**: Two parallel branches for image retrieval + zone detection (one per diagram).
2. **Join**: Both branches complete before the zone pairing agent runs.
3. **Continue**: Blueprint assembler consumes both sets of zones + pairings.

In LangGraph, this is implemented using the `Send` API for map-reduce:

```python
def route_image_pipeline(state):
    if state.get("is_comparison_mode"):
        return [
            Send("image_pipeline_a", {**state, "_target_diagram": "A"}),
            Send("image_pipeline_b", {**state, "_target_diagram": "B"}),
        ]
    else:
        return "image_pipeline"  # single-image path
```

---

## 8. Animation & Game Feel

### 8.1 Slider Discovery Moment

When the student first drags the slider and reveals a structural difference (e.g., cell wall disappears, revealing just a membrane), a subtle "discovery" animation plays:

- The differing zone briefly pulses with a golden glow
- A small sparkle particle effect at the zone boundary
- A soft "aha" sound effect (optional, respecting audio preferences)

This rewards exploration and draws attention to key differences without explicitly categorizing them.

### 8.2 Categorization Feedback

When a zone is categorized:
- The zone smoothly transitions to its category color (green/red/blue/purple)
- A small category icon (checkmark for similar, X for different, arrow for unique) fades in
- If zone pairing lines are enabled, the line connecting paired zones changes color to match the category

### 8.3 Venn Diagram Drop Animation

When an item is dropped into a Venn region:
- The item chip shrinks slightly and settles into position with a spring animation
- The Venn region briefly flashes to confirm the drop
- Items already in the region shift to make room (automatic layout)
- If dropped in the intersection, both circles briefly pulse to reinforce the "shared" concept

### 8.4 Spot-the-Difference Discovery

When a difference is correctly found:
- A circle draws itself around the difference zone on BOTH images simultaneously (animated stroke)
- The progress pip fills in with a satisfying "pop" animation
- A brief checkmark appears and fades
- Remaining undiscovered areas do NOT change -- no hints about remaining differences

### 8.5 Zoom Transitions

When zooming in:
- Smooth CSS transform with ease-out easing
- Zone labels scale inversely (stay readable at all zoom levels)
- If synchronized, both panels zoom simultaneously with a slight stagger (50ms delay on the follower panel creates a satisfying "linked" feeling)

### 8.6 Explore-to-Categorize Transition

When transitioning from explore phase to categorize phase:
- Category buttons slide up from the bottom with a staggered entrance (each button 50ms after the previous)
- The explore prompt fades out
- Zone overlays become slightly more prominent (increased border width, added shadow)
- A brief instruction toast appears: "Click any zone to start categorizing"

---

## 9. Accessibility

### 9.1 Keyboard Navigation

| Action | Keys | Description |
|--------|------|-------------|
| Move slider | Left/Right arrows | Move comparison slider by `keyboardIncrement` (default 5%) |
| Select zone | Tab | Cycle through zones in tab order |
| Categorize zone | 1-4 keys | Assign category to selected zone (1=similar, 2=different, 3=unique A, 4=unique B) |
| Toggle diagram | Space | In overlay mode, toggle between Diagram A and Diagram B |
| Zoom in/out | +/- keys | Adjust zoom level |
| Pan | Arrow keys (when zoomed) | Pan viewport |
| Submit | Enter | Submit categorizations |

### 9.2 Screen Reader Support

- Each zone has an `aria-label` describing its name and current category status: "Nucleus, Diagram A, categorized as Similar in Both"
- The slider has `role="slider"` with `aria-valuemin`, `aria-valuemax`, and `aria-valuenow` for current position
- Category buttons have `aria-pressed` state
- Progress is announced via `aria-live="polite"` region: "5 of 12 zones categorized"
- Diagram switching announced: "Now viewing Diagram B: Animal Cell"

### 9.3 Color-Blind Support

- Categories use both color AND icon/pattern differentiation:
  - Similar: green + checkmark icon + solid fill
  - Different: orange + X icon + diagonal stripes
  - Unique to A: blue + left-arrow icon + dots pattern
  - Unique to B: purple + right-arrow icon + crosshatch pattern
- Pairing lines use dashes/dots in addition to colors
- High contrast mode option: black/white with heavy line weight

### 9.4 Motor Accessibility

- Slider handle has a large hit target (minimum 44x44px)
- Zone overlays have generous click targets (minimum 32x32px)
- Category selection via both click and keyboard shortcut
- No time pressure in default mode (spot-the-difference cooldown can be disabled)
- Drag-and-drop in Venn mode has keyboard alternative: select item with arrow keys, press 1/2/3 to place in region

---

## 10. Current Codebase Gap Analysis

### 10.1 What Exists

| Component | Location | Status |
|-----------|----------|--------|
| `CompareContrast.tsx` | `frontend/.../interactions/CompareContrast.tsx` | Basic side-by-side only. 301 lines. Click zone -> select category -> submit. No slider, overlay, Venn, or spot-the-difference. |
| `CompareConfig` (frontend) | `frontend/.../InteractiveDiagramGame/types.ts` L437-443 | Minimal: `diagramA`, `diagramB`, `expectedCategories`, `highlightMatching`, `instructions`. No comparison mode, no zoom, no pairing. |
| `CompareDiagram` (frontend) | `frontend/.../InteractiveDiagramGame/types.ts` L423-435 | Basic: `id`, `name`, `imageUrl`, `zones[]` with x/y/width/height. No description field on zones. |
| `CompareDesign` (backend) | `backend/app/agents/schemas/game_design_v3.py` L228-234 | Minimal: `expected_categories`, `highlight_matching`, `instruction_text`. No comparison mode or exploration settings. |
| `ComparisonVisualSpec` (backend) | `backend/app/agents/schemas/game_design_v3.py` L152-159 | Has `diagram_a/b_description` and `required_elements`. Missing `shared_elements`, `style_consistency`, `spatial_alignment`, titles. |
| `CompareConfig` (backend blueprint) | `backend/app/agents/schemas/interactive_diagram.py` L292-298 | Mirrors frontend: `diagramA`, `diagramB`, `expectedCategories`. |
| `CompareProgress` (Zustand) | `frontend/.../hooks/useInteractiveDiagramState.ts` | Defined in types but integration is partial (Fix 1.7h stub). |

### 10.2 What Is Missing

**Frontend Components (HIGH priority)**:
1. `ImageComparisonSlider` -- Slider mode component using `react-compare-slider` with zone overlays
2. `OverlayToggle` -- Transparency slider/toggle for overlay mode
3. `VennDiagramCategorizer` -- Drag-and-drop Venn diagram with intersection regions
4. `SpotTheDifference` -- Click-to-find differences mode
5. `ZonePairingLines` -- SVG overlay connecting corresponding zones across panels
6. `SynchronizedZoomPanels` -- Dual-panel zoom/pan using `react-zoom-pan-pinch`
7. `ExplorePhaseOverlay` -- Exploration UI with ready-to-categorize button
8. `ComparisonModeRouter` -- Component that routes to the correct sub-component based on `comparisonMode`
9. Zone `description` field on `CompareDiagram.zones` for explore-phase tooltips

**Backend Pipeline (CRITICAL)**:
1. Dual-image retrieval/generation -- The image pipeline currently handles exactly one image. Compare mode requires two.
2. `diagram_image_b` and `zones_b` state fields in `AgentState`
3. Zone pairing logic (could be a tool in scene_architect_v3 or a dedicated agent)
4. `ComparisonVisualSpec` expansion with `shared_elements`, titles, style constraints
5. `CompareDesign` expansion with `comparison_mode`, `zone_pairings`, exploration settings
6. Blueprint assembler logic to populate expanded `CompareConfig`
7. Graph wiring for parallel dual-image pipeline (Send API)

**Configuration & Data Model (MEDIUM)**:
1. Category customization (labels, colors, custom category types)
2. Spot-the-difference zone definitions (`difference_zones`)
3. Zoom/pan synchronization settings
4. Exploration phase timing configuration
5. Zone pairing display configuration

### 10.3 Dependency Map

```
react-compare-slider  -- needed for slider mode
react-zoom-pan-pinch  -- needed for synchronized zoom/pan
dnd-kit               -- already in project (needed for Venn drag-and-drop)
```

### 10.4 Implementation Priority

1. **Phase A**: Expand backend schemas (`CompareDesign`, `ComparisonVisualSpec`, `CompareConfig`) and add state fields
2. **Phase B**: Implement dual-image pipeline (image retrieval x2, zone detection x2, zone pairing)
3. **Phase C**: Build `ComparisonModeRouter` + `side_by_side` mode (enhance existing `CompareContrast.tsx`)
4. **Phase D**: Build `ImageComparisonSlider` mode (highest engagement value)
5. **Phase E**: Build `VennDiagramCategorizer` mode
6. **Phase F**: Build `OverlayToggle` and `SpotTheDifference` modes
7. **Phase G**: Add zone pairing lines, synchronized zoom, explore phase overlay
