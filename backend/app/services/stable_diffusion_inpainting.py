"""
Stable Diffusion Inpainting Service for high-quality image inpainting.

Uses HuggingFace diffusers library for local Stable Diffusion inpainting.
Optimized for Apple Silicon (M4 MacBook).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("gamed_ai.services.stable_diffusion")

try:
    from diffusers import StableDiffusionInpaintPipeline
    import torch
    from PIL import Image
    STABLE_DIFFUSION_AVAILABLE = True
except ImportError:
    STABLE_DIFFUSION_AVAILABLE = False
    logger.warning(
        "Stable Diffusion not available. Install with: "
        "pip install diffusers transformers accelerate torch"
    )


class StableDiffusionInpaintingService:
    """
    Local Stable Diffusion inpainting service.
    
    Environment Variables:
    - USE_STABLE_DIFFUSION: Enable Stable Diffusion inpainting (default: false)
    - SD_MODEL_ID: HuggingFace model ID (default: runwayml/stable-diffusion-inpainting)
    - SD_DEVICE: Device to use (default: auto-detect, supports mps for Apple Silicon)
    """
    
    def __init__(self):
        self.enabled = os.getenv("USE_STABLE_DIFFUSION", "false").lower() == "true"
        self.model_id = os.getenv("SD_MODEL_ID", "runwayml/stable-diffusion-inpainting")
        self.pipeline: Optional[StableDiffusionInpaintPipeline] = None
        self.device = self._detect_device()
        
    def _detect_device(self) -> str:
        """Detect best device for inference."""
        if not STABLE_DIFFUSION_AVAILABLE:
            return "cpu"
        
        if torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def _load_pipeline(self):
        """Lazy load the Stable Diffusion pipeline."""
        if not STABLE_DIFFUSION_AVAILABLE:
            raise RuntimeError("Stable Diffusion dependencies not installed")
        
        if self.pipeline is None:
            logger.info(f"Loading Stable Diffusion model: {self.model_id} on {self.device}")
            self.pipeline = StableDiffusionInpaintPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
            )
            self.pipeline = self.pipeline.to(self.device)
            logger.info(f"Stable Diffusion pipeline loaded on {self.device}")
    
    async def inpaint(
        self,
        image_path: str,
        mask_path: str,
        output_path: str,
        prompt: str = "",
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5
    ) -> str:
        """
        Inpaint image using Stable Diffusion.
        
        Args:
            image_path: Path to source image
            mask_path: Path to mask image (white=inpaint, black=keep)
            output_path: Path for output image
            prompt: Text prompt for inpainting (optional, empty uses default)
            num_inference_steps: Number of denoising steps (default: 20)
            guidance_scale: Guidance scale (default: 7.5)
            
        Returns:
            Path to inpainted image
        """
        if not self.enabled:
            raise RuntimeError("Stable Diffusion not enabled. Set USE_STABLE_DIFFUSION=true")
        
        if not STABLE_DIFFUSION_AVAILABLE:
            raise RuntimeError("Stable Diffusion dependencies not installed")
        
        self._load_pipeline()
        
        # Load image and mask
        image = Image.open(image_path).convert("RGB")
        mask_image = Image.open(mask_path).convert("L")
        
        # Resize mask to match image if needed
        if mask_image.size != image.size:
            mask_image = mask_image.resize(image.size, Image.Resampling.LANCZOS)
        
        # Use default prompt if not provided
        if not prompt:
            prompt = "clean diagram background, seamless inpainting, no artifacts"
        
        logger.info(f"Running Stable Diffusion inpainting on {self.device}...")
        
        # Run inpainting
        result = self.pipeline(
            prompt=prompt,
            image=image,
            mask_image=mask_image,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        ).images[0]
        
        # Save result
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.save(output_path)
        
        logger.info(f"Stable Diffusion inpainting saved to {output_path}")
        return output_path
    
    def is_available(self) -> bool:
        """Check if Stable Diffusion is available and enabled."""
        return self.enabled and STABLE_DIFFUSION_AVAILABLE


# Singleton instance
_stable_diffusion_service: Optional[StableDiffusionInpaintingService] = None


def get_stable_diffusion_service() -> StableDiffusionInpaintingService:
    """Get singleton Stable Diffusion service instance."""
    global _stable_diffusion_service
    if _stable_diffusion_service is None:
        _stable_diffusion_service = StableDiffusionInpaintingService()
    return _stable_diffusion_service
