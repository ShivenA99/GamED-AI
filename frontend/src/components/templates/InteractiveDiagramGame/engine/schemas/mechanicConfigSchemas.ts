/**
 * mechanicConfigSchemas.ts — Zod schemas for all 10 mechanic configs.
 *
 * Each schema mirrors the corresponding TypeScript interface in types.ts.
 * Uses .default() for optional fields so parsed output always has values.
 * Uses .passthrough() on objects to tolerate unknown backend fields.
 */

import { z } from 'zod';

// ─── Sequence Config ────────────────────────────────────────────────

export const SequenceConfigItemSchema = z.object({
  id: z.string(),
  // Backend sends "content", frontend schema expects "text" — accept both
  text: z.string().optional(),
  content: z.string().optional(),
  description: z.string().optional(),
  explanation: z.string().optional(),
  image: z.string().optional(),
  image_url: z.string().nullable().optional(),
  image_description: z.string().nullable().optional(),
  icon: z.string().optional(),
  category: z.string().optional(),
  is_distractor: z.boolean().optional(),
  order_index: z.number().optional(),
}).passthrough();

export const SequenceConfigSchema = z.object({
  // Accept both camelCase and snake_case variants
  sequenceType: z.enum(['linear', 'cyclic', 'branching', 'ordered']).optional(),
  sequence_type: z.enum(['linear', 'cyclic', 'branching', 'ordered']).optional(),
  items: z.array(SequenceConfigItemSchema).default([]),
  correctOrder: z.array(z.string()).optional(),
  correct_order: z.array(z.string()).optional(),
  allowPartialCredit: z.boolean().optional(),
  allow_partial_credit: z.boolean().optional(),
  instructionText: z.string().optional(),
  instruction_text: z.string().optional(),
  layout_mode: z.enum([
    'horizontal_timeline', 'vertical_timeline', 'vertical_list', 'circular_cycle', 'circular',
    'flowchart', 'insert_between',
  ]).optional(),
  interaction_pattern: z.enum([
    'drag_reorder', 'drag_to_reorder', 'drag_to_slots', 'click_to_swap',
    'click_to_place', 'insert_between', 'number_typing',
  ]).optional(),
  card_type: z.enum([
    'text_only', 'text_with_icon', 'image_with_caption', 'image_only',
    'image_and_text', 'image_card', 'numbered_text',
  ]).optional(),
  connector_style: z.enum(['arrow', 'line', 'numbered', 'none']).optional(),
  show_position_numbers: z.boolean().optional(),
}).passthrough();

// ─── Sorting Config ─────────────────────────────────────────────────

export const SortingItemSchema = z.object({
  id: z.string(),
  text: z.string(),
  correctCategoryId: z.string(),
  correct_category_ids: z.array(z.string()).optional(),
  description: z.string().optional(),
  image: z.string().optional(),
  difficulty: z.enum(['easy', 'medium', 'hard']).optional(),
}).passthrough();

export const SortingCategorySchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string().optional(),
  color: z.string().optional(),
}).passthrough();

export const SortingConfigSchema = z.object({
  items: z.array(SortingItemSchema).default([]),
  categories: z.array(SortingCategorySchema).default([]),
  allowPartialCredit: z.boolean().optional(),
  showCategoryHints: z.boolean().optional(),
  instructions: z.string().optional(),
  sort_mode: z.enum(['bucket', 'venn_2', 'venn_3', 'matrix', 'column']).optional(),
  item_card_type: z.enum(['text_only', 'text_with_icon', 'image_with_caption']).optional(),
  container_style: z.enum(['bucket', 'labeled_bin', 'circle', 'cell', 'column']).optional(),
  submit_mode: z.enum(['batch_submit', 'immediate_feedback', 'round_based']).optional(),
  allow_multi_category: z.boolean().optional(),
}).passthrough();

// ─── Memory Match Config ────────────────────────────────────────────

export const MemoryMatchPairSchema = z.object({
  id: z.string(),
  front: z.string(),
  back: z.string(),
  frontType: z.enum(['text', 'image']).default('text'),
  backType: z.enum(['text', 'image']).default('text'),
  explanation: z.string().optional(),
  category: z.string().optional(),
}).passthrough();

export const MemoryMatchConfigSchema = z.object({
  pairs: z.array(MemoryMatchPairSchema).default([]),
  gridSize: z.tuple([z.number(), z.number()]).optional(),
  flipDurationMs: z.number().optional(),
  showAttemptsCounter: z.boolean().optional(),
  instructions: z.string().optional(),
  game_variant: z.enum(['classic', 'column_match', 'scatter', 'progressive', 'peek']).optional(),
  match_type: z.enum([
    'term_to_definition', 'image_to_label', 'diagram_region_to_label', 'concept_to_example',
  ]).optional(),
  card_back_style: z.enum(['solid', 'gradient', 'pattern', 'question_mark']).optional(),
  matched_card_behavior: z.enum(['fade', 'shrink', 'collect', 'checkmark']).optional(),
  show_explanation_on_match: z.boolean().optional(),
}).passthrough();

// ─── Branching Config ───────────────────────────────────────────────

export const DecisionOptionSchema = z.object({
  id: z.string(),
  text: z.string(),
  nextNodeId: z.string().nullable(),
  isCorrect: z.boolean().optional(),
  consequence: z.string().optional(),
  points: z.number().optional(),
  quality: z.enum(['optimal', 'acceptable', 'suboptimal', 'harmful']).optional(),
  consequence_text: z.string().optional(),
}).passthrough();

export const DecisionNodeSchema = z.object({
  id: z.string(),
  question: z.string(),
  description: z.string().optional(),
  imageUrl: z.string().optional(),
  options: z.array(DecisionOptionSchema).default([]),
  isEndNode: z.boolean().optional(),
  endMessage: z.string().optional(),
  node_type: z.enum(['decision', 'info', 'ending', 'checkpoint']).optional(),
  narrative_text: z.string().optional(),
  ending_type: z.enum(['good', 'neutral', 'bad']).optional(),
}).passthrough();

export const BranchingConfigSchema = z.object({
  nodes: z.array(DecisionNodeSchema).default([]),
  // Accept both camelCase and snake_case
  startNodeId: z.string().optional(),
  start_node_id: z.string().optional(),
  showPathTaken: z.boolean().optional(),
  show_path_taken: z.boolean().optional(),
  allowBacktrack: z.boolean().optional(),
  allow_backtrack: z.boolean().optional(),
  showConsequences: z.boolean().optional(),
  show_consequences: z.boolean().optional(),
  multipleValidEndings: z.boolean().optional(),
  multiple_valid_endings: z.boolean().optional(),
  instructions: z.string().optional(),
  narrative_structure: z.enum(['linear', 'branching', 'foldback']).optional(),
}).passthrough();

// ─── Compare Config ─────────────────────────────────────────────────

const CompareZoneSchema = z.object({
  id: z.string(),
  label: z.string(),
  x: z.number(),
  y: z.number(),
  width: z.number(),
  height: z.number(),
}).passthrough();

export const CompareDiagramSchema = z.object({
  id: z.string(),
  name: z.string(),
  imageUrl: z.string(),
  zones: z.array(CompareZoneSchema).default([]),
}).passthrough();

export const CompareConfigSchema = z.object({
  diagramA: CompareDiagramSchema,
  diagramB: CompareDiagramSchema,
  expectedCategories: z.record(z.string(), z.enum(['similar', 'different', 'unique_a', 'unique_b'])),
  highlightMatching: z.boolean().optional(),
  instructions: z.string().optional(),
  comparison_mode: z.enum([
    'side_by_side', 'slider', 'overlay_toggle', 'venn', 'spot_difference',
  ]).optional(),
  category_types: z.array(z.string()).optional(),
  category_labels: z.record(z.string(), z.string()).optional(),
  category_colors: z.record(z.string(), z.string()).optional(),
  exploration_enabled: z.boolean().optional(),
  zoom_enabled: z.boolean().optional(),
}).passthrough();

// ─── Click-to-Identify Config ───────────────────────────────────────

export const ClickToIdentifyConfigSchema = z.object({
  promptStyle: z.enum(['naming', 'functional']).default('naming'),
  selectionMode: z.enum(['sequential', 'any_order']).default('sequential'),
  highlightStyle: z.enum(['subtle', 'outlined', 'invisible']).default('subtle'),
  magnificationEnabled: z.boolean().optional(),
  magnificationFactor: z.number().optional(),
  exploreModeEnabled: z.boolean().optional(),
  exploreTimeLimitSeconds: z.number().nullable().optional(),
  showZoneCount: z.boolean().optional(),
  instructions: z.string().optional(),
}).passthrough();

// ─── Trace Path Config ──────────────────────────────────────────────

export const TracePathConfigSchema = z.object({
  pathType: z.enum(['linear', 'branching', 'circular']).default('linear'),
  drawingMode: z.enum(['click_waypoints', 'freehand']).default('click_waypoints'),
  particleTheme: z.enum(['dots', 'arrows', 'droplets', 'cells', 'electrons']).default('dots'),
  particleSpeed: z.enum(['slow', 'medium', 'fast']).default('medium'),
  colorTransitionEnabled: z.boolean().optional(),
  showDirectionArrows: z.boolean().optional(),
  showWaypointLabels: z.boolean().optional(),
  showFullFlowOnComplete: z.boolean().optional(),
  instructions: z.string().optional(),
  submitMode: z.enum(['immediate', 'batch']).optional(),
}).passthrough();

// ─── Drag Drop Config ───────────────────────────────────────────────

export const DragDropConfigSchema = z.object({
  interaction_mode: z.enum(['drag_drop', 'click_to_place', 'reverse']).optional(),
  feedback_timing: z.enum(['immediate', 'deferred']).optional(),
  zone_idle_animation: z.enum(['none', 'pulse', 'glow', 'breathe']).optional(),
  zone_hover_effect: z.enum(['highlight', 'scale', 'glow', 'none']).optional(),
  label_style: z.enum(['text', 'text_with_icon', 'text_with_thumbnail', 'text_with_description']).optional(),
  placement_animation: z.enum(['spring', 'ease', 'instant']).optional(),
  spring_stiffness: z.number().optional(),
  spring_damping: z.number().optional(),
  incorrect_animation: z.enum(['shake', 'bounce_back', 'fade_out']).optional(),
  show_placement_particles: z.boolean().optional(),
  leader_line_style: z.enum(['straight', 'elbow', 'curved', 'fluid', 'dotted', 'none']).optional(),
  leader_line_color: z.string().optional(),
  leader_line_width: z.number().optional(),
  leader_line_animate: z.boolean().optional(),
  pin_marker_shape: z.enum(['circle', 'diamond', 'arrow', 'none']).optional(),
  label_anchor_side: z.enum(['auto', 'left', 'right', 'top', 'bottom']).optional(),
  tray_position: z.enum(['bottom', 'right', 'left', 'top']).optional(),
  tray_layout: z.enum(['horizontal', 'vertical', 'grid', 'grouped']).optional(),
  tray_show_remaining: z.boolean().optional(),
  tray_show_categories: z.boolean().optional(),
  show_distractors: z.boolean().optional(),
  distractor_count: z.number().optional(),
  distractor_rejection_mode: z.enum(['immediate', 'deferred']).optional(),
  zoom_enabled: z.boolean().optional(),
  zoom_min: z.number().optional(),
  zoom_max: z.number().optional(),
  minimap_enabled: z.boolean().optional(),
  max_attempts: z.number().optional(),
  shuffle_labels: z.boolean().optional(),
  // Legacy camelCase aliases
  showLeaderLines: z.boolean().optional(),
  snapAnimation: z.enum(['spring', 'ease', 'none']).optional(),
  showInfoPanelOnCorrect: z.boolean().optional(),
  maxAttempts: z.number().optional(),
  shuffleLabels: z.boolean().optional(),
  showHints: z.boolean().optional(),
}).passthrough();

// ─── Description Matching Config ────────────────────────────────────

export const DescriptionMatchingConfigSchema = z.object({
  descriptions: z.record(z.string(), z.string()).optional(),
  mode: z.enum(['click_zone', 'drag_description', 'multiple_choice']).optional(),
  show_connecting_lines: z.boolean().optional(),
  defer_evaluation: z.boolean().optional(),
  distractor_count: z.number().optional(),
  description_panel_position: z.enum(['left', 'right', 'bottom']).optional(),
}).passthrough();

// ─── Scoring Strategy ───────────────────────────────────────────────

export const ScoringStrategySchema = z.object({
  type: z.string(),
  base_points_per_zone: z.number().default(10),
  time_bonus_enabled: z.boolean().optional(),
  partial_credit: z.boolean().optional(),
  max_score: z.number().optional(),
}).passthrough();

// ─── Mechanic Scoring/Feedback ──────────────────────────────────────

export const MechanicScoringSchema = z.object({
  strategy: z.string().optional(),
  points_per_correct: z.number().default(10),
  max_score: z.number().optional(),
  partial_credit: z.boolean().optional(),
}).passthrough();

export const MechanicFeedbackSchema = z.object({
  on_correct: z.string().default('Correct!'),
  on_incorrect: z.string().default('Try again!'),
  on_completion: z.string().default('Well done!'),
  misconceptions: z.array(z.object({
    trigger_label: z.string(),
    message: z.string(),
  })).optional(),
}).passthrough();

// ─── Mechanic (single entry in mechanics array) ─────────────────────

export const MechanicSchema = z.object({
  type: z.string(),
  config: z.record(z.string(), z.unknown()).optional(),
  scoring: MechanicScoringSchema.optional(),
  feedback: MechanicFeedbackSchema.optional(),
}).passthrough();
