"""Game Plan Validator — validates GamePlan output from the game designer.

All checks are deterministic. Also computes max_score fields that the
LLM leaves at 0.
"""

from typing import Any

from app.v4.contracts import SUPPORTED_MECHANICS, CONTENT_ONLY_MECHANICS, ZONE_BASED_MECHANICS
from app.v4.helpers.scoring import compute_mechanic_score
from app.v4.schemas.game_plan import GamePlan
from app.v4.schemas.validation import ValidationIssue, ValidationResult


def validate_game_plan(plan: GamePlan) -> ValidationResult:
    """Validate a GamePlan and compute score fields.

    Returns ValidationResult. On pass, the plan object is mutated with
    computed max_score, scene_max_score, total_max_score values.
    """
    issues: list[ValidationIssue] = []

    # Basic structure
    if not plan.scenes:
        issues.append(ValidationIssue(severity="error", message="GamePlan must have at least 1 scene"))
        return ValidationResult(passed=False, score=0.0, issues=issues)

    all_labels_set = set(plan.all_zone_labels)

    # Check distractor_labels disjoint from all_zone_labels
    distractor_overlap = set(plan.distractor_labels) & all_labels_set
    if distractor_overlap:
        issues.append(ValidationIssue(
            severity="error",
            message=f"distractor_labels overlap with all_zone_labels: {distractor_overlap}",
            field_path="distractor_labels",
        ))

    for si, scene in enumerate(plan.scenes):
        scene_prefix = f"scenes[{si}]"

        if not scene.mechanics:
            issues.append(ValidationIssue(
                severity="error",
                message=f"{scene_prefix}: must have at least 1 mechanic",
                field_path=f"{scene_prefix}.mechanics",
            ))
            continue

        # Zone labels referential integrity: scene.zone_labels ⊆ all_zone_labels
        scene_labels_set = set(scene.zone_labels)
        orphan_scene_labels = scene_labels_set - all_labels_set
        if orphan_scene_labels:
            issues.append(ValidationIssue(
                severity="error",
                message=f"{scene_prefix}: zone_labels {orphan_scene_labels} not in all_zone_labels",
                field_path=f"{scene_prefix}.zone_labels",
            ))

        has_zone_mechanic = False
        has_content_mechanic = False
        scene_mechanic_ids: set[str] = set()
        scene_mechanic_types: list[str] = []

        for mi, mech in enumerate(scene.mechanics):
            mech_prefix = f"{scene_prefix}.mechanics[{mi}]"

            # Mechanic type check
            if mech.mechanic_type not in SUPPORTED_MECHANICS:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"{mech_prefix}: unsupported mechanic_type '{mech.mechanic_type}'",
                    field_path=f"{mech_prefix}.mechanic_type",
                    mechanic_id=mech.mechanic_id,
                ))
                continue

            scene_mechanic_ids.add(mech.mechanic_id)
            scene_mechanic_types.append(mech.mechanic_type)

            is_zone_based = mech.mechanic_type in ZONE_BASED_MECHANICS
            is_content_only = mech.mechanic_type in CONTENT_ONLY_MECHANICS

            if is_zone_based:
                has_zone_mechanic = True
            if is_content_only:
                has_content_mechanic = True

            # Zone-based mechanics must have zone_labels_used
            if is_zone_based and not mech.zone_labels_used:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"{mech_prefix}: zone-based mechanic '{mech.mechanic_type}' must have zone_labels_used",
                    field_path=f"{mech_prefix}.zone_labels_used",
                    mechanic_id=mech.mechanic_id,
                ))

            # Content-only mechanics must have empty zone_labels_used
            if is_content_only and mech.zone_labels_used:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"{mech_prefix}: content-only mechanic '{mech.mechanic_type}' must have empty zone_labels_used",
                    field_path=f"{mech_prefix}.zone_labels_used",
                    mechanic_id=mech.mechanic_id,
                ))

            # mechanic.zone_labels_used ⊆ scene.zone_labels
            mech_labels_set = set(mech.zone_labels_used)
            orphan_mech_labels = mech_labels_set - scene_labels_set
            if orphan_mech_labels:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"{mech_prefix}: zone_labels_used {orphan_mech_labels} not in scene zone_labels",
                    field_path=f"{mech_prefix}.zone_labels_used",
                    mechanic_id=mech.mechanic_id,
                ))

            # Creative design completeness warnings
            cd = mech.creative_design
            if cd:
                if mech.mechanic_type == "sequencing" and not cd.sequence_topic:
                    issues.append(ValidationIssue(
                        severity="warning",
                        message=f"{mech_prefix}: sequencing mechanic should have sequence_topic in creative_design",
                        mechanic_id=mech.mechanic_id,
                    ))
                if mech.mechanic_type == "branching_scenario" and not cd.narrative_premise:
                    issues.append(ValidationIssue(
                        severity="warning",
                        message=f"{mech_prefix}: branching mechanic should have narrative_premise in creative_design",
                        mechanic_id=mech.mechanic_id,
                    ))
                if mech.mechanic_type == "sorting_categories" and not cd.category_names:
                    issues.append(ValidationIssue(
                        severity="warning",
                        message=f"{mech_prefix}: sorting mechanic should have category_names in creative_design",
                        mechanic_id=mech.mechanic_id,
                    ))

            # Compute max_score
            mech.max_score = compute_mechanic_score(mech.expected_item_count, mech.points_per_item)

        # needs_diagram check
        if has_zone_mechanic and not scene.needs_diagram:
            issues.append(ValidationIssue(
                severity="error",
                message=f"{scene_prefix}: has zone-based mechanics but needs_diagram=false",
                field_path=f"{scene_prefix}.needs_diagram",
            ))

        # Content-only scenes: needs_diagram=false is fine
        if not has_zone_mechanic and has_content_mechanic and scene.needs_diagram:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"{scene_prefix}: content-only scene has needs_diagram=true (unnecessary)",
                field_path=f"{scene_prefix}.needs_diagram",
            ))

        # Mechanic connections validation
        for ci, conn in enumerate(scene.mechanic_connections):
            conn_prefix = f"{scene_prefix}.mechanic_connections[{ci}]"
            if conn.from_mechanic_id not in scene_mechanic_ids:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"{conn_prefix}: from_mechanic_id '{conn.from_mechanic_id}' not found in scene",
                    field_path=f"{conn_prefix}.from_mechanic_id",
                ))
            if conn.to_mechanic_id not in scene_mechanic_ids:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"{conn_prefix}: to_mechanic_id '{conn.to_mechanic_id}' not found in scene",
                    field_path=f"{conn_prefix}.to_mechanic_id",
                ))

        # Cycle detection in mechanic_connections via DFS
        if scene.mechanic_connections:
            cycle_error = _detect_cycles(scene.mechanic_connections, scene_mechanic_ids)
            if cycle_error:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"{scene_prefix}: cycle in mechanic_connections: {cycle_error}",
                    field_path=f"{scene_prefix}.mechanic_connections",
                ))

        # Compute scene_max_score
        scene.scene_max_score = sum(m.max_score for m in scene.mechanics)

    # Compute total_max_score
    plan.total_max_score = sum(s.scene_max_score for s in plan.scenes)

    has_errors = any(i.severity == "error" for i in issues)
    score = 0.0 if has_errors else 1.0

    return ValidationResult(passed=not has_errors, score=score, issues=issues)


def _detect_cycles(connections: list, mechanic_ids: set[str]) -> str | None:
    """Detect cycles in mechanic connections using DFS. Returns cycle description or None."""
    adj: dict[str, list[str]] = {mid: [] for mid in mechanic_ids}
    for conn in connections:
        if conn.from_mechanic_id in adj:
            adj[conn.from_mechanic_id].append(conn.to_mechanic_id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {mid: WHITE for mid in mechanic_ids}

    def dfs(node: str) -> str | None:
        color[node] = GRAY
        for neighbor in adj.get(node, []):
            if color.get(neighbor) == GRAY:
                return f"{node} -> {neighbor}"
            if color.get(neighbor) == WHITE:
                result = dfs(neighbor)
                if result:
                    return result
        color[node] = BLACK
        return None

    for mid in mechanic_ids:
        if color[mid] == WHITE:
            result = dfs(mid)
            if result:
                return result
    return None
