"""
Mechanic Contract Registry — V4 Pipeline Source of Truth.

Each mechanic defines exactly what it needs from each pipeline stage,
what entity types it operates on, and which frontend config key it populates.

This replaces all hardcoded mechanic assumptions scattered across agents.
Every agent should consult this registry instead of assuming drag_drop defaults.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class StageContract:
    """What a mechanic needs from a specific pipeline stage."""
    required_output_fields: tuple[str, ...] = ()
    optional_output_fields: tuple[str, ...] = ()
    guidance_note: str = ""


@dataclass(frozen=True)
class MechanicContract:
    """Complete contract for a single mechanic type."""

    # Identity
    mechanic_type: str
    display_name: str

    # Asset requirements
    needs_diagram: bool = True       # Needs a primary diagram image
    needs_zones: bool = True         # Needs zone detection on image
    needs_labels: bool = True        # Needs label→zone mapping
    needs_second_diagram: bool = False  # compare_contrast needs 2

    # Entity type this mechanic operates on
    entity_type: str = "zone_label"  # zone_label | sequence_item | sorting_item | memory_pair | decision_node | compare_feature

    # Frontend config key on InteractiveDiagramBlueprint
    frontend_config_key: Optional[str] = None

    # Per-stage contracts
    game_designer: StageContract = field(default_factory=StageContract)
    scene_architect: StageContract = field(default_factory=StageContract)
    interaction_designer: StageContract = field(default_factory=StageContract)
    asset_generator: StageContract = field(default_factory=StageContract)
    blueprint_assembler: StageContract = field(default_factory=StageContract)

    # Domain knowledge fields to retrieve
    dk_fields: tuple[str, ...] = ("canonical_labels",)


# =============================================================================
# CONTRACT DEFINITIONS
# =============================================================================

DRAG_DROP = MechanicContract(
    mechanic_type="drag_drop",
    display_name="Drag & Drop",
    needs_diagram=True,
    needs_zones=True,
    needs_labels=True,
    entity_type="zone_label",
    frontend_config_key="dragDropConfig",
    dk_fields=("canonical_labels", "visual_description", "key_relationships"),
    game_designer=StageContract(
        required_output_fields=("zones", "labels"),
        guidance_note="Design zones on diagram, labels to drag onto them.",
    ),
    scene_architect=StageContract(
        required_output_fields=("zones", "labels", "mechanic_config"),
        guidance_note="Generate zone positions + label-zone mappings. Use generate_mechanic_content tool.",
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
        guidance_note="Define scoring strategy, feedback messages, distractor labels if needed.",
    ),
    asset_generator=StageContract(
        required_output_fields=("diagram_image", "zones"),
        guidance_note="Search/generate diagram image → Box2d→SAM3 zone detection.",
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("dragDropConfig",),
        guidance_note="Populate dragDropConfig with leader_line_style, tray_position, placement_animation, etc.",
    ),
)

CLICK_TO_IDENTIFY = MechanicContract(
    mechanic_type="click_to_identify",
    display_name="Click to Identify",
    needs_diagram=True,
    needs_zones=True,
    needs_labels=True,
    entity_type="zone_label",
    frontend_config_key="clickToIdentifyConfig",
    dk_fields=("canonical_labels", "visual_description", "functions"),
    game_designer=StageContract(
        required_output_fields=("zones", "identification_prompts"),
        guidance_note="Design zones + functional prompts (e.g., 'Click the part that pumps blood').",
    ),
    scene_architect=StageContract(
        required_output_fields=("zones", "identification_prompts", "mechanic_config"),
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
    ),
    asset_generator=StageContract(
        required_output_fields=("diagram_image", "zones"),
        guidance_note="Search/generate diagram → zone detection.",
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("clickToIdentifyConfig", "identificationPrompts"),
    ),
)

TRACE_PATH = MechanicContract(
    mechanic_type="trace_path",
    display_name="Trace Path",
    needs_diagram=True,
    needs_zones=True,
    needs_labels=True,
    entity_type="zone_label",
    frontend_config_key="tracePathConfig",
    dk_fields=("canonical_labels", "visual_description", "processes", "flow_sequences"),
    game_designer=StageContract(
        required_output_fields=("zones", "paths"),
        guidance_note="Design waypoint zones along a flow path (e.g., blood flow through heart).",
    ),
    scene_architect=StageContract(
        required_output_fields=("zones", "paths", "mechanic_config"),
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
    ),
    asset_generator=StageContract(
        required_output_fields=("diagram_image", "zones"),
        guidance_note="Diagram must show pathways/flow. Zone detection on waypoints.",
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("tracePathConfig", "paths"),
    ),
)

DESCRIPTION_MATCHING = MechanicContract(
    mechanic_type="description_matching",
    display_name="Description Matching",
    needs_diagram=True,
    needs_zones=True,
    needs_labels=True,
    entity_type="zone_label",
    frontend_config_key="descriptionMatchingConfig",
    dk_fields=("canonical_labels", "visual_description", "functions", "key_relationships"),
    game_designer=StageContract(
        required_output_fields=("zones", "descriptions"),
        guidance_note="Design zones + per-zone functional descriptions to match.",
    ),
    scene_architect=StageContract(
        required_output_fields=("zones", "descriptions", "mechanic_config"),
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
    ),
    asset_generator=StageContract(
        required_output_fields=("diagram_image", "zones"),
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("descriptionMatchingConfig",),
    ),
)

SEQUENCING = MechanicContract(
    mechanic_type="sequencing",
    display_name="Sequencing",
    needs_diagram=False,  # Optional — can use flow map background
    needs_zones=False,
    needs_labels=False,
    entity_type="sequence_item",
    frontend_config_key="sequenceConfig",
    dk_fields=("canonical_labels", "processes", "flow_sequences", "temporal_order"),
    game_designer=StageContract(
        required_output_fields=("sequence_items", "correct_order"),
        guidance_note="Design ordered items (steps, stages, phases) with correct sequence.",
    ),
    scene_architect=StageContract(
        required_output_fields=("sequence_items", "correct_order", "mechanic_config"),
        guidance_note="Use generate_mechanic_content with sequence-specific fields.",
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
    ),
    asset_generator=StageContract(
        required_output_fields=(),
        optional_output_fields=("step_icons", "background_image"),
        guidance_note="Optional: generate step icons or flow map background.",
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("sequenceConfig",),
    ),
)

SORTING_CATEGORIES = MechanicContract(
    mechanic_type="sorting_categories",
    display_name="Sorting Categories",
    needs_diagram=False,
    needs_zones=False,
    needs_labels=False,
    entity_type="sorting_item",
    frontend_config_key="sortingConfig",
    dk_fields=("canonical_labels", "categories", "classifications", "key_relationships"),
    game_designer=StageContract(
        required_output_fields=("sorting_items", "categories"),
        guidance_note="Design items to sort and category bins.",
    ),
    scene_architect=StageContract(
        required_output_fields=("sorting_items", "categories", "mechanic_config"),
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
    ),
    asset_generator=StageContract(
        required_output_fields=(),
        optional_output_fields=("category_images", "item_images"),
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("sortingConfig",),
    ),
)

MEMORY_MATCH = MechanicContract(
    mechanic_type="memory_match",
    display_name="Memory Match",
    needs_diagram=False,
    needs_zones=False,
    needs_labels=False,
    entity_type="memory_pair",
    frontend_config_key="memoryMatchConfig",
    dk_fields=("canonical_labels", "definitions", "key_relationships"),
    game_designer=StageContract(
        required_output_fields=("memory_pairs",),
        guidance_note="Design term↔definition or concept↔example pairs.",
    ),
    scene_architect=StageContract(
        required_output_fields=("memory_pairs", "mechanic_config"),
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
    ),
    asset_generator=StageContract(
        required_output_fields=(),
        optional_output_fields=("card_images",),
        guidance_note="Optional: generate card face images for image-based pairs.",
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("memoryMatchConfig",),
    ),
)

BRANCHING_SCENARIO = MechanicContract(
    mechanic_type="branching_scenario",
    display_name="Branching Scenario",
    needs_diagram=False,
    needs_zones=False,
    needs_labels=False,
    entity_type="decision_node",
    frontend_config_key="branchingConfig",
    dk_fields=("canonical_labels", "processes", "cause_effect", "misconceptions"),
    game_designer=StageContract(
        required_output_fields=("decision_nodes", "start_node_id"),
        guidance_note="Design decision tree with nodes, options, consequences.",
    ),
    scene_architect=StageContract(
        required_output_fields=("decision_nodes", "mechanic_config"),
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
    ),
    asset_generator=StageContract(
        required_output_fields=(),
        optional_output_fields=("scene_images",),
        guidance_note="Optional: per-node background/scene images.",
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("branchingConfig",),
    ),
)

COMPARE_CONTRAST = MechanicContract(
    mechanic_type="compare_contrast",
    display_name="Compare & Contrast",
    needs_diagram=True,
    needs_zones=True,
    needs_labels=True,
    needs_second_diagram=True,
    entity_type="compare_feature",
    frontend_config_key="compareConfig",
    dk_fields=("canonical_labels", "visual_description", "key_relationships", "similarities_differences"),
    game_designer=StageContract(
        required_output_fields=("diagram_a", "diagram_b", "expected_categories"),
        guidance_note="Design two subjects to compare, features to categorize.",
    ),
    scene_architect=StageContract(
        required_output_fields=("diagram_a_zones", "diagram_b_zones", "mechanic_config"),
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
    ),
    asset_generator=StageContract(
        required_output_fields=("diagram_a_image", "diagram_b_image"),
        guidance_note="Search/generate TWO diagrams → zone detection on both.",
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("compareConfig",),
    ),
)

HIERARCHICAL = MechanicContract(
    mechanic_type="hierarchical",
    display_name="Hierarchical Labeling",
    needs_diagram=True,
    needs_zones=True,
    needs_labels=True,
    entity_type="zone_label",
    frontend_config_key=None,  # Uses zoneGroups + standard zones/labels
    dk_fields=("canonical_labels", "visual_description", "hierarchy", "key_relationships"),
    game_designer=StageContract(
        required_output_fields=("zones", "labels", "zone_groups"),
        guidance_note="Design hierarchical zone groups with parent→child relationships.",
    ),
    scene_architect=StageContract(
        required_output_fields=("zones", "labels", "zone_groups"),
    ),
    interaction_designer=StageContract(
        required_output_fields=("scoring", "feedback"),
    ),
    asset_generator=StageContract(
        required_output_fields=("diagram_image", "zones"),
    ),
    blueprint_assembler=StageContract(
        required_output_fields=("zoneGroups",),
    ),
)


# =============================================================================
# REGISTRY
# =============================================================================

MECHANIC_CONTRACTS: dict[str, MechanicContract] = {
    "drag_drop": DRAG_DROP,
    "click_to_identify": CLICK_TO_IDENTIFY,
    "trace_path": TRACE_PATH,
    "description_matching": DESCRIPTION_MATCHING,
    "sequencing": SEQUENCING,
    "sorting_categories": SORTING_CATEGORIES,
    "memory_match": MEMORY_MATCH,
    "branching_scenario": BRANCHING_SCENARIO,
    "compare_contrast": COMPARE_CONTRAST,
    "hierarchical": HIERARCHICAL,
}

# Aliases for common misspellings / alternative names
_ALIASES: dict[str, str] = {
    "drag-drop": "drag_drop",
    "drag_and_drop": "drag_drop",
    "label": "drag_drop",
    "labeling": "drag_drop",
    "click": "click_to_identify",
    "click_identify": "click_to_identify",
    "hotspot": "click_to_identify",
    "trace": "trace_path",
    "path": "trace_path",
    "flow": "trace_path",
    "sequence": "sequencing",
    "order": "sequencing",
    "timeline": "sequencing",
    "sort": "sorting_categories",
    "sorting": "sorting_categories",
    "categorize": "sorting_categories",
    "bucket_sort": "sorting_categories",
    "memory": "memory_match",
    "matching": "memory_match",
    "match_pairs": "memory_match",
    "branching": "branching_scenario",
    "decision": "branching_scenario",
    "scenario": "branching_scenario",
    "compare": "compare_contrast",
    "contrast": "compare_contrast",
    "description": "description_matching",
    "timed_challenge": "drag_drop",  # Timed wraps another mechanic; drag_drop is legacy default
}


def get_contract(mechanic_type: str) -> MechanicContract:
    """Get the contract for a mechanic type. Raises ValueError if unknown."""
    normalized = mechanic_type.strip().lower().replace("-", "_")
    if normalized in MECHANIC_CONTRACTS:
        return MECHANIC_CONTRACTS[normalized]
    if normalized in _ALIASES:
        return MECHANIC_CONTRACTS[_ALIASES[normalized]]
    raise ValueError(
        f"Unknown mechanic type: '{mechanic_type}'. "
        f"Valid types: {sorted(MECHANIC_CONTRACTS.keys())}"
    )


def get_contract_safe(mechanic_type: str) -> Optional[MechanicContract]:
    """Get contract or None if unknown. For non-critical paths."""
    try:
        return get_contract(mechanic_type)
    except ValueError:
        return None


def normalize_mechanic_type(raw: str) -> str:
    """Normalize a mechanic type string to its canonical form.

    Returns empty string if unknown — callers must handle this explicitly.
    NEVER returns 'drag_drop' as a fallback for unknown types.
    """
    if not raw:
        return ""
    normalized = raw.strip().lower().replace("-", "_")
    if normalized in MECHANIC_CONTRACTS:
        return normalized
    if normalized in _ALIASES:
        return _ALIASES[normalized]
    return ""


def needs_image_pipeline(mechanic_type: str) -> bool:
    """Check if a mechanic needs the image→zones→labels pipeline."""
    contract = get_contract_safe(mechanic_type)
    if not contract:
        return False
    return contract.needs_diagram and contract.needs_zones


def get_frontend_config_key(mechanic_type: str) -> Optional[str]:
    """Get the frontend blueprint config key for a mechanic."""
    contract = get_contract_safe(mechanic_type)
    return contract.frontend_config_key if contract else None


def get_all_mechanic_types() -> list[str]:
    """Get all valid mechanic type strings."""
    return sorted(MECHANIC_CONTRACTS.keys())


def get_image_mechanics() -> list[str]:
    """Get mechanic types that need diagram images."""
    return [k for k, v in MECHANIC_CONTRACTS.items() if v.needs_diagram]


def get_content_only_mechanics() -> list[str]:
    """Get mechanic types that DON'T need diagram images."""
    return [k for k, v in MECHANIC_CONTRACTS.items() if not v.needs_diagram]
