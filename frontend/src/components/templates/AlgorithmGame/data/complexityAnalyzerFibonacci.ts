import { ComplexityAnalyzerBlueprint } from '../types';

export const complexityAnalyzerFibonacci: ComplexityAnalyzerBlueprint = {
  algorithmName: 'Fibonacci (DP)',
  algorithmDescription:
    'Compare the time complexity of naive recursive Fibonacci vs dynamic programming approach.',
  challenges: [
    {
      challengeId: 'ca-fib-1',
      type: 'identify_from_code',
      title: 'Naive Recursive Fibonacci',
      description: 'What is the time complexity of this recursive implementation?',
      code: `def fib_recursive(n):
    if n <= 1:
        return n
    return fib_recursive(n - 1) + fib_recursive(n - 2)`,
      language: 'python',
      correctComplexity: 'O(2\u207F)',
      options: ['O(n)', 'O(n\u00B2)', 'O(2\u207F)', 'O(n!)'],
      explanation:
        'Each call branches into two recursive calls. The recursion tree has depth n and roughly doubles at each level. This gives approximately 2\u207F total calls. More precisely it is O(\u03C6\u207F) where \u03C6 \u2248 1.618 (golden ratio), but we simplify to O(2\u207F).',
      points: 100,
      hints: [
        'Draw the recursion tree: fib(5) calls fib(4) and fib(3), each of which calls two more...',
        'The tree has depth n and each level roughly doubles the number of calls.',
        'Doubling at each of n levels = 2\u207F total calls.',
      ],
    },
    {
      challengeId: 'ca-fib-2',
      type: 'identify_from_code',
      title: 'DP Fibonacci',
      description: 'Now analyze the dynamic programming version.',
      code: `def fib_dp(n):
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[0], dp[1] = 0, 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]`,
      language: 'python',
      correctComplexity: 'O(n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n\u00B2)'],
      explanation:
        'The DP version uses a single loop from 2 to n, computing each value in O(1) with a table lookup. Total: n-1 iterations = O(n). This is an exponential improvement over the naive recursive version.',
      points: 100,
      hints: [
        'Count the number of loop iterations.',
        'The for loop runs from 2 to n+1, so n-1 iterations.',
        'Each iteration does constant work (one addition, two lookups) = O(n) total.',
      ],
    },
    {
      challengeId: 'ca-fib-3',
      type: 'infer_from_growth',
      title: 'Naive Fibonacci — Growth Explosion',
      description: 'These are function call counts for the naive recursive Fibonacci. What is the pattern?',
      growthData: {
        inputSizes: [5, 10, 15, 20, 25, 30],
        operationCounts: [15, 177, 1973, 21891, 242785, 2692537],
      },
      correctComplexity: 'O(2\u207F)',
      options: ['O(n\u00B2)', 'O(n\u00B3)', 'O(2\u207F)', 'O(n!)'],
      explanation:
        'Each increment of 5 in n multiplies calls by roughly 11x (close to 2\u2075 = 32 but the base is \u03C6 \u2248 1.618, so \u03C6\u2075 \u2248 11.1). This explosive growth is the hallmark of exponential complexity O(2\u207F).',
      points: 100,
      hints: [
        'Look at the ratio between consecutive entries.',
        '177/15 \u2248 11.8, 1973/177 \u2248 11.1, 21891/1973 \u2248 11.1 \u2014 roughly constant multiplicative growth per +5 in n.',
        'Constant multiplicative growth per unit increase in n = exponential = O(2\u207F).',
      ],
    },
  ],
};
