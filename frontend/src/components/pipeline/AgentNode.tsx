'use client'

import { memo, useMemo, useCallback } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { STATUS_COLORS, StageExecution } from './types'

// Agent metadata type (color is now derived from category in PipelineView)
interface AgentMetadata {
  name: string
  description: string
  category: 'input' | 'routing' | 'image' | 'generation' | 'validation' | 'output' | 'decision' | 'orchestrator'
  toolOrModel: string
  icon: string
  isDecisionNode?: boolean
  isOrchestrator?: boolean
}

// React Flow node data interface
interface AgentNodeData {
  id: string
  displayName: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'degraded'
  color: string
  duration_ms?: number | null
  isActive?: boolean
  onClick?: () => void
  stage?: StageExecution
  metadata?: AgentMetadata
  wasExecuted?: boolean  // Whether this agent was executed in the current run
  retryCount?: number    // Number of retries for this agent
  isDecisionNode?: boolean  // Render as diamond shape for routing decisions
  isOrchestrator?: boolean  // Render with orchestrator styling
}

// Format duration helper (outside component to avoid recreation)
const formatDuration = (ms: number) => {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m`
}

// Get short model name (last part after /)
const getShortModelName = (modelId: string | null | undefined) => {
  if (!modelId) return null
  const parts = modelId.split('/')
  const name = parts[parts.length - 1]
  // Truncate to 12 chars
  return name.length > 12 ? name.substring(0, 12) + '…' : name
}

// React Flow node component - Compact square design with enhanced animations
// Wrapped with memo to prevent unnecessary re-renders
export const AgentNode = memo(function AgentNode({ data, selected }: NodeProps<AgentNodeData>) {
  if (!data) return null

  const {
    displayName,
    status = 'pending',
    color = '#6B7280',
    duration_ms,
    isActive = false,
    onClick,
    stage,
    metadata,
    wasExecuted = false,
    retryCount = 0,
  } = data

  const statusColors = STATUS_COLORS[status] || STATUS_COLORS.pending
  const nodeIsActive = isActive || selected
  // Color is now passed as prop (derived from category in PipelineView)
  const categoryColor = color

  // Memoize icon calculation to avoid recalculation on every render
  const icon = useMemo(() => {
    if (metadata?.icon) return metadata.icon
    const name = displayName.toLowerCase()
    if (name.includes('input') || name.includes('enhancer')) return '📝'
    if (name.includes('domain') || name.includes('knowledge')) return '🔍'
    if (name.includes('router')) return '🔀'
    if (name.includes('planner')) return '🎮'
    if (name.includes('scene')) return '🎨'
    if (name.includes('diagram') || name.includes('image')) return '🖼️'
    if (name.includes('segment')) return '✂️'
    if (name.includes('label') || name.includes('zone')) return '🏷️'
    if (name.includes('blueprint')) return '📐'
    if (name.includes('validator') || name.includes('verifier')) return '✅'
    if (name.includes('spec')) return '📋'
    if (name.includes('svg')) return '🎨'
    if (name.includes('code')) return '💻'
    if (name.includes('asset')) return '📦'
    if (name.includes('review')) return '👤'
    return '⚙️'
  }, [metadata?.icon, displayName])

  // Memoize model/tool display
  const displayToolOrModel = useMemo(() => {
    const shortModelName = getShortModelName(stage?.model_id)
    return shortModelName || (metadata?.toolOrModel?.includes('LLM') ? null : metadata?.toolOrModel)
  }, [stage?.model_id, metadata?.toolOrModel])

  // Status-based ring styles
  const statusRingClass = {
    pending: '',
    running: 'ring-2 ring-blue-400 ring-offset-2',
    success: 'ring-2 ring-green-400 ring-offset-1',
    failed: 'ring-2 ring-red-400 ring-offset-1',
    degraded: 'ring-2 ring-orange-400 ring-offset-1',
    skipped: '',
  }[status] || ''

  // Generate accessible label for screen readers
  const ariaLabel = `${displayName} agent. Status: ${status}${duration_ms ? `. Duration: ${formatDuration(duration_ms)}` : ''}${retryCount > 0 ? `. Retried ${retryCount} time${retryCount > 1 ? 's' : ''}` : ''}`

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={ariaLabel}
      aria-pressed={nodeIsActive}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && onClick) {
          e.preventDefault()
          onClick()
        }
      }}
      className={`
        relative bg-white dark:bg-gray-800 rounded-xl shadow-lg border-2
        transition-all duration-300 ease-out cursor-pointer flex flex-col items-center justify-center
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        ${nodeIsActive ? 'scale-105 shadow-xl z-10 ring-4 ring-blue-500 ring-offset-2 border-blue-400 dark:border-blue-500' : statusRingClass}
        ${status === 'running' ? 'animate-pulse' : ''}
        ${status === 'pending' ? 'border-gray-200 dark:border-gray-600' : ''}
        ${status === 'success' ? 'border-green-300 dark:border-green-500' : ''}
        ${status === 'failed' ? 'border-red-300 dark:border-red-500' : ''}
        ${status === 'degraded' ? 'border-orange-300 dark:border-orange-500' : ''}
        hover:shadow-xl hover:scale-[1.02] hover:-translate-y-0.5
        active:scale-100
        p-3
      `}
      style={{
        width: '160px',
        height: '160px',
        borderTopWidth: '4px',
        borderTopColor: categoryColor,
      }}
    >
      {/* Animated background gradient for running state */}
      {status === 'running' && (
        <div
          className="absolute inset-0 rounded-xl opacity-10 animate-pulse"
          style={{ background: `linear-gradient(135deg, ${categoryColor}20 0%, transparent 100%)` }}
          aria-hidden="true"
        />
      )}

      {/* Input Handles - Multiple positions for flexible edge routing */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{
          background: '#94A3B8',
          width: '8px',
          height: '8px',
          border: '2px solid white',
          left: '-4px',
        }}
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        style={{
          background: '#94A3B8',
          width: '8px',
          height: '8px',
          border: '2px solid white',
          top: '-4px',
        }}
      />
      <Handle
        type="target"
        position={Position.Bottom}
        id="bottom"
        style={{
          background: '#94A3B8',
          width: '8px',
          height: '8px',
          border: '2px solid white',
          bottom: '-4px',
        }}
      />

      {/* Status badge - top right */}
      <span
        className={`
          absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded-full font-semibold uppercase
          ${statusColors.bg} ${statusColors.text}
          ${status === 'running' ? 'animate-pulse' : ''}
        `}
        aria-hidden="true"
      >
        {status === 'running' ? '●' : status === 'success' ? '✓' : status === 'failed' ? '✗' : status === 'degraded' ? '⚠' : '○'}
      </span>

      {/* Retry badge - top left, only shown if retries occurred */}
      {retryCount > 0 && (
        <span
          className="absolute top-2 left-2 text-[9px] px-1.5 py-0.5 rounded-full font-semibold bg-orange-100 dark:bg-orange-900/50 text-orange-700 dark:text-orange-300 border border-orange-300 dark:border-orange-600"
          title={`This agent was retried ${retryCount} time${retryCount > 1 ? 's' : ''}`}
          aria-label={`Retried ${retryCount} time${retryCount > 1 ? 's' : ''}`}
        >
          <span aria-hidden="true">🔄</span> {retryCount}
        </span>
      )}

      {/* Centered icon */}
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center text-xl shadow-sm mb-2 transition-transform duration-200"
        style={{ backgroundColor: `${categoryColor}20` }}
        aria-hidden="true"
      >
        {icon}
      </div>

      {/* Agent name - centered, truncated */}
      <h3 className="text-xs font-semibold text-gray-900 dark:text-gray-100 text-center truncate w-full px-1 leading-tight">
        {displayName}
      </h3>

      {/* Category badge - small colored tag */}
      {metadata?.category && (
        <div
          className="text-[7px] text-white text-center truncate w-fit mt-1 px-1.5 py-0.5 rounded-full font-medium uppercase tracking-wide"
          style={{ backgroundColor: categoryColor }}
        >
          {metadata.category}
        </div>
      )}

      {/* Tool/Model badge - shown if available (model takes precedence over metadata) */}
      {displayToolOrModel && (
        <div className="text-[8px] text-gray-500 dark:text-gray-400 text-center truncate w-full mt-0.5 font-mono bg-gray-100 dark:bg-gray-700 rounded px-1 py-0.5 leading-tight">
          {displayToolOrModel}
        </div>
      )}

      {/* Duration - bottom */}
      <div className="absolute bottom-2 left-0 right-0 text-center" aria-hidden="true">
        {duration_ms != null ? (
          <span className="text-[10px] text-gray-500 dark:text-gray-400 font-medium">
            {formatDuration(duration_ms)}
          </span>
        ) : status === 'running' ? (
          <span className="text-[10px] text-blue-500 dark:text-blue-400 animate-pulse">●●●</span>
        ) : null}
      </div>

      {/* Output Handles - Multiple positions for flexible edge routing */}
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{
          background: '#94A3B8',
          width: '8px',
          height: '8px',
          border: '2px solid white',
          right: '-4px',
        }}
      />
      <Handle
        type="source"
        position={Position.Top}
        id="source-top"
        style={{
          background: '#94A3B8',
          width: '8px',
          height: '8px',
          border: '2px solid white',
          top: '-4px',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source-bottom"
        style={{
          background: '#94A3B8',
          width: '8px',
          height: '8px',
          border: '2px solid white',
          bottom: '-4px',
        }}
      />
    </div>
  )
})

// Decision Node component - Diamond shape for routing/decision nodes
// Used for conditional routing nodes like check_post_blueprint_needs, check_diagram_spec_route, etc.
export const DecisionNode = memo(function DecisionNode({ data, selected }: NodeProps<AgentNodeData>) {
  if (!data) return null

  const {
    displayName,
    status = 'pending',
    color = '#14B8A6', // Teal for decision nodes
    duration_ms,
    isActive = false,
    onClick,
    metadata,
    wasExecuted = false,
  } = data

  const statusColors = STATUS_COLORS[status] || STATUS_COLORS.pending
  const nodeIsActive = isActive || selected
  const decisionColor = metadata?.category === 'decision' || metadata?.category === 'routing' ? '#14B8A6' : color

  // Generate accessible label
  const ariaLabel = `${displayName} decision node. Status: ${status}${duration_ms ? `. Duration: ${formatDuration(duration_ms)}` : ''}`

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={ariaLabel}
      aria-pressed={nodeIsActive}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && onClick) {
          e.preventDefault()
          onClick()
        }
      }}
      className={`
        relative cursor-pointer flex items-center justify-center
        focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2
        ${nodeIsActive ? 'scale-110 z-10' : ''}
        ${status === 'running' ? 'animate-pulse' : ''}
      `}
      style={{
        width: '100px',
        height: '100px',
      }}
    >
      {/* Diamond shape container */}
      <div
        className={`
          absolute inset-0 transform rotate-45 bg-white dark:bg-gray-800
          shadow-lg border-2 transition-all duration-300
          ${nodeIsActive ? 'shadow-xl ring-4 ring-teal-500 ring-offset-2' : ''}
          ${status === 'pending' ? 'border-gray-200 dark:border-gray-600' : ''}
          ${status === 'success' ? 'border-teal-400 dark:border-teal-500' : ''}
          ${status === 'failed' ? 'border-red-300 dark:border-red-500' : ''}
          ${status === 'running' ? 'border-blue-300 dark:border-blue-500' : ''}
          hover:shadow-xl hover:scale-[1.02]
        `}
        style={{
          borderColor: status === 'pending' ? undefined : decisionColor,
          width: '70px',
          height: '70px',
          left: '15px',
          top: '15px',
        }}
      />

      {/* Input Handles */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{
          background: decisionColor,
          width: '8px',
          height: '8px',
          border: '2px solid white',
          left: '-4px',
        }}
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        style={{
          background: decisionColor,
          width: '8px',
          height: '8px',
          border: '2px solid white',
          top: '-4px',
        }}
      />

      {/* Content (not rotated) */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center">
        {/* Decision icon */}
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center text-sm mb-1"
          style={{ backgroundColor: `${decisionColor}30` }}
          aria-hidden="true"
        >
          <svg className="w-4 h-4" fill="none" stroke={decisionColor} viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>

        {/* Status indicator */}
        <span
          className={`
            text-[8px] px-1 py-0.5 rounded-full font-semibold uppercase
            ${statusColors.bg} ${statusColors.text}
          `}
          aria-hidden="true"
        >
          {status === 'running' ? '...' : status === 'success' ? 'Y' : status === 'failed' ? 'N' : '?'}
        </span>
      </div>

      {/* Output Handles - Multiple for branching */}
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{
          background: decisionColor,
          width: '8px',
          height: '8px',
          border: '2px solid white',
          right: '-4px',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source-bottom"
        style={{
          background: decisionColor,
          width: '8px',
          height: '8px',
          border: '2px solid white',
          bottom: '-4px',
        }}
      />
      <Handle
        type="source"
        position={Position.Top}
        id="source-top"
        style={{
          background: decisionColor,
          width: '8px',
          height: '8px',
          border: '2px solid white',
          top: '-4px',
        }}
      />

      {/* Name tooltip on hover */}
      <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap text-[9px] text-gray-600 dark:text-gray-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
        {displayName}
      </div>
    </div>
  )
})

// Orchestrator Node component - Larger node with orchestrator badge
// Used for orchestrator agents like multi_scene_orchestrator, game_orchestrator, output_orchestrator
export const OrchestratorNode = memo(function OrchestratorNode({ data, selected }: NodeProps<AgentNodeData>) {
  if (!data) return null

  const {
    displayName,
    status = 'pending',
    color = '#7C3AED', // Violet for orchestrators
    duration_ms,
    isActive = false,
    onClick,
    stage,
    metadata,
    wasExecuted = false,
    retryCount = 0,
  } = data

  const statusColors = STATUS_COLORS[status] || STATUS_COLORS.pending
  const nodeIsActive = isActive || selected
  const orchestratorColor = '#7C3AED' // Violet for orchestrators

  // Get icon
  const icon = useMemo(() => {
    if (metadata?.icon) return metadata.icon
    const name = displayName.toLowerCase()
    if (name.includes('multi_scene') || name.includes('scene')) return '🎬'
    if (name.includes('game')) return '🎮'
    if (name.includes('output')) return '📐'
    if (name.includes('zone')) return '🔬'
    return '🔄'
  }, [metadata?.icon, displayName])

  // Generate accessible label
  const ariaLabel = `${displayName} orchestrator. Status: ${status}${duration_ms ? `. Duration: ${formatDuration(duration_ms)}` : ''}${retryCount > 0 ? `. Retried ${retryCount} times` : ''}`

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={ariaLabel}
      aria-pressed={nodeIsActive}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && onClick) {
          e.preventDefault()
          onClick()
        }
      }}
      className={`
        relative bg-gradient-to-br from-violet-50 to-purple-50 dark:from-gray-800 dark:to-gray-900
        rounded-xl shadow-lg border-2
        transition-all duration-300 ease-out cursor-pointer flex flex-col items-center justify-center
        focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2
        ${nodeIsActive ? 'scale-105 shadow-xl z-10 ring-4 ring-violet-500 ring-offset-2 border-violet-400 dark:border-violet-500' : ''}
        ${status === 'running' ? 'animate-pulse ring-2 ring-violet-400 ring-offset-2' : ''}
        ${status === 'pending' ? 'border-gray-200 dark:border-gray-600' : ''}
        ${status === 'success' ? 'border-violet-300 dark:border-violet-500' : ''}
        ${status === 'failed' ? 'border-red-300 dark:border-red-500' : ''}
        hover:shadow-xl hover:scale-[1.02] hover:-translate-y-0.5
        active:scale-100
        p-3
      `}
      style={{
        width: '180px',
        height: '180px',
        borderTopWidth: '4px',
        borderTopColor: orchestratorColor,
      }}
    >
      {/* Orchestrator badge - top left */}
      <div
        className="absolute -top-2 -left-2 w-8 h-8 rounded-full flex items-center justify-center shadow-md border-2 border-white dark:border-gray-700"
        style={{ backgroundColor: orchestratorColor }}
        title="Orchestrator Agent"
      >
        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </div>

      {/* Animated background for running state */}
      {status === 'running' && (
        <div
          className="absolute inset-0 rounded-xl opacity-20 animate-pulse"
          style={{ background: `linear-gradient(135deg, ${orchestratorColor}40 0%, transparent 100%)` }}
          aria-hidden="true"
        />
      )}

      {/* Input Handles */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{
          background: orchestratorColor,
          width: '10px',
          height: '10px',
          border: '2px solid white',
          left: '-5px',
        }}
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        style={{
          background: orchestratorColor,
          width: '10px',
          height: '10px',
          border: '2px solid white',
          top: '-5px',
        }}
      />

      {/* Status badge - top right */}
      <span
        className={`
          absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded-full font-semibold uppercase
          ${statusColors.bg} ${statusColors.text}
          ${status === 'running' ? 'animate-pulse' : ''}
        `}
        aria-hidden="true"
      >
        {status === 'running' ? '...' : status === 'success' ? 'DONE' : status === 'failed' ? 'ERR' : 'WAIT'}
      </span>

      {/* Retry badge - if retries occurred */}
      {retryCount > 0 && (
        <span
          className="absolute top-2 left-10 text-[9px] px-1.5 py-0.5 rounded-full font-semibold bg-orange-100 dark:bg-orange-900/50 text-orange-700 dark:text-orange-300 border border-orange-300 dark:border-orange-600"
          title={`Retried ${retryCount} times`}
        >
          {retryCount}x
        </span>
      )}

      {/* Centered icon */}
      <div
        className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl shadow-sm mb-2 transition-transform duration-200"
        style={{ backgroundColor: `${orchestratorColor}20` }}
        aria-hidden="true"
      >
        {icon}
      </div>

      {/* Agent name */}
      <h3 className="text-xs font-semibold text-gray-900 dark:text-gray-100 text-center truncate w-full px-1 leading-tight">
        {displayName}
      </h3>

      {/* Orchestrator label */}
      <div
        className="text-[7px] text-white text-center truncate w-fit mt-1 px-1.5 py-0.5 rounded-full font-medium uppercase tracking-wide"
        style={{ backgroundColor: orchestratorColor }}
      >
        Orchestrator
      </div>

      {/* Sub-agents indicator */}
      {metadata?.toolOrModel && (
        <div className="text-[8px] text-gray-500 dark:text-gray-400 text-center truncate w-full mt-0.5 font-mono bg-gray-100 dark:bg-gray-700 rounded px-1 py-0.5 leading-tight">
          {metadata.toolOrModel}
        </div>
      )}

      {/* Duration - bottom */}
      <div className="absolute bottom-2 left-0 right-0 text-center" aria-hidden="true">
        {duration_ms != null ? (
          <span className="text-[10px] text-gray-500 dark:text-gray-400 font-medium">
            {formatDuration(duration_ms)}
          </span>
        ) : status === 'running' ? (
          <span className="text-[10px] text-violet-500 dark:text-violet-400 animate-pulse">processing...</span>
        ) : null}
      </div>

      {/* Output Handles */}
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{
          background: orchestratorColor,
          width: '10px',
          height: '10px',
          border: '2px solid white',
          right: '-5px',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source-bottom"
        style={{
          background: orchestratorColor,
          width: '10px',
          height: '10px',
          border: '2px solid white',
          bottom: '-5px',
        }}
      />
    </div>
  )
})

// Sub-Agent Node — compact card for sub-stages within compound nodes
interface SubAgentNodeData {
  id: string
  label: string
  status: 'success' | 'failed' | 'degraded' | 'running' | 'pending' | 'skipped'
  duration_ms?: number
  mechanic_type?: string
}

export const SubAgentNode = memo(function SubAgentNode({ data, selected }: NodeProps<SubAgentNodeData>) {
  if (!data) return null

  const { label, status = 'pending', duration_ms } = data
  const nodeIsActive = selected

  const statusDotColor = {
    success: 'bg-green-500',
    failed: 'bg-red-500',
    degraded: 'bg-orange-500',
    running: 'bg-blue-500 animate-pulse',
    pending: 'bg-gray-400',
    skipped: 'bg-gray-300',
  }[status] || 'bg-gray-400'

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${label}. Status: ${status}${duration_ms ? `. ${formatDuration(duration_ms)}` : ''}`}
      className={`
        relative bg-white rounded-lg shadow-sm border cursor-pointer
        transition-all duration-200 flex items-center gap-2 px-3 py-2
        focus:outline-none focus:ring-2 focus:ring-blue-400
        ${nodeIsActive ? 'ring-2 ring-blue-500 border-blue-400 shadow-md' : 'border-gray-200 hover:border-gray-300 hover:shadow'}
        ${status === 'failed' ? 'border-red-200 bg-red-50/50' : ''}
      `}
      style={{ width: '180px', minHeight: '36px' }}
    >
      <Handle type="target" position={Position.Top} id="top" style={{ background: '#94A3B8', width: '6px', height: '6px', border: '1.5px solid white', top: '-3px' }} />

      {/* Status dot */}
      <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${statusDotColor}`} />

      {/* Label */}
      <span className="text-[11px] font-medium text-gray-700 truncate flex-1">
        {label}
      </span>

      {/* Duration */}
      {duration_ms != null && (
        <span className="text-[10px] text-gray-400 font-mono flex-shrink-0">
          {formatDuration(duration_ms)}
        </span>
      )}

      <Handle type="source" position={Position.Bottom} id="source-bottom" style={{ background: '#94A3B8', width: '6px', height: '6px', border: '1.5px solid white', bottom: '-3px' }} />
    </div>
  )
})

// Memoized StatusIcon component
const StatusIcon = memo(function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'running':
      return (
        <svg className="w-4 h-4 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
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
      )
    case 'success':
      return (
        <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      )
    case 'failed':
      return (
        <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )
    case 'skipped':
      return (
        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    default: // pending
      return (
        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <circle cx="12" cy="12" r="10" strokeWidth={2} className="opacity-50" />
        </svg>
      )
  }
})

// Format duration for StageListItem (outside component to avoid recreation)
const formatStageDuration = (ms: number) => {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}

// Stage list item for timeline view
// Wrapped with memo to prevent unnecessary re-renders
interface StageListItemProps {
  stage: StageExecution
  isActive?: boolean
  onClick?: () => void
  isLast?: boolean
}

export const StageListItem = memo(function StageListItem({ stage, isActive, onClick, isLast = false }: StageListItemProps) {
  const statusColors = STATUS_COLORS[stage.status] || STATUS_COLORS.pending

  // Memoize aria label
  const ariaLabel = useMemo(() =>
    `${formatStageName(stage.stage_name)}. Status: ${stage.status}${stage.duration_ms ? `. Duration: ${formatStageDuration(stage.duration_ms)}` : ''}`,
    [stage.stage_name, stage.status, stage.duration_ms]
  )

  return (
    <div className="relative flex items-start gap-4">
      {/* Timeline line and dot */}
      <div className="flex flex-col items-center flex-shrink-0" aria-hidden="true">
        <div className={`
          w-4 h-4 rounded-full border-2 flex-shrink-0 mt-1 z-10 relative
          ${statusColors.bg} ${statusColors.border}
        `} />
        {!isLast && (
          <div className="w-0.5 flex-1 min-h-[80px] bg-gray-200 dark:bg-gray-700 mt-1" />
        )}
      </div>

      {/* Stage card */}
      <div
        onClick={onClick}
        role="button"
        tabIndex={0}
        aria-label={ariaLabel}
        aria-pressed={isActive}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && onClick) {
            e.preventDefault()
            onClick()
          }
        }}
        className={`
          flex-1 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5
          cursor-pointer transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          ${isActive ? 'ring-2 ring-blue-500 ring-offset-2 shadow-md border-blue-300 dark:border-blue-500' : 'hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600'}
        `}
      >
        <div className="flex items-start justify-between gap-3">
          {/* Left side - Order and info */}
          <div className="flex items-start gap-3 flex-1 min-w-0">
            {/* Order number badge */}
            <div className={`
              flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold
              ${statusColors.bg} ${statusColors.text}
            `}>
              {stage.stage_order}
            </div>

            {/* Stage info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-semibold text-base text-gray-900 dark:text-gray-100 truncate">
                  {formatStageName(stage.stage_name)}
                </h3>
                <span className={`
                  flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium
                  ${statusColors.bg} ${statusColors.text}
                `} aria-hidden="true">
                  {stage.status}
                </span>
              </div>

              {/* Metrics row */}
              {(stage.duration_ms || stage.total_tokens || stage.estimated_cost_usd) && (
                <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {stage.duration_ms && (
                    <span className="flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {formatStageDuration(stage.duration_ms)}
                    </span>
                  )}
                  {stage.total_tokens && (
                    <>
                      <span className="text-gray-300 dark:text-gray-600" aria-hidden="true">•</span>
                      <span>{stage.total_tokens.toLocaleString()} tokens</span>
                    </>
                  )}
                  {stage.estimated_cost_usd != null && stage.estimated_cost_usd > 0 && (
                    <>
                      <span className="text-gray-300 dark:text-gray-600" aria-hidden="true">•</span>
                      <span className="font-medium">${stage.estimated_cost_usd.toFixed(4)}</span>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right side - Status icon */}
          <div className="flex-shrink-0" aria-hidden="true">
            <StatusIcon status={stage.status} />
          </div>
        </div>
      </div>
    </div>
  )
})

function formatStageName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
