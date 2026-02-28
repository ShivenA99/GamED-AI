'use client';

import { useMemo, useCallback } from 'react';
import { useDroppable } from '@dnd-kit/core';
import { Zone, PlacedLabel, ZoneGroup } from './types';

/**
 * Convert polygon points from percentage coordinates to SVG path
 */
function polygonPointsToSvgPath(points: [number, number][]): string {
  if (!points || points.length < 3) return '';

  const path = points.map((point, index) => {
    const [x, y] = point;
    return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');

  return `${path} Z`;  // Close the path
}

/**
 * Calculate bounding box from polygon points
 */
function getPolygonBounds(points: [number, number][]): { minX: number; minY: number; maxX: number; maxY: number; width: number; height: number } {
  if (!points || points.length === 0) {
    return { minX: 0, minY: 0, maxX: 100, maxY: 100, width: 100, height: 100 };
  }

  const xs = points.map(p => p[0]);
  const ys = points.map(p => p[1]);

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

/**
 * Calculate offset for a zone to avoid visual overlap with other zones.
 *
 * HAD v3: This prevents discrete zones from visually overlapping.
 * For layered zones (part of a parent-child relationship), offset is not applied.
 */
function calculateZoneOffset(
  zone: Zone,
  allZones: Zone[],
  zoneGroups?: ZoneGroup[],
  collisionGapPercent: number = 2
): { x: number; y: number } {
  // Check if this zone is a child in a layered relationship
  const isLayeredChild = zoneGroups?.some(
    (g) => g.childZoneIds?.includes(zone.id)
  );
  if (isLayeredChild) {
    return { x: 0, y: 0 }; // Layered zones can overlap
  }

  // Find overlapping zones
  let offsetX = 0;
  let offsetY = 0;

  const zoneX = zone.x ?? 50;
  const zoneY = zone.y ?? 50;
  const zoneRadius = zone.radius ?? 5;

  for (const other of allZones) {
    if (other.id === zone.id) continue;

    const otherX = other.x ?? 50;
    const otherY = other.y ?? 50;
    const otherRadius = other.radius ?? 5;

    // Calculate distance between centers
    const dx = zoneX - otherX;
    const dy = zoneY - otherY;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const minDistance = zoneRadius + otherRadius + collisionGapPercent;

    if (distance < minDistance && distance > 0) {
      // Calculate repulsion offset
      const overlap = minDistance - distance;
      const pushAmount = overlap / 2;

      // Normalize direction
      const nx = dx / distance;
      const ny = dy / distance;

      offsetX += nx * pushAmount;
      offsetY += ny * pushAmount;
    }
  }

  // Clamp offsets to reasonable range (-10% to 10%)
  offsetX = Math.max(-10, Math.min(10, offsetX));
  offsetY = Math.max(-10, Math.min(10, offsetY));

  return { x: offsetX, y: offsetY };
}

interface DropZoneProps {
  zone: Zone;
  placedLabel?: PlacedLabel & { text: string };
  showHint?: boolean;
  hintText?: string;
  isHighlighted?: boolean;
  allZones?: Zone[];  // HAD v3: For collision detection
  zoneGroups?: ZoneGroup[];  // HAD v3: For identifying layered relationships
  hierarchyLevel?: number;  // HAD v3: Visual differentiation by level
  // Accessibility: Keyboard-based drop support
  activeDragId?: string | null;  // Currently dragged label ID (for keyboard navigation)
  onKeyboardDrop?: (labelId: string, zoneId: string) => void;  // Callback for keyboard-initiated drops
  zoneIndex?: number;  // For screen reader context (e.g., "Zone 1 of 5")
  totalZones?: number;
  // Optional theming from blueprint
  hierarchyColors?: string[];  // per-level stroke colors, default ['#60a5fa','#a78bfa','#2dd4bf']
  collisionGapPercent?: number; // default 2
  pointAreaThreshold?: number;  // radius above which zone is treated as area, default 6
  useCanvasOverlay?: boolean;  // When true, canvas renders polygon outlines; DropZone only renders hit area
  // Hover callback for parent tracking
  onHover?: (zoneId: string | null) => void;
}

export default function DropZone({
  zone,
  placedLabel,
  showHint,
  hintText,
  isHighlighted,
  allZones = [],
  zoneGroups = [],
  hierarchyLevel,
  activeDragId,
  onKeyboardDrop,
  zoneIndex,
  totalZones,
  hierarchyColors,
  collisionGapPercent = 2,
  pointAreaThreshold = 6,
  useCanvasOverlay = false,
  onHover,
}: DropZoneProps) {
  const isCorrectlyPlaced = !!placedLabel?.isCorrect;

  const { isOver, setNodeRef } = useDroppable({
    id: zone.id,
    disabled: isCorrectlyPlaced, // Don't register as drop target once labeled
  });

  // Keyboard handler for accessibility - allows placing labels via Enter/Space
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.key === 'Enter' || e.key === ' ') && activeDragId && onKeyboardDrop) {
        e.preventDefault();
        onKeyboardDrop(activeDragId, zone.id);
      }
    },
    [activeDragId, onKeyboardDrop, zone.id]
  );

  // Generate accessible label for screen readers
  const ariaLabel = useMemo(() => {
    const position = zoneIndex && totalZones ? `Zone ${zoneIndex} of ${totalZones}` : `Drop zone`;
    // Use pronunciation guide if available, otherwise fall back to label
    const labelInfo = zone.pronunciationGuide || zone.label || zone.description || 'unlabeled';
    const status = placedLabel
      ? `Filled with ${placedLabel.text}${placedLabel.isCorrect ? ' (correct)' : ''}`
      : 'Empty';
    const shortcutHint = zone.keyboardShortcut ? ` Press ${zone.keyboardShortcut} to select.` : '';
    return `${position}: ${labelInfo}. ${status}${shortcutHint}`;
  }, [zone.label, zone.description, zone.pronunciationGuide, zone.keyboardShortcut, placedLabel, zoneIndex, totalZones]);

  // Calculate tabIndex from focusOrder or fallback to zoneIndex
  const tabIndex = zone.focusOrder ?? (zoneIndex || 0);

  // HAD v3: Calculate collision offset
  const offset = useMemo(() => {
    if (allZones.length === 0) return { x: 0, y: 0 };
    return calculateZoneOffset(zone, allZones, zoneGroups, collisionGapPercent);
  }, [zone, allZones, zoneGroups, collisionGapPercent]);

  const size = (zone.radius ?? 5) * 2;

  // HAD v3: Adjust position with offset
  const adjustedX = (zone.x ?? 50) + offset.x;
  const adjustedY = (zone.y ?? 50) + offset.y;

  // Determine zone type: area (polygon) vs point (circle/dot)
  const isAreaZone = useMemo(() => {
    // Explicit zone_type takes priority
    if (zone.zone_type === 'area') return true;
    if (zone.zone_type === 'point') return false;

    // Infer from shape and points
    if (zone.shape === 'polygon' && zone.points && zone.points.length >= 3) return true;

    // Infer from radius - small radius = point
    return (zone.radius ?? 5) > pointAreaThreshold;
  }, [zone.zone_type, zone.shape, zone.points, zone.radius, pointAreaThreshold]);

  const isPolygonZone = zone.shape === 'polygon' && zone.points && zone.points.length >= 3;

  // Calculate polygon bounds for positioning
  const polygonBounds = useMemo(() => {
    if (!isPolygonZone || !zone.points) return null;
    return getPolygonBounds(zone.points);
  }, [isPolygonZone, zone.points]);

  // HAD v3: Style based on hierarchy level
  const levelStyles = useMemo(() => {
    const level = zone.hierarchyLevel ?? hierarchyLevel ?? 1;
    switch (level) {
      case 1:
        return 'border-blue-400 hover:border-blue-500';
      case 2:
        return 'border-purple-400 hover:border-purple-500';
      case 3:
        return 'border-teal-400 hover:border-teal-500';
      default:
        return 'border-gray-400 hover:border-primary-400';
    }
  }, [zone.hierarchyLevel, hierarchyLevel]);

  // Distinct zone color palette — each zone gets a unique, visually distinguishable color
  const ZONE_COLORS = [
    { stroke: '#3b82f6', fill: 'rgba(59, 130, 246, 0.15)',  hoverFill: 'rgba(59, 130, 246, 0.35)' },   // blue
    { stroke: '#ef4444', fill: 'rgba(239, 68, 68, 0.15)',   hoverFill: 'rgba(239, 68, 68, 0.35)' },    // red
    { stroke: '#10b981', fill: 'rgba(16, 185, 129, 0.15)',  hoverFill: 'rgba(16, 185, 129, 0.35)' },   // emerald
    { stroke: '#f59e0b', fill: 'rgba(245, 158, 11, 0.15)',  hoverFill: 'rgba(245, 158, 11, 0.35)' },   // amber
    { stroke: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.15)',  hoverFill: 'rgba(139, 92, 246, 0.35)' },   // violet
    { stroke: '#ec4899', fill: 'rgba(236, 72, 153, 0.15)',  hoverFill: 'rgba(236, 72, 153, 0.35)' },   // pink
    { stroke: '#14b8a6', fill: 'rgba(20, 184, 166, 0.15)',  hoverFill: 'rgba(20, 184, 166, 0.35)' },   // teal
    { stroke: '#f97316', fill: 'rgba(249, 115, 22, 0.15)',  hoverFill: 'rgba(249, 115, 22, 0.35)' },   // orange
    { stroke: '#6366f1', fill: 'rgba(99, 102, 241, 0.15)',  hoverFill: 'rgba(99, 102, 241, 0.35)' },   // indigo
    { stroke: '#06b6d4', fill: 'rgba(6, 182, 212, 0.15)',   hoverFill: 'rgba(6, 182, 212, 0.35)' },    // cyan
    { stroke: '#84cc16', fill: 'rgba(132, 204, 22, 0.15)',  hoverFill: 'rgba(132, 204, 22, 0.35)' },   // lime
    { stroke: '#e11d48', fill: 'rgba(225, 29, 72, 0.15)',   hoverFill: 'rgba(225, 29, 72, 0.35)' },    // rose
  ];
  const zoneColor = ZONE_COLORS[(zoneIndex ?? 0) % ZONE_COLORS.length];

  // Get stroke color based on state
  const getStrokeColor = (_level: number, over: boolean, hasLabel: boolean): string => {
    if (hasLabel) return '#22c55e';  // green-500
    if (over) return zoneColor.stroke;
    return zoneColor.stroke;
  };

  // Get fill color based on state
  const getZoneFill = (over: boolean, hasLabel: boolean): string => {
    if (hasLabel) return 'rgba(34, 197, 94, 0.2)';
    if (over) return zoneColor.hoverFill;
    return zoneColor.fill;
  };

  // ── Correctly-labeled zone: render only a floating label, no hit area ──
  // (placed after all hooks to satisfy React rules-of-hooks)
  if (isCorrectlyPlaced && placedLabel) {
    const isPolygon = zone.shape === 'polygon' && zone.points && zone.points.length >= 3;
    let labelX: number;
    let labelY: number;

    if (isPolygon && zone.points) {
      const bounds = getPolygonBounds(zone.points);
      labelX = zone.center?.x ?? (bounds.minX + bounds.width / 2);
      labelY = zone.center?.y ?? (bounds.minY + bounds.height / 2);
    } else {
      labelX = adjustedX;
      labelY = adjustedY;
    }

    return (
      <div
        className="absolute pointer-events-none transform -translate-x-1/2 -translate-y-1/2"
        style={{
          left: `${labelX}%`,
          top: `${labelY}%`,
          zIndex: (zone.hierarchyLevel ?? 1) + 10, // Above active zones
        }}
      >
        <span className="bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300 text-xs font-medium px-2 py-1 rounded whitespace-nowrap shadow-sm">
          {placedLabel.text}
        </span>
      </div>
    );
  }

  // Render polygon zone — transparent hit area (SVG outline handled by canvas overlay)
  if (isAreaZone && isPolygonZone && polygonBounds && zone.points) {
    const { minX, minY, width, height } = polygonBounds;
    const centerX = zone.center?.x ?? (minX + width / 2);
    const centerY = zone.center?.y ?? (minY + height / 2);

    return (
      <div
        ref={setNodeRef}
        tabIndex={tabIndex}
        role="button"
        aria-label={ariaLabel}
        aria-describedby={`zone-instructions-${zone.id}`}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => onHover?.(zone.id)}
        onMouseLeave={() => onHover?.(null)}
        className="absolute focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        style={{
          left: `${minX}%`,
          top: `${minY}%`,
          width: `${Math.max(width, 5)}%`,
          height: `${Math.max(height, 5)}%`,
          zIndex: zone.hierarchyLevel ?? 1,
        }}
      >
        {/* Screen reader instructions */}
        <span id={`zone-instructions-${zone.id}`} className="sr-only">
          {activeDragId
            ? 'Press Enter or Space to place the selected label here'
            : 'Tab to navigate between zones'}
        </span>

        {/* Per-zone SVG only when canvas overlay is NOT handling rendering */}
        {!useCanvasOverlay && (
          <svg
            className="w-full h-full"
            viewBox={`0 0 ${width} ${height}`}
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              d={polygonPointsToSvgPath(zone.points.map(p => [p[0] - minX, p[1] - minY] as [number, number]))}
              fill={getZoneFill(isOver, !!placedLabel)}
              stroke={getStrokeColor(zone.hierarchyLevel ?? hierarchyLevel ?? 1, isOver, !!placedLabel)}
              strokeWidth={isOver ? 3 : 2}
              strokeDasharray={placedLabel ? 'none' : isOver ? 'none' : '6 3'}
              vectorEffect="non-scaling-stroke"
              className="transition-all duration-200"
            />
          </svg>
        )}

        {/* Label indicator at center */}
        {placedLabel && (
          <div
            className="absolute transform -translate-x-1/2 -translate-y-1/2 pointer-events-none"
            style={{
              left: `${((centerX - minX) / width) * 100}%`,
              top: `${((centerY - minY) / height) * 100}%`,
            }}
          >
            <span className="bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300 text-sm font-medium px-2 py-1 rounded whitespace-nowrap">
              {placedLabel.text}
            </span>
          </div>
        )}

        {/* Hint tooltip */}
        {showHint && hintText && !placedLabel && (
          <div
            className="absolute z-10"
            style={{
              left: `${((centerX - minX) / width) * 100}%`,
              top: `${height}%`,
              transform: 'translateX(-50%)',
              marginTop: '4px',
            }}
            role="tooltip"
          >
            <div className="bg-yellow-100 dark:bg-yellow-900/80 border border-yellow-300 dark:border-yellow-700 rounded px-2 py-1 text-xs text-yellow-800 dark:text-yellow-200 whitespace-nowrap max-w-[200px] truncate">
              {hintText}
            </div>
          </div>
        )}

      </div>
    );
  }

  // Render point zone (small dot indicator) for point zones
  if (!isAreaZone || (zone.zone_type === 'point')) {
    return (
      <div
        ref={setNodeRef}
        tabIndex={tabIndex}
        role="button"
        aria-label={ariaLabel}
        aria-describedby={`zone-instructions-${zone.id}`}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => onHover?.(zone.id)}
        onMouseLeave={() => onHover?.(null)}
        className="absolute transform -translate-x-1/2 -translate-y-1/2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-full"
        style={{
          left: `${adjustedX}%`,
          top: `${adjustedY}%`,
          // 40px invisible hit area for usability; visual dot is 16px inside
          width: '40px',
          height: '40px',
          zIndex: zone.hierarchyLevel ?? 1,
        }}
      >
        {/* Screen reader instructions */}
        <span id={`zone-instructions-${zone.id}`} className="sr-only">
          {activeDragId
            ? 'Press Enter or Space to place the selected label here'
            : 'Tab to navigate between zones'}
        </span>

        {/* Point indicator — 16px fixed visual dot centered in the 40px hit area */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div
            className={`
              rounded-full border-2
              flex items-center justify-center
              transition-all duration-200
              ${
                placedLabel
                  ? 'w-4 h-4 bg-green-500 dark:bg-green-400 border-green-600 dark:border-green-500'
                  : isOver
                  ? 'w-5 h-5 scale-125'
                  : isHighlighted
                  ? 'w-4 h-4 bg-yellow-400 dark:bg-yellow-500 border-yellow-500 dark:border-yellow-400'
                  : 'w-4 h-4'
              }
            `}
            style={placedLabel ? undefined : {
              borderColor: zoneColor.stroke,
              backgroundColor: isOver ? zoneColor.hoverFill : zoneColor.fill,
            }}
            aria-hidden="true"
          >
            {placedLabel && (
              <svg className="w-2 h-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
        </div>

        {/* Label positioned near the dot */}
        {placedLabel && (
          <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 pointer-events-none">
            <span className="bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300 text-xs font-medium px-2 py-1 rounded whitespace-nowrap">
              {placedLabel.text}
            </span>
          </div>
        )}

        {/* Hint tooltip */}
        {showHint && hintText && !placedLabel && (
          <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 z-10" role="tooltip">
            <div className="bg-yellow-100 dark:bg-yellow-900/80 border border-yellow-300 dark:border-yellow-700 rounded px-2 py-1 text-xs text-yellow-800 dark:text-yellow-200 whitespace-nowrap max-w-[200px] truncate">
              {hintText}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Check for explicit rectangle zones with width/height
  const isRectZone = zone.shape === 'rect' && zone.width && zone.height;

  // Render explicit rectangle zone
  if (isRectZone) {
    const rectWidth = zone.width || 10;
    const rectHeight = zone.height || 10;
    const strokeColor = getStrokeColor(zone.hierarchyLevel ?? hierarchyLevel ?? 1, isOver, !!placedLabel);

    return (
      <div
        ref={setNodeRef}
        tabIndex={tabIndex}
        role="button"
        aria-label={ariaLabel}
        aria-describedby={`zone-instructions-${zone.id}`}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => onHover?.(zone.id)}
        onMouseLeave={() => onHover?.(null)}
        className="absolute transform -translate-x-1/2 -translate-y-1/2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        style={{
          left: `${adjustedX}%`,
          top: `${adjustedY}%`,
          width: `${rectWidth}%`,
          height: `${rectHeight}%`,
          zIndex: zone.hierarchyLevel ?? 1,
        }}
      >
        {/* Screen reader instructions */}
        <span id={`zone-instructions-${zone.id}`} className="sr-only">
          {activeDragId
            ? 'Press Enter or Space to place the selected label here'
            : 'Tab to navigate between zones'}
        </span>

        {/* Rectangle zone indicator */}
        <div
          className={`
            w-full h-full rounded
            flex items-center justify-center
            transition-all duration-200
            ${
              placedLabel
                ? 'bg-green-100/30 dark:bg-green-900/30 border-2 border-green-500'
                : isOver
                ? 'border-3 scale-105'
                : isHighlighted
                ? 'bg-yellow-100/50 border-2 border-yellow-400'
                : 'border-2 border-dashed'
            }
          `}
          style={{
            borderColor: placedLabel ? undefined : zoneColor.stroke,
            backgroundColor: placedLabel ? undefined : getZoneFill(isOver, false),
          }}
          aria-hidden="true"
        >
          {placedLabel ? (
            <span className="text-xs font-medium text-green-700 dark:text-green-300 px-1 py-0.5 bg-green-100/80 dark:bg-green-900/80 rounded max-w-full truncate">
              {placedLabel.text}
            </span>
          ) : showHint && hintText ? (
            <span className="text-xs text-gray-500 dark:text-gray-400 px-1 max-w-full truncate">
              {hintText}
            </span>
          ) : null}
        </div>

      </div>
    );
  }

  // Fallback: render standard circle zone (original behavior)
  return (
    <div
      ref={setNodeRef}
      // Accessibility: Make zone focusable and interactive via keyboard
      tabIndex={tabIndex}
      role="button"
      aria-label={ariaLabel}
      aria-describedby={`zone-instructions-${zone.id}`}
      onKeyDown={handleKeyDown}
      onMouseEnter={() => onHover?.(zone.id)}
      onMouseLeave={() => onHover?.(null)}
      className="absolute transform -translate-x-1/2 -translate-y-1/2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg"
      style={{
        left: `${adjustedX}%`,
        top: `${adjustedY}%`,
        width: `${size}%`,
        minWidth: '40px',
        minHeight: '28px',
        zIndex: zone.hierarchyLevel ?? 1, // HAD v3: Layer zones by hierarchy
      }}
    >
      {/* Screen reader instructions */}
      <span id={`zone-instructions-${zone.id}`} className="sr-only">
        {activeDragId
          ? 'Press Enter or Space to place the selected label here'
          : 'Tab to navigate between zones'}
      </span>
      {/* Drop zone visual */}
      <div
        className={`
          w-full h-full rounded-lg
          flex items-center justify-center
          transition-all duration-200
          ${
            placedLabel
              ? 'bg-green-100 dark:bg-green-900/30 border-2 border-green-500 dark:border-green-400'
              : isOver
              ? 'border-3 scale-110'
              : isHighlighted
              ? 'bg-yellow-50 dark:bg-yellow-900/20 border-2 border-yellow-400 dark:border-yellow-500'
              : 'border-2 border-dashed'
          }
        `}
        style={placedLabel ? undefined : {
          borderColor: zoneColor.stroke,
          backgroundColor: getZoneFill(isOver, false),
        }}
        aria-hidden="true"
      >
        {placedLabel ? (
          <span className="text-sm font-medium text-green-800 dark:text-green-300 px-2 text-center">
            {placedLabel.text}
          </span>
        ) : (
          <span className="text-xs text-gray-400 dark:text-gray-500">?</span>
        )}
      </div>

      {/* Hint tooltip */}
      {showHint && hintText && !placedLabel && (
        <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 z-10" role="tooltip">
          <div className="bg-yellow-100 dark:bg-yellow-900/80 border border-yellow-300 dark:border-yellow-700 rounded px-2 py-1 text-xs text-yellow-800 dark:text-yellow-200 whitespace-nowrap max-w-[200px] truncate">
            {hintText}
          </div>
        </div>
      )}

    </div>
  );
}
