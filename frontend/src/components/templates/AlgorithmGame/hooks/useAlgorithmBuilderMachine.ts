import { useReducer, useCallback, useMemo } from 'react';
import {
  AlgorithmBuilderBlueprint,
  AlgorithmBuilderGameState,
  AlgorithmBuilderAction,
  AlgorithmBuilderScoringState,
  ParsonsBlock,
  BlockFeedback,
} from '../types';

const initialScoring: AlgorithmBuilderScoringState = {
  totalScore: 0,
  attempts: 0,
  hintsUsed: 0,
  hintPenalty: 0,
  perBlockFeedback: [],
  bonuses: [],
};

function shuffleArray<T>(arr: T[]): T[] {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

function createInitialState(_bp: AlgorithmBuilderBlueprint): AlgorithmBuilderGameState {
  return {
    phase: 'INIT',
    sourceBlocks: [],
    solutionBlocks: [],
    scoring: { ...initialScoring },
    hintTier: 0,
    feedbackMessage: null,
    feedbackType: null,
    activeBlockId: null,
  };
}

function createReducer(bp: AlgorithmBuilderBlueprint) {
  return function reducer(
    state: AlgorithmBuilderGameState,
    action: AlgorithmBuilderAction,
  ): AlgorithmBuilderGameState {
    switch (action.type) {
      case 'START_BUILDING': {
        // Combine correct blocks + distractors, strip indent to 0, shuffle
        const allBlocks: ParsonsBlock[] = [
          ...(bp.correct_order ?? []).map((b) => ({ ...b, indent_level: 0 })),
          ...(bp.distractors ?? []).map((b) => ({ ...b, indent_level: 0 })),
        ];
        return {
          ...state,
          phase: 'BUILDING',
          sourceBlocks: shuffleArray(allBlocks),
          solutionBlocks: [],
          scoring: { ...initialScoring },
          hintTier: 0,
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'MOVE_BLOCK_TO_SOLUTION': {
        if (state.phase !== 'BUILDING') return state;
        const block = state.sourceBlocks.find((b) => b.id === action.blockId);
        if (!block) return state;
        const newSource = state.sourceBlocks.filter((b) => b.id !== action.blockId);
        const newSolution = [...state.solutionBlocks];
        const insertIndex = Math.min(action.index, newSolution.length);
        newSolution.splice(insertIndex, 0, block);
        return {
          ...state,
          sourceBlocks: newSource,
          solutionBlocks: newSolution,
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'MOVE_BLOCK_TO_SOURCE': {
        if (state.phase !== 'BUILDING') return state;
        const block = state.solutionBlocks.find((b) => b.id === action.blockId);
        if (!block) return state;
        return {
          ...state,
          sourceBlocks: [...state.sourceBlocks, { ...block, indent_level: 0 }],
          solutionBlocks: state.solutionBlocks.filter((b) => b.id !== action.blockId),
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'REORDER_SOLUTION': {
        if (state.phase !== 'BUILDING') return state;
        const oldIndex = state.solutionBlocks.findIndex((b) => b.id === action.activeId);
        const newIndex = state.solutionBlocks.findIndex((b) => b.id === action.overId);
        if (oldIndex === -1 || newIndex === -1) return state;
        const newSolution = [...state.solutionBlocks];
        const [moved] = newSolution.splice(oldIndex, 1);
        newSolution.splice(newIndex, 0, moved);
        return { ...state, solutionBlocks: newSolution };
      }

      case 'SET_INDENT': {
        if (state.phase !== 'BUILDING') return state;
        return {
          ...state,
          solutionBlocks: state.solutionBlocks.map((b) =>
            b.id === action.blockId
              ? { ...b, indent_level: Math.max(0, Math.min(3, action.indent)) }
              : b,
          ),
        };
      }

      case 'SET_ACTIVE_BLOCK':
        return { ...state, activeBlockId: action.blockId };

      case 'SUBMIT': {
        return {
          ...state,
          phase: action.allCorrect ? 'COMPLETED' : 'FEEDBACK_SHOWN',
          scoring: {
            ...state.scoring,
            totalScore: action.score,
            attempts: state.scoring.attempts + 1,
            perBlockFeedback: action.feedback,
            bonuses: action.bonuses,
          },
          feedbackMessage: action.allCorrect
            ? 'Perfect! All blocks are in the correct position.'
            : 'Some blocks need rearranging. Check the highlighted feedback.',
          feedbackType: action.allCorrect ? 'success' : 'error',
        };
      }

      case 'RETRY':
        return {
          ...state,
          phase: 'BUILDING',
          scoring: { ...state.scoring, perBlockFeedback: [] },
          feedbackMessage: null,
          feedbackType: null,
        };

      case 'USE_HINT': {
        const newTier = Math.max(state.hintTier, action.tier);
        const isNewHint = newTier > state.hintTier;
        return {
          ...state,
          hintTier: newTier,
          scoring: {
            ...state.scoring,
            hintsUsed: state.scoring.hintsUsed + (isNewHint ? 1 : 0),
            hintPenalty: state.scoring.hintPenalty + (isNewHint ? 40 : 0),
          },
        };
      }

      case 'COMPLETE':
        return { ...state, phase: 'COMPLETED' };

      case 'RESET':
        return createInitialState(bp);

      default:
        return state;
    }
  };
}

export function useAlgorithmBuilderMachine(blueprint: AlgorithmBuilderBlueprint) {
  const reducer = useMemo(() => createReducer(blueprint), [blueprint]);
  const initializer = useCallback(
    () => createInitialState(blueprint),
    [blueprint],
  );

  const [state, dispatch] = useReducer(reducer, undefined, initializer);

  const startBuilding = useCallback(() => dispatch({ type: 'START_BUILDING' }), []);
  const moveToSolution = useCallback(
    (blockId: string, index: number) =>
      dispatch({ type: 'MOVE_BLOCK_TO_SOLUTION', blockId, index }),
    [],
  );
  const moveToSource = useCallback(
    (blockId: string) => dispatch({ type: 'MOVE_BLOCK_TO_SOURCE', blockId }),
    [],
  );
  const reorderSolution = useCallback(
    (activeId: string, overId: string) =>
      dispatch({ type: 'REORDER_SOLUTION', activeId, overId }),
    [],
  );
  const setIndent = useCallback(
    (blockId: string, indent: number) =>
      dispatch({ type: 'SET_INDENT', blockId, indent }),
    [],
  );
  const setActiveBlock = useCallback(
    (blockId: string | null) => dispatch({ type: 'SET_ACTIVE_BLOCK', blockId }),
    [],
  );
  const submit = useCallback(
    (
      feedback: BlockFeedback[],
      score: number,
      bonuses: { type: string; points: number }[],
      allCorrect: boolean,
    ) => dispatch({ type: 'SUBMIT', feedback, score, bonuses, allCorrect }),
    [],
  );
  const retry = useCallback(() => dispatch({ type: 'RETRY' }), []);
  const useHint = useCallback(
    (tier: number) => dispatch({ type: 'USE_HINT', tier }),
    [],
  );
  const complete = useCallback(() => dispatch({ type: 'COMPLETE' }), []);
  const reset = useCallback(() => dispatch({ type: 'RESET' }), []);

  return {
    state,
    dispatch,
    startBuilding,
    moveToSolution,
    moveToSource,
    reorderSolution,
    setIndent,
    setActiveBlock,
    submit,
    retry,
    useHint,
    complete,
    reset,
  };
}
