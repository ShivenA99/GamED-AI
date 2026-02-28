"""
Diagram Analyzer Agent (Preset 2 Only)

Reasoning-based agent that replaces keyword-matching diagram type classification.
Analyzes the educational question to determine optimal visualization strategy.

CRITICAL: This agent is ONLY used when PIPELINE_PRESET=advanced_interactive_diagram.
Preset 1 (interactive_diagram_hierarchical) MUST remain completely untouched.

Outputs:
- Content type analysis (anatomy, process, comparison, etc.)
- Key structures that need zones
- Relationships between elements
- Recommended zone strategy
- Reasoning explanation
"""

import json
import os
from typing import Dict, Any, List, Optional

from app.agents.state import AgentState
from app.services.llm_service import get_llm_service
from app.utils.logging_config import get_logger
from app.agents.instrumentation import InstrumentedAgentContext

logger = get_logger("gamed_ai.agents.diagram_analyzer")


# Zone strategies that the agent can recommend
ZONE_STRATEGIES = {
    "vlm_per_label": {
        "description": "Use VLM to detect each label location individually",
        "best_for": ["anatomy", "labeled diagrams", "component identification"],
        "supports": ["circles", "polygons"]
    },
    "polygon_boundary": {
        "description": "Detect exact polygon boundaries around structures",
        "best_for": ["precise outlines", "overlapping structures", "complex shapes"],
        "supports": ["polygons"]
    },
    "sequential_regions": {
        "description": "Detect ordered regions for process flows",
        "best_for": ["timelines", "sequences", "flowcharts"],
        "supports": ["rectangles", "arrows"]
    },
    "hierarchical_detection": {
        "description": "Detect nested/hierarchical structures with parent-child relationships",
        "best_for": ["org charts", "taxonomies", "nested anatomical structures"],
        "supports": ["circles", "rectangles", "hierarchical_groups"]
    },
    "comparative_dual": {
        "description": "Detect matching zones in two side-by-side diagrams",
        "best_for": ["comparison diagrams", "before/after", "A vs B"],
        "supports": ["paired_zones"]
    },
    "grid_detection": {
        "description": "Detect regular grid-aligned elements",
        "best_for": ["tables", "matrices", "periodic table"],
        "supports": ["rectangles", "grid_cells"]
    }
}


DIAGRAM_ANALYSIS_PROMPT = """You are an expert educational content analyst. Analyze this educational question to determine the optimal visualization and interaction strategy.

## Question to Analyze:
{question_text}

## Domain Knowledge (if available):
{domain_context}

## Available Zone Detection Strategies:
{zone_strategies}

## Your Task:
Reason step-by-step about the content:

1. **Content Type**: What TYPE of visual representation best serves this content?
   - anatomy: parts of biological structures, organs, cells
   - process: sequences, flows, cycles, steps
   - comparison: side-by-side structures, before/after
   - timeline: chronological events, history
   - spatial: maps, geography, layouts
   - hierarchy: organizational charts, taxonomies, nested structures
   - abstract: concepts, relationships, theoretical models

2. **Key Structures**: What specific STRUCTURES need to be identifiable?
   - List the main elements that require zones/labels

3. **Relationships**: What RELATIONSHIPS exist between elements?
   - hierarchy: parent-child, container-contained
   - sequence: before-after, step order
   - cause-effect: triggers, results
   - comparison: similar, different, unique

4. **Zone Strategy**: Which zone detection strategy would capture these accurately?

5. **Multi-Scene Need**: Does this content benefit from multiple scenes/perspectives?
   - Consider: "Label X AND show Y" = multi-scene
   - Consider: nested detail = zoom-in scenes

## Response Format (JSON):
{{
    "diagram_analysis": {{
        "content_type": "<anatomy|process|comparison|timeline|spatial|hierarchy|abstract>",
        "key_structures": ["list of structures needing zones"],
        "relationships": {{
            "type": "<hierarchy|sequence|cause_effect|comparison|none>",
            "details": ["specific relationships found"]
        }},
        "recommended_zone_strategy": "<strategy_name>",
        "multi_scene_recommended": true/false,
        "multi_scene_reason": "<why multiple scenes would help or why not>",
        "reasoning": "<full explanation of your analysis>"
    }}
}}

Respond with ONLY valid JSON."""


async def diagram_analyzer(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Diagram Analyzer Agent - Reasoning-based content analysis.

    ONLY used when PIPELINE_PRESET=advanced_interactive_diagram.

    Inputs: question_text, domain_knowledge
    Outputs: diagram_analysis
    """
    # Check preset - only run for Preset 2
    preset = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")
    if preset != "advanced_interactive_diagram":
        logger.info(f"Skipping diagram_analyzer - preset is '{preset}', not 'advanced_interactive_diagram'")
        # Return explicit skip marker instead of empty dict to avoid downstream confusion
        return {
            "diagram_analysis": None,
            "diagram_analyzer_skipped": True,
            "current_agent": "diagram_analyzer"
        }

    question_id = state.get('question_id', 'unknown')
    logger.info("Processing question", question_id=question_id, agent_name="diagram_analyzer")

    question_text = state.get("question_text", "")
    domain_knowledge = state.get("domain_knowledge", {})

    # Format domain context
    domain_context = "None available"
    if domain_knowledge:
        canonical_labels = domain_knowledge.get("canonical_labels", [])
        relationships = domain_knowledge.get("hierarchical_relationships", [])
        if canonical_labels:
            domain_context = f"Canonical labels: {', '.join(canonical_labels[:10])}"
        if relationships:
            rel_summary = ", ".join([f"{r.get('parent', '?')} -> {r.get('children', [])}" for r in relationships[:3]])
            domain_context += f"\nHierarchical relationships: {rel_summary}"

    # Format zone strategies
    zone_strategies = "\n".join([
        f"- {name}: {info['description']} (best for: {', '.join(info['best_for'][:2])})"
        for name, info in ZONE_STRATEGIES.items()
    ])

    # Build prompt
    prompt = DIAGRAM_ANALYSIS_PROMPT.format(
        question_text=question_text,
        domain_context=domain_context,
        zone_strategies=zone_strategies
    )

    try:
        llm = get_llm_service()
        result = await llm.generate_json_for_agent(
            agent_name="diagram_analyzer",
            prompt=prompt,
            schema_hint="diagram_analysis with content_type, key_structures, relationships, zone_strategy",
        )

        # Extract LLM metrics for instrumentation
        llm_metrics = result.pop("_llm_metrics", None) if isinstance(result, dict) else None
        if llm_metrics and ctx:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms")
            )

        # Normalize result
        diagram_analysis = result.get("diagram_analysis", result) if isinstance(result, dict) else {}

        # Ensure required fields
        diagram_analysis = _normalize_diagram_analysis(diagram_analysis, question_text)

        logger.info(
            "Diagram analysis complete",
            content_type=diagram_analysis.get("content_type"),
            zone_strategy=diagram_analysis.get("recommended_zone_strategy"),
            multi_scene=diagram_analysis.get("multi_scene_recommended")
        )

        return {
            "diagram_analysis": diagram_analysis,
            "current_agent": "diagram_analyzer"
        }

    except Exception as e:
        logger.error(
            "Diagram analysis failed, using fallback",
            exc_info=True,
            error_type=type(e).__name__,
            error_message=str(e)
        )

        # Track fallback usage
        if ctx:
            ctx.set_fallback_used(f"Diagram analysis failed: {str(e)}")

        # Create fallback analysis
        fallback = _create_fallback_analysis(question_text, domain_knowledge)

        return {
            "diagram_analysis": fallback,
            "current_agent": "diagram_analyzer",
            "error_message": f"DiagramAnalyzer fallback: {str(e)}"
        }


def _normalize_diagram_analysis(analysis: Dict[str, Any], question_text: str) -> Dict[str, Any]:
    """Normalize and validate diagram analysis result."""

    if not isinstance(analysis, dict):
        analysis = {}

    # Ensure content_type
    content_type = analysis.get("content_type", "")
    valid_types = ["anatomy", "process", "comparison", "timeline", "spatial", "hierarchy", "abstract"]
    if content_type not in valid_types:
        # Infer from question text
        content_type = _infer_content_type(question_text)
    analysis["content_type"] = content_type

    # Ensure key_structures is a list
    structures = analysis.get("key_structures", [])
    if not isinstance(structures, list):
        structures = []
    analysis["key_structures"] = structures

    # Ensure relationships
    relationships = analysis.get("relationships", {})
    if not isinstance(relationships, dict):
        relationships = {"type": "none", "details": []}
    analysis["relationships"] = relationships

    # Ensure zone strategy
    strategy = analysis.get("recommended_zone_strategy", "")
    if strategy not in ZONE_STRATEGIES:
        # Map content type to default strategy
        strategy = _get_default_strategy(content_type)
    analysis["recommended_zone_strategy"] = strategy

    # Ensure multi_scene fields
    analysis["multi_scene_recommended"] = bool(analysis.get("multi_scene_recommended", False))
    if "multi_scene_reason" not in analysis:
        analysis["multi_scene_reason"] = ""

    # Ensure reasoning
    if "reasoning" not in analysis:
        analysis["reasoning"] = f"Analyzed question for {content_type} content type"

    return analysis


def _infer_content_type(question_text: str) -> str:
    """Simple heuristic inference of content type from question text."""
    q_lower = question_text.lower()

    if any(kw in q_lower for kw in ["compare", "contrast", "difference", "similar"]):
        return "comparison"
    if any(kw in q_lower for kw in ["flow", "process", "cycle", "steps", "stages"]):
        return "process"
    if any(kw in q_lower for kw in ["timeline", "history", "chronological", "events"]):
        return "timeline"
    if any(kw in q_lower for kw in ["map", "geography", "location", "region"]):
        return "spatial"
    if any(kw in q_lower for kw in ["hierarchy", "organization", "structure within"]):
        return "hierarchy"
    if any(kw in q_lower for kw in ["label", "parts", "identify", "diagram", "anatomy"]):
        return "anatomy"

    return "anatomy"  # Default


def _get_default_strategy(content_type: str) -> str:
    """Get default zone strategy for a content type."""
    strategy_map = {
        "anatomy": "vlm_per_label",
        "process": "sequential_regions",
        "comparison": "comparative_dual",
        "timeline": "sequential_regions",
        "spatial": "polygon_boundary",
        "hierarchy": "hierarchical_detection",
        "abstract": "vlm_per_label"
    }
    return strategy_map.get(content_type, "vlm_per_label")


def _create_fallback_analysis(question_text: str, domain_knowledge: Dict) -> Dict[str, Any]:
    """Create fallback analysis when LLM fails."""
    content_type = _infer_content_type(question_text)

    # Extract structures from domain knowledge if available
    structures = []
    if domain_knowledge:
        structures = domain_knowledge.get("canonical_labels", [])[:10]

    # Detect multi-scene need from question structure
    multi_scene = "and" in question_text.lower() and any(
        kw in question_text.lower() for kw in ["label", "show", "explain", "trace", "identify"]
    )

    return {
        "content_type": content_type,
        "key_structures": structures,
        "relationships": {"type": "none", "details": []},
        "recommended_zone_strategy": _get_default_strategy(content_type),
        "multi_scene_recommended": multi_scene,
        "multi_scene_reason": "Multi-part question detected" if multi_scene else "Single focus question",
        "reasoning": f"Fallback analysis: inferred {content_type} from question keywords"
    }
