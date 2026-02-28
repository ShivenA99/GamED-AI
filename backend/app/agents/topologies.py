"""
Agentic Topology Configurations for GamED.AI

This module defines different workflow topologies that can be tested
and compared for game generation quality, cost, and latency.

Pipeline Flow (T1 - Current Architecture):
    input_enhancer → domain_knowledge_retriever → router → game_planner
    → interaction_designer → interaction_validator
    → check_multi_scene
        ├─ >1 scenes → multi_scene_orchestrator (loops scene stages per-scene)
        │                → check_post_scene_needs
        └─ 1 scene  → scene_stage1 → scene_stage2 → scene_stage3
                       → check_post_scene_needs
    → should_run_asset_pipeline
        ├─ run_assets → asset_planner → asset_generator_orchestrator
        │              → asset_validator → blueprint_generator
        └─ skip_assets → blueprint_generator
    → blueprint_validator → END

NOTE: Asset pipeline runs BEFORE blueprint so that blueprint_generator can
reference actual generated asset URLs/paths in the final blueprint.

Image retrieval + zone detection are handled inside labeling_diagram_workflow
(executed by asset_generator_orchestrator), NOT as separate graph nodes.
Legacy diagram_image_retriever/generator/gemini_zone_detector are removed from T1 edges.
"""
from typing import Dict, Any, Callable, Optional, List, Literal
from dataclasses import dataclass, field
from enum import Enum
from langgraph.graph import StateGraph, END

from app.agents.state import AgentState


class TopologyType(Enum):
    """Available topology configurations"""
    T0_SEQUENTIAL = "sequential_baseline"
    T1_SEQUENTIAL_VALIDATED = "sequential_validated"
    T2_ACTOR_CRITIC = "actor_critic"
    T3_HIERARCHICAL = "hierarchical"
    T4_SELF_REFINE = "self_refine"
    T5_MULTI_AGENT_DEBATE = "multi_agent_debate"
    T6_DAG_PARALLEL = "dag_parallel"
    T7_REFLECTION_MEMORY = "reflection_memory"


@dataclass
class TopologyConfig:
    """Configuration for a topology"""
    topology_type: TopologyType
    max_iterations: int = 3
    validation_threshold: float = 0.7
    use_separate_critic: bool = False
    parallel_stages: List[str] = field(default_factory=list)
    use_memory_bank: bool = False
    debate_rounds: int = 2
    human_escalation_threshold: int = 3


@dataclass
class StageMetrics:
    """Metrics collected for each stage execution"""
    stage_name: str
    iteration: int
    tokens_input: int
    tokens_output: int
    latency_ms: int
    validation_score: float
    passed: bool
    error_message: Optional[str] = None


@dataclass
class TopologyMetrics:
    """Aggregate metrics for a topology run"""
    topology_type: TopologyType
    success: bool
    total_iterations: int
    total_tokens: int
    total_latency_ms: int
    quality_scores: Dict[str, float]
    stage_metrics: List[StageMetrics]
    human_intervention_required: bool = False


# =============================================================================
# POST-BLUEPRINT ROUTING FUNCTIONS (Phase 6: Conditional Routing)
# =============================================================================

def check_post_blueprint_needs(state: AgentState) -> dict:
    """
    Analyzes state to determine what post-processing is needed.
    Sets flags for conditional routing after blueprint validation.

    This reduces wasted compute by skipping unnecessary stages:
    - Diagram spec generation is only needed for visual templates (INTERACTIVE_DIAGRAM, SORTING_GAME)
    - Asset pipeline is only needed for templates that require generated assets

    Returns:
        Dict with routing flags:
        - _needs_diagram_spec: Whether diagram spec generation is needed
        - _needs_asset_generation: Whether asset pipeline should run
        - _skip_asset_pipeline: Whether to skip asset pipeline entirely
    """
    from datetime import datetime

    # Get template type from selection
    template_selection = state.get("template_selection", {})
    template_type = template_selection.get("template_type", "") if isinstance(template_selection, dict) else ""

    # Templates that require diagram spec generation (visual/interactive diagrams)
    diagram_spec_templates = {"INTERACTIVE_DIAGRAM", "SORTING_GAME", "MATCHING_GAME"}
    needs_diagram_spec = template_type in diagram_spec_templates

    # Templates that typically need asset generation
    # These are templates with visual components that need images/animations
    asset_templates = {"INTERACTIVE_DIAGRAM", "MATCHING_GAME", "SORTING_GAME", "SEQUENCE_BUILDER"}

    # Check for pending asset needs from scene data
    scene_assets = state.get("scene_assets", {})
    planned_assets = state.get("planned_assets", [])
    generated_assets = state.get("generated_assets", {})

    has_ungenerated_assets = False

    # Check if asset planning has already determined assets are needed
    if planned_assets:
        # Check if any planned assets haven't been generated yet
        for asset in planned_assets:
            asset_id = asset.get("asset_id") or asset.get("id")
            if asset_id and asset_id not in (generated_assets or {}):
                has_ungenerated_assets = True
                break
    elif scene_assets:
        # Fall back to checking scene_assets if no explicit planning done yet
        for asset in scene_assets.get("assets", []):
            if asset.get("source") == "generate":
                asset_id = asset.get("id")
                if asset_id and asset_id not in (generated_assets or {}):
                    has_ungenerated_assets = True
                    break

    # Determine if asset pipeline should run
    # Skip if: template doesn't need assets AND no assets are pending
    needs_asset_generation = template_type in asset_templates or has_ungenerated_assets

    # Simple templates like MCQ don't need any asset generation
    simple_templates = {"MULTIPLE_CHOICE", "TRUE_FALSE", "FILL_BLANK"}
    skip_asset_pipeline = template_type in simple_templates

    return {
        "_needs_diagram_spec": needs_diagram_spec,
        "_needs_asset_generation": needs_asset_generation,
        "_skip_asset_pipeline": skip_asset_pipeline,
        "last_updated_at": datetime.utcnow().isoformat()
    }


def route_post_blueprint(state: AgentState) -> Literal["diagram_spec", "finalize"]:
    """
    Route to appropriate post-blueprint stage based on needs analysis.

    Routing logic:
    1. If _needs_diagram_spec is True -> diagram_spec_generator
    2. Otherwise -> END (finalize)

    This prevents running unnecessary stages like diagram_spec_generator
    for non-diagram games.
    """
    needs_diagram = state.get("_needs_diagram_spec", False)

    # Check if explicit flag is set
    if needs_diagram is not None and needs_diagram:
        return "diagram_spec"

    # Fall back to template-based decision if flag not set
    template_selection = state.get("template_selection", {})
    template_type = template_selection.get("template_type", "") if isinstance(template_selection, dict) else ""

    # Templates that require diagram spec
    diagram_spec_templates = {"INTERACTIVE_DIAGRAM", "SORTING_GAME", "MATCHING_GAME"}
    if template_type in diagram_spec_templates:
        return "diagram_spec"

    # Simple templates skip straight to end
    return "finalize"


def should_run_asset_pipeline(state: AgentState) -> Literal["run_assets", "skip_assets"]:
    """
    Check if asset pipeline should run based on template type and state.

    This is used before the asset_planner node to skip the entire asset
    pipeline for templates that don't need generated assets.

    Returns:
        "run_assets" - Run the full asset pipeline
        "skip_assets" - Skip to blueprint generation directly
    """
    template_selection = state.get("template_selection", {})
    template_type = template_selection.get("template_type", "") if isinstance(template_selection, dict) else ""

    # Templates that typically need asset generation
    asset_templates = {"INTERACTIVE_DIAGRAM", "MATCHING_GAME", "SORTING_GAME", "SEQUENCE_BUILDER"}

    # Check explicit skip flag
    skip_flag = state.get("_skip_asset_pipeline", False)
    if skip_flag:
        return "skip_assets"

    if template_type in asset_templates:
        return "run_assets"

    # Also check if scene planning explicitly requested assets
    scene_assets = state.get("scene_assets", {})
    if scene_assets and scene_assets.get("assets"):
        for asset in scene_assets.get("assets", []):
            if asset.get("source") == "generate":
                return "run_assets"

    return "skip_assets"


def should_run_diagram_spec(state: AgentState) -> Literal["run_diagram_spec", "skip_diagram_spec"]:
    """
    Check if diagram spec generation should run.

    Diagram spec is only needed for visual templates that display diagrams:
    - INTERACTIVE_DIAGRAM: Interactive labeling diagrams
    - SORTING_GAME: Visual sorting with items
    - MATCHING_GAME: Visual matching pairs

    Other templates (MCQ, PARAMETER_PLAYGROUND, etc.) skip this stage.
    """
    template_selection = state.get("template_selection", {})
    template_type = template_selection.get("template_type", "") if isinstance(template_selection, dict) else ""

    # Check explicit needs flag if set
    needs_diagram = state.get("_needs_diagram_spec")
    if needs_diagram is not None:
        return "run_diagram_spec" if needs_diagram else "skip_diagram_spec"

    # Fall back to template-based decision
    diagram_spec_templates = {"INTERACTIVE_DIAGRAM", "SORTING_GAME", "MATCHING_GAME"}

    if template_type in diagram_spec_templates:
        return "run_diagram_spec"

    return "skip_diagram_spec"


def should_use_workflow_mode(state: AgentState) -> Literal["workflow", "legacy"]:
    """
    Check if workflow execution mode should be used.

    Routes to workflow mode if:
    - workflow_execution_plan is populated (from asset_planner)
    - This means asset_planner detected scene_breakdown with asset_needs

    Otherwise uses legacy pipeline (individual diagram agents).

    Workflow mode:
    - asset_generator_orchestrator executes workflows (labeling_diagram_workflow, etc.)
    - Diagram agents are called FROM WITHIN workflows, not as separate graph nodes

    Legacy mode:
    - Diagram agents run as separate graph nodes (diagram_image_retriever -> gemini_zone_detector)
    - Backward compatible with existing pipelines
    """
    import logging
    logger = logging.getLogger("gamed_ai.topologies")

    workflow_plan = state.get("workflow_execution_plan", [])

    if workflow_plan and len(workflow_plan) > 0:
        logger.info(f"Using workflow mode: {len(workflow_plan)} workflow steps planned")
        return "workflow"

    logger.info("Using legacy diagram pipeline (no workflow_execution_plan)")
    return "legacy"


# =============================================================================
# VALIDATOR FUNCTIONS
# =============================================================================

async def validate_pedagogical_context(
    context: Dict[str, Any],
    config: TopologyConfig
) -> tuple[bool, float, str]:
    """Validate pedagogical context output"""
    errors = []
    score = 1.0

    required_fields = ["subject", "blooms_level", "learning_objectives"]
    for field in required_fields:
        if field not in context or not context[field]:
            errors.append(f"Missing {field}")
            score -= 0.3

    if "blooms_level" in context:
        valid_levels = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
        if context["blooms_level"] not in valid_levels:
            errors.append(f"Invalid blooms_level: {context['blooms_level']}")
            score -= 0.2

    passed = score >= config.validation_threshold
    return passed, max(0, score), "; ".join(errors) if errors else ""


async def validate_template_selection(
    selection: Dict[str, Any],
    config: TopologyConfig
) -> tuple[bool, float, str]:
    """Validate template routing output"""
    errors = []
    score = 1.0

    if "template_type" not in selection:
        errors.append("Missing template_type")
        score -= 0.5

    confidence = selection.get("confidence", 0)
    if confidence < 0.5:
        errors.append(f"Low confidence: {confidence}")
        score -= 0.3

    if "rationale" not in selection or len(selection.get("rationale", "")) < 20:
        errors.append("Missing or insufficient rationale")
        score -= 0.2

    passed = score >= config.validation_threshold
    return passed, max(0, score), "; ".join(errors) if errors else ""


async def validate_game_plan(
    plan: Dict[str, Any],
    config: TopologyConfig
) -> tuple[bool, float, str]:
    """Validate game plan output"""
    errors = []
    score = 1.0

    if "learning_objectives" not in plan or not plan["learning_objectives"]:
        errors.append("Missing learning objectives")
        score -= 0.3

    if "game_mechanics" not in plan or not plan["game_mechanics"]:
        errors.append("Missing game mechanics")
        score -= 0.3

    if "scoring_rubric" not in plan:
        errors.append("Missing scoring rubric")
        score -= 0.2

    passed = score >= config.validation_threshold
    return passed, max(0, score), "; ".join(errors) if errors else ""


async def validate_scene(
    scene: Dict[str, Any],
    config: TopologyConfig
) -> tuple[bool, float, str]:
    """Validate scene output"""
    errors = []
    score = 1.0

    required = ["visual_theme", "required_assets", "layout_specification"]
    for field in required:
        if field not in scene or not scene[field]:
            errors.append(f"Missing {field}")
            score -= 0.3

    if "required_assets" in scene:
        if not isinstance(scene["required_assets"], list):
            errors.append("required_assets must be a list")
            score -= 0.2
        elif len(scene["required_assets"]) == 0:
            errors.append("required_assets is empty")
            score -= 0.2
        else:
            # Validate each asset has required fields
            for i, asset in enumerate(scene["required_assets"]):
                if not asset.get("id"):
                    errors.append(f"Asset {i} missing id")
                    score -= 0.1
                if not asset.get("type"):
                    errors.append(f"Asset {i} missing type")
                    score -= 0.1

    passed = score >= config.validation_threshold
    return passed, max(0, score), "; ".join(errors) if errors else ""


# Legacy validate_story kept for backward compatibility
async def validate_story(
    story: Dict[str, Any],
    config: TopologyConfig
) -> tuple[bool, float, str]:
    """Validate story output (legacy - use validate_scene)"""
    errors = []
    score = 1.0

    required = ["story_title", "story_context", "question_flow"]
    for field in required:
        if field not in story or not story[field]:
            errors.append(f"Missing {field}")
            score -= 0.25

    if "question_flow" in story:
        if not isinstance(story["question_flow"], list):
            errors.append("question_flow must be a list")
            score -= 0.2
        elif len(story["question_flow"]) == 0:
            errors.append("question_flow is empty")
            score -= 0.2

    passed = score >= config.validation_threshold
    return passed, max(0, score), "; ".join(errors) if errors else ""


async def validate_blueprint(
    blueprint: Dict[str, Any],
    template_type: str,
    config: TopologyConfig
) -> tuple[bool, float, str]:
    """Validate blueprint against template schema"""
    errors = []
    score = 1.0

    # Check templateType matches
    if blueprint.get("templateType") != template_type:
        errors.append(f"templateType mismatch: expected {template_type}")
        score -= 0.3

    # Check required fields
    required = ["title", "narrativeIntro", "tasks"]
    for field in required:
        if field not in blueprint:
            errors.append(f"Missing {field}")
            score -= 0.2

    # Check tasks have required structure
    if "tasks" in blueprint:
        for i, task in enumerate(blueprint["tasks"]):
            if not isinstance(task, dict):
                errors.append(f"Task {i} is not a dict")
                score -= 0.1
            elif "id" not in task or "questionText" not in task:
                errors.append(f"Task {i} missing id or questionText")
                score -= 0.1

    # Check for correctAnswer in tasks
    if "tasks" in blueprint:
        for task in blueprint["tasks"]:
            if "options" in task and "correctAnswer" not in task:
                errors.append(f"Task {task.get('id')} has options but no correctAnswer")
                score -= 0.15

    passed = score >= config.validation_threshold
    return passed, max(0, score), "; ".join(errors) if errors else ""


# =============================================================================
# CRITIC FUNCTIONS (for Actor-Critic and Self-Refine)
# =============================================================================

CRITIC_PROMPT_TEMPLATE = """
You are an expert educational content reviewer. Evaluate the following {artifact_type}
for a game-based learning platform.

## Artifact to Review:
{artifact}

## Original Question:
{question}

## Evaluation Criteria:
1. **Pedagogical Alignment** (0-10): Does it support the learning objectives?
2. **Completeness** (0-10): Are all required elements present?
3. **Coherence** (0-10): Is it logically consistent and clear?
4. **Engagement** (0-10): Will it create an engaging learning experience?

## Your Response:
Provide scores for each criterion and an overall assessment.
If the artifact needs improvement, provide specific, actionable feedback.
If acceptable, respond with "APPROVED" at the end.

Format:
- Pedagogical: [score]/10 - [brief reason]
- Completeness: [score]/10 - [brief reason]
- Coherence: [score]/10 - [brief reason]
- Engagement: [score]/10 - [brief reason]
- Overall: [APPROVED or NEEDS_REVISION]
- Feedback: [specific improvement suggestions if needed]
"""


async def run_llm_critic(
    artifact: Dict[str, Any],
    artifact_type: str,
    question: str,
    llm_service: Any
) -> tuple[bool, float, str]:
    """Run LLM-based critic on an artifact"""
    import json

    prompt = CRITIC_PROMPT_TEMPLATE.format(
        artifact_type=artifact_type,
        artifact=json.dumps(artifact, indent=2)[:3000],  # Truncate for context
        question=question
    )

    # Call LLM
    response = await llm_service.generate(prompt)

    # Parse response
    approved = "APPROVED" in response.upper()

    # Extract scores (simplified parsing)
    scores = []
    for line in response.split("\n"):
        if "/10" in line:
            try:
                score = int(line.split("/10")[0].split()[-1])
                scores.append(score)
            except (ValueError, IndexError):
                # Skip lines that don't parse as expected score format
                pass

    avg_score = sum(scores) / len(scores) if scores else 5.0
    normalized_score = avg_score / 10.0

    # Extract feedback
    feedback = ""
    if "Feedback:" in response:
        feedback = response.split("Feedback:")[-1].strip()

    return approved, normalized_score, feedback


# =============================================================================
# TOPOLOGY BUILDERS
# =============================================================================

def build_t0_sequential(config: TopologyConfig) -> StateGraph:
    """T0: Sequential baseline (no validation)"""
    from app.agents.graph import (
        input_enhancer_agent,
        router_agent,
        game_planner_agent,
        scene_generator_agent,
        blueprint_generator_agent,
        diagram_spec_generator_agent,
        diagram_svg_generator_agent,
    )

    graph = StateGraph(AgentState)

    graph.add_node("input_enhancer", input_enhancer_agent)
    graph.add_node("router", router_agent)
    graph.add_node("game_planner", game_planner_agent)
    graph.add_node("scene_generator", scene_generator_agent)
    graph.add_node("blueprint_generator", blueprint_generator_agent)
    graph.add_node("diagram_spec_generator", diagram_spec_generator_agent)
    graph.add_node("diagram_svg_generator", diagram_svg_generator_agent)
    # asset_generator removed - diagram_svg_generator now sets generation_complete

    graph.set_entry_point("input_enhancer")
    graph.add_edge("input_enhancer", "router")
    graph.add_edge("router", "game_planner")
    graph.add_edge("game_planner", "scene_generator")
    graph.add_edge("scene_generator", "blueprint_generator")
    graph.add_edge("blueprint_generator", "diagram_spec_generator")
    graph.add_edge("diagram_spec_generator", "diagram_svg_generator")
    graph.add_edge("diagram_svg_generator", END)  # Direct to END (asset_generator removed)

    return graph


def build_t1_sequential_validated(config: TopologyConfig) -> StateGraph:
    """
    T1: Sequential with validators - Simplified pipeline with retry loops.

    PHASE 4 ADDITION: Iteration Loops (Retry with Feedback)
    ========================================================
    This topology implements three retry loops with proper termination criteria:

    1. ASSET RETRY LOOP (asset_validator -> asset_generator_orchestrator)
       - Termination: all_valid=True OR retry_count >= 2 OR skip (graceful degradation)
       - Feedback: failed asset IDs passed to orchestrator for re-generation

    2. BLUEPRINT RETRY LOOP (blueprint_validator -> blueprint_generator)
       - Termination: is_valid=True OR retry_count >= max_retries OR human_review
       - Feedback: validation errors in state.current_validation_errors

    3. DIAGRAM SPEC RETRY LOOP (diagram_spec_validator -> diagram_spec_generator)
       - Termination: is_valid=True OR retry_count >= max_retries OR human_review
       - Feedback: schema/semantic errors in state.current_validation_errors

    Uses the hierarchical label diagram pipeline:
    - 3-stage scene generation: scene_stage1_structure, scene_stage2_assets, scene_stage3_interactions
    - diagram_image_retriever: Retrieves reference image from web
    - diagram_image_generator: Generates clean educational diagram (Gemini nano-banana-pro)
    - gemini_zone_detector: Detects zones using Gemini vision (gemini-3-flash-preview)
    - asset_planner: Plans all assets needed from scene data (NOT blueprint)
    - asset_generator_orchestrator: Sequential asset generation
    - asset_validator: Validates all generated assets
    - blueprint_generator: Creates final blueprint with generated asset references
    - blueprint_validator: Validates the complete blueprint

    KEY DESIGN: Asset pipeline runs BEFORE blueprint generation so that:
    1. Asset planning uses scene data and zones (not blueprint)
    2. Blueprint can reference actual generated asset URLs/paths
    3. Final blueprint is complete with all media references

    REMOVED (no longer needed since we generate clean diagrams):
    - validate_context, validate_routing, validate_plan (redundant)
    - image_label_classifier, qwen_annotation_detector, image_label_remover
    - direct_structure_locator, qwen_sam_zone_detector
    """
    from app.agents.graph import (
        input_enhancer_agent,
        router_agent,
        game_planner_agent,
        blueprint_generator_agent,
        blueprint_validator_agent,
        # PHASE 6: diagram_spec_generator_agent and diagram_svg_generator_agent removed from T1
        # They are no longer needed - frontend renders directly from blueprint
        human_review_node,
    )
    from app.agents.domain_knowledge_retriever import domain_knowledge_retriever_agent
    # Agentic interaction design
    from app.agents.interaction_designer import interaction_designer
    from app.agents.interaction_validator import interaction_validator
    # 3-stage hierarchical scene generation
    from app.agents.scene_stage1_structure import scene_stage1_structure
    from app.agents.scene_stage2_assets import scene_stage2_assets
    from app.agents.scene_stage3_interactions import scene_stage3_interactions
    # Asset generation pipeline
    from app.agents.asset_planner import asset_planner
    from app.agents.asset_generator_orchestrator import asset_generator_orchestrator
    from app.agents.asset_validator import asset_validator
    from app.agents.instrumentation import wrap_agent_with_instrumentation

    graph = StateGraph(AgentState)

    # =========================================================================
    # INPUT PROCESSING (no intermediate validators - handled internally)
    # =========================================================================
    graph.add_node("input_enhancer", wrap_agent_with_instrumentation(input_enhancer_agent, "input_enhancer"))
    graph.add_node("domain_knowledge_retriever", wrap_agent_with_instrumentation(domain_knowledge_retriever_agent, "domain_knowledge_retriever"))
    graph.add_node("router", wrap_agent_with_instrumentation(router_agent, "router"))
    graph.add_node("human_review", human_review_node)

    # =========================================================================
    # GAME PLANNING
    # =========================================================================
    graph.add_node("game_planner", wrap_agent_with_instrumentation(game_planner_agent, "game_planner"))

    # =========================================================================
    # AGENTIC INTERACTION DESIGN (NEW)
    # Replaces hardcoded BLOOMS_INTERACTION_MAPPING with LLM reasoning
    # =========================================================================
    graph.add_node("interaction_designer", wrap_agent_with_instrumentation(interaction_designer, "interaction_designer"))
    graph.add_node("interaction_validator", wrap_agent_with_instrumentation(interaction_validator, "interaction_validator"))

    # =========================================================================
    # 3-STAGE SCENE GENERATION
    # =========================================================================
    graph.add_node("scene_stage1_structure", wrap_agent_with_instrumentation(scene_stage1_structure, "scene_stage1_structure"))
    graph.add_node("scene_stage2_assets", wrap_agent_with_instrumentation(scene_stage2_assets, "scene_stage2_assets"))
    graph.add_node("scene_stage3_interactions", wrap_agent_with_instrumentation(scene_stage3_interactions, "scene_stage3_interactions"))

    # =========================================================================
    # IMAGE PIPELINE (REMOVED from T1 - handled inside labeling_diagram_workflow)
    # Legacy nodes kept for other topologies but NOT wired into T1 edges.
    # =========================================================================

    # =========================================================================
    # BLUEPRINT GENERATION WITH VALIDATION
    # =========================================================================
    graph.add_node("blueprint_generator", wrap_agent_with_instrumentation(blueprint_generator_agent, "blueprint_generator"))
    graph.add_node("blueprint_validator", blueprint_validator_agent)

    # =========================================================================
    # ASSET GENERATION PIPELINE (NEW)
    # =========================================================================
    graph.add_node("asset_planner", wrap_agent_with_instrumentation(asset_planner, "asset_planner"))
    graph.add_node("asset_generator_orchestrator", wrap_agent_with_instrumentation(asset_generator_orchestrator, "asset_generator_orchestrator"))
    graph.add_node("asset_validator", wrap_agent_with_instrumentation(asset_validator, "asset_validator"))

    # =========================================================================
    # PHASE 6: diagram_spec_generator and diagram_svg_generator REMOVED
    # =========================================================================
    # These nodes are no longer needed in T1 - frontend renders directly from
    # blueprint.zones and blueprint.labels. Keeping the imports for other topologies.
    # graph.add_node("diagram_spec_generator", ...) - REMOVED
    # graph.add_node("diagram_svg_generator", ...) - REMOVED

    # =========================================================================
    # EDGES: Define the flow
    # =========================================================================

    # Entry point
    graph.set_entry_point("input_enhancer")

    # Linear start: input_enhancer -> domain_knowledge_retriever -> router
    graph.add_edge("input_enhancer", "domain_knowledge_retriever")
    graph.add_edge("domain_knowledge_retriever", "router")

    # Router can escalate to human_review if confidence is low
    graph.add_conditional_edges(
        "router",
        _check_router_confidence,
        {
            "high_confidence": "game_planner",
            "low_confidence": "human_review"
        }
    )
    graph.add_edge("human_review", "game_planner")  # Resume from game_planner after review

    # Game planner -> Agentic interaction design -> multi-scene check
    # interaction_designer: Designs interaction modes based on pedagogical context
    # interaction_validator: Validates the interaction design before scene generation
    graph.add_edge("game_planner", "interaction_designer")
    graph.add_edge("interaction_designer", "interaction_validator")

    # =========================================================================
    # MULTI-SCENE ROUTING: Check BEFORE scene stages
    # If >1 scene: orchestrator loops scene stages internally per-scene
    # If 1 scene: scene stages run as individual graph nodes
    # =========================================================================
    from app.agents.multi_scene_orchestrator import multi_scene_orchestrator, should_use_multi_scene
    graph.add_node("multi_scene_orchestrator", wrap_agent_with_instrumentation(multi_scene_orchestrator, "multi_scene_orchestrator"))
    graph.add_node("check_multi_scene", lambda state: state)  # Passthrough for conditional

    graph.add_edge("interaction_validator", "check_multi_scene")

    graph.add_conditional_edges(
        "check_multi_scene",
        should_use_multi_scene,
        {
            "multi_scene": "multi_scene_orchestrator",      # Orchestrator loops stages internally
            "single_scene": "scene_stage1_structure"         # Single scene, stages run as graph nodes
        }
    )

    # Single-scene path: 3-stage scene generation
    graph.add_edge("scene_stage1_structure", "scene_stage2_assets")
    graph.add_edge("scene_stage2_assets", "scene_stage3_interactions")
    graph.add_edge("scene_stage3_interactions", "check_post_scene_needs")

    # Multi-scene path joins back after orchestrator
    graph.add_edge("multi_scene_orchestrator", "check_post_scene_needs")

    # =========================================================================
    # PHASE 6: CONDITIONAL ROUTING - Check if asset pipeline is needed
    # =========================================================================
    # Add needs detection node to analyze state and set routing flags
    graph.add_node("check_post_scene_needs", check_post_blueprint_needs)

    # =========================================================================
    # PHASE 6: CONDITIONAL ASSET PIPELINE ROUTING
    # =========================================================================
    # After needs detection, check if asset pipeline should run
    graph.add_conditional_edges(
        "check_post_scene_needs",
        should_run_asset_pipeline,
        {
            "run_assets": "asset_planner",  # Templates that need asset generation
            "skip_assets": "blueprint_generator"  # Simple templates skip to blueprint directly
        }
    )

    # =========================================================================
    # ASSET PIPELINE: asset_planner → asset_generator_orchestrator (direct)
    # =========================================================================
    # Legacy check_workflow_mode and check_diagram_image REMOVED.
    # asset_planner always generates workflow_execution_plan from scene_breakdown.
    # Image retrieval + zone detection are handled inside labeling_diagram_workflow
    # when executed by asset_generator_orchestrator.
    graph.add_edge("asset_planner", "asset_generator_orchestrator")

    # =========================================================================
    # ASSET GENERATION PIPELINE WITH RETRY LOOP (Phase 4)
    # =========================================================================
    # In workflow mode: asset_generator_orchestrator executes labeling_diagram_workflow
    # In legacy mode: asset_generator_orchestrator generates CSS animations and other assets
    graph.add_edge("asset_generator_orchestrator", "asset_validator")

    # Asset retry loop: validator -> retry/skip/continue
    # Uses should_retry_assets for conditional routing with graceful degradation
    graph.add_conditional_edges(
        "asset_validator",
        should_retry_assets,
        {
            "continue": "blueprint_generator",  # All assets valid, proceed to blueprint
            "retry": "asset_generator_orchestrator",  # Retry failed assets only
            "skip": "blueprint_generator"  # Skip and continue with partial assets
        }
    )

    # =========================================================================
    # BLUEPRINT GENERATION WITH RETRY LOOP (Phase 4)
    # =========================================================================
    # Blueprint now has access to generated_assets from the asset pipeline
    graph.add_edge("blueprint_generator", "blueprint_validator")

    # =========================================================================
    # PHASE 6: SIMPLIFIED PIPELINE - DIRECT TO END
    # =========================================================================
    # Blueprint validation is the final step - no need for diagram_spec/svg generation
    # The frontend renders directly from the blueprint, making diagram_spec/svg redundant.
    # blueprint_validator now sets generation_complete=True on success.
    graph.add_conditional_edges(
        "blueprint_validator",
        should_retry_blueprint,
        {
            "continue": END,  # PHASE 6: Route directly to END (generation_complete set in validator)
            "retry": "blueprint_generator",  # Retry with validation errors as feedback
            "human_review": "human_review"  # Max retries exceeded, escalate
        }
    )

    # NOTE: diagram_spec_generator and diagram_svg_generator agents are no longer in T1 pipeline
    # They remain defined in graph.py for other topologies that may need them.
    # The frontend renders zones/labels directly from blueprint.zones and blueprint.labels.

    return graph


def _check_router_confidence(state: AgentState) -> Literal["high_confidence", "low_confidence"]:
    """Check if router has high confidence in template selection."""
    template_selection = state.get("template_selection", {})
    confidence = template_selection.get("confidence", 0.0)

    # Threshold for requiring human review
    threshold = 0.5

    if confidence >= threshold:
        return "high_confidence"
    return "low_confidence"


def build_t4_self_refine(config: TopologyConfig) -> StateGraph:
    """T4: Self-refine with same model critiquing its output"""
    from app.agents.graph import input_enhancer_agent, router_agent

    graph = StateGraph(AgentState)

    # Self-refine combines generation and critique in one node
    graph.add_node("input_enhancer", input_enhancer_agent)
    graph.add_node("router", router_agent)
    graph.add_node("self_refine_generation", create_self_refine_node(config))
    graph.add_node("finalize", lambda state: {"generation_complete": True})

    graph.set_entry_point("input_enhancer")
    graph.add_edge("input_enhancer", "router")
    graph.add_edge("router", "self_refine_generation")
    graph.add_conditional_edges("self_refine_generation", check_refine_complete, {
        "complete": "finalize",
        "continue": "self_refine_generation"
    })
    graph.add_edge("finalize", END)

    return graph


def build_t2_actor_critic(config: TopologyConfig) -> StateGraph:
    """
    T2: Actor-Critic (Evaluator-Optimizer) topology

    Separate generator (actor) and evaluator (critic) agents.
    The critic evaluates outputs and provides feedback for regeneration.

    Flow:
    Input → Enhancer → Router → Generator → Evaluator → [Pass?]
                                    ↑           |
                                    └── No ─────┘
                                           |
                                         Yes → Output
    """
    from app.agents.graph import (
        input_enhancer_agent,
        router_agent,
        game_planner_agent,
        scene_generator_agent,
        blueprint_generator_agent,
        human_review_node
    )
    # asset_generator_agent removed - diagram_svg_generator now sets generation_complete

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("input_enhancer", input_enhancer_agent)
    graph.add_node("router", router_agent)
    graph.add_node("game_planner", game_planner_agent)
    graph.add_node("scene_generator", scene_generator_agent)
    graph.add_node("blueprint_generator", blueprint_generator_agent)
    graph.add_node("critic", create_critic_node(config))
    # asset_generator removed
    graph.add_node("human_review", human_review_node)

    # Entry
    graph.set_entry_point("input_enhancer")

    # Linear flow to generation
    graph.add_edge("input_enhancer", "router")
    graph.add_edge("router", "game_planner")
    graph.add_edge("game_planner", "scene_generator")
    graph.add_edge("scene_generator", "blueprint_generator")

    # Critic evaluates blueprint
    graph.add_edge("blueprint_generator", "critic")

    # Conditional based on critic feedback
    graph.add_conditional_edges("critic", check_critic_approval, {
        "approved": END,  # Direct to END (asset_generator removed)
        "revise": "blueprint_generator",
        "escalate": "human_review"
    })

    graph.add_edge("human_review", "blueprint_generator")

    return graph


def build_t3_hierarchical(config: TopologyConfig) -> StateGraph:
    """
    T3: Hierarchical Supervisor topology

    A supervisor orchestrates specialized teams:
    - Pedagogy Team: InputEnhancer, Context Validator
    - Game Team: GamePlanner, SceneGenerator
    - Code Team: BlueprintGenerator, Validator

    Flow:
                    SUPERVISOR
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
    Pedagogy         Game           Code
      Team           Team           Team
        │               │               │
        └───────────────┴───────────────┘
                        │
                    Assembly
    """
    from app.agents.graph import (
        input_enhancer_agent,
        router_agent,
        game_planner_agent,
        scene_generator_agent,
        blueprint_generator_agent,
        blueprint_validator_agent,
        human_review_node
    )
    # asset_generator_agent removed - diagram_svg_generator now sets generation_complete

    graph = StateGraph(AgentState)

    # Supervisor node
    graph.add_node("supervisor", create_supervisor_node(config))

    # Pedagogy team
    graph.add_node("pedagogy_enhance", input_enhancer_agent)
    graph.add_node("pedagogy_route", router_agent)
    graph.add_node("pedagogy_validate", create_validator_node("pedagogical_context", config))

    # Game team
    graph.add_node("game_plan", game_planner_agent)
    graph.add_node("game_scene", scene_generator_agent)
    graph.add_node("game_validate", create_validator_node("scene", config))

    # Code team
    graph.add_node("code_blueprint", blueprint_generator_agent)
    graph.add_node("code_validate", blueprint_validator_agent)

    # Assembly
    graph.add_node("assembly", create_assembly_node(config))
    # asset_generator removed
    graph.add_node("human_review", human_review_node)

    # Entry
    graph.set_entry_point("supervisor")

    # Supervisor dispatches to pedagogy first
    graph.add_edge("supervisor", "pedagogy_enhance")
    graph.add_edge("pedagogy_enhance", "pedagogy_route")
    graph.add_edge("pedagogy_route", "pedagogy_validate")

    # After pedagogy, move to game team
    graph.add_conditional_edges("pedagogy_validate", check_validation_passed, {
        "passed": "game_plan",
        "retry": "pedagogy_enhance",
        "escalate": "human_review"
    })

    graph.add_edge("game_plan", "game_scene")
    graph.add_edge("game_scene", "game_validate")

    # After game team, move to code team
    graph.add_conditional_edges("game_validate", check_validation_passed, {
        "passed": "code_blueprint",
        "retry": "game_scene",
        "escalate": "human_review"
    })

    graph.add_edge("code_blueprint", "code_validate")

    # After code team, assembly
    graph.add_conditional_edges("code_validate", check_validation_passed, {
        "passed": "assembly",
        "retry": "code_blueprint",
        "escalate": "human_review"
    })

    graph.add_edge("assembly", END)  # Direct to END (asset_generator removed)
    graph.add_edge("human_review", "supervisor")

    return graph


def build_t5_debate(config: TopologyConfig) -> StateGraph:
    """
    T5: Multi-Agent Debate topology

    Multiple proposer agents generate solutions independently,
    then debate and a judge selects the best.

    Flow:
                Input → Enhancer → Router
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
        Proposer A      Proposer B      Proposer C
            │               │               │
            └───────────────┴───────────────┘
                            │
                        Debate
                            │
                        Judge
                            │
                        Output
    """
    from app.agents.graph import input_enhancer_agent, router_agent
    # asset_generator_agent removed - diagram_svg_generator now sets generation_complete

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("input_enhancer", input_enhancer_agent)
    graph.add_node("router", router_agent)

    # Create multiple proposers
    for i in range(config.debate_rounds):
        graph.add_node(f"proposer_{i}", create_proposer_node(i, config))

    graph.add_node("debate_arena", create_debate_node(config))
    graph.add_node("judge", create_judge_node(config))
    # asset_generator removed

    # Entry
    graph.set_entry_point("input_enhancer")

    graph.add_edge("input_enhancer", "router")

    # Router fans out to all proposers
    # Note: LangGraph doesn't support true parallel fan-out, so we chain them
    graph.add_edge("router", "proposer_0")
    for i in range(config.debate_rounds - 1):
        graph.add_edge(f"proposer_{i}", f"proposer_{i + 1}")

    # Last proposer goes to debate
    graph.add_edge(f"proposer_{config.debate_rounds - 1}", "debate_arena")
    graph.add_edge("debate_arena", "judge")
    graph.add_edge("judge", END)  # Direct to END (asset_generator removed)

    return graph


def build_t6_dag(config: TopologyConfig) -> StateGraph:
    """
    T6: DAG Parallel topology

    Parallel execution where dependencies allow.
    Multiple generation paths merge at validation points.

    Flow:
                        Enhancer
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
         Router      Pedagogy         Context
            │         Analyzer        Enricher
            │               │               │
            └───────────────┴───────────────┘
                            │
                        Merger
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
       GamePlan          Story        Blueprint
            │               │               │
            └───────────────┴───────────────┘
                            │
                       Assembler
    """
    from app.agents.graph import (
        input_enhancer_agent,
        router_agent,
        game_planner_agent,
        scene_generator_agent,
        blueprint_generator_agent,
    )
    # asset_generator_agent removed - diagram_svg_generator now sets generation_complete

    graph = StateGraph(AgentState)

    # First parallel branch
    graph.add_node("input_enhancer", input_enhancer_agent)
    graph.add_node("router", router_agent)
    graph.add_node("pedagogy_analyzer", create_pedagogy_analyzer_node(config))
    graph.add_node("context_enricher", create_context_enricher_node(config))
    graph.add_node("merger_1", create_merger_node("phase_1", config))

    # Second parallel branch
    graph.add_node("game_planner", game_planner_agent)
    graph.add_node("scene_generator", scene_generator_agent)
    graph.add_node("blueprint_scaffolder", create_blueprint_scaffolder_node(config))
    graph.add_node("merger_2", create_merger_node("phase_2", config))

    # Final
    graph.add_node("assembler", create_assembly_node(config))
    # asset_generator removed

    # Entry
    graph.set_entry_point("input_enhancer")

    # Phase 1: parallel analysis (simulated via sequence due to LangGraph limitations)
    graph.add_edge("input_enhancer", "router")
    graph.add_edge("router", "pedagogy_analyzer")
    graph.add_edge("pedagogy_analyzer", "context_enricher")
    graph.add_edge("context_enricher", "merger_1")

    # Phase 2: parallel generation
    graph.add_edge("merger_1", "game_planner")
    graph.add_edge("game_planner", "scene_generator")
    graph.add_edge("scene_generator", "blueprint_scaffolder")
    graph.add_edge("blueprint_scaffolder", "merger_2")

    # Final assembly
    graph.add_edge("merger_2", "assembler")
    graph.add_edge("assembler", END)  # Direct to END (asset_generator removed)

    return graph


def build_t7_reflection(config: TopologyConfig) -> StateGraph:
    """
    T7: Reflection with Memory Bank topology

    Agent learns from past attempts using a memory bank.
    Retrieves relevant past experiences to improve generation.

    Flow:
    ┌─────────────────────────────────────────────────────────────────┐
    │                        MEMORY BANK                               │
    │  [Past Failures] [Successful Patterns] [Critique History]       │
    └───────────────────────────────┬─────────────────────────────────┘
                                    │
                                    ▼
    Input ──→ Retriever ──→ Generator ──→ Critic ──→ [Pass?] ──→ Output
                   │                          │           │
                   │                          │       No: Store failure
                   │                          │           │
                   └──────────────────────────┴───────────┘
    """
    from app.agents.graph import (
        input_enhancer_agent,
        router_agent,
        game_planner_agent,
        scene_generator_agent,
        blueprint_generator_agent,
        human_review_node
    )
    # asset_generator_agent removed - diagram_svg_generator now sets generation_complete

    graph = StateGraph(AgentState)

    # Memory-enhanced nodes
    graph.add_node("input_enhancer", input_enhancer_agent)
    graph.add_node("memory_retriever", create_memory_retriever_node(config))
    graph.add_node("router", router_agent)
    graph.add_node("game_planner", game_planner_agent)
    graph.add_node("scene_generator", scene_generator_agent)
    graph.add_node("blueprint_generator", blueprint_generator_agent)
    graph.add_node("critic", create_critic_node(config))
    graph.add_node("memory_store", create_memory_store_node(config))
    # asset_generator removed
    graph.add_node("human_review", human_review_node)

    # Entry
    graph.set_entry_point("input_enhancer")

    # Flow with memory
    graph.add_edge("input_enhancer", "memory_retriever")
    graph.add_edge("memory_retriever", "router")
    graph.add_edge("router", "game_planner")
    graph.add_edge("game_planner", "scene_generator")
    graph.add_edge("scene_generator", "blueprint_generator")
    graph.add_edge("blueprint_generator", "critic")

    # Critic decides: pass, store failure, or escalate
    graph.add_conditional_edges("critic", check_critic_with_memory, {
        "approved": END,  # Direct to END (asset_generator removed)
        "store_and_retry": "memory_store",
        "escalate": "human_review"
    })

    graph.add_edge("memory_store", "blueprint_generator")  # Retry with stored feedback
    graph.add_edge("human_review", "memory_retriever")

    return graph


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_validator_node(artifact_type: str, config: TopologyConfig):
    """Create a validator node for a specific artifact type"""

    async def validator_node(state: AgentState) -> dict:
        from datetime import datetime

        # Get the artifact to validate
        artifact = None
        if artifact_type == "pedagogical_context":
            artifact = state.get("pedagogical_context")
            validator = validate_pedagogical_context
        elif artifact_type == "template_selection":
            artifact = state.get("template_selection")
            validator = validate_template_selection
        elif artifact_type == "game_plan":
            artifact = state.get("game_plan")
            validator = validate_game_plan
        elif artifact_type == "scene":
            artifact = state.get("scene_data")
            validator = validate_scene
        elif artifact_type == "story":  # Legacy support
            artifact = state.get("story_data")
            validator = validate_story
        elif artifact_type == "diagram_spec":
            artifact = state.get("diagram_spec")
            from app.agents.diagram_spec_generator import validate_diagram_spec
            validator = validate_diagram_spec
        else:
            return {"current_validation_errors": ["Unknown artifact type"]}

        if artifact is None:
            return {"current_validation_errors": [f"No {artifact_type} to validate"]}

        # Run validation
        passed, score, errors = await validator(artifact, config)

        # Update retry count
        retry_key = f"{artifact_type}_validator"
        current_retries = state.get("retry_counts", {}).get(retry_key, 0)

        return {
            "validation_results": {
                **state.get("validation_results", {}),
                artifact_type: {
                    "is_valid": passed,
                    "score": score,
                    "errors": errors.split("; ") if errors else [],
                    "warnings": [],
                    "suggestions": [],
                    "validated_at": datetime.utcnow().isoformat()
                }
            },
            "current_validation_errors": errors.split("; ") if errors and not passed else [],
            "retry_counts": {
                **state.get("retry_counts", {}),
                retry_key: current_retries + (0 if passed else 1)
            },
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return validator_node


def create_diagram_spec_validator_node(config: TopologyConfig):
    """
    Create a diagram spec validator node for the retry loop.

    This validator:
    1. Validates the diagram_spec against the DiagramSvgSpec schema
    2. Tracks retry counts
    3. Populates current_validation_errors for feedback to generator

    Part of Phase 4: Iteration Loops (Retry with Feedback)
    """
    async def diagram_spec_validator_node(state: AgentState) -> dict:
        from datetime import datetime
        from app.agents.schemas.interactive_diagram import DiagramSvgSpec

        spec = state.get("diagram_spec", {})
        errors = []
        warnings = []
        is_valid = True

        # Schema validation
        try:
            DiagramSvgSpec.model_validate(spec)
        except Exception as e:
            is_valid = False
            error_str = str(e)
            # Parse pydantic validation errors for actionable feedback
            if "validation error" in error_str.lower():
                errors.append(f"FIX: Schema validation failed - {error_str}")
            else:
                errors.append(f"FIX: Invalid diagram spec - {error_str}")

        # Additional semantic validation
        if spec:
            # Check zones exist
            zones = spec.get("zones", [])
            labels = spec.get("labels", [])

            if not zones:
                errors.append("FIX: diagram_spec.zones is empty - add at least one zone")
                is_valid = False

            if not labels:
                errors.append("FIX: diagram_spec.labels is empty - add at least one label")
                is_valid = False

            # Check zone-label pairing
            zone_ids = {z.get("id") for z in zones if z.get("id")}
            label_zone_refs = {l.get("zone_id") for l in labels if l.get("zone_id")}

            # Labels should reference valid zones
            orphan_labels = label_zone_refs - zone_ids
            if orphan_labels:
                warnings.append(f"ADJUST: Labels reference non-existent zones: {orphan_labels}")

        # Track retry count
        retry_key = "diagram_spec_generator"
        current_retries = state.get("retry_counts", {}).get(retry_key, 0)

        return {
            "validation_results": {
                **state.get("validation_results", {}),
                "diagram_spec": {
                    "is_valid": is_valid,
                    "score": 1.0 if is_valid else 0.0,
                    "errors": errors,
                    "warnings": warnings,
                    "suggestions": [],
                    "validated_at": datetime.utcnow().isoformat()
                }
            },
            "current_validation_errors": errors if not is_valid else [],
            "retry_counts": {
                **state.get("retry_counts", {}),
                retry_key: current_retries + (0 if is_valid else 1)
            },
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return diagram_spec_validator_node


def create_self_refine_node(config: TopologyConfig):
    """Create a self-refine node that generates and critiques iteratively"""

    async def self_refine_node(state: AgentState) -> dict:
        # Self-refine topology implementation:
        # Current: Basic generate-validate-retry loop
        # Future enhancement: Add self-critique step using separate prompt
        # Reference: "Self-Refine: Iterative Refinement with Self-Feedback" (2023)
        # https://arxiv.org/abs/2303.17651

        iteration = state.get("retry_counts", {}).get("self_refine", 0)

        if iteration >= config.max_iterations:
            return {
                "generation_complete": True,
                "error_message": "Max iterations reached"
            }

        # Placeholder - actual implementation would call LLM
        return {
            "retry_counts": {
                **state.get("retry_counts", {}),
                "self_refine": iteration + 1
            }
        }

    return self_refine_node


# =============================================================================
# ITERATION LOOP ROUTING FUNCTIONS (Phase 4: Retry with Feedback)
# =============================================================================

def should_retry_blueprint(state: AgentState) -> Literal["continue", "retry", "human_review"]:
    """
    Conditional routing for blueprint retry loop.

    Implements retry-with-feedback pattern for blueprint generation:
    1. If validation passes -> continue to next stage
    2. If validation fails and retries available -> retry with error feedback
    3. If max retries exceeded -> escalate to human review

    The blueprint_generator receives validation errors in state.current_validation_errors
    which allows it to fix specific issues on retry.

    Termination criteria:
    - validation_results.blueprint.is_valid == True -> continue
    - retry_counts.blueprint_generator >= max_retries -> human_review
    - Otherwise -> retry
    """
    validation = state.get("validation_results", {}).get("blueprint", {})
    retry_counts = state.get("retry_counts", {})
    retry_count = retry_counts.get("blueprint_generator", 0)
    max_retries = state.get("max_retries", 3)

    # Check if validation passed
    if validation.get("is_valid", False):
        return "continue"

    # Check if we can retry
    if retry_count < max_retries:
        import logging
        logger = logging.getLogger("gamed_ai.topologies")
        logger.info(
            f"Blueprint validation failed (attempt {retry_count + 1}/{max_retries}), "
            f"retrying with feedback. Errors: {state.get('current_validation_errors', [])}"
        )
        return "retry"

    # Max retries exceeded, escalate to human review
    import logging
    logger = logging.getLogger("gamed_ai.topologies")
    logger.warning(
        f"Blueprint validation failed after {max_retries} attempts, escalating to human review"
    )
    return "human_review"


def should_retry_assets(state: AgentState) -> Literal["continue", "retry", "skip"]:
    """
    Conditional routing for asset generation retry loop.

    Implements retry-with-feedback pattern for asset generation:
    1. If all assets valid -> continue to blueprint
    2. If some assets failed and retries available -> retry failed assets only
    3. If max retries exceeded -> skip (continue with partial assets)

    Unlike blueprint retry, asset retry uses "skip" instead of "human_review"
    because partial assets are still usable (graceful degradation).

    Termination criteria:
    - assets_valid == True -> continue
    - retry_counts.asset_generator_orchestrator >= 2 -> skip
    - Otherwise -> retry

    State keys from asset_validator:
    - assets_valid: bool - whether all assets passed validation
    - validation_errors: list - list of error messages
    - validated_assets: dict - validated asset data
    """
    import logging
    logger = logging.getLogger("gamed_ai.topologies")

    # Get validation result from asset_validator output
    # asset_validator sets: assets_valid, validation_errors, validated_assets
    assets_valid = state.get("assets_valid", None)
    validation_errors = state.get("validation_errors", [])

    retry_counts = state.get("retry_counts", {})
    retry_count = retry_counts.get("asset_generator_orchestrator", 0)

    # Asset retry has lower max (2) since generation is expensive
    max_asset_retries = 2

    # Check if all assets valid
    if assets_valid is True:
        logger.info("All assets validated successfully, continuing to blueprint_generator")
        return "continue"

    # If no validation results yet (first pass before asset_validator runs), continue
    if assets_valid is None:
        logger.info("No asset validation results yet, continuing to blueprint_generator")
        return "continue"

    # Count failed assets from validation_errors
    failed_count = len(validation_errors) if validation_errors else 0

    # Check if we can retry
    if retry_count < max_asset_retries and failed_count > 0:
        logger.info(
            f"Asset validation failed for {failed_count} assets (attempt {retry_count + 1}/{max_asset_retries}), "
            f"retrying failed assets..."
        )
        return "retry"

    # Max retries exceeded or no failures to retry
    # Skip and continue with partial assets (graceful degradation)
    if failed_count > 0:
        logger.warning(
            f"Asset generation incomplete after {retry_count} retry attempts. "
            f"Continuing with partial assets ({failed_count} failed). "
            f"Blueprint will use available assets."
        )
    else:
        logger.info("No failed assets, continuing to blueprint_generator")

    return "skip"


def should_retry_diagram_spec(state: AgentState) -> Literal["continue", "retry", "human_review"]:
    """
    Conditional routing for diagram spec retry loop.

    Implements retry-with-feedback pattern for diagram spec generation:
    1. If validation passes -> continue to SVG generation
    2. If validation fails and retries available -> retry with error feedback
    3. If max retries exceeded -> escalate to human review

    Termination criteria:
    - validation_results.diagram_spec.is_valid == True -> continue
    - retry_counts.diagram_spec_generator >= max_retries -> human_review
    - Otherwise -> retry
    """
    validation = state.get("validation_results", {}).get("diagram_spec", {})
    retry_counts = state.get("retry_counts", {})
    retry_count = retry_counts.get("diagram_spec_generator", 0)
    max_retries = state.get("max_retries", 3)

    # Check if validation passed
    if validation.get("is_valid", False):
        return "continue"

    # Check if we can retry
    if retry_count < max_retries:
        import logging
        logger = logging.getLogger("gamed_ai.topologies")
        logger.info(
            f"Diagram spec validation failed (attempt {retry_count + 1}/{max_retries}), "
            f"retrying with feedback."
        )
        return "retry"

    # Max retries exceeded
    import logging
    logger = logging.getLogger("gamed_ai.topologies")
    logger.warning(
        f"Diagram spec validation failed after {max_retries} attempts, escalating to human review"
    )
    return "human_review"


def check_validation_passed(state: AgentState) -> Literal["passed", "retry", "escalate"]:
    """Check if validation passed, needs retry, or human escalation

    Smart auto-retry is ENABLED for recoverable errors. Fatal errors always
    escalate to human review. Set auto_retry=False in state to disable.

    Recoverable errors (will retry automatically):
    - Missing fields (can be added)
    - Coordinate out of range (can be fixed)
    - Reference mismatches (can be remapped)
    - Label text issues (can be corrected)

    Fatal errors (always escalate):
    - Complete schema mismatch
    - Empty required arrays that can't be populated
    - Circular dependencies
    - Security/injection issues
    """
    errors = state.get("current_validation_errors", [])

    if not errors:
        return "passed"

    # Categorize errors
    fatal_errors = []
    recoverable_errors = []

    fatal_patterns = [
        "schema mismatch",
        "circular",
        "security",
        "injection",
        "complete failure",
        "cannot parse",
        "invalid json",
    ]

    recoverable_patterns = [
        "missing",
        "coordinate",
        "out of range",
        "reference",
        "not in canonical",
        "duplicate",
        "text field",
        "radius",
        "FIX:",  # Our new actionable error format
        "ADJUST:",
        "PEDAGOGICAL:",
    ]

    for error in errors:
        error_lower = error.lower() if isinstance(error, str) else ""

        # Check for fatal patterns
        is_fatal = any(pat in error_lower for pat in fatal_patterns)

        # Check for recoverable patterns
        is_recoverable = any(pat in error_lower for pat in recoverable_patterns)

        if is_fatal:
            fatal_errors.append(error)
        elif is_recoverable:
            recoverable_errors.append(error)
        else:
            # Unknown error type - treat as recoverable for first few attempts
            recoverable_errors.append(error)

    # If any fatal errors, always escalate
    if fatal_errors:
        return "escalate"

    # Check if auto-retry is enabled (default: ENABLED for recoverable errors)
    auto_retry_enabled = state.get("auto_retry", True)  # Changed default to True

    if not auto_retry_enabled:
        return "escalate"

    # Dynamic retry limits based on error complexity
    retry_counts = state.get("retry_counts", {})
    error_count = len(recoverable_errors)

    # More errors = fewer retries (complexity heuristic)
    if error_count <= 2:
        max_retries = 5  # Simple fixes - more attempts
    elif error_count <= 5:
        max_retries = 4  # Moderate complexity
    else:
        max_retries = 3  # Many errors - fewer attempts before escalation

    # Override with explicit max_retries if set
    max_retries = state.get("max_retries", max_retries)

    for key, count in retry_counts.items():
        if "validator" in key and count >= max_retries:
            return "escalate"

    return "retry"


def check_refine_complete(state: AgentState) -> Literal["complete", "continue"]:
    """Check if self-refine loop is complete"""
    if state.get("generation_complete"):
        return "complete"
    return "continue"


def check_critic_approval(state: AgentState) -> Literal["approved", "revise", "escalate"]:
    """Check critic approval status

    Smart auto-revise is ENABLED by default for recoverable issues.
    Set auto_retry=False in state to disable automatic revisions.
    """
    critic_result = state.get("validation_results", {}).get("critic", {})

    if critic_result.get("is_valid", False):
        return "approved"

    # Check if auto-retry is enabled (default: ENABLED)
    auto_retry_enabled = state.get("auto_retry", True)

    if not auto_retry_enabled:
        return "escalate"

    # Analyze critic feedback for severity
    feedback = critic_result.get("feedback", "")
    score = critic_result.get("score", 0.0)

    # Low score (<0.3) suggests fundamental issues - escalate sooner
    if score < 0.3:
        max_retries = 2
    elif score < 0.5:
        max_retries = 3
    else:
        max_retries = 4  # Close to passing - more attempts

    # Override with explicit max_retries if set
    max_retries = state.get("max_retries", max_retries)

    retry_count = state.get("retry_counts", {}).get("critic", 0)
    if retry_count >= max_retries:
        return "escalate"

    return "revise"


def check_critic_with_memory(state: AgentState) -> Literal["approved", "store_and_retry", "escalate"]:
    """Check critic approval with memory storage option

    Smart auto-retry with memory is ENABLED by default.
    Set auto_retry=False in state to disable automatic store-and-retry behavior.
    """
    critic_result = state.get("validation_results", {}).get("critic", {})

    if critic_result.get("is_valid", False):
        return "approved"

    # Check if auto-retry is enabled (default: ENABLED)
    auto_retry_enabled = state.get("auto_retry", True)

    if not auto_retry_enabled:
        return "escalate"

    # Analyze critic feedback for severity
    score = critic_result.get("score", 0.0)

    # Dynamic retry limits based on score
    if score < 0.3:
        max_retries = 2
    elif score < 0.5:
        max_retries = 3
    else:
        max_retries = 4

    # Override with explicit max_retries if set
    max_retries = state.get("max_retries", max_retries)

    retry_count = state.get("retry_counts", {}).get("critic", 0)
    if retry_count >= max_retries:
        return "escalate"

    return "store_and_retry"


def create_critic_node(config: TopologyConfig):
    """Create a critic node that evaluates generated artifacts"""

    async def critic_node(state: AgentState) -> dict:
        from datetime import datetime
        import json

        blueprint = state.get("blueprint", {})
        scene = state.get("scene_data", {})
        question = state.get("question_text", "")

        # Combine artifacts for evaluation
        artifact = {
            "scene": scene,
            "blueprint": blueprint
        }

        # Track retries
        retry_count = state.get("retry_counts", {}).get("critic", 0)

        # Simplified validation (would use LLM in production)
        errors = []
        score = 1.0

        # Check blueprint completeness
        if not blueprint.get("title"):
            errors.append("Blueprint missing title")
            score -= 0.2

        if not blueprint.get("tasks") or len(blueprint.get("tasks", [])) == 0:
            errors.append("Blueprint has no tasks")
            score -= 0.3

        # Check scene completeness
        if not scene.get("scene_title"):
            errors.append("Scene missing title")
            score -= 0.2
        if not scene.get("required_assets"):
            errors.append("Scene missing required assets")
            score -= 0.3

        is_valid = score >= config.validation_threshold

        return {
            "validation_results": {
                **state.get("validation_results", {}),
                "critic": {
                    "is_valid": is_valid,
                    "score": score,
                    "errors": errors,
                    "feedback": "; ".join(errors) if errors else "Approved",
                    "validated_at": datetime.utcnow().isoformat()
                }
            },
            "retry_counts": {
                **state.get("retry_counts", {}),
                "critic": retry_count + (0 if is_valid else 1)
            },
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return critic_node


def create_supervisor_node(config: TopologyConfig):
    """Create a supervisor node for hierarchical topology"""

    async def supervisor_node(state: AgentState) -> dict:
        from datetime import datetime

        # Supervisor initializes the workflow and tracks team progress
        return {
            "current_agent": "supervisor",
            "agent_history": state.get("agent_history", []) + [{
                "agent_name": "supervisor",
                "started_at": datetime.utcnow().isoformat(),
                "status": "running"
            }],
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return supervisor_node


def create_assembly_node(config: TopologyConfig):
    """Create an assembly node that combines outputs from teams"""

    async def assembly_node(state: AgentState) -> dict:
        from datetime import datetime

        # Combine all artifacts into final output
        blueprint = state.get("blueprint", {})
        scene = state.get("scene_data", {})
        story = state.get("story_data", {})  # Legacy support

        # Merge scene into blueprint if needed (prefer scene_data)
        if blueprint and scene:
            blueprint["narrativeIntro"] = scene.get("minimal_context", blueprint.get("narrativeIntro", ""))
            blueprint["title"] = scene.get("scene_title", blueprint.get("title", ""))
        elif blueprint and story:  # Legacy fallback
            blueprint["narrativeIntro"] = story.get("story_context", blueprint.get("narrativeIntro", ""))
            blueprint["title"] = story.get("story_title", blueprint.get("title", ""))

        return {
            "blueprint": blueprint,
            "current_agent": "assembly",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return assembly_node


def create_proposer_node(proposer_id: int, config: TopologyConfig):
    """Create a proposer node for debate topology"""

    async def proposer_node(state: AgentState) -> dict:
        from datetime import datetime

        # Each proposer generates an alternative solution
        proposals = state.get("debate_proposals", [])

        # Generate a proposal (placeholder - would use LLM)
        proposal = {
            "proposer_id": proposer_id,
            "blueprint": {
                "templateType": state.get("template_selection", {}).get("template_type", "PARAMETER_PLAYGROUND"),
                "title": f"Proposal {proposer_id}: {state.get('question_text', '')[:30]}...",
                "narrativeIntro": f"Approach {proposer_id} for learning",
                "tasks": [{"id": f"task_{proposer_id}", "questionText": state.get("question_text", "")}]
            },
            "confidence": 0.7 + (proposer_id * 0.05)  # Slightly different confidences
        }

        proposals.append(proposal)

        return {
            "debate_proposals": proposals,
            "current_agent": f"proposer_{proposer_id}",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return proposer_node


def create_debate_node(config: TopologyConfig):
    """Create a debate arena node where proposals are compared"""

    async def debate_node(state: AgentState) -> dict:
        from datetime import datetime

        proposals = state.get("debate_proposals", [])

        # Simulate debate by scoring proposals
        scored_proposals = []
        for p in proposals:
            score = p.get("confidence", 0.5)
            # Add bonus for completeness
            if p.get("blueprint", {}).get("tasks"):
                score += 0.1
            scored_proposals.append({**p, "debate_score": min(score, 1.0)})

        return {
            "debate_proposals": scored_proposals,
            "current_agent": "debate_arena",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return debate_node


def create_judge_node(config: TopologyConfig):
    """Create a judge node that selects the best proposal"""

    async def judge_node(state: AgentState) -> dict:
        from datetime import datetime

        proposals = state.get("debate_proposals", [])

        # Select best proposal by score
        best = max(proposals, key=lambda p: p.get("debate_score", 0)) if proposals else None

        if best:
            return {
                "blueprint": best.get("blueprint"),
                "scene_data": {
                    "scene_title": best.get("blueprint", {}).get("title", ""),
                    "minimal_context": best.get("blueprint", {}).get("narrativeIntro", ""),
                    "visual_theme": "educational",
                    "required_assets": [],
                    "asset_interactions": [],
                    "layout_specification": {},
                    "animation_sequences": [],
                    "state_transitions": [],
                    "visual_flow": []
                },
                "generation_complete": True,
                "current_agent": "judge",
                "last_updated_at": datetime.utcnow().isoformat()
            }

        return {
            "error_message": "No proposals to judge",
            "current_agent": "judge",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return judge_node


def create_pedagogy_analyzer_node(config: TopologyConfig):
    """Create a pedagogy analyzer for DAG topology"""

    async def pedagogy_analyzer_node(state: AgentState) -> dict:
        from datetime import datetime

        # Analyze pedagogical aspects (placeholder)
        context = state.get("pedagogical_context", {})

        analysis = {
            "blooms_recommendations": [],
            "learning_path": [],
            "scaffolding_needed": context.get("difficulty") == "advanced"
        }

        return {
            "pedagogy_analysis": analysis,
            "current_agent": "pedagogy_analyzer",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return pedagogy_analyzer_node


def create_context_enricher_node(config: TopologyConfig):
    """Create a context enricher for DAG topology"""

    async def context_enricher_node(state: AgentState) -> dict:
        from datetime import datetime

        # Enrich context with additional information (placeholder)
        context = state.get("pedagogical_context", {})

        enriched = {
            **context,
            "enriched": True,
            "additional_resources": [],
            "related_concepts": []
        }

        return {
            "pedagogical_context": enriched,
            "current_agent": "context_enricher",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return context_enricher_node


def create_merger_node(phase: str, config: TopologyConfig):
    """Create a merger node for DAG topology"""

    async def merger_node(state: AgentState) -> dict:
        from datetime import datetime

        # Merge outputs from parallel branches
        return {
            f"{phase}_merged": True,
            "current_agent": f"merger_{phase}",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return merger_node


def create_blueprint_scaffolder_node(config: TopologyConfig):
    """Create a blueprint scaffolder for DAG topology"""

    async def blueprint_scaffolder_node(state: AgentState) -> dict:
        from datetime import datetime

        template_type = state.get("template_selection", {}).get("template_type", "PARAMETER_PLAYGROUND")

        # Create scaffold blueprint
        scaffold = {
            "templateType": template_type,
            "title": "",
            "narrativeIntro": "",
            "tasks": [],
            "animationCues": {}
        }

        return {
            "blueprint_scaffold": scaffold,
            "current_agent": "blueprint_scaffolder",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return blueprint_scaffolder_node


def create_memory_retriever_node(config: TopologyConfig):
    """Create a memory retriever node for reflection topology"""

    async def memory_retriever_node(state: AgentState) -> dict:
        from datetime import datetime

        # Retrieve relevant memories (placeholder - would use vector DB)
        question = state.get("question_text", "")
        template = state.get("template_selection", {}).get("template_type", "")

        # Simulated memory retrieval
        memories = {
            "similar_questions": [],
            "successful_patterns": [],
            "past_failures": [],
            "best_practices": [
                f"For {template}, ensure all required fields are present",
                "Include clear learning objectives",
                "Provide engaging narrative context"
            ]
        }

        return {
            "retrieved_memories": memories,
            "current_agent": "memory_retriever",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return memory_retriever_node


def create_memory_store_node(config: TopologyConfig):
    """Create a memory store node for reflection topology"""

    async def memory_store_node(state: AgentState) -> dict:
        from datetime import datetime

        # Store failure information for future retrieval
        critic_result = state.get("validation_results", {}).get("critic", {})

        memory_entry = {
            "question_id": state.get("question_id"),
            "template_type": state.get("template_selection", {}).get("template_type"),
            "failure_reason": critic_result.get("errors", []),
            "feedback": critic_result.get("feedback", ""),
            "iteration": state.get("retry_counts", {}).get("critic", 0),
            "stored_at": datetime.utcnow().isoformat()
        }

        # In production, would persist to vector DB
        stored_memories = state.get("stored_memories", [])
        stored_memories.append(memory_entry)

        return {
            "stored_memories": stored_memories,
            "current_agent": "memory_store",
            "last_updated_at": datetime.utcnow().isoformat()
        }

    return memory_store_node


# =============================================================================
# TOPOLOGY FACTORY
# =============================================================================

def create_topology(
    topology_type: TopologyType,
    config: Optional[TopologyConfig] = None
) -> StateGraph:
    """Factory function to create a topology graph"""

    if config is None:
        config = TopologyConfig(topology_type=topology_type)

    builders = {
        TopologyType.T0_SEQUENTIAL: build_t0_sequential,
        TopologyType.T1_SEQUENTIAL_VALIDATED: build_t1_sequential_validated,
        TopologyType.T2_ACTOR_CRITIC: build_t2_actor_critic,
        TopologyType.T3_HIERARCHICAL: build_t3_hierarchical,
        TopologyType.T4_SELF_REFINE: build_t4_self_refine,
        TopologyType.T5_MULTI_AGENT_DEBATE: build_t5_debate,
        TopologyType.T6_DAG_PARALLEL: build_t6_dag,
        TopologyType.T7_REFLECTION_MEMORY: build_t7_reflection,
    }

    builder = builders.get(topology_type)
    if builder is None:
        raise ValueError(f"Topology {topology_type} not implemented yet")

    return builder(config)


def get_topology_description(topology_type: TopologyType) -> str:
    """Get a description of a topology type"""
    descriptions = {
        TopologyType.T0_SEQUENTIAL: "Sequential baseline - linear execution without verification loops",
        TopologyType.T1_SEQUENTIAL_VALIDATED: "Sequential with validators - validation after each stage with retry logic",
        TopologyType.T2_ACTOR_CRITIC: "Actor-Critic - separate generator and evaluator agents with feedback loop",
        TopologyType.T3_HIERARCHICAL: "Hierarchical Supervisor - supervisor orchestrates specialized teams",
        TopologyType.T4_SELF_REFINE: "Self-Refine - same model iteratively critiques and improves its output",
        TopologyType.T5_MULTI_AGENT_DEBATE: "Multi-Agent Debate - multiple proposers debate, judge selects best",
        TopologyType.T6_DAG_PARALLEL: "DAG Parallel - parallel execution where dependencies allow",
        TopologyType.T7_REFLECTION_MEMORY: "Reflection with Memory - learns from past attempts using memory bank",
    }
    return descriptions.get(topology_type, "Unknown topology")


def list_all_topologies() -> List[Dict[str, Any]]:
    """List all available topologies with descriptions"""
    return [
        {
            "type": t,
            "name": t.value,
            "description": get_topology_description(t)
        }
        for t in TopologyType
    ]
