'use client'

import React, { useState, useMemo } from 'react'
import { ZoneOverlayData, ZoneGroup } from './types'

interface ZoneOverlayProps {
  imageSrc: string
  zones: ZoneOverlayData[]
  groups?: ZoneGroup[]
  onZoneClick?: (zone: ZoneOverlayData) => void
  selectedZoneId?: string
  showLabels?: boolean
  showGroupColors?: boolean
}

// Color palette for zone groups
const GROUP_COLORS = [
  { fill: 'rgba(139, 92, 246, 0.2)', stroke: '#8B5CF6' }, // Purple
  { fill: 'rgba(6, 182, 212, 0.2)', stroke: '#06B6D4' },   // Cyan
  { fill: 'rgba(245, 158, 11, 0.2)', stroke: '#F59E0B' },  // Amber
  { fill: 'rgba(16, 185, 129, 0.2)', stroke: '#10B981' },  // Emerald
  { fill: 'rgba(239, 68, 68, 0.2)', stroke: '#EF4444' },   // Red
  { fill: 'rgba(99, 102, 241, 0.2)', stroke: '#6366F1' },  // Indigo
]

// Default zone color
const DEFAULT_ZONE_COLOR = { fill: 'rgba(59, 130, 246, 0.2)', stroke: '#3B82F6' }

export function ZoneOverlay({
  imageSrc,
  zones,
  groups = [],
  onZoneClick,
  selectedZoneId,
  showLabels = true,
  showGroupColors = true,
}: ZoneOverlayProps) {
  const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null)
  const [imageLoaded, setImageLoaded] = useState(false)

  // Create zone-to-color mapping based on groups
  const zoneColorMap = useMemo(() => {
    const colorMap: Record<string, { fill: string; stroke: string }> = {}

    if (showGroupColors && groups.length > 0) {
      groups.forEach((group, groupIndex) => {
        const color = GROUP_COLORS[groupIndex % GROUP_COLORS.length]
        // Parent gets the color
        colorMap[group.parent] = color
        // Children get the same color
        group.children.forEach(child => {
          colorMap[child] = color
        })
      })
    }

    return colorMap
  }, [groups, showGroupColors])

  // Get color for a zone
  const getZoneColor = (zone: ZoneOverlayData) => {
    return zoneColorMap[zone.label] || DEFAULT_ZONE_COLOR
  }

  // Render zone SVG element based on type
  const renderZone = (zone: ZoneOverlayData, index: number) => {
    const color = getZoneColor(zone)
    const isSelected = zone.id === selectedZoneId
    const isHovered = zone.id === hoveredZoneId

    const strokeWidth = isSelected ? 3 : isHovered ? 2.5 : 2
    const opacity = isSelected ? 1 : isHovered ? 0.9 : 0.7

    const handleClick = () => {
      if (onZoneClick) onZoneClick(zone)
    }

    // Common props for all zone shapes
    const commonProps = {
      fill: color.fill,
      stroke: color.stroke,
      strokeWidth,
      opacity,
      cursor: onZoneClick ? 'pointer' : 'default',
      onClick: handleClick,
      onMouseEnter: () => setHoveredZoneId(zone.id),
      onMouseLeave: () => setHoveredZoneId(null),
      className: 'transition-all duration-150',
    }

    switch (zone.zone_type) {
      case 'circle':
        return (
          <circle
            key={zone.id}
            cx={`${zone.x}%`}
            cy={`${zone.y}%`}
            r={`${zone.radius}%`}
            {...commonProps}
          />
        )

      case 'ellipse':
        return (
          <ellipse
            key={zone.id}
            cx={`${zone.x}%`}
            cy={`${zone.y}%`}
            rx={`${zone.rx}%`}
            ry={`${zone.ry}%`}
            transform={zone.rotation ? `rotate(${zone.rotation} ${zone.x}% ${zone.y}%)` : undefined}
            {...commonProps}
          />
        )

      case 'bounding_box':
        return (
          <rect
            key={zone.id}
            x={`${zone.x}%`}
            y={`${zone.y}%`}
            width={`${zone.width}%`}
            height={`${zone.height}%`}
            {...commonProps}
          />
        )

      case 'polygon':
        if (!zone.points || zone.points.length < 3) return null
        const pointsStr = zone.points.map(([x, y]) => `${x}%,${y}%`).join(' ')
        return (
          <polygon
            key={zone.id}
            points={pointsStr}
            {...commonProps}
          />
        )

      case 'path':
        if (!zone.d) return null
        return (
          <path
            key={zone.id}
            d={zone.d}
            {...commonProps}
          />
        )

      default:
        // Fallback to circle with default values
        return (
          <circle
            key={zone.id}
            cx={`${zone.x || 50}%`}
            cy={`${zone.y || 50}%`}
            r={`${zone.radius || 5}%`}
            {...commonProps}
          />
        )
    }
  }

  // Calculate label position for a zone
  const getLabelPosition = (zone: ZoneOverlayData) => {
    switch (zone.zone_type) {
      case 'circle':
      case 'ellipse':
        return { x: zone.x || 50, y: (zone.y || 50) - (zone.radius || zone.ry || 5) - 2 }

      case 'bounding_box':
        return { x: (zone.x || 0) + (zone.width || 0) / 2, y: (zone.y || 0) - 2 }

      case 'polygon':
        if (zone.points && zone.points.length > 0) {
          // Calculate centroid
          const sumX = zone.points.reduce((s, [x]) => s + x, 0)
          const sumY = zone.points.reduce((s, [, y]) => s + y, 0)
          const minY = Math.min(...zone.points.map(([, y]) => y))
          return { x: sumX / zone.points.length, y: minY - 2 }
        }
        return { x: 50, y: 48 }

      default:
        return { x: zone.x || 50, y: (zone.y || 50) - 5 }
    }
  }

  return (
    <div className="relative w-full bg-gray-100 rounded-lg overflow-hidden">
      {/* Image */}
      <img
        src={imageSrc}
        alt="Diagram with zone overlay"
        className="w-full h-auto"
        onLoad={() => setImageLoaded(true)}
        onError={() => setImageLoaded(false)}
      />

      {/* SVG Overlay */}
      {imageLoaded && zones.length > 0 && (
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <g style={{ pointerEvents: 'auto' }}>
            {/* Render zones */}
            {zones.map((zone, index) => renderZone(zone, index))}

            {/* Render labels */}
            {showLabels && zones.map(zone => {
              const pos = getLabelPosition(zone)
              const isSelected = zone.id === selectedZoneId
              const isHovered = zone.id === hoveredZoneId

              return (
                <g key={`label-${zone.id}`}>
                  {/* Label background */}
                  <rect
                    x={`${pos.x - 10}%`}
                    y={`${pos.y - 3}%`}
                    width="20%"
                    height="5%"
                    fill="white"
                    opacity={isSelected || isHovered ? 0.95 : 0.85}
                    rx="1"
                  />
                  {/* Label text */}
                  <text
                    x={`${pos.x}%`}
                    y={`${pos.y}%`}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="2.5"
                    fontWeight={isSelected || isHovered ? 600 : 500}
                    fill={isSelected ? '#2563EB' : isHovered ? '#3B82F6' : '#374151'}
                    style={{ pointerEvents: 'none' }}
                  >
                    {zone.label}
                  </text>
                </g>
              )
            })}
          </g>
        </svg>
      )}

      {/* Loading state */}
      {!imageLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-200">
          <div className="text-gray-500 text-sm">Loading image...</div>
        </div>
      )}

      {/* Zone count badge */}
      {zones.length > 0 && (
        <div className="absolute top-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded-full">
          {zones.length} zone{zones.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
}

// Compact zone list for small displays
export function ZoneList({
  zones,
  groups = [],
  onZoneClick,
  selectedZoneId,
}: {
  zones: ZoneOverlayData[]
  groups?: ZoneGroup[]
  onZoneClick?: (zone: ZoneOverlayData) => void
  selectedZoneId?: string
}) {
  if (zones.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-4">
        No zones detected
      </div>
    )
  }

  // Group zones by hierarchy
  const rootZones = zones.filter(z => !z.parent_label)
  const childZonesByParent = zones.reduce((acc, zone) => {
    if (zone.parent_label) {
      if (!acc[zone.parent_label]) acc[zone.parent_label] = []
      acc[zone.parent_label].push(zone)
    }
    return acc
  }, {} as Record<string, ZoneOverlayData[]>)

  return (
    <div className="space-y-1">
      {rootZones.map(zone => (
        <div key={zone.id}>
          <ZoneListItem
            zone={zone}
            isSelected={zone.id === selectedZoneId}
            onClick={onZoneClick}
          />
          {/* Render children indented */}
          {childZonesByParent[zone.label] && (
            <div className="ml-4 border-l border-gray-200 pl-2 space-y-1 mt-1">
              {childZonesByParent[zone.label].map(child => (
                <ZoneListItem
                  key={child.id}
                  zone={child}
                  isSelected={child.id === selectedZoneId}
                  onClick={onZoneClick}
                  isChild
                />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function ZoneListItem({
  zone,
  isSelected,
  onClick,
  isChild = false,
}: {
  zone: ZoneOverlayData
  isSelected: boolean
  onClick?: (zone: ZoneOverlayData) => void
  isChild?: boolean
}) {
  return (
    <button
      onClick={() => onClick?.(zone)}
      className={`
        w-full text-left px-2 py-1.5 rounded text-sm flex items-center justify-between
        ${isSelected
          ? 'bg-blue-100 text-blue-800'
          : 'hover:bg-gray-100 text-gray-700'
        }
        ${isChild ? 'text-xs' : ''}
      `}
    >
      <span className="font-medium truncate">{zone.label}</span>
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span className="capitalize">{zone.zone_type.replace('_', ' ')}</span>
        {zone.confidence !== undefined && (
          <span className={`${zone.confidence >= 0.8 ? 'text-green-600' : zone.confidence >= 0.5 ? 'text-yellow-600' : 'text-red-600'}`}>
            {Math.round(zone.confidence * 100)}%
          </span>
        )}
      </div>
    </button>
  )
}
