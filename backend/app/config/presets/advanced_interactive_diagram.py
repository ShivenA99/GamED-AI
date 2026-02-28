"""
Advanced Label Diagram Preset (Preset 2)

Production-ready pipeline for generating world-class interactive
label diagram games with:
- Multi-scene support (zoom-in, depth-first, linear progressions)
- Unlimited hierarchy depth with progressive reveal
- Polygon zone shapes (exact structure outlines)
- 8+ interaction modes
- Multiple diagram types (anatomy, flowchart, chart, map, timeline)
- Bloom's taxonomy -> interaction mode mapping
- Description-based matching

Pipeline Flow:
    input_enhancer
        -> domain_knowledge_retriever
        -> diagram_type_classifier (NEW)
        -> router
        -> scene_sequencer (NEW - detects multi-scene need)
        -> game_planner (Bloom's -> interaction mapping)
        -> scene_stage1_structure
        -> scene_stage2_assets
        -> scene_stage3_interactions
        -> diagram_image_retriever
        -> diagram_image_generator
        -> gemini_zone_detector (polygon support, multi-level)
        -> blueprint_generator (multi-scene, new interaction modes)
        -> blueprint_validator
        -> asset_planner
        -> asset_generator_orchestrator
        -> diagram_spec_generator
        -> diagram_svg_generator
        -> END
"""

PRESET_CONFIG = {
    "name": "advanced_interactive_diagram",
    "description": "Advanced label diagram with multi-scene, polygon zones, and 8+ interaction modes",
    "version": "2.0.0",

    # Feature flags for this preset
    "features": {
        # === INHERITED FROM PRESET 1 ===
        "use_image_retrieval": True,
        "use_diagram_generation": True,
        "use_gemini_zone_detection": True,
        "diagram_generator": "gemini",  # Prefer Gemini Imagen
        "diagram_style": "clean_educational",
        "use_scene_stages": True,
        "use_anthropic_assets": True,
        "zone_detection_method": "gemini_vlm",
        "strict_validation": True,

        # === NEW PRESET 2 FEATURES ===

        # Multi-scene support
        "use_multi_scene": True,
        "use_scene_sequencer": True,
        "max_scenes": 5,
        "scene_progression_types": ["linear", "zoom_in", "depth_first", "branching"],

        # Advanced zone detection
        "use_polygon_zones": True,          # Exact shape outlines
        "unlimited_hierarchy_depth": True,  # >2 levels
        "zone_shape_types": ["circle", "polygon", "rectangle"],

        # Diagram type classification
        "use_diagram_type_classifier": True,
        "supported_diagram_types": [
            "anatomy", "flowchart", "chart", "map",
            "timeline", "org_chart", "circuit", "mathematical"
        ],

        # Interaction modes
        "supported_interaction_modes": [
            "drag_drop",
            "click_to_identify",
            "trace_path",
            "hierarchical",
            "description_matching",    # NEW
            "compare_contrast",        # NEW
            "sequencing",              # NEW
            "timed_challenge",         # NEW
        ],

        # Bloom's integration
        "use_blooms_interaction_mapping": True,
        "blooms_guides_interaction": True,  # Not difficulty!

        # Description matching
        "use_description_matching": True,
        "description_source": "zone.description",  # Already exists!

        # Progressive reveal
        "progressive_reveal_enabled": True,
        "reveal_triggers": [
            "complete_parent",
            "click_expand",
            "hover_reveal",
            "stage_complete"
        ],

        # Hierarchy settings
        "use_hierarchical_mode": True,
    },

    # Agents specific to Preset 2
    "additional_agents": [
        "diagram_type_classifier",  # NEW
        "scene_sequencer",          # NEW
    ],

    # Agents disabled (same as Preset 1)
    "disabled_agents": [
        "image_label_classifier",
        "image_label_remover",
        "qwen_annotation_detector",
        "qwen_sam_zone_detector",
        "direct_structure_locator",
        "sam3_prompt_generator",
        "diagram_image_segmenter",
        "diagram_zone_labeler",
    ],

    # Model assignments
    "agent_models": {
        # Input processing
        "input_enhancer": "gemini-2.0-flash-lite",
        "domain_knowledge_retriever": "gemini-2.0-flash",
        "router": "gemini-2.0-flash-lite",

        # NEW: Diagram type classification
        "diagram_type_classifier": "gemini-2.0-flash-lite",

        # NEW: Scene sequencing
        "scene_sequencer": "gemini-2.0-flash",

        # Planning
        "game_planner": "gemini-2.0-flash",

        # Scene generation
        "scene_stage1_structure": "gemini-2.0-flash",
        "scene_stage2_assets": "gemini-2.0-flash",
        "scene_stage3_interactions": "gemini-2.0-flash",

        # Image pipeline
        "diagram_image_retriever": "gemini-2.0-flash-lite",
        "diagram_image_generator": "imagen-3",
        "gemini_zone_detector": "gemini-2.0-flash",

        # Blueprint generation
        "blueprint_generator": "gemini-2.0-flash",
        "blueprint_validator": "gemini-2.0-flash-lite",

        # Asset generation
        "asset_planner": "gemini-2.0-flash-lite",
        "asset_generator_orchestrator": "gemini-2.0-flash",

        # Diagram spec/SVG
        "diagram_spec_generator": "gemini-2.0-flash",
        "diagram_svg_generator": "gemini-2.0-flash-lite",
    },

    # Temperature settings per agent
    "agent_temperatures": {
        "input_enhancer": 0.3,
        "domain_knowledge_retriever": 0.2,
        "router": 0.1,
        "diagram_type_classifier": 0.1,
        "scene_sequencer": 0.4,
        "game_planner": 0.7,
        "scene_stage1_structure": 0.5,
        "scene_stage2_assets": 0.5,
        "scene_stage3_interactions": 0.5,
        "diagram_image_generator": 0.7,       # Some creativity for images
        "gemini_zone_detector": 0.1,          # Precise zone detection
        "blueprint_generator": 0.2,
        "blueprint_validator": 0.1,
        "asset_planner": 0.3,
        "asset_generator_orchestrator": 0.5,
        "diagram_spec_generator": 0.2,
        "diagram_svg_generator": 0.1,
    },

    # Max tokens per agent
    "agent_max_tokens": {
        "game_planner": 4096,
        "scene_sequencer": 2048,
        "scene_stage1_structure": 4096,
        "scene_stage2_assets": 4096,
        "scene_stage3_interactions": 4096,
        "blueprint_generator": 16384,  # Larger for multi-scene
        "diagram_spec_generator": 8192,
    },

    # Pipeline routing configuration
    "routing": {
        # NEW: Diagram type classification after domain knowledge
        "domain_knowledge_retriever_next": "diagram_type_classifier",
        "diagram_type_classifier_next": "router",

        # NEW: Scene sequencer after game planner
        "game_planner_next": "scene_sequencer",
        "scene_sequencer_next": "scene_stage1_structure",

        # Rest same as Preset 1
        "diagram_image_retriever_next": "diagram_image_generator",
        "diagram_image_generator_next": "gemini_zone_detector",
        "gemini_zone_detector_next": "blueprint_generator",
    },

    # Environment variable requirements
    "required_env_vars": [
        "GOOGLE_API_KEY",   # For all Gemini models
        "SERPER_API_KEY",   # For image search
    ],

    # Optional environment variables
    "optional_env_vars": [
        "OPENAI_API_KEY",       # For DALL-E 3 (if using OpenAI generation)
        "ANTHROPIC_API_KEY",    # For Claude models
        "GROQ_API_KEY",         # For fast LLM calls
    ],
}


# Bloom's taxonomy to interaction mode mapping
BLOOMS_INTERACTION_MAPPING = {
    "remember": {
        "primary_mode": "click_to_identify",
        "secondary_mode": "drag_drop",
        "features": {"guided_prompts": True, "show_hints": True}
    },
    "understand": {
        "primary_mode": "drag_drop",
        "secondary_mode": "description_matching",
        "features": {"label_shuffling": True}
    },
    "apply": {
        "primary_mode": "description_matching",
        "secondary_mode": "trace_path",
        "features": {"show_descriptions": True}
    },
    "analyze": {
        "primary_mode": "hierarchical",
        "secondary_mode": "trace_path",
        "features": {"progressive_reveal": True}
    },
    "evaluate": {
        "primary_mode": "compare_contrast",
        "secondary_mode": "hierarchical",
        "features": {"multi_diagram": True}
    },
    "create": {
        "primary_mode": "sequencing",
        "secondary_mode": "timed_challenge",
        "features": {"drawing_tools": False}  # Placeholder for future
    }
}


# Diagram type configurations
DIAGRAM_TYPES = {
    "anatomy": {
        "keywords": ["parts", "organs", "anatomy", "structure", "cells", "label", "body", "system"],
        "search_suffix": "diagram labeled educational",
        "zone_strategy": "vlm_per_label",
        "default_interaction": "drag_drop"
    },
    "flowchart": {
        "keywords": ["flowchart", "process", "steps", "workflow", "algorithm", "flow"],
        "search_suffix": "flowchart diagram",
        "zone_strategy": "shape_detection",
        "default_interaction": "trace_path"
    },
    "chart": {
        "keywords": ["chart", "graph", "data", "statistics", "visualization", "pie", "bar"],
        "search_suffix": "chart visualization",
        "zone_strategy": "axis_detection",
        "default_interaction": "click_to_identify"
    },
    "map": {
        "keywords": ["map", "geography", "countries", "regions", "locations", "continent", "world"],
        "search_suffix": "map political",
        "zone_strategy": "boundary_detection",
        "default_interaction": "hierarchical"
    },
    "timeline": {
        "keywords": ["timeline", "history", "chronological", "events", "dates", "era"],
        "search_suffix": "timeline diagram",
        "zone_strategy": "sequential_detection",
        "default_interaction": "sequencing"
    },
    "org_chart": {
        "keywords": ["organization", "hierarchy", "structure", "org chart", "management"],
        "search_suffix": "organization chart",
        "zone_strategy": "hierarchical_detection",
        "default_interaction": "hierarchical"
    },
    "circuit": {
        "keywords": ["circuit", "electrical", "electronics", "components", "schematic"],
        "search_suffix": "circuit diagram schematic",
        "zone_strategy": "component_detection",
        "default_interaction": "trace_path"
    },
    "mathematical": {
        "keywords": ["graph", "function", "equation", "coordinate", "geometry", "math"],
        "search_suffix": "mathematical diagram",
        "zone_strategy": "coordinate_detection",
        "default_interaction": "click_to_identify"
    },
}


def get_blooms_interaction(blooms_level: str) -> dict:
    """
    Get the interaction mode configuration for a Bloom's taxonomy level.

    Args:
        blooms_level: Bloom's taxonomy level (remember, understand, apply, analyze, evaluate, create)

    Returns:
        Dictionary with primary_mode, secondary_mode, and features
    """
    return BLOOMS_INTERACTION_MAPPING.get(
        blooms_level.lower(),
        BLOOMS_INTERACTION_MAPPING["understand"]  # Default to "understand"
    )


def get_diagram_type_config(diagram_type: str) -> dict:
    """
    Get configuration for a diagram type.

    Args:
        diagram_type: Type of diagram (anatomy, flowchart, etc.)

    Returns:
        Dictionary with keywords, search_suffix, zone_strategy, and default_interaction
    """
    return DIAGRAM_TYPES.get(
        diagram_type.lower(),
        DIAGRAM_TYPES["anatomy"]  # Default to "anatomy"
    )


def detect_diagram_type(question_text: str) -> str:
    """
    Detect diagram type from question text using keyword matching.

    Args:
        question_text: The question text to analyze

    Returns:
        Detected diagram type (defaults to "anatomy")
    """
    question_lower = question_text.lower()

    # Score each diagram type based on keyword matches
    scores = {}
    for dtype, config in DIAGRAM_TYPES.items():
        score = sum(1 for kw in config["keywords"] if kw in question_lower)
        if score > 0:
            scores[dtype] = score

    if scores:
        return max(scores, key=scores.get)

    return "anatomy"  # Default
