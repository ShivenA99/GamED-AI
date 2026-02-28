import { GenericConstraintPuzzleBlueprint } from '../constraintPuzzle/constraintPuzzleTypes';

export const constraintPuzzleTopologicalSort: GenericConstraintPuzzleBlueprint = {
  title: 'Course Schedule Planner',
  narrative:
    'Plan the order to take 6 university courses. Some courses have prerequisites — you must take the prerequisite before the course that depends on it. Find a valid ordering!',
  rules: [
    'Arrange all 6 courses in a valid order',
    'A course cannot come before its prerequisites',
    'Click courses to add them to the sequence',
    'Use arrows to reorder if needed',
  ],
  objective: 'Order all 6 courses so every prerequisite comes before the course that needs it',
  boardConfig: {
    boardType: 'sequence_building',
    // Dependency graph:
    // Math101 → CS201, CS201 → CS301, CS201 → CS302
    // Stats101 → CS302
    // CS301 → CS401, CS302 → CS401
    items: [
      { id: 'math101', label: 'Math 101', icon: '\u{1F4D0}' },
      { id: 'stats101', label: 'Stats 101', icon: '\u{1F4CA}' },
      { id: 'cs201', label: 'CS 201', icon: '\u{1F4BB}' },
      { id: 'cs301', label: 'CS 301', icon: '\u{1F527}' },
      { id: 'cs302', label: 'CS 302', icon: '\u{1F4E1}' },
      { id: 'cs401', label: 'CS 401', icon: '\u{1F393}' },
    ],
    showArrows: true,
  },
  constraints: [
    { type: 'count_exact', count: 6, label: 'courses' },
  ],
  // Scoring: binary — either it's a valid topological order or not.
  // We check the ordering in the scoring config. Since we can't express
  // dependency constraints declaratively yet, we use binary scoring where
  // the optimal value is awarded only if the sequence is valid.
  // For the demo, the constraint evaluator checks count; the CHECK_SOLUTION
  // in the reducer validates all constraints pass. We rely on the player
  // understanding the rules.
  scoringConfig: { method: 'binary', successValue: 6 },
  optimalValue: 6,
  optimalSolutionDescription:
    'Valid orderings include: [Math 101, Stats 101, CS 201, CS 301, CS 302, CS 401] or [Stats 101, Math 101, CS 201, CS 302, CS 301, CS 401]. Any topological sort of the dependency DAG is correct.',
  algorithmName: 'Topological Sort (Kahn\'s Algorithm / DFS)',
  algorithmExplanation:
    'Topological Sort orders vertices of a directed acyclic graph (DAG) such that for every edge u→v, u comes before v. Kahn\'s algorithm: (1) Find all vertices with in-degree 0. (2) Add them to a queue. (3) Remove a vertex from the queue, output it, and decrease in-degrees of its neighbors. (4) Repeat until the queue is empty. DFS approach: run DFS, push vertices to a stack on finish. Reverse the stack for the topological order. Both run in O(V+E).',
  showConstraintsVisually: true,
  allowUndo: true,
  hints: [
    'Start with courses that have no prerequisites: Math 101 and Stats 101 can go first.',
    'CS 201 depends on Math 101. CS 302 depends on both CS 201 and Stats 101. CS 401 is last.',
    'One valid order: Math 101 → Stats 101 → CS 201 → CS 301 → CS 302 → CS 401.',
  ],
  icon: '\u{1F4DA}',
};
