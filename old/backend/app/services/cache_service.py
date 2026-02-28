"""Cache service for story and blueprint generation"""
import hashlib
import json
from typing import Optional, Dict, Any
from pathlib import Path
from app.utils.logger import setup_logger

logger = setup_logger("cache_service")

class CacheService:
    """Service to cache generated story and blueprint data"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache service"""
        if cache_dir is None:
            # Default cache directory in backend/cache
            cache_dir = Path(__file__).parent.parent.parent / "cache"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache service initialized with directory: {self.cache_dir}")
    
    def _get_question_hash(self, question_text: str, options: list = None) -> str:
        """Generate hash from question text and options"""
        # Normalize question text (lowercase, strip whitespace)
        normalized_text = question_text.lower().strip()
        
        # Include options if present
        if options:
            normalized_options = [str(opt).lower().strip() for opt in options]
            normalized_options.sort()  # Sort for consistent hashing
            cache_key = f"{normalized_text}|||{json.dumps(normalized_options, sort_keys=True)}"
        else:
            cache_key = normalized_text
        
        # Generate SHA256 hash
        hash_obj = hashlib.sha256(cache_key.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def _get_cache_path(self, question_hash: str, data_type: str) -> Path:
        """Get cache file path for a question hash and data type"""
        return self.cache_dir / f"{question_hash}_{data_type}.json"
    
    def get_story(self, question_text: str, options: list = None) -> Optional[Dict[str, Any]]:
        """Get cached story data for a question"""
        question_hash = self._get_question_hash(question_text, options)
        cache_path = self._get_cache_path(question_hash, "story")
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                logger.info(f"Cache HIT for story - hash: {question_hash[:8]}...")
                return cached_data
            except Exception as e:
                logger.warning(f"Failed to read story cache: {e}")
        
        logger.debug(f"Cache MISS for story - hash: {question_hash[:8]}...")
        return None
    
    def get_blueprint(self, question_text: str, options: list = None) -> Optional[Dict[str, Any]]:
        """Get cached blueprint data for a question"""
        question_hash = self._get_question_hash(question_text, options)
        cache_path = self._get_cache_path(question_hash, "blueprint")
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                logger.info(f"Cache HIT for blueprint - hash: {question_hash[:8]}...")
                return cached_data
            except Exception as e:
                logger.warning(f"Failed to read blueprint cache: {e}")
        
        logger.debug(f"Cache MISS for blueprint - hash: {question_hash[:8]}...")
        return None
    
    def save_story(self, question_text: str, options: list, story_data: Dict[str, Any]) -> bool:
        """Save story data to cache"""
        question_hash = self._get_question_hash(question_text, options)
        cache_path = self._get_cache_path(question_hash, "story")
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(story_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Cached story - hash: {question_hash[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to save story cache: {e}")
            return False
    
    def save_blueprint(self, question_text: str, options: list, blueprint_data: Dict[str, Any], template_type: str = None) -> bool:
        """Save blueprint data to cache"""
        question_hash = self._get_question_hash(question_text, options)
        cache_path = self._get_cache_path(question_hash, "blueprint")
        
        try:
            # Include template_type in cached data for reference
            cache_data = {
                "blueprint": blueprint_data,
                "template_type": template_type
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Cached blueprint - hash: {question_hash[:8]}..., template: {template_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to save blueprint cache: {e}")
            return False
    
    def has_cache(self, question_text: str, options: list = None) -> Dict[str, bool]:
        """Check if cache exists for story and/or blueprint"""
        question_hash = self._get_question_hash(question_text, options)
        story_path = self._get_cache_path(question_hash, "story")
        blueprint_path = self._get_cache_path(question_hash, "blueprint")
        
        return {
            "story": story_path.exists(),
            "blueprint": blueprint_path.exists(),
            "both": story_path.exists() and blueprint_path.exists()
        }

