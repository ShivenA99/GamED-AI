import { AlgorithmBuilderBlueprint } from '../types';

export const algorithmBuilderBubbleSort: AlgorithmBuilderBlueprint = {
  algorithmName: 'Bubble Sort',
  algorithmDescription:
    'Bubble Sort repeatedly steps through the list, compares adjacent elements, and swaps them if they are in the wrong order. O(n\u00B2) time, O(1) space.',
  problemDescription:
    'Build a bubble sort function that sorts an array in ascending order using adjacent element swaps. Include the early-exit optimization.',
  language: 'python',

  correct_order: [
    { id: 'bb-1', code: 'def bubble_sort(arr):', indent_level: 0, is_distractor: false },
    { id: 'bb-2', code: 'n = len(arr)', indent_level: 1, is_distractor: false },
    { id: 'bb-3', code: 'for i in range(n - 1):', indent_level: 1, is_distractor: false },
    { id: 'bb-4', code: 'swapped = False', indent_level: 2, is_distractor: false },
    { id: 'bb-5', code: 'for j in range(n - 1 - i):', indent_level: 2, is_distractor: false },
    { id: 'bb-6', code: 'if arr[j] > arr[j + 1]:', indent_level: 3, is_distractor: false },
    { id: 'bb-7', code: 'arr[j], arr[j + 1] = arr[j + 1], arr[j]', indent_level: 4, is_distractor: false },
    { id: 'bb-8', code: 'swapped = True', indent_level: 4, is_distractor: false },
    { id: 'bb-9', code: 'if not swapped:', indent_level: 2, is_distractor: false },
    { id: 'bb-10', code: 'break', indent_level: 3, is_distractor: false },
    { id: 'bb-11', code: 'return arr', indent_level: 1, is_distractor: false },
  ],

  distractors: [
    {
      id: 'bb-d1',
      code: 'for j in range(n + 1):',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'range(n+1) causes an IndexError when accessing arr[j+1]. The inner loop must shrink each pass using range(n-1-i).',
    },
    {
      id: 'bb-d2',
      code: 'if arr[j] >= arr[j + 1]:',
      indent_level: 3,
      is_distractor: true,
      distractor_explanation:
        'Using >= instead of > causes unnecessary swaps for equal elements, making the sort unstable and doing extra work.',
    },
  ],

  config: {
    indentation_matters: true,
    max_attempts: null,
    show_line_numbers: true,
    allow_indent_adjustment: true,
  },

  hints: [
    'Bubble Sort uses two nested loops \u2014 the outer controls passes, the inner does adjacent comparisons.',
    'The inner loop range decreases each pass (n-1-i) because the largest element "bubbles" to the end each iteration.',
    'Structure: def \u2192 n=len \u2192 outer for \u2192 swapped=False \u2192 inner for(n-1-i) \u2192 if/swap/swapped=True \u2192 early exit \u2192 return.',
  ],

  test_cases: [
    { id: 'bb-t1', inputDescription: 'arr = [5, 3, 8, 1, 2]', expectedOutput: '[1, 2, 3, 5, 8]' },
    { id: 'bb-t2', inputDescription: 'arr = [1, 2, 3]', expectedOutput: '[1, 2, 3] (already sorted, early exit)' },
  ],
};
