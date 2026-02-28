'use client';

import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragStartEvent,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
  DragOverlay,
  useDroppable,
} from '@dnd-kit/core';
import { Zone, ZoneGroup, Label, PlacedLabel, HierarchyState, AnimationSpec } from '../types';
import { useAnimation, DEFAULT_ANIMATIONS } from '../animations/useAnimation';
import DraggableLabel from '../DraggableLabel';

interface HierarchyControllerProps {
  zones: Zone[];
  zoneGroups: ZoneGroup[];
  labels: Label[];
  onLabelPlace: (labelId: string, zoneId: string, isCorrect: boolean) => void;
  onGroupComplete: (groupId: string) => void;
  onAllComplete: () => void;
  animations?: {
    correctPlacement?: AnimationSpec;
    incorrectPlacement?: AnimationSpec;
  };
  // Diagram image props
  assetUrl?: string;
  assetPrompt?: string;
  width?: number;
  height?: number;
}

interface HierarchicalZoneProps {
  zone: Zone;
  isExpanded: boolean;
  isParent: boolean;
  isVisible: boolean;
  placedLabel?: PlacedLabel & { text: string };
  onExpand?: () => void;
  animationRef: React.RefCallback<HTMLDivElement>;
}

// Helper function to convert polygon points to SVG path (local coordinates)
function polygonPointsToSvgPath(points: number[][], offsetX: number = 0, offsetY: number = 0): string {
  if (!points || points.length < 3) return '';
  const pathParts = points.map((point, index) => {
    const [x, y] = point;
    return `${index === 0 ? 'M' : 'L'} ${x - offsetX} ${y - offsetY}`;
  });
  return pathParts.join(' ') + ' Z';
}

// Calculate bounding box from polygon points
function getPolygonBounds(points: number[][]): { minX: number; minY: number; maxX: number; maxY: number; width: number; height: number } {
  if (!points || points.length === 0) {
    return { minX: 0, minY: 0, maxX: 100, maxY: 100, width: 100, height: 100 };
  }
  const xs = points.map(p => p[0]);
  const ys = points.map(p => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY };
}

// Get stroke color based on hierarchy level
function getHierarchyStrokeColor(level: number, isOver: boolean, hasLabel: boolean, isParent: boolean, isExpanded: boolean): string {
  if (hasLabel) return '#22c55e';  // green-500
  if (isOver) return '#6366f1';    // primary
  if (isParent && !isExpanded) return '#60a5fa';  // blue-400 for expandable parents

  switch (level) {
    case 1: return '#60a5fa';  // blue-400
    case 2: return '#a78bfa';  // purple-400
    case 3: return '#2dd4bf';  // teal-400
    default: return '#9ca3af'; // gray-400
  }
}

function HierarchicalZone({
  zone,
  isExpanded,
  isParent,
  isVisible,
  placedLabel,
  onExpand,
  animationRef,
}: HierarchicalZoneProps) {
  const { isOver, setNodeRef } = useDroppable({
    id: zone.id,
    disabled: !isVisible || !!placedLabel,
  });

  if (!isVisible) return null;

  // Determine zone shape - polygon, circle, or rect
  const isPolygon = zone.shape === 'polygon' && zone.points && zone.points.length >= 3;
  const isCircle = zone.shape === 'circle' || zone.zone_type === 'point';
  const hierarchyLevel = zone.hierarchyLevel ?? 1;

  // For polygon zones, render with SVG inside a positioned div (matches DropZone pattern)
  if (isPolygon) {
    const points = zone.points as number[][];
    const bounds = getPolygonBounds(points);
    const { minX, minY, width, height } = bounds;

    // Translate polygon points to local SVG coordinates
    const svgPath = polygonPointsToSvgPath(points, minX, minY);

    // Calculate center for label placement
    const centerX = zone.center?.x ?? zone.x ?? (minX + width / 2);
    const centerY = zone.center?.y ?? zone.y ?? (minY + height / 2);

    const strokeColor = getHierarchyStrokeColor(hierarchyLevel, isOver, !!placedLabel, isParent, isExpanded);

    // Determine fill color based on state - use very low opacity to keep diagram visible
    let fillColor = 'rgba(255, 255, 255, 0.1)';  // Nearly transparent default
    if (placedLabel) {
      fillColor = 'rgba(34, 197, 94, 0.15)';  // Light green
    } else if (isOver) {
      fillColor = 'rgba(99, 102, 241, 0.2)';  // Primary highlight
    } else if (isParent && !isExpanded) {
      fillColor = 'rgba(96, 165, 250, 0.1)';  // Very light blue for expandable
    }

    return (
      <div
        ref={(el) => {
          setNodeRef(el);
          if (animationRef) animationRef(el);
        }}
        onClick={isParent && !isExpanded ? onExpand : undefined}
        className={`absolute ${isParent && !isExpanded ? 'cursor-pointer' : ''}`}
        style={{
          left: `${minX}%`,
          top: `${minY}%`,
          width: `${Math.max(width, 5)}%`,
          height: `${Math.max(height, 5)}%`,
          zIndex: hierarchyLevel,
        }}
      >
        {/* SVG Polygon Zone */}
        <svg
          className="w-full h-full overflow-visible"
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="none"
        >
          <path
            d={svgPath}
            fill={fillColor}
            stroke={strokeColor}
            strokeWidth={1.5}
            strokeDasharray={placedLabel ? 'none' : '3 2'}
            className="transition-all duration-200"
          />
        </svg>

        {/* Label indicator at center */}
        <div
          className="absolute transform -translate-x-1/2 -translate-y-1/2 pointer-events-none"
          style={{
            left: `${((centerX - minX) / width) * 100}%`,
            top: `${((centerY - minY) / height) * 100}%`,
          }}
        >
          {placedLabel ? (
            <span className="bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded whitespace-nowrap shadow-sm">
              {placedLabel.text}
            </span>
          ) : isParent && !isExpanded ? (
            <div className="text-center bg-white/90 rounded px-2 py-1 shadow-sm">
              <span className="text-sm text-blue-400">?</span>
              <span className="block text-[10px] text-blue-500 whitespace-nowrap">Has sub-parts</span>
            </div>
          ) : (
            <span className="text-sm text-gray-500 bg-white/80 rounded-full w-6 h-6 flex items-center justify-center shadow-sm">?</span>
          )}
        </div>

        {/* Expand indicator for parent zones */}
        {isParent && !isExpanded && (
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2">
            <div className="w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center animate-bounce shadow-md">
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        )}

        {/* Correct placement indicator */}
        {placedLabel?.isCorrect && (
          <div className="absolute" style={{ right: '-8px', top: '-8px' }}>
            <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        )}
      </div>
    );
  }

  // For circle/point zones or rect zones, use positioned divs
  const radius = zone.radius ?? 5;
  const size = isCircle ? radius * 2 : Math.max(radius * 2, 5);
  const zoneSize = Math.max(size, 5);

  return (
    <div
      ref={(el) => {
        setNodeRef(el);
        if (animationRef) animationRef(el);
      }}
      onClick={isParent && !isExpanded ? onExpand : undefined}
      className={`
        absolute transform -translate-x-1/2 -translate-y-1/2
        ${isParent && !isExpanded ? 'cursor-pointer' : ''}
        transition-all duration-300
        pointer-events-auto
      `}
      style={{
        left: `${zone.x}%`,
        top: `${zone.y}%`,
        width: isCircle ? `${zoneSize}%` : (zone.width ? `${zone.width}%` : `${zoneSize}%`),
        height: isCircle ? `${zoneSize}%` : (zone.height ? `${zone.height}%` : undefined),
        minWidth: '40px',
        minHeight: '24px',
        aspectRatio: isCircle ? '1' : undefined,
        zIndex: hierarchyLevel,
      }}
    >
      {/* Zone visual */}
      <div
        className={`
          w-full h-full border-2
          flex flex-col items-center justify-center
          transition-all duration-200
          ${isCircle ? 'rounded-full' : 'rounded-lg'}
          ${
            placedLabel
              ? 'bg-green-100 border-green-500'
              : isOver
              ? 'bg-primary-100 border-primary-500 scale-105'
              : isParent && !isExpanded
              ? 'bg-blue-50 border-blue-400 hover:bg-blue-100 border-dashed'
              : 'bg-white/70 border-gray-400 border-dashed hover:border-primary-400'
          }
        `}
      >
        {placedLabel ? (
          <span className="text-xs font-medium text-green-800 px-1 text-center leading-tight">
            {placedLabel.text}
          </span>
        ) : isParent && !isExpanded ? (
          <div className="text-center">
            <span className="text-sm text-blue-400">?</span>
            <span className="block text-[10px] text-blue-500">Has sub-parts</span>
          </div>
        ) : (
          <span className="text-sm text-gray-400">?</span>
        )}
      </div>

      {/* Expand indicator for parent zones */}
      {isParent && !isExpanded && (
        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2">
          <div className="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center animate-bounce">
            <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      )}

      {/* Correct placement indicator */}
      {placedLabel?.isCorrect && (
        <div className="absolute -top-1 -right-1">
          <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
            <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}

export default function HierarchyController({
  zones,
  zoneGroups,
  labels,
  onLabelPlace,
  onGroupComplete,
  onAllComplete,
  animations,
  assetUrl,
  assetPrompt = 'Diagram',
  width = 800,
  height = 600,
}: HierarchyControllerProps) {
  const { animate } = useAnimation();

  const [hierarchyState, setHierarchyState] = useState<HierarchyState>({
    expandedGroups: [],
    completedParentZones: [],
  });

  const [availableLabels, setAvailableLabels] = useState<Label[]>([]);
  const [placedLabels, setPlacedLabels] = useState<PlacedLabel[]>([]);
  const [draggingLabelId, setDraggingLabelId] = useState<string | null>(null);
  const zoneRefsMap = useRef<Map<string, HTMLDivElement>>(new Map());
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  // Get visible zone IDs based on hierarchy state - must be before useEffect that uses it
  const visibleZoneIds = useMemo((): Set<string> => {
    const visible = new Set<string>();

    // All parent zones are visible
    const parentZoneIds = new Set(zoneGroups.map((g) => g.parentZoneId));
    parentZoneIds.forEach((id) => visible.add(id));

    // Zones not in any group are always visible
    const allGroupedZones = new Set<string>();
    zoneGroups.forEach((g) => {
      allGroupedZones.add(g.parentZoneId);
      g.childZoneIds.forEach((id) => allGroupedZones.add(id));
    });

    zones.forEach((zone) => {
      if (!allGroupedZones.has(zone.id)) {
        visible.add(zone.id);
      }
    });

    // Child zones of expanded groups are visible
    zoneGroups.forEach((group) => {
      if (hierarchyState.expandedGroups.includes(group.id)) {
        group.childZoneIds.forEach((id) => visible.add(id));
      }
    });

    return visible;
  }, [zones, zoneGroups, hierarchyState]);

  // Initialize available labels (only for visible zones)
  useEffect(() => {
    const visibleLabels = labels.filter((label) => visibleZoneIds.has(label.correctZoneId));
    setAvailableLabels(visibleLabels.filter((l) => !placedLabels.some((p) => p.labelId === l.id)));
  }, [labels, visibleZoneIds, placedLabels]);

  // Check if a zone is a parent zone
  const isParentZone = useCallback(
    (zoneId: string): boolean => {
      return zoneGroups.some((g) => g.parentZoneId === zoneId);
    },
    [zoneGroups]
  );

  // Get group for a parent zone
  const getGroupForParent = useCallback(
    (zoneId: string): ZoneGroup | undefined => {
      return zoneGroups.find((g) => g.parentZoneId === zoneId);
    },
    [zoneGroups]
  );

  // Check if a group is expanded
  const isGroupExpanded = useCallback(
    (groupId: string): boolean => {
      return hierarchyState.expandedGroups.includes(groupId);
    },
    [hierarchyState]
  );

  // Handle zone expansion
  const handleExpand = useCallback(
    (zoneId: string) => {
      const group = getGroupForParent(zoneId);
      if (!group) return;

      // Check reveal trigger
      if (group.revealTrigger === 'complete_parent') {
        // Only expand if parent is completed
        const isParentCompleted = placedLabels.some(
          (p) => p.zoneId === zoneId && p.isCorrect
        );
        if (!isParentCompleted) {
          setFeedbackMessage('Complete this label first to reveal sub-parts!');
          setTimeout(() => setFeedbackMessage(null), 2000);
          return;
        }
      }

      setHierarchyState((prev) => ({
        ...prev,
        expandedGroups: [...prev.expandedGroups, group.id],
      }));
    },
    [getGroupForParent, placedLabels]
  );

  // Configure drag sensors
  const mouseSensor = useSensor(MouseSensor, { activationConstraint: { distance: 5 } });
  const touchSensor = useSensor(TouchSensor, { activationConstraint: { delay: 100, tolerance: 5 } });
  const sensors = useSensors(mouseSensor, touchSensor);

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setDraggingLabelId(event.active.id as string);
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setDraggingLabelId(null);

      if (!over || !active) return;

      const labelId = active.id as string;
      const zoneId = over.id as string;
      const label = labels.find((l) => l.id === labelId);

      if (!label) return;

      const isCorrect = label.correctZoneId === zoneId;
      const zoneElement = zoneRefsMap.current.get(zoneId);

      if (isCorrect) {
        if (zoneElement) {
          animate(
            zoneElement,
            animations?.correctPlacement || DEFAULT_ANIMATIONS.correctPlacement
          );
        }

        setPlacedLabels((prev) => [...prev, { labelId, zoneId, isCorrect: true }]);
        setAvailableLabels((prev) => prev.filter((l) => l.id !== labelId));

        // Check if this completes a group
        const parentGroup = zoneGroups.find((g) => g.parentZoneId === zoneId);
        if (parentGroup) {
          onGroupComplete(parentGroup.id);

          // Auto-expand if trigger is complete_parent
          if (parentGroup.revealTrigger === 'complete_parent') {
            setHierarchyState((prev) => ({
              ...prev,
              expandedGroups: [...prev.expandedGroups, parentGroup.id],
              completedParentZones: [...prev.completedParentZones, zoneId],
            }));
          }
        }

        onLabelPlace(labelId, zoneId, true);
      } else {
        if (zoneElement) {
          animate(
            zoneElement,
            animations?.incorrectPlacement || DEFAULT_ANIMATIONS.incorrectPlacement
          );
        }
        setFeedbackMessage('Try again!');
        setTimeout(() => setFeedbackMessage(null), 1500);
        onLabelPlace(labelId, zoneId, false);
      }
    },
    [labels, animate, animations, zoneGroups, onGroupComplete, onLabelPlace]
  );

  // Check for all complete
  useEffect(() => {
    const totalVisibleZones = visibleZoneIds.size;
    const correctPlacements = placedLabels.filter((p) => p.isCorrect).length;

    if (correctPlacements === totalVisibleZones && totalVisibleZones > 0) {
      onAllComplete();
    }
  }, [placedLabels, visibleZoneIds, onAllComplete]);

  // Create ref callback for zones - uses useRef to avoid re-renders
  const createZoneRef = useCallback(
    (zoneId: string) => (el: HTMLDivElement | null) => {
      if (el) {
        zoneRefsMap.current.set(zoneId, el);
      }
    },
    []
  );

  const draggedLabel = draggingLabelId
    ? availableLabels.find((l) => l.id === draggingLabelId)
    : null;

  const getPlacedLabel = (zoneId: string) => {
    const placed = placedLabels.find((p) => p.zoneId === zoneId);
    if (!placed) return undefined;
    const label = labels.find((l) => l.id === placed.labelId);
    if (!label) return undefined;
    const displayText = placed.isCorrect && label.canonicalName
      ? label.canonicalName
      : label.text;
    return { ...placed, text: displayText };
  };

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex flex-col">
        {/* Progress indicator */}
        <div className="flex justify-end mb-2">
          <div className="bg-white rounded-lg px-3 py-2 shadow-md">
            <p className="text-sm text-gray-700">
              {placedLabels.filter((p) => p.isCorrect).length} / {visibleZoneIds.size} labeled
            </p>
            <p className="text-xs text-gray-500">
              {hierarchyState.expandedGroups.length} / {zoneGroups.length} groups expanded
            </p>
          </div>
        </div>

        {/* Diagram container with image and zone overlays */}
        <div
          className="relative bg-gray-100 rounded-lg mx-auto"
          style={{
            width: '100%',
            maxWidth: `${width}px`,
            aspectRatio: `${width} / ${height}`,
          }}
        >
          {/* Diagram image */}
          {assetUrl ? (
            <img
              src={assetUrl}
              alt={assetPrompt}
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center p-8 bg-gradient-to-br from-gray-100 to-gray-200">
              <p className="text-gray-500 text-center text-sm">{assetPrompt}</p>
            </div>
          )}

          {/* All zones - rendered as positioned divs (polygon zones use internal SVG) */}
          {zones.map((zone) => {
            const group = getGroupForParent(zone.id);
            const isParent = !!group;
            const isExpanded = group ? isGroupExpanded(group.id) : false;
            const isVisible = visibleZoneIds.has(zone.id);

            return (
              <HierarchicalZone
                key={zone.id}
                zone={zone}
                isExpanded={isExpanded}
                isParent={isParent}
                isVisible={isVisible}
                placedLabel={getPlacedLabel(zone.id)}
                onExpand={() => handleExpand(zone.id)}
                animationRef={createZoneRef(zone.id)}
              />
            );
          })}
        </div>

        {/* Available labels tray */}
        <div className="mt-4 p-4 bg-gray-50 border rounded-lg">
          <div className="flex flex-wrap gap-2 justify-center">
            {availableLabels.map((label) => (
              <DraggableLabel
                key={label.id}
                id={label.id}
                text={label.text}
                isIncorrect={false}
              />
            ))}
          </div>
        </div>

        {/* Feedback message */}
        {feedbackMessage && (
          <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-20 animate-fade-in">
            <div className="bg-orange-500 text-white rounded-lg px-4 py-2 shadow-lg">
              <p className="text-sm font-medium">{feedbackMessage}</p>
            </div>
          </div>
        )}

        {/* Drag overlay */}
        <DragOverlay>
          {draggedLabel ? (
            <DraggableLabel id={draggedLabel.id} text={draggedLabel.text} />
          ) : null}
        </DragOverlay>
      </div>
    </DndContext>
  );
}
