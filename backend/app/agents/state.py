"""LangGraph State Schema for Game Generation Pipeline"""
from typing import TypedDict, List, Dict, Optional, Literal, Any, Annotated
from datetime import datetime

# Import schemas for multi-scene, multi-mechanic support
from app.agents.schemas.game_plan_schemas import (
    ExtendedGamePlan, SceneBreakdown, ModeTransition, SceneTransition
)


# ==========================================================================
# ENTITY REGISTRY TYPES (Phase 3: Entity Relationship Model)
# ==========================================================================

class ZoneEntity(TypedDict, total=False):
    """
    A zone entity representing a clickable/interactive region in a diagram.

    Zones are the primary unit of interaction in label diagram games.
    They can have parent-child relationships for hierarchical structures.
    """
    id: str  # Unique zone identifier, e.g., "zone_stigma"
    label: str  # Display label for the zone, e.g., "Stigma"
    shape: str  # "circle" | "polygon" | "rect"
    coordinates: Dict[str, Any]  # Shape-specific coords (x, y, radius for circle; points for polygon)
    parent_zone_id: Optional[str]  # For hierarchical zones (e.g., "zone_pistil" is parent of "zone_stigma")
    scene_number: int  # Which scene this zone belongs to (for multi-scene games)

    # Optional metadata
    confidence: Optional[float]  # Detection confidence (0.0-1.0)
    source: Optional[str]  # Detection source (e.g., "gemini_vlm", "leader_line_endpoint")
    hierarchy_level: Optional[int]  # 1=main, 2=sub-part, 3+=nested
    hint: Optional[str]  # Educational hint for this zone
    difficulty: Optional[int]  # 1=easy, 2=moderate, 3=hard

    # Multi-mechanic properties
    mechanic_roles: Optional[Dict[str, str]]  # {"drag_drop": "target", "trace_path": "waypoint"}
    interaction_types: Optional[List[str]]  # ["drag_drop", "trace_path"]


class AssetEntity(TypedDict, total=False):
    """
    An asset entity representing a media resource used in the game.

    Assets include images, animations, sprites, audio, etc.
    They can be generated, retrieved from web, or static/cached.
    """
    id: str  # Unique asset identifier, e.g., "main_diagram", "hint_animation_stigma"
    type: str  # "image" | "animation" | "sprite" | "audio" | "css_animation" | "gif"
    source: str  # "generated" | "retrieved" | "static" | "cached"
    url: Optional[str]  # URL if retrieved from web
    local_path: Optional[str]  # Local file path if generated/cached
    generation_params: Optional[Dict[str, Any]]  # Parameters used for generation

    # Optional metadata
    dimensions: Optional[Dict[str, int]]  # {"width": 800, "height": 600}
    format: Optional[str]  # "png" | "svg" | "gif" | "mp3"
    priority: Optional[int]  # Generation priority (1=high, 2=medium, 3=low)
    placement: Optional[str]  # "background" | "overlay" | "foreground"


class InteractionEntity(TypedDict, total=False):
    """
    An interaction entity defining user interaction behavior.

    Interactions link zones to assets and define game mechanics.
    They specify triggers, targets, and feedback.
    """
    id: str  # Unique interaction identifier, e.g., "drag_label_stigma"
    type: str  # "drag_drop" | "click" | "hover" | "sequence" | "reveal"
    trigger: str  # "on_correct" | "on_reveal" | "on_hover" | "on_click" | "on_drag"
    target_zone_id: str  # The zone this interaction targets
    animation_id: Optional[str]  # Animation asset to play on trigger
    feedback: Dict[str, str]  # {"correct": "Great job!", "incorrect": "Try again"}

    # Optional metadata
    scoring_weight: Optional[float]  # Points multiplier for this interaction
    hint_on_fail: Optional[bool]  # Whether to show hint after failure
    max_attempts: Optional[int]  # Maximum attempts before showing answer
    reveal_order: Optional[int]  # Order in progressive reveal sequence


class EntityRegistry(TypedDict, total=False):
    """
    Central registry linking zones, assets, and interactions.

    This provides a normalized data model for entity relationships,
    similar to a relational database with foreign keys.

    Example usage:
        # Get all assets for a zone
        zone_id = "zone_stigma"
        asset_ids = registry["zone_assets"].get(zone_id, [])
        assets = [registry["assets"][aid] for aid in asset_ids]

        # Get parent zone
        parent_id = registry["zones"]["zone_stigma"].get("parent_zone_id")
        parent = registry["zones"].get(parent_id) if parent_id else None
    """
    # Entity storage (primary tables)
    zones: Dict[str, ZoneEntity]  # zone_id → zone data
    assets: Dict[str, AssetEntity]  # asset_id → asset data
    interactions: Dict[str, InteractionEntity]  # interaction_id → interaction

    # Relationship maps (foreign keys / join tables)
    zone_assets: Dict[str, List[str]]  # zone_id → [asset_ids]
    zone_interactions: Dict[str, List[str]]  # zone_id → [interaction_ids]
    asset_zones: Dict[str, List[str]]  # asset_id → [zone_ids] (reverse lookup)
    scene_zones: Dict[int, List[str]]  # scene_number → [zone_ids]

    # Multi-mechanic tracking
    mechanics_per_scene: Optional[Dict[int, List[str]]]  # {1: ["drag_drop", "trace_path"]}
    mechanic_configs: Optional[Dict[str, Dict]]  # Per-mechanic configuration
    zone_mechanic_map: Optional[Dict[str, Dict[str, str]]]  # zone_id -> mechanic -> role

    # Transition tracking
    mode_transitions: Optional[List[Dict]]  # ModeTransition objects
    scene_transitions: Optional[List[Dict]]  # SceneTransition objects


def create_empty_entity_registry() -> EntityRegistry:
    """Create an empty entity registry with initialized collections."""
    return EntityRegistry(
        zones={},
        assets={},
        interactions={},
        zone_assets={},
        zone_interactions={},
        asset_zones={},
        scene_zones={},
        # Multi-mechanic tracking
        mechanics_per_scene={},
        mechanic_configs={},
        zone_mechanic_map={},
        # Transition tracking
        mode_transitions=[],
        scene_transitions=[],
    )


def merge_retry_counts(current: Dict[str, int], update: Dict[str, int]) -> Dict[str, int]:
    """
    Reducer for retry_counts that merges updates instead of replacing.
    Takes the maximum count for each key to handle concurrent updates.
    """
    if not update:
        return current or {}
    if not current:
        return update
    result = dict(current)
    for key, value in update.items():
        result[key] = max(result.get(key, 0), value)
    return result


class PedagogicalContext(TypedDict, total=False):
    """Enhanced context with Bloom's taxonomy and learning objectives"""
    blooms_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
    blooms_justification: str
    learning_objectives: List[str]
    key_concepts: List[str]
    difficulty: Literal["beginner", "intermediate", "advanced"]
    difficulty_justification: str
    subject: str
    cross_cutting_subjects: List[str]
    common_misconceptions: List[Dict[str, str]]
    prerequisites: List[str]
    question_intent: str


class TemplateSelection(TypedDict, total=False):
    """Router agent output for template selection"""
    template_type: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    alternatives: List[Dict[str, Any]]
    bloom_alignment_score: float
    subject_fit_score: float
    interaction_fit_score: float
    is_production_ready: bool
    requires_code_generation: bool


class SequenceItemData(TypedDict, total=False):
    """Individual item in a sequence (for order/sequence mechanics)."""
    id: str
    text: str
    order_index: int
    description: Optional[str]
    connects_to: Optional[List[str]]  # For branching flows


class GameMechanic(TypedDict, total=False):
    """
    Individual game mechanic definition.

    For order/sequence mechanics, includes sequence_items with the correct ordering.
    """
    id: str
    type: str  # "drag_drop", "order", "sequence", "matching", etc.
    description: str
    interaction_type: str
    scoring_weight: float

    # Phase 0: Sequence/order mechanic fields
    sequence_items: Optional[List[SequenceItemData]]  # Items in correct order
    sequence_type: Optional[str]  # "linear", "cyclic", "branching"
    correct_order: Optional[List[str]]  # Ordered list of item IDs


class ScoringRubric(TypedDict):
    """Scoring configuration for evaluation"""
    max_score: int
    partial_credit: bool
    time_bonus: bool
    hint_penalty: float
    criteria: List[Dict[str, Any]]


class HierarchyInfo(TypedDict, total=False):
    """Hierarchy detection info for INTERACTIVE_DIAGRAM progressive reveal"""
    is_hierarchical: bool
    parent_children: Dict[str, List[str]]  # Maps parent label to child labels
    recommended_mode: str  # "hierarchical" or "drag_drop"
    reveal_trigger: str  # "complete_parent", "click_expand", or "hover_reveal"


class GamePlan(TypedDict, total=False):
    """Game planner agent output"""
    learning_objectives: List[str]
    game_mechanics: List[GameMechanic]
    difficulty_progression: Dict[str, Any]
    feedback_strategy: Dict[str, Any]
    scoring_rubric: ScoringRubric
    estimated_duration_minutes: int
    prerequisite_skills: List[str]
    required_labels: Optional[List[str]]  # For INTERACTIVE_DIAGRAM: labels that must be found in image
    hierarchy_info: Optional[HierarchyInfo]  # For INTERACTIVE_DIAGRAM: hierarchical zone relationships
    scene_breakdown: Optional[List[Dict[str, Any]]]  # Per-scene breakdown with mechanics and asset_needs
    recommended_mode: Optional[str]  # Primary interaction mode
    interaction_features: Optional[Dict[str, Any]]  # Multi-mode config


class SceneData(TypedDict):
    """Scene generator agent output - visual asset planning and interactions"""
    visual_theme: str  # Theme/metaphor for asset design (e.g., "detective", "laboratory")
    scene_title: str  # Title for the scene/game
    required_assets: List[Dict[str, Any]]  # Assets needed: images, animations, UI components
    asset_interactions: List[Dict[str, Any]]  # How assets interact and respond
    layout_specification: Dict[str, Any]  # Component positioning, sizing, layout
    animation_sequences: List[Dict[str, Any]]  # Animation flows and transitions
    state_transitions: List[Dict[str, Any]]  # Visual state changes during gameplay
    visual_flow: List[Dict[str, Any]]  # How scene progresses step-by-step
    minimal_context: str  # 1-2 sentence context for narrativeIntro (from visual_theme)


# Legacy StoryData kept for backward compatibility during migration
class StoryData(TypedDict):
    """Legacy story generator agent output (deprecated - use SceneData)"""
    story_title: str
    story_context: str
    visual_metaphor: str
    narrative_hook: str
    character_name: Optional[str]
    setting_description: str
    question_flow: List[Dict[str, Any]]
    conclusion_text: str


class ValidationResult(TypedDict):
    """Validation output from validator agents"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    validated_at: str


class HumanReviewRequest(TypedDict):
    """Request for human review"""
    review_type: Literal["template_routing", "blueprint_validation", "code_review", "quality_gate"]
    artifact_type: str
    artifact_data: Dict[str, Any]
    reason: str
    suggested_action: str


class AgentExecution(TypedDict):
    """Record of individual agent execution"""
    agent_name: str
    started_at: str
    completed_at: Optional[str]
    status: Literal["running", "completed", "failed"]
    tokens_used: int
    error_message: Optional[str]


class HierarchicalRelationship(TypedDict):
    """Parent-child relationship between labels in a diagram."""
    parent: str
    children: List[str]
    relationship_type: str  # "contains", "composed_of", "subdivided_into"


class SequenceFlowDataState(TypedDict, total=False):
    """Sequence/flow data for order-based mechanics."""
    flow_type: str  # "linear", "cyclic", "branching"
    sequence_items: List[Dict[str, Any]]  # List of sequence items with id, text, order_index
    flow_description: Optional[str]
    source_url: Optional[str]


class ContentCharacteristicsState(TypedDict, total=False):
    """Content characteristics from query intent detection."""
    needs_labels: bool
    needs_sequence: bool
    needs_comparison: bool
    sequence_type: Optional[str]


class DomainKnowledge(TypedDict, total=False):
    """Retrieved canonical domain knowledge from web search."""
    query: str
    canonical_labels: List[str]
    acceptable_variants: Dict[str, List[str]]
    hierarchical_relationships: Optional[List[HierarchicalRelationship]]  # Parent-child relationships
    sources: List[Dict[str, str]]
    retrieved_at: str
    # Phase 0: Sequence/flow data for multi-mechanic support
    sequence_flow_data: Optional[SequenceFlowDataState]
    content_characteristics: Optional[ContentCharacteristicsState]
    # Fields present in Pydantic DomainKnowledge schema but missing here
    query_intent: Optional[str]  # Intent classification from DK retriever
    suggested_reveal_order: Optional[List[str]]  # Optimal label reveal order
    scene_hints: Optional[List[str]]  # Hints for multi-scene structure
    label_descriptions: Optional[Dict[str, str]]  # label -> functional description


class AgentState(TypedDict):
    """Main LangGraph state for game generation pipeline"""
    # Input
    question_id: str
    question_text: str
    question_options: Optional[List[str]]

    # Enhanced Input (from Input Enhancer)
    pedagogical_context: Optional[PedagogicalContext]

    # Routing (from Router Agent)
    template_selection: Optional[TemplateSelection]
    routing_confidence: float
    routing_requires_human_review: bool

    # Domain Knowledge (from web search)
    domain_knowledge: Optional[DomainKnowledge]

    # Diagram image + segmentation pipeline
    diagram_image: Optional[Dict[str, Any]]
    sam3_prompts: Optional[Dict[str, str]]  # Label -> SAM3 prompt (from VLM prompt generator)
    diagram_segments: Optional[Dict[str, Any]]
    diagram_zones: Optional[List[Dict[str, Any]]]
    diagram_labels: Optional[List[Dict[str, Any]]]
    zone_groups: Optional[List[Dict[str, Any]]]  # Hierarchical zone groups from detector

    # Image cleaning (label removal via inpainting)
    cleaned_image_path: Optional[str]
    removed_labels: Optional[List[str]]

    # Generated diagram (from diagram_image_generator)
    generated_diagram_path: Optional[str]

    # Qwen annotation detection (experimental pipeline)
    annotation_elements: Optional[List[Dict[str, Any]]]  # Text boxes + leader lines from qwen_annotation_detector

    # Image label classification (for unlabeled diagram fast path)
    image_classification: Optional[Dict[str, Any]]  # {"is_labeled": bool, "confidence": float, "text_count": int, "method": str}

    # Image search retry tracking
    retry_image_search: bool
    image_search_attempts: int
    max_image_attempts: int

    # Generation Artifacts
    game_plan: Optional[GamePlan]
    scene_data: Optional[SceneData]  # Visual scene planning (assets, interactions, layout)
    story_data: Optional[StoryData]  # Legacy - kept for backward compatibility
    blueprint: Optional[Dict[str, Any]]  # GameBlueprint JSON
    generated_code: Optional[str]  # For stub templates
    asset_urls: Optional[Dict[str, str]]
    diagram_svg: Optional[str]
    diagram_spec: Optional[Dict[str, Any]]

    # Hierarchical Scene Generation (3-stage approach)
    scene_structure: Optional[Dict[str, Any]]  # Stage 1: visual theme, layout, regions
    scene_assets: Optional[Dict[str, Any]]  # Stage 2: assets, layout specification
    scene_interactions: Optional[Dict[str, Any]]  # Stage 3: interactions, animations

    # Multi-Scene Support (Preset 2 - Advanced Label Diagram)
    # Scene sequencer output
    needs_multi_scene: Optional[bool]  # Whether multi-scene game is needed
    num_scenes: Optional[int]  # Number of scenes planned
    scene_progression_type: Optional[str]  # linear | zoom_in | depth_first | branching
    scene_breakdown: Optional[List[Dict[str, Any]]]  # List of scene definitions
    game_sequence: Optional[Dict[str, Any]]  # Complete multi-scene game sequence

    # Per-scene diagram/zone data (keyed by scene_number)
    scene_diagrams: Optional[Dict[int, Dict[str, Any]]]  # scene_number → diagram info
    scene_zones: Optional[Dict[int, List[Dict[str, Any]]]]  # scene_number → zones
    scene_labels: Optional[Dict[int, List[Dict[str, Any]]]]  # scene_number → labels

    # Multi-scene orchestrator output (content per scene)
    all_scene_data: Optional[Dict[int, Dict[str, Any]]]  # scene_number → {structure, assets, interactions, scene_data}

    # HAD v3: Per-scene images and zone groups
    scene_images: Optional[Dict[int, str]]  # scene_number → image path
    scene_zone_groups: Optional[Dict[int, List[Dict[str, Any]]]]  # scene_number → zone groups
    current_scene_number: Optional[int]  # Currently processing scene

    # HAD v3: Zone collision resolution metadata
    zone_collision_metadata: Optional[Dict[str, Any]]  # Resolution details from zone_collision_resolver

    # HAD v3: Query intent from domain knowledge
    query_intent: Optional[Dict[str, Any]]  # {learning_focus, depth_preference, suggested_progression}
    suggested_reveal_order: Optional[List[str]]  # Optimal label reveal order

    # HAD v3: Temporal Intelligence (Petri Net-inspired constraints)
    temporal_constraints: Optional[List[Dict[str, Any]]]  # List of TemporalConstraint dicts
    motion_paths: Optional[List[Dict[str, Any]]]  # List of MotionPath dicts

    # ==========================================================================
    # AGENTIC PRESET 2 FIELDS (advanced_interactive_diagram)
    # ==========================================================================

    # Diagram Type Classification (from diagram_type_classifier agent)
    diagram_type: Optional[str]  # anatomy, process, comparison, timeline, spatial, abstract
    diagram_type_config: Optional[Dict[str, Any]]  # {zone_strategy, keywords, search_suffix, default_interaction}

    # Diagram Analysis (from diagram_analyzer agent - Preset 2)
    diagram_analysis: Optional[Dict[str, Any]]  # {content_type, key_structures, relationships, zone_strategy, reasoning}

    # Game Design (from game_designer agent - Preset 2)
    game_design: Optional[Dict[str, Any]]  # {learning_outcomes, scenes[], scene_structure, reasoning}

    # Interaction Design (from interaction_designer agent - Agentic Interaction Design)
    interaction_designs: Optional[List[Dict[str, Any]]]  # Per-scene interaction designs list
    interaction_design: Optional[Dict[str, Any]]  # Backward compat: first scene's design {primary_interaction_mode, secondary_modes, mode_transitions, scoring_strategy, animation_config}

    # Interaction Validation (from interaction_validator agent)
    interaction_validation: Optional[Dict[str, Any]]  # {is_valid, issues, auto_fixes, validated_design}

    # HAD v3: Design metadata and trace (from game_designer/game_orchestrator)
    design_metadata: Optional[Dict[str, Any]]  # {unified_call, designer, model, duration_ms, etc.}
    design_trace: Optional[List[Dict[str, Any]]]  # ReAct trace for UI visualization

    # ==========================================================================
    # V3 PIPELINE FIELDS
    # ==========================================================================
    # Phase 1: Game Design
    game_design_v3: Optional[Dict[str, Any]]  # GameDesignV3 (slimmed) from game_designer_v3
    design_validation_v3: Optional[Dict[str, Any]]  # {passed, score, issues} from design_validator
    _v3_design_retries: Optional[int]  # Retry counter for game_designer_v3 ↔ design_validator loop

    # Phase 2: Scene Architecture
    scene_specs_v3: Optional[List[Dict[str, Any]]]  # Per-scene zone/mechanic specs from scene_architect_v3
    scene_validation_v3: Optional[Dict[str, Any]]  # Scene validator result
    _v3_scene_retries: Optional[int]  # Retry counter for scene_architect_v3 ↔ scene_validator loop

    # Phase 3: Interaction Design
    interaction_specs_v3: Optional[List[Dict[str, Any]]]  # Per-scene scoring/feedback from interaction_designer_v3
    interaction_validation_v3: Optional[Dict[str, Any]]  # Interaction validator result
    _v3_interaction_retries: Optional[int]  # Retry counter for interaction_designer_v3 ↔ interaction_validator loop

    # Phase 4: Asset Generation
    generated_assets_v3: Optional[Dict[str, Any]]  # Per-scene assets from asset_generator_v3

    # Per-mechanic asset tracking (populated by asset_generator_v3)
    sequence_item_images: Optional[Dict[str, str]]  # item_id -> image_url
    sorting_item_images: Optional[Dict[str, str]]   # item_id -> image_url
    sorting_category_icons: Optional[Dict[str, str]]  # category_id -> icon_url
    memory_card_images: Optional[Dict[str, str]]     # pair_id -> image_url
    diagram_crop_regions: Optional[Dict[str, Dict]]  # zone_id -> {x, y, width, height}

    # Legacy v3 fields (kept for backward compat during migration)
    asset_graph_v3: Optional[Dict[str, Any]]  # AssetGraph — no longer used by new pipeline
    asset_manifest_v3: Optional[Dict[str, Any]]  # AssetManifest — no longer used by new pipeline

    # ==========================================================================
    # ASSET PIPELINE FIELDS
    # ==========================================================================

    # Asset Planning (from asset_planner)
    planned_assets: Optional[List[Dict[str, Any]]]  # [{asset_id, type, method, params, reasoning}]

    # Generated Assets (from asset_generator_orchestrator)
    generated_assets: Optional[Dict[str, Any]]  # {asset_id: {url, local_path, format, success}}

    # Asset Validation (from asset_validator)
    asset_validation: Optional[Dict[str, Any]]  # {all_valid, assets: [{id, valid, issues}]}
    assets_valid: Optional[bool]  # True if all critical assets passed validation
    validated_assets: Optional[List[Dict[str, Any]]]  # Assets with validation_status attached
    validation_errors: Optional[List[str]]  # List of validation error strings

    # ==========================================================================
    # ENTITY REGISTRY (Phase 3: Entity Relationship Model)
    # ==========================================================================

    # Central registry linking zones, assets, and interactions
    # Provides normalized data model for entity relationships
    entity_registry: Optional[EntityRegistry]

    # ==========================================================================
    # WORKFLOW EXECUTION (Multi-mechanic support)
    # ==========================================================================

    # Workflow execution plan from game_planner
    workflow_execution_plan: Optional[List[Dict]]  # Workflow execution steps
    workflow_generated_assets: Optional[Dict[str, Dict]]  # Results from workflows keyed by asset_id

    # ==========================================================================
    # RUNTIME CONTEXT
    # ==========================================================================

    # Pipeline preset for conditional routing
    _pipeline_preset: Optional[str]  # "interactive_diagram_hierarchical" or "advanced_interactive_diagram"

    # AI generation budget tracking
    _ai_images_generated: Optional[int]  # Tracks nanobanana/AI image usage

    # Validation State
    validation_results: Dict[str, ValidationResult]
    current_validation_errors: List[str]

    # Retry Management
    retry_counts: Annotated[Dict[str, int], merge_retry_counts]  # Agent name -> count (with merge reducer)
    max_retries: int  # Default max retries per agent

    # Human-in-the-Loop
    pending_human_review: Optional[HumanReviewRequest]
    human_feedback: Optional[str]
    human_review_completed: bool

    # Execution Tracking
    current_agent: str
    agent_history: List[AgentExecution]
    started_at: str
    last_updated_at: str

    # Observability instrumentation
    _run_id: Optional[str]  # Pipeline run ID for stage tracking
    _stage_order: int  # Current stage order counter

    # Internal routing flags for conditional post-blueprint routing (Phase 6)
    # These flags determine what post-processing stages are needed
    _needs_diagram_spec: Optional[bool]  # True if template requires diagram spec generation
    _needs_asset_generation: Optional[bool]  # True if game needs asset generation pipeline
    _skip_asset_pipeline: Optional[bool]  # True if asset pipeline should be skipped entirely

    # Final Output
    final_visualization_id: Optional[str]
    generation_complete: bool
    error_message: Optional[str]
    output_metadata: Optional[Dict[str, Any]]  # {blueprint_retry_count, validation_score, stage_durations, etc.}


def create_initial_state(
    question_id: str,
    question_text: str,
    question_options: Optional[List[str]] = None
) -> AgentState:
    """Create initial state for a new game generation"""
    now = datetime.utcnow().isoformat()
    return AgentState(
        question_id=question_id,
        question_text=question_text,
        question_options=question_options,
        pedagogical_context=None,
        template_selection=None,
        routing_confidence=0.0,
        routing_requires_human_review=False,
        domain_knowledge=None,
        diagram_image=None,
        diagram_segments=None,
        sam3_prompts=None,
        diagram_zones=None,
        diagram_labels=None,
        zone_groups=None,
        cleaned_image_path=None,
        removed_labels=None,
        generated_diagram_path=None,
        annotation_elements=None,
        image_classification=None,
        retry_image_search=False,
        image_search_attempts=0,
        max_image_attempts=3,
        game_plan=None,
        scene_data=None,
        story_data=None,  # Legacy
        blueprint=None,
        generated_code=None,
        asset_urls=None,
        diagram_svg=None,
        diagram_spec=None,
        # Hierarchical scene generation
        scene_structure=None,
        scene_assets=None,
        scene_interactions=None,
        # Multi-scene support (Preset 2)
        needs_multi_scene=None,
        num_scenes=None,
        scene_progression_type=None,
        scene_breakdown=None,
        game_sequence=None,
        scene_diagrams=None,
        scene_zones=None,
        scene_labels=None,
        # HAD v3: Per-scene images and zone groups
        scene_images=None,
        scene_zone_groups=None,
        current_scene_number=None,
        # HAD v3: Zone collision resolution
        zone_collision_metadata=None,
        # HAD v3: Query intent
        query_intent=None,
        suggested_reveal_order=None,
        # HAD v3: Temporal Intelligence
        temporal_constraints=None,
        motion_paths=None,
        # Agentic Preset 2 fields
        diagram_type=None,
        diagram_type_config=None,
        diagram_analysis=None,
        game_design=None,
        # Agentic Interaction Design
        interaction_designs=None,  # Per-scene interaction designs
        interaction_design=None,  # Backward compat
        interaction_validation=None,
        # HAD v3: Design metadata and trace
        design_metadata=None,
        design_trace=None,
        # V3 pipeline fields
        game_design_v3=None,
        design_validation_v3=None,
        _v3_design_retries=0,
        scene_specs_v3=None,
        scene_validation_v3=None,
        _v3_scene_retries=0,
        interaction_specs_v3=None,
        interaction_validation_v3=None,
        _v3_interaction_retries=0,
        generated_assets_v3=None,
        sequence_item_images=None,
        sorting_item_images=None,
        sorting_category_icons=None,
        memory_card_images=None,
        diagram_crop_regions=None,
        asset_graph_v3=None,
        asset_manifest_v3=None,
        # Asset pipeline fields
        planned_assets=None,
        generated_assets=None,
        asset_validation=None,
        assets_valid=None,
        validated_assets=None,
        validation_errors=None,
        # Entity registry (Phase 3)
        entity_registry=None,
        # Workflow execution (multi-mechanic support)
        workflow_execution_plan=None,
        workflow_generated_assets=None,
        # Runtime context
        _pipeline_preset=None,
        _ai_images_generated=0,
        validation_results={},
        current_validation_errors=[],
        retry_counts={},
        max_retries=3,
        pending_human_review=None,
        human_feedback=None,
        human_review_completed=False,
        current_agent="input_enhancer",
        agent_history=[],
        started_at=now,
        last_updated_at=now,
        final_visualization_id=None,
        generation_complete=False,
        error_message=None,
        output_metadata=None,
        _run_id=None,
        _stage_order=0,
        # Phase 6: Conditional routing flags
        _needs_diagram_spec=None,
        _needs_asset_generation=None,
        _skip_asset_pipeline=None
    )
