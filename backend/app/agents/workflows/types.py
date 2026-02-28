"""Type definitions for workflow data structures."""
from typing import Dict, List, Any, Optional, Literal, TypedDict

MechanicType = Literal[
    "drag_drop", "trace_path", "sequencing", "sorting", "memory_match",
    "comparison", "branching_scenario", "click_to_identify", "reveal", "hotspot"
]

WorkflowType = Literal[
    "labeling_diagram", "trace_path", "sequence_items", "comparison_diagrams",
    "sorting", "memory_match", "branching_scenario"
]

MECHANIC_TO_WORKFLOW: Dict[str, str] = {
    "drag_drop": "labeling_diagram",
    "click_to_identify": "labeling_diagram",
    "hotspot": "labeling_diagram",
    "trace_path": "trace_path",
    "sequencing": "sequence_items",
    "sorting": "sorting",
    "memory_match": "memory_match",
    "comparison": "comparison_diagrams",
    "branching_scenario": "branching_scenario",
    "reveal": "labeling_diagram"
}

class AssetSpec(TypedDict, total=False):
    id: str
    scene_number: int
    asset_type: str
    workflow: str
    spec: Dict[str, Any]
    depends_on: List[str]
    priority: int

class WorkflowExecutionStep(TypedDict):
    asset_id: str
    workflow: str
    scene: int
    dependencies: List[str]
    spec: Dict[str, Any]

class DiagramZone(TypedDict, total=False):
    id: str
    label: str
    x: float
    y: float
    width: Optional[float]
    height: Optional[float]
    shape: Literal["circle", "polygon", "rect"]
    points: Optional[List[List[float]]]
    radius: Optional[float]
    confidence: float
    parent_id: Optional[str]
    mechanic_roles: Dict[str, str]
    scene_number: int

class DiagramLabel(TypedDict, total=False):
    id: str
    text: str
    zone_id: str
    is_canonical: bool
    variants: List[str]
    hint: Optional[str]

class PathWaypoint(TypedDict):
    zone_id: str
    order: int
    label: str
    x: Optional[float]
    y: Optional[float]

class TracePath(TypedDict):
    id: str
    concept: str
    waypoints: List[PathWaypoint]
    description: Optional[str]
    is_cyclic: bool

class SequenceItem(TypedDict, total=False):
    id: str
    content: str
    correct_position: int
    hint: Optional[str]
    explanation: Optional[str]

class SortingItem(TypedDict, total=False):
    id: str
    content: str
    category_id: str
    hint: Optional[str]

class SortingCategory(TypedDict, total=False):
    id: str
    name: str
    description: Optional[str]
    color: Optional[str]

class MemoryPair(TypedDict, total=False):
    id: str
    term: str
    definition: str
    hint: Optional[str]
    image_url: Optional[str]

class BranchingChoice(TypedDict, total=False):
    id: str
    text: str
    next_node_id: str
    is_correct: bool
    feedback: Optional[str]

class BranchingNode(TypedDict, total=False):
    id: str
    content: str
    is_decision_point: bool
    is_terminal: bool
    choices: Optional[List[BranchingChoice]]
    correct_choice_id: Optional[str]
    feedback: Optional[Dict[str, str]]


# Describes what each workflow produces internally so that asset_planner
# can avoid planning duplicate assets for things the workflow already handles.
WORKFLOW_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "labeling_diagram": {
        "description": "Serper image search → Gemini Imagen generation → Gemini+SAM3 zone detection",
        "produces": ["diagram_image", "diagram_zones", "diagram_labels", "zone_groups"],
        "internal_steps": ["serper_image_search", "gemini_imagen_generation", "gemini_sam3_zone_detection"],
        "makes_redundant": ["image", "background", "diagram"],
    },
    "trace_path": {
        "description": "Diagram retrieval + path waypoint detection",
        "produces": ["diagram_image", "trace_paths", "waypoints"],
        "internal_steps": ["diagram_retrieval", "path_detection"],
        "makes_redundant": ["image", "background", "diagram"],
    },
    "sequence_items": {
        "description": "Sequence item generation from domain knowledge",
        "produces": ["sequence_items"],
        "internal_steps": ["sequence_generation"],
        "makes_redundant": [],
    },
    "comparison_diagrams": {
        "description": "Multiple diagram retrieval for comparison mechanics",
        "produces": ["comparison_images", "comparison_zones"],
        "internal_steps": ["multi_diagram_retrieval", "comparison_zone_detection"],
        "makes_redundant": ["image", "background", "diagram"],
    },
    "sorting": {
        "description": "Sorting category and item generation",
        "produces": ["sorting_categories", "sorting_items"],
        "internal_steps": ["sorting_generation"],
        "makes_redundant": [],
    },
    "memory_match": {
        "description": "Memory match pair generation",
        "produces": ["memory_pairs"],
        "internal_steps": ["pair_generation"],
        "makes_redundant": [],
    },
    "branching_scenario": {
        "description": "Branching scenario node/choice generation",
        "produces": ["branching_nodes", "branching_choices"],
        "internal_steps": ["scenario_generation"],
        "makes_redundant": [],
    },
}
