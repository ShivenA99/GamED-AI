"""
Nanobanana Image Generation Service

Provides AI image generation capabilities for educational game assets.
This service integrates with the nanobanana image generation API.

Usage:
    from app.services.nanobanana_service import get_nanobanana_service

    service = get_nanobanana_service()
    response = await service.generate(NanobananaRequest(
        prompt="Clean anatomical diagram of human heart, educational style",
        width=512,
        height=512,
        style="medical_illustration"
    ))

    if response.success:
        image_url = response.image_url
"""

import os
import logging
import aiohttp
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import time
import hashlib

logger = logging.getLogger("gamed_ai.services.nanobanana")


@dataclass
class NanobananaRequest:
    """Request parameters for nanobanana image generation."""
    prompt: str
    width: int = 512
    height: int = 512
    style: Optional[str] = None  # e.g., "educational", "medical_illustration", "cartoon"
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None


@dataclass
class NanobananaResponse:
    """Response from nanobanana image generation."""
    success: bool
    image_url: Optional[str] = None
    image_bytes: Optional[bytes] = None
    local_path: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class NanobananaService:
    """
    Service for generating images via nanobanana.

    Supports:
    - Text-to-image generation
    - Style modifiers for educational content
    - Local caching of generated images

    Configuration via environment variables:
    - NANOBANANA_ENDPOINT: API endpoint URL
    - NANOBANANA_API_KEY: API authentication key
    """

    # Style modifiers for educational content
    STYLE_MODIFIERS = {
        "educational": "clean educational illustration, clear labels, professional, white background",
        "medical_illustration": "medical textbook illustration, anatomically accurate, professional",
        "cartoon": "friendly cartoon style, colorful, child-appropriate, clean lines",
        "scientific": "scientific diagram, precise, technical illustration, labeled",
        "nature": "nature illustration, detailed botanical/zoological style, accurate",
        "diagram": "clean technical diagram, minimal style, clear contrast",
        "infographic": "infographic style, bold colors, clear icons, modern design",
    }

    # Default negative prompt for educational content
    DEFAULT_NEGATIVE_PROMPT = (
        "text, watermark, blurry, low quality, distorted, deformed, "
        "realistic human faces, photorealistic people, inappropriate content"
    )

    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the nanobanana service.

        Args:
            api_endpoint: API endpoint URL (default from NANOBANANA_ENDPOINT env var)
            api_key: API key (default from NANOBANANA_API_KEY env var)
            cache_dir: Directory for caching generated images
        """
        self.api_endpoint = api_endpoint or os.environ.get("NANOBANANA_ENDPOINT")
        self.api_key = api_key or os.environ.get("NANOBANANA_API_KEY")
        self.cache_dir = Path(cache_dir or os.environ.get(
            "NANOBANANA_CACHE_DIR",
            "assets/generated/nanobanana"
        ))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_endpoint:
            logger.warning("NANOBANANA_ENDPOINT not configured - service will use placeholder responses")
        if not self.api_key:
            logger.warning("NANOBANANA_API_KEY not configured")

    async def generate(self, request: NanobananaRequest) -> NanobananaResponse:
        """
        Generate an image using nanobanana.

        Args:
            request: NanobananaRequest with prompt and options

        Returns:
            NanobananaResponse with image URL/bytes or error
        """
        start_time = time.time()

        # Check cache first
        cache_key = self._get_cache_key(request)
        cached_path = self.cache_dir / f"{cache_key}.png"
        if cached_path.exists():
            logger.info(f"Cache hit for nanobanana request: {cache_key[:8]}...")
            return NanobananaResponse(
                success=True,
                local_path=str(cached_path),
                latency_ms=int((time.time() - start_time) * 1000),
                metadata={"cached": True, "cache_key": cache_key}
            )

        # If no API endpoint configured, return placeholder
        if not self.api_endpoint:
            return await self._generate_placeholder(request, start_time)

        try:
            # Enhance prompt with style modifiers
            enhanced_prompt = self._enhance_prompt(request.prompt, request.style)

            # Build request payload
            payload = {
                "prompt": enhanced_prompt,
                "width": request.width,
                "height": request.height,
                "negative_prompt": request.negative_prompt or self.DEFAULT_NEGATIVE_PROMPT,
            }
            if request.seed is not None:
                payload["seed"] = request.seed

            # Make API call
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    self.api_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Nanobanana API error: {response.status} - {error_text}")
                        return NanobananaResponse(
                            success=False,
                            error=f"API error: {response.status}",
                            latency_ms=int((time.time() - start_time) * 1000)
                        )

                    result = await response.json()

                    # Handle response - adapt based on actual nanobanana API response format
                    if "image" in result:
                        # Base64 encoded image
                        image_bytes = base64.b64decode(result["image"])
                    elif "url" in result:
                        # Image URL - fetch and cache
                        async with session.get(result["url"]) as img_response:
                            image_bytes = await img_response.read()
                    else:
                        return NanobananaResponse(
                            success=False,
                            error="Unexpected API response format",
                            latency_ms=int((time.time() - start_time) * 1000)
                        )

                    # Save to cache
                    cached_path.write_bytes(image_bytes)

                    return NanobananaResponse(
                        success=True,
                        image_bytes=image_bytes,
                        local_path=str(cached_path),
                        latency_ms=int((time.time() - start_time) * 1000),
                        metadata={
                            "prompt": enhanced_prompt,
                            "style": request.style,
                            "dimensions": f"{request.width}x{request.height}",
                            "cache_key": cache_key
                        }
                    )

        except aiohttp.ClientError as e:
            logger.error(f"Nanobanana network error: {e}")
            return NanobananaResponse(
                success=False,
                error=f"Network error: {str(e)}",
                latency_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            logger.error(f"Nanobanana generation failed: {e}", exc_info=True)
            return NanobananaResponse(
                success=False,
                error=str(e),
                latency_ms=int((time.time() - start_time) * 1000)
            )

    async def _generate_placeholder(
        self,
        request: NanobananaRequest,
        start_time: float
    ) -> NanobananaResponse:
        """
        Generate a placeholder image when API is not configured.

        Creates a simple colored rectangle with text indicating it's a placeholder.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.warning("PIL not available for placeholder generation")
            return NanobananaResponse(
                success=False,
                error="Nanobanana API not configured and PIL not available for placeholders",
                latency_ms=int((time.time() - start_time) * 1000)
            )

        # Create a placeholder image
        img = Image.new('RGB', (request.width, request.height), color=(240, 240, 245))
        draw = ImageDraw.Draw(img)

        # Draw border
        draw.rectangle(
            [10, 10, request.width - 10, request.height - 10],
            outline=(200, 200, 210),
            width=2
        )

        # Draw placeholder text
        text = f"[Placeholder]\n{request.style or 'image'}\n{request.width}x{request.height}"
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except Exception:
            font = ImageFont.load_default()

        # Center text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (request.width - text_width) // 2
        y = (request.height - text_height) // 2
        draw.text((x, y), text, fill=(100, 100, 120), font=font, align="center")

        # Save to cache
        cache_key = self._get_cache_key(request)
        cached_path = self.cache_dir / f"{cache_key}_placeholder.png"
        img.save(cached_path, "PNG")

        return NanobananaResponse(
            success=True,
            local_path=str(cached_path),
            latency_ms=int((time.time() - start_time) * 1000),
            metadata={
                "placeholder": True,
                "prompt": request.prompt,
                "style": request.style
            }
        )

    def _enhance_prompt(self, prompt: str, style: Optional[str]) -> str:
        """
        Enhance the prompt with style modifiers for better educational content.

        Args:
            prompt: Original prompt
            style: Style identifier (e.g., "educational", "medical_illustration")

        Returns:
            Enhanced prompt with style modifiers
        """
        modifier = self.STYLE_MODIFIERS.get(style, self.STYLE_MODIFIERS["educational"])
        return f"{prompt}, {modifier}"

    def _get_cache_key(self, request: NanobananaRequest) -> str:
        """Generate a cache key for a request."""
        key_data = f"{request.prompt}:{request.width}:{request.height}:{request.style}:{request.seed}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self.api_endpoint and self.api_key)

    async def health_check(self) -> Dict[str, Any]:
        """Check service health and configuration."""
        return {
            "configured": self.is_configured(),
            "endpoint": bool(self.api_endpoint),
            "api_key": bool(self.api_key),
            "cache_dir": str(self.cache_dir),
            "cache_dir_exists": self.cache_dir.exists(),
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_nanobanana_service: Optional[NanobananaService] = None


def get_nanobanana_service() -> NanobananaService:
    """
    Get or create the global nanobanana service instance.

    Returns:
        NanobananaService singleton instance
    """
    global _nanobanana_service
    if _nanobanana_service is None:
        _nanobanana_service = NanobananaService()
    return _nanobanana_service


def reset_nanobanana_service():
    """Reset the singleton instance (for testing)."""
    global _nanobanana_service
    _nanobanana_service = None
