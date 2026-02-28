import { AlgorithmBuilderBlueprint } from '../types';

export const algorithmBuilderLinkedList: AlgorithmBuilderBlueprint = {
  algorithmName: 'Reverse Linked List',
  algorithmDescription:
    'Reversing a singly linked list in-place by redirecting pointers. Uses three pointers (prev, curr, next_node) and runs in O(n) time, O(1) space.',
  problemDescription:
    'Build a function that reverses a singly linked list iteratively using pointer manipulation.',
  language: 'python',

  correct_order: [
    { id: 'll-1', code: 'def reverse_list(head):', indent_level: 0, is_distractor: false },
    { id: 'll-2', code: 'prev = None', indent_level: 1, is_distractor: false },
    { id: 'll-3', code: 'curr = head', indent_level: 1, is_distractor: false },
    { id: 'll-4', code: 'while curr is not None:', indent_level: 1, is_distractor: false },
    { id: 'll-5', code: 'next_node = curr.next', indent_level: 2, is_distractor: false },
    { id: 'll-6', code: 'curr.next = prev', indent_level: 2, is_distractor: false },
    { id: 'll-7', code: 'prev = curr', indent_level: 2, is_distractor: false },
    { id: 'll-8', code: 'curr = next_node', indent_level: 2, is_distractor: false },
    { id: 'll-9', code: 'return prev', indent_level: 1, is_distractor: false },
  ],

  distractors: [
    {
      id: 'll-d1',
      code: 'curr.next = curr',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'Pointing curr.next to itself creates a cycle. The correct line is curr.next = prev to reverse the link direction.',
    },
    {
      id: 'll-d2',
      code: 'prev = next_node',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'prev must be set to curr (the current node), not next_node. Setting prev = next_node skips a node.',
    },
  ],

  config: {
    indentation_matters: true,
    max_attempts: null,
    show_line_numbers: true,
    allow_indent_adjustment: true,
  },

  hints: [
    'You need three pointers: prev starts as None, curr starts at head, and next_node is saved each iteration.',
    'Inside the loop: save next, reverse the link, then advance both pointers. The order of these four operations matters!',
    'Order: def \u2192 prev=None \u2192 curr=head \u2192 while curr \u2192 next_node=curr.next \u2192 curr.next=prev \u2192 prev=curr \u2192 curr=next_node \u2192 return prev.',
  ],

  test_cases: [
    { id: 'll-t1', inputDescription: '1 -> 2 -> 3 -> 4 -> None', expectedOutput: '4 -> 3 -> 2 -> 1 -> None' },
    { id: 'll-t2', inputDescription: '1 -> None', expectedOutput: '1 -> None' },
  ],
};
