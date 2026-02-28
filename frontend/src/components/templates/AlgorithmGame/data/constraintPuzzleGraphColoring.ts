import { GenericConstraintPuzzleBlueprint } from '../constraintPuzzle/constraintPuzzleTypes';

export const constraintPuzzleGraphColoring: GenericConstraintPuzzleBlueprint = {
  title: 'Map Coloring Challenge',
  narrative:
    'Color each region of a map so that no two neighboring regions share the same color. This classic problem appears in scheduling, register allocation, and frequency assignment!',
  rules: [
    'Every region must be assigned a color',
    'No two neighboring regions can share the same color',
    'Use as few colors as possible (3 colors suffice here)',
    'Click a region, then pick a color from the palette',
  ],
  objective: 'Color all 6 regions with no neighbor conflicts using only 3 colors',
  boardConfig: {
    boardType: 'value_assignment',
    slots: [
      { id: 'A', label: 'Region A', neighbors: ['B', 'C', 'D'] },
      { id: 'B', label: 'Region B', neighbors: ['A', 'C', 'E'] },
      { id: 'C', label: 'Region C', neighbors: ['A', 'B', 'D', 'E', 'F'] },
      { id: 'D', label: 'Region D', neighbors: ['A', 'C', 'F'] },
      { id: 'E', label: 'Region E', neighbors: ['B', 'C', 'F'] },
      { id: 'F', label: 'Region F', neighbors: ['C', 'D', 'E'] },
    ],
    domain: ['Red', 'Green', 'Blue'],
    domainColors: {
      Red: '#ef4444',
      Green: '#22c55e',
      Blue: '#3b82f6',
    },
    layout: 'grid',
  },
  constraints: [
    { type: 'all_assigned' },
    { type: 'all_different', scope: 'neighbors' },
  ],
  scoringConfig: { method: 'binary', successValue: 6 },
  optimalValue: 6,
  optimalSolutionDescription:
    'One valid 3-coloring: A=Red, B=Green, C=Blue, D=Green, E=Red, F=Green. The greedy coloring heuristic processes nodes by degree (most constrained first) and assigns the smallest available color.',
  algorithmName: 'Graph Coloring (Greedy / Backtracking)',
  algorithmExplanation:
    'Graph coloring assigns labels (colors) to graph vertices such that no two adjacent vertices share the same color. The greedy algorithm processes vertices in order, assigning each the smallest color not used by its neighbors. While not always optimal, ordering by degree (most constrained first) often finds a minimal coloring. For exact solutions, backtracking explores all assignments, pruning branches where a conflict is detected. The chromatic number (minimum colors needed) is NP-hard to compute in general.',
  showConstraintsVisually: true,
  allowUndo: true,
  hints: [
    'Start with the most connected region (C has 5 neighbors) — it is hardest to color later.',
    'Region C connects to all others. Color C first, then color its neighbors with the remaining 2 colors.',
    'Solution: A=Red, B=Green, C=Blue, D=Green, E=Red, F=Green.',
  ],
  icon: '\u{1F3A8}',
};
