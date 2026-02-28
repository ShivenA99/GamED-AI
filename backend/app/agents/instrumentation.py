"""
Pipeline Instrumentation for Observability

Provides wrappers and utilities to track agent execution for the
observability dashboard:
- Stage execution tracking (timing, status, errors)
- LLM metrics (tokens, latency, cost)
- State snapshot capture

Usage:
    # When creating a pipeline run
    run_id = create_pipeline_run(process_id, topology)
    state["_run_id"] = run_id

    # The instrumented agents will automatically track execution
"""
import traceback
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Awaitable
from functools import wraps
from collections import defaultdict
import json
import logging

from sqlalchemy.orm import Session

from app.db.models import PipelineRun, StageExecution, ExecutionLog, Process
from app.db.database import SessionLocal

logger = logging.getLogger("gamed_ai.agents.instrumentation")


# =============================================================================
# Centralized Agent Metadata Registry
# =============================================================================
# This is the SINGLE SOURCE OF TRUTH for agent metadata.
# The frontend fetches this via /api/observability/graph/structure endpoint.
# Categories: input, routing, image, generation, validation, output, react

AGENT_METADATA_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ==========================================================================
    # INPUT PROCESSING AGENTS
    # ==========================================================================
    "input_enhancer": {
        "name": "Input Enhancer",
        "description": "Analyzes question to extract Bloom's level, subject, and pedagogical context",
        "category": "input",
        "toolOrModel": "LLM (configurable)",
        "icon": "📝"
    },
    "domain_knowledge_retriever": {
        "name": "Domain Knowledge",
        "description": "Retrieves canonical labels and domain terms via web search",
        "category": "input",
        "toolOrModel": "Serper API + LLM",
        "icon": "🔍"
    },
    "diagram_type_classifier": {
        "name": "Diagram Type Classifier",
        "description": "Classifies diagram type (anatomy, flowchart, map, timeline) for optimal processing",
        "category": "input",
        "toolOrModel": "Gemini 2.0 Flash Lite",
        "icon": "📊"
    },
    "diagram_analyzer": {
        "name": "Diagram Analyzer",
        "description": "Reasoning-based content analysis - determines optimal visualization strategy",
        "category": "input",
        "toolOrModel": "LLM (configurable)",
        "icon": "🔬"
    },

    # ==========================================================================
    # ROUTING AGENTS
    # ==========================================================================
    "router": {
        "name": "Template Router",
        "description": "Selects optimal game template based on question type and pedagogy",
        "category": "routing",
        "toolOrModel": "LLM (configurable)",
        "icon": "🔀"
    },
    "phet_simulation_selector": {
        "name": "PhET Simulation Selector",
        "description": "Selects appropriate PhET simulation for the topic",
        "category": "routing",
        "toolOrModel": "LLM + PhET API",
        "icon": "🔬"
    },

    # ==========================================================================
    # IMAGE PROCESSING AGENTS
    # ==========================================================================
    "diagram_image_retriever": {
        "name": "Diagram Retriever",
        "description": "Searches for educational diagram images matching the topic",
        "category": "image",
        "toolOrModel": "Serper Image API",
        "icon": "🖼️"
    },
    "image_label_classifier": {
        "name": "Label Classifier",
        "description": "Classifies if diagram is labeled or unlabeled using EasyOCR + VLM",
        "category": "image",
        "toolOrModel": "EasyOCR + Qwen VL",
        "icon": "🏷️"
    },
    "image_label_remover": {
        "name": "Label Remover",
        "description": "Removes existing text labels from diagram using inpainting",
        "category": "image",
        "toolOrModel": "Inpainting Service",
        "icon": "🧹"
    },
    "qwen_annotation_detector": {
        "name": "Annotation Detector",
        "description": "Detects text labels and leader lines using EasyOCR + geometric inference",
        "category": "image",
        "toolOrModel": "EasyOCR + Geometric",
        "icon": "🔍"
    },
    "qwen_label_remover": {
        "name": "Qwen Label Remover",
        "description": "Removes labels using Qwen VL-guided inpainting",
        "category": "image",
        "toolOrModel": "Qwen VL + Inpainting",
        "icon": "🧹"
    },
    "qwen_sam_zone_detector": {
        "name": "Zone Detector",
        "description": "Creates zones from leader line endpoints with optional SAM3 refinement",
        "category": "image",
        "toolOrModel": "Leader Lines + SAM3",
        "icon": "🎯"
    },
    "qwen_zone_detector": {
        "name": "Qwen Zone Detector",
        "description": "Detects zones using Qwen VL vision-language model",
        "category": "image",
        "toolOrModel": "Qwen VL",
        "icon": "🔍"
    },
    "direct_structure_locator": {
        "name": "Structure Locator",
        "description": "Directly locates structures in unlabeled diagrams using VLM",
        "category": "image",
        "toolOrModel": "Qwen VL + SAM3",
        "icon": "📍"
    },
    "diagram_image_generator": {
        "name": "Diagram Generator",
        "description": "Generates clean educational diagrams using Gemini Imagen",
        "category": "image",
        "toolOrModel": "Gemini Imagen",
        "icon": "🎨"
    },
    "gemini_zone_detector": {
        "name": "Gemini + SAM 3 Zone Detector",
        "description": "Combines Gemini semantic understanding with SAM 3 pixel-precise segmentation for academically accurate polygon zone boundaries",
        "category": "image",
        "toolOrModel": "Gemini 2.5 Flash + SAM 3",
        "icon": "🎯"
    },
    "smart_zone_detector": {
        "name": "Smart Zone Detector",
        "description": "Intelligent zone detection with adaptive strategies",
        "category": "image",
        "toolOrModel": "Multi-model",
        "icon": "🧠"
    },
    "smart_inpainter": {
        "name": "Smart Inpainter",
        "description": "Intelligent inpainting with quality assessment",
        "category": "image",
        "toolOrModel": "Inpainting Service",
        "icon": "🖌️"
    },
    "combined_label_detector": {
        "name": "Combined Label Detector",
        "description": "Combines multiple OCR and VLM methods for robust label detection",
        "category": "image",
        "toolOrModel": "EasyOCR + Qwen VL",
        "icon": "🔍"
    },
    "diagram_image_segmenter": {
        "name": "Image Segmenter",
        "description": "Segments diagram into distinct zones using SAM3",
        "category": "image",
        "toolOrModel": "SAM3",
        "icon": "✂️"
    },
    "diagram_zone_labeler": {
        "name": "Zone Labeler",
        "description": "Labels each segmented zone using vision-language model",
        "category": "image",
        "toolOrModel": "VLM (LLaVA/Ollama)",
        "icon": "🏷️"
    },
    "sam3_prompt_generator": {
        "name": "SAM3 Prompt Gen",
        "description": "Generates point/box prompts for SAM3 segmentation model",
        "category": "image",
        "toolOrModel": "LLM (VLM capable)",
        "icon": "🎯"
    },
    "multi_scene_image_orchestrator": {
        "name": "Multi-Scene Image Orchestrator",
        "description": "Orchestrates per-scene image generation and zone detection for multi-scene games (Preset 2)",
        "category": "orchestrator",
        "toolOrModel": "Gemini Imagen + Vision",
        "icon": "🎬",
        "isOrchestrator": True
    },
    "multi_scene_orchestrator": {
        "name": "Multi-Scene Orchestrator",
        "description": "Loops 3-stage scene generation per-scene for content (structure, assets, interactions)",
        "category": "orchestrator",
        "toolOrModel": "Orchestration",
        "icon": "🎬",
        "isOrchestrator": True
    },
    "image_agent": {
        "name": "Image Agent",
        "description": "Dedicated image pipeline: retrieval, generation, and zone detection",
        "category": "image",
        "toolOrModel": "LLM + 3 Tools",
        "icon": "🖼️"
    },

    # ==========================================================================
    # GENERATION AGENTS
    # ==========================================================================
    "game_planner": {
        "name": "Game Planner",
        "description": "Creates game mechanics, learning objectives, task structure, accessibility config, and event tracking",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🎮"
    },
    "game_designer": {
        "name": "Game Designer",
        "description": "Unified unconstrained game designer - produces creative GameDesign with scenes, interactions, and pedagogical reasoning",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🎯"
    },
    "design_interpreter": {
        "name": "Design Interpreter",
        "description": "Maps unconstrained GameDesign to structured GamePlan with classified mechanics, scene_breakdown, and workflow assignments",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🔀"
    },
    "scene_generator": {
        "name": "Scene Generator",
        "description": "Generates narrative context, visual themes, and scene descriptions (legacy)",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🎨"
    },
    "scene_stage1_structure": {
        "name": "Scene Structure",
        "description": "Stage 1: Generates visual theme, layout type, and region definitions",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🏗️"
    },
    "scene_stage2_assets": {
        "name": "Scene Assets",
        "description": "Stage 2: Generates detailed asset specifications for each region",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🎨"
    },
    "scene_stage3_interactions": {
        "name": "Scene Interactions",
        "description": "Stage 3: Generates animations, behaviors, and state transitions",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🎬"
    },
    "scene_sequencer": {
        "name": "Scene Sequencer",
        "description": "Plans multi-scene games with zoom-in, depth-first, or linear progressions",
        "category": "generation",
        "toolOrModel": "Gemini 2.0 Flash",
        "icon": "🎬"
    },
    "story_generator": {
        "name": "Story Generator",
        "description": "Generates narrative story context (legacy)",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "📖"
    },
    "interaction_designer": {
        "name": "Interaction Designer",
        "description": "Designs custom interaction patterns based on Bloom's level, pedagogy, and content structure",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🎯"
    },
    "blueprint_generator": {
        "name": "Blueprint Generator",
        "description": "Creates complete game blueprint with zones, interactions, scoring, temporal constraints, accessibility specs, and event tracking",
        "category": "generation",
        "toolOrModel": "Gemini 3 Flash",
        "icon": "📐"
    },
    "diagram_spec_generator": {
        "name": "Diagram Spec Generator",
        "description": "Generates SVG specification from zones, blueprint, and assets",
        "category": "generation",
        "toolOrModel": "Gemini 3 Flash",
        "icon": "📋"
    },
    "asset_planner": {
        "name": "Asset Planner",
        "description": "Plans all assets needed from scene data and zones (runs BEFORE blueprint)",
        "category": "generation",
        "toolOrModel": "Rule-based",
        "icon": "📋"
    },
    "code_generator": {
        "name": "Code Generator",
        "description": "Generates React component code for stub templates",
        "category": "generation",
        "toolOrModel": "LLM (coding model)",
        "icon": "💻"
    },
    "research_agent": {
        "name": "Research Agent",
        "description": "Merged agent for question analysis and domain knowledge retrieval. Template is fixed to INTERACTIVE_DIAGRAM.",
        "category": "generation",
        "toolOrModel": "LLM + 2 Tools",
        "icon": "🔬"
    },

    # PhET Generation Agents
    "phet_game_planner": {
        "name": "PhET Game Planner",
        "description": "Plans game mechanics for PhET simulation integration",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🎮"
    },
    "phet_assessment_designer": {
        "name": "PhET Assessment Designer",
        "description": "Designs assessment tasks for PhET simulation",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "📝"
    },
    "phet_blueprint_generator": {
        "name": "PhET Blueprint Generator",
        "description": "Generates blueprint for PhET simulation integration",
        "category": "generation",
        "toolOrModel": "Gemini 3 Flash",
        "icon": "📐"
    },
    "phet_bridge_config_generator": {
        "name": "PhET Bridge Config Generator",
        "description": "Generates bridge configuration for PhET-React integration",
        "category": "generation",
        "toolOrModel": "LLM (configurable)",
        "icon": "🔧"
    },

    # ==========================================================================
    # VALIDATION AGENTS
    # ==========================================================================
    "blueprint_validator": {
        "name": "Blueprint Validator",
        "description": "Validates blueprint schema, semantics, and pedagogical alignment. Supports retry/escalate.",
        "category": "validation",
        "toolOrModel": "Gemini 2.5 Flash Lite",
        "icon": "✅"
    },
    "interaction_validator": {
        "name": "Interaction Validator",
        "description": "Validates interaction design for playability, learning alignment, and technical feasibility",
        "category": "validation",
        "toolOrModel": "Rule-based + Patterns",
        "icon": "✅"
    },
    "playability_validator": {
        "name": "Playability Validator",
        "description": "Validates game playability and educational alignment",
        "category": "validation",
        "toolOrModel": "Rule-based",
        "icon": "✅"
    },
    "asset_validator": {
        "name": "Asset Validator",
        "description": "Validates all generated assets exist, have correct formats, and meet requirements",
        "category": "validation",
        "toolOrModel": "Gemini 2.5 Flash Lite",
        "icon": "✅"
    },
    "diagram_spec_validator": {
        "name": "Diagram Spec Validator",
        "description": "Validates diagram specification structure",
        "category": "validation",
        "toolOrModel": "Rule-based",
        "icon": "✅"
    },
    "code_verifier": {
        "name": "Code Verifier",
        "description": "Verifies generated code with TypeScript and ESLint",
        "category": "validation",
        "toolOrModel": "Docker Sandbox",
        "icon": "🔍"
    },
    "human_review": {
        "name": "Human Review",
        "description": "Checkpoint for manual review and approval",
        "category": "validation",
        "toolOrModel": "Manual Review",
        "icon": "👤"
    },
    "evaluation": {
        "name": "Evaluation",
        "description": "Evaluates overall pipeline quality and metrics",
        "category": "validation",
        "toolOrModel": "Rule-based + LLM",
        "icon": "📊"
    },
    "phet_blueprint_validator": {
        "name": "PhET Blueprint Validator",
        "description": "Validates PhET simulation blueprint",
        "category": "validation",
        "toolOrModel": "Rule-based + LLM",
        "icon": "✅"
    },

    # ==========================================================================
    # OUTPUT AGENTS
    # ==========================================================================
    "diagram_svg_generator": {
        "name": "SVG Generator",
        "description": "Renders final SVG diagram with complex SVG generation",
        "category": "output",
        "toolOrModel": "Gemini 3 Flash",
        "icon": "🎨"
    },
    "asset_generator_orchestrator": {
        "name": "Asset Generator Orchestrator",
        "description": "Executes workflows in dependency order based on workflow_execution_plan",
        "category": "orchestration",
        "toolOrModel": "Workflow executor",
        "icon": "🎭",
        "isOrchestrator": True
    },
    "labeling_diagram_workflow": {
        "name": "Labeling Diagram Workflow",
        "description": "Retrieves diagram image and detects zones for labeling mechanics",
        "category": "workflow",
        "toolOrModel": "Serper + Gemini Vision",
        "icon": "🖼️"
    },
    "trace_path_workflow": {
        "name": "Trace Path Workflow",
        "description": "Generates trace paths from zones and domain knowledge",
        "category": "workflow",
        "toolOrModel": "Zone mapping",
        "icon": "🛤️"
    },
    "sequence_items_workflow": {
        "name": "Sequence Items Workflow",
        "description": "Extracts sequence items from domain knowledge",
        "category": "workflow",
        "toolOrModel": "Domain knowledge",
        "icon": "📋"
    },
    "output_renderer": {
        "name": "Output Renderer",
        "description": "Final rendering: diagram spec generation and SVG output. Split from blueprint_generator.",
        "category": "output",
        "toolOrModel": "LLM + 2 Tools",
        "icon": "🎨"
    },

    # ==========================================================================
    # REACT / MULTI-STEP REASONING AGENTS
    # ==========================================================================
    "research_image_agent": {
        "name": "Research & Image",
        "description": "Multi-step reasoning for question analysis, domain knowledge, and image acquisition. Template fixed to INTERACTIVE_DIAGRAM.",
        "category": "react",
        "toolOrModel": "ReAct + 5 Tools",
        "icon": "🔬"
    },
    "blueprint_agent": {
        "name": "Blueprint Agent",
        "description": "Focused blueprint creation with validation and auto-fix. Reduced tool count for quality.",
        "category": "react",
        "toolOrModel": "ReAct + 3 Tools",
        "icon": "📐"
    },
    "asset_render_agent": {
        "name": "Asset & Render",
        "description": "Asset generation, diagram spec, and SVG rendering. Split from blueprint_asset_agent.",
        "category": "react",
        "toolOrModel": "ReAct + 4 Tools",
        "icon": "🎨"
    },
    "research_routing_agent": {
        "name": "Research & Routing (Legacy)",
        "description": "LEGACY: Multi-step reasoning agent. Use research_image_agent instead.",
        "category": "react",
        "toolOrModel": "ReAct + 6 Tools",
        "icon": "🔬"
    },
    "game_design_agent": {
        "name": "Game Design Agent",
        "description": "Multi-step reasoning agent for game mechanics planning, scene structure, asset population, and interaction design.",
        "category": "react",
        "toolOrModel": "ReAct + 5 Tools",
        "icon": "🎮"
    },
    "blueprint_asset_agent": {
        "name": "Blueprint & Assets (Legacy)",
        "description": "LEGACY: 10 tools causes 20-40% quality degradation. Use blueprint_agent + asset_render_agent instead.",
        "category": "react",
        "toolOrModel": "ReAct + 10 Tools",
        "icon": "📐"
    },

    # ==========================================================================
    # HAD (HIERARCHICAL AGENTIC DAG) AGENTS
    # ==========================================================================
    "zone_planner": {
        "name": "Zone Planner",
        "description": "HAD v3 Vision Cluster: Gemini vision for polygon zone detection with accessibility specs. Supports multi-scene detection.",
        "category": "image",
        "toolOrModel": "Gemini 2.5 Flash (Vision)",
        "icon": "🔬"
    },
    "game_orchestrator": {
        "name": "Game Orchestrator",
        "description": "HAD Legacy: Sequential design with accessibility, event tracking, and undo/redo config. Replaced by game_designer in HAD v3.",
        "category": "generation",
        "toolOrModel": "Orchestrator + 4 Tools",
        "icon": "🎮"
    },
    "output_orchestrator": {
        "name": "Output Orchestrator",
        "description": "HAD Output Cluster: Blueprint generation with validation retry loop (max 3), diagram spec, and SVG rendering.",
        "category": "output",
        "toolOrModel": "Orchestrator + Validation",
        "icon": "📐"
    },

    # ==========================================================================
    # DECISION/ROUTING NODES (Passthrough nodes for conditional routing)
    # ==========================================================================
    "check_routing_confidence_node": {
        "name": "Check Routing Confidence",
        "description": "Evaluates router confidence score. Routes to game planner if confidence >= 0.7, otherwise escalates to human review.",
        "category": "decision",
        "toolOrModel": "Rule-based (confidence >= 0.7)",
        "icon": "🔀",
        "isDecisionNode": True,
        "outcomes": ["high", "low"]
    },
    "check_agentic_design_node": {
        "name": "Check Agentic Design",
        "description": "Determines whether to use agentic game design flow (Preset 2) or standard game planning.",
        "category": "decision",
        "toolOrModel": "Preset Configuration",
        "icon": "🔀",
        "isDecisionNode": True,
        "outcomes": ["agentic", "standard"]
    },
    "check_template_status": {
        "name": "Check Template Status",
        "description": "Determines if selected template is production-ready or requires code generation.",
        "category": "decision",
        "toolOrModel": "Template Registry",
        "icon": "🔀",
        "isDecisionNode": True,
        "outcomes": ["production", "stub"]
    },
    "check_post_blueprint_needs": {
        "name": "Check Post-Blueprint Needs",
        "description": "Analyzes state to determine post-processing requirements. Sets flags for asset pipeline and diagram spec routing.",
        "category": "decision",
        "toolOrModel": "State Analysis",
        "icon": "🔀",
        "isDecisionNode": True,
        "outcomes": ["run_assets", "skip_assets"]
    },
    "check_post_scene_needs": {
        "name": "Check Post-Scene Needs",
        "description": "Analyzes scene data to determine if asset pipeline should run before blueprint generation.",
        "category": "decision",
        "toolOrModel": "State Analysis",
        "icon": "🔀",
        "isDecisionNode": True,
        "outcomes": ["run_assets", "skip_assets"]
    },
    "check_multi_scene": {
        "name": "Check Multi-Scene",
        "description": "Determines if multi-scene orchestration is needed based on scene_breakdown and num_scenes.",
        "category": "decision",
        "toolOrModel": "State Analysis",
        "icon": "🔀",
        "isDecisionNode": True,
        "outcomes": ["multi_scene", "single_scene"]
    },
    "check_diagram_spec_route": {
        "name": "Check Diagram Spec Route",
        "description": "Determines if diagram spec generation is needed based on template type (INTERACTIVE_DIAGRAM, SORTING_GAME, etc.).",
        "category": "decision",
        "toolOrModel": "Template Analysis",
        "icon": "🔀",
        "isDecisionNode": True,
        "outcomes": ["run_diagram_spec", "skip_diagram_spec"]
    },
    "check_diagram_image": {
        "name": "Check Diagram Image",
        "description": "Determines if diagram image retrieval is needed for INTERACTIVE_DIAGRAM templates.",
        "category": "decision",
        "toolOrModel": "Template + Config",
        "icon": "🔀",
        "isDecisionNode": True,
        "outcomes": ["use_image", "skip_image"]
    },

    # ==========================================================================
    # V3 PIPELINE AGENTS
    # ==========================================================================
    "game_designer_v3": {
        "name": "Game Designer v3",
        "description": "ReAct agent that designs multi-scene multi-mechanic educational games using pedagogical tools",
        "category": "generation",
        "toolOrModel": "ReAct (LLM + Tools)",
        "icon": "🎮"
    },
    "design_validator": {
        "name": "Design Validator",
        "description": "Deterministic validation of GameDesignV3 — schema, labels, hierarchy, mechanics, transitions",
        "category": "validation",
        "toolOrModel": "Rule-based (no LLM)",
        "icon": "✓"
    },
    "asset_spec_builder": {
        "name": "Asset Spec Builder",
        "description": "Builds AssetManifest from GameDesignV3 + AssetGraph — deterministic spec generation for workers",
        "category": "generation",
        "toolOrModel": "Deterministic",
        "icon": "📋"
    },
    "asset_orchestrator_v3": {
        "name": "Asset Orchestrator v3",
        "description": "Dispatches asset generation workers (image search, zone detection, CSS, audio, paths) from AssetManifest",
        "category": "generation",
        "toolOrModel": "Worker Dispatch",
        "icon": "🏭",
        "isOrchestrator": True,
    },
    "blueprint_assembler_v3": {
        "name": "Blueprint Assembler v3",
        "description": "Deterministic assembly of InteractiveDiagramBlueprint from GameDesignV3 + generated assets",
        "category": "output",
        "toolOrModel": "Deterministic",
        "icon": "🧩"
    },

    # ==========================================================================
    # V4 PIPELINE AGENTS
    # ==========================================================================
    "v4_input_analyzer": {
        "name": "Input Analyzer",
        "description": "Extract pedagogical context from question (Bloom's, difficulty, concepts)",
        "category": "context",
        "toolOrModel": "Gemini 2.5 Flash",
        "icon": "📝"
    },
    "v4_dk_retriever": {
        "name": "Domain Knowledge Retriever",
        "description": "Gather domain knowledge: canonical labels, descriptions, sequences, comparisons",
        "category": "context",
        "toolOrModel": "Gemini 2.5 Flash + Serper",
        "icon": "🔬"
    },
    "v4_phase0_merge": {
        "name": "Context Merge",
        "description": "Synchronize parallel context gathering results",
        "category": "context",
        "toolOrModel": "Deterministic",
        "icon": "🔀"
    },
    "v4_game_designer": {
        "name": "Game Designer",
        "description": "Design game plan: scenes, mechanics, zone labels, content briefs",
        "category": "design",
        "toolOrModel": "Gemini 2.5 Pro",
        "icon": "🎮"
    },
    "v4_game_plan_validator": {
        "name": "Game Plan Validator",
        "description": "Validate game plan structure, label integrity, score arithmetic",
        "category": "validation",
        "toolOrModel": "Deterministic",
        "icon": "✅"
    },
    "v4_content_builder": {
        "name": "Content Builder",
        "description": "Generate mechanic content and interaction designs for all scenes",
        "category": "generation",
        "toolOrModel": "Gemini 2.5 Pro/Flash (per mechanic)",
        "icon": "📦"
    },
    "v4_asset_worker": {
        "name": "Asset Worker",
        "description": "Search diagram image, detect zones via Gemini vision",
        "category": "assets",
        "toolOrModel": "Gemini 2.5 Flash + Image Search",
        "icon": "🖼️"
    },
    "v4_asset_merge": {
        "name": "Asset Merge",
        "description": "Deduplicate asset results from parallel workers",
        "category": "assets",
        "toolOrModel": "Deterministic",
        "icon": "🔀"
    },
    "v4_assembler": {
        "name": "Blueprint Assembler",
        "description": "Assemble final InteractiveDiagramBlueprint from all upstream outputs",
        "category": "output",
        "toolOrModel": "Deterministic",
        "icon": "🧩"
    },

    # V4 Algorithm Pipeline agents
    "v4a_dk_retriever": {
        "name": "Algorithm DK Retriever",
        "description": "Gather algorithm-specific domain knowledge: pseudocode, complexity, common bugs, examples",
        "category": "input",
        "toolOrModel": "Gemini 2.5 Flash + Serper",
        "icon": "🔬"
    },
    "v4a_game_concept_designer": {
        "name": "Algorithm Concept Designer",
        "description": "Design multi-scene algorithm game with Bloom's-aligned progression across 5 game types",
        "category": "design",
        "toolOrModel": "Gemini 2.5 Pro",
        "icon": "🎮"
    },
    "v4a_concept_validator": {
        "name": "Algorithm Concept Validator",
        "description": "Validate algorithm game concept: scene count, game types, difficulty progression",
        "category": "validation",
        "toolOrModel": "Deterministic",
        "icon": "✅"
    },
    "v4a_graph_builder": {
        "name": "Algorithm Graph Builder",
        "description": "Assign scene IDs, compute max scores, determine asset needs, build transitions",
        "category": "design",
        "toolOrModel": "Deterministic",
        "icon": "🏗️"
    },
    "v4a_plan_validator": {
        "name": "Algorithm Plan Validator",
        "description": "Validate algorithm game plan: unique IDs, valid game types, score consistency",
        "category": "validation",
        "toolOrModel": "Deterministic",
        "icon": "✅"
    },
    "v4a_scene_content_gen": {
        "name": "Scene Content Generator",
        "description": "Generate per-scene game content (state tracer steps, bug rounds, Parsons blocks, etc.)",
        "category": "generation",
        "toolOrModel": "Gemini 2.5 Pro",
        "icon": "📦"
    },
    "v4a_content_merge": {
        "name": "Content Merge",
        "description": "Merge parallel scene content results, deduplicate by scene_id",
        "category": "routing",
        "toolOrModel": "Deterministic",
        "icon": "📥"
    },
    "v4a_asset_worker": {
        "name": "Algorithm Asset Worker",
        "description": "Generate visual assets per scene via image retrieval or Nanobanana AI",
        "category": "assets",
        "toolOrModel": "Nanobanana + Image Search",
        "icon": "🖼️"
    },
    "v4a_asset_merge": {
        "name": "Asset Merge",
        "description": "Merge parallel scene asset results, deduplicate by scene_id",
        "category": "routing",
        "toolOrModel": "Deterministic",
        "icon": "🔀"
    },
    "v4a_blueprint_assembler": {
        "name": "Algorithm Blueprint Assembler",
        "description": "Assemble AlgorithmGameBlueprint from game plan, scene contents, and assets",
        "category": "output",
        "toolOrModel": "Deterministic",
        "icon": "🧩"
    },

    # V4 Cascade agents (fan-out pipeline)
    "v4_game_concept_designer": {
        "name": "Game Concept Designer",
        "description": "Design game concept with scenes, narrative theme, and mechanic assignments",
        "category": "design",
        "toolOrModel": "Gemini 2.5 Pro",
        "icon": "🎯"
    },
    "v4_concept_validator": {
        "name": "Concept Validator",
        "description": "Validate game concept structure, scene completeness, mechanic feasibility",
        "category": "validation",
        "toolOrModel": "Deterministic",
        "icon": "✅"
    },
    "v4_scene_design_send": {
        "name": "Scene Design Dispatch",
        "description": "Fan-out router dispatching parallel scene design tasks",
        "category": "routing",
        "toolOrModel": "Deterministic",
        "icon": "📤"
    },
    "v4_scene_designer": {
        "name": "Scene Designer",
        "description": "Design creative layout, visual style, and zone placement for a scene",
        "category": "design",
        "toolOrModel": "Gemini 2.5 Pro",
        "icon": "🎨"
    },
    "v4_scene_design_merge": {
        "name": "Scene Design Merge",
        "description": "Merge and validate parallel scene design results",
        "category": "merge",
        "toolOrModel": "Deterministic",
        "icon": "🔀"
    },
    "v4_graph_builder": {
        "name": "Graph Builder",
        "description": "Build game plan graph from concept and scene designs",
        "category": "design",
        "toolOrModel": "Gemini 2.5 Pro",
        "icon": "🏗️"
    },
    "v4_content_dispatch": {
        "name": "Content Dispatch",
        "description": "Fan-out router dispatching parallel content generation tasks",
        "category": "routing",
        "toolOrModel": "Deterministic",
        "icon": "📤"
    },
    "v4_content_generator": {
        "name": "Content Generator",
        "description": "Generate mechanic-specific content (questions, options, feedback)",
        "category": "generation",
        "toolOrModel": "Gemini 2.5 Flash",
        "icon": "📝"
    },
    "v4_content_merge": {
        "name": "Content Merge",
        "description": "Merge parallel content generation results",
        "category": "merge",
        "toolOrModel": "Deterministic",
        "icon": "🔀"
    },
    "v4_item_asset_worker": {
        "name": "Item Asset Worker",
        "description": "Enrich content items with image URLs from image_description fields",
        "category": "asset",
        "toolOrModel": "Serper Image API",
        "icon": "🖼️"
    },
    "v4_interaction_designer": {
        "name": "Interaction Designer",
        "description": "Design interaction patterns, UX flows, and feedback for scenes",
        "category": "design",
        "toolOrModel": "Gemini 2.5 Flash",
        "icon": "🖱️"
    },
    "v4_interaction_merge": {
        "name": "Interaction Merge",
        "description": "Merge parallel interaction design results",
        "category": "merge",
        "toolOrModel": "Deterministic",
        "icon": "🔀"
    },
}


def get_agent_metadata(agent_name: str) -> Dict[str, Any]:
    """
    Get metadata for an agent from the registry.

    Returns a default metadata dict if the agent is not found.
    """
    if agent_name in AGENT_METADATA_REGISTRY:
        return AGENT_METADATA_REGISTRY[agent_name]

    # Return default metadata for unknown agents
    return {
        "name": agent_name.replace("_", " ").title(),
        "description": f"Agent: {agent_name}",
        "category": "generation",
        "toolOrModel": "Unknown",
        "icon": "🔧"
    }


# =============================================================================
# Live Step Event Queue for Real-Time Streaming
# =============================================================================

# In-memory store for live step events per run_id
# Structure: {run_id: [LiveStepEvent, ...]}
_live_step_queues: Dict[str, List[Dict]] = defaultdict(list)

# Locks for thread-safe access
_queue_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def emit_live_step(
    run_id: str,
    stage_name: str,
    step_type: str,
    content: str,
    tool: Optional[str] = None
) -> None:
    """
    Emit a live step event for real-time streaming.

    This is the synchronous version that can be called from anywhere.
    Events are stored in memory and picked up by the SSE stream.

    Args:
        run_id: Pipeline run ID
        stage_name: Name of the agent/stage emitting the step
        step_type: One of 'thought', 'action', 'observation', 'decision'
        content: The step content
        tool: Optional tool name for action steps
    """
    step = {
        "type": step_type,
        "content": content,
        "tool": tool,
        "timestamp": datetime.utcnow().isoformat()
    }
    _live_step_queues[run_id].append({
        "stage_name": stage_name,
        "step": step
    })
    logger.debug(f"[LiveStep] {run_id}/{stage_name}: {step_type} - {content[:100]}...")


def get_live_steps(run_id: str, from_index: int = 0) -> List[Dict]:
    """
    Get live steps for a run, optionally starting from an index.

    Used by SSE stream to get new steps since last poll.

    Args:
        run_id: Pipeline run ID
        from_index: Starting index for slicing

    Returns:
        List of step events since from_index
    """
    return _live_step_queues.get(run_id, [])[from_index:]


def clear_live_steps(run_id: str) -> None:
    """Clear live steps for a completed run to free memory."""
    if run_id in _live_step_queues:
        del _live_step_queues[run_id]
    if run_id in _queue_locks:
        del _queue_locks[run_id]


def create_step_callback(run_id: str, stage_name: str, stage_id: Optional[str] = None) -> Callable[[Any], Awaitable[None]]:
    """
    Create a step callback for use with LLMService.generate_with_tools().

    This callback emits live steps to the queue AND persists them as
    execution logs in the database for the Logs tab.

    Args:
        run_id: Pipeline run ID
        stage_name: Name of the agent/stage
        stage_id: Optional stage execution ID for DB logging

    Returns:
        Async callback function compatible with StepCallback type
    """
    async def step_callback(event) -> None:
        # Emit to in-memory queue for SSE streaming
        emit_live_step(
            run_id=run_id,
            stage_name=stage_name,
            step_type=event.type,
            content=event.content,
            tool=getattr(event, 'tool', None)
        )
        # Also persist to DB for the Logs tab (non-blocking, non-fatal)
        try:
            tool_name = getattr(event, 'tool', None)
            level = "info"
            if event.type == "thought":
                msg = f"[THOUGHT] {event.content[:500]}"
            elif event.type == "action":
                msg = f"[ACTION] {tool_name or 'unknown'}: {event.content[:400]}"
            elif event.type == "observation":
                msg = f"[OBSERVATION] {event.content[:500]}"
            elif event.type == "decision":
                msg = f"[DECISION] {event.content[:500]}"
            else:
                msg = f"[{event.type.upper()}] {event.content[:500]}"
            add_execution_log(
                run_id=run_id,
                stage_execution_id=stage_id,
                message=msg,
                level=level,
                metadata={"tool": tool_name} if tool_name else None
            )
        except Exception:
            pass  # Non-fatal: don't break streaming if DB write fails
    return step_callback


# Cost per 1M tokens (approximate, updated Jan 2026)
MODEL_COSTS = {
    # OpenAI
    "gpt-4-turbo-preview": {"input": 10.0, "output": 30.0},
    "gpt-4.5-turbo": {"input": 8.0, "output": 24.0},
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-4o-2024-11": {"input": 5.0, "output": 15.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},

    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},

    # Google Gemini (Jan 2026 pricing)
    "gemini-3-flash": {"input": 0.50, "output": 3.00},
    "gemini-3-flash-preview": {"input": 0.50, "output": 3.00},
    "gemini-3-pro": {"input": 2.00, "output": 12.00},
    "gemini-3-pro-preview": {"input": 2.00, "output": 12.00},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},

    # Groq (free tier, but track for reference)
    "llama-3.3-70b-versatile": {"input": 0.0, "output": 0.0},
    "llama-3.1-70b-versatile": {"input": 0.0, "output": 0.0},
    "llama-3.1-8b-instant": {"input": 0.0, "output": 0.0},
    "mixtral-8x7b-32768": {"input": 0.0, "output": 0.0},

    # DeepSeek models
    "deepseek-coder-v2": {"input": 0.14, "output": 0.28},
    "deepseek-chat": {"input": 0.14, "output": 0.28},

    # Local models (free - Ollama)
    "llama3.2:latest": {"input": 0.0, "output": 0.0},
    "llama3.2": {"input": 0.0, "output": 0.0},
    "llama3.2:3b": {"input": 0.0, "output": 0.0},
    "llama3.1:8b": {"input": 0.0, "output": 0.0},
    "llava:latest": {"input": 0.0, "output": 0.0},
    "qwen2.5:7b": {"input": 0.0, "output": 0.0},
    "qwen2.5-vl:7b": {"input": 0.0, "output": 0.0},
    "qwen2.5-vl:32b": {"input": 0.0, "output": 0.0},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for LLM usage."""
    model_lower = model.lower()
    costs = MODEL_COSTS.get(model_lower, {"input": 0.0, "output": 0.0})
    return (input_tokens / 1_000_000 * costs["input"]) + (output_tokens / 1_000_000 * costs["output"])


def create_pipeline_run(
    process_id: str,
    topology: str,
    config_snapshot: Optional[Dict] = None,
    db: Optional[Session] = None
) -> str:
    """
    Create a new pipeline run record for observability tracking.

    Args:
        process_id: Process ID this run belongs to
        topology: Topology identifier (T0, T1, etc.)
        config_snapshot: Optional configuration snapshot
        db: Optional database session

    Returns:
        run_id: The new pipeline run's ID
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # Get next run number for this process
        existing_runs = db.query(PipelineRun).filter(
            PipelineRun.process_id == process_id
        ).count()

        run = PipelineRun(
            process_id=process_id,
            run_number=existing_runs + 1,
            topology=topology,
            status="running",
            started_at=datetime.utcnow(),
            config_snapshot=config_snapshot
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        logger.info(f"Created pipeline run {run.id} for process {process_id} (topology: {topology})")
        return run.id

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create pipeline run: {e}")
        raise
    finally:
        if should_close:
            db.close()


def update_pipeline_run_status(
    run_id: str,
    status: str,
    error_message: Optional[str] = None,
    error_traceback: Optional[str] = None,
    final_state_summary: Optional[Dict] = None,
    db: Optional[Session] = None
):
    """Update pipeline run status and completion info."""
    from sqlalchemy import func

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run:
            logger.warning(f"Run {run_id} not found")
            return

        run.status = status
        run.finished_at = datetime.utcnow()
        if run.started_at:
            run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

        if error_message:
            run.error_message = error_message
        if error_traceback:
            run.error_traceback = error_traceback
        if final_state_summary:
            run.final_state_summary = final_state_summary

        # Roll up costs and tokens from stage executions when run completes
        if status in ("success", "completed"):
            cost_sum = db.query(func.sum(StageExecution.estimated_cost_usd))\
                .filter(StageExecution.run_id == run_id).scalar()
            token_sum = db.query(func.sum(StageExecution.total_tokens))\
                .filter(StageExecution.run_id == run_id).scalar()
            llm_call_count = db.query(func.count(StageExecution.id))\
                .filter(StageExecution.run_id == run_id)\
                .filter(StageExecution.model_id.isnot(None)).scalar()

            run.total_cost_usd = cost_sum or 0.0
            run.total_tokens = token_sum or 0
            run.total_llm_calls = llm_call_count or 0

            # Also update the parent Process if exists
            if run.process_id:
                process = db.query(Process).filter(Process.id == run.process_id).first()
                if process:
                    process.total_cost_usd = (process.total_cost_usd or 0.0) + (cost_sum or 0.0)
                    process.total_tokens = (process.total_tokens or 0) + (token_sum or 0)
                    process.total_llm_calls = (process.total_llm_calls or 0) + (llm_call_count or 0)

            logger.info(
                f"Run {run_id} cost rollup: ${cost_sum or 0.0:.4f}, "
                f"{token_sum or 0} tokens, {llm_call_count or 0} LLM calls"
            )

        db.commit()
        logger.info(f"Updated run {run_id} status to {status}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update run status: {e}")
    finally:
        if should_close:
            db.close()


def track_stage_start(
    run_id: str,
    stage_name: str,
    stage_order: int,
    input_snapshot: Optional[Dict] = None,
    db: Optional[Session] = None
) -> str:
    """
    Create a StageExecution record when a stage starts.

    Args:
        run_id: Pipeline run ID
        stage_name: Name of the agent/stage
        stage_order: Execution order (1-indexed)
        input_snapshot: Relevant input state (truncated)
        db: Optional database session

    Returns:
        stage_id: The new stage execution's ID
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        stage = StageExecution(
            run_id=run_id,
            stage_name=stage_name,
            stage_order=stage_order,
            status="running",
            started_at=datetime.utcnow(),
            input_snapshot=_truncate_snapshot(input_snapshot) if input_snapshot else None
        )
        db.add(stage)
        db.commit()
        db.refresh(stage)

        logger.debug(f"Stage {stage_name} started (order={stage_order})")
        return stage.id

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to track stage start: {e}")
        raise
    finally:
        if should_close:
            db.close()


def track_stage_complete(
    stage_id: str,
    output_snapshot: Optional[Dict] = None,
    model_id: Optional[str] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    latency_ms: Optional[int] = None,
    validation_passed: Optional[bool] = None,
    validation_score: Optional[float] = None,
    validation_errors: Optional[List] = None,
    used_fallback: bool = False,
    fallback_reason: Optional[str] = None,
    db: Optional[Session] = None
):
    """Mark a stage as successfully completed with metrics.

    If used_fallback is True, the status will be 'degraded' instead of 'success'.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        stage = db.query(StageExecution).filter(StageExecution.id == stage_id).first()
        if not stage:
            logger.warning(f"Stage {stage_id} not found")
            return

        # Use "degraded" status if a fallback was used
        stage.status = "degraded" if used_fallback else "success"
        stage.finished_at = datetime.utcnow()
        if stage.started_at:
            stage.duration_ms = int((stage.finished_at - stage.started_at).total_seconds() * 1000)

        if output_snapshot:
            # Add fallback info to output snapshot if applicable
            snapshot = _truncate_snapshot(output_snapshot)
            if used_fallback:
                snapshot["_used_fallback"] = True
                snapshot["_fallback_reason"] = fallback_reason or "Unknown fallback reason"
            stage.output_snapshot = snapshot
        elif used_fallback:
            stage.output_snapshot = {
                "_used_fallback": True,
                "_fallback_reason": fallback_reason or "Unknown fallback reason"
            }

        # LLM metrics
        if model_id:
            stage.model_id = model_id
        if prompt_tokens is not None:
            stage.prompt_tokens = prompt_tokens
        if completion_tokens is not None:
            stage.completion_tokens = completion_tokens
        if prompt_tokens and completion_tokens:
            stage.total_tokens = prompt_tokens + completion_tokens
            if model_id:
                stage.estimated_cost_usd = estimate_cost(model_id, prompt_tokens, completion_tokens)
        if latency_ms is not None:
            stage.latency_ms = latency_ms

        # Validation results
        if validation_passed is not None:
            stage.validation_passed = validation_passed
        if validation_score is not None:
            stage.validation_score = validation_score
        if validation_errors is not None:
            stage.validation_errors = validation_errors

        db.commit()
        logger.debug(f"Stage {stage.stage_name} completed successfully")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to track stage completion: {e}")
    finally:
        if should_close:
            db.close()


def save_stage_checkpoint(
    run_id: str,
    stage_name: str,
    checkpoint_id: str,
    db: Optional[Session] = None
):
    """
    Save LangGraph checkpoint_id to StageExecution after node completes.
    
    This links LangGraph checkpoints with our stage tracking, enabling
    true resume from specific stages during retry.
    
    Args:
        run_id: Pipeline run ID
        stage_name: Name of the stage (agent) that just completed
        checkpoint_id: LangGraph checkpoint_id from astream_events
        db: Optional database session
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        # Find the most recent stage execution for this run/stage
        # Stage should be in "success" or "degraded" status (just completed)
        stage = db.query(StageExecution).filter(
            StageExecution.run_id == run_id,
            StageExecution.stage_name == stage_name,
            StageExecution.status.in_(["success", "degraded", "running"])  # Include running in case it's being updated
        ).order_by(StageExecution.stage_order.desc()).first()
        
        if not stage:
            logger.warning(
                f"Could not find stage execution for run_id={run_id}, "
                f"stage_name={stage_name} to save checkpoint_id={checkpoint_id}"
            )
            return
        
        # Update stage with checkpoint_id
        stage.checkpoint_id = checkpoint_id
        db.commit()
        
        logger.debug(
            f"Saved checkpoint_id {checkpoint_id} for stage '{stage_name}' "
            f"in run {run_id} (stage_order={stage.stage_order})"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save checkpoint for stage {stage_name}: {e}")
        # Don't raise - checkpoint saving is non-critical
    finally:
        if should_close:
            db.close()


def track_stage_failed(
    stage_id: str,
    error_message: str,
    error_traceback: Optional[str] = None,
    db: Optional[Session] = None
):
    """Mark a stage as failed with error details."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        stage = db.query(StageExecution).filter(StageExecution.id == stage_id).first()
        if not stage:
            logger.warning(f"Stage {stage_id} not found")
            return

        stage.status = "failed"
        stage.finished_at = datetime.utcnow()
        if stage.started_at:
            stage.duration_ms = int((stage.finished_at - stage.started_at).total_seconds() * 1000)

        stage.error_message = error_message
        if error_traceback:
            stage.error_traceback = error_traceback

        db.commit()
        logger.debug(f"Stage {stage.stage_name} failed: {error_message[:100]}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to track stage failure: {e}")
    finally:
        if should_close:
            db.close()


def add_execution_log(
    run_id: str,
    message: str,
    level: str = "info",
    stage_execution_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
    db: Optional[Session] = None
):
    """Add an execution log entry."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        log = ExecutionLog(
            run_id=run_id,
            stage_execution_id=stage_execution_id,
            level=level,
            message=message,
            log_metadata=metadata
        )
        db.add(log)
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add execution log: {e}")
    finally:
        if should_close:
            db.close()


def _truncate_snapshot(data: Dict, max_size_kb: int = 200) -> Dict:
    """
    Truncate snapshot data to prevent database bloat.
    
    Truncates to max_size_kb (default 200KB) by calculating JSON size.
    Preserves top-level keys and truncates nested values if needed.
    Adds metadata about truncation.

    Args:
        data: Dictionary to truncate
        max_size_kb: Maximum size in KB (default 200KB)
        
    Returns:
        Truncated dictionary with metadata if truncated
    """
    if not isinstance(data, dict):
        return data

    # Calculate current size in bytes
    try:
        current_size_bytes = len(json.dumps(data, default=str))
        max_size_bytes = max_size_kb * 1024
        
        # If within limit, return as-is
        if current_size_bytes <= max_size_bytes:
            return data
        
        # Need to truncate - preserve structure but reduce values
        truncated = {}
        total_size = 0
        original_size_kb = current_size_bytes / 1024
        
        for key, value in data.items():
            # Estimate size of this key-value pair
            test_dict = {key: value}
            pair_size = len(json.dumps(test_dict, default=str))
            
            # If adding this would exceed limit, truncate the value
            if total_size + pair_size > max_size_bytes:
                if isinstance(value, str):
                    # Truncate string to fit remaining space
                    remaining = max_size_bytes - total_size - len(json.dumps({key: ""}, default=str))
                    if remaining > 100:  # Only truncate if meaningful space left
                        truncated[key] = value[:remaining - 50] + "... (truncated)"
                    else:
                        truncated[key] = "... (truncated - too large)"
                elif isinstance(value, (list, tuple)):
                    # Keep first N items that fit
                    truncated[key] = []
                    for item in value:
                        test_list = [item]
                        item_size = len(json.dumps({key: test_list}, default=str))
                        if total_size + item_size > max_size_bytes:
                            truncated[key].append("... (truncated)")
                            break
                        truncated[key].append(item)
                        total_size += item_size
                elif isinstance(value, dict):
                    # Recursively truncate nested dict
                    remaining = max_size_bytes - total_size
                    nested = _truncate_snapshot(value, remaining // 1024)
                    truncated[key] = nested
                    total_size += len(json.dumps({key: nested}, default=str))
                else:
                    # For other types, try to include if it fits
                    if total_size + pair_size <= max_size_bytes:
                        truncated[key] = value
                        total_size += pair_size
                    else:
                        truncated[key] = "... (truncated - too large)"
                break
            else:
                # Include this key-value pair
                truncated[key] = value
                total_size += pair_size
        
        # Add truncation metadata
        truncated["_truncated"] = True
        truncated["_original_size_kb"] = round(original_size_kb, 2)
        truncated["_truncated_size_kb"] = round(len(json.dumps(truncated, default=str)) / 1024, 2)
        
        logger.debug(
            f"Truncated snapshot from {original_size_kb:.2f}KB to {truncated['_truncated_size_kb']:.2f}KB "
            f"(limit: {max_size_kb}KB)"
        )
        
        return truncated
        
    except Exception as e:
        # If truncation fails, return minimal data
        logger.warning(f"Failed to truncate snapshot: {e}, returning minimal data")
        return {
            "_truncation_error": str(e),
            "_original_keys": list(data.keys())[:10]  # Keep first 10 keys as reference
        }


def get_stage_order(state: Dict) -> int:
    """Get the current stage order from state."""
    return state.get("_stage_order", 0) + 1


def extract_input_keys(state: Dict, agent_name: str) -> List[str]:
    """Extract relevant input state keys for an agent."""
    # Agent-specific input keys - CORRECTED based on actual code analysis
    agent_inputs = {
        # Core pipeline agents - CORRECTED
        "input_enhancer": ["question_text", "question_options", "current_validation_errors"],
        "domain_knowledge_retriever": ["question_text"],  # Removed pedagogical_context (not used)
        "router": ["question_text", "question_options", "pedagogical_context", "current_validation_errors"],
        "game_planner": ["question_text", "pedagogical_context", "domain_knowledge", "template_selection"],
        "scene_generator": ["question_text", "question_options", "game_plan",
                           "pedagogical_context", "template_selection", "current_validation_errors"],

        # Diagram pipeline agents - CORRECTED
        "diagram_image_retriever": ["question_text", "template_selection", "domain_knowledge", "image_search_attempts"],
        "image_label_remover": ["diagram_image"],
        "sam3_prompt_generator": ["template_selection", "cleaned_image_path", "diagram_image",
                                   "domain_knowledge", "game_plan"],
        "diagram_image_segmenter": ["diagram_image", "sam3_prompts", "cleaned_image_path"],
        "diagram_zone_labeler": ["template_selection", "diagram_segments", "cleaned_image_path",
                                  "game_plan", "domain_knowledge", "sam3_prompts",
                                  "image_search_attempts", "max_image_attempts"],

        # Qwen VLM agents (experimental pipeline)
        "qwen_annotation_detector": ["diagram_image", "template_selection"],
        "qwen_sam_zone_detector": ["annotation_elements", "cleaned_image_path", "diagram_image",
                                   "domain_knowledge", "game_plan"],

        # Image classification agents (unlabeled diagram fast path)
        "image_label_classifier": ["diagram_image"],
        "direct_structure_locator": ["diagram_image", "domain_knowledge", "image_classification"],

        # Hierarchical label diagram preset agents
        "diagram_image_generator": ["diagram_image", "scene_structure", "domain_knowledge", "pedagogical_context"],
        "gemini_zone_detector": ["generated_diagram_path", "cleaned_image_path", "diagram_image", "domain_knowledge"],

        # Advanced label diagram preset agents (Preset 2)
        "diagram_type_classifier": ["question_text", "domain_knowledge"],
        "scene_sequencer": ["question_text", "domain_knowledge", "game_plan", "diagram_type"],

        # Agentic game design agents (Preset 2 - NEW)
        "diagram_analyzer": ["question_text", "domain_knowledge"],
        "game_designer": ["question_text", "pedagogical_context", "domain_knowledge", "template_selection"],
        "design_interpreter": ["game_design", "domain_knowledge", "template_selection"],
        "multi_scene_image_orchestrator": ["scene_breakdown", "needs_multi_scene", "question_text",
                                           "domain_knowledge", "game_design"],
        "multi_scene_orchestrator": ["scene_breakdown", "game_plan", "domain_knowledge",
                                     "interaction_design", "question_text"],

        # Agentic interaction design agents (replaces hardcoded Bloom's mapping)
        "interaction_designer": ["question_text", "pedagogical_context", "domain_knowledge", "game_plan"],
        "interaction_validator": ["interaction_design", "game_plan", "pedagogical_context", "domain_knowledge"],

        # Blueprint generator - MOST CRITICAL FIX
        # NOTE: blueprint_generator now runs AFTER asset pipeline, so it receives generated_assets
        "blueprint_generator": [
            "question_text", "question_options", "pedagogical_context",
            "template_selection", "game_plan", "scene_data", "domain_knowledge",
            "diagram_zones", "diagram_labels", "diagram_image", "cleaned_image_path",
            "current_validation_errors",
            # NEW: Generated assets from asset pipeline (runs before blueprint)
            "generated_assets", "validated_assets",
            # Multi-scene inputs (Preset 2)
            "needs_multi_scene", "scene_diagrams", "scene_zones", "scene_labels",
            "scene_breakdown", "game_design",
            # Entity registry and interaction design (multi-mechanic support)
            "entity_registry", "interaction_design"
        ],

        # Diagram generation agents (with full context)
        "diagram_spec_generator": [
            "blueprint", "diagram_zones", "diagram_labels", "diagram_image",
            "generated_assets", "scene_structure", "generated_diagram_path"
        ],
        "diagram_svg_generator": [
            "diagram_spec", "blueprint", "diagram_image",
            "generated_assets", "validated_assets"
        ],
        "code_generator": ["blueprint", "template_selection", "scene_data"],
        # asset_generator removed - functionality moved to diagram_svg_generator

        # Validation agents
        "blueprint_validator": ["blueprint", "template_selection", "pedagogical_context"],
        "diagram_spec_validator": ["diagram_spec"],
        "code_verifier": ["generated_code", "blueprint", "template_selection"],
        "playability_validator": ["blueprint", "template_selection"],

        # Scene stage agents (hierarchical scene generation) - optimized with domain data
        "scene_stage1_structure": ["question_text", "question_options", "game_plan",
                                   "pedagogical_context", "template_selection", "domain_knowledge"],
        "scene_stage2_assets": ["question_text", "question_options", "game_plan",
                                "template_selection", "scene_structure", "domain_knowledge", "diagram_zones"],
        "scene_stage3_interactions": ["game_plan", "template_selection",
                                      "scene_structure", "scene_assets", "domain_knowledge", "pedagogical_context"],

        # Human review
        "human_review": ["pending_human_review", "current_validation_errors"],

        # =====================================================================
        # PHASE 6: CONDITIONAL ROUTING NODES
        # =====================================================================
        "check_post_scene_needs": ["template_selection", "scene_assets", "planned_assets", "generated_assets"],
        "check_post_blueprint_needs": ["template_selection", "scene_assets", "planned_assets", "generated_assets"],
        "check_post_blueprint_route": ["_needs_diagram_spec", "template_selection"],
        "check_diagram_spec_route": ["_needs_diagram_spec", "template_selection"],

        # Asset generation pipeline (runs BEFORE blueprint - uses scene data, not blueprint)
        "asset_planner": ["game_plan", "scene_breakdown", "domain_knowledge"],
        "asset_generator_orchestrator": ["planned_assets", "workflow_execution_plan", "domain_knowledge"],
        "asset_validator": ["planned_assets", "generated_assets"],  # No blueprint dependency

        # ReAct Agents (Preset 1 ReAct - LEGACY 3-agent architecture)
        "research_routing_agent": ["question_text", "question"],
        "game_design_agent": [
            "question_text", "enhanced_question", "selected_template", "template_selection",
            "blooms_level", "subject", "diagram_zones", "diagram_labels", "pedagogical_context"
        ],
        "blueprint_asset_agent": [
            "question_text", "selected_template", "template_selection", "game_plan",
            "scene_data", "populated_scene", "interactions", "diagram_zones",
            "diagram_labels", "diagram_image_url"
        ],

        # =====================================================================
        # REDESIGNED AGENTS (Agentic Sequential - 8 agents)
        # =====================================================================
        "research_agent": ["question_text", "question"],
        "image_agent": [
            "question_text", "pedagogical_context", "domain_knowledge", "diagram_labels"
        ],
        "output_renderer": [
            "blueprint", "diagram_zones", "diagram_labels", "diagram_image_url", "diagram_spec"
        ],

        # =====================================================================
        # REDESIGNED AGENTS (ReAct - 4 agents)
        # =====================================================================
        "research_image_agent": ["question_text", "question"],
        "blueprint_agent": [
            "question_text", "template_selection", "game_plan", "scene_data",
            "populated_scene", "interactions", "diagram_zones", "diagram_labels",
            "diagram_image_url"
        ],
        "asset_render_agent": [
            "blueprint", "diagram_zones", "diagram_labels", "diagram_image_url"
        ],

        # =====================================================================
        # HAD (Hierarchical Agentic DAG) AGENTS
        # =====================================================================
        "zone_planner": [
            "question_text", "domain_knowledge", "pedagogical_context",
            "template_selection", "generated_diagram_path", "diagram_image"
        ],
        "game_orchestrator": [
            "question_text", "domain_knowledge", "pedagogical_context",
            "template_selection", "diagram_zones", "zone_groups"
        ],
        # Unified game designer
        "game_designer": [
            "question_text", "domain_knowledge", "pedagogical_context",
            "template_selection"
        ],
        "design_interpreter": [
            "game_design", "domain_knowledge", "template_selection"
        ],
        "output_orchestrator": [
            "game_plan", "scene_structure", "scene_assets", "scene_interactions",
            "diagram_zones", "zone_groups", "domain_knowledge", "template_selection"
        ],

        # =====================================================================
        # V3 Pipeline Agents
        # =====================================================================
        "game_designer_v3": [
            "enhanced_question", "question", "subject", "blooms_level",
            "domain_knowledge", "canonical_labels", "learning_objectives",
            "pedagogical_context",
        ],
        "design_validator": ["game_design_v3"],
        "scene_architect_v3": [
            "game_design_v3", "domain_knowledge", "canonical_labels",
        ],
        "scene_validator": ["scene_specs_v3", "game_design_v3"],
        "interaction_designer_v3": [
            "game_design_v3", "scene_specs_v3", "domain_knowledge", "canonical_labels",
        ],
        "interaction_validator": ["interaction_specs_v3", "scene_specs_v3", "game_design_v3"],
        "asset_generator_v3": [
            "game_design_v3", "scene_specs_v3", "interaction_specs_v3",
            "domain_knowledge", "canonical_labels",
        ],
        "blueprint_assembler_v3": [
            "game_design_v3", "scene_specs_v3", "interaction_specs_v3",
            "generated_assets_v3",
        ],
        # Legacy v3 agents (kept for backward compat)
        "asset_spec_builder": ["game_design_v3", "asset_graph_v3"],
        "asset_orchestrator_v3": ["game_design_v3", "asset_graph_v3", "diagram_image"],

        # =====================================================================
        # PhET Simulation Agents
        # =====================================================================
        "phet_simulation_selector": [
            "question_text", "pedagogical_context", "domain_knowledge"
        ],
        "phet_assessment_designer": [
            "question_text", "selected_simulation", "pedagogical_context"
        ],
        "phet_game_planner": [
            "question_text", "selected_simulation", "assessment_design"
        ],
        "phet_bridge_config_generator": [
            "selected_simulation", "game_plan", "assessment_design"
        ],
        "phet_blueprint_generator": [
            "game_plan", "bridge_config", "assessment_design"
        ],

        # =====================================================================
        # V4 Pipeline Agents
        # =====================================================================
        "v4_input_analyzer": ["question_text", "question_options"],
        "v4_dk_retriever": ["question_text", "pedagogical_context"],
        "v4_phase0_merge": ["pedagogical_context", "domain_knowledge"],
        "v4_game_designer": ["question_text", "pedagogical_context", "domain_knowledge",
                             "design_validation", "design_retry_count"],
        "v4_game_plan_validator": ["game_plan"],
        "v4_content_builder": ["game_plan", "domain_knowledge", "pedagogical_context"],
        "v4_asset_worker": ["scene_id", "image_spec", "zone_labels"],
        "v4_asset_merge": ["generated_assets_raw"],
        "v4_assembler": ["game_plan", "mechanic_contents", "interaction_results", "generated_assets"],

        # V4 Algorithm Pipeline agents
        "v4a_dk_retriever": ["question_text", "pedagogical_context"],
        "v4a_game_concept_designer": ["question_text", "pedagogical_context", "domain_knowledge", "concept_retry_count"],
        "v4a_concept_validator": ["game_concept"],
        "v4a_graph_builder": ["game_concept"],
        "v4a_plan_validator": ["game_plan"],
        "v4a_scene_content_gen": ["game_plan", "domain_knowledge"],
        "v4a_content_merge": ["scene_contents_raw"],
        "v4a_asset_worker": ["game_plan", "scene_contents"],
        "v4a_asset_merge": ["scene_assets_raw"],
        "v4a_blueprint_assembler": ["game_plan", "scene_contents", "scene_assets"],

        # V4 Cascade agents (fan-out pipeline)
        "v4_game_concept_designer": ["question_text", "pedagogical_context", "domain_knowledge", "concept_retry_count"],
        "v4_concept_validator": ["game_concept"],
        "v4_scene_design_send": [],
        "v4_scene_designer": ["scene_concept", "scene_index", "narrative_theme", "domain_knowledge"],
        "v4_scene_design_merge": ["scene_creative_designs_raw"],
        "v4_graph_builder": ["game_concept", "scene_creative_designs"],
        "v4_content_dispatch": [],
        "v4_content_generator": ["mechanic_plan", "scene_context", "domain_knowledge"],
        "v4_content_merge": ["mechanic_contents_raw"],
        "v4_item_asset_worker": ["mechanic_contents", "game_plan"],
        "v4_interaction_designer": ["scene_plan", "mechanic_contents", "pedagogical_context"],
        "v4_interaction_merge": ["interaction_results_raw"],
    }
    return agent_inputs.get(agent_name, [])


def extract_output_keys(result: Dict, agent_name: str) -> List[str]:
    """Extract relevant output state keys for an agent."""
    # Agent-specific output keys - covers all 26+ agents in the pipeline
    agent_outputs = {
        # Core pipeline agents
        "input_enhancer": ["pedagogical_context"],
        "domain_knowledge_retriever": ["domain_knowledge"],
        "router": ["template_selection"],
        "game_planner": ["game_plan"],  # Now includes scene_breakdown
        "scene_generator": ["scene"],

        # Diagram pipeline agents
        "diagram_image_retriever": ["diagram_image"],
        "image_label_remover": ["diagram_image", "cleaned_image_path", "removed_labels"],  # Output: cleaned image path and removed labels
        "sam3_prompt_generator": ["sam3_prompts"],
        "diagram_image_segmenter": ["diagram_segments"],
        "diagram_zone_labeler": ["diagram_zones", "diagram_labels"],

        # Qwen VLM agents (experimental pipeline)
        "qwen_annotation_detector": ["annotation_elements", "detection_mask_path", "text_labels_found"],
        "qwen_sam_zone_detector": ["diagram_zones", "diagram_labels", "zone_detection_method", "entity_registry"],

        # Image classification agents (unlabeled diagram fast path)
        "image_label_classifier": ["image_classification"],
        "direct_structure_locator": ["diagram_zones", "diagram_labels", "zone_detection_method",
                                     "cleaned_image_path", "removed_labels"],

        # Hierarchical label diagram preset agents
        "diagram_image_generator": ["generated_diagram_path", "diagram_metadata", "cleaned_image_path"],
        "gemini_zone_detector": ["diagram_zones", "diagram_labels", "zone_groups", "zone_detection_method", "entity_registry", "zone_detection_metadata"],

        # Advanced label diagram preset agents (Preset 2)
        "diagram_type_classifier": ["diagram_type", "diagram_type_config", "zone_strategy", "diagram_type_confidence"],
        "scene_sequencer": ["needs_multi_scene", "num_scenes", "scene_progression_type", "scene_breakdown"],

        # Agentic game design agents (Preset 2 - NEW)
        "diagram_analyzer": ["diagram_analysis"],
        "game_designer": ["game_design"],
        "design_interpreter": ["game_plan", "scene_breakdown", "needs_multi_scene"],
        "multi_scene_image_orchestrator": ["scene_diagrams", "scene_zones", "scene_labels"],
        "multi_scene_orchestrator": ["all_scene_data", "needs_multi_scene", "num_scenes"],

        # Agentic interaction design agents (replaces hardcoded Bloom's mapping)
        "interaction_designer": ["interaction_designs", "interaction_design"],  # List + backward compat
        "interaction_validator": ["interaction_validation", "interaction_design"],

        # Generation agents
        "blueprint_generator": ["blueprint"],
        "diagram_spec_generator": ["diagram_spec"],
        "diagram_svg_generator": ["diagram_svg", "asset_urls", "generation_complete"],  # Moved from asset_generator
        "code_generator": ["generated_code"],
        # asset_generator removed - outputs moved to diagram_svg_generator

        # Validation agents (with retry loop tracking - Phase 4)
        "blueprint_validator": ["validation_results", "current_validation_errors", "retry_counts"],
        "diagram_spec_validator": ["validation_results", "current_validation_errors", "retry_counts"],
        "code_verifier": ["validation_results", "current_validation_errors", "retry_counts"],
        "playability_validator": ["playability_valid", "playability_score", "playability_issues"],

        # Asset validation (with retry loop tracking - Phase 4)
        "asset_validator": ["asset_validation", "validated_assets", "validation_errors", "assets_valid", "retry_counts"],

        # Scene stage agents (hierarchical scene generation)
        "scene_stage1_structure": ["scene_structure"],
        "scene_stage2_assets": ["scene_assets"],
        "scene_stage3_interactions": ["scene_interactions", "scene_data"],

        # Human review
        "human_review": ["human_review_completed", "human_feedback"],

        # =====================================================================
        # PHASE 6: CONDITIONAL ROUTING NODES
        # =====================================================================
        "check_post_scene_needs": ["_needs_diagram_spec", "_needs_asset_generation", "_skip_asset_pipeline"],
        "check_post_blueprint_needs": ["_needs_diagram_spec", "_needs_asset_generation", "_skip_asset_pipeline"],
        "check_post_blueprint_route": [],  # Passthrough node, no outputs
        "check_diagram_spec_route": [],  # Passthrough node, no outputs

        # Asset generation pipeline (enhanced outputs)
        "asset_planner": ["planned_assets", "workflow_execution_plan"],
        "asset_generator_orchestrator": ["generated_assets", "entity_registry"],
        # Note: asset_validator is defined above with retry_counts for Phase 4

        # ReAct Agents (Preset 1 ReAct - LEGACY 3-agent architecture)
        "research_routing_agent": [
            "question_text", "enhanced_question", "blooms_level", "subject",
            "key_concepts", "domain_knowledge", "selected_template", "template_selection",
            "diagram_image_url", "diagram_zones", "diagram_labels", "pedagogical_context"
        ],
        "game_design_agent": [
            "game_plan", "scene_structure", "populated_scene", "scene_data",
            "interactions", "design_validation"
        ],
        "blueprint_asset_agent": [
            "blueprint", "blueprint_valid", "generated_assets", "failed_assets",
            "diagram_spec", "final_svg", "diagram_svg", "production_summary"
        ],

        # =====================================================================
        # REDESIGNED AGENTS (Agentic Sequential - 8 agents)
        # =====================================================================
        "research_agent": [
            "pedagogical_context", "domain_knowledge", "diagram_labels",
            "template_selection", "blooms_level", "subject", "key_concepts"
        ],
        "image_agent": [
            "diagram_image_url", "diagram_image", "diagram_zones"
        ],
        "output_renderer": [
            "diagram_spec", "diagram_svg", "asset_urls", "generation_complete"
        ],

        # =====================================================================
        # REDESIGNED AGENTS (ReAct - 4 agents)
        # =====================================================================
        "research_image_agent": [
            "question_text", "enhanced_question", "blooms_level", "subject",
            "key_concepts", "domain_knowledge", "selected_template", "template_selection",
            "diagram_image_url", "diagram_zones", "diagram_labels", "pedagogical_context"
        ],
        "blueprint_agent": [
            "blueprint", "blueprint_valid", "blueprint_validation_attempts",
            "blueprint_errors_fixed"
        ],
        "asset_render_agent": [
            "planned_assets", "generated_assets", "failed_assets", "diagram_spec",
            "final_svg", "diagram_svg", "asset_urls", "generation_complete",
            "production_summary"
        ],

        # =====================================================================
        # HAD (Hierarchical Agentic DAG) AGENTS
        # =====================================================================
        "zone_planner": [
            "diagram_zones", "diagram_labels", "zone_groups",
            "generated_diagram_path", "zone_detection_method", "zone_detection_metadata",
            "detection_trace",  # ReAct reasoning trace for UI visualization
            # HAD v3: Multi-scene and collision resolution
            "needs_multi_scene", "num_scenes", "scene_progression_type", "scene_breakdown",
            "scene_images", "scene_zones", "scene_zone_groups", "scene_labels",
            "zone_collision_metadata", "query_intent", "suggested_reveal_order",
            # HAD v3: Temporal Intelligence (Petri Net-inspired constraints)
            "temporal_constraints", "motion_paths",
            # Accessibility specs for WCAG 2.2 compliance
            "accessibility_specs"
        ],
        "game_orchestrator": [
            "game_plan", "scene_structure", "scene_assets", "scene_interactions",
            "design_metadata", "design_trace",  # Design reasoning trace for UI visualization
            # HAD v3: Multi-scene game design
            "game_sequence", "needs_multi_scene", "num_scenes", "scene_progression_type",
            # New feature configurations (Phase 2/3 implementation)
            "accessibility_config", "event_tracking_config", "undo_redo_config"
        ],
        # Unified game designer
        "game_designer": [
            "game_design",
        ],
        "design_interpreter": [
            "game_plan", "scene_breakdown", "needs_multi_scene",
        ],
        "output_orchestrator": [
            "blueprint", "diagram_spec", "diagram_svg", "generation_complete",
            "output_metadata"
        ],

        # =====================================================================
        # V3 Pipeline Agents
        # =====================================================================
        "game_designer_v3": ["game_design_v3"],
        "design_validator": ["design_validation_v3"],
        "scene_architect_v3": ["scene_specs_v3"],
        "scene_validator": ["scene_validation_v3"],
        "interaction_designer_v3": ["interaction_specs_v3"],
        "interaction_validator": ["interaction_validation_v3"],
        "asset_generator_v3": ["generated_assets_v3", "diagram_image", "diagram_zones"],
        "blueprint_assembler_v3": ["blueprint", "template_type"],
        # Legacy v3 agents (kept for backward compat)
        "asset_spec_builder": ["asset_manifest_v3", "asset_graph_v3"],
        "asset_orchestrator_v3": [
            "asset_manifest_v3", "generated_assets_v3",
            "diagram_image", "diagram_zones",
        ],

        # =====================================================================
        # PhET Simulation Agents
        # =====================================================================
        "phet_simulation_selector": [
            "selected_simulation", "simulation_capabilities", "selection_rationale"
        ],
        "phet_assessment_designer": [
            "assessment_design", "learning_objectives", "assessment_types"
        ],
        "phet_game_planner": [
            "game_plan", "interaction_sequence", "feedback_strategy"
        ],
        "phet_bridge_config_generator": [
            "bridge_config", "parameter_mappings", "event_handlers"
        ],
        "phet_blueprint_generator": [
            "blueprint", "validation_results"
        ],

        # =====================================================================
        # V4 Pipeline Agents
        # =====================================================================
        "v4_input_analyzer": ["pedagogical_context"],
        "v4_dk_retriever": ["domain_knowledge"],
        "v4_phase0_merge": ["pedagogical_context", "domain_knowledge"],
        "v4_game_designer": ["game_plan", "design_validation", "design_retry_count"],
        "v4_game_plan_validator": ["game_plan", "design_validation"],
        "v4_content_builder": ["mechanic_contents", "interaction_results", "is_degraded"],
        "v4_asset_worker": ["generated_assets_raw"],
        "v4_asset_merge": ["generated_assets", "asset_retry_count"],
        "v4_assembler": ["blueprint", "assembly_warnings", "generation_complete"],

        # V4 Algorithm Pipeline agents
        "v4a_dk_retriever": ["domain_knowledge"],
        "v4a_game_concept_designer": ["game_concept", "concept_retry_count"],
        "v4a_concept_validator": ["concept_validation"],
        "v4a_graph_builder": ["game_plan"],
        "v4a_plan_validator": ["plan_validation"],
        "v4a_scene_content_gen": ["scene_contents_raw"],
        "v4a_content_merge": ["scene_contents"],
        "v4a_asset_worker": ["scene_assets_raw"],
        "v4a_asset_merge": ["scene_assets"],
        "v4a_blueprint_assembler": ["blueprint", "assembly_warnings", "generation_complete"],

        # V4 Cascade agents (fan-out pipeline)
        "v4_game_concept_designer": ["game_concept", "concept_validation", "concept_retry_count"],
        "v4_concept_validator": ["concept_validation"],
        "v4_scene_design_send": [],
        "v4_scene_designer": ["scene_creative_designs_raw"],
        "v4_scene_design_merge": ["scene_creative_designs", "scene_design_validation"],
        "v4_graph_builder": ["game_plan"],
        "v4_content_dispatch": [],
        "v4_content_generator": ["mechanic_contents_raw"],
        "v4_content_merge": ["mechanic_contents"],
        "v4_item_asset_worker": ["mechanic_contents"],
        "v4_interaction_designer": ["interaction_results_raw"],
        "v4_interaction_merge": ["interaction_results"],
    }
    return agent_outputs.get(agent_name, [])


class InstrumentedAgentContext:
    """
    Context manager for instrumenting agent execution.

    Usage:
        async with InstrumentedAgentContext(state, "my_agent") as ctx:
            result = await my_agent_logic(state)
            ctx.set_llm_metrics(model="gpt-4", tokens=1234)
            ctx.complete(result)
            return result
    """

    def __init__(self, state: Dict, agent_name: str):
        self.state = state
        self.agent_name = agent_name
        self.run_id = state.get("_run_id")
        self.stage_id = None
        self._llm_metrics = {}
        self._validation_results = {}
        self._fallback_info = {}
        self._tool_metrics = {}
        self._react_metrics = {}
        self._step_callback = None

        # Create step callback for real-time streaming if run_id is available
        if self.run_id:
            self._step_callback = create_step_callback(self.run_id, agent_name)

    def emit_live_step(
        self,
        step_type: str,
        content: str,
        tool: Optional[str] = None
    ) -> None:
        """
        Emit a live step event for real-time streaming.

        Use this to emit reasoning steps to the frontend in real-time.

        Args:
            step_type: One of 'thought', 'action', 'observation', 'decision'
            content: The step content
            tool: Optional tool name for action steps
        """
        if self.run_id:
            emit_live_step(
                run_id=self.run_id,
                stage_name=self.agent_name,
                step_type=step_type,
                content=content,
                tool=tool
            )

    def get_step_callback(self) -> Optional[Callable[[Any], Awaitable[None]]]:
        """
        Get a step callback for use with LLMService.generate_with_tools().

        Returns:
            Async callback function or None if no run_id
        """
        # Recreate callback with stage_id if available (set in __aenter__)
        if self.run_id and self.stage_id and (
            self._step_callback is None or not getattr(self._step_callback, '_has_stage_id', False)
        ):
            self._step_callback = create_step_callback(self.run_id, self.agent_name, self.stage_id)
            self._step_callback._has_stage_id = True  # type: ignore
        return self._step_callback

    async def __aenter__(self):
        if not self.run_id:
            logger.debug(f"No _run_id in state, skipping instrumentation for {self.agent_name}")
            return self

        try:
            stage_order = get_stage_order(self.state)
            input_keys = extract_input_keys(self.state, self.agent_name)
            input_snapshot = {k: self.state.get(k) for k in input_keys if k in self.state}

            self.stage_id = track_stage_start(
                run_id=self.run_id,
                stage_name=self.agent_name,
                stage_order=stage_order,
                input_snapshot=input_snapshot
            )
            # Update stage order in state
            self.state["_stage_order"] = stage_order
        except Exception as e:
            logger.warning(f"Failed to start stage tracking: {e}")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.stage_id:
            return False  # Don't suppress exceptions

        try:
            if exc_type is not None:
                # Stage failed
                track_stage_failed(
                    stage_id=self.stage_id,
                    error_message=str(exc_val),
                    error_traceback=traceback.format_exc()
                )
            # Success tracking is done explicitly via complete()
        except Exception as e:
            logger.warning(f"Failed to track stage exit: {e}")

        return False  # Don't suppress exceptions

    def set_llm_metrics(
        self,
        model: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None
    ):
        """Set LLM metrics for this stage."""
        if model:
            self._llm_metrics["model_id"] = model
        if prompt_tokens is not None:
            self._llm_metrics["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            self._llm_metrics["completion_tokens"] = completion_tokens
        if latency_ms is not None:
            self._llm_metrics["latency_ms"] = latency_ms

    def set_validation_results(
        self,
        passed: bool,
        score: Optional[float] = None,
        errors: Optional[List] = None
    ):
        """Set validation results for validator stages."""
        self._validation_results["validation_passed"] = passed
        if score is not None:
            self._validation_results["validation_score"] = score
        if errors:
            self._validation_results["validation_errors"] = errors

    def set_fallback_used(self, reason: str):
        """Mark this stage as having used a fallback mechanism.

        This will result in a 'degraded' status instead of 'success'.
        """
        self._fallback_info["used_fallback"] = True
        self._fallback_info["fallback_reason"] = reason

    def set_tool_metrics(self, tool_calls: List[Dict]):
        """Track tool calls for agentic sequential agents.

        Args:
            tool_calls: List of tool call dictionaries with keys:
                - name: Tool name
                - arguments: Tool arguments
                - result: Tool result (truncated if large)
                - status: "success", "error", or "timeout"
                - latency_ms: Execution time in milliseconds
        """
        self._tool_metrics["tool_calls"] = tool_calls
        self._tool_metrics["total_tool_calls"] = len(tool_calls)
        self._tool_metrics["successful_calls"] = sum(
            1 for tc in tool_calls if tc.get("status") == "success"
        )
        self._tool_metrics["failed_calls"] = sum(
            1 for tc in tool_calls if tc.get("status") in ("error", "timeout")
        )
        self._tool_metrics["total_tool_latency_ms"] = sum(
            tc.get("latency_ms", 0) for tc in tool_calls
        )

    def set_react_metrics(
        self,
        iterations: int,
        tool_calls: int,
        reasoning_trace: List[Dict]
    ):
        """Track ReAct-specific metrics for multi-step reasoning agents.

        Args:
            iterations: Number of Reason→Act→Observe cycles
            tool_calls: Total number of tool calls across all iterations
            reasoning_trace: List of ReAct steps with keys:
                - thought: The reasoning/thought text
                - action: Tool call made (optional)
                - observation: Tool result/observation (optional)
                - iteration: Iteration number
        """
        self._react_metrics["react_iterations"] = iterations
        self._react_metrics["react_tool_calls"] = tool_calls
        # Truncate reasoning trace to prevent DB bloat
        truncated_trace = []
        for step in reasoning_trace[:20]:  # Max 20 steps
            truncated_step = {
                "thought": step.get("thought", "")[:500],  # Max 500 chars
                "iteration": step.get("iteration", 0)
            }
            if step.get("action"):
                action = step["action"]
                if isinstance(action, dict):
                    truncated_step["action"] = {
                        "name": action.get("name", ""),
                        "arguments_preview": str(action.get("arguments", {}))[:200]
                    }
                elif isinstance(action, str):
                    # ReAct base passes action as a string (tool name)
                    truncated_step["action"] = {
                        "name": action,
                        "arguments_preview": ""
                    }
            if step.get("observation"):
                obs = str(step.get("observation", ""))
                truncated_step["observation"] = obs[:500] if len(obs) > 500 else obs
            truncated_trace.append(truncated_step)
        self._react_metrics["reasoning_trace"] = truncated_trace

    def complete(self, result: Dict):
        """Mark the stage as successfully completed with the result."""
        if not self.stage_id:
            return

        try:
            output_keys = extract_output_keys(result, self.agent_name)
            output_snapshot = {k: result.get(k) for k in output_keys if k in result}

            # Include tool metrics in output snapshot if present
            if self._tool_metrics:
                output_snapshot["_tool_metrics"] = self._tool_metrics

            # Include ReAct metrics in output snapshot if present
            if self._react_metrics:
                output_snapshot["_react_metrics"] = self._react_metrics

            # Include ReAct trace from react_base.py agents (for frontend visualization)
            if "_react_trace" in result:
                output_snapshot["_react_trace"] = result["_react_trace"]
            if "_llm_metrics" in result:
                output_snapshot["_llm_metrics"] = result["_llm_metrics"]

            # Include sub-stages from compound V4 nodes (for sub-node rendering)
            if hasattr(self, '_sub_stages') and self._sub_stages:
                output_snapshot["_sub_stages"] = self._sub_stages
            elif "_sub_stages" in result:
                output_snapshot["_sub_stages"] = result["_sub_stages"]

            track_stage_complete(
                stage_id=self.stage_id,
                output_snapshot=output_snapshot,
                **self._llm_metrics,
                **self._validation_results,
                **self._fallback_info
            )
        except Exception as e:
            logger.warning(f"Failed to complete stage tracking: {e}")


def instrumented_agent(agent_name: str):
    """
    Decorator to add instrumentation to an agent function.
    
    The wrapped function receives an optional `ctx` parameter (InstrumentedAgentContext).
    If ctx is provided, the agent should:
    1. Capture LLM metrics from LLM calls and call ctx.set_llm_metrics()
    2. Call ctx.complete(result) after successful execution
    
    Usage:
        @instrumented_agent("my_agent")
        async def my_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
            # ... agent logic ...
            if ctx:
                ctx.set_llm_metrics(model="gpt-4", prompt_tokens=100, completion_tokens=50)
                ctx.complete(result)
            return result
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(state: Dict) -> Dict:
            run_id = state.get("_run_id")

            if not run_id:
                # No instrumentation, just run the agent
                return await func(state, None)

            async with InstrumentedAgentContext(state, agent_name) as ctx:
                try:
                    # Pass ctx to the agent function
                    result = await func(state, ctx)
                    
                    # Extract LLM metrics if present in result (backward compatibility)
                    if "_llm_metrics" in result:
                        metrics = result.pop("_llm_metrics")
                        ctx.set_llm_metrics(
                            model=metrics.get("model"),
                            prompt_tokens=metrics.get("prompt_tokens") or metrics.get("input_tokens"),
                            completion_tokens=metrics.get("completion_tokens") or metrics.get("output_tokens"),
                            latency_ms=metrics.get("latency_ms")
                        )

                    # Extract validation results if present
                    validation = result.get("validation_results", {}).get(agent_name.replace("_validator", ""))
                    if validation:
                        ctx.set_validation_results(
                            passed=validation.get("is_valid", False),
                            errors=validation.get("errors")
                        )

                    # Complete the stage if not already done
                    if ctx.stage_id:
                        ctx.complete(result)
                    return result
                except Exception as e:
                    # Exception will be handled by __aexit__
                    raise

        return wrapper
    return decorator


def wrap_agent_with_instrumentation(agent_func: Callable, agent_name: str) -> Callable:
    """
    Wrap an agent function with instrumentation.

    This automatically adds instrumentation to any agent function without requiring
    the @instrumented_agent decorator or manual ctx handling.

    Usage:
        wrapped_agent = wrap_agent_with_instrumentation(input_enhancer_agent, "input_enhancer")
        graph.add_node("input_enhancer", wrapped_agent)
    """
    @wraps(agent_func)
    async def wrapped(state: Dict) -> Dict:
        run_id = state.get("_run_id")
        logger.info(f"[Instrumentation] Agent {agent_name} called, run_id={run_id}")

        if not run_id:
            logger.debug(f"[Instrumentation] No _run_id for {agent_name}, skipping tracking")
            # No instrumentation, just run the agent
            # Try calling with ctx=None for backward compatibility
            try:
                return await agent_func(state, None)
            except TypeError:
                # Agent doesn't accept ctx parameter
                return await agent_func(state)

        # Log start of agent execution
        add_execution_log(
            run_id=run_id,
            message=f"Starting agent: {agent_name}",
            level="info"
        )

        async with InstrumentedAgentContext(state, agent_name) as ctx:
            try:
                # Try calling with ctx parameter
                try:
                    result = await agent_func(state, ctx)
                except TypeError:
                    # Agent doesn't accept ctx parameter, call without it
                    result = await agent_func(state)
                
                # Extract LLM metrics if present in result
                if "_llm_metrics" in result:
                    metrics = result.pop("_llm_metrics")
                    ctx.set_llm_metrics(
                        model=metrics.get("model"),
                        prompt_tokens=metrics.get("prompt_tokens") or metrics.get("input_tokens"),
                        completion_tokens=metrics.get("completion_tokens") or metrics.get("output_tokens"),
                        latency_ms=metrics.get("latency_ms")
                    )

                # Extract validation results if present
                validation = result.get("validation_results", {})
                if validation:
                    # Try to find validation for this agent
                    validation_key = agent_name.replace("_validator", "").replace("_agent", "")
                    if validation_key in validation:
                        val_result = validation[validation_key]
                        ctx.set_validation_results(
                            passed=val_result.get("is_valid", False),
                            score=val_result.get("score"),
                            errors=val_result.get("errors")
                        )

                # Detect fallback usage from result
                # Check for common fallback indicators in the result
                if "_used_fallback" in result:
                    ctx.set_fallback_used(result.pop("_fallback_reason", "Fallback mechanism used"))
                    result.pop("_used_fallback", None)
                # Grid fallback removed - diagram_image_segmenter now fails if SAM3 unavailable
                # No need to check for fallback-grid method

                # Extract tool metrics if present (from agentic sequential agents)
                if "_tool_metrics" in result:
                    tool_metrics = result.pop("_tool_metrics")
                    if "tool_calls" in tool_metrics:
                        ctx.set_tool_metrics(tool_metrics["tool_calls"])

                # Extract ReAct metrics if present (from ReAct agents)
                if "_react_metrics" in result:
                    react_metrics = result.pop("_react_metrics")
                    ctx.set_react_metrics(
                        iterations=react_metrics.get("iterations", 0),
                        tool_calls=react_metrics.get("total_tool_calls", 0),
                        reasoning_trace=react_metrics.get("reasoning_trace", [])
                    )

                # Extract sub-stages from compound V4 nodes (stored in output_snapshot, not in LangGraph state)
                sub_stages = result.pop("_sub_stages", None)
                if sub_stages is not None:
                    ctx._sub_stages = sub_stages

                # Detect degraded status from result (e.g. zone detection failures, content failures)
                if result.get("is_degraded"):
                    ctx.set_fallback_used("Stage completed with degraded results")
                # Also check sub-stages for failures
                elif sub_stages:
                    failed_subs = [s for s in sub_stages if s.get("status") in ("failed", "error")]
                    if failed_subs:
                        ctx.set_fallback_used(f"{len(failed_subs)} sub-stage(s) failed")
                # Check generated_assets_raw for error status (asset workers)
                elif agent_name == "v4_asset_worker":
                    assets = result.get("generated_assets_raw", [])
                    if assets and any(a.get("status") in ("error", "failed") for a in assets):
                        ctx.set_fallback_used("Asset generation failed for this scene")

                # Complete the stage
                if ctx.stage_id:
                    ctx.complete(result)

                # Log successful completion
                duration_msg = ""
                if ctx.stage_id:
                    # Try to get duration from completed stage
                    try:
                        db = SessionLocal()
                        stage = db.query(StageExecution).filter(StageExecution.id == ctx.stage_id).first()
                        if stage and stage.duration_ms:
                            duration_msg = f" in {stage.duration_ms}ms"
                        db.close()
                    except Exception:
                        pass

                add_execution_log(
                    run_id=run_id,
                    stage_execution_id=ctx.stage_id,
                    message=f"Completed agent: {agent_name}{duration_msg}",
                    level="info"
                )

                return result
            except Exception as e:
                # Log failure
                add_execution_log(
                    run_id=run_id,
                    stage_execution_id=ctx.stage_id,
                    message=f"Agent {agent_name} failed: {str(e)[:200]}",
                    level="error"
                )
                # Exception will be handled by __aexit__
                raise

    return wrapped
