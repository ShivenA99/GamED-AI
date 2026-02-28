'use client'

import React, { useMemo } from 'react'
import { StageExecution } from './types'

interface TokenChartProps {
  stages: StageExecution[]
  onStageClick?: (stage: StageExecution) => void
  selectedStage?: StageExecution | null
}

/**
 * Token Usage Bar Chart
 *
 * Displays token consumption per stage as a horizontal bar chart:
 * - Prompt tokens (blue)
 * - Completion tokens (green)
 * - Total cost indicator
 */
export function TokenChart({ stages, onStageClick, selectedStage }: TokenChartProps) {
  // Filter to stages with token data and sort by total tokens
  const stagesWithTokens = useMemo(() => {
    return stages
      .filter(s => (s.prompt_tokens || 0) + (s.completion_tokens || 0) > 0)
      .sort((a, b) => ((b.total_tokens || 0) - (a.total_tokens || 0)))
  }, [stages])

  // Calculate max tokens for scaling
  const maxTokens = useMemo(() => {
    return Math.max(...stagesWithTokens.map(s => s.total_tokens || 0), 1)
  }, [stagesWithTokens])

  // Calculate totals
  const totals = useMemo(() => {
    return stagesWithTokens.reduce(
      (acc, s) => ({
        prompt: acc.prompt + (s.prompt_tokens || 0),
        completion: acc.completion + (s.completion_tokens || 0),
        total: acc.total + (s.total_tokens || 0),
        cost: acc.cost + (s.estimated_cost_usd || 0),
      }),
      { prompt: 0, completion: 0, total: 0, cost: 0 }
    )
  }, [stagesWithTokens])

  // Format stage name
  const formatStageName = (name: string): string => {
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  // Format number with K suffix
  const formatTokens = (n: number): string => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
    return n.toString()
  }

  if (stagesWithTokens.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No token data available
      </div>
    )
  }

  return (
    <div className="space-y-4 py-4">
      {/* Header with totals */}
      <div className="px-4 pb-4 border-b">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Token Usage</h3>
        <div className="grid grid-cols-4 gap-4">
          <div>
            <span className="text-xs text-gray-500 block">Total Tokens</span>
            <span className="text-lg font-mono text-gray-900">{formatTokens(totals.total)}</span>
          </div>
          <div>
            <span className="text-xs text-gray-500 block">Prompt</span>
            <span className="text-lg font-mono text-blue-600">{formatTokens(totals.prompt)}</span>
          </div>
          <div>
            <span className="text-xs text-gray-500 block">Completion</span>
            <span className="text-lg font-mono text-green-600">{formatTokens(totals.completion)}</span>
          </div>
          <div>
            <span className="text-xs text-gray-500 block">Est. Cost</span>
            <span className="text-lg font-mono text-amber-600">${totals.cost.toFixed(4)}</span>
          </div>
        </div>
      </div>

      {/* Stage bars */}
      <div className="space-y-2 px-4">
        {stagesWithTokens.map(stage => {
          const promptWidth = ((stage.prompt_tokens || 0) / maxTokens) * 100
          const completionWidth = ((stage.completion_tokens || 0) / maxTokens) * 100
          const isSelected = selectedStage?.id === stage.id

          return (
            <div
              key={stage.id}
              className={`
                relative flex items-center cursor-pointer transition-all rounded p-2
                ${isSelected ? 'bg-blue-50 ring-2 ring-blue-400' : 'hover:bg-gray-50'}
              `}
              onClick={() => onStageClick?.(stage)}
            >
              {/* Stage name */}
              <div className="w-40 pr-2 flex-shrink-0">
                <span className="text-xs font-medium text-gray-700 truncate block">
                  {formatStageName(stage.stage_name)}
                </span>
                {stage.model_id && (
                  <span className="text-xs text-gray-400 truncate block">
                    {stage.model_id}
                  </span>
                )}
              </div>

              {/* Bar container */}
              <div className="flex-1 relative h-6">
                {/* Background */}
                <div className="absolute inset-0 bg-gray-100 rounded" />

                {/* Prompt tokens (blue) */}
                <div
                  className="absolute top-0 left-0 h-full bg-blue-500 rounded-l"
                  style={{ width: `${promptWidth}%` }}
                />

                {/* Completion tokens (green) */}
                <div
                  className="absolute top-0 h-full bg-green-500"
                  style={{
                    left: `${promptWidth}%`,
                    width: `${completionWidth}%`,
                    borderTopRightRadius: '0.25rem',
                    borderBottomRightRadius: '0.25rem',
                  }}
                />
              </div>

              {/* Token counts */}
              <div className="w-24 pl-2 flex-shrink-0 text-right">
                <span className="text-xs font-mono text-gray-600">
                  {formatTokens(stage.total_tokens || 0)}
                </span>
              </div>

              {/* Cost */}
              <div className="w-16 pl-2 flex-shrink-0 text-right">
                {stage.estimated_cost_usd != null && (
                  <span className="text-xs font-mono text-amber-600">
                    ${stage.estimated_cost_usd.toFixed(4)}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 px-4 pt-4 border-t">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-blue-500" />
          <span className="text-xs text-gray-600">Prompt tokens</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-green-500" />
          <span className="text-xs text-gray-600">Completion tokens</span>
        </div>
      </div>
    </div>
  )
}

export default TokenChart
