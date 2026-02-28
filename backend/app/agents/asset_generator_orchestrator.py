"""
Asset Generator Orchestrator Agent (WORKFLOW EXECUTOR)

This agent serves two modes:
1. WORKFLOW MODE: Executes workflows based on workflow_execution_plan from asset_planner
2. LEGACY MODE: Executes SEQUENTIAL asset generation based on planned assets

Workflow mode is the new approach that generates structured outputs (zones, paths, etc.)
for specific game mechanics. Legacy mode is maintained for backward compatibility.

NOTE: This agent runs BEFORE blueprint_generator. It does NOT need blueprint.

Inputs: planned_assets, workflow_execution_plan (optional)
Outputs: generated_assets, asset_generation_metrics, entity_registry (workflow mode)
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.workflows import (
    WorkflowRegistry,
    WorkflowContext,
    WorkflowResult,
    create_failed_result,
)
from app.services.media_generation_service import (
    get_media_service,
    PlannedAsset,
    GeneratedAsset,
    AssetType,
    GenerationMethod,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.asset_generator_orchestrator")


# =============================================================================
# WORKFLOW EXECUTION MODE
# =============================================================================

def _initialize_entity_registry() -> Dict[str, Any]:
    """Initialize an empty entity registry for tracking generated entities."""
    return {
        # EntityRegistry keys (from state.py EntityRegistry TypedDict)
        "zones": {},
        "assets": {},                # asset_id → asset data
        "interactions": {},          # interaction_id → interaction data
        "zone_assets": {},           # zone_id → [asset_ids]
        "zone_interactions": {},     # zone_id → [interaction_ids]
        "asset_zones": {},           # asset_id → [zone_ids] (reverse lookup)
        "scene_zones": {},           # scene_number → list of zone IDs in that scene
        # Orchestrator workflow-specific keys
        "labels": {},
        "paths": {},
        "sequences": {},
        "sorting_categories": {},
        "memory_pairs": {},
        "branching_nodes": {},
        "zone_groups": {},           # scene_number → list of zone group defs
        "scene_labels": {},          # scene_number → list of label dicts in that scene
        "scene_diagrams": {},        # scene_number → diagram info (URL, local_path)
        "metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
    }


def _merge_to_entity_registry(registry: Dict[str, Any], result: WorkflowResult) -> Dict[str, Any]:
    """Merge workflow result into entity registry based on output type."""
    if not result.success:
        return registry

    output_type = result.output_type
    data = result.data
    scene_number = result.scene_number

    if output_type == "diagram":
        # Merge diagram zones
        zones = data.get("diagram_zones", [])
        scene_zone_ids = []
        for zone in zones:
            zone_id = zone.get("id")
            if zone_id:
                registry["zones"][zone_id] = zone
                scene_zone_ids.append(zone_id)

        # Track which zones belong to which scene
        if scene_number is not None and scene_zone_ids:
            registry.setdefault("scene_zones", {})[scene_number] = scene_zone_ids

        # Merge labels if present
        labels = data.get("diagram_labels", data.get("labels", []))
        scene_labels = []
        for label in labels:
            label_id = label.get("id")
            if label_id:
                registry["labels"][label_id] = label
                scene_labels.append(label)

        # Track per-scene labels
        if scene_number is not None and scene_labels:
            registry.setdefault("scene_labels", {})[scene_number] = scene_labels

        # Merge zone_groups (from SAM3 hierarchical detection)
        zone_groups = data.get("zone_groups", [])
        if zone_groups and scene_number is not None:
            registry.setdefault("zone_groups", {})[scene_number] = zone_groups

        # Track per-scene diagram info (image URL/path)
        diagram_image = data.get("diagram_image")
        diagram_image_local = data.get("diagram_image_local")
        if scene_number is not None and (diagram_image or diagram_image_local):
            registry.setdefault("scene_diagrams", {})[scene_number] = {
                "image_url": diagram_image,
                "local_path": diagram_image_local,
                "source": data.get("image_source", "unknown"),
            }

    elif output_type == "paths":
        # Merge trace paths
        paths = data.get("paths", [])
        for path in paths:
            path_id = path.get("id")
            if path_id:
                registry["paths"][path_id] = path
                # Also add as interaction for game mechanics
                registry["interactions"][path_id] = {
                    "id": path_id,
                    "type": "trace_path",
                    **path
                }

    elif output_type == "sequence":
        # Merge sequence items
        sequences = data.get("sequences", data.get("items", []))
        for seq in sequences:
            seq_id = seq.get("id")
            if seq_id:
                registry["sequences"][seq_id] = seq

    elif output_type == "sorting":
        # Merge sorting categories and items
        categories = data.get("categories", [])
        for cat in categories:
            cat_id = cat.get("id")
            if cat_id:
                registry["sorting_categories"][cat_id] = cat

    elif output_type == "memory":
        # Merge memory pairs
        pairs = data.get("pairs", [])
        for pair in pairs:
            pair_id = pair.get("id")
            if pair_id:
                registry["memory_pairs"][pair_id] = pair

    elif output_type == "branching":
        # Merge branching nodes
        nodes = data.get("nodes", [])
        for node in nodes:
            node_id = node.get("id")
            if node_id:
                registry["branching_nodes"][node_id] = node

    # Update registry metadata
    registry["metadata"]["last_updated"] = datetime.utcnow().isoformat()
    registry["metadata"]["workflow_count"] = registry["metadata"].get("workflow_count", 0) + 1

    return registry


async def _execute_workflows(
    state: AgentState,
    workflow_execution_plan: List[Dict[str, Any]],
    ctx: Optional[InstrumentedAgentContext]
) -> Dict[str, Any]:
    """
    Execute workflows in dependency order based on the execution plan.

    Args:
        state: Current agent state
        workflow_execution_plan: List of workflow steps to execute
        ctx: Instrumentation context

    Returns:
        Dict with generated_assets, entity_registry, and metrics
    """
    import time

    start_time = time.time()

    # Extract context from state
    domain_knowledge = state.get("domain_knowledge", {})
    planned_assets = state.get("planned_assets", [])
    asset_specs = {a.get("id", f"asset_{i}"): a for i, a in enumerate(planned_assets)}

    # Initialize tracking structures
    generated_assets: Dict[str, WorkflowResult] = {}
    existing_registry = state.get("entity_registry")
    if existing_registry:
        # Merge default keys into existing registry (asset_planner may not include
        # workflow-specific keys like 'labels', 'paths', 'sequences', etc.)
        defaults = _initialize_entity_registry()
        for key, value in defaults.items():
            existing_registry.setdefault(key, value)
        entity_registry = existing_registry
    else:
        entity_registry = _initialize_entity_registry()
    workflow_metrics: List[Dict[str, Any]] = []

    logger.info(f"Executing {len(workflow_execution_plan)} workflows in dependency order")

    for step_idx, step in enumerate(workflow_execution_plan):
        workflow_name = step.get("workflow")
        asset_id = step.get("asset_id", f"workflow_{step_idx}")
        scene_num = step.get("scene", 1)
        dependencies_list = step.get("dependencies", [])

        step_start = time.time()
        logger.info(f"[{step_idx + 1}/{len(workflow_execution_plan)}] Executing workflow: {workflow_name} for asset: {asset_id}")

        # Get workflow function from registry
        workflow_fn = WorkflowRegistry.get(workflow_name)

        if not workflow_fn:
            logger.warning(f"Unknown workflow: {workflow_name}, skipping")
            result = create_failed_result(
                workflow_name=workflow_name,
                asset_id=asset_id,
                scene_number=scene_num,
                output_type="unknown",
                error=f"Unknown workflow: {workflow_name}"
            )
            generated_assets[asset_id] = result
            workflow_metrics.append({
                "workflow": workflow_name,
                "asset_id": asset_id,
                "success": False,
                "error": f"Unknown workflow: {workflow_name}",
                "duration_ms": 0
            })
            continue

        # Gather dependencies from previously executed workflows
        dependencies: Dict[str, WorkflowResult] = {}
        for dep_id in dependencies_list:
            if dep_id in generated_assets:
                dependencies[dep_id] = generated_assets[dep_id]
            else:
                logger.warning(f"Dependency {dep_id} not found for workflow {workflow_name}")

        # Get asset spec (from planned assets or from the step itself)
        asset_spec = asset_specs.get(asset_id, step)

        # Create workflow context
        context = WorkflowContext(
            asset_spec=asset_spec,
            domain_knowledge=domain_knowledge,
            dependencies=dependencies,
            scene_number=scene_num,
            instrumentation_ctx=ctx,
            state=state
        )

        # Execute the workflow
        try:
            result = await workflow_fn(context)
            generated_assets[asset_id] = result

            # Merge result into entity registry
            entity_registry = _merge_to_entity_registry(entity_registry, result)

            step_duration = int((time.time() - step_start) * 1000)
            logger.info(f"Workflow {workflow_name} completed: success={result.success}, duration={step_duration}ms")

            workflow_metrics.append({
                "workflow": workflow_name,
                "asset_id": asset_id,
                "success": result.success,
                "output_type": result.output_type,
                "duration_ms": step_duration,
                "error": result.error
            })

        except Exception as e:
            logger.error(f"Workflow {workflow_name} failed with exception: {e}")
            result = create_failed_result(
                workflow_name=workflow_name,
                asset_id=asset_id,
                scene_number=scene_num,
                output_type="error",
                error=str(e)
            )
            generated_assets[asset_id] = result

            step_duration = int((time.time() - step_start) * 1000)
            workflow_metrics.append({
                "workflow": workflow_name,
                "asset_id": asset_id,
                "success": False,
                "error": str(e),
                "duration_ms": step_duration
            })

    # Calculate overall metrics
    total_duration_ms = int((time.time() - start_time) * 1000)
    successes = sum(1 for r in generated_assets.values() if r.success)
    failures = len(generated_assets) - successes

    logger.info(
        f"Workflow execution complete: {successes}/{len(generated_assets)} succeeded "
        f"({failures} failed) in {total_duration_ms}ms"
    )

    # Track metrics in instrumentation context
    if ctx:
        if failures > 0:
            ctx.set_fallback_used(f"{failures} workflows failed")

        ctx.set_tool_metrics([{
            "name": "workflow_execution",
            "arguments": {"total_workflows": len(workflow_execution_plan)},
            "result": {"successful": successes, "failed": failures},
            "status": "success" if failures == 0 else "partial" if successes > 0 else "error",
            "latency_ms": total_duration_ms,
        }])

    # Serialize workflow results for state
    generated_assets_serialized = {
        asset_id: result.to_dict()
        for asset_id, result in generated_assets.items()
    }

    # Build generation metrics
    generation_metrics = {
        "mode": "workflow",
        "total_workflows": len(workflow_execution_plan),
        "successful": successes,
        "failed": failures,
        "total_duration_ms": total_duration_ms,
        "workflows": workflow_metrics
    }

    # Extract diagram_zones and diagram_image from entity_registry for
    # backward compatibility with blueprint_generator (reads state.get("diagram_zones"))
    result = {
        "generated_assets": generated_assets_serialized,
        "entity_registry": entity_registry,
        "asset_generation_metrics": generation_metrics
    }

    # Flatten entity_registry zones to state-level diagram_zones (for single-scene blueprints)
    all_zones = list(entity_registry.get("zones", {}).values())
    if all_zones:
        result["diagram_zones"] = all_zones
        logger.info(f"Set diagram_zones from entity_registry: {len(all_zones)} zones")

    # Flatten zone_groups to state-level zone_groups
    all_zone_groups = []
    zone_groups_by_scene = entity_registry.get("zone_groups", {})
    if zone_groups_by_scene:
        for scene_groups in zone_groups_by_scene.values():
            if isinstance(scene_groups, list):
                all_zone_groups.extend(scene_groups)
        if all_zone_groups:
            result["zone_groups"] = all_zone_groups
            logger.info(f"Set zone_groups from entity_registry: {len(all_zone_groups)} groups")

    # Flatten scene_diagrams to state-level diagram_image
    scene_diagrams = entity_registry.get("scene_diagrams", {})
    if scene_diagrams:
        # Use first scene's diagram
        first_scene = next(iter(scene_diagrams.values()), {})
        if first_scene.get("image_url"):
            result["diagram_image"] = first_scene["image_url"]
        if first_scene.get("local_path"):
            result["generated_diagram_path"] = first_scene["local_path"]

    return result


# =============================================================================
# LEGACY ASSET GENERATION MODE
# =============================================================================

def _reconstruct_planned_asset(asset_dict: Dict[str, Any]) -> PlannedAsset:
    """Reconstruct a PlannedAsset from a dictionary.

    Args:
        asset_dict: Dictionary representation of a PlannedAsset.

    Returns:
        PlannedAsset object.
    """
    # Map string types to enums
    type_mapping = {
        "image": AssetType.IMAGE,
        "gif": AssetType.GIF,
        "video": AssetType.VIDEO,
        "sprite": AssetType.SPRITE,
        "css_animation": AssetType.CSS_ANIMATION,
    }

    # All supported generation methods
    method_mapping = {
        "nanobanana": GenerationMethod.NANOBANANA,
        "dalle": GenerationMethod.DALLE,
        "stable_diffusion": GenerationMethod.STABLE_DIFFUSION,
        "gemini_imagen": GenerationMethod.GEMINI_IMAGEN,  # Deprecated
        "css_animation": GenerationMethod.CSS_ANIMATION,
        "cached": GenerationMethod.CACHED,
        "fetch_url": GenerationMethod.FETCH_URL,
    }

    return PlannedAsset(
        id=asset_dict.get("id", "unknown"),
        type=type_mapping.get(asset_dict.get("type", "image"), AssetType.IMAGE),
        generation_method=method_mapping.get(
            asset_dict.get("generation_method", "cached"),
            GenerationMethod.CACHED
        ),
        prompt=asset_dict.get("prompt"),
        url=asset_dict.get("url"),
        local_path=asset_dict.get("local_path"),  # Pass through existing local file path
        dimensions=asset_dict.get("dimensions"),
        priority=asset_dict.get("priority", 2),
        placement=asset_dict.get("placement", "overlay"),
        zone_id=asset_dict.get("zone_id"),
        layer=asset_dict.get("layer", 0),
        style=asset_dict.get("style"),
        keyframes=asset_dict.get("keyframes"),
    )


def _serialize_generated_asset(asset: GeneratedAsset) -> Dict[str, Any]:
    """Serialize a GeneratedAsset to a dictionary.

    Args:
        asset: GeneratedAsset object.

    Returns:
        Dictionary representation.
    """
    return {
        "id": asset.id,
        "type": asset.type.value,
        "url": asset.url,
        "local_path": asset.local_path,
        "css_content": asset.css_content,
        "keyframes": asset.keyframes,
        "metadata": asset.metadata,
        "success": asset.success,
        "error": asset.error,
    }


async def _generate_with_fallback(
    media_service,
    planned: PlannedAsset,
    fallback_methods: List[GenerationMethod]
) -> GeneratedAsset:
    """Try to generate an asset with fallback methods.

    Args:
        media_service: The media generation service.
        planned: The planned asset.
        fallback_methods: List of fallback methods to try.

    Returns:
        GeneratedAsset result.
    """
    # Try primary method first
    result = await media_service.generate_asset(planned)

    if result.success:
        return result

    # Try fallback methods
    for method in fallback_methods:
        if method == planned.generation_method:
            continue

        logger.info(f"Trying fallback method {method.value} for asset {planned.id}")

        fallback_planned = PlannedAsset(
            id=planned.id,
            type=planned.type,
            generation_method=method,
            prompt=planned.prompt,
            url=planned.url,
            local_path=planned.local_path,  # Pass through existing local file path
            dimensions=planned.dimensions,
            priority=planned.priority,
            placement=planned.placement,
            zone_id=planned.zone_id,
            layer=planned.layer,
            style=planned.style,
        )

        result = await media_service.generate_asset(fallback_planned)

        if result.success:
            logger.info(f"Fallback {method.value} succeeded for asset {planned.id}")
            return result

    return result


async def _generate_single_asset_with_retry(
    media_service,
    planned: PlannedAsset,
    fallback_methods: List[GenerationMethod],
    max_retries: int = 3,
    base_delay: float = 1.0
) -> Tuple[GeneratedAsset, Dict[str, Any]]:
    """Generate a single asset with exponential backoff retry.

    Args:
        media_service: The media generation service.
        planned: The planned asset.
        fallback_methods: List of fallback methods to try.
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        Tuple of (GeneratedAsset, metrics dict)
    """
    import time

    metrics = {
        "asset_id": planned.id,
        "attempts": 0,
        "fallbacks_tried": [],
        "final_method": planned.generation_method.value,
        "success": False,
        "duration_ms": 0,
    }

    start_time = time.time()

    for attempt in range(max_retries):
        metrics["attempts"] = attempt + 1

        try:
            result = await _generate_with_fallback(media_service, planned, fallback_methods)

            if result.success:
                metrics["success"] = True
                metrics["duration_ms"] = int((time.time() - start_time) * 1000)
                return result, metrics

            # If failed, log and retry with backoff
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed for asset {planned.id}: {result.error}"
            )

        except Exception as e:
            logger.error(f"Exception during asset generation attempt {attempt + 1}: {str(e)}")

        # Exponential backoff before retry
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)
            logger.info(f"Retrying asset {planned.id} in {delay:.1f}s...")
            await asyncio.sleep(delay)

    # All retries exhausted
    metrics["duration_ms"] = int((time.time() - start_time) * 1000)

    # Return the last result (failure)
    return GeneratedAsset(
        id=planned.id,
        type=planned.type,
        success=False,
        error=f"Failed after {max_retries} attempts"
    ), metrics


async def asset_generator_orchestrator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    WORKFLOW EXECUTOR - Executes workflows based on workflow_execution_plan.
    Falls back to legacy asset generation if no workflow plan exists.

    This agent serves as the central executor for two modes:

    1. WORKFLOW MODE (new):
       - Triggered when workflow_execution_plan exists in state
       - Executes workflows in dependency order
       - Produces structured outputs (zones, paths, interactions, etc.)
       - Maintains an entity_registry for cross-workflow references

    2. LEGACY MODE (backward compatible):
       - Triggered when no workflow_execution_plan exists
       - Executes SEQUENTIAL asset generation based on planned_assets
       - Each asset is processed one at a time with exponential backoff retry

    NOTE: This agent runs BEFORE blueprint_generator. It does NOT need blueprint.

    Inputs:
        - planned_assets: List of asset specifications
        - workflow_execution_plan (optional): List of workflow steps to execute

    Outputs:
        - generated_assets: Dict or List of generated asset results
        - asset_generation_metrics: Generation statistics
        - entity_registry (workflow mode only): Registry of all generated entities
    """
    # Skip guard: if generated_assets already populated, pass through
    # (prevents re-execution on blueprint retries)
    existing_assets = state.get("generated_assets")
    if existing_assets and len(existing_assets) > 0:
        logger.info(
            f"Skipping asset generation — {len(existing_assets)} assets already generated"
        )
        result = {
            "generated_assets": existing_assets,
            "entity_registry": state.get("entity_registry"),
            "asset_generation_metrics": state.get("asset_generation_metrics", {}),
        }
        # Preserve flattened diagram fields (only set non-None values)
        for key in ("diagram_zones", "zone_groups", "diagram_image", "generated_diagram_path"):
            val = state.get(key)
            if val is not None:
                result[key] = val
        return result

    # Check for new workflow execution mode
    workflow_execution_plan = state.get("workflow_execution_plan", [])

    if workflow_execution_plan:
        logger.info(f"Workflow mode: Found {len(workflow_execution_plan)} workflows to execute")
        return await _execute_workflows(state, workflow_execution_plan, ctx)

    # LEGACY MODE: Original sequential asset generation
    logger.info("Legacy mode: Using sequential asset generation")
    planned_assets_raw = state.get("planned_assets", [])

    if not planned_assets_raw:
        logger.info("No planned assets to generate")
        return {"generated_assets": [], "asset_generation_metrics": {}}

    logger.info(f"Generating {len(planned_assets_raw)} planned assets SEQUENTIALLY")

    # Reconstruct PlannedAsset objects
    planned_assets = [_reconstruct_planned_asset(a) for a in planned_assets_raw]

    # Sort by priority (lower = higher priority)
    planned_assets.sort(key=lambda a: a.priority)

    # Get media service
    media_service = get_media_service()

    # Define fallback chains for each generation method
    fallback_chains = {
        GenerationMethod.NANOBANANA: [GenerationMethod.CACHED],
        GenerationMethod.CSS_ANIMATION: [],
        GenerationMethod.CACHED: [],
        GenerationMethod.FETCH_URL: [GenerationMethod.CACHED],
    }

    # Generate assets SEQUENTIALLY to avoid rate limits
    all_results: List[GeneratedAsset] = []
    all_metrics: List[Dict[str, Any]] = []

    for i, planned in enumerate(planned_assets):
        logger.info(f"Processing asset {i + 1}/{len(planned_assets)}: {planned.id} ({planned.generation_method.value})")

        fallback_methods = fallback_chains.get(planned.generation_method, [])

        # Generate with retry
        result, metrics = await _generate_single_asset_with_retry(
            media_service,
            planned,
            fallback_methods,
            max_retries=3,
            base_delay=1.0
        )

        all_results.append(result)
        all_metrics.append(metrics)

        # Small delay between assets to be nice to APIs
        if i < len(planned_assets) - 1:
            await asyncio.sleep(0.5)

    # Count successes and failures
    successes = sum(1 for r in all_results if r.success)
    failures = sum(1 for r in all_results if not r.success)
    total_duration_ms = sum(
        m.get("duration_ms", 0) if isinstance(m, dict) else 0
        for m in all_metrics
    )

    logger.info(
        f"Asset generation complete: {successes}/{len(all_results)} succeeded "
        f"({failures} failed) in {total_duration_ms}ms"
    )

    # Log any failures
    for result in all_results:
        if not result.success:
            logger.warning(f"Failed to generate asset {result.id}: {result.error}")

    # Track metrics if context available
    if ctx:
        if failures > 0:
            ctx.set_fallback_used(f"{failures} assets failed to generate")

        # Track asset generation as tool metrics
        # Count AI-generated images (Gemini Imagen) for cost estimation
        ai_images = sum(1 for m in all_metrics if m.get("final_method") == "gemini_imagen" and m.get("success"))
        ctx.set_tool_metrics([{
            "name": "asset_generation",
            "arguments": {"total_assets": len(all_results)},
            "result": {"successful": successes, "failed": failures},
            "status": "success" if failures == 0 else "error",
            "latency_ms": total_duration_ms,
            "api_calls": ai_images,
            "estimated_cost_usd": ai_images * 0.02,  # ~$0.02 per Gemini Imagen image
        }])

    # Serialize results for state as Dict keyed by asset_id (matches workflow mode output)
    generated_assets_dict = {
        r.id: _serialize_generated_asset(r) for r in all_results
    }

    # Aggregate metrics
    generation_metrics = {
        "mode": "legacy",
        "total_assets": len(all_results),
        "successful": successes,
        "failed": failures,
        "total_duration_ms": total_duration_ms,
        "assets": all_metrics,
    }

    return {
        "generated_assets": generated_assets_dict,
        "asset_generation_metrics": generation_metrics,
    }
