import { CombinedPuzzleBlueprint } from '../algorithmChallenge/combinedPuzzleTypes';

export const combinedPuzzleMST: CombinedPuzzleBlueprint = {
  title: "Kruskal's MST — Code + Puzzle",
  description:
    "Implement Kruskal's algorithm AND manually select edges to form a minimum spanning tree.",
  icon: '\u{1F310}',

  // ─── Puzzle Side ───────────────────────────────────────────────────
  puzzleBlueprint: {
    title: 'Minimum Spanning Tree',
    narrative:
      'Connect all cities with minimum total cable cost. Select edges to form a spanning tree.',
    rules: [
      'Must connect all 6 nodes.',
      'No cycles allowed.',
      'Exactly 5 edges needed (n-1 for n nodes).',
      'Goal: minimize total edge weight.',
    ],
    objective: 'Select 5 edges connecting all nodes with minimum total weight.',
    boardConfig: {
      boardType: 'graph_interaction',
      nodes: [
        { id: 'A', label: 'A', x: 50, y: 20 },
        { id: 'B', label: 'B', x: 180, y: 20 },
        { id: 'C', label: 'C', x: 310, y: 20 },
        { id: 'D', label: 'D', x: 50, y: 140 },
        { id: 'E', label: 'E', x: 180, y: 140 },
        { id: 'F', label: 'F', x: 310, y: 140 },
      ],
      edges: [
        { id: 'AB', from: 'A', to: 'B', weight: 4 },
        { id: 'AC', from: 'A', to: 'C', weight: 8 },
        { id: 'AD', from: 'A', to: 'D', weight: 2 },
        { id: 'BC', from: 'B', to: 'C', weight: 3 },
        { id: 'BE', from: 'B', to: 'E', weight: 7 },
        { id: 'CF', from: 'C', to: 'F', weight: 1 },
        { id: 'DE', from: 'D', to: 'E', weight: 5 },
        { id: 'EF', from: 'E', to: 'F', weight: 6 },
      ],
      selectionMode: 'edges',
    },
    constraints: [
      { type: 'count_exact', count: 5, label: 'Edges (need 5)' },
      { type: 'connected' },
    ],
    scoringConfig: { method: 'inverse_count', numerator: 15 },
    optimalValue: 15,
    optimalSolutionDescription:
      'CF(1) + AD(2) + BC(3) + AB(4) + DE(5) = 15. Sort by weight, add if no cycle.',
    algorithmName: "Kruskal's Algorithm (Greedy + Union-Find)",
    algorithmExplanation:
      "Sort edges by weight. Add each edge if it doesn't form a cycle (union-find check). Stop after n-1 edges. Time: O(E log E).",
    showConstraintsVisually: true,
    allowUndo: true,
    hints: [
      'Start with the cheapest edge. Which one has weight 1?',
      'After CF and AD, the next cheapest that connects new nodes is BC.',
      'Optimal MST: CF(1), AD(2), BC(3), AB(4), DE(5) = total 15.',
    ],
  },

  // ─── Code Side ─────────────────────────────────────────────────────
  algorithmChallenge: {
    mode: 'parsons',
    language: 'python',
    solutionCode: `def kruskal(nodes, edges):
    parent = {n: n for n in nodes}
    rank = {n: 0 for n in nodes}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1
        return True
    sorted_edges = sorted(edges, key=lambda e: e[2])
    mst = []
    for u, v, w in sorted_edges:
        if union(u, v):
            mst.append((u, v, w))
        if len(mst) == len(nodes) - 1:
            break
    return mst`,
    correctOrder: [
      { id: 'm1', code: 'def kruskal(nodes, edges):', indent_level: 0, is_distractor: false },
      { id: 'm2', code: 'parent = {n: n for n in nodes}', indent_level: 1, is_distractor: false },
      { id: 'm3', code: 'rank = {n: 0 for n in nodes}', indent_level: 1, is_distractor: false },
      { id: 'm4', code: 'def find(x):', indent_level: 1, is_distractor: false },
      { id: 'm5', code: 'while parent[x] != x:', indent_level: 2, is_distractor: false },
      { id: 'm6', code: 'parent[x] = parent[parent[x]]', indent_level: 3, is_distractor: false },
      { id: 'm7', code: 'x = parent[x]', indent_level: 3, is_distractor: false },
      { id: 'm8', code: 'return x', indent_level: 2, is_distractor: false },
      { id: 'm9', code: 'def union(a, b):', indent_level: 1, is_distractor: false },
      { id: 'm10', code: 'ra, rb = find(a), find(b)', indent_level: 2, is_distractor: false },
      { id: 'm11', code: 'if ra == rb:', indent_level: 2, is_distractor: false },
      { id: 'm12', code: 'return False', indent_level: 3, is_distractor: false },
      { id: 'm13', code: 'if rank[ra] < rank[rb]:', indent_level: 2, is_distractor: false },
      { id: 'm14', code: 'ra, rb = rb, ra', indent_level: 3, is_distractor: false },
      { id: 'm15', code: 'parent[rb] = ra', indent_level: 2, is_distractor: false },
      { id: 'm16', code: 'if rank[ra] == rank[rb]:', indent_level: 2, is_distractor: false },
      { id: 'm17', code: 'rank[ra] += 1', indent_level: 3, is_distractor: false },
      { id: 'm18', code: 'return True', indent_level: 2, is_distractor: false },
      { id: 'm19', code: "sorted_edges = sorted(edges, key=lambda e: e[2])", indent_level: 1, is_distractor: false },
      { id: 'm20', code: 'mst = []', indent_level: 1, is_distractor: false },
      { id: 'm21', code: 'for u, v, w in sorted_edges:', indent_level: 1, is_distractor: false },
      { id: 'm22', code: 'if union(u, v):', indent_level: 2, is_distractor: false },
      { id: 'm23', code: 'mst.append((u, v, w))', indent_level: 3, is_distractor: false },
      { id: 'm24', code: 'if len(mst) == len(nodes) - 1:', indent_level: 2, is_distractor: false },
      { id: 'm25', code: 'break', indent_level: 3, is_distractor: false },
      { id: 'm26', code: 'return mst', indent_level: 1, is_distractor: false },
    ],
    distractors: [
      { id: 'md1', code: 'if find(a) == find(b):', indent_level: 2, is_distractor: true, distractor_explanation: 'This duplicates the cycle check already inside union(). Use union() return value instead.' },
      { id: 'md2', code: 'sorted_edges = sorted(edges, key=lambda e: e[0])', indent_level: 1, is_distractor: true, distractor_explanation: 'Sorting by first element (node name) instead of weight defeats the greedy approach.' },
    ],
    parsonsConfig: {
      indentation_matters: true,
      max_attempts: null,
      show_line_numbers: true,
      allow_indent_adjustment: true,
    },
    testCases: [
      {
        id: 'tc-puzzle',
        label: 'Puzzle graph (same edges)',
        setupCode: `nodes = ['A','B','C','D','E','F']
edges = [('A','B',4),('A','C',8),('A','D',2),('B','C',3),('B','E',7),('C','F',1),('D','E',5),('E','F',6)]`,
        callCode: 'result = kruskal(nodes, edges)',
        printCode: `edge_ids = []
for u, v, w in result:
    edge_ids.append("".join(sorted([u,v])))
print(",".join(sorted(edge_ids)))`,
        expectedOutput: 'AB,AD,BC,CF,DE',
        isPuzzleCase: true,
      },
      {
        id: 'tc-triangle',
        label: 'Simple triangle',
        setupCode: `nodes = ['X','Y','Z']\nedges = [('X','Y',1),('Y','Z',2),('X','Z',3)]`,
        callCode: 'result = kruskal(nodes, edges)',
        printCode: 'print(sum(w for _,_,w in result))',
        expectedOutput: '3',
        isPuzzleCase: false,
      },
    ],
    outputFormat: 'list_of_ids',
    hints: [
      "Kruskal's sorts edges by weight and uses union-find to detect cycles.",
      'Union-find: `find` with path compression, `union` by rank.',
      'The cheapest edge (CF=1) is always in the MST. Keep adding until n-1 edges.',
    ],
  },
};
