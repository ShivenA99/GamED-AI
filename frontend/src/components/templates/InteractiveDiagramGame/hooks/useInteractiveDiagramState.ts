import { create } from 'zustand';
import {
  Label,
  PlacedLabel,
  InteractiveDiagramBlueprint,
  DistractorLabel,
  InteractionMode,
  PathProgress,
  IdentificationProgress,
  HierarchyState,
  MultiSceneState,
  DescriptionMatchingState,
  DescriptionMatch,
  GameSequence,
  SceneResult,
  SceneTask,
  TaskResult,
  TemporalConstraint,
  MotionPath,
  MultiModeState,
  ModeTransition,
  // Fix 1.7b: Per-mechanic progress types
  SequencingProgress,
  SortingProgress,
  MemoryMatchProgress,
  BranchingProgress,
  CompareProgress,
} from '../types';
import type { MechanicProgressMap, EngineExtra } from '../mechanicRegistry';
import { getMaxScore, getScoringConfig, calculateScoreDelta } from '../engine/scoringEngine';
import type { ScoringConfig } from '../engine/scoringEngine';
import { hasRemainingModes } from '../engine/completionDetector';
import { evaluateTransitions } from '../engine/transitionEvaluator';
import { sceneToBlueprint } from '../engine/sceneManager';
import { initializeMechanicProgress } from '../engine/mechanicInitializer';
import { getFeedback } from '../engine/feedbackEngine';
import { evaluateIdentification, evaluateDescriptionMatch } from '../engine/correctnessEvaluator';
import { getNextSceneId } from '../engine/sceneFlowGraph';
import type { SceneFlowGraph } from '../engine/sceneFlowGraph';

// sceneToBlueprint is now in engine/sceneManager.ts as sceneToBlueprint

/** Build MechanicProgressMap from current store state */
function _buildProgressMap(state: InteractiveDiagramState): MechanicProgressMap {
  // Convert store PathProgress → TracePathProgress for registry compatibility
  const traceProgress = state.pathProgress ? {
    currentPathIndex: 0,
    pathProgressMap: {
      [state.pathProgress.pathId]: {
        visitedWaypoints: state.pathProgress.visitedWaypoints,
        isComplete: state.pathProgress.isComplete,
      },
    },
  } : null;

  return {
    identification: state.identificationProgress,
    trace: traceProgress,
    sequencing: state.sequencingProgress,
    sorting: state.sortingProgress,
    memoryMatch: state.memoryMatchProgress,
    branching: state.branchingProgress,
    compare: state.compareProgress,
    descriptionMatching: state.descriptionMatchingState,
  };
}

/** Get task label count for per-task label counting */
function _getTaskLabelCount(state: InteractiveDiagramState): number | undefined {
  const ms = state.multiSceneState;
  if (ms && state.gameSequence) {
    const scene = state.gameSequence.scenes[ms.currentSceneIndex];
    const task = scene?.tasks?.[ms.currentTaskIndex];
    if (task && task.label_ids.length > 0) {
      return task.label_ids.length;
    }
  }
  return undefined;
}

/** Build EngineExtra from current store state */
function _buildExtra(state: InteractiveDiagramState): EngineExtra {
  return {
    placedLabels: state.placedLabels,
    taskLabelCount: _getTaskLabelCount(state) ?? state.blueprint?.labels.length,
    hierarchyState: state.hierarchyState,
  };
}

interface InteractiveDiagramState {
  // Labels that haven't been placed yet
  availableLabels: (Label | DistractorLabel)[];
  // Labels that have been placed on zones
  placedLabels: PlacedLabel[];
  // Current score
  score: number;
  // Total possible score
  maxScore: number;
  // Points per zone from blueprint scoring strategy
  basePointsPerZone: number;
  // Whether the game is complete
  isComplete: boolean;
  // Hint visibility state
  showHints: boolean;
  // Currently dragged label
  draggingLabelId: string | null;
  // Feedback for incorrect placement
  incorrectFeedback: { labelId: string; message: string } | null;
  // Blueprint reference
  blueprint: InteractiveDiagramBlueprint | null;
  // QW-8: Original blueprint stored at init for proper reset
  originalBlueprint: InteractiveDiagramBlueprint | null;
  // Interaction mode
  interactionMode: InteractionMode;
  // Path tracing progress (for trace_path mode)
  pathProgress: PathProgress | null;
  // Click-to-identify progress
  identificationProgress: IdentificationProgress | null;
  // Hierarchical state
  hierarchyState: HierarchyState | null;

  // Preset 2: Multi-scene state
  multiSceneState: MultiSceneState | null;
  gameSequence: GameSequence | null;

  // Preset 2: Description matching state
  descriptionMatchingState: DescriptionMatchingState | null;

  // Temporal Intelligence state
  temporalConstraints: TemporalConstraint[];
  motionPaths: MotionPath[];
  completedZoneIds: Set<string>;  // Zones that have been correctly labeled
  visibleZoneIds: Set<string>;    // Zones currently visible (respecting temporal constraints)
  blockedZoneIds: Set<string>;    // Zones blocked by mutex constraints

  // Multi-mode state (Agentic Interaction Design)
  multiModeState: MultiModeState | null;
  modeTransitions: ModeTransition[];

  // Fix 1.5: Transition timer for cleanup
  _transitionTimerId: ReturnType<typeof setTimeout> | null;

  // Fix 1.7b: Per-mechanic progress (Zustand-tracked)
  sequencingProgress: SequencingProgress | null;
  sortingProgress: SortingProgress | null;
  memoryMatchProgress: MemoryMatchProgress | null;
  branchingProgress: BranchingProgress | null;
  compareProgress: CompareProgress | null;

  // Layer 5: Scoring config for current mode (read from blueprint)
  scoringConfig: ScoringConfig;

  // Actions
  initializeGame: (blueprint: InteractiveDiagramBlueprint) => void;
  placeLabel: (labelId: string, zoneId: string) => boolean;
  removeLabel: (labelId: string) => void;
  setDraggingLabel: (labelId: string | null) => void;
  toggleHints: () => void;
  resetGame: () => void;
  clearIncorrectFeedback: () => void;
  // New actions for different interaction modes
  updatePathProgress: (pathProgress: PathProgress) => void;
  updateIdentificationProgress: (progress: IdentificationProgress) => void;
  updateHierarchyState: (state: HierarchyState) => void;
  completeInteraction: () => void;

  // Preset 2: Multi-scene actions
  initializeMultiSceneGame: (sequence: GameSequence) => void;
  advanceToScene: (sceneIndex: number) => void;
  completeScene: (result: SceneResult) => void;

  // Preset 2: Description matching actions
  initializeDescriptionMatching: (mode: 'click_zone' | 'drag_description' | 'multiple_choice') => void;
  recordDescriptionMatch: (match: DescriptionMatch) => void;

  // Fix 1.7b: Per-mechanic actions
  updateSequenceOrder: (itemOrder: string[]) => void;
  submitSequence: () => void;
  updateSortingPlacement: (itemId: string, categoryId: string | null) => void;
  submitSorting: () => void;
  recordMemoryMatch: (pairId: string) => void;
  recordMemoryAttempt: () => void;
  recordBranchingChoice: (nodeId: string, optionId: string, isCorrect: boolean, nextNodeId: string | null) => void;
  undoBranchingChoice: () => void;
  updateCompareCategorization: (zoneId: string, category: string) => void;
  submitCompare: () => void;

  // Temporal Intelligence actions
  updateVisibleZones: () => void;
  getVisibleZones: () => Set<string>;
  isZoneVisible: (zoneId: string) => boolean;
  isZoneBlocked: (zoneId: string) => boolean;

  // Multi-mode actions (Agentic Interaction Design)
  initializeMultiMode: (mechanics: InteractionMode[], transitions: ModeTransition[]) => void;
  checkModeTransition: () => void;
  transitionToMode: (newMode: InteractionMode, transition?: ModeTransition) => void;
  getAvailableModes: () => InteractionMode[];
  canSwitchToMode: (mode: InteractionMode) => boolean;

  // Scene lifecycle actions
  completeCurrentScene: () => void;
  advanceToNextScene: () => void;

  // Task lifecycle actions (tasks within a scene)
  advanceToNextTask: () => void;
  getCurrentTask: () => SceneTask | null;
}

export const useInteractiveDiagramState = create<InteractiveDiagramState>((set, get) => ({
  availableLabels: [],
  placedLabels: [],
  score: 0,
  maxScore: 0,
  basePointsPerZone: 10,
  isComplete: false,
  showHints: false,
  draggingLabelId: null,
  incorrectFeedback: null,
  blueprint: null,
  originalBlueprint: null,
  interactionMode: '' as InteractionMode, // Pre-init; overwritten by initializeGame
  pathProgress: null,
  identificationProgress: null,
  hierarchyState: null,
  multiSceneState: null,
  gameSequence: null,
  descriptionMatchingState: null,
  // Temporal Intelligence state
  temporalConstraints: [],
  motionPaths: [],
  completedZoneIds: new Set(),
  visibleZoneIds: new Set(),
  blockedZoneIds: new Set(),

  // Multi-mode state
  multiModeState: null,
  modeTransitions: [],

  // Fix 1.5: Timer cleanup
  _transitionTimerId: null,

  // Fix 1.7b: Per-mechanic progress defaults
  sequencingProgress: null,
  sortingProgress: null,
  memoryMatchProgress: null,
  branchingProgress: null,
  compareProgress: null,

  // Layer 5: Default scoring config
  scoringConfig: { basePointsPerItem: 10, partialCredit: false, timeBonusEnabled: false, timeBonusMaxSeconds: 120, timeBonusMultiplier: 1.5, attemptPenalty: 0, maxAttempts: 0, streakMultiplier: 1 },

  initializeGame: (blueprint: InteractiveDiagramBlueprint) => {
    console.log('[INIT-GAME] initializeGame called:', {
      title: blueprint.title,
      interactionMode: blueprint.interactionMode,
      mechanics: blueprint.mechanics?.map(m => m.type),
      zones: blueprint.diagram?.zones?.length,
      labels: blueprint.labels?.length,
      hasSequenceConfig: !!(blueprint as unknown as Record<string, unknown>).sequenceConfig,
      hasSortingConfig: !!(blueprint as unknown as Record<string, unknown>).sortingConfig,
    });

    // Combine regular labels with distractor labels and shuffle
    const allLabels: (Label | DistractorLabel)[] = [
      ...blueprint.labels,
      ...(blueprint.distractorLabels || []),
    ];

    // Shuffle the labels
    const shuffled = [...allLabels].sort(() => Math.random() - 0.5);

    // Derive mechanics list and starting mode
    const mechanics = blueprint.mechanics || [];
    const interactionMode = (mechanics[0]?.type || blueprint.interactionMode) as InteractionMode;
    console.log('[INIT-GAME] Derived interactionMode:', interactionMode, 'from mechanics:', mechanics.map(m => m.type));

    // Layer 5: Initialize all per-mechanic progress via registry
    const mechanicState = initializeMechanicProgress(interactionMode, blueprint);

    // Initialize temporal intelligence state
    const temporalConstraints = blueprint.temporalConstraints || [];
    const motionPaths = blueprint.motionPaths || [];

    // Synthesize zoneGroups into temporal constraints for progressive reveal
    const zoneGroupConstraints: TemporalConstraint[] = [];
    for (const group of blueprint.zoneGroups || []) {
      if (group.revealTrigger === 'complete_parent') {
        for (const childId of group.childZoneIds) {
          zoneGroupConstraints.push({
            zone_a: group.parentZoneId,
            zone_b: childId,
            constraint_type: 'after',
            reason: `Zone group ${group.id}: reveal after parent complete`,
            priority: 50,
          });
        }
      }
      // click_expand and hover_reveal are handled via hierarchyState
    }
    const allTemporalConstraints = [...temporalConstraints, ...zoneGroupConstraints];

    // Initialize multi-mode state if multiple mechanics exist
    let multiModeState: MultiModeState | null = null;
    const modeTransitions = blueprint.modeTransitions || [];
    const allModes = [...new Set(mechanics.map(m => m.type))];

    if (allModes.length > 1 || modeTransitions.length > 0) {
      multiModeState = {
        currentMode: interactionMode,
        completedModes: [],
        modeHistory: [{
          mode: interactionMode,
          startTime: Date.now(),
          score: 0,
        }],
        pendingTransition: undefined,
        availableModes: allModes.length > 0 ? allModes : [interactionMode],
      };
    }

    // Compute initial visible zones (root zones or hierarchy level 1)
    const initialVisibleZones = new Set<string>();
    const zones = blueprint.diagram.zones || [];
    for (const zone of zones) {
      // Show zones without parents or with hierarchy level 1
      if (!zone.parentZoneId && (zone.hierarchyLevel === 1 || !zone.hierarchyLevel)) {
        initialVisibleZones.add(zone.id);
      }
    }

    // Layer 5: Read scoring config from blueprint for current mode
    const scoringConfig = getScoringConfig(interactionMode, blueprint);
    const basePointsPerZone = scoringConfig.basePointsPerItem;
    // Calculate max score for the FIRST mode only (not total).
    // Multi-mode games accumulate maxScore in transitionToMode().
    // Using scoringStrategy.max_score (which is the TOTAL across all mechanics)
    // would cause double-counting since transitions add per-mode maxes on top.
    const maxScoreFromStrategy = multiModeState
      ? getMaxScore(interactionMode, blueprint, basePointsPerZone)
      : (blueprint.scoringStrategy?.max_score
        ?? getMaxScore(interactionMode, blueprint, basePointsPerZone));
    console.log('[SCORE] initializeGame mode:', interactionMode, 'multiMode:', !!multiModeState, 'maxScore:', maxScoreFromStrategy, 'basePointsPerZone:', basePointsPerZone);

    // QW-8: Store original blueprint only on first init (not on sub-scene init)
    const existingOriginal = get().originalBlueprint;

    set({
      availableLabels: shuffled,
      placedLabels: [],
      score: 0,
      maxScore: maxScoreFromStrategy,
      basePointsPerZone,
      scoringConfig,
      isComplete: false,
      showHints: false,
      draggingLabelId: null,
      incorrectFeedback: null,
      blueprint,
      originalBlueprint: existingOriginal || blueprint,
      interactionMode,
      // Layer 5: Per-mechanic progress from registry-driven initializer
      ...mechanicState,
      _transitionTimerId: null,
      // Temporal intelligence (includes synthesized zoneGroup constraints)
      temporalConstraints: allTemporalConstraints,
      motionPaths,
      completedZoneIds: new Set(),
      visibleZoneIds: initialVisibleZones,
      blockedZoneIds: new Set(),
      // Multi-mode state
      multiModeState,
      modeTransitions,
    });

    // Update visible zones based on temporal constraints
    get().updateVisibleZones();
  },

  placeLabel: (labelId: string, zoneId: string) => {
    const state = get();
    const { blueprint, availableLabels, placedLabels } = state;

    if (!blueprint) return false;

    // Enforce temporal constraints — reject placement on hidden/blocked zones
    if (state.temporalConstraints.length > 0 && !state.visibleZoneIds.has(zoneId)) {
      set({
        draggingLabelId: null,
        incorrectFeedback: { labelId, message: 'This zone is not yet available.' },
      });
      return false;
    }

    // Find the label being placed
    const label = availableLabels.find((l) => l.id === labelId);
    if (!label) return false;

    // Check if this is a distractor label (no correctZoneId)
    const isDistractor = !('correctZoneId' in label);

    // Check if placement is correct
    let isCorrect = false;
    if (!isDistractor && 'correctZoneId' in label) {
      isCorrect = label.correctZoneId === zoneId;
    }

    if (isCorrect) {
      // Correct placement
      const newPlacedLabels = [...placedLabels, { labelId, zoneId, isCorrect: true }];
      const newAvailableLabels = availableLabels.filter((l) => l.id !== labelId);
      // Completion check via engine
      const taskLabelCount = _getTaskLabelCount(state) ?? blueprint.labels.length;
      const placedCorrectCount = newPlacedLabels.filter((p) => p.isCorrect).length;
      const allLabelsPlaced = placedCorrectCount >= taskLabelCount;
      const isComplete = allLabelsPlaced && !hasRemainingModes(state.multiModeState);

      // Update temporal state - add zone to completed set
      const newCompletedZoneIds = new Set(state.completedZoneIds);
      newCompletedZoneIds.add(zoneId);

      // Layer 5: Use scoring engine for delta
      const scoreDelta = calculateScoreDelta(state.scoringConfig, { isCorrect: true });
      console.log('[SCORE] placeLabel correct:', labelId, '→', zoneId, 'delta:', scoreDelta, 'new score:', state.score + scoreDelta, 'placed:', placedCorrectCount, '/', taskLabelCount);

      set({
        availableLabels: newAvailableLabels,
        placedLabels: newPlacedLabels,
        score: state.score + scoreDelta,
        isComplete,
        draggingLabelId: null,
        incorrectFeedback: null,
        completedZoneIds: newCompletedZoneIds,
      });

      // Update visible zones after placement (may reveal children, unblock mutex)
      get().updateVisibleZones();

      // Check for mode transitions even when labels are done (triggers next mechanic)
      if (allLabelsPlaced || !isComplete) {
        get().checkModeTransition();
      }

      return true;
    } else {
      // Incorrect placement — Layer 5: Use feedback engine
      let message: string;
      if (isDistractor && 'explanation' in label) {
        message = label.explanation;
      } else {
        const fb = getFeedback(state.interactionMode, 'incorrect', blueprint, { labelId, zoneId });
        message = fb.message;
      }

      // Layer 5: Apply attempt penalty if configured
      const penalty = calculateScoreDelta(state.scoringConfig, { isCorrect: false });

      set({
        draggingLabelId: null,
        incorrectFeedback: { labelId, message },
        score: Math.max(0, state.score + penalty),
      });

      return false;
    }
  },

  removeLabel: (labelId: string) => {
    const state = get();
    const { blueprint, placedLabels, availableLabels } = state;

    if (!blueprint) return;

    const placed = placedLabels.find((p) => p.labelId === labelId);
    if (!placed) return;

    // Find the original label
    const originalLabel = blueprint.labels.find((l) => l.id === labelId);
    if (!originalLabel) return;

    // Fix 1.1: Remove zone from completedZoneIds
    const newCompletedZoneIds = new Set(state.completedZoneIds);
    newCompletedZoneIds.delete(placed.zoneId);

    set({
      placedLabels: placedLabels.filter((p) => p.labelId !== labelId),
      availableLabels: [...availableLabels, originalLabel],
      score: Math.max(0, state.score - state.scoringConfig.basePointsPerItem),
      isComplete: false,
      completedZoneIds: newCompletedZoneIds,
    });

    // Recalculate visible zones (may hide children, re-block mutex partners)
    get().updateVisibleZones();
  },

  setDraggingLabel: (labelId: string | null) => {
    set({ draggingLabelId: labelId, incorrectFeedback: null });
  },

  toggleHints: () => {
    set((state) => ({ showHints: !state.showHints }));
  },

  resetGame: () => {
    // QW-8: Use originalBlueprint (top-level) for proper full reset, not scene-scoped blueprint
    const { originalBlueprint, blueprint } = get();
    const resetTarget = originalBlueprint || blueprint;
    if (resetTarget) {
      // Clear originalBlueprint so initializeGame re-stores it
      set({ originalBlueprint: null });
      get().initializeGame(resetTarget);
    }
  },

  clearIncorrectFeedback: () => {
    set({ incorrectFeedback: null });
  },

  updatePathProgress: (pathProgress: PathProgress) => {
    const state = get();
    // Fix 1.2A: Delta-based scoring — don't overwrite existing score
    // Fix: When pathId changes (multi-path), reset prevWaypoints to 0
    // to avoid subtracting the first path's waypoint count from the second path's.
    const samePathId = state.pathProgress?.pathId === pathProgress.pathId;
    const prevWaypoints = samePathId ? (state.pathProgress?.visitedWaypoints.length || 0) : 0;
    const newWaypoints = pathProgress.visitedWaypoints.length;
    const newWaypointCount = newWaypoints - prevWaypoints;
    // Layer 5: Use scoring config for per-waypoint delta
    let delta = 0;
    for (let i = 0; i < newWaypointCount; i++) {
      delta += calculateScoreDelta(state.scoringConfig, { isCorrect: true });
    }
    const isComplete = pathProgress.isComplete;
    console.log('[SCORE] updatePathProgress:', pathProgress.pathId, 'samePathId:', samePathId, 'prev:', prevWaypoints, 'new:', newWaypoints, 'delta:', delta, 'score:', state.score, '→', state.score + delta, 'isComplete:', isComplete);

    set({
      pathProgress,
      score: state.score + delta,
      isComplete,
    });

    // Trigger mode transition check on completion
    if (isComplete) {
      get().checkModeTransition();
    }
  },

  updateIdentificationProgress: (progress: IdentificationProgress) => {
    const state = get();
    const { blueprint } = state;

    if (!blueprint) return;

    // Fix 1.2B: Delta-based scoring — don't overwrite existing score
    const prevCompleted = state.identificationProgress?.completedZoneIds.length || 0;
    const newCompleted = progress.completedZoneIds.length;
    const newCount = newCompleted - prevCompleted;
    // Layer 5: Use scoring config for delta
    let delta = 0;
    for (let i = 0; i < newCount; i++) {
      delta += calculateScoreDelta(state.scoringConfig, { isCorrect: true });
    }

    const totalPrompts = blueprint.identificationPrompts?.length || 0;
    const isComplete = progress.currentPromptIndex >= totalPrompts;

    set({
      identificationProgress: progress,
      score: state.score + delta,
      isComplete,
    });

    // Trigger mode transition check on completion
    if (isComplete) {
      get().checkModeTransition();
    }
  },

  updateHierarchyState: (hierarchyState: HierarchyState) => {
    set({ hierarchyState });
  },

  completeInteraction: () => {
    const state = get();
    const { interactionMode, blueprint } = state;

    if (!blueprint) return;

    // Check if there are remaining modes before ending the game
    if (hasRemainingModes(state.multiModeState)) {
      get().checkModeTransition();
      return;
    }

    // Don't overwrite accumulated maxScore — it was built up through
    // initializeGame (first mode) + transitionToMode (subsequent modes).
    set({
      isComplete: true,
    });
  },

  // =============================================================================
  // PRESET 2: MULTI-SCENE ACTIONS
  // =============================================================================

  initializeMultiSceneGame: (sequence: GameSequence) => {
    const firstScene = sequence.scenes[0];
    if (!firstScene) return;

    // Initialize multi-scene state
    const multiSceneState: MultiSceneState = {
      currentSceneIndex: 0,
      completedSceneIds: [],
      sceneResults: [],
      totalScore: 0,
      isSequenceComplete: false,
      currentTaskIndex: 0,
      taskResults: [],
    };

    // Convert first scene to blueprint-like format for game initialization
    const sceneBlueprint: InteractiveDiagramBlueprint = sceneToBlueprint(firstScene, 0);

    set({
      multiSceneState,
      gameSequence: sequence,
      maxScore: sequence.total_max_score,
    });

    // Initialize the first scene
    get().initializeGame(sceneBlueprint);
  },

  advanceToScene: (sceneIndex: number) => {
    const { gameSequence, multiSceneState } = get();
    if (!gameSequence || !multiSceneState) return;

    const scene = gameSequence.scenes[sceneIndex];
    if (!scene) return;

    console.log('[SCENE-ADV] advanceToScene called:', {
      sceneIndex,
      sceneTitle: scene.title,
      sceneId: scene.scene_id,
      mechanics: scene.mechanics?.map(m => m.type),
      hasSequenceConfig: !!scene.sequenceConfig,
      hasSortingConfig: !!scene.sortingConfig,
      zones: scene.zones?.length,
      labels: scene.labels?.length,
    });

    // Convert scene to blueprint format
    const sceneBlueprint: InteractiveDiagramBlueprint = sceneToBlueprint(scene, sceneIndex);

    console.log('[SCENE-ADV] sceneBlueprint:', {
      title: sceneBlueprint.title,
      interactionMode: sceneBlueprint.interactionMode,
      mechanics: sceneBlueprint.mechanics?.map(m => m.type),
      zones: sceneBlueprint.diagram?.zones?.length,
      labels: sceneBlueprint.labels?.length,
      hasSequenceConfig: !!(sceneBlueprint as unknown as Record<string, unknown>).sequenceConfig,
      hasSortingConfig: !!(sceneBlueprint as unknown as Record<string, unknown>).sortingConfig,
    });

    set({
      multiSceneState: {
        ...multiSceneState,
        currentSceneIndex: sceneIndex,
        currentTaskIndex: 0,
      },
    });

    // Initialize the scene
    get().initializeGame(sceneBlueprint);

    console.log('[SCENE-ADV] After initializeGame:', {
      interactionMode: get().interactionMode,
      currentSceneIndex: get().multiSceneState?.currentSceneIndex,
      isComplete: get().isComplete,
    });
  },

  completeScene: (result: SceneResult) => {
    const { gameSequence, multiSceneState } = get();
    if (!gameSequence || !multiSceneState) return;

    const newSceneResults = [...multiSceneState.sceneResults, result];
    const newTotalScore = newSceneResults.reduce((sum, r) => sum + r.score, 0);
    const newCompletedIds = [...multiSceneState.completedSceneIds, result.scene_id];
    const isSequenceComplete = newCompletedIds.length >= gameSequence.total_scenes;

    set({
      multiSceneState: {
        ...multiSceneState,
        completedSceneIds: newCompletedIds,
        sceneResults: newSceneResults,
        totalScore: newTotalScore,
        isSequenceComplete,
      },
      score: 0,  // Reset for next scene — total lives in multiSceneState.totalScore
      isComplete: isSequenceComplete,
    });
  },

  // =============================================================================
  // PRESET 2: DESCRIPTION MATCHING ACTIONS
  // =============================================================================

  initializeDescriptionMatching: (mode: 'click_zone' | 'drag_description' | 'multiple_choice') => {
    set({
      descriptionMatchingState: {
        currentIndex: 0,
        matches: [],
        mode,
      },
    });
  },

  recordDescriptionMatch: (match: DescriptionMatch) => {
    const state = get();
    const { descriptionMatchingState, blueprint } = state;
    if (!descriptionMatchingState || !blueprint) return;

    const newMatches = [...descriptionMatchingState.matches, match];
    const newIndex = descriptionMatchingState.currentIndex + 1;

    // Layer 5: Use scoring config for delta
    const delta = calculateScoreDelta(state.scoringConfig, { isCorrect: match.isCorrect });
    console.log('[SCORE] recordDescriptionMatch:', match.labelId, '→', match.zoneId, 'correct:', match.isCorrect, 'delta:', delta, 'score:', state.score, '→', state.score + delta);

    // Get zones with descriptions for completion check
    const zonesWithDescriptions = blueprint.diagram.zones.filter(z => z.description);
    const isComplete = newIndex >= zonesWithDescriptions.length;

    set({
      descriptionMatchingState: {
        ...descriptionMatchingState,
        currentIndex: newIndex,
        matches: newMatches,
      },
      score: Math.max(0, state.score + delta),
    });

    // Check completion — use hasRemainingModes like all other mechanics
    if (isComplete) {
      if (hasRemainingModes(get().multiModeState)) {
        get().checkModeTransition();
      } else {
        set({ isComplete: true });
      }
    }
  },

  // =============================================================================
  // FIX 1.7g: PER-MECHANIC STORE ACTIONS
  // =============================================================================

  updateSequenceOrder: (itemOrder: string[]) => {
    const state = get();
    if (!state.sequencingProgress) return;
    set({
      sequencingProgress: {
        ...state.sequencingProgress,
        currentOrder: itemOrder,
      },
    });
  },

  submitSequence: () => {
    const state = get();
    const { sequencingProgress, blueprint, scoringConfig } = state;
    if (!sequencingProgress || !blueprint?.sequenceConfig) return;
    // Guard double submission
    if (sequencingProgress.isSubmitted) return;

    const sc = blueprint.sequenceConfig as any;
    const correctOrder: string[] = sc.correctOrder ?? sc.correct_order ?? [];
    let correctPositions = 0;
    for (let i = 0; i < sequencingProgress.currentOrder.length; i++) {
      if (sequencingProgress.currentOrder[i] === correctOrder[i]) {
        correctPositions++;
      }
    }

    // Layer 5: Partial credit support via scoring config
    const total = sequencingProgress.totalPositions;
    const scoreDelta = scoringConfig.partialCredit
      ? correctPositions * scoringConfig.basePointsPerItem
      : (correctPositions === total ? total * scoringConfig.basePointsPerItem : 0);

    set({
      sequencingProgress: {
        ...sequencingProgress,
        isSubmitted: true,
        correctPositions,
      },
      score: state.score + scoreDelta,
    });

    if (correctPositions === sequencingProgress.totalPositions) {
      // If no mode transitions, mark scene complete directly
      // Fix 4.1: Use hasRemainingModes() not modeTransitions check
      if (hasRemainingModes(get().multiModeState)) {
        get().checkModeTransition();
      } else {
        set({ isComplete: true });
      }
    }
  },

  updateSortingPlacement: (itemId: string, categoryId: string | null) => {
    const state = get();
    if (!state.sortingProgress) {
      console.warn('[SORT-PLACE] sortingProgress is null! Cannot store placement for', itemId);
      return;
    }
    console.log('[SORT-PLACE]', itemId, '→', categoryId);
    set({
      sortingProgress: {
        ...state.sortingProgress,
        itemCategories: {
          ...state.sortingProgress.itemCategories,
          [itemId]: categoryId,
        },
      },
    });
  },

  submitSorting: () => {
    const state = get();
    const { sortingProgress, blueprint, scoringConfig } = state;
    console.log('[SUBMIT-SORTING] Called. sortingProgress:', sortingProgress, 'hasSortingConfig:', !!blueprint?.sortingConfig);
    if (!sortingProgress || !blueprint?.sortingConfig) return;
    // Guard double submission
    if (sortingProgress.isSubmitted) return;

    let correctCount = 0;
    for (const item of blueprint.sortingConfig.items) {
      // Support both correctCategoryId (string) and correct_category_ids (array)
      const isCorrect = item.correct_category_ids?.length
        ? item.correct_category_ids.includes(sortingProgress.itemCategories[item.id] ?? '')
        : sortingProgress.itemCategories[item.id] === item.correctCategoryId;
      console.log('[SUBMIT-SORTING] Item:', item.id, 'placed:', sortingProgress.itemCategories[item.id], 'correctCatId:', item.correctCategoryId, 'isCorrect:', isCorrect);
      if (isCorrect) {
        correctCount++;
      }
    }

    // Layer 5: Partial credit support
    const total = sortingProgress.totalCount;
    const scoreDelta = scoringConfig.partialCredit
      ? correctCount * scoringConfig.basePointsPerItem
      : (correctCount === total ? total * scoringConfig.basePointsPerItem : 0);

    console.log('[SUBMIT-SORTING] correctCount:', correctCount, 'total:', total, 'scoreDelta:', scoreDelta, 'hasRemainingModes:', hasRemainingModes(get().multiModeState));

    set({
      sortingProgress: {
        ...sortingProgress,
        isSubmitted: true,
        correctCount,
      },
      score: state.score + scoreDelta,
    });

    if (correctCount === sortingProgress.totalCount) {
      // Fix 4.1: Use hasRemainingModes() not modeTransitions check
      if (hasRemainingModes(get().multiModeState)) {
        get().checkModeTransition();
      } else {
        console.log('[SUBMIT-SORTING] Setting isComplete=true');
        set({ isComplete: true });
      }
    }
  },

  recordMemoryMatch: (pairId: string) => {
    const state = get();
    if (!state.memoryMatchProgress) return;

    const newMatched = [...state.memoryMatchProgress.matchedPairIds, pairId];
    // Layer 5: Use scoring config for delta
    const scoreDelta = calculateScoreDelta(state.scoringConfig, { isCorrect: true });

    set({
      memoryMatchProgress: {
        ...state.memoryMatchProgress,
        matchedPairIds: newMatched,
      },
      score: state.score + scoreDelta,
    });

    if (newMatched.length >= state.memoryMatchProgress.totalPairs) {
      // Fix 4.1: Use hasRemainingModes() not modeTransitions check
      if (hasRemainingModes(get().multiModeState)) {
        get().checkModeTransition();
      } else {
        set({ isComplete: true });
      }
    }
  },

  recordMemoryAttempt: () => {
    const state = get();
    if (!state.memoryMatchProgress) return;
    set({
      memoryMatchProgress: {
        ...state.memoryMatchProgress,
        attempts: state.memoryMatchProgress.attempts + 1,
      },
    });
  },

  recordBranchingChoice: (
    nodeId: string,
    optionId: string,
    isCorrect: boolean,
    nextNodeId: string | null,
  ) => {
    const state = get();
    if (!state.branchingProgress) return;

    // Layer 5: Use scoring config for delta
    const scoreDelta = calculateScoreDelta(state.scoringConfig, { isCorrect });
    const newPathTaken = [
      ...state.branchingProgress.pathTaken,
      { nodeId, optionId, isCorrect },
    ];

    set({
      branchingProgress: {
        ...state.branchingProgress,
        currentNodeId: nextNodeId || state.branchingProgress.currentNodeId,
        pathTaken: newPathTaken,
      },
      score: Math.max(0, state.score + scoreDelta),
    });

    // End node reached: nextNodeId is null OR points to an isEndNode
    const reachedEnd = nextNodeId === null || (() => {
      const bp = get().blueprint;
      const nodes = bp?.branchingConfig?.nodes
        || (bp as unknown as Record<string, { nodes?: Array<{ id: string; isEndNode?: boolean }> }>)?.branching_config?.nodes
        || [];
      const targetNode = nextNodeId ? nodes.find((n: { id: string; isEndNode?: boolean }) => n.id === nextNodeId) : null;
      return targetNode?.isEndNode === true;
    })();

    if (reachedEnd) {
      // Fix 4.1: Use hasRemainingModes() not modeTransitions check
      if (hasRemainingModes(get().multiModeState)) {
        get().checkModeTransition();
      } else {
        set({ isComplete: true });
      }
    }
  },

  undoBranchingChoice: () => {
    const state = get();
    const bp = state.branchingProgress;
    if (!bp || bp.pathTaken.length === 0) return;

    const removedStep = bp.pathTaken[bp.pathTaken.length - 1];
    const newPath = bp.pathTaken.slice(0, -1);
    // Layer 5: Reverse the score delta that was applied
    const reverseDelta = removedStep.isCorrect ? -state.scoringConfig.basePointsPerItem : state.scoringConfig.attemptPenalty;

    const previousNodeId = removedStep.nodeId;

    set({
      branchingProgress: {
        ...bp,
        currentNodeId: previousNodeId,
        pathTaken: newPath,
      },
      score: Math.max(0, state.score + reverseDelta),
    });
  },

  updateCompareCategorization: (zoneId: string, category: string) => {
    const state = get();
    if (!state.compareProgress) return;
    set({
      compareProgress: {
        ...state.compareProgress,
        categorizations: {
          ...state.compareProgress.categorizations,
          [zoneId]: category,
        },
      },
    });
  },

  submitCompare: () => {
    const state = get();
    const { compareProgress, blueprint, scoringConfig } = state;
    if (!compareProgress || !blueprint?.compareConfig) return;
    // Guard double submission
    if (compareProgress.isSubmitted) return;

    let correctCount = 0;
    for (const [zoneId, expected] of Object.entries(
      blueprint.compareConfig.expectedCategories,
    )) {
      if (compareProgress.categorizations[zoneId] === expected) {
        correctCount++;
      }
    }

    // Layer 5: Partial credit support
    const total = compareProgress.totalCount;
    const scoreDelta = scoringConfig.partialCredit
      ? correctCount * scoringConfig.basePointsPerItem
      : (correctCount === total ? total * scoringConfig.basePointsPerItem : 0);

    set({
      compareProgress: {
        ...compareProgress,
        isSubmitted: true,
        correctCount,
      },
      score: state.score + scoreDelta,
    });

    if (correctCount === compareProgress.totalCount) {
      // Fix 4.1: Use hasRemainingModes() not modeTransitions check
      if (hasRemainingModes(get().multiModeState)) {
        get().checkModeTransition();
      } else {
        set({ isComplete: true });
      }
    }
  },

  // =============================================================================
  // TEMPORAL INTELLIGENCE ACTIONS
  // =============================================================================

  updateVisibleZones: () => {
    const state = get();
    const { blueprint, temporalConstraints, completedZoneIds } = state;

    if (!blueprint) return;

    const zones = blueprint.diagram.zones || [];
    const visible = new Set<string>();
    const blocked = new Set<string>();

    // Build mutex map for O(1) lookups
    const mutexMap = new Map<string, Set<string>>();
    for (const c of temporalConstraints) {
      if (c.constraint_type === 'mutex') {
        if (!mutexMap.has(c.zone_a)) mutexMap.set(c.zone_a, new Set());
        if (!mutexMap.has(c.zone_b)) mutexMap.set(c.zone_b, new Set());
        mutexMap.get(c.zone_a)!.add(c.zone_b);
        mutexMap.get(c.zone_b)!.add(c.zone_a);
      }
    }

    // Build parent-child map
    const parentToChildren = new Map<string, string[]>();
    for (const zone of zones) {
      if (zone.parentZoneId) {
        if (!parentToChildren.has(zone.parentZoneId)) {
          parentToChildren.set(zone.parentZoneId, []);
        }
        parentToChildren.get(zone.parentZoneId)!.push(zone.id);
      }
    }

    // Helper: Check if zone is blocked by mutex with visible zone
    const isBlockedByMutex = (zoneId: string): boolean => {
      const partners = mutexMap.get(zoneId);
      if (!partners) return false;
      for (const partner of partners) {
        // Zone is blocked if a mutex partner is visible and NOT completed
        if (visible.has(partner) && !completedZoneIds.has(partner)) {
          return true;
        }
      }
      return false;
    };

    // Phase 1: Add root zones (level 1 or no parent)
    for (const zone of zones) {
      if (!zone.parentZoneId && (zone.hierarchyLevel === 1 || !zone.hierarchyLevel)) {
        if (!isBlockedByMutex(zone.id)) {
          visible.add(zone.id);
        } else {
          blocked.add(zone.id);
        }
      }
    }

    // Phase 2: Add children of completed parents
    for (const parentId of completedZoneIds) {
      const children = parentToChildren.get(parentId);
      if (!children) continue;

      for (const childId of children) {
        if (visible.has(childId) || blocked.has(childId)) continue;

        if (!isBlockedByMutex(childId)) {
          visible.add(childId);
        } else {
          blocked.add(childId);
        }
      }
    }

    set({
      visibleZoneIds: visible,
      blockedZoneIds: blocked,
    });
  },

  getVisibleZones: () => {
    return get().visibleZoneIds;
  },

  isZoneVisible: (zoneId: string) => {
    return get().visibleZoneIds.has(zoneId);
  },

  isZoneBlocked: (zoneId: string) => {
    return get().blockedZoneIds.has(zoneId);
  },

  // =============================================================================
  // MULTI-MODE ACTIONS (Agentic Interaction Design)
  // =============================================================================

  initializeMultiMode: (mechanics: InteractionMode[], transitions: ModeTransition[]) => {
    const startingMode = mechanics[0] as InteractionMode;
    const multiModeState: MultiModeState = {
      currentMode: startingMode,
      completedModes: [],
      modeHistory: [{
        mode: startingMode,
        startTime: Date.now(),
        score: 0,
      }],
      pendingTransition: undefined,
      availableModes: mechanics,
    };

    set({
      interactionMode: startingMode,
      multiModeState,
      modeTransitions: transitions,
    });
  },

  checkModeTransition: () => {
    const state = get();
    const { multiModeState, modeTransitions, blueprint } = state;

    if (!multiModeState || modeTransitions.length === 0) return;
    if (!blueprint) return;

    // Evaluate transitions via engine (replaces 120-line switch)
    const progressMap = _buildProgressMap(state);
    const transition = evaluateTransitions(modeTransitions, {
      currentMode: multiModeState.currentMode,
      blueprint,
      progress: progressMap,
      placedLabels: state.placedLabels,
      multiModeState,
      taskLabelCount: _getTaskLabelCount(state),
      hierarchyState: state.hierarchyState,
    });

    if (transition) {
      // Store pending transition for UI to handle (show message, animation, etc.)
      set({
        multiModeState: {
          ...multiModeState,
          pendingTransition: transition,
        },
      });

      // Fix 1.5: Clear any pending transition timer before setting new one
      const prevTimer = get()._transitionTimerId;
      if (prevTimer) clearTimeout(prevTimer);

      // Auto-transition after a brief delay for UI feedback
      const timerId = setTimeout(() => {
        set({ _transitionTimerId: null });
        get().transitionToMode(transition.to, transition);
      }, transition.animation === 'none' ? 0 : 500);
      set({ _transitionTimerId: timerId });
    }
  },

  transitionToMode: (newMode: InteractionMode, transition?: ModeTransition) => {
    const state = get();
    const { multiModeState, blueprint, score } = state;

    if (!multiModeState) return;

    // Fix 1.6: Don't mutate modeHistory in-place — create new array
    const updatedHistory = [...multiModeState.modeHistory];
    const lastIdx = updatedHistory.length - 1;
    if (lastIdx >= 0) {
      updatedHistory[lastIdx] = {
        ...updatedHistory[lastIdx],
        endTime: Date.now(),
        score,
      };
    }

    // Layer 5: Initialize per-mechanic progress via registry (replaces ~80 lines of if/else)
    const mechanicState = blueprint
      ? initializeMechanicProgress(newMode, blueprint)
      : initializeMechanicProgress(newMode, { labels: [], diagram: { assetPrompt: '', zones: [] }, tasks: [], animationCues: { correctPlacement: '', incorrectPlacement: '' }, templateType: 'INTERACTIVE_DIAGRAM', title: '', narrativeIntro: '' });

    // Layer 5: Read scoring config for new mode
    const newScoringConfig = blueprint ? getScoringConfig(newMode, blueprint) : state.scoringConfig;

    // SB-FIX-2 + Layer5-Fix-1: ACCUMULATE maxScore across mode transitions
    const modeMaxScore = blueprint
      ? getMaxScore(newMode, blueprint, newScoringConfig.basePointsPerItem)
      : 0;
    const newMaxScore = state.maxScore + modeMaxScore;
    console.log('[SCORE] transitionToMode:', newMode, 'score preserved:', get().score, 'maxScore:', state.maxScore, '+', modeMaxScore, '=', newMaxScore);

    // Update state with new mode
    // Fix 5.3: Preserve cumulative score across mode transitions (was resetting to 0)
    // Layer5-Fix-3: Preserve completedZoneIds across mode transitions (game-level state)
    set({
      isComplete: false,
      interactionMode: newMode,
      score: get().score,                // Fix 5.3: preserve cumulative score
      maxScore: newMaxScore,             // SB-FIX-2 + Layer5-Fix-1
      scoringConfig: newScoringConfig,   // Layer 5: Update scoring config for new mode
      // Layer 5: Per-mechanic progress from registry-driven initializer
      ...mechanicState,
      // completedZoneIds NOT cleared — it's game-level state needed by temporal constraints
      multiModeState: {
        ...multiModeState,
        currentMode: newMode,
        completedModes: [...multiModeState.completedModes, multiModeState.currentMode],
        modeHistory: [
          ...updatedHistory,
          {
            mode: newMode,
            startTime: Date.now(),
            score: 0,
          },
        ],
        pendingTransition: undefined,
      },
    });

    // SB-FIX-3 (partial): Recalculate visible zones for new mode
    get().updateVisibleZones();
  },

  getAvailableModes: () => {
    const { multiModeState } = get();
    if (!multiModeState) return [];
    return multiModeState.availableModes;
  },

  canSwitchToMode: (mode: InteractionMode) => {
    const state = get();
    const { multiModeState, modeTransitions } = state;

    if (!multiModeState) return false;

    // Check if mode is in available modes
    if (!multiModeState.availableModes.includes(mode)) return false;

    // Check if there's a user_choice transition allowing this switch
    const hasUserChoiceTransition = modeTransitions.some(
      t => t.from === multiModeState.currentMode && t.to === mode && t.trigger === 'user_choice'
    );

    // Also allow if mode is in the flat mechanics list (all mechanics are peers)
    return hasUserChoiceTransition || multiModeState.availableModes.includes(mode);
  },

  // =============================================================================
  // SCENE LIFECYCLE ACTIONS
  // =============================================================================

  completeCurrentScene: () => {
    const state = get();
    const { gameSequence, multiSceneState, score, maxScore, placedLabels } = state;
    if (!gameSequence || !multiSceneState) return;

    const currentScene = gameSequence.scenes[multiSceneState.currentSceneIndex];
    if (!currentScene) return;

    console.log('[COMPLETE-SCENE] completeCurrentScene:', {
      sceneId: currentScene.scene_id,
      currentSceneIndex: multiSceneState.currentSceneIndex,
      score,
      maxScore,
    });

    // Accumulate scores across all tasks in this scene (not just the current task's score)
    const taskScoreSum = multiSceneState.taskResults.reduce((sum, tr) => sum + tr.score, 0);
    const taskMaxScoreSum = multiSceneState.taskResults.reduce((sum, tr) => sum + tr.max_score, 0);
    const accumulatedScore = taskScoreSum + score;
    const accumulatedMaxScore = taskMaxScoreSum + maxScore;

    get().completeScene({
      scene_id: currentScene.scene_id,
      score: accumulatedScore,
      max_score: currentScene.max_score || accumulatedMaxScore,
      completed: true,
      matches: placedLabels.map(p => ({ labelId: p.labelId, zoneId: p.zoneId, isCorrect: p.isCorrect })),
    });

    console.log('[COMPLETE-SCENE] After completeScene:', {
      isComplete: get().isComplete,
      isSequenceComplete: get().multiSceneState?.isSequenceComplete,
      completedSceneIds: get().multiSceneState?.completedSceneIds,
    });
  },

  advanceToNextScene: () => {
    const state = get();
    const { gameSequence, multiSceneState } = state;
    if (!gameSequence || !multiSceneState) return;
    if (multiSceneState.isSequenceComplete) {
      console.log('[ADV-NEXT-SCENE] Skipping — sequence already complete');
      return;
    }

    // Layer 5: Use scene flow graph for non-linear progression
    const currentScene = gameSequence.scenes[multiSceneState.currentSceneIndex];
    if (!currentScene) return;

    // Check if gameSequence has a scene_flow graph (future backend support)
    const sceneFlow = (gameSequence as GameSequence & { scene_flow?: SceneFlowGraph }).scene_flow;
    const nextSceneId = getNextSceneId(
      currentScene.scene_id,
      sceneFlow,
      gameSequence,
      multiSceneState.sceneResults,
    );

    console.log('[ADV-NEXT-SCENE] advanceToNextScene:', {
      currentSceneId: currentScene.scene_id,
      currentSceneIndex: multiSceneState.currentSceneIndex,
      nextSceneId,
      nextIdx: nextSceneId ? gameSequence.scenes.findIndex(s => s.scene_id === nextSceneId) : -1,
    });

    if (nextSceneId) {
      const nextIdx = gameSequence.scenes.findIndex(s => s.scene_id === nextSceneId);
      if (nextIdx >= 0) {
        get().advanceToScene(nextIdx);
      }
    }
    // null = game complete (handled by completeCurrentScene)
  },

  // =============================================================================
  // TASK LIFECYCLE ACTIONS (tasks within a scene)
  // =============================================================================

  advanceToNextTask: () => {
    const { gameSequence, multiSceneState, score, placedLabels } = get();
    if (!gameSequence || !multiSceneState) return;

    const scene = gameSequence.scenes[multiSceneState.currentSceneIndex];
    const tasks = scene?.tasks || [];
    const currentTaskIdx = multiSceneState.currentTaskIndex;
    const currentTask = tasks[currentTaskIdx];
    const nextIdx = currentTaskIdx + 1;

    // Fix 1.8: Use store maxScore instead of recalculating (which always gave 100%)
    const taskResult: TaskResult = {
      task_id: currentTask?.task_id || `task_${currentTaskIdx}`,
      score,
      max_score: get().maxScore,
      completed: true,
      matches: placedLabels.map(p => ({ ...p })),
    };

    const newTaskResults = [...multiSceneState.taskResults, taskResult];

    if (nextIdx < tasks.length) {
      // More tasks in this scene — advance to next task (same image)
      // SB-FIX-3: Clear visibleZoneIds before reinit (initializeGame will recalculate)
      // SB-FIX-7: maxScore will be recalculated by initializeGame from new task's blueprint
      set({
        multiSceneState: {
          ...multiSceneState,
          currentTaskIndex: nextIdx,
          taskResults: newTaskResults,
        },
        visibleZoneIds: new Set(),  // SB-FIX-3: Clear leftover zones
        completedZoneIds: new Set(), // SB-FIX-3: Clear leftover completed zones
      });
      // SB-FIX-4: sceneToBlueprint filters temporal constraints to task zones
      const bp = sceneToBlueprint(scene, multiSceneState.currentSceneIndex, nextIdx);
      get().initializeGame(bp);
    } else {
      // All tasks done in this scene — complete and advance to next scene
      set({
        multiSceneState: {
          ...multiSceneState,
          taskResults: newTaskResults,
        },
      });
      get().completeCurrentScene();
      get().advanceToNextScene();
    }
  },

  getCurrentTask: () => {
    const { gameSequence, multiSceneState } = get();
    if (!gameSequence || !multiSceneState) return null;

    const scene = gameSequence.scenes[multiSceneState.currentSceneIndex];
    const tasks = scene?.tasks || [];
    return tasks[multiSceneState.currentTaskIndex] || null;
  },
}));
