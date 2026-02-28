'use client'

import React, { useState, useEffect, useRef } from 'react'
import { LiveStep, LiveStepType } from './types'

// Step type styling (matching ReActTraceViewer patterns)
const STEP_STYLES: Record<LiveStepType, { bg: string; border: string; icon: string; label: string }> = {
  thought: {
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    icon: '💭',
    label: 'THOUGHT',
  },
  action: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: '⚡',
    label: 'ACTION',
  },
  observation: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    icon: '👁',
    label: 'OBSERVATION',
  },
  decision: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: '🎯',
    label: 'DECISION',
  },
}

interface LiveStepsState {
  [stageName: string]: LiveStep[]
}

interface LiveReasoningPanelProps {
  liveSteps: LiveStepsState
  currentStage?: string | null
  title?: string
  maxHeight?: string
  autoScroll?: boolean
}

/**
 * LiveReasoningPanel displays streaming reasoning steps from agents in real-time.
 *
 * This component shows the Thought/Action/Observation/Decision pattern
 * as agents work through their reasoning process, providing visibility
 * into multi-turn agentic workflows.
 */
export function LiveReasoningPanel({
  liveSteps,
  currentStage,
  title = 'Live Reasoning',
  maxHeight = '300px',
  autoScroll = true,
}: LiveReasoningPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Get all steps from all stages, flattened with stage context
  const allSteps = Object.entries(liveSteps).flatMap(([stageName, steps]) =>
    steps.map(step => ({ ...step, stageName }))
  )

  // Auto-scroll to bottom when new steps arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current && isExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [allSteps.length, autoScroll, isExpanded])

  // Format stage name for display
  const formatStageName = (name: string): string => {
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  if (allSteps.length === 0) {
    return null // Don't show panel if no live steps
  }

  return (
    <div className="border rounded-lg bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-gradient-to-r from-purple-50 to-blue-50 hover:from-purple-100 hover:to-blue-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">🧠</span>
          <div className="text-left">
            <h3 className="font-medium text-gray-900 text-sm">{title}</h3>
            <p className="text-xs text-gray-500">
              {allSteps.length} step{allSteps.length !== 1 ? 's' : ''}
              {currentStage && (
                <span className="ml-2">
                  • Currently in <span className="font-medium">{formatStageName(currentStage)}</span>
                </span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Live indicator */}
          <span className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
            Live
          </span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Steps list */}
      {isExpanded && (
        <div
          ref={scrollRef}
          className="p-3 space-y-2 overflow-y-auto"
          style={{ maxHeight }}
        >
          {allSteps.map((step, index) => {
            const style = STEP_STYLES[step.type] || STEP_STYLES.thought

            return (
              <div
                key={`${step.stageName}-${index}-${step.timestamp || ''}`}
                className={`${style.bg} ${style.border} border rounded-lg p-3 animate-fadeIn`}
              >
                {/* Step header */}
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-base">{style.icon}</span>
                  <span
                    className={`text-[10px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded ${
                      step.type === 'action'
                        ? 'bg-blue-100 text-blue-800'
                        : step.type === 'observation'
                          ? 'bg-green-100 text-green-800'
                          : step.type === 'decision'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-purple-100 text-purple-800'
                    }`}
                  >
                    {style.label}
                  </span>
                  {step.tool && (
                    <code className="text-xs bg-gray-200 text-gray-700 px-1.5 py-0.5 rounded font-mono">
                      {step.tool}
                    </code>
                  )}
                  <span className="text-[10px] text-gray-400 ml-auto">
                    {formatStageName(step.stageName)}
                  </span>
                </div>

                {/* Step content */}
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {step.content}
                </p>

                {/* Timestamp if available */}
                {step.timestamp && (
                  <span className="text-[10px] text-gray-400 block mt-1">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

/**
 * Compact version showing just the latest step with a brief summary
 */
export function LiveReasoningSummary({
  liveSteps,
  currentStage,
}: {
  liveSteps: LiveStepsState
  currentStage?: string | null
}) {
  const allSteps = Object.values(liveSteps).flat()
  const latestStep = allSteps[allSteps.length - 1]

  if (!latestStep) {
    return null
  }

  const style = STEP_STYLES[latestStep.type] || STEP_STYLES.thought

  return (
    <div className="flex items-center gap-2 text-sm bg-gray-50 rounded-lg px-3 py-2">
      <span className="flex items-center gap-1">
        <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
        <span className="text-xs text-green-600">Live</span>
      </span>
      <span className="text-gray-300">|</span>
      <span>{style.icon}</span>
      <span className="text-gray-600 truncate max-w-[200px]">
        {latestStep.content}
      </span>
      {latestStep.tool && (
        <code className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
          {latestStep.tool}
        </code>
      )}
    </div>
  )
}

export default LiveReasoningPanel
