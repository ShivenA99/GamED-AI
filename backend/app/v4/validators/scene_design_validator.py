"""Scene Design Validator (Phase 1b).

Deterministic validation of SceneCreativeDesign.
Validates alignment between scene concept mechanics and creative designs.
"""

from app.utils.logging_config import get_logger
from app.v4.schemas.creative_design import SceneCreativeDesign
from app.v4.schemas.validation import ValidationIssue, ValidationResult

logger = get_logger("gamed_ai.v4.scene_design_validator")

# Valid layout modes per mechanic type
VALID_LAYOUT_MODES: dict[str, set[str]] = {
    "drag_drop": {"default", "radial", "grid", "spatial"},
    "sequencing": {"vertical_list", "horizontal_list", "circular_cycle", "flowchart", "default"},
    "sorting_categories": {"bucket", "column", "grid", "venn_2", "default"},
    "trace_path": {"default"},
    "memory_match": {"grid", "scattered", "default"},
    "click_to_identify": {"spatial", "default"},
    "description_matching": {"spatial", "list", "default"},
    "branching_scenario": {"tree", "flowchart", "default"},
    "compare_contrast": {"side_by_side", "overlay", "default"},
    "hierarchical": {"tree", "nested", "default"},
}

VALID_CARD_TYPES = {"text_only", "icon_and_text", "image_card"}


def validate_scene_design(
    design: SceneCreativeDesign,
    scene_concept_mechanics: list[dict],
) -> ValidationResult:
    """Validate a SceneCreativeDesign against its scene concept.

    Checks:
    - Mechanic count alignment
    - Mechanic type alignment
    - instruction_text length
    - layout_mode validity
    - card_type validity
    - image_spec presence for diagram scenes
    - generation_goal non-empty
    """
    issues: list[ValidationIssue] = []
    prefix = f"scene[{design.scene_id}]"

    # Mechanic count alignment
    expected_count = len(scene_concept_mechanics)
    actual_count = len(design.mechanic_designs)
    if actual_count != expected_count:
        issues.append(ValidationIssue(
            severity="error",
            message=(
                f"{prefix}: Expected {expected_count} mechanic designs, "
                f"got {actual_count}"
            ),
        ))

    # Per-mechanic validation
    for mi, md in enumerate(design.mechanic_designs):
        md_prefix = f"{prefix}.mechanic_designs[{mi}]"

        # Type alignment (if we have a matching concept mechanic)
        if mi < len(scene_concept_mechanics):
            expected_type = scene_concept_mechanics[mi].get("mechanic_type")
            if expected_type and md.mechanic_type != expected_type:
                issues.append(ValidationIssue(
                    severity="error",
                    message=(
                        f"{md_prefix}: Expected type '{expected_type}', "
                        f"got '{md.mechanic_type}'"
                    ),
                ))

        # instruction_text length
        if len(md.instruction_text) < 20:
            issues.append(ValidationIssue(
                severity="error",
                message=f"{md_prefix}: instruction_text too short ({len(md.instruction_text)} chars, need 20+)",
            ))

        # visual_style non-empty
        if not md.visual_style.strip():
            issues.append(ValidationIssue(
                severity="error",
                message=f"{md_prefix}: visual_style is empty",
            ))

        # layout_mode validity
        valid_modes = VALID_LAYOUT_MODES.get(md.mechanic_type, {"default"})
        if md.layout_mode not in valid_modes:
            issues.append(ValidationIssue(
                severity="warning",
                message=(
                    f"{md_prefix}: layout_mode '{md.layout_mode}' not valid for "
                    f"{md.mechanic_type} (valid: {valid_modes})"
                ),
            ))

        # card_type validity
        if md.card_type not in VALID_CARD_TYPES:
            issues.append(ValidationIssue(
                severity="warning",
                message=f"{md_prefix}: card_type '{md.card_type}' not valid (valid: {VALID_CARD_TYPES})",
            ))

        # generation_goal non-empty
        if not md.generation_goal.strip():
            issues.append(ValidationIssue(
                severity="error",
                message=f"{md_prefix}: generation_goal is empty",
            ))

    # Image spec check
    has_diagram_mechanic = any(
        m.get("mechanic_type") in {"drag_drop", "click_to_identify", "trace_path", "description_matching"}
        for m in scene_concept_mechanics
    )
    if has_diagram_mechanic and not design.image_spec:
        issues.append(ValidationIssue(
            severity="warning",
            message=f"{prefix}: Scene has zone-based mechanics but no image_spec",
        ))
    if design.image_spec and len(design.image_spec.description) < 20:
        issues.append(ValidationIssue(
            severity="error",
            message=f"{prefix}: image_spec.description too short ({len(design.image_spec.description)} chars)",
        ))

    # Compare contrast needs second_image_spec
    has_compare = any(
        m.get("mechanic_type") == "compare_contrast"
        for m in scene_concept_mechanics
    )
    if has_compare and not design.second_image_spec:
        issues.append(ValidationIssue(
            severity="warning",
            message=f"{prefix}: compare_contrast mechanic but no second_image_spec",
        ))

    has_errors = any(i.severity == "error" for i in issues)
    score = 1.0 if not has_errors else max(0.0, 1.0 - (len(issues) * 0.1))

    return ValidationResult(
        passed=not has_errors,
        score=score,
        issues=issues,
    )
