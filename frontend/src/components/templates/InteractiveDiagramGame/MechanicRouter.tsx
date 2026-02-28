'use client';

import { useMemo } from 'react';
import { DndContext, rectIntersection, CollisionDetection } from '@dnd-kit/core';
import {
  InteractiveDiagramBlueprint,
  InteractionMode,
  MechanicAction,
  ActionResult,
} from './types';

import MechanicConfigError from './MechanicConfigError';
import { TimedChallengeWrapper } from './interactions';

import {
  MECHANIC_REGISTRY,
  registryNeedsDndContext,
  DndState,
  HierarchicalModeCallbacks,
  MechanicProgressMap,
  MechanicContext,
} from './mechanicRegistry';

// ----------------------------------------------------------------
// Props interface — semantic bundles instead of 23+ flat props
// ----------------------------------------------------------------

export interface MechanicRouterProps {
  /** Which mechanic to render */
  mode: InteractionMode;
  /** The current (possibly per-scene) blueprint */
  blueprint: InteractiveDiagramBlueprint;
  /** V4 unified action dispatch — returns ActionResult for immediate feedback */
  onAction: (action: MechanicAction) => ActionResult | null;
  /** Signal game completion */
  completeInteraction: () => void;
  /** Per-mechanic progress map */
  progress: MechanicProgressMap;
  /** Drag-and-drop state bundle (null if not using DnD) */
  dnd: DndState | null;
  /** Hierarchical mode callbacks (not a mechanic — stays separate) */
  hierarchical: HierarchicalModeCallbacks | null;
}

/**
 * Custom collision detection that prefers the smallest overlapping droppable.
 * This ensures that when zones are nested (e.g., Cytoplasm contains Nucleus),
 * dropping on the inner zone targets it rather than the larger outer zone.
 */
const smallestTargetCollision: CollisionDetection = (args) => {
  const collisions = rectIntersection(args);
  if (collisions.length <= 1) return collisions;

  // Sort by area ascending — smallest first = most specific target
  return [...collisions].sort((a, b) => {
    const aRect = args.droppableRects.get(a.id);
    const bRect = args.droppableRects.get(b.id);
    if (!aRect || !bRect) return 0;
    const aArea = aRect.width * aRect.height;
    const bArea = bRect.width * bRect.height;
    return aArea - bArea;
  });
};

// ----------------------------------------------------------------
// Main component — registry-driven lookup
// ----------------------------------------------------------------

export default function MechanicRouter(props: MechanicRouterProps) {
  const { mode, blueprint, onAction, completeInteraction, progress, dnd, hierarchical } = props;

  const content = useMemo(() => {
    // ── timed_challenge is a wrapper, not a mechanic ──
    if (mode === 'timed_challenge') {
      const wrappedMode = blueprint.timedChallengeWrappedMode;
      if (!wrappedMode) {
        return <MechanicConfigError mechanic="timed_challenge" />;
      }
      const timeLimit = blueprint.timeLimitSeconds || 60;
      return (
        <TimedChallengeWrapper
          timeLimitSeconds={timeLimit}
          onTimeUp={completeInteraction}
        >
          <MechanicRouter {...props} mode={wrappedMode as InteractionMode} />
        </TimedChallengeWrapper>
      );
    }

    // ── Registry lookup ──
    const entry = MECHANIC_REGISTRY[mode];
    if (!entry) {
      return <MechanicConfigError mechanic={mode} />;
    }

    // ── Registry-driven config validation ──
    if (entry.validateConfig) {
      const error = entry.validateConfig(blueprint);
      if (error) {
        return <MechanicConfigError mechanic={mode} />;
      }
    }

    // ── Build context and extract props ──
    const ctx: MechanicContext = {
      blueprint,
      onAction,
      completeInteraction,
      progress,
      dnd,
      hierarchical,
    };

    const componentProps = entry.extractProps(ctx);
    const Component = entry.component;
    return <Component {...componentProps} />;
  }, [mode, blueprint, onAction, completeInteraction, progress, dnd, hierarchical, props]);

  // ── Wrap in DndContext if needed ──
  if (registryNeedsDndContext(mode) && dnd) {
    return (
      <DndContext
        sensors={dnd.sensors}
        collisionDetection={smallestTargetCollision}
        onDragStart={dnd.onDragStart}
        onDragEnd={dnd.onDragEnd}
        onDragCancel={dnd.onDragCancel}
      >
        {content}
      </DndContext>
    );
  }

  return <>{content}</>;
}
