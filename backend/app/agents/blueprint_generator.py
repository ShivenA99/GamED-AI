"""
Blueprint Generator Agent

Generates template-specific JSON blueprints that match TypeScript interfaces.
Each blueprint is structured for direct rendering by frontend components.

Key Features:
- Template-specific schema generation with detailed prompts
- Validation feedback incorporation
- Animation cue generation
- Task and scoring integration
- Plug-and-play model configuration via generate_for_agent()
"""

import json
import math
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from functools import lru_cache

from app.agents.state import AgentState
from app.services.llm_service import get_llm_service
from app.agents.schemas.interactive_diagram import (
    get_interactive_diagram_blueprint_schema,
    normalize_labels,
    normalize_zones,
    create_labels_from_zones,
)
from app.utils.logging_config import get_logger
from app.agents.instrumentation import InstrumentedAgentContext
from app.config.pedagogical_constants import DIFFICULTY_LEVEL, DEFAULT_SCORING, DEFAULT_FEEDBACK, DEFAULT_THRESHOLDS

logger = get_logger("gamed_ai.agents.blueprint_generator")

# Path to prompt templates
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# Template type to prompt file mapping
TEMPLATE_PROMPT_FILES = {
    "PARAMETER_PLAYGROUND": "blueprint_parameter_playground.txt",
    "SEQUENCE_BUILDER": "blueprint_sequence_builder.txt",
    "BUCKET_SORT": "blueprint_bucket_sort.txt",
    "INTERACTIVE_DIAGRAM": "blueprint_interactive_diagram.txt",
    "TIMELINE_ORDER": "blueprint_timeline_order.txt",
    "MATCH_PAIRS": "blueprint_match_pairs.txt",
    "STATE_TRACER_CODE": "blueprint_state_tracer_code.txt",
}


@lru_cache(maxsize=20)
def load_template_prompt(template_type: str) -> Optional[str]:
    """
    Load template-specific prompt from file.

    Uses caching to avoid repeated file reads.

    Args:
        template_type: The template type (e.g., "SEQUENCE_BUILDER")

    Returns:
        Prompt content or None if not found
    """
    filename = TEMPLATE_PROMPT_FILES.get(template_type)
    if not filename:
        logger.debug(f"No prompt file mapping for template: {template_type}")
        return None

    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        logger.warning(f"Prompt file not found: {prompt_path}")
        return None

    try:
        with open(prompt_path, "r") as f:
            content = f.read()
            logger.debug(f"Loaded prompt for {template_type} ({len(content)} chars)")
            return content
    except Exception as e:
        logger.error(f"Failed to load prompt file {prompt_path}: {e}")
        return None


# Template-specific TypeScript interfaces (simplified)
TEMPLATE_SCHEMAS = {
    "PARAMETER_PLAYGROUND": {
        "required": ["templateType", "title", "narrativeIntro", "parameters", "visualization", "tasks", "animationCues"],
        "schema": """
{
    "templateType": "PARAMETER_PLAYGROUND",
    "title": string,
    "narrativeIntro": string,
    "parameters": Array<{
        id: string,
        label: string,
        type: "slider" | "input" | "dropdown",
        min?: number,
        max?: number,
        step?: number,
        defaultValue: number | string,
        unit?: string
    }>,
    "visualization": {
        type: "chart" | "graph" | "diagram" | "simulation",
        algorithmType?: string,
        array?: number[],
        target?: number,
        steps?: Array<{stepNumber, variables, explanation}>,
        code?: string
    },
    "tasks": Array<{
        id: string,
        type: "parameter_adjustment" | "prediction",
        questionText: string,
        targetValues?: Record<string, number | string>,
        requiredToProceed: boolean
    }>,
    "animationCues": {
        parameterChange: string,
        visualizationUpdate: string,
        targetReached?: string
    }
}"""
    },
    "SEQUENCE_BUILDER": {
        "required": ["templateType", "title", "narrativeIntro", "steps", "tasks", "animationCues"],
        "schema": """
{
    "templateType": "SEQUENCE_BUILDER",
    "title": string,
    "narrativeIntro": string,
    "steps": Array<{
        id: string,
        text: string,
        orderIndex: number,
        description?: string
    }>,
    "distractors"?: Array<{
        id: string,
        text: string,
        description?: string
    }>,
    "tasks": Array<{
        id: string,
        type: "sequence_order",
        questionText: string,
        requiredToProceed: boolean
    }>,
    "animationCues": {
        stepDrag: string,
        correctPlacement: string,
        incorrectPlacement: string,
        sequenceComplete?: string
    }
}"""
    },
    "BUCKET_SORT": {
        "required": ["templateType", "title", "narrativeIntro", "buckets", "items", "tasks", "animationCues"],
        "schema": """
{
    "templateType": "BUCKET_SORT",
    "title": string,
    "narrativeIntro": string,
    "buckets": Array<{
        id: string,
        label: string,
        description?: string
    }>,
    "items": Array<{
        id: string,
        text: string,
        correctBucketId: string,
        description?: string
    }>,
    "tasks": Array<{
        id: string,
        type: "bucket_sort",
        questionText: string,
        requiredToProceed: boolean
    }>,
    "animationCues": {
        itemDrag: string,
        correctDrop: string,
        incorrectDrop: string,
        bucketFull?: string
    }
}"""
    },
    "INTERACTIVE_DIAGRAM": {
        "required": ["templateType", "title", "narrativeIntro", "diagram", "labels", "tasks", "animationCues"],
        "schema": """
{
    "templateType": "INTERACTIVE_DIAGRAM",
    "title": string,
    "narrativeIntro": string,
    "diagram": {
        assetPrompt: string,
        assetUrl?: string,
        zones: Array<{
            id: string,
            label: string,
            x: number (0-100),
            y: number (0-100),
            radius: number
        }>
    },
    "labels": Array<{
        id: string,
        text: string,
        correctZoneId: string
    }>,
    "tasks": Array<{
        id: string,
        type: "interactive_diagram",
        questionText: string,
        requiredToProceed: boolean
    }>,
    "animationCues": {
        correctPlacement: string,
        incorrectPlacement: string
    }
}"""
    },
    "TIMELINE_ORDER": {
        "required": ["templateType", "title", "narrativeIntro", "events", "timeline", "tasks", "animationCues"],
        "schema": """
{
    "templateType": "TIMELINE_ORDER",
    "title": string,
    "narrativeIntro": string,
    "events": Array<{
        id: string,
        text: string,
        timestamp: number,
        description?: string
    }>,
    "timeline": {
        startTime: number,
        endTime: number,
        unit?: string
    },
    "tasks": Array<{
        id: string,
        type: "timeline_order",
        questionText: string,
        requiredToProceed: boolean
    }>,
    "animationCues": {
        eventPlacement: string,
        correctOrder: string,
        incorrectOrder: string
    }
}"""
    },
    "MATCH_PAIRS": {
        "required": ["templateType", "title", "narrativeIntro", "pairs", "tasks", "animationCues"],
        "schema": """
{
    "templateType": "MATCH_PAIRS",
    "title": string,
    "narrativeIntro": string,
    "pairs": Array<{
        id: string,
        leftItem: { id: string, text: string },
        rightItem: { id: string, text: string }
    }>,
    "tasks": Array<{
        id: string,
        type: "match_pairs",
        questionText: string,
        requiredToProceed: boolean
    }>,
    "animationCues": {
        cardFlip: string,
        cardMatch: string,
        cardMismatch: string,
        allMatched?: string
    }
}"""
    },
    "STATE_TRACER_CODE": {
        "required": ["templateType", "title", "narrativeIntro", "code", "steps", "tasks", "animationCues"],
        "schema": """
{
    "templateType": "STATE_TRACER_CODE",
    "title": string,
    "narrativeIntro": string,
    "code": string,
    "initialInput"?: any,
    "steps": Array<{
        index: number,
        description: string,
        expectedVariables: Record<string, any>,
        highlightLine?: number
    }>,
    "tasks": Array<{
        id: string,
        type: "variable_value" | "step_analysis",
        questionText: string,
        stepIndex?: number,
        variableName?: string,
        correctAnswer: string,
        requiredToProceed: boolean
    }>,
    "animationCues": {
        lineHighlight: string,
        variableUpdate: string,
        stepComplete: string
    }
}"""
    }
}


BLUEPRINT_GENERATOR_PROMPT = """You are an expert educational game blueprint designer. Generate a complete, valid blueprint for the specified template.

## Question:
{question_text}

## Answer Options:
{question_options}

## Template Type: {template_type}

## Template Schema:
{template_schema}

## Story Context:
{story_context}

## Game Mechanics:
{game_mechanics}

## Pedagogical Context:
- Subject: {subject}
- Difficulty: {difficulty}
- Key Concepts: {key_concepts}

## Previous Validation Errors (if any):
{validation_errors}

## Blueprint Requirements:
1. Follow the EXACT schema structure shown above
2. All required fields MUST be present
3. IDs must be unique strings (use descriptive names like "step_1", "bucket_metals")
4. Ensure correctAnswer values match option values exactly
5. Include meaningful animation cues for feedback
6. Tasks should align with learning objectives

## Generate the blueprint:
Create a complete, valid JSON blueprint that:
- Teaches the concept through interactive gameplay
- Includes all required fields for the template
- Has appropriate difficulty and engagement
- Provides clear feedback through animation cues

Respond with ONLY the valid JSON blueprint, no explanation."""


def _build_enhanced_prompt(
    template_type: str,
    question_text: str,
    question_options: List[str],
    ped_context: Dict[str, Any],
    game_plan: Dict[str, Any],
    scene_data: Dict[str, Any] = None,
    story_data: Dict[str, Any] = None,  # Legacy support
    prev_errors: List[str] = None,
    domain_knowledge: Dict[str, Any] = None,
    generated_assets: List[Dict[str, Any]] = None  # NEW: Assets from asset pipeline
) -> str:
    """
    Build the prompt using template-specific file if available,
    otherwise fall back to the generic prompt.
    """
    # Try to load template-specific prompt
    template_prompt = load_template_prompt(template_type)

    # Format options
    options_str = "\n".join(f"- {opt}" for opt in question_options) if question_options else "None"

    # Initialize scene_summary for later use
    scene_summary = ""

    # Scene context (prefer scene_data, fallback to story_data for legacy)
    # Build detailed scene summary for better blueprint alignment
    if scene_data:
        # Extract summary stats for prompt
        visual_theme = scene_data.get("visual_theme", "educational")
        scene_title = scene_data.get("scene_title", "")
        layout_type = scene_data.get("layout_type", "center_focus")
        required_assets = scene_data.get("required_assets", [])
        animation_sequences = scene_data.get("animation_sequences", [])

        scene_context = json.dumps({
            "visual_theme": visual_theme,
            "scene_title": scene_title,
            "minimal_context": scene_data.get("minimal_context", ""),
            "layout_type": layout_type,
            "required_assets_count": len(required_assets),
            "asset_ids": [a.get("id") for a in required_assets[:10] if isinstance(a, dict)],
            "asset_interactions": scene_data.get("asset_interactions", [])[:5],  # Limit for prompt size
            "layout_specification": scene_data.get("layout_specification", {}),
            "animation_sequences": animation_sequences[:3],  # Limit for prompt size
        }, indent=2)

        # Build scene summary for more explicit guidance
        scene_summary = f"""
### Scene Design Summary (from hierarchical generation):
- Visual Theme: {visual_theme}
- Scene Title: {scene_title}
- Layout Type: {layout_type}
- Required Assets: {len(required_assets)} components defined
- Defined Interactions: {len(scene_data.get('asset_interactions', []))} interactions
- Animation Sequences: {len(animation_sequences)} animations
"""
        context_label = "Scene Context"
    elif story_data:
        scene_context = json.dumps({
            "title": story_data.get("story_title", ""),
            "context": story_data.get("story_context", ""),
            "narrative_hook": story_data.get("narrative_hook", ""),
            "characters": story_data.get("characters", []),
            "visual_metaphor": story_data.get("visual_metaphor", "")
        }, indent=2)
        context_label = "Story Context (Legacy)"
    else:
        scene_context = "{}"
        context_label = "Scene Context"

    # Game mechanics
    mechanics_str = json.dumps(game_plan.get("game_mechanics", []), indent=2)

    # Validation errors
    errors_str = json.dumps(prev_errors, indent=2) if prev_errors else "None"
    knowledge_str = json.dumps(domain_knowledge or {}, indent=2)

    # Generated assets summary (from asset pipeline that runs before blueprint)
    assets_summary = ""
    if generated_assets:
        # Normalize to list of dicts — workflow mode produces Dict[str, WorkflowResult], legacy produces List
        if isinstance(generated_assets, dict):
            asset_list = []
            for aid, aval in generated_assets.items():
                if isinstance(aval, dict):
                    aval.setdefault("id", aid)
                    asset_list.append(aval)
                else:
                    asset_list.append({"id": aid, "value": str(aval)})
        else:
            asset_list = [a for a in generated_assets if isinstance(a, dict)]

        successful_assets = [a for a in asset_list if a.get("success", False)]
        assets_summary = f"""
### Generated Assets (use these URLs/paths in your blueprint):
{json.dumps([{
    "id": a.get("id"),
    "type": a.get("type"),
    "url": a.get("url"),
    "local_path": a.get("local_path"),
    "placement": a.get("metadata", {}).get("placement", "overlay") if isinstance(a.get("metadata"), dict) else "overlay"
} for a in successful_assets], indent=2)}

IMPORTANT: Reference these generated asset URLs in your blueprint's mediaAssets or diagram.assetUrl fields.
"""

    if template_prompt:
        # Use template-specific prompt with context appended
        # Build validation error guidance if there are errors
        error_guidance = ""
        if prev_errors:
            error_guidance = f"""
### CRITICAL: Previous Validation Errors (FIX THESE FIRST):
The previous blueprint had these errors that MUST be fixed:
{json.dumps(prev_errors, indent=2)}

Address ALL the above errors in your output. Do not repeat these mistakes.
"""

        # Use scene_summary if available (defined in scene_data block above)
        scene_summary_str = scene_summary if scene_data else ""

        context_section = f"""
## GENERATION CONTEXT
{error_guidance}
### Question to Transform:
{question_text}

### Answer Options:
{options_str}

### Pedagogical Context:
- Subject: {ped_context.get("subject", "General")}
- Bloom's Level: {ped_context.get("blooms_level", "understand")}
- Difficulty: {ped_context.get("difficulty", "intermediate")}
- Key Concepts: {json.dumps(ped_context.get("key_concepts", []))}
- Learning Objectives: {json.dumps(ped_context.get("learning_objectives", []))}
{scene_summary_str}
### {context_label}:
{scene_context}

### Game Mechanics:
{mechanics_str}

### Domain Knowledge (use canonical labels and variants):
{knowledge_str}
{assets_summary}
Now generate a complete, valid JSON blueprint following the schema and examples above.
Use the visual theme "{scene_data.get('visual_theme', 'educational') if scene_data else 'educational'}" and scene title "{scene_data.get('scene_title', '') if scene_data else ''}" from the scene context.
"""
        return template_prompt + context_section

    else:
        # Fall back to generic prompt
        template_info = TEMPLATE_SCHEMAS.get(template_type, TEMPLATE_SCHEMAS["PARAMETER_PLAYGROUND"])
        return BLUEPRINT_GENERATOR_PROMPT.format(
            question_text=question_text,
            question_options=options_str,
            template_type=template_type,
            template_schema=template_info["schema"],
            story_context=scene_context,
            game_mechanics=mechanics_str,
            subject=ped_context.get("subject", "General"),
            difficulty=ped_context.get("difficulty", "intermediate"),
            key_concepts=json.dumps(ped_context.get("key_concepts", [])),
            validation_errors=errors_str
        )


async def blueprint_generator_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    """
    Blueprint Generator Agent

    Generates a template-specific JSON blueprint based on all previous
    agent outputs (pedagogical context, template selection, game plan, story).

    Uses template-specific prompts from files when available, with
    plug-and-play model configuration via generate_for_agent().

    For multi-scene games (Preset 2), generates a GameSequence blueprint
    with per-scene diagrams, zones, and interactions.

    Args:
        state: Current agent state with all upstream data

    Returns:
        Updated state with blueprint populated
    """
    logger.info(f"BlueprintGenerator: Creating blueprint for question {state.get('question_id', 'unknown')}")

    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])
    ped_context = state.get("pedagogical_context", {})
    template_selection = state.get("template_selection", {})
    game_plan = state.get("game_plan", {})
    scene_data = state.get("scene_data", {})
    # Legacy support
    story_data = state.get("story_data", {})
    domain_knowledge = state.get("domain_knowledge", {})

    # Get generated assets from the asset pipeline (runs BEFORE blueprint)
    # These contain actual URLs/paths that should be referenced in the blueprint
    generated_assets = state.get("generated_assets", [])
    if generated_assets:
        logger.info(f"BlueprintGenerator: Received {len(generated_assets)} generated assets from asset pipeline")

    # Check for multi-scene data (from multi_scene_orchestrator or entity_registry)
    needs_multi_scene = state.get("needs_multi_scene", False)
    all_scene_data = state.get("all_scene_data") or {}  # From multi_scene_orchestrator
    scene_diagrams = state.get("scene_diagrams") or {}
    scene_zones = state.get("scene_zones") or {}
    scene_labels = state.get("scene_labels") or {}

    # scene_breakdown can come from game_plan or state directly
    scene_breakdown = state.get("scene_breakdown", [])
    if not scene_breakdown and game_plan:
        scene_breakdown = game_plan.get("scene_breakdown", [])

    # Get entity_registry for multi-scene tracking
    entity_registry = state.get("entity_registry") or {}
    registry_scene_zones = entity_registry.get("scene_zones", {}) if entity_registry else {}

    # Determine if multi-scene blueprint is needed
    # Triggers: needs_multi_scene flag OR multiple scenes in breakdown OR multiple scenes in registry
    has_multiple_scenes = (
        (all_scene_data and len(all_scene_data) > 1) or
        (scene_diagrams and len(scene_diagrams) > 1) or
        (scene_breakdown and len(scene_breakdown) > 1) or
        (registry_scene_zones and len(registry_scene_zones) > 1)
    )

    if needs_multi_scene and has_multiple_scenes:
        scene_count = max(
            len(all_scene_data) if all_scene_data else 0,
            len(scene_diagrams) if scene_diagrams else 0,
            len(scene_breakdown) if scene_breakdown else 0,
            len(registry_scene_zones) if registry_scene_zones else 0
        )
        logger.info(f"BlueprintGenerator: Creating multi-scene blueprint with {scene_count} scenes")
        return await _generate_multi_scene_blueprint(
            state=state,
            question_text=question_text,
            question_options=question_options,
            ped_context=ped_context,
            template_selection=template_selection,
            game_plan=game_plan,
            scene_breakdown=scene_breakdown,
            scene_diagrams=scene_diagrams,
            scene_zones=scene_zones,
            scene_labels=scene_labels,
            domain_knowledge=domain_knowledge,
            all_scene_data=all_scene_data,
            ctx=ctx
        )

    template_type = template_selection.get("template_type", "PARAMETER_PLAYGROUND")

    # Get previous validation errors for feedback
    prev_errors = state.get("current_validation_errors", [])

    # Build enhanced prompt (uses template-specific file if available)
    prompt = _build_enhanced_prompt(
        template_type=template_type,
        question_text=question_text,
        question_options=question_options,
        ped_context=ped_context,
        game_plan=game_plan,
        scene_data=scene_data,
        story_data=story_data,  # Legacy support
        prev_errors=prev_errors,
        domain_knowledge=domain_knowledge,
        generated_assets=generated_assets  # NEW: Pass generated assets from asset pipeline
    )

    try:
        llm = get_llm_service()

        # Use agent-specific model configuration (plug-and-play)
        json_schema = None
        if template_type == "INTERACTIVE_DIAGRAM":
            json_schema = get_interactive_diagram_blueprint_schema()

        blueprint = await llm.generate_json_for_agent(
            agent_name="blueprint_generator",
            prompt=prompt,
            schema_hint=f"Valid {template_type} blueprint JSON matching the schema",
            json_schema=json_schema
        )

        # Extract LLM metrics from the result for instrumentation
        llm_metrics = blueprint.pop("_llm_metrics", None) if isinstance(blueprint, dict) else None
        if llm_metrics and ctx:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms")
            )

        # Ensure template type is set correctly
        blueprint["templateType"] = template_type

        # Merge scene data into blueprint (prefer scene_data, fallback to story_data for legacy)
        if scene_data:
            blueprint = _merge_scene_into_blueprint(blueprint, scene_data)
        elif story_data:
            blueprint = _merge_story_into_blueprint(blueprint, story_data)

        # Merge generated assets into blueprint (from asset pipeline that runs BEFORE blueprint)
        if generated_assets:
            blueprint = _merge_generated_assets_into_blueprint(blueprint, generated_assets)

        # Enforce INTERACTIVE_DIAGRAM schema correctness (T0 guard)
        if template_type == "INTERACTIVE_DIAGRAM":
            fallback = _create_fallback_blueprint(
                template_type, question_text, question_options, scene_data, story_data
            )
            # Extract hierarchy_info from game_plan for hierarchical mode
            hierarchy_info = game_plan.get("hierarchy_info") if game_plan else None
            # Extract interaction_design from state (from interaction_designer agent)
            # Use 'or {}' pattern because state.get returns None if key exists with None value
            interaction_design = state.get("interaction_design") or {}
            blueprint = _sanitize_interactive_diagram_blueprint(
                blueprint,
                fallback,
                question_text,
                domain_knowledge=domain_knowledge,
                diagram_zones=state.get("diagram_zones"),
                diagram_labels=state.get("diagram_labels"),
                scene_data=scene_data,
                hierarchy_info=hierarchy_info,
                zone_groups=state.get("zone_groups"),
                temporal_constraints=state.get("temporal_constraints"),
                game_plan=game_plan,  # For scoring_rubric
                ped_context=ped_context,  # For common_misconceptions
                interaction_design=interaction_design,  # For agentic scoring strategy
            )
            # Use diagram image URL - priority order:
            # 1. generated_diagram_path or cleaned_image_path (local generated file)
            # 2. diagram_image.generated_path (if is_generated=True)
            # 3. original diagram_image URL (web image)
            generated_diagram_path = state.get("generated_diagram_path")
            cleaned_image_path = state.get("cleaned_image_path")
            diagram_image = state.get("diagram_image", {}) or {}
            question_id = state.get("question_id", "unknown")

            # Helper to check if a local path exists (handles relative paths)
            def local_path_exists(path: str) -> bool:
                if not path:
                    return False
                p = Path(path)
                if p.exists():
                    return True
                # Try relative to backend directory
                backend_path = Path(__file__).parent.parent.parent / path
                return backend_path.exists()

            # Get the best available local path
            local_diagram_path = (
                generated_diagram_path or
                cleaned_image_path or
                diagram_image.get("generated_path")
            )

            # Priority 1: Use local generated/cleaned diagram
            if local_diagram_path and local_path_exists(local_diagram_path):
                # Copy to expected serving location so /api/assets/{id}/generated/diagram.png works
                import shutil
                assets_dir = Path(__file__).parent.parent.parent / "pipeline_outputs" / "assets" / question_id / "generated"
                assets_dir.mkdir(parents=True, exist_ok=True)
                target_path = assets_dir / "diagram.png"
                try:
                    src = Path(local_diagram_path)
                    if not src.exists():
                        src = Path(__file__).parent.parent.parent / local_diagram_path
                    if src.exists() and not target_path.exists():
                        shutil.copy(str(src), str(target_path))
                        logger.info(f"Copied diagram to serving location: {target_path}")
                except Exception as copy_err:
                    logger.warning(f"Failed to copy diagram to assets dir: {copy_err}")

                # Serve through backend endpoint
                diagram_url = f"/api/assets/{question_id}/generated/diagram.png"
                blueprint.setdefault("diagram", {})["assetUrl"] = diagram_url
                logger.info(
                    "Using local diagram in blueprint",
                    local_path=local_diagram_path,
                    asset_url=diagram_url
                )
            # Priority 2: Check if diagram_image is generated and has a path
            elif diagram_image.get("is_generated") and diagram_image.get("generated_path"):
                generated_path = diagram_image["generated_path"]
                if local_path_exists(generated_path):
                    diagram_url = f"/api/assets/{question_id}/generated/diagram.png"
                    blueprint.setdefault("diagram", {})["assetUrl"] = diagram_url
                    logger.info(
                        "Using diagram_image.generated_path in blueprint",
                        generated_path=generated_path,
                        asset_url=diagram_url
                    )
            # Priority 3: Use original web image URL
            elif diagram_image.get("image_url"):
                blueprint.setdefault("diagram", {})["assetUrl"] = diagram_image["image_url"]
                logger.info("Using original image URL in blueprint",
                          metadata={"asset_url": diagram_image["image_url"][:80]})
            
            # Log zone information
            diagram_zones = state.get("diagram_zones", [])
            if diagram_zones:
                logger.info("Using SAM-generated zones in blueprint", 
                           metadata={
                               "zones_count": len(diagram_zones),
                               "zones": [z.get("id") for z in diagram_zones[:5]]
                           })
            else:
                logger.warning("No diagram zones available for blueprint")
            validation_result = await validate_blueprint(
                blueprint,
                template_type,
                context={
                    "question_text": question_text,
                    "pedagogical_context": ped_context,
                    "domain_knowledge": domain_knowledge,
                    "diagram_zones": state.get("diagram_zones"),
                    "diagram_image": state.get("diagram_image"),
                },
            )
            if not validation_result.get("valid", False):
                logger.warning(
                    "BlueprintGenerator: INTERACTIVE_DIAGRAM invalid after sanitize, using fallback. "
                    f"Errors: {validation_result.get('errors', [])}"
                )
                blueprint = fallback

        logger.info(
            f"BlueprintGenerator: Created {template_type} blueprint with "
            f"{len(blueprint.get('tasks', []))} tasks"
        )

        # Return only changed keys - DO NOT use **state as it overwrites retry_counts
        return {
            "blueprint": blueprint,
            "current_agent": "blueprint_generator",
            "current_validation_errors": []  # Clear previous errors
        }

    except Exception as e:
        logger.error(f"BlueprintGenerator: LLM call failed: {e}", exc_info=True)

        # Create fallback blueprint
        fallback = _create_fallback_blueprint(
            template_type, question_text, question_options, scene_data, story_data
        )
        
        # Even when using fallback, preserve SAM zones and labels if available
        diagram_zones = state.get("diagram_zones")
        diagram_labels = state.get("diagram_labels")
        if isinstance(diagram_zones, list) and diagram_zones:
            logger.info("Preserving SAM zones in fallback blueprint", zones_count=len(diagram_zones))
            fallback["diagram"]["zones"] = diagram_zones
        if isinstance(diagram_labels, list) and diagram_labels:
            logger.info("Preserving SAM labels in fallback blueprint", labels_count=len(diagram_labels))
            fallback["labels"] = diagram_labels

        # Return only changed keys - DO NOT use **state as it overwrites retry_counts
        return {
            "blueprint": fallback,
            "current_agent": "blueprint_generator",
            "error_message": f"BlueprintGenerator fallback: {str(e)}"
        }


def _merge_scene_into_blueprint(blueprint: Dict[str, Any], scene_data: Dict[str, Any]) -> Dict[str, Any]:
    """Merge scene data into the blueprint"""

    # Use scene title if blueprint title is missing
    if not blueprint.get("title") and scene_data.get("scene_title"):
        blueprint["title"] = scene_data["scene_title"]

    # Use minimal context for narrative intro (1-2 sentences from scene)
    if not blueprint.get("narrativeIntro") and scene_data.get("minimal_context"):
        blueprint["narrativeIntro"] = scene_data["minimal_context"]

    # Integrate animation sequences into animationCues
    if scene_data.get("animation_sequences") and not blueprint.get("animationCues"):
        animation_sequences = scene_data["animation_sequences"]
        blueprint["animationCues"] = {}
        for seq in animation_sequences:
            seq_id = seq.get("id", "")
            if seq_id == "step_execution":
                blueprint["animationCues"]["stepComplete"] = seq.get("description", "Step completed")
            elif seq_id == "variable_change":
                blueprint["animationCues"]["variableUpdate"] = seq.get("description", "Variable updated")
            elif seq_id == "search_complete":
                blueprint["animationCues"]["codeComplete"] = seq.get("description", "Code execution complete")

    return blueprint


def _merge_story_into_blueprint(blueprint: Dict[str, Any], story_data: Dict[str, Any]) -> Dict[str, Any]:
    """Merge story data into the blueprint (legacy support)"""

    # Use story title if blueprint title is missing
    if not blueprint.get("title") and story_data.get("story_title"):
        blueprint["title"] = story_data["story_title"]

    # Use story context for narrative intro
    if not blueprint.get("narrativeIntro") and story_data.get("story_context"):
        blueprint["narrativeIntro"] = story_data["story_context"]

    return blueprint


def _merge_generated_assets_into_blueprint(
    blueprint: Dict[str, Any],
    generated_assets
) -> Dict[str, Any]:
    """Merge generated assets into the blueprint.

    This function ensures the blueprint references actual generated asset URLs/paths
    from the asset pipeline that runs BEFORE blueprint generation.

    Args:
        blueprint: The generated blueprint
        generated_assets: Dict or List of generated assets from asset_generator_orchestrator

    Returns:
        Blueprint with generated asset references merged in
    """
    if not generated_assets:
        return blueprint

    # Normalize to list of dicts — workflow mode produces Dict[str, result], legacy produces List
    if isinstance(generated_assets, dict):
        asset_list = []
        for aid, aval in generated_assets.items():
            if isinstance(aval, dict):
                aval.setdefault("id", aid)
                asset_list.append(aval)
            else:
                asset_list.append({"id": aid, "value": str(aval)})
    else:
        asset_list = [a for a in generated_assets if isinstance(a, dict)]

    successful_assets = [a for a in asset_list if a.get("success", False)]

    if not successful_assets:
        logger.warning("No successful generated assets to merge into blueprint")
        return blueprint

    # Build a lookup by asset ID
    asset_lookup = {a.get("id"): a for a in successful_assets}

    # Merge into mediaAssets
    if not blueprint.get("mediaAssets"):
        blueprint["mediaAssets"] = []

    existing_ids = {a.get("id") for a in blueprint.get("mediaAssets", [])}

    for asset in successful_assets:
        asset_id = asset.get("id")
        if asset_id and asset_id not in existing_ids:
            media_asset = {
                "id": asset_id,
                "type": asset.get("type", "image"),
                "url": asset.get("url") or asset.get("local_path"),
            }
            # Add CSS content for animations
            if asset.get("css_content"):
                media_asset["cssContent"] = asset["css_content"]
            # Add metadata
            metadata = asset.get("metadata", {})
            if isinstance(metadata, dict):
                if metadata.get("placement"):
                    media_asset["placement"] = metadata["placement"]
                if metadata.get("zone_id"):
                    media_asset["zoneId"] = metadata["zone_id"]

            blueprint["mediaAssets"].append(media_asset)
            existing_ids.add(asset_id)

    # Update diagram.assetUrl if we have a main diagram asset
    if "main_diagram" in asset_lookup:
        diagram_asset = asset_lookup["main_diagram"]
        diagram_url = diagram_asset.get("url") or diagram_asset.get("local_path")
        if diagram_url:
            blueprint.setdefault("diagram", {})["assetUrl"] = diagram_url
            logger.info(f"Set diagram.assetUrl from generated asset: {diagram_url}")

    # Update background asset URL if available
    if "scene_background" in asset_lookup:
        bg_asset = asset_lookup["scene_background"]
        bg_url = bg_asset.get("url") or bg_asset.get("local_path")
        if bg_url:
            blueprint["backgroundUrl"] = bg_url
            logger.info(f"Set backgroundUrl from generated asset: {bg_url}")

    logger.info(f"Merged {len(successful_assets)} generated assets into blueprint")
    return blueprint


INTERACTIVE_DIAGRAM_ALLOWED_KEYS = {
    "templateType",
    "title",
    "narrativeIntro",
    "diagram",
    "labels",
    "distractorLabels",
    "tasks",
    "animationCues",
    # New fields for enhanced interactions
    "animations",           # Structured animation specs
    "interactionMode",      # drag_drop | click_to_identify | trace_path | hierarchical
    "zoneGroups",           # Hierarchical zone groups
    "identificationPrompts", # For click_to_identify mode
    "selectionMode",        # sequential | any_order
    "paths",                # For trace_path mode
    "mediaAssets",          # Media asset definitions
    # Phase 2/3 implementation - temporal intelligence
    "temporalConstraints",  # Petri Net-inspired zone visibility constraints
    "motionPaths",          # Keyframe-based motion animations
    # Scoring configuration from scoring_rubric
    "maxScore",             # Maximum possible score
    "partialCredit",        # Whether partial credit is allowed
    "timeBonus",            # Whether time bonus is enabled
    "hintPenalty",          # Penalty factor for using hints (0.0-1.0)
    # Existing optional fields
    "hints",
    "feedbackMessages",
    # Phase 0: Multi-mechanic support
    "sequenceConfig",       # For order/sequence mechanics (correctOrder, items, etc.)
}


def _generate_zone_groups_from_hierarchy(hierarchy_info: dict, zones: list) -> list:
    """
    Generate zoneGroups from hierarchy info and detected zones.

    Args:
        hierarchy_info: Dictionary with is_hierarchical, parent_children, reveal_trigger
        zones: List of zone dictionaries with id and label fields

    Returns:
        List of zone group dictionaries for hierarchical mode
    """
    if not hierarchy_info or not hierarchy_info.get("is_hierarchical"):
        return []

    parent_children = hierarchy_info.get("parent_children", {})
    reveal_trigger = hierarchy_info.get("reveal_trigger", "complete_parent")
    zone_groups = []

    # Build zone ID lookup by normalized label
    zone_by_label = {}
    for z in zones:
        if isinstance(z, dict):
            label = (z.get("label") or "").lower().strip()
            zone_id = z.get("id")
            if label and zone_id:
                zone_by_label[label] = zone_id

    for parent, children in parent_children.items():
        parent_normalized = parent.lower().strip()
        parent_zone_id = zone_by_label.get(parent_normalized)

        child_zone_ids = []
        for child in children:
            child_normalized = child.lower().strip()
            child_zone_id = zone_by_label.get(child_normalized)
            if child_zone_id:
                child_zone_ids.append(child_zone_id)

        if parent_zone_id and child_zone_ids:
            zone_groups.append({
                "id": f"group_{parent_normalized.replace(' ', '_')}",
                "parentZoneId": parent_zone_id,
                "childZoneIds": child_zone_ids,
                "revealTrigger": reveal_trigger,
                "label": f"{parent.title()} components"
            })
            logger.debug(
                f"Created zone group for {parent}",
                parent_zone_id=parent_zone_id,
                child_zone_ids=child_zone_ids
            )
        else:
            logger.warning(
                f"Could not create zone group for {parent}",
                parent_zone_id=parent_zone_id,
                children_found=len(child_zone_ids),
                children_expected=len(children)
            )

    return zone_groups


def _generate_default_zone_positions(count: int) -> List[tuple]:
    """Generate evenly spaced zone positions within a 0-100 grid."""
    if count <= 0:
        return []
    rows = math.ceil(math.sqrt(count))
    cols = math.ceil(count / rows)
    x_step = 100 / (cols + 1)
    y_step = 100 / (rows + 1)
    positions = []
    for idx in range(count):
        row = idx // cols
        col = idx % cols
        positions.append((round((col + 1) * x_step, 2), round((row + 1) * y_step, 2)))
    return positions


def _generate_structured_animations(animation_cues: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate structured animation specs from text-based animation cues.

    Maps common animation keywords to structured specs:
    - "pulse", "glow" -> pulse animation
    - "shake", "bounce" -> shake animation
    - "highlight", "snap" -> scale animation
    - "confetti", "celebration" -> confetti animation

    Args:
        animation_cues: Text-based animation cues dict

    Returns:
        Structured animations dict
    """
    def _parse_cue_to_spec(cue_text: str, default_type: str) -> Dict[str, Any]:
        """Parse a text cue into an animation spec."""
        text = (cue_text or "").lower()

        # Determine animation type from keywords
        if any(kw in text for kw in ["pulse", "glow", "highlight", "light"]):
            anim_type = "pulse"
        elif any(kw in text for kw in ["shake", "vibrate", "reject"]):
            anim_type = "shake"
        elif any(kw in text for kw in ["bounce", "spring", "jump"]):
            anim_type = "bounce"
        elif any(kw in text for kw in ["scale", "grow", "expand", "snap"]):
            anim_type = "scale"
        elif any(kw in text for kw in ["fade", "dissolve"]):
            anim_type = "fade"
        elif any(kw in text for kw in ["confetti", "celebration", "party"]):
            anim_type = "confetti"
        else:
            anim_type = default_type

        # Determine color from keywords
        if any(kw in text for kw in ["green", "correct", "success"]):
            color = "#22c55e"
        elif any(kw in text for kw in ["red", "wrong", "error", "incorrect"]):
            color = "#ef4444"
        elif any(kw in text for kw in ["blue", "primary"]):
            color = "#3b82f6"
        elif any(kw in text for kw in ["yellow", "warning"]):
            color = "#eab308"
        else:
            color = "#3b82f6"  # Default blue

        # Determine duration from keywords
        if any(kw in text for kw in ["quick", "fast", "snap"]):
            duration = 200
        elif any(kw in text for kw in ["slow", "long"]):
            duration = 600
        else:
            duration = 400

        return {
            "type": anim_type,
            "duration_ms": duration,
            "easing": "ease-out",
            "color": color,
            "intensity": 1.0
        }

    structured = {}

    # Map each cue
    if animation_cues.get("labelDrag"):
        structured["labelDrag"] = _parse_cue_to_spec(animation_cues["labelDrag"], "scale")

    if animation_cues.get("correctPlacement"):
        spec = _parse_cue_to_spec(animation_cues["correctPlacement"], "pulse")
        spec["color"] = "#22c55e"  # Always green for correct
        structured["correctPlacement"] = spec

    if animation_cues.get("incorrectPlacement"):
        spec = _parse_cue_to_spec(animation_cues["incorrectPlacement"], "shake")
        spec["color"] = "#ef4444"  # Always red for incorrect
        structured["incorrectPlacement"] = spec

    if animation_cues.get("allLabeled"):
        spec = _parse_cue_to_spec(animation_cues["allLabeled"], "confetti")
        spec["duration_ms"] = 2000  # Longer for completion
        spec["intensity"] = 1.5
        structured["completion"] = spec

    return structured


def _generate_paths_from_mechanics(
    game_plan: Optional[Dict[str, Any]],
    domain_knowledge: Optional[Dict[str, Any]],
    zones: List[Dict[str, Any]],
    interaction_mode: str,
) -> Optional[List[Dict[str, Any]]]:
    """
    Generate paths[] array for trace_path mode from sequence data.

    Bridges the gap between sequence_flow_data and PathDrawer's waypoint format.
    Uses zone centroids as waypoint positions.

    Args:
        game_plan: Game plan from game_planner agent
        domain_knowledge: Domain knowledge with sequence_flow_data
        zones: Detected zones with centroids
        interaction_mode: Current interaction mode

    Returns:
        List of path definitions or None if not trace_path mode
    """
    if interaction_mode != "trace_path":
        return None

    if not game_plan and not domain_knowledge:
        return None

    # Build zone lookup by label (case-insensitive)
    zone_by_label: Dict[str, Dict[str, Any]] = {}
    for zone in zones:
        if isinstance(zone, dict) and zone.get("label"):
            zone_by_label[zone["label"].lower()] = zone

    # Get sequence items from game_plan mechanics or domain_knowledge
    sequence_items = []
    path_description = "Trace the path"

    # First try game_plan mechanics
    game_mechanics = game_plan.get("game_mechanics", []) if game_plan else []
    for mechanic in game_mechanics:
        if not isinstance(mechanic, dict):
            continue
        mechanic_type = mechanic.get("type", "").lower()
        if mechanic_type in ("trace", "path", "flow", "trace_path"):
            sequence_items = mechanic.get("sequence_items", [])
            path_description = mechanic.get("description", path_description)
            break

    # Fallback to domain_knowledge.sequence_flow_data
    if not sequence_items and domain_knowledge:
        sequence_flow_data = domain_knowledge.get("sequence_flow_data")
        if sequence_flow_data:
            sequence_items = sequence_flow_data.get("sequence_items", [])
            path_description = sequence_flow_data.get("description", path_description)
            logger.info(
                "Using sequence_flow_data for trace_path waypoints",
                item_count=len(sequence_items)
            )

    if not sequence_items:
        logger.warning("No sequence items found for trace_path mode")
        return None

    # Generate waypoints from sequence items
    waypoints = []
    for item in sequence_items:
        if isinstance(item, dict):
            item_text = item.get("text") or item.get("label") or item.get("id", "")
            order_index = item.get("order_index", len(waypoints))
        elif isinstance(item, str):
            item_text = item
            order_index = len(waypoints)
        else:
            continue

        # Find matching zone
        item_lower = item_text.lower()
        zone = zone_by_label.get(item_lower)

        # Try partial match if exact match fails
        if not zone:
            for zone_label, z in zone_by_label.items():
                if item_lower in zone_label or zone_label in item_lower:
                    zone = z
                    break

        if zone:
            waypoints.append({
                "zoneId": zone.get("id"),
                "order": order_index + 1,  # 1-indexed for display
            })
            logger.debug(f"Mapped '{item_text}' to zone '{zone.get('id')}'")
        else:
            logger.warning(f"No zone found for sequence item '{item_text}'")

    if not waypoints:
        logger.warning("No waypoints generated for trace_path")
        return None

    # Sort waypoints by order
    waypoints.sort(key=lambda w: w.get("order", 0))

    # Return paths array with single path
    paths = [{
        "id": "path_main",
        "description": path_description,
        "requiresOrder": True,
        "waypoints": waypoints,
    }]

    logger.info(
        "Generated trace_path paths",
        waypoint_count=len(waypoints),
        description=path_description
    )

    return paths


def _generate_sequence_config_from_mechanics(
    game_plan: Optional[Dict[str, Any]],
    domain_knowledge: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Generate sequenceConfig from order/sequence mechanics in game_plan.

    Phase 0: Multi-mechanic support - enables games that combine labeling
    with sequencing (e.g., "Label heart parts AND show blood flow order").

    Args:
        game_plan: Game plan from game_planner agent
        domain_knowledge: Domain knowledge with potential sequence_flow_data

    Returns:
        SequenceConfig dict or None if no sequence mechanic exists
    """
    if not game_plan:
        return None

    game_mechanics = game_plan.get("game_mechanics", [])

    for mechanic in game_mechanics:
        if not isinstance(mechanic, dict):
            continue

        mechanic_type = mechanic.get("type", "").lower()

        if mechanic_type in ("order", "sequence", "ordering"):
            # Get sequence items from mechanic
            sequence_items = mechanic.get("sequence_items", [])
            correct_order = mechanic.get("correct_order", [])

            # Fallback to domain_knowledge if mechanic doesn't have items
            if not sequence_items and domain_knowledge:
                sequence_flow_data = domain_knowledge.get("sequence_flow_data")
                if sequence_flow_data:
                    sequence_items = sequence_flow_data.get("sequence_items", [])
                    logger.info(
                        "Using sequence_flow_data from domain_knowledge for sequenceConfig",
                        item_count=len(sequence_items)
                    )

            # Build correct_order from sequence_items if not provided
            if not correct_order and sequence_items:
                correct_order = [
                    item.get("id") for item in sorted(
                        sequence_items,
                        key=lambda x: x.get("order_index", 0)
                    )
                ]

            if not sequence_items:
                logger.warning(
                    "Order mechanic found but no sequence_items available",
                    mechanic_id=mechanic.get("id")
                )
                return None

            # Build sequenceConfig
            sequence_config = {
                "sequenceType": mechanic.get("sequence_type", "linear"),
                "items": [
                    {
                        "id": item.get("id", f"item_{idx}"),
                        "text": item.get("text", ""),
                        "description": item.get("description"),
                    }
                    for idx, item in enumerate(sequence_items)
                ],
                "correctOrder": correct_order,
                "allowPartialCredit": True,
                "instructionText": mechanic.get("description") or \
                    f"Arrange the items in the correct {mechanic.get('sequence_type', 'order')}"
            }

            logger.info(
                "Generated sequenceConfig from order mechanic",
                mechanic_id=mechanic.get("id"),
                item_count=len(sequence_config["items"]),
                sequence_type=sequence_config["sequenceType"]
            )

            return sequence_config

    return None


def _generate_hint_for_label(
    label: str,
    domain_knowledge: Dict[str, Any],
    hierarchy_info: Optional[Dict[str, Any]] = None
) -> str:
    """
    Auto-generate a contextual hint for a label using domain knowledge and hierarchy.

    Uses canonical_labels, acceptable_variants, and parent-child relationships
    to create meaningful hints that guide learners without giving away the answer.
    """
    if not domain_knowledge:
        return f"Think about where {label} would be located in the diagram."

    # Check hierarchical relationships for parent context
    hierarchical_rels = domain_knowledge.get("hierarchical_relationships", [])
    parent_label = None
    sibling_labels = []

    for rel in hierarchical_rels:
        if isinstance(rel, dict):
            children = rel.get("children", [])
            if label.lower() in [c.lower() for c in children]:
                parent_label = rel.get("parent")
                sibling_labels = [c for c in children if c.lower() != label.lower()]
                break

    # Check if this label is a parent
    child_labels = []
    for rel in hierarchical_rels:
        if isinstance(rel, dict) and rel.get("parent", "").lower() == label.lower():
            child_labels = rel.get("children", [])
            break

    # Check acceptable variants for alternative names
    variants = domain_knowledge.get("acceptable_variants", {})
    label_variants = variants.get(label, [])

    # Build hint based on available context
    if parent_label:
        if sibling_labels:
            return f"This structure is part of the {parent_label}, along with {', '.join(sibling_labels[:2])}."
        return f"This structure is part of the {parent_label}."

    if child_labels:
        return f"This structure contains {', '.join(child_labels[:3])}. Look for the larger region."

    if label_variants:
        return f"Also known as: {', '.join(label_variants[:2])}."

    # Fall back to generic hint with canonical context
    canonical = domain_knowledge.get("canonical_labels", [])
    if label in canonical:
        idx = canonical.index(label)
        if idx > 0:
            return f"This is related to {canonical[idx-1]} in the structure."

    return f"Identify the location of {label} in the diagram."


def _generate_feedback_for_distractor(
    distractor_text: str,
    label_text: str,
    common_misconceptions: List[Dict[str, str]],
    domain_knowledge: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate targeted feedback for a distractor label using common misconceptions.

    Matches misconceptions to distractors/labels and generates corrective feedback.
    """
    distractor_lower = distractor_text.lower()
    label_lower = label_text.lower() if label_text else ""

    # Check if any misconception relates to this distractor
    for misconception in common_misconceptions:
        if isinstance(misconception, dict):
            misconception_text = misconception.get("misconception", "").lower()
            correction = misconception.get("correction", "")

            # Check if distractor matches misconception pattern
            if distractor_lower in misconception_text or label_lower in misconception_text:
                if correction:
                    return f"Remember, {correction}"

            # Check for keyword overlap
            distractor_words = set(distractor_lower.split())
            misconception_words = set(misconception_text.split())
            if len(distractor_words & misconception_words) >= 2:
                if correction:
                    return f"Common mistake: {correction}"

    # Check domain knowledge for context
    if domain_knowledge:
        canonical = domain_knowledge.get("canonical_labels", [])
        canonical_lower = [c.lower() for c in canonical]

        # If distractor is similar to a canonical label
        for canonical_label in canonical:
            if distractor_lower in canonical_label.lower() or canonical_label.lower() in distractor_lower:
                return f"'{distractor_text}' is similar to but different from '{canonical_label}'. Check the exact terminology."

    # Generic fallback with more context
    return (
        f"'{distractor_text}' is not part of this diagram. "
        f"It may belong to a different structure or is a common misconception."
    )


def _sanitize_interactive_diagram_blueprint(
    blueprint: Dict[str, Any],
    fallback: Dict[str, Any],
    question_text: str,
    domain_knowledge: Optional[Dict[str, Any]] = None,
    diagram_zones: Optional[List[Dict[str, Any]]] = None,
    diagram_labels: Optional[List[Dict[str, Any]]] = None,
    scene_data: Optional[Dict[str, Any]] = None,
    hierarchy_info: Optional[Dict[str, Any]] = None,
    zone_groups: Optional[List[Dict[str, Any]]] = None,  # From gemini_zone_detector
    temporal_constraints: Optional[List[Dict[str, Any]]] = None,  # From zone_planner
    game_plan: Optional[Dict[str, Any]] = None,  # For scoring_rubric
    ped_context: Optional[Dict[str, Any]] = None,  # For common_misconceptions
    interaction_design: Optional[Dict[str, Any]] = None,  # From interaction_designer agent
) -> Dict[str, Any]:
    """
    Ensure INTERACTIVE_DIAGRAM blueprints are schema-correct and free of scene fields.

    Now also handles:
    - New interaction modes (drag_drop, click_to_identify, trace_path, hierarchical)
    - Structured animations
    - Zone groups for hierarchical mode
    - Media assets
    - Hierarchical content detection from game_plan
    """
    sanitized = {k: blueprint.get(k) for k in INTERACTIVE_DIAGRAM_ALLOWED_KEYS if k in blueprint}

    # Set interaction mode based on hierarchy_info if available
    if hierarchy_info and hierarchy_info.get("is_hierarchical"):
        sanitized["interactionMode"] = hierarchy_info.get("recommended_mode", "hierarchical")
        logger.info(
            "Setting hierarchical interaction mode from hierarchy_info",
            mode=sanitized["interactionMode"]
        )
    elif not sanitized.get("interactionMode"):
        sanitized["interactionMode"] = ""

    # Infer interaction mode from scene_data if available
    if scene_data and not blueprint.get("interactionMode"):
        animation_sequences = scene_data.get("animation_sequences", [])
        for seq in animation_sequences:
            if "path" in seq.get("id", "").lower() or "trace" in seq.get("id", "").lower():
                sanitized["interactionMode"] = "trace_path"
                break
            elif "expand" in seq.get("id", "").lower() or "hierarchy" in seq.get("id", "").lower():
                sanitized["interactionMode"] = "hierarchical"
                break

    # Generate structured animations from text-based cues if not provided
    if not sanitized.get("animations") and sanitized.get("animationCues"):
        sanitized["animations"] = _generate_structured_animations(sanitized["animationCues"])

    # Always enforce correct templateType
    sanitized["templateType"] = "INTERACTIVE_DIAGRAM"

    # Fill required fields from fallback if missing/invalid
    for key in ("title", "narrativeIntro", "diagram", "labels", "tasks", "animationCues"):
        if not sanitized.get(key):
            sanitized[key] = fallback.get(key)

    # Ensure diagram structure
    if not isinstance(sanitized.get("diagram"), dict):
        sanitized["diagram"] = fallback.get("diagram", {})
    diagram_allowed = {"assetPrompt", "assetUrl", "width", "height", "zones"}
    sanitized["diagram"] = {k: sanitized["diagram"].get(k) for k in diagram_allowed if k in sanitized["diagram"]}
    if not sanitized["diagram"].get("assetPrompt"):
        sanitized["diagram"]["assetPrompt"] = fallback.get("diagram", {}).get("assetPrompt", "")
    def _coerce_dimension(value: Any, fallback_value: int) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            raw = value.strip().lower()
            if raw.endswith("px"):
                raw = raw[:-2].strip()
            if raw.isdigit():
                return int(raw)
        return fallback_value
    fallback_width = fallback.get("diagram", {}).get("width") or 800
    fallback_height = fallback.get("diagram", {}).get("height") or 600
    sanitized["diagram"]["width"] = _coerce_dimension(sanitized["diagram"].get("width"), fallback_width)
    sanitized["diagram"]["height"] = _coerce_dimension(sanitized["diagram"].get("height"), fallback_height)
    
    # PRIORITY: Use SAM-generated zones if available (overrides LLM-generated zones)
    # Always normalize zones to canonical format
    if isinstance(diagram_zones, list) and diagram_zones:
        normalized_zones = normalize_zones(diagram_zones)
        logger.info(
            "Using SAM-generated zones in sanitized blueprint",
            metadata={
                "zones_count": len(normalized_zones),
                "zone_ids": [z.get("id") for z in normalized_zones[:5]]
            }
        )
        sanitized["diagram"]["zones"] = normalized_zones
    else:
        # Fallback to LLM-generated zones or default
        zones = sanitized["diagram"].get("zones")
        if not isinstance(zones, list) or not zones:
            logger.warning("No SAM zones available, using fallback zones")
            fallback_zones = fallback.get("diagram", {}).get("zones", [])
            sanitized["diagram"]["zones"] = normalize_zones(fallback_zones)
        else:
            logger.info("Using LLM-generated zones (SAM zones not provided)",
                       metadata={"zones_count": len(zones) if isinstance(zones, list) else 0})
            sanitized["diagram"]["zones"] = normalize_zones(zones)
    
    zone_ids = [z.get("id") for z in sanitized["diagram"].get("zones", []) if isinstance(z, dict)]

    def _slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

    # Ensure labels structure - use standardized normalizer
    labels = sanitized.get("labels")
    zones = sanitized.get("diagram", {}).get("zones", [])

    if isinstance(diagram_labels, list) and diagram_labels:
        # Normalize diagram_labels to canonical format
        sanitized["labels"] = normalize_labels(diagram_labels, zones)
        labels = sanitized["labels"]
        logger.info(f"Normalized {len(labels)} diagram_labels to canonical format")
    elif isinstance(labels, list) and labels:
        # Normalize existing labels to canonical format
        sanitized["labels"] = normalize_labels(labels, zones)
        labels = sanitized["labels"]
        logger.info(f"Normalized {len(labels)} existing labels to canonical format")
    elif zones:
        # Create labels from zones if no labels provided
        sanitized["labels"] = create_labels_from_zones(zones)
        labels = sanitized["labels"]
        logger.info(f"Created {len(labels)} labels from zones")
    else:
        sanitized["labels"] = normalize_labels(fallback.get("labels", []), zones)
        labels = sanitized["labels"]

    # Replace generic labels with canonical labels when available
    canonical_labels = (domain_knowledge or {}).get("canonical_labels", []) or []
    if canonical_labels:
        def _is_generic(text: str) -> bool:
            lowered = (text or "").strip().lower()
            return not lowered or lowered.startswith("label") or lowered.startswith("part")

        generic_count = sum(
            1 for label in labels
            if isinstance(label, dict) and _is_generic(label.get("text", ""))
        )
        if labels and generic_count == len(labels):
            sanitized["labels"] = []
            for idx, label_text in enumerate(canonical_labels, start=1):
                if not isinstance(label_text, str) or not label_text.strip():
                    continue
                slug = _slugify(label_text) or str(idx)
                sanitized["labels"].append({
                    "id": f"label_{slug}",
                    "text": label_text.strip(),
                    "correctZoneId": slug
                })
            labels = sanitized["labels"]
        else:
            normalized_canonical = {_slugify(l) for l in canonical_labels if isinstance(l, str)}
            normalized_labels = {
                _slugify(label.get("text", ""))
                for label in labels
                if isinstance(label, dict)
            }
            if normalized_canonical and not normalized_labels.issuperset(normalized_canonical):
                sanitized["labels"] = []
                for idx, label_text in enumerate(canonical_labels, start=1):
                    if not isinstance(label_text, str) or not label_text.strip():
                        continue
                    slug = _slugify(label_text) or str(idx)
                    sanitized["labels"].append({
                        "id": f"label_{slug}",
                        "text": label_text.strip(),
                        "correctZoneId": slug
                    })
                labels = sanitized["labels"]

    # Extract labels from question text if labels are too generic
    def _extract_candidates(text: str) -> List[str]:
        if not text:
            return []
        parts = []
        paren_matches = re.findall(r"\(([^)]+)\)", text)
        parts.extend(paren_matches)

        colon_match = re.search(r"countries?:\s*([^\.]+)", text, re.IGNORECASE)
        if colon_match:
            parts.append(colon_match.group(1))
        else:
            for trigger in ["with", "including"]:
                match = re.search(rf"{trigger}\s+([^\.]+)", text, re.IGNORECASE)
                if match:
                    parts.append(match.group(1))
                    break

        candidates = []
        for part in parts:
            chunk = part.split(".")[0]
            chunk = chunk.replace(" and ", ", ")
            for item in chunk.split(","):
                item = item.strip(" .;:")
                if not item:
                    continue
                item = re.sub(r"^\d+\s+\w+\s+", "", item)
                item = re.sub(r"^(major\s+)?countries?\s*[:\-]?\s*", "", item, flags=re.IGNORECASE)
                if ":" in item:
                    item = item.split(":", 1)[1].strip()
                if not item or len(item) < 2:
                    continue
                candidates.append(item.title())
        # De-duplicate while preserving order
        seen = set()
        result = []
        for item in candidates:
            if item.lower() in seen:
                continue
            seen.add(item.lower())
            result.append(item)
        return result

    def _slug(value: str) -> str:
        return re.sub(r"\W+", "_", value).strip("_").lower()

    if labels and all(isinstance(l, dict) and l.get("text", "").lower().startswith("label") for l in labels):
        candidates = _extract_candidates(question_text)
        if len(candidates) >= 3:
            sanitized["labels"] = [
                {"id": f"label_{_slug(name)}", "text": name, "correctZoneId": _slug(name)}
                for name in candidates
            ]
            labels = sanitized["labels"]

    # Align zones with labels if references don't match
    if isinstance(labels, list) and labels:
        label_zone_ids = []
        seen_label_ids = set()
        seen_zone_ids = set()
        for i, label in enumerate(labels):
            if not isinstance(label, dict):
                continue
            if not label.get("id") and label.get("labelId"):
                label["id"] = label.get("labelId")
            label_text = label.get("text") or f"Label {i + 1}"
            if not label.get("text"):
                label["text"] = label_text
            base_label_id = label.get("id") or f"label_{_slug(label_text)}"
            label_id = base_label_id
            suffix = 1
            while label_id in seen_label_ids:
                suffix += 1
                label_id = f"{base_label_id}_{suffix}"
            label["id"] = label_id
            seen_label_ids.add(label_id)

            base_zone_id = label.get("correctZoneId") or f"zone_{_slug(label_text)}"
            zone_id = base_zone_id
            suffix = 1
            while zone_id in seen_zone_ids:
                suffix += 1
                zone_id = f"{base_zone_id}_{suffix}"
            label["correctZoneId"] = zone_id
            seen_zone_ids.add(zone_id)
            label_zone_ids.append(zone_id)

        existing_zone_ids = zone_ids
        has_duplicate_zone_ids = len(existing_zone_ids) != len(set(existing_zone_ids))
        missing_zone_ids = set(label_zone_ids) - set(existing_zone_ids) if existing_zone_ids else set(label_zone_ids)
        
        # Only regenerate zones if we're NOT using SAM-generated zones
        # If diagram_zones were provided (from SAM), preserve them and update labels to match
        if isinstance(diagram_zones, list) and diagram_zones:
            # Using SAM zones - update labels to match zone IDs, don't regenerate zones
            logger.info("Preserving SAM-generated zones, updating labels to match zone IDs")
            # Use diagram_labels if provided, otherwise match labels to zones by text
            if isinstance(diagram_labels, list) and diagram_labels:
                # Use provided labels (from zone labeler)
                sanitized["labels"] = diagram_labels
                logger.info("Using SAM-generated labels", labels_count=len(diagram_labels))
            else:
                # Match labels to zones
                zone_id_set = set(existing_zone_ids)
                for label in labels:
                    if not isinstance(label, dict):
                        continue
                    # Find matching zone for this label
                    label_text = label.get("text", "")
                    # Try to find zone with matching label text
                    matching_zone = None
                    for zone in sanitized["diagram"]["zones"]:
                        if isinstance(zone, dict):
                            zone_label = zone.get("label", "")
                            if zone_label and label_text and zone_label.lower() == label_text.lower():
                                matching_zone = zone
                                break
                    
                    if matching_zone:
                        label["correctZoneId"] = matching_zone.get("id")
                    elif existing_zone_ids:
                        # Assign to first available zone if no match found
                        label["correctZoneId"] = existing_zone_ids[0]
        elif has_duplicate_zone_ids or missing_zone_ids:
            # Only regenerate if NOT using SAM zones
            positions = _generate_default_zone_positions(len(label_zone_ids))
            new_zones = []
            for i, zone_id in enumerate(label_zone_ids):
                label_text = labels[i].get("text") if isinstance(labels[i], dict) else None
                new_zones.append({
                    "id": zone_id,
                    "label": label_text or f"Part {i + 1}",
                    "x": positions[i][0],
                    "y": positions[i][1],
                    "radius": 10
                })
            sanitized["diagram"]["zones"] = new_zones
            zone_ids = label_zone_ids

    # Ensure zone labels are meaningful (avoid generic Part labels)
    if isinstance(sanitized["diagram"].get("zones"), list):
        zone_map = {z.get("id"): z for z in sanitized["diagram"]["zones"] if isinstance(z, dict)}
        for label in labels:
            if not isinstance(label, dict):
                continue
            zone = zone_map.get(label.get("correctZoneId"))
            if zone and zone.get("label", "").lower().startswith("part"):
                zone["label"] = label.get("text", zone["label"])

    # Set zone groups - priority order:
    # 1. zone_groups from gemini_zone_detector (most accurate)
    # 2. Generate from hierarchy_info
    # 3. Existing zoneGroups in blueprint
    if zone_groups:
        # Use zone groups from detector (already properly formatted)
        sanitized["zoneGroups"] = zone_groups
        sanitized["interactionMode"] = "hierarchical"
        logger.info(
            "Using zone_groups from detector",
            group_count=len(zone_groups),
            groups=[g.get("id") for g in zone_groups]
        )
    elif hierarchy_info and hierarchy_info.get("is_hierarchical"):
        if not sanitized.get("zoneGroups"):
            zones_for_grouping = sanitized.get("diagram", {}).get("zones", [])
            generated_groups = _generate_zone_groups_from_hierarchy(hierarchy_info, zones_for_grouping)
            if generated_groups:
                sanitized["zoneGroups"] = generated_groups
                sanitized["interactionMode"] = "hierarchical"
                logger.info(
                    "Generated zone groups from hierarchy_info",
                    group_count=len(generated_groups),
                    groups=[g.get("id") for g in generated_groups]
                )
        else:
            logger.info(
                "Using existing zoneGroups from blueprint",
                group_count=len(sanitized.get("zoneGroups", []))
            )

    # Infer interaction mode from game_plan mechanics
    if game_plan and not sanitized.get("interactionMode"):
        game_mechanics = game_plan.get("game_mechanics", [])
        for mechanic in game_mechanics:
            if not isinstance(mechanic, dict):
                continue
            mechanic_type = mechanic.get("type", "").lower()
            # Check for trace/path/flow mechanics
            if mechanic_type in ("trace", "trace_path", "path", "flow", "trace_flow"):
                sanitized["interactionMode"] = "trace_path"
                logger.info(
                    "Setting trace_path mode from game_plan mechanic",
                    mechanic_type=mechanic_type
                )
                break
            # Check for sequence/order mechanics that might be trace-based
            elif mechanic_type in ("sequence", "order", "ordering"):
                # Only set trace_path if the mechanic description suggests tracing
                desc = mechanic.get("description", "").lower()
                if any(word in desc for word in ("trace", "flow", "path", "follow")):
                    sanitized["interactionMode"] = "trace_path"
                    logger.info(
                        "Setting trace_path mode from sequence mechanic with trace-like description",
                        mechanic_type=mechanic_type,
                        description=mechanic.get("description")
                    )
                    break

    # Set default interaction mode if not set
    if not sanitized.get("interactionMode"):
        sanitized["interactionMode"] = ""

    # Ensure tasks structure
    tasks = sanitized.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        sanitized["tasks"] = fallback.get("tasks", [])
    else:
        first_task = tasks[0] if tasks else {}
        if not isinstance(first_task, dict) or not first_task.get("questionText") or first_task.get("type") != "interactive_diagram":
            sanitized["tasks"] = fallback.get("tasks", [])

    # Ensure animation cues structure
    anim = sanitized.get("animationCues")
    if not isinstance(anim, dict):
        anim = {}
    required_anim_keys = ["correctPlacement", "incorrectPlacement"]
    if any(not isinstance(anim.get(k), str) or not anim.get(k) for k in required_anim_keys):
        anim = fallback.get("animationCues", {})
    if anim.get("labelDrag") is not None and not isinstance(anim.get("labelDrag"), str):
        anim["labelDrag"] = None
    if anim.get("allLabeled") is not None and not isinstance(anim.get("allLabeled"), str):
        anim["allLabeled"] = None
    sanitized["animationCues"] = anim

    # Filter hints to existing zones and auto-generate missing hints
    zone_id_set = set(zone_ids) if zone_ids else set()
    existing_hints = sanitized.get("hints", [])

    if isinstance(existing_hints, list) and zone_id_set:
        # Filter to valid zone IDs
        sanitized["hints"] = [
            h for h in existing_hints
            if isinstance(h, dict) and h.get("zoneId") in zone_id_set
        ]
    else:
        sanitized["hints"] = []

    # Auto-generate hints for zones without hints using domain_knowledge
    if domain_knowledge and zone_id_set:
        existing_hint_zones = {h.get("zoneId") for h in sanitized["hints"] if isinstance(h, dict)}
        zones_without_hints = zone_id_set - existing_hint_zones

        # Get zone label mapping
        zone_label_map = {}
        for zone in sanitized.get("diagram", {}).get("zones", []):
            if isinstance(zone, dict):
                zone_label_map[zone.get("id")] = zone.get("label", "")

        # Generate hints for zones missing them
        generated_hints = []
        for zone_id in zones_without_hints:
            zone_label = zone_label_map.get(zone_id, "")
            if zone_label:
                hint_text = _generate_hint_for_label(
                    label=zone_label,
                    domain_knowledge=domain_knowledge,
                    hierarchy_info=hierarchy_info
                )
                generated_hints.append({
                    "zoneId": zone_id,
                    "hint": hint_text
                })

        if generated_hints:
            sanitized["hints"].extend(generated_hints)
            logger.info(f"Auto-generated {len(generated_hints)} hints from domain_knowledge")

    # === Calculate maxScore from interaction_design, scoring_rubric, or label count ===
    # Priority: 1) interaction_design.scoring_strategy, 2) scoring_rubric.max_score from game_plan, 3) label_count * 10
    label_count = len(sanitized.get("labels", []))
    scoring_rubric = (game_plan or {}).get("scoring_rubric", {})
    scoring_strategy = (interaction_design or {}).get("scoring_strategy", {})

    # Use scoring_strategy from interaction_design if available (agentic design)
    if isinstance(scoring_strategy, dict) and scoring_strategy.get("max_score"):
        sanitized["maxScore"] = int(scoring_strategy["max_score"])
        logger.debug(f"Using maxScore from interaction_design.scoring_strategy: {sanitized['maxScore']}")
    elif isinstance(scoring_rubric, dict) and scoring_rubric.get("max_score"):
        sanitized["maxScore"] = int(scoring_rubric["max_score"])
        logger.debug(f"Using maxScore from scoring_rubric: {sanitized['maxScore']}")
    else:
        # Use base_points_per_zone from interaction_design or shared constant
        base_points = scoring_strategy.get("base_points_per_zone", DEFAULT_SCORING["base_points_per_zone"]) if scoring_strategy else DEFAULT_SCORING["base_points_per_zone"]
        sanitized["maxScore"] = label_count * base_points if label_count > 0 else 100
        logger.debug(f"Calculated maxScore: {sanitized['maxScore']} ({label_count} labels x {base_points})")

    # Include partial_credit, time_bonus, and hint_penalty settings
    # Priority: interaction_design.scoring_strategy > game_plan.scoring_rubric
    if isinstance(scoring_strategy, dict) and scoring_strategy:
        if scoring_strategy.get("partial_credit") is not None:
            sanitized["partialCredit"] = bool(scoring_strategy["partial_credit"])
        time_bonus = scoring_strategy.get("time_bonus", {})
        if isinstance(time_bonus, dict):
            sanitized["timeBonus"] = bool(time_bonus.get("enabled", False))
            if time_bonus.get("max_bonus"):
                sanitized["timeBonusMax"] = int(time_bonus["max_bonus"])
        elif time_bonus is not None:
            sanitized["timeBonus"] = bool(time_bonus)
        if scoring_strategy.get("hint_penalty") is not None:
            sanitized["hintPenalty"] = float(scoring_strategy["hint_penalty"]) / 100.0  # Convert from percentage
    elif isinstance(scoring_rubric, dict):
        if scoring_rubric.get("partial_credit") is not None:
            sanitized["partialCredit"] = bool(scoring_rubric["partial_credit"])
        if scoring_rubric.get("time_bonus") is not None:
            sanitized["timeBonus"] = bool(scoring_rubric["time_bonus"])
        if scoring_rubric.get("hint_penalty") is not None:
            sanitized["hintPenalty"] = float(scoring_rubric["hint_penalty"])

    # Also use interaction mode from interaction_design if not already set
    if interaction_design and not sanitized.get("interactionMode"):
        primary_mode = interaction_design.get("primary_interaction_mode")
        if primary_mode:
            sanitized["interactionMode"] = primary_mode
            logger.debug(f"Using interactionMode from interaction_design: {primary_mode}")

    # === Propagate mechanics list from interaction_design ===
    if interaction_design:
        # Build flat mechanics list: [primary, ...additional]
        primary_mode = sanitized.get("interactionMode") or ""
        additional_modes = interaction_design.get("secondary_modes", [])
        if additional_modes:
            mechanics_list = [{"type": primary_mode}]
            for m in additional_modes:
                mechanics_list.append({"type": m})
            sanitized["mechanics"] = mechanics_list
            logger.debug(f"Built mechanics list from interaction_design: {[m['type'] for m in mechanics_list]}")

        # Mode transitions (triggers for switching between modes)
        mode_transitions = interaction_design.get("mode_transitions", [])
        if mode_transitions:
            sanitized["modeTransitions"] = mode_transitions
            logger.debug(f"Added {len(mode_transitions)} modeTransitions from interaction_design")

        # Scoring strategy for frontend
        scoring_strat = interaction_design.get("scoring_strategy", {})
        if scoring_strat:
            sanitized["scoringStrategy"] = {
                "type": scoring_strat.get("type", "standard"),
                "base_points_per_zone": scoring_strat.get("base_points_per_zone", DEFAULT_SCORING["base_points_per_zone"]),
                "time_bonus_enabled": scoring_strat.get("time_bonus_enabled", False),
                "partial_credit": scoring_strat.get("partial_credit", True),
                "max_score": scoring_strat.get("max_score"),
            }
            logger.debug(f"Added scoringStrategy from interaction_design: {sanitized['scoringStrategy']}")

        # Feedback messages for frontend
        feedback_messages = interaction_design.get("feedback_messages")
        if feedback_messages:
            sanitized["feedbackMessages"] = feedback_messages
        elif not sanitized.get("feedbackMessages"):
            sanitized["feedbackMessages"] = DEFAULT_FEEDBACK

        # Thresholds for frontend
        thresholds = interaction_design.get("thresholds")
        if thresholds:
            sanitized["thresholds"] = thresholds
        elif not sanitized.get("thresholds"):
            sanitized["thresholds"] = DEFAULT_THRESHOLDS

        # Animation config
        animation_config = interaction_design.get("animation_config", {})
        if animation_config and not sanitized.get("animations"):
            sanitized["animations"] = {
                "correctPlacement": {"type": animation_config.get("correct_animation", "pulse")},
                "incorrectPlacement": {"type": animation_config.get("incorrect_animation", "shake")},
                "completion": {"type": animation_config.get("completion_animation", "confetti")},
            }

    # === Generate distractor feedback using common_misconceptions ===
    # Extract common_misconceptions from pedagogical context for targeted feedback
    common_misconceptions = (ped_context or {}).get("common_misconceptions", [])
    labels = sanitized.get("labels", [])
    label_texts = [l.get("text", "") for l in labels if isinstance(l, dict)]

    distractor_labels = sanitized.get("distractorLabels", [])
    if isinstance(distractor_labels, list):
        updated_distractors = []
        for i, distractor in enumerate(distractor_labels):
            if isinstance(distractor, dict):
                distractor_text = distractor.get("text", "This label")
                # Generate targeted feedback using common_misconceptions
                if not distractor.get("explanation") or distractor.get("explanation", "").startswith("'"):
                    # Find related label for context
                    related_label = label_texts[i % len(label_texts)] if label_texts else ""
                    distractor["explanation"] = _generate_feedback_for_distractor(
                        distractor_text=distractor_text,
                        label_text=related_label,
                        common_misconceptions=common_misconceptions,
                        domain_knowledge=domain_knowledge
                    )
                updated_distractors.append(distractor)
        sanitized["distractorLabels"] = updated_distractors
        if common_misconceptions:
            logger.debug(f"Generated distractor feedback using {len(common_misconceptions)} misconceptions")

    # === NEW: Copy generated_diagram_path to diagram.assetUrl if not set ===
    # This ensures the generated diagram is included in the blueprint
    if not sanitized.get("diagram", {}).get("assetUrl"):
        # The assetUrl will be set by the main function from cleaned_image_path or diagram_image
        pass  # Handled in main blueprint_generator_agent function

    # === NEW: Include temporal constraints for frontend Petri Net-inspired visibility ===
    # These constraints control zone reveal order and mutex relationships
    if temporal_constraints:
        sanitized["temporalConstraints"] = temporal_constraints
        logger.info(
            f"Added {len(temporal_constraints)} temporal constraints to blueprint",
            metadata={
                "mutex_count": sum(1 for c in temporal_constraints if c.get("constraint_type") == "mutex"),
                "concurrent_count": sum(1 for c in temporal_constraints if c.get("constraint_type") == "concurrent"),
            }
        )

    # === NEW: Include difficulty_progression from game_plan ===
    # This enables frontend to implement progressive difficulty levels
    if game_plan:
        difficulty_progression = game_plan.get("difficulty_progression", {})
        if difficulty_progression:
            sanitized["difficultyProgression"] = {
                "levels": difficulty_progression.get("levels", []),
                "progressionRules": difficulty_progression.get("progression_rules", []),
                "initialState": difficulty_progression.get("initial_state", {}),
            }
            logger.debug(f"Added difficultyProgression from game_plan")

        # Also include game_mechanics summary for frontend
        game_mechanics = game_plan.get("game_mechanics", [])
        if game_mechanics:
            sanitized["gameMechanics"] = [
                {
                    "id": m.get("id"),
                    "type": m.get("type"),
                    "weight": m.get("weight"),
                    "description": m.get("description", ""),
                }
                for m in game_mechanics
            ]
            logger.debug(f"Added {len(game_mechanics)} game mechanics to blueprint")

    # Phase 0: Generate sequenceConfig from order/sequence mechanics
    sequence_config = _generate_sequence_config_from_mechanics(game_plan, domain_knowledge)
    if sequence_config:
        sanitized["sequenceConfig"] = sequence_config
        logger.info(
            "Added sequenceConfig to blueprint",
            item_count=len(sequence_config.get("items", [])),
            sequence_type=sequence_config.get("sequenceType")
        )

    # Generate paths for trace_path mode from sequence data
    interaction_mode = sanitized.get("interactionMode") or ""
    zones = sanitized.get("diagram", {}).get("zones", [])
    paths = _generate_paths_from_mechanics(game_plan, domain_knowledge, zones, interaction_mode)
    if paths:
        sanitized["paths"] = paths
        logger.info(
            "Added trace_path paths to blueprint",
            path_count=len(paths),
            total_waypoints=sum(len(p.get("waypoints", [])) for p in paths)
        )

    return sanitized


def _create_fallback_blueprint(
    template_type: str,
    question_text: str,
    question_options: Optional[List[str]],
    scene_data: Dict[str, Any] = None,
    story_data: Dict[str, Any] = None  # Legacy support
) -> Dict[str, Any]:
    """Create a fallback blueprint when LLM fails"""

    # Prefer scene_data, fallback to story_data
    if scene_data:
        title = scene_data.get("scene_title", "Learning Challenge")
        context = scene_data.get("minimal_context", question_text[:200])
    elif story_data:
        title = story_data.get("story_title", "Learning Challenge")
        context = story_data.get("story_context", question_text[:200])
    else:
        title = "Learning Challenge"
        context = question_text[:200]

    base = {
        "templateType": template_type,
        "title": title,
        "narrativeIntro": context,
        "tasks": [{
            "id": "task_1",
            "type": "primary",
            "questionText": question_text,
            "requiredToProceed": True
        }],
        "animationCues": {
            "onCorrect": "celebration",
            "onIncorrect": "encouragement"
        }
    }

    # Add template-specific fields
    if template_type == "PARAMETER_PLAYGROUND":
        base["parameters"] = [{
            "id": "param_1",
            "label": "Value",
            "type": "slider",
            "min": 0,
            "max": 100,
            "defaultValue": 50,
            "unit": ""
        }]
        base["visualization"] = {
            "type": "simulation",
            "description": "Interactive visualization"
        }
        base["animationCues"] = {
            "parameterChange": "smooth transition",
            "visualizationUpdate": "animate change",
            "targetReached": "success celebration"
        }

    elif template_type == "SEQUENCE_BUILDER":
        base["steps"] = []
        if question_options:
            for i, opt in enumerate(question_options):
                base["steps"].append({
                    "id": f"step_{i + 1}",
                    "text": opt,
                    "orderIndex": i + 1
                })
        else:
            base["steps"] = [
                {"id": "step_1", "text": "First step", "orderIndex": 1},
                {"id": "step_2", "text": "Second step", "orderIndex": 2},
                {"id": "step_3", "text": "Third step", "orderIndex": 3}
            ]
        base["tasks"][0]["type"] = "sequence_order"
        base["animationCues"] = {
            "stepDrag": "lift and glow",
            "correctPlacement": "snap into place with sparkle",
            "incorrectPlacement": "shake and return",
            "sequenceComplete": "full celebration"
        }

    elif template_type == "BUCKET_SORT":
        base["buckets"] = [
            {"id": "bucket_1", "label": "Category A"},
            {"id": "bucket_2", "label": "Category B"}
        ]
        base["items"] = []
        if question_options:
            for i, opt in enumerate(question_options):
                base["items"].append({
                    "id": f"item_{i + 1}",
                    "text": opt,
                    "correctBucketId": f"bucket_{(i % 2) + 1}"
                })
        base["tasks"][0]["type"] = "bucket_sort"
        base["animationCues"] = {
            "itemDrag": "lift with shadow",
            "correctDrop": "green flash and settle",
            "incorrectDrop": "red shake and return",
            "bucketFull": "bucket glow"
        }

    elif template_type == "INTERACTIVE_DIAGRAM":
        base["diagram"] = {
            "assetPrompt": f"Educational diagram for: {question_text[:50]}",
            "zones": [
                {"id": "zone_1", "label": "Part 1", "x": 30, "y": 30, "radius": 10},
                {"id": "zone_2", "label": "Part 2", "x": 70, "y": 50, "radius": 10}
            ]
        }
        base["labels"] = [
            {"id": "label_1", "text": "Label A", "correctZoneId": "zone_1"},
            {"id": "label_2", "text": "Label B", "correctZoneId": "zone_2"}
        ]
        base["tasks"][0]["type"] = "interactive_diagram"
        base["animationCues"] = {
            "correctPlacement": "snap and highlight",
            "incorrectPlacement": "bounce back"
        }

    elif template_type == "MATCH_PAIRS":
        base["pairs"] = []
        if question_options and len(question_options) >= 2:
            for i in range(0, len(question_options), 2):
                if i + 1 < len(question_options):
                    base["pairs"].append({
                        "id": f"pair_{i // 2 + 1}",
                        "leftItem": {"id": f"left_{i + 1}", "text": question_options[i]},
                        "rightItem": {"id": f"right_{i + 1}", "text": question_options[i + 1]}
                    })
        else:
            base["pairs"] = [{
                "id": "pair_1",
                "leftItem": {"id": "left_1", "text": "Item A"},
                "rightItem": {"id": "right_1", "text": "Match A"}
            }]
        base["tasks"][0]["type"] = "match_pairs"
        base["animationCues"] = {
            "cardFlip": "flip animation",
            "cardMatch": "matched glow",
            "cardMismatch": "shake and flip back",
            "allMatched": "celebration"
        }

    elif template_type == "STATE_TRACER_CODE":
        base["code"] = "# Example code\nx = 1\ny = 2\nresult = x + y"
        base["steps"] = [
            {"index": 0, "description": "Initialize x", "expectedVariables": {"x": 1}},
            {"index": 1, "description": "Initialize y", "expectedVariables": {"x": 1, "y": 2}},
            {"index": 2, "description": "Calculate result", "expectedVariables": {"x": 1, "y": 2, "result": 3}}
        ]
        base["tasks"][0]["type"] = "variable_value"
        base["animationCues"] = {
            "lineHighlight": "glow current line",
            "variableUpdate": "highlight changed variable",
            "stepComplete": "checkmark"
        }

    return base


# Validator for blueprints
async def validate_blueprint(
    blueprint: Dict[str, Any],
    template_type: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validate the blueprint against template schema.

    Returns:
        Dict with 'valid' bool, 'errors' list, and 'warnings' list
    """
    errors = []
    warnings = []

    # Get template schema
    template_info = TEMPLATE_SCHEMAS.get(template_type, {})
    required_fields = template_info.get("required", ["templateType", "title", "tasks"])

    # Check required fields with actionable guidance
    for field in required_fields:
        if field not in blueprint:
            errors.append(
                f"FIX: Missing required field '{field}'. "
                f"Add '{field}' to the blueprint JSON at the root level."
            )

    # Check templateType matches
    if blueprint.get("templateType") != template_type:
        errors.append(f"templateType mismatch: expected {template_type}, got {blueprint.get('templateType')}")

    # Check tasks structure
    tasks = blueprint.get("tasks", [])
    if not tasks:
        errors.append("No tasks defined")
    else:
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"Task {i} is not an object")
            elif not task.get("id"):
                errors.append(f"Task {i} missing id")
            elif not task.get("questionText"):
                warnings.append(f"Task {task.get('id')} missing questionText")

    context = context or {}
    question_text = (context.get("question_text") or "").lower()
    ped_context = context.get("pedagogical_context") or {}
    domain_knowledge = context.get("domain_knowledge") or {}
    diagram_zones_context = context.get("diagram_zones") or []
    diagram_image_context = context.get("diagram_image") or {}

    # Template-specific validation
    if template_type == "SEQUENCE_BUILDER":
        steps = blueprint.get("steps", [])
        if not steps:
            errors.append("SEQUENCE_BUILDER requires steps")
        else:
            order_indices = [s.get("orderIndex") for s in steps if s.get("orderIndex") is not None]
            if len(order_indices) != len(set(order_indices)):
                errors.append("Duplicate orderIndex values in steps")

    elif template_type == "BUCKET_SORT":
        buckets = blueprint.get("buckets", [])
        items = blueprint.get("items", [])
        if not buckets:
            errors.append("BUCKET_SORT requires buckets")
        if not items:
            errors.append("BUCKET_SORT requires items")
        else:
            bucket_ids = {b.get("id") for b in buckets}
            for item in items:
                if item.get("correctBucketId") not in bucket_ids:
                    errors.append(f"Item {item.get('id')} has invalid correctBucketId")

    elif template_type == "INTERACTIVE_DIAGRAM":
        diagram = blueprint.get("diagram", {})
        zones = diagram.get("zones", [])
        labels = blueprint.get("labels", [])

        # Validate zones exist
        if not zones:
            errors.append("INTERACTIVE_DIAGRAM requires diagram.zones")
        if not labels:
            errors.append("INTERACTIVE_DIAGRAM requires labels")

        # Validate diagram dimensions are numeric if provided
        for dim_key in ("width", "height"):
            dim_val = diagram.get(dim_key)
            if dim_val is not None and not isinstance(dim_val, (int, float)):
                errors.append(f"diagram.{dim_key} must be numeric")

        # Validate zone coordinates (0-100 range) and radius
        zone_ids = []
        for zone in zones:
            zone_id = zone.get("id", "unknown")
            x, y = zone.get("x"), zone.get("y")

            # Check coordinates exist
            if x is None or y is None:
                errors.append(
                    f"FIX: Zone '{zone_id}' missing coordinates. Add 'x' and 'y' fields (0-100 scale). "
                    f"Example: {{'id': '{zone_id}', 'x': 50, 'y': 50, 'radius': 10}}"
                )
            elif not (0 <= x <= 100 and 0 <= y <= 100):
                errors.append(
                    f"FIX: Zone '{zone_id}' has out-of-range coordinates (x={x}, y={y}). "
                    f"Coordinates must be 0-100. Use x={min(100, max(0, x))}, y={min(100, max(0, y))}."
                )

            # Check zone shape - either radius (circle) or points (polygon)
            has_radius = zone.get("radius") is not None
            has_points = zone.get("points") is not None and len(zone.get("points", [])) >= 3

            if not has_radius and not has_points:
                errors.append(
                    f"FIX: Zone '{zone_id}' missing shape definition. Add 'radius' field (typical: 8-15) for circle "
                    f"or 'points' array for polygon. Example: {{'id': '{zone_id}', ..., 'radius': 10}}"
                )
            elif has_radius:
                if zone.get("radius") < 1 or zone.get("radius") > 50:
                    warnings.append(
                        f"ADJUST: Zone '{zone_id}' radius={zone.get('radius')} is unusual (recommended: 5-15). "
                        f"Smaller radius for precise targets, larger for easier interaction."
                    )
            # For polygon zones, validate points
            elif has_points:
                points = zone.get("points", [])
                for i, pt in enumerate(points):
                    if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                        errors.append(f"FIX: Zone '{zone_id}' has invalid point at index {i}")
                        break

            zone_ids.append(zone_id)

        if len(zone_ids) != len(set(zone_ids)):
            # Find the duplicates
            seen = set()
            duplicates = []
            for zid in zone_ids:
                if zid in seen:
                    duplicates.append(zid)
                seen.add(zid)
            errors.append(
                f"FIX: Duplicate zone ids: {duplicates[:3]}. Each zone needs unique id. "
                f"Rename duplicates using descriptive suffixes like 'zone_left_lung', 'zone_right_lung'."
            )

        # Validate label references to zones
        seen_label_ids = set()
        for idx, label in enumerate(labels):
            # Handle both dict and string label formats
            if isinstance(label, str):
                # Simple string label - convert to expected format conceptually
                label_id = f"label_{idx}"
                label_text = label
                correct_zone = None
            elif isinstance(label, dict):
                label_id = label.get("id", f"label_{idx}")
                label_text = label.get("text")
                correct_zone = label.get("correctZoneId")

                if not label.get("id"):
                    errors.append(
                        f"FIX: Label at index {idx} missing 'id'. Add unique id like 'label_{idx + 1}' or "
                        f"'label_{{descriptive_name}}'."
                    )
                elif label_id in seen_label_ids:
                    errors.append(
                        f"FIX: Duplicate label id '{label_id}'. Each label needs unique id. "
                        f"Change to '{label_id}_{idx + 1}' or use descriptive suffix."
                    )
                else:
                    seen_label_ids.add(label_id)

                if not label_text:
                    errors.append(
                        f"FIX: Label '{label_id}' missing 'text' field. Add the display text. "
                        f"Example: {{'id': '{label_id}', 'text': 'Heart', 'correctZoneId': 'zone_heart'}}"
                    )

                if correct_zone and correct_zone not in set(zone_ids):
                    available_zones = ", ".join(zone_ids[:5]) + ("..." if len(zone_ids) > 5 else "")
                    errors.append(
                        f"FIX: Label '{label_id}' references non-existent zone '{correct_zone}'. "
                        f"Available zones: [{available_zones}]. Update correctZoneId to match."
                    )
            else:
                errors.append(f"FIX: Label at index {idx} has invalid type {type(label).__name__}. Expected dict or string.")

        # Semantic validation using domain knowledge (if available)
        canonical_labels = domain_knowledge.get("canonical_labels", []) or []
        acceptable_variants = domain_knowledge.get("acceptable_variants", {}) or {}
        if canonical_labels:
            normalized_canonical = {c.strip().lower() for c in canonical_labels if isinstance(c, str)}
            normalized_variants = set()
            for key, variants in acceptable_variants.items():
                if isinstance(variants, list):
                    normalized_variants.update(v.strip().lower() for v in variants if isinstance(v, str))
                if isinstance(key, str):
                    normalized_variants.add(key.strip().lower())
            allowed = normalized_canonical.union(normalized_variants)
            for label in labels:
                # Handle both string and dict label formats
                if isinstance(label, str):
                    label_text = label.strip().lower()
                    label_display = label
                elif isinstance(label, dict):
                    label_text = (label.get("text") or "").strip().lower()
                    label_display = label.get("text", "unknown")
                else:
                    continue
                if label_text and label_text not in allowed:
                    canonical_examples = list(normalized_canonical)[:4]
                    errors.append(
                        f"FIX: Label '{label_display}' not in canonical labels. "
                        f"Use correct terminology: {canonical_examples}..."
                    )

        # Minimum label count heuristic for anatomy/diagram prompts
        anatomy_keywords = ("parts of", "anatomy", "diagram", "label the parts", "structures of")
        subject = (ped_context.get("subject") or "").lower()
        needs_richer_labels = any(k in question_text for k in anatomy_keywords) or subject in {
            "biology",
            "botany",
            "anatomy",
            "medicine",
        }
        if needs_richer_labels and len(labels) < 6:
            errors.append(
                f"FIX: INTERACTIVE_DIAGRAM has {len(labels)} labels but anatomy/diagram topics require at least 6. "
                f"Add more labels covering all key structures. Check domain_knowledge.canonical_labels for required terms."
            )

        if diagram_zones_context:
            if len(labels) != len(diagram_zones_context):
                errors.append("INTERACTIVE_DIAGRAM labels count must match segmented zone count")
        if diagram_image_context and not diagram.get("assetUrl"):
            warnings.append("Diagram image available but assetUrl missing in blueprint")

        # Validate animation cues
        animation_cues = blueprint.get("animationCues", {})
        if not isinstance(animation_cues, dict):
            errors.append("animationCues must be an object")
        else:
            if not animation_cues.get("correctPlacement"):
                errors.append("animationCues.correctPlacement missing")
            if not animation_cues.get("incorrectPlacement"):
                errors.append("animationCues.incorrectPlacement missing")

        # Validate structured animations if present
        animations = blueprint.get("animations")
        if animations and isinstance(animations, dict):
            valid_anim_types = {"pulse", "glow", "scale", "shake", "fade", "bounce", "confetti", "path_draw"}
            valid_easings = {"linear", "ease-out", "ease-in-out", "bounce", "elastic"}

            for anim_key, anim_spec in animations.items():
                if not isinstance(anim_spec, dict):
                    continue
                anim_type = anim_spec.get("type")
                if anim_type and anim_type not in valid_anim_types:
                    warnings.append(
                        f"Animation '{anim_key}' has unknown type '{anim_type}'. "
                        f"Valid types: {valid_anim_types}"
                    )
                easing = anim_spec.get("easing")
                if easing and easing not in valid_easings:
                    warnings.append(
                        f"Animation '{anim_key}' has unknown easing '{easing}'. "
                        f"Valid easings: {valid_easings}"
                    )

        # Validate interaction mode
        interaction_mode = blueprint.get("interactionMode") or ""
        valid_modes = {"drag_drop", "click_to_identify", "trace_path", "hierarchical"}
        if interaction_mode not in valid_modes:
            errors.append(
                f"Invalid interactionMode '{interaction_mode}'. "
                f"Valid modes: {valid_modes}"
            )

        # Validate click_to_identify mode requirements
        if interaction_mode == "click_to_identify":
            prompts = blueprint.get("identificationPrompts", [])
            if not prompts:
                warnings.append(
                    "click_to_identify mode should have identificationPrompts defined"
                )
            else:
                for prompt in prompts:
                    if not isinstance(prompt, dict):
                        continue
                    prompt_zone = prompt.get("zoneId")
                    if prompt_zone and prompt_zone not in set(zone_ids):
                        errors.append(
                            f"IdentificationPrompt references non-existent zone '{prompt_zone}'"
                        )

        # Validate trace_path mode requirements
        if interaction_mode == "trace_path":
            paths = blueprint.get("paths", [])
            if not paths:
                warnings.append(
                    "trace_path mode should have paths defined"
                )
            else:
                for path in paths:
                    if not isinstance(path, dict):
                        continue
                    waypoints = path.get("waypoints", [])
                    for wp in waypoints:
                        if isinstance(wp, dict):
                            wp_zone = wp.get("zoneId")
                            if wp_zone and wp_zone not in set(zone_ids):
                                errors.append(
                                    f"Path waypoint references non-existent zone '{wp_zone}'"
                                )

        # Validate hierarchical mode requirements
        if interaction_mode == "hierarchical":
            zone_groups = blueprint.get("zoneGroups", [])
            if not zone_groups:
                warnings.append(
                    "hierarchical mode should have zoneGroups defined"
                )
            else:
                for group in zone_groups:
                    if not isinstance(group, dict):
                        continue
                    parent_zone = group.get("parentZoneId")
                    if parent_zone and parent_zone not in set(zone_ids):
                        errors.append(
                            f"ZoneGroup references non-existent parent zone '{parent_zone}'"
                        )
                    child_zones = group.get("childZoneIds", [])
                    for child in child_zones:
                        if child not in set(zone_ids):
                            errors.append(
                                f"ZoneGroup references non-existent child zone '{child}'"
                            )

    elif template_type == "PARAMETER_PLAYGROUND":
        if not blueprint.get("parameters"):
            errors.append("PARAMETER_PLAYGROUND requires parameters")
        if not blueprint.get("visualization"):
            errors.append("PARAMETER_PLAYGROUND requires visualization")

    # Check animation cues
    if not blueprint.get("animationCues"):
        warnings.append("Missing animationCues - game may lack feedback")

    # Add pedagogical validation
    ped_errors, ped_warnings = _validate_pedagogical_alignment(
        blueprint, template_type, ped_context, domain_knowledge
    )
    errors.extend(ped_errors)
    warnings.extend(ped_warnings)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "blueprint": blueprint
    }


def _validate_pedagogical_alignment(
    blueprint: Dict[str, Any],
    template_type: str,
    pedagogical_context: Dict[str, Any],
    domain_knowledge: Dict[str, Any]
) -> tuple[List[str], List[str]]:
    """
    Validate pedagogical alignment of the blueprint.

    Checks:
    1. Tasks align with Bloom's level from pedagogical_context
    2. Labels match domain_knowledge.canonical_labels
    3. Task count appropriate for complexity
    4. Game mechanics support learning objectives

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    blooms_level = pedagogical_context.get("blooms_level", "").lower()
    subject = pedagogical_context.get("subject", "")
    difficulty = pedagogical_context.get("difficulty", "intermediate")
    learning_objectives = pedagogical_context.get("learning_objectives", [])
    canonical_labels = domain_knowledge.get("canonical_labels", []) or []

    tasks = blueprint.get("tasks", [])
    labels = blueprint.get("labels", [])

    # 1. Validate task alignment with Bloom's level
    blooms_task_counts = {
        "remember": (1, 3),      # Simple recall - 1-3 tasks
        "understand": (2, 4),    # Comprehension - 2-4 tasks
        "apply": (2, 5),         # Application - 2-5 tasks
        "analyze": (3, 6),       # Analysis - 3-6 tasks
        "evaluate": (3, 7),      # Evaluation - 3-7 tasks
        "create": (4, 10),       # Creation - 4-10 tasks (more complex)
    }

    if blooms_level in blooms_task_counts:
        min_tasks, max_tasks = blooms_task_counts[blooms_level]
        if len(tasks) < min_tasks:
            warnings.append(
                f"PEDAGOGICAL: For Bloom's '{blooms_level}' level, recommend at least {min_tasks} tasks "
                f"(current: {len(tasks)}). Consider adding more learning activities."
            )
        elif len(tasks) > max_tasks:
            warnings.append(
                f"PEDAGOGICAL: For Bloom's '{blooms_level}' level, {len(tasks)} tasks may overwhelm learners "
                f"(recommended: {min_tasks}-{max_tasks})."
            )

    # 2. Validate label alignment with canonical labels (for INTERACTIVE_DIAGRAM)
    if template_type == "INTERACTIVE_DIAGRAM" and canonical_labels:
        # Handle both dict labels and string labels
        label_texts = set()
        for lbl in labels:
            if isinstance(lbl, dict):
                text = (lbl.get("text") or "").strip().lower()
            elif isinstance(lbl, str):
                text = lbl.strip().lower()
            else:
                continue
            if text:
                label_texts.add(text)
        canonical_set = {cl.strip().lower() for cl in canonical_labels if isinstance(cl, str)}

        # Check for missing canonical labels
        # Note: When zones come from image detection (SAM/Gemini), not all canonical
        # structures may be visible/detectable in the generated image. Use warnings
        # for partial coverage rather than hard errors.
        missing_labels = canonical_set - label_texts
        label_coverage = len(label_texts) / len(canonical_set) if canonical_set else 1.0

        if missing_labels and label_coverage >= 0.5:
            # At least 50% coverage - warn about missing labels
            warnings.append(
                f"PEDAGOGICAL: {len(missing_labels)} canonical labels not included: {list(missing_labels)[:5]}. "
                f"Coverage: {label_coverage:.0%} ({len(label_texts)}/{len(canonical_set)})"
            )
        elif missing_labels and label_coverage >= 0.3:
            # 30-50% coverage - soft error, but allow retry
            warnings.append(
                f"PEDAGOGICAL: Low label coverage ({label_coverage:.0%}). "
                f"Missing {len(missing_labels)} labels: {list(missing_labels)[:5]}"
            )
        elif missing_labels:
            # Less than 30% coverage - this is problematic
            errors.append(
                f"PEDAGOGICAL: Very low label coverage ({label_coverage:.0%}). "
                f"Only {len(label_texts)} of {len(canonical_set)} canonical labels present. "
                f"FIX: Add more labels from: {list(missing_labels)[:5]}"
            )

        # Check for extra labels not in canonical list (might be hallucinated)
        extra_labels = label_texts - canonical_set
        if extra_labels:
            # Allow acceptable variants
            acceptable_variants = domain_knowledge.get("acceptable_variants", {}) or {}
            variant_set = set()
            for variants in acceptable_variants.values():
                if isinstance(variants, list):
                    variant_set.update(v.strip().lower() for v in variants if isinstance(v, str))

            truly_extra = extra_labels - variant_set - {"", "label", "part"}
            if truly_extra:
                warnings.append(
                    f"PEDAGOGICAL: Labels not in canonical list (may be hallucinated): {list(truly_extra)[:3]}. "
                    f"Verify these are correct terminology for {subject}."
                )

    # 3. Validate task complexity — always advanced thresholds
    complexity = {"max_steps": 10, "max_options": 10}

    # Check sequence steps
    if template_type == "SEQUENCE_BUILDER":
        steps = blueprint.get("steps", [])
        if len(steps) > complexity["max_steps"]:
            warnings.append(
                f"PEDAGOGICAL: {len(steps)} sequence steps may be too complex for '{difficulty}' difficulty "
                f"(recommended max: {complexity['max_steps']})"
            )

    # Check bucket sort items
    if template_type == "BUCKET_SORT":
        items = blueprint.get("items", [])
        if len(items) > complexity["max_options"] * 2:  # 2x because items go into multiple buckets
            warnings.append(
                f"PEDAGOGICAL: {len(items)} items may overwhelm '{difficulty}' level learners"
            )

    # 4. Validate game mechanics support learning objectives
    if learning_objectives:
        # Check if tasks actually address learning objectives
        task_texts = " ".join(
            (t.get("questionText") or "") + " " + (t.get("type") or "")
            for t in tasks if isinstance(t, dict)
        ).lower()

        keywords_found = 0
        for objective in learning_objectives:
            if isinstance(objective, str):
                # Extract key terms from objective
                key_terms = [word for word in objective.lower().split()
                            if len(word) > 4 and word not in {"should", "student", "learn", "understand", "about"}]
                if any(term in task_texts for term in key_terms[:3]):
                    keywords_found += 1

        if learning_objectives and keywords_found == 0:
            warnings.append(
                "PEDAGOGICAL: Tasks may not directly address stated learning objectives. "
                "Consider aligning task text with: " + ", ".join(learning_objectives[:2])
            )

    # 5. Template-specific pedagogical checks
    if template_type == "STATE_TRACER_CODE":
        steps = blueprint.get("steps", [])
        if blooms_level in ["remember", "understand"] and len(steps) > 5:
            warnings.append(
                f"PEDAGOGICAL: Code tracing with {len(steps)} steps is complex for "
                f"'{blooms_level}' level. Consider simplifying."
            )

    return errors, warnings


# =============================================================================
# MULTI-SCENE BLUEPRINT GENERATION (Preset 2)
# =============================================================================

async def _generate_multi_scene_blueprint(
    state: AgentState,
    question_text: str,
    question_options: list,
    ped_context: dict,
    template_selection: dict,
    game_plan: dict,
    scene_breakdown: list,
    scene_diagrams: Dict[int, Dict[str, Any]],
    scene_zones: Dict[int, List[Dict[str, Any]]],
    scene_labels: Dict[int, List[Dict[str, Any]]],
    domain_knowledge: dict,
    all_scene_data: Optional[Dict[int, Dict[str, Any]]] = None,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Generate a multi-scene GameSequence blueprint with multi-mechanic support.

    Creates a blueprint with multiple scenes, each having its own diagram,
    zones, labels, interaction modes, secondary modes, and mode transitions.

    This function now consumes:
    - entity_registry: Central registry from asset_generator_orchestrator with
      zones, assets, interactions, and per-scene mechanics
    - scene_breakdown: From game_plan with mechanics list
    - interaction_design: From interaction_designer with mode_transitions
    - game_plan.scene_transitions: Scene-to-scene transitions

    Args:
        state: Current agent state
        question_text: Original question
        question_options: Answer choices
        ped_context: Pedagogical context
        template_selection: Template selection info
        game_plan: Game plan data with scene_breakdown
        scene_breakdown: List of scene definitions from game_planner
        scene_diagrams: Per-scene diagram info
        scene_zones: Per-scene zone lists
        scene_labels: Per-scene label lists
        domain_knowledge: Domain knowledge
        ctx: Instrumentation context

    Returns:
        State update with multi-scene blueprint in game_sequence format
    """
    from uuid import uuid4
    from pathlib import Path

    question_id = state.get("question_id", "unknown")
    game_design = state.get("game_design", {})

    # Extract entity_registry from state (populated by asset_generator_orchestrator)
    entity_registry = state.get("entity_registry") or {}

    # Use all_scene_data from multi_scene_orchestrator (content per scene)
    all_scene_data = all_scene_data or state.get("all_scene_data") or {}
    if all_scene_data:
        logger.info(f"BlueprintGenerator: Using all_scene_data for {len(all_scene_data)} scenes")

    # Extract interaction_design from state (from interaction_designer agent)
    interaction_design = state.get("interaction_design") or {}

    # Extract progression type from scene_sequencer or game_design
    progression_type = state.get("scene_progression_type", "linear")

    # Get scene_transitions from game_plan or entity_registry
    game_plan_transitions = game_plan.get("scene_transitions", []) if game_plan else []
    registry_transitions = entity_registry.get("scene_transitions", []) if entity_registry else []
    scene_transitions_input = game_plan_transitions or registry_transitions

    # Get mode_transitions from interaction_design or entity_registry
    interaction_mode_transitions = interaction_design.get("mode_transitions", [])
    registry_mode_transitions = entity_registry.get("mode_transitions", [])

    # Get per-scene mechanics from entity_registry
    mechanics_per_scene = entity_registry.get("mechanics_per_scene", {}) if entity_registry else {}
    mechanic_configs = entity_registry.get("mechanic_configs", {}) if entity_registry else {}

    logger.info(
        "Building multi-scene blueprint",
        scene_count=len(scene_breakdown),
        has_entity_registry=bool(entity_registry),
        mechanics_per_scene=mechanics_per_scene,
        mode_transitions_count=len(interaction_mode_transitions) + len(registry_mode_transitions)
    )

    # Build scenes array
    scenes = []
    total_max_score = 0

    for scene_def in scene_breakdown:
        scene_number = scene_def.get("scene_number", len(scenes) + 1)
        scene_title = scene_def.get("title", f"Scene {scene_number}")
        scene_scope = scene_def.get("scope", scene_def.get("description", ""))
        focus_labels = scene_def.get("focus_labels", [])

        # Get per-scene data - priority: entity_registry > all_scene_data > scene_* dicts
        # From entity_registry (most authoritative - populated by asset_generator_orchestrator)
        registry_zone_ids = entity_registry.get("scene_zones", {}).get(scene_number, []) if entity_registry else []
        registry_zones = [
            entity_registry.get("zones", {}).get(zid)
            for zid in registry_zone_ids
            if entity_registry.get("zones", {}).get(zid)
        ] if entity_registry else []

        # Per-scene labels from entity_registry
        registry_labels = entity_registry.get("scene_labels", {}).get(scene_number, []) if entity_registry else []

        # Per-scene zone_groups from entity_registry (SAM3 hierarchical)
        scene_zone_groups = entity_registry.get("zone_groups", {}).get(scene_number, []) if entity_registry else []

        # Fall back to scene_zones/scene_labels dicts, then all_scene_data
        zones = registry_zones if registry_zones else scene_zones.get(scene_number, [])
        labels = registry_labels if registry_labels else scene_labels.get(scene_number, [])

        # If still no zones/labels, try all_scene_data from multi_scene_orchestrator
        scene_content = all_scene_data.get(scene_number, {}) if all_scene_data else {}
        if not zones and scene_content:
            scene_assets = scene_content.get("assets") or {}
            if isinstance(scene_assets, dict):
                zones = scene_assets.get("zones", [])
                if not labels:
                    labels = scene_assets.get("labels", [])

        # If still no labels, create from zones + focus_labels
        if not labels and zones and focus_labels:
            labels = _create_labels_from_focus(zones, focus_labels)

        # Get diagram info - priority: entity_registry > scene_diagrams dict > global diagram_image
        registry_diagram = entity_registry.get("scene_diagrams", {}).get(scene_number, {}) if entity_registry else {}
        diagram_info = registry_diagram if registry_diagram else scene_diagrams.get(scene_number, {})

        # Fallback: if no per-scene diagram, inherit from the global pipeline image
        if not diagram_info or not any(diagram_info.get(k) for k in ("local_path", "image_url", "generated_path")):
            global_diagram = state.get("diagram_image") or {}
            if isinstance(global_diagram, dict) and any(global_diagram.get(k) for k in ("local_path", "image_url", "generated_path")):
                diagram_info = global_diagram
                logger.info(
                    "Scene inheriting global diagram_image (no per-scene diagram)",
                    scene_number=scene_number,
                    diagram_keys=list(global_diagram.keys())
                )

        # Determine mechanics for this scene
        # Priority: scene_breakdown.mechanics > scene_breakdown.interaction_mode > mechanics_per_scene > game_design > default
        scene_mechanics_raw = scene_def.get("mechanics", [])

        if not scene_mechanics_raw:
            # Try from interaction_mode + secondary_modes (backward compat from game_planner)
            im = scene_def.get("interaction_mode")
            if im:
                scene_mechanics_raw = [{"type": im}]
                for sm in scene_def.get("secondary_modes", []):
                    scene_mechanics_raw.append({"type": sm})

        if not scene_mechanics_raw and mechanics_per_scene:
            # From entity_registry mechanics_per_scene
            per_scene = mechanics_per_scene.get(scene_number, [])
            if per_scene:
                scene_mechanics_raw = [{"type": m} if isinstance(m, str) else m for m in per_scene]

        if not scene_mechanics_raw and game_design:
            # From game_design
            designed_scenes = game_design.get("scenes", [])
            for ds in designed_scenes:
                if ds.get("scene") == scene_number:
                    scene_mechanics_raw = [{"type": ds.get("pattern") or ""}]
                    break

        if not scene_mechanics_raw:
            scene_mechanics_raw = []

        # Derive starting mode from mechanics[0]
        interaction_mode = (scene_mechanics_raw[0].get("type") or "") if isinstance(scene_mechanics_raw[0], dict) else str(scene_mechanics_raw[0]) if scene_mechanics_raw else ""

        # Build diagram URL - priority: entity_registry local_path > image_url > fallback
        diagram_local_path = diagram_info.get("local_path")
        diagram_image_url = diagram_info.get("image_url")
        generated_path = diagram_info.get("generated_path")

        if diagram_local_path:
            # Workflow saved a local file — serve through generic asset endpoint
            diagram_url = f"/api/assets/workflow/{Path(diagram_local_path).name}"
        elif diagram_image_url and diagram_image_url.startswith("http"):
            # Direct web URL from image retrieval
            diagram_url = diagram_image_url
        elif generated_path:
            diagram_url = f"/api/assets/{question_id}/scene_{scene_number}/diagram.png"
        else:
            # Fallback to main diagram
            diagram_url = f"/api/assets/{question_id}/generated/diagram.png"

        # Calculate scene score based on labels and mechanics complexity
        base_score = max(10 * len(labels), 20) if labels else 20
        # Add bonus for multi-mechanic scenes (beyond the first mechanic)
        mechanics_bonus = max(0, len(scene_mechanics_raw) - 1) * 5
        scene_score = base_score + mechanics_bonus
        total_max_score += scene_score

        # Get mode_transitions specific to this scene
        scene_mode_transitions = []
        for mt in (interaction_mode_transitions + registry_mode_transitions):
            if isinstance(mt, dict):
                # Check if this transition belongs to this scene
                mt_scene = mt.get("scene_number") or mt.get("scene")
                if mt_scene == scene_number or mt_scene is None:
                    scene_mode_transitions.append(mt)

        # Build scene mechanics array — flat list matching frontend Mechanic interface: { type, config? }
        scene_mechanics = []
        for mech in scene_mechanics_raw:
            m_type = (mech.get("type") or "") if isinstance(mech, dict) else str(mech)
            m_config = mech.get("config") if isinstance(mech, dict) else None
            # Merge config from mechanic_configs registry if available
            registry_config = mechanic_configs.get(m_type, {})
            merged_config = {**registry_config, **(m_config or {})} if (registry_config or m_config) else None
            entry = {"type": m_type}
            if merged_config:
                entry["config"] = merged_config
            scene_mechanics.append(entry)

        # Normalize zones and labels for blueprint format
        normalized_zones = normalize_zones(zones) if zones else []
        normalized_labels = labels if labels else []
        if not normalized_labels and normalized_zones:
            normalized_labels = create_labels_from_zones(normalized_zones)

        # Build scene tasks from game_plan tasks (SceneTask format)
        scene_task_defs = scene_def.get("tasks", [])
        blueprint_tasks = []
        if scene_task_defs:
            for task_def in scene_task_defs:
                if not isinstance(task_def, dict):
                    continue
                task_focus = task_def.get("focus_labels", [])
                # Map focus_labels to zone_ids (fuzzy match)
                task_zone_ids = (
                    [z["id"] for z in normalized_zones if _label_matches_focus(z.get("label", ""), task_focus)]
                    if task_focus else [z["id"] for z in normalized_zones]
                )
                # Map focus_labels to label_ids
                task_label_ids = (
                    [l["id"] for l in normalized_labels if _label_matches_focus(l.get("text", ""), task_focus)]
                    if task_focus else [l["id"] for l in normalized_labels]
                )
                blueprint_tasks.append({
                    "task_id": task_def.get("task_id", f"task_{len(blueprint_tasks) + 1}"),
                    "title": task_def.get("title", ""),
                    "mechanic_type": task_def.get("mechanic") or "",
                    "zone_ids": task_zone_ids,
                    "label_ids": task_label_ids,
                    "instructions": task_def.get("description"),
                    "scoring_weight": float(task_def.get("scoring_weight", 1.0)),
                    "config": task_def.get("config"),
                })

        # Build scene
        scene = {
            "scene_id": f"scene_{scene_number}_{uuid4().hex[:8]}",
            "scene_number": scene_number,
            "title": scene_title,
            "scope": scene_scope,
            "focus_labels": focus_labels,
            "diagram": {
                "assetUrl": diagram_url,
                "assetPrompt": scene_scope or scene_title,
            },
            "zones": normalized_zones,
            "labels": normalized_labels,
            "zoneGroups": scene_zone_groups if scene_zone_groups else [],
            "mechanics": scene_mechanics,
            "interaction_mode": interaction_mode,  # Convenience shorthand (derived from mechanics[0].type)
            "mode_transitions": scene_mode_transitions,
            "max_score": scene_score,
            "tasks": blueprint_tasks if blueprint_tasks else [],  # SceneTask format
            "animationCues": {
                "correctPlacement": "Zone glows green and label snaps into position",
                "incorrectPlacement": "Zone flashes red briefly",
                "modeTransition": "Smooth transition to next interaction mode"
            }
        }

        # Add prerequisite for non-first scenes
        if scene_number > 1:
            scene["prerequisite_scene"] = f"scene_{scene_number - 1}"

        scenes.append(scene)

    # Build scene_transitions for game_sequence
    scene_transitions = []
    if scene_transitions_input:
        # Use provided transitions
        for tr in scene_transitions_input:
            if isinstance(tr, dict):
                scene_transitions.append({
                    "from_scene": tr.get("from_scene") or tr.get("from"),
                    "to_scene": tr.get("to_scene") or tr.get("to"),
                    "trigger": tr.get("trigger", "mode_sequence_complete"),
                    "condition": tr.get("condition"),
                    "animation": tr.get("animation", "fade")
                })
    else:
        # Generate default linear transitions
        for i in range(len(scenes) - 1):
            scene_transitions.append({
                "from_scene": i + 1,
                "to_scene": i + 2,
                "trigger": "mode_sequence_complete",
                "animation": "fade"
            })

    # Build the multi-scene blueprint (GameSequence format)
    # Uses snake_case for is_multi_scene to match frontend TypeScript types
    sequence_id = f"seq_{question_id}_{uuid4().hex[:8]}"

    blueprint = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "is_multi_scene": True,  # snake_case for frontend compatibility
        # Wrap scenes in game_sequence object to match MultiSceneInteractiveDiagramBlueprint type
        "game_sequence": {
            "sequence_id": sequence_id,
            "sequence_title": _generate_sequence_title(question_text, len(scenes)),
            "total_scenes": len(scenes),
            "progression_type": progression_type,
            "scenes": scenes,
            "scene_transitions": scene_transitions,
            "total_max_score": total_max_score,
            "allow_scene_skip": False,
            "allow_revisit": True,
        },
        # Top-level metadata
        "title": _generate_sequence_title(question_text, len(scenes)),
        "narrativeIntro": _generate_sequence_intro(question_text, scenes),
        "animations": {
            "sceneTransition": "Smooth fade to next scene",
            "sequenceComplete": "Celebration animation with score display",
            "modeTransition": "Subtle transition between interaction modes"
        },
        # Include first scene's diagram for backward compatibility with single-scene consumers
        "diagram": scenes[0]["diagram"] if scenes else {},
        "labels": scenes[0]["labels"] if scenes else [],
        "zones": scenes[0].get("zones", []) if scenes else [],
        "zoneGroups": scenes[0].get("zoneGroups", []) if scenes else [],
        # Backward compat: first scene's interaction mode
        "interactionMode": (scenes[0].get("interaction_mode") or "") if scenes else "",
        "tasks": [
            {
                "id": "task_complete_sequence",
                "type": "sequence_completion",
                "questionText": f"Complete all {len(scenes)} scenes to finish the activity",
                "requiredToProceed": True
            }
        ]
    }

    logger.info(
        f"Generated multi-scene blueprint with {len(scenes)} scenes",
        total_zones=sum(len(s.get("zones", [])) for s in scenes),
        total_mechanics=sum(len(s.get("mechanics", [])) for s in scenes),
        scene_transitions=len(scene_transitions),
        progression_type=progression_type
    )

    if ctx:
        ctx.complete({"blueprint": blueprint})

    return {
        "blueprint": blueprint,
        "current_agent": "blueprint_generator",
        "current_validation_errors": []
    }


def _map_interaction_to_task_type(interaction_mode: str) -> str:
    """Map interaction mode to task type."""
    mode_to_task = {
        "drag_drop": "interactive_diagram",
        "click_to_identify": "identify_parts",
        "trace_path": "trace_path",
        "hierarchical": "hierarchical_labeling",
        "description_matching": "match_descriptions",
        "sequencing": "sequence_order",
        "compare_contrast": "compare_structures",
    }
    return mode_to_task.get(interaction_mode, "interactive_diagram")


def _generate_scene_task_text(scene_title: str, interaction_mode: str) -> str:
    """Generate task text for a scene based on its mode."""
    mode_templates = {
        "drag_drop": f"Drag the labels to the correct positions in: {scene_title}",
        "click_to_identify": f"Click on each part to identify it in: {scene_title}",
        "trace_path": f"Trace the path through: {scene_title}",
        "hierarchical": f"Label all parts and sub-parts in: {scene_title}",
        "description_matching": f"Match the descriptions to the correct parts in: {scene_title}",
        "sequencing": f"Arrange the elements in the correct order for: {scene_title}",
        "compare_contrast": f"Identify similarities and differences in: {scene_title}",
    }
    return mode_templates.get(interaction_mode, f"Complete the activity: {scene_title}")


def _label_matches_focus(label_text: str, focus_labels: List[str]) -> bool:
    """Check if a label text matches any of the focus labels (case-insensitive substring)."""
    if not focus_labels:
        return True
    label_lower = label_text.lower()
    return any(fl.lower() in label_lower or label_lower in fl.lower() for fl in focus_labels)


def _create_labels_from_focus(zones: list, focus_labels: list) -> list:
    """Create label entries from zones and focus_labels when no labels are available."""
    labels = []
    for i, label_text in enumerate(focus_labels):
        label_id = f"label_{i+1}"
        # Try to match zone by label text
        matched_zone = None
        for zone in zones:
            zone_label = zone.get("label", "").lower()
            if zone_label == label_text.lower() or label_text.lower() in zone_label:
                matched_zone = zone
                break
        labels.append({
            "id": label_id,
            "text": label_text,
            "zoneId": matched_zone.get("id") if matched_zone else f"zone_{i+1}",
        })
    return labels


def _generate_sequence_title(question_text: str, num_scenes: int) -> str:
    """Generate a title for the sequence."""
    # Extract key topic from question
    words = question_text.split()[:8]
    topic = " ".join(words)
    if len(question_text) > len(topic):
        topic += "..."
    return f"Interactive Exploration: {topic}"


def _generate_sequence_intro(question_text: str, scenes: list) -> str:
    """Generate narrative intro for the sequence."""
    scene_names = [s.get("title", f"Scene {i+1}") for i, s in enumerate(scenes[:3])]
    scenes_text = ", ".join(scene_names)
    if len(scenes) > 3:
        scenes_text += f", and {len(scenes) - 3} more"

    return (
        f"Explore this topic through {len(scenes)} interactive scenes: {scenes_text}. "
        f"Complete each scene to unlock the next and build your understanding step by step."
    )
