"""
Asset Spec — Constraints for generating game assets.

Every asset in the AssetGraph gets a spec BEFORE generation. Specs encode
dimensional, style, positional, and content constraints that keep all assets
in sync. The asset_spec_builder creates these from the GameDesignV3; the
asset_orchestrator reads them to delegate to the correct worker.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssetType(str, Enum):
    """What kind of asset this is."""
    DIAGRAM = "diagram"                  # Primary diagram image
    BACKGROUND = "background"            # Scene background layer
    ZONE_OVERLAY = "zone_overlay"        # Zone boundary overlay
    SPRITE = "sprite"                    # 2D sprite with transparency
    OVERLAY = "overlay"                  # Decorative overlay
    DECORATION = "decoration"            # Floating decoration element
    SVG = "svg"                          # Vector graphic element
    LOTTIE = "lottie"                    # Lottie animation JSON
    CSS_ANIMATION = "css_animation"      # CSS keyframe animation
    SOUND_EFFECT = "sound_effect"        # Audio SFX
    GIF = "gif"                          # Animated GIF
    PATH_DATA = "path_data"             # Trace path waypoints
    CLICK_TARGETS = "click_targets"     # Click-to-identify targets


class WorkerType(str, Enum):
    """Which worker handles generation."""
    IMAGEN = "imagen_worker"                    # Google Imagen 4
    GEMINI_IMAGE = "gemini_image_worker"        # Gemini Flash Image (editing, blending)
    ZONE_DETECTOR = "zone_detector_worker"      # Gemini Flash vision
    CSS_ANIMATION = "css_animation_worker"      # Deterministic CSS generation
    SVG_RENDERER = "svg_renderer_worker"        # Programmatic SVG / Recraft V3
    LOTTIE_GEN = "lottie_worker"                # LottieFiles / Recraft Lottie
    AUDIO_GEN = "audio_worker"                  # ElevenLabs SFX
    PATH_GEN = "path_worker"                    # Gemini vision + zone centers
    CLICK_TARGET_GEN = "click_target_worker"    # Deterministic transform
    IMAGE_SEARCH = "image_search_worker"        # Web image search
    SPRITE_GEN = "sprite_worker"                # Imagen 4 with transparency
    NOOP = "noop"                               # No generation needed (cached/preset)


# Default routing: asset_type -> preferred worker
ASSET_TYPE_TO_WORKER: Dict[AssetType, WorkerType] = {
    AssetType.DIAGRAM: WorkerType.IMAGE_SEARCH,  # search first, generate fallback
    AssetType.BACKGROUND: WorkerType.IMAGEN,
    AssetType.ZONE_OVERLAY: WorkerType.ZONE_DETECTOR,
    AssetType.SPRITE: WorkerType.SPRITE_GEN,
    AssetType.OVERLAY: WorkerType.IMAGEN,
    AssetType.DECORATION: WorkerType.IMAGEN,
    AssetType.SVG: WorkerType.SVG_RENDERER,
    AssetType.LOTTIE: WorkerType.LOTTIE_GEN,
    AssetType.CSS_ANIMATION: WorkerType.CSS_ANIMATION,
    AssetType.SOUND_EFFECT: WorkerType.AUDIO_GEN,
    AssetType.GIF: WorkerType.GEMINI_IMAGE,
    AssetType.PATH_DATA: WorkerType.PATH_GEN,
    AssetType.CLICK_TARGETS: WorkerType.CLICK_TARGET_GEN,
}


class DimensionSpec(BaseModel):
    """Dimensional constraints ensuring assets fit together."""
    model_config = ConfigDict(extra="allow")

    width: Optional[int] = None           # Exact pixels
    height: Optional[int] = None
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    aspect_ratio: Optional[str] = None    # "4:3", "16:9", "1:1"

    # Relative sizing
    scale_relative_to: Optional[str] = None   # asset_id to scale relative to
    scale_factor: Optional[float] = None      # 0.0-1.0 multiplier


class PositionSpec(BaseModel):
    """Positional constraints for placing an asset."""
    model_config = ConfigDict(extra="allow")

    # Percentage-based (0-100), relative to parent container
    x_percent: Optional[float] = None
    y_percent: Optional[float] = None
    z_index: int = 0

    # Anchor point for positioning
    anchor: str = "center"  # center, top_left, top_right, bottom_left, bottom_right

    # Relative positioning
    relative_to: Optional[str] = None  # Position relative to this asset_id
    offset_x: float = 0.0
    offset_y: float = 0.0


class StyleSpec(BaseModel):
    """Style constraints ensuring visual consistency across assets."""
    model_config = ConfigDict(extra="allow")

    color_palette: Optional[Dict[str, str]] = None  # Inherited from theme
    visual_tone: Optional[str] = None
    transparency: bool = False

    # For image generation: prompt modifiers
    style_prompt_suffix: Optional[str] = None
    negative_prompt: Optional[str] = None

    # Consistency reference: match style of another asset
    reference_asset_id: Optional[str] = None
    reference_image_path: Optional[str] = None


class ContentSpec(BaseModel):
    """Content requirements from the game design."""
    model_config = ConfigDict(extra="allow")

    description: str = ""
    required_elements: List[str] = Field(default_factory=list)
    generation_prompt: Optional[str] = None

    # For zone detection
    zone_labels: List[str] = Field(default_factory=list)
    zone_hints: Dict[str, str] = Field(default_factory=dict)  # label -> hint

    # For animations
    animation_type: Optional[str] = None
    duration_ms: Optional[int] = None
    easing: Optional[str] = None
    trigger: Optional[str] = None
    particle_config: Optional[Dict[str, Any]] = None

    # For audio
    sound_event: Optional[str] = None
    sound_description: Optional[str] = None

    # For paths
    waypoint_labels: List[str] = Field(default_factory=list)
    path_type: Optional[str] = None

    # For click targets
    click_options: List[str] = Field(default_factory=list)
    correct_assignments: Dict[str, str] = Field(default_factory=dict)


class AssetSpec(BaseModel):
    """Complete specification for generating a single asset.

    Created by asset_spec_builder from GameDesignV3.
    Consumed by asset_orchestrator workers.
    """
    model_config = ConfigDict(extra="allow")

    asset_id: str
    asset_type: AssetType
    graph_node_id: str  # corresponding node in AssetGraph

    # Constraints
    dimensions: DimensionSpec = Field(default_factory=DimensionSpec)
    position: Optional[PositionSpec] = None
    style: StyleSpec = Field(default_factory=StyleSpec)
    content: ContentSpec = Field(default_factory=ContentSpec)

    # Generation routing
    worker: WorkerType = WorkerType.NOOP
    fallback_worker: Optional[WorkerType] = None
    priority: int = 0  # Higher = generate earlier (within same dependency level)

    # Dependencies
    depends_on: List[str] = Field(default_factory=list)  # asset_ids that must exist first
    scene_number: Optional[int] = None

    # Status (updated during generation)
    status: str = "pending"  # pending, generating, completed, failed
    generated_path: Optional[str] = None
    served_url: Optional[str] = None
    error: Optional[str] = None
    generation_metrics: Dict[str, Any] = Field(default_factory=dict)


class AssetManifest(BaseModel):
    """Collection of all AssetSpecs for a game, with generation metadata."""
    model_config = ConfigDict(extra="allow")

    game_id: str
    specs: Dict[str, AssetSpec] = Field(default_factory=dict)  # asset_id -> spec
    generation_order: List[str] = Field(default_factory=list)  # asset_ids in order
    total_estimated_cost: float = 0.0
    total_estimated_time_seconds: float = 0.0

    def add_spec(self, spec: AssetSpec) -> None:
        self.specs[spec.asset_id] = spec

    def get_spec(self, asset_id: str) -> Optional[AssetSpec]:
        return self.specs.get(asset_id)

    def get_specs_by_type(self, asset_type: AssetType) -> List[AssetSpec]:
        return [s for s in self.specs.values() if s.asset_type == asset_type]

    def get_specs_for_scene(self, scene_number: int) -> List[AssetSpec]:
        return [s for s in self.specs.values() if s.scene_number == scene_number]

    def get_pending_specs(self) -> List[AssetSpec]:
        return [s for s in self.specs.values() if s.status == "pending"]

    def get_completed_specs(self) -> List[AssetSpec]:
        return [s for s in self.specs.values() if s.status == "completed"]

    def mark_completed(self, asset_id: str, path: str, url: Optional[str] = None) -> None:
        spec = self.specs.get(asset_id)
        if spec:
            spec.status = "completed"
            spec.generated_path = path
            spec.served_url = url

    def mark_failed(self, asset_id: str, error: str) -> None:
        spec = self.specs.get(asset_id)
        if spec:
            spec.status = "failed"
            spec.error = error


# ---------------------------------------------------------------------------
# Cost estimation helpers
# ---------------------------------------------------------------------------

WORKER_COST_ESTIMATES: Dict[WorkerType, float] = {
    WorkerType.IMAGEN: 0.02,
    WorkerType.GEMINI_IMAGE: 0.04,
    WorkerType.ZONE_DETECTOR: 0.01,
    WorkerType.CSS_ANIMATION: 0.0,
    WorkerType.SVG_RENDERER: 0.08,
    WorkerType.LOTTIE_GEN: 0.08,
    WorkerType.AUDIO_GEN: 0.01,
    WorkerType.PATH_GEN: 0.01,
    WorkerType.CLICK_TARGET_GEN: 0.0,
    WorkerType.IMAGE_SEARCH: 0.0,
    WorkerType.SPRITE_GEN: 0.04,
    WorkerType.NOOP: 0.0,
}


def estimate_manifest_cost(manifest: AssetManifest) -> float:
    """Estimate total generation cost for a manifest."""
    total = 0.0
    for spec in manifest.specs.values():
        total += WORKER_COST_ESTIMATES.get(spec.worker, 0.0)
    return total
