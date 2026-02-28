import { StateTracerBlueprint, ExecutionStep } from '../types';

const CODE = `def bubble_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

# Example: bubble_sort([5, 3, 1, 4, 2])`;

// ============================================================================
// Full execution trace: bubble sort on [5, 3, 1, 4, 2]
// 4 passes, ~20 meaningful steps with mixed prediction types
// ============================================================================

const steps: ExecutionStep[] = [
  // --- INIT ---
  {
    stepNumber: 0,
    codeLine: 1,
    description: 'Function called with arr = [5, 3, 1, 4, 2]',
    variables: { arr: [5, 3, 1, 4, 2], n: 5 },
    changedVariables: ['arr', 'n'],
    dataStructure: {
      type: 'array',
      elements: [5, 3, 1, 4, 2],
      highlights: [],
    },
    prediction: null, // auto-advance
    explanation: 'The function receives the unsorted array and computes n = 5.',
    hints: ['', '', ''],
  },

  // =================== PASS 0 (i=0): j goes 0..3 ===================

  // Step 1: Compare arr[0]=5 vs arr[1]=3
  {
    stepNumber: 1,
    codeLine: 5,
    description: 'Compare arr[0]=5 with arr[1]=3',
    variables: { arr: [5, 3, 1, 4, 2], n: 5, i: 0, j: 0 },
    changedVariables: ['i', 'j'],
    dataStructure: {
      type: 'array',
      elements: [5, 3, 1, 4, 2],
      highlights: [
        { index: 0, color: 'comparing' },
        { index: 1, color: 'comparing' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is arr[0] (5) greater than arr[1] (3)?',
      options: [
        { id: 'yes', label: 'Yes — swap needed' },
        { id: 'no', label: 'No — no swap' },
      ],
      correctId: 'yes',
    },
    explanation: '5 > 3 is true, so we need to swap these elements.',
    hints: [
      'Compare the two highlighted values.',
      '5 is greater than 3, so the condition is true.',
      'The answer is Yes — a swap is needed.',
    ],
  },

  // Step 2: Swap arr[0] and arr[1] → [3, 5, 1, 4, 2]
  {
    stepNumber: 2,
    codeLine: 6,
    description: 'Swap arr[0] and arr[1]',
    variables: { arr: [5, 3, 1, 4, 2], n: 5, i: 0, j: 0 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [5, 3, 1, 4, 2],
      highlights: [
        { index: 0, color: 'swapping' },
        { index: 1, color: 'swapping' },
      ],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'What does the array look like after swapping positions 0 and 1?',
      elements: [5, 3, 1, 4, 2],
      correctArrangement: [3, 5, 1, 4, 2],
    },
    explanation: 'After swapping: arr[0]=3, arr[1]=5. The array becomes [3, 5, 1, 4, 2].',
    hints: [
      'Only the two highlighted elements change positions.',
      'Swap 5 and 3: the smaller one goes left.',
      'The array becomes [3, 5, 1, 4, 2].',
    ],
  },

  // Step 3: Compare arr[1]=5 vs arr[2]=1
  {
    stepNumber: 3,
    codeLine: 5,
    description: 'Compare arr[1]=5 with arr[2]=1',
    variables: { arr: [3, 5, 1, 4, 2], n: 5, i: 0, j: 1 },
    changedVariables: ['arr', 'j'],
    dataStructure: {
      type: 'array',
      elements: [3, 5, 1, 4, 2],
      highlights: [
        { index: 1, color: 'comparing' },
        { index: 2, color: 'comparing' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Will a swap happen between arr[1] (5) and arr[2] (1)?',
      options: [
        { id: 'yes', label: 'Yes — swap needed' },
        { id: 'no', label: 'No — already in order' },
      ],
      correctId: 'yes',
    },
    explanation: '5 > 1 is true. A swap is needed.',
    hints: [
      'Compare 5 and 1.',
      '5 > 1, so the condition on line 5 is true.',
      'Yes — a swap will happen.',
    ],
  },

  // Step 4: Swap arr[1] and arr[2] → [3, 1, 5, 4, 2]
  {
    stepNumber: 4,
    codeLine: 6,
    description: 'Swap arr[1] and arr[2]',
    variables: { arr: [3, 5, 1, 4, 2], n: 5, i: 0, j: 1 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [3, 5, 1, 4, 2],
      highlights: [
        { index: 1, color: 'swapping' },
        { index: 2, color: 'swapping' },
      ],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'Arrange the array after swapping positions 1 and 2.',
      elements: [3, 5, 1, 4, 2],
      correctArrangement: [3, 1, 5, 4, 2],
    },
    explanation: 'After swapping: arr[1]=1, arr[2]=5. Array is now [3, 1, 5, 4, 2].',
    hints: [
      'Only positions 1 and 2 change.',
      'Swap 5 and 1.',
      'The array becomes [3, 1, 5, 4, 2].',
    ],
  },

  // Step 5: Compare arr[2]=5 vs arr[3]=4
  {
    stepNumber: 5,
    codeLine: 5,
    description: 'Compare arr[2]=5 with arr[3]=4',
    variables: { arr: [3, 1, 5, 4, 2], n: 5, i: 0, j: 2 },
    changedVariables: ['arr', 'j'],
    dataStructure: {
      type: 'array',
      elements: [3, 1, 5, 4, 2],
      highlights: [
        { index: 2, color: 'comparing' },
        { index: 3, color: 'comparing' },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What two values are being compared? (format: a, b)',
      correctValue: '5, 4',
      acceptableValues: ['5,4', '5 ,4', '5, 4', '5 , 4'],
      placeholder: 'e.g. 5, 4',
    },
    explanation: 'We compare arr[2]=5 with arr[3]=4. Since 5 > 4, a swap will follow.',
    hints: [
      'Look at the indices j=2 and j+1=3.',
      'arr[2] is 5 and arr[3] is 4.',
      'The answer is 5, 4.',
    ],
  },

  // Step 6: Swap arr[2] and arr[3] → [3, 1, 4, 5, 2]
  {
    stepNumber: 6,
    codeLine: 6,
    description: 'Swap arr[2] and arr[3]',
    variables: { arr: [3, 1, 5, 4, 2], n: 5, i: 0, j: 2 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [3, 1, 5, 4, 2],
      highlights: [
        { index: 2, color: 'swapping' },
        { index: 3, color: 'swapping' },
      ],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'What does the array look like after swapping positions 2 and 3?',
      elements: [3, 1, 5, 4, 2],
      correctArrangement: [3, 1, 4, 5, 2],
    },
    explanation: 'After swap: [3, 1, 4, 5, 2]. The 5 keeps "bubbling" right.',
    hints: [
      'Swap the two highlighted elements.',
      '5 and 4 switch places.',
      'The array becomes [3, 1, 4, 5, 2].',
    ],
  },

  // Step 7: Compare arr[3]=5 vs arr[4]=2
  {
    stepNumber: 7,
    codeLine: 5,
    description: 'Compare arr[3]=5 with arr[4]=2',
    variables: { arr: [3, 1, 4, 5, 2], n: 5, i: 0, j: 3 },
    changedVariables: ['arr', 'j'],
    dataStructure: {
      type: 'array',
      elements: [3, 1, 4, 5, 2],
      highlights: [
        { index: 3, color: 'comparing' },
        { index: 4, color: 'comparing' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is arr[3] (5) greater than arr[4] (2)?',
      options: [
        { id: 'yes', label: 'Yes — swap needed' },
        { id: 'no', label: 'No — no swap' },
      ],
      correctId: 'yes',
    },
    explanation: '5 > 2 is true. One more swap in this pass.',
    hints: [
      'Compare the highlighted values.',
      '5 is greater than 2.',
      'Yes — swap needed.',
    ],
  },

  // Step 8: Swap arr[3] and arr[4] → [3, 1, 4, 2, 5]. Pass 0 done, 5 is sorted.
  {
    stepNumber: 8,
    codeLine: 6,
    description: 'Swap arr[3] and arr[4]. Pass 0 complete!',
    variables: { arr: [3, 1, 4, 5, 2], n: 5, i: 0, j: 3 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [3, 1, 4, 5, 2],
      highlights: [
        { index: 3, color: 'swapping' },
        { index: 4, color: 'swapping' },
      ],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'Arrange the array after the swap. What is sorted at the end?',
      elements: [3, 1, 4, 5, 2],
      correctArrangement: [3, 1, 4, 2, 5],
    },
    explanation: 'After swap: [3, 1, 4, 2, 5]. The largest element (5) has "bubbled" to position 4 — it is now sorted!',
    hints: [
      'Swap positions 3 and 4.',
      '5 and 2 switch places. 5 ends up at the rightmost position.',
      'The array becomes [3, 1, 4, 2, 5].',
    ],
  },

  // Pass boundary question
  {
    stepNumber: 9,
    codeLine: 3,
    description: 'Pass 0 complete. Which elements are in their final sorted position?',
    variables: { arr: [3, 1, 4, 2, 5], n: 5, i: 1, j: 0 },
    changedVariables: ['arr', 'i', 'j'],
    dataStructure: {
      type: 'array',
      elements: [3, 1, 4, 2, 5],
      highlights: [{ index: 4, color: 'sorted' }],
      sortedIndices: [4],
    },
    prediction: {
      type: 'multi_select',
      prompt: 'Which elements are now in their final sorted position?',
      options: [
        { id: '0', label: '3 (index 0)' },
        { id: '1', label: '1 (index 1)' },
        { id: '2', label: '4 (index 2)' },
        { id: '3', label: '2 (index 3)' },
        { id: '4', label: '5 (index 4)' },
      ],
      correctIds: ['4'],
    },
    explanation: 'After pass 0, the largest element (5) is in its final position at the end. All other elements may still move.',
    hints: [
      'Bubble sort places one element in its correct position each pass.',
      'The largest unsorted element "bubbles" to the right end.',
      'Only 5 at index 4 is in its final position.',
    ],
  },

  // =================== PASS 1 (i=1): j goes 0..2 ===================

  // Step 10: Compare arr[0]=3 vs arr[1]=1
  {
    stepNumber: 10,
    codeLine: 5,
    description: 'Pass 1: Compare arr[0]=3 with arr[1]=1',
    variables: { arr: [3, 1, 4, 2, 5], n: 5, i: 1, j: 0 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [3, 1, 4, 2, 5],
      highlights: [
        { index: 0, color: 'comparing' },
        { index: 1, color: 'comparing' },
      ],
      sortedIndices: [4],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is arr[0] (3) greater than arr[1] (1)?',
      options: [
        { id: 'yes', label: 'Yes — swap' },
        { id: 'no', label: 'No — skip' },
      ],
      correctId: 'yes',
    },
    explanation: '3 > 1, so we swap.',
    hints: [
      'Compare 3 and 1.',
      '3 is larger.',
      'Yes — swap.',
    ],
  },

  // Step 11: Swap → [1, 3, 4, 2, 5]
  {
    stepNumber: 11,
    codeLine: 6,
    description: 'Swap arr[0] and arr[1]',
    variables: { arr: [3, 1, 4, 2, 5], n: 5, i: 1, j: 0 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [3, 1, 4, 2, 5],
      highlights: [
        { index: 0, color: 'swapping' },
        { index: 1, color: 'swapping' },
      ],
      sortedIndices: [4],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'Arrange the array after swapping positions 0 and 1.',
      elements: [3, 1, 4, 2, 5],
      correctArrangement: [1, 3, 4, 2, 5],
    },
    explanation: 'Array becomes [1, 3, 4, 2, 5].',
    hints: [
      'Swap the first two elements.',
      '3 and 1 switch.',
      '[1, 3, 4, 2, 5].',
    ],
  },

  // Step 12: Compare arr[1]=3 vs arr[2]=4 — NO swap
  {
    stepNumber: 12,
    codeLine: 5,
    description: 'Compare arr[1]=3 with arr[2]=4',
    variables: { arr: [1, 3, 4, 2, 5], n: 5, i: 1, j: 1 },
    changedVariables: ['arr', 'j'],
    dataStructure: {
      type: 'array',
      elements: [1, 3, 4, 2, 5],
      highlights: [
        { index: 1, color: 'comparing' },
        { index: 2, color: 'comparing' },
      ],
      sortedIndices: [4],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is arr[1] (3) greater than arr[2] (4)?',
      options: [
        { id: 'yes', label: 'Yes — swap' },
        { id: 'no', label: 'No — skip (already in order)' },
      ],
      correctId: 'no',
    },
    explanation: '3 < 4, so no swap needed. We move on.',
    hints: [
      'Is 3 greater than 4?',
      '3 is not greater than 4.',
      'No — skip.',
    ],
  },

  // Step 13: Compare arr[2]=4 vs arr[3]=2 → swap
  {
    stepNumber: 13,
    codeLine: 5,
    description: 'Compare arr[2]=4 with arr[3]=2',
    variables: { arr: [1, 3, 4, 2, 5], n: 5, i: 1, j: 2 },
    changedVariables: ['j'],
    dataStructure: {
      type: 'array',
      elements: [1, 3, 4, 2, 5],
      highlights: [
        { index: 2, color: 'comparing' },
        { index: 3, color: 'comparing' },
      ],
      sortedIndices: [4],
    },
    prediction: {
      type: 'value',
      prompt: 'What two values are being compared? (format: a, b)',
      correctValue: '4, 2',
      acceptableValues: ['4,2', '4 ,2', '4, 2', '4 , 2'],
      placeholder: 'e.g. 4, 2',
    },
    explanation: 'We compare arr[2]=4 and arr[3]=2. Since 4 > 2, a swap follows.',
    hints: [
      'Look at indices j=2 and j+1=3.',
      'arr[2]=4 and arr[3]=2.',
      '4, 2.',
    ],
  },

  // Step 14: Swap arr[2] and arr[3] → [1, 3, 2, 4, 5]
  {
    stepNumber: 14,
    codeLine: 6,
    description: 'Swap arr[2] and arr[3]. Pass 1 complete!',
    variables: { arr: [1, 3, 4, 2, 5], n: 5, i: 1, j: 2 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 3, 4, 2, 5],
      highlights: [
        { index: 2, color: 'swapping' },
        { index: 3, color: 'swapping' },
      ],
      sortedIndices: [4],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'Arrange the array after swapping positions 2 and 3.',
      elements: [1, 3, 4, 2, 5],
      correctArrangement: [1, 3, 2, 4, 5],
    },
    explanation: 'Array becomes [1, 3, 2, 4, 5]. Now 4 and 5 are both in their final positions.',
    hints: [
      'Swap positions 2 and 3.',
      '4 and 2 switch places.',
      '[1, 3, 2, 4, 5].',
    ],
  },

  // =================== PASS 2 (i=2): j goes 0..1 ===================

  // Step 15: Compare arr[0]=1 vs arr[1]=3 — NO swap
  {
    stepNumber: 15,
    codeLine: 5,
    description: 'Pass 2: Compare arr[0]=1 with arr[1]=3',
    variables: { arr: [1, 3, 2, 4, 5], n: 5, i: 2, j: 0 },
    changedVariables: ['arr', 'i', 'j'],
    dataStructure: {
      type: 'array',
      elements: [1, 3, 2, 4, 5],
      highlights: [
        { index: 0, color: 'comparing' },
        { index: 1, color: 'comparing' },
      ],
      sortedIndices: [3, 4],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Will a swap happen between arr[0] (1) and arr[1] (3)?',
      options: [
        { id: 'yes', label: 'Yes — swap' },
        { id: 'no', label: 'No — already in order' },
      ],
      correctId: 'no',
    },
    explanation: '1 < 3, no swap needed.',
    hints: [
      'Compare 1 and 3.',
      '1 is smaller.',
      'No swap.',
    ],
  },

  // Step 16: Compare arr[1]=3 vs arr[2]=2 → swap
  {
    stepNumber: 16,
    codeLine: 5,
    description: 'Compare arr[1]=3 with arr[2]=2',
    variables: { arr: [1, 3, 2, 4, 5], n: 5, i: 2, j: 1 },
    changedVariables: ['j'],
    dataStructure: {
      type: 'array',
      elements: [1, 3, 2, 4, 5],
      highlights: [
        { index: 1, color: 'comparing' },
        { index: 2, color: 'comparing' },
      ],
      sortedIndices: [3, 4],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is arr[1] (3) greater than arr[2] (2)?',
      options: [
        { id: 'yes', label: 'Yes — swap' },
        { id: 'no', label: 'No — skip' },
      ],
      correctId: 'yes',
    },
    explanation: '3 > 2, swap needed.',
    hints: [
      'Is 3 greater than 2?',
      'Yes, 3 > 2.',
      'Yes — swap.',
    ],
  },

  // Step 17: Swap → [1, 2, 3, 4, 5]. Pass 2 done!
  {
    stepNumber: 17,
    codeLine: 6,
    description: 'Swap arr[1] and arr[2]. Pass 2 complete!',
    variables: { arr: [1, 3, 2, 4, 5], n: 5, i: 2, j: 1 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 3, 2, 4, 5],
      highlights: [
        { index: 1, color: 'swapping' },
        { index: 2, color: 'swapping' },
      ],
      sortedIndices: [3, 4],
    },
    prediction: {
      type: 'arrangement',
      prompt: 'Arrange the array after swapping positions 1 and 2.',
      elements: [1, 3, 2, 4, 5],
      correctArrangement: [1, 2, 3, 4, 5],
    },
    explanation: 'Array becomes [1, 2, 3, 4, 5]. The array is now fully sorted!',
    hints: [
      'Swap 3 and 2.',
      '3 and 2 switch places at indices 1 and 2.',
      '[1, 2, 3, 4, 5].',
    ],
  },

  // =================== PASS 3 (i=3): j goes 0..0 ===================

  // Step 18: Compare arr[0]=1 vs arr[1]=2 — NO swap
  {
    stepNumber: 18,
    codeLine: 5,
    description: 'Pass 3: Compare arr[0]=1 with arr[1]=2. No swap — array already sorted!',
    variables: { arr: [1, 2, 3, 4, 5], n: 5, i: 3, j: 0 },
    changedVariables: ['arr', 'i', 'j'],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5],
      highlights: [
        { index: 0, color: 'comparing' },
        { index: 1, color: 'comparing' },
      ],
      sortedIndices: [2, 3, 4],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is arr[0] (1) greater than arr[1] (2)?',
      options: [
        { id: 'yes', label: 'Yes — one more swap' },
        { id: 'no', label: 'No — done!' },
      ],
      correctId: 'no',
    },
    explanation: '1 < 2, no swap. This pass makes no swaps — the array is sorted.',
    hints: [
      'Compare 1 and 2.',
      '1 is not greater than 2.',
      'No — the algorithm is finishing.',
    ],
  },

  // Step 19: Final — return sorted array
  {
    stepNumber: 19,
    codeLine: 7,
    description: 'Return the sorted array [1, 2, 3, 4, 5]',
    variables: { arr: [1, 2, 3, 4, 5], n: 5, i: 3, j: 0 },
    changedVariables: [],
    dataStructure: {
      type: 'array',
      elements: [1, 2, 3, 4, 5],
      highlights: [],
      sortedIndices: [0, 1, 2, 3, 4],
    },
    prediction: null, // auto-advance to completion
    explanation: 'Bubble sort complete! The array [5, 3, 1, 4, 2] is now sorted to [1, 2, 3, 4, 5].',
    hints: ['', '', ''],
  },
];

export const bubbleSortDemo: StateTracerBlueprint = {
  algorithmName: 'Bubble Sort',
  algorithmDescription:
    'Bubble Sort repeatedly compares adjacent elements and swaps them if they are in the wrong order. The largest unsorted element "bubbles" to its correct position each pass.',
  narrativeIntro:
    'Sort these student test scores from lowest to highest using Bubble Sort. Predict what happens at each step — can you trace the algorithm perfectly?',
  code: CODE,
  language: 'python',
  steps,
};
