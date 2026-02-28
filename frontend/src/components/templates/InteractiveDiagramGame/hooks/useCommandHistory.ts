/**
 * useCommandHistory - Hook for integrating Command Pattern with game state
 *
 * Provides React integration for the command history system with:
 * - Automatic state synchronization
 * - Keyboard shortcuts (Ctrl+Z / Cmd+Z for undo, Ctrl+Y / Cmd+Shift+Z for redo)
 * - UI state updates for undo/redo buttons
 */

import { useCallback, useEffect, useState, useMemo, useRef } from 'react';
import {
  CommandHistory,
  CommandHistoryState,
  CommandHistoryOptions,
  getCommandHistory,
  resetCommandHistory,
  GameCommand,
} from '../commands';
import { PlaceLabelCommand, LabelStoreActions } from '../commands/PlaceLabelCommand';
import { RemoveLabelCommand } from '../commands/RemoveLabelCommand';
import { useInteractiveDiagramState } from './useInteractiveDiagramState';

/**
 * Hook options for command history integration
 */
export interface UseCommandHistoryOptions extends CommandHistoryOptions {
  /** Enable keyboard shortcuts (default: true) */
  enableKeyboardShortcuts?: boolean;
  /** Enable analytics callbacks (default: false) */
  enableAnalytics?: boolean;
  /** Analytics callback for command events */
  onAnalyticsEvent?: (event: CommandAnalyticsEvent) => void;
}

/**
 * Analytics event for command tracking
 */
export interface CommandAnalyticsEvent {
  type: 'execute' | 'undo' | 'redo';
  commandType: string;
  commandDescription: string;
  timestamp: number;
  gameTimeMs?: number;
}

/**
 * Return type for the hook
 */
export interface UseCommandHistoryReturn {
  /** Execute a command */
  execute: (command: GameCommand) => boolean;
  /** Undo the last command */
  undo: () => GameCommand | null;
  /** Redo the last undone command */
  redo: () => GameCommand | null;
  /** Current history state for UI */
  historyState: CommandHistoryState;
  /** Clear all history */
  clear: () => void;
  /** Get the command history instance */
  getHistory: () => CommandHistory;
  /** Check if undo is available */
  canUndo: boolean;
  /** Check if redo is available */
  canRedo: boolean;
}

const DEFAULT_OPTIONS: UseCommandHistoryOptions = {
  maxHistorySize: 50,
  enableKeyboardShortcuts: true,
  enableAnalytics: false,
};

/**
 * Hook for using command history with React components.
 * Provides undo/redo functionality with keyboard shortcuts and UI state.
 */
export function useCommandHistory(
  options: UseCommandHistoryOptions = {}
): UseCommandHistoryReturn {
  // Memoize options to prevent unnecessary effect reruns
  const mergedOptions = useMemo(
    () => ({ ...DEFAULT_OPTIONS, ...options }),
    [
      options.maxHistorySize,
      options.enableKeyboardShortcuts,
      options.enableAnalytics,
      options.clearRedoOnExecute,
      // Note: callbacks are handled separately via refs
    ]
  );

  // Store callbacks in refs to avoid effect dependencies
  const onCommandExecuteRef = useRef(options.onCommandExecute);
  const onUndoRedoRef = useRef(options.onUndoRedo);
  const onAnalyticsEventRef = useRef(options.onAnalyticsEvent);

  // Keep refs updated
  useEffect(() => {
    onCommandExecuteRef.current = options.onCommandExecute;
    onUndoRedoRef.current = options.onUndoRedo;
    onAnalyticsEventRef.current = options.onAnalyticsEvent;
  }, [options.onCommandExecute, options.onUndoRedo, options.onAnalyticsEvent]);

  // Create or get command history instance
  const [history] = useState<CommandHistory>(() => {
    return getCommandHistory({
      maxHistorySize: mergedOptions.maxHistorySize,
      onCommandExecute: (cmd) => onCommandExecuteRef.current?.(cmd),
      onUndoRedo: (cmd, isUndo) => onUndoRedoRef.current?.(cmd, isUndo),
    });
  });

  // Track history state for React reactivity
  const [historyState, setHistoryState] = useState<CommandHistoryState>(
    history.getState()
  );

  // Subscribe to history changes
  useEffect(() => {
    const unsubscribe = history.subscribe((event) => {
      // Update React state when history changes
      setHistoryState(history.getState());

      // Fire analytics event if enabled
      if (mergedOptions.enableAnalytics && onAnalyticsEventRef.current) {
        if (event.type !== 'clear') {
          onAnalyticsEventRef.current({
            type: event.type,
            commandType: event.command.type,
            commandDescription: event.command.description,
            timestamp: Date.now(),
          });
        }
      }
    });

    return unsubscribe;
  }, [history, mergedOptions.enableAnalytics]);

  // Keyboard shortcut handler
  useEffect(() => {
    if (!mergedOptions.enableKeyboardShortcuts) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const modifierKey = isMac ? e.metaKey : e.ctrlKey;

      // Undo: Ctrl+Z / Cmd+Z
      if (modifierKey && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        history.undo();
      }

      // Redo: Ctrl+Y / Cmd+Shift+Z
      if (modifierKey && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        history.redo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [history, mergedOptions.enableKeyboardShortcuts]);

  // Execute command
  const execute = useCallback(
    (command: GameCommand): boolean => {
      return history.execute(command);
    },
    [history]
  );

  // Undo last command
  const undo = useCallback((): GameCommand | null => {
    return history.undo();
  }, [history]);

  // Redo last undone command
  const redo = useCallback((): GameCommand | null => {
    return history.redo();
  }, [history]);

  // Clear history
  const clear = useCallback(() => {
    history.clear();
  }, [history]);

  // Get history instance
  const getHistory = useCallback(() => history, [history]);

  return {
    execute,
    undo,
    redo,
    historyState,
    clear,
    getHistory,
    canUndo: historyState.canUndo,
    canRedo: historyState.canRedo,
  };
}

/**
 * Hook for label diagram specific commands.
 * Provides convenience methods for creating and executing label commands.
 */
export function useLabelCommands() {
  const store = useInteractiveDiagramState();
  const { execute, undo, redo, canUndo, canRedo, historyState } = useCommandHistory({
    enableKeyboardShortcuts: true,
  });

  // Create store actions adapter for commands
  const storeActions = useMemo(
    () => ({
      placeLabel: store.placeLabel,
      removeLabel: store.removeLabel,
      getPlacedLabels: () => store.placedLabels,
      getAvailableLabels: () => store.availableLabels.map((l) => ({ id: l.id, text: l.text })),
    }),
    [store.placeLabel, store.removeLabel, store.placedLabels, store.availableLabels]
  );

  // Place label with command
  const placeLabelWithHistory = useCallback(
    (labelId: string, zoneId: string, labelText: string): boolean => {
      const command = new PlaceLabelCommand(storeActions, labelId, zoneId, labelText);
      return execute(command);
    },
    [storeActions, execute]
  );

  // Remove label with command
  const removeLabelWithHistory = useCallback(
    (labelId: string, labelText: string): void => {
      const command = new RemoveLabelCommand(storeActions, labelId, labelText);
      execute(command);
    },
    [storeActions, execute]
  );

  return {
    placeLabelWithHistory,
    removeLabelWithHistory,
    undo,
    redo,
    canUndo,
    canRedo,
    historyState,
  };
}

export default useCommandHistory;
