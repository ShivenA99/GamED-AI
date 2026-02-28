import { ComplexityAnalyzerBlueprint } from '../types';

export const complexityAnalyzerBubbleSort: ComplexityAnalyzerBlueprint = {
  algorithmName: 'Bubble Sort',
  algorithmDescription:
    'Analyze the time complexity of bubble sort — the simple comparison-based sorting algorithm.',
  challenges: [
    {
      challengeId: 'ca-bsort-1',
      type: 'identify_from_code',
      title: 'Bubble Sort — Worst Case',
      description: 'Determine the worst-case time complexity of this implementation.',
      code: `def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr`,
      language: 'python',
      correctComplexity: 'O(n\u00B2)',
      options: ['O(n)', 'O(n log n)', 'O(n\u00B2)', 'O(n\u00B3)'],
      explanation:
        'The outer loop runs n times. The inner loop runs n-1, n-2, ..., 1 times. Total comparisons: n(n-1)/2 = O(n\u00B2). The early exit optimization (swapped flag) helps the best case but the worst case remains O(n\u00B2).',
      points: 100,
      hints: [
        'Count the nested loops and how many times each runs.',
        'Outer loop: n iterations. Inner loop: up to n-i-1 iterations per outer loop.',
        'Sum of 1+2+...+(n-1) = n(n-1)/2 = O(n\u00B2).',
      ],
    },
    {
      challengeId: 'ca-bsort-2',
      type: 'infer_from_growth',
      title: 'Bubble Sort — Growth Pattern',
      description: 'The table shows comparisons for different array sizes. What is the growth rate?',
      growthData: {
        inputSizes: [10, 20, 50, 100, 200, 500],
        operationCounts: [45, 190, 1225, 4950, 19900, 124750],
      },
      correctComplexity: 'O(n\u00B2)',
      options: ['O(n)', 'O(n log n)', 'O(n\u00B2)', 'O(2\u207F)'],
      explanation:
        'When n doubles (10\u219220), comparisons roughly quadruple (45\u2192190 \u2248 4.2x). When n goes 10x (10\u2192100), comparisons go ~100x (45\u21924950 = 110x). This quadratic relationship is O(n\u00B2).',
      points: 100,
      hints: [
        'Compare how comparisons change when you double the input size.',
        'From n=10 to n=20: comparisons go from 45 to 190 (about 4x). From n=100 to n=200: 4950 to 19900 (about 4x).',
        'Doubling n quadruples the work \u2014 that is the signature of O(n\u00B2).',
      ],
    },
    {
      challengeId: 'ca-bsort-3',
      type: 'identify_from_code',
      title: 'Bubble Sort — Best Case',
      description: 'With the early-exit optimization, what is the best-case time complexity?',
      code: `def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break  # No swaps = already sorted
    return arr`,
      language: 'python',
      correctComplexity: 'O(n)',
      options: ['O(1)', 'O(n)', 'O(n log n)', 'O(n\u00B2)'],
      explanation:
        'In the best case (already sorted array), the inner loop runs n-1 comparisons on the first pass, makes no swaps, and the outer loop breaks immediately. One pass through n elements = O(n).',
      points: 100,
      hints: [
        'Think about what happens when the array is already sorted.',
        'If no swaps happen in the first pass, the loop breaks early.',
        'One pass through the array = n-1 comparisons = O(n).',
      ],
    },
  ],
};
