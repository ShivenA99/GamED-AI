'use client'

import React, { useState, useEffect } from 'react'
import { StageExecution, STATUS_COLORS } from './types'
import { ToolCallHistory, ToolCall } from './ToolCallHistory'
import { AGENT_METADATA } from './PipelineView'

interface StageDetailSectionProps {
  stage: StageExecution & { run_id?: string }
  onRetry?: (stageName: string) => void
  onClose: () => void
}

// Agent output rendering is handled by AgentOutputInline below (JsonViewer + state keys).
// Full custom renderers live in StagePanel and are used when PipelineView renders its own sidebar.

export function StageDetailSection({ stage, onRetry, onClose }: StageDetailSectionProps) {
  const [logsExpanded, setLogsExpanded] = useState(false)
  const [inputExpanded, setInputExpanded] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)
  const [retryError, setRetryError] = useState<string | null>(null)
  const [logs, setLogs] = useState<Array<{ id: string; level: string; message: string; timestamp: string }>>([])
  const [loadingLogs, setLoadingLogs] = useState(false)

  const statusColors = STATUS_COLORS[stage.status] || STATUS_COLORS.pending
  const metadata = AGENT_METADATA[stage.stage_name]

  // Fetch logs
  useEffect(() => {
    if (!logsExpanded || !stage.id || !stage.run_id) return
    if (stage.id.startsWith('pending-') || stage.id.startsWith('inferred-')) return

    const fetchLogs = async () => {
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
    }
    fetchLogs()
  }, [logsExpanded, stage.id, stage.run_id])

  const handleRetry = async () => {
    if (!onRetry) return
    setIsRetrying(true)
    setRetryError(null)
    try {
      await onRetry(stage.stage_name)
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : 'Retry failed')
    } finally {
      setIsRetrying(false)
    }
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  const formatStageName = (name: string): string => {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  // Extract tool calls from output
  const toolCalls = extractToolCalls(stage.output_snapshot)

  // Extract ReAct trace
  const reactTrace = stage.output_snapshot?._react_trace as Array<Record<string, unknown>> | undefined

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {metadata?.icon && <span className="text-lg">{metadata.icon}</span>}
          <h2 className="text-base font-semibold text-gray-900">
            {metadata?.name || formatStageName(stage.stage_name)}
          </h2>
          <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${statusColors.bg} ${statusColors.text}`}>
            {stage.status}
          </span>
          {metadata?.toolOrModel && (
            <span className="text-xs text-gray-400 hidden sm:inline">{metadata.toolOrModel}</span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors"
          title="Close"
        >
          <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* 2-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[45%_55%] divide-y lg:divide-y-0 lg:divide-x divide-gray-200">
        {/* Left column — Overview */}
        <div className="p-5 space-y-4">
          {/* Timing */}
          <DetailSection title="Timing">
            <DetailRow label="Started" value={stage.started_at ? new Date(stage.started_at).toLocaleString() : '-'} />
            <DetailRow label="Finished" value={stage.finished_at ? new Date(stage.finished_at).toLocaleString() : '-'} />
            <DetailRow label="Duration" value={stage.duration_ms ? formatDuration(stage.duration_ms) : '-'} />
            {stage.retry_count > 0 && (
              <DetailRow label="Retries" value={stage.retry_count.toString()} className="text-orange-600" />
            )}
          </DetailSection>

          {/* LLM Metrics */}
          {(stage.model_id || stage.total_tokens || stage.estimated_cost_usd) && (
            <DetailSection title="LLM Metrics">
              {stage.model_id && <DetailRow label="Model" value={stage.model_id} />}
              {stage.prompt_tokens != null && <DetailRow label="Prompt" value={stage.prompt_tokens.toLocaleString()} />}
              {stage.completion_tokens != null && <DetailRow label="Completion" value={stage.completion_tokens.toLocaleString()} />}
              {stage.total_tokens != null && <DetailRow label="Total tokens" value={stage.total_tokens.toLocaleString()} />}
              {stage.latency_ms != null && <DetailRow label="Latency" value={formatDuration(stage.latency_ms)} />}
              {stage.estimated_cost_usd != null && <DetailRow label="Cost" value={`$${stage.estimated_cost_usd.toFixed(4)}`} />}
            </DetailSection>
          )}

          {/* Validation */}
          {stage.validation_passed !== null && (
            <DetailSection title="Validation">
              <DetailRow
                label="Passed"
                value={stage.validation_passed ? 'Yes' : 'No'}
                className={stage.validation_passed ? 'text-green-600' : 'text-red-600'}
              />
              {stage.validation_score !== null && (
                <DetailRow label="Score" value={`${(stage.validation_score * 100).toFixed(0)}%`} />
              )}
              {stage.validation_errors && stage.validation_errors.length > 0 && (
                <div className="mt-2 space-y-1">
                  {stage.validation_errors.map((err, i) => (
                    <p key={i} className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">{err}</p>
                  ))}
                </div>
              )}
            </DetailSection>
          )}

          {/* Error */}
          {stage.error_message && (
            <DetailSection title="Error">
              <div className="bg-red-50 p-3 rounded text-sm text-red-700">{stage.error_message}</div>
              {stage.error_traceback && (
                <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto max-h-40">
                  {stage.error_traceback}
                </pre>
              )}
            </DetailSection>
          )}

          {/* Retry button */}
          {onRetry && !stage.id?.startsWith('pending-') && !stage.id?.startsWith('inferred-') && (
            <div className="pt-2 border-t border-gray-100">
              <button
                onClick={handleRetry}
                disabled={isRetrying}
                className="w-full py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
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
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Retry from this Stage
                  </>
                )}
              </button>
              {retryError && (
                <p className="text-xs text-red-600 mt-2 text-center">{retryError}</p>
              )}
            </div>
          )}
        </div>

        {/* Right column — Output, Tools, ReAct */}
        <div className="p-5 space-y-4 max-h-[600px] overflow-y-auto">
          {/* Agent Output */}
          <DetailSection title="Agent Output">
            <AgentOutputInline stageName={stage.stage_name} output={stage.output_snapshot} />
          </DetailSection>

          {/* Tool Calls — inline collapsible */}
          {toolCalls.length > 0 && (
            <DetailSection title={`Tool Calls (${toolCalls.length})`} defaultOpen>
              <ToolCallHistory toolCalls={toolCalls} title="" />
            </DetailSection>
          )}

          {/* ReAct Trace — inline collapsible */}
          {reactTrace && reactTrace.length > 0 && (
            <DetailSection title={`ReAct Trace (${reactTrace.length} steps)`} defaultOpen={false}>
              <div className="space-y-2">
                {reactTrace.map((step, idx) => (
                  <div key={idx} className="space-y-1">
                    {typeof step.thought === 'string' && step.thought && (
                      <div className="text-xs p-2 rounded border bg-purple-50 text-purple-700 border-purple-200">
                        <span className="font-mono uppercase text-[10px] font-semibold px-1 py-0.5 rounded bg-purple-100 text-purple-800">
                          thought #{(step.iteration as number) || idx + 1}
                        </span>
                        <p className="mt-1 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words">
                          {(step.thought as string).substring(0, 500)}
                        </p>
                      </div>
                    )}
                    {step.action != null && (
                      <div className="text-xs p-2 rounded border bg-blue-50 text-blue-700 border-blue-200">
                        <span className="font-mono uppercase text-[10px] font-semibold px-1 py-0.5 rounded bg-blue-100 text-blue-800">
                          action
                        </span>
                        <p className="mt-1 font-mono text-[11px]">
                          {typeof step.action === 'string'
                            ? step.action
                            : `${(step.action as { name?: string }).name || 'unknown'}(${
                                (step.action as { arguments?: Record<string, unknown> }).arguments
                                  ? JSON.stringify((step.action as { arguments?: Record<string, unknown> }).arguments).substring(0, 200)
                                  : ''
                              })`
                          }
                        </p>
                      </div>
                    )}
                    {step.observation != null && (
                      <div className="text-xs p-2 rounded border bg-gray-50 text-gray-700 border-gray-200">
                        <span className="font-mono uppercase text-[10px] font-semibold px-1 py-0.5 rounded bg-gray-100 text-gray-800">
                          observation
                        </span>
                        <p className="mt-1 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words">
                          {String(step.observation).substring(0, 500)}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </DetailSection>
          )}
        </div>
      </div>

      {/* Expandable full-width sections */}
      <div className="border-t border-gray-200">
        {/* Input section */}
        <div className="border-b border-gray-100">
          <button
            onClick={() => setInputExpanded(!inputExpanded)}
            className="w-full px-5 py-2.5 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <span className="text-sm font-medium text-gray-700">Input Snapshot</span>
            <svg className={`w-4 h-4 text-gray-400 transition-transform ${inputExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {inputExpanded && (
            <div className="px-5 pb-4">
              {stage.input_state_keys && stage.input_state_keys.length > 0 && (
                <div className="mb-2">
                  <span className="text-xs text-gray-500">State keys read:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {stage.input_state_keys.map(key => (
                      <span key={key} className="text-xs bg-gray-100 px-2 py-0.5 rounded">{key}</span>
                    ))}
                  </div>
                </div>
              )}
              <JsonViewerCompact data={stage.input_snapshot} />
            </div>
          )}
        </div>

        {/* Logs section */}
        <div>
          <button
            onClick={() => setLogsExpanded(!logsExpanded)}
            className="w-full px-5 py-2.5 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <span className="text-sm font-medium text-gray-700">Logs</span>
            <svg className={`w-4 h-4 text-gray-400 transition-transform ${logsExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {logsExpanded && (
            <div className="px-5 pb-4 max-h-80 overflow-y-auto">
              {loadingLogs ? (
                <div className="text-center py-4">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2" />
                  <p className="text-xs text-gray-500">Loading logs...</p>
                </div>
              ) : logs.length > 0 ? (
                <div className="space-y-1">
                  {logs.map(log => (
                    <div key={log.id} className={`text-xs p-2 rounded border ${
                      log.level === 'error' ? 'bg-red-50 border-red-200 text-red-700'
                      : log.level === 'warn' || log.level === 'warning' ? 'bg-yellow-50 border-yellow-200 text-yellow-700'
                      : 'bg-gray-50 border-gray-200 text-gray-700'
                    }`}>
                      <div className="flex justify-between items-start mb-0.5">
                        <span className={`font-mono uppercase text-[10px] font-semibold px-1 py-0.5 rounded ${
                          log.level === 'error' ? 'bg-red-100 text-red-800'
                          : log.level === 'warn' || log.level === 'warning' ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                        }`}>{log.level}</span>
                        <span className="text-gray-400 text-[10px]">{new Date(log.timestamp).toLocaleTimeString()}</span>
                      </div>
                      <p className="font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words">{log.message}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500 text-center py-4">No logs available</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Inferred/pending stage info */}
      {(stage.id?.startsWith('inferred-') || stage.id?.startsWith('pending-')) && (
        <div className="px-5 py-3 bg-yellow-50 border-t border-yellow-200">
          <p className="text-xs text-yellow-800">
            {stage.status === 'success'
              ? 'Stage data not recorded. The pipeline completed but this stage\'s execution data was not saved.'
              : 'This stage has not executed yet.'}
          </p>
        </div>
      )}
    </div>
  )
}

// --- Helper Components ---

function DetailSection({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 mb-2 group"
      >
        <svg className={`w-3 h-3 text-gray-400 transition-transform ${open ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <h3 className="text-sm font-medium text-gray-900 group-hover:text-blue-600">{title}</h3>
      </button>
      {open && <div className="space-y-1 pl-4">{children}</div>}
    </div>
  )
}

function DetailRow({ label, value, className = '' }: { label: string; value: string; className?: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className={`font-medium ${className || 'text-gray-900'}`}>{value}</span>
    </div>
  )
}

function JsonViewerCompact({ data }: { data?: Record<string, unknown> | null }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  if (!data || Object.keys(data).length === 0) {
    return <p className="text-xs text-gray-500 text-center py-2">No data</p>
  }

  const jsonString = JSON.stringify(data, null, 2)
  const isLarge = jsonString.length > 500

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50 border-b">
        <span className="text-xs text-gray-500">JSON</span>
        <div className="flex items-center gap-2">
          {isLarge && (
            <button onClick={() => setExpanded(!expanded)} className="text-xs text-blue-600 hover:text-blue-800">
              {expanded ? 'Collapse' : 'Expand'}
            </button>
          )}
          <button
            onClick={() => { navigator.clipboard.writeText(jsonString); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>
      <pre className={`p-3 text-xs overflow-auto font-mono bg-gray-50 ${expanded ? 'max-h-[400px]' : 'max-h-32'}`}>
        {jsonString}
      </pre>
    </div>
  )
}

// Inline agent output renderer - uses simple renderers for common agents
function AgentOutputInline({ stageName, output }: { stageName: string; output?: Record<string, unknown> | null }) {
  if (!output) {
    return <p className="text-xs text-gray-500 text-center py-3">No output data</p>
  }

  // Show output state keys if available
  const stateKeys = output._output_state_keys as string[] | undefined

  return (
    <div className="space-y-3">
      {stateKeys && stateKeys.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {stateKeys.map(key => (
            <span key={key} className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">{key}</span>
          ))}
        </div>
      )}
      <JsonViewerCompact data={output} />
    </div>
  )
}

// Extract tool calls from various output formats
function extractToolCalls(output?: Record<string, unknown> | null): ToolCall[] {
  if (!output) return []
  const toolCalls: ToolCall[] = []

  // Direct tool_calls array
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

  // API calls (Serper, etc.)
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

  // React trace tool calls
  if (output._react_trace && Array.isArray(output._react_trace)) {
    const traceSteps = output._react_trace as Array<Record<string, unknown>>
    traceSteps.filter(s => s.action).forEach(s => {
      const action = s.action as { name?: string; arguments?: Record<string, unknown> } | null
      toolCalls.push({
        name: action?.name || 'unknown',
        arguments: action?.arguments,
        result: s.observation,
        status: s.observation !== undefined ? 'success' as const : 'pending' as const,
        latency_ms: undefined,
        timestamp: undefined,
      })
    })
  }

  // Tool metrics
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

  return toolCalls
}
