import { useCallback } from 'react';
import {
  ScoringConfig,
  ScoringState,
  DEFAULT_SCORING,
  PredictionResult,
  ExtendedPrediction,
} from '../types';

export function getStreakMultiplier(streak: number, config: ScoringConfig): number {
  let multiplier = 1;
  for (const t of config.streakThresholds) {
    if (streak >= t.min) multiplier = t.multiplier;
  }
  return multiplier;
}

export function computeHintPenalty(hintsUsedThisStep: number, config: ScoringConfig): number {
  let totalPenalty = 0;
  for (let i = 0; i < hintsUsedThisStep && i < config.hintPenalties.length; i++) {
    totalPenalty += config.hintPenalties[i];
  }
  return Math.min(totalPenalty, 1); // cap at 100%
}

export function computePartialScore(prediction: ExtendedPrediction, result: PredictionResult): number {
  if (result.isCorrect) return 1;

  if (prediction.type === 'arrangement') {
    const player = result.playerAnswer as number[];
    const correct = result.correctAnswer as number[];
    if (player.length !== correct.length) return 0;
    let matches = 0;
    for (let i = 0; i < correct.length; i++) {
      if (player[i] === correct[i]) matches++;
    }
    return matches / correct.length;
  }

  if (prediction.type === 'multi_select') {
    const selected = new Set(result.playerAnswer as string[]);
    const correct = new Set(result.correctAnswer as string[]);
    let hits = 0;
    let misses = 0;
    for (const s of selected) {
      if (correct.has(s)) hits++;
      else misses++;
    }
    return Math.max(0, (hits - misses) / correct.size);
  }

  return 0; // value and multiple_choice: binary
}

export function computeStepScore(
  partialScore: number,
  streak: number,
  hintsUsedThisStep: number,
  config: ScoringConfig,
): number {
  const multiplier = getStreakMultiplier(streak, config);
  const hintPenalty = computeHintPenalty(hintsUsedThisStep, config);
  return Math.round(config.basePoints * partialScore * multiplier * (1 - hintPenalty));
}

export function useScoring(config: ScoringConfig = DEFAULT_SCORING) {
  const scoreStep = useCallback(
    (
      prediction: ExtendedPrediction,
      result: PredictionResult,
      currentStreak: number,
      hintsUsedThisStep: number,
    ) => {
      const partial = computePartialScore(prediction, result);
      const points = computeStepScore(partial, currentStreak, hintsUsedThisStep, config);
      return { points, partial };
    },
    [config],
  );

  const computeFinalScore = useCallback(
    (scoring: ScoringState): number => {
      if (scoring.incorrectCount === 0 && scoring.totalPredictions > 0) {
        return Math.round(scoring.totalScore * (1 + config.perfectRunBonus));
      }
      return scoring.totalScore;
    },
    [config],
  );

  return { scoreStep, computeFinalScore, getStreakMultiplier: (s: number) => getStreakMultiplier(s, config) };
}
