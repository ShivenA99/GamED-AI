"""
Render Tools for GamED.AI v2

Tools for rendering SVG diagrams and game elements.
These tools handle the final output generation phase.
"""

import json
from typing import Dict, Any, List, Optional
from xml.etree import ElementTree as ET

from app.utils.logging_config import get_logger
from app.tools.registry import register_tool

logger = get_logger("gamed_ai.tools.render")


# ============================================================================
# SVG Rendering
# ============================================================================

async def render_svg_impl(
    diagram_spec: Dict[str, Any],
    width: int = 800,
    height: int = 600,
    style: str = "modern",
    include_background: bool = True,
    background_color: str = "#f5f5f5"
) -> Dict[str, Any]:
    """
    Render an SVG diagram from a diagram specification.

    Args:
        diagram_spec: Diagram specification with drop zones and labels
        width: SVG width in pixels
        height: SVG height in pixels
        style: Visual style (modern, classic, minimal)
        include_background: Whether to include background rect
        background_color: Background color

    Returns:
        Dict with svg_content, width, height, element_count
    """
    spec = diagram_spec.get("diagram_spec", diagram_spec)
    drop_zones = spec.get("drop_zones", [])
    label_chips = spec.get("label_chips", [])

    # Create SVG root
    svg = ET.Element("svg")
    svg.set("xmlns", "http://www.w3.org/2000/svg")
    svg.set("width", str(width))
    svg.set("height", str(height))
    svg.set("viewBox", f"0 0 {width} {height}")

    # Add defs for styles and filters
    defs = ET.SubElement(svg, "defs")
    _add_svg_styles(defs, style)

    # Add background
    if include_background:
        bg_rect = ET.SubElement(svg, "rect")
        bg_rect.set("width", "100%")
        bg_rect.set("height", "100%")
        bg_rect.set("fill", background_color)

    # Create groups for layering
    zones_group = ET.SubElement(svg, "g")
    zones_group.set("id", "drop-zones")

    labels_group = ET.SubElement(svg, "g")
    labels_group.set("id", "label-chips")

    # Render drop zones
    for zone in drop_zones:
        _render_drop_zone(zones_group, zone, width, height, style)

    # Render label chips
    for i, chip in enumerate(label_chips):
        _render_label_chip(labels_group, chip, i, len(label_chips), width, height, style)

    # Convert to string
    svg_content = ET.tostring(svg, encoding="unicode")

    return {
        "svg_content": svg_content,
        "width": width,
        "height": height,
        "element_count": len(drop_zones) + len(label_chips),
        "zone_count": len(drop_zones),
        "label_count": len(label_chips)
    }


def _add_svg_styles(defs: ET.Element, style: str) -> None:
    """Add style definitions to SVG."""
    style_elem = ET.SubElement(defs, "style")

    if style == "modern":
        style_elem.text = """
            .drop-zone { fill: rgba(59, 130, 246, 0.1); stroke: #3B82F6; stroke-width: 2; rx: 8; }
            .drop-zone:hover { fill: rgba(59, 130, 246, 0.2); }
            .drop-zone.correct { fill: rgba(34, 197, 94, 0.2); stroke: #22C55E; }
            .drop-zone.incorrect { fill: rgba(239, 68, 68, 0.2); stroke: #EF4444; }
            .label-chip { fill: white; stroke: #E5E7EB; stroke-width: 1; rx: 4; }
            .label-chip:hover { fill: #F3F4F6; cursor: grab; }
            .label-chip.dragging { opacity: 0.7; }
            .label-text { font-family: system-ui, -apple-system, sans-serif; font-size: 14px; fill: #1F2937; }
        """
    elif style == "classic":
        style_elem.text = """
            .drop-zone { fill: rgba(0, 0, 0, 0.05); stroke: #666; stroke-width: 1; }
            .label-chip { fill: #FFFBEB; stroke: #666; stroke-width: 1; }
            .label-text { font-family: Georgia, serif; font-size: 14px; fill: #333; }
        """
    else:  # minimal
        style_elem.text = """
            .drop-zone { fill: none; stroke: #999; stroke-width: 1; stroke-dasharray: 4; }
            .label-chip { fill: white; stroke: #ccc; stroke-width: 1; }
            .label-text { font-family: monospace; font-size: 12px; fill: #333; }
        """

    # Add filter for shadow
    filter_elem = ET.SubElement(defs, "filter")
    filter_elem.set("id", "shadow")
    filter_elem.set("x", "-20%")
    filter_elem.set("y", "-20%")
    filter_elem.set("width", "140%")
    filter_elem.set("height", "140%")

    fe_offset = ET.SubElement(filter_elem, "feOffset")
    fe_offset.set("result", "offOut")
    fe_offset.set("in", "SourceAlpha")
    fe_offset.set("dx", "2")
    fe_offset.set("dy", "2")

    fe_blur = ET.SubElement(filter_elem, "feGaussianBlur")
    fe_blur.set("result", "blurOut")
    fe_blur.set("in", "offOut")
    fe_blur.set("stdDeviation", "3")

    fe_blend = ET.SubElement(filter_elem, "feBlend")
    fe_blend.set("in", "SourceGraphic")
    fe_blend.set("in2", "blurOut")
    fe_blend.set("mode", "normal")


def _render_drop_zone(
    parent: ET.Element,
    zone: Dict[str, Any],
    svg_width: int,
    svg_height: int,
    style: str
) -> None:
    """Render a single drop zone."""
    group = ET.SubElement(parent, "g")
    group.set("id", zone.get("id", "zone"))
    group.set("class", "drop-zone-group")
    group.set("data-label", zone.get("label", ""))

    # Get position (normalized 0-1 coordinates)
    pos = zone.get("position", {"x": 0.5, "y": 0.5})
    x = pos.get("x", 0.5) * svg_width
    y = pos.get("y", 0.5) * svg_height

    # Get size
    size = zone.get("size", {"width": 80, "height": 40})
    w = size.get("width", 80)
    h = size.get("height", 40)

    # Center the rectangle on the position
    rect_x = x - w / 2
    rect_y = y - h / 2

    # Create drop zone rectangle
    rect = ET.SubElement(group, "rect")
    rect.set("class", "drop-zone")
    rect.set("x", str(rect_x))
    rect.set("y", str(rect_y))
    rect.set("width", str(w))
    rect.set("height", str(h))
    rect.set("rx", "8")

    # Add connector line (from zone to edge for leader line style)
    if zone.get("connector"):
        line = ET.SubElement(group, "line")
        line.set("class", "connector-line")
        connector = zone["connector"]
        line.set("x1", str(x))
        line.set("y1", str(y))
        line.set("x2", str(connector.get("x", x) * svg_width))
        line.set("y2", str(connector.get("y", y) * svg_height))
        line.set("stroke", "#999")
        line.set("stroke-width", "1")


def _render_label_chip(
    parent: ET.Element,
    chip: Dict[str, Any],
    index: int,
    total: int,
    svg_width: int,
    svg_height: int,
    style: str
) -> None:
    """Render a single label chip."""
    group = ET.SubElement(parent, "g")
    group.set("id", chip.get("id", f"label_{index}"))
    group.set("class", "label-chip-group")
    group.set("data-correct-zone", chip.get("matched_zone", ""))

    # Calculate position in a tray at the bottom
    tray_y = svg_height - 60
    chip_width = 120
    chip_height = 36

    # Distribute chips evenly
    total_width = total * (chip_width + 10) - 10
    start_x = (svg_width - total_width) / 2
    chip_x = start_x + index * (chip_width + 10)

    # Create chip background
    rect = ET.SubElement(group, "rect")
    rect.set("class", "label-chip")
    rect.set("x", str(chip_x))
    rect.set("y", str(tray_y))
    rect.set("width", str(chip_width))
    rect.set("height", str(chip_height))
    rect.set("rx", "4")
    rect.set("filter", "url(#shadow)")

    # Add text
    text = ET.SubElement(group, "text")
    text.set("class", "label-text")
    text.set("x", str(chip_x + chip_width / 2))
    text.set("y", str(tray_y + chip_height / 2 + 5))
    text.set("text-anchor", "middle")
    text.text = chip.get("text", f"Label {index + 1}")


async def optimize_svg_impl(
    svg_content: str,
    minify: bool = True,
    remove_comments: bool = True
) -> Dict[str, Any]:
    """
    Optimize SVG content for smaller file size.

    Args:
        svg_content: Raw SVG content
        minify: Whether to minify whitespace
        remove_comments: Whether to remove XML comments

    Returns:
        Dict with optimized_svg, original_size, optimized_size, savings
    """
    original_size = len(svg_content)

    optimized = svg_content

    if remove_comments:
        import re
        optimized = re.sub(r'<!--.*?-->', '', optimized, flags=re.DOTALL)

    if minify:
        # Remove extra whitespace
        import re
        optimized = re.sub(r'\s+', ' ', optimized)
        optimized = re.sub(r'>\s+<', '><', optimized)
        optimized = optimized.strip()

    optimized_size = len(optimized)
    savings = ((original_size - optimized_size) / original_size) * 100 if original_size > 0 else 0

    return {
        "optimized_svg": optimized,
        "original_size": original_size,
        "optimized_size": optimized_size,
        "savings_percent": round(savings, 1)
    }


async def generate_game_asset_impl(
    asset_type: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a specific game asset.

    Args:
        asset_type: Type of asset (icon, button, decoration)
        parameters: Asset-specific parameters

    Returns:
        Dict with asset_data, format, metadata
    """
    if asset_type == "icon":
        return _generate_icon_svg(parameters)
    elif asset_type == "button":
        return _generate_button_svg(parameters)
    elif asset_type == "decoration":
        return _generate_decoration_svg(parameters)
    else:
        return {
            "error": f"Unknown asset type: {asset_type}"
        }


def _generate_icon_svg(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate an icon SVG."""
    icon_type = params.get("type", "check")
    size = params.get("size", 24)
    color = params.get("color", "#22C55E")

    icons = {
        "check": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24"><path fill="{color}" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>',
        "cross": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24"><path fill="{color}" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
        "star": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24"><path fill="{color}" d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>'
    }

    return {
        "asset_data": icons.get(icon_type, icons["check"]),
        "format": "svg",
        "metadata": {"type": icon_type, "size": size, "color": color}
    }


def _generate_button_svg(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a button SVG."""
    text = params.get("text", "Button")
    width = params.get("width", 120)
    height = params.get("height", 40)
    bg_color = params.get("bg_color", "#3B82F6")
    text_color = params.get("text_color", "white")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
        <rect width="{width}" height="{height}" rx="8" fill="{bg_color}"/>
        <text x="{width/2}" y="{height/2 + 5}" text-anchor="middle" fill="{text_color}" font-family="system-ui" font-size="14">{text}</text>
    </svg>'''

    return {
        "asset_data": svg,
        "format": "svg",
        "metadata": {"text": text, "width": width, "height": height}
    }


def _generate_decoration_svg(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a decoration SVG."""
    decoration_type = params.get("type", "divider")
    width = params.get("width", 200)
    color = params.get("color", "#E5E7EB")

    decorations = {
        "divider": f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="2"><line x1="0" y1="1" x2="{width}" y2="1" stroke="{color}" stroke-width="2"/></svg>',
        "corner": f'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><path d="M0 0 L20 0 L20 5 L5 5 L5 20 L0 20 Z" fill="{color}"/></svg>'
    }

    return {
        "asset_data": decorations.get(decoration_type, decorations["divider"]),
        "format": "svg",
        "metadata": {"type": decoration_type, "width": width, "color": color}
    }


# ============================================================================
# Tool Registration
# ============================================================================

def register_render_tools() -> None:
    """Register all render tools in the registry."""

    register_tool(
        name="render_svg",
        description="Render an SVG diagram from a diagram specification. Creates interactive drop zones and draggable label chips.",
        parameters={
            "type": "object",
            "properties": {
                "diagram_spec": {
                    "type": "object",
                    "description": "Diagram specification with drop zones and labels"
                },
                "width": {
                    "type": "integer",
                    "description": "SVG width in pixels",
                    "default": 800
                },
                "height": {
                    "type": "integer",
                    "description": "SVG height in pixels",
                    "default": 600
                },
                "style": {
                    "type": "string",
                    "description": "Visual style",
                    "enum": ["modern", "classic", "minimal"],
                    "default": "modern"
                },
                "include_background": {
                    "type": "boolean",
                    "description": "Include background rectangle",
                    "default": True
                },
                "background_color": {
                    "type": "string",
                    "description": "Background color",
                    "default": "#f5f5f5"
                }
            },
            "required": ["diagram_spec"]
        },
        function=render_svg_impl
    )

    register_tool(
        name="optimize_svg",
        description="Optimize SVG content for smaller file size. Minifies whitespace and removes comments.",
        parameters={
            "type": "object",
            "properties": {
                "svg_content": {
                    "type": "string",
                    "description": "Raw SVG content"
                },
                "minify": {
                    "type": "boolean",
                    "description": "Minify whitespace",
                    "default": True
                },
                "remove_comments": {
                    "type": "boolean",
                    "description": "Remove XML comments",
                    "default": True
                }
            },
            "required": ["svg_content"]
        },
        function=optimize_svg_impl
    )

    register_tool(
        name="generate_game_asset",
        description="Generate a specific game asset like icons, buttons, or decorations.",
        parameters={
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "Type of asset",
                    "enum": ["icon", "button", "decoration"]
                },
                "parameters": {
                    "type": "object",
                    "description": "Asset-specific parameters"
                }
            },
            "required": ["asset_type", "parameters"]
        },
        function=generate_game_asset_impl
    )

    logger.info("Render tools registered")
