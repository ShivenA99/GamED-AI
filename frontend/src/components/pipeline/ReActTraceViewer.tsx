'use client'

import React, { useState } from 'react'
import { ReActTrace, ReActStep, StepType } from './types'

interface ReActTraceViewerProps {
  trace: ReActTrace
  title?: string
  defaultExpanded?: boolean
}

// Step type styling
const STEP_STYLES: Record<StepType, { bg: string; border: string; icon: string; label: string }> = {
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
  error: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: '❌',
    label: 'ERROR',
  },
  result: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    icon: '✅',
    label: 'RESULT',
  },
}

function StepItem({ step, index }: { step: ReActStep; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const style = STEP_STYLES[step.type] || STEP_STYLES.thought

  const hasDetails = step.tool || step.tool_args || step.result || step.metadata

  return (
    <div className={`${style.bg} ${style.border} border rounded-lg p-3`}>
      {/* Step header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className="text-lg flex-shrink-0">{style.icon}</span>
          <span
            className={`text-[10px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded ${
              step.type === 'error'
                ? 'bg-red-100 text-red-800'
                : step.type === 'result'
                  ? 'bg-emerald-100 text-emerald-800'
                  : step.type === 'action'
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
          {step.duration_ms !== undefined && step.duration_ms > 0 && (
            <span className="text-xs text-gray-400 ml-auto flex-shrink-0">
              {step.duration_ms}ms
            </span>
          )}
        </div>
        {hasDetails && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="ml-2 text-gray-400 hover:text-gray-600 flex-shrink-0"
          >
            <svg
              className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Step content */}
      <p className="text-sm text-gray-700 mt-2 leading-relaxed">{step.content}</p>

      {/* Expanded details */}
      {expanded && hasDetails && (
        <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
          {step.tool_args && Object.keys(step.tool_args).length > 0 && (
            <div>
              <span className="text-xs text-gray-500 font-medium">Arguments:</span>
              <pre className="text-xs mt-1 bg-gray-100 p-2 rounded overflow-x-auto max-h-24">
                {JSON.stringify(step.tool_args, null, 2)}
              </pre>
            </div>
          )}
          {step.result !== undefined && (
            <div>
              <span className="text-xs text-gray-500 font-medium">Result:</span>
              <pre className="text-xs mt-1 bg-gray-100 p-2 rounded overflow-x-auto max-h-32">
                {typeof step.result === 'string'
                  ? step.result
                  : JSON.stringify(step.result, null, 2)}
              </pre>
            </div>
          )}
          {step.metadata && Object.keys(step.metadata).length > 0 && (
            <div>
              <span className="text-xs text-gray-500 font-medium">Metadata:</span>
              <pre className="text-xs mt-1 bg-gray-100 p-2 rounded overflow-x-auto max-h-20">
                {JSON.stringify(step.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ReActTraceViewer({ trace, title, defaultExpanded = true }: ReActTraceViewerProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  if (!trace || !trace.steps || trace.steps.length === 0) {
    return null
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <div className="border rounded-lg overflow-hidden bg-white">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full bg-gray-50 px-4 py-3 flex items-center justify-between hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">
            {trace.success ? '🎯' : '⚠️'}
          </span>
          <div className="text-left">
            <h4 className="font-medium text-gray-900 text-sm">
              {title || `${trace.phase.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Trace`}
            </h4>
            <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
              <span>{trace.steps.length} steps</span>
              <span className="text-gray-300">|</span>
              <span>{trace.iterations} iteration{trace.iterations !== 1 ? 's' : ''}</span>
              {trace.total_duration_ms > 0 && (
                <>
                  <span className="text-gray-300">|</span>
                  <span>{formatDuration(trace.total_duration_ms)}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              trace.success
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-700'
            }`}
          >
            {trace.success ? 'Success' : 'Failed'}
          </span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </button>

      {/* Steps */}
      {isExpanded && (
        <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
          {trace.steps.map((step, index) => (
            <StepItem key={`${step.timestamp}-${index}`} step={step} index={index} />
          ))}
        </div>
      )}
    </div>
  )
}

// Multi-trace viewer for zone_planner which has multiple phases
export function MultiTraceViewer({
  traces,
  title,
}: {
  traces: ReActTrace[]
  title?: string
}) {
  if (!traces || traces.length === 0) {
    return null
  }

  const totalSteps = traces.reduce((sum, t) => sum + (t.steps?.length || 0), 0)
  const totalDuration = traces.reduce((sum, t) => sum + (t.total_duration_ms || 0), 0)
  const allSuccess = traces.every(t => t.success)

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{allSuccess ? '✅' : '⚠️'}</span>
          <span className="font-medium text-gray-900">
            {title || 'Reasoning Trace'}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>{traces.length} phase{traces.length !== 1 ? 's' : ''}</span>
          <span className="text-gray-300">|</span>
          <span>{totalSteps} steps</span>
          {totalDuration > 0 && (
            <>
              <span className="text-gray-300">|</span>
              <span>
                {totalDuration < 1000
                  ? `${totalDuration}ms`
                  : `${(totalDuration / 1000).toFixed(1)}s`}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Individual traces */}
      {traces.map((trace, index) => (
        <ReActTraceViewer
          key={`${trace.phase}-${index}`}
          trace={trace}
          defaultExpanded={index === 0}
        />
      ))}
    </div>
  )
}
