try:
    from .imagen import ImagenGenerator
except ImportError:
    ImagenGenerator = None

try:
    from .gemini_image import GeminiImageGenerator
except ImportError:
    GeminiImageGenerator = None

from .sprite_packer import SpritePacker

try:
    from .vectorizer import Vectorizer
except ImportError:
    Vectorizer = None