"""
Asset Planner Agent - WORKFLOW ROUTER

Maps asset requirements from game_plan to execution workflows.
Determines what assets need to be generated and assigns workflows based on
mechanic types and dependencies.

NOTE: This agent runs BEFORE blueprint_generator in the pipeline.
It does NOT depend on blueprint data - only game_plan and zones.

The WORKFLOW ROUTER:
1. Reads asset_needs from game_plan.scene_breakdown
2. Maps asset_needs to workflows using MECHANIC_TO_WORKFLOW
3. Generates workflow_execution_plan with dependency ordering (topological sort)
4. Outputs planned_assets with workflow assignments

Uses the asset_capabilities manifest to reason about optimal generation
strategies based on asset type, latency constraints, and practical limits.

Inputs:
    - game_plan: ExtendedGamePlan with scene_breakdown and asset_needs
    - scene_structure: Scene layout from scene_stage1 (regions, visual theme) [legacy]
    - scene_assets: Asset definitions from scene_stage2 [legacy]
    - scene_interactions: Interaction definitions from scene_stage3 [legacy]
    - scene_data: Combined scene data (legacy compatibility)
    - generated_diagram_path: Path to generated diagram image (if any)
    - diagram_zones: Zone definitions from gemini_zone_detector
    - entity_registry: Phase 3 entity registry

Outputs:
    - planned_assets: List of asset specs with workflow assignments
    - workflow_execution_plan: Ordered list of workflow steps (topologically sorted)
    - entity_registry: Updated with assets
"""

from typing import Any, Dict, List, Optional

from app.agents.state import (
    AgentState,
    AssetEntity,
    EntityRegistry,
    ZoneEntity,
    create_empty_entity_registry,
)
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.media_generation_service import (
    PlannedAsset,
    AssetType,
    GenerationMethod,
)
# Import asset capabilities for intelligent method selection
from app.config.asset_capabilities import (
    GENERATION_METHODS as CAPABILITY_METHODS,
    ASSET_TYPES as CAPABILITY_ASSET_TYPES,
    PRACTICAL_LIMITS,
    get_methods_for_asset_type,
    get_available_methods,
    format_capabilities_for_prompt,
    GenerationStatus,
    LatencyCategory,
)
# Import workflow types for mechanic-to-workflow mapping
from app.agents.workflows.types import (
    MECHANIC_TO_WORKFLOW,
    WORKFLOW_CAPABILITIES,
    WorkflowExecutionStep,
    AssetSpec,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.asset_planner")


def _determine_generation_method(
    asset_spec: Dict[str, Any],
    available_methods: List[str],
    ai_images_generated: int = 0
) -> GenerationMethod:
    """Determine the best generation method for an asset.

    Uses asset_capabilities manifest to reason about optimal method selection.
    Considers: asset type, available methods, latency, and practical constraints.

    Args:
        asset_spec: Asset specification from blueprint.
        available_methods: List of available generation methods.
        ai_images_generated: Number of AI images already generated in this game.

    Returns:
        The best generation method to use.
    """
    # Quick paths for already-available assets
    if asset_spec.get("url"):
        return GenerationMethod.CACHED

    if asset_spec.get("local_path"):
        return GenerationMethod.CACHED

    if asset_spec.get("source") == "generated":
        return GenerationMethod.CACHED

    # Get asset type for capability-aware selection
    asset_type_str = asset_spec.get("type", "image")

    # CSS animations always use CSS generator
    if asset_type_str == "css_animation":
        return GenerationMethod.CSS_ANIMATION

    # Check practical limits for AI generation
    max_ai_images = PRACTICAL_LIMITS.get("max_generated_images_per_game", 5)
    can_use_ai = ai_images_generated < max_ai_images

    # Map asset type to capability manifest type
    capability_type_map = {
        "image": "background_image",
        "background": "background_image",
        "sprite": "sprite",
        "icon": "icon",
        "animation": "hint_animation",
        "hint_animation": "hint_animation",
        "feedback_animation": "feedback_animation",
        "zone_overlay": "zone_overlay",
        "diagram": "diagram_image",
    }
    capability_type = capability_type_map.get(asset_type_str, "background_image")

    # Get preferred methods from capability manifest
    if capability_type in CAPABILITY_ASSET_TYPES:
        asset_type_def = CAPABILITY_ASSET_TYPES[capability_type]
        preferred_methods = asset_type_def.preferred_methods
    else:
        # Default fallback: prefer url_fetch and cached (always available)
        preferred_methods = ["url_fetch", "cached", "css_animation"]

    # Find first available method from preferred list
    for method_id in preferred_methods:
        # Skip url_fetch if asset has no URL to fetch
        if method_id == "url_fetch" and not asset_spec.get("url"):
            continue

        # Skip AI methods if budget exhausted
        if method_id in ["nanobanana", "dalle", "stable_diffusion"] and not can_use_ai:
            continue

        # Skip unavailable methods (gemini_imagen is deprecated)
        if method_id == "gemini_imagen":
            continue

        # Check if method is available and production-ready
        if method_id in CAPABILITY_METHODS:
            method_def = CAPABILITY_METHODS[method_id]
            if method_def.status == GenerationStatus.PRODUCTION:
                # Map capability method IDs to service's GenerationMethod enum
                method_map = {
                    "nanobanana": GenerationMethod.NANOBANANA if hasattr(GenerationMethod, "NANOBANANA") else GenerationMethod.CACHED,
                    "dalle": GenerationMethod.DALLE if hasattr(GenerationMethod, "DALLE") else GenerationMethod.CACHED,
                    "stable_diffusion": GenerationMethod.STABLE_DIFFUSION if hasattr(GenerationMethod, "STABLE_DIFFUSION") else GenerationMethod.CACHED,
                    "svg_renderer": GenerationMethod.SVG_RENDERER if hasattr(GenerationMethod, "SVG_RENDERER") else GenerationMethod.CACHED,
                    "png_converter": GenerationMethod.CACHED,
                    "gif_generator": GenerationMethod.GIF_GENERATOR if hasattr(GenerationMethod, "GIF_GENERATOR") else GenerationMethod.CACHED,
                    "css_animation": GenerationMethod.CSS_ANIMATION,
                    "url_fetch": GenerationMethod.FETCH_URL if hasattr(GenerationMethod, "FETCH_URL") else GenerationMethod.CACHED,
                    "cached": GenerationMethod.CACHED,
                }
                if method_id in method_map:
                    return method_map[method_id]

    # Fallback chain: prioritize methods that are actually implemented
    # 1. If Nanobanana available and AI budget allows, use it (preferred)
    if "nanobanana" in available_methods and can_use_ai:
        return GenerationMethod.NANOBANANA
    # 2. If DALL-E available and AI budget allows, use it
    if "dalle" in available_methods and can_use_ai:
        return GenerationMethod.DALLE
    # 3. If Stable Diffusion available and AI budget allows, use it
    if "stable_diffusion" in available_methods and can_use_ai:
        return GenerationMethod.STABLE_DIFFUSION
    # 4. Always fall back to cached (graceful degradation)
    return GenerationMethod.CACHED


def _extract_assets_from_game_plan(game_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract asset hints from game plan (replaces blueprint extraction).

    Since asset_planner now runs BEFORE blueprint_generator, we extract
    hints from game_plan instead of blueprint.

    This function handles ALL mechanic types:
    - drag_drop, drag-drop, label: Creates drop zone animations + individual label assets
    - order, sequence, ordering: Creates sequence indicator assets
    - animation, visual: Creates CSS animations (original behavior)

    Args:
        game_plan: The game plan with mechanics and animation hints.

    Returns:
        List of asset specifications.
    """
    assets = []

    if not game_plan:
        return assets

    # Get required_labels for creating individual label assets
    required_labels = game_plan.get("required_labels", [])
    hierarchy_info = game_plan.get("hierarchy_info", {})

    # Extract assets from game_mechanics - handle ALL mechanic types
    game_mechanics = game_plan.get("game_mechanics", [])
    for i, mechanic in enumerate(game_mechanics):
        if not isinstance(mechanic, dict):
            continue

        mechanic_type = mechanic.get("type", "").lower()
        mechanic_id = mechanic.get("id", f"mechanic_{i}")

        # Drag-drop mechanics (labeling games)
        if mechanic_type in ("drag_drop", "drag-drop", "label", "labeling"):
            # Drop zone highlight animation
            assets.append({
                "id": f"{mechanic_id}_drop_zones",
                "type": "css_animation",
                "style": {
                    "type": "glow",
                    "duration_ms": 300,
                    "color": "#3B82F6",  # Blue highlight
                },
                "for_mechanic": mechanic_id,
                "priority": 2,
            })

            # Individual label assets for each required_label.
            # NOTE: These are created as type "ui_element" intentionally.
            # They are filtered out later (line ~1018) before image generation
            # because the frontend renders them as text. They exist here so the
            # entity_registry can track them for mechanic-to-asset relationships
            # and the blueprint_generator can reference label metadata.
            for j, label in enumerate(required_labels):
                label_id = label.lower().replace(" ", "_").replace("-", "_")
                assets.append({
                    "id": f"label_{label_id}",
                    "type": "ui_element",
                    "description": f"Draggable label: {label}",
                    "specifications": {
                        "text": label,
                        "index": j,
                        "draggable": True,
                    },
                    "for_mechanic": mechanic_id,
                    "priority": 2,
                })

            # Correct/incorrect feedback animations
            assets.append({
                "id": f"{mechanic_id}_correct_feedback",
                "type": "css_animation",
                "style": {
                    "type": "glow",
                    "duration_ms": 500,
                    "color": "#10B981",  # Green for correct
                },
                "for_mechanic": mechanic_id,
                "priority": 3,
            })
            assets.append({
                "id": f"{mechanic_id}_incorrect_feedback",
                "type": "css_animation",
                "style": {
                    "type": "shake",
                    "duration_ms": 400,
                },
                "for_mechanic": mechanic_id,
                "priority": 3,
            })

        # Sequence/order mechanics (blood flow, process ordering)
        elif mechanic_type in ("order", "sequence", "ordering", "sequencing"):
            # Sequence step indicators
            sequence_items = mechanic.get("sequence_items", [])
            if not sequence_items:
                # Try to extract from hierarchy_info blood flow path
                sequence_items = hierarchy_info.get("blood_flow_sequence", [])

            # NOTE: ui_element type - filtered out before generation (see label note above)
            assets.append({
                "id": f"{mechanic_id}_sequence_indicators",
                "type": "ui_element",
                "description": "Sequence step indicators (1, 2, 3...)",
                "specifications": {
                    "item_count": len(sequence_items) if sequence_items else 8,
                    "items": sequence_items,
                },
                "for_mechanic": mechanic_id,
                "priority": 2,
            })

            # Path/flow animation for showing correct sequence
            assets.append({
                "id": f"{mechanic_id}_flow_animation",
                "type": "css_animation",
                "style": {
                    "type": "path_draw",
                    "duration_ms": 2000,
                    "color": "#EF4444",  # Red for blood flow
                },
                "for_mechanic": mechanic_id,
                "priority": 3,
            })

        # Animation/visual mechanics (original behavior)
        elif "animation" in mechanic_type or "visual" in mechanic_type:
            assets.append({
                "id": f"{mechanic_id}_animation",
                "type": "css_animation",
                "style": {
                    "type": "pulse",
                    "duration_ms": 500,
                },
                "for_mechanic": mechanic_id,
                "priority": 3,
            })

    # Extract from scoring_rubric if it suggests visual feedback
    scoring_rubric = game_plan.get("scoring_rubric", {})
    if scoring_rubric.get("visual_feedback") or scoring_rubric:
        # Always add completion celebration animation
        assets.append({
            "id": "completion_celebration",
            "type": "css_animation",
            "style": {
                "type": "confetti",
                "duration_ms": 3000,
            },
            "priority": 3,
        })

    # Extract from interaction_features if available
    interaction_features = game_plan.get("interaction_features", {})
    if interaction_features.get("hints_enabled"):
        assets.append({
            "id": "hint_pulse_animation",
            "type": "css_animation",
            "style": {
                "type": "pulse",
                "duration_ms": 600,
                "color": "#F59E0B",  # Amber for hints
            },
            "priority": 3,
        })

    logger.info(f"Extracted {len(assets)} assets from game_plan mechanics: {[m.get('type') for m in game_mechanics]}")
    return assets


def _extract_assets_from_scene(scene_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract asset specifications from scene data.

    Args:
        scene_data: Optional scene data from scene stages.

    Returns:
        List of asset specifications.
    """
    if not scene_data:
        return []

    assets = []

    # Extract from required_assets if available
    required_assets = scene_data.get("required_assets", [])
    for asset in required_assets:
        assets.append({
            "id": asset.get("id", f"scene_{len(assets)}"),
            "type": asset.get("type", "image"),
            "prompt": asset.get("description") or asset.get("prompt"),
            "placement": asset.get("placement", "background"),
            "priority": 1,  # Scene assets are high priority
        })

    # Extract background from visual_theme
    # Handle both string (theme name) and dict (legacy) formats
    visual_theme = scene_data.get("visual_theme", "")
    if visual_theme:
        if isinstance(visual_theme, str):
            # visual_theme is a simple theme name string like "botanical_explorer"
            assets.append({
                "id": "scene_background",
                "type": "image",
                "prompt": f"Educational diagram background, {visual_theme} theme, clean, professional",
                "placement": "background",
                "priority": 1,
            })
        elif isinstance(visual_theme, dict) and visual_theme.get("background_style"):
            # visual_theme is a dict with background_style (legacy format)
            assets.append({
                "id": "scene_background",
                "type": "image",
                "prompt": f"Educational diagram background, {visual_theme.get('background_style')}, clean, professional",
                "placement": "background",
                "priority": 1,
            })

    # Extract from animation_sequences
    animation_sequences = scene_data.get("animation_sequences", [])
    for i, anim in enumerate(animation_sequences):
        if isinstance(anim, dict):
            assets.append({
                "id": f"scene_anim_{i}",
                "type": "css_animation",
                "style": {
                    "type": _map_animation_description_to_type(anim.get("description", "")),
                    "duration_ms": anim.get("duration_ms", 500),
                },
                "priority": 3,
            })

    return assets


def _map_animation_description_to_type(description: str) -> str:
    """Map a text animation description to an animation type.

    Args:
        description: Text description of animation.

    Returns:
        Animation type string.
    """
    description_lower = description.lower()

    if "pulse" in description_lower or "throb" in description_lower:
        return "pulse"
    elif "glow" in description_lower or "light" in description_lower:
        return "glow"
    elif "shake" in description_lower or "vibrate" in description_lower:
        return "shake"
    elif "fade" in description_lower:
        return "fade"
    elif "bounce" in description_lower or "jump" in description_lower:
        return "bounce"
    elif "scale" in description_lower or "grow" in description_lower or "shrink" in description_lower:
        return "scale"
    elif "confetti" in description_lower or "celebrate" in description_lower:
        return "confetti"
    elif "path" in description_lower or "draw" in description_lower or "trace" in description_lower:
        return "path_draw"
    else:
        return "pulse"  # Default


def _determine_available_methods() -> List[str]:
    """Determine which generation methods are available.

    Returns methods that are actually implemented in media_generation_service.
    Note: gemini_imagen is NOT included because it's not implemented yet.

    Implemented methods:
    - css_animation: Always available (no external dependencies)
    - cached: Always available (local cache)
    - url_fetch: Always available (fetch from URLs)
    - dalle: Available if OPENAI_API_KEY is set
    - stable_diffusion: Available if REPLICATE_API_TOKEN is set

    Returns:
        List of available method names.
    """
    import os

    # Methods that are always available (no API keys needed)
    methods = ["css_animation", "cached", "url_fetch"]

    # Check for DALL-E (OpenAI)
    if os.environ.get("OPENAI_API_KEY"):
        methods.append("dalle")

    # Check for Stable Diffusion (Replicate)
    if os.environ.get("REPLICATE_API_TOKEN"):
        methods.append("stable_diffusion")

    # Check for Nanobanana (primary image generation method)
    if os.environ.get("NANOBANANA_API_KEY"):
        methods.append("nanobanana")

    # NOTE: gemini_imagen is DEPRECATED - use nanobanana instead.
    # The gemini_imagen method was never implemented in media_generation_service.py.

    return methods


def _get_zones_from_entity_registry(
    entity_registry: Optional[EntityRegistry],
) -> List[Dict[str, Any]]:
    """
    Extract zone information from entity registry.

    This provides a normalized way to access zone data for asset planning,
    regardless of how zones were detected (Gemini, Qwen, etc.).

    Args:
        entity_registry: The entity registry containing zones

    Returns:
        List of zone dicts with normalized format
    """
    if not entity_registry:
        return []

    zones_dict = entity_registry.get("zones", {})
    if not zones_dict:
        return []

    zones = []
    for zone_id, zone_entity in zones_dict.items():
        # Convert ZoneEntity to simplified zone dict
        zone = {
            "id": zone_entity.get("id", zone_id),
            "label": zone_entity.get("label", ""),
            "shape": zone_entity.get("shape", "circle"),
            "parent_zone_id": zone_entity.get("parent_zone_id"),
            "scene_number": zone_entity.get("scene_number", 1),
            "hierarchy_level": zone_entity.get("hierarchy_level"),
        }

        # Extract coordinates based on shape
        coords = zone_entity.get("coordinates", {})
        if zone_entity.get("shape") == "circle":
            zone["x"] = coords.get("x", 50)
            zone["y"] = coords.get("y", 50)
            zone["radius"] = coords.get("radius", 5)
        elif zone_entity.get("shape") == "polygon":
            zone["points"] = coords.get("points", [])
            center = coords.get("center", {})
            zone["x"] = center.get("x", 50)
            zone["y"] = center.get("y", 50)

        zones.append(zone)

    return zones


def _extract_zone_based_assets(
    zones: List[Dict[str, Any]],
    scene_interactions: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Plan assets based on zone information.

    Uses zones to determine what assets are needed:
    - Hint animations for each zone
    - Feedback animations for interactions
    - Zone overlays for visual feedback

    Args:
        zones: List of zones from entity registry or diagram_zones
        scene_interactions: Interaction definitions for animation hints

    Returns:
        List of zone-based asset specifications
    """
    assets = []

    for zone in zones:
        zone_id = zone.get("id", "")
        label = zone.get("label", "")
        hierarchy_level = zone.get("hierarchy_level", 1)

        # Create hint animation for each zone
        # Lower hierarchy levels (sub-parts) may need more subtle animations
        animation_intensity = 1.0 if hierarchy_level == 1 else 0.7

        assets.append({
            "id": f"hint_anim_{zone_id}",
            "type": "css_animation",
            "style": {
                "type": "pulse",
                "duration_ms": 400 if hierarchy_level == 1 else 300,
                "intensity": animation_intensity,
            },
            "zone_id": zone_id,
            "priority": 3,  # Lower priority (animations)
        })

        # Create feedback animation for correct answers
        assets.append({
            "id": f"feedback_anim_{zone_id}",
            "type": "css_animation",
            "style": {
                "type": "glow",
                "duration_ms": 500,
                "color": "#4CAF50",  # Green for correct
            },
            "zone_id": zone_id,
            "priority": 3,
        })

    return assets


# =============================================================================
# WORKFLOW ROUTING FUNCTIONS (New WORKFLOW ROUTER capability)
# =============================================================================


def _calculate_priority(depends_on: List[str]) -> int:
    """Calculate execution priority based on dependencies.

    Lower priority = execute first. Assets with no dependencies have priority 0.

    Args:
        depends_on: List of asset IDs this asset depends on

    Returns:
        Priority value (0 = highest priority, execute first)
    """
    return len(depends_on)


def _topological_sort(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort workflow execution steps so dependencies come before dependents.

    Uses Kahn's algorithm for topological sorting.

    Args:
        steps: List of workflow execution steps with dependencies

    Returns:
        Sorted list where dependencies appear before dependents
    """
    if not steps:
        return []

    # Build dependency graph
    id_to_step = {s["asset_id"]: s for s in steps}
    in_degree = {s["asset_id"]: 0 for s in steps}

    # Calculate in-degrees
    for step in steps:
        for dep in step.get("dependencies", []):
            if dep in in_degree:
                in_degree[step["asset_id"]] += 1

    # Kahn's algorithm
    result = []
    queue = [sid for sid, deg in in_degree.items() if deg == 0]

    while queue:
        current = queue.pop(0)
        if current in id_to_step:
            result.append(id_to_step[current])

            # Reduce in-degree for dependents
            for step in steps:
                if current in step.get("dependencies", []):
                    in_degree[step["asset_id"]] -= 1
                    if in_degree[step["asset_id"]] == 0:
                        queue.append(step["asset_id"])

    # Handle any cycles (shouldn't happen but defensive)
    if len(result) < len(steps):
        # Add remaining steps that weren't processed (cycle detected)
        processed_ids = {s["asset_id"] for s in result}
        for step in steps:
            if step["asset_id"] not in processed_ids:
                result.append(step)
                logger.warning(f"Cycle detected in dependencies involving {step['asset_id']}")

    return result


def _extract_assets_from_scene_breakdown(
    game_plan: Dict[str, Any]
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    WORKFLOW ROUTER: Extract assets from game_plan.scene_breakdown.

    Maps asset_needs to workflows using MECHANIC_TO_WORKFLOW.
    Returns both planned_assets (with workflow assignments) and
    workflow_execution_plan (topologically sorted).

    Args:
        game_plan: ExtendedGamePlan with scene_breakdown containing asset_needs

    Returns:
        Tuple of (planned_assets, workflow_execution_plan)
    """
    planned_assets: List[Dict[str, Any]] = []
    workflow_execution_plan: List[Dict[str, Any]] = []

    # Get scene_breakdown from game_plan
    scene_breakdown = game_plan.get("scene_breakdown", [])

    if not scene_breakdown:
        logger.debug("No scene_breakdown in game_plan, skipping workflow routing")
        return planned_assets, workflow_execution_plan

    logger.info(f"WORKFLOW ROUTER: Processing {len(scene_breakdown)} scenes from game_plan")

    for scene in scene_breakdown:
        scene_num = scene.get("scene_number", 1)
        scene_title = scene.get("title", f"Scene {scene_num}")
        asset_needs = scene.get("asset_needs", {})
        mechanics = scene.get("mechanics", [])

        logger.debug(
            f"Scene {scene_num} ({scene_title}): "
            f"{len(asset_needs)} asset_needs, {len(mechanics)} mechanics"
        )

        # Process asset_needs for this scene
        for asset_id, asset_spec in asset_needs.items():
            # Handle both dict and Pydantic model formats
            if hasattr(asset_spec, "model_dump"):
                asset_spec = asset_spec.model_dump()
            elif hasattr(asset_spec, "dict"):
                asset_spec = asset_spec.dict()
            elif not isinstance(asset_spec, dict):
                logger.warning(f"Unknown asset_spec type for {asset_id}: {type(asset_spec)}")
                continue

            # Get workflow from asset_spec or infer from mechanic
            workflow = asset_spec.get("workflow")

            # If no explicit workflow, try to infer from mechanic type
            if not workflow:
                mechanic_type = asset_spec.get("type")
                if mechanic_type:
                    workflow = MECHANIC_TO_WORKFLOW.get(mechanic_type, "labeling_diagram")

            # Default to labeling_diagram if still not determined
            if not workflow:
                workflow = "labeling_diagram"

            # Get dependencies
            depends_on = asset_spec.get("depends_on", [])
            if not isinstance(depends_on, list):
                depends_on = []

            # Create full asset ID with scene prefix
            full_asset_id = f"scene_{scene_num}_{asset_id}"

            # Prefix dependencies with scene number
            full_dependencies = [f"scene_{scene_num}_{d}" for d in depends_on]

            # Calculate priority (lower = execute first)
            priority = _calculate_priority(depends_on)

            # Create planned asset with workflow assignment
            planned_asset = {
                "id": full_asset_id,
                "scene_number": scene_num,
                "asset_type": asset_id,  # Original asset key (e.g., "primary", "comparison")
                "workflow": workflow,
                "spec": asset_spec,
                "depends_on": full_dependencies,
                "priority": priority,
                # Pass through relevant spec fields
                "query": asset_spec.get("query"),
                "type": asset_spec.get("type", "image"),
                "concept": asset_spec.get("concept"),
                "config": asset_spec.get("config", {}),
            }
            planned_assets.append(planned_asset)

            # Create workflow execution step
            workflow_step: WorkflowExecutionStep = {
                "asset_id": full_asset_id,
                "workflow": workflow,
                "scene": scene_num,
                "dependencies": full_dependencies,
                "spec": asset_spec,
            }
            workflow_execution_plan.append(workflow_step)

            logger.debug(
                f"  Asset {full_asset_id}: workflow={workflow}, "
                f"deps={full_dependencies}, priority={priority}"
            )

    # Deduplicate: same scene + same workflow → keep first, remove others
    seen_workflows_per_scene: Dict[tuple, str] = {}  # (scene_num, workflow) → first_asset_id
    skipped_asset_ids: set = set()
    for step in workflow_execution_plan:
        key = (step["scene"], step["workflow"])
        if key in seen_workflows_per_scene:
            first_id = seen_workflows_per_scene[key]
            skipped_asset_ids.add(step["asset_id"])
            logger.debug(
                f"Dedup: {step['asset_id']} same workflow as {first_id} in scene {step['scene']}, skipping"
            )
        else:
            seen_workflows_per_scene[key] = step["asset_id"]

    workflow_execution_plan = [s for s in workflow_execution_plan if s["asset_id"] not in skipped_asset_ids]
    planned_assets = [a for a in planned_assets if a.get("id") not in skipped_asset_ids]

    # Topological sort to order by dependencies
    workflow_execution_plan = _topological_sort(workflow_execution_plan)

    logger.info(
        f"WORKFLOW ROUTER: {len(planned_assets)} planned assets, "
        f"{len(workflow_execution_plan)} workflow steps (topologically sorted)"
    )

    return planned_assets, workflow_execution_plan


def _update_registry_with_assets(
    entity_registry: Optional[EntityRegistry],
    planned_assets: List[Dict[str, Any]],
) -> EntityRegistry:
    """
    Add planned assets to the entity registry.

    Creates AssetEntity entries and populates zone_assets relationship map.

    Args:
        entity_registry: Existing entity registry (or None to create new)
        planned_assets: List of planned asset specifications

    Returns:
        Updated EntityRegistry with assets populated
    """
    registry = entity_registry or create_empty_entity_registry()

    # Ensure required dicts exist
    if registry.get("assets") is None:
        registry["assets"] = {}
    if registry.get("zone_assets") is None:
        registry["zone_assets"] = {}
    if registry.get("asset_zones") is None:
        registry["asset_zones"] = {}

    for asset_spec in planned_assets:
        asset_id = asset_spec.get("id", f"asset_{len(registry['assets'])}")

        # Determine source based on generation method
        method = asset_spec.get("generation_method", "cached")
        if method == "cached":
            source = "cached"
        elif method in ("gemini_imagen", "nanobanana"):
            source = "generated"
        else:
            source = "static"

        # Create AssetEntity
        asset_entity: AssetEntity = {
            "id": asset_id,
            "type": asset_spec.get("type", "image"),
            "source": source,
            "url": asset_spec.get("url"),
            "local_path": asset_spec.get("local_path"),
            "generation_params": {
                "method": method,
                "prompt": asset_spec.get("prompt"),
                "style": asset_spec.get("style"),
            } if asset_spec.get("prompt") or asset_spec.get("style") else None,
            "dimensions": asset_spec.get("dimensions"),
            "priority": asset_spec.get("priority", 2),
            "placement": asset_spec.get("placement"),
        }

        # Add to registry
        registry["assets"][asset_id] = asset_entity

        # Update zone_assets and asset_zones relationships
        zone_id = asset_spec.get("zone_id")
        if zone_id:
            # zone_assets: zone_id -> [asset_ids]
            if zone_id not in registry["zone_assets"]:
                registry["zone_assets"][zone_id] = []
            if asset_id not in registry["zone_assets"][zone_id]:
                registry["zone_assets"][zone_id].append(asset_id)

            # asset_zones: asset_id -> [zone_ids] (reverse lookup)
            if asset_id not in registry["asset_zones"]:
                registry["asset_zones"][asset_id] = []
            if zone_id not in registry["asset_zones"][asset_id]:
                registry["asset_zones"][asset_id].append(zone_id)

    logger.info(
        f"Added {len(planned_assets)} assets to entity registry, "
        f"{len(registry.get('zone_assets', {}))} zone-asset relationships"
    )

    return registry


def _get_redundant_asset_types_for_workflows(
    workflow_execution_plan: List[Dict[str, Any]]
) -> set:
    """Read WORKFLOW_CAPABILITIES to find asset types made redundant by assigned workflows.

    For example, the labeling_diagram workflow internally handles image retrieval
    and generation, so planning separate "image", "background", or "diagram"
    assets would be redundant.

    Args:
        workflow_execution_plan: List of workflow execution steps

    Returns:
        Set of asset type strings that are redundant
    """
    redundant: set = set()
    for step in workflow_execution_plan:
        workflow_name = step.get("workflow", "")
        caps = WORKFLOW_CAPABILITIES.get(workflow_name)
        if caps:
            redundant.update(caps.get("makes_redundant", []))
    return redundant


async def asset_planner(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Analyze scene data and plan required media assets.

    NOTE: This agent runs BEFORE blueprint_generator. It does NOT read from blueprint.

    Inputs: scene_structure, scene_assets, scene_interactions,
            scene_data, generated_diagram_path, diagram_zones, game_plan,
            entity_registry (Phase 3)
    Outputs: planned_assets, entity_registry (updated with assets)

    This agent examines scene data from all stages to determine what media assets
    need to be generated, and chooses the best generation method for each based
    on availability and requirements.

    Phase 3 Entity Registry:
    - Reads zones from entity_registry if available (preferred over diagram_zones)
    - Writes planned assets to entity_registry
    - Populates zone_assets and asset_zones relationships
    """
    # Skip guard: if planned_assets and workflow_execution_plan already exist,
    # pass through without re-planning (prevents re-execution on blueprint retries)
    existing_planned = state.get("planned_assets")
    existing_workflow_plan = state.get("workflow_execution_plan")
    if existing_planned and existing_workflow_plan:
        logger.info(
            f"Skipping asset planning — {len(existing_planned)} assets and "
            f"{len(existing_workflow_plan)} workflow steps already planned"
        )
        return {
            "planned_assets": existing_planned,
            "workflow_execution_plan": existing_workflow_plan,
            "entity_registry": state.get("entity_registry"),
        }

    # Get game plan (for animation hints - replaces blueprint dependency)
    game_plan = state.get("game_plan", {})

    # ==========================================================================
    # ENTITY REGISTRY INTEGRATION (Phase 3)
    # ==========================================================================
    # Read zones from entity registry if available (preferred data source)
    entity_registry = state.get("entity_registry")

    # Get zones from entity registry (normalized format)
    registry_zones = _get_zones_from_entity_registry(entity_registry)
    if registry_zones:
        logger.info(f"Using {len(registry_zones)} zones from entity registry")

    # Get scene data from hierarchical stages (preferred) or legacy scene_data
    scene_structure = state.get("scene_structure", {})
    scene_assets = state.get("scene_assets", {})
    scene_interactions = state.get("scene_interactions", {})
    scene_data = state.get("scene_data")  # Legacy fallback

    # Ensure dict types for safety
    if not isinstance(scene_structure, dict):
        scene_structure = {}
    if not isinstance(scene_assets, dict):
        scene_assets = {}
    if not isinstance(scene_interactions, dict):
        scene_interactions = {}
    if not isinstance(scene_data, dict):
        scene_data = {}

    # Merge hierarchical scene data if available
    if scene_structure or scene_assets or scene_interactions:
        # Combine into scene_data format for processing
        # NOTE: scene_stage2_assets outputs {"scene_assets": {"required_assets": [...], ...}}
        # So we use "required_assets" key, NOT "assets"
        scene_data = {
            **scene_data,
            "visual_theme": scene_structure.get("visual_theme", scene_data.get("visual_theme")),
            "required_assets": [
                *scene_assets.get("required_assets", []),  # FIX: was "assets" - wrong key!
                *scene_data.get("required_assets", []),
            ],
            "animation_sequences": scene_interactions.get("animations", scene_interactions.get("asset_interactions", [])),
            "regions": scene_structure.get("regions", []),
        }

    # Get diagram-related assets
    generated_diagram_path = state.get("generated_diagram_path")

    # Use registry zones if available, fallback to diagram_zones
    diagram_zones = registry_zones if registry_zones else (state.get("diagram_zones", []) or [])

    logger.info("Asset planner analyzing scene data for required assets (runs before blueprint)")

    # Determine available generation methods
    available_methods = _determine_available_methods()
    logger.info(f"Available generation methods: {available_methods}")

    # Extract assets from game plan (replaces blueprint extraction)
    game_plan_assets = _extract_assets_from_game_plan(game_plan)
    logger.info(f"Found {len(game_plan_assets)} assets in game plan")

    # Extract assets from scene data
    scene_asset_specs = _extract_assets_from_scene(scene_data)
    logger.info(f"Found {len(scene_asset_specs)} assets in scene data")

    # ==========================================================================
    # ZONE-BASED ASSET PLANNING (Phase 3)
    # ==========================================================================
    # Plan assets based on zones (hint animations, feedback, etc.)
    zone_based_assets = _extract_zone_based_assets(
        zones=diagram_zones,
        scene_interactions=scene_interactions,
    )
    logger.info(f"Planned {len(zone_based_assets)} zone-based assets")

    # Add generated diagram as an asset if it exists
    diagram_assets = []
    if generated_diagram_path:
        diagram_assets.append({
            "id": "main_diagram",
            "type": "image",
            "url": generated_diagram_path if generated_diagram_path.startswith("http") else None,
            "local_path": generated_diagram_path if not generated_diagram_path.startswith("http") else None,
            "placement": "background",
            "priority": 1,  # Critical - main diagram
            "source": "generated",
        })
        logger.info(f"Added generated diagram to assets: {generated_diagram_path}")

    # Combine and deduplicate (game_plan_assets replaces blueprint_assets)
    # Include zone_based_assets for Phase 3 entity registry
    all_asset_specs = game_plan_assets + scene_asset_specs + diagram_assets + zone_based_assets
    seen_ids = set()
    unique_assets = []
    for asset in all_asset_specs:
        asset_id = asset.get("id")
        if asset_id not in seen_ids:
            seen_ids.add(asset_id)
            unique_assets.append(asset)

    # Convert to PlannedAsset objects
    # Track AI image generation count for budget enforcement
    ai_images_count = state.get("_ai_images_generated", 0)
    planned_assets = []

    # Filter out assets that don't need generation
    has_main_diagram = any(a.get("id") == "main_diagram" and a.get("local_path") for a in unique_assets)

    for spec in unique_assets:
        asset_type_str = spec.get("type", "image")
        asset_id = spec.get("id", "")

        # Skip UI elements - frontend renders these as text, no image generation needed
        if asset_type_str == "ui_element":
            logger.debug(f"Skipping UI element asset: {asset_id} (frontend handles)")
            continue

        # Skip label assets without URLs/paths - these are text labels rendered by frontend
        # Pattern: label_*, label_target_* are draggable text labels, not images
        if asset_id.startswith("label_") and not spec.get("local_path") and not spec.get("url"):
            logger.debug(f"Skipping text label asset: {asset_id} (frontend renders)")
            continue

        # Skip redundant diagram image assets if main_diagram already exists
        if has_main_diagram and asset_type_str == "image" and "diagram" in asset_id.lower() and asset_id != "main_diagram":
            if not spec.get("local_path") and not spec.get("url"):
                logger.debug(f"Skipping redundant diagram asset: {asset_id} (main_diagram exists)")
                continue

        # Map string type to enum
        type_mapping = {
            "image": AssetType.IMAGE,
            "gif": AssetType.GIF,
            "video": AssetType.VIDEO,
            "sprite": AssetType.SPRITE,
            "css_animation": AssetType.CSS_ANIMATION,
        }
        asset_type = type_mapping.get(asset_type_str, AssetType.IMAGE)

        # Determine generation method (capability-aware with budget tracking)
        generation_method = _determine_generation_method(
            spec, available_methods, ai_images_generated=ai_images_count
        )

        # Track AI generation usage for budget enforcement
        if generation_method in (GenerationMethod.NANOBANANA, GenerationMethod.DALLE, GenerationMethod.STABLE_DIFFUSION):
            ai_images_count += 1

        planned = PlannedAsset(
            id=spec.get("id", f"asset_{len(planned_assets)}"),
            type=asset_type,
            generation_method=generation_method,
            prompt=spec.get("prompt"),
            url=spec.get("url"),
            local_path=spec.get("local_path"),  # Pass through existing local file path
            dimensions=spec.get("dimensions"),
            priority=spec.get("priority", 2),
            placement=spec.get("placement", "overlay"),
            zone_id=spec.get("zone_id"),
            layer=spec.get("layer", 0),
            style=spec.get("style"),
        )
        planned_assets.append(planned)

    # Sort by priority
    planned_assets.sort(key=lambda a: a.priority)

    logger.info(f"Planned {len(planned_assets)} assets for generation")

    # Convert to serializable format for state
    planned_assets_dict = [
        {
            "id": p.id,
            "type": p.type.value,
            "generation_method": p.generation_method.value,
            "prompt": p.prompt,
            "url": p.url,
            "local_path": p.local_path,  # Include local_path for existing files
            "dimensions": p.dimensions,
            "priority": p.priority,
            "placement": p.placement,
            "zone_id": p.zone_id,
            "layer": p.layer,
            "style": p.style,
        }
        for p in planned_assets
    ]

    # ==========================================================================
    # UPDATE ENTITY REGISTRY WITH ASSETS (Phase 3)
    # ==========================================================================
    # Add planned assets to entity registry and populate relationships
    updated_registry = _update_registry_with_assets(
        entity_registry=entity_registry,
        planned_assets=planned_assets_dict,
    )

    logger.info(
        f"Entity registry updated: "
        f"{len(updated_registry.get('zones', {}))} zones, "
        f"{len(updated_registry.get('assets', {}))} assets, "
        f"{len(updated_registry.get('zone_assets', {}))} zone-asset links"
    )

    # ==========================================================================
    # WORKFLOW ROUTING (Phase 4)
    # ==========================================================================
    # Extract workflow execution plan from game_plan.scene_breakdown if present
    # This enables workflow mode in asset_generator_orchestrator
    workflow_planned_assets, workflow_execution_plan = _extract_assets_from_scene_breakdown(game_plan)

    if workflow_execution_plan:
        logger.info(
            f"WORKFLOW MODE: Generated {len(workflow_execution_plan)} workflow steps "
            f"and {len(workflow_planned_assets)} workflow assets"
        )
        # Use WORKFLOW_CAPABILITIES to find asset types made redundant by
        # assigned workflows. This generalizes the dedup to work for ALL
        # workflow types rather than hardcoding "image" checks.
        redundant_types = _get_redundant_asset_types_for_workflows(workflow_execution_plan)
        if redundant_types:
            logger.info(f"Workflow-redundant asset types: {redundant_types}")

        workflow_asset_ids = {a.get("id") for a in workflow_planned_assets}
        non_redundant = []
        for a in planned_assets_dict:
            aid = a.get("id", "")
            atype = a.get("type", "")
            # Skip assets whose type is made redundant by an assigned workflow
            if aid not in workflow_asset_ids and atype in redundant_types:
                logger.debug(f"Dropping redundant '{atype}' asset '{aid}' — workflow handles this type")
                continue
            if aid not in workflow_asset_ids:
                non_redundant.append(a)
        merged_assets = workflow_planned_assets + non_redundant
        planned_assets_dict = merged_assets

    return {
        "planned_assets": planned_assets_dict,
        "workflow_execution_plan": workflow_execution_plan,  # Phase 4: Workflow routing
        "entity_registry": updated_registry,  # Phase 3: Updated registry with assets
        "_ai_images_generated": ai_images_count,  # Track for budget enforcement
    }
