/**
 * mechanicInitializer.ts — Registry-driven mechanic state initialization.
 * Delegates to MECHANIC_REGISTRY.initializeProgress() for per-mechanic logic.
 * No React, no Zustand.
 */

import type {
  InteractiveDiagramBlueprint,
  InteractionMode,
  PathProgress,
  IdentificationProgress,
  HierarchyState,
  DescriptionMatchingState,
  SequencingProgress,
  SortingProgress,
  MemoryMatchProgress,
  BranchingProgress,
  CompareProgress,
} from '../types';
import { MECHANIC_REGISTRY } from '../mechanicRegistry';

/** All per-mechanic progress fields that get reset on mode init/transition */
export interface MechanicProgressState {
  pathProgress: PathProgress | null;
  identificationProgress: IdentificationProgress | null;
  hierarchyState: HierarchyState | null;
  descriptionMatchingState: DescriptionMatchingState | null;
  sequencingProgress: SequencingProgress | null;
  sortingProgress: SortingProgress | null;
  memoryMatchProgress: MemoryMatchProgress | null;
  branchingProgress: BranchingProgress | null;
  compareProgress: CompareProgress | null;
}

const DEFAULTS: MechanicProgressState = {
  pathProgress: null,
  identificationProgress: null,
  hierarchyState: null,
  descriptionMatchingState: null,
  sequencingProgress: null,
  sortingProgress: null,
  memoryMatchProgress: null,
  branchingProgress: null,
  compareProgress: null,
};

/**
 * Initialize all per-mechanic progress for a given mode.
 * Returns a full MechanicProgressState with nulls for inactive mechanics.
 */
export function initializeMechanicProgress(
  mode: InteractionMode,
  blueprint: InteractiveDiagramBlueprint,
): MechanicProgressState {
  const entry = MECHANIC_REGISTRY[mode];
  const custom = entry?.initializeProgress?.(blueprint) ?? {};
  return { ...DEFAULTS, ...custom };
}
