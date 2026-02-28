'use client'

import { useState } from 'react'
import { PipelineRun, STATUS_COLORS } from './types'
import Link from 'next/link'

interface RunHistoryCardProps {
  runs: PipelineRun[]
  processId: string
  onRetry?: (runId: string, stageName: string) => void
}

export function RunHistoryCard({ runs, processId, onRetry }: RunHistoryCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (runs.length === 0) {
    return (
      <div className="mt-4 border-t pt-4">
        <div className="text-sm text-gray-500 text-center py-4">
          <p>No pipeline runs found for this game.</p>
          <Link
            href="/pipeline"
            className="mt-2 inline-block text-blue-600 hover:underline text-sm"
          >
            View all runs in Pipeline Dashboard →
          </Link>
        </div>
      </div>
    )
  }

  const latestRun = runs[0]
  const hasMultipleRuns = runs.length > 1

  const formatDuration = (ms: number | null) => {
    if (ms === null) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="mt-4 border-t pt-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
      >
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span>Run History ({runs.length} {runs.length === 1 ? 'run' : 'runs'})</span>
      </button>

      {isExpanded && (
        <div className="mt-3 space-y-2 pl-6">
          {runs.map((run, index) => (
            <RunHistoryItem
              key={run.id}
              run={run}
              isLatest={index === 0}
              onRetry={onRetry}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function RunHistoryItem({
  run,
  isLatest,
  onRetry,
}: {
  run: PipelineRun
  isLatest: boolean
  onRetry?: (runId: string, stageName: string) => void
}) {
  const statusColors = STATUS_COLORS[run.status] || STATUS_COLORS.pending

  const formatDuration = (ms: number | null) => {
    if (ms === null) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
      ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className={`
      p-3 rounded-lg border
      ${isLatest ? 'bg-white' : 'bg-gray-50'}
    `}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Status badge */}
          <span className={`px-2 py-0.5 text-xs rounded-full ${statusColors.bg} ${statusColors.text}`}>
            {run.status}
          </span>

          {/* Run info */}
          <div>
            <span className="text-sm font-medium text-gray-900">
              Run #{run.run_number}
              {isLatest && (
                <span className="ml-2 text-xs text-gray-400">(latest)</span>
              )}
            </span>

            {/* Retry info */}
            {run.retry_from_stage && (
              <div className="text-xs text-gray-500">
                Retried from: {run.retry_from_stage.replace(/_/g, ' ')}
              </div>
            )}
          </div>
        </div>

        {/* Metadata */}
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>{formatTime(run.started_at)}</span>
          {run.duration_ms && (
            <span>{formatDuration(run.duration_ms)}</span>
          )}
        </div>
      </div>

      {/* Error message for failed runs */}
      {run.status === 'failed' && run.error_message && (
        <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-700">
          {run.error_message.length > 100
            ? run.error_message.slice(0, 100) + '...'
            : run.error_message}
        </div>
      )}

      {/* Actions */}
      <div className="mt-2 flex items-center gap-2">
        <Link
          href={`/pipeline/runs/${run.id}`}
          className="text-xs text-blue-600 hover:underline"
        >
          View Details
        </Link>

        {run.status === 'failed' && onRetry && (
          <button
            onClick={() => onRetry(run.id, run.retry_from_stage || '')}
            className="text-xs text-blue-600 hover:underline"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  )
}

// Simplified run badge for compact displays
export function RunStatusBadge({ run }: { run: PipelineRun }) {
  const statusColors = STATUS_COLORS[run.status] || STATUS_COLORS.pending

  return (
    <div className="flex items-center gap-2">
      <span className={`px-2 py-0.5 text-xs rounded-full ${statusColors.bg} ${statusColors.text}`}>
        {run.status}
      </span>
      <span className="text-xs text-gray-500">v{run.run_number}</span>
    </div>
  )
}

// Run timeline for displaying multiple runs vertically
export function RunTimeline({ runs }: { runs: PipelineRun[] }) {
  if (runs.length === 0) return null

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-gray-200" />

      <div className="space-y-4">
        {runs.map((run, index) => (
          <div key={run.id} className="relative flex items-start gap-4 pl-8">
            {/* Dot on timeline */}
            <div className={`
              absolute left-1.5 w-3 h-3 rounded-full border-2 bg-white
              ${run.status === 'success' ? 'border-green-500' :
                run.status === 'failed' ? 'border-red-500' :
                run.status === 'running' ? 'border-blue-500' :
                'border-gray-300'}
            `} />

            {/* Run content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Run #{run.run_number}</span>
                <span className={`
                  text-xs px-2 py-0.5 rounded-full
                  ${run.status === 'success' ? 'bg-green-100 text-green-700' :
                    run.status === 'failed' ? 'bg-red-100 text-red-700' :
                    run.status === 'running' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-700'}
                `}>
                  {run.status}
                </span>
              </div>

              {run.started_at && (
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(run.started_at).toLocaleString()}
                </p>
              )}

              {run.retry_from_stage && (
                <p className="text-xs text-gray-400 mt-1">
                  Retried from {run.retry_from_stage.replace(/_/g, ' ')}
                </p>
              )}

              {run.status === 'failed' && run.error_message && (
                <p className="text-xs text-red-600 mt-1 truncate">
                  {run.error_message}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
