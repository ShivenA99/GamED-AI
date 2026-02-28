import { AlgorithmBuilderBlueprint } from '../types';

export const algorithmBuilderFibonacci: AlgorithmBuilderBlueprint = {
  algorithmName: 'Fibonacci (Dynamic Programming)',
  algorithmDescription:
    'Computing Fibonacci numbers using bottom-up dynamic programming avoids redundant computation, running in O(n) time and O(n) space.',
  problemDescription:
    'Build a function that computes the nth Fibonacci number using bottom-up dynamic programming with a DP table.',
  language: 'python',

  correct_order: [
    { id: 'fib-1', code: 'def fibonacci(n):', indent_level: 0, is_distractor: false },
    { id: 'fib-2', code: 'if n <= 1:', indent_level: 1, is_distractor: false },
    { id: 'fib-3', code: 'return n', indent_level: 2, is_distractor: false },
    { id: 'fib-4', code: 'dp = [0] * (n + 1)', indent_level: 1, is_distractor: false },
    { id: 'fib-5', code: 'dp[0] = 0', indent_level: 1, is_distractor: false },
    { id: 'fib-6', code: 'dp[1] = 1', indent_level: 1, is_distractor: false },
    { id: 'fib-7', code: 'for i in range(2, n + 1):', indent_level: 1, is_distractor: false },
    { id: 'fib-8', code: 'dp[i] = dp[i - 1] + dp[i - 2]', indent_level: 2, is_distractor: false },
    { id: 'fib-9', code: 'return dp[n]', indent_level: 1, is_distractor: false },
  ],

  distractors: [
    {
      id: 'fib-d1',
      code: 'dp[i] = dp[i - 1] * dp[i - 2]',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'Fibonacci uses addition (dp[i-1] + dp[i-2]), not multiplication. Multiplying would give a completely different sequence.',
    },
    {
      id: 'fib-d2',
      code: 'for i in range(n):',
      indent_level: 1,
      is_distractor: true,
      distractor_explanation:
        'range(n) starts from 0, but dp[0] and dp[1] are base cases. The loop must start from 2: range(2, n+1).',
    },
  ],

  config: {
    indentation_matters: true,
    max_attempts: null,
    show_line_numbers: true,
    allow_indent_adjustment: true,
  },

  hints: [
    'Start with the base case check, then set up the DP table before the loop.',
    'The DP table is initialized with zeros, then base cases dp[0]=0 and dp[1]=1 are set before the loop.',
    'Order: def \u2192 base case (n<=1) \u2192 dp table init \u2192 dp[0]=0, dp[1]=1 \u2192 for i in range(2,n+1) \u2192 dp[i] = dp[i-1]+dp[i-2] \u2192 return dp[n].',
  ],

  test_cases: [
    { id: 'fib-t1', inputDescription: 'n = 0', expectedOutput: '0' },
    { id: 'fib-t2', inputDescription: 'n = 1', expectedOutput: '1' },
    { id: 'fib-t3', inputDescription: 'n = 10', expectedOutput: '55' },
  ],
};
