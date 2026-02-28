"""
Diagram Type Classifier Agent

Classifies the type of diagram needed based on the question text.
This helps determine the optimal zone detection strategy and
default interaction mode for the game.

Supported diagram types:
- anatomy: Body parts, organs, cells, structures
- flowchart: Processes, workflows, algorithms
- chart: Data visualizations, graphs, statistics
- map: Geography, regions, locations
- timeline: Chronological events, history
- org_chart: Organization hierarchies, structures
- circuit: Electrical schematics, components
- mathematical: Functions, coordinates, geometry

Inputs:
- question_text: The question to classify
- domain_knowledge: Optional domain knowledge for context

Outputs:
- diagram_type: The classified diagram type
- zone_strategy: Recommended zone detection strategy
- diagram_type_confidence: Confidence score (0-1)
"""

from typing import Dict, Any, Optional, List

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.config.presets.advanced_interactive_diagram import (
    DIAGRAM_TYPES,
    get_diagram_type_config,
    detect_diagram_type
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.diagram_type_classifier")


async def diagram_type_classifier_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Classify the diagram type from the question text.

    Uses a combination of:
    1. Keyword matching (fast, deterministic)
    2. Domain knowledge hints
    3. Optional VLM analysis if image is available

    Args:
        state: Current agent state with question_text and optional domain_knowledge
        ctx: Optional instrumentation context

    Returns:
        Updated state with diagram_type, zone_strategy, and confidence
    """
    question_id = state.get('question_id', 'unknown')
    logger.info("Processing question", question_id=question_id, agent_name="diagram_type_classifier")

    question_text = state.get("question_text", "")
    domain_knowledge = state.get("domain_knowledge", {})
    diagram_image = state.get("diagram_image")  # May not be available yet

    # Phase 1: Keyword-based classification
    keyword_type, keyword_confidence = _classify_by_keywords(question_text)

    # Phase 2: Domain knowledge enhancement
    domain_type, domain_confidence = _classify_by_domain_knowledge(domain_knowledge)

    # Phase 3: Combine classifications
    final_type, final_confidence = _combine_classifications(
        keyword_type, keyword_confidence,
        domain_type, domain_confidence
    )

    # Get configuration for the detected type
    type_config = get_diagram_type_config(final_type)

    result = {
        "diagram_type": final_type,
        "diagram_type_config": type_config,
        "zone_strategy": type_config.get("zone_strategy", "vlm_per_label"),
        "diagram_type_confidence": final_confidence,
        "diagram_search_suffix": type_config.get("search_suffix", "diagram labeled"),
        "default_interaction_mode": type_config.get("default_interaction", ""),
        "current_agent": "diagram_type_classifier",
    }

    logger.info(
        f"Classified diagram type: {final_type}",
        diagram_type=final_type,
        confidence=final_confidence,
        zone_strategy=result["zone_strategy"]
    )

    if ctx:
        ctx.complete(result)

    return result


def _classify_by_keywords(question_text: str) -> tuple[str, float]:
    """
    Classify diagram type using keyword matching.

    Args:
        question_text: The question text to analyze

    Returns:
        Tuple of (diagram_type, confidence)
    """
    question_lower = question_text.lower()

    # Score each diagram type based on keyword matches
    scores = {}
    total_keywords_matched = 0

    for dtype, config in DIAGRAM_TYPES.items():
        keywords = config.get("keywords", [])
        matches = sum(1 for kw in keywords if kw in question_lower)
        if matches > 0:
            scores[dtype] = matches
            total_keywords_matched += matches

    if not scores:
        # Default to anatomy if no matches
        return "anatomy", 0.3

    # Find the best match
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Calculate confidence based on how much better the best match is
    if total_keywords_matched > 0:
        # Base confidence on the proportion of keywords matched by the best type
        confidence = min(0.9, 0.4 + (best_score / total_keywords_matched) * 0.5)
    else:
        confidence = 0.4

    # Bonus for multiple matches
    if best_score >= 3:
        confidence = min(0.95, confidence + 0.2)
    elif best_score >= 2:
        confidence = min(0.9, confidence + 0.1)

    return best_type, confidence


def _classify_by_domain_knowledge(domain_knowledge: Dict[str, Any]) -> tuple[Optional[str], float]:
    """
    Classify diagram type using domain knowledge hints.

    Args:
        domain_knowledge: Domain knowledge dictionary

    Returns:
        Tuple of (diagram_type or None, confidence)
    """
    if not domain_knowledge or not isinstance(domain_knowledge, dict):
        return None, 0.0

    # Check for explicit diagram type in domain knowledge
    if "diagram_type" in domain_knowledge:
        return domain_knowledge["diagram_type"], 0.8

    # Check for subject hints
    subject = (domain_knowledge.get("subject") or "").lower()
    canonical_labels = domain_knowledge.get("canonical_labels", [])

    # Subject-based heuristics
    subject_type_map = {
        "biology": "anatomy",
        "anatomy": "anatomy",
        "chemistry": "anatomy",  # Molecular structures
        "physics": "circuit",
        "electronics": "circuit",
        "history": "timeline",
        "geography": "map",
        "math": "mathematical",
        "computer science": "flowchart",
        "business": "org_chart",
        "statistics": "chart",
    }

    for subject_kw, dtype in subject_type_map.items():
        if subject_kw in subject:
            return dtype, 0.6

    # Check canonical labels for hints
    if canonical_labels:
        labels_str = " ".join(str(l).lower() for l in canonical_labels)

        # Anatomy hints
        anatomy_keywords = ["heart", "lung", "brain", "cell", "organ", "muscle", "bone"]
        if any(kw in labels_str for kw in anatomy_keywords):
            return "anatomy", 0.7

        # Map hints
        map_keywords = ["country", "state", "city", "region", "continent", "ocean"]
        if any(kw in labels_str for kw in map_keywords):
            return "map", 0.7

        # Circuit hints
        circuit_keywords = ["resistor", "capacitor", "transistor", "voltage", "current"]
        if any(kw in labels_str for kw in circuit_keywords):
            return "circuit", 0.7

    return None, 0.0


def _combine_classifications(
    keyword_type: str,
    keyword_confidence: float,
    domain_type: Optional[str],
    domain_confidence: float
) -> tuple[str, float]:
    """
    Combine keyword and domain knowledge classifications.

    Args:
        keyword_type: Type from keyword classification
        keyword_confidence: Confidence from keyword classification
        domain_type: Type from domain knowledge (may be None)
        domain_confidence: Confidence from domain knowledge

    Returns:
        Tuple of (final_type, final_confidence)
    """
    if domain_type is None:
        # Only keyword classification available
        return keyword_type, keyword_confidence

    if keyword_type == domain_type:
        # Both agree - boost confidence
        combined_confidence = min(0.95, keyword_confidence + domain_confidence * 0.3)
        return keyword_type, combined_confidence

    # Classifications disagree - pick the one with higher confidence
    if domain_confidence > keyword_confidence:
        return domain_type, domain_confidence
    else:
        return keyword_type, keyword_confidence


def get_zone_strategy_for_type(diagram_type: str) -> str:
    """
    Get the recommended zone detection strategy for a diagram type.

    Args:
        diagram_type: The classified diagram type

    Returns:
        Zone strategy string
    """
    config = get_diagram_type_config(diagram_type)
    return config.get("zone_strategy", "vlm_per_label")


def get_search_suffix_for_type(diagram_type: str) -> str:
    """
    Get the recommended image search suffix for a diagram type.

    Args:
        diagram_type: The classified diagram type

    Returns:
        Search suffix string
    """
    config = get_diagram_type_config(diagram_type)
    return config.get("search_suffix", "diagram labeled educational")
