'use client'

import { useState, useEffect, useRef, useCallback, use } from 'react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { PipelineRun, StageExecution } from '@/components/pipeline'
import { RetryBreadcrumb } from '@/components/pipeline/RetryBreadcrumb'
import { Skeleton } from '@/components/ui/skeleton'

// Lazy load heavy components for better code splitting
const PipelineView = dynamic(
  () => import('@/components/pipeline').then(mod => ({ default: mod.PipelineView })),
  {
    loading: () => (
      <div className="space-y-4 p-6">
        <div className="flex items-center gap-4 mb-6">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-6 w-48" />
        </div>
        <Skeleton className="h-96 w-full rounded-xl mt-6" />
        <p className="text-center text-sm text-muted-foreground">Loading pipeline visualization...</p>
      </div>
    ),
    ssr: false,
  }
)

const StagePanel = dynamic(
  () => import('@/components/pipeline/StagePanel').then(mod => ({ default: mod.StagePanel })),
  { ssr: false }
)

const LiveReasoningPanel = dynamic(
  () => import('@/components/pipeline').then(mod => ({ default: mod.LiveReasoningPanel })),
  { ssr: false }
)

// Load verification utilities for browser console
if (typeof window !== 'undefined') {
  import('@/app/api/verification/retry-checks').then(module => {
    (window as unknown as { verifyRetryFixes: typeof module }).verifyRetryFixes = module
    console.log('Retry verification utilities loaded! Use verifyRetryFixes.all(runId) in console.')
  }).catch(() => {
    // Silently fail if module not found
  })
}

export default function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: runId } = use(params)
  const [run, setRun] = useState<PipelineRun | null>(null)
  const [stages, setStages] = useState<StageExecution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedStage, setSelectedStage] = useState<StageExecution | null>(null)
  const [headerExpanded, setHeaderExpanded] = useState(false)
  const [liveCollapsed, setLiveCollapsed] = useState(false)
  const [liveSteps, setLiveSteps] = useState<Record<string, Array<{ type: 'thought' | 'action' | 'observation' | 'decision'; content: string; timestamp: string }>>>({})
  const stageDetailRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fetchRun = async () => {
      try {
        const response = await fetch(`/api/observability/runs/${runId}`)

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          throw new Error(errorData.error || `HTTP ${response.status}: Failed to fetch run`)
        }

        const data = await response.json()

        if (!data || !data.id) {
          throw new Error('Invalid run data received')
        }

        setRun(data)
        setStages(data.stages || [])
        setLoading(false)
      } catch (err) {
        console.error('[RunDetailPage] Error fetching run:', err)
        setError(err instanceof Error ? err.message : 'Unknown error')
        setLoading(false)
      }
    }

    if (runId) {
      fetchRun()
    } else {
      setError('No run ID provided')
      setLoading(false)
    }
  }, [runId])

  // SSE connection state (declared before polling so ref is available)
  const sseConnectedRef = useRef(false)

  // REST polling fallback — only active when SSE is NOT connected
  useEffect(() => {
    if (!runId || !run || run.status !== 'running') {
      return
    }

    const interval = setInterval(async () => {
      // Skip polling when SSE is connected to avoid race conditions
      if (sseConnectedRef.current) return

      try {
        const response = await fetch(`/api/observability/runs/${runId}`)
        if (response.ok) {
          const data = await response.json()
          if (data && data.id) {
            setRun(data)
            setStages(data.stages || [])
          }
        }
      } catch (err) {
        console.error('[RunDetailPage] Error polling run:', err)
      }
    }, 2000) // 2s fallback interval when SSE is down

    return () => clearInterval(interval)
  }, [runId, run?.status])

  // SSE for live updates when pipeline is running
  useEffect(() => {
    if (!runId || !run || run.status !== 'running') {
      sseConnectedRef.current = false
      return
    }

    let eventSource: EventSource | null = null
    try {
      eventSource = new EventSource(`/api/observability/runs/${runId}/stream`)

      // Handle stage/run updates (backend sends named event: update)
      eventSource.addEventListener('update', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)
          sseConnectedRef.current = true
          if (data.stages) setStages(data.stages)
          if (data.run) setRun(prev => prev ? { ...prev, ...data.run } : prev)
        } catch {
          // Ignore parse errors
        }
      })

      // Handle live reasoning steps (backend sends named event: live_step)
      eventSource.addEventListener('live_step', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)
          if (data.stage_name && data.step_type && data.content) {
            const stepType = data.step_type as 'thought' | 'action' | 'observation' | 'decision'
            setLiveSteps(prev => ({
              ...prev,
              [data.stage_name]: [
                ...(prev[data.stage_name] || []).slice(-50),
                { type: stepType, content: data.content, timestamp: new Date().toISOString() }
              ]
            }))
          }
        } catch {
          // Ignore parse errors
        }
      })

      // Handle completion (backend sends named event: complete)
      eventSource.addEventListener('complete', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)
          if (data.stages) setStages(data.stages)
          setRun(prev => prev ? { ...prev, status: data.status || 'success' } : prev)
        } catch {
          // Ignore parse errors
        }
        eventSource?.close()
      })

      // Handle errors
      eventSource.addEventListener('error', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)
          console.error('[SSE] Error event:', data.error)
        } catch {
          // Connection error, not a named error event
        }
      })

      eventSource.onerror = () => {
        sseConnectedRef.current = false
        eventSource?.close()
      }
    } catch {
      // SSE not available
    }

    return () => {
      sseConnectedRef.current = false
      eventSource?.close()
    }
  }, [runId, run?.status])

  const handleRetry = async (runIdToRetry: string, stageName: string): Promise<void> => {
    try {
      const response = await fetch(`/api/observability/runs/${runIdToRetry}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_stage: stageName })
      })

      if (response.ok) {
        const data = await response.json()
        if (data.new_run_id) {
          window.location.href = `/pipeline/runs/${data.new_run_id}`
        } else {
          throw new Error('Retry started but no new run ID returned')
        }
      } else {
        let errorMessage = 'Failed to retry pipeline'
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorData.error || errorData.message || errorMessage
        } catch {
          errorMessage = response.statusText || `HTTP ${response.status}: Failed to retry`
        }
        throw new Error(errorMessage)
      }
    } catch (err) {
      if (err instanceof Error) {
        throw err
      }
      throw new Error('An unexpected error occurred while retrying')
    }
  }

  // Scroll stage detail section into view when a stage is selected
  const handleSelectStage = useCallback((stage: StageExecution | null) => {
    setSelectedStage(stage)
    if (stage && stageDetailRef.current) {
      setTimeout(() => {
        stageDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 100)
    }
  }, [])

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-[#0770A2] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading pipeline run...</p>
        </div>
      </div>
    )
  }

  if (error || !run) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load Run</h2>
          <p className="text-red-600 mb-6">{error || 'Run not found'}</p>
          <div className="flex flex-col gap-3">
            <Link
              href="/games"
              className="px-6 py-3 bg-[#0770A2] text-white rounded-xl hover:bg-[#055A7D] transition-colors font-medium"
            >
              Back to Games
            </Link>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors font-medium"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  const formatDuration = (ms: number | null) => {
    if (ms === null) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-700 border-green-200'
      case 'failed': return 'bg-red-100 text-red-700 border-red-200'
      case 'running': return 'bg-blue-100 text-blue-700 border-blue-200'
      case 'degraded': return 'bg-orange-100 text-orange-700 border-orange-200'
      default: return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  return (
    <div className="w-full max-w-[1600px] mx-auto px-4 py-6 space-y-4">
      {/* Navigation Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm">
        <Link href="/games" className="text-gray-500 hover:text-[#0770A2] transition-colors">
          Games
        </Link>
        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        {run.process_id && (
          <>
            <Link href={`/game/${run.process_id}`} className="text-gray-500 hover:text-[#0770A2] transition-colors">
              Game
            </Link>
            <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </>
        )}
        <span className="text-gray-900 font-medium">Run #{run.run_number}</span>
      </nav>

      {/* Retry Chain Breadcrumb */}
      <RetryBreadcrumb
        currentRunId={run.id}
        currentRunNumber={run.run_number}
        parentRunId={run.parent_run_id}
        retryDepth={run.retry_depth}
      />

      {/* Compact Header Bar */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {/* Summary row — always visible */}
        <div className="px-6 py-4 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4 min-w-0">
            <h1 className="text-lg font-bold text-gray-900 whitespace-nowrap">
              Run #{run.run_number}
            </h1>
            <span className={`px-2.5 py-1 rounded-lg text-xs font-medium border flex-shrink-0 ${getStatusColor(run.status)}`}>
              {run.status}
            </span>
            <p className="text-sm text-gray-500 truncate max-w-md hidden md:block">
              {run.question_text || 'No question text'}
            </p>
          </div>

          <div className="flex items-center gap-4 flex-shrink-0">
            {/* Key metrics inline */}
            {run.total_cost_usd !== undefined && (
              <span className="text-xs font-mono text-green-600" title="Total cost">
                ${(run.total_cost_usd ?? 0).toFixed(4)}
              </span>
            )}
            {run.total_tokens !== undefined && (
              <span className="text-xs font-mono text-gray-600" title="Total tokens">
                {(run.total_tokens ?? 0).toLocaleString()} tok
              </span>
            )}
            <span className="text-xs text-gray-500" title="Duration">
              {formatDuration(run.duration_ms)}
            </span>
            {run.process_id && (
              <Link
                href={`/game/${run.process_id}`}
                className="px-3 py-1.5 bg-[#58CC02] text-white rounded-lg hover:bg-[#46A302] transition-colors text-sm font-medium flex items-center gap-1"
              >
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
                Play
              </Link>
            )}
            <button
              onClick={() => setHeaderExpanded(!headerExpanded)}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
              title={headerExpanded ? 'Collapse details' : 'Expand details'}
            >
              <svg className={`w-4 h-4 text-gray-500 transition-transform ${headerExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Expandable metadata */}
        {headerExpanded && (
          <div className="px-6 pb-5 pt-0 border-t border-gray-100 space-y-4">
            {/* Question text on mobile */}
            <p className="text-sm text-gray-600 md:hidden">
              {run.question_text || 'No question text'}
            </p>

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <span className="text-xs text-gray-500 block mb-0.5">Topology</span>
                <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-lg ${
                  run.topology === 'T0' ? 'bg-purple-100 text-purple-700' : 'bg-[#E8F4F8] text-[#0770A2]'
                }`}>
                  {run.topology}
                </span>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-0.5">Duration</span>
                <p className="text-sm font-semibold text-gray-900">{formatDuration(run.duration_ms)}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-0.5">Started</span>
                <p className="text-sm text-gray-900">
                  {run.started_at ? new Date(run.started_at).toLocaleString() : '-'}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-0.5">Template</span>
                <p className="text-sm text-gray-900">{run.template_type?.replace(/_/g, ' ') || '-'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500 block mb-0.5">LLM Calls</span>
                <p className="text-sm font-mono text-gray-900">
                  {run.total_llm_calls ?? stages.filter(s => s.model_id).length}
                </p>
              </div>
            </div>

            {/* Retry info */}
            {run.retry_from_stage && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-sm">
                <svg className="w-4 h-4 text-amber-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span className="text-amber-800">
                  Retried from: <strong>{run.retry_from_stage.replace(/_/g, ' ')}</strong>
                </span>
              </div>
            )}

            {/* Error message */}
            {run.error_message && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <svg className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-red-800">Error</p>
                    <p className="text-red-700 text-xs mt-1">{run.error_message}</p>
                    {run.error_traceback && (
                      <pre className="mt-2 text-xs bg-red-100 p-2 rounded overflow-x-auto max-h-32 text-red-800">
                        {run.error_traceback}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Pipeline Graph + Stage Detail Sidebar */}
      <div className="flex gap-4">
        {/* Graph */}
        <div className={`bg-white rounded-xl border border-gray-200 overflow-hidden ${selectedStage ? 'flex-1 min-w-0' : 'w-full'}`}>
          <PipelineView
            run={run}
            stages={stages}
            onRetry={handleRetry}
            onSelectStage={handleSelectStage}
          />
        </div>

        {/* Stage Detail Sidebar */}
        {selectedStage && (
          <div ref={stageDetailRef} className="w-[560px] flex-shrink-0">
            <StagePanel
              stage={{ ...selectedStage, run_id: run.id }}
              onRetry={
                (selectedStage.status === 'failed' || selectedStage.status === 'degraded' || selectedStage.stage_name === 'human_review')
                  ? async (stageName: string) => { await handleRetry(run.id, stageName) }
                  : undefined
              }
              onClose={() => setSelectedStage(null)}
            />
          </div>
        )}
      </div>

      {/* Live Activity — only visible when running */}
      {run.status === 'running' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div
            className="px-4 py-2 border-b border-gray-100 bg-gray-50 flex items-center justify-between cursor-pointer"
            onClick={() => setLiveCollapsed(!liveCollapsed)}
          >
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium text-gray-700">Live Activity</span>
              <span className="text-xs text-gray-400">
                {stages.filter(s => s.status === 'running').map(s => s.stage_name.replace(/_/g, ' ')).join(', ') || 'processing...'}
              </span>
            </div>
            <svg className={`w-4 h-4 text-gray-400 transition-transform ${liveCollapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
          {!liveCollapsed && (
            <div className="h-64 overflow-y-auto">
              <LiveReasoningPanel
                liveSteps={liveSteps}
                currentStage={stages.find(s => s.status === 'running')?.stage_name}
                maxHeight="256px"
              />
            </div>
          )}
        </div>
      )}

      {/* Child Runs (retries) */}
      {run.child_runs && run.child_runs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-3 border-b border-gray-100 bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-900">Retry Runs</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {run.child_runs.map(child => (
              <Link
                key={child.id}
                href={`/pipeline/runs/${child.id}`}
                className="flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-lg border ${getStatusColor(child.status)}`}>
                    {child.status}
                  </span>
                  <span className="font-medium text-sm text-gray-900">Run #{child.run_number}</span>
                  {child.retry_from_stage && (
                    <span className="text-xs text-gray-500">
                      from {child.retry_from_stage.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">
                    {child.started_at ? new Date(child.started_at).toLocaleString() : '-'}
                  </span>
                  <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
