'use client'

import React, { useState, useEffect, useMemo } from 'react'
import DOMPurify from 'dompurify'
import { StageExecution, STATUS_COLORS, ReActTrace, ZoneOverlayData, ZoneGroup, DetailLevel } from './types'
import { ReActTraceViewer, MultiTraceViewer } from './ReActTraceViewer'
import { ToolCallHistory, ToolCall } from './ToolCallHistory'
import { ZoneOverlay, ZoneList } from './ZoneOverlay'

// Configure DOMPurify for SVG sanitization
const sanitizeSVG = (svg: string): string => {
  return DOMPurify.sanitize(svg, {
    USE_PROFILES: { svg: true, svgFilters: true },
    ADD_TAGS: ['use'],
    ADD_ATTR: ['xlink:href', 'xmlns:xlink'],
  })
}

// Configure DOMPurify for HTML (syntax highlighting)
const sanitizeHTML = (html: string): string => {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['span', 'div', 'br'],
    ALLOWED_ATTR: ['class', 'style'],
  })
}

interface StagePanelProps {
  stage: StageExecution & { run_id?: string }
  onRetry?: (stageName: string) => void
  onClose: () => void
}

export function StagePanel({ stage, onRetry, onClose }: StagePanelProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'input' | 'output' | 'logs' | 'tools'>('overview')
  const [logs, setLogs] = useState<Array<{ id: string; level: string; message: string; timestamp: string }>>([])
  const [loadingLogs, setLoadingLogs] = useState(false)
  const [logSearchTerm, setLogSearchTerm] = useState('')
  const [isRetrying, setIsRetrying] = useState(false)
  const [retryError, setRetryError] = useState<string | null>(null)
  const [showRetryConfirm, setShowRetryConfirm] = useState(false)
  const statusColors = STATUS_COLORS[stage.status] || STATUS_COLORS.pending

  const handleRetry = async () => {
    if (!onRetry) return
    
    // Prevent retrying successful stages (defensive check)
    if (stage.status === 'success') {
      setRetryError('Cannot retry a successful stage. Only failed or degraded stages can be retried.')
      return
    }
    
    setIsRetrying(true)
    setRetryError(null)

    try {
      await onRetry(stage.stage_name)
      // If successful, the parent component should handle navigation
      // Don't close dialog here - let navigation happen
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Retry failed. Please try again.'
      setRetryError(errorMessage)
      console.error('[StagePanel] Retry error:', err)
      // Keep dialog open so user can see the error
    } finally {
      setIsRetrying(false)
    }
  }

  // Fetch logs when logs tab is selected, and poll for updates if stage is running
  useEffect(() => {
    const fetchLogs = async () => {
      if (activeTab === 'logs' && stage.id && stage.run_id) {
        setLoadingLogs(true)
        try {
          const res = await fetch(`/api/observability/runs/${stage.run_id}/logs?stage_id=${stage.id}`)
          const data = await res.json()
          setLogs(data.logs || [])
        } catch (err) {
          console.error('Error fetching logs:', err)
        } finally {
          setLoadingLogs(false)
        }
      } else if (stage.logs) {
        setLogs(stage.logs)
      }
    }

    fetchLogs()

    // Poll for logs if stage is running
    if (activeTab === 'logs' && stage.status === 'running' && stage.id && stage.run_id) {
      const interval = setInterval(fetchLogs, 2000) // Poll every 2 seconds
      return () => clearInterval(interval)
    }
  }, [activeTab, stage.id, stage.run_id, stage.logs, stage.status])

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  const formatStageName = (name: string): string => {
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  return (
    <div className="w-96 h-full bg-white border-l shadow-lg flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex justify-between items-center bg-gray-50">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {formatStageName(stage.stage_name)}
          </h2>
          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors.bg} ${statusColors.text}`}>
            {stage.status}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-200 rounded-full"
        >
          <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        {(['overview', 'input', 'output', 'logs', 'tools'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`
              flex-1 py-2 text-sm font-medium capitalize
              ${activeTab === tab
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'}
            `}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {/* Timing */}
            <Section title="Timing">
              <InfoRow label="Started" value={stage.started_at ? new Date(stage.started_at).toLocaleString() : '-'} />
              <InfoRow label="Finished" value={stage.finished_at ? new Date(stage.finished_at).toLocaleString() : '-'} />
              <InfoRow label="Duration" value={stage.duration_ms ? formatDuration(stage.duration_ms) : '-'} />
              {stage.retry_count > 0 && (
                <InfoRow 
                  label="Retry Count" 
                  value={stage.retry_count.toString()}
                  valueClassName="text-orange-600"
                />
              )}
            </Section>

            {/* LLM Metrics */}
            {(stage.model_id || stage.total_tokens || stage.estimated_cost_usd) && (
              <Section title="LLM Metrics">
                {stage.model_id && (
                  <InfoRow label="Model" value={stage.model_id} />
                )}
                {stage.prompt_tokens != null && (
                  <InfoRow label="Prompt tokens" value={stage.prompt_tokens.toLocaleString()} />
                )}
                {stage.completion_tokens != null && (
                  <InfoRow label="Completion tokens" value={stage.completion_tokens.toLocaleString()} />
                )}
                {stage.total_tokens != null && (
                  <InfoRow label="Total tokens" value={stage.total_tokens.toLocaleString()} />
                )}
                {stage.latency_ms != null && (
                  <InfoRow
                    label="Latency"
                    value={formatDuration(stage.latency_ms)}
                  />
                )}
                {stage.estimated_cost_usd != null && (
                  <InfoRow
                    label="Cost"
                    value={`$${stage.estimated_cost_usd.toFixed(4)}`}
                  />
                )}
              </Section>
            )}

            {/* Validation */}
            {stage.validation_passed !== null && (
              <Section title="Validation">
                <InfoRow
                  label="Passed"
                  value={stage.validation_passed ? 'Yes' : 'No'}
                  valueClassName={stage.validation_passed ? 'text-green-600' : 'text-red-600'}
                />
                {stage.validation_score !== null && (
                  <InfoRow label="Score" value={`${(stage.validation_score * 100).toFixed(0)}%`} />
                )}
                {stage.validation_errors && stage.validation_errors.length > 0 && (
                  <div className="mt-2">
                    <span className="text-xs text-gray-500 font-medium">Errors:</span>
                    <ul className="mt-1 space-y-1">
                      {stage.validation_errors.map((error, i) => (
                        <li key={i} className="text-xs text-red-600 bg-red-50 p-2 rounded">
                          {error}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </Section>
            )}

            {/* Error */}
            {stage.error_message && (
              <Section title="Error">
                <div className="bg-red-50 p-3 rounded text-sm text-red-700">
                  {stage.error_message}
                </div>
                {stage.error_traceback && (
                  <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto max-h-40">
                    {stage.error_traceback}
                  </pre>
                )}
              </Section>
            )}

            {/* Sub-stage retry attempts (for compound V4 nodes) */}
            {(() => {
              const attempts = stage.output_snapshot?._attempts as Array<Record<string, unknown>> | undefined
              if (!attempts || attempts.length === 0) return null
              return (
              <Section title="Retry Attempts">
                <div className="space-y-2">
                  {attempts.map((attempt, i) => {
                    const status = attempt.status as string
                    const error = attempt.error as string | undefined
                    const durationMs = attempt.duration_ms as number | undefined
                    const model = attempt.model as string | undefined
                    const attemptNum = attempt.attempt as number | undefined
                    const promptPreview = attempt.prompt_preview as string | undefined
                    const responsePreview = attempt.response_preview as string | undefined
                    return (
                      <div key={i} className={`p-2.5 rounded-lg border text-xs ${
                        status === 'success' ? 'bg-green-50 border-green-200' :
                        status === 'parse_error' ? 'bg-yellow-50 border-yellow-200' :
                        status === 'validation_failed' ? 'bg-orange-50 border-orange-200' :
                        'bg-red-50 border-red-200'
                      }`}>
                        <div className="flex items-center justify-between">
                          <span className="font-medium">
                            Attempt {attemptNum || i + 1}
                            <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                              status === 'success' ? 'bg-green-100 text-green-800' :
                              status === 'parse_error' ? 'bg-yellow-100 text-yellow-800' :
                              status === 'validation_failed' ? 'bg-orange-100 text-orange-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {status?.replace(/_/g, ' ')}
                            </span>
                          </span>
                          <span className="text-gray-400 font-mono text-[10px]">
                            {model && `${model} `}
                            {durationMs != null && `${(durationMs / 1000).toFixed(1)}s`}
                          </span>
                        </div>
                        {error && (
                          <p className="mt-1.5 text-[11px] text-red-600 font-mono whitespace-pre-wrap break-words">
                            {error}
                          </p>
                        )}
                        {promptPreview && (
                          <details className="mt-2">
                            <summary className="text-[10px] text-gray-500 cursor-pointer hover:text-gray-700">
                              Prompt ({promptPreview.length} chars)
                            </summary>
                            <pre className="mt-1 text-[10px] bg-white/70 p-2 rounded overflow-x-auto max-h-32 whitespace-pre-wrap break-words text-gray-600">
                              {promptPreview}
                            </pre>
                          </details>
                        )}
                        {responsePreview && (
                          <details className="mt-1">
                            <summary className="text-[10px] text-gray-500 cursor-pointer hover:text-gray-700">
                              Response ({responsePreview.length} chars)
                            </summary>
                            <pre className="mt-1 text-[10px] bg-white/70 p-2 rounded overflow-x-auto max-h-32 whitespace-pre-wrap break-words text-gray-600">
                              {responsePreview}
                            </pre>
                          </details>
                        )}
                      </div>
                    )
                  })}
                </div>
              </Section>
              )
            })()}

            {/* Sub-stage context info */}
            {stage.stage_name.includes('::') && (() => {
              const subType = stage.output_snapshot?._sub_stage_type as string | undefined
              const mechType = stage.output_snapshot?._mechanic_type as string | undefined
              const sceneId = stage.output_snapshot?._scene_id as string | undefined
              const promptPreview = stage.output_snapshot?._prompt_preview as string | undefined
              const responsePreview = stage.output_snapshot?._response_preview as string | undefined
              return (
                <>
                <Section title="Sub-stage Info">
                  <InfoRow label="Parent Agent" value={stage.stage_name.split('::')[0]} />
                  {subType && <InfoRow label="Type" value={subType} />}
                  {mechType && <InfoRow label="Mechanic" value={mechType.replace(/_/g, ' ')} />}
                  {sceneId && <InfoRow label="Scene" value={sceneId} />}
                </Section>
                {(promptPreview || responsePreview) && (
                  <Section title="LLM Call">
                    {promptPreview && (
                      <details>
                        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700 font-medium">
                          Prompt ({promptPreview.length} chars)
                        </summary>
                        <pre className="mt-1 text-[10px] bg-gray-50 p-2 rounded overflow-x-auto max-h-40 whitespace-pre-wrap break-words text-gray-600 border">
                          {promptPreview}
                        </pre>
                      </details>
                    )}
                    {responsePreview && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700 font-medium">
                          Raw Response ({responsePreview.length} chars)
                        </summary>
                        <pre className="mt-1 text-[10px] bg-gray-50 p-2 rounded overflow-x-auto max-h-40 whitespace-pre-wrap break-words text-gray-600 border">
                          {responsePreview}
                        </pre>
                      </details>
                    )}
                  </Section>
                )}
                </>
              )
            })()}
          </div>
        )}

        {activeTab === 'input' && (
          <div>
            {stage.input_state_keys && stage.input_state_keys.length > 0 && (
              <div className="mb-3">
                <span className="text-xs text-gray-500 font-medium">State keys read:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {stage.input_state_keys.map(key => (
                    <span key={key} className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                      {key}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <JsonViewer data={stage.input_snapshot} />
          </div>
        )}

        {activeTab === 'output' && (
          <div>
            {stage.output_state_keys && stage.output_state_keys.length > 0 && (
              <div className="mb-3">
                <span className="text-xs text-gray-500 font-medium">State keys written:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {stage.output_state_keys.map(key => (
                    <span key={key} className="text-xs bg-green-100 px-2 py-0.5 rounded">
                      {key}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <AgentOutputRenderer stageName={stage.stage_name} output={stage.output_snapshot} />
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="space-y-2">
            {/* Sub-stage notice */}
            {stage.stage_name.includes('::') && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
                <span className="font-medium">Sub-stage of {stage.stage_name.split('::')[0]}</span>
                <p className="mt-1 text-amber-600">
                  Individual sub-stage logs are not tracked separately. Logs below are from the parent agent.
                </p>
              </div>
            )}
            {/* Search input */}
            <div className="sticky top-0 bg-white pb-2 border-b">
              <div className="relative">
                <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  placeholder="Search logs..."
                  value={logSearchTerm}
                  onChange={(e) => setLogSearchTerm(e.target.value)}
                  className="w-full pl-8 pr-3 py-2 text-xs border rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                {logSearchTerm && (
                  <button
                    onClick={() => setLogSearchTerm('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
              {logSearchTerm && logs.length > 0 && (
                <div className="text-xs text-gray-500 mt-1">
                  {logs.filter(log =>
                    log.message.toLowerCase().includes(logSearchTerm.toLowerCase()) ||
                    log.level.toLowerCase().includes(logSearchTerm.toLowerCase())
                  ).length} of {logs.length} logs match
                </div>
              )}
            </div>

            {/* Logs list */}
            {loadingLogs && logs.length === 0 && !stage.output_snapshot?._react_trace ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                <p className="text-sm text-gray-500">Loading logs...</p>
              </div>
            ) : logs.length > 0 ? (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {logs
                  .filter(log =>
                    !logSearchTerm ||
                    log.message.toLowerCase().includes(logSearchTerm.toLowerCase()) ||
                    log.level.toLowerCase().includes(logSearchTerm.toLowerCase())
                  )
                  .map(log => (
                    <div
                      key={log.id}
                      className={`text-xs p-3 rounded-lg border ${
                        log.level === 'error'
                          ? 'bg-red-50 text-red-700 border-red-200'
                          : log.level === 'warn' || log.level === 'warning'
                            ? 'bg-yellow-50 text-yellow-700 border-yellow-200'
                            : 'bg-gray-50 text-gray-700 border-gray-200'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className={`font-mono uppercase text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                          log.level === 'error' ? 'bg-red-100 text-red-800' :
                          log.level === 'warn' || log.level === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                          log.level === 'info' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {log.level}
                        </span>
                        <span className="text-gray-400 text-[10px]">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words">
                        {logSearchTerm ? (
                          highlightSearchTerm(log.message, logSearchTerm)
                        ) : (
                          log.message
                        )}
                      </p>
                    </div>
                  ))}
                {stage.status === 'running' && (
                  <div className="text-center py-2">
                    <div className="inline-flex items-center gap-2 text-xs text-blue-600">
                      <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                      <span>Streaming logs...</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (() => {
              // Fallback: show ReAct trace from output_snapshot as log entries
              const output = stage.output_snapshot || {}
              const reactTrace = output._react_trace as Array<{
                iteration: number
                thought?: string
                action?: { name: string; arguments?: Record<string, unknown> } | null
                observation?: string
              }> | undefined

              if (reactTrace && reactTrace.length > 0) {
                return (
                  <div className="space-y-2 max-h-[600px] overflow-y-auto">
                    <p className="text-xs text-gray-400 mb-2">Showing ReAct trace (no streaming logs available)</p>
                    {reactTrace.map((step, idx) => (
                      <div key={idx} className="space-y-1">
                        {step.thought && (
                          <div className="text-xs p-2 rounded-lg border bg-blue-50 text-blue-700 border-blue-200">
                            <span className="font-mono uppercase text-[10px] font-semibold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">
                              thought #{step.iteration}
                            </span>
                            <p className="mt-1 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words">
                              {step.thought.substring(0, 500)}
                            </p>
                          </div>
                        )}
                        {step.action && (
                          <div className="text-xs p-2 rounded-lg border bg-purple-50 text-purple-700 border-purple-200">
                            <span className="font-mono uppercase text-[10px] font-semibold px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">
                              action
                            </span>
                            <p className="mt-1 font-mono text-[11px] leading-relaxed">
                              {step.action.name}({step.action.arguments ? JSON.stringify(step.action.arguments).substring(0, 200) : ''})
                            </p>
                          </div>
                        )}
                        {step.observation && (
                          <div className="text-xs p-2 rounded-lg border bg-gray-50 text-gray-700 border-gray-200">
                            <span className="font-mono uppercase text-[10px] font-semibold px-1.5 py-0.5 rounded bg-gray-100 text-gray-800">
                              observation
                            </span>
                            <p className="mt-1 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words">
                              {step.observation.substring(0, 500)}
                            </p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )
              }
              return <p className="text-sm text-gray-500 text-center py-4">No logs available</p>
            })()}
          </div>
        )}

        {activeTab === 'tools' && (
          <div className="space-y-4">
            {/* Sub-stage notice */}
            {stage.stage_name.includes('::') && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
                <span className="font-medium">Sub-stage of {stage.stage_name.split('::')[0]}</span>
                <p className="mt-1 text-amber-600">
                  Tool calls shown below are from the parent agent&apos;s session. Individual sub-stage tool calls are tracked as retry attempts in the Overview tab.
                </p>
              </div>
            )}
            {/* Extract tool calls from output_snapshot if available */}
            {(() => {
              const output = stage.output_snapshot || {}
              const toolCalls: ToolCall[] = []

              // Check for tool_calls in various locations in the output
              if (output.tool_calls && Array.isArray(output.tool_calls)) {
                toolCalls.push(...output.tool_calls.map((tc: Record<string, unknown>) => ({
                  name: tc.name as string || 'unknown',
                  arguments: tc.arguments as Record<string, unknown> || tc.args as Record<string, unknown>,
                  result: tc.result,
                  status: (tc.status as ToolCall['status']) || 'success',
                  latency_ms: tc.latency_ms as number,
                  timestamp: tc.timestamp as string,
                  error: tc.error as string,
                })))
              }

              // Check for api_calls (e.g., from Serper searches)
              if (output.api_calls && Array.isArray(output.api_calls)) {
                toolCalls.push(...output.api_calls.map((ac: Record<string, unknown>) => ({
                  name: ac.api as string || ac.name as string || 'api_call',
                  arguments: ac.params as Record<string, unknown> || ac.arguments as Record<string, unknown>,
                  result: ac.response || ac.result,
                  status: ac.error ? 'error' as const : 'success' as const,
                  latency_ms: ac.latency_ms as number,
                  timestamp: ac.timestamp as string,
                  error: ac.error as string,
                })))
              }

              // Check for react_trace steps that are actions with tools
              if (output.react_trace && typeof output.react_trace === 'object') {
                const trace = output.react_trace as { steps?: Array<Record<string, unknown>> }
                if (trace.steps && Array.isArray(trace.steps)) {
                  const actionSteps = trace.steps.filter((s: Record<string, unknown>) => s.type === 'action' && s.tool)
                  toolCalls.push(...actionSteps.map((s: Record<string, unknown>) => ({
                    name: s.tool as string,
                    arguments: s.tool_args as Record<string, unknown>,
                    result: s.result,
                    status: s.result !== undefined ? 'success' as const : 'pending' as const,
                    latency_ms: s.duration_ms as number,
                    timestamp: s.timestamp as string,
                  })))
                }
              }

              // Check for _react_trace (v3 ReAct agents store trace with underscore prefix)
              if (output._react_trace && Array.isArray(output._react_trace)) {
                const traceSteps = output._react_trace as Array<Record<string, unknown>>
                const actionSteps = traceSteps.filter((s: Record<string, unknown>) => s.action)
                toolCalls.push(...actionSteps.map((s: Record<string, unknown>) => {
                  const action = s.action as { name?: string; arguments?: Record<string, unknown> } | null
                  return {
                    name: action?.name || 'unknown',
                    arguments: action?.arguments,
                    result: s.observation,
                    status: s.observation !== undefined ? 'success' as const : 'pending' as const,
                    latency_ms: undefined,
                    timestamp: undefined,
                  }
                }))
              }

              // Check for _tool_metrics (from instrumentation ctx.set_tool_metrics)
              if (output._tool_metrics && typeof output._tool_metrics === 'object') {
                const tm = output._tool_metrics as { tool_calls?: Array<Record<string, unknown>> }
                if (tm.tool_calls && Array.isArray(tm.tool_calls)) {
                  toolCalls.push(...tm.tool_calls.map((tc: Record<string, unknown>) => ({
                    name: tc.name as string || 'unknown',
                    arguments: tc.arguments as Record<string, unknown>,
                    result: tc.result,
                    status: (tc.status as ToolCall['status']) || 'success',
                    latency_ms: tc.latency_ms as number,
                    timestamp: tc.timestamp as string,
                    error: tc.error as string,
                  })))
                }
              }

              if (toolCalls.length > 0) {
                return <ToolCallHistory toolCalls={toolCalls} title="Tool Calls" />
              }

              return (
                <div className="text-center py-8">
                  <div className="w-12 h-12 mx-auto mb-3 bg-gray-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <p className="text-sm text-gray-500">No tool calls recorded for this stage</p>
                  <p className="text-xs text-gray-400 mt-1">Tool calls will appear here when agents use external tools</p>
                </div>
              )
            })()}
          </div>
        )}
      </div>

      {/* Footer with retry/review actions - show for failed, degraded (fallback), or human_review */}
      {(stage.status === 'failed' || stage.status === 'degraded' || stage.stage_name === 'human_review') && onRetry && !stage.id?.startsWith('pending-') && !stage.id?.startsWith('inferred-') && (
        <div className="p-4 border-t bg-gray-50 space-y-3">
          {/* Human Review Banner */}
          {stage.stage_name === 'human_review' && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-3">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-purple-800">Human Review Required</h3>
                  <p className="text-sm text-purple-700 mt-1">
                    The pipeline has paused and requires your review before continuing.
                    Please review the validation errors below and choose an action.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Fallback Used Banner */}
          {stage.status === 'degraded' && stage.stage_name !== 'human_review' && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-3">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-xl">⚠️</span>
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-orange-800">Fallback Used</h3>
                  <p className="text-sm text-orange-700 mt-1">
                    This stage completed with a fallback method. The primary method failed or was unavailable.
                    You can retry to attempt the primary method again.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Validation Errors Summary (for failed stages) */}
          {stage.validation_errors && stage.validation_errors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
              <h4 className="text-sm font-medium text-red-800 mb-2 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Validation Errors
              </h4>
              <ul className="space-y-1">
                {stage.validation_errors.map((error, i) => (
                  <li key={i} className="text-xs text-red-700 flex items-start gap-2">
                    <span className="text-red-400 mt-0.5">•</span>
                    <span>{error}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!showRetryConfirm ? (
            <div className="space-y-2">
              {/* Primary Action: Retry */}
              <button
                onClick={() => setShowRetryConfirm(true)}
                className={`w-full py-3 text-white rounded-lg font-medium flex items-center justify-center gap-2 shadow-sm transition-all hover:shadow ${
                  stage.status === 'degraded'
                    ? 'bg-orange-600 hover:bg-orange-700'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {stage.stage_name === 'human_review'
                  ? 'Approve & Continue Pipeline'
                  : stage.status === 'degraded'
                    ? 'Retry with Primary Method'
                    : 'Retry from this Stage'}
              </button>

              {/* Help text */}
              <p className="text-xs text-center text-gray-500">
                {stage.stage_name === 'human_review'
                  ? 'This will resume the pipeline from the last failed stage'
                  : stage.status === 'degraded'
                    ? 'This will attempt the primary method instead of fallback'
                    : 'This will re-run this stage and all subsequent stages'}
              </p>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 space-y-3">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <p className="font-medium text-yellow-800">Confirm Action</p>
                  <p className="text-sm text-yellow-700 mt-1">
                    {stage.stage_name === 'human_review'
                      ? 'This will resume the pipeline and re-run the failed stage with a fresh attempt.'
                      : stage.status === 'degraded'
                        ? <>This will retry <strong>{formatStageName(stage.stage_name)}</strong> using the primary method instead of fallback. Subsequent stages will also be re-run.</>
                        : <>This will re-run <strong>{formatStageName(stage.stage_name)}</strong> and all subsequent stages. Previous data will be replaced.</>}
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowRetryConfirm(false)}
                  className="flex-1 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRetry}
                  disabled={isRetrying}
                  className="flex-1 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isRetrying ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Retrying...
                    </>
                  ) : (
                    'Confirm Retry'
                  )}
                </button>
              </div>
            </div>
          )}
          {retryError && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-2">
                <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-800">Retry Failed</p>
                  <p className="text-xs text-red-700 mt-1">{retryError}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Info for inferred/pending stages */}
      {(stage.id?.startsWith('inferred-') || stage.id?.startsWith('pending-')) && (
        <div className="p-4 border-t bg-yellow-50">
          <div className="text-sm text-yellow-800">
            {stage.status === 'success' ? (
              <>
                <p className="font-medium mb-1">⚠️ Stage data not recorded</p>
                <p className="text-xs">The pipeline completed successfully, but this stage's execution data was not saved to the database. This indicates a backend instrumentation issue.</p>
              </>
            ) : (
              <>
                <p className="font-medium mb-1">Stage not executed yet</p>
                <p className="text-xs">This stage will run when the pipeline reaches it.</p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-gray-900 mb-2">{title}</h3>
      <div className="space-y-1">{children}</div>
    </div>
  )
}

function InfoRow({
  label,
  value,
  valueClassName = '',
}: {
  label: string
  value: string
  valueClassName?: string
}) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className={`font-medium ${valueClassName || 'text-gray-900'}`}>{value}</span>
    </div>
  )
}

/**
 * Convert backend _react_trace (from react_base.py) to frontend ReActTrace format.
 * Backend format: Array<{iteration, thought, action: {name, arguments}, observation}>
 * Frontend format: ReActTrace with steps[] of type ReActStep
 */
function convertBackendTrace(
  rawTrace: Array<Record<string, unknown>>,
  agentName: string,
  metrics?: { iterations?: number; tool_calls?: number; latency_ms?: number }
): import('./types').ReActTrace {
  const steps: import('./types').ReActStep[] = []
  const now = new Date().toISOString()

  for (const step of rawTrace) {
    // Thought step
    if (typeof step.thought === 'string' && step.thought) {
      steps.push({
        type: 'thought',
        content: step.thought,
        timestamp: now,
      })
    }
    // Action step
    const action = step.action as { name?: string; arguments?: Record<string, unknown> } | string | null
    if (action) {
      const toolName = typeof action === 'string' ? action : action?.name || 'unknown'
      const toolArgs = typeof action === 'object' && action !== null ? (action.arguments || {}) : {}
      steps.push({
        type: 'action',
        content: `Call ${toolName}`,
        tool: toolName,
        tool_args: toolArgs as Record<string, unknown>,
        timestamp: now,
      })
    }
    // Observation step
    if (step.observation != null) {
      const obs = typeof step.observation === 'string' ? step.observation : JSON.stringify(step.observation)
      steps.push({
        type: 'observation',
        content: obs.slice(0, 500),
        tool: typeof action === 'string' ? action : (action as { name?: string } | null)?.name,
        timestamp: now,
      })
    }
  }

  return {
    phase: agentName,
    iterations: metrics?.iterations ?? rawTrace.length,
    max_iterations: 10,
    steps,
    success: true,
    total_duration_ms: metrics?.latency_ms ?? 0,
    started_at: now,
    completed_at: now,
  }
}

/**
 * Extract ToolCall[] from backend _react_trace for ToolCallHistory component.
 */
function extractToolCallsFromTrace(
  rawTrace: Array<Record<string, unknown>>
): import('./ToolCallHistory').ToolCall[] {
  const calls: import('./ToolCallHistory').ToolCall[] = []
  for (const step of rawTrace) {
    const action = step.action as { name?: string; arguments?: Record<string, unknown> } | string | null
    if (!action) continue

    const toolName = typeof action === 'string' ? action : action?.name || 'unknown'
    const toolArgs = typeof action === 'object' && action !== null ? (action.arguments || {}) : {}
    const obs = step.observation

    calls.push({
      name: toolName,
      arguments: toolArgs as Record<string, unknown>,
      result: obs,
      status: obs === '[FINAL ANSWER]' || !obs ? 'pending' : 'success',
      timestamp: new Date().toISOString(),
    })
  }
  return calls
}

// Agent-specific output renderers
function AgentOutputRenderer({ stageName, output }: { stageName: string; output?: Record<string, unknown> | null }) {
  if (!output) {
    return <p className="text-sm text-gray-500 text-center py-4">No output data</p>
  }

  // Input Enhancer - show pedagogical context summary
  if (stageName === 'input_enhancer' && output.pedagogical_context) {
    const ctx = output.pedagogical_context as { blooms_level?: string; subject?: string; topic?: string; grade_level?: string; learning_objectives?: string[] }
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          {ctx.blooms_level && (
            <div className="bg-purple-50 p-2 rounded-lg">
              <span className="text-xs text-purple-600 font-medium">Bloom&apos;s Level</span>
              <p className="text-sm font-semibold text-purple-800">{ctx.blooms_level}</p>
            </div>
          )}
          {ctx.subject && (
            <div className="bg-blue-50 p-2 rounded-lg">
              <span className="text-xs text-blue-600 font-medium">Subject</span>
              <p className="text-sm font-semibold text-blue-800">{ctx.subject}</p>
            </div>
          )}
          {ctx.topic && (
            <div className="bg-green-50 p-2 rounded-lg">
              <span className="text-xs text-green-600 font-medium">Topic</span>
              <p className="text-sm font-semibold text-green-800">{ctx.topic}</p>
            </div>
          )}
          {ctx.grade_level && (
            <div className="bg-orange-50 p-2 rounded-lg">
              <span className="text-xs text-orange-600 font-medium">Grade Level</span>
              <p className="text-sm font-semibold text-orange-800">{ctx.grade_level}</p>
            </div>
          )}
        </div>
        {ctx.learning_objectives && ctx.learning_objectives.length > 0 && (
          <div className="bg-gray-50 p-2 rounded-lg">
            <span className="text-xs text-gray-600 font-medium">Learning Objectives</span>
            <ul className="mt-1 space-y-0.5">
              {ctx.learning_objectives.map((obj, i) => (
                <li key={i} className="text-xs text-gray-700">• {obj}</li>
              ))}
            </ul>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Domain Knowledge - show canonical labels
  if (stageName === 'domain_knowledge_retriever' && output.domain_knowledge) {
    const dk = output.domain_knowledge as { canonical_labels?: string[]; sources?: string[]; key_terms?: string[] }
    return (
      <div className="space-y-3">
        {dk.canonical_labels && dk.canonical_labels.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Canonical Labels</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {dk.canonical_labels.map((label, i) => (
                <span key={i} className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}
        {dk.key_terms && dk.key_terms.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Key Terms</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {dk.key_terms.map((term, i) => (
                <span key={i} className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                  {term}
                </span>
              ))}
            </div>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Router - show template selection
  if (stageName === 'router' && output.template_selection) {
    const ts = output.template_selection as { template_type?: string; confidence?: number; reasoning?: string }
    return (
      <div className="space-y-3">
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-green-800">{ts.template_type?.replace(/_/g, ' ')}</span>
            {ts.confidence != null && (
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                ts.confidence >= 0.8 ? 'bg-green-200 text-green-800' :
                ts.confidence >= 0.6 ? 'bg-yellow-200 text-yellow-800' :
                'bg-red-200 text-red-800'
              }`}>
                {(ts.confidence * 100).toFixed(0)}% confidence
              </span>
            )}
          </div>
          {ts.reasoning && (
            <p className="text-xs text-green-700 mt-2">{ts.reasoning}</p>
          )}
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Zone Labeler - show labeled zones
  if (stageName === 'diagram_zone_labeler' && (output.diagram_labels || output.diagram_zones)) {
    const labels = (output.diagram_labels || []) as string[]
    const zones = (output.diagram_zones || []) as Array<{ id?: string; label?: string }>
    const displayLabels = labels.length > 0 ? labels : zones.map(z => z.label).filter(Boolean)

    return (
      <div className="space-y-3">
        <div>
          <span className="text-xs text-gray-500 font-medium">Detected Labels ({displayLabels.length})</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {displayLabels.map((label, i) => (
              <span key={i} className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded">
                {i + 1}. {label}
              </span>
            ))}
          </div>
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Validation results - show pass/fail clearly
  if (stageName.includes('validator') || stageName.includes('verifier')) {
    const vr = output.validation_results as Record<string, { is_valid?: boolean; errors?: string[]; score?: number }> | undefined
    if (vr) {
      const key = Object.keys(vr)[0]
      const result = vr[key]
      if (result) {
        return (
          <div className="space-y-3">
            <div className={`p-3 rounded-lg border ${
              result.is_valid ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center gap-2">
                {result.is_valid ? (
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
                <span className={`font-medium ${result.is_valid ? 'text-green-800' : 'text-red-800'}`}>
                  {result.is_valid ? 'Validation Passed' : 'Validation Failed'}
                </span>
                {result.score != null && (
                  <span className="ml-auto text-xs text-gray-500">
                    Score: {(result.score * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              {result.errors && result.errors.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {result.errors.map((err, i) => (
                    <li key={i} className="text-xs text-red-700">• {err}</li>
                  ))}
                </ul>
              )}
            </div>
            <JsonViewer data={output} title="Full Output" />
          </div>
        )
      }
    }
  }

  // Game Planner - show game plan summary
  if (stageName === 'game_planner' && output.game_plan) {
    const gp = output.game_plan as {
      learning_objectives?: string[];
      game_mechanics?: Array<{ id?: string; type?: string; description?: string; scoring_weight?: number }>;
      scoring_rubric?: { max_score?: number; partial_credit?: boolean };
      estimated_duration_minutes?: number;
      difficulty_progression?: { hints_available?: boolean; max_attempts?: number };
      required_labels?: string[];
      hierarchy_info?: { is_hierarchical?: boolean; recommended_mode?: string };
    }
    return (
      <div className="space-y-3">
        <div className="border rounded-lg p-3 bg-yellow-50">
          <div className="text-sm space-y-2">
            {/* Learning Objectives */}
            {gp.learning_objectives && gp.learning_objectives.length > 0 && (
              <div>
                <strong>Learning Objectives:</strong>
                <ul className="mt-1 list-disc list-inside text-xs text-gray-700">
                  {gp.learning_objectives.slice(0, 3).map((obj, i) => (
                    <li key={i}>{obj}</li>
                  ))}
                  {gp.learning_objectives.length > 3 && (
                    <li className="text-gray-500">+{gp.learning_objectives.length - 3} more...</li>
                  )}
                </ul>
              </div>
            )}
            {/* Game Mechanics */}
            {gp.game_mechanics && gp.game_mechanics.length > 0 && (
              <div>
                <strong>Game Mechanics:</strong>
                <div className="flex flex-wrap gap-1 mt-1">
                  {gp.game_mechanics.map((m, i) => (
                    <span key={i} className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded" title={m.description}>
                      {m.type || m.id}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {/* Scoring */}
            {gp.scoring_rubric && (
              <p><strong>Max Score:</strong> {gp.scoring_rubric.max_score || 100} {gp.scoring_rubric.partial_credit && '(partial credit enabled)'}</p>
            )}
            {/* Duration */}
            {gp.estimated_duration_minutes && (
              <p><strong>Duration:</strong> ~{gp.estimated_duration_minutes} minutes</p>
            )}
            {/* Difficulty */}
            {gp.difficulty_progression && (
              <p><strong>Hints:</strong> {gp.difficulty_progression.hints_available ? 'Available' : 'Disabled'} | <strong>Max Attempts:</strong> {gp.difficulty_progression.max_attempts || 3}</p>
            )}
            {/* INTERACTIVE_DIAGRAM specific */}
            {gp.required_labels && gp.required_labels.length > 0 && (
              <div>
                <strong>Required Labels:</strong>
                <div className="flex flex-wrap gap-1 mt-1">
                  {gp.required_labels.slice(0, 6).map((label, i) => (
                    <span key={i} className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                      {label}
                    </span>
                  ))}
                  {gp.required_labels.length > 6 && (
                    <span className="text-xs text-gray-500">+{gp.required_labels.length - 6} more</span>
                  )}
                </div>
              </div>
            )}
            {/* Hierarchical mode */}
            {gp.hierarchy_info?.is_hierarchical && (
              <p className="text-xs text-purple-600"><strong>Mode:</strong> Hierarchical ({gp.hierarchy_info.recommended_mode})</p>
            )}
          </div>
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Interaction Designer - show interaction patterns and Bloom's alignment
  if (stageName === 'interaction_designer' && output.interaction_design) {
    const design = output.interaction_design as {
      primary_mode?: string;
      secondary_modes?: string[];
      blooms_alignment?: string;
      scoring_strategy?: { type?: string; weights?: Record<string, number> };
      accessibility_features?: string[];
    }
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          {design.primary_mode && (
            <div className="bg-purple-50 p-2 rounded-lg">
              <span className="text-xs text-purple-600 font-medium">Primary Mode</span>
              <p className="text-sm font-semibold text-purple-800">{design.primary_mode.replace(/_/g, ' ')}</p>
            </div>
          )}
          {design.blooms_alignment && (
            <div className="bg-blue-50 p-2 rounded-lg">
              <span className="text-xs text-blue-600 font-medium">Bloom&apos;s Level</span>
              <p className="text-sm font-semibold text-blue-800">{design.blooms_alignment}</p>
            </div>
          )}
        </div>
        {design.secondary_modes && design.secondary_modes.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Secondary Modes</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {design.secondary_modes.map((mode, i) => (
                <span key={i} className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                  {mode.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        )}
        {design.scoring_strategy && (
          <div className="bg-green-50 p-2 rounded-lg">
            <span className="text-xs text-green-600 font-medium">Scoring Strategy</span>
            <p className="text-sm text-green-800">{design.scoring_strategy.type || 'weighted'}</p>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Interaction Validator - show validation results
  if (stageName === 'interaction_validator' && (output.validation_result || output.is_valid !== undefined)) {
    const isValid = output.is_valid as boolean | undefined ?? (output.validation_result as { is_valid?: boolean })?.is_valid
    const score = output.score as number | undefined ?? (output.validation_result as { score?: number })?.score
    const issues = (output.issues || output.validation_issues || (output.validation_result as { issues?: string[] })?.issues || []) as string[]

    return (
      <div className="space-y-3">
        <div className={`p-3 rounded-lg border ${
          isValid ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center gap-2">
            {isValid ? (
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            <span className={`font-medium ${isValid ? 'text-green-800' : 'text-red-800'}`}>
              {isValid ? 'Interaction Design Valid' : 'Validation Failed'}
            </span>
            {score != null && (
              <span className="ml-auto text-xs text-gray-500">
                Score: {(score * 100).toFixed(0)}%
              </span>
            )}
          </div>
          {issues.length > 0 && (
            <ul className="mt-2 space-y-1">
              {issues.slice(0, 5).map((issue, i) => (
                <li key={i} className="text-xs text-red-700">• {issue}</li>
              ))}
              {issues.length > 5 && (
                <li className="text-xs text-gray-500">+{issues.length - 5} more issues</li>
              )}
            </ul>
          )}
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Scene Sequencer - show scene progression planning
  if (stageName === 'scene_sequencer' && (output.scene_sequence || output.scene_breakdown)) {
    const sequence = (output.scene_sequence || output.scene_breakdown) as {
      total_scenes?: number;
      progression_type?: string;
      scenes?: Array<{ scene_id?: string; title?: string; interaction_mode?: string }>;
    }
    const isSingleScene = (sequence.total_scenes || 1) <= 1

    return (
      <div className="space-y-3">
        <div className={`p-3 rounded-lg border ${isSingleScene ? 'bg-gray-50 border-gray-200' : 'bg-indigo-50 border-indigo-200'}`}>
          <div className="flex items-center gap-2">
            <span className={`text-lg ${isSingleScene ? '📄' : '📚'}`}>{isSingleScene ? '📄' : '📚'}</span>
            <div>
              <span className={`font-medium ${isSingleScene ? 'text-gray-800' : 'text-indigo-800'}`}>
                {isSingleScene ? 'Single Scene' : `${sequence.total_scenes} Scenes`}
              </span>
              {sequence.progression_type && (
                <p className="text-xs text-gray-500">
                  Progression: {sequence.progression_type.replace(/_/g, ' ')}
                </p>
              )}
            </div>
          </div>
        </div>
        {sequence.scenes && sequence.scenes.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Scene Breakdown</span>
            <div className="mt-1 space-y-1">
              {sequence.scenes.slice(0, 5).map((scene, i) => (
                <div key={scene.scene_id || i} className="text-xs bg-gray-50 p-2 rounded flex justify-between">
                  <span className="font-medium">{i + 1}. {scene.title || scene.scene_id}</span>
                  {scene.interaction_mode && (
                    <span className="text-gray-500">{scene.interaction_mode.replace(/_/g, ' ')}</span>
                  )}
                </div>
              ))}
              {sequence.scenes.length > 5 && (
                <p className="text-xs text-gray-400">+{sequence.scenes.length - 5} more scenes</p>
              )}
            </div>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Multi-Scene Orchestrator - show per-scene image and zone data
  if (stageName === 'multi_scene_orchestrator' || stageName === 'multi_scene_image_orchestrator') {
    const scenes = (output.processed_scenes || output.scenes || []) as Array<{
      scene_id?: string;
      image_url?: string;
      zones?: Array<{ id?: string; label?: string }>;
      zone_groups?: Array<{ id?: string; label?: string }>;
    }>
    const totalZones = scenes.reduce((sum, s) => sum + (s.zones?.length || 0), 0)

    return (
      <div className="space-y-3">
        <div className="bg-violet-50 p-3 rounded-lg border border-violet-200">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎬</span>
            <div>
              <span className="font-medium text-violet-800">{scenes.length} Scenes Processed</span>
              <p className="text-xs text-violet-600">{totalZones} total zones detected</p>
            </div>
          </div>
        </div>
        {scenes.length > 0 && (
          <div className="space-y-2">
            {scenes.slice(0, 4).map((scene, i) => (
              <div key={scene.scene_id || i} className="border rounded-lg p-2 bg-white">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Scene {i + 1}: {scene.scene_id || `scene_${i + 1}`}</span>
                  <span className="text-xs text-gray-500">
                    {scene.zones?.length || 0} zones
                    {scene.zone_groups && scene.zone_groups.length > 0 && ` • ${scene.zone_groups.length} groups`}
                  </span>
                </div>
                {scene.image_url && (
                  <img
                    src={scene.image_url}
                    alt={`Scene ${i + 1}`}
                    className="mt-2 max-h-24 rounded border object-cover"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                )}
              </div>
            ))}
            {scenes.length > 4 && (
              <p className="text-xs text-gray-400 text-center">+{scenes.length - 4} more scenes</p>
            )}
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Scene Generator - show scene details (legacy)
  if (stageName === 'scene_generator' && output.scene) {
    const scene = output.scene as { title?: string; setting?: string; narrative?: string }
    return (
      <div className="space-y-3">
        <div className="border rounded-lg p-3 bg-pink-50">
          <div className="text-sm space-y-2">
            {scene.title && (
              <p><strong>Scene:</strong> {scene.title}</p>
            )}
            {scene.setting && (
              <p className="text-xs text-gray-600">{scene.setting}</p>
            )}
            {scene.narrative && (
              <p className="text-xs italic text-gray-700 mt-2">&quot;{scene.narrative}&quot;</p>
            )}
          </div>
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Scene Stage 1: Structure - show visual theme, layout, regions
  if (stageName === 'scene_stage1_structure' && output.scene_structure) {
    const structure = output.scene_structure as {
      visual_theme?: string;
      layout_type?: string;
      scene_title?: string;
      minimal_context?: string;
      regions?: Array<{ id: string; purpose: string; position?: string; suggested_size?: string }>;
    }
    return (
      <div className="space-y-3">
        {structure.scene_title && (
          <div className="bg-purple-50 p-2 rounded-lg">
            <span className="text-xs text-purple-600 font-medium">Scene Title</span>
            <p className="text-sm font-semibold text-purple-800">{structure.scene_title}</p>
          </div>
        )}
        {structure.minimal_context && (
          <p className="text-xs italic text-gray-600">&quot;{structure.minimal_context}&quot;</p>
        )}
        <div className="grid grid-cols-2 gap-2">
          {structure.visual_theme && (
            <div className="bg-pink-50 p-2 rounded-lg">
              <span className="text-xs text-pink-600 font-medium">Visual Theme</span>
              <p className="text-sm font-semibold text-pink-800">{structure.visual_theme}</p>
            </div>
          )}
          {structure.layout_type && (
            <div className="bg-blue-50 p-2 rounded-lg">
              <span className="text-xs text-blue-600 font-medium">Layout</span>
              <p className="text-sm font-semibold text-blue-800">{structure.layout_type}</p>
            </div>
          )}
        </div>
        {structure.regions && structure.regions.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Regions ({structure.regions.length})</span>
            <div className="mt-1 space-y-1">
              {structure.regions.slice(0, 5).map((region) => (
                <div key={region.id} className="text-xs bg-gray-50 p-2 rounded">
                  <span className="font-medium">{region.id}</span>: {region.purpose}
                </div>
              ))}
              {structure.regions.length > 5 && (
                <p className="text-xs text-gray-400">+{structure.regions.length - 5} more regions</p>
              )}
            </div>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Scene Stage 2: Assets - show assets and layout spec
  if (stageName === 'scene_stage2_assets' && output.scene_assets) {
    const assets = output.scene_assets as {
      required_assets?: Array<{ id: string; type: string; description?: string; for_region?: string }>;
      layout_specification?: { layout_type?: string; panels?: unknown[] };
    }
    return (
      <div className="space-y-3">
        {assets.required_assets && (
          <div>
            <span className="text-xs text-gray-500 font-medium">
              Assets ({assets.required_assets.length})
            </span>
            <div className="mt-1 space-y-1">
              {assets.required_assets.slice(0, 6).map((asset) => (
                <div key={asset.id} className="text-xs bg-amber-50 p-2 rounded">
                  <span className="font-medium text-amber-700">{asset.id}</span>
                  <span className="text-gray-500 ml-2">({asset.type})</span>
                  {asset.for_region && (
                    <span className="text-gray-400 ml-1">→ {asset.for_region}</span>
                  )}
                </div>
              ))}
              {assets.required_assets.length > 6 && (
                <p className="text-xs text-gray-400">+{assets.required_assets.length - 6} more assets</p>
              )}
            </div>
          </div>
        )}
        {assets.layout_specification && (
          <div className="bg-blue-50 p-2 rounded-lg">
            <span className="text-xs text-blue-600 font-medium">Layout</span>
            <p className="text-sm text-blue-800">{assets.layout_specification.layout_type || 'N/A'}</p>
            {assets.layout_specification.panels && (
              <p className="text-xs text-blue-600">{Array.isArray(assets.layout_specification.panels) ? assets.layout_specification.panels.length : 0} panels</p>
            )}
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Scene Stage 3: Interactions - show animations and state transitions
  if (stageName === 'scene_stage3_interactions' && (output.scene_interactions || output.scene_data)) {
    const interactions = (output.scene_interactions || {}) as {
      asset_interactions?: Array<{ asset_id: string; interaction_type: string }>;
      animation_sequences?: Array<{ id: string; total_duration?: string }>;
      state_transitions?: Array<{ from_state: string; to_state: string }>;
      visual_flow?: Array<{ step: number; description: string }>;
    }
    return (
      <div className="space-y-3">
        {interactions.asset_interactions && interactions.asset_interactions.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">
              Interactions ({interactions.asset_interactions.length})
            </span>
            <div className="mt-1 flex flex-wrap gap-1">
              {interactions.asset_interactions.slice(0, 5).map((interaction, i) => (
                <span key={i} className="text-xs bg-cyan-50 text-cyan-700 px-2 py-1 rounded">
                  {interaction.asset_id}: {interaction.interaction_type}
                </span>
              ))}
              {interactions.asset_interactions.length > 5 && (
                <span className="text-xs text-gray-400">+{interactions.asset_interactions.length - 5} more</span>
              )}
            </div>
          </div>
        )}
        {interactions.animation_sequences && interactions.animation_sequences.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">
              Animations ({interactions.animation_sequences.length})
            </span>
            <div className="mt-1 flex flex-wrap gap-1">
              {interactions.animation_sequences.slice(0, 5).map((anim) => (
                <span key={anim.id} className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded">
                  {anim.id} {anim.total_duration && `(${anim.total_duration})`}
                </span>
              ))}
            </div>
          </div>
        )}
        {interactions.state_transitions && interactions.state_transitions.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">
              State Transitions ({interactions.state_transitions.length})
            </span>
            <div className="mt-1 space-y-1">
              {interactions.state_transitions.slice(0, 3).map((t, i) => (
                <div key={i} className="text-xs bg-indigo-50 text-indigo-700 p-1 rounded">
                  {t.from_state} → {t.to_state}
                </div>
              ))}
            </div>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Diagram Image Retriever - show retrieved image
  if (stageName === 'diagram_image_retriever' && output.diagram_image) {
    const diagramImage = output.diagram_image as { image_url?: string; source_name?: string; title?: string }
    if (diagramImage.image_url) {
      return (
        <div className="space-y-3">
          <div className="border rounded-lg overflow-hidden">
            <img
              src={diagramImage.image_url}
              alt={diagramImage.title || 'Retrieved diagram'}
              className="max-w-full h-auto"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          </div>
          <div className="text-xs text-gray-500 space-y-1">
            {diagramImage.title && <p><strong>Title:</strong> {diagramImage.title}</p>}
            {diagramImage.source_name && <p><strong>Source:</strong> {diagramImage.source_name}</p>}
          </div>
          <JsonViewer data={output} title="Full Output" />
        </div>
      )
    }
  }

  // Diagram Image Segmenter - show segment info
  if (stageName === 'diagram_image_segmenter' && output.diagram_segments) {
    const segments = output.diagram_segments as { method?: string; segments?: unknown[]; image_path?: string }
    const segmentCount = Array.isArray(segments.segments) ? segments.segments.length : 0

    return (
      <div className="space-y-3">
        {/* Method badge */}
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
            Method: {segments.method || 'sam3'}
          </span>
          <span className="text-xs text-gray-500">
            {segmentCount} segments detected
          </span>
        </div>

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Image Label Remover - show cleaned image output
  if (stageName === 'image_label_remover') {
    const cleanedPath = output.cleaned_image_path as string | undefined
    const removedLabels = output.removed_labels as string[] | undefined

    return (
      <div className="space-y-3">
        {/* Status summary */}
        <div className={`p-3 rounded-lg border ${
          removedLabels && removedLabels.length > 0
            ? 'bg-green-50 border-green-200'
            : 'bg-yellow-50 border-yellow-200'
        }`}>
          <div className="flex items-center gap-2">
            <span className="text-lg">
              {removedLabels && removedLabels.length > 0 ? '✅' : '⚠️'}
            </span>
            <span className={`font-medium ${
              removedLabels && removedLabels.length > 0
                ? 'text-green-800'
                : 'text-yellow-800'
            }`}>
              {removedLabels && removedLabels.length > 0
                ? `Removed ${removedLabels.length} label${removedLabels.length > 1 ? 's' : ''}`
                : 'No labels removed (using original image)'}
            </span>
          </div>
        </div>

        {/* Cleaned image path */}
        {cleanedPath && (
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600 border-b">
              Cleaned Image Path
            </div>
            <div className="p-2 bg-white">
              <div className="text-xs text-gray-700 font-mono bg-gray-50 p-2 rounded break-all">
                {cleanedPath}
              </div>
            </div>
          </div>
        )}

        {/* Removed labels */}
        {removedLabels && removedLabels.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Removed Labels</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {removedLabels.map((label, i) => (
                <span key={i} className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded line-through">
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // SAM3 Prompt Generator - show prompts dictionary
  if (stageName === 'sam3_prompt_generator' && output.sam3_prompts) {
    const prompts = output.sam3_prompts as Record<string, string>
    const promptEntries = Object.entries(prompts)

    return (
      <div className="space-y-3">
        <div>
          <span className="text-xs text-gray-500 font-medium">
            Generated Prompts ({promptEntries.length})
          </span>
          <div className="mt-2 space-y-1.5">
            {promptEntries.map(([label, prompt]) => (
              <div key={label} className="flex items-start gap-2 text-xs">
                <span className="bg-lime-100 text-lime-800 px-2 py-0.5 rounded font-medium shrink-0">
                  {label}
                </span>
                <span className="text-gray-600 italic">
                  &quot;{prompt}&quot;
                </span>
              </div>
            ))}
          </div>
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Qwen Annotation Detector - show text labels and leader lines
  if (stageName === 'qwen_annotation_detector') {
    const annotations = (output.annotation_elements || []) as Array<{
      type?: string
      content?: string
      bbox?: number[]
      confidence?: number
      connects_to?: string
      start?: number[]
      end?: number[]
    }>
    const textLabels = (output.text_labels_found || []) as string[]
    const textCount = (output.text_boxes_count || 0) as number
    const lineCount = (output.lines_detected || 0) as number
    const method = (output.detection_method || 'unknown') as string

    return (
      <div className="space-y-3">
        {/* Detection method badge */}
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            method === 'hybrid_geometric' ? 'bg-green-100 text-green-800' :
            method === 'qwen_vl' ? 'bg-blue-100 text-blue-800' :
            'bg-yellow-100 text-yellow-800'
          }`}>
            {method === 'hybrid_geometric' ? '🔍 Hybrid Geometric' :
             method === 'qwen_vl' ? '🤖 Qwen VL' :
             '⚠️ EasyOCR Fallback'}
          </span>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-blue-50 p-2 rounded-lg text-center">
            <span className="text-xs text-blue-600 font-medium">Text Labels</span>
            <p className="text-lg font-bold text-blue-800">{textCount}</p>
            {textCount === lineCount && textCount > 0 && (
              <span className="text-[10px] text-green-600">✅ Match</span>
            )}
          </div>
          <div className="bg-purple-50 p-2 rounded-lg text-center">
            <span className="text-xs text-purple-600 font-medium">Leader Lines</span>
            <p className="text-lg font-bold text-purple-800">{lineCount}</p>
            {lineCount === textCount && lineCount > 0 && (
              <span className="text-[10px] text-green-600">✅ Match</span>
            )}
          </div>
          <div className="bg-gray-50 p-2 rounded-lg text-center">
            <span className="text-xs text-gray-600 font-medium">Total</span>
            <p className="text-lg font-bold text-gray-800">{annotations.length}</p>
          </div>
        </div>

        {/* Text labels found */}
        {textLabels.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Text Labels Found</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {textLabels.map((label, i) => (
                <span key={i} className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Annotation elements preview */}
        {annotations.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">
              Annotation Elements ({annotations.length})
            </span>
            <div className="mt-1 space-y-1 max-h-32 overflow-y-auto">
              {annotations.slice(0, 8).map((ann, i) => (
                <div key={i} className={`text-xs p-1.5 rounded ${
                  ann.type === 'text' ? 'bg-blue-50' : 'bg-purple-50'
                }`}>
                  <span className="font-medium">
                    {ann.type === 'text' ? ann.content : `${ann.connects_to} connector`}
                  </span>
                  <span className="text-gray-500 ml-2">
                    ({ann.type})
                    {ann.confidence && ` ${(ann.confidence * 100).toFixed(0)}%`}
                    {ann.type === 'line' && ann.end && ` → endpoint: [${ann.end.join(', ')}]`}
                  </span>
                </div>
              ))}
              {annotations.length > 8 && (
                <p className="text-xs text-gray-400">+{annotations.length - 8} more</p>
              )}
            </div>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Qwen SAM Zone Detector - show zones with source breakdown
  if (stageName === 'qwen_sam_zone_detector') {
    const zones = (output.diagram_zones || []) as Array<{
      id?: string
      label?: string
      x?: number
      y?: number
      confidence?: number
      source?: string
    }>
    const method = (output.zone_detection_method || 'unknown') as string
    const usedFallback = output._used_fallback as boolean | undefined
    const fallbackReason = output._fallback_reason as string | undefined

    // Count zones by source
    const leaderLineCount = zones.filter(z => z.source?.includes('leader_line')).length
    const qwenCount = zones.filter(z => z.source?.includes('qwen')).length
    const fallbackCount = zones.filter(z => z.source === 'fallback' || z.source === 'grid').length

    return (
      <div className="space-y-3">
        {/* Detection method badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            method.includes('leader_line') ? 'bg-green-100 text-green-800' :
            method.includes('qwen') ? 'bg-blue-100 text-blue-800' :
            method === 'grid_clip' ? 'bg-yellow-100 text-yellow-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {method.includes('leader_line') ? '📍 Leader Lines' :
             method.includes('qwen') ? '🤖 Qwen VL' :
             method === 'grid_clip' ? '📐 Grid CLIP' :
             `❓ ${method}`}
          </span>
          {method === 'leader_line_sam' && (
            <span className="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800">
              + SAM3 Refinement
            </span>
          )}
        </div>

        {/* Source breakdown */}
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-green-50 p-2 rounded-lg text-center">
            <span className="text-xs text-green-600 font-medium">Leader Lines</span>
            <p className="text-lg font-bold text-green-800">{leaderLineCount}</p>
            {leaderLineCount === zones.length && zones.length > 0 && (
              <span className="text-[10px] text-green-600">🟢 100%</span>
            )}
          </div>
          <div className="bg-blue-50 p-2 rounded-lg text-center">
            <span className="text-xs text-blue-600 font-medium">Qwen VL</span>
            <p className="text-lg font-bold text-blue-800">{qwenCount}</p>
          </div>
          <div className="bg-yellow-50 p-2 rounded-lg text-center">
            <span className="text-xs text-yellow-600 font-medium">Fallback</span>
            <p className="text-lg font-bold text-yellow-800">{fallbackCount}</p>
          </div>
        </div>

        {/* Fallback warning */}
        {usedFallback && fallbackReason && (
          <div className="bg-orange-50 border border-orange-200 rounded p-2">
            <span className="text-xs text-orange-700">⚠️ {fallbackReason}</span>
          </div>
        )}

        {/* Zones list */}
        {zones.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">
              Zones Detected ({zones.length})
            </span>
            <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
              {zones.map((zone) => (
                <div key={zone.id} className="text-xs bg-gray-50 p-1.5 rounded flex items-center justify-between">
                  <span>
                    <span className="font-medium text-gray-800">{zone.id}:</span>
                    <span className="text-gray-700 ml-1">{zone.label}</span>
                  </span>
                  <span className="text-gray-500 text-[10px]">
                    @ ({zone.x?.toFixed(1)}%, {zone.y?.toFixed(1)}%)
                    {zone.confidence && ` [${(zone.confidence * 100).toFixed(0)}%]`}
                    {zone.source && ` [${zone.source.replace('_', ' ')}]`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Success banner */}
        {zones.length > 0 && !usedFallback && (
          <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
            <span className="text-xs text-green-700">
              ✅ All {zones.length} zones mapped successfully
            </span>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Image Label Classifier - show classification result
  if (stageName === 'image_label_classifier' && output.image_classification) {
    const classification = output.image_classification as {
      is_labeled?: boolean
      confidence?: number
      text_count?: number
      method?: string
      text_labels_found?: string[]
      reasoning?: string
    }

    return (
      <div className="space-y-3">
        {/* Main classification badge */}
        <div className={`p-3 rounded-lg border ${
          classification.is_labeled
            ? 'bg-orange-50 border-orange-200'
            : 'bg-green-50 border-green-200'
        }`}>
          <div className="flex items-center justify-between">
            <span className={`font-semibold ${
              classification.is_labeled ? 'text-orange-800' : 'text-green-800'
            }`}>
              {classification.is_labeled ? '🏷️ LABELED' : '✨ UNLABELED'}
            </span>
            {classification.confidence != null && (
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                classification.confidence >= 0.8 ? 'bg-green-200 text-green-800' :
                classification.confidence >= 0.6 ? 'bg-yellow-200 text-yellow-800' :
                'bg-red-200 text-red-800'
              }`}>
                {(classification.confidence * 100).toFixed(0)}% confidence
              </span>
            )}
          </div>
          {classification.is_labeled ? (
            <p className="text-xs text-orange-700 mt-2">
              → Will use cleaning pipeline (label remover → annotation detector → zone detector)
            </p>
          ) : (
            <p className="text-xs text-green-700 mt-2">
              → Will use fast path (direct structure locator)
            </p>
          )}
        </div>

        {/* Method and text count */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-blue-50 p-2 rounded-lg">
            <span className="text-xs text-blue-600 font-medium">Method</span>
            <p className="text-sm font-semibold text-blue-800">
              {classification.method === 'easyocr_heuristic' ? 'EasyOCR Heuristic' :
               classification.method === 'qwen_vl' ? 'Qwen VL' :
               classification.method || 'Unknown'}
            </p>
          </div>
          <div className="bg-purple-50 p-2 rounded-lg">
            <span className="text-xs text-purple-600 font-medium">Text Regions</span>
            <p className="text-sm font-semibold text-purple-800">{classification.text_count ?? 0}</p>
          </div>
        </div>

        {/* Text labels found */}
        {classification.text_labels_found && classification.text_labels_found.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Text Labels Found</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {classification.text_labels_found.map((label, i) => (
                <span key={i} className="text-xs bg-orange-100 text-orange-800 px-2 py-0.5 rounded">
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Reasoning */}
        {classification.reasoning && (
          <div className="bg-gray-50 p-2 rounded-lg">
            <span className="text-xs text-gray-500 font-medium">Reasoning</span>
            <p className="text-xs text-gray-700 mt-1">{classification.reasoning}</p>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Direct Structure Locator - show located structures
  if (stageName === 'direct_structure_locator') {
    const zones = (output.diagram_zones || []) as Array<{
      id?: string
      label?: string
      x?: number
      y?: number
      confidence?: number
      source?: string
    }>
    const method = (output.zone_detection_method || 'unknown') as string
    const usedFallback = output._used_fallback as boolean | undefined
    const fallbackReason = output._fallback_reason as string | undefined

    // Count zones by source
    const directVlmCount = zones.filter(z => z.source?.includes('direct_vlm')).length
    const fallbackCount = zones.filter(z => z.source === 'fallback').length

    return (
      <div className="space-y-3">
        {/* Fast path indicator */}
        <div className="bg-green-50 border border-green-200 rounded p-2">
          <span className="text-xs text-green-700">
            ⚡ Fast Path: Direct structure location (skipped cleaning pipeline)
          </span>
        </div>

        {/* Detection method badge */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-2 py-1 rounded text-xs font-medium bg-indigo-100 text-indigo-800">
            📍 Direct VLM Location
          </span>
          {method === 'direct_vlm' && (
            <span className="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800">
              Qwen VL
            </span>
          )}
        </div>

        {/* Source breakdown */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-indigo-50 p-2 rounded-lg text-center">
            <span className="text-xs text-indigo-600 font-medium">Direct VLM</span>
            <p className="text-lg font-bold text-indigo-800">{directVlmCount}</p>
            {directVlmCount === zones.length && zones.length > 0 && (
              <span className="text-[10px] text-indigo-600">🟢 100%</span>
            )}
          </div>
          <div className="bg-yellow-50 p-2 rounded-lg text-center">
            <span className="text-xs text-yellow-600 font-medium">Fallback</span>
            <p className="text-lg font-bold text-yellow-800">{fallbackCount}</p>
          </div>
        </div>

        {/* Fallback warning */}
        {usedFallback && fallbackReason && (
          <div className="bg-orange-50 border border-orange-200 rounded p-2">
            <span className="text-xs text-orange-700">⚠️ {fallbackReason}</span>
          </div>
        )}

        {/* Zones list */}
        {zones.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">
              Structures Located ({zones.length})
            </span>
            <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
              {zones.map((zone) => (
                <div key={zone.id} className="text-xs bg-gray-50 p-1.5 rounded flex items-center justify-between">
                  <span>
                    <span className="font-medium text-gray-800">{zone.id}:</span>
                    <span className="text-gray-700 ml-1">{zone.label}</span>
                  </span>
                  <span className="text-gray-500 text-[10px]">
                    @ ({zone.x?.toFixed(1)}%, {zone.y?.toFixed(1)}%)
                    {zone.confidence && ` [${(zone.confidence * 100).toFixed(0)}%]`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Success banner */}
        {zones.length > 0 && !usedFallback && (
          <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
            <span className="text-xs text-green-700">
              ✅ All {zones.length} structures located directly
            </span>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // SVG Generator - render the SVG inline
  if (stageName === 'diagram_svg_generator' && output.diagram_svg) {
    const svgContent = sanitizeSVG(output.diagram_svg as string)
    return (
      <div className="space-y-3">
        <div className="border rounded-lg p-4 bg-white overflow-auto max-h-64">
          <div
            dangerouslySetInnerHTML={{ __html: svgContent }}
            className="[&>svg]:max-w-full [&>svg]:h-auto"
          />
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Asset Planner - show planned assets with generation methods
  if (stageName === 'asset_planner' && output.planned_assets) {
    const plannedAssets = output.planned_assets as Array<{
      id: string
      type: string
      generation_method: string
      prompt?: string
      url?: string
      priority: number
      placement?: string
      zone_id?: string
    }>

    // Group by generation method
    const methodGroups: Record<string, typeof plannedAssets> = {}
    for (const asset of plannedAssets) {
      const method = asset.generation_method || 'unknown'
      if (!methodGroups[method]) methodGroups[method] = []
      methodGroups[method].push(asset)
    }

    // Method colors
    const methodColors: Record<string, string> = {
      dalle: 'bg-green-100 text-green-800',
      stable_diffusion: 'bg-purple-100 text-purple-800',
      fetch_url: 'bg-blue-100 text-blue-800',
      css_animation: 'bg-orange-100 text-orange-800',
      cached: 'bg-gray-100 text-gray-800',
    }

    return (
      <div className="space-y-3">
        {/* Summary stats */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-indigo-50 p-2 rounded-lg text-center">
            <span className="text-xs text-indigo-600 font-medium">Total Assets</span>
            <p className="text-lg font-bold text-indigo-800">{plannedAssets.length}</p>
          </div>
          <div className="bg-teal-50 p-2 rounded-lg text-center">
            <span className="text-xs text-teal-600 font-medium">Methods</span>
            <p className="text-lg font-bold text-teal-800">{Object.keys(methodGroups).length}</p>
          </div>
        </div>

        {/* Grouped by method */}
        {Object.entries(methodGroups).map(([method, assets]) => (
          <div key={method} className="border rounded-lg p-2">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${methodColors[method] || 'bg-gray-100 text-gray-800'}`}>
                {method.replace(/_/g, ' ').toUpperCase()}
              </span>
              <span className="text-xs text-gray-500">{assets.length} assets</span>
            </div>
            <div className="space-y-1">
              {assets.map((asset) => (
                <div key={asset.id} className="text-xs bg-gray-50 p-1.5 rounded">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-800">{asset.id}</span>
                    <span className="text-gray-500">{asset.type}</span>
                  </div>
                  {asset.prompt && (
                    <p className="text-gray-600 mt-0.5 truncate" title={asset.prompt}>
                      {asset.prompt.length > 50 ? asset.prompt.substring(0, 50) + '...' : asset.prompt}
                    </p>
                  )}
                  {asset.placement && (
                    <span className="text-gray-400 text-[10px]">
                      placement: {asset.placement}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Asset Generator Orchestrator - show generated assets with status
  if (stageName === 'asset_generator_orchestrator' && output.generated_assets) {
    // Normalize: workflow mode returns Dict[str, WorkflowResult], legacy returns Array
    const rawAssets = output.generated_assets
    const generatedAssets: Array<{
      id: string
      type: string
      url?: string
      local_path?: string
      css_content?: string
      success: boolean
      error?: string
      metadata?: Record<string, unknown>
    }> = Array.isArray(rawAssets)
      ? rawAssets
      : Object.entries(rawAssets as Record<string, Record<string, unknown>>).map(([key, val]) => ({
          id: key,
          type: (val.output_type as string) || (val.type as string) || 'workflow',
          url: (val.data as Record<string, unknown>)?.diagram_image as string | undefined,
          local_path: (val.data as Record<string, unknown>)?.diagram_image_local as string | undefined,
          success: val.success !== false,
          error: val.error as string | undefined,
          metadata: val.metadata as Record<string, unknown> | undefined,
        }))

    const successCount = generatedAssets.filter(a => a.success).length
    const failureCount = generatedAssets.filter(a => !a.success).length

    return (
      <div className="space-y-3">
        {/* Summary stats */}
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-indigo-50 p-2 rounded-lg text-center">
            <span className="text-xs text-indigo-600 font-medium">Total</span>
            <p className="text-lg font-bold text-indigo-800">{generatedAssets.length}</p>
          </div>
          <div className="bg-green-50 p-2 rounded-lg text-center">
            <span className="text-xs text-green-600 font-medium">Success</span>
            <p className="text-lg font-bold text-green-800">{successCount}</p>
          </div>
          <div className="bg-red-50 p-2 rounded-lg text-center">
            <span className="text-xs text-red-600 font-medium">Failed</span>
            <p className="text-lg font-bold text-red-800">{failureCount}</p>
          </div>
        </div>

        {/* Success banner or warning */}
        {failureCount === 0 && generatedAssets.length > 0 ? (
          <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
            <span className="text-xs text-green-700">
              ✅ All {generatedAssets.length} assets generated successfully
            </span>
          </div>
        ) : failureCount > 0 ? (
          <div className="bg-orange-50 border border-orange-200 rounded p-2 text-center">
            <span className="text-xs text-orange-700">
              ⚠️ {failureCount} asset(s) failed to generate
            </span>
          </div>
        ) : null}

        {/* Asset list */}
        {generatedAssets.length > 0 && (
          <div className="border rounded-lg divide-y max-h-60 overflow-y-auto">
            {generatedAssets.map((asset) => (
              <div key={asset.id} className="px-3 py-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-800">{asset.id}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500">{asset.type}</span>
                    {asset.success ? (
                      <span className="px-1.5 py-0.5 rounded bg-green-100 text-green-800 text-[10px]">OK</span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-800 text-[10px]">FAILED</span>
                    )}
                  </div>
                </div>
                {asset.url && (
                  <a
                    href={asset.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline truncate block mt-1"
                  >
                    {asset.url.length > 50 ? asset.url.substring(0, 50) + '...' : asset.url}
                  </a>
                )}
                {asset.css_content && (
                  <p className="text-gray-500 mt-1 font-mono truncate">
                    {asset.css_content.substring(0, 40)}...
                  </p>
                )}
                {asset.error && (
                  <p className="text-red-600 mt-1">{asset.error}</p>
                )}
              </div>
            ))}
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Asset Validator - show validation results
  if (stageName === 'asset_validator' && (output.validated_assets !== undefined || output.validation_errors !== undefined)) {
    const validatedAssets = (output.validated_assets || []) as Array<{
      id: string
      type: string
      validation_status: string
      validation_messages?: string[]
    }>
    const validationErrors = (output.validation_errors || []) as string[]
    const assetsValid = output.assets_valid as boolean

    return (
      <div className="space-y-3">
        {/* Summary stats */}
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-indigo-50 p-2 rounded-lg text-center">
            <span className="text-xs text-indigo-600 font-medium">Validated</span>
            <p className="text-lg font-bold text-indigo-800">{validatedAssets.length}</p>
          </div>
          <div className="bg-green-50 p-2 rounded-lg text-center">
            <span className="text-xs text-green-600 font-medium">Status</span>
            <p className="text-lg font-bold text-green-800">
              {assetsValid ? '✓' : '✗'}
            </p>
          </div>
          <div className="bg-red-50 p-2 rounded-lg text-center">
            <span className="text-xs text-red-600 font-medium">Errors</span>
            <p className="text-lg font-bold text-red-800">{validationErrors.length}</p>
          </div>
        </div>

        {/* Validation result banner */}
        {assetsValid ? (
          <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
            <span className="text-xs text-green-700">
              ✅ All assets validated successfully
            </span>
          </div>
        ) : (
          <div className="bg-red-50 border border-red-200 rounded p-2">
            <span className="text-xs text-red-700 font-medium block mb-1">
              ❌ Asset validation failed
            </span>
            {validationErrors.length > 0 && (
              <ul className="text-xs text-red-600 space-y-0.5">
                {validationErrors.slice(0, 5).map((err, i) => (
                  <li key={i}>• {err}</li>
                ))}
                {validationErrors.length > 5 && (
                  <li className="text-gray-500">... and {validationErrors.length - 5} more</li>
                )}
              </ul>
            )}
          </div>
        )}

        {/* Validated assets list */}
        {validatedAssets.length > 0 && (
          <div className="border rounded-lg divide-y max-h-40 overflow-y-auto">
            {validatedAssets.map((asset) => (
              <div key={asset.id} className="px-3 py-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-800">{asset.id}</span>
                  <span className="px-1.5 py-0.5 rounded bg-green-100 text-green-800 text-[10px]">
                    {asset.validation_status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Asset Generator - show asset list with links
  if (stageName === 'asset_generator' && output.asset_urls) {
    const assetUrls = output.asset_urls as Record<string, string>
    return (
      <div className="space-y-3">
        <div className="border rounded-lg divide-y">
          {Object.entries(assetUrls).map(([name, url]) => (
            <div key={name} className="flex items-center gap-3 px-3 py-2 text-xs">
              <span className="font-mono bg-gray-100 px-2 py-0.5 rounded text-gray-700">
                {name}
              </span>
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline truncate flex-1"
              >
                {url.length > 40 ? url.substring(0, 40) + '...' : url}
              </a>
            </div>
          ))}
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Blueprint Generator - show a summary with safe rendering
  if (stageName === 'blueprint_generator' && output.blueprint) {
    const blueprint = output.blueprint as {
      title?: string
      templateType?: string
      labels?: Array<{ id: string; text: string; correctZoneId: string }>
      diagram?: { imageUrl?: string; zones?: Array<{ id: string; label?: string; zone_type?: string; coordinates?: Record<string, unknown> }> }
      tasks?: unknown[]
      narrativeIntro?: string
    }

    const bpImageUrl = blueprint.diagram?.imageUrl
    const bpProxied = bpImageUrl?.startsWith('http')
      ? `/api/generate/proxy/image?url=${encodeURIComponent(bpImageUrl)}`
      : bpImageUrl
    const bpZones = (blueprint.diagram?.zones || []).map(z => ({
      id: z.id,
      label: z.label || z.id,
      zone_type: (z.zone_type || 'bounding_box') as 'circle' | 'ellipse' | 'bounding_box' | 'polygon' | 'path',
      coordinates: z.coordinates || {},
    }))

    return (
      <div className="space-y-3">
        <div className="border rounded-lg p-3 bg-purple-50">
          <div className="text-sm space-y-2">
            {blueprint.title && (
              <p><strong>Title:</strong> {blueprint.title}</p>
            )}
            {blueprint.templateType && (
              <p><strong>Template:</strong> {blueprint.templateType.replace(/_/g, ' ')}</p>
            )}
            {Array.isArray(blueprint.labels) && blueprint.labels.length > 0 && (
              <div>
                <strong>Labels ({blueprint.labels.length}):</strong>
                <div className="flex flex-wrap gap-1 mt-1">
                  {blueprint.labels.map((label, i) => (
                    <span key={typeof label === 'object' && label?.id ? label.id : i} className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded">
                      {typeof label === 'object' ? label.text : String(label)}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {blueprint.diagram?.zones && Array.isArray(blueprint.diagram.zones) && (
              <p><strong>Zones:</strong> {blueprint.diagram.zones.length}</p>
            )}
            {Array.isArray(blueprint.tasks) && (
              <p><strong>Tasks:</strong> {blueprint.tasks.length}</p>
            )}
            {blueprint.narrativeIntro && (
              <div>
                <strong>Narrative:</strong>
                <p className="text-xs text-gray-600 mt-1 italic">
                  &quot;{blueprint.narrativeIntro.length > 100 ? blueprint.narrativeIntro.slice(0, 100) + '...' : blueprint.narrativeIntro}&quot;
                </p>
              </div>
            )}
          </div>
        </div>
        {bpProxied && bpZones.length > 0 && (
          <div className="border rounded-lg overflow-hidden">
            <div className="px-3 py-1.5 bg-purple-50 border-b text-xs font-medium text-purple-700">Blueprint Zone Layout</div>
            <ZoneOverlay imageSrc={bpProxied} zones={bpZones} showLabels={true} />
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Diagram Image Generator - show generated diagram info
  if (stageName === 'diagram_image_generator') {
    const generatedPath = output.generated_diagram_path as string | undefined
    const metadata = output.diagram_metadata as {
      generator?: string
      size?: string
      duration_ms?: number
      subject?: string
      canonical_labels?: string[]
    } | undefined

    return (
      <div className="space-y-3">
        {/* Generator badge */}
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            metadata?.generator?.includes('dall-e') ? 'bg-green-100 text-green-800' :
            metadata?.generator?.includes('gemini') ? 'bg-blue-100 text-blue-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {metadata?.generator?.includes('dall-e') ? '🎨 DALL-E 3' :
             metadata?.generator?.includes('gemini') ? '🖼️ Gemini Imagen' :
             `Generator: ${metadata?.generator || 'Unknown'}`}
          </span>
          {metadata?.size && (
            <span className="text-xs text-gray-500">{metadata.size}</span>
          )}
          {metadata?.duration_ms && (
            <span className="text-xs text-gray-400">{(metadata.duration_ms / 1000).toFixed(1)}s</span>
          )}
        </div>

        {/* Subject and labels */}
        {metadata?.subject && (
          <div className="bg-indigo-50 p-2 rounded-lg">
            <span className="text-xs text-indigo-600 font-medium">Subject</span>
            <p className="text-sm font-semibold text-indigo-800">{metadata.subject}</p>
          </div>
        )}
        {metadata?.canonical_labels && metadata.canonical_labels.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Parts Included</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {metadata.canonical_labels.map((label, i) => (
                <span key={i} className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Generated path */}
        {generatedPath && (
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-green-50 px-3 py-1.5 text-xs font-medium text-green-600 border-b">
              Generated Diagram Path
            </div>
            <div className="p-2 bg-white">
              <div className="text-xs text-gray-700 font-mono bg-gray-50 p-2 rounded break-all">
                {generatedPath}
              </div>
            </div>
          </div>
        )}

        {/* Success banner */}
        {generatedPath && (
          <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
            <span className="text-xs text-green-700">
              ✅ Clean diagram generated successfully
            </span>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Gemini Zone Detector - show zones with hierarchical groups
  if (stageName === 'gemini_zone_detector') {
    const zones = (output.diagram_zones || []) as Array<{
      id?: string
      label?: string
      x?: number
      y?: number
      radius?: number
      confidence?: number
      hint?: string
      difficulty?: number
    }>
    const zoneGroups = (output.zone_groups || []) as Array<{
      id?: string
      name?: string
      zones?: string[]
      revealOrder?: number
    }>
    const method = (output.zone_detection_method || 'gemini_vlm') as string
    const metadata = output.zone_detection_metadata as {
      model?: string
      duration_ms?: number
      parts_not_found?: string[]
    } | undefined

    return (
      <div className="space-y-3">
        {/* Detection method badge */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
            🔍 Gemini Vision
          </span>
          {metadata?.model && (
            <span className="text-xs text-gray-500">{metadata.model}</span>
          )}
          {metadata?.duration_ms && (
            <span className="text-xs text-gray-400">{(metadata.duration_ms / 1000).toFixed(1)}s</span>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-blue-50 p-2 rounded-lg text-center">
            <span className="text-xs text-blue-600 font-medium">Zones Detected</span>
            <p className="text-lg font-bold text-blue-800">{zones.length}</p>
          </div>
          <div className="bg-purple-50 p-2 rounded-lg text-center">
            <span className="text-xs text-purple-600 font-medium">Zone Groups</span>
            <p className="text-lg font-bold text-purple-800">{zoneGroups.length}</p>
          </div>
        </div>

        {/* Zone groups */}
        {zoneGroups.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Hierarchical Groups</span>
            <div className="mt-1 space-y-1.5">
              {zoneGroups.map((group) => (
                <div key={group.id} className="bg-purple-50 p-2 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-purple-800">{group.name}</span>
                    <span className="text-[10px] text-purple-600">
                      Reveal #{group.revealOrder} • {group.zones?.length || 0} zones
                    </span>
                  </div>
                  {group.zones && group.zones.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {group.zones.map((zoneId, i) => (
                        <span key={i} className="text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                          {zoneId}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Zones list */}
        {zones.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">
              Zones Detected ({zones.length})
            </span>
            <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
              {zones.map((zone) => (
                <div key={zone.id} className="text-xs bg-gray-50 p-1.5 rounded flex items-center justify-between">
                  <span>
                    <span className="font-medium text-gray-800">{zone.id}:</span>
                    <span className="text-gray-700 ml-1">{zone.label}</span>
                  </span>
                  <span className="text-gray-500 text-[10px]">
                    @ ({zone.x?.toFixed(1)}%, {zone.y?.toFixed(1)}%)
                    {zone.confidence && ` [${(zone.confidence * 100).toFixed(0)}%]`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Parts not found warning */}
        {metadata?.parts_not_found && metadata.parts_not_found.length > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded p-2">
            <span className="text-xs text-orange-700 font-medium">⚠️ Parts not found:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {metadata.parts_not_found.map((part, i) => (
                <span key={i} className="text-xs bg-orange-100 text-orange-800 px-2 py-0.5 rounded">
                  {part}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ZoneOverlay — render diagram image with detected zones */}
        {(() => {
          const diagramImage = output.diagram_image as string | { image_url?: string; url?: string } | undefined
          const imageUrl = typeof diagramImage === 'string' ? diagramImage : diagramImage?.image_url || diagramImage?.url || output.diagram_image_url as string | undefined
          const proxiedUrl = imageUrl?.startsWith('http')
            ? `/api/generate/proxy/image?url=${encodeURIComponent(imageUrl)}`
            : imageUrl
          const overlayZones = zones.map(z => ({
            id: z.id || '',
            label: z.label || '',
            zone_type: 'circle' as const,
            coordinates: { x: z.x || 0, y: z.y || 0, radius: z.radius || 3 },
          }))
          const overlayGroups = zoneGroups.map(g => ({
            id: g.id || '',
            parent: g.name || '',
            children: g.zones || [],
            relationship_type: 'contains' as const,
          }))

          if (proxiedUrl && overlayZones.length > 0) {
            return (
              <div className="border rounded-lg overflow-hidden">
                <ZoneOverlay
                  imageSrc={proxiedUrl}
                  zones={overlayZones}
                  groups={overlayGroups}
                  showLabels={true}
                />
              </div>
            )
          }
          return null
        })()}

        {/* Success banner */}
        {zones.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
            <span className="text-xs text-green-700">
              ✅ {zones.length} zone{zones.length > 1 ? 's' : ''} detected
              {zoneGroups.length > 0 && ` with ${zoneGroups.length} hierarchical group${zoneGroups.length > 1 ? 's' : ''}`}
            </span>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Diagram Analyzer - show reasoning-based content analysis (Preset 2)
  if (stageName === 'diagram_analyzer' && output.diagram_analysis) {
    const analysis = output.diagram_analysis as {
      content_type?: string
      key_structures?: string[]
      relationships?: { type?: string; details?: string[] }
      recommended_zone_strategy?: string
      multi_scene_recommended?: boolean
      multi_scene_reason?: string
      reasoning?: string
    }

    return (
      <div className="space-y-3">
        {/* Content type badge */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 font-medium">Content Type</span>
            <span className="font-semibold text-indigo-800 px-2 py-0.5 bg-indigo-100 rounded">
              {analysis.content_type || 'Unknown'}
            </span>
          </div>
        </div>

        {/* Key structures */}
        {analysis.key_structures && analysis.key_structures.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Key Structures ({analysis.key_structures.length})</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {analysis.key_structures.slice(0, 8).map((s, i) => (
                <span key={i} className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                  {s}
                </span>
              ))}
              {analysis.key_structures.length > 8 && (
                <span className="text-xs text-gray-400">+{analysis.key_structures.length - 8} more</span>
              )}
            </div>
          </div>
        )}

        {/* Relationships */}
        {analysis.relationships && analysis.relationships.type && analysis.relationships.type !== 'none' && (
          <div className="bg-purple-50 p-2 rounded-lg">
            <span className="text-xs text-purple-600 font-medium">Relationships: </span>
            <span className="text-xs text-purple-800">{analysis.relationships.type}</span>
          </div>
        )}

        {/* Zone strategy */}
        {analysis.recommended_zone_strategy && (
          <div className="bg-cyan-50 p-2 rounded-lg">
            <span className="text-xs text-cyan-600 font-medium">Zone Strategy: </span>
            <span className="text-xs text-cyan-800">{analysis.recommended_zone_strategy}</span>
          </div>
        )}

        {/* Multi-scene recommendation */}
        {analysis.multi_scene_recommended && (
          <div className="bg-amber-50 border border-amber-200 p-2 rounded-lg">
            <span className="text-xs text-amber-700 font-medium">Multi-Scene Recommended</span>
            {analysis.multi_scene_reason && (
              <p className="text-xs text-amber-600 mt-1">{analysis.multi_scene_reason}</p>
            )}
          </div>
        )}

        {/* Reasoning */}
        {analysis.reasoning && (
          <div className="bg-gray-50 p-2 rounded-lg">
            <span className="text-xs text-gray-500 font-medium">Reasoning</span>
            <p className="text-xs text-gray-700 mt-1">{analysis.reasoning}</p>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Game Designer - show full agentic game design (Preset 2)
  if (stageName === 'game_designer' && output.game_design) {
    const design = output.game_design as {
      learning_outcomes?: string[]
      scenes?: Array<{
        scene?: number
        title?: string
        pattern?: string
        purpose?: string
        scoring_weight?: number
      }>
      scene_structure?: string
      reasoning?: string
    }

    return (
      <div className="space-y-3">
        {/* Learning outcomes */}
        {design.learning_outcomes && design.learning_outcomes.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Learning Outcomes</span>
            <ul className="mt-1 space-y-1">
              {design.learning_outcomes.map((outcome, i) => (
                <li key={i} className="text-xs text-gray-700 bg-green-50 p-1.5 rounded">
                  {outcome}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Scene structure badge */}
        {design.scene_structure && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 font-medium">Structure:</span>
            <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-full">
              {design.scene_structure}
            </span>
          </div>
        )}

        {/* Scenes */}
        {design.scenes && design.scenes.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Scenes ({design.scenes.length})</span>
            <div className="mt-2 space-y-2">
              {design.scenes.map((scene, i) => (
                <div key={i} className="bg-blue-50 border border-blue-200 p-2 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-blue-800">
                      Scene {scene.scene}: {scene.title}
                    </span>
                    <span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded">
                      {scene.pattern}
                    </span>
                  </div>
                  {scene.purpose && (
                    <p className="text-xs text-blue-700 mt-1">{scene.purpose}</p>
                  )}
                  {scene.scoring_weight != null && (
                    <p className="text-xs text-blue-600 mt-1">
                      Weight: {(scene.scoring_weight * 100).toFixed(0)}%
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Design reasoning */}
        {design.reasoning && (
          <div className="bg-gray-50 p-2 rounded-lg">
            <span className="text-xs text-gray-500 font-medium">Design Reasoning</span>
            <p className="text-xs text-gray-700 mt-1">{design.reasoning}</p>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Game Designer v3 - show structured game design with scenes, labels, mechanics
  if (stageName === 'game_designer_v3' && output.game_design_v3) {
    const design = output.game_design_v3 as {
      title?: string
      pedagogical_reasoning?: string
      learning_objectives?: string[]
      labels?: {
        zone_labels?: string[]
        distractor_labels?: Array<{ text?: string; explanation?: string }>
        group_only_labels?: string[]
        hierarchy?: { enabled?: boolean; strategy?: string; groups?: Array<{ parent?: string; children?: string[] }> }
      }
      scenes?: Array<{
        scene_number?: number
        title?: string
        mechanics?: Array<{ type?: string; zone_labels_used?: string[] }>
      }>
      theme?: { visual_tone?: string; narrative_frame?: string }
      estimated_duration_minutes?: number
    }
    const reactTrace = output._react_trace as Array<Record<string, unknown>> | undefined
    const llmMetrics = output._llm_metrics as { iterations?: number; tool_calls?: number; latency_ms?: number } | undefined

    return (
      <div className="space-y-3">
        {/* Title + metrics bar */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-indigo-800">{design.title || 'Game Design'}</span>
            {llmMetrics && (
              <span className="text-xs text-indigo-600">
                {llmMetrics.iterations} iterations, {llmMetrics.tool_calls} tool calls
                {llmMetrics.latency_ms && ` (${(llmMetrics.latency_ms / 1000).toFixed(1)}s)`}
              </span>
            )}
          </div>
          {design.pedagogical_reasoning && (
            <p className="text-xs text-indigo-700">{design.pedagogical_reasoning}</p>
          )}
        </div>

        {/* Labels summary */}
        {design.labels && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <span className="text-xs text-green-700 font-medium">Labels</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {design.labels.zone_labels?.map((l, i) => (
                <span key={i} className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">{l}</span>
              ))}
              {design.labels.distractor_labels?.map((d, i) => (
                <span key={`d-${i}`} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full" title={d.explanation}>{d.text} (distractor)</span>
              ))}
            </div>
            {design.labels.hierarchy?.enabled && (
              <p className="text-xs text-green-600 mt-1">Hierarchy: {design.labels.hierarchy.strategy}</p>
            )}
          </div>
        )}

        {/* Scenes */}
        {design.scenes && design.scenes.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Scenes ({design.scenes.length})</span>
            <div className="mt-1 space-y-2">
              {design.scenes.map((scene, i) => (
                <div key={i} className="bg-blue-50 border border-blue-200 p-2 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-blue-800">
                      Scene {scene.scene_number}: {scene.title}
                    </span>
                    <div className="flex gap-1">
                      {scene.mechanics?.map((m, j) => (
                        <span key={j} className="text-xs bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded">{m.type}</span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ReAct Trace Viewer */}
        {reactTrace && reactTrace.length > 0 && (
          <ReActTraceViewer
            trace={convertBackendTrace(reactTrace, 'game_designer_v3', llmMetrics)}
            title="Design Reasoning Trace"
            defaultExpanded={false}
          />
        )}

        {/* Tool Call History */}
        {reactTrace && reactTrace.length > 0 && (
          <ToolCallHistory toolCalls={extractToolCallsFromTrace(reactTrace)} />
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Asset Orchestrator v3 - show asset generation summary
  if (stageName === 'asset_orchestrator_v3' && output.generated_assets_v3) {
    const assets = output.generated_assets_v3 as Record<string, {
      asset_id?: string
      success?: boolean
      asset_type?: string
      worker?: string
      latency_ms?: number
      cost_usd?: number
      error?: string
    }>
    const summary = output._asset_generation_summary as {
      total?: number; succeeded?: number; failed?: number; cost_usd?: number; latency_ms?: number
    } | undefined

    return (
      <div className="space-y-3">
        {summary && (
          <div className="bg-teal-50 border border-teal-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-teal-800">Asset Generation</span>
              <span className="text-xs text-teal-600">
                {summary.succeeded}/{summary.total} succeeded
                {summary.cost_usd != null && ` ($${summary.cost_usd.toFixed(4)})`}
                {summary.latency_ms != null && ` (${(summary.latency_ms / 1000).toFixed(1)}s)`}
              </span>
            </div>
          </div>
        )}
        <div className="space-y-1">
          {Object.entries(assets).map(([id, asset]) => (
            <div key={id} className={`flex items-center justify-between p-2 rounded border ${
              asset.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center gap-2">
                <span className="text-xs">{asset.success ? '✓' : '✗'}</span>
                <span className="text-xs font-mono font-medium">{id}</span>
                <span className="text-xs text-gray-500">{asset.worker}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs bg-gray-100 px-1.5 rounded">{asset.asset_type}</span>
                {asset.latency_ms != null && (
                  <span className="text-xs text-gray-500">{asset.latency_ms.toFixed(0)}ms</span>
                )}
              </div>
            </div>
          ))}
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Blueprint Assembler v3 - show assembled blueprint summary
  if (stageName === 'blueprint_assembler_v3' && output.blueprint) {
    const bp = output.blueprint as {
      templateType?: string
      title?: string
      total_max_score?: number
      diagram?: { imageUrl?: string; zones?: Array<{ id: string; label?: string; zone_type?: string; coordinates?: Record<string, unknown> }> }
      scenes?: Array<{
        scene_id?: string
        title?: string
        zones?: Array<unknown>
        labels?: Array<unknown>
        mechanics?: Array<{ mechanic_type?: string }>
      }>
      _validation_issues?: string[]
    }
    const assemblerImageUrl = bp.diagram?.imageUrl
    const assemblerProxied = assemblerImageUrl?.startsWith('http')
      ? `/api/generate/proxy/image?url=${encodeURIComponent(assemblerImageUrl)}`
      : assemblerImageUrl
    const assemblerZones = (bp.diagram?.zones || []).map(z => ({
      id: z.id,
      label: z.label || z.id,
      zone_type: (z.zone_type || 'bounding_box') as 'circle' | 'ellipse' | 'bounding_box' | 'polygon' | 'path',
      coordinates: z.coordinates || {},
    }))

    return (
      <div className="space-y-3">
        <div className={`rounded-lg p-3 border ${
          bp._validation_issues ? 'bg-yellow-50 border-yellow-200' : 'bg-emerald-50 border-emerald-200'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-800">{bp.title || 'Blueprint'}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              bp._validation_issues ? 'bg-yellow-100 text-yellow-800' : 'bg-emerald-100 text-emerald-800'
            }`}>
              {bp._validation_issues ? 'Issues' : 'Valid'}
            </span>
          </div>
          <div className="flex gap-3 mt-1 text-xs text-gray-600">
            <span>{bp.templateType}</span>
            <span>Max Score: {bp.total_max_score}</span>
            <span>{bp.scenes?.length || 0} scenes</span>
          </div>
        </div>

        {bp.scenes && bp.scenes.length > 0 && (
          <div className="space-y-2">
            {bp.scenes.map((scene, i) => (
              <div key={i} className="bg-gray-50 border border-gray-200 p-2 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-800">{scene.title}</span>
                  <div className="flex gap-2 text-xs text-gray-500">
                    <span>{(scene.zones as Array<unknown>)?.length || 0} zones</span>
                    <span>{(scene.labels as Array<unknown>)?.length || 0} labels</span>
                    {scene.mechanics?.map((m, j) => (
                      <span key={j} className="bg-purple-100 text-purple-700 px-1.5 rounded">{m.mechanic_type}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {assemblerProxied && assemblerZones.length > 0 && (
          <div className="border rounded-lg overflow-hidden">
            <div className="px-3 py-1.5 bg-emerald-50 border-b text-xs font-medium text-emerald-700">Assembled Blueprint Layout</div>
            <ZoneOverlay imageSrc={assemblerProxied} zones={assemblerZones} showLabels={true} />
          </div>
        )}

        {bp._validation_issues && bp._validation_issues.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-2">
            <span className="text-xs font-medium text-yellow-800">Validation Issues</span>
            <ul className="mt-1">
              {bp._validation_issues.map((issue, i) => (
                <li key={i} className="text-xs text-yellow-700">• {issue}</li>
              ))}
            </ul>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Design Validator - show validation results
  if (stageName === 'design_validator' && output.design_validation_v3) {
    const validation = output.design_validation_v3 as {
      valid?: boolean
      score?: number
      errors?: string[]
      warnings?: string[]
    }

    return (
      <div className="space-y-3">
        <div className={`rounded-lg p-3 border ${
          validation.valid ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{validation.valid ? 'Design Valid' : 'Design Invalid'}</span>
            {validation.score != null && (
              <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">Score: {(validation.score * 100).toFixed(0)}%</span>
            )}
          </div>
        </div>
        {validation.errors && validation.errors.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded p-2">
            <span className="text-xs font-medium text-red-800">Errors</span>
            <ul className="mt-1">
              {validation.errors.map((e, i) => <li key={i} className="text-xs text-red-700">• {e}</li>)}
            </ul>
          </div>
        )}
        {validation.warnings && validation.warnings.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
            <span className="text-xs font-medium text-yellow-800">Warnings</span>
            <ul className="mt-1">
              {validation.warnings.map((w, i) => <li key={i} className="text-xs text-yellow-700">• {w}</li>)}
            </ul>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Scene Architect v3 - show per-scene zone/mechanic specs
  if (stageName === 'scene_architect_v3' && output.scene_specs_v3) {
    const specs = output.scene_specs_v3 as Array<{
      scene_number?: number
      title?: string
      image_description?: string
      zones?: Array<{ label?: string; position_hint?: string }>
      mechanic_configs?: Array<{ type?: string }>
    }>

    return (
      <div className="space-y-3">
        <div className="text-xs text-gray-500">{specs.length} scene spec(s)</div>
        {specs.map((spec, i) => (
          <div key={i} className="bg-blue-50 border border-blue-200 rounded-lg p-2 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-blue-800">Scene {spec.scene_number}: {spec.title}</span>
              <div className="flex gap-1">
                {spec.mechanic_configs?.map((m, j) => (
                  <span key={j} className="text-xs bg-blue-100 text-blue-700 px-1.5 rounded">{m.type}</span>
                ))}
              </div>
            </div>
            <div className="text-xs text-gray-600">{spec.zones?.length || 0} zones</div>
            {spec.image_description && (
              <div className="text-xs text-gray-500 truncate">Image: {spec.image_description}</div>
            )}
          </div>
        ))}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Scene Validator - show scene validation results
  if (stageName === 'scene_validator' && output.scene_validation_v3) {
    const validation = output.scene_validation_v3 as {
      passed?: boolean
      score?: number
      issues?: string[]
    }

    return (
      <div className="space-y-3">
        <div className={`rounded-lg p-3 border ${
          validation.passed ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{validation.passed ? 'Scene Specs Valid' : 'Scene Specs Invalid'}</span>
            {validation.score != null && (
              <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">Score: {(validation.score * 100).toFixed(0)}%</span>
            )}
          </div>
        </div>
        {validation.issues && validation.issues.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
            <span className="text-xs font-medium text-yellow-800">Issues ({validation.issues.length})</span>
            <ul className="mt-1">
              {validation.issues.map((issue, i) => <li key={i} className="text-xs text-yellow-700">• {issue}</li>)}
            </ul>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Interaction Designer v3 - show per-scene interaction specs
  if (stageName === 'interaction_designer_v3' && output.interaction_specs_v3) {
    const specs = output.interaction_specs_v3 as Array<{
      scene_number?: number
      scoring?: Array<{ mechanic_type?: string; max_score?: number }>
      feedback?: Array<{ mechanic_type?: string; misconception_feedback?: Array<unknown> }>
      mode_transitions?: Array<{ from_mechanic?: string; to_mechanic?: string }>
    }>

    return (
      <div className="space-y-3">
        <div className="text-xs text-gray-500">{specs.length} interaction spec(s)</div>
        {specs.map((spec, i) => {
          const totalScore = spec.scoring?.reduce((sum, s) => sum + (s.max_score || 0), 0) || 0
          const misconceptions = spec.feedback?.reduce((sum, f) => sum + ((f.misconception_feedback as Array<unknown>)?.length || 0), 0) || 0
          return (
            <div key={i} className="bg-purple-50 border border-purple-200 rounded-lg p-2 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-purple-800">Scene {spec.scene_number}</span>
                <span className="text-xs text-gray-600">Max: {totalScore} pts</span>
              </div>
              <div className="flex gap-2 text-xs text-gray-600">
                <span>{spec.scoring?.length || 0} mechanics scored</span>
                <span>{misconceptions} misconceptions</span>
                <span>{spec.mode_transitions?.length || 0} transitions</span>
              </div>
            </div>
          )
        })}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Interaction Validator - show interaction validation results
  if (stageName === 'interaction_validator' && output.interaction_validation_v3) {
    const validation = output.interaction_validation_v3 as {
      passed?: boolean
      score?: number
      issues?: string[]
    }

    return (
      <div className="space-y-3">
        <div className={`rounded-lg p-3 border ${
          validation.passed ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{validation.passed ? 'Interactions Valid' : 'Interactions Invalid'}</span>
            {validation.score != null && (
              <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">Score: {(validation.score * 100).toFixed(0)}%</span>
            )}
          </div>
        </div>
        {validation.issues && validation.issues.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
            <span className="text-xs font-medium text-yellow-800">Issues ({validation.issues.length})</span>
            <ul className="mt-1">
              {validation.issues.map((issue, i) => <li key={i} className="text-xs text-yellow-700">• {issue}</li>)}
            </ul>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Asset Generator v3 - show per-scene asset generation results
  if (stageName === 'asset_generator_v3' && output.generated_assets_v3) {
    const assets = output.generated_assets_v3 as {
      scenes?: Record<string, {
        diagram_image_url?: string
        diagram_image_path?: string
        zones?: Array<{ label?: string; confidence?: number }>
        zone_detection_method?: string
      }>
    }
    const sceneEntries = Object.entries(assets.scenes || {})

    return (
      <div className="space-y-3">
        <div className="text-xs text-gray-500">{sceneEntries.length} scene(s) with assets</div>
        {sceneEntries.map(([sceneNum, scene]) => (
          <div key={sceneNum} className="bg-teal-50 border border-teal-200 rounded-lg p-2 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-teal-800">Scene {sceneNum}</span>
              <span className="text-xs text-gray-500">{scene.zone_detection_method}</span>
            </div>
            <div className="flex gap-2 text-xs text-gray-600">
              <span>{scene.zones?.length || 0} zones detected</span>
              {scene.diagram_image_url && <span className="text-teal-600">Has image</span>}
            </div>
            {scene.zones && scene.zones.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {scene.zones.slice(0, 8).map((z, j) => (
                  <span key={j} className="text-xs bg-teal-100 text-teal-700 px-1.5 rounded">
                    {z.label} {z.confidence ? `(${(z.confidence * 100).toFixed(0)}%)` : ''}
                  </span>
                ))}
                {scene.zones.length > 8 && (
                  <span className="text-xs text-gray-400">+{scene.zones.length - 8} more</span>
                )}
              </div>
            )}
          </div>
        ))}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Multi-Scene Image Orchestrator - show per-scene diagram generation
  if (stageName === 'multi_scene_image_orchestrator') {
    const sceneDiagrams = output.scene_diagrams as Record<number, {
      scene_number?: number
      generated_path?: string
      scope?: string
      focus_labels?: string[]
    }> | undefined
    const sceneZones = output.scene_zones as Record<number, Array<{
      id?: string
      label?: string
      x?: number
      y?: number
    }>> | undefined
    const sceneLabels = output.scene_labels as Record<number, Array<{
      id?: string
      text?: string
    }>> | undefined

    const sceneNumbers = sceneDiagrams ? Object.keys(sceneDiagrams).map(Number).sort((a, b) => a - b) : []

    return (
      <div className="space-y-3">
        {/* Summary */}
        <div className="bg-cyan-50 p-2 rounded-lg">
          <span className="text-xs text-cyan-800 font-medium">
            Generated {sceneNumbers.length} scene diagrams
          </span>
        </div>

        {/* Per-scene details */}
        {sceneNumbers.map(sceneNum => {
          const diagram = sceneDiagrams?.[sceneNum]
          const zones = sceneZones?.[sceneNum] || []
          const labels = sceneLabels?.[sceneNum] || []

          return (
            <div key={sceneNum} className="bg-blue-50 border border-blue-200 p-2 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-blue-800">
                  Scene {sceneNum}: {diagram?.scope || 'No scope'}
                </span>
                <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                  {zones.length} zones
                </span>
              </div>
              {diagram?.focus_labels && diagram.focus_labels.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {diagram.focus_labels.slice(0, 5).map((label, i) => (
                    <span key={i} className="text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">
                      {label}
                    </span>
                  ))}
                  {diagram.focus_labels.length > 5 && (
                    <span className="text-xs text-gray-500">+{diagram.focus_labels.length - 5} more</span>
                  )}
                </div>
              )}
              <div className="mt-1 text-xs text-blue-600">
                Labels: {labels.length} | Path: {diagram?.generated_path?.slice(-30) || 'N/A'}
              </div>
            </div>
          )
        })}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // === ReAct Agent Output Renderers ===

  // Research & Routing Agent - shows research findings and routing decision
  if (stageName === 'research_routing_agent') {
    const domainKnowledge = output.domain_knowledge as {
      canonical_labels?: string[]
      definitions?: Record<string, string>
      related_terms?: string[]
    } | undefined
    const templateSelection = output.template_selection as {
      template?: string
      confidence?: number
    } | undefined
    const labels = (output.diagram_labels || []) as string[]
    const zones = (output.diagram_zones || []) as Array<{ id?: string; label?: string }>
    const imageUrl = output.diagram_image_url as string | undefined
    const blooms = output.blooms_level as string | undefined
    const subject = output.subject as string | undefined

    return (
      <div className="space-y-3">
        {/* Pedagogical context */}
        {(blooms || subject) && (
          <div className="grid grid-cols-2 gap-2">
            {blooms && (
              <div className="bg-purple-50 p-2 rounded-lg">
                <span className="text-xs text-purple-600 font-medium">Bloom&apos;s Level</span>
                <p className="text-sm font-semibold text-purple-800">{blooms}</p>
              </div>
            )}
            {subject && (
              <div className="bg-blue-50 p-2 rounded-lg">
                <span className="text-xs text-blue-600 font-medium">Subject</span>
                <p className="text-sm font-semibold text-blue-800">{subject}</p>
              </div>
            )}
          </div>
        )}

        {/* Template selection */}
        {templateSelection?.template && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-green-800">{templateSelection.template.replace(/_/g, ' ')}</span>
              {templateSelection.confidence != null && (
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  templateSelection.confidence >= 0.8 ? 'bg-green-200 text-green-800' :
                  templateSelection.confidence >= 0.6 ? 'bg-yellow-200 text-yellow-800' :
                  'bg-red-200 text-red-800'
                }`}>
                  {(templateSelection.confidence * 100).toFixed(0)}% confidence
                </span>
              )}
            </div>
          </div>
        )}

        {/* Canonical labels */}
        {domainKnowledge?.canonical_labels && domainKnowledge.canonical_labels.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Canonical Labels</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {domainKnowledge.canonical_labels.map((label, i) => (
                <span key={i} className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Detected zones */}
        {zones.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Detected Zones ({zones.length})</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {zones.slice(0, 8).map((zone, i) => (
                <span key={i} className="text-xs bg-orange-100 text-orange-800 px-2 py-0.5 rounded">
                  {zone.label || labels[i] || `Zone ${i + 1}`}
                </span>
              ))}
              {zones.length > 8 && (
                <span className="text-xs text-gray-400">+{zones.length - 8} more</span>
              )}
            </div>
          </div>
        )}

        {/* Image URL */}
        {imageUrl && (
          <div className="bg-gray-50 p-2 rounded-lg">
            <span className="text-xs text-gray-500 font-medium">Diagram Image</span>
            <p className="text-xs text-gray-700 mt-1 truncate">{imageUrl}</p>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Game Design Agent - shows game plan and interactions
  if (stageName === 'game_design_agent') {
    const gamePlan = output.game_plan as {
      mechanics?: { core_mechanic?: string; interaction_type?: string }
      scoring_rules?: Record<string, unknown>
    } | undefined
    const sceneStructure = output.scene_structure as {
      layout_type?: string
      regions?: Array<{ id?: string; type?: string }>
    } | undefined
    const populatedScene = output.populated_scene as {
      elements?: Array<{ id?: string; type?: string }>
    } | undefined
    const interactions = (output.interactions || []) as Array<{
      source?: string
      target?: string
    }>
    const validation = output.design_validation as {
      mechanics_valid?: boolean
      layout_valid?: boolean
      interactions_valid?: boolean
      overall_score?: number
    } | undefined

    return (
      <div className="space-y-3">
        {/* Game mechanics */}
        {gamePlan?.mechanics && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <span className="text-xs text-yellow-600 font-medium">Game Mechanics</span>
            <div className="mt-1 flex flex-wrap gap-2">
              {gamePlan.mechanics.core_mechanic && (
                <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                  {gamePlan.mechanics.core_mechanic}
                </span>
              )}
              {gamePlan.mechanics.interaction_type && (
                <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                  {gamePlan.mechanics.interaction_type}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Scene structure */}
        {sceneStructure && (
          <div className="bg-blue-50 p-2 rounded-lg">
            <span className="text-xs text-blue-600 font-medium">Scene Structure</span>
            <p className="text-sm text-blue-800 mt-1">
              Layout: {sceneStructure.layout_type || 'default'}
              {sceneStructure.regions && ` • ${sceneStructure.regions.length} regions`}
            </p>
          </div>
        )}

        {/* Populated elements */}
        {populatedScene?.elements && populatedScene.elements.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Elements ({populatedScene.elements.length})</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {populatedScene.elements.slice(0, 6).map((el, i) => (
                <span key={i} className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                  {el.type || el.id}
                </span>
              ))}
              {populatedScene.elements.length > 6 && (
                <span className="text-xs text-gray-400">+{populatedScene.elements.length - 6} more</span>
              )}
            </div>
          </div>
        )}

        {/* Interactions count */}
        {interactions.length > 0 && (
          <div className="bg-purple-50 p-2 rounded-lg">
            <span className="text-xs text-purple-600 font-medium">Interactions</span>
            <p className="text-sm text-purple-800 mt-1">{interactions.length} interaction mappings defined</p>
          </div>
        )}

        {/* Validation results */}
        {validation && (
          <div className={`p-2 rounded-lg border ${
            validation.overall_score && validation.overall_score >= 0.8
              ? 'bg-green-50 border-green-200'
              : 'bg-yellow-50 border-yellow-200'
          }`}>
            <span className="text-xs font-medium">Design Validation</span>
            <div className="mt-1 flex flex-wrap gap-2 text-xs">
              <span className={validation.mechanics_valid ? 'text-green-700' : 'text-red-700'}>
                Mechanics: {validation.mechanics_valid ? '✓' : '✗'}
              </span>
              <span className={validation.layout_valid ? 'text-green-700' : 'text-red-700'}>
                Layout: {validation.layout_valid ? '✓' : '✗'}
              </span>
              <span className={validation.interactions_valid ? 'text-green-700' : 'text-red-700'}>
                Interactions: {validation.interactions_valid ? '✓' : '✗'}
              </span>
              {validation.overall_score != null && (
                <span className="ml-auto">Score: {(validation.overall_score * 100).toFixed(0)}%</span>
              )}
            </div>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Blueprint & Asset Agent - shows blueprint and asset generation results
  if (stageName === 'blueprint_asset_agent') {
    const blueprint = output.blueprint as {
      template?: string
      game_title?: string
      scenes?: Array<{ scene_id?: string }>
    } | undefined
    const blueprintValid = output.blueprint_valid as boolean | undefined
    const generatedAssets = (output.generated_assets || []) as Array<{ name?: string; url?: string }>
    const failedAssets = (output.failed_assets || []) as Array<{ name?: string; error?: string }>
    const diagramSpec = output.diagram_spec as {
      drop_zones?: Array<{ id?: string }>
      label_chips?: Array<{ text?: string }>
    } | undefined
    const svgContent = (output.final_svg || output.diagram_svg) as string | undefined
    const summary = output.production_summary as {
      validation_attempts?: number
      assets_generated?: number
      svg_size_bytes?: number
    } | undefined

    return (
      <div className="space-y-3">
        {/* Blueprint summary */}
        {blueprint && (
          <div className={`p-3 rounded-lg border ${
            blueprintValid ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">
                {blueprint.game_title || blueprint.template || 'Game Blueprint'}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded ${
                blueprintValid ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
              }`}>
                {blueprintValid ? 'Valid' : 'Pending'}
              </span>
            </div>
            {blueprint.scenes && (
              <p className="text-xs text-gray-600 mt-1">{blueprint.scenes.length} scene(s)</p>
            )}
          </div>
        )}

        {/* Diagram spec */}
        {diagramSpec && (
          <div className="bg-blue-50 p-2 rounded-lg">
            <span className="text-xs text-blue-600 font-medium">Diagram Spec</span>
            <p className="text-xs text-blue-800 mt-1">
              {diagramSpec.drop_zones?.length || 0} drop zones • {diagramSpec.label_chips?.length || 0} label chips
            </p>
          </div>
        )}

        {/* Asset generation results */}
        {(generatedAssets.length > 0 || failedAssets.length > 0) && (
          <div className="space-y-2">
            <span className="text-xs text-gray-500 font-medium">Assets</span>
            <div className="flex gap-2">
              <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                {generatedAssets.length} generated
              </span>
              {failedAssets.length > 0 && (
                <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
                  {failedAssets.length} failed
                </span>
              )}
            </div>
          </div>
        )}

        {/* SVG output indicator */}
        {svgContent && (
          <div className="bg-indigo-50 p-2 rounded-lg">
            <span className="text-xs text-indigo-600 font-medium">SVG Output</span>
            <p className="text-xs text-indigo-800 mt-1">
              {summary?.svg_size_bytes
                ? `${(summary.svg_size_bytes / 1024).toFixed(1)} KB`
                : 'Generated'}
            </p>
          </div>
        )}

        {/* Production summary */}
        {summary && (
          <div className="bg-gray-50 p-2 rounded-lg text-xs text-gray-600">
            <span className="font-medium">Production Summary</span>
            <div className="mt-1 flex flex-wrap gap-2">
              {summary.validation_attempts && (
                <span>Validation attempts: {summary.validation_attempts}</span>
              )}
              {summary.assets_generated != null && (
                <span>Assets: {summary.assets_generated}</span>
              )}
            </div>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Tool Calls Viewer - for agentic sequential agents
  if (output._tool_metrics) {
    const toolMetrics = output._tool_metrics as {
      tool_calls?: Array<{
        name?: string
        arguments_preview?: string
        result_preview?: string
        status?: string
        latency_ms?: number
      }>
      total_tool_calls?: number
      successful_calls?: number
      failed_calls?: number
      total_tool_latency_ms?: number
    }

    return (
      <div className="space-y-3">
        {/* Tool metrics summary */}
        <div className="bg-violet-50 border border-violet-200 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-violet-800">Tool Calls</span>
            <span className="text-xs text-violet-600">
              {toolMetrics.successful_calls}/{toolMetrics.total_tool_calls} successful
              {toolMetrics.total_tool_latency_ms && ` • ${(toolMetrics.total_tool_latency_ms / 1000).toFixed(2)}s total`}
            </span>
          </div>

          {/* Individual tool calls */}
          {toolMetrics.tool_calls && toolMetrics.tool_calls.length > 0 && (
            <div className="space-y-2 mt-3">
              {toolMetrics.tool_calls.map((call, i) => (
                <div
                  key={i}
                  className={`p-2 rounded border ${
                    call.status === 'success'
                      ? 'bg-green-50 border-green-200'
                      : call.status === 'error'
                        ? 'bg-red-50 border-red-200'
                        : 'bg-yellow-50 border-yellow-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-medium text-gray-800">
                      {call.name}
                    </span>
                    <div className="flex items-center gap-2">
                      {call.latency_ms && (
                        <span className="text-xs text-gray-500">{call.latency_ms}ms</span>
                      )}
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        call.status === 'success'
                          ? 'bg-green-100 text-green-700'
                          : call.status === 'error'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {call.status}
                      </span>
                    </div>
                  </div>
                  {call.arguments_preview && (
                    <p className="text-xs text-gray-600 mt-1 font-mono truncate">
                      args: {call.arguments_preview}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // ReAct Trace Viewer - for ReAct agents with multi-step reasoning
  if (output._react_metrics) {
    const reactMetrics = output._react_metrics as {
      react_iterations?: number
      react_tool_calls?: number
      reasoning_trace?: Array<{
        thought?: string
        action?: { name?: string; arguments_preview?: string }
        observation?: string
        iteration?: number
      }>
    }

    return (
      <div className="space-y-3">
        {/* ReAct summary */}
        <div className="bg-violet-50 border border-violet-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-violet-800">ReAct Reasoning Loop</span>
            <span className="text-xs text-violet-600">
              {reactMetrics.react_iterations} iterations • {reactMetrics.react_tool_calls} tool calls
            </span>
          </div>
        </div>

        {/* Reasoning trace */}
        {reactMetrics.reasoning_trace && reactMetrics.reasoning_trace.length > 0 && (
          <div className="space-y-2">
            <span className="text-xs text-gray-500 font-medium">Reasoning Trace</span>
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {reactMetrics.reasoning_trace.map((step, i) => (
                <div key={i} className="border rounded-lg overflow-hidden">
                  {/* Iteration header */}
                  <div className="bg-gray-100 px-3 py-1.5 border-b">
                    <span className="text-xs font-medium text-gray-700">
                      Iteration {step.iteration ?? i + 1}
                    </span>
                  </div>

                  <div className="p-3 space-y-2">
                    {/* Thought */}
                    {step.thought && (
                      <div className="bg-blue-50 p-2 rounded">
                        <span className="text-xs font-medium text-blue-700">💭 Thought</span>
                        <p className="text-xs text-blue-800 mt-1">{step.thought}</p>
                      </div>
                    )}

                    {/* Action */}
                    {step.action && (
                      <div className="bg-purple-50 p-2 rounded">
                        <span className="text-xs font-medium text-purple-700">⚡ Action</span>
                        <p className="text-xs font-mono text-purple-800 mt-1">
                          {step.action.name}
                          {step.action.arguments_preview && (
                            <span className="text-purple-600 ml-1">({step.action.arguments_preview})</span>
                          )}
                        </p>
                      </div>
                    )}

                    {/* Observation */}
                    {step.observation && (
                      <div className="bg-green-50 p-2 rounded">
                        <span className="text-xs font-medium text-green-700">👁️ Observation</span>
                        <p className="text-xs text-green-800 mt-1 max-h-20 overflow-y-auto">
                          {step.observation}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // Check for fallback indicator in any output
  if (output._used_fallback) {
    return (
      <div className="space-y-3">
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <span className="text-orange-500">⚠️</span>
            <div className="text-xs text-orange-800">
              <p className="font-medium">Fallback mechanism used</p>
              <p className="mt-1">{output._fallback_reason as string || 'A fallback was used for this stage.'}</p>
            </div>
          </div>
        </div>
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // ==========================================================================
  // HAD (Hierarchical Agentic DAG) Orchestrator Renderers
  // ==========================================================================

  // Zone Planner - show zones, groups, and reasoning trace with image preview
  if (stageName === 'zone_planner') {
    const zones = (output.diagram_zones || []) as ZoneOverlayData[]
    const zoneGroups = (output.zone_groups || []) as ZoneGroup[]
    const imagePath = output.generated_diagram_path as string | undefined
    // Check for trace data in various possible field names
    const detectionTrace = (output.detection_trace || output.reasoning_trace || output._react_trace) as ReActTrace[] | undefined
    const metadata = output.zone_detection_metadata as {
      model?: string
      duration_ms?: number
      retry_count?: number
      detection_strategy?: string
      spatial_validation?: {
        is_valid?: boolean
        overall_score?: number
        errors?: string[]
      }
    } | undefined

    return (
      <ZonePlannerOutput
        zones={zones}
        zoneGroups={zoneGroups}
        imagePath={imagePath}
        detectionTrace={detectionTrace}
        metadata={metadata}
        output={output}
      />
    )
  }

  // Game Orchestrator - show game plan, scene design, and reasoning trace
  if (stageName === 'game_orchestrator') {
    const gamePlan = output.game_plan as {
      learning_objectives?: string[]
      game_mechanics?: string[] | Array<{ type?: string }>
      scoring_rubric?: { max_score?: number }
    } | undefined
    const sceneStructure = output.scene_structure as {
      visual_theme?: string
      layout_type?: string
      regions?: Array<{ id: string }>
    } | undefined
    const sceneAssets = output.scene_assets as {
      required_assets?: Array<{ id: string; type: string }>
    } | undefined
    const sceneInteractions = output.scene_interactions as {
      asset_interactions?: Array<{ asset_id: string; interaction_type: string }>
    } | undefined
    // Check for trace data in various possible field names
    const designTrace = (output.design_trace || output.reasoning_trace || output._react_trace) as ReActTrace[] | undefined
    const designMetadata = output.design_metadata as {
      total_duration_ms?: number
      stage_durations_ms?: Record<string, number>
    } | undefined

    return (
      <GameOrchestratorOutput
        gamePlan={gamePlan}
        sceneStructure={sceneStructure}
        sceneAssets={sceneAssets}
        sceneInteractions={sceneInteractions}
        designTrace={designTrace}
        designMetadata={designMetadata}
        output={output}
      />
    )
  }

  // Game Designer (HAD v3) - unified game design with same output structure as game_orchestrator
  if (stageName === 'game_designer') {
    const gamePlan = output.game_plan as {
      learning_objectives?: string[]
      game_mechanics?: string[] | Array<{ type?: string }>
      scoring_rubric?: { max_score?: number }
    } | undefined
    const sceneStructure = output.scene_structure as {
      visual_theme?: string
      layout_type?: string
      regions?: Array<{ id: string }>
    } | undefined
    const sceneAssets = output.scene_assets as {
      required_assets?: Array<{ id: string; type: string }>
    } | undefined
    const sceneInteractions = output.scene_interactions as {
      asset_interactions?: Array<{ asset_id: string; interaction_type: string }>
    } | undefined
    // Check for trace data in various possible field names
    const designTrace = (output.design_trace || output.reasoning_trace || output._react_trace) as ReActTrace[] | undefined
    const designMetadata = output.design_metadata as {
      total_duration_ms?: number
      call_duration_ms?: number
      unified_call?: boolean
      model?: string
    } | undefined

    return (
      <GameOrchestratorOutput
        gamePlan={gamePlan}
        sceneStructure={sceneStructure}
        sceneAssets={sceneAssets}
        sceneInteractions={sceneInteractions}
        designTrace={designTrace}
        designMetadata={designMetadata}
        output={output}
      />
    )
  }

  // Output Orchestrator - show blueprint, validation, and retry info
  if (stageName === 'output_orchestrator') {
    const blueprint = output.blueprint as {
      title?: string
      templateType?: string
      labels?: Array<{ id: string; text: string }>
      diagram?: { zones?: Array<{ id: string }> }
    } | undefined
    const diagramSvg = output.diagram_svg as string | undefined
    const generationComplete = output.generation_complete as boolean | undefined
    const outputMetadata = output.output_metadata as {
      total_duration_ms?: number
      validation_attempts?: number
      blueprint_retries?: number
    } | undefined
    // Check for trace data in various possible field names
    const orchestrationTrace = (output.orchestration_trace || output.reasoning_trace || output._react_trace) as ReActTrace[] | ReActTrace | undefined

    return (
      <OutputOrchestratorOutput
        blueprint={blueprint}
        diagramSvg={diagramSvg}
        generationComplete={generationComplete}
        outputMetadata={outputMetadata}
        orchestrationTrace={orchestrationTrace}
        output={output}
      />
    )
  }

  // Generic ReAct trace fallback — any agent with _react_trace gets the trace viewer
  const genericReactTrace = output._react_trace as Array<Record<string, unknown>> | undefined
  const genericLlmMetrics = output._llm_metrics as { iterations?: number; tool_calls?: number; latency_ms?: number } | undefined
  if (genericReactTrace && Array.isArray(genericReactTrace) && genericReactTrace.length > 0) {
    return (
      <div className="space-y-3">
        <ReActTraceViewer
          trace={convertBackendTrace(genericReactTrace, stageName, genericLlmMetrics)}
          title={`${stageName} Reasoning Trace`}
          defaultExpanded={false}
        />
        <ToolCallHistory toolCalls={extractToolCallsFromTrace(genericReactTrace)} />
        <JsonViewer data={output} title="Output" />
      </div>
    )
  }

  // ====== V4 Pipeline Agent Renderers ======

  // V4 Input Analyzer — pedagogical context
  if (stageName === 'v4_input_analyzer') {
    const ctx = (output.pedagogical_context || output.input_analysis || output) as {
      blooms_level?: string; subject?: string; topic?: string; difficulty?: string;
      key_concepts?: string[]; misconceptions?: string[]
    }
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          {ctx.blooms_level && (
            <div className="bg-purple-50 p-2 rounded-lg">
              <span className="text-xs text-purple-600 font-medium">Bloom&apos;s Level</span>
              <p className="text-sm font-semibold text-purple-800">{ctx.blooms_level}</p>
            </div>
          )}
          {ctx.subject && (
            <div className="bg-blue-50 p-2 rounded-lg">
              <span className="text-xs text-blue-600 font-medium">Subject</span>
              <p className="text-sm font-semibold text-blue-800">{ctx.subject}</p>
            </div>
          )}
          {ctx.topic && (
            <div className="bg-green-50 p-2 rounded-lg">
              <span className="text-xs text-green-600 font-medium">Topic</span>
              <p className="text-sm font-semibold text-green-800">{ctx.topic}</p>
            </div>
          )}
          {ctx.difficulty && (
            <div className="bg-orange-50 p-2 rounded-lg">
              <span className="text-xs text-orange-600 font-medium">Difficulty</span>
              <p className="text-sm font-semibold text-orange-800">{ctx.difficulty}</p>
            </div>
          )}
        </div>
        {ctx.key_concepts && ctx.key_concepts.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Key Concepts</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {ctx.key_concepts.map((c, i) => (
                <span key={i} className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">{c}</span>
              ))}
            </div>
          </div>
        )}
        {ctx.misconceptions && ctx.misconceptions.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Common Misconceptions</span>
            <ul className="mt-1 space-y-0.5">
              {ctx.misconceptions.map((m, i) => (
                <li key={i} className="text-xs text-red-700 bg-red-50 px-2 py-1 rounded">• {m}</li>
              ))}
            </ul>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // V4 Domain Knowledge Retriever
  if (stageName === 'v4_dk_retriever') {
    const dk = (output.domain_knowledge || output) as {
      canonical_labels?: string[]; descriptions?: Record<string, string>;
      key_terms?: string[]; mechanic_data?: Record<string, unknown>
    }
    return (
      <div className="space-y-3">
        {dk.canonical_labels && dk.canonical_labels.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Canonical Labels ({dk.canonical_labels.length})</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {dk.canonical_labels.map((label, i) => (
                <span key={i} className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">{label}</span>
              ))}
            </div>
          </div>
        )}
        {dk.key_terms && dk.key_terms.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Key Terms</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {dk.key_terms.map((t, i) => (
                <span key={i} className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">{t}</span>
              ))}
            </div>
          </div>
        )}
        {dk.descriptions && Object.keys(dk.descriptions).length > 0 && (
          <div>
            <span className="text-xs text-gray-500 font-medium">Label Descriptions</span>
            <div className="mt-1 space-y-1 max-h-32 overflow-y-auto">
              {Object.entries(dk.descriptions).slice(0, 8).map(([label, desc]) => (
                <div key={label} className="text-xs bg-gray-50 p-1.5 rounded">
                  <span className="font-medium text-gray-800">{label}:</span>{' '}
                  <span className="text-gray-600">{String(desc).slice(0, 100)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // V4 Game Designer — game plan with scenes & mechanics
  if (stageName === 'v4_game_designer' || stageName === 'v4_game_concept_designer') {
    const plan = (output.game_plan || output.game_design || output) as {
      title?: string; total_max_score?: number;
      scenes?: Array<{ scene_id?: string; title?: string; mechanic_types?: string[]; labels?: string[] }>
    }
    return (
      <div className="space-y-3">
        {plan.title && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
            <span className="text-sm font-semibold text-indigo-800">{plan.title}</span>
            <div className="flex gap-3 mt-1 text-xs text-indigo-600">
              <span>Max Score: {plan.total_max_score || '?'}</span>
              <span>{plan.scenes?.length || 0} scenes</span>
            </div>
          </div>
        )}
        {plan.scenes && plan.scenes.length > 0 && (
          <div className="space-y-2">
            {plan.scenes.map((scene, i) => (
              <div key={i} className="bg-gray-50 border border-gray-200 p-2 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">{scene.title || scene.scene_id || `Scene ${i + 1}`}</span>
                  <div className="flex gap-1">
                    {scene.mechanic_types?.map((m, j) => (
                      <span key={j} className="text-[10px] bg-purple-100 text-purple-700 px-1.5 rounded">{m}</span>
                    ))}
                  </div>
                </div>
                {scene.labels && scene.labels.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {scene.labels.slice(0, 8).map((l, j) => (
                      <span key={j} className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">{l}</span>
                    ))}
                    {scene.labels.length > 8 && <span className="text-[10px] text-gray-400">+{scene.labels.length - 8}</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // V4 Game Plan Validator
  if (stageName === 'v4_game_plan_validator') {
    const v = (output.validation_result || output.game_plan_validation || output) as {
      valid?: boolean; computed_max_score?: number; errors?: string[]; warnings?: string[]
    }
    return (
      <div className="space-y-3">
        <div className={`rounded-lg p-3 border ${v.valid ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{v.valid ? 'Game Plan Valid' : 'Validation Failed'}</span>
            {v.computed_max_score != null && (
              <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">Max Score: {v.computed_max_score}</span>
            )}
          </div>
        </div>
        {v.errors && v.errors.length > 0 && (
          <ul className="space-y-1">
            {v.errors.map((e, i) => <li key={i} className="text-xs text-red-700 bg-red-50 px-2 py-1 rounded">• {e}</li>)}
          </ul>
        )}
        {v.warnings && v.warnings.length > 0 && (
          <ul className="space-y-1">
            {v.warnings.map((w, i) => <li key={i} className="text-xs text-yellow-700 bg-yellow-50 px-2 py-1 rounded">• {w}</li>)}
          </ul>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // V4 Content Builder — per-scene/mechanic content tree
  if (stageName === 'v4_content_builder') {
    const mechanicContents = (output.mechanic_contents || []) as Array<{
      mechanic_id?: string; scene_id?: string; mechanic_type?: string; status?: string; content?: Record<string, unknown>
    }>
    const interactionResults = (output.interaction_results || []) as Array<{ scene_id?: string }>
    const subStages = (output._sub_stages || []) as Array<{ id?: string; name?: string; status?: string; duration_ms?: number; mechanic_type?: string }>
    const successCount = mechanicContents.filter(m => m.status === 'success').length
    const failedCount = mechanicContents.filter(m => m.status === 'failed').length
    const sceneIds = [...new Set(mechanicContents.map(m => m.scene_id).filter(Boolean))]
    return (
      <div className="space-y-3">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <span className="text-sm font-semibold text-amber-800">Content Built</span>
          <div className="flex gap-3 mt-1 text-xs text-amber-600">
            <span>{sceneIds.length} scene(s)</span>
            <span>{mechanicContents.length} mechanics</span>
            <span className="text-green-600">{successCount} passed</span>
            {failedCount > 0 && <span className="text-red-600">{failedCount} failed</span>}
            <span>{interactionResults.length} interactions</span>
          </div>
        </div>
        {mechanicContents.length > 0 && (
          <div className="space-y-1">
            {mechanicContents.slice(0, 8).map((mc, i) => (
              <div key={i} className={`text-xs p-2 rounded border flex items-center justify-between ${
                mc.status === 'success' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
              }`}>
                <div className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${mc.status === 'success' ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="font-medium">{mc.mechanic_id || mc.mechanic_type}</span>
                </div>
                <div className="flex items-center gap-2 text-gray-500">
                  <span className="bg-purple-100 text-purple-700 px-1.5 rounded text-[10px]">{mc.mechanic_type}</span>
                  <span>{mc.scene_id}</span>
                </div>
              </div>
            ))}
          </div>
        )}
        {subStages.length > 0 && (
          <div className="border border-amber-200 rounded-lg overflow-hidden">
            <div className="px-3 py-1.5 bg-amber-50 border-b text-xs font-medium text-amber-700">
              Sub-stages ({subStages.length})
            </div>
            <div className="divide-y divide-gray-100">
              {subStages.map((ss, i) => (
                <div key={i} className="px-3 py-1.5 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      ss.status === 'success' ? 'bg-green-500' : ss.status === 'failed' ? 'bg-red-500' : 'bg-gray-400'
                    }`} />
                    <span>{ss.name || ss.id}</span>
                  </div>
                  <span className="text-gray-400">{ss.duration_ms != null ? `${(ss.duration_ms / 1000).toFixed(1)}s` : ''}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // V4 Asset Worker — per-scene image generation results with ZoneOverlay
  if (stageName === 'v4_asset_worker') {
    const results = (output.asset_results || output.scene_assets || output) as Record<string, unknown>
    const sceneKeys = Object.keys(results).filter(k => !k.startsWith('_'))
    return (
      <div className="space-y-3">
        <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-3">
          <span className="text-sm font-semibold text-cyan-800">Assets Generated</span>
          <div className="text-xs text-cyan-600 mt-1">{sceneKeys.length} scene(s) processed</div>
        </div>
        {sceneKeys.slice(0, 4).map(key => {
          const scene = results[key] as {
            image_url?: string;
            zones?: Array<{ id: string; label?: string; zone_type?: string; coordinates?: Record<string, unknown> }>
            match_quality?: number; status?: string
          } | undefined
          const imgUrl = scene?.image_url
          const proxiedUrl = imgUrl?.startsWith('http')
            ? `/api/generate/proxy/image?url=${encodeURIComponent(imgUrl)}`
            : imgUrl
          const overlayZones = (scene?.zones || []).map(z => ({
            id: z.id,
            label: z.label || z.id,
            zone_type: (z.zone_type || 'bounding_box') as 'circle' | 'ellipse' | 'bounding_box' | 'polygon' | 'path',
            coordinates: z.coordinates || {},
          }))
          return (
            <div key={key} className="bg-gray-50 border border-gray-200 p-2 rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium">{key}</span>
                <div className="flex items-center gap-2">
                  {scene?.match_quality != null && (
                    <span className={`text-[10px] px-1.5 rounded ${scene.match_quality >= 0.8 ? 'bg-green-100 text-green-700' : scene.match_quality >= 0.5 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                      {Math.round(scene.match_quality * 100)}% match
                    </span>
                  )}
                  <span className="text-xs text-gray-500">{overlayZones.length} zones</span>
                </div>
              </div>
              {proxiedUrl && overlayZones.length > 0 ? (
                <div className="border rounded overflow-hidden">
                  <ZoneOverlay imageSrc={proxiedUrl} zones={overlayZones} showLabels={true} />
                </div>
              ) : proxiedUrl ? (
                <img
                  src={proxiedUrl}
                  alt={key}
                  className="max-h-28 rounded border object-cover"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
              ) : null}
            </div>
          )
        })}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // V4 Asset Merge — deduplicated assets summary
  if (stageName === 'v4_asset_merge') {
    const merged = (output.merged_assets || output) as {
      total_scenes?: number; total_zones?: number; dedup_count?: number;
      scenes?: Array<{ scene_id?: string; status?: string; zone_count?: number }>
    }
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-cyan-50 p-2 rounded-lg text-center">
            <span className="text-xs text-cyan-600 font-medium">Scenes</span>
            <p className="text-lg font-bold text-cyan-800">{merged.total_scenes || merged.scenes?.length || '?'}</p>
          </div>
          <div className="bg-blue-50 p-2 rounded-lg text-center">
            <span className="text-xs text-blue-600 font-medium">Total Zones</span>
            <p className="text-lg font-bold text-blue-800">{merged.total_zones || '?'}</p>
          </div>
          <div className="bg-green-50 p-2 rounded-lg text-center">
            <span className="text-xs text-green-600 font-medium">Deduplicated</span>
            <p className="text-lg font-bold text-green-800">{merged.dedup_count || 0}</p>
          </div>
        </div>
        {merged.scenes && merged.scenes.length > 0 && (
          <div className="space-y-1">
            {merged.scenes.map((s, i) => (
              <div key={i} className={`text-xs p-2 rounded border flex items-center justify-between ${
                s.status === 'success' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
              }`}>
                <span className="font-medium">{s.scene_id || `Scene ${i + 1}`}</span>
                <div className="flex gap-2">
                  <span>{s.zone_count || 0} zones</span>
                  <span className={s.status === 'success' ? 'text-green-600' : 'text-red-600'}>{s.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // V4 Assembler — final blueprint summary
  if (stageName === 'v4_assembler') {
    const bp = (output.blueprint || output) as {
      title?: string; templateType?: string; total_max_score?: number;
      diagram?: { imageUrl?: string; zones?: Array<{ id: string; label?: string; zone_type?: string; coordinates?: Record<string, unknown> }> }
      scenes?: Array<{ scene_id?: string; title?: string; mechanic_types?: string[] }>
      labels?: Array<{ id: string; text: string }>
    }
    const v4ImageUrl = bp.diagram?.imageUrl
    const v4Proxied = v4ImageUrl?.startsWith('http')
      ? `/api/generate/proxy/image?url=${encodeURIComponent(v4ImageUrl)}`
      : v4ImageUrl
    const v4Zones = (bp.diagram?.zones || []).map(z => ({
      id: z.id,
      label: z.label || z.id,
      zone_type: (z.zone_type || 'bounding_box') as 'circle' | 'ellipse' | 'bounding_box' | 'polygon' | 'path',
      coordinates: z.coordinates || {},
    }))

    return (
      <div className="space-y-3">
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-emerald-800">{bp.title || 'Blueprint'}</span>
            <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">
              {bp.templateType?.replace(/_/g, ' ') || 'Unknown'}
            </span>
          </div>
          <div className="flex gap-3 mt-1 text-xs text-emerald-600">
            <span>Max Score: {bp.total_max_score || '?'}</span>
            <span>{bp.scenes?.length || 0} scenes</span>
            <span>{bp.labels?.length || 0} labels</span>
            <span>{v4Zones.length} zones</span>
          </div>
        </div>
        {v4Proxied && v4Zones.length > 0 && (
          <div className="border rounded-lg overflow-hidden">
            <div className="px-3 py-1.5 bg-emerald-50 border-b text-xs font-medium text-emerald-700">Final Layout</div>
            <ZoneOverlay imageSrc={v4Proxied} zones={v4Zones} showLabels={true} />
          </div>
        )}
        {bp.scenes && bp.scenes.length > 0 && (
          <div className="space-y-1">
            {bp.scenes.map((scene, i) => (
              <div key={i} className="bg-gray-50 border border-gray-200 p-2 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">{scene.title || scene.scene_id}</span>
                  <div className="flex gap-1">
                    {scene.mechanic_types?.map((m, j) => (
                      <span key={j} className="text-[10px] bg-purple-100 text-purple-700 px-1.5 rounded">{m}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        <JsonViewer data={output} title="Full Output" />
      </div>
    )
  }

  // === Sub-stage mechanic content renderers (for compound V4 nodes) ===
  if (stageName.includes('::')) {
    const parentName = stageName.split('::')[0]

    // Content sub-stages — show full mechanic content
    if (parentName === 'v4_content_builder' || parentName === 'content_builder') {
      // output is now the full content dict (items, sequence_items, pairs, etc.)
      const items = (output.items || output.sequence_items || output.pairs || output.categories || []) as Array<Record<string, unknown>>
      const distractors = output.distractors as Array<Record<string, unknown>> | undefined
      const mechanicScoring = output.mechanic_scoring as Record<string, unknown> | undefined
      const mechanicFeedback = output.mechanic_feedback as Record<string, unknown> | undefined

      return (
        <div className="space-y-3">
          {items.length > 0 && (
            <div className="bg-indigo-50 p-3 rounded-lg border border-indigo-200">
              <span className="text-xs text-indigo-600 font-medium">Generated Content ({items.length} items)</span>
              <div className="mt-2 space-y-1.5 max-h-60 overflow-y-auto">
                {items.map((item, i) => {
                  const itemLabel = String(item.label || item.name || item.title || item.text || `Item ${i + 1}`)
                  const itemDesc = item.description ? String(item.description).slice(0, 120) : null
                  return (
                    <div key={i} className="bg-white p-2 rounded text-xs">
                      <span className="font-medium text-gray-700">{itemLabel}</span>
                      {itemDesc && (
                        <p className="text-gray-500 mt-0.5 text-[11px]">{itemDesc}</p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
          {distractors && distractors.length > 0 && (
            <div className="bg-orange-50 p-3 rounded-lg border border-orange-200">
              <span className="text-xs text-orange-600 font-medium">Distractors ({distractors.length})</span>
              <div className="flex flex-wrap gap-1 mt-1.5">
                {distractors.map((d, i) => (
                  <span key={i} className="text-[10px] bg-orange-100 text-orange-800 px-1.5 py-0.5 rounded">
                    {(d.label || d.text || `Distractor ${i + 1}`) as string}
                  </span>
                ))}
              </div>
            </div>
          )}
          {(mechanicScoring || mechanicFeedback) && (
            <div className="bg-green-50 p-3 rounded-lg border border-green-200">
              <span className="text-xs text-green-600 font-medium">Interaction Design</span>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {mechanicScoring && (
                  <div className="bg-white p-2 rounded">
                    <span className="text-[10px] text-gray-500">Scoring</span>
                    <p className="text-xs font-semibold text-green-700">Configured</p>
                  </div>
                )}
                {mechanicFeedback && (
                  <div className="bg-white p-2 rounded">
                    <span className="text-[10px] text-gray-500">Feedback</span>
                    <p className="text-xs font-semibold text-green-700">Configured</p>
                  </div>
                )}
              </div>
            </div>
          )}
          <JsonViewer data={output} title="Full Output" />
        </div>
      )
    }

    // DK sub-stages — show extraction data
    if (parentName === 'v4_dk_retriever' || parentName === 'dk_retriever') {
      const canonicalLabels = output.canonical_labels as string[] | undefined
      const descriptions = output.descriptions as Record<string, string> | undefined
      const sources = output.sources as Array<Record<string, unknown> | string> | undefined

      return (
        <div className="space-y-3">
          {canonicalLabels && canonicalLabels.length > 0 && (
            <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
              <span className="text-xs text-blue-600 font-medium">Canonical Labels ({canonicalLabels.length})</span>
              <div className="flex flex-wrap gap-1 mt-1.5">
                {canonicalLabels.map((label, i) => (
                  <span key={i} className="text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded">{label}</span>
                ))}
              </div>
            </div>
          )}
          {descriptions && Object.keys(descriptions).length > 0 && (
            <div className="bg-purple-50 p-3 rounded-lg border border-purple-200">
              <span className="text-xs text-purple-600 font-medium">Label Descriptions ({Object.keys(descriptions).length})</span>
              <div className="mt-2 space-y-1.5 max-h-48 overflow-y-auto">
                {Object.entries(descriptions).map(([label, desc]) => (
                  <div key={label} className="bg-white p-2 rounded text-xs">
                    <span className="font-medium text-gray-700">{label}</span>
                    <p className="text-gray-500 mt-0.5 text-[11px]">{String(desc).slice(0, 100)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {sources && sources.length > 0 && (
            <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
              <span className="text-xs text-gray-600 font-medium">Sources ({sources.length})</span>
              <div className="mt-1.5 space-y-1">
                {sources.slice(0, 5).map((src, i) => (
                  <p key={i} className="text-[11px] text-gray-500 truncate">
                    {typeof src === 'string' ? src : (src.title || src.url || `Source ${i + 1}`) as string}
                  </p>
                ))}
              </div>
            </div>
          )}
          <JsonViewer data={output} title="Full Output" />
        </div>
      )
    }

    // Generic sub-stage fallback
    return (
      <div className="space-y-3">
        <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
          <span className="text-xs text-gray-600 font-medium">Sub-stage Output</span>
        </div>
        <JsonViewer data={output} title="Output" />
      </div>
    )
  }

  // (Duplicate V4 renderers removed — primary set is at line ~4085 above)

  // Default: just show JSON
  return <JsonViewer data={output} title="Output" />
}

function JsonViewer({ data, title }: { data?: Record<string, unknown> | null; title?: string }) {
  const [expanded, setExpanded] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [copied, setCopied] = useState(false)

  if (!data || Object.keys(data).length === 0) {
    return <p className="text-sm text-gray-500 text-center py-4">No data available</p>
  }

  const jsonString = JSON.stringify(data, null, 2)
  const isLarge = jsonString.length > 500

  const copyToClipboard = () => {
    navigator.clipboard.writeText(jsonString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Simple syntax highlighting
  const highlightJson = (json: string, search: string): React.ReactNode => {
    const lines = json.split('\n')
    return lines.map((line, i) => {
      // Highlight keys (text before :)
      let highlighted = line
        .replace(/"([^"]+)":/g, '<span class="text-blue-600">"$1"</span>:')
        // Highlight string values (text after : in quotes)
        .replace(/: "([^"]*)"(,?)$/g, ': <span class="text-green-600">"$1"</span>$2')
        // Highlight numbers
        .replace(/: (\d+\.?\d*)(,?)$/g, ': <span class="text-orange-600">$1</span>$2')
        // Highlight booleans and null
        .replace(/: (true|false|null)(,?)$/g, ': <span class="text-purple-600">$1</span>$2')

      // Highlight search matches
      const hasMatch = search && line.toLowerCase().includes(search.toLowerCase())
      const sanitizedHighlighted = sanitizeHTML(highlighted)
      if (hasMatch) {
        return (
          <div
            key={i}
            className="bg-yellow-100 -mx-3 px-3"
            dangerouslySetInnerHTML={{ __html: sanitizedHighlighted }}
          />
        )
      }

      return <div key={i} dangerouslySetInnerHTML={{ __html: sanitizedHighlighted }} />
    })
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b gap-2">
        <span className="text-xs font-medium text-gray-600 flex-shrink-0">
          {title || 'JSON'}
        </span>
        <div className="flex items-center gap-2 flex-1 justify-end">
          <input
            type="text"
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="text-xs px-2 py-1 border rounded w-20 focus:w-28 transition-all focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          {isLarge && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              {expanded ? 'Collapse' : 'Expand'}
            </button>
          )}
          <button
            onClick={copyToClipboard}
            className="text-xs text-gray-600 hover:text-gray-800 font-medium flex items-center gap-1"
          >
            {copied ? (
              <>
                <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Copied
              </>
            ) : (
              <>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </>
            )}
          </button>
        </div>
      </div>

      {/* JSON Content with syntax highlighting */}
      <pre
        className={`p-3 text-xs overflow-auto font-mono bg-gray-50 ${
          expanded ? 'max-h-[500px]' : 'max-h-40'
        }`}
      >
        <code>{highlightJson(jsonString, searchTerm)}</code>
      </pre>
    </div>
  )
}

// Helper to highlight search terms in log messages
function highlightSearchTerm(text: string, search: string): React.ReactNode {
  if (!search) return text
  const regex = new RegExp(`(${search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  const parts = text.split(regex)
  return parts.map((part, i) =>
    regex.test(part) ? (
      <mark key={i} className="bg-yellow-200 px-0.5 rounded">
        {part}
      </mark>
    ) : (
      part
    )
  )
}

// =============================================================================
// HAD Orchestrator Output Components
// =============================================================================

// Zone Planner Output - shows zones, groups, reasoning trace, and image preview
function ZonePlannerOutput({
  zones,
  zoneGroups,
  imagePath,
  detectionTrace,
  metadata,
  output,
}: {
  zones: ZoneOverlayData[]
  zoneGroups: ZoneGroup[]
  imagePath?: string
  detectionTrace?: ReActTrace[]
  metadata?: {
    model?: string
    duration_ms?: number
    retry_count?: number
    detection_strategy?: string
    spatial_validation?: {
      is_valid?: boolean
      overall_score?: number
      errors?: string[]
    }
  }
  output: Record<string, unknown>
}) {
  const [detailLevel, setDetailLevel] = useState<DetailLevel>('summary')
  const [selectedZoneId, setSelectedZoneId] = useState<string | undefined>()

  // Format duration helper
  const formatDuration = (ms?: number) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-cyan-100 text-cyan-800 text-xs font-medium rounded-full">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
            </svg>
            {zones.length} zone{zones.length !== 1 ? 's' : ''}
          </span>
          {zoneGroups.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded-full">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z" />
              </svg>
              {zoneGroups.length} group{zoneGroups.length !== 1 ? 's' : ''}
            </span>
          )}
          {detectionTrace && detectionTrace.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-800 text-xs font-medium rounded-full">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
              </svg>
              {detectionTrace.reduce((sum, t) => sum + (t.iterations || 1), 0)} iteration{detectionTrace.reduce((sum, t) => sum + (t.iterations || 1), 0) !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <button
          onClick={() => setDetailLevel(detailLevel === 'summary' ? 'full' : 'summary')}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          {detailLevel === 'summary' ? 'Show Details' : 'Hide Details'}
        </button>
      </div>

      {/* Metadata Row */}
      {metadata && (
        <div className="flex flex-wrap gap-3 text-xs text-gray-500">
          {metadata.model && <span>Model: {metadata.model.split('/').pop()}</span>}
          {metadata.duration_ms && <span>Duration: {formatDuration(metadata.duration_ms)}</span>}
          {metadata.detection_strategy && <span>Strategy: {metadata.detection_strategy}</span>}
          {metadata.retry_count !== undefined && metadata.retry_count > 0 && (
            <span className="text-orange-600">{metadata.retry_count} retries</span>
          )}
        </div>
      )}

      {/* Image with Zone Overlay */}
      {imagePath && (
        <div className="border rounded-lg overflow-hidden">
          <ZoneOverlay
            imageSrc={imagePath.startsWith('/') ? `/api/files${imagePath}` : imagePath}
            zones={zones}
            groups={zoneGroups}
            onZoneClick={(zone) => setSelectedZoneId(zone.id === selectedZoneId ? undefined : zone.id)}
            selectedZoneId={selectedZoneId}
            showLabels={detailLevel === 'full'}
            showGroupColors={true}
          />
        </div>
      )}

      {/* Spatial Validation Status */}
      {metadata?.spatial_validation && (
        <div className={`p-3 rounded-lg ${metadata.spatial_validation.is_valid ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
          <div className="flex items-center gap-2">
            {metadata.spatial_validation.is_valid ? (
              <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            )}
            <span className={`text-sm font-medium ${metadata.spatial_validation.is_valid ? 'text-green-700' : 'text-red-700'}`}>
              Spatial Validation: {metadata.spatial_validation.is_valid ? 'Passed' : 'Failed'}
              {metadata.spatial_validation.overall_score !== undefined && ` (${Math.round(metadata.spatial_validation.overall_score * 100)}%)`}
            </span>
          </div>
          {metadata.spatial_validation.errors && metadata.spatial_validation.errors.length > 0 && (
            <ul className="mt-2 text-xs text-red-600 list-disc list-inside">
              {metadata.spatial_validation.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Full Details */}
      {detailLevel === 'full' && (
        <>
          {/* Zone List */}
          {zones.length > 0 && (
            <div className="border rounded-lg p-3">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Detected Zones</h4>
              <ZoneList
                zones={zones}
                groups={zoneGroups}
                onZoneClick={(zone) => setSelectedZoneId(zone.id === selectedZoneId ? undefined : zone.id)}
                selectedZoneId={selectedZoneId}
              />
            </div>
          )}

          {/* ReAct Reasoning Trace */}
          {detectionTrace && detectionTrace.length > 0 && (
            <MultiTraceViewer traces={detectionTrace} title="Detection Reasoning" />
          )}

          {/* Raw JSON */}
          <JsonViewer data={output} title="Raw Output" />
        </>
      )}
    </div>
  )
}

// Game Orchestrator Output - shows game plan, scene design, and reasoning trace
function GameOrchestratorOutput({
  gamePlan,
  sceneStructure,
  sceneAssets,
  sceneInteractions,
  designTrace,
  designMetadata,
  output,
}: {
  gamePlan?: {
    learning_objectives?: string[]
    game_mechanics?: string[] | Array<{ type?: string }>
    scoring_rubric?: { max_score?: number }
  }
  sceneStructure?: {
    visual_theme?: string
    layout_type?: string
    regions?: Array<{ id: string }>
  }
  sceneAssets?: {
    required_assets?: Array<{ id: string; type: string }>
  }
  sceneInteractions?: {
    asset_interactions?: Array<{ asset_id: string; interaction_type: string }>
  }
  designTrace?: ReActTrace[]
  designMetadata?: {
    total_duration_ms?: number
    stage_durations_ms?: Record<string, number>
  }
  output: Record<string, unknown>
}) {
  const [detailLevel, setDetailLevel] = useState<DetailLevel>('summary')

  // Format duration helper
  const formatDuration = (ms?: number) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  // Count mechanics
  const mechanicsCount = gamePlan?.game_mechanics?.length || 0
  const objectivesCount = gamePlan?.learning_objectives?.length || 0
  const regionsCount = sceneStructure?.regions?.length || 0
  const assetsCount = sceneAssets?.required_assets?.length || 0
  const interactionsCount = sceneInteractions?.asset_interactions?.length || 0

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-800 text-xs font-medium rounded-full">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
            {objectivesCount} objective{objectivesCount !== 1 ? 's' : ''}
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
            </svg>
            {mechanicsCount} mechanic{mechanicsCount !== 1 ? 's' : ''}
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
            {regionsCount} region{regionsCount !== 1 ? 's' : ''}
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded-full">
            {assetsCount} asset{assetsCount !== 1 ? 's' : ''}
          </span>
        </div>
        <button
          onClick={() => setDetailLevel(detailLevel === 'summary' ? 'full' : 'summary')}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          {detailLevel === 'summary' ? 'Show Details' : 'Hide Details'}
        </button>
      </div>

      {/* Metadata Row */}
      {designMetadata && (
        <div className="flex flex-wrap gap-3 text-xs text-gray-500">
          {designMetadata.total_duration_ms && (
            <span>Total: {formatDuration(designMetadata.total_duration_ms)}</span>
          )}
          {designMetadata.stage_durations_ms && Object.entries(designMetadata.stage_durations_ms).map(([stage, ms]) => (
            <span key={stage}>{stage.replace(/_/g, ' ')}: {formatDuration(ms)}</span>
          ))}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3">
        {/* Game Plan Card */}
        <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🎮</span>
            <h4 className="text-sm font-medium text-amber-900">Game Plan</h4>
          </div>
          <div className="text-xs text-amber-700 space-y-1">
            <p>{objectivesCount} learning objective{objectivesCount !== 1 ? 's' : ''}</p>
            <p>{mechanicsCount} game mechanic{mechanicsCount !== 1 ? 's' : ''}</p>
            {gamePlan?.scoring_rubric?.max_score && (
              <p>Max score: {gamePlan.scoring_rubric.max_score}</p>
            )}
          </div>
        </div>

        {/* Scene Card */}
        <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🎬</span>
            <h4 className="text-sm font-medium text-blue-900">Scene Design</h4>
          </div>
          <div className="text-xs text-blue-700 space-y-1">
            <p>{regionsCount} region{regionsCount !== 1 ? 's' : ''}</p>
            <p>{assetsCount} asset{assetsCount !== 1 ? 's' : ''}</p>
            <p>{interactionsCount} interaction{interactionsCount !== 1 ? 's' : ''}</p>
            {sceneStructure?.visual_theme && (
              <p>Theme: {sceneStructure.visual_theme}</p>
            )}
          </div>
        </div>
      </div>

      {/* Full Details */}
      {detailLevel === 'full' && (
        <>
          {/* Learning Objectives */}
          {gamePlan?.learning_objectives && gamePlan.learning_objectives.length > 0 && (
            <div className="border rounded-lg p-3">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Learning Objectives</h4>
              <ul className="text-xs text-gray-700 space-y-1 list-disc list-inside">
                {gamePlan.learning_objectives.map((obj, i) => (
                  <li key={i}>{obj}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Game Mechanics */}
          {gamePlan?.game_mechanics && gamePlan.game_mechanics.length > 0 && (
            <div className="border rounded-lg p-3">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Game Mechanics</h4>
              <div className="flex flex-wrap gap-2">
                {gamePlan.game_mechanics.map((mech, i) => (
                  <span key={i} className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                    {typeof mech === 'string' ? mech : mech.type || 'Unknown'}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Scene Structure */}
          {sceneStructure && (
            <div className="border rounded-lg p-3">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Scene Structure</h4>
              <div className="text-xs text-gray-700 space-y-1">
                {sceneStructure.visual_theme && <p><span className="font-medium">Theme:</span> {sceneStructure.visual_theme}</p>}
                {sceneStructure.layout_type && <p><span className="font-medium">Layout:</span> {sceneStructure.layout_type}</p>}
                {sceneStructure.regions && sceneStructure.regions.length > 0 && (
                  <div className="mt-2">
                    <span className="font-medium">Regions:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {sceneStructure.regions.map((region, i) => (
                        <span key={i} className="bg-gray-100 px-1.5 py-0.5 rounded">{region.id}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Design Trace */}
          {designTrace && designTrace.length > 0 && (
            <MultiTraceViewer traces={designTrace} title="Design Reasoning" />
          )}

          {/* Raw JSON */}
          <JsonViewer data={output} title="Raw Output" />
        </>
      )}
    </div>
  )
}

// Output Orchestrator Output - shows blueprint, validation, and retry info
function OutputOrchestratorOutput({
  blueprint,
  diagramSvg,
  generationComplete,
  outputMetadata,
  orchestrationTrace,
  output,
}: {
  blueprint?: {
    title?: string
    templateType?: string
    labels?: Array<{ id: string; text: string }>
    diagram?: { zones?: Array<{ id: string }> }
  }
  diagramSvg?: string
  generationComplete?: boolean
  outputMetadata?: {
    total_duration_ms?: number
    validation_attempts?: number
    blueprint_retries?: number
  }
  orchestrationTrace?: ReActTrace[] | ReActTrace
  output: Record<string, unknown>
}) {
  const [detailLevel, setDetailLevel] = useState<DetailLevel>('summary')
  const [showSvgPreview, setShowSvgPreview] = useState(true)

  // Format duration helper
  const formatDuration = (ms?: number) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  // Extract counts
  const labelsCount = blueprint?.labels?.length || 0
  const zonesCount = blueprint?.diagram?.zones?.length || 0
  const validationAttempts = outputMetadata?.validation_attempts || 0
  const blueprintRetries = outputMetadata?.blueprint_retries || 0

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-2">
          {/* Generation Status */}
          <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${
            generationComplete
              ? 'bg-green-100 text-green-800'
              : 'bg-yellow-100 text-yellow-800'
          }`}>
            {generationComplete ? (
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
            )}
            {generationComplete ? 'Complete' : 'In Progress'}
          </span>

          {/* Blueprint Status */}
          <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${
            blueprint ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-600'
          }`}>
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
            </svg>
            Blueprint {blueprint ? '✓' : '✗'}
          </span>

          {/* Retry Badge */}
          {(validationAttempts > 1 || blueprintRetries > 0) && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-800 text-xs font-medium rounded-full">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
              {blueprintRetries > 0 ? `${blueprintRetries} retries` : `${validationAttempts} attempts`}
            </span>
          )}
        </div>
        <button
          onClick={() => setDetailLevel(detailLevel === 'summary' ? 'full' : 'summary')}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          {detailLevel === 'summary' ? 'Show Details' : 'Hide Details'}
        </button>
      </div>

      {/* Metadata Row */}
      {outputMetadata && (
        <div className="flex flex-wrap gap-3 text-xs text-gray-500">
          {outputMetadata.total_duration_ms && (
            <span>Duration: {formatDuration(outputMetadata.total_duration_ms)}</span>
          )}
          {blueprint?.templateType && (
            <span>Template: {blueprint.templateType}</span>
          )}
        </div>
      )}

      {/* SVG Preview */}
      {diagramSvg && (
        <div className="border rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b">
            <span className="text-xs font-medium text-gray-600">Diagram Preview</span>
            <button
              onClick={() => setShowSvgPreview(!showSvgPreview)}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              {showSvgPreview ? 'Hide' : 'Show'}
            </button>
          </div>
          {showSvgPreview && (
            <div
              className="p-4 bg-white flex justify-center"
              dangerouslySetInnerHTML={{ __html: sanitizeSVG(diagramSvg) }}
            />
          )}
        </div>
      )}

      {/* Blueprint Summary Card */}
      {blueprint && (
        <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">📋</span>
            <h4 className="text-sm font-medium text-emerald-900">
              {blueprint.title || 'Blueprint'}
            </h4>
          </div>
          <div className="text-xs text-emerald-700 space-y-1">
            {blueprint.templateType && <p>Template: {blueprint.templateType}</p>}
            <p>{labelsCount} label{labelsCount !== 1 ? 's' : ''}</p>
            <p>{zonesCount} zone{zonesCount !== 1 ? 's' : ''}</p>
          </div>
        </div>
      )}

      {/* Full Details */}
      {detailLevel === 'full' && (
        <>
          {/* Labels List */}
          {blueprint?.labels && blueprint.labels.length > 0 && (
            <div className="border rounded-lg p-3">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Labels</h4>
              <div className="flex flex-wrap gap-2">
                {blueprint.labels.map((label, i) => (
                  <span key={i} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                    {label.text || label.id}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Zones List */}
          {blueprint?.diagram?.zones && blueprint.diagram.zones.length > 0 && (
            <div className="border rounded-lg p-3">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Diagram Zones</h4>
              <div className="flex flex-wrap gap-2">
                {blueprint.diagram.zones.map((zone, i) => (
                  <span key={i} className="text-xs bg-cyan-100 text-cyan-700 px-2 py-1 rounded">
                    {zone.id}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Orchestration Trace */}
          {orchestrationTrace && (
            Array.isArray(orchestrationTrace) && orchestrationTrace.length > 0 ? (
              <MultiTraceViewer traces={orchestrationTrace} title="Orchestration Reasoning" />
            ) : !Array.isArray(orchestrationTrace) && orchestrationTrace.steps && orchestrationTrace.steps.length > 0 ? (
              <ReActTraceViewer trace={orchestrationTrace} title="Orchestration Reasoning" />
            ) : null
          )}

          {/* Raw JSON */}
          <JsonViewer data={output} title="Raw Output" />
        </>
      )}
    </div>
  )
}
