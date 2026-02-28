// Gameplay mode: learn (hints, no timer) vs test (no hints, timed)
export type GameplayMode = 'learn' | 'test';

// Interaction mode types
// Preset 1: drag_drop, click_to_identify, trace_path, hierarchical
// Preset 2 adds: description_matching, compare_contrast, sequencing, timed_challenge
// Preset 3 adds: sorting_categories, memory_match, branching_scenario
export type InteractionMode =
  | 'drag_drop'
  | 'click_to_identify'
  | 'trace_path'
  | 'hierarchical'
  | 'description_matching'  // Preset 2
  | 'compare_contrast'      // Preset 2
  | 'sequencing'            // Preset 2
  | 'timed_challenge'       // Preset 2
  | 'sorting_categories'    // Preset 3
  | 'memory_match'          // Preset 3
  | 'branching_scenario';   // Preset 3

// =============================================================================
// MULTI-MODE GAME TYPES (Agentic Interaction Design)
// =============================================================================

/**
 * Trigger conditions for mode transitions
 */
export type ModeTransitionTrigger =
  | 'all_zones_labeled'    // All zones in current mode are correctly labeled
  | 'path_complete'        // Path tracing completed
  | 'percentage_complete'  // X% of zones labeled correctly
  | 'specific_zones'       // Specific zone IDs completed
  | 'time_elapsed'         // After X seconds
  | 'user_choice'          // User selects to switch modes
  | 'hierarchy_level_complete' // All zones at current hierarchy level done
  // Mechanic-specific triggers (Fix 1.7a)
  | 'identification_complete'  // All identification prompts answered
  | 'sequence_complete'
  | 'sorting_complete'
  | 'memory_complete'
  | 'branching_complete'
  | 'compare_complete'
  | 'description_complete';

/**
 * Defines a transition between interaction modes
 */
export interface ModeTransition {
  from: InteractionMode;
  to: InteractionMode;
  trigger: ModeTransitionTrigger;
  triggerValue?: number | string[];  // Percentage or specific zone IDs
  animation?: 'fade' | 'slide' | 'zoom' | 'none';
  message?: string;  // Message to show during transition
}

/**
 * A single game mechanic with its type and optional configuration.
 * Replaces the old primaryMode/secondaryModes split — mechanics is a flat list.
 * The first mechanic is the starting mode; transitions define the graph.
 */
export interface Mechanic {
  type: InteractionMode;
  config?: Record<string, unknown>;
  // From backend IDMechanic (populated by blueprint_assembler_v3) — Fix 3.1
  scoring?: {
    strategy: string;
    points_per_correct: number;
    max_score: number;
    partial_credit?: boolean;
  };
  feedback?: {
    on_correct: string;
    on_incorrect: string;
    on_completion: string;
    misconceptions?: Array<{ trigger_label: string; message: string }>;
  };
}

/**
 * State for tracking multi-mode progression
 */
export interface MultiModeState {
  currentMode: InteractionMode;
  completedModes: InteractionMode[];
  modeHistory: Array<{
    mode: InteractionMode;
    startTime: number;
    endTime?: number;
    score: number;
  }>;
  pendingTransition?: ModeTransition;
  availableModes: InteractionMode[];  // Modes user can switch to
}

export type AnimationType = 'pulse' | 'glow' | 'scale' | 'shake' | 'fade' | 'bounce' | 'confetti' | 'path_draw';
export type EasingType = 'linear' | 'ease-out' | 'ease-in-out' | 'bounce' | 'elastic';
export type ZoneShape = 'circle' | 'polygon' | 'rect';
export type ZoneType = 'point' | 'area';  // 'point' = small dot indicator, 'area' = precise boundary

// Scene progression types for multi-scene games (Preset 2)
export type SceneProgressionType = 'linear' | 'zoom_in' | 'depth_first' | 'branching';

// =============================================================================
// TEMPORAL CONSTRAINT TYPES (Petri Net-inspired)
// =============================================================================

export type TemporalConstraintType =
  | 'before'      // zone_a must be completed before zone_b appears
  | 'after'       // zone_a appears after zone_b is completed
  | 'mutex'       // zone_a and zone_b cannot be visible simultaneously
  | 'concurrent'  // zone_a and zone_b can appear together (same hierarchy)
  | 'sequence';   // zone_a → zone_b in strict order (for motion paths)

export type MotionTrigger =
  | 'on_reveal'       // When zone becomes visible
  | 'on_complete'     // When zone is correctly labeled
  | 'on_hover'        // When user hovers over zone
  | 'on_scene_enter'  // When entering a new scene
  | 'on_incorrect';   // When incorrect placement attempt

export interface TemporalConstraint {
  zone_a: string;
  zone_b: string;
  constraint_type: TemporalConstraintType;
  reason: string;
  priority: number;  // 1-100, higher = more important
}

export interface MotionKeyframe {
  time_ms: number;
  x?: number;
  y?: number;
  scale?: number;
  rotation?: number;
  opacity?: number;
  backgroundColor?: string;
  transform?: string;
}

export interface MotionPath {
  asset_id: string;
  keyframes: MotionKeyframe[];
  easing: string;
  trigger: MotionTrigger;
  stagger_delay_ms?: number;
  loop?: boolean;
}

export interface TemporalState {
  activeZones: Set<string>;
  completedZones: Set<string>;
  blockedZones: Set<string>;
  pendingZones: Set<string>;
}

export interface AnimationSpec {
  type: AnimationType;
  duration_ms: number;
  easing: EasingType;
  color?: string;
  intensity?: number;
  delay_ms?: number;
}

export interface Zone {
  id: string;
  label: string;

  // Position and size (for circle and rect shapes)
  x?: number;  // 0-100 percentage (optional for polygon)
  y?: number;  // 0-100 percentage (optional for polygon)
  radius?: number;  // For circle shapes
  width?: number;   // For rect shapes (0-100 percentage)
  height?: number;  // For rect shapes (0-100 percentage)

  // Zone type: 'point' for small dot indicators, 'area' for precise boundaries
  zone_type?: ZoneType;

  // Zone shape for interactive overlay
  shape?: ZoneShape;

  // Polygon support (Preset 2): list of [x, y] coordinate pairs (0-100% scale)
  points?: [number, number][];

  // Center point for label placement (auto-calculated for polygons)
  center?: { x: number; y: number };

  // Unlimited hierarchy support (Preset 2)
  parentZoneId?: string;  // For hierarchical zones
  hierarchyLevel?: number;  // 1 = root, 2 = child, 3 = grandchild, etc.
  childZoneIds?: string[];

  // Educational metadata
  description?: string;
  hint?: string;
  difficulty?: number;  // 1-5

  // Accessibility metadata (Phase 5)
  focusOrder?: number;  // Tab index for keyboard navigation
  pronunciationGuide?: string;  // Phonetic guide for screen readers
  keyboardShortcut?: string;  // Custom keyboard shortcut (e.g., "Alt+1")

  // Diagram type specific metadata
  diagramType?: string;
  metadata?: Record<string, unknown>;
}

export interface ZoneGroup {
  id: string;
  parentZoneId: string;
  childZoneIds: string[];
  revealTrigger: 'complete_parent' | 'click_expand' | 'hover_reveal';
  label?: string;
}

export interface Label {
  id: string;
  text: string;
  correctZoneId: string;
  /** Original zone name when text is a description (for post-placement display) */
  canonicalName?: string;
}

export interface DistractorLabel {
  id: string;
  text: string;
  explanation: string;
}

export interface IdentificationPrompt {
  zoneId: string;
  prompt: string;
  order?: number;
}

export interface PathWaypoint {
  zoneId: string;
  order: number;
}

export interface TracePath {
  id: string;
  waypoints: PathWaypoint[];
  description: string;
  requiresOrder: boolean;
}

export interface Task {
  id: string;
  type: 'label_diagram' | 'identify_function' | 'trace_path' | 'click_identify' | 'hierarchical_label';
  questionText: string;
  requiredToProceed: boolean;
}

/** A task (phase) within a scene. Each task uses the same image but may
 *  activate a different subset of zones/labels with a different mechanic. */
export interface SceneTask {
  task_id: string;
  title: string;
  mechanic_type: InteractionMode;
  zone_ids: string[];
  label_ids: string[];
  instructions?: string;
  scoring_weight: number;
  config?: Record<string, unknown>;
}

export interface TaskResult {
  task_id: string;
  score: number;
  max_score: number;
  completed: boolean;
  matches: PlacedLabel[];
}

export interface Hint {
  zoneId: string;
  hintText: string;
}

export interface StructuredAnimations {
  labelDrag?: AnimationSpec;
  correctPlacement: AnimationSpec;
  incorrectPlacement: AnimationSpec;
  completion?: AnimationSpec;
  zoneHover?: AnimationSpec;
  pathProgress?: AnimationSpec;
}

export interface AnimationCues {
  labelDrag?: string;
  correctPlacement: string;
  incorrectPlacement: string;
  allLabeled?: string;
}

export interface FeedbackMessages {
  perfect: string;
  good: string;
  retry: string;
}

// =============================================================================
// SEQUENCE CONFIG TYPES (Phase 0: Multi-Mechanic Support)
// =============================================================================

/**
 * A single item in a sequence configuration.
 */
export interface SequenceConfigItem {
  id: string;
  content: string;
  description?: string;
  image?: string;       // URL/path to illustration
  icon?: string;        // Emoji or icon identifier
  category?: string;    // Grouping category
  is_distractor?: boolean;
  order_index?: number; // Correct position (0-based)
}

/**
 * Sequence configuration for order-based mechanics in INTERACTIVE_DIAGRAM games.
 *
 * Enables games that include both labeling AND sequencing mechanics,
 * e.g., "Label the heart AND show the order of blood flow".
 */
export interface SequenceConfig {
  /** Type of sequence: linear (A→B→C), cyclic (loop), branching (A→B or C) */
  sequenceType: 'linear' | 'cyclic' | 'branching';
  /** Items available for sequencing */
  items: SequenceConfigItem[];
  /** Ordered list of item IDs in the correct sequence */
  correctOrder: string[];
  /** Whether to give partial credit for partially correct sequences */
  allowPartialCredit?: boolean;
  /** Instruction text for the sequencing task */
  instructionText?: string;
  /** Layout mode for the sequencing display */
  layout_mode?: 'horizontal_timeline' | 'vertical_list' | 'circular_cycle' | 'flowchart' | 'insert_between';
  /** How the user interacts with the sequence */
  interaction_pattern?: 'drag_reorder' | 'drag_to_slots' | 'click_to_swap' | 'number_typing';
  /** Card visual style */
  card_type?: 'text_only' | 'text_with_icon' | 'image_with_caption' | 'image_only';
  /** Connector visual between items */
  connector_style?: 'arrow' | 'line' | 'numbered' | 'none';
  /** Whether to show slot position numbers */
  show_position_numbers?: boolean;
}

export interface MediaAsset {
  id: string;
  type: 'image' | 'gif' | 'video' | 'sprite' | 'css_animation';
  url?: string;
  generationPrompt?: string;
  placement: 'background' | 'overlay' | 'zone' | 'decoration';
  zoneId?: string;
  layer: number;
}

// =============================================================================
// PHASE 3 INTERACTION MODE CONFIGS
// =============================================================================

/**
 * Sorting categories configuration
 */
export interface SortingItem {
  id: string;
  content: string;
  correctCategoryId: string;
  /** Multi-category support: item can belong to multiple categories */
  correct_category_ids?: string[];
  description?: string;
  image?: string;
  difficulty?: 'easy' | 'medium' | 'hard';
}

export interface SortingCategory {
  id: string;
  label: string;
  description?: string;
  color?: string;
}

export interface SortingConfig {
  items: SortingItem[];
  categories: SortingCategory[];
  allowPartialCredit?: boolean;
  showCategoryHints?: boolean;
  instructions?: string;
  /** Sorting layout mode */
  sort_mode?: 'bucket' | 'venn_2' | 'venn_3' | 'matrix' | 'column';
  /** Item card visual style */
  item_card_type?: 'text_only' | 'text_with_icon' | 'image_with_caption';
  /** Container visual style */
  container_style?: 'bucket' | 'labeled_bin' | 'circle' | 'cell' | 'column';
  /** When to evaluate answers */
  submit_mode?: 'batch_submit' | 'immediate_feedback' | 'round_based';
  /** Allow items to belong to multiple categories */
  allow_multi_category?: boolean;
}

/**
 * Memory match configuration
 */
export interface MemoryMatchPair {
  id: string;
  front: string;
  back: string;
  frontType: 'text' | 'image';
  backType: 'text' | 'image';
  /** Pedagogical explanation shown when pair is matched */
  explanation?: string;
  /** Optional category for progressive reveal */
  category?: string;
}

export interface MemoryMatchConfig {
  pairs: MemoryMatchPair[];
  gridSize?: [number, number];
  flipDurationMs?: number;
  showAttemptsCounter?: boolean;
  instructions?: string;
  /** Game variant determines layout and rules */
  game_variant?: 'classic' | 'column_match' | 'scatter' | 'progressive' | 'peek';
  /** What types of content are being matched */
  match_type?: 'term_to_definition' | 'image_to_label' | 'diagram_region_to_label' | 'concept_to_example';
  /** Card back visual style */
  card_back_style?: 'solid' | 'gradient' | 'pattern' | 'question_mark';
  /** What happens to matched cards */
  matched_card_behavior?: 'fade' | 'shrink' | 'collect' | 'checkmark';
  /** Show explanation popup on successful match */
  show_explanation_on_match?: boolean;
}

/**
 * Branching scenario configuration
 */
export interface DecisionOption {
  id: string;
  text: string;
  nextNodeId: string | null;
  isCorrect?: boolean;
  consequence?: string;
  points?: number;
  /** Quality level for nuanced scoring */
  quality?: 'optimal' | 'acceptable' | 'suboptimal' | 'harmful';
  /** Consequence narrative text */
  consequence_text?: string;
}

export interface DecisionNode {
  id: string;
  question: string;
  description?: string;
  imageUrl?: string;
  options: DecisionOption[];
  isEndNode?: boolean;
  endMessage?: string;
  /** Node type determines UI treatment */
  node_type?: 'decision' | 'info' | 'ending' | 'checkpoint';
  /** Narrative text shown before the prompt */
  narrative_text?: string;
  /** Ending quality for end nodes */
  ending_type?: 'good' | 'neutral' | 'bad';
}

export interface BranchingConfig {
  nodes: DecisionNode[];
  startNodeId: string;
  showPathTaken?: boolean;
  allowBacktrack?: boolean;
  showConsequences?: boolean;
  multipleValidEndings?: boolean;
  instructions?: string;
  /** Story structure type */
  narrative_structure?: 'linear' | 'branching' | 'foldback';
}

/**
 * Compare contrast configuration (for two separate diagrams)
 */
export interface CompareDiagram {
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

export interface CompareConfig {
  diagramA: CompareDiagram;
  diagramB: CompareDiagram;
  expectedCategories: Record<string, 'similar' | 'different' | 'unique_a' | 'unique_b'>;
  highlightMatching?: boolean;
  instructions?: string;
  /** Comparison visualization mode */
  comparison_mode?: 'side_by_side' | 'slider' | 'overlay_toggle' | 'venn' | 'spot_difference';
  /** Category types to use for categorization */
  category_types?: string[];
  /** Custom labels for category types */
  category_labels?: Record<string, string>;
  /** Custom colors for category types */
  category_colors?: Record<string, string>;
  /** Enable free exploration before quiz */
  exploration_enabled?: boolean;
  /** Enable zoom on diagrams */
  zoom_enabled?: boolean;
}

// =============================================================================
// CLICK/TRACE/DRAG CONFIG TYPES (Phase 1 expansion)
// =============================================================================

export interface ClickToIdentifyConfig {
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

export interface TracePathConfig {
  pathType: 'linear' | 'branching' | 'circular';
  drawingMode: 'click_waypoints' | 'freehand';
  particleTheme: 'dots' | 'arrows' | 'droplets' | 'cells' | 'electrons';
  particleSpeed: 'slow' | 'medium' | 'fast';
  colorTransitionEnabled?: boolean;
  showDirectionArrows?: boolean;
  showWaypointLabels?: boolean;
  showFullFlowOnComplete?: boolean;
  instructions?: string;
  /** 'batch' (default): user selects all waypoints then submits for scoring.
   *  'immediate': validates each click in sequence (legacy, easier). */
  submitMode?: 'immediate' | 'batch';
}

export type LeaderLineStyle = 'straight' | 'elbow' | 'curved' | 'fluid' | 'dotted' | 'none';
export type PinMarkerShape = 'circle' | 'diamond' | 'arrow' | 'none';
export type LabelCardStyle = 'text' | 'text_with_icon' | 'text_with_thumbnail' | 'text_with_description';
export type TrayLayout = 'horizontal' | 'vertical' | 'grid' | 'grouped';
export type DragDropInteractionMode = 'drag_drop' | 'click_to_place' | 'reverse';

export interface DragDropConfig {
  // Interaction
  interaction_mode?: DragDropInteractionMode;
  feedback_timing?: 'immediate' | 'deferred';

  // Zone rendering
  zone_idle_animation?: 'none' | 'pulse' | 'glow' | 'breathe';
  zone_hover_effect?: 'highlight' | 'scale' | 'glow' | 'none';

  // Label card
  label_style?: LabelCardStyle;

  // Placement animation
  placement_animation?: 'spring' | 'ease' | 'instant';
  spring_stiffness?: number;
  spring_damping?: number;
  incorrect_animation?: 'shake' | 'bounce_back' | 'fade_out';
  show_placement_particles?: boolean;

  // Leader lines
  leader_line_style?: LeaderLineStyle;
  leader_line_color?: string;
  leader_line_width?: number;
  leader_line_animate?: boolean;
  pin_marker_shape?: PinMarkerShape;
  label_anchor_side?: 'auto' | 'left' | 'right' | 'top' | 'bottom';

  // Label tray
  tray_position?: 'bottom' | 'right' | 'left' | 'top';
  tray_layout?: TrayLayout;
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

  // Legacy compat
  showLeaderLines?: boolean;
  snapAnimation?: 'spring' | 'ease' | 'none';
  showInfoPanelOnCorrect?: boolean;
  maxAttempts?: number;
  shuffleLabels?: boolean;
  showHints?: boolean;
}

/** Extended label with rich card data for enhanced drag_drop */
export interface EnhancedLabel extends Label {
  icon?: string;
  thumbnail_url?: string;
  description?: string;
  category?: string;
}

/** Distractor label with confusion target and explanation */
export interface EnhancedDistractorLabel extends DistractorLabel {
  confusion_target_zone_id?: string;
  category?: string;
}

/** Leader line anchor points per zone */
export interface LeaderLineAnchor {
  zone_id: string;
  pin_x: number;  // 0-100%
  pin_y: number;  // 0-100%
  label_x: number; // 0-100%
  label_y: number; // 0-100%
  preferred_style?: LeaderLineStyle;
}

/** Enhanced zone with pin anchor and category */
export interface EnhancedZone extends Zone {
  pin_anchor?: { x: number; y: number };
  label_position?: { x: number; y: number };
  category?: string;
  function?: string;
}

export interface DescriptionMatchingConfig {
  descriptions?: Record<string, string>;
  mode?: 'click_zone' | 'drag_description' | 'multiple_choice';
  show_connecting_lines?: boolean;
  defer_evaluation?: boolean;
  distractor_count?: number;
  description_panel_position?: 'left' | 'right' | 'bottom';
}

export interface PathWaypoint {
  zoneId: string;
  order: number;
  /** Waypoint type for special behavior */
  type?: 'standard' | 'gate' | 'branch_point' | 'terminus';
  /** SVG path data for custom path segments */
  svg_path_data?: string;
}

export interface InteractiveOverlayZone {
  id: string;
  shape: ZoneShape;
  coordinates: Record<string, number>;
  interactions: Record<string, string>;
  styles: Record<string, Record<string, unknown>>;
}

export interface InteractiveOverlaySpec {
  canvas: { width: number; height: number };
  zones: InteractiveOverlayZone[];
  animations: Record<string, unknown>[];
}

export interface InteractiveDiagramBlueprint {
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

  // Animation cues (legacy text-based format)
  animationCues: AnimationCues;

  // Structured animations (preferred over text-based)
  animations?: StructuredAnimations;

  // Game mechanics — flat list, first entry is the starting mode.
  // Transitions between mechanics are defined by modeTransitions.
  mechanics?: Mechanic[];
  modeTransitions?: ModeTransition[];  // Transition rules between mechanics

  // Convenience: starting mode shorthand (derived from mechanics[0].type if omitted)
  interactionMode?: InteractionMode;

  // Hierarchical zone groups
  zoneGroups?: ZoneGroup[];

  // Click-to-identify prompts
  identificationPrompts?: IdentificationPrompt[];
  selectionMode?: 'sequential' | 'any_order';

  // Path definitions for trace_path mode
  paths?: TracePath[];

  // Media assets
  mediaAssets?: MediaAsset[];

  // Temporal intelligence (Petri Net-inspired constraints)
  temporalConstraints?: TemporalConstraint[];
  motionPaths?: MotionPath[];
  revealOrder?: string[];  // Suggested zone reveal order

  // Scoring configuration (from interaction_design)
  scoringStrategy?: {
    type: string;
    base_points_per_zone: number;
    time_bonus_enabled?: boolean;
    partial_credit?: boolean;
    max_score?: number;
  };

  hints?: Hint[];
  feedbackMessages?: FeedbackMessages;

  // Phase 0: Multi-mechanic support - sequence configuration
  /** Sequence configuration for order/sequence mechanics (e.g., blood flow order) */
  sequenceConfig?: SequenceConfig;

  // Phase 3: Additional interaction mode configurations
  /** Sorting categories configuration for sorting_categories mode */
  sortingConfig?: SortingConfig;
  /** Memory match configuration for memory_match mode */
  memoryMatchConfig?: MemoryMatchConfig;
  /** Branching scenario configuration for branching_scenario mode */
  branchingConfig?: BranchingConfig;
  /** Compare contrast configuration for two separate diagrams */
  compareConfig?: CompareConfig;
  /** Description matching configuration */
  descriptionMatchingConfig?: DescriptionMatchingConfig;
  /** Click-to-identify configuration */
  clickToIdentifyConfig?: ClickToIdentifyConfig;
  /** Trace path configuration */
  tracePathConfig?: TracePathConfig;
  /** Drag drop configuration */
  dragDropConfig?: DragDropConfig;
  /** Wrapped mode for timed_challenge (defaults to drag_drop) */
  timedChallengeWrappedMode?: InteractionMode;
  /** Time limit in seconds for timed_challenge mode */
  timeLimitSeconds?: number;
}

export interface PlacedLabel {
  labelId: string;
  zoneId: string;
  isCorrect: boolean;
}

// Path tracing state
export interface PathProgress {
  pathId: string;
  visitedWaypoints: string[];
  isComplete: boolean;
}

// Click-to-identify state
export interface IdentificationProgress {
  currentPromptIndex: number;
  completedZoneIds: string[];
  incorrectAttempts: number;
}

// Hierarchical state
export interface HierarchyState {
  expandedGroups: string[];
  completedParentZones: string[];
}

export interface GameState {
  // Labels that haven't been placed yet
  availableLabels: Label[];
  // Labels that have been placed on zones
  placedLabels: PlacedLabel[];
  // Current score
  score: number;
  // Whether the game is complete
  isComplete: boolean;
  // Hint visibility state
  showHints: boolean;
  // Currently dragged label
  draggingLabelId: string | null;
  // Interaction mode (current active mode)
  interactionMode: InteractionMode;
  // Path tracing progress (for trace_path mode)
  pathProgress?: PathProgress;
  // Click-to-identify progress
  identificationProgress?: IdentificationProgress;
  // Hierarchical state
  hierarchyState?: HierarchyState;
  // Multi-scene state (Preset 2)
  multiSceneState?: MultiSceneState;
  // Description matching state (Preset 2)
  descriptionMatchingState?: DescriptionMatchingState;
  // Multi-mode state (Agentic Interaction Design)
  multiModeState?: MultiModeState;
}

// =============================================================================
// MULTI-SCENE GAME TYPES (Preset 2)
// =============================================================================

/**
 * Single scene in a multi-scene game
 */
export interface GameScene {
  scene_id: string;
  scene_number: number;
  title: string;
  narrative_intro: string;
  diagram: {
    type?: string;
    assetUrl?: string;
    svgContent?: string;
    assetPrompt?: string;
  };
  zones: Zone[];
  labels: Label[];
  max_score: number;
  prerequisite_scene?: string | null;
  child_scenes?: string[];
  reveal_trigger?: 'all_correct' | 'percentage' | 'specific_zones' | 'manual';
  reveal_threshold?: number;
  time_limit_seconds?: number;
  hints_enabled?: boolean;
  feedback_enabled?: boolean;

  // Tasks within this scene (phases using the same image but different zone subsets/mechanics)
  tasks: SceneTask[];

  // Per-scene mechanic configuration (passthrough to InteractiveDiagramBlueprint)
  // mechanics[0].type is the starting mode for this scene
  mechanics?: Mechanic[];
  // Backward compat: single starting mode (derived from mechanics[0].type if omitted)
  interaction_mode?: InteractionMode;
  mode_transitions?: ModeTransition[];
  zoneGroups?: ZoneGroup[];
  paths?: TracePath[];

  // Per-mechanic configs — camelCase (V4, sent by backend directly)
  sequenceConfig?: SequenceConfig;
  sortingConfig?: SortingConfig;
  memoryMatchConfig?: MemoryMatchConfig;
  branchingConfig?: BranchingConfig;
  compareConfig?: CompareConfig;
  clickToIdentifyConfig?: ClickToIdentifyConfig;
  tracePathConfig?: TracePathConfig;
  dragDropConfig?: DragDropConfig;
  descriptionMatchingConfig?: DescriptionMatchingConfig;
  identificationPrompts?: IdentificationPrompt[];
  temporalConstraints?: TemporalConstraint[];
  motionPaths?: MotionPath[];
  scoringStrategy?: InteractiveDiagramBlueprint['scoringStrategy'];

  // Legacy snake_case aliases (backward compat with older pipeline outputs)
  sequence_config?: SequenceConfig;
  sorting_config?: SortingConfig;
  memory_match_config?: MemoryMatchConfig;
  branching_config?: BranchingConfig;
  compare_config?: CompareConfig;
  click_to_identify_config?: ClickToIdentifyConfig;
  trace_path_config?: TracePathConfig;
  drag_drop_config?: DragDropConfig;
  description_matching_config?: DescriptionMatchingConfig;
  temporal_constraints?: TemporalConstraint[];
  motion_paths?: MotionPath[];
  hints?: Hint[];
  scoring_strategy?: InteractiveDiagramBlueprint['scoringStrategy'];
  distractor_labels?: DistractorLabel[];
  identification_prompts?: IdentificationPrompt[];
}

/**
 * Multi-scene game container
 */
export interface GameSequence {
  sequence_id: string;
  sequence_title: string;
  sequence_description?: string;
  total_scenes: number;
  scenes: GameScene[];
  progression_type: SceneProgressionType;
  total_max_score: number;
  passing_score?: number;
  bonus_for_no_hints?: boolean;
  require_completion?: boolean;
  allow_scene_skip?: boolean;
  allow_revisit?: boolean;
  estimated_duration_minutes?: number;
  difficulty_level?: 'beginner' | 'intermediate' | 'advanced';
}

/**
 * Multi-scene game state
 */
export interface MultiSceneState {
  currentSceneIndex: number;
  completedSceneIds: string[];
  sceneResults: SceneResult[];
  totalScore: number;
  isSequenceComplete: boolean;
  currentTaskIndex: number;
  taskResults: TaskResult[];
}

export interface SceneResult {
  scene_id: string;
  score: number;
  max_score: number;
  completed: boolean;
  matches: PlacedLabel[];
  time_taken_seconds?: number;
}

/**
 * Description matching state (Preset 2)
 */
export interface DescriptionMatchingState {
  currentIndex: number;
  matches: DescriptionMatch[];
  mode: 'click_zone' | 'drag_description' | 'multiple_choice';
}

export interface DescriptionMatch {
  labelId: string;
  zoneId: string;
  isCorrect: boolean;
}

// =====================================================
// PER-MECHANIC PROGRESS TYPES (Zustand-tracked) — Fix 1.7a
// =====================================================

/** Sequencing mechanic progress */
export interface SequencingProgress {
  currentOrder: string[];     // Item IDs in user's current arrangement
  isSubmitted: boolean;
  correctPositions: number;
  totalPositions: number;
}

/** Sorting categories mechanic progress */
export interface SortingProgress {
  itemCategories: Record<string, string | null>;  // itemId → categoryId (null = unsorted)
  isSubmitted: boolean;
  correctCount: number;
  totalCount: number;
}

/** Memory match mechanic progress */
export interface MemoryMatchProgress {
  matchedPairIds: string[];   // IDs of successfully matched pairs
  attempts: number;           // Total flip-pair attempts
  totalPairs: number;
}

/** Branching scenario mechanic progress */
export interface BranchingProgress {
  currentNodeId: string;
  pathTaken: Array<{ nodeId: string; optionId: string; isCorrect: boolean }>;
}

/** Compare/contrast mechanic progress */
export interface CompareProgress {
  categorizations: Record<string, string>;  // zoneId → category
  isSubmitted: boolean;
  correctCount: number;
  totalCount: number;
}

// =====================================================
// V4 MECHANIC ACTION TYPES — Standardized Component Contract
// =====================================================

/**
 * Click-to-identify progress (alias of IdentificationProgress for V4 naming)
 */
export type ClickToIdentifyProgress = IdentificationProgress;

/**
 * Trace path progress per-path (extends existing PathProgress)
 */
export interface TracePathProgress {
  currentPathIndex: number;
  pathProgressMap: Record<string, { visitedWaypoints: string[]; isComplete: boolean }>;
}

// ── Per-mechanic action types ──

export interface DragDropPlaceAction {
  type: 'place';
  mechanic: 'drag_drop';
  labelId: string;
  zoneId: string;
}

export interface DragDropRemoveAction {
  type: 'remove';
  mechanic: 'drag_drop';
  labelId: string;
}

export interface ClickToIdentifyAction {
  type: 'identify';
  mechanic: 'click_to_identify';
  zoneId: string;
}

export interface TracePathVisitWaypointAction {
  type: 'visit_waypoint';
  mechanic: 'trace_path';
  pathId: string;
  zoneId: string;
}

export interface TracePathSubmitAction {
  type: 'submit_path';
  mechanic: 'trace_path';
  pathId: string;
  selectedZoneIds: string[];
}

export interface SequencingReorderAction {
  type: 'reorder';
  mechanic: 'sequencing';
  newOrder: string[];
}

export interface SequencingSubmitAction {
  type: 'submit_sequence';
  mechanic: 'sequencing';
}

export interface SortingPlaceAction {
  type: 'sort';
  mechanic: 'sorting_categories';
  itemId: string;
  categoryId: string;
}

export interface SortingRemoveAction {
  type: 'unsort';
  mechanic: 'sorting_categories';
  itemId: string;
}

export interface SortingSubmitAction {
  type: 'submit_sorting';
  mechanic: 'sorting_categories';
}

// ── Memory match actions ──

export interface MemoryMatchPairAction {
  type: 'match_pair';
  mechanic: 'memory_match';
  pairId: string;
}

export interface MemoryMatchAttemptAction {
  type: 'memory_attempt';
  mechanic: 'memory_match';
}

// ── Branching scenario actions ──

export interface BranchingChoiceAction {
  type: 'branching_choice';
  mechanic: 'branching_scenario';
  nodeId: string;
  optionId: string;
  isCorrect: boolean;
  nextNodeId: string | null;
}

export interface BranchingUndoAction {
  type: 'branching_undo';
  mechanic: 'branching_scenario';
}

// ── Compare/contrast actions ──

export interface CompareCategorizeAction {
  type: 'categorize';
  mechanic: 'compare_contrast';
  zoneId: string;
  category: string;
}

export interface CompareSubmitAction {
  type: 'submit_compare';
  mechanic: 'compare_contrast';
}

// ── Description matching actions ──

export interface DescriptionMatchAction {
  type: 'description_match';
  mechanic: 'description_matching';
  labelId: string;
  zoneId: string;
}

/** Result returned from mechanic action dispatch.
 *  Components use this for immediate UI feedback without computing scores. */
export interface ActionResult {
  isCorrect: boolean;
  scoreDelta: number;
  message?: string;
  /** Mechanic-specific data (e.g. { correctPositions: 3, totalPositions: 5 }) */
  data?: Record<string, unknown>;
}

/**
 * Discriminated union of all mechanic actions.
 * Components emit these via onAction(); the store/engine dispatches them.
 * To add a new mechanic: define its action interfaces above, then add to this union.
 */
export type MechanicAction =
  | DragDropPlaceAction
  | DragDropRemoveAction
  | ClickToIdentifyAction
  | TracePathVisitWaypointAction
  | TracePathSubmitAction
  | SequencingReorderAction
  | SequencingSubmitAction
  | SortingPlaceAction
  | SortingRemoveAction
  | SortingSubmitAction
  | MemoryMatchPairAction
  | MemoryMatchAttemptAction
  | BranchingChoiceAction
  | BranchingUndoAction
  | CompareCategorizeAction
  | CompareSubmitAction
  | DescriptionMatchAction;

/**
 * Extended blueprint for multi-scene games (Preset 2)
 */
export interface MultiSceneInteractiveDiagramBlueprint {
  templateType: 'INTERACTIVE_DIAGRAM';
  title: string;
  narrativeIntro: string;
  is_multi_scene: true;
  game_sequence: GameSequence;
  animationCues: AnimationCues;
  animations?: StructuredAnimations;
  feedbackMessages?: FeedbackMessages;
  global_hints?: Hint[];
  mediaAssets?: MediaAsset[];
  // Temporal intelligence (Petri Net-inspired constraints)
  temporalConstraints?: TemporalConstraint[];
  motionPaths?: MotionPath[];
}
