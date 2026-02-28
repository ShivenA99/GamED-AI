import { BugHunterBlueprint } from '../types';

export const bugHunterLinkedList: BugHunterBlueprint = {
  algorithmName: 'Linked List Reversal',
  algorithmDescription:
    'Reversing a singly linked list in-place is a classic pointer manipulation problem. The algorithm iterates through the list, redirecting each node\'s next pointer to the previous node, achieving O(n) time and O(1) space complexity.',
  narrativeIntro:
    'This linked list reversal has two bugs \u2014 one in the pointer manipulation and one in what the function returns. Can you trace through and fix them?',
  language: 'python',

  buggyCode: `def reverse_linked_list(head):
    prev = None
    curr = head
    while curr is not None:
        next_node = curr.next
        curr.next = curr
        prev = curr
        curr = next_node
    return curr`,

  correctCode: `def reverse_linked_list(head):
    prev = None
    curr = head
    while curr is not None:
        next_node = curr.next
        curr.next = prev
        prev = curr
        curr = next_node
    return prev`,

  bugs: [
    {
      bugId: 'bug-1',
      lineNumber: 6,
      buggyLineText: '        curr.next = curr',
      correctLineText: '        curr.next = prev',
      bugType: 'wrong_variable',
      difficulty: 2,
      explanation:
        'Setting curr.next = curr creates a self-loop \u2014 the node points to itself. We need curr.next = prev to point backward to the previous node, which is the core of the reversal.',
      bugTypeExplanation:
        'A wrong variable error occurs when a different variable is used than intended, causing incorrect pointer assignments in linked list operations.',
      fixOptions: [
        {
          id: 'fix-1a',
          codeText: '        curr.next = curr',
          isCorrect: false,
          feedback:
            'This creates a self-loop: the node points to itself instead of the previous node. This causes an infinite loop if you traverse the list.',
        },
        {
          id: 'fix-1b',
          codeText: '        curr.next = prev',
          isCorrect: true,
          feedback:
            'Correct! Pointing curr.next to prev reverses the direction of the link, which is the core operation of in-place reversal.',
        },
        {
          id: 'fix-1c',
          codeText: '        curr.next = next_node',
          isCorrect: false,
          feedback:
            'This would keep the original forward link, not reversing anything.',
        },
        {
          id: 'fix-1d',
          codeText: '        curr.next = head',
          isCorrect: false,
          feedback:
            'Pointing every node to head would make all nodes point to the same place, destroying the list structure.',
        },
      ],
      hints: [
        'This is a wrong variable error \u2014 the wrong reference is being assigned.',
        'The bug is in the pointer reassignment inside the loop (lines 5-6).',
        'Line 6 points curr.next to the wrong node. In reversal, each node should point backward.',
      ],
    },
    {
      bugId: 'bug-2',
      lineNumber: 9,
      buggyLineText: '    return curr',
      correctLineText: '    return prev',
      bugType: 'logic_error',
      difficulty: 3,
      explanation:
        'When the loop ends, curr is None (we\'ve gone past the last node). The reversed list\'s new head is prev, which holds the last node processed \u2014 what was originally the tail.',
      bugTypeExplanation:
        'A logic error means the code structure is correct but a crucial detail is wrong, often returning the wrong value or using the wrong variable at a key point.',
      fixOptions: [
        {
          id: 'fix-2a',
          codeText: '    return curr',
          isCorrect: false,
          feedback:
            'After the loop, curr is always None because the loop continues while curr is not None. Returning None means the reversed list is lost.',
        },
        {
          id: 'fix-2b',
          codeText: '    return prev',
          isCorrect: true,
          feedback:
            'Correct! prev holds the last node we processed, which is the new head of the reversed list.',
        },
        {
          id: 'fix-2c',
          codeText: '    return head',
          isCorrect: false,
          feedback:
            'head still points to the original first node, which is now the TAIL of the reversed list, not the new head.',
        },
        {
          id: 'fix-2d',
          codeText: '    return next_node',
          isCorrect: false,
          feedback:
            'next_node is None at loop exit (same as curr). It was a temporary variable used during iteration.',
        },
      ],
      hints: [
        'This is a logic error \u2014 the function returns the wrong value.',
        'The bug is in the return statement (line 9).',
        'Line 9 returns curr, but what is curr\'s value after the loop exits?',
      ],
    },
  ],

  testCases: [
    {
      id: 'test-1',
      inputDescription: '1 -> 2 -> 3 -> None',
      expectedOutput: '3 -> 2 -> 1 -> None',
      buggyOutput: 'None (infinite loop / wrong result)',
      exposedBugs: ['bug-1', 'bug-2'],
    },
    {
      id: 'test-2',
      inputDescription: '5 -> None (single node)',
      expectedOutput: '5 -> None',
      buggyOutput: 'None',
      exposedBugs: ['bug-2'],
    },
  ],

  redHerrings: [
    {
      lineNumber: 2,
      feedback:
        'Initializing prev to None is correct. The original head\'s next pointer should become None (it becomes the new tail).',
    },
    {
      lineNumber: 5,
      feedback:
        'Saving curr.next before we overwrite it is essential. Without this, we\'d lose the reference to the rest of the list.',
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
