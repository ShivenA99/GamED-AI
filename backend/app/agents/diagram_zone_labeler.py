"""
Diagram Zone Labeler Agent

This agent matches each required label to the best segment from all available segments.
It uses VLM to score each label-segment pair and selects the best 6 zones (one per label).
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.vlm_service import label_zone_with_vlm, VLMError
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.diagram_zone_labeler")


def _slugify(value: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _pick_label_from_response(response: str, candidates: List[str]) -> Optional[str]:
    lowered = response.lower()
    for label in candidates:
        if label.lower() in lowered:
            return label
    return None


async def _score_label_segment_match(
    label: str,
    segment: Dict[str, Any],
    image_obj: Any,
    image_bytes: bytes,
    sam3_prompts: Dict[str, str],
    required_labels: List[str]
) -> Tuple[float, Optional[str]]:
    """
    Score how well a segment matches a specific label using VLM.
    
    Returns:
        (score, response_text): score is 1.0 if exact match, 0.0 if no match, 
                                or confidence value if VLM provides it.
                                response_text is the raw VLM response.
    """
    try:
        from io import BytesIO
        
        # Crop segment from image
        zone_bytes = image_bytes
        if image_obj and "bbox" in segment:
            try:
                bbox = segment["bbox"]
                x, y = int(bbox.get("x", 0)), int(bbox.get("y", 0))
                w, h = int(bbox.get("width", 0)), int(bbox.get("height", 0))
                crop = image_obj.crop((x, y, x + w, y + h))
                buffer = BytesIO()
                crop.save(buffer, format="PNG")
                zone_bytes = buffer.getvalue()
            except Exception:
                zone_bytes = image_bytes
        
        # Get SAM3 prompt for this label if available
        sam3_prompt = sam3_prompts.get(label, "")
        
        # Enhanced prompt that asks VLM to verify if this segment matches the label
        # Include context about other labels to help with disambiguation
        other_labels = [l for l in required_labels if l != label]
        prompt = (
            f"You are analyzing a diagram zone to determine if it represents '{label}'. "
            f"{f'This zone was segmented using SAM3 with the prompt: \"{sam3_prompt}\". ' if sam3_prompt else ''}"
            f"\n\nExamine the highlighted zone in the image carefully. "
            f"\n\nRequired labels for this diagram: {', '.join(required_labels)}"
            f"\n\nYour task:"
            f"\n1. Look at the highlighted zone in the image"
            f"\n2. Determine if this zone correctly and accurately represents '{label}'"
            f"\n3. Consider the context: this is a diagram with {len(required_labels)} distinct parts to label"
            f"\n4. If you are confident this zone represents '{label}', respond with exactly: 'YES: {label}'"
            f"\n5. If this zone does NOT represent '{label}', respond with: 'NO: <best_matching_label>' where <best_matching_label> is the most appropriate label from: {', '.join(required_labels)}"
            f"\n\nBe precise and careful. Only respond with 'YES: {label}' if you are highly confident this zone represents '{label}'. "
            f"If you have any doubt, respond with 'NO:' followed by the best matching label from the list."
        )
        
        response = await label_zone_with_vlm(
            image_bytes=zone_bytes,
            candidate_labels=required_labels,
            prompt=prompt,
        )
        
        response_lower = response.lower().strip()
        label_lower = label.lower()
        
        # Check for explicit YES match (highest confidence)
        # Patterns: "yes: label", "yes label", "yes, label", "yes - label", etc.
        yes_patterns = [
            f"yes: {label_lower}",
            f"yes {label_lower}",
            f"yes, {label_lower}",
            f"yes - {label_lower}",
            f"yes, it is {label_lower}",
            f"yes, this is {label_lower}",
            f"yes, this represents {label_lower}",
            f"yes, this zone is {label_lower}",
        ]
        for pattern in yes_patterns:
            if pattern in response_lower:
                return (1.0, response)
        
        # Check for explicit NO (low confidence)
        if response_lower.startswith("no") or response_lower.startswith("no:"):
            # Check if it mentions a different label
            for other_label in required_labels:
                if other_label.lower() != label_lower and other_label.lower() in response_lower:
                    return (0.1, response)  # Very low score - explicitly says NO and suggests different label
            # NO but doesn't suggest alternative
            return (0.2, response)
        
        # Check if response contains the label (partial match - medium confidence)
        if label_lower in response_lower:
            # Check for positive indicators
            positive_indicators = ["is", "represents", "shows", "displays", "contains", "correct", "matches", "this is", "this zone"]
            has_positive = any(indicator in response_lower for indicator in positive_indicators)
            if has_positive:
                return (0.8, response)  # High confidence - mentions label with positive context
            return (0.5, response)  # Medium confidence - mentions label but unclear context
        
        # Check if any other required label is mentioned (low confidence)
        for other_label in required_labels:
            if other_label.lower() != label_lower and other_label.lower() in response_lower:
                return (0.15, response)  # Very low score - mentions different label
        
        # No clear match found
        return (0.0, response)
        
    except VLMError as e:
        logger.debug(f"VLM error scoring label '{label}': {e}")
        return (0.0, None)
    except Exception as e:
        logger.debug(f"Error scoring label '{label}': {e}")
        return (0.0, None)


async def diagram_zone_labeler_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    question_id = state.get("question_id", "unknown")
    template_type = state.get("template_selection", {}).get("template_type", "")
    
    logger.info("Starting zone labeling", 
                question_id=question_id,
                template_type=template_type,
                agent_name="diagram_zone_labeler")
    
    if template_type != "INTERACTIVE_DIAGRAM":
        logger.info(f"Skipping zone labeling: template_type={template_type}")
        return {**state, "current_agent": "diagram_zone_labeler"}

    segments_info = state.get("diagram_segments") or {}
    segments = segments_info.get("segments") or []
    
    logger.info("Zone labeling input", 
               segments_count=len(segments),
               segmentation_method=segments_info.get("method", "unknown"))
    
    # Prefer cleaned image path, fallback to original
    image_path = state.get("cleaned_image_path") or segments_info.get("image_path")
    logger.info("Image path for labeling", 
               image_path=image_path,
               using_cleaned_image=state.get("cleaned_image_path") is not None)
    
    # Get labels from game_plan.required_labels first (set by game_planner for INTERACTIVE_DIAGRAM)
    # Fallback to domain_knowledge.canonical_labels for backward compatibility
    game_plan = state.get("game_plan", {}) or {}
    required_labels = game_plan.get("required_labels")
    
    if not required_labels:
        domain_knowledge = state.get("domain_knowledge", {}) or {}
        if isinstance(domain_knowledge, dict):
            required_labels = [l for l in (domain_knowledge.get("canonical_labels", []) or []) if isinstance(l, str)]
        else:
            required_labels = []
        logger.info("Using domain_knowledge labels (game_plan.required_labels not found)", 
                   labels_count=len(required_labels),
                   labels=required_labels[:10] if required_labels else [])
    else:
        logger.info("Using game_plan.required_labels", 
                   labels_count=len(required_labels),
                   labels=required_labels[:10])
    
    logger.info("Zone labeling validation", 
               segments_count=len(segments),
               required_labels_count=len(required_labels) if required_labels else 0,
               has_segments=bool(segments),
               has_labels=bool(required_labels))
    
    if not segments:
        logger.error("Missing segments for zone labeling", 
                    segments_count=0,
                    segments_info_type=type(segments_info).__name__)
        return {
            **state,
            "current_agent": "diagram_zone_labeler",
            "current_validation_errors": ["Missing segments for zone labeling"],
        }
    
    if not required_labels:
        logger.error("Missing required labels for zone labeling", 
                    required_labels_count=0,
                    domain_knowledge_type=type(state.get("domain_knowledge")).__name__,
                    game_plan_has_required_labels=bool(game_plan.get("required_labels")))
        return {
            **state,
            "current_agent": "diagram_zone_labeler",
            "current_validation_errors": ["Missing required labels for zone labeling"],
        }

    # Load image bytes and dimensions if possible
    image_bytes = None
    image_obj = None
    width = 800
    height = 600
    if image_path:
        try:
            from pathlib import Path
            image_bytes = Path(image_path).read_bytes()
            try:
                from PIL import Image
                image_obj = Image.open(image_path).convert("RGB")
                width, height = image_obj.size
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"ZoneLabeler: Failed to load image for VLM: {e}")

    # Get SAM3 prompts for context (from prompt generator agent)
    sam3_prompts = state.get("sam3_prompts") or {}
    
    # Track which segments have been assigned to avoid duplicates
    used_segment_indices = set()
    zones: List[Dict[str, Any]] = []
    labels: List[Dict[str, Any]] = []
    vlm_success_count = 0
    vlm_failure_count = 0
    fallback_count = 0
    
    logger.info(
        "Starting label-to-segment matching",
        required_labels_count=len(required_labels),
        available_segments_count=len(segments),
        strategy="best_match_per_label"
    )
    
    # For each required label, find the best matching segment
    for label_idx, label in enumerate(required_labels, start=1):
        logger.info(f"Matching label {label_idx}/{len(required_labels)}: '{label}'")
        
        best_segment_idx: Optional[int] = None
        best_score: float = -1.0
        best_response: Optional[str] = None
        labeling_method = "fallback"
        
        if image_bytes and image_obj:
            # Score all available (unused) segments against this label
            segment_scores: List[Tuple[int, float, Optional[str]]] = []
            
            for seg_idx, segment in enumerate(segments):
                # Skip already assigned segments
                if seg_idx in used_segment_indices:
                    continue
                
                try:
                    score, response = await _score_label_segment_match(
                        label=label,
                        segment=segment,
                        image_obj=image_obj,
                        image_bytes=image_bytes,
                        sam3_prompts=sam3_prompts,
                        required_labels=required_labels
                    )
                    segment_scores.append((seg_idx, score, response))
                    
                    if score > best_score:
                        best_score = score
                        best_segment_idx = seg_idx
                        best_response = response
                        labeling_method = "vlm"
                    
                    logger.debug(
                        f"Scored segment {seg_idx + 1} for label '{label}': {score:.2f}",
                        label=label,
                        segment_index=seg_idx,
                        score=score
                    )
                    
                except VLMError as e:
                    vlm_failure_count += 1
                    error_type = type(e).__name__
                    error_msg = str(e)
                    
                    # Log first error per label, then only debug
                    if vlm_failure_count <= len(required_labels):
                        logger.warning(
                            f"VLM failed for label '{label}', segment {seg_idx + 1}",
                            label=label,
                            segment_index=seg_idx,
                            error_type=error_type,
                            error_message=error_msg
                        )
                except Exception as e:
                    logger.debug(f"Error scoring segment {seg_idx + 1} for label '{label}': {e}")
            
            # Log scoring summary
            if segment_scores:
                sorted_scores = sorted(segment_scores, key=lambda x: x[1], reverse=True)
                logger.info(
                    f"Label '{label}' scoring complete",
                    label=label,
                    best_segment_index=best_segment_idx,
                    best_score=best_score,
                    total_segments_evaluated=len(segment_scores),
                    top_3_scores=[(idx, score) for idx, score, _ in sorted_scores[:3]]
                )
        
        # Select the best segment, or fallback if VLM failed
        selected_segment_idx = best_segment_idx
        
        if selected_segment_idx is None:
            # Fallback: use first unused segment
            for seg_idx in range(len(segments)):
                if seg_idx not in used_segment_indices:
                    selected_segment_idx = seg_idx
                    fallback_count += 1
                    labeling_method = "sequential-fallback"
                    logger.warning(
                        f"Using fallback for label '{label}': assigning segment {seg_idx + 1}",
                        label=label,
                        segment_index=seg_idx,
                        reason="VLM unavailable or no good matches found"
                    )
                    break
        
        if selected_segment_idx is None:
            logger.error(f"No segments available for label '{label}'")
            continue
        
        # Mark segment as used
        used_segment_indices.add(selected_segment_idx)
        selected_segment = segments[selected_segment_idx]
        
        if best_score >= 0.5:
            vlm_success_count += 1
        
        # Extract coordinates from segment
        if "center_px" in selected_segment:
            cx = float(selected_segment["center_px"]["x"])
            cy = float(selected_segment["center_px"]["y"])
            x = round((cx / width) * 100, 2)
            y = round((cy / height) * 100, 2)
        else:
            x = float(selected_segment.get("x", 50))
            y = float(selected_segment.get("y", 50))

        radius = float(selected_segment.get("radius", 10))
        
        # Generate unique zone ID
        base_zone_id = _slugify(label) or f"zone_{label_idx}"
        zone_id = base_zone_id
        zone_id_counter = 1
        existing_zone_ids = {z.get("id") for z in zones}
        while zone_id in existing_zone_ids:
            zone_id = f"{base_zone_id}_{zone_id_counter}"
            zone_id_counter += 1

        zones.append({
            "id": zone_id,
            "label": label,
            "x": x,
            "y": y,
            "radius": radius,
        })
        labels.append({
            "id": f"label_{zone_id}",
            "text": label,
            "correctZoneId": zone_id,
        })
        
        logger.info(
            f"Assigned label '{label}' to segment {selected_segment_idx + 1}",
            label=label,
            segment_index=selected_segment_idx,
            zone_id=zone_id,
            method=labeling_method,
            score=best_score if best_score >= 0 else None
        )

    # Validate that all required labels were found
    found_labels = {z["label"].lower() for z in zones}
    required_set = {l.lower() for l in required_labels}
    missing_labels = required_set - found_labels
    
    # Determine overall labeling method
    if vlm_success_count > 0:
        primary_method = "vlm_best_match"
        fallback_used = fallback_count > 0
    else:
        primary_method = "sequential-fallback"
        fallback_used = True
    
    logger.info(
        "Zone labeling completed",
        strategy="label_to_segment_matching",
        fallback_used=fallback_used,
        primary_method=primary_method,
        vlm_success_count=vlm_success_count,
        vlm_failure_count=vlm_failure_count,
        fallback_count=fallback_count,
        zones_created=len(zones),
        labels_created=len(labels),
        segments_used=len(used_segment_indices),
        segments_available=len(segments),
        found_labels=list(found_labels),
        required_labels=list(required_set),
        missing_labels=list(missing_labels) if missing_labels else []
    )
    
    if fallback_used:
        logger.warning(
            "Zone labeling used fallback method for some labels",
            fallback_used=True,
            primary_method="vlm_best_match",
            fallback_method="sequential_assignment",
            vlm_success_count=vlm_success_count,
            vlm_failure_count=vlm_failure_count,
            fallback_count=fallback_count,
            total_segments=len(segments),
            reason="VLM unavailable or failed for some label-segment pairs",
            action_required="Start Ollama and pull VLM model: ollama pull llava:latest"
        )
    
    if missing_labels:
        logger.warning(
            "Some required labels were not matched to zones",
            missing_labels=list(missing_labels),
            found_labels_count=len(found_labels),
            required_labels_count=len(required_set)
        )
    
    # Set retry flag if labels are missing and we haven't exceeded max attempts
    # Note: image_search_attempts tracks completed attempts (0 = initial, 1 = first retry, etc.)
    # To allow max_image_attempts total attempts, we need attempts < max_image_attempts - 1
    # because we increment AFTER checking, and the initial attempt is already done
    retry_image_search = False
    image_search_attempts = state.get("image_search_attempts", 0)
    max_image_attempts = state.get("max_image_attempts", 3)
    
    # Check if we can do another retry (current attempts + 1 retry < max total attempts)
    # With max_image_attempts=3: allow retry if attempts < 2 (i.e., 0 or 1)
    # This gives us: initial (0) + retry 1 (1) + retry 2 (2) = 3 total attempts
    if missing_labels and image_search_attempts < max_image_attempts - 1:
        retry_image_search = True
        image_search_attempts += 1
        logger.warning(
            "Missing required labels, will retry image search",
            missing_labels=list(missing_labels),
            attempt=image_search_attempts + 1,  # +1 because attempts is 0-indexed
            max_attempts=max_image_attempts
        )
    elif missing_labels:
        logger.warning(
            "Missing required labels, max retry attempts reached",
            missing_labels=list(missing_labels),
            attempt=image_search_attempts,
            max_attempts=max_image_attempts
        )
    else:
        logger.info("All required labels found successfully", 
                   found_labels_count=len(found_labels),
                   required_labels_count=len(required_set))

    logger.info("Zone labeling agent completed", 
               zones_count=len(zones),
               labels_count=len(labels),
               retry_needed=retry_image_search)

    return {
        **state,
        "diagram_zones": zones,
        "diagram_labels": labels,
        "retry_image_search": retry_image_search,
        "image_search_attempts": image_search_attempts,
        "current_agent": "diagram_zone_labeler",
        "last_updated_at": datetime.utcnow().isoformat(),
    }
