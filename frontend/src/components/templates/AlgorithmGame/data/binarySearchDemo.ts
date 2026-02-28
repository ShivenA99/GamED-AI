import { StateTracerBlueprint, ExecutionStep } from '../types';

const CODE = `def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

# Example: binary_search([1, 2, 3, 4, 5, 7, 9], 7)`;

// ============================================================================
// Full execution trace: binary search for 7 in [1, 2, 3, 4, 5, 7, 9]
// 2 iterations: mid=3 (arr[3]=4 < 7 → go right), mid=5 (arr[5]=7 → found!)
// 10 steps with mixed prediction types
// ============================================================================

const steps: ExecutionStep[] = [
  // --- Step 0: INIT ---
  {
    stepNumber: 0,
    codeLine: 1,
    description: 'Function called with arr = [1, 2, 3, 4, 5, 7, 9] and target = 7',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 0, right: 6 },
    changedVariables: ['arr', 'target', 'left', 'right'],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: null, // auto-advance
    explanation:
      'The function receives a sorted array and the target value 7. We initialize left = 0 and right = 6 (last index).',
    hints: ['', '', ''],
  },

  // =================== ITERATION 1 ===================

  // --- Step 1: While condition check ---
  {
    stepNumber: 1,
    codeLine: 3,
    description: 'Check while condition: is left (0) <= right (6)?',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 0, right: 6 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [
        { index: 0, color: 'active' },
        { index: 1, color: 'active' },
        { index: 2, color: 'active' },
        { index: 3, color: 'active' },
        { index: 4, color: 'active' },
        { index: 5, color: 'active' },
        { index: 6, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Will the while loop execute? (Is left <= right, i.e., 0 <= 6?)',
      options: [
        { id: 'yes', label: 'Yes \u2014 loop executes' },
        { id: 'no', label: 'No \u2014 loop skipped' },
      ],
      correctId: 'yes',
    },
    explanation:
      'left = 0 and right = 6. Since 0 <= 6 is true, the while loop body executes. The entire array is our search range.',
    hints: [
      'Compare the values of left and right.',
      'left is 0 and right is 6. Is 0 <= 6?',
      'Yes \u2014 the loop executes because 0 <= 6.',
    ],
  },

  // --- Step 2: Compute mid ---
  {
    stepNumber: 2,
    codeLine: 4,
    description: 'Compute mid = (left + right) // 2 = (0 + 6) // 2',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 0, right: 6, mid: 3 },
    changedVariables: ['mid'],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [
        { index: 0, color: 'active' },
        { index: 1, color: 'active' },
        { index: 2, color: 'active' },
        { index: 3, color: 'comparing' },
        { index: 4, color: 'active' },
        { index: 5, color: 'active' },
        { index: 6, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: {
      type: 'value',
      prompt: 'What is mid = (0 + 6) // 2?',
      correctValue: '3',
      acceptableValues: ['3'],
      placeholder: 'e.g. 3',
    },
    explanation:
      'mid = (0 + 6) // 2 = 6 // 2 = 3. We will check the element at index 3, which is arr[3] = 4.',
    hints: [
      'Add left and right, then do integer division by 2.',
      '(0 + 6) = 6. What is 6 // 2?',
      'mid = 3.',
    ],
  },

  // --- Step 3: Compare arr[mid] with target ---
  {
    stepNumber: 3,
    codeLine: 5,
    description: 'Compare arr[3] = 4 with target = 7',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 0, right: 6, mid: 3 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [
        { index: 0, color: 'active' },
        { index: 1, color: 'active' },
        { index: 2, color: 'active' },
        { index: 3, color: 'comparing' },
        { index: 4, color: 'active' },
        { index: 5, color: 'active' },
        { index: 6, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is arr[3] = 4 equal to, less than, or greater than target = 7?',
      options: [
        { id: 'eq', label: 'Equal (4 == 7)' },
        { id: 'lt', label: 'Less than (4 < 7)' },
        { id: 'gt', label: 'Greater than (4 > 7)' },
      ],
      correctId: 'lt',
    },
    explanation:
      'arr[3] = 4 and target = 7. Since 4 < 7, the target must be in the right half of the current range. We will move left to mid + 1.',
    hints: [
      'Compare the value at the midpoint (4) with the target (7).',
      '4 is smaller than 7.',
      'Less than \u2014 4 < 7, so we search the right half.',
    ],
  },

  // --- Step 4: Update left = mid + 1 ---
  {
    stepNumber: 4,
    codeLine: 8,
    description: 'arr[3] = 4 < 7, so search right half: left = mid + 1',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 4, right: 6, mid: 3 },
    changedVariables: ['left'],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [
        { index: 4, color: 'active' },
        { index: 5, color: 'active' },
        { index: 6, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: {
      type: 'value',
      prompt: 'What is the new value of left after left = mid + 1?',
      correctValue: '4',
      acceptableValues: ['4'],
      placeholder: 'e.g. 4',
    },
    explanation:
      'Since arr[mid] < target, we discard the left half. left = 3 + 1 = 4. The new search range is indices [4, 5, 6] which hold values [5, 7, 9].',
    hints: [
      'mid is 3. What is mid + 1?',
      '3 + 1 = 4. left is updated to 4.',
      'left = 4. The search range narrows to [4..6].',
    ],
  },

  // =================== ITERATION 2 ===================

  // --- Step 5: While condition check ---
  {
    stepNumber: 5,
    codeLine: 3,
    description: 'Check while condition: is left (4) <= right (6)?',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 4, right: 6, mid: 3 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [
        { index: 4, color: 'active' },
        { index: 5, color: 'active' },
        { index: 6, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Will the while loop continue? (Is left <= right, i.e., 4 <= 6?)',
      options: [
        { id: 'yes', label: 'Yes \u2014 loop continues' },
        { id: 'no', label: 'No \u2014 loop ends' },
      ],
      correctId: 'yes',
    },
    explanation:
      'left = 4 and right = 6. Since 4 <= 6 is true, we continue searching. The search range is now [5, 7, 9].',
    hints: [
      'Compare left and right.',
      'left is 4, right is 6. Is 4 <= 6?',
      'Yes \u2014 the loop continues because 4 <= 6.',
    ],
  },

  // --- Step 6: Compute mid ---
  {
    stepNumber: 6,
    codeLine: 4,
    description: 'Compute mid = (left + right) // 2 = (4 + 6) // 2',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 4, right: 6, mid: 5 },
    changedVariables: ['mid'],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [
        { index: 4, color: 'active' },
        { index: 5, color: 'comparing' },
        { index: 6, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: {
      type: 'value',
      prompt: 'What is mid = (4 + 6) // 2?',
      correctValue: '5',
      acceptableValues: ['5'],
      placeholder: 'e.g. 5',
    },
    explanation:
      'mid = (4 + 6) // 2 = 10 // 2 = 5. We will check arr[5] = 7.',
    hints: [
      'Add left and right, then integer-divide by 2.',
      '(4 + 6) = 10. What is 10 // 2?',
      'mid = 5.',
    ],
  },

  // --- Step 7: Compare arr[mid] with target ---
  {
    stepNumber: 7,
    codeLine: 5,
    description: 'Compare arr[5] = 7 with target = 7',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 4, right: 6, mid: 5 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [
        { index: 4, color: 'active' },
        { index: 5, color: 'comparing' },
        { index: 6, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is arr[5] = 7 equal to, less than, or greater than target = 7?',
      options: [
        { id: 'eq', label: 'Equal (7 == 7)' },
        { id: 'lt', label: 'Less than (7 < 7)' },
        { id: 'gt', label: 'Greater than (7 > 7)' },
      ],
      correctId: 'eq',
    },
    explanation:
      'arr[5] = 7 and target = 7. They are equal! We have found the target at index 5.',
    hints: [
      'Compare the value at index 5 with the target.',
      'arr[5] is 7 and target is 7. Are they the same?',
      'Equal \u2014 7 == 7. The target is found!',
    ],
  },

  // --- Step 8: Return mid ---
  {
    stepNumber: 8,
    codeLine: 6,
    description: 'Target found! Return mid = 5',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 4, right: 6, mid: 5 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [
        { index: 5, color: 'success' },
      ],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: {
      type: 'value',
      prompt: 'What index is returned?',
      correctValue: '5',
      acceptableValues: ['5'],
      placeholder: 'e.g. 5',
    },
    explanation:
      'The target 7 was found at index 5. The function returns 5. Binary search found the element in just 2 iterations!',
    hints: [
      'The function returns the index where the target was found.',
      'We found 7 at index mid. What is mid?',
      'The answer is 5.',
    ],
  },

  // --- Step 9: Result summary ---
  {
    stepNumber: 9,
    codeLine: 6,
    description: 'Binary search complete. Which indices were examined during the search?',
    variables: { arr: [1, 2, 3, 4, 5, 7, 9], target: 7, left: 4, right: 6, mid: 5, result: 5 },
    changedVariables: ['result'],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5, 7, 9],
      highlights: [
        { index: 3, color: 'comparing' },
        { index: 5, color: 'success' },
      ],
      sortedIndices: [0, 1, 2, 3, 4, 5, 6],
    },
    prediction: {
      type: 'multi_select',
      prompt: 'Which indices were checked as mid during the search?',
      options: [
        { id: '0', label: 'Index 0 (value 1)' },
        { id: '1', label: 'Index 1 (value 2)' },
        { id: '2', label: 'Index 2 (value 3)' },
        { id: '3', label: 'Index 3 (value 4)' },
        { id: '4', label: 'Index 4 (value 5)' },
        { id: '5', label: 'Index 5 (value 7)' },
        { id: '6', label: 'Index 6 (value 9)' },
      ],
      correctIds: ['3', '5'],
    },
    explanation:
      'Binary search checked only 2 out of 7 elements: index 3 (value 4) and index 5 (value 7). This is much faster than linear search, which might check all 7 elements. Binary search runs in O(log n) time.',
    hints: [
      'Think about which elements we computed as mid.',
      'In iteration 1, mid was 3. In iteration 2, mid was 5.',
      'Indices 3 and 5 were the only ones checked.',
    ],
  },
];

export const binarySearchDemo: StateTracerBlueprint = {
  algorithmName: 'Binary Search',
  algorithmDescription:
    'Efficiently find an element in a sorted array by repeatedly halving the search range.',
  narrativeIntro:
    'Search for 7 in a sorted array. How quickly can binary search narrow down the position?',
  code: CODE,
  language: 'python',
  steps,
};
