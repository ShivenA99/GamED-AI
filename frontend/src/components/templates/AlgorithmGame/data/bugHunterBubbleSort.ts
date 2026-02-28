import { BugHunterBlueprint } from '../types';

export const bugHunterBubbleSort: BugHunterBlueprint = {
  algorithmName: 'Bubble Sort',
  algorithmDescription:
    'Bubble sort is a simple comparison-based sorting algorithm that repeatedly steps through the list, compares adjacent elements, and swaps them if they are in the wrong order. The pass through the list is repeated until the list is sorted, achieving O(n^2) time complexity.',
  narrativeIntro:
    'This bubble sort implementation has two bugs \u2014 one in the comparison logic and one in the swap mechanism. Can you find and fix both?',
  language: 'python',

  buggyCode: `def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] < arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = arr[j]
    return arr`,

  correctCode: `def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
    return arr`,

  bugs: [
    {
      bugId: 'bug-1',
      lineNumber: 5,
      buggyLineText: '            if arr[j] < arr[j + 1]:',
      correctLineText: '            if arr[j] > arr[j + 1]:',
      bugType: 'wrong_operator',
      difficulty: 1,
      explanation:
        'Using < instead of > makes the algorithm swap when elements are in the correct order, resulting in descending sort instead of ascending.',
      bugTypeExplanation:
        'A wrong operator error uses an incorrect comparison or arithmetic operator, reversing the intended logic.',
      fixOptions: [
        {
          id: 'fix-1a',
          codeText: '            if arr[j] < arr[j + 1]:',
          isCorrect: false,
          feedback:
            'This is the current buggy code. It swaps when the left is smaller, producing descending order.',
        },
        {
          id: 'fix-1b',
          codeText: '            if arr[j] > arr[j + 1]:',
          isCorrect: true,
          feedback:
            'Correct! We swap when the left element is larger to bubble it rightward, producing ascending order.',
        },
        {
          id: 'fix-1c',
          codeText: '            if arr[j] >= arr[j + 1]:',
          isCorrect: false,
          feedback:
            'Using >= would also swap equal elements unnecessarily, making the sort unstable.',
        },
        {
          id: 'fix-1d',
          codeText: '            if arr[j] == arr[j + 1]:',
          isCorrect: false,
          feedback:
            "This would only swap equal elements, which doesn't sort anything.",
        },
      ],
      hints: [
        'This is a wrong operator error \u2014 the comparison direction is reversed.',
        'The bug is in the comparison inside the inner loop (lines 4-6).',
        'Line 5 uses the wrong comparison operator \u2014 think about which direction we want to sort.',
      ],
    },
    {
      bugId: 'bug-2',
      lineNumber: 8,
      buggyLineText: '                arr[j + 1] = arr[j]',
      correctLineText: '                arr[j + 1] = temp',
      bugType: 'wrong_variable',
      difficulty: 2,
      explanation:
        'After saving arr[j] to temp and overwriting arr[j] with arr[j+1], we need to write temp (the original arr[j]) into arr[j+1]. Writing arr[j] again just copies the already-overwritten value.',
      bugTypeExplanation:
        'A wrong variable error occurs when a different variable is used than intended, often causing data loss or incorrect computations in swap operations.',
      fixOptions: [
        {
          id: 'fix-2a',
          codeText: '                arr[j + 1] = arr[j]',
          isCorrect: false,
          feedback:
            "This is the current buggy code. After line 7 overwrites arr[j], arr[j] already contains arr[j+1]'s value.",
        },
        {
          id: 'fix-2b',
          codeText: '                arr[j + 1] = temp',
          isCorrect: true,
          feedback:
            'Correct! temp holds the original arr[j] value, which needs to go into arr[j+1] to complete the swap.',
        },
        {
          id: 'fix-2c',
          codeText: '                arr[j + 1] = arr[j - 1]',
          isCorrect: false,
          feedback:
            'arr[j-1] is an unrelated element. The swap is between positions j and j+1 only.',
        },
        {
          id: 'fix-2d',
          codeText: '                arr[j] = temp',
          isCorrect: false,
          feedback:
            "This would put the original value back in arr[j], undoing line 7's assignment and making the swap a no-op.",
        },
      ],
      hints: [
        'This is a wrong variable error \u2014 a variable reference is incorrect.',
        'The bug is in the swap logic (lines 6-8).',
        'Line 8 should use the temporary variable, not arr[j].',
      ],
    },
  ],

  testCases: [
    {
      id: 'test-1',
      inputDescription: 'arr = [64, 34, 25, 12, 22, 11, 90]',
      expectedOutput: '[11, 12, 22, 25, 34, 64, 90]',
      buggyOutput: '[90, 90, 90, 90, 90, 90, 90]',
      exposedBugs: ['bug-1', 'bug-2'],
    },
    {
      id: 'test-2',
      inputDescription: 'arr = [5, 1, 4, 2, 8]',
      expectedOutput: '[1, 2, 4, 5, 8]',
      buggyOutput: '[8, 8, 8, 8, 8]',
      exposedBugs: ['bug-1', 'bug-2'],
    },
  ],

  redHerrings: [
    {
      lineNumber: 4,
      feedback:
        'This correctly reduces the inner loop range as sorted elements accumulate at the end. The n - i - 1 boundary is optimal.',
    },
    {
      lineNumber: 6,
      feedback:
        'Saving arr[j] to a temporary variable before overwriting it is the correct first step of a manual swap.',
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
