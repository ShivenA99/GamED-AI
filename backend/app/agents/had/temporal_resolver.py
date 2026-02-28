"""
Temporal Resolver for Zone Visibility Management

Implements a Petri Net-inspired constraint system for managing zone visibility
in label diagram games. Ensures overlapping zones from different hierarchies
never appear simultaneously, preventing visual clutter.

Key Concepts:
- Tokens = zones
- Places = visibility states (hidden, pending, active, completed)
- Transitions = user actions (label placement, scene change)

Constraint Types:
- MUTEX: Two zones cannot be visible simultaneously
- CONCURRENT: Two zones can appear together (same hierarchy)
- BEFORE/AFTER: Sequential ordering constraints
- SEQUENCE: Strict order for motion paths

Priority Levels:
- 100: Scene boundaries (highest - cannot override)
- 50:  Hierarchy rules (parent-child relationships)
- 10:  Spatial overlap (auto-generated mutex)
- 1:   Pedagogical hints (from agents, lowest)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.had.temporal_resolver")


@dataclass
class TemporalConstraint:
    """A constraint between two zones defining their temporal relationship."""
    zone_a: str
    zone_b: str
    constraint_type: str  # "before", "after", "mutex", "concurrent", "sequence"
    reason: str
    priority: int = 1


@dataclass
class TemporalState:
    """Current state of zone visibility based on temporal constraints."""
    active_zones: Set[str] = field(default_factory=set)
    completed_zones: Set[str] = field(default_factory=set)
    blocked_zones: Set[str] = field(default_factory=set)
    pending_zones: Set[str] = field(default_factory=set)


def generate_temporal_constraints(
    zones: List[Dict[str, Any]],
    zone_groups: Optional[List[Dict[str, Any]]] = None,
    collision_metadata: Optional[Dict[str, Any]] = None,
    scene_number: Optional[int] = None,
) -> List[TemporalConstraint]:
    """
    RULE-BASED temporal constraint generation (NO LLM).

    This is the core algorithm that automatically derives temporal
    relationships from spatial and hierarchical data.

    Priority Levels:
      - 100: Scene boundaries (zones in different scenes never overlap)
      - 50:  Hierarchy rules (parent-child always concurrent)
      - 10:  Spatial overlap (mutex for different-hierarchy overlaps)
      - 1:   Pedagogical hints (from agent, lowest priority)

    Args:
        zones: List of zone definitions with id, label, hierarchyLevel, parentZoneId
        zone_groups: List of zone group definitions with parent/child relationships
        collision_metadata: Overlap detection metadata from zone_collision_resolver
        scene_number: Current scene number for multi-scene games

    Returns:
        List of TemporalConstraint objects sorted by priority (highest first)
    """
    constraints: List[TemporalConstraint] = []

    if not zones:
        return constraints

    # =========================================================================
    # STEP 1: Build hierarchy lookup structures (O(n) preprocessing)
    # =========================================================================
    parent_to_children: Dict[str, List[str]] = {}
    child_to_parent: Dict[str, str] = {}
    siblings: Dict[str, List[str]] = {}
    zone_by_id: Dict[str, Dict[str, Any]] = {z.get("id", ""): z for z in zones if z.get("id")}

    # Build from zone_groups
    if zone_groups:
        for group in zone_groups:
            parent_id = group.get("parentZoneId") or group.get("parent_zone_id")
            child_ids = group.get("childZoneIds") or group.get("child_zone_ids", [])

            if parent_id:
                parent_to_children[parent_id] = child_ids
                for child_id in child_ids:
                    child_to_parent[child_id] = parent_id
                    siblings[child_id] = [c for c in child_ids if c != child_id]

    # Also build from zone parentZoneId if present
    for zone in zones:
        zone_id = zone.get("id", "")
        parent_id = zone.get("parentZoneId")
        if parent_id and zone_id:
            child_to_parent[zone_id] = parent_id
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            if zone_id not in parent_to_children[parent_id]:
                parent_to_children[parent_id].append(zone_id)

    logger.debug(f"Built hierarchy: {len(parent_to_children)} parents, {len(child_to_parent)} children")

    # =========================================================================
    # STEP 2: Generate CONCURRENT constraints for parent-child relationships
    # =========================================================================
    for parent_id, child_ids in parent_to_children.items():
        for child_id in child_ids:
            constraints.append(TemporalConstraint(
                zone_a=parent_id,
                zone_b=child_id,
                constraint_type="concurrent",
                reason="parent_child_hierarchy",
                priority=50,
            ))

        # Siblings can also appear together (same parent)
        for i, child_a in enumerate(child_ids):
            for child_b in child_ids[i + 1:]:
                constraints.append(TemporalConstraint(
                    zone_a=child_a,
                    zone_b=child_b,
                    constraint_type="concurrent",
                    reason="same_parent_siblings",
                    priority=50,
                ))

    # =========================================================================
    # STEP 3: Process overlapping zone pairs for MUTEX constraints
    # =========================================================================
    overlapping_pairs = []

    if collision_metadata:
        # Try different keys for backward compatibility
        overlapping_pairs = collision_metadata.get("overlapping_pairs", [])
        if not overlapping_pairs:
            before_data = collision_metadata.get("before", {})
            overlapping_pairs = before_data.get("overlapping_zone_pairs", [])
        if not overlapping_pairs:
            after_data = collision_metadata.get("after", {})
            overlapping_pairs = after_data.get("discrete_overlaps", [])

    for overlap in overlapping_pairs:
        zone_a = overlap.get("zone_a") or overlap.get("zone_a_id")
        zone_b = overlap.get("zone_b") or overlap.get("zone_b_id")
        iou = overlap.get("iou", 0)

        if not zone_a or not zone_b:
            continue

        # Skip trivial overlaps
        if iou < 0.01:
            continue

        # Determine relationship between zones
        relationship = _classify_relationship(
            zone_a, zone_b, parent_to_children, child_to_parent, siblings
        )

        if relationship == "parent_child":
            # Already added as concurrent above
            pass

        elif relationship == "siblings":
            # Already added as concurrent above
            pass

        elif relationship == "layered":
            # Zones with "composed_of" relationship are intentional layers
            constraints.append(TemporalConstraint(
                zone_a=zone_a,
                zone_b=zone_b,
                constraint_type="concurrent",
                reason="intentional_layering",
                priority=50,
            ))

        elif relationship == "same_hierarchy":
            # Part of the same hierarchy tree - allow concurrent
            constraints.append(TemporalConstraint(
                zone_a=zone_a,
                zone_b=zone_b,
                constraint_type="concurrent",
                reason="same_hierarchy_tree",
                priority=40,
            ))

        else:
            # DIFFERENT HIERARCHIES - This is the key mutex case
            # These zones should NEVER appear at the same time
            constraints.append(TemporalConstraint(
                zone_a=zone_a,
                zone_b=zone_b,
                constraint_type="mutex",
                reason="spatial_overlap_different_hierarchy",
                priority=10,
            ))
            logger.debug(f"Created MUTEX constraint: {zone_a} <-> {zone_b} (IoU={iou:.2f})")

    # =========================================================================
    # STEP 4: Sort by priority (highest first)
    # =========================================================================
    constraints.sort(key=lambda c: -c.priority)

    logger.info(
        f"Generated {len(constraints)} temporal constraints: "
        f"{sum(1 for c in constraints if c.constraint_type == 'mutex')} mutex, "
        f"{sum(1 for c in constraints if c.constraint_type == 'concurrent')} concurrent"
    )

    return constraints


def _classify_relationship(
    zone_a: str,
    zone_b: str,
    parent_to_children: Dict[str, List[str]],
    child_to_parent: Dict[str, str],
    siblings: Dict[str, List[str]],
) -> str:
    """
    Classify the relationship between two zones.

    Returns:
        "parent_child" - Direct parent-child relationship
        "siblings" - Same parent
        "same_hierarchy" - Share a common ancestor
        "layered" - Intentional layering (composed_of)
        "unrelated" - Different hierarchies
    """
    # Check parent-child
    if zone_a in parent_to_children and zone_b in parent_to_children[zone_a]:
        return "parent_child"
    if zone_b in parent_to_children and zone_a in parent_to_children[zone_b]:
        return "parent_child"

    # Check siblings (same parent)
    if zone_a in siblings and zone_b in siblings[zone_a]:
        return "siblings"
    if zone_b in siblings and zone_a in siblings[zone_b]:
        return "siblings"

    # Check if they share a common ancestor (same hierarchy tree)
    ancestor_a = _get_root_ancestor(zone_a, child_to_parent)
    ancestor_b = _get_root_ancestor(zone_b, child_to_parent)
    if ancestor_a and ancestor_b and ancestor_a == ancestor_b:
        return "same_hierarchy"

    # No relationship - different hierarchies
    return "unrelated"


def _get_root_ancestor(zone_id: str, child_to_parent: Dict[str, str]) -> Optional[str]:
    """Traverse up to find root ancestor."""
    current = zone_id
    visited: Set[str] = set()

    while current in child_to_parent and current not in visited:
        visited.add(current)
        current = child_to_parent[current]

    return current if current else None


class TemporalResolver:
    """
    Petri Net-inspired resolver for zone visibility.

    Tokens = zones
    Places = visibility states (hidden, pending, active, completed)
    Transitions = user actions (label placement, scene change)
    """

    def __init__(self, constraints: List[TemporalConstraint]):
        """
        Initialize resolver with temporal constraints.

        Args:
            constraints: List of TemporalConstraint objects
        """
        self.constraints = constraints
        self.mutex_graph = self._build_mutex_graph()
        self.concurrent_pairs = self._build_concurrent_pairs()
        self.sequence_graph = self._build_sequence_graph()

    def _build_mutex_graph(self) -> Dict[str, Set[str]]:
        """Build graph of mutex relationships for O(1) lookups."""
        graph: Dict[str, Set[str]] = {}

        for c in self.constraints:
            if c.constraint_type == "mutex":
                if c.zone_a not in graph:
                    graph[c.zone_a] = set()
                if c.zone_b not in graph:
                    graph[c.zone_b] = set()
                graph[c.zone_a].add(c.zone_b)
                graph[c.zone_b].add(c.zone_a)

        return graph

    def _build_concurrent_pairs(self) -> Set[Tuple[str, str]]:
        """Build set of concurrent pairs."""
        pairs: Set[Tuple[str, str]] = set()

        for c in self.constraints:
            if c.constraint_type == "concurrent":
                # Store in sorted order for consistent lookup
                pair = tuple(sorted([c.zone_a, c.zone_b]))
                pairs.add(pair)

        return pairs

    def _build_sequence_graph(self) -> Dict[str, List[str]]:
        """Build graph of sequence/before relationships."""
        graph: Dict[str, List[str]] = {}

        for c in self.constraints:
            if c.constraint_type in ("before", "sequence"):
                if c.zone_a not in graph:
                    graph[c.zone_a] = []
                graph[c.zone_a].append(c.zone_b)

        return graph

    def get_visible_zones(
        self,
        all_zones: List[Dict[str, Any]],
        completed_zones: Set[str],
        current_scene: Optional[int] = None,
    ) -> Tuple[Set[str], Set[str]]:
        """
        Compute which zones should be visible given current state.

        Algorithm:
        1. Start with all level-1 zones (roots)
        2. Add children of completed parents
        3. REMOVE any zones that mutex with currently visible zones
        4. Apply scene filtering

        Args:
            all_zones: List of all zone definitions
            completed_zones: Set of zone IDs that have been correctly labeled
            current_scene: Current scene number (for multi-scene filtering)

        Returns:
            Tuple of (visible_zones, blocked_zones)
        """
        visible: Set[str] = set()
        blocked: Set[str] = set()

        # Filter to current scene if specified
        if current_scene is not None:
            scene_zones = [
                z for z in all_zones
                if z.get("scene_number", 1) == current_scene
            ]
        else:
            scene_zones = all_zones

        # Get zone hierarchy levels
        zone_levels: Dict[str, int] = {}
        zone_parents: Dict[str, str] = {}
        for zone in scene_zones:
            zone_id = zone.get("id", "")
            zone_levels[zone_id] = zone.get("hierarchyLevel", 1)
            if zone.get("parentZoneId"):
                zone_parents[zone_id] = zone.get("parentZoneId")

        # Start with root zones (level 1 or no parent)
        root_zones = [
            z.get("id") for z in scene_zones
            if zone_levels.get(z.get("id", ""), 1) == 1
            or z.get("id") not in zone_parents
        ]

        # Add root zones that aren't blocked
        for zone_id in root_zones:
            if zone_id and not self._is_blocked_by_mutex(zone_id, visible, completed_zones):
                visible.add(zone_id)
            elif zone_id:
                blocked.add(zone_id)

        # Add children of completed parents
        for zone_id in list(completed_zones):
            # Find children of this zone
            for zone in scene_zones:
                if zone.get("parentZoneId") == zone_id:
                    child_id = zone.get("id", "")
                    if child_id and not self._is_blocked_by_mutex(child_id, visible, completed_zones):
                        visible.add(child_id)
                    elif child_id:
                        blocked.add(child_id)

        # Check for sequence constraints
        for zone_id in list(visible):
            if not self._has_met_prerequisites(zone_id, completed_zones):
                visible.discard(zone_id)
                blocked.add(zone_id)

        return visible, blocked

    def _is_blocked_by_mutex(
        self,
        zone_id: str,
        visible_zones: Set[str],
        completed_zones: Set[str],
    ) -> bool:
        """
        Check if zone is blocked by mutex constraint with any visible zone.

        A zone is blocked if:
        1. It has a mutex constraint with a currently visible zone
        2. AND neither zone is completed (completed zones can coexist)
        """
        mutex_partners = self.mutex_graph.get(zone_id, set())

        for visible_zone in visible_zones:
            if visible_zone in mutex_partners:
                # If the visible zone is completed, we might unblock this zone
                # depending on hierarchy relationships
                if visible_zone not in completed_zones:
                    return True

        return False

    def _has_met_prerequisites(
        self,
        zone_id: str,
        completed_zones: Set[str],
    ) -> bool:
        """
        Check if zone has met all prerequisite (before) constraints.
        """
        # Find all zones that must be completed before this one
        for c in self.constraints:
            if c.constraint_type in ("before", "sequence"):
                if c.zone_b == zone_id:
                    # zone_a must be completed before zone_b can appear
                    if c.zone_a not in completed_zones:
                        return False

        return True

    def get_zones_to_hide_on_complete(
        self,
        completed_zone_id: str,
        currently_visible: Set[str],
    ) -> Set[str]:
        """
        Determine which zones should be hidden when a zone is completed.

        When a zone's hierarchy is fully complete, zones that had mutex
        with it can now become visible, and this zone can fade out.

        Args:
            completed_zone_id: ID of the zone that was just completed
            currently_visible: Set of currently visible zone IDs

        Returns:
            Set of zone IDs that should be hidden/faded out
        """
        to_hide: Set[str] = set()

        # Check if completing this zone allows mutex partners to appear
        mutex_partners = self.mutex_graph.get(completed_zone_id, set())

        # For now, keep completed zones visible but dimmed
        # The frontend will handle the visual state change

        return to_hide

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert constraints to list of dicts for JSON serialization."""
        return [
            {
                "zone_a": c.zone_a,
                "zone_b": c.zone_b,
                "constraint_type": c.constraint_type,
                "reason": c.reason,
                "priority": c.priority,
            }
            for c in self.constraints
        ]


def constraints_to_dict_list(constraints: List[TemporalConstraint]) -> List[Dict[str, Any]]:
    """Convert constraints to list of dicts for JSON serialization."""
    return [
        {
            "zone_a": c.zone_a,
            "zone_b": c.zone_b,
            "constraint_type": c.constraint_type,
            "reason": c.reason,
            "priority": c.priority,
        }
        for c in constraints
    ]


def add_pedagogical_hints(
    constraints: List[TemporalConstraint],
    suggested_order: Optional[List[str]] = None,
    sequence_hints: Optional[List[Dict[str, Any]]] = None,
) -> List[TemporalConstraint]:
    """
    Add pedagogical ordering hints from agent to existing constraints.

    Agent hints have lowest priority (1) and cannot override mutex constraints.

    Args:
        constraints: Existing temporal constraints
        suggested_order: Suggested zone reveal order from agent
        sequence_hints: Explicit sequence constraints from agent

    Returns:
        Combined list of constraints with pedagogical hints added
    """
    new_constraints = list(constraints)

    # Add sequence constraints from suggested order
    if suggested_order:
        for i in range(len(suggested_order) - 1):
            new_constraints.append(TemporalConstraint(
                zone_a=suggested_order[i],
                zone_b=suggested_order[i + 1],
                constraint_type="before",
                reason="pedagogical_suggested_order",
                priority=1,
            ))

    # Add explicit sequence hints
    if sequence_hints:
        for hint in sequence_hints:
            new_constraints.append(TemporalConstraint(
                zone_a=hint.get("zone_a", ""),
                zone_b=hint.get("zone_b", ""),
                constraint_type=hint.get("type", "before"),
                reason=hint.get("reason", "pedagogical_hint"),
                priority=hint.get("priority", 1),
            ))

    # Re-sort by priority
    new_constraints.sort(key=lambda c: -c.priority)

    return new_constraints
