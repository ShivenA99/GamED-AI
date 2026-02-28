import { useMemo } from 'react';
import { BugHunterScoringState } from '../types';

export interface BugHunterScoreSummary {
  finalScore: number;
  accuracy: number; // 0-100
  maxPossible: number;
  bonusTotal: number;
  message: string;
}

export function useBugHunterScoring(scoring: BugHunterScoringState): BugHunterScoreSummary {
  return useMemo(() => {
    const bonusTotal = scoring.bonuses.reduce((s, b) => s + b.points, 0);
    const finalScore = Math.max(0, scoring.totalScore);

    const accuracy =
      scoring.totalBugs > 0
        ? Math.round((scoring.bugsFound / scoring.totalBugs) * 100)
        : 0;

    // Max possible: highest base (200 for free-text, 150 for MCQ) * max diff mult (2.0) + all bonuses (225)
    const maxPossible = scoring.totalBugs * 200 * 2 + 225;

    const message =
      accuracy === 100 && scoring.wrongLineClicks === 0
        ? 'Perfect debugging! You found every bug without a single wrong click!'
        : accuracy === 100
        ? 'All bugs found! Great debugging skills.'
        : accuracy >= 50
        ? 'Good progress! Keep sharpening your debugging instincts.'
        : 'Debugging is hard — keep practicing and you\'ll get better!';

    return { finalScore, accuracy, maxPossible, bonusTotal, message };
  }, [scoring]);
}
