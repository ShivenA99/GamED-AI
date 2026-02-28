'use client';

import { useEffect, useRef, useMemo } from 'react';
import { LeaderLineStyle, PinMarkerShape, LeaderLineAnchor, PlacedLabel } from './types';

interface LeaderLineOverlayProps {
  /** Container dimensions for coordinate mapping */
  containerWidth: number;
  containerHeight: number;
  /** Placed labels to draw lines for */
  placedLabels: PlacedLabel[];
  /** Anchor definitions per zone */
  anchors: LeaderLineAnchor[];
  /** Default line style */
  lineStyle?: LeaderLineStyle;
  /** Line color */
  lineColor?: string;
  /** Line width */
  lineWidth?: number;
  /** Whether to animate line drawing */
  animate?: boolean;
  /** Pin marker shape at zone end */
  pinMarkerShape?: PinMarkerShape;
  /** IDs of correctly placed labels (only draw for correct ones) */
  correctZoneIds?: Set<string>;
}

/** Generate SVG path data for different leader line styles */
function generateLinePath(
  style: LeaderLineStyle,
  x1: number, y1: number,
  x2: number, y2: number,
): string {
  switch (style) {
    case 'straight':
      return `M ${x1} ${y1} L ${x2} ${y2}`;

    case 'elbow': {
      // L-shaped: horizontal then vertical (or vice-versa depending on direction)
      const midX = x2;
      return `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2}`;
    }

    case 'curved': {
      // Quadratic bezier with control point offset
      const cx = (x1 + x2) / 2;
      const cy = y1 - Math.abs(y2 - y1) * 0.3;
      return `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
    }

    case 'fluid': {
      // Smooth S-curve using cubic bezier
      const dx = x2 - x1;
      const dy = y2 - y1;
      const cp1x = x1 + dx * 0.4;
      const cp1y = y1;
      const cp2x = x2 - dx * 0.4;
      const cp2y = y2;
      return `M ${x1} ${y1} C ${cp1x} ${cp1y} ${cp2x} ${cp2y} ${x2} ${y2}`;
    }

    default:
      return '';
  }
}

/** Render a pin marker shape */
function PinMarker({
  shape,
  x,
  y,
  color,
  size = 6,
}: {
  shape: PinMarkerShape;
  x: number;
  y: number;
  color: string;
  size?: number;
}) {
  switch (shape) {
    case 'circle':
      return (
        <circle
          cx={x}
          cy={y}
          r={size}
          fill={color}
          stroke="white"
          strokeWidth={1.5}
        />
      );

    case 'diamond': {
      const half = size;
      return (
        <polygon
          points={`${x},${y - half} ${x + half},${y} ${x},${y + half} ${x - half},${y}`}
          fill={color}
          stroke="white"
          strokeWidth={1.5}
        />
      );
    }

    case 'arrow': {
      const s = size;
      return (
        <polygon
          points={`${x},${y - s} ${x + s * 0.7},${y + s * 0.5} ${x - s * 0.7},${y + s * 0.5}`}
          fill={color}
          stroke="white"
          strokeWidth={1}
        />
      );
    }

    default:
      return null;
  }
}

export default function LeaderLineOverlay({
  containerWidth,
  containerHeight,
  placedLabels,
  anchors,
  lineStyle = 'curved',
  lineColor = '#6366f1',
  lineWidth = 2,
  animate = true,
  pinMarkerShape = 'circle',
  correctZoneIds,
}: LeaderLineOverlayProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Build anchor lookup
  const anchorMap = useMemo(() => {
    const map = new Map<string, LeaderLineAnchor>();
    anchors.forEach((a) => map.set(a.zone_id, a));
    return map;
  }, [anchors]);

  // Lines to draw: only for correctly placed labels with anchors
  const lines = useMemo(() => {
    return placedLabels
      .filter((pl) => {
        if (correctZoneIds && !correctZoneIds.has(pl.zoneId)) return false;
        return pl.isCorrect && anchorMap.has(pl.zoneId);
      })
      .map((pl) => {
        const anchor = anchorMap.get(pl.zoneId)!;
        const style = anchor.preferred_style || lineStyle;
        return {
          id: `line-${pl.zoneId}`,
          zoneId: pl.zoneId,
          style,
          // Pin point (on zone)
          pinX: (anchor.pin_x / 100) * containerWidth,
          pinY: (anchor.pin_y / 100) * containerHeight,
          // Label anchor point (where the placed label sits)
          labelX: (anchor.label_x / 100) * containerWidth,
          labelY: (anchor.label_y / 100) * containerHeight,
        };
      });
  }, [placedLabels, anchorMap, correctZoneIds, lineStyle, containerWidth, containerHeight]);

  if (lineStyle === 'none' || lines.length === 0) return null;

  return (
    <svg
      ref={svgRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 5 }}
      aria-hidden="true"
    >
      <defs>
        {/* Gradient for leader lines */}
        <linearGradient id="leader-line-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={lineColor} stopOpacity={0.8} />
          <stop offset="100%" stopColor={lineColor} stopOpacity={1} />
        </linearGradient>
      </defs>

      {lines.map((line) => {
        const pathD = generateLinePath(
          line.style,
          line.labelX, line.labelY,
          line.pinX, line.pinY,
        );

        return (
          <g key={line.id}>
            {/* Shadow path for depth */}
            <path
              d={pathD}
              fill="none"
              stroke="rgba(0,0,0,0.1)"
              strokeWidth={lineWidth + 2}
              strokeLinecap="round"
            />

            {/* Main line with optional draw-on animation */}
            <path
              d={pathD}
              fill="none"
              stroke={lineColor}
              strokeWidth={lineWidth}
              strokeLinecap="round"
              className={animate ? 'leader-line-animate' : ''}
              style={animate ? {
                strokeDasharray: 1000,
                strokeDashoffset: 0,
                animation: 'leader-line-draw 0.6s ease-out forwards',
              } : undefined}
            />

            {/* Pin marker at zone anchor */}
            {pinMarkerShape !== 'none' && (
              <PinMarker
                shape={pinMarkerShape}
                x={line.pinX}
                y={line.pinY}
                color={lineColor}
                size={5}
              />
            )}
          </g>
        );
      })}

      {/* CSS animation for draw-on effect */}
      <style>{`
        @keyframes leader-line-draw {
          from {
            stroke-dashoffset: 1000;
          }
          to {
            stroke-dashoffset: 0;
          }
        }
      `}</style>
    </svg>
  );
}
