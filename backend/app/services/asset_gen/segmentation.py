"""Local SAM3 segmentation service for zone detection.

Uses Meta's SAM3 via MLX on Apple Silicon for pixel-precise zone boundaries.
Supports three modes:
  1. Text-only: SAM3 text prompt per label (unreliable for complex diagrams)
  2. Gemini-guided: Gemini provides bounding boxes → SAM3 uses text + box prompt
     for pixel-precise segmentation within the guided region
  3. Box-only: Gemini boxes used as geometric prompts without text

Falls back gracefully (returns None) if SAM3/MLX is unavailable.
"""

import asyncio
import logging
import math
import threading
import time
from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger("gamed_ai.asset_gen.segmentation")

# Serialize SAM3 Metal GPU access — concurrent backbone computations crash on Apple Silicon.
# Only 1 SAM3 inference (backbone + prompts) may run at a time.
_SAM3_SEMAPHORE = asyncio.Semaphore(1)

# ── SAM3 status tracker (read by /health/sam3 endpoint) ──────────────────────
_sam3_status = {
    "state": "idle",           # idle | loading | busy | error
    "model_loaded": False,
    "current_scene": None,     # scene_id being processed
    "current_mode": None,      # "text-only" | "guided"
    "current_label": None,     # label currently being segmented
    "queue_waiting": 0,        # coroutines waiting on semaphore
    "total_calls": 0,
    "total_completed": 0,
    "total_errors": 0,
    "last_error": None,
    "last_backbone_ms": None,
    "last_prompt_ms": None,
    "last_completed_at": None,
    "busy_since": None,        # timestamp when current inference started
    "executor_thread": None,   # thread name running GPU work
}
_status_lock = threading.Lock()


def get_sam3_status() -> dict:
    """Return a snapshot of SAM3 status for the health endpoint."""
    with _status_lock:
        snap = dict(_sam3_status)
    # Add derived fields
    if snap["busy_since"]:
        snap["busy_duration_s"] = round(time.time() - snap["busy_since"], 1)
    else:
        snap["busy_duration_s"] = 0
    return snap


def _update_status(**kwargs):
    with _status_lock:
        _sam3_status.update(kwargs)


def _mask_to_polygon(
    mask: np.ndarray,
    simplify_tolerance: float = 0.5,
    min_points: int = 8,
    max_points: int = 100,
) -> Optional[list[list[float]]]:
    """Convert binary mask to polygon using OpenCV contours + Douglas-Peucker.

    Returns list of [x, y] pairs as percentages (0-100), or None.
    """
    try:
        import cv2
    except ImportError:
        return None

    if mask is None or mask.size == 0:
        return None

    if mask.dtype == bool:
        mask_u8 = mask.astype(np.uint8) * 255
    else:
        mask_u8 = (mask * 255).astype(np.uint8) if mask.max() <= 1 else mask.astype(np.uint8)

    contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 100:
        return None

    perimeter = cv2.arcLength(largest, True)
    epsilon = simplify_tolerance * perimeter / 100
    simplified = cv2.approxPolyDP(largest, epsilon, True)

    while len(simplified) > max_points and epsilon < perimeter / 10:
        epsilon *= 1.5
        simplified = cv2.approxPolyDP(largest, epsilon, True)
    while len(simplified) < min_points and epsilon > 0.1:
        epsilon *= 0.5
        simplified = cv2.approxPolyDP(largest, epsilon, True)

    h, w = mask.shape[:2]
    return [
        [round(float(pt[0][0]) / w * 100, 1), round(float(pt[0][1]) / h * 100, 1)]
        for pt in simplified
    ]


class LocalSegmentationService:
    """Thin adapter around SAM3MLXService for the asset_gen pipeline."""

    def __init__(self):
        self._sam3 = None

    def _ensure_loaded(self):
        if self._sam3 is not None:
            return
        from app.services.sam3_mlx_service import get_sam3_mlx_service
        self._sam3 = get_sam3_mlx_service()

    def _extract_mask_from_result(self, result: dict, image_size: tuple[int, int]) -> Optional[np.ndarray]:
        """Extract binary mask from SAM3 result, handling both instance masks and semantic seg."""
        img_w, img_h = image_size

        # Try instance masks first (from box/geometric prompts)
        masks = result.get("masks")
        if masks is not None:
            masks_np = np.array(masks)
            if masks_np.size > 0:
                # Take highest-confidence mask
                scores = result.get("scores")
                if scores is not None:
                    scores_np = np.array(scores)
                    if scores_np.size > 0:
                        best_idx = int(np.argmax(scores_np))
                        mask = masks_np[best_idx]
                    else:
                        mask = masks_np[0]
                else:
                    mask = masks_np[0]

                # Remove extra dims
                while mask.ndim > 2:
                    mask = mask[0]

                binary = mask > 0.5 if mask.dtype in (np.float32, np.float64) else mask.astype(bool)
                if np.any(binary):
                    if binary.shape != (img_h, img_w):
                        mask_pil = Image.fromarray(binary.astype(np.uint8) * 255)
                        mask_pil = mask_pil.resize((img_w, img_h), Image.BILINEAR)
                        binary = np.array(mask_pil) > 127
                    return binary

        # Fall back to semantic segmentation
        seg = result.get("semantic_seg")
        if seg is None:
            return None

        seg_np = np.array(seg)
        if seg_np.ndim == 4:
            seg_np = seg_np[0, 0]
        elif seg_np.ndim == 3:
            seg_np = seg_np[0]

        probs = 1.0 / (1.0 + np.exp(-seg_np.astype(np.float32)))
        binary = probs > 0.5

        if not np.any(binary):
            return None

        if binary.shape != (img_h, img_w):
            mask_pil = Image.fromarray(binary.astype(np.uint8) * 255)
            mask_pil = mask_pil.resize((img_w, img_h), Image.BILINEAR)
            binary = np.array(mask_pil) > 127

        return binary

    def _mask_to_zone(self, binary: np.ndarray, label: str) -> Optional[dict]:
        """Convert a binary mask to a zone dict."""
        polygon = _mask_to_polygon(binary)
        if not polygon or len(polygon) < 3:
            return None

        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        cx = round(sum(xs) / len(xs), 1)
        cy = round(sum(ys) / len(ys), 1)
        max_dist = round(max(math.hypot(px - cx, py - cy) for px, py in polygon), 1)

        zone_id = f"zone_{label.lower().replace(' ', '_').replace('-', '_')}"
        return {
            "id": zone_id,
            "label": label,
            "points": polygon,
            "x": cx,
            "y": cy,
            "radius": max_dist,
            "center": {"x": cx, "y": cy},
            "shape": "polygon",
            "description": "",
        }

    def _compute_backbone(self, image: Image.Image) -> dict:
        """Compute SAM3 backbone features ONCE for an image.

        This is the expensive step (~2-4s). The returned state can be reused
        for multiple text/box prompts via reset_all_prompts() which preserves
        backbone_out but clears prompt-specific data.
        """
        tid = threading.current_thread().name
        _update_status(executor_thread=tid)
        logger.info(f"[SAM3:backbone] Starting on thread={tid}")
        t0 = time.time()
        self._sam3._ensure_loaded()
        state = self._sam3._processor.set_image(image)
        elapsed = int((time.time() - t0) * 1000)
        logger.info(f"[SAM3:backbone] Completed in {elapsed}ms on thread={tid}")
        return state

    def _run_text_prompt(self, state: dict, label: str) -> dict:
        """Run a text prompt against cached backbone features."""
        processor = self._sam3._processor
        processor.reset_all_prompts(state)
        state = processor.set_text_prompt(prompt=label, state=state)
        return state

    def _run_guided_prompt(self, state: dict, label: str, sam_box: list) -> dict:
        """Run text + box prompt against cached backbone features."""
        processor = self._sam3._processor
        processor.reset_all_prompts(state)
        state = processor.set_text_prompt(prompt=label, state=state)
        state = processor.add_geometric_prompt(box=sam_box, label=True, state=state)
        return state

    @staticmethod
    def _box_from_guide(box_info: dict) -> list[float]:
        """Convert guide box (percentage coords) to SAM3 format [cx, cy, w, h] normalized 0-1."""
        bx = box_info["x"] / 100.0
        by = box_info["y"] / 100.0

        if "width" in box_info:
            # top-left + size format → center format
            bw = box_info["width"] / 100.0
            bh = box_info["height"] / 100.0
            cx = bx + bw / 2
            cy = by + bh / 2
        else:
            # center + radius format (from Gemini text zone)
            cx = bx
            cy = by
            radius = box_info.get("radius", 10) / 100.0
            bw = radius * 2
            bh = radius * 2

        return [cx, cy, bw, bh]

    async def detect_zones(
        self,
        image_bytes: bytes,
        expected_labels: list[str],
        context: str = "",
        scene_id: str = "unknown",
    ) -> list[dict] | None:
        """Detect zones using local SAM3 text-prompted segmentation (no guidance).

        Computes backbone features ONCE, then runs each label as a text prompt.
        Much faster and lower memory than recomputing per label.

        Returns a list of zone dicts, or None if SAM3 is unavailable.
        """
        try:
            self._ensure_loaded()
            _update_status(model_loaded=True)
        except Exception as e:
            logger.info(f"SAM3 not available: {e}")
            _update_status(state="error", last_error=str(e))
            return None

        _update_status(queue_waiting=_sam3_status["queue_waiting"] + 1)
        logger.info(f"[SAM3:{scene_id}] Waiting for semaphore (queue={_sam3_status['queue_waiting']})")
        sem_wait_start = time.time()

        async with _SAM3_SEMAPHORE:
            sem_wait_ms = int((time.time() - sem_wait_start) * 1000)
            _update_status(
                queue_waiting=max(0, _sam3_status["queue_waiting"] - 1),
                state="busy",
                current_scene=scene_id,
                current_mode="text-only",
                busy_since=time.time(),
                total_calls=_sam3_status["total_calls"] + 1,
            )
            logger.info(f"[SAM3:{scene_id}] Semaphore acquired after {sem_wait_ms}ms "
                        f"(queue_remaining={_sam3_status['queue_waiting']})")

            try:
                image = Image.open(BytesIO(image_bytes)).convert("RGB")
                img_w, img_h = image.size
                loop = asyncio.get_event_loop()

                # Compute backbone ONCE (expensive ~2-4s)
                t_backbone = time.time()
                _update_status(current_label="<backbone>")
                logger.info(f"[SAM3:{scene_id}] Computing backbone ({img_w}x{img_h})... "
                            f"thread={threading.current_thread().name}")
                state = await loop.run_in_executor(None, self._compute_backbone, image)
                backbone_ms = int((time.time() - t_backbone) * 1000)
                _update_status(last_backbone_ms=backbone_ms)
                logger.info(f"[SAM3:{scene_id}] Backbone ready in {backbone_ms}ms")

                zones: list[dict] = []
                for i, label in enumerate(expected_labels):
                    try:
                        t_prompt = time.time()
                        _update_status(current_label=f"{label} ({i+1}/{len(expected_labels)})")
                        state = await loop.run_in_executor(
                            None, self._run_text_prompt, state, label
                        )
                        prompt_ms = int((time.time() - t_prompt) * 1000)
                        _update_status(last_prompt_ms=prompt_ms)

                        binary = self._extract_mask_from_result(state, (img_w, img_h))
                        if binary is None:
                            logger.info(f"[SAM3:{scene_id}] '{label}' → no mask ({prompt_ms}ms)")
                            continue
                        zone = self._mask_to_zone(binary, label)
                        if zone:
                            zones.append(zone)
                            logger.info(f"[SAM3:{scene_id}] '{label}' → {len(zone['points'])}-pt polygon ({prompt_ms}ms)")
                    except Exception as e:
                        logger.warning(f"[SAM3:{scene_id}] text-only failed for '{label}': {e}")

                self._cleanup_state(state)
                _update_status(
                    state="idle",
                    current_scene=None,
                    current_mode=None,
                    current_label=None,
                    busy_since=None,
                    total_completed=_sam3_status["total_completed"] + 1,
                    last_completed_at=time.time(),
                )

                if not zones:
                    logger.warning(f"[SAM3:{scene_id}] text-only: 0/{len(expected_labels)} zones")
                    return None
                logger.info(f"[SAM3:{scene_id}] text-only: {len(zones)}/{len(expected_labels)} zones")
                return zones

            except Exception as e:
                _update_status(
                    state="error",
                    current_scene=None,
                    busy_since=None,
                    total_errors=_sam3_status["total_errors"] + 1,
                    last_error=f"{scene_id}: {e}",
                )
                logger.error(f"[SAM3:{scene_id}] text-only crashed: {e}", exc_info=True)
                raise

    async def detect_zones_guided(
        self,
        image_bytes: bytes,
        expected_labels: list[str],
        guide_boxes: dict[str, dict],
        context: str = "",
        scene_id: str = "unknown",
    ) -> list[dict] | None:
        """Detect zones using Gemini-guided SAM3: text prompt + bounding box.

        Computes backbone ONCE, then for each label:
          1. reset_all_prompts (preserves backbone)
          2. set_text_prompt (semantic guidance)
          3. add_geometric_prompt (spatial guidance from Gemini)

        This gives pixel-precise boundaries guided to the correct region.

        Args:
            image_bytes: Source diagram PNG/JPG
            expected_labels: Labels to detect
            guide_boxes: Map of label → {x, y, radius} or {x, y, width, height}
                         in percentage coords (0-100).
            context: Optional context string
            scene_id: For logging/status tracking

        Returns:
            List of zone dicts with pixel-precise polygon boundaries, or None.
        """
        try:
            self._ensure_loaded()
            _update_status(model_loaded=True)
        except Exception as e:
            logger.info(f"SAM3 not available: {e}")
            _update_status(state="error", last_error=str(e))
            return None

        _update_status(queue_waiting=_sam3_status["queue_waiting"] + 1)
        logger.info(f"[SAM3:{scene_id}] Waiting for semaphore (queue={_sam3_status['queue_waiting']})")
        sem_wait_start = time.time()

        async with _SAM3_SEMAPHORE:
            sem_wait_ms = int((time.time() - sem_wait_start) * 1000)
            _update_status(
                queue_waiting=max(0, _sam3_status["queue_waiting"] - 1),
                state="busy",
                current_scene=scene_id,
                current_mode="guided",
                busy_since=time.time(),
                total_calls=_sam3_status["total_calls"] + 1,
            )
            logger.info(f"[SAM3:{scene_id}] Semaphore acquired after {sem_wait_ms}ms "
                        f"(queue_remaining={_sam3_status['queue_waiting']})")

            try:
                image = Image.open(BytesIO(image_bytes)).convert("RGB")
                img_w, img_h = image.size
                loop = asyncio.get_event_loop()

                # Compute backbone ONCE
                t_backbone = time.time()
                _update_status(current_label="<backbone>")
                logger.info(f"[SAM3:{scene_id}] Computing backbone ({img_w}x{img_h})... "
                            f"thread={threading.current_thread().name}")
                state = await loop.run_in_executor(None, self._compute_backbone, image)
                backbone_ms = int((time.time() - t_backbone) * 1000)
                _update_status(last_backbone_ms=backbone_ms)
                logger.info(f"[SAM3:{scene_id}] Backbone ready in {backbone_ms}ms")

                zones: list[dict] = []
                for i, label in enumerate(expected_labels):
                    box_info = guide_boxes.get(label)
                    if not box_info:
                        logger.warning(f"[SAM3:{scene_id}] No guide box for '{label}', skipping")
                        continue

                    try:
                        sam_box = self._box_from_guide(box_info)

                        t_prompt = time.time()
                        _update_status(current_label=f"{label} ({i+1}/{len(expected_labels)})")
                        state = await loop.run_in_executor(
                            None, self._run_guided_prompt, state, label, sam_box
                        )
                        prompt_ms = int((time.time() - t_prompt) * 1000)
                        _update_status(last_prompt_ms=prompt_ms)

                        binary = self._extract_mask_from_result(state, (img_w, img_h))
                        if binary is None:
                            logger.warning(f"[SAM3:{scene_id}] guided: no mask for '{label}' ({prompt_ms}ms)")
                            continue

                        zone = self._mask_to_zone(binary, label)
                        if zone:
                            zones.append(zone)
                            logger.info(
                                f"[SAM3:{scene_id}] guided '{label}' → {len(zone['points'])}-pt polygon "
                                f"({prompt_ms}ms, box: {sam_box[0]:.2f},{sam_box[1]:.2f} "
                                f"{sam_box[2]:.2f}x{sam_box[3]:.2f})"
                            )

                    except Exception as e:
                        logger.warning(f"[SAM3:{scene_id}] guided failed for '{label}': {e}")

                self._cleanup_state(state)
                _update_status(
                    state="idle",
                    current_scene=None,
                    current_mode=None,
                    current_label=None,
                    busy_since=None,
                    total_completed=_sam3_status["total_completed"] + 1,
                    last_completed_at=time.time(),
                )

                if not zones:
                    logger.warning(f"[SAM3:{scene_id}] guided: 0/{len(expected_labels)} zones")
                    return None
                logger.info(f"[SAM3:{scene_id}] guided: {len(zones)}/{len(expected_labels)} zones")
                return zones

            except Exception as e:
                _update_status(
                    state="error",
                    current_scene=None,
                    busy_since=None,
                    total_errors=_sam3_status["total_errors"] + 1,
                    last_error=f"{scene_id}: {e}",
                )
                logger.error(f"[SAM3:{scene_id}] guided crashed: {e}", exc_info=True)
                raise

    @staticmethod
    def _cleanup_state(state: dict):
        """Free memory from SAM3 inference state."""
        import gc
        keys_to_clear = ["masks", "mask_logits", "scores", "boxes", "semantic_seg", "backbone_out"]
        for k in keys_to_clear:
            state.pop(k, None)
        gc.collect()
        try:
            import mlx.core as mx
            mx.clear_cache()
        except Exception:
            pass
