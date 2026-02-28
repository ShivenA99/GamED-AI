"""Gemini native image generation and editing via google-genai SDK.

Uses gemini-2.5-flash-image for:
- Image editing (remove labels, clean up, restyle)
- Style-consistent multi-image generation via multi-turn chat
- Reference-based generation (match style of existing image)
- Zone detection on diagram images
"""

import json
import logging
import os
import re
from io import BytesIO
from typing import Optional

from PIL import Image
from google import genai
from google.genai import types

logger = logging.getLogger("gamed_ai.asset_gen.gemini")


class GeminiImageEditor:
    """Edit and generate images using Gemini native image generation."""

    IMAGE_MODEL = "gemini-2.5-flash-image"
    VISION_MODEL = "gemini-3-flash-preview"

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GOOGLE_API_KEY not set")
        self.client = genai.Client(api_key=key)

    async def clean_diagram(
        self,
        image_bytes: bytes,
        instructions: str = "Remove all text labels, annotations, arrows, and leader lines. Reconstruct the background cleanly. Keep all structural elements intact.",
    ) -> bytes:
        """Remove labels/annotations from a diagram image.

        Args:
            image_bytes: Source image PNG/JPG bytes
            instructions: What to remove/clean

        Returns:
            Cleaned PNG image bytes
        """
        source = Image.open(BytesIO(image_bytes))
        logger.info(f"Cleaning diagram: {source.size}, instructions: {instructions[:80]}...")

        response = self.client.models.generate_content(
            model=self.IMAGE_MODEL,
            contents=[instructions, source],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.inline_data.data

        raise RuntimeError("Gemini did not return an image")

    async def regenerate_from_reference(
        self,
        reference_bytes: bytes,
        prompt: str,
        aspect_ratio: str = "4:3",
    ) -> bytes:
        """Generate a new image inspired by a reference image.

        This is the core "search → regenerate" workflow:
        1. We found a reference diagram via Serper
        2. We send it to Gemini with instructions to create a clean custom version
        3. Result: copyright-free, customized, label-free diagram

        Args:
            reference_bytes: Reference image bytes
            prompt: Description of what to generate
            aspect_ratio: Output aspect ratio

        Returns:
            Generated PNG image bytes
        """
        reference = Image.open(BytesIO(reference_bytes))
        logger.info(f"Regenerating from reference: {reference.size}")

        response = self.client.models.generate_content(
            model=self.IMAGE_MODEL,
            contents=[
                reference,
                f"Using the above image ONLY as a reference for anatomical layout and structure, "
                f"create a completely new, original illustration. {prompt} "
                f"MOST IMPORTANT RULE: The generated image must contain ABSOLUTELY ZERO text. "
                f"No labels, no annotations, no captions, no arrows with text, no leader lines, "
                f"no watermarks, no letters, no numbers, no words of any kind. "
                f"If the reference image has text labels, REMOVE them entirely — "
                f"draw only the anatomical structures themselves. "
                f"Clean white background, high contrast, textbook illustration quality.",
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.inline_data.data

        raise RuntimeError("Gemini did not return an image")

    async def generate_style_consistent_set(
        self,
        items: list[dict],
        style_description: str,
        aspect_ratio: str = "1:1",
        reference_image: bytes | None = None,
    ) -> list[bytes]:
        """Generate a set of images with consistent style using multi-turn chat.

        Args:
            items: List of dicts with 'name' and 'description' keys
            style_description: Style to maintain across all images
            aspect_ratio: Aspect ratio for all images
            reference_image: Optional reference image bytes (e.g. from Serper)
                to ground the visual style of the first generation

        Returns:
            List of PNG image bytes, one per item
        """
        logger.info(
            f"Generating style-consistent set of {len(items)} images"
            f"{' (with reference image)' if reference_image else ''}"
        )

        chat = self.client.chats.create(
            model=self.IMAGE_MODEL,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )

        results = []

        # First image sets the style — optionally grounded by a reference image
        first = items[0]
        first_prompt = (
            f"Generate a {style_description} of {first['name']}. "
            f"{first.get('description', '')}. "
            f"Clean white background, centered, no text, high quality. "
            f"This is the first in a set — establish a consistent visual style."
        )

        if reference_image:
            ref_img = Image.open(BytesIO(reference_image))
            logger.info(f"Using reference image ({ref_img.size}) to ground style")
            response = chat.send_message([
                ref_img,
                f"Use this reference image as visual inspiration for style, colors, "
                f"and level of detail. Do NOT copy it — create an original illustration. "
                f"{first_prompt}",
            ])
        else:
            response = chat.send_message(first_prompt)

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                results.append(part.inline_data.data)
                break

        # Subsequent images match the style
        for item in items[1:]:
            try:
                response = chat.send_message(
                    f"Now generate {item['name']} in exactly the same visual style. "
                    f"{item.get('description', '')}. "
                    f"Match the colors, line weight, and rendering style of the previous images."
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        results.append(part.inline_data.data)
                        break
            except Exception as e:
                logger.warning(f"Failed to generate {item['name']}: {e}")
                # Generate standalone as fallback
                fb = await self._generate_standalone(item, style_description, aspect_ratio)
                results.append(fb)

        logger.info(f"Generated {len(results)}/{len(items)} images")
        return results

    async def _generate_standalone(
        self, item: dict, style: str, aspect_ratio: str
    ) -> bytes:
        """Fallback: generate a single image without chat context."""
        response = self.client.models.generate_content(
            model=self.IMAGE_MODEL,
            contents=(
                f"A {style} of {item['name']}. {item.get('description', '')}. "
                f"Clean white background, centered, no text."
            ),
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                return part.inline_data.data
        raise RuntimeError(f"Failed to generate image for {item['name']}")

    async def detect_zones(
        self,
        image_bytes: bytes,
        expected_labels: list[str],
        context: str = "",
    ) -> list[dict]:
        """Detect interactive zones using Gemini native segmentation masks.

        Uses Gemini's segmentation mask API → OpenCV contours → Douglas-Peucker
        polygon simplification for pixel-precise zone boundaries.

        Falls back to text-based polygon detection if OpenCV is unavailable.

        Returns:
            List of zone dicts with polygon boundaries (0-100 percentage coords).
        """
        # Try mask-based detection first (pixel-precise)
        mask_result = None
        try:
            mask_result = await self._detect_zones_with_masks(image_bytes, expected_labels, context)
        except Exception as e:
            logger.warning(f"Mask-based detection failed, falling back to text: {e}")

        if mask_result and len(mask_result) >= len(expected_labels):
            return mask_result

        # If masks got some but not all zones, supplement with text fallback
        if mask_result and len(mask_result) > 0:
            found_labels = {z["label"].lower() for z in mask_result}
            missing_labels = [l for l in expected_labels if l.lower() not in found_labels]
            if missing_labels:
                logger.info(f"Masks found {len(mask_result)}/{len(expected_labels)} — "
                            f"text fallback for: {', '.join(missing_labels)}")
                try:
                    text_result = await self._detect_zones_with_text(
                        image_bytes, missing_labels, context
                    )
                    mask_result.extend(text_result)
                except Exception as e:
                    logger.warning(f"Text fallback for missing zones failed: {e}")
            return mask_result

        # Full fallback: text-based polygon detection for all labels
        return await self._detect_zones_with_text(image_bytes, expected_labels, context)

    async def _detect_zones_with_masks(
        self,
        image_bytes: bytes,
        expected_labels: list[str],
        context: str = "",
    ) -> list[dict] | None:
        """Detect zones using Gemini's native segmentation mask API.

        Gemini returns multipart responses: alternating text parts (JSON with
        label + box_2d) and inline_data parts (PNG segmentation masks).
        We decode masks → OpenCV findContours → Douglas-Peucker simplification
        → pixel-precise polygon boundaries.

        IMPORTANT: Do NOT use response_mime_type="application/json" — that forces
        Gemini to serialize binary mask PNGs as JSON strings, corrupting them.
        """
        try:
            import cv2
            import numpy as np
            import io as _io
        except ImportError:
            logger.warning("OpenCV not available — skipping mask detection")
            return None

        image = Image.open(BytesIO(image_bytes))
        img_width, img_height = image.size
        labels_text = ", ".join(expected_labels)
        subject = context.replace("Educational diagram of ", "") if context else "educational"

        logger.info(f"Detecting zones with native masks for: {labels_text}")

        prompt = (
            f"Give the segmentation masks for each of these parts in this "
            f"{subject} diagram: {labels_text}\n\n"
            f"For each part, output:\n"
            f'1. A JSON object with "label" (exact name as listed) and '
            f'"box_2d" ([y_min, x_min, y_max, x_max] in 0-1000 scale)\n'
            f"2. The segmentation mask image for that part\n\n"
            f"Return results for ALL {len(expected_labels)} parts. "
            f"Each part MUST have its own mask image."
        )

        # MUST use IMAGE_MODEL with IMAGE modality to get actual PNG masks.
        # VISION_MODEL (text-only) returns text-encoded mask tokens that can't be decoded.
        import time as _time
        response = None
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.IMAGE_MODEL,
                    contents=[prompt, image],
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
                    ),
                )
                # Check that we got multipart response with images
                parts_check = response.candidates[0].content.parts if response.candidates else []
                has_images = any(
                    hasattr(p, 'inline_data') and p.inline_data
                    for p in parts_check
                )
                if has_images:
                    break
                logger.warning(f"Mask attempt {attempt+1}: no image parts in response, retrying")
            except Exception as e:
                logger.warning(f"Mask attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    _time.sleep(5 * (attempt + 1))
                continue

        if not response or not response.candidates:
            return None

        # Parse multipart response: alternating text + inline_data parts
        parts = response.candidates[0].content.parts if response.candidates else []
        logger.info(f"Mask response: {len(parts)} parts")

        # Collect (metadata, mask_bytes) pairs
        entries = []
        current_meta = None
        for part in parts:
            if hasattr(part, 'text') and part.text:
                # Text part — extract JSON metadata (label + box_2d)
                text = part.text.strip()
                # Strip markdown code fences
                text = re.sub(r'```(?:json)?\s*', '', text).strip().rstrip('`').strip()

                # Gemini sometimes emits duplicate "label" keys:
                #   {"box_2d": [...], "label": "Petal", "label": "label"}
                # json.loads keeps LAST duplicate, so "label" overwrites "Petal".
                # Fix: extract FIRST "label" value via regex before json.loads.
                first_label = None
                label_match = re.search(r'"label"\s*:\s*"([^"]+)"', text)
                if label_match and label_match.group(1) != "label":
                    first_label = label_match.group(1)

                # Find JSON objects in the text (may contain garbage around them)
                for match in re.finditer(r'\{[^{}]+\}', text):
                    try:
                        obj = json.loads(match.group())
                        if "box_2d" in obj:
                            # Restore correct label if it was overwritten by duplicate key
                            if first_label and obj.get("label") == "label":
                                obj["label"] = first_label
                            current_meta = obj
                            first_label = None  # consumed
                    except json.JSONDecodeError:
                        continue
            elif hasattr(part, 'inline_data') and part.inline_data:
                # Image part — this is a mask PNG
                mask_data = part.inline_data.data
                if current_meta:
                    entries.append((current_meta, mask_data))
                    current_meta = None
                elif entries and entries[-1][1] is None:
                    # Attach to previous metadata that has no mask yet
                    meta = entries[-1][0]
                    entries[-1] = (meta, mask_data)

        logger.info(f"Parsed {len(entries)} mask entries from multipart response")

        if not entries:
            logger.warning("No mask entries found in response")
            return None

        # Build label lookup for case-insensitive matching
        label_lookup = {l.lower(): l for l in expected_labels}

        result = []
        for entry_meta, mask_data in entries:
            raw_label = entry_meta.get("label", "")
            # Normalize label: match to expected labels case-insensitively
            label = label_lookup.get(raw_label.lower(), raw_label)
            box_2d = entry_meta.get("box_2d")

            if not label or not box_2d:
                logger.warning(f"Missing label/box_2d for entry, skipping")
                continue

            if not mask_data:
                logger.warning(f"No mask data for '{label}', skipping")
                continue

            try:
                # box_2d is [y_min, x_min, y_max, x_max] in 0-1000 scale
                # Gemini sometimes returns 5 values — take first 4
                y0, x0, y1, x1 = box_2d[:4]
                px0 = int(x0 * img_width / 1000)
                py0 = int(y0 * img_height / 1000)
                px1 = int(x1 * img_width / 1000)
                py1 = int(y1 * img_height / 1000)
                box_w = max(px1 - px0, 1)
                box_h = max(py1 - py0, 1)

                # Decode mask PNG (inline_data is raw bytes, not base64)
                if isinstance(mask_data, str):
                    import base64
                    mask_bytes_decoded = base64.b64decode(mask_data)
                else:
                    mask_bytes_decoded = bytes(mask_data)

                mask_img = Image.open(_io.BytesIO(mask_bytes_decoded)).convert("L")
                mask_resized = mask_img.resize((box_w, box_h), Image.NEAREST)
                mask_array = np.array(mask_resized)

                # Place mask in full-image canvas
                full_mask = np.zeros((img_height, img_width), dtype=np.uint8)
                paste_y0, paste_x0 = max(0, py0), max(0, px0)
                paste_y1 = min(img_height, py0 + box_h)
                paste_x1 = min(img_width, px0 + box_w)
                src_y0, src_x0 = paste_y0 - py0, paste_x0 - px0
                src_y1 = src_y0 + (paste_y1 - paste_y0)
                src_x1 = src_x0 + (paste_x1 - paste_x0)
                full_mask[paste_y0:paste_y1, paste_x0:paste_x1] = mask_array[src_y0:src_y1, src_x0:src_x1]

                # Binarize + find contours
                _, binary = cv2.threshold(full_mask, 127, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours:
                    continue

                largest = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest) < 100:
                    continue

                # Douglas-Peucker simplification
                perimeter = cv2.arcLength(largest, True)
                epsilon = 0.005 * perimeter
                simplified = cv2.approxPolyDP(largest, epsilon, True)

                while len(simplified) > 80 and epsilon < perimeter / 10:
                    epsilon *= 1.5
                    simplified = cv2.approxPolyDP(largest, epsilon, True)

                while len(simplified) < 6 and epsilon > 0.1:
                    epsilon *= 0.5
                    simplified = cv2.approxPolyDP(largest, epsilon, True)

                # Convert to percentage coordinates
                polygon = []
                for pt in simplified:
                    x_pct = round(float(pt[0][0]) / img_width * 100, 1)
                    y_pct = round(float(pt[0][1]) / img_height * 100, 1)
                    polygon.append([x_pct, y_pct])

                if len(polygon) < 3:
                    continue

                cx = round(sum(p[0] for p in polygon) / len(polygon), 1)
                cy = round(sum(p[1] for p in polygon) / len(polygon), 1)
                max_dist = max(
                    ((p[0] - cx) ** 2 + (p[1] - cy) ** 2) ** 0.5
                    for p in polygon
                )

                zone_id = f"zone_{label.lower().replace(' ', '_').replace('-', '_')}"
                result.append({
                    "id": zone_id,
                    "label": label,
                    "points": polygon,
                    "x": cx,
                    "y": cy,
                    "radius": round(max_dist, 1),
                    "center": {"x": cx, "y": cy},
                    "shape": "polygon",
                    "description": "",
                })
                logger.info(f"  Mask→polygon '{label}': {len(polygon)} points, center=({cx},{cy})")

            except Exception as e:
                logger.warning(f"Mask processing failed for '{label}': {e}")
                continue

        if not result:
            logger.warning("No zones from masks — will fall back to text detection")
            return None

        logger.info(f"Mask detection: {len(result)}/{len(expected_labels)} zones")
        return result

    async def _detect_zones_with_text(
        self,
        image_bytes: bytes,
        expected_labels: list[str],
        context: str = "",
    ) -> list[dict]:
        """Fallback: detect zones via text-based polygon coordinate estimation."""
        image = Image.open(BytesIO(image_bytes))
        labels_text = ", ".join(expected_labels)
        logger.info(f"Detecting zones with text fallback for: {labels_text}")

        prompt = (
            f"Analyze this educational diagram and locate each of these structures: {labels_text}.\n"
            f"{f'Context: {context}' if context else ''}\n\n"
            f"For each structure, trace its PRECISE BOUNDARY as a polygon.\n"
            f"Use percentage coordinates (0-100 for both x and y, where 0,0 is top-left).\n\n"
            f"Rules for polygon boundaries:\n"
            f"- Use 5-12 vertices that tightly follow the visible outline of the structure\n"
            f"- For irregular shapes, use MORE vertices to capture the contour accurately\n"
            f"- For roughly circular structures, use 6-8 vertices forming an approximate circle\n"
            f"- Vertices should be ordered clockwise\n"
            f"- Each vertex is [x, y] where x=horizontal%, y=vertical%\n\n"
            f"Return a JSON array where each element has:\n"
            f"- \"label\": the structure name (exactly as listed above)\n"
            f"- \"points\": [[x1,y1], [x2,y2], ...] polygon vertices (5-12 points, 0-100 percentage)\n"
            f"- \"description\": one sentence describing this structure's function\n\n"
            f"Return ONLY the JSON array, no markdown, no explanation."
        )

        response = self.client.models.generate_content(
            model=self.VISION_MODEL,
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip()
        zones = self._parse_json_array(raw)

        result = []
        for z in zones:
            zone_id = f"zone_{z['label'].lower().replace(' ', '_').replace('-', '_')}"
            points = z.get("points", [])

            if points and len(points) >= 3:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                max_dist = max(
                    ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
                    for px, py in points
                )
                result.append({
                    "id": zone_id,
                    "label": z["label"],
                    "points": [[float(p[0]), float(p[1])] for p in points],
                    "x": round(cx, 1),
                    "y": round(cy, 1),
                    "radius": round(max_dist, 1),
                    "center": {"x": round(cx, 1), "y": round(cy, 1)},
                    "shape": "polygon",
                    "description": z.get("description", ""),
                })
            else:
                x = float(z.get("x", 50))
                y = float(z.get("y", 50))
                radius = float(z.get("radius", 5))
                result.append({
                    "id": zone_id,
                    "label": z["label"],
                    "x": x,
                    "y": y,
                    "radius": radius,
                    "shape": "circle",
                    "description": z.get("description", ""),
                })

        logger.info(f"Text detection: {len(result)} zones ({sum(1 for z in result if z['shape'] == 'polygon')} polygons)")
        return result

    def _parse_json_array(self, raw: str) -> list:
        """Robustly parse a JSON array from possibly malformed LLM output."""
        # 1. Direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 2. Markdown code block extraction
        code_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', raw, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. Balanced bracket extraction
        first_bracket = raw.find("[")
        if first_bracket != -1:
            depth = 0
            in_string = False
            escape_next = False
            for i in range(first_bracket, len(raw)):
                c = raw[i]
                if escape_next:
                    escape_next = False
                    continue
                if c == '\\' and in_string:
                    escape_next = True
                    continue
                if c == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(raw[first_bracket:i + 1])
                        except json.JSONDecodeError:
                            break

        # 4. Simple first-[ to last-] fallback
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError(
            f"Could not extract JSON array from response (len={len(raw)})",
            raw[:200], 0
        )

    async def detect_bounding_boxes(
        self,
        image_bytes: bytes,
        expected_labels: list[str],
        context: str = "",
        model: str | None = None,
    ) -> list[dict]:
        """Detect bounding boxes using Gemini's native box_2d object detection.

        Uses the trained box_2d output format [ymin, xmin, ymax, xmax] on 0-1000 scale
        which is far more accurate than asking Gemini to guess polygon coordinates.

        Returns list of {label, box_2d, x, y, width, height} in percentage coords (0-100).
        Supports multiple instances per label (e.g., 4 mitochondria).
        """
        image = Image.open(BytesIO(image_bytes))
        labels_text = ", ".join(expected_labels)
        use_model = model or self.VISION_MODEL

        logger.info(f"Detecting bounding boxes via {use_model} for: {labels_text}")

        prompt = (
            f"Detect each of these structures in this diagram: {labels_text}\n"
            f"{f'Context: {context}' if context else ''}\n\n"
            f"Return a JSON array. For EACH visible instance of each structure, return:\n"
            f"- \"label\": exact structure name from the list above\n"
            f"- \"box_2d\": [ymin, xmin, ymax, xmax] normalized to 0-1000 scale\n\n"
            f"If a structure appears multiple times (e.g., multiple mitochondria), "
            f"return a separate entry for EACH instance.\n"
            f"Return ONLY the JSON array."
        )

        response = self.client.models.generate_content(
            model=use_model,
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip()
        detections = self._parse_json_array(raw)

        result = []
        for d in detections:
            label = d.get("label", "")
            box = d.get("box_2d")
            if not label or not box or len(box) < 4:
                continue

            # box_2d is [ymin, xmin, ymax, xmax] in 0-1000 scale → convert to percentage
            ymin, xmin, ymax, xmax = [float(v) / 10.0 for v in box[:4]]
            x_center = (xmin + xmax) / 2
            y_center = (ymin + ymax) / 2
            width = xmax - xmin
            height = ymax - ymin

            result.append({
                "label": label,
                "box_2d": [round(v, 1) for v in [ymin, xmin, ymax, xmax]],
                "x": round(x_center, 1),
                "y": round(y_center, 1),
                "width": round(width, 1),
                "height": round(height, 1),
                "radius": round(max(width, height) / 2, 1),
            })

        logger.info(f"Box detection ({use_model}): {len(result)} boxes, "
                     f"{len(set(r['label'] for r in result))} labels")
        return result

    async def trace_paths_on_diagram(
        self,
        image_bytes: bytes,
        path_description: str,
        waypoint_labels: list[str],
    ) -> list[dict]:
        """Detect path waypoints and suggest SVG path curves between them.

        Args:
            image_bytes: Diagram image bytes
            path_description: What path to trace (e.g., "blood flow through heart")
            waypoint_labels: Ordered list of waypoint names

        Returns:
            List of waypoint dicts with positions and SVG path segments
        """
        image = Image.open(BytesIO(image_bytes))
        waypoints_text = " → ".join(waypoint_labels)

        prompt = (
            f"Analyze this diagram and trace the path: {path_description}\n"
            f"Waypoints in order: {waypoints_text}\n\n"
            f"For each waypoint, provide its position (x, y as 0-100 percentage).\n"
            f"Also provide SVG path data (M/C/Q commands) for the curve from each "
            f"waypoint to the next, using the same 0-100 coordinate system.\n\n"
            f"Return a JSON array where each element has:\n"
            f"- \"label\": waypoint name\n"
            f"- \"x\": horizontal position (0-100)\n"
            f"- \"y\": vertical position (0-100)\n"
            f"- \"svg_path_to_next\": SVG path data string to the next waypoint (null for last)\n\n"
            f"Return ONLY the JSON array."
        )

        response = self.client.models.generate_content(
            model=self.VISION_MODEL,
            contents=[prompt, image],
        )

        raw = response.text.strip()
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            raw = json_match.group()

        return json.loads(raw)
