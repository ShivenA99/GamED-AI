# V4 Pipeline Implementation Plan (Revised — Frontend-First)

**Date**: 2026-02-12
**Status**: Active implementation
**Approach**: Frontend-first. Build rich game components → derive DSL from what we built → build pipeline to produce it.

---

## Why This Order

The original V4 plan (saved in `docs/audit/28_v4_pipeline_implementation_plan.md`) defined the Game Specification DSL first, then built the pipeline, then expected the frontend to consume it. That's backwards.

The research docs (`docs/audit/research/01-07`) define 300K+ characters of component specs, config interfaces, and data models per mechanic. Current frontend implements only 10-30% of what those docs specify. If we define the DSL before building the rich frontend, we'll define the wrong shape and have to redo it.

**Corrected order:**
1. **Phase A**: Build each mechanic's frontend to full richness, one at a time. Test with hardcoded data. Verify playable quality.
2. **Phase B**: Derive the Game Specification DSL from the exact data shapes the rich frontend actually consumed.
3. **Phase C**: Build mechanic contracts, remove drag_drop bias, build V4 pipeline agents to produce exactly those shapes.

Each phase plan is written AFTER the previous phase is verified. The scope of each phase grows as we learn from building.

---

## Build Order (Priority 6, then Deferred 3)

From `docs/audit/15_comprehensive_fix_plan.md`:

| # | Mechanic | Research Doc | Why This Order |
|---|----------|-------------|----------------|
| 1 | **drag_drop** | `research/07_drag_drop_richness.md` | Most mature, most users, upgrade from baseline |
| 2 | **sequencing** | `research/01_sequencing_games.md` | No diagram needed, most different from current pipeline |
| 3 | **sorting_categories** | `research/03_sorting_categorization_games.md` | No diagram needed, 5 sort modes to build |
| 4 | **memory_match** | `research/02_memory_match_games.md` | No diagram needed, 5 game variants |
| 5 | **click_to_identify** | `research/06_click_trace_description_games.md` §1 | Diagram-based, 5 new components |
| 6 | **trace_path** | `research/06_click_trace_description_games.md` §2 | Diagram-based, particle system, most complex |
| D1 | description_matching | `research/06_click_trace_description_games.md` §3 | Deferred |
| D2 | compare_contrast | `research/05_compare_contrast_games.md` | Deferred |
| D3 | branching_scenario | `research/04_branching_scenario_games.md` | Deferred |

---

## Phase A: Frontend Component Expansion

### Process Per Mechanic

For each mechanic (one at a time, in order above):

```
Step 1: Read research doc → understand every component, config prop, data shape
Step 2: Build/upgrade frontend components per research spec
Step 3: Create hardcoded test fixture JSON that exercises ALL features
Step 4: Create a test page (or use existing /test-game) that renders the fixture
Step 5: Verify in browser — is this a quality, playable game?
Step 6: Document the exact data shape consumed → this becomes the mechanic's DSL input
Step 7: Move to next mechanic
```

### A1: drag_drop — Leader Lines, Spring Physics, Rich Labels

**Research doc**: `research/07_drag_drop_richness.md` (51K chars)

**What exists today**:
- `DraggableLabel.tsx` — text-only pill with basic dnd-kit drag
- `DropZone.tsx` — dashed rectangle/circle/polygon outline
- `LabelTray.tsx` — single `flex-wrap` container
- `DiagramCanvas.tsx` — renders zones + labels over image
- CSS `transition-all duration-200` for snap (no spring physics)
- No leader lines, no pin markers, no zoom/pan, no label categories, no distractor rendering

**New components to build** (10 components):

| Component | Priority | Description |
|-----------|----------|-------------|
| `LeaderLineOverlay` | HIGH | Full-canvas SVG overlay: straight/elbow/curved/fluid lines from placed labels to zone pin points. Draw-on animation via stroke-dasharray. |
| `EnhancedLabelCard` | HIGH | Upgrade DraggableLabel: 4 card types (text, text+icon, text+thumbnail, text+description). 7 visual states (idle, hover, grabbed, dragging, placed, incorrect, disabled). |
| `AnimatedSnap` | HIGH | Framer Motion spring physics for placement. Configurable stiffness/damping. Bounce-back on incorrect. |
| `PinMarker` | MEDIUM | Small SVG markers (circle/diamond/arrow) at leader line zone anchor points. |
| `EnhancedLabelTray` | MEDIUM | Grouped by category, scrollable, remaining count badge, 4 layouts (horizontal/vertical/grid/grouped). Search filter for large label sets. |
| `ZoomPanCanvas` | MEDIUM | react-zoom-pan-pinch wrapper around DiagramCanvas. Min/max zoom, minimap, zoom controls. |
| `ClickToPlaceMode` | HIGH | Complete click-to-place interaction: click label → click zone. No dragging. Accessibility alternative. |
| `DistractorManager` | MEDIUM | Mix distractor labels into tray. Reject on placement (immediate mode) or reveal on submit (deferred mode). |
| `InfoPanel` | LOW | Slide-in panel showing structure details after correct placement. Learn mode only. |
| `ReverseMode` | LOW | Zone-highlights-first interaction: zone glows → student picks label from bank. |

**DragDropConfig interface** (full — 40+ fields):

```typescript
interface DragDropConfig {
  // Interaction
  interaction_mode: 'drag_drop' | 'click_to_place' | 'reverse';
  feedback_timing: 'immediate' | 'deferred';

  // Zone rendering
  zone_idle_animation: 'none' | 'pulse' | 'glow' | 'breathe';
  zone_hover_effect: 'highlight' | 'scale' | 'glow' | 'none';

  // Label card
  label_style: 'text' | 'text_with_icon' | 'text_with_thumbnail' | 'text_with_description';

  // Placement animation
  placement_animation: 'spring' | 'ease' | 'instant';
  spring_stiffness: number;
  spring_damping: number;
  incorrect_animation: 'shake' | 'bounce_back' | 'fade_out';
  show_placement_particles: boolean;

  // Leader lines
  leader_line_style: 'straight' | 'elbow' | 'curved' | 'fluid' | 'none';
  leader_line_color: string;
  leader_line_width: number;
  leader_line_animate: boolean;
  pin_marker_shape: 'circle' | 'diamond' | 'arrow' | 'none';
  label_anchor_side: 'auto' | 'left' | 'right' | 'top' | 'bottom';

  // Label tray
  tray_position: 'bottom' | 'right' | 'left' | 'top';
  tray_layout: 'horizontal' | 'vertical' | 'grid' | 'grouped';
  tray_show_remaining: boolean;
  tray_show_categories: boolean;

  // Distractors
  show_distractors: boolean;
  distractor_count: number;
  distractor_rejection_mode: 'immediate' | 'deferred';

  // Zoom/pan
  zoom_enabled: boolean;
  zoom_min: number;
  zoom_max: number;
  minimap_enabled: boolean;

  // Max attempts
  max_attempts: number;
  shuffle_labels: boolean;
}
```

**Test fixture data shape** (what the hardcoded JSON must provide):
- `diagram.assetUrl`, `diagram.width`, `diagram.height`
- `diagram.zones[]` — each with `id`, `label`, `shape`, `x`, `y`, coordinates, `pin_anchor`, `label_position`, `category`, `description`, `function`
- `labels[]` — each with `id`, `text`, `correct_zone_id`, `icon`, `thumbnail_url`, `category`, `description`
- `distractorLabels[]` — each with `id`, `text`, `explanation`, `confusion_target_zone_id`
- `leaderLineAnchors[]` — per-zone `pin_x`, `pin_y`, `label_x`, `label_y`, `preferred_style`
- `dragDropConfig` — full config object above

**Verification criteria**:
- Leader lines draw on with animation when label placed correctly
- Spring physics snap animation visible on placement
- Incorrect placement bounces label back to tray with shake
- Zoom/pan works on diagram
- Label tray grouped by category with remaining count
- Distractor labels mixed in, rejected with explanation
- Click-to-place mode works without any dragging

---

### A2: sequencing — Rich Cards, Timeline Track, Connectors

**Research doc**: `research/01_sequencing_games.md` (27K chars)

**What exists today**:
- `SequenceBuilder.tsx` — vertical sortable list with plain text rows and drag handle icon
- dnd-kit `SortableContext` for reordering
- No card layout, no track visualization, no connectors, no slots, no images

**New components to build** (9+ components):

| Component | Priority | Description |
|-----------|----------|-------------|
| `SequenceItemCard` | HIGH | Rich card: image area, title, description, category accent. 5 card types. Drag states. |
| `SequenceTrack` | HIGH | Visual track lane. 5 layouts: horizontal/vertical timeline, circular, flowchart, insert_between. |
| `SequenceSlot` | HIGH | Drop target slot. 6 styles. States: idle, drag-nearby, hover, occupied, locked. |
| `SequenceConnector` | HIGH | SVG arrows/lines between placed cards. 5 styles. Animate-in on placement. |
| `SequenceSourceArea` | MEDIUM | Card tray/pool. 4 layouts. |
| `CircularTrack` | MEDIUM | Circular/cyclic layout for life cycles, water cycles. |
| `InsertBetweenController` | MEDIUM | Insert cards between existing ones. |
| `ClickToPlaceSequence` | MEDIUM | Tap items in order. |
| `ProgressiveReveal` | LOW | Draw-pile progressive card reveal. |

---

### A3: sorting_categories — Buckets, Venn Diagrams, Matrix Grid

**Research doc**: `research/03_sorting_categorization_games.md` (40K chars)

**New components**: 12+ including BucketContainer, SortingItemCard, ItemPool, VennDiagram2, VennDiagram3, MatrixGrid, ColumnSort, ClickToPlaceSort, IterativeCorrection, MultiCategoryPlacer, StaggeredReveal, CategoryCelebration.

---

### A4: memory_match — 3D Flip, Game Variants, Explanation Reveal

**Research doc**: `research/02_memory_match_games.md` (30K chars)

**New components**: 15+ including FlipCard, CardFace renderers (5), CardBack renderers (4), ColumnMatchView, ScatterView, ProgressiveWrapper, ExplanationOverlay, MatchParticles, StatsBar.

---

### A5: click_to_identify — Prompt Banner, Zone States, Magnification

**Research doc**: `research/06_click_trace_description_games.md` §1

**New components**: 6 including PromptBanner, ZoneHighlightStateMachine, MagnificationLens, ExploreTestController, SelectionModeController, ZoneHighlightConfig.

---

### A6: trace_path — Particle System, Curved Paths, Color Transitions

**Research doc**: `research/06_click_trace_description_games.md` §2

**New components**: 8 including SVGPathDefinitionLayer, AnimatedParticleSystem, ColorTransitionEngine, DirectionalArrowOverlay, WaypointZoneMarker, GateValveAnimation, FreehandDrawingCanvas, DrawingModeController.

---

## Phase B: Game Specification DSL

**When**: After all 6 priority mechanics are built and verified.

**Process**:
1. Collect exact data shapes consumed by each rich frontend component
2. Create unified `GameSpecification` Pydantic model (backend) from those shapes
3. Create Zod mirror schema (frontend) for runtime validation
4. Write tests: for each mechanic, take the hardcoded test fixture from Phase A, validate against both Pydantic and Zod schemas
5. Define `to_frontend_json()` that converts GameSpecification → the shape each component expects

---

## Phase C: Pipeline Rearchitecture

**When**: After Phase B DSL is defined and validated.

Covers:
- C1: Mechanic Contract Registry
- C2: drag_drop Bias Eradication
- C3: V4 Subgraph Architecture
- C4: Incremental GameState
- C5: Asset Tools Per Mechanic
- C6: Hierarchical as Composable Mode
- C7: Token Optimization

---

## Phase D: Game Rule Engine (Frontend)

**When**: Can start in parallel with Phase C.

Covers:
- json-rules-engine integration
- Custom operator registry per mechanic
- Rule evaluator hook wired to Zustand store
- Backend rule templates per mechanic
- Declarative scoring/feedback/completion

---

## Key References

| Document | Content |
|----------|---------|
| `docs/audit/research/07_drag_drop_richness.md` | drag_drop component specs (51K) |
| `docs/audit/research/01_sequencing_games.md` | sequencing component specs (27K) |
| `docs/audit/research/03_sorting_categorization_games.md` | sorting component specs (40K) |
| `docs/audit/research/02_memory_match_games.md` | memory match component specs (30K) |
| `docs/audit/research/06_click_trace_description_games.md` | click/trace/description specs (46K) |
| `docs/audit/research/05_compare_contrast_games.md` | compare contrast specs (53K, deferred) |
| `docs/audit/research/04_branching_scenario_games.md` | branching specs (51K, deferred) |
| `docs/audit/28_v4_pipeline_implementation_plan.md` | Original V4 plan (pipeline-first, for reference) |
| `docs/audit/15_comprehensive_fix_plan.md` | Priority mechanics and architecture principles |
