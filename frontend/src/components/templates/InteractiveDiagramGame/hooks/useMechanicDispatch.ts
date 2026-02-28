import { useCallback } from 'react';
import {
  InteractiveDiagramBlueprint,
  MechanicAction,
  ActionResult,
  PathProgress,
  IdentificationProgress,
} from '../types';
import { evaluateIdentification, evaluateDescriptionMatch } from '../engine/correctnessEvaluator';
import { useInteractiveDiagramState } from './useInteractiveDiagramState';

/**
 * Dependencies from the store / parent that the dispatch hook needs.
 */
export interface DispatchDeps {
  blueprint: InteractiveDiagramBlueprint;

  // Drag-drop
  placeLabel: (labelId: string, zoneId: string) => boolean;
  removeLabel: (labelId: string) => void;

  // Click-to-identify
  identificationProgress: IdentificationProgress | null;
  updateIdentificationProgress: (progress: IdentificationProgress) => void;

  // Trace path
  pathProgress: PathProgress | null;
  updatePathProgress: (progress: PathProgress) => void;

  // Sequencing
  updateSequenceOrder: (order: string[]) => void;
  submitSequence: () => void;

  // Sorting
  updateSortingPlacement: (itemId: string, categoryId: string | null) => void;
  submitSorting: () => void;

  // Memory match
  recordMemoryMatch: (pairId: string) => void;
  recordMemoryAttempt: () => void;

  // Branching
  recordBranchingChoice: (nodeId: string, optionId: string, isCorrect: boolean, nextNodeId: string | null) => void;
  undoBranchingChoice: () => void;

  // Compare/contrast
  updateCompareCategorization: (zoneId: string, category: string) => void;
  submitCompare: () => void;

  // Description matching
  recordDescriptionMatch: (match: { labelId: string; zoneId: string; isCorrect: boolean }) => void;
}

/**
 * Unified action dispatch hook. Translates MechanicAction → store calls.
 *
 * Layer 5: Correctness evaluation uses engine/correctnessEvaluator.
 * Layer 3: Returns ActionResult so components get immediate feedback
 *          without needing to duplicate scoring/correctness logic.
 */
export function useMechanicDispatch(deps: DispatchDeps): (action: MechanicAction) => ActionResult | null {
  const {
    blueprint,
    placeLabel,
    removeLabel,
    identificationProgress,
    updateIdentificationProgress,
    pathProgress,
    updatePathProgress,
    updateSequenceOrder,
    submitSequence,
    updateSortingPlacement,
    submitSorting,
    recordMemoryMatch,
    recordMemoryAttempt,
    recordBranchingChoice,
    undoBranchingChoice,
    updateCompareCategorization,
    submitCompare,
    recordDescriptionMatch,
  } = deps;

  return useCallback(
    (action: MechanicAction): ActionResult | null => {
      switch (action.type) {
        // ---- click_to_identify ----
        case 'identify': {
          if (!identificationProgress) return null;
          const { isCorrect } = evaluateIdentification(action.zoneId, identificationProgress, blueprint);
          if (isCorrect) {
            updateIdentificationProgress({
              ...identificationProgress,
              currentPromptIndex: identificationProgress.currentPromptIndex + 1,
              completedZoneIds: [...identificationProgress.completedZoneIds, action.zoneId],
            });
          } else {
            updateIdentificationProgress({
              ...identificationProgress,
              incorrectAttempts: identificationProgress.incorrectAttempts + 1,
            });
          }
          return { isCorrect, scoreDelta: isCorrect ? 1 : 0 };
        }

        // ---- trace_path ----
        case 'visit_waypoint': {
          if (!pathProgress) return null;
          const newVisited = [...pathProgress.visitedWaypoints, action.zoneId];
          const tracePath = blueprint.paths?.find(p => p.id === action.pathId);
          const totalWaypoints = tracePath?.waypoints?.length ?? 0;
          const isPathComplete = totalWaypoints > 0 && newVisited.length >= totalWaypoints;
          updatePathProgress({
            pathId: action.pathId,
            visitedWaypoints: newVisited,
            isComplete: isPathComplete,
          });
          return null; // fire-and-forget
        }
        case 'submit_path': {
          if (!pathProgress) return null;
          updatePathProgress({
            pathId: action.pathId,
            visitedWaypoints: action.selectedZoneIds,
            isComplete: true,
          });
          // Validate against blueprint paths
          const path = blueprint.paths?.find(p => p.id === action.pathId);
          const correctOrder = path?.waypoints
            ?.filter(w => w.zoneId)
            .sort((a, b) => a.order - b.order)
            .map(w => w.zoneId) ?? [];
          const isPathCorrect = correctOrder.length > 0
            && action.selectedZoneIds.length === correctOrder.length
            && action.selectedZoneIds.every((id: string, i: number) => id === correctOrder[i]);
          return { isCorrect: isPathCorrect, scoreDelta: 0, data: { submitted: true } };
        }

        // ---- sequencing ----
        case 'reorder': {
          updateSequenceOrder(action.newOrder);
          return null; // fire-and-forget
        }
        case 'submit_sequence': {
          submitSequence();
          // Zustand set is sync — getState() returns post-update values
          const sp = useInteractiveDiagramState.getState().sequencingProgress;
          const isSeqCorrect = sp != null && sp.correctPositions === sp.totalPositions;
          return {
            isCorrect: isSeqCorrect,
            scoreDelta: 0,
            data: { submitted: true, correctPositions: sp?.correctPositions, totalPositions: sp?.totalPositions },
          };
        }

        // ---- sorting_categories ----
        case 'sort': {
          updateSortingPlacement(action.itemId, action.categoryId);
          return null; // fire-and-forget
        }
        case 'unsort': {
          updateSortingPlacement(action.itemId, null);
          return null; // fire-and-forget
        }
        case 'submit_sorting': {
          submitSorting();
          const sortP = useInteractiveDiagramState.getState().sortingProgress;
          const isSortCorrect = sortP != null && sortP.correctCount === sortP.totalCount;
          return {
            isCorrect: isSortCorrect,
            scoreDelta: 0,
            data: { submitted: true, correctCount: sortP?.correctCount, totalCount: sortP?.totalCount },
          };
        }

        // ---- memory_match ----
        case 'match_pair': {
          recordMemoryMatch(action.pairId);
          return { isCorrect: true, scoreDelta: 1, data: { pairId: action.pairId } };
        }
        case 'memory_attempt': {
          recordMemoryAttempt();
          return null; // fire-and-forget
        }

        // ---- branching_scenario ----
        case 'branching_choice': {
          recordBranchingChoice(action.nodeId, action.optionId, action.isCorrect, action.nextNodeId);
          return {
            isCorrect: action.isCorrect,
            scoreDelta: action.isCorrect ? 1 : 0,
            data: { nodeId: action.nodeId, nextNodeId: action.nextNodeId },
          };
        }
        case 'branching_undo': {
          undoBranchingChoice();
          return null; // fire-and-forget
        }

        // ---- compare_contrast ----
        case 'categorize': {
          updateCompareCategorization(action.zoneId, action.category);
          return null; // fire-and-forget
        }
        case 'submit_compare': {
          submitCompare();
          const cp = useInteractiveDiagramState.getState().compareProgress;
          const isCompCorrect = cp != null && cp.correctCount === cp.totalCount;
          return {
            isCorrect: isCompCorrect,
            scoreDelta: 0,
            data: { submitted: true, correctCount: cp?.correctCount, totalCount: cp?.totalCount },
          };
        }

        // ---- description_matching ----
        case 'description_match': {
          const { isCorrect } = evaluateDescriptionMatch(action.labelId, action.zoneId, blueprint);
          recordDescriptionMatch({ labelId: action.labelId, zoneId: action.zoneId, isCorrect });
          return { isCorrect, scoreDelta: isCorrect ? 1 : 0 };
        }

        // ---- drag_drop ----
        case 'place': {
          const isCorrect = placeLabel(action.labelId, action.zoneId);
          return { isCorrect, scoreDelta: isCorrect ? 1 : 0 };
        }
        case 'remove': {
          removeLabel(action.labelId);
          return null;
        }

        default:
          console.warn('[useMechanicDispatch] Unhandled action:', action);
          return null;
      }
    },
    [
      blueprint, placeLabel, removeLabel, identificationProgress, updateIdentificationProgress,
      pathProgress, updatePathProgress, updateSequenceOrder, submitSequence,
      updateSortingPlacement, submitSorting, recordMemoryMatch, recordMemoryAttempt,
      recordBranchingChoice, undoBranchingChoice, updateCompareCategorization,
      submitCompare, recordDescriptionMatch,
    ]
  );
}
