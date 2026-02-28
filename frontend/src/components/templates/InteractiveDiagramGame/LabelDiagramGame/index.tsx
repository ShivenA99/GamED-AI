'use client';

import { useEffect, useCallback, useMemo } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragStartEvent,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core';
import { LabelDiagramBlueprint } from './types';
import { useLabelDiagramState } from './hooks/useLabelDiagramState';
import DiagramCanvas from './DiagramCanvas';
import LabelTray from './LabelTray';
import GameControls from './GameControls';
import ResultsPanel from './ResultsPanel';
import DraggableLabel from './DraggableLabel';

interface LabelDiagramGameProps {
  blueprint: LabelDiagramBlueprint;
  onComplete?: (score: number) => void;
  sessionId?: string;
}

const coerceDimension = (value: unknown, fallbackValue: number): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.round(value);
  }
  if (typeof value === 'string') {
    const raw = value.trim().toLowerCase();
    const numeric = raw.endsWith('px') ? raw.slice(0, -2).trim() : raw;
    const parsed = Number(numeric);
    if (Number.isFinite(parsed)) {
      return Math.round(parsed);
    }
  }
  return fallbackValue;
};

const slugify = (value: string): string =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');

const generateDefaultPositions = (count: number) => {
  if (count <= 0) return [];
  const rows = Math.ceil(Math.sqrt(count));
  const cols = Math.ceil(count / rows);
  const xStep = 100 / (cols + 1);
  const yStep = 100 / (rows + 1);
  const positions: Array<{ x: number; y: number }> = [];
  for (let idx = 0; idx < count; idx += 1) {
    const row = Math.floor(idx / cols);
    const col = idx % cols;
    positions.push({
      x: Math.round((col + 1) * xStep * 100) / 100,
      y: Math.round((row + 1) * yStep * 100) / 100,
    });
  }
  return positions;
};

const normalizeBlueprint = (input: LabelDiagramBlueprint): LabelDiagramBlueprint => {
  const diagram = input.diagram ?? { assetPrompt: '', zones: [] };
  const width = coerceDimension(diagram.width, 800);
  const height = coerceDimension(diagram.height, 600);
  const zones = Array.isArray(diagram.zones) ? diagram.zones.map((zone) => ({ ...zone })) : [];

  const zoneIdQueues = new Map<string, string[]>();
  const usedZoneIds = new Set<string>();
  const normalizedZones = zones.map((zone, index) => {
    const originalId = zone.id || `zone_${index + 1}`;
    let uniqueId = originalId;
    let suffix = 1;
    while (usedZoneIds.has(uniqueId)) {
      suffix += 1;
      uniqueId = `${originalId}_${suffix}`;
    }
    usedZoneIds.add(uniqueId);
    if (!zoneIdQueues.has(originalId)) {
      zoneIdQueues.set(originalId, []);
    }
    zoneIdQueues.get(originalId)?.push(uniqueId);
    return { ...zone, id: uniqueId };
  });

  const labels = Array.isArray(input.labels) ? input.labels.map((label) => ({ ...label })) : [];
  const usedLabelIds = new Set<string>();
  const assignedZoneIds = new Set<string>();
  const normalizedLabels = labels.map((label, index) => {
    const labelText = label.text || `Label ${index + 1}`;
    const baseLabelId =
      (label as { id?: string }).id ||
      (label as { labelId?: string }).labelId ||
      `label_${slugify(labelText) || index + 1}`;
    let uniqueLabelId = baseLabelId;
    let labelSuffix = 1;
    while (usedLabelIds.has(uniqueLabelId)) {
      labelSuffix += 1;
      uniqueLabelId = `${baseLabelId}_${labelSuffix}`;
    }
    usedLabelIds.add(uniqueLabelId);

    const originalZoneId =
      label.correctZoneId || normalizedZones[index]?.id || `zone_${index + 1}`;
    let mappedZoneId = originalZoneId;
    const queue = zoneIdQueues.get(originalZoneId);
    if (queue && queue.length > 0) {
      mappedZoneId = queue.shift() as string;
    }
    if (assignedZoneIds.has(mappedZoneId)) {
      let zoneSuffix = 1;
      let uniqueZoneId = `${mappedZoneId}_${zoneSuffix}`;
      while (assignedZoneIds.has(uniqueZoneId)) {
        zoneSuffix += 1;
        uniqueZoneId = `${mappedZoneId}_${zoneSuffix}`;
      }
      mappedZoneId = uniqueZoneId;
    }
    assignedZoneIds.add(mappedZoneId);

    return {
      ...label,
      id: uniqueLabelId,
      text: labelText,
      correctZoneId: mappedZoneId,
    };
  });

  const zoneIdSet = new Set(normalizedZones.map((zone) => zone.id));
  const fallbackPositions = generateDefaultPositions(normalizedLabels.length);
  normalizedLabels.forEach((label, index) => {
    if (!zoneIdSet.has(label.correctZoneId)) {
      const position = fallbackPositions[index] || { x: 50, y: 50 };
      normalizedZones.push({
        id: label.correctZoneId,
        label: label.text,
        x: position.x,
        y: position.y,
        radius: 10,
      });
      zoneIdSet.add(label.correctZoneId);
    }
  });

  return {
    ...input,
    diagram: {
      ...diagram,
      width,
      height,
      zones: normalizedZones,
    },
    labels: normalizedLabels,
  };
};

export default function LabelDiagramGame({
  blueprint,
  onComplete,
}: LabelDiagramGameProps) {
  const {
    availableLabels,
    placedLabels,
    score,
    maxScore,
    isComplete,
    showHints,
    draggingLabelId,
    incorrectFeedback,
    initializeGame,
    placeLabel,
    setDraggingLabel,
    toggleHints,
    resetGame,
    clearIncorrectFeedback,
  } = useLabelDiagramState();
  const normalizedBlueprint = useMemo(
    () => normalizeBlueprint(blueprint),
    [blueprint]
  );

  // Initialize game on mount
  useEffect(() => {
    initializeGame(normalizedBlueprint);
  }, [normalizedBlueprint, initializeGame]);

  // Notify completion
  useEffect(() => {
    if (isComplete && onComplete) {
      onComplete(score);
    }
  }, [isComplete, score, onComplete]);

  // Clear incorrect feedback after a delay
  useEffect(() => {
    if (incorrectFeedback) {
      const timer = setTimeout(clearIncorrectFeedback, 2000);
      return () => clearTimeout(timer);
    }
  }, [incorrectFeedback, clearIncorrectFeedback]);

  // Configure drag sensors
  const mouseSensor = useSensor(MouseSensor, {
    activationConstraint: {
      distance: 5,
    },
  });
  const touchSensor = useSensor(TouchSensor, {
    activationConstraint: {
      delay: 100,
      tolerance: 5,
    },
  });
  const sensors = useSensors(mouseSensor, touchSensor);

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      setDraggingLabel(event.active.id as string);
    },
    [setDraggingLabel]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;

      if (over && active) {
        placeLabel(active.id as string, over.id as string);
      } else {
        setDraggingLabel(null);
      }
    },
    [placeLabel, setDraggingLabel]
  );

  const handleDragCancel = useCallback(() => {
    setDraggingLabel(null);
  }, [setDraggingLabel]);

  // Find the currently dragged label for the overlay
  const draggedLabel = draggingLabelId
    ? availableLabels.find((l) => l.id === draggingLabelId)
    : null;

  // Show results when complete
  if (isComplete) {
    return (
      <div className="game-container">
        <ResultsPanel
          score={score}
          maxScore={maxScore}
          feedbackMessages={normalizedBlueprint.feedbackMessages}
          onPlayAgain={resetGame}
        />
      </div>
    );
  }

  return (
    <div className="game-container">
      {/* Title and intro */}
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">{normalizedBlueprint.title}</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">{normalizedBlueprint.narrativeIntro}</p>
      </div>

      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        {/* Game controls */}
        <GameControls
          showHints={showHints}
          onToggleHints={toggleHints}
          onReset={resetGame}
          hasHints={!!normalizedBlueprint.hints?.length}
          score={score}
          maxScore={maxScore}
        />

        {/* Task instruction */}
        {normalizedBlueprint.tasks?.[0] && (
          <div className="my-4 p-4 bg-blue-50 rounded-lg">
            <p className="text-blue-800 font-medium">
              {normalizedBlueprint.tasks[0].questionText}
            </p>
          </div>
        )}

        {/* Diagram canvas with drop zones */}
        <div className="my-6">
          <DiagramCanvas
            assetUrl={normalizedBlueprint.diagram.assetUrl}
            assetPrompt={normalizedBlueprint.diagram.assetPrompt}
            zones={normalizedBlueprint.diagram.zones}
            placedLabels={placedLabels}
            labels={normalizedBlueprint.labels}
            hints={normalizedBlueprint.hints}
            showHints={showHints}
            width={normalizedBlueprint.diagram.width}
            height={normalizedBlueprint.diagram.height}
          />
        </div>

        {/* Label tray */}
        <LabelTray
          labels={availableLabels}
          draggingLabelId={draggingLabelId}
          incorrectLabelId={incorrectFeedback?.labelId}
        />

        {/* Incorrect feedback message */}
        {incorrectFeedback && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg animate-fade-in">
            <p className="text-red-700 text-sm">{incorrectFeedback.message}</p>
          </div>
        )}

        {/* Drag overlay for smooth dragging */}
        <DragOverlay>
          {draggedLabel ? (
            <DraggableLabel id={draggedLabel.id} text={draggedLabel.text} />
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}

export { default as DiagramLabelingHarness } from './Harness';
