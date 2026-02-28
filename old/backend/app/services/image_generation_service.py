"""Image Generation Service - DALL-E 3 integration for generating images"""
import os
import hashlib
import uuid
import requests
from pathlib import Path
from typing import Optional, Dict
from openai import OpenAI
from openai import OpenAIError
from dotenv import load_dotenv
from app.utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Set up logging
logger = setup_logger("image_generation_service")


class ImageGenerationService:
    """Service for generating images using OpenAI DALL-E 3"""
    
    def __init__(self):
        """Initialize image generation service"""
        # Check if image generation is enabled
        self.enabled = os.getenv("IMAGE_GENERATION_ENABLED", "true").lower() == "true"
        
        if not self.enabled:
            logger.info("Image generation is disabled via IMAGE_GENERATION_ENABLED")
            self.openai_client = None
            return
        
        # Initialize OpenAI client
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("OPENAI_API_KEY not found - image generation will use placeholders")
            self.openai_client = None
            return
        
        try:
            self.openai_client = OpenAI(api_key=openai_key)
            logger.info("OpenAI client initialized for image generation")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
        
        # Set up storage directory - resolve relative to project root
        storage_path = os.getenv("IMAGE_STORAGE_PATH")
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # Default: backend/static/generated_images relative to project root
            # Get project root (3 levels up from this file: app/services/image_generation_service.py)
            project_root = Path(__file__).parent.parent.parent.parent
            self.storage_path = project_root / "backend" / "static" / "generated_images"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Image storage directory: {self.storage_path.absolute()}")
        
        # In-memory cache: prompt_hash -> image_id
        self._cache: Dict[str, str] = {}
        
        # Base URL for serving images
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        """
        Generate image from prompt and return URL
        
        Args:
            prompt: Text description for image generation
            size: Image size ("1024x1024", "1792x1024", or "1024x1792")
        
        Returns:
            URL to the generated image (or placeholder if generation fails)
        """
        if not self.enabled or not self.openai_client:
            logger.warning("Image generation disabled or OpenAI client not available, using placeholder")
            return self._get_placeholder_url(prompt)
        
        try:
            # Check cache first
            prompt_hash = self._get_prompt_hash(prompt)
            cached_image_id = self._check_cache(prompt_hash)
            if cached_image_id:
                image_path = self.storage_path / f"{cached_image_id}.png"
                if image_path.exists():
                    logger.info(f"Using cached image for prompt hash: {prompt_hash[:16]}...")
                    return f"{self.base_url}/static/images/{cached_image_id}.png"
            
            # Generate new image
            logger.info(f"Generating image with DALL-E 3 - Prompt: {prompt[:100]}...")
            
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            logger.info(f"DALL-E 3 generated image URL: {image_url[:100]}...")
            
            # Download image
            image_data = self._download_image(image_url)
            
            # Generate unique image ID
            image_id = str(uuid.uuid4())
            
            # Store image
            stored_url = self._store_image(image_data, image_id)
            
            # Update cache
            self._cache[prompt_hash] = image_id
            
            logger.info(f"Image generated and stored successfully: {image_id}")
            return stored_url
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error during image generation: {e}")
            return self._get_placeholder_url(prompt)
        except requests.RequestException as e:
            logger.error(f"Network error downloading image: {e}")
            return self._get_placeholder_url(prompt)
        except Exception as e:
            logger.error(f"Unexpected error during image generation: {e}", exc_info=True)
            return self._get_placeholder_url(prompt)
    
    def _get_prompt_hash(self, prompt: str) -> str:
        """Generate SHA256 hash for prompt (for caching)"""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    
    def _check_cache(self, prompt_hash: str) -> Optional[str]:
        """Check if image exists in cache"""
        return self._cache.get(prompt_hash)
    
    def _download_image(self, url: str) -> bytes:
        """Download image from URL"""
        logger.debug(f"Downloading image from: {url[:100]}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        logger.debug(f"Downloaded image: {len(response.content)} bytes")
        return response.content
    
    def _store_image(self, image_data: bytes, image_id: str) -> str:
        """Store image file and return URL"""
        image_path = self.storage_path / f"{image_id}.png"
        
        with open(image_path, 'wb') as f:
            f.write(image_data)
        
        logger.debug(f"Stored image: {image_path}")
        return f"{self.base_url}/static/images/{image_id}.png"
    
    def _get_placeholder_url(self, prompt: str) -> str:
        """Get placeholder URL as fallback"""
        # Use a simple placeholder service
        prompt_safe = prompt.replace(' ', '+')[:50]
        return f"https://placeholder.com/800x600?text={prompt_safe}"

