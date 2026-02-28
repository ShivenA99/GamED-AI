"""
Qwen VLM Annotation Detector Agent

Uses Qwen2.5-VL to detect ONLY annotation elements in educational diagrams:
- Text labels (the words/phrases that label diagram parts)
- Leader lines (the thin lines connecting labels to diagram parts)
- Arrows/pointers (if any)

CRITICAL: This agent explicitly distinguishes annotation elements from
diagram structure. Hough Transform detects ALL lines including diagram
boundaries, organelle outlines, etc. This agent uses semantic understanding
to detect ONLY the annotation elements that should be removed.

Based on research:
- Qwen2.5-VL coordinates are in [0, 1000) normalized range
- Format: (x1, y1), (x2, y2) for top-left and bottom-right
- Per-label detection is more accurate than bulk detection

Inputs: diagram_image, template_selection
Outputs: annotation_elements, detection_mask_path, text_labels_found
"""

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.qwen_annotation_detector")


# NEW: VLM-based detection prompt with canonical labels context
VLM_SEMANTIC_DETECTION_PROMPT = """You are analyzing an educational diagram to find ALL text labels and their positions.

EXPECTED LABELS TO FIND: {canonical_labels}

For this diagram, carefully scan for each expected label and report its location.

OUTPUT FORMAT (JSON):
{{
  "detected_labels": [
    {{"text": "Label Name", "bbox_percent": [x1, y1, x2, y2], "leader_endpoint": [x, y], "confidence": 0.95}},
    ...
  ],
  "missed_labels": ["any expected labels not found"],
  "additional_text": ["any other text found not in expected list"]
}}

COORDINATE SYSTEM:
- All values are percentages (0-100) of image dimensions
- (0,0) = top-left, (100,100) = bottom-right
- bbox_percent: [left, top, right, bottom] of text bounding box
- leader_endpoint: [x, y] where the leader line points to in the diagram (if visible)

SCAN STRATEGY:
1. Look at LEFT edge for labels (usually pointing right into diagram)
2. Look at RIGHT edge for labels (usually pointing left into diagram)
3. Look at TOP and BOTTOM for any additional labels
4. For each label, trace any visible line to find where it points

Return ONLY valid JSON."""


# Prompt for detecting ALL annotation elements (text + leader lines + arrows)
ANNOTATION_DETECTION_PROMPT = """Analyze this educational/scientific diagram image CAREFULLY.

Your task: Identify ALL text labels AND their leader lines visible in this diagram.

LOOK FOR TEXT ON BOTH SIDES OF THE DIAGRAM:
- Labels on the LEFT side (e.g., Pistil, Stigma, Style, Ovary)
- Labels on the RIGHT side (e.g., Stamen, Anther, Filament, Petal, Sepal)
- Labels at the BOTTOM (e.g., Receptacle, Peduncle)

FOR EACH TEXT LABEL:
- Find the exact text content
- Find its bounding box position (coordinates in 0-1000 scale where 1000 = full image width/height)
- Find the leader line connecting it to the diagram (if any)

COORDINATE SYSTEM:
- 0-1000 normalized scale
- (0,0) = top-left corner of image
- (1000,1000) = bottom-right corner of image
- Example: Text at image center would be around (500, 500)
- Example: Text on the far right would be around (800-950, y)
- Example: Text on the far left would be around (0-150, y)

DO NOT INCLUDE:
- Lines that are part of the flower/diagram structure (petals, stems, etc.)
- Only include thin pointer/leader lines from text to diagram

OUTPUT FORMAT (JSON only):
{
  "annotations": [
    {"type": "text", "content": "Pistil", "bbox": [10, 100, 80, 140]},
    {"type": "line", "bbox": [80, 110, 200, 130], "start": [80, 120], "end": [200, 120], "connects_to": "Pistil"},
    {"type": "text", "content": "Stamen", "bbox": [850, 50, 950, 90]},
    {"type": "line", "bbox": [750, 60, 850, 80], "start": [850, 70], "end": [750, 70], "connects_to": "Stamen"}
  ],
  "total_text_labels": 11,
  "total_leader_lines": 11
}

CRITICAL:
- Scan the ENTIRE image for text - left side, right side, top, bottom
- Each text should have DIFFERENT coordinates reflecting its actual position
- Leader line "start" is near the text, "end" is where it points to the diagram

Return ONLY valid JSON, no markdown code blocks, no explanations."""


# Prompt for detecting leader lines for a specific text label
LEADER_LINE_PROMPT = """Look at this educational diagram.

There is a text label "{label}" at position [{x1}, {y1}, {x2}, {y2}] (0-1000 scale).

Find the leader line (if any) that connects this text label to a diagram part.

A leader line is:
- A thin straight line extending from the text label toward the diagram
- Used to point from the text to what it labels
- NOT a diagram structure line (not cell boundaries, not organelle outlines)

If you find a leader line for this text, respond:
{{
  "found": true,
  "label": "{label}",
  "line": {{
    "start": [x, y],  // Point near/at the text label
    "end": [x, y],    // Point where line reaches the diagram
    "bbox": [x1, y1, x2, y2]  // Bounding box covering the line
  }}
}}

If NO leader line exists for this text, respond:
{{
  "found": false,
  "label": "{label}",
  "reason": "explanation"
}}

Return ONLY JSON, no other text."""


class QwenAnnotationDetector:
    """
    Service for detecting annotation elements using Qwen2.5-VL.

    This provides more accurate detection than Hough Transform because
    it understands the semantic difference between annotation elements
    (text labels, leader lines) and diagram structure.
    """

    def __init__(self):
        self.model = os.getenv("QWEN_VL_MODEL", "qwen2.5vl:7b")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = float(os.getenv("QWEN_VL_TIMEOUT", "300.0"))
        self._available = None

    async def is_available(self) -> bool:
        """Check if Qwen VL model is available via Ollama."""
        if self._available is not None:
            return self._available

        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self._available = any(self.model in m for m in models)
                    if not self._available:
                        logger.warning(f"Qwen VL '{self.model}' not found. Run: ollama pull {self.model}")
                    return self._available
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")
            self._available = False
        return False

    async def detect_annotations(
        self,
        image_path: str,
        use_hybrid: bool = True,
        canonical_labels: List[str] = None
    ) -> Dict[str, Any]:
        """
        Detect all annotation elements in the image.

        Detection strategies (in order of preference):
        1. VLM semantic detection with canonical labels (best for labeled diagrams)
        2. Hybrid EasyOCR + geometric line inference
        3. Pure VLM detection (fallback)

        Args:
            image_path: Path to the diagram image
            use_hybrid: Use hybrid EasyOCR+geometric approach
            canonical_labels: List of expected label texts (improves VLM accuracy)

        Returns:
            Dict with annotations list, counts, and mask_path
        """
        start_time = time.time()

        # Strategy 1: VLM semantic detection with canonical labels (BEST for labeled diagrams)
        if canonical_labels and await self.is_available():
            logger.info(f"Using VLM semantic detection with {len(canonical_labels)} canonical labels")
            result = await self._detect_vlm_semantic(image_path, canonical_labels, start_time)
            if result.get("annotations") and len(result["annotations"]) > 0:
                return result
            logger.warning("VLM semantic detection returned no results, trying hybrid...")

        # Strategy 2: Hybrid EasyOCR + geometric
        if use_hybrid:
            return await self._detect_hybrid(image_path, start_time)

        # Strategy 3: Pure Qwen approach (generic prompt)
        if not await self.is_available():
            logger.warning("Qwen VL not available, cannot detect annotations")
            return {
                "annotations": [],
                "total_text_labels": 0,
                "total_leader_lines": 0,
                "error": "Qwen VL not available"
            }

        # Encode image
        image_data = self._encode_image(image_path)

        # Call Qwen VL
        response = await self._call_ollama(ANNOTATION_DETECTION_PROMPT, image_data)

        # Parse response
        result = self._parse_response(response)

        # Create mask from annotations
        mask_path = None
        if result.get("annotations"):
            mask_path = self._create_annotation_mask(image_path, result["annotations"])
            result["detection_mask_path"] = mask_path

        result["latency_ms"] = int((time.time() - start_time) * 1000)
        result["model"] = self.model

        logger.info(
            f"Qwen VL detected {result.get('total_text_labels', 0)} text labels, "
            f"{result.get('total_leader_lines', 0)} leader lines in {result['latency_ms']}ms"
        )

        return result

    async def _detect_vlm_semantic(
        self,
        image_path: str,
        canonical_labels: List[str],
        start_time: float
    ) -> Dict[str, Any]:
        """
        VLM-based semantic detection using canonical labels for guidance.

        This approach tells the VLM what labels to look for, improving accuracy.
        """
        import cv2

        img = cv2.imread(image_path)
        if img is None:
            return {"annotations": [], "error": "Could not load image"}
        h, w = img.shape[:2]

        # Encode image
        image_data = self._encode_image(image_path)

        # Build prompt with canonical labels
        labels_str = ", ".join(canonical_labels[:15])  # Limit to avoid prompt overflow
        prompt = VLM_SEMANTIC_DETECTION_PROMPT.format(canonical_labels=labels_str)

        # Call VLM
        response = await self._call_ollama(prompt, image_data)

        # Parse response
        annotations = []
        try:
            # Clean markdown
            cleaned = re.sub(r'^```json\s*', '', response, flags=re.MULTILINE)
            cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            detected = data.get("detected_labels", [])

            for item in detected:
                text = item.get("text", "")
                bbox_pct = item.get("bbox_percent", [])
                leader_ep = item.get("leader_endpoint", [])

                if not text or len(bbox_pct) != 4:
                    continue

                # Convert from percentage (0-100) to normalized (0-1000)
                bbox_norm = [int(v * 10) for v in bbox_pct]

                # Convert to pixel coordinates for mask
                px1 = int(bbox_pct[0] * w / 100)
                py1 = int(bbox_pct[1] * h / 100)
                px2 = int(bbox_pct[2] * w / 100)
                py2 = int(bbox_pct[3] * h / 100)

                text_ann = {
                    "type": "text",
                    "content": text,
                    "bbox": bbox_norm,
                    "bbox_px": [px1, py1, px2, py2],
                    "confidence": item.get("confidence", 0.8)
                }
                annotations.append(text_ann)

                # Add leader line if endpoint provided
                if len(leader_ep) == 2:
                    # Leader line from text center to endpoint
                    text_center_x = (bbox_pct[0] + bbox_pct[2]) / 2
                    text_center_y = (bbox_pct[1] + bbox_pct[3]) / 2

                    line_ann = {
                        "type": "line",
                        "bbox": [
                            int(min(text_center_x, leader_ep[0]) * 10),
                            int(min(text_center_y, leader_ep[1]) * 10),
                            int(max(text_center_x, leader_ep[0]) * 10),
                            int(max(text_center_y, leader_ep[1]) * 10)
                        ],
                        "start": [int(text_center_x * 10), int(text_center_y * 10)],
                        "end": [int(leader_ep[0] * 10), int(leader_ep[1] * 10)],
                        "connects_to": text
                    }
                    annotations.append(line_ann)

            logger.info(f"VLM semantic detection found {len([a for a in annotations if a['type']=='text'])} labels")

            # Log any missed labels
            missed = data.get("missed_labels", [])
            if missed:
                logger.warning(f"VLM could not find labels: {missed}")

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse VLM response: {e}")
            logger.debug(f"Response: {response[:500]}")

        # Create mask
        mask_path = None
        if annotations:
            mask_path = self._create_annotation_mask(image_path, annotations)

        text_count = len([a for a in annotations if a.get("type") == "text"])
        line_count = len([a for a in annotations if a.get("type") == "line"])
        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "annotations": annotations,
            "total_text_labels": text_count,
            "total_leader_lines": line_count,
            "detection_mask_path": mask_path,
            "latency_ms": latency_ms,
            "model": self.model,
            "method": "vlm_semantic"
        }

    async def _detect_hybrid(self, image_path: str, start_time: float) -> Dict[str, Any]:
        """
        Hybrid detection: EasyOCR for text + geometric inference for leader lines.

        This approach:
        1. Use EasyOCR for precise text coordinates
        2. Infer leader lines geometrically (lines extending from text toward diagram center)
        3. Use Hough to find actual line pixels, but only in expected regions

        This avoids the problem of Hough detecting diagram structure by
        constraining the search to regions near text boxes.
        """
        import easyocr

        logger.info("Using hybrid detection: EasyOCR + geometric line inference")

        # Step 1: EasyOCR for precise text detection
        # Use lower thresholds to catch more text (especially smaller/faded labels)
        reader = easyocr.Reader(['en'], gpu=False)
        ocr_results = reader.readtext(
            image_path,
            paragraph=False,
            min_size=5,
            text_threshold=0.3,  # Lower threshold for better recall
            low_text=0.3,
            link_threshold=0.3
        )

        img = cv2.imread(image_path)
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        annotations = []
        text_boxes = []

        for detection in ocr_results:
            bbox_points, text, confidence = detection
            xs = [p[0] for p in bbox_points]
            ys = [p[1] for p in bbox_points]

            # Pixel coordinates
            px1, py1 = int(min(xs)), int(min(ys))
            px2, py2 = int(max(xs)), int(max(ys))

            # Normalized 0-1000 coordinates
            nx1 = int(px1 * 1000 / w)
            ny1 = int(py1 * 1000 / h)
            nx2 = int(px2 * 1000 / w)
            ny2 = int(py2 * 1000 / h)

            text_ann = {
                "type": "text",
                "content": text,
                "bbox": [nx1, ny1, nx2, ny2],
                "bbox_px": [px1, py1, px2, py2],
                "confidence": confidence
            }
            annotations.append(text_ann)
            text_boxes.append(text_ann)

        logger.info(f"EasyOCR detected {len(annotations)} text regions")

        # Step 2: Detect leader lines geometrically
        # Leader lines typically extend horizontally from text toward diagram center
        diagram_center_x = w // 2
        line_annotations = []

        for text_ann in text_boxes:
            px1, py1, px2, py2 = text_ann["bbox_px"]
            text_center_x = (px1 + px2) // 2
            text_center_y = (py1 + py2) // 2

            # Determine direction: text on left -> line goes right, text on right -> line goes left
            if text_center_x < diagram_center_x * 0.6:
                # Text on left side - line extends to the right
                search_start_x = px2  # Right edge of text
                search_end_x = min(w, px2 + int(w * 0.4))  # Up to 40% of image width
                direction = "right"
            elif text_center_x > diagram_center_x * 1.4:
                # Text on right side - line extends to the left
                search_start_x = max(0, px1 - int(w * 0.4))  # Up to 40% left
                search_end_x = px1  # Left edge of text
                direction = "left"
            else:
                # Text in middle - skip
                continue

            # Search for line pixels in a narrow horizontal band
            search_band_y1 = max(0, text_center_y - 15)
            search_band_y2 = min(h, text_center_y + 15)

            # Extract region and detect edges
            if direction == "right":
                region = gray[search_band_y1:search_band_y2, search_start_x:search_end_x]
                offset_x = search_start_x
            else:
                region = gray[search_band_y1:search_band_y2, search_start_x:search_end_x]
                offset_x = search_start_x

            if region.size == 0:
                continue

            # Use Canny edge detection on the small region
            edges = cv2.Canny(region, 50, 150)

            # Find line using Hough on the small region
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=20,
                                    minLineLength=20, maxLineGap=10)

            if lines is not None and len(lines) > 0:
                # Find the most horizontal line
                best_line = None
                best_score = -1

                for line in lines:
                    lx1, ly1, lx2, ly2 = line[0]
                    # Score by horizontalness (closer to 0 angle is better)
                    angle = abs(np.arctan2(ly2 - ly1, lx2 - lx1))
                    horizontal_score = 1 - min(angle, np.pi - angle) / (np.pi / 2)
                    length = np.sqrt((lx2 - lx1)**2 + (ly2 - ly1)**2)

                    if horizontal_score > 0.7 and length > 15:
                        score = horizontal_score * length
                        if score > best_score:
                            best_score = score
                            best_line = line[0]

                if best_line is not None:
                    lx1, ly1, lx2, ly2 = best_line
                    # Convert back to image coordinates
                    line_px1 = offset_x + lx1
                    line_py1 = search_band_y1 + ly1
                    line_px2 = offset_x + lx2
                    line_py2 = search_band_y1 + ly2

                    # Extend line slightly for better coverage
                    if direction == "right":
                        line_px1 = max(px2 - 5, 0)
                    else:
                        line_px2 = min(px1 + 5, w)

                    line_annotations.append({
                        "type": "line",
                        "bbox": [
                            int(min(line_px1, line_px2) * 1000 / w),
                            int(min(line_py1, line_py2) * 1000 / h),
                            int(max(line_px1, line_px2) * 1000 / w),
                            int(max(line_py1, line_py2) * 1000 / h)
                        ],
                        "bbox_px": [
                            min(line_px1, line_px2),
                            min(line_py1, line_py2),
                            max(line_px1, line_px2),
                            max(line_py1, line_py2)
                        ],
                        "start": [int(line_px1 * 1000 / w), int(line_py1 * 1000 / h)],
                        "end": [int(line_px2 * 1000 / w), int(line_py2 * 1000 / h)],
                        "connects_to": text_ann.get("content", ""),
                        "direction": direction
                    })

        annotations.extend(line_annotations)
        logger.info(f"Geometric inference found {len(line_annotations)} leader lines")

        # Create mask
        mask_path = None
        if annotations:
            mask_path = self._create_annotation_mask(image_path, annotations)

        text_count = len(text_boxes)
        line_count = len(line_annotations)

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(f"Hybrid detection: {text_count} text, {line_count} lines in {latency_ms}ms")

        return {
            "annotations": annotations,
            "total_text_labels": text_count,
            "total_leader_lines": line_count,
            "detection_mask_path": mask_path,
            "latency_ms": latency_ms,
            "model": "easyocr+geometric",
            "method": "hybrid_geometric"
        }

    async def detect_annotations_per_label(
        self,
        image_path: str,
        text_labels: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        For each text label, detect its leader line using per-label prompts.
        This is more accurate than bulk detection.

        Args:
            image_path: Path to the diagram image
            text_labels: List of {"content": "label", "bbox": [x1,y1,x2,y2]}

        Returns:
            List of line annotations
        """
        if not await self.is_available():
            return []

        image_data = self._encode_image(image_path)
        lines = []

        for label_info in text_labels:
            label = label_info.get("content", "")
            bbox = label_info.get("bbox", [0, 0, 100, 100])

            if len(bbox) != 4:
                continue

            prompt = LEADER_LINE_PROMPT.format(
                label=label,
                x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3]
            )

            response = await self._call_ollama(prompt, image_data)

            try:
                # Clean and parse
                cleaned = re.sub(r'^```json\s*', '', response, flags=re.MULTILINE)
                cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
                cleaned = cleaned.strip()

                data = json.loads(cleaned)

                if data.get("found", False) and data.get("line"):
                    line_info = data["line"]
                    lines.append({
                        "type": "line",
                        "bbox": line_info.get("bbox", bbox),
                        "start": line_info.get("start", []),
                        "end": line_info.get("end", []),
                        "connects_to": label
                    })
                    logger.debug(f"Found leader line for '{label}'")
                else:
                    logger.debug(f"No leader line for '{label}': {data.get('reason', 'unknown')}")

            except Exception as e:
                logger.warning(f"Failed to parse leader line response for '{label}': {e}")

        return lines

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 with optimization."""
        import base64
        from PIL import Image
        import io

        img = Image.open(image_path)
        width, height = img.size
        max_size = 1024

        # Resize if too large
        if width > max_size or height > max_size:
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert to RGB
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Compress to JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    async def _call_ollama(self, prompt: str, image_base64: str) -> str:
        """Call Ollama API with image."""
        import httpx

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_ctx": 4096
                    }
                }
            )
            response.raise_for_status()
            return response.json().get("response", "")

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse Qwen VL JSON response."""
        # Clean markdown
        cleaned = re.sub(r'^```json\s*', '', response, flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Qwen VL response: {e}")
            logger.debug(f"Response: {response[:500]}")
            return {
                "annotations": [],
                "total_text_labels": 0,
                "total_leader_lines": 0,
                "parse_error": str(e)
            }

    def _create_annotation_mask(
        self,
        image_path: str,
        annotations: List[Dict[str, Any]]
    ) -> str:
        """
        Create a binary mask from detected annotations.

        Uses adaptive padding and morphological operations for clean masks.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        for ann in annotations:
            bbox = ann.get("bbox", [])
            if len(bbox) != 4:
                continue

            # Convert from 0-1000 normalized to pixel coordinates
            x1 = int(bbox[0] * w / 1000)
            y1 = int(bbox[1] * h / 1000)
            x2 = int(bbox[2] * w / 1000)
            y2 = int(bbox[3] * h / 1000)

            ann_type = ann.get("type", "text")

            # Adaptive padding based on element type
            if ann_type == "text":
                padding = max(8, min(20, int((x2 - x1) * 0.2)))
            elif ann_type == "line":
                padding = max(4, min(12, int((x2 - x1) * 0.15)))
            else:
                padding = max(6, min(15, int((x2 - x1) * 0.18)))

            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(w, x2 + padding)
            y2 = min(h, y2 + padding)

            # Fill bounding box
            mask[y1:y2, x1:x2] = 255

            # For lines, also draw the line with thickness
            if ann_type == "line" and ann.get("start") and ann.get("end"):
                start, end = ann["start"], ann["end"]
                if len(start) == 2 and len(end) == 2:
                    pt1 = (int(start[0] * w / 1000), int(start[1] * h / 1000))
                    pt2 = (int(end[0] * w / 1000), int(end[1] * h / 1000))
                    thickness = max(4, min(10, int(w * 0.012)))
                    cv2.line(mask, pt1, pt2, 255, thickness=thickness)

        # Morphological cleanup - connect nearby regions
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.dilate(mask, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Save mask
        mask_dir = Path(image_path).parent
        mask_path = str(mask_dir / f"{Path(image_path).stem}_annotation_mask.png")
        cv2.imwrite(mask_path, mask)

        logger.info(f"Created annotation mask at {mask_path}")
        return mask_path


async def qwen_annotation_detector(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    Detect annotation elements (text labels + leader lines) using Qwen VLM.

    This agent uses semantic understanding to distinguish annotation elements
    from diagram structure, solving the problem where Hough Transform
    incorrectly detects diagram lines.

    When canonical_labels are available from domain_knowledge, uses VLM semantic
    detection for higher accuracy (tells VLM what to look for).

    Inputs: diagram_image, template_selection, domain_knowledge (optional)
    Outputs: annotation_elements, detection_mask_path, text_labels_found
    """
    logger.info("=== QWEN ANNOTATION DETECTOR STARTING ===")

    # Get image path - try multiple sources
    # 1. First try diagram_image.local_path (if set)
    # 2. Then try constructing path from question_id (how image_label_remover saves it)
    diagram_image = state.get("diagram_image", {})
    image_path = diagram_image.get("local_path")

    if not image_path or not Path(image_path).exists():
        # Try constructing path from question_id (matching image_label_remover behavior)
        question_id = state.get("question_id", "unknown")
        constructed_path = Path(__file__).parent.parent.parent / "pipeline_outputs" / "assets" / question_id / "diagram.jpg"
        if constructed_path.exists():
            image_path = str(constructed_path)
            logger.info(f"Using constructed image path: {image_path}")
        else:
            logger.error(f"Image not found: {image_path} and constructed path {constructed_path} doesn't exist")
            return {
                "annotation_elements": [],
                "detection_mask_path": None,
                "text_labels_found": [],
                "detection_error": "Image not found"
            }

    logger.info(f"Processing image: {image_path}")

    # Get canonical labels from domain_knowledge for VLM guidance
    domain_knowledge = state.get("domain_knowledge", {})
    canonical_labels = domain_knowledge.get("canonical_labels", [])
    if canonical_labels:
        logger.info(f"Using {len(canonical_labels)} canonical labels for VLM guidance: {canonical_labels[:5]}...")

    # Initialize detector
    detector = QwenAnnotationDetector()

    # Detect annotations using Qwen VL with canonical labels for better accuracy
    result = await detector.detect_annotations(
        image_path,
        use_hybrid=True,
        canonical_labels=canonical_labels if canonical_labels else None
    )

    if result.get("error"):
        logger.warning(f"Qwen VL detection failed: {result.get('error')}")
        # Fall back to EasyOCR for text-only detection
        logger.info("Falling back to EasyOCR text detection (no leader lines)")
        result = await _fallback_easyocr_detection(image_path)

    # Track metrics
    if ctx:
        ctx.set_llm_metrics(
            model=result.get("model", "qwen2.5vl:7b"),
            prompt_tokens=0,  # Ollama doesn't report this
            completion_tokens=0,
            latency_ms=result.get("latency_ms", 0)
        )

        if result.get("_used_fallback"):
            ctx.set_fallback_used(result.get("_fallback_reason", "Qwen VL unavailable"))

    annotations = result.get("annotations", [])
    text_labels = [a for a in annotations if a.get("type") == "text"]
    leader_lines = [a for a in annotations if a.get("type") == "line"]

    logger.info(f"Detection complete: {len(text_labels)} text labels, {len(leader_lines)} leader lines")

    return {
        "annotation_elements": annotations,
        "detection_mask_path": result.get("detection_mask_path"),
        "text_labels_found": [t.get("content", "") for t in text_labels],
        "text_boxes_count": len(text_labels),
        "lines_detected": len(leader_lines),
        "detection_method": "qwen_vl" if not result.get("_used_fallback") else "easyocr_fallback"
    }


async def _fallback_easyocr_detection(image_path: str) -> Dict[str, Any]:
    """
    Fallback to EasyOCR for text-only detection when Qwen VL is unavailable.

    Note: This will NOT detect leader lines, only text boxes.
    """
    import easyocr

    logger.info("Running EasyOCR fallback detection")
    start_time = time.time()

    reader = easyocr.Reader(['en'], gpu=False)
    results = reader.readtext(image_path)

    img = cv2.imread(image_path)
    h, w = img.shape[:2]

    annotations = []
    for detection in results:
        bbox_points, text, confidence = detection
        xs = [p[0] for p in bbox_points]
        ys = [p[1] for p in bbox_points]

        # Convert to normalized 0-1000 coordinates
        x1 = int(min(xs) * 1000 / w)
        y1 = int(min(ys) * 1000 / h)
        x2 = int(max(xs) * 1000 / w)
        y2 = int(max(ys) * 1000 / h)

        annotations.append({
            "type": "text",
            "content": text,
            "bbox": [x1, y1, x2, y2],
            "confidence": confidence
        })

    # Create mask
    mask = np.zeros((h, w), dtype=np.uint8)
    for ann in annotations:
        bbox = ann["bbox"]
        px1 = int(bbox[0] * w / 1000)
        py1 = int(bbox[1] * h / 1000)
        px2 = int(bbox[2] * w / 1000)
        py2 = int(bbox[3] * h / 1000)

        # Add padding
        padding = 12
        px1 = max(0, px1 - padding)
        py1 = max(0, py1 - padding)
        px2 = min(w, px2 + padding)
        py2 = min(h, py2 + padding)

        mask[py1:py2, px1:px2] = 255

    mask_path = str(Path(image_path).parent / f"{Path(image_path).stem}_easyocr_mask.png")
    cv2.imwrite(mask_path, mask)

    return {
        "annotations": annotations,
        "total_text_labels": len(annotations),
        "total_leader_lines": 0,  # EasyOCR can't detect lines
        "detection_mask_path": mask_path,
        "model": "easyocr",
        "latency_ms": int((time.time() - start_time) * 1000),
        "_used_fallback": True,
        "_fallback_reason": "Qwen VL unavailable, text-only detection"
    }
