"""
Per-Agent Model Configuration

Provides plug-and-play model assignment for each agent in the pipeline.
Supports presets for different optimization goals (cost, quality, balanced).

Environment Variables:
    AGENT_CONFIG_PRESET: Use a preset ("cost_optimized", "quality_optimized", "balanced")
    AGENT_MODEL_<AGENT_NAME>: Override model for specific agent
    AGENT_TEMPERATURE_<AGENT_NAME>: Override temperature for specific agent

Example:
    AGENT_CONFIG_PRESET=quality_optimized
    AGENT_MODEL_BLUEPRINT_GENERATOR=gpt-4o
    AGENT_TEMPERATURE_STORY_GENERATOR=0.9

Usage:
    from app.config.agent_models import get_agent_config, load_config_from_env

    config = load_config_from_env()  # Loads from environment
    model = config.get_model("blueprint_generator")  # "gpt-4o"
    temp = config.get_temperature("blueprint_generator")  # 0.4
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Literal
from contextvars import ContextVar

from app.config.models import MODEL_REGISTRY

logger = logging.getLogger("gamed_ai.config.agent_models")


@dataclass
class AgentModelConfig:
    """
    Configuration for which model each agent uses.

    Attributes:
        default_model: Fallback model for agents without specific assignment
        agent_models: Mapping of agent name to model key
        agent_temperatures: Mapping of agent name to temperature
        agent_max_tokens: Mapping of agent name to max tokens
    """

    # Default model for all agents
    default_model: str = "local-llama"

    # Default temperature for all agents
    default_temperature: float = 0.7

    # Per-agent model overrides
    # Default configuration uses local models (Ollama) for development
    agent_models: Dict[str, str] = field(default_factory=lambda: {
        # Input processing (fast, local)
        "input_enhancer": "local-qwen-coder",
        "domain_knowledge_retriever": "local-qwen-coder",
        "router": "local-qwen-coder",

        # Game planning (local)
        "game_planner": "local-qwen-coder",
        "game_designer": "local-qwen-coder",
        "design_interpreter": "local-qwen-coder",
        "scene_generator": "local-llama",
        "story_generator": "local-llama",  # Legacy

        # 3-stage scene generation (hierarchical pipeline)
        "scene_stage1_structure": "local-qwen-coder",
        "scene_stage2_assets": "local-qwen-coder",
        "scene_stage3_interactions": "local-qwen-coder",

        # Asset generation pipeline (new agents)
        "asset_planner": "local-qwen-coder",
        "asset_generator_orchestrator": "local-llama",
        "asset_validator": "local-qwen-coder",

        # Blueprint generation
        "blueprint_generator": "local-qwen-coder",
        "blueprint_validator": "local-qwen-coder",

        # Diagram generation
        "diagram_spec_generator": "local-qwen-coder",
        "diagram_svg_generator": "local-llama",

        # Code generation
        "code_generator": "local-deepseek-coder",
        "code_verifier": "local-llama",

        # Topology-specific agents
        "critic": "local-llama",
        "judge": "local-llama",
        "supervisor": "local-llama",
        "proposer": "local-llama",
        "memory_retriever": "local-llama",

        # Image pipeline agents (use local or VLM)
        "diagram_image_retriever": "local-qwen-coder",
        "diagram_image_segmenter": "local-qwen-coder",
        "diagram_zone_labeler": "local-qwen-coder",

        # V4 pipeline agents
        "input_analyzer": "gemini-2.5-flash",
        "v4_input_analyzer": "gemini-2.5-flash",
        "dk_retriever": "gemini-2.5-flash",
        "v4_dk_retriever": "gemini-2.5-flash",
        "game_designer": "gemini-2.5-pro",
        "v4_game_designer": "gemini-2.5-pro",
        "content_builder_pro": "gemini-2.5-pro",
        "content_builder_flash": "gemini-2.5-flash",
        "content_generator_pro": "gemini-2.5-pro",
        "content_generator_flash": "gemini-2.5-flash",
        "v4_content_builder": "gemini-2.5-pro",
        "interaction_designer": "gemini-2.5-flash",
        "v4_asset_worker": "gemini-2.5-flash",
    })

    # Per-agent temperature overrides
    # Lower = more deterministic (better for structured JSON output)
    # Higher = more creative (better for narrative/story content)
    # OPTIMIZED: Structured output agents use very low temperatures for reliability
    agent_temperatures: Dict[str, float] = field(default_factory=lambda: {
        "input_enhancer": 0.3,
        "router": 0.1,               # LOWERED: Consistent routing decisions
        "domain_knowledge_retriever": 0.2,
        "game_planner": 0.5,         # Moderate creativity for mechanics
        "game_designer": 0.7,       # Higher creativity for game design
        "design_interpreter": 0.3,  # Low for reliable structured mapping
        "scene_generator": 0.5,      # LOWERED: Better JSON structure
        "story_generator": 0.7,
        # 3-stage scene generation (hierarchical pipeline)
        "scene_stage1_structure": 0.4,  # Structure needs some creativity
        "scene_stage2_assets": 0.3,     # Assets need reliable JSON
        "scene_stage3_interactions": 0.3,  # Interactions need reliable JSON
        # Asset generation pipeline
        "asset_planner": 0.2,           # Reliable asset planning
        "asset_generator_orchestrator": 0.3,  # Some flexibility in orchestration
        "asset_validator": 0.1,         # Deterministic validation
        # Blueprint generation
        "blueprint_generator": 0.2,  # LOWERED: Reliable JSON generation
        "blueprint_validator": 0.1,
        # Diagram generation
        "diagram_spec_generator": 0.1,  # LOWERED: Precise specifications
        "diagram_svg_generator": 0.1,
        # Code generation
        "code_generator": 0.3,       # LOWERED: More deterministic code
        "code_verifier": 0.1,
        # Topology agents
        "critic": 0.2,
        "judge": 0.1,
        "supervisor": 0.3,
        "proposer": 0.7,
        "memory_retriever": 0.2,
        # Image pipeline agents
        "diagram_image_retriever": 0.1,
        "diagram_image_segmenter": 0.1,
        "diagram_zone_labeler": 0.2,

        # V4 pipeline agents
        "input_analyzer": 0.3,
        "v4_input_analyzer": 0.3,
        "dk_retriever": 0.2,
        "v4_dk_retriever": 0.2,
        "game_designer": 0.5,
        "v4_game_designer": 0.5,
        "content_builder_pro": 0.4,
        "content_builder_flash": 0.3,
        "content_generator_pro": 0.4,
        "content_generator_flash": 0.3,
        "v4_content_builder": 0.4,
        "interaction_designer": 0.3,
        "v4_asset_worker": 0.1,
    })

    # Per-agent max tokens (optional override)
    # OPTIMIZED: Increased for agents that generate large JSON structures
    agent_max_tokens: Dict[str, int] = field(default_factory=lambda: {
        "input_enhancer": 2048,
        "router": 1024,
        "domain_knowledge_retriever": 2048,
        "game_planner": 4096,
        "game_designer": 8192,       # Multi-scene designs need space
        "design_interpreter": 6144,  # Structured mapping output
        "scene_generator": 10240,     # INCREASED: Complex hierarchical scenes
        "story_generator": 4096,      # Legacy
        # 3-stage scene generation
        "scene_stage1_structure": 6144,  # INCREASED: Hierarchical zone definitions
        "scene_stage2_assets": 6144,
        "scene_stage3_interactions": 8192,  # INCREASED: Per-zone configs for 10+ zones
        # Interaction design
        "interaction_designer": 6144,  # Per-scene designs
        # Asset generation pipeline
        "asset_planner": 4096,
        "asset_generator_orchestrator": 8192,
        "asset_validator": 2048,
        # Blueprint generation
        "blueprint_generator": 16384, # INCREASED: Large blueprint JSON with zones/labels
        "blueprint_validator": 4096,  # INCREASED: Detailed error messages
        # Diagram generation
        "diagram_spec_generator": 8192,  # INCREASED: Detailed diagram specs
        "diagram_svg_generator": 8192,   # INCREASED: SVG can be verbose
        # Code generation
        "code_generator": 8192,
        "code_verifier": 1024,
        # Topology agents
        "critic": 2048,
        "judge": 2048,

        # V4 pipeline agents
        "input_analyzer": 2048,
        "v4_input_analyzer": 2048,
        "dk_retriever": 4096,
        "v4_dk_retriever": 4096,
        "v4_game_designer": 8192,
        "content_builder_pro": 8192,
        "content_builder_flash": 4096,
        "content_generator_pro": 8192,
        "content_generator_flash": 4096,
        "v4_content_builder": 8192,
        "v4_asset_worker": 2048,

        # V4 Algorithm pipeline agents
        "v4a_dk_retriever": 4096,
        "v4a_game_concept_designer": 8192,
        "v4a_scene_content_gen_state_tracer": 16384,  # Execution traces with steps are large
        "v4a_scene_content_gen_bug_hunter": 16384,     # Multi-round bugs + test cases
        "v4a_scene_content_gen_algorithm_builder": 12288,  # Parsons blocks + distractors
        "v4a_scene_content_gen_complexity_analyzer": 12288,  # Growth data + challenges
        "v4a_scene_content_gen_constraint_puzzle": 12288,    # Board config + constraints
    })

    def get_model(self, agent_name: str) -> str:
        """Get model key for an agent"""
        model = self.agent_models.get(agent_name, self.default_model)
        if model not in MODEL_REGISTRY:
            logger.warning(
                f"Model '{model}' for agent '{agent_name}' not in registry, "
                f"falling back to '{self.default_model}'"
            )
            return self.default_model
        return model

    def get_temperature(self, agent_name: str) -> float:
        """Get temperature for an agent"""
        return self.agent_temperatures.get(agent_name, self.default_temperature)

    def get_max_tokens(self, agent_name: str) -> int:
        """Get max tokens for an agent"""
        return self.agent_max_tokens.get(agent_name, 4096)

    def set_model(self, agent_name: str, model_key: str) -> None:
        """Set model for an agent"""
        if model_key not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model: {model_key}")
        self.agent_models[agent_name] = model_key

    def set_temperature(self, agent_name: str, temperature: float) -> None:
        """Set temperature for an agent"""
        if not 0.0 <= temperature <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temperature}")
        self.agent_temperatures[agent_name] = temperature

    def get_all_agents(self) -> List[str]:
        """Get list of all configured agents"""
        return list(set(self.agent_models.keys()) | set(self.agent_temperatures.keys()))

    def get_temperature_with_retry_escalation(
        self,
        agent_name: str,
        retry_count: int = 0,
        escalation_factor: float = 0.1
    ) -> float:
        """
        Get temperature with retry escalation for failed generations.

        On retries, slightly increase temperature to encourage different outputs.
        This helps break out of repetitive failure patterns.

        Args:
            agent_name: Name of the agent
            retry_count: Number of previous retry attempts
            escalation_factor: How much to increase temperature per retry (default 0.1)

        Returns:
            Adjusted temperature (capped at 1.0)

        Example:
            Base temp 0.2, retry_count=2 → 0.2 + (2 * 0.1) = 0.4
        """
        base_temp = self.get_temperature(agent_name)

        # Don't escalate on first attempt or very low base temps
        if retry_count == 0:
            return base_temp

        # Calculate escalation (max 3 escalation steps)
        effective_retries = min(retry_count, 3)
        escalated_temp = base_temp + (effective_retries * escalation_factor)

        # Cap at 1.0 to avoid overly random outputs
        return min(escalated_temp, 1.0)

    def to_dict(self) -> Dict:
        """Export configuration as dict"""
        return {
            "default_model": self.default_model,
            "default_temperature": self.default_temperature,
            "agent_models": dict(self.agent_models),
            "agent_temperatures": dict(self.agent_temperatures),
            "agent_max_tokens": dict(self.agent_max_tokens),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentModelConfig":
        """Create configuration from dict"""
        return cls(
            default_model=data.get("default_model", "claude-sonnet"),
            default_temperature=data.get("default_temperature", 0.7),
            agent_models=data.get("agent_models", {}),
            agent_temperatures=data.get("agent_temperatures", {}),
            agent_max_tokens=data.get("agent_max_tokens", {}),
        )


# =============================================================================
# PRESET CONFIGURATIONS
# =============================================================================

PRESET_CONFIGS: Dict[str, AgentModelConfig] = {
    # -------------------------------------------------------------------------
    # Cost Optimized: Use cheapest models, good for testing/development
    # Estimated cost: ~$0.01-0.02 per pipeline run
    # -------------------------------------------------------------------------
    "cost_optimized": AgentModelConfig(
        default_model="claude-haiku",
        default_temperature=0.5,
        agent_models={
            "input_enhancer": "claude-haiku",
            "router": "claude-haiku",
            "game_planner": "gpt-4o-mini",
            "scene_generator": "claude-haiku",
            "story_generator": "claude-haiku",  # Legacy
            "blueprint_generator": "gpt-4o-mini",
            "diagram_spec_generator": "gpt-4o-mini",
            "diagram_svg_generator": "claude-haiku",
            "blueprint_validator": "claude-haiku",
            "code_generator": "gpt-4o-mini",
            "code_verifier": "claude-haiku",
            "critic": "claude-haiku",
            "judge": "claude-haiku",
            "supervisor": "claude-haiku",
            "proposer": "gpt-4o-mini",
        },
        agent_temperatures={
            "input_enhancer": 0.3,
            "router": 0.3,
            "game_planner": 0.7,
            "scene_generator": 0.7,
            "story_generator": 0.7,  # Legacy
            "blueprint_generator": 0.4,
            "diagram_spec_generator": 0.2,
            "diagram_svg_generator": 0.1,
            "blueprint_validator": 0.1,
            "code_generator": 0.4,
            "code_verifier": 0.1,
            "critic": 0.2,
            "judge": 0.1,
        }
    ),

    # -------------------------------------------------------------------------
    # Quality Optimized: Use best models, higher cost for maximum quality
    # Estimated cost: ~$0.20-0.50 per pipeline run
    # -------------------------------------------------------------------------
    "quality_optimized": AgentModelConfig(
        default_model="claude-sonnet",
        default_temperature=0.7,
        agent_models={
            "input_enhancer": "claude-sonnet",
            "router": "claude-sonnet",
            "game_planner": "claude-opus",
            "scene_generator": "claude-opus",
            "story_generator": "claude-opus",  # Legacy
            "blueprint_generator": "gpt-4o",
            "diagram_spec_generator": "gpt-4o",
            "diagram_svg_generator": "claude-haiku",
            "blueprint_validator": "claude-sonnet",
            "code_generator": "gpt-4o",
            "code_verifier": "claude-sonnet",
            "critic": "claude-opus",
            "judge": "claude-opus",
            "supervisor": "claude-opus",
            "proposer": "gpt-4o",
        },
        agent_temperatures={
            "input_enhancer": 0.3,
            "router": 0.2,
            "game_planner": 0.8,
            "scene_generator": 0.8,
            "story_generator": 0.9,  # Legacy
            "blueprint_generator": 0.5,
            "diagram_spec_generator": 0.2,
            "diagram_svg_generator": 0.1,
            "blueprint_validator": 0.1,
            "code_generator": 0.4,
            "code_verifier": 0.1,
            "critic": 0.2,
            "judge": 0.1,
        }
    ),

    # -------------------------------------------------------------------------
    # Balanced: Good quality/cost ratio, recommended for production
    # Estimated cost: ~$0.05-0.10 per pipeline run
    # -------------------------------------------------------------------------
    "balanced": AgentModelConfig(
        default_model="claude-sonnet",
        default_temperature=0.7,
        agent_models={
            "input_enhancer": "claude-sonnet",
            "router": "claude-haiku",      # Fast routing
            "game_planner": "gpt-4-turbo",
            "scene_generator": "claude-sonnet",
            "story_generator": "claude-sonnet",  # Legacy
            "blueprint_generator": "gpt-4o",
            "diagram_spec_generator": "gpt-4o",
            "diagram_svg_generator": "claude-haiku",
            "blueprint_validator": "claude-haiku",  # Fast validation
            "code_generator": "gpt-4o",
            "code_verifier": "claude-haiku",
            "critic": "claude-sonnet",
            "judge": "claude-sonnet",
            "supervisor": "claude-sonnet",
            "proposer": "gpt-4-turbo",
        },
        agent_temperatures={
            "input_enhancer": 0.3,
            "router": 0.3,
            "game_planner": 0.7,
            "story_generator": 0.8,
            "blueprint_generator": 0.4,
            "diagram_spec_generator": 0.2,
            "diagram_svg_generator": 0.1,
            "blueprint_validator": 0.1,
            "code_generator": 0.4,
            "code_verifier": 0.1,
            "critic": 0.2,
            "judge": 0.1,
        }
    ),

    # -------------------------------------------------------------------------
    # Local Only: Optimized for Ollama local models
    # Best models: qwen2.5:7b (JSON), deepseek-coder:6.7b (code), llama3.2 (general)
    # Estimated cost: $0 (local compute)
    # RAM: 8-16GB recommended
    # -------------------------------------------------------------------------
    "local_only": AgentModelConfig(
        default_model="local-qwen-coder",  # Best for JSON generation
        default_temperature=0.3,  # Lower = more deterministic output
        agent_models={
            "input_enhancer": "local-qwen-coder",      # Good at analysis
            "router": "local-qwen-coder",              # Good at classification
            "game_planner": "local-qwen-coder",        # Structured output
            "scene_generator": "local-qwen-coder",     # Critical: best for JSON
            "story_generator": "local-qwen-coder",     # Legacy
            "blueprint_generator": "local-qwen-coder", # Critical: best for JSON
            "diagram_spec_generator": "local-qwen-coder",
            "diagram_svg_generator": "local-llama",
            "blueprint_validator": "local-llama",      # Simple validation
            "code_generator": "local-deepseek-coder",  # Best for code
            "code_verifier": "local-llama",            # Simple verification
            "critic": "local-qwen-coder",              # Analysis
            "judge": "local-qwen-coder",               # Reasoning
            "supervisor": "local-qwen-coder",          # Coordination
            "proposer": "local-qwen-coder",            # Proposals
        },
        agent_temperatures={
            "input_enhancer": 0.3,       # Consistent analysis
            "router": 0.2,               # Very low for consistent routing
            "game_planner": 0.4,         # Some creativity
            "scene_generator": 0.2,      # Very low for JSON accuracy
            "story_generator": 0.4,      # Legacy
            "blueprint_generator": 0.2,  # Very low for JSON accuracy
            "diagram_spec_generator": 0.2,
            "diagram_svg_generator": 0.1,
            "blueprint_validator": 0.1,  # Deterministic
            "code_generator": 0.2,       # Low for deterministic code
            "code_verifier": 0.1,        # Deterministic
            "critic": 0.2,               # Consistent critique
            "judge": 0.1,                # Consistent judgment
        },
        agent_max_tokens={
            "input_enhancer": 2048,
            "router": 1024,
            "game_planner": 4096,
            "scene_generator": 6144,      # Reduced to prevent truncation
            "story_generator": 4096,      # Legacy
            "blueprint_generator": 6144,  # Reduced to prevent truncation
            "diagram_spec_generator": 3072,
            "diagram_svg_generator": 1024,
            "blueprint_validator": 1024,
            "code_generator": 8192,
            "code_verifier": 1024,
            "critic": 2048,
            "judge": 2048,
        }
    ),

    # -------------------------------------------------------------------------
    # Anthropic Only: Use only Claude models (no OpenAI dependency)
    # -------------------------------------------------------------------------
    "anthropic_only": AgentModelConfig(
        default_model="claude-sonnet",
        default_temperature=0.7,
        agent_models={
            "input_enhancer": "claude-sonnet",
            "router": "claude-haiku",
            "game_planner": "claude-sonnet",
            "scene_generator": "claude-opus",
            "story_generator": "claude-opus",  # Legacy
            "blueprint_generator": "claude-sonnet",
            "blueprint_validator": "claude-haiku",
            "code_generator": "claude-sonnet",
            "code_verifier": "claude-haiku",
            "critic": "claude-opus",
            "judge": "claude-opus",
        }
    ),

    # -------------------------------------------------------------------------
    # OpenAI Only: Use only GPT models (no Anthropic dependency)
    # -------------------------------------------------------------------------
    "openai_only": AgentModelConfig(
        default_model="gpt-4-turbo",
        default_temperature=0.7,
        agent_models={
            "input_enhancer": "gpt-4-turbo",
            "router": "gpt-4o-mini",
            "game_planner": "gpt-4-turbo",
            "scene_generator": "gpt-4o",
            "story_generator": "gpt-4o",  # Legacy
            "blueprint_generator": "gpt-4o",
            "blueprint_validator": "gpt-4o-mini",
            "code_generator": "gpt-4o",
            "code_verifier": "gpt-4o-mini",
            "critic": "gpt-4o",
            "judge": "gpt-4o",
        }
    ),

    # -------------------------------------------------------------------------
    # Groq Free: Use Groq's free tier (Llama 3.3, Llama 3.1)
    # Sign up at: https://console.groq.com
    # Estimated cost: $0 (free tier with rate limits)
    # -------------------------------------------------------------------------
    "groq_free": AgentModelConfig(
        default_model="llama-3.3-70b-versatile",
        default_temperature=0.7,
        agent_models={
            "input_enhancer": "llama-3.3-70b-versatile",
            "router": "llama-3.1-8b-instant",       # Fast routing
            "game_planner": "llama-3.3-70b-versatile",
            "scene_generator": "llama-3.3-70b-versatile",
            "story_generator": "llama-3.3-70b-versatile",  # Legacy
            "blueprint_generator": "llama-3.3-70b-versatile",
            "blueprint_validator": "llama-3.1-8b-instant",  # Fast validation
            "code_generator": "llama-3.3-70b-versatile",
            "code_verifier": "llama-3.1-8b-instant",
            "critic": "llama-3.3-70b-versatile",
            "judge": "llama-3.3-70b-versatile",
            "supervisor": "llama-3.3-70b-versatile",
            "proposer": "llama-3.3-70b-versatile",
        },
        agent_temperatures={
            "input_enhancer": 0.3,
            "router": 0.3,
            "game_planner": 0.7,
            "story_generator": 0.8,
            "blueprint_generator": 0.4,
            "blueprint_validator": 0.1,
            "code_generator": 0.4,
            "code_verifier": 0.1,
            "critic": 0.2,
            "judge": 0.1,
        }
    ),

    # -------------------------------------------------------------------------
    # Open Source: Use only LOCAL or GROQ models (open source)
    # Estimated cost: $0 (local) or free tier (Groq)
    # -------------------------------------------------------------------------
    "open_source": AgentModelConfig(
        default_model="local-llama",
        default_temperature=0.7,
        agent_models={
            "input_enhancer": "local-qwen-coder",
            "router": "local-qwen-coder",
            "game_planner": "local-llama",
            "scene_generator": "local-qwen-coder",
            "story_generator": "local-qwen-coder",  # Legacy
            "blueprint_generator": "local-qwen-coder",
            "diagram_spec_generator": "local-qwen-coder",
            "diagram_svg_generator": "local-llama",
            "blueprint_validator": "local-llama",
            "code_generator": "local-deepseek-coder",
            "code_verifier": "local-llama",
            "critic": "local-qwen-coder",
            "judge": "local-qwen-coder",
            "supervisor": "local-qwen-coder",
            "proposer": "local-qwen-coder",
        },
        agent_temperatures={
            "input_enhancer": 0.3,
            "router": 0.3,
            "game_planner": 0.7,
            "scene_generator": 0.2,
            "story_generator": 0.4,  # Legacy
            "blueprint_generator": 0.2,
            "diagram_spec_generator": 0.2,
            "diagram_svg_generator": 0.1,
            "blueprint_validator": 0.1,
            "code_generator": 0.2,
            "code_verifier": 0.1,
            "critic": 0.2,
            "judge": 0.1,
        }
    ),

    # -------------------------------------------------------------------------
    # Hybrid Multi-Provider: Optimal model assignment for each agent
    # Uses Qwen (local) for fast tasks, Claude for quality, Gemini for vision
    # Estimated cost: ~$0.10-0.30 per pipeline run
    # -------------------------------------------------------------------------
    "hybrid_multi_provider": AgentModelConfig(
        default_model="local-qwen-coder",
        default_temperature=0.3,
        agent_models={
            # Input processing (fast, local Qwen)
            "input_enhancer": "local-qwen-coder",
            "domain_knowledge_retriever": "local-qwen-coder",
            "router": "local-qwen-coder",

            # Game planning (local Qwen)
            "game_planner": "local-qwen-coder",

            # 3-stage scene generation (local Qwen - fast JSON)
            "scene_stage1_structure": "local-qwen-coder",
            "scene_stage2_assets": "local-qwen-coder",
            "scene_stage3_interactions": "local-qwen-coder",

            # Asset generation pipeline (Claude - quality decisions)
            "asset_planner": "claude-sonnet",
            "asset_generator_orchestrator": "claude-opus",  # Complex orchestration
            "asset_validator": "claude-sonnet",

            # Blueprint generation (Claude - quality JSON)
            "blueprint_generator": "claude-sonnet",
            "blueprint_validator": "claude-sonnet",

            # Diagram generation (Claude - complex SVG/spec)
            "diagram_spec_generator": "claude-sonnet",
            "diagram_svg_generator": "claude-opus",  # Complex SVG rendering

            # Code generation (local for code)
            "code_generator": "local-deepseek-coder",
            "code_verifier": "local-qwen-coder",

            # Topology agents (use Claude for quality)
            "critic": "claude-sonnet",
            "judge": "claude-sonnet",
            "supervisor": "claude-sonnet",
            "proposer": "local-qwen-coder",
            "memory_retriever": "local-qwen-coder",

            # Image pipeline (Gemini vision is used directly, not via LLM)
            "diagram_image_retriever": "local-qwen-coder",
        },
        agent_temperatures={
            "input_enhancer": 0.3,
            "router": 0.1,
            "game_planner": 0.5,
            "scene_stage1_structure": 0.4,
            "scene_stage2_assets": 0.3,
            "scene_stage3_interactions": 0.3,
            "asset_planner": 0.2,
            "asset_generator_orchestrator": 0.3,
            "asset_validator": 0.1,
            "blueprint_generator": 0.2,
            "blueprint_validator": 0.1,
            "diagram_spec_generator": 0.1,
            "diagram_svg_generator": 0.1,
            "code_generator": 0.2,
            "code_verifier": 0.1,
            "critic": 0.2,
            "judge": 0.1,
        },
        agent_max_tokens={
            "input_enhancer": 2048,
            "router": 1024,
            "game_planner": 4096,
            "scene_stage1_structure": 4096,
            "scene_stage2_assets": 6144,
            "scene_stage3_interactions": 4096,
            "asset_planner": 4096,
            "asset_generator_orchestrator": 8192,
            "asset_validator": 2048,
            "blueprint_generator": 16384,  # Large blueprints
            "blueprint_validator": 4096,
            "diagram_spec_generator": 8192,
            "diagram_svg_generator": 8192,
            "code_generator": 8192,
            "code_verifier": 2048,
        }
    ),

    # -------------------------------------------------------------------------
    # Gemini Only: Use only Google Gemini models (no OpenAI/Anthropic dependency)
    # Cost-effective with strong capabilities
    # Estimated cost: ~$0.01-0.05 per pipeline run
    # -------------------------------------------------------------------------
    "gemini_only": AgentModelConfig(
        default_model="gemini-2.5-flash",
        default_temperature=0.3,
        agent_models={
            # Input processing (fast, cheap - use gemini-2.5-flash-lite)
            "input_enhancer": "gemini-2.5-flash-lite",
            "domain_knowledge_retriever": "gemini-2.5-flash-lite",
            "router": "gemini-2.5-flash-lite",

            # Game planning (balanced - use gemini-2.5-flash)
            "game_planner": "gemini-2.5-flash",
            "game_designer": "gemini-2.5-flash",
            "design_interpreter": "gemini-2.5-flash",
            "scene_generator": "gemini-2.5-flash",
            "story_generator": "gemini-2.5-flash",  # Legacy

            # 3-stage scene generation (use gemini-2.5-flash)
            "scene_stage1_structure": "gemini-2.5-flash",
            "scene_stage2_assets": "gemini-2.5-flash",
            "scene_stage3_interactions": "gemini-2.5-flash",

            # Asset generation pipeline (complex tasks - use gemini-3-flash)
            "asset_planner": "gemini-2.5-flash",
            "asset_generator_orchestrator": "gemini-3-flash",  # Complex orchestration
            "asset_validator": "gemini-2.5-flash-lite",  # Simple validation

            # Blueprint generation (complex - use gemini-3-flash)
            "blueprint_generator": "gemini-3-flash",
            "blueprint_validator": "gemini-2.5-flash-lite",

            # Diagram generation (complex - use gemini-3-flash)
            "diagram_spec_generator": "gemini-3-flash",
            "diagram_svg_generator": "gemini-3-flash",

            # Code generation
            "code_generator": "gemini-2.5-flash",
            "code_verifier": "gemini-2.5-flash-lite",

            # Topology agents (balanced)
            "critic": "gemini-2.5-flash",
            "judge": "gemini-2.5-flash",
            "supervisor": "gemini-2.5-flash",
            "proposer": "gemini-2.5-flash",
            "memory_retriever": "gemini-2.5-flash-lite",

            # Image pipeline agents (fast)
            "diagram_image_retriever": "gemini-2.5-flash-lite",

            # V3 pipeline agents
            "game_designer_v3": "gemini-2.5-pro",  # ReAct creative design needs strong model
            "scene_architect_v3": "gemini-2.5-pro",  # ReAct — must follow tool-calling workflow
            "interaction_designer_v3": "gemini-2.5-pro",  # ReAct — must follow tool-calling workflow
            "asset_generator_v3": "gemini-2.5-flash",  # Multi-step asset ops
            "blueprint_assembler_v3": "gemini-2.5-flash",  # ReAct assembly + repair
            "asset_orchestrator_v3": "gemini-2.5-flash",  # Legacy deterministic orchestration
            "asset_spec_builder": "gemini-2.5-flash-lite",  # Deterministic

            # V4 Algorithm pipeline agents
            "v4a_dk_retriever": "gemini-2.5-flash",
            "v4a_game_concept_designer": "gemini-2.5-pro",  # Complex multi-scene game design
            "v4a_scene_content_gen_state_tracer": "gemini-2.5-pro",  # Long structured JSON with code+steps
            "v4a_scene_content_gen_bug_hunter": "gemini-2.5-pro",  # Multi-round bugs with code
            "v4a_scene_content_gen_algorithm_builder": "gemini-2.5-pro",  # Parsons blocks with code
            "v4a_scene_content_gen_complexity_analyzer": "gemini-2.5-flash",  # Simpler pattern (flash tier per contracts.py)
            "v4a_scene_content_gen_constraint_puzzle": "gemini-2.5-pro",  # Board config + constraints
        },
        agent_temperatures={
            "input_enhancer": 0.3,
            "router": 0.1,               # Very low for consistent routing
            "domain_knowledge_retriever": 0.2,
            "game_planner": 0.5,
            "game_designer": 0.7,
            "game_designer_v3": 0.7,     # Creative design benefits from higher temperature
            "design_interpreter": 0.3,
            "scene_generator": 0.4,
            "scene_stage1_structure": 0.4,
            "scene_stage2_assets": 0.3,
            "scene_stage3_interactions": 0.3,
            "interaction_designer": 0.4,
            "asset_planner": 0.2,
            "asset_generator_orchestrator": 0.3,
            "asset_validator": 0.1,
            "blueprint_generator": 0.2,  # Low for reliable JSON
            "blueprint_validator": 0.1,
            "diagram_spec_generator": 0.1,
            "diagram_svg_generator": 0.1,
            "code_generator": 0.2,
            "code_verifier": 0.1,
            "critic": 0.2,
            "judge": 0.1,
            # V4 Algorithm pipeline agents
            "v4a_game_concept_designer": 0.7,  # Creative game design
            "v4a_scene_content_gen_state_tracer": 0.3,  # Structured JSON
            "v4a_scene_content_gen_bug_hunter": 0.3,
            "v4a_scene_content_gen_algorithm_builder": 0.3,
            "v4a_scene_content_gen_complexity_analyzer": 0.2,
            "v4a_scene_content_gen_constraint_puzzle": 0.3,
        },
        agent_max_tokens={
            "input_enhancer": 2048,
            "router": 1024,
            "game_planner": 4096,
            "game_designer": 8192,
            "design_interpreter": 6144,
            "scene_generator": 8192,
            "scene_stage1_structure": 6144,
            "scene_stage2_assets": 6144,
            "scene_stage3_interactions": 8192,
            "interaction_designer": 6144,
            "asset_planner": 4096,
            "asset_generator_orchestrator": 8192,
            "asset_validator": 2048,
            "blueprint_generator": 16384,  # Large blueprints
            "blueprint_validator": 4096,
            "diagram_spec_generator": 8192,
            "diagram_svg_generator": 8192,
            "code_generator": 8192,
            "code_verifier": 2048,
            # V3 pipeline agents
            "game_designer_v3": 16384,  # Large structured output (multi-scene design)
            # V4 Algorithm pipeline agents
            "v4a_dk_retriever": 4096,
            "v4a_game_concept_designer": 8192,
            "v4a_scene_content_gen_state_tracer": 16384,
            "v4a_scene_content_gen_bug_hunter": 16384,
            "v4a_scene_content_gen_algorithm_builder": 12288,
            "v4a_scene_content_gen_complexity_analyzer": 12288,
            "v4a_scene_content_gen_constraint_puzzle": 12288,
        }
    ),

    # -------------------------------------------------------------------------
    # Closed Source: Use only OPENAI or ANTHROPIC models
    # Estimated cost: ~$0.05-0.15 per pipeline run
    # -------------------------------------------------------------------------
    "closed_source": AgentModelConfig(
        default_model="claude-sonnet",
        default_temperature=0.7,
        agent_models={
            "input_enhancer": "claude-sonnet",
            "router": "claude-haiku",
            "game_planner": "gpt-4-turbo",
            "scene_generator": "claude-sonnet",
            "story_generator": "claude-sonnet",  # Legacy
            "blueprint_generator": "gpt-4o",
            "diagram_spec_generator": "gpt-4o",
            "diagram_svg_generator": "claude-haiku",
            "blueprint_validator": "claude-haiku",
            "code_generator": "gpt-4o",
            "code_verifier": "claude-haiku",
            "critic": "claude-sonnet",
            "judge": "claude-sonnet",
            "supervisor": "claude-sonnet",
            "proposer": "gpt-4-turbo",
        },
        agent_temperatures={
            "input_enhancer": 0.3,
            "router": 0.3,
            "game_planner": 0.7,
            "scene_generator": 0.7,
            "story_generator": 0.8,  # Legacy
            "blueprint_generator": 0.4,
            "diagram_spec_generator": 0.2,
            "diagram_svg_generator": 0.1,
            "blueprint_validator": 0.1,
            "code_generator": 0.4,
            "code_verifier": 0.1,
            "critic": 0.2,
            "judge": 0.1,
        }
    ),
}


def get_models_by_source_type(source_type: Literal["open_source", "closed_source"]) -> Dict[str, "ModelConfig"]:
    """Get models filtered by open source vs closed source"""
    from app.config.models import MODEL_REGISTRY, ModelProvider
    
    if source_type == "open_source":
        # LOCAL and GROQ are open source
        return {
            k: v for k, v in MODEL_REGISTRY.items()
            if v.provider in [ModelProvider.LOCAL, ModelProvider.GROQ]
        }
    else:  # closed_source
        # OPENAI and ANTHROPIC are closed source
        return {
            k: v for k, v in MODEL_REGISTRY.items()
            if v.provider in [ModelProvider.OPENAI, ModelProvider.ANTHROPIC]
        }


# =============================================================================
# CONFIGURATION LOADING
# =============================================================================

def load_config_from_env() -> AgentModelConfig:
    """
    Load agent configuration from environment variables.

    Priority:
    1. AGENT_CONFIG_PRESET (set by user's provider selection)
    2. Individual AGENT_MODEL_<NAME> overrides
    3. Individual AGENT_TEMPERATURE_<NAME> overrides
    4. Default "balanced" preset

    The system respects the user's explicit provider selection and does NOT
    automatically override to local models regardless of USE_OLLAMA setting.

    Returns:
        AgentModelConfig with merged settings
    """
    # Start with preset (or balanced default)
    preset_name = os.getenv("AGENT_CONFIG_PRESET", "balanced")
    if preset_name not in PRESET_CONFIGS:
        logger.warning(
            f"Unknown preset '{preset_name}', using 'balanced'. "
            f"Available: {list(PRESET_CONFIGS.keys())}"
        )
        preset_name = "balanced"

    logger.info(f"Loading agent model configuration with preset: {preset_name}")
    
    # Copy preset (don't modify original)
    import copy
    config = copy.deepcopy(PRESET_CONFIGS[preset_name])

    # Merge any new agents from default config (keeps presets forward-compatible)
    base_defaults = AgentModelConfig()
    for agent_name, model_key in base_defaults.agent_models.items():
        if agent_name not in config.agent_models:
            config.agent_models[agent_name] = model_key
    for agent_name, temp in base_defaults.agent_temperatures.items():
        if agent_name not in config.agent_temperatures:
            config.agent_temperatures[agent_name] = temp

    # REMOVED: USE_OLLAMA override logic that ignores user selection
    # The system now respects the user's explicit provider selection via presets

    # Apply individual model overrides (after preset selection)
    for env_key, env_value in os.environ.items():
        if env_key.startswith("AGENT_MODEL_"):
            agent_name = env_key[12:].lower()  # Remove prefix, lowercase
            if env_value in MODEL_REGISTRY:
                config.agent_models[agent_name] = env_value
                logger.info(f"Override: {agent_name} model → {env_value}")
            else:
                logger.warning(f"Unknown model in {env_key}: {env_value}")

    # Apply individual temperature overrides
    for env_key, env_value in os.environ.items():
        if env_key.startswith("AGENT_TEMPERATURE_"):
            agent_name = env_key[18:].lower()  # Remove prefix, lowercase
            try:
                temp = float(env_value)
                config.agent_temperatures[agent_name] = temp
                logger.info(f"Override: {agent_name} temperature → {temp}")
            except ValueError:
                logger.warning(f"Invalid temperature in {env_key}: {env_value}")

    return config


def get_agent_config(preset: str = "balanced") -> AgentModelConfig:
    """
    Get a preset agent configuration.

    Args:
        preset: Name of preset ("cost_optimized", "quality_optimized", "balanced")

    Returns:
        AgentModelConfig for the preset
    """
    if preset not in PRESET_CONFIGS:
        raise ValueError(
            f"Unknown preset: '{preset}'. Available: {list(PRESET_CONFIGS.keys())}"
        )
    return PRESET_CONFIGS[preset]


# Context-aware runtime configuration (per-run context)
_runtime_config_var: ContextVar[Optional[AgentModelConfig]] = ContextVar('agent_config', default=None)


def get_runtime_config() -> AgentModelConfig:
    """Get the runtime configuration (per-run context)"""
    config = _runtime_config_var.get()
    if config is None:
        config = load_config_from_env()
        _runtime_config_var.set(config)
    return config


def set_runtime_config(config: AgentModelConfig) -> None:
    """Set the runtime configuration for current context"""
    _runtime_config_var.set(config)
