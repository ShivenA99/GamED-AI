# Model Selection & Configuration System Implementation

## Overview
Implemented a comprehensive model selection and configuration system that allows users to choose between open source and closed source models, and select different pipeline topologies dynamically.

## Changes Made

### 1. Backend Configuration Files

#### `backend/config.yaml` (NEW)
- Created centralized configuration file for model sources and topologies
- Defines available presets and default settings
- Provides human-readable descriptions for UI

#### `backend/app/config/agent_models.py`
- **Added new presets:**
  - `open_source`: Uses LOCAL and GROQ models only
  - `closed_source`: Uses OPENAI and ANTHROPIC models only
- **Added helper function:** `get_models_by_source_type()` to filter models by source type
- **Updated runtime config:** Changed from singleton to context-aware using `ContextVar` for per-run configuration

#### `backend/app/config/models.py`
- **Added `is_open_source` field** to `ModelConfig` dataclass
- **Marked open source models:** Set `is_open_source=True` for all LOCAL and GROQ models

### 2. Graph Compilation System

#### `backend/app/agents/graph.py`
- **Modified `get_compiled_graph()`:** Now accepts optional `topology` parameter
- **Dynamic topology selection:** Maps string topology names to `TopologyType` enums
- **Factory pattern:** Uses `create_topology()` from `topologies.py` instead of hardcoded `create_game_generation_graph()`

### 3. API Updates

#### `backend/app/routes/generate.py`
- **Added `GenerationConfig` Pydantic model:** Accepts `model_source`, `topology`, and `agent_config_preset`
- **Updated `/generate` endpoint:** Accepts configuration in request body
- **Dynamic preset selection:** Automatically selects `open_source` or `closed_source` preset based on model source
- **Updated `run_generation_pipeline()`:** Accepts `topology` and `agent_preset` parameters
- **Per-run environment variables:** Temporarily sets `AGENT_CONFIG_PRESET` for each run
- **Configuration storage:** Stores model source, topology, and preset in `PipelineRun.config_snapshot`

### 4. Frontend Updates

#### `frontend/src/app/page.tsx`
- **Added configuration UI:** Radio buttons for model source selection
- **Added topology dropdown:** Select from T0, T1, T2, T4, T5, T7
- **Updated API call:** Sends configuration in request body instead of query parameters
- **State management:** Added `modelSource` and `topology` state variables

#### `frontend/src/app/api/generate/route.ts`
- **Updated to accept config:** Parses config from request body
- **Passes config to backend:** Forwards configuration to backend API

### 5. Database Schema
- **Verified `PipelineRun.config_snapshot`:** Confirmed it can store nested configuration objects
- **Configuration persistence:** All run configurations are stored for audit and debugging

## Key Features

### Model Source Selection
- **Open Source:** Uses LOCAL (Ollama) and GROQ models - completely free
- **Closed Source:** Uses OpenAI and Anthropic models - higher quality but paid
- **Automatic preset mapping:** UI selection automatically maps to appropriate agent presets

### Topology Selection
- **T0:** Sequential Baseline - fastest, no validation
- **T1:** Sequential Validated - recommended for production
- **T2:** Actor-Critic - experimental
- **T4:** Self-Refine - iterative improvement
- **T5:** Multi-Agent Debate - consensus-based
- **T7:** Reflection with Memory - learning from past runs

### Per-Run Configuration
- **Context-aware:** Each pipeline run uses its own configuration
- **Thread-safe:** No interference between concurrent runs
- **Environment isolation:** Temporary environment variable changes don't affect other runs

## Backward Compatibility
- **Default behavior:** Falls back to `closed_source` + `T1` if no config provided
- **Environment variables:** Still respects `AGENT_CONFIG_PRESET` and `TOPOLOGY` as fallbacks
- **Existing runs:** Continue to work with default configuration

## Testing Checklist
- [ ] Open source preset uses only LOCAL/GROQ models
- [ ] Closed source preset uses only OPENAI/ANTHROPIC models
- [ ] Topology selection works for all supported topologies
- [ ] Configuration is properly stored in database
- [ ] Frontend UI updates correctly reflect selections
- [ ] Backend API validates and accepts configuration
- [ ] Per-run config doesn't affect concurrent runs
- [ ] Graph compilation succeeds for all topologies

## Configuration Examples

### Open Source Configuration
```yaml
model_source: open_source
topology: T1
agent_config_preset: open_source
```
Uses: local-llama, local-qwen-coder, groq-llama3-70b, etc.

### Closed Source Configuration
```yaml
model_source: closed_source
topology: T1
agent_config_preset: closed_source
```
Uses: claude-sonnet, gpt-4o, gpt-4-turbo, etc.

## Future Enhancements
- Add model performance metrics to UI
- Implement cost estimation based on selected configuration
- Add configuration presets/templates
- Support custom model configurations
- Add A/B testing for different topologies