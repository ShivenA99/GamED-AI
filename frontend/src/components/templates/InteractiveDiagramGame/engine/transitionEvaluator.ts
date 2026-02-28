/**
 * transitionEvaluator.ts — Pure transition evaluation functions.
 * No React, no Zustand. Delegates mechanic-specific triggers to registry.
 */

import type {
  InteractiveDiagramBlueprint,
  InteractionMode,
  ModeTransition,
  PlacedLabel,
  MultiModeState,
  HierarchyState,
} from '../types';
import { MECHANIC_REGISTRY, MechanicProgressMap, EngineExtra } from '../mechanicRegistry';

export interface TransitionContext {
  currentMode: InteractionMode;
  blueprint: InteractiveDiagramBlueprint;
  progress: MechanicProgressMap;
  placedLabels: PlacedLabel[];
  multiModeState: MultiModeState;
  taskLabelCount?: number;
  hierarchyState?: HierarchyState | null;
}

/**
 * Evaluate all transitions from the current mode.
 * Returns the first transition whose trigger is satisfied, or null.
 */
export function evaluateTransitions(
  transitions: ModeTransition[],
  ctx: TransitionContext,
): ModeTransition | null {
  const applicableTransitions = transitions.filter(
    t => t.from === ctx.currentMode,
  );

  const extra: EngineExtra = {
    placedLabels: ctx.placedLabels,
    taskLabelCount: ctx.taskLabelCount,
    hierarchyState: ctx.hierarchyState,
  };

  for (const transition of applicableTransitions) {
    const satisfied = isTriggerSatisfied(transition, ctx, extra);
    if (satisfied) return transition;
  }

  return null;
}

function isTriggerSatisfied(
  transition: ModeTransition,
  ctx: TransitionContext,
  extra: EngineExtra,
): boolean {
  const { trigger } = transition;

  // 1. Try registry's checkTrigger for the current mode
  const entry = MECHANIC_REGISTRY[ctx.currentMode];
  if (entry?.checkTrigger) {
    const result = entry.checkTrigger(trigger, ctx.progress, ctx.blueprint, extra);
    if (result !== null) return result;
  }

  // 2. Handle generic triggers not tied to a specific mechanic
  switch (trigger) {
    case 'percentage_complete': {
      const correctPlacements = ctx.placedLabels.filter(p => p.isCorrect).length;
      const totalLabels = extra.taskLabelCount ?? ctx.blueprint.labels.length;
      const percentage = totalLabels > 0 ? (correctPlacements / totalLabels) * 100 : 0;
      const threshold = typeof transition.triggerValue === 'number' ? transition.triggerValue : 50;
      return percentage >= threshold;
    }

    case 'specific_zones': {
      if (Array.isArray(transition.triggerValue)) {
        const completedZoneIds = ctx.placedLabels
          .filter(p => p.isCorrect)
          .map(p => p.zoneId);
        return transition.triggerValue.every(
          zoneId => completedZoneIds.includes(zoneId),
        );
      }
      return false;
    }

    case 'time_elapsed': {
      const triggerVal = transition.triggerValue;
      if (typeof triggerVal === 'number' && ctx.multiModeState.modeHistory) {
        const currentModeEntry = ctx.multiModeState.modeHistory.find(
          h => h.mode === ctx.currentMode && !h.endTime,
        );
        if (currentModeEntry) {
          const elapsed = (Date.now() - currentModeEntry.startTime) / 1000;
          return elapsed >= triggerVal;
        }
      }
      return false;
    }

    case 'user_choice':
      // Handled by manual switching, not automatic
      return false;

    default:
      return false;
  }
}
