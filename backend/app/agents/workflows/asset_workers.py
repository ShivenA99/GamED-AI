"""
Asset Workers — Pluggable generation backends for AssetSpecs.

Each worker handles one or more AssetTypes. Workers are registered in
a worker registry and dispatched by the asset_orchestrator based on the
spec's `worker` field.

Worker contract:
    async def execute(spec: AssetSpec, context: WorkerContext) -> WorkerResult

WorkerResult contains the generated file path, served URL, and metadata.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.agents.schemas.asset_spec import (
    AssetSpec,
    AssetType,
    WorkerType,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.workers.asset_workers")


# ---------------------------------------------------------------------------
# Worker context and result
# ---------------------------------------------------------------------------

@dataclass
class WorkerContext:
    """Shared context for all workers in a generation run."""
    run_id: str = ""
    output_dir: str = "assets"
    base_url: str = "/api/assets"
    existing_assets: Dict[str, str] = field(default_factory=dict)  # asset_id -> path
    diagram_image_path: Optional[str] = None  # Primary diagram for zone detection
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerResult:
    """Result from a worker execution."""
    success: bool
    asset_id: str
    path: Optional[str] = None           # Local file path
    url: Optional[str] = None            # Served URL
    data: Optional[Dict[str, Any]] = None  # Structured data (for path_data, zones, etc.)
    error: Optional[str] = None
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base worker
# ---------------------------------------------------------------------------

class AssetWorker(ABC):
    """Base class for asset generation workers."""

    worker_type: WorkerType

    @abstractmethod
    async def execute(self, spec: AssetSpec, context: WorkerContext) -> WorkerResult:
        """
        Generate an asset from its spec.

        Args:
            spec: Complete asset specification
            context: Shared generation context

        Returns:
            WorkerResult with path/url/data on success, error on failure
        """
        pass

    def _make_output_path(self, spec: AssetSpec, context: WorkerContext, ext: str) -> str:
        """Generate a deterministic output path for an asset."""
        os.makedirs(context.output_dir, exist_ok=True)
        filename = f"{spec.asset_id}.{ext}"
        return os.path.join(context.output_dir, filename)

    def _make_url(self, spec: AssetSpec, context: WorkerContext, path: str) -> str:
        """Generate a served URL for an asset."""
        filename = os.path.basename(path)
        return f"{context.base_url}/{context.run_id}/{filename}"


# ---------------------------------------------------------------------------
# Image Search Worker
# ---------------------------------------------------------------------------

class ImageSearchWorker(AssetWorker):
    """Searches for diagram images from web or cached sources."""

    worker_type = WorkerType.IMAGE_SEARCH

    async def execute(self, spec: AssetSpec, context: WorkerContext) -> WorkerResult:
        start = time.monotonic()
        try:
            from app.services.image_retrieval import get_image_retrieval_service

            service = get_image_retrieval_service()
            query = spec.content.generation_prompt or spec.content.description
            if not query:
                return WorkerResult(
                    success=False,
                    asset_id=spec.asset_id,
                    error="No search query in spec content",
                )

            result = await service.search_and_download(
                query=query,
                output_dir=context.output_dir,
                filename=f"{spec.asset_id}.png",
            )

            if result and result.get("path"):
                path = result["path"]
                elapsed = (time.monotonic() - start) * 1000
                return WorkerResult(
                    success=True,
                    asset_id=spec.asset_id,
                    path=path,
                    url=self._make_url(spec, context, path),
                    latency_ms=elapsed,
                    metadata={"source": result.get("source", "web")},
                )

            return WorkerResult(
                success=False,
                asset_id=spec.asset_id,
                error="Image search returned no results",
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error(f"ImageSearchWorker failed for {spec.asset_id}: {e}")
            return WorkerResult(
                success=False,
                asset_id=spec.asset_id,
                error=str(e),
                latency_ms=elapsed,
            )


# ---------------------------------------------------------------------------
# Gemini Image Worker (generation/editing)
# ---------------------------------------------------------------------------

class GeminiImageWorker(AssetWorker):
    """Generates or edits images using Gemini Flash image model."""

    worker_type = WorkerType.GEMINI_IMAGE

    async def execute(self, spec: AssetSpec, context: WorkerContext) -> WorkerResult:
        start = time.monotonic()
        try:
            from app.services.gemini_service import get_gemini_service

            service = get_gemini_service()
            prompt = spec.content.generation_prompt or spec.content.description

            if not prompt:
                return WorkerResult(
                    success=False,
                    asset_id=spec.asset_id,
                    error="No generation prompt in spec",
                )

            # Check for reference image (editing mode)
            reference_path = spec.style.reference_image_path
            if reference_path and os.path.exists(reference_path):
                result = await service.edit_image(
                    image_path=reference_path,
                    prompt=prompt,
                    output_path=self._make_output_path(spec, context, "png"),
                )
            else:
                result = await service.generate_image(
                    prompt=prompt,
                    output_path=self._make_output_path(spec, context, "png"),
                )

            if result and result.get("path"):
                path = result["path"]
                elapsed = (time.monotonic() - start) * 1000
                return WorkerResult(
                    success=True,
                    asset_id=spec.asset_id,
                    path=path,
                    url=self._make_url(spec, context, path),
                    latency_ms=elapsed,
                    cost_usd=0.04,
                )

            return WorkerResult(
                success=False,
                asset_id=spec.asset_id,
                error="Gemini image generation returned no result",
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error(f"GeminiImageWorker failed for {spec.asset_id}: {e}")
            return WorkerResult(
                success=False,
                asset_id=spec.asset_id,
                error=str(e),
                latency_ms=elapsed,
            )


# ---------------------------------------------------------------------------
# Zone Detector Worker
# ---------------------------------------------------------------------------

class ZoneDetectorWorker(AssetWorker):
    """Detects zones (polygons) on a diagram image using Gemini vision."""

    worker_type = WorkerType.ZONE_DETECTOR

    async def execute(self, spec: AssetSpec, context: WorkerContext) -> WorkerResult:
        start = time.monotonic()
        try:
            # Find the diagram image to detect zones on
            diagram_path = context.diagram_image_path
            if not diagram_path:
                # Try to find from existing assets
                for aid, path in context.existing_assets.items():
                    if "diagram" in aid or "img_" in aid:
                        diagram_path = path
                        break

            if not diagram_path or not os.path.exists(diagram_path):
                return WorkerResult(
                    success=False,
                    asset_id=spec.asset_id,
                    error="No diagram image found for zone detection",
                )

            zone_labels = spec.content.zone_labels
            if not zone_labels:
                return WorkerResult(
                    success=False,
                    asset_id=spec.asset_id,
                    error="No zone_labels in spec content",
                )

            from app.agents.gemini_zone_detector import detect_zones_gemini

            zones = await detect_zones_gemini(
                image_path=diagram_path,
                labels=zone_labels,
                hints=spec.content.zone_hints or {},
            )

            elapsed = (time.monotonic() - start) * 1000

            if zones:
                return WorkerResult(
                    success=True,
                    asset_id=spec.asset_id,
                    data={"zones": zones},
                    latency_ms=elapsed,
                    cost_usd=0.01,
                    metadata={"detected_count": len(zones), "expected_count": len(zone_labels)},
                )

            return WorkerResult(
                success=False,
                asset_id=spec.asset_id,
                error="Zone detection returned no zones",
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error(f"ZoneDetectorWorker failed for {spec.asset_id}: {e}")
            return WorkerResult(
                success=False,
                asset_id=spec.asset_id,
                error=str(e),
                latency_ms=elapsed,
            )


# ---------------------------------------------------------------------------
# CSS Animation Worker (deterministic)
# ---------------------------------------------------------------------------

class CSSAnimationWorker(AssetWorker):
    """Generates CSS keyframe animations deterministically — no API call."""

    worker_type = WorkerType.CSS_ANIMATION

    # Animation templates
    ANIMATION_TEMPLATES = {
        "pulse": """@keyframes {name} {{
  0%, 100% {{ transform: scale(1); opacity: 1; }}
  50% {{ transform: scale(1.05); opacity: 0.8; }}
}}""",
        "shake": """@keyframes {name} {{
  0%, 100% {{ transform: translateX(0); }}
  10%, 30%, 50%, 70%, 90% {{ transform: translateX(-4px); }}
  20%, 40%, 60%, 80% {{ transform: translateX(4px); }}
}}""",
        "glow": """@keyframes {name} {{
  0%, 100% {{ box-shadow: 0 0 5px {color}40; }}
  50% {{ box-shadow: 0 0 20px {color}80, 0 0 30px {color}40; }}
}}""",
        "bounce": """@keyframes {name} {{
  0% {{ transform: scale(0.8); opacity: 0; }}
  60% {{ transform: scale(1.1); opacity: 1; }}
  100% {{ transform: scale(1); }}
}}""",
        "fade_in": """@keyframes {name} {{
  0% {{ opacity: 0; }}
  100% {{ opacity: 1; }}
}}""",
        "confetti": """@keyframes {name} {{
  0% {{ transform: translateY(0) rotate(0deg); opacity: 1; }}
  100% {{ transform: translateY(-100vh) rotate(720deg); opacity: 0; }}
}}""",
        "slide_in": """@keyframes {name} {{
  0% {{ transform: translateX(-20px); opacity: 0; }}
  100% {{ transform: translateX(0); opacity: 1; }}
}}""",
    }

    async def execute(self, spec: AssetSpec, context: WorkerContext) -> WorkerResult:
        start = time.monotonic()

        anim_type = spec.content.animation_type or "pulse"
        name = spec.asset_id.replace("-", "_")
        color = "#22c55e"  # Default green

        if spec.style.color_palette:
            color = spec.style.color_palette.get("success", color)

        template = self.ANIMATION_TEMPLATES.get(anim_type, self.ANIMATION_TEMPLATES["pulse"])
        css = template.format(name=name, color=color)

        # Add animation shorthand
        duration = spec.content.duration_ms or 600
        easing = spec.content.easing or "ease-in-out"
        trigger = spec.content.trigger or "on_event"

        animation_data = {
            "keyframes": css,
            "animation": f"{name} {duration}ms {easing}",
            "trigger": trigger,
            "type": anim_type,
        }

        # Write CSS file
        output_path = self._make_output_path(spec, context, "css")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(css)

        elapsed = (time.monotonic() - start) * 1000

        return WorkerResult(
            success=True,
            asset_id=spec.asset_id,
            path=output_path,
            url=self._make_url(spec, context, output_path),
            data=animation_data,
            latency_ms=elapsed,
            cost_usd=0.0,
        )


# ---------------------------------------------------------------------------
# Audio Worker
# ---------------------------------------------------------------------------

class AudioWorker(AssetWorker):
    """Generates sound effects. Falls back to preset sounds."""

    worker_type = WorkerType.AUDIO_GEN

    # Preset sound URLs for common events
    PRESET_SOUNDS = {
        "correct": "/sounds/correct.mp3",
        "incorrect": "/sounds/incorrect.mp3",
        "complete": "/sounds/complete.mp3",
        "click": "/sounds/click.mp3",
        "drop": "/sounds/drop.mp3",
        "reveal": "/sounds/reveal.mp3",
        "transition": "/sounds/transition.mp3",
        "tick": "/sounds/tick.mp3",
    }

    async def execute(self, spec: AssetSpec, context: WorkerContext) -> WorkerResult:
        start = time.monotonic()

        sound_event = spec.content.sound_event or ""

        # Check presets first
        for key, url in self.PRESET_SOUNDS.items():
            if key in sound_event.lower() or key in spec.asset_id.lower():
                elapsed = (time.monotonic() - start) * 1000
                return WorkerResult(
                    success=True,
                    asset_id=spec.asset_id,
                    url=url,
                    data={"source": "preset", "event": key},
                    latency_ms=elapsed,
                    cost_usd=0.0,
                )

        # Fallback: try ElevenLabs SFX if available
        try:
            from app.services.media_generation_service import get_media_service

            service = get_media_service()
            description = spec.content.sound_description or spec.content.description or sound_event
            result = await service.generate_sound_effect(
                description=description,
                output_path=self._make_output_path(spec, context, "mp3"),
            )
            if result and result.get("path"):
                elapsed = (time.monotonic() - start) * 1000
                return WorkerResult(
                    success=True,
                    asset_id=spec.asset_id,
                    path=result["path"],
                    url=self._make_url(spec, context, result["path"]),
                    latency_ms=elapsed,
                    cost_usd=0.01,
                )
        except (ImportError, Exception) as e:
            logger.debug(f"AudioWorker: Media service unavailable, using preset fallback: {e}")

        # Final fallback
        elapsed = (time.monotonic() - start) * 1000
        return WorkerResult(
            success=True,
            asset_id=spec.asset_id,
            url=self.PRESET_SOUNDS.get("click", "/sounds/click.mp3"),
            data={"source": "preset", "event": "fallback"},
            latency_ms=elapsed,
            cost_usd=0.0,
        )


# ---------------------------------------------------------------------------
# Path Worker
# ---------------------------------------------------------------------------

class PathWorker(AssetWorker):
    """Generates path waypoint data from zone positions or Gemini vision."""

    worker_type = WorkerType.PATH_GEN

    async def execute(self, spec: AssetSpec, context: WorkerContext) -> WorkerResult:
        start = time.monotonic()

        waypoint_labels = spec.content.waypoint_labels
        if not waypoint_labels:
            return WorkerResult(
                success=False,
                asset_id=spec.asset_id,
                error="No waypoint_labels in spec content",
            )

        # Try to derive path from existing zone data
        zone_data = context.config.get("zone_data", {})
        waypoints = []

        for label in waypoint_labels:
            zone = zone_data.get(label)
            if zone:
                # Use zone center as waypoint
                coords = zone.get("coordinates", zone.get("polygon", []))
                if coords:
                    cx = sum(p[0] for p in coords) / len(coords) if coords else 50
                    cy = sum(p[1] for p in coords) / len(coords) if coords else 50
                    waypoints.append({
                        "label": label,
                        "x": round(cx, 1),
                        "y": round(cy, 1),
                        "order": len(waypoints),
                    })

        if not waypoints:
            # No zone data — generate placeholder waypoints
            for i, label in enumerate(waypoint_labels):
                waypoints.append({
                    "label": label,
                    "x": 20 + (i * 60 / max(len(waypoint_labels) - 1, 1)),
                    "y": 50,
                    "order": i,
                })

        path_data = {
            "waypoints": waypoints,
            "path_type": spec.content.path_type or "linear",
            "total_waypoints": len(waypoints),
        }

        # Write path JSON
        output_path = self._make_output_path(spec, context, "json")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(path_data, f, indent=2)

        elapsed = (time.monotonic() - start) * 1000
        return WorkerResult(
            success=True,
            asset_id=spec.asset_id,
            path=output_path,
            data=path_data,
            latency_ms=elapsed,
            cost_usd=0.0,
        )


# ---------------------------------------------------------------------------
# Click Target Worker (deterministic)
# ---------------------------------------------------------------------------

class ClickTargetWorker(AssetWorker):
    """Generates click target regions from zone data."""

    worker_type = WorkerType.CLICK_TARGET_GEN

    async def execute(self, spec: AssetSpec, context: WorkerContext) -> WorkerResult:
        start = time.monotonic()

        click_options = spec.content.click_options
        correct_assignments = spec.content.correct_assignments

        if not click_options:
            return WorkerResult(
                success=False,
                asset_id=spec.asset_id,
                error="No click_options in spec content",
            )

        # Build click target definitions
        targets = []
        zone_data = context.config.get("zone_data", {})

        for label, option in correct_assignments.items():
            zone = zone_data.get(label, {})
            targets.append({
                "label": label,
                "correct_option": option,
                "zone_id": zone.get("id", label.lower().replace(" ", "_")),
            })

        target_data = {
            "options": click_options,
            "targets": targets,
            "total_targets": len(targets),
        }

        output_path = self._make_output_path(spec, context, "json")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(target_data, f, indent=2)

        elapsed = (time.monotonic() - start) * 1000
        return WorkerResult(
            success=True,
            asset_id=spec.asset_id,
            path=output_path,
            data=target_data,
            latency_ms=elapsed,
            cost_usd=0.0,
        )


# ---------------------------------------------------------------------------
# Noop Worker
# ---------------------------------------------------------------------------

class NoopWorker(AssetWorker):
    """No-op worker for assets that don't need generation (cached/preset)."""

    worker_type = WorkerType.NOOP

    async def execute(self, spec: AssetSpec, context: WorkerContext) -> WorkerResult:
        return WorkerResult(
            success=True,
            asset_id=spec.asset_id,
            data={"source": "noop"},
            latency_ms=0.0,
            cost_usd=0.0,
        )


# ---------------------------------------------------------------------------
# Worker Registry
# ---------------------------------------------------------------------------

class WorkerRegistry:
    """Registry mapping WorkerType to worker instances."""

    _workers: Dict[WorkerType, AssetWorker]

    def __init__(self):
        self._workers = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register all built-in workers."""
        defaults = [
            ImageSearchWorker(),
            GeminiImageWorker(),
            ZoneDetectorWorker(),
            CSSAnimationWorker(),
            AudioWorker(),
            PathWorker(),
            ClickTargetWorker(),
            NoopWorker(),
        ]
        for w in defaults:
            self._workers[w.worker_type] = w

    def register(self, worker: AssetWorker) -> None:
        """Register a custom worker."""
        self._workers[worker.worker_type] = worker

    def get(self, worker_type: WorkerType) -> Optional[AssetWorker]:
        """Get a worker by type."""
        return self._workers.get(worker_type)

    def list_types(self) -> List[WorkerType]:
        """List all registered worker types."""
        return list(self._workers.keys())


_registry: Optional[WorkerRegistry] = None


def get_worker_registry() -> WorkerRegistry:
    """Get or create the singleton worker registry."""
    global _registry
    if _registry is None:
        _registry = WorkerRegistry()
    return _registry


# ---------------------------------------------------------------------------
# Manifest executor
# ---------------------------------------------------------------------------

async def execute_manifest(
    manifest: "AssetManifest",
    context: WorkerContext,
    max_concurrent: int = 3,
    on_progress: Optional["Callable"] = None,
) -> Dict[str, WorkerResult]:
    """
    Execute all specs in a manifest respecting dependencies and ordering.

    Args:
        manifest: The asset manifest with specs and ordering
        context: Shared worker context
        max_concurrent: Maximum concurrent workers (unused currently, sequential)
        on_progress: Optional async callback(asset_id, status, detail) for streaming progress

    Returns dict of asset_id -> WorkerResult.
    """
    from app.agents.schemas.asset_spec import AssetManifest

    registry = get_worker_registry()
    results: Dict[str, WorkerResult] = {}
    completed_ids: set = set()

    # Process in generation_order first, then remaining
    ordered_ids = list(manifest.generation_order)
    remaining = [aid for aid in manifest.specs if aid not in ordered_ids]
    all_ids = ordered_ids + remaining

    for asset_id in all_ids:
        spec = manifest.get_spec(asset_id)
        if not spec:
            continue

        # Wait for dependencies
        for dep_id in spec.depends_on:
            if dep_id not in completed_ids:
                dep_result = results.get(dep_id)
                if dep_result and dep_result.success:
                    completed_ids.add(dep_id)

        # Get worker
        worker = registry.get(spec.worker)
        if not worker:
            logger.warning(f"No worker for {spec.worker.value}, using noop")
            worker = registry.get(WorkerType.NOOP) or NoopWorker()

        # Execute
        try:
            logger.info(f"Executing {spec.worker.value} for {asset_id}")
            if on_progress:
                await on_progress(asset_id, "started", f"Worker: {spec.worker.value}")
            result = await worker.execute(spec, context)
            results[asset_id] = result

            if result.success:
                completed_ids.add(asset_id)
                manifest.mark_completed(asset_id, result.path or "", result.url)
                if result.path:
                    context.existing_assets[asset_id] = result.path
                if on_progress:
                    await on_progress(asset_id, "complete", f"{spec.worker.value} succeeded ({result.latency_ms:.0f}ms)")
            else:
                # Try fallback worker
                if spec.fallback_worker:
                    fallback = registry.get(spec.fallback_worker)
                    if fallback:
                        logger.info(f"Trying fallback {spec.fallback_worker.value} for {asset_id}")
                        if on_progress:
                            await on_progress(asset_id, "fallback", f"Trying {spec.fallback_worker.value}")
                        result = await fallback.execute(spec, context)
                        results[asset_id] = result
                        if result.success:
                            completed_ids.add(asset_id)
                            manifest.mark_completed(asset_id, result.path or "", result.url)
                            if result.path:
                                context.existing_assets[asset_id] = result.path

                if not result.success:
                    manifest.mark_failed(asset_id, result.error or "Unknown error")
                    if on_progress:
                        await on_progress(asset_id, "failed", result.error or "Unknown error")

        except Exception as e:
            logger.error(f"Worker execution failed for {asset_id}: {e}")
            results[asset_id] = WorkerResult(
                success=False,
                asset_id=asset_id,
                error=str(e),
            )
            manifest.mark_failed(asset_id, str(e))
            if on_progress:
                await on_progress(asset_id, "error", str(e))

    return results
