'use client';

import { useEffect, useCallback, useMemo, useRef, useState } from 'react';
import {
  DragEndEvent,
  DragStartEvent,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  InteractiveDiagramBlueprint,
  InteractionMode,
  MultiSceneInteractiveDiagramBlueprint,
  GameSequence,
  GameScene,
  SceneTask,
  MechanicAction,
} from './types';
import { parseBlueprint, isMultiSceneParseResult } from './engine/schemas/parseBlueprint';
import { useInteractiveDiagramState } from './hooks/useInteractiveDiagramState';
import { useCommandHistory } from './hooks/useCommandHistory';
import { useEventLog } from './hooks/useEventLog';
import { usePersistence } from './hooks/usePersistence';
import { PlaceLabelCommand } from './commands/PlaceLabelCommand';
import { resetCommandHistory } from './commands';
import {
  AnnouncementProvider,
  useAnnouncements,
  KeyboardNav,
} from './accessibility';
import { GameErrorBoundary } from './ErrorBoundary';
import GameControls from './GameControls';
import ResultsPanel from './ResultsPanel';
import {
  GameSequenceRenderer,
  // Undo/Redo controls
  UndoRedoControls,
  // Multi-mode indicator
  ModeIndicator,
} from './interactions';
import SceneTransition, { SceneIndicator, useSceneTransition } from './SceneTransition';
import MechanicRouter, { MechanicRouterProps } from './MechanicRouter';
import { useMechanicDispatch } from './hooks/useMechanicDispatch';
import type { DndState, HierarchicalModeCallbacks, MechanicProgressMap } from './mechanicRegistry';
import { MECHANIC_REGISTRY, getRegistryInstructions } from './mechanicRegistry';
import { getSceneAction } from './engine/sceneManager';

// Type guard for multi-scene blueprints
function isMultiSceneBlueprint(
  blueprint: InteractiveDiagramBlueprint | MultiSceneInteractiveDiagramBlueprint
): blueprint is MultiSceneInteractiveDiagramBlueprint {
  return 'is_multi_scene' in blueprint && blueprint.is_multi_scene === true;
}

export type { GameplayMode } from './types';
import type { GameplayMode } from './types';

interface InteractiveDiagramGameProps {
  blueprint: InteractiveDiagramBlueprint | MultiSceneInteractiveDiagramBlueprint;
  onComplete?: (score: number) => void;
  sessionId?: string;
  gameplayMode?: GameplayMode;
}

const coerceDimension = (value: unknown, fallbackValue: number): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.round(value);
  }
  if (typeof value === 'string') {
    const raw = value.trim().toLowerCase();
    const numeric = raw.endsWith('px') ? raw.slice(0, -2).trim() : raw;
    const parsed = Number(numeric);
    if (Number.isFinite(parsed)) {
      return Math.round(parsed);
    }
  }
  return fallbackValue;
};

const slugify = (value: string): string =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');

const generateDefaultPositions = (count: number) => {
  if (count <= 0) return [];
  const rows = Math.ceil(Math.sqrt(count));
  const cols = Math.ceil(count / rows);
  const xStep = 100 / (cols + 1);
  const yStep = 100 / (rows + 1);
  const positions: Array<{ x: number; y: number }> = [];
  for (let idx = 0; idx < count; idx += 1) {
    const row = Math.floor(idx / cols);
    const col = idx % cols;
    positions.push({
      x: Math.round((col + 1) * xStep * 100) / 100,
      y: Math.round((row + 1) * yStep * 100) / 100,
    });
  }
  return positions;
};

const normalizeBlueprint = (input: InteractiveDiagramBlueprint): InteractiveDiagramBlueprint => {
  const diagram = input.diagram ?? { assetPrompt: '', zones: [] };
  const width = coerceDimension(diagram.width, 800);
  const height = coerceDimension(diagram.height, 600);
  const zones = Array.isArray(diagram.zones) ? diagram.zones.map((zone) => ({ ...zone })) : [];

  const zoneIdQueues = new Map<string, string[]>();
  const usedZoneIds = new Set<string>();
  const normalizedZones = zones.map((zone, index) => {
    const originalId = zone.id || `zone_${index + 1}`;
    let uniqueId = originalId;
    let suffix = 1;
    while (usedZoneIds.has(uniqueId)) {
      suffix += 1;
      uniqueId = `${originalId}_${suffix}`;
    }
    usedZoneIds.add(uniqueId);
    if (!zoneIdQueues.has(originalId)) {
      zoneIdQueues.set(originalId, []);
    }
    zoneIdQueues.get(originalId)?.push(uniqueId);
    return { ...zone, id: uniqueId };
  });

  const labels = Array.isArray(input.labels) ? input.labels.map((label) => ({ ...label })) : [];
  const usedLabelIds = new Set<string>();
  const assignedZoneIds = new Set<string>();
  const normalizedLabels = labels.map((label, index) => {
    const labelText = label.text || `Label ${index + 1}`;
    const baseLabelId =
      (label as { id?: string }).id ||
      (label as { labelId?: string }).labelId ||
      `label_${slugify(labelText) || index + 1}`;
    let uniqueLabelId = baseLabelId;
    let labelSuffix = 1;
    while (usedLabelIds.has(uniqueLabelId)) {
      labelSuffix += 1;
      uniqueLabelId = `${baseLabelId}_${labelSuffix}`;
    }
    usedLabelIds.add(uniqueLabelId);

    const originalZoneId =
      label.correctZoneId || normalizedZones[index]?.id || `zone_${index + 1}`;
    let mappedZoneId = originalZoneId;
    const queue = zoneIdQueues.get(originalZoneId);
    if (queue && queue.length > 0) {
      mappedZoneId = queue.shift() as string;
    }
    if (assignedZoneIds.has(mappedZoneId)) {
      let zoneSuffix = 1;
      let uniqueZoneId = `${mappedZoneId}_${zoneSuffix}`;
      while (assignedZoneIds.has(uniqueZoneId)) {
        zoneSuffix += 1;
        uniqueZoneId = `${mappedZoneId}_${zoneSuffix}`;
      }
      mappedZoneId = uniqueZoneId;
    }
    assignedZoneIds.add(mappedZoneId);

    return {
      ...label,
      id: uniqueLabelId,
      text: labelText,
      correctZoneId: mappedZoneId,
    };
  });

  // Fix 3.3 + 3.5: Match labels to zones by text similarity instead of creating phantom zones
  const zoneIdSet = new Set(normalizedZones.map((zone) => zone.id));
  const matchedZoneIds = new Set<string>();
  normalizedLabels.forEach((label) => {
    if (!zoneIdSet.has(label.correctZoneId)) {
      // Fix 3.5: Try exact zone.label === label.text match first
      const exactMatch = normalizedZones.find(
        z => z.label.toLowerCase().trim() === label.text.toLowerCase().trim()
          && !matchedZoneIds.has(z.id)
      );
      if (exactMatch) {
        label.correctZoneId = exactMatch.id;
        matchedZoneIds.add(exactMatch.id);
      } else {
        // Try substring match
        const partialMatch = normalizedZones.find(
          z => (z.label.toLowerCase().includes(label.text.toLowerCase())
             || label.text.toLowerCase().includes(z.label.toLowerCase()))
            && !matchedZoneIds.has(z.id)
        );
        if (partialMatch) {
          label.correctZoneId = partialMatch.id;
          matchedZoneIds.add(partialMatch.id);
        } else {
          // Fix 3.3: Log warning instead of creating phantom zone
          console.warn(
            `[normalizeBlueprint] Label "${label.text}" references non-existent zone "${label.correctZoneId}". No matching zone found.`
          );
        }
      }
    }
  });

  return {
    ...input,
    diagram: {
      ...diagram,
      width,
      height,
      zones: normalizedZones,
    },
    labels: normalizedLabels,
  };
};

/**
 * Auto-migrate old multi-scene blueprints where scenes without images
 * should be tasks within the previous scene.
 */
function migrateMultiSceneBlueprint(
  bp: MultiSceneInteractiveDiagramBlueprint
): MultiSceneInteractiveDiagramBlueprint {
  if (!bp.game_sequence?.scenes) return bp;

  // If any scene already has tasks, already migrated
  if (bp.game_sequence.scenes.some(s => s.tasks && s.tasks.length > 0)) return bp;

  const migratedScenes: GameScene[] = [];

  for (const scene of bp.game_sequence.scenes) {
    const hasImage = scene.diagram?.assetUrl;
    const hasZonesOrLabels = (scene.zones?.length || 0) > 0 || (scene.labels?.length || 0) > 0;

    // Only merge into previous scene if:
    // 1. No image of its own
    // 2. Has zones/labels (suggesting it shares the previous scene's diagram)
    // 3. There IS a previous scene to merge into
    // Content-only scenes (no image, no zones, no labels) like sequencing,
    // sorting, memory_match, branching are standalone and should NOT be merged.
    if (!hasImage && hasZonesOrLabels && migratedScenes.length > 0) {
      // No image but has zones/labels — merge as task into previous scene
      const prevScene = migratedScenes[migratedScenes.length - 1];
      // Ensure prev scene has tasks array initialized with its own content as first task
      if (!prevScene.tasks || prevScene.tasks.length === 0) {
        prevScene.tasks = [{
          task_id: `task_${prevScene.scene_id}`,
          title: prevScene.title,
          mechanic_type: (prevScene.mechanics?.[0]?.type || prevScene.interaction_mode) as SceneTask['mechanic_type'],
          zone_ids: (prevScene.zones || []).map(z => z.id),
          label_ids: (prevScene.labels || []).map(l => l.id),
          scoring_weight: 1,
        }];
      }
      // Add this scene as a new task
      prevScene.tasks.push({
        task_id: `task_${scene.scene_id}`,
        title: scene.title,
        mechanic_type: (scene.mechanics?.[0]?.type || scene.interaction_mode) as SceneTask['mechanic_type'],
        zone_ids: (scene.zones || []).map(z => z.id),
        label_ids: (scene.labels || []).map(l => l.id),
        scoring_weight: 1,
        config: scene.sequence_config ? { sequence_config: scene.sequence_config } : undefined,
      });
      // Merge zones/labels into prev scene (dedup by id)
      if (!prevScene.zones) prevScene.zones = [];
      if (!prevScene.labels) prevScene.labels = [];
      const existingZoneIds = new Set(prevScene.zones.map(z => z.id));
      for (const z of (scene.zones || [])) {
        if (!existingZoneIds.has(z.id)) prevScene.zones.push(z);
      }
      const existingLabelIds = new Set(prevScene.labels.map(l => l.id));
      for (const l of (scene.labels || [])) {
        if (!existingLabelIds.has(l.id)) prevScene.labels.push(l);
      }
      // Accumulate max_score
      prevScene.max_score = (prevScene.max_score || 0) + (scene.max_score || 0);
    } else {
      migratedScenes.push({ ...scene });
    }
  }

  if (migratedScenes.length === bp.game_sequence.scenes.length) {
    return bp; // No migration needed
  }

  return {
    ...bp,
    game_sequence: {
      ...bp.game_sequence,
      scenes: migratedScenes,
      total_scenes: migratedScenes.length,
    },
  };
}

/**
 * Inner component that uses accessibility hooks
 * Must be wrapped by AnnouncementProvider
 */
function InteractiveDiagramGameInner({
  blueprint,
  onComplete,
  sessionId,
  gameplayMode = 'learn',
}: InteractiveDiagramGameProps) {
  const {
    availableLabels,
    placedLabels,
    score,
    maxScore,
    isComplete,
    showHints,
    draggingLabelId,
    incorrectFeedback,
    interactionMode,
    pathProgress,
    identificationProgress,
    hierarchyState,
    multiSceneState,
    gameSequence,
    descriptionMatchingState,
    // Multi-mode state (Agentic Interaction Design)
    multiModeState,
    modeTransitions,
    initializeGame,
    placeLabel,
    removeLabel,
    setDraggingLabel,
    toggleHints,
    resetGame,
    clearIncorrectFeedback,
    updatePathProgress,
    updateIdentificationProgress,
    updateHierarchyState,
    completeInteraction,
    // Preset 2: Multi-scene actions
    initializeMultiSceneGame,
    advanceToScene,
    completeScene,
    // Preset 2: Description matching actions
    initializeDescriptionMatching,
    recordDescriptionMatch,
    // Multi-mode actions
    transitionToMode,
    canSwitchToMode,
    // Task actions
    advanceToNextTask,
    getCurrentTask,
    // Fix 1.12: Per-mechanic progress & actions
    sequencingProgress,
    sortingProgress,
    memoryMatchProgress,
    branchingProgress,
    compareProgress,
    updateSequenceOrder,
    submitSequence,
    updateSortingPlacement,
    submitSorting,
    recordMemoryMatch,
    recordMemoryAttempt,
    recordBranchingChoice,
    undoBranchingChoice,
    updateCompareCategorization,
    submitCompare,
  } = useInteractiveDiagramState();

  // Track incorrect attempts for analytics
  const incorrectAttemptsRef = useRef(0);
  const hintsUsedRef = useRef(0);

  // Event logging for analytics (must be before useCommandHistory since it's referenced there)
  const eventLog = useEventLog({
    sessionId,
    gameId: blueprint.title,
    autoLogGameStart: true,
    autoLogZoneReveals: true,
  });

  // Command History for undo/redo
  // Use a ref to get current history length without stale closure
  const historyLengthRef = useRef(0);

  const {
    execute: executeCommand,
    undo,
    redo,
    canUndo,
    canRedo,
    historyState,
    clear: clearHistory,
  } = useCommandHistory({
    enableKeyboardShortcuts: true,
    onUndoRedo: (command, isUndo) => {
      // Log undo/redo events using ref for current value
      if (isUndo) {
        eventLog.logUndo(command.type, command.description, historyLengthRef.current);
      } else {
        eventLog.logRedo(command.type, command.description, historyLengthRef.current);
      }
    },
  });

  // Keep ref in sync with historyState
  useEffect(() => {
    historyLengthRef.current = historyState.historyLength;
  }, [historyState.historyLength]);

  // Screen reader announcements for accessibility
  const { announceGameAction } = useAnnouncements();

  // Persistence for auto-save (only when sessionId is provided)
  const persistence = usePersistence({
    gameId: blueprint.title || 'untitled-game',
    sessionId: sessionId || 'anonymous',
    autoSave: !!sessionId, // Only auto-save if we have a session
    autoSaveInterval: 30000, // 30 seconds
    onSave: () => {
      // Announce save to screen readers
      announceGameAction({ type: 'custom', message: 'Game progress saved', priority: 'polite' });
    },
    onLoad: (savedState) => {
      // Announce load to screen readers
      announceGameAction({ type: 'custom', message: 'Previous game progress restored', priority: 'polite' });
    },
  });

  // Check for and offer to restore saved game
  const [showRestorePrompt, setShowRestorePrompt] = useState(false);
  const [hasSave, setHasSave] = useState(false);

  // Use stable reference for persistence methods
  const hasSavedGameRef = useRef(persistence.hasSavedGame);
  hasSavedGameRef.current = persistence.hasSavedGame;

  useEffect(() => {
    if (!sessionId) return;

    let isMounted = true;

    // Check if there's a saved game on mount
    const checkSavedGame = async () => {
      try {
        const exists = await hasSavedGameRef.current();
        if (isMounted && exists) {
          setHasSave(true);
          setShowRestorePrompt(true);
        }
      } catch (error) {
        console.error('Failed to check for saved game:', error);
      }
    };

    checkSavedGame();

    return () => {
      isMounted = false;
    };
  }, [sessionId]);

  // Handle restore game
  const handleRestoreGame = useCallback(async () => {
    await persistence.loadGame();
    setShowRestorePrompt(false);
  }, [persistence]);

  // Handle start fresh
  const handleStartFresh = useCallback(async () => {
    await persistence.clearSave();
    setShowRestorePrompt(false);
    setHasSave(false);
  }, [persistence]);

  // ─── Layer 4: Parse + validate blueprint via Zod schemas ──────────
  const { parsedBlueprint, validationWarnings, validationErrors } = useMemo(() => {
    const result = parseBlueprint(blueprint);
    if (result.warnings.length > 0) {
      console.warn('[GameDataConfig] Blueprint warnings:', result.warnings);
    }
    if (result.errors.length > 0) {
      console.error('[GameDataConfig] Blueprint errors:', result.errors);
    }
    if (isMultiSceneParseResult(result)) {
      return {
        parsedBlueprint: result.blueprint as InteractiveDiagramBlueprint | MultiSceneInteractiveDiagramBlueprint,
        validationWarnings: result.warnings,
        validationErrors: result.errors,
      };
    }
    return {
      parsedBlueprint: result.blueprint as InteractiveDiagramBlueprint | MultiSceneInteractiveDiagramBlueprint,
      validationWarnings: result.warnings,
      validationErrors: result.errors,
    };
  }, [blueprint]);

  // Check if this is a multi-scene blueprint
  const isMultiScene = isMultiSceneBlueprint(parsedBlueprint);

  // Apply migration to merge broken multi-scene blueprints (scenes without images -> tasks)
  const migratedBlueprint = useMemo(() => {
    if (isMultiScene) {
      return migrateMultiSceneBlueprint(parsedBlueprint as MultiSceneInteractiveDiagramBlueprint);
    }
    return parsedBlueprint;
  }, [parsedBlueprint, isMultiScene]);

  // For multi-scene, don't normalize the whole thing; handle separately
  const normalizedBlueprint = useMemo(() => {
    if (isMultiScene) {
      // Multi-scene: create a stub InteractiveDiagramBlueprint with empty diagram
      // so unconditional accesses to normalizedBlueprint.diagram.zones don't crash.
      // Actual scene rendering uses per-scene data via GameSequenceRenderer.
      const multiBlueprint = migratedBlueprint as MultiSceneInteractiveDiagramBlueprint;
      const firstScene = multiBlueprint.game_sequence?.scenes?.[0];
      return {
        ...migratedBlueprint,
        diagram: {
          zones: firstScene?.zones || [],
          assetUrl: firstScene?.diagram?.assetUrl,
        },
        labels: firstScene?.labels || [],
        interactionMode: (firstScene?.mechanics?.[0]?.type || firstScene?.interaction_mode) as InteractionMode,
      } as unknown as InteractiveDiagramBlueprint;
    }
    return normalizeBlueprint(migratedBlueprint as InteractiveDiagramBlueprint);
  }, [migratedBlueprint, isMultiScene]);

  // Initialize game on mount — use ref guard to prevent re-initialization during gameplay.
  // BUG FIX: Without this guard, if any dependency reference changes (e.g. normalizedBlueprint
  // recreated by useMemo), initializeMultiSceneGame would fire again, resetting currentSceneIndex
  // to 0 and showing scene 1 again mid-gameplay.
  const gameInitializedRef = useRef(false);
  useEffect(() => {
    // Guard: Only initialize once per blueprint. Scene advancement is handled
    // by advanceToScene/initializeGame, NOT by this effect.
    if (gameInitializedRef.current) {
      console.log('[INIT-EFFECT] Skipping — game already initialized');
      return;
    }
    gameInitializedRef.current = true;
    console.log('[INIT-EFFECT] Init useEffect fired! isMultiScene:', isMultiScene);
    if (isMultiScene) {
      // Initialize multi-scene game (using migrated blueprint)
      const multiBlueprint = migratedBlueprint as MultiSceneInteractiveDiagramBlueprint;
      console.log('[INIT-EFFECT] Calling initializeMultiSceneGame with', multiBlueprint.game_sequence?.scenes?.length, 'scenes');
      initializeMultiSceneGame(multiBlueprint.game_sequence);
      // Announce game start
      announceGameAction({
        type: 'game_started',
        title: multiBlueprint.title,
        totalZones: multiBlueprint.game_sequence.scenes.reduce(
          (acc, scene) => acc + (scene.zones?.length || 0),
          0
        ),
      });
    } else {
      initializeGame(normalizedBlueprint);
      // Announce game start
      announceGameAction({
        type: 'game_started',
        title: normalizedBlueprint.title,
        totalZones: normalizedBlueprint.diagram.zones.length,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blueprint]);

  // Handle task/scene advancement via engine's getSceneAction
  // Layer5-Fix-2: Guard against pending mode transitions to prevent race condition
  useEffect(() => {
    if (isComplete && multiSceneState && gameSequence && !multiModeState?.pendingTransition) {
      const action = getSceneAction(multiSceneState, gameSequence);
      console.log('[SCENE-EFFECT] Scene advancement useEffect fired:', {
        isComplete,
        currentSceneIndex: multiSceneState.currentSceneIndex,
        completedSceneIds: multiSceneState.completedSceneIds,
        isSequenceComplete: multiSceneState.isSequenceComplete,
        actionType: action.type,
        pendingTransition: multiModeState?.pendingTransition,
      });
      if (action.type === 'advance_task') {
        const timer = setTimeout(() => {
          console.log('[SCENE-EFFECT] Executing advance_task');
          advanceToNextTask();
        }, 800);
        return () => clearTimeout(timer);
      }
      if (action.type === 'advance_scene') {
        const timer = setTimeout(() => {
          console.log('[SCENE-EFFECT] Executing advance_scene');
          // Delegate to store's completeCurrentScene (accumulates task scores)
          // then advanceToNextScene (uses scene flow graph)
          const store = useInteractiveDiagramState.getState();
          store.completeCurrentScene();
          store.advanceToNextScene();
        }, 800);
        return () => clearTimeout(timer);
      }
      if (action.type === 'complete_game') {
        const timer = setTimeout(() => {
          console.log('[SCENE-EFFECT] Executing complete_game');
          const store = useInteractiveDiagramState.getState();
          store.completeCurrentScene();
          // completeCurrentScene → completeScene sets isSequenceComplete = true
          // which triggers the completion notification useEffect below
        }, 800);
        return () => clearTimeout(timer);
      }
    }
  }, [isComplete, multiSceneState, gameSequence, multiModeState?.pendingTransition, advanceToNextTask]);

  // Notify completion and log analytics
  // Layer5-Fix-5: Use ref to prevent double-firing when maxScore changes
  const completionLoggedRef = useRef(false);
  useEffect(() => {
    if (isComplete && (!multiSceneState || multiSceneState.isSequenceComplete)) {
      if (completionLoggedRef.current) return;
      completionLoggedRef.current = true;

      // Multi-scene: use totalScore from multiSceneState (score was reset to 0 by completeScene)
      const logScore = multiSceneState ? multiSceneState.totalScore : score;
      const logMaxScore = isMultiScene
        ? (migratedBlueprint as MultiSceneInteractiveDiagramBlueprint).game_sequence.total_max_score
        : maxScore;

      const correctPlacements = placedLabels.filter((p) => p.isCorrect).length;
      eventLog.logGameCompleted(
        logScore,
        logMaxScore,
        correctPlacements,
        incorrectAttemptsRef.current,
        hintsUsedRef.current,
        historyState.historyLength,
        0,
        undefined
      );

      announceGameAction({
        type: 'game_completed',
        score: logScore,
        maxScore: logMaxScore,
      });

      if (onComplete) {
        onComplete(logScore);
      }
    } else {
      // Reset when game is no longer complete (e.g., reset/new game)
      completionLoggedRef.current = false;
    }
  }, [isComplete, multiSceneState, score, maxScore, isMultiScene, migratedBlueprint, placedLabels, eventLog, historyState, onComplete, announceGameAction]);

  // Enhanced toggle hints with analytics
  const handleToggleHints = useCallback(() => {
    if (!showHints) {
      hintsUsedRef.current += 1;
      eventLog.logHintRequested('general');
      // Announce hint activation to screen readers
      announceGameAction({
        type: 'hint_shown',
        hintText: 'Hint mode activated. Zones will now show label hints.',
      });
    } else {
      announceGameAction({
        type: 'custom',
        message: 'Hint mode deactivated',
        priority: 'polite',
      });
    }
    toggleHints();
  }, [showHints, toggleHints, eventLog, announceGameAction]);

  // Enhanced reset with history clear
  const handleResetGame = useCallback(() => {
    completionLoggedRef.current = false;
    resetGame();
    clearHistory();
    incorrectAttemptsRef.current = 0;
    hintsUsedRef.current = 0;
    eventLog.resetForNewGame({ gameId: blueprint.title });
    // Re-initialize the game from scratch
    if (isMultiScene) {
      const multiBlueprint = migratedBlueprint as MultiSceneInteractiveDiagramBlueprint;
      initializeMultiSceneGame(multiBlueprint.game_sequence);
    } else {
      initializeGame(normalizedBlueprint);
    }
  }, [resetGame, clearHistory, eventLog, blueprint.title, isMultiScene, migratedBlueprint, normalizedBlueprint, initializeGame, initializeMultiSceneGame]);

  // Clear incorrect feedback after a delay
  useEffect(() => {
    if (incorrectFeedback) {
      const timer = setTimeout(clearIncorrectFeedback, 2000);
      return () => clearTimeout(timer);
    }
  }, [incorrectFeedback, clearIncorrectFeedback]);

  // Configure drag sensors
  const mouseSensor = useSensor(MouseSensor, {
    activationConstraint: {
      distance: 5,
    },
  });
  const touchSensor = useSensor(TouchSensor, {
    activationConstraint: {
      delay: 100,
      tolerance: 5,
    },
  });
  const sensors = useSensors(mouseSensor, touchSensor);

  // ── V4: Unified action dispatch via hook (before drag handlers so they can reference it) ──
  const handleAction = useMechanicDispatch({
    blueprint: normalizedBlueprint,
    placeLabel,
    removeLabel,
    identificationProgress,
    updateIdentificationProgress,
    pathProgress,
    updatePathProgress,
    updateSequenceOrder,
    submitSequence,
    updateSortingPlacement,
    submitSorting,
    recordMemoryMatch,
    recordMemoryAttempt,
    recordBranchingChoice,
    undoBranchingChoice,
    updateCompareCategorization,
    submitCompare,
    recordDescriptionMatch,
  });

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const labelId = event.active.id as string;
      setDraggingLabel(labelId);

      // Log drag start event
      const label = availableLabels.find((l) => l.id === labelId);
      if (label) {
        eventLog.logDragStarted(labelId, label.text, 'tray');
      }
    },
    [setDraggingLabel, availableLabels, eventLog]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      const labelId = active.id as string;
      const label = availableLabels.find((l) => l.id === labelId);

      if (over && active && label) {
        const zoneId = over.id as string;
        // Route through unified dispatch instead of direct store call
        const result = handleAction({ type: 'place', mechanic: 'drag_drop', labelId, zoneId });
        const isCorrect = result?.isCorrect ?? false;
        const zone = normalizedBlueprint.diagram.zones.find((z) => z.id === zoneId);
        const zoneName = zone?.label || zoneId;

        eventLog.logLabelPlaced(labelId, label.text, zoneId, isCorrect);
        announceGameAction({
          type: 'label_placed',
          labelText: label.text,
          zoneName,
          isCorrect,
        });

        if (isCorrect) {
          if (zone) {
            eventLog.logZoneCompleted(zoneId, zone.label || zoneId, labelId, hintsUsedRef.current);
            announceGameAction({
              type: 'zone_completed',
              zoneName,
            });
          }
        } else {
          incorrectAttemptsRef.current += 1;
        }

        eventLog.logDragEnded(labelId, label.text, 'zone', zoneId);
      } else {
        setDraggingLabel(null);
        if (label) {
          eventLog.logDragEnded(labelId, label.text, 'cancelled');
        }
      }
    },
    [handleAction, setDraggingLabel, availableLabels, normalizedBlueprint, eventLog, announceGameAction]
  );

  const handleDragCancel = useCallback(() => {
    const labelId = draggingLabelId;
    setDraggingLabel(null);

    if (labelId) {
      const label = availableLabels.find((l) => l.id === labelId);
      if (label) {
        eventLog.logDragEnded(labelId, label.text, 'cancelled');
      }
    }
  }, [setDraggingLabel, draggingLabelId, availableLabels, eventLog]);

  // LEGACY: handleHotspotClick — replaced by handleAction (V4 unified dispatch)
  // The 'identify' case in handleAction now handles click_to_identify logic.

  const handleGroupExpand = useCallback(
    (groupId: string) => {
      if (!hierarchyState) return;

      updateHierarchyState({
        ...hierarchyState,
        expandedGroups: [...hierarchyState.expandedGroups, groupId],
      });
    },
    [hierarchyState, updateHierarchyState]
  );

  const handleHierarchyLabelPlace = useCallback(
    (labelId: string, zoneId: string, isCorrect: boolean) => {
      if (isCorrect) {
        placeLabel(labelId, zoneId);

        const zoneGroups = normalizedBlueprint.zoneGroups || [];
        const parentGroup = zoneGroups.find((g) => g.parentZoneId === zoneId);

        if (parentGroup && hierarchyState) {
          updateHierarchyState({
            ...hierarchyState,
            completedParentZones: [...hierarchyState.completedParentZones, zoneId],
          });
        }
      }
    },
    [placeLabel, normalizedBlueprint.zoneGroups, hierarchyState, updateHierarchyState]
  );

  // ── V4: Convert legacy PathProgress → TracePathProgress ──
  const traceProgress = useMemo(() => {
    if (!pathProgress) return null;
    return {
      currentPathIndex: 0,
      pathProgressMap: {
        [pathProgress.pathId]: {
          visitedWaypoints: pathProgress.visitedWaypoints,
          isComplete: pathProgress.isComplete,
        },
      },
    };
  }, [pathProgress]);

  // AC-1: Build MechanicRouter props for the current (or per-scene) blueprint
  const buildMechanicRouterProps = useCallback(
    (currentBlueprint?: InteractiveDiagramBlueprint): MechanicRouterProps => {
      const bp = currentBlueprint || normalizedBlueprint;
      // Always use store's interactionMode — it gets updated by mode transitions.
      // Scene blueprints have the STARTING mode, but after transition the store has the CURRENT mode.
      const mode = interactionMode as InteractionMode;

      const progressMap: MechanicProgressMap = {
        identification: identificationProgress,
        trace: traceProgress,
        sequencing: sequencingProgress,
        sorting: sortingProgress,
        memoryMatch: memoryMatchProgress,
        branching: branchingProgress,
        compare: compareProgress,
        descriptionMatching: descriptionMatchingState,
      };

      const dndState: DndState = {
        placedLabels,
        availableLabels,
        draggingLabelId,
        incorrectFeedback,
        showHints,
        sensors,
        onDragStart: handleDragStart,
        onDragEnd: handleDragEnd,
        onDragCancel: handleDragCancel,
      };

      const hierarchicalCallbacks: HierarchicalModeCallbacks = {
        hierarchyState,
        onGroupExpand: handleGroupExpand,
        onHierarchyLabelPlace: handleHierarchyLabelPlace,
      };

      return {
        mode,
        blueprint: bp,
        onAction: handleAction,
        completeInteraction,
        progress: progressMap,
        dnd: dndState,
        hierarchical: hierarchicalCallbacks,
      };
    },
    [
      normalizedBlueprint, interactionMode, handleAction, completeInteraction,
      identificationProgress, traceProgress, sequencingProgress, sortingProgress,
      memoryMatchProgress, branchingProgress, compareProgress, descriptionMatchingState,
      placedLabels, availableLabels, draggingLabelId, incorrectFeedback, showHints, sensors,
      handleDragStart, handleDragEnd, handleDragCancel,
      hierarchyState, handleGroupExpand, handleHierarchyLabelPlace,
    ]
  );

  // [AC-1: renderInteractionContent switch moved to MechanicRouter.tsx — ~400 lines removed]
  // Render scene for multi-scene games
  const renderScene = useCallback(
    (scene: GameScene) => {
      console.log('[RENDER-SCENE] renderScene called:', {
        sceneId: scene.scene_id,
        sceneTitle: scene.title,
        mechanics: scene.mechanics?.map(m => m.type),
        storeInteractionMode: interactionMode,
      });
      // Get current task index for task-aware zone/label filtering
      const taskIdx = multiSceneState?.currentTaskIndex ?? 0;
      const task = scene.tasks?.[taskIdx];

      // Filter zones/labels to task subset when tasks are defined
      let activeZones = scene.zones;
      let activeLabels = scene.labels;
      if (task && task.zone_ids.length > 0) {
        activeZones = scene.zones.filter(z => task.zone_ids.includes(z.id));
      }
      if (task && task.label_ids.length > 0) {
        activeLabels = scene.labels.filter(l => task.label_ids.includes(l.id));
      }

      const startingMode = (task?.mechanic_type
        || scene.mechanics?.[0]?.type
        || scene.interaction_mode
        || 'drag_drop') as InteractionMode;

      // Build per-mechanic config forwarding from registry (camelCase first, snake_case fallback)
      const sceneRecord = scene as unknown as Record<string, unknown>;
      const mechanicConfigs: Record<string, unknown> = {};
      for (const [, entry] of Object.entries(MECHANIC_REGISTRY)) {
        if (entry.configKey) {
          const key = entry.configKey as string;
          const snakeKey = key.replace(/[A-Z]/g, m => '_' + m.toLowerCase());
          mechanicConfigs[key] = sceneRecord[key] || sceneRecord[snakeKey];
        }
      }

      const sceneBlueprint: InteractiveDiagramBlueprint = {
        templateType: 'INTERACTIVE_DIAGRAM',
        title: task?.title || scene.title,
        narrativeIntro: task?.instructions || scene.narrative_intro,
        diagram: {
          assetPrompt: scene.diagram.assetPrompt || scene.title,
          assetUrl: scene.diagram.assetUrl,
          zones: activeZones,
        },
        labels: activeLabels,
        distractorLabels: scene.distractor_labels,
        tasks: [
          {
            id: task?.task_id || `task_${scene.scene_number}`,
            type: 'label_diagram',
            questionText: task?.instructions || scene.narrative_intro,
            requiredToProceed: true,
          },
        ],
        animationCues: {
          correctPlacement: 'Great!',
          incorrectPlacement: 'Try again!',
        },
        mechanics: scene.mechanics || [{ type: startingMode }],
        interactionMode: startingMode,
        modeTransitions: scene.mode_transitions,
        zoneGroups: scene.zoneGroups,
        paths: scene.paths,
        // Registry-driven per-mechanic configs
        ...mechanicConfigs,
        // Non-registry fields that aren't mechanic configs
        temporalConstraints: scene.temporalConstraints || scene.temporal_constraints,
        motionPaths: scene.motionPaths || scene.motion_paths,
        hints: scene.hints,
        scoringStrategy: scene.scoringStrategy || scene.scoring_strategy,
        identificationPrompts: scene.identificationPrompts || scene.identification_prompts,
      };

      // AC-2: MechanicRouter handles its own DndContext — no outer wrapper needed
      return <MechanicRouter {...buildMechanicRouterProps(sceneBlueprint)} />;
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [buildMechanicRouterProps, interactionMode, placedLabels, availableLabels, draggingLabelId, incorrectFeedback, showHints, multiSceneState?.currentTaskIndex]
  );

  // Handle multi-scene sequence completion
  const handleSequenceComplete = useCallback(
    (totalResults: { total_score: number }) => {
      if (onComplete) {
        onComplete(totalResults.total_score);
      }
    },
    [onComplete]
  );

  // ─── Layer 4: Surface fatal validation errors before game starts ──
  if (validationErrors.length > 0) {
    return (
      <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-4 m-4">
        <h3 className="text-red-800 dark:text-red-200 font-semibold">Game Configuration Error</h3>
        <p className="text-red-600 dark:text-red-300 text-sm mt-1">
          The game blueprint has issues that prevent it from loading correctly.
        </p>
        <ul className="list-disc list-inside mt-2 text-sm text-red-700 dark:text-red-300">
          {validationErrors.map((e, i) => <li key={i}>{e}</li>)}
        </ul>
        {validationWarnings.length > 0 && (
          <details className="mt-2">
            <summary className="text-amber-600 dark:text-amber-400 text-sm cursor-pointer">
              {validationWarnings.length} warning(s)
            </summary>
            <ul className="list-disc list-inside mt-1 text-sm text-amber-600 dark:text-amber-400">
              {validationWarnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </details>
        )}
      </div>
    );
  }

  // Show results when complete
  if (isComplete && (!multiSceneState || multiSceneState.isSequenceComplete)) {
    // Get appropriate feedback messages
    const feedbackMessages = isMultiScene
      ? (blueprint as MultiSceneInteractiveDiagramBlueprint).feedbackMessages
      : normalizedBlueprint.feedbackMessages;

    // Multi-scene: use accumulated totals from multiSceneState
    const finalScore = isMultiScene && multiSceneState
      ? multiSceneState.totalScore
      : score;
    const finalMaxScore = isMultiScene
      ? (migratedBlueprint as MultiSceneInteractiveDiagramBlueprint).game_sequence.total_max_score
      : maxScore;
    const finalSceneResults = isMultiScene && multiSceneState
      ? multiSceneState.sceneResults
      : undefined;
    const finalSceneNames = isMultiScene
      ? (migratedBlueprint as MultiSceneInteractiveDiagramBlueprint).game_sequence.scenes.map(s => s.title)
      : undefined;

    return (
      <div className="game-container">
        <ResultsPanel
          score={finalScore}
          maxScore={finalMaxScore}
          feedbackMessages={feedbackMessages}
          onPlayAgain={handleResetGame}
          sceneResults={finalSceneResults}
          sceneNames={finalSceneNames}
        />
      </div>
    );
  }

  // Multi-scene game rendering (Preset 2)
  if (isMultiScene) {
    const multiBlueprint = migratedBlueprint as MultiSceneInteractiveDiagramBlueprint;
    const sequence = multiBlueprint.game_sequence;

    // HAD v3: Track completed scenes for indicator
    const completedSceneIds = multiSceneState?.completedSceneIds || [];
    const currentSceneIndex = multiSceneState?.currentSceneIndex ?? 0;

    // Derive total game score: accumulated completed scenes + current scene in progress
    const totalGameScore = (multiSceneState?.totalScore ?? 0) + score;
    const totalGameMaxScore = sequence.total_max_score;

    return (
      <div className="game-container">
        {/* Title and intro */}
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2">{multiBlueprint.title}</h1>
          <p className="text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">{multiBlueprint.narrativeIntro}</p>
        </div>

        {/* HAD v3: Scene progress indicator with per-scene scores */}
        <SceneIndicator
          totalScenes={sequence.total_scenes}
          currentScene={currentSceneIndex + 1}
          completedScenes={completedSceneIds.map((_, i) => i + 1)}
          sceneResults={multiSceneState?.sceneResults}
          sceneNames={sequence.scenes.map(s => s.title)}
        />

        {/* Game controls with two-tier score + task progress */}
        <div className="mb-4">
          <GameControls
            showHints={showHints}
            onToggleHints={handleToggleHints}
            onReset={handleResetGame}
            hasHints={false}
            score={score}
            maxScore={maxScore}
            totalScore={totalGameScore}
            totalMaxScore={totalGameMaxScore}
            taskProgress={(() => {
              const currentScene = sequence.scenes[currentSceneIndex];
              const tasks = currentScene?.tasks || [];
              return tasks.length > 1
                ? {
                    tasks,
                    currentTaskIndex: multiSceneState?.currentTaskIndex ?? 0,
                    taskResults: multiSceneState?.taskResults ?? [],
                  }
                : undefined;
            })()}
          />
        </div>

        {/* Multi-scene renderer */}
        <GameSequenceRenderer
          sequence={sequence}
          renderScene={renderScene}
          onSequenceComplete={handleSequenceComplete}
        />
      </div>
    );
  }

  // Single-scene game rendering (Preset 1 default)
  return (
    <div className="game-container">
      {/* Title and intro */}
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2">{normalizedBlueprint.title}</h1>
        <p className="text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">{normalizedBlueprint.narrativeIntro}</p>
      </div>

      {/* AC-2: DndContext moved inside MechanicRouter — only wraps drag-based mechanics */}

      {/* Game controls with undo/redo and mode indicator */}
      <div className="flex items-center justify-between mb-4">
        <GameControls
          showHints={showHints}
          onToggleHints={handleToggleHints}
          onReset={handleResetGame}
          hasHints={!!normalizedBlueprint.hints?.length}
          score={score}
          maxScore={maxScore}
          taskProgress={
            multiSceneState && gameSequence
              ? (() => {
                  const currentScene = gameSequence.scenes[multiSceneState.currentSceneIndex];
                  const tasks = currentScene?.tasks || [];
                  return tasks.length > 1
                    ? {
                        tasks,
                        currentTaskIndex: multiSceneState.currentTaskIndex,
                        taskResults: multiSceneState.taskResults,
                      }
                    : undefined;
                })()
              : undefined
          }
        />
        <div className="flex items-center gap-4">
          {/* Multi-mode indicator (when enabled) */}
          {multiModeState && (
            <ModeIndicator
              currentMode={interactionMode}
              multiModeState={multiModeState}
              onModeSwitch={(mode) => {
                if (canSwitchToMode(mode)) {
                  transitionToMode(mode);
                }
              }}
              allowManualSwitch={modeTransitions.some(t => t.trigger === 'user_choice')}
              showProgress={true}
              pendingTransition={multiModeState.pendingTransition}
              position="inline"
            />
          )}
          {/* Undo/Redo controls */}
          <UndoRedoControls
            position="inline"
            showTooltips={true}
            showKeyboardHints={true}
          />
        </div>
      </div>

      {/* QW-4: Per-mechanic instructions — registry-driven */}
      {/* Skip for mechanics that render their own instruction box (sequencing, sorting, memory_match, branching, compare) */}
      {(() => {
        const modesWithOwnInstructions: InteractionMode[] = [
          'sequencing', 'sorting_categories', 'memory_match',
          'branching_scenario', 'compare_contrast', 'trace_path',
        ];
        if (modesWithOwnInstructions.includes(interactionMode as InteractionMode)) return null;
        const currentTask = getCurrentTask();
        const instructionText =
          currentTask?.instructions
          || getRegistryInstructions(interactionMode as InteractionMode, normalizedBlueprint)
          || normalizedBlueprint.tasks?.[0]?.questionText;
        return instructionText ? (
          <div className="my-4 p-4 bg-blue-50 rounded-lg">
            <p className="text-blue-800 font-medium">{instructionText}</p>
          </div>
        ) : null;
      })()}

      {/* Render interaction content based on mode, with transition animation */}
      {multiModeState?.pendingTransition ? (
        <div
          className="mode-transition-overlay"
          data-animation={multiModeState.pendingTransition.animation || 'fade'}
        >
          <div className="mode-transition-message">
            <p className="text-lg font-medium text-gray-700 dark:text-gray-200">
              {multiModeState.pendingTransition.message || `Switching to ${multiModeState.pendingTransition.to.replace('_', ' ')} mode...`}
            </p>
          </div>
        </div>
      ) : (
        <div className="mode-transition-content">
          <MechanicRouter {...buildMechanicRouterProps()} />
        </div>
      )}

      {/* Restore prompt for saved games */}
      {showRestorePrompt && hasSave && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md shadow-xl" role="dialog" aria-labelledby="restore-dialog-title" aria-modal="true">
            <h2 id="restore-dialog-title" className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">
              Resume Previous Game?
            </h2>
            <p className="text-gray-600 dark:text-gray-300 mb-6">
              You have a saved game in progress. Would you like to continue where you left off?
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleStartFresh}
                className="px-4 py-2 text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                aria-label="Start a new game"
              >
                Start Fresh
              </button>
              <button
                onClick={handleRestoreGame}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                aria-label="Resume saved game"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save indicator */}
      {persistence.isSaving && (
        <div className="fixed bottom-4 right-4 bg-gray-800 dark:bg-gray-700 text-white px-3 py-2 rounded-lg text-sm shadow-lg" role="status" aria-live="polite">
          Saving...
        </div>
      )}
      {persistence.lastSaveTime && !persistence.isSaving && (
        <div className="fixed bottom-4 right-4 text-gray-500 dark:text-gray-400 text-xs" aria-hidden="true">
          Last saved: {new Date(persistence.lastSaveTime).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}

/**
 * Main exported component with accessibility providers and error boundary
 *
 * Wraps the game with:
 * - GameErrorBoundary for graceful error handling
 * - AnnouncementProvider for screen reader announcements
 * - KeyboardNav for enhanced keyboard navigation
 */
export default function InteractiveDiagramGame(props: InteractiveDiagramGameProps) {
  return (
    <GameErrorBoundary
      onError={(error, errorInfo) => {
        // Log to console (could also send to analytics service)
        console.error('InteractiveDiagramGame error:', error.message, errorInfo.componentStack);
      }}
    >
      <AnnouncementProvider>
        <KeyboardNav
          enabled={true}
          wrapAround={true}
          customHandlers={{
            // Allow Escape to reset focus
            Escape: () => {
              const activeElement = document.activeElement as HTMLElement;
              activeElement?.blur();
            },
          }}
        >
          <InteractiveDiagramGameInner {...props} />
        </KeyboardNav>
      </AnnouncementProvider>
    </GameErrorBoundary>
  );
}

export { default as DiagramLabelingHarness } from './Harness';
