"""
Asset Capability Manifest

Machine-readable capability manifest that agents reason about to plan
optimal asset generation strategies for educational games.

Each capability defines:
- What it can generate
- Best use cases
- Latency characteristics
- Status (production/experimental)

This enables truly agentic asset generation - agents reason about
WHAT methods to use based on context and constraints.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field


class GenerationStatus(Enum):
    """Implementation status of a generation method."""
    PRODUCTION = "production"       # Fully implemented and tested
    PARTIAL = "partial"             # Partially implemented
    EXPERIMENTAL = "experimental"   # In development
    UNAVAILABLE = "unavailable"     # Not available in current environment


class LatencyCategory(Enum):
    """Latency category for generation methods."""
    INSTANT = "instant"   # < 100ms
    FAST = "fast"         # 100ms - 1s
    MEDIUM = "medium"     # 1s - 10s
    SLOW = "slow"         # > 10s


@dataclass
class GenerationMethod:
    """Definition of an asset generation method."""
    id: str
    name: str
    description: str
    supports: List[str]          # Supported output formats
    best_for: List[str]          # Best use cases
    latency: LatencyCategory
    status: GenerationStatus
    max_size: Optional[tuple] = None   # Max dimensions (width, height) or None for unlimited
    requires_api_key: Optional[str] = None
    configuration_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetType:
    """Definition of an asset type."""
    id: str
    name: str
    description: str
    preferred_methods: List[str]     # Ordered list of preferred generation methods
    typical_size: Optional[tuple] = None
    required: bool = True
    supports_transparency: bool = False
    configuration_options: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# GENERATION METHODS
# =============================================================================

GENERATION_METHODS: Dict[str, GenerationMethod] = {
    "nanobanana": GenerationMethod(
        id="nanobanana",
        name="Nanobanana Image Generation",
        description="AI image generation via nanobanana service for educational content",
        supports=["png", "jpg"],
        best_for=[
            "backgrounds",
            "sprites",
            "characters",
            "objects",
            "educational diagrams",
            "scene illustrations"
        ],
        latency=LatencyCategory.MEDIUM,
        status=GenerationStatus.PRODUCTION,  # Now integrated into media_generation_service
        max_size=(1024, 1024),
        requires_api_key="NANOBANANA_API_KEY",
        configuration_options={
            "style_hints": True,
            "negative_prompt": True,
            "seed": True
        }
    ),

    "svg_renderer": GenerationMethod(
        id="svg_renderer",
        name="Programmatic SVG Generation",
        description="Generate SVG graphics programmatically for overlays and UI elements",
        supports=["svg"],
        best_for=[
            "zone_overlays",
            "diagrams",
            "ui_elements",
            "icons",
            "shapes",
            "interactive regions"
        ],
        latency=LatencyCategory.FAST,
        status=GenerationStatus.PRODUCTION,
        max_size=None,  # Vector graphics, unlimited
        configuration_options={
            "stroke_width": True,
            "fill_opacity": True,
            "animation": True
        }
    ),

    "png_converter": GenerationMethod(
        id="png_converter",
        name="SVG to PNG Converter",
        description="Convert SVG graphics to PNG format via cairosvg",
        supports=["png"],
        best_for=[
            "zone_overlays_as_png",
            "rasterized_graphics",
            "compatibility_output"
        ],
        latency=LatencyCategory.FAST,
        status=GenerationStatus.PRODUCTION,
        configuration_options={
            "scale": True,
            "background_color": True
        }
    ),

    "gif_generator": GenerationMethod(
        id="gif_generator",
        name="Animated GIF Generator",
        description="Create animated GIFs from frame sequences for hints and feedback",
        supports=["gif"],
        best_for=[
            "hint_animations",
            "flow_demos",
            "feedback_animations",
            "progress_indicators",
            "tutorial_animations"
        ],
        latency=LatencyCategory.MEDIUM,
        status=GenerationStatus.PRODUCTION,
        max_size=(512, 512),
        configuration_options={
            "max_frames": 30,
            "frame_duration_ms": 100,
            "loop": True
        }
    ),

    "css_animation": GenerationMethod(
        id="css_animation",
        name="CSS Keyframe Animations",
        description="Generate CSS keyframe animations for hover effects and feedback",
        supports=["css"],
        best_for=[
            "hover_effects",
            "pulse",
            "glow",
            "shake",
            "bounce",
            "feedback_animations"
        ],
        latency=LatencyCategory.INSTANT,
        status=GenerationStatus.PRODUCTION,
        configuration_options={
            "animation_type": ["pulse", "glow", "shake", "bounce", "fade"],
            "duration_ms": True,
            "iteration_count": True
        }
    ),

    "url_fetch": GenerationMethod(
        id="url_fetch",
        name="URL Fetch and Cache",
        description="Fetch existing images from URLs and cache locally",
        supports=["png", "jpg", "gif", "svg", "webp"],
        best_for=[
            "existing_assets",
            "stock_images",
            "retrieved_diagrams",
            "external_resources"
        ],
        latency=LatencyCategory.MEDIUM,  # Depends on source
        status=GenerationStatus.PRODUCTION,
        configuration_options={
            "cache_duration_hours": 24,
            "fallback_url": True
        }
    ),

    "cached": GenerationMethod(
        id="cached",
        name="Cached Asset Retrieval",
        description="Retrieve previously generated or cached assets",
        supports=["png", "jpg", "gif", "svg", "webp", "css"],
        best_for=[
            "repeated_assets",
            "common_icons",
            "ui_elements"
        ],
        latency=LatencyCategory.INSTANT,
        status=GenerationStatus.PRODUCTION,
        configuration_options={}
    ),

    "gemini_imagen": GenerationMethod(
        id="gemini_imagen",
        name="Gemini Imagen (Deprecated)",
        description="DEPRECATED: Use nanobanana instead. Not implemented in media_generation_service.",
        supports=["png", "jpg"],
        best_for=[],  # Deprecated - don't use
        latency=LatencyCategory.MEDIUM,
        status=GenerationStatus.UNAVAILABLE,  # Not implemented - use nanobanana
        max_size=(1024, 1024),
        requires_api_key="GOOGLE_API_KEY",
        configuration_options={}
    ),
}


# =============================================================================
# ASSET TYPES
# =============================================================================

ASSET_TYPES: Dict[str, AssetType] = {
    "background_image": AssetType(
        id="background_image",
        name="Background Image",
        description="Full scene background for game canvas",
        preferred_methods=["url_fetch", "nanobanana", "cached"],
        typical_size=(800, 600),
        required=True,
        supports_transparency=False,
        configuration_options={
            "aspect_ratio": "4:3",
            "style": "educational"
        }
    ),

    "zone_overlay": AssetType(
        id="zone_overlay",
        name="Zone Overlay",
        description="Interactive zone markers overlay on diagram",
        preferred_methods=["svg_renderer", "png_converter"],
        typical_size=None,  # Matches diagram size
        required=True,
        supports_transparency=True,
        configuration_options={
            "zone_shape": ["circle", "polygon", "rectangle"],
            "fill_opacity": 0.3,
            "stroke_width": 2
        }
    ),

    "sprite": AssetType(
        id="sprite",
        name="Game Sprite",
        description="Individual game object, character, or item",
        preferred_methods=["nanobanana", "url_fetch", "cached"],
        typical_size=(128, 128),
        required=False,
        supports_transparency=True,
        configuration_options={
            "animation_frames": False
        }
    ),

    "icon": AssetType(
        id="icon",
        name="UI Icon",
        description="Small icon for UI elements and controls",
        preferred_methods=["svg_renderer", "cached", "url_fetch"],
        typical_size=(32, 32),
        required=False,
        supports_transparency=True,
        configuration_options={}
    ),

    "hint_animation": AssetType(
        id="hint_animation",
        name="Hint Animation",
        description="Animated hint showing expected interaction",
        preferred_methods=["gif_generator", "css_animation"],
        typical_size=(256, 256),
        required=False,
        supports_transparency=True,
        configuration_options={
            "max_duration_seconds": 3,
            "hint_style": ["drag_arrow", "pulse_highlight", "path_trace"]
        }
    ),

    "feedback_animation": AssetType(
        id="feedback_animation",
        name="Feedback Animation",
        description="Visual feedback for correct/incorrect responses",
        preferred_methods=["css_animation", "gif_generator"],
        typical_size=None,  # Applied to zone
        required=False,
        supports_transparency=True,
        configuration_options={
            "feedback_type": ["success", "error", "partial"]
        }
    ),

    "diagram_image": AssetType(
        id="diagram_image",
        name="Diagram Image",
        description="Primary educational diagram for the game",
        preferred_methods=["url_fetch", "nanobanana", "cached"],
        typical_size=(800, 600),
        required=True,
        supports_transparency=False,
        configuration_options={
            "diagram_style": ["clean", "labeled", "annotated"]
        }
    ),
}


# =============================================================================
# PRACTICAL LIMITS
# =============================================================================

PRACTICAL_LIMITS = {
    "max_assets_per_scene": 10,
    "max_generated_images_per_game": 5,  # AI generation has latency
    "max_gif_frames": 30,
    "recommended_total_assets": 15,
    "max_svg_complexity": 1000,  # Max nodes in SVG
    "max_file_size_kb": 500,

    # What to avoid
    "avoid": [
        "video_generation",       # Not supported
        "3d_models",              # Not supported
        "audio_generation",       # Not supported
        "complex_animations",     # Use CSS for simple, GIF for complex
        "real_photos_of_people",  # Privacy/ethical concerns
    ],

    # Budget allocation per game
    "latency_budget_ms": 30000,  # 30 seconds total for all asset generation
    "ai_generation_budget": 3,   # Max AI-generated images per game
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_generation_method(method_id: str) -> Optional[GenerationMethod]:
    """Get a generation method by ID."""
    return GENERATION_METHODS.get(method_id)


def get_asset_type(asset_type_id: str) -> Optional[AssetType]:
    """Get an asset type by ID."""
    return ASSET_TYPES.get(asset_type_id)


def get_methods_for_asset_type(asset_type_id: str) -> List[GenerationMethod]:
    """Get available generation methods for an asset type, in preference order."""
    asset_type = get_asset_type(asset_type_id)
    if not asset_type:
        return []

    methods = []
    for method_id in asset_type.preferred_methods:
        method = get_generation_method(method_id)
        if method and method.status != GenerationStatus.UNAVAILABLE:
            methods.append(method)
    return methods


def get_available_methods() -> List[GenerationMethod]:
    """Get all production-ready generation methods."""
    return [
        m for m in GENERATION_METHODS.values()
        if m.status in [GenerationStatus.PRODUCTION, GenerationStatus.PARTIAL]
    ]


def get_methods_by_latency(max_latency: LatencyCategory) -> List[GenerationMethod]:
    """Get methods that meet a latency requirement."""
    latency_order = [
        LatencyCategory.INSTANT,
        LatencyCategory.FAST,
        LatencyCategory.MEDIUM,
        LatencyCategory.SLOW
    ]

    max_idx = latency_order.index(max_latency)
    acceptable = set(latency_order[:max_idx + 1])

    return [m for m in GENERATION_METHODS.values() if m.latency in acceptable]


def format_capabilities_for_prompt() -> str:
    """
    Format the asset capabilities for inclusion in LLM prompts.

    Returns a concise description suitable for agent reasoning.
    """
    lines = ["=== ASSET GENERATION CAPABILITIES ===\n"]

    lines.append("## Available Generation Methods:\n")
    for method in GENERATION_METHODS.values():
        status_tag = f"[{method.status.value.upper()}]"
        lines.append(f"- {method.name} ({method.id}) {status_tag}")
        lines.append(f"  Outputs: {', '.join(method.supports)}")
        lines.append(f"  Best for: {', '.join(method.best_for[:3])}")
        lines.append(f"  Latency: {method.latency.value}")
        lines.append("")

    lines.append("\n## Asset Types:\n")
    for asset_type in ASSET_TYPES.values():
        required_tag = "[REQUIRED]" if asset_type.required else "[OPTIONAL]"
        lines.append(f"- {asset_type.name} ({asset_type.id}) {required_tag}")
        lines.append(f"  Methods: {', '.join(asset_type.preferred_methods[:3])}")
        lines.append("")

    lines.append("\n## Practical Limits:\n")
    lines.append(f"- Max AI-generated images per game: {PRACTICAL_LIMITS['max_generated_images_per_game']}")
    lines.append(f"- Max assets per scene: {PRACTICAL_LIMITS['max_assets_per_scene']}")
    lines.append(f"- Latency budget: {PRACTICAL_LIMITS['latency_budget_ms']}ms")
    lines.append(f"- Avoid: {', '.join(PRACTICAL_LIMITS['avoid'][:3])}")

    return "\n".join(lines)


def get_capability_summary() -> Dict[str, Any]:
    """Get a summary of asset capabilities for debugging/monitoring."""
    return {
        "total_methods": len(GENERATION_METHODS),
        "production_methods": len(get_available_methods()),
        "asset_types": len(ASSET_TYPES),
        "required_assets": [
            at.id for at in ASSET_TYPES.values() if at.required
        ],
        "practical_limits": PRACTICAL_LIMITS
    }
