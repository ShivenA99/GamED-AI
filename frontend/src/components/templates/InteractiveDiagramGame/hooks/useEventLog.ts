/**
 * useEventLog - Hook for integrating Event Sourcing with game state
 *
 * Provides React integration for the event logging system with:
 * - Automatic game state tracking
 * - Analytics summary generation
 * - Export functionality
 */

import { useCallback, useEffect, useRef, useMemo, useState } from 'react';
import { GameEventLog, GameEventLogOptions, getEventLog, resetEventLog } from '../events';
import { useInteractiveDiagramState } from './useInteractiveDiagramState';

/**
 * Hook options for event log integration
 */
export interface UseEventLogOptions extends GameEventLogOptions {
  /** Automatically log game start when blueprint is initialized */
  autoLogGameStart?: boolean;
  /** Automatically log zone reveals */
  autoLogZoneReveals?: boolean;
}

const DEFAULT_OPTIONS: UseEventLogOptions = {
  autoLogGameStart: true,
  autoLogZoneReveals: true,
  autoPersist: false,
};

/**
 * Hook for using event log with React components.
 * Provides convenient methods for logging game events and generating analytics.
 */
export function useEventLog(options: UseEventLogOptions = {}) {
  // Memoize options to prevent unnecessary reruns
  const mergedOptions = useMemo(
    () => ({ ...DEFAULT_OPTIONS, ...options }),
    [
      options.maxEvents,
      options.sessionId,
      options.gameId,
      options.autoPersist,
      options.persistenceKey,
      options.autoLogGameStart,
      options.autoLogZoneReveals,
    ]
  );

  // Store onEvent callback in ref to avoid dependency issues
  const onEventRef = useRef(options.onEvent);
  useEffect(() => {
    onEventRef.current = options.onEvent;
  }, [options.onEvent]);

  // Initialize event log lazily with useState for proper SSR/Strict Mode handling
  const [eventLog] = useState<GameEventLog>(() => {
    return getEventLog({
      maxEvents: mergedOptions.maxEvents,
      sessionId: mergedOptions.sessionId,
      gameId: mergedOptions.gameId,
      autoPersist: mergedOptions.autoPersist,
      persistenceKey: mergedOptions.persistenceKey,
      onEvent: (event) => onEventRef.current?.(event),
    });
  });

  // Keep a ref for reset functionality
  const eventLogRef = useRef<GameEventLog>(eventLog);

  // Track previous visible zones for auto-logging
  const prevVisibleZonesRef = useRef<Set<string>>(new Set());
  const store = useInteractiveDiagramState();

  // Auto-log game start when blueprint changes
  useEffect(() => {
    if (!mergedOptions.autoLogGameStart || !store.blueprint) return;

    const sceneIndex = store.multiSceneState?.currentSceneIndex;
    eventLog.logGameStarted(
      store.blueprint.title || 'unknown',
      store.blueprint.templateType,
      store.blueprint.diagram.zones.length,
      store.blueprint.labels.length,
      store.interactionMode,
      false, // hasTimedChallenge - need to check wrapper
      undefined
    );

    // Log scene index for multi-scene games
    if (sceneIndex !== undefined && sceneIndex !== null) {
      eventLog.log('scene_entered', {
        sceneIndex,
        interactionMode: store.interactionMode,
      });
    }

    // Log initial visible zones
    if (mergedOptions.autoLogZoneReveals) {
      store.visibleZoneIds.forEach((zoneId) => {
        const zone = store.blueprint?.diagram.zones.find((z) => z.id === zoneId);
        if (zone) {
          eventLog.logZoneRevealed(
            zoneId,
            zone.label || zoneId,
            'initial',
            zone.hierarchyLevel,
            zone.parentZoneId
          );
        }
      });
    }

    prevVisibleZonesRef.current = new Set(store.visibleZoneIds);
  }, [
    store.blueprint,
    store.interactionMode,
    store.visibleZoneIds,
    store.multiSceneState,
    eventLog,
    mergedOptions.autoLogGameStart,
    mergedOptions.autoLogZoneReveals,
  ]);

  // Auto-log zone reveals when visible zones change
  useEffect(() => {
    if (!mergedOptions.autoLogZoneReveals || !store.blueprint) return;

    const currentVisible = store.visibleZoneIds;
    const prevVisible = prevVisibleZonesRef.current;

    // Find newly revealed zones
    currentVisible.forEach((zoneId) => {
      if (!prevVisible.has(zoneId)) {
        const zone = store.blueprint?.diagram.zones.find((z) => z.id === zoneId);
        if (zone) {
          // Determine reason for reveal
          let reason: 'initial' | 'parent_completed' | 'mutex_cleared' | 'hierarchy_expanded' =
            'parent_completed';

          if (zone.parentZoneId && store.completedZoneIds.has(zone.parentZoneId)) {
            reason = 'parent_completed';
          } else {
            reason = 'mutex_cleared';
          }

          eventLog.logZoneRevealed(
            zoneId,
            zone.label || zoneId,
            reason,
            zone.hierarchyLevel,
            zone.parentZoneId
          );
        }
      }
    });

    prevVisibleZonesRef.current = new Set(currentVisible);
  }, [store.visibleZoneIds, store.completedZoneIds, store.blueprint, mergedOptions.autoLogZoneReveals, eventLog]);

  // Logging methods
  const logLabelPlaced = useCallback(
    (labelId: string, labelText: string, zoneId: string, isCorrect: boolean) => {
      return eventLog.logLabelPlaced(labelId, labelText, zoneId, isCorrect);
    },
    [eventLog]
  );

  const logLabelRemoved = useCallback(
    (
      labelId: string,
      labelText: string,
      fromZoneId: string,
      wasCorrect: boolean,
      reason: 'user_action' | 'undo' | 'reset' = 'user_action'
    ) => {
      return eventLog.logLabelRemoved(labelId, labelText, fromZoneId, wasCorrect, reason);
    },
    [eventLog]
  );

  const logDragStarted = useCallback(
    (
      labelId: string,
      labelText: string,
      fromLocation: 'tray' | 'zone',
      fromZoneId?: string
    ) => {
      eventLog.logDragStarted(labelId, labelText, fromLocation, fromZoneId);
    },
    [eventLog]
  );

  const logDragEnded = useCallback(
    (
      labelId: string,
      labelText: string,
      toLocation: 'zone' | 'tray' | 'cancelled',
      toZoneId?: string
    ) => {
      eventLog.logDragEnded(labelId, labelText, toLocation, toZoneId);
    },
    [eventLog]
  );

  const logZoneCompleted = useCallback(
    (zoneId: string, zoneName: string, labelId: string, hintsUsed: number = 0) => {
      return eventLog.logZoneCompleted(zoneId, zoneName, labelId, hintsUsed);
    },
    [eventLog]
  );

  const logGameCompleted = useCallback(
    (
      finalScore: number,
      maxScore: number,
      correctPlacements: number,
      incorrectAttempts: number,
      hintsUsed: number,
      undoCount: number,
      redoCount: number,
      timeBonus?: number
    ) => {
      return eventLog.logGameCompleted(
        finalScore,
        maxScore,
        correctPlacements,
        incorrectAttempts,
        hintsUsed,
        undoCount,
        redoCount,
        timeBonus
      );
    },
    [eventLog]
  );

  const logHintRequested = useCallback(
    (
      hintType: 'zone_highlight' | 'label_hint' | 'general',
      targetZoneId?: string,
      targetLabelId?: string
    ) => {
      eventLog.logHintRequested(hintType, targetZoneId, targetLabelId);
    },
    [eventLog]
  );

  const logUndo = useCallback(
    (undoneCommandType: string, undoneCommandDescription: string, stackDepth: number) => {
      eventLog.logUndo(undoneCommandType, undoneCommandDescription, stackDepth);
    },
    [eventLog]
  );

  const logRedo = useCallback(
    (redoneCommandType: string, redoneCommandDescription: string, stackDepth: number) => {
      eventLog.logRedo(redoneCommandType, redoneCommandDescription, stackDepth);
    },
    [eventLog]
  );

  const logPaused = useCallback(() => {
    eventLog.logPaused();
  }, [eventLog]);

  const logResumed = useCallback(() => {
    eventLog.logResumed();
  }, [eventLog]);

  const logError = useCallback(
    (errorType: string, errorMessage: string, context?: Record<string, unknown>) => {
      eventLog.logError(errorType, errorMessage, context);
    },
    [eventLog]
  );

  // Analytics and export
  const generateSummary = useCallback(() => {
    return eventLog.generateSummary();
  }, [eventLog]);

  const exportEvents = useCallback(() => {
    return eventLog.export();
  }, [eventLog]);

  const getEvents = useCallback(() => {
    return eventLog.getEvents();
  }, [eventLog]);

  const clearEvents = useCallback(() => {
    eventLog.clear();
  }, [eventLog]);

  // Reset for new game - note: this creates a new instance separate from the main one
  const resetForNewGame = useCallback(
    (newOptions?: Partial<UseEventLogOptions>) => {
      const newEventLog = resetEventLog({
        ...mergedOptions,
        ...newOptions,
        onEvent: (event) => onEventRef.current?.(event),
      });
      eventLogRef.current = newEventLog;
      prevVisibleZonesRef.current = new Set();
      // Note: callbacks need to use eventLogRef.current for the new instance
    },
    [mergedOptions]
  );

  return {
    // Logging methods
    logLabelPlaced,
    logLabelRemoved,
    logDragStarted,
    logDragEnded,
    logZoneCompleted,
    logGameCompleted,
    logHintRequested,
    logUndo,
    logRedo,
    logPaused,
    logResumed,
    logError,

    // Analytics
    generateSummary,
    exportEvents,
    getEvents,
    clearEvents,
    resetForNewGame,

    // Direct access
    eventLog,
  };
}

export default useEventLog;
