import { StateTracerBlueprint, ExecutionStep } from '../types';

const CODE = `class Node:
    def __init__(self, val):
        self.val = val
        self.left = self.right = None

def insert(root, val):
    if root is None:
        return Node(val)
    if val < root.val:
        root.left = insert(root.left, val)
    else:
        root.right = insert(root.right, val)
    return root

# Insert: 8, 3, 10, 1, 6, 14`;

// ============================================================================
// Full execution trace: BST insert of [8, 3, 10, 1, 6, 14]
// 12 steps building the tree progressively with mixed prediction types
// ============================================================================

const steps: ExecutionStep[] = [
  // --- Step 0: Insert 8 as root (auto-advance) ---
  {
    stepNumber: 0,
    codeLine: 9,
    description: 'Insert 8 into an empty tree. Since root is None, 8 becomes the root node.',
    variables: { inserting: 8, comparing_with: null, direction: null },
    changedVariables: ['inserting'],
    dataStructure: {
      type: 'tree',
      nodes: [{ id: 'n8', value: 8, state: 'inserted' }],
      root: 'n8',
    },
    prediction: null, // auto-advance
    explanation:
      'The tree is empty (root is None), so we create a new Node with value 8 and it becomes the root.',
    hints: ['', '', ''],
  },

  // --- Step 1: Insert 3 — compare with 8 ---
  {
    stepNumber: 1,
    codeLine: 10,
    description: 'Insert 3: compare with root node 8. Is 3 < 8?',
    variables: { inserting: 3, comparing_with: 8, direction: null },
    changedVariables: ['inserting', 'comparing_with'],
    dataStructure: {
      type: 'tree',
      nodes: [{ id: 'n8', value: 8, state: 'comparing' }],
      root: 'n8',
      highlightPath: ['n8'],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is 3 < 8? Should we go left or right?',
      options: [
        { id: 'left', label: 'Left — 3 is less than 8' },
        { id: 'right', label: 'Right — 3 is greater than or equal to 8' },
      ],
      correctId: 'left',
    },
    explanation:
      '3 < 8 is true, so we recurse into the left subtree of node 8.',
    hints: [
      'In a BST, smaller values go left, larger values go right.',
      '3 is less than 8, so we go left.',
      'The answer is Left.',
    ],
  },

  // --- Step 2: 3 inserted as left child of 8 ---
  {
    stepNumber: 2,
    codeLine: 11,
    description: 'Node 8 has no left child (None), so 3 is inserted as the left child of 8.',
    variables: { inserting: 3, comparing_with: 8, direction: 'left' },
    changedVariables: ['direction'],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', state: 'default' },
        { id: 'n3', value: 3, state: 'inserted' },
      ],
      root: 'n8',
    },
    prediction: {
      type: 'value',
      prompt: 'Where is 3 placed in the tree?',
      correctValue: 'left child of 8',
      acceptableValues: [
        'left child of 8',
        'left of 8',
        'left child of root',
        '8.left',
        'left',
      ],
      placeholder: 'e.g. left child of 8',
    },
    explanation:
      'We recursed left from 8 and found None, so we create a new node with value 3 as the left child of 8.',
    hints: [
      'We went left from the root. What is there?',
      'The left subtree of 8 is empty (None), so 3 is placed there.',
      'The answer is: left child of 8.',
    ],
  },

  // --- Step 3: Insert 10 — compare with 8 ---
  {
    stepNumber: 3,
    codeLine: 10,
    description: 'Insert 10: compare with root node 8. Is 10 < 8?',
    variables: { inserting: 10, comparing_with: 8, direction: null },
    changedVariables: ['inserting', 'comparing_with', 'direction'],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', state: 'comparing' },
        { id: 'n3', value: 3, state: 'default' },
      ],
      root: 'n8',
      highlightPath: ['n8'],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is 10 < 8? Should we go left or right?',
      options: [
        { id: 'left', label: 'Left — 10 is less than 8' },
        { id: 'right', label: 'Right — 10 is greater than or equal to 8' },
      ],
      correctId: 'right',
    },
    explanation:
      '10 < 8 is false (10 >= 8), so we recurse into the right subtree of node 8.',
    hints: [
      'Compare 10 with 8. Which is larger?',
      '10 is greater than 8, so the condition val < root.val is false.',
      'The answer is Right.',
    ],
  },

  // --- Step 4: 10 inserted as right child of 8 (auto-advance) ---
  {
    stepNumber: 4,
    codeLine: 12,
    description: 'Node 8 has no right child (None), so 10 is inserted as the right child of 8.',
    variables: { inserting: 10, comparing_with: 8, direction: 'right' },
    changedVariables: ['direction'],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', right: 'n10', state: 'default' },
        { id: 'n3', value: 3, state: 'default' },
        { id: 'n10', value: 10, state: 'inserted' },
      ],
      root: 'n8',
    },
    prediction: null, // auto-advance
    explanation:
      'We recursed right from 8 and found None, so we create a new node with value 10 as the right child of 8.',
    hints: ['', '', ''],
  },

  // --- Step 5: Insert 1 — compare with 8 ---
  {
    stepNumber: 5,
    codeLine: 10,
    description: 'Insert 1: compare with root node 8. Which direction?',
    variables: { inserting: 1, comparing_with: 8, direction: null },
    changedVariables: ['inserting', 'comparing_with', 'direction'],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', right: 'n10', state: 'comparing' },
        { id: 'n3', value: 3, state: 'default' },
        { id: 'n10', value: 10, state: 'default' },
      ],
      root: 'n8',
      highlightPath: ['n8'],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'After comparing 1 with 8, which way do we go?',
      options: [
        { id: 'left', label: 'Left — 1 is less than 8' },
        { id: 'right', label: 'Right — 1 is greater than or equal to 8' },
      ],
      correctId: 'left',
    },
    explanation:
      '1 < 8 is true, so we recurse into the left subtree of node 8, arriving at node 3.',
    hints: [
      'Is 1 smaller or larger than 8?',
      '1 is much smaller than 8, so we go left.',
      'The answer is Left.',
    ],
  },

  // --- Step 6: Insert 1 — compare with 3 ---
  {
    stepNumber: 6,
    codeLine: 10,
    description: 'Continue inserting 1: now compare with node 3. Is 1 < 3?',
    variables: { inserting: 1, comparing_with: 3, direction: 'left' },
    changedVariables: ['comparing_with'],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', right: 'n10', state: 'path' },
        { id: 'n3', value: 3, state: 'comparing' },
        { id: 'n10', value: 10, state: 'default' },
      ],
      root: 'n8',
      highlightPath: ['n8', 'n3'],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Is 1 < 3? Should we go left or right from node 3?',
      options: [
        { id: 'left', label: 'Left — 1 is less than 3' },
        { id: 'right', label: 'Right — 1 is greater than or equal to 3' },
      ],
      correctId: 'left',
    },
    explanation:
      '1 < 3 is true, so we recurse into the left subtree of node 3. Since node 3 has no left child, 1 will be inserted there.',
    hints: [
      'Compare 1 with the current node value 3.',
      '1 is less than 3, so the condition is true.',
      'The answer is Left.',
    ],
  },

  // --- Step 7: 1 inserted as left child of 3 ---
  {
    stepNumber: 7,
    codeLine: 11,
    description: 'Node 3 has no left child, so 1 is inserted as the left child of 3.',
    variables: { inserting: 1, comparing_with: 3, direction: 'left' },
    changedVariables: [],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', right: 'n10', state: 'default' },
        { id: 'n3', value: 3, left: 'n1', state: 'default' },
        { id: 'n10', value: 10, state: 'default' },
        { id: 'n1', value: 1, state: 'inserted' },
      ],
      root: 'n8',
    },
    prediction: {
      type: 'value',
      prompt: 'Where is 1 placed in the tree?',
      correctValue: 'left child of 3',
      acceptableValues: [
        'left child of 3',
        'left of 3',
        '3.left',
        'left',
      ],
      placeholder: 'e.g. left child of 3',
    },
    explanation:
      'We followed the path 8 -> 3 (both times going left). Node 3 has no left child, so 1 is inserted as the left child of 3.',
    hints: [
      'We went left from 8, then left from 3.',
      'Node 3 has no left child yet, so 1 goes there.',
      'The answer is: left child of 3.',
    ],
  },

  // --- Step 8: Insert 6 — traverse to 3, then compare ---
  {
    stepNumber: 8,
    codeLine: 10,
    description: 'Insert 6: traverse left from 8 to reach node 3. Now compare 6 with 3.',
    variables: { inserting: 6, comparing_with: 3, direction: null },
    changedVariables: ['inserting', 'comparing_with', 'direction'],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', right: 'n10', state: 'path' },
        { id: 'n3', value: 3, left: 'n1', state: 'comparing' },
        { id: 'n10', value: 10, state: 'default' },
        { id: 'n1', value: 1, state: 'default' },
      ],
      root: 'n8',
      highlightPath: ['n8', 'n3'],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'We arrived at node 3. Is 6 < 3? Which direction from node 3?',
      options: [
        { id: 'left', label: 'Left — 6 is less than 3' },
        { id: 'right', label: 'Right — 6 is greater than or equal to 3' },
      ],
      correctId: 'right',
    },
    explanation:
      '6 < 3 is false (6 >= 3), so we recurse into the right subtree of node 3. Since node 3 has no right child, 6 will be inserted there.',
    hints: [
      'Compare 6 with the current node value 3.',
      '6 is greater than 3, so the condition val < root.val is false.',
      'The answer is Right.',
    ],
  },

  // --- Step 9: 6 inserted as right child of 3 ---
  {
    stepNumber: 9,
    codeLine: 12,
    description: 'Node 3 has no right child, so 6 is inserted as the right child of 3.',
    variables: { inserting: 6, comparing_with: 3, direction: 'right' },
    changedVariables: ['direction'],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', right: 'n10', state: 'default' },
        { id: 'n3', value: 3, left: 'n1', right: 'n6', state: 'default' },
        { id: 'n10', value: 10, state: 'default' },
        { id: 'n1', value: 1, state: 'default' },
        { id: 'n6', value: 6, state: 'inserted' },
      ],
      root: 'n8',
    },
    prediction: {
      type: 'value',
      prompt: 'Where is 6 placed in the tree?',
      correctValue: 'right child of 3',
      acceptableValues: [
        'right child of 3',
        'right of 3',
        '3.right',
        'right',
      ],
      placeholder: 'e.g. right child of 3',
    },
    explanation:
      'We followed the path 8 -> 3 (going left from 8, then right from 3). Node 3 has no right child, so 6 is inserted as the right child of 3.',
    hints: [
      'We went left from 8 to reach 3, then right from 3.',
      'Node 3 already has 1 as its left child, but no right child.',
      'The answer is: right child of 3.',
    ],
  },

  // --- Step 10: Insert 14 — compare with 8, then 10 ---
  {
    stepNumber: 10,
    codeLine: 12,
    description: 'Insert 14: traverse right from 8 to reach node 10. Now compare 14 with 10.',
    variables: { inserting: 14, comparing_with: 10, direction: null },
    changedVariables: ['inserting', 'comparing_with', 'direction'],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', right: 'n10', state: 'path' },
        { id: 'n3', value: 3, left: 'n1', right: 'n6', state: 'default' },
        { id: 'n10', value: 10, state: 'comparing' },
        { id: 'n1', value: 1, state: 'default' },
        { id: 'n6', value: 6, state: 'default' },
      ],
      root: 'n8',
      highlightPath: ['n8', 'n10'],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'We arrived at node 10. Is 14 < 10? Which direction?',
      options: [
        { id: 'left', label: 'Left — 14 is less than 10' },
        { id: 'right', label: 'Right — 14 is greater than or equal to 10' },
      ],
      correctId: 'right',
    },
    explanation:
      '14 < 10 is false (14 >= 10), so we recurse into the right subtree of node 10. Since node 10 has no right child, 14 will be inserted there.',
    hints: [
      'Compare 14 with the current node value 10.',
      '14 is greater than 10, so we go right.',
      'The answer is Right.',
    ],
  },

  // --- Step 11: 14 inserted as right child of 10 — final summary ---
  {
    stepNumber: 11,
    codeLine: 12,
    description:
      'Node 10 has no right child, so 14 is inserted as the right child of 10. The BST is complete!',
    variables: { inserting: 14, comparing_with: 10, direction: 'right' },
    changedVariables: ['direction'],
    dataStructure: {
      type: 'tree',
      nodes: [
        { id: 'n8', value: 8, left: 'n3', right: 'n10', state: 'default' },
        { id: 'n3', value: 3, left: 'n1', right: 'n6', state: 'default' },
        { id: 'n10', value: 10, right: 'n14', state: 'default' },
        { id: 'n1', value: 1, state: 'default' },
        { id: 'n6', value: 6, state: 'default' },
        { id: 'n14', value: 14, state: 'inserted' },
      ],
      root: 'n8',
    },
    prediction: {
      type: 'multi_select',
      prompt: 'The BST is complete! Which nodes are leaf nodes (no children)?',
      options: [
        { id: 'n8', label: '8' },
        { id: 'n3', label: '3' },
        { id: 'n10', label: '10' },
        { id: 'n1', label: '1' },
        { id: 'n6', label: '6' },
        { id: 'n14', label: '14' },
      ],
      correctIds: ['n1', 'n6', 'n14'],
    },
    explanation:
      'All 6 nodes are inserted. The leaf nodes (nodes with no children) are 1, 6, and 14. Node 8 is the root with children 3 and 10. Node 3 has children 1 and 6. Node 10 has child 14.',
    hints: [
      'A leaf node has no left or right children.',
      'Look at nodes 1, 6, and 14 — do any of them have children?',
      'The leaf nodes are 1, 6, and 14.',
    ],
  },
];

export const bstInsertDemo: StateTracerBlueprint = {
  algorithmName: 'BST Insert',
  algorithmDescription:
    'Build a Binary Search Tree by inserting elements one at a time, comparing at each node to find the correct position.',
  narrativeIntro:
    'Build a BST by inserting [8, 3, 10, 1, 6, 14]. Can you predict where each node goes?',
  code: CODE,
  language: 'python',
  steps,
};
