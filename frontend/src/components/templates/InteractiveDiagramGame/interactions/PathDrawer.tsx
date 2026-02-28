'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { Zone, TracePath, PathProgress, AnimationSpec } from '../types';
import { useAnimation, DEFAULT_ANIMATIONS } from '../animations/useAnimation';

interface PathDrawerProps {
  zones: Zone[];
  paths: TracePath[];
  onPathComplete: (pathId: string) => void;
  onAllPathsComplete: () => void;
  // MF-2: Store integration for resume support
  storeProgress?: PathProgress | null;
  onWaypointVisited?: (pathId: string, waypointZoneId: string) => void;
  animations?: {
    pathProgress?: AnimationSpec;
    correctPlacement?: AnimationSpec;
    incorrectPlacement?: AnimationSpec;
  };
  pathColor?: string;
  feedbackMessages?: {
    complete?: string;
    progress?: string;
    wrongOrder?: string;
    notOnPath?: string;
  };
}

interface PathVisualizerProps {
  zones: Zone[];
  visitedWaypoints: string[];
  containerRef: React.RefObject<HTMLDivElement>;
  pathColor?: string;
}

function PathVisualizer({ zones, visitedWaypoints, containerRef, pathColor = '#22c55e' }: PathVisualizerProps) {
  const [lines, setLines] = useState<Array<{ x1: number; y1: number; x2: number; y2: number }>>([]);

  // Calculate line positions when waypoints change
  useEffect(() => {
    if (!containerRef.current || visitedWaypoints.length < 2) {
      setLines([]);
      return;
    }

    const container = containerRef.current;
    const rect = container.getBoundingClientRect();

    const newLines: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];

    for (let i = 0; i < visitedWaypoints.length - 1; i++) {
      const zone1 = zones.find((z) => z.id === visitedWaypoints[i]);
      const zone2 = zones.find((z) => z.id === visitedWaypoints[i + 1]);

      if (zone1 && zone2 && zone1.x != null && zone1.y != null && zone2.x != null && zone2.y != null) {
        newLines.push({
          x1: (zone1.x / 100) * rect.width,
          y1: (zone1.y / 100) * rect.height,
          x2: (zone2.x / 100) * rect.width,
          y2: (zone2.y / 100) * rect.height,
        });
      }
    }

    setLines(newLines);
  }, [zones, visitedWaypoints, containerRef]);

  if (lines.length === 0) return null;

  return (
    <svg className="absolute inset-0 pointer-events-none z-10">
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill={pathColor} />
        </marker>
      </defs>
      {lines.map((line, index) => (
        <line
          key={index}
          x1={line.x1}
          y1={line.y1}
          x2={line.x2}
          y2={line.y2}
          stroke={pathColor}
          strokeWidth="3"
          strokeDasharray="8,4"
          markerEnd="url(#arrowhead)"
          className="animate-path-draw"
          style={{
            animation: 'path_draw 0.5s ease-out forwards',
          }}
        />
      ))}
    </svg>
  );
}

interface PathZoneProps {
  zone: Zone;
  isNextWaypoint: boolean;
  isVisited: boolean;
  waypointNumber?: number;
  onClick: () => void;
  animationRef: React.RefCallback<HTMLDivElement>;
}

function PathZone({
  zone,
  isNextWaypoint,
  isVisited,
  waypointNumber,
  onClick,
  animationRef,
}: PathZoneProps) {
  const size = (zone.radius ?? 5) * 2;

  return (
    <div
      ref={animationRef}
      onClick={onClick}
      className={`
        absolute transform -translate-x-1/2 -translate-y-1/2
        cursor-pointer transition-all duration-200
        ${isVisited ? '' : ''}
      `}
      style={{
        left: `${zone.x}%`,
        top: `${zone.y}%`,
        width: `${size}%`,
        minWidth: '50px',
        minHeight: '50px',
      }}
    >
      <div
        className={`
          w-full h-full rounded-full border-3
          flex items-center justify-center
          transition-all duration-200
          ${
            isVisited
              ? 'bg-green-100 border-green-500'
              : isNextWaypoint
              ? 'bg-yellow-100 border-yellow-400 animate-pulse ring-4 ring-yellow-200'
              : 'bg-white/50 border-gray-300 hover:border-blue-400 hover:bg-blue-50'
          }
        `}
      >
        {isVisited && waypointNumber !== undefined && (
          <div className="w-7 h-7 bg-green-500 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-bold">{waypointNumber}</span>
          </div>
        )}
        {isNextWaypoint && !isVisited && (
          <div className="w-7 h-7 bg-yellow-400 rounded-full flex items-center justify-center">
            <span className="text-yellow-800 text-sm font-bold">?</span>
          </div>
        )}
      </div>

      {/* Zone label */}
      <div className="absolute left-1/2 -translate-x-1/2 top-full mt-1 z-20">
        <div className="bg-gray-800 text-white rounded px-2 py-1 text-xs whitespace-nowrap">
          {zone.label}
        </div>
      </div>
    </div>
  );
}

export default function PathDrawer({
  zones,
  paths,
  onPathComplete,
  onAllPathsComplete,
  storeProgress,
  onWaypointVisited,
  animations,
  pathColor,
  feedbackMessages: fbMsg,
}: PathDrawerProps) {
  const { animate } = useAnimation();
  const containerRef = useRef<HTMLDivElement>(null);

  // Track progress for each path — MF-2: init from storeProgress if resuming
  const [pathProgress, setPathProgress] = useState<Record<string, PathProgress>>(() => {
    const initial: Record<string, PathProgress> = {};
    paths.forEach((path) => {
      // If storeProgress matches this path, use it
      if (storeProgress && storeProgress.pathId === path.id) {
        initial[path.id] = { ...storeProgress };
      } else {
        initial[path.id] = {
          pathId: path.id,
          visitedWaypoints: [],
          isComplete: false,
        };
      }
    });
    return initial;
  });

  const [currentPathIndex, setCurrentPathIndex] = useState(0);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [zoneRefs, setZoneRefs] = useState<Map<string, HTMLDivElement>>(new Map());

  const currentPath = paths[currentPathIndex];
  const currentProgress = currentPath ? pathProgress[currentPath.id] : null;

  // Get sorted waypoints for current path
  const sortedWaypoints = currentPath
    ? [...currentPath.waypoints].sort((a, b) => a.order - b.order)
    : [];

  // Find the next expected waypoint
  const nextWaypointIndex = currentProgress?.visitedWaypoints.length || 0;
  const nextWaypoint = sortedWaypoints[nextWaypointIndex];

  const handleZoneClick = useCallback(
    (zoneId: string) => {
      if (!currentPath || !currentProgress) return;

      const zoneElement = zoneRefs.get(zoneId);
      const isCorrectNext = currentPath.requiresOrder
        ? nextWaypoint?.zoneId === zoneId
        : sortedWaypoints.some(
            (wp) =>
              wp.zoneId === zoneId &&
              !currentProgress.visitedWaypoints.includes(zoneId)
          );

      if (isCorrectNext) {
        // Correct waypoint clicked
        if (zoneElement) {
          animate(
            zoneElement,
            animations?.correctPlacement || DEFAULT_ANIMATIONS.correctPlacement
          );
        }

        const newVisited = [...currentProgress.visitedWaypoints, zoneId];
        const isPathComplete = newVisited.length === sortedWaypoints.length;

        setPathProgress((prev) => ({
          ...prev,
          [currentPath.id]: {
            ...prev[currentPath.id],
            visitedWaypoints: newVisited,
            isComplete: isPathComplete,
          },
        }));

        // MF-2: Notify store of waypoint visit
        onWaypointVisited?.(currentPath.id, zoneId);

        if (isPathComplete) {
          setFeedbackMessage(fbMsg?.complete ?? 'Path complete!');
          onPathComplete(currentPath.id);

          // Move to next path or complete
          if (currentPathIndex < paths.length - 1) {
            setTimeout(() => {
              setCurrentPathIndex((prev) => prev + 1);
              setFeedbackMessage(null);
            }, 1500);
          } else {
            setTimeout(() => {
              onAllPathsComplete();
            }, 1500);
          }
        } else {
          setFeedbackMessage(fbMsg?.progress ?? 'Good! Continue tracing...');
          setTimeout(() => setFeedbackMessage(null), 1000);
        }
      } else {
        // Wrong waypoint
        if (zoneElement) {
          animate(
            zoneElement,
            animations?.incorrectPlacement || DEFAULT_ANIMATIONS.incorrectPlacement
          );
        }
        setFeedbackMessage(
          currentPath.requiresOrder
            ? (fbMsg?.wrongOrder ?? 'Wrong order! Follow the path sequence.')
            : (fbMsg?.notOnPath ?? 'This point is already visited or not on the path.')
        );
        setTimeout(() => setFeedbackMessage(null), 2000);
      }
    },
    [
      currentPath,
      currentProgress,
      nextWaypoint,
      sortedWaypoints,
      animate,
      animations,
      onPathComplete,
      onAllPathsComplete,
      currentPathIndex,
      paths.length,
      zoneRefs,
    ]
  );

  // Create ref callback for zones
  const createZoneRef = useCallback(
    (zoneId: string) => (el: HTMLDivElement | null) => {
      if (el) {
        setZoneRefs((prev) => new Map(prev).set(zoneId, el));
      }
    },
    []
  );

  const isZoneOnPath = (zoneId: string) => {
    return sortedWaypoints.some((wp) => wp.zoneId === zoneId);
  };

  const isZoneVisited = (zoneId: string) => {
    return currentProgress?.visitedWaypoints.includes(zoneId) || false;
  };

  const getWaypointNumber = (zoneId: string): number | undefined => {
    const index = currentProgress?.visitedWaypoints.indexOf(zoneId);
    return index !== undefined && index >= 0 ? index + 1 : undefined;
  };

  return (
    <div ref={containerRef} className="relative w-full h-full">
      {/* Path description */}
      {currentPath && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20">
          <div className="bg-blue-600 text-white rounded-lg px-4 py-2 shadow-lg">
            <p className="text-sm font-medium">{currentPath.description}</p>
          </div>
        </div>
      )}

      {/* Progress indicator */}
      <div className="absolute top-4 right-4 z-20">
        <div className="bg-white rounded-lg px-3 py-2 shadow-md">
          <p className="text-sm text-gray-700">
            Path {currentPathIndex + 1} of {paths.length}
          </p>
          <p className="text-xs text-gray-500">
            {currentProgress?.visitedWaypoints.length || 0} / {sortedWaypoints.length} waypoints
          </p>
        </div>
      </div>

      {/* Path visualization (lines between visited waypoints) */}
      {currentProgress && (
        <PathVisualizer
          zones={zones}
          visitedWaypoints={currentProgress.visitedWaypoints}
          containerRef={containerRef}
          pathColor={pathColor}
        />
      )}

      {/* Path zones */}
      {zones.map((zone) => (
        <PathZone
          key={zone.id}
          zone={zone}
          isNextWaypoint={isZoneOnPath(zone.id) && !isZoneVisited(zone.id)}
          isVisited={isZoneVisited(zone.id)}
          waypointNumber={getWaypointNumber(zone.id)}
          onClick={() => handleZoneClick(zone.id)}
          animationRef={createZoneRef(zone.id)}
        />
      ))}

      {/* Feedback message */}
      {feedbackMessage && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 animate-fade-in">
          <div
            className={`rounded-lg px-4 py-2 shadow-lg ${
              feedbackMessage.includes('complete') || feedbackMessage.includes('Good')
                ? 'bg-green-500 text-white'
                : 'bg-orange-500 text-white'
            }`}
          >
            <p className="text-sm font-medium">{feedbackMessage}</p>
          </div>
        </div>
      )}
    </div>
  );
}
