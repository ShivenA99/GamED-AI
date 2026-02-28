'use client'

import React, { useState, useCallback, useMemo, useEffect } from 'react'
import { GameScene, GameSequence, SceneProgressionType } from '../types'
import { useInteractiveDiagramState } from '../hooks/useInteractiveDiagramState'

interface GameSequenceRendererProps {
  sequence: GameSequence
  renderScene: (scene: GameScene) => React.ReactNode
  onSequenceComplete: (totalResults: SequenceResult) => void
  transitionDelayMs?: number
}

interface SceneResult {
  scene_id: string
  score: number
  max_score: number
  completed: boolean
  matches: Array<{ labelId: string; zoneId: string; isCorrect: boolean }>
}

interface SequenceResult {
  sequence_id: string
  total_score: number
  total_max_score: number
  scenes_completed: number
  total_scenes: number
  scene_results: SceneResult[]
}

/**
 * Get the next scene based on progression type
 *
 * - linear: Simply go to scene_number + 1
 * - zoom_in: Find child scenes of current (more detailed views)
 * - depth_first: Complete all children before siblings
 * - branching: User selects from available branches
 */
function getNextScene(
  currentScene: GameScene,
  completedSceneIds: Set<string>,
  allScenes: GameScene[],
  progressionType: SceneProgressionType
): GameScene | null {
  switch (progressionType) {
    case 'linear':
      // Next scene by scene_number
      return allScenes.find(s => s.scene_number === currentScene.scene_number + 1) || null

    case 'zoom_in':
      // Find child scenes (more detailed view of current area)
      const childScenes = allScenes.filter(
        s => s.prerequisite_scene === currentScene.scene_id &&
             !completedSceneIds.has(s.scene_id)
      )
      if (childScenes.length > 0) {
        return childScenes[0]
      }
      // If no children, find next sibling or parent's sibling
      return findNextAvailable(currentScene, completedSceneIds, allScenes)

    case 'depth_first':
      // Complete all children first, then move to siblings
      const children = allScenes.filter(s => s.prerequisite_scene === currentScene.scene_id)
      const uncompletedChild = children.find(c => !completedSceneIds.has(c.scene_id))
      if (uncompletedChild) {
        return uncompletedChild
      }
      // Find next sibling or go up the tree
      return findNextSibling(currentScene, completedSceneIds, allScenes)

    case 'branching':
      // Return null - user will select from available branches
      return null

    default:
      return allScenes.find(s => s.scene_number === currentScene.scene_number + 1) || null
  }
}

/**
 * Find next sibling scene at the same level
 */
function findNextSibling(
  currentScene: GameScene,
  completedSceneIds: Set<string>,
  allScenes: GameScene[]
): GameScene | null {
  // Find siblings (same prerequisite)
  const siblings = allScenes.filter(
    s => s.prerequisite_scene === currentScene.prerequisite_scene &&
         s.scene_id !== currentScene.scene_id &&
         !completedSceneIds.has(s.scene_id)
  )
  if (siblings.length > 0) {
    // Return the one with lowest scene_number
    return siblings.sort((a, b) => a.scene_number - b.scene_number)[0]
  }

  // No siblings available, go up to parent's level
  if (currentScene.prerequisite_scene) {
    const parent = allScenes.find(s => s.scene_id === currentScene.prerequisite_scene)
    if (parent) {
      return findNextSibling(parent, completedSceneIds, allScenes)
    }
  }

  return null
}

/**
 * Find next available scene (any uncompleted)
 */
function findNextAvailable(
  currentScene: GameScene,
  completedSceneIds: Set<string>,
  allScenes: GameScene[]
): GameScene | null {
  // First try siblings
  const sibling = findNextSibling(currentScene, completedSceneIds, allScenes)
  if (sibling) return sibling

  // Otherwise any uncompleted scene that's unlocked
  return allScenes.find(s => {
    if (completedSceneIds.has(s.scene_id)) return false
    if (!s.prerequisite_scene) return true
    return completedSceneIds.has(s.prerequisite_scene)
  }) || null
}

/**
 * Get available branches for branching progression
 */
function getAvailableBranches(
  completedSceneIds: Set<string>,
  allScenes: GameScene[]
): GameScene[] {
  return allScenes.filter(scene => {
    // Skip completed scenes
    if (completedSceneIds.has(scene.scene_id)) return false
    // No prerequisite = available
    if (!scene.prerequisite_scene) return true
    // Prerequisite completed = available
    return completedSceneIds.has(scene.prerequisite_scene)
  })
}

/**
 * GameSequenceRenderer Component (Preset 2)
 *
 * Handles multi-scene game progression with:
 * - Scene transitions and animations
 * - Progress tracking across scenes
 * - Unlock conditions (linear, zoom-in, branching)
 * - Score aggregation
 */
export const GameSequenceRenderer: React.FC<GameSequenceRendererProps> = ({
  sequence,
  renderScene,
  onSequenceComplete,
  transitionDelayMs = 1000,
}) => {
  const {
    multiSceneState,
  } = useInteractiveDiagramState()

  const currentSceneIndex = multiSceneState?.currentSceneIndex ?? 0
  const completedSceneIds = multiSceneState?.completedSceneIds ?? []
  const completedScenes = new Set(completedSceneIds)

  const [isTransitioning, setIsTransitioning] = useState(false)
  const [showBranchSelector, setShowBranchSelector] = useState(false)

  const currentScene = sequence.scenes[currentSceneIndex]

  // Get available branches for branching progression
  const availableBranches = useMemo(() => {
    if (sequence.progression_type !== 'branching') return []
    return getAvailableBranches(completedScenes, sequence.scenes)
  }, [sequence.progression_type, completedScenes, sequence.scenes])

  // Check if a scene is unlocked based on prerequisites
  const isSceneUnlocked = useCallback((scene: GameScene) => {
    if (!scene.prerequisite_scene) return true
    return completedScenes.has(scene.prerequisite_scene)
  }, [completedScenes])

  // Scene completion is handled by the useEffect in index.tsx (getSceneAction).
  // That handler properly distinguishes advance_task vs advance_scene and avoids
  // the race condition this duplicate handler caused (bypassing the task system).

  // Navigation for non-linear progressions
  const handleSceneSelect = useCallback((sceneIndex: number) => {
    const scene = sequence.scenes[sceneIndex]
    if (isSceneUnlocked(scene)) {
      useInteractiveDiagramState.getState().advanceToScene(sceneIndex)
    }
  }, [sequence.scenes, isSceneUnlocked])

  return (
    <div className="game-sequence-renderer">
      {/* Scene progress + score are rendered by the parent (SceneIndicator + GameControls) */}

      {/* Scene selector for non-linear progressions (branching/depth-first/zoom_in) */}
      {(sequence.progression_type === 'branching' ||
        sequence.progression_type === 'depth_first' ||
        sequence.progression_type === 'zoom_in') && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">
              {sequence.progression_type === 'zoom_in' && 'Zoom Level: '}
              {sequence.progression_type === 'depth_first' && 'Exploration Path: '}
              {sequence.progression_type === 'branching' && 'Available Paths: '}
            </span>
            {sequence.allow_scene_skip && (
              <span className="text-xs text-blue-600">Click to navigate</span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {(sequence.scenes || []).map((scene, idx) => {
              const isUnlocked = isSceneUnlocked(scene)
              const isCompleted = completedScenes.has(scene.scene_id)
              const isCurrent = idx === currentSceneIndex
              // For zoom_in, show hierarchy level
              const hierarchyDepth = scene.prerequisite_scene
                ? sequence.scenes.filter(s => {
                    let current = scene
                    let depth = 0
                    while (current.prerequisite_scene) {
                      depth++
                      current = sequence.scenes.find(s => s.scene_id === current.prerequisite_scene) || current
                      if (!current.prerequisite_scene) break
                    }
                    return depth
                  }).length + 1
                : 1

              const zoomMarginLeft = sequence.progression_type === 'zoom_in'
                ? Math.min(hierarchyDepth * 2, 8) * 4  // 4px per unit, max 32px
                : 0

              return (
                <button
                  key={scene.scene_id}
                  onClick={() => {
                    if (isUnlocked) {
                      handleSceneSelect(idx)
                      setShowBranchSelector(false)
                    }
                  }}
                  disabled={!isUnlocked && !sequence.allow_scene_skip}
                  style={zoomMarginLeft ? { marginLeft: `${zoomMarginLeft}px` } : undefined}
                  className={`
                    px-3 py-2 rounded-lg text-sm font-medium transition-all
                    ${isCurrent
                      ? 'bg-blue-500 text-white ring-2 ring-blue-300'
                      : isCompleted
                        ? 'bg-green-100 text-green-800 border border-green-300'
                        : isUnlocked
                          ? 'bg-gray-100 text-gray-700 hover:bg-gray-200 hover:border-blue-300'
                          : 'bg-gray-50 text-gray-400 cursor-not-allowed opacity-60'
                    }
                  `}
                >
                  <div className="flex items-center gap-1">
                    {isCompleted && (
                      <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                    {!isUnlocked && (
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                    )}
                    {sequence.progression_type === 'zoom_in' && (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                      </svg>
                    )}
                    <span>{scene.title}</span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Branch selector modal for branching progression */}
      {showBranchSelector && availableBranches.length > 0 && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-bold text-gray-800 mb-2">Choose Your Path</h3>
            <p className="text-sm text-gray-600 mb-4">Select the next area to explore:</p>
            <div className="space-y-2">
              {availableBranches.map((scene) => {
                const idx = sequence.scenes.findIndex(s => s.scene_id === scene.scene_id)
                return (
                  <button
                    key={scene.scene_id}
                    onClick={() => {
                      handleSceneSelect(idx)
                      setShowBranchSelector(false)
                    }}
                    className="w-full p-4 text-left bg-gray-50 hover:bg-blue-50 border-2 border-gray-200 hover:border-blue-400 rounded-lg transition-all"
                  >
                    <div className="font-medium text-gray-800">{scene.title}</div>
                    <div className="text-sm text-gray-500 mt-1">{scene.narrative_intro}</div>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Transition overlay */}
      {isTransitioning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-8 text-center animate-pulse">
            <h3 className="text-xl font-bold text-gray-800 mb-2">
              Great job!
            </h3>
            <p className="text-gray-600">
              Moving to {sequence.progression_type === 'zoom_in' ? 'closer view' : 'next scene'}...
            </p>
          </div>
        </div>
      )}

      {/* Current scene */}
      {currentScene && !isTransitioning && (
        <div className="scene-container">
          {/* Scene intro */}
          <div className="mb-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-600">
                Scene {currentScene.scene_number} of {sequence.total_scenes}
              </span>
              <span className="text-sm text-gray-500">
                {(currentScene.mechanics?.[0]?.type || currentScene.interaction_mode || 'unknown').replace('_', ' ')}
              </span>
            </div>
            <h2 className="text-xl font-bold text-gray-800 mb-1">
              {currentScene.title}
            </h2>
            <p className="text-gray-600">
              {currentScene.narrative_intro}
            </p>
          </div>

          {/* Scene content - rendered by parent */}
          {renderScene(currentScene)}
        </div>
      )}

      {/* Summary after all scenes */}
      {/* Sequence completion is handled by the parent ResultsPanel */}
    </div>
  )
}

export default GameSequenceRenderer
