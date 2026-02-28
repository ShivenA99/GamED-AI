import { ComplexityAnalyzerBlueprint } from '../types';

export const complexityAnalyzerBST: ComplexityAnalyzerBlueprint = {
  algorithmName: 'BST Insert',
  algorithmDescription:
    'Analyze the time complexity of inserting into a binary search tree — best, worst, and average cases.',
  challenges: [
    {
      challengeId: 'ca-bst-1',
      type: 'identify_from_code',
      title: 'BST Insert — Average Case',
      description: 'Determine the average-case time complexity for a balanced BST.',
      code: `class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

def insert(root, val):
    if root is None:
        return TreeNode(val)
    if val < root.val:
        root.left = insert(root.left, val)
    else:
        root.right = insert(root.right, val)
    return root`,
      language: 'python',
      correctComplexity: 'O(log n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)'],
      explanation:
        'In a balanced BST, each recursive call goes one level deeper (left or right). The tree height is log\u2082(n) for n nodes. So insertion traverses at most log(n) levels = O(log n).',
      points: 100,
      hints: [
        'Think about the height of a balanced binary tree.',
        'A balanced BST with n nodes has height \u2248 log\u2082(n).',
        'Insert traverses root to leaf = O(height) = O(log n) for balanced trees.',
      ],
    },
    {
      challengeId: 'ca-bst-2',
      type: 'identify_from_code',
      title: 'BST Insert — Worst Case (Skewed)',
      description: 'What if elements are inserted in sorted order (creating a skewed tree)?',
      code: `# Inserting 1, 2, 3, 4, 5 in order:
#    1
#     \\
#      2
#       \\
#        3
#         \\
#          4
#           \\
#            5

def insert(root, val):
    if root is None:
        return TreeNode(val)
    if val < root.val:
        root.left = insert(root.left, val)
    else:
        root.right = insert(root.right, val)
    return root`,
      language: 'python',
      correctComplexity: 'O(n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n\u00B2)'],
      explanation:
        'When elements are inserted in sorted order, the BST degenerates into a linked list (all right children). The height becomes n, so insertion must traverse all n nodes = O(n).',
      points: 100,
      hints: [
        'What does the tree look like after inserting 1, 2, 3, 4, 5 in order?',
        'It becomes a straight line (linked list). The height = n.',
        'Traversing a linked list of n nodes = O(n).',
      ],
    },
    {
      challengeId: 'ca-bst-3',
      type: 'infer_from_growth',
      title: 'BST Insert — Balanced Case Growth',
      description: 'Comparisons per insert for balanced BSTs of various sizes.',
      growthData: {
        inputSizes: [7, 15, 31, 63, 127, 255],
        operationCounts: [3, 4, 5, 6, 7, 8],
      },
      correctComplexity: 'O(log n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n\u00B2)'],
      explanation:
        'The sizes are 2\u00B3-1, 2\u2074-1, ..., 2\u2078-1 (perfect binary trees). The comparison counts are exactly 3, 4, ..., 8 = log\u2082(n+1). This is textbook O(log n).',
      points: 100,
      hints: [
        'Notice the input sizes: 7, 15, 31, ... these are 2^k - 1.',
        'When n doubles (roughly), comparisons increase by just 1.',
        '+1 comparison per doubling of n = O(log n).',
      ],
    },
  ],
};
