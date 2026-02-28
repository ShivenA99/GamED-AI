'use client'

import { useState, useEffect, useCallback } from 'react'
import { PipelineRun, StageExecution, RunUpdateEvent, LiveStep, LiveStepEvent } from './types'
import { PipelineView, PipelineProgressBar } from './PipelineView'
import { LiveReasoningPanel, LiveReasoningSummary } from './LiveReasoningPanel'

interface LivePipelineViewProps {
  runId: string
  onComplete?: (run: PipelineRun) => void
  onCancel?: () => void
  compact?: boolean
}

// Metrics state for tracking tokens and cost
interface LiveMetrics {
  totalTokens: number
  totalCostUsd: number
}

// Live steps grouped by stage
interface LiveStepsState {
  [stageName: string]: LiveStep[]
}

export function LivePipelineView({
  runId,
  onComplete,
  onCancel,
  compact = false,
}: LivePipelineViewProps) {
  const [run, setRun] = useState<PipelineRun | null>(null)
  const [stages, setStages] = useState<StageExecution[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  // New state for metrics and live steps
  const [metrics, setMetrics] = useState<LiveMetrics>({ totalTokens: 0, totalCostUsd: 0 })
  const [liveSteps, setLiveSteps] = useState<LiveStepsState>({})

  // Fetch initial run data
  useEffect(() => {
    const fetchRun = async () => {
      try {
        const response = await fetch(`/api/observability/runs/${runId}`)
        if (!response.ok) throw new Error('Failed to fetch run')
        const data = await response.json()
        setRun(data)
        setStages(data.stages || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      }
    }

    fetchRun()
  }, [runId])

  // Connect to SSE stream for live updates
  useEffect(() => {
    if (!runId) return

    const eventSource = new EventSource(`/api/observability/runs/${runId}/stream`)

    eventSource.onopen = () => {
      setIsConnected(true)
    }

    eventSource.addEventListener('update', (event) => {
      const data: RunUpdateEvent = JSON.parse(event.data)

      setRun(prev => prev ? {
        ...prev,
        status: data.status as PipelineRun['status'],
        duration_ms: data.duration_ms,
        // Update aggregate metrics
        total_tokens: data.total_tokens,
        total_cost_usd: data.total_cost_usd,
      } : null)

      // Update metrics state
      if (data.total_tokens !== undefined || data.total_cost_usd !== undefined) {
        setMetrics({
          totalTokens: data.total_tokens || 0,
          totalCostUsd: data.total_cost_usd || 0,
        })
      }

      // Update stages from the event with per-stage metrics
      setStages(data.stages.map((s, i) => ({
        id: `${runId}-${s.stage_name}`,
        stage_name: s.stage_name,
        stage_order: i + 1,
        status: s.status as StageExecution['status'],
        duration_ms: s.duration_ms,
        started_at: null,
        finished_at: null,
        // Per-stage metrics from SSE (NEW)
        model_id: s.model_id || null,
        prompt_tokens: null,
        completion_tokens: null,
        total_tokens: s.tokens || null,
        estimated_cost_usd: s.cost || null,
        latency_ms: null,
        error_message: null,
        retry_count: 0,
        validation_passed: null,
        validation_score: null,
      })))
    })

    // Handle live_step events for streaming reasoning steps (NEW)
    eventSource.addEventListener('live_step', (event) => {
      const data: LiveStepEvent = JSON.parse(event.data)

      setLiveSteps(prev => {
        const stageName = data.stage_name
        const existingSteps = prev[stageName] || []
        // Avoid duplicates by checking content
        const isDuplicate = existingSteps.some(
          step => step.content === data.step.content && step.type === data.step.type
        )
        if (isDuplicate) {
          return prev
        }
        return {
          ...prev,
          [stageName]: [...existingSteps, data.step]
        }
      })
    })

    eventSource.addEventListener('complete', (event) => {
      const data = JSON.parse(event.data)
      setRun(prev => prev ? {
        ...prev,
        status: data.status,
        duration_ms: data.duration_ms,
        error_message: data.error_message,
        // Final metrics from complete event
        total_tokens: data.total_tokens,
        total_cost_usd: data.total_cost_usd,
      } : null)

      // Update final metrics
      if (data.total_tokens !== undefined || data.total_cost_usd !== undefined) {
        setMetrics({
          totalTokens: data.total_tokens || 0,
          totalCostUsd: data.total_cost_usd || 0,
        })
      }

      // Fetch final state
      fetch(`/api/observability/runs/${runId}`)
        .then(res => res.json())
        .then(fullRun => {
          setRun(fullRun)
          setStages(fullRun.stages || [])
          if (onComplete) {
            onComplete(fullRun)
          }
        })

      eventSource.close()
    })

    eventSource.onerror = () => {
      setIsConnected(false)
      // Try to reconnect after a delay
      setTimeout(() => {
        // Refetch run status
        fetch(`/api/observability/runs/${runId}`)
          .then(res => res.json())
          .then(data => {
            setRun(data)
            setStages(data.stages || [])
          })
      }, 2000)
    }

    return () => {
      eventSource.close()
    }
  }, [runId, onComplete])

  if (error) {
    return (
      <div className="p-4 bg-red-50 rounded-lg">
        <p className="text-red-700">Error: {error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 text-sm text-red-600 underline"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!run) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  // Helper to format cost
  const formatCost = (cost: number) => {
    if (cost < 0.01) return `$${cost.toFixed(6)}`
    if (cost < 1) return `$${cost.toFixed(4)}`
    return `$${cost.toFixed(2)}`
  }

  // Helper to format token count
  const formatTokens = (tokens: number) => {
    if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`
    return tokens.toString()
  }

  if (compact) {
    return (
      <div className="p-4 bg-white rounded-lg border">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-gray-900">Pipeline Progress</h3>
          <div className="flex items-center gap-3">
            {/* Compact metrics display */}
            {metrics.totalTokens > 0 && (
              <span className="text-xs text-gray-500">
                {formatTokens(metrics.totalTokens)} tokens
              </span>
            )}
            {metrics.totalCostUsd > 0 && (
              <span className="text-xs text-gray-500">
                {formatCost(metrics.totalCostUsd)}
              </span>
            )}
            {!isConnected && run.status === 'running' && (
              <span className="text-xs text-yellow-600">Reconnecting...</span>
            )}
          </div>
        </div>
        <PipelineProgressBar run={run} stages={stages} />

        {/* Live reasoning summary in compact mode */}
        {run.status === 'running' && Object.keys(liveSteps).length > 0 && (
          <div className="mt-3">
            <LiveReasoningSummary
              liveSteps={liveSteps}
              currentStage={stages.find(s => s.status === 'running')?.stage_name}
            />
          </div>
        )}

        {onCancel && run.status === 'running' && (
          <button
            onClick={onCancel}
            className="mt-4 w-full py-2 text-sm text-gray-600 hover:text-gray-900 border rounded-lg"
          >
            Cancel
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border shadow-sm h-[600px] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Pipeline Run #{run.run_number}
          </h2>
          <p className="text-sm text-gray-500">
            Topology: {run.topology} | Status: {run.status}
            {/* Inline metrics */}
            {metrics.totalTokens > 0 && (
              <span className="ml-2">| {formatTokens(metrics.totalTokens)} tokens</span>
            )}
            {metrics.totalCostUsd > 0 && (
              <span className="ml-1">| {formatCost(metrics.totalCostUsd)}</span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {!isConnected && run.status === 'running' && (
            <span className="text-xs text-yellow-600 flex items-center gap-1">
              <span className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
              Reconnecting...
            </span>
          )}

          {onCancel && run.status === 'running' && (
            <button
              onClick={onCancel}
              className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded border border-red-200"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Pipeline view */}
      <div className="flex-1 overflow-hidden">
        <PipelineView run={run} stages={stages} />
      </div>

      {/* Live reasoning panel - shown when running and steps available */}
      {run.status === 'running' && Object.keys(liveSteps).length > 0 && (
        <div className="border-t p-4">
          <LiveReasoningPanel
            liveSteps={liveSteps}
            currentStage={stages.find(s => s.status === 'running')?.stage_name}
            title="Agent Reasoning"
            maxHeight="200px"
            autoScroll={true}
          />
        </div>
      )}
    </div>
  )
}

// Simple version for showing generation progress
export function GenerationProgress({
  processId,
  onComplete,
}: {
  processId: string
  onComplete?: (success: boolean) => void
}) {
  const [status, setStatus] = useState<string>('pending')
  const [currentAgent, setCurrentAgent] = useState<string>('')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!processId) return

    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/status/${processId}`)
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.error || `HTTP ${response.status}: Failed to fetch status`)
        }
        const data = await response.json()

        // Map API response to component state
        // API returns: status, current_step, error (not current_agent, error_message)
        setStatus(data.status || 'pending')
        setCurrentAgent(data.current_step || '')
        // Progress not available from API, estimate based on status
        setProgress(data.status === 'completed' || data.status === 'success' ? 100 : data.status === 'failed' ? 0 : 50)

        if (data.status === 'completed' || data.status === 'success') {
          if (onComplete) onComplete(true)
        } else if (data.status === 'error' || data.status === 'failed') {
          setError(data.error || 'Generation failed')
          if (onComplete) onComplete(false)
        }
      } catch (err) {
        console.error('Error polling status:', err)
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch status'
        setError(errorMessage)
        setStatus('error')
      }
    }

    // Poll every 2 seconds
    const interval = setInterval(pollStatus, 2000)
    pollStatus() // Initial fetch

    return () => clearInterval(interval)
  }, [processId, onComplete])

  const formatAgentName = (name: string) => {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  return (
    <div className="p-6 bg-white rounded-xl border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-gray-900">Generating Game...</h3>
        <span className={`
          px-2 py-1 text-xs rounded-full
          ${status === 'processing' || status === 'running' ? 'bg-blue-100 text-blue-700' :
            status === 'completed' || status === 'success' ? 'bg-green-100 text-green-700' :
            status === 'error' || status === 'failed' ? 'bg-red-100 text-red-700' :
            'bg-gray-100 text-gray-700'}
        `}>
          {status}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-3">
        <div
          className={`h-full transition-all duration-500 ${
            status === 'error' || status === 'failed' ? 'bg-red-500' : 
            status === 'completed' || status === 'success' ? 'bg-green-500' :
            'bg-blue-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Current agent */}
      {currentAgent && (status === 'processing' || status === 'running') && (
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <svg className="w-4 h-4 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>{formatAgentName(currentAgent)}</span>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mt-3 p-3 bg-red-50 rounded-lg">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Success message */}
      {(status === 'completed' || status === 'success') && (
        <div className="flex items-center gap-2 text-green-600">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-sm font-medium">Generation complete!</span>
        </div>
      )}
    </div>
  )
}
