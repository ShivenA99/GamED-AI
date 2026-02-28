'use client'

import React from 'react'

interface SceneProgressBarProps {
  currentScene: number
  totalScenes: number
  completedScenes: number
  progressPercent: number
  currentScore: number
  maxScore: number
  progressionType: 'linear' | 'zoom_in' | 'depth_first' | 'branching'
}

/**
 * SceneProgressBar Component (Preset 2)
 *
 * Shows progress through a multi-scene game:
 * - Current scene indicator
 * - Overall progress bar
 * - Score display
 * - Progression type indicator (zoom icon, tree icon, etc.)
 */
export const SceneProgressBar: React.FC<SceneProgressBarProps> = ({
  currentScene,
  totalScenes,
  completedScenes,
  progressPercent,
  currentScore,
  maxScore,
  progressionType,
}) => {
  // Get icon for progression type
  const getProgressionIcon = () => {
    switch (progressionType) {
      case 'zoom_in':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
          </svg>
        )
      case 'depth_first':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M19 9l-7 7-7-7" />
          </svg>
        )
      case 'branching':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
          </svg>
        )
      default: // linear
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        )
    }
  }

  // Get progression type label
  const getProgressionLabel = () => {
    switch (progressionType) {
      case 'zoom_in': return 'Zoom In'
      case 'depth_first': return 'Explore Deep'
      case 'branching': return 'Choose Path'
      default: return 'Linear'
    }
  }

  return (
    <div className="scene-progress-bar mb-6 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
      {/* Top row: Scene counter and progression type */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-600">
            Scene {currentScene} of {totalScenes}
          </span>
          {completedScenes > 0 && (
            <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">
              {completedScenes} complete
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 text-gray-500">
          {getProgressionIcon()}
          <span className="text-xs font-medium">{getProgressionLabel()}</span>
        </div>
      </div>

      {/* Progress bar with scene markers */}
      <div className="relative">
        {/* Background bar */}
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          {/* Progress fill */}
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Scene markers */}
        <div className="absolute top-0 left-0 right-0 h-2 flex items-center justify-between px-0">
          {Array.from({ length: totalScenes }).map((_, idx) => {
            const position = ((idx + 1) / totalScenes) * 100
            const isCompleted = idx < completedScenes
            const isCurrent = idx + 1 === currentScene

            return (
              <div
                key={idx}
                className={`
                  absolute w-3 h-3 rounded-full border-2 transform -translate-x-1/2 -translate-y-0.5
                  transition-all duration-300
                  ${isCompleted
                    ? 'bg-green-500 border-green-600'
                    : isCurrent
                      ? 'bg-blue-500 border-blue-600 scale-125'
                      : 'bg-white border-gray-300'
                  }
                `}
                style={{ left: `${position}%` }}
              />
            )
          })}
        </div>
      </div>

      {/* Bottom row: Score */}
      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
          <span className="text-sm font-semibold text-gray-700">
            {currentScore} / {maxScore} points
          </span>
        </div>

        <div className="text-xs text-gray-500">
          {Math.round((currentScore / maxScore) * 100)}% complete
        </div>
      </div>
    </div>
  )
}

export default SceneProgressBar
