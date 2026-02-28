import { CombinedPuzzleBlueprint } from '../algorithmChallenge/combinedPuzzleTypes';

export const combinedPuzzleGraphColoring: CombinedPuzzleBlueprint = {
  title: 'Graph Coloring — Code + Puzzle',
  description:
    'Write a backtracking algorithm AND manually color the graph so no adjacent nodes share a color.',
  icon: '\u{1F3A8}',

  // ─── Puzzle Side ───────────────────────────────────────────────────
  puzzleBlueprint: {
    title: 'Graph Coloring',
    narrative:
      'Color each node so that no two connected nodes share the same color. Use as few colors as possible.',
    rules: [
      'Adjacent nodes must have different colors.',
      'All nodes must be assigned a color.',
      'Try to use the minimum number of colors.',
    ],
    objective: 'Assign colors to all nodes with no adjacent conflicts using 3 colors.',
    boardConfig: {
      boardType: 'value_assignment',
      slots: [
        { id: 'A', label: 'A', neighbors: ['B', 'D'] },
        { id: 'B', label: 'B', neighbors: ['A', 'C', 'E'] },
        { id: 'C', label: 'C', neighbors: ['B', 'F'] },
        { id: 'D', label: 'D', neighbors: ['A', 'E'] },
        { id: 'E', label: 'E', neighbors: ['B', 'D', 'F'] },
        { id: 'F', label: 'F', neighbors: ['C', 'E'] },
      ],
      domain: ['Red', 'Green', 'Blue'],
      domainColors: {
        Red: '#ef4444',
        Green: '#22c55e',
        Blue: '#3b82f6',
      },
      layout: 'graph',
    },
    constraints: [
      { type: 'all_different', scope: 'neighbors' },
      { type: 'all_assigned' },
    ],
    scoringConfig: { method: 'binary', successValue: 1 },
    optimalValue: 1,
    optimalSolutionDescription:
      'A valid 3-coloring exists. One solution: A=Red, B=Green, C=Red, D=Green, E=Blue, F=Green.',
    algorithmName: 'Graph Coloring (Backtracking)',
    algorithmExplanation:
      'Try assigning colors one node at a time. If a conflict arises, backtrack and try the next color. The chromatic number of this graph is 3.',
    showConstraintsVisually: true,
    allowUndo: true,
    hints: [
      'Node E has 3 neighbors — it constrains the most. Color it first mentally.',
      'If A=Red and D=Green, then E must be Blue (neighbors with both A and D via indirect paths).',
      'One valid coloring: A=Red, B=Green, C=Red, D=Green, E=Blue, F=Green.',
    ],
  },

  // ─── Code Side ─────────────────────────────────────────────────────
  algorithmChallenge: {
    mode: 'free_code',
    language: 'python',
    starterCode: `def graph_coloring(adj, colors):
    """
    adj: dict mapping node -> list of neighbor nodes
    colors: list of available colors (strings)
    Returns: dict mapping node -> color, or None if impossible
    """
    assignment = {}
    nodes = sorted(adj.keys())

    def is_safe(node, color):
        # TODO: Check if any neighbor has this color
        pass

    def backtrack(idx):
        # TODO: Base case + recursive case
        pass

    if backtrack(0):
        return assignment
    return None
`,
    solutionCode: `def graph_coloring(adj, colors):
    assignment = {}
    nodes = sorted(adj.keys())

    def is_safe(node, color):
        for neighbor in adj[node]:
            if assignment.get(neighbor) == color:
                return False
        return True

    def backtrack(idx):
        if idx == len(nodes):
            return True
        node = nodes[idx]
        for color in colors:
            if is_safe(node, color):
                assignment[node] = color
                if backtrack(idx + 1):
                    return True
                del assignment[node]
        return False

    if backtrack(0):
        return assignment
    return None
`,
    testCases: [
      {
        id: 'tc-puzzle',
        label: 'Puzzle graph',
        setupCode: `adj = {
    'A': ['B', 'D'],
    'B': ['A', 'C', 'E'],
    'C': ['B', 'F'],
    'D': ['A', 'E'],
    'E': ['B', 'D', 'F'],
    'F': ['C', 'E'],
}
colors = ['Red', 'Green', 'Blue']`,
        callCode: 'result = graph_coloring(adj, colors)',
        printCode: `if result:
    print(",".join(f"{k}={v}" for k,v in sorted(result.items())))
else:
    print("None")`,
        expectedOutput: 'A=Red,B=Green,C=Red,D=Green,E=Blue,F=Red',
        isPuzzleCase: true,
      },
      {
        id: 'tc-triangle',
        label: 'Triangle (3 colors needed)',
        setupCode: `adj = {'X': ['Y','Z'], 'Y': ['X','Z'], 'Z': ['X','Y']}
colors = ['R','G','B']`,
        callCode: 'result = graph_coloring(adj, colors)',
        printCode: `if result:
    vals = sorted(set(result.values()))
    print(len(vals))
else:
    print("None")`,
        expectedOutput: '3',
        isPuzzleCase: false,
      },
      {
        id: 'tc-impossible',
        label: 'Triangle with 2 colors (impossible)',
        setupCode: `adj = {'X': ['Y','Z'], 'Y': ['X','Z'], 'Z': ['X','Y']}
colors = ['R','G']`,
        callCode: 'result = graph_coloring(adj, colors)',
        printCode: 'print(result)',
        expectedOutput: 'None',
        isPuzzleCase: false,
      },
    ],
    outputFormat: 'list_of_ids',
    hints: [
      'is_safe checks if any neighbor already has the proposed color.',
      'Backtracking: try each color for the current node, recurse, undo if stuck.',
      'Base case: if idx == len(nodes), all nodes are colored — return True.',
    ],
  },
};
