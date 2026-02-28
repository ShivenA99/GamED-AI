"""
Direct Structure Locator Agent

For unlabeled diagrams, uses Qwen VL to directly locate structures without
needing to go through the text removal pipeline.

This is the "fast path" for clean diagrams that don't have text labels.
The VLM is asked to find each canonical structure in the diagram and
provide its location coordinates.

Inputs: diagram_image, domain_knowledge, image_classification
Outputs: diagram_zones, diagram_labels, zone_detection_method, cleaned_image_path
"""

import base64
import io
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.direct_structure_locator")


# Prompt for locating a specific structure in an unlabeled diagram
LOCATE_STRUCTURE_PROMPT = """Look at this educational/scientific diagram.

This is an UNLABELED diagram (no text labels on the image). Your task is to locate a specific anatomical/scientific structure.

Find the EXACT location of "{label}" in this diagram.

If you find "{label}", respond with:
{{
  "found": true,
  "label": "{label}",
  "center": [x, y],
  "bbox": [x1, y1, x2, y2],
  "confidence": 0.0-1.0
}}

If you CANNOT find "{label}" in the diagram, respond:
{{
  "found": false,
  "label": "{label}",
  "reason": "explanation"
}}

IMPORTANT:
- Coordinates use 0-1000 normalized scale (0,0 is top-left, 1000,1000 is bottom-right)
- The "center" should be the center point of the structure
- The "bbox" should tightly bound the structure: [left, top, right, bottom]
- Look for the actual anatomical/scientific structure by its shape and position
- Since there are no text labels, rely on visual features and biological knowledge
- Be precise - the center point should be INSIDE the structure

Return ONLY valid JSON, no other text."""


class DirectStructureLocator:
    """
    Locates structures directly in unlabeled diagrams using Qwen VL.
    """

    def __init__(self):
        self.qwen_model = os.getenv("QWEN_VL_MODEL", "qwen2.5vl:7b")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = float(os.getenv("QWEN_VL_TIMEOUT", "180.0"))
        self._qwen_available = None

    async def is_qwen_available(self) -> bool:
        """Check if Qwen VL is available."""
        if self._qwen_available is not None:
            return self._qwen_available

        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    models = [m.get("name", "") for m in response.json().get("models", [])]
                    self._qwen_available = any(self.qwen_model in m for m in models)
                    return self._qwen_available
        except Exception as e:
            logger.warning(f"Could not check Qwen VL availability: {e}")
            self._qwen_available = False
        return False

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        img = Image.open(image_path)

        # Resize if too large
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
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    async def _locate_structure(self, label: str, image_data: str) -> Dict[str, Any]:
        """
        Use Qwen VL to locate a specific structure in the diagram.

        Args:
            label: The structure name to find
            image_data: Base64 encoded image

        Returns:
            Location result dict
        """
        import httpx

        prompt = LOCATE_STRUCTURE_PROMPT.format(label=label)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.qwen_model,
                        "prompt": prompt,
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

                return json.loads(cleaned)

            except Exception as e:
                logger.warning(f"Failed to locate '{label}': {e}")
                return {"found": False, "label": label, "reason": str(e)}

    async def locate_all_structures(
        self,
        image_path: str,
        canonical_labels: List[str]
    ) -> Dict[str, Any]:
        """
        Locate all canonical structures in an unlabeled diagram.

        Args:
            image_path: Path to the diagram image
            canonical_labels: List of structure names to find

        Returns:
            Dict with zones, labels, and method
        """
        start_time = time.time()

        # Check Qwen availability
        if not await self.is_qwen_available():
            logger.warning("Qwen VL not available for direct structure location")
            return {
                "zones": [],
                "labels": [],
                "method": "error",
                "error": "Qwen VL not available"
            }

        # Load image dimensions
        image = cv2.imread(image_path)
        if image is None:
            return {
                "zones": [],
                "labels": [],
                "method": "error",
                "error": f"Could not load image: {image_path}"
            }

        h, w = image.shape[:2]

        # Encode image once
        image_data = self._encode_image(image_path)

        zones = []
        found_labels = []
        missing_labels = []

        # Locate each structure
        for label in canonical_labels:
            logger.debug(f"Locating structure: {label}")

            result = await self._locate_structure(label, image_data)

            if result.get("found", False):
                center = result.get("center", [500, 500])
                bbox = result.get("bbox", [0, 0, 1000, 1000])
                confidence = result.get("confidence", 0.8)

                # Convert from 0-1000 scale to percentage and pixels
                x_pct = center[0] / 10  # 0-1000 -> 0-100%
                y_pct = center[1] / 10

                # Calculate bbox in pixels
                bbox_x = int(bbox[0] * w / 1000)
                bbox_y = int(bbox[1] * h / 1000)
                bbox_width = int((bbox[2] - bbox[0]) * w / 1000)
                bbox_height = int((bbox[3] - bbox[1]) * h / 1000)

                # Calculate radius (max 50)
                radius = min(min(bbox_width, bbox_height) / 2, 50)

                zone = {
                    "id": f"zone_{label.lower().replace(' ', '_')}",
                    "label": label,
                    "x": x_pct,
                    "y": y_pct,
                    "radius": radius,
                    "bbox": {
                        "x": bbox_x,
                        "y": bbox_y,
                        "width": bbox_width,
                        "height": bbox_height
                    },
                    "confidence": confidence,
                    "source": "direct_vlm"
                }
                zones.append(zone)
                found_labels.append(label)

                logger.debug(f"Found '{label}' at ({x_pct:.1f}%, {y_pct:.1f}%) with confidence {confidence:.2f}")
            else:
                missing_labels.append(label)
                logger.warning(f"Could not find '{label}': {result.get('reason', 'unknown')}")

        # Create fallback zones for missing labels
        if missing_labels:
            logger.info(f"Creating fallback zones for {len(missing_labels)} missing labels")
            fallback_zones = self._create_fallback_zones(missing_labels, w, h)
            zones.extend(fallback_zones)

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "zones": zones,
            "labels": found_labels + missing_labels,
            "method": "direct_vlm",
            "found_count": len(found_labels),
            "missing_count": len(missing_labels),
            "latency_ms": latency_ms
        }

    def _create_fallback_zones(
        self,
        missing_labels: List[str],
        w: int,
        h: int
    ) -> List[Dict]:
        """Create fallback zones for labels that couldn't be located."""
        zones = []
        n = len(missing_labels)

        for i, label in enumerate(missing_labels):
            # Spread fallback zones across the diagram
            x_pct = (i + 0.5) * 100 / max(n, 1)
            y_pct = 50  # Middle of image

            bbox_width = w / max(n, 1)
            bbox_height = h * 0.3

            zones.append({
                "id": f"zone_{label.lower().replace(' ', '_')}",
                "label": label,
                "x": x_pct,
                "y": y_pct,
                "radius": min(min(bbox_width, bbox_height) / 2, 50),
                "bbox": {
                    "x": int(w * i / max(n, 1)),
                    "y": int(h * 0.35),
                    "width": int(bbox_width),
                    "height": int(bbox_height)
                },
                "confidence": 0.3,
                "source": "fallback"
            })

        return zones


async def direct_structure_locator(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Locate structures directly in unlabeled diagrams using Qwen VL.

    This agent is the "fast path" for clean diagrams without text labels.
    It skips the text removal pipeline entirely and goes straight to
    structure location.

    Inputs: diagram_image, domain_knowledge, image_classification
    Outputs: diagram_zones, diagram_labels, zone_detection_method, cleaned_image_path
    """
    logger.info("=== DIRECT STRUCTURE LOCATOR STARTING ===")

    # Verify this is an unlabeled image
    classification = state.get("image_classification", {})
    is_labeled = classification.get("is_labeled", True)

    if is_labeled:
        logger.warning("Image is classified as labeled, should use cleaning pipeline")
        # This shouldn't happen if routing is correct, but handle gracefully
        return {
            "_error": "Image is labeled, should use cleaning pipeline",
            "_skip": True
        }

    # Get image path
    diagram_image = state.get("diagram_image", {})
    image_path = diagram_image.get("local_path")

    if not image_path or not Path(image_path).exists():
        logger.error(f"No valid image path: {image_path}")
        return {
            "diagram_zones": [],
            "diagram_labels": [],
            "zone_detection_method": "error",
            "_error": "No valid image path"
        }

    logger.info(f"Processing unlabeled image: {image_path}")
    logger.info(f"Classification confidence: {classification.get('confidence', 0):.2f}")

    # Get canonical labels
    domain_knowledge = state.get("domain_knowledge", {})
    game_plan = state.get("game_plan", {})

    canonical_labels = (
        domain_knowledge.get("canonical_labels", []) or
        game_plan.get("required_labels", []) or
        []
    )

    if not canonical_labels:
        logger.warning("No canonical labels provided")
        return {
            "diagram_zones": [],
            "diagram_labels": [],
            "zone_detection_method": "no_labels",
            "cleaned_image_path": image_path,
            "removed_labels": [],
            "_warning": "No canonical labels provided"
        }

    logger.info(f"Locating {len(canonical_labels)} structures: {canonical_labels}")

    # Locate structures
    locator = DirectStructureLocator()
    result = await locator.locate_all_structures(image_path, canonical_labels)

    zones = result.get("zones", [])
    method = result.get("method", "unknown")

    # Track metrics
    if ctx:
        ctx.set_llm_metrics(
            model="qwen2.5vl:7b",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=result.get("latency_ms", 0)
        )

        if result.get("missing_count", 0) > 0:
            ctx.set_fallback_used(f"Missing {result['missing_count']} labels")

    # Format output
    diagram_zones = []
    diagram_labels = []

    for zone in zones:
        diagram_zones.append({
            "id": zone["id"],
            "label": zone["label"],
            "x": zone["x"],
            "y": zone["y"],
            "radius": zone.get("radius", 20),
            "bbox": zone.get("bbox"),
            "confidence": zone.get("confidence", 0.8),
            "source": zone.get("source", method)
        })

        if zone["label"]:
            diagram_labels.append({
                "id": zone["id"],
                "text": zone["label"]
            })

    logger.info(f"Direct structure location complete: {len(diagram_zones)} zones, "
                f"found={result.get('found_count', 0)}, missing={result.get('missing_count', 0)}")

    return {
        "diagram_zones": diagram_zones,
        "diagram_labels": diagram_labels,
        "zone_detection_method": method,
        "cleaned_image_path": image_path,  # No cleaning needed - use original
        "removed_labels": [],  # No labels were removed
        "_used_fallback": result.get("missing_count", 0) > 0,
        "_fallback_reason": f"Missing {result.get('missing_count', 0)} labels" if result.get("missing_count", 0) > 0 else None
    }
