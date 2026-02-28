/**
 * completionDetector.ts — Pure completion detection functions.
 * No React, no Zustand. Reads from MECHANIC_REGISTRY.
 */

import type {
  InteractiveDiagramBlueprint,
  InteractionMode,
  PlacedLabel,
  MultiModeState,
} from '../types';
import { MECHANIC_REGISTRY, MechanicProgressMap, EngineExtra } from '../mechanicRegistry';

/**
 * Check if a single mechanic is complete.
 */
export function isMechanicComplete(
  mode: InteractionMode,
  progress: MechanicProgressMap,
  blueprint: InteractiveDiagramBlueprint,
  extra?: EngineExtra,
): boolean {
  const entry = MECHANIC_REGISTRY[mode];
  if (!entry) return false;
  return entry.isComplete(progress, blueprint, extra);
}

/**
 * Check if the entire game is complete:
 * - Current mechanic is done
 * - No remaining modes in multi-mode
 */
export function isGameComplete(
  currentMode: InteractionMode,
  progress: MechanicProgressMap,
  blueprint: InteractiveDiagramBlueprint,
  multiModeState: MultiModeState | null,
  extra?: EngineExtra,
): boolean {
  const mechanicDone = isMechanicComplete(currentMode, progress, blueprint, extra);
  if (!mechanicDone) return false;

  // If no multi-mode, mechanic done = game done
  if (!multiModeState) return true;

  // Check for remaining modes
  const remaining = multiModeState.availableModes.filter(
    m => m !== multiModeState.currentMode && !multiModeState.completedModes.includes(m),
  );
  return remaining.length === 0;
}

/**
 * Check if there are remaining modes after current mechanic completes.
 * Used by completeInteraction to decide whether to trigger transition or end game.
 */
export function hasRemainingModes(multiModeState: MultiModeState | null): boolean {
  if (!multiModeState) return false;
  const remaining = multiModeState.availableModes.filter(
    m => m !== multiModeState.currentMode && !multiModeState.completedModes.includes(m),
  );
  return remaining.length > 0;
}
