import { ComplexityAnalyzerBlueprint } from '../types';

export const complexityAnalyzerInsertionSort: ComplexityAnalyzerBlueprint = {
  algorithmName: 'Insertion Sort',
  algorithmDescription:
    'Analyze insertion sort — the simple in-place sorting algorithm that builds the sorted array one element at a time.',
  challenges: [
    {
      challengeId: 'ca-isort-1',
      type: 'identify_from_code',
      title: 'Insertion Sort — Worst Case',
      description: 'Determine the worst-case time complexity.',
      code: `def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr`,
      language: 'python',
      correctComplexity: 'O(n\u00B2)',
      options: ['O(n)', 'O(n log n)', 'O(n\u00B2)', 'O(n\u00B3)'],
      explanation:
        'The outer loop runs n-1 times. In the worst case (reverse-sorted array), the inner while loop runs i times for the i-th iteration. Total: 1+2+...+(n-1) = n(n-1)/2 = O(n\u00B2).',
      points: 100,
      hints: [
        'Consider the worst case: what arrangement maximizes the inner loop?',
        'In a reverse-sorted array, every element must be shifted all the way back.',
        '1+2+...+(n-1) = n(n-1)/2 = O(n\u00B2).',
      ],
    },
    {
      challengeId: 'ca-isort-2',
      type: 'identify_from_code',
      title: 'Insertion Sort — Best Case',
      description: 'What is the best-case time complexity?',
      code: `def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr`,
      language: 'python',
      correctComplexity: 'O(n)',
      options: ['O(1)', 'O(n)', 'O(n log n)', 'O(n\u00B2)'],
      explanation:
        'In the best case (already sorted), the inner while loop condition arr[j] > key is immediately false for every i. The outer loop still runs n-1 times but does O(1) work each = O(n).',
      points: 100,
      hints: [
        'What happens when the array is already sorted?',
        'For each i, arr[i-1] <= arr[i] so the while loop body never executes.',
        'n-1 iterations of the outer loop, O(1) each = O(n).',
      ],
    },
    {
      challengeId: 'ca-isort-3',
      type: 'infer_from_growth',
      title: 'Insertion Sort — Worst Case Growth',
      description: 'Comparison counts for reverse-sorted arrays of various sizes.',
      growthData: {
        inputSizes: [10, 20, 50, 100, 200, 500],
        operationCounts: [45, 190, 1225, 4950, 19900, 124750],
      },
      correctComplexity: 'O(n\u00B2)',
      options: ['O(n)', 'O(n log n)', 'O(n\u00B2)', 'O(2\u207F)'],
      explanation:
        'Doubling n (10\u219220) roughly quadruples operations (45\u2192190 \u2248 4.2x). Going 5x (10\u219250) increases by ~27x (45\u21921225 \u2248 27x, close to 25). This quadratic growth confirms O(n\u00B2).',
      points: 100,
      hints: [
        'What happens to the operation count when you double n?',
        '10\u219220: 45\u2192190 (\u00D74.2). 100\u2192200: 4950\u219219900 (\u00D74.0). Roughly quadrupling.',
        'Doubling n \u2192 4x operations = O(n\u00B2).',
      ],
    },
  ],
};
