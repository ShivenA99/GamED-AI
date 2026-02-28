// ============================================================================
// Blueprint Migration — Convert old ConstraintPuzzleBlueprint to generic
// ============================================================================

import { ConstraintPuzzleBlueprint } from '../types';
import {
  GenericConstraintPuzzleBlueprint,
  Constraint,
  PuzzleScoringConfig,
  BoardConfig,
} from './constraintPuzzleTypes';

/**
 * Detect whether a blueprint is already in the new generic format.
 */
export function isGenericBlueprint(
  bp: ConstraintPuzzleBlueprint | GenericConstraintPuzzleBlueprint,
): bp is GenericConstraintPuzzleBlueprint {
  return 'boardConfig' in bp;
}

/**
 * Convert a legacy ConstraintPuzzleBlueprint to GenericConstraintPuzzleBlueprint.
 */
export function migrateBlueprint(
  old: ConstraintPuzzleBlueprint,
): GenericConstraintPuzzleBlueprint {
  const { puzzleData } = old;

  let boardConfig: BoardConfig;
  let constraints: Constraint[];
  let scoringConfig: PuzzleScoringConfig;
  let icon: string | undefined;

  switch (puzzleData.type) {
    case 'knapsack': {
      boardConfig = {
        boardType: 'item_selection',
        items: puzzleData.items.map((it) => ({
          id: it.id,
          label: it.name,
          icon: it.icon,
          properties: { weight: it.weight, value: it.value },
        })),
        displayColumns: ['weight', 'value'],
        propertyLabels: { weight: 'Weight', value: 'Value' },
        layout: 'grid',
      };
      constraints = [
        { type: 'capacity', property: 'weight', max: puzzleData.capacity, label: 'Weight', showBar: true },
        { type: 'count_range', min: 1 },
      ];
      scoringConfig = { method: 'sum_property', property: 'value' };
      icon = '\u{1F392}';
      break;
    }

    case 'n_queens': {
      boardConfig = {
        boardType: 'grid_placement',
        rows: puzzleData.boardSize,
        cols: puzzleData.boardSize,
        pieceIcon: '\u265B',
        prePopulated: puzzleData.prePlaced?.map((p) => ({ row: p.row, col: p.col, locked: true })),
        highlightThreats: true,
      };
      constraints = [
        { type: 'count_exact', count: puzzleData.boardSize, label: 'queens' },
        { type: 'no_conflict', conflictRule: 'row_col_diagonal' },
      ];
      scoringConfig = { method: 'binary', successValue: old.optimalValue };
      icon = '\u265B';
      break;
    }

    case 'coin_change': {
      boardConfig = {
        boardType: 'multiset_building',
        pool: puzzleData.denominations.map((d) => ({
          id: `coin-${d}`,
          value: d,
          label: String(d),
        })),
        targetDisplay: 'progress_bar',
        targetLabel: 'Amount',
      };
      constraints = [
        { type: 'exact_target', target: puzzleData.targetAmount, showBar: true },
      ];
      scoringConfig = { method: 'inverse_count', numerator: puzzleData.targetAmount };
      icon = '\u{1FA99}';
      break;
    }

    case 'activity_selection': {
      boardConfig = {
        boardType: 'item_selection',
        items: puzzleData.activities.map((a) => ({
          id: a.id,
          label: a.name,
          properties: { start: a.start, end: a.end },
        })),
        displayColumns: ['start', 'end'],
        propertyLabels: { start: 'Start', end: 'End' },
        layout: 'list',
      };
      constraints = [
        { type: 'no_overlap', startProperty: 'start', endProperty: 'end' },
        { type: 'count_range', min: 1 },
      ];
      scoringConfig = { method: 'count' };
      icon = '\u{1F4C5}';
      break;
    }
  }

  return {
    title: old.title,
    narrative: old.narrative,
    rules: old.rules,
    objective: old.objective,
    boardConfig,
    constraints,
    scoringConfig,
    optimalValue: old.optimalValue,
    optimalSolutionDescription: old.optimalSolutionDescription,
    algorithmName: old.algorithmName,
    algorithmExplanation: old.algorithmExplanation,
    showConstraintsVisually: old.showConstraintsVisually,
    allowUndo: old.allowUndo,
    hints: old.hints,
    icon,
  };
}
