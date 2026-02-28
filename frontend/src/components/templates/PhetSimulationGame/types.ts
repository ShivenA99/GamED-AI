/**
 * Type definitions for PhET Simulation Game
 */

// =============================================================================
// ENUMS
// =============================================================================

export type AssessmentType =
  | 'exploration'
  | 'parameter_discovery'
  | 'target_achievement'
  | 'prediction_verification'
  | 'comparative_analysis'
  | 'optimization'
  | 'measurement'
  | 'construction'
  | 'sequence_execution';

export type InteractionType =
  | 'slider_adjust'
  | 'button_click'
  | 'drag_drop'
  | 'toggle'
  | 'text_input'
  | 'selection'
  | 'measurement'
  | 'drawing';

export type CheckpointConditionType =
  | 'property_equals'
  | 'property_range'
  | 'property_changed'
  | 'interaction_occurred'
  | 'outcome_achieved'
  | 'time_spent'
  | 'exploration_breadth'
  | 'sequence_completed';

export type BloomsLevel =
  | 'remember'
  | 'understand'
  | 'apply'
  | 'analyze'
  | 'evaluate'
  | 'create';

export type Difficulty = 'easy' | 'medium' | 'hard';

// =============================================================================
// SIMULATION CONFIGURATION
// =============================================================================

export interface SimulationParameter {
  phetioId: string;
  name: string;
  type: 'number' | 'boolean' | 'string' | 'enum';
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
  enumValues?: string[];
  defaultValue?: any;
}

export interface SimulationInteraction {
  id: string;
  type: InteractionType;
  phetioId: string;
  name: string;
  dataFields?: string[];
}

export interface SimulationOutcome {
  id: string;
  name: string;
  phetioId: string;
  unit?: string;
  description?: string;
}

export interface SimulationConfig {
  simulationId: string;
  version: string;
  screen?: string;
  localPath?: string;
  parameters: SimulationParameter[];
  interactions: SimulationInteraction[];
  outcomes: SimulationOutcome[];
  initialState?: Record<string, any>;
  hiddenElements?: string[];
  disabledElements?: string[];
}

// =============================================================================
// ASSESSMENT & CHECKPOINTS
// =============================================================================

export interface CheckpointCondition {
  type: CheckpointConditionType;
  propertyId?: string;
  operator?: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'in_range';
  value?: any;
  minValue?: number;
  maxValue?: number;
  tolerance?: number;
  interactionId?: string;
  interactionData?: Record<string, any>;
  outcomeId?: string;
  minSeconds?: number;
  minUniqueValues?: number;
  parameterIds?: string[];
  sequenceSteps?: string[];
}

export interface Checkpoint {
  id: string;
  description: string;
  conditions: CheckpointCondition[];
  conditionLogic: 'all' | 'any';
  points: number;
  feedback?: string;
  hint?: string;
  requiresPrevious?: string;
}

export interface PredictionQuestion {
  question: string;
  options: string[];
  correctOption?: string;
}

export interface QuizQuestion {
  question: string;
  options: string[];
  correct: string;
  points: number;
  explanation?: string;
}

export interface MeasurementTask {
  id: string;
  label: string;
  outcomeId: string;
  unit?: string;
  expectedValue?: number;
  tolerance?: number;
}

export interface AssessmentTask {
  id: string;
  type: AssessmentType;
  title: string;
  instructions: string;
  learningObjective?: string;
  bloomsLevel?: BloomsLevel;
  checkpoints: Checkpoint[];
  hints?: string[];
  prediction?: PredictionQuestion;
  measurements?: MeasurementTask[];
  requiredToProceed: boolean;
  timeLimit?: number;
  quiz?: QuizQuestion[];
}

// =============================================================================
// SCORING
// =============================================================================

export interface ScoringRubric {
  maxScore: number;
  explorationBonus?: number;
  speedBonus?: Record<string, number>;
  hintPenalty?: number;
  incorrectAttemptPenalty?: number;
  dimensions?: Record<string, number>;
}

// =============================================================================
// ANIMATIONS & FEEDBACK
// =============================================================================

export interface AnimationSpec {
  type: 'pulse' | 'glow' | 'scale' | 'shake' | 'fade' | 'bounce' | 'confetti' | 'highlight';
  duration_ms: number;
  color?: string;
  intensity?: number;
}

export interface FeedbackMessages {
  checkpointComplete: string;
  taskComplete: string;
  incorrectAttempt: string;
  hintUsed: string;
  gameComplete: Record<string, string>;
}

export interface StructuredAnimations {
  checkpointComplete: AnimationSpec;
  incorrectAttempt: AnimationSpec;
  taskComplete: AnimationSpec;
  gameComplete: AnimationSpec;
}

// =============================================================================
// BRIDGE CONFIGURATION
// =============================================================================

export interface BridgeConfig {
  simulationId: string;
  version: string;
  localPath?: string;
  screen?: string;
  trackProperties: Array<{
    name: string;
    phetioId: string;
    type: string;
    unit?: string;
    min?: number;
    max?: number;
  }>;
  trackInteractions: Array<{
    id: string;
    phetioId: string;
    type: string;
    name: string;
    dataFields?: string[];
  }>;
  trackOutcomes: Array<{
    id: string;
    phetioId: string;
    name: string;
    unit?: string;
  }>;
  requiredProperties: string[];
  requiredInteractions: string[];
  requiredOutcomes: string[];
  initialState: Record<string, any>;
  hiddenElements: string[];
  disabledElements: string[];
  messagePrefix: string;
  debounceMs: number;
  batchUpdates: boolean;
  pollIntervalMs?: number;
  usePolling?: boolean;
  emitStateChanges: boolean;
  emitInteractions: boolean;
  emitOutcomes: boolean;
}

// =============================================================================
// MAIN BLUEPRINT
// =============================================================================

export interface PhetSimulationBlueprint {
  templateType: 'PHET_SIMULATION';
  title: string;
  narrativeIntro: string;
  simulation: SimulationConfig;
  assessmentType: AssessmentType;
  tasks: AssessmentTask[];
  scoring: ScoringRubric;
  feedback: FeedbackMessages;
  animations: StructuredAnimations;
  learningObjectives: string[];
  targetBloomsLevel: BloomsLevel;
  estimatedMinutes: number;
  difficulty: Difficulty;
  bridgeConfig?: BridgeConfig;
}

// =============================================================================
// GAME STATE
// =============================================================================

export interface GameState {
  startTime: number;
  currentTaskIndex: number;
  completedCheckpoints: Set<string>;
  completedTasks: Set<string>;
  score: number;
  hintsUsed: number;
  changedProperties: Set<string>;
  exploredValues: Map<string, Set<any>>;
  interactions: PhetInteraction[];
  simulationState: Record<string, any>;
  isComplete: boolean;
  lastActivityTime: number;
}

export interface PhetInteraction {
  id: string;
  type: InteractionType;
  timestamp: number;
  data?: Record<string, any>;
}

export interface CheckpointStatus {
  id: string;
  completed: boolean;
  completedAt?: number;
  pointsAwarded?: number;
}

// =============================================================================
// GAME RESULTS
// =============================================================================

export interface GameResults {
  finalScore: number;
  maxScore: number;
  completedCheckpoints: string[];
  completedTasks: string[];
  hintsUsed: number;
  timeSpentSeconds: number;
  explorationMetrics?: {
    uniqueParameterValues: Record<string, number>;
    totalInteractions: number;
    discoveredRelationships: string[];
  };
}

export interface GameProgress {
  currentTaskIndex: number;
  totalTasks: number;
  completedCheckpoints: string[];
  score: number;
  maxScore: number;
  timeElapsedSeconds: number;
}

// =============================================================================
// COMPONENT PROPS
// =============================================================================

export interface PhetSimulationGameProps {
  blueprint: PhetSimulationBlueprint;
  onComplete?: (results: GameResults) => void;
  onProgress?: (progress: GameProgress) => void;
}

export interface PhetFrameProps {
  simulationId: string;
  localPath?: string;
  screen?: string;
  isReady: boolean;
}

export interface TaskPanelProps {
  task: AssessmentTask;
  completedCheckpoints: Set<string>;
  hintsUsed: number;
  onUseHint: () => void;
}

export interface ScorePanelProps {
  score: number;
  maxScore: number;
  currentTask: number;
  totalTasks: number;
}

export interface CheckpointProgressProps {
  checkpoints: Checkpoint[];
  completedCheckpoints: Set<string>;
}

export interface ResultsPanelProps {
  score: number;
  maxScore: number;
  feedback: FeedbackMessages;
  results: GameResults;
  onRestart: () => void;
}
