"""
MLX-based local image generation for M-series Macs.

This service provides local image generation using Apple's Metal Performance Shaders
via the diffusers library with MPS backend. It's optimized for M-series MacBooks
and avoids cloud API costs for image generation.

Requirements:
    pip install diffusers torch torchvision accelerate

Environment Variables:
    MLX_SD_MODEL: Model ID to use (default: "stabilityai/stable-diffusion-2-1-base")
    USE_MLX_SD: Set to "true" to enable MLX-based generation
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("gamed_ai.services.mlx_generation")


class MLXImageGenerator:
    """Generate images locally using MLX-optimized Stable Diffusion."""

    def __init__(self):
        self._pipe = None
        self._is_available: Optional[bool] = None
        self.model_id = os.getenv("MLX_SD_MODEL", "stabilityai/stable-diffusion-2-1-base")

    async def is_available(self) -> bool:
        """Check if MPS (Metal Performance Shaders) is available for image generation."""
        if self._is_available is not None:
            return self._is_available

        try:
            import torch
            self._is_available = torch.backends.mps.is_available()
            if self._is_available:
                logger.info(f"MPS available for local image generation with model: {self.model_id}")
            else:
                logger.info("MPS not available - local image generation disabled")
            return self._is_available
        except ImportError:
            logger.warning("torch not installed - local image generation unavailable")
            self._is_available = False
            return False
        except Exception as e:
            logger.warning(f"Error checking MPS availability: {e}")
            self._is_available = False
            return False

    def _ensure_loaded(self):
        """Lazy-load the Stable Diffusion pipeline."""
        if self._pipe is not None:
            return

        logger.info(f"Loading Stable Diffusion model: {self.model_id}")

        try:
            from diffusers import StableDiffusionPipeline
            import torch

            # Load with float16 for efficiency
            self._pipe = StableDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16,
            ).to("mps")

            # Enable attention slicing for memory efficiency on M-series
            self._pipe.enable_attention_slicing()

            # Disable safety checker for educational content (optional)
            # self._pipe.safety_checker = None

            logger.info("Stable Diffusion model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Stable Diffusion model: {e}")
            raise

    async def generate(
        self,
        prompt: str,
        output_path: str,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        negative_prompt: str = "blurry, bad quality, distorted, ugly",
    ) -> str:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the desired image
            output_path: Path where to save the generated image
            width: Image width (default 512)
            height: Image height (default 512)
            num_inference_steps: Number of denoising steps (default 20)
            guidance_scale: How closely to follow the prompt (default 7.5)
            negative_prompt: What to avoid in the image

        Returns:
            Path to the saved image
        """
        # Run in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._generate_sync,
            prompt,
            output_path,
            width,
            height,
            num_inference_steps,
            guidance_scale,
            negative_prompt,
        )

    def _generate_sync(
        self,
        prompt: str,
        output_path: str,
        width: int,
        height: int,
        num_inference_steps: int,
        guidance_scale: float,
        negative_prompt: str,
    ) -> str:
        """Synchronous image generation (runs in thread)."""
        self._ensure_loaded()

        logger.info(f"Generating image: {prompt[:50]}...")

        result = self._pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )

        image = result.images[0]

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Save the image
        image.save(output_path)
        logger.info(f"Image saved to: {output_path}")

        return output_path

    async def generate_educational_diagram_asset(
        self,
        asset_type: str,
        description: str,
        output_path: str,
    ) -> str:
        """
        Generate an educational diagram asset with optimized prompts.

        Args:
            asset_type: Type of asset (background, icon, illustration)
            description: Description of the asset
            output_path: Path to save the image

        Returns:
            Path to the saved image
        """
        # Build optimized prompt for educational content
        base_prompts = {
            "background": "clean minimalist educational background, light colors, subtle gradient, professional",
            "icon": "simple flat icon, educational style, clean lines, minimal detail",
            "illustration": "educational illustration, clear and simple, scientific accuracy, labeled parts visible",
        }

        base = base_prompts.get(asset_type, "educational diagram, clean and professional")
        full_prompt = f"{base}, {description}"

        # Use smaller size for icons
        if asset_type == "icon":
            width, height = 256, 256
        else:
            width, height = 512, 512

        return await self.generate(
            prompt=full_prompt,
            output_path=output_path,
            width=width,
            height=height,
        )


# Singleton instance
_generator: Optional[MLXImageGenerator] = None


def get_mlx_generator() -> MLXImageGenerator:
    """Get the singleton MLX image generator instance."""
    global _generator
    if _generator is None:
        _generator = MLXImageGenerator()
    return _generator
