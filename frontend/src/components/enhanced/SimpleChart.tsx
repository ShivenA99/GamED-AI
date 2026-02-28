'use client'

import React, { useEffect, useRef, useState } from 'react'

/**
 * SimpleChart - Quick data visualization component
 *
 * Provides simple chart rendering for educational visualizations.
 * Uses a simple SVG-based implementation for basic needs.
 *
 * For more advanced charts, install Chart.js:
 * npm install chart.js react-chartjs-2
 *
 * Library: Chart.js (MIT License) - for advanced use
 */

export interface DataPoint {
  label: string
  value: number
  color?: string
}

export interface SimpleChartProps {
  data: DataPoint[]
  type: 'bar' | 'pie' | 'line' | 'doughnut'
  title?: string
  width?: number
  height?: number
  showLegend?: boolean
  showValues?: boolean
  animated?: boolean
}

const DEFAULT_COLORS = [
  '#3B82F6', // Blue
  '#10B981', // Green
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#06B6D4', // Cyan
  '#F97316', // Orange
]

export function SimpleChart({
  data,
  type,
  title,
  width = 400,
  height = 300,
  showLegend = true,
  showValues = true,
  animated = true,
}: SimpleChartProps) {
  const [isAnimated, setIsAnimated] = useState(!animated)

  useEffect(() => {
    if (animated) {
      const timer = setTimeout(() => setIsAnimated(true), 100)
      return () => clearTimeout(timer)
    }
  }, [animated])

  // Assign colors to data points
  const coloredData = data.map((d, i) => ({
    ...d,
    color: d.color || DEFAULT_COLORS[i % DEFAULT_COLORS.length],
  }))

  const maxValue = Math.max(...data.map((d) => d.value))
  const total = data.reduce((sum, d) => sum + d.value, 0)

  // Render based on chart type
  const renderChart = () => {
    switch (type) {
      case 'bar':
        return renderBarChart()
      case 'pie':
      case 'doughnut':
        return renderPieChart(type === 'doughnut')
      case 'line':
        return renderLineChart()
      default:
        return renderBarChart()
    }
  }

  // Bar chart
  const renderBarChart = () => {
    const padding = 40
    const chartWidth = width - padding * 2
    const chartHeight = height - padding * 2
    const barWidth = chartWidth / data.length - 10
    const scale = chartHeight / maxValue

    return (
      <svg width={width} height={height}>
        {/* Y axis */}
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={height - padding}
          stroke="#9CA3AF"
          strokeWidth={1}
        />
        {/* X axis */}
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          stroke="#9CA3AF"
          strokeWidth={1}
        />

        {/* Bars */}
        {coloredData.map((d, i) => {
          const barHeight = isAnimated ? d.value * scale : 0
          const x = padding + i * (chartWidth / data.length) + 5
          const y = height - padding - barHeight

          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                fill={d.color}
                rx={4}
                className="transition-all duration-500"
              />
              {/* Label */}
              <text
                x={x + barWidth / 2}
                y={height - padding + 15}
                textAnchor="middle"
                className="text-xs fill-gray-600"
              >
                {d.label.length > 10 ? d.label.substring(0, 10) + '...' : d.label}
              </text>
              {/* Value */}
              {showValues && isAnimated && (
                <text
                  x={x + barWidth / 2}
                  y={y - 5}
                  textAnchor="middle"
                  className="text-xs fill-gray-700 font-medium"
                >
                  {d.value}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    )
  }

  // Pie/Doughnut chart
  const renderPieChart = (isDoughnut: boolean) => {
    const centerX = width / 2
    const centerY = height / 2
    const radius = Math.min(width, height) / 2 - 40
    const innerRadius = isDoughnut ? radius * 0.6 : 0

    let currentAngle = -Math.PI / 2 // Start at top

    const slices = coloredData.map((d) => {
      const sliceAngle = (d.value / total) * Math.PI * 2
      const startAngle = currentAngle
      const endAngle = currentAngle + sliceAngle
      currentAngle = endAngle

      // Calculate path
      const x1 = centerX + radius * Math.cos(startAngle)
      const y1 = centerY + radius * Math.sin(startAngle)
      const x2 = centerX + radius * Math.cos(endAngle)
      const y2 = centerY + radius * Math.sin(endAngle)

      const innerX1 = centerX + innerRadius * Math.cos(startAngle)
      const innerY1 = centerY + innerRadius * Math.sin(startAngle)
      const innerX2 = centerX + innerRadius * Math.cos(endAngle)
      const innerY2 = centerY + innerRadius * Math.sin(endAngle)

      const largeArc = sliceAngle > Math.PI ? 1 : 0

      const path = isDoughnut
        ? `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} L ${innerX2} ${innerY2} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${innerX1} ${innerY1} Z`
        : `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`

      // Label position
      const midAngle = startAngle + sliceAngle / 2
      const labelRadius = radius * 0.7
      const labelX = centerX + labelRadius * Math.cos(midAngle)
      const labelY = centerY + labelRadius * Math.sin(midAngle)

      return {
        ...d,
        path,
        labelX,
        labelY,
        percentage: Math.round((d.value / total) * 100),
      }
    })

    return (
      <svg width={width} height={height}>
        {slices.map((slice, i) => (
          <g key={i}>
            <path
              d={slice.path}
              fill={slice.color}
              className={`transition-all duration-500 ${isAnimated ? '' : 'opacity-0'}`}
            />
            {showValues && isAnimated && slice.percentage > 5 && (
              <text
                x={slice.labelX}
                y={slice.labelY}
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-xs fill-white font-medium"
              >
                {slice.percentage}%
              </text>
            )}
          </g>
        ))}
      </svg>
    )
  }

  // Line chart
  const renderLineChart = () => {
    const padding = 40
    const chartWidth = width - padding * 2
    const chartHeight = height - padding * 2
    const stepX = chartWidth / (data.length - 1 || 1)
    const scale = chartHeight / maxValue

    const points = coloredData.map((d, i) => ({
      x: padding + i * stepX,
      y: height - padding - d.value * scale,
      ...d,
    }))

    const linePath = points
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
      .join(' ')

    return (
      <svg width={width} height={height}>
        {/* Grid lines */}
        {[...Array(5)].map((_, i) => {
          const y = padding + (chartHeight / 4) * i
          return (
            <line
              key={i}
              x1={padding}
              y1={y}
              x2={width - padding}
              y2={y}
              stroke="#E5E7EB"
              strokeDasharray="4 4"
            />
          )
        })}

        {/* Axes */}
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={height - padding}
          stroke="#9CA3AF"
          strokeWidth={1}
        />
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          stroke="#9CA3AF"
          strokeWidth={1}
        />

        {/* Line */}
        <path
          d={linePath}
          fill="none"
          stroke="#3B82F6"
          strokeWidth={2}
          className={`transition-all duration-700 ${isAnimated ? '' : 'opacity-0'}`}
        />

        {/* Points and labels */}
        {points.map((p, i) => (
          <g key={i}>
            <circle
              cx={p.x}
              cy={p.y}
              r={5}
              fill="#3B82F6"
              stroke="white"
              strokeWidth={2}
              className={`transition-all duration-500 ${isAnimated ? '' : 'opacity-0'}`}
            />
            <text
              x={p.x}
              y={height - padding + 15}
              textAnchor="middle"
              className="text-xs fill-gray-600"
            >
              {p.label}
            </text>
            {showValues && isAnimated && (
              <text
                x={p.x}
                y={p.y - 10}
                textAnchor="middle"
                className="text-xs fill-gray-700 font-medium"
              >
                {p.value}
              </text>
            )}
          </g>
        ))}
      </svg>
    )
  }

  return (
    <div className="inline-block">
      {/* Title */}
      {title && (
        <h3 className="text-sm font-semibold text-gray-700 text-center mb-2">
          {title}
        </h3>
      )}

      {/* Chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-2">
        {renderChart()}
      </div>

      {/* Legend */}
      {showLegend && (
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          {coloredData.map((d, i) => (
            <div key={i} className="flex items-center gap-1">
              <div
                className="w-3 h-3 rounded"
                style={{ backgroundColor: d.color }}
              />
              <span className="text-xs text-gray-600">{d.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SimpleChart
