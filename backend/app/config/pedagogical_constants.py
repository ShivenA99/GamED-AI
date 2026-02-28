"""
Centralized pedagogical constants — single source of truth.

All agents import from here instead of defining their own copies.
Design decision: difficulty is always "advanced", scoring is always 10 pts/zone.
"""

BLOOM_LEVELS = ["remember", "understand", "apply", "analyze", "evaluate", "create"]

BLOOM_COMPLEXITY = {
    "remember": 1,
    "understand": 2,
    "apply": 3,
    "analyze": 4,
    "evaluate": 5,
    "create": 6,
}

# Fixed difficulty — no progression, always advanced
DIFFICULTY_LEVEL = "advanced"

# Fixed scoring — no difficulty multiplier
DEFAULT_SCORING = {
    "base_points_per_zone": 10,
    "time_bonus_max_percent": 20,
    "partial_credit_multiplier": 0.5,
    "penalty_per_incorrect": 5,
}

DEFAULT_THRESHOLDS = {
    "perfect": 100,
    "great": 70,
    "good": 50,
}

DEFAULT_FEEDBACK = {
    "perfect": "Perfect! You labeled everything correctly!",
    "good": "Great job! You got most of them right!",
    "retry": "Keep practicing! You'll get better!",
}

DEFAULT_TIMING = {
    "transition_delay_ms": 1000,
    "feedback_display_ms": 1500,
    "confetti_duration_perfect_ms": 4000,
    "confetti_duration_good_ms": 2500,
}
