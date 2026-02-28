/**
 * Command Pattern exports for Undo/Redo support
 *
 * Provides undoable actions for game interactions with:
 * - Complete audit trail for learning analytics
 * - Replay functionality
 * - Deterministic state reconstruction
 */

// Types
export type {
  GameCommand,
  GameCommandType,
  SerializedCommand,
  CommandResult,
  CommandHistoryState,
  CommandHistoryEvent,
  CommandHistorySubscriber,
} from './types';

// Command History Manager
export {
  CommandHistory,
  getCommandHistory,
  resetCommandHistory,
  type CommandHistoryOptions,
} from './CommandHistory';

// Label Commands
export {
  PlaceLabelCommand,
  createPlaceLabelCommand,
  type LabelStoreActions as PlaceLabelStoreActions,
} from './PlaceLabelCommand';

export {
  RemoveLabelCommand,
  createRemoveLabelCommand,
  type LabelStoreActions as RemoveLabelStoreActions,
} from './RemoveLabelCommand';

// Re-export for convenience
export type { LabelStoreActions } from './PlaceLabelCommand';
