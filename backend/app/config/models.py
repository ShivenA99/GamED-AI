"""
Model Configuration Registry

Provides a centralized registry of available LLM models with their
configurations, costs, and capabilities.

Supports:
- OpenAI (GPT-4o, GPT-4-turbo, GPT-4o-mini)
- Anthropic (Claude Opus, Sonnet, Haiku)
- Local models (future: Ollama, vLLM)

Usage:
    from app.config.models import MODEL_REGISTRY, get_model_config

    config = get_model_config("claude-sonnet")
    print(f"Using {config.model_id} at ${config.cost_per_1k_input}/1k tokens")
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any


class ModelProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"  # Gemini models
    GROQ = "groq"      # Free tier available!
    TOGETHER = "together"  # Free credits on signup
    LOCAL = "local"    # Ollama, vLLM


class ModelTier(Enum):
    """Model capability/cost tiers"""
    FAST = "fast"           # Quick responses, lower cost (~$0.0001-$0.001/1k)
    BALANCED = "balanced"   # Good quality/cost ratio (~$0.003-$0.01/1k)
    PREMIUM = "premium"     # Best quality, higher cost (~$0.01-$0.075/1k)


@dataclass
class ModelConfig:
    """
    Configuration for a specific LLM model.

    Attributes:
        provider: The LLM provider (OpenAI, Anthropic, Local)
        model_id: The model identifier used in API calls
        tier: Performance/cost tier
        max_tokens: Maximum output tokens
        temperature: Default temperature for sampling
        cost_per_1k_input: Cost per 1000 input tokens (USD)
        cost_per_1k_output: Cost per 1000 output tokens (USD)
        context_window: Maximum context window size
        supports_json_mode: Whether model supports structured JSON output
        supports_vision: Whether model supports image inputs
    """
    provider: ModelProvider
    model_id: str
    tier: ModelTier
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    context_window: int = 128000
    supports_json_mode: bool = True
    supports_vision: bool = False
    is_open_source: bool = False  # Add this field

    def estimated_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for a request"""
        return (
            (input_tokens / 1000) * self.cost_per_1k_input +
            (output_tokens / 1000) * self.cost_per_1k_output
        )


# =============================================================================
# MODEL REGISTRY
# =============================================================================

MODEL_REGISTRY: Dict[str, ModelConfig] = {
    # -------------------------------------------------------------------------
    # OpenAI Models
    # -------------------------------------------------------------------------
    "gpt-4o": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o",
        tier=ModelTier.PREMIUM,
        max_tokens=4096,
        temperature=0.7,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        context_window=128000,
        supports_json_mode=True,
        supports_vision=True
    ),

    "gpt-4o-mini": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o-mini",
        tier=ModelTier.FAST,
        max_tokens=4096,
        temperature=0.7,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        context_window=128000,
        supports_json_mode=True,
        supports_vision=True
    ),

    "gpt-4-turbo": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-4-turbo-preview",
        tier=ModelTier.BALANCED,
        max_tokens=4096,
        temperature=0.7,
        cost_per_1k_input=0.01,
        cost_per_1k_output=0.03,
        context_window=128000,
        supports_json_mode=True,
        supports_vision=True
    ),

    "gpt-3.5-turbo": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-3.5-turbo",
        tier=ModelTier.FAST,
        max_tokens=4096,
        temperature=0.7,
        cost_per_1k_input=0.0005,
        cost_per_1k_output=0.0015,
        context_window=16385,
        supports_json_mode=True,
        supports_vision=False
    ),

    # -------------------------------------------------------------------------
    # Anthropic Models
    # -------------------------------------------------------------------------
    "claude-opus": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-opus-20240229",
        tier=ModelTier.PREMIUM,
        max_tokens=4096,
        temperature=0.7,
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        context_window=200000,
        supports_json_mode=True,
        supports_vision=True
    ),

    "claude-sonnet": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-5-sonnet-20241022",
        tier=ModelTier.BALANCED,
        max_tokens=8192,
        temperature=0.7,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        context_window=200000,
        supports_json_mode=True,
        supports_vision=True
    ),

    "claude-haiku": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-5-haiku-20241022",
        tier=ModelTier.FAST,
        max_tokens=8192,
        temperature=0.7,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        context_window=200000,
        supports_json_mode=True,
        supports_vision=True
    ),

    # Full model IDs (for direct routing when model_id is passed)
    "claude-3-5-sonnet-20241022": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-5-sonnet-20241022",
        tier=ModelTier.BALANCED,
        max_tokens=8192,
        temperature=0.7,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        context_window=200000,
        supports_json_mode=True,
        supports_vision=True
    ),

    "claude-3-5-haiku-20241022": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-5-haiku-20241022",
        tier=ModelTier.FAST,
        max_tokens=8192,
        temperature=0.7,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        context_window=200000,
        supports_json_mode=True,
        supports_vision=True
    ),

    # Legacy Claude 3 models (for compatibility)
    "claude-3-sonnet": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-sonnet-20240229",
        tier=ModelTier.BALANCED,
        max_tokens=4096,
        temperature=0.7,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        context_window=200000,
        supports_json_mode=True,
        supports_vision=True
    ),

    # -------------------------------------------------------------------------
    # Groq Models (FREE TIER - Fast inference)
    # Sign up at: https://console.groq.com
    # Updated Jan 2025: Using current available models
    # -------------------------------------------------------------------------
    "llama-3.3-70b-versatile": ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.3-70b-versatile",
        tier=ModelTier.BALANCED,
        max_tokens=32768,
        temperature=0.7,
        cost_per_1k_input=0.59,  # $0.59 input per 1M tokens = $0.00059 per 1k
        cost_per_1k_output=0.79,  # $0.79 output per 1M tokens = $0.00079 per 1k
        context_window=131072,
        supports_json_mode=True,
        supports_vision=False,
        is_open_source=True
    ),

    "llama-3.1-8b-instant": ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.1-8b-instant",
        tier=ModelTier.FAST,
        max_tokens=131072,
        temperature=0.7,
        cost_per_1k_input=0.05,  # $0.05 input per 1M tokens = $0.00005 per 1k
        cost_per_1k_output=0.08,  # $0.08 output per 1M tokens = $0.00008 per 1k
        context_window=131072,
        supports_json_mode=True,
        supports_vision=False,
        is_open_source=True
    ),

    # Legacy keys (for backward compatibility)
    "groq-llama3-70b": ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.3-70b-versatile",
        tier=ModelTier.BALANCED,
        max_tokens=32768,
        temperature=0.7,
        cost_per_1k_input=0.0,  # Free tier!
        cost_per_1k_output=0.0,
        context_window=128000,
        supports_json_mode=True,
        supports_vision=False,
        is_open_source=True
    ),

    "groq-llama3-8b": ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.1-8b-instant",
        tier=ModelTier.FAST,
        max_tokens=131072,
        temperature=0.7,
        cost_per_1k_input=0.0,  # Free tier!
        cost_per_1k_output=0.0,
        context_window=131072,
        supports_json_mode=True,
        supports_vision=False,
        is_open_source=True
    ),

    "groq-mixtral": ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.3-70b-versatile",  # Fallback since mixtral not available
        tier=ModelTier.BALANCED,
        max_tokens=32768,
        temperature=0.7,
        cost_per_1k_input=0.0,  # Free tier!
        cost_per_1k_output=0.0,
        context_window=131072,
        supports_json_mode=True,
        supports_vision=False,
        is_open_source=True
    ),

    # -------------------------------------------------------------------------
    # Google Gemini Models (January 2026)
    # Get API key at: https://aistudio.google.com/app/apikey
    # -------------------------------------------------------------------------

    # Gemini 3 Series (Latest - Preview)
    "gemini-3-flash": ModelConfig(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-3-flash-preview",
        tier=ModelTier.BALANCED,
        max_tokens=8192,
        temperature=0.7,
        cost_per_1k_input=0.0005,   # $0.50 per 1M input
        cost_per_1k_output=0.003,   # $3.00 per 1M output
        context_window=1000000,     # 1M context window
        supports_json_mode=True,
        supports_vision=True,
        is_open_source=False
    ),

    "gemini-3-pro": ModelConfig(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-3-pro-preview",
        tier=ModelTier.PREMIUM,
        max_tokens=8192,
        temperature=0.7,
        cost_per_1k_input=0.002,    # $2.00 per 1M input
        cost_per_1k_output=0.012,   # $12.00 per 1M output
        context_window=1000000,
        supports_json_mode=True,
        supports_vision=True,
        is_open_source=False
    ),

    # Gemini 2.5 Series (Stable)
    "gemini-2.5-flash": ModelConfig(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-2.5-flash",
        tier=ModelTier.BALANCED,
        max_tokens=8192,
        temperature=0.7,
        cost_per_1k_input=0.0003,   # $0.30 per 1M input
        cost_per_1k_output=0.0025,  # $2.50 per 1M output
        context_window=1000000,
        supports_json_mode=True,
        supports_vision=True,
        is_open_source=False
    ),

    "gemini-2.5-flash-lite": ModelConfig(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-2.5-flash-lite",
        tier=ModelTier.FAST,
        max_tokens=8192,
        temperature=0.7,
        cost_per_1k_input=0.0001,   # $0.10 per 1M input
        cost_per_1k_output=0.0004,  # $0.40 per 1M output
        context_window=1000000,
        supports_json_mode=True,
        supports_vision=True,
        is_open_source=False
    ),

    "gemini-2.5-pro": ModelConfig(
        provider=ModelProvider.GOOGLE,
        model_id="gemini-2.5-pro",
        tier=ModelTier.PREMIUM,
        max_tokens=8192,
        temperature=0.7,
        cost_per_1k_input=0.00125,  # $1.25 per 1M input
        cost_per_1k_output=0.010,   # $10.00 per 1M output
        context_window=1000000,
        supports_json_mode=True,
        supports_vision=True,
        is_open_source=False
    ),

    # -------------------------------------------------------------------------
    # Local Models (Ollama - Completely Free)
    # Install: brew install ollama && ollama run llama3.1
    # -------------------------------------------------------------------------
    "local-llama": ModelConfig(
        provider=ModelProvider.LOCAL,
        model_id="llama3.2:latest",  # Ollama model name format
        tier=ModelTier.BALANCED,
        max_tokens=4096,
        temperature=0.7,
        cost_per_1k_input=0.0,  # Free (local compute)
        cost_per_1k_output=0.0,
        context_window=128000,
        supports_json_mode=True,
        supports_vision=False,
        is_open_source=True
    ),

    "local-mixtral": ModelConfig(
        provider=ModelProvider.LOCAL,
        model_id="mixtral",
        tier=ModelTier.FAST,
        max_tokens=4096,
        temperature=0.7,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        context_window=32768,
        supports_json_mode=True,
        supports_vision=False,
        is_open_source=True
    ),

    "local-deepseek-coder": ModelConfig(
        provider=ModelProvider.LOCAL,
        model_id="deepseek-coder:6.7b",  # Best coding model for Ollama
        tier=ModelTier.BALANCED,
        max_tokens=8192,
        temperature=0.2,  # Lower temp for code generation
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        context_window=16384,
        supports_json_mode=True,
        supports_vision=False,
        is_open_source=True
    ),

    "local-qwen-coder": ModelConfig(
        provider=ModelProvider.LOCAL,
        model_id="qwen2.5:7b",  # Using qwen2.5:7b (coder version not available yet)
        tier=ModelTier.BALANCED,
        max_tokens=8192,
        temperature=0.3,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        context_window=32768,
        supports_json_mode=True,
        supports_vision=False,
        is_open_source=True
    ),
}


def get_model_config(model_key: str) -> ModelConfig:
    """
    Get configuration for a model by its key.

    Args:
        model_key: Key in MODEL_REGISTRY (e.g., "claude-sonnet", "gpt-4o")

    Returns:
        ModelConfig for the specified model

    Raises:
        KeyError: If model_key not found in registry
    """
    if model_key not in MODEL_REGISTRY:
        available = ", ".join(MODEL_REGISTRY.keys())
        raise KeyError(
            f"Unknown model: '{model_key}'. Available: {available}"
        )
    return MODEL_REGISTRY[model_key]


def get_models_by_tier(tier: ModelTier) -> Dict[str, ModelConfig]:
    """Get all models of a specific tier"""
    return {
        key: config
        for key, config in MODEL_REGISTRY.items()
        if config.tier == tier
    }


def get_models_by_provider(provider: ModelProvider) -> Dict[str, ModelConfig]:
    """Get all models from a specific provider"""
    return {
        key: config
        for key, config in MODEL_REGISTRY.items()
        if config.provider == provider
    }


def get_cheapest_model(
    min_tier: ModelTier = ModelTier.FAST,
    provider: Optional[ModelProvider] = None
) -> str:
    """
    Get the cheapest model meeting minimum requirements.

    Args:
        min_tier: Minimum capability tier
        provider: Optional provider filter

    Returns:
        Model key for the cheapest qualifying model
    """
    tier_order = [ModelTier.FAST, ModelTier.BALANCED, ModelTier.PREMIUM]
    min_tier_idx = tier_order.index(min_tier)

    candidates = []
    for key, config in MODEL_REGISTRY.items():
        tier_idx = tier_order.index(config.tier)
        if tier_idx >= min_tier_idx:
            if provider is None or config.provider == provider:
                # Use output cost as primary metric (usually more expensive)
                candidates.append((config.cost_per_1k_output, key))

    if not candidates:
        return "claude-sonnet"  # Default fallback

    candidates.sort()
    return candidates[0][1]


def estimate_pipeline_cost(
    agent_models: Dict[str, str],
    avg_input_tokens: int = 2000,
    avg_output_tokens: int = 1000
) -> float:
    """
    Estimate cost for running the full pipeline once.

    Args:
        agent_models: Mapping of agent name to model key
        avg_input_tokens: Average input tokens per agent
        avg_output_tokens: Average output tokens per agent

    Returns:
        Estimated total cost in USD
    """
    total = 0.0
    for agent_name, model_key in agent_models.items():
        if model_key in MODEL_REGISTRY:
            config = MODEL_REGISTRY[model_key]
            total += config.estimated_cost(avg_input_tokens, avg_output_tokens)
    return total
