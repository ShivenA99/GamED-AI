"""
Interaction Pattern Library

Machine-readable capability manifest that agents reason about to select
optimal interaction patterns for educational games.

Each pattern defines:
- Cognitive demands (what skills it exercises)
- Best use cases (when to use this pattern)
- Complexity level
- Implementation status
- Required frontend components

This library enables truly agentic game design - agents reason about
WHAT patterns to use based on content, not hardcoded Bloom's mappings.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field


class PatternStatus(Enum):
    """Implementation status of an interaction pattern."""
    COMPLETE = "complete"          # Fully implemented and tested
    PARTIAL = "partial"            # Partially implemented, some features missing
    MISSING = "missing"            # Not yet implemented
    EXPERIMENTAL = "experimental"  # In development, may change


class PatternComplexity(Enum):
    """Complexity level of an interaction pattern."""
    LOW = "low"                    # Simple, single action
    LOW_TO_MEDIUM = "low_to_medium"
    MEDIUM = "medium"              # Multiple steps, some reasoning
    MEDIUM_TO_HIGH = "medium_to_high"
    HIGH = "high"                  # Complex reasoning, multiple interactions


@dataclass
class InteractionPattern:
    """Definition of an interaction pattern."""
    id: str
    name: str
    description: str
    cognitive_demands: List[str]
    best_for: List[str]
    complexity: PatternComplexity
    status: PatternStatus
    frontend_component: str
    supports_multi_scene: bool = False
    supports_timing: bool = False
    supports_partial_credit: bool = True
    prerequisites: List[str] = field(default_factory=list)
    can_combine_with: List[str] = field(default_factory=list)
    configuration_options: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# INTERACTION PATTERN LIBRARY
# =============================================================================

INTERACTION_PATTERNS: Dict[str, InteractionPattern] = {
    # =========================================================================
    # CORE PATTERNS (Complete)
    # =========================================================================

    "drag_drop": InteractionPattern(
        id="drag_drop",
        name="Drag and Drop Labeling",
        description="User drags labels from a pool to correct positions on a diagram. "
                   "Immediate feedback on placement. Supports shuffled labels and hints.",
        cognitive_demands=[
            "recall",
            "spatial_reasoning",
            "association",
            "visual_matching"
        ],
        best_for=[
            "labeling parts of diagrams",
            "matching terms to locations",
            "anatomy identification",
            "component naming",
            "vocabulary building"
        ],
        complexity=PatternComplexity.LOW_TO_MEDIUM,
        status=PatternStatus.COMPLETE,
        frontend_component="DragDropZones",
        supports_multi_scene=True,
        supports_timing=True,
        supports_partial_credit=True,
        can_combine_with=["description_matching", "hierarchical", "sequencing"],
        configuration_options={
            "shuffle_labels": True,
            "show_hints": True,
            "allow_reposition": True,
            "snap_to_zone": True,
            "max_attempts": 3
        }
    ),

    "hierarchical": InteractionPattern(
        id="hierarchical",
        name="Hierarchical Progressive Reveal",
        description="Labels are revealed progressively based on parent-child relationships. "
                   "User completes parent labels before children appear. Supports deep nesting.",
        cognitive_demands=[
            "hierarchical_thinking",
            "part_whole_reasoning",
            "systematic_exploration",
            "relationship_understanding"
        ],
        best_for=[
            "nested anatomical structures",
            "organizational hierarchies",
            "taxonomy classification",
            "systems with components and sub-components",
            "geological layers"
        ],
        complexity=PatternComplexity.MEDIUM,
        status=PatternStatus.COMPLETE,
        frontend_component="HierarchicalDragDrop",
        supports_multi_scene=True,
        supports_timing=False,
        supports_partial_credit=True,
        prerequisites=["drag_drop"],
        can_combine_with=["drag_drop", "description_matching"],
        configuration_options={
            "reveal_trigger": "complete_parent",  # or "click_expand", "hover_reveal"
            "max_depth": 5,
            "show_structure_preview": False,
            "animate_reveal": True
        }
    ),

    "click_to_identify": InteractionPattern(
        id="click_to_identify",
        name="Click to Identify",
        description="User clicks on zones when prompted with a label name. "
                   "Simple identification task, good for memorization.",
        cognitive_demands=[
            "recall",
            "recognition",
            "visual_identification"
        ],
        best_for=[
            "basic memorization",
            "identification practice",
            "review exercises",
            "quick assessments",
            "beginner learners"
        ],
        complexity=PatternComplexity.LOW,
        status=PatternStatus.COMPLETE,
        frontend_component="ClickToIdentify",
        supports_multi_scene=True,
        supports_timing=True,
        supports_partial_credit=True,
        can_combine_with=["drag_drop", "timed_challenge"],
        configuration_options={
            "prompt_style": "name",  # or "description", "function"
            "highlight_on_hover": True,
            "show_feedback_immediately": True
        }
    ),

    # =========================================================================
    # EXTENDED PATTERNS (Partial/In Development)
    # =========================================================================

    "trace_path": InteractionPattern(
        id="trace_path",
        name="Path Tracing",
        description="User traces a path through connected elements in correct order. "
                   "Good for process flows, blood circulation, electrical circuits.",
        cognitive_demands=[
            "sequence_understanding",
            "process_flow_comprehension",
            "cause_effect_reasoning",
            "spatial_navigation"
        ],
        best_for=[
            "blood flow paths",
            "nerve signal pathways",
            "food chain sequences",
            "water cycles",
            "electrical circuits",
            "metabolic pathways"
        ],
        complexity=PatternComplexity.MEDIUM,
        status=PatternStatus.COMPLETE,  # Tools + frontend component ready
        frontend_component="PathDrawer",
        supports_multi_scene=True,
        supports_timing=True,
        supports_partial_credit=True,
        prerequisites=["click_to_identify"],
        can_combine_with=["drag_drop", "sequencing"],
        configuration_options={
            "drawing_mode": "click_waypoints",  # or "freehand"
            "show_valid_paths": False,
            "allow_backtrack": True,
            "highlight_endpoints": True
        }
    ),

    "description_matching": InteractionPattern(
        id="description_matching",
        name="Description Matching",
        description="Match functional descriptions to diagram zones. Tests understanding "
                   "of purpose/function rather than just names.",
        cognitive_demands=[
            "comprehension",
            "function_understanding",
            "semantic_reasoning",
            "application_of_knowledge"
        ],
        best_for=[
            "organ functions",
            "component roles",
            "purpose identification",
            "deeper understanding tasks",
            "functional analysis"
        ],
        complexity=PatternComplexity.MEDIUM,
        status=PatternStatus.COMPLETE,  # Tools + frontend component ready
        frontend_component="DescriptionMatcher",
        supports_multi_scene=True,
        supports_timing=True,
        supports_partial_credit=True,
        prerequisites=["drag_drop"],
        can_combine_with=["drag_drop", "hierarchical"],
        configuration_options={
            "mode": "match_to_zone",  # or "zone_to_description", "multiple_choice"
            "show_zone_names": False,
            "randomize_descriptions": True
        }
    ),

    # =========================================================================
    # ADDITIONAL PATTERNS (Implemented)
    # =========================================================================

    "sequencing": InteractionPattern(
        id="sequencing",
        name="Sequence Builder",
        description="User arranges elements in correct chronological or logical order. "
                   "Supports both linear sequences and branching paths.",
        cognitive_demands=[
            "temporal_reasoning",
            "causality_understanding",
            "logical_ordering",
            "process_comprehension"
        ],
        best_for=[
            "timelines",
            "life cycles",
            "historical events",
            "process steps",
            "algorithmic sequences",
            "development stages"
        ],
        complexity=PatternComplexity.MEDIUM,
        status=PatternStatus.COMPLETE,  # Implemented: SequenceBuilder.tsx
        frontend_component="SequenceBuilder",
        supports_multi_scene=True,
        supports_timing=True,
        supports_partial_credit=True,
        can_combine_with=["drag_drop", "trace_path"],
        configuration_options={
            "sequence_type": "linear",  # or "branching", "parallel"
            "allow_partial_order": False,
            "show_position_hints": True,
            "animate_on_complete": True
        }
    ),

    "compare_contrast": InteractionPattern(
        id="compare_contrast",
        name="Compare and Contrast",
        description="User identifies similarities and differences between two or more "
                   "diagrams or structures shown side by side.",
        cognitive_demands=[
            "analysis",
            "evaluation",
            "comparative_reasoning",
            "critical_thinking",
            "pattern_recognition"
        ],
        best_for=[
            "comparing cell types",
            "healthy vs diseased structures",
            "before/after comparisons",
            "species comparisons",
            "structural variations"
        ],
        complexity=PatternComplexity.HIGH,
        status=PatternStatus.COMPLETE,  # Implemented: CompareContrast.tsx
        frontend_component="CompareContrast",
        supports_multi_scene=False,  # Usually single scene with multiple diagrams
        supports_timing=True,
        supports_partial_credit=True,
        prerequisites=["drag_drop"],
        can_combine_with=["sorting_categories"],
        configuration_options={
            "comparison_mode": "side_by_side",  # or "overlay", "toggle"
            "highlight_matching": True,
            "categories": ["similar", "different", "unique_to_a", "unique_to_b"]
        }
    ),

    "sorting_categories": InteractionPattern(
        id="sorting_categories",
        name="Sorting into Categories",
        description="User sorts items into predefined categories. Good for classification "
                   "tasks and distinguishing features.",
        cognitive_demands=[
            "classification",
            "categorization",
            "attribute_identification",
            "grouping_logic"
        ],
        best_for=[
            "plant vs animal features",
            "classifying by properties",
            "grouping by function",
            "taxonomic classification",
            "state of matter identification"
        ],
        complexity=PatternComplexity.MEDIUM,
        status=PatternStatus.COMPLETE,  # Implemented: SortingCategories.tsx
        frontend_component="SortingCategories",
        supports_multi_scene=True,
        supports_timing=True,
        supports_partial_credit=True,
        can_combine_with=["compare_contrast", "drag_drop"],
        configuration_options={
            "num_categories": 2,  # Typically 2-4
            "category_labels": [],
            "allow_multiple_per_item": False,
            "show_category_hints": True
        }
    ),

    "branching_scenario": InteractionPattern(
        id="branching_scenario",
        name="Branching Scenario",
        description="User navigates through decision points with consequences. "
                   "Good for diagnostic reasoning and ethical dilemmas.",
        cognitive_demands=[
            "decision_making",
            "consequence_prediction",
            "critical_analysis",
            "hypothesis_testing",
            "ethical_reasoning"
        ],
        best_for=[
            "diagnostic reasoning",
            "troubleshooting procedures",
            "ethical decision making",
            "patient scenarios",
            "debugging algorithms",
            "safety procedures"
        ],
        complexity=PatternComplexity.HIGH,
        status=PatternStatus.COMPLETE,  # Implemented: BranchingScenario.tsx
        frontend_component="BranchingScenario",
        supports_multi_scene=True,  # Each branch can be a scene
        supports_timing=False,
        supports_partial_credit=True,
        can_combine_with=["click_to_identify"],
        configuration_options={
            "show_path_taken": True,
            "allow_backtrack": True,
            "show_consequences": True,
            "multiple_valid_endings": True
        }
    ),

    "memory_match": InteractionPattern(
        id="memory_match",
        name="Memory Match",
        description="Classic card-matching game adapted for educational content. "
                   "Match terms to definitions, images to labels, etc.",
        cognitive_demands=[
            "memory",
            "association",
            "pattern_matching",
            "visual_recognition"
        ],
        best_for=[
            "vocabulary building",
            "term-definition matching",
            "image-concept association",
            "review and reinforcement",
            "gamified memorization"
        ],
        complexity=PatternComplexity.LOW,
        status=PatternStatus.COMPLETE,  # Implemented: MemoryMatch.tsx
        frontend_component="MemoryMatch",
        supports_multi_scene=False,
        supports_timing=True,
        supports_partial_credit=False,  # Usually binary success
        can_combine_with=["timed_challenge"],
        configuration_options={
            "grid_size": [4, 4],
            "card_type": "text_text",  # or "image_text", "image_image"
            "flip_duration_ms": 500,
            "show_attempts_counter": True
        }
    ),

    "timed_challenge": InteractionPattern(
        id="timed_challenge",
        name="Timed Challenge",
        description="Wrapper pattern that adds time pressure to other interactions. "
                   "Good for mastery assessment and engagement.",
        cognitive_demands=[
            "speed",
            "automaticity",
            "recall_under_pressure",
            "efficiency"
        ],
        best_for=[
            "mastery assessment",
            "fluency building",
            "competitive games",
            "review mode",
            "gamification"
        ],
        complexity=PatternComplexity.LOW_TO_MEDIUM,
        status=PatternStatus.COMPLETE,  # Implemented: TimedChallengeWrapper.tsx
        frontend_component="TimedChallengeWrapper",
        supports_multi_scene=True,
        supports_timing=True,  # By definition
        supports_partial_credit=True,
        can_combine_with=["drag_drop", "click_to_identify", "memory_match", "sequencing"],
        configuration_options={
            "time_limit_seconds": 60,
            "show_timer": True,
            "time_bonus_scoring": True,
            "pause_allowed": False
        }
    ),

    # =========================================================================
    # ADVANCED PATTERNS (Research Phase)
    # =========================================================================

    "phet_simulation": InteractionPattern(
        id="phet_simulation",
        name="PhET Simulation Integration",
        description="Embeds PhET interactive simulations with guided exploration and checkpoints. "
                   "Good for scientific inquiry and experimentation.",
        cognitive_demands=[
            "experimentation",
            "hypothesis_testing",
            "variable_manipulation",
            "observation",
            "data_interpretation"
        ],
        best_for=[
            "physics concepts",
            "chemistry reactions",
            "mathematical visualizations",
            "scientific inquiry",
            "cause-effect exploration"
        ],
        complexity=PatternComplexity.HIGH,
        status=PatternStatus.EXPERIMENTAL,  # From PhET research
        frontend_component="PhETSimulation",
        supports_multi_scene=True,
        supports_timing=False,
        supports_partial_credit=True,
        can_combine_with=["branching_scenario"],
        configuration_options={
            "simulation_id": "",
            "checkpoints": [],
            "guided_mode": True,
            "free_exploration_time": 60
        }
    ),

    "parameter_discovery": InteractionPattern(
        id="parameter_discovery",
        name="Parameter Discovery (PhET-style)",
        description="User adjusts variables and observes effects. Good for understanding "
                   "cause-effect relationships and mathematical functions.",
        cognitive_demands=[
            "experimentation",
            "hypothesis_testing",
            "variable_manipulation",
            "cause_effect_reasoning"
        ],
        best_for=[
            "scientific simulations",
            "mathematical functions",
            "physics concepts",
            "what-if scenarios",
            "sensitivity analysis"
        ],
        complexity=PatternComplexity.HIGH,
        status=PatternStatus.EXPERIMENTAL,  # From PhET research
        frontend_component="ParameterPlayground",
        supports_multi_scene=True,
        supports_timing=False,
        supports_partial_credit=True,
        can_combine_with=["trace_path"],
        configuration_options={
            "parameters": [],
            "visualization_type": "graph",  # or "animation", "table"
            "record_observations": True
        }
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_pattern(pattern_id: str) -> Optional[InteractionPattern]:
    """Get an interaction pattern by ID."""
    return INTERACTION_PATTERNS.get(pattern_id)


def get_patterns_by_status(status: PatternStatus) -> List[InteractionPattern]:
    """Get all patterns with a specific status."""
    return [p for p in INTERACTION_PATTERNS.values() if p.status == status]


def get_patterns_for_cognitive_demand(demand: str) -> List[InteractionPattern]:
    """Get patterns that exercise a specific cognitive demand."""
    return [p for p in INTERACTION_PATTERNS.values() if demand in p.cognitive_demands]


def get_patterns_best_for(use_case: str) -> List[InteractionPattern]:
    """Get patterns that are best for a specific use case (fuzzy match)."""
    use_case_lower = use_case.lower()
    return [
        p for p in INTERACTION_PATTERNS.values()
        if any(use_case_lower in bf.lower() for bf in p.best_for)
    ]


def get_combinable_patterns(pattern_id: str) -> List[InteractionPattern]:
    """Get patterns that can be combined with a given pattern."""
    pattern = get_pattern(pattern_id)
    if not pattern:
        return []
    return [
        INTERACTION_PATTERNS[pid]
        for pid in pattern.can_combine_with
        if pid in INTERACTION_PATTERNS
    ]


def get_implemented_patterns() -> List[InteractionPattern]:
    """Get all patterns that are at least partially implemented."""
    return [
        p for p in INTERACTION_PATTERNS.values()
        if p.status in [PatternStatus.COMPLETE, PatternStatus.PARTIAL]
    ]


def format_patterns_for_prompt() -> str:
    """
    Format the interaction patterns library for inclusion in LLM prompts.

    Returns a concise, structured description suitable for agent reasoning.
    """
    lines = ["=== AVAILABLE INTERACTION PATTERNS ===\n"]

    for pattern in INTERACTION_PATTERNS.values():
        status_emoji = {
            PatternStatus.COMPLETE: "[READY]",
            PatternStatus.PARTIAL: "[PARTIAL]",
            PatternStatus.MISSING: "[PLANNED]",
            PatternStatus.EXPERIMENTAL: "[EXPERIMENTAL]"
        }[pattern.status]

        lines.append(f"\n### {pattern.name} ({pattern.id}) {status_emoji}")
        lines.append(f"Description: {pattern.description}")
        lines.append(f"Complexity: {pattern.complexity.value}")
        lines.append(f"Best for: {', '.join(pattern.best_for[:4])}")
        lines.append(f"Cognitive demands: {', '.join(pattern.cognitive_demands[:4])}")
        if pattern.can_combine_with:
            lines.append(f"Combines with: {', '.join(pattern.can_combine_with)}")

    return "\n".join(lines)


def get_pattern_summary() -> Dict[str, Any]:
    """Get a summary of all patterns for debugging/monitoring."""
    return {
        "total_patterns": len(INTERACTION_PATTERNS),
        "by_status": {
            status.value: len(get_patterns_by_status(status))
            for status in PatternStatus
        },
        "implemented": [p.id for p in get_implemented_patterns()],
        "missing": [p.id for p in get_patterns_by_status(PatternStatus.MISSING)]
    }


# =============================================================================
# SCORING STRATEGIES
# =============================================================================

SCORING_STRATEGIES = {
    "standard": {
        "id": "standard",
        "name": "Standard Scoring",
        "description": "Standard scoring based on correct placements",
        "base_points_per_zone": 10,
        "partial_credit": True,
        "time_bonus_enabled": False,
        "hint_penalty_percentage": 20,
        "formula": "score = (correct_zones / total_zones) * max_score - hint_penalty",
    },
    "time_based": {
        "id": "time_based",
        "name": "Time-Based Scoring",
        "description": "Points decrease with time spent, bonus for fast completion",
        "base_points_per_zone": 15,
        "partial_credit": True,
        "time_bonus_enabled": True,
        "time_bonus_max": 50,
        "hint_penalty_percentage": 25,
        "formula": "score = base_score + time_bonus - hint_penalty",
    },
    "mastery": {
        "id": "mastery",
        "name": "Mastery Mode",
        "description": "All-or-nothing for mastery demonstration",
        "base_points_per_zone": 0,
        "partial_credit": False,
        "completion_bonus": 100,
        "hint_penalty_percentage": 50,
        "formula": "score = 100 if all_correct else 0",
    },
    "progressive": {
        "id": "progressive",
        "name": "Progressive Multiplier",
        "description": "Points increase for consecutive correct answers",
        "base_points_per_zone": 5,
        "partial_credit": True,
        "streak_multiplier": 1.5,
        "max_multiplier": 3.0,
        "hint_penalty_percentage": 30,
        "formula": "score = base * min(streak_multiplier^streak, max_multiplier)",
    },
    "exploration": {
        "id": "exploration",
        "name": "Exploration Mode",
        "description": "Minimal scoring, focus on learning without pressure",
        "base_points_per_zone": 1,
        "partial_credit": True,
        "completion_bonus": 10,
        "hint_penalty_percentage": 0,
        "formula": "score = completion_percentage * 10",
    },
    "adaptive": {
        "id": "adaptive",
        "name": "Adaptive Difficulty",
        "description": "Points adjust based on difficulty level",
        "base_points_per_zone": 10,
        "partial_credit": True,
        "difficulty_multipliers": {
            "easy": 0.5,
            "intermediate": 1.0,
            "advanced": 1.5,
            "expert": 2.0,
        },
        "hint_penalty_percentage": 15,
        "formula": "score = base * difficulty_multiplier - hint_penalty",
    },
}


# =============================================================================
# ANIMATION REGISTRY
# =============================================================================

SUPPORTED_ANIMATIONS = {
    # Core animations (always available)
    "pulse": {
        "id": "pulse",
        "name": "Pulse",
        "description": "Gentle pulsing to draw attention",
        "css_animation": "pulse 2s ease-in-out infinite",
        "use_cases": ["highlight_zone", "draw_attention", "hint"],
        "frontend_supported": True,
    },
    "glow": {
        "id": "glow",
        "name": "Glow",
        "description": "Glowing effect around element",
        "css_animation": "glow 1.5s ease-in-out infinite",
        "use_cases": ["correct_answer", "highlight_zone", "success"],
        "frontend_supported": True,
    },
    "scale": {
        "id": "scale",
        "name": "Scale",
        "description": "Scale up/down animation",
        "css_animation": "scale 0.3s ease-out",
        "use_cases": ["on_click", "on_drop", "feedback"],
        "frontend_supported": True,
    },
    "shake": {
        "id": "shake",
        "name": "Shake",
        "description": "Shake effect for incorrect answers",
        "css_animation": "shake 0.5s ease-in-out",
        "use_cases": ["incorrect_answer", "error", "warning"],
        "frontend_supported": True,
    },
    "fade": {
        "id": "fade",
        "name": "Fade",
        "description": "Fade in/out transition",
        "css_animation": "fadeIn 0.4s ease-out",
        "use_cases": ["reveal", "hide", "transition", "progressive_show"],
        "frontend_supported": True,
    },
    "bounce": {
        "id": "bounce",
        "name": "Bounce",
        "description": "Bouncy entrance animation",
        "css_animation": "bounce 0.6s ease-out",
        "use_cases": ["on_correct", "celebration", "entrance"],
        "frontend_supported": True,
    },

    # Extended animations
    "confetti": {
        "id": "confetti",
        "name": "Confetti",
        "description": "Confetti burst for celebrations",
        "requires_library": True,
        "use_cases": ["completion", "perfect_score", "achievement"],
        "frontend_supported": True,
    },
    "path_draw": {
        "id": "path_draw",
        "name": "Path Draw",
        "description": "Animated path drawing for connections",
        "css_animation": "stroke-dashoffset 1s ease-in-out",
        "use_cases": ["trace_path", "show_connection", "reveal_relationship"],
        "frontend_supported": True,
    },
    "ripple": {
        "id": "ripple",
        "name": "Ripple",
        "description": "Ripple effect from click point",
        "css_animation": "ripple 0.6s ease-out",
        "use_cases": ["on_click", "feedback", "interaction"],
        "frontend_supported": True,
    },
    "highlight_connections": {
        "id": "highlight_connections",
        "name": "Highlight Connections",
        "description": "Highlight related zones and their connections",
        "css_animation": "highlight 0.8s ease-in-out",
        "use_cases": ["show_relationships", "hierarchical_reveal", "trace"],
        "frontend_supported": True,
    },
    "slide_in": {
        "id": "slide_in",
        "name": "Slide In",
        "description": "Slide in from direction",
        "css_animation": "slideIn 0.4s ease-out",
        "use_cases": ["reveal_children", "progressive_show", "entrance"],
        "frontend_supported": True,
    },
    "zoom_focus": {
        "id": "zoom_focus",
        "name": "Zoom Focus",
        "description": "Zoom and focus on element",
        "css_animation": "zoomFocus 0.5s ease-out",
        "use_cases": ["detail_view", "expand", "focus"],
        "frontend_supported": True,
    },
    "sparkle": {
        "id": "sparkle",
        "name": "Sparkle",
        "description": "Sparkle effect for special achievements",
        "requires_library": True,
        "use_cases": ["achievement", "bonus", "special"],
        "frontend_supported": True,
    },
    "morph": {
        "id": "morph",
        "name": "Morph",
        "description": "Shape morphing between states",
        "css_animation": "morph 0.5s ease-in-out",
        "use_cases": ["state_change", "transform", "transition"],
        "frontend_supported": False,  # Planned
    },
}


# =============================================================================
# MULTI-MODE GAME SUPPORT
# =============================================================================

def check_pattern_compatibility(primary: str, secondary: str) -> bool:
    """Check if two patterns are compatible for multi-mode games."""
    primary_pattern = get_pattern(primary)
    secondary_pattern = get_pattern(secondary)

    if not primary_pattern or not secondary_pattern:
        return False

    # Check explicit compatibility
    if secondary in primary_pattern.can_combine_with:
        return True
    if primary in secondary_pattern.can_combine_with:
        return True

    return False


def get_compatible_patterns_list(pattern_id: str) -> List[str]:
    """Get list of pattern IDs compatible with the given pattern."""
    pattern = get_pattern(pattern_id)
    if not pattern:
        return []
    return pattern.can_combine_with


def validate_multi_mode_combination(modes: List[str]) -> Dict[str, Any]:
    """
    Validate a combination of interaction modes for a multi-mode game.

    Args:
        modes: List of mode IDs to combine

    Returns:
        Dict with valid flag, errors, warnings, and suggestions
    """
    if not modes:
        return {"valid": False, "errors": ["No modes provided"]}

    if len(modes) == 1:
        pattern = get_pattern(modes[0])
        if not pattern:
            return {"valid": False, "errors": [f"Unknown mode: {modes[0]}"]}
        if pattern.status == PatternStatus.MISSING:
            return {"valid": False, "errors": [f"Mode not implemented: {modes[0]}"]}
        return {"valid": True, "errors": [], "warnings": []}

    errors = []
    warnings = []

    # Check all modes exist and are implemented
    for mode in modes:
        pattern = get_pattern(mode)
        if not pattern:
            errors.append(f"Unknown mode: {mode}")
        elif pattern.status == PatternStatus.MISSING:
            errors.append(f"Mode not implemented: {mode}")
        elif pattern.status == PatternStatus.EXPERIMENTAL:
            warnings.append(f"Mode is experimental: {mode}")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Check pairwise compatibility
    for i, mode1 in enumerate(modes):
        for mode2 in modes[i+1:]:
            if not check_pattern_compatibility(mode1, mode2):
                warnings.append(
                    f"Modes '{mode1}' and '{mode2}' may not combine well"
                )

    # Check complexity doesn't compound too much
    total_complexity = 0
    complexity_values = {
        PatternComplexity.LOW: 1,
        PatternComplexity.LOW_TO_MEDIUM: 2,
        PatternComplexity.MEDIUM: 3,
        PatternComplexity.MEDIUM_TO_HIGH: 4,
        PatternComplexity.HIGH: 5,
    }
    for mode in modes:
        pattern = get_pattern(mode)
        if pattern:
            total_complexity += complexity_values.get(pattern.complexity, 3)

    if total_complexity > 8:
        warnings.append(
            f"Combined complexity is high ({total_complexity}), "
            "consider simplifying for better user experience"
        )

    return {
        "valid": True,
        "errors": [],
        "warnings": warnings,
        "total_complexity": total_complexity,
        "modes": modes,
    }


def suggest_secondary_modes(primary_mode: str, blooms_level: str = None) -> List[str]:
    """
    Suggest secondary modes that complement a primary mode.

    Args:
        primary_mode: The primary interaction mode
        blooms_level: Optional Bloom's taxonomy level for filtering

    Returns:
        List of suggested secondary mode IDs
    """
    compatible = get_compatible_patterns_list(primary_mode)

    if not compatible:
        return []

    if not blooms_level:
        return compatible[:3]  # Return top 3

    # Filter by cognitive demand alignment with Bloom's level
    blooms_demands = {
        "remember": ["recall", "recognition", "memory"],
        "understand": ["comprehension", "association", "visual_matching"],
        "apply": ["application_of_knowledge", "process_comprehension"],
        "analyze": ["analysis", "hierarchical_thinking", "relationship_understanding"],
        "evaluate": ["evaluation", "critical_thinking", "comparative_reasoning"],
        "create": ["decision_making", "hypothesis_testing", "synthesis"],
    }

    target_demands = blooms_demands.get(blooms_level.lower(), [])
    suggestions = []

    for mode_id in compatible:
        pattern = get_pattern(mode_id)
        if pattern and pattern.status in [PatternStatus.COMPLETE, PatternStatus.PARTIAL]:
            # Score by cognitive demand overlap
            overlap = len(set(pattern.cognitive_demands) & set(target_demands))
            suggestions.append((mode_id, overlap))

    # Sort by overlap score and return top 3
    suggestions.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in suggestions[:3]]


# =============================================================================
# ADDITIONAL HELPER FUNCTIONS
# =============================================================================

def get_scoring_strategy(strategy_id: str) -> Optional[Dict[str, Any]]:
    """Get scoring strategy configuration by ID."""
    return SCORING_STRATEGIES.get(strategy_id)


def get_all_scoring_strategies() -> Dict[str, Dict[str, Any]]:
    """Get all scoring strategies."""
    return SCORING_STRATEGIES


def get_animation(animation_id: str) -> Optional[Dict[str, Any]]:
    """Get animation configuration by ID."""
    return SUPPORTED_ANIMATIONS.get(animation_id)


def get_animations_for_use_case(use_case: str) -> List[str]:
    """Get animation IDs suitable for a specific use case."""
    return [
        anim_id for anim_id, anim in SUPPORTED_ANIMATIONS.items()
        if use_case in anim.get("use_cases", []) and anim.get("frontend_supported", True)
    ]


def get_frontend_supported_patterns() -> List[str]:
    """Get list of pattern IDs that are frontend-supported."""
    return [
        p.id for p in INTERACTION_PATTERNS.values()
        if p.status in [PatternStatus.COMPLETE, PatternStatus.PARTIAL]
    ]


def format_scoring_strategies_for_prompt() -> str:
    """Format scoring strategies for inclusion in LLM prompts."""
    lines = ["=== AVAILABLE SCORING STRATEGIES ===\n"]

    for strategy in SCORING_STRATEGIES.values():
        lines.append(f"\n### {strategy['name']} ({strategy['id']})")
        lines.append(f"Description: {strategy['description']}")
        lines.append(f"Base points: {strategy.get('base_points_per_zone', 'N/A')}")
        lines.append(f"Partial credit: {strategy.get('partial_credit', False)}")
        if strategy.get('time_bonus_enabled'):
            lines.append(f"Time bonus: up to {strategy.get('time_bonus_max', 0)} points")

    return "\n".join(lines)


def format_animations_for_prompt() -> str:
    """Format animations for inclusion in LLM prompts."""
    lines = ["=== AVAILABLE ANIMATIONS ===\n"]

    for anim_id, anim in SUPPORTED_ANIMATIONS.items():
        if anim.get("frontend_supported", True):
            lines.append(f"- {anim['name']} ({anim_id}): {anim['description']}")
            lines.append(f"  Use cases: {', '.join(anim.get('use_cases', []))}")

    return "\n".join(lines)
