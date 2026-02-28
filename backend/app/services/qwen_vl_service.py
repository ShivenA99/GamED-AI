"""
Qwen2.5-VL Service for Object Detection, Label+Line Detection, and Zone Labeling.

This service provides vision-language model capabilities using Qwen2.5-VL via Ollama.
It supports:
- Text label and leader line detection for removal
- Per-label zone detection (more accurate than bulk detection)
- Bounding box generation in normalized coordinates

Environment Variables:
    OLLAMA_BASE_URL: Ollama server URL (default: http://localhost:11434)
    QWEN_VL_MODEL: Model name (default: qwen2.5vl:7b)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("gamed_ai.services.qwen_vl")


class QwenVLError(Exception):
    """Raised when Qwen VL operations fail."""
    pass


# Prompt for detecting text words only (first step - per-word approach)
TEXT_DETECTION_PROMPT = """Analyze this educational/scientific diagram image.

Your task: Identify ALL text labels (words/phrases) that are annotations on this diagram.

Find every text label visible in the image. These are annotation labels, not part of the diagram structure itself.

For EACH text label found, provide:
- "content": The exact text as it appears (e.g., "cell membrane", "nucleus", "mitochondrion")
- "bbox": [x1, y1, x2, y2] - bounding box coordinates in 0-1000 normalized scale
  - x1, y1 = top-left corner
  - x2, y2 = bottom-right corner
  - Each text must have UNIQUE coordinates based on its actual position

Output as JSON:
{
  "text_labels": [
    {"content": "cell membrane", "bbox": [x1, y1, x2, y2]},
    {"content": "nucleus", "bbox": [x1, y1, x2, y2]}
  ]
}

IMPORTANT:
- Include ALL text labels visible in the image
- Each text label must have DIFFERENT bbox coordinates
- Coordinates are normalized to 0-1000 scale
- Return ONLY valid JSON, no markdown, no explanations

Return ONLY the JSON object, nothing else."""


# Prompt for detecting leader line for a specific text label (per-word approach)
LEADER_LINE_FOR_TEXT_PROMPT = """Look at this educational/scientific diagram image.

There is a text label "{text_label}" at coordinates [{x1}, {y1}, {x2}, {y2}] (normalized 0-1000 scale).

Your task: Find the leader line that connects this text label to a diagram part.

A leader line is:
- A thin line that extends from the text label outward toward a diagram part
- Used to point from the text to what it's labeling
- NOT part of the diagram structure itself (not cell membrane, not organelle boundaries)

If you find a leader line connecting to this text, provide:
{{
  "found": true,
  "text_label": "{text_label}",
  "line": {{
    "start": [x, y],  // Point near/at the text label (normalized 0-1000)
    "end": [x, y],    // Point where line connects to diagram part (normalized 0-1000)
    "bbox": [x1, y1, x2, y2]  // Bounding box covering the entire line
  }}
}}

If no leader line is found, respond:
{{
  "found": false,
  "text_label": "{text_label}",
  "reason": "No leader line found"
}}

IMPORTANT:
- Do NOT include diagram structure lines (cell membrane, organelle boundaries)
- Only detect the thin annotation line connecting this specific text to a diagram part
- Coordinates are normalized to 0-1000 scale
- Return ONLY valid JSON, no markdown, no explanations

Return ONLY the JSON object, nothing else."""


# Prompt for detecting text labels AND leader lines (bulk approach - kept for fallback)
LABEL_LINE_DETECTION_PROMPT = """Analyze this educational/scientific diagram image carefully.

Your task: Identify ONLY annotation elements (text labels and their connecting leader lines) that should be removed.

CRITICAL DISTINCTION - You must distinguish between:
✅ **REMOVE**: Annotation elements (text labels + leader lines connecting text to diagram parts)
❌ **KEEP**: Diagram structure lines (cell membrane boundaries, organelle outlines, internal structures)

Elements to detect and REMOVE:
1. **Text Labels**: Any text annotations visible outside or near diagram parts (e.g., "cell membrane", "nucleus", "mitochondrion")
2. **Leader Lines**: Thin lines that connect text labels to diagram parts. These are annotation guides, NOT part of the diagram structure.
   - Leader lines are typically: short, straight, connect text to one specific part, extend from text outward
   - They are NOT: long boundary lines, organelle outlines, internal structure lines, or lines that are part of the diagram itself

Elements to IGNORE (do NOT detect):
- Cell membrane outline (the outer boundary of the cell)
- Organelle boundaries (nucleus membrane, mitochondria outline, etc.)
- Internal structure lines (ER tubules, cristae, etc.)
- Any lines that are part of the actual diagram structure

CRITICAL COORDINATE REQUIREMENTS:
- Output coordinates in pixel format [x1, y1, x2, y2] where:
  - x1, y1 = top-left corner coordinates
  - x2, y2 = bottom-right corner coordinates
  - Minimum value is 0, maximum value is 1000 (normalized to image dimensions)
  - Each annotation MUST have UNIQUE, ACCURATE coordinates based on its actual position
  - Do NOT use the same coordinates for different elements
  - Coordinates must reflect the actual bounding box of each element in the image

For EACH element found:
- type: "text" | "line" | "arrow"
- bbox: [x1, y1, x2, y2] - unique coordinates for this element's position
- For text: "content" field with the actual visible text
- For lines: "start" [x, y] and "end" [x, y] point coordinates (where line starts and ends)

Output as JSON with this EXACT format:
{
  "annotations": [
    {"type": "text", "content": "cell membrane", "bbox": [x1, y1, x2, y2]},
    {"type": "text", "content": "nucleus", "bbox": [x1, y1, x2, y2]},
    {"type": "line", "bbox": [x1, y1, x2, y2], "start": [x, y], "end": [x, y]},
    {"type": "arrow", "bbox": [x1, y1, x2, y2]}
  ]
}

IMPORTANT RULES:
- Each text label must have DIFFERENT bbox coordinates based on where it appears in the image
- Include ONLY leader lines that connect text to diagram parts - these are annotation guides
- Do NOT include diagram structure lines (boundaries, outlines, internal structures)
- Leader lines are typically: short (20-200 pixels), connect text to one specific part, extend outward from text
- The goal is to identify ONLY annotation elements to remove, preserving all diagram structure
- Coordinates are normalized to 0-1000 scale (0,0 is top-left, 1000,1000 is bottom-right)
- Return ONLY valid JSON, no markdown code blocks (```json), no explanations before or after

Return ONLY the JSON object, nothing else."""


# Per-label zone detection prompt - MORE ACCURATE than bulk detection
PER_LABEL_DETECTION_PROMPT = """Look at this educational/scientific diagram image.

Find the EXACT location of "{label}" in this diagram.

The "{label}" is one of the key parts/components of this diagram. Locate it precisely.

Respond with JSON containing the bounding box coordinates (0-1000 normalized scale):
{{
  "found": true,
  "label": "{label}",
  "bbox": [x1, y1, x2, y2],
  "center": [center_x, center_y],
  "confidence": 0.95
}}

If you cannot find "{label}" in the image, respond:
{{
  "found": false,
  "label": "{label}",
  "reason": "brief explanation"
}}

IMPORTANT:
- Coordinates use 0-1000 scale (0,0 is top-left, 1000,1000 is bottom-right)
- bbox is [left, top, right, bottom]
- center is the center point [x, y]
- Be precise - look for the actual anatomical/scientific component, not text labels

Return ONLY the JSON, no other text."""


# Bulk zone detection prompt (fallback)
ZONE_DETECTION_PROMPT = """Analyze this educational diagram image.

Identify all distinct anatomical/scientific components visible.
For each component, provide:
1. A label (e.g., "petal", "stamen", "leaf")
2. A bounding box in normalized coordinates (0-1000 scale)

{context}

Output as JSON:
{{
  "detected_zones": [
    {{"id": "zone_1", "label": "component_name", "bbox": [x1, y1, x2, y2], "confidence": 0.95}}
  ]
}}

Focus on scientific/anatomical parts, ignore decorative elements.
Return ONLY the JSON, no other text."""


class QwenVLService:
    """Service for Qwen2.5-VL vision-language model operations."""
    
    def __init__(self):
        self.model = os.getenv("QWEN_VL_MODEL", "qwen2.5vl:7b")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._available = None
        self.timeout = float(os.getenv("QWEN_VL_TIMEOUT", "300.0"))  # VLM can be slow, default 5 minutes
    
    async def is_available(self) -> bool:
        """Check if Qwen VL model is available via Ollama."""
        if self._available is not None:
            return self._available
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self._available = any(self.model in m for m in models)
                    if not self._available:
                        logger.warning(
                            f"Qwen VL model '{self.model}' not found. "
                            f"Available models: {models[:5]}... "
                            f"Run: ollama pull {self.model}"
                        )
                    return self._available
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")
            self._available = False
        return False
    
    async def detect_text_labels_only(
        self,
        image_path: str
    ) -> List[Dict[str, Any]]:
        """
        Step 1: Detect all text labels in the image.
        
        Args:
            image_path: Path to the diagram image
            
        Returns:
            List of text labels with content and bbox
        """
        if not await self.is_available():
            raise QwenVLError(f"Qwen VL model '{self.model}' not available")
        
        # Encode image
        image_data = self._encode_image(image_path)
        
        # Get image dimensions for context
        try:
            from PIL import Image
            img = Image.open(image_path)
            img_width, img_height = img.size
            dimension_hint = f"\n\nNote: Image dimensions are {img_width}x{img_height} pixels. Use 0-1000 normalized scale."
            prompt = TEXT_DETECTION_PROMPT + dimension_hint
        except (IOError, OSError, FileNotFoundError) as e:
            logger.debug(f"Could not read image dimensions: {e}, using base prompt")
            prompt = TEXT_DETECTION_PROMPT
        
        response = await self._call_ollama(prompt, image_data)
        
        # Parse response
        try:
            # Clean markdown if present
            cleaned = re.sub(r'^```json\s*', '', response, flags=re.MULTILINE)
            cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            text_labels = data.get("text_labels", [])
            
            logger.info(f"Qwen VL detected {len(text_labels)} text labels")
            return text_labels
        except Exception as e:
            logger.error(f"Failed to parse text labels response: {e}")
            logger.debug(f"Response: {response[:500]}")
            return []
    
    async def detect_leader_line_for_text(
        self,
        image_path: str,
        text_label: str,
        text_bbox: List[int]
    ) -> Optional[Dict[str, Any]]:
        """
        Step 2: For a specific text label, detect its connecting leader line.
        
        Args:
            image_path: Path to the diagram image
            text_label: The text content
            text_bbox: [x1, y1, x2, y2] in normalized 0-1000 scale
            
        Returns:
            Dict with line info if found, None otherwise
        """
        if not await self.is_available():
            return None
        
        # Encode image
        image_data = self._encode_image(image_path)
        
        # Build prompt with text label and coordinates
        x1, y1, x2, y2 = text_bbox
        prompt = LEADER_LINE_FOR_TEXT_PROMPT.format(
            text_label=text_label,
            x1=x1, y1=y1, x2=x2, y2=y2
        )
        
        response = await self._call_ollama(prompt, image_data)
        
        # Parse response
        try:
            cleaned = re.sub(r'^```json\s*', '', response, flags=re.MULTILINE)
            cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            if data.get("found", False):
                return data.get("line")
            return None
        except Exception as e:
            logger.warning(f"Failed to parse leader line response for '{text_label}': {e}")
            return None
    
    async def detect_labels_and_lines_per_word(
        self,
        image_path: str
    ) -> Dict[str, Any]:
        """
        Per-word approach: Detect all text labels, then for each detect its leader line.
        This is more accurate than bulk detection.
        
        Args:
            image_path: Path to the diagram image
            
        Returns:
            Dict with annotations and mask_path
        """
        start_time = time.time()
        
        if not await self.is_available():
            raise QwenVLError(f"Qwen VL model '{self.model}' not available")
        
        # Step 1: Detect all text labels
        logger.info("Step 1: Detecting all text labels...")
        text_labels = await self.detect_text_labels_only(image_path)
        
        if not text_labels:
            logger.warning("No text labels detected")
            return {
                "annotations": [],
                "mask_path": None,
                "model": self.model,
                "latency_ms": int((time.time() - start_time) * 1000)
            }
        
        # Step 2: For each text label, detect its leader line
        logger.info(f"Step 2: Detecting leader lines for {len(text_labels)} text labels...")
        annotations = []
        
        for text_info in text_labels:
            text_content = text_info.get("content", "")
            text_bbox = text_info.get("bbox", [])
            
            if len(text_bbox) != 4:
                continue
            
            # Add text annotation
            annotations.append({
                "type": "text",
                "content": text_content,
                "bbox": text_bbox
            })
            
            # Detect leader line for this text
            line_info = await self.detect_leader_line_for_text(
                image_path, text_content, text_bbox
            )
            
            if line_info:
                annotations.append({
                    "type": "line",
                    "bbox": line_info.get("bbox", text_bbox),
                    "start": line_info.get("start", []),
                    "end": line_info.get("end", []),
                    "text_label": text_content
                })
                logger.debug(f"Found leader line for '{text_content}'")
            else:
                logger.debug(f"No leader line found for '{text_content}'")
        
        logger.info(f"Per-word detection: {len(text_labels)} text labels, {sum(1 for a in annotations if a.get('type') == 'line')} leader lines")
        
        # Step 3: Create mask from annotations
        mask_path = None
        if annotations:
            mask_path = await self._create_comprehensive_mask(image_path, annotations)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "annotations": annotations,
            "mask_path": mask_path,
            "model": self.model,
            "latency_ms": latency_ms
        }
    
    async def detect_labels_and_lines(
        self,
        image_path: str,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect text labels AND leader lines for removal (bulk approach).
        
        Args:
            image_path: Path to the diagram image
            custom_prompt: Optional custom detection prompt
            
        Returns:
            Dict with:
            - annotations: List of detected annotations
            - mask_path: Path to generated mask image
            - model: Model used
            - latency_ms: Processing time
        """
        start_time = time.time()

        if not await self.is_available():
            raise QwenVLError(
                f"Qwen VL model '{self.model}' not available. "
                f"Run: ollama pull {self.model}"
            )

        # Get original image dimensions before encoding (for coordinate scaling)
        try:
            from PIL import Image
            original_img = Image.open(image_path)
            original_width, original_height = original_img.size
            # Check if image was resized during encoding
            max_size = 1024
            if original_width > max_size or original_height > max_size:
                if original_width > original_height:
                    encoded_width = max_size
                    encoded_height = int(original_height * (max_size / original_width))
                else:
                    encoded_height = max_size
                    encoded_width = int(original_width * (max_size / original_height))
                scale_x = original_width / encoded_width
                scale_y = original_height / encoded_height
            else:
                scale_x = 1.0
                scale_y = 1.0
        except Exception as e:
            logger.warning(f"Could not get image dimensions: {e}, assuming no scaling")
            scale_x = 1.0
            scale_y = 1.0

        # Encode image (may resize if too large)
        image_data = self._encode_image(image_path)

        # Build prompt with image dimensions for better coordinate accuracy
        base_prompt = custom_prompt or LABEL_LINE_DETECTION_PROMPT
        
        # Add image dimension context to help with coordinate accuracy
        try:
            from PIL import Image
            img = Image.open(image_path)
            img_width, img_height = img.size
            dimension_hint = f"\n\nNote: The image dimensions are approximately {img_width}x{img_height} pixels. Use coordinates in 0-1000 normalized scale where 1000 represents the full width/height."
            prompt = base_prompt + dimension_hint
        except (IOError, OSError, FileNotFoundError) as e:
            logger.debug(f"Could not read image dimensions: {e}, using base prompt")
            prompt = base_prompt
        
        response = await self._call_ollama(prompt, image_data)
        
        # Log raw response for debugging (first 1000 chars)
        logger.debug(f"Qwen VL raw response (first 1000 chars): {response[:1000]}")

        # Parse response
        annotations = self._parse_annotations_response(response)
        
        # Scale coordinates back to original image size if image was resized
        if scale_x != 1.0 or scale_y != 1.0:
            logger.info(f"Scaling annotations from encoded size to original (scale: {scale_x:.2f}x, {scale_y:.2f}x)")
            for ann in annotations:
                bbox = ann.get("bbox", [])
                if len(bbox) == 4:
                    ann["bbox"] = [
                        int(bbox[0] * scale_x),
                        int(bbox[1] * scale_y),
                        int(bbox[2] * scale_x),
                        int(bbox[3] * scale_y)
                    ]
                # Scale line start/end points if present
                if ann.get("start") and len(ann["start"]) == 2:
                    ann["start"] = [int(ann["start"][0] * scale_x), int(ann["start"][1] * scale_y)]
                if ann.get("end") and len(ann["end"]) == 2:
                    ann["end"] = [int(ann["end"][0] * scale_x), int(ann["end"][1] * scale_y)]

        logger.info(
            f"Detected {len(annotations)} annotations "
            f"(text: {sum(1 for a in annotations if a.get('type') == 'text')}, "
            f"lines: {sum(1 for a in annotations if a.get('type') == 'line')})"
        )

        # Generate mask from annotations (using original image)
        mask_path = None
        if annotations:
            mask_path = await self._create_comprehensive_mask(image_path, annotations)

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "annotations": annotations,
            "mask_path": mask_path,
            "model": self.model,
            "latency_ms": latency_ms,
            "raw_response": response[:500] if response else None
        }
    
    async def detect_zone_for_label(
        self,
        image_path: str,
        label: str,
        image_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect zone for a single label using per-label prompt (more accurate).
        
        Args:
            image_path: Path to the diagram image
            label: Label to find
            image_data: Optional pre-encoded image data
            
        Returns:
            Dict with found, label, bbox, center, confidence
        """
        if not await self.is_available():
            raise QwenVLError(
                f"Qwen VL model '{self.model}' not available. "
                f"Run: ollama pull {self.model}"
            )
        
        if image_data is None:
            image_data = self._encode_image(image_path)
        
        prompt = PER_LABEL_DETECTION_PROMPT.format(label=label)
        response = await self._call_ollama(prompt, image_data)
        
        # Parse response
        try:
            # Clean markdown if present
            cleaned = re.sub(r'^```json\s*', '', response, flags=re.MULTILINE)
            cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            return data
        except Exception as e:
            logger.warning(f"Failed to parse zone detection response for '{label}': {e}")
            logger.debug(f"Response: {response[:500]}")
            return {"found": False, "label": label, "reason": f"Parse error: {e}"}
    
    async def detect_zones_per_label(
        self,
        image_path: str,
        labels: List[str],
        parallel: bool = False
    ) -> Dict[str, Any]:
        """
        Detect zones for multiple labels using per-label approach (more accurate).
        
        Args:
            image_path: Path to the diagram image
            labels: List of labels to find
            parallel: Whether to run queries in parallel (faster but may overwhelm Ollama)
            
        Returns:
            Dict with detected_zones and missing labels
        """
        if not await self.is_available():
            raise QwenVLError(
                f"Qwen VL model '{self.model}' not available. "
                f"Run: ollama pull {self.model}"
            )
        
        # Encode image once
        image_data = self._encode_image(image_path)
        
        if parallel:
            # Run all queries in parallel
            tasks = [
                self.detect_zone_for_label(image_path, label, image_data)
                for label in labels
            ]
            results = await asyncio.gather(*tasks)
        else:
            # Run sequentially (more reliable)
            results = []
            for label in labels:
                result = await self.detect_zone_for_label(image_path, label, image_data)
                results.append(result)
        
        detected_zones = []
        missing = []
        
        for result in results:
            if result.get("found", False):
                detected_zones.append({
                    "id": f"zone_{len(detected_zones) + 1}",
                    "label": result.get("label"),
                    "bbox": result.get("bbox"),
                    "center": result.get("center"),
                    "confidence": result.get("confidence", 0.95)
                })
            else:
                missing.append(result.get("label"))
        
        return {
            "detected_zones": detected_zones,
            "missing": missing,
            "model": self.model
        }
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64, with optimization for large images.
        
        Optimizations:
        - Resize if too large (max 1024px longest side)
        - Compress to JPEG quality 85
        - This prevents Ollama crashes and reduces payload size
        """
        try:
            from PIL import Image
            import io
        except ImportError:
            raise QwenVLError("PIL required: pip install Pillow")
        
        img = Image.open(image_path)
        width, height = img.size
        max_size = 1024
        
        # Resize if too large
        scale_x = scale_y = 1.0
        if width > max_size or height > max_size:
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            scale_x = width / new_width
            scale_y = height / new_height
            
            logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height} for Qwen VL")
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Compress to JPEG quality 85
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        image_bytes = buffer.getvalue()
        
        # Encode to base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        return image_base64
    
    def _parse_annotations_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse Qwen VL response to extract annotations.
        Handles markdown code blocks and incomplete JSON.
        """
        # Clean markdown code blocks
        cleaned_response = re.sub(r'^```json\s*', '', response, flags=re.MULTILINE)
        cleaned_response = re.sub(r'^```\s*', '', cleaned_response, flags=re.MULTILINE)
        cleaned_response = re.sub(r'```\s*$', '', cleaned_response, flags=re.MULTILINE)
        cleaned_response = cleaned_response.strip()
        
        # Try to parse JSON
        try:
            data = json.loads(cleaned_response)
            annotations = data.get("annotations", [])
            if annotations:
                logger.info(f"Successfully parsed JSON from response (found {len(annotations)} annotations)")
                return annotations
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse attempt 1 failed: {e}")
        
        # Try to find JSON object in response
        try:
            # Look for { ... } pattern
            match = re.search(r'\{[^{}]*"annotations"[^{}]*\[.*?\]', cleaned_response, re.DOTALL)
            if match:
                json_str = match.group(0)
                # Try to complete incomplete JSON
                if not json_str.rstrip().endswith('}'):
                    # Find last complete annotation entry
                    last_complete = json_str.rfind('}')
                    if last_complete > 0:
                        json_str = json_str[:last_complete + 1] + ']}'
                
                data = json.loads(json_str)
                annotations = data.get("annotations", [])
                if annotations:
                    logger.info(f"Fixed incomplete JSON and parsed {len(annotations)} annotations")
                    return annotations
        except Exception as e:
            logger.warning(f"JSON parse attempt 2 failed: {e}")
        
        logger.error(f"Could not parse JSON from Qwen VL response")
        logger.debug(f"Response (first 1000 chars): {response[:1000]}")
        return []
    
    async def _call_ollama(self, prompt: str, image_base64: str) -> str:
        """Call Ollama API with image."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "images": [image_base64],
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temperature for accurate coordinates
                            "num_ctx": 4096
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
            except httpx.TimeoutException:
                raise QwenVLError(f"Ollama request timed out after {self.timeout}s")
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get("error", {}).get("message", str(e))
                except (json.JSONDecodeError, ValueError, AttributeError) as parse_error:
                    logger.debug(f"Could not parse error response JSON: {parse_error}")
                    error_detail = str(e)
                logger.error(f"Ollama HTTP {e.response.status_code}: {error_detail}")
                raise QwenVLError(f"Ollama HTTP error {e.response.status_code}: {error_detail}")
            except Exception as e:
                logger.error(f"Ollama call failed: {e}")
                raise QwenVLError(f"Ollama call failed: {e}")
    
    async def _create_comprehensive_mask(
        self,
        image_path: str,
        annotations: List[Dict[str, Any]]
    ) -> str:
        """
        Create mask covering both text and lines with optimized dilation.
        
        Based on research:
        - Character-wise masks are better than bounding boxes
        - Adaptive padding based on element size
        - Proper dilation to avoid remnants without artifacts
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            raise QwenVLError("OpenCV required: pip install opencv-python")

        img = cv2.imread(image_path)
        if img is None:
            raise QwenVLError(f"Could not load image: {image_path}")

        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        for ann in annotations:
            bbox = ann.get("bbox", [])
            if len(bbox) != 4:
                continue

            x1 = int(bbox[0] * w / 1000)
            y1 = int(bbox[1] * h / 1000)
            x2 = int(bbox[2] * w / 1000)
            y2 = int(bbox[3] * h / 1000)

            ann_type = ann.get("type", "text")
            
            # Adaptive padding based on element size and type
            bbox_width = x2 - x1
            bbox_height = y2 - y1
            element_size = max(bbox_width, bbox_height)
            
            if ann_type == "text":
                # For text: use 20-30% of element size, minimum 10px, maximum 25px
                padding = max(10, min(25, int(element_size * 0.25)))
            elif ann_type == "line":
                # For lines: use 15-20% of element size, minimum 5px, maximum 15px
                padding = max(5, min(15, int(element_size * 0.18)))
            else:
                # For arrows/brackets: medium padding
                padding = max(8, min(20, int(element_size * 0.20)))

            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(w, x2 + padding)
            y2 = min(h, y2 + padding)

            # Fill the bounding box region
            mask[y1:y2, x1:x2] = 255

            # For lines, draw the line itself with sufficient thickness
            if ann_type == "line" and ann.get("start") and ann.get("end"):
                start, end = ann["start"], ann["end"]
                if len(start) == 2 and len(end) == 2:
                    pt1 = (int(start[0] * w / 1000), int(start[1] * h / 1000))
                    pt2 = (int(end[0] * w / 1000), int(end[1] * h / 1000))
                    # Line thickness: 1-2% of image width, minimum 6px, maximum 12px
                    line_thickness = max(6, min(12, int(w * 0.015)))
                    cv2.line(mask, pt1, pt2, 255, thickness=line_thickness)

        # Connect fragmented line segments using morphological closing
        # Use directional kernels to connect lines without over-dilating
        
        # First, identify line regions (thin, elongated)
        line_mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)
        line_regions = cv2.subtract(mask, line_mask)
        
        # For line regions, use morphological closing to connect fragments
        if np.sum(line_regions > 0) > 0:
            # Use small kernel for closing gaps in lines
            close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            line_regions = cv2.morphologyEx(line_regions, cv2.MORPH_CLOSE, close_kernel, iterations=1)
            # Recombine with text regions
            mask = cv2.bitwise_or(mask, line_regions)
        
        # Minimal dilation to ensure complete coverage without over-expansion
        kernel_size = max(3, min(7, int(w * 0.008)))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Optional: Slight blur for smoother edges (minimal)
        mask = cv2.GaussianBlur(mask, (3, 3), 0.5)
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

        mask_dir = Path(image_path).parent
        mask_path = str(mask_dir / f"{Path(image_path).stem}_qwen_mask.png")
        cv2.imwrite(mask_path, mask)

        logger.info(f"Created comprehensive mask at {mask_path} (adaptive padding, optimized dilation)")
        return mask_path


# Singleton instance
_qwen_vl_service: Optional[QwenVLService] = None


def get_qwen_vl_service() -> QwenVLService:
    """Get singleton Qwen VL service instance."""
    global _qwen_vl_service
    if _qwen_vl_service is None:
        _qwen_vl_service = QwenVLService()
    return _qwen_vl_service
