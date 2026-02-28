import { AlgorithmBuilderBlueprint } from '../types';

export const algorithmBuilderBinarySearch: AlgorithmBuilderBlueprint = {
  algorithmName: 'Binary Search',
  algorithmDescription:
    'Binary search efficiently finds a target value in a sorted array by repeatedly dividing the search range in half, achieving O(log n) time complexity.',
  problemDescription:
    'Build a binary search function that returns the index of target in a sorted array arr, or -1 if not found.',
  language: 'python',

  correct_order: [
    { id: 'bs-1', code: 'def binary_search(arr, target):', indent_level: 0, is_distractor: false },
    { id: 'bs-2', code: 'left, right = 0, len(arr) - 1', indent_level: 1, is_distractor: false },
    { id: 'bs-3', code: 'while left <= right:', indent_level: 1, is_distractor: false },
    { id: 'bs-4', code: 'mid = (left + right) // 2', indent_level: 2, is_distractor: false },
    { id: 'bs-5', code: 'if arr[mid] == target:', indent_level: 2, is_distractor: false },
    { id: 'bs-6', code: 'return mid', indent_level: 3, is_distractor: false },
    { id: 'bs-7', code: 'elif arr[mid] < target:', indent_level: 2, is_distractor: false },
    { id: 'bs-8', code: 'left = mid + 1', indent_level: 3, is_distractor: false },
    { id: 'bs-9', code: 'else:', indent_level: 2, is_distractor: false },
    { id: 'bs-10', code: 'right = mid - 1', indent_level: 3, is_distractor: false },
    { id: 'bs-11', code: 'return -1', indent_level: 1, is_distractor: false },
  ],

  distractors: [
    {
      id: 'bs-d1',
      code: 'while left < right:',
      indent_level: 1,
      is_distractor: true,
      distractor_explanation:
        'Using < instead of <= would skip checking when left equals right, missing the last element in the search range.',
    },
    {
      id: 'bs-d2',
      code: 'mid = (left + right) / 2',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'Float division (/) gives a decimal result. Integer division (//) is needed for array indexing.',
    },
    {
      id: 'bs-d3',
      code: 'left = mid',
      indent_level: 3,
      is_distractor: true,
      distractor_explanation:
        'Must be mid + 1, not mid. Using just mid causes an infinite loop when arr[mid] < target because left never advances past mid.',
    },
  ],

  config: {
    indentation_matters: true,
    max_attempts: null,
    show_line_numbers: true,
    allow_indent_adjustment: true,
  },

  hints: [
    'The function signature and return statement frame the algorithm — place those first.',
    'Think about the structure: function def \u2192 initialization \u2192 while loop \u2192 comparisons \u2192 return.',
    'The correct order starts with def, then left/right init, while loop with <=, mid calculation, three-way if/elif/else, and finally return -1.',
  ],

  test_cases: [
    { id: 'bs-t1', inputDescription: 'arr = [1, 3, 5, 7, 9], target = 5', expectedOutput: '2' },
    { id: 'bs-t2', inputDescription: 'arr = [1, 3, 5, 7, 9], target = 9', expectedOutput: '4' },
    { id: 'bs-t3', inputDescription: 'arr = [1], target = 1', expectedOutput: '0' },
    { id: 'bs-t4', inputDescription: 'arr = [2, 4, 6], target = 5', expectedOutput: '-1' },
  ],
};
