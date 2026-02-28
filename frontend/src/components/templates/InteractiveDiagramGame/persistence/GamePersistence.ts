/**
 * GamePersistence - IndexedDB-based save/load system
 *
 * Provides:
 * - Auto-save game progress
 * - Resume interrupted sessions
 * - Version migration for schema updates
 * - Cross-session persistence
 */

// Database configuration
const DB_NAME = 'gamed-ai-saves';
const DB_VERSION = 1;
const STORES = {
  gameState: 'game-state',
  events: 'game-events',
  settings: 'user-settings',
} as const;

/**
 * Saved game state structure
 */
export interface SavedGameState {
  id: string;
  gameId: string;
  sessionId: string;
  version: number;
  timestamp: number;
  /** Optimistic locking version - incremented on each save */
  saveVersion?: number;
  /** Base version this save was derived from (for conflict detection) */
  baseVersion?: number;
  state: {
    placedLabels: Array<{ labelId: string; zoneId: string; isCorrect: boolean }>;
    score: number;
    completedZoneIds: string[];
    visibleZoneIds: string[];
    hintsUsed: number;
    incorrectAttempts: number;
    elapsedTimeMs: number;
    multiSceneState?: {
      currentSceneIndex: number;
      completedSceneIds: string[];
      sceneResults: Array<{ scene_id: string; score: number; max_score: number; completed: boolean; matches: Array<{ labelId: string; zoneId: string; isCorrect: boolean }> }>;
      totalScore: number;
      isSequenceComplete: boolean;
    };
    // Phase E: Per-mechanic progress types for resume support
    pathProgress?: {
      pathId: string;
      visitedWaypoints: string[];
      isComplete: boolean;
    } | null;
    identificationProgress?: {
      currentPromptIndex: number;
      completedZoneIds: string[];
      incorrectAttempts: number;
    } | null;
    hierarchyState?: {
      expandedGroups: string[];
      completedParentZones: string[];
    } | null;
    descriptionMatchingState?: {
      currentIndex: number;
      matches: Array<{ labelId: string; zoneId: string; isCorrect: boolean }>;
      mode: string;
    } | null;
    sequencingProgress?: {
      currentOrder: string[];
      isSubmitted: boolean;
      correctPositions: number;
      totalPositions: number;
    } | null;
    sortingProgress?: {
      itemCategories: Record<string, string | null>;
      isSubmitted: boolean;
      correctCount: number;
      totalCount: number;
    } | null;
    memoryMatchProgress?: {
      matchedPairIds: string[];
      attempts: number;
      totalPairs: number;
    } | null;
    branchingProgress?: {
      currentNodeId: string;
      pathTaken: Array<{ nodeId: string; optionId: string; isCorrect: boolean }>;
    } | null;
    compareProgress?: {
      categorizations: Record<string, string>;
      isSubmitted: boolean;
      correctCount: number;
      totalCount: number;
    } | null;
    // Current interaction mode for proper resume
    interactionMode?: string;
  };
  commandHistory?: {
    undoStack: Array<{ type: string; description: string; data: unknown }>;
    redoStack: Array<{ type: string; description: string; data: unknown }>;
  };
}

/**
 * Conflict detection result
 */
export interface SaveConflict {
  localSave: SavedGameState;
  remoteSave: SavedGameState;
  resolution: 'local' | 'remote' | 'merge';
}

/**
 * Conflict resolution strategies
 */
export type ConflictResolutionStrategy = 'last-write-wins' | 'higher-progress' | 'ask-user';

/**
 * Result of a save operation with conflict detection
 */
export interface SaveResult {
  success: boolean;
  saveId?: string;
  conflict?: SaveConflict;
}

/**
 * User settings structure
 */
export interface UserSettings {
  id: string;
  highContrastMode: boolean;
  reducedMotion: boolean;
  fontSize: 'small' | 'medium' | 'large';
  colorBlindMode: 'none' | 'deuteranopia' | 'protanopia' | 'tritanopia';
  soundEnabled: boolean;
  autoSave: boolean;
}

const DEFAULT_SETTINGS: UserSettings = {
  id: 'default',
  highContrastMode: false,
  reducedMotion: false,
  fontSize: 'medium',
  colorBlindMode: 'none',
  soundEnabled: true,
  autoSave: true,
};

/**
 * Open or create the IndexedDB database
 */
function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB not supported'));
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      reject(new Error('Failed to open database'));
    };

    request.onsuccess = () => {
      resolve(request.result);
    };

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;

      // Create game state store
      if (!db.objectStoreNames.contains(STORES.gameState)) {
        const gameStore = db.createObjectStore(STORES.gameState, { keyPath: 'id' });
        gameStore.createIndex('gameId', 'gameId', { unique: false });
        gameStore.createIndex('sessionId', 'sessionId', { unique: false });
        gameStore.createIndex('timestamp', 'timestamp', { unique: false });
      }

      // Create events store
      if (!db.objectStoreNames.contains(STORES.events)) {
        const eventsStore = db.createObjectStore(STORES.events, { keyPath: 'id' });
        eventsStore.createIndex('sessionId', 'sessionId', { unique: false });
        eventsStore.createIndex('timestamp', 'timestamp', { unique: false });
      }

      // Create settings store
      if (!db.objectStoreNames.contains(STORES.settings)) {
        db.createObjectStore(STORES.settings, { keyPath: 'id' });
      }
    };
  });
}

/**
 * GamePersistence class for managing save/load operations
 *
 * Features:
 * - IndexedDB-based persistence
 * - Auto-save support
 * - Version migration
 * - Conflict detection and resolution with optimistic locking
 */
export class GamePersistence {
  private db: IDBDatabase | null = null;
  private autoSaveInterval: number | null = null;
  private conflictStrategy: ConflictResolutionStrategy = 'higher-progress';

  /**
   * Initialize the persistence layer
   */
  async initialize(): Promise<void> {
    try {
      this.db = await openDatabase();
    } catch (error) {
      console.warn('GamePersistence: Failed to initialize IndexedDB', error);
    }
  }

  /**
   * Set conflict resolution strategy
   */
  setConflictStrategy(strategy: ConflictResolutionStrategy): void {
    this.conflictStrategy = strategy;
  }

  /**
   * Save game progress with conflict detection
   *
   * Uses optimistic locking to detect conflicts when multiple sessions
   * or browser tabs are editing the same game.
   */
  async saveProgress(
    gameId: string,
    sessionId: string,
    state: SavedGameState['state'],
    commandHistory?: SavedGameState['commandHistory'],
    baseVersion?: number
  ): Promise<string> {
    if (!this.db) {
      await this.initialize();
    }

    if (!this.db) {
      throw new Error('Database not available');
    }

    const saveId = `save_${gameId}_${sessionId}_${Date.now()}`;

    // Get existing save to check for conflicts and determine version
    const existingSave = await this.loadProgress(gameId);
    const newSaveVersion = (existingSave?.saveVersion ?? 0) + 1;

    const save: SavedGameState = {
      id: saveId,
      gameId,
      sessionId,
      version: DB_VERSION,
      saveVersion: newSaveVersion,
      baseVersion: baseVersion ?? existingSave?.saveVersion,
      timestamp: Date.now(),
      state,
      commandHistory,
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.gameState], 'readwrite');
      const store = transaction.objectStore(STORES.gameState);
      const request = store.put(save);

      request.onerror = () => reject(new Error('Failed to save progress'));
      request.onsuccess = () => resolve(saveId);
    });
  }

  /**
   * Save with conflict detection - returns conflict info if detected
   *
   * Uses optimistic locking: compares baseVersion with current remoteSave version.
   * If they don't match, a conflict is detected and resolved according to strategy.
   */
  async saveWithConflictCheck(
    gameId: string,
    sessionId: string,
    state: SavedGameState['state'],
    commandHistory?: SavedGameState['commandHistory'],
    baseVersion?: number
  ): Promise<SaveResult> {
    if (!this.db) {
      await this.initialize();
    }

    if (!this.db) {
      return { success: false };
    }

    // Load existing save to check for conflicts
    const existingSave = await this.loadProgress(gameId);

    // Check for version conflict
    if (existingSave && baseVersion !== undefined && existingSave.saveVersion !== baseVersion) {
      // Conflict detected! Another save happened since our base version
      const localSave: SavedGameState = {
        id: `local_${gameId}_${Date.now()}`,
        gameId,
        sessionId,
        version: DB_VERSION,
        saveVersion: (existingSave.saveVersion ?? 0) + 1,
        baseVersion,
        timestamp: Date.now(),
        state,
        commandHistory,
      };

      const conflict: SaveConflict = {
        localSave,
        remoteSave: existingSave,
        resolution: this.resolveConflict(localSave, existingSave),
      };

      // Apply resolution
      const resolvedSave = conflict.resolution === 'local' ? localSave : existingSave;

      if (conflict.resolution !== 'remote') {
        // Save the resolved version
        const saveId = await this.saveProgress(
          gameId,
          sessionId,
          resolvedSave.state,
          resolvedSave.commandHistory,
          resolvedSave.saveVersion
        );
        return { success: true, saveId, conflict };
      }

      // Remote wins - don't save, return conflict info
      return { success: false, conflict };
    }

    // No conflict, proceed with normal save
    const saveId = await this.saveProgress(gameId, sessionId, state, commandHistory, baseVersion);
    return { success: true, saveId };
  }

  /**
   * Resolve conflict between local and remote saves
   */
  private resolveConflict(local: SavedGameState, remote: SavedGameState): 'local' | 'remote' | 'merge' {
    switch (this.conflictStrategy) {
      case 'last-write-wins':
        // Most recent timestamp wins
        return local.timestamp > remote.timestamp ? 'local' : 'remote';

      case 'higher-progress':
        // Higher score or more completed zones wins
        const localProgress = local.state.completedZoneIds.length + local.state.score;
        const remoteProgress = remote.state.completedZoneIds.length + remote.state.score;

        if (localProgress > remoteProgress) {
          return 'local';
        } else if (remoteProgress > localProgress) {
          return 'remote';
        }
        // Tie-breaker: use timestamp
        return local.timestamp > remote.timestamp ? 'local' : 'remote';

      case 'ask-user':
        // Return 'merge' to indicate UI should prompt user
        return 'merge';

      default:
        return 'local';
    }
  }

  /**
   * Merge two saves (for manual conflict resolution)
   *
   * Takes the best of both saves:
   * - All placed labels from both (union)
   * - Higher score
   * - More recent timestamp
   */
  mergeSaves(local: SavedGameState, remote: SavedGameState): SavedGameState {
    // Merge placed labels (union, avoiding duplicates)
    const placedLabelsMap = new Map<string, SavedGameState['state']['placedLabels'][0]>();

    for (const label of remote.state.placedLabels) {
      placedLabelsMap.set(`${label.labelId}-${label.zoneId}`, label);
    }
    for (const label of local.state.placedLabels) {
      placedLabelsMap.set(`${label.labelId}-${label.zoneId}`, label);
    }

    // Merge completed zones (union)
    const completedZoneIds = [...new Set([
      ...local.state.completedZoneIds,
      ...remote.state.completedZoneIds,
    ])];

    // Take higher values for cumulative metrics
    const mergedState: SavedGameState['state'] = {
      placedLabels: Array.from(placedLabelsMap.values()),
      score: Math.max(local.state.score, remote.state.score),
      completedZoneIds,
      visibleZoneIds: [...new Set([...local.state.visibleZoneIds, ...remote.state.visibleZoneIds])],
      hintsUsed: Math.max(local.state.hintsUsed, remote.state.hintsUsed),
      incorrectAttempts: Math.max(local.state.incorrectAttempts, remote.state.incorrectAttempts),
      elapsedTimeMs: Math.max(local.state.elapsedTimeMs, remote.state.elapsedTimeMs),
    };

    return {
      id: `merged_${local.gameId}_${Date.now()}`,
      gameId: local.gameId,
      sessionId: local.sessionId,
      version: DB_VERSION,
      saveVersion: Math.max(local.saveVersion ?? 0, remote.saveVersion ?? 0) + 1,
      timestamp: Date.now(),
      state: mergedState,
      // Take the longer command history
      commandHistory:
        (local.commandHistory?.undoStack.length ?? 0) >
        (remote.commandHistory?.undoStack.length ?? 0)
          ? local.commandHistory
          : remote.commandHistory,
    };
  }

  /**
   * Load most recent save for a game
   */
  async loadProgress(gameId: string): Promise<SavedGameState | null> {
    if (!this.db) {
      await this.initialize();
    }

    if (!this.db) {
      return null;
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.gameState], 'readonly');
      const store = transaction.objectStore(STORES.gameState);
      const index = store.index('gameId');
      const request = index.getAll(gameId);

      request.onerror = () => reject(new Error('Failed to load progress'));
      request.onsuccess = () => {
        const saves = request.result as SavedGameState[];
        if (saves.length === 0) {
          resolve(null);
        } else {
          // Return the most recent save
          const sorted = saves.sort((a, b) => b.timestamp - a.timestamp);
          resolve(this.migrateIfNeeded(sorted[0]));
        }
      };
    });
  }

  /**
   * Load save by session ID
   */
  async loadBySession(sessionId: string): Promise<SavedGameState | null> {
    if (!this.db) {
      await this.initialize();
    }

    if (!this.db) {
      return null;
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.gameState], 'readonly');
      const store = transaction.objectStore(STORES.gameState);
      const index = store.index('sessionId');
      const request = index.getAll(sessionId);

      request.onerror = () => reject(new Error('Failed to load session'));
      request.onsuccess = () => {
        const saves = request.result as SavedGameState[];
        if (saves.length === 0) {
          resolve(null);
        } else {
          const sorted = saves.sort((a, b) => b.timestamp - a.timestamp);
          resolve(this.migrateIfNeeded(sorted[0]));
        }
      };
    });
  }

  /**
   * Delete a specific save
   */
  async deleteSave(saveId: string): Promise<void> {
    if (!this.db) {
      await this.initialize();
    }

    if (!this.db) {
      return;
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.gameState], 'readwrite');
      const store = transaction.objectStore(STORES.gameState);
      const request = store.delete(saveId);

      request.onerror = () => reject(new Error('Failed to delete save'));
      request.onsuccess = () => resolve();
    });
  }

  /**
   * Clear all saves for a game
   */
  async clearGameSaves(gameId: string): Promise<void> {
    if (!this.db) {
      await this.initialize();
    }

    if (!this.db) {
      return;
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.gameState], 'readwrite');
      const store = transaction.objectStore(STORES.gameState);
      const index = store.index('gameId');
      const request = index.getAllKeys(gameId);

      request.onerror = () => reject(new Error('Failed to clear saves'));
      request.onsuccess = () => {
        const keys = request.result;
        keys.forEach((key) => store.delete(key));
        resolve();
      };
    });
  }

  /**
   * Get all saves (for save management UI)
   */
  async getAllSaves(): Promise<SavedGameState[]> {
    if (!this.db) {
      await this.initialize();
    }

    if (!this.db) {
      return [];
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.gameState], 'readonly');
      const store = transaction.objectStore(STORES.gameState);
      const request = store.getAll();

      request.onerror = () => reject(new Error('Failed to get saves'));
      request.onsuccess = () => {
        const saves = request.result as SavedGameState[];
        resolve(saves.sort((a, b) => b.timestamp - a.timestamp));
      };
    });
  }

  /**
   * Save user settings
   */
  async saveSettings(settings: Partial<UserSettings>): Promise<void> {
    if (!this.db) {
      await this.initialize();
    }

    if (!this.db) {
      return;
    }

    const currentSettings = await this.loadSettings();
    const updatedSettings = { ...currentSettings, ...settings };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.settings], 'readwrite');
      const store = transaction.objectStore(STORES.settings);
      const request = store.put(updatedSettings);

      request.onerror = () => reject(new Error('Failed to save settings'));
      request.onsuccess = () => resolve();
    });
  }

  /**
   * Load user settings
   */
  async loadSettings(): Promise<UserSettings> {
    if (!this.db) {
      await this.initialize();
    }

    if (!this.db) {
      return DEFAULT_SETTINGS;
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORES.settings], 'readonly');
      const store = transaction.objectStore(STORES.settings);
      const request = store.get('default');

      request.onerror = () => resolve(DEFAULT_SETTINGS);
      request.onsuccess = () => {
        resolve(request.result || DEFAULT_SETTINGS);
      };
    });
  }

  /**
   * Enable auto-save with specified interval
   */
  startAutoSave(
    intervalMs: number,
    getSaveData: () => { gameId: string; sessionId: string; state: SavedGameState['state'] }
  ): void {
    this.stopAutoSave();

    this.autoSaveInterval = window.setInterval(async () => {
      try {
        const data = getSaveData();
        await this.saveProgress(data.gameId, data.sessionId, data.state);
      } catch (error) {
        console.warn('Auto-save failed:', error);
      }
    }, intervalMs);
  }

  /**
   * Stop auto-save
   */
  stopAutoSave(): void {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
      this.autoSaveInterval = null;
    }
  }

  /**
   * Migrate save data if needed
   */
  private migrateIfNeeded(save: SavedGameState): SavedGameState {
    if (save.version === DB_VERSION) {
      return save;
    }

    // Add migration logic here as needed
    // For now, just return the save as-is
    return { ...save, version: DB_VERSION };
  }

  /**
   * Close database connection
   */
  close(): void {
    this.stopAutoSave();
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }
}

// Singleton instance
let persistence: GamePersistence | null = null;

/**
 * Get or create the persistence instance
 */
export function getGamePersistence(): GamePersistence {
  if (!persistence) {
    persistence = new GamePersistence();
  }
  return persistence;
}

/**
 * Reset persistence (for testing)
 */
export function resetGamePersistence(): GamePersistence {
  if (persistence) {
    persistence.close();
  }
  persistence = new GamePersistence();
  return persistence;
}
