"""
Trace Path Workflow - Generates trace paths from zones and domain knowledge.

DEPENDS ON: labeling_diagram_workflow (needs zones)

Creates trace paths for concepts like:
- Blood flow through heart
- Signal paths through nervous system
- Process flows in chemical reactions
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.agents.workflows.base import (
    WorkflowContext, WorkflowResult, WorkflowRegistry, create_failed_result
)
from app.agents.workflows.types import TracePath, PathWaypoint

logger = logging.getLogger("gamed_ai.workflows.trace_path")


@WorkflowRegistry.register(
    name="trace_path",
    description="Generates trace paths from zones and domain knowledge sequences",
    output_type="paths"
)
async def trace_path_workflow(context: WorkflowContext) -> WorkflowResult:
    """
    Generate trace paths using zones from diagram workflow.

    Inputs from context:
        - dependencies["diagram"]: Result from labeling_diagram_workflow
        - domain_knowledge.sequence_flow_data: Sequence information
        - asset_spec.spec.concept: The path concept (e.g., "blood_flow")

    Outputs:
        - paths: List of TracePath objects with waypoints
    """
    asset_id = context.asset_spec.get("id", "paths")
    scene_number = context.scene_number
    started_at = datetime.utcnow().isoformat()

    # Get zones from dependencies
    diagram_dep = context.get_dependency("diagram")

    if not diagram_dep:
        return create_failed_result(
            "trace_path", asset_id, scene_number, "paths",
            "No diagram dependency found - trace_path requires labeling_diagram first"
        )

    zones = diagram_dep.data.get("diagram_zones", [])

    if not zones:
        return create_failed_result(
            "trace_path", asset_id, scene_number, "paths",
            "No zones available from diagram workflow"
        )

    # Get path concept from spec
    path_concept = context.get_spec_value("concept", "flow")

    # Extract sequence from domain_knowledge
    sequence_data = context.domain_knowledge.get("sequence_flow_data", {})
    sequence_items = sequence_data.get("sequence_items", [])

    if not sequence_items:
        # Try to infer from canonical labels
        canonical_labels = context.domain_knowledge.get("canonical_labels", [])
        sequence_items = _infer_sequence_from_labels(canonical_labels, path_concept)

    # Map sequence items to zones
    waypoints = []
    for i, item in enumerate(sequence_items):
        zone = _find_zone_by_label(zones, item)
        if zone:
            waypoints.append({
                "zone_id": zone["id"],
                "order": i + 1,
                "label": item,
                "x": zone.get("x"),
                "y": zone.get("y")
            })
        else:
            logger.warning(f"Could not find zone for sequence item: {item}")

    # Determine if path is cyclic
    is_cyclic = sequence_data.get("is_cyclic", False) or path_concept in ["circulation", "cycle"]

    path = {
        "id": f"path_{path_concept}",
        "concept": path_concept,
        "waypoints": waypoints,
        "description": sequence_data.get("description", f"Path showing {path_concept}"),
        "is_cyclic": is_cyclic
    }

    return WorkflowResult(
        success=True,
        workflow_name="trace_path",
        asset_id=asset_id,
        scene_number=scene_number,
        output_type="paths",
        data={
            "paths": [path],
            "path_concept": path_concept,
            "waypoint_count": len(waypoints),
            "is_cyclic": is_cyclic
        },
        started_at=started_at,
        completed_at=datetime.utcnow().isoformat()
    )


def _find_zone_by_label(zones: List[Dict], label: str) -> Optional[Dict]:
    """Find a zone by its label (case-insensitive, partial match)."""
    label_lower = label.lower().strip()

    # Exact match first
    for zone in zones:
        zone_label = zone.get("label", "").lower().strip()
        if zone_label == label_lower:
            return zone

    # Partial match (label contains or is contained)
    for zone in zones:
        zone_label = zone.get("label", "").lower().strip()
        if label_lower in zone_label or zone_label in label_lower:
            return zone

    # Word-based match
    label_words = set(label_lower.split())
    for zone in zones:
        zone_label = zone.get("label", "").lower().strip()
        zone_words = set(zone_label.split())
        if label_words & zone_words:  # Any common words
            return zone

    return None


def _infer_sequence_from_labels(labels: List[str], concept: str) -> List[str]:
    """
    Attempt to infer a sequence from labels when no explicit sequence provided.
    Uses heuristics based on common patterns.
    """
    concept_lower = concept.lower()

    # Blood flow / circulatory system patterns
    if any(term in concept_lower for term in ["blood", "flow", "circulat", "heart"]):
        order_hints = [
            "vena cava", "right atrium", "tricuspid", "right ventricle",
            "pulmonary valve", "pulmonary artery", "lung", "pulmonary vein",
            "left atrium", "mitral", "bicuspid", "left ventricle",
            "aortic valve", "aorta"
        ]
        return _order_labels_by_hints(labels, order_hints)

    # Digestive system patterns
    if any(term in concept_lower for term in ["digest", "food", "nutrient"]):
        order_hints = [
            "mouth", "esophagus", "stomach", "small intestine",
            "large intestine", "colon", "rectum"
        ]
        return _order_labels_by_hints(labels, order_hints)

    # Nervous system signal patterns
    if any(term in concept_lower for term in ["nerve", "signal", "neuron"]):
        order_hints = [
            "stimulus", "receptor", "sensory", "afferent",
            "brain", "motor", "efferent", "effector", "response"
        ]
        return _order_labels_by_hints(labels, order_hints)

    # Default: return labels as-is
    return labels


def _order_labels_by_hints(labels: List[str], order_hints: List[str]) -> List[str]:
    """Order labels based on hint sequence."""
    ordered = []
    used = set()

    for hint in order_hints:
        hint_lower = hint.lower()
        for label in labels:
            if label not in used:
                label_lower = label.lower()
                if hint_lower in label_lower or label_lower in hint_lower:
                    ordered.append(label)
                    used.add(label)
                    break

    # Add any remaining labels at the end
    for label in labels:
        if label not in used:
            ordered.append(label)

    return ordered if ordered else labels
