// ============================================================================
// Scoring Evaluator — Compute playerValue from state + scoringConfig
// ============================================================================

import {
  PuzzleScoringConfig,
  GenericPuzzleState,
  BoardConfig,
  ItemSelectionBoardConfig,
} from './constraintPuzzleTypes';

/**
 * Compute the player's raw value for the current puzzle state.
 * This is compared against optimalValue to get the optimality ratio.
 */
export function computePlayerValue(
  config: PuzzleScoringConfig,
  state: GenericPuzzleState,
  boardConfig: BoardConfig,
): number {
  switch (config.method) {
    case 'sum_property':
      return evalSumProperty(config, state, boardConfig);
    case 'count':
      return evalCount(state, boardConfig);
    case 'inverse_count':
      return evalInverseCount(config, state, boardConfig);
    case 'binary':
      return config.successValue; // caller checks if constraints pass first
    case 'ratio':
      return evalRatio(config, state, boardConfig);
    case 'weighted_sum':
      return evalWeightedSum(config, state, boardConfig);
  }
}

function evalSumProperty(
  config: Extract<PuzzleScoringConfig, { method: 'sum_property' }>,
  state: GenericPuzzleState,
  boardConfig: BoardConfig,
): number {
  if (boardConfig.boardType === 'item_selection') {
    const items = (boardConfig as ItemSelectionBoardConfig).items;
    return items
      .filter((it) => state.selectedIds.includes(it.id))
      .reduce((sum, it) => sum + (Number(it.properties[config.property]) || 0), 0);
  }
  return 0;
}

function evalCount(
  state: GenericPuzzleState,
  boardConfig: BoardConfig,
): number {
  switch (boardConfig.boardType) {
    case 'item_selection':
      return state.selectedIds.length;
    case 'grid_placement':
      return state.placements.length;
    case 'multiset_building':
      return state.bag.length;
    case 'graph_interaction':
      return state.selectedEdgeIds.length + state.selectedIds.length;
    case 'value_assignment':
      return Object.values(state.assignments).filter((v) => v != null).length;
    case 'sequence_building':
      return state.sequence.length;
  }
}

function evalInverseCount(
  config: Extract<PuzzleScoringConfig, { method: 'inverse_count' }>,
  state: GenericPuzzleState,
  boardConfig: BoardConfig,
): number {
  const count = evalCount(state, boardConfig);
  return count > 0 ? config.numerator / count : 0;
}

function evalRatio(
  config: Extract<PuzzleScoringConfig, { method: 'ratio' }>,
  state: GenericPuzzleState,
  boardConfig: BoardConfig,
): number {
  const count = evalCount(state, boardConfig);
  return config.total > 0 ? count / config.total : 0;
}

function evalWeightedSum(
  config: Extract<PuzzleScoringConfig, { method: 'weighted_sum' }>,
  state: GenericPuzzleState,
  boardConfig: BoardConfig,
): number {
  if (boardConfig.boardType === 'item_selection') {
    const items = (boardConfig as ItemSelectionBoardConfig).items;
    return items
      .filter((it) => state.selectedIds.includes(it.id))
      .reduce(
        (sum, it) =>
          sum +
          (Number(it.properties[config.valueProperty]) || 0) *
            (Number(it.properties[config.weightProperty]) || 0),
        0,
      );
  }
  return 0;
}
