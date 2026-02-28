export { default as HotspotManager } from './HotspotManager';
export { default as PathDrawer } from './PathDrawer';
export { default as HierarchyController } from './HierarchyController';

// Preset 2 interaction components
export { DescriptionMatcher } from './DescriptionMatcher';
export { SVGZoneRenderer } from './SVGZoneRenderer';
export { GameSequenceRenderer } from './GameSequenceRenderer';
export { SceneProgressBar } from './SceneProgressBar';

// New interaction patterns (Agentic Game Design)
export { SequenceBuilder } from './SequenceBuilder';
export type { SequenceItem, SequenceBuilderProps, SequenceResult } from './SequenceBuilder';

export { CompareContrast } from './CompareContrast';
export type { ComparableDiagram, CompareZone, CompareContrastProps, CompareResult } from './CompareContrast';

export { SortingCategories } from './SortingCategories';
export type { SortableItem, Category, SortingCategoriesProps, SortingResult } from './SortingCategories';

export { TimedChallengeWrapper } from './TimedChallengeWrapper';
export type { TimedChallengeProps, TimedChallengeResult } from './TimedChallengeWrapper';

export { MemoryMatch } from './MemoryMatch';
export type { MatchPair, MemoryMatchProps, MemoryMatchResult } from './MemoryMatch';

export { BranchingScenario } from './BranchingScenario';
export type { DecisionNode, DecisionOption, BranchingScenarioProps } from './BranchingScenario';

// Temporal Intelligence (Petri Net-inspired zone visibility)
export {
  useTemporalController,
  createDefaultMotionPaths,
  canAppearTogether,
  computeRevealOrder,
} from './TemporalController';

// Undo/Redo Controls (Command Pattern UI)
export {
  UndoRedoControls,
  UndoRedoCompact,
  UndoRedoFloating,
  type UndoRedoControlsProps,
} from './UndoRedoControls';

// Multi-Mode Indicator (Agentic Interaction Design)
export {
  ModeIndicator,
  ModeBadge,
  type ModeIndicatorProps,
} from './ModeIndicator';
