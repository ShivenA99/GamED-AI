import { BugHunterBlueprint } from '../types';

export const bugHunterBinarySearch: BugHunterBlueprint = {
  algorithmName: 'Binary Search',
  algorithmDescription:
    'Binary search is an efficient algorithm for finding a target value in a sorted array. It repeatedly divides the search range in half by comparing the target to the middle element, achieving O(log n) time complexity.',
  narrativeIntro:
    'A search function is failing to find elements that exist in the array. Users report that certain lookups return -1 even though the value is present. Your mission: find and fix the bug hiding in this binary search implementation.',
  language: 'python',

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
      bugId: 'bug-1',
      lineNumber: 4,
      buggyLineText: '    while left < right:',
      correctLineText: '    while left <= right:',
      bugType: 'off_by_one',
      difficulty: 1,
      explanation:
        'The condition `left < right` exits the loop when left equals right, skipping the last element. The correct condition `left <= right` ensures we check when only one element remains in the search range.',
      bugTypeExplanation:
        'An off-by-one error occurs when a loop or index boundary is wrong by exactly 1, causing it to process one too many or too few elements.',
      fixOptions: [
        {
          id: 'fix-a',
          codeText: '    while left < right:',
          isCorrect: false,
          feedback:
            'This is the current buggy code. It exits the loop prematurely when left equals right.',
        },
        {
          id: 'fix-b',
          codeText: '    while left <= right:',
          isCorrect: true,
          feedback:
            "Correct! When left equals right, there's still one element to check. The <= ensures we don't skip it.",
        },
        {
          id: 'fix-c',
          codeText: '    while left != right:',
          isCorrect: false,
          feedback:
            'This would miss cases where left jumps past right after an update, potentially causing an infinite loop.',
        },
        {
          id: 'fix-d',
          codeText: '    while left < right + 1:',
          isCorrect: false,
          feedback:
            'While mathematically equivalent to <=, this is unconventional and obscures the intent.',
        },
      ],
      hints: [
        'This is an off-by-one error \u2014 a boundary is wrong by exactly 1.',
        'The bug is in the loop condition (lines 3-5).',
        'Line 4 has the wrong comparison operator in the while condition.',
      ],
    },
  ],

  testCases: [
    {
      id: 'test-1',
      inputDescription: 'arr = [1, 3, 5, 7, 9], target = 9',
      expectedOutput: '4',
      buggyOutput: '-1',
      exposedBugs: ['bug-1'],
    },
    {
      id: 'test-2',
      inputDescription: 'arr = [1, 3, 5, 7, 9], target = 5',
      expectedOutput: '2',
      buggyOutput: '2',
      exposedBugs: [],
    },
    {
      id: 'test-3',
      inputDescription: 'arr = [1], target = 1',
      expectedOutput: '0',
      buggyOutput: '-1',
      exposedBugs: ['bug-1'],
    },
  ],

  redHerrings: [
    {
      lineNumber: 5,
      feedback:
        "This correctly computes the midpoint using integer division. In Python, there's no integer overflow risk.",
    },
    {
      lineNumber: 9,
      feedback:
        'This correctly narrows the search to the right half. Moving left past mid avoids infinite loops.',
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
