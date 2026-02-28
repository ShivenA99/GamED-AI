/**
 * Event Sourcing exports for Game Analytics
 *
 * Provides complete audit trail for:
 * - Learning analytics
 * - Replay functionality
 * - Debugging and testing
 * - Performance metrics
 */

// Types
export type {
  BaseGameEvent,
  GameEvent,
  GameEventType,
  SerializedGameEvent,
  GameAnalyticsSummary,
  // Specific event types
  LabelPlacedEvent,
  LabelRemovedEvent,
  LabelDragStartedEvent,
  LabelDragEndedEvent,
  ZoneRevealedEvent,
  ZoneCompletedEvent,
  GameStartedEvent,
  GameCompletedEvent,
  GamePausedEvent,
  GameResumedEvent,
  HintRequestedEvent,
  UndoActionEvent,
  RedoActionEvent,
  TimerExpiredEvent,
  ErrorOccurredEvent,
  SceneEnteredEvent,
  SceneCompletedEvent,
} from './types';

// Event Log
export {
  GameEventLog,
  getEventLog,
  resetEventLog,
  type GameEventLogOptions,
} from './GameEventLog';
