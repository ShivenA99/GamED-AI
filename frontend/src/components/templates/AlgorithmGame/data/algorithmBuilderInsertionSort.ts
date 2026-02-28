import { AlgorithmBuilderBlueprint } from '../types';

export const algorithmBuilderInsertionSort: AlgorithmBuilderBlueprint = {
  algorithmName: 'Insertion Sort',
  algorithmDescription:
    'Insertion Sort builds a sorted subarray one element at a time by shifting larger elements right to make room. O(n\u00B2) worst case, O(n) best case (nearly sorted).',
  problemDescription:
    'Build an insertion sort function that sorts an array in ascending order by inserting each element into its correct position in the sorted portion.',
  language: 'python',

  correct_order: [
    { id: 'is-1', code: 'def insertion_sort(arr):', indent_level: 0, is_distractor: false },
    { id: 'is-2', code: 'for i in range(1, len(arr)):', indent_level: 1, is_distractor: false },
    { id: 'is-3', code: 'key = arr[i]', indent_level: 2, is_distractor: false },
    { id: 'is-4', code: 'j = i - 1', indent_level: 2, is_distractor: false },
    { id: 'is-5', code: 'while j >= 0 and arr[j] > key:', indent_level: 2, is_distractor: false },
    { id: 'is-6', code: 'arr[j + 1] = arr[j]', indent_level: 3, is_distractor: false },
    { id: 'is-7', code: 'j -= 1', indent_level: 3, is_distractor: false },
    { id: 'is-8', code: 'arr[j + 1] = key', indent_level: 2, is_distractor: false },
    { id: 'is-9', code: 'return arr', indent_level: 1, is_distractor: false },
  ],

  distractors: [
    {
      id: 'is-d1',
      code: 'while j > 0 and arr[j] > key:',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'Using j > 0 instead of j >= 0 skips comparing with arr[0], so the smallest element may never reach the front of the array.',
    },
    {
      id: 'is-d2',
      code: 'arr[j] = key',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'Placing key at arr[j] is off by one. After the while loop, j points one position before the insertion point, so key goes at arr[j+1].',
    },
  ],

  config: {
    indentation_matters: true,
    max_attempts: null,
    show_line_numbers: true,
    allow_indent_adjustment: true,
  },

  hints: [
    'The outer loop starts from index 1 (the second element). Each iteration inserts one element into the sorted portion.',
    'Inside the loop: save the key, walk j backward while elements are larger than key, shift them right, then place key.',
    'Order: def \u2192 for i in range(1,len) \u2192 key=arr[i] \u2192 j=i-1 \u2192 while j>=0 and arr[j]>key \u2192 shift right \u2192 j-=1 \u2192 arr[j+1]=key \u2192 return.',
  ],

  test_cases: [
    { id: 'is-t1', inputDescription: 'arr = [12, 11, 13, 5, 6]', expectedOutput: '[5, 6, 11, 12, 13]' },
    { id: 'is-t2', inputDescription: 'arr = [1, 2, 3]', expectedOutput: '[1, 2, 3]' },
  ],
};
