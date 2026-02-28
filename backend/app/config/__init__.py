"""
GamED.AI v2 Configuration Module

This module provides plug-and-play model configuration for agents.
"""

from app.config.models import (
    ModelProvider,
    ModelTier,
    ModelConfig,
    MODEL_REGISTRY,
    get_model_config
)

from app.config.agent_models import (
    AgentModelConfig,
    PRESET_CONFIGS,
    get_agent_config,
    load_config_from_env,
    get_runtime_config,
    set_runtime_config
)

__all__ = [
    # Model Registry
    "ModelProvider",
    "ModelTier",
    "ModelConfig",
    "MODEL_REGISTRY",
    "get_model_config",

    # Agent Configuration
    "AgentModelConfig",
    "PRESET_CONFIGS",
    "get_agent_config",
    "load_config_from_env",
    "get_runtime_config",
    "set_runtime_config"
]
