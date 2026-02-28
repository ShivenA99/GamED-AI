"""
SceneSpecV3 — Per-scene structural specification.

Produced by scene_architect_v3 (Phase 2).
Consumed by interaction_designer_v3, asset_generator_v3, blueprint_assembler_v3.

Defines: zones with IDs/hints/descriptions, mechanic configurations,
image requirements, and zone hierarchy — for each scene.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agents.schemas.game_design_v3 import (
    PathDesign,
    ClickDesign,
    SequenceDesign,
    SortingDesign,
    BranchingDesign,
    CompareDesign,
    MemoryMatchDesign,
    DescriptionMatchDesign,
    TimedDesign,
)


class ZoneSpecV3(BaseModel):
    """Structural zone specification (no coordinates — those come from asset_generator)."""
    model_config = ConfigDict(extra="allow")

    zone_id: str  # e.g., "zone_left_atrium"
    label: str  # Display label: "Left Atrium"
    position_hint: str = ""  # Spatial hint: "upper-left quadrant of heart"
    description: str = ""  # Educational description for hover/tooltip
    hint: str = ""  # Hint text for students
    difficulty: int = 2  # 1-5

    @model_validator(mode="before")
    @classmethod
    def _coerce_zone(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Auto-generate zone_id from label if missing
        if "zone_id" not in data and "label" in data:
            label = data["label"]
            data["zone_id"] = f"zone_{label.lower().replace(' ', '_').replace('-', '_')}"
        return data


class MechanicConfigV3(BaseModel):
    """Per-mechanic configuration within a scene.

    Has both typed optional config fields (path_config, click_config, etc.)
    AND a generic `config` dict for backwards compatibility. The model_validator
    promotes data from `config` dict into typed fields when possible.
    """
    model_config = ConfigDict(extra="allow")

    type: str  # "drag_drop", "click_to_identify", "trace_path", etc.
    zone_labels_used: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)

    # Typed per-mechanic config fields (populated from `config` or directly)
    path_config: Optional[PathDesign] = None
    click_config: Optional[ClickDesign] = None
    sequence_config: Optional[SequenceDesign] = None
    sorting_config: Optional[SortingDesign] = None
    branching_config: Optional[BranchingDesign] = None
    compare_config: Optional[CompareDesign] = None
    memory_config: Optional[MemoryMatchDesign] = None
    timed_config: Optional[TimedDesign] = None
    description_match_config: Optional[DescriptionMatchDesign] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_config(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # LLM sometimes uses mechanic_type instead of type
        if "type" not in data and "mechanic_type" in data:
            data["type"] = data.pop("mechanic_type")

        # Promote config dict contents into typed fields when type matches
        mech_type = data.get("type", "")
        config = data.get("config", {})
        if isinstance(config, dict) and config:
            _CONFIG_FIELD_MAP = {
                "trace_path": "path_config",
                "click_to_identify": "click_config",
                "sequencing": "sequence_config",
                "sorting_categories": "sorting_config",
                "branching_scenario": "branching_config",
                "compare_contrast": "compare_config",
                "memory_match": "memory_config",
                "timed_challenge": "timed_config",
                "description_matching": "description_match_config",
            }
            field_name = _CONFIG_FIELD_MAP.get(mech_type)
            if field_name and field_name not in data:
                data[field_name] = config

        return data

    def get_typed_config(self) -> Optional[BaseModel]:
        """Return the typed config for this mechanic, if available."""
        _map = {
            "trace_path": self.path_config,
            "click_to_identify": self.click_config,
            "sequencing": self.sequence_config,
            "sorting_categories": self.sorting_config,
            "branching_scenario": self.branching_config,
            "compare_contrast": self.compare_config,
            "memory_match": self.memory_config,
            "timed_challenge": self.timed_config,
            "description_matching": self.description_match_config,
        }
        return _map.get(self.type)


class ZoneHierarchyV3(BaseModel):
    """Zone hierarchy within a scene."""
    model_config = ConfigDict(extra="allow")

    parent: str  # Parent label
    children: List[str]  # Child labels
    reveal_trigger: str = "click_expand"  # click_expand, complete_parent, hover_reveal


class SceneSpecV3(BaseModel):
    """Complete structural specification for one scene."""
    model_config = ConfigDict(extra="allow")

    scene_number: int
    title: str = ""

    # Image requirements (for asset generator)
    image_description: str = ""
    image_requirements: List[str] = Field(default_factory=list)
    image_style: str = "clean_educational"

    # Zone architecture
    zones: List[ZoneSpecV3] = Field(default_factory=list)

    # Mechanic-specific configuration (one per mechanic in this scene)
    mechanic_configs: List[MechanicConfigV3] = Field(default_factory=list)

    # Mechanic data requirements (what each mechanic needs to function)
    mechanic_data: Dict[str, Any] = Field(default_factory=dict)

    # Hierarchy (if applicable)
    zone_hierarchy: List[ZoneHierarchyV3] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_scene_spec(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # visual_description → image_description
        if "visual_description" in data and "image_description" not in data:
            data["image_description"] = data.pop("visual_description")
        # zone_hierarchy as dict → list
        zh = data.get("zone_hierarchy")
        if isinstance(zh, dict):
            # Convert {parent: {children: [...], ...}} to list format
            items = []
            for parent, info in zh.items():
                if isinstance(info, dict):
                    items.append({
                        "parent": parent,
                        "children": info.get("children", []),
                        "reveal_trigger": info.get("reveal_trigger", "click_expand"),
                    })
                elif isinstance(info, list):
                    items.append({"parent": parent, "children": info})
            data["zone_hierarchy"] = items
        return data

    def summary(self) -> str:
        """Generate structured summary for downstream agents."""
        zone_count = len(self.zones)
        mech_types = [mc.type for mc in self.mechanic_configs]
        return (
            f"Scene {self.scene_number}: '{self.title}' | "
            f"{zone_count} zones | mechanics: {', '.join(mech_types)}"
        )


def validate_scene_specs(
    scene_specs: List[Dict[str, Any]],
    game_design: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Cross-stage contract validation for scene specs.

    Checks:
    - Every game_design zone_label has a zone in scene_specs
    - Scene numbers match
    - Mechanic types match
    - Zones have non-empty hints/descriptions
    - Image descriptions are non-empty
    """
    issues: List[str] = []

    # Parse scene specs
    parsed_specs: List[SceneSpecV3] = []
    for spec_dict in scene_specs:
        try:
            parsed_specs.append(SceneSpecV3.model_validate(spec_dict))
        except Exception as e:
            issues.append(f"Failed to parse scene spec: {e}")

    # Get design info
    design_labels_raw = game_design.get("labels", {})
    if isinstance(design_labels_raw, dict):
        design_zone_labels = set(design_labels_raw.get("zone_labels", []))
    else:
        design_zone_labels = set()

    design_scenes = game_design.get("scenes", [])
    design_scene_numbers = {s.get("scene_number") or s.get("scene_number", 0) for s in design_scenes}

    # Cross-stage checks
    spec_labels = set()
    spec_scene_numbers = set()
    for spec in parsed_specs:
        spec_scene_numbers.add(spec.scene_number)
        for z in spec.zones:
            spec_labels.add(z.label)

    # Check 1: Every design zone_label has a zone in specs
    missing_labels = design_zone_labels - spec_labels
    if missing_labels:
        issues.append(f"CROSS-STAGE: Labels in game_design but missing from scene_specs: {missing_labels}")

    # Check 2: Scene numbers match
    if design_scene_numbers and design_scene_numbers != spec_scene_numbers:
        issues.append(f"CROSS-STAGE: Scene number mismatch. Design: {sorted(design_scene_numbers)}, Specs: {sorted(spec_scene_numbers)}")

    # Check 3: Mechanic types match per scene
    for spec in parsed_specs:
        design_scene = next(
            (s for s in design_scenes if s.get("scene_number") == spec.scene_number),
            None,
        )
        if design_scene:
            design_mechanics = design_scene.get("mechanics", [])
            design_types = {m.get("type", "") for m in design_mechanics if isinstance(m, dict)}
            spec_types = {mc.type for mc in spec.mechanic_configs}
            if design_types and design_types != spec_types:
                issues.append(
                    f"CROSS-STAGE: Scene {spec.scene_number} mechanic mismatch. "
                    f"Design: {sorted(design_types)}, Spec: {sorted(spec_types)}"
                )

    # Internal checks
    for spec in parsed_specs:
        if not spec.zones:
            issues.append(f"Scene {spec.scene_number}: no zones defined")
        if not spec.mechanic_configs:
            issues.append(f"Scene {spec.scene_number}: no mechanic configs")
        if not spec.image_description:
            issues.append(f"Scene {spec.scene_number}: empty image_description")
        for z in spec.zones:
            if not z.position_hint:
                issues.append(f"Scene {spec.scene_number}, zone '{z.label}': empty position_hint")

        # F3: Mechanic-specific data requirements
        for mc in spec.mechanic_configs:
            typed = mc.get_typed_config()
            mtype = mc.type

            if mtype == "trace_path":
                pc = mc.path_config
                if not pc or not pc.waypoints:
                    issues.append(
                        f"Scene {spec.scene_number}: trace_path mechanic needs "
                        f"path_config with waypoints"
                    )

            elif mtype == "click_to_identify":
                cc = mc.click_config
                if not cc or (not cc.prompts and not cc.click_options):
                    issues.append(
                        f"Scene {spec.scene_number}: click_to_identify mechanic needs "
                        f"click_config with prompts or click_options"
                    )

            elif mtype == "sequencing":
                sc = mc.sequence_config
                if not sc or not sc.correct_order:
                    issues.append(
                        f"Scene {spec.scene_number}: sequencing mechanic needs "
                        f"sequence_config with correct_order"
                    )

            elif mtype == "description_matching":
                dmc = mc.description_match_config
                if not dmc or not dmc.descriptions:
                    issues.append(
                        f"Scene {spec.scene_number}: description_matching mechanic needs "
                        f"description_match_config with descriptions"
                    )

            elif mtype == "sorting_categories":
                sc = mc.sorting_config
                if not sc or not sc.categories or not sc.items:
                    issues.append(
                        f"Scene {spec.scene_number}: sorting_categories mechanic needs "
                        f"sorting_config with categories and items"
                    )

            elif mtype == "branching_scenario":
                bc = mc.branching_config
                if not bc or not bc.nodes:
                    issues.append(
                        f"Scene {spec.scene_number}: branching_scenario mechanic needs "
                        f"branching_config with nodes"
                    )

            elif mtype == "memory_match":
                mmc = mc.memory_config
                if not mmc or not mmc.pairs:
                    issues.append(
                        f"Scene {spec.scene_number}: memory_match mechanic needs "
                        f"memory_config with pairs"
                    )

            elif mtype == "compare_contrast":
                cfg = mc.compare_config
                if not cfg or not cfg.expected_categories:
                    issues.append(
                        f"Scene {spec.scene_number}: compare_contrast mechanic needs "
                        f"compare_config with expected_categories"
                    )

    has_fatal = any("CROSS-STAGE" in i or "no zones" in i or "no mechanic" in i for i in issues)
    passed = not has_fatal
    score = max(0.0, 1.0 - 0.15 * len([i for i in issues if "CROSS-STAGE" in i]) - 0.05 * len(issues))

    return {"passed": passed, "score": round(score, 3), "issues": issues}
