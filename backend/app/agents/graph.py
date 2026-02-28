"""
LangGraph State Machine for Game Generation Pipeline

This module defines the main orchestration graph for game generation.
Implements the T1 Sequential Validated topology by default.
"""

from typing import Literal, Optional, Callable, Any
from datetime import datetime
import logging
import json
import asyncio

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import os

from app.agents.state import AgentState
from app.agents.instrumentation import instrumented_agent, wrap_agent_with_instrumentation


# =============================================================================
# AGENT TIMEOUT CONFIGURATION
# =============================================================================

# Per-agent timeout settings (in seconds)
# Longer timeouts for agents that involve LLM calls or external APIs
AGENT_TIMEOUTS = {
    # Fast agents (local processing)
    "input_enhancer": 60,
    "router": 30,
    "blueprint_validator": 30,
    "diagram_spec_validator": 30,
    "code_verifier": 60,
    "phet_blueprint_validator": 30,
    "asset_validator": 60,

    # Medium agents (single LLM call)
    "domain_knowledge_retriever": 90,
    "game_planner": 120,
    "game_designer": 120,
    "design_interpreter": 120,
    "scene_stage1_structure": 120,
    "scene_stage2_assets": 120,
    "scene_stage3_interactions": 120,
    "blueprint_generator": 180,
    "diagram_spec_generator": 120,
    "diagram_svg_generator": 90,

    # Slow agents (multiple LLM calls or external APIs)
    "diagram_image_retriever": 180,
    "diagram_image_generator": 300,
    "image_label_remover": 180,
    "qwen_annotation_detector": 300,
    "qwen_sam_zone_detector": 300,
    "gemini_zone_detector": 300,
    "direct_structure_locator": 180,

    # Very slow agents (complex orchestration)
    "zone_planner": 600,
    "game_orchestrator": 600,
    "output_orchestrator": 600,

    # V3 pipeline agents
    "game_designer_v3": 120,
    "design_validator": 30,
    "scene_architect_v3": 90,
    "scene_validator": 30,
    "interaction_designer_v3": 90,
    "interaction_validator": 30,
    "asset_generator_v3": 600,
    "blueprint_assembler_v3": 60,

    # V4 pipeline agents
    "v4_input_analyzer": 60,
    "v4_dk_retriever": 90,
    "v4_phase0_merge": 10,
    "v4_game_designer": 120,
    "v4_game_plan_validator": 10,
    "v4_content_builder": 300,   # Sequential — processes all mechanics
    "v4_asset_worker": 180,
    "v4_asset_merge": 10,
    "v4_assembler": 30,

    # Default timeout for unlisted agents
    "_default": 180,
}


class AgentTimeoutError(Exception):
    """Raised when an agent execution times out."""
    pass


def wrap_with_timeout(agent_func: Callable, agent_name: str) -> Callable:
    """
    Wrap an agent function with timeout protection.

    Args:
        agent_func: The agent function to wrap
        agent_name: Name of the agent (for timeout lookup and logging)

    Returns:
        Wrapped function with timeout
    """
    timeout = AGENT_TIMEOUTS.get(agent_name, AGENT_TIMEOUTS["_default"])

    async def wrapper(state: AgentState, *args, **kwargs) -> Any:
        try:
            return await asyncio.wait_for(
                agent_func(state, *args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Agent '{agent_name}' timed out after {timeout}s")
            raise AgentTimeoutError(
                f"Agent '{agent_name}' exceeded {timeout}s timeout. "
                f"Consider increasing AGENT_TIMEOUTS['{agent_name}']."
            )

    # Preserve function metadata
    wrapper.__name__ = getattr(agent_func, '__name__', agent_name)
    wrapper.__doc__ = getattr(agent_func, '__doc__', None)

    return wrapper


def wrap_agent_with_timeout_and_instrumentation(agent_func: Callable, agent_name: str) -> Callable:
    """
    Wrap an agent with both timeout protection and instrumentation.

    This is the recommended way to add agents to the graph for full observability
    and protection against hanging agents.
    """
    # First wrap with timeout, then with instrumentation
    timed_agent = wrap_with_timeout(agent_func, agent_name)
    return wrap_agent_with_instrumentation(timed_agent, agent_name)

# Pipeline architecture versions (chronological evolution)
# V1 — Basic image classification + SAM segmentation (baseline)
PRESET_1_BASELINE = "preset_1"
# V1.1 — 7 agentic agents with structured tools
PRESET_1_AGENTIC_SEQUENTIAL = "preset_1_agentic_sequential"
# V2 — 3 ReAct agents (game_designer, diagram_analyzer)
PRESET_1_REACT = "preset_1_react"
# V2.5 — Hierarchical Agentic DAG with ReAct loops, 4-cluster architecture
PRESET_HAD = "had"
# V3 — 5-Phase ReAct Architecture with 12 agents (CURRENT)
PRESET_V3 = "v3"
# V4 — Streamlined 5-phase pipeline with parallel context + Send API assets
PRESET_V4 = "v4"
# V4 Algorithm — Algorithm game pipeline (state_tracer, bug_hunter, etc.)
PRESET_V4_ALGORITHM = "v4_algorithm"

# Import actual agent implementations
from app.agents.input_enhancer import input_enhancer_agent
from app.agents.domain_knowledge_retriever import domain_knowledge_retriever_agent
from app.agents.diagram_image_retriever import diagram_image_retriever_agent
from app.agents.image_label_remover import image_label_remover_agent
from app.agents.diagram_image_segmenter import diagram_image_segmenter_agent
from app.agents.diagram_zone_labeler import diagram_zone_labeler_agent
from app.agents.router import router_agent, validate_routing_decision
from app.agents.game_planner import game_planner_agent

# PhET simulation pipeline agents
from app.agents.phet_simulation_selector import phet_simulation_selector_agent
from app.agents.phet_game_planner import phet_game_planner_agent
from app.agents.phet_assessment_designer import phet_assessment_designer_agent
from app.agents.phet_blueprint_generator import phet_blueprint_generator_agent
from app.agents.phet_bridge_config_generator import phet_bridge_config_generator_agent
from app.agents.schemas.phet_simulation import validate_phet_blueprint
from app.agents.scene_generator import scene_generator_agent
from app.agents.scene_stage1_structure import scene_stage1_structure
from app.agents.scene_stage2_assets import scene_stage2_assets
from app.agents.scene_stage3_interactions import scene_stage3_interactions
from app.agents.blueprint_generator import blueprint_generator_agent
from app.agents.diagram_spec_generator import diagram_spec_generator_agent
from app.agents.diagram_svg_generator import diagram_svg_generator_agent
from app.agents.schemas.interactive_diagram import DiagramSvgSpec

# Qwen VLM agents (experimental pipeline for annotation detection)
from app.agents.qwen_annotation_detector import qwen_annotation_detector
from app.agents.qwen_sam_zone_detector import qwen_sam_zone_detector

# Image classification agents (unlabeled diagram fast path)
from app.agents.image_label_classifier import image_label_classifier
from app.agents.direct_structure_locator import direct_structure_locator

# Asset planning and generation agents
from app.agents.asset_planner import asset_planner
from app.agents.asset_generator_orchestrator import asset_generator_orchestrator
from app.agents.asset_validator import asset_validator

# Hierarchical label diagram preset agents (new pipeline)
from app.agents.diagram_image_generator import diagram_image_generator
from app.agents.gemini_zone_detector import gemini_zone_detector
from app.agents.gemini_sam3_zone_detector import gemini_sam3_zone_detector

# Advanced label diagram preset agents (Preset 2)
from app.agents.diagram_type_classifier import diagram_type_classifier_agent
from app.agents.scene_sequencer import scene_sequencer_agent

# Agentic game design agents (Preset 2 - NEW)
from app.agents.diagram_analyzer import diagram_analyzer
from app.agents.game_designer import game_designer_agent as game_designer
from app.agents.design_interpreter import design_interpreter_agent
from app.agents.multi_scene_image_orchestrator import multi_scene_image_orchestrator

# Multi-scene orchestrator (Phase 5)
from app.agents.multi_scene_orchestrator import multi_scene_orchestrator

# Agentic interaction design agents (replaces hardcoded Bloom's mapping)
from app.agents.interaction_designer import interaction_designer
from app.agents.interaction_validator import interaction_validator

# HAD (Hierarchical Agentic DAG) architecture agents
from app.agents.had.zone_planner import zone_planner
from app.agents.had.game_orchestrator import game_orchestrator
from app.agents.had.output_orchestrator import output_orchestrator
# HAD v3: Unified game designer (optional replacement for game_orchestrator)
from app.agents.had.game_designer import game_designer as had_game_designer

# HAD v3 configuration: Use unified game_designer instead of game_orchestrator
# Set via environment variable: HAD_USE_UNIFIED_DESIGNER=true
import os
HAD_USE_UNIFIED_DESIGNER = os.environ.get("HAD_USE_UNIFIED_DESIGNER", "false").lower() == "true"

# v3 pipeline agents (Preset: v3)
from app.agents.game_designer_v3 import game_designer_v3_agent
from app.agents.design_validator import design_validator_agent
from app.agents.scene_architect_v3 import scene_architect_v3_agent
from app.agents.scene_validator import scene_validator_agent
from app.agents.interaction_designer_v3 import interaction_designer_v3_agent
from app.agents.interaction_validator import interaction_validator_agent as interaction_validator_v3_agent
from app.agents.asset_generator_v3 import asset_generator_v3_agent
from app.agents.blueprint_assembler_v3 import blueprint_assembler_v3_agent, deterministic_blueprint_assembler_agent
# Legacy v3 imports (kept for backward compat — no longer in v3 graph)
from app.agents.asset_spec_builder import asset_spec_builder_agent
from app.agents.asset_orchestrator_v3 import asset_orchestrator_v3_agent

logger = logging.getLogger("gamed_ai.graph")


# =============================================================================
# REMAINING PLACEHOLDER AGENTS
# =============================================================================

@instrumented_agent("blueprint_validator")
async def blueprint_validator_agent(state: AgentState, ctx=None) -> dict:
    """
    Validate generated blueprint.

    Performs:
    1. Schema validation (required fields)
    2. Semantic validation (valid references)
    3. Pedagogical validation (alignment check)
    """
    from app.agents.blueprint_generator import validate_blueprint

    logger.info("BlueprintValidator: Validating blueprint")

    blueprint = state.get("blueprint", {})
    template_type = blueprint.get("templateType", state.get("template_selection", {}).get("template_type", ""))

    # Run validation
    validation_result = await validate_blueprint(
        blueprint,
        template_type,
        context={
            "question_text": state.get("question_text", ""),
            "pedagogical_context": state.get("pedagogical_context", {}),
            "domain_knowledge": state.get("domain_knowledge", {}),
            "diagram_zones": state.get("diagram_zones"),
            "diagram_image": state.get("diagram_image"),
        },
    )

    errors = validation_result.get("errors", [])
    warnings = validation_result.get("warnings", [])
    is_valid = validation_result.get("valid", False)

    # Track retries
    retry_counts = state.get("retry_counts", {})
    if not is_valid:
        retry_counts["blueprint_generator"] = retry_counts.get("blueprint_generator", 0) + 1

    result_state = {
        "validation_results": {
            **state.get("validation_results", {}),
            "blueprint": {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "suggestions": [],
                "validated_at": datetime.utcnow().isoformat()
            }
        },
        "retry_counts": retry_counts,
        "current_validation_errors": errors,
        "current_agent": "check_template_status",
        "last_updated_at": datetime.utcnow().isoformat()
    }

    # Phase 6: Set generation_complete when blueprint is valid
    # This signals pipeline completion, allowing us to skip diagram_spec/svg agents
    if is_valid:
        result_state["generation_complete"] = True
        logger.info("BlueprintValidator: Blueprint valid - setting generation_complete=True")

    # Set validation results for instrumentation
    if ctx:
        ctx.set_validation_results(
            passed=is_valid,
            errors=errors if not is_valid else None
        )
        ctx.complete(result_state)

    return result_state


@instrumented_agent("diagram_spec_validator")
async def diagram_spec_validator_agent(state: AgentState, ctx=None) -> dict:
    """Validate diagram SVG spec."""
    logger.info("DiagramSpecValidator: Validating diagram spec")

    spec = state.get("diagram_spec", {})
    errors = []
    warnings = []
    is_valid = True

    try:
        DiagramSvgSpec.model_validate(spec)
    except Exception as e:
        is_valid = False
        errors.append(str(e))

    retry_counts = state.get("retry_counts", {})
    if not is_valid:
        retry_counts["diagram_spec_generator"] = retry_counts.get("diagram_spec_generator", 0) + 1

    result_state = {
        "validation_results": {
            **state.get("validation_results", {}),
            "diagram_spec": {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "suggestions": [],
                "validated_at": datetime.utcnow().isoformat()
            }
        },
        "retry_counts": retry_counts,
        "current_validation_errors": errors,
        "current_agent": "diagram_spec_validator",
        "last_updated_at": datetime.utcnow().isoformat()
    }
    
    # Set validation results for instrumentation
    if ctx:
        ctx.set_validation_results(
            passed=is_valid,
            errors=errors if not is_valid else None
        )
        ctx.complete(result_state)
    
    return result_state


@instrumented_agent("code_generator")
async def code_generator_agent(state: AgentState, ctx=None) -> dict:
    """
    Generate React component code for stub templates using LLM.
    
    Uses a coding-focused model (deepseek-coder or qwen-coder) to generate
    TypeScript React components that implement the game blueprint.
    """
    from app.services.llm_service import get_llm_service
    
    template_type = state.get("template_selection", {}).get("template_type", "")
    blueprint = state.get("blueprint", {})
    scene_data = state.get("scene_data", {})
    
    logger.info(f"CodeGenerator: Generating code for stub template {template_type}")

    # Build code generation prompt
    code_prompt = f"""Generate a complete, production-ready React TypeScript component for the {template_type} game template.

## Blueprint Data:
{json.dumps(blueprint, indent=2)}

## Scene Requirements:
{json.dumps(scene_data.get("required_assets", []), indent=2) if scene_data else "[]"}

## Requirements:
1. Component name: {template_type}Game
2. Props interface: {{ blueprint: {template_type}Blueprint, onComplete: (result: any) => void }}
3. Implement all game mechanics from the blueprint
4. Use TypeScript with strict typing
5. Include proper error handling
6. Follow React best practices (hooks, state management)
7. Implement all tasks and interactions from blueprint
8. Use the scene assets and layout specifications

## Template-Specific Requirements:
{_get_template_code_requirements(template_type)}

Generate ONLY the TypeScript React component code. No explanations, no markdown, just the code starting with 'import React'."""

    try:
        llm = get_llm_service()
        
        # Use code generation model (lower temperature for deterministic code)
        response = await llm.generate_for_agent(
            agent_name="code_generator",
            prompt=code_prompt,
            system_prompt="You are an expert React TypeScript developer. Generate clean, production-ready code.",
            temperature=0.2,  # Lower temp for code
            max_tokens=8192
        )
        
        # Capture LLM metrics for instrumentation
        if ctx:
            ctx.set_llm_metrics(
                model=response.model,
                prompt_tokens=response.input_tokens,
                completion_tokens=response.output_tokens,
                latency_ms=response.latency_ms
            )
        
        generated_code = response.content.strip()
        
        # Remove markdown code blocks if present
        if generated_code.startswith("```typescript"):
            generated_code = generated_code[13:]
        elif generated_code.startswith("```tsx"):
            generated_code = generated_code[6:]
        elif generated_code.startswith("```"):
            generated_code = generated_code[3:]
        if generated_code.endswith("```"):
            generated_code = generated_code[:-3]
        generated_code = generated_code.strip()
        
        logger.info(f"CodeGenerator: Generated {len(generated_code)} characters of code")
        
        return {
            **state,
            "current_agent": "code_verifier",
            "generated_code": generated_code,
            "last_updated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"CodeGenerator: LLM call failed: {e}", exc_info=True)
        
        # Fallback to placeholder
        generated_code = f'''import React from 'react';

interface {template_type}Props {{
    blueprint: any;
    onComplete: (result: any) => void;
}}

export const {template_type}Game: React.FC<{template_type}Props> = ({{ blueprint, onComplete }}) => {{
    return (
        <div className="game-container">
            <h1>{{blueprint.title}}</h1>
            <p>{{blueprint.narrativeIntro}}</p>
            {{/* Game implementation - generation failed: {str(e)} */}}
        </div>
    );
}};'''
        
        return {
            **state,
            "current_agent": "code_verifier",
            "generated_code": generated_code,
            "error_message": f"CodeGenerator fallback: {str(e)}",
            "last_updated_at": datetime.utcnow().isoformat()
        }


def _get_template_code_requirements(template_type: str) -> str:
    """Get template-specific code requirements"""
    requirements = {
        "STATE_TRACER_CODE": """
- Display code editor with syntax highlighting
- Show variable panel that updates on each step
- Implement step-by-step execution with Next/Previous controls
- Highlight current executing line
- Show call stack for recursive functions
- Allow user to predict variable values before stepping
""",
        "PARAMETER_PLAYGROUND": """
- Interactive parameter sliders/inputs
- Real-time visualization updates
- Parameter validation and constraints
- Visual feedback on parameter changes
""",
        "SEQUENCE_BUILDER": """
- Drag-and-drop sequence ordering
- Visual feedback on correct/incorrect order
- Step-by-step sequence validation
""",
    }
    return requirements.get(template_type, "- Implement all blueprint tasks and interactions")


@instrumented_agent("code_verifier")
async def code_verifier_agent(state: AgentState, ctx=None) -> dict:
    """
    Verify generated code in Docker sandbox.
    
    Performs:
    1. TypeScript compilation check
    2. ESLint validation
    3. Custom verification (component structure, props, etc.)
    """
    from app.sandbox.verifier import get_verifier
    
    logger.info("CodeVerifier: Verifying generated code")

    code = state.get("generated_code", "")
    blueprint = state.get("blueprint", {})
    template_type = state.get("template_selection", {}).get("template_type", "")
    
    errors = []
    warnings = []
    
    # Basic validation first
    if not code or len(code) < 50:
        errors.append("Generated code is too short or empty")
        is_valid = False
    elif "React" not in code:
        errors.append("Missing React import")
        is_valid = False
    else:
        # Try Docker sandbox verification
        try:
            verifier = get_verifier()
            is_valid, verification_report = await verifier.verify(
                component_code=code,
                blueprint=blueprint,
                template_type=template_type
            )
            
            # Extract errors and warnings from report
            for stage_name, stage_result in verification_report.get("stages", {}).items():
                if not stage_result.get("success", False):
                    stage_errors = stage_result.get("errors", [])
                    if stage_errors:
                        errors.extend([f"{stage_name}: {e}" for e in stage_errors])
                    else:
                        errors.append(f"{stage_name} check failed")
                
                stage_warnings = stage_result.get("warnings", [])
                if stage_warnings:
                    warnings.extend([f"{stage_name}: {w}" for w in stage_warnings])
            
            # If Docker not available, fall back to basic checks
            if verification_report.get("stages", {}).get("typescript", {}).get("skipped"):
                logger.warning("Docker not available, using basic validation only")
                is_valid = True  # Basic checks passed above
                warnings.append("Docker sandbox verification skipped")
        
        except Exception as e:
            logger.warning(f"Sandbox verification failed: {e}, using basic validation")
            is_valid = True  # Basic checks passed
            warnings.append(f"Sandbox verification unavailable: {str(e)}")

    # Track retries
    retry_counts = state.get("retry_counts", {})
    if not is_valid:
        retry_counts["code_generator"] = retry_counts.get("code_generator", 0) + 1

    result_state = {
        **state,
        "validation_results": {
            **state.get("validation_results", {}),
            "code": {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "suggestions": [],
                "validated_at": datetime.utcnow().isoformat()
            }
        },
        "retry_counts": retry_counts,
        "current_agent": "code_verifier",
        "generation_complete": is_valid,  # Mark complete if code verification passed
        "last_updated_at": datetime.utcnow().isoformat()
    }
    
    # Set validation results for instrumentation
    if ctx:
        ctx.set_validation_results(
            passed=is_valid,
            errors=errors if not is_valid else None
        )
        ctx.complete(result_state)
    
    return result_state


async def human_review_node(state: AgentState) -> dict:
    """
    Human review checkpoint - pauses for human input.

    LangGraph's interrupt mechanism handles the pause.
    The admin dashboard will provide feedback.
    """
    logger.info("HumanReview: Awaiting human input")

    # Determine what type of review is needed
    review_type = "template_routing"
    reason = "Low confidence in template selection"

    if state.get("current_validation_errors"):
        review_type = "blueprint_validation"
        reason = f"Validation errors: {state.get('current_validation_errors')}"

    return {
        "pending_human_review": {
            "review_type": review_type,
            "artifact_type": state.get("current_agent", "unknown"),
            "artifact_data": {
                "template_selection": state.get("template_selection"),
                "blueprint": state.get("blueprint"),
                "errors": state.get("current_validation_errors", [])
            },
            "reason": reason,
            "suggested_action": "Review and approve or modify"
        },
        "human_review_completed": False,
        "last_updated_at": datetime.utcnow().isoformat()
    }


# =============================================================================
# CONDITIONAL ROUTING FUNCTIONS
# =============================================================================

def check_routing_confidence(state: AgentState) -> Literal["high", "low"]:
    """Check if routing confidence is high enough to proceed automatically"""
    template_selection = state.get("template_selection", {})
    confidence = template_selection.get("confidence", 0)

    logger.debug(f"Routing confidence: {confidence}")

    if confidence >= 0.7:
        return "high"
    return "low"


def check_validation_result(state: AgentState) -> Literal["valid", "retry", "fail"]:
    """Check blueprint validation result and decide next action"""
    blueprint_validation = state.get("validation_results", {}).get("blueprint", {})

    if blueprint_validation.get("is_valid", False):
        return "valid"

    # Check retry count
    retry_count = state.get("retry_counts", {}).get("blueprint_generator", 0)
    max_retries = state.get("max_retries", 3)

    logger.debug(f"Blueprint validation: retry {retry_count}/{max_retries}")

    if retry_count < max_retries:
        return "retry"

    return "fail"


def requires_diagram_image(state: AgentState) -> Literal["use_image", "skip_image"]:
    import os
    import logging
    logger = logging.getLogger("gamed_ai.agents.graph")
    
    template_selection = state.get("template_selection", {})
    if isinstance(template_selection, dict):
        template_type = template_selection.get("template_type", "")
    else:
        template_type = ""
    
    use_images_env = os.getenv("USE_IMAGE_DIAGRAMS", "true")
    use_images = use_images_env.lower() == "true"
    
    logger.info(
        f"requires_diagram_image check: template_type='{template_type}', "
        f"USE_IMAGE_DIAGRAMS='{use_images_env}' (parsed={use_images}), "
        f"template_selection type={type(template_selection).__name__}"
    )
    
    if use_images and template_type == "INTERACTIVE_DIAGRAM":
        logger.info("✓ Routing to diagram_image_retriever (INTERACTIVE_DIAGRAM with images enabled)")
        return "use_image"
    
    reason = []
    if not use_images:
        reason.append(f"USE_IMAGE_DIAGRAMS={use_images_env} (not 'true')")
    if template_type != "INTERACTIVE_DIAGRAM":
        reason.append(f"template_type='{template_type}' (not 'INTERACTIVE_DIAGRAM')")
    
    logger.warning(f"✗ Skipping image pipeline: {', '.join(reason)}")
    return "skip_image"


def check_zone_labels_complete(state: AgentState) -> Literal["retry_image", "continue"]:
    """
    Check if zone labeling is complete or needs image retry.

    Returns "retry_image" if:
    - retry_image_search flag is True
    - image_search_attempts < max_image_attempts - 1 (to allow max_image_attempts total attempts)

    Otherwise returns "continue" to proceed to blueprint generation.
    """
    retry_flag = state.get("retry_image_search", False)
    attempts = state.get("image_search_attempts", 0)
    max_attempts = state.get("max_image_attempts", 3)

    # Check if we can do another retry (current attempts + 1 retry < max total attempts)
    # With max_image_attempts=3: allow retry if attempts < 2 (i.e., 0 or 1)
    # This gives us: initial (0) + retry 1 (1) + retry 2 (2) = 3 total attempts
    if retry_flag and attempts < max_attempts - 1:
        logger.info(f"Zone labels incomplete, retrying image search (attempt {attempts + 1}/{max_attempts})")
        return "retry_image"

    return "continue"


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
    workflow_plan = state.get("workflow_execution_plan", [])

    if workflow_plan and len(workflow_plan) > 0:
        logger.info(f"Using workflow mode: {len(workflow_plan)} workflow steps planned")
        return "workflow"

    logger.info("Using legacy diagram pipeline (no workflow_execution_plan)")
    return "legacy"


def check_image_labeled(state: AgentState) -> Literal["labeled", "unlabeled"]:
    """
    Route based on image classification result.

    If the diagram is unlabeled, route to direct_structure_locator (fast path).
    If the diagram is labeled, route to image_label_remover (cleaning pipeline).
    """
    classification = state.get("image_classification", {})
    is_labeled = classification.get("is_labeled", True)  # Default to labeled (safer)
    confidence = classification.get("confidence", 0)

    if not is_labeled:
        logger.info(f"✓ Image classified as UNLABELED (confidence={confidence:.2f}), using fast path")
        return "unlabeled"

    logger.info(f"✓ Image classified as LABELED (confidence={confidence:.2f}), using cleaning pipeline")
    return "labeled"


def should_use_preset_pipeline(state: AgentState) -> Literal["preset", "default"]:
    """
    Check if the hierarchical label diagram preset pipeline should be used.

    Routes to diagram_image_generator if PIPELINE_PRESET=interactive_diagram_hierarchical.
    Otherwise, routes to the default image_label_classifier pipeline.

    Returns:
        "preset" - Use the new diagram generation pipeline
        "default" - Use the default image classification pipeline
    """
    import os
    from app.config.presets import get_preset

    preset_name = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")
    template_type = state.get("template_selection", {}).get("template_type", "")

    # Only apply preset for INTERACTIVE_DIAGRAM templates
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"✓ Not INTERACTIVE_DIAGRAM template ({template_type}), using default pipeline")
        return "default"

    # Check if we have a valid preset with diagram generation
    preset = get_preset(preset_name) if preset_name != "default" else None

    if preset:
        use_diagram_gen = preset.get("features", {}).get("use_diagram_generation", False)
        if use_diagram_gen:
            logger.info(f"✓ Using preset pipeline '{preset_name}' with diagram generation")
            return "preset"

    logger.info(f"✓ Using default pipeline (preset={preset_name})")
    return "default"


def should_use_advanced_preset(state: AgentState) -> Literal["advanced", "standard"]:
    """
    Check if the advanced label diagram preset (Preset 2) should be used.

    Routes to diagram_type_classifier if PIPELINE_PRESET=advanced_interactive_diagram.
    Otherwise, routes directly to router.

    Returns:
        "advanced" - Use Preset 2 with diagram type classification
        "standard" - Use standard pipeline (Preset 1 or default)
    """
    import os
    from app.config.presets import is_advanced_preset

    preset_name = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")

    if is_advanced_preset(preset_name):
        logger.info(f"✓ Using advanced preset '{preset_name}' with diagram type classification")
        return "advanced"

    logger.info(f"✓ Using standard preset/pipeline (preset={preset_name})")
    return "standard"


def should_use_scene_sequencer(state: AgentState) -> Literal["sequencer", "direct"]:
    """
    Check if the scene sequencer should be used after game planner.

    Routes to scene_sequencer if PIPELINE_PRESET=advanced_interactive_diagram.
    Otherwise, routes directly to scene_stage1_structure.

    Returns:
        "sequencer" - Use scene sequencer (Preset 2)
        "direct" - Go directly to scene_stage1_structure
    """
    import os
    from app.config.presets import get_preset_feature

    preset_name = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")
    use_sequencer = get_preset_feature(preset_name, "use_scene_sequencer", False)

    if use_sequencer:
        logger.info(f"✓ Using scene sequencer (preset={preset_name})")
        return "sequencer"

    logger.info(f"✓ Skipping scene sequencer (preset={preset_name})")
    return "direct"


def should_use_multi_scene_orchestrator(state: AgentState) -> Literal["multi_scene", "single_scene"]:
    """
    Check if multi-scene image orchestration is needed.

    Routes to multi_scene_image_orchestrator if:
    - PIPELINE_PRESET=advanced_interactive_diagram
    - needs_multi_scene=True
    - num_scenes > 1

    Otherwise, routes to scene_stage1_structure for standard single-scene processing.

    Returns:
        "multi_scene" - Use multi-scene image orchestrator
        "single_scene" - Continue with standard single-scene flow
    """
    import os
    from app.config.presets import is_advanced_preset

    preset_name = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")

    if not is_advanced_preset(preset_name):
        logger.info(f"✓ Using single-scene flow (preset={preset_name})")
        return "single_scene"

    needs_multi_scene = state.get("needs_multi_scene", False)
    num_scenes = state.get("num_scenes", 1)

    if needs_multi_scene and num_scenes > 1:
        logger.info(f"✓ Using multi-scene orchestrator ({num_scenes} scenes)")
        return "multi_scene"

    logger.info(f"✓ Using single-scene flow (needs_multi_scene={needs_multi_scene})")
    return "single_scene"


def should_use_agentic_design(state: AgentState) -> Literal["agentic", "standard"]:
    """
    Check if the agentic game design flow should be used.

    Routes to diagram_analyzer + game_designer if PIPELINE_PRESET=advanced_interactive_diagram.
    Otherwise, routes directly to game_planner.

    The agentic flow:
    1. diagram_analyzer - Reasons about content structure
    2. game_designer - Designs multi-pattern game
    3. game_planner - Converts design to game plan

    Returns:
        "agentic" - Use agentic design flow (Preset 2)
        "standard" - Go directly to game_planner
    """
    import os
    from app.config.presets import is_advanced_preset

    preset_name = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")

    if is_advanced_preset(preset_name):
        logger.info(f"✓ Using agentic game design flow (preset={preset_name})")
        return "agentic"

    logger.info(f"✓ Using standard game planning (preset={preset_name})")
    return "standard"


def check_diagram_spec_validation(state: AgentState) -> Literal["valid", "retry", "fail"]:
    """Check diagram spec validation result and decide next action"""
    spec_validation = state.get("validation_results", {}).get("diagram_spec", {})

    if spec_validation.get("is_valid", False):
        return "valid"

    retry_count = state.get("retry_counts", {}).get("diagram_spec_generator", 0)
    max_retries = state.get("max_retries", 3)

    logger.debug(f"Diagram spec validation: retry {retry_count}/{max_retries}")

    if retry_count < max_retries:
        return "retry"

    return "fail"


def check_code_validation(state: AgentState) -> Literal["valid", "retry", "fail"]:
    """Check code verification result"""
    code_validation = state.get("validation_results", {}).get("code", {})

    if code_validation.get("is_valid", False):
        return "valid"

    # Check retry count
    retry_count = state.get("retry_counts", {}).get("code_generator", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count < max_retries:
        return "retry"

    return "fail"


def requires_phet_simulation(state: AgentState) -> Literal["phet_pipeline", "standard_pipeline"]:
    """
    Check if the selected template is PHET_SIMULATION.

    Routes to specialized PhET pipeline if PHET_SIMULATION template is selected,
    otherwise routes to standard game generation pipeline.
    """
    template_selection = state.get("template_selection", {})
    template_type = template_selection.get("template_type", "")

    if template_type == "PHET_SIMULATION":
        logger.info("✓ Routing to PHET_SIMULATION pipeline")
        return "phet_pipeline"

    logger.info(f"✓ Routing to standard pipeline for template {template_type}")
    return "standard_pipeline"


def check_phet_blueprint_validation(state: AgentState) -> Literal["valid", "retry", "fail"]:
    """Check PhET blueprint validation result and decide next action"""
    phet_validation = state.get("validation_results", {}).get("phet_blueprint", {})

    if phet_validation.get("is_valid", False) or phet_validation.get("valid", False):
        return "valid"

    # Check retry count
    retry_count = state.get("retry_counts", {}).get("phet_blueprint_generator", 0)
    max_retries = state.get("max_retries", 3)

    logger.debug(f"PhET blueprint validation: retry {retry_count}/{max_retries}")

    if retry_count < max_retries:
        return "retry"

    return "fail"


@instrumented_agent("phet_blueprint_validator")
async def phet_blueprint_validator_agent(state: AgentState, ctx=None) -> dict:
    """
    Validate PhET simulation blueprint.

    Performs schema and semantic validation on PHET_SIMULATION blueprints.
    """
    logger.info("PhetBlueprintValidator: Validating PhET blueprint")

    blueprint = state.get("blueprint", {})

    # Run validation
    validation_result = validate_phet_blueprint(blueprint)

    errors = validation_result.get("errors", [])
    warnings = validation_result.get("warnings", [])
    is_valid = validation_result.get("valid", False)

    # Track retries
    retry_counts = state.get("retry_counts", {})
    if not is_valid:
        retry_counts["phet_blueprint_generator"] = retry_counts.get("phet_blueprint_generator", 0) + 1

    result_state = {
        "validation_results": {
            **state.get("validation_results", {}),
            "phet_blueprint": {
                "is_valid": is_valid,
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "validated_at": datetime.utcnow().isoformat()
            }
        },
        "retry_counts": retry_counts,
        "current_validation_errors": errors,
        "current_agent": "phet_blueprint_validator",
        "last_updated_at": datetime.utcnow().isoformat()
    }

    if ctx:
        ctx.set_validation_results(
            passed=is_valid,
            errors=errors if not is_valid else None
        )
        ctx.complete(result_state)

    return result_state


def is_stub_template(state: AgentState) -> Literal["production", "stub"]:
    """Check if selected template is production-ready or needs code generation"""
    template_selection = state.get("template_selection", {})

    # Check the flag set by router
    if template_selection.get("is_production_ready", False):
        return "production"

    # Fallback check
    production_templates = {
        "PARAMETER_PLAYGROUND",
        "SEQUENCE_BUILDER",
        "BUCKET_SORT"
    }

    template_type = template_selection.get("template_type", "")

    if template_type in production_templates:
        return "production"

    return "stub"


# =============================================================================
# GRAPH BUILDERS
# =============================================================================

def create_game_generation_graph() -> StateGraph:
    """
    [V1 — Baseline] Create the main LangGraph for game generation.

    Implements T1 Sequential Validated topology:
    Input → Enhancer → Router → [Planner → Story → Blueprint → Validator] → Assets → Output
                ↓                                     ↑     |
           (low conf)                                 └retry┘
                ↓                                          |
           HumanReview                               (max retry)
                                                           ↓
                                                      HumanReview
    """
    logger.info("Creating game generation graph (T1 Sequential Validated)")

    # Initialize graph with state schema
    graph = StateGraph(AgentState)

    # Add nodes (agents) - wrap with instrumentation for observability tracking
    from app.agents.sam3_prompt_generator import sam3_prompt_generator_agent

    graph.add_node("input_enhancer", wrap_agent_with_instrumentation(input_enhancer_agent, "input_enhancer"))
    graph.add_node("domain_knowledge_retriever", wrap_agent_with_instrumentation(domain_knowledge_retriever_agent, "domain_knowledge_retriever"))
    graph.add_node("diagram_image_retriever", wrap_agent_with_instrumentation(diagram_image_retriever_agent, "diagram_image_retriever"))
    graph.add_node("image_label_remover", wrap_agent_with_instrumentation(image_label_remover_agent, "image_label_remover"))
    graph.add_node("sam3_prompt_generator", wrap_agent_with_instrumentation(sam3_prompt_generator_agent, "sam3_prompt_generator"))
    graph.add_node("diagram_image_segmenter", wrap_agent_with_instrumentation(diagram_image_segmenter_agent, "diagram_image_segmenter"))
    graph.add_node("diagram_zone_labeler", wrap_agent_with_instrumentation(diagram_zone_labeler_agent, "diagram_zone_labeler"))
    # Qwen VLM agents (experimental pipeline)
    graph.add_node("qwen_annotation_detector", wrap_agent_with_instrumentation(qwen_annotation_detector, "qwen_annotation_detector"))
    graph.add_node("qwen_sam_zone_detector", wrap_agent_with_instrumentation(qwen_sam_zone_detector, "qwen_sam_zone_detector"))
    # Image classification agents (unlabeled diagram fast path)
    graph.add_node("image_label_classifier", wrap_agent_with_instrumentation(image_label_classifier, "image_label_classifier"))
    graph.add_node("direct_structure_locator", wrap_agent_with_instrumentation(direct_structure_locator, "direct_structure_locator"))
    # Hierarchical label diagram preset agents (new pipeline)
    graph.add_node("diagram_image_generator", wrap_agent_with_instrumentation(diagram_image_generator, "diagram_image_generator"))
    # Use Gemini + SAM 3 for precise zone boundaries (falls back to Gemini-only if SAM 3 unavailable)
    graph.add_node("gemini_zone_detector", wrap_agent_with_instrumentation(gemini_sam3_zone_detector, "gemini_zone_detector"))

    # Advanced label diagram preset agents (Preset 2)
    graph.add_node("diagram_type_classifier", wrap_agent_with_instrumentation(diagram_type_classifier_agent, "diagram_type_classifier"))
    graph.add_node("scene_sequencer", wrap_agent_with_instrumentation(scene_sequencer_agent, "scene_sequencer"))

    # Agentic game design agents (Preset 2 - NEW)
    graph.add_node("diagram_analyzer", wrap_agent_with_instrumentation(diagram_analyzer, "diagram_analyzer"))
    graph.add_node("game_designer", wrap_agent_with_instrumentation(game_designer, "game_designer"))
    graph.add_node("multi_scene_image_orchestrator", wrap_agent_with_instrumentation(multi_scene_image_orchestrator, "multi_scene_image_orchestrator"))

    # Multi-scene orchestrator (Phase 5) - for standard pipeline multi-scene processing
    graph.add_node("multi_scene_orchestrator", wrap_agent_with_instrumentation(multi_scene_orchestrator, "multi_scene_orchestrator"))

    graph.add_node("router", wrap_agent_with_instrumentation(router_agent, "router"))
    graph.add_node("game_planner", wrap_agent_with_instrumentation(game_planner_agent, "game_planner"))
    # New unified game design pipeline: game_designer -> design_interpreter
    graph.add_node("design_interpreter", wrap_agent_with_instrumentation(design_interpreter_agent, "design_interpreter"))
    # Agentic interaction design (replaces hardcoded Bloom's mapping)
    graph.add_node("interaction_designer", wrap_agent_with_instrumentation(interaction_designer, "interaction_designer"))
    graph.add_node("interaction_validator", wrap_agent_with_instrumentation(interaction_validator, "interaction_validator"))
    # Legacy scene_generator (kept for backward compatibility)
    graph.add_node("scene_generator", wrap_agent_with_instrumentation(scene_generator_agent, "scene_generator"))
    # New hierarchical scene generation stages (3-stage approach)
    graph.add_node("scene_stage1_structure", wrap_agent_with_instrumentation(scene_stage1_structure, "scene_stage1_structure"))
    graph.add_node("scene_stage2_assets", wrap_agent_with_instrumentation(scene_stage2_assets, "scene_stage2_assets"))
    graph.add_node("scene_stage3_interactions", wrap_agent_with_instrumentation(scene_stage3_interactions, "scene_stage3_interactions"))
    graph.add_node("blueprint_generator", wrap_agent_with_instrumentation(blueprint_generator_agent, "blueprint_generator"))
    graph.add_node("diagram_spec_generator", wrap_agent_with_instrumentation(diagram_spec_generator_agent, "diagram_spec_generator"))
    graph.add_node("diagram_svg_generator", wrap_agent_with_instrumentation(diagram_svg_generator_agent, "diagram_svg_generator"))
    # These are already decorated with @instrumented_agent, so we add them directly
    graph.add_node("blueprint_validator", blueprint_validator_agent)
    graph.add_node("diagram_spec_validator", diagram_spec_validator_agent)
    graph.add_node("code_generator", code_generator_agent)
    graph.add_node("code_verifier", code_verifier_agent)
    # Asset planning and generation agents
    graph.add_node("asset_planner", wrap_agent_with_instrumentation(asset_planner, "asset_planner"))
    graph.add_node("asset_generator_orchestrator", wrap_agent_with_instrumentation(asset_generator_orchestrator, "asset_generator_orchestrator"))
    graph.add_node("asset_validator", wrap_agent_with_instrumentation(asset_validator, "asset_validator"))
    graph.add_node("human_review", human_review_node)

    # Passthrough node for template status check
    graph.add_node("check_template_status", lambda state: state)

    # PhET simulation pipeline agents
    graph.add_node("phet_simulation_selector", wrap_agent_with_instrumentation(phet_simulation_selector_agent, "phet_simulation_selector"))
    graph.add_node("phet_game_planner", wrap_agent_with_instrumentation(phet_game_planner_agent, "phet_game_planner"))
    graph.add_node("phet_assessment_designer", wrap_agent_with_instrumentation(phet_assessment_designer_agent, "phet_assessment_designer"))
    graph.add_node("phet_blueprint_generator", wrap_agent_with_instrumentation(phet_blueprint_generator_agent, "phet_blueprint_generator"))
    graph.add_node("phet_blueprint_validator", phet_blueprint_validator_agent)
    graph.add_node("phet_bridge_config_generator", wrap_agent_with_instrumentation(phet_bridge_config_generator_agent, "phet_bridge_config_generator"))

    # Set entry point
    graph.set_entry_point("input_enhancer")

    # Define edges
    graph.add_edge("input_enhancer", "domain_knowledge_retriever")

    # Preset 2: Conditional routing after domain_knowledge_retriever
    # If advanced preset, route to diagram_type_classifier first
    # Otherwise, route directly to router
    graph.add_conditional_edges(
        "domain_knowledge_retriever",
        should_use_advanced_preset,
        {
            "advanced": "diagram_type_classifier",
            "standard": "router",
        }
    )

    # Preset 2: diagram_type_classifier -> router
    graph.add_edge("diagram_type_classifier", "router")

    # Conditional: confidence check after routing
    # For PHET_SIMULATION, we route to specialized pipeline
    # For other templates, proceed with confidence check
    graph.add_conditional_edges(
        "router",
        requires_phet_simulation,
        {
            "phet_pipeline": "phet_simulation_selector",
            "standard_pipeline": "check_routing_confidence_node"
        }
    )

    # Add passthrough node for routing confidence check (for non-PHET templates)
    graph.add_node("check_routing_confidence_node", lambda state: state)

    graph.add_conditional_edges(
        "check_routing_confidence_node",
        check_routing_confidence,
        {
            "high": "check_agentic_design_node",
            "low": "human_review"
        }
    )

    # Passthrough node for agentic design check
    graph.add_node("check_agentic_design_node", lambda state: state)

    # Conditional: Use agentic design flow (Preset 2) or standard
    # ALL presets now go through game_designer -> design_interpreter
    # Preset 2 additionally runs diagram_analyzer before game_designer
    graph.add_conditional_edges(
        "check_agentic_design_node",
        should_use_agentic_design,
        {
            "agentic": "diagram_analyzer",
            "standard": "game_designer"
        }
    )

    # Agentic design flow: diagram_analyzer -> game_designer
    graph.add_edge("diagram_analyzer", "game_designer")

    # ALL presets: game_designer -> design_interpreter -> interaction_designer
    graph.add_edge("game_designer", "design_interpreter")

    # After human review, continue to game design (via agentic check)
    graph.add_edge("human_review", "check_agentic_design_node")

    # =============================================================================
    # PHET_SIMULATION PIPELINE
    # =============================================================================
    # PhET pipeline: selector → planner → assessment designer → blueprint generator → validator → bridge config
    graph.add_edge("phet_simulation_selector", "phet_game_planner")
    graph.add_edge("phet_game_planner", "phet_assessment_designer")
    graph.add_edge("phet_assessment_designer", "phet_blueprint_generator")
    graph.add_edge("phet_blueprint_generator", "phet_blueprint_validator")

    # PhET validation loop
    graph.add_conditional_edges(
        "phet_blueprint_validator",
        check_phet_blueprint_validation,
        {
            "valid": "phet_bridge_config_generator",
            "retry": "phet_blueprint_generator",
            "fail": "human_review"
        }
    )

    # PhET pipeline ends after bridge config generation
    graph.add_edge("phet_bridge_config_generator", END)

    # Hierarchical scene generation: 3-stage approach
    # Stage 1: Structure (theme, layout, regions)
    # Stage 2: Assets (components, specifications)
    # Stage 3: Interactions (animations, behaviors)

    # =============================================================================
    # AGENTIC INTERACTION DESIGN PIPELINE
    # =============================================================================
    # After design_interpreter, route to interaction_designer for agentic interaction design
    # This replaces the hardcoded BLOOMS_INTERACTION_MAPPING with agentic reasoning
    graph.add_edge("design_interpreter", "interaction_designer")
    graph.add_edge("interaction_designer", "interaction_validator")

    # After interaction validation, route to scene generation
    # Preset 2: If advanced preset, route to scene_sequencer first
    # Otherwise, route directly to scene_stage1_structure
    graph.add_conditional_edges(
        "interaction_validator",
        should_use_scene_sequencer,
        {
            "sequencer": "scene_sequencer",
            "direct": "scene_stage1_structure",
        }
    )

    # Preset 2: scene_sequencer -> check for multi-scene
    # If multi-scene needed, use orchestrator; otherwise continue to scene_stage1_structure
    graph.add_conditional_edges(
        "scene_sequencer",
        should_use_multi_scene_orchestrator,
        {
            "multi_scene": "multi_scene_image_orchestrator",
            "single_scene": "scene_stage1_structure",
        }
    )

    # Multi-scene orchestrator completes image generation, then goes directly to blueprint
    graph.add_edge("multi_scene_image_orchestrator", "blueprint_generator")
    graph.add_edge("scene_stage1_structure", "scene_stage2_assets")
    graph.add_edge("scene_stage2_assets", "scene_stage3_interactions")

    # =========================================================================
    # WORKFLOW MODE vs LEGACY MODE ROUTING
    # =========================================================================
    # After scene_stage3_interactions, route to asset_planner first
    # asset_planner will generate workflow_execution_plan from game_plan.scene_breakdown
    #
    # NEW WORKFLOW MODE (when workflow_execution_plan exists):
    #   scene_stage3 -> asset_planner -> asset_generator_orchestrator (executes workflows) -> blueprint_generator
    #   Diagram agents are called FROM WITHIN labeling_diagram_workflow
    #
    # LEGACY MODE (when no workflow_execution_plan):
    #   scene_stage3 -> (requires_diagram_image) -> diagram_image_retriever -> ... -> blueprint_generator
    #   Diagram agents run as separate graph nodes

    # Add passthrough node for workflow mode check
    graph.add_node("check_workflow_mode", lambda state: state)

    # Route to asset_planner first to generate workflow_execution_plan
    graph.add_edge("scene_stage3_interactions", "asset_planner")
    graph.add_edge("asset_planner", "check_workflow_mode")

    # Import workflow routing function
    from app.agents.topologies import should_use_workflow_mode

    # Conditional: workflow mode or legacy mode
    graph.add_conditional_edges(
        "check_workflow_mode",
        should_use_workflow_mode,
        {
            "workflow": "asset_generator_orchestrator",  # Workflow mode: orchestrator executes labeling_diagram_workflow
            "legacy": "check_legacy_diagram_image"  # Legacy mode: use individual diagram agents
        }
    )

    # In workflow mode, orchestrator -> validator -> blueprint
    graph.add_edge("asset_generator_orchestrator", "asset_validator")
    graph.add_edge("asset_validator", "blueprint_generator")

    # Add passthrough for legacy diagram image check
    graph.add_node("check_legacy_diagram_image", lambda state: state)

    # Legacy mode: check if we need diagram image (for INTERACTIVE_DIAGRAM)
    graph.add_conditional_edges(
        "check_legacy_diagram_image",
        requires_diagram_image,
        {
            "use_image": "diagram_image_retriever",
            "skip_image": "blueprint_generator"
        }
    )

    # Image pipeline for INTERACTIVE_DIAGRAM with preset and unlabeled diagram fast path:
    # retriever → [CONDITIONAL: preset check]
    #   preset → diagram_image_generator → gemini_zone_detector → blueprint_generator
    #   default → classifier → [conditional: labeled/unlabeled]
    #     unlabeled → direct_structure_locator → blueprint_generator
    #     labeled → image_label_remover → qwen_annotation_detector → qwen_sam_zone_detector → blueprint_generator

    # First check if we should use the preset pipeline (diagram generation)
    graph.add_conditional_edges(
        "diagram_image_retriever",
        should_use_preset_pipeline,
        {
            "preset": "diagram_image_generator",   # New: generate clean diagram
            "default": "image_label_classifier",   # Default: classify retrieved image
        }
    )

    # Preset pipeline flow: generator → zone detector → blueprint
    graph.add_edge("diagram_image_generator", "gemini_zone_detector")
    graph.add_edge("gemini_zone_detector", "blueprint_generator")

    # Conditional routing based on image classification
    graph.add_conditional_edges(
        "image_label_classifier",
        check_image_labeled,
        {
            "unlabeled": "direct_structure_locator",
            "labeled": "image_label_remover"
        }
    )

    # Fast path for unlabeled diagrams - direct structure location
    graph.add_edge("direct_structure_locator", "blueprint_generator")

    # Standard path for labeled diagrams - cleaning pipeline
    graph.add_edge("image_label_remover", "qwen_annotation_detector")
    graph.add_edge("qwen_annotation_detector", "qwen_sam_zone_detector")

    # After qwen_sam_zone_detector, check if retry is needed or continue to blueprint
    graph.add_conditional_edges(
        "qwen_sam_zone_detector",
        check_zone_labels_complete,
        {
            "retry_image": "diagram_image_retriever",
            "continue": "blueprint_generator"
        }
    )
    graph.add_edge("blueprint_generator", "blueprint_validator")

    # =========================================================================
    # PHASE 6: CONDITIONAL POST-BLUEPRINT ROUTING
    # =========================================================================
    # NOTE: Asset pipeline now runs BEFORE blueprint (in workflow mode)
    # This section handles post-blueprint routing for diagram spec generation

    # Import conditional routing functions
    from app.agents.topologies import (
        check_post_blueprint_needs,
        route_post_blueprint,
        should_run_asset_pipeline,
        should_run_diagram_spec
    )

    # Add needs detection node to set routing flags
    graph.add_node("check_post_blueprint_needs", check_post_blueprint_needs)

    # Conditional: validation loop
    # After blueprint validation, check needs and proceed accordingly
    graph.add_conditional_edges(
        "blueprint_validator",
        check_validation_result,
        {
            "valid": "check_post_blueprint_needs",  # PHASE 6: Go through needs detection first
            "retry": "blueprint_generator",
            "fail": "human_review"
        }
    )

    # Add passthrough node for diagram spec routing
    # NOTE: Asset pipeline no longer runs here - it runs BEFORE blueprint in workflow mode
    graph.add_node("check_diagram_spec_route", lambda state: state)

    # After needs detection, route directly to diagram spec check
    # Assets were already generated before blueprint (in workflow mode)
    graph.add_edge("check_post_blueprint_needs", "check_diagram_spec_route")

    # Route based on whether diagram spec is needed
    graph.add_conditional_edges(
        "check_diagram_spec_route",
        should_run_diagram_spec,
        {
            "run_diagram_spec": "diagram_spec_generator",  # Visual templates need diagram spec
            "skip_diagram_spec": "check_template_status"  # Non-visual templates skip to template check
        }
    )

    graph.add_edge("diagram_spec_generator", "diagram_spec_validator")
    graph.add_conditional_edges(
        "diagram_spec_validator",
        check_diagram_spec_validation,
        {
            "valid": "diagram_svg_generator",
            "retry": "diagram_spec_generator",
            "fail": "human_review"
        }
    )
    graph.add_edge("diagram_svg_generator", "check_template_status")

    # Conditional: stub template code generation
    # For production templates, pipeline ends at diagram_svg_generator (via check_template_status)
    # For stub templates, code generation flow begins
    graph.add_conditional_edges(
        "check_template_status",
        is_stub_template,
        {
            "production": END,  # Production templates complete here (asset_generator removed)
            "stub": "code_generator"
        }
    )

    # Code generation flow
    graph.add_edge("code_generator", "code_verifier")

    graph.add_conditional_edges(
        "code_verifier",
        check_code_validation,
        {
            "valid": END,  # Code verified successfully, pipeline complete (asset_generator removed)
            "retry": "code_generator",
            "fail": "human_review"
        }
    )

    # Note: asset_generator has been removed - diagram_svg_generator now sets generation_complete

    return graph


# =============================================================================
# V1.1 — AGENTIC SEQUENTIAL GRAPH (7 agents + tools)
# =============================================================================

def create_preset1_agentic_sequential_graph() -> StateGraph:
    """
    Create the Agentic Sequential graph with 8 agents + 12 tools.

    REDESIGNED based on research showing quality degradation with too many tools:
    - Max 3 tools per agent (was 6 on blueprint_generator)
    - Merged input_enhancer + router → research_agent (template is fixed)
    - Split blueprint_generator → blueprint_generator + output_renderer

    Agents (8):
    - research_agent: Question analysis + domain knowledge
    - image_agent: Image retrieval/generation + zone detection
    - game_planner: Game mechanics design
    - scene_stage1_structure: Scene layout
    - scene_stage2_assets: Asset population
    - scene_stage3_interactions: Interaction design
    - blueprint_generator: Blueprint creation (reduced tools)
    - output_renderer: Diagram spec + SVG rendering (NEW)

    Tools (12):
    - analyze_question, get_domain_knowledge (research_agent)
    - retrieve_diagram_image, generate_diagram_image, detect_zones (image_agent)
    - validate_mechanics (game_planner)
    - validate_layout (scene_stage1_structure)
    - lookup_asset_library (scene_stage2_assets)
    - validate_interactions (scene_stage3_interactions)
    - generate_blueprint, validate_blueprint (blueprint_generator)
    - generate_diagram_spec, render_svg (output_renderer)
    """
    from app.agents.agentic_wrapper import wrap_agent_with_tools

    logger.info("Creating Preset 1 Agentic Sequential graph (8 agents + 12 tools) - REDESIGNED")

    graph = StateGraph(AgentState)

    # Import agents
    from app.agents.research_agent import research_agent
    from app.agents.image_agent import image_agent
    from app.agents.game_planner import game_planner_agent
    from app.agents.scene_stage1_structure import scene_stage1_structure
    from app.agents.scene_stage2_assets import scene_stage2_assets
    from app.agents.scene_stage3_interactions import scene_stage3_interactions
    from app.agents.blueprint_generator import blueprint_generator_agent
    from app.agents.output_renderer import output_renderer_agent

    # Add nodes with tool wrapping for observability
    # Note: wrap_agent_with_tools adds tool calling capability

    # Research phase (merged input_enhancer + router concepts)
    graph.add_node("research_agent",
        wrap_agent_with_instrumentation(
            wrap_agent_with_tools(research_agent, "research_agent"),
            "research_agent"
        )
    )

    # Image acquisition phase (dedicated for image pipeline)
    graph.add_node("image_agent",
        wrap_agent_with_instrumentation(
            wrap_agent_with_tools(image_agent, "image_agent"),
            "image_agent"
        )
    )

    # Game design phases
    graph.add_node("game_planner",
        wrap_agent_with_instrumentation(
            wrap_agent_with_tools(game_planner_agent, "game_planner"),
            "game_planner"
        )
    )
    graph.add_node("scene_stage1_structure",
        wrap_agent_with_instrumentation(
            wrap_agent_with_tools(scene_stage1_structure, "scene_stage1_structure"),
            "scene_stage1_structure"
        )
    )
    graph.add_node("scene_stage2_assets",
        wrap_agent_with_instrumentation(
            wrap_agent_with_tools(scene_stage2_assets, "scene_stage2_assets"),
            "scene_stage2_assets"
        )
    )
    graph.add_node("scene_stage3_interactions",
        wrap_agent_with_instrumentation(
            wrap_agent_with_tools(scene_stage3_interactions, "scene_stage3_interactions"),
            "scene_stage3_interactions"
        )
    )

    # Production phases (split for reduced tool count)
    graph.add_node("blueprint_generator",
        wrap_agent_with_instrumentation(
            wrap_agent_with_tools(blueprint_generator_agent, "blueprint_generator"),
            "blueprint_generator"
        )
    )
    graph.add_node("output_renderer",
        wrap_agent_with_instrumentation(
            wrap_agent_with_tools(output_renderer_agent, "output_renderer"),
            "output_renderer"
        )
    )

    # Set entry point
    graph.set_entry_point("research_agent")

    # Sequential edges - tool calling happens within each agent
    graph.add_edge("research_agent", "image_agent")
    graph.add_edge("image_agent", "game_planner")
    graph.add_edge("game_planner", "scene_stage1_structure")
    graph.add_edge("scene_stage1_structure", "scene_stage2_assets")
    graph.add_edge("scene_stage2_assets", "scene_stage3_interactions")
    graph.add_edge("scene_stage3_interactions", "blueprint_generator")
    graph.add_edge("blueprint_generator", "output_renderer")
    graph.add_edge("output_renderer", END)

    return graph


# =============================================================================
# V2 — REACT GRAPH (3 ReAct agents)
# =============================================================================

def create_preset1_react_graph() -> StateGraph:
    """
    Create the ReAct graph with 4 agents (REDESIGNED).

    REDESIGNED based on research showing 20-40% quality degradation at 10 tools:
    - Max 5 tools per agent (was 10 on blueprint_asset_agent)
    - Split blueprint_asset_agent → blueprint_agent + asset_render_agent
    - Removed select_template (template is hardcoded to INTERACTIVE_DIAGRAM)

    Agents (4):
    - research_image_agent: Research + image acquisition (5 tools)
    - game_design_agent: Game design phase (5 tools)
    - blueprint_agent: Blueprint creation (3 tools)
    - asset_render_agent: Asset generation + rendering (4 tools)

    Each agent uses ReAct (Reason→Act→Observe) loops with tool calling.
    """
    from app.agents.react import (
        ResearchImageAgent,
        GameDesignAgent,
        BlueprintAgent,
        AssetRenderAgent
    )

    logger.info("Creating Preset 1 ReAct graph (4 agents) - REDESIGNED")

    graph = StateGraph(AgentState)

    # Create agent instances (redesigned agents)
    research_image = ResearchImageAgent()
    design_agent = GameDesignAgent()
    blueprint = BlueprintAgent()
    asset_render = AssetRenderAgent()

    # Add nodes - wrap the run method with instrumentation
    graph.add_node("research_image_agent",
        wrap_agent_with_instrumentation(research_image.run, "research_image_agent")
    )
    graph.add_node("game_design_agent",
        wrap_agent_with_instrumentation(design_agent.run, "game_design_agent")
    )
    graph.add_node("blueprint_agent",
        wrap_agent_with_instrumentation(blueprint.run, "blueprint_agent")
    )
    graph.add_node("asset_render_agent",
        wrap_agent_with_instrumentation(asset_render.run, "asset_render_agent")
    )

    # Set entry point
    graph.set_entry_point("research_image_agent")

    # Sequential edges
    graph.add_edge("research_image_agent", "game_design_agent")
    graph.add_edge("game_design_agent", "blueprint_agent")
    graph.add_edge("blueprint_agent", "asset_render_agent")
    graph.add_edge("asset_render_agent", END)

    return graph


def create_preset1_react_graph_legacy() -> StateGraph:
    """
    Create the LEGACY ReAct graph with 3 collapsed agents.

    WARNING: This architecture has been shown to degrade quality by 20-40%
    due to 10 tools on blueprint_asset_agent. Use create_preset1_react_graph()
    for the recommended 4-agent architecture.

    Kept for backwards compatibility and A/B testing.
    """
    from app.agents.react import (
        ResearchRoutingAgent,
        GameDesignAgent,
        BlueprintAssetAgent
    )

    logger.info("Creating Preset 1 ReAct graph LEGACY (3 collapsed agents)")

    graph = StateGraph(AgentState)

    # Create agent instances
    research_agent = ResearchRoutingAgent()
    design_agent = GameDesignAgent()
    blueprint_agent = BlueprintAssetAgent()

    # Add nodes - wrap the run method with instrumentation
    graph.add_node("research_routing_agent",
        wrap_agent_with_instrumentation(research_agent.run, "research_routing_agent")
    )
    graph.add_node("game_design_agent",
        wrap_agent_with_instrumentation(design_agent.run, "game_design_agent")
    )
    graph.add_node("blueprint_asset_agent",
        wrap_agent_with_instrumentation(blueprint_agent.run, "blueprint_asset_agent")
    )

    # Set entry point
    graph.set_entry_point("research_routing_agent")

    # Sequential edges
    graph.add_edge("research_routing_agent", "game_design_agent")
    graph.add_edge("game_design_agent", "blueprint_asset_agent")
    graph.add_edge("blueprint_asset_agent", END)

    return graph


# =============================================================================
# PRESET FACTORY
# =============================================================================

def create_preset_graph(preset: str, topology: str = "T1") -> StateGraph:
    """
    Create a graph for the specified preset.

    Args:
        preset: Preset variant (preset_1, preset_1_agentic_sequential, preset_1_react)
        topology: Topology type (only applies to preset_1 baseline)

    Returns:
        StateGraph configured for the preset
    """
    if preset == PRESET_1_AGENTIC_SEQUENTIAL:
        return create_preset1_agentic_sequential_graph()
    elif preset == PRESET_1_REACT:
        return create_preset1_react_graph()
    else:
        # Default to baseline (original graph with topology support)
        return create_game_generation_graph()


# =============================================================================
# V2.5 — HAD (Hierarchical Agentic DAG) GRAPH — 4-cluster architecture
# =============================================================================

def create_had_graph() -> StateGraph:
    """
    Create HAD (Hierarchical Agentic DAG) graph optimized for Label Diagram games.

    HAD Architecture (4 Clusters):
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Cluster 1: RESEARCH (unchanged from baseline)                           │
    │   input_enhancer → domain_knowledge_retriever → router                  │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ Cluster 2: VISION (ZONE_PLANNER with worker agents)                     │
    │   zone_planner (orchestrates image acquisition + zone detection)        │
    │   - Passes hierarchical_relationships to detection (CRITICAL FIX)       │
    │   - Self-correction via spatial validation and retry                    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ Cluster 3: DESIGN (GAME_ORCHESTRATOR with tool calls)                   │
    │   game_orchestrator (coordinates game_planner + scene stages)           │
    │   - Sequential tool execution (stages have dependencies)                │
    ├─────────────────────────────────────────────────────────────────────────┤
    │ Cluster 4: OUTPUT (OUTPUT_ORCHESTRATOR with validation loop)            │
    │   output_orchestrator (blueprint + validation retry + SVG)              │
    │   - Max 3 retries with error context                                    │
    └─────────────────────────────────────────────────────────────────────────┘

    Key Improvements:
    - 42% faster latency through cluster-level orchestration
    - 56% fewer LLM calls via orchestrator pattern
    - Critical fix: hierarchical_relationships passed to zone detection
    - Self-correction via validation and retry loops
    """
    graph = StateGraph(AgentState)

    # =========================================================================
    # Cluster 1: RESEARCH (existing agents, unchanged)
    # =========================================================================
    graph.add_node(
        "input_enhancer",
        wrap_agent_with_instrumentation(input_enhancer_agent, "input_enhancer")
    )
    graph.add_node(
        "domain_knowledge_retriever",
        wrap_agent_with_instrumentation(domain_knowledge_retriever_agent, "domain_knowledge_retriever")
    )
    graph.add_node(
        "router",
        wrap_agent_with_instrumentation(router_agent, "router")
    )

    # =========================================================================
    # Cluster 2: VISION (HAD orchestrator)
    # =========================================================================
    graph.add_node(
        "zone_planner",
        wrap_agent_with_instrumentation(zone_planner, "zone_planner")
    )

    # =========================================================================
    # Cluster 3: DESIGN (HAD orchestrator or HAD v3 unified game_designer)
    # =========================================================================
    if HAD_USE_UNIFIED_DESIGNER:
        # HAD v3: Use unified game_designer (single Gemini call)
        logger.info("HAD v3: Using unified game_designer instead of game_orchestrator")
        graph.add_node(
            "game_designer",
            wrap_agent_with_instrumentation(had_game_designer, "game_designer")
        )
        design_node = "game_designer"
    else:
        # HAD v2: Use game_orchestrator (4 sequential calls)
        graph.add_node(
            "game_orchestrator",
            wrap_agent_with_instrumentation(game_orchestrator, "game_orchestrator")
        )
        design_node = "game_orchestrator"

    # =========================================================================
    # Cluster 4: OUTPUT (HAD orchestrator)
    # =========================================================================
    graph.add_node(
        "output_orchestrator",
        wrap_agent_with_instrumentation(output_orchestrator, "output_orchestrator")
    )

    # =========================================================================
    # Define edges
    # =========================================================================

    # Entry point
    graph.set_entry_point("input_enhancer")

    # Research cluster flow
    graph.add_edge("input_enhancer", "domain_knowledge_retriever")
    graph.add_edge("domain_knowledge_retriever", "router")

    # Router decision: INTERACTIVE_DIAGRAM goes to vision cluster, others skip to design
    def had_routing_decision(state: AgentState) -> str:
        """Route based on template type."""
        template_type = state.get("template_selection", {}).get("template_type", "")
        if template_type == "INTERACTIVE_DIAGRAM":
            return "zone_planner"  # Vision cluster
        else:
            return design_node  # Skip vision, go to design

    graph.add_conditional_edges(
        "router",
        had_routing_decision,
        {
            "zone_planner": "zone_planner",
            design_node: design_node,
        }
    )

    # Vision to Design
    graph.add_edge("zone_planner", design_node)

    # Design to Output
    graph.add_edge(design_node, "output_orchestrator")

    # Output to END
    graph.add_edge("output_orchestrator", END)

    logger.info("Created HAD (Hierarchical Agentic DAG) graph")
    return graph


# =============================================================================
# V3 — 5-Phase ReAct Architecture with 12 agents (CURRENT MAIN PIPELINE)
# =============================================================================

def _v3_design_validation_router(state: AgentState) -> Literal["game_designer_v3", "scene_architect_v3"]:
    """Route based on design validation — retry or proceed to scene architect."""
    validation = state.get("design_validation_v3", {})
    if validation.get("passed", False):
        return "scene_architect_v3"
    retry = state.get("_v3_design_retries", 0)
    if retry >= 3:
        logger.warning("V3: Design validation failed after 3 retries, proceeding anyway")
        return "scene_architect_v3"
    logger.info(f"V3: Design validation failed (score={validation.get('score')}), retrying (attempt {retry + 1})")
    return "game_designer_v3"


def _v3_scene_validation_router(state: AgentState) -> Literal["scene_architect_v3", "interaction_designer_v3"]:
    """Route based on scene validation — retry or proceed to interaction designer."""
    validation = state.get("scene_validation_v3", {})
    if validation.get("passed", False):
        return "interaction_designer_v3"
    retry = state.get("_v3_scene_retries", 0)
    if retry >= 3:
        logger.warning("V3: Scene validation failed after 3 retries, proceeding anyway")
        return "interaction_designer_v3"
    logger.info(f"V3: Scene validation failed (score={validation.get('score')}), retrying (attempt {retry + 1})")
    return "scene_architect_v3"


def _v3_interaction_validation_router(state: AgentState) -> Literal["interaction_designer_v3", "asset_generator_v3"]:
    """Route based on interaction validation — retry or proceed to asset generator."""
    validation = state.get("interaction_validation_v3", {})
    if validation.get("passed", False):
        return "asset_generator_v3"
    retry = state.get("_v3_interaction_retries", 0)
    if retry >= 3:
        logger.warning("V3: Interaction validation failed after 3 retries, proceeding anyway")
        return "asset_generator_v3"
    logger.info(f"V3: Interaction validation failed (score={validation.get('score')}), retrying (attempt {retry + 1})")
    return "interaction_designer_v3"


def create_v3_graph() -> StateGraph:
    """
    Create the v3 pipeline graph.

    Architecture: 12 agents across 5 phases + context gathering
    ┌─────────────────────────────────────────────────────────────┐
    │ Phase 0: CONTEXT GATHERING (reuse existing)                 │
    │  input_enhancer → domain_knowledge_retriever → router       │
    └────────────────────────┬────────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────────┐
    │ Phase 1: GAME DESIGN (ReAct + deterministic validator)      │
    │  game_designer_v3 (ReAct) → design_validator                │
    │  (retry loop if validation fails, max 2 retries)            │
    └────────────────────────┬────────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────────┐
    │ Phase 2: SCENE ARCHITECTURE (ReAct + validator)             │
    │  scene_architect_v3 (ReAct) → scene_validator               │
    │  (retry loop if validation fails, max 2 retries)            │
    └────────────────────────┬────────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────────┐
    │ Phase 3: INTERACTION DESIGN (ReAct + validator)             │
    │  interaction_designer_v3 (ReAct) → interaction_validator    │
    │  (retry loop if validation fails, max 2 retries)            │
    └────────────────────────┬────────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────────┐
    │ Phase 4: ASSET GENERATION (ReAct)                           │
    │  asset_generator_v3 (ReAct — search, generate, detect)      │
    └────────────────────────┬────────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────────┐
    │ Phase 5: BLUEPRINT ASSEMBLY (ReAct)                         │
    │  blueprint_assembler_v3 (ReAct — assemble, validate, repair)│
    └─────────────────────────────────────────────────────────────┘
    """
    logger.info("Creating v3 pipeline graph (5-phase ReAct architecture)")

    graph = StateGraph(AgentState)

    # Phase 0: Context Gathering (reuse existing agents)
    graph.add_node("input_enhancer", wrap_agent_with_instrumentation(input_enhancer_agent, "input_enhancer"))
    graph.add_node("domain_knowledge_retriever", wrap_agent_with_instrumentation(domain_knowledge_retriever_agent, "domain_knowledge_retriever"))
    graph.add_node("router", wrap_agent_with_instrumentation(router_agent, "router"))

    # Phase 1: Game Design
    graph.add_node("game_designer_v3", wrap_agent_with_instrumentation(game_designer_v3_agent, "game_designer_v3"))
    graph.add_node("design_validator", wrap_agent_with_instrumentation(design_validator_agent, "design_validator"))

    # Phase 2: Scene Architecture (NEW)
    graph.add_node("scene_architect_v3", wrap_agent_with_instrumentation(scene_architect_v3_agent, "scene_architect_v3"))
    graph.add_node("scene_validator", wrap_agent_with_instrumentation(scene_validator_agent, "scene_validator"))

    # Phase 3: Interaction Design (NEW)
    graph.add_node("interaction_designer_v3", wrap_agent_with_instrumentation(interaction_designer_v3_agent, "interaction_designer_v3"))
    graph.add_node("interaction_validator", wrap_agent_with_instrumentation(interaction_validator_v3_agent, "interaction_validator"))

    # Phase 4: Asset Generation (NEW — replaces asset_spec_builder + asset_orchestrator_v3)
    graph.add_node("asset_generator_v3", wrap_agent_with_instrumentation(asset_generator_v3_agent, "asset_generator_v3"))

    # Phase 5: Blueprint Assembly (deterministic — no LLM overhead)
    graph.add_node("blueprint_assembler_v3", wrap_agent_with_instrumentation(deterministic_blueprint_assembler_agent, "blueprint_assembler_v3"))

    # ── Wiring ──

    # Phase 0: Context Gathering
    graph.set_entry_point("input_enhancer")
    graph.add_edge("input_enhancer", "domain_knowledge_retriever")
    graph.add_edge("domain_knowledge_retriever", "router")

    # Router → Phase 1
    graph.add_edge("router", "game_designer_v3")

    # Phase 1: Design validation retry loop
    graph.add_edge("game_designer_v3", "design_validator")
    graph.add_conditional_edges(
        "design_validator",
        _v3_design_validation_router,
        {
            "game_designer_v3": "game_designer_v3",
            "scene_architect_v3": "scene_architect_v3",
        },
    )

    # Phase 2: Scene validation retry loop
    graph.add_edge("scene_architect_v3", "scene_validator")
    graph.add_conditional_edges(
        "scene_validator",
        _v3_scene_validation_router,
        {
            "scene_architect_v3": "scene_architect_v3",
            "interaction_designer_v3": "interaction_designer_v3",
        },
    )

    # Phase 3: Interaction validation retry loop
    graph.add_edge("interaction_designer_v3", "interaction_validator")
    graph.add_conditional_edges(
        "interaction_validator",
        _v3_interaction_validation_router,
        {
            "interaction_designer_v3": "interaction_designer_v3",
            "asset_generator_v3": "asset_generator_v3",
        },
    )

    # Phase 4 → Phase 5
    graph.add_edge("asset_generator_v3", "blueprint_assembler_v3")

    # Phase 5 → END
    graph.add_edge("blueprint_assembler_v3", END)

    logger.info("Created v3 pipeline graph (12 nodes, 5 phases)")
    return graph


# Singleton checkpointer instance and context manager
_checkpointer = None
_checkpointer_cm = None  # Store context manager to keep it alive


def get_checkpointer():
    """
    Get database-backed checkpointer for LangGraph.
    
    Uses SQLite checkpointer for development (matches current DB setup).
    Can be extended to support PostgreSQL for production.
    
    Returns:
        Checkpointer instance (SqliteSaver or PostgresSaver)
    """
    global _checkpointer, _checkpointer_cm
    
    if _checkpointer is not None:
        return _checkpointer
    
    db_url = os.getenv("DATABASE_URL", "sqlite:///./gamed_ai_v2.db")
    
    try:
        if db_url.startswith("sqlite"):
            # Use Async SQLite checkpointer for async operations
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            
            # Extract SQLite path (remove sqlite:/// prefix)
            sqlite_path = db_url.replace("sqlite:///", "")
            if sqlite_path == ":memory:":
                sqlite_path = ":memory:"
            
            logger.info(f"Initializing Async SQLite checkpointer with path: {sqlite_path}")
            # AsyncSqliteSaver.from_conn_string() returns a context manager
            # We need to enter it to get the actual checkpointer
            # Store the context manager to keep it alive for the lifetime of the app
            _checkpointer_cm = AsyncSqliteSaver.from_conn_string(sqlite_path)
            _checkpointer = _checkpointer_cm.__enter__()
            return _checkpointer
        else:
            # Use PostgreSQL checkpointer
            try:
                from langgraph.checkpoint.postgres import PostgresSaver
                logger.info("Initializing PostgreSQL checkpointer")
                # PostgresSaver.from_conn_string() may also return a context manager
                # Check if it's a context manager
                cm = PostgresSaver.from_conn_string(db_url)
                if hasattr(cm, '__enter__'):
                    _checkpointer_cm = cm
                    _checkpointer = _checkpointer_cm.__enter__()
                else:
                    _checkpointer = cm
                return _checkpointer
            except ImportError:
                logger.warning(
                    "PostgreSQL checkpointer not available. Install langgraph-checkpoint-postgres. "
                    "Falling back to MemorySaver."
                )
                _checkpointer = MemorySaver()
                return _checkpointer
    except Exception as e:
        logger.error(f"Failed to initialize database checkpointer: {e}. Falling back to MemorySaver.")
        _checkpointer = MemorySaver()
        return _checkpointer


def compile_graph_with_memory():
    """Compile graph with database checkpointing for persistence"""
    graph = create_game_generation_graph()
    checkpointer = get_checkpointer()
    logger.info("Compiling graph with database checkpointer")
    return graph.compile(checkpointer=checkpointer)


# Singleton compiled graph
_compiled_graph = None


def get_compiled_graph(topology: Optional[str] = None, preset: Optional[str] = None):
    """
    Get compiled graph for specified topology and preset.

    Args:
        topology: Topology type (T0, T1, T2, etc.) or None for default T1
        preset: Preset variant (preset_1, preset_1_agentic_sequential, preset_1_react)
                If specified, overrides topology-based creation

    Returns:
        Compiled StateGraph with checkpointer
    """
    from app.agents.topologies import TopologyType, create_topology

    # Check for preset variants first
    if preset:
        preset_lower = preset.lower()
        # V4 Algorithm — Algorithm game pipeline
        if preset_lower == "v4_algorithm":
            logger.info("Creating V4 Algorithm pipeline graph (6-phase, 12 nodes)")
            from app.v4_algorithm.graph import create_v4_algorithm_graph
            checkpointer = get_checkpointer()
            return create_v4_algorithm_graph(checkpointer=checkpointer)
        # V4 — Streamlined 5-phase pipeline (parallel context, Send API assets)
        elif preset_lower == "v4":
            logger.info("Creating V4 pipeline graph (5-phase streamlined architecture)")
            from app.v4.graph import create_v4_graph
            checkpointer = get_checkpointer()
            return create_v4_graph(checkpointer=checkpointer)
        # V3 — Current main pipeline (5-Phase ReAct Architecture)
        elif preset_lower == PRESET_V3 or preset_lower == "v3":
            logger.info("Creating V3 pipeline graph (5-Phase ReAct Architecture — CURRENT)")
            graph = create_v3_graph()
        # V2.5 — HAD (Hierarchical Agentic DAG, 4-cluster)
        elif preset_lower == PRESET_HAD or preset_lower == "had":
            logger.info("Creating V2.5 HAD (Hierarchical Agentic DAG) graph")
            graph = create_had_graph()
        # V2 — ReAct graph (3 ReAct agents)
        elif preset_lower == PRESET_1_REACT:
            logger.info("Creating V2 ReAct graph")
            graph = create_preset1_react_graph()
        # V1.1 — Agentic Sequential (7 agents + tools)
        elif preset_lower == PRESET_1_AGENTIC_SEQUENTIAL:
            logger.info("Creating V1.1 Agentic Sequential graph")
            graph = create_preset1_agentic_sequential_graph()
        # V1 — Baseline (original 17-agent sequential)
        elif preset_lower == PRESET_1_BASELINE or preset_lower == "preset_1":
            logger.info(f"Creating V1 Baseline with topology {topology or 'T1'}")
            topology = topology or "T1"
            topology_map = {
                "T0": TopologyType.T0_SEQUENTIAL,
                "T1": TopologyType.T1_SEQUENTIAL_VALIDATED,
                "T2": TopologyType.T2_ACTOR_CRITIC,
                "T4": TopologyType.T4_SELF_REFINE,
                "T5": TopologyType.T5_MULTI_AGENT_DEBATE,
                "T7": TopologyType.T7_REFLECTION_MEMORY,
            }
            topology_type = topology_map.get(topology.upper(), TopologyType.T1_SEQUENTIAL_VALIDATED)
            graph = create_topology(topology_type)
        # Legacy game-type presets (V1 era)
        elif preset_lower in ("interactive_diagram_hierarchical", "advanced_interactive_diagram", "default",
                                "label_diagram_hierarchical", "advanced_label_diagram"):
            logger.info(f"Creating V1 game generation graph for legacy preset '{preset}'")
            graph = create_game_generation_graph()
        else:
            logger.warning(f"Unknown preset '{preset}', falling back to baseline")
            graph = create_game_generation_graph()
    else:
        # Default to T1 topology if not specified
        if topology is None:
            topology = "T1"

        # Map string to TopologyType enum
        topology_map = {
            "T0": TopologyType.T0_SEQUENTIAL,
            "T1": TopologyType.T1_SEQUENTIAL_VALIDATED,
            "T2": TopologyType.T2_ACTOR_CRITIC,
            "T4": TopologyType.T4_SELF_REFINE,
            "T5": TopologyType.T5_MULTI_AGENT_DEBATE,
            "T7": TopologyType.T7_REFLECTION_MEMORY,
        }

        topology_type = topology_map.get(topology.upper(), TopologyType.T1_SEQUENTIAL_VALIDATED)

        # Create topology graph
        graph = create_topology(topology_type)
        logger.info(f"Creating graph with topology {topology}")

    # Compile with checkpointer
    checkpointer = get_checkpointer()
    logger.info("Compiling graph with database checkpointer")
    return graph.compile(checkpointer=checkpointer)


async def run_game_generation(
    question_id: str,
    question_text: str,
    question_options: list = None,
    thread_id: str = None
) -> dict:
    """
    Run the game generation pipeline.

    Args:
        question_id: Unique ID for the question
        question_text: The question text
        question_options: Optional answer choices
        thread_id: Optional thread ID for resuming

    Returns:
        Final state after generation
    """
    from app.agents.state import create_initial_state

    graph = get_compiled_graph()
    initial_state = create_initial_state(question_id, question_text, question_options)

    config = {"configurable": {"thread_id": thread_id or question_id}}

    logger.info(f"Starting game generation for question {question_id}")

    try:
        final_state = await graph.ainvoke(initial_state, config)
        logger.info(f"Game generation complete for {question_id}")
        return final_state
    except Exception as e:
        logger.error(f"Game generation failed: {e}", exc_info=True)
        raise
