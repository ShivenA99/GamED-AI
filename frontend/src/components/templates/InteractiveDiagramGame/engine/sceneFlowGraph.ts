/**
 * sceneFlowGraph.ts — Non-linear scene progression support.
 * Evaluates scene flow graphs with conditional edges.
 * Falls back to linear progression when no flow graph is present.
 * No React, no Zustand.
 */

import type { GameSequence, SceneResult } from '../types';

export interface SceneFlowEdge {
  from_scene: string;
  to_scene: string;
  condition?: {
    type: 'score_threshold' | 'completion' | 'always';
    value?: number; // e.g., 80 for "score >= 80%"
  };
  animation?: string;
}

export interface SceneFlowGraph {
  edges: SceneFlowEdge[];
}

/**
 * Determine the next scene ID given the current scene, flow graph, and results.
 * Returns null if game is complete (no valid transitions).
 */
export function getNextSceneId(
  currentSceneId: string,
  flow: SceneFlowGraph | undefined,
  gameSequence: GameSequence,
  sceneResults: SceneResult[],
): string | null {
  // If no flow graph, fall back to linear progression
  if (!flow || flow.edges.length === 0) {
    const currentIdx = gameSequence.scenes.findIndex(
      s => s.scene_id === currentSceneId,
    );
    const nextIdx = currentIdx + 1;
    return nextIdx < gameSequence.scenes.length
      ? gameSequence.scenes[nextIdx].scene_id
      : null;
  }

  // Evaluate flow edges for the current scene
  const outEdges = flow.edges.filter(e => e.from_scene === currentSceneId);
  for (const edge of outEdges) {
    if (evaluateFlowCondition(edge.condition, currentSceneId, sceneResults)) {
      return edge.to_scene;
    }
  }

  return null; // no valid transition = game complete
}

function evaluateFlowCondition(
  condition: SceneFlowEdge['condition'],
  sceneId: string,
  results: SceneResult[],
): boolean {
  if (!condition || condition.type === 'always') return true;

  const result = results.find(r => r.scene_id === sceneId);
  if (!result) return false;

  switch (condition.type) {
    case 'completion':
      return result.completed;
    case 'score_threshold':
      return result.max_score > 0
        ? (result.score / result.max_score * 100) >= (condition.value ?? 0)
        : false;
    default:
      return true;
  }
}
