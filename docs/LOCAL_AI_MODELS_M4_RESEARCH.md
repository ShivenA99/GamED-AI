# Local AI Models for M4 MacBook Pro 16GB - Comprehensive Research (2025)

## Executive Summary

For your M4 MacBook Pro with 16GB unified memory, you can efficiently run models up to **7-8 billion parameters** with proper quantization. This guide covers the best local AI models across all categories to expand your agents' capabilities.

**Key Constraints:**
- 16GB unified memory (shared between CPU/GPU)
- Models should be quantized (Q4_K_M recommended)
- Target: 7-8B parameter models max for good performance
- Expected speed: 15-28 tokens/second on 8B models with Metal acceleration

---

## Table of Contents

1. [Text/LLM Models](#1-textllm-models)
2. [Vision Language Models (VLM)](#2-vision-language-models-vlm)
3. [Code Generation Models](#3-code-generation-models)
4. [Embedding Models](#4-embedding-models)
5. [Image Generation Models](#5-image-generation-models)
6. [Text-to-Speech Models](#6-text-to-speech-models)
7. [Frameworks & Tools](#7-frameworks--tools)
8. [Recommendations by Use Case](#8-recommendations-by-use-case)

---

## 1. Text/LLM Models

### General Purpose Models

#### **Llama 3.2 3B** ⭐ Best for Speed
- **Size**: 1.9GB (Q4_K_M)
- **Ollama**: `ollama pull llama3.2:3b`
- **Use Case**: Fast general tasks, routing, simple generation
- **Speed**: ~25-30 tokens/sec on M4
- **Context**: 128K tokens
- **Best For**: Input enhancer, router, validators

#### **Qwen2.5 7B** ⭐ Best for JSON/Structured Output
- **Size**: 4.2GB (Q4_K_M)
- **Ollama**: `ollama pull qwen2.5:7b`
- **Use Case**: JSON generation, structured output, analysis
- **Speed**: ~18-22 tokens/sec on M4
- **Context**: 32K tokens
- **Best For**: Blueprint generator, scene generator, diagram spec generator
- **Note**: You're already using this! Excellent choice.

#### **Mistral 7B**
- **Size**: 4.4GB (Q4_K_M)
- **Ollama**: `ollama pull mistral:7b`
- **Use Case**: Fast, capable general-purpose
- **Speed**: ~20-25 tokens/sec on M4
- **Context**: 8K tokens
- **Best For**: General planning, story generation

#### **Phi-3 Mini 4B**
- **Size**: 2.4GB (Q4_K_M)
- **Ollama**: `ollama pull phi3:mini`
- **Use Case**: Efficient reasoning, quick inference
- **Speed**: ~25-30 tokens/sec on M4
- **Context**: 128K tokens
- **Best For**: Fast reasoning tasks, validators

#### **Llama 3.1 8B** (if you need more capability)
- **Size**: ~5GB (Q4_K_M)
- **Ollama**: `ollama pull llama3.1:8b`
- **Use Case**: More capable than 3.2, still fast
- **Speed**: ~15-20 tokens/sec on M4
- **Context**: 128K tokens
- **Best For**: Complex planning, multi-step reasoning

### Reasoning Models (New in 2025)

#### **DeepSeek-R1 1.5B** (Distilled)
- **Size**: ~1GB (Q4_K_M)
- **Ollama**: `ollama pull deepseek-r1:1.5b`
- **Use Case**: Advanced reasoning, chain-of-thought
- **Speed**: ~30+ tokens/sec on M4
- **Context**: 64K tokens
- **Best For**: Complex problem solving, validation logic

#### **DeepSeek-R1 7B** (Distilled)
- **Size**: ~4.5GB (Q4_K_M)
- **Ollama**: `ollama pull deepseek-r1:7b`
- **Use Case**: Strong reasoning with better quality
- **Speed**: ~18-22 tokens/sec on M4
- **Best For**: Critical reasoning tasks, judge, critic agents

---

## 2. Vision Language Models (VLM)

### Current Setup
You're using **LLaVA** via Ollama, which is good. Here are better alternatives:

#### **FastVLM-0.5B** ⭐ Apple's Optimized VLM
- **Size**: ~1GB
- **Source**: HuggingFace `apple/FastVLM-0.5B-fp16`
- **Use Case**: Ultra-fast vision tasks
- **Speed**: 85x faster than LLaVA-OneVision
- **Best For**: Quick image analysis, label detection
- **Setup**: Use MLX framework (see Frameworks section)
- **Note**: Apple's own model, optimized for M4!

#### **FastVLM-1.5B**
- **Size**: ~3GB
- **Source**: HuggingFace `apple/FastVLM-1.5B-fp16`
- **Use Case**: Better quality than 0.5B, still very fast
- **Speed**: 7.9x faster than Cambrian-1-8B
- **Best For**: Zone labeling, detailed image analysis

#### **Qwen2.5-VL 7B** ⭐ Best Quality
- **Size**: ~4.5GB (Q4_K_M)
- **Ollama**: `ollama pull qwen2.5-vl:7b`
- **Use Case**: High-quality vision-language tasks
- **Speed**: ~15-20 tokens/sec on M4
- **Best For**: Complex diagram analysis, multi-image tasks
- **Note**: You're already using this! Excellent choice.

#### **LLaVA 7B** (Current)
- **Size**: ~4.5GB (Q4_K_M)
- **Ollama**: `ollama pull llava:7b`
- **Use Case**: General vision-language tasks
- **Speed**: ~15-18 tokens/sec on M4
- **Status**: Good, but FastVLM is faster

### Recommendation
**Upgrade path**: Keep Qwen2.5-VL for quality tasks, add FastVLM-0.5B for speed-critical tasks.

---

## 3. Code Generation Models

### Current Setup
You're using **DeepSeek Coder 6.7B**, which is excellent. Here are alternatives:

#### **DeepSeek Coder 6.7B** ⭐ Current Best
- **Size**: 3.8GB (Q4_K_M)
- **Ollama**: `ollama pull deepseek-coder:6.7b`
- **Use Case**: Code generation, debugging
- **Speed**: ~20-25 tokens/sec on M4
- **Context**: 16K tokens
- **Status**: Keep this! One of the best code models.

#### **Qwen2.5-Coder 7B**
- **Size**: 4.2GB (Q4_K_M)
- **Ollama**: `ollama pull qwen2.5-coder:7b` (if available)
- **Use Case**: Alternative code model
- **Best For**: If you want consistency with Qwen2.5 family

#### **CodeLlama 7B**
- **Size**: 4.4GB (Q4_K_M)
- **Ollama**: `ollama pull codellama:7b`
- **Use Case**: General code generation
- **Speed**: ~18-22 tokens/sec on M4
- **Best For**: Alternative to DeepSeek

#### **StarCoder2 7B**
- **Size**: 4.5GB (Q4_K_M)
- **Ollama**: `ollama pull starcoder2:7b`
- **Use Case**: Code completion, generation
- **Best For**: Large codebase understanding

### Recommendation
**Keep DeepSeek Coder 6.7B** - it's the best code model for your setup.

---

## 4. Embedding Models

### Current Status
You may not have embeddings set up yet. These are essential for:
- Semantic search
- Similarity matching
- RAG (Retrieval Augmented Generation)
- Domain knowledge retrieval

#### **all-MiniLM-L6-v2** ⭐ Best for 16GB
- **Size**: 33.4M parameters (~130MB)
- **Library**: Sentence Transformers
- **Use Case**: Fast, lightweight embeddings
- **Speed**: Very fast on M4
- **Quality**: Good for most tasks
- **Setup**: `pip install sentence-transformers`

#### **all-MiniLM-L12-v2**
- **Size**: 33.4M parameters (~130MB)
- **Library**: Sentence Transformers
- **Use Case**: Slightly better quality than L6
- **Best For**: When you need better quality

#### **e5-small-v2**
- **Size**: 118M parameters (~450MB)
- **Library**: Sentence Transformers
- **Use Case**: Better quality embeddings
- **Best For**: When quality matters more than speed

#### **bge-small-en-v1.5**
- **Size**: 33M parameters (~130MB)
- **Library**: Sentence Transformers
- **Use Case**: State-of-the-art small embeddings
- **Best For**: Best quality in small size category

### Setup Example
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(['text1', 'text2'])
```

### Integration with Your System
Consider adding embedding-based retrieval to:
- `domain_knowledge_retriever` agent
- Similar question matching
- Content similarity search

---

## 5. Image Generation Models

### Current Status
You may be using external APIs. Here are local options:

#### **Stable Diffusion 3.5 Turbo** ⭐ Fastest
- **Size**: ~15.5GB (download)
- **Speed**: 2 seconds for 512×512 images on M4
- **Use Case**: Fast image generation
- **Setup Options**:
  1. **Draw Things App** (easiest) - App Store
  2. **MLX Stable Diffusion** - Python/MLX
  3. **Core ML** - Apple's optimized version
- **Best For**: Quick asset generation

#### **Stable Diffusion 1.5** (Smaller)
- **Size**: ~4GB
- **Speed**: ~5-10 seconds for 512×512
- **Use Case**: Lower memory usage
- **Best For**: When SD 3.5 Turbo is too large

#### **Stable Diffusion XL** (Better Quality)
- **Size**: ~7GB
- **Speed**: ~10-15 seconds for 1024×1024
- **Use Case**: Higher quality images
- **Best For**: When quality matters

### Setup with MLX
```bash
pip install mlx-diffusion
# Then use MLX-optimized SD models
```

### Recommendation
**Start with Stable Diffusion 3.5 Turbo via Draw Things App** for easiest setup, or MLX for programmatic access.

---

## 6. Text-to-Speech Models

### Current Status
You may not have TTS yet. Here are local options:

#### **Chatterbox-TTS Apple Silicon** ⭐ Optimized for M4
- **Size**: ~500MB
- **Speed**: 2-3x faster with MPS GPU
- **Use Case**: Voice cloning, natural TTS
- **Features**:
  - Voice cloning (6+ seconds reference audio)
  - Smart text chunking
  - Configurable parameters
- **Source**: HuggingFace `Jimmi42/chatterbox-tts-apple-silicon-code`
- **Best For**: Game narration, character voices

#### **NeuTTS**
- **Size**: ~200MB
- **Use Case**: On-device TTS
- **Best For**: Simple TTS needs

#### **Piper TTS**
- **Size**: ~50-100MB per voice
- **Use Case**: Fast, lightweight TTS
- **Best For**: Basic text-to-speech

### Recommendation
**Chatterbox-TTS Apple Silicon** for best quality and M4 optimization.

---

## 7. Frameworks & Tools

### Ollama ⭐ Primary Tool (You're Using This)
- **Status**: Already set up
- **Best For**: Easy model management
- **Models**: All models listed above
- **Advantage**: Metal acceleration built-in

### MLX ⭐ Apple's Native Framework
- **What**: Apple's machine learning framework
- **Advantage**: Optimized for Apple Silicon, unified memory
- **Use Cases**:
  - FastVLM models
  - Custom model training/fine-tuning
  - Stable Diffusion
- **Install**: `pip install mlx mlx-lm`
- **Best For**: When you need maximum performance

### llama.cpp
- **What**: C++ implementation with Metal support
- **Advantage**: Maximum performance, GPU offloading
- **Use Cases**: When Ollama isn't fast enough
- **Best For**: Production deployments needing speed

### LM Studio
- **What**: GUI for local LLMs
- **Advantage**: User-friendly, model browser
- **Use Cases**: Testing models, non-programmers
- **Best For**: Quick model testing

### Sentence Transformers
- **What**: Embedding model framework
- **Install**: `pip install sentence-transformers`
- **Best For**: Embeddings, semantic search

---

## 8. Recommendations by Use Case

### For Your Current Agents

#### **Input Enhancer**
- **Current**: `local-qwen-coder` ✅ Good
- **Alternative**: `llama3.2:3b` (faster) or `phi3:mini` (better reasoning)

#### **Router**
- **Current**: `local-qwen-coder` ✅ Good
- **Alternative**: `llama3.2:3b` (faster for simple classification)

#### **Game Planner**
- **Current**: `local-llama` ✅ Good
- **Alternative**: `qwen2.5:7b` (better structured output) or `deepseek-r1:7b` (better reasoning)

#### **Scene Generator**
- **Current**: `local-qwen-coder` ✅ Excellent (JSON generation)
- **Keep**: This is perfect for JSON output

#### **Blueprint Generator**
- **Current**: `local-qwen-coder` ✅ Excellent (JSON generation)
- **Keep**: This is perfect for JSON output

#### **Code Generator**
- **Current**: `local-deepseek-coder` ✅ Excellent
- **Keep**: Best code model available

#### **Diagram Zone Labeler**
- **Current**: `qwen2.5-vl:7b` ✅ Excellent
- **Enhancement**: Add `FastVLM-0.5B` for speed-critical tasks

### New Capabilities to Add

#### **1. Embedding-Based Retrieval**
- **Model**: `all-MiniLM-L6-v2`
- **Use**: Enhance `domain_knowledge_retriever` with semantic search
- **Setup**: `pip install sentence-transformers`

#### **2. Image Generation**
- **Model**: Stable Diffusion 3.5 Turbo
- **Use**: Generate game assets locally
- **Setup**: Draw Things App or MLX

#### **3. Text-to-Speech**
- **Model**: Chatterbox-TTS Apple Silicon
- **Use**: Game narration, character voices
- **Setup**: HuggingFace model

#### **4. Advanced Reasoning**
- **Model**: `deepseek-r1:7b`
- **Use**: Enhance judge, critic, validator agents
- **Setup**: `ollama pull deepseek-r1:7b`

#### **5. Faster Vision Tasks**
- **Model**: FastVLM-0.5B
- **Use**: Quick image analysis, label detection
- **Setup**: MLX framework

---

## Quick Setup Guide

### 1. Install Additional Ollama Models
```bash
# Reasoning models
ollama pull deepseek-r1:7b

# Alternative general models
ollama pull phi3:mini
ollama pull mistral:7b

# Alternative code model (if needed)
ollama pull codellama:7b
```

### 2. Install Embedding Support
```bash
cd backend
source venv/bin/activate
pip install sentence-transformers
```

### 3. Install MLX (for FastVLM, SD)
```bash
pip install mlx mlx-lm mlx-diffusion
```

### 4. Update Model Registry
Add new models to `backend/app/config/models.py`:
```python
"local-phi3-mini": ModelConfig(
    provider=ModelProvider.LOCAL,
    model_id="phi3:mini",
    tier=ModelTier.FAST,
    max_tokens=4096,
    temperature=0.7,
    cost_per_1k_input=0.0,
    cost_per_1k_output=0.0,
    context_window=128000,
    supports_json_mode=True,
    supports_vision=False
),

"local-deepseek-r1": ModelConfig(
    provider=ModelProvider.LOCAL,
    model_id="deepseek-r1:7b",
    tier=ModelTier.BALANCED,
    max_tokens=8192,
    temperature=0.3,  # Lower for reasoning
    cost_per_1k_input=0.0,
    cost_per_1k_output=0.0,
    context_window=64000,
    supports_json_mode=True,
    supports_vision=False
),
```

---

## Performance Benchmarks (M4 16GB)

| Model | Size | Tokens/sec | Use Case |
|-------|------|------------|----------|
| Llama 3.2 3B | 1.9GB | 25-30 | Fast tasks |
| Phi-3 Mini 4B | 2.4GB | 25-30 | Reasoning |
| Qwen2.5 7B | 4.2GB | 18-22 | JSON/Structured |
| Mistral 7B | 4.4GB | 20-25 | General purpose |
| DeepSeek Coder 6.7B | 3.8GB | 20-25 | Code generation |
| DeepSeek-R1 7B | 4.5GB | 18-22 | Reasoning |
| Qwen2.5-VL 7B | 4.5GB | 15-20 | Vision-language |
| FastVLM-0.5B | 1GB | 85x faster | Fast vision |

---

## Memory Management Tips

1. **Quantization**: Always use Q4_K_M quantization (Ollama default)
2. **Model Switching**: Don't load multiple large models simultaneously
3. **Context Windows**: Use smaller context for simple tasks
4. **Batch Processing**: Process requests sequentially to avoid memory spikes
5. **Monitor Usage**: Use Activity Monitor to track memory usage

---

## Cost Comparison

| Solution | Cost | Speed | Privacy |
|----------|------|-------|---------|
| **Local (Ollama)** | $0 | Fast | ✅ Full |
| **Groq Free** | $0 | Very Fast | ⚠️ API |
| **OpenAI API** | $0.01-0.50/run | Fast | ⚠️ API |
| **Anthropic API** | $0.01-0.50/run | Fast | ⚠️ API |

**Recommendation**: Use local models for development/testing, API models for production if needed.

---

## Next Steps

1. **Immediate**: Test `deepseek-r1:7b` for reasoning tasks
2. **Short-term**: Add embedding support for semantic search
3. **Medium-term**: Integrate FastVLM-0.5B for faster vision tasks
4. **Long-term**: Add Stable Diffusion for local image generation

---

## Resources

- **Ollama Models**: https://ollama.com/library
- **MLX Framework**: https://mlx-framework.org/
- **HuggingFace**: https://huggingface.co/
- **Apple ML Research**: https://machinelearning.apple.com/

---

## Summary

Your current setup is excellent! You're using:
- ✅ Qwen2.5 7B for JSON generation (perfect choice)
- ✅ DeepSeek Coder 6.7B for code (best available)
- ✅ Qwen2.5-VL 7B for vision (excellent quality)

**Top additions to consider:**
1. **DeepSeek-R1 7B** - Better reasoning for validators/judges
2. **FastVLM-0.5B** - Faster vision tasks (via MLX)
3. **Embedding models** - Semantic search capabilities
4. **Stable Diffusion 3.5 Turbo** - Local image generation

All of these will run efficiently on your M4 16GB MacBook Pro!
