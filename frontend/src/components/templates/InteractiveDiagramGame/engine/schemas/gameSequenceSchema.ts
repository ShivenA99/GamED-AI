/**
 * gameSequenceSchema.ts — Zod schema for multi-scene blueprint.
 *
 * Validates GameSequence and GameScene objects, normalizing
 * snake_case config keys to camelCase during parse.
 */

import { z } from 'zod';
import { normalizeSceneKeys } from './caseNormalizer';

// ─── Scene Task ─────────────────────────────────────────────────────

const SceneTaskSchema = z.object({
  task_id: z.string(),
  title: z.string().default(''),
  mechanic_type: z.string(),
  zone_ids: z.array(z.string()).default([]),
  label_ids: z.array(z.string()).default([]),
  instructions: z.string().optional(),
  scoring_weight: z.number().default(1),
  config: z.record(z.string(), z.unknown()).optional(),
}).passthrough();

// ─── Game Scene ─────────────────────────────────────────────────────

const GameSceneSchema = z.object({
  scene_id: z.string(),
  scene_number: z.number().default(1),
  title: z.string().default(''),
  narrative_intro: z.string().default(''),
  diagram: z.object({
    type: z.string().optional(),
    assetUrl: z.string().nullable().optional(),
    imageUrl: z.string().nullable().optional(),
    svgContent: z.string().optional(),
    assetPrompt: z.string().optional(),
  }).passthrough(),
  zones: z.array(z.record(z.string(), z.unknown())).default([]),
  labels: z.array(z.record(z.string(), z.unknown())).default([]),
  max_score: z.number().default(0),
  prerequisite_scene: z.string().nullable().optional(),
  child_scenes: z.array(z.string()).optional(),
  reveal_trigger: z.enum(['all_correct', 'percentage', 'specific_zones', 'manual']).optional(),
  reveal_threshold: z.number().optional(),
  time_limit_seconds: z.number().optional(),
  hints_enabled: z.boolean().optional(),
  feedback_enabled: z.boolean().optional(),
  tasks: z.array(SceneTaskSchema).default([]),
  mechanics: z.array(z.record(z.string(), z.unknown())).optional(),
  interaction_mode: z.string().optional(),
  mode_transitions: z.array(z.record(z.string(), z.unknown())).optional(),
  zoneGroups: z.array(z.record(z.string(), z.unknown())).optional(),
  paths: z.array(z.record(z.string(), z.unknown())).optional(),
  hints: z.array(z.record(z.string(), z.unknown())).optional(),
  distractor_labels: z.array(z.record(z.string(), z.unknown())).optional(),
}).passthrough()
  // After parsing, promote snake_case config keys to camelCase
  .transform((scene) => normalizeSceneKeys(scene));

// ─── Game Sequence ──────────────────────────────────────────────────

const GameSequenceSchema = z.object({
  sequence_id: z.string().default('default'),
  sequence_title: z.string().default(''),
  sequence_description: z.string().optional(),
  total_scenes: z.number().default(0),
  scenes: z.array(GameSceneSchema).default([]),
  progression_type: z.enum(['linear', 'zoom_in', 'depth_first', 'branching']).default('linear'),
  total_max_score: z.number().default(0),
  passing_score: z.number().optional(),
  bonus_for_no_hints: z.boolean().optional(),
  require_completion: z.boolean().optional(),
  allow_scene_skip: z.boolean().optional(),
  allow_revisit: z.boolean().optional(),
  estimated_duration_minutes: z.number().optional(),
  difficulty_level: z.enum(['beginner', 'intermediate', 'advanced']).optional(),
}).passthrough();

// ─── Multi-Scene Blueprint ──────────────────────────────────────────

export const MultiSceneBlueprintSchema = z.object({
  templateType: z.string().default('INTERACTIVE_DIAGRAM'),
  title: z.string().default('Untitled Game'),
  narrativeIntro: z.string().default(''),
  is_multi_scene: z.literal(true),
  game_sequence: GameSequenceSchema,
  animationCues: z.object({
    correctPlacement: z.string().default('Correct!'),
    incorrectPlacement: z.string().default('Try again!'),
  }).passthrough().default({
    correctPlacement: 'Correct!',
    incorrectPlacement: 'Try again!',
  }),
  animations: z.unknown().optional(),
  feedbackMessages: z.object({
    perfect: z.string().default('Perfect score!'),
    good: z.string().default('Good job!'),
    retry: z.string().default('Try again!'),
  }).passthrough().optional(),
  global_hints: z.array(z.record(z.string(), z.unknown())).optional(),
  mediaAssets: z.unknown().optional(),
  temporalConstraints: z.array(z.record(z.string(), z.unknown())).optional(),
  motionPaths: z.array(z.record(z.string(), z.unknown())).optional(),
}).passthrough();

export type MultiSceneBlueprintParsed = z.infer<typeof MultiSceneBlueprintSchema>;
