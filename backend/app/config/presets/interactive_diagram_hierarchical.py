"""
Label Diagram Hierarchical Preset

A production-ready pipeline preset for generating interactive hierarchical
label diagram games with:
- Retrieved reference image (used as input for generation)
- Generated clean diagram (DALL-E/Gemini uses reference + context)
- Gemini zone detection (on generated image)
- 3-stage scene generation
- Anthropic asset generation
- Hierarchical progressive reveal (frontend)

Pipeline Flow:
    input_enhancer
        -> domain_knowledge_retriever (extracts hierarchical_relationships)
        -> router
        -> game_planner (detects hierarchy, sets recommended_mode)
        -> scene_stage1_structure
        -> scene_stage2_assets
        -> scene_stage3_interactions
        -> diagram_image_retriever (retrieves REFERENCE image from web)
        -> diagram_image_generator (NEW - generates clean diagram)
        -> gemini_zone_detector (detects zones + creates zoneGroups)
        -> blueprint_generator (includes zoneGroups)
        -> blueprint_validator
        -> asset_planner
        -> asset_generator_orchestrator
        -> diagram_spec_generator
        -> diagram_svg_generator
        -> END
"""

PRESET_CONFIG = {
    "name": "interactive_diagram_hierarchical",
    "description": "Hierarchical label diagram with AI-generated clean images",
    "version": "1.0.0",

    # Feature flags for this preset
    "features": {
        # Image pipeline features
        "use_image_retrieval": True,        # Retrieve reference images from web
        "use_diagram_generation": True,     # Generate clean diagrams (vs using retrieved)
        "use_gemini_zone_detection": True,  # Use Gemini for zone detection

        # Diagram generator configuration
        "diagram_generator": "gemini",      # "openai" (DALL-E 3) or "gemini" (Imagen)
        "diagram_style": "clean_educational",  # Style directive for generation

        # Scene generation features
        "use_scene_stages": True,           # Use 3-stage hierarchical scene generation
        "use_hierarchical_mode": True,      # Enable hierarchical game mode

        # Asset generation
        "use_anthropic_assets": True,       # Use Claude for asset descriptions

        # Zone detection configuration
        "zone_detection_method": "gemini_vlm",  # "gemini_vlm" or "sam3"
        "use_polygon_zones": True,              # Enable precise polygon zone boundaries
        "intelligent_zone_types": True,         # Agent decides point vs area per-label
        "unlimited_hierarchy_depth": True,      # Enable unlimited hierarchy depth (10 levels)

        # Validation
        "strict_validation": True,          # Enforce strict blueprint validation
    },

    # Agents that should be SKIPPED in this preset
    # These are replaced by the new diagram generation pipeline
    "disabled_agents": [
        "image_label_classifier",        # Not needed - we generate clean images
        "image_label_remover",           # Not needed - we generate clean images
        "qwen_annotation_detector",      # Not needed - no annotations to detect
        "qwen_sam_zone_detector",        # Replaced by gemini_zone_detector
        "direct_structure_locator",      # Not needed - using Gemini detection
        "sam3_prompt_generator",         # Not needed
        "diagram_image_segmenter",       # Not needed
        "diagram_zone_labeler",          # Replaced by gemini_zone_detector
    ],

    # Model assignments per agent (Gemini-only)
    "agent_models": {
        # Input processing
        "input_enhancer": "gemini-2.5-flash",
        "domain_knowledge_retriever": "gemini-2.5-flash",
        "router": "gemini-2.5-flash",

        # Planning
        "game_planner": "gemini-2.5-pro",

        # Scene generation (3-stage)
        "scene_stage1_structure": "gemini-2.5-pro",
        "scene_stage2_assets": "gemini-2.5-pro",
        "scene_stage3_interactions": "gemini-2.5-pro",

        # Image pipeline
        "diagram_image_retriever": "gemini-2.5-flash",  # Image search
        "diagram_image_generator": "gemini-imagen",     # Image generation (Nano Banana)
        "gemini_zone_detector": "gemini-2.5-flash",     # Zone detection

        # Blueprint generation
        "blueprint_generator": "gemini-2.5-pro",
        "blueprint_validator": "gemini-2.5-flash",

        # Asset generation
        "asset_planner": "gemini-2.5-flash",
        "asset_generator_orchestrator": "gemini-2.5-pro",

        # Diagram spec/SVG
        "diagram_spec_generator": "gemini-2.5-pro",
        "diagram_svg_generator": "gemini-2.5-flash",
    },

    # Temperature settings per agent
    "agent_temperatures": {
        "input_enhancer": 0.3,
        "domain_knowledge_retriever": 0.2,
        "router": 0.1,
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
        "scene_stage1_structure": 4096,
        "scene_stage2_assets": 4096,
        "scene_stage3_interactions": 4096,
        "blueprint_generator": 12288,
        "diagram_spec_generator": 6144,
    },

    # Pipeline routing configuration
    "routing": {
        # After diagram_image_retriever, go to generator (not classifier)
        "diagram_image_retriever_next": "diagram_image_generator",

        # After generator, go to Gemini zone detection
        "diagram_image_generator_next": "gemini_zone_detector",

        # After zone detection, go to blueprint
        "gemini_zone_detector_next": "blueprint_generator",
    },

    # Environment variable requirements (Gemini-only)
    "required_env_vars": [
        "GOOGLE_API_KEY",       # For all Gemini models (LLM + Imagen + Zone detection)
        "SERPER_API_KEY",       # For image search
    ],

    # Optional environment variables
    "optional_env_vars": [
        "ANTHROPIC_API_KEY",    # For Claude models (if switching providers)
        "OPENAI_API_KEY",       # For DALL-E 3 (if switching providers)
        "GROQ_API_KEY",         # For fast LLM calls (if switching providers)
    ],
}
