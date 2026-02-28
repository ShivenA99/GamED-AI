import { CombinedPuzzleBlueprint } from '../algorithmChallenge/combinedPuzzleTypes';
import { combinedPuzzleKnapsack } from './combinedPuzzleKnapsack';
import { combinedPuzzleMST } from './combinedPuzzleMST';
import { combinedPuzzleActivitySelection } from './combinedPuzzleActivitySelection';
import { combinedPuzzleGraphColoring } from './combinedPuzzleGraphColoring';

export {
  combinedPuzzleKnapsack,
  combinedPuzzleMST,
  combinedPuzzleActivitySelection,
  combinedPuzzleGraphColoring,
};

export interface CombinedPuzzleDemoEntry {
  id: string;
  demo: CombinedPuzzleBlueprint;
}

export const allCombinedPuzzleDemos: CombinedPuzzleDemoEntry[] = [
  { id: 'cp-code-knapsack', demo: combinedPuzzleKnapsack },
  { id: 'cp-code-mst', demo: combinedPuzzleMST },
  { id: 'cp-code-activity', demo: combinedPuzzleActivitySelection },
  { id: 'cp-code-coloring', demo: combinedPuzzleGraphColoring },
];
