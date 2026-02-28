"""
Asset Graph — Graph-based data structure encoding all game entity relationships.

The game IS its asset graph. Every zone, label, animation, sound, image, and
interaction is a node. Edges encode relationships (containment, positioning,
triggers, dependencies, temporal ordering). The game engine traverses this
graph at runtime; the asset orchestrator traverses it at generation time.

Key design decisions:
- Assets can belong to scenes directly (backgrounds, decorations, scene-level
  animations) OR to zones (zone overlays, zone-specific feedback). Both are
  first-class. Scene-level assets have their own game logic independent of zones.
- Generation order is derived from DEPENDS_ON edges via topological sort.
- The graph serializes to JSON for the frontend blueprint.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("gamed_ai.schemas.asset_graph")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    GAME = "game"
    SCENE = "scene"
    MECHANIC = "mechanic"
    IMAGE = "image"
    ZONE = "zone"
    LABEL = "label"
    ANIMATION = "animation"
    SOUND = "sound"
    ASSET = "asset"
    THEME = "theme"
    PATH = "path"
    TRANSITION = "transition"


class RelationType(str, Enum):
    # Containment hierarchy
    CONTAINS = "contains"                  # game->scene, scene->mechanic, scene->asset
    BELONGS_TO = "belongs_to"              # zone->image, label->zone, asset->scene

    # Visual composition
    HAS_IMAGE = "has_image"                # scene->image (primary diagram)
    HAS_BACKGROUND = "has_background"      # scene->asset (background layer)
    HAS_OVERLAY = "has_overlay"            # image->asset OR scene->asset (overlay)
    POSITIONED_ON = "positioned_on"        # zone->image (carries x,y in metadata)
    DECORATES = "decorates"                # asset->scene (decoration, no zone)

    # Interaction logic
    OPERATES_ON = "operates_on"            # mechanic->[zones] it interacts with
    TARGETS = "targets"                    # label->zone (correct assignment)
    AVAILABLE_IN = "available_in"          # label->mechanic (which mechanic uses it)

    # Triggers & effects
    TRIGGERS = "triggers"                  # event->animation or event->sound
    TRIGGERED_BY = "triggered_by"          # animation/sound->event source

    # Transitions
    TRANSITIONS_TO = "transitions_to"      # mechanic->mechanic or scene->scene

    # Asset relationships
    STYLED_BY = "styled_by"                # any node->theme
    STYLE_REFERENCE = "style_reference"    # asset->asset (match style of)
    DEPENDS_ON = "depends_on"              # asset->asset (generation dependency)

    # Audio binding
    PLAYS_ON = "plays_on"                  # sound->event_type

    # Temporal ordering
    REVEALS = "reveals"                    # zone->child_zones (hierarchy)
    BEFORE = "before"                      # zone_a before zone_b
    AFTER = "after"                        # zone_a after zone_b
    MUTEX = "mutex"                        # zone_a and zone_b mutually exclusive
    SEQUENCE = "sequence"                  # ordered constraint

    # Path relationships
    HAS_WAYPOINT = "has_waypoint"          # path->zone (waypoint in order)
    FOLLOWS_PATH = "follows_path"          # mechanic->path


# ---------------------------------------------------------------------------
# Node models
# ---------------------------------------------------------------------------

class BaseNode(BaseModel):
    """Common fields for all graph nodes."""
    model_config = ConfigDict(extra="allow")

    id: str
    node_type: NodeType
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GameNode(BaseNode):
    node_type: NodeType = NodeType.GAME
    title: str = ""
    template_type: str = "INTERACTIVE_DIAGRAM"
    total_max_score: int = 0
    star_thresholds: List[float] = Field(default_factory=lambda: [0.6, 0.8, 1.0])
    narrative_intro: str = ""
    estimated_duration_minutes: int = 5


class ThemeNode(BaseNode):
    node_type: NodeType = NodeType.THEME
    visual_tone: str = "clinical_educational"
    color_palette: Dict[str, str] = Field(default_factory=lambda: {
        "primary": "#3b82f6",
        "success": "#22c55e",
        "error": "#ef4444",
        "warning": "#f59e0b",
        "background": "#f8fafc",
        "surface": "#ffffff",
        "text_primary": "#0f172a",
        "text_secondary": "#64748b",
    })
    background_description: Optional[str] = None
    narrative_frame: Optional[str] = None


class SceneNode(BaseNode):
    node_type: NodeType = NodeType.SCENE
    scene_number: int = 1
    title: str = ""
    learning_goal: str = ""
    narrative_intro: Optional[str] = None
    max_score: int = 0
    time_limit_seconds: Optional[int] = None


class MechanicNode(BaseNode):
    """An interaction mechanic within a scene."""
    node_type: NodeType = NodeType.MECHANIC
    mechanic_type: str = "drag_drop"
    description: str = ""
    zone_labels_used: List[str] = Field(default_factory=list)
    scoring: Dict[str, Any] = Field(default_factory=dict)
    feedback: Dict[str, Any] = Field(default_factory=dict)
    # Mode-specific configuration stored generically
    mode_config: Dict[str, Any] = Field(default_factory=dict)


class ImageNode(BaseNode):
    """A primary diagram or visual asset."""
    node_type: NodeType = NodeType.IMAGE
    description: str = ""
    required_elements: List[str] = Field(default_factory=list)
    style: str = "clean educational"
    image_source: str = "search"  # search, generate, search_then_generate
    # Populated after generation
    generated_path: Optional[str] = None
    served_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class ZoneNode(BaseNode):
    """An interactive zone on a diagram image."""
    node_type: NodeType = NodeType.ZONE
    label: str = ""
    zone_type: Optional[str] = None  # point, area
    shape: Optional[str] = None  # circle, polygon, rect
    # Position (percentage-based, 0-100)
    x_percent: Optional[float] = None
    y_percent: Optional[float] = None
    radius_percent: Optional[float] = None
    width_percent: Optional[float] = None
    height_percent: Optional[float] = None
    points: Optional[List[List[float]]] = None  # polygon vertices
    center: Optional[Dict[str, float]] = None
    # Hierarchy
    hierarchy_level: int = 1
    parent_zone_id: Optional[str] = None
    child_zone_ids: List[str] = Field(default_factory=list)
    # Educational
    difficulty: Optional[int] = None  # 1-5
    hint_progression: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class LabelNode(BaseNode):
    """A label that can be placed on a zone."""
    node_type: NodeType = NodeType.LABEL
    text: str = ""
    is_distractor: bool = False
    distractor_explanation: Optional[str] = None
    correct_zone_id: Optional[str] = None
    appears_in_scenes: List[int] = Field(default_factory=list)


class AnimationNode(BaseNode):
    """An animation that triggers on game events."""
    node_type: NodeType = NodeType.ANIMATION
    animation_type: str = "pulse"  # pulse, glow, scale, shake, fade, bounce, confetti, path_draw
    trigger: str = "on_correct"  # on_correct, on_incorrect, on_complete, on_hover, on_scene_enter, on_drag
    target_node_id: Optional[str] = None  # what node this animates (zone, asset, label)
    duration_ms: int = 400
    easing: str = "ease-out"
    color: Optional[str] = None
    intensity: Optional[float] = None
    delay_ms: int = 0
    particle_config: Optional[Dict[str, Any]] = None
    css_content: Optional[str] = None  # generated CSS keyframes


class SoundNode(BaseNode):
    """A sound effect bound to a game event."""
    node_type: NodeType = NodeType.SOUND
    sound_event: str = "correct"  # correct, incorrect, drag_start, drop, completion, hint_used, timer_warning, streak, scene_transition
    description: str = ""
    url: Optional[str] = None
    preset: Optional[str] = None
    volume: float = 0.5
    delay_ms: int = 0


class AssetGameLogic(BaseModel):
    """Game logic for an asset that operates independently of zones.

    Examples:
    - A background sprite that pulses when the timer is low
    - An overlay that fades in when a mechanic completes
    - A decoration that changes state based on score thresholds
    - A mascot character whose expression changes on correct/incorrect
    """
    model_config = ConfigDict(extra="allow")

    # When does this asset activate?
    trigger: Optional[str] = None  # on_scene_enter, on_complete, on_correct, on_incorrect, on_mechanic_start, on_mechanic_complete, on_score_threshold, on_streak, on_timer_warning, always, never
    trigger_config: Dict[str, Any] = Field(default_factory=dict)  # {threshold: 0.7, mechanic_type: "drag_drop"}

    # State machine: asset can have named states with different visuals
    states: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    # e.g. {"idle": {"opacity": 1, "scale": 1}, "active": {"opacity": 1, "scale": 1.1, "glow": true}}
    initial_state: str = "idle"

    # Conditions for state transitions
    state_transitions: List[Dict[str, Any]] = Field(default_factory=list)
    # e.g. [{"from": "idle", "to": "active", "when": "on_mechanic_start"}, ...]

    # Does this asset interact with other assets?
    emits_events: List[str] = Field(default_factory=list)  # events this asset can emit
    listens_to: List[str] = Field(default_factory=list)  # events this asset responds to


class AssetNode(BaseNode):
    """A media asset (background, overlay, sprite, decoration, svg, lottie, css_animation).

    Assets can belong to scenes directly (scene-level assets with independent
    game logic) or be associated with specific zones. Scene-level assets can
    have their own state machines and trigger logic that operates independently
    of the zone/label interaction system.
    """
    node_type: NodeType = NodeType.ASSET
    asset_type: str = "image"  # background, overlay, sprite, decoration, svg, lottie, css_animation, image, gif
    description: str = ""
    placement: str = "decoration"  # background, overlay, zone, decoration
    layer: int = 0  # z-order, -10 to 10
    # Generation
    generation_prompt: Optional[str] = None
    generation_worker: Optional[str] = None
    # Populated after generation
    generated_path: Optional[str] = None
    served_url: Optional[str] = None
    css_content: Optional[str] = None
    lottie_data: Optional[Dict[str, Any]] = None
    # Dimensions
    width: Optional[int] = None
    height: Optional[int] = None
    # Game logic (independent of zones)
    game_logic: Optional[AssetGameLogic] = None
    # Motion path for animated assets
    motion_keyframes: Optional[List[Dict[str, Any]]] = None
    motion_loop: bool = False
    motion_easing: str = "ease-in-out"


class PathNode(BaseNode):
    """A trace path (ordered sequence of waypoints)."""
    node_type: NodeType = NodeType.PATH
    description: str = ""
    path_type: str = "linear"  # linear, cyclic, branching
    waypoint_zone_ids: List[str] = Field(default_factory=list)  # ordered
    visual_style: Optional[str] = None  # blue_to_red_gradient, etc.


class TransitionNode(BaseNode):
    """A transition between mechanics or scenes."""
    node_type: NodeType = NodeType.TRANSITION
    from_id: str = ""  # mechanic_id or scene_id
    to_id: str = ""
    trigger: str = "all_complete"  # score_threshold, all_complete, all_zones_labeled, time_elapsed, user_choice
    threshold: Optional[float] = None
    animation: str = "fade"  # fade, slide_left, slide_right, zoom_in, reveal, none
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Union type for deserialization
# ---------------------------------------------------------------------------

NODE_TYPE_MAP: Dict[str, type] = {
    NodeType.GAME: GameNode,
    NodeType.SCENE: SceneNode,
    NodeType.MECHANIC: MechanicNode,
    NodeType.IMAGE: ImageNode,
    NodeType.ZONE: ZoneNode,
    NodeType.LABEL: LabelNode,
    NodeType.ANIMATION: AnimationNode,
    NodeType.SOUND: SoundNode,
    NodeType.ASSET: AssetNode,
    NodeType.THEME: ThemeNode,
    NodeType.PATH: PathNode,
    NodeType.TRANSITION: TransitionNode,
}

AnyNode = Union[
    GameNode, SceneNode, MechanicNode, ImageNode, ZoneNode,
    LabelNode, AnimationNode, SoundNode, AssetNode, ThemeNode,
    PathNode, TransitionNode,
]


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------

class Edge(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str
    target: str
    relationship: RelationType
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# AssetGraph
# ---------------------------------------------------------------------------

class AssetGraph:
    """Graph store encoding all relationships for the game engine.

    Nodes represent game entities (scenes, zones, labels, assets, etc.).
    Edges represent relationships (containment, positioning, triggers, etc.).

    The asset orchestrator uses topological_sort(DEPENDS_ON) to determine
    generation order. The blueprint assembler traverses the graph to build
    the frontend-compatible JSON. The frontend game engine uses the serialized
    graph to run interactions at runtime.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, AnyNode] = {}
        self._edges: List[Edge] = []
        self._outgoing: Dict[str, List[Edge]] = defaultdict(list)
        self._incoming: Dict[str, List[Edge]] = defaultdict(list)

    # -- Node operations ---------------------------------------------------

    def add_node(self, node: AnyNode) -> None:
        """Add a node to the graph. Overwrites if id already exists."""
        if node.id in self._nodes:
            logger.debug("Overwriting node %s", node.id)
        self._nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[AnyNode]:
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[AnyNode]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its connected edges."""
        if node_id not in self._nodes:
            return
        del self._nodes[node_id]
        # Remove edges
        self._edges = [e for e in self._edges if e.source != node_id and e.target != node_id]
        # Rebuild indices
        self._rebuild_indices()

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    # -- Edge operations ---------------------------------------------------

    def add_edge(self, edge: Edge) -> None:
        """Add an edge. Both source and target must exist as nodes."""
        if edge.source not in self._nodes:
            logger.warning("Edge source %s not in graph, adding anyway", edge.source)
        if edge.target not in self._nodes:
            logger.warning("Edge target %s not in graph, adding anyway", edge.target)
        self._edges.append(edge)
        self._outgoing[edge.source].append(edge)
        self._incoming[edge.target].append(edge)

    def add_edge_simple(
        self,
        source: str,
        target: str,
        relationship: RelationType,
        **metadata: Any,
    ) -> Edge:
        """Convenience: create and add an edge in one call."""
        edge = Edge(source=source, target=target, relationship=relationship, metadata=metadata)
        self.add_edge(edge)
        return edge

    def get_edges_from(self, node_id: str, relationship: Optional[RelationType] = None) -> List[Edge]:
        edges = self._outgoing.get(node_id, [])
        if relationship is not None:
            edges = [e for e in edges if e.relationship == relationship]
        return edges

    def get_edges_to(self, node_id: str, relationship: Optional[RelationType] = None) -> List[Edge]:
        edges = self._incoming.get(node_id, [])
        if relationship is not None:
            edges = [e for e in edges if e.relationship == relationship]
        return edges

    def get_neighbors(
        self, node_id: str, relationship: Optional[RelationType] = None
    ) -> List[AnyNode]:
        """Get outgoing neighbor nodes, optionally filtered by relationship."""
        edges = self.get_edges_from(node_id, relationship)
        nodes = []
        for e in edges:
            n = self._nodes.get(e.target)
            if n is not None:
                nodes.append(n)
        return nodes

    def get_incoming_neighbors(
        self, node_id: str, relationship: Optional[RelationType] = None
    ) -> List[AnyNode]:
        """Get incoming neighbor nodes."""
        edges = self.get_edges_to(node_id, relationship)
        nodes = []
        for e in edges:
            n = self._nodes.get(e.source)
            if n is not None:
                nodes.append(n)
        return nodes

    # -- Convenience queries -----------------------------------------------

    def get_scene_nodes(self) -> List[SceneNode]:
        """Scenes sorted by scene_number."""
        scenes = self.get_nodes_by_type(NodeType.SCENE)
        return sorted(scenes, key=lambda s: s.scene_number)  # type: ignore[attr-defined]

    def get_mechanics_for_scene(self, scene_id: str) -> List[MechanicNode]:
        """Mechanics contained in a scene."""
        return [
            n for n in self.get_neighbors(scene_id, RelationType.CONTAINS)
            if n.node_type == NodeType.MECHANIC
        ]

    def get_assets_for_scene(self, scene_id: str) -> List[AssetNode]:
        """Assets directly owned by a scene (backgrounds, decorations, etc.)."""
        result: List[AssetNode] = []
        for n in self.get_neighbors(scene_id, RelationType.CONTAINS):
            if n.node_type == NodeType.ASSET:
                result.append(n)  # type: ignore[arg-type]
        for n in self.get_neighbors(scene_id, RelationType.HAS_BACKGROUND):
            if n.node_type == NodeType.ASSET:
                result.append(n)  # type: ignore[arg-type]
        # Deduplicate by id
        seen = set()
        deduped = []
        for a in result:
            if a.id not in seen:
                seen.add(a.id)
                deduped.append(a)
        return deduped

    def get_image_for_scene(self, scene_id: str) -> Optional[ImageNode]:
        """Primary diagram image for a scene."""
        images = self.get_neighbors(scene_id, RelationType.HAS_IMAGE)
        return images[0] if images else None  # type: ignore[return-value]

    def get_zones_for_image(self, image_id: str) -> List[ZoneNode]:
        """Zones positioned on an image."""
        return [
            n for n in self.get_incoming_neighbors(image_id, RelationType.POSITIONED_ON)
            if n.node_type == NodeType.ZONE
        ]

    def get_labels_for_zone(self, zone_id: str) -> List[LabelNode]:
        """Labels that target a zone."""
        return [
            n for n in self.get_incoming_neighbors(zone_id, RelationType.TARGETS)
            if n.node_type == NodeType.LABEL
        ]

    def get_animations_for_trigger(self, trigger: str) -> List[AnimationNode]:
        """All animations matching a trigger type."""
        return [
            n for n in self.get_nodes_by_type(NodeType.ANIMATION)
            if n.trigger == trigger  # type: ignore[attr-defined]
        ]

    def get_sounds_for_event(self, event: str) -> List[SoundNode]:
        """All sounds matching an event type."""
        return [
            n for n in self.get_nodes_by_type(NodeType.SOUND)
            if n.sound_event == event  # type: ignore[attr-defined]
        ]

    def get_paths_for_scene(self, scene_id: str) -> List[PathNode]:
        """Paths contained in a scene (via mechanics)."""
        paths: List[PathNode] = []
        for mech in self.get_mechanics_for_scene(scene_id):
            for n in self.get_neighbors(mech.id, RelationType.FOLLOWS_PATH):
                if n.node_type == NodeType.PATH:
                    paths.append(n)  # type: ignore[arg-type]
        return paths

    def get_transitions_from(self, node_id: str) -> List[TransitionNode]:
        """Transitions originating from a node (mechanic or scene)."""
        return [
            n for n in self.get_neighbors(node_id, RelationType.TRANSITIONS_TO)
            if n.node_type == NodeType.TRANSITION
        ]

    # -- Per-scene subgraph ------------------------------------------------

    def get_scene_subgraph(self, scene_id: str) -> "AssetGraph":
        """Extract a subgraph containing only nodes/edges relevant to a scene.

        This is the primary performance optimization: the game engine only
        needs to traverse the current scene's subgraph at runtime, not the
        entire game graph.

        Includes: the scene node, its mechanics, image, zones, labels,
        animations, sounds, assets (both zone-attached and scene-level),
        paths, and transitions FROM this scene.
        """
        subgraph = AssetGraph()
        visited: set[str] = set()

        def _collect(node_id: str) -> None:
            if node_id in visited or node_id not in self._nodes:
                return
            visited.add(node_id)
            subgraph.add_node(self._nodes[node_id])

        # Start with the scene itself
        _collect(scene_id)

        # Theme (global, always included)
        for theme in self.get_nodes_by_type(NodeType.THEME):
            _collect(theme.id)

        # Image
        img = self.get_image_for_scene(scene_id)
        if img:
            _collect(img.id)

        # Mechanics
        for mech in self.get_mechanics_for_scene(scene_id):
            _collect(mech.id)
            # Labels available in this mechanic
            for label in self.get_neighbors(mech.id, RelationType.AVAILABLE_IN):
                _collect(label.id)

        # All scene-level assets (backgrounds, decorations, overlays)
        for asset in self.get_assets_for_scene(scene_id):
            _collect(asset.id)

        # Zones on the image
        if img:
            for zone in self.get_zones_for_image(img.id):
                _collect(zone.id)
                # Labels targeting this zone
                for label in self.get_labels_for_zone(zone.id):
                    _collect(label.id)
                # Child zones (hierarchy)
                for child_id in getattr(zone, 'child_zone_ids', []):
                    _collect(child_id)

        # Also collect labels from the LABEL node type that belong to this scene
        for label_node in self.get_nodes_by_type(NodeType.LABEL):
            if hasattr(label_node, 'appears_in_scenes'):
                scene_node = self.get_node(scene_id)
                if scene_node and hasattr(scene_node, 'scene_number'):
                    if scene_node.scene_number in label_node.appears_in_scenes:  # type: ignore
                        _collect(label_node.id)

        # Paths
        for path in self.get_paths_for_scene(scene_id):
            _collect(path.id)

        # Animations and sounds reachable from collected nodes
        for nid in list(visited):
            for edge in self.get_edges_from(nid, RelationType.TRIGGERS):
                _collect(edge.target)
            for edge in self.get_edges_to(nid, RelationType.TRIGGERS):
                _collect(edge.source)

        # Transitions FROM this scene's mechanics
        for mech in self.get_mechanics_for_scene(scene_id):
            for trans in self.get_transitions_from(mech.id):
                _collect(trans.id)
        # Scene-level transitions
        for trans in self.get_transitions_from(scene_id):
            _collect(trans.id)

        # Copy relevant edges (both endpoints in subgraph)
        for edge in self._edges:
            if edge.source in visited and edge.target in visited:
                subgraph.add_edge(edge)

        return subgraph

    def get_all_scene_subgraphs(self) -> Dict[str, "AssetGraph"]:
        """Extract subgraphs for all scenes. Keyed by scene_id."""
        return {
            scene.id: self.get_scene_subgraph(scene.id)
            for scene in self.get_scene_nodes()
        }

    def get_scene_asset_ids(self, scene_id: str) -> set[str]:
        """Quick lookup: all asset/image node IDs belonging to a scene.

        Useful for filtering generation order to a specific scene.
        """
        ids: set[str] = set()
        img = self.get_image_for_scene(scene_id)
        if img:
            ids.add(img.id)
        for asset in self.get_assets_for_scene(scene_id):
            ids.add(asset.id)
        # Animations and sounds connected to scene nodes
        for edge in self.get_edges_from(scene_id):
            target = self.get_node(edge.target)
            if target and target.node_type in (NodeType.ANIMATION, NodeType.SOUND, NodeType.ASSET):
                ids.add(edge.target)
        return ids

    # -- Topological sort --------------------------------------------------

    def topological_sort(self, relationship: RelationType = RelationType.DEPENDS_ON) -> List[str]:
        """Kahn's algorithm for topological ordering on a specific edge type.

        Returns node_ids in dependency order (dependencies first).
        Raises ValueError if cycle detected.
        """
        # Build adjacency and in-degree for the specified relationship only
        in_degree: Dict[str, int] = defaultdict(int)
        adj: Dict[str, List[str]] = defaultdict(list)
        involved: set[str] = set()

        for edge in self._edges:
            if edge.relationship != relationship:
                continue
            involved.add(edge.source)
            involved.add(edge.target)
            adj[edge.source].append(edge.target)
            in_degree.setdefault(edge.source, 0)
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

        # Start with nodes having no incoming edges of this relationship
        queue: deque[str] = deque()
        for nid in involved:
            if in_degree.get(nid, 0) == 0:
                queue.append(nid)

        result: List[str] = []
        while queue:
            nid = queue.popleft()
            result.append(nid)
            for neighbor in adj.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(involved):
            cycle_nodes = involved - set(result)
            raise ValueError(f"Cycle detected in {relationship.value} edges involving: {cycle_nodes}")

        return result

    def get_generation_order(self) -> List[str]:
        """Node IDs that need generation, in dependency order."""
        try:
            return self.topological_sort(RelationType.DEPENDS_ON)
        except ValueError as e:
            logger.error("Generation order has cycle: %s", e)
            # Return all nodes with DEPENDS_ON edges in arbitrary order
            involved = set()
            for edge in self._edges:
                if edge.relationship == RelationType.DEPENDS_ON:
                    involved.add(edge.source)
                    involved.add(edge.target)
            return list(involved)

    # -- Validation --------------------------------------------------------

    def validate_graph(self) -> List[str]:
        """Check graph integrity. Returns list of issues (empty = valid)."""
        issues: List[str] = []

        # Check edges reference existing nodes
        for edge in self._edges:
            if edge.source not in self._nodes:
                issues.append(f"Edge references missing source node: {edge.source}")
            if edge.target not in self._nodes:
                issues.append(f"Edge references missing target node: {edge.target}")

        # Check every scene has at least one mechanic
        for scene in self.get_scene_nodes():
            mechs = self.get_mechanics_for_scene(scene.id)
            if not mechs:
                issues.append(f"Scene '{scene.title}' ({scene.id}) has no mechanics")

        # Check every scene has an image
        for scene in self.get_scene_nodes():
            img = self.get_image_for_scene(scene.id)
            if img is None:
                issues.append(f"Scene '{scene.title}' ({scene.id}) has no primary image")

        # Check labels have correct_zone_id pointing to existing zones
        for node in self.get_nodes_by_type(NodeType.LABEL):
            label = node  # type: LabelNode
            if not label.is_distractor and label.correct_zone_id:  # type: ignore[attr-defined]
                if label.correct_zone_id not in self._nodes:  # type: ignore[attr-defined]
                    issues.append(f"Label '{label.text}' targets non-existent zone: {label.correct_zone_id}")  # type: ignore[attr-defined]

        # Check for DEPENDS_ON cycles
        try:
            self.topological_sort(RelationType.DEPENDS_ON)
        except ValueError as e:
            issues.append(f"Dependency cycle: {e}")

        # Check zone hierarchy consistency
        for node in self.get_nodes_by_type(NodeType.ZONE):
            zone = node  # type: ZoneNode
            if zone.parent_zone_id and zone.parent_zone_id not in self._nodes:  # type: ignore[attr-defined]
                issues.append(f"Zone '{zone.label}' references non-existent parent: {zone.parent_zone_id}")  # type: ignore[attr-defined]

        return issues

    # -- Serialization -----------------------------------------------------

    def serialize(self) -> Dict[str, Any]:
        """Serialize entire graph to a JSON-compatible dict."""
        return {
            "nodes": {nid: n.model_dump() for nid, n in self._nodes.items()},
            "edges": [e.model_dump() for e in self._edges],
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "AssetGraph":
        """Reconstruct graph from serialized dict."""
        graph = cls()

        for nid, ndata in data.get("nodes", {}).items():
            node_type_str = ndata.get("node_type")
            try:
                node_type = NodeType(node_type_str)
            except ValueError:
                logger.warning("Unknown node_type '%s' for node %s, using BaseNode", node_type_str, nid)
                node = BaseNode(**ndata)
                graph.add_node(node)
                continue

            node_cls = NODE_TYPE_MAP.get(node_type, BaseNode)
            node = node_cls(**ndata)
            graph.add_node(node)

        for edata in data.get("edges", []):
            edge = Edge(**edata)
            graph.add_edge(edge)

        return graph

    # -- Factory: build from GameDesignV3 ----------------------------------

    @classmethod
    def from_game_design(cls, design: "GameDesignV3") -> "AssetGraph":
        """Build an AssetGraph from a GameDesignV3 document.

        Creates nodes for game, theme, scenes, mechanics, images, zones,
        labels, paths, transitions, and wires all edges.

        This is the fallback when no upstream agent has built the graph.
        """
        from app.agents.schemas.game_design_v3 import GameDesignV3 as GDV3

        graph = cls()

        # Game root node
        game_id = f"game_{design.title.lower().replace(' ', '_')[:24]}" if design.title else "game_root"
        graph.add_node(GameNode(
            id=game_id,
            title=design.title,
            total_max_score=design.total_max_score or design.compute_total_max_score(),
            star_thresholds=design.star_thresholds,
            narrative_intro=design.narrative_intro,
            estimated_duration_minutes=design.estimated_duration_minutes,
        ))

        # Theme node
        theme_id = "theme_global"
        if design.theme:
            graph.add_node(ThemeNode(
                id=theme_id,
                visual_tone=design.theme.visual_tone,
                color_palette=design.theme.color_palette,
                background_description=design.theme.background_description,
                narrative_frame=design.theme.narrative_frame,
            ))
            graph.add_edge_simple(game_id, theme_id, RelationType.STYLED_BY)

        # Collect all zone labels and group-only labels
        zone_labels = set(design.labels.zone_labels) if design.labels else set()
        group_only = set(design.labels.group_only_labels) if design.labels else set()

        # Build label nodes (global)
        label_node_ids: dict[str, str] = {}  # label_text -> node_id
        for label_text in zone_labels:
            lid = f"label_{label_text.lower().replace(' ', '_')[:32]}"
            graph.add_node(LabelNode(
                id=lid,
                text=label_text,
                is_distractor=False,
            ))
            label_node_ids[label_text] = lid

        # Distractor labels
        if design.labels and design.labels.distractor_labels:
            for dl in design.labels.distractor_labels:
                lid = f"label_dist_{dl.text.lower().replace(' ', '_')[:28]}"
                graph.add_node(LabelNode(
                    id=lid,
                    text=dl.text,
                    is_distractor=True,
                    distractor_explanation=dl.explanation,
                ))
                label_node_ids[dl.text] = lid

        # Build scene subgraphs
        for scene in design.scenes:
            sn = scene.scene_number
            scene_id = f"scene_{sn}"

            graph.add_node(SceneNode(
                id=scene_id,
                scene_number=sn,
                title=scene.title,
                learning_goal=scene.learning_goal,
                narrative_intro=scene.narrative_intro,
                max_score=scene.max_score,
                time_limit_seconds=scene.time_limit_seconds,
            ))
            graph.add_edge_simple(game_id, scene_id, RelationType.CONTAINS)

            # Image node for this scene
            image_id = f"image_scene_{sn}"
            desc = scene.visual.description if scene.visual else ""
            required = scene.visual.required_elements if scene.visual else []
            source = scene.visual.image_source if scene.visual else "search_then_generate"
            style = scene.visual.style if scene.visual else "clean educational"

            graph.add_node(ImageNode(
                id=image_id,
                description=desc,
                required_elements=required,
                style=style,
                image_source=source,
            ))
            graph.add_edge_simple(scene_id, image_id, RelationType.HAS_IMAGE)

            # Zone nodes
            scene_zone_ids: dict[str, str] = {}  # label -> zone_id
            scene_labels = scene.zone_labels or list(zone_labels)
            for label_text in scene_labels:
                zone_id = f"zone_{sn}_{label_text.lower().replace(' ', '_')[:28]}"
                graph.add_node(ZoneNode(
                    id=zone_id,
                    label=label_text,
                ))
                scene_zone_ids[label_text] = zone_id
                graph.add_edge_simple(zone_id, image_id, RelationType.POSITIONED_ON)

                # Link label → zone
                if label_text in label_node_ids:
                    graph.add_edge_simple(label_node_ids[label_text], zone_id, RelationType.TARGETS)

            # Group-only zones
            for g_label in group_only:
                zone_id = f"zone_{sn}_{g_label.lower().replace(' ', '_')[:28]}"
                if not graph.has_node(zone_id):
                    graph.add_node(ZoneNode(
                        id=zone_id,
                        label=g_label,
                        metadata={"group_only": True},
                    ))
                    scene_zone_ids[g_label] = zone_id
                    graph.add_edge_simple(zone_id, image_id, RelationType.POSITIONED_ON)

            # Hierarchy edges
            if design.labels and design.labels.hierarchy and design.labels.hierarchy.enabled:
                for group in design.labels.hierarchy.groups:
                    parent_zid = scene_zone_ids.get(group.parent)
                    if parent_zid:
                        for child_label in group.children:
                            child_zid = scene_zone_ids.get(child_label)
                            if child_zid:
                                graph.add_edge_simple(parent_zid, child_zid, RelationType.REVEALS)

            # Mechanic nodes
            for mi, mech in enumerate(scene.mechanics):
                mech_id = f"mech_{sn}_{mech.type}_{mi}"
                graph.add_node(MechanicNode(
                    id=mech_id,
                    mechanic_type=mech.type,
                    description=mech.description,
                    zone_labels_used=mech.zone_labels_used,
                    scoring=mech.scoring.model_dump() if mech.scoring else {},
                    feedback=mech.feedback.model_dump() if mech.feedback else {},
                ))
                graph.add_edge_simple(scene_id, mech_id, RelationType.CONTAINS)

                # Mechanic → zones it operates on
                for label_text in mech.zone_labels_used:
                    zid = scene_zone_ids.get(label_text)
                    if zid:
                        graph.add_edge_simple(mech_id, zid, RelationType.OPERATES_ON)

                # Labels available in this mechanic
                for label_text in mech.zone_labels_used:
                    lid = label_node_ids.get(label_text)
                    if lid:
                        graph.add_edge_simple(lid, mech_id, RelationType.AVAILABLE_IN)

                # Path node for trace_path
                if mech.type == "trace_path" and mech.path_config:
                    path_id = f"path_{sn}_{mi}"
                    graph.add_node(PathNode(
                        id=path_id,
                        description=mech.description,
                        path_type=mech.path_config.path_type,
                        waypoint_zone_ids=[
                            scene_zone_ids.get(wp, wp)
                            for wp in mech.path_config.waypoints
                        ],
                        visual_style=mech.path_config.visual_style,
                    ))
                    graph.add_edge_simple(mech_id, path_id, RelationType.FOLLOWS_PATH)

            # Media assets
            for asset in scene.media_assets:
                aid = f"asset_{sn}_{asset.id}"
                graph.add_node(AssetNode(
                    id=aid,
                    asset_type=asset.asset_type,
                    description=asset.description,
                    placement=asset.placement,
                    layer=asset.layer,
                    generation_prompt=asset.generation_prompt,
                    width=asset.width,
                    height=asset.height,
                ))
                graph.add_edge_simple(scene_id, aid, RelationType.CONTAINS)
                # Asset depends on image (must generate image first)
                graph.add_edge_simple(aid, image_id, RelationType.DEPENDS_ON)

            # Sounds
            for si, sound in enumerate(scene.sounds):
                sound_id = f"sound_{sn}_{sound.event}_{si}"
                graph.add_node(SoundNode(
                    id=sound_id,
                    sound_event=sound.event,
                    description=sound.description,
                    preset=sound.preset,
                    volume=sound.volume,
                ))
                graph.add_edge_simple(scene_id, sound_id, RelationType.CONTAINS)

        # Scene transitions
        for ti, trans in enumerate(design.scene_transitions):
            trans_id = f"transition_{trans.from_scene}_to_{trans.to_scene}"
            graph.add_node(TransitionNode(
                id=trans_id,
                from_id=f"scene_{trans.from_scene}",
                to_id=f"scene_{trans.to_scene}",
                trigger=trans.trigger,
                threshold=trans.threshold,
                animation=trans.animation,
                message=trans.message,
            ))
            graph.add_edge_simple(
                f"scene_{trans.from_scene}", trans_id, RelationType.TRANSITIONS_TO
            )

        # Global sounds
        for si, sound in enumerate(design.global_sounds):
            sound_id = f"sound_global_{sound.event}_{si}"
            graph.add_node(SoundNode(
                id=sound_id,
                sound_event=sound.event,
                description=sound.description,
                preset=sound.preset,
                volume=sound.volume,
            ))
            graph.add_edge_simple(game_id, sound_id, RelationType.CONTAINS)

        logger.info(
            f"AssetGraph.from_game_design: Built graph with "
            f"{graph.node_count} nodes, {graph.edge_count} edges "
            f"from design '{design.title}'"
        )
        return graph

    # -- Internal helpers --------------------------------------------------

    def _rebuild_indices(self) -> None:
        self._outgoing = defaultdict(list)
        self._incoming = defaultdict(list)
        for e in self._edges:
            self._outgoing[e.source].append(e)
            self._incoming[e.target].append(e)

    def __repr__(self) -> str:
        return f"AssetGraph(nodes={self.node_count}, edges={self.edge_count})"
