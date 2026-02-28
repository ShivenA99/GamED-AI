import { CombinedPuzzleBlueprint } from '../algorithmChallenge/combinedPuzzleTypes';

export const combinedPuzzleKnapsack: CombinedPuzzleBlueprint = {
  title: '0/1 Knapsack — Code + Puzzle',
  description:
    'Implement the dynamic programming solution AND manually select the best items for your knapsack.',
  icon: '\u{1F392}',

  // ─── Puzzle Side ───────────────────────────────────────────────────
  puzzleBlueprint: {
    title: 'Knapsack Packing',
    narrative:
      'You have a backpack with limited capacity. Choose items to maximize total value without exceeding the weight limit.',
    rules: [
      'Total weight must not exceed 15 kg.',
      'Each item can be taken at most once.',
      'Goal: maximize total value.',
    ],
    objective: 'Select items to maximize value within 15 kg capacity.',
    boardConfig: {
      boardType: 'item_selection',
      items: [
        { id: 'water', label: 'Water Bottle', properties: { weight: 3, value: 4 }, icon: '\u{1F4A7}' },
        { id: 'food', label: 'Food Pack', properties: { weight: 5, value: 7 }, icon: '\u{1F35E}' },
        { id: 'tent', label: 'Tent', properties: { weight: 8, value: 9 }, icon: '\u26FA' },
        { id: 'stove', label: 'Camp Stove', properties: { weight: 4, value: 6 }, icon: '\u{1F525}' },
        { id: 'rope', label: 'Rope', properties: { weight: 2, value: 3 }, icon: '\u{1FA22}' },
        { id: 'map', label: 'Map & Compass', properties: { weight: 1, value: 2 }, icon: '\u{1F5FA}' },
      ],
      displayColumns: ['weight', 'value'],
      propertyLabels: { weight: 'Weight (kg)', value: 'Value' },
    },
    constraints: [
      { type: 'capacity', property: 'weight', max: 15, label: 'Weight', showBar: true },
    ],
    scoringConfig: { method: 'sum_property', property: 'value' },
    optimalValue: 22,
    optimalSolutionDescription:
      'Take Food (5kg, $7) + Tent (8kg, $9) + Stove (4kg, $6) = 15kg, $22 — no capacity wasted.',
    algorithmName: '0/1 Knapsack (Dynamic Programming)',
    algorithmExplanation:
      'Build a DP table where dp[i][w] = max value using items 1..i with capacity w. For each item, decide to include or skip. Time: O(n*W), Space: O(n*W).',
    showConstraintsVisually: true,
    allowUndo: true,
    hints: [
      'Think about which combination of items gives the best value-to-weight ratio.',
      'The tent is heavy but valuable. Can you fit it with other items?',
      'Optimal: food + tent + stove = 15kg, $22.',
    ],
  },

  // ─── Code Side ─────────────────────────────────────────────────────
  algorithmChallenge: {
    mode: 'parsons',
    language: 'python',
    solutionCode: `def knapsack(items, capacity):
    n = len(items)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        w, v = items[i - 1]
        for c in range(capacity + 1):
            dp[i][c] = dp[i - 1][c]
            if c >= w:
                dp[i][c] = max(dp[i][c], dp[i - 1][c - w] + v)
    result = []
    c = capacity
    for i in range(n, 0, -1):
        if dp[i][c] != dp[i - 1][c]:
            result.append(i - 1)
            c -= items[i - 1][0]
    return sorted(result)`,
    correctOrder: [
      { id: 'k1', code: 'def knapsack(items, capacity):', indent_level: 0, is_distractor: false },
      { id: 'k2', code: 'n = len(items)', indent_level: 1, is_distractor: false },
      { id: 'k3', code: 'dp = [[0] * (capacity + 1) for _ in range(n + 1)]', indent_level: 1, is_distractor: false },
      { id: 'k4', code: 'for i in range(1, n + 1):', indent_level: 1, is_distractor: false },
      { id: 'k5', code: 'w, v = items[i - 1]', indent_level: 2, is_distractor: false },
      { id: 'k6', code: 'for c in range(capacity + 1):', indent_level: 2, is_distractor: false },
      { id: 'k7', code: 'dp[i][c] = dp[i - 1][c]', indent_level: 3, is_distractor: false },
      { id: 'k8', code: 'if c >= w:', indent_level: 3, is_distractor: false },
      { id: 'k9', code: 'dp[i][c] = max(dp[i][c], dp[i - 1][c - w] + v)', indent_level: 3, is_distractor: false },
      { id: 'k10', code: 'result = []', indent_level: 1, is_distractor: false },
      { id: 'k11', code: 'c = capacity', indent_level: 1, is_distractor: false },
      { id: 'k12', code: 'for i in range(n, 0, -1):', indent_level: 1, is_distractor: false },
      { id: 'k13', code: 'if dp[i][c] != dp[i - 1][c]:', indent_level: 2, is_distractor: false },
      { id: 'k14', code: 'result.append(i - 1)', indent_level: 3, is_distractor: false },
      { id: 'k15', code: 'c -= items[i - 1][0]', indent_level: 3, is_distractor: false },
      { id: 'k16', code: 'return sorted(result)', indent_level: 1, is_distractor: false },
    ],
    distractors: [
      { id: 'd1', code: 'dp[i][c] = dp[i - 1][c] + v', indent_level: 3, is_distractor: true, distractor_explanation: 'Adding value without checking capacity violates the knapsack constraint.' },
      { id: 'd2', code: 'for c in range(w, capacity + 1):', indent_level: 2, is_distractor: true, distractor_explanation: 'This range skip is for the space-optimized 1D version, not the 2D traceback version.' },
    ],
    parsonsConfig: {
      indentation_matters: true,
      max_attempts: null,
      show_line_numbers: true,
      allow_indent_adjustment: true,
    },
    testCases: [
      {
        id: 'tc-puzzle',
        label: 'Puzzle case (same items)',
        setupCode: `items = [(3,4), (5,7), (8,9), (4,6), (2,3), (1,2)]\nnames = ['water','food','tent','stove','rope','map']`,
        callCode: 'result = knapsack(items, 15)',
        printCode: 'print(",".join(sorted([names[i] for i in result])))',
        expectedOutput: 'food,stove,tent',
        isPuzzleCase: true,
      },
      {
        id: 'tc-small',
        label: 'Small case',
        setupCode: 'items = [(2, 3), (3, 4), (4, 5)]',
        callCode: 'result = knapsack(items, 5)',
        printCode: 'print(sorted(result))',
        expectedOutput: '[0, 1]',
        isPuzzleCase: false,
      },
      {
        id: 'tc-empty',
        label: 'Zero capacity',
        setupCode: 'items = [(1, 10), (2, 20)]',
        callCode: 'result = knapsack(items, 0)',
        printCode: 'print(sorted(result))',
        expectedOutput: '[]',
        isPuzzleCase: false,
      },
    ],
    outputFormat: 'list_of_ids',
    hints: [
      'The DP table has dimensions (n+1) x (capacity+1).',
      'For each item, copy the value from the row above, then check if including it is better.',
      'Traceback: if dp[i][c] differs from dp[i-1][c], item i-1 was included.',
    ],
  },
};
