"""
Claude-based Diagram Processing Service

Uses Anthropic's Claude API for precise zone detection on diagrams.
Claude has excellent vision capabilities for identifying parts and locations.

Requires: ANTHROPIC_API_KEY in environment
"""

import asyncio
import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("gamed_ai.services.claude_diagram")

# Telemetry storage
TELEMETRY_DIR = Path("pipeline_outputs/claude_telemetry")
TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ClaudeCallMetrics:
    """Metrics for a single Claude API call."""
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
        }


class ClaudeDiagramService:
    """Service for diagram analysis using Anthropic Claude API."""

    MODEL = "claude-sonnet-4-20250514"  # Latest Claude with vision

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self._client = None
        self._call_history: List[ClaudeCallMetrics] = []

    def _get_client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("Anthropic client initialized successfully")
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    def _generate_call_id(self, task: str) -> str:
        """Generate unique call ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{task}_{timestamp}"

    def _save_telemetry(self, metrics: ClaudeCallMetrics):
        """Save telemetry to file."""
        self._call_history.append(metrics)

        telemetry_file = TELEMETRY_DIR / f"{metrics.call_id}.json"
        with open(telemetry_file, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)

        logger.info(
            f"Claude API Call: {metrics.task} | Model: {metrics.model} | "
            f"Duration: {metrics.duration_ms}ms | Tokens: {metrics.input_tokens}+{metrics.output_tokens}"
        )

    def _encode_image_base64(self, image_path: str) -> tuple[str, str]:
        """Encode image to base64."""
        path = Path(image_path)
        suffix = path.suffix.lower()

        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/jpeg")

        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        return image_data, media_type

    async def detect_zones(
        self,
        image_path: str,
        canonical_labels: List[str],
    ) -> Dict[str, Any]:
        """
        Detect zones for each canonical label using Claude's vision.

        Args:
            image_path: Path to the diagram image
            canonical_labels: List of part names to locate

        Returns:
            Dict with zones list containing rich metadata
        """
        call_id = self._generate_call_id("detect_zones")
        metrics = ClaudeCallMetrics(
            call_id=call_id,
            model=self.MODEL,
            task="detect_zones",
            started_at=datetime.now(),
        )

        labels_str = ", ".join(canonical_labels)

        prompt = f"""Analyze this flower anatomy diagram carefully.

TASK: Locate these flower parts with PRECISE coordinates:
{labels_str}

For EACH visible part, provide:
- label: The part name exactly as listed
- x: Center X coordinate (0-100%, where 0=left edge, 100=right edge)
- y: Center Y coordinate (0-100%, where 0=top edge, 100=bottom edge)
- width: Width of clickable area as percentage
- height: Height of clickable area as percentage
- color: Primary color of this part
- hint: Educational hint about this part's function (1 sentence)
- difficulty: 1=easy to find, 2=moderate, 3=tricky

IMPORTANT:
- Be VERY precise with x,y coordinates - point to the exact CENTER of each structure
- These coordinates will be used for click targets in an educational game
- Examine the image carefully before responding

OUTPUT FORMAT (JSON only, no markdown):
{{
  "zones": [
    {{"label": "petal", "x": 50.0, "y": 30.0, "width": 30.0, "height": 20.0, "color": "purple", "hint": "Colorful parts that attract pollinators", "difficulty": 1}},
    ...
  ],
  "image_description": "Brief description of the diagram"
}}"""

        try:
            client = self._get_client()

            # Encode image
            image_data, media_type = self._encode_image_base64(image_path)

            start_time = time.time()

            # Call Claude
            message = client.messages.create(
                model=self.MODEL,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            }
                        ],
                    }
                ],
            )

            metrics.duration_ms = int((time.time() - start_time) * 1000)
            metrics.completed_at = datetime.now()
            metrics.input_tokens = message.usage.input_tokens
            metrics.output_tokens = message.usage.output_tokens

            # Extract response
            response_text = message.content[0].text

            # Parse JSON
            try:
                # Clean up response
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```"):
                    lines = cleaned_text.split("\n")
                    cleaned_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

                result = json.loads(cleaned_text)

                # Validate zones
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
                            "hint": zone.get("hint", ""),
                            "difficulty": int(zone.get("difficulty", 2)),
                            "confidence": 0.95,
                            "source": "claude_vision",
                        })

                metrics.success = True
                self._save_telemetry(metrics)

                # Save zones
                output_dir = Path("pipeline_outputs/claude_outputs")
                output_dir.mkdir(parents=True, exist_ok=True)
                zones_file = output_dir / f"zones_{call_id}.json"

                output_data = {
                    "zones": validated_zones,
                    "image_description": result.get("image_description", ""),
                    "call_id": call_id,
                    "duration_ms": metrics.duration_ms,
                    "tokens": {"input": metrics.input_tokens, "output": metrics.output_tokens},
                }

                with open(zones_file, "w") as f:
                    json.dump(output_data, f, indent=2)

                return {
                    "success": True,
                    "zones": validated_zones,
                    "image_description": result.get("image_description", ""),
                    "zones_file": str(zones_file),
                    "call_id": call_id,
                    "duration_ms": metrics.duration_ms,
                    "tokens": {"input": metrics.input_tokens, "output": metrics.output_tokens},
                }

            except json.JSONDecodeError as e:
                metrics.error = f"JSON parse error: {e}"
                metrics.success = False
                self._save_telemetry(metrics)

                return {
                    "success": False,
                    "error": f"Failed to parse JSON: {e}",
                    "raw_response": response_text,
                    "call_id": call_id,
                }

        except Exception as e:
            metrics.completed_at = datetime.now()
            metrics.error = str(e)
            metrics.success = False
            self._save_telemetry(metrics)

            logger.error(f"Claude detect_zones failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "call_id": call_id,
            }


# Singleton
_service: Optional[ClaudeDiagramService] = None


def get_claude_service() -> ClaudeDiagramService:
    """Get singleton Claude service instance."""
    global _service
    if _service is None:
        _service = ClaudeDiagramService()
    return _service
