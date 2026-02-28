"""
Vision Tools for GamED.AI v2

Tools for image analysis using Gemini Vision, diagram generation using DALL-E 3,
and zone detection for educational diagrams.
"""

import os
import json
import base64
from typing import Dict, Any, List, Optional
import httpx

from app.utils.logging_config import get_logger
from app.tools.registry import register_tool

logger = get_logger("gamed_ai.tools.vision")


# ============================================================================
# Tool Implementations
# ============================================================================

async def generate_diagram_image_impl(
    prompt: str,
    style: str = "educational",
    size: str = "1024x1024"
) -> Dict[str, Any]:
    """
    Generate a clean educational diagram using DALL-E 3.

    Args:
        prompt: Description of the diagram to generate
        style: Image style (educational, technical, simple)
        size: Image size (1024x1024, 1024x1792, 1792x1024)

    Returns:
        Dict with image_url, revised_prompt, metadata
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        logger.warning("OPENAI_API_KEY not set, cannot generate images")
        return {
            "image_url": None,
            "error": "OPENAI_API_KEY not configured"
        }

    # Enhance prompt for educational diagrams
    enhanced_prompt = f"""Create a clean, professional educational diagram: {prompt}

Style requirements:
- Clean white or light background
- Clear, well-separated visual elements
- No text labels or annotations on the image
- Professional scientific illustration style
- High contrast for clarity
- {style} style"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "dall-e-3",
                    "prompt": enhanced_prompt,
                    "size": size,
                    "quality": "standard",
                    "n": 1
                }
            )
            response.raise_for_status()
            data = response.json()

        image_data = data.get("data", [{}])[0]

        return {
            "image_url": image_data.get("url"),
            "revised_prompt": image_data.get("revised_prompt"),
            "original_prompt": prompt,
            "size": size,
            "model": "dall-e-3"
        }

    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return {
            "image_url": None,
            "error": str(e)
        }


async def detect_zones_impl(
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    structure_names: Optional[List[str]] = None,
    detection_mode: str = "auto"
) -> Dict[str, Any]:
    """
    Detect zones/regions in a diagram using Gemini Vision.

    Args:
        image_url: URL of the image to analyze
        image_base64: Base64-encoded image data
        structure_names: Optional list of structures to detect
        detection_mode: Detection mode (auto, labeled, unlabeled)

    Returns:
        Dict with zones list containing name, bbox, center, confidence
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        logger.warning("GOOGLE_API_KEY not set, cannot detect zones")
        return {
            "zones": [],
            "error": "GOOGLE_API_KEY not configured"
        }

    if not image_url and not image_base64:
        return {
            "zones": [],
            "error": "Either image_url or image_base64 is required"
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=google_api_key)

        # Build prompt for zone detection
        structure_hint = ""
        if structure_names:
            structure_hint = f"\n\nLook specifically for these structures: {', '.join(structure_names)}"

        detection_prompt = f"""Analyze this educational diagram and identify distinct regions/zones.

For each identifiable structure or region:
1. Provide a descriptive name
2. Estimate its bounding box as [x1, y1, x2, y2] in normalized coordinates (0-1)
3. Estimate the center point [cx, cy] in normalized coordinates
4. Provide a confidence score (0-1)

Detection mode: {detection_mode}
{structure_hint}

Respond in JSON format:
{{
    "zones": [
        {{
            "name": "structure name",
            "bbox": [x1, y1, x2, y2],
            "center": [cx, cy],
            "confidence": 0.95,
            "description": "brief description"
        }}
    ],
    "diagram_type": "anatomy|chemistry|physics|other",
    "total_structures": 5
}}"""

        # Prepare content with image
        contents = []

        if image_url:
            # Fetch image and convert to base64
            async with httpx.AsyncClient(timeout=30) as http_client:
                img_response = await http_client.get(image_url)
                img_response.raise_for_status()
                image_bytes = img_response.content
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Build Gemini request with image
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type="image/jpeg",
                                data=base64.b64decode(image_base64)
                            )
                        ),
                        types.Part(text=detection_prompt)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096
            )
        )

        # Parse response
        text_content = ""
        if hasattr(response, 'text'):
            text_content = response.text
        elif hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    text_content += part.text

        # Extract JSON from response
        try:
            # Try to find JSON in response
            start = text_content.find("{")
            end = text_content.rfind("}") + 1
            if start != -1 and end > start:
                json_str = text_content[start:end]
                result = json.loads(json_str)
                return result
        except json.JSONDecodeError:
            pass

        # If JSON parsing fails, return raw zones
        return {
            "zones": [],
            "raw_response": text_content[:500],
            "error": "Could not parse zone detection response"
        }

    except Exception as e:
        logger.error(f"Zone detection failed: {e}", exc_info=True)
        return {
            "zones": [],
            "error": str(e)
        }


async def classify_diagram_impl(
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify a diagram as labeled or unlabeled using Gemini Vision.

    Args:
        image_url: URL of the image to analyze
        image_base64: Base64-encoded image data

    Returns:
        Dict with is_labeled, label_count, label_style, confidence
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        return {
            "is_labeled": False,
            "error": "GOOGLE_API_KEY not configured"
        }

    if not image_url and not image_base64:
        return {
            "is_labeled": False,
            "error": "Either image_url or image_base64 is required"
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=google_api_key)

        classification_prompt = """Analyze this diagram and determine if it has text labels/annotations.

Check for:
1. Text labels pointing to parts of the diagram
2. Leader lines connecting text to structures
3. Numbered or lettered annotations
4. Any text overlay on the image

Respond in JSON format:
{
    "is_labeled": true/false,
    "label_count": 0,
    "label_style": "leader_lines|numbered|lettered|inline|none",
    "confidence": 0.95,
    "detected_labels": ["label1", "label2"]
}"""

        # Prepare image content
        if image_url:
            async with httpx.AsyncClient(timeout=30) as http_client:
                img_response = await http_client.get(image_url)
                img_response.raise_for_status()
                image_bytes = img_response.content
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type="image/jpeg",
                                data=base64.b64decode(image_base64)
                            )
                        ),
                        types.Part(text=classification_prompt)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=1024
            )
        )

        # Parse response
        text_content = ""
        if hasattr(response, 'text'):
            text_content = response.text
        elif hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    text_content += part.text

        try:
            start = text_content.find("{")
            end = text_content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text_content[start:end])
        except json.JSONDecodeError:
            pass

        return {
            "is_labeled": False,
            "confidence": 0.5,
            "error": "Could not parse classification response"
        }

    except Exception as e:
        logger.error(f"Diagram classification failed: {e}")
        return {
            "is_labeled": False,
            "error": str(e)
        }


async def locate_structures_impl(
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    structures_to_find: List[str] = None
) -> Dict[str, Any]:
    """
    Locate specific structures in an unlabeled diagram using Gemini Vision.

    Args:
        image_url: URL of the image
        image_base64: Base64-encoded image data
        structures_to_find: List of structure names to locate

    Returns:
        Dict with located_structures containing name, position, confidence
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        return {
            "located_structures": [],
            "error": "GOOGLE_API_KEY not configured"
        }

    if not structures_to_find:
        return {
            "located_structures": [],
            "error": "structures_to_find is required"
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=google_api_key)

        structures_list = ", ".join(structures_to_find)

        location_prompt = f"""Locate these specific structures in the diagram: {structures_list}

For each structure you can identify:
1. Provide the exact name from the list
2. Give the center position in normalized coordinates [x, y] where (0,0) is top-left and (1,1) is bottom-right
3. Estimate a bounding box [x1, y1, x2, y2]
4. Rate your confidence (0-1)

Respond in JSON format:
{{
    "located_structures": [
        {{
            "name": "structure name",
            "center": [0.5, 0.5],
            "bbox": [0.3, 0.3, 0.7, 0.7],
            "confidence": 0.9,
            "found": true
        }}
    ],
    "not_found": ["structure names not found in image"]
}}"""

        if image_url:
            async with httpx.AsyncClient(timeout=30) as http_client:
                img_response = await http_client.get(image_url)
                img_response.raise_for_status()
                image_bytes = img_response.content
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type="image/jpeg",
                                data=base64.b64decode(image_base64)
                            )
                        ),
                        types.Part(text=location_prompt)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4096
            )
        )

        text_content = ""
        if hasattr(response, 'text'):
            text_content = response.text
        elif hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    text_content += part.text

        try:
            start = text_content.find("{")
            end = text_content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text_content[start:end])
        except json.JSONDecodeError:
            pass

        return {
            "located_structures": [],
            "error": "Could not parse location response"
        }

    except Exception as e:
        logger.error(f"Structure location failed: {e}")
        return {
            "located_structures": [],
            "error": str(e)
        }


# ============================================================================
# Tool Registration
# ============================================================================

def register_vision_tools() -> None:
    """Register all vision tools in the registry."""

    # generate_diagram_image
    register_tool(
        name="generate_diagram_image",
        description="Generate a clean educational diagram using DALL-E 3. Creates unlabeled diagrams suitable for labeling exercises.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of the diagram to generate"
                },
                "style": {
                    "type": "string",
                    "description": "Image style (educational, technical, simple)",
                    "default": "educational"
                },
                "size": {
                    "type": "string",
                    "description": "Image size",
                    "enum": ["1024x1024", "1024x1792", "1792x1024"],
                    "default": "1024x1024"
                }
            },
            "required": ["prompt"]
        },
        function=generate_diagram_image_impl
    )

    # detect_zones
    register_tool(
        name="detect_zones",
        description="Detect zones/regions in a diagram using Gemini Vision. Returns bounding boxes and center points for each identifiable structure.",
        parameters={
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to analyze"
                },
                "image_base64": {
                    "type": "string",
                    "description": "Base64-encoded image data"
                },
                "structure_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific structures to detect"
                },
                "detection_mode": {
                    "type": "string",
                    "description": "Detection mode",
                    "enum": ["auto", "labeled", "unlabeled"],
                    "default": "auto"
                }
            }
        },
        function=detect_zones_impl
    )

    # classify_diagram
    register_tool(
        name="classify_diagram",
        description="Classify a diagram as labeled or unlabeled using Gemini Vision. Detects presence of text annotations and leader lines.",
        parameters={
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to analyze"
                },
                "image_base64": {
                    "type": "string",
                    "description": "Base64-encoded image data"
                }
            }
        },
        function=classify_diagram_impl
    )

    # locate_structures
    register_tool(
        name="locate_structures",
        description="Locate specific structures in an unlabeled diagram using Gemini Vision. Fast path for finding known structures without annotation detection.",
        parameters={
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the image"
                },
                "image_base64": {
                    "type": "string",
                    "description": "Base64-encoded image data"
                },
                "structures_to_find": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of structure names to locate"
                }
            },
            "required": ["structures_to_find"]
        },
        function=locate_structures_impl
    )

    logger.info("Vision tools registered")
