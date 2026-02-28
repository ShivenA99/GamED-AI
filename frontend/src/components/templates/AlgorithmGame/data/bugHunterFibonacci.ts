import { BugHunterBlueprint } from '../types';

export const bugHunterFibonacci: BugHunterBlueprint = {
  algorithmName: 'Fibonacci (Dynamic Programming)',
  algorithmDescription:
    'The Fibonacci sequence is computed using bottom-up dynamic programming. A DP table stores previously computed values so each subproblem is solved only once, achieving O(n) time and space complexity.',
  narrativeIntro:
    'This Fibonacci implementation uses dynamic programming, but it produces wrong results. Two bugs are hiding in the base case and recurrence relation.',
  language: 'python',

  buggyCode: `def fibonacci(n):
    if n <= 0:
        return 0
    if n == 1:
        return 1
    dp = [0] * (n + 1)
    dp[0] = 0
    dp[1] = 2
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] * dp[i - 2]
    return dp[n]`,

  correctCode: `def fibonacci(n):
    if n <= 0:
        return 0
    if n == 1:
        return 1
    dp = [0] * (n + 1)
    dp[0] = 0
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]`,

  bugs: [
    {
      bugId: 'bug-1',
      lineNumber: 8,
      buggyLineText: '    dp[1] = 2',
      correctLineText: '    dp[1] = 1',
      bugType: 'wrong_initialization',
      difficulty: 1,
      explanation:
        'The first Fibonacci number F(1) is 1, not 2. Setting dp[1] = 2 makes every subsequent value wrong because all Fibonacci numbers depend on this base case.',
      bugTypeExplanation:
        'A wrong initialization error sets a variable or array element to an incorrect starting value, causing cascading errors in dependent computations.',
      fixOptions: [
        {
          id: 'fix-1a',
          codeText: '    dp[1] = 2',
          isCorrect: false,
          feedback:
            'F(1) = 2 is wrong. The Fibonacci sequence starts 0, 1, 1, 2, 3, 5... so F(1) = 1.',
        },
        {
          id: 'fix-1b',
          codeText: '    dp[1] = 1',
          isCorrect: true,
          feedback:
            'Correct! F(1) = 1 is the standard Fibonacci base case.',
        },
        {
          id: 'fix-1c',
          codeText: '    dp[1] = 0',
          isCorrect: false,
          feedback:
            'F(1) = 0 would make dp[1] = dp[0] = 0, and all subsequent values would be 0.',
        },
        {
          id: 'fix-1d',
          codeText: '    dp[1] = -1',
          isCorrect: false,
          feedback:
            'Fibonacci numbers are non-negative. F(1) = -1 has no mathematical basis.',
        },
      ],
      hints: [
        'This is a wrong initialization error \u2014 a base case value is incorrect.',
        'The bug is in the base case setup (lines 7-8).',
        'Line 8 sets dp[1] to the wrong value. What is F(1)?',
      ],
    },
    {
      bugId: 'bug-2',
      lineNumber: 10,
      buggyLineText: '        dp[i] = dp[i - 1] * dp[i - 2]',
      correctLineText: '        dp[i] = dp[i - 1] + dp[i - 2]',
      bugType: 'wrong_operator',
      difficulty: 2,
      explanation:
        'The Fibonacci recurrence is F(n) = F(n-1) + F(n-2), using addition. Multiplication produces an entirely different (much faster growing) sequence.',
      bugTypeExplanation:
        'A wrong operator error uses an incorrect arithmetic or comparison operator, fundamentally changing the computation.',
      fixOptions: [
        {
          id: 'fix-2a',
          codeText: '        dp[i] = dp[i - 1] * dp[i - 2]',
          isCorrect: false,
          feedback:
            'Multiplication grows exponentially faster than addition. F(5) would be 0 (due to dp[0]=0) instead of 5.',
        },
        {
          id: 'fix-2b',
          codeText: '        dp[i] = dp[i - 1] + dp[i - 2]',
          isCorrect: true,
          feedback:
            'Correct! The Fibonacci recurrence uses addition: F(n) = F(n-1) + F(n-2).',
        },
        {
          id: 'fix-2c',
          codeText: '        dp[i] = dp[i - 1] - dp[i - 2]',
          isCorrect: false,
          feedback:
            'Subtraction would produce alternating values: 0, 1, 1, 0, 1, -1, ... \u2014 not Fibonacci.',
        },
        {
          id: 'fix-2d',
          codeText: '        dp[i] = dp[i - 1] ** dp[i - 2]',
          isCorrect: false,
          feedback:
            'Exponentiation would produce astronomically large numbers. This has no relation to Fibonacci.',
        },
      ],
      hints: [
        'This is a wrong operator error \u2014 the arithmetic operation is incorrect.',
        'The bug is in the recurrence relation (lines 9-10).',
        'Line 10 uses the wrong arithmetic operator. The Fibonacci recurrence uses addition.',
      ],
    },
  ],

  testCases: [
    {
      id: 'test-1',
      inputDescription: 'n = 6',
      expectedOutput: '8',
      buggyOutput: '0',
      exposedBugs: ['bug-1', 'bug-2'],
    },
    {
      id: 'test-2',
      inputDescription: 'n = 1',
      expectedOutput: '1',
      buggyOutput: '1',
      exposedBugs: [],
    },
    {
      id: 'test-3',
      inputDescription: 'n = 5',
      expectedOutput: '5',
      buggyOutput: '0',
      exposedBugs: ['bug-1', 'bug-2'],
    },
  ],

  redHerrings: [
    {
      lineNumber: 6,
      feedback:
        'Initializing the DP table with zeros and size n+1 is correct. We need indices 0 through n.',
    },
    {
      lineNumber: 9,
      feedback:
        'Starting from index 2 and going up to n (inclusive) is the correct loop range for bottom-up Fibonacci.',
    },
  ],

  config: {
    revealSequentially: true,
    showTestOutput: true,
    showRunButton: false,
    fixMode: 'multiple_choice',
    maxWrongLineClicks: 10,
  },
};
