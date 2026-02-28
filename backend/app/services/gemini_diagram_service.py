"""
Gemini-based Diagram Processing Service

Uses Google's Gemini API for:
1. Diagram Cleaning - Remove text labels and leader lines using Nano Banana (Gemini 2.5 Flash Image)
2. Zone Detection - Identify exact positions of diagram parts using Gemini 3 Flash vision

Requires: GOOGLE_API_KEY in environment
"""

import asyncio
import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
import io

logger = logging.getLogger("gamed_ai.services.gemini_diagram")

# Telemetry storage
TELEMETRY_DIR = Path("pipeline_outputs/gemini_telemetry")
TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class GeminiCallMetrics:
    """Metrics for a single Gemini API call."""
    call_id: str
    model: str
    task: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    success: bool = False
    error: Optional[str] = None
    prompt_preview: str = ""
    response_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "model": self.model,
            "task": self.task,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "success": self.success,
            "error": self.error,
            "prompt_preview": self.prompt_preview[:200] if self.prompt_preview else "",
            "response_preview": self.response_preview[:500] if self.response_preview else "",
        }


class GeminiDiagramService:
    """Service for diagram processing using Google Gemini API."""

    # Model configurations
    # For image editing/cleaning - Nano Banana Pro for best quality
    CLEANING_MODEL = "nano-banana-pro-preview"
    # For vision/zone detection - Gemini 3 Flash for best accuracy
    VISION_MODEL = "gemini-3-flash-preview"

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self._client = None
        self._call_history: List[GeminiCallMetrics] = []

    def _get_client(self):
        """Lazy-load the Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Gemini client initialized successfully")
            except ImportError:
                raise ImportError("google-genai package not installed. Run: pip install google-genai")
        return self._client

    def _generate_call_id(self, task: str) -> str:
        """Generate unique call ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{task}_{timestamp}"

    def _save_telemetry(self, metrics: GeminiCallMetrics):
        """Save telemetry to file."""
        self._call_history.append(metrics)

        # Save to file
        telemetry_file = TELEMETRY_DIR / f"{metrics.call_id}.json"
        with open(telemetry_file, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)

        logger.info(
            f"Gemini API Call: {metrics.task} | Model: {metrics.model} | "
            f"Duration: {metrics.duration_ms}ms | Success: {metrics.success}"
        )

    def _encode_image_base64(self, image_path: str) -> Tuple[str, str]:
        """Encode image to base64 and determine MIME type."""
        path = Path(image_path)
        suffix = path.suffix.lower()

        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        return image_data, mime_type

    async def clean_diagram(
        self,
        image_path: str,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Clean a diagram by removing text labels and leader lines.

        Uses Gemini 2.5 Flash Image (Nano Banana) for intelligent inpainting.

        Args:
            image_path: Path to the input diagram image
            output_path: Optional path to save cleaned image

        Returns:
            Dict with cleaned_image_path, success, and metrics
        """
        call_id = self._generate_call_id("clean_diagram")
        metrics = GeminiCallMetrics(
            call_id=call_id,
            model=self.CLEANING_MODEL,
            task="clean_diagram",
            started_at=datetime.now(),
        )

        prompt = """Edit this image to extract ONLY the flower illustration.

REMOVE COMPLETELY:
- ALL text (title, labels, fun facts, everything)
- ALL lines and arrows pointing to parts
- The bee character
- The speech bubble
- Any logos or watermarks
- The bracket annotations on the sides

KEEP ONLY:
- The flower cross-section illustration itself
- All flower parts: petals (purple), stamens (yellow), pistil (orange), sepals (green), stem
- The exact colors and shapes of the flower anatomy

OUTPUT:
- Just the flower on a pure white background
- No text, no lines, no annotations, no other elements
- Clean isolated flower illustration only

Generate the cleaned flower image."""

        metrics.prompt_preview = prompt

        try:
            client = self._get_client()
            from google.genai import types

            # Load image
            img = Image.open(image_path)

            start_time = time.time()

            # Call Gemini with image editing
            response = client.models.generate_content(
                model=self.CLEANING_MODEL,
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    response_modalities=["image", "text"],
                )
            )

            metrics.duration_ms = int((time.time() - start_time) * 1000)
            metrics.completed_at = datetime.now()

            # Extract the generated image
            cleaned_image = None
            response_text = ""

            for part in response.parts:
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    # Got image data
                    image_data = part.inline_data.data
                    cleaned_image = Image.open(io.BytesIO(image_data))
                elif hasattr(part, 'text') and part.text:
                    response_text += part.text

            metrics.response_preview = response_text or "[Image generated]"

            if cleaned_image:
                # Save cleaned image
                if output_path is None:
                    output_dir = Path("pipeline_outputs/gemini_outputs")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = str(output_dir / f"cleaned_{call_id}.png")

                cleaned_image.save(output_path)

                metrics.success = True
                self._save_telemetry(metrics)

                return {
                    "success": True,
                    "cleaned_image_path": output_path,
                    "call_id": call_id,
                    "duration_ms": metrics.duration_ms,
                    "response_text": response_text,
                }
            else:
                metrics.error = "No image in response"
                metrics.success = False
                self._save_telemetry(metrics)

                return {
                    "success": False,
                    "error": "No image generated in response",
                    "response_text": response_text,
                    "call_id": call_id,
                }

        except Exception as e:
            metrics.completed_at = datetime.now()
            metrics.error = str(e)
            metrics.success = False
            self._save_telemetry(metrics)

            logger.error(f"Gemini clean_diagram failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "call_id": call_id,
            }

    async def detect_zones(
        self,
        image_path: str,
        canonical_labels: List[str],
    ) -> Dict[str, Any]:
        """
        Detect zones (positions) for each canonical label in the diagram.

        Uses Gemini 3 Flash vision to identify exact positions of diagram parts.

        Args:
            image_path: Path to the (preferably cleaned) diagram image
            canonical_labels: List of part names to locate (e.g., ["petal", "stamen", "pistil"])

        Returns:
            Dict with zones list, each containing label, x, y (as percentages), confidence
        """
        call_id = self._generate_call_id("detect_zones")
        metrics = GeminiCallMetrics(
            call_id=call_id,
            model=self.VISION_MODEL,
            task="detect_zones",
            started_at=datetime.now(),
        )

        labels_str = ", ".join(canonical_labels)

        prompt = f"""Analyze this flower anatomy diagram for an interactive educational game.

TASK: Locate these flower parts with PRECISE coordinates and detailed information:
{labels_str}

For EACH visible part, provide:
1. label: The part name (exactly as listed)
2. x: Center X coordinate (0-100%, where 0=left, 100=right)
3. y: Center Y coordinate (0-100%, where 0=top, 100=bottom)
4. width: Approximate width of the part as percentage of image
5. height: Approximate height of the part as percentage of image
6. color: Primary color of this part in the diagram
7. shape: Shape description (e.g., "elongated oval", "rounded triangle")
8. hint: A short educational hint about this part's function
9. difficulty: How easy to identify (1=obvious, 2=moderate, 3=tricky)

PRECISION REQUIREMENTS:
- Coordinates must point to the EXACT visual center of each structure
- This data will be used for click-target zones in a game
- Be as accurate as possible - students will click on these locations

OUTPUT FORMAT (JSON only, no markdown code blocks):
{{
  "zones": [
    {{
      "label": "petal",
      "x": 65.0,
      "y": 32.0,
      "width": 15.0,
      "height": 20.0,
      "color": "purple",
      "shape": "curved elongated",
      "hint": "Colorful parts that attract pollinators",
      "difficulty": 1
    }}
  ],
  "image_description": "Description of the diagram",
  "educational_context": "What students learn from this diagram",
  "parts_not_found": []
}}"""

        metrics.prompt_preview = prompt

        try:
            client = self._get_client()
            from google.genai import types

            # Load and encode image
            img = Image.open(image_path)

            start_time = time.time()

            # Call Gemini vision
            response = client.models.generate_content(
                model=self.VISION_MODEL,
                contents=[prompt, img],
            )

            metrics.duration_ms = int((time.time() - start_time) * 1000)
            metrics.completed_at = datetime.now()

            # Extract response text
            response_text = response.text if hasattr(response, 'text') else str(response)
            metrics.response_preview = response_text

            # Parse JSON from response
            try:
                # Clean up response (remove markdown code blocks if present)
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```"):
                    # Remove markdown code fence
                    lines = cleaned_text.split("\n")
                    cleaned_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

                result = json.loads(cleaned_text)

                # Validate and normalize zones
                zones = result.get("zones", [])
                validated_zones = []

                for zone in zones:
                    if all(k in zone for k in ["label", "x", "y"]):
                        validated_zones.append({
                            "id": f"zone_{zone['label'].lower().replace(' ', '_')}",
                            "label": zone["label"],
                            "x": max(0, min(100, float(zone["x"]))),
                            "y": max(0, min(100, float(zone["y"]))),
                            "width": float(zone.get("width", 10)),
                            "height": float(zone.get("height", 10)),
                            "color": zone.get("color", ""),
                            "shape": zone.get("shape", ""),
                            "hint": zone.get("hint", ""),
                            "difficulty": int(zone.get("difficulty", 2)),
                            "confidence": float(zone.get("confidence", 0.9)),
                            "source": "gemini_vision",
                        })

                metrics.success = True
                self._save_telemetry(metrics)

                # Save zones to file
                output_dir = Path("pipeline_outputs/gemini_outputs")
                output_dir.mkdir(parents=True, exist_ok=True)
                zones_file = output_dir / f"zones_{call_id}.json"

                output_data = {
                    "zones": validated_zones,
                    "image_description": result.get("image_description", ""),
                    "educational_context": result.get("educational_context", ""),
                    "parts_not_found": result.get("parts_not_found", []),
                    "call_id": call_id,
                    "duration_ms": metrics.duration_ms,
                    "canonical_labels": canonical_labels,
                }

                with open(zones_file, "w") as f:
                    json.dump(output_data, f, indent=2)

                return {
                    "success": True,
                    "zones": validated_zones,
                    "image_description": result.get("image_description", ""),
                    "parts_not_found": result.get("parts_not_found", []),
                    "zones_file": str(zones_file),
                    "call_id": call_id,
                    "duration_ms": metrics.duration_ms,
                }

            except json.JSONDecodeError as e:
                metrics.error = f"JSON parse error: {e}"
                metrics.success = False
                self._save_telemetry(metrics)

                return {
                    "success": False,
                    "error": f"Failed to parse response as JSON: {e}",
                    "raw_response": response_text,
                    "call_id": call_id,
                }

        except Exception as e:
            metrics.completed_at = datetime.now()
            metrics.error = str(e)
            metrics.success = False
            self._save_telemetry(metrics)

            logger.error(f"Gemini detect_zones failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "call_id": call_id,
            }

    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of all API calls."""
        return [m.to_dict() for m in self._call_history]

    def get_total_cost_estimate(self) -> float:
        """Estimate total cost based on token usage (approximate)."""
        # Approximate pricing: $0.075 per 1M input tokens, $0.30 per 1M output tokens
        total_input = sum(m.input_tokens for m in self._call_history)
        total_output = sum(m.output_tokens for m in self._call_history)

        input_cost = (total_input / 1_000_000) * 0.075
        output_cost = (total_output / 1_000_000) * 0.30

        return input_cost + output_cost


# Singleton instance
_service: Optional[GeminiDiagramService] = None


def get_gemini_service() -> GeminiDiagramService:
    """Get the singleton Gemini service instance."""
    global _service
    if _service is None:
        _service = GeminiDiagramService()
    return _service
