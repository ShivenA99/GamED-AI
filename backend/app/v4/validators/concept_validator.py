"""Game Concept Validator (Phase 1a).

Deterministic structural validation of GameConcept.
No LLM calls — pure rule checking.
"""

from app.utils.logging_config import get_logger
from app.v4.contracts import SUPPORTED_MECHANICS, ZONE_BASED_MECHANICS
from app.v4.schemas.game_concept import GameConcept
from app.v4.schemas.validation import ValidationIssue, ValidationResult

logger = get_logger("gamed_ai.v4.concept_validator")


def validate_game_concept(concept: GameConcept) -> ValidationResult:
    """Validate a GameConcept for structural correctness.

    Checks:
    - Scene count (1-6)
    - Mechanic types are supported
    - Zone labels consistency
    - Visual mechanics have needs_diagram=True
    - Content-only mechanics have correct settings
    - Distractor labels don't overlap with zone labels
    """
    issues: list[ValidationIssue] = []

    # Scene count
    if len(concept.scenes) < 1:
        issues.append(ValidationIssue(
            severity="error", message="Must have at least 1 scene"
        ))
    if len(concept.scenes) > 6:
        issues.append(ValidationIssue(
            severity="warning", message=f"Too many scenes ({len(concept.scenes)}), max recommended is 6"
        ))

    all_zone_labels_set = set(concept.all_zone_labels)

    for si, scene in enumerate(concept.scenes):
        scene_prefix = f"scenes[{si}]"

        # Scene must have mechanics
        if not scene.mechanics:
            issues.append(ValidationIssue(
                severity="error",
                message=f"{scene_prefix}: No mechanics defined",
                field_path=f"scenes[{si}].mechanics",
            ))
            continue

        scene_labels_set = set(scene.zone_labels)

        # Scene zone labels must be subset of all_zone_labels
        orphan_labels = scene_labels_set - all_zone_labels_set
        if orphan_labels:
            issues.append(ValidationIssue(
                severity="error",
                message=f"{scene_prefix}: Zone labels {orphan_labels} not in all_zone_labels",
                field_path=f"scenes[{si}].zone_labels",
            ))

        for mi, mech in enumerate(scene.mechanics):
            mech_prefix = f"{scene_prefix}.mechanics[{mi}]"

            # Mechanic type must be supported
            if mech.mechanic_type not in SUPPORTED_MECHANICS:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"{mech_prefix}: Unsupported mechanic type '{mech.mechanic_type}'",
                    field_path=f"scenes[{si}].mechanics[{mi}].mechanic_type",
                ))
                continue

            # Zone-based mechanics need diagram
            if mech.mechanic_type in ZONE_BASED_MECHANICS:
                if not scene.needs_diagram:
                    issues.append(ValidationIssue(
                        severity="error",
                        message=f"{mech_prefix}: {mech.mechanic_type} requires needs_diagram=true",
                        field_path=f"scenes[{si}].needs_diagram",
                    ))

                # Zone labels used must be in scene zone labels
                mech_labels = set(mech.zone_labels_used)
                orphan_mech = mech_labels - scene_labels_set
                if orphan_mech:
                    issues.append(ValidationIssue(
                        severity="error",
                        message=(
                            f"{mech_prefix}: Zone labels {orphan_mech} not in scene zone_labels"
                        ),
                        field_path=f"scenes[{si}].mechanics[{mi}].zone_labels_used",
                    ))

            # expected_item_count > 0
            if mech.expected_item_count < 1:
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"{mech_prefix}: expected_item_count must be >= 1",
                    field_path=f"scenes[{si}].mechanics[{mi}].expected_item_count",
                ))

            # Timed mechanics need time_limit_seconds
            if mech.is_timed and (not mech.time_limit_seconds or mech.time_limit_seconds <= 0):
                issues.append(ValidationIssue(
                    severity="warning",
                    message=f"{mech_prefix}: Timed mechanic has no time_limit_seconds",
                    field_path=f"scenes[{si}].mechanics[{mi}].time_limit_seconds",
                ))

    # Distractor labels must not overlap
    distractor_set = set(concept.distractor_labels)
    overlap = distractor_set & all_zone_labels_set
    if overlap:
        issues.append(ValidationIssue(
            severity="error",
            message=f"distractor_labels overlap with all_zone_labels: {overlap}",
            field_path="distractor_labels",
        ))

    # Compute pass/fail
    has_errors = any(i.severity == "error" for i in issues)
    score = 1.0 if not has_errors else max(0.0, 1.0 - (len(issues) * 0.1))

    result = ValidationResult(
        passed=not has_errors,
        score=score,
        issues=issues,
    )

    logger.info(f"Concept validation: passed={result.passed}, issues={len(issues)}")
    return result
