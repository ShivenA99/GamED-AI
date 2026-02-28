'use client';

/**
 * Temporal Controller for Zone Visibility Management
 *
 * Implements a Petri Net-inspired constraint system for managing zone visibility
 * in label diagram games. Ensures overlapping zones from different hierarchies
 * never appear simultaneously, preventing visual clutter.
 *
 * Key features:
 * - O(1) mutex lookups via pre-computed maps
 * - Handles parent-child reveal cascades
 * - Respects priority-based constraint resolution
 * - Provides motion path trigger integration
 */

import { useMemo, useCallback } from 'react';
import {
  Zone,
  TemporalConstraint,
  MotionPath,
  TemporalState,
  TemporalConstraintType,
  MotionTrigger,
} from '../types';

// =============================================================================
// Types
// =============================================================================

interface UseTemporalControllerProps {
  zones: Zone[];
  constraints: TemporalConstraint[];
  completedZones: Set<string>;
  motionPaths?: MotionPath[];
}

interface UseTemporalControllerResult {
  /** Set of zone IDs that should be visible */
  visibleZones: Set<string>;
  /** Set of zone IDs blocked by mutex constraints */
  blockedZones: Set<string>;
  /** Set of zone IDs waiting for prerequisites */
  pendingZones: Set<string>;
  /** Check if a specific zone is visible */
  isZoneVisible: (zoneId: string) => boolean;
  /** Check if a zone is blocked by mutex */
  isZoneBlocked: (zoneId: string) => boolean;
  /** Get the reason why a zone is blocked */
  getBlockReason: (zoneId: string) => string | null;
  /** Get zones that will be unblocked when this zone is completed */
  getUnblockedOnComplete: (zoneId: string) => string[];
  /** Get motion paths for a specific trigger */
  getMotionPathsForTrigger: (trigger: MotionTrigger, zoneId?: string) => MotionPath[];
  /** Get the full temporal state */
  temporalState: TemporalState;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for managing zone visibility based on temporal constraints.
 *
 * Uses memoization and pre-computed lookup maps for optimal performance.
 */
export function useTemporalController({
  zones,
  constraints,
  completedZones,
  motionPaths = [],
}: UseTemporalControllerProps): UseTemporalControllerResult {
  // =========================================================================
  // Build mutex lookup map for O(1) checks
  // =========================================================================
  const mutexMap = useMemo(() => {
    const map = new Map<string, Set<string>>();

    for (const c of constraints) {
      if (c.constraint_type === 'mutex') {
        // Add bidirectional mutex
        if (!map.has(c.zone_a)) {
          map.set(c.zone_a, new Set());
        }
        if (!map.has(c.zone_b)) {
          map.set(c.zone_b, new Set());
        }
        map.get(c.zone_a)!.add(c.zone_b);
        map.get(c.zone_b)!.add(c.zone_a);
      }
    }

    return map;
  }, [constraints]);

  // =========================================================================
  // Build prerequisite lookup (before/sequence constraints)
  // =========================================================================
  const prerequisiteMap = useMemo(() => {
    const map = new Map<string, Set<string>>();

    for (const c of constraints) {
      if (c.constraint_type === 'before' || c.constraint_type === 'sequence') {
        // zone_a must be completed before zone_b appears
        if (!map.has(c.zone_b)) {
          map.set(c.zone_b, new Set());
        }
        map.get(c.zone_b)!.add(c.zone_a);
      }
    }

    return map;
  }, [constraints]);

  // =========================================================================
  // Build concurrent pairs set
  // =========================================================================
  const concurrentPairs = useMemo(() => {
    const pairs = new Set<string>();

    for (const c of constraints) {
      if (c.constraint_type === 'concurrent') {
        // Store in sorted order for consistent lookup
        const key = [c.zone_a, c.zone_b].sort().join('|');
        pairs.add(key);
      }
    }

    return pairs;
  }, [constraints]);

  // =========================================================================
  // Build zone hierarchy maps
  // =========================================================================
  const { parentToChildren, childToParent, rootZones } = useMemo(() => {
    const p2c = new Map<string, string[]>();
    const c2p = new Map<string, string>();
    const roots = new Set<string>();

    for (const zone of zones) {
      if (zone.parentZoneId) {
        c2p.set(zone.id, zone.parentZoneId);
        if (!p2c.has(zone.parentZoneId)) {
          p2c.set(zone.parentZoneId, []);
        }
        p2c.get(zone.parentZoneId)!.push(zone.id);
      } else {
        // Root zone (no parent or hierarchy level 1)
        roots.add(zone.id);
      }
    }

    return { parentToChildren: p2c, childToParent: c2p, rootZones: roots };
  }, [zones]);

  // =========================================================================
  // Compute visible, blocked, and pending zones
  // =========================================================================
  const { visibleZones, blockedZones, pendingZones, blockReasons } = useMemo(() => {
    const visible = new Set<string>();
    const blocked = new Set<string>();
    const pending = new Set<string>();
    const reasons = new Map<string, string>();

    // Helper: Check if zone has unmet prerequisites
    const hasUnmetPrerequisites = (zoneId: string): boolean => {
      const prereqs = prerequisiteMap.get(zoneId);
      if (!prereqs) return false;

      for (const prereq of prereqs) {
        if (!completedZones.has(prereq)) {
          return true;
        }
      }
      return false;
    };

    // Helper: Check if zone is blocked by mutex with visible zone
    const isBlockedByMutex = (zoneId: string, currentVisible: Set<string>): string | null => {
      const mutexPartners = mutexMap.get(zoneId);
      if (!mutexPartners) return null;

      for (const partner of mutexPartners) {
        if (currentVisible.has(partner) && !completedZones.has(partner)) {
          return partner;
        }
      }
      return null;
    };

    // Phase 1: Add root zones
    for (const zoneId of rootZones) {
      // Check prerequisites first
      if (hasUnmetPrerequisites(zoneId)) {
        pending.add(zoneId);
        reasons.set(zoneId, 'Waiting for prerequisite zones');
        continue;
      }

      // Check mutex
      const mutexPartner = isBlockedByMutex(zoneId, visible);
      if (mutexPartner) {
        blocked.add(zoneId);
        reasons.set(zoneId, `Blocked by mutex with ${mutexPartner}`);
        continue;
      }

      visible.add(zoneId);
    }

    // Phase 2: Add children of completed parents
    for (const parentId of completedZones) {
      const children = parentToChildren.get(parentId);
      if (!children) continue;

      for (const childId of children) {
        // Skip if already processed
        if (visible.has(childId) || blocked.has(childId) || pending.has(childId)) {
          continue;
        }

        // Check prerequisites
        if (hasUnmetPrerequisites(childId)) {
          pending.add(childId);
          reasons.set(childId, 'Waiting for prerequisite zones');
          continue;
        }

        // Check mutex
        const mutexPartner = isBlockedByMutex(childId, visible);
        if (mutexPartner) {
          blocked.add(childId);
          reasons.set(childId, `Blocked by mutex with ${mutexPartner}`);
          continue;
        }

        visible.add(childId);
      }
    }

    // Phase 3: Mark remaining zones as pending
    for (const zone of zones) {
      if (!visible.has(zone.id) && !blocked.has(zone.id) && !pending.has(zone.id)) {
        // Check if parent is not completed
        if (zone.parentZoneId && !completedZones.has(zone.parentZoneId)) {
          pending.add(zone.id);
          reasons.set(zone.id, `Waiting for parent ${zone.parentZoneId} to be completed`);
        }
      }
    }

    return { visibleZones: visible, blockedZones: blocked, pendingZones: pending, blockReasons: reasons };
  }, [zones, constraints, completedZones, mutexMap, prerequisiteMap, parentToChildren, rootZones]);

  // =========================================================================
  // Utility functions
  // =========================================================================

  const isZoneVisible = useCallback(
    (zoneId: string) => visibleZones.has(zoneId),
    [visibleZones]
  );

  const isZoneBlocked = useCallback(
    (zoneId: string) => blockedZones.has(zoneId),
    [blockedZones]
  );

  const getBlockReason = useCallback(
    (zoneId: string): string | null => {
      // Access blockReasons from the memoized result
      const mutexPartners = mutexMap.get(zoneId);
      if (mutexPartners) {
        for (const partner of mutexPartners) {
          if (visibleZones.has(partner) && !completedZones.has(partner)) {
            return `Blocked by mutex with ${partner}`;
          }
        }
      }
      return null;
    },
    [mutexMap, visibleZones, completedZones]
  );

  const getUnblockedOnComplete = useCallback(
    (zoneId: string): string[] => {
      const unblocked: string[] = [];

      // Find zones that have mutex with this zone
      const mutexPartners = mutexMap.get(zoneId);
      if (mutexPartners) {
        for (const partner of mutexPartners) {
          if (blockedZones.has(partner)) {
            unblocked.push(partner);
          }
        }
      }

      // Find children of this zone
      const children = parentToChildren.get(zoneId);
      if (children) {
        unblocked.push(...children);
      }

      return unblocked;
    },
    [mutexMap, blockedZones, parentToChildren]
  );

  const getMotionPathsForTrigger = useCallback(
    (trigger: MotionTrigger, zoneId?: string): MotionPath[] => {
      return motionPaths.filter((path) => {
        if (path.trigger !== trigger) return false;
        if (zoneId && path.asset_id !== zoneId) return false;
        return true;
      });
    },
    [motionPaths]
  );

  // =========================================================================
  // Build temporal state object
  // =========================================================================
  const temporalState: TemporalState = useMemo(
    () => ({
      activeZones: visibleZones,
      completedZones,
      blockedZones,
      pendingZones,
    }),
    [visibleZones, completedZones, blockedZones, pendingZones]
  );

  return {
    visibleZones,
    blockedZones,
    pendingZones,
    isZoneVisible,
    isZoneBlocked,
    getBlockReason,
    getUnblockedOnComplete,
    getMotionPathsForTrigger,
    temporalState,
  };
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Create default motion paths for common game events.
 */
export function createDefaultMotionPaths(zones: Zone[]): MotionPath[] {
  const paths: MotionPath[] = [];

  for (const zone of zones) {
    // Fade in on reveal
    paths.push({
      asset_id: zone.id,
      keyframes: [
        { time_ms: 0, opacity: 0 },
        { time_ms: 300, opacity: 1 },
      ],
      easing: 'ease-out',
      trigger: 'on_reveal',
    });

    // Pulse on correct
    paths.push({
      asset_id: zone.id,
      keyframes: [
        { time_ms: 0, scale: 1.0, backgroundColor: undefined },
        { time_ms: 200, scale: 1.1, backgroundColor: '#22c55e' },
        { time_ms: 400, scale: 1.0, backgroundColor: '#dcfce7' },
      ],
      easing: 'ease-in-out',
      trigger: 'on_complete',
    });

    // Shake on incorrect
    paths.push({
      asset_id: zone.id,
      keyframes: [
        { time_ms: 0, x: 0 },
        { time_ms: 50, x: -5 },
        { time_ms: 100, x: 5 },
        { time_ms: 150, x: -5 },
        { time_ms: 200, x: 5 },
        { time_ms: 250, x: 0 },
      ],
      easing: 'linear',
      trigger: 'on_incorrect',
    });
  }

  return paths;
}

/**
 * Check if two zones can appear together based on constraints.
 */
export function canAppearTogether(
  zoneA: string,
  zoneB: string,
  constraints: TemporalConstraint[]
): boolean {
  for (const c of constraints) {
    if (c.constraint_type === 'mutex') {
      if (
        (c.zone_a === zoneA && c.zone_b === zoneB) ||
        (c.zone_a === zoneB && c.zone_b === zoneA)
      ) {
        return false;
      }
    }
  }
  return true;
}

/**
 * Get the reveal order based on constraints and hierarchy.
 */
export function computeRevealOrder(
  zones: Zone[],
  constraints: TemporalConstraint[],
  suggestedOrder?: string[]
): string[] {
  // Start with suggested order if provided
  if (suggestedOrder && suggestedOrder.length > 0) {
    return suggestedOrder;
  }

  // Build order based on hierarchy level
  const sortedZones = [...zones].sort((a, b) => {
    const levelA = a.hierarchyLevel ?? 1;
    const levelB = b.hierarchyLevel ?? 1;
    return levelA - levelB;
  });

  return sortedZones.map((z) => z.id);
}

export default useTemporalController;
