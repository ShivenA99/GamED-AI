import { ConstraintPuzzleBlueprint } from '../types';

export const constraintPuzzleKnapsack: ConstraintPuzzleBlueprint = {
  puzzleType: 'knapsack',
  title: 'Camping Trip Packing',
  narrative:
    'You are packing for a camping trip with a weight limit on your backpack. Each item has a weight and a value (how useful it is). Maximize the total value without exceeding the weight capacity!',
  rules: [
    'Your backpack can hold at most 15 kg',
    'Each item can be taken at most once',
    'Maximize the total value of items you pack',
    'You cannot exceed the weight limit',
  ],
  objective: 'Pack the most valuable combination of items within 15 kg',
  puzzleData: {
    type: 'knapsack',
    capacity: 15,
    items: [
      { id: 'tent', name: 'Tent', weight: 7, value: 10, icon: '\u26FA' },
      { id: 'sleeping-bag', name: 'Sleeping Bag', weight: 5, value: 8, icon: '\u{1F6CF}' },
      { id: 'stove', name: 'Camp Stove', weight: 3, value: 6, icon: '\u{1F525}' },
      { id: 'water', name: 'Water Filter', weight: 2, value: 7, icon: '\u{1F4A7}' },
      { id: 'food', name: 'Food Pack', weight: 4, value: 5, icon: '\u{1F35E}' },
      { id: 'first-aid', name: 'First Aid Kit', weight: 1, value: 4, icon: '\u{1FA79}' },
      { id: 'lantern', name: 'Lantern', weight: 3, value: 3, icon: '\u{1F4A1}' },
      { id: 'chair', name: 'Folding Chair', weight: 6, value: 2, icon: '\u{1FA91}' },
    ],
  },
  optimalValue: 30, // tent(10) + sleeping_bag(8) + water(7) + stove(6) = 31... let me recalculate
  // tent(7kg,10v) + water(2kg,7v) + stove(3kg,6v) + first_aid(1kg,4v) = 13kg, 27v
  // sleeping_bag(5kg,8v) + water(2kg,7v) + stove(3kg,6v) + food(4kg,5v) + first_aid(1kg,4v) = 15kg, 30v
  optimalSolutionDescription:
    'Take Sleeping Bag (8), Water Filter (7), Camp Stove (6), Food Pack (5), and First Aid Kit (4) = 30 value at exactly 15 kg. The DP approach fills a table[item][weight] and backtracks to find the optimal set.',
  algorithmName: '0/1 Knapsack (Dynamic Programming)',
  algorithmExplanation:
    'The 0/1 Knapsack problem is solved optimally using Dynamic Programming. Build a 2D table dp[i][w] where i = items considered and w = remaining capacity. For each item, choose the maximum of: (1) not including it (dp[i-1][w]) or (2) including it (dp[i-1][w-weight] + value). The optimal value is dp[n][W]. Backtrack through the table to find which items were selected. Time complexity: O(n \u00D7 W) where n = items, W = capacity.',
  showConstraintsVisually: true,
  showOptimalityScore: true,
  allowUndo: true,
  hints: [
    'Think about value-to-weight ratio: which items give the most value per kg?',
    'Water Filter has the best ratio (7 value / 2 kg = 3.5). First Aid Kit is next (4/1 = 4.0).',
    'Optimal: Sleeping Bag + Water Filter + Stove + Food + First Aid = 30 value, 15 kg.',
  ],
};
