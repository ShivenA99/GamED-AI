/**
 * CommandHistory - Manages undo/redo stack for game commands
 *
 * Implements the Command Pattern for:
 * - Undo/redo functionality (students can correct mistakes)
 * - Complete audit trail for learning analytics
 * - Replay functionality
 * - Deterministic state reconstruction
 */

import {
  GameCommand,
  CommandHistoryState,
  CommandHistoryEvent,
  CommandHistorySubscriber,
  SerializedCommand,
} from './types';

/**
 * Configuration options for CommandHistory
 */
export interface CommandHistoryOptions {
  /** Maximum number of commands to keep in history (default: 50) */
  maxHistorySize?: number;
  /** Whether to auto-clear redo stack on new command (default: true) */
  clearRedoOnExecute?: boolean;
  /** Callback for command execution (for analytics) */
  onCommandExecute?: (command: GameCommand) => void;
  /** Callback for undo/redo (for analytics) */
  onUndoRedo?: (command: GameCommand, isUndo: boolean) => void;
}

const DEFAULT_OPTIONS: Required<CommandHistoryOptions> = {
  maxHistorySize: 50,
  clearRedoOnExecute: true,
  onCommandExecute: () => {},
  onUndoRedo: () => {},
};

/**
 * CommandHistory manages a stack of executed commands with undo/redo support.
 */
export class CommandHistory {
  private undoStack: GameCommand[] = [];
  private redoStack: GameCommand[] = [];
  private options: Required<CommandHistoryOptions>;
  private subscribers: Set<CommandHistorySubscriber> = new Set();
  private isExecuting: boolean = false;

  constructor(options: CommandHistoryOptions = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options };
  }

  /**
   * Execute a command and add it to the history.
   * Clears the redo stack (new action invalidates future timeline).
   */
  execute(command: GameCommand): boolean {
    // Prevent re-entrancy
    if (this.isExecuting) {
      console.warn('CommandHistory: Cannot execute command while another is executing');
      return false;
    }

    // Check if command can be executed
    if (command.canExecute && !command.canExecute()) {
      return false;
    }

    this.isExecuting = true;
    try {
      // Execute the command
      command.execute();

      // Add to undo stack
      this.undoStack.push(command);

      // Clear redo stack (new action creates new timeline)
      if (this.options.clearRedoOnExecute) {
        this.redoStack = [];
      }

      // Enforce max history size
      while (this.undoStack.length > this.options.maxHistorySize) {
        this.undoStack.shift();
      }

      // Notify subscribers and analytics
      this.notify({ type: 'execute', command });
      this.options.onCommandExecute(command);

      return true;
    } finally {
      this.isExecuting = false;
    }
  }

  /**
   * Undo the most recent command.
   * Returns the undone command, or null if nothing to undo.
   */
  undo(): GameCommand | null {
    if (this.undoStack.length === 0 || this.isExecuting) {
      return null;
    }

    const command = this.undoStack.pop()!;

    // Check if command can be undone
    if (command.canUndo && !command.canUndo()) {
      // Put it back and return null
      this.undoStack.push(command);
      return null;
    }

    this.isExecuting = true;
    try {
      // Undo the command
      command.undo();

      // Move to redo stack
      this.redoStack.push(command);

      // Notify subscribers and analytics
      this.notify({ type: 'undo', command });
      this.options.onUndoRedo(command, true);

      return command;
    } finally {
      this.isExecuting = false;
    }
  }

  /**
   * Redo the most recently undone command.
   * Returns the redone command, or null if nothing to redo.
   */
  redo(): GameCommand | null {
    if (this.redoStack.length === 0 || this.isExecuting) {
      return null;
    }

    const command = this.redoStack.pop()!;

    // Check if command can be executed
    if (command.canExecute && !command.canExecute()) {
      // Put it back and return null
      this.redoStack.push(command);
      return null;
    }

    this.isExecuting = true;
    try {
      // Re-execute the command
      command.execute();

      // Move back to undo stack
      this.undoStack.push(command);

      // Notify subscribers and analytics
      this.notify({ type: 'redo', command });
      this.options.onUndoRedo(command, false);

      return command;
    } finally {
      this.isExecuting = false;
    }
  }

  /**
   * Check if undo is available.
   */
  canUndo(): boolean {
    return this.undoStack.length > 0 && !this.isExecuting;
  }

  /**
   * Check if redo is available.
   */
  canRedo(): boolean {
    return this.redoStack.length > 0 && !this.isExecuting;
  }

  /**
   * Get description of the command that would be undone.
   */
  getUndoDescription(): string | null {
    if (this.undoStack.length === 0) return null;
    return this.undoStack[this.undoStack.length - 1].description;
  }

  /**
   * Get description of the command that would be redone.
   */
  getRedoDescription(): string | null {
    if (this.redoStack.length === 0) return null;
    return this.redoStack[this.redoStack.length - 1].description;
  }

  /**
   * Get current state for UI display.
   */
  getState(): CommandHistoryState {
    return {
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      undoDescription: this.getUndoDescription(),
      redoDescription: this.getRedoDescription(),
      historyLength: this.undoStack.length,
      currentIndex: this.undoStack.length,
    };
  }

  /**
   * Get all commands in the undo stack (for debugging/analytics).
   */
  getHistory(): readonly GameCommand[] {
    return [...this.undoStack];
  }

  /**
   * Get all commands in the redo stack (for debugging).
   */
  getRedoHistory(): readonly GameCommand[] {
    return [...this.redoStack];
  }

  /**
   * Serialize command history for persistence.
   * Commands can implement a serialize() method to provide custom data.
   */
  serialize(): SerializedCommand[] {
    return this.undoStack.map((cmd) => ({
      id: cmd.id,
      type: cmd.type,
      description: cmd.description,
      timestamp: cmd.timestamp,
      data: this.extractCommandData(cmd),
    }));
  }

  /**
   * Extract serializable data from a command.
   * Commands can implement a getData() method for custom serialization.
   */
  private extractCommandData(cmd: GameCommand): Record<string, unknown> {
    // Check if command has a getData method (for custom serialization)
    const cmdWithData = cmd as GameCommand & {
      getData?: () => Record<string, unknown>;
      labelId?: string;
      zoneId?: string;
      labelText?: string;
    };

    if (typeof cmdWithData.getData === 'function') {
      return cmdWithData.getData();
    }

    // Fallback: extract known properties from label commands
    const data: Record<string, unknown> = {};
    if ('labelId' in cmdWithData) data.labelId = cmdWithData.labelId;
    if ('zoneId' in cmdWithData) data.zoneId = cmdWithData.zoneId;
    if ('labelText' in cmdWithData) data.labelText = cmdWithData.labelText;

    return data;
  }

  /**
   * Clear all history.
   */
  clear(): void {
    this.undoStack = [];
    this.redoStack = [];
    this.notify({ type: 'clear' });
  }

  /**
   * Update callback options without clearing history.
   * Useful for updating analytics callbacks when component re-renders.
   */
  updateCallbacks(options: Partial<CommandHistoryOptions>): void {
    if (options.onCommandExecute !== undefined) {
      this.options.onCommandExecute = options.onCommandExecute || (() => {});
    }
    if (options.onUndoRedo !== undefined) {
      this.options.onUndoRedo = options.onUndoRedo || (() => {});
    }
    if (options.maxHistorySize !== undefined) {
      this.options.maxHistorySize = options.maxHistorySize;
    }
    if (options.clearRedoOnExecute !== undefined) {
      this.options.clearRedoOnExecute = options.clearRedoOnExecute;
    }
  }

  /**
   * Subscribe to history changes.
   * Returns unsubscribe function.
   */
  subscribe(subscriber: CommandHistorySubscriber): () => void {
    this.subscribers.add(subscriber);
    return () => {
      this.subscribers.delete(subscriber);
    };
  }

  /**
   * Notify all subscribers of an event.
   */
  private notify(event: CommandHistoryEvent): void {
    this.subscribers.forEach((subscriber) => {
      try {
        subscriber(event);
      } catch (error) {
        console.error('CommandHistory subscriber error:', error);
      }
    });
  }
}

/**
 * Singleton instance for global command history.
 * Use this for the main game, or create separate instances for testing.
 */
let globalHistory: CommandHistory | null = null;

/**
 * Get or create the global command history instance.
 * If options are provided and instance exists, updates callbacks only
 * (to avoid clearing history but allow new analytics callbacks).
 */
export function getCommandHistory(options?: CommandHistoryOptions): CommandHistory {
  if (!globalHistory) {
    globalHistory = new CommandHistory(options);
  } else if (options) {
    // Update callbacks without recreating instance (preserves history)
    globalHistory.updateCallbacks(options);
  }
  return globalHistory;
}

/**
 * Reset the global command history (for testing or new game).
 */
export function resetCommandHistory(options?: CommandHistoryOptions): CommandHistory {
  globalHistory = new CommandHistory(options);
  return globalHistory;
}
