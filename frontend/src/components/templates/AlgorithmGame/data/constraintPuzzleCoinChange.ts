import { ConstraintPuzzleBlueprint } from '../types';

export const constraintPuzzleCoinChange: ConstraintPuzzleBlueprint = {
  puzzleType: 'coin_change',
  title: 'Exact Change Challenge',
  narrative:
    'You need to make exact change for a purchase. Using the available coin denominations, make exactly the target amount using the fewest coins possible!',
  rules: [
    'Make exactly the target amount (no more, no less)',
    'You can use each denomination as many times as needed',
    'Use the fewest coins possible for the best score',
    'Click a coin to add it; click a selected coin to remove it',
  ],
  objective: 'Make exactly 36 cents using the fewest coins',
  puzzleData: {
    type: 'coin_change',
    targetAmount: 36,
    denominations: [1, 5, 10, 25],
  },
  optimalValue: 3, // Using fewest coins: 25 + 10 + 1 = 36 (3 coins)
  optimalSolutionDescription:
    'Optimal: 25 + 10 + 1 = 36 using just 3 coins. The greedy approach (always pick the largest coin that fits) works for standard US denominations but not for all denomination sets.',
  algorithmName: 'Coin Change (Dynamic Programming)',
  algorithmExplanation:
    'The Coin Change problem finds the minimum number of coins to make a target amount. Build a DP array dp[0..amount] where dp[i] = minimum coins to make amount i. Initialize dp[0]=0, all others = infinity. For each amount i from 1 to target, for each coin c: if c <= i, dp[i] = min(dp[i], dp[i-c] + 1). The answer is dp[target]. Time: O(amount \u00D7 coins). Note: Greedy works for US coins but not for arbitrary denominations (e.g., coins = [1, 3, 4], amount = 6: greedy gives 4+1+1=3 coins, DP gives 3+3=2 coins).',
  showConstraintsVisually: true,
  showOptimalityScore: true,
  allowUndo: true,
  hints: [
    'Start with the largest coin that does not exceed the remaining amount.',
    'Use the 25-cent coin first. Then look at what is left.',
    'Optimal: one 25-cent + one 10-cent + one 1-cent = 36 cents, 3 coins total.',
  ],
};
