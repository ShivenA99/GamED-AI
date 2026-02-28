# Sorting / Categorization Games: Components, Assets & Interaction Research

**Date**: 2026-02-11
**Scope**: What NEW visual components, configurable assets, and interaction patterns make sorting/categorization games feel like real, engaging assessment games. Focused on testing classification ability without giving away answers.

---

## Table of Contents

1. [Reference Games & What They Do Right](#1-reference-games--what-they-do-right)
2. [Sort Mode Taxonomy](#2-sort-mode-taxonomy)
3. [Visual Components](#3-visual-components)
4. [Interaction Patterns](#4-interaction-patterns)
5. [Configurable Properties](#5-configurable-properties)
6. [Pipeline Data Model](#6-pipeline-data-model)
7. [Animation & Game Feel](#7-animation--game-feel)
8. [Accessibility](#8-accessibility)
9. [Current Codebase Gap Analysis](#9-current-codebase-gap-analysis)

---

## 1. Reference Games & What They Do Right

### 1.1 BrainPOP Sortify

The gold standard for educational sorting assessment. Players sort 30 tiles into labeled bins across multiple rounds. The key design decisions that make it work:

- **Player-labeled bins**: Players choose their own category labels, not the game. This tests whether the student understands classification criteria, not just recognition. In assessment mode, pre-labeled bins test whether the student can apply given criteria.
- **Tile design**: Each tile contains both an image and a vocabulary word. The dual-encoding (visual + text) tests whether students understand the concept, not just pattern-match on text.
- **Multi-round clearing**: Tiles are sorted in batches. Incorrectly sorted tiles return to the pool for re-sorting, creating iterative correction without revealing the right answer.
- **Difficulty-weighted categories**: Some categories are harder than others and scored higher. This rewards deeper classification (e.g., sorting by function vs. by color).
- **Bin peeking**: Players can click a bin to peek inside and see what they already placed there, maintaining spatial memory.
- **Flexible solutions**: The same tile can validly go into different bins depending on the classification scheme chosen, supporting multiple valid solutions.

### 1.2 Shodor Interactivate Venn Diagram Sorter

Interactive Venn diagram sorting for shapes with properties:

- **2-circle and 3-circle modes**: Users sort colored polygons into overlapping Venn diagram regions. Items can belong to zero, one, or multiple categories depending on their properties.
- **Overlap regions as first-class drop targets**: The intersection areas between circles are distinct droppable zones. A triangle that is both "red" and "has 3 sides" goes in the overlap, not in either single circle.
- **Rule discovery mode**: The computer sets a secret rule and the player must discover it by sorting, then guess the rule. This tests analytical reasoning.
- **Outside region**: Items that belong to neither category go outside all circles, which is an important assessment feature (tests exclusion reasoning).

### 1.3 ClassTools Vortex

A sorting game generator where items are dragged into spinning vortex funnels:

- **Up to 4 categories**: Simple, clean UI with labeled vortex containers.
- **Speed scoring**: Scoring based on both accuracy and speed, adding time pressure.
- **Visual drama**: Items visually swirl into the vortex when dropped correctly, providing satisfying physics-based feedback.
- **Shareable URLs**: Each game configuration gets a unique URL for sharing.

### 1.4 NRICH Carroll Diagrams

Two-way classification tables (Carroll diagrams) for mathematical sorting:

- **Two-axis classification**: Items are sorted along two independent properties simultaneously (e.g., "odd/even" on one axis, "greater than 10 / not" on the other), creating a 2x2 or larger grid.
- **Configurable criteria**: Teachers can change the sorting properties via settings.
- **Drag-to-cell**: Numbers are dragged into cells of the grid, requiring the student to evaluate two properties at once.
- **Reversible placement**: Students can change their mind and reposition items freely before submission.

### 1.5 Ball Sort Puzzle (Mobile)

While not educational, this genre demonstrates satisfying sorting mechanics:

- **Tube/container metaphor**: Items (colored balls) stack inside transparent containers, creating a visual sense of progress as a container fills with one color.
- **Constraint-based sorting**: Only the top item can be moved; items can only go on matching colors or empty containers. This creates puzzle-like depth.
- **Confetti burst on completion**: Satisfying visual reward when a container is fully sorted.
- **Undo support**: Players can undo moves, encouraging experimentation.

### 1.6 H5P Drag and Drop / Category Sorting

Open-source interactive content type:

- **Drop zone configuration**: Each draggable can be allowed in specific drop zones (any zone for guessing, one correct zone for assessment).
- **Batch submit**: Students place all items, then click "Check" to see results all at once.
- **Retry without reveal**: Students can retry without the correct answers being shown, preserving assessment integrity.

### 1.7 MakeSort (Google Slides Add-on)

Generates sorting activities from ordered lists:

- **Auto-shuffle**: Items are automatically shuffled and scattered on the slide, creating a satisfying "mess to order" progression.
- **Position-based validation**: Checks answer correctness by comparing shape positions to the correct arrangement.
- **Instant feedback**: A sidebar tracks progress and points update in real-time.

---

## 2. Sort Mode Taxonomy

The sorting mechanic supports fundamentally different spatial layouts. Each mode changes the visual geometry of the sorting area and the rules for valid placements.

### 2.1 Bucket Sort (`bucket`)

The default and most common mode. Items are sorted into distinct, non-overlapping containers.

```
+------------------+    +------------------+    +------------------+
|   Category A     |    |   Category B     |    |   Category C     |
|   [header/icon]  |    |   [header/icon]  |    |   [header/icon]  |
|                  |    |                  |    |                  |
|  [item] [item]   |    |  [item]          |    |  [item] [item]   |
|  [item]          |    |  [item] [item]   |    |                  |
+------------------+    +------------------+    +------------------+
```

**Properties**: 2-6 categories, each item belongs to exactly one category, categories can have different visual styles (color, icon, header image).

**Assessment value**: Tests basic classification ability. Good for taxonomic sorting (living/non-living), property-based grouping (metals/non-metals), or functional classification (input/output devices).

### 2.2 Venn Diagram 2-Circle (`venn_2`)

Two overlapping circles creating 3 drop regions: A only, B only, A and B intersection.

```
        +-----------+
       /     A       \
      /    only       \
     |       +----+----+---+
     |       | A  & B  |   |
      \      |overlap|   /
       \     +----+----+--+
        +----+    B only  /
              \          /
               +--------+
```

**Properties**: Exactly 2 categories plus overlap region plus "outside" region. Items can belong to 0, 1, or 2 categories. The overlap zone is the key assessment challenge.

**Assessment value**: Tests whether students can identify items that share properties across categories. Requires understanding of set intersection. Much harder than bucket sort.

### 2.3 Venn Diagram 3-Circle (`venn_3`)

Three overlapping circles creating 7 distinct drop regions (A only, B only, C only, AB, AC, BC, ABC) plus an "outside" region.

```
         +------+
        / A only \
       /    +--+--+--+
      |     |AB|ABC| |
       \   +--+--+--+
        +--+ |AC|BC| /
           | +--+--+
           \ C only/
            +-----+
```

**Properties**: 3 categories, up to 8 regions (7 Venn regions + outside). This is the most analytically demanding mode.

**Assessment value**: Tests multi-dimensional classification. Extremely effective for biology (organisms with multiple characteristics), chemistry (element properties), or any domain where items have compound properties.

### 2.4 Matrix / Carroll Diagram (`matrix`)

A 2D grid where rows represent one classification axis and columns represent another. Items are sorted into cells based on two simultaneous criteria.

```
              | Property X: Yes | Property X: No |
--------------+-----------------+----------------+
Property Y:   |                 |                |
  Yes         |  [item] [item]  |  [item]        |
--------------+-----------------+----------------+
Property Y:   |                 |                |
  No          |  [item]         |  [item] [item] |
--------------+-----------------+----------------+
```

**Properties**: 2 axes, each with 2-4 values, creating a grid of cells. Each cell is a unique combination of axis values.

**Assessment value**: Tests two-dimensional reasoning. Students must evaluate items on two independent criteria simultaneously. Very effective for properties that are orthogonal (e.g., "conductor/insulator" x "natural/man-made").

### 2.5 Column Sort (`column`)

Items are sorted into vertical columns, often representing a spectrum or ordered categories.

```
 Col A    Col B    Col C    Col D
+------+ +------+ +------+ +------+
|      | |      | |      | |      |
|[item]| |[item]| |[item]| |[item]|
|[item]| |[item]| |      | |[item]|
|[item]| |      | |      | |      |
+------+ +------+ +------+ +------+
```

**Properties**: 2-6 columns, items stack vertically within each column. Visually similar to bucket sort but with a columnar layout that emphasizes parallelism and comparison across categories.

**Assessment value**: Works well for ordered/spectrum classifications (weak/moderate/strong, low/medium/high pH) where the spatial arrangement implies ordering.

### 2.6 Timeline Sort (Potential Extension)

Items sorted onto a horizontal timeline with date/period regions. Structurally similar to column sort but with temporal semantics and a linear left-to-right axis.

---

## 3. Visual Components

### 3.1 Item Cards

Item cards are the objects being sorted. Their visual richness is the single biggest factor in making a sorting game feel like a real game vs. homework.

#### Card Types (`item_card_type`)

| Type | Content | Use Case | Visual Weight |
|------|---------|----------|---------------|
| `text_only` | Text label only | Vocabulary, abstract concepts | Light |
| `text_with_icon` | Text + small icon/emoji | Quick visual cue, accessible | Medium |
| `image_with_caption` | Image + text below | Science specimens, objects, art | Heavy |
| `image_only` | Image only (no text) | Visual classification, art, shapes | Heavy |
| `rich_card` | Image + title + description line | Detailed items needing context | Very Heavy |

#### Card Design Properties

- **Card dimensions**: Configurable width/height ratio. Compact (pill-shaped) for text-only, square for image items, tall for rich cards.
- **Border treatment**: Rounded corners with subtle shadow. Border color can match the assigned category when placed (visual confirmation without revealing correctness).
- **Thumbnail/illustration**: For `image_with_caption` and `rich_card` types, the item has an associated illustration. This is the primary asset the pipeline must generate.
- **Grab handle indicator**: A subtle dot-grid or grip icon indicates the card is draggable.
- **Hover state**: Slight elevation (shadow increase) and scale-up (1.02x) on hover to signal interactivity.
- **Drag state**: Card lifts (larger shadow, 1.05x scale), slight rotation (2-3 degrees), reduced opacity at source position (ghost).
- **Card back**: Optional card-back design for memory-match hybrid modes. Not typically needed for pure sorting.

### 3.2 Category Containers

Category containers are the drop targets. Their visual treatment must clearly communicate "this is a destination" and provide identity to each category.

#### Container Styles (`container_style`)

| Style | Visual | Best For |
|-------|--------|----------|
| `bucket` | Rounded rectangle with colored header bar, interior area for dropped items | Default, most sort modes |
| `labeled_bin` | Bucket with large text label and optional icon in header | Simple categorization |
| `circle` | Circular container (for Venn diagram modes) | Venn 2 / Venn 3 |
| `cell` | Grid cell with row/column headers (for matrix mode) | Matrix / Carroll diagram |
| `column` | Tall vertical container with header | Column sort |
| `funnel` | Tapered container narrowing at bottom, items compress as they enter | Themed / engaging |
| `themed` | Custom-shaped container matching the topic (e.g., beaker for chemistry, biome for ecology) | Subject-specific immersion |

#### Container Design Properties

- **Header region**: Each container has a header showing the category name, optional icon, and optional color band. The header is always visible even when scrolling items inside.
- **Category color**: A consistent color applied to the header, border accent, and subtle background tint. Colors should be distinct and accessible (pass WCAG AA contrast).
- **Category icon**: Optional icon or small illustration representing the category concept (e.g., a flame icon for "Exothermic", a snowflake for "Endothermic").
- **Item count badge**: Small pill showing the number of items currently in the container (e.g., "3/5" or just "3").
- **Drop indicator**: When dragging over a container, the border glows/pulses, background lightens, and the container slightly expands (scale 1.02x) to invite the drop.
- **Empty state**: Dashed border with "Drop items here" placeholder text when the container is empty.
- **Scroll behavior**: If a container has many items, items scroll vertically within the container while the header remains fixed.
- **Min-height**: Containers maintain a minimum height even when empty so the layout does not collapse.

### 3.3 Item Pool / Source Tray

The unsorted items live in a source area before being placed into categories.

#### Pool Layouts

| Layout | Visual | Best For |
|--------|--------|----------|
| `horizontal_tray` | Items arranged in a horizontal scrollable row at top or bottom | Few items (< 10), mobile |
| `wrapped_grid` | Items in a flex-wrap grid | Many items (10-30), desktop |
| `scattered` | Items randomly positioned in a free-form area | Gamified "mess to order" feel |
| `stacked_deck` | Items stacked like a deck, only top item visible | Sequential reveal, adds suspense |

#### Pool Design Properties

- **Visual boundary**: Dashed border or subtle background to delineate the pool from the sorting area.
- **Counter**: "X items remaining" badge updates as items are sorted.
- **Return-to-pool**: Items can be dragged back to the pool from a category (unsort).
- **Shuffle button**: Optional button to reshuffle the visual order of pool items (does not change correctness).

### 3.4 Venn Diagram Components (Modes: `venn_2`, `venn_3`)

Venn diagrams require specialized visual components beyond standard containers.

- **SVG circle rendering**: Circles rendered as SVG with semi-transparent fills so overlapping regions are visually distinct (color blending).
- **Region labels**: Each distinct region (A only, B only, overlap, outside) has a subtle label. For the overlap, the label might say "Both A & B" or be blank for harder assessment.
- **Hit-test regions**: Drop detection uses geometric hit-testing (point-in-polygon) to determine which Venn region an item was dropped into, not just bounding-box collision.
- **Outside region**: A clearly marked area outside all circles for items that belong to no category.
- **Circle labels**: Each circle has a prominent label at its top arc showing the category name.
- **Item arrangement within regions**: Items dropped into a region auto-arrange (grid/flow layout) to avoid overlap.

### 3.5 Matrix Components (Mode: `matrix`)

- **Row headers**: Labels on the left side for one axis of classification.
- **Column headers**: Labels across the top for the second axis.
- **Grid cells**: Each cell is a distinct drop target at the intersection of a row and column value.
- **Cell highlighting**: Active cell highlights when item is dragged over it.
- **Corner cell**: The top-left corner cell can show the axis names (Row Axis / Column Axis) or be decorative.

### 3.6 Header / Instructions Region

- **Instruction banner**: A styled banner at the top showing the sorting instructions. Configurable text.
- **Category legend**: Optional legend showing all category names with their colors/icons for reference.
- **Progress indicator**: Shows how many items have been sorted out of the total (e.g., progress bar or "12/20 sorted").

---

## 4. Interaction Patterns

### 4.1 Primary: Drag-to-Category

The standard interaction. User grabs an item from the pool and drags it to a category container.

**Micro-interaction sequence**:
1. **Hover on item**: Cursor changes to grab, item lifts slightly (shadow + scale).
2. **Grab (mousedown/touchstart)**: Item lifts fully, ghost remains at original position, cursor changes to grabbing.
3. **Drag (mousemove/touchmove)**: Item follows cursor with slight lag. Valid drop targets highlight as the item passes over them.
4. **Hover over container**: Container border glows, background lightens, "magnetic" pull starts (item accelerates toward container center when close).
5. **Drop (mouseup/touchend)**: Item snaps into position within the container, brief settle animation (slight bounce or ease-out). Container count badge updates.
6. **Drop outside**: Item returns to pool with smooth animation (ease-back to original position).
7. **Re-sort**: Item can be dragged from one category to another, or back to the pool. The source container count decreases and the destination increases.

### 4.2 Alternative: Click-then-Click (Accessibility)

For users who cannot drag, or for touch devices where drag is unreliable:

1. **Click item**: Item highlights with a selection ring. A "Where does this go?" prompt appears.
2. **Click category**: Item animates from pool to the clicked category (fly-in animation).
3. **Click same item again**: Deselects.

This mode can be toggled globally or detected automatically (e.g., on keyboard-only navigation).

### 4.3 Submit Modes (`submit_mode`)

| Mode | Behavior | Assessment Value |
|------|----------|------------------|
| `batch_submit` | All items must be sorted before "Check Answers" button activates. Results shown for all items at once. | Best for summative assessment. No per-item feedback leaks. |
| `immediate_feedback` | Each drop gives instant right/wrong feedback. Incorrect items bounce back to pool. | Best for formative learning. Reveals answers immediately. |
| `round_based` | Items sorted in rounds. After each round, incorrect items return to pool. No per-item feedback, just "X correct this round". | BrainPOP Sortify model. Good middle ground. |
| `lock_on_place` | Once placed, items cannot be moved. Forces commitment. | High-stakes assessment. Tests confidence. |

### 4.4 Iterative Correction

For `round_based` and `batch_submit` modes, after checking:

- Incorrectly sorted items are visually flagged (red border flash) and returned to the pool.
- Correctly sorted items lock in place (green confirmation, slightly dimmed, non-draggable).
- The student re-sorts only the remaining incorrect items.
- This continues for a configurable number of rounds (e.g., max 3 attempts).
- No per-item correction feedback is shown (no "this should have gone in Category B"). The student must figure out the correct placement independently.

### 4.5 Multi-Category Items (`allow_multi_category`)

For Venn diagram modes, items can belong to multiple categories:

- After placing an item in one category, the item does NOT disappear from the pool. Instead, a copy remains (with a badge showing "1 placement").
- The student can place the same item in additional categories.
- A "Done with this item" button or double-click finalizes the item.
- This is critical for Venn diagram assessment where an item like "bat" might go in both "mammals" and "flying animals".

### 4.6 Multi-Level / Hierarchical Sorting

Items are sorted in stages of increasing specificity:

1. **Level 1**: Sort animals into "Vertebrates" and "Invertebrates" (2 buckets).
2. **Level 2**: Within "Vertebrates", sort into "Mammals", "Birds", "Reptiles", "Fish", "Amphibians" (5 sub-buckets).
3. **Level 3**: Within "Mammals", sort by habitat or diet.

Each level is a separate task within the same scene. The container for the completed parent category "opens up" to reveal sub-categories for the next level.

---

## 5. Configurable Properties

### 5.1 Sort Configuration (`SortingConfig`)

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `sort_mode` | `bucket \| venn_2 \| venn_3 \| matrix \| column` | `bucket` | Spatial layout mode for the sorting area |
| `item_card_type` | `text_only \| text_with_icon \| image_with_caption \| image_only \| rich_card` | `text_only` | Visual richness of item cards |
| `container_style` | `bucket \| labeled_bin \| circle \| cell \| column \| funnel \| themed` | `bucket` | Visual style of category containers |
| `header_type` | `text_only \| text_with_icon \| image_banner \| color_band` | `text_only` | How category headers are rendered |
| `pool_layout` | `horizontal_tray \| wrapped_grid \| scattered \| stacked_deck` | `wrapped_grid` | Layout of the unsorted item pool |
| `submit_mode` | `batch_submit \| immediate_feedback \| round_based \| lock_on_place` | `batch_submit` | When and how answers are checked |
| `allow_multi_category` | `boolean` | `false` | Whether items can belong to multiple categories (for Venn modes) |
| `max_attempts` | `number` | `3` | Maximum sorting rounds (for round_based submit mode) |
| `show_category_count` | `boolean` | `true` | Show item count badge on containers |
| `show_pool_count` | `boolean` | `true` | Show remaining items counter |
| `allow_reorder_within` | `boolean` | `false` | Whether item order within a category matters |
| `shuffle_items` | `boolean` | `true` | Randomize item order in pool on load |
| `instructions` | `string` | `"Sort each item into the correct category."` | Instruction text shown to the student |

### 5.2 Matrix-Specific Configuration

| Property | Type | Description |
|----------|------|-------------|
| `row_axis_label` | `string` | Label for the row axis (e.g., "State of Matter") |
| `column_axis_label` | `string` | Label for the column axis (e.g., "Conductivity") |
| `row_values` | `string[]` | Values along the row axis (e.g., ["Solid", "Liquid", "Gas"]) |
| `column_values` | `string[]` | Values along the column axis (e.g., ["Conductor", "Insulator"]) |

### 5.3 Venn-Specific Configuration

| Property | Type | Description |
|----------|------|-------------|
| `show_region_labels` | `boolean` | Whether overlap regions are labeled (e.g., "Both A & B") |
| `show_outside_region` | `boolean` | Whether to show an "outside" drop target for items belonging to no category |
| `circle_labels` | `string[]` | Labels for each circle (2 for venn_2, 3 for venn_3) |

---

## 6. Pipeline Data Model

### 6.1 Category Schema

Categories are the targets (containers/bins/circles/columns) that items are sorted into.

```python
class SortingCategory(BaseModel):
    """A single sorting category (bucket/bin/circle/column/cell)."""
    id: str                           # Unique ID, e.g. "cat_vertebrates"
    name: str                         # Display name, e.g. "Vertebrates"
    description: Optional[str]        # Optional hint/description (only shown if showCategoryHints=true)
    icon: Optional[str]               # Emoji or icon identifier, e.g. "🦴" or "icon:backbone"
    color: Optional[str]              # Tailwind color key, e.g. "blue", "green", "purple"
    header_image: Optional[str]       # URL/path to a generated header illustration
    # For matrix mode only:
    row_value: Optional[str]          # Which row this category belongs to
    column_value: Optional[str]       # Which column this category belongs to
```

### 6.2 Item Schema

Items are the objects being sorted. Each item has one or more correct category placements.

```python
class SortingItem(BaseModel):
    """A single item to be sorted into a category."""
    id: str                           # Unique ID, e.g. "item_eagle"
    text: str                         # Display text, e.g. "Eagle"
    image: Optional[str]              # URL/path to a generated item illustration
    correct_category_ids: List[str]   # List of valid category IDs (single for bucket, multiple for Venn)
    explanation: Optional[str]        # Post-submission explanation of why this item belongs here (not shown during assessment)
    difficulty: Optional[str]         # "easy" | "medium" | "hard" — for adaptive ordering
```

**Note on `correct_category_ids` vs `correct_category_id`**: The current codebase uses a single `correctCategoryId: str`. This must be upgraded to a list to support Venn diagram modes where items can belong to multiple categories. For backward compatibility, the pipeline can emit a single-element list for bucket mode.

### 6.3 Full Sorting Config

```python
class SortingConfig(BaseModel):
    """Complete configuration for a sorting/categorization mechanic instance."""
    # Core data
    categories: List[SortingCategory]
    items: List[SortingItem]

    # Mode configuration
    sort_mode: Literal["bucket", "venn_2", "venn_3", "matrix", "column"] = "bucket"
    item_card_type: Literal["text_only", "text_with_icon", "image_with_caption", "image_only", "rich_card"] = "text_only"
    container_style: Literal["bucket", "labeled_bin", "circle", "cell", "column", "funnel", "themed"] = "bucket"
    header_type: Literal["text_only", "text_with_icon", "image_banner", "color_band"] = "text_only"
    pool_layout: Literal["horizontal_tray", "wrapped_grid", "scattered", "stacked_deck"] = "wrapped_grid"
    submit_mode: Literal["batch_submit", "immediate_feedback", "round_based", "lock_on_place"] = "batch_submit"

    # Behavior flags
    allow_multi_category: bool = False
    max_attempts: int = 3
    show_category_count: bool = True
    show_pool_count: bool = True
    shuffle_items: bool = True
    instructions: str = "Sort each item into the correct category."

    # Matrix-specific (only used when sort_mode == "matrix")
    row_axis_label: Optional[str] = None
    column_axis_label: Optional[str] = None
    row_values: Optional[List[str]] = None
    column_values: Optional[List[str]] = None

    # Venn-specific (only used when sort_mode in ["venn_2", "venn_3"])
    show_region_labels: bool = True
    show_outside_region: bool = True
    circle_labels: Optional[List[str]] = None
```

### 6.4 Pipeline Generation Requirements

What the pipeline must generate for each sort mode:

| Sort Mode | Categories | Items | Images Needed | Special |
|-----------|-----------|-------|---------------|---------|
| `bucket` | 2-6 named categories with colors/icons | 8-24 items, each with 1 correct category | Per-item illustrations (if image card type), per-category icon | None |
| `venn_2` | 2 circle categories | 8-16 items, some with 2 correct categories | Per-item illustrations, 2 circle labels | Overlap items must be identified |
| `venn_3` | 3 circle categories | 10-21 items, some with 2-3 correct categories | Per-item illustrations, 3 circle labels | 7-region mapping required |
| `matrix` | rows x columns cell categories | 6-20 items, each maps to one cell | Per-item illustrations | Row/column axis labels and values |
| `column` | 2-6 column categories | 8-24 items | Per-item illustrations | Column ordering may be significant |

### 6.5 Example: Biology Classification (Bucket Mode)

```json
{
  "sort_mode": "bucket",
  "item_card_type": "image_with_caption",
  "container_style": "labeled_bin",
  "categories": [
    { "id": "cat_mammals", "name": "Mammals", "color": "orange", "icon": "🦁" },
    { "id": "cat_reptiles", "name": "Reptiles", "color": "green", "icon": "🦎" },
    { "id": "cat_amphibians", "name": "Amphibians", "color": "blue", "icon": "🐸" }
  ],
  "items": [
    { "id": "item_1", "text": "Dolphin", "correct_category_ids": ["cat_mammals"], "image": "/assets/dolphin.svg" },
    { "id": "item_2", "text": "Gecko", "correct_category_ids": ["cat_reptiles"], "image": "/assets/gecko.svg" },
    { "id": "item_3", "text": "Newt", "correct_category_ids": ["cat_amphibians"], "image": "/assets/newt.svg" },
    { "id": "item_4", "text": "Platypus", "correct_category_ids": ["cat_mammals"], "image": "/assets/platypus.svg" }
  ],
  "submit_mode": "batch_submit",
  "instructions": "Sort each animal into its correct vertebrate class."
}
```

### 6.6 Example: Chemistry Properties (Venn 2 Mode)

```json
{
  "sort_mode": "venn_2",
  "item_card_type": "text_with_icon",
  "allow_multi_category": true,
  "show_outside_region": true,
  "circle_labels": ["Conducts Electricity", "Magnetic"],
  "categories": [
    { "id": "cat_conducts", "name": "Conducts Electricity", "color": "blue" },
    { "id": "cat_magnetic", "name": "Magnetic", "color": "red" }
  ],
  "items": [
    { "id": "item_iron", "text": "Iron", "correct_category_ids": ["cat_conducts", "cat_magnetic"] },
    { "id": "item_copper", "text": "Copper", "correct_category_ids": ["cat_conducts"] },
    { "id": "item_nickel", "text": "Nickel", "correct_category_ids": ["cat_conducts", "cat_magnetic"] },
    { "id": "item_wood", "text": "Wood", "correct_category_ids": [] },
    { "id": "item_aluminum", "text": "Aluminum", "correct_category_ids": ["cat_conducts"] }
  ],
  "submit_mode": "batch_submit",
  "instructions": "Sort each material based on its properties. Some materials may belong in the overlap region."
}
```

### 6.7 Example: States of Matter (Matrix Mode)

```json
{
  "sort_mode": "matrix",
  "item_card_type": "text_with_icon",
  "container_style": "cell",
  "row_axis_label": "State of Matter",
  "column_axis_label": "Natural vs Synthetic",
  "row_values": ["Solid", "Liquid", "Gas"],
  "column_values": ["Natural", "Synthetic"],
  "categories": [
    { "id": "cell_solid_natural", "name": "Solid + Natural", "row_value": "Solid", "column_value": "Natural" },
    { "id": "cell_solid_synthetic", "name": "Solid + Synthetic", "row_value": "Solid", "column_value": "Synthetic" },
    { "id": "cell_liquid_natural", "name": "Liquid + Natural", "row_value": "Liquid", "column_value": "Natural" },
    { "id": "cell_liquid_synthetic", "name": "Liquid + Synthetic", "row_value": "Liquid", "column_value": "Synthetic" },
    { "id": "cell_gas_natural", "name": "Gas + Natural", "row_value": "Gas", "column_value": "Natural" },
    { "id": "cell_gas_synthetic", "name": "Gas + Synthetic", "row_value": "Gas", "column_value": "Synthetic" }
  ],
  "items": [
    { "id": "item_granite", "text": "Granite", "correct_category_ids": ["cell_solid_natural"] },
    { "id": "item_plastic", "text": "Plastic", "correct_category_ids": ["cell_solid_synthetic"] },
    { "id": "item_water", "text": "Water", "correct_category_ids": ["cell_liquid_natural"] },
    { "id": "item_gasoline", "text": "Gasoline", "correct_category_ids": ["cell_liquid_synthetic"] },
    { "id": "item_oxygen", "text": "Oxygen", "correct_category_ids": ["cell_gas_natural"] },
    { "id": "item_freon", "text": "Freon", "correct_category_ids": ["cell_gas_synthetic"] }
  ],
  "submit_mode": "batch_submit",
  "instructions": "Classify each substance by its state of matter AND whether it is naturally occurring or synthetic."
}
```

---

## 7. Animation & Game Feel

### 7.1 Drag Feedback

- **Pickup**: `transform: scale(1.05); box-shadow: 0 8px 25px rgba(0,0,0,0.15); rotate: 2deg` with `transition: 100ms ease-out`.
- **Ghost at source**: Original position shows a 40% opacity ghost of the item.
- **Magnetic snap**: When the dragged item enters a container's bounding box, it accelerates toward the container center (spring physics with damping).

### 7.2 Drop Feedback

- **Snap-in**: Item decelerates and settles into position with a subtle bounce (ease-out-back timing: slight overshoot then settle).
- **Container pulse**: Container border briefly pulses (scale 1.01x, border color intensifies) when an item is dropped in.
- **Count update**: Item count badge increments with a scale-up animation (pop effect).
- **Pool shrink**: Pool counter decrements with the number briefly highlighted.

### 7.3 Submission Feedback

- **Batch reveal**: When "Check Answers" is clicked, items are evaluated in a staggered cascade (50ms delay between each). Each item gets a green checkmark or red X overlay.
- **Container glow**: Containers with all correct items get a green glow ring. Containers with any incorrect items get a red ring.
- **Incorrect return**: Incorrectly sorted items animate back to the pool (arc trajectory, not linear) with a gentle shake effect.
- **Correct lock**: Correctly sorted items dim slightly and become non-draggable, with a lock icon overlay.

### 7.4 Venn-Specific Animations

- **Circle hover**: When dragging over a Venn circle, the circle's fill opacity increases and the label brightens.
- **Overlap highlight**: When the item is in an overlap region, both circles highlight simultaneously, and the overlap region itself gets a distinct highlight.
- **Outside drop**: Dropping outside all circles triggers a subtle "excluded" animation (item settles into the outside area with a muted color treatment).

### 7.5 Satisfying Completion

- **All sorted**: When the last item leaves the pool, a brief "All sorted!" message animates in.
- **Perfect score**: Confetti or particle burst animation on 100% correct.
- **Category celebration**: Fully correct categories get a brief sparkle/shine effect on their header.

---

## 8. Accessibility

### 8.1 Keyboard Navigation

- **Tab**: Moves focus between items in the pool.
- **Enter/Space on focused item**: Selects the item for placement (enters "placement mode").
- **Tab (in placement mode)**: Cycles through available category containers.
- **Enter/Space on focused container**: Places the selected item into that container.
- **Escape**: Cancels the current selection (returns to browsing mode).
- **Arrow keys**: Navigate within the pool or within a container's items.
- **Delete/Backspace on a placed item**: Returns the item to the pool.

### 8.2 Screen Reader Support

- Items announce: "{item text}, unsorted item, {position} of {total}".
- Categories announce: "{category name}, {count} items, drop target".
- On placement: "Moved {item text} to {category name}".
- On submission: "{correct count} of {total} correct".

### 8.3 Touch Device Considerations

- Touch targets minimum 44x44px.
- Long-press to initiate drag on mobile (avoids conflict with scroll).
- Alternative: tap-to-select then tap-category pattern for one-handed use.
- Provide a "Click to place" toggle button visible on touch devices.

---

## 9. Current Codebase Gap Analysis

### 9.1 Backend Gaps

| Component | Current State | Gap |
|-----------|--------------|-----|
| `SortingConfig` (interactive_diagram.py) | Basic: items, categories, allowPartialCredit, showCategoryHints | Missing: sort_mode, item_card_type, container_style, header_type, pool_layout, submit_mode, allow_multi_category, matrix/venn-specific fields |
| `SortingCategory` (interactive_diagram.py) | Has: id, label, description, color | Missing: icon, header_image, row_value, column_value |
| `SortingItem` (interactive_diagram.py) | Has: id, text, correctCategoryId, description | Missing: image, correct_category_ids (list), explanation, difficulty |
| `SortingDesign` (game_design_v3.py) | Has: categories, items (as dicts), show_category_hints | Missing: All sort_mode configuration, structured category/item schemas |
| Pipeline generation | Categories and items generated as flat lists | No image generation for items, no mode-specific validation, no Venn/matrix support |

### 9.2 Frontend Gaps

| Component | Current State | Gap |
|-----------|--------------|-----|
| `SortingCategories.tsx` | Basic DnD with buckets, batch submit only | Missing: Venn mode, matrix mode, column mode, item card types beyond text, container styles, submit modes, multi-category support, iterative correction |
| Item cards | Text-only with optional description | Missing: image support, icon support, rich card layout, card type switching |
| Category containers | Simple rounded div with color header | Missing: icons, image headers, themed styles, funnel style, count badges |
| Pool | Flex-wrap div | Missing: layout options, counter, shuffle button, scattered mode |
| Animations | Minimal (opacity/scale on drag) | Missing: snap bounce, magnetic pull, staggered reveal, confetti, arc return |
| Accessibility | KeyboardSensor included | Missing: click-to-place alternative, screen reader announcements, touch mode |
| Venn diagram | Not implemented | Completely missing: SVG circles, overlap detection, region labels, multi-category placement |
| Matrix mode | Not implemented | Completely missing: grid layout, row/column headers, cell drop targets |

### 9.3 Priority Implementation Order

1. **Schema upgrade**: Extend `SortingConfig`, `SortingCategory`, `SortingItem` with all new fields (backward compatible with defaults).
2. **Bucket mode polish**: Add container styles, item card types, submit modes, pool layouts, animations to existing bucket implementation.
3. **Venn 2 mode**: SVG circle rendering, overlap detection, multi-category items, region labels.
4. **Matrix mode**: Grid layout, row/column headers, cell drop targets, two-axis classification.
5. **Column mode**: Vertical stacking containers, ordered column semantics.
6. **Venn 3 mode**: Triple-circle rendering, 7-region hit detection (most complex).
7. **Pipeline integration**: Game designer generates sort_mode-appropriate configs, asset generator creates per-item illustrations, blueprint assembler populates all config fields.

---

## Appendix A: Sort Mode Decision Matrix (For Game Planner Agent)

| Question Pattern | Recommended Mode | Reasoning |
|-----------------|------------------|-----------|
| "Classify X into groups" | `bucket` | Simple one-to-one classification |
| "Which X have property A, B, or both?" | `venn_2` | Items can share properties |
| "Classify by three overlapping traits" | `venn_3` | Multi-dimensional property analysis |
| "Sort X by two independent properties" | `matrix` | Two orthogonal classification axes |
| "Arrange X from least to most" | `column` | Ordered/spectrum classification |
| "Group X into taxonomic levels" | `bucket` + multi-level | Hierarchical classification |

## Appendix B: Item Count Guidelines

| Sort Mode | Min Items | Ideal Items | Max Items | Categories |
|-----------|-----------|-------------|-----------|------------|
| `bucket` | 6 | 12-16 | 30 | 2-6 |
| `venn_2` | 6 | 10-14 | 20 | 2 (+overlap +outside) |
| `venn_3` | 8 | 14-18 | 24 | 3 (+4 overlap regions +outside) |
| `matrix` | 4 | 8-12 | 20 | rows x columns (typically 4-9 cells) |
| `column` | 6 | 10-16 | 24 | 2-6 |

## Appendix C: Assessment Integrity Notes

Since this is a TESTING mechanic, these principles must be maintained:

1. **Never reveal correct placements during active assessment.** In `batch_submit` mode, show only aggregate results (X of Y correct), not which specific items are wrong. In `round_based` mode, return incorrect items to the pool without indicating where they should go.
2. **Category descriptions should not give away answers.** Descriptions like "Animals that lay eggs" are acceptable (they describe the category criterion). Descriptions like "Put the chicken, snake, and turtle here" are not.
3. **Item descriptions should not reveal their category.** An item description like "A cold-blooded vertebrate" on a "Reptiles vs Mammals" sort gives away the answer. Descriptions should provide neutral context only.
4. **Shuffling must be truly random.** Items should not be pre-grouped by their correct category in the pool.
5. **Distractor items are valuable.** In Venn diagram modes, include items that belong to NO category (outside region). In bucket mode, consider a "None of these" category if the assessment tests exclusion reasoning.
