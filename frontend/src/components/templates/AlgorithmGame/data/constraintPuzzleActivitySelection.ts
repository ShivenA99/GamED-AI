import { ConstraintPuzzleBlueprint } from '../types';

export const constraintPuzzleActivitySelection: ConstraintPuzzleBlueprint = {
  puzzleType: 'activity_selection',
  title: 'Conference Room Scheduling',
  narrative:
    'You are scheduling a conference room for the day. Multiple meetings are requested but some overlap. Select the maximum number of non-overlapping meetings!',
  rules: [
    'No two selected meetings can overlap in time',
    'Maximize the number of meetings you can fit',
    'Each meeting has a fixed start and end time',
    'Meetings that share an endpoint (one ends when another starts) are allowed',
  ],
  objective: 'Schedule the maximum number of non-overlapping meetings',
  puzzleData: {
    type: 'activity_selection',
    activities: [
      { id: 'a1', name: 'Team Standup', start: 0, end: 2 },
      { id: 'a2', name: 'Design Review', start: 1, end: 4 },
      { id: 'a3', name: 'Sprint Planning', start: 3, end: 5 },
      { id: 'a4', name: 'Code Review', start: 2, end: 6 },
      { id: 'a5', name: 'Architecture Talk', start: 5, end: 7 },
      { id: 'a6', name: 'Demo Prep', start: 6, end: 8 },
      { id: 'a7', name: 'Client Call', start: 5, end: 9 },
      { id: 'a8', name: 'Retrospective', start: 8, end: 10 },
      { id: 'a9', name: 'Workshop', start: 3, end: 8 },
      { id: 'a10', name: 'Lightning Talk', start: 7, end: 9 },
    ],
  },
  optimalValue: 4, // a1(0-2), a3(3-5), a5(5-7), a8(8-10) = 4 non-overlapping
  optimalSolutionDescription:
    'Optimal: Team Standup (0-2), Sprint Planning (3-5), Architecture Talk (5-7), Retrospective (8-10) = 4 meetings. The greedy algorithm sorts by end time and always picks the next activity that does not overlap.',
  algorithmName: 'Activity Selection (Greedy)',
  algorithmExplanation:
    'The Activity Selection problem is solved optimally with a Greedy algorithm. Sort activities by finish time. Pick the first activity. For each remaining activity, if its start time is >= the last selected activity\'s end time, select it. This greedy choice is provably optimal: by finishing as early as possible, we leave maximum room for future activities. Time complexity: O(n log n) for sorting + O(n) for selection = O(n log n).',
  showConstraintsVisually: true,
  showOptimalityScore: true,
  allowUndo: true,
  hints: [
    'Think about which meetings end earliest — that leaves the most room for others.',
    'Sort by end time: Standup(2), Design Review(4), Sprint Planning(5), Code Review(6), Architecture Talk(7), Demo Prep(8), Workshop(8), Client Call(9), Lightning Talk(9), Retro(10).',
    'Greedy solution: pick Standup (ends 2), skip Design Review (starts 1 < 2), pick Sprint Planning (starts 3 >= 2), pick Architecture Talk (starts 5 >= 5), pick Retrospective (starts 8 >= 7).',
  ],
};
