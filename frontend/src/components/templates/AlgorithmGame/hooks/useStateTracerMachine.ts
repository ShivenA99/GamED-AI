import { useReducer, useCallback } from 'react';
import {
  GameState,
  GameAction,
  ScoringState,
  ExecutionStep,
} from '../types';

const initialScoring: ScoringState = {
  totalScore: 0,
  streak: 0,
  maxStreak: 0,
  correctCount: 0,
  incorrectCount: 0,
  totalPredictions: 0,
  hintsUsed: 0,
  stepScores: [],
  hintPenaltiesApplied: [],
};

const initialState: GameState = {
  phase: 'INIT',
  currentStepIndex: 0,
  executedLines: [],
  scoring: { ...initialScoring },
  hintState: { currentTier: 0, hintsForStep: [] },
  lastResult: null,
  isPlaying: false,
  speed: 1,
};

function reducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'ADVANCE_TO_STEP': {
      const newExecuted = state.executedLines.includes(action.stepIndex)
        ? state.executedLines
        : [...state.executedLines, action.stepIndex];
      return {
        ...state,
        phase: 'SHOWING_STATE',
        currentStepIndex: action.stepIndex,
        executedLines: newExecuted,
        hintState: { currentTier: 0, hintsForStep: [] },
        lastResult: null,
      };
    }

    case 'SHOW_PREDICTION':
      return {
        ...state,
        phase: 'AWAITING_PREDICTION',
      };

    case 'SUBMIT_PREDICTION': {
      const { result, pointsEarned } = action;
      const newStreak = result.isCorrect ? state.scoring.streak + 1 : 0;
      return {
        ...state,
        phase: 'PREDICTION_SUBMITTED',
        lastResult: result,
        scoring: {
          ...state.scoring,
          totalScore: state.scoring.totalScore + pointsEarned,
          streak: newStreak,
          maxStreak: Math.max(state.scoring.maxStreak, newStreak),
          correctCount: state.scoring.correctCount + (result.isCorrect ? 1 : 0),
          incorrectCount: state.scoring.incorrectCount + (result.isCorrect ? 0 : 1),
          totalPredictions: state.scoring.totalPredictions + 1,
          stepScores: [...state.scoring.stepScores, pointsEarned],
          hintPenaltiesApplied: [
            ...state.scoring.hintPenaltiesApplied,
            state.hintState.currentTier,
          ],
        },
      };
    }

    case 'FINISH_REVEAL':
      return {
        ...state,
        phase: 'REVEALING_RESULT',
      };

    case 'USE_HINT': {
      const newTier = Math.max(state.hintState.currentTier, action.tier);
      return {
        ...state,
        hintState: {
          ...state.hintState,
          currentTier: newTier,
        },
        scoring: {
          ...state.scoring,
          hintsUsed: state.scoring.hintsUsed + (newTier > state.hintState.currentTier ? 1 : 0),
        },
      };
    }

    case 'COMPLETE_GAME':
      return {
        ...state,
        phase: 'COMPLETED',
        isPlaying: false,
      };

    case 'RESET':
      return { ...initialState };

    case 'SET_PLAYING':
      return { ...state, isPlaying: action.isPlaying };

    case 'SET_SPEED':
      return { ...state, speed: action.speed };

    default:
      return state;
  }
}

export function useStateTracerMachine(steps: ExecutionStep[]) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const goToStep = useCallback(
    (index: number) => {
      if (index < 0 || index >= steps.length) return;
      dispatch({ type: 'ADVANCE_TO_STEP', stepIndex: index });

      // If the step has a prediction, transition to AWAITING_PREDICTION after a short delay
      const step = steps[index];
      if (step.prediction) {
        setTimeout(() => dispatch({ type: 'SHOW_PREDICTION' }), 400);
      }
    },
    [steps],
  );

  const advanceToNext = useCallback(() => {
    const nextIndex = state.currentStepIndex + 1;
    if (nextIndex >= steps.length) {
      dispatch({ type: 'COMPLETE_GAME' });
      return;
    }
    goToStep(nextIndex);
  }, [state.currentStepIndex, steps.length, goToStep]);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return {
    state,
    dispatch,
    goToStep,
    advanceToNext,
    reset,
    currentStep: steps[state.currentStepIndex] as ExecutionStep | undefined,
  };
}
