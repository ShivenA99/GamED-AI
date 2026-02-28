/**
 * scoringEngine.ts — Pure scoring functions for the game engine.
 * No React, no Zustand. Reads from MECHANIC_REGISTRY and blueprint config.
 */

import type { InteractiveDiagramBlueprint, InteractionMode } from '../types';
import { MECHANIC_REGISTRY } from '../mechanicRegistry';

// ─── Scoring Configuration ───────────────────────────────────────────

export interface ScoringConfig {
  basePointsPerItem: number;
  partialCredit: boolean;
  timeBonusEnabled: boolean;
  timeBonusMaxSeconds: number;
  timeBonusMultiplier: number;
  attemptPenalty: number;        // points deducted per wrong attempt
  maxAttempts: number;           // 0 = unlimited
  streakMultiplier: number;      // bonus for consecutive correct
}

/**
 * Read scoring config from blueprint, falling back to defaults.
 * Priority: mechanic-level scoring > blueprint scoringStrategy > defaults.
 */
export function getScoringConfig(
  mode: InteractionMode,
  blueprint: InteractiveDiagramBlueprint,
): ScoringConfig {
  const mechanic = blueprint.mechanics?.find(m => m.type === mode);
  const strategy = blueprint.scoringStrategy;
  return {
    basePointsPerItem: mechanic?.scoring?.points_per_correct ?? strategy?.base_points_per_zone ?? 10,
    partialCredit: mechanic?.scoring?.partial_credit ?? strategy?.partial_credit ?? false,
    timeBonusEnabled: strategy?.time_bonus_enabled ?? false,
    timeBonusMaxSeconds: 120,
    timeBonusMultiplier: 1.5,
    attemptPenalty: 0,
    maxAttempts: 0,
    streakMultiplier: 1,
  };
}

export interface ScoreEvent {
  isCorrect: boolean;
  attemptCount?: number;
  consecutiveCorrect?: number;
}

/**
 * Calculate score delta for an action, respecting config.
 * Returns positive for correct, negative for incorrect (penalty), 0 for no effect.
 */
export function calculateScoreDelta(
  config: ScoringConfig,
  event: ScoreEvent,
): number {
  if (!event.isCorrect) {
    return -config.attemptPenalty;
  }
  let points = config.basePointsPerItem;
  if (event.consecutiveCorrect && config.streakMultiplier > 1) {
    points *= (1 + (event.consecutiveCorrect - 1) * (config.streakMultiplier - 1));
  }
  return Math.round(points);
}

// ─── Max Score ───────────────────────────────────────────────────────

/**
 * Get max score for a single mechanic mode using registry.
 * Falls back to labels.length * pointsPerZone for unknown modes.
 */
export function getMaxScore(
  mode: InteractionMode,
  blueprint: InteractiveDiagramBlueprint,
  pointsPerZone: number,
): number {
  const entry = MECHANIC_REGISTRY[mode];
  if (entry) {
    return entry.getMaxScore(blueprint, pointsPerZone);
  }
  // Fallback for unregistered modes
  return blueprint.labels.length * pointsPerZone;
}

/**
 * Calculate cumulative maxScore across all active mechanics in a multi-mode game.
 */
export function getCumulativeMaxScore(
  modes: InteractionMode[],
  blueprint: InteractiveDiagramBlueprint,
  pointsPerZone: number,
): number {
  return modes.reduce(
    (sum, mode) => sum + getMaxScore(mode, blueprint, pointsPerZone),
    0,
  );
}
