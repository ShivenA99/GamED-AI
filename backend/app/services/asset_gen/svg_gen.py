"""SVG generation via Gemini text models.

Generates SVG code for icons, patterns, connectors, particles, and other
vector assets used in interactive diagram games.
"""

import logging
import os
import re
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger("gamed_ai.asset_gen.svg_gen")


class SVGGenerator:
    """Generate SVG code using Gemini text models."""

    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GOOGLE_API_KEY not set")
        self.client = genai.Client(api_key=key)

    async def generate_svg(
        self,
        description: str,
        width: int = 64,
        height: int = 64,
        style_hints: str = "",
    ) -> str:
        """Generate SVG code from a text description.

        Args:
            description: What the SVG should depict
            width: Default viewBox width
            height: Default viewBox height
            style_hints: Additional style guidance

        Returns:
            Valid SVG markup string
        """
        prompt = (
            f"Generate a clean SVG icon: {description}.\n"
            f"ViewBox: 0 0 {width} {height}. {style_hints}\n\n"
            f"Requirements:\n"
            f"- Return ONLY the SVG code, no markdown, no explanation\n"
            f"- Start with <svg and end with </svg>\n"
            f"- Use simple paths and shapes, minimal complexity\n"
            f"- No embedded raster images or external references\n"
            f"- Include viewBox attribute\n"
            f"- Use fill colors, not stroke-only designs\n"
        )

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
        )

        return self._extract_svg(response.text)

    async def generate_icon_set(
        self,
        icons: list[dict],
        size: int = 48,
        style: str = "flat, modern, educational",
    ) -> dict[str, str]:
        """Generate a set of related SVG icons with consistent style.

        Args:
            icons: List of {name, description} dicts
            size: Icon size (square viewBox)
            style: Style description applied to all icons

        Returns:
            Dict mapping icon name to SVG code
        """
        logger.info(f"Generating {len(icons)} SVG icons")
        results = {}

        # Build a single prompt for all icons to ensure stylistic consistency
        icon_specs = "\n".join(
            f"  {i+1}. \"{icon['name']}\": {icon['description']}"
            for i, icon in enumerate(icons)
        )

        prompt = (
            f"Generate {len(icons)} SVG icons in a consistent {style} style.\n"
            f"Each icon: viewBox=\"0 0 {size} {size}\"\n\n"
            f"Icons to generate:\n{icon_specs}\n\n"
            f"Requirements:\n"
            f"- All icons should share consistent visual style, stroke widths, and color palette\n"
            f"- Each SVG must be self-contained (start with <svg, end with </svg>)\n"
            f"- Use a cohesive color palette across all icons\n"
            f"- No text elements, no external references\n"
            f"- Simple, recognizable shapes suitable for 48x48 display\n\n"
            f"Format your response as:\n"
            f"ICON: icon_name\n"
            f"<svg ...>...</svg>\n"
            f"ICON: next_icon_name\n"
            f"<svg ...>...</svg>\n"
        )

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
        )

        raw = response.text
        # Parse ICON: name / SVG blocks
        blocks = re.split(r'ICON:\s*', raw)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            lines = block.split('\n', 1)
            if len(lines) < 2:
                continue
            name = lines[0].strip().strip('"').strip("'")
            svg_part = lines[1]
            try:
                svg = self._extract_svg(svg_part)
                # Match to closest icon name
                matched_name = self._match_icon_name(name, [ic["name"] for ic in icons])
                results[matched_name] = svg
            except ValueError:
                logger.warning(f"Failed to extract SVG for icon: {name}")

        logger.info(f"Generated {len(results)}/{len(icons)} icons")
        return results

    async def generate_card_back_pattern(
        self,
        theme: str,
        width: int = 200,
        height: int = 280,
        colors: list[str] | None = None,
    ) -> str:
        """Generate a decorative SVG pattern for card backs.

        Args:
            theme: Theme description (e.g., "biology cells", "space")
            width: Card width
            height: Card height
            colors: Color palette to use

        Returns:
            SVG markup string
        """
        color_str = ", ".join(colors) if colors else "indigo, purple, blue"
        prompt = (
            f"Generate an SVG card back pattern with theme: {theme}.\n"
            f"Size: {width}x{height} pixels.\n"
            f"Color palette: {color_str}.\n\n"
            f"Requirements:\n"
            f"- Decorative, repeating geometric or thematic pattern\n"
            f"- Use <pattern> or <defs> for repeating elements\n"
            f"- Rounded corners (rx=12)\n"
            f"- Gradient background using the color palette\n"
            f"- Subtle, elegant — this is the back of a game card\n"
            f"- Return ONLY the SVG code, no markdown\n"
        )

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
        )

        return self._extract_svg(response.text)

    async def generate_connector_svg(
        self,
        connector_type: str = "arrow",
        color: str = "#6366f1",
        animated: bool = True,
    ) -> str:
        """Generate SVG connector/arrow for timeline/sequence layouts.

        Args:
            connector_type: "arrow", "dotted_line", "curved_arrow"
            color: Connector color
            animated: Whether to include CSS animation

        Returns:
            SVG markup string
        """
        animation_note = "Include a CSS animation for a flow/pulse effect." if animated else ""
        prompt = (
            f"Generate an SVG {connector_type} connector.\n"
            f"Color: {color}. Size: 60x30.\n"
            f"{animation_note}\n\n"
            f"Requirements:\n"
            f"- Horizontal connector pointing right\n"
            f"- Clean arrowhead at the end\n"
            f"- Return ONLY the SVG code\n"
        )

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
        )

        return self._extract_svg(response.text)

    async def generate_particle_sprite(
        self,
        theme: str = "sparkle",
        size: int = 24,
        color: str = "#fbbf24",
    ) -> str:
        """Generate a small SVG sprite for particle effects.

        Args:
            theme: "sparkle", "droplet", "star", "bubble", "cell"
            size: Sprite size
            color: Primary color

        Returns:
            SVG markup string
        """
        prompt = (
            f"Generate a tiny SVG {theme} sprite, {size}x{size}.\n"
            f"Color: {color}. Style: simple, iconic.\n"
            f"- Return ONLY the SVG code, no markdown\n"
            f"- Suitable for particle animation in a game\n"
        )

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
        )

        return self._extract_svg(response.text)

    def _extract_svg(self, text: str) -> str:
        """Extract SVG markup from model response text."""
        # Try to find SVG within markdown code blocks first
        code_match = re.search(r'```(?:svg|xml)?\s*\n?(.*?)```', text, re.DOTALL)
        if code_match:
            text = code_match.group(1)

        # Find the SVG element
        svg_match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.DOTALL)
        if svg_match:
            return svg_match.group(1).strip()

        raise ValueError("No valid SVG found in response")

    def _match_icon_name(self, generated_name: str, expected_names: list[str]) -> str:
        """Fuzzy match a generated icon name to expected names."""
        gen_lower = generated_name.lower().replace("_", " ").replace("-", " ")

        # Exact match
        for name in expected_names:
            if name.lower() == gen_lower:
                return name

        # Substring match
        for name in expected_names:
            if name.lower() in gen_lower or gen_lower in name.lower():
                return name

        # Word overlap
        gen_words = set(gen_lower.split())
        best_match = expected_names[0]
        best_overlap = 0
        for name in expected_names:
            name_words = set(name.lower().replace("_", " ").replace("-", " ").split())
            overlap = len(gen_words & name_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = name

        return best_match
