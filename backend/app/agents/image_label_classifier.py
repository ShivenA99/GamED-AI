"""
Image Label Classifier Agent

Classifies whether a diagram is labeled or unlabeled using a two-stage approach:
1. Fast heuristic using EasyOCR text detection
2. VLM-based classification for ambiguous cases

This enables the pipeline to route unlabeled diagrams directly to structure
location, skipping the text removal pipeline.

Inputs: diagram_image
Outputs: image_classification
"""

import base64
import io
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.image_label_classifier")

# Qwen VL prompt for classifying labeled/unlabeled diagrams
CLASSIFY_PROMPT = """Analyze this educational/scientific diagram.

Determine if this diagram has TEXT LABELS on it that identify parts or components.

A LABELED diagram has:
- Text annotations pointing to or near diagram parts
- Labels with arrows/lines connecting to structures
- Numbered annotations with a legend
- Part names written on or next to the diagram

An UNLABELED diagram has:
- Clean visual representation without text
- May show structures but no identifying labels
- Blank worksheet or quiz-style diagram
- No text overlays on the image

Respond with ONLY this JSON format:
{
  "is_labeled": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "text_labels_found": ["list", "of", "labels"] or []
}

Return ONLY valid JSON, no other text."""


def detect_text_fast(image_path: str, min_confidence: float = 0.6) -> List[Dict[str, Any]]:
    """
    Fast text detection using EasyOCR.

    Args:
        image_path: Path to the image file
        min_confidence: Minimum confidence threshold for text detection

    Returns:
        List of detected text regions with text and confidence
    """
    try:
        import easyocr
    except ImportError:
        logger.warning("EasyOCR not available, returning empty result")
        return []

    try:
        # Initialize reader (cached after first use)
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)

        # Read and detect text
        results = reader.readtext(image_path)

        # Filter by confidence
        text_regions = []
        for bbox, text, confidence in results:
            if confidence >= min_confidence and len(text.strip()) >= 2:
                # Filter out very short or numeric-only text
                if not text.strip().isdigit():
                    text_regions.append({
                        "text": text.strip(),
                        "confidence": confidence,
                        "bbox": bbox
                    })

        logger.debug(f"EasyOCR detected {len(text_regions)} text regions (min_conf={min_confidence})")
        return text_regions

    except Exception as e:
        logger.warning(f"EasyOCR text detection failed: {e}")
        return []


async def qwen_classify_labeled(image_path: str) -> Dict[str, Any]:
    """
    Use Qwen VL to classify if diagram is labeled or unlabeled.

    Args:
        image_path: Path to the diagram image

    Returns:
        Classification result dict
    """
    import httpx

    qwen_model = os.getenv("QWEN_VL_MODEL", "qwen2.5vl:7b")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    timeout = float(os.getenv("QWEN_VL_TIMEOUT", "60.0"))

    # Encode image
    img = Image.open(image_path)
    max_size = 1024
    if img.width > max_size or img.height > max_size:
        if img.width > img.height:
            new_size = (max_size, int(img.height * max_size / img.width))
        else:
            new_size = (int(img.width * max_size / img.height), max_size)
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    if img.mode != "RGB":
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    image_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": qwen_model,
                    "prompt": CLASSIFY_PROMPT,
                    "images": [image_data],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_ctx": 4096}
                }
            )
            response.raise_for_status()
            text = response.json().get("response", "")

            # Parse JSON response
            cleaned = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
            cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

            result = json.loads(cleaned)

            return {
                "is_labeled": result.get("is_labeled", True),
                "confidence": result.get("confidence", 0.8),
                "text_count": len(result.get("text_labels_found", [])),
                "text_labels_found": result.get("text_labels_found", []),
                "reasoning": result.get("reasoning", ""),
                "method": "qwen_vl"
            }

    except Exception as e:
        logger.warning(f"Qwen VL classification failed: {e}")
        # Default to labeled (safer assumption)
        return {
            "is_labeled": True,
            "confidence": 0.5,
            "text_count": 0,
            "method": "fallback_default",
            "error": str(e)
        }


async def _ensure_image_downloaded(state: dict, diagram_image: dict) -> str:
    """
    Ensure the diagram image is downloaded and return the local path.

    Downloads the image if local_path is not set or file doesn't exist.
    """
    import httpx

    # Try local_path first
    local_path = diagram_image.get("local_path")
    if local_path and Path(local_path).exists():
        return local_path

    # Try constructing path from question_id (matching image_label_remover behavior)
    question_id = state.get("question_id", "unknown")
    base_dir = Path(__file__).parent.parent.parent / "pipeline_outputs" / "assets" / question_id
    constructed_path = base_dir / "diagram.jpg"

    if constructed_path.exists():
        logger.info(f"Found existing image at: {constructed_path}")
        return str(constructed_path)

    # Download from image_url
    image_url = diagram_image.get("image_url")
    if not image_url:
        logger.error("No image_url available to download")
        return None

    logger.info(f"Downloading image from: {image_url[:80]}...")

    try:
        base_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()

            # Determine file extension from content type or URL
            content_type = response.headers.get("content-type", "")
            if "png" in content_type or image_url.lower().endswith(".png"):
                ext = ".png"
            elif "gif" in content_type or image_url.lower().endswith(".gif"):
                ext = ".gif"
            else:
                ext = ".jpg"

            output_path = base_dir / f"diagram{ext}"
            output_path.write_bytes(response.content)

            logger.info(f"Downloaded image to: {output_path}")
            return str(output_path)

    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return None


async def image_label_classifier(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Classify if a diagram is labeled or unlabeled.

    Uses a two-stage approach:
    1. Fast EasyOCR heuristic for clear cases
    2. Qwen VL for ambiguous cases

    Inputs: diagram_image
    Outputs: image_classification
    """
    start_time = time.time()
    logger.info("=== IMAGE LABEL CLASSIFIER STARTING ===")

    diagram_image = state.get("diagram_image", {})

    # Ensure image is downloaded
    image_path = await _ensure_image_downloaded(state, diagram_image)

    if not image_path or not Path(image_path).exists():
        logger.error(f"No valid image path: {image_path}")
        return {
            "image_classification": {
                "is_labeled": True,  # Default to labeled (safer)
                "confidence": 0.0,
                "text_count": 0,
                "method": "error",
                "error": "No valid image path"
            }
        }

    logger.info(f"Classifying image: {image_path}")

    # Stage 1: Fast EasyOCR heuristic
    text_regions = detect_text_fast(image_path, min_confidence=0.6)
    text_count = len(text_regions)

    logger.info(f"EasyOCR detected {text_count} text regions")

    # Clear cases - no VLM needed
    if text_count == 0:
        classification = {
            "is_labeled": False,
            "confidence": 0.95,
            "text_count": 0,
            "text_labels_found": [],
            "method": "easyocr_heuristic"
        }
        logger.info("Classified as UNLABELED (no text detected)")

    elif text_count >= 4:
        # Multiple text regions strongly indicates labeled diagram
        labels = [r["text"] for r in text_regions[:10]]
        classification = {
            "is_labeled": True,
            "confidence": 0.9,
            "text_count": text_count,
            "text_labels_found": labels,
            "method": "easyocr_heuristic"
        }
        logger.info(f"Classified as LABELED ({text_count} text regions)")

    else:
        # Ambiguous case (1-3 text regions) - use Qwen VL
        logger.info(f"Ambiguous case ({text_count} text regions), using Qwen VL")
        classification = await qwen_classify_labeled(image_path)

        # Override text count with our EasyOCR count
        classification["text_count"] = text_count

        if classification.get("is_labeled"):
            logger.info(f"Qwen VL classified as LABELED: {classification.get('reasoning', '')[:100]}")
        else:
            logger.info(f"Qwen VL classified as UNLABELED: {classification.get('reasoning', '')[:100]}")

    # Track metrics
    latency_ms = int((time.time() - start_time) * 1000)
    classification["latency_ms"] = latency_ms

    if ctx:
        if classification.get("method") == "qwen_vl":
            ctx.set_llm_metrics(
                model="qwen2.5vl:7b",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms
            )

    logger.info(f"Classification complete: is_labeled={classification['is_labeled']}, "
                f"confidence={classification['confidence']:.2f}, method={classification['method']}")

    return {
        "image_classification": classification
    }
