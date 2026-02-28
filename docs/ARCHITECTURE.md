# Architecture

Comprehensive architecture reference for GamED.AI v2.

---

## Pipeline Flow Overview

```
Question → InputEnhancer → DomainKnowledgeRetriever → Router
                                                        ↓
                                            ┌───────────┴───────────┐
                                      LABEL_DIAGRAM           PHET_SIMULATION / Other
                                            ↓                        ↓
                                  DiagramImageRetriever        PhET Agent Cluster
                                            ↓                  (selector → planner →
                                  ImageLabelClassifier          designer → blueprint →
                                            ↓                   bridge config)
                                  ┌─────────┴─────────┐
                                LABELED           UNLABELED
                                  ↓                   ↓
                      QwenAnnotationDetector   DirectStructureLocator
                      (labels + leader lines)  (Qwen VL fast path)
                                  ↓                   │
                      QwenLabelRemover                │
                      (inpainting)                     │
                                  ↓                   │
                      QwenSamZoneDetector              │
                      (SAM3 + endpoints)               │
                                  ↓                   ↓
                                  └─────────┬─────────┘
                                            ↓
                              GamePlanner → InteractionDesigner
                                            ↓
                              ┌─────────────┴──────────────┐
                         Single-Scene               Multi-Scene
                              ↓                         ↓
                      SceneGenerator           MultiSceneOrchestrator
                      (3-stage)                SceneSequencer
                              ↓                         ↓
                  ┌───────────┼───────────┐           (per scene)
                  ↓           ↓           ↓
              Stage1      Stage2      Stage3
            Structure     Assets    Interactions
                              ↓
                  ┌───────────┴───────────┐
              Workflow Mode          Legacy Mode
                  ↓                       ↓
          AssetPlanner            BlueprintGenerator
          AssetGeneratorOrch      BlueprintValidator (retry 3x)
          AssetValidator                  ↓
                  ↓               DiagramSpecGenerator
          BlueprintGenerator      DiagramSpecValidator (retry 3x)
          BlueprintValidator              ↓
                  ↓               DiagramSvgGenerator
                OUTPUT                    ↓
                                      OUTPUT
```

---

## Conditional Routing Logic

### Template Selection (Router)
The `router` agent classifies the question and selects a template. Key routing functions in `graph.py`:
- `should_use_preset_pipeline()` — checks `_pipeline_preset` for non-default presets
- `should_use_advanced_preset()` — routes to advanced_label_diagram preset
- `requires_phet_simulation()` — routes to PhET agent cluster
- `is_stub_template()` — handles unsupported template types

### Labeled vs Unlabeled Diagrams
`ImageLabelClassifier` (EasyOCR + Qwen VL) sets `image_classification`:
- **LABELED** → QwenAnnotationDetector → QwenLabelRemover → QwenSamZoneDetector
- **UNLABELED** → DirectStructureLocator (fast path, bypasses inpainting)

### Multi-Scene Detection
`GamePlanner` populates `scene_breakdown` when multi-mechanic games are needed:
- `should_use_scene_sequencer()` — checks if `scene_breakdown` has multiple scenes
- `should_use_multi_scene_orchestrator()` — routes to per-scene image/zone orchestration

### Workflow Mode
`check_workflow_mode()` inspects `workflow_execution_plan`:
- **Workflow mode** → AssetPlanner → AssetGeneratorOrchestrator → AssetValidator
- **Legacy mode** → direct BlueprintGenerator path

### Post-Blueprint Routing (Phase 6)
`check_post_blueprint_needs()` inspects state flags:
- `_needs_diagram_spec` → DiagramSpecGenerator path
- `_needs_asset_generation` → Asset generation path
- `_skip_asset_pipeline` → Skip to output

---

## Pipeline Presets

### Default (`default`)
Main `create_game_generation_graph()` — 59+ agents, full conditional routing. Image classification + SAM segmentation baseline.

### Hierarchical (`label_diagram_hierarchical`)
`create_preset1_agentic_sequential_graph()` — 8 agents + 12 tools. AI diagram generation via Gemini + Gemini zone detection. Replaces image search with generation.

### Advanced (`advanced_label_diagram`)
Full agentic flow with `game_designer`, `diagram_analyzer`, `diagram_type_classifier`. Adds design trace metadata and richer interaction patterns.

### HAD (`had`)
`create_had_graph()` — Hierarchical Agentic DAG with 4 clusters:

| Cluster | Role | Key Agents/Tools |
|---------|------|-----------------|
| 1. RESEARCH | Input processing | input_enhancer, domain_knowledge_retriever (shared) |
| 2. VISION | Zone detection | zone_planner (Gemini vision, polygon zones, multi-scene) |
| 3. DESIGN | Game design | game_orchestrator OR game_designer (HAD v3 unified) |
| 4. OUTPUT | Blueprint + validation | output_orchestrator (retry loop) |

HAD support modules:
- `zone_collision_resolver` — resolves overlapping zones
- `spatial_validator` — validates spatial constraints
- `temporal_resolver` — Petri Net-inspired temporal constraint resolution
- `react_loop` — ReAct reasoning loop for tool-using agents

---

## Workflow System

**Location:** `backend/app/agents/workflows/`

### MechanicTypes (10)
`drag_drop`, `trace_path`, `sequencing`, `sorting`, `memory_match`, `comparison`, `branching_scenario`, `click_to_identify`, `reveal`, `hotspot`

### WorkflowTypes (7)
`labeling_diagram`, `trace_path`, `sequence_items`, `comparison_diagrams`, `sorting`, `memory_match`, `branching_scenario`

### Workflow Implementations
- `labeling_diagram_workflow.py` — Diagram retrieval and zone detection
- `trace_path_workflow.py` — Path tracing from zones
- `base.py` — BaseWorkflow abstract class

The workflow system is activated when `workflow_execution_plan` is non-empty, triggered by the AssetPlanner based on `scene_breakdown` mechanics.

---

## Entity Registry

**State field:** `entity_registry`

Tracks zones, assets, and interactions with cross-references:
- Zones have IDs, coordinates, labels
- Assets reference their parent zones
- Interactions reference participating entities

Used by AssetGeneratorOrchestrator and BlueprintGenerator for consistent entity tracking across the pipeline.

---

## Tool Framework

**Location:** `backend/app/tools/`

| Module | Purpose |
|--------|---------|
| `registry.py` | Tool registration and lookup |
| `blueprint_tools.py` | Blueprint generation and validation tools |
| `game_design_tools.py` | Game mechanics and interaction design tools |
| `vision_tools.py` | Image analysis, zone detection, segmentation tools |
| `research_tools.py` | Web search, domain knowledge tools |
| `render_tools.py` | SVG rendering, diagram generation tools |

Used primarily by HAD and Advanced preset agents that use ReAct-style tool calling.

---

## Complete Agent Table

### Input Processing (Phase 1)

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `input_enhancer` | Extract Bloom's level, subject, difficulty, enrich question | LLM |
| `domain_knowledge_retriever` | Web search for canonical labels, hierarchical relationships | Serper API |
| `diagram_type_classifier` | Classify diagram type (anatomical, circuit, etc.) | LLM |

### Routing (Phase 2)

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `router` | Select game template based on question type | LLM |
| `phet_simulation_selector` | Select appropriate PhET simulation | LLM + PhET catalog |

### Image Pipeline (Phase 3)

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `diagram_image_retriever` | Find diagram images from web | Serper Image Search |
| `image_label_classifier` | Classify diagram as labeled/unlabeled | EasyOCR + Qwen VL |
| `qwen_annotation_detector` | Detect text labels and leader lines | Qwen2.5-VL |
| `qwen_label_remover` | Remove detected annotations via inpainting | OpenCV/LaMa |
| `qwen_sam_zone_detector` | Create zones at leader line endpoints | SAM3 + Qwen VL |
| `direct_structure_locator` | Locate structures in unlabeled diagrams (fast path) | Qwen VL |
| `combined_label_detector` | Combined label detection pipeline | EasyOCR + Qwen VL |
| `smart_zone_detector` | Intelligent zone detection with fallbacks | SAM3 + Qwen VL |
| `smart_inpainter` | Smart inpainting with quality checks | LaMa + OpenCV |
| `qwen_zone_detector` | Zone detection via Qwen VL | Qwen2.5-VL |
| `diagram_image_generator` | Generate diagrams via AI (preset 1) | Gemini |
| `gemini_zone_detector` | Zone detection via Gemini vision | Gemini |
| `gemini_sam3_zone_detector` | SAM3-guided zone detection with Gemini | SAM3 + Gemini |
| `image_agent` | General image processing agent | Various |
| `multi_scene_image_orchestrator` | Orchestrate per-scene image processing | Orchestrator |

### Design (Phase 4)

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `game_planner` | Plan game mechanics, objectives, scene breakdown | LLM |
| `game_designer` | Full game design (advanced/HAD presets) | LLM + tools |
| `interaction_designer` | Design interaction patterns and behaviors | LLM |
| `interaction_validator` | Validate interaction designs | Rule-based + LLM |
| `research_agent` | Research domain content for game design | Serper + LLM |
| `diagram_analyzer` | Analyze diagram structure (advanced preset) | LLM + vision |

### Scene Generation (Phase 5)

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `scene_generator` | Legacy single-scene generation | LLM |
| `scene_stage1_structure` | Define scene layout and regions | LLM |
| `scene_stage2_assets` | Populate regions with visual assets | LLM |
| `scene_stage3_interactions` | Define behaviors and interactions | LLM |
| `scene_sequencer` | Sequence multi-scene progression | LLM |
| `multi_scene_orchestrator` | Orchestrate multi-scene generation | Orchestrator |
| `story_generator` | Generate narrative elements | LLM |

### Asset Pipeline

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `asset_planner` | Plan asset requirements from scene data | LLM |
| `asset_generator_orchestrator` | Orchestrate asset generation (workflow/legacy) | Orchestrator |
| `asset_validator` | Validate generated assets | Rule-based |

### Blueprint & Output (Phase 6)

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `blueprint_generator` | Generate game blueprint JSON | LLM |
| `playability_validator` | Validate blueprint playability | Rule-based + LLM |
| `diagram_spec_generator` | Generate SVG diagram specifications | LLM |
| `diagram_svg_generator` | Render final SVG from specs | SVG renderer |
| `output_renderer` | Final output assembly | Renderer |

### PhET Agents

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `phet_game_planner` | Plan PhET-based game | LLM + PhET catalog |
| `phet_assessment_designer` | Design PhET assessment questions | LLM |
| `phet_blueprint_generator` | Generate PhET game blueprint | LLM |
| `phet_bridge_config_generator` | Generate PhET bridge configuration | LLM |

### HAD Agents

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `zone_planner` | Vision-based zone detection (HAD) | Gemini Vision |
| `game_orchestrator` | Sequential game design (HAD) | LLM + tools |
| `output_orchestrator` | Blueprint + validation (HAD) | LLM + tools |
| `zone_collision_resolver` | Resolve overlapping zones | Algorithmic |
| `spatial_validator` | Validate spatial constraints | Algorithmic |
| `temporal_resolver` | Resolve temporal constraints | Petri Net |

### ReAct & Agentic

| Agent | Purpose | Models/Tools |
|-------|---------|-------------|
| `react_base` | Base ReAct loop implementation | LLM + tools |
| `agentic_wrapper` | Wrapper for agentic tool-using agents | LLM + tool registry |

### Decision Nodes

| Node | Purpose |
|------|---------|
| `check_routing_confidence_node` | Route based on confidence threshold |
| `check_agentic_design_node` | Route to agentic design flow |
| `check_template_status` | Check template completeness |
| `check_post_blueprint_needs` | Route post-blueprint (diagram spec, assets, skip) |
| `check_diagram_spec_route` | Route diagram spec validation |
| `check_workflow_mode` | Route workflow vs legacy mode |
| `check_legacy_diagram_image` | Check legacy diagram image availability |
| `human_review` | Human-in-the-loop review point |

---

## AgentState Fields Reference

### Core Input
- `question_id`, `question_text`, `question_options`

### Enhanced Input
- `pedagogical_context` — Bloom's level, subject, difficulty, enriched question

### Routing
- `template_selection`, `routing_confidence`, `routing_requires_human_review`

### Domain Knowledge
- `domain_knowledge` — canonical labels, hierarchical relationships, sequence flow data

### Diagram Pipeline
- `diagram_image`, `sam3_prompts`, `diagram_segments`, `diagram_zones`, `diagram_labels`
- `zone_groups`, `cleaned_image_path`, `removed_labels`, `generated_diagram_path`
- `annotation_elements`, `image_classification`

### Image Search Retry
- `retry_image_search`, `image_search_attempts`, `max_image_attempts`

### Generation Artifacts
- `game_plan`, `scene_data`, `story_data`, `blueprint`, `generated_code`
- `asset_urls`, `diagram_svg`, `diagram_spec`

### Hierarchical Scene Generation
- `scene_structure`, `scene_assets`, `scene_interactions`

### Multi-Scene Support
- `needs_multi_scene`, `num_scenes`, `scene_progression_type`, `scene_breakdown`
- `game_sequence`, `scene_diagrams`, `scene_zones`, `scene_labels`
- `scene_images`, `scene_zone_groups`, `current_scene_number`

### HAD v3 Fields
- `zone_collision_metadata`, `query_intent`, `suggested_reveal_order`
- `temporal_constraints`, `motion_paths`

### Agentic/Advanced Preset Fields
- `diagram_type`, `diagram_type_config`, `diagram_analysis`, `game_design`
- `interaction_designs`, `interaction_design`, `interaction_validation`
- `design_metadata`, `design_trace`

### Asset Pipeline
- `planned_assets`, `generated_assets`, `asset_validation`

### Entity Registry
- `entity_registry` — zones, assets, interactions with cross-references

### Workflow Execution
- `workflow_execution_plan`, `workflow_generated_assets`

### Runtime Context
- `_pipeline_preset`, `_ai_images_generated`

### Validation State
- `validation_results`, `current_validation_errors`

### Retry Management
- `retry_counts`, `max_retries`

### Human-in-the-Loop
- `pending_human_review`, `human_feedback`, `human_review_completed`

### Execution Tracking
- `current_agent`, `agent_history`, `started_at`, `last_updated_at`

### Observability
- `_run_id`, `_stage_order`

### Routing Flags (Phase 6)
- `_needs_diagram_spec`, `_needs_asset_generation`, `_skip_asset_pipeline`

### Final Output
- `final_visualization_id`, `generation_complete`, `error_message`, `output_metadata`

---

## Service Integrations

| Service | File | Purpose |
|---------|------|---------|
| `llm_service` | LLM provider abstraction (Groq, OpenAI, Anthropic, Gemini) |
| `qwen_vl_service` | Qwen2.5-VL vision-language model |
| `gemini_service` | Google Gemini API |
| `gemini_diagram_service` | Gemini-based diagram generation |
| `claude_diagram_service` | Claude-based diagram generation |
| `image_retrieval` | Web image search via Serper |
| `inpainting_service` | Image inpainting orchestration |
| `lama_inpainting_service` | LaMa inpainting model |
| `stable_diffusion_inpainting` | Stable Diffusion inpainting |
| `sam3_mlx_service` | SAM3 on Apple Silicon (MLX) |
| `sam3_zone_service` | SAM3 zone detection |
| `mlx_sam3_segmentation` | MLX-accelerated SAM3 segmentation |
| `segmentation` | General segmentation service |
| `vlm_service` | Vision-language model abstraction |
| `web_search` | Web search via Serper |
| `clip_filtering_service` | CLIP-based image filtering |
| `clip_labeling_service` | CLIP-based image labeling |
| `line_detection_service` | Leader line detection |
| `json_repair` | JSON output repair for LLM responses |
| `media_generation_service` | Media asset generation |
| `mlx_generation_service` | MLX-accelerated generation |
| `nanobanana_service` | NanoBanana service integration |
| `sam_guided_detection_service` | SAM-guided detection |

---

## Frontend Components

### Game Templates
- `LabelDiagramGame/` — Full label-the-diagram game with drag-and-drop, accessibility, animations, commands, events, persistence
- `PhetSimulationGame/` — PhET simulation wrapper

### Pipeline Observability UI
- `PipelineView.tsx` — Main pipeline DAG visualization
- `LivePipelineView.tsx` — Real-time pipeline streaming
- `StagePanel.tsx` — Agent output rendering
- `AgentNode.tsx` — Individual agent node component
- `TimelineView.tsx` — Timeline visualization
- `TokenChart.tsx` — Token usage charts
- `CostBreakdown.tsx` — Cost analysis
- `LiveTokenCounter.tsx` — Real-time token counter
- `ReActTraceViewer.tsx` — ReAct reasoning trace
- `ToolCallHistory.tsx` — Tool call log
- `RetryHistory.tsx` — Retry attempt history
- `ClusterView.tsx` — HAD cluster visualization
- `SubTaskPanel.tsx` — Sub-task details
- `ZoneOverlay.tsx` — Zone visualization overlay
- `LiveReasoningPanel.tsx` — Live reasoning display
