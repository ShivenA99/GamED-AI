'use client';

import React from 'react';
import {
  DragStartEvent,
  DragEndEvent,
  SensorDescriptor,
  SensorOptions,
} from '@dnd-kit/core';
import {
  InteractiveDiagramBlueprint,
  InteractionMode,
  PlacedLabel,
  Label,
  DistractorLabel,
  IdentificationProgress,
  TracePathProgress,
  HierarchyState,
  DescriptionMatchingState,
  SequencingProgress,
  SortingProgress,
  MemoryMatchProgress,
  BranchingProgress,
  CompareProgress,
  MechanicAction,
  ActionResult,
  ModeTransitionTrigger,
} from './types';
import type { MechanicProgressState } from './engine/mechanicInitializer';

// ─── DnD State Bundle ────────────────────────────────────────────────
export interface DndState {
  placedLabels: PlacedLabel[];
  availableLabels: (Label | DistractorLabel)[];
  draggingLabelId: string | null;
  incorrectFeedback: { labelId: string; message: string } | null;
  showHints: boolean;
  sensors: SensorDescriptor<SensorOptions>[];
  onDragStart: (e: DragStartEvent) => void;
  onDragEnd: (e: DragEndEvent) => void;
  onDragCancel: () => void;
}

// ─── Hierarchical Mode Callbacks (not a mechanic) ────────────────────
export interface HierarchicalModeCallbacks {
  hierarchyState: HierarchyState | null;
  onGroupExpand: (groupId: string) => void;
  onHierarchyLabelPlace: (labelId: string, zoneId: string, isCorrect: boolean) => void;
}

// ─── Progress Map ────────────────────────────────────────────────────
export interface MechanicProgressMap {
  identification: IdentificationProgress | null;
  trace: TracePathProgress | null;
  sequencing: SequencingProgress | null;
  sorting: SortingProgress | null;
  memoryMatch: MemoryMatchProgress | null;
  branching: BranchingProgress | null;
  compare: CompareProgress | null;
  descriptionMatching: DescriptionMatchingState | null;
}

// ─── Mechanic Context (passed to extractProps) ───────────────────────
export interface MechanicContext {
  blueprint: InteractiveDiagramBlueprint;
  onAction: (action: MechanicAction) => ActionResult | null;
  completeInteraction: () => void;
  progress: MechanicProgressMap;
  dnd: DndState | null;
  hierarchical: HierarchicalModeCallbacks | null;
}

// ─── Registry Entry ──────────────────────────────────────────────────
export interface MechanicRegistryEntry {
  component: React.ComponentType<any>;
  needsDndContext: boolean;
  configKey: keyof InteractiveDiagramBlueprint | null;
  extractProps: (ctx: MechanicContext) => Record<string, unknown>;

  // ── Layer 5: Engine metadata ──
  /** Calculate max score for this mechanic */
  getMaxScore: (blueprint: InteractiveDiagramBlueprint, pointsPerZone: number) => number;
  /** Check if this mechanic is complete given current progress */
  isComplete: (progress: MechanicProgressMap, blueprint: InteractiveDiagramBlueprint, extra?: EngineExtra) => boolean;
  /** Check if a transition trigger is satisfied (null = not handled by this mechanic) */
  checkTrigger?: (trigger: ModeTransitionTrigger, progress: MechanicProgressMap, blueprint: InteractiveDiagramBlueprint, extra?: EngineExtra) => boolean | null;

  // ── Layer 2: Registry-driven per-mechanic logic ──
  /** Validate that blueprint has the required config for this mechanic. Returns error message if invalid, null if valid. */
  validateConfig?: (blueprint: InteractiveDiagramBlueprint) => string | null;
  /** Extract instruction text from blueprint config for this mechanic. */
  getInstructions?: (blueprint: InteractiveDiagramBlueprint) => string | null;
  /** Initialize progress state for this mechanic. Returns fields to spread into MechanicProgressState. */
  initializeProgress?: (blueprint: InteractiveDiagramBlueprint) => Partial<MechanicProgressState>;
}

/** Extra state needed by engine functions that isn't in progress map */
export interface EngineExtra {
  placedLabels?: PlacedLabel[];
  taskLabelCount?: number;
  hierarchyState?: HierarchyState | null;
}

// ─── Lazy imports (avoid circular deps) ──────────────────────────────
// Components are imported at usage site (MechanicRouter) to keep this file
// as a pure data registry. We use string keys and resolve components at render.

import EnhancedDragDropGame from './EnhancedDragDropGame';
import { EnhancedHotspotManager } from './interactions/EnhancedHotspotManager';
import { EnhancedPathDrawer } from './interactions/EnhancedPathDrawer';
import EnhancedSequenceBuilder from './interactions/EnhancedSequenceBuilder';
import EnhancedSortingCategories from './interactions/EnhancedSortingCategories';
import { EnhancedMemoryMatch } from './interactions/EnhancedMemoryMatch';
import {
  HierarchyController,
  DescriptionMatcher,
  CompareContrast,
  BranchingScenario,
} from './interactions';

// ─── Registry ────────────────────────────────────────────────────────
export const MECHANIC_REGISTRY: Partial<Record<InteractionMode, MechanicRegistryEntry>> = {
  drag_drop: {
    component: EnhancedDragDropGame,
    needsDndContext: true,
    configKey: 'dragDropConfig',
    extractProps: (ctx) => ({
      blueprint: ctx.blueprint,
      placedLabels: ctx.dnd?.placedLabels ?? [],
      availableLabels: ctx.dnd?.availableLabels ?? [],
      draggingLabelId: ctx.dnd?.draggingLabelId ?? null,
      incorrectFeedback: ctx.dnd?.incorrectFeedback ?? null,
      showHints: ctx.dnd?.showHints ?? false,
      sensors: ctx.dnd?.sensors ?? [],
      onDragStart: ctx.dnd?.onDragStart,
      onDragEnd: ctx.dnd?.onDragEnd,
      onDragCancel: ctx.dnd?.onDragCancel,
      onAction: ctx.onAction,
    }),
    validateConfig: (bp) => !bp.labels?.length ? 'No labels configured for drag_drop' : null,
    getInstructions: () => null,
    getMaxScore: (bp, pts) => bp.labels.length * pts,
    isComplete: (_progress, bp, extra) => {
      const taskLabelCount = extra?.taskLabelCount ?? bp.labels.length;
      const placedCorrect = extra?.placedLabels?.filter(p => p.isCorrect).length ?? 0;
      return placedCorrect >= taskLabelCount;
    },
    checkTrigger: (trigger, _progress, bp, extra) => {
      const placedLabels = extra?.placedLabels ?? [];
      const correctPlacements = placedLabels.filter(p => p.isCorrect).length;
      const totalLabels = extra?.taskLabelCount ?? bp.labels.length;
      switch (trigger) {
        case 'all_zones_labeled':
          return correctPlacements >= totalLabels;
        case 'percentage_complete': return null; // handled generically
        case 'specific_zones': return null; // handled generically
        default: return null;
      }
    },
  },

  click_to_identify: {
    component: EnhancedHotspotManager,
    needsDndContext: false,
    configKey: 'clickToIdentifyConfig',
    extractProps: (ctx) => ({
      zones: ctx.blueprint.diagram.zones,
      prompts: ctx.blueprint.identificationPrompts || [],
      config: ctx.blueprint.clickToIdentifyConfig,
      progress: ctx.progress.identification,
      onAction: ctx.onAction,
      assetUrl: ctx.blueprint.diagram.assetUrl,
      width: ctx.blueprint.diagram.width,
      height: ctx.blueprint.diagram.height,
    }),
    validateConfig: (bp) => !bp.identificationPrompts?.length ? 'No identification prompts' : null,
    getInstructions: (bp) => bp.clickToIdentifyConfig?.instructions ?? null,
    initializeProgress: (bp) => ({
      identificationProgress: bp.identificationPrompts?.length
        ? { currentPromptIndex: 0, completedZoneIds: [], incorrectAttempts: 0 }
        : null,
    }),
    getMaxScore: (bp, pts) => (bp.identificationPrompts?.length ?? 0) * pts,
    isComplete: (progress, bp) => {
      const id = progress.identification;
      if (!id) return false;
      const totalPrompts = bp.identificationPrompts?.length ?? 0;
      return id.currentPromptIndex >= totalPrompts;
    },
    checkTrigger: (trigger, progress, bp) => {
      if (trigger === 'identification_complete') {
        const id = progress.identification;
        if (!id) return false;
        const totalPrompts = bp.identificationPrompts?.length ?? 0;
        return id.currentPromptIndex >= totalPrompts;
      }
      return null;
    },
  },

  trace_path: {
    component: EnhancedPathDrawer,
    needsDndContext: false,
    configKey: 'tracePathConfig',
    extractProps: (ctx) => ({
      zones: ctx.blueprint.diagram.zones,
      paths: ctx.blueprint.paths || [],
      config: ctx.blueprint.tracePathConfig,
      assetUrl: ctx.blueprint.diagram.assetUrl,
      width: ctx.blueprint.diagram.width,
      height: ctx.blueprint.diagram.height,
      traceProgress: ctx.progress.trace,
      onAction: ctx.onAction,
    }),
    validateConfig: (bp) => !bp.paths?.length ? 'No paths configured for trace_path' : null,
    getInstructions: (bp) => bp.tracePathConfig?.instructions ?? null,
    initializeProgress: (bp) => ({
      pathProgress: bp.paths?.length
        ? { pathId: bp.paths[0].id, visitedWaypoints: [], isComplete: false }
        : null,
    }),
    getMaxScore: (bp, pts) => {
      const totalWaypoints = bp.paths?.reduce((sum, p) => sum + p.waypoints.length, 0) ?? 0;
      return totalWaypoints * pts;
    },
    isComplete: (progress) => {
      const tp = progress.trace;
      if (!tp) return false;
      const entries = Object.values(tp.pathProgressMap);
      return entries.length > 0 && entries.every(e => e.isComplete);
    },
    checkTrigger: (trigger, progress) => {
      if (trigger === 'path_complete') {
        const tp = progress.trace;
        if (!tp) return false;
        const entries = Object.values(tp.pathProgressMap);
        return entries.length > 0 && entries.every(e => e.isComplete);
      }
      return null;
    },
  },

  sequencing: {
    component: EnhancedSequenceBuilder,
    needsDndContext: false,
    configKey: 'sequenceConfig',
    extractProps: (ctx) => {
      const bp = ctx.blueprint;
      const sc = bp.sequenceConfig;
      // Backend sends snake_case, frontend types use camelCase — normalize both
      const correctOrder = (sc as any)?.correct_order ?? sc?.correctOrder;
      if (sc && sc.items?.length > 0) {
        // Normalize interaction_pattern values
        const rawPattern = sc.interaction_pattern ?? (sc as any)?.interactionPattern ?? 'drag_to_reorder';
        const interactionPattern = rawPattern === 'drag_reorder' ? 'drag_to_reorder' : rawPattern;
        // Normalize card_type values
        const rawCard = sc.card_type ?? (sc as any)?.cardType ?? 'text_only';
        const cardType = rawCard === 'image_card' ? 'image_and_text' : rawCard;
        return {
          items: sc.items.map((item: any, idx: number) => ({
            id: item.id,
            content: item.content ?? item.text ?? '',
            orderIndex: idx,
            description: item.explanation ?? item.description,
            image: item.image ?? item.image_url,
            icon: item.icon,
          })),
          correctOrder,
          allowPartialCredit: (sc as any)?.allow_partial_credit ?? sc?.allowPartialCredit,
          config: {
            layout_mode: (
              sc.layout_mode === 'vertical_list' ? 'vertical_timeline' :
              sc.layout_mode === 'circular_cycle' ? 'circular' :
              sc.layout_mode
            ),
            interaction_pattern: interactionPattern,
            card_type: cardType,
            connector_style: sc.connector_style ?? (sc as any)?.connectorStyle,
            show_position_numbers: sc.show_position_numbers ?? (sc as any)?.showPositionNumbers,
            is_cyclic: ((sc as any)?.sequence_type ?? sc?.sequenceType) === 'cyclic',
            instruction_text: (sc as any)?.instruction_text ?? sc?.instructionText,
          },
          storeProgress: ctx.progress.sequencing,
          onAction: ctx.onAction,
        };
      }
      // Fallback: derive from labels
      console.warn('Sequencing mode active but no sequenceConfig. Using labels as fallback.');
      return {
        items: bp.labels.map((l, idx) => ({ id: l.id, content: l.text, orderIndex: idx })),
        correctOrder: bp.labels.map((l) => l.id),
        onAction: ctx.onAction,
      };
    },
    validateConfig: (bp) => !bp.sequenceConfig?.items?.length ? 'No sequence items' : null,
    getInstructions: (bp) => (bp.sequenceConfig as any)?.instruction_text ?? bp.sequenceConfig?.instructionText ?? null,
    initializeProgress: (bp) => {
      if (!bp.sequenceConfig) return {};
      const sc = bp.sequenceConfig;
      const correctOrder = (sc as any)?.correct_order ?? sc?.correctOrder ?? [];
      const ids = sc.items.map((i: any) => i.id);
      return {
        sequencingProgress: {
          currentOrder: ids,
          isSubmitted: false,
          correctPositions: 0,
          totalPositions: correctOrder.length,
        },
      };
    },
    getMaxScore: (bp, pts) => (bp.sequenceConfig?.items.length ?? 0) * pts,
    isComplete: (progress) => {
      const sp = progress.sequencing;
      return sp !== null && sp !== undefined && sp.isSubmitted && sp.correctPositions === sp.totalPositions;
    },
    checkTrigger: (trigger, progress) => {
      if (trigger === 'sequence_complete') {
        const sp = progress.sequencing;
        return sp !== null && sp !== undefined && sp.isSubmitted && sp.correctPositions === sp.totalPositions;
      }
      return null;
    },
  },

  sorting_categories: {
    component: EnhancedSortingCategories,
    needsDndContext: false,
    configKey: 'sortingConfig',
    extractProps: (ctx) => {
      const config = ctx.blueprint.sortingConfig;
      return {
        items: config?.items ?? [],
        categories: config?.categories ?? [],
        config,
        storeProgress: ctx.progress.sorting,
        onAction: ctx.onAction,
      };
    },
    validateConfig: (bp) => !bp.sortingConfig?.items || !bp.sortingConfig?.categories ? 'Missing sorting items or categories' : null,
    getInstructions: (bp) => bp.sortingConfig?.instructions ?? null,
    initializeProgress: (bp) => {
      if (!bp.sortingConfig) return {};
      const initial: Record<string, string | null> = {};
      bp.sortingConfig.items.forEach(item => { initial[item.id] = null; });
      return {
        sortingProgress: {
          itemCategories: initial,
          isSubmitted: false,
          correctCount: 0,
          totalCount: bp.sortingConfig.items.length,
        },
      };
    },
    getMaxScore: (bp, pts) => (bp.sortingConfig?.items.length ?? 0) * pts,
    isComplete: (progress) => {
      const sp = progress.sorting;
      return sp !== null && sp !== undefined && sp.isSubmitted && sp.correctCount === sp.totalCount;
    },
    checkTrigger: (trigger, progress) => {
      if (trigger === 'sorting_complete') {
        const sp = progress.sorting;
        return sp !== null && sp !== undefined && sp.isSubmitted && sp.correctCount === sp.totalCount;
      }
      return null;
    },
  },

  memory_match: {
    component: EnhancedMemoryMatch,
    needsDndContext: false,
    configKey: 'memoryMatchConfig',
    extractProps: (ctx) => ({
      config: ctx.blueprint.memoryMatchConfig ?? { pairs: [] },
      storeProgress: ctx.progress.memoryMatch,
      onAction: ctx.onAction,
    }),
    validateConfig: (bp) => !bp.memoryMatchConfig?.pairs ? 'No memory match pairs' : null,
    getInstructions: (bp) => bp.memoryMatchConfig?.instructions ?? null,
    initializeProgress: (bp) => {
      if (!bp.memoryMatchConfig) return {};
      return {
        memoryMatchProgress: {
          matchedPairIds: [],
          attempts: 0,
          totalPairs: bp.memoryMatchConfig.pairs.length,
        },
      };
    },
    getMaxScore: (bp, pts) => (bp.memoryMatchConfig?.pairs.length ?? 0) * pts,
    isComplete: (progress) => {
      const mm = progress.memoryMatch;
      return mm !== null && mm !== undefined && mm.matchedPairIds.length >= mm.totalPairs;
    },
    checkTrigger: (trigger, progress) => {
      if (trigger === 'memory_complete') {
        const mm = progress.memoryMatch;
        return mm !== null && mm !== undefined && mm.matchedPairIds.length >= mm.totalPairs;
      }
      return null;
    },
  },

  branching_scenario: {
    component: BranchingScenario,
    needsDndContext: false,
    configKey: 'branchingConfig',
    extractProps: (ctx) => {
      const config = ctx.blueprint.branchingConfig as any;
      return {
        nodes: config?.nodes ?? [],
        startNodeId: config?.startNodeId ?? config?.start_node_id ?? '',
        showPathTaken: config?.show_path_taken ?? config?.showPathTaken ?? true,
        allowBacktrack: config?.allow_backtrack ?? config?.allowBacktrack ?? true,
        showConsequences: config?.show_consequences ?? config?.showConsequences ?? true,
        multipleValidEndings: config?.multiple_valid_endings ?? config?.multipleValidEndings ?? false,
        storeProgress: ctx.progress.branching,
        onAction: ctx.onAction,
        instructions: config?.instructions,
      };
    },
    validateConfig: (bp) => {
      const c = bp.branchingConfig as any;
      return !c?.nodes || !(c?.startNodeId || c?.start_node_id) ? 'Missing branching nodes or startNodeId' : null;
    },
    getInstructions: (bp) => bp.branchingConfig?.instructions ?? null,
    initializeProgress: (bp) => {
      if (!bp.branchingConfig) return {};
      const c = bp.branchingConfig as any;
      return {
        branchingProgress: {
          currentNodeId: c.startNodeId ?? c.start_node_id ?? '',
          pathTaken: [],
        },
      };
    },
    getMaxScore: (bp, pts) => (bp.branchingConfig?.nodes?.filter(n => !n.isEndNode).length ?? 0) * pts,
    isComplete: (progress, bp) => {
      const br = progress.branching;
      if (!br || !bp.branchingConfig) return false;
      const currentNode = bp.branchingConfig.nodes.find(n => n.id === br.currentNodeId);
      return currentNode?.isEndNode === true;
    },
    checkTrigger: (trigger, progress, bp) => {
      if (trigger === 'branching_complete') {
        const br = progress.branching;
        if (!br || !bp.branchingConfig) return false;
        const currentNode = bp.branchingConfig.nodes.find(n => n.id === br.currentNodeId);
        return currentNode?.isEndNode === true;
      }
      return null;
    },
  },

  compare_contrast: {
    component: CompareContrast,
    needsDndContext: false,
    configKey: 'compareConfig',
    extractProps: (ctx) => {
      const bp = ctx.blueprint;
      const config = bp.compareConfig;
      if (config && config.diagramA && config.diagramB) {
        return {
          diagramA: config.diagramA,
          diagramB: config.diagramB,
          expectedCategories: config.expectedCategories,
          highlightMatching: config.highlightMatching ?? true,
          instructions: config.instructions,
          storeProgress: ctx.progress.compare,
          onAction: ctx.onAction,
        };
      }
      // Legacy stub fallback
      return {
        diagramA: {
          id: 'diagramA',
          name: bp.title,
          imageUrl: bp.diagram.assetUrl || '',
          zones: bp.diagram.zones.map((z) => ({
            id: z.id, label: z.label, x: z.x || 50, y: z.y || 50,
            width: (z.radius || 5) * 2, height: (z.radius || 5) * 2,
          })),
        },
        diagramB: {
          id: 'diagramB',
          name: bp.title + ' (Compare)',
          imageUrl: bp.diagram.assetUrl || '',
          zones: bp.diagram.zones.map((z) => ({
            id: `${z.id}_b`, label: z.label, x: z.x || 50, y: z.y || 50,
            width: (z.radius || 5) * 2, height: (z.radius || 5) * 2,
          })),
        },
        expectedCategories: bp.diagram.zones.reduce(
          (acc, z) => { acc[z.id] = 'similar'; return acc; },
          {} as Record<string, 'similar' | 'different' | 'unique_a' | 'unique_b'>,
        ),
      };
    },
    getInstructions: (bp) => bp.compareConfig?.instructions ?? null,
    initializeProgress: (bp) => {
      if (!bp.compareConfig) return {};
      return {
        compareProgress: {
          categorizations: {},
          isSubmitted: false,
          correctCount: 0,
          totalCount: Object.keys(bp.compareConfig.expectedCategories).length,
        },
      };
    },
    getMaxScore: (bp, pts) => Object.keys(bp.compareConfig?.expectedCategories ?? {}).length * pts,
    isComplete: (progress) => {
      const cp = progress.compare;
      return cp !== null && cp !== undefined && cp.isSubmitted && cp.correctCount === cp.totalCount;
    },
    checkTrigger: (trigger, progress) => {
      if (trigger === 'compare_complete') {
        const cp = progress.compare;
        return cp !== null && cp !== undefined && cp.isSubmitted && cp.correctCount === cp.totalCount;
      }
      return null;
    },
  },

  description_matching: {
    component: DescriptionMatcher,
    needsDndContext: false,
    configKey: 'descriptionMatchingConfig',
    extractProps: (ctx) => ({
      zones: ctx.blueprint.diagram.zones,
      labels: ctx.blueprint.labels,
      descriptions: ctx.blueprint.descriptionMatchingConfig?.descriptions,
      assetUrl: ctx.blueprint.diagram.assetUrl,
      onAction: ctx.onAction,
      mode: ctx.progress.descriptionMatching?.mode || 'click_zone',
      showHints: ctx.dnd?.showHints ?? false,
      storeProgress: ctx.progress.descriptionMatching,
    }),
    initializeProgress: (bp) => ({
      descriptionMatchingState: {
        currentIndex: 0,
        matches: [],
        mode: ((bp.descriptionMatchingConfig as Record<string, unknown>)?.mode as 'click_zone' | 'drag_description' | 'multiple_choice') || 'click_zone',
      },
    }),
    getMaxScore: (bp, pts) => bp.diagram.zones.filter(z => z.description).length * pts,
    isComplete: (progress, bp) => {
      const dm = progress.descriptionMatching;
      if (!dm) return false;
      const totalDescriptions = bp.diagram.zones.filter(z => z.description).length;
      return dm.currentIndex >= totalDescriptions;
    },
    checkTrigger: (trigger, progress, bp) => {
      if (trigger === 'description_complete') {
        const dm = progress.descriptionMatching;
        if (!dm) return false;
        const totalDescriptions = bp.diagram.zones.filter(z => z.description).length;
        return dm.currentIndex >= totalDescriptions;
      }
      return null;
    },
  },

  hierarchical: {
    component: HierarchyController,
    needsDndContext: true,
    configKey: null,
    extractProps: (ctx) => ({
      zones: ctx.blueprint.diagram.zones,
      zoneGroups: ctx.blueprint.zoneGroups || [],
      labels: ctx.blueprint.labels,
      onLabelPlace: ctx.hierarchical?.onHierarchyLabelPlace,
      onGroupComplete: ctx.hierarchical?.onGroupExpand,
      onAllComplete: ctx.completeInteraction,
      assetUrl: ctx.blueprint.diagram.assetUrl,
      assetPrompt: ctx.blueprint.diagram.assetPrompt,
      width: ctx.blueprint.diagram.width,
      height: ctx.blueprint.diagram.height,
    }),
    initializeProgress: (bp) => ({
      hierarchyState: bp.zoneGroups?.length
        ? { expandedGroups: [], completedParentZones: [] }
        : null,
    }),
    getMaxScore: (bp, pts) => {
      const regularZones = bp.labels.length;
      const childZones = bp.zoneGroups?.reduce((sum, g) => sum + g.childZoneIds.length, 0) ?? 0;
      return (regularZones + childZones) * pts;
    },
    isComplete: (_progress, bp, extra) => {
      // Hierarchical completion is driven by the HierarchyController calling completeInteraction
      // This is a best-effort check based on placed labels
      const placedCorrect = extra?.placedLabels?.filter(p => p.isCorrect).length ?? 0;
      const totalLabels = bp.labels.length + (bp.zoneGroups?.reduce((s, g) => s + g.childZoneIds.length, 0) ?? 0);
      return placedCorrect >= totalLabels;
    },
    checkTrigger: (trigger, _progress, bp, extra) => {
      if (trigger === 'hierarchy_level_complete') {
        const hs = extra?.hierarchyState;
        if (!hs) return false;
        const currentLevel = hs.expandedGroups.length + 1;
        const zonesAtLevel = bp.diagram.zones.filter(z => (z.hierarchyLevel || 1) === currentLevel);
        const placedLabels = extra?.placedLabels ?? [];
        const completedAtLevel = placedLabels.filter(p =>
          p.isCorrect && zonesAtLevel.some(z => z.id === p.zoneId)
        ).length;
        return completedAtLevel >= zonesAtLevel.length && zonesAtLevel.length > 0;
      }
      return null;
    },
  },
};

/**
 * Check if a mechanic mode needs DndContext (drag-and-drop).
 * Reads from registry instead of hardcoded list.
 */
export function registryNeedsDndContext(mode: InteractionMode): boolean {
  return MECHANIC_REGISTRY[mode]?.needsDndContext ?? false;
}

/**
 * Extract instruction text from the registry for a given mechanic mode.
 */
export function getRegistryInstructions(
  mode: InteractionMode,
  blueprint: InteractiveDiagramBlueprint,
): string | null {
  return MECHANIC_REGISTRY[mode]?.getInstructions?.(blueprint) ?? null;
}
