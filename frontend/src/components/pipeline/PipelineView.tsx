'use client'

import { useState, useMemo, useCallback, useEffect, useRef } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  ConnectionMode,
  MarkerType,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow'
import {
  PipelineRun,
  StageExecution,
  CATEGORY_COLORS,
  GraphStructure,
  ExecutionPath,
  GraphStructureEdge,
  PipelineRunWithTotals,
  ClusterDefinition
} from './types'
import { AgentNode, DecisionNode, OrchestratorNode, SubAgentNode, StageListItem } from './AgentNode'
import { StagePanel } from './StagePanel'
import { ClusterView, HAD_CLUSTER_LAYOUT } from './ClusterView'
import {
  resolveStageStatus,
  createStatusResolver,
  buildStageStatusMap,
  type StatusResolutionContext,
  type StageStatusResult
} from '@/lib/stageStatus'

interface PipelineViewProps {
  run: PipelineRun | PipelineRunWithTotals
  stages: StageExecution[]
  onRetry?: (runId: string, stageName: string) => void
  compact?: boolean
  onSelectStage?: (stage: StageExecution | null) => void
}

// Define the graph layout - each array is a COLUMN (left to right flow)
// Columns represent dependency levels - agents in the same column have the same depth
//
// SIMPLIFIED PIPELINE (No Labeled/Unlabeled Branch):
//   1. Linear start: input_enhancer → domain_knowledge_retriever → router
//   2. Conditional: router → game_planner (high confidence) OR human_review (low confidence)
//   3. game_planner → scene_stage1_structure → scene_stage2_assets → scene_stage3_interactions
//   4. INTERACTIVE_DIAGRAM image pipeline:
//      - diagram_image_retriever: Retrieve reference image from web
//      - diagram_image_generator: Generate clean educational diagram (Gemini Imagen)
//      - gemini_zone_detector: Detect zones using Gemini vision
//   5. Asset pipeline (runs BEFORE blueprint): asset_planner → asset_generator_orchestrator → asset_validator
//   6. blueprint_generator → blueprint_validator (can retry or escalate to human_review)
//      NOTE: Blueprint now has access to generated_assets from the asset pipeline
//   7. diagram_spec_generator → diagram_svg_generator → END
//
// NOTE: Asset pipeline runs BEFORE blueprint so that blueprint can reference actual generated asset URLs
const GRAPH_LAYOUT = [
  ['input_enhancer'],                                 // Col 0: Entry point
  ['domain_knowledge_retriever'],                     // Col 1: Retrieve domain knowledge
  ['diagram_type_classifier', 'diagram_analyzer'],    // Col 2: Classify diagram type (Preset 2) / Analyze (Agentic)
  ['router', 'human_review'],                         // Col 3: Router + Human Review (escalation point)
  ['game_designer'],                                  // Col 4: Unconstrained game design (all presets)
  ['design_interpreter'],                             // Col 5: Creative→structured mapping
  ['game_planner'],                                   // Col 6: Legacy game planner (deprecated)
  ['interaction_designer'],                           // Col 6: Agentic interaction design
  ['interaction_validator'],                          // Col 7: Validate interaction design
  ['scene_sequencer'],                                // Col 8: Multi-scene planning (Preset 2)
  ['scene_stage1_structure', 'multi_scene_image_orchestrator'], // Col 9: Scene structure OR Multi-scene image orchestrator
  ['scene_stage2_assets'],                            // Col 10: Scene Stage 2 - Assets
  ['scene_stage3_interactions'],                      // Col 11: Scene Stage 3 - Interactions
  ['multi_scene_orchestrator'],                       // Col 12: Multi-scene orchestrator (multi-scene games only)
  ['diagram_image_retriever'],                        // Col 13: Retrieve reference image
  ['diagram_image_generator'],                        // Col 14: Generate clean diagram (Gemini)
  ['gemini_zone_detector'],                           // Col 15: Detect zones (Gemini Vision)
  ['asset_planner'],                                  // Col 16: Plan required assets
  ['asset_generator_orchestrator'],                   // Col 17: Generate assets sequentially
  ['asset_validator'],                                // Col 18: Validate generated assets
  ['blueprint_generator'],                            // Col 19: Generate game blueprint (with generated_assets)
  ['blueprint_validator'],                            // Col 20: Validate (retry/escalate)
  ['diagram_spec_generator'],                         // Col 21: Generate SVG spec
  ['diagram_svg_generator'],                          // Col 22: Render SVG → END
]

// ReAct Pipeline Layout - REDESIGNED 4 agents with reduced tool count
// Research shows 20-40% quality degradation at 10 tools per agent
// Used when preset is "preset_1_react"
const REACT_GRAPH_LAYOUT = [
  ['research_image_agent'],      // Col 0: Research + Image (5 tools) - replaces 5 agents
  ['game_design_agent'],         // Col 1: Game Design (5 tools) - replaces 4 agents
  ['blueprint_agent'],           // Col 2: Blueprint creation (3 tools)
  ['asset_render_agent'],        // Col 3: Assets + Rendering (4 tools)
]

// Legacy ReAct Layout - 3 collapsed agents (NOT RECOMMENDED)
// Kept for backwards compatibility
const REACT_GRAPH_LAYOUT_LEGACY = [
  ['research_routing_agent'],    // Col 0: Research + Routing + Image (6 tools)
  ['game_design_agent'],         // Col 1: Game Design (9 tools)
  ['blueprint_asset_agent'],     // Col 2: Blueprint + Assets (10 tools - TOO MANY)
]

// HAD (Hierarchical Agentic DAG) Layout - Vision + Game Design clusters
// Used when HAD agents are detected in the run
const HAD_GRAPH_LAYOUT = [
  ['input_enhancer'],                    // Col 0: Entry point
  ['domain_knowledge_retriever'],        // Col 1: Domain knowledge
  ['router'],                            // Col 2: Template selection
  ['diagram_image_retriever'],           // Col 3: Image retrieval
  ['zone_planner'],                      // Col 4: HAD Vision Cluster - zone detection
  ['game_designer', 'game_orchestrator'], // Col 5: HAD Game Design (v3 unified or legacy)
  ['output_orchestrator'],               // Col 6: HAD Output - blueprint + rendering
  ['blueprint_validator'],               // Col 7: Validation
]

// V3 Pipeline Layout - 5-phase ReAct architecture with validation loops
// Used when preset is "v3"
const V3_GRAPH_LAYOUT = [
  ['input_enhancer'],                    // Col 0: Entry point
  ['domain_knowledge_retriever'],        // Col 1: Domain knowledge
  ['router'],                            // Col 2: Template selection
  ['game_designer_v3'],                  // Col 3: Phase 1 — ReAct game design (5 tools)
  ['design_validator'],                  // Col 4: Phase 1 — Design validation
  ['scene_architect_v3'],                // Col 5: Phase 2 — ReAct scene architecture (4 tools)
  ['scene_validator'],                   // Col 6: Phase 2 — Scene validation
  ['interaction_designer_v3'],           // Col 7: Phase 3 — ReAct interaction design (4 tools)
  ['interaction_validator'],             // Col 8: Phase 3 — Interaction validation
  ['asset_generator_v3'],               // Col 9: Phase 4 — ReAct asset generation (5 tools)
  ['blueprint_assembler_v3'],            // Col 10: Phase 5 — ReAct blueprint assembly (4 tools)
]

// V4 Pipeline Layout - Streamlined 5-phase pipeline
// Phase 0 parallel context (input_analyzer + dk_retriever shown as same column)
// Phase 1 design with retry, Phase 2 content build, Phase 3 assets, Phase 4 assembly
const V4_GRAPH_LAYOUT = [
  ['v4_input_analyzer', 'v4_dk_retriever'],              // Col 0: Phase 0 — Parallel context gathering
  ['v4_phase0_merge'],                                    // Col 1: Phase 0 — Merge barrier
  ['v4_game_concept_designer'],                           // Col 2: Phase 1a — Concept design
  ['v4_concept_validator'],                               // Col 3: Phase 1a — Concept validation
  ['v4_scene_design_send', 'v4_scene_designer', 'v4_scene_design_merge'],  // Col 4: Phase 1b — Scene design fan-out/worker/in
  ['v4_graph_builder'],                                   // Col 5: Phase 1c — Graph construction
  ['v4_game_plan_validator'],                             // Col 6: Phase 1c — Plan validation
  ['v4_content_dispatch', 'v4_content_generator', 'v4_content_merge'],  // Col 7: Phase 2a — Content fan-out/worker/in
  ['v4_item_asset_worker'],                               // Col 8: Phase 2a+ — Item image enrichment
  ['v4_interaction_designer', 'v4_interaction_merge'],    // Col 9: Phase 2b — Interaction design + merge
  ['v4_asset_worker'],                                    // Col 9: Phase 3a — Parallel asset workers
  ['v4_asset_merge'],                                     // Col 10: Phase 3b — Asset merge
  ['v4_assembler'],                                       // Col 11: Phase 4 — Blueprint assembly
]

// Fan-out stages that can have multiple executions
const V4_FANOUT_STAGES = new Set([
  'v4_scene_designer',
  'v4_content_generator',
  'v4_interaction_designer',
  'v4_asset_worker',
])

// V4 Algorithm Pipeline Layout
const V4_ALGORITHM_GRAPH_LAYOUT = [
  ['v4_input_analyzer', 'v4a_dk_retriever'],         // Col 0: Phase 0 — Parallel context gathering
  ['algo_phase0_merge'],                              // Col 1: Phase 0 — Merge barrier
  ['v4a_game_concept_designer'],                      // Col 2: Phase 1 — Concept design
  ['v4a_concept_validator'],                           // Col 3: Phase 1 — Concept validation
  ['v4a_graph_builder'],                               // Col 4: Phase 2 — Plan construction
  ['v4a_plan_validator'],                              // Col 5: Phase 2 — Plan validation
  ['v4a_scene_content_gen'],                           // Col 6: Phase 3 — Parallel content gen
  ['v4a_content_merge'],                               // Col 7: Phase 3 — Content merge
  ['v4a_asset_worker'],                                // Col 8: Phase 4 — Parallel asset gen
  ['v4a_asset_merge'],                                 // Col 9: Phase 4 — Asset merge
  ['v4a_blueprint_assembler'],                         // Col 10: Phase 5 — Blueprint assembly
]

const V4_ALGORITHM_FANOUT_STAGES = new Set([
  'v4a_scene_content_gen',
  'v4a_asset_worker',
])

// PhET Simulation Layout - For PhET-based interactive games
// Used when template is PHET_SIMULATION
const PHET_GRAPH_LAYOUT = [
  ['input_enhancer'],                    // Col 0: Entry point
  ['domain_knowledge_retriever'],        // Col 1: Domain knowledge
  ['router'],                            // Col 2: Template selection (routes to PhET)
  ['phet_simulation_selector'],          // Col 3: Select PhET simulation
  ['phet_assessment_designer'],          // Col 4: Design assessment tasks
  ['phet_game_planner'],                 // Col 5: Plan game mechanics
  ['phet_bridge_config_generator'],      // Col 6: Generate bridge config
  ['phet_blueprint_generator'],          // Col 7: Generate final blueprint
  ['blueprint_validator'],               // Col 8: Validation
]

// Agentic Sequential Layout - REDESIGNED 8 agents with max 3 tools each
// Merged input_enhancer + router → research_agent (template is fixed)
// Split blueprint_generator → blueprint_generator + output_renderer
// Used when preset is "preset_1_agentic_sequential"
const AGENTIC_SEQUENTIAL_GRAPH_LAYOUT = [
  ['research_agent'],                                 // Col 0: Question analysis + domain knowledge
  ['image_agent'],                                    // Col 1: Image pipeline (3 tools)
  ['game_planner'],                                   // Col 2: Plan mechanics
  ['scene_stage1_structure'],                         // Col 3: Scene structure
  ['scene_stage2_assets'],                            // Col 4: Scene assets
  ['scene_stage3_interactions'],                      // Col 5: Scene interactions
  ['blueprint_generator'],                            // Col 6: Blueprint creation (2 tools)
  ['output_renderer'],                                // Col 7: Diagram spec + SVG rendering
]

// Legacy Agentic Sequential Layout - 8 agents (for backwards compatibility)
const AGENTIC_SEQUENTIAL_GRAPH_LAYOUT_LEGACY = [
  ['input_enhancer'],                                 // Col 0: Entry + domain knowledge tool
  ['router'],                                         // Col 1: Router + image tools
  ['game_planner'],                                   // Col 2: Plan mechanics
  ['scene_stage1_structure'],                         // Col 3: Scene structure
  ['scene_stage2_assets'],                            // Col 4: Scene assets
  ['scene_stage3_interactions'],                      // Col 5: Scene interactions
  ['blueprint_generator'],                            // Col 6: Blueprint + validation/rendering tools
  ['playability_validator'],                          // Col 7: Final validation
]

// Category color scheme - each category has a distinct color
// This makes it easy to visually group agents by their function
export const CATEGORY_INFO: Record<string, {
  name: string
  description: string
  color: string
  nodeType?: 'agent' | 'decision' | 'orchestrator'
}> = {
  input: {
    name: 'Input Processing',
    description: 'Analyze and enhance input data',
    color: '#8B5CF6', // Purple
  },
  routing: {
    name: 'Routing',
    description: 'Decision making and path selection',
    color: '#10B981', // Green
  },
  decision: {
    name: 'Decision Node',
    description: 'Conditional routing based on state analysis',
    color: '#14B8A6', // Teal
    nodeType: 'decision',
  },
  orchestrator: {
    name: 'Orchestrator',
    description: 'Coordinates sub-agents and retry loops',
    color: '#7C3AED', // Violet
    nodeType: 'orchestrator',
  },
  image: {
    name: 'Image Processing',
    description: 'Retrieve, segment, and label images',
    color: '#06B6D4', // Cyan
  },
  generation: {
    name: 'Content Generation',
    description: 'Generate game content and code',
    color: '#F59E0B', // Amber
  },
  validation: {
    name: 'Validation',
    description: 'Validate and verify outputs',
    color: '#EF4444', // Red
  },
  output: {
    name: 'Output',
    description: 'Final asset packaging and rendering',
    color: '#6366F1', // Indigo
  },
  react: {
    name: 'ReAct Agent',
    description: 'Multi-step reasoning agents with tool calling',
    color: '#7C3AED', // Violet
  },
}

// Helper to get color for a category
const getCategoryColor = (category: string): string => {
  return CATEGORY_INFO[category]?.color || '#6B7280'
}

// =============================================================================
// FALLBACK Agent Metadata Registry
// =============================================================================
// This is a FALLBACK used only when the backend API is unavailable.
// The SINGLE SOURCE OF TRUTH is AGENT_METADATA_REGISTRY in:
//   backend/app/agents/instrumentation.py
//
// When the backend is available, metadata is fetched via:
//   GET /api/observability/graph/structure?topology=T1
//
// Colors are derived from CATEGORY_INFO based on the agent's category.
// =============================================================================
export const AGENT_METADATA: Record<string, {
  name: string
  description: string
  category: 'input' | 'routing' | 'image' | 'generation' | 'validation' | 'output' | 'react' | 'decision' | 'orchestrator' | 'asset'
  toolOrModel: string
  icon: string
  isDecisionNode?: boolean
  isOrchestrator?: boolean
}> = {
  input_enhancer: {
    name: 'Input Enhancer',
    description: "Analyzes question to extract Bloom's level, subject, and pedagogical context",
    category: 'input',
    toolOrModel: 'Qwen (Local)',
    icon: '📝'
  },
  domain_knowledge_retriever: {
    name: 'Domain Knowledge',
    description: 'Retrieves canonical labels and domain terms via web search',
    category: 'input',
    toolOrModel: 'Serper API + Qwen',
    icon: '🔍'
  },
  router: {
    name: 'Template Router',
    description: 'Selects optimal game template based on question type and pedagogy',
    category: 'routing',
    toolOrModel: 'Qwen (Local)',
    icon: '🔀'
  },
  game_planner: {
    name: 'Game Planner',
    description: 'Creates game mechanics, learning objectives, task structure, accessibility config, and event tracking',
    category: 'generation',
    toolOrModel: 'Qwen (Local)',
    icon: '🎮'
  },
  interaction_designer: {
    name: 'Interaction Designer',
    description: 'Designs custom interaction patterns based on Bloom\'s level, pedagogy, and content structure',
    category: 'generation',
    toolOrModel: 'LLM (configurable)',
    icon: '🎯'
  },
  interaction_validator: {
    name: 'Interaction Validator',
    description: 'Validates interaction design for playability, learning alignment, and technical feasibility',
    category: 'validation',
    toolOrModel: 'Rule-based + Patterns',
    icon: '✅'
  },
  scene_generator: {
    name: 'Scene Generator',
    description: 'Generates narrative context, visual themes, and scene descriptions (legacy)',
    category: 'generation',
    toolOrModel: 'LLM (configurable)',
    icon: '🎨'
  },
  scene_stage1_structure: {
    name: 'Scene Structure',
    description: 'Stage 1: Generates visual theme, layout type, and region definitions',
    category: 'generation',
    toolOrModel: 'Qwen (Local)',
    icon: '🏗️'
  },
  scene_stage2_assets: {
    name: 'Scene Assets',
    description: 'Stage 2: Generates detailed asset specifications for each region',
    category: 'generation',
    toolOrModel: 'Qwen (Local)',
    icon: '🎨'
  },
  scene_stage3_interactions: {
    name: 'Scene Interactions',
    description: 'Stage 3: Generates animations, behaviors, and state transitions',
    category: 'generation',
    toolOrModel: 'Qwen (Local)',
    icon: '🎬'
  },
  diagram_image_retriever: {
    name: 'Diagram Retriever',
    description: 'Searches for educational diagram images matching the topic',
    category: 'image',
    toolOrModel: 'Serper Image API',
    icon: '🖼️'
  },
  image_label_remover: {
    name: 'Label Remover',
    description: 'Removes existing text labels from diagram using inpainting',
    category: 'image',
    toolOrModel: 'Inpainting Service',
    icon: '🧹'
  },
  sam3_prompt_generator: {
    name: 'SAM3 Prompt Gen',
    description: 'Generates point/box prompts for SAM3 segmentation model',
    category: 'image',
    toolOrModel: 'LLM (VLM capable)',
    icon: '🎯'
  },
  diagram_image_segmenter: {
    name: 'Image Segmenter',
    description: 'Segments diagram into distinct zones using SAM3 or grid fallback',
    category: 'image',
    toolOrModel: 'SAM3 / Grid Fallback',
    icon: '✂️'
  },
  diagram_zone_labeler: {
    name: 'Zone Labeler',
    description: 'Labels each segmented zone using vision-language model',
    category: 'image',
    toolOrModel: 'VLM (LLaVA/Ollama)',
    icon: '🏷️'
  },
  qwen_annotation_detector: {
    name: 'Annotation Detector',
    description: 'Detects text labels and leader lines using EasyOCR + geometric inference',
    category: 'image',
    toolOrModel: 'EasyOCR + Geometric',
    icon: '🔍'
  },
  qwen_sam_zone_detector: {
    name: 'Zone Detector',
    description: 'Creates zones from leader line endpoints with optional SAM3 refinement',
    category: 'image',
    toolOrModel: 'Leader Lines + SAM3',
    icon: '🎯'
  },
  image_label_classifier: {
    name: 'Label Classifier',
    description: 'Classifies if diagram is labeled or unlabeled using EasyOCR + VLM',
    category: 'image',
    toolOrModel: 'EasyOCR + Qwen VL',
    icon: '🏷️'
  },
  direct_structure_locator: {
    name: 'Structure Locator',
    description: 'Directly locates structures in unlabeled diagrams using VLM',
    category: 'image',
    toolOrModel: 'Qwen VL + SAM3',
    icon: '📍'
  },
  // Hierarchical label diagram preset agents (Gemini pipeline)
  diagram_image_generator: {
    name: 'Diagram Generator',
    description: 'Generates clean educational diagrams using Gemini Imagen (nano-banana-pro)',
    category: 'image',
    toolOrModel: 'Gemini Imagen',
    icon: '🎨'
  },
  gemini_zone_detector: {
    name: 'Gemini Zone Detector',
    description: 'Detects zone positions using Gemini vision with hierarchical grouping',
    category: 'image',
    toolOrModel: 'Gemini 2.0 Flash',
    icon: '🔍'
  },
  // Advanced label diagram preset agents (Preset 2)
  diagram_type_classifier: {
    name: 'Diagram Type Classifier',
    description: 'Classifies diagram type (anatomy, flowchart, map, timeline, etc.) for optimal processing',
    category: 'input',
    toolOrModel: 'Gemini 2.0 Flash Lite',
    icon: '📊'
  },
  scene_sequencer: {
    name: 'Scene Sequencer',
    description: 'Plans multi-scene games with zoom-in, depth-first, or linear progressions',
    category: 'generation',
    toolOrModel: 'Gemini 2.0 Flash',
    icon: '🎬'
  },
  // Agentic game design agents
  diagram_analyzer: {
    name: 'Diagram Analyzer',
    description: 'Reasoning-based content analysis - determines optimal visualization strategy',
    category: 'input',
    toolOrModel: 'LLM (configurable)',
    icon: '🔬'
  },
  game_designer: {
    name: 'Game Designer',
    description: 'Unconstrained creative game designer — produces free-form GameDesign with scenes, interactions, and visual needs',
    category: 'generation',
    toolOrModel: 'LLM (configurable)',
    icon: '🎮'
  },
  design_interpreter: {
    name: 'Design Interpreter',
    description: 'Maps unconstrained GameDesign → structured GamePlan with classified mechanics, scene_breakdown, and workflow hints',
    category: 'generation',
    toolOrModel: 'LLM (configurable)',
    icon: '🔀'
  },
  multi_scene_image_orchestrator: {
    name: 'Multi-Scene Image Orchestrator',
    description: 'Orchestrates per-scene image generation and zone detection for multi-scene games (Preset 2)',
    category: 'orchestrator',
    toolOrModel: 'Gemini Imagen + Vision',
    icon: '🎬',
    isOrchestrator: true,
  },
  multi_scene_orchestrator: {
    name: 'Multi-Scene Orchestrator',
    description: 'Iterates through scenes to generate images and detect zones per-scene',
    category: 'orchestrator',
    toolOrModel: 'Orchestration',
    icon: '🎬',
    isOrchestrator: true,
  },
  blueprint_generator: {
    name: 'Blueprint Gen',
    description: 'Creates complete blueprint with zones, interactions, scoring, temporal constraints, accessibility specs, and event tracking',
    category: 'generation',
    toolOrModel: 'Gemini 3 Flash',
    icon: '📐'
  },
  blueprint_validator: {
    name: 'Blueprint Validator',
    description: 'Validates blueprint schema, semantics, and pedagogical alignment. Supports retry/escalate.',
    category: 'validation',
    toolOrModel: 'Gemini 2.5 Flash Lite',
    icon: '✅'
  },
  diagram_spec_generator: {
    name: 'Diagram Spec Gen',
    description: 'Generates SVG specification from zones, blueprint, and generated assets',
    category: 'generation',
    toolOrModel: 'Gemini 3 Flash',
    icon: '📋'
  },
  diagram_svg_generator: {
    name: 'SVG Generator',
    description: 'Renders final SVG diagram with complex SVG generation',
    category: 'output',
    toolOrModel: 'Gemini 3 Flash',
    icon: '🎨'
  },
  code_generator: {
    name: 'Code Generator',
    description: 'Generates React component code for stub templates',
    category: 'generation',
    toolOrModel: 'LLM (coding model)',
    icon: '💻'
  },
  code_verifier: {
    name: 'Code Verifier',
    description: 'Verifies generated code with TypeScript and ESLint',
    category: 'validation',
    toolOrModel: 'Docker Sandbox',
    icon: '🔍'
  },
  human_review: {
    name: 'Human Review',
    description: 'Checkpoint for manual review and approval',
    category: 'validation',
    toolOrModel: 'Manual Review',
    icon: '👤'
  },
  asset_planner: {
    name: 'Asset Planner',
    description: 'Plans all assets needed from scene data and zones (runs BEFORE blueprint).',
    category: 'generation',
    toolOrModel: 'Rule-based',
    icon: '📋'
  },
  asset_generator_orchestrator: {
    name: 'Asset Generator',
    description: 'Sequentially generates all planned assets using Gemini Imagen, with exponential backoff retry.',
    category: 'orchestrator',
    toolOrModel: 'Gemini 3 Flash + Imagen',
    icon: '🎨',
    isOrchestrator: true,
  },
  asset_validator: {
    name: 'Asset Validator',
    description: 'Validates all generated assets exist, have correct formats, and meet requirements.',
    category: 'validation',
    toolOrModel: 'Gemini 2.5 Flash Lite',
    icon: '✅'
  },

  // === PHASE 6: CONDITIONAL ROUTING NODES (Decision Nodes - Diamond Shape) ===
  check_post_scene_needs: {
    name: 'Post-Scene Check',
    description: 'Analyzes state to determine if asset pipeline is needed based on template type.',
    category: 'decision',
    toolOrModel: 'Rule-based',
    icon: '🔀',
    isDecisionNode: true,
  },
  check_post_blueprint_needs: {
    name: 'Post-Blueprint Check',
    description: 'Analyzes state to set routing flags for conditional post-blueprint processing.',
    category: 'decision',
    toolOrModel: 'Rule-based',
    icon: '🔀',
    isDecisionNode: true,
  },
  check_post_blueprint_route: {
    name: 'Blueprint Route',
    description: 'Routes to diagram spec or finalize based on template requirements.',
    category: 'decision',
    toolOrModel: 'Passthrough',
    icon: '🔀',
    isDecisionNode: true,
  },
  check_diagram_spec_route: {
    name: 'Spec Route',
    description: 'Routes to diagram spec generator or template check based on needs.',
    category: 'decision',
    toolOrModel: 'Passthrough',
    icon: '🔀',
    isDecisionNode: true,
  },
  check_multi_scene: {
    name: 'Multi-Scene Check',
    description: 'Determines if game requires multiple scenes based on scene sequencer output.',
    category: 'decision',
    toolOrModel: 'Rule-based',
    icon: '🔀',
    isDecisionNode: true,
  },
  check_diagram_image: {
    name: 'Diagram Image Check',
    description: 'Determines if diagram image pipeline is needed based on template type.',
    category: 'decision',
    toolOrModel: 'Rule-based',
    icon: '🔀',
    isDecisionNode: true,
  },

  // === REDESIGNED Agentic Sequential Agents (8 agents, max 3 tools each) ===
  research_agent: {
    name: 'Research Agent',
    description: 'Merged agent for question analysis and domain knowledge retrieval. Template is fixed to INTERACTIVE_DIAGRAM.',
    category: 'input',
    toolOrModel: 'LLM + 2 Tools',
    icon: '🔬'
  },
  image_agent: {
    name: 'Image Agent',
    description: 'Dedicated image pipeline: retrieval, generation, and zone detection.',
    category: 'image',
    toolOrModel: 'LLM + 3 Tools',
    icon: '🖼️'
  },
  output_renderer: {
    name: 'Output Renderer',
    description: 'Final rendering: diagram spec generation and SVG output. Split from blueprint_generator.',
    category: 'output',
    toolOrModel: 'LLM + 2 Tools',
    icon: '🎨'
  },
  playability_validator: {
    name: 'Playability Validator',
    description: 'Validates game playability and educational alignment.',
    category: 'validation',
    toolOrModel: 'Rule-based',
    icon: '✅'
  },

  // === REDESIGNED ReAct Agents (4 agents, max 5 tools each) ===
  research_image_agent: {
    name: 'Research & Image',
    description: 'Multi-step reasoning for question analysis, domain knowledge, and image acquisition. Template fixed to INTERACTIVE_DIAGRAM.',
    category: 'react',
    toolOrModel: 'ReAct + 5 Tools',
    icon: '🔬'
  },
  blueprint_agent: {
    name: 'Blueprint Agent',
    description: 'Focused blueprint creation with validation and auto-fix. Reduced tool count for quality.',
    category: 'react',
    toolOrModel: 'ReAct + 3 Tools',
    icon: '📐'
  },
  asset_render_agent: {
    name: 'Asset & Render',
    description: 'Asset generation, diagram spec, and SVG rendering. Split from blueprint_asset_agent.',
    category: 'react',
    toolOrModel: 'ReAct + 4 Tools',
    icon: '🎨'
  },

  // === LEGACY ReAct Agents (3 agents - NOT RECOMMENDED for production) ===
  research_routing_agent: {
    name: 'Research & Routing (Legacy)',
    description: 'LEGACY: Multi-step reasoning agent. Use research_image_agent instead.',
    category: 'react',
    toolOrModel: 'ReAct + 6 Tools',
    icon: '🔬'
  },
  game_design_agent: {
    name: 'Game Design',
    description: 'Multi-step reasoning agent for game mechanics planning, scene structure, asset population, and interaction design.',
    category: 'react',
    toolOrModel: 'ReAct + 5 Tools',
    icon: '🎮'
  },
  blueprint_asset_agent: {
    name: 'Blueprint & Assets (Legacy)',
    description: 'LEGACY: 10 tools causes 20-40% quality degradation. Use blueprint_agent + asset_render_agent instead.',
    category: 'react',
    toolOrModel: 'ReAct + 10 Tools',
    icon: '📐'
  },

  // === HAD (Hierarchical Agentic DAG) Orchestrator Agents ===
  zone_planner: {
    name: 'Zone Planner',
    description: 'HAD v3 Vision Cluster: Gemini vision for polygon zone detection with accessibility specs. Supports multi-scene detection.',
    category: 'orchestrator',
    toolOrModel: 'Gemini 2.5 Flash (Vision)',
    icon: '🔬',
    isOrchestrator: true,
  },
  game_orchestrator: {
    name: 'Game Orchestrator',
    description: 'HAD Legacy: Sequential design with accessibility, event tracking, and undo/redo config. Replaced by game_designer in HAD v3.',
    category: 'orchestrator',
    toolOrModel: 'Orchestrator + 4 Tools',
    icon: '🎮',
    isOrchestrator: true,
  },
  output_orchestrator: {
    name: 'Output Orchestrator',
    description: 'HAD Output Cluster: Blueprint generation with validation retry loop (max 3), diagram spec, and SVG rendering.',
    category: 'orchestrator',
    toolOrModel: 'Orchestrator + Validation',
    icon: '📐',
    isOrchestrator: true,
  },

  // === V3 Pipeline Agents (5-phase ReAct architecture) ===
  game_designer_v3: {
    name: 'Game Designer v3',
    description: 'ReAct agent — designs game concept, mechanics, scenes, labels (5 tools incl. submit)',
    category: 'generation',
    toolOrModel: 'ReAct (Gemini Pro)',
    icon: '🎮',
  },
  design_validator: {
    name: 'Design Validator',
    description: 'Deterministic validation of GameDesignV3 — schema, labels, hierarchy, mechanics, transitions',
    category: 'validation',
    toolOrModel: 'Rule-based (no LLM)',
    icon: '✓',
  },
  scene_architect_v3: {
    name: 'Scene Architect v3',
    description: 'ReAct agent — designs per-scene zone layout, mechanic configs, image requirements (4 tools)',
    category: 'generation',
    toolOrModel: 'ReAct (Gemini Flash)',
    icon: '🏗️',
  },
  scene_validator: {
    name: 'Scene Validator',
    description: 'Cross-stage contract validation of scene specs against game design',
    category: 'validation',
    toolOrModel: 'Rule-based (no LLM)',
    icon: '✓',
  },
  interaction_designer_v3: {
    name: 'Interaction Designer v3',
    description: 'ReAct agent — designs scoring, feedback, misconceptions, animations, transitions (4 tools)',
    category: 'generation',
    toolOrModel: 'ReAct (Gemini Flash)',
    icon: '🎯',
  },
  asset_generator_v3: {
    name: 'Asset Generator v3',
    description: 'ReAct agent — searches/generates diagram images, detects zones, generates animations (5 tools)',
    category: 'generation',
    toolOrModel: 'ReAct (Gemini Flash)',
    icon: '🖼️',
  },
  blueprint_assembler_v3: {
    name: 'Blueprint Assembler v3',
    description: 'ReAct agent — assembles, validates, and repairs frontend-ready blueprint (4 tools)',
    category: 'output',
    toolOrModel: 'ReAct (Gemini Flash)',
    icon: '🧩',
  },
  // Legacy v3 agents (kept for backward compat in older runs)
  asset_spec_builder: {
    name: 'Asset Spec Builder',
    description: 'Builds AssetManifest from GameDesignV3 + AssetGraph (legacy)',
    category: 'generation',
    toolOrModel: 'Deterministic',
    icon: '📋',
  },
  asset_orchestrator_v3: {
    name: 'Asset Orchestrator v3',
    description: 'Dispatches asset generation workers from AssetManifest (legacy)',
    category: 'orchestrator',
    toolOrModel: 'Worker Dispatch',
    icon: '🏭',
    isOrchestrator: true,
  },

  // === V4 Pipeline Agents (streamlined 5-phase architecture) ===
  v4_input_analyzer: {
    name: 'Input Analyzer',
    description: 'Extracts pedagogical context: Bloom\'s level, difficulty, key concepts, misconceptions',
    category: 'input',
    toolOrModel: 'Gemini 2.5 Flash',
    icon: '📝',
  },
  v4_dk_retriever: {
    name: 'Domain Knowledge Retriever',
    description: 'Gathers canonical labels, descriptions, sequences, comparisons via search + LLM',
    category: 'input',
    toolOrModel: 'Gemini 2.5 Flash + Serper',
    icon: '🔬',
  },
  v4_phase0_merge: {
    name: 'Context Merge',
    description: 'Synchronization barrier — joins parallel context gathering results',
    category: 'routing',
    toolOrModel: 'Deterministic',
    icon: '🔀',
  },
  v4_game_concept_designer: {
    name: 'Game Concept Designer',
    description: 'Designs initial game concept: title, theme, scene breakdown, mechanic assignments',
    category: 'generation',
    toolOrModel: 'Gemini 2.5 Pro',
    icon: '🎮',
  },
  v4_concept_validator: {
    name: 'Concept Validator',
    description: 'Validates game concept structure, scene consistency, and mechanic feasibility',
    category: 'validation',
    toolOrModel: 'Deterministic',
    icon: '✓',
  },
  v4_scene_design_send: {
    name: 'Scene Design Dispatch',
    description: 'Fan-out: sends each scene for parallel creative design via LangGraph Send API',
    category: 'routing',
    toolOrModel: 'Send API',
    icon: '📤',
  },
  v4_scene_design_merge: {
    name: 'Scene Design Merge',
    description: 'Collects parallel scene design results into unified scene list',
    category: 'routing',
    toolOrModel: 'Deterministic',
    icon: '📥',
  },
  v4_graph_builder: {
    name: 'Graph Builder',
    description: 'Constructs final game plan graph: scenes, mechanics, zone labels, content briefs',
    category: 'generation',
    toolOrModel: 'Deterministic',
    icon: '🏗️',
  },
  v4_game_plan_validator: {
    name: 'Game Plan Validator',
    description: 'Validates structure, label integrity, mechanic types; computes max_score fields',
    category: 'validation',
    toolOrModel: 'Deterministic',
    icon: '✓',
  },
  v4_content_dispatch: {
    name: 'Content Dispatch',
    description: 'Fan-out: sends each mechanic for parallel content generation via Send API',
    category: 'routing',
    toolOrModel: 'Send API',
    icon: '📤',
  },
  v4_content_merge: {
    name: 'Content Merge',
    description: 'Collects parallel mechanic content results into unified content list',
    category: 'routing',
    toolOrModel: 'Deterministic',
    icon: '📥',
  },
  v4_item_asset_worker: {
    name: 'Item Asset Worker',
    description: 'Enriches content items with image URLs from image_description fields',
    category: 'asset',
    toolOrModel: 'Serper Image API',
    icon: '🖼️',
  },
  v4_interaction_merge: {
    name: 'Interaction Merge',
    description: 'Collects interaction design results (scoring, feedback, transitions) per scene',
    category: 'routing',
    toolOrModel: 'Deterministic',
    icon: '📥',
  },
  v4_content_builder: {
    name: 'Content Builder',
    description: 'Generates mechanic content (8 types) + interaction designs (scoring, feedback, transitions)',
    category: 'generation',
    toolOrModel: 'Gemini 2.5 Pro/Flash',
    icon: '📦',
  },
  v4_asset_worker: {
    name: 'Asset Worker',
    description: 'Searches diagram images, detects zones via Gemini vision (parallel via Send API)',
    category: 'generation',
    toolOrModel: 'Gemini 2.5 Flash + Image Search',
    icon: '🖼️',
  },
  v4_asset_merge: {
    name: 'Asset Merge',
    description: 'Deduplicates asset results by scene_id from parallel workers',
    category: 'routing',
    toolOrModel: 'Deterministic',
    icon: '🔀',
  },
  v4_assembler: {
    name: 'Blueprint Assembler',
    description: 'Assembles InteractiveDiagramBlueprint from game plan, content, and assets. 100% deterministic.',
    category: 'output',
    toolOrModel: 'Deterministic',
    icon: '🧩',
  },

  // === V4 Algorithm Pipeline Agents ===
  v4a_dk_retriever: {
    name: 'Algorithm DK Retriever',
    description: 'Gathers algorithm-specific domain knowledge: pseudocode, complexity, common bugs, examples',
    category: 'input',
    toolOrModel: 'Gemini 2.5 Flash + Serper',
    icon: '🔬',
  },
  v4a_game_concept_designer: {
    name: 'Algorithm Concept Designer',
    description: 'Designs multi-scene algorithm game with Bloom\'s-aligned progression across 5 game types',
    category: 'generation',
    toolOrModel: 'Gemini 2.5 Pro',
    icon: '🎮',
  },
  v4a_concept_validator: {
    name: 'Algorithm Concept Validator',
    description: 'Validates algorithm game concept: scene count, game types, difficulty progression',
    category: 'validation',
    toolOrModel: 'Deterministic',
    icon: '✓',
  },
  v4a_graph_builder: {
    name: 'Algorithm Graph Builder',
    description: 'Assigns scene IDs, computes max scores, determines asset needs, builds transitions',
    category: 'generation',
    toolOrModel: 'Deterministic',
    icon: '🏗️',
  },
  v4a_plan_validator: {
    name: 'Algorithm Plan Validator',
    description: 'Validates algorithm game plan: unique IDs, valid game types, score consistency',
    category: 'validation',
    toolOrModel: 'Deterministic',
    icon: '✓',
  },
  v4a_scene_content_gen: {
    name: 'Scene Content Generator',
    description: 'Generates per-scene game content (state tracer steps, bug rounds, Parsons blocks, etc.)',
    category: 'generation',
    toolOrModel: 'Gemini 2.5 Pro',
    icon: '📦',
  },
  v4a_content_merge: {
    name: 'Content Merge',
    description: 'Merges parallel scene content results, deduplicates by scene_id',
    category: 'routing',
    toolOrModel: 'Deterministic',
    icon: '📥',
  },
  v4a_asset_worker: {
    name: 'Algorithm Asset Worker',
    description: 'Generates visual assets per scene via image retrieval or Nanobanana AI',
    category: 'asset',
    toolOrModel: 'Nanobanana + Image Search',
    icon: '🖼️',
  },
  v4a_asset_merge: {
    name: 'Asset Merge',
    description: 'Merges parallel scene asset results, deduplicates by scene_id',
    category: 'routing',
    toolOrModel: 'Deterministic',
    icon: '🔀',
  },
  v4a_blueprint_assembler: {
    name: 'Algorithm Blueprint Assembler',
    description: 'Assembles AlgorithmGameBlueprint from game plan, scene contents, and assets',
    category: 'output',
    toolOrModel: 'Deterministic',
    icon: '🧩',
  },

  // === PhET Simulation Agents ===
  phet_simulation_selector: {
    name: 'PhET Simulation Selector',
    description: 'Selects appropriate PhET simulation for the question based on domain knowledge and pedagogical context',
    category: 'routing',
    toolOrModel: 'LLM (configurable)',
    icon: '🔬'
  },
  phet_assessment_designer: {
    name: 'PhET Assessment Designer',
    description: 'Designs assessment tasks using simulation capabilities and learning objectives',
    category: 'generation',
    toolOrModel: 'LLM (configurable)',
    icon: '📝'
  },
  phet_game_planner: {
    name: 'PhET Game Planner',
    description: 'Plans game mechanics, interaction flow, and feedback strategy for PhET-based games',
    category: 'generation',
    toolOrModel: 'LLM (configurable)',
    icon: '🎯'
  },
  phet_bridge_config_generator: {
    name: 'PhET Bridge Config',
    description: 'Generates bridge configuration for simulation integration including parameter mappings and event handlers',
    category: 'generation',
    toolOrModel: 'LLM (configurable)',
    icon: '🔗'
  },
  phet_blueprint_generator: {
    name: 'PhET Blueprint Gen',
    description: 'Generates final blueprint for PhET simulation game with validation',
    category: 'generation',
    toolOrModel: 'LLM (configurable)',
    icon: '📋'
  },
}

// Helper to get agent color (from category)
export const getAgentColor = (agentId: string): string => {
  const agent = AGENT_METADATA[agentId]
  return agent ? getCategoryColor(agent.category) : '#6B7280'
}

// Helper to get agent metadata with dynamic fallback
// Prefers metadata from GraphStructure (backend) over static AGENT_METADATA
export function getAgentMetadataWithFallback(
  agentId: string,
  graphStructure: GraphStructure | null
): {
  name: string
  description: string
  category: string
  toolOrModel: string
  icon: string
  isFromBackend: boolean
  isDecisionNode?: boolean
  isOrchestrator?: boolean
} {
  // Try to get from dynamic graph structure first (backend is source of truth)
  if (graphStructure?.nodes) {
    const graphNode = graphStructure.nodes.find(n => n.id === agentId)
    if (graphNode) {
      // Check if this is a decision or orchestrator node based on category or name
      const isDecision = graphNode.category === 'decision' ||
                         graphNode.category === 'routing' ||
                         agentId.startsWith('check_')
      const isOrchestrator = graphNode.category === 'orchestrator' ||
                              agentId.includes('orchestrator') ||
                              agentId === 'zone_planner'
      return {
        name: graphNode.name,
        description: graphNode.description,
        category: graphNode.category,
        toolOrModel: graphNode.toolOrModel,
        icon: graphNode.icon,
        isFromBackend: true,
        isDecisionNode: isDecision,
        isOrchestrator: isOrchestrator,
      }
    }
  }

  // Fall back to static AGENT_METADATA
  const staticMeta = AGENT_METADATA[agentId]
  if (staticMeta) {
    return {
      ...staticMeta,
      isFromBackend: false
    }
  }

  // Ultimate fallback for unknown agents - check name patterns
  const isDecision = agentId.startsWith('check_') || agentId.includes('route')
  const isOrchestrator = agentId.includes('orchestrator')

  return {
    name: agentId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    description: `Agent: ${agentId}`,
    category: isDecision ? 'decision' : isOrchestrator ? 'orchestrator' : 'generation',
    toolOrModel: 'Unknown',
    icon: isDecision ? '🔀' : isOrchestrator ? '🔄' : '🔧',
    isFromBackend: false,
    isDecisionNode: isDecision,
    isOrchestrator: isOrchestrator,
  }
}

// Backward compatibility alias (without color field - use getAgentColor instead)
const AGENT_INFO = AGENT_METADATA

// Helper to format stage names for display
function formatStageName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function PipelineView({ run, stages, onRetry, compact = false, onSelectStage: externalOnSelectStage }: PipelineViewProps) {
  const [selectedStageInternal, setSelectedStageInternal] = useState<StageExecution | null>(null)
  // Use external handler if provided, otherwise use internal state
  const selectedStage = externalOnSelectStage ? selectedStageInternal : selectedStageInternal
  const setSelectedStage = (stage: StageExecution | null) => {
    setSelectedStageInternal(stage)
    externalOnSelectStage?.(stage)
  }
  const [viewMode, setViewMode] = useState<'graph' | 'timeline' | 'cluster'>('graph') // Default to graph view

  // Dynamic graph structure from backend
  const [graphStructure, setGraphStructure] = useState<GraphStructure | null>(null)
  const [executionPath, setExecutionPath] = useState<ExecutionPath | null>(null)
  const [graphLoading, setGraphLoading] = useState(true)
  const [graphError, setGraphError] = useState<string | null>(null)

  // Detect if this is a HAD (Hierarchical Agentic DAG) run by checking for HAD-specific orchestrator agents
  // NOTE: Only trigger for runs that use the actual HAD 4-cluster architecture, not just any run with game_designer
  const isHADRun = useMemo(() => {
    // These are the HAD-specific orchestrators that indicate a true HAD run
    // game_designer alone is NOT enough - it's used in multiple presets
    const hadOrchestratorAgents = ['zone_planner', 'game_orchestrator', 'output_orchestrator']
    // Check if any stages are HAD orchestrators (need at least 2 to be a real HAD run)
    const hadStageCount = stages.filter(s => hadOrchestratorAgents.includes(s.stage_name)).length
    // Or check graph structure for HAD nodes
    const hadNodeCount = graphStructure?.nodes?.filter(n => hadOrchestratorAgents.includes(n.id)).length || 0
    // Require at least 2 HAD orchestrators to trigger cluster view
    return hadStageCount >= 2 || hadNodeCount >= 2
  }, [stages, graphStructure])

  // Auto-switch to cluster view for HAD runs (only on initial load when stages appear)
  useEffect(() => {
    if (isHADRun && stages.length > 0 && viewMode === 'graph') {
      setViewMode('cluster')
    }
  }, [isHADRun, stages.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // Cast run to extended type if it has totals
  const runWithTotals = run as PipelineRunWithTotals

  // Fetch graph structure from backend
  useEffect(() => {
    const fetchGraphStructure = async () => {
      try {
        setGraphLoading(true)
        setGraphError(null)

        // Fetch graph structure
        const graphResponse = await fetch(`/api/observability/graph/structure?topology=${run.topology || 'T1'}`)
        if (graphResponse.ok) {
          const graphData = await graphResponse.json()
          setGraphStructure(graphData)
        } else {
          console.warn('[PipelineView] Could not fetch graph structure, using fallback')
          setGraphError('Could not load graph structure')
        }
      } catch (err) {
        console.error('[PipelineView] Error fetching graph structure:', err)
        setGraphError('Error loading graph structure')
      } finally {
        setGraphLoading(false)
      }
    }

    fetchGraphStructure()
  }, [run.topology])

  // Fetch execution path for this run
  useEffect(() => {
    const fetchExecutionPath = async () => {
      if (!run.id) return

      try {
        const pathResponse = await fetch(`/api/observability/runs/${run.id}/execution-path`)
        if (pathResponse.ok) {
          const pathData = await pathResponse.json()
          setExecutionPath(pathData)
        }
      } catch (err) {
        console.error('[PipelineView] Error fetching execution path:', err)
      }
    }

    // Fetch immediately and on status change
    fetchExecutionPath()

    // Poll for execution path updates when running
    if (run.status === 'running') {
      const interval = setInterval(fetchExecutionPath, 2000)
      return () => clearInterval(interval)
    }
  }, [run.id, run.status, stages.length])

  // Create a map of stage statuses (last-write-wins for node color/status)
  // and a separate map for all executions (for fan-out rendering)
  const stageStatusMap = useMemo(() => {
    const map: Record<string, StageExecution> = {}
    stages.forEach(stage => {
      map[stage.stage_name] = stage
    })

    // If no stages but run is complete, infer status from run status
    if (stages.length === 0 && run.status === 'success') {
      console.warn('[PipelineView] Run completed successfully but no stages recorded. This indicates a backend instrumentation issue.')
    }

    return map
  }, [stages, run.status])

  // Group all executions per stage name (for fan-out workers)
  const stageExecutions = useMemo(() => {
    const map: Record<string, StageExecution[]> = {}
    stages.forEach(stage => {
      if (!map[stage.stage_name]) map[stage.stage_name] = []
      map[stage.stage_name].push(stage)
    })
    return map
  }, [stages])

  // Create unified status resolution context
  // See @/lib/stageStatus.ts for detailed reasoning on resolution priority
  const statusResolutionContext: StatusResolutionContext = useMemo(() => ({
    stageStatusMap,
    executionPath,
    runStatus: run.status,
    isRunning: run.status === 'running'
  }), [stageStatusMap, executionPath, run.status])

  // Create a memoized status resolver for efficient lookups
  const resolveStatus = useMemo(() =>
    createStatusResolver(statusResolutionContext),
    [statusResolutionContext]
  )

  const handleRetry = async (stageName: string) => {
    if (onRetry) {
      try {
        await onRetry(run.id, stageName)
      } catch (err) {
        // Re-throw so StagePanel can catch and display it
        throw err
      }
    }
  }

  return (
    <div className={externalOnSelectStage ? "flex flex-col" : "flex h-full"}>
      {/* Main content */}
      <div className={externalOnSelectStage ? "" : "flex-1 flex flex-col"}>
        {/* View mode toggle */}
        <div className="flex items-center justify-between p-3 border-b bg-gray-50">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">View:</span>
            <div className="flex rounded-lg overflow-hidden border">
              <button
                onClick={() => setViewMode('timeline')}
                className={`px-3 py-1 text-sm ${
                  viewMode === 'timeline'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                Timeline
              </button>
              <button
                onClick={() => setViewMode('graph')}
                className={`px-3 py-1 text-sm ${
                  viewMode === 'graph'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                Graph
              </button>
              {/* Cluster view button - only show for HAD runs */}
              {isHADRun && (
                <button
                  onClick={() => setViewMode('cluster')}
                  className={`px-3 py-1 text-sm ${
                    viewMode === 'cluster'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  Clusters
                </button>
              )}
            </div>
          </div>

          {/* Summary stats */}
          <div className="flex items-center gap-4 text-sm">
            {/* Cost & tokens from execution path or run totals */}
            {(executionPath?.totals || runWithTotals.total_cost_usd !== undefined) && (
              <>
                <span className="text-green-600 font-medium" title="Total cost for this run">
                  💰 ${(executionPath?.totals?.totalCost ?? runWithTotals.total_cost_usd ?? 0).toFixed(4)}
                </span>
                <span className="text-blue-600 font-medium" title="Total tokens used">
                  📊 {((executionPath?.totals?.totalTokens ?? runWithTotals.total_tokens ?? 0)).toLocaleString()} tokens
                </span>
              </>
            )}
            {/* Retry count if any */}
            {(executionPath?.totals?.retryCount ?? runWithTotals.total_retries ?? 0) > 0 && (
              <span className="text-orange-600 font-medium" title="Total retries across all stages">
                🔄 {executionPath?.totals?.retryCount ?? runWithTotals.total_retries} retries
              </span>
            )}
            {/* Stage progress */}
            <span className="text-gray-500">
              {(() => {
                // Use active layout's node count for specialized pipelines, fallback to graph structure
                const preset = (run.config_snapshot?.pipeline_preset as string || '').toLowerCase()
                const layoutForCount = preset === 'v4' ? V4_GRAPH_LAYOUT
                  : preset === 'v4_algorithm' ? V4_ALGORITHM_GRAPH_LAYOUT
                  : preset === 'v3' ? V3_GRAPH_LAYOUT
                  : preset === 'had' ? HAD_GRAPH_LAYOUT
                  : preset.includes('react') ? REACT_GRAPH_LAYOUT
                  : null
                const expectedStageCount = layoutForCount
                  ? layoutForCount.flat().length
                  : (graphStructure?.nodes?.filter(n => n.id !== 'human_review').length
                    ?? GRAPH_LAYOUT.flat().filter((a: string) => a !== 'human_review').length)
                const completedCount = stages.filter(s => s.status === 'success' || s.status === 'degraded').length
                const failedCount = stages.filter(s => s.status === 'failed').length
                const runningCount = stages.filter(s => s.status === 'running').length
                // Show at least 1 running when pipeline is active but stages array not yet populated
                const displayRunningCount = run.status === 'running' && runningCount === 0 && stages.length > 0 ? 1 : runningCount

                if (run.status === 'running') {
                  if (stages.length === 0) {
                    return 'Pipeline starting...'
                  }
                  return `${completedCount}/${expectedStageCount} stages (${displayRunningCount > 0 ? displayRunningCount + ' running' : 'processing'})`
                }
                if (run.status === 'success') {
                  // Use unique stage names from actual execution (handles retries/Send API duplicates)
                  const uniqueExecutedCount = new Set(stages.map(s => s.stage_name)).size
                  return `${completedCount}/${executionPath?.totals?.uniqueStages ?? uniqueExecutedCount} stages completed`
                }
                if (run.status === 'failed') {
                  return `${completedCount}/${expectedStageCount} stages (${failedCount} failed)`
                }
                return stages.length > 0
                  ? `${completedCount}/${expectedStageCount} stages`
                  : 'No stages executed yet'
              })()}
            </span>
            {run.duration_ms && (
              <span className="text-gray-500">
                ⏱️ {run.duration_ms < 1000
                  ? `${run.duration_ms}ms`
                  : run.duration_ms < 60000
                    ? `${(run.duration_ms / 1000).toFixed(1)}s`
                    : `${Math.floor(run.duration_ms / 60000)}m ${Math.floor((run.duration_ms % 60000) / 1000)}s`}
              </span>
            )}
          </div>
        </div>

        {/* Human Review Banner - shows when pipeline is awaiting review */}
        {(() => {
          const humanReviewStage = stages.find(s => s.stage_name === 'human_review' && s.status === 'success')
          const failedStage = stages.find(s => s.status === 'failed')
          const isAwaitingReview = run.status === 'failed' && (humanReviewStage || failedStage)

          if (!isAwaitingReview) return null

          const reviewStage = humanReviewStage || failedStage

          return (
            <div className="mx-4 mt-4 bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0 animate-pulse">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </div>

                {/* Content */}
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-purple-800 flex items-center gap-2">
                    Manual Review Required
                    <span className="text-xs bg-purple-200 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                      Action Needed
                    </span>
                  </h3>
                  <p className="text-sm text-purple-700 mt-1">
                    The pipeline has paused at <strong>{reviewStage ? formatStageName(reviewStage.stage_name) : 'validation'}</strong> and requires your review.
                    {failedStage?.validation_errors && failedStage.validation_errors.length > 0 && (
                      <span className="block mt-1 text-red-600">
                        {failedStage.validation_errors.length} validation error{failedStage.validation_errors.length > 1 ? 's' : ''} detected.
                      </span>
                    )}
                  </p>

                  {/* Action buttons */}
                  <div className="flex items-center gap-3 mt-3">
                    <button
                      onClick={() => {
                        if (reviewStage) {
                          setSelectedStage(reviewStage)
                        }
                      }}
                      className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors flex items-center gap-2 shadow-sm"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      Review Details
                    </button>
                    {onRetry && reviewStage && (
                      <button
                        onClick={() => handleRetry(reviewStage.stage_name)}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors flex items-center gap-2 shadow-sm"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Retry & Continue
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        })()}

        {/* Content area */}
        <div className={externalOnSelectStage ? "p-4" : "flex-1 overflow-auto p-4"}>
          {viewMode === 'timeline' ? (
            <TimelineView
              run={run}
              stages={stages}
              selectedStage={selectedStage}
              onSelectStage={setSelectedStage}
              graphStructure={graphStructure}
              executionPath={executionPath}
              stageStatusMap={stageStatusMap}
            />
          ) : viewMode === 'cluster' ? (
            <HADClusterView
              stages={stages}
              selectedStageName={selectedStage?.stage_name}
              onSelectStage={(stage) => setSelectedStage(stage)}
            />
          ) : (
            <GraphView
              run={run}
              stageStatusMap={stageStatusMap}
              stageExecutions={stageExecutions}
              selectedStage={selectedStage}
              graphStructure={graphStructure}
              executionPath={executionPath}
              graphLoading={graphLoading}
              onSelectStage={(stageName) => {
                // Handle fan-out execution selection (e.g. "v4_asset_worker::fanout::2")
                if (stageName.includes('::fanout::')) {
                  const [parentId, , indexStr] = stageName.split('::')
                  const execIdx = parseInt(indexStr, 10)
                  const executions = stageExecutions[parentId] || []
                  if (executions[execIdx]) {
                    setSelectedStage(executions[execIdx])
                    return
                  }
                }
                // Handle sub-stage selection (e.g. "v4_content_builder::sub::content_drag_drop_scene_1")
                if (stageName.includes('::sub::')) {
                  const [parentId, , subId] = stageName.split('::')
                  const parentStage = stageStatusMap[parentId]
                  const subStages = parentStage?.output_snapshot?._sub_stages as Array<Record<string, unknown>> | undefined
                  const subStage = subStages?.find((s: Record<string, unknown>) => s.id === subId)
                  if (subStage && parentStage) {
                    // Build output_snapshot with full content + attempts metadata
                    const outputSnapshot = {
                      ...(subStage.output_summary as Record<string, unknown> || {}),
                      _attempts: subStage.attempts as Array<Record<string, unknown>> | undefined,
                      _sub_stage_type: subStage.type as string | undefined,
                      _mechanic_type: subStage.mechanic_type as string | undefined,
                      _scene_id: subStage.scene_id as string | undefined,
                      _prompt_preview: subStage.prompt_preview as string | undefined,
                      _response_preview: subStage.response_preview as string | undefined,
                    }
                    setSelectedStage({
                      id: stageName,
                      stage_name: `${parentId}::${(subStage.name as string) || subId}`,
                      stage_order: parentStage.stage_order,
                      status: (subStage.status as string) === 'success' ? 'success' : (subStage.status as string) === 'failed' ? 'failed' : 'degraded',
                      started_at: parentStage.started_at,
                      finished_at: parentStage.finished_at,
                      duration_ms: (subStage.duration_ms as number) || null,
                      model_id: (subStage.model as string) || parentStage.model_id,
                      prompt_tokens: null,
                      completion_tokens: null,
                      total_tokens: null,
                      estimated_cost_usd: null,
                      latency_ms: (subStage.duration_ms as number) || null,
                      error_message: (subStage.error as string) || null,
                      retry_count: ((subStage.attempt as number) || 1) - 1,
                      validation_passed: (subStage.validation_passed as boolean) ?? null,
                      validation_score: null,
                      output_snapshot: outputSnapshot,
                      input_snapshot: subStage.input_summary as Record<string, unknown> || {},
                      run_id: parentStage.run_id,  // Inherit run_id for logs/tools API access
                    })
                    return
                  }
                }

                const stage = stageStatusMap[stageName]
                if (stage) {
                  // Stage has been executed - show full details
                  setSelectedStage(stage)
                } else {
                  // Stage hasn't run yet or wasn't recorded - use unified status resolver
                  const statusResult = resolveStatus(stageName)
                  setSelectedStage({
                    id: statusResult.isInferred ? `inferred-${stageName}` : `pending-${stageName}`,
                    stage_name: stageName,
                    stage_order: 999,
                    status: statusResult.status,
                    started_at: null,
                    finished_at: null,
                    duration_ms: null,
                    model_id: null,
                    prompt_tokens: null,
                    completion_tokens: null,
                    total_tokens: null,
                    estimated_cost_usd: null,
                    latency_ms: null,
                    error_message: null,
                    retry_count: 0,
                    validation_passed: null,
                    validation_score: null,
                  })
                }
              }}
            />
          )}
        </div>
      </div>

      {/* Stage detail panel — only show sidebar when NOT using external handler */}
      {!externalOnSelectStage && selectedStage && (
        <StagePanel
          stage={{ ...selectedStage, run_id: run.id }}
          onRetry={
            // Enable retry for failed, degraded (fallback used), or human_review stages
            (selectedStage.status === 'failed' || selectedStage.status === 'degraded' || selectedStage.stage_name === 'human_review')
              ? handleRetry
              : undefined
          }
          onClose={() => setSelectedStage(null)}
        />
      )}
    </div>
  )
}

// HAD Cluster view - groups stages by cluster for HAD architecture visualization
function HADClusterView({
  stages,
  selectedStageName,
  onSelectStage,
}: {
  stages: StageExecution[]
  selectedStageName?: string
  onSelectStage: (stage: StageExecution) => void
}) {
  const [expandedClusters, setExpandedClusters] = useState<Record<string, boolean>>(() => {
    // Start with all clusters expanded
    return HAD_CLUSTER_LAYOUT.reduce((acc, cluster) => {
      acc[cluster.id] = true
      return acc
    }, {} as Record<string, boolean>)
  })

  const toggleCluster = (clusterId: string) => {
    setExpandedClusters(prev => ({
      ...prev,
      [clusterId]: !prev[clusterId],
    }))
  }

  return (
    <div className="max-w-4xl mx-auto py-6 space-y-4">
      {/* HAD Architecture Header */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-4 border border-purple-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-purple-900">Hierarchical Agentic DAG (HAD)</h3>
            <p className="text-sm text-purple-700">
              Hybrid architecture with orchestrator agents coordinating specialized clusters
            </p>
          </div>
        </div>
      </div>

      {/* Clusters */}
      {HAD_CLUSTER_LAYOUT.map((cluster) => (
        <ClusterView
          key={cluster.id}
          cluster={cluster}
          stages={stages}
          onSelectStage={onSelectStage}
          selectedStageName={selectedStageName}
          isExpanded={expandedClusters[cluster.id]}
          onToggle={() => toggleCluster(cluster.id)}
        />
      ))}

      {/* Empty state */}
      {stages.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-gray-500 font-medium">Pipeline Starting...</p>
          <p className="text-gray-400 text-sm mt-1">Agents will appear in their clusters as they execute</p>
        </div>
      )}
    </div>
  )
}

// Timeline view - list of stages in execution order with visual timeline
function TimelineView({
  run,
  stages,
  selectedStage,
  onSelectStage,
  graphStructure,
  executionPath,
  stageStatusMap,
}: {
  run: PipelineRun
  stages: StageExecution[]
  selectedStage: StageExecution | null
  onSelectStage: (stage: StageExecution) => void
  graphStructure: GraphStructure | null
  executionPath: ExecutionPath | null
  stageStatusMap: Record<string, StageExecution>
}) {
  // Build timeline items from execution path or graph structure
  const timelineItems = useMemo(() => {
    const items: Array<{
      id: string
      name: string
      displayName: string
      status: 'pending' | 'running' | 'success' | 'failed' | 'degraded' | 'skipped'
      duration_ms?: number | null
      stage?: StageExecution
      isDecisionNode?: boolean
      isOrchestrator?: boolean
      isRetry?: boolean
      retryCount?: number
      conditionTaken?: string
      category?: string
      icon?: string
    }> = []

    // If we have execution path, use it to show the actual flow
    if (executionPath?.executedStages && executionPath.executedStages.length > 0) {
      executionPath.executedStages.forEach((execStage, index) => {
        const stage = stageStatusMap[execStage.stageName]
        const nodeMeta = graphStructure?.nodes?.find(n => n.id === execStage.stageName)

        // Check for decision made at this stage
        const decision = executionPath.conditionalDecisions?.find(
          d => d.atStage === execStage.stageName
        )

        items.push({
          id: stage?.id || `exec-${index}`,
          name: execStage.stageName,
          displayName: nodeMeta?.name || formatAgentName(execStage.stageName),
          status: stage?.status || (execStage.status as 'pending' | 'running' | 'success' | 'failed' | 'degraded' | 'skipped') || 'success',
          duration_ms: stage?.duration_ms || execStage.durationMs,
          stage,
          isDecisionNode: nodeMeta?.isDecisionNode,
          isOrchestrator: nodeMeta?.isOrchestrator,
          retryCount: stage?.retry_count || execStage.retryCount,
          isRetry: (stage?.retry_count || execStage.retryCount || 0) > 0,
          conditionTaken: decision?.decision,
          category: nodeMeta?.category,
          icon: nodeMeta?.icon,
        })
      })
    } else if (stages.length > 0) {
      // Fall back to stages array
      const sortedStages = [...stages].sort((a, b) => a.stage_order - b.stage_order)
      sortedStages.forEach(stage => {
        const nodeMeta = graphStructure?.nodes?.find(n => n.id === stage.stage_name)
        items.push({
          id: stage.id,
          name: stage.stage_name,
          displayName: nodeMeta?.name || formatAgentName(stage.stage_name),
          status: stage.status,
          duration_ms: stage.duration_ms,
          stage,
          isDecisionNode: nodeMeta?.isDecisionNode,
          isOrchestrator: nodeMeta?.isOrchestrator,
          retryCount: stage.retry_count,
          isRetry: stage.retry_count > 0,
          category: nodeMeta?.category,
          icon: nodeMeta?.icon,
        })
      })
    }

    return items
  }, [executionPath, stages, stageStatusMap, graphStructure])

  // Calculate summary stats
  const stats = useMemo(() => {
    const executed = timelineItems.filter(i => i.status !== 'pending' && i.status !== 'skipped')
    const totalDuration = executed.reduce((sum, i) => sum + (i.duration_ms || 0), 0)
    const totalRetries = timelineItems.reduce((sum, i) => sum + (i.retryCount || 0), 0)
    const decisionCount = timelineItems.filter(i => i.conditionTaken).length
    return { executed: executed.length, totalDuration, totalRetries, decisionCount }
  }, [timelineItems])

  // Helper to format duration
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  }

  // Helper to format agent name
  function formatAgentName(name: string): string {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  // Status styles
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'success': return { dot: 'bg-green-500', ring: 'ring-green-200', text: 'text-green-700', bg: 'bg-green-50' }
      case 'running': return { dot: 'bg-blue-500 animate-pulse', ring: 'ring-blue-200', text: 'text-blue-700', bg: 'bg-blue-50' }
      case 'failed': return { dot: 'bg-red-500', ring: 'ring-red-200', text: 'text-red-700', bg: 'bg-red-50' }
      case 'degraded': return { dot: 'bg-orange-500', ring: 'ring-orange-200', text: 'text-orange-700', bg: 'bg-orange-50' }
      case 'skipped': return { dot: 'bg-gray-300', ring: 'ring-gray-100', text: 'text-gray-500', bg: 'bg-gray-50' }
      default: return { dot: 'bg-gray-400', ring: 'ring-gray-200', text: 'text-gray-600', bg: 'bg-gray-50' }
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-6">
      {/* Summary header */}
      <div className="mb-6 p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Execution Timeline</h3>
            <p className="text-sm text-gray-500 mt-1">
              {run.status === 'running' ? 'Pipeline in progress...' :
               run.status === 'success' ? 'Pipeline completed successfully' :
               run.status === 'failed' ? 'Pipeline failed' : 'Pipeline status: ' + run.status}
            </p>
          </div>
          <div className="flex gap-4 text-sm">
            <div className="text-center">
              <div className="font-semibold text-gray-900">{stats.executed}</div>
              <div className="text-gray-500 text-xs">Stages</div>
            </div>
            {stats.totalDuration > 0 && (
              <div className="text-center">
                <div className="font-semibold text-gray-900">{formatDuration(stats.totalDuration)}</div>
                <div className="text-gray-500 text-xs">Duration</div>
              </div>
            )}
            {stats.totalRetries > 0 && (
              <div className="text-center">
                <div className="font-semibold text-orange-600">{stats.totalRetries}</div>
                <div className="text-gray-500 text-xs">Retries</div>
              </div>
            )}
            {stats.decisionCount > 0 && (
              <div className="text-center">
                <div className="font-semibold text-teal-600">{stats.decisionCount}</div>
                <div className="text-gray-500 text-xs">Decisions</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {timelineItems.length > 0 ? (
        <div className="relative">
          {/* Vertical timeline line */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gradient-to-b from-gray-300 via-gray-200 to-gray-100" />

          {/* Timeline items */}
          <div className="space-y-4">
            {timelineItems.map((item, index) => {
              const style = getStatusStyle(item.status)
              const isSelected = selectedStage?.stage_name === item.name

              return (
                <div key={item.id} className="relative pl-14">
                  {/* Timeline node */}
                  <div className={`absolute left-4 w-5 h-5 rounded-full ${style.dot} ring-4 ${style.ring} z-10`}>
                    {item.isDecisionNode && (
                      <div className="absolute inset-0 flex items-center justify-center text-white text-[10px] font-bold">
                        ?
                      </div>
                    )}
                    {item.isOrchestrator && (
                      <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-purple-500 rounded-full border border-white" />
                    )}
                  </div>

                  {/* Content card */}
                  <button
                    onClick={() => item.stage && onSelectStage(item.stage)}
                    className={`w-full text-left p-4 rounded-lg border transition-all ${
                      isSelected
                        ? 'border-blue-400 bg-blue-50 ring-2 ring-blue-200 shadow-md'
                        : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                    } ${!item.stage ? 'opacity-60 cursor-default' : 'cursor-pointer'}`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          {/* Icon */}
                          {item.icon && (
                            <span className="text-lg">{item.icon}</span>
                          )}

                          {/* Name */}
                          <h4 className="font-medium text-gray-900 truncate">
                            {item.displayName}
                          </h4>

                          {/* Badges */}
                          {item.isDecisionNode && (
                            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-teal-100 text-teal-700 rounded">
                              Decision
                            </span>
                          )}
                          {item.isOrchestrator && (
                            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-purple-100 text-purple-700 rounded">
                              Orchestrator
                            </span>
                          )}
                          {item.isRetry && (
                            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-orange-100 text-orange-700 rounded flex items-center gap-0.5">
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                              </svg>
                              {item.retryCount}
                            </span>
                          )}
                        </div>

                        {/* Condition taken */}
                        {item.conditionTaken && (
                          <div className="mt-1.5 flex items-center gap-1.5 text-xs">
                            <span className="text-gray-500">Branch:</span>
                            <span className={`px-1.5 py-0.5 rounded font-medium ${style.bg} ${style.text}`}>
                              {item.conditionTaken}
                            </span>
                          </div>
                        )}

                        {/* Category */}
                        {item.category && (
                          <div className="mt-1 text-xs text-gray-500 capitalize">
                            {item.category}
                          </div>
                        )}
                      </div>

                      {/* Right side: Status & Duration */}
                      <div className="flex flex-col items-end gap-1">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded capitalize ${style.bg} ${style.text}`}>
                          {item.status}
                        </span>
                        {item.duration_ms && (
                          <span className="text-xs text-gray-500">
                            {formatDuration(item.duration_ms)}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>

                  {/* Connector to next item (if not last) */}
                  {index < timelineItems.length - 1 && (
                    <div className="absolute left-[22px] top-8 h-4 w-0.5 bg-gray-200" />
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="text-center py-16 bg-white rounded-lg border border-gray-200">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {run.status === 'running' ? 'Pipeline starting...' : 'No stages executed yet'}
          </h3>
          <p className="text-gray-500 max-w-md mx-auto">
            {run.status === 'running'
              ? 'The pipeline is initializing. Timeline will populate as stages execute.'
              : 'Run the pipeline to see the execution timeline.'}
          </p>
        </div>
      )}
    </div>
  )
}

// Category Legend Component - shows color coding for agent categories and special node types
function CategoryLegend() {
  const [isExpanded, setIsExpanded] = useState(true)

  return (
    <div className="absolute top-4 right-4 z-10 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
      {/* Header with toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between text-sm font-medium text-gray-700 hover:bg-gray-100"
      >
        <span>Legend</span>
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Legend items */}
      {isExpanded && (
        <div className="p-2 space-y-2">
          {/* Node Types Section */}
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider px-1">
            Node Types
          </div>
          <div className="flex items-center gap-2 px-1">
            <div className="w-4 h-4 rounded border-2 border-gray-300 bg-white flex-shrink-0" />
            <span className="text-xs text-gray-700">Regular Agent</span>
          </div>
          <div className="flex items-center gap-2 px-1">
            <div
              className="w-4 h-4 transform rotate-45 border-2 flex-shrink-0"
              style={{ borderColor: '#14B8A6', backgroundColor: 'white' }}
            />
            <span className="text-xs text-gray-700">Decision Node</span>
          </div>
          <div className="flex items-center gap-2 px-1">
            <div className="w-4 h-4 rounded border-2 flex-shrink-0 relative" style={{ borderColor: '#7C3AED', backgroundColor: '#F3E8FF' }}>
              <div
                className="absolute -top-1 -left-1 w-2 h-2 rounded-full"
                style={{ backgroundColor: '#7C3AED' }}
              />
            </div>
            <span className="text-xs text-gray-700">Orchestrator</span>
          </div>

          {/* Divider */}
          <div className="border-t border-gray-200 my-1" />

          {/* Categories Section */}
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider px-1">
            Categories
          </div>
          {Object.entries(CATEGORY_INFO)
            .filter(([key]) => !['decision', 'orchestrator'].includes(key))
            .map(([key, info]) => (
              <div key={key} className="flex items-center gap-2 px-1">
                <div
                  className="w-3 h-3 rounded-sm flex-shrink-0"
                  style={{ backgroundColor: info.color }}
                />
                <span className="text-xs text-gray-700">{info.name}</span>
              </div>
            ))}

          {/* Divider */}
          <div className="border-t border-gray-200 my-1" />

          {/* Edge Types Section */}
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider px-1">
            Edge Types
          </div>
          <div className="flex items-center gap-2 px-1">
            <div className="w-6 h-0.5 bg-green-500 flex-shrink-0" />
            <span className="text-xs text-gray-700">Success path</span>
          </div>
          <div className="flex items-center gap-2 px-1">
            <svg className="w-6 h-3 flex-shrink-0" viewBox="0 0 24 12">
              <path d="M0 6 L24 6" stroke="#F97316" strokeWidth="2" strokeDasharray="8,4" />
            </svg>
            <span className="text-xs text-gray-700">Retry loop</span>
          </div>
          <div className="flex items-center gap-2 px-1">
            <svg className="w-6 h-3 flex-shrink-0" viewBox="0 0 24 12">
              <path d="M0 6 L24 6" stroke="#F43F5E" strokeWidth="2" strokeDasharray="5,5" />
            </svg>
            <span className="text-xs text-gray-700">Escalation</span>
          </div>
        </div>
      )}
    </div>
  )
}

// Inner graph component that uses useReactFlow hook
function GraphViewInner({
  run,
  stageStatusMap,
  stageExecutions = {},
  selectedStage,
  onSelectStage,
  graphStructure,
  executionPath,
  graphLoading,
}: {
  run: PipelineRun
  stageStatusMap: Record<string, StageExecution>
  stageExecutions?: Record<string, StageExecution[]>
  selectedStage: StageExecution | null
  onSelectStage: (stageName: string) => void
  graphStructure: GraphStructure | null
  executionPath: ExecutionPath | null
  graphLoading: boolean
}) {
  const { setCenter, getNode, fitView } = useReactFlow()
  const initialCenterDone = useRef(false)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)

  // ResizeObserver to handle graph container resizes — prevents graph disappearing
  useEffect(() => {
    // Clean up previous observer
    resizeObserverRef.current?.disconnect()

    // Find the ReactFlow wrapper element by querying for .react-flow
    const rfContainer = document.querySelector('.react-flow') as HTMLElement | null
    if (!rfContainer) return

    let timeoutId: ReturnType<typeof setTimeout>
    const observer = new ResizeObserver(() => {
      clearTimeout(timeoutId)
      timeoutId = setTimeout(() => {
        requestAnimationFrame(() => {
          fitView({ padding: 0.2, maxZoom: 1.2 })
        })
      }, 200)
    })
    observer.observe(rfContainer)
    resizeObserverRef.current = observer

    return () => {
      clearTimeout(timeoutId)
      observer.disconnect()
    }
  }, [fitView])

  // Build set of executed stage names for highlighting
  const executedStageNames = useMemo(() => {
    const names = new Set<string>()
    executionPath?.executedStages?.forEach(s => names.add(s.stageName))
    // Also include stages from stageStatusMap
    Object.keys(stageStatusMap).forEach(name => names.add(name))
    return names
  }, [executionPath, stageStatusMap])

  // Build set of edges that were actually traversed
  const traversedEdges = useMemo(() => {
    const edges = new Set<string>()
    executionPath?.edgesTaken?.forEach(e => {
      edges.add(`${e.from}->${e.to}`)
    })
    return edges
  }, [executionPath])

  // Build retry counts per stage
  const retryCountByStage = useMemo(() => {
    const counts: Record<string, number> = {}
    executionPath?.stagesWithRetries?.forEach(s => {
      counts[s.stageName] = s.executions - 1 // executions - 1 = retries
    })
    // Also check stageStatusMap for retry counts
    Object.values(stageStatusMap).forEach(s => {
      if (s.retry_count && s.retry_count > 0) {
        counts[s.stage_name] = Math.max(counts[s.stage_name] || 0, s.retry_count)
      }
    })
    return counts
  }, [executionPath, stageStatusMap])

  // Create unified status resolver for consistent status across all visualizations
  // See @/lib/stageStatus.ts for priority order and reasoning documentation
  const resolveStageStatusLocal = useMemo(() => {
    const context: StatusResolutionContext = {
      stageStatusMap,
      executionPath,
      runStatus: run.status,
      isRunning: run.status === 'running'
    }
    return createStatusResolver(context)
  }, [stageStatusMap, executionPath, run.status])

  // Define workflow connections (edges) for the 2-step Gemini pipeline
  // sourceHandle/targetHandle: 'right'/'left' for horizontal, 'source-top'/'top' or 'source-bottom'/'bottom' for vertical
  // isEscalation: true for paths to human_review (shown differently)
  const edgeDefinitions: Array<{
    from: string
    to: string
    sourceHandle?: string
    targetHandle?: string
    type?: string
    isEscalation?: boolean
  }> = [
    // === Linear start sequence ===
    { from: 'input_enhancer', to: 'domain_knowledge_retriever' },
    // Preset 2: domain_knowledge_retriever -> diagram_type_classifier -> router
    { from: 'domain_knowledge_retriever', to: 'diagram_type_classifier' },
    { from: 'diagram_type_classifier', to: 'router' },

    // === Router branching ===
    // Standard path (Preset 1): router -> game_planner
    { from: 'router', to: 'game_planner', sourceHandle: 'right', targetHandle: 'left' },
    { from: 'router', to: 'human_review', sourceHandle: 'source-bottom', targetHandle: 'top', isEscalation: true },
    { from: 'human_review', to: 'game_planner', sourceHandle: 'right', targetHandle: 'bottom' },

    // === Agentic design flow (Preset 2): router -> diagram_analyzer -> game_designer -> game_planner ===
    { from: 'router', to: 'diagram_analyzer', sourceHandle: 'source-bottom', targetHandle: 'left' },
    { from: 'diagram_analyzer', to: 'game_designer' },
    { from: 'game_designer', to: 'game_planner', targetHandle: 'bottom' },

    // === Agentic interaction design: game_planner -> interaction_designer -> interaction_validator ===
    { from: 'game_planner', to: 'interaction_designer' },
    { from: 'interaction_designer', to: 'interaction_validator' },

    // === Main flow: interaction_validator -> scene_sequencer (Preset 2) -> scene stages ===
    { from: 'interaction_validator', to: 'scene_sequencer' },
    // Single scene path
    { from: 'scene_sequencer', to: 'scene_stage1_structure' },
    // Multi-scene path (Preset 2)
    { from: 'scene_sequencer', to: 'multi_scene_image_orchestrator', sourceHandle: 'source-bottom', targetHandle: 'left' },
    { from: 'multi_scene_image_orchestrator', to: 'asset_planner' },  // CHANGED: goes to asset pipeline
    { from: 'scene_stage1_structure', to: 'scene_stage2_assets' },
    { from: 'scene_stage2_assets', to: 'scene_stage3_interactions' },

    // === 2-step Gemini image pipeline (INTERACTIVE_DIAGRAM) ===
    { from: 'scene_stage3_interactions', to: 'diagram_image_retriever' },
    { from: 'diagram_image_retriever', to: 'diagram_image_generator' },
    { from: 'diagram_image_generator', to: 'gemini_zone_detector' },
    // For non-INTERACTIVE_DIAGRAM templates, skip_image goes directly to asset_planner
    { from: 'gemini_zone_detector', to: 'asset_planner' },  // CHANGED: zones feed into asset pipeline

    // === Asset generation pipeline (runs BEFORE blueprint) ===
    { from: 'asset_planner', to: 'asset_generator_orchestrator' },
    { from: 'asset_generator_orchestrator', to: 'asset_validator' },
    { from: 'asset_validator', to: 'blueprint_generator' },  // CHANGED: assets feed into blueprint

    // === Blueprint validation chain ===
    { from: 'blueprint_generator', to: 'blueprint_validator' },
    { from: 'blueprint_validator', to: 'diagram_spec_generator' },  // CHANGED: direct to spec

    // === Spec generation and SVG output ===
    { from: 'diagram_spec_generator', to: 'diagram_svg_generator' },
  ]

  // HORIZONTAL LAYOUT: X increases with column index, Y varies within column
  const COLUMN_SPACING = 200  // Horizontal spacing between columns (reduced for longer pipeline)
  const ROW_SPACING = 200     // Vertical spacing within a column (for parallel agents)
  const CENTER_Y = 200        // Center point for single-agent columns

  // Auto-detect the correct layout from pipeline_preset or executed agents
  const activeLayout = useMemo(() => {
    // 1. Check pipeline_preset from config_snapshot (most reliable)
    const preset = (run.config_snapshot?.pipeline_preset as string || '').toLowerCase()
    if (preset === 'v4') return V4_GRAPH_LAYOUT
    if (preset === 'v4_algorithm') return V4_ALGORITHM_GRAPH_LAYOUT
    if (preset === 'v3') return V3_GRAPH_LAYOUT
    if (preset === 'had') return HAD_GRAPH_LAYOUT
    if (preset.includes('react')) return REACT_GRAPH_LAYOUT
    if (preset.includes('agentic_sequential')) return AGENTIC_SEQUENTIAL_GRAPH_LAYOUT
    if (preset.includes('phet')) return PHET_GRAPH_LAYOUT

    // 2. Fallback: auto-detect from executed agents
    const executedIds = new Set(Object.keys(stageStatusMap))
    if (executedIds.has('v4a_game_concept_designer') || executedIds.has('v4a_blueprint_assembler')) return V4_ALGORITHM_GRAPH_LAYOUT
    if (executedIds.has('v4_game_concept_designer') || executedIds.has('v4_content_builder') || executedIds.has('v4_assembler')) return V4_GRAPH_LAYOUT
    if (executedIds.has('game_designer_v3') || executedIds.has('scene_architect_v3') || executedIds.has('blueprint_assembler_v3')) return V3_GRAPH_LAYOUT
    if (executedIds.has('zone_planner') || executedIds.has('output_orchestrator')) return HAD_GRAPH_LAYOUT
    if (executedIds.has('phet_simulation_selector')) return PHET_GRAPH_LAYOUT

    return GRAPH_LAYOUT
  }, [run.config_snapshot, stageStatusMap])

  // Convert to React Flow nodes with horizontal layout
  const nodes: Node[] = useMemo(() => {
    // For specialized layouts (V3, HAD, PhET, ReAct), always show ALL agents in the layout
    // regardless of execution status — non-executed agents appear as "pending"
    const isSpecializedLayout = activeLayout !== GRAPH_LAYOUT

    // Dynamic graph structure path — use for default layout with graphStructure from backend
    // Skip for specialized layouts (V3, HAD, etc.) — those use the static layout path below
    if (!isSpecializedLayout && graphStructure?.nodes && graphStructure.nodes.length > 0) {
      const nodeById = new Map(graphStructure.nodes.map(n => [n.id, n]))
      const graphNodes = new Set(graphStructure.nodes.map(n => n.id))
      const executedAgentIds = new Set([
        ...Object.keys(stageStatusMap),
        ...Array.from(executedStageNames)
      ])
      // Always filter to executed agents only — T1 topology has 44+ nodes which overwhelms the graph
      const showOnlyExecuted = executedAgentIds.size > 0

      const allNodes: Node[] = []
      let actualColIndex = 0

      for (const column of activeLayout) {
        const agentsInColumn = column.filter(agentId => {
          if (!graphNodes.has(agentId)) return false
          if (!showOnlyExecuted) return true
          return executedAgentIds.has(agentId)
        })

        if (agentsInColumn.length === 0) continue

        const totalInColumn = agentsInColumn.length
        const startY = totalInColumn === 1
          ? CENTER_Y
          : CENTER_Y - (totalInColumn - 1) * ROW_SPACING / 2

        agentsInColumn.forEach((agentId, rowIndex) => {
          const stage = stageStatusMap[agentId]
          const graphNode = nodeById.get(agentId)
          const info = graphNode
            ? { name: graphNode.name, category: graphNode.category }
            : AGENT_INFO[agentId] || { name: agentId, category: 'generation' }
          const agentColor = getAgentColor(agentId)

          let agentStatus = stage?.status || 'pending'
          const wasExecuted = executedStageNames.has(agentId)

          if (!stage && wasExecuted) {
            agentStatus = 'success'
          } else if (!stage && run.status === 'success') {
            agentStatus = wasExecuted ? 'success' : 'skipped'
          } else if (!stage) {
            agentStatus = 'pending'
          }

          const retryCount = retryCountByStage[agentId] || 0
          const staticMeta = AGENT_METADATA[agentId]
          const isDecisionNode = staticMeta?.isDecisionNode ||
                                 staticMeta?.category === 'decision' ||
                                 agentId.startsWith('check_')
          const isOrchestrator = staticMeta?.isOrchestrator ||
                                 staticMeta?.category === 'orchestrator' ||
                                 agentId.includes('orchestrator') ||
                                 agentId === 'zone_planner'

          const nodeType = isDecisionNode ? 'decision' : isOrchestrator ? 'orchestrator' : 'agent'

          allNodes.push({
            id: agentId,
            type: nodeType,
            position: {
              x: actualColIndex * COLUMN_SPACING,
              y: startY + rowIndex * ROW_SPACING,
            },
            data: {
              id: agentId,
              displayName: info.name,
              status: agentStatus,
              color: agentColor,
              duration_ms: stage?.duration_ms,
              isActive: selectedStage?.stage_name === agentId,
              onClick: () => onSelectStage(agentId),
              stage: stage,
              metadata: graphNode ? {
                name: graphNode.name,
                description: graphNode.description,
                category: graphNode.category,
                toolOrModel: graphNode.toolOrModel,
                icon: graphNode.icon,
                isDecisionNode,
                isOrchestrator,
              } : AGENT_METADATA[agentId],
              wasExecuted,
              retryCount,
              isDecisionNode,
              isOrchestrator,
            },
            selected: selectedStage?.stage_name === agentId,
          })
        })

        actualColIndex++
      }

      return allNodes
    }

    // Specialized layout path (V3, HAD, PhET, ReAct) OR fallback for default layout
    // For specialized layouts: show ALL agents from the layout, mark unexecuted as pending
    // For default layout fallback: only show executed agents
    const executedAgentIds = new Set(Object.keys(stageStatusMap))

    // For default layout: if nothing executed, show nothing
    if (!isSpecializedLayout && executedAgentIds.size === 0 && run.status !== 'running') {
      return []
    }

    const nodes: Node[] = []
    let colIndex = 0

    for (const column of activeLayout) {
      // For specialized layouts, show ALL agents; for default, only executed
      const agentsInColumn = isSpecializedLayout
        ? column  // Show all agents in the layout
        : column.filter(agentId => executedAgentIds.has(agentId))

      if (agentsInColumn.length === 0) continue

      const totalInColumn = agentsInColumn.length
      const startY = totalInColumn === 1
        ? CENTER_Y
        : CENTER_Y - (totalInColumn - 1) * ROW_SPACING / 2

      agentsInColumn.forEach((agentId, rowIndex) => {
        const executions = stageExecutions[agentId] || []
        // For fan-out stages, use first execution for the main node (not last-write-wins)
        const isFanout = V4_FANOUT_STAGES.has(agentId) || V4_ALGORITHM_FANOUT_STAGES.has(agentId)
        const stage = (isFanout && executions.length > 0)
          ? executions[0]
          : stageStatusMap[agentId]
        const info = AGENT_INFO[agentId] || { name: agentId, category: 'generation' }
        const agentColor = getAgentColor(agentId)
        const wasExecuted = executedAgentIds.has(agentId) || executedStageNames.has(agentId)

        // Determine status
        let agentStatus = stage?.status || 'pending'
        if (!stage && wasExecuted) {
          agentStatus = 'success'
        } else if (!stage && run.status === 'success') {
          agentStatus = wasExecuted ? 'success' : 'skipped'
        } else if (!stage && run.status === 'failed') {
          agentStatus = wasExecuted ? 'failed' : 'skipped'
        } else if (!stage) {
          agentStatus = run.status === 'running' ? 'pending' : 'skipped'
        }

        const retryCount = retryCountByStage[agentId] || 0

        const staticMeta = AGENT_METADATA[agentId]
        // Merge nodes are NOT decision nodes — only check_*, router, and validator nodes are
        const isMergeNode = agentId.includes('merge') || agentId.includes('phase0_merge')
        const isDecisionNode = !isMergeNode && (
          staticMeta?.isDecisionNode ||
          staticMeta?.category === 'decision' ||
          agentId.startsWith('check_') ||
          agentId.includes('validator')
        )
        const isOrchestrator = staticMeta?.isOrchestrator ||
                               staticMeta?.category === 'orchestrator' ||
                               agentId.includes('orchestrator') ||
                               agentId === 'zone_planner'

        const nodeType = isDecisionNode ? 'decision' : isOrchestrator ? 'orchestrator' : 'agent'

        // For fan-out stages, show count badge in display name
        const fanoutCount = (V4_FANOUT_STAGES.has(agentId) || V4_ALGORITHM_FANOUT_STAGES.has(agentId)) && executions.length > 1
          ? ` (${executions.length}x)`
          : ''

        nodes.push({
          id: agentId,
          type: nodeType,
          position: {
            x: colIndex * COLUMN_SPACING,
            y: startY + rowIndex * ROW_SPACING,
          },
          data: {
            id: agentId,
            displayName: `${info.name}${fanoutCount}`,
            status: agentStatus,
            color: agentColor,
            duration_ms: stage?.duration_ms,
            isActive: selectedStage?.stage_name === agentId,
            onClick: () => onSelectStage(agentId),
            stage: stage,
            metadata: AGENT_METADATA[agentId],
            isDecisionNode,
            isOrchestrator,
            retryCount,
            wasExecuted: true,
          },
          selected: selectedStage?.stage_name === agentId,
        })

        // Fan-out: render additional sub-nodes for stages with multiple executions
        if ((V4_FANOUT_STAGES.has(agentId) || V4_ALGORITHM_FANOUT_STAGES.has(agentId)) && executions.length > 1) {
          const parentX = colIndex * COLUMN_SPACING
          const parentY = startY + rowIndex * ROW_SPACING
          executions.forEach((exec, execIdx) => {
            if (execIdx === 0) return // First execution is the main node
            const subId = `${agentId}::fanout::${execIdx}`
            const inputSnap = (exec.input_snapshot || {}) as Record<string, unknown>
            const outputSnap = (exec.output_snapshot || {}) as Record<string, unknown>
            const sceneLabel = (inputSnap.scene_id as string) ||
                               (inputSnap.mechanic_id as string) ||
                               (outputSnap.scene_id as string) ||
                               (outputSnap.mechanic_id as string) ||
                               `#${execIdx + 1}`
            nodes.push({
              id: subId,
              type: 'subAgent',
              position: {
                x: parentX - 10,
                y: parentY + 50 + execIdx * 45,
              },
              data: {
                id: subId,
                displayName: `${info.name} ${sceneLabel}`,
                status: exec.status || 'pending',
                color: agentColor,
                duration_ms: exec.duration_ms,
                isActive: selectedStage?.id === exec.id,
                onClick: () => onSelectStage(subId),
                stage: exec,
                metadata: AGENT_METADATA[agentId],
                mechanic_type: (outputSnap.mechanic_type as string) || undefined,
              },
              selected: selectedStage?.id === exec.id,
            })
          })
        }
      })

      colIndex++ // Only increment for columns that have executed agents
    }

    return nodes
  }, [stageStatusMap, stageExecutions, selectedStage, onSelectStage, graphStructure, run.status, executedStageNames, retryCountByStage])

  // Auto-zoom to center on selected stage when it changes
  useEffect(() => {
    if (selectedStage) {
      const node = getNode(selectedStage.stage_name)
      if (node) {
        // Center on the selected node with smooth animation
        setCenter(
          node.position.x + 80,  // Center of 160px wide node
          node.position.y + 80,  // Center of 160px tall node
          { zoom: 1.2, duration: 500 }
        )
      }
    }
  }, [selectedStage, getNode, setCenter])

  // Center on first agent on initial load
  useEffect(() => {
    if (!initialCenterDone.current && nodes.length > 0) {
      initialCenterDone.current = true
      // Small delay to ensure ReactFlow is ready
      setTimeout(() => {
        setCenter(
          nodes[0].position.x + 80,
          nodes[0].position.y + 80,
          { zoom: 0.9, duration: 300 }
        )
      }, 100)
    }
  }, [nodes, setCenter])

  // Convert to React Flow edges with proper styling for horizontal layout
  const edges: Edge[] = useMemo(() => {
    const isSpecializedLayout = activeLayout !== GRAPH_LAYOUT
    const existingNodeIds = new Set(nodes.map(n => n.id))

    let edgesToUse: Array<{ from: string; to: string; type?: string; isEscalation?: boolean; isRetryEdge?: boolean; conditionValue?: string }>

    if (isSpecializedLayout) {
      // For specialized layouts (V3, V4, HAD, PhET, ReAct), generate edges
      // dynamically from the layout: each node in column N connects to
      // each node in column N+1 (fan-out / fan-in pattern)
      const generated: typeof edgesToUse = []
      for (let col = 0; col < activeLayout.length - 1; col++) {
        const currentCol = activeLayout[col].filter(id => existingNodeIds.has(id))
        const nextCol = activeLayout[col + 1].filter(id => existingNodeIds.has(id))
        for (const from of currentCol) {
          for (const to of nextCol) {
            generated.push({ from, to, type: 'direct', isEscalation: false, isRetryEdge: false })
          }
        }
      }
      edgesToUse = generated
    } else {
      // Default layout: use backend graph structure or static edge definitions
      edgesToUse = graphStructure?.edges ?? edgeDefinitions.map(e => ({
        from: e.from,
        to: e.to,
        type: 'direct' as const,
        isEscalation: e.isEscalation,
        isRetryEdge: false,
      }))
    }

    // Filter edges to only include those where BOTH source and target exist
    const filteredEdges = edgesToUse.filter(edge =>
      existingNodeIds.has(edge.from) && existingNodeIds.has(edge.to)
    )

    return filteredEdges.map((edge, idx) => {
      const fromStage = stageStatusMap[edge.from]
      const toStage = stageStatusMap[edge.to]

      // Check if this edge was actually traversed in the execution
      const edgeKey = `${edge.from}->${edge.to}`
      const wasTraversed = traversedEdges.has(edgeKey)

      // Use unified status resolver for consistent status across all visualizations
      // See @/lib/stageStatus.ts for resolution priority and reasoning
      const toStatus = resolveStageStatusLocal(edge.to).status
      const fromStatus = resolveStageStatusLocal(edge.from).status

      // Escalation edges (to human_review) are styled differently
      const isEscalation = edge.isEscalation || edge.to === 'human_review'
      const isRetryEdge = edge.isRetryEdge || false
      const isConditional = edge.type === 'conditional'

      // Determine edge color based on execution status
      let edgeColor = '#E2E8F0' // light gray (pending/not traversed)
      let edgeOpacity = wasTraversed ? 1.0 : 0.3 // Dim edges that weren't traversed

      if (isEscalation) {
        edgeColor = '#F43F5E' // Rose color for escalation paths
      } else if (isRetryEdge && wasTraversed) {
        edgeColor = '#F97316' // Orange for retry edges that were used
      } else if (wasTraversed) {
        // Edge was traversed - color based on target status
        if (toStatus === 'success') {
          edgeColor = '#10B981' // green
        } else if (toStatus === 'degraded') {
          edgeColor = '#F97316' // orange
        } else if (toStatus === 'failed') {
          edgeColor = '#EF4444' // red
        } else if (toStatus === 'running') {
          edgeColor = '#3B82F6' // blue
        } else {
          edgeColor = '#94A3B8' // gray (completed but no specific status)
        }
        edgeOpacity = 1.0
      } else if (executedStageNames.size > 0) {
        // We have execution data but this edge wasn't traversed
        edgeColor = '#CBD5E1' // Lighter gray for non-traversed
        edgeOpacity = 0.25
      } else if (fromStatus === 'success' || fromStatus === 'degraded') {
        edgeColor = '#94A3B8' // gray (completed)
      }

      // Default handles for horizontal flow
      const sourceHandle = 'right'
      const targetHandle = 'left'

      // Determine stroke style
      let strokeDasharray: string | undefined = undefined
      if (isEscalation) {
        strokeDasharray = '5,5' // Dashed for escalation
      } else if (isConditional && !wasTraversed) {
        strokeDasharray = '3,3' // Dotted for conditional not taken
      } else if (isRetryEdge) {
        strokeDasharray = '8,4' // Long dash for retry
      }

      return {
        id: `e-${edge.from}-${edge.to}-${idx}`,
        source: edge.from,
        target: edge.to,
        sourceHandle,
        targetHandle,
        type: 'smoothstep',
        animated: toStatus === 'running',
        style: {
          stroke: edgeColor,
          strokeWidth: wasTraversed ? 2.5 : 1.5,
          strokeDasharray,
          opacity: edgeOpacity,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: edgeColor,
        },
        // Add label for conditional edges that were traversed
        label: isConditional && wasTraversed && edge.conditionValue ? edge.conditionValue : undefined,
        labelStyle: { fontSize: 10, fill: '#64748B' },
        labelBgStyle: { fill: 'white', fillOpacity: 0.8 },
      }
    })
  }, [stageStatusMap, run.status, graphStructure, traversedEdges, executedStageNames, nodes, activeLayout])

  // Expand compound nodes with _sub_stages into virtual sub-nodes
  const expandedNodes = useMemo(() => {
    const subNodes: Node[] = []
    const SUB_NODE_Y_OFFSET = 200
    const SUB_NODE_Y_SPACING = 50

    for (const parentNode of nodes) {
      const stage = stageStatusMap[parentNode.id]
      const subStages = stage?.output_snapshot?._sub_stages as Array<{
        id: string; name: string; type?: string; mechanic_type?: string;
        scene_id?: string; status: string; duration_ms?: number;
        model?: string; attempt?: number; validation_passed?: boolean;
        error?: string | null; input_summary?: Record<string, unknown>;
        output_summary?: Record<string, unknown>; attempts?: Array<Record<string, unknown>>;
      }> | undefined

      if (!subStages || subStages.length === 0) continue

      subStages.forEach((sub, idx) => {
        const subNodeId = `${parentNode.id}::${sub.id}`
        subNodes.push({
          id: subNodeId,
          type: 'subAgent',
          position: {
            x: parentNode.position.x - 10,
            y: parentNode.position.y + SUB_NODE_Y_OFFSET + idx * SUB_NODE_Y_SPACING,
          },
          data: {
            id: subNodeId,
            label: sub.mechanic_type
              ? `${sub.mechanic_type} (${sub.scene_id || ''})`
              : sub.name,
            status: sub.status as 'success' | 'failed' | 'degraded' | 'running' | 'pending' | 'skipped',
            duration_ms: sub.duration_ms,
            mechanic_type: sub.mechanic_type,
            // onClick handled by onNodeClick to avoid double-firing
          },
          selected: selectedStage?.stage_name === `${parentNode.id}::sub::${sub.id}`,
        })
      })
    }

    return [...nodes, ...subNodes]
  }, [nodes, stageStatusMap, selectedStage, onSelectStage])

  // Generate edges from parent to sub-nodes
  const expandedEdges = useMemo(() => {
    const subEdges: Edge[] = []

    for (const parentNode of nodes) {
      const stage = stageStatusMap[parentNode.id]
      const subStages = stage?.output_snapshot?._sub_stages as Array<{ id: string; status?: string }> | undefined
      if (!subStages || subStages.length === 0) continue

      subStages.forEach((sub, idx) => {
        const subNodeId = `${parentNode.id}::${sub.id}`
        // Connect parent to first sub-node, then chain sub-nodes
        const sourceId = idx === 0 ? parentNode.id : `${parentNode.id}::${subStages[idx - 1].id}`
        const sourceHandle = idx === 0 ? 'source-bottom' : 'source-bottom'
        subEdges.push({
          id: `sub-e-${sourceId}-${subNodeId}`,
          source: sourceId,
          target: subNodeId,
          sourceHandle,
          targetHandle: 'top',
          type: 'smoothstep',
          style: {
            stroke: '#94A3B8',
            strokeWidth: 1.5,
            strokeDasharray: '4,4',
            opacity: 0.6,
          },
        })
      })
    }

    return [...edges, ...subEdges]
  }, [edges, nodes, stageStatusMap])

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    // Handle sub-node clicks by constructing synthetic stage data
    if (node.id.includes('::')) {
      const parts = node.id.split('::')
      const parentId = parts[0]
      const subId = parts.slice(1).join('::')
      const parentStage = stageStatusMap[parentId]
      const subStages = parentStage?.output_snapshot?._sub_stages as Array<Record<string, unknown>> | undefined
      const subStage = subStages?.find(s => s.id === subId)

      if (subStage && parentStage) {
        // Build synthetic StageExecution for sub-stage rendering in StagePanel
        const syntheticId = `${parentId}::sub::${subId}`
        onSelectStage(syntheticId)
        return
      }
    }
    onSelectStage(node.id)
  }, [onSelectStage, stageStatusMap])

  // Custom node types for React Flow
  const nodeTypes = useMemo(() => ({
    agent: AgentNode,
    decision: DecisionNode,
    orchestrator: OrchestratorNode,
    subAgent: SubAgentNode,
  }), [])

  return (
    <ReactFlow
      nodes={expandedNodes}
      edges={expandedEdges}
      nodeTypes={nodeTypes}
      onNodeClick={onNodeClick}
      connectionMode={ConnectionMode.Loose}
      fitView
      fitViewOptions={{
        padding: 0.3,
        maxZoom: 1.2,
      }}
      minZoom={0.2}
      maxZoom={2}
      attributionPosition="bottom-left"
    >
      <Background color="#E5E7EB" gap={16} />
      <Controls />
      <MiniMap
        nodeColor={(node) => {
          const status = node.data?.status || 'pending'
          if (status === 'success') return '#10B981'
          if (status === 'degraded') return '#F97316'
          if (status === 'failed') return '#EF4444'
          if (status === 'running') return '#3B82F6'
          return '#E2E8F0'
        }}
        maskColor="rgba(0, 0, 0, 0.1)"
        style={{
          backgroundColor: '#f9fafb',
          border: '1px solid #e5e7eb',
        }}
      />

      {/* Category Legend */}
      <CategoryLegend />
    </ReactFlow>
  )
}

// Wrapper component with ReactFlowProvider for useReactFlow hook
function GraphView(props: {
  run: PipelineRun
  stageStatusMap: Record<string, StageExecution>
  stageExecutions?: Record<string, StageExecution[]>
  selectedStage: StageExecution | null
  onSelectStage: (stageName: string) => void
  graphStructure: GraphStructure | null
  executionPath: ExecutionPath | null
  graphLoading: boolean
}) {
  return (
    <div className="w-full bg-gray-50 rounded-lg h-[65vh] min-h-[500px]">
      {/* Loading indicator for graph structure */}
      {props.graphLoading && (
        <div className="absolute top-2 left-2 z-10 flex items-center gap-2 bg-white/90 px-3 py-1 rounded-lg shadow text-sm text-gray-600">
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Loading graph...
        </div>
      )}
      <ReactFlowProvider>
        <GraphViewInner {...props} />
      </ReactFlowProvider>
    </div>
  )
}

// Compact version for embedding in other pages
export function PipelineProgressBar({ run, stages }: { run: PipelineRun; stages: StageExecution[] }) {
  // Pick layout based on pipeline_preset or executed agents
  const layout = useMemo(() => {
    const preset = (run.config_snapshot?.pipeline_preset as string || '').toLowerCase()
    if (preset === 'v4') return V4_GRAPH_LAYOUT
    if (preset === 'v4_algorithm') return V4_ALGORITHM_GRAPH_LAYOUT
    if (preset === 'v3') return V3_GRAPH_LAYOUT
    if (preset === 'had') return HAD_GRAPH_LAYOUT
    const executedIds = new Set(stages.map(s => s.stage_name))
    if (executedIds.has('v4a_game_concept_designer') || executedIds.has('v4a_blueprint_assembler')) return V4_ALGORITHM_GRAPH_LAYOUT
    if (executedIds.has('v4_game_concept_designer')) return V4_GRAPH_LAYOUT
    if (executedIds.has('game_designer_v3')) return V3_GRAPH_LAYOUT
    if (executedIds.has('zone_planner')) return HAD_GRAPH_LAYOUT
    return GRAPH_LAYOUT
  }, [run.config_snapshot, stages])
  // Exclude human_review from expected count since it's often skipped
  const expectedStageCount = stages.length > 0 ? stages.length : layout.flat().filter((a: string) => a !== 'human_review').length
  const successCount = stages.filter(s => s.status === 'success' || s.status === 'degraded').length
  const runningCount = stages.filter(s => s.status === 'running').length
  const failedCount = stages.filter(s => s.status === 'failed').length
  const totalCount = expectedStageCount

  const progressPercent = (successCount / totalCount) * 100

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">
          {run.status === 'running' ? (
            <>
              Running: {stages.find(s => s.status === 'running')?.stage_name.replace(/_/g, ' ') || 'Starting...'}
            </>
          ) : run.status === 'success' ? (
            'Completed successfully'
          ) : run.status === 'failed' ? (
            `Failed at: ${stages.find(s => s.status === 'failed')?.stage_name.replace(/_/g, ' ')}`
          ) : (
            run.status
          )}
        </span>
        <span className="text-gray-500">
          {successCount}/{stages.length} stages
        </span>
      </div>

      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            failedCount > 0
              ? 'bg-red-500'
              : runningCount > 0
                ? 'bg-blue-500'
                : stages.some(s => s.status === 'degraded')
                  ? 'bg-orange-500'
                  : 'bg-green-500'
          }`}
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {run.status === 'running' && (
        <div className="flex justify-center">
          <div className="flex items-center gap-2 text-blue-600">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="text-sm">Processing...</span>
          </div>
        </div>
      )}
    </div>
  )
}
