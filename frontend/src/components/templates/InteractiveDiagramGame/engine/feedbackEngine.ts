/**
 * feedbackEngine.ts — Mechanic-aware feedback resolution.
 * Reads from blueprint's Mechanic.feedback and animationCues, with misconception support.
 * No React, no Zustand.
 */

import type { InteractiveDiagramBlueprint, InteractionMode } from '../types';

export interface FeedbackResult {
  message: string;
  type: 'correct' | 'incorrect' | 'completion' | 'misconception' | 'hint';
  severity: 'success' | 'warning' | 'error' | 'info';
}

export interface FeedbackContext {
  labelId?: string;
  zoneId?: string;
  labelText?: string;
}

/**
 * Get feedback for a game event, checking mechanic-level feedback,
 * misconception matches, and falling back to animationCues.
 */
export function getFeedback(
  mode: InteractionMode,
  event: 'correct' | 'incorrect' | 'completion',
  blueprint: InteractiveDiagramBlueprint,
  context?: FeedbackContext,
): FeedbackResult {
  const mechanic = blueprint.mechanics?.find(m => m.type === mode);
  const fb = mechanic?.feedback;

  // Check for misconception match on incorrect events
  if (event === 'incorrect' && fb?.misconceptions && context) {
    // Resolve label text from context or blueprint
    const labelText = context.labelText
      ?? blueprint.labels.find(l => l.id === context.labelId)?.text;

    if (labelText) {
      const misconception = fb.misconceptions.find(
        m => m.trigger_label === labelText,
      );
      if (misconception) {
        return {
          message: misconception.message,
          type: 'misconception',
          severity: 'warning',
        };
      }
    }
  }

  // Use mechanic-level feedback if available
  if (fb) {
    switch (event) {
      case 'correct':
        if (fb.on_correct) {
          return { message: fb.on_correct, type: 'correct', severity: 'success' };
        }
        break;
      case 'incorrect':
        if (fb.on_incorrect) {
          return { message: fb.on_incorrect, type: 'incorrect', severity: 'error' };
        }
        break;
      case 'completion':
        if (fb.on_completion) {
          return { message: fb.on_completion, type: 'completion', severity: 'success' };
        }
        break;
    }
  }

  // Fallback to animationCues
  const cues = blueprint.animationCues;
  switch (event) {
    case 'correct':
      return {
        message: cues?.correctPlacement ?? 'Correct!',
        type: 'correct',
        severity: 'success',
      };
    case 'incorrect':
      return {
        message: cues?.incorrectPlacement ?? 'Try again!',
        type: 'incorrect',
        severity: 'error',
      };
    case 'completion':
      return {
        message: cues?.allLabeled ?? 'Well done!',
        type: 'completion',
        severity: 'success',
      };
  }
}
