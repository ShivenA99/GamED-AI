import { BugHunterBlueprint } from '../types';

export const bugHunterBFS: BugHunterBlueprint = {
  algorithmName: 'Breadth-First Search (BFS)',
  algorithmDescription:
    'BFS is a graph traversal algorithm that explores all neighbors at the current depth before moving to nodes at the next depth level. It uses a queue (FIFO) to manage the frontier and guarantees the shortest path in unweighted graphs.',
  narrativeIntro:
    "This BFS implementation traverses a graph, but something's off \u2014 the traversal order doesn't match BFS. Find the 2 bugs.",
  language: 'python',

  buggyCode: `def bfs(graph, start):
    visited = set()
    queue = [start]
    order = []
    while queue:
        node = queue.pop()
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        for neighbor in graph[node]:
            queue.append(neighbor)
    return order`,

  correctCode: `def bfs(graph, start):
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
    return order`,

  bugs: [
    {
      bugId: 'bug-1',
      lineNumber: 6,
      buggyLineText: '        node = queue.pop()',
      correctLineText: '        node = queue.pop(0)',
      bugType: 'logic_error',
      difficulty: 2,
      explanation:
        'queue.pop() removes from the END (LIFO \u2014 stack behavior = DFS), but BFS requires removing from the FRONT (FIFO). queue.pop(0) dequeues from the front for correct BFS order.',
      bugTypeExplanation:
        'A logic error means the code runs without crashing but implements the wrong algorithm or strategy.',
      fixOptions: [
        {
          id: 'fix-1a',
          codeText: '        node = queue.pop()',
          isCorrect: false,
          feedback:
            'pop() without an argument removes from the end, making this a stack (DFS), not a queue (BFS).',
        },
        {
          id: 'fix-1b',
          codeText: '        node = queue.pop(0)',
          isCorrect: true,
          feedback:
            'Correct! pop(0) removes from the front of the list, giving FIFO (queue) behavior needed for BFS.',
        },
        {
          id: 'fix-1c',
          codeText: '        node = queue.pop(-1)',
          isCorrect: false,
          feedback:
            'pop(-1) is the same as pop() \u2014 it removes from the end, giving DFS behavior.',
        },
        {
          id: 'fix-1d',
          codeText: '        node = queue.remove(queue[0])',
          isCorrect: false,
          feedback:
            'remove() returns None, not the removed element. This would cause node to be None.',
        },
      ],
      hints: [
        'This is a logic error \u2014 the code implements a different algorithm than intended.',
        'The bug is in how elements are removed from the queue (lines 5-6).',
        'Line 6 uses pop() which removes from the wrong end of the list for BFS.',
      ],
    },
    {
      bugId: 'bug-2',
      lineNumber: 12,
      buggyLineText: '            queue.append(neighbor)',
      correctLineText:
        '            if neighbor not in visited:\n                queue.append(neighbor)',
      bugType: 'logic_error',
      difficulty: 2,
      explanation:
        'Without checking if a neighbor was already visited, we add duplicates to the queue. While the visited check on line 7 prevents processing duplicates, the queue grows unnecessarily large with repeated entries.',
      bugTypeExplanation:
        'A logic error means the code works but is inefficient or produces subtly wrong results due to missing conditions.',
      fixOptions: [
        {
          id: 'fix-2a',
          codeText: '            queue.append(neighbor)',
          isCorrect: false,
          feedback:
            "This adds ALL neighbors regardless of whether they've been visited, causing the queue to fill with duplicates.",
        },
        {
          id: 'fix-2b',
          codeText:
            '            if neighbor not in visited:\n                queue.append(neighbor)',
          isCorrect: true,
          feedback:
            'Correct! Checking visited before enqueueing prevents duplicate entries and keeps the queue efficient.',
        },
        {
          id: 'fix-2c',
          codeText:
            '            if neighbor in visited:\n                queue.append(neighbor)',
          isCorrect: false,
          feedback:
            'This is backwards \u2014 it would only enqueue already-visited nodes, which would never be processed.',
        },
        {
          id: 'fix-2d',
          codeText: '            queue.insert(0, neighbor)',
          isCorrect: false,
          feedback:
            "Inserting at the front would change traversal order and still doesn't filter visited nodes.",
        },
      ],
      hints: [
        'This is a logic error \u2014 a necessary condition check is missing.',
        'The bug is in how neighbors are added to the queue (lines 11-12).',
        'Line 12 should check whether the neighbor was already visited before adding to the queue.',
      ],
    },
  ],

  testCases: [
    {
      id: 'test-1',
      inputDescription:
        'graph = {A:[B,C], B:[D,E], C:[F], D:[], E:[], F:[]}, start = A',
      expectedOutput: '[A, B, C, D, E, F]',
      buggyOutput: '[A, C, F, B, E, D]',
      exposedBugs: ['bug-1'],
    },
    {
      id: 'test-2',
      inputDescription: 'graph = {1:[2,3], 2:[4], 3:[4], 4:[]}, start = 1',
      expectedOutput: '[1, 2, 3, 4]',
      buggyOutput: '[1, 3, 4, 2, 4]',
      exposedBugs: ['bug-1', 'bug-2'],
    },
  ],

  redHerrings: [
    {
      lineNumber: 3,
      feedback:
        'Initializing the queue with the start node is correct. BFS always begins by enqueueing the starting node.',
    },
    {
      lineNumber: 9,
      feedback:
        "Adding the node to visited when it's dequeued (not when enqueued) is a valid BFS approach. This correctly prevents reprocessing.",
    },
  ],

  config: {
    revealSequentially: true,
    showTestOutput: true,
    showRunButton: false,
    fixMode: 'multiple_choice',
    maxWrongLineClicks: 10,
  },
};
