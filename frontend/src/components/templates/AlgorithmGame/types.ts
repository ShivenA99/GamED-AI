// ============================================================================
// State Tracer Game — Type Definitions
// ============================================================================

// ---------------------------------------------------------------------------
// Prediction types
// ---------------------------------------------------------------------------

export type PredictionType =
  | 'arrangement'
  | 'value'
  | 'multiple_choice'
  | 'multi_select';

export interface ArrangementPrediction {
  type: 'arrangement';
  prompt: string;
  elements: number[];
  correctArrangement: number[];
}

export interface ValuePrediction {
  type: 'value';
  prompt: string;
  correctValue: string;
  acceptableValues?: string[];
  placeholder?: string;
}

export interface MultipleChoicePrediction {
  type: 'multiple_choice';
  prompt: string;
  options: { id: string; label: string }[];
  correctId: string;
}

export interface MultiSelectPrediction {
  type: 'multi_select';
  prompt: string;
  options: { id: string; label: string }[];
  correctIds: string[];
}

export type Prediction =
  | ArrangementPrediction
  | ValuePrediction
  | MultipleChoicePrediction
  | MultiSelectPrediction;

// ---------------------------------------------------------------------------
// Data structure visualization
// ---------------------------------------------------------------------------

export type HighlightColor = 'active' | 'comparing' | 'swapping' | 'sorted' | 'success' | 'error'
  | 'blue' | 'red' | 'green' | 'yellow' | 'purple' | 'orange' | 'cyan' | 'emerald' | 'teal'
  | (string & {}); // Allow any string for LLM-generated colors

export interface ArrayHighlight {
  index: number;
  color: HighlightColor;
  label?: string;
}

export interface ArrayDataStructure {
  type: 'array';
  elements: number[];
  highlights: ArrayHighlight[];
  sortedIndices?: number[];
}

// --- Graph ---

export type GraphNodeState = 'unvisited' | 'in_frontier' | 'current' | 'visited';
export type GraphEdgeState = 'default' | 'exploring' | 'visited' | 'in_result';

export interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  state: GraphNodeState;
}

export interface GraphEdge {
  from: string;
  to: string;
  weight?: number;
  state: GraphEdgeState;
  directed?: boolean;
}

export interface GraphDataStructure {
  type: 'graph';
  nodes: GraphNode[];
  edges: GraphEdge[];
  auxiliary?: { label: string; items: string[] };
}

// --- Tree ---

export type TreeNodeState = 'default' | 'comparing' | 'path' | 'found' | 'inserted';

export interface TreeNode {
  id: string;
  value: number;
  left?: string;
  right?: string;
  children?: string[]; // N-ary tree support
  state: TreeNodeState;
}

export interface TreeDataStructure {
  type: 'tree';
  nodes: TreeNode[];
  root: string;
  highlightPath?: string[];
}

// --- DP Table ---

export type DPCellState = 'empty' | 'filled' | 'computing' | 'read' | 'optimal';

export interface DPCell {
  value: number | string | null;
  state: DPCellState;
}

export interface DPDependency {
  from: [number, number];
  to: [number, number];
}

export interface DPTableDataStructure {
  type: 'dp_table';
  cells: DPCell[][];
  rowLabels?: string[];
  colLabels?: string[];
  activeCell?: [number, number];
  dependencies?: DPDependency[];
}

// --- Stack ---

export type StackItemState = 'default' | 'pushing' | 'popping' | 'top' | 'matched';

export interface StackItem {
  id: string;
  value: string;
  state: StackItemState;
}

export interface StackDataStructure {
  type: 'stack';
  items: StackItem[];
  capacity?: number;
}

// --- Queue ---

export type QueueItemState = 'default' | 'enqueuing' | 'dequeuing' | 'front' | 'back' | 'active';

export interface QueueItem {
  id: string;
  value: string | number;
  state?: QueueItemState;
}

export interface QueueDataStructure {
  type: 'queue';
  items: QueueItem[];
  frontIndex?: number;
  backIndex?: number;
  capacity?: number;
  highlights?: number[];
  variant?: string; // fifo, deque, priority
}

// --- Linked List ---

export type LLNodeState = 'default' | 'current' | 'prev' | 'done';

export interface LLNode {
  id: string;
  value: number | string;
  next: string | null;
  state: LLNodeState;
}

export interface LLPointer {
  name: string;
  target: string | null;
  color: string;
}

export interface LinkedListDataStructure {
  type: 'linked_list';
  nodes: LLNode[];
  head: string | null;
  pointers?: LLPointer[];
}

// --- Heap ---

export interface HeapDataStructure {
  type: 'heap';
  elements: number[];
  heapType: 'min' | 'max';
  highlights: number[];
}

// --- Hash Map ---

export interface HashMapBucketEntry {
  key: string;
  value: any;
}

export interface HashMapDataStructure {
  type: 'hash_map';
  buckets: Array<Array<HashMapBucketEntry>>;
  capacity: number;
  highlights: number[];
}

// --- Custom Object ---

export interface CustomObjectDataStructure {
  type: 'custom';
  fields: Record<string, any>;
  highlights: string[];
  label: string;
}

// --- Union ---

export type DataStructure =
  | ArrayDataStructure
  | GraphDataStructure
  | TreeDataStructure
  | DPTableDataStructure
  | StackDataStructure
  | QueueDataStructure
  | LinkedListDataStructure
  | HeapDataStructure
  | HashMapDataStructure
  | CustomObjectDataStructure;

// ---------------------------------------------------------------------------
// Execution steps
// ---------------------------------------------------------------------------

export interface VariableState {
  name: string;
  value: number | string | boolean | number[] | null;
  changed: boolean;
}

export interface ExecutionStep {
  stepNumber: number;
  codeLine: number;
  description: string;
  variables: Record<string, number | string | boolean | number[] | null>;
  changedVariables: string[];
  dataStructure: DataStructure;
  prediction: ExtendedPrediction | null; // null = auto-advance step (no prediction needed)
  explanation: string;
  hints: [string, string, string]; // [nudge, clue, answer] — 3-tier
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

export interface ScoringConfig {
  basePoints: number;
  streakThresholds: { min: number; multiplier: number }[];
  hintPenalties: [number, number, number]; // [nudge %, clue %, answer %]
  perfectRunBonus: number; // percentage, e.g. 0.20
}

export const DEFAULT_SCORING: ScoringConfig = {
  basePoints: 100,
  streakThresholds: [
    { min: 0, multiplier: 1 },
    { min: 3, multiplier: 1.5 },
    { min: 5, multiplier: 2 },
    { min: 8, multiplier: 3 },
  ],
  hintPenalties: [0.1, 0.2, 0.3], // cumulative percentage
  perfectRunBonus: 0.2,
};

export interface ScoringState {
  totalScore: number;
  streak: number;
  maxStreak: number;
  correctCount: number;
  incorrectCount: number;
  totalPredictions: number;
  hintsUsed: number;
  stepScores: number[];
  hintPenaltiesApplied: number[];
}

// ---------------------------------------------------------------------------
// State machine
// ---------------------------------------------------------------------------

export type GamePhase =
  | 'INIT'
  | 'SHOWING_STATE'
  | 'AWAITING_PREDICTION'
  | 'PREDICTION_SUBMITTED'
  | 'REVEALING_RESULT'
  | 'COMPLETED';

export interface HintState {
  currentTier: number; // 0 = no hints used, 1 = nudge, 2 = clue, 3 = answer
  hintsForStep: string[];
}

export interface PredictionResult {
  isCorrect: boolean;
  partialScore: number; // 0..1 for partial credit
  playerAnswer: number[] | string | string[];
  correctAnswer: number[] | string | string[];
}

export interface GameState {
  phase: GamePhase;
  currentStepIndex: number;
  executedLines: number[];
  scoring: ScoringState;
  hintState: HintState;
  lastResult: PredictionResult | null;
  isPlaying: boolean;
  speed: number;
}

// ---------------------------------------------------------------------------
// Actions for useReducer
// ---------------------------------------------------------------------------

export type GameAction =
  | { type: 'ADVANCE_TO_STEP'; stepIndex: number }
  | { type: 'SHOW_PREDICTION' }
  | { type: 'SUBMIT_PREDICTION'; result: PredictionResult; pointsEarned: number }
  | { type: 'FINISH_REVEAL' }
  | { type: 'USE_HINT'; tier: number }
  | { type: 'COMPLETE_GAME' }
  | { type: 'RESET' }
  | { type: 'SET_PLAYING'; isPlaying: boolean }
  | { type: 'SET_SPEED'; speed: number };

// ---------------------------------------------------------------------------
// Blueprint (top-level data from backend or demo)
// ---------------------------------------------------------------------------

export interface StateTracerBlueprint {
  algorithmName: string;
  algorithmDescription: string;
  narrativeIntro: string;
  code: string;
  language: string;
  steps: ExecutionStep[];
  scoringConfig?: ScoringConfig;
}

// ============================================================================
// Bug Hunter Game — Type Definitions
// ============================================================================

// ---------------------------------------------------------------------------
// Bug types & line states
// ---------------------------------------------------------------------------

export type BugType =
  | 'off_by_one'
  | 'wrong_operator'
  | 'wrong_variable'
  | 'missing_base_case'
  | 'wrong_initialization'
  | 'wrong_return'
  | 'infinite_loop'
  | 'boundary_error'
  | 'logic_error';

export type LineState =
  | 'default'
  | 'hover'
  | 'selected'
  | 'wrong_click'
  | 'fixed'
  | 'current_bug';

// ---------------------------------------------------------------------------
// Blueprint sub-types
// ---------------------------------------------------------------------------

export interface FixOption {
  id: string;
  codeText: string;
  isCorrect: boolean;
  feedback: string;
}

export interface BugDefinition {
  bugId: string;
  bugLines?: number[];                // Multi-line: array of line numbers
  buggyLinesText?: string[];          // Multi-line: array of buggy line strings
  correctLinesText?: string[];        // Multi-line: array of correct line strings
  lineNumber?: number;                // Single-line (backward compat)
  buggyLineText?: string;             // Single-line (backward compat)
  correctLineText?: string;           // Single-line (backward compat)
  bugType: BugType;
  difficulty: 1 | 2 | 3;
  explanation: string;
  bugTypeExplanation: string;
  fixOptions?: FixOption[];           // Optional — only used in MC mode
  hints: [string, string, string];    // [category, location, line]
}

export interface TestCase {
  id: string;
  inputDescription: string;
  expectedOutput: string;
  buggyOutput: string;
  exposedBugs: string[];
}

export interface RedHerring {
  lineNumber: number;
  feedback: string;
}

export type FixMode = 'multiple_choice' | 'free_text';

export interface BugHunterConfig {
  revealSequentially: boolean;
  showTestOutput: boolean;
  showRunButton: boolean;
  fixMode: FixMode;
  maxWrongLineClicks: number;
  roundMode?: boolean;
}

// ---------------------------------------------------------------------------
// Bug Hunter rounds
// ---------------------------------------------------------------------------

export interface BugHunterRound {
  roundId: string;
  title: string;
  buggyCode: string;
  correctCode: string;
  bugs: BugDefinition[];
  testCases: TestCase[];
  redHerrings: RedHerring[];
}

// ---------------------------------------------------------------------------
// Test execution
// ---------------------------------------------------------------------------

export interface TestExecutionResult {
  testId: string;
  passed: boolean;
  actualOutput: string;
  expectedOutput: string;
  error?: string;
}

// ---------------------------------------------------------------------------
// Bug Hunter state machine
// ---------------------------------------------------------------------------

export type BugHunterPhase =
  | 'INIT'
  | 'READING_CODE'
  | 'BUG_HUNTING'
  | 'LINE_SELECTED'
  | 'WRONG_FIX'
  | 'BUG_FIXED'
  | 'VERIFICATION'
  | 'COMPLETED';

export interface BugHunterScoringState {
  totalScore: number;
  bugsFound: number;
  totalBugs: number;
  wrongLineClicks: number;
  wrongFixAttempts: number;
  hintsUsed: number;
  perBugScores: { bugId: string; points: number; attempts: number; hintsUsed: number }[];
  bonuses: { type: string; points: number }[];
}

export interface BugHunterGameState {
  phase: BugHunterPhase;
  currentBugIndex: number;
  currentRoundIndex: number;
  fixedBugIds: string[];
  lineStates: Record<number, LineState>;
  selectedLine: number | null;
  selectedLines: number[];
  scoring: BugHunterScoringState;
  hintTier: number; // 0=none, 1=category, 2=location, 3=line
  feedbackMessage: string | null;
  feedbackType: 'success' | 'error' | 'info' | null;
  wrongFixCount: number; // for current bug
  currentBugAttempts: number; // line click attempts for current bug
  testResults: TestExecutionResult[];
  showTestResults: boolean;
  executionPending: boolean;
}

export type BugHunterAction =
  | { type: 'START_HUNTING' }
  | { type: 'CLICK_LINE'; lineNumber: number }
  | { type: 'SELECT_LINE'; lineNumber: number; multiSelect: boolean }
  | { type: 'CONFIRM_SELECTION' }
  | { type: 'DISMISS_FEEDBACK' }
  | { type: 'SUBMIT_FIX'; fixId: string }
  | { type: 'SUBMIT_FREE_TEXT'; code: string }
  | { type: 'SET_TEST_RESULTS'; results: TestExecutionResult[] }
  | { type: 'ADVANCE_AFTER_FIX' }
  | { type: 'ADVANCE_ROUND' }
  | { type: 'USE_HINT'; tier: number }
  | { type: 'START_VERIFICATION' }
  | { type: 'DISMISS_TEST_RESULTS' }
  | { type: 'SET_EXECUTION_PENDING'; pending: boolean }
  | { type: 'COMPLETE' }
  | { type: 'RESET' };

// ---------------------------------------------------------------------------
// Bug Hunter Blueprint (top-level)
// ---------------------------------------------------------------------------

export interface BugHunterBlueprint {
  algorithmName: string;
  algorithmDescription: string;
  narrativeIntro: string;
  language: string;

  // Single-code mode (backward compat)
  buggyCode?: string;
  correctCode?: string;
  bugs?: BugDefinition[];
  testCases?: TestCase[];
  redHerrings?: RedHerring[];

  // Rounds mode
  rounds?: BugHunterRound[];

  config: BugHunterConfig;
}

// Normalized blueprint — after normalization, always has rounds
export interface NormalizedBugHunterBlueprint {
  algorithmName: string;
  algorithmDescription: string;
  narrativeIntro: string;
  language: string;
  rounds: BugHunterRound[];
  config: BugHunterConfig;
}

// Normalized bug — always has multi-line fields
export interface NormalizedBugDefinition extends BugDefinition {
  bugLines: number[];
  buggyLinesText: string[];
  correctLinesText: string[];
}

// ============================================================================
// Algorithm Builder (Parsons Problems) — Type Definitions
// ============================================================================

// ---------------------------------------------------------------------------
// Parsons block & feedback
// ---------------------------------------------------------------------------

export interface ParsonsBlock {
  id: string;
  code: string;
  indent_level: number; // 0-3
  is_distractor: boolean;
  distractor_explanation?: string;
  group_id?: string; // interchangeable blocks share group_id
}

export type BlockFeedbackStatus =
  | 'correct'
  | 'wrong_position'
  | 'wrong_indent'
  | 'distractor_included'
  | 'distractor_excluded'
  | 'missing'
  | 'neutral';

export interface BlockFeedback {
  blockId: string;
  status: BlockFeedbackStatus;
  correctPosition?: number;
  correctIndent?: number;
  pointsAwarded: number;
}

// ---------------------------------------------------------------------------
// Blueprint sub-types
// ---------------------------------------------------------------------------

export interface AlgorithmBuilderConfig {
  indentation_matters: boolean;
  max_attempts: number | null; // null = unlimited
  show_line_numbers: boolean;
  allow_indent_adjustment: boolean;
}

export interface AlgorithmBuilderTestCase {
  id: string;
  inputDescription: string;
  expectedOutput: string;
  explanation?: string;
}

// ---------------------------------------------------------------------------
// Algorithm Builder Blueprint (top-level)
// ---------------------------------------------------------------------------

export interface AlgorithmBuilderBlueprint {
  algorithmName: string;
  algorithmDescription: string;
  problemDescription: string;
  language: string;
  correct_order: ParsonsBlock[];
  distractors: ParsonsBlock[];
  config: AlgorithmBuilderConfig;
  hints: [string, string, string]; // 3-tier hints
  test_cases?: AlgorithmBuilderTestCase[];
}

// ---------------------------------------------------------------------------
// Algorithm Builder state machine
// ---------------------------------------------------------------------------

export type AlgorithmBuilderPhase =
  | 'INIT'
  | 'BUILDING'
  | 'FEEDBACK_SHOWN'
  | 'COMPLETED';

export interface AlgorithmBuilderScoringState {
  totalScore: number;
  attempts: number;
  hintsUsed: number;
  hintPenalty: number;
  perBlockFeedback: BlockFeedback[];
  bonuses: { type: string; points: number }[];
}

export interface AlgorithmBuilderGameState {
  phase: AlgorithmBuilderPhase;
  sourceBlocks: ParsonsBlock[];
  solutionBlocks: ParsonsBlock[];
  scoring: AlgorithmBuilderScoringState;
  hintTier: number; // 0=none, 1, 2, 3
  feedbackMessage: string | null;
  feedbackType: 'success' | 'error' | 'info' | null;
  activeBlockId: string | null;
}

export type AlgorithmBuilderAction =
  | { type: 'START_BUILDING' }
  | { type: 'MOVE_BLOCK_TO_SOLUTION'; blockId: string; index: number }
  | { type: 'MOVE_BLOCK_TO_SOURCE'; blockId: string }
  | { type: 'REORDER_SOLUTION'; activeId: string; overId: string }
  | { type: 'SET_INDENT'; blockId: string; indent: number }
  | { type: 'SET_ACTIVE_BLOCK'; blockId: string | null }
  | {
      type: 'SUBMIT';
      feedback: BlockFeedback[];
      score: number;
      bonuses: { type: string; points: number }[];
      allCorrect: boolean;
    }
  | { type: 'RETRY' }
  | { type: 'USE_HINT'; tier: number }
  | { type: 'COMPLETE' }
  | { type: 'RESET' };

// ============================================================================
// Complexity Analyzer — Type Definitions
// ============================================================================

// ---------------------------------------------------------------------------
// Challenge types
// ---------------------------------------------------------------------------

export type ComplexityChallengeType =
  | 'identify_from_code'
  | 'infer_from_growth'
  | 'find_bottleneck';

export interface CodeSection {
  sectionId: string;
  label: string;
  startLine: number;
  endLine: number;
  complexity: string;
  isBottleneck: boolean;
}

export interface ComplexityChallenge {
  challengeId: string;
  type: ComplexityChallengeType;
  title: string;
  description?: string;
  code?: string;
  language?: string;
  growthData?: { inputSizes: number[]; operationCounts: number[] };
  codeSections?: CodeSection[];
  correctComplexity: string;
  options: string[];
  explanation: string;
  points: number;
  hints: [string, string, string];
}

// ---------------------------------------------------------------------------
// Blueprint
// ---------------------------------------------------------------------------

export interface ComplexityAnalyzerBlueprint {
  algorithmName: string;
  algorithmDescription: string;
  challenges: ComplexityChallenge[];
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

export interface ComplexityAnalyzerScoringState {
  totalScore: number;
  correctCount: number;
  totalChallenges: number;
  hintsUsed: number;
  perChallenge: {
    challengeId: string;
    correct: boolean;
    points: number;
    attempts: number;
  }[];
  bonuses: { type: string; points: number }[];
}

// ---------------------------------------------------------------------------
// State machine
// ---------------------------------------------------------------------------

export type ComplexityAnalyzerPhase =
  | 'INIT'
  | 'CHALLENGE'
  | 'FEEDBACK'
  | 'COMPLETED';

export interface ComplexityAnalyzerGameState {
  phase: ComplexityAnalyzerPhase;
  currentChallengeIndex: number;
  selectedAnswer: string | null;
  selectedSection: string | null;
  isCorrect: boolean | null;
  scoring: ComplexityAnalyzerScoringState;
  hintTier: number;
  attempts: number;
}

export type ComplexityAnalyzerAction =
  | { type: 'START' }
  | { type: 'SELECT_ANSWER'; answer: string }
  | { type: 'SELECT_SECTION'; sectionId: string }
  | { type: 'SUBMIT' }
  | { type: 'NEXT_CHALLENGE' }
  | { type: 'USE_HINT'; tier: number }
  | { type: 'CA_COMPLETE' }
  | { type: 'CA_RESET' };

// ============================================================================
// Constraint Puzzle — Type Definitions
// ============================================================================

// ---------------------------------------------------------------------------
// Puzzle types
// ---------------------------------------------------------------------------

export type ConstraintPuzzleType =
  | 'knapsack'
  | 'n_queens'
  | 'coin_change'
  | 'activity_selection';

export interface KnapsackItem {
  id: string;
  name: string;
  weight: number;
  value: number;
  icon: string;
}

export interface KnapsackPuzzleData {
  type: 'knapsack';
  capacity: number;
  items: KnapsackItem[];
}

export interface NQueensPuzzleData {
  type: 'n_queens';
  boardSize: number;
  prePlaced?: { row: number; col: number }[];
}

export interface CoinChangePuzzleData {
  type: 'coin_change';
  targetAmount: number;
  denominations: number[];
}

export interface ActivitySelectionItem {
  id: string;
  name: string;
  start: number;
  end: number;
}

export interface ActivitySelectionPuzzleData {
  type: 'activity_selection';
  activities: ActivitySelectionItem[];
}

export type PuzzleData =
  | KnapsackPuzzleData
  | NQueensPuzzleData
  | CoinChangePuzzleData
  | ActivitySelectionPuzzleData;

// ---------------------------------------------------------------------------
// Blueprint
// ---------------------------------------------------------------------------

export interface ConstraintPuzzleBlueprint {
  puzzleType: ConstraintPuzzleType;
  title: string;
  narrative: string;
  rules: string[];
  objective: string;
  puzzleData: PuzzleData;
  optimalValue: number;
  optimalSolutionDescription: string;
  algorithmName: string;
  algorithmExplanation: string;
  showConstraintsVisually: boolean;
  showOptimalityScore: boolean;
  allowUndo: boolean;
  hints: [string, string, string];
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

export interface ConstraintPuzzleScoringState {
  totalScore: number;
  moveCount: number;
  hintsUsed: number;
  optimalityRatio: number;
  bonuses: { type: string; points: number }[];
}

// ---------------------------------------------------------------------------
// State machine
// ---------------------------------------------------------------------------

export type ConstraintPuzzlePhase =
  | 'INIT'
  | 'PLAYING'
  | 'PUZZLE_SOLVED'
  | 'ALGORITHM_REVEAL'
  | 'COMPLETED';

export interface ConstraintPuzzleGameState {
  phase: ConstraintPuzzlePhase;
  selectedItemIds: string[];
  queenPositions: { row: number; col: number }[];
  selectedCoins: number[];
  selectedActivityIds: string[];
  scoring: ConstraintPuzzleScoringState;
  hintTier: number;
  moveHistory: string[];
  feedbackMessage: string | null;
  feedbackType: 'success' | 'error' | 'info' | null;
}

export type ConstraintPuzzleAction =
  | { type: 'CP_START' }
  | { type: 'TOGGLE_ITEM'; itemId: string }
  | { type: 'PLACE_QUEEN'; row: number; col: number }
  | { type: 'REMOVE_QUEEN'; row: number; col: number }
  | { type: 'ADD_COIN'; denomination: number }
  | { type: 'REMOVE_COIN'; index: number }
  | { type: 'TOGGLE_ACTIVITY'; activityId: string }
  | { type: 'CP_UNDO' }
  | { type: 'CHECK_SOLUTION' }
  | { type: 'REVEAL_ALGORITHM' }
  | { type: 'CP_USE_HINT'; tier: number }
  | { type: 'CP_COMPLETE' }
  | { type: 'CP_RESET' };

// ============================================================================
// Generic Constraint Puzzle — Re-exports
// ============================================================================
// New data-driven system. Legacy types above kept for migration compatibility.

export type {
  BoardType,
  BoardConfig,
  SelectableItem,
  ItemSelectionBoardConfig,
  GridPlacementBoardConfig,
  MultisetBuildingBoardConfig,
  GraphInteractionBoardConfig,
  ValueAssignmentBoardConfig,
  SequenceBuildingBoardConfig,
  Constraint,
  ConstraintResult,
  PuzzleScoringConfig,
  GenericConstraintPuzzleBlueprint,
  GenericPuzzleState,
  GenericPuzzleAction,
  BoardRendererProps,
  BoardRegistryEntry,
} from './constraintPuzzle/constraintPuzzleTypes';

// ============================================================================
// Learn / Test Mode Configuration
// ============================================================================

export interface LearnModeConfig {
  auto_reveal_hint_tier_1_after_ms: number | null;
  hint_penalties: [number, number, number];
  partial_credit_multiplier: number;
  show_correct_answer_on_wrong: boolean;
  show_misconceptions_preemptively: boolean;
  scaffolding: Record<string, unknown>;
}

export interface TestModeConfig {
  auto_reveal_hint_tier_1_after_ms: null;
  hint_penalties: [number, number, number];
  partial_credit_multiplier: number;
  show_correct_answer_on_wrong: boolean;
  show_misconceptions_preemptively: boolean;
  time_limit_seconds: number | null;
}

export type GameplayMode = 'learn' | 'test';

// ============================================================================
// Algorithm Game Blueprint (top-level from backend)
// ============================================================================

export interface AlgorithmSceneBlueprint {
  scene_id: string;
  scene_number: number;
  title: string;
  game_type: string;
  difficulty: string;
  learning_goal: string;
  max_score: number;
  content: Record<string, unknown>;
  asset_url?: string | null;
}

export interface AlgorithmGameBlueprint {
  templateType: 'ALGORITHM_GAME';
  title: string;
  subject: string;
  difficulty: string;
  algorithmName: string;
  algorithmCategory: string;
  narrativeIntro: string;
  totalMaxScore: number;
  passThreshold: number;

  learn_config: LearnModeConfig;
  test_config: TestModeConfig;

  // Single-scene
  algorithmGameType?: string;
  stateTracerBlueprint?: StateTracerBlueprint;
  bugHunterBlueprint?: BugHunterBlueprint;
  algorithmBuilderBlueprint?: AlgorithmBuilderBlueprint;
  complexityAnalyzerBlueprint?: ComplexityAnalyzerBlueprint;
  constraintPuzzleBlueprint?: ConstraintPuzzleBlueprint;

  // Multi-scene
  is_multi_scene: boolean;
  scenes?: AlgorithmSceneBlueprint[];
  scene_transitions?: Array<{ from_scene: string; to_scene: string; trigger: string }>;

  // Assets
  scene_assets?: Record<string, { image_url?: string }>;
}

// ============================================================================
// Extended Prediction Types (new)
// ============================================================================

export interface CodeCompletionPrediction {
  type: 'code_completion';
  prompt: string;
  codeTemplate: string;
  correctCode: string;
  acceptableVariants?: string[];
}

export interface TrueFalsePrediction {
  type: 'true_false';
  prompt: string;
  correctAnswer: boolean;
  explanation?: string;
}

// Extended union (includes new types)
export type ExtendedPrediction =
  | Prediction
  | CodeCompletionPrediction
  | TrueFalsePrediction;

// ============================================================================
// Extended Complexity Types
// ============================================================================

export type ComplexityDimension = 'time' | 'space' | 'both';
export type CaseVariant = 'worst' | 'best' | 'average' | 'amortized';

export interface ExtendedComplexityChallenge extends ComplexityChallenge {
  complexityDimension?: ComplexityDimension;
  caseVariant?: CaseVariant;
}
