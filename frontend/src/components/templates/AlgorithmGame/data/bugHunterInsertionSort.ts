import { BugHunterBlueprint } from '../types';

export const bugHunterInsertionSort: BugHunterBlueprint = {
  algorithmName: 'Insertion Sort',
  algorithmDescription:
    'Insertion sort builds a sorted portion of the array one element at a time. It picks the next unsorted element (the "key"), shifts larger sorted elements to the right, and inserts the key into its correct position. It runs in O(n^2) worst case but O(n) for nearly sorted input.',
  narrativeIntro:
    'This insertion sort has two subtle bugs \u2014 one in the loop boundary and one in where the key gets placed. Can you find them?',
  language: 'python',

  buggyCode: `def insertion_sort(arr):
    for i in range(0, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j] = key
    return arr`,

  correctCode: `def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr`,

  bugs: [
    {
      bugId: 'bug-1',
      lineNumber: 2,
      buggyLineText: '    for i in range(0, len(arr)):',
      correctLineText: '    for i in range(1, len(arr)):',
      bugType: 'off_by_one',
      difficulty: 1,
      explanation:
        'Starting from index 0 means we try to \'insert\' the first element, which sets j = -1 and then arr[-1] = key, overwriting the last element. The first element is already \'sorted\' by itself, so we start from index 1.',
      bugTypeExplanation:
        'An off-by-one error occurs when a loop start or end boundary is wrong by exactly 1.',
      fixOptions: [
        {
          id: 'fix-1a',
          codeText: '    for i in range(0, len(arr)):',
          isCorrect: false,
          feedback:
            'Starting from 0 sets j = -1 on the first iteration, causing arr[-1] (the last element) to be overwritten.',
        },
        {
          id: 'fix-1b',
          codeText: '    for i in range(1, len(arr)):',
          isCorrect: true,
          feedback:
            'Correct! The first element (index 0) is trivially sorted. We start inserting from index 1.',
        },
        {
          id: 'fix-1c',
          codeText: '    for i in range(0, len(arr) - 1):',
          isCorrect: false,
          feedback:
            'This still starts from 0 (wrong) and also skips the last element, leaving it unsorted.',
        },
        {
          id: 'fix-1d',
          codeText: '    for i in range(2, len(arr)):',
          isCorrect: false,
          feedback:
            'Starting from 2 skips index 1, leaving the second element potentially unsorted.',
        },
      ],
      hints: [
        'This is an off-by-one error \u2014 the loop starts at the wrong index.',
        'The bug is in the outer loop range (line 2).',
        'Line 2 starts from 0 but insertion sort\'s outer loop should start from 1.',
      ],
    },
    {
      bugId: 'bug-2',
      lineNumber: 8,
      buggyLineText: '        arr[j] = key',
      correctLineText: '        arr[j + 1] = key',
      bugType: 'wrong_variable',
      difficulty: 2,
      explanation:
        'After the while loop, j points to the element just BEFORE the insertion point (or j = -1 if key goes at the start). The key should go at position j + 1, not j. Using arr[j] overwrites the wrong element.',
      bugTypeExplanation:
        'A wrong variable error occurs when an index or variable is off, writing to or reading from the wrong position.',
      fixOptions: [
        {
          id: 'fix-2a',
          codeText: '        arr[j] = key',
          isCorrect: false,
          feedback:
            'j points to the last element that\'s greater than key (or -1). Writing to arr[j] overwrites an element that should stay in place.',
        },
        {
          id: 'fix-2b',
          codeText: '        arr[j + 1] = key',
          isCorrect: true,
          feedback:
            'Correct! The insertion point is j + 1: the position right after the last element smaller than key.',
        },
        {
          id: 'fix-2c',
          codeText: '        arr[i] = key',
          isCorrect: false,
          feedback:
            'arr[i] has already been shifted by the inner loop. Writing key back to i undoes the shifting work.',
        },
        {
          id: 'fix-2d',
          codeText: '        arr[j - 1] = key',
          isCorrect: false,
          feedback:
            'j - 1 is two positions before the insertion point, overwriting an element that\'s already correctly placed.',
        },
      ],
      hints: [
        'This is a wrong variable error \u2014 the index is off by one.',
        'The bug is in the key placement after the inner loop (line 8).',
        'Line 8 places key at position j, but it should be at j + 1.',
      ],
    },
  ],

  testCases: [
    {
      id: 'test-1',
      inputDescription: 'arr = [5, 2, 4, 6, 1, 3]',
      expectedOutput: '[1, 2, 3, 4, 5, 6]',
      buggyOutput: '[2, 4, 5, 1, 3, 6]',
      exposedBugs: ['bug-1', 'bug-2'],
    },
    {
      id: 'test-2',
      inputDescription: 'arr = [3, 1]',
      expectedOutput: '[1, 3]',
      buggyOutput: '[1, 1]',
      exposedBugs: ['bug-1', 'bug-2'],
    },
  ],

  redHerrings: [
    {
      lineNumber: 4,
      feedback:
        'Starting j at i-1 is correct \u2014 we compare the key against elements from right to left in the sorted portion.',
    },
    {
      lineNumber: 6,
      feedback:
        'Shifting arr[j] to arr[j+1] correctly makes room for the key by moving larger elements one position to the right.',
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
