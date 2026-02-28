// ============================================================================
// Generic Constraint Puzzle State Machine (useReducer-based)
// ============================================================================
// Replaces useConstraintPuzzleMachine with a generic, data-driven reducer.
// All puzzle types handled via boardConfig + constraints + scoringConfig.
// ============================================================================

import { useReducer, useCallback, useMemo } from 'react';
import {
  GenericConstraintPuzzleBlueprint,
  GenericPuzzleState,
  GenericPuzzleAction,
  ConstraintPuzzleScoringState,
  ConstraintResult,
  BoardConfig,
  GridPlacementBoardConfig,
  MultisetBuildingBoardConfig,
} from '../constraintPuzzle/constraintPuzzleTypes';
import { evaluateConstraints, allConstraintsSatisfied } from '../constraintPuzzle/constraintEvaluator';
import { computePlayerValue } from '../constraintPuzzle/scoringEvaluator';
import { getInitialBoardState } from '../constraintPuzzle/boardRegistry';

// ---------------------------------------------------------------------------
// Initial State
// ---------------------------------------------------------------------------

const initialScoring: ConstraintPuzzleScoringState = {
  totalScore: 0,
  moveCount: 0,
  hintsUsed: 0,
  optimalityRatio: 0,
  bonuses: [],
};

function createInitialState(config: BoardConfig): GenericPuzzleState {
  const boardState = getInitialBoardState(config);
  return {
    phase: 'INIT',
    selectedIds: [],
    placements: [],
    bag: [],
    selectedEdgeIds: [],
    assignments: {},
    sequence: [],
    scoring: { ...initialScoring },
    hintTier: 0,
    moveHistory: [],
    feedbackMessage: null,
    feedbackType: null,
    constraintResults: [],
    ...boardState,
  };
}

// ---------------------------------------------------------------------------
// Reducer factory (captures blueprint in closure)
// ---------------------------------------------------------------------------

function createReducer(bp: GenericConstraintPuzzleBlueprint) {
  const config = bp.boardConfig;

  return function reducer(
    state: GenericPuzzleState,
    action: GenericPuzzleAction,
  ): GenericPuzzleState {
    switch (action.type) {
      // ---- Lifecycle ----
      case 'CP_START':
        return { ...state, phase: 'PLAYING' };

      case 'REVEAL_ALGORITHM':
        return { ...state, phase: 'ALGORITHM_REVEAL' };

      case 'CP_COMPLETE':
        return { ...state, phase: 'COMPLETED' };

      case 'CP_RESET':
        return createInitialState(config);

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

      case 'CP_UNDO': {
        if (state.phase !== 'PLAYING' || state.moveHistory.length === 0) return state;
        const boardState = getInitialBoardState(config);
        return {
          ...state,
          ...boardState,
          moveHistory: [],
          constraintResults: [],
          feedbackMessage: 'Board reset.',
          feedbackType: 'info',
        };
      }

      // ---- item_selection / graph_interaction (nodes) ----
      case 'TOGGLE': {
        if (state.phase !== 'PLAYING') return state;
        const has = state.selectedIds.includes(action.id);
        const next = has
          ? state.selectedIds.filter((id) => id !== action.id)
          : [...state.selectedIds, action.id];

        const nextState: GenericPuzzleState = {
          ...state,
          selectedIds: next,
          moveHistory: [...state.moveHistory, `toggle:${action.id}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };

        // Live constraint check (for capacity feedback)
        if (!has && bp.showConstraintsVisually) {
          const results = evaluateConstraints(bp.constraints, nextState, config);
          const capacityViolation = results.find(
            (r) => !r.satisfied && r.constraint.type === 'capacity',
          );
          if (capacityViolation) {
            return {
              ...state,
              feedbackMessage: capacityViolation.message,
              feedbackType: 'error',
              constraintResults: results,
            };
          }
          // Check overlap violation
          const overlapViolation = results.find(
            (r) => !r.satisfied && r.constraint.type === 'no_overlap',
          );
          if (overlapViolation) {
            return {
              ...state,
              feedbackMessage: overlapViolation.message,
              feedbackType: 'error',
              constraintResults: results,
            };
          }
          nextState.constraintResults = results;
        }
        return nextState;
      }

      // ---- grid_placement ----
      case 'PLACE': {
        if (state.phase !== 'PLAYING') return state;
        const exists = state.placements.some(
          (p) => p.row === action.row && p.col === action.col,
        );
        if (exists) return state;

        const newPlacements = [...state.placements, { row: action.row, col: action.col }];
        const nextState: GenericPuzzleState = {
          ...state,
          placements: newPlacements,
          moveHistory: [...state.moveHistory, `place:${action.row},${action.col}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };

        if (bp.showConstraintsVisually) {
          const results = evaluateConstraints(bp.constraints, nextState, config);
          const conflict = results.find(
            (r) => !r.satisfied && r.constraint.type === 'no_conflict',
          );
          nextState.constraintResults = results;
          if (conflict) {
            nextState.feedbackMessage = conflict.message;
            nextState.feedbackType = 'error';
          }
        }
        return nextState;
      }

      case 'REMOVE_PLACEMENT': {
        if (state.phase !== 'PLAYING') return state;
        // Don't allow removal of locked pre-populated pieces
        if (config.boardType === 'grid_placement') {
          const cfg = config as GridPlacementBoardConfig;
          const isLocked = cfg.prePopulated?.some(
            (p) => p.row === action.row && p.col === action.col && p.locked,
          );
          if (isLocked) return state;
        }
        const filtered = state.placements.filter(
          (p) => !(p.row === action.row && p.col === action.col),
        );
        return {
          ...state,
          placements: filtered,
          moveHistory: [...state.moveHistory, `remove:${action.row},${action.col}`],
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      // ---- multiset_building ----
      case 'ADD_TO_BAG': {
        if (state.phase !== 'PLAYING') return state;

        // Check maxCount for pool items
        if (config.boardType === 'multiset_building') {
          const cfg = config as MultisetBuildingBoardConfig;
          const poolItem = cfg.pool.find((p) => p.value === action.value);
          if (poolItem?.maxCount != null) {
            const currentCount = state.bag.filter((v) => v === action.value).length;
            if (currentCount >= poolItem.maxCount) {
              return {
                ...state,
                feedbackMessage: `Max ${poolItem.maxCount} of "${poolItem.label ?? action.value}" allowed`,
                feedbackType: 'error',
              };
            }
          }
        }

        const newBag = [...state.bag, action.value];
        const nextState: GenericPuzzleState = {
          ...state,
          bag: newBag,
          moveHistory: [...state.moveHistory, `add:${action.value}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };

        // Check exact_target overshoot
        if (bp.showConstraintsVisually) {
          const results = evaluateConstraints(bp.constraints, nextState, config);
          const targetConstraint = results.find(
            (r) => r.constraint.type === 'exact_target',
          );
          if (
            targetConstraint &&
            targetConstraint.currentValue != null &&
            targetConstraint.targetValue != null &&
            targetConstraint.currentValue > targetConstraint.targetValue
          ) {
            return {
              ...state,
              feedbackMessage: `Total ${targetConstraint.currentValue} exceeds target ${targetConstraint.targetValue}!`,
              feedbackType: 'error',
              constraintResults: results,
            };
          }
          nextState.constraintResults = results;
        }
        return nextState;
      }

      case 'REMOVE_FROM_BAG': {
        if (state.phase !== 'PLAYING') return state;
        const bag = [...state.bag];
        bag.splice(action.index, 1);
        return {
          ...state,
          bag,
          moveHistory: [...state.moveHistory, `removebag:${action.index}`],
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      // ---- graph_interaction (edges) ----
      case 'SELECT_EDGE': {
        if (state.phase !== 'PLAYING') return state;
        if (state.selectedEdgeIds.includes(action.edgeId)) return state;
        return {
          ...state,
          selectedEdgeIds: [...state.selectedEdgeIds, action.edgeId],
          moveHistory: [...state.moveHistory, `seledge:${action.edgeId}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'DESELECT_EDGE': {
        if (state.phase !== 'PLAYING') return state;
        return {
          ...state,
          selectedEdgeIds: state.selectedEdgeIds.filter((id) => id !== action.edgeId),
          moveHistory: [...state.moveHistory, `deseledge:${action.edgeId}`],
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      // ---- value_assignment ----
      case 'ASSIGN': {
        if (state.phase !== 'PLAYING') return state;
        const newAssignments = { ...state.assignments, [action.slotId]: action.value };
        const nextState: GenericPuzzleState = {
          ...state,
          assignments: newAssignments,
          moveHistory: [...state.moveHistory, `assign:${action.slotId}=${action.value}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };

        if (bp.showConstraintsVisually) {
          const results = evaluateConstraints(bp.constraints, nextState, config);
          const violation = results.find(
            (r) => !r.satisfied && r.constraint.type === 'all_different',
          );
          nextState.constraintResults = results;
          if (violation) {
            nextState.feedbackMessage = violation.message;
            nextState.feedbackType = 'error';
          }
        }
        return nextState;
      }

      case 'CLEAR_ASSIGNMENT': {
        if (state.phase !== 'PLAYING') return state;
        return {
          ...state,
          assignments: { ...state.assignments, [action.slotId]: null },
          moveHistory: [...state.moveHistory, `clear:${action.slotId}`],
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      // ---- sequence_building ----
      case 'SET_SEQUENCE': {
        if (state.phase !== 'PLAYING') return state;
        return {
          ...state,
          sequence: action.sequence,
          moveHistory: [...state.moveHistory, `setseq:${action.sequence.join(',')}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'ADD_TO_SEQUENCE': {
        if (state.phase !== 'PLAYING') return state;
        if (state.sequence.includes(action.id)) return state;
        return {
          ...state,
          sequence: [...state.sequence, action.id],
          moveHistory: [...state.moveHistory, `addseq:${action.id}`],
          scoring: { ...state.scoring, moveCount: state.scoring.moveCount + 1 },
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      case 'REMOVE_FROM_SEQUENCE': {
        if (state.phase !== 'PLAYING') return state;
        return {
          ...state,
          sequence: state.sequence.filter((id) => id !== action.id),
          moveHistory: [...state.moveHistory, `rmseq:${action.id}`],
          feedbackMessage: null,
          feedbackType: null,
        };
      }

      // ---- CHECK_SOLUTION ----
      case 'CHECK_SOLUTION': {
        if (state.phase !== 'PLAYING') return state;

        const results = evaluateConstraints(bp.constraints, state, config);
        const valid = allConstraintsSatisfied(results);

        if (!valid) {
          const firstFail = results.find((r) => !r.satisfied);
          return {
            ...state,
            feedbackMessage: firstFail?.message ?? 'Invalid solution. Check the constraints and try again.',
            feedbackType: 'error',
            constraintResults: results,
          };
        }

        // All constraints pass — compute score
        const playerValue = computePlayerValue(
          bp.scoringConfig,
          state,
          config,
        );
        const optRatio =
          bp.optimalValue > 0 ? playerValue / bp.optimalValue : 0;
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
          feedbackMessage:
            optRatio >= 1
              ? 'Perfect! You found the optimal solution!'
              : `Good solution! Your answer achieves ${Math.round(optRatio * 100)}% of optimal.`,
          feedbackType: optRatio >= 1 ? 'success' : 'info',
          constraintResults: results,
          scoring: {
            ...state.scoring,
            totalScore: Math.max(baseScore - hintPenalty, 0) + bonusTotal,
            optimalityRatio: optRatio,
            bonuses,
          },
        };
      }

      default:
        return state;
    }
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useGenericConstraintPuzzleMachine(
  blueprint: GenericConstraintPuzzleBlueprint,
) {
  const reducer = useMemo(() => createReducer(blueprint), [blueprint]);
  const [state, dispatch] = useReducer(
    reducer,
    blueprint.boardConfig,
    createInitialState,
  );

  const start = useCallback(() => dispatch({ type: 'CP_START' }), []);
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
    dispatch,
    start,
    undo,
    checkSolution,
    revealAlgorithm,
    useHint,
    complete,
    reset,
  };
}
