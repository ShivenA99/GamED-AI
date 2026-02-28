import { BugHunterBlueprint } from '../types';

export const bugHunterBST: BugHunterBlueprint = {
  algorithmName: 'BST Insert',
  algorithmDescription:
    'BST insertion places a new value into a binary search tree by recursively comparing the value against each node: values less than the node go left, values greater go right. When a null position is found, a new node is created. This maintains the BST invariant (left < parent < right) and runs in O(h) time where h is the tree height.',
  narrativeIntro:
    'This BST insert function builds a tree incorrectly. Two bugs in the comparison and return logic need fixing.',
  language: 'python',

  buggyCode: `def bst_insert(root, value):
    if root is None:
        return TreeNode(value)
    if value > root.val:
        root.left = bst_insert(root.left, value)
    else:
        root.right = bst_insert(root.right, value)
    return value`,

  correctCode: `def bst_insert(root, value):
    if root is None:
        return TreeNode(value)
    if value < root.val:
        root.left = bst_insert(root.left, value)
    else:
        root.right = bst_insert(root.right, value)
    return root`,

  bugs: [
    {
      bugId: 'bug-1',
      lineNumber: 4,
      buggyLineText: '    if value > root.val:',
      correctLineText: '    if value < root.val:',
      bugType: 'wrong_operator',
      difficulty: 2,
      explanation:
        'In a BST, values less than the current node go LEFT. Using > sends larger values left, which violates the BST property and builds an inverted tree.',
      bugTypeExplanation:
        'A wrong operator error uses an incorrect comparison operator, reversing the intended logic of a conditional.',
      fixOptions: [
        {
          id: 'fix-1a',
          codeText: '    if value > root.val:',
          isCorrect: false,
          feedback:
            'This sends values greater than root to the left subtree, violating the BST property where left < parent < right.',
        },
        {
          id: 'fix-1b',
          codeText: '    if value < root.val:',
          isCorrect: true,
          feedback:
            'Correct! Values less than root.val belong in the left subtree, maintaining the BST invariant.',
        },
        {
          id: 'fix-1c',
          codeText: '    if value >= root.val:',
          isCorrect: false,
          feedback:
            'Using >= still sends larger values left. Also, equal values going left instead of right is a design choice but the direction is still wrong.',
        },
        {
          id: 'fix-1d',
          codeText: '    if value == root.val:',
          isCorrect: false,
          feedback:
            'This would only go left for duplicates, sending all other values right regardless of comparison.',
        },
      ],
      hints: [
        'This is a wrong operator error \u2014 the comparison direction is reversed.',
        'The bug is in the BST comparison logic (lines 4-5).',
        'Line 4 uses > but BST insertion goes left for values LESS than the current node.',
      ],
    },
    {
      bugId: 'bug-2',
      lineNumber: 8,
      buggyLineText: '    return value',
      correctLineText: '    return root',
      bugType: 'wrong_return',
      difficulty: 2,
      explanation:
        'The function should return the root of the (sub)tree after insertion. Returning value (a number) instead of root (a TreeNode) breaks the recursive tree construction \u2014 parent nodes lose their subtree references.',
      bugTypeExplanation:
        'A wrong return error returns the wrong value from a function, often returning raw data instead of the correct data structure.',
      fixOptions: [
        {
          id: 'fix-2a',
          codeText: '    return value',
          isCorrect: false,
          feedback:
            'Returning the raw value loses the tree structure. Parent nodes calling bst_insert need the TreeNode back to maintain links.',
        },
        {
          id: 'fix-2b',
          codeText: '    return root',
          isCorrect: true,
          feedback:
            "Correct! Returning root preserves the tree structure so the parent node's left/right assignment works correctly.",
        },
        {
          id: 'fix-2c',
          codeText: '    return None',
          isCorrect: false,
          feedback:
            'Returning None would disconnect every subtree, leaving only the newly created leaf nodes.',
        },
        {
          id: 'fix-2d',
          codeText: '    return TreeNode(value)',
          isCorrect: false,
          feedback:
            'Creating a new node every time would replace existing subtrees with single-node trees.',
        },
      ],
      hints: [
        'This is a wrong return error \u2014 the function returns the wrong thing.',
        'The bug is in the return statement (line 8).',
        'Line 8 returns value (a number) instead of the tree node.',
      ],
    },
  ],

  testCases: [
    {
      id: 'test-1',
      inputDescription: 'Insert 5, 3, 7, 1 into empty BST',
      expectedOutput: 'BST: 5(left:3(left:1), right:7)',
      buggyOutput: 'TypeError / broken tree',
      exposedBugs: ['bug-1', 'bug-2'],
    },
    {
      id: 'test-2',
      inputDescription: 'Insert 10 into BST with root 5',
      expectedOutput: '5(right:10)',
      buggyOutput: '5(left:10) / wrong type',
      exposedBugs: ['bug-1', 'bug-2'],
    },
  ],

  redHerrings: [
    {
      lineNumber: 2,
      feedback:
        'Checking for None correctly handles the base case \u2014 when we\'ve found the insertion point, we create and return a new node.',
    },
    {
      lineNumber: 5,
      feedback:
        'Recursively inserting into the left subtree and reassigning root.left is the correct pattern for BST insertion.',
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
