"""Imagen 4 image generation via google-genai SDK."""

import logging
import os
from io import BytesIO
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger("gamed_ai.asset_gen.imagen")


class ImagenGenerator:
    """Generate images using Google Imagen 4.

    Uses the unified google-genai SDK with:
    - imagen-4.0-generate-001 for high quality (default)
    - imagen-4.0-fast-generate-001 for speed/batch
    """

    MODELS = {
        "standard": "imagen-4.0-generate-001",
        "fast": "imagen-4.0-fast-generate-001",
        "ultra": "imagen-4.0-ultra-generate-001",
    }

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GOOGLE_API_KEY not set")
        self.client = genai.Client(api_key=key)

    async def generate(
        self,
        prompt: str,
        *,
        model: str = "standard",
        num_images: int = 1,
        aspect_ratio: str = "4:3",
        image_size: str = "1K",
        seed: int | None = None,
        safety_level: str = "block_low_and_above",
    ) -> list[bytes]:
        """Generate images from text prompt.

        Args:
            prompt: Text description of image to generate
            model: "standard", "fast", or "ultra"
            num_images: Number of images (1-4)
            aspect_ratio: "1:1", "3:4", "4:3", "9:16", "16:9"
            image_size: "1K" or "2K" (2K not available on fast)
            seed: Deterministic seed (disables watermark)
            safety_level: Safety filter level

        Returns:
            List of image bytes (PNG format)
        """
        model_id = self.MODELS.get(model, model)
        logger.info(f"Imagen generate: model={model_id}, ratio={aspect_ratio}, size={image_size}")

        config_kwargs = dict(
            number_of_images=min(num_images, 4),
            aspect_ratio=aspect_ratio,
            output_mime_type="image/png",
            safety_filter_level=safety_level,
            person_generation="allow_adult",
        )
        # Fast model doesn't support image_size
        if model != "fast" and image_size:
            config_kwargs["image_size"] = image_size

        config = types.GenerateImagesConfig(**config_kwargs)

        if seed is not None:
            config.seed = seed
            config.add_watermark = False

        try:
            response = self.client.models.generate_images(
                model=model_id,
                prompt=prompt,
                config=config,
            )
        except Exception as e:
            logger.error(f"Imagen generation failed: {e}")
            raise

        results = []
        for img in response.generated_images:
            results.append(img.image.image_bytes)

        logger.info(f"Imagen generated {len(results)} images")
        return results

    async def generate_educational_diagram(
        self,
        subject: str,
        structures: list[str],
        style: str = "clean medical illustration",
        aspect_ratio: str = "4:3",
        include_labels: bool = False,
    ) -> bytes:
        """Generate a clean educational diagram.

        Args:
            subject: What to draw (e.g., "human heart cross-section")
            structures: List of structures to include
            style: Visual style description
            include_labels: Whether to include text labels
            aspect_ratio: Image aspect ratio

        Returns:
            PNG image bytes
        """
        structures_text = ", ".join(structures)
        label_instruction = (
            f"with clear black text labels pointing to each structure: {structures_text}"
            if include_labels
            else f"showing these structures clearly but WITHOUT any text labels or annotations: {structures_text}"
        )

        prompt = (
            f"A {style} of {subject}, "
            f"{label_instruction}. "
            f"White background, high contrast, clean edges, "
            f"no decorative elements, no shadows, no watermarks. "
            f"Textbook quality, anatomically accurate, "
            f"suitable for an educational interactive game."
        )

        images = await self.generate(
            prompt,
            model="standard",
            num_images=1,
            aspect_ratio=aspect_ratio,
            image_size="2K",
        )
        return images[0]

    async def generate_item_illustration(
        self,
        item_name: str,
        context: str,
        style: str = "scientific illustration",
        aspect_ratio: str = "1:1",
        size: str = "1K",
    ) -> bytes:
        """Generate a single item illustration for cards.

        Args:
            item_name: Name of the item (e.g., "Mitochondria")
            context: Context for the illustration
            style: Visual style
            aspect_ratio: Image aspect ratio
            size: Image resolution

        Returns:
            PNG image bytes
        """
        prompt = (
            f"A {style} of {item_name}. {context}. "
            f"Clean white background, centered composition, "
            f"high detail, no text labels, no annotations, "
            f"suitable for an educational game card."
        )

        images = await self.generate(
            prompt,
            model="fast",
            num_images=1,
            aspect_ratio=aspect_ratio,
            image_size=size,
        )
        return images[0]
