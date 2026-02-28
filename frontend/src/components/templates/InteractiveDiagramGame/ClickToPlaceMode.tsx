'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zone, Label, PlacedLabel, Hint, ZoneGroup, EnhancedLabel, EnhancedDistractorLabel, DragDropConfig, LeaderLineAnchor } from './types';
import DiagramCanvas from './DiagramCanvas';
import EnhancedLabelTray from './EnhancedLabelTray';
import LeaderLineOverlay from './LeaderLineOverlay';

interface ClickToPlaceModeProps {
  /** Available labels to place */
  labels: (EnhancedLabel | EnhancedDistractorLabel)[];
  /** All labels (for lookup) */
  allLabels: Label[];
  /** Placed labels */
  placedLabels: PlacedLabel[];
  /** Zones on the diagram */
  zones: Zone[];
  /** Diagram image URL */
  assetUrl?: string;
  /** Diagram dimensions */
  width?: number;
  height?: number;
  /** Hints */
  hints?: Hint[];
  /** Show hints */
  showHints?: boolean;
  /** Zone groups */
  zoneGroups?: ZoneGroup[];
  /** Game title */
  title?: string;
  /** Drag drop config for styling */
  config?: DragDropConfig;
  /** Leader line anchors */
  leaderLineAnchors?: LeaderLineAnchor[];
  /** Callback when label is placed */
  onPlace: (labelId: string, zoneId: string) => boolean;
  /** ID of label that was incorrectly placed */
  incorrectLabelId?: string | null;
}

export default function ClickToPlaceMode({
  labels,
  allLabels,
  placedLabels,
  zones,
  assetUrl,
  width = 800,
  height = 600,
  hints,
  showHints = false,
  zoneGroups = [],
  title = 'Interactive Diagram',
  config,
  leaderLineAnchors = [],
  onPlace,
  incorrectLabelId,
}: ClickToPlaceModeProps) {
  const [selectedLabelId, setSelectedLabelId] = useState<string | null>(null);
  const [feedbackZoneId, setFeedbackZoneId] = useState<string | null>(null);
  const [feedbackCorrect, setFeedbackCorrect] = useState(false);

  // Handle label click in tray
  const handleLabelClick = useCallback((labelId: string) => {
    setSelectedLabelId((prev) => (prev === labelId ? null : labelId));
  }, []);

  // Handle zone click on diagram
  const handleZoneClick = useCallback(
    (labelId: string, zoneId: string) => {
      // If no label selected, select this label (shouldn't normally happen via zone click)
      if (!selectedLabelId) return;

      const isCorrect = onPlace(selectedLabelId, zoneId);
      setFeedbackZoneId(zoneId);
      setFeedbackCorrect(isCorrect);

      if (isCorrect) {
        setSelectedLabelId(null);
      }

      // Clear feedback after animation
      setTimeout(() => setFeedbackZoneId(null), 800);
    },
    [selectedLabelId, onPlace]
  );

  const correctZoneIds = new Set(
    placedLabels.filter((pl) => pl.isCorrect).map((pl) => pl.zoneId)
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Selection indicator banner */}
      <AnimatePresence>
        {selectedLabelId && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-700 rounded-lg px-4 py-2 flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
              <span className="text-sm text-indigo-700 dark:text-indigo-300">
                Selected: <strong>{labels.find((l) => l.id === selectedLabelId)?.text}</strong>
                {' — '}now click a zone to place it
              </span>
            </div>
            <button
              onClick={() => setSelectedLabelId(null)}
              className="text-indigo-500 hover:text-indigo-700 text-sm underline"
            >
              Cancel
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Diagram with clickable zones */}
      <div className="relative">
        <DiagramCanvas
          assetUrl={assetUrl}
          assetPrompt={title}
          zones={zones}
          placedLabels={placedLabels}
          labels={allLabels}
          hints={hints}
          showHints={showHints}
          width={width}
          height={height}
          zoneGroups={zoneGroups}
          title={title}
          activeDragId={selectedLabelId}
          onKeyboardDrop={handleZoneClick}
        />

        {/* Leader lines */}
        {leaderLineAnchors.length > 0 && (
          <LeaderLineOverlay
            containerWidth={width}
            containerHeight={height}
            placedLabels={placedLabels}
            anchors={leaderLineAnchors}
            lineStyle={config?.leader_line_style || 'curved'}
            lineColor={config?.leader_line_color || '#6366f1'}
            lineWidth={config?.leader_line_width || 2}
            animate={config?.leader_line_animate !== false}
            pinMarkerShape={config?.pin_marker_shape || 'circle'}
            correctZoneIds={correctZoneIds}
          />
        )}

        {/* Click feedback overlay */}
        <AnimatePresence>
          {feedbackZoneId && (
            <motion.div
              className="absolute inset-0 pointer-events-none z-50"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Brief flash of color */}
              <div
                className={`absolute inset-0 ${
                  feedbackCorrect ? 'bg-green-500/10' : 'bg-red-500/10'
                }`}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Label tray (click mode) */}
      <EnhancedLabelTray
        labels={labels}
        draggingLabelId={null}
        incorrectLabelId={incorrectLabelId}
        layout={config?.tray_layout || 'horizontal'}
        position={config?.tray_position || 'bottom'}
        showCategories={config?.tray_show_categories}
        showRemaining={config?.tray_show_remaining !== false}
        labelStyle={config?.label_style || 'text'}
        incorrectAnimation={config?.incorrect_animation || 'shake'}
        onLabelClick={handleLabelClick}
        selectedLabelId={selectedLabelId}
      />
    </div>
  );
}
