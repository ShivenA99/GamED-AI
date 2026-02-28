import { CombinedPuzzleBlueprint } from '../algorithmChallenge/combinedPuzzleTypes';

export const combinedPuzzleActivitySelection: CombinedPuzzleBlueprint = {
  title: 'Activity Selection — Code + Puzzle',
  description:
    'Implement the greedy activity selection algorithm AND manually pick non-overlapping activities.',
  icon: '\u{1F4C5}',

  // ─── Puzzle Side ───────────────────────────────────────────────────
  puzzleBlueprint: {
    title: 'Activity Scheduling',
    narrative:
      'You have one meeting room for the day. Select as many non-overlapping activities as possible.',
    rules: [
      'No two selected activities can overlap in time.',
      'Goal: select the maximum number of activities.',
    ],
    objective: 'Select the maximum number of non-overlapping activities.',
    boardConfig: {
      boardType: 'item_selection',
      items: [
        { id: 'a1', label: 'Yoga (1-3)', properties: { start: 1, end: 3 }, icon: '\u{1F9D8}' },
        { id: 'a2', label: 'Meeting (2-5)', properties: { start: 2, end: 5 }, icon: '\u{1F4BC}' },
        { id: 'a3', label: 'Lunch (3-4)', properties: { start: 3, end: 4 }, icon: '\u{1F35C}' },
        { id: 'a4', label: 'Workshop (4-7)', properties: { start: 4, end: 7 }, icon: '\u{1F4DD}' },
        { id: 'a5', label: 'Break (5-6)', properties: { start: 5, end: 6 }, icon: '\u2615' },
        { id: 'a6', label: 'Seminar (6-8)', properties: { start: 6, end: 8 }, icon: '\u{1F393}' },
        { id: 'a7', label: 'Dinner (8-9)', properties: { start: 8, end: 9 }, icon: '\u{1F37D}' },
      ],
      displayColumns: ['start', 'end'],
      propertyLabels: { start: 'Start', end: 'End' },
    },
    constraints: [
      { type: 'no_overlap', startProperty: 'start', endProperty: 'end' },
    ],
    scoringConfig: { method: 'count' },
    optimalValue: 4,
    optimalSolutionDescription:
      'Yoga(1-3) + Lunch(3-4) + Break(5-6) + Dinner(8-9) = 4 activities. Greedy: always pick the activity that ends earliest.',
    algorithmName: 'Greedy Activity Selection',
    algorithmExplanation:
      'Sort by end time. Always pick the next activity whose start time >= last selected end time. This greedy choice is provably optimal. Time: O(n log n).',
    showConstraintsVisually: true,
    allowUndo: true,
    hints: [
      'Which activity ends the earliest? Start there.',
      'After Yoga (ends at 3), the next available is Lunch (starts at 3).',
      'Optimal: Yoga(1-3), Lunch(3-4), Break(5-6), Dinner(8-9) = 4 activities.',
    ],
  },

  // ─── Code Side ─────────────────────────────────────────────────────
  algorithmChallenge: {
    mode: 'parsons',
    language: 'python',
    solutionCode: `def activity_selection(activities):
    sorted_acts = sorted(activities, key=lambda a: a[1])
    selected = [sorted_acts[0]]
    last_end = sorted_acts[0][1]
    for act in sorted_acts[1:]:
        if act[0] >= last_end:
            selected.append(act)
            last_end = act[1]
    return selected`,
    correctOrder: [
      { id: 'as1', code: 'def activity_selection(activities):', indent_level: 0, is_distractor: false },
      { id: 'as2', code: 'sorted_acts = sorted(activities, key=lambda a: a[1])', indent_level: 1, is_distractor: false },
      { id: 'as3', code: 'selected = [sorted_acts[0]]', indent_level: 1, is_distractor: false },
      { id: 'as4', code: 'last_end = sorted_acts[0][1]', indent_level: 1, is_distractor: false },
      { id: 'as5', code: 'for act in sorted_acts[1:]:', indent_level: 1, is_distractor: false },
      { id: 'as6', code: 'if act[0] >= last_end:', indent_level: 2, is_distractor: false },
      { id: 'as7', code: 'selected.append(act)', indent_level: 3, is_distractor: false },
      { id: 'as8', code: 'last_end = act[1]', indent_level: 3, is_distractor: false },
      { id: 'as9', code: 'return selected', indent_level: 1, is_distractor: false },
    ],
    distractors: [
      { id: 'asd1', code: 'sorted_acts = sorted(activities, key=lambda a: a[0])', indent_level: 1, is_distractor: true, distractor_explanation: 'Sorting by start time instead of end time does NOT give optimal activity selection.' },
      { id: 'asd2', code: 'if act[0] > last_end:', indent_level: 2, is_distractor: true, distractor_explanation: 'Using > instead of >= means activities that start exactly when the previous ends are excluded.' },
    ],
    parsonsConfig: {
      indentation_matters: true,
      max_attempts: null,
      show_line_numbers: true,
      allow_indent_adjustment: true,
    },
    testCases: [
      {
        id: 'tc-puzzle',
        label: 'Puzzle activities',
        setupCode: `activities = [(1,3,'a1'),(2,5,'a2'),(3,4,'a3'),(4,7,'a4'),(5,6,'a5'),(6,8,'a6'),(8,9,'a7')]
names = {'a1':'a1','a2':'a2','a3':'a3','a4':'a4','a5':'a5','a6':'a6','a7':'a7'}`,
        callCode: 'result = activity_selection(activities)',
        printCode: 'print(",".join(sorted([a[2] for a in result])))',
        expectedOutput: 'a1,a3,a5,a7',
        isPuzzleCase: true,
      },
      {
        id: 'tc-all-overlap',
        label: 'All overlapping',
        setupCode: 'activities = [(1,5,"x"),(2,6,"y"),(3,7,"z")]',
        callCode: 'result = activity_selection(activities)',
        printCode: 'print(len(result))',
        expectedOutput: '1',
        isPuzzleCase: false,
      },
      {
        id: 'tc-no-overlap',
        label: 'No overlaps',
        setupCode: 'activities = [(1,2,"a"),(3,4,"b"),(5,6,"c")]',
        callCode: 'result = activity_selection(activities)',
        printCode: 'print(len(result))',
        expectedOutput: '3',
        isPuzzleCase: false,
      },
    ],
    outputFormat: 'list_of_ids',
    hints: [
      'The key insight: sort by END time, not start time.',
      'After sorting, greedily pick the first non-overlapping activity.',
      'The algorithm is: sort by end, pick first, then pick next whose start >= last end.',
    ],
  },
};
