import { ConstraintPuzzleBlueprint } from '../types';
import { GenericConstraintPuzzleBlueprint } from '../constraintPuzzle/constraintPuzzleTypes';
import { constraintPuzzleKnapsack } from './constraintPuzzleKnapsack';
import { constraintPuzzleNQueens } from './constraintPuzzleNQueens';
import { constraintPuzzleCoinChange } from './constraintPuzzleCoinChange';
import { constraintPuzzleActivitySelection } from './constraintPuzzleActivitySelection';
import { constraintPuzzleGraphColoring } from './constraintPuzzleGraphColoring';
import { constraintPuzzleMST } from './constraintPuzzleMST';
import { constraintPuzzleTopologicalSort } from './constraintPuzzleTopologicalSort';

export {
  constraintPuzzleKnapsack,
  constraintPuzzleNQueens,
  constraintPuzzleCoinChange,
  constraintPuzzleActivitySelection,
  constraintPuzzleGraphColoring,
  constraintPuzzleMST,
  constraintPuzzleTopologicalSort,
};

export interface ConstraintPuzzleDemoEntry {
  id: string;
  demo: ConstraintPuzzleBlueprint | GenericConstraintPuzzleBlueprint;
}

export const allConstraintPuzzleDemos: ConstraintPuzzleDemoEntry[] = [
  // Legacy format (auto-migrated at runtime)
  { id: 'cp-knapsack', demo: constraintPuzzleKnapsack },
  { id: 'cp-n-queens', demo: constraintPuzzleNQueens },
  { id: 'cp-coin-change', demo: constraintPuzzleCoinChange },
  { id: 'cp-activity-selection', demo: constraintPuzzleActivitySelection },
  // Generic format (new board types)
  { id: 'cp-graph-coloring', demo: constraintPuzzleGraphColoring },
  { id: 'cp-mst', demo: constraintPuzzleMST },
  { id: 'cp-topological-sort', demo: constraintPuzzleTopologicalSort },
];
