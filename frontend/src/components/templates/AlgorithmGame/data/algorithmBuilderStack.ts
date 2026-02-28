import { AlgorithmBuilderBlueprint } from '../types';

export const algorithmBuilderStack: AlgorithmBuilderBlueprint = {
  algorithmName: 'Valid Parentheses (Stack)',
  algorithmDescription:
    'Checks if a string of brackets is balanced using a stack. Each opening bracket pushes to the stack; each closing bracket must match the top. O(n) time.',
  problemDescription:
    'Build a function that returns True if a string of parentheses/brackets/braces is valid (properly opened and closed), False otherwise.',
  language: 'python',

  correct_order: [
    { id: 'vp-1', code: 'def is_valid(s):', indent_level: 0, is_distractor: false },
    { id: 'vp-2', code: 'stack = []', indent_level: 1, is_distractor: false },
    { id: 'vp-3', code: "mapping = {')': '(', ']': '[', '}': '{'}", indent_level: 1, is_distractor: false },
    { id: 'vp-4', code: 'for char in s:', indent_level: 1, is_distractor: false },
    { id: 'vp-5', code: 'if char in mapping:', indent_level: 2, is_distractor: false },
    { id: 'vp-6', code: 'if not stack or stack[-1] != mapping[char]:', indent_level: 3, is_distractor: false },
    { id: 'vp-7', code: 'return False', indent_level: 4, is_distractor: false },
    { id: 'vp-8', code: 'stack.pop()', indent_level: 3, is_distractor: false },
    { id: 'vp-9', code: 'else:', indent_level: 2, is_distractor: false },
    { id: 'vp-10', code: 'stack.append(char)', indent_level: 3, is_distractor: false },
    { id: 'vp-11', code: 'return len(stack) == 0', indent_level: 1, is_distractor: false },
  ],

  distractors: [
    {
      id: 'vp-d1',
      code: 'stack.pop()',
      indent_level: 2,
      is_distractor: true,
      distractor_explanation:
        'Popping without first checking if the stack is empty and if the top matches would crash on empty stack or accept invalid sequences.',
    },
    {
      id: 'vp-d2',
      code: "mapping = {'(': ')', '[': ']', '{': '}'}", // reversed mapping
      indent_level: 1,
      is_distractor: true,
      distractor_explanation:
        'The mapping is reversed \u2014 it maps opening to closing. We need closing-to-opening so we can look up what the matching opener should be.',
    },
  ],

  config: {
    indentation_matters: true,
    max_attempts: null,
    show_line_numbers: true,
    allow_indent_adjustment: true,
  },

  hints: [
    'A stack tracks unmatched opening brackets. When you see a closing bracket, check if it matches the top of the stack.',
    'The mapping goes from closing bracket to opening bracket. Check two things before popping: stack is not empty AND top matches.',
    'Order: def \u2192 stack=[] \u2192 mapping \u2192 for char \u2192 if closing bracket \u2192 check stack top \u2192 return False / pop \u2192 else push \u2192 return empty check.',
  ],

  test_cases: [
    { id: 'vp-t1', inputDescription: 's = "([]){}"', expectedOutput: 'True' },
    { id: 'vp-t2', inputDescription: 's = "([)]"', expectedOutput: 'False' },
    { id: 'vp-t3', inputDescription: 's = ""', expectedOutput: 'True' },
  ],
};
