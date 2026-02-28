'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

interface PipelineRun {
  id: string
  process_id: string
  run_number: number
  topology: string
  status: string
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  error_message: string | null
  stages?: StageExecution[]
}

interface StageExecution {
  id: string
  stage_name: string
  stage_order: number
  status: string
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  model_id: string | null
  total_tokens: number | null
  estimated_cost_usd: number | null
  input_snapshot: unknown
  output_snapshot: unknown
  error_message: string | null
}

interface RunDetail {
  id: string
  process_id: string
  run_number: number
  topology: string
  status: string
  duration_ms: number | null
  started_at: string
  stages: StageExecution[]
  question_text?: string
  template_type?: string
}

export default function PipelinePage() {
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [selectedRuns, setSelectedRuns] = useState<string[]>([])
  const [runDetails, setRunDetails] = useState<Record<string, RunDetail>>({})
  const [loading, setLoading] = useState(true)
  const [expandedAgents, setExpandedAgents] = useState<Record<string, boolean>>({})
  const [filterTopology, setFilterTopology] = useState<string>('')

  useEffect(() => {
    fetchRuns()
  }, [filterTopology])

  const fetchRuns = async () => {
    try {
      let url = '/api/observability/runs?limit=50'
      if (filterTopology) {
        url += `&topology=${filterTopology}`
      }
      const response = await fetch(url)
      const data = await response.json()
      setRuns(data.runs || [])
    } catch (error) {
      console.error('Error fetching runs:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchRunDetail = async (runId: string) => {
    if (runDetails[runId]) return

    try {
      const response = await fetch(`/api/observability/runs/${runId}`)
      const data = await response.json()
      setRunDetails(prev => ({ ...prev, [runId]: data }))
    } catch (error) {
      console.error('Error fetching run detail:', error)
    }
  }

  const toggleRunSelection = async (runId: string) => {
    if (selectedRuns.includes(runId)) {
      setSelectedRuns(prev => prev.filter(id => id !== runId))
    } else {
      setSelectedRuns(prev => [...prev, runId])
      await fetchRunDetail(runId)
    }
  }

  const toggleAgent = (runId: string, agentName: string) => {
    const key = `${runId}-${agentName}`
    setExpandedAgents(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts)
    return date.toLocaleString()
  }

  const agentDisplayNames: Record<string, string> = {
    input_enhancer: 'Input Enhancer',
    domain_knowledge_retriever: 'Domain Knowledge',
    router: 'Template Router',
    game_planner: 'Game Planner',
    scene_generator: 'Scene Generator',
    diagram_image_retriever: 'Diagram Retriever',
    image_label_remover: 'Label Remover',
    sam3_prompt_generator: 'SAM3 Prompt Gen',
    diagram_image_segmenter: 'Image Segmenter',
    diagram_zone_labeler: 'Zone Labeler',
    blueprint_generator: 'Blueprint Generator',
    blueprint_validator: 'Blueprint Validator',
    diagram_spec_generator: 'Diagram Spec Gen',
    diagram_spec_validator: 'Diagram Spec Validator',
    diagram_svg_generator: 'SVG Generator',
    code_generator: 'Code Generator',
    code_verifier: 'Code Verifier',
    asset_generator: 'Asset Generator'
  }

  const getAgentIcon = (agentName: string): string => {
    const icons: Record<string, string> = {
      input_enhancer: '📝',
      domain_knowledge_retriever: '🔍',
      router: '🔀',
      game_planner: '🎮',
      scene_generator: '🎨',
      diagram_image_retriever: '🖼️',
      image_label_remover: '🧹',
      sam3_prompt_generator: '🎯',
      diagram_image_segmenter: '✂️',
      diagram_zone_labeler: '🏷️',
      blueprint_generator: '📐',
      blueprint_validator: '✅',
      diagram_spec_generator: '📋',
      diagram_spec_validator: '✓',
      diagram_svg_generator: '🎨',
      code_generator: '💻',
      code_verifier: '🔍',
      asset_generator: '📦'
    }
    return icons[agentName] || '⚙️'
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'bg-success-bg text-success dark:bg-success/20 border-success/30'
      case 'failed': return 'bg-error-bg text-error dark:bg-error/20 border-error/30'
      case 'running': return 'bg-info-bg text-info dark:bg-info/20 border-info/30'
      case 'degraded': return 'bg-warning-bg text-warning dark:bg-warning/20 border-warning/30'
      default: return 'bg-muted text-muted-foreground border-border'
    }
  }

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading pipeline runs...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Pipeline Comparison</h1>
          <p className="text-muted-foreground mt-1">Compare agent outputs across different topologies and runs</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={filterTopology}
            onChange={(e) => setFilterTopology(e.target.value)}
            className="px-4 py-2 border border-input rounded-xl text-sm bg-background text-foreground hover:border-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 transition-colors"
          >
            <option value="">All Topologies</option>
            <option value="T0">T0 - Sequential</option>
            <option value="T1">T1 - Validated</option>
          </select>
          <button
            onClick={fetchRuns}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-xl text-sm hover:bg-primary/90 transition-colors font-medium flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {runs.length === 0 ? (
        <div className="text-center py-16 bg-card rounded-2xl border border-border">
          <div className="w-20 h-20 bg-muted rounded-2xl flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl">📊</span>
          </div>
          <h3 className="text-xl font-semibold text-foreground mb-2">No pipeline runs found</h3>
          <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
            Generate a game to see pipeline execution data here.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 transition-colors font-medium"
          >
            Create a Game
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Runs List */}
          <div className="lg:col-span-1">
            <div className="bg-card rounded-xl border border-border overflow-hidden">
              <div className="px-5 py-4 border-b border-border bg-muted/50">
                <h2 className="font-semibold text-foreground">Pipeline Runs</h2>
                <p className="text-xs text-muted-foreground mt-0.5">Click to view agent outputs</p>
              </div>
              <div className="max-h-[600px] overflow-y-auto">
                {runs.map(run => {
                  const stageCount = run.stages?.length || 0
                  const isSelected = selectedRuns.includes(run.id)

                  return (
                    <div
                      key={run.id}
                      onClick={() => toggleRunSelection(run.id)}
                      className={`p-4 border-b border-border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-primary/10 border-l-4 border-l-primary'
                          : 'hover:bg-muted/50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`px-2 py-0.5 text-xs font-medium rounded-lg ${
                              run.topology === 'T0' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' : 'bg-primary/10 text-primary'
                            }`}>
                              {run.topology}
                            </span>
                            <span className={`px-2 py-0.5 text-xs font-medium rounded-lg border ${getStatusColor(run.status)}`}>
                              {run.status}
                            </span>
                          </div>
                          <p className="text-sm font-medium text-foreground truncate">
                            Run #{run.run_number}
                          </p>
                          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                            <span>{run.duration_ms ? formatDuration(run.duration_ms) : run.status === 'running' ? 'running...' : '-'}</span>
                            <span>{stageCount} stages</span>
                          </div>
                        </div>
                        <Link
                          href={`/pipeline/runs/${run.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs text-primary hover:text-primary/80 font-medium ml-2"
                        >
                          View
                        </Link>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Selected Run Details */}
          <div className="lg:col-span-2">
            {selectedRuns.length === 0 ? (
              <div className="bg-card rounded-xl border border-border p-12 text-center">
                <div className="w-16 h-16 bg-muted rounded-xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                  </svg>
                </div>
                <p className="text-foreground font-medium mb-1">Select a pipeline run</p>
                <p className="text-sm text-muted-foreground">Click on a run to view detailed stage outputs</p>
              </div>
            ) : (
              <div className="space-y-6">
                {selectedRuns.map(runId => {
                  const detail = runDetails[runId]
                  if (!detail) {
                    return (
                      <div key={runId} className="bg-card rounded-xl border border-border p-6">
                        <div className="animate-pulse space-y-3">
                          <div className="h-4 bg-muted rounded w-3/4"></div>
                          <div className="h-4 bg-muted rounded w-1/2"></div>
                        </div>
                      </div>
                    )
                  }

                  const stages = [...(detail.stages || [])].sort(
                    (a, b) => a.stage_order - b.stage_order
                  )

                  return (
                    <div key={runId} className="bg-card rounded-xl border border-border overflow-hidden">
                      {/* Run Header */}
                      <div className={`px-5 py-4 border-b ${
                        detail.status === 'success' ? 'bg-success-bg dark:bg-success/10 border-success/20' :
                        detail.status === 'failed' ? 'bg-error-bg dark:bg-error/10 border-error/20' :
                        detail.status === 'degraded' ? 'bg-warning-bg dark:bg-warning/10 border-warning/20' :
                        'bg-info-bg dark:bg-info/10 border-info/20'
                      }`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`px-2 py-0.5 text-xs font-medium rounded-lg ${
                                detail.topology === 'T0' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' : 'bg-card text-primary'
                              }`}>
                                {detail.topology}
                              </span>
                              <span className={`px-2 py-0.5 text-xs font-medium rounded-lg border ${getStatusColor(detail.status)}`}>
                                {detail.status}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                Run #{detail.run_number}
                              </span>
                            </div>
                            <p className="text-sm text-foreground">
                              Process: {detail.process_id.substring(0, 12)}...
                            </p>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium text-foreground">
                              {detail.duration_ms ? formatDuration(detail.duration_ms) : '-'}
                            </div>
                            <div className="text-xs text-muted-foreground">{formatTimestamp(detail.started_at)}</div>
                          </div>
                        </div>
                      </div>

                      {/* Stage Outputs */}
                      <div className="divide-y divide-border">
                        {stages.length === 0 ? (
                          <div className="p-6 text-center text-muted-foreground">
                            No stage data available
                          </div>
                        ) : stages.map(stage => {
                          const isExpanded = expandedAgents[`${runId}-${stage.stage_name}`]

                          return (
                            <div key={stage.id}>
                              <button
                                onClick={() => toggleAgent(runId, stage.stage_name)}
                                className="w-full px-5 py-4 flex items-center justify-between hover:bg-muted/50 transition-colors"
                              >
                                <div className="flex items-center gap-3">
                                  <span className="text-xl">{getAgentIcon(stage.stage_name)}</span>
                                  <div className="text-left">
                                    <div className="flex items-center gap-2">
                                      <span className="font-medium text-foreground">
                                        {agentDisplayNames[stage.stage_name] || stage.stage_name}
                                      </span>
                                      <span className={`text-[10px] px-1.5 py-0.5 rounded-lg font-medium border ${getStatusColor(stage.status)}`}>
                                        {stage.status}
                                      </span>
                                    </div>
                                    <div className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                                      {stage.duration_ms && <span>{formatDuration(stage.duration_ms)}</span>}
                                      {stage.model_id && (
                                        <span className="font-mono bg-muted px-1.5 py-0.5 rounded text-[10px]">
                                          {stage.model_id.split('/').pop()}
                                        </span>
                                      )}
                                      {stage.total_tokens && <span>{stage.total_tokens.toLocaleString()} tokens</span>}
                                    </div>
                                  </div>
                                </div>
                                <svg
                                  className={`w-5 h-5 text-muted-foreground transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                              </button>

                              {isExpanded && (
                                <div className="px-5 py-4 bg-muted/50 border-t border-border space-y-4">
                                  {stage.error_message && (
                                    <div className="bg-error-bg dark:bg-error/10 border border-error/30 rounded-lg p-3 text-sm text-error">
                                      <strong>Error:</strong> {stage.error_message}
                                    </div>
                                  )}
                                  {stage.input_snapshot != null ? (
                                    <div>
                                      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Input</h4>
                                      <pre className="text-xs overflow-x-auto p-3 bg-card rounded-lg border border-border max-h-48 overflow-y-auto text-foreground">
                                        {JSON.stringify(stage.input_snapshot as Record<string, unknown>, null, 2)}
                                      </pre>
                                    </div>
                                  ) : null}
                                  {stage.output_snapshot != null ? (
                                    <div>
                                      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Output</h4>
                                      <pre className="text-xs overflow-x-auto p-3 bg-card rounded-lg border border-border max-h-48 overflow-y-auto text-foreground">
                                        {JSON.stringify(stage.output_snapshot as Record<string, unknown>, null, 2)}
                                      </pre>
                                    </div>
                                  ) : null}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>

                      {/* Quick actions */}
                      <div className="border-t border-border px-5 py-4 bg-muted/50">
                        <Link
                          href={`/pipeline/runs/${runId}`}
                          className="text-sm text-primary hover:text-primary/80 font-medium flex items-center gap-1.5 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                          </svg>
                          Open Full Run Dashboard
                        </Link>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
