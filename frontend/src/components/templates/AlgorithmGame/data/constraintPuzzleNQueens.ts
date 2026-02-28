import { ConstraintPuzzleBlueprint } from '../types';

export const constraintPuzzleNQueens: ConstraintPuzzleBlueprint = {
  puzzleType: 'n_queens',
  title: '6-Queens Challenge',
  narrative:
    'Place 6 queens on a 6x6 chessboard so that no two queens threaten each other. Queens can attack along rows, columns, and diagonals.',
  rules: [
    'Place exactly 6 queens on the 6x6 board',
    'No two queens can share the same row',
    'No two queens can share the same column',
    'No two queens can share the same diagonal',
  ],
  objective: 'Place all 6 queens with no conflicts',
  puzzleData: {
    type: 'n_queens',
    boardSize: 6,
  },
  optimalValue: 6,
  optimalSolutionDescription:
    'One valid solution: (0,1), (1,3), (2,5), (3,0), (4,2), (5,4). There are 4 distinct solutions for the 6-Queens problem (not counting rotations/reflections).',
  algorithmName: 'Backtracking',
  algorithmExplanation:
    'The N-Queens problem is classically solved with Backtracking. Place queens column by column. For each column, try each row. If placing a queen creates no conflict, move to the next column. If all rows conflict, backtrack to the previous column and try the next row. This prunes invalid branches early. Time complexity: O(N!) in the worst case, but pruning makes it much faster in practice. For N=6, only 4 valid solutions exist out of 46,656 possible placements.',
  showConstraintsVisually: true,
  showOptimalityScore: false,
  allowUndo: true,
  hints: [
    'Start from the corners or edges where there are fewer diagonal conflicts.',
    'Try placing queens in a staircase pattern, avoiding adjacent rows/columns.',
    'One solution: row 1 col 2, row 2 col 4, row 3 col 6, row 4 col 1, row 5 col 3, row 6 col 5 (1-indexed).',
  ],
};
