import os
from typing import Any, Dict, List
from google import genai
from google.genai import types


class ImagenGenerator:
    """Wrapper for Google Imagen API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable required")
        
        self.client = genai.Client(api_key=self.api_key)
    
    def generate_images(
        self,
        prompt: str,
        config: Dict[str, Any],
        safety_settings: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Generate images using Imagen API."""
        
        # Convert safety settings
        safety_config = []
        for setting in safety_settings:
            safety_config.append(
                types.SafetySetting(
                    category=getattr(types.HarmCategory, setting["category"]),
                    threshold=getattr(types.HarmBlockThreshold, setting["threshold"])
                )
            )
        
        # Create generation config
        generate_config = types.GenerateImagesConfig(
            number_of_images=config["numberOfImages"],
            aspect_ratio=config["aspectRatio"],
            image_size=config["imageSize"],
            person_generation=getattr(types.PersonGeneration, config["personGeneration"].upper()),
            safety_settings=safety_config,
        )
        
        if config.get("seed"):
            generate_config.seed = config["seed"]
        
        # Generate images
        response = self.client.models.generate_images(
            model=config.get("model", "imagen-4.0-generate-001"),
            prompt=prompt,
            config=generate_config,
        )
        
        # Convert response to our format
        results = []
        for img in response.generated_images:
            results.append({
                "id": f"imagen_{len(results)}",
                "url": img.image.uri if hasattr(img.image, 'uri') else str(img.image),
                "metadata": {
                    "seed": config.get("seed"),
                    "model": config.get("model", "imagen-4.0-generate-001"),
                }
            })
        
        return results