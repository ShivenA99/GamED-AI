import { AlgorithmBuilderBlueprint } from '../types';

export const algorithmBuilderBFS: AlgorithmBuilderBlueprint = {
  algorithmName: 'Breadth-First Search',
  algorithmDescription:
    'BFS explores a graph level by level using a queue (FIFO). It finds the shortest path in unweighted graphs and runs in O(V + E) time.',
  problemDescription:
    'Build a BFS function that returns all nodes reachable from a start node in a graph represented as an adjacency list.',
  language: 'python',

  correct_order: [
    { id: 'bfs-1', code: 'from collections import deque', indent_level: 0, is_distractor: false },
    { id: 'bfs-2', code: 'def bfs(graph, start):', indent_level: 0, is_distractor: false },
    { id: 'bfs-3', code: 'visited = set()', indent_level: 1, is_distractor: false },
    { id: 'bfs-4', code: 'queue = deque([start])', indent_level: 1, is_distractor: false },
    { id: 'bfs-5', code: 'visited.add(start)', indent_level: 1, is_distractor: false },
    { id: 'bfs-6', code: 'result = []', indent_level: 1, is_distractor: false },
    { id: 'bfs-7', code: 'while queue:', indent_level: 1, is_distractor: false },
    { id: 'bfs-8', code: 'node = queue.popleft()', indent_level: 2, is_distractor: false },
    { id: 'bfs-9', code: 'result.append(node)', indent_level: 2, is_distractor: false },
    { id: 'bfs-10', code: 'for neighbor in graph[node]:', indent_level: 2, is_distractor: false },
    { id: 'bfs-11', code: 'if neighbor not in visited:', indent_level: 3, is_distractor: false },
    { id: 'bfs-12', code: 'visited.add(neighbor)', indent_level: 4, is_distractor: false },
    { id: 'bfs-13', code: 'queue.append(neighbor)', indent_level: 4, is_distractor: false },
    { id: 'bfs-14', code: 'return result', indent_level: 1, is_distractor: false },
  ],

  distractors: [
    {
      id: 'bfs-d1',
      code: 'stack = [start]',
      indent_level: 1,
      is_distractor: true,
      distractor_explanation:
        'Using a stack instead of a deque/queue turns BFS into DFS. BFS requires FIFO ordering via a queue.',
    },
    {
      id: 'bfs-d2',
      code: 'node = queue.pop()',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'pop() removes from the right (LIFO/stack behavior). BFS needs popleft() for FIFO queue behavior.',
    },
    {
      id: 'bfs-d3',
      code: 'queue.append(neighbor)',
      indent_level: 3,
      is_distractor: true,
      distractor_explanation:
        'This appends without checking if the neighbor was already visited, causing infinite loops in cyclic graphs.',
    },
  ],

  config: {
    indentation_matters: true,
    max_attempts: null,
    show_line_numbers: true,
    allow_indent_adjustment: true,
  },

  hints: [
    'BFS uses a queue (deque) and a visited set. The import statement comes first.',
    'The core loop: dequeue a node, process it, then enqueue all unvisited neighbors. Remember to mark neighbors as visited before enqueueing.',
    'Order: import \u2192 def \u2192 visited set \u2192 queue init \u2192 mark start \u2192 result list \u2192 while loop \u2192 popleft \u2192 append result \u2192 for neighbor \u2192 if not visited \u2192 add+enqueue \u2192 return.',
  ],

  test_cases: [
    {
      id: 'bfs-t1',
      inputDescription: "graph = {'A': ['B','C'], 'B': ['D'], 'C': ['D'], 'D': []}, start = 'A'",
      expectedOutput: "['A', 'B', 'C', 'D']",
    },
  ],
};
