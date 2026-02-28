"""
ZONE_PLANNER - HAD Vision Cluster Orchestrator (v3 Gemini-Only)

Coordinates image acquisition and zone detection with hierarchical awareness.
Uses direct Gemini vision calls with polygon zone detection.

HAD v3 Architecture: Simplified Gemini-Only Zone Detection
- Direct Gemini vision call with polygon output (no SAM/Qwen dependencies)
- Self-validation in prompt (reduces retry loops)
- Relationship-aware detection strategy

v3 Improvements over v2:
- Single layer of zone detection (direct Gemini service call)
- Polygon zones by default (not circles)
- Model selection per task (cost optimization)
- Self-validation in prompt

Inputs from Research Cluster:
    - canonical_labels: From domain_knowledge
    - hierarchical_relationships: From domain_knowledge (with relationship_type)
    - subject: From pedagogical_context

Outputs to Design Cluster:
    - diagram_zones: Detected zones with polygon positions
    - zone_groups: Hierarchical groupings
    - generated_diagram_path or diagram_image: Image path/URL
    - zone_detection_metadata: Detection details and validation results
    - detection_trace: List of reasoning traces for UI visualization
"""

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.had.vision_tools import (
    search_images,
    detect_zones,
    validate_spatial_coherence,
)
from app.agents.had.spatial_validator import (
    validate_hierarchical_spatial_coherence,
    generate_corrective_prompt,
)
from app.agents.had.zone_collision_resolver import (
    ZoneCollisionResolver,
    resolve_zone_overlaps,
)
from app.agents.had.temporal_resolver import (
    generate_temporal_constraints,
    constraints_to_dict_list,
)
from app.agents.had.react_loop import TraceBuilder, ReActTrace
from app.utils.logging_config import get_logger

# HAD v3: Import Gemini service for direct zone detection
try:
    from app.services.gemini_service import (
        get_gemini_service,
        GeminiModel,
        ZoneDetectionResult,
    )
    GEMINI_SERVICE_AVAILABLE = True
except ImportError:
    GEMINI_SERVICE_AVAILABLE = False

logger = get_logger("gamed_ai.agents.had.zone_planner")

# Configuration
MAX_DETECTION_RETRIES = 3
MAX_IMAGE_SEARCH_RETRIES = 2

# HAD v3: Use direct Gemini service for zone detection (set to True for v3)
USE_GEMINI_DIRECT = os.environ.get("HAD_USE_GEMINI_DIRECT", "true").lower() == "true"

# Multi-scene thresholds
MULTI_SCENE_LABEL_THRESHOLD = 12
MULTI_SCENE_HIERARCHY_DEPTH_THRESHOLD = 2


async def zone_planner(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> dict:
    """
    HAD Vision Cluster: Orchestrates image acquisition and zone detection.

    HAD v3 Enhancements:
    - Multi-scene support with per-scene image acquisition
    - Zone collision resolution based on relationship types
    - Query-intent aware zone detection
    - Scene transition planning

    This orchestrator spawns worker-like processes for:
    1. Image acquisition (search or generation)
    2. Zone detection with hierarchical awareness
    3. Spatial validation with potential retry
    4. Zone collision resolution (NEW in v3)

    The key improvement over flat pipeline:
    - Hierarchical relationships are passed to detection
    - Detection strategy adapts to relationship_type
    - Self-correction via validation and retry
    - Automatic multi-scene handling for complex diagrams
    """
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")

    logger.info(f"ZONE_PLANNER starting for {question_id}, template={template_type}")

    # Only process INTERACTIVE_DIAGRAM templates
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"Skipping zone_planner for non-INTERACTIVE_DIAGRAM template: {template_type}")
        return {
            "current_agent": "zone_planner",
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    # Extract inputs from Research Cluster
    domain_knowledge = state.get("domain_knowledge", {}) or {}
    canonical_labels = list(domain_knowledge.get("canonical_labels", []) or [])
    hierarchical_relationships = domain_knowledge.get("hierarchical_relationships", [])

    # HAD v3: Extract query intent for zone detection strategy
    query_intent = domain_knowledge.get("query_intent", {})
    suggested_reveal_order = domain_knowledge.get("suggested_reveal_order", [])
    scene_hints = domain_knowledge.get("scene_hints", [])

    pedagogical_context = state.get("pedagogical_context", {}) or {}
    subject = pedagogical_context.get("subject", "")

    question_text = state.get("question_text", "")

    if not canonical_labels:
        logger.warning("No canonical labels found")
        return {
            "current_agent": "zone_planner",
            "current_validation_errors": ["No canonical labels for zone detection"],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    # HAD v3: Determine if multi-scene is needed
    needs_multi_scene = _check_needs_multi_scene(
        canonical_labels=canonical_labels,
        hierarchical_relationships=hierarchical_relationships,
        scene_hints=scene_hints,
    )

    logger.info(
        f"Zone planning with {len(canonical_labels)} labels, "
        f"{len(hierarchical_relationships) if hierarchical_relationships else 0} hierarchical groups, "
        f"needs_multi_scene={needs_multi_scene}"
    )

    # HAD v3: Route to multi-scene or single-scene processing
    if needs_multi_scene:
        return await _multi_scene_zone_planning(
            state=state,
            ctx=ctx,
            canonical_labels=canonical_labels,
            hierarchical_relationships=hierarchical_relationships,
            query_intent=query_intent,
            suggested_reveal_order=suggested_reveal_order,
            scene_hints=scene_hints,
            subject=subject,
            question_text=question_text,
        )

    # ==========================================================================
    # Phase 1: Image Acquisition Worker
    # ==========================================================================
    image_result = await _image_acquisition_worker(
        question_text=question_text,
        subject=subject,
        canonical_labels=canonical_labels,
        existing_image=state.get("generated_diagram_path") or (state.get("diagram_image") or {}).get("local_path"),
    )

    if not image_result.get("success"):
        logger.error(f"Image acquisition failed: {image_result.get('error')}")
        return {
            "current_agent": "zone_planner",
            "current_validation_errors": [f"Image acquisition failed: {image_result.get('error')}"],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    image_path = image_result.get("image_path")
    logger.info(f"Image acquired: {image_path}")

    # ==========================================================================
    # Phase 2: Zone Detection Worker (with retry loop)
    # ==========================================================================
    detection_result = await _zone_detection_worker(
        image_path=image_path,
        canonical_labels=canonical_labels,
        hierarchical_relationships=hierarchical_relationships,
        subject=subject,
        max_retries=MAX_DETECTION_RETRIES,
    )

    if not detection_result.get("success"):
        logger.error(f"Zone detection failed: {detection_result.get('error')}")
        return {
            "current_agent": "zone_planner",
            "current_validation_errors": [f"Zone detection failed: {detection_result.get('error')}"],
            "last_updated_at": datetime.utcnow().isoformat(),
        }

    zones = detection_result.get("zones", [])
    zone_groups = detection_result.get("zone_groups", [])
    validation = detection_result.get("validation", {})

    logger.info(
        f"Zone detection complete: {len(zones)} zones, {len(zone_groups)} groups, "
        f"validation_score={validation.get('overall_score', 0):.2f}"
    )

    # HAD v3: Apply zone collision resolution
    resolved_zones, collision_metadata = resolve_zone_overlaps(
        zones=zones,
        relationships=hierarchical_relationships,
        strategy="auto",
    )

    logger.info(
        f"Zone collision resolution: {collision_metadata.get('before', {}).get('total_overlaps', 0)} overlaps found, "
        f"{collision_metadata.get('after', {}).get('discrete_overlaps', []).__len__()} discrete overlaps remaining"
    )

    # ==========================================================================
    # Phase 3: Temporal Constraint Generation
    # ==========================================================================
    # Generate temporal constraints from zone hierarchy and collision metadata
    temporal_constraints = generate_temporal_constraints(
        zones=resolved_zones,
        zone_groups=zone_groups,
        collision_metadata=collision_metadata,
        scene_number=1,  # Single scene
    )
    temporal_constraints_dicts = constraints_to_dict_list(temporal_constraints)

    logger.info(
        f"Generated {len(temporal_constraints)} temporal constraints: "
        f"{sum(1 for c in temporal_constraints if c.constraint_type == 'mutex')} mutex, "
        f"{sum(1 for c in temporal_constraints if c.constraint_type == 'concurrent')} concurrent"
    )

    # Track metrics
    if ctx:
        ctx.set_llm_metrics(
            model=detection_result.get("model", "gemini-3-flash-preview"),
            latency_ms=detection_result.get("duration_ms", 0),
        )

    # Combine traces from both phases for UI visualization
    detection_trace = []
    if image_result.get("trace"):
        detection_trace.append(image_result["trace"])
    if detection_result.get("trace"):
        detection_trace.append(detection_result["trace"])

    return {
        "diagram_zones": resolved_zones,  # HAD v3: Use resolved zones
        "diagram_labels": [{"id": z.get("id"), "text": z.get("label")} for z in resolved_zones],
        "zone_groups": zone_groups,
        "generated_diagram_path": image_path,
        "zone_detection_method": "had_zone_planner",
        "zone_detection_metadata": {
            "model": detection_result.get("model"),
            "duration_ms": detection_result.get("duration_ms"),
            "retry_count": detection_result.get("retry_count", 0),
            "spatial_validation": validation,
            "hierarchical_groups_used": len(hierarchical_relationships) if hierarchical_relationships else 0,
            "detection_strategy": detection_result.get("strategy", "auto"),
            "detected_at": datetime.utcnow().isoformat(),
        },
        "zone_collision_metadata": collision_metadata,  # HAD v3: Collision resolution details
        "temporal_constraints": temporal_constraints_dicts,  # NEW: Temporal constraints for frontend
        "query_intent": query_intent,  # HAD v3: Query intent for frontend
        "suggested_reveal_order": suggested_reveal_order,  # HAD v3: Reveal order
        "needs_multi_scene": False,  # Single scene
        "detection_trace": detection_trace,  # For UI visualization
        "current_agent": "zone_planner",
        "last_updated_at": datetime.utcnow().isoformat(),
    }


async def _image_acquisition_worker(
    question_text: str,
    subject: str,
    canonical_labels: List[str],
    existing_image: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Image Acquisition Worker: Acquires diagram image through search or generation.

    Reasoning process (with trace capture):
    1. Check if we already have an image
    2. If not, decide between search vs generation
    3. Execute acquisition with quality validation
    4. Retry with refined query if needed
    """
    logger.info("ImageAcquisitionWorker starting")

    # Initialize trace builder for this phase
    trace = TraceBuilder(phase="image_acquisition")

    # Check for existing image
    if existing_image and os.path.exists(existing_image):
        logger.info(f"Using existing image: {existing_image}")
        trace.thought(
            "Checking for existing image in state",
            existing_image=existing_image
        )
        trace.observation(
            f"Found existing image at {existing_image}",
            result={"exists": True, "path": existing_image}
        )
        trace.decision("Using existing image - no search needed")
        trace.result("Image acquired from existing state", result=existing_image)

        return {
            "success": True,
            "image_path": existing_image,
            "method": "existing",
            "trace": trace.complete(success=True).to_dict(),
        }

    # Decide acquisition strategy
    trace.thought(
        f"Need to acquire a diagram image for subject: {subject}. "
        f"Will search for educational diagrams with labels: {canonical_labels[:3]}..."
    )
    trace.decision("Using web search for educational diagram (Serper Image API)")

    # Use web search to find educational diagrams
    best_result = None
    for attempt in range(MAX_IMAGE_SEARCH_RETRIES):
        search_query = _build_search_query(question_text, subject, canonical_labels, attempt)

        trace.thought(
            f"Attempt {attempt + 1}: Building search query based on subject and labels"
        )
        trace.action(
            tool="search_images",
            args={"query": search_query, "subject": subject, "num_results": 5},
            description=f"Searching: '{search_query}'"
        )

        logger.info(f"Searching images (attempt {attempt + 1}): {search_query}")
        start_time = time.time()

        result = await search_images(
            query=search_query,
            subject=subject,
            num_results=5,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        if result.success and result.selected_image_path:
            trace.observation(
                f"Found {len(result.images)} images, selected best match",
                result={
                    "images_found": len(result.images),
                    "selected_path": result.selected_image_path,
                },
                tool="search_images",
                duration_ms=duration_ms
            )
            trace.result(
                f"Successfully acquired image on attempt {attempt + 1}",
                result=result.selected_image_path
            )

            return {
                "success": True,
                "image_path": result.selected_image_path,
                "method": "web_search",
                "attempt": attempt + 1,
                "trace": trace.complete(success=True).to_dict(),
            }
        else:
            trace.observation(
                f"Search returned {len(result.images) if result.images else 0} images, "
                f"none suitable: {result.error or 'quality too low'}",
                result={"error": result.error},
                tool="search_images",
                duration_ms=duration_ms
            )

            if attempt < MAX_IMAGE_SEARCH_RETRIES - 1:
                trace.thought(
                    f"Will retry with refined query (adding more specific terms)"
                )

    trace.error("Failed to acquire image after all attempts")

    return {
        "success": False,
        "error": "Failed to acquire image after multiple attempts",
        "trace": trace.complete(success=False).to_dict(),
    }


def _build_search_query(
    question_text: str,
    subject: str,
    canonical_labels: List[str],
    attempt: int = 0,
) -> str:
    """Build search query with refinement based on attempt number."""
    # Extract the topic from the question (e.g., "flower" from "Label the parts of a flower")
    topic = question_text.lower()

    # Remove common prefixes to get the actual topic
    prefixes = [
        "label the parts of a ",
        "label the parts of an ",
        "label the parts of the ",
        "label the parts of ",
        "label the ",
        "identify the parts of a ",
        "identify the parts of an ",
        "identify the parts of ",
        "identify ",
    ]
    for prefix in prefixes:
        if topic.startswith(prefix):
            topic = topic[len(prefix):]
            break

    # Clean up
    topic = topic.rstrip("?.,!")

    # If we couldn't extract a good topic, fall back to the first few labels
    if not topic or topic == subject.lower() or len(topic) < 3:
        if canonical_labels:
            topic = canonical_labels[0]  # Use first label as topic hint

    if attempt == 0:
        # First attempt: specific topic + diagram
        return f"{topic} diagram labeled parts"
    elif attempt == 1:
        # Second attempt: add top labels
        top_labels = canonical_labels[:3]
        return f"{topic} anatomy diagram {' '.join(top_labels)}"
    else:
        # Third attempt: educational focus
        return f"{topic} educational diagram structure"


# =============================================================================
# HAD v3: Direct Gemini Zone Detection with Polygon Output
# =============================================================================

async def _zone_detection_gemini_direct(
    image_path: str,
    canonical_labels: List[str],
    hierarchical_relationships: Optional[List[Dict[str, Any]]],
    subject: str,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    HAD v3: Direct Gemini zone detection with polygon output.

    Simplifies the 4-layer call stack to a single Gemini service call:
    - zone_planner -> gemini_service.detect_zones_with_polygons()

    Features:
    - Polygon zones by default (not circles)
    - Self-validation in prompt (reduces retries)
    - Model selection: gemini-2.5-flash for vision
    """
    trace = TraceBuilder(phase="zone_detection_gemini_direct")

    # Determine detection strategy
    strategy = _determine_detection_strategy(hierarchical_relationships)
    query_intent = {"strategy": strategy}

    hierarchy_desc = "none"
    if hierarchical_relationships:
        rel_types = set(r.get("relationship_type", "contains") for r in hierarchical_relationships)
        hierarchy_desc = f"{len(hierarchical_relationships)} groups with types: {rel_types}"

    trace.thought(
        f"HAD v3: Using direct Gemini vision for polygon zone detection. "
        f"Strategy: {strategy}. Hierarchy: {hierarchy_desc}. "
        f"Labels: {len(canonical_labels)} ({', '.join(canonical_labels[:5])}{'...' if len(canonical_labels) > 5 else ''})"
    )

    trace.action(
        tool="gemini_detect_zones_polygons",
        args={
            "image_path": image_path,
            "labels_count": len(canonical_labels),
            "strategy": strategy,
            "model": "gemini-2.5-flash",
        },
        description="Single Gemini vision call with polygon output and self-validation"
    )

    try:
        gemini_service = get_gemini_service()

        start_time = time.time()

        # Single call with polygon output
        detection_result = await gemini_service.detect_zones_with_polygons(
            image_path=image_path,
            canonical_labels=canonical_labels,
            relationships=hierarchical_relationships,
            query_intent=query_intent,
            model=GeminiModel.FLASH,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Convert Zone objects to dicts
        zones = [
            {
                "id": z.id,
                "label": z.label,
                "shape": z.shape.value,
                "points": z.points,
                "x": z.center.get("x") if z.center else z.x,
                "y": z.center.get("y") if z.center else z.y,
                "radius": z.radius,
                "width": z.width,
                "height": z.height,
                "hierarchy_level": z.hierarchy_level,
                "parent_zone_id": z.parent_zone_id,
                "confidence": z.confidence,
                "hint": z.hint,
                "visible": z.visible,
            }
            for z in detection_result.zones
        ]

        # Convert ZoneGroup objects to dicts
        zone_groups = [
            {
                "parent_zone_id": g.parent_zone_id,
                "child_zone_ids": g.child_zone_ids,
                "relationship_type": g.relationship_type,
            }
            for g in detection_result.zone_groups
        ]

        # Count polygon zones
        polygon_count = sum(1 for z in zones if z.get("shape") == "polygon")

        trace.observation(
            f"Detected {len(zones)} zones ({polygon_count} polygons), {len(zone_groups)} groups. "
            f"Self-validation: {detection_result.validation}",
            result={
                "zones_count": len(zones),
                "polygon_count": polygon_count,
                "groups_count": len(zone_groups),
                "validation": detection_result.validation,
                "parts_not_found": detection_result.parts_not_found,
            },
            tool="gemini_detect_zones_polygons",
            duration_ms=duration_ms
        )

        # Use self-validation from Gemini response
        validation = detection_result.validation
        is_valid = validation.get("all_labels_found", True) and validation.get("centers_inside_polygons", True)
        overall_score = 1.0 if is_valid else 0.7

        if validation.get("discrete_overlaps", 0) > 0:
            overall_score -= 0.1 * validation.get("discrete_overlaps", 0)

        trace.decision(f"Detection complete with score {overall_score:.2f}")
        trace.result(
            f"HAD v3 Gemini direct detection: {len(zones)} zones, {polygon_count} polygons",
            result={
                "zones_count": len(zones),
                "polygon_count": polygon_count,
                "validation_score": overall_score,
            }
        )

        logger.info(
            f"HAD v3 Gemini direct: {len(zones)} zones ({polygon_count} polygons), "
            f"duration={duration_ms}ms, score={overall_score:.2f}"
        )

        return {
            "success": True,
            "zones": zones,
            "zone_groups": zone_groups,
            "validation": {
                "is_valid": is_valid,
                "overall_score": overall_score,
                "errors": [],
                "warnings": detection_result.parts_not_found,
                "suggestions": [],
                "group_scores": {},
            },
            "strategy": strategy,
            "retry_count": 0,
            "duration_ms": duration_ms,
            "model": "gemini-2.5-flash",
            "detection_method": "had_v3_gemini_direct",
            "polygon_count": polygon_count,
            "collision_metadata": detection_result.collision_metadata,
            "trace": trace.complete(success=True).to_dict(),
        }

    except Exception as e:
        logger.error(f"HAD v3 Gemini direct detection failed: {e}", exc_info=True)
        trace.error(f"Detection failed: {str(e)}")

        # Fall back to legacy detection
        logger.info("Falling back to legacy zone detection")
        return await _zone_detection_worker_legacy(
            image_path=image_path,
            canonical_labels=canonical_labels,
            hierarchical_relationships=hierarchical_relationships,
            subject=subject,
            max_retries=max_retries,
        )


async def _zone_detection_worker_legacy(
    image_path: str,
    canonical_labels: List[str],
    hierarchical_relationships: Optional[List[Dict[str, Any]]],
    subject: str,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Legacy zone detection worker (pre-HAD v3).

    Uses the vision_tools.detect_zones which calls gemini_zone_detector.
    Kept for fallback and backwards compatibility.
    """
    trace = TraceBuilder(phase="zone_detection_legacy")

    strategy = _determine_detection_strategy(hierarchical_relationships)
    logger.info(f"Legacy detection strategy: {strategy}")

    hierarchy_desc = "none"
    if hierarchical_relationships:
        rel_types = set(r.get("relationship_type", "contains") for r in hierarchical_relationships)
        hierarchy_desc = f"{len(hierarchical_relationships)} groups with types: {rel_types}"

    trace.thought(
        f"Using legacy zone detection via vision_tools. "
        f"Strategy: {strategy}. Hierarchy: {hierarchy_desc}."
    )

    best_result = None
    best_score = 0.0
    total_duration_ms = 0

    for attempt in range(max_retries):
        logger.info(f"Legacy zone detection attempt {attempt + 1}/{max_retries}")

        corrective_prompt = ""
        if attempt > 0 and best_result:
            validation = best_result.get("validation", {})
            if not validation.get("is_valid", True):
                corrective_prompt = generate_corrective_prompt(
                    validation,
                    hierarchical_relationships or [],
                )

        trace.action(
            tool="detect_zones_legacy",
            args={"attempt": attempt + 1},
            description=f"Legacy detection attempt {attempt + 1}/{max_retries}"
        )

        start_time = time.time()
        detection_result = await detect_zones(
            image_path=image_path,
            canonical_labels=canonical_labels,
            hierarchical_relationships=hierarchical_relationships,
            detection_strategy=strategy,
            subject=subject,
        )
        duration_ms = int((time.time() - start_time) * 1000)

        if not detection_result.success:
            trace.observation(
                f"Detection failed: {detection_result.error}",
                result={"error": detection_result.error},
                tool="detect_zones_legacy",
                duration_ms=duration_ms
            )
            continue

        total_duration_ms += duration_ms
        zones = detection_result.zones
        zone_groups = detection_result.zone_groups

        # Validate
        if hierarchical_relationships:
            validation = validate_hierarchical_spatial_coherence(zones, hierarchical_relationships)
        else:
            validation = type('obj', (object,), {
                'is_valid': True,
                'overall_score': 1.0,
                'errors': [],
                'warnings': [],
                'suggestions': [],
                'group_scores': {},
            })()

        current_score = validation.overall_score

        if current_score > best_score or best_result is None:
            best_score = current_score
            best_result = {
                "success": True,
                "zones": zones,
                "zone_groups": zone_groups,
                "validation": {
                    "is_valid": validation.is_valid,
                    "overall_score": validation.overall_score,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                    "suggestions": validation.suggestions,
                    "group_scores": validation.group_scores,
                },
                "strategy": strategy,
                "retry_count": attempt,
                "duration_ms": total_duration_ms,
                "detection_method": "legacy_vision_tools",
            }

        if validation.is_valid and current_score >= 0.7:
            break

    if best_result is None:
        trace.error("All legacy detection attempts failed")
        return {
            "success": False,
            "error": "All legacy detection attempts failed",
            "trace": trace.complete(success=False).to_dict(),
        }

    best_result["trace"] = trace.complete(success=True).to_dict()
    return best_result


async def _zone_detection_worker(
    image_path: str,
    canonical_labels: List[str],
    hierarchical_relationships: Optional[List[Dict[str, Any]]],
    subject: str,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Zone Detection Worker: Detects zones with hierarchical awareness and self-correction.

    HAD v3: Routes to Gemini direct detection when USE_GEMINI_DIRECT is True.

    Reasoning process (with trace capture):
    1. Analyze hierarchical relationships to determine detection strategy
    2. Detect zones with hierarchy-aware prompt (polygon output)
    3. Validate spatial coherence against relationships
    4. If validation fails, retry with corrective prompt
    """
    logger.info("ZoneDetectionWorker starting")

    # HAD v3: Use direct Gemini service for polygon zone detection
    if USE_GEMINI_DIRECT and GEMINI_SERVICE_AVAILABLE:
        logger.info("Using HAD v3 direct Gemini zone detection (polygon output)")
        return await _zone_detection_gemini_direct(
            image_path=image_path,
            canonical_labels=canonical_labels,
            hierarchical_relationships=hierarchical_relationships,
            subject=subject,
            max_retries=max_retries,
        )

    # Fall back to legacy detection (vision_tools.detect_zones)
    logger.info("Using legacy zone detection (via vision_tools)")

    # Initialize trace builder for this phase
    trace = TraceBuilder(phase="zone_detection")

    # Determine detection strategy based on relationship types
    strategy = _determine_detection_strategy(hierarchical_relationships)
    logger.info(f"Detection strategy: {strategy}")

    # Record initial reasoning
    hierarchy_desc = "none"
    if hierarchical_relationships:
        rel_types = set(r.get("relationship_type", "contains") for r in hierarchical_relationships)
        hierarchy_desc = f"{len(hierarchical_relationships)} groups with types: {rel_types}"

    trace.thought(
        f"Analyzing hierarchical relationships to determine detection strategy. "
        f"Found {hierarchy_desc}. "
        f"Labels to detect: {len(canonical_labels)} ({', '.join(canonical_labels[:5])}{'...' if len(canonical_labels) > 5 else ''})"
    )
    trace.decision(
        f"Using '{strategy}' detection strategy based on relationship types",
        strategy=strategy,
        hierarchical_groups=len(hierarchical_relationships) if hierarchical_relationships else 0
    )

    best_result = None
    best_score = 0.0
    total_duration_ms = 0

    for attempt in range(max_retries):
        logger.info(f"Zone detection attempt {attempt + 1}/{max_retries}")

        # Build corrective prompt for retries
        corrective_prompt = ""
        if attempt > 0 and best_result:
            validation = best_result.get("validation", {})
            if not validation.get("is_valid", True):
                corrective_prompt = generate_corrective_prompt(
                    validation,
                    hierarchical_relationships or [],
                )
                trace.thought(
                    f"Previous attempt had validation errors. Generating corrective guidance: "
                    f"{validation.get('errors', [])[:2]}"
                )
                logger.info(f"Using corrective prompt for retry")

        # Record action
        trace.action(
            tool="detect_zones_gemini",
            args={
                "image_path": image_path,
                "labels_count": len(canonical_labels),
                "strategy": strategy,
                "attempt": attempt + 1,
            },
            description=f"Detecting zones (attempt {attempt + 1}/{max_retries})"
        )

        # Detect zones
        start_time = time.time()
        detection_result = await detect_zones(
            image_path=image_path,
            canonical_labels=canonical_labels,
            hierarchical_relationships=hierarchical_relationships,
            detection_strategy=strategy,
            subject=subject,
        )
        duration_ms = int((time.time() - start_time) * 1000)

        if not detection_result.success:
            trace.observation(
                f"Detection failed: {detection_result.error}",
                result={"error": detection_result.error},
                tool="detect_zones_gemini",
                duration_ms=duration_ms
            )
            logger.warning(f"Detection attempt {attempt + 1} failed: {detection_result.error}")
            continue

        total_duration_ms += duration_ms

        zones = detection_result.zones
        zone_groups = detection_result.zone_groups

        trace.observation(
            f"Detected {len(zones)} zones, {len(zone_groups)} groups",
            result={
                "zones_count": len(zones),
                "zone_types": list(set(z.get("zone_type", "circle") for z in zones)),
                "groups_count": len(zone_groups),
            },
            tool="detect_zones_gemini",
            duration_ms=duration_ms
        )

        # Validate spatial coherence
        trace.action(
            tool="validate_spatial_coherence",
            args={"zones_count": len(zones), "hierarchy_groups": len(hierarchical_relationships) if hierarchical_relationships else 0},
            description="Validating zone positions against hierarchy"
        )

        validation_start = time.time()
        if hierarchical_relationships:
            validation = validate_hierarchical_spatial_coherence(
                zones,
                hierarchical_relationships,
            )
        else:
            validation = type('obj', (object,), {
                'is_valid': True,
                'overall_score': 1.0,
                'errors': [],
                'warnings': [],
                'suggestions': [],
                'group_scores': {},
                'analysis': {},
            })()
        validation_duration = int((time.time() - validation_start) * 1000)

        current_score = validation.overall_score

        trace.observation(
            f"Validation: score={current_score:.2f}, valid={validation.is_valid}",
            result={
                "is_valid": validation.is_valid,
                "score": current_score,
                "errors": validation.errors[:3] if validation.errors else [],
            },
            tool="validate_spatial_coherence",
            duration_ms=validation_duration
        )

        logger.info(
            f"Attempt {attempt + 1}: {len(zones)} zones, "
            f"validation_score={current_score:.2f}, is_valid={validation.is_valid}"
        )

        # Track best result
        if current_score > best_score or best_result is None:
            best_score = current_score
            best_result = {
                "success": True,
                "zones": zones,
                "zone_groups": zone_groups,
                "validation": {
                    "is_valid": validation.is_valid,
                    "overall_score": validation.overall_score,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                    "suggestions": validation.suggestions,
                    "group_scores": validation.group_scores,
                },
                "strategy": strategy,
                "retry_count": attempt,
                "duration_ms": total_duration_ms,
            }

        # If validation passes, we're done
        if validation.is_valid and current_score >= 0.7:
            trace.decision(f"Validation passed on attempt {attempt + 1} with score {current_score:.2f}")
            trace.result(
                f"Successfully detected {len(zones)} zones with {len(zone_groups)} groups",
                result={
                    "zones_count": len(zones),
                    "groups_count": len(zone_groups),
                    "validation_score": current_score,
                }
            )
            logger.info(f"Validation passed on attempt {attempt + 1}")
            break

        # Log validation issues for debugging
        if validation.errors:
            for error in validation.errors[:3]:
                logger.warning(f"Validation error: {error}")

    if best_result is None:
        trace.error("All detection attempts failed")
        return {
            "success": False,
            "error": "All detection attempts failed",
            "trace": trace.complete(success=False).to_dict(),
        }

    # Add trace to result
    best_result["trace"] = trace.complete(success=True).to_dict()

    return best_result


def _determine_detection_strategy(
    hierarchical_relationships: Optional[List[Dict[str, Any]]]
) -> str:
    """
    Determine detection strategy based on relationship types.

    Returns:
        'layered': If any composed_of/subdivided_into relationships exist
        'discrete': If only contains/has_part relationships exist
        'auto': If no relationships or mixed types
    """
    if not hierarchical_relationships:
        return "auto"

    has_layered = False
    has_discrete = False

    for rel in hierarchical_relationships:
        rel_type = rel.get("relationship_type", "contains")
        if rel_type in ("composed_of", "subdivided_into"):
            has_layered = True
        else:
            has_discrete = True

    if has_layered and not has_discrete:
        return "layered"
    elif has_discrete and not has_layered:
        return "discrete"
    else:
        return "auto"


# =============================================================================
# Standalone test function
# =============================================================================

async def test_zone_planner():
    """Test the zone_planner with sample input."""
    from app.agents.state import create_initial_state

    state = create_initial_state(
        question_id="test_001",
        question_text="Label the parts of a human heart"
    )

    # Add domain knowledge with hierarchical relationships
    state["domain_knowledge"] = {
        "canonical_labels": [
            "Heart Wall", "Epicardium", "Myocardium", "Endocardium",
            "Left Atrium", "Right Atrium", "Left Ventricle", "Right Ventricle",
            "Aorta", "Pulmonary Artery"
        ],
        "hierarchical_relationships": [
            {
                "parent": "Heart Wall",
                "children": ["Epicardium", "Myocardium", "Endocardium"],
                "relationship_type": "composed_of"
            }
        ],
    }

    state["pedagogical_context"] = {
        "subject": "Biology - Human Anatomy",
    }

    state["template_selection"] = {
        "template_type": "INTERACTIVE_DIAGRAM",
    }

    result = await zone_planner(state)

    print(f"Success: {result.get('diagram_zones') is not None}")
    print(f"Zones: {len(result.get('diagram_zones', []))}")
    print(f"Zone groups: {len(result.get('zone_groups', []))}")
    print(f"Metadata: {result.get('zone_detection_metadata', {})}")

    return result


def _check_needs_multi_scene(
    canonical_labels: List[str],
    hierarchical_relationships: Optional[List[Dict[str, Any]]],
    scene_hints: Optional[List[Dict[str, Any]]],
) -> bool:
    """
    Determine if multi-scene game structure is needed.

    Criteria:
    - Explicit scene hints from domain knowledge
    - Hierarchy depth > 2
    - Label count > 12
    """
    # Explicit scene hints take priority
    if scene_hints and len(scene_hints) > 0:
        return True

    # Check label count
    if len(canonical_labels) > MULTI_SCENE_LABEL_THRESHOLD:
        return True

    # Check hierarchy depth
    if hierarchical_relationships:
        depth = _calculate_hierarchy_depth(hierarchical_relationships)
        if depth > MULTI_SCENE_HIERARCHY_DEPTH_THRESHOLD:
            return True

    return False


def _calculate_hierarchy_depth(relationships: List[Dict[str, Any]]) -> int:
    """Calculate maximum hierarchy depth from relationships."""
    if not relationships:
        return 1

    # Build parent-child graph
    children_of = {}
    all_children = set()

    for rel in relationships:
        parent = rel.get("parent", "").lower()
        children = [c.lower() for c in rel.get("children", [])]
        children_of[parent] = children
        all_children.update(children)

    # Find roots
    roots = set(children_of.keys()) - all_children
    if not roots:
        roots = set(children_of.keys())

    # BFS to find max depth
    max_depth = 1
    visited = set()
    queue = [(r, 1) for r in roots]

    while queue:
        node, depth = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        max_depth = max(max_depth, depth)

        for child in children_of.get(node, []):
            queue.append((child, depth + 1))

    return max_depth


async def _multi_scene_zone_planning(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext],
    canonical_labels: List[str],
    hierarchical_relationships: List[Dict[str, Any]],
    query_intent: Dict[str, Any],
    suggested_reveal_order: List[str],
    scene_hints: List[Dict[str, Any]],
    subject: str,
    question_text: str,
) -> Dict[str, Any]:
    """
    Multi-scene zone planning for complex diagrams.

    Process:
    1. Plan scene structure based on hierarchy and hints
    2. For each scene, acquire appropriate image
    3. Detect zones for each scene's focus labels
    4. Resolve overlaps within each scene
    """
    logger.info("Starting multi-scene zone planning")

    # Initialize trace builder
    trace = TraceBuilder(phase="multi_scene_zone_planning")

    trace.thought(
        f"Planning multi-scene game structure. "
        f"Total labels: {len(canonical_labels)}, "
        f"Scene hints: {len(scene_hints)}"
    )

    # Step 1: Plan scene structure
    scene_breakdown = _plan_scene_structure(
        canonical_labels=canonical_labels,
        hierarchical_relationships=hierarchical_relationships,
        scene_hints=scene_hints,
        suggested_reveal_order=suggested_reveal_order,
    )

    trace.decision(
        f"Planned {len(scene_breakdown)} scenes",
        scenes=[s.get("title") for s in scene_breakdown]
    )

    # Step 2: Process each scene
    scene_images = {}
    scene_zones = {}
    scene_zone_groups = {}
    scene_labels_map = {}

    existing_image = state.get("generated_diagram_path") or (state.get("diagram_image") or {}).get("local_path")

    for scene in scene_breakdown:
        scene_num = scene["scene_number"]
        focus_labels = scene["focus_labels"]
        scene_scope = scene.get("scope", "overview")

        logger.info(f"Processing scene {scene_num}: {scene.get('title')}")

        trace.action(
            tool="acquire_scene_image",
            args={"scene_number": scene_num, "focus_labels": focus_labels[:3]},
            description=f"Acquiring image for scene {scene_num}"
        )

        # For scene 1, use existing image or search for overview
        if scene_num == 1 and existing_image and os.path.exists(existing_image):
            image_path = existing_image
        else:
            # Search for scene-specific image
            image_result = await _image_acquisition_worker(
                question_text=question_text,
                subject=subject,
                canonical_labels=focus_labels,
                existing_image=existing_image if scene_num == 1 else None,
            )

            if not image_result.get("success"):
                logger.warning(f"Scene {scene_num} image acquisition failed, using fallback")
                image_path = existing_image
            else:
                image_path = image_result.get("image_path")

        scene_images[scene_num] = image_path

        # Detect zones for this scene
        trace.action(
            tool="detect_scene_zones",
            args={"scene_number": scene_num, "labels_count": len(focus_labels)},
            description=f"Detecting zones for scene {scene_num}"
        )

        # Filter hierarchical relationships for this scene's labels
        scene_relationships = _filter_relationships_for_labels(
            hierarchical_relationships, focus_labels
        )

        detection_result = await _zone_detection_worker(
            image_path=image_path,
            canonical_labels=focus_labels,
            hierarchical_relationships=scene_relationships,
            subject=subject,
            max_retries=MAX_DETECTION_RETRIES,
        )

        if detection_result.get("success"):
            zones = detection_result.get("zones", [])
            zone_groups = detection_result.get("zone_groups", [])

            # Resolve overlaps for this scene
            resolved_zones, collision_meta = resolve_zone_overlaps(
                zones=zones,
                relationships=scene_relationships,
                strategy="auto",
            )

            scene_zones[scene_num] = resolved_zones
            scene_zone_groups[scene_num] = zone_groups
            scene_labels_map[scene_num] = [
                {"id": z.get("id"), "text": z.get("label")} for z in resolved_zones
            ]

            trace.observation(
                f"Scene {scene_num}: {len(resolved_zones)} zones detected",
                result={"zones_count": len(resolved_zones), "groups_count": len(zone_groups)},
                tool="detect_scene_zones"
            )
        else:
            logger.error(f"Zone detection failed for scene {scene_num}")
            scene_zones[scene_num] = []
            scene_zone_groups[scene_num] = []
            scene_labels_map[scene_num] = []

    # Determine scene progression type
    progression_type = _determine_progression_type(
        scene_breakdown, hierarchical_relationships
    )

    trace.result(
        f"Multi-scene planning complete: {len(scene_breakdown)} scenes, {progression_type} progression",
        result={
            "num_scenes": len(scene_breakdown),
            "progression_type": progression_type,
            "total_zones": sum(len(zones) for zones in scene_zones.values()),
        }
    )

    # Use first scene as primary for backwards compatibility
    primary_zones = scene_zones.get(1, [])
    primary_zone_groups = scene_zone_groups.get(1, [])
    primary_image = scene_images.get(1)

    # Generate temporal constraints for primary scene
    temporal_constraints = generate_temporal_constraints(
        zones=primary_zones,
        zone_groups=primary_zone_groups,
        collision_metadata=None,  # No collision metadata in multi-scene
        scene_number=1,
    )
    temporal_constraints_dicts = constraints_to_dict_list(temporal_constraints)

    logger.info(
        f"Generated {len(temporal_constraints)} temporal constraints for multi-scene primary"
    )

    return {
        # Primary scene data (backwards compatibility)
        "diagram_zones": primary_zones,
        "diagram_labels": [{"id": z.get("id"), "text": z.get("label")} for z in primary_zones],
        "zone_groups": primary_zone_groups,
        "generated_diagram_path": primary_image,
        "zone_detection_method": "had_zone_planner_multi_scene",

        # Multi-scene data
        "needs_multi_scene": True,
        "num_scenes": len(scene_breakdown),
        "scene_progression_type": progression_type,
        "scene_breakdown": scene_breakdown,
        "scene_images": scene_images,
        "scene_zones": scene_zones,
        "scene_zone_groups": scene_zone_groups,
        "scene_labels": scene_labels_map,

        # Query intent data
        "query_intent": query_intent,
        "suggested_reveal_order": suggested_reveal_order,

        # Temporal constraints for frontend
        "temporal_constraints": temporal_constraints_dicts,

        # Metadata
        "zone_detection_metadata": {
            "is_multi_scene": True,
            "num_scenes": len(scene_breakdown),
            "progression_type": progression_type,
            "detected_at": datetime.utcnow().isoformat(),
        },
        "detection_trace": [trace.complete(success=True).to_dict()],
        "current_agent": "zone_planner",
        "last_updated_at": datetime.utcnow().isoformat(),
    }


def _plan_scene_structure(
    canonical_labels: List[str],
    hierarchical_relationships: List[Dict[str, Any]],
    scene_hints: List[Dict[str, Any]],
    suggested_reveal_order: List[str],
) -> List[Dict[str, Any]]:
    """
    Plan scene structure based on hierarchy and hints.

    Strategy:
    1. If scene_hints provided, use them directly
    2. Otherwise, group by hierarchy level
    3. Scene 1 gets top-level labels, Scene 2+ get children
    """
    scenes = []

    if scene_hints:
        # Use explicit scene hints
        for idx, hint in enumerate(scene_hints, start=1):
            scenes.append({
                "scene_number": idx,
                "title": hint.get("focus", f"Scene {idx}"),
                "scope": hint.get("suggested_scope", "detailed"),
                "focus_labels": _extract_labels_for_hint(
                    hint, canonical_labels, hierarchical_relationships
                ),
                "reason": hint.get("reason", ""),
            })
    else:
        # Group by hierarchy level
        parent_labels = set()
        child_labels = set()

        for rel in hierarchical_relationships or []:
            parent_labels.add(rel.get("parent", "").lower())
            for child in rel.get("children", []):
                child_labels.add(child.lower())

        # Top-level labels (not children of anything)
        top_level = [
            label for label in canonical_labels
            if label.lower() not in child_labels
        ]

        # Child labels
        children = [
            label for label in canonical_labels
            if label.lower() in child_labels
        ]

        # Scene 1: Overview with top-level labels
        scenes.append({
            "scene_number": 1,
            "title": "Overview",
            "scope": "overview",
            "focus_labels": top_level if top_level else canonical_labels[:6],
            "reason": "Main structures",
        })

        # Scene 2: Details with child labels
        if children:
            scenes.append({
                "scene_number": 2,
                "title": "Details",
                "scope": "detailed",
                "focus_labels": children,
                "reason": "Sub-structures and components",
            })

    return scenes


def _extract_labels_for_hint(
    hint: Dict[str, Any],
    canonical_labels: List[str],
    hierarchical_relationships: List[Dict[str, Any]],
) -> List[str]:
    """Extract relevant labels from a scene hint."""
    focus = hint.get("focus", "").lower()

    # Try to match against canonical labels
    matched_labels = []
    for label in canonical_labels:
        if focus in label.lower() or label.lower() in focus:
            matched_labels.append(label)

    # If no matches, try to find by parent
    if not matched_labels:
        for rel in hierarchical_relationships:
            if focus in rel.get("parent", "").lower():
                matched_labels.extend([rel.get("parent")] + rel.get("children", []))
                break

    # Fallback: return first N labels
    if not matched_labels:
        matched_labels = canonical_labels[:6]

    return matched_labels


def _filter_relationships_for_labels(
    relationships: List[Dict[str, Any]],
    labels: List[str],
) -> List[Dict[str, Any]]:
    """Filter hierarchical relationships to only include relevant labels."""
    labels_lower = set(label.lower() for label in labels)

    filtered = []
    for rel in relationships:
        parent = rel.get("parent", "").lower()
        children = rel.get("children", [])

        if parent in labels_lower:
            # Filter children to only include those in labels
            relevant_children = [c for c in children if c.lower() in labels_lower]
            if relevant_children:
                filtered.append({
                    **rel,
                    "children": relevant_children,
                })

    return filtered


def _determine_progression_type(
    scene_breakdown: List[Dict[str, Any]],
    hierarchical_relationships: List[Dict[str, Any]],
) -> str:
    """
    Determine scene progression type.

    Options: linear, zoom_in, depth_first, branching
    """
    if len(scene_breakdown) <= 1:
        return "linear"

    # Check if scenes go from overview to detail (zoom_in)
    scopes = [s.get("scope", "").lower() for s in scene_breakdown]
    if scopes == ["overview", "detailed"] or "zoom" in str(scene_breakdown):
        return "zoom_in"

    # Check for branching (multiple parallel paths)
    if len(scene_breakdown) > 2:
        # Could implement more sophisticated branching detection
        return "branching"

    # Default to linear
    return "linear"


if __name__ == "__main__":
    asyncio.run(test_zone_planner())
