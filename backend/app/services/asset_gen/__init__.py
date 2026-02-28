"""
Asset Generation Service for GamED.AI

Spec-based multi-media asset generation workflows using:
- Google Imagen 4 for high-quality raster images
- Gemini native (2.5 Flash Image) for iterative editing & style consistency
- Gemini text models for SVG code generation
- Serper for reference image search
- Pillow for image processing (crop, resize, composite)
"""

from .core import AssetGenService
from .imagen import ImagenGenerator
from .gemini_image import GeminiImageEditor
from .svg_gen import SVGGenerator
from .search import ImageSearcher
from .storage import AssetStorage

__all__ = [
    "AssetGenService",
    "ImagenGenerator",
    "GeminiImageEditor",
    "SVGGenerator",
    "ImageSearcher",
    "AssetStorage",
]
