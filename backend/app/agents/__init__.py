"""
GamED.AI v2 Agents Module

This module provides the LangGraph-based agent system for educational game generation.

Core Agents:
- InputEnhancer: Extracts pedagogical context (Bloom's level, learning objectives)
- DomainKnowledgeRetriever: Web search for canonical labels (Serper API)
- Router: Selects optimal game template with confidence scoring
- GamePlanner: Generates game mechanics and scoring rubrics
- SceneGenerator: Plans visual assets and interactions
- BlueprintGenerator: Produces template-specific JSON blueprints
- BlueprintValidator: Validates blueprints (schema, semantic, pedagogical)
- CodeGenerator: Generates React components for stub templates
- CodeVerifier: Docker sandbox verification
- AssetGenerator: AI image generation

Label Diagram Pipeline Agents:
- DiagramImageRetriever: Searches for diagram images online (Serper Images API)
- DiagramImageSegmenter: Segments images into zones (SAM3 only, no fallback)
- DiagramZoneLabeler: Identifies labels for each zone (VLM/LLaVA)
- DiagramSpecGenerator: Generates SVG specification from blueprint
- DiagramSpecValidator: Validates SVG spec before rendering
- DiagramSvgGenerator: Renders interactive SVG from spec

Topologies:
- T0: Sequential baseline (no validation)
- T1: Sequential with validators (default)
- T2: Actor-Critic (separate evaluator)
- T3: Hierarchical supervisor
- T4: Self-Refine (same model critiques)
- T5: Multi-Agent Debate
- T6: DAG Parallel
- T7: Reflection with Memory
"""

# Suppress Pydantic V1 deprecation warnings for Python 3.14+
import warnings
warnings.filterwarnings("ignore", message=".*Pydantic V1.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*pydantic.v1.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*Core Pydantic V1.*", category=UserWarning)

from app.agents.state import (
    AgentState,
    PedagogicalContext,
    TemplateSelection,
    GamePlan,
    SceneData,
    StoryData,  # Legacy
    ValidationResult,
    HumanReviewRequest,
    create_initial_state
)

from app.agents.graph import (
    create_game_generation_graph,
    compile_graph_with_memory,
    get_compiled_graph,
    run_game_generation
)

from app.agents.input_enhancer import (
    input_enhancer_agent,
    validate_pedagogical_context,
    BLOOM_LEVELS,
    SUBJECTS
)

from app.agents.router import (
    router_agent,
    validate_routing_decision,
    get_template_metadata,
    get_production_ready_templates,
    get_all_templates,
    TEMPLATE_REGISTRY
)

from app.agents.game_planner import (
    game_planner_agent,
    validate_game_plan,
    TEMPLATE_MECHANICS
)

from app.agents.scene_generator import (
    scene_generator_agent,
    validate_scene_data
)

# Label Diagram Pipeline Agents
from app.agents.domain_knowledge_retriever import (
    domain_knowledge_retriever_agent
)
from app.agents.diagram_image_retriever import (
    diagram_image_retriever_agent
)
from app.agents.image_label_remover import (
    image_label_remover_agent
)
from app.agents.sam3_prompt_generator import (
    sam3_prompt_generator_agent
)
from app.agents.diagram_image_segmenter import (
    diagram_image_segmenter_agent
)
from app.agents.diagram_zone_labeler import (
    diagram_zone_labeler_agent
)
from app.agents.diagram_spec_generator import (
    diagram_spec_generator_agent
)
from app.agents.diagram_svg_generator import (
    diagram_svg_generator_agent
)

from app.agents.story_generator import (
    story_generator_agent,  # Legacy
    validate_story_data,  # Legacy
    SUBJECT_THEMES
)

from app.agents.blueprint_generator import (
    blueprint_generator_agent,
    validate_blueprint,
    TEMPLATE_SCHEMAS
)

from app.agents.topologies import (
    TopologyType,
    TopologyConfig,
    TopologyMetrics,
    create_topology,
    get_topology_description,
    list_all_topologies
)

from app.agents.evaluation import (
    TestCase,
    EvaluationResult,
    BenchmarkReport,
    LLMJudge,
    TopologyBenchmark,
    SAMPLE_TEST_CASES
)

__all__ = [
    # State
    "AgentState",
    "PedagogicalContext",
    "TemplateSelection",
    "GamePlan",
    "SceneData",
    "StoryData",  # Legacy
    "ValidationResult",
    "HumanReviewRequest",
    "create_initial_state",

    # Graph
    "create_game_generation_graph",
    "compile_graph_with_memory",
    "get_compiled_graph",
    "run_game_generation",

    # Core Agents
    "input_enhancer_agent",
    "router_agent",
    "game_planner_agent",
    "scene_generator_agent",
    "story_generator_agent",  # Legacy
    "blueprint_generator_agent",

    # Label Diagram Pipeline Agents
    "domain_knowledge_retriever_agent",
    "diagram_image_retriever_agent",
    "image_label_remover_agent",
    "sam3_prompt_generator_agent",
    "diagram_image_segmenter_agent",
    "diagram_zone_labeler_agent",
    "diagram_spec_generator_agent",
    "diagram_svg_generator_agent",

    # Validation
    "validate_pedagogical_context",
    "validate_routing_decision",
    "validate_game_plan",
    "validate_scene_data",
    "validate_story_data",  # Legacy
    "validate_blueprint",

    # Template utilities
    "get_template_metadata",
    "get_production_ready_templates",
    "get_all_templates",
    "TEMPLATE_REGISTRY",
    "TEMPLATE_MECHANICS",
    "TEMPLATE_SCHEMAS",
    "SUBJECT_THEMES",
    "BLOOM_LEVELS",
    "SUBJECTS",

    # Topologies
    "TopologyType",
    "TopologyConfig",
    "TopologyMetrics",
    "create_topology",
    "get_topology_description",
    "list_all_topologies",

    # Evaluation
    "TestCase",
    "EvaluationResult",
    "BenchmarkReport",
    "LLMJudge",
    "TopologyBenchmark",
    "SAMPLE_TEST_CASES"
]
