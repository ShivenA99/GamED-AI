# Audit 14: V3 Pipeline Graph Wiring, Services, Routes, and Model Assignments

**Date**: 2026-02-11
**Scope**: Audit of `create_v3_graph()`, all Gemini/media services, `generate.py` routes, and `agent_models.py` model assignments against research findings from audits 01-09.

---

## Table of Contents

1. [Graph Wiring Audit](#1-graph-wiring-audit)
2. [Validation Retry Logic](#2-validation-retry-logic)
3. [Timeouts per Agent](#3-timeouts-per-agent)
4. [Drag-Drop-Only Assumptions](#4-drag-drop-only-assumptions)
5. [Services Audit](#5-services-audit)
6. [Routes Audit](#6-routes-audit)
7. [Model Assignments Audit](#7-model-assignments-audit)
8. [Gap Summary](#8-gap-summary)
9. [Recommended Changes](#9-recommended-changes)

---

## 1. Graph Wiring Audit

### 1.1 How `create_v3_graph()` Wires Agents

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/graph.py` (lines 1901-2016)

The V3 graph is a 12-node, 5-phase linear pipeline with 3 conditional retry loops:

```
Phase 0: input_enhancer -> domain_knowledge_retriever -> router
Phase 1: game_designer_v3 -> design_validator -> (retry or proceed)
Phase 2: scene_architect_v3 -> scene_validator -> (retry or proceed)
Phase 3: interaction_designer_v3 -> interaction_validator -> (retry or proceed)
Phase 4: asset_generator_v3
Phase 5: blueprint_assembler_v3 -> END
```

**Node Registration** (all use `wrap_agent_with_instrumentation`):
- Phase 0: `input_enhancer`, `domain_knowledge_retriever`, `router` (reused from V1)
- Phase 1: `game_designer_v3` (ReAct), `design_validator` (deterministic)
- Phase 2: `scene_architect_v3` (ReAct), `scene_validator` (deterministic)
- Phase 3: `interaction_designer_v3` (ReAct), `interaction_validator` (deterministic)
- Phase 4: `asset_generator_v3` (ReAct, max 8 iterations, 120s tool timeout)
- Phase 5: `blueprint_assembler_v3` (ReAct)

**Edge Wiring**:
- Entry point: `input_enhancer`
- Linear edges: `input_enhancer` -> `domain_knowledge_retriever` -> `router` -> `game_designer_v3`
- Phase 1: `game_designer_v3` -> `design_validator` -> conditional(`_v3_design_validation_router`)
- Phase 2: `scene_architect_v3` -> `scene_validator` -> conditional(`_v3_scene_validation_router`)
- Phase 3: `interaction_designer_v3` -> `interaction_validator` -> conditional(`_v3_interaction_validation_router`)
- Phase 4 to 5: `asset_generator_v3` -> `blueprint_assembler_v3` -> END

**Import Sources** (graph.py lines 214-221):
```python
from app.agents.game_designer_v3 import game_designer_v3_agent
from app.agents.design_validator import design_validator_agent
from app.agents.scene_architect_v3 import scene_architect_v3_agent
from app.agents.scene_validator import scene_validator_agent
from app.agents.interaction_designer_v3 import interaction_designer_v3_agent
from app.agents.interaction_validator import interaction_validator_agent as interaction_validator_v3_agent
from app.agents.asset_generator_v3 import asset_generator_v3_agent
from app.agents.blueprint_assembler_v3 import blueprint_assembler_v3_agent
```

### 1.2 Graph Selection in `get_compiled_graph()`

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/graph.py` (lines 2097-2176)

The V3 graph is created when `preset` is `"v3"` (case-insensitive). The preset constant is `PRESET_V3`. All graphs are compiled with a SQLite/Postgres checkpointer from `get_checkpointer()`.

**FINDING G-1**: The V3 preset is listed in `presets_needing_full_graph` in `generate.py` (line 858), so the `/generate` endpoint correctly dispatches to `create_v3_graph()`.

**FINDING G-2**: The `recursion_limit` is set to 80 in `generate.py` (line 869). With 12 nodes and max 2 retries per validation loop, the worst case is 12 + (2 * 3) = 18 node executions. 80 is adequate.

---

## 2. Validation Retry Logic

### 2.1 Design Validation Router

**File**: `graph.py` lines 1862-1872, `design_validator.py` line 277

```python
def _v3_design_validation_router(state):
    validation = state.get("design_validation_v3", {})
    if validation.get("passed", False):
        return "scene_architect_v3"
    retry = state.get("_v3_design_retries", 0)
    if retry >= 2:
        return "scene_architect_v3"  # Proceed anyway after 2 retries
    return "game_designer_v3"  # Retry
```

- **Max retries**: 2 (counter incremented by `design_validator` on each invocation)
- **Failure behavior**: Proceeds to `scene_architect_v3` even if validation fails after 2 retries (logged as warning)
- **Retry counter**: `_v3_design_retries` (initialized to 0 in `state.py` line 631)

### 2.2 Scene Validation Router

**File**: `graph.py` lines 1875-1885, `scene_validator.py` lines 37-97

Same pattern: max 2 retries via `_v3_scene_retries`, proceeds to `interaction_designer_v3` on failure.

### 2.3 Interaction Validation Router

**File**: `graph.py` lines 1888-1898, `interaction_validator.py` lines 639-711

Same pattern: max 2 retries via `_v3_interaction_retries`, proceeds to `asset_generator_v3` on failure.

### 2.4 Validation Retry Gaps

**FINDING V-1 (CRITICAL)**: The retry counter is incremented by the **validator** (e.g., `design_validator` increments `_v3_design_retries`), but the **router** checks it. This means on the first invocation, the validator sets `_v3_design_retries = 1`, and the router sees `retry = 1`. After the first retry, validator sets it to 2, and the router sees `retry = 2`, which triggers `>= 2` and proceeds. This means we get exactly **1 retry** (the designer runs twice total: initial + 1 retry), NOT 2 retries. The comment "max 2 retries" is misleading -- it is effectively 1 retry (2 total executions of the designer).

**FINDING V-2**: There is **no timeout** on the validation loop itself. If the designer agent is slow (e.g., 3-5 minutes per ReAct loop with Gemini Pro), the retry loop could take 10+ minutes. No circuit breaker exists.

**FINDING V-3**: When validation fails and the pipeline proceeds anyway (after max retries), the downstream agents receive **potentially invalid** design/scene/interaction specs. No degraded-mode handling exists -- the pipeline just continues with whatever the designer produced.

**FINDING V-4**: The validators are deterministic (no LLM calls) and fast. The bottleneck is always the ReAct agent being retried. Good design choice.

---

## 3. Timeouts per Agent

### 3.1 ReAct Agent Timeouts

The timeouts are configured per-agent in their `__init__` methods:

| Agent | `max_iterations` | `tool_timeout` | Model (gemini_only preset) |
|-------|-------------------|----------------|---------------------------|
| `game_designer_v3` | 10 (default) | 60s (default) | `gemini-2.5-pro` |
| `scene_architect_v3` | 10 (default) | 60s (default) | `gemini-2.5-pro` |
| `interaction_designer_v3` | 10 (default) | 60s (default) | `gemini-2.5-pro` |
| `asset_generator_v3` | **8** | **120s** | `gemini-2.5-flash` |
| `blueprint_assembler_v3` | 10 (default) | 60s (default) | `gemini-2.5-flash` |

**FINDING T-1**: `asset_generator_v3` has a 120s tool timeout because its tools (search_diagram_image, generate_diagram_image, detect_zones) involve external API calls and image processing. This is reasonable.

**FINDING T-2**: There is **no overall pipeline timeout**. The `run_generation_pipeline` function in `generate.py` has no global timeout. A stuck agent can hang indefinitely. The only protection is LangGraph's `recursion_limit=80`.

**FINDING T-3**: The LLM service has a per-call retry config (`max_retries=3`, `initial_delay=1.0`, `max_delay=30.0`, exponential backoff). Combined with 10 ReAct iterations, a single agent could theoretically take 10 * (3 retries * 30s max_delay + 60s tool_timeout) = ~900s = 15 minutes in the worst case.

---

## 4. Drag-Drop-Only Assumptions

### 4.1 Graph-Level Assumptions

**FINDING DD-1**: The V3 graph itself is **mechanic-agnostic**. It does not branch on mechanic type -- all mechanics flow through the same 5 phases. This is correct per research findings.

**FINDING DD-2**: The `router` node (reused from V1) routes by **template type** (INTERACTIVE_DIAGRAM, PHET_SIMULATION, etc.), not by mechanic type. In V3, `router` always passes to `game_designer_v3` regardless of template type. This means V3 currently only produces INTERACTIVE_DIAGRAM games.

### 4.2 Tool-Level Assumptions

**FINDING DD-3 (CRITICAL)**: The `asset_generator_v3` tools are **diagram-centric**. All 5 tools assume a single diagram image per scene with zone overlays:
- `search_diagram_image`: Searches for "educational diagram images"
- `generate_diagram_image`: Generates "clean unlabeled diagram image"
- `detect_zones`: Detects "interactive zones in diagram images"
- `submit_assets`: Validates per-scene `diagram_image_url` + `zones`

This works for **drag_drop**, **click_to_identify**, **trace_path**, and **description_matching** (all zone-based mechanics). However, it does NOT support:
- **Sequencing**: Needs per-item illustrations/cards, not a single diagram with zones
- **Sorting/Categories**: Needs item images and category visuals
- **Memory Match**: Needs pairs of card images (front/back)
- **Compare/Contrast**: Needs dual images (two subjects side by side or separate)
- **Branching Scenarios**: Needs scene-change images, character sprites, scenario backgrounds

**FINDING DD-4**: The `_MECHANIC_IMAGE_HINTS` dict in `asset_generator_tools.py` (lines 229-281) provides mechanic-specific prompting for image generation. This is good -- it tailors the diagram for each mechanic. But the underlying asset model (1 diagram + zones per scene) is still fundamentally diagram-only.

**FINDING DD-5**: The `blueprint_assembler_tools.py` assembler (line 871 area) converts scene data to frontend format assuming `diagram_image_url` + `zones[]` + `labels[]`. For mechanics like sequencing or memory match, the blueprint would need `items[]` with individual images, `card_pairs[]`, or `sequence_steps[]` -- none of which exist in the asset pipeline.

### 4.3 What Needs to Change for Mechanic-General Support

1. **New asset tools needed** (all using Gemini API):
   - `generate_item_illustrations`: Generate per-item card images for sequencing/sorting/memory
   - `generate_scene_background`: Generate a thematic scene background (not a labeled diagram)
   - `generate_card_pair_images`: Generate matching front/back card images for memory match
   - `generate_dual_comparison_images`: Generate two side-by-side or separate comparison images
   - `generate_character_sprite`: Generate character/scenario sprites for branching

2. **Modified `submit_assets` schema**: Accept mechanic-aware asset bundles:
   ```json
   {
     "scenes": {
       "1": {
         "diagram_image_url": "...",   // for diagram-based mechanics
         "zones": [...],
         "items": [...],               // for sequencing/sorting/memory
         "card_pairs": [...],          // for memory match
         "comparison_images": [...],   // for compare/contrast
         "background_image_url": "...",// for branching scenarios
       }
     }
   }
   ```

3. **Blueprint assembler changes**: The assembler needs to handle non-diagram asset types and populate the correct frontend config fields (sequenceConfig, sortingConfig, memoryMatchConfig, etc.) with image references.

---

## 5. Services Audit

### 5.1 Available Gemini Services

#### 5.1.1 GeminiService (`gemini_service.py`)

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/services/gemini_service.py`
**Purpose**: HAD v3 (Hierarchical Agentic DAG) zone detection and game design
**Client**: `google.genai.Client` (google-genai SDK)

**Available Methods**:
| Method | Model Default | Purpose | Vision? |
|--------|--------------|---------|---------|
| `detect_zones_with_polygons()` | `gemini-2.5-flash` | Zone detection with polygon output | Yes |
| `design_game()` | `gemini-3-flash` | Unified game design | Yes |
| `generate_text()` | `gemini-2.5-flash-lite` | Simple text generation | No |

**Available Models** (enum `GeminiModel`):
- `FLASH_LITE`: `gemini-2.5-flash-lite-preview-06-17` ($0.10/1M in, $0.40/1M out)
- `FLASH`: `gemini-2.5-flash` ($0.30/1M in, $2.50/1M out)
- `FLASH_3`: `gemini-3-flash-preview` ($0.50/1M in, $3.00/1M out)
- `PRO`: `gemini-2.5-pro` ($1.25/1M in, $10.00/1M out)

**Features**: Telemetry tracking, cost estimation, token counting, collision metadata

**FINDING S-1**: This service is NOT used by the V3 pipeline. It is only used by the HAD (V2.5) pipeline. The V3 pipeline uses `LLMService` for LLM calls and `diagram_image_generator.generate_with_gemini()` for image generation.

#### 5.1.2 GeminiDiagramService (`gemini_diagram_service.py`)

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/services/gemini_diagram_service.py`
**Purpose**: Diagram cleaning and zone detection for the hierarchical preset

**Available Methods**:
| Method | Model | Purpose | Vision? |
|--------|-------|---------|---------|
| `clean_diagram()` | `nano-banana-pro-preview` | Remove text labels via image editing | Yes (image output) |
| `detect_zones()` | `gemini-3-flash-preview` | Detect zone positions | Yes |

**FINDING S-2**: The `clean_diagram()` method is hardcoded to a flower-specific prompt ("Extract ONLY the flower illustration"). This is NOT general-purpose. The V3 pipeline's `generate_diagram_image_impl` tool does NOT use this service -- it uses `diagram_image_generator.generate_with_gemini()` directly.

**FINDING S-3**: Both `gemini_service.py` and `gemini_diagram_service.py` export a `get_gemini_service()` function, but they return **different service classes** (`GeminiService` vs `GeminiDiagramService`). This is a naming collision that could cause import confusion.

#### 5.1.3 Diagram Image Generator (`diagram_image_generator.py`)

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/agents/diagram_image_generator.py`
**Purpose**: Image generation using Gemini Imagen

**Available Methods**:
| Method | Model | Purpose |
|--------|-------|---------|
| `generate_with_gemini()` | configurable via `GEMINI_IMAGE_MODEL` env (default: `gemini-2.5-flash-image`) | Generate clean diagram images |
| `download_and_validate_image()` | N/A | Download and validate reference images |

**Features**: Reference image support, PIL validation, configurable model

**FINDING S-4**: This is the actual image generation backend used by V3's `generate_diagram_image_impl` tool. It uses `response_modalities=["image", "text"]` to get Gemini to generate images. The model default is `gemini-2.5-flash-image` (Nano Banana).

#### 5.1.4 MediaGenerationService (`media_generation_service.py`)

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/services/media_generation_service.py`
**Purpose**: Unified interface for generating various media assets

**Available Methods**:
| Method | Backend | Purpose |
|--------|---------|---------|
| `generate_image_dalle()` | OpenAI DALL-E 3 | DALL-E image generation |
| `generate_image_stable_diffusion()` | Replicate / MLX | Stable Diffusion |
| `fetch_image_url()` | HTTP fetch | Download and cache images |
| `generate_css_animation()` | Deterministic | CSS keyframe animations |
| `generate_asset()` | Dispatches | Unified asset generation |
| `generate_batch()` | Parallel/serial | Batch asset generation |

**Supported Generation Methods** (enum `GenerationMethod`):
- `NANOBANANA`: Nanobanana API (primary)
- `CSS_ANIMATION`: CSS-based animations
- `CACHED`: Pre-existing assets
- `FETCH_URL`: URL-based fetching
- `GEMINI_IMAGEN`: Deprecated
- `STABLE_DIFFUSION`: Replicate/MLX
- `DALLE`: OpenAI DALL-E 3

**FINDING S-5**: The `MediaGenerationService` is NOT used by the V3 pipeline at all. It is a legacy service from earlier versions. The V3 asset_generator_v3 tools bypass it entirely, going directly to `diagram_image_generator.generate_with_gemini()`.

**FINDING S-6**: The `GEMINI_IMAGEN` method is marked deprecated in favor of `NANOBANANA`, but the V3 pipeline uses `generate_with_gemini()` directly (which calls the same Gemini Imagen API). There is no unified interface.

#### 5.1.5 NanobananaService (`nanobanana_service.py`)

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/services/nanobanana_service.py`
**Purpose**: AI image generation via nanobanana API (third-party)
**Configuration**: `NANOBANANA_ENDPOINT` and `NANOBANANA_API_KEY` env vars

**FINDING S-7**: The Nanobanana service is a third-party API wrapper. It is NOT used by V3. The V3 pipeline generates images via Gemini directly.

#### 5.1.6 LLMService (`llm_service.py`)

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/services/llm_service.py`
**Purpose**: Unified LLM service for all agents (OpenAI, Anthropic, Gemini, Groq, Ollama)

This is the primary LLM backend for all V3 ReAct agents. It provides:
- `generate()`: Basic text generation
- `generate_for_agent()`: Agent-specific model/temperature config
- `generate_json()`: Structured JSON output
- `generate_with_tools()`: Tool calling (single-shot or ReAct mode)

The `ReActAgent` base class uses `generate_with_tools(mode="react")` for all V3 ReAct agents.

**FINDING S-8**: The LLM service supports Gemini tool calling via the `google.genai` SDK. It handles Gemini's function declaration format, including the `additionalProperties` limitation.

### 5.2 What Image Generation Capabilities Are Available via Gemini

**Gemini endpoints/methods available for asset generation**:

1. **Text-to-Image** (via `generate_with_gemini()`):
   - Model: `gemini-2.5-flash-image` (default) or `gemini-3-pro-image-preview`
   - Input: text prompt + optional reference image
   - Output: PNG image
   - Config: `response_modalities=["image", "text"]`
   - Capability: Can generate clean educational diagrams, remove text from reference images

2. **Vision Analysis** (via `GeminiService.detect_zones_with_polygons()`):
   - Model: `gemini-2.5-flash` (default)
   - Input: image + text prompt
   - Output: JSON with polygon zones
   - Config: `response_mime_type="application/json"`, `temperature=0.1`

3. **Vision + Game Design** (via `GeminiService.design_game()`):
   - Model: `gemini-3-flash-preview` (default)
   - Input: image + zones + pedagogical context
   - Output: JSON with game_plan, scene_structure, scene_assets, scene_interactions

4. **Image Editing/Cleaning** (via `GeminiDiagramService.clean_diagram()`):
   - Model: `nano-banana-pro-preview`
   - Input: image + edit instructions
   - Output: edited PNG image
   - Config: `response_modalities=["image", "text"]`

### 5.3 What Is Missing for Multi-Mechanic Asset Generation

**ALL new asset generation tools MUST use Gemini API**. Here is what is available and what is missing:

| Asset Type | Gemini Method Available? | Current Implementation | Gap |
|-----------|--------------------------|------------------------|-----|
| Diagram image (labeled/unlabeled) | Yes - `gemini-2.5-flash-image` | `generate_with_gemini()` | None |
| Zone detection on diagram | Yes - `gemini-2.5-flash` vision | `detect_zones_impl()` | None |
| Per-item illustration (for sequencing) | Yes - same Gemini Image API | NOT IMPLEMENTED | **HIGH** |
| Card content images (for memory match) | Yes - same Gemini Image API | NOT IMPLEMENTED | **HIGH** |
| Scene backgrounds (for branching) | Yes - same Gemini Image API | NOT IMPLEMENTED | **MEDIUM** |
| Character sprites | Yes - same Gemini Image API (limited) | NOT IMPLEMENTED | **MEDIUM** |
| Dual-image comparison | Yes - 2x Gemini Image calls | NOT IMPLEMENTED | **HIGH** |
| Image editing (text removal) | Yes - Nano Banana | `clean_diagram()` in GeminiDiagramService | Hardcoded flower prompt |
| CSS animations | N/A - deterministic | `generate_animation_css_impl()` | None |

**How to implement missing capabilities**:

All missing asset types can be generated using the SAME Gemini Image API (`gemini-2.5-flash-image`). The key is:
1. Use `response_modalities=["image", "text"]`
2. Craft mechanic-specific prompts (e.g., "Generate a single card-sized illustration of [item] in educational style")
3. Call `client.models.generate_content()` with the appropriate prompt
4. Save the generated image locally

The `generate_with_gemini()` function in `diagram_image_generator.py` is already a working template. New tools just need different prompts and output schemas.

---

## 6. Routes Audit

### 6.1 Blueprint Save and Serve Flow

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/routes/generate.py`

**Save Flow** (lines 988-1004):
1. When `generation_complete=True` and `final_state["blueprint"]` exists:
2. Creates a `Visualization` record with: `process_id`, `template_type` (from `blueprint.templateType`), `blueprint` (full dict), `asset_urls`, `pedagogical_context`, `game_plan`, `story_data`
3. Template type is extracted via `blueprint.get("templateType", "UNKNOWN")`

**Serve Flow** (lines 662-718):
1. `GET /generate/{process_id}/blueprint` queries `Visualization` by `process_id`
2. Returns: `process_id`, `template_type`, `blueprint`, `story_data`, `pedagogical_context`, `game_plan`
3. **Image URL processing** (lines 686-708): For the root-level `diagram` object:
   - If cleaned image exists locally: sets `assetUrl` to `/api/assets/{question_id}/cleaned/diagram_cleaned.png`
   - If external URL: proxies via `/api/proxy/image?url=...`
   - If already a local asset URL: keeps as-is

**FINDING R-1 (CRITICAL)**: The blueprint serve endpoint ONLY processes image URLs for the **root-level** `blueprint.diagram` object. For **multi-scene** games, each scene has its own `diagram.assetUrl` inside `game_sequence.scenes[].diagram.assetUrl`. These per-scene image URLs are **NOT proxied or cleaned**. They remain as raw URLs (local file paths or external URLs) which may not be accessible from the frontend.

**FINDING R-2**: The `_build_agent_outputs()` function (lines 220-273) records outputs from V1 agents (`input_enhancer`, `diagram_image_retriever`, `diagram_zone_labeler`, `router`, `game_planner`, `scene_generator`, `blueprint_generator`, etc.) but does NOT record V3-specific agent outputs (`game_designer_v3`, `scene_architect_v3`, `interaction_designer_v3`, `asset_generator_v3`, `blueprint_assembler_v3`). This means the pipeline run JSON saved in `pipeline_outputs/` lacks V3 agent output data.

### 6.2 Image URL Proxying

**Available Endpoints**:

| Endpoint | Purpose | SSRF Protection | Cache |
|----------|---------|-----------------|-------|
| `GET /proxy/image?url=...` | Proxy external images | Yes (blocks private IPs) | 1hr cache header |
| `GET /assets/{qid}/cleaned/diagram_cleaned.png` | Serve cleaned diagrams | No (local file) | 1hr cache header |
| `GET /assets/{qid}/generated/diagram.png` | Serve generated diagrams | No (local file) | 1hr cache header |
| `GET /assets/workflow/{filename}` | Serve workflow images | No (filename sanitization) | 1hr cache header |

**FINDING R-3**: There is no endpoint for serving V3-generated assets from `pipeline_outputs/v3_assets/{run_id}/`. The V3 `asset_generator_v3` saves images to this directory, but the frontend cannot access them because no route serves files from there.

**FINDING R-4**: The generated diagram endpoint (`/assets/{qid}/generated/diagram.png`) searches for images keyed by `question_id`, but V3 saves images keyed by `run_id` (in `pipeline_outputs/v3_assets/{run_id}/`). This ID mismatch means V3-generated images are not servable via this endpoint.

### 6.3 Multi-Scene Image Handling Gaps

**FINDING R-5**: The blueprint assembler creates `game_sequence.scenes[i].diagram.assetUrl` with values like:
- Local file path: `pipeline_outputs/v3_assets/abc123/generated_heart_1234.png` (NOT a URL, not servable)
- External URL: `https://example.com/image.png` (not proxied, CORS issues)

Neither is correctly handled by the existing routes. The frontend would need:
- A route like `GET /assets/v3/{run_id}/{filename}` to serve V3-generated local images
- The blueprint serve endpoint to proxy/rewrite ALL scene image URLs, not just root-level

**FINDING R-6**: The `save_pipeline_run()` call in the finally block (line 1044) passes `topology="T1"` hardcoded, even for V3 runs. This is incorrect metadata.

---

## 7. Model Assignments Audit

### 7.1 V3 Agent Model Assignments

**File**: `/Users/shivenagarwal/GamifyAssessment/backend/app/config/agent_models.py`

Only the `gemini_only` preset (lines 671-776) has V3 agent assignments. All other presets (cost_optimized, quality_optimized, balanced, etc.) do NOT list V3 agents, meaning they fall back to the default model.

**V3 assignments in `gemini_only` preset**:

| Agent | Model | Tier | Cost (per 1M tokens) | Notes |
|-------|-------|------|---------------------|-------|
| `game_designer_v3` | `gemini-2.5-pro` | Premium | $1.25 in / $10.00 out | ReAct, creative design |
| `scene_architect_v3` | `gemini-2.5-pro` | Premium | $1.25 in / $10.00 out | ReAct, multi-tool workflow |
| `interaction_designer_v3` | `gemini-2.5-pro` | Premium | $1.25 in / $10.00 out | ReAct, multi-tool workflow |
| `asset_generator_v3` | `gemini-2.5-flash` | Balanced | $0.30 in / $2.50 out | Multi-step asset ops |
| `blueprint_assembler_v3` | `gemini-2.5-flash` | Balanced | $0.30 in / $2.50 out | ReAct assembly + repair |
| `asset_orchestrator_v3` | `gemini-2.5-flash` | Balanced | (legacy) | Not used in V3 graph |
| `asset_spec_builder` | `gemini-2.5-flash-lite` | Fast | (legacy) | Not used in V3 graph |

**FINDING M-1**: The model assignments are CORRECT for the V3 pipeline. Per the memory notes: "scene_architect_v3 + interaction_designer_v3 MUST use gemini-2.5-pro (not flash). Flash doesn't follow multi-tool workflows (stops at 3 iterations without calling submit tools)." This is correctly configured.

**FINDING M-2**: `game_designer_v3` uses `gemini-2.5-pro` which is the most expensive model. This is justified because it must produce a complete, multi-scene game design with mechanics, difficulty, and scoring in a single ReAct loop. The temperature is 0.7 (creative) which is appropriate.

**FINDING M-3**: `asset_generator_v3` uses `gemini-2.5-flash` (not pro). This is reasonable since its tools (search, generate, detect) do the heavy lifting, and the LLM is mainly orchestrating tool calls. Flash is adequate for orchestration.

**FINDING M-4**: `blueprint_assembler_v3` uses `gemini-2.5-flash`. This is appropriate since its tools (assemble, validate, repair, submit) are deterministic. The LLM only needs to call tools in the right order.

### 7.2 Missing Model Assignments

**FINDING M-5**: The `design_validator`, `scene_validator`, and `interaction_validator` agents are NOT listed in any preset's model assignments. They are deterministic (no LLM calls), so this is correct -- they don't need model assignments.

**FINDING M-6**: Only the `gemini_only` preset has V3 agent assignments. If a user selects any other preset (balanced, cost_optimized, etc.) and pipeline_preset=v3, the V3 agents will fall back to the preset's `default_model`. For example:
- `balanced` default: `claude-sonnet` -- V3 agents would use Claude Sonnet
- `cost_optimized` default: `claude-haiku` -- V3 agents would use Claude Haiku
- `local_only` default: `local-qwen-coder` -- V3 agents would use Qwen 7B locally

This could cause failures because:
1. Claude/GPT models may not follow the same tool-calling patterns as Gemini
2. Local models (Qwen 7B) cannot reliably do multi-step ReAct loops with 5+ tools
3. The `generate_with_gemini()` image generation function ALWAYS uses Gemini regardless of the agent model -- but the orchestration quality degrades with weaker models

**FINDING M-7**: The `max_tokens` for `game_designer_v3` is 16384 (line 774). This is only set in the `gemini_only` preset. Other presets use the default 4096, which may be insufficient for a multi-scene game design JSON.

### 7.3 Flash vs Pro Assessment for Multi-Mechanic Workloads

Based on the research findings (MEMORY.md: "Flash doesn't follow multi-tool workflows"):

| Agent | Current Model | Correct for Multi-Mechanic? | Notes |
|-------|--------------|----------------------------|-------|
| `game_designer_v3` | `gemini-2.5-pro` | YES | Must produce complex multi-mechanic designs with scoring, difficulty, and per-mechanic configs |
| `scene_architect_v3` | `gemini-2.5-pro` | YES | Must call `generate_mechanic_content` tool to produce per-mechanic layouts and then submit |
| `interaction_designer_v3` | `gemini-2.5-pro` | YES | Must call `enrich_mechanic_content` tool for each mechanic type and then submit |
| `asset_generator_v3` | `gemini-2.5-flash` | MAYBE | For diagram-only mechanics, flash is fine. For multi-mechanic (sequencing, memory, etc.), the agent needs to call NEW tools (item illustrations, card images) -- may need pro for reliable multi-tool orchestration |
| `blueprint_assembler_v3` | `gemini-2.5-flash` | YES | Tools are deterministic; flash is adequate for orchestration |

**FINDING M-8**: When new asset generation tools are added for non-diagram mechanics, `asset_generator_v3` may need to be upgraded to `gemini-2.5-pro` to reliably orchestrate 8+ tools across multiple scenes. Flash tends to stop after 3-4 tool calls.

---

## 8. Gap Summary

### Critical Gaps (Must Fix)

| ID | Category | Description | Impact |
|----|----------|-------------|--------|
| DD-3 | Asset Pipeline | Asset tools are diagram-only; no support for per-item illustrations, card images, dual images | Sequencing, memory, sorting, compare, branching mechanics produce empty/broken games |
| R-1 | Routes | Multi-scene blueprint image URLs not proxied/rewritten | Multi-scene games show broken images |
| R-3 | Routes | No route to serve V3-generated images from `pipeline_outputs/v3_assets/` | V3-generated images not accessible from frontend |
| R-4 | Routes | ID mismatch: routes use `question_id`, V3 saves by `run_id` | V3 image serving fails |
| V-1 | Validation | "Max 2 retries" is actually max 1 retry (2 total executions) | Lower quality tolerance than expected |

### High-Priority Gaps

| ID | Category | Description | Impact |
|----|----------|-------------|--------|
| DD-5 | Blueprint | Assembler assumes diagram+zones model; no per-mechanic asset bundles | Non-diagram mechanics produce incomplete blueprints |
| R-2 | Routes | `_build_agent_outputs()` ignores V3 agent outputs | Observability/debugging degraded for V3 |
| R-6 | Routes | Topology hardcoded to "T1" for all pipeline saves | Incorrect run metadata |
| M-6 | Models | Only `gemini_only` preset has V3 agent configs; other presets use fallback defaults | V3 with non-Gemini presets may fail |
| S-2 | Services | `GeminiDiagramService.clean_diagram()` hardcoded to flower prompt | Cannot clean non-flower diagrams |
| S-3 | Services | `get_gemini_service()` naming collision between two services | Import confusion |

### Medium-Priority Gaps

| ID | Category | Description | Impact |
|----|----------|-------------|--------|
| T-2 | Timeouts | No overall pipeline timeout | Stuck agents hang indefinitely |
| V-2 | Validation | No timeout on retry loops | Slow agents extend pipeline time |
| V-3 | Validation | No degraded-mode handling after failed retries | Downstream agents receive invalid specs |
| M-7 | Models | `game_designer_v3` max_tokens=16384 only in gemini_only preset | Other presets may truncate design output |
| M-8 | Models | `asset_generator_v3` may need pro model for multi-mechanic orchestration | Complex asset workflows may fail with flash |
| S-1 | Services | `GeminiService` not used by V3 (uses LLMService instead) | Wasted service code; zone polygon detection not leveraged |
| S-5 | Services | `MediaGenerationService` not used by V3 | Multiple unused service layers |

### Low-Priority Gaps

| ID | Category | Description | Impact |
|----|----------|-------------|--------|
| S-6 | Services | GEMINI_IMAGEN deprecated in MediaGenerationService but Gemini Image still used directly | Inconsistent API surface |
| S-7 | Services | NanobananaService not used by V3 | Dead code for V3 |
| G-2 | Graph | recursion_limit=80 is generous but not harmful | Minor config overhead |

---

## 9. Recommended Changes

### 9.1 Priority 1: V3 Image Serving (Fixes R-1, R-3, R-4)

Add a new route to serve V3-generated assets:

```python
# In generate.py or a new v3_assets.py route file

@router.get("/assets/v3/{run_id}/{filename}")
async def serve_v3_asset(run_id: str, filename: str):
    """Serve V3-generated assets (diagrams, item images, etc.)."""
    import re
    if not re.match(r'^[a-zA-Z0-9_\-]+$', run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id")
    if not re.match(r'^[a-zA-Z0-9_\-]+\.(png|jpg|jpeg|svg|gif|webp)$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = Path("pipeline_outputs/v3_assets") / run_id / filename
    if not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="image/png", headers={
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
    })
```

Modify the blueprint serve endpoint to rewrite ALL scene image URLs:

```python
# In get_generated_blueprint(), after loading blueprint:
if isinstance(blueprint, dict):
    # Process all scene diagram URLs (multi-scene)
    game_seq = blueprint.get("game_sequence", {})
    for scene in game_seq.get("scenes", []):
        diagram = scene.get("diagram", {})
        asset_url = diagram.get("assetUrl", "")
        if asset_url.startswith("pipeline_outputs/v3_assets/"):
            # Rewrite local path to API URL
            parts = asset_url.split("/")
            run_id = parts[2] if len(parts) > 2 else ""
            filename = parts[-1] if parts else ""
            diagram["assetUrl"] = f"/api/assets/v3/{run_id}/{filename}"
        elif asset_url.startswith("http"):
            encoded = urllib.parse.quote(asset_url, safe="")
            diagram["assetUrl"] = f"/api/proxy/image?url={encoded}"
```

### 9.2 Priority 2: New Asset Generation Tools (Fixes DD-3, DD-5)

Create new tools in `asset_generator_tools.py` using the existing `generate_with_gemini()` function:

```python
async def generate_item_illustration_impl(
    item_label: str,
    description: str,
    style: str = "clean educational card",
    dimensions: Dict[str, int] = {"width": 256, "height": 256},
) -> Dict[str, Any]:
    """Generate a single-item illustration for sequencing/sorting/memory cards."""
    from app.agents.diagram_image_generator import generate_with_gemini
    prompt = (
        f"Generate a single clear illustration of '{item_label}': {description}. "
        f"Style: {style}. Card-sized, centered, white background, no text."
    )
    return await generate_with_gemini(prompt=prompt, dimensions=dimensions)
```

Register as tool in `register_asset_generator_tools()`.

### 9.3 Priority 3: Fix _build_agent_outputs (Fix R-2)

Add V3 agent output recording:

```python
# In _build_agent_outputs():
record("game_designer_v3", state.get("game_design_v3"))
record("design_validator", state.get("design_validation_v3"))
record("scene_architect_v3", state.get("scene_specs_v3"))
record("scene_validator", state.get("scene_validation_v3"))
record("interaction_designer_v3", state.get("interaction_specs_v3"))
record("interaction_validator", state.get("interaction_validation_v3"))
record("asset_generator_v3", state.get("generated_assets_v3"))
record("blueprint_assembler_v3", state.get("blueprint"))
```

### 9.4 Priority 4: V3 Model Assignments for All Presets (Fix M-6)

Add V3 agent entries to the `balanced`, `cost_optimized`, and `quality_optimized` presets:

```python
# In balanced preset agent_models:
"game_designer_v3": "gpt-4o",           # or "claude-sonnet"
"scene_architect_v3": "gpt-4o",
"interaction_designer_v3": "gpt-4o",
"asset_generator_v3": "gpt-4o-mini",    # orchestration only
"blueprint_assembler_v3": "gpt-4o-mini",
```

### 9.5 Priority 5: Fix Retry Count (Fix V-1)

Change the router condition from `>= 2` to `>= 3` for true 2 retries:

```python
def _v3_design_validation_router(state):
    validation = state.get("design_validation_v3", {})
    if validation.get("passed", False):
        return "scene_architect_v3"
    retry = state.get("_v3_design_retries", 0)
    if retry >= 3:  # Changed from 2 to 3 for true 2 retries
        logger.warning("V3: Design validation failed after 2 retries, proceeding anyway")
        return "scene_architect_v3"
    return "game_designer_v3"
```

Apply same fix to `_v3_scene_validation_router` and `_v3_interaction_validation_router`.

### 9.6 Priority 6: Fix Topology Metadata (Fix R-6)

```python
# In run_generation_pipeline() finally block, line 1048:
save_pipeline_run(
    run_id=process_id,
    ...
    topology=pipeline_preset or topology,  # Fixed: was hardcoded "T1"
    ...
)
```

---

## Appendix A: Service Dependency Map

```
V3 Pipeline Service Dependencies:

ReAct Agents (5)
  └── LLMService (llm_service.py)
        ├── google.genai Client (for Gemini models)
        ├── AsyncOpenAI (for GPT/Groq/Ollama)
        └── AsyncAnthropic (for Claude)

Asset Generator Tools (5)
  ├── search_diagram_image
  │     ├── image_retrieval.py (web search)
  │     └── generate_diagram_image_impl (auto-clean)
  │           └── diagram_image_generator.generate_with_gemini()
  │                 └── google.genai Client (gemini-2.5-flash-image)
  ├── generate_diagram_image
  │     └── diagram_image_generator.generate_with_gemini()
  ├── detect_zones
  │     ├── gemini_sam3_zone_detector (Gemini + SAM3)
  │     ├── gemini_zone_detector (Gemini only)
  │     └── qwen_zone_detector (Qwen VL, fallback)
  ├── generate_animation_css (deterministic, no service)
  └── submit_assets (deterministic, no service)

NOT used by V3:
  - GeminiService (gemini_service.py) -- HAD V2.5 only
  - GeminiDiagramService (gemini_diagram_service.py) -- hierarchical preset only
  - MediaGenerationService (media_generation_service.py) -- legacy
  - NanobananaService (nanobanana_service.py) -- not integrated
```

## Appendix B: Blueprint Image URL Flow

```
Current flow (broken for V3 multi-scene):

1. asset_generator_v3 saves image to:
   pipeline_outputs/v3_assets/{run_id}/generated_{slug}_{timestamp}.png

2. blueprint_assembler_v3 sets:
   scene.diagram.assetUrl = "pipeline_outputs/v3_assets/{run_id}/generated_*.png"
   (raw local file path, NOT a URL)

3. generate.py saves blueprint to Visualization table

4. GET /generate/{pid}/blueprint returns blueprint
   - Only rewrites blueprint.diagram.assetUrl (root level)
   - Does NOT rewrite game_sequence.scenes[].diagram.assetUrl

5. Frontend receives local file path as assetUrl -> broken image

Required flow:
1. Same
2. Same
3. Same
4. Rewrite ALL scene diagram URLs to /api/assets/v3/{run_id}/{filename}
5. Add GET /assets/v3/{run_id}/{filename} route
```

## Appendix C: Gemini API Capabilities for New Asset Tools

All new tools should use `generate_with_gemini()` as template:

```python
# Available Gemini Image generation config:
client.models.generate_content(
    model="gemini-2.5-flash-image",  # or gemini-3-pro-image-preview
    contents=[prompt_text, optional_reference_image],
    config=types.GenerateContentConfig(
        response_modalities=["image", "text"],  # REQUIRED for image output
    )
)
```

**Supported use cases**:
- Text-to-image: Pass only text prompt
- Image editing: Pass text prompt + reference PIL Image
- Style transfer: Pass "Recreate this image in [style]" + reference
- Multi-image: Call the API multiple times (no batch support)

**Limitations**:
- No batch/parallel image generation in a single API call
- Max ~1024px output resolution
- Rate limits: varies by model tier
- No video/GIF generation
- No SVG output (raster only)
