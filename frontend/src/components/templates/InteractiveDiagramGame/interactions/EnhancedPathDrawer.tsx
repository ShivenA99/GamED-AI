'use client';

import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Zone, TracePath, TracePathProgress, TracePathConfig, MechanicAction, ActionResult } from '../types';

export interface EnhancedPathDrawerProps {
  zones: Zone[];
  paths: TracePath[];
  config?: TracePathConfig;
  assetUrl?: string;
  width?: number;
  height?: number;
  /** Source-of-truth progress from store. Component derives path state from this. */
  traceProgress?: TracePathProgress | null;
  /** Unified action dispatch — the only output channel. */
  onAction: (action: MechanicAction) => ActionResult | null;
}

// ─── Particle Shapes ────────────────────────────────────────────────
type ParticleTheme = 'dots' | 'arrows' | 'droplets' | 'cells' | 'electrons';

function ParticleShape({ theme, color, size }: { theme: ParticleTheme; color: string; size: number }) {
  const half = size / 2;
  switch (theme) {
    case 'arrows':
      return (
        <polygon
          points={`0,${half} ${size},${half} ${half},0`}
          fill={color}
        />
      );
    case 'droplets':
      return (
        <>
          <circle cx={half} cy={half + 1} r={half * 0.7} fill={color} />
          <polygon points={`${half},0 ${half - 2},${half} ${half + 2},${half}`} fill={color} />
        </>
      );
    case 'cells':
      return (
        <>
          <circle cx={half} cy={half} r={half} fill={color} opacity={0.7} />
          <circle cx={half} cy={half} r={half * 0.4} fill={color} />
        </>
      );
    case 'electrons':
      return (
        <>
          <circle cx={half} cy={half} r={half * 0.6} fill={color} />
          <circle cx={half} cy={half} r={half} fill="none" stroke={color} strokeWidth={0.5} opacity={0.5} />
        </>
      );
    case 'dots':
    default:
      return <circle cx={half} cy={half} r={half} fill={color} />;
  }
}

// ─── Animated Particles Along Path ──────────────────────────────────
function AnimatedParticles({
  pathData,
  theme = 'dots',
  color = '#3b82f6',
  speed = 'medium',
  count = 5,
  particleSize = 6,
  active,
}: {
  pathData: string;
  theme: ParticleTheme;
  color: string;
  speed: 'slow' | 'medium' | 'fast';
  count: number;
  particleSize: number;
  active: boolean;
}) {
  const pathRef = useRef<SVGPathElement>(null);
  const speedMs = speed === 'slow' ? 4000 : speed === 'fast' ? 1500 : 2500;

  if (!active || !pathData) return null;

  return (
    <>
      {/* Invisible path for length measurement */}
      <path ref={pathRef} d={pathData} fill="none" stroke="none" />
      {Array.from({ length: count }).map((_, i) => (
        <g key={i}>
          <animateMotion
            dur={`${speedMs}ms`}
            repeatCount="indefinite"
            begin={`${(i / count) * speedMs}ms`}
            path={pathData}
            rotate="auto"
          >
            {/* Empty animate to avoid React warning */}
          </animateMotion>
          {/* We need a group with animateMotion inside */}
        </g>
      ))}
      {/* Use CSS animation approach for better browser support */}
      {Array.from({ length: count }).map((_, i) => {
        const offset = (i / count) * 100;
        return (
          <g key={`particle-${i}`}>
            <svg
              width={particleSize}
              height={particleSize}
              overflow="visible"
            >
              <ParticleShape theme={theme} color={color} size={particleSize} />
              <animateMotion
                dur={`${speedMs}ms`}
                repeatCount="indefinite"
                begin={`-${(i / count) * speedMs}ms`}
                rotate="auto"
              >
                <mpath href={`#${pathData.substring(0, 20).replace(/[^a-zA-Z0-9]/g, '')}`} />
              </animateMotion>
            </svg>
          </g>
        );
      })}
    </>
  );
}

// ─── SVG Path Segment ───────────────────────────────────────────────
function PathSegment({
  fromZone,
  toZone,
  svgPathData,
  strokeColor,
  strokeWidth,
  isActive,
  isCompleted,
  showArrows,
  segmentIndex,
}: {
  fromZone: Zone;
  toZone: Zone;
  svgPathData?: string;
  strokeColor: string;
  strokeWidth: number;
  isActive: boolean;
  isCompleted: boolean;
  showArrows: boolean;
  segmentIndex: number;
}) {
  // Default: generate curved path between zone centers
  const x1 = fromZone.x ?? 50;
  const y1 = fromZone.y ?? 50;
  const x2 = toZone.x ?? 50;
  const y2 = toZone.y ?? 50;

  const pathId = `segment-${segmentIndex}`;

  // Generate a nice curved path if no explicit SVG data provided
  const pathD = useMemo(() => {
    if (svgPathData) return svgPathData;

    // Create a gentle curve between points
    const dx = x2 - x1;
    const dy = y2 - y1;
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    // Perpendicular offset for curve
    const offset = Math.min(Math.abs(dx), Math.abs(dy)) * 0.15;
    const cpX = midX - (dy > 0 ? offset : -offset);
    const cpY = midY + (dx > 0 ? offset : -offset);

    return `M ${x1} ${y1} Q ${cpX} ${cpY} ${x2} ${y2}`;
  }, [svgPathData, x1, y1, x2, y2]);

  const pathLength = 200; // Approximation for animation

  return (
    <g>
      {/* Shadow path */}
      <path
        d={pathD}
        fill="none"
        stroke="rgba(0,0,0,0.1)"
        strokeWidth={strokeWidth + 2}
        strokeLinecap="round"
      />
      {/* Main path */}
      <path
        id={pathId}
        d={pathD}
        fill="none"
        stroke={isCompleted ? strokeColor : 'rgba(148,163,184,0.4)'}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={isCompleted ? 'none' : '6,4'}
        style={isCompleted ? {
          strokeDasharray: pathLength,
          strokeDashoffset: 0,
          animation: `drawPath 0.6s ease-out forwards`,
        } : undefined}
      />
      {/* Direction arrows along path */}
      {showArrows && isCompleted && (
        <>
          {[0.3, 0.6, 0.9].map((pct) => {
            // Approximate arrow positions along the path
            const ax = x1 + (x2 - x1) * pct;
            const ay = y1 + (y2 - y1) * pct;
            const angle = Math.atan2(y2 - y1, x2 - x1) * (180 / Math.PI);
            return (
              <g key={pct} transform={`translate(${ax}, ${ay}) rotate(${angle})`}>
                <polygon
                  points="-4,-3 4,0 -4,3"
                  fill={strokeColor}
                  opacity={0.6}
                />
              </g>
            );
          })}
        </>
      )}
    </g>
  );
}

// ─── Waypoint Marker ────────────────────────────────────────────────
function WaypointMarker({
  zone,
  waypointType = 'standard',
  isVisited,
  isNext,
  isTerminus,
  waypointNumber,
  showLabel,
  onClick,
}: {
  zone: Zone;
  waypointType: 'standard' | 'gate' | 'branch_point' | 'terminus';
  isVisited: boolean;
  isNext: boolean;
  isTerminus: boolean;
  waypointNumber?: number;
  showLabel: boolean;
  onClick: () => void;
}) {
  const zoneX = zone.x ?? 50;
  const zoneY = zone.y ?? 50;
  const radius = zone.radius ?? 4;

  // No special styling for "next" waypoint — all unvisited waypoints look neutral
  // to avoid revealing the correct order
  const markerColor = isVisited ? '#22c55e' : '#94a3b8';
  const bgColor = isVisited ? 'bg-green-100' : 'bg-white/60';
  const borderColor = isVisited ? 'border-green-500' : 'border-gray-300 hover:border-blue-400';

  const iconForType = () => {
    switch (waypointType) {
      case 'gate':
        return isVisited ? '🔓' : '🔒';
      case 'branch_point':
        return '⑂';
      case 'terminus':
        return isVisited ? '🏁' : '⊕';
      default:
        if (isVisited && waypointNumber !== undefined) {
          return String(waypointNumber);
        }
        return '·';
    }
  };

  return (
    <div
      className="absolute transform -translate-x-1/2 -translate-y-1/2"
      style={{
        left: `${zoneX}%`,
        top: `${zoneY}%`,
        zIndex: isNext ? 20 : 10,
      }}
    >
      <motion.button
        onClick={onClick}
        className={`
          w-10 h-10 rounded-full border-3 flex items-center justify-center
          cursor-pointer transition-colors duration-200
          ${bgColor} ${borderColor} shadow-md
          hover:scale-110
        `}
        animate={
          isVisited
            ? { scale: [1, 1.15, 1], transition: { duration: 0.3 } }
            : {}
        }
        whileHover={{ scale: 1.15 }}
        whileTap={{ scale: 0.95 }}
      >
        {waypointType === 'gate' && !isVisited ? (
          <span className="text-lg">🔒</span>
        ) : isVisited ? (
          waypointNumber !== undefined ? (
            <span className="text-sm font-bold text-green-700">{waypointNumber}</span>
          ) : (
            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          )
        ) : (
          <span className="w-2 h-2 rounded-full bg-gray-400" />
        )}
      </motion.button>

      {/* Gate open animation */}
      {waypointType === 'gate' && isVisited && (
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1.5, opacity: 0 }}
          transition={{ duration: 0.8 }}
          className="absolute inset-0 rounded-full border-2 border-green-400"
        />
      )}

      {/* Label */}
      {showLabel && (
        <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 whitespace-nowrap">
          <span className={`
            text-xs px-2 py-0.5 rounded shadow-sm
            ${isVisited
              ? 'bg-green-100 text-green-800'
              : 'bg-gray-100 text-gray-600'
            }
          `}>
            {zone.label}
          </span>
        </div>
      )}
    </div>
  );
}

// ─── Color Transition Path ──────────────────────────────────────────
function ColorTransitionPaths({
  zones,
  visitedWaypoints,
  pathWaypoints,
  baseColor,
}: {
  zones: Zone[];
  visitedWaypoints: string[];
  pathWaypoints: { zoneId: string; order: number }[];
  baseColor: string;
}) {
  // Create gradient segments for visited path
  const gradientColors = ['#3b82f6', '#8b5cf6', '#ec4899', '#ef4444'];

  return (
    <>
      <defs>
        {visitedWaypoints.map((_, i) => {
          if (i === 0) return null;
          const colorIdx1 = Math.floor((i - 1) / Math.max(1, visitedWaypoints.length - 1) * (gradientColors.length - 1));
          const colorIdx2 = Math.min(colorIdx1 + 1, gradientColors.length - 1);
          return (
            <linearGradient key={`grad-${i}`} id={`pathGrad-${i}`}>
              <stop offset="0%" stopColor={gradientColors[colorIdx1]} />
              <stop offset="100%" stopColor={gradientColors[colorIdx2]} />
            </linearGradient>
          );
        })}
      </defs>
      {visitedWaypoints.map((zoneId, i) => {
        if (i === 0) return null;
        const prevId = visitedWaypoints[i - 1];
        const z1 = zones.find(z => z.id === prevId);
        const z2 = zones.find(z => z.id === zoneId);
        if (!z1 || !z2) return null;

        const x1 = z1.x ?? 50;
        const y1 = z1.y ?? 50;
        const x2 = z2.x ?? 50;
        const y2 = z2.y ?? 50;
        const dx = x2 - x1;
        const dy = y2 - y1;
        const offset = Math.min(Math.abs(dx), Math.abs(dy)) * 0.15;
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        const cpX = midX - (dy > 0 ? offset : -offset);
        const cpY = midY + (dx > 0 ? offset : -offset);

        return (
          <motion.path
            key={`color-${i}`}
            d={`M ${x1} ${y1} Q ${cpX} ${cpY} ${x2} ${y2}`}
            fill="none"
            stroke={`url(#pathGrad-${i})`}
            strokeWidth={4}
            strokeLinecap="round"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        );
      })}
    </>
  );
}

// ─── Flowing Particles Layer ────────────────────────────────────────
function FlowingParticles({
  zones,
  visitedWaypoints,
  theme,
  color,
  speed,
}: {
  zones: Zone[];
  visitedWaypoints: string[];
  theme: ParticleTheme;
  color: string;
  speed: 'slow' | 'medium' | 'fast';
}) {
  const [particles, setParticles] = useState<Array<{ id: number; progress: number; segmentIndex: number }>>([]);
  const animRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);

  const speedFactor = speed === 'slow' ? 0.15 : speed === 'fast' ? 0.5 : 0.3;

  // Build path points
  const pathPoints = useMemo(() => {
    return visitedWaypoints.map(id => {
      const z = zones.find(z => z.id === id);
      return z ? { x: z.x ?? 50, y: z.y ?? 50 } : null;
    }).filter(Boolean) as { x: number; y: number }[];
  }, [zones, visitedWaypoints]);

  // Animate particles
  useEffect(() => {
    if (pathPoints.length < 2) {
      setParticles([]);
      return;
    }

    const numParticles = Math.min(pathPoints.length * 2, 8);
    const initialParticles = Array.from({ length: numParticles }, (_, i) => ({
      id: i,
      progress: (i / numParticles) * (pathPoints.length - 1),
      segmentIndex: Math.floor((i / numParticles) * (pathPoints.length - 1)),
    }));
    setParticles(initialParticles);

    const animate = (time: number) => {
      if (!lastTimeRef.current) lastTimeRef.current = time;
      const dt = (time - lastTimeRef.current) / 1000;
      lastTimeRef.current = time;

      setParticles(prev => prev.map(p => {
        let newProgress = p.progress + speedFactor * dt;
        if (newProgress >= pathPoints.length - 1) {
          newProgress = 0; // Loop
        }
        return {
          ...p,
          progress: newProgress,
          segmentIndex: Math.floor(newProgress),
        };
      }));

      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [pathPoints, speedFactor]);

  if (pathPoints.length < 2) return null;

  return (
    <>
      {particles.map(p => {
        const segIdx = Math.min(p.segmentIndex, pathPoints.length - 2);
        const t = p.progress - segIdx;
        const p1 = pathPoints[segIdx];
        const p2 = pathPoints[segIdx + 1];
        if (!p1 || !p2) return null;

        const x = p1.x + (p2.x - p1.x) * t;
        const y = p1.y + (p2.y - p1.y) * t;

        // Calculate rotation for directional particles
        const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x) * (180 / Math.PI);

        return (
          <g
            key={p.id}
            transform={`translate(${x}, ${y}) rotate(${theme === 'dots' || theme === 'cells' ? 0 : angle})`}
            opacity={0.8}
          >
            <ParticleShape theme={theme} color={color} size={5} />
          </g>
        );
      })}
    </>
  );
}

// ─── Path Progress Banner ───────────────────────────────────────────
function PathBanner({
  description,
  pathIndex,
  totalPaths,
  visitedCount,
  totalWaypoints,
  isComplete,
}: {
  description: string;
  pathIndex: number;
  totalPaths: number;
  visitedCount: number;
  totalWaypoints: number;
  isComplete: boolean;
}) {
  const progressPct = totalWaypoints > 0 ? (visitedCount / totalWaypoints) * 100 : 0;

  return (
    <motion.div
      key={description}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full mb-4"
    >
      {/* Path description */}
      <div className={`
        rounded-xl px-6 py-4 shadow-lg
        ${isComplete
          ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white'
          : 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white'
        }
      `}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-sm font-bold flex-shrink-0">
              {isComplete ? '✓' : `${pathIndex + 1}`}
            </div>
            <p className="text-base font-medium leading-snug">{description}</p>
          </div>
          <div className="flex-shrink-0 ml-4 flex items-center gap-3">
            {totalPaths > 1 && (
              <span className="text-sm text-white/70 bg-white/10 px-3 py-1 rounded-full">
                Path {pathIndex + 1}/{totalPaths}
              </span>
            )}
            <span className="text-sm text-white/70 bg-white/10 px-3 py-1 rounded-full">
              {visitedCount}/{totalWaypoints}
            </span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-3 w-full h-1.5 bg-white/20 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-white/70 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progressPct}%` }}
            transition={{ type: 'spring', stiffness: 80 }}
          />
        </div>
      </div>
    </motion.div>
  );
}

// ─── Completion Flow Animation ──────────────────────────────────────
function CompletionFlowAnimation({
  zones,
  visitedWaypoints,
  theme,
  show,
}: {
  zones: Zone[];
  visitedWaypoints: string[];
  theme: ParticleTheme;
  show: boolean;
}) {
  if (!show || visitedWaypoints.length < 2) return null;

  const pathPoints = visitedWaypoints.map(id => {
    const z = zones.find(z => z.id === id);
    return z ? { x: z.x ?? 50, y: z.y ?? 50 } : null;
  }).filter(Boolean) as { x: number; y: number }[];

  // Create a single long animation path
  const pathParts = pathPoints.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`));
  const fullPath = pathParts.join(' ');

  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Glow effect on completed path */}
      <path
        d={fullPath}
        fill="none"
        stroke="#22c55e"
        strokeWidth={6}
        strokeLinecap="round"
        opacity={0.3}
      >
        <animate
          attributeName="opacity"
          values="0.3;0.6;0.3"
          dur="2s"
          repeatCount="indefinite"
        />
      </path>
      {/* Flow particles along complete path */}
      {Array.from({ length: 6 }).map((_, i) => (
        <circle key={i} r={3} fill="#22c55e">
          <animateMotion
            dur="3s"
            repeatCount="indefinite"
            begin={`${(i / 6) * -3}s`}
            path={fullPath}
          />
          <animate
            attributeName="opacity"
            values="0.4;1;0.4"
            dur="3s"
            repeatCount="indefinite"
            begin={`${(i / 6) * -3}s`}
          />
        </circle>
      ))}
    </motion.g>
  );
}

// ─── Main Component ─────────────────────────────────────────────────
export function EnhancedPathDrawer({
  zones,
  paths,
  config,
  assetUrl,
  width = 800,
  height = 600,
  traceProgress,
  onAction,
}: EnhancedPathDrawerProps) {
  const {
    pathType = 'linear',
    drawingMode = 'click_waypoints',
    particleTheme = 'dots',
    particleSpeed = 'medium',
    colorTransitionEnabled = false,
    showDirectionArrows = true,
    showWaypointLabels = true,
    showFullFlowOnComplete = true,
    instructions,
    submitMode = 'batch',  // Default: submit-based scoring (no path/arrow hints)
  } = config || {};

  const isBatchMode = submitMode === 'batch';

  const containerRef = useRef<HTMLDivElement>(null);

  // Derive persistent state from traceProgress prop (source of truth)
  const currentPathIndex = traceProgress?.currentPathIndex ?? 0;
  const pathProgressMap = useMemo(() => {
    const base: Record<string, { visited: string[]; complete: boolean }> = {};
    paths.forEach(p => { base[p.id] = { visited: [], complete: false }; });
    if (traceProgress?.pathProgressMap) {
      for (const [pathId, prog] of Object.entries(traceProgress.pathProgressMap)) {
        base[pathId] = { visited: prog.visitedWaypoints, complete: prog.isComplete };
      }
    }
    return base;
  }, [paths, traceProgress]);

  // Transient visual state only
  const [feedbackMessage, setFeedbackMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [showCompletionFlow, setShowCompletionFlow] = useState(false);

  // Batch mode state — transient UI scratchpad (user building a selection)
  const [batchSelected, setBatchSelected] = useState<string[]>([]);
  const [batchSubmitted, setBatchSubmitted] = useState(false);
  const [batchResults, setBatchResults] = useState<Record<string, 'correct' | 'incorrect' | 'missed'>>({});

  const currentPath = paths[currentPathIndex];
  const currentProgress = currentPath ? pathProgressMap[currentPath.id] : null;

  const sortedWaypoints = useMemo(() => {
    if (!currentPath) return [];
    return [...currentPath.waypoints].sort((a, b) => a.order - b.order);
  }, [currentPath]);

  const nextWaypointIndex = currentProgress?.visited.length || 0;
  const nextWaypoint = sortedWaypoints[nextWaypointIndex];

  // Particle color based on theme
  const particleColor = useMemo(() => {
    switch (particleTheme) {
      case 'droplets': return '#3b82f6';
      case 'cells': return '#ef4444';
      case 'electrons': return '#eab308';
      case 'arrows': return '#22c55e';
      default: return '#8b5cf6';
    }
  }, [particleTheme]);

  // ── Batch mode: toggle zone selection ────────────────────────────
  const handleBatchZoneClick = useCallback((zoneId: string) => {
    if (!currentPath || batchSubmitted) return;
    setBatchSelected(prev =>
      prev.includes(zoneId)
        ? prev.filter(id => id !== zoneId)
        : [...prev, zoneId]
    );
  }, [currentPath, batchSubmitted]);

  const handleBatchSubmit = useCallback(() => {
    if (!currentPath) return;
    setBatchSubmitted(true);

    // Emit unified action — store handles validation and progress update
    onAction({ type: 'submit_path', mechanic: 'trace_path', pathId: currentPath.id, selectedZoneIds: [...batchSelected] });

    // Local visual feedback based on config data
    const expectedZoneIds = sortedWaypoints.map(wp => wp.zoneId);
    const results: Record<string, 'correct' | 'incorrect' | 'missed'> = {};

    if (currentPath.requiresOrder) {
      expectedZoneIds.forEach((expectedId, i) => {
        if (i < batchSelected.length && batchSelected[i] === expectedId) {
          results[expectedId] = 'correct';
        } else {
          results[expectedId] = 'missed';
        }
      });
      batchSelected.forEach(id => {
        if (!(id in results)) results[id] = 'incorrect';
      });
    } else {
      const expectedSet = new Set(expectedZoneIds);
      const selectedSet = new Set(batchSelected);
      expectedZoneIds.forEach(id => {
        results[id] = selectedSet.has(id) ? 'correct' : 'missed';
      });
      batchSelected.forEach(id => {
        if (!expectedSet.has(id)) results[id] = 'incorrect';
      });
    }

    setBatchResults(results);

    const correctCount = Object.values(results).filter(r => r === 'correct').length;
    const total = expectedZoneIds.length;

    if (correctCount === total) {
      setFeedbackMessage({ text: 'Perfect! Path traced correctly!', type: 'success' });
      if (showFullFlowOnComplete) setShowCompletionFlow(true);
    } else {
      setFeedbackMessage({
        text: `${correctCount}/${total} correct. ${total - correctCount} missed or wrong.`,
        type: 'error',
      });
    }
  }, [currentPath, batchSelected, sortedWaypoints, onAction, showFullFlowOnComplete]);

  const handleBatchRetry = useCallback(() => {
    setBatchSelected([]);
    setBatchSubmitted(false);
    setBatchResults({});
    setFeedbackMessage(null);
  }, []);

  // ── Immediate mode: click handler ────────────────────────
  const handleImmediateZoneClick = useCallback((zoneId: string) => {
    if (!currentPath || !currentProgress || currentProgress.complete) return;

    const isCorrectNext = currentPath.requiresOrder
      ? nextWaypoint?.zoneId === zoneId
      : sortedWaypoints.some(
          wp => wp.zoneId === zoneId && !currentProgress.visited.includes(zoneId)
        );

    if (isCorrectNext) {
      // Emit unified action — store handles progress update and completion
      onAction({ type: 'visit_waypoint', mechanic: 'trace_path', pathId: currentPath.id, zoneId });

      const newVisited = [...currentProgress.visited, zoneId];
      const pathDone = newVisited.length === sortedWaypoints.length;

      if (pathDone) {
        setFeedbackMessage({ text: 'Path complete!', type: 'success' });
        if (showFullFlowOnComplete) setShowCompletionFlow(true);

        if (currentPathIndex < paths.length - 1) {
          setTimeout(() => {
            setFeedbackMessage(null);
            setShowCompletionFlow(false);
          }, 2000);
        }
      } else {
        setFeedbackMessage({ text: 'Good! Continue tracing...', type: 'info' });
        setTimeout(() => setFeedbackMessage(null), 1000);
      }
    } else {
      setFeedbackMessage({
        text: currentPath.requiresOrder
          ? 'Wrong order! Follow the path sequence.'
          : 'Already visited or not on this path.',
        type: 'error',
      });
      setTimeout(() => setFeedbackMessage(null), 2000);
    }
  }, [currentPath, currentProgress, nextWaypoint, sortedWaypoints, onAction, currentPathIndex, paths.length, showFullFlowOnComplete]);

  const handleZoneClick = isBatchMode ? handleBatchZoneClick : handleImmediateZoneClick;

  const isOnCurrentPath = (zoneId: string) => sortedWaypoints.some(wp => wp.zoneId === zoneId);
  const isVisited = (zoneId: string) => currentProgress?.visited.includes(zoneId) || false;
  const getWaypointNumber = (zoneId: string) => {
    if (isBatchMode) return undefined; // Never show numbers in batch mode
    const idx = currentProgress?.visited.indexOf(zoneId);
    return idx !== undefined && idx >= 0 ? idx + 1 : undefined;
  };
  const getWaypointType = (zoneId: string) => {
    const wp = sortedWaypoints.find(wp => wp.zoneId === zoneId);
    return wp?.type || 'standard';
  };

  // Batch mode: visual state per zone
  const getBatchZoneState = (zoneId: string) => {
    if (batchSubmitted && batchResults[zoneId]) return batchResults[zoneId];
    if (batchSelected.includes(zoneId)) return 'selected';
    return 'default';
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Instructions */}
      {instructions && (
        <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-300">{instructions}</p>
        </div>
      )}

      {/* Path banner */}
      {currentPath && (
        <PathBanner
          description={currentPath.description}
          pathIndex={currentPathIndex}
          totalPaths={paths.length}
          visitedCount={currentProgress?.visited.length || 0}
          totalWaypoints={sortedWaypoints.length}
          isComplete={currentProgress?.complete || false}
        />
      )}

      {/* Diagram container */}
      <div
        ref={containerRef}
        className="relative rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800 mx-auto"
        style={{ maxWidth: `${width}px`, aspectRatio: `${width} / ${height}` }}
      >
        {/* Diagram image */}
        {assetUrl && (
          <img
            src={assetUrl}
            alt="Educational diagram"
            className="w-full h-full object-contain"
          />
        )}

        {/* SVG overlay for paths and particles */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox={`0 0 100 100`}
          preserveAspectRatio="none"
        >
          {/* Path segments — only show COMPLETED segments (never preview future path) */}
          {sortedWaypoints.map((wp, i) => {
            if (i === 0) return null;
            const prevWp = sortedWaypoints[i - 1];
            const z1 = zones.find(z => z.id === prevWp.zoneId);
            const z2 = zones.find(z => z.id === wp.zoneId);
            if (!z1 || !z2) return null;

            const isSegmentCompleted = isVisited(prevWp.zoneId) && isVisited(wp.zoneId);

            // Only render segments that are already completed — never show future path
            if (!isSegmentCompleted) return null;

            return (
              <PathSegment
                key={`seg-${i}`}
                fromZone={z1}
                toZone={z2}
                svgPathData={wp.svg_path_data}
                strokeColor={'#22c55e'}
                strokeWidth={2.5}
                isActive={false}
                isCompleted={true}
                showArrows={showDirectionArrows}
                segmentIndex={i}
              />
            );
          })}

          {/* Batch mode: reveal correct path after submit */}
          {isBatchMode && batchSubmitted && sortedWaypoints.map((wp, i) => {
            if (i === 0) return null;
            const prevWp = sortedWaypoints[i - 1];
            const z1 = zones.find(z => z.id === prevWp.zoneId);
            const z2 = zones.find(z => z.id === wp.zoneId);
            if (!z1 || !z2) return null;

            return (
              <PathSegment
                key={`reveal-${i}`}
                fromZone={z1}
                toZone={z2}
                svgPathData={wp.svg_path_data}
                strokeColor={'#22c55e'}
                strokeWidth={2.5}
                isActive={false}
                isCompleted={true}
                showArrows={showDirectionArrows}
                segmentIndex={i}
              />
            );
          })}

          {/* Color transition overlay */}
          {colorTransitionEnabled && currentProgress && (
            <ColorTransitionPaths
              zones={zones}
              visitedWaypoints={currentProgress.visited}
              pathWaypoints={sortedWaypoints}
              baseColor={particleColor}
            />
          )}

          {/* Flowing particles along visited segments */}
          {currentProgress && currentProgress.visited.length >= 2 && !currentProgress.complete && (
            <FlowingParticles
              zones={zones}
              visitedWaypoints={currentProgress.visited}
              theme={particleTheme}
              color={particleColor}
              speed={particleSpeed}
            />
          )}

          {/* Completion flow animation */}
          {showCompletionFlow && currentProgress && (
            <CompletionFlowAnimation
              zones={zones}
              visitedWaypoints={currentProgress.visited}
              theme={particleTheme}
              show={showCompletionFlow}
            />
          )}
        </svg>

        {/* Waypoint markers (HTML layer on top) */}
        {zones.filter(z => isOnCurrentPath(z.id)).map(zone => {
          if (isBatchMode) {
            // Batch mode: custom visual states
            const batchState = getBatchZoneState(zone.id);
            const bgColor = batchState === 'correct' ? 'bg-green-100' : batchState === 'incorrect' ? 'bg-red-100' : batchState === 'missed' ? 'bg-orange-100' : batchState === 'selected' ? 'bg-blue-100' : 'bg-white/60';
            const borderColor = batchState === 'correct' ? 'border-green-500' : batchState === 'incorrect' ? 'border-red-500' : batchState === 'missed' ? 'border-orange-400' : batchState === 'selected' ? 'border-blue-500' : 'border-gray-300';
            const zoneX = zone.x ?? 50;
            const zoneY = zone.y ?? 50;

            return (
              <div
                key={zone.id}
                className="absolute transform -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${zoneX}%`, top: `${zoneY}%`, zIndex: 10 }}
              >
                <motion.button
                  onClick={() => handleZoneClick(zone.id)}
                  className={`w-10 h-10 rounded-full border-3 flex items-center justify-center cursor-pointer transition-colors duration-200 shadow-md hover:scale-110 ${bgColor} ${borderColor}`}
                  whileHover={{ scale: 1.15 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {batchState === 'correct' ? (
                    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                  ) : batchState === 'incorrect' ? (
                    <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" /></svg>
                  ) : batchState === 'missed' ? (
                    <span className="w-3 h-3 rounded-full bg-orange-400" />
                  ) : batchState === 'selected' ? (
                    <span className="text-sm font-bold text-blue-700">{batchSelected.indexOf(zone.id) + 1}</span>
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-gray-400" />
                  )}
                </motion.button>
                {showWaypointLabels && (
                  <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 whitespace-nowrap">
                    <span className={`text-xs px-2 py-0.5 rounded shadow-sm ${batchState === 'selected' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'}`}>
                      {zone.label}
                    </span>
                  </div>
                )}
              </div>
            );
          }

          // Immediate mode: WaypointMarker — no "next" hint to avoid revealing answer
          return (
            <WaypointMarker
              key={zone.id}
              zone={zone}
              waypointType={getWaypointType(zone.id)}
              isVisited={isVisited(zone.id)}
              isNext={false}
              isTerminus={
                sortedWaypoints.length > 0 &&
                sortedWaypoints[sortedWaypoints.length - 1].zoneId === zone.id
              }
              waypointNumber={getWaypointNumber(zone.id)}
              showLabel={showWaypointLabels}
              onClick={() => handleZoneClick(zone.id)}
            />
          );
        })}
      </div>

      {/* Batch mode: Submit / Retry buttons */}
      {isBatchMode && !batchSubmitted && batchSelected.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 flex justify-center"
        >
          <button
            onClick={handleBatchSubmit}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg transition-colors"
          >
            Submit Path ({batchSelected.length} selected)
          </button>
        </motion.div>
      )}
      {isBatchMode && batchSubmitted && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-4 flex justify-center"
        >
          <button
            onClick={handleBatchRetry}
            className="px-6 py-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 font-semibold rounded-xl shadow transition-colors"
          >
            Try Again
          </button>
        </motion.div>
      )}

      {/* Feedback message */}
      <AnimatePresence>
        {feedbackMessage && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-3"
          >
            <div className={`
              rounded-lg px-4 py-3 shadow-md text-center
              ${feedbackMessage.type === 'success'
                ? 'bg-green-50 dark:bg-green-900/20 border border-green-300 dark:border-green-700 text-green-800 dark:text-green-200'
                : feedbackMessage.type === 'error'
                ? 'bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700 text-red-800 dark:text-red-200'
                : 'bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200'
              }
            `}>
              <p className="text-sm font-medium">{feedbackMessage.text}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* All paths complete */}
      <AnimatePresence>
        {paths.every(p => pathProgressMap[p.id]?.complete) && paths.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 border-2 border-green-300 dark:border-green-700 rounded-xl text-center"
          >
            <p className="text-lg font-bold text-green-800 dark:text-green-200">🎯 All paths traced!</p>
            <p className="text-sm text-green-600 dark:text-green-400 mt-1">
              {paths.length} path{paths.length > 1 ? 's' : ''} completed
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default EnhancedPathDrawer;
