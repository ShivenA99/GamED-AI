/**
 * Hooks exports for InteractiveDiagramGame
 */

export { useInteractiveDiagramState } from './useInteractiveDiagramState';
export {
  useCommandHistory,
  useLabelCommands,
  type UseCommandHistoryOptions,
  type UseCommandHistoryReturn,
  type CommandAnalyticsEvent,
} from './useCommandHistory';
export {
  useEventLog,
  type UseEventLogOptions,
} from './useEventLog';
export {
  usePersistence,
  type UsePersistenceOptions,
  type UsePersistenceReturn,
} from './usePersistence';
export { useReducedMotion } from './useReducedMotion';
export {
  useZoneCollision,
  isPointInPolygon,
  isPointInCircle,
  isPointInZone,
  findZoneAtPoint,
  findClosestZone,
  distanceToZoneCenter,
} from './useZoneCollision';

// Re-export command types for UI components
export type { CommandHistoryState } from '../commands';
