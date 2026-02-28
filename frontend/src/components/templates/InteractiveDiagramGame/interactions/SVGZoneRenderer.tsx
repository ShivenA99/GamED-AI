'use client'

import React, { useMemo } from 'react'
import { Zone } from '../types'

interface SVGZoneRendererProps {
  zones: Zone[]
  containerWidth: number
  containerHeight: number
  activeZoneId?: string | null
  matchedZoneIds?: string[]
  onZoneClick?: (zoneId: string) => void
  onZoneHover?: (zoneId: string | null) => void
  showLabels?: boolean
  highlightParent?: boolean
}

/**
 * SVGZoneRenderer Component (Preset 2)
 *
 * Renders SVG zones including:
 * - Circle zones (standard)
 * - Polygon zones (exact shape outlines)
 * - Rectangle zones
 *
 * Features:
 * - Hit detection for irregular polygon shapes
 * - Hover and click interactions
 * - Visual feedback for matched/active states
 */
export const SVGZoneRenderer: React.FC<SVGZoneRendererProps> = ({
  zones,
  containerWidth,
  containerHeight,
  activeZoneId,
  matchedZoneIds = [],
  onZoneClick,
  onZoneHover,
  showLabels = false,
  highlightParent = false,
}) => {
  // Convert percentage coordinates to pixel coordinates
  const toPixelX = (percent: number) => (percent / 100) * containerWidth
  const toPixelY = (percent: number) => (percent / 100) * containerHeight

  // Generate SVG path for polygon zones
  const getPolygonPath = (points: [number, number][]) => {
    if (!points || points.length < 3) return ''

    const pixelPoints = points.map(([x, y]) => [toPixelX(x), toPixelY(y)])
    const pathData = pixelPoints
      .map((point, i) => `${i === 0 ? 'M' : 'L'} ${point[0]},${point[1]}`)
      .join(' ')

    return pathData + ' Z'
  }

  // Get zone center for label placement
  const getZoneCenter = (zone: Zone) => {
    if (zone.center) {
      return {
        x: toPixelX(zone.center.x),
        y: toPixelY(zone.center.y),
      }
    }

    if (zone.shape === 'polygon' && zone.points && zone.points.length > 0) {
      // Calculate centroid of polygon
      const points = zone.points as [number, number][]
      const sumX = points.reduce((sum, p) => sum + p[0], 0)
      const sumY = points.reduce((sum, p) => sum + p[1], 0)
      return {
        x: toPixelX(sumX / points.length),
        y: toPixelY(sumY / points.length),
      }
    }

    // Default: use x, y as center
    return {
      x: toPixelX(zone.x ?? 50),
      y: toPixelY(zone.y ?? 50),
    }
  }

  // Determine zone colors based on state
  const getZoneColors = (zone: Zone) => {
    const isMatched = matchedZoneIds.includes(zone.id)
    const isActive = activeZoneId === zone.id
    const isParent = highlightParent && zones.some(z => z.parentZoneId === zone.id)

    if (isMatched) {
      return {
        fill: 'rgba(16, 185, 129, 0.3)',  // Green
        stroke: '#10B981',
        strokeWidth: 3,
      }
    }

    if (isActive) {
      return {
        fill: 'rgba(59, 130, 246, 0.3)',  // Blue
        stroke: '#3B82F6',
        strokeWidth: 3,
      }
    }

    if (isParent) {
      return {
        fill: 'rgba(249, 115, 22, 0.2)',  // Orange
        stroke: '#F97316',
        strokeWidth: 2,
      }
    }

    return {
      fill: 'rgba(156, 163, 175, 0.2)',  // Gray
      stroke: '#9CA3AF',
      strokeWidth: 1,
    }
  }

  // Render a single zone
  const renderZone = (zone: Zone) => {
    const colors = getZoneColors(zone)
    const center = getZoneCenter(zone)
    const zoneKey = zone.id

    const handleClick = () => {
      if (onZoneClick) {
        onZoneClick(zone.id)
      }
    }

    const handleMouseEnter = () => {
      if (onZoneHover) {
        onZoneHover(zone.id)
      }
    }

    const handleMouseLeave = () => {
      if (onZoneHover) {
        onZoneHover(null)
      }
    }

    // Render based on shape type
    if (zone.shape === 'polygon' && zone.points && zone.points.length >= 3) {
      const path = getPolygonPath(zone.points as [number, number][])

      return (
        <g key={zoneKey}>
          <path
            d={path}
            fill={colors.fill}
            stroke={colors.stroke}
            strokeWidth={colors.strokeWidth}
            className="cursor-pointer transition-all duration-200 hover:opacity-80"
            onClick={handleClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          />
          {showLabels && (
            <text
              x={center.x}
              y={center.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-xs font-medium fill-gray-700 pointer-events-none"
            >
              {zone.label}
            </text>
          )}
        </g>
      )
    }

    if (zone.shape === 'rect') {
      const width = (zone.radius ?? 10) * 2 * (containerWidth / 100)
      const height = (zone.radius ?? 10) * 2 * (containerHeight / 100)
      const x = toPixelX(zone.x ?? 50) - width / 2
      const y = toPixelY(zone.y ?? 50) - height / 2

      return (
        <g key={zoneKey}>
          <rect
            x={x}
            y={y}
            width={width}
            height={height}
            fill={colors.fill}
            stroke={colors.stroke}
            strokeWidth={colors.strokeWidth}
            rx={4}
            className="cursor-pointer transition-all duration-200 hover:opacity-80"
            onClick={handleClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          />
          {showLabels && (
            <text
              x={center.x}
              y={center.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-xs font-medium fill-gray-700 pointer-events-none"
            >
              {zone.label}
            </text>
          )}
        </g>
      )
    }

    // Default: circle
    const radius = (zone.radius ?? 10) * (containerWidth / 100)

    return (
      <g key={zoneKey}>
        <circle
          cx={center.x}
          cy={center.y}
          r={radius}
          fill={colors.fill}
          stroke={colors.stroke}
          strokeWidth={colors.strokeWidth}
          className="cursor-pointer transition-all duration-200 hover:opacity-80"
          onClick={handleClick}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        />
        {showLabels && (
          <text
            x={center.x}
            y={center.y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="text-xs font-medium fill-gray-700 pointer-events-none"
          >
            {zone.label}
          </text>
        )}
      </g>
    )
  }

  // Sort zones by hierarchy level (render parents first, then children on top)
  const sortedZones = useMemo(() => {
    return [...zones].sort((a, b) => {
      const levelA = a.hierarchyLevel ?? 1
      const levelB = b.hierarchyLevel ?? 1
      return levelA - levelB  // Lower levels (parents) first
    })
  }, [zones])

  return (
    <svg
      width={containerWidth}
      height={containerHeight}
      className="absolute top-0 left-0 pointer-events-auto"
      style={{ zIndex: 10 }}
    >
      {/* Render zones */}
      {sortedZones.map(renderZone)}

      {/* Optional: render hierarchy lines connecting parents to children */}
      {highlightParent && sortedZones.map(zone => {
        if (!zone.parentZoneId) return null

        const parent = zones.find(z => z.id === zone.parentZoneId)
        if (!parent) return null

        const childCenter = getZoneCenter(zone)
        const parentCenter = getZoneCenter(parent)

        return (
          <line
            key={`hierarchy-${zone.id}`}
            x1={parentCenter.x}
            y1={parentCenter.y}
            x2={childCenter.x}
            y2={childCenter.y}
            stroke="#F97316"
            strokeWidth={1}
            strokeDasharray="4,2"
            opacity={0.5}
            className="pointer-events-none"
          />
        )
      })}
    </svg>
  )
}

export default SVGZoneRenderer
