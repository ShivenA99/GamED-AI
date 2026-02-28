"""
Asset Validator Agent

Validates all generated assets before final output.
Ensures all planned assets were generated, files exist, and meet requirements.

NOTE: This agent runs BEFORE blueprint_generator. It does NOT need blueprint.

Inputs: planned_assets, generated_assets
Outputs: validated_assets, validation_errors, assets_valid
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.asset_validator")


def _validate_file_exists(file_path: str) -> Tuple[bool, str]:
    """Check if a file exists and is accessible.

    Args:
        file_path: Path to the file.

    Returns:
        (success, message)
    """
    if not file_path:
        return False, "No file path provided"

    # Handle both local paths and URLs
    if file_path.startswith("http://") or file_path.startswith("https://"):
        # For URLs, we assume they're valid (could add HTTP HEAD check)
        return True, "URL asset (assumed valid)"

    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"

    if not os.path.isfile(file_path):
        return False, f"Path is not a file: {file_path}"

    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, f"File is empty: {file_path}"

    return True, f"File exists ({file_size} bytes)"


def _validate_image_dimensions(file_path: str, min_size: int = 50, max_size: int = 4096) -> Tuple[bool, str]:
    """Validate image dimensions are within acceptable range.

    Args:
        file_path: Path to the image file.
        min_size: Minimum dimension (width or height).
        max_size: Maximum dimension.

    Returns:
        (success, message)
    """
    if not file_path or file_path.startswith("http"):
        # Skip validation for URLs
        return True, "URL image (dimensions not checked)"

    try:
        from PIL import Image

        with Image.open(file_path) as img:
            width, height = img.size

            if width < min_size or height < min_size:
                return False, f"Image too small: {width}x{height} (min: {min_size})"

            if width > max_size or height > max_size:
                return False, f"Image too large: {width}x{height} (max: {max_size})"

            return True, f"Valid dimensions: {width}x{height}"

    except ImportError:
        return True, "PIL not installed, skipping dimension check"
    except Exception as e:
        return False, f"Error checking dimensions: {str(e)}"


def _validate_svg_content(content: str) -> Tuple[bool, str]:
    """Validate SVG content is well-formed.

    Args:
        content: SVG string content.

    Returns:
        (success, message)
    """
    if not content:
        return False, "Empty SVG content"

    if not content.strip().startswith("<"):
        return False, "SVG content doesn't start with <"

    if "<svg" not in content.lower():
        return False, "No <svg> tag found"

    if "</svg>" not in content.lower():
        return False, "No closing </svg> tag found"

    # Basic balanced tag check
    open_count = content.lower().count("<svg")
    close_count = content.lower().count("</svg>")
    if open_count != close_count:
        return False, f"Unbalanced SVG tags: {open_count} opens, {close_count} closes"

    return True, f"SVG valid ({len(content)} chars)"


def _validate_css_animation(css_content: str) -> Tuple[bool, str]:
    """Validate CSS animation content.

    Args:
        css_content: CSS string content.

    Returns:
        (success, message)
    """
    if not css_content:
        return False, "Empty CSS content"

    # Check for keyframes
    if "@keyframes" not in css_content:
        return False, "No @keyframes rule found"

    # Basic syntax check
    if "{" not in css_content or "}" not in css_content:
        return False, "Missing curly braces"

    # Check balanced braces
    open_count = css_content.count("{")
    close_count = css_content.count("}")
    if open_count != close_count:
        return False, f"Unbalanced braces: {open_count} opens, {close_count} closes"

    return True, f"CSS valid ({len(css_content)} chars)"


async def asset_validator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Validate all generated assets before final output.

    NOTE: This agent runs BEFORE blueprint_generator. It does NOT need blueprint.

    Inputs: planned_assets, generated_assets
    Outputs: validated_assets, validation_errors, assets_valid

    Validates:
    1. All planned assets were generated
    2. File paths exist and are accessible
    3. Image dimensions are appropriate
    4. SVG content is well-formed
    5. CSS animations are valid
    """
    planned_assets = state.get("planned_assets", [])
    generated_assets = state.get("generated_assets", [])

    # Ensure we have lists
    if not isinstance(planned_assets, list):
        planned_assets = []
    # Handle Dict format from workflow mode: convert {asset_id: result} to [result]
    if isinstance(generated_assets, dict):
        logger.info(f"Converting generated_assets from Dict ({len(generated_assets)} keys) to list format")
        normalized = []
        for aid, aval in generated_assets.items():
            if isinstance(aval, dict):
                # Workflow results use 'asset_id', normalize to 'id'
                aval.setdefault("id", aval.get("asset_id", aid))
                # Flatten data.diagram_image to top-level url/local_path for validation
                data = aval.get("data", {})
                if isinstance(data, dict):
                    if not aval.get("url"):
                        aval["url"] = data.get("diagram_image") or data.get("url")
                    if not aval.get("local_path"):
                        aval["local_path"] = data.get("diagram_image_local") or data.get("local_path")
                normalized.append(aval)
        generated_assets = normalized
    if not isinstance(generated_assets, list):
        generated_assets = []

    logger.info(f"Validating {len(generated_assets)} generated assets against {len(planned_assets)} planned")

    validation_errors: List[str] = []
    validated_assets: List[Dict[str, Any]] = []

    # Build lookup for generated assets by ID (with type check)
    generated_by_id = {
        a.get("id"): a for a in generated_assets
        if isinstance(a, dict) and a.get("id")
    }

    # Validate each planned asset was generated
    for planned in planned_assets:
        if not isinstance(planned, dict):
            logger.warning(f"Skipping non-dict planned asset: {type(planned)}")
            continue
        asset_id = planned.get("id")
        asset_type = planned.get("type", "image")

        generated = generated_by_id.get(asset_id)

        if not generated:
            # Check if asset was critical
            priority = planned.get("priority", 2)
            if priority <= 1:  # High priority
                validation_errors.append(f"Missing critical asset: {asset_id}")
            else:
                logger.warning(f"Optional asset not generated: {asset_id}")
            continue

        # Check if generation succeeded
        if not generated.get("success", False):
            error = generated.get("error", "Unknown error")
            validation_errors.append(f"Asset {asset_id} failed to generate: {error}")
            continue

        # Validate based on asset type
        asset_valid = True
        asset_messages = []

        if asset_type == "image":
            # Check file or URL exists
            url = generated.get("url")
            local_path = generated.get("local_path")
            path_to_check = local_path or url

            if path_to_check:
                valid, msg = _validate_file_exists(path_to_check)
                if not valid:
                    asset_valid = False
                    validation_errors.append(f"Asset {asset_id}: {msg}")
                else:
                    asset_messages.append(msg)

                # Check dimensions for local files
                if local_path and valid:
                    dim_valid, dim_msg = _validate_image_dimensions(local_path)
                    if not dim_valid:
                        asset_valid = False
                        validation_errors.append(f"Asset {asset_id}: {dim_msg}")
                    else:
                        asset_messages.append(dim_msg)
            else:
                validation_errors.append(f"Asset {asset_id}: No URL or local path")
                asset_valid = False

        elif asset_type == "css_animation":
            css_content = generated.get("css_content")
            if css_content:
                valid, msg = _validate_css_animation(css_content)
                if not valid:
                    asset_valid = False
                    validation_errors.append(f"Asset {asset_id}: {msg}")
                else:
                    asset_messages.append(msg)
            else:
                # CSS animations might be in keyframes
                keyframes = generated.get("keyframes")
                if not keyframes:
                    validation_errors.append(f"Asset {asset_id}: No CSS content or keyframes")
                    asset_valid = False

        elif asset_type == "svg":
            # Check for SVG content or file
            svg_content = generated.get("svg_content")
            local_path = generated.get("local_path")

            if svg_content:
                valid, msg = _validate_svg_content(svg_content)
                if not valid:
                    asset_valid = False
                    validation_errors.append(f"Asset {asset_id}: {msg}")
                else:
                    asset_messages.append(msg)
            elif local_path:
                valid, msg = _validate_file_exists(local_path)
                if not valid:
                    asset_valid = False
                    validation_errors.append(f"Asset {asset_id}: {msg}")
                else:
                    asset_messages.append(msg)
            else:
                validation_errors.append(f"Asset {asset_id}: No SVG content or file")
                asset_valid = False

        if asset_valid:
            validated_assets.append({
                **generated,
                "validation_status": "valid",
                "validation_messages": asset_messages
            })

    # NOTE: Blueprint check removed - asset_validator now runs BEFORE blueprint_generator
    # The blueprint_generator will receive validated_assets and include them in the blueprint

    # Determine overall validation result
    critical_errors = [e for e in validation_errors if "critical" in e.lower() or "failed" in e.lower()]
    assets_valid = len(critical_errors) == 0

    logger.info(
        f"Asset validation complete: {len(validated_assets)} valid, "
        f"{len(validation_errors)} errors ({len(critical_errors)} critical)"
    )

    # Track metrics if context available
    if ctx:
        if validation_errors:
            ctx.set_fallback_used(f"{len(validation_errors)} validation errors")

    return {
        "validated_assets": validated_assets,
        "validation_errors": validation_errors if validation_errors else None,
        "assets_valid": assets_valid,
    }
