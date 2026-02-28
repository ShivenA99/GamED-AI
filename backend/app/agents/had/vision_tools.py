"""
Vision Tools for HAD ZONE_PLANNER

Low-level tools for the Vision Cluster with support for:
1. Image Acquisition: Search and retrieve diagram images
2. Multi-Type Zone Detection: Polygon, bounding box, ellipse, path-based zones
3. Spatial Validation: Validate zone positions against hierarchy
4. Asset Generation: Generate game media assets

Zone Types Supported:
- circle: Simple circular zones (x, y, radius)
- ellipse: Elliptical zones (x, y, rx, ry, rotation)
- bounding_box: Rectangular zones (x, y, width, height)
- polygon: Free-form polygon zones (array of [x, y] points)
- path: SVG path-based zones for complex shapes (path string)

Note: SAM3 and DALL-E have been removed. Zone detection uses Gemini Vision
for accurate free-form zone extraction.
"""

import asyncio
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.had.vision_tools")


# =============================================================================
# Zone Type Definitions
# =============================================================================

class CircleZone(BaseModel):
    """Circular zone definition."""
    type: str = "circle"
    x: float = Field(description="Center X coordinate (0-100 percentage)")
    y: float = Field(description="Center Y coordinate (0-100 percentage)")
    radius: float = Field(description="Radius (0-100 percentage)")


class EllipseZone(BaseModel):
    """Elliptical zone definition."""
    type: str = "ellipse"
    x: float = Field(description="Center X coordinate (0-100 percentage)")
    y: float = Field(description="Center Y coordinate (0-100 percentage)")
    rx: float = Field(description="Horizontal radius (0-100 percentage)")
    ry: float = Field(description="Vertical radius (0-100 percentage)")
    rotation: float = Field(default=0, description="Rotation angle in degrees")


class BoundingBoxZone(BaseModel):
    """Rectangular bounding box zone."""
    type: str = "bounding_box"
    x: float = Field(description="Top-left X coordinate (0-100 percentage)")
    y: float = Field(description="Top-left Y coordinate (0-100 percentage)")
    width: float = Field(description="Width (0-100 percentage)")
    height: float = Field(description="Height (0-100 percentage)")


class PolygonZone(BaseModel):
    """Free-form polygon zone defined by vertices."""
    type: str = "polygon"
    points: List[List[float]] = Field(
        description="Array of [x, y] coordinate pairs forming the polygon"
    )


class PathZone(BaseModel):
    """SVG path-based zone for complex shapes."""
    type: str = "path"
    d: str = Field(description="SVG path 'd' attribute string")
    viewBox: Optional[str] = Field(default=None, description="SVG viewBox if needed")


class ZoneDefinition(BaseModel):
    """Complete zone definition with label and shape."""
    label: str = Field(description="The label/name for this zone")
    zone_type: str = Field(description="Type: circle, ellipse, bounding_box, polygon, path")
    shape: Dict[str, Any] = Field(description="Shape-specific parameters")
    hierarchy_level: Optional[int] = Field(default=None, description="Nesting level (0=root)")
    parent_label: Optional[str] = Field(default=None, description="Parent zone label if nested")
    confidence: Optional[float] = Field(default=None, description="Detection confidence 0-1")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# =============================================================================
# Tool Input/Output Schemas
# =============================================================================

class SearchImagesInput(BaseModel):
    """Input schema for search_images tool."""
    query: str = Field(description="Search query for diagram images")
    subject: str = Field(default="", description="Subject context (e.g., 'Biology')")
    num_results: int = Field(default=5, description="Number of images to retrieve")
    prefer_unlabeled: bool = Field(default=True, description="Prefer clean unlabeled diagrams")


class SearchImagesOutput(BaseModel):
    """Output schema for search_images tool."""
    success: bool
    images: List[Dict[str, Any]] = Field(default_factory=list)
    selected_image_path: Optional[str] = None
    image_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DetectZonesInput(BaseModel):
    """Input schema for detect_zones tool."""
    image_path: str = Field(description="Path to the diagram image")
    canonical_labels: List[str] = Field(description="Labels to detect")
    hierarchical_relationships: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Parent-child relationships with relationship_type"
    )
    detection_strategy: str = Field(
        default="auto",
        description="Detection strategy: 'layered' | 'discrete' | 'auto'"
    )
    preferred_zone_types: Optional[List[str]] = Field(
        default=None,
        description="Preferred zone types: polygon, bounding_box, ellipse, circle, path"
    )


class DetectZonesOutput(BaseModel):
    """Output schema for detect_zones tool."""
    success: bool
    zones: List[Dict[str, Any]] = Field(default_factory=list)
    zone_groups: List[Dict[str, Any]] = Field(default_factory=list)
    spatial_validation: Optional[Dict[str, Any]] = None
    detection_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ValidateSpatialCoherenceInput(BaseModel):
    """Input schema for validate_spatial_coherence tool."""
    zones: List[Dict[str, Any]] = Field(description="Detected zones")
    hierarchical_relationships: List[Dict[str, Any]] = Field(
        description="Parent-child relationships to validate against"
    )


class ValidateSpatialCoherenceOutput(BaseModel):
    """Output schema for validate_spatial_coherence tool."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# =============================================================================
# Asset Generation Schemas
# =============================================================================

class GenerateAssetInput(BaseModel):
    """Input schema for asset generation tools."""
    asset_type: str = Field(description="Type: background, icon, sprite, feedback, decoration")
    prompt: str = Field(description="Description of the asset to generate")
    style: str = Field(default="educational", description="Visual style")
    size: Optional[Tuple[int, int]] = Field(default=None, description="Size (width, height)")
    format: str = Field(default="png", description="Output format: png, svg, gif")


class GenerateAssetOutput(BaseModel):
    """Output schema for asset generation tools."""
    success: bool
    asset_path: Optional[str] = None
    asset_url: Optional[str] = None
    asset_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# Image Search Tool
# =============================================================================

async def search_images(
    query: str,
    subject: str = "",
    num_results: int = 5,
    prefer_unlabeled: bool = True,
) -> SearchImagesOutput:
    """
    Search for diagram images using Serper API.

    This tool searches for educational diagrams suitable for labeling games.
    It prefers clean, unlabeled diagrams when possible.
    """
    import httpx

    try:
        from app.services.image_retrieval import (
            search_diagram_images,
            select_best_image_scored,
        )

        # Enhance query with subject context
        enhanced_query = query
        if subject:
            enhanced_query = f"{subject} {enhanced_query}"

        # Add preference for unlabeled if requested
        if prefer_unlabeled:
            enhanced_query = f"{enhanced_query} unlabeled clean diagram"

        logger.info(f"Searching images: {enhanced_query}")

        # Search for images using Serper API
        results = await search_diagram_images(enhanced_query, max_results=num_results)

        if not results:
            return SearchImagesOutput(
                success=False,
                error="No images found for query"
            )

        # Select the best image using scoring
        best_image = select_best_image_scored(results, prefer_unlabeled=prefer_unlabeled)

        if not best_image:
            return SearchImagesOutput(
                success=False,
                error="No usable image found in results"
            )

        # Download the image locally
        image_url = best_image.get("image_url")
        if not image_url:
            return SearchImagesOutput(
                success=False,
                error="No image URL in result"
            )

        # Create output directory
        output_dir = os.path.join("pipeline_outputs", "retrieved_diagrams")
        os.makedirs(output_dir, exist_ok=True)

        # Download the image
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()

            # Determine extension from content type
            content_type = response.headers.get("content-type", "image/png")
            ext = "png"
            if "jpeg" in content_type or "jpg" in content_type:
                ext = "jpg"
            elif "gif" in content_type:
                ext = "gif"
            elif "webp" in content_type:
                ext = "webp"

            # Save to file
            filename = f"diagram_{uuid.uuid4().hex[:8]}.{ext}"
            local_path = os.path.join(output_dir, filename)

            with open(local_path, "wb") as f:
                f.write(response.content)

        logger.info(f"Downloaded image to: {local_path}")

        return SearchImagesOutput(
            success=True,
            images=results,
            selected_image_path=local_path,
            image_metadata={
                "source_url": best_image.get("source_url"),
                "title": best_image.get("title"),
                "format": ext,
            }
        )

    except Exception as e:
        logger.error(f"Image search failed: {e}")
        return SearchImagesOutput(
            success=False,
            error=str(e)
        )


# =============================================================================
# Zone Detection Tool (Multi-Type Support)
# =============================================================================

async def detect_zones(
    image_path: str,
    canonical_labels: List[str],
    hierarchical_relationships: Optional[List[Dict[str, Any]]] = None,
    detection_strategy: str = "auto",
    subject: str = "",
    preferred_zone_types: Optional[List[str]] = None,
) -> DetectZonesOutput:
    """
    Detect zones in a diagram with hierarchy-aware strategy.

    Supports multiple zone types for accurate free-form detection:
    - polygon: Best for irregular anatomical structures
    - bounding_box: Best for rectangular UI elements
    - ellipse: Best for circular/oval structures
    - circle: Simple circular zones
    - path: SVG paths for complex outlines

    Detection strategies:
    - 'layered': For composed_of/subdivided_into relationships (concentric/nested)
    - 'discrete': For contains/has_part relationships (separate regions)
    - 'auto': Infer from relationship_type in hierarchical_relationships
    """
    try:
        from app.agents.gemini_zone_detector import (
            detect_zones_with_gemini,
            create_zone_groups,
            validate_zone_spatial_coherence,
        )

        # Default to polygon for most accurate free-form detection
        if not preferred_zone_types:
            preferred_zone_types = ["polygon", "bounding_box", "ellipse"]

        logger.info(
            f"Detecting zones with strategy={detection_strategy}, "
            f"labels={len(canonical_labels)}, "
            f"hierarchy_groups={len(hierarchical_relationships) if hierarchical_relationships else 0}, "
            f"preferred_types={preferred_zone_types}"
        )

        # Call the enhanced zone detection with hierarchical context
        result = await detect_zones_with_gemini(
            image_path=image_path,
            canonical_labels=canonical_labels,
            subject=subject,
            hierarchical_relationships=hierarchical_relationships,
            preferred_zone_types=preferred_zone_types,
        )

        if not result.get("success"):
            return DetectZonesOutput(
                success=False,
                error=result.get("error", "Zone detection failed")
            )

        zones = result.get("zones", [])

        # Enhance zones with type information if not present
        for zone in zones:
            if "zone_type" not in zone:
                # Infer type from shape data
                if "points" in zone:
                    zone["zone_type"] = "polygon"
                elif "d" in zone:
                    zone["zone_type"] = "path"
                elif "width" in zone and "height" in zone:
                    zone["zone_type"] = "bounding_box"
                elif "rx" in zone and "ry" in zone:
                    zone["zone_type"] = "ellipse"
                else:
                    zone["zone_type"] = "circle"

        # Create zone groups from hierarchical relationships
        zone_groups = create_zone_groups(hierarchical_relationships, zones)

        # Validate spatial coherence
        is_valid, errors = validate_zone_spatial_coherence(
            zones, hierarchical_relationships
        )

        spatial_validation = {
            "is_valid": is_valid,
            "errors": [e for e in errors if "ERROR" in e],
            "warnings": [e for e in errors if "WARNING" in e],
        }

        detection_metadata = {
            "strategy": detection_strategy,
            "zone_types_detected": list(set(z.get("zone_type", "circle") for z in zones)),
            "total_zones": len(zones),
            "total_groups": len(zone_groups),
        }

        return DetectZonesOutput(
            success=True,
            zones=zones,
            zone_groups=zone_groups,
            spatial_validation=spatial_validation,
            detection_metadata=detection_metadata,
        )

    except Exception as e:
        logger.error(f"Zone detection failed: {e}", exc_info=True)
        return DetectZonesOutput(
            success=False,
            error=str(e)
        )


# =============================================================================
# Spatial Validation Tool
# =============================================================================

async def validate_spatial_coherence(
    zones: List[Dict[str, Any]],
    hierarchical_relationships: List[Dict[str, Any]],
) -> ValidateSpatialCoherenceOutput:
    """
    Validate that detected zones match hierarchical relationship expectations.

    Checks:
    - For 'composed_of': Children should be within/overlapping parent
    - For 'contains': Children should be within parent boundary
    - For 'has_part': Children can be discrete but near parent
    """
    try:
        from app.agents.gemini_zone_detector import validate_zone_spatial_coherence

        is_valid, errors = validate_zone_spatial_coherence(
            zones, hierarchical_relationships
        )

        # Separate errors and warnings
        error_list = [e for e in errors if "ERROR" in e]
        warning_list = [e for e in errors if "WARNING" in e]

        # Generate suggestions based on errors
        suggestions = []
        for error in error_list:
            if "too far from parent" in error.lower():
                suggestions.append(
                    "The child zones appear scattered. For layered structures, "
                    "re-detect with explicit instruction that children are LAYERS "
                    "within the parent boundary, not discrete scattered parts."
                )
            if "large spread" in error.lower():
                suggestions.append(
                    "Child zones have too much spread for layered structures. "
                    "They should be at similar positions (overlapping/concentric)."
                )
            if "outside parent" in error.lower():
                suggestions.append(
                    "Some child zones are outside the parent boundary. "
                    "Use polygon zone type for more accurate boundary detection."
                )

        return ValidateSpatialCoherenceOutput(
            is_valid=is_valid,
            errors=error_list,
            warnings=warning_list,
            suggestions=suggestions,
        )

    except Exception as e:
        logger.error(f"Spatial validation failed: {e}")
        return ValidateSpatialCoherenceOutput(
            is_valid=False,
            errors=[f"Validation error: {str(e)}"]
        )


# =============================================================================
# Asset Generation Tools
# =============================================================================

async def generate_game_asset(
    asset_type: str,
    prompt: str,
    style: str = "educational",
    size: Optional[Tuple[int, int]] = None,
    output_format: str = "png",
) -> GenerateAssetOutput:
    """
    Generate game media assets using available generation services.

    Asset types:
    - background: Scene background images
    - icon: UI icons (checkmark, X, arrows, etc.)
    - sprite: Game character/object sprites
    - feedback: Feedback visuals (correct/incorrect indicators)
    - decoration: Decorative elements
    - label_tag: Label tags for drag-and-drop

    Uses configured image generation service (Gemini Imagen, etc.)
    Falls back to placeholder generation if no service available.
    """
    try:
        output_dir = os.path.join("pipeline_outputs", "generated_assets", asset_type)
        os.makedirs(output_dir, exist_ok=True)

        filename = f"{asset_type}_{uuid.uuid4().hex[:8]}.{output_format}"
        output_path = os.path.join(output_dir, filename)

        # Try to use available generation service
        generated = False

        # Check for Gemini Imagen service
        try:
            from app.services.media_generation_service import MediaGenerationService
            service = MediaGenerationService()

            result = await service.generate_image(
                prompt=f"{style} style {asset_type}: {prompt}",
                size=size or (512, 512),
                output_path=output_path,
            )

            if result.get("success"):
                generated = True
                output_path = result.get("path", output_path)

        except ImportError:
            logger.debug("MediaGenerationService not available, trying fallback")
        except Exception as e:
            logger.warning(f"Media generation service failed: {e}")

        # Fallback: Create SVG placeholder for certain types
        if not generated and output_format == "svg":
            svg_content = _create_placeholder_svg(asset_type, prompt, size or (100, 100))
            output_path = output_path.replace(f".{output_format}", ".svg")
            with open(output_path, "w") as f:
                f.write(svg_content)
            generated = True

        # Fallback: Return placeholder info
        if not generated:
            return GenerateAssetOutput(
                success=True,
                asset_path=None,
                asset_type=asset_type,
                metadata={
                    "placeholder": True,
                    "prompt": prompt,
                    "style": style,
                    "message": "Asset generation service not available. Use placeholder or external asset."
                }
            )

        return GenerateAssetOutput(
            success=True,
            asset_path=output_path,
            asset_type=asset_type,
            metadata={
                "prompt": prompt,
                "style": style,
                "size": size,
                "format": output_format,
            }
        )

    except Exception as e:
        logger.error(f"Asset generation failed: {e}")
        return GenerateAssetOutput(
            success=False,
            error=str(e)
        )


def _create_placeholder_svg(asset_type: str, prompt: str, size: Tuple[int, int]) -> str:
    """Create a placeholder SVG for assets when generation is unavailable."""
    width, height = size

    # Different placeholders based on asset type
    if asset_type == "icon":
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#f0f0f0" stroke="#ccc" stroke-width="2"/>
  <text x="{width/2}" y="{height/2}" text-anchor="middle" dominant-baseline="middle" font-size="12" fill="#666">
    {asset_type[:10]}
  </text>
</svg>'''

    elif asset_type == "feedback":
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <circle cx="{width/2}" cy="{height/2}" r="{min(width, height)/3}" fill="#4CAF50" opacity="0.3"/>
  <text x="{width/2}" y="{height/2}" text-anchor="middle" dominant-baseline="middle" font-size="16" fill="#4CAF50">
    ✓
  </text>
</svg>'''

    elif asset_type == "label_tag":
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="2" y="2" width="{width-4}" height="{height-4}" rx="4" fill="#fff" stroke="#2196F3" stroke-width="2"/>
  <text x="{width/2}" y="{height/2}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="#333">
    Label
  </text>
</svg>'''

    else:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#e0e0e0"/>
  <text x="{width/2}" y="{height/2}" text-anchor="middle" dominant-baseline="middle" font-size="10" fill="#999">
    {asset_type}
  </text>
</svg>'''


async def generate_background(
    theme: str,
    subject: str = "",
    style: str = "educational",
    size: Tuple[int, int] = (1920, 1080),
) -> GenerateAssetOutput:
    """Generate a background image for the game scene."""
    prompt = f"{theme} background for {subject}" if subject else f"{theme} background"
    return await generate_game_asset(
        asset_type="background",
        prompt=prompt,
        style=style,
        size=size,
    )


async def generate_ui_icon(
    icon_type: str,
    style: str = "flat",
    size: Tuple[int, int] = (48, 48),
) -> GenerateAssetOutput:
    """Generate UI icons for game interface."""
    icon_prompts = {
        "checkmark": "green checkmark success icon",
        "cross": "red X error icon",
        "arrow_left": "left arrow navigation icon",
        "arrow_right": "right arrow navigation icon",
        "hint": "lightbulb hint icon",
        "reset": "circular reset refresh icon",
        "submit": "submit button icon",
        "drag": "drag handle grip icon",
    }
    prompt = icon_prompts.get(icon_type, f"{icon_type} icon")
    return await generate_game_asset(
        asset_type="icon",
        prompt=prompt,
        style=style,
        size=size,
        output_format="svg",
    )


async def generate_feedback_visual(
    feedback_type: str,
    style: str = "animated",
) -> GenerateAssetOutput:
    """Generate feedback visuals for correct/incorrect responses."""
    feedback_prompts = {
        "correct": "green glowing checkmark celebration animation",
        "incorrect": "red gentle X shake animation",
        "partial": "yellow amber partial success indicator",
        "hint_reveal": "subtle glow highlight effect",
        "progress": "progress bar filling animation",
    }
    prompt = feedback_prompts.get(feedback_type, f"{feedback_type} feedback visual")
    return await generate_game_asset(
        asset_type="feedback",
        prompt=prompt,
        style=style,
        size=(120, 120),
        output_format="svg",
    )


# =============================================================================
# Tool Registry for HAD
# =============================================================================

VISION_TOOLS = {
    "search_images": {
        "function": search_images,
        "input_schema": SearchImagesInput,
        "output_schema": SearchImagesOutput,
        "description": "Search for diagram images using web search",
    },
    "detect_zones": {
        "function": detect_zones,
        "input_schema": DetectZonesInput,
        "output_schema": DetectZonesOutput,
        "description": "Detect clickable zones with multi-type support (polygon, bbox, ellipse, path)",
    },
    "validate_spatial_coherence": {
        "function": validate_spatial_coherence,
        "input_schema": ValidateSpatialCoherenceInput,
        "output_schema": ValidateSpatialCoherenceOutput,
        "description": "Validate zone positions against hierarchical relationships",
    },
    "generate_game_asset": {
        "function": generate_game_asset,
        "input_schema": GenerateAssetInput,
        "output_schema": GenerateAssetOutput,
        "description": "Generate game media assets (backgrounds, icons, sprites)",
    },
    "generate_background": {
        "function": generate_background,
        "input_schema": None,
        "output_schema": GenerateAssetOutput,
        "description": "Generate scene background images",
    },
    "generate_ui_icon": {
        "function": generate_ui_icon,
        "input_schema": None,
        "output_schema": GenerateAssetOutput,
        "description": "Generate UI icons (checkmark, arrows, hints)",
    },
    "generate_feedback_visual": {
        "function": generate_feedback_visual,
        "input_schema": None,
        "output_schema": GenerateAssetOutput,
        "description": "Generate feedback visuals for correct/incorrect responses",
    },
}
