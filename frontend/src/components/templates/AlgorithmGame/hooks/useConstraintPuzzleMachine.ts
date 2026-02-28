import { useReducer, useCallback, useMemo } from 'react';
import {
  ConstraintPuzzleBlueprint,
  ConstraintPuzzleGameState,
  ConstraintPuzzleAction,
  ConstraintPuzzleScoringState,
  KnapsackPuzzleData,
  NQueensPuzzleData,
  CoinChangePuzzleData,
  ActivitySelectionPuzzleData,
} from '../types';

const initialScoring: ConstraintPuzzleScoringState = {
  totalScore: 0,
  moveCount: 0,
  hintsUsed: 0,
  optimalityRatio: 0,
  bonuses: [],
};

function createInitialState(): ConstraintPuzzleGameState {
  return {
    phase: 'INIT',
    selectedItemIds: [],
    queenPositions: [],
    selectedCoins: [],
    selectedActivityIds: [],
    scoring: { ...initialScoring },
    hintTier: 0,
    moveHistory: [],
    feedbackMessage: null,
    feedbackType: null,
  };
}

// ---- Knapsack helpers ----
function knapsackValue(data: KnapsackPuzzleData, selectedIds: string[]): number {
  return data.items
    .filter((it) => selectedIds.includes(it.id))
    .reduce((s, it) => s + it.value, 0);
}

function knapsackWeight(data: KnapsackPuzzleData, selectedIds: string[]): number {
  return data.items
    .filter((it) => selectedIds.includes(it.id))
    .reduce((s, it) => s + it.weight, 0);
}

// ---- N-Queens helpers ----
function queensConflict(
  positions: { row: number; col: number }[],
): boolean {
  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      const a = positions[i];
      const b = positions[j];
      if (a.row === b.row || a.col === b.col) return true;
      if (Math.abs(a.row - b.row) === Math.abs(a.col - b.col)) return true;
    }
  }
  return false;
}

// ---- Coin change helpers ----
function coinSum(coins: number[]): number {
  return coins.reduce((s, c) => s + c, 0);
}

// ---- Activity selection helpers ----
function activitiesOverlap(
  data: ActivitySelectionPuzzleData,
  selectedIds: string[],
): boolean {
  const selected = data.activities
    .filter((a) => selectedIds.includes(a.id))
    .sort((a, b) => a.start - b.start);
  for (let i = 1; i < selected.length; i++) {
    if (selected[i].start < selected[i - 1].end) return true;
  }
  return false;
}

function createReducer(bp: ConstraintPuzzleBlueprint) {
  return function reducer(
    state: ConstraintPuzzleGameState,
    action: ConstraintPuzzleAction,
  ): ConstraintPuzzleGameState {
    switch (action.type) {
      case 'CP_START':
        return { ...state, phase: 'PLAYING' };

      case 'TOGGLE_ITEM': {
        if (state.phase !== 'PLAYING') return state;
        const has = state.selectedItemIds.includes(action.itemId);
        const next = has
          ? state.selectedItemIds.filter((id) => id !== action.itemId)
          : [...state.selectedItemIds, action.itemId];

        // check weight
        if (!has && bp.puzzleData.type === 'knapsack') {
          const w = knapsackWeight(bp.puzzleData, next);
          if (w > bp.puzzleData.capacity) {
            return {
              ...state,
              feedbackMessage: 'Over capacity! Remove something first.',
              feedbackType: 'error',
            };
          }
        }
        return {
          ...state,
          selectedItemIds: next,
          moveHistory: [...state.moveHistory, `toggle:${action.itemId}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'PLACE_QUEEN': {
        if (state.phase !== 'PLAYING') return state;
        const existing = state.queenPositions.find(
          (q) => q.row === action.row && q.col === action.col,
        );
        if (existing) return state; // already placed

        const newPositions = [...state.queenPositions, { row: action.row, col: action.col }];
        const hasConflict = queensConflict(newPositions);

        return {
          ...state,
          queenPositions: newPositions,
          moveHistory: [...state.moveHistory, `place:${action.row},${action.col}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: hasConflict ? 'Queens conflict! Two queens threaten each other.' : null,
          feedbackType: hasConflict ? 'error' : null,
        };
      }

      case 'REMOVE_QUEEN': {
        if (state.phase !== 'PLAYING') return state;
        const filtered = state.queenPositions.filter(
          (q) => !(q.row === action.row && q.col === action.col),
        );
        return {
          ...state,
          queenPositions: filtered,
          moveHistory: [...state.moveHistory, `remove:${action.row},${action.col}`],
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'ADD_COIN': {
        if (state.phase !== 'PLAYING') return state;
        const newCoins = [...state.selectedCoins, action.denomination];
        if (bp.puzzleData.type === 'coin_change') {
          const sum = coinSum(newCoins);
          if (sum > bp.puzzleData.targetAmount) {
            return {
              ...state,
              feedbackMessage: `Total ${sum} exceeds target ${bp.puzzleData.targetAmount}!`,
              feedbackType: 'error',
            };
          }
        }
        return {
          ...state,
          selectedCoins: newCoins,
          moveHistory: [...state.moveHistory, `add:${action.denomination}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'REMOVE_COIN': {
        if (state.phase !== 'PLAYING') return state;
        const coins = [...state.selectedCoins];
        coins.splice(action.index, 1);
        return {
          ...state,
          selectedCoins: coins,
          moveHistory: [...state.moveHistory, `removecoin:${action.index}`],
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'TOGGLE_ACTIVITY': {
        if (state.phase !== 'PLAYING') return state;
        const has = state.selectedActivityIds.includes(action.activityId);
        const next = has
          ? state.selectedActivityIds.filter((id) => id !== action.activityId)
          : [...state.selectedActivityIds, action.activityId];

        // check overlap
        if (!has && bp.puzzleData.type === 'activity_selection') {
          if (activitiesOverlap(bp.puzzleData, next)) {
            return {
              ...state,
              feedbackMessage: 'Activities overlap! Remove a conflicting one first.',
              feedbackType: 'error',
            };
          }
        }
        return {
          ...state,
          selectedActivityIds: next,
          moveHistory: [...state.moveHistory, `activity:${action.activityId}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'CP_UNDO': {
        if (state.phase !== 'PLAYING' || state.moveHistory.length === 0) return state;
        // Simple undo: reset to initial playing state
        return {
          ...state,
          selectedItemIds: [],
          queenPositions:
            bp.puzzleData.type === 'n_queens' && bp.puzzleData.prePlaced
              ? [...bp.puzzleData.prePlaced]
              : [],
          selectedCoins: [],
          selectedActivityIds: [],
          moveHistory: [],
          feedbackMessage: 'Board reset.',
          feedbackType: 'info',
        };
      }

      case 'CHECK_SOLUTION': {
        if (state.phase !== 'PLAYING') return state;
        const data = bp.puzzleData;
        let playerValue = 0;
        let isValid = false;

        switch (data.type) {
          case 'knapsack': {
            const w = knapsackWeight(data, state.selectedItemIds);
            playerValue = knapsackValue(data, state.selectedItemIds);
            isValid = w <= data.capacity && state.selectedItemIds.length > 0;
            break;
          }
          case 'n_queens': {
            isValid =
              state.queenPositions.length === data.boardSize &&
              !queensConflict(state.queenPositions);
            playerValue = isValid ? bp.optimalValue : state.queenPositions.length;
            break;
          }
          case 'coin_change': {
            const sum = coinSum(state.selectedCoins);
            isValid = sum === data.targetAmount;
            playerValue = isValid ? data.targetAmount / state.selectedCoins.length : 0;
            break;
          }
          case 'activity_selection': {
            isValid =
              !activitiesOverlap(data, state.selectedActivityIds) &&
              state.selectedActivityIds.length > 0;
            playerValue = state.selectedActivityIds.length;
            break;
          }
        }

        if (!isValid) {
          return {
            ...state,
            feedbackMessage: 'Invalid solution. Check the constraints and try again.',
            feedbackType: 'error',
          };
        }

        const optRatio = bp.optimalValue > 0 ? playerValue / bp.optimalValue : 0;
        const baseScore = Math.round(300 * Math.min(optRatio, 1));
        const hintPenalty = state.hintTier * 40;

        const bonuses: { type: string; points: number }[] = [];
        if (optRatio >= 1) {
          bonuses.push({ type: 'Optimal solution!', points: 100 });
        }
        if (state.scoring.hintsUsed === 0) {
          bonuses.push({ type: 'No hints used', points: 50 });
        }
        const bonusTotal = bonuses.reduce((s, b) => s + b.points, 0);

        return {
          ...state,
          phase: 'PUZZLE_SOLVED',
          feedbackMessage: optRatio >= 1
            ? 'Perfect! You found the optimal solution!'
            : `Good solution! Your answer achieves ${Math.round(optRatio * 100)}% of optimal.`,
          feedbackType: optRatio >= 1 ? 'success' : 'info',
          scoring: {
            ...state.scoring,
            totalScore: Math.max(baseScore - hintPenalty, 0) + bonusTotal,
            optimalityRatio: optRatio,
            bonuses,
          },
        };
      }

      case 'REVEAL_ALGORITHM':
        return { ...state, phase: 'ALGORITHM_REVEAL' };

      case 'CP_USE_HINT': {
        const newTier = Math.max(state.hintTier, action.tier);
        const isNew = newTier > state.hintTier;
        return {
          ...state,
          hintTier: newTier,
          scoring: {
            ...state.scoring,
            hintsUsed: state.scoring.hintsUsed + (isNew ? 1 : 0),
          },
        };
      }

      case 'CP_COMPLETE':
        return { ...state, phase: 'COMPLETED' };

      case 'CP_RESET':
        return createInitialState();

      default:
        return state;
    }
  };
}

export function useConstraintPuzzleMachine(blueprint: ConstraintPuzzleBlueprint) {
  const reducer = useMemo(() => createReducer(blueprint), [blueprint]);
  const [state, dispatch] = useReducer(reducer, undefined, createInitialState);

  const start = useCallback(() => dispatch({ type: 'CP_START' }), []);
  const toggleItem = useCallback(
    (itemId: string) => dispatch({ type: 'TOGGLE_ITEM', itemId }),
    [],
  );
  const placeQueen = useCallback(
    (row: number, col: number) => dispatch({ type: 'PLACE_QUEEN', row, col }),
    [],
  );
  const removeQueen = useCallback(
    (row: number, col: number) => dispatch({ type: 'REMOVE_QUEEN', row, col }),
    [],
  );
  const addCoin = useCallback(
    (denomination: number) => dispatch({ type: 'ADD_COIN', denomination }),
    [],
  );
  const removeCoin = useCallback(
    (index: number) => dispatch({ type: 'REMOVE_COIN', index }),
    [],
  );
  const toggleActivity = useCallback(
    (activityId: string) => dispatch({ type: 'TOGGLE_ACTIVITY', activityId }),
    [],
  );
  const undo = useCallback(() => dispatch({ type: 'CP_UNDO' }), []);
  const checkSolution = useCallback(() => dispatch({ type: 'CHECK_SOLUTION' }), []);
  const revealAlgorithm = useCallback(() => dispatch({ type: 'REVEAL_ALGORITHM' }), []);
  const useHint = useCallback(
    (tier: number) => dispatch({ type: 'CP_USE_HINT', tier }),
    [],
  );
  const complete = useCallback(() => dispatch({ type: 'CP_COMPLETE' }), []);
  const reset = useCallback(() => dispatch({ type: 'CP_RESET' }), []);

  return {
    state,
    start,
    toggleItem,
    placeQueen,
    removeQueen,
    addCoin,
    removeCoin,
    toggleActivity,
    undo,
    checkSolution,
    revealAlgorithm,
    useHint,
    complete,
    reset,
  };
}
