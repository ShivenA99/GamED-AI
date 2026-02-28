// ============================================================================
// Generic Constraint Puzzle — Type Definitions
// ============================================================================
// Data-driven system: backend generates blueprint, frontend renders generically.
// Any algorithm/optimization problem becomes a constraint puzzle via config.
// ============================================================================

// ---------------------------------------------------------------------------
// Board Types — 6 board types cover 95%+ of algorithmic puzzles
// ---------------------------------------------------------------------------

export type BoardType =
  | 'item_selection'
  | 'grid_placement'
  | 'multiset_building'
  | 'graph_interaction'
  | 'value_assignment'
  | 'sequence_building';

// ---------------------------------------------------------------------------
// Selectable Items (shared by item_selection)
// ---------------------------------------------------------------------------

export interface SelectableItem {
  id: string;
  label: string;
  icon?: string;
  /** Arbitrary numeric/string properties, e.g. { weight: 7, value: 10 } */
  properties: Record<string, number | string>;
}

// ---------------------------------------------------------------------------
// Board Configs (discriminated union on boardType)
// ---------------------------------------------------------------------------

export interface ItemSelectionBoardConfig {
  boardType: 'item_selection';
  items: SelectableItem[];
  /** Which property keys to show as columns, e.g. ['weight', 'value'] */
  displayColumns?: string[];
  /** Human-readable labels for property keys, e.g. { weight: 'Weight (kg)' } */
  propertyLabels?: Record<string, string>;
  layout?: 'grid' | 'list';
}

export interface GridPlacementBoardConfig {
  boardType: 'grid_placement';
  rows: number;
  cols: number;
  pieceIcon?: string;
  prePopulated?: { row: number; col: number; locked?: boolean }[];
  highlightThreats?: boolean;
}

export interface MultisetBuildingBoardConfig {
  boardType: 'multiset_building';
  pool: {
    id: string;
    value: number | string;
    label?: string;
    icon?: string;
    maxCount?: number;
  }[];
  targetDisplay?: 'progress_bar' | 'counter' | 'none';
  targetLabel?: string;
}

export interface GraphInteractionBoardConfig {
  boardType: 'graph_interaction';
  nodes: { id: string; label: string; x: number; y: number }[];
  edges: {
    id: string;
    from: string;
    to: string;
    weight?: number;
    directed?: boolean;
  }[];
  selectionMode: 'nodes' | 'edges' | 'both';
}

export interface ValueAssignmentBoardConfig {
  boardType: 'value_assignment';
  slots: { id: string; label: string; neighbors?: string[] }[];
  domain: (string | number)[];
  domainColors?: Record<string, string>;
  layout?: 'graph' | 'grid' | 'list';
}

export interface SequenceBuildingBoardConfig {
  boardType: 'sequence_building';
  items: { id: string; label: string; icon?: string }[];
  showArrows?: boolean;
}

export type BoardConfig =
  | ItemSelectionBoardConfig
  | GridPlacementBoardConfig
  | MultisetBuildingBoardConfig
  | GraphInteractionBoardConfig
  | ValueAssignmentBoardConfig
  | SequenceBuildingBoardConfig;

// ---------------------------------------------------------------------------
// Declarative Constraints
// ---------------------------------------------------------------------------

export type Constraint =
  | { type: 'capacity'; property: string; max: number; label?: string; showBar?: boolean }
  | { type: 'exact_target'; property?: string; target: number; showBar?: boolean }
  | { type: 'no_overlap'; startProperty: string; endProperty: string }
  | { type: 'no_conflict'; conflictRule: 'row_col_diagonal' | 'row_col' | 'adjacent' }
  | { type: 'count_exact'; count: number; label?: string }
  | { type: 'count_range'; min?: number; max?: number }
  | { type: 'all_different'; scope?: 'neighbors' | 'row' | 'col' | 'all' }
  | { type: 'all_assigned' }
  | { type: 'connected' };

export interface ConstraintResult {
  constraint: Constraint;
  satisfied: boolean;
  message: string;
  /** For capacity/target constraints, the current numeric value */
  currentValue?: number;
  /** For capacity/target constraints, the max/target value */
  targetValue?: number;
}

// ---------------------------------------------------------------------------
// Scoring Config
// ---------------------------------------------------------------------------

export type PuzzleScoringConfig =
  | { method: 'sum_property'; property: string }
  | { method: 'count' }
  | { method: 'inverse_count'; numerator: number }
  | { method: 'binary'; successValue: number }
  | { method: 'ratio'; total: number }
  | { method: 'weighted_sum'; valueProperty: string; weightProperty: string };

// ---------------------------------------------------------------------------
// Generic Blueprint
// ---------------------------------------------------------------------------

export interface GenericConstraintPuzzleBlueprint {
  title: string;
  narrative: string;
  rules: string[];
  objective: string;
  boardConfig: BoardConfig;
  constraints: Constraint[];
  scoringConfig: PuzzleScoringConfig;
  optimalValue: number;
  optimalSolutionDescription: string;
  algorithmName: string;
  algorithmExplanation: string;
  showConstraintsVisually: boolean;
  allowUndo: boolean;
  hints: [string, string, string];
  icon?: string;
}

// ---------------------------------------------------------------------------
// Generic Puzzle State
// ---------------------------------------------------------------------------

export type ConstraintPuzzlePhase =
  | 'INIT'
  | 'PLAYING'
  | 'PUZZLE_SOLVED'
  | 'ALGORITHM_REVEAL'
  | 'COMPLETED';

export interface ConstraintPuzzleScoringState {
  totalScore: number;
  moveCount: number;
  hintsUsed: number;
  optimalityRatio: number;
  bonuses: { type: string; points: number }[];
}

export interface GenericPuzzleState {
  phase: ConstraintPuzzlePhase;
  // Board-specific selection state (only the relevant fields are populated)
  selectedIds: string[];
  placements: { row: number; col: number }[];
  bag: (number | string)[];
  selectedEdgeIds: string[];
  assignments: Record<string, string | number | null>;
  sequence: string[];
  // Common state
  scoring: ConstraintPuzzleScoringState;
  hintTier: number;
  moveHistory: string[];
  feedbackMessage: string | null;
  feedbackType: 'success' | 'error' | 'info' | null;
  constraintResults: ConstraintResult[];
}

// ---------------------------------------------------------------------------
// Generic Actions
// ---------------------------------------------------------------------------

export type GenericPuzzleAction =
  // Lifecycle
  | { type: 'CP_START' }
  | { type: 'CP_UNDO' }
  | { type: 'CHECK_SOLUTION' }
  | { type: 'REVEAL_ALGORITHM' }
  | { type: 'CP_USE_HINT'; tier: number }
  | { type: 'CP_COMPLETE' }
  | { type: 'CP_RESET' }
  // item_selection / graph_interaction (nodes)
  | { type: 'TOGGLE'; id: string }
  // grid_placement
  | { type: 'PLACE'; row: number; col: number }
  | { type: 'REMOVE_PLACEMENT'; row: number; col: number }
  // multiset_building
  | { type: 'ADD_TO_BAG'; value: number | string }
  | { type: 'REMOVE_FROM_BAG'; index: number }
  // graph_interaction (edges)
  | { type: 'SELECT_EDGE'; edgeId: string }
  | { type: 'DESELECT_EDGE'; edgeId: string }
  // value_assignment
  | { type: 'ASSIGN'; slotId: string; value: string | number }
  | { type: 'CLEAR_ASSIGNMENT'; slotId: string }
  // sequence_building
  | { type: 'SET_SEQUENCE'; sequence: string[] }
  | { type: 'ADD_TO_SEQUENCE'; id: string }
  | { type: 'REMOVE_FROM_SEQUENCE'; id: string };

// ---------------------------------------------------------------------------
// Board Registry Entry Interface
// ---------------------------------------------------------------------------

export interface BoardRendererProps {
  config: BoardConfig;
  state: GenericPuzzleState;
  dispatch: React.Dispatch<GenericPuzzleAction>;
  constraints: Constraint[];
  constraintResults: ConstraintResult[];
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

export interface BoardRegistryEntry {
  component: React.ComponentType<BoardRendererProps>;
  getInitialBoardState: (config: BoardConfig) => Partial<GenericPuzzleState>;
}
