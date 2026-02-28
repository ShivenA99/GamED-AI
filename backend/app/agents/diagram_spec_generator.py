"""
Diagram SVG Spec Generator Agent

Creates a structured SVG specification for INTERACTIVE_DIAGRAM templates.
The spec is later rendered into a final SVG asset.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.agents.schemas.interactive_diagram import (
    DiagramSvgSpec,
    get_diagram_svg_spec_schema
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.diagram_spec_generator")

# Subject-based color themes for diagram styling
# Each theme has primary (zones), secondary (background), and accent (highlights)
SUBJECT_COLOR_THEMES = {
    "biology": {"primary": "#22c55e", "secondary": "#86efac", "accent": "#ef4444"},
    "anatomy": {"primary": "#ef4444", "secondary": "#fecaca", "accent": "#3b82f6"},
    "physiology": {"primary": "#ef4444", "secondary": "#fecaca", "accent": "#8b5cf6"},
    "geography": {"primary": "#22c55e", "secondary": "#bbf7d0", "accent": "#0ea5e9"},
    "geology": {"primary": "#ca8a04", "secondary": "#fef08a", "accent": "#78716c"},
    "chemistry": {"primary": "#6366f1", "secondary": "#c7d2fe", "accent": "#f59e0b"},
    "physics": {"primary": "#0ea5e9", "secondary": "#bae6fd", "accent": "#f97316"},
    "astronomy": {"primary": "#1e3a8a", "secondary": "#3b82f6", "accent": "#fbbf24"},
    "botany": {"primary": "#16a34a", "secondary": "#dcfce7", "accent": "#facc15"},
    "zoology": {"primary": "#ea580c", "secondary": "#fed7aa", "accent": "#22c55e"},
    "ecology": {"primary": "#15803d", "secondary": "#bbf7d0", "accent": "#0ea5e9"},
    "history": {"primary": "#92400e", "secondary": "#fef3c7", "accent": "#1f2937"},
    "mathematics": {"primary": "#7c3aed", "secondary": "#ede9fe", "accent": "#06b6d4"},
    "computer science": {"primary": "#059669", "secondary": "#d1fae5", "accent": "#f43f5e"},
    "engineering": {"primary": "#475569", "secondary": "#e2e8f0", "accent": "#f97316"},
    "medicine": {"primary": "#dc2626", "secondary": "#fee2e2", "accent": "#2563eb"},
    "default": {"primary": "#3b82f6", "secondary": "#dbeafe", "accent": "#8b5cf6"}
}


def _get_theme_for_subject(subject: str) -> Dict[str, str]:
    """Get color theme based on subject, with fallback to default."""
    if not subject:
        return SUBJECT_COLOR_THEMES["default"]

    subject_lower = subject.lower().strip()

    # Direct match
    if subject_lower in SUBJECT_COLOR_THEMES:
        return SUBJECT_COLOR_THEMES[subject_lower]

    # Partial match (e.g., "human anatomy" matches "anatomy")
    for key in SUBJECT_COLOR_THEMES:
        if key in subject_lower or subject_lower in key:
            return SUBJECT_COLOR_THEMES[key]

    # Category-based fallback
    if any(term in subject_lower for term in ["life", "living", "organism", "cell"]):
        return SUBJECT_COLOR_THEMES["biology"]
    if any(term in subject_lower for term in ["earth", "rock", "mineral", "volcano"]):
        return SUBJECT_COLOR_THEMES["geology"]
    if any(term in subject_lower for term in ["space", "star", "planet", "solar"]):
        return SUBJECT_COLOR_THEMES["astronomy"]
    if any(term in subject_lower for term in ["code", "programming", "algorithm", "software"]):
        return SUBJECT_COLOR_THEMES["computer science"]

    return SUBJECT_COLOR_THEMES["default"]

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
SPEC_PROMPT_FILE = PROMPTS_DIR / "diagram_svg_spec_interactive_diagram.txt"


def _load_spec_prompt() -> Optional[str]:
    if SPEC_PROMPT_FILE.exists():
        return SPEC_PROMPT_FILE.read_text()
    return None


def _build_default_spec(blueprint: Dict[str, Any], subject: str = None) -> Dict[str, Any]:
    """
    Build default SVG spec from blueprint with subject-based theming.

    Args:
        blueprint: The game blueprint containing diagram and labels
        subject: Optional subject for color theming (e.g., "biology", "anatomy")

    Returns:
        Default SVG spec dictionary
    """
    diagram = blueprint.get("diagram", {})
    labels = blueprint.get("labels", []) or []
    zones = diagram.get("zones", []) or []

    # Get subject-based color theme
    theme = _get_theme_for_subject(subject)
    primary_color = theme["primary"]
    secondary_color = theme["secondary"]

    def _coerce_dimension(value: Any, fallback_value: int) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            raw = value.strip().lower()
            if raw.endswith("px"):
                raw = raw[:-2].strip()
            if raw.isdigit():
                return int(raw)
        return fallback_value
    width = _coerce_dimension(diagram.get("width"), 800)
    height = _coerce_dimension(diagram.get("height"), 600)

    zone_map = {z.get("id"): z for z in zones if isinstance(z, dict)}

    spec_zones = []
    for idx, label in enumerate(labels, start=1):
        if not isinstance(label, dict):
            continue
        zone_id = label.get("correctZoneId") or f"zone_{idx}"
        zone = zone_map.get(zone_id, {})

        # Determine marker shape from zone data
        marker_shape = "circle"
        if zone.get("shape") == "polygon" and zone.get("points"):
            marker_shape = "polygon"

        spec_zones.append({
            "id": zone_id,
            "label": label.get("text") or zone.get("label") or f"Zone {idx}",
            "x": zone.get("x", 50),
            "y": zone.get("y", 50),
            "radius": zone.get("radius", 10),
            "color": primary_color,  # Use theme color
            "markerShape": marker_shape,
            # Include polygon points if available
            **({"points": zone.get("points")} if zone.get("points") else {})
        })

    return {
        "canvas": {"width": width, "height": height},
        "background": {
            "style": "grid",
            "primary": "#f8fafc",
            "secondary": secondary_color  # Use theme secondary color
        },
        "showLabels": False,
        "legend": {
            "title": "Labels",
            "items": [
                {"label": z.get("label", ""), "color": z.get("color", primary_color)}
                for z in spec_zones
                if isinstance(z, dict)
            ]
        },
        "zones": spec_zones,
        "decorations": [],
        "theme": theme  # Include theme for downstream use
    }


def _validate_spec(spec: Dict[str, Any], labels: List[Dict[str, Any]]) -> List[str]:
    errors = []
    try:
        DiagramSvgSpec.model_validate(spec)
    except Exception as e:
        errors.append(str(e))
    if len(spec.get("zones", [])) != len(labels):
        errors.append("Zones count does not match labels count")
    return errors


async def diagram_spec_generator_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    """
    Generate SVG spec for INTERACTIVE_DIAGRAM templates.

    Stores spec in state['diagram_spec'].
    Uses subject-based color theming from pedagogical_context.
    """
    blueprint = state.get("blueprint", {})
    template_type = blueprint.get("templateType", state.get("template_selection", {}).get("template_type"))

    if template_type != "INTERACTIVE_DIAGRAM":
        return {**state, "current_agent": "diagram_spec_generator"}

    # Extract subject for theming
    ped_context = state.get("pedagogical_context", {}) or {}
    subject = ped_context.get("subject", "")

    default_spec = _build_default_spec(blueprint, subject=subject)
    logger.info(f"Using theme for subject '{subject}': {default_spec.get('theme', {}).get('primary', 'default')}")
    prompt = _load_spec_prompt()

    if not prompt:
        return {
            **state,
            "diagram_spec": default_spec,
            "current_agent": "diagram_spec_generator"
        }

    question_text = state.get("question_text", "")
    ped_context = state.get("pedagogical_context", {}) or {}
    asset_prompt = blueprint.get("diagram", {}).get("assetPrompt", "")
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    prev_errors = state.get("current_validation_errors", [])
    error_context = "\n".join(f"- {err}" for err in prev_errors) if prev_errors else "None"
    context_section = f"""
## GENERATION CONTEXT
Question: {question_text}
Subject: {ped_context.get("subject", "General")}
Difficulty: {ped_context.get("difficulty", "intermediate")}
Asset Prompt: {asset_prompt}
Labels: {json.dumps([l.get("text") for l in blueprint.get("labels", []) if isinstance(l, dict)])}
Zones: {json.dumps(blueprint.get("diagram", {}).get("zones", []))}
Canonical Labels: {json.dumps(domain_knowledge.get("canonical_labels", []))}
Acceptable Variants: {json.dumps(domain_knowledge.get("acceptable_variants", {}))}
Previous Validation Errors: {error_context}
"""

    try:
        llm = get_llm_service()
        spec = await llm.generate_json_for_agent(
            agent_name="diagram_spec_generator",
            prompt=prompt + context_section,
            schema_hint="Valid diagram SVG spec JSON",
            json_schema=get_diagram_svg_spec_schema()
        )

        # Extract LLM metrics for instrumentation
        llm_metrics = spec.pop("_llm_metrics", None)
        if ctx and llm_metrics:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms"),
            )

        errors = _validate_spec(spec, blueprint.get("labels", []) or [])
        if errors:
            logger.warning(f"DiagramSpecGenerator: invalid spec, repairing with fallback. Errors: {errors}")
            spec = default_spec

        return {
            **state,
            "diagram_spec": spec,
            "current_agent": "diagram_spec_generator"
        }
    except Exception as e:
        logger.error(f"DiagramSpecGenerator: failed: {e}", exc_info=True)
        return {
            **state,
            "diagram_spec": default_spec,
            "current_agent": "diagram_spec_generator",
            "error_message": f"DiagramSpecGenerator failed: {str(e)}"
        }


async def validate_diagram_spec(spec: Dict[str, Any], config) -> tuple[bool, float, str]:
    """Validate diagram SVG spec against schema."""
    try:
        DiagramSvgSpec.model_validate(spec)
        return True, 1.0, ""
    except Exception as e:
        return False, 0.0, str(e)
