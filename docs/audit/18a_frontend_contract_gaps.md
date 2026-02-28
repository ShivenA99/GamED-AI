# Frontend-Backend Contract Gap Analysis — V4 Pipeline

**Date**: 2026-02-14
**Purpose**: Identify every field mismatch between frontend TypeScript types and V4 backend Pydantic schemas
**Scope**: All 10 mechanic types + root blueprint fields

---

## Executive Summary

### Critical Findings

1. **MechanicCreativeDesign carries ZERO frontend-specific config fields** — All visual config (card_type, layout_mode, connector_style, etc.) live in MechanicCreativeDesign but frontend expects them in per-mechanic config objects
2. **Massive duplication** — Every frontend config has instruction/layout/visual fields that MechanicCreativeDesign already has
3. **Frontend expects scoring/feedback at mechanic.config level** — V4 has them at SceneContent.scoring/feedback (separate arrays)
4. **V4 has NO TYPES for mechanic.config payload** — MechanicCreativeDesign is art direction, not frontend config
5. **Frontend zone/label format incompatibility** — Frontend expects zone.points as [[x,y],...]; V4 DetectedZone.coordinates is Dict[str, Any]

### Gap Categories

| Category | Count | Severity |
|----------|-------|----------|
| Missing visual config fields | 47 | CRITICAL |
| Missing scoring/feedback in config | 20 | CRITICAL |
| Instruction text duplication | 10 | HIGH |
| Type mismatches (coordinates, IDs) | 8 | HIGH |
| Unused V4 fields (waste) | 12 | MEDIUM |
| Missing distractor support | 4 | MEDIUM |

---

## 1. Drag & Drop

### Frontend Type: `DragDropConfig`

```typescript
interface DragDropConfig {
  // Interaction
  interaction_mode?: 'drag_drop' | 'click_to_place' | 'reverse';
  feedback_timing?: 'immediate' | 'deferred';

  // Zone rendering
  zone_idle_animation?: 'none' | 'pulse' | 'glow' | 'breathe';
  zone_hover_effect?: 'highlight' | 'scale' | 'glow' | 'none';

  // Label card
  label_style?: 'text' | 'text_with_icon' | 'text_with_thumbnail' | 'text_with_description';

  // Placement animation
  placement_animation?: 'spring' | 'ease' | 'instant';
  spring_stiffness?: number;
  spring_damping?: number;
  incorrect_animation?: 'shake' | 'bounce_back' | 'fade_out';
  show_placement_particles?: boolean;

  // Leader lines
  leader_line_style?: 'straight' | 'elbow' | 'curved' | 'fluid' | 'none';
  leader_line_color?: string;
  leader_line_width?: number;
  leader_line_animate?: boolean;
  pin_marker_shape?: 'circle' | 'diamond' | 'arrow' | 'none';
  label_anchor_side?: 'auto' | 'left' | 'right' | 'top' | 'bottom';

  // Label tray
  tray_position?: 'bottom' | 'right' | 'left' | 'top';
  tray_layout?: 'horizontal' | 'vertical' | 'grid' | 'grouped';
  tray_show_remaining?: boolean;
  tray_show_categories?: boolean;

  // Distractors
  show_distractors?: boolean;
  distractor_count?: number;
  distractor_rejection_mode?: 'immediate' | 'deferred';

  // Zoom/pan
  zoom_enabled?: boolean;
  zoom_min?: number;
  zoom_max?: number;
  minimap_enabled?: boolean;

  // Max attempts
  max_attempts?: number;
  shuffle_labels?: boolean;
}
```

### V4 Backend: `DragDropContent` + `MechanicCreativeDesign`

**DragDropContent** (from `MechanicContent.drag_drop`):
```python
class DragDropContent(BaseModel):
    labels: List[Dict[str, str]]  # [{text, zone_label}]
    distractor_labels: List[str] = []
```

**MechanicCreativeDesign** (from `SceneCreativeDesign.mechanic_designs`):
```python
class MechanicCreativeDesign(BaseModel):
    mechanic_type: str
    visual_style: str                    # "clean_labels_with_pins"
    card_type: str = "text_only"         # MATCHES label_style
    layout_mode: str = "default"         # NOT USED BY DRAG_DROP
    connector_style: str = "arrow"       # NOT USED (leader_line_style separate)
    color_direction: str = ""
    instruction_text: str
    instruction_tone: str = "educational"
    narrative_hook: str = ""
    hint_strategy: str = "progressive"
    feedback_style: str = "encouraging"
    difficulty_curve: str = "gradual"
    generation_goal: str
    key_concepts: List[str] = []
    pedagogical_focus: str = ""
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `interaction_mode` | ❌ MISSING | **GAP** | No backend field |
| `feedback_timing` | ❌ MISSING | **GAP** | No backend field |
| `zone_idle_animation` | ❌ MISSING | **GAP** | No backend field |
| `zone_hover_effect` | ❌ MISSING | **GAP** | No backend field |
| `label_style` | `card_type` | ✅ MATCH | card_type maps to label_style |
| `placement_animation` | ❌ MISSING | **GAP** | No backend field |
| `spring_stiffness` | ❌ MISSING | **GAP** | No backend field |
| `spring_damping` | ❌ MISSING | **GAP** | No backend field |
| `incorrect_animation` | ❌ MISSING | **GAP** | No backend field |
| `show_placement_particles` | ❌ MISSING | **GAP** | No backend field |
| `leader_line_style` | ❌ MISSING | **GAP** | connector_style doesn't match semantics |
| `leader_line_color` | ❌ MISSING | **GAP** | No backend field |
| `leader_line_width` | ❌ MISSING | **GAP** | No backend field |
| `leader_line_animate` | ❌ MISSING | **GAP** | No backend field |
| `pin_marker_shape` | ❌ MISSING | **GAP** | No backend field |
| `label_anchor_side` | ❌ MISSING | **GAP** | No backend field |
| `tray_position` | ❌ MISSING | **GAP** | No backend field |
| `tray_layout` | ❌ MISSING | **GAP** | No backend field |
| `tray_show_remaining` | ❌ MISSING | **GAP** | No backend field |
| `tray_show_categories` | ❌ MISSING | **GAP** | No backend field |
| `show_distractors` | `distractor_labels` | ⚠️ PARTIAL | V4 has distractor_labels list, not boolean flag |
| `distractor_count` | ❌ MISSING | **GAP** | Implicitly len(distractor_labels) |
| `distractor_rejection_mode` | ❌ MISSING | **GAP** | No backend field |
| `zoom_enabled` | ❌ MISSING | **GAP** | No backend field |
| `zoom_min` | ❌ MISSING | **GAP** | No backend field |
| `zoom_max` | ❌ MISSING | **GAP** | No backend field |
| `minimap_enabled` | ❌ MISSING | **GAP** | No backend field |
| `max_attempts` | ❌ MISSING | **GAP** | No backend field |
| `shuffle_labels` | ❌ MISSING | **GAP** | No backend field |

**Total gaps: 26 / 29 fields missing**

### Unused V4 Fields (WASTE)

| V4 Field | Why Unused |
|----------|-----------|
| `visual_style` | Frontend doesn't consume (UI ignores) |
| `layout_mode` | Not applicable to drag_drop |
| `connector_style` | Separate from leader_line_style |
| `instruction_tone` | Not consumed by frontend |
| `narrative_hook` | Not consumed by frontend |
| `hint_strategy` | Stored in separate feedback config |
| `feedback_style` | Stored in separate feedback config |
| `difficulty_curve` | Not consumed by frontend |
| `generation_goal` | Internal, not sent to frontend |
| `key_concepts` | Internal, not sent to frontend |
| `pedagogical_focus` | Internal, not sent to frontend |

---

## 2. Click to Identify

### Frontend Type: `ClickToIdentifyConfig`

```typescript
interface ClickToIdentifyConfig {
  promptStyle: 'naming' | 'functional';
  selectionMode: 'sequential' | 'any_order';
  highlightStyle: 'subtle' | 'outlined' | 'invisible';
  magnificationEnabled?: boolean;
  magnificationFactor?: number;
  exploreModeEnabled?: boolean;
  exploreTimeLimitSeconds?: number | null;
  showZoneCount?: boolean;
  instructions?: string;
}
```

### V4 Backend: `ClickToIdentifyContent` + `MechanicCreativeDesign`

```python
class ClickPrompt(BaseModel):
    zone_label: str
    prompt_text: str
    order: int

class ClickToIdentifyContent(BaseModel):
    prompts: List[ClickPrompt]
    prompt_style: str = "naming"          # MATCHES promptStyle
    selection_mode: str = "sequential"    # MATCHES selectionMode
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `promptStyle` | `prompt_style` | ✅ MATCH | snake_case vs camelCase |
| `selectionMode` | `selection_mode` | ✅ MATCH | snake_case vs camelCase |
| `highlightStyle` | ❌ MISSING | **GAP** | No backend field |
| `magnificationEnabled` | ❌ MISSING | **GAP** | No backend field |
| `magnificationFactor` | ❌ MISSING | **GAP** | No backend field |
| `exploreModeEnabled` | ❌ MISSING | **GAP** | No backend field |
| `exploreTimeLimitSeconds` | ❌ MISSING | **GAP** | No backend field |
| `showZoneCount` | ❌ MISSING | **GAP** | No backend field |
| `instructions` | `instruction_text` | ⚠️ PARTIAL | In MechanicCreativeDesign, not ClickToIdentifyContent |

**Total gaps: 6 / 9 fields missing**

---

## 3. Trace Path

### Frontend Type: `TracePathConfig`

```typescript
interface TracePathConfig {
  pathType: 'linear' | 'branching' | 'circular';
  drawingMode: 'click_waypoints' | 'freehand';
  particleTheme: 'dots' | 'arrows' | 'droplets' | 'cells' | 'electrons';
  particleSpeed: 'slow' | 'medium' | 'fast';
  colorTransitionEnabled?: boolean;
  showDirectionArrows?: boolean;
  showWaypointLabels?: boolean;
  showFullFlowOnComplete?: boolean;
  instructions?: string;
  submitMode?: 'immediate' | 'batch';
}
```

### V4 Backend: `TracePathContent` + `MechanicCreativeDesign`

```python
class TraceWaypoint(BaseModel):
    zone_label: str
    order: int

class TracePath(BaseModel):
    id: str
    description: str = ""
    requires_order: bool = True
    waypoints: List[TraceWaypoint]

class TracePathContent(BaseModel):
    paths: List[TracePath]
    path_type: str = "linear"            # MATCHES pathType
    drawing_mode: str = "click_waypoints" # MATCHES drawingMode
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `pathType` | `path_type` | ✅ MATCH | snake_case vs camelCase |
| `drawingMode` | `drawing_mode` | ✅ MATCH | snake_case vs camelCase |
| `particleTheme` | ❌ MISSING | **GAP** | No backend field |
| `particleSpeed` | ❌ MISSING | **GAP** | No backend field |
| `colorTransitionEnabled` | ❌ MISSING | **GAP** | No backend field |
| `showDirectionArrows` | ❌ MISSING | **GAP** | No backend field |
| `showWaypointLabels` | ❌ MISSING | **GAP** | No backend field |
| `showFullFlowOnComplete` | ❌ MISSING | **GAP** | No backend field |
| `instructions` | `instruction_text` | ⚠️ PARTIAL | In MechanicCreativeDesign, not TracePathContent |
| `submitMode` | ❌ MISSING | **GAP** | No backend field |

**Total gaps: 7 / 10 fields missing**

---

## 4. Sequencing

### Frontend Type: `SequenceConfig`

```typescript
interface SequenceConfigItem {
  id: string;
  text: string;
  description?: string;
  image?: string;
  icon?: string;
  category?: string;
  is_distractor?: boolean;
  order_index?: number;
}

interface SequenceConfig {
  sequenceType: 'linear' | 'cyclic' | 'branching';
  items: SequenceConfigItem[];
  correctOrder: string[];
  allowPartialCredit?: boolean;
  instructionText?: string;
  layout_mode?: 'horizontal_timeline' | 'vertical_list' | 'circular_cycle' | 'flowchart' | 'insert_between';
  interaction_pattern?: 'drag_reorder' | 'drag_to_slots' | 'click_to_swap' | 'number_typing';
  card_type?: 'text_only' | 'text_with_icon' | 'image_with_caption' | 'image_only';
  connector_style?: 'arrow' | 'line' | 'numbered' | 'none';
  show_position_numbers?: boolean;
}
```

### V4 Backend: `SequencingContent` + `MechanicCreativeDesign`

```python
class SequenceItem(BaseModel):
    id: str                               # MATCHES
    text: str                             # MATCHES
    description: str = ""                 # MATCHES
    icon: str = ""                        # MATCHES
    order_index: int                      # MATCHES
    is_distractor: bool = False           # MATCHES
    image_description: Optional[str] = None  # ⚠️ NOT URL (need to resolve from item images)

class SequencingContent(BaseModel):
    items: List[SequenceItem]             # MATCHES
    correct_order: List[str]              # MATCHES
    sequence_type: str = "linear"         # MATCHES
    instruction_text: str = ""            # MATCHES
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `sequenceType` | `sequence_type` | ✅ MATCH | snake_case vs camelCase |
| `items[].id` | `items[].id` | ✅ MATCH | — |
| `items[].text` | `items[].text` | ✅ MATCH | — |
| `items[].description` | `items[].description` | ✅ MATCH | — |
| `items[].image` | `items[].image_description` | ⚠️ PARTIAL | V4 has description, not URL (needs asset resolution) |
| `items[].icon` | `items[].icon` | ✅ MATCH | — |
| `items[].category` | ❌ MISSING | **GAP** | No backend field |
| `items[].is_distractor` | `items[].is_distractor` | ✅ MATCH | — |
| `items[].order_index` | `items[].order_index` | ✅ MATCH | — |
| `correctOrder` | `correct_order` | ✅ MATCH | snake_case vs camelCase |
| `allowPartialCredit` | ❌ MISSING | **GAP** | Should be in MechanicScoring, not content |
| `instructionText` | `instruction_text` | ✅ MATCH | — |
| `layout_mode` | `layout_mode` | ⚠️ PARTIAL | In MechanicCreativeDesign, not SequencingContent |
| `interaction_pattern` | ❌ MISSING | **GAP** | No backend field |
| `card_type` | `card_type` | ⚠️ PARTIAL | In MechanicCreativeDesign, not SequencingContent |
| `connector_style` | `connector_style` | ⚠️ PARTIAL | In MechanicCreativeDesign, not SequencingContent |
| `show_position_numbers` | ❌ MISSING | **GAP** | No backend field |

**Total gaps: 5 / 16 fields missing**
**Partial matches: 4 fields in wrong schema (MechanicCreativeDesign vs SequencingContent)**

---

## 5. Sorting Categories

### Frontend Type: `SortingConfig`

```typescript
interface SortingItem {
  id: string;
  text: string;
  correctCategoryId: string;
  correct_category_ids?: string[];  // Multi-category support
  description?: string;
  image?: string;
  difficulty?: 'easy' | 'medium' | 'hard';
}

interface SortingCategory {
  id: string;
  label: string;
  description?: string;
  color?: string;
}

interface SortingConfig {
  items: SortingItem[];
  categories: SortingCategory[];
  allowPartialCredit?: boolean;
  showCategoryHints?: boolean;
  instructions?: string;
  sort_mode?: 'bucket' | 'venn_2' | 'venn_3' | 'matrix' | 'column';
  item_card_type?: 'text_only' | 'text_with_icon' | 'image_with_caption';
  container_style?: 'bucket' | 'labeled_bin' | 'circle' | 'cell' | 'column';
  submit_mode?: 'batch_submit' | 'immediate_feedback' | 'round_based';
  allow_multi_category?: boolean;
}
```

### V4 Backend: `SortingContent` + `MechanicCreativeDesign`

```python
class SortingCategory(BaseModel):
    id: str                               # MATCHES
    label: str                            # MATCHES
    description: str = ""                 # MATCHES
    color: Optional[str] = None           # MATCHES

class SortingItem(BaseModel):
    id: str                               # MATCHES
    text: str                             # MATCHES
    correct_category_id: str              # MATCHES
    correct_category_ids: List[str] = []  # MATCHES
    description: str = ""                 # MATCHES
    image_description: Optional[str] = None  # ⚠️ NOT URL
    difficulty: str = "medium"            # MATCHES

class SortingContent(BaseModel):
    categories: List[SortingCategory]     # MATCHES
    items: List[SortingItem]              # MATCHES
    instruction_text: str = ""            # MATCHES
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `items` | `items` | ✅ MATCH | — |
| `items[].image` | `items[].image_description` | ⚠️ PARTIAL | V4 has description, not URL |
| `categories` | `categories` | ✅ MATCH | — |
| `categories[].color` | `categories[].color` | ✅ MATCH | — |
| `allowPartialCredit` | ❌ MISSING | **GAP** | Should be in MechanicScoring |
| `showCategoryHints` | ❌ MISSING | **GAP** | No backend field |
| `instructions` | `instruction_text` | ✅ MATCH | — |
| `sort_mode` | ❌ MISSING | **GAP** | Should be in MechanicCreativeDesign.layout_mode |
| `item_card_type` | `card_type` | ⚠️ PARTIAL | In MechanicCreativeDesign, not SortingContent |
| `container_style` | ❌ MISSING | **GAP** | No backend field |
| `submit_mode` | ❌ MISSING | **GAP** | No backend field |
| `allow_multi_category` | ⚠️ IMPLICIT | **PARTIAL** | Implied by correct_category_ids presence |

**Total gaps: 5 / 11 fields missing**
**Partial matches: 3 fields need resolution**

---

## 6. Memory Match

### Frontend Type: `MemoryMatchConfig`

```typescript
interface MemoryMatchPair {
  id: string;
  front: string;
  back: string;
  frontType: 'text' | 'image';
  backType: 'text' | 'image';
  explanation?: string;
  category?: string;
}

interface MemoryMatchConfig {
  pairs: MemoryMatchPair[];
  gridSize?: [number, number];
  flipDurationMs?: number;
  showAttemptsCounter?: boolean;
  instructions?: string;
  game_variant?: 'classic' | 'column_match' | 'scatter' | 'progressive' | 'peek';
  match_type?: 'term_to_definition' | 'image_to_label' | 'diagram_region_to_label' | 'concept_to_example';
  card_back_style?: 'solid' | 'gradient' | 'pattern' | 'question_mark';
  matched_card_behavior?: 'fade' | 'shrink' | 'collect' | 'checkmark';
  show_explanation_on_match?: boolean;
}
```

### V4 Backend: `MemoryMatchContent` + `MechanicCreativeDesign`

```python
class MemoryPair(BaseModel):
    id: str                               # MATCHES
    front: str                            # MATCHES
    back: str                             # MATCHES
    front_type: str = "text"              # MATCHES
    back_type: str = "text"               # MATCHES
    explanation: str = ""                 # MATCHES
    category: str = ""                    # MATCHES

class MemoryMatchContent(BaseModel):
    pairs: List[MemoryPair]               # MATCHES
    match_type: str = "term_to_definition"  # MATCHES
    game_variant: str = "classic"         # MATCHES
    grid_size: Optional[List[int]] = None # MATCHES (List[int] vs [number, number])
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `pairs` | `pairs` | ✅ MATCH | — |
| `gridSize` | `grid_size` | ✅ MATCH | snake_case vs camelCase |
| `flipDurationMs` | ❌ MISSING | **GAP** | No backend field |
| `showAttemptsCounter` | ❌ MISSING | **GAP** | No backend field |
| `instructions` | `instruction_text` | ⚠️ PARTIAL | In MechanicCreativeDesign, not MemoryMatchContent |
| `game_variant` | `game_variant` | ✅ MATCH | — |
| `match_type` | `match_type` | ✅ MATCH | — |
| `card_back_style` | ❌ MISSING | **GAP** | No backend field |
| `matched_card_behavior` | ❌ MISSING | **GAP** | No backend field |
| `show_explanation_on_match` | ❌ MISSING | **GAP** | No backend field |

**Total gaps: 5 / 10 fields missing**

---

## 7. Branching Scenario

### Frontend Type: `BranchingConfig`

```typescript
interface DecisionOption {
  id: string;
  text: string;
  nextNodeId: string | null;
  isCorrect?: boolean;
  consequence?: string;
  points?: number;
  quality?: 'optimal' | 'acceptable' | 'suboptimal' | 'harmful';
  consequence_text?: string;
}

interface DecisionNode {
  id: string;
  question: string;
  description?: string;
  imageUrl?: string;
  options: DecisionOption[];
  isEndNode?: boolean;
  endMessage?: string;
  node_type?: 'decision' | 'info' | 'ending' | 'checkpoint';
  narrative_text?: string;
  ending_type?: 'good' | 'neutral' | 'bad';
}

interface BranchingConfig {
  nodes: DecisionNode[];
  startNodeId: string;
  showPathTaken?: boolean;
  allowBacktrack?: boolean;
  showConsequences?: boolean;
  multipleValidEndings?: boolean;
  instructions?: string;
  narrative_structure?: 'linear' | 'branching' | 'foldback';
}
```

### V4 Backend: `BranchingContent` + `MechanicCreativeDesign`

```python
class DecisionOption(BaseModel):
    id: str                               # MATCHES
    text: str                             # MATCHES
    next_node_id: Optional[str] = None    # MATCHES
    is_correct: bool = False              # MATCHES
    consequence: str = ""                 # MATCHES
    points: int = 0                       # MATCHES
    quality: Optional[str] = None         # MATCHES

class DecisionNode(BaseModel):
    id: str                               # MATCHES
    question: str                         # MATCHES
    description: str = ""                 # MATCHES
    node_type: str = "decision"           # MATCHES
    is_end_node: bool = False             # MATCHES
    end_message: str = ""                 # MATCHES
    ending_type: Optional[str] = None     # MATCHES
    options: List[DecisionOption] = []    # MATCHES
    narrative_text: str = ""              # MATCHES
    image_description: Optional[str] = None  # ⚠️ NOT URL

class BranchingContent(BaseModel):
    nodes: List[DecisionNode]             # MATCHES
    start_node_id: str                    # MATCHES
    narrative_structure: str = "branching"  # MATCHES
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `nodes` | `nodes` | ✅ MATCH | — |
| `nodes[].imageUrl` | `nodes[].image_description` | ⚠️ PARTIAL | V4 has description, not URL |
| `options[].consequence_text` | `options[].consequence` | ✅ MATCH | Same field |
| `startNodeId` | `start_node_id` | ✅ MATCH | snake_case vs camelCase |
| `showPathTaken` | ❌ MISSING | **GAP** | No backend field |
| `allowBacktrack` | ❌ MISSING | **GAP** | No backend field |
| `showConsequences` | ❌ MISSING | **GAP** | No backend field |
| `multipleValidEndings` | ❌ MISSING | **GAP** | No backend field |
| `instructions` | `instruction_text` | ⚠️ PARTIAL | In MechanicCreativeDesign, not BranchingContent |
| `narrative_structure` | `narrative_structure` | ✅ MATCH | — |

**Total gaps: 4 / 10 fields missing**

---

## 8. Compare & Contrast

### Frontend Type: `CompareConfig`

```typescript
interface CompareDiagram {
  id: string;
  name: string;
  imageUrl: string;
  zones: Array<{
    id: string;
    label: string;
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
}

interface CompareConfig {
  diagramA: CompareDiagram;
  diagramB: CompareDiagram;
  expectedCategories: Record<string, 'similar' | 'different' | 'unique_a' | 'unique_b'>;
  highlightMatching?: boolean;
  instructions?: string;
  comparison_mode?: 'side_by_side' | 'slider' | 'overlay_toggle' | 'venn' | 'spot_difference';
  category_types?: string[];
  category_labels?: Record<string, string>;
  category_colors?: Record<string, string>;
  exploration_enabled?: boolean;
  zoom_enabled?: boolean;
}
```

### V4 Backend: `CompareContrastContent` + `MechanicCreativeDesign`

```python
class CompareSubject(BaseModel):
    name: str                             # MATCHES diagramA/B.name
    description: str = ""
    zone_labels: List[str] = []           # ⚠️ List of labels, NOT zone objects

class CompareContrastContent(BaseModel):
    subject_a: CompareSubject             # ⚠️ No image URL, no zones
    subject_b: CompareSubject             # ⚠️ No image URL, no zones
    expected_categories: Dict[str, str]   # MATCHES
    comparison_mode: str = "side_by_side" # MATCHES
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `diagramA.id` | ❌ MISSING | **GAP** | No ID field |
| `diagramA.name` | `subject_a.name` | ✅ MATCH | — |
| `diagramA.imageUrl` | ❌ MISSING | **CRITICAL** | V4 has NO image URL |
| `diagramA.zones` | `subject_a.zone_labels` | ⚠️ PARTIAL | V4 has label strings, not zone objects with coords |
| `diagramB.*` | Same as above | **CRITICAL** | Same issues |
| `expectedCategories` | `expected_categories` | ✅ MATCH | — |
| `highlightMatching` | ❌ MISSING | **GAP** | No backend field |
| `instructions` | `instruction_text` | ⚠️ PARTIAL | In MechanicCreativeDesign |
| `comparison_mode` | `comparison_mode` | ✅ MATCH | — |
| `category_types` | ❌ MISSING | **GAP** | No backend field |
| `category_labels` | ❌ MISSING | **GAP** | No backend field |
| `category_colors` | ❌ MISSING | **GAP** | No backend field (should be in color palette) |
| `exploration_enabled` | ❌ MISSING | **GAP** | No backend field |
| `zoom_enabled` | ❌ MISSING | **GAP** | No backend field |

**Total gaps: 10 / 14 fields missing**
**CRITICAL: CompareContrastContent has NO zone data, NO image URLs**

---

## 9. Description Matching

### Frontend Type: `DescriptionMatchingConfig`

```typescript
interface DescriptionMatchingConfig {
  descriptions?: Record<string, string>;  // zoneId → description
  mode?: 'click_zone' | 'drag_description' | 'multiple_choice';
  show_connecting_lines?: boolean;
  defer_evaluation?: boolean;
  distractor_count?: number;
  description_panel_position?: 'left' | 'right' | 'bottom';
}
```

### V4 Backend: `DescriptionMatchingContent` + `MechanicCreativeDesign`

```python
class DescriptionEntry(BaseModel):
    zone_label: str                       # ⚠️ zone_label, not zoneId
    description: str                      # MATCHES

class DescriptionMatchingContent(BaseModel):
    descriptions: List[DescriptionEntry]  # ⚠️ List, not Record
    mode: str = "click_zone"              # MATCHES
    distractor_descriptions: List[str] = []  # ⚠️ List of strings, not count
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `descriptions` | `descriptions` | ⚠️ MISMATCH | Frontend: Record<string, string>; V4: List[DescriptionEntry] |
| `mode` | `mode` | ✅ MATCH | — |
| `show_connecting_lines` | ❌ MISSING | **GAP** | No backend field |
| `defer_evaluation` | ❌ MISSING | **GAP** | No backend field |
| `distractor_count` | `distractor_descriptions` | ⚠️ PARTIAL | V4 has list, not count |
| `description_panel_position` | ❌ MISSING | **GAP** | No backend field |

**Total gaps: 3 / 6 fields missing**
**CRITICAL: descriptions type mismatch (Record vs List)**

---

## 10. Hierarchical

### Frontend Type: (No dedicated config, uses zoneGroups)

Frontend expects:
- `blueprint.zoneGroups: ZoneGroup[]`
- `Zone.parentZoneId`, `Zone.hierarchyLevel`, `Zone.childZoneIds`

### V4 Backend: `HierarchicalContent` + zone relationships

```python
class HierarchicalGroup(BaseModel):
    parent_label: str
    child_labels: List[str]
    reveal_trigger: str = "complete_parent"

class HierarchicalContent(BaseModel):
    groups: List[HierarchicalGroup]
```

### Gap Matrix

| Frontend Field | V4 Schema Field | Status | Notes |
|----------------|-----------------|--------|-------|
| `zoneGroups[].id` | ❌ MISSING | **GAP** | HierarchicalGroup has no ID |
| `zoneGroups[].parentZoneId` | `groups[].parent_label` | ⚠️ PARTIAL | V4 has label, not zone ID |
| `zoneGroups[].childZoneIds` | `groups[].child_labels` | ⚠️ PARTIAL | V4 has labels, not zone IDs |
| `zoneGroups[].revealTrigger` | `groups[].reveal_trigger` | ✅ MATCH | — |
| `zoneGroups[].label` | ❌ MISSING | **GAP** | No group label field |

**Total gaps: 2 / 5 fields missing**
**ID translation required: labels → zone IDs**

---

## 11. Root Blueprint Fields

### Frontend: `InteractiveDiagramBlueprint`

```typescript
interface InteractiveDiagramBlueprint {
  templateType: 'INTERACTIVE_DIAGRAM';
  title: string;
  narrativeIntro: string;
  diagram: {
    assetPrompt: string;
    assetUrl?: string;
    width?: number;
    height?: number;
    zones: Zone[];
    overlaySpec?: InteractiveOverlaySpec;
  };
  labels: Label[];
  distractorLabels?: DistractorLabel[];
  tasks: Task[];

  // Mechanics
  mechanics?: Mechanic[];              // Flat list
  modeTransitions?: ModeTransition[];

  // Per-mechanic configs (10 types)
  sequenceConfig?: SequenceConfig;
  sortingConfig?: SortingConfig;
  memoryMatchConfig?: MemoryMatchConfig;
  branchingConfig?: BranchingConfig;
  compareConfig?: CompareConfig;
  clickToIdentifyConfig?: ClickToIdentifyConfig;
  tracePathConfig?: TracePathConfig;
  dragDropConfig?: DragDropConfig;
  descriptionMatchingConfig?: DescriptionMatchingConfig;

  // Scoring (top-level or per-mechanic?)
  scoringStrategy?: {
    type: string;
    base_points_per_zone: number;
    time_bonus_enabled?: boolean;
    partial_credit?: boolean;
    max_score?: number;
  };

  // Temporal intelligence
  temporalConstraints?: TemporalConstraint[];
  motionPaths?: MotionPath[];
  revealOrder?: string[];

  // Animation
  animationCues: AnimationCues;
  animations?: StructuredAnimations;

  hints?: Hint[];
  feedbackMessages?: FeedbackMessages;
}
```

### V4 Backend: Blueprint Assembly from `GamePlan` + `SceneContent` + `SceneAssets`

V4 assembler must construct:

1. **`mechanics[]`** from `GamePlan.scenes[].mechanics[]`
   - Each `MechanicPlan` → `Mechanic`
   - `Mechanic.type` = `MechanicPlan.mechanic_type`
   - `Mechanic.config` = ??? (NO V4 SCHEMA for this)
   - `Mechanic.scoring` from `SceneContent.scoring[]`
   - `Mechanic.feedback` from `SceneContent.feedback[]`

2. **Per-mechanic config objects** (e.g., `sequenceConfig`) from:
   - `SceneContent.mechanic_contents[mechanic_id]` (content data)
   - `MechanicPlan.creative_design` (visual config)
   - BUT: NO SCHEMA defines the final merged config structure

3. **`diagram.zones`** from `SceneAssets.primary_diagram.zones`
   - `DetectedZone` → `Zone` (coordinate conversion required)

4. **`labels`** from multiple sources:
   - Drag_drop: `DragDropContent.labels`
   - Sequencing: `SequencingContent.items`
   - Sorting: `SortingContent.items`
   - Memory: `MemoryPair.front` / `MemoryPair.back`

### Critical Blueprint Assembly Gaps

| Blueprint Field | V4 Source | Status | Notes |
|----------------|-----------|--------|-------|
| `mechanics[].config` | ❌ UNDEFINED | **CRITICAL** | No schema defines this payload |
| `mechanics[].scoring` | `SceneContent.scoring` | ✅ MATCH | Array lookup by mechanic_id |
| `mechanics[].feedback` | `SceneContent.feedback` | ✅ MATCH | Array lookup by mechanic_id |
| `modeTransitions` | `SceneContent.mode_transitions` | ✅ MATCH | — |
| `sequenceConfig` | `SequencingContent` + `MechanicCreativeDesign` | ⚠️ PARTIAL | Need merge logic |
| `sortingConfig` | `SortingContent` + `MechanicCreativeDesign` | ⚠️ PARTIAL | Need merge logic |
| `memoryMatchConfig` | `MemoryMatchContent` + `MechanicCreativeDesign` | ⚠️ PARTIAL | Need merge logic |
| `branchingConfig` | `BranchingContent` + `MechanicCreativeDesign` | ⚠️ PARTIAL | Need merge logic |
| `compareConfig` | `CompareContrastContent` + `SceneAssets` | ❌ BROKEN | No image URLs in content |
| `clickToIdentifyConfig` | `ClickToIdentifyContent` + `MechanicCreativeDesign` | ⚠️ PARTIAL | Need merge logic |
| `tracePathConfig` | `TracePathContent` + `MechanicCreativeDesign` | ⚠️ PARTIAL | Need merge logic |
| `dragDropConfig` | `DragDropContent` + `MechanicCreativeDesign` | ⚠️ PARTIAL | Need merge logic |
| `descriptionMatchingConfig` | `DescriptionMatchingContent` + `MechanicCreativeDesign` | ⚠️ PARTIAL | Need merge logic + type fix |
| `diagram.zones` | `SceneAssets.primary_diagram.zones` | ⚠️ PARTIAL | Coordinate conversion required |
| `diagram.assetUrl` | `SceneAssets.primary_diagram.image_url` | ✅ MATCH | — |
| `labels` | Multiple `MechanicContent` sources | ⚠️ COMPLEX | Needs aggregation logic |
| `temporalConstraints` | ❌ MISSING | **GAP** | No V4 agent produces this |
| `motionPaths` | ❌ MISSING | **GAP** | No V4 agent produces this |
| `revealOrder` | ❌ MISSING | **GAP** | No V4 agent produces this |

---

## 12. Zone & Label Coordinate Issues

### Frontend Expectations

```typescript
interface Zone {
  id: string;
  label: string;
  shape?: 'circle' | 'polygon' | 'rect';
  points?: [number, number][];  // For polygon
  x?: number;  // For circle/rect
  y?: number;
  radius?: number;
  width?: number;
  height?: number;
  center?: { x: number; y: number };
}
```

### V4 Backend

```python
class DetectedZone(BaseModel):
    id: str
    label: str
    shape: str
    coordinates: Dict[str, Any]  # ⚠️ Opaque dict
    confidence: float = 0.0
```

### Conversion Required

Blueprint assembler must:
1. Parse `coordinates` dict based on `shape`
2. For `shape="polygon"`: extract points → `points: [[x,y],...]`
3. For `shape="circle"`: extract x, y, radius
4. For `shape="rect"`: extract x, y, width, height
5. Compute `center` for all shapes
6. Normalize coordinates to 0-100% scale (if not already)

**V3 had this logic in `_normalize_coordinates()` — V4 must reuse or reimplement.**

---

## 13. Mechanic.config Payload — The Missing Schema

### Current State

Frontend expects:
```typescript
interface Mechanic {
  type: InteractionMode;
  config?: Record<string, unknown>;  // ⚠️ Opaque
  scoring?: {...};
  feedback?: {...};
}
```

V4 has:
- `MechanicContent` (per-mechanic content data)
- `MechanicCreativeDesign` (visual/narrative direction)
- `MechanicScoring` + `MechanicFeedback` (separate arrays)

**Blueprint assembler must MERGE these into `config` payload, but NO SCHEMA defines the merge contract.**

### Proposed Fix

Blueprint assembler should:
1. Copy all fields from `MechanicContent.<mechanic_type>` (e.g., `SequencingContent`)
2. Overlay visual config from `MechanicCreativeDesign`:
   - `layout_mode`
   - `card_type`
   - `connector_style`
   - `instruction_text`
3. Add frontend-specific defaults for missing fields (e.g., `zoom_enabled: false`)

Example for sequencing:
```python
mechanic_config = {
    # From SequencingContent
    "sequenceType": content.sequencing.sequence_type,
    "items": [item.dict() for item in content.sequencing.items],
    "correctOrder": content.sequencing.correct_order,
    "instructionText": content.sequencing.instruction_text,

    # From MechanicCreativeDesign
    "layout_mode": creative_design.layout_mode,
    "card_type": creative_design.card_type,
    "connector_style": creative_design.connector_style,

    # Frontend defaults
    "allowPartialCredit": scoring.partial_credit,
    "show_position_numbers": False,  # Default
    "interaction_pattern": "drag_reorder",  # Default
}
```

---

## 14. Summary of Critical Gaps

### 🔴 CRITICAL (Blocks Functionality)

1. **Mechanic.config schema undefined** — No spec for what goes in `mechanics[].config`
2. **CompareConfig missing image URLs and zones** — `CompareContrastContent` has NO image data
3. **DragDropConfig missing 26/29 fields** — Visual config almost entirely missing
4. **Zone coordinate conversion undefined** — `DetectedZone.coordinates` opaque dict
5. **Description matching type mismatch** — Frontend: Record; V4: List

### 🟡 HIGH (Degrades UX)

6. **Instruction text duplication** — In both `MechanicContent` and `MechanicCreativeDesign`
7. **Visual config split across schemas** — `layout_mode`, `card_type` in MechanicCreativeDesign, but frontend expects them in per-mechanic config
8. **Scoring/feedback separate from config** — Frontend expects in `Mechanic.config`, V4 has separate arrays
9. **Item images as descriptions** — V4 has `image_description`, frontend needs `image` URL
10. **Hierarchical groups lack IDs** — Frontend needs `zoneGroups[].id`, V4 has no ID field

### 🟢 MEDIUM (Workarounds Exist)

11. **Temporal constraints missing** — No V4 agent produces `temporalConstraints`, `motionPaths`, `revealOrder`
12. **Distractor handling inconsistent** — V4 uses lists, frontend uses counts
13. **Multi-scene support unclear** — V4 GamePlan has scenes, but blueprint assembly unclear
14. **snake_case vs camelCase** — Systematic conversion needed

---

## 15. Recommended Actions

### Immediate (Block V4 Implementation)

1. **Define `MechanicConfigPayload` schemas** — One for each of 10 mechanics, specifying:
   - Required fields from `MechanicContent.<type>`
   - Required fields from `MechanicCreativeDesign`
   - Frontend-specific defaults

2. **Fix CompareContrastContent** — Add:
   - `subject_a.image_spec: ImageSpec`
   - `subject_b.image_spec: ImageSpec`
   - Zone data (or reference to SceneAssets)

3. **Standardize zone coordinates** — Document `DetectedZone.coordinates` format per shape:
   ```python
   # circle
   {"x": float, "y": float, "radius": float}
   # rect
   {"x": float, "y": float, "width": float, "height": float}
   # polygon
   {"points": [[x, y], ...]}
   ```

4. **Fix description matching type** — Change to:
   ```python
   descriptions: Dict[str, str]  # zone_label → description
   ```

5. **Document blueprint assembly merge logic** — Write exact transformation rules

### Short-term (Before V4 Launch)

6. **Add missing visual config fields to MechanicCreativeDesign**:
   - `tray_position`, `tray_layout`, `leader_line_style`, etc. (drag_drop)
   - `particleTheme`, `particleSpeed` (trace_path)
   - `game_variant`, `card_back_style` (memory_match)
   - etc.

7. **Consolidate instruction text** — Remove duplication, decide: MechanicContent or MechanicCreativeDesign?

8. **Add item image URL resolution** — Asset pipeline must:
   - Generate images for `SequenceItem.image_description`
   - Return URLs in `SceneAssets.item_images`
   - Blueprint assembler maps URLs to items by item_id

9. **Add zoneGroup IDs** — Generate `zg_{scene}_{index}` in blueprint assembler

10. **Write V4→Frontend type converter** — Automated camelCase conversion + defaults

### Long-term (V4.1+)

11. **Temporal intelligence agents** — Add agents to produce temporalConstraints, motionPaths
12. **Frontend config reduction** — Simplify frontend types to match V4 semantics
13. **Schema-driven rendering** — Frontend reads MechanicCreativeDesign directly

---

## 16. File Impact Analysis

### Files That Need Changes

| File | Change Type | Reason |
|------|------------|--------|
| `v4/schemas.py` | ADD | New `MechanicConfigPayload` classes (10 types) |
| `v4/schemas.py` | FIX | CompareContrastContent add image_spec fields |
| `v4/schemas.py` | FIX | DescriptionMatchingContent change to Dict |
| `v4/schemas.py` | FIX | DetectedZone.coordinates document format |
| `v4/schemas.py` | ADD | HierarchicalGroup add id field |
| `v4/phase2/content_generator.py` | FIX | Generate image URLs for items |
| `v4/phase3/asset_chains.py` | ADD | Item image generation chain |
| `v4/phase4/blueprint_assembler.py` | REWRITE | Merge logic for all 10 mechanic configs |
| `v4/phase4/blueprint_assembler.py` | ADD | Zone coordinate conversion (reuse V3) |
| `v4/phase4/blueprint_assembler.py` | ADD | ZoneGroup ID generation |
| `frontend/types.ts` | UPDATE | Add V4 compatibility layer |

### Estimated LOC Changes

| Change | Lines |
|--------|-------|
| MechanicConfigPayload schemas | ~300 |
| CompareContrastContent fix | ~20 |
| Blueprint assembler merge logic | ~400 |
| Zone coordinate conversion | ~100 (reuse V3) |
| Asset chain item images | ~150 |
| Frontend type converter | ~200 |
| **Total** | **~1,170** |

---

## Appendix A: Full Field Inventory

### Fields Present in V4 but NOT Consumed by Frontend

| V4 Field | Schema | Why Unused |
|----------|--------|-----------|
| `visual_style` | MechanicCreativeDesign | Not consumed (UI doesn't read) |
| `instruction_tone` | MechanicCreativeDesign | Not consumed |
| `narrative_hook` | MechanicCreativeDesign | Not consumed |
| `feedback_style` | MechanicCreativeDesign | Replaced by MechanicFeedback |
| `hint_strategy` | MechanicCreativeDesign | Replaced by zone hints |
| `difficulty_curve` | MechanicCreativeDesign | Not consumed |
| `generation_goal` | MechanicCreativeDesign | Internal only |
| `key_concepts` | MechanicCreativeDesign | Internal only |
| `pedagogical_focus` | MechanicCreativeDesign | Internal only |
| `color_direction` | MechanicCreativeDesign | Used by asset_art_director, not frontend |
| `image_description` | SequenceItem, etc. | Needs URL resolution |
| `confidence` | DetectedZone | Not shown to users |

### Fields Present in Frontend but NOT in V4

(See per-mechanic gap matrices above — 78 total missing fields)

---

**End of Report**
