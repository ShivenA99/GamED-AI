"""
Asset Generator v3 — ReAct Agent for Visual Asset Generation.

Uses tool-calling to produce diagram images and zone overlays for each
scene in the game. Follows a search-first strategy: tries web search for
images, falls back to AI generation, then detects interactive zones.

Tools: search_diagram_image, generate_diagram_image, detect_zones,
       generate_animation_css, submit_assets
Output: generated_assets_v3 (per-scene assets) in state
Also writes diagram_image / diagram_zones for backward compatibility.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.agents.react_base import ReActAgent, extract_json_from_response
from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.tools.v3_context import set_v3_tool_context
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.asset_generator_v3")


SYSTEM_PROMPT = """\
You are the Asset Generator for GamED.AI. Your job: generate visual assets \
(diagram images, zone overlays) for each scene in a multi-scene, multi-mechanic game.

## Asset Generation Strategy

For each scene, you produce:
1. A clean diagram image (no text labels/annotations) showing the educational content
2. Zone overlays marking interactive regions on the diagram

## Mechanic-Aware Image Generation

Different mechanics need different visual characteristics:
- **drag_drop / click_to_identify**: Clear structures with distinct boundaries and colors
- **trace_path**: Must show pathways, tubes, vessels, or connections between structures
- **sequencing**: Show stages/phases clearly separated in spatial arrangement
- **compare_contrast**: Show two subjects side by side for visual comparison
- **sorting_categories**: Show distinct items that can be categorized
- **hierarchical**: Show nested/layered structures with clear parent-child relationships
- **description_matching / memory_match / branching_scenario**: Clear, identifiable structures

## Per-Scene Process

For each scene:
1. `search_diagram_image` -- Search for a reference image. The tool auto-generates \
   a CLEAN mechanic-aware version. Check "cleaned" field: if true, local_path is clean.
2. If search fails or cleaned=false, call `generate_diagram_image` with a detailed \
   description. You can pass reference_image_path for visual reference.
3. `detect_zones` on the CLEAN image (not the reference). Pass expected zone labels. \
   Start with detection_method="auto". If labels are missing, try "gemini" or "gemini_sam3".
4. If zone detection misses labels, retry with a different method.

After ALL scenes are done:
5. `submit_assets` -- Submit all scenes at once. Do NOT submit per-scene.

## Guidelines
- Generate assets for ALL scenes, not just the first one
- Always use the cleaned/generated image for zone detection, never the raw reference
- Zone labels must match the expected labels from scene_specs or game_design
- For multi-scene, use scene keys matching scene numbers ("1", "2", "3")
- If a scene has unique visual needs (trace_path pathways, compare side-by-side), \
  reflect this in the search query or generation description
"""


class AssetGeneratorV3(ReActAgent):
    """ReAct agent that generates visual assets for each game scene."""

    def __init__(self, model: Optional[str] = None):
        super().__init__(
            name="asset_generator_v3",
            system_prompt=SYSTEM_PROMPT,
            max_iterations=15,
            tool_timeout=120.0,  # Image ops can be slow
            model=model,
            temperature=0.3,  # Lower temp for more deterministic asset ops
        )

    def get_tool_names(self) -> List[str]:
        return [
            "search_diagram_image",
            "generate_diagram_image",
            "detect_zones",
            "generate_animation_css",
            "submit_assets",
        ]

    def build_task_prompt(self, state: AgentState) -> str:
        """Build task prompt from pipeline state, listing per-scene requirements."""
        scene_specs = state.get("scene_specs_v3") or []
        game_design = state.get("game_design_v3") or {}
        question = state.get("enhanced_question") or state.get("question_text", "")
        subject = state.get("subject", "")
        canonical_labels = state.get("canonical_labels", [])

        sections: List[str] = []

        # Context
        sections.append(f"## Question\n{question}")
        if subject:
            sections.append(f"## Subject\n{subject}")

        # Game design summary
        title = game_design.get("title", "")
        if title:
            sections.append(f"## Game Title\n{title}")

        # Known labels
        if canonical_labels:
            labels_str = ", ".join(canonical_labels[:30])
            sections.append(f"## Known Labels\n{labels_str}")

        # Per-scene specifications
        if scene_specs:
            sections.append("## Scene Specifications\n")
            for spec in scene_specs:
                scene_num = spec.get("scene_number", "?")
                scene_title = spec.get("title", f"Scene {scene_num}")

                # Extract image requirements
                image_desc = spec.get("image_description", "")
                image_reqs = spec.get("image_requirements", {})
                if isinstance(image_reqs, dict):
                    image_reqs_str = json.dumps(image_reqs, indent=2)
                elif isinstance(image_reqs, str):
                    image_reqs_str = image_reqs
                elif isinstance(image_reqs, list):
                    image_reqs_str = ", ".join(str(r) for r in image_reqs)
                else:
                    image_reqs_str = str(image_reqs) if image_reqs else ""

                # Extract expected zone labels
                zone_labels = spec.get("zone_labels", [])
                if not zone_labels:
                    zones_list = spec.get("zones", [])
                    zone_labels = [z.get("label", "") for z in zones_list if z.get("label")]

                # Extract mechanic types for this scene
                mechanic_types = []
                mechanic_configs = spec.get("mechanic_configs", [])
                for mc in mechanic_configs:
                    if isinstance(mc, dict):
                        mt = mc.get("type", "")
                        if mt:
                            mechanic_types.append(mt)
                if not mechanic_types:
                    # Fallback: from game_design scenes
                    for gd_scene in game_design.get("scenes", []):
                        if gd_scene.get("scene_number") == scene_num:
                            for m in gd_scene.get("mechanics", []):
                                mt = m.get("type", "") if isinstance(m, dict) else str(m)
                                if mt:
                                    mechanic_types.append(mt)

                scene_section = f"### Scene {scene_num}: {scene_title}\n"
                if image_desc:
                    scene_section += f"- **Image Description**: {image_desc}\n"
                if image_reqs_str:
                    scene_section += f"- **Image Requirements**: {image_reqs_str}\n"
                if mechanic_types:
                    scene_section += f"- **Mechanics**: {', '.join(mechanic_types)}\n"
                if zone_labels:
                    labels_list = ", ".join(zone_labels)
                    scene_section += f"- **Expected Zone Labels** ({len(zone_labels)}): {labels_list}\n"
                else:
                    scene_section += "- **Expected Zone Labels**: (use canonical labels from above)\n"

                sections.append(scene_section)
        else:
            # No scene specs — build from game_design scenes
            gd_scenes = game_design.get("scenes", [])
            if gd_scenes:
                sections.append("## Scenes from Game Design\n")
                for gd_scene in gd_scenes:
                    sn = gd_scene.get("scene_number", "?")
                    st = gd_scene.get("title", f"Scene {sn}")
                    sv = gd_scene.get("visual_description", "")
                    mechs = [m.get("type", "") for m in gd_scene.get("mechanics", []) if isinstance(m, dict)]
                    szl = gd_scene.get("zone_labels_in_scene", gd_scene.get("zone_labels", canonical_labels))
                    scene_section = f"### Scene {sn}: {st}\n"
                    if sv:
                        scene_section += f"- **Visual**: {sv}\n"
                    if mechs:
                        scene_section += f"- **Mechanics**: {', '.join(mechs)}\n"
                    if szl:
                        scene_section += f"- **Zone Labels**: {', '.join(str(l) for l in szl[:20])}\n"
                    sections.append(scene_section)
            else:
                sections.append(
                    "## Note\n"
                    "No scene specifications or game design scenes found. "
                    "Generate assets for a single scene using the known labels above."
                )

        # Task instructions
        sections.append("""## Your Task

Generate visual assets for EVERY scene listed above. For each scene:

1. **Search** using search_diagram_image with the scene's visual description + subject
   - The tool auto-generates a clean version. Check "cleaned" field.
   - If cleaned=false, call generate_diagram_image with reference_image_path

2. **If search fails**, call generate_diagram_image with a detailed description
   - Include mechanic-specific visual requirements (pathways for trace_path, side-by-side for compare, etc.)

3. **Detect zones** using detect_zones on the CLEAN image (not raw reference)
   - Pass expected zone labels for this scene
   - Start with detection_method="auto"
   - If labels missing, retry with "gemini" or "gemini_sam3"

4. After ALL scenes: call submit_assets with complete results

For multi-scene games, every scene must have an image and zones.
Use scene keys matching scene numbers ("1", "2", "3").
""")

        return "\n\n".join(sections)

    def parse_final_result(
        self,
        response: Any,
        state: AgentState,
    ) -> Dict[str, Any]:
        """
        Parse the LLM's final response into state updates.

        Extracts per-scene assets from:
        1. submit_assets tool results (preferred — already validated)
        2. JSON in the final response text (fallback)
        """
        content = response.content if hasattr(response, "content") else str(response)
        tool_results = response.tool_results if hasattr(response, "tool_results") else []
        tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []

        logger.info(
            f"AssetGeneratorV3: Parsing result — "
            f"content_len={len(content)}, tool_calls={len(tool_calls)}, "
            f"tool_results={len(tool_results)}"
        )

        # Strategy 1: Extract from submit_assets tool results
        assets_data = self._extract_from_submit_assets(tool_calls, tool_results)

        # Strategy 2: Try extracting from response content
        if not assets_data:
            assets_data = self._extract_from_content(content)

        # Strategy 3: Reconstruct from individual tool results
        if not assets_data:
            assets_data = self._reconstruct_from_tool_results(tool_calls, tool_results)

        if not assets_data:
            logger.error(
                "AssetGeneratorV3: Could not extract asset data from response"
            )
            return {
                "current_agent": "asset_generator_v3",
                "generated_assets_v3": None,
                "_error": "Failed to extract asset data from response",
            }

        # Build the generated_assets_v3 state field
        generated_assets = self._build_generated_assets(assets_data)

        logger.info(
            f"AssetGeneratorV3: Generated assets for "
            f"{len(generated_assets.get('scenes', {}))} scene(s)"
        )

        # Backward compatibility: write diagram_image and diagram_zones from scene 1
        result: Dict[str, Any] = {
            "current_agent": "asset_generator_v3",
            "generated_assets_v3": generated_assets,
        }

        first_scene = self._get_first_scene(generated_assets)
        if first_scene:
            # diagram_image for backward compat
            image_url = first_scene.get("diagram_image_url", "")
            image_path = first_scene.get("diagram_image_path", "")
            if image_url or image_path:
                result["diagram_image"] = {
                    "image_url": image_url,
                    "local_path": image_path,
                    "url": image_url,
                    "source": "asset_generator_v3",
                }

            # diagram_zones for backward compat
            zones = first_scene.get("zones", [])
            if zones:
                result["diagram_zones"] = zones

        return result

    def _extract_from_submit_assets(
        self,
        tool_calls: List[Any],
        tool_results: List[Any],
    ) -> Optional[Dict[str, Any]]:
        """Extract asset data from submit_assets tool call results."""
        for tc, tr in zip(tool_calls, tool_results):
            if not hasattr(tc, "name"):
                continue
            if tc.name != "submit_assets":
                continue

            result = tr.result if hasattr(tr, "result") else tr
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    continue

            if not isinstance(result, dict):
                continue

            status = result.get("status", "")
            if status == "accepted":
                validated = result.get("validated_scenes", {})
                if validated:
                    return {"scenes": validated, "source": "submit_assets_accepted"}

            # Even if rejected, try to use the input from the tool call
            if hasattr(tc, "arguments") and isinstance(tc.arguments, dict):
                scenes = tc.arguments.get("scenes", {})
                if scenes:
                    return {"scenes": scenes, "source": "submit_assets_input"}

        return None

    def _extract_from_content(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract asset data from the final response text."""
        parsed = extract_json_from_response(content)
        if not parsed:
            return None

        # Check if this looks like an asset bundle
        if isinstance(parsed, dict):
            if "scenes" in parsed:
                return {"scenes": parsed["scenes"], "source": "response_json"}
            # Maybe the top-level keys are scene numbers
            if any(key.isdigit() for key in parsed.keys()):
                scenes = {}
                for key, val in parsed.items():
                    if isinstance(val, dict) and ("zones" in val or "diagram_image_url" in val):
                        scenes[key] = val
                if scenes:
                    return {"scenes": scenes, "source": "response_json_scenes"}

        return None

    def _reconstruct_from_tool_results(
        self,
        tool_calls: List[Any],
        tool_results: List[Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Reconstruct asset data from individual search/detect tool results.

        This is the last-resort fallback: gather images and zones from
        the tool call history.
        """
        images: Dict[str, Dict[str, Any]] = {}  # scene_num → image info
        zones: Dict[str, List[Dict[str, Any]]] = {}  # scene_num → zones
        methods: Dict[str, str] = {}  # scene_num → detection method

        # We process tool results in order, building up per-scene data
        # Since we don't know which scene each call was for, we assign
        # images and zones to scene "1" by default (or increment if we
        # see multiple image results).
        current_scene = "1"
        scene_counter = 1

        for tc, tr in zip(tool_calls, tool_results):
            if not hasattr(tc, "name"):
                continue

            result = tr.result if hasattr(tr, "result") else tr
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    continue
            if not isinstance(result, dict):
                continue

            if tc.name == "search_diagram_image" and result.get("success"):
                # If we already have an image for this scene, move to next
                if current_scene in images:
                    scene_counter += 1
                    current_scene = str(scene_counter)
                images[current_scene] = {
                    "diagram_image_url": result.get("image_url", ""),
                    "diagram_image_path": result.get("local_path", ""),
                }

            elif tc.name == "generate_diagram_image" and result.get("success"):
                if current_scene in images:
                    scene_counter += 1
                    current_scene = str(scene_counter)
                images[current_scene] = {
                    "diagram_image_url": "",
                    "diagram_image_path": result.get("generated_path", ""),
                }

            elif tc.name == "detect_zones" and result.get("success"):
                detected = result.get("zones", [])
                method = result.get("method_used", "unknown")
                zones[current_scene] = detected
                methods[current_scene] = method

        # Merge images and zones into scenes
        if not images and not zones:
            return None

        all_scene_keys = sorted(set(list(images.keys()) + list(zones.keys())))
        scenes = {}
        for sk in all_scene_keys:
            scene_data = images.get(sk, {})
            scene_data["zones"] = zones.get(sk, [])
            scene_data["zone_detection_method"] = methods.get(sk, "unknown")
            scene_data.setdefault("diagram_image_url", "")
            scene_data.setdefault("diagram_image_path", "")
            scenes[sk] = scene_data

        return {"scenes": scenes, "source": "reconstructed"}

    def _build_generated_assets(self, assets_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the generated_assets_v3 state field from extracted data.

        Returns:
            Dict with scenes, metadata, and summary.
        """
        scenes = assets_data.get("scenes", {})
        source = assets_data.get("source", "unknown")

        # Normalize keys: LLM may use "diagram_image" instead of the expected
        # "diagram_image_url" / "diagram_image_path" keys
        for scene_key, scene_data in scenes.items():
            if not isinstance(scene_data, dict):
                continue
            di = scene_data.get("diagram_image")
            if di and not scene_data.get("diagram_image_url") and not scene_data.get("diagram_image_path"):
                if isinstance(di, str):
                    if di.startswith("http"):
                        scene_data["diagram_image_url"] = di
                        scene_data.setdefault("diagram_image_path", "")
                    else:
                        scene_data["diagram_image_path"] = di
                        scene_data.setdefault("diagram_image_url", "")

        total_zones = 0
        scenes_with_images = 0
        for scene_key, scene_data in scenes.items():
            zone_list = scene_data.get("zones", [])
            total_zones += len(zone_list)
            if scene_data.get("diagram_image_url") or scene_data.get("diagram_image_path"):
                scenes_with_images += 1

        return {
            "scenes": scenes,
            "metadata": {
                "source": source,
                "scene_count": len(scenes),
                "scenes_with_images": scenes_with_images,
                "total_zones": total_zones,
            },
        }

    def _get_first_scene(self, generated_assets: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the first scene data for backward compatibility."""
        scenes = generated_assets.get("scenes", {})
        if not scenes:
            return None
        # Try scene "1" first, then the first available key
        if "1" in scenes:
            return scenes["1"]
        first_key = sorted(scenes.keys())[0]
        return scenes[first_key]


# ---------------------------------------------------------------------------
# Agent function (LangGraph node interface)
# ---------------------------------------------------------------------------

_agent_instance: Optional[AssetGeneratorV3] = None


def _get_agent(model: Optional[str] = None) -> AssetGeneratorV3:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AssetGeneratorV3(model=model)
    return _agent_instance


async def asset_generator_v3_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None,
) -> AgentState:
    """
    Asset Generator v3 Agent — ReAct agent for visual asset generation.

    Reads: scene_specs_v3, game_design_v3, canonical_labels, subject,
           enhanced_question, domain_knowledge
    Writes: generated_assets_v3, diagram_image (compat), diagram_zones (compat)
    """
    logger.info("AssetGeneratorV3: Starting asset generation")

    # Inject pipeline state into tool context
    set_v3_tool_context(state)

    # Get model override from state if available
    model = state.get("_model_override")
    agent = _get_agent(model)

    result = await agent.run(state, ctx)

    # Merge result into state
    return {
        **state,
        **result,
        "current_agent": "asset_generator_v3",
    }
