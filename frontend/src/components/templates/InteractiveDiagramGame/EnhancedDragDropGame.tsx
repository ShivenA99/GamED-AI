'use client';

import { useMemo, useRef, useState, useCallback, useEffect } from 'react';
import { DragOverlay, DragStartEvent, DragEndEvent, SensorDescriptor, SensorOptions } from '@dnd-kit/core';
import { motion, AnimatePresence } from 'framer-motion';
import {
  InteractiveDiagramBlueprint,
  PlacedLabel,
  Label,
  DistractorLabel,
  DragDropConfig,
  EnhancedLabel,
  EnhancedDistractorLabel,
  LeaderLineAnchor,
  MechanicAction,
  ActionResult,
} from './types';
import DiagramCanvas from './DiagramCanvas';
import EnhancedLabelCard, { PlacementParticles } from './EnhancedLabelCard';
import EnhancedLabelTray from './EnhancedLabelTray';
import LeaderLineOverlay from './LeaderLineOverlay';
import ZoomPanCanvas from './ZoomPanCanvas';
import ClickToPlaceMode from './ClickToPlaceMode';
import DistractorManager from './DistractorManager';
import { useInteractiveDiagramState } from './hooks/useInteractiveDiagramState';

interface EnhancedDragDropGameProps {
  blueprint: InteractiveDiagramBlueprint;
  placedLabels: PlacedLabel[];
  availableLabels: (Label | DistractorLabel)[];
  draggingLabelId: string | null;
  incorrectFeedback: { labelId: string; message: string } | null;
  showHints: boolean;
  sensors: SensorDescriptor<SensorOptions>[];
  onDragStart: (e: DragStartEvent) => void;
  onDragEnd: (e: DragEndEvent) => void;
  onDragCancel: () => void;
  /** For click-to-place mode: direct placement handler */
  onPlace?: (labelId: string, zoneId: string) => boolean;
  /** Unified action dispatch (V4). Drag-drop is already controlled by parent,
   *  but emits actions for logging/store integration. */
  onAction?: (action: MechanicAction) => ActionResult | null;
}

/** Extract DragDropConfig with sensible defaults */
function getConfig(bp: InteractiveDiagramBlueprint): DragDropConfig {
  const cfg = bp.dragDropConfig || {};
  return {
    interaction_mode: cfg.interaction_mode || 'drag_drop',
    feedback_timing: cfg.feedback_timing || 'immediate',
    zone_idle_animation: cfg.zone_idle_animation || 'none',
    zone_hover_effect: cfg.zone_hover_effect || 'highlight',
    label_style: cfg.label_style || 'text',
    placement_animation: cfg.placement_animation || (cfg.snapAnimation === 'none' ? 'instant' : cfg.snapAnimation) || 'spring',
    spring_stiffness: cfg.spring_stiffness || 300,
    spring_damping: cfg.spring_damping || 25,
    incorrect_animation: cfg.incorrect_animation || 'shake',
    show_placement_particles: cfg.show_placement_particles ?? true,
    leader_line_style: cfg.leader_line_style || (cfg.showLeaderLines ? 'curved' : 'none'),
    leader_line_color: cfg.leader_line_color || '#6366f1',
    leader_line_width: cfg.leader_line_width || 2,
    leader_line_animate: cfg.leader_line_animate ?? true,
    pin_marker_shape: cfg.pin_marker_shape || 'circle',
    label_anchor_side: cfg.label_anchor_side || 'auto',
    tray_position: cfg.tray_position || 'bottom',
    tray_layout: cfg.tray_layout || 'horizontal',
    tray_show_remaining: cfg.tray_show_remaining ?? true,
    tray_show_categories: cfg.tray_show_categories ?? false,
    show_distractors: cfg.show_distractors ?? ((bp.distractorLabels?.length || 0) > 0),
    distractor_count: cfg.distractor_count || bp.distractorLabels?.length || 0,
    distractor_rejection_mode: cfg.distractor_rejection_mode || 'immediate',
    zoom_enabled: cfg.zoom_enabled ?? false,
    zoom_min: cfg.zoom_min || 0.5,
    zoom_max: cfg.zoom_max || 3,
    minimap_enabled: cfg.minimap_enabled ?? false,
    max_attempts: cfg.max_attempts || cfg.maxAttempts || 0,
    shuffle_labels: cfg.shuffle_labels ?? cfg.shuffleLabels ?? true,
  };
}

/** Auto-generate leader line anchors from zone positions if not provided in blueprint */
function generateDefaultAnchors(
  zones: InteractiveDiagramBlueprint['diagram']['zones'],
  labels: Label[],
  trayPosition: string,
): LeaderLineAnchor[] {
  return zones.map((zone) => {
    const zoneX = zone.x ?? 50;
    const zoneY = zone.y ?? 50;

    // Place label anchor on the opposite side of the tray
    let labelX = zoneX;
    let labelY = zoneY;
    const offset = 15;

    switch (trayPosition) {
      case 'bottom':
        labelY = Math.min(zoneY + offset, 95);
        break;
      case 'top':
        labelY = Math.max(zoneY - offset, 5);
        break;
      case 'right':
        labelX = Math.min(zoneX + offset, 95);
        break;
      case 'left':
        labelX = Math.max(zoneX - offset, 5);
        break;
    }

    return {
      zone_id: zone.id,
      pin_x: zoneX,
      pin_y: zoneY,
      label_x: labelX,
      label_y: labelY,
    };
  });
}

/** Enrich labels with category/icon/description from zone data */
function enrichLabels(
  labels: (Label | DistractorLabel)[],
  zones: InteractiveDiagramBlueprint['diagram']['zones'],
): (EnhancedLabel | EnhancedDistractorLabel)[] {
  return labels.map((label) => {
    if ('correctZoneId' in label) {
      const zone = zones.find((z) => z.id === label.correctZoneId);
      return {
        ...label,
        category: (zone?.metadata?.category as string) || undefined,
        description: zone?.description,
      } as EnhancedLabel;
    }
    return label as EnhancedDistractorLabel;
  });
}

export default function EnhancedDragDropGame({
  blueprint: bp,
  placedLabels,
  availableLabels,
  draggingLabelId,
  incorrectFeedback,
  showHints,
  sensors,
  onDragStart,
  onDragEnd,
  onDragCancel,
  onPlace,
  onAction,
}: EnhancedDragDropGameProps) {
  const config = useMemo(() => getConfig(bp), [bp]);
  const containerRef = useRef<HTMLDivElement>(null);

  // Progressive reveal: filter zones to only visible ones
  const storeVisibleZoneIds = useInteractiveDiagramState((s) => s.visibleZoneIds);
  const storeCompletedZoneIds = useInteractiveDiagramState((s) => s.completedZoneIds);
  const visibleZones = useMemo(() => {
    // Empty visibleZoneIds = show all (backwards compatible when no hierarchy)
    const base = (!storeVisibleZoneIds || storeVisibleZoneIds.size === 0)
      ? bp.diagram.zones
      : bp.diagram.zones.filter((z) => storeVisibleZoneIds.has(z.id));
    // Hide completed parent zones — their children are now revealed underneath
    return base.filter((z) => {
      if (storeCompletedZoneIds.has(z.id) && z.childZoneIds && z.childZoneIds.length > 0) {
        return false; // completed parent: hide hit area so children are targetable
      }
      return true;
    });
  }, [bp.diagram.zones, storeVisibleZoneIds, storeCompletedZoneIds]);

  // Filter available labels to only those whose correctZoneId is visible
  const visibleLabels = useMemo(() => {
    if (!storeVisibleZoneIds || storeVisibleZoneIds.size === 0) return availableLabels;
    return availableLabels.filter((label) => {
      if ('correctZoneId' in label) {
        return storeVisibleZoneIds.has(label.correctZoneId);
      }
      return true; // distractors always visible if present
    });
  }, [availableLabels, storeVisibleZoneIds]);

  // Particle effect state
  const [particlePos, setParticlePos] = useState<{ x: number; y: number; show: boolean }>({
    x: 0,
    y: 0,
    show: false,
  });

  // Track last placed label for particle effect
  const lastPlacedRef = useRef<string | null>(null);

  useEffect(() => {
    const latest = placedLabels[placedLabels.length - 1];
    if (latest && latest.isCorrect && latest.zoneId !== lastPlacedRef.current) {
      lastPlacedRef.current = latest.zoneId;
      // Find zone position for particles (placement is now handled by dispatch)
      const zone = visibleZones.find((z) => z.id === latest.zoneId);
      if (zone && containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const x = ((zone.x ?? 50) / 100) * rect.width;
        const y = ((zone.y ?? 50) / 100) * rect.height;
        setParticlePos({ x, y, show: true });
        setTimeout(() => setParticlePos((prev) => ({ ...prev, show: false })), 700);
      }
    }
  }, [placedLabels, visibleZones]);

  // Enrich labels (filtered by visibility)
  const enrichedLabels = useMemo(
    () => enrichLabels(visibleLabels, visibleZones),
    [visibleLabels, visibleZones]
  );

  // Leader line anchors
  const leaderLineAnchors = useMemo(() => {
    if (config.leader_line_style === 'none') return [];
    // Use from blueprint if available, otherwise generate defaults
    return generateDefaultAnchors(visibleZones, bp.labels, config.tray_position || 'bottom');
  }, [visibleZones, bp.labels, config.leader_line_style, config.tray_position]);

  // Stable reference for real labels passed to DistractorManager (prevents re-shuffle on every render)
  const realLabelsForDistractors = useMemo(
    () => enrichedLabels.filter((l): l is EnhancedLabel => 'correctZoneId' in l),
    [enrichedLabels]
  );

  // Correct zone IDs set
  const correctZoneIds = useMemo(
    () => new Set(placedLabels.filter((pl) => pl.isCorrect).map((pl) => pl.zoneId)),
    [placedLabels]
  );

  const width = bp.diagram.width || 800;
  const height = bp.diagram.height || 600;

  // Dragged label for overlay
  const draggedLabel = useMemo(
    () => (draggingLabelId ? availableLabels.find((l) => l.id === draggingLabelId) : null),
    [draggingLabelId, availableLabels]
  );

  // ---- Click-to-place mode ----
  if (config.interaction_mode === 'click_to_place' && onPlace) {
    return (
      <ClickToPlaceMode
        labels={enrichedLabels}
        allLabels={bp.labels}
        placedLabels={placedLabels}
        zones={visibleZones}
        assetUrl={bp.diagram.assetUrl}
        width={width}
        height={height}
        hints={bp.hints}
        showHints={showHints}
        zoneGroups={bp.zoneGroups}
        title={bp.title}
        config={config}
        leaderLineAnchors={leaderLineAnchors}
        onPlace={onPlace}
        incorrectLabelId={incorrectFeedback?.labelId}
      />
    );
  }

  // ---- Standard drag-drop mode (enhanced) ----
  const diagramContent = (
    <div ref={containerRef} className="relative my-6">
      <DiagramCanvas
        assetUrl={bp.diagram.assetUrl}
        assetPrompt={bp.diagram.assetPrompt}
        zones={visibleZones}
        placedLabels={placedLabels}
        labels={bp.labels}
        hints={bp.hints}
        showHints={showHints}
        width={width}
        height={height}
        zoneGroups={bp.zoneGroups}
        mediaAssets={bp.mediaAssets}
        title={bp.title}
      />

      {/* Leader lines overlay */}
      {config.leader_line_style !== 'none' && leaderLineAnchors.length > 0 && (
        <LeaderLineOverlay
          containerWidth={width}
          containerHeight={height}
          placedLabels={placedLabels}
          anchors={leaderLineAnchors}
          lineStyle={config.leader_line_style}
          lineColor={config.leader_line_color}
          lineWidth={config.leader_line_width}
          animate={config.leader_line_animate}
          pinMarkerShape={config.pin_marker_shape}
          correctZoneIds={correctZoneIds}
        />
      )}

      {/* Placement particles */}
      {config.show_placement_particles && (
        <PlacementParticles
          x={particlePos.x}
          y={particlePos.y}
          show={particlePos.show}
          color="#22c55e"
        />
      )}
    </div>
  );

  // Determine whether distractors should be mixed
  const hasDistractors = config.show_distractors && bp.distractorLabels && bp.distractorLabels.length > 0;

  const renderTrayAndDiagram = (mixedLabels: (EnhancedLabel | EnhancedDistractorLabel)[] | null) => {
    const labelsToShow = mixedLabels || enrichedLabels;
    const totalOriginal = bp.labels.length + (bp.distractorLabels?.length || 0);

    const tray = (
      <EnhancedLabelTray
        labels={labelsToShow}
        draggingLabelId={draggingLabelId}
        incorrectLabelId={incorrectFeedback?.labelId}
        layout={config.tray_layout}
        position={config.tray_position}
        showCategories={config.tray_show_categories}
        showRemaining={config.tray_show_remaining}
        labelStyle={config.label_style}
        incorrectAnimation={config.incorrect_animation}
        totalLabels={totalOriginal}
      />
    );

    // Layout based on tray position
    if (config.tray_position === 'right' || config.tray_position === 'left') {
      return (
        <div className={`flex gap-4 ${config.tray_position === 'left' ? 'flex-row-reverse' : 'flex-row'}`}>
          <div className="flex-1">
            {config.zoom_enabled ? (
              <ZoomPanCanvas
                enabled
                minZoom={config.zoom_min}
                maxZoom={config.zoom_max}
                showControls
              >
                {diagramContent}
              </ZoomPanCanvas>
            ) : (
              diagramContent
            )}
          </div>
          <div className="flex-shrink-0">
            {tray}
          </div>
        </div>
      );
    }

    // Default: top/bottom
    const isTop = config.tray_position === 'top';
    return (
      <div className="flex flex-col gap-4">
        {isTop && tray}
        {config.zoom_enabled ? (
          <ZoomPanCanvas
            enabled
            minZoom={config.zoom_min}
            maxZoom={config.zoom_max}
            showControls
          >
            {diagramContent}
          </ZoomPanCanvas>
        ) : (
          diagramContent
        )}
        {!isTop && tray}
      </div>
    );
  };

  return (
    <>
      {hasDistractors ? (
        <DistractorManager
          realLabels={realLabelsForDistractors}
          distractorLabels={bp.distractorLabels || []}
          rejectionMode={config.distractor_rejection_mode}
          shuffle={config.shuffle_labels}
        >
          {({ mixedLabels }) => renderTrayAndDiagram(mixedLabels)}
        </DistractorManager>
      ) : (
        renderTrayAndDiagram(null)
      )}

      {/* Incorrect feedback toast */}
      <AnimatePresence>
        {incorrectFeedback && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="mt-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg"
          >
            <p className="text-red-700 dark:text-red-300 text-sm">{incorrectFeedback.message}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Drag overlay with enhanced card */}
      <DragOverlay>
        {draggedLabel ? (
          <EnhancedLabelCard
            id={draggedLabel.id}
            text={draggedLabel.text}
            cardStyle={config.label_style}
            state="dragging"
          />
        ) : null}
      </DragOverlay>
    </>
  );
}
