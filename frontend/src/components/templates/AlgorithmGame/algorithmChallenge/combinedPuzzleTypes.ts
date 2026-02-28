// ============================================================================
// Combined Puzzle + Code Game — Type Definitions
// ============================================================================
// Pairs a manual constraint puzzle (board) with an algorithm code challenge
// (Parsons or free-code). Student must both write and manually solve.
// ============================================================================

import { GenericConstraintPuzzleBlueprint, GenericPuzzleState } from '../constraintPuzzle/constraintPuzzleTypes';
import { ParsonsBlock, AlgorithmBuilderConfig } from '../types';

// ---------------------------------------------------------------------------
// Algorithm Challenge (code side)
// ---------------------------------------------------------------------------

export type ChallengeMode = 'parsons' | 'free_code' | 'both';

export interface AlgorithmChallengeTestCase {
  id: string;
  label: string;
  /** Python code to set up inputs (e.g. `items = [(7,10), ...]`) */
  setupCode: string;
  /** Python code to call the function (e.g. `result = knapsack(items, 15)`) */
  callCode: string;
  /** Python code to print the result (e.g. `print(sorted(result))`) */
  printCode: string;
  expectedOutput: string;
  /** When true, this test uses the same data as the puzzle board */
  isPuzzleCase?: boolean;
}

export interface AlgorithmChallenge {
  mode: ChallengeMode;
  language: 'python';
  /** Parsons blocks — correct order (mode = 'parsons' | 'both') */
  correctOrder?: ParsonsBlock[];
  /** Parsons distractor blocks */
  distractors?: ParsonsBlock[];
  /** Parsons config overrides */
  parsonsConfig?: AlgorithmBuilderConfig;
  /** Starter code shown in free-code editor */
  starterCode?: string;
  /** Reference solution (used for grading free-code, never shown) */
  solutionCode: string;
  /** Test cases for code execution */
  testCases: AlgorithmChallengeTestCase[];
  /** How to format code output for comparison with puzzle state */
  outputFormat: 'list_of_ids' | 'list_of_indices' | 'list_of_pairs' | 'single_value';
  /** 3-tier hints for the code side */
  hints: [string, string, string];
}

// ---------------------------------------------------------------------------
// Combined Blueprint (composition of puzzle + code)
// ---------------------------------------------------------------------------

export interface CombinedPuzzleBlueprint {
  title: string;
  description: string;
  icon?: string;
  puzzleBlueprint: GenericConstraintPuzzleBlueprint;
  algorithmChallenge: AlgorithmChallenge;
}

// ---------------------------------------------------------------------------
// Code-side state
// ---------------------------------------------------------------------------

export type CodePhase =
  | 'IDLE'
  | 'BUILDING'      // Parsons: arranging blocks
  | 'EDITING'        // Free code: typing
  | 'RUNNING'        // Pyodide executing
  | 'RESULTS_SHOWN'  // Test results visible
  | 'SUBMITTED';     // Code side locked in

export interface TestRunResult {
  testId: string;
  label: string;
  expectedOutput: string;
  actualOutput: string;
  passed: boolean;
  error?: string;
  executionTimeMs: number;
  isPuzzleCase?: boolean;
}

export interface CodeSideState {
  phase: CodePhase;
  activeTab: 'parsons' | 'free_code';
  freeCodeValue: string;
  testResults: TestRunResult[];
  passRate: number;         // 0..1
  codeScore: number;        // 0..300
  hintTier: number;
  pyodideReady: boolean;
  pyodideLoading: boolean;
  errorMessage: string | null;
  /** The serialized output from the puzzle-case test (for comparison) */
  puzzleCaseOutput: string | null;
}

// ---------------------------------------------------------------------------
// Combined game phases
// ---------------------------------------------------------------------------

export type CombinedGamePhase =
  | 'INTRO'
  | 'PLAYING'
  | 'COMPARING'
  | 'COMPLETED';

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

export interface CombinedScoring {
  codeScore: number;          // 0..300
  puzzleScore: number;        // 0..300
  consistencyBonus: number;   // 0 | 100
  totalScore: number;         // 0..700
}

// ---------------------------------------------------------------------------
// Serialization helpers (puzzle state → comparable string)
// ---------------------------------------------------------------------------

export type PuzzleSerializer = (state: GenericPuzzleState) => string;

export function serializeItemSelection(state: GenericPuzzleState): string {
  return [...state.selectedIds].sort().join(',');
}

export function serializeGraphInteraction(state: GenericPuzzleState): string {
  return [...state.selectedEdgeIds].sort().join(',');
}

export function serializeValueAssignment(state: GenericPuzzleState): string {
  return Object.entries(state.assignments)
    .filter(([, v]) => v != null)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join(',');
}

export function serializeSequenceBuilding(state: GenericPuzzleState): string {
  return state.sequence.join(',');
}

export function serializeGridPlacement(state: GenericPuzzleState): string {
  return [...state.placements]
    .sort((a, b) => a.row - b.row || a.col - b.col)
    .map((p) => `(${p.row},${p.col})`)
    .join(',');
}

export function serializeMultisetBuilding(state: GenericPuzzleState): string {
  return [...state.bag].sort().join(',');
}

/** Pick the right serializer based on board type */
export function getSerializerForBoardType(boardType: string): PuzzleSerializer {
  switch (boardType) {
    case 'item_selection': return serializeItemSelection;
    case 'graph_interaction': return serializeGraphInteraction;
    case 'value_assignment': return serializeValueAssignment;
    case 'sequence_building': return serializeSequenceBuilding;
    case 'grid_placement': return serializeGridPlacement;
    case 'multiset_building': return serializeMultisetBuilding;
    default: return serializeItemSelection;
  }
}

/** Normalize output for comparison: lowercase, trim, collapse whitespace */
export function normalizeForComparison(s: string): string {
  return s.toLowerCase().replace(/\s+/g, '').trim();
}
