"""
Diagram SVG Generator Agent

Creates a lightweight SVG diagram for INTERACTIVE_DIAGRAM templates so the
frontend can render a visual with zone markers without external assets.

This agent also sets the final completion flags (`generation_complete`, `asset_urls`)
that were previously handled by the now-removed asset_generator agent.
"""

import math
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.diagram_svg_generator")

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


def _escape(text: str) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _percent_to_px(value: float, total: float) -> float:
    return (value / 100.0) * total


def _radius_to_px(radius_percent: float, width: float, height: float) -> float:
    return max(6.0, _percent_to_px(radius_percent, min(width, height)))


def _build_svg_from_spec(spec: Dict[str, Any], title: str) -> str:
    canvas = spec.get("canvas", {}) or {}
    width = float(canvas.get("width") or 800)
    height = float(canvas.get("height") or 600)
    background = spec.get("background", {}) or {}
    zones = spec.get("zones", []) or []
    decorations = spec.get("decorations", []) or []
    show_labels = bool(spec.get("showLabels", False))
    legend = spec.get("legend", {}) or {}

    bg_primary = background.get("primary", "#f8fafc")
    bg_secondary = background.get("secondary", "#eef2ff")
    bg_style = background.get("style", "grid")

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" height="{int(height)}" viewBox="0 0 {int(width)} {int(height)}">',
        '<defs>',
        '<linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">',
        f'<stop offset="0%" stop-color="{_escape(bg_primary)}"/>',
        f'<stop offset="100%" stop-color="{_escape(bg_secondary)}"/>',
        '</linearGradient>',
        '<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">',
        '<path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" stroke-width="1"/>',
        "</pattern>",
        "</defs>",
        f'<rect width="{int(width)}" height="{int(height)}" fill="url(#bgGradient)"/>',
        f'<rect width="{int(width)}" height="{int(height)}" fill="url(#grid)" opacity="{"0.6" if bg_style == "grid" else "0"}"/>',
        f'<text x="{int(width * 0.5)}" y="28" text-anchor="middle" font-size="18" font-family="Arial" fill="#334155">{_escape(title)}</text>',
        '<g id="zones">',
    ]

    for idx, zone in enumerate(zones, start=1):
        if not isinstance(zone, dict):
            continue
        zone_id = zone.get("id") or f"zone_{idx}"
        zone_label = zone.get("label") or f"Zone {idx}"
        safe_label = _escape(zone_label)
        zone_color = _escape(zone.get("color", "#3b82f6"))
        zone_shape = zone.get("shape", "circle")
        zone_points = zone.get("points", [])

        # Start the zone group
        svg_parts.append(
            f'<g data-zone-id="{_escape(zone_id)}" data-zone-label="{safe_label}" aria-label="{safe_label}">'
        )

        # Render polygon zones if shape is polygon and points are available
        if zone_shape == "polygon" and zone_points and isinstance(zone_points, list):
            # Convert percentage points to pixel coordinates
            # Points can be [[x1,y1], [x2,y2], ...] or [{"x": x1, "y": y1}, ...]
            points_px = []
            for pt in zone_points:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    px_x = _percent_to_px(float(pt[0]), width)
                    px_y = _percent_to_px(float(pt[1]), height)
                    points_px.append(f"{px_x:.2f},{px_y:.2f}")
                elif isinstance(pt, dict) and "x" in pt and "y" in pt:
                    px_x = _percent_to_px(float(pt["x"]), width)
                    px_y = _percent_to_px(float(pt["y"]), height)
                    points_px.append(f"{px_x:.2f},{px_y:.2f}")

            if points_px:
                points_str = " ".join(points_px)

                # Extract RGB values from zone_color for fill opacity
                # Default fill with low opacity
                fill_color = f"rgba(59,130,246,0.12)"

                svg_parts.extend([
                    f'<polygon points="{points_str}" fill="{fill_color}" stroke="{zone_color}" stroke-width="2"/>',
                ])

                # Calculate centroid for label positioning
                if len(zone_points) >= 3:
                    sum_x = sum(float(pt[0] if isinstance(pt, (list, tuple)) else pt.get("x", 0)) for pt in zone_points)
                    sum_y = sum(float(pt[1] if isinstance(pt, (list, tuple)) else pt.get("y", 0)) for pt in zone_points)
                    centroid_x = _percent_to_px(sum_x / len(zone_points), width)
                    centroid_y = _percent_to_px(sum_y / len(zone_points), height)

                    # Add center marker
                    svg_parts.append(
                        f'<circle cx="{centroid_x:.2f}" cy="{centroid_y:.2f}" r="4" fill="{zone_color}"/>'
                    )
                    # Add zone number
                    svg_parts.append(
                        f'<text x="{centroid_x + 10:.2f}" y="{centroid_y - 10:.2f}" font-size="12" font-family="Arial" fill="#1f2937">#{idx}</text>'
                    )
        else:
            # Default circle rendering
            x = _percent_to_px(float(zone.get("x", 50)), width)
            y = _percent_to_px(float(zone.get("y", 50)), height)
            r = _radius_to_px(float(zone.get("radius", 8)), width, height)

            svg_parts.extend([
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="rgba(59,130,246,0.12)" stroke="{zone_color}" stroke-width="2"/>',
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{max(3.0, r * 0.15):.2f}" fill="{zone_color}"/>',
                f'<text x="{x + r + 6:.2f}" y="{y - r - 6:.2f}" font-size="12" font-family="Arial" fill="#1f2937">#{idx}</text>',
            ])

        # Add accessibility elements
        svg_parts.extend([
            f'<title>{safe_label}</title>',
            f'<desc>Zone {idx} for {safe_label}</desc>',
            '</g>',
        ])

    svg_parts.extend([
        "</g>",
        '<g id="decorations">',
    ])

    for decoration in decorations:
        if not isinstance(decoration, dict):
            continue
        d_type = decoration.get("type")
        props = decoration.get("props", {}) if isinstance(decoration.get("props"), dict) else {}
        if d_type == "text":
            text = _escape(props.get("text", ""))
            x = _percent_to_px(float(props.get("x", 0)), width)
            y = _percent_to_px(float(props.get("y", 0)), height)
            fill = _escape(props.get("fill", "#334155"))
            svg_parts.append(
                f'<text x="{x:.2f}" y="{y:.2f}" font-size="12" font-family="Arial" fill="{fill}">{text}</text>'
            )
        elif d_type == "shape":
            x = _percent_to_px(float(props.get("x", 0)), width)
            y = _percent_to_px(float(props.get("y", 0)), height)
            w = _percent_to_px(float(props.get("width", 10)), width)
            h = _percent_to_px(float(props.get("height", 10)), height)
            fill = _escape(props.get("fill", "rgba(148,163,184,0.2)"))
            svg_parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" rx="6" ry="6" />'
            )
        elif d_type == "path":
            d = _escape(props.get("d", ""))
            stroke = _escape(props.get("stroke", "#94a3b8"))
            svg_parts.append(
                f'<path d="{d}" stroke="{stroke}" fill="none" stroke-width="2" />'
            )

    svg_parts.extend([
        "</g>",
        f'<g id="legend" opacity="{1 if show_labels else 0}">',
        f'<rect x="16" y="{int(height - 120)}" width="220" height="96" rx="8" ry="8" fill="rgba(255,255,255,0.9)" stroke="#e2e8f0"/>',
        f'<text x="28" y="{int(height - 90)}" font-size="12" font-family="Arial" fill="#1f2937">{_escape(legend.get("title", "Labels"))}</text>',
    ])

    for i, item in enumerate(legend.get("items", []) if isinstance(legend.get("items"), list) else []):
        if not isinstance(item, dict):
            continue
        label = _escape(item.get("label", f"Item {i + 1}"))
        color = _escape(item.get("color", "#3b82f6"))
        y = int(height - 70 + i * 16)
        svg_parts.append(f'<circle cx="30" cy="{y}" r="4" fill="{color}"/>')
        svg_parts.append(f'<text x="40" y="{y + 4}" font-size="11" font-family="Arial" fill="#334155">{label}</text>')

    svg_parts.extend([
        "</g>",
        "</svg>"
    ])

    return "".join(svg_parts)


def _build_svg_from_blueprint(blueprint: Dict[str, Any], subject: str = None) -> str:
    """
    Build SVG directly from blueprint with optional subject-based theming.

    Args:
        blueprint: The game blueprint with diagram and labels
        subject: Optional subject for color theming

    Returns:
        SVG string
    """
    diagram = blueprint.get("diagram", {})
    zones = diagram.get("zones", []) or []
    labels = blueprint.get("labels", []) or []

    # Get subject-based color theme
    theme = _get_theme_for_subject(subject)
    primary_color = theme["primary"]
    secondary_color = theme["secondary"]

    width = float(diagram.get("width") or 800)
    height = float(diagram.get("height") or 600)
    title = _escape(blueprint.get("title") or "Label Diagram")

    label_map = {
        label.get("correctZoneId"): label.get("text")
        for label in labels
        if isinstance(label, dict)
    }

    spec = {
        "canvas": {"width": width, "height": height},
        "background": {"style": "grid", "primary": "#f8fafc", "secondary": secondary_color},
        "showLabels": False,
        "legend": {
            "title": "Labels",
            "items": [{"label": label_map.get(z.get("id"), z.get("label", "")), "color": primary_color} for z in zones if isinstance(z, dict)]
        },
        "zones": [
            {
                "id": z.get("id"),
                "label": z.get("label") or label_map.get(z.get("id")) or "Zone",
                "x": z.get("x", 50),
                "y": z.get("y", 50),
                "radius": z.get("radius", 8),
                "color": primary_color,
                # Include polygon shape data if available
                "shape": z.get("shape", "circle"),
                **({"points": z.get("points")} if z.get("points") else {})
            }
            for z in zones if isinstance(z, dict)
        ],
        "decorations": []
    }

    return _build_svg_from_spec(spec, title)


async def diagram_svg_generator_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    """
    Generate an SVG diagram for INTERACTIVE_DIAGRAM templates.

    Stores SVG in state['diagram_svg'] for use by asset_generator_agent.
    Uses subject-based color theming from pedagogical_context.
    """
    blueprint = state.get("blueprint", {})
    template_type = blueprint.get("templateType", state.get("template_selection", {}).get("template_type"))

    # Extract subject for theming
    ped_context = state.get("pedagogical_context", {}) or {}
    subject = ped_context.get("subject", "")

    if template_type != "INTERACTIVE_DIAGRAM":
        # Non-INTERACTIVE_DIAGRAM templates: mark as complete without SVG
        return {
            "diagram_svg": None,
            "asset_urls": {},
            "generation_complete": True,
            "current_agent": "diagram_svg_generator",
        }

    if blueprint.get("diagram", {}).get("assetUrl") or state.get("diagram_image"):
        # Has existing image asset - use it but still generate zone overlay SVG
        existing_url = blueprint.get("diagram", {}).get("assetUrl")
        diagram_image = state.get("diagram_image", {})
        if not existing_url and diagram_image:
            existing_url = diagram_image.get("image_url")

        # Still generate zone overlay SVG for interactive zones
        svg = None
        try:
            title = blueprint.get("title") or "Label Diagram"
            if state.get("diagram_spec"):
                svg = _build_svg_from_spec(state["diagram_spec"], title)
            else:
                svg = _build_svg_from_blueprint(blueprint, subject=subject)
            logger.info(f"DiagramSvgGenerator: Generated zone overlay SVG for existing image (theme: {subject or 'default'})")
        except Exception as e:
            logger.warning(f"DiagramSvgGenerator: Failed to generate zone overlay: {e}")

        asset_urls = {"diagram": existing_url} if existing_url else {}

        return {
            "diagram_svg": svg,  # Now returns SVG overlay instead of None
            "asset_urls": asset_urls,
            "generation_complete": True,
            "current_agent": "diagram_svg_generator",
        }

    try:
        title = blueprint.get("title") or "Label Diagram"
        if state.get("diagram_spec"):
            svg = _build_svg_from_spec(state["diagram_spec"], title)
        else:
            svg = _build_svg_from_blueprint(blueprint, subject=subject)
        logger.info(f"DiagramSvgGenerator: Generated SVG diagram (theme: {subject or 'default'})")

        # Create data URI for SVG (previously done by asset_generator)
        asset_urls = {}
        if svg:
            data_uri = f"data:image/svg+xml;utf8,{quote(svg)}"
            asset_urls["diagram"] = data_uri

        return {
            "diagram_svg": svg,
            "asset_urls": asset_urls,
            "generation_complete": True,
            "current_agent": "diagram_svg_generator",
        }
    except Exception as e:
        logger.error(f"DiagramSvgGenerator: Failed to generate SVG: {e}", exc_info=True)
        return {
            "diagram_svg": None,
            "asset_urls": {},
            "generation_complete": True,  # Still mark complete even on error
            "current_agent": "diagram_svg_generator",
            "error_message": f"DiagramSvgGenerator failed: {str(e)}"
        }
