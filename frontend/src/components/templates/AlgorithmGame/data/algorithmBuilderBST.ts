import { AlgorithmBuilderBlueprint } from '../types';

export const algorithmBuilderBST: AlgorithmBuilderBlueprint = {
  algorithmName: 'BST Insert',
  algorithmDescription:
    'Inserting a value into a Binary Search Tree by recursively traversing left (smaller) or right (larger) until finding an empty spot. O(h) time where h is tree height.',
  problemDescription:
    'Build a recursive function that inserts a new value into a BST, maintaining the BST property (left < node < right).',
  language: 'python',

  correct_order: [
    { id: 'bst-1', code: 'def insert(node, val):', indent_level: 0, is_distractor: false },
    { id: 'bst-2', code: 'if node is None:', indent_level: 1, is_distractor: false },
    { id: 'bst-3', code: 'return TreeNode(val)', indent_level: 2, is_distractor: false },
    { id: 'bst-4', code: 'if val < node.val:', indent_level: 1, is_distractor: false },
    { id: 'bst-5', code: 'node.left = insert(node.left, val)', indent_level: 2, is_distractor: false },
    { id: 'bst-6', code: 'elif val > node.val:', indent_level: 1, is_distractor: false },
    { id: 'bst-7', code: 'node.right = insert(node.right, val)', indent_level: 2, is_distractor: false },
    { id: 'bst-8', code: 'return node', indent_level: 1, is_distractor: false },
  ],

  distractors: [
    {
      id: 'bst-d1',
      code: 'node.left = insert(node.right, val)',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'This assigns the right subtree\'s result to the left child. When val < node.val, we must recurse into node.left, not node.right.',
    },
    {
      id: 'bst-d2',
      code: 'if val > node.val:',
      indent_level: 1,
      is_distractor: true,
      distractor_explanation:
        'This duplicates the greater-than check. After the less-than check, we need elif val > node.val (not another if), to handle the case where val equals node.val (skip insertion of duplicates).',
    },
  ],

  config: {
    indentation_matters: true,
    max_attempts: null,
    show_line_numbers: true,
    allow_indent_adjustment: true,
  },

  hints: [
    'Start with the base case: if the node is None, create and return a new TreeNode.',
    'Compare val to node.val: go left if smaller, right if larger. The recursive call\'s return value must be assigned back to node.left or node.right.',
    'Order: def \u2192 if None: return new node \u2192 if val < node.val: node.left = recurse left \u2192 elif val > node.val: node.right = recurse right \u2192 return node.',
  ],

  test_cases: [
    { id: 'bst-t1', inputDescription: 'Insert 5 into empty tree', expectedOutput: 'Tree with root = 5' },
    { id: 'bst-t2', inputDescription: 'Insert 3 into tree [5]', expectedOutput: 'Tree: 5 -> left: 3' },
  ],
};
