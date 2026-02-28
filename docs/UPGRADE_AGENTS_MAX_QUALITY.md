# Direct Agent Upgrade Guide - Maximum Quality for M4 16GB

## Quick Summary

To maximize quality on your M4 MacBook Pro 16GB, upgrade these agents:

1. **Reasoning/Validation Agents** → DeepSeek-R1 7B (best reasoning model that fits in 16GB)
2. **JSON Generation Agents** → Keep Qwen2.5 7B (already optimal)
3. **Code Generation** → Keep DeepSeek Coder 6.7B (already optimal)
4. **Vision Tasks** → **Two options:**
   - **Option A (Quality)**: Keep Qwen2.5-VL 7B (best quality, already optimal)
   - **Option B (Speed + Quality)**: Add FastVLM-1.5B for speed-critical tasks (85x faster, MLX framework)

## Step 1: Install DeepSeek-R1 7B Model

```bash
# Pull the best reasoning model for your hardware
ollama pull deepseek-r1:7b
```

This model is specifically designed for advanced reasoning and will significantly improve:
- Blueprint validation accuracy
- Judge/critic evaluation quality
- Code verification logic

## Step 2: Add Model to Registry

Add this to `backend/app/config/models.py` in the `MODEL_REGISTRY` dictionary (around line 290):

```python
"local-deepseek-r1-7b": ModelConfig(
    provider=ModelProvider.LOCAL,
    model_id="deepseek-r1:7b",
    tier=ModelTier.PREMIUM,  # Best quality tier
    max_tokens=8192,
    temperature=0.3,  # Lower for reasoning tasks
    cost_per_1k_input=0.0,
    cost_per_1k_output=0.0,
    context_window=64000,
    supports_json_mode=True,
    supports_vision=False
),
```

## Step 3: Update Agent Assignments

In `backend/app/config/agent_models.py`, update the `local_only` preset (around line 309):

**Current assignments:**
```python
"blueprint_validator": "local-llama",      # Simple validation
"code_verifier": "local-llama",            # Simple verification
"critic": "local-qwen-coder",              # Analysis
"judge": "local-qwen-coder",               # Reasoning
```

**Upgrade to:**
```python
"blueprint_validator": "local-deepseek-r1-7b",  # Enhanced reasoning validation
"code_verifier": "local-deepseek-r1-7b",         # Better code logic verification
"critic": "local-deepseek-r1-7b",                # Advanced critique
"judge": "local-deepseek-r1-7b",                 # Best reasoning for judgment
```

**Also update temperatures for reasoning models:**
```python
"blueprint_validator": 0.2,  # Lower for deterministic reasoning
"code_verifier": 0.2,        # Lower for deterministic verification
"critic": 0.3,                # Slightly higher for nuanced critique
"judge": 0.2,                 # Lower for consistent judgment
```

## Step 4: Verify Your Current Optimal Models

These are already the best for your hardware - **keep them**:

✅ **Qwen2.5 7B** (`local-qwen-coder`)
- Used for: `blueprint_generator`, `scene_generator`, `diagram_spec_generator`
- Why: Best JSON/structured output generation
- Status: Already optimal

✅ **DeepSeek Coder 6.7B** (`local-deepseek-coder`)
- Used for: `code_generator`
- Why: Best code generation model available
- Status: Already optimal

✅ **Qwen2.5-VL 7B** (via Ollama)
- Used for: `qwen_label_remover`, `qwen_zone_detector`
- Why: Best quality vision-language model for your hardware
- Status: Already optimal for quality
- **Upgrade Option**: Add FastVLM-1.5B for speed (see Vision Upgrades section)

## Complete Upgraded Configuration

Here's the complete `local_only` preset with maximum quality:

```python
"local_only": AgentModelConfig(
    default_model="local-qwen-coder",  # Best for JSON generation
    default_temperature=0.3,
    agent_models={
        "input_enhancer": "local-qwen-coder",      # Good at analysis
        "router": "local-qwen-coder",              # Good at classification
        "game_planner": "local-qwen-coder",        # Structured output
        "scene_generator": "local-qwen-coder",     # Critical: best for JSON
        "story_generator": "local-qwen-coder",     # Legacy
        "blueprint_generator": "local-qwen-coder", # Critical: best for JSON
        "diagram_spec_generator": "local-qwen-coder",
        "diagram_svg_generator": "local-llama",
        "blueprint_validator": "local-deepseek-r1-7b",  # ⬆️ UPGRADED: Best reasoning
        "code_generator": "local-deepseek-coder",  # Best for code
        "code_verifier": "local-deepseek-r1-7b",        # ⬆️ UPGRADED: Better logic
        "critic": "local-deepseek-r1-7b",               # ⬆️ UPGRADED: Advanced critique
        "judge": "local-deepseek-r1-7b",                # ⬆️ UPGRADED: Best reasoning
        "supervisor": "local-qwen-coder",          # Coordination
        "proposer": "local-qwen-coder",            # Proposals
    },
    agent_temperatures={
        "input_enhancer": 0.3,
        "router": 0.2,
        "game_planner": 0.4,
        "scene_generator": 0.2,
        "story_generator": 0.4,
        "blueprint_generator": 0.2,
        "diagram_spec_generator": 0.2,
        "diagram_svg_generator": 0.1,
        "blueprint_validator": 0.2,  # ⬆️ Lower for deterministic reasoning
        "code_generator": 0.2,
        "code_verifier": 0.2,         # ⬆️ Lower for deterministic verification
        "critic": 0.3,                # ⬆️ Slightly higher for nuanced critique
        "judge": 0.2,                 # ⬆️ Lower for consistent judgment
        "supervisor": 0.3,
        "proposer": 0.7,
    },
)
```

## Expected Quality Improvements

### Blueprint Validator
- **Before**: Simple schema validation with `local-llama`
- **After**: Advanced semantic reasoning with DeepSeek-R1 7B
- **Impact**: Better detection of logical inconsistencies, pedagogical misalignments

### Judge Agent (T2/T5 topologies)
- **Before**: Basic evaluation with `local-qwen-coder`
- **After**: Chain-of-thought reasoning with DeepSeek-R1 7B
- **Impact**: More thorough quality assessment, better scoring

### Critic Agent (T2/T4 topologies)
- **Before**: Simple analysis with `local-qwen-coder`
- **After**: Advanced critique with reasoning chains
- **Impact**: More actionable feedback, better iteration suggestions

### Code Verifier
- **Before**: Basic verification with `local-llama`
- **After**: Logical code analysis with DeepSeek-R1 7B
- **Impact**: Better detection of bugs, logic errors, edge cases

## Memory Usage

With these upgrades:
- **DeepSeek-R1 7B**: ~4.5GB (Q4_K_M quantization)
- **Qwen2.5 7B**: ~4.2GB
- **DeepSeek Coder 6.7B**: ~3.8GB
- **Qwen2.5-VL 7B**: ~4.5GB (when used)

**Total**: Models are loaded on-demand, so you won't have all loaded simultaneously. With 16GB, you can comfortably run any single 7B model with room for context and system overhead.

## Testing the Upgrade

After making changes, test with:

```bash
# Test blueprint validation
PYTHONPATH=. python backend/scripts/test_blueprint_integration.py

# Test full pipeline
PYTHONPATH=. python backend/scripts/test_label_diagram.py
```

## Alternative: Environment Variable Override

If you want to test without modifying code, use environment variables:

```bash
export AGENT_MODEL_BLUEPRINT_VALIDATOR=local-deepseek-r1-7b
export AGENT_MODEL_JUDGE=local-deepseek-r1-7b
export AGENT_MODEL_CRITIC=local-deepseek-r1-7b
export AGENT_MODEL_CODE_VERIFIER=local-deepseek-r1-7b

export AGENT_TEMPERATURE_BLUEPRINT_VALIDATOR=0.2
export AGENT_TEMPERATURE_JUDGE=0.2
export AGENT_TEMPERATURE_CRITIC=0.3
export AGENT_TEMPERATURE_CODE_VERIFIER=0.2
```

## Vision Task Upgrades

### Current Setup
You're using **Qwen2.5-VL 7B** via Ollama, which provides excellent quality. However, there are faster alternatives:

### Option A: Keep Qwen2.5-VL 7B (Best Quality)
- **Status**: Already optimal for quality
- **Speed**: ~15-20 tokens/sec on M4
- **Use Case**: Best for accuracy-critical vision tasks
- **No changes needed** - you already have the best quality VLM

### Option B: Add FastVLM-1.5B for Speed (Recommended Hybrid Approach)
- **Speed**: 7.9x faster than Qwen2.5-VL
- **Quality**: Slightly lower but still excellent
- **Size**: ~3GB (fits easily in 16GB)
- **Framework**: MLX (Apple's native framework, not Ollama)
- **Best For**: Quick label detection, initial zone identification

**Hybrid Strategy:**
1. Use **FastVLM-1.5B** for fast initial detection/analysis
2. Use **Qwen2.5-VL 7B** for final quality-critical tasks

**Implementation:**
1. Install MLX:
   ```bash
   pip install mlx mlx-lm
   ```

2. Create FastVLM service (`backend/app/services/fastvlm_service.py`):
   - Load FastVLM-1.5B model from HuggingFace
   - Implement fast path for simple vision tasks
   - Fallback to Qwen2.5-VL for complex tasks

3. Update vision agents:
   - `qwen_label_remover`: Use FastVLM for quick detection, Qwen2.5-VL for final accuracy
   - `qwen_zone_detector`: Use FastVLM for initial zones, Qwen2.5-VL for refinement

**Expected Improvement:**
- 7-8x faster vision processing for simple tasks
- Maintain quality with Qwen2.5-VL for complex tasks
- Better overall pipeline speed

### Option C: FastVLM-0.5B (Ultra-Fast)
- **Speed**: 85x faster than LLaVA-OneVision
- **Size**: ~1GB
- **Use Case**: Ultra-fast pre-filtering, simple tasks only
- **Trade-off**: Lower quality, best for speed-critical simple tasks

## Summary

**What to change:**
1. Add `local-deepseek-r1-7b` to model registry
2. Update 4 agents: `blueprint_validator`, `judge`, `critic`, `code_verifier`
3. Lower temperatures for reasoning tasks (0.2-0.3)
4. **(Optional)** Add FastVLM-1.5B for vision speed improvements

**What to keep:**
- All JSON generation agents (already optimal)
- Code generator (already optimal)
- Qwen2.5-VL 7B for vision quality (already optimal)

**Vision Upgrade Recommendation:**
- **If speed matters**: Add FastVLM-1.5B with hybrid approach
- **If quality is paramount**: Keep Qwen2.5-VL 7B only

**Result:**
Maximum quality within your 16GB hardware constraints, with optional speed improvements for vision tasks!
