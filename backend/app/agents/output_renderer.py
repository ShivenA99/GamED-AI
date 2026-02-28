"""
Output Renderer Agent

Handles the final rendering phase for the Agentic Sequential pipeline:
- Generates diagram specifications (from zones and labels)
- Renders final SVG output

This agent was split from blueprint_generator to reduce cognitive load
(research shows 5-10 tools per agent maximum for quality).

Tools available:
- generate_diagram_spec: Create drop zone and label chip specifications
- render_svg: Render the final SVG from specs
"""

import json
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.output_renderer")


def _escape(text: str) -> str:
    """XML-safe escaping for SVG content."""
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
    """Convert percentage to pixels."""
    return (value / 100.0) * total


def _radius_to_px(radius_percent: float, width: float, height: float) -> float:
    """Convert radius percentage to pixels."""
    return max(6.0, _percent_to_px(radius_percent, min(width, height)))


def _build_diagram_spec(
    zones: List[Dict[str, Any]],
    labels: List[str],
    blueprint: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build a diagram specification from zones and labels.

    Args:
        zones: List of detected zones with positions
        labels: List of label strings
        blueprint: The game blueprint

    Returns:
        Diagram specification with canvas, zones, and styling
    """
    # Get dimensions from blueprint or defaults
    diagram = blueprint.get("diagram", {})
    width = int(diagram.get("width", 800))
    height = int(diagram.get("height", 600))

    # Build zone specifications
    spec_zones = []
    for i, zone in enumerate(zones):
        if not isinstance(zone, dict):
            continue

        # Get label for this zone
        label = labels[i] if i < len(labels) else f"Zone {i + 1}"

        # Get zone position (normalize to percentage)
        x = zone.get("x", zone.get("center", [50, 50])[0] if isinstance(zone.get("center"), list) else 50)
        y = zone.get("y", zone.get("center", [50, 50])[1] if isinstance(zone.get("center"), list) else 50)

        # Convert from pixel to percentage if needed
        if isinstance(x, (int, float)) and x > 100:
            x = (x / width) * 100
        if isinstance(y, (int, float)) and y > 100:
            y = (y / height) * 100

        spec_zones.append({
            "id": zone.get("id", f"zone_{i + 1}"),
            "label": label,
            "x": float(x),
            "y": float(y),
            "radius": float(zone.get("radius", 8)),
            "color": zone.get("color", "#3b82f6"),
            "markerShape": zone.get("markerShape", "circle")
        })

    return {
        "canvas": {"width": width, "height": height},
        "background": {
            "style": "grid",
            "primary": "#f8fafc",
            "secondary": "#eef2ff"
        },
        "showLabels": False,
        "legend": {
            "title": "Labels",
            "items": [
                {"label": z.get("label", ""), "color": z.get("color", "#3b82f6")}
                for z in spec_zones
            ]
        },
        "zones": spec_zones,
        "decorations": []
    }


def _build_svg_from_spec(spec: Dict[str, Any], title: str) -> str:
    """
    Render SVG from diagram specification.

    Args:
        spec: Diagram specification
        title: Title to display in SVG

    Returns:
        SVG string
    """
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
        x = _percent_to_px(float(zone.get("x", 50)), width)
        y = _percent_to_px(float(zone.get("y", 50)), height)
        r = _radius_to_px(float(zone.get("radius", 8)), width, height)
        safe_label = _escape(zone_label)
        zone_color = _escape(zone.get("color", "#3b82f6"))

        svg_parts.extend([
            f'<g data-zone-id="{_escape(zone_id)}" data-zone-label="{safe_label}" aria-label="{safe_label}">',
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="rgba(59,130,246,0.12)" stroke="{zone_color}" stroke-width="2"/>',
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{max(3.0, r * 0.15):.2f}" fill="{zone_color}"/>',
            f'<text x="{x + r + 6:.2f}" y="{y - r - 6:.2f}" font-size="12" font-family="Arial" fill="#1f2937">#{idx}</text>',
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


async def output_renderer_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Output Renderer Agent - Final rendering for Label Diagram games.

    This agent:
    1. Generates diagram specification from zones/labels
    2. Renders final SVG output

    Inputs: blueprint, diagram_zones, diagram_labels, diagram_image_url
    Outputs: diagram_spec, diagram_svg, asset_urls, generation_complete
    """
    logger.info("OutputRenderer: Starting final rendering phase")

    blueprint = state.get("blueprint", {})
    zones = state.get("diagram_zones", []) or []
    labels = state.get("diagram_labels", []) or []
    diagram_image_url = state.get("diagram_image_url", "")

    # Check template type
    template_type = blueprint.get("templateType", "INTERACTIVE_DIAGRAM")
    template_selection = state.get("template_selection", {})
    if template_selection:
        template_type = template_selection.get("template", template_type)

    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"OutputRenderer: Non-INTERACTIVE_DIAGRAM template ({template_type}), marking complete")
        return {
            "diagram_spec": None,
            "diagram_svg": None,
            "asset_urls": {},
            "generation_complete": True,
            "current_agent": "output_renderer",
        }

    try:
        # Step 1: Generate diagram specification
        logger.info(f"OutputRenderer: Building spec from {len(zones)} zones and {len(labels)} labels")

        # Use existing spec if available, otherwise build from state
        diagram_spec = state.get("diagram_spec")
        if not diagram_spec:
            diagram_spec = _build_diagram_spec(zones, labels, blueprint)

        # Step 2: Render SVG
        title = blueprint.get("title") or state.get("question_text", "Label Diagram")[:50]
        svg_content = _build_svg_from_spec(diagram_spec, title)

        logger.info(f"OutputRenderer: Generated SVG ({len(svg_content)} bytes)")

        # Step 3: Build asset URLs
        asset_urls = {}
        if diagram_image_url:
            asset_urls["diagram"] = diagram_image_url
        elif svg_content:
            # Create data URI for SVG as fallback
            data_uri = f"data:image/svg+xml;utf8,{quote(svg_content)}"
            asset_urls["diagram"] = data_uri

        # Track metrics
        if ctx:
            ctx.set_custom_metric("zones_rendered", len(zones))
            ctx.set_custom_metric("svg_size_bytes", len(svg_content) if svg_content else 0)

        return {
            "diagram_spec": diagram_spec,
            "diagram_svg": svg_content,
            "asset_urls": asset_urls,
            "generation_complete": True,
            "current_agent": "output_renderer",
        }

    except Exception as e:
        logger.error(f"OutputRenderer: Failed: {e}", exc_info=True)
        return {
            "diagram_spec": None,
            "diagram_svg": None,
            "asset_urls": {},
            "generation_complete": True,  # Mark complete even on error
            "current_agent": "output_renderer",
            "error_message": f"OutputRenderer failed: {str(e)}"
        }
