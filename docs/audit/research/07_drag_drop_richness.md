# Drag-and-Drop Diagram Labeling: Components & Assets for Game-Like Assessment

## Purpose

This document defines what visual components, assets, interactions, and configurable properties are needed to make a **drag-and-drop diagram labeling mechanic** feel like a premium, game-like assessment -- not a flat HTML exercise with rectangles on an image.

Scope: Only mechanic-specific components and assets for the drag-drop labeling interaction. Excludes scoring strategies, hint systems, combo/streak mechanics, post-game review panels, and other game-wide features handled separately. The mechanic is a **testing mechanic** -- it assesses whether students can correctly place labels. It must not reveal answers, highlight correct positions, or otherwise leak information that would compromise assessment validity.

---

## 1. Reference Examples: What Makes Great Diagram Labeling Games

### 1.1 BioDigital Human

BioDigital Human is a 3D anatomy platform with over 14,000 anatomical structures. Its labeling system is the gold standard for connecting text labels to visual structures on a complex image.

**Key design lessons:**
- **Leader lines**: Every label connects to its target structure via a visible leader line -- a thin line running from the label card to a pin point on the structure surface. The leader line style is configurable: users can switch between "Leader Line" (straight/angled line from pin to floating label) and "Floating" (label hovers near the pin with no connecting line). Labels can be positioned on the left or right side of the pin.
- **Pin points**: Each label anchors to a specific point on the 3D model surface via a small circular pin marker. The pin is the ground truth position; the label card floats at a readable distance, connected by the leader line.
- **Draggable label repositioning**: Users can drag label tags to move them if they cover underlying structures, without changing the pin anchor. This separation of label display position from anchor position is critical for complex diagrams with many overlapping structures.
- **Label editing**: Content, style, and interaction properties are editable per-label. Labels are not static text -- they are interactive UI objects with configurable behavior.
- **Clean focus**: The diagram is the primary focus. Labels are layered on top without cluttering the underlying image. The visual hierarchy ensures the anatomy is always readable beneath the label overlay.

### 1.2 Complete Anatomy (3D4Medical)

A comprehensive 3D anatomy application with quiz modes that assess anatomical knowledge through interactive labeling and identification.

**Key design lessons:**
- **Dual quiz modes**: "Label Anatomy" questions require choosing the correct label for each structure from a drop-down menu attached to pin points. "Select Anatomy in 3D" questions reverse the direction -- the label name is shown and the student must click/tap the correct structure on the model. These two modes test complementary skills (name-to-location vs. location-to-name).
- **Pin labels with pronunciation**: Labels include audio pronunciation guides, so students engage with both visual identification and terminology. 728 pin labels have associated audio.
- **Captured starting positions**: Quiz creators capture a specific model position (rotation, zoom level) as the starting view for each question, ensuring all students see the same perspective. This is the equivalent of controlling the diagram viewport.
- **Post-answer reveal**: After submission, correct answers appear both in the label itself AND in a separate information panel. This dual-display pattern prevents the student from needing to hunt for the answer.

### 1.3 Seterra (GeoGuessr)

A geography quiz platform with 400+ map-based labeling quizzes. The simplest and most addictive labeling game in production, with millions of users.

**Key design lessons:**
- **Click-on-map, not drag-drop**: Seterra's primary mode is "click the named location on the map." A label name appears as a prompt, and the student clicks the correct region. This is the reverse labeling pattern -- zone highlights, student picks. No dragging at all.
- **Extreme visual clarity**: The map is the entire screen. No sidebars, no chrome, no distractions. The tray of remaining labels doubles as a progress indicator (names disappear as they are correctly placed). The interface has near-zero cognitive overhead.
- **Short session design**: Each quiz has 10-50 items and takes 1-5 minutes. The tight scope makes replay attractive and failure low-stakes. This framing -- small, repeatable, fast -- is more game-like than a single exhaustive labeling exercise.
- **Score-as-speed**: Seterra's primary metric is time-to-completion, not accuracy. Incorrect clicks add time penalty. This reframes the exercise as a speed game, creating urgency without changing the core mechanic.

### 1.4 Kenhub

An online anatomy learning platform with 6,000+ anatomical illustrations and 1,000+ quiz questions. Their quizzes use a spaced-repetition algorithm.

**Key design lessons:**
- **Adaptive difficulty**: The quiz algorithm tracks weak spots based on wrong answers and serves more questions on those structures. This means the label set is not static -- it changes between sessions based on performance history. The system learns which labels the student struggles with.
- **Mixed quiz types**: Within a single session, Kenhub mixes identification quizzes (label this structure), clinical question banks (scenario-based), and "Intelligent Mix" (combination). The drag-drop labeling is one mode within a broader assessment framework, not a standalone exercise.
- **Diagram-paired text**: Every diagram is paired with detailed textual explanations. The diagram is not decorative -- it is the primary learning artifact, with text supporting it rather than the reverse. This "diagram-first" information architecture makes the labeling feel substantive.

### 1.5 H5P Drag and Drop

An open-source HTML5 content type used in Moodle, WordPress, and other LMS platforms. The most widely deployed drag-and-drop labeling implementation in education.

**Key design lessons:**
- **Configurable drop zones**: Each drop zone can be configured with a label, tip text, size constraints (minimum 24x24, maximum 1000x1000 canvas), and zone acceptance rules. Zones can accept one element or multiple elements, and auto-alignment can be toggled.
- **Relationship cardinality**: H5P supports one-to-one (each label goes to exactly one zone), one-to-many (one label can go to multiple zones), many-to-one (multiple labels can be placed in one zone), and many-to-many mappings. Most educational labeling is one-to-one, but anatomy systems (where one structure has multiple valid names) need many-to-one.
- **Draggable-to-zone assignment**: Each draggable specifies which drop zones it is allowed to land on (its "acceptance list"), separate from which zone is the correct answer. This enables constrained drag spaces where certain labels can only be dropped in certain regions, reducing random guessing on large diagrams.
- **Simple visual vocabulary**: H5P zones are rectangles with optional background color. There is no polygon support, no leader lines, no pin points. The result is functional but visually plain -- the "baseline" that every premium implementation should exceed.

### 1.6 Quizlet Diagrams

A mainstream study tool where users create labeling quizzes by tagging hotspots on uploaded images.

**Key design lessons:**
- **Hotspot tagging**: Users click on an image to place circular hotspot markers, then associate each hotspot with a term and definition. The hotspot is a simple point with a configurable hit radius -- not a polygon or bounding box. Free users get up to 8 hotspots; paid users have unlimited.
- **Two study modes**: "Learn" mode gives instant feedback and repeats missed items. "Match" mode requires all items to be matched correctly before the activity is complete. These map cleanly to "learn mode" and "test mode" in an assessment context.
- **Blur tool for pre-labeled images**: Quizlet's only image editing tool is a blur brush. If the uploaded diagram already has text labels on it, users blur them before adding hotspots. This is the manual equivalent of the AI label-removal pipeline (ImageLabelClassifier + SmartInpainter).
- **Minimal UI footprint**: Hotspots are small numbered circles on the image. No leader lines, no label cards on the diagram itself. Labels appear only in the sidebar/tray. This extreme minimalism keeps the diagram clean but sacrifices spatial association.

---

## 2. Visual Components That Make Drag-Drop Labeling Game-Like

The current DraggableLabel component is a single text string in a bordered pill. The DropZone is a dashed rectangle, circle, or polygon outline. The LabelTray is a `flex-wrap` container. Below is everything needed to transform the interaction from "functional HTML exercise" to "game-like premium experience."

### 2.1 Leader Lines

Leader lines are the single most impactful visual upgrade for diagram labeling. They are SVG paths connecting a placed label to the boundary or center of its target zone, drawn on a full-canvas overlay. Without leader lines, placed labels sit inside or near their zones with no visible connection to the underlying anatomy. With leader lines, the diagram looks like a professional illustration from a textbook.

#### How They Work

When a label is correctly placed, a thin SVG path is drawn from the label's position (either inside the zone or at a designated label anchor point outside the zone) to a pin point on the zone boundary. The path is animated with a "draw-on" effect using SVG `stroke-dasharray` and `stroke-dashoffset` transitions.

#### Leader Line Anatomy

```
[LABEL CARD] -------- leader line path --------> [PIN POINT on zone boundary]
                                                         |
                                                   (small circle
                                                    or diamond marker)
```

The label card sits at the "label end." The pin point sits at the "anchor end" on the zone. The line runs between them, optionally with a bend (elbow) or curve (bezier).

#### Leader Line Style Types

| Style | SVG Path | Best For |
|-------|----------|----------|
| `straight` | `M x1,y1 L x2,y2` | Simple diagrams with few labels, no overlap |
| `elbow` | `M x1,y1 L xMid,y1 L xMid,y2 L x2,y2` | Dense diagrams where labels are arranged in a column to one side |
| `curved` | `M x1,y1 Q cx,cy x2,y2` (quadratic bezier) | Organic diagrams (biology, anatomy) where straight lines feel clinical |
| `fluid` | `M x1,y1 C cp1x,cp1y cp2x,cp2y x2,y2` (cubic bezier) | Complex layouts where lines need to route around obstacles |

#### Leader Line Animation

The "draw-on" effect is achieved with CSS/SVG animation:

```css
@keyframes draw-leader-line {
  from { stroke-dashoffset: var(--line-length); }
  to   { stroke-dashoffset: 0; }
}
```

The line appears to draw itself from the pin point toward the label (or vice versa) over 300-500ms. This animation fires once when the label is first placed correctly.

#### Configurable Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `leader_line_style` | `'straight' \| 'elbow' \| 'curved' \| 'fluid' \| 'none'` | `'straight'` | Path shape between label and anchor |
| `leader_line_color` | `string` (hex/css color) | `'#94a3b8'` (slate-400) | Stroke color |
| `leader_line_width` | `number` | `1.5` | Stroke width in pixels (non-scaling-stroke) |
| `leader_line_dash` | `string \| null` | `null` (solid) | Dash pattern (e.g., `'6 3'` for dashed) |
| `leader_line_animate` | `boolean` | `true` | Whether to animate the draw-on effect |
| `leader_line_animate_duration_ms` | `number` | `400` | Duration of draw-on animation |
| `pin_marker_shape` | `'circle' \| 'diamond' \| 'arrow' \| 'none'` | `'circle'` | Marker shape at the zone anchor end |
| `pin_marker_size` | `number` | `6` | Marker diameter/width in pixels |
| `label_anchor_side` | `'auto' \| 'left' \| 'right' \| 'top' \| 'bottom'` | `'auto'` | Which side of the diagram the label cards cluster on |

#### Implementation: LeaderLineOverlay Component

A new `LeaderLineOverlay` component renders as a single full-canvas SVG (like the existing `PolygonOverlay`) with one `<path>` per placed label. The SVG uses `viewBox="0 0 100 100"` to match the percentage-based coordinate system of zones.

Each leader line path needs two endpoints:
1. **Pin anchor**: A point on the zone boundary (for area zones) or the zone center (for point zones). For polygon zones, this is the closest point on the polygon boundary to the label position. For circle zones, it is the point on the circle perimeter closest to the label.
2. **Label position**: Either the center of the placed label card (if inside the zone) or a designated position in a label column alongside the diagram (if using external label layout).

### 2.2 Zone Shape Types

The current implementation supports three zone shapes: `circle`, `polygon`, and `rect`. The type system also defines `ZoneType` as `'point' | 'area'`. This is a solid foundation. The gap is not in type support but in visual richness and configurable behavior per shape.

#### Zone Shape Rendering Upgrades

| Shape | Current State | Upgraded State |
|-------|---------------|----------------|
| `circle` | Dashed circle, flat color fill | Smooth gradient fill on hover, configurable hit radius (separate from visual radius), pulsing idle animation |
| `polygon` | Smooth Catmull-Rom path via `PolygonOverlay` | Per-polygon fill opacity, configurable stroke style (solid/dashed/dotted), optional vertex markers for debugging |
| `rect` | Dashed rectangle with border | Rounded corners configurable, shadow on hover, optional inner label slot |
| `point` | Small colored dot | Configurable point marker (circle, crosshair, pin icon, numbered badge), configurable hit radius independent of visual size |

#### New Zone Shape: `freeform`

Some anatomical structures (blood vessels, nerves, irregular tissue boundaries) cannot be represented well by circles, rectangles, or even closed polygons. A `freeform` zone type would accept an open SVG path (not closed) with a configurable stroke width that defines the hit area. This is useful for structures like "trace the path of the vagus nerve" where the target is a line, not an area.

#### Configurable Zone Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `zone_shape` | `'circle' \| 'polygon' \| 'rect' \| 'point' \| 'freeform'` | `'circle'` | Shape of the drop target |
| `zone_type` | `'point' \| 'area'` | Inferred from radius | Whether the zone is a small indicator or a precise boundary |
| `hit_radius` | `number` | Same as visual radius | Radius of the invisible hit area (can be larger than visual radius for small targets) |
| `visual_radius` | `number` | Same as `radius` | Visual size of the zone indicator |
| `idle_animation` | `'none' \| 'pulse' \| 'glow' \| 'breathe'` | `'none'` | Subtle animation when zone is empty and waiting for a label |
| `hover_effect` | `'highlight' \| 'scale' \| 'glow' \| 'none'` | `'highlight'` | Visual feedback when label is dragged over zone |
| `fill_opacity` | `number` | `0.06` (polygon), `0` (point) | Opacity of zone fill color |
| `stroke_style` | `'solid' \| 'dashed' \| 'dotted' \| 'none'` | `'dashed'` | Stroke rendering for zone boundary |
| `corner_radius` | `number` | `4` | Border radius for rect zones (px) |

### 2.3 Label Card Design

The current DraggableLabel is a plain text string in a bordered pill with shadow. This is the baseline. Premium labeling games use rich label cards with multiple content zones.

#### Label Card Types

| Type | Layout | Content | Use Case |
|------|--------|---------|----------|
| `text` | Single-line text | Label name only | Simple diagrams, many labels, compact tray |
| `text_with_icon` | Icon (left) + text (right) | Small icon hint + label name | Categorized labels (organs, bones, muscles) where icon signals category |
| `text_with_thumbnail` | Thumbnail (top or left) + text | Small image + label name | Histology, cell biology, where the label itself has a visual referent |
| `text_with_description` | Title (top) + description (bottom, smaller) | Label name + supporting text | LEARN MODE ONLY -- description visible after placement |

#### Label Card Anatomy

```
+------+----------------------------+
| ICON |  Label Text                |  <-- text_with_icon
|      |  (optional category tag)   |
+------+----------------------------+

+-----------------------------------+
| [THUMBNAIL IMAGE]                 |  <-- text_with_thumbnail
|-----------------------------------|
|  Label Text                       |
+-----------------------------------+

+-----------------------------------+
|  Label Text                       |  <-- text (current implementation)
+-----------------------------------+
```

#### Label Card States

| State | Visual Treatment |
|-------|-----------------|
| `idle` | Default card appearance in tray. Subtle shadow, full opacity. Grab cursor on hover. |
| `dragging` | Elevated shadow (larger blur, offset), slight scale-up (1.05x), reduced opacity on the tray ghost (0.5). The dragged copy follows the pointer. |
| `hover_over_zone` | Zone highlight activates. Label card shows subtle green/blue tint if zone is a valid target. |
| `placed_correct` | Card snaps into position with spring animation. Green accent. Leader line draws on. |
| `placed_incorrect` | Card shakes horizontally (3 oscillations, 200ms), then springs back to tray. Red flash on card border. |
| `distractor_rejected` | Same as incorrect, but with a distinct visual (e.g., strikethrough on text, gray-out) to signal "this label does not belong anywhere." |
| `disabled` | Grayed out, no pointer events. Used for already-placed labels in the tray. |

#### Configurable Label Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `label_style` | `'text' \| 'text_with_icon' \| 'text_with_thumbnail' \| 'text_with_description'` | `'text'` | Card layout type |
| `label_icon` | `string \| null` | `null` | Icon identifier (emoji, icon name, or URL) |
| `label_thumbnail_url` | `string \| null` | `null` | Thumbnail image URL |
| `label_description` | `string \| null` | `null` | Supporting text (LEARN MODE ONLY) |
| `label_category` | `string \| null` | `null` | Category tag for grouping in tray |
| `label_color` | `string \| null` | `null` | Accent color for card border/background |
| `label_font_size` | `'sm' \| 'base' \| 'lg'` | `'sm'` | Text size within the card |

### 2.4 Animated Snap Feedback

The moment a label is placed is the critical feedback point. The animation must communicate correctness/incorrectness without revealing the answer (in test mode, correctness may not be revealed until submission).

#### Correct Placement Animation (when feedback is enabled)

A spring physics animation with configurable stiffness and damping:

1. Label snaps from pointer position to zone center (or label anchor position) using a spring transition.
2. On arrival, a brief scale pulse (1.0 -> 1.1 -> 1.0, 200ms) provides tactile confirmation.
3. The zone border transitions from dashed to solid.
4. Leader line draws on from pin point to label (300-400ms).
5. Optional: A small particle burst (3-5 particles) radiates from the placement point.

Spring parameters:
- `stiffness`: 300 (snappy but not instantaneous)
- `damping`: 25 (slight overshoot then settle)
- `mass`: 0.8 (responsive, not heavy)

#### Incorrect Placement Animation (when feedback is enabled)

1. Label lands at zone center momentarily (100ms).
2. Horizontal shake: 3 oscillations of +/- 8px over 200ms, with decreasing amplitude.
3. Label animates back to tray position using a spring transition (stiffness: 200, damping: 20).
4. Zone border briefly flashes red (150ms), then returns to default.
5. Label in tray shows a brief red border pulse (300ms), then returns to default.

#### Deferred Feedback (Test Mode)

In test mode, correctness is not revealed per-placement. Instead:

1. Label snaps to zone center with spring animation (same as correct).
2. Zone border transitions from dashed to solid (neutral color, not green/red).
3. Label is shown in zone with neutral styling.
4. No leader line animation (or leader line in neutral gray).
5. Correctness is revealed only after the student submits all placements.

#### Configurable Animation Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `placement_animation` | `'spring' \| 'ease' \| 'instant' \| 'none'` | `'spring'` | Animation type for label-to-zone snap |
| `spring_stiffness` | `number` | `300` | Spring stiffness (higher = snappier) |
| `spring_damping` | `number` | `25` | Spring damping (higher = less overshoot) |
| `incorrect_animation` | `'shake' \| 'bounce_back' \| 'fade_out' \| 'none'` | `'shake'` | Animation for incorrect placement |
| `show_placement_particles` | `boolean` | `false` | Particle burst on correct placement |
| `feedback_timing` | `'immediate' \| 'deferred'` | `'immediate'` | When to reveal correctness |

### 2.5 Zoom and Pan on Diagram Canvas

For large, detailed diagrams (anatomy, engineering schematics, maps), the ability to zoom into regions and pan across the diagram is essential. Without it, small structures are impossible to label on mobile devices, and dense diagrams become an unreadable mess of overlapping zones.

#### Zoom Behavior

| Feature | Description |
|---------|-------------|
| Pinch-to-zoom (touch) | Two-finger pinch gesture scales the diagram canvas. Min zoom: 1x (fit-to-container). Max zoom: 4x. |
| Scroll-wheel zoom (desktop) | Mouse wheel scales the diagram, centered on cursor position. Modifier key (Ctrl/Cmd) required to prevent accidental zoom during scroll. |
| Zoom controls (UI) | Floating zoom buttons (+/-/reset) in corner of canvas. Visible on hover, always visible on touch devices. |
| Zoom-to-zone | When a specific zone is selected (via tray interaction or keyboard), the canvas smoothly pans and zooms to center that zone at 2x magnification. |

#### Pan Behavior

| Feature | Description |
|---------|-------------|
| Drag-to-pan | When zoomed in, single-finger drag (touch) or mouse drag (with pan modifier) moves the canvas viewport. Must not conflict with label dragging. |
| Boundary clamping | Pan is clamped so the diagram edge cannot move past the viewport center. No infinite scroll. |
| Minimap | Optional: A small thumbnail of the full diagram appears in the corner when zoomed in, showing the current viewport as a highlighted rectangle. |

#### Implementation Notes

Use `react-zoom-pan-pinch` library, which provides `TransformWrapper` and `TransformComponent` with configurable min/max scale, pan boundaries, and gesture handling. The library supports both touch and mouse input and handles the conflict between drag-to-pan and drag-to-drop by requiring a modifier key or distinct gesture for panning.

Critical: Zoom state must be shared with the drop zone coordinate system. When zoomed to 2x, a drop at viewport pixel (400, 300) must be correctly translated to diagram percentage coordinates. The `react-zoom-pan-pinch` library provides a `transformState` object with `scale`, `positionX`, and `positionY` that can be used for this conversion.

#### Configurable Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `zoom_enabled` | `boolean` | `false` | Whether zoom/pan controls are available |
| `zoom_min` | `number` | `1` | Minimum zoom level (1 = fit-to-container) |
| `zoom_max` | `number` | `4` | Maximum zoom level |
| `zoom_controls_visible` | `boolean` | `true` | Show floating +/-/reset buttons |
| `minimap_enabled` | `boolean` | `false` | Show minimap when zoomed in |
| `zoom_to_zone_on_select` | `boolean` | `false` | Auto-zoom to zone when selected |

### 2.6 Contextual Info Panel (LEARN MODE ONLY)

After a label is correctly placed in learn mode, an info panel can slide in to provide additional context about the labeled structure. This is the "reward for correct placement" -- the student gets to learn more about what they just identified.

**IMPORTANT: This component must NEVER appear in test mode.** In test mode, revealing additional information about correctly-placed labels would compromise assessment validity by confirming correct answers and potentially helping with remaining labels.

#### Info Panel Anatomy

```
+-----------------------------------------------+
|  [STRUCTURE NAME]                    [X close] |
|-----------------------------------------------|
|  [THUMBNAIL / DIAGRAM HIGHLIGHT]              |
|                                               |
|  Brief description of the structure.          |
|  Function: What this structure does.          |
|  Clinical relevance: Why it matters.          |
|                                               |
|  Related structures: [tag] [tag] [tag]        |
+-----------------------------------------------+
```

#### Display Behavior

- Panel slides in from the right side (or bottom on mobile) over 300ms with an ease-out transition.
- Only one info panel is visible at a time. Placing a new label dismisses the previous panel and shows the new one.
- Panel auto-dismisses after 8 seconds (configurable) or when the user clicks/taps elsewhere.
- The underlying diagram area optionally highlights the relevant zone with a glow effect while the panel is open.

#### Configurable Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `info_panel_enabled` | `boolean` | `false` | Whether to show info panels (LEARN MODE ONLY) |
| `info_panel_position` | `'right' \| 'bottom' \| 'overlay'` | `'right'` | Where the panel appears |
| `info_panel_auto_dismiss_ms` | `number` | `8000` | Auto-dismiss timeout (0 = manual dismiss only) |
| `info_panel_content` | `Record<string, InfoContent>` | `{}` | Per-zone content: title, description, function, thumbnail_url |

### 2.7 Label Tray

The current LabelTray is a basic `flex-wrap` container with a heading. Premium labeling games use a more structured tray with grouping, scrolling, and progress indication.

#### Tray Layout Modes

| Layout | Description | Best For |
|--------|-------------|----------|
| `horizontal` | Labels in a single horizontal scrollable row below the diagram | Wide diagrams, few labels (< 10) |
| `vertical` | Labels in a vertical scrollable column to the right of the diagram | Tall diagrams, many labels (10+) |
| `grid` | Labels in a scrollable grid (2-3 columns) | Large label sets with thumbnails |
| `grouped` | Labels grouped by category with collapsible headers | Labels with natural categories (organs, bones, muscles) |

#### Tray Features

| Feature | Description |
|---------|-------------|
| Remaining count | Badge showing "X remaining" that counts down as labels are placed. Visible in tray header. |
| Category grouping | Labels grouped under collapsible section headers (e.g., "Arteries", "Veins", "Nerves"). Groups defined by `label_category` property. |
| Scroll indicators | Fade gradient at top/bottom (or left/right) edges when content is scrollable beyond the visible area. |
| Empty state | When all labels are placed, the tray shows a completion message with a checkmark. |
| Search/filter | For large label sets (20+), an optional text input that filters visible labels by substring match. |
| Distractor styling | Distractor labels (labels with no correct zone) are visually identical to correct labels in the tray. They are only distinguished after the student attempts to place them (they are rejected by all zones) or after submission (they are highlighted as distractors). |

#### Configurable Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `tray_position` | `'bottom' \| 'right' \| 'left' \| 'top'` | `'bottom'` | Where the label tray appears relative to the diagram |
| `tray_layout` | `'horizontal' \| 'vertical' \| 'grid' \| 'grouped'` | `'horizontal'` | Internal layout of labels within the tray |
| `tray_show_remaining` | `boolean` | `true` | Show remaining label count badge |
| `tray_show_categories` | `boolean` | `false` | Group labels by category |
| `tray_scrollable` | `boolean` | `true` | Enable scroll when labels overflow |
| `tray_search_enabled` | `boolean` | `false` | Show filter/search input (for 20+ labels) |
| `tray_max_visible` | `number` | `0` (unlimited) | Max visible labels before scroll (0 = show all) |

### 2.8 Distractor Labels

Distractor labels are incorrect labels that do not match any zone on the diagram. They are mixed into the label tray to increase assessment difficulty and prevent process-of-elimination strategies.

#### Distractor Design Principles

1. **Plausibility**: Distractors must be plausible alternatives to correct labels. "Xyz123" is not a distractor; "Pulmonary vein" (when the correct answer is "Pulmonary artery") is.
2. **Visual indistinguishability**: Distractors must look identical to correct labels in the tray. Same card type, same styling, same font. No visual cues that distinguish them before placement.
3. **Graceful rejection**: When a student drags a distractor to any zone, the zone should not accept it (if immediate feedback is enabled). The label bounces back to the tray. In deferred feedback mode, the distractor can be placed in any zone (it will be scored as incorrect on submission).
4. **Post-submission reveal**: After submission, distractors can be highlighted with a distinct style (e.g., strikethrough, gray-out, red "X" badge) and their explanation text displayed.

#### Configurable Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `show_distractors` | `boolean` | `false` | Whether to include distractor labels |
| `distractor_count` | `number` | `0` | Number of distractor labels to include |
| `distractor_rejection_mode` | `'immediate' \| 'deferred'` | `'immediate'` | When distractors are identified as wrong |
| `distractor_reveal_style` | `'strikethrough' \| 'grayout' \| 'badge' \| 'none'` | `'strikethrough'` | How distractors are visually marked post-submission |

---

## 3. Interaction Patterns

The current implementation supports only classic drag-and-drop. Premium labeling games offer multiple interaction patterns that test the same knowledge in different ways and accommodate different input modalities.

### 3.1 Classic Drag-and-Drop

The default mode. Labels live in a tray. The student picks up a label, drags it over the diagram, and drops it on a zone. If the zone accepts it, the label is placed. If not, the label returns to the tray.

**Touch behavior**: On touch devices, a long-press (200ms) initiates the drag. The label follows the finger. Releasing the finger over a valid zone places the label.

**Mouse behavior**: Click-and-hold initiates the drag. The label follows the cursor. Releasing over a valid zone places the label.

### 3.2 Click-to-Place (Accessibility Alternative)

The primary accessible alternative to drag-and-drop, as required by WCAG 2.5.7 (Dragging Movements). This mode replaces the continuous drag gesture with two discrete clicks/taps.

**Interaction flow:**
1. Student clicks/taps a label in the tray. The label becomes "selected" (highlighted border, slight scale-up).
2. Student clicks/taps a zone on the diagram. If the zone accepts the label, it is placed.
3. Clicking a different label while one is selected deselects the first and selects the new one.
4. Clicking an empty area deselects the current label.

**Keyboard flow (full keyboard navigation):**
1. Tab navigates between labels in the tray and zones on the diagram.
2. Enter/Space on a label selects it.
3. Tab to a zone, then Enter/Space places the selected label.
4. Escape deselects the current label.
5. Arrow keys can navigate between zones within the diagram (spatial navigation based on zone positions).

**Visual indicators:**
- Selected label in tray: Thicker border, primary color accent, slight scale-up (1.05x).
- Zone accepting a selected label: Subtle highlight (same as drag-over state).
- Screen reader announcements: "Label [name] selected. Tab to a zone and press Enter to place."

### 3.3 Reverse Mode (Zone-to-Label)

Instead of "pick a label, place it on a zone," reverse mode highlights a zone and asks the student to pick the correct label from the tray. This tests recognition from the opposite direction (location-to-name vs. name-to-location).

**Interaction flow:**
1. The system highlights one zone on the diagram (pulsing border, glow effect).
2. A prompt appears: "What structure is highlighted?"
3. The student clicks/taps the correct label from the tray.
4. If correct, the label is placed on the zone and the next zone is highlighted.
5. If incorrect, the label is rejected and the zone remains highlighted for another attempt.

**Zone highlighting sequence:**
- Sequential: Zones are highlighted in a fixed order (top-to-bottom, left-to-right, or by difficulty).
- Random: Zones are highlighted in random order.
- Adaptive: Zones the student previously got wrong are highlighted first.

**Visual treatment:**
- Highlighted zone: Pulsing border animation (2s cycle), fill with 20% opacity of the accent color, optional arrow pointing to the zone from the prompt text.
- Non-highlighted zones: Dimmed (50% opacity of normal zone display).

### 3.4 Label-from-Bank (No Tray, Type-In)

Instead of a drag tray, the student sees an empty text input attached to each zone. They type the label name. Autocomplete can optionally suggest from a word bank.

This mode is NOT drag-and-drop; it is a typing/recall mode. It is listed here because it is a common alternative interaction pattern for the same assessment objective (label identification) and may coexist with drag-drop in a multi-mode game.

### 3.5 Interaction Mode Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `interaction_mode` | `'drag_drop' \| 'click_to_place' \| 'reverse' \| 'label_from_bank'` | `'drag_drop'` | Primary interaction pattern |
| `allow_mode_switch` | `boolean` | `true` | Whether user can switch between drag_drop and click_to_place |
| `reverse_highlight_order` | `'sequential' \| 'random' \| 'adaptive'` | `'sequential'` | Zone highlighting order in reverse mode |
| `reverse_prompt_position` | `'top' \| 'overlay' \| 'inline'` | `'top'` | Where the "What structure?" prompt appears |

---

## 4. Full Configuration Schema

This section consolidates all configurable properties into a single schema that the pipeline can generate and the frontend can consume.

### 4.1 DragDropConfig (Blueprint-Level)

```typescript
interface DragDropConfig {
  // -- Interaction --
  interaction_mode: 'drag_drop' | 'click_to_place' | 'reverse' | 'label_from_bank';
  allow_mode_switch: boolean;
  feedback_timing: 'immediate' | 'deferred';

  // -- Zone rendering --
  zone_idle_animation: 'none' | 'pulse' | 'glow' | 'breathe';
  zone_hover_effect: 'highlight' | 'scale' | 'glow' | 'none';
  zone_stroke_style: 'solid' | 'dashed' | 'dotted' | 'none';
  zone_fill_opacity: number;

  // -- Label card --
  label_style: 'text' | 'text_with_icon' | 'text_with_thumbnail' | 'text_with_description';
  label_font_size: 'sm' | 'base' | 'lg';

  // -- Placement animation --
  placement_animation: 'spring' | 'ease' | 'instant' | 'none';
  spring_stiffness: number;
  spring_damping: number;
  incorrect_animation: 'shake' | 'bounce_back' | 'fade_out' | 'none';
  show_placement_particles: boolean;

  // -- Leader lines --
  leader_line_style: 'straight' | 'elbow' | 'curved' | 'fluid' | 'none';
  leader_line_color: string;
  leader_line_width: number;
  leader_line_dash: string | null;
  leader_line_animate: boolean;
  leader_line_animate_duration_ms: number;
  pin_marker_shape: 'circle' | 'diamond' | 'arrow' | 'none';
  pin_marker_size: number;
  label_anchor_side: 'auto' | 'left' | 'right' | 'top' | 'bottom';

  // -- Label tray --
  tray_position: 'bottom' | 'right' | 'left' | 'top';
  tray_layout: 'horizontal' | 'vertical' | 'grid' | 'grouped';
  tray_show_remaining: boolean;
  tray_show_categories: boolean;
  tray_scrollable: boolean;
  tray_search_enabled: boolean;

  // -- Distractors --
  show_distractors: boolean;
  distractor_count: number;
  distractor_rejection_mode: 'immediate' | 'deferred';

  // -- Zoom/pan --
  zoom_enabled: boolean;
  zoom_min: number;
  zoom_max: number;
  zoom_controls_visible: boolean;
  minimap_enabled: boolean;

  // -- Info panel (LEARN MODE ONLY) --
  info_panel_enabled: boolean;
  info_panel_position: 'right' | 'bottom' | 'overlay';
  info_panel_auto_dismiss_ms: number;

  // -- Reverse mode --
  reverse_highlight_order: 'sequential' | 'random' | 'adaptive';
  reverse_prompt_position: 'top' | 'overlay' | 'inline';
}
```

### 4.2 Default Configuration Presets

| Preset | Scenario | Key Overrides from Default |
|--------|----------|--------------------------|
| `minimal` | Simple diagram, 3-6 labels, young learners | `label_style: 'text'`, `leader_line_style: 'none'`, `zoom_enabled: false`, `show_distractors: false`, `tray_position: 'bottom'` |
| `standard` | Medium diagram, 6-12 labels | `leader_line_style: 'straight'`, `pin_marker_shape: 'circle'`, `placement_animation: 'spring'` |
| `anatomy` | Dense anatomy diagram, 10-20 labels | `leader_line_style: 'elbow'`, `label_anchor_side: 'right'`, `tray_position: 'right'`, `tray_layout: 'vertical'`, `zoom_enabled: true`, `label_style: 'text_with_icon'` |
| `geography` | Map labeling | `interaction_mode: 'click_to_place'`, `zone_shape: 'point'`, `leader_line_style: 'none'`, `tray_position: 'right'`, `tray_layout: 'vertical'` |
| `assessment` | Formal test mode | `feedback_timing: 'deferred'`, `show_distractors: true`, `info_panel_enabled: false`, `leader_line_style: 'none'` (no visual confirmation until submission) |

---

## 5. Pipeline Generation Requirements

For the AI pipeline to produce diagram labeling games with the components described above, it must generate specific data structures beyond the current zone/label schema.

### 5.1 Clean Diagram Image

The image pipeline (ImageLabelClassifier -> SmartInpainter) already produces a label-free diagram image. No changes needed here, but the image quality requirements for premium labeling are:

| Requirement | Detail |
|-------------|--------|
| Resolution | Minimum 800x600, recommended 1200x900 for zoom support |
| Label removal | All pre-existing text labels must be fully inpainted. Residual text fragments break the game. |
| Contrast | Zone boundaries must be visually distinguishable from the background at 1x zoom. Low-contrast diagrams (pencil sketches, light watermarks) need preprocessing. |
| Aspect ratio | Must be known and communicated to the frontend so zone percentage coordinates are accurate |

### 5.2 Zones with Shape Data

Each zone must include complete shape geometry, not just a center point.

```typescript
interface ZoneSpec {
  id: string;
  label: string;                              // Correct label text
  zone_type: 'point' | 'area';
  shape: 'circle' | 'polygon' | 'rect' | 'point';

  // Position (percentage 0-100)
  x: number;                                  // Center X
  y: number;                                  // Center Y

  // Shape-specific geometry
  radius?: number;                            // For circle: visual radius (%)
  hit_radius?: number;                        // Hit area radius (can be > visual radius)
  width?: number;                             // For rect: width (%)
  height?: number;                            // For rect: height (%)
  points?: [number, number][];                // For polygon: vertex coordinates (%)

  // Leader line anchor
  pin_anchor?: { x: number; y: number };      // Point on zone boundary for leader line attachment
  label_position?: { x: number; y: number };  // Suggested label card position (outside zone)

  // Metadata
  description?: string;                       // Structure description (LEARN MODE info panel)
  function?: string;                          // Structure function (LEARN MODE info panel)
  category?: string;                          // Category for tray grouping
  difficulty?: number;                        // 1-5
}
```

### 5.3 Labels with Correct Zone ID and Metadata

```typescript
interface LabelSpec {
  id: string;
  text: string;                               // Display text
  correct_zone_id: string;                    // Which zone this label belongs to
  icon?: string;                              // Icon for text_with_icon style
  thumbnail_url?: string;                     // Thumbnail for text_with_thumbnail style
  category?: string;                          // Category for tray grouping
  description?: string;                       // LEARN MODE ONLY: shown after correct placement
}
```

### 5.4 Distractor Labels

```typescript
interface DistractorLabelSpec {
  id: string;
  text: string;                               // Display text (must be plausible)
  explanation: string;                        // Why this is wrong (shown post-submission)
  confusion_target_zone_id?: string;          // Which zone this distractor is designed to confuse with
  category?: string;                          // Same category system as correct labels
}
```

### 5.5 Leader Line Anchors

The pipeline must generate pin anchor points for leader lines. For point zones, the anchor is the zone center. For area zones, the anchor should be a visually appropriate point on the boundary -- typically the point on the boundary closest to the label's suggested external position.

```typescript
interface LeaderLineAnchor {
  zone_id: string;
  pin_x: number;                              // Anchor point X (% of diagram)
  pin_y: number;                              // Anchor point Y (% of diagram)
  label_x: number;                            // Suggested label card position X
  label_y: number;                            // Suggested label card position Y
  preferred_style?: 'straight' | 'elbow' | 'curved';
}
```

The pipeline's zone detection agents (GeminiZoneDetector, SAM3, DirectStructureLocator) produce zone boundaries. The leader line anchor generation can be a post-processing step that:
1. For each zone, finds the centroid.
2. Determines the label placement side (left or right of diagram center, based on zone position).
3. Calculates the pin anchor as the boundary point closest to the label placement side.
4. Generates the label position at a consistent offset from the diagram edge.

### 5.6 DragDropConfig Generation

The game planner or interaction designer agent should generate a `DragDropConfig` object based on:
- **Diagram complexity**: Number of zones, density of zones, presence of overlapping structures.
- **Label count**: 3-6 labels = minimal preset. 6-12 = standard. 12+ = anatomy preset with zoom.
- **Subject domain**: Anatomy/biology = leader lines + icon labels. Geography = click-to-place + point zones.
- **Assessment context**: Test mode = deferred feedback + distractors. Learn mode = immediate feedback + info panels.

---

## 6. Accessibility

### 6.1 WCAG 2.5.7: Dragging Movements

WCAG 2.5.7 (Level AA, introduced in WCAG 2.2) requires that all functionality using dragging movements must have a single-pointer alternative that does not require dragging, unless dragging is essential.

For diagram labeling, dragging is NOT essential (the same functionality can be achieved with click-to-place). Therefore, the implementation MUST provide a click-to-place alternative.

**Implementation requirements:**
- `click_to_place` interaction mode must be available as a toggle (e.g., accessibility settings button).
- The toggle must be discoverable (not hidden in a settings menu three levels deep).
- The click-to-place mode must provide identical functionality to drag-and-drop (same labels, same zones, same feedback).

**Important distinction**: WCAG 2.5.7 requires a single-pointer alternative, not just a keyboard alternative. Touch-screen users who cannot perform drag gestures (motor impairments) need to be able to tap a label, then tap a zone. Keyboard-only access (Tab + Enter) is a separate requirement (WCAG 2.1.1 Keyboard) and is also needed, but does not satisfy 2.5.7 on its own.

### 6.2 Keyboard Navigation

| Key | Action |
|-----|--------|
| Tab | Move focus between label tray, diagram zones, and control buttons |
| Shift+Tab | Move focus in reverse order |
| Enter / Space | Select a label (if focused on tray) or place the selected label (if focused on zone) |
| Escape | Deselect the currently selected label |
| Arrow keys | Navigate between zones spatially (up/down/left/right based on zone positions) |
| Home / End | Jump to first/last zone |

### 6.3 Screen Reader Announcements

| Event | Announcement |
|-------|-------------|
| Label selected | "[Label text] selected. Use Tab to navigate to a zone, then press Enter to place." |
| Label placed (correct, immediate feedback) | "[Label text] placed correctly on [zone label]." |
| Label placed (incorrect, immediate feedback) | "[Label text] is incorrect for this zone. Label returned to tray." |
| Label placed (deferred feedback) | "[Label text] placed on zone [index]." |
| All labels placed | "All labels placed. [X] of [Y] correct." (or "Ready to submit" in deferred mode) |
| Zone focused | "Zone [index] of [total]: [zone label]. [status]." |

### 6.4 Motion Sensitivity

All animations (spring snaps, shake feedback, leader line draw-on, zone pulses) must respect `prefers-reduced-motion`. When the user's OS setting indicates reduced motion:
- Spring animations become instant transitions.
- Shake feedback becomes a color flash only.
- Leader lines appear instantly without draw-on animation.
- Zone pulse/glow animations are disabled.

---

## 7. Component Summary Matrix

| Component | New/Existing | Priority | Complexity | Description |
|-----------|-------------|----------|------------|-------------|
| **LeaderLineOverlay** | NEW | High | Medium | Full-canvas SVG overlay drawing lines from placed labels to zone anchors |
| **EnhancedLabelCard** | Upgrade of DraggableLabel | High | Low | Rich label cards with icon, thumbnail, and description slots |
| **AnimatedSnap** | NEW | High | Medium | Spring physics animation system for placement feedback |
| **EnhancedLabelTray** | Upgrade of LabelTray | Medium | Low | Grouped, scrollable, categorized tray with remaining count |
| **ZoomPanCanvas** | NEW wrapper | Medium | Medium | Wraps DiagramCanvas with react-zoom-pan-pinch for zoom/pan support |
| **InfoPanel** | NEW | Low | Low | Slide-in panel showing structure details (LEARN MODE ONLY) |
| **ReverseMode** | NEW interaction | Low | Medium | Zone-highlights-first interaction pattern |
| **ClickToPlace** | Partially exists | High | Low | Complete the keyboard + click-to-place interaction mode |
| **DistractorManager** | Logic enhancement | Medium | Low | Mixing, rejection, and post-submission reveal of distractor labels |
| **PinMarker** | NEW | Medium | Low | Small SVG markers (circle, diamond, arrow) at leader line anchor points |

---

## 8. Current Codebase Gaps

Based on analysis of the existing implementation:

| Gap | Current State | Required State |
|-----|--------------|----------------|
| Leader lines | Not implemented | LeaderLineOverlay component with configurable styles |
| Label card types | Text-only pill (DraggableLabel.tsx) | Four card types with icon, thumbnail, description slots |
| Snap animation | CSS `transition-all duration-200` (no spring physics) | Framer Motion spring animation with configurable stiffness/damping |
| Zoom/pan | Not implemented | react-zoom-pan-pinch wrapper around DiagramCanvas |
| Label tray layout | Single `flex-wrap` container | Four layout modes (horizontal, vertical, grid, grouped) with scroll |
| Tray remaining count | Not shown | Badge in tray header |
| Distractor labels | Type exists in schema (DistractorLabel) but not rendered differently | Mixed into tray, rejected on placement or scored on submission |
| Click-to-place | Keyboard support exists (Enter/Space on zones) | Full click-to-place mode with visual selected-label state |
| Reverse mode | Not implemented | Zone highlight -> pick label interaction flow |
| Info panel | Not implemented | Slide-in panel for learn mode |
| Pin markers | Not implemented | SVG markers at leader line zone anchors |
| DragDropConfig | Not in schema | Full config interface consumed by components |
| Zone idle animation | None | Configurable pulse/glow/breathe for empty zones |
| Incorrect placement animation | CSS `animate-shake` class | Spring-based bounce-back to tray |
| Label tray categories | `label_category` not used | Grouped rendering with collapsible headers |
| Motion sensitivity | Not checked | `prefers-reduced-motion` media query respected |

---

## 9. Implementation Priority

### Phase 1: Core Visual Upgrades (Highest impact, moderate effort)
1. **LeaderLineOverlay** -- The single biggest visual upgrade. Draw SVG paths from placed labels to zone pin points.
2. **AnimatedSnap** -- Replace CSS transitions with spring physics (Framer Motion). Configure correct/incorrect animations.
3. **EnhancedLabelTray** -- Add remaining count badge, scrollable overflow, and category grouping.

### Phase 2: Interaction Alternatives (Accessibility + engagement)
4. **ClickToPlace** -- Complete the click-to-place mode with full visual feedback and WCAG 2.5.7 compliance.
5. **ReverseMode** -- Zone-highlights-first interaction pattern as an alternative assessment mode.
6. **DistractorManager** -- Mix distractors into the tray, handle rejection, reveal post-submission.

### Phase 3: Rich Content (Polish + depth)
7. **EnhancedLabelCard** -- Add icon, thumbnail, and description card types.
8. **ZoomPanCanvas** -- Wrap DiagramCanvas with zoom/pan for dense diagrams.
9. **InfoPanel** -- Slide-in structure details panel for learn mode.
10. **PinMarker** -- Small SVG markers at leader line anchor points.

### Phase 4: Pipeline Integration
11. **DragDropConfig generation** -- Add config generation to game_planner/interaction_designer agents.
12. **Leader line anchor generation** -- Post-processing step in blueprint assembler to calculate pin anchors.
13. **Distractor label generation** -- Domain knowledge retriever produces plausible distractors with explanations.
14. **Label metadata generation** -- Icons, thumbnails, categories from domain knowledge.
