"""Blueprint Validator — final gate before output.

Validates the assembled InteractiveDiagramBlueprint dict against
frontend expectations. Content-only scenes are allowed to have empty zones/labels.
"""

from typing import Any

from app.v4.contracts import ZONE_BASED_MECHANICS
from app.v4.schemas.validation import ValidationIssue, ValidationResult


# Valid frontend trigger types
VALID_TRIGGERS = {
    "all_zones_labeled", "path_complete", "identification_complete",
    "sequence_complete", "sorting_complete", "memory_complete",
    "branching_complete", "description_complete", "percentage_complete",
    "time_elapsed", "user_choice", "score_threshold",
    "all_paths_complete", "mode_timer_expired",
}

# mechanic_type -> required root config key
_MECHANIC_CONFIG_MAP = {
    "drag_drop": "dragDropConfig",
    "click_to_identify": "clickToIdentifyConfig",
    "trace_path": "tracePathConfig",
    "sequencing": "sequenceConfig",
    "sorting_categories": "sortingConfig",
    "memory_match": "memoryMatchConfig",
    "branching_scenario": "branchingConfig",
    "description_matching": "descriptionMatchingConfig",
}


def validate_blueprint(blueprint: dict[str, Any]) -> ValidationResult:
    """Validate final blueprint before returning to frontend."""
    issues: list[ValidationIssue] = []

    # templateType
    if blueprint.get("templateType") != "INTERACTIVE_DIAGRAM":
        issues.append(ValidationIssue(
            severity="error",
            message=f"templateType must be 'INTERACTIVE_DIAGRAM', got '{blueprint.get('templateType')}'",
            field_path="templateType",
        ))

    # diagram
    diagram = blueprint.get("diagram")
    if not diagram:
        issues.append(ValidationIssue(severity="error", message="diagram is missing", field_path="diagram"))

    # mechanics
    mechanics = blueprint.get("mechanics", [])
    if not mechanics:
        issues.append(ValidationIssue(severity="error", message="mechanics[] is empty", field_path="mechanics"))

    mechanic_types = {m.get("type") for m in mechanics}
    has_zone_mechanic = bool(mechanic_types & ZONE_BASED_MECHANICS)

    # Zone-based scenes need zones
    if has_zone_mechanic and diagram:
        zones = diagram.get("zones", [])
        if not zones:
            issues.append(ValidationIssue(
                severity="warning",
                message="Zone-based mechanics present but diagram.zones is empty (may be ok if assets failed)",
                field_path="diagram.zones",
            ))

    # Labels need correctZoneId
    labels = blueprint.get("labels", [])
    zone_ids = {z.get("id") for z in (diagram.get("zones", []) if diagram else [])}
    for i, label in enumerate(labels):
        cz = label.get("correctZoneId")
        if cz and zone_ids and cz not in zone_ids:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"labels[{i}].correctZoneId '{cz}' not in diagram.zones",
                field_path=f"labels[{i}].correctZoneId",
            ))

    # Collect all config sources: root + game_sequence scenes
    all_config_sources = [blueprint]
    game_seq = blueprint.get("game_sequence", {})
    if isinstance(game_seq, dict):
        all_config_sources.extend(game_seq.get("scenes", []))

    # Per-mechanic config presence (check root AND game_sequence scenes)
    for mtype in mechanic_types:
        config_key = _MECHANIC_CONFIG_MAP.get(mtype)
        if config_key and not any(config_key in src for src in all_config_sources):
            issues.append(ValidationIssue(
                severity="error",
                message=f"Missing {config_key} for mechanic '{mtype}'",
                field_path=config_key,
            ))

    # identificationPrompts for click_to_identify (check root AND scenes)
    if "click_to_identify" in mechanic_types:
        if not any("identificationPrompts" in src for src in all_config_sources):
            issues.append(ValidationIssue(
                severity="error",
                message="identificationPrompts[] must be at root for click_to_identify",
                field_path="identificationPrompts",
            ))

    # paths for trace_path (check root AND scenes)
    if "trace_path" in mechanic_types:
        if not any("paths" in src for src in all_config_sources):
            issues.append(ValidationIssue(
                severity="error",
                message="paths[] must be at root for trace_path",
                field_path="paths",
            ))

    # Score arithmetic
    total_max = blueprint.get("totalMaxScore", 0)
    scoring = blueprint.get("scoringStrategy", {})
    scoring_max = scoring.get("max_score", 0)
    if total_max != scoring_max:
        issues.append(ValidationIssue(
            severity="warning",
            message=f"totalMaxScore ({total_max}) != scoringStrategy.max_score ({scoring_max})",
            field_path="totalMaxScore",
        ))

    # Mode transitions trigger validation
    for ti, trans in enumerate(blueprint.get("modeTransitions", [])):
        trigger = trans.get("trigger", "")
        if trigger and trigger not in VALID_TRIGGERS:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"modeTransitions[{ti}].trigger '{trigger}' not in known triggers",
                field_path=f"modeTransitions[{ti}].trigger",
            ))

    # animationCues
    if "animationCues" not in blueprint:
        issues.append(ValidationIssue(
            severity="warning", message="animationCues missing",
            field_path="animationCues",
        ))

    # Branching graph connectivity
    if "branchingConfig" in blueprint:
        _validate_branching_config(blueprint["branchingConfig"], issues)

    # Sorting category references
    if "sortingConfig" in blueprint:
        _validate_sorting_config(blueprint["sortingConfig"], issues)

    # Memory pair uniqueness
    if "memoryMatchConfig" in blueprint:
        _validate_memory_config(blueprint["memoryMatchConfig"], issues)

    has_errors = any(i.severity == "error" for i in issues)
    return ValidationResult(passed=not has_errors, score=0.0 if has_errors else 1.0, issues=issues)


def _validate_branching_config(config: dict[str, Any], issues: list[ValidationIssue]) -> None:
    """Check branching graph connectivity."""
    nodes = config.get("nodes", [])
    start_id = config.get("startNodeId", "")
    if not nodes or not start_id:
        return

    node_map = {n.get("id"): n for n in nodes}
    if start_id not in node_map:
        issues.append(ValidationIssue(
            severity="error",
            message=f"branchingConfig.startNodeId '{start_id}' not in nodes",
            field_path="branchingConfig.startNodeId",
        ))
        return

    # Check end nodes reachable
    end_ids = {n.get("id") for n in nodes if n.get("isEndNode")}
    visited: set[str] = set()
    stack = [start_id]
    while stack:
        nid = stack.pop()
        if nid in visited or nid not in node_map:
            continue
        visited.add(nid)
        for opt in node_map[nid].get("options", []):
            next_id = opt.get("nextNodeId")
            if next_id:
                stack.append(next_id)

    unreachable = end_ids - visited
    if unreachable:
        issues.append(ValidationIssue(
            severity="error",
            message=f"Unreachable end nodes in branchingConfig: {unreachable}",
            field_path="branchingConfig.nodes",
        ))


def _validate_sorting_config(config: dict[str, Any], issues: list[ValidationIssue]) -> None:
    """Check sorting items reference valid categories."""
    cat_ids = {c.get("id") for c in config.get("categories", [])}
    for i, item in enumerate(config.get("items", [])):
        cid = item.get("correctCategoryId", "")
        if cid and cid not in cat_ids:
            issues.append(ValidationIssue(
                severity="error",
                message=f"sortingConfig.items[{i}].correctCategoryId '{cid}' not in categories",
                field_path=f"sortingConfig.items[{i}].correctCategoryId",
            ))


def _validate_memory_config(config: dict[str, Any], issues: list[ValidationIssue]) -> None:
    """Check memory pair ID uniqueness."""
    seen: set[str] = set()
    for i, pair in enumerate(config.get("pairs", [])):
        pid = pair.get("id", "")
        if pid in seen:
            issues.append(ValidationIssue(
                severity="error",
                message=f"Duplicate memoryMatchConfig pair ID: '{pid}'",
                field_path=f"memoryMatchConfig.pairs[{i}].id",
            ))
        seen.add(pid)
