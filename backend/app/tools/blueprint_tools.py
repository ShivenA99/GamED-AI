"""
Blueprint Tools for GamED.AI v2

Tools for validating blueprints, generating diagram specs, and managing assets.
These tools support the production phase of game generation.
"""

import json
from typing import Dict, Any, List, Optional, Tuple

from app.utils.logging_config import get_logger
from app.tools.registry import register_tool

logger = get_logger("gamed_ai.tools.blueprint")


# ============================================================================
# Blueprint Validation
# ============================================================================

async def validate_blueprint_impl(
    blueprint: Dict[str, Any],
    template_type: str = "INTERACTIVE_DIAGRAM"
) -> Dict[str, Any]:
    """
    Validate a game blueprint against schema and semantic rules.

    Args:
        blueprint: The blueprint JSON to validate
        template_type: Template type for template-specific validation

    Returns:
        Dict with valid, score, errors, warnings
    """
    errors = []
    warnings = []
    score = 1.0

    # Required top-level fields
    required_fields = ["template", "game_title", "scenes"]

    for field in required_fields:
        if field not in blueprint:
            errors.append(f"Missing required field: {field}")
            score -= 0.2

    if errors:
        return {
            "valid": False,
            "score": max(0, score),
            "errors": errors,
            "warnings": warnings
        }

    # Template validation
    if blueprint.get("template") != template_type:
        warnings.append(f"Template mismatch: expected {template_type}, got {blueprint.get('template')}")

    # Scenes validation
    scenes = blueprint.get("scenes", [])
    if not scenes:
        errors.append("Blueprint must have at least one scene")
        score -= 0.3
    else:
        for i, scene in enumerate(scenes):
            scene_errors = _validate_scene(scene, i, template_type)
            errors.extend(scene_errors)
            score -= len(scene_errors) * 0.1

    # Template-specific validation
    if template_type == "INTERACTIVE_DIAGRAM":
        template_errors = _validate_interactive_diagram_blueprint(blueprint)
        errors.extend(template_errors)
        score -= len(template_errors) * 0.1

    return {
        "valid": len(errors) == 0,
        "score": max(0, min(1.0, score)),
        "errors": errors,
        "warnings": warnings,
        "template_type": template_type
    }


def _validate_scene(scene: Dict[str, Any], index: int, template_type: str) -> List[str]:
    """Validate a single scene."""
    errors = []
    prefix = f"Scene {index}"

    # Required scene fields
    required = ["scene_id", "background"]
    for field in required:
        if field not in scene:
            errors.append(f"{prefix}: Missing required field '{field}'")

    # Validate elements if present
    elements = scene.get("elements", [])
    for j, element in enumerate(elements):
        if "id" not in element:
            errors.append(f"{prefix} Element {j}: Missing 'id'")
        if "type" not in element:
            errors.append(f"{prefix} Element {j}: Missing 'type'")

    return errors


def _validate_interactive_diagram_blueprint(blueprint: Dict[str, Any]) -> List[str]:
    """INTERACTIVE_DIAGRAM-specific validation."""
    errors = []

    scenes = blueprint.get("scenes", [])
    if scenes:
        main_scene = scenes[0]

        # Check for drop zones
        elements = main_scene.get("elements", [])
        drop_zones = [e for e in elements if e.get("type") == "drop_zone"]

        if not drop_zones:
            errors.append("INTERACTIVE_DIAGRAM requires at least one drop_zone element")

        # Check for labels
        labels = main_scene.get("labels", [])
        if not labels:
            errors.append("INTERACTIVE_DIAGRAM requires labels array")

        # Check drop zone count matches labels
        if len(drop_zones) != len(labels):
            errors.append(f"Mismatch: {len(drop_zones)} drop zones but {len(labels)} labels")

    return errors


async def fix_blueprint_impl(
    blueprint: Dict[str, Any],
    errors: List[str],
    template_type: str = "INTERACTIVE_DIAGRAM"
) -> Dict[str, Any]:
    """
    Attempt to fix common blueprint errors.

    Args:
        blueprint: The blueprint with errors
        errors: List of error messages
        template_type: Template type

    Returns:
        Dict with fixed_blueprint, fixes_applied, remaining_errors
    """
    from app.services.llm_service import get_llm_service

    llm = get_llm_service()

    fixes_applied = []
    fixed_blueprint = json.loads(json.dumps(blueprint))  # Deep copy

    # Try to fix missing fields
    if "template" not in fixed_blueprint:
        fixed_blueprint["template"] = template_type
        fixes_applied.append("Added missing template field")

    if "game_title" not in fixed_blueprint:
        fixed_blueprint["game_title"] = "Educational Game"
        fixes_applied.append("Added default game_title")

    if "scenes" not in fixed_blueprint:
        fixed_blueprint["scenes"] = []
        fixes_applied.append("Added empty scenes array")

    # If there are complex errors, use LLM to fix
    complex_errors = [e for e in errors if "drop_zone" in e or "labels" in e]
    if complex_errors and fixed_blueprint.get("scenes"):
        fix_prompt = f"""Fix this game blueprint to resolve these errors:

Errors:
{json.dumps(complex_errors, indent=2)}

Current Blueprint:
{json.dumps(fixed_blueprint, indent=2)}

Rules for {template_type}:
1. Each label must have a corresponding drop_zone element
2. Drop zones need id, position (x, y), and correct_label properties
3. Labels array should list all labelable items

Return the corrected blueprint JSON only."""

        try:
            result = await llm.generate_json(
                prompt=fix_prompt,
                system_prompt="You are a game blueprint repair expert. Fix the JSON to meet requirements."
            )
            if result:
                fixed_blueprint = result
                fixes_applied.append("Applied LLM-assisted fixes")
        except Exception as e:
            logger.warning(f"LLM fix failed: {e}")

    # Re-validate
    validation = await validate_blueprint_impl(fixed_blueprint, template_type)

    return {
        "fixed_blueprint": fixed_blueprint,
        "fixes_applied": fixes_applied,
        "remaining_errors": validation.get("errors", []),
        "now_valid": validation.get("valid", False),
        "score": validation.get("score", 0)
    }


# ============================================================================
# Blueprint Generation
# ============================================================================

async def generate_blueprint_impl(
    game_plan: Dict[str, Any],
    scene_data: Dict[str, Any],
    interactions: Dict[str, Any],
    zones: List[Dict[str, Any]],
    labels: List[str],
    template_type: str = "INTERACTIVE_DIAGRAM",
    diagram_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a complete game blueprint from design components.

    Args:
        game_plan: Game mechanics and objectives from game_planner
        scene_data: Scene structure and assets from scene stages
        interactions: Interaction definitions from scene_stage3
        zones: Detected zones with positions
        labels: List of labels for the diagram
        template_type: Game template type
        diagram_url: URL of the diagram image (optional)

    Returns:
        Dict with blueprint, valid, errors
    """
    try:
        # Extract game metadata
        game_title = game_plan.get("game_title", game_plan.get("title", "Educational Game"))
        learning_objectives = game_plan.get("learning_objectives", [])
        mechanics = game_plan.get("mechanics", game_plan.get("game_mechanics", {}))

        # Build scene elements from zones and labels
        elements = []
        for i, zone in enumerate(zones):
            label = labels[i] if i < len(labels) else f"Zone {i+1}"

            # Get zone position (normalize if needed)
            center = zone.get("center", [0.5, 0.5])
            bbox = zone.get("bbox", zone.get("bounding_box", [0, 0, 1, 1]))

            # Calculate position as percentage
            x_pct = center[0] if isinstance(center[0], float) and center[0] <= 1 else center[0] / 100
            y_pct = center[1] if isinstance(center[1], float) and center[1] <= 1 else center[1] / 100

            elements.append({
                "id": f"dropzone_{i}",
                "type": "drop_zone",
                "position": {
                    "x": round(x_pct * 100, 1),
                    "y": round(y_pct * 100, 1),
                    "unit": "percent"
                },
                "size": {
                    "width": 80,
                    "height": 40
                },
                "correct_label": label,
                "bbox": bbox,
                "style": {
                    "borderColor": "#3B82F6",
                    "borderWidth": 2,
                    "borderStyle": "dashed",
                    "borderRadius": 8,
                    "backgroundColor": "rgba(59, 130, 246, 0.1)"
                }
            })

        # Build background
        background = {
            "type": "image" if diagram_url else "color",
        }
        if diagram_url:
            background["url"] = diagram_url
        else:
            background["color"] = "#f5f5f5"

        # Build main scene
        main_scene = {
            "scene_id": "main",
            "name": scene_data.get("name", "Main Scene"),
            "background": background,
            "elements": elements,
            "labels": labels,
            "interactions": interactions.get("interactions", []) if isinstance(interactions, dict) else []
        }

        # Build complete blueprint
        blueprint = {
            "template": template_type,
            "game_title": game_title,
            "metadata": {
                "learning_objectives": learning_objectives,
                "difficulty": game_plan.get("difficulty", "medium"),
                "estimated_time": game_plan.get("estimated_time", "5 minutes"),
                "subject": game_plan.get("subject", ""),
                "grade_level": game_plan.get("grade_level", ""),
                "generated_at": __import__("datetime").datetime.now().isoformat()
            },
            "mechanics": mechanics,
            "scenes": [main_scene],
            "scoring": {
                "correct_placement": game_plan.get("points_per_correct", 10),
                "incorrect_placement": game_plan.get("points_per_incorrect", -5),
                "hint_penalty": game_plan.get("hint_penalty", -2),
                "time_bonus": game_plan.get("time_bonus", True)
            },
            "feedback": {
                "correct": game_plan.get("correct_feedback", "Correct! Well done."),
                "incorrect": game_plan.get("incorrect_feedback", "Try again."),
                "complete": game_plan.get("complete_feedback", "Congratulations! You've completed the activity.")
            }
        }

        # Validate the generated blueprint
        validation = await validate_blueprint_impl(blueprint, template_type)

        return {
            "blueprint": blueprint,
            "valid": validation.get("valid", False),
            "score": validation.get("score", 0),
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
            "element_count": len(elements),
            "label_count": len(labels)
        }

    except Exception as e:
        logger.error(f"Blueprint generation failed: {e}")
        return {
            "blueprint": None,
            "valid": False,
            "score": 0,
            "errors": [f"Generation failed: {str(e)}"],
            "warnings": []
        }


# ============================================================================
# Asset Planning & Generation
# ============================================================================

async def plan_assets_impl(
    blueprint: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Plan assets needed for a game blueprint.

    Args:
        blueprint: The game blueprint

    Returns:
        Dict with asset_list, generation_plan, estimated_count
    """
    assets = []

    # Extract assets from scenes
    for scene in blueprint.get("scenes", []):
        # Background
        bg = scene.get("background", {})
        if bg.get("type") == "image" and bg.get("url"):
            assets.append({
                "type": "background",
                "source": "url",
                "url": bg["url"],
                "scene_id": scene.get("scene_id")
            })
        elif bg.get("type") == "generated":
            assets.append({
                "type": "background",
                "source": "generate",
                "prompt": bg.get("generation_prompt", ""),
                "scene_id": scene.get("scene_id")
            })

        # Elements
        for element in scene.get("elements", []):
            if element.get("image_url"):
                assets.append({
                    "type": "element",
                    "element_id": element.get("id"),
                    "source": "url",
                    "url": element["image_url"]
                })
            elif element.get("generate"):
                assets.append({
                    "type": "element",
                    "element_id": element.get("id"),
                    "source": "generate",
                    "prompt": element.get("generation_prompt", "")
                })

    return {
        "asset_list": assets,
        "total_count": len(assets),
        "to_download": len([a for a in assets if a["source"] == "url"]),
        "to_generate": len([a for a in assets if a["source"] == "generate"]),
        "generation_plan": _create_generation_plan(assets)
    }


def _create_generation_plan(assets: List[Dict]) -> List[Dict]:
    """Create a prioritized asset generation plan."""
    plan = []

    # Prioritize: backgrounds first, then elements
    backgrounds = [a for a in assets if a["type"] == "background"]
    elements = [a for a in assets if a["type"] == "element"]

    for i, bg in enumerate(backgrounds):
        plan.append({
            "priority": i + 1,
            "asset": bg,
            "action": "download" if bg["source"] == "url" else "generate"
        })

    for i, elem in enumerate(elements):
        plan.append({
            "priority": len(backgrounds) + i + 1,
            "asset": elem,
            "action": "download" if elem["source"] == "url" else "generate"
        })

    return plan


async def generate_assets_impl(
    asset_plan: Dict[str, Any],
    max_concurrent: int = 3
) -> Dict[str, Any]:
    """
    Execute asset generation plan.

    Args:
        asset_plan: Plan from plan_assets_impl
        max_concurrent: Max concurrent generations

    Returns:
        Dict with generated_assets, failed_assets, total_generated
    """
    import asyncio
    import httpx

    generated = []
    failed = []

    generation_plan = asset_plan.get("generation_plan", [])

    async def process_asset(plan_item: Dict) -> Dict:
        asset = plan_item["asset"]
        action = plan_item["action"]

        try:
            if action == "download":
                # Download from URL
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(asset["url"])
                    response.raise_for_status()

                return {
                    "asset": asset,
                    "status": "success",
                    "data_size": len(response.content),
                    "content_type": response.headers.get("content-type")
                }

            elif action == "generate":
                # Use vision tools to generate
                from app.tools.vision_tools import generate_diagram_image_impl

                result = await generate_diagram_image_impl(
                    prompt=asset.get("prompt", "Educational diagram")
                )

                if result.get("image_url"):
                    return {
                        "asset": asset,
                        "status": "success",
                        "generated_url": result["image_url"]
                    }
                else:
                    return {
                        "asset": asset,
                        "status": "failed",
                        "error": result.get("error", "Generation failed")
                    }

        except Exception as e:
            return {
                "asset": asset,
                "status": "failed",
                "error": str(e)
            }

    # Process in batches
    for i in range(0, len(generation_plan), max_concurrent):
        batch = generation_plan[i:i + max_concurrent]
        results = await asyncio.gather(*[process_asset(item) for item in batch])

        for result in results:
            if result["status"] == "success":
                generated.append(result)
            else:
                failed.append(result)

    return {
        "generated_assets": generated,
        "failed_assets": failed,
        "total_generated": len(generated),
        "total_failed": len(failed),
        "success_rate": len(generated) / max(1, len(generation_plan))
    }


async def validate_assets_impl(
    generated_assets: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validate generated assets.

    Args:
        generated_assets: List of generated asset results

    Returns:
        Dict with valid, invalid, validation_results
    """
    valid = []
    invalid = []

    for asset in generated_assets:
        if asset.get("status") != "success":
            invalid.append({
                "asset": asset.get("asset"),
                "reason": "Generation failed"
            })
            continue

        # Check for required data
        if asset.get("data_size", 0) > 0 or asset.get("generated_url"):
            valid.append(asset)
        else:
            invalid.append({
                "asset": asset.get("asset"),
                "reason": "No data or URL"
            })

    return {
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "valid_assets": valid,
        "invalid_assets": invalid,
        "all_valid": len(invalid) == 0
    }


# ============================================================================
# Diagram Spec Generation
# ============================================================================

async def generate_diagram_spec_impl(
    blueprint: Dict[str, Any],
    zones: List[Dict[str, Any]],
    labels: List[str]
) -> Dict[str, Any]:
    """
    Generate diagram specification from blueprint and zones.

    Args:
        blueprint: The game blueprint
        zones: Detected zones with positions
        labels: List of labels for the diagram

    Returns:
        Dict with diagram_spec containing drop zones and label positions
    """
    # Map zones to labels
    if len(zones) != len(labels):
        logger.warning(f"Zone count ({len(zones)}) != label count ({len(labels)})")

    drop_zones = []
    for i, zone in enumerate(zones):
        label = labels[i] if i < len(labels) else f"Zone {i+1}"

        drop_zones.append({
            "id": f"dropzone_{i}",
            "label": label,
            "position": {
                "x": zone.get("center", [0.5, 0.5])[0],
                "y": zone.get("center", [0.5, 0.5])[1]
            },
            "bbox": zone.get("bbox", [0, 0, 1, 1]),
            "size": {
                "width": 80,
                "height": 40
            }
        })

    # Generate label chips
    label_chips = []
    for i, label in enumerate(labels):
        label_chips.append({
            "id": f"label_{i}",
            "text": label,
            "matched_zone": f"dropzone_{i}"
        })

    return {
        "diagram_spec": {
            "drop_zones": drop_zones,
            "label_chips": label_chips,
            "total_zones": len(drop_zones),
            "total_labels": len(label_chips)
        },
        "valid": len(drop_zones) == len(label_chips)
    }


async def validate_diagram_spec_impl(
    diagram_spec: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate a diagram specification.

    Args:
        diagram_spec: The diagram spec to validate

    Returns:
        Dict with valid, errors, warnings
    """
    errors = []
    warnings = []

    spec = diagram_spec.get("diagram_spec", diagram_spec)

    drop_zones = spec.get("drop_zones", [])
    label_chips = spec.get("label_chips", [])

    if not drop_zones:
        errors.append("No drop zones defined")

    if not label_chips:
        errors.append("No label chips defined")

    if len(drop_zones) != len(label_chips):
        errors.append(f"Mismatch: {len(drop_zones)} zones vs {len(label_chips)} labels")

    # Check each drop zone
    for i, zone in enumerate(drop_zones):
        if "id" not in zone:
            errors.append(f"Drop zone {i}: missing id")
        if "position" not in zone:
            errors.append(f"Drop zone {i}: missing position")
        if "label" not in zone:
            warnings.append(f"Drop zone {i}: missing label")

    # Check each label chip
    for i, chip in enumerate(label_chips):
        if "id" not in chip:
            errors.append(f"Label chip {i}: missing id")
        if "text" not in chip:
            errors.append(f"Label chip {i}: missing text")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "zone_count": len(drop_zones),
        "label_count": len(label_chips)
    }


# ============================================================================
# Tool Registration
# ============================================================================

def register_blueprint_tools() -> None:
    """Register all blueprint tools in the registry."""

    register_tool(
        name="generate_blueprint",
        description="Generate a complete game blueprint from design components. Assembles game plan, scene data, interactions, zones, and labels into a valid blueprint JSON structure.",
        parameters={
            "type": "object",
            "properties": {
                "game_plan": {
                    "type": "object",
                    "description": "Game mechanics and objectives from game_planner"
                },
                "scene_data": {
                    "type": "object",
                    "description": "Scene structure and assets from scene stages"
                },
                "interactions": {
                    "type": "object",
                    "description": "Interaction definitions from scene_stage3"
                },
                "zones": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Detected zones with positions (center, bbox)"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of labels for the diagram"
                },
                "template_type": {
                    "type": "string",
                    "description": "Game template type",
                    "default": "INTERACTIVE_DIAGRAM"
                },
                "diagram_url": {
                    "type": "string",
                    "description": "URL of the diagram image (optional)"
                }
            },
            "required": ["game_plan", "scene_data", "interactions", "zones", "labels"]
        },
        function=generate_blueprint_impl
    )

    register_tool(
        name="validate_blueprint",
        description="Validate a game blueprint against schema and semantic rules. Returns validation status, score, and error messages.",
        parameters={
            "type": "object",
            "properties": {
                "blueprint": {
                    "type": "object",
                    "description": "The blueprint JSON to validate"
                },
                "template_type": {
                    "type": "string",
                    "description": "Template type for validation",
                    "default": "INTERACTIVE_DIAGRAM"
                }
            },
            "required": ["blueprint"]
        },
        function=validate_blueprint_impl
    )

    register_tool(
        name="fix_blueprint",
        description="Attempt to automatically fix common blueprint errors. Uses rule-based fixes and LLM assistance.",
        parameters={
            "type": "object",
            "properties": {
                "blueprint": {
                    "type": "object",
                    "description": "The blueprint with errors"
                },
                "errors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of error messages to fix"
                },
                "template_type": {
                    "type": "string",
                    "default": "INTERACTIVE_DIAGRAM"
                }
            },
            "required": ["blueprint", "errors"]
        },
        function=fix_blueprint_impl
    )

    register_tool(
        name="plan_assets",
        description="Plan assets needed for a game blueprint. Returns list of assets to download or generate.",
        parameters={
            "type": "object",
            "properties": {
                "blueprint": {
                    "type": "object",
                    "description": "The game blueprint"
                }
            },
            "required": ["blueprint"]
        },
        function=plan_assets_impl
    )

    register_tool(
        name="generate_assets",
        description="Execute asset generation plan. Downloads URLs and generates images as needed.",
        parameters={
            "type": "object",
            "properties": {
                "asset_plan": {
                    "type": "object",
                    "description": "Asset plan from plan_assets"
                },
                "max_concurrent": {
                    "type": "integer",
                    "description": "Max concurrent operations",
                    "default": 3
                }
            },
            "required": ["asset_plan"]
        },
        function=generate_assets_impl
    )

    register_tool(
        name="validate_assets",
        description="Validate generated assets. Checks for valid data and required properties.",
        parameters={
            "type": "object",
            "properties": {
                "generated_assets": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of generated asset results"
                }
            },
            "required": ["generated_assets"]
        },
        function=validate_assets_impl
    )

    register_tool(
        name="generate_diagram_spec",
        description="Generate diagram specification from blueprint and detected zones. Creates drop zones and label chip mappings.",
        parameters={
            "type": "object",
            "properties": {
                "blueprint": {
                    "type": "object",
                    "description": "The game blueprint"
                },
                "zones": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Detected zones with positions"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of labels for the diagram"
                }
            },
            "required": ["blueprint", "zones", "labels"]
        },
        function=generate_diagram_spec_impl
    )

    register_tool(
        name="validate_diagram_spec",
        description="Validate a diagram specification. Checks zone-label matching and required fields.",
        parameters={
            "type": "object",
            "properties": {
                "diagram_spec": {
                    "type": "object",
                    "description": "The diagram spec to validate"
                }
            },
            "required": ["diagram_spec"]
        },
        function=validate_diagram_spec_impl
    )

    logger.info("Blueprint tools registered")
