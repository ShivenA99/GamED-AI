// ============================================================================
// Constraint Evaluator — Pure function evaluating state against constraints
// ============================================================================

import {
  Constraint,
  ConstraintResult,
  GenericPuzzleState,
  BoardConfig,
  ItemSelectionBoardConfig,
  GridPlacementBoardConfig,
  ValueAssignmentBoardConfig,
} from './constraintPuzzleTypes';

/**
 * Evaluate all constraints against the current puzzle state.
 * Returns an array of ConstraintResult with pass/fail + messages.
 */
export function evaluateConstraints(
  constraints: Constraint[],
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult[] {
  return constraints.map((c) => evaluateOne(c, state, config));
}

/**
 * Returns true if ALL constraints are satisfied.
 */
export function allConstraintsSatisfied(results: ConstraintResult[]): boolean {
  return results.every((r) => r.satisfied);
}

// ---------------------------------------------------------------------------
// Individual constraint evaluators
// ---------------------------------------------------------------------------

function evaluateOne(
  constraint: Constraint,
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult {
  switch (constraint.type) {
    case 'capacity':
      return evalCapacity(constraint, state, config);
    case 'exact_target':
      return evalExactTarget(constraint, state, config);
    case 'no_overlap':
      return evalNoOverlap(constraint, state, config);
    case 'no_conflict':
      return evalNoConflict(constraint, state, config);
    case 'count_exact':
      return evalCountExact(constraint, state, config);
    case 'count_range':
      return evalCountRange(constraint, state, config);
    case 'all_different':
      return evalAllDifferent(constraint, state, config);
    case 'all_assigned':
      return evalAllAssigned(constraint, state, config);
    case 'connected':
      return evalConnected(constraint, state, config);
    default:
      return { constraint, satisfied: false, message: 'Unknown constraint type' };
  }
}

// ---------------------------------------------------------------------------
// capacity: sum of a property on selected items must not exceed max
// ---------------------------------------------------------------------------

function evalCapacity(
  c: Extract<Constraint, { type: 'capacity' }>,
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult {
  if (config.boardType !== 'item_selection') {
    return { constraint: c, satisfied: true, message: 'N/A' };
  }
  const items = (config as ItemSelectionBoardConfig).items;
  const selected = items.filter((it) => state.selectedIds.includes(it.id));
  const total = selected.reduce(
    (sum, it) => sum + (Number(it.properties[c.property]) || 0),
    0,
  );
  const satisfied = total <= c.max;
  const label = c.label ?? c.property;
  return {
    constraint: c,
    satisfied,
    message: satisfied
      ? `${label}: ${total}/${c.max}`
      : `${label} exceeds limit: ${total}/${c.max}`,
    currentValue: total,
    targetValue: c.max,
  };
}

// ---------------------------------------------------------------------------
// exact_target: sum of property (or bag values) must equal target
// ---------------------------------------------------------------------------

function evalExactTarget(
  c: Extract<Constraint, { type: 'exact_target' }>,
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult {
  let total: number;
  if (config.boardType === 'multiset_building') {
    total = state.bag.reduce((sum: number, v) => sum + Number(v), 0);
  } else if (config.boardType === 'item_selection' && c.property) {
    const items = (config as ItemSelectionBoardConfig).items;
    const selected = items.filter((it) => state.selectedIds.includes(it.id));
    total = selected.reduce(
      (sum, it) => sum + (Number(it.properties[c.property!]) || 0),
      0,
    );
  } else {
    total = 0;
  }
  const satisfied = total === c.target;
  return {
    constraint: c,
    satisfied,
    message: satisfied
      ? `Target reached: ${total}/${c.target}`
      : `Progress: ${total}/${c.target}`,
    currentValue: total,
    targetValue: c.target,
  };
}

// ---------------------------------------------------------------------------
// no_overlap: selected items must not have overlapping time ranges
// ---------------------------------------------------------------------------

function evalNoOverlap(
  c: Extract<Constraint, { type: 'no_overlap' }>,
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult {
  if (config.boardType !== 'item_selection') {
    return { constraint: c, satisfied: true, message: 'N/A' };
  }
  const items = (config as ItemSelectionBoardConfig).items;
  const selected = items
    .filter((it) => state.selectedIds.includes(it.id))
    .sort(
      (a, b) =>
        Number(a.properties[c.startProperty]) -
        Number(b.properties[c.startProperty]),
    );

  for (let i = 1; i < selected.length; i++) {
    const prevEnd = Number(selected[i - 1].properties[c.endProperty]);
    const currStart = Number(selected[i].properties[c.startProperty]);
    if (currStart < prevEnd) {
      return {
        constraint: c,
        satisfied: false,
        message: `Overlap: "${selected[i - 1].label}" and "${selected[i].label}"`,
      };
    }
  }
  return { constraint: c, satisfied: true, message: 'No overlaps' };
}

// ---------------------------------------------------------------------------
// no_conflict: grid placements must not conflict
// ---------------------------------------------------------------------------

function evalNoConflict(
  c: Extract<Constraint, { type: 'no_conflict' }>,
  state: GenericPuzzleState,
  _config: BoardConfig,
): ConstraintResult {
  const positions = state.placements;
  if (positions.length <= 1) {
    return { constraint: c, satisfied: true, message: 'No conflicts' };
  }
  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      const a = positions[i];
      const b = positions[j];
      if (hasConflict(a, b, c.conflictRule)) {
        return {
          constraint: c,
          satisfied: false,
          message: `Conflict at (${a.row},${a.col}) and (${b.row},${b.col})`,
        };
      }
    }
  }
  return { constraint: c, satisfied: true, message: 'No conflicts' };
}

function hasConflict(
  a: { row: number; col: number },
  b: { row: number; col: number },
  rule: 'row_col_diagonal' | 'row_col' | 'adjacent',
): boolean {
  switch (rule) {
    case 'row_col_diagonal':
      return (
        a.row === b.row ||
        a.col === b.col ||
        Math.abs(a.row - b.row) === Math.abs(a.col - b.col)
      );
    case 'row_col':
      return a.row === b.row || a.col === b.col;
    case 'adjacent':
      return (
        Math.abs(a.row - b.row) <= 1 &&
        Math.abs(a.col - b.col) <= 1 &&
        !(a.row === b.row && a.col === b.col)
      );
  }
}

// ---------------------------------------------------------------------------
// count_exact: exactly N items/placements/etc
// ---------------------------------------------------------------------------

function evalCountExact(
  c: Extract<Constraint, { type: 'count_exact' }>,
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult {
  const count = getSelectionCount(state, config);
  const satisfied = count === c.count;
  const label = c.label ?? 'items';
  return {
    constraint: c,
    satisfied,
    message: satisfied
      ? `${count}/${c.count} ${label} placed`
      : `Need exactly ${c.count} ${label} (have ${count})`,
    currentValue: count,
    targetValue: c.count,
  };
}

// ---------------------------------------------------------------------------
// count_range: between min and max items
// ---------------------------------------------------------------------------

function evalCountRange(
  c: Extract<Constraint, { type: 'count_range' }>,
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult {
  const count = getSelectionCount(state, config);
  const min = c.min ?? 0;
  const max = c.max ?? Infinity;
  const satisfied = count >= min && count <= max;
  return {
    constraint: c,
    satisfied,
    message: satisfied
      ? `${count} selected (valid)`
      : `Need ${min}${max < Infinity ? `-${max}` : '+'} items (have ${count})`,
    currentValue: count,
  };
}

// ---------------------------------------------------------------------------
// all_different: all assigned values must be different within scope
// ---------------------------------------------------------------------------

function evalAllDifferent(
  c: Extract<Constraint, { type: 'all_different' }>,
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult {
  const scope = c.scope ?? 'all';

  if (config.boardType === 'value_assignment') {
    const cfg = config as ValueAssignmentBoardConfig;
    const entries = Object.entries(state.assignments).filter(
      ([, v]) => v != null,
    );

    if (scope === 'neighbors') {
      for (const slot of cfg.slots) {
        const myVal = state.assignments[slot.id];
        if (myVal == null) continue;
        for (const nId of slot.neighbors ?? []) {
          const nVal = state.assignments[nId];
          if (nVal != null && nVal === myVal) {
            return {
              constraint: c,
              satisfied: false,
              message: `"${slot.label}" and neighbor share value "${myVal}"`,
            };
          }
        }
      }
      return { constraint: c, satisfied: true, message: 'All neighbors different' };
    }

    // scope 'all'
    const values = entries.map(([, v]) => v);
    const unique = new Set(values);
    const satisfied = unique.size === values.length;
    return {
      constraint: c,
      satisfied,
      message: satisfied ? 'All values unique' : 'Duplicate values found',
    };
  }

  return { constraint: c, satisfied: true, message: 'N/A' };
}

// ---------------------------------------------------------------------------
// all_assigned: every slot must have a value
// ---------------------------------------------------------------------------

function evalAllAssigned(
  c: Extract<Constraint, { type: 'all_assigned' }>,
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult {
  if (config.boardType === 'value_assignment') {
    const cfg = config as ValueAssignmentBoardConfig;
    const assigned = Object.values(state.assignments).filter((v) => v != null).length;
    const total = cfg.slots.length;
    const satisfied = assigned === total;
    return {
      constraint: c,
      satisfied,
      message: satisfied
        ? 'All slots assigned'
        : `${assigned}/${total} slots assigned`,
      currentValue: assigned,
      targetValue: total,
    };
  }
  return { constraint: c, satisfied: true, message: 'N/A' };
}

// ---------------------------------------------------------------------------
// connected: selected edges/nodes form a connected subgraph
// ---------------------------------------------------------------------------

function evalConnected(
  c: Extract<Constraint, { type: 'connected' }>,
  state: GenericPuzzleState,
  config: BoardConfig,
): ConstraintResult {
  if (config.boardType !== 'graph_interaction') {
    return { constraint: c, satisfied: true, message: 'N/A' };
  }
  const { edges, nodes } = config;

  // Build adjacency from selected edges
  const selectedEdges = edges.filter((e) => state.selectedEdgeIds.includes(e.id));
  if (selectedEdges.length === 0) {
    return {
      constraint: c,
      satisfied: false,
      message: 'No edges selected',
    };
  }

  const touchedNodes = new Set<string>();
  const adj = new Map<string, Set<string>>();
  for (const e of selectedEdges) {
    touchedNodes.add(e.from);
    touchedNodes.add(e.to);
    if (!adj.has(e.from)) adj.set(e.from, new Set());
    if (!adj.has(e.to)) adj.set(e.to, new Set());
    adj.get(e.from)!.add(e.to);
    adj.get(e.to)!.add(e.from);
  }

  // Also include selected node IDs
  for (const nId of state.selectedIds) {
    touchedNodes.add(nId);
  }

  // BFS from first touched node
  const allTouched = Array.from(touchedNodes);
  if (allTouched.length === 0) {
    return { constraint: c, satisfied: true, message: 'Connected' };
  }

  const visited = new Set<string>();
  const queue = [allTouched[0]];
  visited.add(allTouched[0]);
  while (queue.length > 0) {
    const cur = queue.shift()!;
    for (const nb of adj.get(cur) ?? []) {
      if (!visited.has(nb)) {
        visited.add(nb);
        queue.push(nb);
      }
    }
  }

  // Check if all nodes in the graph are connected (for MST-like puzzles)
  const targetNodes = nodes.map((n) => n.id);
  const allConnected = targetNodes.every((n) => visited.has(n));

  return {
    constraint: c,
    satisfied: allConnected,
    message: allConnected
      ? 'All nodes connected'
      : `${visited.size}/${targetNodes.length} nodes reachable`,
    currentValue: visited.size,
    targetValue: targetNodes.length,
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getSelectionCount(
  state: GenericPuzzleState,
  config: BoardConfig,
): number {
  switch (config.boardType) {
    case 'item_selection':
      return state.selectedIds.length;
    case 'grid_placement':
      return state.placements.length;
    case 'multiset_building':
      return state.bag.length;
    case 'graph_interaction':
      return state.selectedIds.length + state.selectedEdgeIds.length;
    case 'value_assignment':
      return Object.values(state.assignments).filter((v) => v != null).length;
    case 'sequence_building':
      return state.sequence.length;
  }
}
