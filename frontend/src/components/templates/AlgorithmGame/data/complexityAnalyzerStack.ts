import { ComplexityAnalyzerBlueprint } from '../types';

export const complexityAnalyzerStack: ComplexityAnalyzerBlueprint = {
  algorithmName: 'Valid Parentheses (Stack)',
  algorithmDescription:
    'Analyze the time complexity of the classic stack-based parentheses validation algorithm.',
  challenges: [
    {
      challengeId: 'ca-stack-1',
      type: 'identify_from_code',
      title: 'Valid Parentheses — Time Complexity',
      description: 'Determine the time complexity where n = length of the input string.',
      code: `def is_valid(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    for char in s:
        if char in mapping:
            top = stack.pop() if stack else '#'
            if mapping[char] != top:
                return False
        else:
            stack.append(char)
    return len(stack) == 0`,
      language: 'python',
      correctComplexity: 'O(n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n\u00B2)'],
      explanation:
        'The for loop iterates over each character exactly once. Each iteration does O(1) work: a dictionary lookup, a push or pop (both O(1) for a list/stack). So the total is O(n).',
      points: 100,
      hints: [
        'Count the main loop iterations.',
        'One pass through the string, one operation per character.',
        'n characters, O(1) per character = O(n).',
      ],
    },
    {
      challengeId: 'ca-stack-2',
      type: 'infer_from_growth',
      title: 'Parentheses Checker — Growth',
      description: 'Given operation counts for strings of various lengths, identify the pattern.',
      growthData: {
        inputSizes: [10, 50, 200, 1000, 5000, 20000],
        operationCounts: [10, 50, 200, 1000, 5000, 20000],
      },
      correctComplexity: 'O(n)',
      options: ['O(1)', 'O(n)', 'O(n log n)', 'O(n\u00B2)'],
      explanation:
        'Operations scale exactly with input: doubling input doubles operations. The 1:1 ratio confirms O(n) linear time.',
      points: 100,
      hints: [
        'Compare operation counts to input sizes.',
        'Every row shows ops = n exactly.',
        'Perfect proportionality = O(n).',
      ],
    },
    {
      challengeId: 'ca-stack-3',
      type: 'find_bottleneck',
      title: 'Validate All Strings in List',
      description: 'This validates every string in a list. Which section is the bottleneck?',
      code: `def validate_all(strings):
    # Section A: Iterate over all strings
    results = []
    for s in strings:
        # Section B: Validate one string
        stack = []
        mapping = {')': '(', '}': '{', ']': '['}
        valid = True
        for char in s:
            if char in mapping:
                top = stack.pop() if stack else '#'
                if mapping[char] != top:
                    valid = False
                    break
            else:
                stack.append(char)
        if valid:
            valid = len(stack) == 0
        results.append(valid)
    return results`,
      language: 'python',
      codeSections: [
        { sectionId: 'sec-a', label: 'Section A: Outer loop', startLine: 2, endLine: 18, complexity: 'O(k)', isBottleneck: false },
        { sectionId: 'sec-b', label: 'Section B: Inner validation', startLine: 5, endLine: 16, complexity: 'O(m)', isBottleneck: true },
      ],
      correctComplexity: 'O(k \u00D7 m)',
      options: ['O(k)', 'O(m)', 'O(k + m)', 'O(k \u00D7 m)'],
      explanation:
        'The outer loop runs k times (number of strings). For each string, the inner loop runs up to m times (length of that string). The nested loops give O(k \u00D7 m) total, where the inner validation is the bottleneck per iteration.',
      points: 150,
      hints: [
        'k = number of strings, m = average length of each string.',
        'For each of k strings, we scan up to m characters.',
        'Nested iteration: k outer \u00D7 m inner = O(k \u00D7 m).',
      ],
    },
  ],
};
