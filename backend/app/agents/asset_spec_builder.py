"""
Asset Spec Builder Agent (v3)

Deterministic transformation: GameDesignV3 + AssetGraph → AssetManifest.

Creates an AssetSpec for every asset-producing node in the graph, encoding:
- Dimensional constraints (consistent sizing)
- Style constraints (from theme)
- Content requirements (from game design)
- Worker routing (which generation tool handles it)
- Dependencies (from graph edges)
- Generation ordering (topological sort)

NO LLM calls. Pure data transformation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.game_design_v3 import GameDesignV3
from app.agents.schemas.asset_graph import (
    AssetGraph,
    NodeType,
    RelationType,
    ImageNode,
    AnimationNode,
    SoundNode,
    AssetNode,
    PathNode,
    SceneNode,
    ZoneNode,
)
from app.agents.schemas.asset_spec import (
    AssetSpec,
    AssetManifest,
    AssetType,
    WorkerType,
    DimensionSpec,
    PositionSpec,
    StyleSpec,
    ContentSpec,
    ASSET_TYPE_TO_WORKER,
    estimate_manifest_cost,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.asset_spec_builder")

# Default dimensions per asset type
DEFAULT_DIMENSIONS: Dict[AssetType, Dict[str, Any]] = {
    AssetType.DIAGRAM: {"width": 800, "height": 600, "aspect_ratio": "4:3"},
    AssetType.BACKGROUND: {"width": 1200, "height": 800, "aspect_ratio": "3:2"},
    AssetType.ZONE_OVERLAY: {},
    AssetType.SPRITE: {"max_width": 200, "max_height": 200},
    AssetType.OVERLAY: {"width": 400, "height": 300},
    AssetType.DECORATION: {"max_width": 150, "max_height": 150},
    AssetType.SVG: {"width": 600, "height": 400},
    AssetType.LOTTIE: {"width": 300, "height": 300},
    AssetType.CSS_ANIMATION: {},
    AssetType.SOUND_EFFECT: {},
    AssetType.GIF: {"width": 200, "height": 200},
    AssetType.PATH_DATA: {},
    AssetType.CLICK_TARGETS: {},
}

# Asset type priority (higher = generate earlier)
PRIORITY: Dict[AssetType, int] = {
    AssetType.DIAGRAM: 100,
    AssetType.BACKGROUND: 95,
    AssetType.ZONE_OVERLAY: 80,
    AssetType.PATH_DATA: 70,
    AssetType.CLICK_TARGETS: 70,
    AssetType.SPRITE: 60,
    AssetType.OVERLAY: 50,
    AssetType.SVG: 50,
    AssetType.DECORATION: 40,
    AssetType.CSS_ANIMATION: 30,
    AssetType.GIF: 30,
    AssetType.LOTTIE: 30,
    AssetType.SOUND_EFFECT: 20,
}

# Fallback workers
FALLBACKS: Dict[WorkerType, WorkerType] = {
    WorkerType.IMAGE_SEARCH: WorkerType.IMAGEN,
    WorkerType.IMAGEN: WorkerType.GEMINI_IMAGE,
    WorkerType.SVG_RENDERER: WorkerType.GEMINI_IMAGE,
    WorkerType.LOTTIE_GEN: WorkerType.CSS_ANIMATION,
    WorkerType.SPRITE_GEN: WorkerType.IMAGEN,
}

# Asset subtype → AssetType
ASSET_SUBTYPE_MAP: Dict[str, AssetType] = {
    "background": AssetType.BACKGROUND,
    "overlay": AssetType.OVERLAY,
    "sprite": AssetType.SPRITE,
    "decoration": AssetType.DECORATION,
    "svg": AssetType.SVG,
    "zone_overlay": AssetType.ZONE_OVERLAY,
    "lottie": AssetType.LOTTIE,
    "css_animation": AssetType.CSS_ANIMATION,
    "gif": AssetType.GIF,
    "image": AssetType.DIAGRAM,
}


def build_asset_manifest(
    design: GameDesignV3,
    graph: AssetGraph,
) -> AssetManifest:
    """
    Build a complete AssetManifest from a GameDesignV3 and its AssetGraph.

    Iterates over all asset-producing nodes (IMAGE, ANIMATION, SOUND, ASSET, PATH)
    and creates an AssetSpec for each.
    """
    game_id = design.title.lower().replace(" ", "_")[:32]
    manifest = AssetManifest(game_id=game_id)

    # Extract theme style for inheritance
    theme_style = _extract_theme_style(design)

    # Process IMAGE nodes → DIAGRAM specs
    for node in graph.get_nodes_by_type(NodeType.IMAGE):
        assert isinstance(node, ImageNode)
        asset_type = AssetType.DIAGRAM
        scene_num = _find_scene_number(node.id, graph)
        spec = _build_spec_for_image(node, asset_type, scene_num, design, graph, theme_style)
        manifest.add_spec(spec)

    # Process ANIMATION nodes → CSS_ANIMATION / LOTTIE / GIF specs
    for node in graph.get_nodes_by_type(NodeType.ANIMATION):
        assert isinstance(node, AnimationNode)
        asset_type = _animation_type(node)
        scene_num = _find_scene_number(node.id, graph)
        spec = _build_spec_for_animation(node, asset_type, scene_num, theme_style)
        manifest.add_spec(spec)

    # Process SOUND nodes → SOUND_EFFECT specs
    for node in graph.get_nodes_by_type(NodeType.SOUND):
        assert isinstance(node, SoundNode)
        scene_num = _find_scene_number(node.id, graph)
        spec = _build_spec_for_sound(node, scene_num, theme_style)
        manifest.add_spec(spec)

    # Process ASSET nodes → SPRITE / OVERLAY / DECORATION / etc. specs
    for node in graph.get_nodes_by_type(NodeType.ASSET):
        assert isinstance(node, AssetNode)
        asset_type = ASSET_SUBTYPE_MAP.get(node.asset_type, AssetType.SPRITE)
        scene_num = _find_scene_number(node.id, graph)
        spec = _build_spec_for_asset(node, asset_type, scene_num, graph, theme_style)
        manifest.add_spec(spec)

    # Process PATH nodes → PATH_DATA specs
    for node in graph.get_nodes_by_type(NodeType.PATH):
        assert isinstance(node, PathNode)
        scene_num = _find_scene_number(node.id, graph)
        spec = _build_spec_for_path(node, scene_num, theme_style)
        manifest.add_spec(spec)

    # Compute generation order via topological sort
    try:
        topo_order = graph.topological_sort()
        manifest.generation_order = [
            nid for nid in topo_order if nid in manifest.specs
        ]
    except Exception as e:
        logger.warning(f"Topological sort failed: {e}. Using priority-based order.")
        manifest.generation_order = sorted(
            manifest.specs.keys(),
            key=lambda nid: -manifest.specs[nid].priority,
        )

    manifest.total_estimated_cost = estimate_manifest_cost(manifest)

    logger.info(
        f"Built manifest: {len(manifest.specs)} specs, "
        f"order={len(manifest.generation_order)}, "
        f"est_cost=${manifest.total_estimated_cost:.3f}"
    )
    return manifest


# ---------------------------------------------------------------------------
# Theme extraction
# ---------------------------------------------------------------------------

def _extract_theme_style(design: GameDesignV3) -> StyleSpec:
    """Extract a base StyleSpec from the game design's theme."""
    style = StyleSpec()
    if design.theme:
        if design.theme.color_palette:
            style.color_palette = dict(design.theme.color_palette)
        style.visual_tone = design.theme.visual_tone
        if design.theme.background_description:
            style.style_prompt_suffix = design.theme.background_description
    return style


# ---------------------------------------------------------------------------
# Scene number lookup
# ---------------------------------------------------------------------------

def _find_scene_number(node_id: str, graph: AssetGraph) -> Optional[int]:
    """Walk incoming BELONGS_TO/CONTAINS edges to find the owning scene."""
    visited = set()
    stack = [node_id]

    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)

        node = graph.get_node(current)
        if node and node.node_type == NodeType.SCENE:
            return getattr(node, "scene_number", None)

        # Walk BELONGS_TO (child → parent)
        for edge in graph.get_edges_from(current, RelationType.BELONGS_TO):
            stack.append(edge.target)
        # Walk CONTAINS in reverse (parent → child → look at parent)
        for edge in graph.get_edges_to(current, RelationType.CONTAINS):
            stack.append(edge.source)

    return None


# ---------------------------------------------------------------------------
# Per-type spec builders
# ---------------------------------------------------------------------------

def _build_spec_for_image(
    node: ImageNode,
    asset_type: AssetType,
    scene_num: Optional[int],
    design: GameDesignV3,
    graph: AssetGraph,
    theme: StyleSpec,
) -> AssetSpec:
    defaults = DEFAULT_DIMENSIONS.get(asset_type, {})
    dims = DimensionSpec(
        width=node.width or defaults.get("width"),
        height=node.height or defaults.get("height"),
        aspect_ratio=defaults.get("aspect_ratio"),
    )

    # Content from game design visual spec
    content = ContentSpec(description=node.description)
    if scene_num:
        for scene in design.scenes:
            if scene.scene_number == scene_num and scene.visual:
                content.description = scene.visual.description or content.description
                content.generation_prompt = scene.visual.description
                if scene.visual.required_elements:
                    content.required_elements = scene.visual.required_elements
                break

    # Collect zone labels from zones positioned on this image
    zone_labels = []
    for zone_node in graph.get_zones_for_image(node.id):
        zone_labels.append(zone_node.label)
    if zone_labels:
        content.zone_labels = zone_labels

    worker = ASSET_TYPE_TO_WORKER.get(asset_type, WorkerType.IMAGE_SEARCH)
    deps = [e.target for e in graph.get_edges_from(node.id, RelationType.DEPENDS_ON)]

    return AssetSpec(
        asset_id=node.id,
        asset_type=asset_type,
        graph_node_id=node.id,
        dimensions=dims,
        style=StyleSpec(
            color_palette=theme.color_palette,
            visual_tone=theme.visual_tone,
            style_prompt_suffix=theme.style_prompt_suffix,
        ),
        content=content,
        worker=worker,
        fallback_worker=FALLBACKS.get(worker),
        priority=PRIORITY.get(asset_type, 10),
        depends_on=deps,
        scene_number=scene_num,
    )


def _animation_type(node: AnimationNode) -> AssetType:
    atype = node.animation_type.lower()
    if atype == "lottie":
        return AssetType.LOTTIE
    if atype == "gif":
        return AssetType.GIF
    return AssetType.CSS_ANIMATION


def _build_spec_for_animation(
    node: AnimationNode,
    asset_type: AssetType,
    scene_num: Optional[int],
    theme: StyleSpec,
) -> AssetSpec:
    defaults = DEFAULT_DIMENSIONS.get(asset_type, {})
    dims = DimensionSpec(
        width=defaults.get("width"),
        height=defaults.get("height"),
    )
    content = ContentSpec(
        animation_type=node.animation_type,
        duration_ms=node.duration_ms,
        easing=node.easing,
        trigger=node.trigger,
    )
    if node.particle_config:
        content.particle_config = node.particle_config

    worker = ASSET_TYPE_TO_WORKER.get(asset_type, WorkerType.CSS_ANIMATION)

    return AssetSpec(
        asset_id=node.id,
        asset_type=asset_type,
        graph_node_id=node.id,
        dimensions=dims,
        style=StyleSpec(color_palette=theme.color_palette, visual_tone=theme.visual_tone),
        content=content,
        worker=worker,
        fallback_worker=FALLBACKS.get(worker),
        priority=PRIORITY.get(asset_type, 10),
        scene_number=scene_num,
    )


def _build_spec_for_sound(
    node: SoundNode,
    scene_num: Optional[int],
    theme: StyleSpec,
) -> AssetSpec:
    content = ContentSpec(
        sound_event=node.sound_event,
        sound_description=node.description,
    )
    return AssetSpec(
        asset_id=node.id,
        asset_type=AssetType.SOUND_EFFECT,
        graph_node_id=node.id,
        content=content,
        worker=WorkerType.AUDIO_GEN,
        priority=PRIORITY.get(AssetType.SOUND_EFFECT, 10),
        scene_number=scene_num,
    )


def _build_spec_for_asset(
    node: AssetNode,
    asset_type: AssetType,
    scene_num: Optional[int],
    graph: AssetGraph,
    theme: StyleSpec,
) -> AssetSpec:
    defaults = DEFAULT_DIMENSIONS.get(asset_type, {})
    dims = DimensionSpec(
        width=node.width or defaults.get("width"),
        height=node.height or defaults.get("height"),
        max_width=defaults.get("max_width"),
        max_height=defaults.get("max_height"),
    )

    content = ContentSpec(
        description=node.description,
        generation_prompt=node.generation_prompt,
    )

    # Encode game logic trigger
    if node.game_logic:
        content.trigger = node.game_logic.trigger

    # Position from layer
    position = PositionSpec(z_index=node.layer) if node.layer != 0 else None

    # Check POSITIONED_ON edges for relative positioning
    pos_edges = graph.get_edges_from(node.id, RelationType.POSITIONED_ON)
    if pos_edges:
        position = PositionSpec(
            relative_to=pos_edges[0].target,
            z_index=node.layer,
        )

    worker = ASSET_TYPE_TO_WORKER.get(asset_type, WorkerType.NOOP)
    if node.generation_worker:
        try:
            worker = WorkerType(node.generation_worker)
        except ValueError:
            pass

    deps = [e.target for e in graph.get_edges_from(node.id, RelationType.DEPENDS_ON)]

    return AssetSpec(
        asset_id=node.id,
        asset_type=asset_type,
        graph_node_id=node.id,
        dimensions=dims,
        position=position,
        style=StyleSpec(
            color_palette=theme.color_palette,
            visual_tone=theme.visual_tone,
            transparency=asset_type in (AssetType.SPRITE, AssetType.OVERLAY),
        ),
        content=content,
        worker=worker,
        fallback_worker=FALLBACKS.get(worker),
        priority=PRIORITY.get(asset_type, 10),
        depends_on=deps,
        scene_number=scene_num,
    )


def _build_spec_for_path(
    node: PathNode,
    scene_num: Optional[int],
    theme: StyleSpec,
) -> AssetSpec:
    content = ContentSpec(
        description=node.description,
        waypoint_labels=node.waypoint_zone_ids,
        path_type=node.path_type,
    )
    return AssetSpec(
        asset_id=node.id,
        asset_type=AssetType.PATH_DATA,
        graph_node_id=node.id,
        content=content,
        worker=WorkerType.PATH_GEN,
        fallback_worker=None,
        priority=PRIORITY.get(AssetType.PATH_DATA, 10),
        scene_number=scene_num,
    )


# ---------------------------------------------------------------------------
# Agent wrapper
# ---------------------------------------------------------------------------

async def asset_spec_builder_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Asset Spec Builder Agent — deterministic transformation.

    Reads: game_design_v3, asset_graph_v3 from state
    Writes: asset_manifest_v3 (serialized AssetManifest)
    """
    logger.info("AssetSpecBuilder: Starting")

    raw_design = state.get("game_design_v3")
    raw_graph = state.get("asset_graph_v3")

    if not raw_design:
        logger.error("AssetSpecBuilder: No game_design_v3 in state")
        return {
            **state,
            "current_agent": "asset_spec_builder",
            "error_message": "No game_design_v3 found in state",
        }

    if not raw_graph:
        logger.info("AssetSpecBuilder: No asset_graph_v3 in state, building from design")
        # Build graph from design as fallback
        try:
            if isinstance(raw_design, dict):
                _design = GameDesignV3.model_validate(raw_design)
            else:
                _design = raw_design
            raw_graph = AssetGraph.from_game_design(_design).serialize()
        except Exception as e:
            logger.error(f"AssetSpecBuilder: Failed to build graph from design: {e}")
            return {
                **state,
                "current_agent": "asset_spec_builder",
                "error_message": f"Failed to build asset graph from design: {e}",
            }

    try:
        if isinstance(raw_design, dict):
            design = GameDesignV3.model_validate(raw_design)
        else:
            design = raw_design

        if isinstance(raw_graph, dict):
            graph = AssetGraph.deserialize(raw_graph)
        else:
            graph = raw_graph
    except Exception as e:
        logger.error(f"AssetSpecBuilder: Failed to parse inputs: {e}")
        return {
            **state,
            "current_agent": "asset_spec_builder",
            "error_message": f"Failed to parse inputs: {e}",
        }

    try:
        manifest = build_asset_manifest(design, graph)
    except Exception as e:
        logger.error(f"AssetSpecBuilder: Failed to build manifest: {e}", exc_info=True)
        return {
            **state,
            "current_agent": "asset_spec_builder",
            "error_message": f"Failed to build asset manifest: {e}",
        }

    manifest_dict = manifest.model_dump(mode="json")

    logger.info(
        f"AssetSpecBuilder: Created {len(manifest.specs)} asset specs, "
        f"est. cost ${manifest.total_estimated_cost:.3f}"
    )

    # Also store the graph in state if it was built as fallback
    result_state = {
        **state,
        "current_agent": "asset_spec_builder",
        "asset_manifest_v3": manifest_dict,
    }
    # Ensure graph is in state for orchestrator
    if not state.get("asset_graph_v3") and isinstance(raw_graph, dict):
        result_state["asset_graph_v3"] = raw_graph
    return result_state
