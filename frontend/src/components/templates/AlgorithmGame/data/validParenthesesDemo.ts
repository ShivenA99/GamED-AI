import { StateTracerBlueprint, ExecutionStep } from '../types';

const CODE = `def is_valid(s):
    stack = []
    for char in s:
        if char == '(':
            stack.append(char)
        elif char == ')':
            if not stack:
                return False
            stack.pop()
    return len(stack) == 0

# Example: is_valid("(()(()))")`;

// ============================================================================
// Full execution trace: valid parentheses check on "(()(()))"
// 8 characters processed, ~10 steps with mixed prediction types
// ============================================================================

const steps: ExecutionStep[] = [
  // --- Step 0: INIT ---
  {
    stepNumber: 0,
    codeLine: 2,
    description: 'Initialize an empty stack to track open parentheses.',
    variables: { stack_contents: '', char: '', index: 0, stack_size: 0 },
    changedVariables: ['stack_contents', 'char', 'index', 'stack_size'],
    dataStructure: {
      type: 'stack',
      items: [],
      capacity: 8,
    },
    prediction: null, // auto-advance
    explanation:
      'We start with an empty stack. As we scan the string "(()(()))", each \'(\' will be pushed and each \')\' will pop the top.',
    hints: ['', '', ''],
  },

  // --- Step 1: char='(' at index 0 — push ---
  {
    stepNumber: 1,
    codeLine: 4,
    description: 'Read char \'(\' at index 0. Should we push or pop?',
    variables: { stack_contents: '(', char: '(', index: 0, stack_size: 1 },
    changedVariables: ['stack_contents', 'char', 'stack_size'],
    dataStructure: {
      type: 'stack',
      items: [{ id: 's0', value: '(', state: 'pushing' }],
      capacity: 8,
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'We encounter \'(\'. Do we push or pop?',
      options: [
        { id: 'push', label: 'Push \'(\' onto the stack' },
        { id: 'pop', label: 'Pop from the stack' },
      ],
      correctId: 'push',
    },
    explanation:
      'An opening parenthesis \'(\' always gets pushed onto the stack. The stack now has one element.',
    hints: [
      'Think about what an opening parenthesis means.',
      'Opening parens are stored on the stack to be matched later.',
      'Push — we push \'(\' onto the stack.',
    ],
  },

  // --- Step 2: char='(' at index 1 — push ---
  {
    stepNumber: 2,
    codeLine: 4,
    description: 'Read char \'(\' at index 1. Another opening parenthesis.',
    variables: { stack_contents: '(,(', char: '(', index: 1, stack_size: 2 },
    changedVariables: ['stack_contents', 'index', 'stack_size'],
    dataStructure: {
      type: 'stack',
      items: [
        { id: 's0', value: '(', state: 'default' },
        { id: 's1', value: '(', state: 'pushing' },
      ],
      capacity: 8,
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Another \'(\'. What do we do?',
      options: [
        { id: 'push', label: 'Push \'(\' onto the stack' },
        { id: 'pop', label: 'Pop from the stack' },
        { id: 'nothing', label: 'Do nothing' },
      ],
      correctId: 'push',
    },
    explanation:
      'Another opening parenthesis gets pushed. The stack now has two \'(\' elements waiting for matches.',
    hints: [
      'Same rule as before for \'(\'.',
      'Opening parentheses always get pushed.',
      'Push — the stack now has two elements.',
    ],
  },

  // --- Step 3: char=')' at index 2 — pop ---
  {
    stepNumber: 3,
    codeLine: 8,
    description: 'Read char \')\' at index 2. This is a closing parenthesis — we need to match it.',
    variables: { stack_contents: '(', char: ')', index: 2, stack_size: 1 },
    changedVariables: ['stack_contents', 'char', 'index', 'stack_size'],
    dataStructure: {
      type: 'stack',
      items: [
        { id: 's0', value: '(', state: 'default' },
        { id: 's1', value: '(', state: 'matched' },
      ],
      capacity: 8,
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'We encounter \')\'. Push or pop for a closing parenthesis?',
      options: [
        { id: 'push', label: 'Push \')\' onto the stack' },
        { id: 'pop', label: 'Pop from the stack' },
      ],
      correctId: 'pop',
    },
    explanation:
      'A closing parenthesis matches the most recent unmatched opening parenthesis. We pop \'(\' from the top. Stack size goes from 2 to 1.',
    hints: [
      'Closing parens need to match with an opening paren.',
      'The match is done by popping the top of the stack.',
      'Pop — we remove the top \'(\' to match this \')\'.',
    ],
  },

  // --- Step 4: char='(' at index 3 — push ---
  {
    stepNumber: 4,
    codeLine: 4,
    description: 'Read char \'(\' at index 3. Push onto the stack.',
    variables: { stack_contents: '(,(', char: '(', index: 3, stack_size: 2 },
    changedVariables: ['stack_contents', 'char', 'index', 'stack_size'],
    dataStructure: {
      type: 'stack',
      items: [
        { id: 's0', value: '(', state: 'default' },
        { id: 's2', value: '(', state: 'pushing' },
      ],
      capacity: 8,
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'Another \'(\'. What happens to the stack?',
      options: [
        { id: 'push', label: 'Push — stack grows to size 2' },
        { id: 'pop', label: 'Pop — stack shrinks to size 0' },
      ],
      correctId: 'push',
    },
    explanation:
      'Opening parenthesis pushes onto the stack. We now have 2 unmatched \'(\' again.',
    hints: [
      'Remember the rule for \'(\'.',
      'Opening parens are always pushed.',
      'Push — the stack grows back to size 2.',
    ],
  },

  // --- Step 5: char='(' at index 4 — push (auto-advance) ---
  {
    stepNumber: 5,
    codeLine: 4,
    description: 'Read char \'(\' at index 4. Push onto the stack.',
    variables: { stack_contents: '(,(,(', char: '(', index: 4, stack_size: 3 },
    changedVariables: ['stack_contents', 'index', 'stack_size'],
    dataStructure: {
      type: 'stack',
      items: [
        { id: 's0', value: '(', state: 'default' },
        { id: 's2', value: '(', state: 'default' },
        { id: 's3', value: '(', state: 'pushing' },
      ],
      capacity: 8,
    },
    prediction: null, // auto-advance — same pattern as before
    explanation:
      'Another opening parenthesis pushed. Stack now has 3 elements. We have 3 unmatched opening parens.',
    hints: ['', '', ''],
  },

  // --- Step 6: char=')' at index 5 — pop ---
  {
    stepNumber: 6,
    codeLine: 8,
    description: 'Read char \')\' at index 5. Pop the top of the stack.',
    variables: { stack_contents: '(,(', char: ')', index: 5, stack_size: 2 },
    changedVariables: ['stack_contents', 'char', 'index', 'stack_size'],
    dataStructure: {
      type: 'stack',
      items: [
        { id: 's0', value: '(', state: 'default' },
        { id: 's2', value: '(', state: 'default' },
        { id: 's3', value: '(', state: 'matched' },
      ],
      capacity: 8,
    },
    prediction: {
      type: 'value',
      prompt: 'After popping, what is the stack size?',
      correctValue: '2',
      acceptableValues: ['2'],
      placeholder: 'e.g. 2',
    },
    explanation:
      'Closing paren pops the top. Stack goes from 3 to 2 items. The inner pair "()" at indices 4-5 is now matched.',
    hints: [
      'The stack had 3 items before this pop.',
      '3 minus 1 equals...',
      'The stack size is 2 after the pop.',
    ],
  },

  // --- Step 7: char=')' at index 6 — pop ---
  {
    stepNumber: 7,
    codeLine: 8,
    description: 'Read char \')\' at index 6. Pop again.',
    variables: { stack_contents: '(', char: ')', index: 6, stack_size: 1 },
    changedVariables: ['stack_contents', 'index', 'stack_size'],
    dataStructure: {
      type: 'stack',
      items: [
        { id: 's0', value: '(', state: 'default' },
        { id: 's2', value: '(', state: 'matched' },
      ],
      capacity: 8,
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'After this pop, how many items remain on the stack?',
      options: [
        { id: '0', label: '0 — stack is empty' },
        { id: '1', label: '1 — one item left' },
        { id: '2', label: '2 — two items left' },
      ],
      correctId: '1',
    },
    explanation:
      'Another closing paren pops the top. Stack goes from 2 to 1. The group "(())" at indices 3-6 is now matched.',
    hints: [
      'We had 2 items and popped one.',
      '2 minus 1 equals...',
      '1 — one \'(\' remains on the stack.',
    ],
  },

  // --- Step 8: char=')' at index 7 — pop (last character) ---
  {
    stepNumber: 8,
    codeLine: 8,
    description: 'Read char \')\' at index 7 (last character). Pop the final element.',
    variables: { stack_contents: '', char: ')', index: 7, stack_size: 0 },
    changedVariables: ['stack_contents', 'index', 'stack_size'],
    dataStructure: {
      type: 'stack',
      items: [
        { id: 's0', value: '(', state: 'popping' },
      ],
      capacity: 8,
    },
    prediction: {
      type: 'value',
      prompt: 'What is the stack size after this final pop?',
      correctValue: '0',
      acceptableValues: ['0'],
      placeholder: 'e.g. 0',
    },
    explanation:
      'The last closing paren matches the very first opening paren. The stack is now completely empty.',
    hints: [
      'We had 1 item and popped it.',
      '1 minus 1 equals...',
      'The stack size is 0 — completely empty.',
    ],
  },

  // --- Step 9: Check result — stack empty → True ---
  {
    stepNumber: 9,
    codeLine: 9,
    description: 'Loop finished. Check: is len(stack) == 0?',
    variables: { stack_contents: '', char: '', index: 8, stack_size: 0 },
    changedVariables: ['char', 'index'],
    dataStructure: {
      type: 'stack',
      items: [],
      capacity: 8,
    },
    prediction: {
      type: 'multiple_choice',
      prompt: 'The stack is empty. Is the string "(()(()))" valid?',
      options: [
        { id: 'yes', label: 'Yes — all parentheses are matched' },
        { id: 'no', label: 'No — there are unmatched parentheses' },
      ],
      correctId: 'yes',
    },
    explanation:
      'The stack is empty after processing all 8 characters, which means every opening parenthesis found a matching closing parenthesis. The function returns True — the string is valid!',
    hints: [
      'An empty stack means all parens were matched.',
      'len(stack) == 0 is True, so we return True.',
      'Yes — "(()(()))" is a valid parentheses string.',
    ],
  },
];

export const validParenthesesDemo: StateTracerBlueprint = {
  algorithmName: 'Valid Parentheses',
  algorithmDescription:
    'Check if a string of parentheses is balanced using a stack.',
  narrativeIntro:
    'Is "(()(()))" valid? Use a stack to track open parentheses and predict each push/pop.',
  code: CODE,
  language: 'python',
  steps,
};
