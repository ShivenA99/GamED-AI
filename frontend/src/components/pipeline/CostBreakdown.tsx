'use client'

import React, { useMemo } from 'react'
import { StageExecution } from './types'

interface CostBreakdownProps {
  stages: StageExecution[]
  onStageClick?: (stage: StageExecution) => void
}

interface CostItem {
  stage: StageExecution
  cost: number
  percentage: number
  color: string
}

// Category-based colors for stages
const CATEGORY_COLORS: Record<string, string> = {
  input: '#3B82F6',      // blue
  routing: '#8B5CF6',    // purple
  image: '#10B981',      // green
  generation: '#F59E0B', // amber
  validation: '#6366F1', // indigo
  output: '#EC4899',     // pink
  react: '#14B8A6',      // teal
}

// Stage to category mapping (simplified)
const getStageCategoryColor = (stageName: string): string => {
  if (stageName.includes('validator') || stageName.includes('verifier')) return CATEGORY_COLORS.validation
  if (stageName.includes('image') || stageName.includes('zone') || stageName.includes('diagram')) return CATEGORY_COLORS.image
  if (stageName.includes('router')) return CATEGORY_COLORS.routing
  if (stageName.includes('input') || stageName.includes('enhancer') || stageName.includes('domain')) return CATEGORY_COLORS.input
  if (stageName.includes('output') || stageName.includes('svg') || stageName.includes('render')) return CATEGORY_COLORS.output
  if (stageName.includes('agent')) return CATEGORY_COLORS.react
  return CATEGORY_COLORS.generation
}

/**
 * Cost Breakdown Pie/Donut Chart
 *
 * Displays cost distribution across stages using a donut chart
 */
export function CostBreakdown({ stages, onStageClick }: CostBreakdownProps) {
  // Calculate cost breakdown
  const { items, totalCost } = useMemo(() => {
    const stagesWithCost = stages.filter(s => (s.estimated_cost_usd || 0) > 0)
    const total = stagesWithCost.reduce((sum, s) => sum + (s.estimated_cost_usd || 0), 0)

    const items: CostItem[] = stagesWithCost
      .map(stage => ({
        stage,
        cost: stage.estimated_cost_usd || 0,
        percentage: total > 0 ? ((stage.estimated_cost_usd || 0) / total) * 100 : 0,
        color: getStageCategoryColor(stage.stage_name),
      }))
      .sort((a, b) => b.cost - a.cost)

    return { items, totalCost: total }
  }, [stages])

  // Format stage name
  const formatStageName = (name: string): string => {
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  // Generate SVG donut chart path
  const generateDonutPath = (startAngle: number, endAngle: number, outerRadius: number, innerRadius: number) => {
    const startOuter = polarToCartesian(50, 50, outerRadius, startAngle)
    const endOuter = polarToCartesian(50, 50, outerRadius, endAngle)
    const startInner = polarToCartesian(50, 50, innerRadius, endAngle)
    const endInner = polarToCartesian(50, 50, innerRadius, startAngle)

    const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0

    return [
      `M ${startOuter.x} ${startOuter.y}`,
      `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${endOuter.x} ${endOuter.y}`,
      `L ${startInner.x} ${startInner.y}`,
      `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${endInner.x} ${endInner.y}`,
      'Z',
    ].join(' ')
  }

  const polarToCartesian = (cx: number, cy: number, r: number, angle: number) => {
    const rad = (angle - 90) * (Math.PI / 180)
    return {
      x: cx + r * Math.cos(rad),
      y: cy + r * Math.sin(rad),
    }
  }

  // Generate donut segments
  const segments = useMemo(() => {
    let currentAngle = 0
    return items.map(item => {
      const angle = (item.percentage / 100) * 360
      const segment = {
        ...item,
        startAngle: currentAngle,
        endAngle: currentAngle + Math.max(angle, 1), // Min 1 degree for visibility
        path: generateDonutPath(currentAngle, currentAngle + Math.max(angle, 1), 45, 25),
      }
      currentAngle += angle
      return segment
    })
  }, [items])

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No cost data available
      </div>
    )
  }

  return (
    <div className="p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Cost Breakdown</h3>

      <div className="flex gap-6">
        {/* Donut Chart */}
        <div className="relative w-40 h-40 flex-shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
            {segments.map((segment, i) => (
              <path
                key={segment.stage.id}
                d={segment.path}
                fill={segment.color}
                className="cursor-pointer transition-opacity hover:opacity-80"
                onClick={() => onStageClick?.(segment.stage)}
              />
            ))}
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-lg font-bold text-gray-900">${totalCost.toFixed(4)}</span>
            <span className="text-xs text-gray-500">Total</span>
          </div>
        </div>

        {/* Legend/List */}
        <div className="flex-1 space-y-1 max-h-40 overflow-y-auto">
          {items.slice(0, 8).map(item => (
            <div
              key={item.stage.id}
              className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 rounded p-1"
              onClick={() => onStageClick?.(item.stage)}
            >
              <div
                className="w-3 h-3 rounded-sm flex-shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <span className="flex-1 truncate text-gray-700 text-xs">
                {formatStageName(item.stage.stage_name)}
              </span>
              <span className="text-xs font-mono text-gray-500">
                {item.percentage.toFixed(1)}%
              </span>
              <span className="text-xs font-mono text-green-600">
                ${item.cost.toFixed(4)}
              </span>
            </div>
          ))}
          {items.length > 8 && (
            <div className="text-xs text-gray-400 pt-1">
              +{items.length - 8} more stages...
            </div>
          )}
        </div>
      </div>

      {/* Category Legend */}
      <div className="flex flex-wrap gap-3 mt-4 pt-4 border-t">
        {Object.entries(CATEGORY_COLORS).map(([category, color]) => (
          <div key={category} className="flex items-center gap-1">
            <div
              className="w-2 h-2 rounded-sm"
              style={{ backgroundColor: color }}
            />
            <span className="text-xs text-gray-500 capitalize">{category}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default CostBreakdown
