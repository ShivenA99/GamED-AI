import { BugHunterBlueprint } from '../types';

export const bugHunterRoundsDemo: BugHunterBlueprint = {
  algorithmName: 'Algorithm Gauntlet',
  algorithmDescription:
    'Three rounds of debugging across different algorithms: binary search, bubble sort, and BFS. Each round presents a different buggy implementation.',
  narrativeIntro:
    'Welcome to the Algorithm Gauntlet! You\'ll face three rounds of debugging, each with a different algorithm. Fix one bug per round to advance.',
  language: 'python',

  rounds: [
    {
      roundId: 'round-1',
      title: 'Binary Search: Off-by-One',
      buggyCode: `def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    while left < right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1`,
      correctCode: `def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1`,
      bugs: [
        {
          bugId: 'r1-bug-1',
          lineNumber: 4,
          buggyLineText: '    while left < right:',
          correctLineText: '    while left <= right:',
          bugType: 'off_by_one',
          difficulty: 1,
          explanation:
            'Using < instead of <= exits the loop when left equals right, missing the last element.',
          bugTypeExplanation: 'Off-by-one errors are boundary mistakes by exactly 1.',
          fixOptions: [
            { id: 'r1-fix-a', codeText: '    while left < right:', isCorrect: false, feedback: 'This is the current buggy code.' },
            { id: 'r1-fix-b', codeText: '    while left <= right:', isCorrect: true, feedback: 'Correct! <= ensures the last element is checked.' },
            { id: 'r1-fix-c', codeText: '    while left != right:', isCorrect: false, feedback: 'This could miss elements or loop forever.' },
            { id: 'r1-fix-d', codeText: '    while True:', isCorrect: false, feedback: 'This would create an infinite loop without a proper break.' },
          ],
          hints: [
            'This is an off-by-one error.',
            'Look at the while loop condition.',
            'Line 4: the comparison operator is wrong.',
          ],
        },
      ],
      testCases: [
        { id: 'r1-t1', inputDescription: '[1,3,5,7,9], target=9', expectedOutput: '4', buggyOutput: '-1', exposedBugs: ['r1-bug-1'] },
        { id: 'r1-t2', inputDescription: '[1,3,5,7,9], target=5', expectedOutput: '2', buggyOutput: '2', exposedBugs: [] },
        { id: 'r1-t3', inputDescription: '[1], target=1', expectedOutput: '0', buggyOutput: '-1', exposedBugs: ['r1-bug-1'] },
      ],
      redHerrings: [
        { lineNumber: 5, feedback: 'The midpoint calculation is correct.' },
      ],
    },
    {
      roundId: 'round-2',
      title: 'Bubble Sort: Wrong Operator',
      buggyCode: `def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] < arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr`,
      correctCode: `def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr`,
      bugs: [
        {
          bugId: 'r2-bug-1',
          lineNumber: 5,
          buggyLineText: '            if arr[j] < arr[j + 1]:',
          correctLineText: '            if arr[j] > arr[j + 1]:',
          bugType: 'wrong_operator',
          difficulty: 1,
          explanation:
            'Using < instead of > sorts in descending order instead of ascending.',
          bugTypeExplanation: 'Wrong operator errors use an incorrect comparison or arithmetic operator.',
          fixOptions: [
            { id: 'r2-fix-a', codeText: '            if arr[j] < arr[j + 1]:', isCorrect: false, feedback: 'This sorts descending, not ascending.' },
            { id: 'r2-fix-b', codeText: '            if arr[j] > arr[j + 1]:', isCorrect: true, feedback: 'Correct! > swaps when left is larger, producing ascending order.' },
            { id: 'r2-fix-c', codeText: '            if arr[j] >= arr[j + 1]:', isCorrect: false, feedback: 'This makes the sort unstable by swapping equal elements.' },
            { id: 'r2-fix-d', codeText: '            if arr[j] == arr[j + 1]:', isCorrect: false, feedback: 'This only swaps equal elements, which does nothing useful.' },
          ],
          hints: [
            'This is a wrong operator error.',
            'Look at the comparison in the inner loop.',
            'Line 5: the comparison direction is reversed.',
          ],
        },
      ],
      testCases: [
        { id: 'r2-t1', inputDescription: '[64, 34, 25, 12]', expectedOutput: '[12, 25, 34, 64]', buggyOutput: '[64, 34, 25, 12]', exposedBugs: ['r2-bug-1'] },
        { id: 'r2-t2', inputDescription: '[5, 1, 4, 2, 8]', expectedOutput: '[1, 2, 4, 5, 8]', buggyOutput: '[8, 5, 4, 2, 1]', exposedBugs: ['r2-bug-1'] },
      ],
      redHerrings: [
        { lineNumber: 4, feedback: 'The loop range n - i - 1 is correct, skipping already-sorted elements.' },
      ],
    },
    {
      roundId: 'round-3',
      title: 'BFS: Missing Visited Check',
      buggyCode: `from collections import deque

def bfs(graph, start):
    visited = set()
    queue = deque([start])
    result = []
    while queue:
        node = queue.popleft()
        result.append(node)
        visited.add(node)
        for neighbor in graph[node]:
            queue.append(neighbor)
    return result`,
      correctCode: `from collections import deque

def bfs(graph, start):
    visited = set()
    queue = deque([start])
    result = []
    while queue:
        node = queue.popleft()
        result.append(node)
        visited.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                queue.append(neighbor)
    return result`,
      bugs: [
        {
          bugId: 'r3-bug-1',
          bugLines: [12],
          buggyLinesText: ['            queue.append(neighbor)'],
          correctLinesText: ['            if neighbor not in visited:', '                queue.append(neighbor)'],
          bugType: 'missing_base_case',
          difficulty: 2,
          explanation:
            'Without checking if a neighbor is already visited, nodes get added to the queue multiple times, causing infinite loops in cyclic graphs and incorrect results.',
          bugTypeExplanation: 'A missing guard check allows unintended repeated processing.',
          fixOptions: [
            { id: 'r3-fix-a', codeText: '            queue.append(neighbor)', isCorrect: false, feedback: 'This is the current buggy code, missing the visited check.' },
            { id: 'r3-fix-b', codeText: '            if neighbor not in visited: queue.append(neighbor)', isCorrect: true, feedback: 'Correct! Checking visited prevents re-processing nodes.' },
            { id: 'r3-fix-c', codeText: '            if neighbor in visited: queue.append(neighbor)', isCorrect: false, feedback: 'This is backwards \u2014 it would only add already-visited nodes.' },
            { id: 'r3-fix-d', codeText: '            if neighbor != start: queue.append(neighbor)', isCorrect: false, feedback: 'This only prevents revisiting the start node, not all visited nodes.' },
          ],
          hints: [
            'A guard condition is missing that prevents repeated work.',
            'The bug is in how neighbors are added to the queue.',
            'Line 12: neighbors should only be added if not already visited.',
          ],
        },
      ],
      testCases: [
        {
          id: 'r3-t1',
          inputDescription: '{A:[B,C], B:[A,D], C:[A], D:[B]}, start=A',
          expectedOutput: '[A, B, C, D]',
          buggyOutput: 'infinite loop',
          exposedBugs: ['r3-bug-1'],
        },
        {
          id: 'r3-t2',
          inputDescription: '{1:[2,3], 2:[4], 3:[], 4:[]}, start=1',
          expectedOutput: '[1, 2, 3, 4]',
          buggyOutput: '[1, 2, 3, 4]',
          exposedBugs: [],
        },
      ],
      redHerrings: [
        { lineNumber: 8, feedback: 'popleft() is correct for BFS \u2014 it processes nodes in FIFO order.' },
        { lineNumber: 10, feedback: 'Adding to visited after dequeuing is a valid BFS pattern.' },
      ],
    },
  ],

  config: {
    revealSequentially: true,
    showTestOutput: true,
    showRunButton: false,
    fixMode: 'multiple_choice',
    maxWrongLineClicks: 10,
    roundMode: true,
  },
};
