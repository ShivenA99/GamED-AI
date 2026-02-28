'use client'

import React, { useState } from 'react'

// =============================================================================
// Types
// =============================================================================

export interface SubTask {
  id: string
  name: string
  status: 'pending' | 'running' | 'success' | 'failed'
  duration_ms?: number
  tokens?: number
  input?: Record<string, unknown>
  output?: Record<string, unknown>
  error?: string
}

export interface SubTaskPanelProps {
  subTasks: SubTask[]
  title?: string
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}

function formatSubTaskName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// =============================================================================
// Status Badge Component
// =============================================================================

const STATUS_STYLES = {
  pending: {
    dot: 'bg-gray-400',
    badge: 'bg-gray-100 text-gray-700 border-gray-200',
    text: 'Pending',
  },
  running: {
    dot: 'bg-blue-500 animate-pulse',
    badge: 'bg-blue-100 text-blue-700 border-blue-200',
    text: 'Running',
  },
  success: {
    dot: 'bg-green-500',
    badge: 'bg-green-100 text-green-700 border-green-200',
    text: 'Success',
  },
  failed: {
    dot: 'bg-red-500',
    badge: 'bg-red-100 text-red-700 border-red-200',
    text: 'Failed',
  },
}

function StatusBadge({ status }: { status: SubTask['status'] }) {
  const style = STATUS_STYLES[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${style.badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {style.text}
    </span>
  )
}

// =============================================================================
// Expandable JSON Viewer Component
// =============================================================================

function JsonViewer({ data, title }: { data: Record<string, unknown>; title: string }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="mt-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        {title}
      </button>
      {isExpanded && (
        <pre className="mt-1 p-2 bg-gray-50 rounded text-xs text-gray-700 overflow-x-auto max-h-48 border border-gray-200">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}

// =============================================================================
// Sub-Task Card Component
// =============================================================================

function SubTaskCard({ subTask }: { subTask: SubTask }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const statusStyle = STATUS_STYLES[subTask.status]

  return (
    <div
      className={`border rounded-lg transition-all ${
        subTask.status === 'failed' ? 'border-red-200 bg-red-50/30' : 'border-gray-200 bg-white'
      }`}
    >
      {/* Card Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3 flex items-center justify-between hover:bg-gray-50/50 transition-colors rounded-lg"
      >
        <div className="flex items-center gap-3">
          {/* Status dot */}
          <div className={`w-2.5 h-2.5 rounded-full ${statusStyle.dot}`} />

          {/* Name */}
          <span className="text-sm font-medium text-gray-900">
            {formatSubTaskName(subTask.name)}
          </span>

          {/* Status badge */}
          <StatusBadge status={subTask.status} />
        </div>

        <div className="flex items-center gap-3">
          {/* Duration */}
          {subTask.duration_ms !== undefined && (
            <span className="text-xs text-gray-500">
              {formatDuration(subTask.duration_ms)}
            </span>
          )}

          {/* Tokens */}
          {subTask.tokens !== undefined && subTask.tokens > 0 && (
            <span className="text-xs text-gray-500">
              {subTask.tokens.toLocaleString()} tokens
            </span>
          )}

          {/* Expand icon */}
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-100">
          {/* Error message */}
          {subTask.error && (
            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              <span className="font-medium">Error: </span>
              {subTask.error}
            </div>
          )}

          {/* Input */}
          {subTask.input && Object.keys(subTask.input).length > 0 && (
            <JsonViewer data={subTask.input} title="Input" />
          )}

          {/* Output */}
          {subTask.output && Object.keys(subTask.output).length > 0 && (
            <JsonViewer data={subTask.output} title="Output" />
          )}

          {/* Empty state */}
          {!subTask.error && !subTask.input && !subTask.output && (
            <div className="mt-2 text-xs text-gray-400 italic">
              No additional details available
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Progress Indicator Component
// =============================================================================

function ProgressIndicator({ completed, total, running }: { completed: number; total: number; running: number }) {
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{completed} of {total} completed</span>
        <span>{percent}%</span>
      </div>
      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${running > 0 ? 'bg-blue-500' : 'bg-green-500'}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      {running > 0 && (
        <div className="flex items-center gap-1 text-xs text-blue-600">
          <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span>{running} running</span>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Main SubTaskPanel Component
// =============================================================================

export function SubTaskPanel({ subTasks, title = 'Sub-Tasks' }: SubTaskPanelProps) {
  // Calculate summary stats
  const total = subTasks.length
  const completed = subTasks.filter(t => t.status === 'success').length
  const failed = subTasks.filter(t => t.status === 'failed').length
  const running = subTasks.filter(t => t.status === 'running').length
  const pending = subTasks.filter(t => t.status === 'pending').length

  const totalDuration = subTasks.reduce((sum, t) => sum + (t.duration_ms || 0), 0)
  const totalTokens = subTasks.reduce((sum, t) => sum + (t.tokens || 0), 0)

  if (total === 0) {
    return null
  }

  return (
    <div className="border-2 rounded-xl overflow-hidden shadow-sm" style={{ borderColor: '#F59E0B40' }}>
      {/* Header */}
      <div className="px-4 py-3" style={{ backgroundColor: '#F59E0B10' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Icon */}
            <div className="p-1.5 rounded-lg bg-amber-100">
              <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            </div>

            {/* Title */}
            <div>
              <h3 className="font-semibold text-gray-900">{title}</h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Breakdown of orchestrator sub-tasks
              </p>
            </div>
          </div>

          {/* Summary badges */}
          <div className="flex items-center gap-2">
            {completed > 0 && (
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                {completed} done
              </span>
            )}
            {failed > 0 && (
              <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                {failed} failed
              </span>
            )}
            {pending > 0 && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                {pending} pending
              </span>
            )}
          </div>
        </div>

        {/* Progress indicator if any are running */}
        {(running > 0 || (completed > 0 && completed < total)) && (
          <div className="mt-3">
            <ProgressIndicator completed={completed} total={total} running={running} />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4 bg-white space-y-2">
        {/* Stats row */}
        {(totalDuration > 0 || totalTokens > 0) && (
          <div className="flex items-center gap-4 text-xs text-gray-500 pb-2 border-b border-gray-100">
            {totalDuration > 0 && (
              <div className="flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Total: {formatDuration(totalDuration)}</span>
              </div>
            )}
            {totalTokens > 0 && (
              <div className="flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
                <span>Total: {totalTokens.toLocaleString()} tokens</span>
              </div>
            )}
          </div>
        )}

        {/* Sub-task list */}
        <div className="space-y-2">
          {subTasks.map(subTask => (
            <SubTaskCard key={subTask.id} subTask={subTask} />
          ))}
        </div>
      </div>
    </div>
  )
}

export default SubTaskPanel
