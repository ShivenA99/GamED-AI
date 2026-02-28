import { StateTracerBlueprint, ExecutionStep } from '../types';

const CODE = `def bfs(graph, start):
    visited = set()
    queue = [start]
    order = []
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                queue.append(neighbor)
    return order

# Example: bfs(graph, 'A')`;

// ============================================================================
// Graph layout (6 nodes):
//         A (200,30)
//        / \
//   B (120,110)  C (280,110)
//   / \            \
// D    E            F
// (60,190) (180,190) (340,190)
//
// Edges (directed): A->B, A->C, B->D, B->E, C->F
// BFS traversal order from A: A, B, C, D, E, F
// ============================================================================

// Helper to build a graph snapshot at each step
function makeNodes(
  states: Record<string, 'unvisited' | 'in_frontier' | 'current' | 'visited'>
) {
  const positions: Record<string, { x: number; y: number }> = {
    A: { x: 200, y: 30 },
    B: { x: 120, y: 110 },
    C: { x: 280, y: 110 },
    D: { x: 60, y: 190 },
    E: { x: 180, y: 190 },
    F: { x: 340, y: 190 },
  };
  return Object.entries(positions).map(([id, pos]) => ({
    id,
    label: id,
    x: pos.x,
    y: pos.y,
    state: states[id] ?? ('unvisited' as const),
  }));
}

type EdgeState = 'default' | 'exploring' | 'visited';

function makeEdges(
  edgeStates: Record<string, EdgeState>
) {
  const allEdges = [
    { from: 'A', to: 'B' },
    { from: 'A', to: 'C' },
    { from: 'B', to: 'D' },
    { from: 'B', to: 'E' },
    { from: 'C', to: 'F' },
  ];
  return allEdges.map((e) => ({
    ...e,
    directed: true,
    state: edgeStates[`${e.from}-${e.to}`] ?? ('default' as const),
  }));
}

// ============================================================================
// Execution steps
// ============================================================================

const steps: ExecutionStep[] = [
  // --- Step 0: Initialization ---
  {
    stepNumber: 0,
    codeLine: 1,
    description: 'Initialize BFS: visited = {}, queue = [A], order = []',
    variables: { visited: '', queue: 'A', order: '', node: '' },
    changedVariables: ['visited', 'queue', 'order'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'in_frontier',
        B: 'unvisited',
        C: 'unvisited',
        D: 'unvisited',
        E: 'unvisited',
        F: 'unvisited',
      }),
      edges: makeEdges({}),
      auxiliary: { label: 'Queue', items: ['A'] },
    },
    prediction: null,
    explanation:
      'We start BFS by placing the start node A into the queue. The visited set and order list are empty.',
    hints: ['', '', ''],
  },

  // --- Step 1: Dequeue A, mark current ---
  {
    stepNumber: 1,
    codeLine: 6,
    description: 'Dequeue the front of the queue. Which node is dequeued?',
    variables: { visited: '', queue: 'A', order: '', node: '' },
    changedVariables: ['node'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'current',
        B: 'unvisited',
        C: 'unvisited',
        D: 'unvisited',
        E: 'unvisited',
        F: 'unvisited',
      }),
      edges: makeEdges({}),
      auxiliary: { label: 'Queue', items: [] },
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Which node is dequeued first from the queue?',
      options: [
        { id: 'A', label: 'A' },
        { id: 'B', label: 'B' },
        { id: 'C', label: 'C' },
        { id: 'D', label: 'D' },
      ],
      correctId: 'A',
    },
    explanation:
      'A is the only node in the queue, so it is dequeued first. It becomes the current node.',
    hints: [
      'BFS uses a queue: first-in, first-out.',
      'The queue contains only A right now.',
      'A is dequeued first.',
    ],
  },

  // --- Step 2: Process A - add neighbors B, C ---
  {
    stepNumber: 2,
    codeLine: 11,
    description: 'Visit A, then add its unvisited neighbors to the queue.',
    variables: { visited: 'A', queue: '', order: 'A', node: 'A' },
    changedVariables: ['visited', 'queue', 'order'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'current',
        B: 'unvisited',
        C: 'unvisited',
        D: 'unvisited',
        E: 'unvisited',
        F: 'unvisited',
      }),
      edges: makeEdges({
        'A-B': 'exploring',
        'A-C': 'exploring',
      }),
      auxiliary: { label: 'Queue', items: [] },
    },
    prediction: {
      type: 'multi_select',
      prompt: 'Which neighbors of A are added to the queue?',
      options: [
        { id: 'B', label: 'B' },
        { id: 'C', label: 'C' },
        { id: 'D', label: 'D' },
        { id: 'E', label: 'E' },
        { id: 'F', label: 'F' },
      ],
      correctIds: ['B', 'C'],
    },
    explanation:
      'A has two neighbors: B and C. Neither has been visited, so both are added to the queue.',
    hints: [
      'Look at the edges leaving node A.',
      'A connects to B and C.',
      'Both B and C are added to the queue.',
    ],
  },

  // --- Step 3: A visited, queue = [B, C] ---
  {
    stepNumber: 3,
    codeLine: 13,
    description: 'A is now visited. Queue contains [B, C].',
    variables: { visited: 'A', queue: 'B,C', order: 'A', node: 'A' },
    changedVariables: ['queue'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'visited',
        B: 'in_frontier',
        C: 'in_frontier',
        D: 'unvisited',
        E: 'unvisited',
        F: 'unvisited',
      }),
      edges: makeEdges({
        'A-B': 'visited',
        'A-C': 'visited',
      }),
      auxiliary: { label: 'Queue', items: ['B', 'C'] },
    },
    prediction: null,
    explanation:
      'A is fully processed and marked visited. B and C are in the queue, waiting to be explored.',
    hints: ['', '', ''],
  },

  // --- Step 4: Dequeue B, mark current ---
  {
    stepNumber: 4,
    codeLine: 6,
    description: 'Dequeue the front of the queue. Which node is dequeued next?',
    variables: { visited: 'A', queue: 'B,C', order: 'A', node: 'A' },
    changedVariables: ['node'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'visited',
        B: 'current',
        C: 'in_frontier',
        D: 'unvisited',
        E: 'unvisited',
        F: 'unvisited',
      }),
      edges: makeEdges({
        'A-B': 'visited',
        'A-C': 'visited',
      }),
      auxiliary: { label: 'Queue', items: ['C'] },
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Which node is dequeued next from [B, C]?',
      options: [
        { id: 'B', label: 'B' },
        { id: 'C', label: 'C' },
        { id: 'D', label: 'D' },
        { id: 'E', label: 'E' },
      ],
      correctId: 'B',
    },
    explanation:
      'BFS uses FIFO order. B was added before C, so B is dequeued next.',
    hints: [
      'A queue is first-in, first-out (FIFO).',
      'B was added to the queue before C.',
      'B is dequeued next.',
    ],
  },

  // --- Step 5: Process B - add neighbors D, E ---
  {
    stepNumber: 5,
    codeLine: 11,
    description: 'Visit B, then add its unvisited neighbors to the queue.',
    variables: { visited: 'A,B', queue: 'C', order: 'A,B', node: 'B' },
    changedVariables: ['visited', 'queue', 'order'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'visited',
        B: 'current',
        C: 'in_frontier',
        D: 'unvisited',
        E: 'unvisited',
        F: 'unvisited',
      }),
      edges: makeEdges({
        'A-B': 'visited',
        'A-C': 'visited',
        'B-D': 'exploring',
        'B-E': 'exploring',
      }),
      auxiliary: { label: 'Queue', items: ['C'] },
    },
    prediction: {
      type: 'multi_select',
      prompt: 'Which neighbors of B are added to the queue?',
      options: [
        { id: 'A', label: 'A' },
        { id: 'C', label: 'C' },
        { id: 'D', label: 'D' },
        { id: 'E', label: 'E' },
        { id: 'F', label: 'F' },
      ],
      correctIds: ['D', 'E'],
    },
    explanation:
      'B has neighbors D and E (A is already visited). Both D and E are added to the queue.',
    hints: [
      'Look at the edges leaving B. Which neighbors have not been visited?',
      'B connects to A, D, and E, but A is already visited.',
      'D and E are added to the queue.',
    ],
  },

  // --- Step 6: B visited, queue = [C, D, E] ---
  {
    stepNumber: 6,
    codeLine: 13,
    description: 'B is now visited. Queue contains [C, D, E].',
    variables: { visited: 'A,B', queue: 'C,D,E', order: 'A,B', node: 'B' },
    changedVariables: ['queue'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'visited',
        B: 'visited',
        C: 'in_frontier',
        D: 'in_frontier',
        E: 'in_frontier',
        F: 'unvisited',
      }),
      edges: makeEdges({
        'A-B': 'visited',
        'A-C': 'visited',
        'B-D': 'visited',
        'B-E': 'visited',
      }),
      auxiliary: { label: 'Queue', items: ['C', 'D', 'E'] },
    },
    prediction: {
      type: 'value',
      prompt: 'How many nodes are currently in the queue?',
      correctValue: '3',
      acceptableValues: ['3', 'three'],
      placeholder: 'Enter a number',
    },
    explanation:
      'The queue now holds [C, D, E] - three nodes. C was already there; D and E were just added.',
    hints: [
      'Count the nodes waiting in the queue.',
      'C was already in the queue; D and E were just added.',
      'The answer is 3.',
    ],
  },

  // --- Step 7: Dequeue C, mark current ---
  {
    stepNumber: 7,
    codeLine: 6,
    description: 'Dequeue the front of the queue. Which node is dequeued next?',
    variables: { visited: 'A,B', queue: 'C,D,E', order: 'A,B', node: 'B' },
    changedVariables: ['node'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'visited',
        B: 'visited',
        C: 'current',
        D: 'in_frontier',
        E: 'in_frontier',
        F: 'unvisited',
      }),
      edges: makeEdges({
        'A-B': 'visited',
        'A-C': 'visited',
        'B-D': 'visited',
        'B-E': 'visited',
      }),
      auxiliary: { label: 'Queue', items: ['D', 'E'] },
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Which node is dequeued next from [C, D, E]?',
      options: [
        { id: 'C', label: 'C' },
        { id: 'D', label: 'D' },
        { id: 'E', label: 'E' },
        { id: 'F', label: 'F' },
      ],
      correctId: 'C',
    },
    explanation:
      'C was added to the queue before D and E, so it is dequeued first (FIFO).',
    hints: [
      'Remember: queues are first-in, first-out.',
      'C was enqueued during the processing of A, before D and E.',
      'C is dequeued next.',
    ],
  },

  // --- Step 8: Process C - add neighbor F ---
  {
    stepNumber: 8,
    codeLine: 11,
    description: 'Visit C, then add its unvisited neighbors to the queue.',
    variables: { visited: 'A,B,C', queue: 'D,E', order: 'A,B,C', node: 'C' },
    changedVariables: ['visited', 'queue', 'order'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'visited',
        B: 'visited',
        C: 'current',
        D: 'in_frontier',
        E: 'in_frontier',
        F: 'unvisited',
      }),
      edges: makeEdges({
        'A-B': 'visited',
        'A-C': 'visited',
        'B-D': 'visited',
        'B-E': 'visited',
        'C-F': 'exploring',
      }),
      auxiliary: { label: 'Queue', items: ['D', 'E'] },
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Which node is added to the queue from C\'s neighbors?',
      options: [
        { id: 'A', label: 'A' },
        { id: 'B', label: 'B' },
        { id: 'F', label: 'F' },
        { id: 'none', label: 'No new nodes' },
      ],
      correctId: 'F',
    },
    explanation:
      'C has one unvisited neighbor: F. A is already visited. F is added to the queue.',
    hints: [
      'Look at edges leaving C.',
      'C connects to A and F, but A is already visited.',
      'F is the only node added.',
    ],
  },

  // --- Step 9: Dequeue D ---
  {
    stepNumber: 9,
    codeLine: 6,
    description: 'C is now visited. Dequeue the next node from [D, E, F].',
    variables: { visited: 'A,B,C', queue: 'D,E,F', order: 'A,B,C', node: 'C' },
    changedVariables: ['node', 'queue'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'visited',
        B: 'visited',
        C: 'visited',
        D: 'current',
        E: 'in_frontier',
        F: 'in_frontier',
      }),
      edges: makeEdges({
        'A-B': 'visited',
        'A-C': 'visited',
        'B-D': 'visited',
        'B-E': 'visited',
        'C-F': 'visited',
      }),
      auxiliary: { label: 'Queue', items: ['E', 'F'] },
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Which node is dequeued next from [D, E, F]?',
      options: [
        { id: 'D', label: 'D' },
        { id: 'E', label: 'E' },
        { id: 'F', label: 'F' },
      ],
      correctId: 'D',
    },
    explanation:
      'D was enqueued first among D, E, F. FIFO order means D is dequeued next. D has no unvisited neighbors, so nothing is added.',
    hints: [
      'FIFO: the first node added is the first removed.',
      'D was added before E and F.',
      'D is dequeued next.',
    ],
  },

  // --- Step 10: Dequeue E (auto-advance) ---
  {
    stepNumber: 10,
    codeLine: 6,
    description: 'D is visited (no unvisited neighbors). Dequeue E from [E, F].',
    variables: { visited: 'A,B,C,D', queue: 'E,F', order: 'A,B,C,D', node: 'D' },
    changedVariables: ['visited', 'order', 'node', 'queue'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'visited',
        B: 'visited',
        C: 'visited',
        D: 'visited',
        E: 'current',
        F: 'in_frontier',
      }),
      edges: makeEdges({
        'A-B': 'visited',
        'A-C': 'visited',
        'B-D': 'visited',
        'B-E': 'visited',
        'C-F': 'visited',
      }),
      auxiliary: { label: 'Queue', items: ['F'] },
    },
    prediction: null,
    explanation:
      'E is dequeued. Like D, E has no unvisited neighbors, so nothing new is added to the queue.',
    hints: ['', '', ''],
  },

  // --- Step 11: Dequeue F, all visited ---
  {
    stepNumber: 11,
    codeLine: 14,
    description: 'Dequeue F. All nodes have been visited. BFS is complete!',
    variables: {
      visited: 'A,B,C,D,E,F',
      queue: '',
      order: 'A,B,C,D,E,F',
      node: 'F',
    },
    changedVariables: ['visited', 'order', 'node', 'queue'],
    dataStructure: {
      type: 'graph',
      nodes: makeNodes({
        A: 'visited',
        B: 'visited',
        C: 'visited',
        D: 'visited',
        E: 'visited',
        F: 'visited',
      }),
      edges: makeEdges({
        'A-B': 'visited',
        'A-C': 'visited',
        'B-D': 'visited',
        'B-E': 'visited',
        'C-F': 'visited',
      }),
      auxiliary: { label: 'Queue', items: [] },
    },
    prediction: {
      type: 'value',
      prompt: 'What is the complete BFS traversal order?',
      correctValue: 'A, B, C, D, E, F',
      acceptableValues: [
        'A, B, C, D, E, F',
        'A,B,C,D,E,F',
        'A B C D E F',
        'ABCDEF',
      ],
      placeholder: 'e.g. A, B, C, D, E, F',
    },
    explanation:
      'F is the last node visited. The queue is now empty, so BFS terminates. The full traversal order is A, B, C, D, E, F - nodes were explored level by level.',
    hints: [
      'List all nodes in the order they were dequeued and visited.',
      'Level 0: A. Level 1: B, C. Level 2: D, E, F.',
      'The answer is A, B, C, D, E, F.',
    ],
  },
];

export const bfsDemo: StateTracerBlueprint = {
  algorithmName: 'Breadth-First Search',
  algorithmDescription:
    'Explore a graph level by level using a queue, visiting all neighbors before moving deeper.',
  narrativeIntro:
    'Traverse a graph using BFS starting from node A. Can you predict which node is visited next?',
  code: CODE,
  language: 'python',
  steps,
};
