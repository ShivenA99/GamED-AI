// ============================================================================
// Constraint & Scoring Normalization Layer
// ============================================================================
// Normalizes backend LLM-generated constraint puzzle data to match the
// frontend TypeScript types defined in constraintPuzzleTypes.ts.
//
// Handles three categories of mismatch:
// 1. Constraint shape: backend uses {type, params: {prop: val}, description}
//    but frontend expects typed fields at top level (e.g. {type: "capacity", property: "weight", max: 15})
// 2. Scoring config: backend uses different method names (optimality_ratio vs ratio)
//    and may nest params in a params dict
// 3. Item field names: backend uses "name", frontend expects "label"
// ============================================================================

import type {
  Constraint,
  PuzzleScoringConfig,
  SelectableItem,
  BoardConfig,
  GenericConstraintPuzzleBlueprint,
} from './constraintPuzzleTypes';

// ---------------------------------------------------------------------------
// Constraint normalization
// ---------------------------------------------------------------------------

/**
 * Map of backend constraint type names to the frontend's discriminated union types.
 * The frontend Constraint union supports exactly these types:
 *   capacity | exact_target | no_overlap | no_conflict | count_exact |
 *   count_range | all_different | all_assigned | connected
 */
const CONSTRAINT_TYPE_MAP: Record<string, Constraint['type']> = {
  // Direct matches
  capacity: 'capacity',
  exact_target: 'exact_target',
  no_overlap: 'no_overlap',
  no_conflict: 'no_conflict',
  count_exact: 'count_exact',
  count_range: 'count_range',
  all_different: 'all_different',
  all_assigned: 'all_assigned',
  connected: 'connected',
  // Backend variants that map to frontend types
  sum_property: 'capacity',
  max_property: 'capacity',
  min_count: 'count_range',
  max_count: 'count_range',
  exact_count: 'count_exact',
  unique: 'all_different',
  distinct: 'all_different',
  no_duplicate: 'all_different',
  fill_all: 'all_assigned',
  assign_all: 'all_assigned',
  connectivity: 'connected',
  reachable: 'connected',
  target: 'exact_target',
  target_sum: 'exact_target',
  overlap: 'no_overlap',
  time_overlap: 'no_overlap',
  conflict: 'no_conflict',
  queen_conflict: 'no_conflict',
};

/**
 * Normalize a single raw constraint object from the backend into the frontend
 * Constraint discriminated union shape.
 *
 * Handles both flat format (frontend-native) and nested {type, params, description}
 * format that the backend LLM may produce.
 */
export function normalizeConstraint(raw: Record<string, unknown>): Constraint | null {
  if (!raw || typeof raw !== 'object') return null;

  const rawType = String(raw.type || '').toLowerCase().trim();
  const mappedType = CONSTRAINT_TYPE_MAP[rawType];

  if (!mappedType) {
    // Unknown constraint type - skip rather than crash
    console.warn(`[normalizeConstraint] Unknown constraint type: "${rawType}", skipping`);
    return null;
  }

  // Flatten params dict to top level: params fields are overridden by top-level fields
  const params = raw.params && typeof raw.params === 'object'
    ? (raw.params as Record<string, unknown>)
    : {};
  // Top-level fields take precedence over params
  const flat: Record<string, unknown> = { ...params };
  for (const [key, value] of Object.entries(raw)) {
    if (key !== 'params' && key !== 'type' && key !== 'description') {
      flat[key] = value;
    }
  }

  // Build the correct shape for each constraint type
  switch (mappedType) {
    case 'capacity': {
      const property = asString(flat.property) || asString(flat.prop) || 'value';
      const max = asNumber(flat.max) ?? asNumber(flat.limit) ?? asNumber(flat.maximum) ?? Infinity;
      return {
        type: 'capacity',
        property,
        max,
        label: asStringOptional(flat.label) ?? asStringOptional(raw.description as unknown),
        showBar: asBoolean(flat.showBar),
      };
    }

    case 'exact_target': {
      const target = asNumber(flat.target) ?? asNumber(flat.targetValue) ?? asNumber(flat.value) ?? 0;
      return {
        type: 'exact_target',
        property: asStringOptional(flat.property),
        target,
        showBar: asBoolean(flat.showBar),
      };
    }

    case 'no_overlap': {
      const startProperty = asString(flat.startProperty) || asString(flat.start_property) || asString(flat.start) || 'start';
      const endProperty = asString(flat.endProperty) || asString(flat.end_property) || asString(flat.end) || 'end';
      return {
        type: 'no_overlap',
        startProperty,
        endProperty,
      };
    }

    case 'no_conflict': {
      const ruleRaw = asString(flat.conflictRule) || asString(flat.conflict_rule) || asString(flat.rule) || 'row_col_diagonal';
      const validRules = ['row_col_diagonal', 'row_col', 'adjacent'] as const;
      const conflictRule = validRules.includes(ruleRaw as typeof validRules[number])
        ? (ruleRaw as 'row_col_diagonal' | 'row_col' | 'adjacent')
        : 'row_col_diagonal';
      return {
        type: 'no_conflict',
        conflictRule,
      };
    }

    case 'count_exact': {
      const count = asNumber(flat.count) ?? asNumber(flat.exact) ?? asNumber(flat.n) ?? 1;
      return {
        type: 'count_exact',
        count,
        label: asStringOptional(flat.label) ?? asStringOptional(raw.description as unknown),
      };
    }

    case 'count_range': {
      // Handle min_count / max_count backend types that mapped here
      let min = asNumberOptional(flat.min);
      let max = asNumberOptional(flat.max);
      if (rawType === 'min_count') {
        min = min ?? asNumber(flat.count) ?? 1;
      } else if (rawType === 'max_count') {
        max = max ?? asNumber(flat.count) ?? 10;
      }
      const result: Constraint & { type: 'count_range' } = { type: 'count_range' };
      if (min != null) result.min = min;
      if (max != null) result.max = max;
      return result;
    }

    case 'all_different': {
      const scopeRaw = asString(flat.scope) || 'all';
      const validScopes = ['neighbors', 'row', 'col', 'all'] as const;
      const scope = validScopes.includes(scopeRaw as typeof validScopes[number])
        ? (scopeRaw as 'neighbors' | 'row' | 'col' | 'all')
        : 'all';
      return { type: 'all_different', scope };
    }

    case 'all_assigned':
      return { type: 'all_assigned' };

    case 'connected':
      return { type: 'connected' };
  }
}

/**
 * Normalize an array of raw constraints, filtering out any that cannot be mapped.
 */
export function normalizeConstraints(raw: unknown): Constraint[] {
  if (!Array.isArray(raw)) return [];
  const results: Constraint[] = [];
  for (const item of raw) {
    if (item && typeof item === 'object') {
      const normalized = normalizeConstraint(item as Record<string, unknown>);
      if (normalized) results.push(normalized);
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Scoring config normalization
// ---------------------------------------------------------------------------

/**
 * Map of backend scoring method names to the frontend's discriminated union methods.
 * Frontend PuzzleScoringConfig supports:
 *   sum_property | count | inverse_count | binary | ratio | weighted_sum
 */
const SCORING_METHOD_MAP: Record<string, PuzzleScoringConfig['method']> = {
  // Direct matches
  sum_property: 'sum_property',
  count: 'count',
  inverse_count: 'inverse_count',
  binary: 'binary',
  ratio: 'ratio',
  weighted_sum: 'weighted_sum',
  // Backend variants
  optimality_ratio: 'ratio',
  proportion: 'ratio',
  total_value: 'sum_property',
  item_count: 'count',
  pass_fail: 'binary',
  all_or_nothing: 'binary',
};

/**
 * Normalize a raw scoring config object from the backend into the frontend
 * PuzzleScoringConfig discriminated union shape.
 */
export function normalizeScoringConfig(raw: unknown): PuzzleScoringConfig {
  if (!raw || typeof raw !== 'object') {
    return { method: 'ratio', total: 100 };
  }

  const obj = raw as Record<string, unknown>;
  const rawMethod = String(obj.method || 'ratio').toLowerCase().trim();
  const mappedMethod = SCORING_METHOD_MAP[rawMethod] || 'ratio';

  // Flatten params dict
  const params = obj.params && typeof obj.params === 'object'
    ? (obj.params as Record<string, unknown>)
    : {};
  const flat: Record<string, unknown> = { ...params };
  for (const [key, value] of Object.entries(obj)) {
    if (key !== 'params' && key !== 'method') {
      flat[key] = value;
    }
  }

  switch (mappedMethod) {
    case 'sum_property': {
      const property = asString(flat.property) || asString(flat.prop) || 'value';
      return { method: 'sum_property', property };
    }

    case 'count':
      return { method: 'count' };

    case 'inverse_count': {
      const numerator = asNumber(flat.numerator) ?? asNumber(flat.total) ?? 100;
      return { method: 'inverse_count', numerator };
    }

    case 'binary': {
      const successValue = asNumber(flat.successValue) ?? asNumber(flat.success_value) ?? asNumber(flat.maxPoints) ?? 400;
      return { method: 'binary', successValue };
    }

    case 'ratio': {
      const total = asNumber(flat.total) ?? asNumber(flat.optimalValue) ?? asNumber(flat.optimal_value) ?? asNumber(flat.maxPoints) ?? 100;
      return { method: 'ratio', total };
    }

    case 'weighted_sum': {
      const valueProperty = asString(flat.valueProperty) || asString(flat.value_property) || 'value';
      const weightProperty = asString(flat.weightProperty) || asString(flat.weight_property) || 'weight';
      return { method: 'weighted_sum', valueProperty, weightProperty };
    }

    default:
      return { method: 'ratio', total: 100 };
  }
}

// ---------------------------------------------------------------------------
// Item normalization (name -> label, ensure required fields)
// ---------------------------------------------------------------------------

/**
 * Normalize an array of raw items, ensuring each has the required SelectableItem fields.
 * Handles backend "name" field mapping to frontend "label".
 */
export function normalizeItems(items: unknown): SelectableItem[] {
  if (!Array.isArray(items)) return [];
  return items.map((item, i) => {
    if (!item || typeof item !== 'object') {
      return { id: `item_${i}`, label: `Item ${i + 1}`, properties: {} };
    }
    const obj = item as Record<string, unknown>;
    return {
      ...obj,
      id: asString(obj.id) || `item_${i}`,
      label: asString(obj.label) || asString(obj.name) || `Item ${i + 1}`,
      icon: asStringOptional(obj.icon) ?? '',
      properties: (obj.properties && typeof obj.properties === 'object'
        ? obj.properties
        : {}) as Record<string, number | string>,
    };
  });
}

// ---------------------------------------------------------------------------
// Board config normalization (normalizes items within board configs)
// ---------------------------------------------------------------------------

/**
 * Normalize item-level fields within a board config.
 * Applies name->label mapping and ensures required fields for board types
 * that contain item arrays (item_selection, sequence_building).
 */
export function normalizeBoardConfig(config: unknown): BoardConfig {
  if (!config || typeof config !== 'object') {
    // Fallback to an empty item_selection board
    return { boardType: 'item_selection', items: [] };
  }

  const cfg = config as Record<string, unknown>;
  const boardType = cfg.boardType as string;

  if (boardType === 'item_selection') {
    return {
      ...cfg,
      boardType: 'item_selection',
      items: normalizeItems(cfg.items),
    } as BoardConfig;
  }

  if (boardType === 'sequence_building') {
    // sequence_building items have {id, label, icon?} - normalize name->label
    const rawItems = Array.isArray(cfg.items) ? cfg.items : [];
    const items = rawItems.map((item: Record<string, unknown>, i: number) => ({
      id: asString(item?.id) || `item_${i}`,
      label: asString(item?.label) || asString(item?.name) || `Item ${i + 1}`,
      icon: asStringOptional(item?.icon),
    }));
    return { ...cfg, boardType: 'sequence_building', items } as BoardConfig;
  }

  if (boardType === 'multiset_building') {
    // multiset pool items have {id, value, label?, icon?} - normalize name->label
    const rawPool = Array.isArray(cfg.pool) ? cfg.pool : [];
    const pool = rawPool.map((item: Record<string, unknown>, i: number) => ({
      ...item,
      id: asString(item?.id) || `pool_${i}`,
      value: item?.value ?? i,
      label: asString(item?.label) || asString(item?.name),
      icon: asStringOptional(item?.icon),
    }));
    return { ...cfg, boardType: 'multiset_building', pool } as BoardConfig;
  }

  if (boardType === 'graph_interaction') {
    // graph nodes have {id, label, x, y} - normalize name->label
    const rawNodes = Array.isArray(cfg.nodes) ? cfg.nodes : [];
    const nodes = rawNodes.map((node: Record<string, unknown>, i: number) => ({
      ...node,
      id: asString(node?.id) || `node_${i}`,
      label: asString(node?.label) || asString(node?.name) || `Node ${i + 1}`,
      x: asNumber(node?.x) ?? 0,
      y: asNumber(node?.y) ?? 0,
    }));
    return { ...cfg, boardType: 'graph_interaction', nodes } as BoardConfig;
  }

  if (boardType === 'value_assignment') {
    // slots have {id, label, neighbors?} - normalize name->label
    const rawSlots = Array.isArray(cfg.slots) ? cfg.slots : [];
    const slots = rawSlots.map((slot: Record<string, unknown>, i: number) => ({
      ...slot,
      id: asString(slot?.id) || `slot_${i}`,
      label: asString(slot?.label) || asString(slot?.name) || `Slot ${i + 1}`,
    }));
    return { ...cfg, boardType: 'value_assignment', slots } as BoardConfig;
  }

  // grid_placement and any other types - pass through as-is
  return cfg as unknown as BoardConfig;
}

// ---------------------------------------------------------------------------
// Full blueprint normalization (entry point)
// ---------------------------------------------------------------------------

/**
 * Apply all normalization passes to a GenericConstraintPuzzleBlueprint.
 * This is the main entry point called from ConstraintPuzzleGame.tsx.
 *
 * Handles both old format (params dict, name fields) and new format (flat fields)
 * since existing blueprints may use either.
 */
export function normalizeBlueprint(
  bp: GenericConstraintPuzzleBlueprint,
): GenericConstraintPuzzleBlueprint {
  return {
    ...bp,
    constraints: normalizeConstraints(bp.constraints),
    scoringConfig: normalizeScoringConfig(bp.scoringConfig),
    boardConfig: normalizeBoardConfig(bp.boardConfig),
    showConstraintsVisually: bp.showConstraintsVisually ?? true,
    allowUndo: bp.allowUndo ?? true,
    hints: bp.hints ?? ['Think about the constraints.', 'Try a different approach.', 'Consider the optimal strategy.'],
  };
}

// ---------------------------------------------------------------------------
// Type coercion helpers
// ---------------------------------------------------------------------------

function asString(v: unknown): string {
  if (typeof v === 'string') return v;
  if (typeof v === 'number') return String(v);
  return '';
}

function asStringOptional(v: unknown): string | undefined {
  if (typeof v === 'string') return v;
  return undefined;
}

function asNumber(v: unknown): number | undefined {
  if (typeof v === 'number' && !isNaN(v)) return v;
  if (typeof v === 'string') {
    const n = Number(v);
    if (!isNaN(n)) return n;
  }
  return undefined;
}

function asNumberOptional(v: unknown): number | undefined {
  return asNumber(v);
}

function asBoolean(v: unknown): boolean | undefined {
  if (typeof v === 'boolean') return v;
  return undefined;
}
