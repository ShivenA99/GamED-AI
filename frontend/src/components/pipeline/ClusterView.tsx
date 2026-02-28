'use client'

import React, { useState } from 'react'
import { ClusterDefinition, StageExecution } from './types'

interface ClusterViewProps {
  cluster: ClusterDefinition
  stages: StageExecution[]
  onSelectStage: (stage: StageExecution) => void
  selectedStageName?: string
  isExpanded?: boolean
  onToggle?: () => void
}

// Helper to format duration
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}

// Helper to get cluster status from stages
function getClusterStatus(stages: StageExecution[]): 'pending' | 'running' | 'success' | 'failed' | 'degraded' {
  if (stages.length === 0) return 'pending'

  const hasRunning = stages.some(s => s.status === 'running')
  if (hasRunning) return 'running'

  const hasFailed = stages.some(s => s.status === 'failed')
  if (hasFailed) return 'failed'

  const hasDegraded = stages.some(s => s.status === 'degraded')
  if (hasDegraded) return 'degraded'

  const allSuccess = stages.every(s => s.status === 'success' || s.status === 'skipped')
  if (allSuccess && stages.length > 0) return 'success'

  return 'pending'
}

// Status colors
const STATUS_COLORS = {
  pending: { dot: 'bg-gray-400', ring: 'ring-gray-200' },
  running: { dot: 'bg-blue-500 animate-pulse', ring: 'ring-blue-200' },
  success: { dot: 'bg-green-500', ring: 'ring-green-200' },
  failed: { dot: 'bg-red-500', ring: 'ring-red-200' },
  degraded: { dot: 'bg-orange-500', ring: 'ring-orange-200' },
  skipped: { dot: 'bg-gray-300', ring: 'ring-gray-100' },
}

export function ClusterView({
  cluster,
  stages,
  onSelectStage,
  selectedStageName,
  isExpanded = true,
  onToggle,
}: ClusterViewProps) {
  const [localExpanded, setLocalExpanded] = useState(isExpanded)
  const expanded = onToggle ? isExpanded : localExpanded

  // Filter stages that belong to this cluster
  const clusterStages = stages.filter(s => cluster.agents.includes(s.stage_name))

  // Calculate totals
  const totalDuration = clusterStages.reduce((sum, s) => sum + (s.duration_ms || 0), 0)
  const totalTokens = clusterStages.reduce((sum, s) => sum + (s.total_tokens || 0), 0)
  const status = getClusterStatus(clusterStages)
  const statusStyle = STATUS_COLORS[status]

  const handleToggle = () => {
    if (onToggle) {
      onToggle()
    } else {
      setLocalExpanded(!localExpanded)
    }
  }

  return (
    <div
      className={`border-2 rounded-xl overflow-hidden transition-all duration-200 ${
        expanded ? 'shadow-md' : 'shadow-sm'
      }`}
      style={{ borderColor: cluster.color + '40' }}
    >
      {/* Cluster Header */}
      <button
        onClick={handleToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
        style={{ backgroundColor: cluster.color + '10' }}
      >
        <div className="flex items-center gap-3">
          {/* Status indicator */}
          <div className={`w-3 h-3 rounded-full ${statusStyle.dot}`} />

          {/* Cluster name */}
          <div className="text-left">
            <h3 className="font-semibold text-gray-900">{cluster.name}</h3>
            {cluster.description && (
              <p className="text-xs text-gray-500 mt-0.5">{cluster.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Stats */}
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span>{clusterStages.length} agent{clusterStages.length !== 1 ? 's' : ''}</span>
            {totalDuration > 0 && (
              <>
                <span className="text-gray-300">|</span>
                <span>{formatDuration(totalDuration)}</span>
              </>
            )}
            {totalTokens > 0 && (
              <>
                <span className="text-gray-300">|</span>
                <span>{totalTokens.toLocaleString()} tokens</span>
              </>
            )}
          </div>

          {/* Expand/collapse icon */}
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
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

      {/* Cluster Content */}
      {expanded && (
        <div className="p-4 bg-white">
          {clusterStages.length === 0 ? (
            <div className="text-center py-4 text-gray-500 text-sm">
              No stages executed yet
            </div>
          ) : (
            <div className={`space-y-2 ${cluster.layout === 'horizontal' ? 'flex gap-2 flex-wrap' : ''}`}>
              {clusterStages.map(stage => (
                <AgentMiniCard
                  key={stage.id}
                  stage={stage}
                  isSelected={stage.stage_name === selectedStageName}
                  onClick={() => onSelectStage(stage)}
                  clusterColor={cluster.color}
                  horizontal={cluster.layout === 'horizontal'}
                />
              ))}
            </div>
          )}

          {/* Show tool indicators if configured */}
          {cluster.showTools && clusterStages.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <span className="text-xs text-gray-500 font-medium">Tools Used:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {getToolsUsed(clusterStages).map(tool => (
                  <span key={tool} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                    {tool}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Show retry loop indicator if configured */}
          {cluster.showRetryLoop && (
            <RetryLoopIndicator stages={clusterStages} />
          )}
        </div>
      )}
    </div>
  )
}

// Mini card for agent within cluster
function AgentMiniCard({
  stage,
  isSelected,
  onClick,
  clusterColor,
  horizontal,
}: {
  stage: StageExecution
  isSelected: boolean
  onClick: () => void
  clusterColor: string
  horizontal?: boolean
}) {
  const statusStyle = STATUS_COLORS[stage.status] || STATUS_COLORS.pending

  return (
    <button
      onClick={onClick}
      className={`
        text-left p-3 rounded-lg border transition-all
        ${horizontal ? 'flex-1 min-w-[150px]' : 'w-full'}
        ${isSelected
          ? 'border-blue-400 bg-blue-50 ring-2 ring-blue-200'
          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
        }
      `}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${statusStyle.dot}`} />
          <span className="text-sm font-medium text-gray-900">
            {formatStageName(stage.stage_name)}
          </span>
        </div>
        {stage.retry_count > 0 && (
          <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">
            {stage.retry_count} retry
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 mt-1.5 text-xs text-gray-500">
        {stage.duration_ms && (
          <span>{formatDuration(stage.duration_ms)}</span>
        )}
        {stage.model_id && (
          <>
            <span className="text-gray-300">|</span>
            <span className="truncate max-w-[100px]" title={stage.model_id}>
              {stage.model_id.split('/').pop() || stage.model_id}
            </span>
          </>
        )}
      </div>
    </button>
  )
}

// Retry loop visualization
function RetryLoopIndicator({ stages }: { stages: StageExecution[] }) {
  const totalRetries = stages.reduce((sum, s) => sum + (s.retry_count || 0), 0)

  if (totalRetries === 0) return null

  return (
    <div className="mt-3 pt-3 border-t border-gray-100">
      <div className="flex items-center gap-2 text-xs">
        <svg className="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        <span className="text-orange-600 font-medium">
          {totalRetries} validation retry attempt{totalRetries !== 1 ? 's' : ''}
        </span>
      </div>
    </div>
  )
}

// Helper to format stage names
function formatStageName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// Extract tools used from stage output metadata
function getToolsUsed(stages: StageExecution[]): string[] {
  const tools = new Set<string>()

  stages.forEach(stage => {
    // Try to extract from output snapshot
    const output = stage.output_snapshot as Record<string, unknown> | undefined
    if (output) {
      // Look for trace info
      const trace = (output.detection_trace || output.design_trace) as Array<{ steps?: Array<{ tool?: string }> }> | undefined
      if (Array.isArray(trace)) {
        trace.forEach(t => {
          if (t.steps) {
            t.steps.forEach(step => {
              if (step.tool) tools.add(step.tool)
            })
          }
        })
      }

      // Look for metadata with tool info
      const metadata = (output.zone_detection_metadata || output.design_metadata) as Record<string, unknown> | undefined
      if (metadata?.tools_used) {
        const toolsUsed = metadata.tools_used as string[]
        toolsUsed.forEach(t => tools.add(t))
      }
    }
  })

  return Array.from(tools)
}

// Export the cluster layout definition for HAD architecture
export const HAD_CLUSTER_LAYOUT: ClusterDefinition[] = [
  {
    id: 'research',
    name: 'Research Cluster',
    description: 'Input processing and domain knowledge retrieval',
    color: '#8B5CF6',
    agents: ['input_enhancer', 'domain_knowledge_retriever', 'router'],
    layout: 'horizontal',
  },
  {
    id: 'vision',
    name: 'Vision Cluster',
    description: 'Image acquisition and zone detection with reasoning',
    color: '#06B6D4',
    agents: ['zone_planner'],
    layout: 'single',
    showTools: true,
  },
  {
    id: 'design',
    name: 'Design Cluster',
    description: 'Game planning and scene design orchestration',
    color: '#F59E0B',
    agents: ['game_orchestrator'],
    layout: 'single',
    showTools: true,
    showSubPipeline: true,
  },
  {
    id: 'output',
    name: 'Output Cluster',
    description: 'Blueprint generation with validation retry loop',
    color: '#10B981',
    agents: ['output_orchestrator'],
    layout: 'single',
    showRetryLoop: true,
  },
]
