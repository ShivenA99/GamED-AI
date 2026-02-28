/**
 * usePersistence - Hook for integrating game persistence with React
 *
 * Provides:
 * - Auto-save functionality
 * - Load/resume support
 * - Settings management
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  GamePersistence,
  getGamePersistence,
  SavedGameState,
  UserSettings,
} from '../persistence';
import { useInteractiveDiagramState } from './useInteractiveDiagramState';

export interface UsePersistenceOptions {
  /** Game ID for saving */
  gameId: string;
  /** Session ID */
  sessionId: string;
  /** Enable auto-save (default: true) */
  autoSave?: boolean;
  /** Auto-save interval in ms (default: 30000 = 30 seconds) */
  autoSaveInterval?: number;
  /** Callback when save completes */
  onSave?: () => void;
  /** Callback when load completes */
  onLoad?: (state: SavedGameState) => void;
}

export interface UsePersistenceReturn {
  /** Save current game state */
  saveGame: () => Promise<void>;
  /** Load saved game state */
  loadGame: () => Promise<SavedGameState | null>;
  /** Check if a save exists */
  hasSavedGame: () => Promise<boolean>;
  /** Clear saved game */
  clearSave: () => Promise<void>;
  /** User settings */
  settings: UserSettings;
  /** Update settings */
  updateSettings: (settings: Partial<UserSettings>) => Promise<void>;
  /** Is currently saving */
  isSaving: boolean;
  /** Is currently loading */
  isLoading: boolean;
  /** Last save timestamp */
  lastSaveTime: number | null;
}

const DEFAULT_OPTIONS: Partial<UsePersistenceOptions> = {
  autoSave: true,
  autoSaveInterval: 30000, // 30 seconds
};

/**
 * Hook for game persistence with auto-save support
 */
export function usePersistence(options: UsePersistenceOptions): UsePersistenceReturn {
  const mergedOptions = { ...DEFAULT_OPTIONS, ...options };
  const { gameId, sessionId, autoSave, autoSaveInterval, onSave, onLoad } = mergedOptions;

  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [lastSaveTime, setLastSaveTime] = useState<number | null>(null);
  const [settings, setSettings] = useState<UserSettings>({
    id: 'default',
    highContrastMode: false,
    reducedMotion: false,
    fontSize: 'medium',
    colorBlindMode: 'none',
    soundEnabled: true,
    autoSave: true,
  });

  const persistenceRef = useRef<GamePersistence | null>(null);
  const store = useInteractiveDiagramState();

  // Initialize persistence
  useEffect(() => {
    const init = async () => {
      persistenceRef.current = getGamePersistence();
      await persistenceRef.current.initialize();

      // Load settings
      const savedSettings = await persistenceRef.current.loadSettings();
      setSettings(savedSettings);
    };
    init();

    return () => {
      if (persistenceRef.current) {
        persistenceRef.current.stopAutoSave();
      }
    };
  }, []);

  // Get current state for saving — Phase E: includes all per-mechanic progress
  const getCurrentState = useCallback((): SavedGameState['state'] => {
    return {
      placedLabels: store.placedLabels,
      score: store.score,
      completedZoneIds: Array.from(store.completedZoneIds),
      visibleZoneIds: Array.from(store.visibleZoneIds),
      hintsUsed: 0, // Would need to track this
      incorrectAttempts: 0, // Would need to track this
      elapsedTimeMs: 0, // Would need to track this
      multiSceneState: store.multiSceneState ?? undefined,
      // Phase E: Per-mechanic progress
      pathProgress: store.pathProgress,
      identificationProgress: store.identificationProgress,
      hierarchyState: store.hierarchyState,
      descriptionMatchingState: store.descriptionMatchingState,
      sequencingProgress: store.sequencingProgress,
      sortingProgress: store.sortingProgress,
      memoryMatchProgress: store.memoryMatchProgress,
      branchingProgress: store.branchingProgress,
      compareProgress: store.compareProgress,
      interactionMode: store.interactionMode,
    };
  }, [
    store.placedLabels, store.score, store.completedZoneIds, store.visibleZoneIds,
    store.multiSceneState, store.pathProgress, store.identificationProgress,
    store.hierarchyState, store.descriptionMatchingState, store.sequencingProgress,
    store.sortingProgress, store.memoryMatchProgress, store.branchingProgress,
    store.compareProgress, store.interactionMode,
  ]);

  // Save game
  const saveGame = useCallback(async (): Promise<void> => {
    if (!persistenceRef.current || isSaving) return;

    setIsSaving(true);
    try {
      const state = getCurrentState();
      await persistenceRef.current.saveProgress(gameId, sessionId, state);
      setLastSaveTime(Date.now());
      onSave?.();
    } catch (error) {
      console.error('Failed to save game:', error);
    } finally {
      setIsSaving(false);
    }
  }, [gameId, sessionId, getCurrentState, isSaving, onSave]);

  // Load game — Fix 4.2: Actually restore state, not just announce
  const loadGame = useCallback(async (): Promise<SavedGameState | null> => {
    if (!persistenceRef.current || isLoading) return null;

    setIsLoading(true);
    try {
      const save = await persistenceRef.current.loadProgress(gameId);
      if (save && save.state) {
        // Restore state into Zustand store
        const s = save.state;
        const restoredCompletedZoneIds = new Set<string>(s.completedZoneIds || []);
        const restoredVisibleZoneIds = new Set<string>(s.visibleZoneIds || []);
        // QW-5: Rebuild availableLabels by filtering out already-placed labels
        const currentBlueprint = useInteractiveDiagramState.getState().blueprint;
        const allLabels = currentBlueprint
          ? [...currentBlueprint.labels, ...(currentBlueprint.distractorLabels || [])]
          : [];
        const placedLabelIds = new Set((s.placedLabels || []).map(p => p.labelId));
        const restoredAvailableLabels = allLabels.filter(l => !placedLabelIds.has(l.id));

        useInteractiveDiagramState.setState({
          placedLabels: s.placedLabels || [],
          availableLabels: restoredAvailableLabels,
          score: s.score || 0,
          completedZoneIds: restoredCompletedZoneIds,
          visibleZoneIds: restoredVisibleZoneIds,
          multiSceneState: s.multiSceneState
            ? {
                ...s.multiSceneState,
                currentTaskIndex: (s.multiSceneState as Record<string, unknown>).currentTaskIndex as number ?? 0,
                taskResults: (s.multiSceneState as Record<string, unknown>).taskResults as Array<{ task_id: string; score: number; max_score: number; completed: boolean; matches: Array<{ labelId: string; zoneId: string; isCorrect: boolean }> }> ?? [],
              }
            : null,
          // Phase E: Restore per-mechanic progress types
          pathProgress: s.pathProgress ?? null,
          identificationProgress: s.identificationProgress ?? null,
          hierarchyState: s.hierarchyState ?? null,
          descriptionMatchingState: (s.descriptionMatchingState as import('../types').DescriptionMatchingState) ?? null,
          sequencingProgress: s.sequencingProgress ?? null,
          sortingProgress: s.sortingProgress ?? null,
          memoryMatchProgress: s.memoryMatchProgress ?? null,
          branchingProgress: s.branchingProgress ?? null,
          compareProgress: s.compareProgress ?? null,
          // Restore interaction mode if saved
          ...(s.interactionMode ? { interactionMode: s.interactionMode as import('../types').InteractionMode } : {}),
        });
        onLoad?.(save);
      }
      return save;
    } catch (error) {
      console.error('Failed to load game:', error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [gameId, isLoading, onLoad]);

  // Check for saved game
  const hasSavedGame = useCallback(async (): Promise<boolean> => {
    if (!persistenceRef.current) return false;

    try {
      const save = await persistenceRef.current.loadProgress(gameId);
      return save !== null;
    } catch {
      return false;
    }
  }, [gameId]);

  // Clear save
  const clearSave = useCallback(async (): Promise<void> => {
    if (!persistenceRef.current) return;

    try {
      await persistenceRef.current.clearGameSaves(gameId);
      setLastSaveTime(null);
    } catch (error) {
      console.error('Failed to clear save:', error);
    }
  }, [gameId]);

  // Update settings
  const updateSettings = useCallback(async (newSettings: Partial<UserSettings>): Promise<void> => {
    if (!persistenceRef.current) return;

    try {
      await persistenceRef.current.saveSettings(newSettings);
      setSettings((prev) => ({ ...prev, ...newSettings }));
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  }, []);

  // Set up auto-save
  useEffect(() => {
    if (!autoSave || !persistenceRef.current || !settings.autoSave) return;

    persistenceRef.current.startAutoSave(autoSaveInterval!, () => ({
      gameId,
      sessionId,
      state: getCurrentState(),
    }));

    return () => {
      persistenceRef.current?.stopAutoSave();
    };
  }, [autoSave, autoSaveInterval, gameId, sessionId, getCurrentState, settings.autoSave]);

  return {
    saveGame,
    loadGame,
    hasSavedGame,
    clearSave,
    settings,
    updateSettings,
    isSaving,
    isLoading,
    lastSaveTime,
  };
}

export default usePersistence;
