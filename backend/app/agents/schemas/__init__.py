"""Schema helpers for guided decoding and blueprint validation."""

from app.agents.schemas.interactive_diagram import (
    InteractiveDiagramZone,
    InteractiveDiagramLabel,
    get_interactive_diagram_blueprint_schema,
    get_diagram_svg_spec_schema,
)

from app.agents.schemas.blueprint_schemas import (
    validate_blueprint,
    get_schema_for_template,
    SequenceBuilderBlueprint,
    BucketSortBlueprint,
    ParameterPlaygroundBlueprint,
    TimelineOrderBlueprint,
    MatchPairsBlueprint,
    StateTracerCodeBlueprint,
    InteractiveDiagramBlueprint,
    TEMPLATE_SCHEMA_MAP,
)

from app.agents.schemas.game_design_v3 import GameDesignV3, validate_game_design
from app.agents.schemas.asset_graph import AssetGraph, Edge as AssetEdge, NodeType, RelationType
from app.agents.schemas.asset_spec import AssetSpec, AssetManifest, AssetType, WorkerType

from app.agents.schemas.game_plan_schemas import (
    MechanicType,
    WorkflowType,
    ProgressionType,
    TransitionTrigger,
    MechanicSpec,
    AssetNeed,
    ModeTransition,
    SceneBreakdown,
    SceneTask,
    SceneTransition,
    ScoringRubric,
    ExtendedGamePlan,
    create_single_scene_plan,
    GameDesign,
    SceneDesign,
)

from app.agents.schemas.blueprint_schemas import BlueprintSceneTask

__all__ = [
    # Interactive diagram (existing)
    "InteractiveDiagramZone",
    "InteractiveDiagramLabel",
    "get_interactive_diagram_blueprint_schema",
    "get_diagram_svg_spec_schema",
    # Blueprint schemas
    "validate_blueprint",
    "get_schema_for_template",
    "SequenceBuilderBlueprint",
    "BucketSortBlueprint",
    "ParameterPlaygroundBlueprint",
    "TimelineOrderBlueprint",
    "MatchPairsBlueprint",
    "StateTracerCodeBlueprint",
    "InteractiveDiagramBlueprint",
    "TEMPLATE_SCHEMA_MAP",
    # v3 schemas
    "GameDesignV3",
    "validate_game_design",
    "AssetGraph",
    "AssetEdge",
    "NodeType",
    "RelationType",
    "AssetSpec",
    "AssetManifest",
    "AssetType",
    "WorkerType",
    # Game plan schemas (multi-scene, multi-mechanic)
    "MechanicType",
    "WorkflowType",
    "ProgressionType",
    "TransitionTrigger",
    "MechanicSpec",
    "AssetNeed",
    "ModeTransition",
    "SceneBreakdown",
    "SceneTask",
    "BlueprintSceneTask",
    "SceneTransition",
    "ScoringRubric",
    "ExtendedGamePlan",
    "create_single_scene_plan",
    # Unconstrained game design schemas
    "GameDesign",
    "SceneDesign",
]
