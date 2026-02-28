import { ComplexityAnalyzerBlueprint } from '../types';

export const complexityAnalyzerBinarySearch: ComplexityAnalyzerBlueprint = {
  algorithmName: 'Binary Search',
  algorithmDescription:
    'Analyze the time complexity of binary search — the classic divide-and-conquer search on sorted arrays.',
  challenges: [
    {
      challengeId: 'ca-bs-1',
      type: 'identify_from_code',
      title: 'Binary Search — Overall Complexity',
      description: 'Examine the code and determine the worst-case time complexity.',
      code: `def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1`,
      language: 'python',
      correctComplexity: 'O(log n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n\u00B2)'],
      explanation:
        'Each iteration halves the search space. Starting with n elements, after k iterations we have n/2^k elements. The loop ends when n/2^k = 1, so k = log\u2082(n). Therefore O(log n).',
      points: 100,
      hints: [
        'Think about what happens to the search space each iteration.',
        'The search space is halved every time — from n to n/2 to n/4...',
        'Halving n until you reach 1 takes log\u2082(n) steps.',
      ],
    },
    {
      challengeId: 'ca-bs-2',
      type: 'infer_from_growth',
      title: 'Binary Search — Growth Pattern',
      description: 'Given operation counts for different input sizes, identify the growth rate.',
      growthData: {
        inputSizes: [10, 100, 1000, 10000, 100000, 1000000],
        operationCounts: [4, 7, 10, 14, 17, 20],
      },
      correctComplexity: 'O(log n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n\u00B2)'],
      explanation:
        'The operation count grows very slowly: doubling when n increases by 10x. Going from 10 to 1,000,000 (100,000x increase) only adds ~16 operations. This is characteristic of logarithmic growth.',
      points: 100,
      hints: [
        'Notice how slowly the operation count grows compared to n.',
        'When n goes from 10 to 1,000,000, ops only go from 4 to 20.',
        'This slow growth (roughly +3 per 10x increase in n) is O(log n).',
      ],
    },
    {
      challengeId: 'ca-bs-3',
      type: 'find_bottleneck',
      title: 'Binary Search with Preprocessing',
      description: 'This function sorts first, then searches. Which section dominates?',
      code: `def search_with_sort(arr, target):
    # Section A: Sort the array
    arr.sort()

    # Section B: Binary search
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1`,
      language: 'python',
      codeSections: [
        { sectionId: 'sec-a', label: 'Section A: Sort', startLine: 2, endLine: 3, complexity: 'O(n log n)', isBottleneck: true },
        { sectionId: 'sec-b', label: 'Section B: Search', startLine: 5, endLine: 13, complexity: 'O(log n)', isBottleneck: false },
      ],
      correctComplexity: 'O(n log n)',
      options: ['O(log n)', 'O(n)', 'O(n log n)', 'O(n\u00B2)'],
      explanation:
        'Section A (sorting) is O(n log n), Section B (binary search) is O(log n). The overall complexity is determined by the bottleneck: O(n log n) dominates O(log n), so the total is O(n log n).',
      points: 150,
      hints: [
        'Consider the complexity of each section separately.',
        'Python\'s sort() uses Timsort which is O(n log n). Binary search is O(log n).',
        'The overall complexity is the maximum of all sections: O(n log n).',
      ],
    },
  ],
};
