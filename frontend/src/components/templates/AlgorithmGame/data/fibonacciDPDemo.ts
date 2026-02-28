import { StateTracerBlueprint, ExecutionStep } from '../types';

const CODE = `def fibonacci(n):
    dp = [0] * (n + 1)
    dp[0] = 0
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]

# Example: fibonacci(7) → 13`;

// ============================================================================
// Full execution trace: bottom-up Fibonacci DP for fib(0)..fib(7)
// 11 steps with value predictions, multiple choice, and dependency tracking
// ============================================================================

const steps: ExecutionStep[] = [
  // --- Step 0: Initialize DP table ---
  {
    stepNumber: 0,
    codeLine: 2,
    description: 'Initialize dp table of size n+1 = 8, all values set to 0.',
    variables: { dp: [0, 0, 0, 0, 0, 0, 0, 0], n: 7 },
    changedVariables: ['dp', 'n'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
    },
    prediction: null,
    explanation: 'We create a table with 8 slots (indices 0 through 7), one for each Fibonacci number we need to compute.',
    hints: ['', '', ''],
  },

  // --- Step 1: Base case dp[0] = 0 ---
  {
    stepNumber: 1,
    codeLine: 3,
    description: 'Set base case: dp[0] = 0.',
    variables: { dp: [0, 0, 0, 0, 0, 0, 0, 0], n: 7 },
    changedVariables: ['dp'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'computing' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 0],
    },
    prediction: {
      type: 'value',
      prompt: 'What is fib(0)?',
      correctValue: '0',
      acceptableValues: ['0'],
      placeholder: 'Enter a number',
    },
    explanation: 'The 0th Fibonacci number is defined as 0. This is our first base case.',
    hints: [
      'This is a base case defined by the algorithm.',
      'The Fibonacci sequence starts with 0.',
      'fib(0) = 0.',
    ],
  },

  // --- Step 2: Base case dp[1] = 1 ---
  {
    stepNumber: 2,
    codeLine: 4,
    description: 'Set base case: dp[1] = 1.',
    variables: { dp: [0, 0, 0, 0, 0, 0, 0, 0], n: 7 },
    changedVariables: ['dp'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'filled' },
        { value: 1, state: 'computing' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 1],
    },
    prediction: {
      type: 'value',
      prompt: 'What is fib(1)?',
      correctValue: '1',
      acceptableValues: ['1'],
      placeholder: 'Enter a number',
    },
    explanation: 'The 1st Fibonacci number is defined as 1. This is our second base case.',
    hints: [
      'This is the second base case.',
      'The Fibonacci sequence starts 0, 1, ...',
      'fib(1) = 1.',
    ],
  },

  // --- Step 3: Compute dp[2] = dp[0] + dp[1] = 0 + 1 = 1 ---
  {
    stepNumber: 3,
    codeLine: 6,
    description: 'Compute dp[2] = dp[0] + dp[1] = 0 + 1.',
    variables: { dp: [0, 1, 0, 0, 0, 0, 0, 0], i: 2, n: 7 },
    changedVariables: ['dp', 'i'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'read' },
        { value: 1, state: 'read' },
        { value: 1, state: 'computing' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 2],
      dependencies: [
        { from: [0, 0], to: [0, 2] },
        { from: [0, 1], to: [0, 2] },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What is fib(2) = fib(0) + fib(1)?',
      correctValue: '1',
      acceptableValues: ['1'],
      placeholder: 'Enter a number',
    },
    explanation: 'fib(2) = fib(0) + fib(1) = 0 + 1 = 1. We read the two previous cells and add them.',
    hints: [
      'Look at the two cells that fib(2) depends on.',
      'fib(0) = 0 and fib(1) = 1. Add them together.',
      'fib(2) = 0 + 1 = 1.',
    ],
  },

  // --- Step 4: Ask which cells dp[3] depends on (MC) ---
  {
    stepNumber: 4,
    codeLine: 6,
    description: 'Which cells does dp[3] depend on?',
    variables: { dp: [0, 1, 1, 0, 0, 0, 0, 0], i: 3, n: 7 },
    changedVariables: ['dp', 'i'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: null, state: 'computing' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 3],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Which cells does fib(3) depend on?',
      options: [
        { id: '01', label: 'fib(0) and fib(1)' },
        { id: '12', label: 'fib(1) and fib(2)' },
        { id: '02', label: 'fib(0) and fib(2)' },
      ],
      correctId: '12',
    },
    explanation: 'The recurrence is dp[i] = dp[i-1] + dp[i-2]. For i=3, that means dp[2] and dp[1].',
    hints: [
      'Look at the recurrence formula: dp[i] = dp[i-1] + dp[i-2].',
      'For i=3: dp[3] = dp[2] + dp[1].',
      'fib(3) depends on fib(1) and fib(2).',
    ],
  },

  // --- Step 5: Compute dp[3] = dp[1] + dp[2] = 1 + 1 = 2 ---
  {
    stepNumber: 5,
    codeLine: 6,
    description: 'Compute dp[3] = dp[1] + dp[2] = 1 + 1.',
    variables: { dp: [0, 1, 1, 0, 0, 0, 0, 0], i: 3, n: 7 },
    changedVariables: ['dp'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'filled' },
        { value: 1, state: 'read' },
        { value: 1, state: 'read' },
        { value: 2, state: 'computing' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 3],
      dependencies: [
        { from: [0, 1], to: [0, 3] },
        { from: [0, 2], to: [0, 3] },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What is fib(3)?',
      correctValue: '2',
      acceptableValues: ['2'],
      placeholder: 'Enter a number',
    },
    explanation: 'fib(3) = fib(1) + fib(2) = 1 + 1 = 2.',
    hints: [
      'Add the two dependency cells together.',
      'fib(1) = 1 and fib(2) = 1.',
      'fib(3) = 1 + 1 = 2.',
    ],
  },

  // --- Step 6: Compute dp[4] = dp[2] + dp[3] = 1 + 2 = 3 ---
  {
    stepNumber: 6,
    codeLine: 6,
    description: 'Compute dp[4] = dp[2] + dp[3] = 1 + 2.',
    variables: { dp: [0, 1, 1, 2, 0, 0, 0, 0], i: 4, n: 7 },
    changedVariables: ['dp', 'i'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 1, state: 'read' },
        { value: 2, state: 'read' },
        { value: 3, state: 'computing' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 4],
      dependencies: [
        { from: [0, 2], to: [0, 4] },
        { from: [0, 3], to: [0, 4] },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What is fib(4) = fib(2) + fib(3)?',
      correctValue: '3',
      acceptableValues: ['3'],
      placeholder: 'Enter a number',
    },
    explanation: 'fib(4) = fib(2) + fib(3) = 1 + 2 = 3.',
    hints: [
      'Use the recurrence: dp[4] = dp[3] + dp[2].',
      'fib(2) = 1 and fib(3) = 2.',
      'fib(4) = 1 + 2 = 3.',
    ],
  },

  // --- Step 7: Compute dp[5] = dp[3] + dp[4] = 2 + 3 = 5 ---
  {
    stepNumber: 7,
    codeLine: 6,
    description: 'Compute dp[5] = dp[3] + dp[4] = 2 + 3.',
    variables: { dp: [0, 1, 1, 2, 3, 0, 0, 0], i: 5, n: 7 },
    changedVariables: ['dp', 'i'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 2, state: 'read' },
        { value: 3, state: 'read' },
        { value: 5, state: 'computing' },
        { value: null, state: 'empty' },
        { value: null, state: 'empty' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 5],
      dependencies: [
        { from: [0, 3], to: [0, 5] },
        { from: [0, 4], to: [0, 5] },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What is fib(5)?',
      correctValue: '5',
      acceptableValues: ['5'],
      placeholder: 'Enter a number',
    },
    explanation: 'fib(5) = fib(3) + fib(4) = 2 + 3 = 5.',
    hints: [
      'Add the two previous Fibonacci numbers.',
      'fib(3) = 2 and fib(4) = 3.',
      'fib(5) = 2 + 3 = 5.',
    ],
  },

  // --- Step 8: Compute dp[6] = dp[4] + dp[5] = 3 + 5 = 8 ---
  {
    stepNumber: 8,
    codeLine: 6,
    description: 'Compute dp[6] = dp[4] + dp[5] = 3 + 5.',
    variables: { dp: [0, 1, 1, 2, 3, 5, 0, 0], i: 6, n: 7 },
    changedVariables: ['dp', 'i'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 2, state: 'filled' },
        { value: 3, state: 'read' },
        { value: 5, state: 'read' },
        { value: 8, state: 'computing' },
        { value: null, state: 'empty' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 6],
      dependencies: [
        { from: [0, 4], to: [0, 6] },
        { from: [0, 5], to: [0, 6] },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What is fib(6)?',
      correctValue: '8',
      acceptableValues: ['8'],
      placeholder: 'Enter a number',
    },
    explanation: 'fib(6) = fib(4) + fib(5) = 3 + 5 = 8.',
    hints: [
      'Add the two previous Fibonacci values.',
      'fib(4) = 3 and fib(5) = 5.',
      'fib(6) = 3 + 5 = 8.',
    ],
  },

  // --- Step 9: Compute dp[7] = dp[5] + dp[6] = 5 + 8 = 13 ---
  {
    stepNumber: 9,
    codeLine: 6,
    description: 'Compute dp[7] = dp[5] + dp[6] = 5 + 8.',
    variables: { dp: [0, 1, 1, 2, 3, 5, 8, 0], i: 7, n: 7 },
    changedVariables: ['dp', 'i'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 2, state: 'filled' },
        { value: 3, state: 'filled' },
        { value: 5, state: 'read' },
        { value: 8, state: 'read' },
        { value: 13, state: 'computing' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 7],
      dependencies: [
        { from: [0, 5], to: [0, 7] },
        { from: [0, 6], to: [0, 7] },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What is fib(7)?',
      correctValue: '13',
      acceptableValues: ['13'],
      placeholder: 'Enter a number',
    },
    explanation: 'fib(7) = fib(5) + fib(6) = 5 + 8 = 13.',
    hints: [
      'This is the final computation. Add the two previous values.',
      'fib(5) = 5 and fib(6) = 8.',
      'fib(7) = 5 + 8 = 13.',
    ],
  },

  // --- Step 10: Return result ---
  {
    stepNumber: 10,
    codeLine: 7,
    description: 'Return dp[7] = 13. The complete Fibonacci table is filled.',
    variables: { dp: [0, 1, 1, 2, 3, 5, 8, 13], i: 7, n: 7 },
    changedVariables: ['dp'],
    dataStructure: {
      type: 'dp_table',
      cells: [[
        { value: 0, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 1, state: 'filled' },
        { value: 2, state: 'filled' },
        { value: 3, state: 'filled' },
        { value: 5, state: 'filled' },
        { value: 8, state: 'filled' },
        { value: 13, state: 'optimal' },
      ]],
      colLabels: ['fib(0)', 'fib(1)', 'fib(2)', 'fib(3)', 'fib(4)', 'fib(5)', 'fib(6)', 'fib(7)'],
      activeCell: [0, 7],
    },
    prediction: null,
    explanation: 'The DP table is complete. fibonacci(7) = 13. By building from base cases up, we computed each value exactly once in O(n) time, avoiding the exponential blowup of naive recursion.',
    hints: ['', '', ''],
  },
];

export const fibonacciDPDemo: StateTracerBlueprint = {
  algorithmName: 'Fibonacci (DP)',
  algorithmDescription:
    'Compute Fibonacci numbers using dynamic programming \u2014 build from base cases up.',
  narrativeIntro:
    'Fill the DP table for Fibonacci. Can you predict each value from its dependencies?',
  code: CODE,
  language: 'python',
  steps,
};
