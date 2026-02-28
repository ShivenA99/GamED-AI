/**
 * Command Pattern Types for Undo/Redo Support
 *
 * Based on industry-standard game architecture patterns.
 * Enables complete audit trail, replay systems, and learning analytics.
 */

/**
 * Base command interface that all game commands must implement.
 * Commands encapsulate actions that can be executed and undone.
 */
export interface GameCommand {
  /** Unique identifier for the command */
  readonly id: string;

  /** Human-readable description for UI display */
  readonly description: string;

  /** Timestamp when command was created */
  readonly timestamp: number;

  /** Command type for serialization/analytics */
  readonly type: GameCommandType;

  /** Execute the command (do the action) */
  execute(): void;

  /** Undo the command (reverse the action) */
  undo(): void;

  /** Optional: Check if command can be executed */
  canExecute?(): boolean;

  /** Optional: Check if command can be undone */
  canUndo?(): boolean;

  /** Optional: Merge with another command (for combining rapid actions) */
  merge?(other: GameCommand): GameCommand | null;
}

/**
 * Command types for analytics and serialization
 */
export type GameCommandType =
  | 'place_label'
  | 'remove_label'
  | 'toggle_hints'
  | 'reset_game'
  | 'complete_path'
  | 'identify_zone'
  | 'expand_hierarchy'
  | 'match_description'
  | 'composite'; // For grouped commands

/**
 * Serializable command data for persistence and analytics
 */
export interface SerializedCommand {
  id: string;
  type: GameCommandType;
  description: string;
  timestamp: number;
  data: Record<string, unknown>;
}

/**
 * Command execution result for validation
 */
export interface CommandResult {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
}

/**
 * Command history state for UI display
 */
export interface CommandHistoryState {
  canUndo: boolean;
  canRedo: boolean;
  undoDescription: string | null;
  redoDescription: string | null;
  historyLength: number;
  currentIndex: number;
}

/**
 * Command history event types for subscriptions
 */
export type CommandHistoryEvent =
  | { type: 'execute'; command: GameCommand }
  | { type: 'undo'; command: GameCommand }
  | { type: 'redo'; command: GameCommand }
  | { type: 'clear' };

/**
 * Subscriber callback type
 */
export type CommandHistorySubscriber = (event: CommandHistoryEvent) => void;
