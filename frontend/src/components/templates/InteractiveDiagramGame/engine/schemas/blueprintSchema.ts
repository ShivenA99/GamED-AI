/**
 * blueprintSchema.ts — Zod schema for InteractiveDiagramBlueprint.
 *
 * Validates the root blueprint object (single-scene).
 * Uses .default() for required fields with sensible fallbacks.
 * Uses .passthrough() to tolerate unknown backend fields.
 */

import { z } from 'zod';
import {
  SequenceConfigSchema,
  SortingConfigSchema,
  MemoryMatchConfigSchema,
  BranchingConfigSchema,
  CompareConfigSchema,
  ClickToIdentifyConfigSchema,
  TracePathConfigSchema,
  DragDropConfigSchema,
  DescriptionMatchingConfigSchema,
  ScoringStrategySchema,
  MechanicSchema,
} from './mechanicConfigSchemas';

// ─── Sub-schemas ────────────────────────────────────────────────────

const ZoneSchema = z.object({
  id: z.string(),
  label: z.string(),
  x: z.number().optional(),
  y: z.number().optional(),
  radius: z.number().optional(),
  width: z.number().optional(),
  height: z.number().optional(),
  zone_type: z.enum(['point', 'area']).optional(),
  shape: z.enum(['circle', 'polygon', 'rect']).optional(),
  points: z.array(z.tuple([z.number(), z.number()])).optional(),
  center: z.object({ x: z.number(), y: z.number() }).optional(),
  parentZoneId: z.string().optional(),
  hierarchyLevel: z.number().optional(),
  childZoneIds: z.array(z.string()).optional(),
  description: z.string().optional(),
  hint: z.string().optional(),
  difficulty: z.number().optional(),
  focusOrder: z.number().optional(),
  pronunciationGuide: z.string().optional(),
  keyboardShortcut: z.string().optional(),
  diagramType: z.string().optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
}).passthrough();

const LabelSchema = z.object({
  id: z.string(),
  text: z.string(),
  correctZoneId: z.string(),
}).passthrough();

const DistractorLabelSchema = z.object({
  id: z.string(),
  text: z.string(),
  explanation: z.string(),
}).passthrough();

const TaskSchema = z.object({
  id: z.string(),
  type: z.string(),
  questionText: z.string().default(''),
  requiredToProceed: z.boolean().default(true),
}).passthrough();

const HintSchema = z.object({
  zoneId: z.string(),
  hintText: z.string(),
}).passthrough();

const AnimationCuesSchema = z.object({
  labelDrag: z.string().optional(),
  correctPlacement: z.string().default('Correct!'),
  incorrectPlacement: z.string().default('Try again!'),
  allLabeled: z.string().optional(),
}).passthrough();

const IdentificationPromptSchema = z.object({
  zoneId: z.string(),
  prompt: z.string(),
  order: z.number().optional(),
}).passthrough();

const PathWaypointSchema = z.object({
  zoneId: z.string(),
  order: z.number(),
  type: z.enum(['standard', 'gate', 'branch_point', 'terminus']).optional(),
  svg_path_data: z.string().optional(),
}).passthrough();

const TracePathSchema = z.object({
  id: z.string(),
  waypoints: z.array(PathWaypointSchema).default([]),
  description: z.string().default(''),
  requiresOrder: z.boolean().default(true),
}).passthrough();

const ZoneGroupSchema = z.object({
  id: z.string(),
  parentZoneId: z.string(),
  childZoneIds: z.array(z.string()).default([]),
  revealTrigger: z.enum(['complete_parent', 'click_expand', 'hover_reveal']).default('complete_parent'),
  label: z.string().optional(),
}).passthrough();

const ModeTransitionSchema = z.object({
  from: z.string(),
  to: z.string(),
  trigger: z.string(),
  triggerValue: z.union([z.number(), z.array(z.string())]).optional(),
  animation: z.enum(['fade', 'slide', 'zoom', 'none']).optional(),
  message: z.string().optional(),
}).passthrough();

const TemporalConstraintSchema = z.object({
  zone_a: z.string(),
  zone_b: z.string(),
  constraint_type: z.enum(['before', 'after', 'mutex', 'concurrent', 'sequence']),
  reason: z.string().default(''),
  priority: z.number().default(50),
}).passthrough();

const MotionKeyframeSchema = z.object({
  time_ms: z.number(),
  x: z.number().optional(),
  y: z.number().optional(),
  scale: z.number().optional(),
  rotation: z.number().optional(),
  opacity: z.number().optional(),
  backgroundColor: z.string().optional(),
  transform: z.string().optional(),
}).passthrough();

const MotionPathSchema = z.object({
  asset_id: z.string(),
  keyframes: z.array(MotionKeyframeSchema).default([]),
  easing: z.string().default('linear'),
  trigger: z.enum(['on_reveal', 'on_complete', 'on_hover', 'on_scene_enter', 'on_incorrect']),
  stagger_delay_ms: z.number().optional(),
  loop: z.boolean().optional(),
}).passthrough();

const FeedbackMessagesSchema = z.object({
  perfect: z.string().default('Perfect score!'),
  good: z.string().default('Good job!'),
  retry: z.string().default('Try again!'),
}).passthrough();

const DiagramSchema = z.object({
  assetPrompt: z.string().default(''),
  assetUrl: z.string().nullable().optional(),
  width: z.number().optional(),
  height: z.number().optional(),
  zones: z.array(ZoneSchema).default([]),
  overlaySpec: z.unknown().optional(),
}).passthrough();

// ─── Root Blueprint Schema ──────────────────────────────────────────

export const BlueprintSchema = z.object({
  templateType: z.string().default('INTERACTIVE_DIAGRAM'),
  title: z.string().default('Untitled Game'),
  narrativeIntro: z.string().default(''),
  diagram: DiagramSchema,
  labels: z.array(LabelSchema).default([]),
  distractorLabels: z.array(DistractorLabelSchema).optional(),
  tasks: z.array(TaskSchema).default([]),
  animationCues: AnimationCuesSchema.default({
    correctPlacement: 'Correct!',
    incorrectPlacement: 'Try again!',
  }),
  animations: z.unknown().optional(),
  mechanics: z.array(MechanicSchema).optional(),
  modeTransitions: z.array(ModeTransitionSchema).optional(),
  interactionMode: z.string().optional(),
  zoneGroups: z.array(ZoneGroupSchema).optional(),
  identificationPrompts: z.array(IdentificationPromptSchema).optional(),
  selectionMode: z.enum(['sequential', 'any_order']).optional(),
  paths: z.array(TracePathSchema).optional(),
  mediaAssets: z.unknown().optional(),
  temporalConstraints: z.array(TemporalConstraintSchema).optional(),
  motionPaths: z.array(MotionPathSchema).optional(),
  revealOrder: z.array(z.string()).optional(),
  scoringStrategy: ScoringStrategySchema.optional(),
  hints: z.array(HintSchema).optional(),
  feedbackMessages: FeedbackMessagesSchema.optional(),
  // Per-mechanic configs (all optional)
  sequenceConfig: SequenceConfigSchema.optional(),
  sortingConfig: SortingConfigSchema.optional(),
  memoryMatchConfig: MemoryMatchConfigSchema.optional(),
  branchingConfig: BranchingConfigSchema.optional(),
  compareConfig: CompareConfigSchema.optional(),
  descriptionMatchingConfig: DescriptionMatchingConfigSchema.optional(),
  clickToIdentifyConfig: ClickToIdentifyConfigSchema.optional(),
  tracePathConfig: TracePathConfigSchema.optional(),
  dragDropConfig: DragDropConfigSchema.optional(),
  timedChallengeWrappedMode: z.string().optional(),
  timeLimitSeconds: z.number().optional(),
}).passthrough();

export type BlueprintParsed = z.infer<typeof BlueprintSchema>;
