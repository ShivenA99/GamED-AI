/**
 * usePhetSimulationState Hook
 *
 * Manages game state, scoring, and checkpoint tracking for PhET simulation games.
 */

import { useCallback, useEffect, useMemo, useReducer, useState } from 'react';
import {
  PhetSimulationBlueprint,
  GameState,
  AssessmentTask,
  Checkpoint,
  CheckpointCondition,
  PhetInteraction
} from '../types';

// =============================================================================
// STATE REDUCER
// =============================================================================

type GameAction =
  | { type: 'COMPLETE_CHECKPOINT'; checkpointId: string; points: number }
  | { type: 'COMPLETE_TASK'; taskId: string }
  | { type: 'USE_HINT' }
  | { type: 'NEXT_TASK' }
  | { type: 'ADD_INTERACTION'; interaction: PhetInteraction }
  | { type: 'UPDATE_SIMULATION_STATE'; state: Record<string, any> }
  | { type: 'TRACK_PROPERTY_CHANGE'; property: string; value: any }
  | { type: 'SET_COMPLETE' }
  | { type: 'RESET' };

function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'COMPLETE_CHECKPOINT': {
      const newCompletedCheckpoints = new Set(state.completedCheckpoints);
      newCompletedCheckpoints.add(action.checkpointId);
      return {
        ...state,
        completedCheckpoints: newCompletedCheckpoints,
        score: state.score + action.points,
        lastActivityTime: Date.now()
      };
    }

    case 'COMPLETE_TASK': {
      const newCompletedTasks = new Set(state.completedTasks);
      newCompletedTasks.add(action.taskId);
      return {
        ...state,
        completedTasks: newCompletedTasks,
        lastActivityTime: Date.now()
      };
    }

    case 'USE_HINT':
      return {
        ...state,
        hintsUsed: state.hintsUsed + 1
      };

    case 'NEXT_TASK':
      return {
        ...state,
        currentTaskIndex: state.currentTaskIndex + 1,
        lastActivityTime: Date.now()
      };

    case 'ADD_INTERACTION':
      return {
        ...state,
        interactions: [...state.interactions, action.interaction],
        lastActivityTime: Date.now()
      };

    case 'UPDATE_SIMULATION_STATE':
      return {
        ...state,
        simulationState: { ...state.simulationState, ...action.state }
      };

    case 'TRACK_PROPERTY_CHANGE': {
      const newChangedProperties = new Set(state.changedProperties);
      newChangedProperties.add(action.property);

      const newExploredValues = new Map(state.exploredValues);
      const existingValues = newExploredValues.get(action.property) || new Set();
      existingValues.add(action.value);
      newExploredValues.set(action.property, existingValues);

      return {
        ...state,
        changedProperties: newChangedProperties,
        exploredValues: newExploredValues,
        lastActivityTime: Date.now()
      };
    }

    case 'SET_COMPLETE':
      return {
        ...state,
        isComplete: true
      };

    case 'RESET':
      return createInitialState();

    default:
      return state;
  }
}

function createInitialState(): GameState {
  return {
    startTime: Date.now(),
    currentTaskIndex: 0,
    completedCheckpoints: new Set(),
    completedTasks: new Set(),
    score: 0,
    hintsUsed: 0,
    changedProperties: new Set(),
    exploredValues: new Map(),
    interactions: [],
    simulationState: {},
    isComplete: false,
    lastActivityTime: Date.now()
  };
}

// =============================================================================
// MAIN HOOK
// =============================================================================

export function usePhetSimulationState(blueprint: PhetSimulationBlueprint) {
  const [gameState, dispatch] = useReducer(gameReducer, createInitialState());
  const [revealedHintIndex, setRevealedHintIndex] = useState(-1);

  // Current task
  const currentTask = useMemo(() => {
    return blueprint.tasks[gameState.currentTaskIndex] || null;
  }, [blueprint.tasks, gameState.currentTaskIndex]);

  // Max score calculation
  const maxScore = useMemo(() => {
    return blueprint.tasks.reduce((total, task) => {
      return total + task.checkpoints.reduce((taskTotal, cp) => taskTotal + cp.points, 0);
    }, 0);
  }, [blueprint.tasks]);

  // Check if current task is complete
  const isTaskComplete = useCallback((task: AssessmentTask): boolean => {
    return task.checkpoints.every(cp =>
      gameState.completedCheckpoints.has(cp.id)
    );
  }, [gameState.completedCheckpoints]);

  // Check if game is complete
  const isComplete = useMemo(() => {
    if (gameState.isComplete) return true;

    // All required tasks must be complete
    return blueprint.tasks
      .filter(t => t.requiredToProceed)
      .every(t => isTaskComplete(t));
  }, [blueprint.tasks, isTaskComplete, gameState.isComplete]);

  // Complete a checkpoint
  const completeCheckpoint = useCallback((checkpointId: string, points: number) => {
    if (gameState.completedCheckpoints.has(checkpointId)) return;

    // Apply hint penalty
    let adjustedPoints = points;
    if (gameState.hintsUsed > 0 && blueprint.scoring.hintPenalty) {
      adjustedPoints = Math.max(1, points - (gameState.hintsUsed * blueprint.scoring.hintPenalty));
    }

    dispatch({ type: 'COMPLETE_CHECKPOINT', checkpointId, points: adjustedPoints });

    // Check if task is now complete
    if (currentTask) {
      const taskCheckpoints = currentTask.checkpoints;
      const allComplete = taskCheckpoints.every(
        cp => cp.id === checkpointId || gameState.completedCheckpoints.has(cp.id)
      );

      if (allComplete) {
        dispatch({ type: 'COMPLETE_TASK', taskId: currentTask.id });
      }
    }
  }, [gameState.completedCheckpoints, gameState.hintsUsed, blueprint.scoring.hintPenalty, currentTask]);

  // Use a hint
  const useHint = useCallback(() => {
    if (!currentTask?.hints) return;

    const nextHintIndex = revealedHintIndex + 1;
    if (nextHintIndex < currentTask.hints.length) {
      setRevealedHintIndex(nextHintIndex);
      dispatch({ type: 'USE_HINT' });
    }
  }, [currentTask?.hints, revealedHintIndex]);

  // Move to next task
  const nextTask = useCallback(() => {
    if (gameState.currentTaskIndex < blueprint.tasks.length - 1) {
      dispatch({ type: 'NEXT_TASK' });
      setRevealedHintIndex(-1);
    } else {
      dispatch({ type: 'SET_COMPLETE' });
    }
  }, [gameState.currentTaskIndex, blueprint.tasks.length]);

  // Track simulation state change
  const trackStateChange = useCallback((property: string, value: any) => {
    dispatch({ type: 'TRACK_PROPERTY_CHANGE', property, value });
  }, []);

  // Track interaction
  const trackInteraction = useCallback((interaction: PhetInteraction) => {
    dispatch({ type: 'ADD_INTERACTION', interaction });
  }, []);

  // Update simulation state
  const updateSimulationState = useCallback((state: Record<string, any>) => {
    dispatch({ type: 'UPDATE_SIMULATION_STATE', state });
  }, []);

  // Reset game
  const resetGame = useCallback(() => {
    dispatch({ type: 'RESET' });
    setRevealedHintIndex(-1);
  }, []);

  // Get revealed hints
  const revealedHints = useMemo(() => {
    if (!currentTask?.hints) return [];
    return currentTask.hints.slice(0, revealedHintIndex + 1);
  }, [currentTask?.hints, revealedHintIndex]);

  return {
    gameState,
    currentTaskIndex: gameState.currentTaskIndex,
    currentTask,
    completedCheckpoints: gameState.completedCheckpoints,
    completedTasks: gameState.completedTasks,
    score: gameState.score,
    maxScore,
    hintsUsed: gameState.hintsUsed,
    isComplete,
    completeCheckpoint,
    useHint,
    nextTask,
    trackStateChange,
    trackInteraction,
    updateSimulationState,
    resetGame,
    revealedHints,
    isTaskComplete
  };
}

// =============================================================================
// CHECKPOINT EVALUATION
// =============================================================================

export function evaluateCheckpoint(
  checkpoint: Checkpoint,
  simulationState: Record<string, any>,
  interactions: PhetInteraction[],
  gameState: GameState
): boolean {
  const results = checkpoint.conditions.map(condition =>
    evaluateCondition(condition, simulationState, interactions, gameState)
  );

  if (checkpoint.conditionLogic === 'any') {
    return results.some(r => r);
  }
  return results.every(r => r);
}

export function evaluateCondition(
  condition: CheckpointCondition,
  state: Record<string, any>,
  interactions: PhetInteraction[],
  gameState: GameState
): boolean {
  const condType = condition.type.toLowerCase();

  switch (condType) {
    case 'property_equals': {
      const value = state[condition.propertyId!];
      if (value === undefined) return false;

      const tolerance = condition.tolerance || 0;
      if (typeof value === 'number' && typeof condition.value === 'number') {
        return Math.abs(value - condition.value) <= tolerance;
      }
      return value === condition.value;
    }

    case 'property_range': {
      const value = state[condition.propertyId!];
      if (typeof value !== 'number') return false;
      return value >= (condition.minValue ?? -Infinity) &&
             value <= (condition.maxValue ?? Infinity);
    }

    case 'property_changed': {
      return gameState.changedProperties.has(condition.propertyId!);
    }

    case 'interaction_occurred': {
      return interactions.some(i => i.id === condition.interactionId);
    }

    case 'outcome_achieved': {
      const value = state[condition.outcomeId!];
      if (value === undefined) return false;

      const target = condition.value;
      switch (condition.operator) {
        case 'eq': return value === target;
        case 'neq': return value !== target;
        case 'gt': return value > target;
        case 'gte': return value >= target;
        case 'lt': return value < target;
        case 'lte': return value <= target;
        default: return false;
      }
    }

    case 'time_spent': {
      const elapsed = (Date.now() - gameState.startTime) / 1000;
      return elapsed >= (condition.minSeconds ?? 0);
    }

    case 'exploration_breadth': {
      if (!condition.parameterIds || condition.parameterIds.length === 0) return false;

      for (const paramId of condition.parameterIds) {
        const uniqueValues = gameState.exploredValues.get(paramId);
        if (!uniqueValues || uniqueValues.size < (condition.minUniqueValues ?? 1)) {
          return false;
        }
      }
      return true;
    }

    case 'sequence_completed': {
      if (!condition.sequenceSteps || condition.sequenceSteps.length === 0) return true;

      // Check if interactions match the sequence
      let sequenceIndex = 0;
      for (const interaction of interactions) {
        if (interaction.id === condition.sequenceSteps[sequenceIndex]) {
          sequenceIndex++;
          if (sequenceIndex >= condition.sequenceSteps.length) {
            return true;
          }
        }
      }
      return false;
    }

    default:
      console.warn(`[PhetSimulationState] Unknown condition type: ${condType}`);
      return false;
  }
}
