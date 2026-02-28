"""Content Validator — validates per-mechanic content from the content generator.

Strict enforcement: item counts must match expected_item_count exactly.
All zone_label references must be in the mechanic's zone_labels_used.
"""

from typing import Any

from app.v4.schemas.game_plan import MechanicPlan
from app.v4.schemas.validation import ValidationIssue, ValidationResult
from app.v4.helpers.utils import normalize_label_text


def validate_mechanic_content(
    content: dict[str, Any],
    mechanic_plan: MechanicPlan,
) -> ValidationResult:
    """Validate content output against the mechanic plan.

    Dispatches to per-mechanic validation based on mechanic_type.
    """
    issues: list[ValidationIssue] = []
    mtype = mechanic_plan.mechanic_type
    mid = mechanic_plan.mechanic_id
    canonical = set(normalize_label_text(l) for l in mechanic_plan.zone_labels_used)

    validator = _VALIDATORS.get(mtype)
    if validator is None:
        issues.append(ValidationIssue(
            severity="error",
            message=f"No content validator for mechanic type: {mtype}",
            mechanic_id=mid,
        ))
        return ValidationResult(passed=False, score=0.0, issues=issues)

    validator(content, mechanic_plan, canonical, issues)

    has_errors = any(i.severity == "error" for i in issues)
    return ValidationResult(passed=not has_errors, score=0.0 if has_errors else 1.0, issues=issues)


def _check_item_count(
    items: list, expected: int, field_name: str,
    mid: str, issues: list[ValidationIssue],
) -> None:
    """Strict: item count must exactly match expected_item_count."""
    if len(items) != expected:
        issues.append(ValidationIssue(
            severity="error",
            message=f"{field_name}: expected {expected} items, got {len(items)}",
            field_path=field_name,
            mechanic_id=mid,
        ))


def _check_label_in_canonical(
    label: str, canonical: set[str], field_path: str,
    mid: str, issues: list[ValidationIssue],
) -> None:
    """Check that a label reference exists in canonical zone_labels."""
    if normalize_label_text(label) not in canonical:
        issues.append(ValidationIssue(
            severity="error",
            message=f"{field_path}: label '{label}' not in zone_labels_used",
            field_path=field_path,
            mechanic_id=mid,
        ))


# ── Per-mechanic validators ─────────────────────────────────────

def _validate_drag_drop(
    content: dict, plan: MechanicPlan, canonical: set[str],
    issues: list[ValidationIssue],
) -> None:
    mid = plan.mechanic_id
    labels = content.get("labels", [])

    if not labels:
        issues.append(ValidationIssue(severity="error", message="labels is empty", mechanic_id=mid))
        return

    _check_item_count(labels, plan.expected_item_count, "labels", mid, issues)

    # No duplicates
    seen: set[str] = set()
    for i, label in enumerate(labels):
        norm = normalize_label_text(label)
        if norm in seen:
            issues.append(ValidationIssue(
                severity="error", message=f"Duplicate label: '{label}'",
                field_path=f"labels[{i}]", mechanic_id=mid,
            ))
        seen.add(norm)
        _check_label_in_canonical(label, canonical, f"labels[{i}]", mid, issues)


def _validate_click_to_identify(
    content: dict, plan: MechanicPlan, canonical: set[str],
    issues: list[ValidationIssue],
) -> None:
    mid = plan.mechanic_id
    prompts = content.get("prompts", [])

    if not prompts:
        issues.append(ValidationIssue(severity="error", message="prompts is empty", mechanic_id=mid))
        return

    _check_item_count(prompts, plan.expected_item_count, "prompts", mid, issues)

    for i, prompt in enumerate(prompts):
        if not prompt.get("text"):
            issues.append(ValidationIssue(
                severity="error", message=f"prompts[{i}].text is empty",
                field_path=f"prompts[{i}].text", mechanic_id=mid,
            ))
        target = prompt.get("target_label", "")
        if target:
            _check_label_in_canonical(target, canonical, f"prompts[{i}].target_label", mid, issues)
        else:
            issues.append(ValidationIssue(
                severity="error", message=f"prompts[{i}].target_label is empty",
                field_path=f"prompts[{i}].target_label", mechanic_id=mid,
            ))
        if not prompt.get("explanation"):
            issues.append(ValidationIssue(
                severity="warning", message=f"prompts[{i}].explanation is empty",
                field_path=f"prompts[{i}].explanation", mechanic_id=mid,
            ))


def _validate_trace_path(
    content: dict, plan: MechanicPlan, canonical: set[str],
    issues: list[ValidationIssue],
) -> None:
    mid = plan.mechanic_id
    paths = content.get("paths", [])

    if not paths:
        issues.append(ValidationIssue(severity="error", message="paths is empty", mechanic_id=mid))
        return

    _check_item_count(paths, plan.expected_item_count, "paths", mid, issues)

    for i, path in enumerate(paths):
        waypoints = path.get("waypoints", [])
        if len(waypoints) < 2:
            issues.append(ValidationIssue(
                severity="error", message=f"paths[{i}]: needs >= 2 waypoints, got {len(waypoints)}",
                field_path=f"paths[{i}].waypoints", mechanic_id=mid,
            ))
        for wi, wp in enumerate(waypoints):
            label = wp.get("label", "")
            if label:
                _check_label_in_canonical(label, canonical, f"paths[{i}].waypoints[{wi}].label", mid, issues)

        # Check waypoints are ordered
        orders = [wp.get("order", 0) for wp in waypoints]
        if orders != sorted(orders):
            issues.append(ValidationIssue(
                severity="warning", message=f"paths[{i}]: waypoints not in order",
                field_path=f"paths[{i}].waypoints", mechanic_id=mid,
            ))


def _validate_sequencing(
    content: dict, plan: MechanicPlan, canonical: set[str],
    issues: list[ValidationIssue],
) -> None:
    mid = plan.mechanic_id
    items = content.get("items", [])
    correct_order = content.get("correct_order", [])

    if not items:
        issues.append(ValidationIssue(severity="error", message="items is empty", mechanic_id=mid))
        return

    _check_item_count(items, plan.expected_item_count, "items", mid, issues)

    item_ids = {item.get("id") for item in items}

    # correct_order must reference all item IDs
    order_set = set(correct_order)
    if order_set != item_ids:
        missing = item_ids - order_set
        extra = order_set - item_ids
        msg_parts = []
        if missing:
            msg_parts.append(f"missing from correct_order: {missing}")
        if extra:
            msg_parts.append(f"extra in correct_order: {extra}")
        issues.append(ValidationIssue(
            severity="error", message=f"correct_order mismatch: {'; '.join(msg_parts)}",
            field_path="correct_order", mechanic_id=mid,
        ))

    # No duplicate IDs
    if len(item_ids) != len(items):
        issues.append(ValidationIssue(
            severity="error", message="Duplicate item IDs",
            field_path="items", mechanic_id=mid,
        ))


def _validate_sorting(
    content: dict, plan: MechanicPlan, canonical: set[str],
    issues: list[ValidationIssue],
) -> None:
    mid = plan.mechanic_id
    categories = content.get("categories", [])
    items = content.get("items", [])

    if len(categories) < 2:
        issues.append(ValidationIssue(
            severity="error", message=f"Need >= 2 categories, got {len(categories)}",
            field_path="categories", mechanic_id=mid,
        ))

    if not items:
        issues.append(ValidationIssue(severity="error", message="items is empty", mechanic_id=mid))
        return

    _check_item_count(items, plan.expected_item_count, "items", mid, issues)

    cat_ids = {c.get("id") for c in categories}
    used_cat_ids: set[str] = set()

    for i, item in enumerate(items):
        cat_id = item.get("correctCategoryId", "")
        if cat_id not in cat_ids:
            issues.append(ValidationIssue(
                severity="error",
                message=f"items[{i}].correctCategoryId '{cat_id}' not in categories",
                field_path=f"items[{i}].correctCategoryId", mechanic_id=mid,
            ))
        else:
            used_cat_ids.add(cat_id)

    # Check for orphan categories (no items assigned)
    orphan_cats = cat_ids - used_cat_ids
    if orphan_cats:
        issues.append(ValidationIssue(
            severity="warning",
            message=f"Orphan categories with no items: {orphan_cats}",
            field_path="categories", mechanic_id=mid,
        ))


def _validate_memory_match(
    content: dict, plan: MechanicPlan, canonical: set[str],
    issues: list[ValidationIssue],
) -> None:
    mid = plan.mechanic_id
    pairs = content.get("pairs", [])

    if len(pairs) < 3:
        issues.append(ValidationIssue(
            severity="error", message=f"Need >= 3 pairs, got {len(pairs)}",
            field_path="pairs", mechanic_id=mid,
        ))
        return

    _check_item_count(pairs, plan.expected_item_count, "pairs", mid, issues)

    seen_ids: set[str] = set()
    for i, pair in enumerate(pairs):
        pid = pair.get("id", "")
        if pid in seen_ids:
            issues.append(ValidationIssue(
                severity="error", message=f"Duplicate pair ID: '{pid}'",
                field_path=f"pairs[{i}].id", mechanic_id=mid,
            ))
        seen_ids.add(pid)

        if not pair.get("front"):
            issues.append(ValidationIssue(
                severity="error", message=f"pairs[{i}].front is empty",
                field_path=f"pairs[{i}].front", mechanic_id=mid,
            ))
        if not pair.get("back"):
            issues.append(ValidationIssue(
                severity="error", message=f"pairs[{i}].back is empty",
                field_path=f"pairs[{i}].back", mechanic_id=mid,
            ))


def _validate_branching(
    content: dict, plan: MechanicPlan, canonical: set[str],
    issues: list[ValidationIssue],
) -> None:
    mid = plan.mechanic_id
    nodes = content.get("nodes", [])
    start_id = content.get("startNodeId", "")

    if len(nodes) < 2:
        issues.append(ValidationIssue(
            severity="error", message=f"Need >= 2 nodes, got {len(nodes)}",
            field_path="nodes", mechanic_id=mid,
        ))
        return

    node_ids = {n.get("id") for n in nodes}
    node_map = {n.get("id"): n for n in nodes}

    # startNodeId exists
    if start_id not in node_ids:
        issues.append(ValidationIssue(
            severity="error", message=f"startNodeId '{start_id}' not found in nodes",
            field_path="startNodeId", mechanic_id=mid,
        ))

    # Non-end nodes must have options; all nextNodeId must be valid
    end_nodes: set[str] = set()
    for i, node in enumerate(nodes):
        nid = node.get("id", "")
        is_end = node.get("isEndNode", False)
        options = node.get("options", [])

        if is_end:
            end_nodes.add(nid)
            continue

        if not options:
            issues.append(ValidationIssue(
                severity="error",
                message=f"nodes[{i}] ('{nid}'): non-end node must have options",
                field_path=f"nodes[{i}].options", mechanic_id=mid,
            ))
            continue

        for oi, opt in enumerate(options):
            next_id = opt.get("nextNodeId")
            if next_id is not None and next_id not in node_ids:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"nodes[{i}].options[{oi}].nextNodeId '{next_id}' not found",
                    field_path=f"nodes[{i}].options[{oi}].nextNodeId", mechanic_id=mid,
                ))

    # All end nodes reachable from start (DFS)
    if start_id in node_ids and end_nodes:
        reachable = _reachable_nodes(start_id, node_map)
        unreachable_ends = end_nodes - reachable
        if unreachable_ends:
            issues.append(ValidationIssue(
                severity="error",
                message=f"End nodes unreachable from start: {unreachable_ends}",
                field_path="nodes", mechanic_id=mid,
            ))

        # Check for orphan nodes (not reachable from start)
        orphans = node_ids - reachable
        if orphans:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"Orphan nodes not reachable from start: {orphans}",
                field_path="nodes", mechanic_id=mid,
            ))


def _reachable_nodes(start_id: str, node_map: dict[str, dict]) -> set[str]:
    """BFS/DFS to find all reachable nodes from start."""
    visited: set[str] = set()
    stack = [start_id]
    while stack:
        nid = stack.pop()
        if nid in visited or nid not in node_map:
            continue
        visited.add(nid)
        node = node_map[nid]
        for opt in node.get("options", []):
            next_id = opt.get("nextNodeId")
            if next_id and next_id not in visited:
                stack.append(next_id)
    return visited


def _validate_description_matching(
    content: dict, plan: MechanicPlan, canonical: set[str],
    issues: list[ValidationIssue],
) -> None:
    mid = plan.mechanic_id
    descriptions = content.get("descriptions", {})

    if not descriptions:
        issues.append(ValidationIssue(
            severity="error", message="descriptions is empty",
            field_path="descriptions", mechanic_id=mid,
        ))
        return

    _check_item_count(list(descriptions), plan.expected_item_count, "descriptions", mid, issues)

    # All keys must be in zone_labels
    for key in descriptions:
        _check_label_in_canonical(key, canonical, f"descriptions['{key}']", mid, issues)

    # Descriptions should be distinct
    desc_values = list(descriptions.values())
    if len(set(desc_values)) != len(desc_values):
        issues.append(ValidationIssue(
            severity="warning",
            message="Some descriptions are identical — may confuse students",
            field_path="descriptions", mechanic_id=mid,
        ))


# ── Validator dispatch ───────────────────────────────────────────

_VALIDATORS = {
    "drag_drop": _validate_drag_drop,
    "click_to_identify": _validate_click_to_identify,
    "trace_path": _validate_trace_path,
    "sequencing": _validate_sequencing,
    "sorting_categories": _validate_sorting,
    "memory_match": _validate_memory_match,
    "branching_scenario": _validate_branching,
    "description_matching": _validate_description_matching,
}
