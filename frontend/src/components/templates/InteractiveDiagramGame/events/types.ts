/**
 * Event Sourcing Types for Game Analytics
 *
 * Provides complete audit trail for:
 * - Learning analytics and student progress analysis
 * - Replay functionality
 * - Debugging and testing
 * - Performance metrics
 */

/**
 * Base event type that all game events extend
 */
export interface BaseGameEvent {
  /** Unique event ID */
  id: string;
  /** Event type identifier */
  type: GameEventType;
  /** Wall clock timestamp */
  timestamp: number;
  /** Game time in ms (accounts for pauses) */
  gameTimeMs: number;
  /** Session ID for grouping events */
  sessionId: string;
  /** Blueprint/Game ID */
  gameId?: string;
}

/**
 * All possible game event types
 */
export type GameEventType =
  // Label interactions
  | 'label_placed'
  | 'label_removed'
  | 'label_drag_started'
  | 'label_drag_ended'
  // Zone interactions
  | 'zone_revealed'
  | 'zone_completed'
  | 'zone_hover_entered'
  | 'zone_hover_exited'
  // Game flow
  | 'game_started'
  | 'game_completed'
  | 'game_reset'
  | 'game_paused'
  | 'game_resumed'
  // Scene management
  | 'scene_entered'
  | 'scene_completed'
  | 'scene_exited'
  // User assistance
  | 'hint_requested'
  | 'hint_shown'
  | 'hint_dismissed'
  // Undo/Redo
  | 'undo_action'
  | 'redo_action'
  // Timer events
  | 'timer_started'
  | 'timer_paused'
  | 'timer_resumed'
  | 'timer_expired'
  // Errors
  | 'error_occurred'
  // Custom
  | 'custom';

/**
 * Game paused event
 */
export interface GamePausedEvent extends BaseGameEvent {
  type: 'game_paused';
  data: Record<string, never>;
}

/**
 * Game resumed event
 */
export interface GameResumedEvent extends BaseGameEvent {
  type: 'game_resumed';
  data: Record<string, never>;
}

/**
 * Label placed event
 */
export interface LabelPlacedEvent extends BaseGameEvent {
  type: 'label_placed';
  data: {
    labelId: string;
    labelText: string;
    zoneId: string;
    isCorrect: boolean;
    attemptNumber: number;
    timeToPlaceMs: number;
  };
}

/**
 * Label removed event
 */
export interface LabelRemovedEvent extends BaseGameEvent {
  type: 'label_removed';
  data: {
    labelId: string;
    labelText: string;
    fromZoneId: string;
    wasCorrect: boolean;
    reason: 'user_action' | 'undo' | 'reset';
  };
}

/**
 * Label drag started event
 */
export interface LabelDragStartedEvent extends BaseGameEvent {
  type: 'label_drag_started';
  data: {
    labelId: string;
    labelText: string;
    fromLocation: 'tray' | 'zone';
    fromZoneId?: string;
  };
}

/**
 * Label drag ended event
 */
export interface LabelDragEndedEvent extends BaseGameEvent {
  type: 'label_drag_ended';
  data: {
    labelId: string;
    labelText: string;
    toLocation: 'zone' | 'tray' | 'cancelled';
    toZoneId?: string;
    dragDurationMs: number;
  };
}

/**
 * Zone revealed event
 */
export interface ZoneRevealedEvent extends BaseGameEvent {
  type: 'zone_revealed';
  data: {
    zoneId: string;
    zoneName: string;
    reason: 'initial' | 'parent_completed' | 'mutex_cleared' | 'hierarchy_expanded';
    hierarchyLevel?: number;
    parentZoneId?: string;
  };
}

/**
 * Zone completed event
 */
export interface ZoneCompletedEvent extends BaseGameEvent {
  type: 'zone_completed';
  data: {
    zoneId: string;
    zoneName: string;
    labelId: string;
    timeToCompleteMs: number;
    attemptsCount: number;
    hintsUsed: number;
  };
}

/**
 * Game started event
 */
export interface GameStartedEvent extends BaseGameEvent {
  type: 'game_started';
  data: {
    blueprintId: string;
    templateType: string;
    totalZones: number;
    totalLabels: number;
    interactionMode: string;
    hasTimedChallenge: boolean;
    timeLimitSeconds?: number;
  };
}

/**
 * Game completed event
 */
export interface GameCompletedEvent extends BaseGameEvent {
  type: 'game_completed';
  data: {
    finalScore: number;
    maxScore: number;
    correctPlacements: number;
    incorrectAttempts: number;
    totalTimeMs: number;
    hintsUsed: number;
    undoCount: number;
    redoCount: number;
    timeBonus?: number;
  };
}

/**
 * Hint requested event
 */
export interface HintRequestedEvent extends BaseGameEvent {
  type: 'hint_requested';
  data: {
    hintType: 'zone_highlight' | 'label_hint' | 'general';
    targetZoneId?: string;
    targetLabelId?: string;
    hintNumber: number;
  };
}

/**
 * Undo action event
 */
export interface UndoActionEvent extends BaseGameEvent {
  type: 'undo_action';
  data: {
    undoneCommandType: string;
    undoneCommandDescription: string;
    stackDepth: number;
  };
}

/**
 * Redo action event
 */
export interface RedoActionEvent extends BaseGameEvent {
  type: 'redo_action';
  data: {
    redoneCommandType: string;
    redoneCommandDescription: string;
    stackDepth: number;
  };
}

/**
 * Timer expired event
 */
export interface TimerExpiredEvent extends BaseGameEvent {
  type: 'timer_expired';
  data: {
    timeLimitSeconds: number;
    completedZones: number;
    totalZones: number;
    finalScore: number;
  };
}

/**
 * Error occurred event
 */
export interface ErrorOccurredEvent extends BaseGameEvent {
  type: 'error_occurred';
  data: {
    errorType: string;
    errorMessage: string;
    context?: Record<string, unknown>;
  };
}

/**
 * Scene entered event
 */
export interface SceneEnteredEvent extends BaseGameEvent {
  type: 'scene_entered';
  data: {
    sceneId: string;
    sceneIndex: number;
    totalScenes: number;
    sceneTitle: string;
  };
}

/**
 * Scene completed event
 */
export interface SceneCompletedEvent extends BaseGameEvent {
  type: 'scene_completed';
  data: {
    sceneId: string;
    sceneIndex: number;
    score: number;
    maxScore: number;
    timeSpentMs: number;
  };
}

/**
 * Union type of all game events
 */
export type GameEvent =
  | LabelPlacedEvent
  | LabelRemovedEvent
  | LabelDragStartedEvent
  | LabelDragEndedEvent
  | ZoneRevealedEvent
  | ZoneCompletedEvent
  | GameStartedEvent
  | GameCompletedEvent
  | GamePausedEvent
  | GameResumedEvent
  | HintRequestedEvent
  | UndoActionEvent
  | RedoActionEvent
  | TimerExpiredEvent
  | ErrorOccurredEvent
  | SceneEnteredEvent
  | SceneCompletedEvent
  | (BaseGameEvent & { type: 'custom'; data: Record<string, unknown> });

/**
 * Serialized event for storage/transmission
 */
export interface SerializedGameEvent {
  id: string;
  type: GameEventType;
  timestamp: number;
  gameTimeMs: number;
  sessionId: string;
  gameId?: string;
  data: Record<string, unknown>;
}

/**
 * Analytics summary generated from events
 */
export interface GameAnalyticsSummary {
  sessionId: string;
  gameId?: string;
  startTime: number;
  endTime?: number;
  totalDurationMs: number;
  eventsCount: number;

  // Interaction metrics
  labelPlacements: number;
  correctPlacements: number;
  incorrectAttempts: number;
  labelRemovals: number;

  // Zone metrics
  zonesCompleted: number;
  zonesRevealed: number;

  // Assistance metrics
  hintsUsed: number;
  undoCount: number;
  redoCount: number;

  // Performance metrics
  averageTimePerZoneMs: number;
  averageAttemptsPerZone: number;

  // Final results
  finalScore?: number;
  maxScore?: number;
  completed: boolean;
}
