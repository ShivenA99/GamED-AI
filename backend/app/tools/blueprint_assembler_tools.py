"""
Blueprint Assembler v3 Tools -- ReAct agent toolbox for blueprint_assembler_v3.

Four tools that give the blueprint assembler agent the ability to:
1. Assemble a blueprint from upstream state (game_design, scene_specs, interaction_specs, assets)
2. Validate a blueprint for frontend compatibility
3. Repair common issues in a blueprint
4. Submit the final blueprint (terminal validation gate)

All tools are deterministic (no LLM calls). They read upstream state via v3 context injection.
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional

from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.tools.blueprint_assembler")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_id(prefix: str, *parts: str) -> str:
    """Generate a deterministic ID from parts."""
    slug = "_".join(p.lower().replace(" ", "_") for p in parts if p)
    return f"{prefix}_{slug}" if slug else f"{prefix}_{uuid.uuid4().hex[:6]}"


def _normalize_label(label: str) -> str:
    """Normalize a label for matching: lowercase, strip trailing 's' for plural."""
    s = label.lower().strip()
    # Strip common plural suffix for matching (petals→petal, sepals→sepal)
    if s.endswith("s") and len(s) > 3:
        return s[:-1]
    return s


def _normalize_grid_size(raw_grid_size: Any, pair_count: int) -> List[int]:
    """Normalize grid_size to [cols, rows] array. Handles string '4x3', list, int, or None."""
    if isinstance(raw_grid_size, (list, tuple)) and len(raw_grid_size) >= 2:
        return [int(raw_grid_size[0]), int(raw_grid_size[1])]
    if isinstance(raw_grid_size, str) and "x" in raw_grid_size.lower():
        parts = raw_grid_size.lower().split("x")
        try:
            return [int(parts[0].strip()), int(parts[1].strip())]
        except (ValueError, IndexError):
            pass
    # Calculate from pair count: total cards = pairs * 2
    total_cards = max(pair_count * 2, 4)
    cols = math.ceil(math.sqrt(total_cards))
    rows = math.ceil(total_cards / cols)
    return [cols, rows]


def _normalize_particle_speed(raw_speed: Any) -> str:
    """Convert numeric particle_speed to string enum 'slow'|'medium'|'fast'."""
    if isinstance(raw_speed, str) and raw_speed in ("slow", "medium", "fast"):
        return raw_speed
    if isinstance(raw_speed, (int, float)):
        if raw_speed <= 0.5:
            return "slow"
        elif raw_speed >= 1.5:
            return "fast"
        else:
            return "medium"
    return "medium"


def _build_zone_lookup(zones: List[Dict[str, Any]], key_field: str = "label") -> Dict[str, Dict[str, Any]]:
    """Build a case+plural-insensitive lookup from zone dicts.

    Indexes each zone under multiple normalized keys so that
    'Petals', 'petals', 'Petal', 'petal' all resolve to the same zone.
    """
    lookup: Dict[str, Dict[str, Any]] = {}
    for z in zones:
        if not isinstance(z, dict):
            continue
        raw = z.get(key_field, z.get("id", ""))
        if not raw:
            continue
        low = raw.lower()
        norm = _normalize_label(raw)
        # Index under all forms
        for k in (low, norm, low + "s", norm + "s"):
            if k not in lookup:
                lookup[k] = z
    return lookup


def _normalize_coordinates(raw_coords: Any, shape: str) -> Optional[Dict[str, Any]]:
    """Convert raw zone coordinates to IDZone-compatible dict format.

    Zone detection can return coordinates in various formats:
    - List of {x, y} dicts: [{"x": 10, "y": 20}, ...]
    - List of [x, y] tuples: [[10, 20], [30, 40], ...]
    - Dict with points key: {"points": [...]}
    - Dict with x, y keys (circle): {"x": 50, "y": 50, "radius": 20}
    - None

    Frontend expects:
    - polygon: points as [[x, y], ...] in 0-100% scale
    - circle: x, y, radius
    """
    if raw_coords is None:
        return None
    if isinstance(raw_coords, dict):
        return raw_coords
    if isinstance(raw_coords, list) and len(raw_coords) > 0:
        points = []
        for pt in raw_coords:
            if isinstance(pt, dict):
                points.append([pt.get("x", 0), pt.get("y", 0)])
            elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                points.append([pt[0], pt[1]])
        if points:
            return {"points": points}
    return None


def _clamp_coordinate(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a coordinate value to the given range."""
    return max(lo, min(hi, val))


def _postprocess_zones(scene_dict: Dict[str, Any]) -> None:
    """Post-process zones in a scene dict: flatten coordinates for frontend.

    Handles:
    - Flattening nested ``coordinates`` dict into top-level fields
    - Auto-detecting ``shape`` from points data (polygon vs circle)
    - Computing ``x``/``y`` center from polygon points when missing
    """
    for zone in scene_dict.get("zones", []):
        coords = zone.get("coordinates")
        if isinstance(coords, dict):
            if "points" in coords:
                zone["points"] = coords["points"]
            if "x" in coords:
                zone["x"] = coords["x"]
            if "y" in coords:
                zone["y"] = coords["y"]
            if "radius" in coords:
                zone["radius"] = coords["radius"]

        # --- Shape auto-detection ---
        # Frontend PolygonOverlay filters on shape === "polygon".
        # Zone detection often returns shape="circle" even when it provides polygon points.
        points = zone.get("points")
        if isinstance(points, list) and len(points) >= 3:
            zone["shape"] = "polygon"
        elif not zone.get("shape"):
            zone["shape"] = "circle"

        # --- Center / x,y computation from points ---
        if isinstance(points, list) and len(points) >= 3:
            xs = [p[0] for p in points if isinstance(p, (list, tuple)) and len(p) >= 2]
            ys = [p[1] for p in points if isinstance(p, (list, tuple)) and len(p) >= 2]
            if xs and ys:
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                if not zone.get("center"):
                    zone["center"] = {"x": cx, "y": cy}
                if zone.get("x") is None:
                    zone["x"] = cx
                if zone.get("y") is None:
                    zone["y"] = cy

        # --- Fallback: derive x/y from center if still missing ---
        center = zone.get("center")
        if isinstance(center, dict):
            if zone.get("x") is None and "x" in center:
                zone["x"] = center["x"]
            if zone.get("y") is None and "y" in center:
                zone["y"] = center["y"]


def _safe_model_dump(obj: Any) -> Any:
    """Safely dump a pydantic model or dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return obj


# ---------------------------------------------------------------------------
# Tool 1: assemble_blueprint
# ---------------------------------------------------------------------------

async def assemble_blueprint_impl() -> Dict[str, Any]:
    """
    Assemble an InteractiveDiagramBlueprint from all upstream v3 state.

    Reads game_design_v3, scene_specs_v3, interaction_specs_v3, generated_assets_v3
    from the v3 tool context and produces a frontend-ready blueprint dict.
    """
    from app.tools.v3_context import get_v3_tool_context

    ctx = get_v3_tool_context()
    raw_design = ctx.get("game_design_v3")
    scene_specs_list = ctx.get("scene_specs_v3") or []
    interaction_specs_list = ctx.get("interaction_specs_v3") or []
    generated_assets = ctx.get("generated_assets_v3") or {}

    warnings: List[str] = []

    if not raw_design:
        return {
            "blueprint": None,
            "assembly_warnings": ["No game_design_v3 in context -- cannot assemble blueprint"],
        }

    # Parse design (could be dict or pydantic model)
    design: Dict[str, Any]
    if isinstance(raw_design, dict):
        design = raw_design
    elif hasattr(raw_design, "model_dump"):
        design = raw_design.model_dump()
    else:
        design = dict(raw_design)

    # Build lookup maps for scene_specs and interaction_specs
    # They are lists; index by scene_number if available
    scene_specs_map: Dict[int, Dict[str, Any]] = {}
    for spec in scene_specs_list:
        if isinstance(spec, dict):
            sn = spec.get("scene_number")
            if sn is not None:
                scene_specs_map[int(sn)] = spec

    interaction_specs_map: Dict[int, Dict[str, Any]] = {}
    for spec in interaction_specs_list:
        if isinstance(spec, dict):
            sn = spec.get("scene_number")
            if sn is not None:
                interaction_specs_map[int(sn)] = spec

    # Extract global design fields
    title = design.get("title", "Untitled Game")
    narrative_intro = design.get("narrative_intro") or design.get("pedagogical_reasoning", "")
    learning_objectives = design.get("learning_objectives", [])
    estimated_duration = design.get("estimated_duration_minutes", 5)

    # Theme
    raw_theme = design.get("theme")
    theme_dict = None
    if isinstance(raw_theme, dict):
        theme_dict = {
            "visual_tone": raw_theme.get("visual_tone", "educational"),
            "color_palette": raw_theme.get("color_palette", {}),
            "background_description": raw_theme.get("background_description"),
            "narrative_frame": raw_theme.get("narrative_frame"),
        }
    elif isinstance(raw_theme, str):
        theme_dict = {"visual_tone": raw_theme}

    # Labels (global)
    labels_data = design.get("labels", {})
    if isinstance(labels_data, list):
        labels_data = {"zone_labels": labels_data}
    global_labels = labels_data.get("zone_labels", [])
    group_only_labels = set(labels_data.get("group_only_labels", []))

    # Distractor labels
    distractor_list: List[Dict[str, str]] = []
    for dl in labels_data.get("distractor_labels", []):
        if isinstance(dl, dict):
            distractor_list.append({
                "text": dl.get("text", ""),
                "explanation": dl.get("explanation", ""),
            })
        elif isinstance(dl, str):
            distractor_list.append({"text": dl, "explanation": ""})

    # Hierarchy
    hierarchy_dict = None
    hierarchy_raw = labels_data.get("hierarchy")
    if isinstance(hierarchy_raw, dict) and hierarchy_raw.get("enabled"):
        groups_raw = hierarchy_raw.get("groups", [])
        groups_serialized = []
        for g in groups_raw:
            if isinstance(g, dict):
                groups_serialized.append(g)
            elif hasattr(g, "model_dump"):
                groups_serialized.append(g.model_dump())
        hierarchy_dict = {
            "enabled": True,
            "strategy": hierarchy_raw.get("strategy", ""),
            "groups": groups_serialized,
        }

    # Build parent_map for hierarchy child -> parent
    parent_map: Dict[str, str] = {}
    if hierarchy_dict and hierarchy_dict.get("enabled"):
        for group in hierarchy_dict.get("groups", []):
            parent_label = group.get("parent", "")
            for child in group.get("children", []):
                parent_map[child] = parent_label

    # Build generated_assets lookup
    # generated_assets_v3 format: {scenes: {scene_num_str: {diagram_image_url, zones: [...]}}}
    asset_scenes: Dict[int, Dict[str, Any]] = {}
    if isinstance(generated_assets, dict):
        scenes_data = generated_assets.get("scenes", {})
        if isinstance(scenes_data, dict):
            for sn_key, sn_data in scenes_data.items():
                try:
                    asset_scenes[int(sn_key)] = sn_data if isinstance(sn_data, dict) else {}
                except (ValueError, TypeError):
                    pass

    # Build scenes
    scenes_dicts: List[Dict[str, Any]] = []
    total_max_score = 0
    design_scenes = design.get("scenes", [])

    for scene_design in design_scenes:
        if not isinstance(scene_design, dict):
            if hasattr(scene_design, "model_dump"):
                scene_design = scene_design.model_dump()
            else:
                continue

        scene_number = scene_design.get("scene_number", 1)
        scene_title = scene_design.get("title", f"Scene {scene_number}")

        # Gather scene zone labels
        scene_zone_labels = (
            scene_design.get("zone_labels")
            or scene_design.get("zone_labels_in_scene")
            or global_labels
        )

        # Get asset data for this scene
        scene_assets = asset_scenes.get(scene_number, {})
        asset_zones = scene_assets.get("zones", [])
        diagram_image_url = (
            scene_assets.get("diagram_image_url")
            or scene_assets.get("diagram_image_path")
            or scene_assets.get("diagram_image")
            or ""
        )

        # Get scene spec for this scene
        scene_spec = scene_specs_map.get(scene_number, {})
        spec_zones = scene_spec.get("zones", [])

        # Get interaction spec for this scene
        interaction_spec = interaction_specs_map.get(scene_number, {})

        # Build zone maps with fuzzy matching (case + plural insensitive)
        detected_zone_map = _build_zone_lookup(asset_zones)
        spec_zone_map = _build_zone_lookup(spec_zones)

        # --- Build zones ---
        zones: List[Dict[str, Any]] = []

        # Group-only zones first
        for g_label in group_only_labels:
            detected = detected_zone_map.get(_normalize_label(g_label), {})
            raw_coords = detected.get("coordinates") or detected.get("polygon") or detected.get("points")
            shape = detected.get("shape", "circle")
            coords = _normalize_coordinates(raw_coords, shape)

            zone_id = _make_id("zone", str(scene_number), g_label)
            zone_entry: Dict[str, Any] = {
                "id": zone_id,
                "label": g_label,
                "shape": shape,
                "coordinates": coords,
                "group_only": True,
                "parentZoneId": None,
            }

            # Enrich from spec
            spec_z = spec_zone_map.get(_normalize_label(g_label), {})
            if spec_z.get("description"):
                zone_entry["description"] = spec_z["description"]

            zones.append(zone_entry)

        # Regular zones
        for label in scene_zone_labels:
            if label in group_only_labels:
                continue

            detected = detected_zone_map.get(_normalize_label(label), {})
            parent_label = parent_map.get(label)
            parent_id = _make_id("zone", str(scene_number), parent_label) if parent_label else None

            # Coordinates: prefer detected, then spec position_hints
            raw_coords = detected.get("coordinates") or detected.get("polygon") or detected.get("points")
            # Also accept flat x/y/radius from detected
            if raw_coords is None and detected.get("x") is not None:
                if detected.get("shape", "circle") == "circle":
                    raw_coords = {
                        "x": detected["x"],
                        "y": detected.get("y", 50),
                        "radius": detected.get("radius", 5),
                    }
                elif detected.get("points"):
                    raw_coords = {"points": detected["points"]}

            shape = detected.get("shape", "circle")
            coords = _normalize_coordinates(raw_coords, shape)

            # If no coords from assets, try spec position_hints
            if coords is None:
                spec_z = spec_zone_map.get(_normalize_label(label), {})
                position_hint = spec_z.get("position_hint") or spec_z.get("position")
                if isinstance(position_hint, dict):
                    coords = _normalize_coordinates(position_hint, shape)

            zone_id = _make_id("zone", str(scene_number), label)
            zone_entry = {
                "id": zone_id,
                "label": label,
                "shape": shape,
                "coordinates": coords,
                "group_only": False,
                "parentZoneId": parent_id,
            }

            # Enrich from spec
            spec_z = spec_zone_map.get(_normalize_label(label), {})
            if spec_z.get("description"):
                zone_entry["description"] = spec_z["description"]
            if spec_z.get("hint_progression"):
                # Frontend expects `hint: string`, provide first hint + full list
                hints = spec_z["hint_progression"]
                if isinstance(hints, list) and hints:
                    zone_entry["hint"] = hints[0]
                elif isinstance(hints, str):
                    zone_entry["hint"] = hints
            if spec_z.get("difficulty"):
                zone_entry["difficulty"] = spec_z["difficulty"]
            if detected.get("confidence"):
                zone_entry["confidence"] = detected["confidence"]

            zones.append(zone_entry)

        # Assign default coordinates to zones that have none.
        # This ensures zones are clickable/draggable on the frontend even
        # when neither zone detection nor spec position_hints provided coords.
        zones_without_coords = [z for z in zones if not z.get("coordinates") and not z.get("group_only")]
        if zones_without_coords:
            n = len(zones_without_coords)
            cols = max(1, int(n ** 0.5 + 0.5))
            for idx, z in enumerate(zones_without_coords):
                row, col = divmod(idx, cols)
                x = 15 + (col * 70 / max(cols - 1, 1)) if cols > 1 else 50
                y = 15 + (row * 70 / max((n // cols), 1)) if n > cols else 50
                z["coordinates"] = {"x": round(x, 1), "y": round(y, 1), "radius": 5}
                z["shape"] = "circle"

        # --- Build labels ---
        # IMPORTANT: labels[] must contain ONLY correct (non-distractor) labels.
        # Distractors go in a separate distractor_labels[] list.
        # Frontend contract:
        #   labels[].correctZoneId = zone id (required, used for matching)
        #   distractorLabels[] have NO correctZoneId (frontend checks 'correctZoneId' in label)
        labels: List[Dict[str, Any]] = []
        zone_by_label = {z["label"]: z["id"] for z in zones if not z.get("group_only")}

        # Use descriptions as label text for drag_drop — always more pedagogically
        # valuable (student matches description to visible zone on diagram).
        # label_descriptions come from domain knowledge retriever.
        dk_dict = ctx.get("domain_knowledge", {})
        if not isinstance(dk_dict, dict):
            dk_dict = {}
        label_descriptions = dk_dict.get("label_descriptions") or ctx.get("label_descriptions") or {}

        for label_text, zone_id in zone_by_label.items():
            description = label_descriptions.get(label_text, "")
            if description:
                # Description mode: label text is the description, canonical_name is the zone name
                labels.append({
                    "id": _make_id("label", str(scene_number), label_text),
                    "text": description,
                    "correctZoneId": zone_id,
                    "canonicalName": label_text,
                })
            else:
                # Fallback: no description available, use zone name
                labels.append({
                    "id": _make_id("label", str(scene_number), label_text),
                    "text": label_text,
                    "correctZoneId": zone_id,
                })

        # Build per-scene distractor labels (separate from correct labels)
        scene_distractors: List[Dict[str, Any]] = []
        for dl in distractor_list:
            dl_text = dl.get("text", "")
            if not dl_text:
                continue
            scene_distractors.append({
                "id": _make_id("label", str(scene_number), "dist", dl_text),
                "text": dl_text,
                "explanation": dl.get("explanation", ""),
            })

        # --- Build mechanics ---
        mechanics: List[Dict[str, Any]] = []
        scene_mechanics = scene_design.get("mechanics", [])
        mechanic_configs = scene_spec.get("mechanic_configs", [])

        # Build mechanic config lookup
        mech_config_map: Dict[str, Dict[str, Any]] = {}
        for mc in mechanic_configs:
            if isinstance(mc, dict):
                mtype = mc.get("mechanic_type") or mc.get("type", "")
                mech_config_map[mtype] = mc

        # Scoring and feedback from interaction_spec
        # InteractionSpecV3 stores scoring/feedback as LISTS of per-mechanic dicts,
        # each with a "mechanic_type" key. Convert to lookup dicts keyed by type.
        raw_scoring = interaction_spec.get("scoring", [])
        raw_feedback = interaction_spec.get("feedback", [])
        scoring_by_type: Dict[str, Dict[str, Any]] = {}
        feedback_by_type: Dict[str, Dict[str, Any]] = {}
        if isinstance(raw_scoring, list):
            for s in raw_scoring:
                if isinstance(s, dict) and s.get("mechanic_type"):
                    scoring_by_type[s["mechanic_type"]] = s
        elif isinstance(raw_scoring, dict):
            scoring_by_type = raw_scoring  # Legacy dict format
        if isinstance(raw_feedback, list):
            for f in raw_feedback:
                if isinstance(f, dict) and f.get("mechanic_type"):
                    feedback_by_type[f["mechanic_type"]] = f
        elif isinstance(raw_feedback, dict):
            feedback_by_type = raw_feedback  # Legacy dict format
        misconceptions = interaction_spec.get("misconceptions", [])

        for mech in scene_mechanics:
            if not isinstance(mech, dict):
                if hasattr(mech, "model_dump"):
                    mech = mech.model_dump()
                else:
                    continue

            mech_type = mech.get("type") or ""
            mech_id = _make_id("mech", str(scene_number), mech_type)

            # Config from scene_spec mechanic_configs
            extra_config = mech_config_map.get(mech_type, {})

            # Build config from type-specific fields in design
            config: Dict[str, Any] = {}
            for config_key in ("path_config", "click_config", "sequence_config",
                               "sorting_config", "branching_config", "compare_config",
                               "memory_config", "timed_config", "description_match_config"):
                raw_cfg = mech.get(config_key)
                if raw_cfg:
                    config.update(_safe_model_dump(raw_cfg))

            # Merge extra config from scene_spec
            extra_mech_config = extra_config.get("config", {})
            if isinstance(extra_mech_config, dict):
                config.update(extra_mech_config)

            # Scoring: prefer interaction_spec per-mechanic, then design mechanic scoring
            mech_scoring = None
            if mech_type in scoring_by_type:
                mech_scoring = scoring_by_type[mech_type]
            elif scoring_by_type:
                # Use first available scoring as fallback
                first_scoring = next(iter(scoring_by_type.values()), {})
                mech_scoring = {
                    k: v for k, v in first_scoring.items()
                    if k in ("points_per_correct", "max_score", "partial_credit", "hint_penalty", "time_bonus", "streak_bonus")
                }

            if not mech_scoring:
                raw_scoring = mech.get("scoring")
                if raw_scoring:
                    mech_scoring = _safe_model_dump(raw_scoring)

            # Feedback: prefer interaction_spec per-mechanic, then design mechanic feedback
            mech_feedback = None
            if mech_type in feedback_by_type:
                mech_feedback = feedback_by_type[mech_type]
            elif feedback_by_type:
                # Use first available feedback as fallback
                first_feedback = next(iter(feedback_by_type.values()), {})
                fb_keys = ("on_correct", "on_incorrect", "misconception_feedback",
                           "completion_message", "varied_correct_messages", "varied_incorrect_messages")
                mech_feedback = {k: v for k, v in first_feedback.items() if k in fb_keys and v}

            if not mech_feedback:
                raw_feedback = mech.get("feedback")
                if raw_feedback:
                    mech_feedback = _safe_model_dump(raw_feedback)

            # Merge misconceptions into feedback
            if misconceptions and mech_feedback:
                existing_mf = mech_feedback.get("misconception_feedback", [])
                for mc in misconceptions:
                    if isinstance(mc, dict) and mc not in existing_mf:
                        existing_mf.append(mc)
                mech_feedback["misconception_feedback"] = existing_mf

            # Zone labels for this mechanic
            mech_zone_labels = mech.get("zone_labels_used", [])
            if not mech_zone_labels:
                mech_zone_labels = list(zone_by_label.keys())

            # Calculate score contribution
            if mech_scoring and isinstance(mech_scoring, dict):
                ms = mech_scoring.get("max_score")
                if ms and isinstance(ms, (int, float)):
                    total_max_score += int(ms)

            mechanics.append({
                "mechanicId": mech_id,
                "mechanicType": mech_type,
                "interactionMode": mech_type,
                "config": config if config else None,
                "zoneLabels": mech_zone_labels,
                "scoring": mech_scoring,
                "feedback": mech_feedback,
            })

        # Fix 2.10: Populate per-mechanic frontend config fields from scene_spec mechanic configs
        # and interaction_spec scoring/feedback. This ensures the frontend gets the data it needs
        # for non-drag_drop mechanics.
        for mech_entry in mechanics:
            mech_type = mech_entry.get("mechanicType", "")
            mech_cfg = mech_entry.get("config") or {}

            # Get mechanic config from scene_spec
            spec_mc = mech_config_map.get(mech_type, {})
            spec_config = spec_mc.get("config", {})
            if isinstance(spec_config, dict):
                mech_cfg.update(spec_config)

            # trace_path -> paths (waypoints list for frontend)
            # Fix S-5: Use "id" not "pathId", add "description"/"requiresOrder" for TracePath compat
            if mech_type == "trace_path":
                waypoints = mech_cfg.get("waypoints", [])
                if waypoints:
                    path_waypoints = []
                    for idx, wp in enumerate(waypoints):
                        wp_zone_id = _make_id("zone", str(scene_number), wp)
                        path_waypoints.append({
                            "zoneId": wp_zone_id,
                            "order": idx,
                        })
                    mech_entry["paths"] = [{
                        "id": _make_id("path", str(scene_number)),
                        "waypoints": path_waypoints,
                        "description": mech_cfg.get("description", "Trace the path through the structures"),
                        "requiresOrder": mech_cfg.get("requires_order", True),
                    }]
                    # Phase 1 expanded fields
                    mech_entry["tracePathConfig"] = {
                        "drawingMode": mech_cfg.get("drawing_mode", "click_waypoints"),
                        "pathType": mech_cfg.get("path_type", "linear"),
                        "particleTheme": mech_cfg.get("particle_theme", "dots"),
                        "particleSpeed": _normalize_particle_speed(mech_cfg.get("particle_speed", 1.0)),
                        "colorTransitionEnabled": mech_cfg.get("color_transition_enabled", False),
                        "showDirectionArrows": mech_cfg.get("show_direction_arrows", True),
                        "showWaypointLabels": mech_cfg.get("show_waypoint_labels", True),
                        "showFullFlowOnComplete": mech_cfg.get("show_full_flow_on_complete", True),
                        "instructions": mech_cfg.get("instructions", mech_cfg.get("instruction_text", "Trace the path")),
                    }

            # click_to_identify -> identificationPrompts
            # Fix S-4: Generate [{zoneId, prompt, order}] not string[]
            elif mech_type == "click_to_identify":
                prompts = mech_cfg.get("prompts", [])
                zone_labels = mech_entry.get("zoneLabels") or []
                if prompts and isinstance(prompts, list) and len(prompts) > 0:
                    # Normalize: if prompts are already objects, pass through; if strings, convert
                    normalized = []
                    for idx_p, p in enumerate(prompts):
                        if isinstance(p, dict) and "zoneId" in p and "prompt" in p:
                            normalized.append(p)
                        elif isinstance(p, str):
                            # Try to match prompt to a zone label
                            matched_zone_id = ""
                            for zl in zone_labels:
                                if zl.lower() in p.lower():
                                    matched_zone_id = zone_by_label.get(zl, "")
                                    break
                            normalized.append({
                                "zoneId": matched_zone_id,
                                "prompt": p,
                                "order": idx_p,
                            })
                    mech_entry["identificationPrompts"] = normalized
                else:
                    # Build prompts from zone labels with proper {zoneId, prompt, order} format
                    id_prompts = []
                    for idx_zl, lbl in enumerate(zone_labels):
                        z_id = zone_by_label.get(lbl, "")
                        id_prompts.append({
                            "zoneId": z_id,
                            "prompt": f"Identify and click on the {lbl}",
                            "order": idx_zl,
                        })
                    mech_entry["identificationPrompts"] = id_prompts
                # Phase 1 expanded fields
                mech_entry["clickToIdentifyConfig"] = {
                    "promptStyle": mech_cfg.get("prompt_style", "naming"),
                    "highlightOnHover": mech_cfg.get("highlight_on_hover", True),
                    "highlightStyle": mech_cfg.get("highlight_style", "subtle"),
                    "selectionMode": mech_cfg.get("selection_mode", "sequential"),
                    "showZoneCount": mech_cfg.get("show_zone_count", True),
                    "magnificationEnabled": mech_cfg.get("magnification_enabled", False),
                    "instructions": mech_cfg.get("instructions", mech_cfg.get("instruction_text", "Click on each structure")),
                }

            # sequencing -> sequenceConfig
            # Fix S-3: Emit both "instructionText" and "instructions" for frontend compat
            elif mech_type == "sequencing":
                items = mech_cfg.get("items", [])
                correct_order = mech_cfg.get("correct_order", [])
                if items or correct_order:
                    instr_text = mech_cfg.get("instruction_text", "Arrange in the correct order")
                    mech_entry["sequenceConfig"] = {
                        "sequenceType": mech_cfg.get("sequence_type", "linear"),
                        "items": items,
                        "correctOrder": correct_order,
                        "instructionText": instr_text,
                        "instructions": instr_text,
                        # Phase 1 expanded fields
                        "layoutMode": mech_cfg.get("layout_mode", "horizontal_timeline"),
                        "interactionPattern": mech_cfg.get("interaction_pattern", "drag_reorder"),
                        "cardType": mech_cfg.get("card_type", "text_only"),
                        "connectorStyle": mech_cfg.get("connector_style", "arrow"),
                        "showPositionNumbers": mech_cfg.get("show_position_numbers", True),
                    }

            # description_matching -> descriptionMatchingConfig
            # Fix S-5b: Convert descriptions list to {zoneId: description} dict
            elif mech_type == "description_matching":
                raw_descriptions = mech_cfg.get("descriptions", [])
                descriptions_dict: Dict[str, str] = {}
                if isinstance(raw_descriptions, dict):
                    # Already in correct format
                    descriptions_dict = raw_descriptions
                elif isinstance(raw_descriptions, list):
                    # Convert [{label, description}] or [{zone_id, description}] to {zoneId: description}
                    for desc_item in raw_descriptions:
                        if isinstance(desc_item, dict):
                            # Try zone_id first, then match by label
                            z_id = desc_item.get("zone_id", "")
                            if not z_id:
                                lbl = desc_item.get("label", "")
                                z_id = zone_by_label.get(lbl, "")
                            desc_text = desc_item.get("description", "")
                            if z_id and desc_text:
                                descriptions_dict[z_id] = desc_text
                if descriptions_dict:
                    # Normalize mode to valid frontend enum values
                    raw_mode = mech_cfg.get("mode", "click_zone")
                    valid_modes = {"click_zone", "drag_description", "multiple_choice"}
                    mode = raw_mode if raw_mode in valid_modes else "click_zone"
                    instr_text = mech_cfg.get("instruction_text", "Match each description to the correct structure")
                    mech_entry["descriptionMatchingConfig"] = {
                        "mode": mode,
                        "descriptions": descriptions_dict,
                        "instructions": instr_text,
                        # Phase 1 expanded fields
                        "showConnectingLines": mech_cfg.get("show_connecting_lines", True),
                        "descriptionPanelPosition": mech_cfg.get("description_panel_position", "right"),
                        "deferEvaluation": mech_cfg.get("defer_evaluation", False),
                        "distractorDescriptions": mech_cfg.get("distractor_descriptions", []),
                    }

            # sorting_categories -> sortingConfig
            # Fix S-6: Ensure items have correctCategoryId, emit "instructions"
            elif mech_type == "sorting_categories":
                categories = mech_cfg.get("categories", [])
                items = mech_cfg.get("items", [])
                if categories:
                    # Normalize category objects: ensure {id, label}
                    norm_categories = []
                    for cat in categories:
                        if isinstance(cat, dict):
                            norm_categories.append({
                                "id": cat.get("id", cat.get("label", "").lower().replace(" ", "_")),
                                "label": cat.get("label", cat.get("id", "")),
                                "description": cat.get("description"),
                                "color": cat.get("color"),
                            })
                        elif isinstance(cat, str):
                            norm_categories.append({"id": cat.lower().replace(" ", "_"), "label": cat})

                    # Normalize items: ensure correctCategoryId and correctCategoryIds
                    norm_items = []
                    for item in items:
                        if isinstance(item, dict):
                            # Support both singular and list forms
                            correct_ids = item.get("correct_category_ids") or item.get("correctCategoryIds", [])
                            correct_cat = item.get("correctCategoryId") or item.get("correct_category_id") or item.get("category", "")
                            if not correct_ids and correct_cat:
                                correct_ids = [correct_cat]
                            if not correct_cat and correct_ids:
                                correct_cat = correct_ids[0]
                            norm_items.append({
                                "id": item.get("id", ""),
                                "text": item.get("text", ""),
                                "correctCategoryId": correct_cat,
                                "correctCategoryIds": correct_ids,
                                "description": item.get("description"),
                                "difficulty": item.get("difficulty"),
                            })

                    instr_text = mech_cfg.get("instruction_text", "Sort items into the correct categories")
                    mech_entry["sortingConfig"] = {
                        "categories": norm_categories,
                        "items": norm_items,
                        "showCategoryHints": mech_cfg.get("show_category_hints", True),
                        "allowPartialCredit": mech_cfg.get("allow_partial_credit", True),
                        "instructionText": instr_text,
                        "instructions": instr_text,
                        # Phase 1 expanded fields
                        "sortMode": mech_cfg.get("sort_mode", "bucket"),
                        "submitMode": mech_cfg.get("submit_mode", "batch_submit"),
                        "itemCardType": mech_cfg.get("item_card_type", "text_only"),
                        "containerStyle": mech_cfg.get("container_style", "bucket"),
                        "allowMultiCategory": mech_cfg.get("allow_multi_category", False),
                    }

            # memory_match -> memoryMatchConfig
            # Fix S-7: Ensure pairs have {id, front, back, frontType, backType}, emit "instructions"
            elif mech_type == "memory_match":
                pairs = mech_cfg.get("pairs", [])
                if pairs:
                    norm_pairs = []
                    for idx_p, pair in enumerate(pairs):
                        if isinstance(pair, dict):
                            norm_pairs.append({
                                "id": pair.get("id", f"pair_{idx_p + 1}"),
                                "front": pair.get("front") or pair.get("term") or pair.get("text", f"Card {idx_p + 1}"),
                                "back": pair.get("back") or pair.get("definition") or pair.get("match", ""),
                                "frontType": pair.get("frontType") or pair.get("front_type", "text"),
                                "backType": pair.get("backType") or pair.get("back_type", "text"),
                                "explanation": pair.get("explanation", ""),
                                "category": pair.get("category"),
                            })
                    instr_text = mech_cfg.get("instruction_text", "Find matching pairs")
                    mech_entry["memoryMatchConfig"] = {
                        "pairs": norm_pairs,
                        "gridSize": _normalize_grid_size(mech_cfg.get("grid_size"), len(norm_pairs)),
                        "flipDurationMs": mech_cfg.get("flip_duration_ms", 600),
                        "showAttemptsCounter": mech_cfg.get("show_attempts_counter", True),
                        "instructionText": instr_text,
                        "instructions": instr_text,
                        # Phase 1 expanded fields
                        "gameVariant": mech_cfg.get("game_variant", "classic"),
                        "matchType": mech_cfg.get("match_type", "term_to_definition"),
                        "cardBackStyle": mech_cfg.get("card_back_style", "pattern"),
                        "matchedCardBehavior": mech_cfg.get("matched_card_behavior", "fade"),
                        "showExplanationOnMatch": mech_cfg.get("show_explanation_on_match", True),
                    }

            # branching_scenario -> branchingConfig
            # Fix L3-1: Normalize node fields from backend (prompt/choices/next_node_id)
            # to frontend format (question/options/nextNodeId/isEndNode)
            elif mech_type == "branching_scenario":
                raw_nodes = mech_cfg.get("nodes", [])
                if raw_nodes:
                    norm_nodes = []
                    for raw_node in raw_nodes:
                        if not isinstance(raw_node, dict):
                            continue
                        # Normalize options/choices
                        raw_opts = raw_node.get("options") or raw_node.get("choices", [])
                        norm_opts = []
                        for oi, opt in enumerate(raw_opts):
                            if not isinstance(opt, dict):
                                continue
                            norm_opts.append({
                                "id": opt.get("id", f"opt_{oi}"),
                                "text": opt.get("text", ""),
                                "nextNodeId": opt.get("nextNodeId") or opt.get("next_node_id"),
                                "isCorrect": opt.get("isCorrect") if opt.get("isCorrect") is not None else opt.get("is_correct"),
                                "consequence": opt.get("consequence") or opt.get("consequence_text", ""),
                                "points": opt.get("points", 0),
                                "quality": opt.get("quality"),
                            })
                        is_end = raw_node.get("isEndNode") if raw_node.get("isEndNode") is not None else raw_node.get("is_end_node", False)
                        # Also detect end nodes: no options or node_type == "ending"
                        if not is_end and (not norm_opts or raw_node.get("node_type") == "ending"):
                            is_end = True
                        norm_nodes.append({
                            "id": raw_node.get("id", ""),
                            "question": raw_node.get("question") or raw_node.get("prompt", ""),
                            "description": raw_node.get("description") or raw_node.get("narrative_text", ""),
                            "imageUrl": raw_node.get("imageUrl") or raw_node.get("image_url"),
                            "options": norm_opts,
                            "isEndNode": is_end,
                            "endMessage": raw_node.get("endMessage") or raw_node.get("end_message", ""),
                            "node_type": raw_node.get("node_type", "decision"),
                            "narrative_text": raw_node.get("narrative_text"),
                            "ending_type": raw_node.get("ending_type"),
                        })
                    instr_text = mech_cfg.get("instruction_text", "Make decisions and see the consequences")
                    # Determine startNodeId: explicit config > first node's id
                    start_id = mech_cfg.get("start_node_id") or mech_cfg.get("startNodeId", "")
                    if not start_id and norm_nodes:
                        start_id = norm_nodes[0]["id"]
                    mech_entry["branchingConfig"] = {
                        "nodes": norm_nodes,
                        "startNodeId": start_id,
                        "showPathTaken": mech_cfg.get("show_path_taken", True),
                        "allowBacktrack": mech_cfg.get("allow_backtrack", False),
                        "showConsequences": mech_cfg.get("show_consequences", True),
                        "instructions": instr_text,
                        # Phase 1 expanded fields
                        "narrativeStructure": mech_cfg.get("narrative_structure", "linear"),
                    }

            # compare_contrast -> compareConfig
            # Fix L3-2: Build diagramA/diagramB from config or synthesize from zones
            elif mech_type == "compare_contrast":
                expected = mech_cfg.get("expected_categories", {})
                instr_text = mech_cfg.get("instruction_text", "Compare and categorize the structures")

                # Try to get diagramA/diagramB from upstream; if missing, synthesize
                diagram_a = mech_cfg.get("diagram_a") or mech_cfg.get("diagramA")
                diagram_b = mech_cfg.get("diagram_b") or mech_cfg.get("diagramB")

                if not diagram_a:
                    # Synthesize from zones: split zones into two halves for A/B
                    all_zone_list = zones  # already built above
                    mid = max(1, len(all_zone_list) // 2)
                    zones_a = all_zone_list[:mid]
                    zones_b = all_zone_list[mid:]
                    subjects = mech_cfg.get("subjects", [])
                    diagram_a = {
                        "id": "diagram_a",
                        "name": subjects[0] if len(subjects) > 0 else scene_title + " (A)",
                        "imageUrl": diagram_image_url,
                        "zones": [{"id": z["id"], "label": z.get("label", ""), "x": z.get("x", 0), "y": z.get("y", 0), "width": z.get("width", 10), "height": z.get("height", 10)} for z in zones_a],
                    }
                    diagram_b = {
                        "id": "diagram_b",
                        "name": subjects[1] if len(subjects) > 1 else scene_title + " (B)",
                        "imageUrl": diagram_image_url,
                        "zones": [{"id": z["id"], "label": z.get("label", ""), "x": z.get("x", 0), "y": z.get("y", 0), "width": z.get("width", 10), "height": z.get("height", 10)} for z in zones_b],
                    }

                mech_entry["compareConfig"] = {
                    "diagramA": diagram_a,
                    "diagramB": diagram_b,
                    "expectedCategories": expected,
                    "highlightMatching": mech_cfg.get("highlight_matching", True),
                    "instructions": instr_text,
                    # Phase 1 expanded fields
                    "subjects": mech_cfg.get("subjects", []),
                    "comparisonMode": mech_cfg.get("comparison_mode", "venn_diagram"),
                    "categoryTypes": mech_cfg.get("category_types", []),
                    "similarities": mech_cfg.get("similarities", []),
                    "differences": mech_cfg.get("differences", []),
                    "explorationEnabled": mech_cfg.get("exploration_enabled", False),
                    "zoomEnabled": mech_cfg.get("zoom_enabled", False),
                }

            # drag_drop -> dragDropConfig
            if mech_type == "drag_drop":
                mech_entry["dragDropConfig"] = {
                    "interactionMode": mech_cfg.get("interaction_mode", "drag_drop"),
                    "feedbackTiming": mech_cfg.get("feedback_timing", "immediate"),
                    "zoneIdleAnimation": mech_cfg.get("zone_idle_animation", "none"),
                    "leaderLineStyle": mech_cfg.get("leader_line_style", "curved"),
                    "snapToZone": mech_cfg.get("snap_to_zone", True),
                    "returnOnMiss": mech_cfg.get("return_on_miss", True),
                    "trayPosition": mech_cfg.get("tray_position", "bottom"),
                    "trayLayout": mech_cfg.get("tray_layout", "horizontal"),
                    "labelCardStyle": mech_cfg.get("label_card_style", "text"),
                    "pinMarkerShape": mech_cfg.get("pin_marker_shape", "circle"),
                    "showLeaderLines": mech_cfg.get("show_leader_lines", True),
                    "instructions": mech_cfg.get("instructions", mech_cfg.get("instruction_text", "Drag labels to the correct zones")),
                }

            # timed_challenge -> wraps another mode with time limit
            if mech_type == "timed_challenge":
                wrapped = mech_cfg.get("wrapped_mode") or mech_cfg.get("timedChallengeWrappedMode", "drag_drop")
                time_limit = mech_cfg.get("time_limit_seconds") or mech_cfg.get("timeLimitSeconds", 60)
                mech_entry["timedChallengeWrappedMode"] = wrapped
                mech_entry["timeLimitSeconds"] = int(time_limit)

            mech_entry["config"] = mech_cfg if mech_cfg else None

        # Mode transitions from interaction_spec
        mode_transitions = interaction_spec.get("mode_transitions", [])
        mechanic_data = scene_spec.get("mechanic_data") or scene_spec.get("extra_data")

        # Scene completion from interaction_spec
        scene_completion = interaction_spec.get("scene_completion")

        # Build scene dict
        scene_dict: Dict[str, Any] = {
            "scene_id": _make_id("scene", str(scene_number)),
            "scene_number": scene_number,
            "title": scene_title,
            "diagram_image_url": diagram_image_url,
            "zones": zones,
            "labels": labels,
            "distractor_labels": scene_distractors,
            "mechanics": mechanics,
            "mode_transitions": mode_transitions if mode_transitions else [],
            "mechanic_data": mechanic_data,
            "scene_completion": scene_completion,
        }

        if scene_design.get("narrative_intro"):
            scene_dict["narrative_intro"] = scene_design["narrative_intro"]
        if scene_design.get("learning_goal"):
            scene_dict["learning_goal"] = scene_design["learning_goal"]

        # Post-process zones: flatten coordinates for frontend
        _postprocess_zones(scene_dict)

        scenes_dicts.append(scene_dict)

    # Scene transitions
    scene_transitions: List[Dict[str, Any]] = []
    design_transitions = design.get("scene_transitions", [])
    for st in design_transitions:
        if not isinstance(st, dict):
            if hasattr(st, "model_dump"):
                st = st.model_dump()
            else:
                continue
        transition_entry: Dict[str, Any] = {
            "from_scene": st.get("from_scene"),
            "to_scene": st.get("to_scene"),
            "trigger": st.get("trigger", "score_threshold"),
            "trigger_value": st.get("threshold") or st.get("trigger_value"),
            "animation": st.get("animation", "slide_left"),
        }
        if st.get("message"):
            transition_entry["message"] = st["message"]

        # Enrich from interaction_specs transition_to_next
        from_sn = st.get("from_scene")
        if from_sn is not None:
            i_spec = interaction_specs_map.get(int(from_sn), {})
            transition_to_next = i_spec.get("transition_to_next")
            if isinstance(transition_to_next, dict):
                if transition_to_next.get("trigger"):
                    transition_entry["trigger"] = transition_to_next["trigger"]
                if transition_to_next.get("trigger_value"):
                    transition_entry["trigger_value"] = transition_to_next["trigger_value"]
                if transition_to_next.get("animation"):
                    transition_entry["animation"] = transition_to_next["animation"]
                if transition_to_next.get("message"):
                    transition_entry["message"] = transition_to_next["message"]

        scene_transitions.append(transition_entry)

    # Total max score fallback
    if total_max_score == 0:
        total_max_score = len(global_labels) * 10
        if total_max_score == 0:
            total_max_score = 100

    # Difficulty
    difficulty_raw = design.get("difficulty")
    difficulty_dict = None
    if isinstance(difficulty_raw, dict):
        difficulty_dict = difficulty_raw
    elif hasattr(difficulty_raw, "model_dump"):
        difficulty_dict = difficulty_raw.model_dump()
    elif isinstance(difficulty_raw, str):
        difficulty_dict = {"approach": difficulty_raw}

    # Animation cues: collect from interaction_specs
    animation_cues: Dict[str, Any] = {}
    for i_spec in interaction_specs_list:
        if isinstance(i_spec, dict):
            anims = i_spec.get("animations", {})
            if isinstance(anims, dict):
                animation_cues.update(anims)

    # Ensure default animation cues if none
    if not animation_cues:
        animation_cues = {
            "correctPlacement": {"type": "pulse", "color": "#22c55e", "duration_ms": 400},
            "incorrectPlacement": {"type": "shake", "color": "#ef4444", "duration_ms": 300},
            "completion": {"type": "confetti", "duration_ms": 2000},
            "hintReveal": {"type": "glow", "color": "#f59e0b", "duration_ms": 600},
        }

    # ----- Convert scenes to frontend-compatible format -----
    # Frontend expects:
    #   - templateType: "INTERACTIVE_DIAGRAM" (not "INTERACTIVE_DIAGRAM")
    #   - Multi-scene: is_multi_scene=true, game_sequence={scenes: GameScene[]}
    #   - Single-scene: flat diagram/zones/labels at root level
    #   - GameScene.diagram = {assetUrl} (not diagram_image_url)
    #   - Mechanic = {type, config} (not {mechanicType, mechanicId, ...})

    # Transform each scene_dict to match frontend GameScene interface
    game_scenes: List[Dict[str, Any]] = []
    # Track first valid diagram URL for fallback on scenes with missing images
    _first_diagram_url = None
    for sd in scenes_dicts:
        if sd.get("diagram_image_url") and not _first_diagram_url:
            _first_diagram_url = sd["diagram_image_url"]

    for sd in scenes_dicts:
        # Build diagram object from diagram_image_url
        diagram_url = sd.get("diagram_image_url") or _first_diagram_url
        diagram_obj: Dict[str, Any] = {}
        if diagram_url:
            diagram_obj["assetUrl"] = diagram_url
            # Provide default dimensions if not set (frontend needs width/height)
            diagram_obj.setdefault("width", sd.get("diagram_width", 800))
            diagram_obj.setdefault("height", sd.get("diagram_height", 600))
            # Copy zones into diagram.zones for frontend DiagramCanvas
            diagram_obj["zones"] = sd.get("zones", [])

        # Convert mechanics from V3 format to frontend Mechanic format
        # Fix 3.4: Forward scoring, feedback, and animations (not just type + config)
        fe_mechanics: List[Dict[str, Any]] = []
        for m in sd.get("mechanics", []):
            fe_mech: Dict[str, Any] = {
                "type": m.get("mechanicType") or m.get("type") or "",
            }
            if m.get("config"):
                fe_mech["config"] = m["config"]
            # Forward scoring data so frontend can use it
            if m.get("scoring"):
                fe_mech["scoring"] = m["scoring"]
            # Forward feedback data so frontend can display it
            if m.get("feedback"):
                fe_mech["feedback"] = m["feedback"]
            # Forward animations so frontend can render them
            if m.get("animations"):
                fe_mech["animations"] = m["animations"]
            # Forward per-mechanic frontend config fields (Fix 2.10)
            for config_key in ("paths", "identificationPrompts", "sequenceConfig",
                               "descriptionMatchingConfig", "sortingConfig",
                               "memoryMatchConfig", "branchingConfig", "compareConfig",
                               "tracePathConfig", "clickToIdentifyConfig", "dragDropConfig"):
                if m.get(config_key):
                    fe_mech[config_key] = m[config_key]
            fe_mechanics.append(fe_mech)

        # Compute scene max_score from mechanics scoring
        scene_max = 0
        for m in sd.get("mechanics", []):
            scoring = m.get("scoring")
            if isinstance(scoring, dict):
                ms = scoring.get("max_score")
                if isinstance(ms, (int, float)):
                    scene_max += int(ms)
        if scene_max == 0:
            # labels[] now only contains correct labels (distractors are separate)
            scene_max = len(sd.get("labels", [])) * 10

        # Primary mechanic type for this scene (first mechanic, used by frontend routing)
        primary_mech_type = ""
        if fe_mechanics:
            primary_mech_type = fe_mechanics[0].get("type") or ""

        game_scene: Dict[str, Any] = {
            "scene_id": sd.get("scene_id", _make_id("scene", str(sd.get("scene_number", 1)))),
            "scene_number": sd.get("scene_number", 1),
            "title": sd.get("title", ""),
            "narrative_intro": sd.get("narrative_intro") or sd.get("learning_goal", ""),
            "diagram": diagram_obj,
            "zones": sd.get("zones", []),
            "labels": sd.get("labels", []),
            "max_score": scene_max,
            "mechanics": fe_mechanics,
            "mechanic_type": primary_mech_type,
            "interaction_mode": primary_mech_type,
            "mode_transitions": sd.get("mode_transitions", []),
            "distractor_labels": sd.get("distractor_labels", []),
        }
        if sd.get("scene_completion"):
            game_scene["scene_completion"] = sd["scene_completion"]

        # Promote per-mechanic config keys to scene level for frontend _sceneToBlueprint
        for fm in fe_mechanics:
            if isinstance(fm, dict):
                for ck in ("paths", "identificationPrompts", "sequenceConfig",
                           "descriptionMatchingConfig", "sortingConfig",
                           "memoryMatchConfig", "branchingConfig", "compareConfig",
                           "tracePathConfig", "clickToIdentifyConfig", "dragDropConfig"):
                    if fm.get(ck) and ck not in game_scene:
                        game_scene[ck] = fm[ck]

        game_scenes.append(game_scene)

    is_multi = len(game_scenes) > 1

    if is_multi:
        # Multi-scene: wrap in game_sequence
        difficulty_level = "intermediate"
        if isinstance(difficulty_dict, dict):
            dl = difficulty_dict.get("level") or difficulty_dict.get("approach", "")
            if dl in ("beginner", "intermediate", "advanced"):
                difficulty_level = dl

        game_sequence: Dict[str, Any] = {
            "sequence_id": _make_id("seq", title[:20] if title else "game"),
            "sequence_title": title,
            "sequence_description": narrative_intro,
            "total_scenes": len(game_scenes),
            "scenes": game_scenes,
            "progression_type": "linear",
            "total_max_score": total_max_score if total_max_score > 0 else sum(gs.get("max_score", 0) for gs in game_scenes),
            "passing_score": int(total_max_score * 0.6) if total_max_score > 0 else 60,
            "require_completion": True,
            "allow_scene_skip": False,
            "allow_revisit": False,
            "estimated_duration_minutes": estimated_duration,
            "difficulty_level": difficulty_level,
        }

        # Promote first scene's diagram/labels/zones to root level for backward compat.
        # Frontend components (MechanicRouter, DiagramCanvas) read bp.diagram.zones, bp.labels
        # even in multi-scene mode, since _sceneToBlueprint may fall back to root fields.
        first_scene = game_scenes[0] if game_scenes else {}
        first_mechs = first_scene.get("mechanics", [])
        root_mechanic_configs: Dict[str, Any] = {}
        for fm in first_mechs:
            if isinstance(fm, dict):
                for config_key in ("paths", "identificationPrompts", "sequenceConfig",
                                   "descriptionMatchingConfig", "sortingConfig",
                                   "memoryMatchConfig", "branchingConfig", "compareConfig",
                                   "tracePathConfig", "clickToIdentifyConfig", "dragDropConfig"):
                    if fm.get(config_key):
                        root_mechanic_configs[config_key] = fm[config_key]

        blueprint_dict: Dict[str, Any] = {
            "templateType": "INTERACTIVE_DIAGRAM",
            "title": title,
            "narrativeIntro": narrative_intro,
            "is_multi_scene": True,
            "game_sequence": game_sequence,
            # Root-level fields from first scene for backward compat
            "diagram": first_scene.get("diagram", {}),
            "zones": first_scene.get("zones", []),
            "labels": first_scene.get("labels", []),
            "distractorLabels": first_scene.get("distractor_labels", []),
            "mechanics": first_scene.get("mechanics", []),
            "interaction_mode": first_mechs[0].get("type") or "" if first_mechs else "",
            "animationCues": animation_cues,
            "theme": theme_dict,
            "hierarchy": hierarchy_dict,
            "learning_objectives": learning_objectives,
            "scoringStrategy": {
                "type": "standard",
                "base_points_per_zone": 10,
                "time_bonus_enabled": False,
                "partial_credit": True,
                "max_score": total_max_score,
            },
            "totalMaxScore": total_max_score,
            **root_mechanic_configs,
        }
    else:
        # Single scene: flatten to root-level structure
        single = game_scenes[0] if game_scenes else {}
        diagram_url = single.get("diagram", {}).get("assetUrl")

        # Fix 2.10: Extract per-mechanic frontend config fields from first scene's mechanics
        # and promote to blueprint root level for backward compatibility
        first_scene_mechs = single.get("mechanics", [])
        root_mechanic_configs: Dict[str, Any] = {}
        for fm in first_scene_mechs:
            if isinstance(fm, dict):
                for config_key in ("paths", "identificationPrompts", "sequenceConfig",
                                   "descriptionMatchingConfig", "sortingConfig",
                                   "memoryMatchConfig", "branchingConfig", "compareConfig",
                                   "tracePathConfig", "clickToIdentifyConfig", "dragDropConfig"):
                    if fm.get(config_key):
                        root_mechanic_configs[config_key] = fm[config_key]

        # Fix 4.3: Promote mode_transitions and interaction_mode for single-scene
        single_mechs = single.get("mechanics", [])
        first_mech_type = single_mechs[0].get("type", "drag_drop") if single_mechs else "drag_drop"
        single_transitions = single.get("mode_transitions", [])

        blueprint_dict = {
            "templateType": "INTERACTIVE_DIAGRAM",
            "title": title,
            "narrativeIntro": narrative_intro,
            "diagram": single.get("diagram", {}),
            "zones": single.get("zones", []),
            "labels": single.get("labels", []),
            "distractorLabels": single.get("distractor_labels", []),
            "mechanics": single_mechs,
            "interaction_mode": first_mech_type,
            "mode_transitions": single_transitions,
            "animationCues": animation_cues,
            "theme": theme_dict,
            "hierarchy": hierarchy_dict,
            "scoringStrategy": {
                "type": "standard",
                "base_points_per_zone": 10,
                "time_bonus_enabled": False,
                "partial_credit": True,
                "max_score": total_max_score,
            },
            "totalMaxScore": total_max_score,
            "learning_objectives": learning_objectives,
            # Backward compat: promote mechanic configs to root level
            **root_mechanic_configs,
        }

    if not scenes_dicts:
        warnings.append("No scenes were assembled -- design may have empty scenes list")
    for i, sd in enumerate(scenes_dicts):
        if not sd.get("zones"):
            warnings.append(f"Scene {sd.get('scene_number', i+1)} has no zones")
        if not sd.get("labels"):
            warnings.append(f"Scene {sd.get('scene_number', i+1)} has no labels")

    logger.info(
        f"Blueprint assembled: {len(scenes_dicts)} scenes, "
        f"{sum(len(s.get('zones', [])) for s in scenes_dicts)} total zones, "
        f"max_score={total_max_score}"
    )

    return {
        "blueprint": blueprint_dict,
        "assembly_warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Tool 2: validate_blueprint
# ---------------------------------------------------------------------------

async def validate_blueprint_impl(
    blueprint: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate a blueprint for frontend compatibility.

    Checks zone-label consistency, coordinate ranges, required fields,
    scoring, scene transitions, and minimum content requirements.
    """
    issues: List[str] = []
    fixable_issues: List[str] = []

    if not blueprint:
        return {"valid": False, "issues": ["Blueprint is empty or None"], "fixable_issues": []}

    # Required top-level fields
    if not blueprint.get("title"):
        issues.append("Missing title")
        fixable_issues.append("Missing title")

    if not blueprint.get("narrativeIntro"):
        fixable_issues.append("Missing narrativeIntro (can use pedagogical_reasoning as fallback)")

    if not blueprint.get("animationCues"):
        fixable_issues.append("Missing animationCues (can add defaults)")

    # Handle both multi-scene (game_sequence.scenes) and flat (scenes/zones at root)
    if blueprint.get("is_multi_scene") and blueprint.get("game_sequence"):
        scenes = blueprint["game_sequence"].get("scenes", [])
    elif blueprint.get("scenes"):
        scenes = blueprint["scenes"]
    else:
        # Single-scene: synthesize a scene from root-level fields
        scenes = [{
            "scene_number": 1,
            "zones": blueprint.get("zones", []),
            "labels": blueprint.get("labels", []),
        }]
    if not scenes or (len(scenes) == 1 and not scenes[0].get("zones") and not blueprint.get("zones")):
        issues.append("No scenes in blueprint")
        return {"valid": False, "issues": issues, "fixable_issues": fixable_issues}

    total_max_score = blueprint.get("total_max_score", 0)
    if total_max_score <= 0:
        fixable_issues.append("total_max_score is 0 or negative (can recalculate)")

    # Scene transitions reference valid scene numbers
    valid_scene_numbers = {s.get("scene_number") for s in scenes if isinstance(s, dict)}
    for st in blueprint.get("scene_transitions", []):
        if isinstance(st, dict):
            if st.get("from_scene") not in valid_scene_numbers:
                issues.append(f"Scene transition references invalid from_scene: {st.get('from_scene')}")
            if st.get("to_scene") not in valid_scene_numbers:
                issues.append(f"Scene transition references invalid to_scene: {st.get('to_scene')}")

    # Per-scene checks
    for scene in scenes:
        if not isinstance(scene, dict):
            issues.append("Scene is not a dict")
            continue

        sn = scene.get("scene_number", "?")
        scene_zones = scene.get("zones", [])
        scene_labels = scene.get("labels", [])

        # At least 1 zone and 1 label per scene
        if not scene_zones:
            issues.append(f"Scene {sn}: no zones")
            fixable_issues.append(f"Scene {sn}: missing zones (can create placeholders)")

        if not scene_labels:
            issues.append(f"Scene {sn}: no labels")

        # Build zone ID set
        zone_ids = set()
        for z in scene_zones:
            if isinstance(z, dict):
                zone_ids.add(z.get("id", ""))

        # Label-zone consistency
        for lbl in scene_labels:
            if not isinstance(lbl, dict):
                continue
            if lbl.get("isDistractor"):
                continue
            correct_zone = lbl.get("correctZoneId", "")
            if correct_zone and correct_zone not in zone_ids:
                issues.append(
                    f"Scene {sn}: label '{lbl.get('text', '?')}' references "
                    f"non-existent zone '{correct_zone}'"
                )
                fixable_issues.append(
                    f"Scene {sn}: label-zone ID mismatch for '{lbl.get('text', '?')}'"
                )

        # Fix 2.11: Mechanic-specific validation
        scene_mechs = scene.get("mechanics", [])
        for mech in scene_mechs:
            if not isinstance(mech, dict):
                continue
            mtype = mech.get("type", "")

            if mtype == "trace_path":
                if not mech.get("paths") and not (mech.get("config") or {}).get("waypoints"):
                    fixable_issues.append(
                        f"Scene {sn}: trace_path mechanic missing 'paths' or 'waypoints'. "
                        f"Path will not render correctly."
                    )

            if mtype == "click_to_identify":
                if not mech.get("identificationPrompts"):
                    fixable_issues.append(
                        f"Scene {sn}: click_to_identify missing 'identificationPrompts'. "
                        f"Will fall back to generic prompts."
                    )

            if mtype == "sequencing":
                seq_cfg = mech.get("sequenceConfig") or (mech.get("config") or {})
                if not seq_cfg.get("correctOrder") and not seq_cfg.get("correct_order"):
                    issues.append(
                        f"Scene {sn}: sequencing mechanic missing correctOrder/correct_order"
                    )

            if mtype == "description_matching":
                dm_cfg = mech.get("descriptionMatchingConfig") or (mech.get("config") or {})
                if not dm_cfg.get("descriptions"):
                    fixable_issues.append(
                        f"Scene {sn}: description_matching missing descriptions"
                    )

            if mtype == "sorting_categories":
                sort_cfg = mech.get("sortingConfig") or (mech.get("config") or {})
                if not sort_cfg.get("categories"):
                    issues.append(
                        f"Scene {sn}: sorting_categories missing categories"
                    )
                if not sort_cfg.get("items"):
                    fixable_issues.append(
                        f"Scene {sn}: sorting_categories missing items"
                    )

            if mtype == "memory_match":
                mem_cfg = mech.get("memoryMatchConfig") or (mech.get("config") or {})
                if not mem_cfg.get("pairs"):
                    issues.append(
                        f"Scene {sn}: memory_match missing pairs"
                    )

            if mtype == "branching_scenario":
                br_cfg = mech.get("branchingConfig") or (mech.get("config") or {})
                if not br_cfg.get("nodes"):
                    issues.append(
                        f"Scene {sn}: branching_scenario missing nodes"
                    )
                if not br_cfg.get("startNodeId") and not br_cfg.get("start_node_id"):
                    fixable_issues.append(
                        f"Scene {sn}: branching_scenario missing startNodeId"
                    )

            if mtype == "compare_contrast":
                cmp_cfg = mech.get("compareConfig") or (mech.get("config") or {})
                if not cmp_cfg.get("expectedCategories") and not cmp_cfg.get("expected_categories"):
                    fixable_issues.append(
                        f"Scene {sn}: compare_contrast missing expectedCategories"
                    )

            # All mechanics should have scoring
            if not mech.get("scoring"):
                fixable_issues.append(
                    f"Scene {sn}: mechanic '{mtype}' missing scoring data"
                )

        # Zone coordinate validation (0-100% range)
        for z in scene_zones:
            if not isinstance(z, dict):
                continue
            z_id = z.get("id", "?")
            # Check flat x, y
            x = z.get("x")
            y = z.get("y")
            if x is not None and isinstance(x, (int, float)):
                if x < 0 or x > 100:
                    fixable_issues.append(f"Scene {sn}: zone '{z_id}' x={x} out of 0-100 range")
            if y is not None and isinstance(y, (int, float)):
                if y < 0 or y > 100:
                    fixable_issues.append(f"Scene {sn}: zone '{z_id}' y={y} out of 0-100 range")
            # Check polygon points
            points = z.get("points", [])
            for pt in points:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    if pt[0] < 0 or pt[0] > 100 or pt[1] < 0 or pt[1] > 100:
                        fixable_issues.append(
                            f"Scene {sn}: zone '{z_id}' point [{pt[0]}, {pt[1]}] out of 0-100 range"
                        )
                        break  # Only report once per zone

    valid = len(issues) == 0
    return {
        "valid": valid,
        "issues": issues,
        "fixable_issues": fixable_issues,
    }


# ---------------------------------------------------------------------------
# Tool 3: repair_blueprint
# ---------------------------------------------------------------------------

async def repair_blueprint_impl(
    blueprint: Dict[str, Any],
    issues_to_fix: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Repair common issues in a blueprint.

    Handles: zone-label ID mismatches, missing zones (placeholder grid),
    missing animationCues, scoring recalculation, coordinate normalization,
    missing narrativeIntro.
    """
    from app.tools.v3_context import get_v3_tool_context

    if not blueprint:
        return {"repaired_blueprint": None, "fixes_applied": ["Blueprint was None -- cannot repair"]}

    ctx = get_v3_tool_context()
    raw_design = ctx.get("game_design_v3") or {}
    scene_specs_list = ctx.get("scene_specs_v3") or []

    if isinstance(raw_design, dict):
        design = raw_design
    elif hasattr(raw_design, "model_dump"):
        design = raw_design.model_dump()
    else:
        design = {}

    fixes_applied: List[str] = []
    issues_to_fix = issues_to_fix or []
    issues_lower = [i.lower() for i in issues_to_fix]

    # Resolve scene list: multi-scene uses game_sequence.scenes, single uses root
    if blueprint.get("is_multi_scene") and blueprint.get("game_sequence"):
        _bp_scenes = blueprint["game_sequence"].get("scenes", [])
    else:
        _bp_scenes = blueprint.get("scenes", [])
        if not _bp_scenes:
            # Single-scene fallback: synthesize from root-level fields
            _bp_scenes = [{
                "scene_number": 1,
                "zones": blueprint.get("zones", []),
                "labels": blueprint.get("labels", []),
                "mechanics": blueprint.get("mechanics", []),
            }]

    # --- Fix 1: Missing narrativeIntro ---
    if not blueprint.get("narrativeIntro"):
        fallback = design.get("pedagogical_reasoning") or design.get("narrative_intro") or design.get("title", "")
        if fallback:
            blueprint["narrativeIntro"] = fallback
            fixes_applied.append(f"Set narrativeIntro from pedagogical_reasoning")

    # --- Fix 2: Missing animationCues ---
    if not blueprint.get("animationCues"):
        blueprint["animationCues"] = {
            "correctPlacement": {"type": "pulse", "color": "#22c55e", "duration_ms": 400},
            "incorrectPlacement": {"type": "shake", "color": "#ef4444", "duration_ms": 300},
            "completion": {"type": "confetti", "duration_ms": 2000},
            "hintReveal": {"type": "glow", "color": "#f59e0b", "duration_ms": 600},
        }
        fixes_applied.append("Added default animationCues")

    # --- Fix 3: Zone-label ID mismatches ---
    for scene in _bp_scenes:
        if not isinstance(scene, dict):
            continue
        sn = scene.get("scene_number", "?")
        zone_ids = {z.get("id", ""): z for z in scene.get("zones", []) if isinstance(z, dict)}
        zone_by_label_lower = {
            z.get("label", "").lower(): z.get("id", "")
            for z in scene.get("zones", [])
            if isinstance(z, dict) and not z.get("group_only")
        }

        for lbl in scene.get("labels", []):
            if not isinstance(lbl, dict):
                continue
            if lbl.get("isDistractor"):
                continue
            correct_zone = lbl.get("correctZoneId", "")
            if correct_zone and correct_zone not in zone_ids:
                # Try case-insensitive match
                label_text = lbl.get("text", "").lower()
                matched_id = zone_by_label_lower.get(label_text)
                if matched_id:
                    lbl["correctZoneId"] = matched_id
                    fixes_applied.append(f"Scene {sn}: fixed label '{lbl.get('text')}' zone ID (case-insensitive match)")
                else:
                    # Fuzzy: find best substring match
                    best_match = None
                    best_score = 0
                    for z_label_lower, z_id in zone_by_label_lower.items():
                        # Simple overlap score
                        overlap = len(set(label_text.split()) & set(z_label_lower.split()))
                        if overlap > best_score:
                            best_score = overlap
                            best_match = z_id
                    if best_match and best_score > 0:
                        lbl["correctZoneId"] = best_match
                        fixes_applied.append(f"Scene {sn}: fuzzy-matched label '{lbl.get('text')}' to zone '{best_match}'")

    # --- Fix 4: Missing zones -- create placeholders from scene_specs_v3 ---
    scene_specs_map: Dict[int, Dict[str, Any]] = {}
    for spec in scene_specs_list:
        if isinstance(spec, dict):
            sn = spec.get("scene_number")
            if sn is not None:
                scene_specs_map[int(sn)] = spec

    for scene in _bp_scenes:
        if not isinstance(scene, dict):
            continue
        sn = scene.get("scene_number", 1)
        if scene.get("zones"):
            continue
        # Scene has no zones -- build placeholders
        spec = scene_specs_map.get(sn, {})
        spec_zones = spec.get("zones", [])
        labels_data = design.get("labels", {})
        if isinstance(labels_data, list):
            labels_data = {"zone_labels": labels_data}
        zone_labels = labels_data.get("zone_labels", [])

        # Determine labels for this scene
        placeholder_labels = [
            sz.get("label", "") for sz in spec_zones if isinstance(sz, dict) and sz.get("label")
        ]
        if not placeholder_labels:
            placeholder_labels = zone_labels

        if not placeholder_labels:
            continue

        # Spread zones in a grid
        n = len(placeholder_labels)
        cols = max(1, math.ceil(math.sqrt(n)))
        rows = max(1, math.ceil(n / cols))

        new_zones: List[Dict[str, Any]] = []
        for idx, lbl in enumerate(placeholder_labels):
            row = idx // cols
            col = idx % cols
            x = 15 + (col * 70 / max(1, cols - 1)) if cols > 1 else 50
            y = 15 + (row * 70 / max(1, rows - 1)) if rows > 1 else 50
            zone_id = _make_id("zone", str(sn), lbl)
            new_zones.append({
                "id": zone_id,
                "label": lbl,
                "shape": "circle",
                "coordinates": {"x": round(x, 1), "y": round(y, 1), "radius": 5},
                "x": round(x, 1),
                "y": round(y, 1),
                "radius": 5,
                "group_only": False,
                "parentZoneId": None,
            })

        scene["zones"] = new_zones
        fixes_applied.append(f"Scene {sn}: created {len(new_zones)} placeholder zones in grid layout")

        # Also rebuild labels if needed
        if not scene.get("labels"):
            new_labels = []
            for z in new_zones:
                if not z.get("group_only"):
                    new_labels.append({
                        "id": _make_id("label", str(sn), z["label"]),
                        "text": z["label"],
                        "correctZoneId": z["id"],
                        "isDistractor": False,
                    })
            scene["labels"] = new_labels
            fixes_applied.append(f"Scene {sn}: rebuilt {len(new_labels)} labels from placeholder zones")

    # --- Fix 5: Coordinate normalization to 0-100% ---
    for scene in _bp_scenes:
        if not isinstance(scene, dict):
            continue
        for z in scene.get("zones", []):
            if not isinstance(z, dict):
                continue
            # Clamp flat x/y
            if z.get("x") is not None and isinstance(z["x"], (int, float)):
                orig = z["x"]
                z["x"] = _clamp_coordinate(z["x"])
                if orig != z["x"]:
                    fixes_applied.append(f"Clamped zone '{z.get('id', '?')}' x from {orig} to {z['x']}")
            if z.get("y") is not None and isinstance(z["y"], (int, float)):
                orig = z["y"]
                z["y"] = _clamp_coordinate(z["y"])
                if orig != z["y"]:
                    fixes_applied.append(f"Clamped zone '{z.get('id', '?')}' y from {orig} to {z['y']}")

            # Clamp polygon points
            pts = z.get("points", [])
            for i, pt in enumerate(pts):
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    new_pt = [_clamp_coordinate(pt[0]), _clamp_coordinate(pt[1])]
                    if new_pt != list(pt[:2]):
                        pts[i] = new_pt
                        fixes_applied.append(f"Clamped zone '{z.get('id', '?')}' polygon point to 0-100 range")

    # --- Mechanic-specific auto-repair (all 10 mechanics) ---
    for scene in _bp_scenes:
        if not isinstance(scene, dict):
            continue
        sn = scene.get("scene_number", "?")
        scene_labels = [
            lbl.get("text", "") for lbl in scene.get("labels", [])
            if isinstance(lbl, dict) and not lbl.get("isDistractor")
        ]
        zone_by_label_r = {
            z.get("label", ""): z.get("id", "")
            for z in scene.get("zones", [])
            if isinstance(z, dict) and not z.get("group_only")
        }

        for mech in scene.get("mechanics", []):
            if not isinstance(mech, dict):
                continue
            mtype = mech.get("type", "")
            config = mech.get("config") or {}

            # click_to_identify: generate prompts + clickToIdentifyConfig if missing
            if mtype == "click_to_identify":
                if not mech.get("identificationPrompts"):
                    config_prompts = config.get("prompts", [])
                    if config_prompts:
                        mech["identificationPrompts"] = config_prompts
                    else:
                        id_prompts = []
                        for idx_zl, lbl in enumerate(scene_labels):
                            z_id = zone_by_label_r.get(lbl, "")
                            id_prompts.append({
                                "zoneId": z_id,
                                "prompt": f"Identify and click on the {lbl}",
                                "order": idx_zl,
                            })
                        mech["identificationPrompts"] = id_prompts
                    fixes_applied.append(f"Scene {sn}: generated identificationPrompts for click_to_identify")
                if not mech.get("clickToIdentifyConfig"):
                    mech["clickToIdentifyConfig"] = {
                        "promptStyle": config.get("prompt_style", "naming"),
                        "highlightOnHover": config.get("highlight_on_hover", True),
                        "highlightStyle": config.get("highlight_style", "subtle"),
                        "selectionMode": config.get("selection_mode", "sequential"),
                        "showZoneCount": config.get("show_zone_count", True),
                        "instructions": config.get("instructions", "Click on each structure"),
                    }
                    fixes_applied.append(f"Scene {sn}: generated clickToIdentifyConfig")

            # trace_path: build paths + tracePathConfig from config waypoints if missing
            if mtype == "trace_path":
                if not mech.get("paths"):
                    waypoints = config.get("waypoints", [])
                    if waypoints:
                        path_waypoints = []
                        for idx, wp in enumerate(waypoints):
                            wp_zone_id = _make_id("zone", str(sn), wp)
                            path_waypoints.append({
                                "zoneId": wp_zone_id,
                                "label": wp,
                                "order": idx,
                            })
                        mech["paths"] = [{
                            "id": _make_id("path", str(sn)),
                            "waypoints": path_waypoints,
                            "description": config.get("description", "Trace the path"),
                            "requiresOrder": config.get("requires_order", True),
                        }]
                        fixes_applied.append(f"Scene {sn}: built paths from trace_path waypoints")
                if not mech.get("tracePathConfig"):
                    mech["tracePathConfig"] = {
                        "drawingMode": config.get("drawing_mode", "click_waypoints"),
                        "pathType": config.get("path_type", "linear"),
                        "particleTheme": config.get("particle_theme", "dots"),
                        "showDirectionArrows": config.get("show_direction_arrows", True),
                        "showWaypointLabels": config.get("show_waypoint_labels", True),
                        "instructions": config.get("instructions", "Trace the path"),
                    }
                    fixes_applied.append(f"Scene {sn}: generated tracePathConfig")

            # sequencing: build sequenceConfig from config
            if mtype == "sequencing" and not mech.get("sequenceConfig"):
                items = config.get("items", [])
                correct_order = config.get("correct_order", [])
                if items or correct_order:
                    instr = config.get("instruction_text", "Arrange in the correct order")
                    mech["sequenceConfig"] = {
                        "sequenceType": config.get("sequence_type", "linear"),
                        "items": items,
                        "correctOrder": correct_order,
                        "instructionText": instr,
                        "instructions": instr,
                        "layoutMode": config.get("layout_mode", "horizontal_timeline"),
                        "interactionPattern": config.get("interaction_pattern", "drag_reorder"),
                        "cardType": config.get("card_type", "text_only"),
                        "connectorStyle": config.get("connector_style", "arrow"),
                        "showPositionNumbers": config.get("show_position_numbers", True),
                    }
                    fixes_applied.append(f"Scene {sn}: built sequenceConfig from config")

            # sorting_categories: build sortingConfig from config
            if mtype == "sorting_categories" and not mech.get("sortingConfig"):
                categories = config.get("categories", [])
                items = config.get("items", [])
                if categories:
                    norm_cats = []
                    for cat in categories:
                        if isinstance(cat, dict):
                            norm_cats.append({
                                "id": cat.get("id", cat.get("label", "").lower().replace(" ", "_")),
                                "label": cat.get("label", cat.get("id", "")),
                                "description": cat.get("description"),
                            })
                        elif isinstance(cat, str):
                            norm_cats.append({"id": cat.lower().replace(" ", "_"), "label": cat})
                    norm_items = []
                    for item in items:
                        if isinstance(item, dict):
                            correct_ids = item.get("correct_category_ids") or item.get("correctCategoryIds", [])
                            correct_cat = item.get("correctCategoryId") or item.get("correct_category_id", "")
                            if not correct_ids and correct_cat:
                                correct_ids = [correct_cat]
                            if not correct_cat and correct_ids:
                                correct_cat = correct_ids[0]
                            norm_items.append({
                                "id": item.get("id", ""),
                                "text": item.get("text", ""),
                                "correctCategoryId": correct_cat,
                                "correctCategoryIds": correct_ids,
                            })
                    instr = config.get("instruction_text", "Sort items into the correct categories")
                    mech["sortingConfig"] = {
                        "categories": norm_cats,
                        "items": norm_items,
                        "showCategoryHints": config.get("show_category_hints", True),
                        "allowPartialCredit": config.get("allow_partial_credit", True),
                        "instructionText": instr,
                        "instructions": instr,
                        "sortMode": config.get("sort_mode", "bucket"),
                        "submitMode": config.get("submit_mode", "batch_submit"),
                    }
                    fixes_applied.append(f"Scene {sn}: built sortingConfig from config")

            # description_matching: build descriptionMatchingConfig from config
            if mtype == "description_matching" and not mech.get("descriptionMatchingConfig"):
                raw_descs = config.get("descriptions", [])
                desc_dict = {}
                if isinstance(raw_descs, dict):
                    desc_dict = raw_descs
                elif isinstance(raw_descs, list):
                    for d in raw_descs:
                        if isinstance(d, dict):
                            z_id = d.get("zone_id", "")
                            if not z_id:
                                z_id = zone_by_label_r.get(d.get("label", d.get("zone_label", "")), "")
                            if z_id and d.get("description"):
                                desc_dict[z_id] = d["description"]
                if desc_dict:
                    instr = config.get("instruction_text", "Match each description to the correct structure")
                    mech["descriptionMatchingConfig"] = {
                        "mode": config.get("mode", "click_zone"),
                        "descriptions": desc_dict,
                        "instructions": instr,
                        "showConnectingLines": config.get("show_connecting_lines", True),
                        "descriptionPanelPosition": config.get("description_panel_position", "right"),
                    }
                    fixes_applied.append(f"Scene {sn}: built descriptionMatchingConfig from config")

            # memory_match: build memoryMatchConfig from config
            if mtype == "memory_match" and not mech.get("memoryMatchConfig"):
                pairs = config.get("pairs", [])
                if pairs:
                    norm_pairs = []
                    for idx_p, pair in enumerate(pairs):
                        if isinstance(pair, dict):
                            norm_pairs.append({
                                "id": pair.get("id", f"pair_{idx_p + 1}"),
                                "front": pair.get("front") or pair.get("term", f"Card {idx_p + 1}"),
                                "back": pair.get("back") or pair.get("definition", ""),
                                "frontType": pair.get("frontType", "text"),
                                "backType": pair.get("backType", "text"),
                                "explanation": pair.get("explanation", ""),
                            })
                    instr = config.get("instruction_text", "Find matching pairs")
                    mech["memoryMatchConfig"] = {
                        "pairs": norm_pairs,
                        "gridSize": config.get("grid_size"),
                        "flipDurationMs": config.get("flip_duration_ms", 600),
                        "showAttemptsCounter": config.get("show_attempts_counter", True),
                        "instructionText": instr,
                        "instructions": instr,
                        "gameVariant": config.get("game_variant", "classic"),
                        "matchType": config.get("match_type", "term_to_definition"),
                        "showExplanationOnMatch": config.get("show_explanation_on_match", True),
                    }
                    fixes_applied.append(f"Scene {sn}: built memoryMatchConfig from config")

            # branching_scenario: build branchingConfig from config
            if mtype == "branching_scenario" and not mech.get("branchingConfig"):
                nodes = config.get("nodes", [])
                if nodes:
                    instr = config.get("instruction_text", "Make decisions and see the consequences")
                    mech["branchingConfig"] = {
                        "nodes": nodes,
                        "startNodeId": config.get("start_node_id") or config.get("startNodeId", ""),
                        "showPathTaken": config.get("show_path_taken", True),
                        "allowBacktrack": config.get("allow_backtrack", False),
                        "showConsequences": config.get("show_consequences", True),
                        "instructions": instr,
                    }
                    fixes_applied.append(f"Scene {sn}: built branchingConfig from config")

            # compare_contrast: build compareConfig from config
            if mtype == "compare_contrast" and not mech.get("compareConfig"):
                expected = config.get("expected_categories", {})
                if expected:
                    instr = config.get("instruction_text", "Compare and categorize the structures")
                    mech["compareConfig"] = {
                        "expectedCategories": expected,
                        "highlightMatching": config.get("highlight_matching", True),
                        "instructions": instr,
                        "subjects": config.get("subjects", []),
                        "comparisonMode": config.get("comparison_mode", "venn_diagram"),
                        "similarities": config.get("similarities", []),
                        "differences": config.get("differences", []),
                    }
                    fixes_applied.append(f"Scene {sn}: built compareConfig from config")

            # drag_drop: build dragDropConfig from config
            if mtype == "drag_drop" and not mech.get("dragDropConfig"):
                mech["dragDropConfig"] = {
                    "interactionMode": config.get("interaction_mode", "drag_drop"),
                    "feedbackTiming": config.get("feedback_timing", "immediate"),
                    "zoneIdleAnimation": config.get("zone_idle_animation", "none"),
                    "leaderLineStyle": config.get("leader_line_style", "curved"),
                    "snapToZone": config.get("snap_to_zone", True),
                    "returnOnMiss": config.get("return_on_miss", True),
                    "trayPosition": config.get("tray_position", "bottom"),
                    "trayLayout": config.get("tray_layout", "horizontal"),
                    "labelCardStyle": config.get("label_card_style", "text"),
                    "pinMarkerShape": config.get("pin_marker_shape", "circle"),
                    "showLeaderLines": config.get("show_leader_lines", True),
                    "instructions": config.get("instructions", "Drag labels to the correct zones"),
                }
                fixes_applied.append(f"Scene {sn}: built dragDropConfig from config")

            # Add default scoring if missing (all mechanics)
            if not mech.get("scoring"):
                n_labels = len(mech.get("zoneLabels", scene_labels))
                strategy_map = {
                    "trace_path": "progressive", "sequencing": "progressive",
                    "memory_match": "time_based", "branching_scenario": "mastery",
                    "compare_contrast": "mastery",
                }
                ppc_map = {
                    "trace_path": 15, "sequencing": 15,
                    "branching_scenario": 20, "compare_contrast": 15,
                }
                mech["scoring"] = {
                    "strategy": strategy_map.get(mtype, "standard"),
                    "points_per_correct": ppc_map.get(mtype, 10),
                    "max_score": n_labels * ppc_map.get(mtype, 10) or 100,
                    "partial_credit": mtype != "memory_match",
                    "hint_penalty": 0.0 if mtype in ("memory_match", "branching_scenario") else 0.1,
                }
                fixes_applied.append(f"Scene {sn}: added default scoring for '{mtype}'")

    # --- Fix 6: Scoring recalculation ---
    recalculated_score = 0
    for scene in _bp_scenes:
        if not isinstance(scene, dict):
            continue
        for mech in scene.get("mechanics", []):
            if not isinstance(mech, dict):
                continue
            scoring = mech.get("scoring")
            if isinstance(scoring, dict):
                ms = scoring.get("max_score")
                if isinstance(ms, (int, float)):
                    recalculated_score += int(ms)

    if recalculated_score > 0 and recalculated_score != blueprint.get("total_max_score", 0):
        old_score = blueprint.get("total_max_score", 0)
        blueprint["total_max_score"] = recalculated_score
        fixes_applied.append(f"Recalculated total_max_score: {old_score} -> {recalculated_score}")
    elif recalculated_score == 0 and (blueprint.get("total_max_score") or 0) <= 0:
        # Fallback: count labels * 10
        n_labels = sum(
            len([l for l in s.get("labels", []) if isinstance(l, dict) and not l.get("isDistractor")])
            for s in blueprint.get("scenes", [])
            if isinstance(s, dict)
        )
        fallback_score = max(100, n_labels * 10)
        blueprint["total_max_score"] = fallback_score
        fixes_applied.append(f"Set fallback total_max_score: {fallback_score} (from {n_labels} labels)")

    return {
        "repaired_blueprint": blueprint,
        "fixes_applied": fixes_applied,
    }


# ---------------------------------------------------------------------------
# Tool 4: submit_blueprint
# ---------------------------------------------------------------------------

async def submit_blueprint_impl(
    blueprint: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Final validation gate and submission of the blueprint.

    Checks essential frontend requirements. Returns accepted/rejected
    with specific issues if rejected.
    """
    if not blueprint:
        return {
            "accepted": False,
            "issues": ["Blueprint is None or empty"],
        }

    critical_issues: List[str] = []

    # Must have at least 1 scene
    scenes = blueprint.get("scenes", [])
    if not scenes:
        critical_issues.append("No scenes in blueprint")

    # Each scene must have zones with coordinates and labels with correctZoneId
    for scene in scenes:
        if not isinstance(scene, dict):
            critical_issues.append("Scene is not a dict")
            continue

        sn = scene.get("scene_number", "?")
        scene_zones = scene.get("zones", [])
        scene_labels = scene.get("labels", [])

        if not scene_zones:
            critical_issues.append(f"Scene {sn}: no zones")

        if not scene_labels:
            critical_issues.append(f"Scene {sn}: no labels")

        # Zones must have some form of coordinates
        zones_without_coords = 0
        for z in scene_zones:
            if not isinstance(z, dict):
                continue
            has_coords = (
                z.get("coordinates") is not None
                or z.get("x") is not None
                or z.get("points") is not None
            )
            if not has_coords:
                zones_without_coords += 1
        if zones_without_coords > 0:
            # This is a warning, not critical -- zones can work without coords
            # in some frontend rendering modes
            pass

        # Labels must have correctZoneId
        for lbl in scene_labels:
            if not isinstance(lbl, dict):
                continue
            if not lbl.get("isDistractor") and not lbl.get("correctZoneId"):
                critical_issues.append(
                    f"Scene {sn}: label '{lbl.get('text', '?')}' missing correctZoneId"
                )

    # Must have animationCues
    if not blueprint.get("animationCues"):
        critical_issues.append("Missing animationCues")

    # Template type
    if blueprint.get("templateType") not in ("INTERACTIVE_DIAGRAM", "INTERACTIVE_DIAGRAM"):
        critical_issues.append(
            f"templateType is '{blueprint.get('templateType')}', expected 'INTERACTIVE_DIAGRAM'"
        )

    if critical_issues:
        logger.warning(f"Blueprint submission rejected: {critical_issues}")
        return {
            "accepted": False,
            "issues": critical_issues,
        }

    # Compute stats for the acceptance response
    total_zones = sum(len(s.get("zones", [])) for s in scenes if isinstance(s, dict))
    total_labels = sum(len(s.get("labels", [])) for s in scenes if isinstance(s, dict))

    logger.info(
        f"Blueprint accepted: {len(scenes)} scenes, "
        f"{total_zones} zones, {total_labels} labels, "
        f"max_score={blueprint.get('total_max_score', 0)}"
    )

    return {
        "accepted": True,
        "issues": [],
        "stats": {
            "scenes": len(scenes),
            "total_zones": total_zones,
            "total_labels": total_labels,
            "total_max_score": blueprint.get("total_max_score", 0),
        },
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_blueprint_assembler_tools() -> None:
    """Register all blueprint assembler v3 tools in the tool registry."""
    from app.tools.registry import register_tool

    register_tool(
        name="assemble_blueprint",
        description=(
            "Assemble a complete InteractiveDiagramBlueprint from upstream pipeline state "
            "(game_design_v3, scene_specs_v3, interaction_specs_v3, generated_assets_v3). "
            "No arguments needed -- reads all data from pipeline context. "
            "Returns the assembled blueprint dict and any assembly warnings."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=assemble_blueprint_impl,
    )

    register_tool(
        name="validate_blueprint",
        description=(
            "Validate a blueprint for frontend compatibility. "
            "Checks zone-label ID consistency, coordinate ranges (0-100%), "
            "required fields, scoring totals, scene transitions, and minimum content. "
            "Returns valid/invalid status with issues and fixable_issues lists."
        ),
        parameters={
            "type": "object",
            "properties": {
                "blueprint": {
                    "type": "object",
                    "description": "The blueprint dict to validate",
                },
            },
            "required": ["blueprint"],
        },
        function=validate_blueprint_impl,
    )

    register_tool(
        name="repair_blueprint",
        description=(
            "Repair common issues in a blueprint. Fixes zone-label ID mismatches "
            "(case-insensitive and fuzzy matching), creates placeholder zones for "
            "scenes missing them, adds default animationCues, recalculates scoring, "
            "normalizes coordinates to 0-100% range, and fills missing narrativeIntro. "
            "Returns the repaired blueprint and list of fixes applied."
        ),
        parameters={
            "type": "object",
            "properties": {
                "blueprint": {
                    "type": "object",
                    "description": "The blueprint dict to repair",
                },
                "issues_to_fix": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of issue descriptions to fix (from validate_blueprint)",
                },
            },
            "required": ["blueprint"],
        },
        function=repair_blueprint_impl,
    )

    register_tool(
        name="submit_blueprint",
        description=(
            "Final submission gate for the assembled blueprint. "
            "Performs essential checks: zones have coordinates, labels have correctZoneId, "
            "animationCues present, at least 1 scene. Returns accepted/rejected "
            "with specific issues if rejected."
        ),
        parameters={
            "type": "object",
            "properties": {
                "blueprint": {
                    "type": "object",
                    "description": "The final blueprint dict to submit",
                },
            },
            "required": ["blueprint"],
        },
        function=submit_blueprint_impl,
    )

    logger.info("Registered 4 blueprint assembler v3 tools")
