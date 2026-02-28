import { StateTracerBlueprint, ExecutionStep } from '../types';

const CODE = `def reverse_list(head):
    prev = None
    curr = head
    while curr:
        next_node = curr.next
        curr.next = prev
        prev = curr
        curr = next_node
    return prev

# Example: 1 → 2 → 3 → null`;

// ============================================================================
// Full execution trace: reverse linked list 1→2→3→null
// Three-pointer technique: prev, curr, next_node
// 10 steps covering all iterations of the while loop
// ============================================================================

const steps: ExecutionStep[] = [
  // --- INIT: prev = None, curr = head ---
  {
    stepNumber: 0,
    codeLine: 2,
    description: 'Initialize prev = None, curr = head (node 1). Ready to begin reversal.',
    variables: { prev: null, curr: 'n1', next_node: null },
    changedVariables: ['prev', 'curr'],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: 'n2', state: 'current' },
        { id: 'n2', value: 2, next: 'n3', state: 'default' },
        { id: 'n3', value: 3, next: null, state: 'default' },
      ],
      head: 'n1',
      pointers: [
        { name: 'prev', target: null, color: '#ef4444' },
        { name: 'curr', target: 'n1', color: '#facc15' },
      ],
    },
    prediction: null, // auto-advance
    explanation:
      'We start with prev = None (nothing before the first node) and curr pointing to the head of the list (node 1).',
    hints: ['', '', ''],
  },

  // =================== ITERATION 1: curr = n1 ===================

  // Step 1: next_node = curr.next (= n2)
  {
    stepNumber: 1,
    codeLine: 4,
    description: 'Save the next node before we break the link: next_node = curr.next',
    variables: { prev: null, curr: 'n1', next_node: 'n2' },
    changedVariables: ['next_node'],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: 'n2', state: 'current' },
        { id: 'n2', value: 2, next: 'n3', state: 'default' },
        { id: 'n3', value: 3, next: null, state: 'default' },
      ],
      head: 'n1',
      pointers: [
        { name: 'prev', target: null, color: '#ef4444' },
        { name: 'curr', target: 'n1', color: '#facc15' },
        { name: 'next_node', target: 'n2', color: '#22d3ee' },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What is curr.next? (the node after node 1)',
      correctValue: '2',
      acceptableValues: ['2', 'node 2', 'n2'],
      placeholder: 'e.g. 2',
    },
    explanation:
      'curr is node 1, and node 1\'s next pointer points to node 2. We save this in next_node so we don\'t lose it when we reverse the link.',
    hints: [
      'curr is node 1. What node comes after it in the original list?',
      'The original list is 1 → 2 → 3. Node 1 points to node 2.',
      'The answer is 2 (node 2).',
    ],
  },

  // Step 2: curr.next = prev (null) — reverse the link
  {
    stepNumber: 2,
    codeLine: 5,
    description: 'Reverse the link: curr.next = prev (null). Node 1 now points to nothing.',
    variables: { prev: null, curr: 'n1', next_node: 'n2' },
    changedVariables: [],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: 'n2', state: 'current' },
        { id: 'n2', value: 2, next: 'n3', state: 'default' },
        { id: 'n3', value: 3, next: null, state: 'default' },
      ],
      head: 'n1',
      pointers: [
        { name: 'prev', target: null, color: '#ef4444' },
        { name: 'curr', target: 'n1', color: '#facc15' },
        { name: 'next_node', target: 'n2', color: '#22d3ee' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Where does curr.next point after reassignment (curr.next = prev)?',
      options: [
        { id: 'null', label: 'null (prev is None)' },
        { id: 'n2', label: 'node 2' },
        { id: 'n3', label: 'node 3' },
      ],
      correctId: 'null',
    },
    explanation:
      'prev is currently None, so curr.next = prev sets node 1\'s next to null. Node 1 is now detached from the rest of the list — this is the first reversed link.',
    hints: [
      'What is the current value of prev?',
      'prev is None (null). So curr.next becomes null.',
      'The answer is null — node 1 now points to nothing.',
    ],
  },

  // Step 3: prev = curr (n1), curr = next_node (n2)
  {
    stepNumber: 3,
    codeLine: 6,
    description: 'Advance pointers: prev = curr (node 1), curr = next_node (node 2).',
    variables: { prev: 'n1', curr: 'n2', next_node: 'n2' },
    changedVariables: ['prev', 'curr'],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: null, state: 'done' },
        { id: 'n2', value: 2, next: 'n3', state: 'current' },
        { id: 'n3', value: 3, next: null, state: 'default' },
      ],
      head: 'n1',
      pointers: [
        { name: 'prev', target: 'n1', color: '#ef4444' },
        { name: 'curr', target: 'n2', color: '#facc15' },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What does prev equal now? (after prev = curr)',
      correctValue: '1',
      acceptableValues: ['1', 'node 1', 'n1'],
      placeholder: 'e.g. 1',
    },
    explanation:
      'We move prev forward to where curr was (node 1), and curr advances to next_node (node 2). Node 1 is now fully processed — its link is reversed (points to null).',
    hints: [
      'prev takes on the value that curr had before advancing.',
      'curr was pointing to node 1, so prev becomes node 1.',
      'The answer is 1 (node 1).',
    ],
  },

  // =================== ITERATION 2: curr = n2 ===================

  // Step 4: next_node = curr.next (= n3)
  {
    stepNumber: 4,
    codeLine: 4,
    description: 'Save next_node = curr.next. What does node 2 point to?',
    variables: { prev: 'n1', curr: 'n2', next_node: 'n3' },
    changedVariables: ['next_node'],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: null, state: 'done' },
        { id: 'n2', value: 2, next: 'n3', state: 'current' },
        { id: 'n3', value: 3, next: null, state: 'default' },
      ],
      head: 'n1',
      pointers: [
        { name: 'prev', target: 'n1', color: '#ef4444' },
        { name: 'curr', target: 'n2', color: '#facc15' },
        { name: 'next_node', target: 'n3', color: '#22d3ee' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'What is curr.next (node 2\'s next pointer)?',
      options: [
        { id: 'n1', label: 'node 1' },
        { id: 'n3', label: 'node 3' },
        { id: 'null', label: 'null' },
      ],
      correctId: 'n3',
    },
    explanation:
      'Node 2 still has its original forward link to node 3 (we haven\'t reversed it yet). So next_node = node 3.',
    hints: [
      'We haven\'t touched node 2\'s next pointer yet. What did it originally point to?',
      'In the original list: 1 → 2 → 3. Node 2 points to node 3.',
      'The answer is node 3.',
    ],
  },

  // Step 5: curr.next = prev (n1) — reverse the link
  {
    stepNumber: 5,
    codeLine: 5,
    description: 'Reverse the link: curr.next = prev. Node 2 now points back to node 1.',
    variables: { prev: 'n1', curr: 'n2', next_node: 'n3' },
    changedVariables: [],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: null, state: 'done' },
        { id: 'n2', value: 2, next: 'n3', state: 'current' },
        { id: 'n3', value: 3, next: null, state: 'default' },
      ],
      head: 'n1',
      pointers: [
        { name: 'prev', target: 'n1', color: '#ef4444' },
        { name: 'curr', target: 'n2', color: '#facc15' },
        { name: 'next_node', target: 'n3', color: '#22d3ee' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Where does curr.next now point after curr.next = prev?',
      options: [
        { id: 'n1', label: 'node 1 (prev)' },
        { id: 'n3', label: 'node 3' },
        { id: 'null', label: 'null' },
      ],
      correctId: 'n1',
    },
    explanation:
      'prev is node 1, so curr.next = prev makes node 2 point to node 1. The link between node 2 and node 1 is now reversed: 2 → 1 → null.',
    hints: [
      'What is prev currently?',
      'prev is node 1. So curr.next becomes node 1.',
      'The answer is node 1 — the link is reversed.',
    ],
  },

  // Step 6: prev = curr (n2), curr = next_node (n3)
  {
    stepNumber: 6,
    codeLine: 6,
    description: 'Advance pointers: prev = curr (node 2), curr = next_node (node 3).',
    variables: { prev: 'n2', curr: 'n3', next_node: 'n3' },
    changedVariables: ['prev', 'curr'],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: null, state: 'done' },
        { id: 'n2', value: 2, next: 'n1', state: 'done' },
        { id: 'n3', value: 3, next: null, state: 'current' },
      ],
      head: 'n1',
      pointers: [
        { name: 'prev', target: 'n2', color: '#ef4444' },
        { name: 'curr', target: 'n3', color: '#facc15' },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What does prev equal now? (after prev = curr)',
      correctValue: '2',
      acceptableValues: ['2', 'node 2', 'n2'],
      placeholder: 'e.g. 2',
    },
    explanation:
      'prev advances to node 2, curr advances to node 3. The reversed portion so far is: 2 → 1 → null. Only node 3 remains.',
    hints: [
      'prev takes on the value curr had.',
      'curr was node 2, so prev becomes node 2.',
      'The answer is 2 (node 2).',
    ],
  },

  // =================== ITERATION 3: curr = n3 ===================

  // Step 7: next_node = curr.next (= null)
  {
    stepNumber: 7,
    codeLine: 4,
    description: 'Save next_node = curr.next. Node 3 is the last node.',
    variables: { prev: 'n2', curr: 'n3', next_node: null },
    changedVariables: ['next_node'],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: null, state: 'done' },
        { id: 'n2', value: 2, next: 'n1', state: 'done' },
        { id: 'n3', value: 3, next: null, state: 'current' },
      ],
      head: 'n1',
      pointers: [
        { name: 'prev', target: 'n2', color: '#ef4444' },
        { name: 'curr', target: 'n3', color: '#facc15' },
        { name: 'next_node', target: null, color: '#22d3ee' },
      ],
    },
    prediction: {
      type: 'value',
      prompt: 'What is curr.next? (node 3 is the last node)',
      correctValue: 'null',
      acceptableValues: ['null', 'None', 'none', 'nothing'],
      placeholder: 'e.g. null',
    },
    explanation:
      'Node 3 is the last node in the original list, so curr.next is null. This means next_node = null, and after this iteration curr will become null, ending the loop.',
    hints: [
      'Node 3 is the tail of the original list. What comes after it?',
      'The original list ends at node 3: 1 → 2 → 3 → null.',
      'The answer is null.',
    ],
  },

  // Step 8: curr.next = prev (n2) — final link reversal
  {
    stepNumber: 8,
    codeLine: 5,
    description: 'Reverse the last link: curr.next = prev. Node 3 now points to node 2.',
    variables: { prev: 'n2', curr: 'n3', next_node: null },
    changedVariables: [],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: null, state: 'done' },
        { id: 'n2', value: 2, next: 'n1', state: 'done' },
        { id: 'n3', value: 3, next: null, state: 'current' },
      ],
      head: 'n1',
      pointers: [
        { name: 'prev', target: 'n2', color: '#ef4444' },
        { name: 'curr', target: 'n3', color: '#facc15' },
        { name: 'next_node', target: null, color: '#22d3ee' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'After curr.next = prev, the full reversed chain is:',
      options: [
        { id: 'correct', label: '3 → 2 → 1 → null' },
        { id: 'wrong1', label: '1 → 2 → 3 → null' },
        { id: 'wrong2', label: '3 → 1 → 2 → null' },
      ],
      correctId: 'correct',
    },
    explanation:
      'Node 3 now points to node 2, which points to node 1, which points to null. All three links have been reversed: 3 → 2 → 1 → null.',
    hints: [
      'We set node 3\'s next to prev (node 2). Node 2 already points to node 1.',
      'Follow the chain: 3 → 2 → 1 → null.',
      'The answer is 3 → 2 → 1 → null.',
    ],
  },

  // Step 9: prev = curr (n3), curr = next_node (null). Loop ends.
  {
    stepNumber: 9,
    codeLine: 6,
    description: 'Advance pointers: prev = node 3, curr = null. The while loop ends.',
    variables: { prev: 'n3', curr: null, next_node: null },
    changedVariables: ['prev', 'curr'],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: null, state: 'done' },
        { id: 'n2', value: 2, next: 'n1', state: 'done' },
        { id: 'n3', value: 3, next: 'n2', state: 'done' },
      ],
      head: 'n3',
      pointers: [
        { name: 'prev', target: 'n3', color: '#ef4444' },
        { name: 'curr', target: null, color: '#facc15' },
      ],
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Does the while loop continue? (curr is now null)',
      options: [
        { id: 'yes', label: 'Yes — there are more nodes' },
        { id: 'no', label: 'No — curr is null, loop ends' },
      ],
      correctId: 'no',
    },
    explanation:
      'curr is now null, so the while loop condition (while curr) is False. The loop terminates. prev holds the new head of the reversed list (node 3).',
    hints: [
      'The while loop continues as long as curr is not null.',
      'curr was set to next_node, which was null.',
      'No — curr is null, so the loop ends.',
    ],
  },

  // Step 10: return prev — the new head
  {
    stepNumber: 10,
    codeLine: 8,
    description: 'Return prev (node 3) as the new head. Reversed list: 3 → 2 → 1 → null.',
    variables: { prev: 'n3', curr: null, next_node: null },
    changedVariables: [],
    dataStructure: {
      type: 'linked_list',
      nodes: [
        { id: 'n1', value: 1, next: null, state: 'done' },
        { id: 'n2', value: 2, next: 'n1', state: 'done' },
        { id: 'n3', value: 3, next: 'n2', state: 'done' },
      ],
      head: 'n3',
      pointers: [
        { name: 'prev', target: 'n3', color: '#ef4444' },
      ],
    },
    prediction: null, // auto-advance to completion
    explanation:
      'The function returns prev, which is node 3 — the new head of the reversed list. The original list 1 → 2 → 3 → null has been reversed to 3 → 2 → 1 → null using only three pointers and no extra space.',
    hints: ['', '', ''],
  },
];

export const reverseLinkedListDemo: StateTracerBlueprint = {
  algorithmName: 'Reverse Linked List',
  algorithmDescription:
    'Reverse a singly linked list in-place using three pointers: prev, curr, and next.',
  narrativeIntro:
    'Reverse the linked list 1 → 2 → 3. Track the three pointers and predict each reassignment.',
  code: CODE,
  language: 'python',
  steps,
};
