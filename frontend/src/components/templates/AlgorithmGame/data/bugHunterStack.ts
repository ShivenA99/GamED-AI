import { BugHunterBlueprint } from '../types';

export const bugHunterStack: BugHunterBlueprint = {
  algorithmName: 'Valid Parentheses (Stack)',
  algorithmDescription:
    'The valid parentheses algorithm uses a stack to check whether every opening bracket has a matching closing bracket in the correct order. It processes each character, pushing openers and popping for closers, achieving O(n) time complexity.',
  narrativeIntro:
    'This valid parentheses checker works for most inputs but crashes on a specific edge case. Can you find the boundary error?',
  language: 'python',

  buggyCode: `def is_valid_parentheses(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    for char in s:
        if char in mapping:
            top = stack.pop()
            if mapping[char] != top:
                return False
        else:
            stack.append(char)
    return len(stack) == 0`,

  correctCode: `def is_valid_parentheses(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    for char in s:
        if char in mapping:
            if not stack:
                return False
            top = stack.pop()
            if mapping[char] != top:
                return False
        else:
            stack.append(char)
    return len(stack) == 0`,

  bugs: [
    {
      bugId: 'bug-1',
      lineNumber: 6,
      buggyLineText: '            top = stack.pop()',
      correctLineText:
        '            if not stack:\n                return False\n            top = stack.pop()',
      bugType: 'boundary_error',
      difficulty: 2,
      explanation:
        "Calling stack.pop() on an empty stack raises an IndexError. This happens when the input starts with a closing bracket like ')abc'. We need to handle the empty stack case before popping.",
      bugTypeExplanation:
        'A boundary error fails to handle edge cases like empty collections, zero-length inputs, or single elements, causing crashes or wrong results on boundary inputs.',
      fixOptions: [
        {
          id: 'fix-a',
          codeText: '            top = stack.pop()',
          isCorrect: false,
          feedback:
            'This is the current code. It crashes with IndexError when the stack is empty (e.g., input starts with a closing bracket).',
        },
        {
          id: 'fix-b',
          codeText: "            top = stack.pop() if stack else '#'",
          isCorrect: true,
          feedback:
            "Correct! Using a sentinel value '#' when the stack is empty prevents the crash. Since '#' won't match any mapping value, it correctly returns False.",
        },
        {
          id: 'fix-c',
          codeText: '            top = stack[-1]',
          isCorrect: false,
          feedback:
            "peek (stack[-1]) also crashes on empty stack and doesn't remove the element, so the stack would grow incorrectly.",
        },
        {
          id: 'fix-d',
          codeText: '            top = stack.pop(0)',
          isCorrect: false,
          feedback:
            'pop(0) removes from the bottom of the stack, giving FIFO behavior instead of LIFO. This fundamentally breaks the matching logic.',
        },
      ],
      hints: [
        "This is a boundary error \u2014 an edge case isn't handled.",
        'The bug is in the stack operation inside the loop (lines 5-6).',
        "Line 6 pops from the stack without checking if it's empty first.",
      ],
    },
  ],

  testCases: [
    {
      id: 'test-1',
      inputDescription: 's = "(())"',
      expectedOutput: 'True',
      buggyOutput: 'True',
      exposedBugs: [],
    },
    {
      id: 'test-2',
      inputDescription: 's = ")("',
      expectedOutput: 'False',
      buggyOutput: 'IndexError',
      exposedBugs: ['bug-1'],
    },
    {
      id: 'test-3',
      inputDescription: 's = "([)]"',
      expectedOutput: 'False',
      buggyOutput: 'False',
      exposedBugs: [],
    },
  ],

  redHerrings: [
    {
      lineNumber: 3,
      feedback:
        'The mapping correctly pairs each closing bracket with its matching opening bracket. This is a standard approach.',
    },
    {
      lineNumber: 11,
      feedback:
        "Checking that the stack is empty at the end correctly handles unmatched opening brackets like '((('.",
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
