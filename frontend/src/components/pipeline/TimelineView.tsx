'use client'

import React, { useMemo } from 'react'
import { StageExecution, STATUS_COLORS } from './types'

interface TimelineViewProps {
  stages: StageExecution[]
  onStageClick?: (stage: StageExecution) => void
  selectedStage?: StageExecution | null
}

/**
 * Timeline/Gantt View for Pipeline Execution
 *
 * Displays stages as horizontal bars showing:
 * - Execution duration (bar width)
 * - Stage status (bar color)
 * - Stage order (vertical position)
 * - Token usage indicator (opacity gradient)
 */
export function TimelineView({ stages, onStageClick, selectedStage }: TimelineViewProps) {
  // Deduplicate and sort stages by start time
  // Group multiple executions of the same stage (retries) into one entry
  const sortedStages = useMemo(() => {
    // Group stages by stage_name to handle duplicates/retries
    const stagesByName = new Map<string, StageExecution[]>()
    stages.forEach(stage => {
      const existing = stagesByName.get(stage.stage_name) || []
      existing.push(stage)
      stagesByName.set(stage.stage_name, existing)
    })

    // For each group, merge into a single entry with retry info
    const dedupedStages: StageExecution[] = []
    stagesByName.forEach((executions, stageName) => {
      // Sort executions by start time
      const sorted = [...executions].sort((a, b) => {
        const aStart = a.started_at ? new Date(a.started_at).getTime() : 0
        const bStart = b.started_at ? new Date(b.started_at).getTime() : 0
        return aStart - bStart
      })

      // Use the LATEST execution as the primary entry
      const latest = sorted[sorted.length - 1]

      // Calculate total duration across all executions
      const totalDuration = sorted.reduce((sum, s) => sum + (s.duration_ms || 0), 0)

      // Count actual retries (executions - 1)
      const retryCount = Math.max(0, sorted.length - 1)

      // Get earliest start and latest end
      const earliestStart = sorted[0].started_at
      const latestEnd = sorted[sorted.length - 1].finished_at

      // Create merged entry
      dedupedStages.push({
        ...latest,
        id: latest.id, // Keep the latest ID
        duration_ms: totalDuration,
        retry_count: retryCount,
        started_at: earliestStart,
        finished_at: latestEnd,
        // Store all executions for detailed view if needed
        _executions: sorted,
      } as StageExecution & { _executions?: StageExecution[] })
    })

    // Sort by first start time
    return dedupedStages.sort((a, b) => {
      const aStart = a.started_at ? new Date(a.started_at).getTime() : 0
      const bStart = b.started_at ? new Date(b.started_at).getTime() : 0
      return aStart - bStart
    })
  }, [stages])

  // Calculate timeline bounds
  const { minTime, maxTime, totalDuration } = useMemo(() => {
    if (sortedStages.length === 0) return { minTime: 0, maxTime: 0, totalDuration: 0 }

    const times = sortedStages.flatMap(s => {
      const times: number[] = []
      if (s.started_at) times.push(new Date(s.started_at).getTime())
      if (s.finished_at) times.push(new Date(s.finished_at).getTime())
      return times
    }).filter(t => t > 0)

    if (times.length === 0) return { minTime: 0, maxTime: 0, totalDuration: 0 }

    const min = Math.min(...times)
    const max = Math.max(...times)
    return { minTime: min, maxTime: max, totalDuration: max - min }
  }, [sortedStages])

  // Format duration for display
  const formatDuration = (ms: number | null): string => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  // Format stage name
  const formatStageName = (name: string): string => {
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  // Get bar position and width as percentages
  const getBarStyle = (stage: StageExecution) => {
    if (!stage.started_at || totalDuration === 0) {
      return { left: '0%', width: '100%' }
    }

    const startTime = new Date(stage.started_at).getTime()
    const endTime = stage.finished_at
      ? new Date(stage.finished_at).getTime()
      : maxTime

    const left = ((startTime - minTime) / totalDuration) * 100
    const width = ((endTime - startTime) / totalDuration) * 100

    return {
      left: `${Math.max(0, left)}%`,
      width: `${Math.max(1, Math.min(100, width))}%`, // Min 1% for visibility
    }
  }

  // Get status color
  const getStatusColor = (status: string): string => {
    const colors = STATUS_COLORS[status as keyof typeof STATUS_COLORS] || STATUS_COLORS.pending
    return colors.bg
  }

  if (stages.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No stages to display
      </div>
    )
  }

  return (
    <div className="space-y-1 py-4">
      {/* Timeline Header */}
      <div className="flex items-center justify-between mb-4 px-4">
        <span className="text-sm font-medium text-gray-700">Timeline View</span>
        <span className="text-xs text-gray-500">
          Total: {formatDuration(totalDuration)}
        </span>
      </div>

      {/* Time axis */}
      <div className="relative h-6 mb-2 mx-4">
        <div className="absolute inset-0 flex justify-between text-xs text-gray-400">
          <span>0s</span>
          <span>{formatDuration(totalDuration / 4)}</span>
          <span>{formatDuration(totalDuration / 2)}</span>
          <span>{formatDuration((totalDuration * 3) / 4)}</span>
          <span>{formatDuration(totalDuration)}</span>
        </div>
      </div>

      {/* Stage bars */}
      <div className="space-y-2">
        {sortedStages.map((stage, index) => {
          const barStyle = getBarStyle(stage)
          const statusColors = STATUS_COLORS[stage.status] || STATUS_COLORS.pending
          const isSelected = selectedStage?.id === stage.id
          // Detect skipped stages
          const isSkipped = stage.status === 'skipped' ||
            (stage.output_snapshot && typeof stage.output_snapshot === 'object' && '_skipped' in stage.output_snapshot)

          return (
            <div
              key={stage.id}
              className={`
                relative h-10 flex items-center cursor-pointer transition-all
                ${isSelected ? 'bg-blue-50 ring-2 ring-blue-400 rounded' : 'hover:bg-gray-50'}
                ${isSkipped ? 'opacity-50' : ''}
              `}
              onClick={() => onStageClick?.(stage)}
            >
              {/* Stage name (fixed width) */}
              <div className="w-40 pr-2 flex-shrink-0 flex items-center gap-1">
                <span className="text-xs font-medium text-gray-700 truncate block">
                  {formatStageName(stage.stage_name)}
                </span>
                {/* Skipped indicator */}
                {isSkipped && (
                  <span className="text-[10px] text-gray-400 italic">(skipped)</span>
                )}
                {/* Retry count badge */}
                {stage.retry_count > 0 && (
                  <span className="flex-shrink-0 w-4 h-4 rounded-full bg-orange-500 text-white text-[10px] font-bold flex items-center justify-center" title={`${stage.retry_count} retries`}>
                    {stage.retry_count}
                  </span>
                )}
              </div>

              {/* Timeline bar container */}
              <div className="flex-1 relative h-6">
                {/* Background track */}
                <div className="absolute inset-0 bg-gray-100 rounded" />

                {/* Stage bar */}
                <div
                  className={`absolute top-0 bottom-0 rounded transition-all ${statusColors.bg} ${statusColors.border} border`}
                  style={barStyle}
                >
                  {/* Token indicator */}
                  {stage.total_tokens && stage.total_tokens > 0 && (
                    <div
                      className="absolute top-0 right-0 h-full bg-gradient-to-l from-white/30 to-transparent rounded-r"
                      style={{ width: '30%' }}
                    />
                  )}
                </div>

                {/* Token usage bar (subtle indicator at bottom) */}
                {stage.total_tokens && stage.total_tokens > 0 && (
                  <div
                    className="absolute bottom-0 left-0 h-1 bg-blue-400/40 rounded-b"
                    style={{
                      width: `${Math.min(100, (stage.total_tokens / 10000) * 100)}%`,
                      marginLeft: barStyle.left
                    }}
                    title={`${stage.total_tokens.toLocaleString()} tokens`}
                  />
                )}

                {/* Duration label */}
                <div
                  className="absolute top-1/2 transform -translate-y-1/2 text-xs font-medium z-10"
                  style={{
                    left: `calc(${barStyle.left} + 4px)`,
                    color: stage.status === 'running' ? '#1D4ED8' : '#374151',
                  }}
                >
                  {formatDuration(stage.duration_ms)}
                </div>
              </div>

              {/* Cost indicator */}
              <div className="w-20 pl-2 flex-shrink-0 text-right">
                {stage.estimated_cost_usd != null && (
                  <span className="text-xs font-mono text-green-600">
                    ${stage.estimated_cost_usd.toFixed(4)}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-6 px-4 pt-4 border-t flex-wrap">
        <span className="text-xs text-gray-500">Status:</span>
        {(['success', 'failed', 'running', 'degraded', 'pending'] as const).map(status => {
          const colors = STATUS_COLORS[status]
          return (
            <div key={status} className="flex items-center gap-1">
              <div className={`w-3 h-3 rounded ${colors.bg} ${colors.border} border`} />
              <span className="text-xs text-gray-600 capitalize">{status}</span>
            </div>
          )
        })}
        {/* Skipped indicator */}
        <div className="flex items-center gap-1 opacity-50">
          <div className="w-3 h-3 rounded bg-gray-200 border border-gray-300" />
          <span className="text-xs text-gray-600">skipped</span>
        </div>
        {/* Retry indicator */}
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 rounded-full bg-orange-500 text-white text-[10px] font-bold flex items-center justify-center">
            2
          </div>
          <span className="text-xs text-gray-600">retries</span>
        </div>
      </div>
    </div>
  )
}

export default TimelineView
