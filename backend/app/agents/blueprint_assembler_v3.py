"""
Blueprint Assembler v3 -- Deterministic + ReAct (legacy) Blueprint Assembly.

Provides two assembly paths:
1. `deterministic_blueprint_assembler_agent()` — Direct function calls, no LLM overhead.
   Calls assemble → validate → repair loop deterministically.
2. `blueprint_assembler_v3_agent()` — Legacy ReAct agent wrapper (kept for backward compat).

Reads: game_design_v3, scene_specs_v3, interaction_specs_v3, generated_assets_v3
Writes: blueprint (InteractiveDiagramBlueprint dict), generation_complete
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response
from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.game_design_v3 import GameDesignV3, SceneDesign, MechanicDesign
from app.agents.schemas.blueprint_schemas import (
    InteractiveDiagramBlueprint,
    IDScene,
    IDZone,
    IDLabel,
    IDMechanic,
    IDMechanicTransition,
    IDSceneTransition,
    IDSceneAsset,
    validate_blueprint,
)
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.blueprint_assembler_v3")


# ---------------------------------------------------------------------------
# Legacy assembly helpers (kept for backward compatibility with any imports)
# ---------------------------------------------------------------------------

def _make_id(prefix: str, *parts: str) -> str:
    """Generate a deterministic ID from parts."""
    slug = "_".join(p.lower().replace(" ", "_") for p in parts if p)
    return f"{prefix}_{slug}" if slug else f"{prefix}_{uuid.uuid4().hex[:6]}"


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


def _assemble_zones(
    scene: SceneDesign,
    design: GameDesignV3,
    zone_data: List[Dict[str, Any]],
) -> List[IDZone]:
    """Assemble zones for a scene from design + detected zone data."""
    zones: List[IDZone] = []

    detected_map: Dict[str, Dict[str, Any]] = {}
    for z in zone_data:
        label = z.get("label", "")
        detected_map[label] = z

    scene_labels = scene.zone_labels or []
    if not scene_labels and design.labels:
        scene_labels = design.labels.zone_labels or []

    group_only_labels = set()
    if design.labels and design.labels.group_only_labels:
        group_only_labels = set(design.labels.group_only_labels)

    parent_map: Dict[str, str] = {}
    if design.labels and design.labels.hierarchy and design.labels.hierarchy.enabled:
        for group in design.labels.hierarchy.groups or []:
            for child in group.children:
                parent_map[child] = group.parent

    for g_label in group_only_labels:
        detected = detected_map.get(g_label, {})
        raw_coords = detected.get("coordinates") or detected.get("polygon")
        shape = detected.get("shape", "circle")
        coords = _normalize_coordinates(raw_coords, shape)

        zones.append(IDZone(
            id=_make_id("zone", str(scene.scene_number), g_label),
            label=g_label,
            shape=shape,
            coordinates=coords,
            group_only=True,
            parent_zone_id=None,
        ))

    for label in scene_labels:
        detected = detected_map.get(label, {})
        parent_label = parent_map.get(label)
        parent_id = _make_id("zone", str(scene.scene_number), parent_label) if parent_label else None

        raw_coords = detected.get("coordinates") or detected.get("polygon")
        shape = detected.get("shape", "circle")
        coords = _normalize_coordinates(raw_coords, shape)

        zones.append(IDZone(
            id=_make_id("zone", str(scene.scene_number), label),
            label=label,
            shape=shape,
            coordinates=coords,
            parent_zone_id=parent_id,
            group_only=False,
        ))

    return zones


def _assemble_labels(
    scene: SceneDesign,
    design: GameDesignV3,
    zones: List[IDZone],
) -> List[IDLabel]:
    """Assemble labels for a scene. Maps labels to zone IDs."""
    labels: List[IDLabel] = []
    zone_by_label = {z.label: z.id for z in zones if not z.group_only}

    for label_text in zone_by_label:
        labels.append(IDLabel(
            id=_make_id("label", str(scene.scene_number), label_text),
            text=label_text,
            correct_zone_id=zone_by_label[label_text],
            is_distractor=False,
        ))

    if design.labels and design.labels.distractor_labels:
        for dl in design.labels.distractor_labels:
            labels.append(IDLabel(
                id=_make_id("label", str(scene.scene_number), "dist", dl.text),
                text=dl.text,
                correct_zone_id="__distractor__",
                is_distractor=True,
                explanation=dl.explanation,
            ))

    return labels


def _assemble_mechanics(
    scene: SceneDesign,
    zones: List[IDZone],
) -> List[IDMechanic]:
    """Assemble mechanics for a scene from design."""
    mechanics: List[IDMechanic] = []

    for mech in scene.mechanics:
        config: Dict[str, Any] = {}

        if mech.type == "trace_path" and mech.path_config:
            config = mech.path_config.model_dump() if hasattr(mech.path_config, "model_dump") else dict(mech.path_config)
        elif mech.type == "click_to_identify" and mech.click_config:
            config = mech.click_config.model_dump() if hasattr(mech.click_config, "model_dump") else dict(mech.click_config)
        elif mech.type == "sequencing" and mech.sequence_config:
            config = mech.sequence_config.model_dump() if hasattr(mech.sequence_config, "model_dump") else dict(mech.sequence_config)

        scoring_dict = None
        if mech.scoring:
            scoring_dict = mech.scoring.model_dump() if hasattr(mech.scoring, "model_dump") else dict(mech.scoring)

        feedback_dict = None
        if mech.feedback:
            feedback_dict = mech.feedback.model_dump() if hasattr(mech.feedback, "model_dump") else dict(mech.feedback)

        mech_zone_labels = mech.zone_labels_used or []

        mechanics.append(IDMechanic(
            mechanic_id=_make_id("mech", str(scene.scene_number), mech.type),
            mechanic_type=mech.type,
            interaction_mode=mech.type,
            config=config if config else None,
            zone_labels=mech_zone_labels,
            scoring=scoring_dict,
            feedback=feedback_dict,
        ))

    return mechanics


def _assemble_scene_assets(
    scene: SceneDesign,
    generated_assets: Dict[str, Any],
) -> List[IDSceneAsset]:
    """Collect generated assets for this scene."""
    assets: List[IDSceneAsset] = []

    for asset_id, asset_data in generated_assets.items():
        if not isinstance(asset_data, dict):
            continue
        asset_scene = asset_data.get("scene_number")
        if asset_scene is not None and asset_scene != scene.scene_number:
            continue

        if not asset_data.get("success", False):
            continue

        assets.append(IDSceneAsset(
            asset_id=asset_id,
            asset_type=asset_data.get("asset_type", "unknown"),
            url=asset_data.get("url"),
            path=asset_data.get("path"),
        ))

    return assets


def assemble_blueprint(
    design: GameDesignV3,
    generated_assets: Dict[str, Any],
    diagram_image: Optional[str] = None,
    diagram_zones: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Legacy assembler: Assemble an InteractiveDiagramBlueprint from
    GameDesignV3 + generated assets.

    Returns the blueprint as a dict (not Pydantic model) for state storage.
    Kept for backward compatibility with non-ReAct callers.
    """
    zones_data = diagram_zones or []

    scenes: List[IDScene] = []
    total_max_score = 0

    for scene_design in design.scenes:
        zones = _assemble_zones(scene_design, design, zones_data)
        labels = _assemble_labels(scene_design, design, zones)
        mechanics = _assemble_mechanics(scene_design, zones)
        assets = _assemble_scene_assets(scene_design, generated_assets)

        for mech in mechanics:
            if mech.scoring and isinstance(mech.scoring, dict):
                total_max_score += mech.scoring.get("max_score") or 0

        scene_diagram_url = None
        if diagram_image:
            scene_diagram_url = diagram_image if diagram_image.startswith("/") else f"/api/assets/{diagram_image}"

        for asset in assets:
            if asset.asset_type == "diagram" and asset.url:
                scene_diagram_url = asset.url

        scenes.append(IDScene(
            scene_id=_make_id("scene", str(scene_design.scene_number)),
            scene_number=scene_design.scene_number,
            title=scene_design.title or f"Scene {scene_design.scene_number}",
            diagram_image_url=scene_diagram_url,
            zones=zones,
            labels=labels,
            mechanics=mechanics,
            assets=assets,
        ))

    scene_transitions: List[IDSceneTransition] = []
    if design.scene_transitions:
        for st in design.scene_transitions:
            scene_transitions.append(IDSceneTransition(
                from_scene=st.from_scene,
                to_scene=st.to_scene,
                trigger=st.trigger or "score_threshold",
                trigger_value=st.threshold,
                animation=st.animation or "slide_left",
            ))

    hierarchy_dict = None
    if design.labels and design.labels.hierarchy and design.labels.hierarchy.enabled:
        h = design.labels.hierarchy
        hierarchy_dict = {
            "enabled": True,
            "strategy": h.strategy,
            "groups": [g.model_dump() for g in (h.groups or [])],
        }

    theme_dict = None
    if design.theme:
        theme_dict = {
            "visual_tone": design.theme.visual_tone,
            "color_palette": design.theme.color_palette,
            "background_description": design.theme.background_description,
            "narrative_frame": design.theme.narrative_frame,
        }

    distractor_list = []
    if design.labels and design.labels.distractor_labels:
        for dl in design.labels.distractor_labels:
            distractor_list.append({
                "text": dl.text,
                "explanation": dl.explanation or "",
            })

    global_labels = design.labels.zone_labels if design.labels else []

    if total_max_score == 0:
        total_max_score = len(global_labels) * 10

    scenes_dicts = [s.model_dump() for s in scenes]

    for scene_dict in scenes_dicts:
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
                points = coords.get("points", [])
                if points and not zone.get("center"):
                    xs = [p[0] for p in points if isinstance(p, (list, tuple)) and len(p) >= 2]
                    ys = [p[1] for p in points if isinstance(p, (list, tuple)) and len(p) >= 2]
                    if xs and ys:
                        zone["center"] = {"x": sum(xs) / len(xs), "y": sum(ys) / len(ys)}

    blueprint_dict = {
        "templateType": "INTERACTIVE_DIAGRAM",
        "title": design.title,
        "narrativeIntro": design.pedagogical_reasoning or "",
        "theme": theme_dict,
        "global_labels": global_labels,
        "distractor_labels": distractor_list,
        "hierarchy": hierarchy_dict,
        "scenes": scenes_dicts,
        "scene_transitions": [st.model_dump() for st in scene_transitions],
        "total_max_score": total_max_score,
        "pass_threshold": 0.6,
        "difficulty": design.difficulty.model_dump() if design.difficulty else None,
        "learning_objectives": design.learning_objectives or [],
        "estimated_duration_minutes": design.estimated_duration_minutes,
    }

    return blueprint_dict


# ---------------------------------------------------------------------------
# ReAct Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Blueprint Assembler for GamED.AI. Your job: combine game design, \
scene specs, interaction specs, and generated assets into a frontend-ready \
InteractiveDiagramBlueprint.

## Process

Follow these steps exactly:
1. Call `assemble_blueprint` to create the initial blueprint from pipeline state.
2. Call `validate_blueprint` with the assembled blueprint to check for issues.
3. If validation found issues, call `repair_blueprint` to fix them.
4. If repairs were made, call `validate_blueprint` again to confirm repairs worked.
5. Call `submit_blueprint` with the final blueprint.

## Important Notes

- The `assemble_blueprint` tool reads all upstream data automatically (no arguments needed).
- The blueprint must be a complete InteractiveDiagramBlueprint with:
  - templateType: "INTERACTIVE_DIAGRAM"
  - title, narrativeIntro, theme, global_labels, distractor_labels
  - scenes with zones, labels, mechanics, animationCues
  - scene_transitions, total_max_score, pass_threshold
- Every non-distractor label must have a correctZoneId matching an actual zone.id
- Zone coordinates should be in 0-100% range
- animationCues must be present (defaults will be added if missing)
- Do NOT output the blueprint as your final answer -- use submit_blueprint instead.

## Error Handling

- If assemble_blueprint returns warnings, note them but continue to validation.
- If validate_blueprint finds issues, always try repair_blueprint before giving up.
- If submit_blueprint rejects the blueprint, review the issues and try to fix them.
"""


class BlueprintAssemblerV3(ReActAgent):
    """ReAct agent that assembles, validates, repairs, and submits blueprints."""

    def __init__(self, model: Optional[str] = None):
        super().__init__(
            name="blueprint_assembler_v3",
            system_prompt=SYSTEM_PROMPT,
            max_iterations=8,
            tool_timeout=30.0,
            model=model,
            temperature=0.2,  # Low temperature for deterministic assembly
        )

    def get_tool_names(self) -> List[str]:
        return [
            "assemble_blueprint",
            "validate_blueprint",
            "repair_blueprint",
            "submit_blueprint",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build task prompt summarizing available upstream data."""
        raw_design = state.get("game_design_v3")
        scene_specs = state.get("scene_specs_v3") or []
        interaction_specs = state.get("interaction_specs_v3") or []
        generated_assets = state.get("generated_assets_v3") or {}

        sections: List[str] = []

        # Design summary
        if raw_design:
            design = raw_design if isinstance(raw_design, dict) else (
                raw_design.model_dump() if hasattr(raw_design, "model_dump") else {}
            )
            title = design.get("title", "Untitled")
            scenes = design.get("scenes", [])
            labels_data = design.get("labels", {})
            if isinstance(labels_data, list):
                labels_data = {"zone_labels": labels_data}
            zone_labels = labels_data.get("zone_labels", [])
            distractor_labels = labels_data.get("distractor_labels", [])

            sections.append(
                f"## Game Design Available\n"
                f"- Title: {title}\n"
                f"- Scenes: {len(scenes)}\n"
                f"- Zone labels: {len(zone_labels)}\n"
                f"- Distractor labels: {len(distractor_labels)}"
            )
        else:
            sections.append("## WARNING: No game_design_v3 found in state!")

        # Scene specs summary
        if scene_specs:
            total_zones = sum(
                len(s.get("zones", [])) for s in scene_specs if isinstance(s, dict)
            )
            total_configs = sum(
                len(s.get("mechanic_configs", [])) for s in scene_specs if isinstance(s, dict)
            )
            sections.append(
                f"## Scene Specs Available\n"
                f"- Scene specs: {len(scene_specs)}\n"
                f"- Total spec zones: {total_zones}\n"
                f"- Total mechanic configs: {total_configs}"
            )
        else:
            sections.append("## Scene Specs: None available")

        # Interaction specs summary
        if interaction_specs:
            has_scoring = sum(
                1 for s in interaction_specs
                if isinstance(s, dict) and s.get("scoring")
            )
            has_feedback = sum(
                1 for s in interaction_specs
                if isinstance(s, dict) and s.get("feedback")
            )
            sections.append(
                f"## Interaction Specs Available\n"
                f"- Interaction specs: {len(interaction_specs)}\n"
                f"- With scoring: {has_scoring}\n"
                f"- With feedback: {has_feedback}"
            )
        else:
            sections.append("## Interaction Specs: None available")

        # Generated assets summary
        if generated_assets:
            asset_scenes = generated_assets.get("scenes", {})
            n_asset_scenes = len(asset_scenes) if isinstance(asset_scenes, dict) else 0
            total_asset_zones = 0
            if isinstance(asset_scenes, dict):
                for sn_data in asset_scenes.values():
                    if isinstance(sn_data, dict):
                        total_asset_zones += len(sn_data.get("zones", []))
            sections.append(
                f"## Generated Assets Available\n"
                f"- Asset scenes: {n_asset_scenes}\n"
                f"- Total asset zones: {total_asset_zones}"
            )
        else:
            sections.append("## Generated Assets: None available")

        sections.append(
            "\n## Your Task\n"
            "Assemble these upstream outputs into a complete InteractiveDiagramBlueprint.\n"
            "Follow the process: assemble -> validate -> repair (if needed) -> submit."
        )

        return "\n\n".join(sections)

    def parse_final_result(
        self,
        response: Any,
        state: AgentState,
    ) -> Dict[str, Any]:
        """
        Parse the final response into state updates.

        Extraction priority:
        1. submit_blueprint tool call arguments (has the final blueprint)
        2. assemble_blueprint or repair_blueprint tool results
        3. JSON in text response
        """
        blueprint = None

        # Strategy 1: Look for submit_blueprint tool call arguments
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in reversed(response.tool_calls):
                if tc.name == "submit_blueprint":
                    bp = tc.arguments.get("blueprint")
                    if bp and isinstance(bp, dict):
                        blueprint = bp
                        logger.info("Extracted blueprint from submit_blueprint tool call args")
                        break

        # Strategy 2: Look for tool results with blueprint
        if blueprint is None and hasattr(response, "tool_results") and response.tool_results:
            for tr in reversed(response.tool_results):
                if not hasattr(tr, "result") or not tr.result:
                    continue
                result = tr.result
                if isinstance(result, dict):
                    # From repair_blueprint
                    if "repaired_blueprint" in result and isinstance(result["repaired_blueprint"], dict):
                        blueprint = result["repaired_blueprint"]
                        logger.info("Extracted blueprint from repair_blueprint tool result")
                        break
                    # From assemble_blueprint
                    if "blueprint" in result and isinstance(result["blueprint"], dict):
                        blueprint = result["blueprint"]
                        logger.info("Extracted blueprint from assemble_blueprint tool result")
                        break

        # Strategy 3: Extract from text response
        if blueprint is None:
            content = response.content if hasattr(response, "content") else str(response)
            if content:
                extracted = extract_json_from_response(content)
                if isinstance(extracted, dict):
                    # Could be the blueprint itself or a wrapper
                    if extracted.get("templateType") in ("INTERACTIVE_DIAGRAM", "INTERACTIVE_DIAGRAM"):
                        blueprint = extracted
                        logger.info("Extracted blueprint from text response (direct)")
                    elif "blueprint" in extracted and isinstance(extracted["blueprint"], dict):
                        blueprint = extracted["blueprint"]
                        logger.info("Extracted blueprint from text response (wrapped)")

        if blueprint is None:
            logger.error("BlueprintAssemblerV3: Could not extract blueprint from any source")
            return {
                "current_agent": "blueprint_assembler_v3",
                "blueprint": None,
                "generation_complete": False,
                "_error": "Failed to extract blueprint from response",
            }

        # Validate that it looks like a blueprint
        if not blueprint.get("scenes"):
            logger.warning("BlueprintAssemblerV3: Blueprint has no scenes")

        logger.info(
            f"BlueprintAssemblerV3: Blueprint extracted -- "
            f"{len(blueprint.get('scenes', []))} scenes, "
            f"max_score={blueprint.get('total_max_score', 0)}"
        )

        return {
            "current_agent": "blueprint_assembler_v3",
            "blueprint": blueprint,
            "template_type": "INTERACTIVE_DIAGRAM",
            "generation_complete": True,
        }


# ---------------------------------------------------------------------------
# Agent function (LangGraph node interface)
# ---------------------------------------------------------------------------

_agent_instance: Optional[BlueprintAssemblerV3] = None


def _get_agent(model: Optional[str] = None) -> BlueprintAssemblerV3:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BlueprintAssemblerV3(model=model)
    return _agent_instance


async def blueprint_assembler_v3_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Blueprint Assembler v3 Agent -- ReAct agent for blueprint assembly.

    Reads: game_design_v3, scene_specs_v3, interaction_specs_v3, generated_assets_v3
    Writes: blueprint (InteractiveDiagramBlueprint dict)
    """
    from app.tools.v3_context import set_v3_tool_context

    logger.info("BlueprintAssemblerV3: Starting blueprint assembly (ReAct)")

    # Inject pipeline state into tool context before running ReAct loop
    set_v3_tool_context(state)

    # Get model override from state if available
    model = state.get("_model_override")
    agent = _get_agent(model)

    result = await agent.run(state, ctx)

    # Merge result into state
    return {
        **state,
        **result,
        "current_agent": "blueprint_assembler_v3",
    }


# ---------------------------------------------------------------------------
# Deterministic assembler (V4 — no LLM overhead)
# ---------------------------------------------------------------------------

MAX_REPAIR_ITERATIONS = 2


async def deterministic_blueprint_assembler_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Deterministic blueprint assembler — replaces the ReAct agent with direct
    function calls to assemble → validate → repair (loop) → finalize.

    No LLM calls. All assembly, validation, and repair logic is deterministic.

    Reads: game_design_v3, scene_specs_v3, interaction_specs_v3, generated_assets_v3
    Writes: blueprint, template_type, generation_complete
    """
    from app.tools.v3_context import set_v3_tool_context
    from app.tools.blueprint_assembler_tools import (
        assemble_blueprint_impl,
        validate_blueprint_impl,
        repair_blueprint_impl,
    )

    logger.info("Deterministic blueprint assembler: starting")

    # Inject pipeline state into tool context (same as ReAct path)
    set_v3_tool_context(state)

    # Step 1: Assemble
    try:
        assembly_result = await assemble_blueprint_impl()
    except Exception as e:
        logger.error(f"Blueprint assembly failed: {e}")
        return {
            **state,
            "current_agent": "blueprint_assembler_v3",
            "blueprint": None,
            "generation_complete": False,
            "_error": f"Assembly failed: {e}",
        }

    blueprint = assembly_result.get("blueprint")
    warnings = assembly_result.get("assembly_warnings", [])

    if not blueprint:
        logger.error("Blueprint assembly returned None")
        return {
            **state,
            "current_agent": "blueprint_assembler_v3",
            "blueprint": None,
            "generation_complete": False,
            "_error": "Assembly produced no blueprint",
        }

    if warnings:
        logger.warning(f"Assembly warnings: {warnings}")

    # Step 2: Validate → Repair loop
    for iteration in range(MAX_REPAIR_ITERATIONS + 1):
        validation = await validate_blueprint_impl(blueprint)
        is_valid = validation.get("valid", False)
        issues = validation.get("issues", [])
        fixable = validation.get("fixable_issues", [])

        if is_valid:
            logger.info(f"Blueprint valid after iteration {iteration}")
            break

        if not fixable and not issues:
            logger.info("No fixable issues found, accepting blueprint")
            break

        if iteration >= MAX_REPAIR_ITERATIONS:
            logger.warning(
                f"Blueprint still has issues after {MAX_REPAIR_ITERATIONS} repair iterations: {issues}"
            )
            break

        # Repair
        logger.info(f"Repairing blueprint (iteration {iteration + 1}): {len(fixable)} fixable issues")
        repair_result = await repair_blueprint_impl(blueprint, issues_to_fix=fixable or issues)
        repaired = repair_result.get("repaired_blueprint")
        if repaired and isinstance(repaired, dict):
            blueprint = repaired
            fixes = repair_result.get("fixes_applied", [])
            logger.info(f"Applied {len(fixes)} fixes: {fixes[:5]}")
        else:
            logger.warning("Repair returned no blueprint, keeping current")
            break

    # Step 3: Finalize
    scene_count = len(blueprint.get("scenes", []))
    if blueprint.get("is_multi_scene") and blueprint.get("game_sequence"):
        scene_count = len(blueprint["game_sequence"].get("scenes", []))

    logger.info(
        f"Deterministic assembly complete: "
        f"{scene_count} scenes, max_score={blueprint.get('total_max_score', 0)}"
    )

    if ctx:
        ctx.complete({
            "blueprint_scenes": scene_count,
            "total_max_score": blueprint.get("total_max_score", 0),
        })

    return {
        **state,
        "current_agent": "blueprint_assembler_v3",
        "blueprint": blueprint,
        "template_type": "INTERACTIVE_DIAGRAM",
        "generation_complete": True,
    }
