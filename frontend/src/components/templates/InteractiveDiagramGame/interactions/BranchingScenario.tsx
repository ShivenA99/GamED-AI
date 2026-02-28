'use client'

import React, { useState, useCallback } from 'react'
import type { MechanicAction, ActionResult } from '../types'

/**
 * BranchingScenario - Decision tree navigation interaction component
 *
 * Users navigate through decision points with consequences.
 * Good for diagnostic reasoning, troubleshooting, and ethical dilemmas.
 */

export interface DecisionNode {
  id: string
  question: string
  description?: string
  imageUrl?: string
  options: DecisionOption[]
  isEndNode?: boolean
  endMessage?: string
}

export interface DecisionOption {
  id: string
  text: string
  nextNodeId: string | null // null for end nodes
  isCorrect?: boolean
  consequence?: string
  points?: number
}

export interface BranchingScenarioProps {
  nodes: DecisionNode[]
  startNodeId: string
  showPathTaken?: boolean
  allowBacktrack?: boolean
  showConsequences?: boolean
  multipleValidEndings?: boolean
  instructions?: string
  pointsPerDecision?: number
  timingConfig?: {
    consequenceDisplayMs?: number
    quickTransitionMs?: number
  }
  // Store integration props (Fix 1.7h) — optional for standalone use
  storeProgress?: { currentNodeId: string; pathTaken: Array<{ nodeId: string; optionId: string; isCorrect: boolean }> } | null
  /** V4 unified action dispatch */
  onAction?: (action: MechanicAction) => ActionResult | null
}

interface PathStep {
  nodeId: string
  optionId: string
  isCorrect: boolean
  consequence?: string
}

export function BranchingScenario({
  nodes,
  startNodeId,
  showPathTaken = true,
  allowBacktrack = true,
  showConsequences = true,
  multipleValidEndings = false,
  instructions = 'Navigate through the scenario by making decisions.',
  pointsPerDecision = 10,
  timingConfig,
  storeProgress,
  onAction,
}: BranchingScenarioProps) {
  // Layer 3: Initialize from storeProgress for restoration
  const [currentNodeId, setCurrentNodeId] = useState(
    storeProgress?.currentNodeId ?? startNodeId
  )
  const [pathTaken, setPathTaken] = useState<PathStep[]>(() =>
    (storeProgress?.pathTaken ?? []).map(p => ({
      nodeId: p.nodeId,
      optionId: p.optionId,
      isCorrect: p.isCorrect,
      consequence: undefined,
    }))
  )
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const [isComplete, setIsComplete] = useState(false)

  const currentNode = nodes.find((n) => n.id === currentNodeId)

  const handleOptionSelect = useCallback((optionId: string) => {
    if (isComplete) return
    setSelectedOption(optionId)
  }, [isComplete])

  const handleConfirm = useCallback(() => {
    if (!selectedOption || !currentNode) return

    const option = currentNode.options.find((o) => o.id === selectedOption)
    if (!option) return

    // Show feedback
    setShowFeedback(true)

    // Add to path
    const step: PathStep = {
      nodeId: currentNodeId,
      optionId: selectedOption,
      isCorrect: option.isCorrect ?? true,
      consequence: option.consequence,
    }

    setPathTaken((prev) => [...prev, step])
    onAction?.({ type: 'branching_choice', mechanic: 'branching_scenario', nodeId: currentNodeId, optionId: selectedOption, isCorrect: option.isCorrect ?? true, nextNodeId: option.nextNodeId })

    // After feedback delay, move to next node or complete
    setTimeout(() => {
      setShowFeedback(false)
      setSelectedOption(null)

      // Check if we've reached an end: nextNodeId is null, current is end, target is end, or target doesn't exist
      const targetNode = option.nextNodeId ? nodes.find(n => n.id === option.nextNodeId) : null;
      const reachedEnd = option.nextNodeId === null || currentNode.isEndNode || targetNode?.isEndNode || (option.nextNodeId !== null && !targetNode);

      if (reachedEnd) {
        // Navigate to end node so its message renders
        if (targetNode?.isEndNode) {
          setCurrentNodeId(option.nextNodeId!)
        }
        setIsComplete(true)
        // Store detects completion via branching_choice action (nextNodeId=null triggers it)
      } else {
        setCurrentNodeId(option.nextNodeId!)
      }
    }, showConsequences && option.consequence ? (timingConfig?.consequenceDisplayMs ?? 2000) : (timingConfig?.quickTransitionMs ?? 500))
  }, [selectedOption, currentNode, currentNodeId, pathTaken, showConsequences, onAction])

  const handleBacktrack = useCallback(() => {
    if (!allowBacktrack || pathTaken.length === 0) return
    onAction?.({ type: 'branching_undo', mechanic: 'branching_scenario' })

    const newPath = pathTaken.slice(0, -1)
    setPathTaken(newPath)

    if (newPath.length === 0) {
      setCurrentNodeId(startNodeId)
    } else {
      // Find what node that step led to
      const lastStep = pathTaken[pathTaken.length - 1]
      setCurrentNodeId(lastStep.nodeId)
    }

    setSelectedOption(null)
    setShowFeedback(false)
  }, [allowBacktrack, pathTaken, startNodeId])

  const handleReset = useCallback(() => {
    setCurrentNodeId(startNodeId)
    setPathTaken([])
    setSelectedOption(null)
    setShowFeedback(false)
    setIsComplete(false)
  }, [startNodeId])

  if (!currentNode) {
    // Missing node — show last consequence and treat as scenario end
    const lastStep = pathTaken[pathTaken.length - 1]
    return (
      <div className="w-full max-w-3xl mx-auto p-4">
        <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl">
          <p className="font-semibold text-amber-800 mb-2">Scenario Ended</p>
          {lastStep?.consequence && (
            <p className="text-sm text-amber-700 mb-2">{lastStep.consequence}</p>
          )}
          <p className="text-sm text-gray-600">This path has concluded. Your choices led to a different outcome.</p>
        </div>
      </div>
    )
  }

  const selectedOptionData = currentNode.options.find((o) => o.id === selectedOption)

  return (
    <div className="w-full max-w-3xl mx-auto p-4">
      {/* Instructions */}
      {pathTaken.length === 0 && (
        <div className="mb-4 p-3 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">{instructions}</p>
        </div>
      )}

      {/* Path progress */}
      {showPathTaken && pathTaken.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-gray-500 mb-2">
            Decision Path ({pathTaken.length} step{pathTaken.length !== 1 ? 's' : ''})
          </p>
          <div className="flex flex-wrap gap-2">
            {pathTaken.map((step, idx) => (
              <span
                key={idx}
                className={`
                  text-xs px-2 py-1 rounded-full
                  ${step.isCorrect
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                  }
                `}
              >
                Step {idx + 1}: {step.isCorrect ? '✓' : '✗'}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Current scenario */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        {/* Header */}
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <p className="text-xs text-gray-500">
            Decision Point {pathTaken.length + 1}
          </p>
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Image if present */}
          {currentNode.imageUrl && (
            <img
              src={currentNode.imageUrl}
              alt="Scenario"
              className="w-full h-48 object-cover rounded-lg mb-4"
            />
          )}

          {/* Question */}
          <h2 className="text-lg font-semibold text-gray-800 mb-2">
            {currentNode.question}
          </h2>
          {currentNode.description && (
            <p className="text-sm text-gray-600 mb-4">{currentNode.description}</p>
          )}

          {/* End node message */}
          {currentNode.isEndNode && currentNode.endMessage && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg mb-4">
              <p className="text-amber-800">{currentNode.endMessage}</p>
            </div>
          )}

          {/* Options */}
          {!currentNode.isEndNode && (
            <div className="space-y-2 mb-4">
              {currentNode.options.map((option) => (
                <button
                  key={option.id}
                  onClick={() => handleOptionSelect(option.id)}
                  disabled={showFeedback || isComplete}
                  className={`
                    w-full p-3 text-left rounded-lg border-2 transition-all duration-200
                    ${selectedOption === option.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                    }
                    ${showFeedback && selectedOption === option.id && option.isCorrect
                      ? 'border-green-500 bg-green-50'
                      : ''
                    }
                    ${showFeedback && selectedOption === option.id && option.isCorrect === false
                      ? 'border-red-500 bg-red-50'
                      : ''
                    }
                    ${showFeedback || isComplete ? 'cursor-default' : 'cursor-pointer'}
                  `}
                >
                  <p className="text-sm font-medium text-gray-800">{option.text}</p>
                </button>
              ))}
            </div>
          )}

          {/* Feedback display */}
          {showFeedback && selectedOptionData?.consequence && showConsequences && (
            <div
              className={`p-3 rounded-lg mb-4 ${
                selectedOptionData.isCorrect
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-amber-50 border border-amber-200'
              }`}
            >
              <p className="text-sm">
                {selectedOptionData.isCorrect && (
                  <span className="text-green-700 font-medium">Correct! </span>
                )}
                {selectedOptionData.isCorrect === false && (
                  <span className="text-amber-700 font-medium">Not quite. </span>
                )}
                <span className="text-gray-700">{selectedOptionData.consequence}</span>
              </p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex justify-between">
          <div>
            {allowBacktrack && pathTaken.length > 0 && !isComplete && (
              <button
                onClick={handleBacktrack}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                ← Go Back
              </button>
            )}
          </div>
          <div className="flex gap-2">
            {isComplete && (
              <button
                onClick={handleReset}
                className="px-4 py-2 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                Try Again
              </button>
            )}
            {!isComplete && !currentNode.isEndNode && (
              <button
                onClick={handleConfirm}
                disabled={!selectedOption || showFeedback}
                className={`
                  px-4 py-2 text-sm rounded-lg font-medium transition-colors
                  ${selectedOption && !showFeedback
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                {showFeedback ? 'Processing...' : 'Confirm Choice'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Completion summary */}
      {isComplete && (
        <div className="mt-4 p-4 bg-green-100 border border-green-300 rounded-lg">
          <h3 className="font-bold text-green-800 mb-2">Scenario Complete!</h3>
          <p className="text-sm text-green-700">
            You made {pathTaken.length + 1} decisions.
            {pathTaken.filter((s) => s.isCorrect).length + (selectedOptionData?.isCorrect ? 1 : 0)} were optimal choices.
          </p>
        </div>
      )}
    </div>
  )
}

export default BranchingScenario
