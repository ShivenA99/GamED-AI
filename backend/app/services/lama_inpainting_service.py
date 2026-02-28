"""
LaMa Inpainting Service via IOPaint API.

LaMa (Large Mask inpainting) is a state-of-the-art inpainting model that
produces much better results than OpenCV for removing labels and leader lines
from educational diagrams.

Requires IOPaint to be running:
    pip install iopaint
    iopaint start --model=lama --device=mps --port=8080
"""

import base64
import io
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("gamed_ai.services.lama_inpainting")


class LaMaInpaintingService:
    """
    Inpaint images using LaMa via IOPaint HTTP API.

    IOPaint provides a simple HTTP interface to LaMa and other inpainting models.
    """

    def __init__(self, url: str = None, timeout: float = 60.0):
        """
        Initialize the LaMa inpainting service.

        Args:
            url: IOPaint server URL (default: http://localhost:8080)
            timeout: Request timeout in seconds
        """
        self.url = url or os.getenv("IOPAINT_URL", "http://localhost:8080")
        self.timeout = timeout
        self._available = None
        logger.info(f"LaMaInpaintingService initialized with URL: {self.url}")

    async def is_available(self) -> bool:
        """Check if IOPaint server is available."""
        if self._available is not None:
            return self._available

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.url}/")
                self._available = response.status_code == 200
        except Exception as e:
            logger.warning(f"IOPaint server not available at {self.url}: {e}")
            self._available = False

        return self._available

    async def inpaint(
        self,
        image_path: str,
        mask_path: str,
        output_path: str
    ) -> str:
        """
        Inpaint an image using LaMa via IOPaint API.

        Args:
            image_path: Path to the input image
            mask_path: Path to the binary mask (white = areas to inpaint)
            output_path: Path to save the inpainted result

        Returns:
            Path to the output image
        """
        # Read and encode image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode()

        # Read and encode mask
        with open(mask_path, "rb") as f:
            mask_bytes = f.read()
        mask_b64 = base64.b64encode(mask_bytes).decode()

        # Determine image type from extension
        ext = Path(image_path).suffix.lower()
        media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"

        logger.info(f"Sending inpainting request to IOPaint: {image_path}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.url}/inpaint",
                    json={
                        "image": f"data:{media_type};base64,{image_b64}",
                        "mask": f"data:image/png;base64,{mask_b64}",
                    },
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    logger.error(f"IOPaint error: {response.status_code} - {response.text}")
                    raise RuntimeError(f"IOPaint inpainting failed: {response.status_code}")

                result = response.json()

        except httpx.TimeoutException:
            logger.error(f"IOPaint request timed out after {self.timeout}s")
            raise RuntimeError("IOPaint request timed out")
        except httpx.ConnectError:
            logger.error(f"Could not connect to IOPaint at {self.url}")
            raise RuntimeError(f"IOPaint not available at {self.url}")

        # Decode output
        output_data = result.get("image") or result.get("output")
        if not output_data:
            logger.error(f"No output in IOPaint response: {result.keys()}")
            raise RuntimeError("IOPaint returned no output image")

        # Handle base64 with or without data URI prefix
        if output_data.startswith("data:"):
            output_data = output_data.split(",", 1)[1]

        output_bytes = base64.b64decode(output_data)

        # Save output
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(output_bytes)

        logger.info(f"LaMa inpainting complete: {output_path}")
        return output_path

    async def inpaint_bytes(
        self,
        image_bytes: bytes,
        mask_bytes: bytes,
        image_format: str = "png"
    ) -> bytes:
        """
        Inpaint image bytes and return result bytes.

        Args:
            image_bytes: Input image bytes
            mask_bytes: Mask image bytes
            image_format: Output format (png or jpeg)

        Returns:
            Inpainted image bytes
        """
        image_b64 = base64.b64encode(image_bytes).decode()
        mask_b64 = base64.b64encode(mask_bytes).decode()

        media_type = "image/jpeg" if image_format == "jpeg" else "image/png"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.url}/inpaint",
                json={
                    "image": f"data:{media_type};base64,{image_b64}",
                    "mask": f"data:image/png;base64,{mask_b64}",
                }
            )

            if response.status_code != 200:
                raise RuntimeError(f"IOPaint inpainting failed: {response.status_code}")

            result = response.json()

        output_data = result.get("image") or result.get("output")
        if output_data.startswith("data:"):
            output_data = output_data.split(",", 1)[1]

        return base64.b64decode(output_data)


class SDInpaintingService:
    """
    Stable Diffusion inpainting for highest quality results.

    This is slower than LaMa but can produce better results for
    complex inpainting tasks.
    """

    def __init__(self):
        """Initialize the SD inpainting service."""
        self._pipe = None
        self._device = None
        self.num_steps = int(os.getenv("SD_INPAINT_STEPS", "30"))
        self.guidance_scale = float(os.getenv("SD_GUIDANCE_SCALE", "7.5"))
        logger.info(f"SDInpaintingService initialized: steps={self.num_steps}")

    def _ensure_loaded(self):
        """Lazy load the SD inpainting pipeline."""
        if self._pipe is not None:
            return

        try:
            import torch
            from diffusers import StableDiffusionInpaintPipeline

            logger.info("Loading Stable Diffusion inpainting pipeline...")

            # Choose device
            if torch.backends.mps.is_available():
                self._device = "mps"
                dtype = torch.float32  # MPS doesn't support float16 for all ops
            elif torch.cuda.is_available():
                self._device = "cuda"
                dtype = torch.float16
            else:
                self._device = "cpu"
                dtype = torch.float32

            self._pipe = StableDiffusionInpaintPipeline.from_pretrained(
                "runwayml/stable-diffusion-inpainting",
                torch_dtype=dtype
            )
            self._pipe = self._pipe.to(self._device)

            # Optimize for memory
            if hasattr(self._pipe, "enable_attention_slicing"):
                self._pipe.enable_attention_slicing()

            logger.info(f"SD inpainting pipeline loaded on device: {self._device}")

        except ImportError as e:
            logger.error(f"Failed to import diffusers/torch: {e}")
            raise ImportError(
                "SD inpainting requires diffusers and torch. Install with: "
                "pip install diffusers transformers accelerate torch"
            )

    async def is_available(self) -> bool:
        """Check if SD inpainting is available."""
        try:
            import diffusers  # noqa: F401
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    async def inpaint(
        self,
        image_path: str,
        mask_path: str,
        output_path: str,
        prompt: str = "clean diagram background, seamless texture"
    ) -> str:
        """
        Inpaint an image using Stable Diffusion.

        Args:
            image_path: Path to the input image
            mask_path: Path to the binary mask
            output_path: Path to save the result
            prompt: Text prompt guiding the inpainting

        Returns:
            Path to the output image
        """
        from PIL import Image

        self._ensure_loaded()

        # Load images
        image = Image.open(image_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")

        # SD inpainting expects 512x512 or similar
        original_size = image.size
        target_size = (512, 512)

        image_resized = image.resize(target_size, Image.Resampling.LANCZOS)
        mask_resized = mask.resize(target_size, Image.Resampling.LANCZOS)

        logger.info(f"Running SD inpainting with prompt: '{prompt}'")

        # Run inpainting
        result = self._pipe(
            prompt=prompt,
            image=image_resized,
            mask_image=mask_resized,
            num_inference_steps=self.num_steps,
            guidance_scale=self.guidance_scale
        ).images[0]

        # Resize back to original size
        result = result.resize(original_size, Image.Resampling.LANCZOS)

        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.save(output_path)

        logger.info(f"SD inpainting complete: {output_path}")
        return output_path


def opencv_inpaint(
    image_path: str,
    mask_path: str,
    output_path: str,
    method: str = "NS",
    radius: int = 5
) -> str:
    """
    Fallback inpainting using OpenCV (fast but lower quality).

    Args:
        image_path: Path to the input image
        mask_path: Path to the binary mask
        output_path: Path to save the result
        method: "NS" (Navier-Stokes) or "TELEA" (Fast Marching)
        radius: Inpainting radius

    Returns:
        Path to the output image
    """
    import cv2

    image = cv2.imread(image_path)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    if mask is None:
        raise ValueError(f"Could not load mask: {mask_path}")

    # Ensure mask matches image size
    if mask.shape[:2] != image.shape[:2]:
        mask = cv2.resize(mask, (image.shape[1], image.shape[0]))

    # Choose method
    flags = cv2.INPAINT_NS if method == "NS" else cv2.INPAINT_TELEA

    # Inpaint
    result = cv2.inpaint(image, mask, radius, flags)

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, result)

    logger.info(f"OpenCV inpainting ({method}) complete: {output_path}")
    return output_path


# Singleton instances
_lama_service: Optional[LaMaInpaintingService] = None
_sd_service: Optional[SDInpaintingService] = None


def get_lama_service() -> LaMaInpaintingService:
    """Get or create the LaMa service singleton."""
    global _lama_service
    if _lama_service is None:
        _lama_service = LaMaInpaintingService()
    return _lama_service


def get_sd_service() -> SDInpaintingService:
    """Get or create the SD service singleton."""
    global _sd_service
    if _sd_service is None:
        _sd_service = SDInpaintingService()
    return _sd_service


def get_inpainting_method() -> str:
    """Get the configured inpainting method."""
    return os.getenv("INPAINTING_METHOD", "lama")
