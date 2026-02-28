"""
Game Design Tools for GamED.AI v2

Tools for planning game mechanics, designing scene structure, and managing interactions.
These tools support the game design phase of the pipeline.
"""

import json
from typing import Dict, Any, List, Optional

from app.utils.logging_config import get_logger
from app.tools.registry import register_tool

logger = get_logger("gamed_ai.tools.game_design")


# ============================================================================
# Game Mechanics
# ============================================================================

async def plan_mechanics_impl(
    question: str,
    blooms_level: str,
    template_name: str,
    learning_objectives: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Plan game mechanics based on pedagogical context.

    Args:
        question: The educational question
        blooms_level: Bloom's taxonomy level
        template_name: Selected game template
        learning_objectives: Optional specific learning objectives

    Returns:
        Dict with mechanics, scoring_rules, feedback_patterns
    """
    from app.services.llm_service import get_llm_service

    llm = get_llm_service()

    mechanics_prompt = f"""Design game mechanics for this educational game:

Question: {question}
Bloom's Level: {blooms_level}
Template: {template_name}
Learning Objectives: {json.dumps(learning_objectives or [])}

Design mechanics that:
1. Align with the Bloom's taxonomy level
2. Provide appropriate challenge for learning
3. Give meaningful feedback

Respond in JSON format:
{{
    "core_mechanic": "description of main game mechanic",
    "interaction_type": "drag_drop|click|type|sequence",
    "difficulty_level": "easy|medium|hard",
    "time_limit": null or seconds,
    "scoring_rules": {{
        "correct_answer": 10,
        "partial_credit": 5,
        "hint_penalty": -2,
        "time_bonus": true
    }},
    "feedback_patterns": {{
        "on_correct": "immediate|delayed|summary",
        "on_incorrect": "immediate|delayed|summary",
        "show_explanation": true
    }},
    "progression": {{
        "allows_retry": true,
        "max_attempts": 3,
        "scaffolding": true
    }}
}}"""

    try:
        result = await llm.generate_json(
            prompt=mechanics_prompt,
            system_prompt="You are an educational game designer. Design engaging, pedagogically-sound mechanics."
        )

        return {
            "mechanics": result,
            "template": template_name,
            "blooms_level": blooms_level
        }

    except Exception as e:
        logger.error(f"Mechanics planning failed: {e}")
        # Return sensible defaults
        return {
            "mechanics": {
                "core_mechanic": "drag and drop labeling",
                "interaction_type": "drag_drop",
                "difficulty_level": "medium",
                "time_limit": None,
                "scoring_rules": {
                    "correct_answer": 10,
                    "partial_credit": 5,
                    "hint_penalty": -2
                },
                "feedback_patterns": {
                    "on_correct": "immediate",
                    "on_incorrect": "immediate",
                    "show_explanation": True
                },
                "progression": {
                    "allows_retry": True,
                    "max_attempts": 3
                }
            },
            "template": template_name,
            "blooms_level": blooms_level,
            "error": str(e)
        }


async def validate_mechanics_impl(
    mechanics: Dict[str, Any],
    template_name: str
) -> Dict[str, Any]:
    """
    Validate game mechanics against template requirements.

    Args:
        mechanics: The mechanics specification
        template_name: Template to validate against

    Returns:
        Dict with valid, errors, warnings
    """
    errors = []
    warnings = []

    # Required fields
    required = ["core_mechanic", "interaction_type", "scoring_rules"]
    for field in required:
        if field not in mechanics:
            errors.append(f"Missing required field: {field}")

    # Template-specific validation
    if template_name == "INTERACTIVE_DIAGRAM":
        if mechanics.get("interaction_type") not in ["drag_drop", "click"]:
            warnings.append("INTERACTIVE_DIAGRAM works best with drag_drop or click interaction")

    elif template_name == "SEQUENCE_BUILDER":
        if mechanics.get("interaction_type") not in ["drag_drop", "sequence"]:
            warnings.append("SEQUENCE_BUILDER requires drag_drop or sequence interaction")

    # Scoring validation
    scoring = mechanics.get("scoring_rules", {})
    if scoring.get("correct_answer", 0) <= 0:
        errors.append("correct_answer score must be positive")

    # Progression validation
    progression = mechanics.get("progression", {})
    if progression.get("max_attempts", 1) < 1:
        errors.append("max_attempts must be at least 1")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "mechanics": mechanics
    }


# ============================================================================
# Scene Structure
# ============================================================================

async def design_structure_impl(
    game_plan: Dict[str, Any],
    diagram_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Design the scene structure/layout for the game.

    Args:
        game_plan: Game plan with mechanics and objectives
        diagram_info: Optional diagram zones and labels

    Returns:
        Dict with layout, regions, visual_hierarchy
    """
    from app.services.llm_service import get_llm_service

    llm = get_llm_service()

    # Determine zones needed
    zones = diagram_info.get("zones", []) if diagram_info else []
    zone_count = len(zones)

    structure_prompt = f"""Design the visual layout structure for this educational game:

Game Plan: {json.dumps(game_plan, indent=2)}
Number of interactive zones: {zone_count}
Zones: {json.dumps(zones[:5], indent=2) if zones else "Not specified"}

Design a layout that:
1. Centers the main learning content
2. Provides clear visual hierarchy
3. Has intuitive interaction areas
4. Includes space for labels/answers

Respond in JSON format:
{{
    "layout_type": "centered|split|grid|custom",
    "regions": [
        {{
            "id": "main_content",
            "type": "diagram|image|text",
            "position": {{"x": 0.5, "y": 0.4}},
            "size": {{"width": 0.8, "height": 0.6}},
            "purpose": "Primary learning content"
        }},
        {{
            "id": "label_tray",
            "type": "interactive",
            "position": {{"x": 0.5, "y": 0.9}},
            "size": {{"width": 0.9, "height": 0.15}},
            "purpose": "Draggable labels"
        }}
    ],
    "visual_hierarchy": {{
        "primary_focus": "main_content",
        "secondary": ["label_tray"],
        "decorative": []
    }},
    "spacing": {{
        "margin": 20,
        "padding": 15,
        "gap": 10
    }}
}}"""

    try:
        result = await llm.generate_json(
            prompt=structure_prompt,
            system_prompt="You are a UI/UX designer for educational games. Create clear, engaging layouts."
        )

        return {
            "structure": result,
            "zone_count": zone_count
        }

    except Exception as e:
        logger.error(f"Structure design failed: {e}")
        return {
            "structure": {
                "layout_type": "centered",
                "regions": [
                    {
                        "id": "main_content",
                        "type": "diagram",
                        "position": {"x": 0.5, "y": 0.4},
                        "size": {"width": 0.8, "height": 0.6}
                    },
                    {
                        "id": "label_tray",
                        "type": "interactive",
                        "position": {"x": 0.5, "y": 0.9},
                        "size": {"width": 0.9, "height": 0.15}
                    }
                ],
                "visual_hierarchy": {
                    "primary_focus": "main_content",
                    "secondary": ["label_tray"]
                }
            },
            "zone_count": zone_count,
            "error": str(e)
        }


async def validate_layout_impl(
    layout: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate a scene layout structure.

    Args:
        layout: The layout specification

    Returns:
        Dict with valid, errors, warnings
    """
    errors = []
    warnings = []

    structure = layout.get("structure", layout)

    # Check for required regions
    regions = structure.get("regions", [])
    if not regions:
        errors.append("Layout must have at least one region")

    # Validate each region
    region_ids = set()
    for i, region in enumerate(regions):
        if "id" not in region:
            errors.append(f"Region {i}: missing id")
        else:
            if region["id"] in region_ids:
                errors.append(f"Duplicate region id: {region['id']}")
            region_ids.add(region["id"])

        if "position" not in region:
            warnings.append(f"Region {i}: missing position")

        # Check position bounds
        pos = region.get("position", {})
        x, y = pos.get("x", 0.5), pos.get("y", 0.5)
        if not (0 <= x <= 1 and 0 <= y <= 1):
            warnings.append(f"Region {region.get('id', i)}: position out of bounds")

    # Check visual hierarchy
    hierarchy = structure.get("visual_hierarchy", {})
    primary = hierarchy.get("primary_focus")
    if primary and primary not in region_ids:
        errors.append(f"Primary focus '{primary}' not found in regions")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "region_count": len(regions)
    }


# ============================================================================
# Asset Population
# ============================================================================

async def populate_assets_impl(
    structure: Dict[str, Any],
    zones: List[Dict[str, Any]],
    labels: List[str]
) -> Dict[str, Any]:
    """
    Populate the structure with specific assets.

    Args:
        structure: Scene structure from design_structure
        zones: Detected zones with positions
        labels: Labels for the diagram

    Returns:
        Dict with populated_structure containing all assets
    """
    populated = json.loads(json.dumps(structure))  # Deep copy

    # Add zones as elements
    elements = []

    for i, zone in enumerate(zones):
        label = labels[i] if i < len(labels) else f"Zone {i+1}"

        elements.append({
            "id": f"drop_zone_{i}",
            "type": "drop_zone",
            "position": {
                "x": zone.get("center", [0.5, 0.5])[0],
                "y": zone.get("center", [0.5, 0.5])[1]
            },
            "size": {"width": 80, "height": 40},
            "correct_label": label,
            "style": {
                "fill": "rgba(59, 130, 246, 0.1)",
                "stroke": "#3B82F6",
                "stroke_width": 2
            }
        })

    # Add label chips
    for i, label in enumerate(labels):
        elements.append({
            "id": f"label_chip_{i}",
            "type": "label_chip",
            "text": label,
            "target_zone": f"drop_zone_{i}",
            "draggable": True,
            "style": {
                "fill": "white",
                "stroke": "#E5E7EB",
                "text_color": "#1F2937"
            }
        })

    populated["elements"] = elements
    populated["zone_count"] = len(zones)
    populated["label_count"] = len(labels)

    return {
        "populated_structure": populated,
        "element_count": len(elements)
    }


async def lookup_asset_library_impl(
    asset_type: str,
    query: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Look up available assets in the asset library.

    Args:
        asset_type: Type of asset to look up
        query: Optional search query
        tags: Optional filter tags

    Returns:
        Dict with assets list
    """
    # This would connect to an actual asset library in production
    # For now, return sample assets

    sample_assets = {
        "background": [
            {"id": "bg_white", "url": None, "description": "White background"},
            {"id": "bg_light", "url": None, "description": "Light gray background"},
            {"id": "bg_grid", "url": None, "description": "Grid pattern background"}
        ],
        "icon": [
            {"id": "icon_check", "svg": "check", "description": "Checkmark icon"},
            {"id": "icon_cross", "svg": "cross", "description": "Cross icon"},
            {"id": "icon_star", "svg": "star", "description": "Star icon"}
        ],
        "decoration": [
            {"id": "deco_corner", "svg": "corner", "description": "Corner decoration"},
            {"id": "deco_divider", "svg": "divider", "description": "Divider line"}
        ]
    }

    assets = sample_assets.get(asset_type, [])

    if query:
        query_lower = query.lower()
        assets = [a for a in assets if query_lower in a.get("description", "").lower()]

    return {
        "assets": assets,
        "asset_type": asset_type,
        "count": len(assets)
    }


# ============================================================================
# Interactions
# ============================================================================

async def define_interactions_impl(
    populated_structure: Dict[str, Any],
    mechanics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Define interactions between game elements.

    Args:
        populated_structure: Structure with populated assets
        mechanics: Game mechanics specification

    Returns:
        Dict with interactions list
    """
    elements = populated_structure.get("elements", [])
    interaction_type = mechanics.get("interaction_type") or ""

    interactions = []

    # Find drop zones and labels
    drop_zones = [e for e in elements if e.get("type") == "drop_zone"]
    label_chips = [e for e in elements if e.get("type") == "label_chip"]

    for zone in drop_zones:
        # Find matching label
        matching_label = next(
            (l for l in label_chips if l.get("target_zone") == zone["id"]),
            None
        )

        if matching_label:
            interactions.append({
                "id": f"interaction_{zone['id']}",
                "type": interaction_type,
                "source": matching_label["id"],
                "target": zone["id"],
                "validation": {
                    "type": "exact_match",
                    "correct_value": zone.get("correct_label")
                },
                "feedback": {
                    "on_correct": {
                        "action": "snap_to_zone",
                        "visual": "success_highlight",
                        "audio": "success_sound"
                    },
                    "on_incorrect": {
                        "action": "bounce_back",
                        "visual": "error_highlight",
                        "audio": "error_sound"
                    }
                }
            })

    return {
        "interactions": interactions,
        "interaction_count": len(interactions),
        "interaction_type": interaction_type
    }


async def validate_interactions_impl(
    interactions: List[Dict[str, Any]],
    elements: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validate interactions against available elements.

    Args:
        interactions: List of interaction definitions
        elements: List of elements in the scene

    Returns:
        Dict with valid, errors, warnings
    """
    errors = []
    warnings = []

    element_ids = {e.get("id") for e in elements}

    for i, interaction in enumerate(interactions):
        # Check source exists
        source = interaction.get("source")
        if source and source not in element_ids:
            errors.append(f"Interaction {i}: source '{source}' not found")

        # Check target exists
        target = interaction.get("target")
        if target and target not in element_ids:
            errors.append(f"Interaction {i}: target '{target}' not found")

        # Check validation
        if "validation" not in interaction:
            warnings.append(f"Interaction {i}: missing validation rules")

        # Check feedback
        if "feedback" not in interaction:
            warnings.append(f"Interaction {i}: missing feedback configuration")

    # Check all elements have interactions
    interactive_elements = [e for e in elements if e.get("type") in ["drop_zone", "label_chip"]]
    interacted_elements = set()
    for interaction in interactions:
        interacted_elements.add(interaction.get("source"))
        interacted_elements.add(interaction.get("target"))

    for elem in interactive_elements:
        if elem.get("id") not in interacted_elements:
            warnings.append(f"Element '{elem.get('id')}' has no interactions")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "interaction_count": len(interactions)
    }


async def validate_scene_impl(
    scene: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform comprehensive scene validation.

    Args:
        scene: Complete scene specification

    Returns:
        Dict with valid, errors, warnings, scores
    """
    errors = []
    warnings = []
    scores = {
        "structure": 1.0,
        "assets": 1.0,
        "interactions": 1.0,
        "completeness": 1.0
    }

    # Structure validation
    if "regions" not in scene and "structure" not in scene:
        errors.append("Scene missing structure/regions")
        scores["structure"] = 0

    # Elements validation
    elements = scene.get("elements", [])
    if not elements:
        errors.append("Scene has no elements")
        scores["assets"] = 0
    else:
        # Check for required element types
        element_types = {e.get("type") for e in elements}
        if "drop_zone" not in element_types:
            warnings.append("No drop zones defined")
            scores["assets"] -= 0.3
        if "label_chip" not in element_types:
            warnings.append("No label chips defined")
            scores["assets"] -= 0.3

    # Interactions validation
    interactions = scene.get("interactions", [])
    if not interactions:
        warnings.append("No interactions defined")
        scores["interactions"] = 0.5

    # Completeness check
    required_fields = ["elements", "background"]
    missing = [f for f in required_fields if f not in scene]
    if missing:
        warnings.append(f"Missing optional fields: {missing}")
        scores["completeness"] -= len(missing) * 0.2

    overall_score = sum(scores.values()) / len(scores)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "scores": scores,
        "overall_score": round(overall_score, 2)
    }


# ============================================================================
# Tool Registration
# ============================================================================

def register_game_design_tools() -> None:
    """Register all game design tools in the registry."""

    register_tool(
        name="plan_mechanics",
        description="Plan game mechanics based on pedagogical context. Returns scoring rules, feedback patterns, and progression settings.",
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The educational question"
                },
                "blooms_level": {
                    "type": "string",
                    "description": "Bloom's taxonomy level"
                },
                "template_name": {
                    "type": "string",
                    "description": "Selected game template"
                },
                "learning_objectives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific learning objectives"
                }
            },
            "required": ["question", "blooms_level", "template_name"]
        },
        function=plan_mechanics_impl
    )

    register_tool(
        name="validate_mechanics",
        description="Validate game mechanics against template requirements.",
        parameters={
            "type": "object",
            "properties": {
                "mechanics": {
                    "type": "object",
                    "description": "The mechanics specification"
                },
                "template_name": {
                    "type": "string",
                    "description": "Template to validate against"
                }
            },
            "required": ["mechanics", "template_name"]
        },
        function=validate_mechanics_impl
    )

    register_tool(
        name="design_structure",
        description="Design the scene structure/layout for the game. Returns regions and visual hierarchy.",
        parameters={
            "type": "object",
            "properties": {
                "game_plan": {
                    "type": "object",
                    "description": "Game plan with mechanics"
                },
                "diagram_info": {
                    "type": "object",
                    "description": "Optional diagram zones and labels"
                }
            },
            "required": ["game_plan"]
        },
        function=design_structure_impl
    )

    register_tool(
        name="validate_layout",
        description="Validate a scene layout structure.",
        parameters={
            "type": "object",
            "properties": {
                "layout": {
                    "type": "object",
                    "description": "The layout specification"
                }
            },
            "required": ["layout"]
        },
        function=validate_layout_impl
    )

    register_tool(
        name="populate_assets",
        description="Populate the structure with specific assets based on zones and labels.",
        parameters={
            "type": "object",
            "properties": {
                "structure": {
                    "type": "object",
                    "description": "Scene structure from design_structure"
                },
                "zones": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Detected zones"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels for the diagram"
                }
            },
            "required": ["structure", "zones", "labels"]
        },
        function=populate_assets_impl
    )

    register_tool(
        name="lookup_asset_library",
        description="Look up available assets in the asset library.",
        parameters={
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "Type of asset"
                },
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter tags"
                }
            },
            "required": ["asset_type"]
        },
        function=lookup_asset_library_impl
    )

    register_tool(
        name="define_interactions",
        description="Define interactions between game elements.",
        parameters={
            "type": "object",
            "properties": {
                "populated_structure": {
                    "type": "object",
                    "description": "Structure with assets"
                },
                "mechanics": {
                    "type": "object",
                    "description": "Game mechanics"
                }
            },
            "required": ["populated_structure", "mechanics"]
        },
        function=define_interactions_impl
    )

    register_tool(
        name="validate_interactions",
        description="Validate interactions against available elements.",
        parameters={
            "type": "object",
            "properties": {
                "interactions": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Interaction definitions"
                },
                "elements": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Scene elements"
                }
            },
            "required": ["interactions", "elements"]
        },
        function=validate_interactions_impl
    )

    register_tool(
        name="validate_scene",
        description="Perform comprehensive scene validation including structure, assets, and interactions.",
        parameters={
            "type": "object",
            "properties": {
                "scene": {
                    "type": "object",
                    "description": "Complete scene specification"
                }
            },
            "required": ["scene"]
        },
        function=validate_scene_impl
    )

    logger.info("Game design tools registered")
