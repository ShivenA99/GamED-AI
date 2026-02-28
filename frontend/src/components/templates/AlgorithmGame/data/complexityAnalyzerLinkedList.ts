import { ComplexityAnalyzerBlueprint } from '../types';

export const complexityAnalyzerLinkedList: ComplexityAnalyzerBlueprint = {
  algorithmName: 'Linked List Reversal',
  algorithmDescription:
    'Analyze the time and space complexity of iterative linked list reversal.',
  challenges: [
    {
      challengeId: 'ca-ll-1',
      type: 'identify_from_code',
      title: 'Iterative Reversal — Time Complexity',
      description: 'Determine the time complexity of this iterative linked list reversal.',
      code: `def reverse_linked_list(head):
    prev = None
    curr = head
    while curr:
        next_node = curr.next
        curr.next = prev
        prev = curr
        curr = next_node
    return prev`,
      language: 'python',
      correctComplexity: 'O(n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n\u00B2)'],
      explanation:
        'The while loop visits each node exactly once, performing O(1) pointer reassignment per node. With n nodes in the list, the total time is O(n).',
      points: 100,
      hints: [
        'How many times does the while loop iterate?',
        'The loop moves curr forward one node each iteration until the end.',
        'n nodes visited once each = O(n).',
      ],
    },
    {
      challengeId: 'ca-ll-2',
      type: 'infer_from_growth',
      title: 'Linked List Operations — Growth',
      description: 'Operation counts for reversing linked lists of various sizes.',
      growthData: {
        inputSizes: [100, 500, 1000, 5000, 10000, 50000],
        operationCounts: [100, 500, 1000, 5000, 10000, 50000],
      },
      correctComplexity: 'O(n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)'],
      explanation:
        'The operation count equals the input size exactly: 100\u2192100, 500\u2192500, 10000\u219210000. A perfect 1:1 ratio is the definition of linear time O(n).',
      points: 100,
      hints: [
        'Compare each input size to its operation count.',
        'The operation count equals n every time.',
        'A direct proportionality (ops = c \u00D7 n) means O(n).',
      ],
    },
    {
      challengeId: 'ca-ll-3',
      type: 'find_bottleneck',
      title: 'Search + Reverse',
      description: 'This function searches for a value, then reverses the list. Which dominates?',
      code: `def find_and_reverse(head, target):
    # Section A: Linear search
    curr = head
    found = False
    while curr:
        if curr.val == target:
            found = True
            break
        curr = curr.next

    # Section B: Reverse entire list
    prev = None
    curr = head
    while curr:
        next_node = curr.next
        curr.next = prev
        prev = curr
        curr = next_node

    return prev, found`,
      language: 'python',
      codeSections: [
        { sectionId: 'sec-a', label: 'Section A: Search', startLine: 2, endLine: 8, complexity: 'O(n)', isBottleneck: false },
        { sectionId: 'sec-b', label: 'Section B: Reverse', startLine: 10, endLine: 16, complexity: 'O(n)', isBottleneck: false },
      ],
      correctComplexity: 'O(n)',
      options: ['O(1)', 'O(log n)', 'O(n)', 'O(n\u00B2)'],
      explanation:
        'Both sections are O(n). Section A searches (at worst) all n nodes. Section B reverses all n nodes. O(n) + O(n) = O(2n) = O(n). Neither dominates — they contribute equally.',
      points: 150,
      hints: [
        'What is the complexity of each section independently?',
        'Both search and reverse traverse the list once each: O(n) + O(n).',
        'O(n) + O(n) = O(2n) = O(n) — constants are dropped.',
      ],
    },
  ],
};
