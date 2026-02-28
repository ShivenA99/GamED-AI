// ============================================================================
// Board Registry — O(1) dispatch from boardType to component + initializer
// ============================================================================

import {
  BoardType,
  BoardConfig,
  BoardRegistryEntry,
  GenericPuzzleState,
  GridPlacementBoardConfig,
  ValueAssignmentBoardConfig,
} from './constraintPuzzleTypes';
import ItemSelectionBoard from './boards/ItemSelectionBoard';
import GridPlacementBoard from './boards/GridPlacementBoard';
import MultisetBuildingBoard from './boards/MultisetBuildingBoard';
import GraphInteractionBoard from './boards/GraphInteractionBoard';
import ValueAssignmentBoard from './boards/ValueAssignmentBoard';
import SequenceBuildingBoard from './boards/SequenceBuildingBoard';

/**
 * Normalize LLM-generated board type strings to canonical BoardType values.
 * The LLM may output creative variants like "drag_and_drop_inventory" or "knapsack_selection"
 * that need to be mapped to our 6 registered board types.
 */
export function normalizeBoardType(raw: string): BoardType {
  const t = raw.toLowerCase().replace(/[-\s]+/g, '_');

  // item_selection variants
  if (
    t.includes('item_selection') ||
    t.includes('inventory') ||
    t.includes('knapsack') ||
    t.includes('drag_and_drop') ||
    t.includes('pick') ||
    t.includes('select_items') ||
    t.includes('checkbox')
  ) {
    return 'item_selection';
  }

  // grid_placement variants
  if (
    t.includes('grid') ||
    t.includes('board') ||
    t.includes('chess') ||
    t.includes('queens') ||
    t.includes('placement') ||
    t.includes('matrix')
  ) {
    return 'grid_placement';
  }

  // sequence_building variants
  if (
    t.includes('sequence') ||
    t.includes('ordering') ||
    t.includes('schedule') ||
    t.includes('timeline') ||
    t.includes('topological')
  ) {
    return 'sequence_building';
  }

  // graph_interaction variants
  if (
    t.includes('graph') ||
    t.includes('network') ||
    t.includes('path') ||
    t.includes('tree') ||
    t.includes('edge') ||
    t.includes('node')
  ) {
    return 'graph_interaction';
  }

  // value_assignment variants
  if (
    t.includes('assignment') ||
    t.includes('coloring') ||
    t.includes('labeling') ||
    t.includes('assign')
  ) {
    return 'value_assignment';
  }

  // multiset_building variants
  if (
    t.includes('multiset') ||
    t.includes('bag') ||
    t.includes('collection') ||
    t.includes('coin') ||
    t.includes('denomination')
  ) {
    return 'multiset_building';
  }

  // Default fallback: item_selection (most generic)
  return 'item_selection';
}

export const BOARD_REGISTRY: Record<BoardType, BoardRegistryEntry> = {
  item_selection: {
    component: ItemSelectionBoard,
    getInitialBoardState: () => ({
      selectedIds: [],
    }),
  },
  grid_placement: {
    component: GridPlacementBoard,
    getInitialBoardState: (config: BoardConfig) => {
      const cfg = config as GridPlacementBoardConfig;
      const prePlaced = cfg.prePopulated?.map((p) => ({ row: p.row, col: p.col })) ?? [];
      return { placements: prePlaced };
    },
  },
  multiset_building: {
    component: MultisetBuildingBoard,
    getInitialBoardState: () => ({
      bag: [],
    }),
  },
  graph_interaction: {
    component: GraphInteractionBoard,
    getInitialBoardState: () => ({
      selectedIds: [],
      selectedEdgeIds: [],
    }),
  },
  value_assignment: {
    component: ValueAssignmentBoard,
    getInitialBoardState: (config: BoardConfig) => {
      const cfg = config as ValueAssignmentBoardConfig;
      const assignments: Record<string, string | number | null> = {};
      for (const slot of cfg.slots) {
        assignments[slot.id] = null;
      }
      return { assignments };
    },
  },
  sequence_building: {
    component: SequenceBuildingBoard,
    getInitialBoardState: () => ({
      sequence: [],
    }),
  },
};

/**
 * Get the initial board-specific state for a given board config.
 * Normalizes the boardType first to handle LLM-generated variants.
 */
export function getInitialBoardState(
  config: BoardConfig,
): Partial<GenericPuzzleState> {
  const canonicalType = normalizeBoardType(config.boardType);
  const entry = BOARD_REGISTRY[canonicalType];
  if (!entry) {
    // Ultimate fallback — should never happen after normalization
    return { selectedIds: [] };
  }
  return entry.getInitialBoardState(config);
}
