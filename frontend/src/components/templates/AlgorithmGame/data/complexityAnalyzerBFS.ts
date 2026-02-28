import { ComplexityAnalyzerBlueprint } from '../types';

export const complexityAnalyzerBFS: ComplexityAnalyzerBlueprint = {
  algorithmName: 'Breadth-First Search (BFS)',
  algorithmDescription:
    'Analyze the time complexity of BFS — the level-order graph traversal algorithm using a queue.',
  challenges: [
    {
      challengeId: 'ca-bfs-1',
      type: 'identify_from_code',
      title: 'BFS — Overall Complexity',
      description: 'Examine the BFS implementation. V = vertices, E = edges.',
      code: `from collections import deque

def bfs(graph, start):
    visited = set()
    queue = deque([start])
    visited.add(start)
    result = []

    while queue:
        vertex = queue.popleft()
        result.append(vertex)
        for neighbor in graph[vertex]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return result`,
      language: 'python',
      correctComplexity: 'O(V + E)',
      options: ['O(V)', 'O(E)', 'O(V + E)', 'O(V \u00D7 E)'],
      explanation:
        'Each vertex is enqueued and dequeued exactly once: O(V). For each vertex, we iterate over its adjacency list — across all vertices, this totals E edge checks. So the overall complexity is O(V + E).',
      points: 100,
      hints: [
        'Consider vertices and edges separately.',
        'Each vertex enters the queue exactly once. Each edge is examined exactly once (or twice in undirected graphs).',
        'Visiting all V vertices + checking all E edges = O(V + E).',
      ],
    },
    {
      challengeId: 'ca-bfs-2',
      type: 'infer_from_growth',
      title: 'BFS on Complete Graphs',
      description: 'Given BFS operation counts on complete graphs (where E = V(V-1)/2), what is the growth?',
      growthData: {
        inputSizes: [10, 20, 50, 100, 200],
        operationCounts: [55, 210, 1275, 5050, 20100],
      },
      correctComplexity: 'O(n\u00B2)',
      options: ['O(n)', 'O(n log n)', 'O(n\u00B2)', 'O(2\u207F)'],
      explanation:
        'On complete graphs, E = V(V-1)/2 \u2248 V\u00B2/2. So O(V + E) = O(V + V\u00B2) = O(V\u00B2). The growth data confirms this: doubling V roughly quadruples the operation count.',
      points: 100,
      hints: [
        'In a complete graph, every vertex connects to every other vertex.',
        'E = V(V-1)/2 which is roughly V\u00B2/2.',
        'O(V + E) with E = O(V\u00B2) simplifies to O(V\u00B2).',
      ],
    },
    {
      challengeId: 'ca-bfs-3',
      type: 'find_bottleneck',
      title: 'BFS with Path Reconstruction',
      description: 'This BFS finds shortest path then reconstructs it. Which part dominates?',
      code: `from collections import deque

def bfs_shortest_path(graph, start, end):
    # Section A: BFS traversal
    visited = {start: None}
    queue = deque([start])
    while queue:
        vertex = queue.popleft()
        if vertex == end:
            break
        for neighbor in graph[vertex]:
            if neighbor not in visited:
                visited[neighbor] = vertex
                queue.append(neighbor)

    # Section B: Path reconstruction
    path = []
    current = end
    while current is not None:
        path.append(current)
        current = visited.get(current)
    return path[::-1]`,
      language: 'python',
      codeSections: [
        { sectionId: 'sec-a', label: 'Section A: BFS', startLine: 4, endLine: 13, complexity: 'O(V + E)', isBottleneck: true },
        { sectionId: 'sec-b', label: 'Section B: Reconstruct', startLine: 15, endLine: 20, complexity: 'O(V)', isBottleneck: false },
      ],
      correctComplexity: 'O(V + E)',
      options: ['O(V)', 'O(E)', 'O(V + E)', 'O(V\u00B2)'],
      explanation:
        'Section A (BFS) is O(V + E). Section B (path reconstruction) walks back at most V nodes = O(V). Since V + E \u2265 V for any connected graph, the BFS dominates: O(V + E).',
      points: 150,
      hints: [
        'Analyze each section independently.',
        'BFS visits each vertex and edge once. Path reconstruction follows parent pointers back.',
        'O(V + E) dominates O(V), so overall is O(V + E).',
      ],
    },
  ],
};
