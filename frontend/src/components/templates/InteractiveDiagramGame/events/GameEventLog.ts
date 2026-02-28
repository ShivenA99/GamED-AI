/**
 * GameEventLog - Event Sourcing for Game Analytics
 *
 * Provides:
 * - Complete audit trail of all game interactions
 * - Learning analytics data collection
 * - Replay functionality
 * - Performance metrics
 * - Exportable data for backend analytics
 */

import {
  GameEvent,
  GameEventType,
  BaseGameEvent,
  SerializedGameEvent,
  GameAnalyticsSummary,
  LabelPlacedEvent,
  LabelRemovedEvent,
  ZoneCompletedEvent,
  GameCompletedEvent,
} from './types';

/**
 * Configuration for GameEventLog
 */
export interface GameEventLogOptions {
  /** Maximum events to keep in memory (default: 1000) */
  maxEvents?: number;
  /** Session ID (auto-generated if not provided) */
  sessionId?: string;
  /** Game/Blueprint ID */
  gameId?: string;
  /** Auto-persist to localStorage (default: false) */
  autoPersist?: boolean;
  /** localStorage key prefix (default: 'gamed-events') */
  persistenceKey?: string;
  /** Callback when event is logged */
  onEvent?: (event: GameEvent) => void;
}

const DEFAULT_OPTIONS: Required<Omit<GameEventLogOptions, 'onEvent' | 'gameId'>> = {
  maxEvents: 1000,
  sessionId: '',
  autoPersist: false,
  persistenceKey: 'gamed-events',
};

/**
 * Generates a unique session ID
 */
function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Generates a unique event ID
 */
function generateEventId(): string {
  return `evt_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * GameEventLog - Manages event logging for game analytics
 */
export class GameEventLog {
  private events: GameEvent[] = [];
  private options: Required<Omit<GameEventLogOptions, 'onEvent' | 'gameId'>> & {
    onEvent?: (event: GameEvent) => void;
    gameId?: string;
  };
  private startTime: number;
  private gameStartTime: number = 0;
  private isPaused: boolean = false;
  private pausedAt: number = 0;
  private totalPausedTime: number = 0;

  // Metrics tracking
  private labelAttempts: Map<string, number> = new Map();
  private zoneStartTimes: Map<string, number> = new Map();
  private dragStartTimes: Map<string, number> = new Map();

  constructor(options: GameEventLogOptions = {}) {
    this.options = {
      ...DEFAULT_OPTIONS,
      ...options,
      sessionId: options.sessionId || generateSessionId(),
    };
    this.startTime = Date.now();
    this.gameStartTime = this.startTime;

    // Load persisted events if enabled
    if (this.options.autoPersist) {
      this.loadPersistedEvents();
    }
  }

  /**
   * Get current game time (accounts for pauses)
   */
  getGameTime(): number {
    if (this.isPaused) {
      return this.pausedAt - this.gameStartTime - this.totalPausedTime;
    }
    return Date.now() - this.gameStartTime - this.totalPausedTime;
  }

  /**
   * Log a game event
   */
  log<T extends GameEvent>(
    type: T['type'],
    data: T extends BaseGameEvent & { data: infer D } ? D : Record<string, unknown>
  ): T {
    const event = {
      id: generateEventId(),
      type,
      timestamp: Date.now(),
      gameTimeMs: this.getGameTime(),
      sessionId: this.options.sessionId,
      gameId: this.options.gameId,
      data,
    } as T;

    this.events.push(event);

    // Enforce max events limit
    while (this.events.length > this.options.maxEvents) {
      this.events.shift();
    }

    // Auto-persist if enabled
    if (this.options.autoPersist) {
      this.persistEvents();
    }

    // Notify callback
    this.options.onEvent?.(event);

    return event;
  }

  /**
   * Log label placed event with automatic attempt tracking
   */
  logLabelPlaced(
    labelId: string,
    labelText: string,
    zoneId: string,
    isCorrect: boolean
  ): LabelPlacedEvent {
    // Track attempts
    const currentAttempts = this.labelAttempts.get(labelId) || 0;
    this.labelAttempts.set(labelId, currentAttempts + 1);

    // Calculate time to place (from drag start if available)
    const dragStartTime = this.dragStartTimes.get(labelId);
    const timeToPlaceMs = dragStartTime ? Date.now() - dragStartTime : 0;
    this.dragStartTimes.delete(labelId);

    return this.log<LabelPlacedEvent>('label_placed', {
      labelId,
      labelText,
      zoneId,
      isCorrect,
      attemptNumber: currentAttempts + 1,
      timeToPlaceMs,
    });
  }

  /**
   * Log label removed event
   */
  logLabelRemoved(
    labelId: string,
    labelText: string,
    fromZoneId: string,
    wasCorrect: boolean,
    reason: 'user_action' | 'undo' | 'reset' = 'user_action'
  ): LabelRemovedEvent {
    return this.log<LabelRemovedEvent>('label_removed', {
      labelId,
      labelText,
      fromZoneId,
      wasCorrect,
      reason,
    });
  }

  /**
   * Log drag started event
   */
  logDragStarted(
    labelId: string,
    labelText: string,
    fromLocation: 'tray' | 'zone',
    fromZoneId?: string
  ): void {
    this.dragStartTimes.set(labelId, Date.now());
    this.log('label_drag_started', {
      labelId,
      labelText,
      fromLocation,
      fromZoneId,
    });
  }

  /**
   * Log drag ended event
   */
  logDragEnded(
    labelId: string,
    labelText: string,
    toLocation: 'zone' | 'tray' | 'cancelled',
    toZoneId?: string
  ): void {
    const dragStartTime = this.dragStartTimes.get(labelId);
    const dragDurationMs = dragStartTime ? Date.now() - dragStartTime : 0;

    if (toLocation !== 'zone') {
      this.dragStartTimes.delete(labelId);
    }

    this.log('label_drag_ended', {
      labelId,
      labelText,
      toLocation,
      toZoneId,
      dragDurationMs,
    });
  }

  /**
   * Log zone revealed event
   */
  logZoneRevealed(
    zoneId: string,
    zoneName: string,
    reason: 'initial' | 'parent_completed' | 'mutex_cleared' | 'hierarchy_expanded',
    hierarchyLevel?: number,
    parentZoneId?: string
  ): void {
    this.zoneStartTimes.set(zoneId, Date.now());
    this.log('zone_revealed', {
      zoneId,
      zoneName,
      reason,
      hierarchyLevel,
      parentZoneId,
    });
  }

  /**
   * Log zone completed event
   */
  logZoneCompleted(
    zoneId: string,
    zoneName: string,
    labelId: string,
    hintsUsed: number = 0
  ): ZoneCompletedEvent {
    const startTime = this.zoneStartTimes.get(zoneId);
    const timeToCompleteMs = startTime ? Date.now() - startTime : 0;
    const attemptsCount = this.labelAttempts.get(labelId) || 1;

    return this.log<ZoneCompletedEvent>('zone_completed', {
      zoneId,
      zoneName,
      labelId,
      timeToCompleteMs,
      attemptsCount,
      hintsUsed,
    });
  }

  /**
   * Log game started event
   */
  logGameStarted(
    blueprintId: string,
    templateType: string,
    totalZones: number,
    totalLabels: number,
    interactionMode: string,
    hasTimedChallenge: boolean,
    timeLimitSeconds?: number
  ): void {
    this.gameStartTime = Date.now();
    this.totalPausedTime = 0;
    this.isPaused = false;
    this.labelAttempts.clear();
    this.zoneStartTimes.clear();
    this.dragStartTimes.clear();

    this.log('game_started', {
      blueprintId,
      templateType,
      totalZones,
      totalLabels,
      interactionMode,
      hasTimedChallenge,
      timeLimitSeconds,
    });
  }

  /**
   * Log game completed event
   */
  logGameCompleted(
    finalScore: number,
    maxScore: number,
    correctPlacements: number,
    incorrectAttempts: number,
    hintsUsed: number,
    undoCount: number,
    redoCount: number,
    timeBonus?: number
  ): GameCompletedEvent {
    return this.log<GameCompletedEvent>('game_completed', {
      finalScore,
      maxScore,
      correctPlacements,
      incorrectAttempts,
      totalTimeMs: this.getGameTime(),
      hintsUsed,
      undoCount,
      redoCount,
      timeBonus,
    });
  }

  /**
   * Log hint requested event
   */
  logHintRequested(
    hintType: 'zone_highlight' | 'label_hint' | 'general',
    targetZoneId?: string,
    targetLabelId?: string
  ): void {
    const hintEvents = this.events.filter((e) => e.type === 'hint_requested');
    this.log('hint_requested', {
      hintType,
      targetZoneId,
      targetLabelId,
      hintNumber: hintEvents.length + 1,
    });
  }

  /**
   * Log undo action
   */
  logUndo(undoneCommandType: string, undoneCommandDescription: string, stackDepth: number): void {
    this.log('undo_action', {
      undoneCommandType,
      undoneCommandDescription,
      stackDepth,
    });
  }

  /**
   * Log redo action
   */
  logRedo(redoneCommandType: string, redoneCommandDescription: string, stackDepth: number): void {
    this.log('redo_action', {
      redoneCommandType,
      redoneCommandDescription,
      stackDepth,
    });
  }

  /**
   * Log game paused
   */
  logPaused(): void {
    if (!this.isPaused) {
      this.isPaused = true;
      this.pausedAt = Date.now();
      this.log('game_paused', {});
    }
  }

  /**
   * Log game resumed
   */
  logResumed(): void {
    if (this.isPaused) {
      this.totalPausedTime += Date.now() - this.pausedAt;
      this.isPaused = false;
      this.log('game_resumed', {});
    }
  }

  /**
   * Log error
   */
  logError(errorType: string, errorMessage: string, context?: Record<string, unknown>): void {
    this.log('error_occurred', {
      errorType,
      errorMessage,
      context,
    });
  }

  /**
   * Get all events
   */
  getEvents(): readonly GameEvent[] {
    return [...this.events];
  }

  /**
   * Get events by type
   */
  getEventsByType<T extends GameEventType>(type: T): GameEvent[] {
    return this.events.filter((e) => e.type === type);
  }

  /**
   * Get events in time range
   */
  getEventsInRange(startMs: number, endMs: number): GameEvent[] {
    return this.events.filter(
      (e) => e.gameTimeMs >= startMs && e.gameTimeMs <= endMs
    );
  }

  /**
   * Generate analytics summary
   */
  generateSummary(): GameAnalyticsSummary {
    const labelPlacements = this.events.filter((e) => e.type === 'label_placed');
    const correctPlacements = labelPlacements.filter(
      (e) => (e as LabelPlacedEvent).data.isCorrect
    ).length;
    const zonesCompleted = this.events.filter((e) => e.type === 'zone_completed');
    const zonesRevealed = this.events.filter((e) => e.type === 'zone_revealed');
    const hints = this.events.filter((e) => e.type === 'hint_requested');
    const undos = this.events.filter((e) => e.type === 'undo_action');
    const redos = this.events.filter((e) => e.type === 'redo_action');
    const gameCompleted = this.events.find((e) => e.type === 'game_completed') as
      | GameCompletedEvent
      | undefined;

    const totalTimeMs = this.getGameTime();

    return {
      sessionId: this.options.sessionId,
      gameId: this.options.gameId,
      startTime: this.startTime,
      endTime: gameCompleted?.timestamp,
      totalDurationMs: totalTimeMs,
      eventsCount: this.events.length,

      labelPlacements: labelPlacements.length,
      correctPlacements,
      incorrectAttempts: labelPlacements.length - correctPlacements,
      labelRemovals: this.events.filter((e) => e.type === 'label_removed').length,

      zonesCompleted: zonesCompleted.length,
      zonesRevealed: zonesRevealed.length,

      hintsUsed: hints.length,
      undoCount: undos.length,
      redoCount: redos.length,

      averageTimePerZoneMs:
        zonesCompleted.length > 0
          ? zonesCompleted.reduce(
              (sum, e) => sum + (e as ZoneCompletedEvent).data.timeToCompleteMs,
              0
            ) / zonesCompleted.length
          : 0,
      averageAttemptsPerZone:
        zonesCompleted.length > 0
          ? zonesCompleted.reduce(
              (sum, e) => sum + (e as ZoneCompletedEvent).data.attemptsCount,
              0
            ) / zonesCompleted.length
          : 0,

      finalScore: gameCompleted?.data.finalScore,
      maxScore: gameCompleted?.data.maxScore,
      completed: !!gameCompleted,
    };
  }

  /**
   * Export events for transmission to backend
   */
  export(): SerializedGameEvent[] {
    return this.events.map((event) => ({
      id: event.id,
      type: event.type,
      timestamp: event.timestamp,
      gameTimeMs: event.gameTimeMs,
      sessionId: event.sessionId,
      gameId: event.gameId,
      data: 'data' in event ? (event.data as Record<string, unknown>) : {},
    }));
  }

  /**
   * Clear all events
   */
  clear(): void {
    this.events = [];
    this.labelAttempts.clear();
    this.zoneStartTimes.clear();
    this.dragStartTimes.clear();

    if (this.options.autoPersist) {
      this.clearPersistedEvents();
    }
  }

  /**
   * Persist events to localStorage
   */
  private persistEvents(): void {
    if (typeof localStorage === 'undefined') return;

    try {
      const key = `${this.options.persistenceKey}-${this.options.sessionId}`;
      localStorage.setItem(key, JSON.stringify(this.export()));
    } catch (error) {
      console.warn('Failed to persist events:', error);
    }
  }

  /**
   * Load events from localStorage
   */
  private loadPersistedEvents(): void {
    if (typeof localStorage === 'undefined') return;

    try {
      const key = `${this.options.persistenceKey}-${this.options.sessionId}`;
      const stored = localStorage.getItem(key);
      if (stored) {
        const events = JSON.parse(stored) as SerializedGameEvent[];
        // Reconstruct events (basic restoration)
        this.events = events.map((e) => ({
          ...e,
          data: e.data,
        })) as GameEvent[];
      }
    } catch (error) {
      console.warn('Failed to load persisted events:', error);
    }
  }

  /**
   * Clear persisted events from localStorage
   */
  private clearPersistedEvents(): void {
    if (typeof localStorage === 'undefined') return;

    try {
      const key = `${this.options.persistenceKey}-${this.options.sessionId}`;
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('Failed to clear persisted events:', error);
    }
  }
}

/**
 * Singleton instance for global event logging
 */
let globalEventLog: GameEventLog | null = null;

/**
 * Get or create the global event log instance
 */
export function getEventLog(options?: GameEventLogOptions): GameEventLog {
  if (!globalEventLog) {
    globalEventLog = new GameEventLog(options);
  }
  return globalEventLog;
}

/**
 * Reset the global event log (for new game session)
 */
export function resetEventLog(options?: GameEventLogOptions): GameEventLog {
  globalEventLog = new GameEventLog(options);
  return globalEventLog;
}
