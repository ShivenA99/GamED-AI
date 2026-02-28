import { GenericConstraintPuzzleBlueprint } from '../constraintPuzzle/constraintPuzzleTypes';

export const constraintPuzzleMST: GenericConstraintPuzzleBlueprint = {
  title: 'Network Cable Challenge',
  narrative:
    'A town needs internet! Connect all 6 buildings with the minimum total cable length. Select edges to build your network — but every building must be reachable!',
  rules: [
    'Select edges (cables) to connect all buildings',
    'All buildings must be reachable from any other',
    'Minimize the total cable length (edge weights)',
    'Click an edge to toggle it on/off',
  ],
  objective: 'Connect all 6 buildings using the least total cable length',
  boardConfig: {
    boardType: 'graph_interaction',
    nodes: [
      { id: 'A', label: 'A', x: 60, y: 40 },
      { id: 'B', label: 'B', x: 200, y: 40 },
      { id: 'C', label: 'C', x: 340, y: 40 },
      { id: 'D', label: 'D', x: 60, y: 180 },
      { id: 'E', label: 'E', x: 200, y: 180 },
      { id: 'F', label: 'F', x: 340, y: 180 },
    ],
    edges: [
      { id: 'AB', from: 'A', to: 'B', weight: 4 },
      { id: 'AC', from: 'A', to: 'C', weight: 8 },
      { id: 'AD', from: 'A', to: 'D', weight: 2 },
      { id: 'BC', from: 'B', to: 'C', weight: 3 },
      { id: 'BE', from: 'B', to: 'E', weight: 5 },
      { id: 'CD', from: 'C', to: 'D', weight: 9 },
      { id: 'CF', from: 'C', to: 'F', weight: 1 },
      { id: 'DE', from: 'D', to: 'E', weight: 6 },
      { id: 'EF', from: 'E', to: 'F', weight: 7 },
    ],
    selectionMode: 'edges',
  },
  constraints: [
    { type: 'connected' },
  ],
  scoringConfig: { method: 'binary', successValue: 5 },
  // MST: AD(2) + AB(4) + BC(3) + CF(1) + BE(5) = 15? Let me compute:
  // Kruskal: sort edges by weight: CF(1), AD(2), BC(3), AB(4), BE(5), DE(6), EF(7), AC(8), CD(9)
  // Pick CF(1): {C,F}
  // Pick AD(2): {A,D}, {C,F}
  // Pick BC(3): {B,C,F}, {A,D}
  // Pick AB(4): {A,B,C,D,F}
  // Pick BE(5): would connect E. But B-E connects {A,B,C,D,E,F}. Done!
  // Wait, AB merges {A,D} and {B,C,F} → {A,B,C,D,F}. Then BE(5) adds E. Total = 1+2+3+4+5 = 15
  // 5 edges for 6 nodes = correct MST
  optimalValue: 5,
  optimalSolutionDescription:
    'Minimum Spanning Tree: CF(1) + AD(2) + BC(3) + AB(4) + BE(5) = total weight 15. Kruskal\'s algorithm sorts edges by weight and greedily adds them if they don\'t form a cycle.',
  algorithmName: 'Minimum Spanning Tree (Kruskal\'s Algorithm)',
  algorithmExplanation:
    'A Minimum Spanning Tree (MST) connects all vertices with the minimum total edge weight. Kruskal\'s algorithm: (1) Sort all edges by weight. (2) For each edge in order, add it if it doesn\'t create a cycle (use Union-Find). (3) Stop when you have V-1 edges. Prim\'s algorithm grows the tree from a starting vertex, always adding the cheapest edge that connects a new vertex. Both run in O(E log E) time.',
  showConstraintsVisually: true,
  allowUndo: true,
  hints: [
    'Start with the cheapest edges. The lightest edge (weight 1) is always in the MST.',
    'After CF(1) and AD(2), look for edges that connect new buildings without forming loops.',
    'Optimal: CF(1) + AD(2) + BC(3) + AB(4) + BE(5) = 15 total cable length.',
  ],
  icon: '\u{1F310}',
};
