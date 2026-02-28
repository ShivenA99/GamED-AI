/**
 * extractTaskConfig - Resolve mechanic-specific config for a given task/mode.
 *
 * Priority:
 *  1. task.config (per-task override)
 *  2. blueprint[mechanicTypeConfig] (root-level config matching mechanic via registry)
 *  3. mechanics[].config (from scene mechanics array)
 *  4. fallback defaults
 */

import { InteractiveDiagramBlueprint, InteractionMode } from '../types';
import { MECHANIC_REGISTRY } from '../mechanicRegistry';

export function extractMechanicConfig(
  blueprint: InteractiveDiagramBlueprint,
  mode: InteractionMode,
): Record<string, unknown> | undefined {
  // 1. Try root-level config field via registry's configKey
  const entry = MECHANIC_REGISTRY[mode];
  const configKey = entry?.configKey;
  if (configKey) {
    const rootConfig = blueprint[configKey];
    if (rootConfig && typeof rootConfig === 'object') {
      return rootConfig as Record<string, unknown>;
    }
  }

  // 2. Try mechanics array
  const mechanic = blueprint.mechanics?.find(
    (m) => (typeof m === 'string' ? m : m.type) === mode,
  );
  if (mechanic && typeof mechanic === 'object' && 'config' in mechanic) {
    return mechanic.config as Record<string, unknown>;
  }

  return undefined;
}

/**
 * Check if a mechanic mode needs DndContext (drag-and-drop).
 * Delegates to the mechanic registry for source of truth.
 */
export { registryNeedsDndContext as mechanicNeedsDndContext } from '../mechanicRegistry';
