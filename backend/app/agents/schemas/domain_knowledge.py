"""
Pydantic schema for domain knowledge retrieval.
Used for guided decoding and validation of retrieved facts.

Includes query intent analysis for determining:
- What the user wants to learn (learning_focus)
- How detailed the learning should be (depth_preference)
- Optimal order to reveal labels (suggested_reveal_order)
- Whether multi-scene is beneficial (scene_hints)
- Sequence/flow data for order-based mechanics (sequence_flow_data)
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# SEQUENCE/FLOW DATA SCHEMAS (Phase 0: Multi-Mechanic Support)
# =============================================================================

class SequenceItem(BaseModel):
    """
    A single item in a sequence/flow.

    Used for order-based game mechanics (e.g., "show the order of blood flow").
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique identifier for this sequence item")
    text: str = Field(description="Display text for this item (e.g., 'Right Atrium')")
    order_index: int = Field(ge=0, description="Position in the correct order (0-indexed)")
    description: Optional[str] = Field(default=None, description="Educational description of this step")
    connects_to: Optional[List[str]] = Field(
        default=None,
        description="For branching flows: list of item IDs this connects to"
    )


class SequenceFlowData(BaseModel):
    """
    Sequence/flow data extracted from authoritative sources.

    Captures the correct ordering for process-based queries like
    "show the order of blood flow through the heart".
    """
    model_config = ConfigDict(extra="forbid")

    flow_type: Literal["linear", "cyclic", "branching"] = Field(
        default="linear",
        description="Type of sequence: 'linear' (A→B→C), 'cyclic' (A→B→C→A), 'branching' (A→B or C)"
    )
    sequence_items: List[SequenceItem] = Field(
        default_factory=list,
        description="Items in the sequence with their correct order"
    )
    flow_description: Optional[str] = Field(
        default=None,
        description="Natural language description of the flow/process"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL of the authoritative source for this sequence"
    )


class ContentCharacteristics(BaseModel):
    """
    Characteristics of the query content that determine what knowledge is needed.

    Used to trigger appropriate data retrieval (labels, sequence, comparison, etc.).
    """
    model_config = ConfigDict(extra="forbid")

    needs_labels: bool = Field(default=True, description="Whether label data is needed")
    needs_sequence: bool = Field(default=False, description="Whether sequence/order data is needed")
    needs_comparison: bool = Field(default=False, description="Whether comparison data is needed")
    sequence_type: Optional[str] = Field(
        default=None,
        description="Type of sequence if needs_sequence is True: 'linear', 'cyclic', 'branching'"
    )


class DomainKnowledgeSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None


class HierarchicalRelationship(BaseModel):
    """Parent-child relationship between labels in a diagram."""
    model_config = ConfigDict(extra="forbid")

    parent: str = Field(description="The parent/container label (e.g., 'stamen')")
    children: List[str] = Field(description="Child labels contained within the parent (e.g., ['anther', 'filament'])")
    relationship_type: Literal["contains", "composed_of", "subdivided_into", "has_part"] = Field(
        default="contains",
        description="Type of hierarchical relationship: 'composed_of'/'subdivided_into' for layered structures (allow overlap), 'contains'/'has_part' for discrete parts (no overlap)"
    )


class QueryIntent(BaseModel):
    """
    Analysis of what the user wants to learn from the question.

    This informs zone detection strategy and progressive reveal order.
    """
    model_config = ConfigDict(extra="forbid")

    learning_focus: Literal["identify_parts", "understand_structure", "trace_process", "compare_components"] = Field(
        default="identify_parts",
        description="What does the user want to learn? 'identify_parts' for basic labeling, 'understand_structure' for how parts relate, 'trace_process' for following a flow, 'compare_components' for similarities/differences"
    )
    depth_preference: Literal["overview", "detailed", "comprehensive"] = Field(
        default="detailed",
        description="How detailed should the learning be? 'overview' for main parts only, 'detailed' for main + sub-parts, 'comprehensive' for all levels"
    )
    suggested_progression: List[str] = Field(
        default_factory=list,
        description="Recommended order to learn labels based on pedagogical best practice (general before specific), spatial logic, and complexity"
    )


class SceneHint(BaseModel):
    """
    Hint for multi-scene game structuring.

    Suggests when content should be split into multiple scenes for better learning.
    """
    model_config = ConfigDict(extra="forbid")

    focus: str = Field(description="What labels/concepts this scene should focus on")
    reason: str = Field(description="Why this content needs a separate scene (e.g., 'detailed sub-structure', 'different view needed')")
    suggested_scope: Optional[str] = Field(
        default=None,
        description="Optional scope description (e.g., 'zoomed view of organelles', 'cross-section view')"
    )


class DomainKnowledge(BaseModel):
    """
    Retrieved canonical domain knowledge from web search.

    Enhanced with query intent analysis for HAD v3 multi-scene support
    and sequence/flow data for multi-mechanic support.
    """
    model_config = ConfigDict(extra="forbid")

    query: str
    canonical_labels: List[str] = Field(min_length=1)
    acceptable_variants: Dict[str, List[str]] = Field(default_factory=dict)
    hierarchical_relationships: Optional[List[HierarchicalRelationship]] = Field(
        default=None,
        description="Parent-child relationships where one part contains others (e.g., stamen contains anther + filament)"
    )
    sources: List[DomainKnowledgeSource] = Field(default_factory=list)

    # HAD v3: Query intent analysis
    query_intent: Optional[QueryIntent] = Field(
        default=None,
        description="Analysis of what the user wants to learn from this question"
    )
    suggested_reveal_order: Optional[List[str]] = Field(
        default=None,
        description="Optimal order to reveal labels for learning (parents before children, outer before inner)"
    )
    scene_hints: Optional[List[SceneHint]] = Field(
        default=None,
        description="Suggestions for multi-scene structuring when content is complex"
    )

    # Phase 0: Multi-mechanic support - sequence/flow data
    sequence_flow_data: Optional[SequenceFlowData] = Field(
        default=None,
        description="Sequence/ordering data for process-based queries (e.g., blood flow order)"
    )
    content_characteristics: Optional[ContentCharacteristics] = Field(
        default=None,
        description="Characteristics indicating what types of knowledge the query needs"
    )


class EnhancedDomainKnowledge(DomainKnowledge):
    """
    Extended domain knowledge with computed fields for HAD v3.

    Adds utility methods for zone detection and game planning.
    """
    model_config = ConfigDict(extra="allow")

    def get_hierarchy_depth(self) -> int:
        """Calculate the maximum hierarchy depth from relationships."""
        if not self.hierarchical_relationships:
            return 1

        # Build parent-child graph
        children_of = {}
        all_children = set()
        for rel in self.hierarchical_relationships:
            parent = rel.parent.lower()
            children_of[parent] = [c.lower() for c in rel.children]
            all_children.update(children_of[parent])

        # Find roots (parents that are not children of anything)
        roots = set(children_of.keys()) - all_children
        if not roots:
            roots = set(children_of.keys())

        # BFS to find max depth
        max_depth = 1
        visited = set()
        queue = [(r, 1) for r in roots]

        while queue:
            node, depth = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            max_depth = max(max_depth, depth)

            for child in children_of.get(node, []):
                queue.append((child, depth + 1))

        return max_depth

    def needs_multi_scene(self) -> bool:
        """Determine if multi-scene game structure is recommended."""
        # Explicit scene hints take priority
        if self.scene_hints and len(self.scene_hints) > 0:
            return True

        # Check hierarchy depth
        if self.get_hierarchy_depth() > 2:
            return True

        # Check label count
        if len(self.canonical_labels) > 12:
            return True

        return False

    def get_labels_by_level(self) -> Dict[int, List[str]]:
        """Group labels by their hierarchy level."""
        levels: Dict[int, List[str]] = {1: []}

        if not self.hierarchical_relationships:
            # All labels are level 1
            levels[1] = self.canonical_labels
            return levels

        # Build child-to-parent mapping
        child_to_parent = {}
        parent_labels = set()
        for rel in self.hierarchical_relationships:
            parent_labels.add(rel.parent.lower())
            for child in rel.children:
                child_to_parent[child.lower()] = rel.parent.lower()

        # Assign levels
        for label in self.canonical_labels:
            label_lower = label.lower()
            level = 1
            current = label_lower

            while current in child_to_parent:
                level += 1
                current = child_to_parent[current]

            if level not in levels:
                levels[level] = []
            levels[level].append(label)

        return levels


def get_domain_knowledge_schema() -> Dict[str, Any]:
    return DomainKnowledge.model_json_schema()


def get_enhanced_domain_knowledge_schema() -> Dict[str, Any]:
    return EnhancedDomainKnowledge.model_json_schema()
