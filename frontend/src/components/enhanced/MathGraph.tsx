'use client'

import React, { useState, useCallback } from 'react'

/**
 * MathGraph - Interactive mathematical graphing component
 *
 * Provides function plotting and interactive geometry visualization.
 * Uses a simple SVG-based implementation for React compatibility.
 *
 * For more advanced features, consider:
 * - Mafs (React-native, MIT license): npm install mafs
 * - JSXGraph (MIT/LGPL): For complex interactive geometry
 */

export interface MathFunction {
  id: string
  expression: string
  color: string
  label?: string
}

export interface Point {
  x: number
  y: number
  label?: string
  color?: string
}

export interface MathGraphProps {
  width?: number
  height?: number
  xMin?: number
  xMax?: number
  yMin?: number
  yMax?: number
  functions?: MathFunction[]
  points?: Point[]
  showGrid?: boolean
  showAxes?: boolean
  showLabels?: boolean
  interactive?: boolean
  onPointClick?: (point: Point) => void
  onGraphClick?: (x: number, y: number) => void
}

// Simple math expression parser
function evaluateExpression(expr: string, x: number): number | null {
  try {
    // Replace common math functions
    const sanitized = expr
      .replace(/sin/g, 'Math.sin')
      .replace(/cos/g, 'Math.cos')
      .replace(/tan/g, 'Math.tan')
      .replace(/sqrt/g, 'Math.sqrt')
      .replace(/abs/g, 'Math.abs')
      .replace(/log/g, 'Math.log')
      .replace(/exp/g, 'Math.exp')
      .replace(/\^/g, '**')
      .replace(/pi/gi, 'Math.PI')
      .replace(/e(?![xp])/gi, 'Math.E')

    // Create function and evaluate
    const fn = new Function('x', `return ${sanitized}`)
    const result = fn(x)

    if (typeof result !== 'number' || !isFinite(result)) {
      return null
    }
    return result
  } catch {
    return null
  }
}

export function MathGraph({
  width = 500,
  height = 400,
  xMin = -10,
  xMax = 10,
  yMin = -10,
  yMax = 10,
  functions = [],
  points = [],
  showGrid = true,
  showAxes = true,
  showLabels = true,
  interactive = false,
  onPointClick,
  onGraphClick,
}: MathGraphProps) {
  const [hoverPoint, setHoverPoint] = useState<{ x: number; y: number } | null>(null)

  // Coordinate transformation
  const toPixelX = useCallback(
    (x: number) => ((x - xMin) / (xMax - xMin)) * width,
    [xMin, xMax, width]
  )

  const toPixelY = useCallback(
    (y: number) => height - ((y - yMin) / (yMax - yMin)) * height,
    [yMin, yMax, height]
  )

  const toMathX = useCallback(
    (px: number) => xMin + (px / width) * (xMax - xMin),
    [xMin, xMax, width]
  )

  const toMathY = useCallback(
    (py: number) => yMax - (py / height) * (yMax - yMin),
    [yMin, yMax, height]
  )

  // Generate function paths
  const generateFunctionPath = useCallback(
    (fn: MathFunction) => {
      const points: string[] = []
      const step = (xMax - xMin) / 500

      for (let x = xMin; x <= xMax; x += step) {
        const y = evaluateExpression(fn.expression, x)
        if (y !== null && y >= yMin && y <= yMax) {
          const px = toPixelX(x)
          const py = toPixelY(y)
          points.push(points.length === 0 ? `M ${px} ${py}` : `L ${px} ${py}`)
        }
      }

      return points.join(' ')
    },
    [xMin, xMax, yMin, yMax, toPixelX, toPixelY]
  )

  // Generate grid lines
  const gridLines = []
  const gridStep = 1

  if (showGrid) {
    // Vertical lines
    for (let x = Math.ceil(xMin); x <= xMax; x += gridStep) {
      gridLines.push(
        <line
          key={`v-${x}`}
          x1={toPixelX(x)}
          y1={0}
          x2={toPixelX(x)}
          y2={height}
          stroke="#e5e7eb"
          strokeWidth={1}
        />
      )
    }

    // Horizontal lines
    for (let y = Math.ceil(yMin); y <= yMax; y += gridStep) {
      gridLines.push(
        <line
          key={`h-${y}`}
          x1={0}
          y1={toPixelY(y)}
          x2={width}
          y2={toPixelY(y)}
          stroke="#e5e7eb"
          strokeWidth={1}
        />
      )
    }
  }

  // Handle click
  const handleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!interactive || !onGraphClick) return

      const rect = e.currentTarget.getBoundingClientRect()
      const px = e.clientX - rect.left
      const py = e.clientY - rect.top

      const x = toMathX(px)
      const y = toMathY(py)

      onGraphClick(x, y)
    },
    [interactive, onGraphClick, toMathX, toMathY]
  )

  // Handle mouse move for hover coordinates
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!interactive) return

      const rect = e.currentTarget.getBoundingClientRect()
      const px = e.clientX - rect.left
      const py = e.clientY - rect.top

      setHoverPoint({
        x: Math.round(toMathX(px) * 100) / 100,
        y: Math.round(toMathY(py) * 100) / 100,
      })
    },
    [interactive, toMathX, toMathY]
  )

  return (
    <div className="relative">
      <svg
        width={width}
        height={height}
        className="bg-white border border-gray-200 rounded-lg"
        onClick={handleClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverPoint(null)}
      >
        {/* Grid */}
        {gridLines}

        {/* Axes */}
        {showAxes && (
          <>
            {/* X axis */}
            {yMin <= 0 && yMax >= 0 && (
              <line
                x1={0}
                y1={toPixelY(0)}
                x2={width}
                y2={toPixelY(0)}
                stroke="#374151"
                strokeWidth={2}
              />
            )}
            {/* Y axis */}
            {xMin <= 0 && xMax >= 0 && (
              <line
                x1={toPixelX(0)}
                y1={0}
                x2={toPixelX(0)}
                y2={height}
                stroke="#374151"
                strokeWidth={2}
              />
            )}
          </>
        )}

        {/* Axis labels */}
        {showLabels && showAxes && (
          <>
            {/* X axis labels */}
            {Array.from(
              { length: Math.floor((xMax - xMin) / 2) + 1 },
              (_, i) => Math.ceil(xMin) + i * 2
            ).map((x) => {
              if (x === 0) return null
              return (
                <text
                  key={`x-${x}`}
                  x={toPixelX(x)}
                  y={toPixelY(0) + 15}
                  textAnchor="middle"
                  className="text-xs fill-gray-500"
                >
                  {x}
                </text>
              )
            })}
            {/* Y axis labels */}
            {Array.from(
              { length: Math.floor((yMax - yMin) / 2) + 1 },
              (_, i) => Math.ceil(yMin) + i * 2
            ).map((y) => {
              if (y === 0) return null
              return (
                <text
                  key={`y-${y}`}
                  x={toPixelX(0) - 8}
                  y={toPixelY(y) + 4}
                  textAnchor="end"
                  className="text-xs fill-gray-500"
                >
                  {y}
                </text>
              )
            })}
          </>
        )}

        {/* Functions */}
        {functions.map((fn) => (
          <path
            key={fn.id}
            d={generateFunctionPath(fn)}
            fill="none"
            stroke={fn.color}
            strokeWidth={2}
          />
        ))}

        {/* Points */}
        {points.map((point, i) => (
          <g key={i}>
            <circle
              cx={toPixelX(point.x)}
              cy={toPixelY(point.y)}
              r={6}
              fill={point.color || '#3B82F6'}
              stroke="white"
              strokeWidth={2}
              className={interactive ? 'cursor-pointer hover:r-8' : ''}
              onClick={() => onPointClick?.(point)}
            />
            {point.label && (
              <text
                x={toPixelX(point.x) + 10}
                y={toPixelY(point.y) - 10}
                className="text-xs fill-gray-700"
              >
                {point.label}
              </text>
            )}
          </g>
        ))}
      </svg>

      {/* Hover coordinates */}
      {interactive && hoverPoint && (
        <div className="absolute top-2 right-2 px-2 py-1 bg-gray-800 text-white text-xs rounded">
          ({hoverPoint.x}, {hoverPoint.y})
        </div>
      )}

      {/* Function legend */}
      {functions.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {functions.map((fn) => (
            <span
              key={fn.id}
              className="text-xs px-2 py-1 rounded"
              style={{ backgroundColor: `${fn.color}20`, color: fn.color }}
            >
              {fn.label || `f(x) = ${fn.expression}`}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default MathGraph
