"""V4 Algorithm Pipeline Contracts — game type classification and model routing."""

from typing import Any

from app.v4_algorithm.schemas.algorithm_game_types import GAME_TYPE_DEFAULT_SCORES


SUPPORTED_GAME_TYPES: set[str] = {
    "state_tracer",
    "bug_hunter",
    "algorithm_builder",
    "complexity_analyzer",
    "constraint_puzzle",
}

# Game types that need visual assets
ASSET_NEEDED_TYPES: set[str] = {
    "state_tracer",       # Optional illustration
    "complexity_analyzer", # Growth charts
    "constraint_puzzle",  # Board illustration
}

# Game types that are purely code-based (no required visual)
CODE_ONLY_TYPES: set[str] = {
    "bug_hunter",
    "algorithm_builder",
}

# Model routing: pro for complex generation, flash for simpler
MODEL_ROUTING: dict[str, str] = {
    "state_tracer": "pro",          # Complex execution traces
    "bug_hunter": "pro",            # Multi-round bug generation
    "algorithm_builder": "pro",     # Correct ordering + distractors
    "complexity_analyzer": "flash", # Simpler pattern
    "constraint_puzzle": "pro",     # Complex constraint design
}


def get_default_score(game_type: str) -> int:
    """Get default max score for a game type."""
    return GAME_TYPE_DEFAULT_SCORES.get(game_type, 400)


def get_model_tier(game_type: str) -> str:
    """Get model tier (pro/flash) for a game type."""
    return MODEL_ROUTING.get(game_type, "pro")


def needs_visual_asset(game_type: str) -> bool:
    """Whether a game type benefits from visual asset generation."""
    return game_type in ASSET_NEEDED_TYPES


def build_capability_spec() -> dict[str, Any]:
    """Build capability spec for prompt injection."""
    return {
        "supported_game_types": sorted(SUPPORTED_GAME_TYPES),
        "asset_needed_types": sorted(ASSET_NEEDED_TYPES),
        "code_only_types": sorted(CODE_ONLY_TYPES),
        "default_scores": GAME_TYPE_DEFAULT_SCORES,
    }
