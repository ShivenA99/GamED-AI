import { StateTracerBlueprint, ExecutionStep } from '../types';

const CODE = `def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr

# Example: insertion_sort([4, 2, 5, 1, 3])`;

// ============================================================================
// Full execution trace: insertion sort on [4, 2, 5, 1, 3]
// 4 passes (i = 1..4), ~15 meaningful steps with mixed prediction types
// ============================================================================

const steps: ExecutionStep[] = [
  // --- INIT ---
  {
    stepNumber: 0,
    codeLine: 1,
    description: 'Function called with arr = [4, 2, 5, 1, 3]',
    variables: { arr: [4, 2, 5, 1, 3], i: null, key: null, j: null },
    changedVariables: ['arr'],
    dataStructure: {
      type: 'array',
      elements: [4, 2, 5, 1, 3],
      highlights: [],
    },
    prediction: null, // auto-advance
    explanation:
      'The function receives the unsorted array [4, 2, 5, 1, 3]. Insertion sort will build the sorted portion from left to right, inserting each element into its correct position.',
    hints: ['', '', ''],
  },

  // =================== PASS 1 (i=1): key = arr[1] = 2 ===================

  // Step 1: Pick key = 2
  {
    stepNumber: 1,
    codeLine: 3,
    description: 'i=1: Pick key = arr[1] = 2. The sorted prefix is [4].',
    variables: { arr: [4, 2, 5, 1, 3], i: 1, key: 2, j: 0 },
    changedVariables: ['i', 'key', 'j'],
    dataStructure: {
      type: 'array',
      elements: [4, 2, 5, 1, 3],
      highlights: [
        { index: 0, color: 'sorted' },
        { index: 1, color: 'active' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'What is the key for this pass?',
      options: [
        { id: 'a', label: '4' },
        { id: 'b', label: '2' },
        { id: 'c', label: '5' },
        { id: 'd', label: '1' },
      ],
      correctId: 'b',
    },
    explanation:
      'At i=1 the key is arr[1] = 2. We need to insert 2 into the sorted prefix [4].',
    hints: [
      'The key is always the element at index i.',
      'i is 1, so the key is arr[1].',
      'The key is 2.',
    ],
  },

  // Step 2: Compare arr[0]=4 > key=2? Yes, shift 4 right
  {
    stepNumber: 2,
    codeLine: 5,
    description: 'Compare arr[0]=4 with key=2. Is 4 > 2?',
    variables: { arr: [4, 2, 5, 1, 3], i: 1, key: 2, j: 0 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [4, 2, 5, 1, 3],
      highlights: [
        { index: 0, color: 'comparing' },
        { index: 1, color: 'active' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'arr[0] = 4 and key = 2. Will 4 be shifted right?',
      options: [
        { id: 'yes', label: 'Yes \u2014 4 > 2, shift right' },
        { id: 'no', label: 'No \u2014 4 is not greater, stop' },
      ],
      correctId: 'yes',
    },
    explanation:
      '4 > 2 is true, so we shift 4 one position to the right (arr[1] = 4). Then j becomes -1, so the while loop ends.',
    hints: [
      'Compare the sorted element with the key.',
      '4 is greater than 2, so the condition is true.',
      'Yes \u2014 4 shifts right to make room for 2.',
    ],
  },

  // Step 3: After shift + insert key=2 at position 0 -> [2, 4, 5, 1, 3]
  {
    stepNumber: 3,
    codeLine: 8,
    description: 'Insert key=2 at position 0. Pass 1 complete!',
    variables: { arr: [2, 4, 5, 1, 3], i: 1, key: 2, j: -1 },
    changedVariables: ['arr', 'j'],
    dataStructure: {
      type: 'array',
      elements: [4, 4, 5, 1, 3],
      highlights: [
        { index: 0, color: 'active' },
        { index: 1, color: 'swapping' },
      ],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'After shifting 4 right and inserting 2, what is the array?',
      elements: [4, 2, 5, 1, 3],
      correctArrangement: [2, 4, 5, 1, 3],
    },
    explanation:
      '4 shifted right to index 1, and key=2 is placed at index 0. The array is now [2, 4, 5, 1, 3]. Sorted prefix: [2, 4].',
    hints: [
      '4 moved from index 0 to index 1. Where does 2 go?',
      '2 is smaller than 4, so it goes to the leftmost position.',
      'The array becomes [2, 4, 5, 1, 3].',
    ],
  },

  // =================== PASS 2 (i=2): key = arr[2] = 5 ===================

  // Step 4: Pick key = 5
  {
    stepNumber: 4,
    codeLine: 3,
    description: 'i=2: Pick key = arr[2] = 5. The sorted prefix is [2, 4].',
    variables: { arr: [2, 4, 5, 1, 3], i: 2, key: 5, j: 1 },
    changedVariables: ['i', 'key', 'j'],
    dataStructure: {
      type: 'array',
      elements: [2, 4, 5, 1, 3],
      highlights: [
        { index: 0, color: 'sorted' },
        { index: 1, color: 'sorted' },
        { index: 2, color: 'active' },
      ],
      sortedIndices: [0, 1],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'What is the key for this pass (i=2)?',
      options: [
        { id: 'a', label: '2' },
        { id: 'b', label: '4' },
        { id: 'c', label: '5' },
        { id: 'd', label: '1' },
      ],
      correctId: 'c',
    },
    explanation:
      'At i=2 the key is arr[2] = 5. We need to find where 5 belongs in the sorted prefix [2, 4].',
    hints: [
      'The key is the element at the current index i.',
      'i=2, so the key is arr[2].',
      'The key is 5.',
    ],
  },

  // Step 5: Compare arr[1]=4 > key=5? No, insert in place
  {
    stepNumber: 5,
    codeLine: 5,
    description: 'Compare arr[1]=4 with key=5. Is 4 > 5?',
    variables: { arr: [2, 4, 5, 1, 3], i: 2, key: 5, j: 1 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [2, 4, 5, 1, 3],
      highlights: [
        { index: 0, color: 'sorted' },
        { index: 1, color: 'comparing' },
        { index: 2, color: 'active' },
      ],
      sortedIndices: [0, 1],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'arr[1] = 4 and key = 5. Will any shifting happen?',
      options: [
        { id: 'yes', label: 'Yes \u2014 4 > 5, shift right' },
        { id: 'no', label: 'No \u2014 4 is not greater than 5, insert in place' },
      ],
      correctId: 'no',
    },
    explanation:
      '4 > 5 is false, so the while loop does not execute. Key 5 stays in its current position. No shifts needed.',
    hints: [
      'Compare 4 with 5. Which is larger?',
      '4 is less than 5, so the while condition fails immediately.',
      'No \u2014 5 is already in the correct position.',
    ],
  },

  // Step 6: Array stays [2, 4, 5, 1, 3]
  {
    stepNumber: 6,
    codeLine: 8,
    description: 'Key=5 stays at index 2. Array unchanged: [2, 4, 5, 1, 3]. Sorted prefix: [2, 4, 5].',
    variables: { arr: [2, 4, 5, 1, 3], i: 2, key: 5, j: 1 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [2, 4, 5, 1, 3],
      highlights: [
        { index: 0, color: 'sorted' },
        { index: 1, color: 'sorted' },
        { index: 2, color: 'sorted' },
      ],
      sortedIndices: [0, 1, 2],
    },
    prediction: null, // auto-advance
    explanation:
      'Since 5 >= 4, no shifting was needed. The sorted prefix grows to [2, 4, 5]. Three elements are now sorted.',
    hints: ['', '', ''],
  },

  // =================== PASS 3 (i=3): key = arr[3] = 1 ===================

  // Step 7: Pick key = 1
  {
    stepNumber: 7,
    codeLine: 3,
    description: 'i=3: Pick key = arr[3] = 1. The sorted prefix is [2, 4, 5].',
    variables: { arr: [2, 4, 5, 1, 3], i: 3, key: 1, j: 2 },
    changedVariables: ['i', 'key', 'j'],
    dataStructure: {
      type: 'array',
      elements: [2, 4, 5, 1, 3],
      highlights: [
        { index: 0, color: 'sorted' },
        { index: 1, color: 'sorted' },
        { index: 2, color: 'sorted' },
        { index: 3, color: 'active' },
      ],
      sortedIndices: [0, 1, 2],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'What is the key for this pass (i=3)?',
      options: [
        { id: 'a', label: '5' },
        { id: 'b', label: '3' },
        { id: 'c', label: '1' },
        { id: 'd', label: '2' },
      ],
      correctId: 'c',
    },
    explanation:
      'At i=3 the key is arr[3] = 1. Since 1 is smaller than every element in the sorted prefix [2, 4, 5], it will need to travel all the way to the front.',
    hints: [
      'The key comes from index i=3.',
      'arr[3] = 1.',
      'The key is 1.',
    ],
  },

  // Step 8: All three elements shift right: 5, 4, 2
  {
    stepNumber: 8,
    codeLine: 6,
    description: 'Shifting: 5 > 1, 4 > 1, 2 > 1 \u2014 all three shift right to make room.',
    variables: { arr: [2, 4, 5, 1, 3], i: 3, key: 1, j: -1 },
    changedVariables: ['j'],
    dataStructure: {
      type: 'array',
      elements: [2, 4, 5, 1, 3],
      highlights: [
        { index: 0, color: 'swapping' },
        { index: 1, color: 'swapping' },
        { index: 2, color: 'swapping' },
        { index: 3, color: 'active' },
      ],
      sortedIndices: [0, 1, 2],
    },
    prediction: {
      type: 'multi_select',
      prompt: 'Which elements in the sorted prefix shift right to make room for key=1?',
      options: [
        { id: '0', label: '2 (index 0)' },
        { id: '1', label: '4 (index 1)' },
        { id: '2', label: '5 (index 2)' },
      ],
      correctIds: ['0', '1', '2'],
    },
    explanation:
      'All three sorted elements (5, 4, 2) are greater than key=1, so each shifts right by one position. j decrements from 2 to -1.',
    hints: [
      'Compare each sorted element with key=1. Which are greater?',
      '5 > 1, 4 > 1, and 2 > 1 \u2014 all three are greater.',
      'All three elements (2, 4, 5) shift right.',
    ],
  },

  // Step 9: After shift + insert key=1 at position 0 -> [1, 2, 4, 5, 3]
  {
    stepNumber: 9,
    codeLine: 8,
    description: 'Insert key=1 at position 0. Pass 3 complete!',
    variables: { arr: [1, 2, 4, 5, 3], i: 3, key: 1, j: -1 },
    changedVariables: ['arr'],
    dataStructure: {
      type: 'array',
      elements: [2, 2, 4, 5, 3],
      highlights: [
        { index: 0, color: 'active' },
        { index: 1, color: 'swapping' },
        { index: 2, color: 'swapping' },
        { index: 3, color: 'swapping' },
      ],
      sortedIndices: [0, 1, 2, 3],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'After all shifts and inserting 1, what is the array?',
      elements: [2, 4, 5, 1, 3],
      correctArrangement: [1, 2, 4, 5, 3],
    },
    explanation:
      'Elements 2, 4, 5 each shifted one position right. Key=1 is inserted at index 0. Array: [1, 2, 4, 5, 3]. Sorted prefix: [1, 2, 4, 5].',
    hints: [
      '2, 4, and 5 each move one position to the right.',
      'That opens up index 0 for the key.',
      'The array becomes [1, 2, 4, 5, 3].',
    ],
  },

  // =================== PASS 4 (i=4): key = arr[4] = 3 ===================

  // Step 10: Pick key = 3
  {
    stepNumber: 10,
    codeLine: 3,
    description: 'i=4: Pick key = arr[4] = 3. The sorted prefix is [1, 2, 4, 5].',
    variables: { arr: [1, 2, 4, 5, 3], i: 4, key: 3, j: 3 },
    changedVariables: ['i', 'key', 'j'],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 4, 5, 3],
      highlights: [
        { index: 0, color: 'sorted' },
        { index: 1, color: 'sorted' },
        { index: 2, color: 'sorted' },
        { index: 3, color: 'sorted' },
        { index: 4, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'What is the key for the final pass (i=4)?',
      options: [
        { id: 'a', label: '5' },
        { id: 'b', label: '3' },
        { id: 'c', label: '4' },
        { id: 'd', label: '1' },
      ],
      correctId: 'b',
    },
    explanation:
      'At i=4 the key is arr[4] = 3. We need to find the correct position for 3 within [1, 2, 4, 5].',
    hints: [
      'The key is always at index i.',
      'i=4, so the key is arr[4].',
      'The key is 3.',
    ],
  },

  // Step 11: Compare arr[3]=5 > key=3? Yes, shift
  {
    stepNumber: 11,
    codeLine: 5,
    description: 'Compare arr[3]=5 with key=3. Is 5 > 3?',
    variables: { arr: [1, 2, 4, 5, 3], i: 4, key: 3, j: 3 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 4, 5, 3],
      highlights: [
        { index: 0, color: 'sorted' },
        { index: 1, color: 'sorted' },
        { index: 2, color: 'sorted' },
        { index: 3, color: 'comparing' },
        { index: 4, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'arr[3] = 5 and key = 3. Will 5 shift right?',
      options: [
        { id: 'yes', label: 'Yes \u2014 5 > 3, shift right' },
        { id: 'no', label: 'No \u2014 stop here' },
      ],
      correctId: 'yes',
    },
    explanation:
      '5 > 3 is true, so 5 shifts from index 3 to index 4. j decrements to 2.',
    hints: [
      'Compare 5 with the key value 3.',
      '5 is greater than 3.',
      'Yes \u2014 5 shifts right.',
    ],
  },

  // Step 12: Compare arr[2]=4 > key=3? Yes, shift
  {
    stepNumber: 12,
    codeLine: 5,
    description: 'Compare arr[2]=4 with key=3. Is 4 > 3?',
    variables: { arr: [1, 2, 4, 5, 3], i: 4, key: 3, j: 2 },
    changedVariables: ['j'],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 4, 5, 3],
      highlights: [
        { index: 0, color: 'sorted' },
        { index: 1, color: 'sorted' },
        { index: 2, color: 'comparing' },
        { index: 3, color: 'swapping' },
        { index: 4, color: 'active' },
      ],
      sortedIndices: [0, 1, 2, 3],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'arr[2] = 4 and key = 3. Will 4 also shift right?',
      options: [
        { id: 'yes', label: 'Yes \u2014 4 > 3, shift right' },
        { id: 'no', label: 'No \u2014 4 is not greater, stop' },
      ],
      correctId: 'yes',
    },
    explanation:
      '4 > 3 is true, so 4 shifts from index 2 to index 3. j decrements to 1. Now arr[1]=2, and 2 > 3 is false, so the while loop stops.',
    hints: [
      'Compare 4 with the key value 3.',
      '4 is greater than 3, so the while condition is still true.',
      'Yes \u2014 4 shifts right. The loop will stop at arr[1]=2 since 2 < 3.',
    ],
  },

  // Step 13: After shift + insert key=3 at position 2 -> [1, 2, 3, 4, 5]
  {
    stepNumber: 13,
    codeLine: 8,
    description: 'Insert key=3 at position 2. The array is now fully sorted!',
    variables: { arr: [1, 2, 3, 4, 5], i: 4, key: 3, j: 1 },
    changedVariables: ['arr', 'j'],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 4, 4, 5],
      highlights: [
        { index: 0, color: 'sorted' },
        { index: 1, color: 'sorted' },
        { index: 2, color: 'active' },
        { index: 3, color: 'swapping' },
        { index: 4, color: 'swapping' },
      ],
      sortedIndices: [0, 1, 2, 3, 4],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'After shifting 4 and 5 right and inserting 3, what is the final array?',
      elements: [1, 2, 4, 5, 3],
      correctArrangement: [1, 2, 3, 4, 5],
    },
    explanation:
      '4 and 5 shifted right by one position each. Key=3 is inserted at index 2. The array is now [1, 2, 3, 4, 5] \u2014 fully sorted!',
    hints: [
      '4 and 5 each move one position right.',
      'That opens up index 2 for the key=3.',
      'The array becomes [1, 2, 3, 4, 5].',
    ],
  },

  // Step 14: Done!
  {
    stepNumber: 14,
    codeLine: 9,
    description: 'Return the sorted array [1, 2, 3, 4, 5]',
    variables: { arr: [1, 2, 3, 4, 5], i: 4, key: 3, j: 1 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5],
      highlights: [
        { index: 0, color: 'success' },
        { index: 1, color: 'success' },
        { index: 2, color: 'success' },
        { index: 3, color: 'success' },
        { index: 4, color: 'success' },
      ],
      sortedIndices: [0, 1, 2, 3, 4],
    },
    prediction: {
      type: 'multi_select',
      prompt: 'Which elements are now in their correct sorted position?',
      options: [
        { id: '0', label: '1 (index 0)' },
        { id: '1', label: '2 (index 1)' },
        { id: '2', label: '3 (index 2)' },
        { id: '3', label: '4 (index 3)' },
        { id: '4', label: '5 (index 4)' },
      ],
      correctIds: ['0', '1', '2', '3', '4'],
    },
    explanation:
      'Insertion sort complete! The array [4, 2, 5, 1, 3] is now sorted to [1, 2, 3, 4, 5]. Every element is in its correct position.',
    hints: [
      'The algorithm has finished all passes.',
      'Look at the array \u2014 is every element in order?',
      'All five elements are in their correct sorted positions.',
    ],
  },
];

export const insertionSortDemo: StateTracerBlueprint = {
  algorithmName: 'Insertion Sort',
  algorithmDescription:
    'Build the sorted array one element at a time by inserting each into its correct position.',
  narrativeIntro:
    'Sort [4, 2, 5, 1, 3] by inserting elements into their correct position. Can you predict each shift?',
  code: CODE,
  language: 'python',
  steps,
};
