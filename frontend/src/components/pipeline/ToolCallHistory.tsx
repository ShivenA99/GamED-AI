'use client'

import React, { useState } from 'react'

/**
 * Interface for individual tool calls tracked by the backend instrumentation
 */
export interface ToolCall {
  name: string
  arguments?: Record<string, unknown>
  result?: unknown
  status: 'success' | 'error' | 'timeout' | 'pending'
  latency_ms?: number
  timestamp?: string
  error?: string
}

interface ToolCallHistoryProps {
  toolCalls: ToolCall[]
  /** Optional title for the component header */
  title?: string
  /** Whether to show the summary stats section */
  showSummary?: boolean
  /** Maximum height for the tool call list (scrollable) */
  maxHeight?: string
}

/**
 * Displays tool call history for LLM agents with expandable details
 * and summary statistics.
 */
export function ToolCallHistory({
  toolCalls,
  title = 'Tool Calls',
  showSummary = true,
  maxHeight = '400px',
}: ToolCallHistoryProps) {
  const [expandedCalls, setExpandedCalls] = useState<Set<number>>(new Set())

  // Calculate summary statistics
  const stats = React.useMemo(() => {
    const successful = toolCalls.filter(tc => tc.status === 'success').length
    const failed = toolCalls.filter(tc => tc.status === 'error').length
    const timedOut = toolCalls.filter(tc => tc.status === 'timeout').length
    const pending = toolCalls.filter(tc => tc.status === 'pending').length
    const totalLatency = toolCalls.reduce((sum, tc) => sum + (tc.latency_ms || 0), 0)

    return {
      total: toolCalls.length,
      successful,
      failed,
      timedOut,
      pending,
      totalLatency,
    }
  }, [toolCalls])

  const toggleExpanded = (index: number) => {
    setExpandedCalls(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const formatLatency = (ms: number | undefined): string => {
    if (ms === undefined) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const formatTimestamp = (ts: string | undefined): string => {
    if (!ts) return '-'
    try {
      return new Date(ts).toLocaleTimeString()
    } catch {
      return ts
    }
  }

  const getStatusIcon = (status: ToolCall['status']) => {
    switch (status) {
      case 'success':
        return (
          <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )
      case 'error':
        return (
          <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )
      case 'timeout':
        return (
          <svg className="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      case 'pending':
        return (
          <svg className="w-4 h-4 text-blue-500 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        )
    }
  }

  const getStatusBadgeClasses = (status: ToolCall['status']) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'timeout':
        return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'pending':
        return 'bg-blue-100 text-blue-800 border-blue-200'
    }
  }

  if (toolCalls.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-4">
        No tool calls recorded
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <h3 className="text-sm font-medium text-gray-900">{title}</h3>

      {/* Summary Stats */}
      {showSummary && (
        <div className="grid grid-cols-4 gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-900">{stats.total}</div>
            <div className="text-xs text-gray-500">Total</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-green-600">{stats.successful}</div>
            <div className="text-xs text-gray-500">Success</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-red-600">{stats.failed + stats.timedOut}</div>
            <div className="text-xs text-gray-500">Failed</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-blue-600">{formatLatency(stats.totalLatency)}</div>
            <div className="text-xs text-gray-500">Total Time</div>
          </div>
        </div>
      )}

      {/* Tool Call List */}
      <div
        className="space-y-2 overflow-y-auto"
        style={{ maxHeight }}
      >
        {toolCalls.map((call, index) => {
          const isExpanded = expandedCalls.has(index)

          return (
            <div
              key={index}
              className={`border rounded-lg overflow-hidden ${
                call.status === 'error' ? 'border-red-200' : 'border-gray-200'
              }`}
            >
              {/* Tool Call Header - Always visible */}
              <button
                onClick={() => toggleExpanded(index)}
                className="w-full px-3 py-2 flex items-center justify-between bg-white hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {getStatusIcon(call.status)}
                  <code className="text-xs font-mono bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded">
                    {call.name}
                  </code>
                  <span className={`text-xs px-1.5 py-0.5 rounded border ${getStatusBadgeClasses(call.status)}`}>
                    {call.status}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {call.latency_ms !== undefined && (
                    <span className="text-xs text-gray-500">
                      {formatLatency(call.latency_ms)}
                    </span>
                  )}
                  {call.timestamp && (
                    <span className="text-xs text-gray-400">
                      {formatTimestamp(call.timestamp)}
                    </span>
                  )}
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

              {/* Expanded Details */}
              {isExpanded && (
                <div className="border-t border-gray-200 bg-gray-50 p-3 space-y-3">
                  {/* Error Message */}
                  {call.error && (
                    <div className="bg-red-50 border border-red-200 rounded p-2">
                      <span className="text-xs font-medium text-red-700">Error</span>
                      <p className="text-xs text-red-600 mt-1 font-mono whitespace-pre-wrap">
                        {call.error}
                      </p>
                    </div>
                  )}

                  {/* Arguments */}
                  {call.arguments && Object.keys(call.arguments).length > 0 && (
                    <div>
                      <span className="text-xs font-medium text-gray-600">Arguments</span>
                      <pre className="mt-1 text-xs bg-white border border-gray-200 rounded p-2 overflow-x-auto max-h-40">
                        {JSON.stringify(call.arguments, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Result */}
                  {call.result !== undefined && (
                    <div>
                      <span className="text-xs font-medium text-gray-600">Result</span>
                      <pre className="mt-1 text-xs bg-white border border-gray-200 rounded p-2 overflow-x-auto max-h-40">
                        {typeof call.result === 'string'
                          ? call.result
                          : JSON.stringify(call.result, null, 2)
                        }
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Compact version of ToolCallHistory for inline display
 */
export function ToolCallSummary({ toolCalls }: { toolCalls: ToolCall[] }) {
  const successful = toolCalls.filter(tc => tc.status === 'success').length
  const failed = toolCalls.filter(tc => tc.status === 'error' || tc.status === 'timeout').length
  const totalLatency = toolCalls.reduce((sum, tc) => sum + (tc.latency_ms || 0), 0)

  if (toolCalls.length === 0) {
    return null
  }

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-500">Tools:</span>
      <span className="font-medium">{toolCalls.length}</span>
      {successful > 0 && (
        <span className="text-green-600">({successful} ok)</span>
      )}
      {failed > 0 && (
        <span className="text-red-600">({failed} failed)</span>
      )}
      {totalLatency > 0 && (
        <span className="text-gray-400">
          {totalLatency < 1000 ? `${totalLatency}ms` : `${(totalLatency / 1000).toFixed(1)}s`}
        </span>
      )}
    </div>
  )
}

export default ToolCallHistory
