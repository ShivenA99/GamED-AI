"""
Pipeline Presets

Provides preset configurations for different pipeline modes.
Each preset defines:
- Features to enable/disable
- Agents to disable
- Model assignments per agent

Usage:
    from app.config.presets import PRESET_REGISTRY, get_preset

    # Get a preset config
    preset = get_preset("interactive_diagram_hierarchical")

    # Check if feature is enabled
    if preset["features"]["use_diagram_generation"]:
        ...
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("gamed_ai.config.presets")

# Import preset configurations
from .interactive_diagram_hierarchical import PRESET_CONFIG as INTERACTIVE_DIAGRAM_HIERARCHICAL_CONFIG
from .advanced_interactive_diagram import PRESET_CONFIG as ADVANCED_INTERACTIVE_DIAGRAM_CONFIG
from .had import PRESET_CONFIG as HAD_CONFIG


# Registry of all available presets
PRESET_REGISTRY: Dict[str, Dict[str, Any]] = {
    "interactive_diagram_hierarchical": INTERACTIVE_DIAGRAM_HIERARCHICAL_CONFIG,  # Preset 1
    "advanced_interactive_diagram": ADVANCED_INTERACTIVE_DIAGRAM_CONFIG,          # Preset 2
    "had": HAD_CONFIG,                                                 # HAD (4-cluster)
}


def get_preset(preset_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a preset configuration by name.

    Args:
        preset_name: Name of the preset (e.g., "interactive_diagram_hierarchical")

    Returns:
        Preset configuration dict or None if not found
    """
    if preset_name not in PRESET_REGISTRY:
        logger.warning(
            f"Unknown preset '{preset_name}'. "
            f"Available presets: {list(PRESET_REGISTRY.keys())}"
        )
        return None

    return PRESET_REGISTRY[preset_name]


def is_agent_disabled(preset_name: str, agent_name: str) -> bool:
    """
    Check if an agent is disabled in the given preset.

    Args:
        preset_name: Name of the preset
        agent_name: Name of the agent to check

    Returns:
        True if agent is disabled, False otherwise
    """
    preset = get_preset(preset_name)
    if preset is None:
        return False

    disabled_agents = preset.get("disabled_agents", [])
    return agent_name in disabled_agents


def get_preset_feature(preset_name: str, feature_name: str, default: Any = None) -> Any:
    """
    Get a feature value from a preset.

    Args:
        preset_name: Name of the preset
        feature_name: Name of the feature
        default: Default value if feature not found

    Returns:
        Feature value or default
    """
    preset = get_preset(preset_name)
    if preset is None:
        return default

    features = preset.get("features", {})
    return features.get(feature_name, default)


def list_presets() -> list:
    """List all available preset names."""
    return list(PRESET_REGISTRY.keys())


def get_additional_agents(preset_name: str) -> list:
    """
    Get list of additional agents required by a preset.

    Args:
        preset_name: Name of the preset

    Returns:
        List of additional agent names (empty if none or preset not found)
    """
    preset = get_preset(preset_name)
    if preset is None:
        return []

    return preset.get("additional_agents", [])


def get_preset_routing(preset_name: str, from_agent: str) -> Optional[str]:
    """
    Get the next agent in the routing for a preset.

    Args:
        preset_name: Name of the preset
        from_agent: The agent to get the next routing for

    Returns:
        Name of the next agent or None if not specified
    """
    preset = get_preset(preset_name)
    if preset is None:
        return None

    routing = preset.get("routing", {})
    routing_key = f"{from_agent}_next"
    return routing.get(routing_key)


def is_advanced_preset(preset_name: str) -> bool:
    """
    Check if a preset is an advanced preset (Preset 2+).

    Advanced presets have additional features like:
    - Multi-scene support
    - Polygon zones
    - Bloom's interaction mapping

    Args:
        preset_name: Name of the preset

    Returns:
        True if preset is advanced, False otherwise
    """
    preset = get_preset(preset_name)
    if preset is None:
        return False

    features = preset.get("features", {})
    return features.get("use_multi_scene", False) or \
           features.get("use_polygon_zones", False) or \
           features.get("use_blooms_interaction_mapping", False)
