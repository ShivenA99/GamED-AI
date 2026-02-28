'use client'

import React from 'react'
import Link from 'next/link'
import { PipelineRun, PipelineRunSummary } from './types'

interface RetryHistoryProps {
  currentRun: PipelineRun
  childRuns?: PipelineRunSummary[]
  parentRunId?: string | null
}

const STATUS_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  success: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200' },
  failed: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
  running: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200' },
  pending: { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-200' },
  cancelled: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-200' },
}

/**
 * Retry History Visualization
 *
 * Displays the retry chain for a pipeline run:
 * - Parent runs (if this is a retry)
 * - Current run (highlighted)
 * - Child runs (retries of this run)
 */
export function RetryHistory({ currentRun, childRuns, parentRunId }: RetryHistoryProps) {
  const hasHistory = parentRunId || (childRuns && childRuns.length > 0)

  if (!hasHistory) {
    return null
  }

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusStyle = (status: string) => {
    return STATUS_STYLES[status] || STATUS_STYLES.pending
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Retry History
      </h3>

      <div className="space-y-2">
        {/* Parent run link */}
        {parentRunId && (
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center">
              <svg className="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            </div>
            <Link
              href={`/pipeline/runs/${parentRunId}`}
              className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
            >
              View parent run
            </Link>
            <span className="text-xs text-gray-400">
              (original)
            </span>
          </div>
        )}

        {/* Current run */}
        <div className="flex items-center gap-2 py-2 px-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
            <span className="text-xs text-white font-medium">
              {currentRun.run_number}
            </span>
          </div>
          <div className="flex-1">
            <span className="text-sm font-medium text-gray-900">
              Run #{currentRun.run_number}
            </span>
            {currentRun.retry_from_stage && (
              <span className="text-xs text-gray-500 ml-2">
                (retried from {currentRun.retry_from_stage.replace(/_/g, ' ')})
              </span>
            )}
          </div>
          <span className={`text-xs px-2 py-0.5 rounded ${getStatusStyle(currentRun.status).bg} ${getStatusStyle(currentRun.status).text}`}>
            {currentRun.status}
          </span>
          <span className="text-xs text-gray-400">current</span>
        </div>

        {/* Child runs (retries) */}
        {childRuns && childRuns.length > 0 && (
          <div className="ml-4 border-l-2 border-gray-200 pl-4 space-y-2">
            <span className="text-xs text-gray-500 block mb-1">Retries:</span>
            {childRuns.map((child) => {
              const style = getStatusStyle(child.status)
              return (
                <Link
                  key={child.id}
                  href={`/pipeline/runs/${child.id}`}
                  className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-gray-50 transition-colors"
                >
                  <div className={`w-5 h-5 rounded-full ${style.bg} flex items-center justify-center`}>
                    <span className={`text-xs font-medium ${style.text}`}>
                      {child.run_number}
                    </span>
                  </div>
                  <div className="flex-1">
                    <span className="text-sm text-gray-700">
                      Run #{child.run_number}
                    </span>
                    {child.retry_from_stage && (
                      <span className="text-xs text-gray-400 ml-1">
                        ({child.retry_from_stage.replace(/_/g, ' ')})
                      </span>
                    )}
                  </div>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${style.bg} ${style.text}`}>
                    {child.status}
                  </span>
                  <span className="text-xs text-gray-400">
                    {formatDate(child.started_at)}
                  </span>
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {/* Retry depth indicator */}
      {currentRun.retry_depth !== undefined && currentRun.retry_depth > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-2">
          <span className="text-xs text-gray-500">Retry depth:</span>
          <div className="flex gap-1">
            {Array.from({ length: currentRun.retry_depth + 1 }).map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${i === currentRun.retry_depth ? 'bg-blue-500' : 'bg-gray-300'}`}
              />
            ))}
          </div>
          <span className="text-xs text-gray-400">
            ({currentRun.retry_depth} of 3 max)
          </span>
        </div>
      )}
    </div>
  )
}

export default RetryHistory
