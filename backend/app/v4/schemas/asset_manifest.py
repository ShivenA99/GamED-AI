"""Asset schemas — asset pipeline input/output types for the 3-stage cascade.

Phase 3a: Asset Needs (deterministic analysis) → Art Direction (LLM)
Phase 3b: Asset Chains (execution) → Asset Results
"""

from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


# ── Asset Needs (deterministic, from asset_needs_analyzer) ───────

class DiagramAssetNeed(BaseModel):
    """What diagram is needed (determined by content, not yet art-directed)."""

    asset_id: str
    scene_id: str
    expected_labels: list[str]
    image_description: str = ""
    needs_zone_detection: bool = True


class ItemImageNeed(BaseModel):
    """An item-level image need (sequencing items, etc.)."""

    asset_id: str
    item_id: str
    description: str
    mechanic_id: str


class NodeImageNeed(BaseModel):
    """A node illustration need (branching scenario nodes)."""

    asset_id: str
    node_id: str
    description: str
    mechanic_id: str


class ColorPaletteNeed(BaseModel):
    """A color palette need (sorting categories, compare contrast)."""

    asset_id: str
    count: int
    category_labels: list[str] = Field(default_factory=list)
    mechanic_id: str


class AssetNeeds(BaseModel):
    """What assets are needed for a scene (deterministic analysis)."""

    scene_id: str
    primary_diagram: Optional[DiagramAssetNeed] = None
    second_diagram: Optional[DiagramAssetNeed] = None
    item_images: list[ItemImageNeed] = Field(default_factory=list)
    node_illustrations: list[NodeImageNeed] = Field(default_factory=list)
    color_palettes: list[ColorPaletteNeed] = Field(default_factory=list)


# ── Art Direction (from asset_art_director LLM) ─────────────────

class ArtDirectedDiagram(BaseModel):
    """Crafted search + style for one diagram asset."""

    asset_id: str
    search_queries: list[str] = Field(min_length=1)
    style_prompt: str
    spatial_guidance: str = ""
    color_direction: dict[str, str] = Field(default_factory=dict)
    annotation_preference: str = "clean_unlabeled"
    negative_prompt: str = ""
    expected_labels: list[str] = Field(default_factory=list)


class ArtDirectedItemImage(BaseModel):
    """Crafted search + style for item card images."""

    asset_id: str
    item_id: str
    search_query: str
    style_prompt: str
    size_hint: str = "thumbnail"


class ArtDirectedColorPalette(BaseModel):
    """Curated color palette matching scene aesthetic."""

    asset_id: str
    theme: str = "categorical"
    colors: dict[str, str] = Field(default_factory=dict)
    rationale: str = ""


class ArtDirectedManifest(BaseModel):
    """Complete art direction for one scene's assets."""

    scene_id: str
    visual_theme: str = ""
    primary_diagram: Optional[ArtDirectedDiagram] = None
    second_diagram: Optional[ArtDirectedDiagram] = None
    item_images: list[ArtDirectedItemImage] = Field(default_factory=list)
    node_illustrations: list[ArtDirectedItemImage] = Field(default_factory=list)
    color_palettes: list[ArtDirectedColorPalette] = Field(default_factory=list)


# ── Asset Results (from asset chains) ───────────────────────────

class DetectedZone(BaseModel):
    """A single detected zone from zone detection."""

    id: str
    label: str
    shape: str = "polygon"
    coordinates: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0


class ZoneMatchReport(BaseModel):
    """Report of zone matching between detected and expected."""

    matched: list[dict[str, Any]] = Field(default_factory=list)
    unmatched_spec: list[str] = Field(default_factory=list)
    unmatched_detected: list[str] = Field(default_factory=list)


class DiagramAssetResult(BaseModel):
    """Result of diagram generation + zone detection."""

    asset_id: str
    image_url: str = ""
    image_path: str = ""
    zones: list[DetectedZone] = Field(default_factory=list)
    zone_match_report: Optional[ZoneMatchReport] = None


class ItemImageResult(BaseModel):
    """Result of item image generation/search."""

    asset_id: str
    item_id: str
    image_url: str = ""


class ColorPaletteResult(BaseModel):
    """Result of color palette curation."""

    asset_id: str
    colors: dict[str, str] = Field(default_factory=dict)


class SceneAssets(BaseModel):
    """Complete assets for one scene."""

    scene_id: str
    status: Literal["success", "partial", "error"] = "success"
    primary_diagram: Optional[DiagramAssetResult] = None
    second_diagram: Optional[DiagramAssetResult] = None
    item_images: list[ItemImageResult] = Field(default_factory=list)
    color_palettes: list[ColorPaletteResult] = Field(default_factory=list)
    error: Optional[str] = None


# ── Legacy compatibility (for existing asset_worker) ────────────

class AssetResult(BaseModel):
    """Result of asset generation for one scene (legacy format).

    Used by the existing asset_worker. Will be replaced by SceneAssets
    once the full 3-stage cascade is wired.
    """

    scene_id: str
    status: Literal["success", "error"]
    diagram_url: Optional[str] = None
    zones: list[dict[str, Any]] = Field(default_factory=list)
    match_quality: Optional[float] = None
    error: Optional[str] = None
