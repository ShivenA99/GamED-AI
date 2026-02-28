"""
Media Generation Service

Unified interface for generating various media assets:
- Static images (via Stable Diffusion, DALL-E, or image retrieval)
- CSS animations
- GIFs from image sequences
- Asset caching and retrieval
"""

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles

from app.services.nanobanana_service import get_nanobanana_service, NanobananaRequest

logger = logging.getLogger("gamed_ai.services.media_generation")


class GenerationMethod(Enum):
    """Available methods for generating media assets."""
    # Active methods
    NANOBANANA = "nanobanana"  # Nanobanana API for image generation (primary)
    CSS_ANIMATION = "css_animation"  # CSS-based animations
    CACHED = "cached"  # Pre-existing/cached assets
    FETCH_URL = "fetch_url"  # URL-based image fetching
    # Legacy methods (kept for enum compatibility)
    GEMINI_IMAGEN = "gemini_imagen"  # Deprecated - use NANOBANANA instead
    STABLE_DIFFUSION = "stable_diffusion"
    DALLE = "dalle"


class AssetType(Enum):
    """Types of media assets that can be generated."""
    IMAGE = "image"
    GIF = "gif"
    VIDEO = "video"
    SPRITE = "sprite"
    CSS_ANIMATION = "css_animation"


@dataclass
class PlannedAsset:
    """Represents a planned asset for generation."""
    id: str
    type: AssetType
    generation_method: GenerationMethod
    prompt: Optional[str] = None
    url: Optional[str] = None
    local_path: Optional[str] = None  # Pre-existing local file path
    dimensions: Optional[Dict[str, int]] = None
    priority: int = 1
    placement: str = "overlay"
    zone_id: Optional[str] = None
    layer: int = 0
    style: Optional[Dict[str, Any]] = None
    keyframes: Optional[str] = None


@dataclass
class GeneratedAsset:
    """Represents a generated asset."""
    id: str
    type: AssetType
    url: Optional[str] = None
    local_path: Optional[str] = None
    css_content: Optional[str] = None
    keyframes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    success: bool = True
    error: Optional[str] = None


class MediaGenerationService:
    """Service for generating media assets."""

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the media generation service.

        Args:
            cache_dir: Directory for caching generated assets.
        """
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "cache"
        )
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

        # Initialize API clients (lazy loaded)
        self._openai_client = None
        self._sd_pipeline = None

    def _get_cache_key(self, prompt: str, asset_type: AssetType,
                       dimensions: Optional[Dict[str, int]] = None) -> str:
        """Generate a cache key for an asset."""
        key_parts = [prompt, asset_type.value]
        if dimensions:
            key_parts.extend([str(dimensions.get("width", 0)),
                           str(dimensions.get("height", 0))])
        key_string = "_".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cached_path(self, cache_key: str, extension: str = "png") -> Path:
        """Get the path for a cached asset."""
        return Path(self.cache_dir) / f"{cache_key}.{extension}"

    async def check_cache(self, prompt: str, asset_type: AssetType,
                          dimensions: Optional[Dict[str, int]] = None) -> Optional[str]:
        """Check if an asset is cached.

        Args:
            prompt: The generation prompt.
            asset_type: Type of asset.
            dimensions: Optional dimensions.

        Returns:
            Path to cached asset if exists, None otherwise.
        """
        cache_key = self._get_cache_key(prompt, asset_type, dimensions)

        for ext in ["png", "jpg", "gif", "css"]:
            cached_path = self._get_cached_path(cache_key, ext)
            if cached_path.exists():
                logger.info(f"Cache hit for asset: {cache_key}")
                return str(cached_path)

        return None

    async def generate_image_dalle(self, prompt: str,
                                   dimensions: Optional[Dict[str, int]] = None) -> GeneratedAsset:
        """Generate an image using DALL-E API.

        Args:
            prompt: The image generation prompt.
            dimensions: Optional width/height specifications.

        Returns:
            GeneratedAsset with the generated image URL.
        """
        try:
            # Check cache first
            cached = await self.check_cache(prompt, AssetType.IMAGE, dimensions)
            if cached:
                return GeneratedAsset(
                    id=f"dalle_{self._get_cache_key(prompt, AssetType.IMAGE, dimensions)}",
                    type=AssetType.IMAGE,
                    local_path=cached,
                    success=True
                )

            # Lazy load OpenAI client
            if self._openai_client is None:
                try:
                    from openai import AsyncOpenAI
                    self._openai_client = AsyncOpenAI()
                except ImportError:
                    return GeneratedAsset(
                        id="dalle_error",
                        type=AssetType.IMAGE,
                        success=False,
                        error="OpenAI package not installed"
                    )
                except Exception as e:
                    return GeneratedAsset(
                        id="dalle_error",
                        type=AssetType.IMAGE,
                        success=False,
                        error=f"Failed to initialize OpenAI client: {str(e)}"
                    )

            # Determine size
            size = "1024x1024"
            if dimensions:
                w, h = dimensions.get("width", 1024), dimensions.get("height", 1024)
                if w > h:
                    size = "1792x1024"
                elif h > w:
                    size = "1024x1792"

            response = await self._openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1
            )

            image_url = response.data[0].url
            cache_key = self._get_cache_key(prompt, AssetType.IMAGE, dimensions)

            return GeneratedAsset(
                id=f"dalle_{cache_key}",
                type=AssetType.IMAGE,
                url=image_url,
                success=True,
                metadata={"prompt": prompt, "size": size}
            )

        except Exception as e:
            logger.error(f"DALL-E generation failed: {str(e)}")
            return GeneratedAsset(
                id="dalle_error",
                type=AssetType.IMAGE,
                success=False,
                error=str(e)
            )

    async def generate_image_stable_diffusion(self, prompt: str,
                                               dimensions: Optional[Dict[str, int]] = None) -> GeneratedAsset:
        """Generate an image using Stable Diffusion (local or API).

        Args:
            prompt: The image generation prompt.
            dimensions: Optional width/height specifications.

        Returns:
            GeneratedAsset with the generated image path.
        """
        try:
            # Check cache first
            cached = await self.check_cache(prompt, AssetType.IMAGE, dimensions)
            if cached:
                return GeneratedAsset(
                    id=f"sd_{self._get_cache_key(prompt, AssetType.IMAGE, dimensions)}",
                    type=AssetType.IMAGE,
                    local_path=cached,
                    success=True
                )

            # Check for local SD installation
            sd_available = os.environ.get("SD_MODEL_PATH") or os.environ.get("REPLICATE_API_TOKEN")

            if not sd_available:
                return GeneratedAsset(
                    id="sd_unavailable",
                    type=AssetType.IMAGE,
                    success=False,
                    error="Stable Diffusion not configured. Set SD_MODEL_PATH or REPLICATE_API_TOKEN."
                )

            # Use Replicate API if configured
            replicate_token = os.environ.get("REPLICATE_API_TOKEN")
            if replicate_token:
                try:
                    import replicate

                    width = dimensions.get("width", 768) if dimensions else 768
                    height = dimensions.get("height", 768) if dimensions else 768

                    output = await asyncio.to_thread(
                        replicate.run,
                        "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                        input={
                            "prompt": prompt,
                            "width": width,
                            "height": height,
                            "num_outputs": 1
                        }
                    )

                    image_url = output[0] if output else None
                    cache_key = self._get_cache_key(prompt, AssetType.IMAGE, dimensions)

                    return GeneratedAsset(
                        id=f"sd_{cache_key}",
                        type=AssetType.IMAGE,
                        url=image_url,
                        success=True,
                        metadata={"prompt": prompt, "width": width, "height": height}
                    )

                except Exception as e:
                    logger.error(f"Replicate SD generation failed: {str(e)}")
                    return GeneratedAsset(
                        id="sd_error",
                        type=AssetType.IMAGE,
                        success=False,
                        error=str(e)
                    )

            # Try MLX-based local generation on M-series Macs
            if os.environ.get("USE_MLX_SD", "false").lower() == "true":
                try:
                    from app.services.mlx_generation_service import get_mlx_generator

                    generator = get_mlx_generator()
                    if await generator.is_available():
                        cache_key = self._get_cache_key(prompt, AssetType.IMAGE, dimensions)
                        output_path = str(self._get_cached_path(cache_key, "png"))

                        width = dimensions.get("width", 512) if dimensions else 512
                        height = dimensions.get("height", 512) if dimensions else 512

                        await generator.generate(
                            prompt=prompt,
                            output_path=output_path,
                            width=width,
                            height=height,
                        )

                        logger.info(f"MLX SD generated image: {output_path}")

                        return GeneratedAsset(
                            id=f"mlx_{cache_key}",
                            type=AssetType.IMAGE,
                            local_path=output_path,
                            success=True,
                            metadata={"prompt": prompt, "width": width, "height": height, "method": "mlx_sd"}
                        )
                    else:
                        logger.info("MLX SD not available, falling back")
                except ImportError as e:
                    logger.warning(f"MLX generator import failed: {e}")
                except Exception as e:
                    logger.warning(f"MLX generation failed: {e}")

            # Local SD pipeline not available
            return GeneratedAsset(
                id="sd_not_implemented",
                type=AssetType.IMAGE,
                success=False,
                error="Local Stable Diffusion not available. Install diffusers and set USE_MLX_SD=true."
            )

        except Exception as e:
            logger.error(f"Stable Diffusion generation failed: {str(e)}")
            return GeneratedAsset(
                id="sd_error",
                type=AssetType.IMAGE,
                success=False,
                error=str(e)
            )

    async def fetch_image_url(self, url: str) -> GeneratedAsset:
        """Fetch and cache an image from a URL.

        Args:
            url: The URL to fetch the image from.

        Returns:
            GeneratedAsset with the cached image path.
        """
        try:
            import aiohttp

            cache_key = hashlib.md5(url.encode()).hexdigest()
            cached_path = self._get_cached_path(cache_key, "png")

            if cached_path.exists():
                return GeneratedAsset(
                    id=f"fetch_{cache_key}",
                    type=AssetType.IMAGE,
                    local_path=str(cached_path),
                    url=url,
                    success=True
                )

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.read()

                        # Determine extension from content type
                        content_type = response.headers.get("content-type", "image/png")
                        ext = "png"
                        if "jpeg" in content_type or "jpg" in content_type:
                            ext = "jpg"
                        elif "gif" in content_type:
                            ext = "gif"

                        save_path = self._get_cached_path(cache_key, ext)
                        async with aiofiles.open(save_path, "wb") as f:
                            await f.write(content)

                        return GeneratedAsset(
                            id=f"fetch_{cache_key}",
                            type=AssetType.IMAGE,
                            local_path=str(save_path),
                            url=url,
                            success=True
                        )
                    else:
                        return GeneratedAsset(
                            id=f"fetch_{cache_key}",
                            type=AssetType.IMAGE,
                            success=False,
                            error=f"HTTP {response.status}"
                        )

        except Exception as e:
            logger.error(f"Image fetch failed: {str(e)}")
            return GeneratedAsset(
                id="fetch_error",
                type=AssetType.IMAGE,
                success=False,
                error=str(e)
            )

    def generate_css_animation(self, animation_type: str,
                               duration_ms: int = 500,
                               easing: str = "ease-out",
                               color: Optional[str] = None,
                               intensity: float = 1.0) -> GeneratedAsset:
        """Generate CSS animation keyframes and styles.

        Args:
            animation_type: Type of animation (pulse, glow, shake, etc.)
            duration_ms: Duration in milliseconds.
            easing: Easing function.
            color: Optional color for the animation.
            intensity: Intensity multiplier.

        Returns:
            GeneratedAsset with CSS keyframes and styles.
        """
        animation_id = f"anim_{animation_type}_{duration_ms}"
        keyframes = ""
        css_class = ""

        if animation_type == "pulse":
            scale = 1.0 + (0.1 * intensity)
            keyframes = f"""
@keyframes {animation_id} {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale({scale}); }}
}}"""
            css_class = f"""
.{animation_id} {{
    animation: {animation_id} {duration_ms}ms {easing} infinite;
}}"""

        elif animation_type == "glow":
            glow_color = color or "#22c55e"
            spread = int(20 * intensity)
            keyframes = f"""
@keyframes {animation_id} {{
    0%, 100% {{ box-shadow: 0 0 0 0 {glow_color}40; }}
    50% {{ box-shadow: 0 0 {spread}px {spread // 2}px {glow_color}80; }}
}}"""
            css_class = f"""
.{animation_id} {{
    animation: {animation_id} {duration_ms}ms {easing} infinite;
}}"""

        elif animation_type == "shake":
            offset = int(5 * intensity)
            keyframes = f"""
@keyframes {animation_id} {{
    0%, 100% {{ transform: translateX(0); }}
    25% {{ transform: translateX(-{offset}px); }}
    75% {{ transform: translateX({offset}px); }}
}}"""
            css_class = f"""
.{animation_id} {{
    animation: {animation_id} {duration_ms}ms {easing};
}}"""

        elif animation_type == "fade":
            keyframes = f"""
@keyframes {animation_id} {{
    0% {{ opacity: 0; }}
    100% {{ opacity: 1; }}
}}"""
            css_class = f"""
.{animation_id} {{
    animation: {animation_id} {duration_ms}ms {easing} forwards;
}}"""

        elif animation_type == "bounce":
            height = int(20 * intensity)
            keyframes = f"""
@keyframes {animation_id} {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(-{height}px); }}
}}"""
            css_class = f"""
.{animation_id} {{
    animation: {animation_id} {duration_ms}ms {easing};
}}"""

        elif animation_type == "scale":
            scale = 1.0 + (0.2 * intensity)
            keyframes = f"""
@keyframes {animation_id} {{
    0% {{ transform: scale(1); }}
    50% {{ transform: scale({scale}); }}
    100% {{ transform: scale(1); }}
}}"""
            css_class = f"""
.{animation_id} {{
    animation: {animation_id} {duration_ms}ms {easing};
}}"""

        elif animation_type == "confetti":
            # Confetti is more complex - generate multiple particle animations
            keyframes = f"""
@keyframes {animation_id} {{
    0% {{ transform: translateY(0) rotate(0deg); opacity: 1; }}
    100% {{ transform: translateY(400px) rotate(720deg); opacity: 0; }}
}}"""
            css_class = f"""
.{animation_id} {{
    animation: {animation_id} {duration_ms}ms {easing} forwards;
}}"""

        elif animation_type == "path_draw":
            keyframes = f"""
@keyframes {animation_id} {{
    0% {{ stroke-dashoffset: 1000; }}
    100% {{ stroke-dashoffset: 0; }}
}}"""
            css_class = f"""
.{animation_id} {{
    stroke-dasharray: 1000;
    stroke-dashoffset: 1000;
    animation: {animation_id} {duration_ms}ms {easing} forwards;
}}"""

        else:
            return GeneratedAsset(
                id=animation_id,
                type=AssetType.CSS_ANIMATION,
                success=False,
                error=f"Unknown animation type: {animation_type}"
            )

        return GeneratedAsset(
            id=animation_id,
            type=AssetType.CSS_ANIMATION,
            css_content=css_class.strip(),
            keyframes=keyframes.strip(),
            success=True,
            metadata={
                "animation_type": animation_type,
                "duration_ms": duration_ms,
                "easing": easing,
                "color": color,
                "intensity": intensity
            }
        )

    async def _generate_via_nanobanana(self, planned: PlannedAsset) -> GeneratedAsset:
        """Generate an image via the nanobanana service.

        Args:
            planned: The planned asset specification.

        Returns:
            GeneratedAsset with the generated image.
        """
        if not planned.prompt:
            return GeneratedAsset(
                id=planned.id,
                type=planned.type,
                success=False,
                error="No prompt provided for nanobanana generation"
            )

        try:
            nanobanana = get_nanobanana_service()

            # Check if service is configured
            if not nanobanana.is_configured():
                logger.warning("Nanobanana service not configured, using placeholder")
                # Still try - it will return a placeholder image

            # Build request with dimensions and style
            width = planned.dimensions.get("width", 512) if planned.dimensions else 512
            height = planned.dimensions.get("height", 512) if planned.dimensions else 512
            style = planned.style.get("style") if planned.style else "educational"

            request = NanobananaRequest(
                prompt=planned.prompt,
                width=width,
                height=height,
                style=style
            )

            # Generate image
            response = await nanobanana.generate(request)

            if response.success:
                return GeneratedAsset(
                    id=planned.id,
                    type=planned.type,
                    url=response.image_url,
                    local_path=response.local_path,
                    success=True,
                    metadata={
                        "generation_method": "nanobanana",
                        "latency_ms": response.latency_ms,
                        "width": width,
                        "height": height,
                        "style": style,
                        **(response.metadata or {})
                    }
                )
            else:
                return GeneratedAsset(
                    id=planned.id,
                    type=planned.type,
                    success=False,
                    error=f"Nanobanana generation failed: {response.error}"
                )

        except Exception as e:
            logger.error(f"Nanobanana generation error: {e}")
            return GeneratedAsset(
                id=planned.id,
                type=planned.type,
                success=False,
                error=f"Nanobanana error: {str(e)}"
            )

    async def generate_asset(self, planned: PlannedAsset) -> GeneratedAsset:
        """Generate an asset based on the planned specification.

        Args:
            planned: The planned asset specification.

        Returns:
            GeneratedAsset with the generated content.
        """
        logger.info(f"Generating asset: {planned.id} via {planned.generation_method.value}")

        if planned.generation_method == GenerationMethod.NANOBANANA:
            return await self._generate_via_nanobanana(planned)

        elif planned.generation_method == GenerationMethod.DALLE:
            return await self.generate_image_dalle(planned.prompt, planned.dimensions)

        elif planned.generation_method == GenerationMethod.STABLE_DIFFUSION:
            return await self.generate_image_stable_diffusion(planned.prompt, planned.dimensions)

        elif planned.generation_method == GenerationMethod.FETCH_URL:
            if planned.url:
                return await self.fetch_image_url(planned.url)
            else:
                return GeneratedAsset(
                    id=planned.id,
                    type=planned.type,
                    success=False,
                    error="No URL provided for fetch"
                )

        elif planned.generation_method == GenerationMethod.CSS_ANIMATION:
            style = planned.style or {}
            return self.generate_css_animation(
                animation_type=style.get("type", "pulse"),
                duration_ms=style.get("duration_ms", 500),
                easing=style.get("easing", "ease-out"),
                color=style.get("color"),
                intensity=style.get("intensity", 1.0)
            )

        elif planned.generation_method == GenerationMethod.CACHED:
            # First check if local_path is already provided (asset already exists)
            if planned.local_path:
                local_file = Path(planned.local_path)
                if local_file.exists():
                    logger.info(f"Using existing local file for {planned.id}: {planned.local_path}")
                    return GeneratedAsset(
                        id=planned.id,
                        type=planned.type,
                        local_path=planned.local_path,
                        success=True,
                        metadata={"source": "existing_local_file"}
                    )

            # Then check the cache
            cached = await self.check_cache(
                planned.prompt or planned.id,
                planned.type,
                planned.dimensions
            )
            if cached:
                return GeneratedAsset(
                    id=planned.id,
                    type=planned.type,
                    local_path=cached,
                    success=True
                )
            else:
                return GeneratedAsset(
                    id=planned.id,
                    type=planned.type,
                    success=False,
                    error="Asset not found in cache"
                )

        else:
            return GeneratedAsset(
                id=planned.id,
                type=planned.type,
                success=False,
                error=f"Unknown generation method: {planned.generation_method}"
            )

    async def generate_batch(self, planned_assets: List[PlannedAsset],
                            parallel: bool = True) -> List[GeneratedAsset]:
        """Generate multiple assets, optionally in parallel.

        Args:
            planned_assets: List of planned assets to generate.
            parallel: Whether to generate in parallel.

        Returns:
            List of generated assets.
        """
        # Sort by priority
        sorted_assets = sorted(planned_assets, key=lambda a: a.priority)

        if parallel:
            tasks = [self.generate_asset(asset) for asset in sorted_assets]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for asset in sorted_assets:
                result = await self.generate_asset(asset)
                results.append(result)
            return results


# Global instance
_media_service: Optional[MediaGenerationService] = None


def get_media_service() -> MediaGenerationService:
    """Get or create the global media generation service instance."""
    global _media_service
    if _media_service is None:
        _media_service = MediaGenerationService()
    return _media_service
