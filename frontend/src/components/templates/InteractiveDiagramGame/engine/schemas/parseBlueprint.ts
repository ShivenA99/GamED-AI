/**
 * parseBlueprint.ts — Single entry point for blueprint validation.
 *
 * Replaces raw `as any` casts with a parse→validate→normalize pipeline.
 * Returns typed blueprint + warnings/errors for UI feedback.
 */

import { BlueprintSchema } from './blueprintSchema';
import { MultiSceneBlueprintSchema } from './gameSequenceSchema';
import { normalizeSceneKeys, normalizeMisconceptions, normalizeMechanicConfigs } from './caseNormalizer';
import type {
  InteractiveDiagramBlueprint,
  MultiSceneInteractiveDiagramBlueprint,
} from '../../types';

// ─── Types ──────────────────────────────────────────────────────────

export interface ParseResult {
  blueprint: InteractiveDiagramBlueprint;
  warnings: string[];
  errors: string[];
}

export interface MultiSceneParseResult {
  blueprint: MultiSceneInteractiveDiagramBlueprint;
  warnings: string[];
  errors: string[];
}

// ─── Multi-scene detection ──────────────────────────────────────────

function isRawMultiScene(raw: unknown): boolean {
  return (
    typeof raw === 'object' &&
    raw !== null &&
    'is_multi_scene' in raw &&
    (raw as Record<string, unknown>).is_multi_scene === true
  );
}

// ─── Mechanic config completeness check ─────────────────────────────

const CONFIG_REQUIREMENTS: Record<string, { key: string; minItems?: string }> = {
  sequencing: { key: 'sequenceConfig', minItems: 'items' },
  sorting_categories: { key: 'sortingConfig', minItems: 'items' },
  memory_match: { key: 'memoryMatchConfig', minItems: 'pairs' },
  branching_scenario: { key: 'branchingConfig', minItems: 'nodes' },
  compare_contrast: { key: 'compareConfig' },
  click_to_identify: { key: 'identificationPrompts' },
  trace_path: { key: 'paths' },
};

function validateMechanicConfig(
  mode: string,
  bp: Record<string, unknown>,
  warnings: string[],
): void {
  const req = CONFIG_REQUIREMENTS[mode];
  if (!req) return;

  const config = bp[req.key];
  if (!config) {
    warnings.push(`Mechanic "${mode}" active but ${req.key} is missing`);
  } else if (req.minItems) {
    const items = (config as Record<string, unknown>)[req.minItems];
    if (!Array.isArray(items) || items.length === 0) {
      warnings.push(`${req.key}.${req.minItems} is empty — mechanic will have no content`);
    }
  }
}

// ─── Misconception normalization on mechanics array ─────────────────

function normalizeMechanicsFeedback(bp: Record<string, unknown>): void {
  const mechanics = bp.mechanics;
  if (!Array.isArray(mechanics)) return;

  for (const mechanic of mechanics) {
    if (mechanic?.feedback?.misconceptions) {
      mechanic.feedback.misconceptions = normalizeMisconceptions(
        mechanic.feedback.misconceptions,
      );
    }
  }
}

// ─── Single-scene parse ─────────────────────────────────────────────

function parseSingleBlueprint(
  raw: unknown,
  warnings: string[],
  errors: string[],
): InteractiveDiagramBlueprint {
  // Normalize snake_case root keys before Zod parse
  const normalized = typeof raw === 'object' && raw !== null
    ? normalizeSceneKeys(raw as Record<string, unknown>)
    : raw;

  const result = BlueprintSchema.safeParse(normalized);

  if (!result.success) {
    for (const issue of result.error.issues) {
      const path = issue.path.join('.');
      errors.push(`${path || 'root'}: ${issue.message}`);
    }
    // Best-effort: return raw cast since Zod failed
    return (normalized || {}) as InteractiveDiagramBlueprint;
  }

  const bp = result.data as Record<string, unknown>;

  // Normalize snake_case → camelCase inside mechanic configs
  normalizeMechanicConfigs(bp);

  // Normalize misconceptions in mechanics array
  normalizeMechanicsFeedback(bp);

  // Validate mechanic config completeness
  const mode = (
    (bp.mechanics as Array<{ type: string }> | undefined)?.[0]?.type ||
    bp.interactionMode
  ) as string | undefined;

  if (mode) {
    validateMechanicConfig(mode, bp, warnings);
  }

  // Validate zones exist
  const diagram = bp.diagram as { zones?: unknown[] } | undefined;
  if (!diagram?.zones || diagram.zones.length === 0) {
    warnings.push('Blueprint has no zones — game may be empty');
  }

  // Validate labels exist for drag_drop mode
  const labels = bp.labels as unknown[] | undefined;
  if (mode === 'drag_drop' && (!labels || labels.length === 0)) {
    warnings.push('drag_drop mode active but no labels provided');
  }

  return bp as unknown as InteractiveDiagramBlueprint;
}

// ─── Multi-scene parse ──────────────────────────────────────────────

function parseMultiSceneBlueprint(
  raw: unknown,
  warnings: string[],
  errors: string[],
): MultiSceneInteractiveDiagramBlueprint {
  const result = MultiSceneBlueprintSchema.safeParse(raw);

  if (!result.success) {
    for (const issue of result.error.issues) {
      const path = issue.path.join('.');
      errors.push(`${path || 'root'}: ${issue.message}`);
    }
    return (raw || {}) as MultiSceneInteractiveDiagramBlueprint;
  }

  const bp = result.data;

  // Validate scenes exist
  if (!bp.game_sequence?.scenes || bp.game_sequence.scenes.length === 0) {
    errors.push('Multi-scene blueprint has no scenes');
  } else {
    // Validate each scene has zones
    for (const scene of bp.game_sequence.scenes) {
      if (!scene.zones || scene.zones.length === 0) {
        warnings.push(`Scene "${scene.scene_id}" has no zones`);
      }
    }
  }

  return bp as unknown as MultiSceneInteractiveDiagramBlueprint;
}

// ─── Public API ─────────────────────────────────────────────────────

/**
 * Parse and validate a raw blueprint from the API.
 *
 * Handles both single-scene and multi-scene blueprints.
 * Fills defaults, converts snake_case → camelCase, validates mechanic configs.
 *
 * @returns Typed blueprint with warnings/errors
 */
export function parseBlueprint(raw: unknown): ParseResult | MultiSceneParseResult {
  const warnings: string[] = [];
  const errors: string[] = [];

  if (raw === null || raw === undefined) {
    errors.push('Blueprint is null or undefined');
    return {
      blueprint: { templateType: 'INTERACTIVE_DIAGRAM', title: '', narrativeIntro: '', diagram: { assetPrompt: '', zones: [] }, labels: [], tasks: [], animationCues: { correctPlacement: 'Correct!', incorrectPlacement: 'Try again!' } },
      warnings,
      errors,
    } as ParseResult;
  }

  if (isRawMultiScene(raw)) {
    return {
      blueprint: parseMultiSceneBlueprint(raw, warnings, errors),
      warnings,
      errors,
    } as MultiSceneParseResult;
  }

  return {
    blueprint: parseSingleBlueprint(raw, warnings, errors),
    warnings,
    errors,
  } as ParseResult;
}

/**
 * Type guard: is the parse result for a multi-scene blueprint?
 */
export function isMultiSceneParseResult(
  result: ParseResult | MultiSceneParseResult,
): result is MultiSceneParseResult {
  return (
    'is_multi_scene' in result.blueprint &&
    (result.blueprint as MultiSceneInteractiveDiagramBlueprint).is_multi_scene === true
  );
}
