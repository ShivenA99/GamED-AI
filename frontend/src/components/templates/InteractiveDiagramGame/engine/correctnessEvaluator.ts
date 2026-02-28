/**
 * correctnessEvaluator.ts — Centralized correctness evaluation.
 * Moves correctness authority into the engine so the store is the single source of truth.
 * Components and dispatch should NOT decide correctness.
 * No React, no Zustand.
 */

import type {
  InteractiveDiagramBlueprint,
  IdentificationProgress,
} from '../types';

export interface IdentifyEvaluation {
  isCorrect: boolean;
  completedZoneId?: string;
}

/**
 * Evaluate a click_to_identify action.
 * Returns whether the clicked zone matches the current prompt.
 */
export function evaluateIdentification(
  zoneId: string,
  progress: IdentificationProgress,
  blueprint: InteractiveDiagramBlueprint,
): IdentifyEvaluation {
  const prompts = blueprint.identificationPrompts || [];
  const currentPrompt = prompts[progress.currentPromptIndex];
  const isCorrect = currentPrompt?.zoneId === zoneId;
  return {
    isCorrect,
    completedZoneId: isCorrect ? zoneId : undefined,
  };
}

export interface DescriptionMatchEvaluation {
  isCorrect: boolean;
}

/**
 * Evaluate a description_matching action.
 *
 * Description matching is zone-centric: the player is shown a zone's description
 * and must click the correct zone. `descriptionZoneId` is the zone whose description
 * is displayed; `clickedZoneId` is what the player clicked. Correct when they match.
 *
 * Falls back to label-based lookup for backward compatibility.
 */
export function evaluateDescriptionMatch(
  descriptionZoneId: string,
  clickedZoneId: string,
  blueprint: InteractiveDiagramBlueprint,
): DescriptionMatchEvaluation {
  // Primary: zone-centric — does the clicked zone match the described zone?
  if (blueprint.diagram?.zones?.some((z: { id: string }) => z.id === descriptionZoneId)) {
    return { isCorrect: descriptionZoneId === clickedZoneId };
  }
  // Fallback: label-centric (legacy) — find label, check its correctZoneId
  const label = blueprint.labels.find(l => l.id === descriptionZoneId);
  return {
    isCorrect: label ? label.correctZoneId === clickedZoneId : false,
  };
}
