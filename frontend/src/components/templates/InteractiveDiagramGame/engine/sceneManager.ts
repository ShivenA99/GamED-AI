/**
 * sceneManager.ts — Pure scene/task lifecycle functions.
 * No React, no Zustand.
 */

import type {
  InteractiveDiagramBlueprint,
  InteractionMode,
  GameScene,
  GameSequence,
  MultiSceneState,
  TemporalConstraint,
} from '../types';

// ─── Scene Action Discriminated Union ────────────────────────────────

export type SceneAction =
  | { type: 'advance_task' }
  | { type: 'advance_scene' }
  | { type: 'complete_game' }
  | { type: 'wait' };

/**
 * Determine next action when a mechanic/task completes.
 */
export function getSceneAction(
  multiSceneState: MultiSceneState | null,
  gameSequence: GameSequence | null,
): SceneAction {
  if (!multiSceneState || !gameSequence) {
    return { type: 'complete_game' };
  }

  if (multiSceneState.isSequenceComplete) {
    return { type: 'complete_game' };
  }

  const currentScene = gameSequence.scenes[multiSceneState.currentSceneIndex];
  const tasks = currentScene?.tasks ?? [];
  const nextTaskIdx = multiSceneState.currentTaskIndex + 1;

  // More tasks in this scene
  if (tasks.length > 1 && nextTaskIdx < tasks.length) {
    return { type: 'advance_task' };
  }

  // More scenes
  const nextSceneIdx = multiSceneState.currentSceneIndex + 1;
  if (nextSceneIdx < gameSequence.scenes.length) {
    return { type: 'advance_scene' };
  }

  return { type: 'complete_game' };
}

/**
 * Convert a GameScene to InteractiveDiagramBlueprint.
 * Single source of truth for scene→blueprint conversion.
 *
 * When taskIndex is provided and the scene has tasks, only the zones/labels
 * matching that task are activated. The image stays the same.
 */
export function sceneToBlueprint(
  scene: GameScene,
  sceneIndex: number,
  taskIndex: number = 0,
): InteractiveDiagramBlueprint {
  // Create implicit task if none exist
  const task = (scene.tasks && scene.tasks.length > 0) ? scene.tasks[taskIndex] : {
    task_id: `task_${sceneIndex + 1}_implicit`,
    title: scene.title,
    mechanic_type: (scene.mechanics?.[0]?.type || scene.interaction_mode) as InteractionMode,
    zone_ids: scene.zones.map(z => z.id),
    label_ids: scene.labels.map(l => l.id),
    scoring_weight: 1,
  };

  // Filter zones/labels to task subset when task specifies them
  let activeZones = scene.zones;
  let activeLabels = scene.labels;

  if (task && task.zone_ids.length > 0) {
    activeZones = scene.zones.filter(z => task.zone_ids.includes(z.id));
  }
  if (task && task.label_ids.length > 0) {
    activeLabels = scene.labels.filter(l => task.label_ids.includes(l.id));
  }

  // Derive starting mode
  const startingMode = (task?.mechanic_type
    || scene.mechanics?.[0]?.type
    || scene.interaction_mode) as InteractionMode;

  // Temporal constraint filtering
  const allConstraints = scene.temporalConstraints || scene.temporal_constraints;
  const filteredConstraints = (() => {
    if (!allConstraints) return undefined;
    if (!task || task.zone_ids.length === 0) return allConstraints;
    const taskZoneSet = new Set(task.zone_ids);
    return allConstraints.filter(
      (c: TemporalConstraint) => taskZoneSet.has(c.zone_a) && taskZoneSet.has(c.zone_b),
    );
  })();

  return {
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
    tasks: [{
      id: task?.task_id || `task_${sceneIndex + 1}`,
      type: 'label_diagram',
      questionText: task?.instructions || scene.narrative_intro,
      requiredToProceed: true,
    }],
    animationCues: {
      correctPlacement: 'Great!',
      incorrectPlacement: 'Try again!',
    },
    mechanics: scene.mechanics || [{ type: startingMode }],
    interactionMode: startingMode,
    modeTransitions: scene.mode_transitions,
    zoneGroups: scene.zoneGroups,
    paths: scene.paths,
    sequenceConfig: scene.sequenceConfig || scene.sequence_config,
    sortingConfig: scene.sortingConfig || scene.sorting_config,
    memoryMatchConfig: scene.memoryMatchConfig || scene.memory_match_config,
    branchingConfig: scene.branchingConfig || scene.branching_config,
    descriptionMatchingConfig: scene.descriptionMatchingConfig || scene.description_matching_config,
    compareConfig: scene.compareConfig || scene.compare_config,
    identificationPrompts: scene.identificationPrompts || scene.identification_prompts,
    clickToIdentifyConfig: scene.clickToIdentifyConfig || scene.click_to_identify_config,
    tracePathConfig: scene.tracePathConfig || scene.trace_path_config,
    dragDropConfig: scene.dragDropConfig || scene.drag_drop_config,
    temporalConstraints: filteredConstraints,
    motionPaths: scene.motionPaths || scene.motion_paths,
    hints: scene.hints,
    scoringStrategy: scene.scoringStrategy || scene.scoring_strategy,
  };
}
