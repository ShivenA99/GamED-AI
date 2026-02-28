import { useReducer, useCallback, useMemo } from 'react';
import {
  ComplexityAnalyzerBlueprint,
  ComplexityAnalyzerGameState,
  ComplexityAnalyzerAction,
  ComplexityAnalyzerScoringState,
} from '../types';

const initialScoring: ComplexityAnalyzerScoringState = {
  totalScore: 0,
  correctCount: 0,
  totalChallenges: 0,
  hintsUsed: 0,
  perChallenge: [],
  bonuses: [],
};

function createInitialState(bp: ComplexityAnalyzerBlueprint): ComplexityAnalyzerGameState {
  return {
    phase: 'INIT',
    currentChallengeIndex: 0,
    selectedAnswer: null,
    selectedSection: null,
    isCorrect: null,
    scoring: { ...initialScoring, totalChallenges: bp.challenges.length },
    hintTier: 0,
    attempts: 0,
  };
}

function createReducer(bp: ComplexityAnalyzerBlueprint) {
  return function reducer(
    state: ComplexityAnalyzerGameState,
    action: ComplexityAnalyzerAction,
  ): ComplexityAnalyzerGameState {
    switch (action.type) {
      case 'START':
        return { ...state, phase: 'CHALLENGE', currentChallengeIndex: 0 };

      case 'SELECT_ANSWER':
        if (state.phase !== 'CHALLENGE') return state;
        return { ...state, selectedAnswer: action.answer };

      case 'SELECT_SECTION':
        if (state.phase !== 'CHALLENGE') return state;
        return { ...state, selectedSection: action.sectionId };

      case 'SUBMIT': {
        if (state.phase !== 'CHALLENGE' || !state.selectedAnswer) return state;
        const challenge = bp.challenges[state.currentChallengeIndex];
        if (!challenge) return state;

        let isCorrect = state.selectedAnswer === challenge.correctComplexity;

        // For bottleneck type, also check selected section
        if (challenge.type === 'find_bottleneck' && challenge.codeSections) {
          const bottleneck = challenge.codeSections.find((s) => s.isBottleneck);
          if (!bottleneck || state.selectedSection !== bottleneck.sectionId) {
            isCorrect = false;
          }
        }

        const hintPenalty = state.hintTier * 0.3; // 30% per hint
        const basePoints = isCorrect
          ? Math.round(challenge.points * (1 - hintPenalty))
          : 0;

        return {
          ...state,
          phase: 'FEEDBACK',
          isCorrect,
          attempts: state.attempts + 1,
          scoring: {
            ...state.scoring,
            totalScore: state.scoring.totalScore + basePoints,
            correctCount: state.scoring.correctCount + (isCorrect ? 1 : 0),
            perChallenge: [
              ...state.scoring.perChallenge,
              {
                challengeId: challenge.challengeId,
                correct: isCorrect,
                points: basePoints,
                attempts: state.attempts + 1,
              },
            ],
          },
        };
      }

      case 'NEXT_CHALLENGE': {
        const nextIndex = state.currentChallengeIndex + 1;
        if (nextIndex >= bp.challenges.length) {
          // All challenges done — compute bonuses
          const bonuses: { type: string; points: number }[] = [];
          const allCorrect = state.scoring.perChallenge.every((c) => c.correct);
          if (allCorrect && state.scoring.perChallenge.length === bp.challenges.length) {
            bonuses.push({ type: 'All challenges perfect', points: 150 });
          }
          if (state.scoring.hintsUsed === 0) {
            bonuses.push({ type: 'No hints used', points: 50 });
          }
          const bonusTotal = bonuses.reduce((s, b) => s + b.points, 0);

          return {
            ...state,
            phase: 'COMPLETED',
            scoring: {
              ...state.scoring,
              totalScore: state.scoring.totalScore + bonusTotal,
              bonuses,
            },
          };
        }

        return {
          ...state,
          phase: 'CHALLENGE',
          currentChallengeIndex: nextIndex,
          selectedAnswer: null,
          selectedSection: null,
          isCorrect: null,
          hintTier: 0,
          attempts: 0,
        };
      }

      case 'USE_HINT': {
        const newTier = Math.max(state.hintTier, action.tier);
        const isNewHint = newTier > state.hintTier;
        return {
          ...state,
          hintTier: newTier,
          scoring: {
            ...state.scoring,
            hintsUsed: state.scoring.hintsUsed + (isNewHint ? 1 : 0),
          },
        };
      }

      case 'CA_COMPLETE':
        return { ...state, phase: 'COMPLETED' };

      case 'CA_RESET':
        return createInitialState(bp);

      default:
        return state;
    }
  };
}

export function useComplexityAnalyzerMachine(blueprint: ComplexityAnalyzerBlueprint) {
  const reducer = useMemo(() => createReducer(blueprint), [blueprint]);
  const initializer = useCallback(
    () => createInitialState(blueprint),
    [blueprint],
  );

  const [state, dispatch] = useReducer(reducer, undefined, initializer);

  const start = useCallback(() => dispatch({ type: 'START' }), []);
  const selectAnswer = useCallback(
    (answer: string) => dispatch({ type: 'SELECT_ANSWER', answer }),
    [],
  );
  const selectSection = useCallback(
    (sectionId: string) => dispatch({ type: 'SELECT_SECTION', sectionId }),
    [],
  );
  const submit = useCallback(() => dispatch({ type: 'SUBMIT' }), []);
  const nextChallenge = useCallback(() => dispatch({ type: 'NEXT_CHALLENGE' }), []);
  const useHint = useCallback(
    (tier: number) => dispatch({ type: 'USE_HINT', tier }),
    [],
  );
  const complete = useCallback(() => dispatch({ type: 'CA_COMPLETE' }), []);
  const reset = useCallback(() => dispatch({ type: 'CA_RESET' }), []);

  const currentChallenge = blueprint.challenges[state.currentChallengeIndex] ?? null;

  return {
    state,
    currentChallenge,
    start,
    selectAnswer,
    selectSection,
    submit,
    nextChallenge,
    useHint,
    complete,
    reset,
  };
}
