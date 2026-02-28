"""
Example Game Designs for Agent Learning

This module provides exemplar game designs that teach the Game Designer agent
how to reason about combining interaction patterns for different learning objectives.

These examples demonstrate:
- Multi-pattern game design
- Scene progression strategies
- Pattern selection rationale
- Pedagogical reasoning

The Game Designer agent uses these examples as few-shot learning prompts.
"""

from typing import Dict, List, Any


# =============================================================================
# EXAMPLE GAME DESIGNS
# =============================================================================

EXAMPLE_GAME_DESIGNS: List[Dict[str, Any]] = [
    # =========================================================================
    # Example 1: Multi-Pattern Anatomy Game
    # =========================================================================
    {
        "question": "Label the parts of the human heart and show how blood flows through it",
        "analysis": {
            "learning_intents": [
                "identify_parts",
                "trace_process",
                "understand_function"
            ],
            "content_type": "anatomy",
            "is_multi_part": True,
            "requires_sequence": True
        },
        "design": {
            "learning_outcomes": [
                "Identify and name the 4 chambers of the heart",
                "Trace the path of blood through the heart",
                "Explain the function of each chamber in circulation"
            ],
            "scenes": [
                {
                    "scene": 1,
                    "title": "Name the Chambers",
                    "pattern": "drag_drop",
                    "purpose": "Build foundational knowledge of heart anatomy",
                    "diagram_requirements": "Full heart cross-section",
                    "zones_needed": ["left_atrium", "right_atrium", "left_ventricle", "right_ventricle"],
                    "scoring_weight": 0.4
                },
                {
                    "scene": 2,
                    "title": "Follow the Blood",
                    "pattern": "trace_path",
                    "purpose": "Understand the directional flow of blood",
                    "diagram_requirements": "Heart with blood vessels visible",
                    "zones_needed": ["path_waypoints"],
                    "scoring_weight": 0.3,
                    "prerequisites": ["scene_1"]
                },
                {
                    "scene": 3,
                    "title": "Chamber Functions",
                    "pattern": "description_matching",
                    "purpose": "Connect structure to function",
                    "diagram_requirements": "Highlighted chambers",
                    "zones_needed": ["same_as_scene_1"],
                    "scoring_weight": 0.3,
                    "descriptions_to_match": [
                        "Receives deoxygenated blood from the body",
                        "Pumps blood to the lungs",
                        "Receives oxygenated blood from the lungs",
                        "Pumps blood to the entire body"
                    ]
                }
            ],
            "scene_structure": "linear",
            "reasoning": "The question has two parts: 'label' (naming) AND 'show flow' (process). "
                        "This requires multiple patterns. We start with drag_drop to establish "
                        "vocabulary, then trace_path for flow understanding, then description_matching "
                        "to consolidate learning by connecting structure to function."
        }
    },

    # =========================================================================
    # Example 2: Comparison Game
    # =========================================================================
    {
        "question": "Compare plant and animal cells - identify their similarities and differences",
        "analysis": {
            "learning_intents": [
                "compare_structures",
                "identify_similarities",
                "identify_differences"
            ],
            "content_type": "comparison",
            "is_multi_part": False,
            "requires_comparison": True
        },
        "design": {
            "learning_outcomes": [
                "Identify organelles common to both cell types",
                "Identify organelles unique to plant cells",
                "Identify organelles unique to animal cells",
                "Explain why these differences exist"
            ],
            "scenes": [
                {
                    "scene": 1,
                    "title": "Spot the Differences",
                    "pattern": "compare_contrast",
                    "purpose": "Visual comparison of both cell types side by side",
                    "diagram_requirements": "Plant cell and animal cell diagrams side by side",
                    "zones_needed": [
                        "plant_cell_wall", "chloroplast", "large_vacuole",  # Plant-only
                        "centrioles", "lysosomes",  # Animal-only
                        "nucleus", "mitochondria", "endoplasmic_reticulum"  # Shared
                    ],
                    "scoring_weight": 0.5
                },
                {
                    "scene": 2,
                    "title": "Sort the Features",
                    "pattern": "sorting_categories",
                    "purpose": "Reinforce distinction through active categorization",
                    "categories": ["Plant Only", "Animal Only", "Both"],
                    "items": [
                        "Cell wall", "Chloroplast", "Large central vacuole",
                        "Centrioles", "Lysosomes",
                        "Nucleus", "Mitochondria", "Cell membrane", "Ribosomes"
                    ],
                    "scoring_weight": 0.5
                }
            ],
            "scene_structure": "linear",
            "reasoning": "A comparison question needs compare_contrast as the primary pattern. "
                        "We follow with sorting_categories to reinforce the distinctions made "
                        "in the comparison. This dual approach helps cement the differences."
        }
    },

    # =========================================================================
    # Example 3: Hierarchical Anatomy Game
    # =========================================================================
    {
        "question": "Label the parts of the digestive system, including the structures within each organ",
        "analysis": {
            "learning_intents": [
                "identify_parts",
                "understand_hierarchy",
                "explore_detail"
            ],
            "content_type": "anatomy",
            "has_hierarchy": True,
            "depth": 3
        },
        "design": {
            "learning_outcomes": [
                "Identify the major organs of the digestive system",
                "Identify sub-structures within the stomach",
                "Identify sub-structures within the small intestine",
                "Understand the relationship between organs and their components"
            ],
            "scenes": [
                {
                    "scene": 1,
                    "title": "The Digestive Journey",
                    "pattern": "hierarchical",
                    "purpose": "Progressive exploration from organs to sub-structures",
                    "diagram_requirements": "Full digestive system with expandable regions",
                    "hierarchy": {
                        "level_1": ["mouth", "esophagus", "stomach", "small_intestine", "large_intestine"],
                        "stomach_children": ["fundus", "body", "pylorus"],
                        "small_intestine_children": ["duodenum", "jejunum", "ileum"]
                    },
                    "reveal_trigger": "complete_parent",
                    "scoring_weight": 1.0
                }
            ],
            "scene_structure": "single",
            "reasoning": "The question asks for structures 'within each organ', indicating hierarchy. "
                        "We use the hierarchical pattern with progressive reveal. When the user "
                        "labels an organ correctly, its sub-structures appear. This mimics the "
                        "natural way anatomists describe nested structures."
        }
    },

    # =========================================================================
    # Example 4: Process/Timeline Game
    # =========================================================================
    {
        "question": "Explain the stages of mitosis in order",
        "analysis": {
            "learning_intents": [
                "understand_sequence",
                "identify_stages",
                "recognize_characteristics"
            ],
            "content_type": "process",
            "is_sequential": True
        },
        "design": {
            "learning_outcomes": [
                "Identify the stages of mitosis in correct order",
                "Recognize key characteristics of each stage",
                "Understand the progression from one stage to the next"
            ],
            "scenes": [
                {
                    "scene": 1,
                    "title": "Order the Stages",
                    "pattern": "sequencing",
                    "purpose": "Establish correct order of mitosis stages",
                    "items": ["Prophase", "Metaphase", "Anaphase", "Telophase"],
                    "correct_order": [0, 1, 2, 3],
                    "scoring_weight": 0.4
                },
                {
                    "scene": 2,
                    "title": "Match the Characteristics",
                    "pattern": "description_matching",
                    "purpose": "Connect each stage to its defining feature",
                    "descriptions": [
                        "Chromosomes condense and become visible",
                        "Chromosomes align at the cell's equator",
                        "Sister chromatids separate and move to poles",
                        "Nuclear envelopes reform around chromosome sets"
                    ],
                    "scoring_weight": 0.3
                },
                {
                    "scene": 3,
                    "title": "Test Your Knowledge",
                    "pattern": "timed_challenge",
                    "wrapped_pattern": "click_to_identify",
                    "purpose": "Mastery check with time pressure",
                    "time_limit_seconds": 45,
                    "scoring_weight": 0.3
                }
            ],
            "scene_structure": "linear",
            "reasoning": "Sequence questions need sequencing pattern first to establish order. "
                        "We add description_matching to ensure understanding beyond memorized "
                        "order. The timed challenge at the end tests automaticity/mastery."
        }
    },

    # =========================================================================
    # Example 5: Diagnostic/Decision Game
    # =========================================================================
    {
        "question": "What happens if a cell's mitochondria stop functioning? Diagnose the effects.",
        "analysis": {
            "learning_intents": [
                "predict_consequences",
                "apply_knowledge",
                "reason_about_function"
            ],
            "content_type": "functional_reasoning",
            "requires_decision_making": True
        },
        "design": {
            "learning_outcomes": [
                "Identify the function of mitochondria",
                "Predict the effects of mitochondrial failure",
                "Connect organelle function to cell survival"
            ],
            "scenes": [
                {
                    "scene": 1,
                    "title": "Diagnostic Investigation",
                    "pattern": "branching_scenario",
                    "purpose": "Guide through diagnostic reasoning process",
                    "scenario": "A cell's energy production has stopped. Investigate why.",
                    "nodes": [
                        {
                            "id": "start",
                            "question": "Where is ATP primarily produced?",
                            "options": ["Mitochondria", "Nucleus", "Ribosome"],
                            "correct": "Mitochondria",
                            "consequence_correct": "Correct! Let's examine the mitochondria.",
                            "consequence_incorrect": "Not quite. Remember which organelle is the 'powerhouse'."
                        },
                        {
                            "id": "effects",
                            "question": "What would happen without ATP?",
                            "options": [
                                "Cell cannot perform active transport",
                                "Cell cannot make proteins",
                                "Cell cannot replicate DNA"
                            ],
                            "correct": "Cell cannot perform active transport",
                            "explanation": "Active transport requires energy (ATP)."
                        }
                    ],
                    "scoring_weight": 1.0
                }
            ],
            "scene_structure": "single",
            "reasoning": "This is a 'what-if' question requiring diagnostic reasoning. "
                        "branching_scenario is ideal because it guides the learner through "
                        "a logical investigation, showing consequences of their reasoning."
        }
    },

    # =========================================================================
    # Example 6: Simple Labeling Game
    # =========================================================================
    {
        "question": "Label the parts of a flower",
        "analysis": {
            "learning_intents": [
                "identify_parts"
            ],
            "content_type": "anatomy",
            "is_simple": True
        },
        "design": {
            "learning_outcomes": [
                "Identify and name the main parts of a flower"
            ],
            "scenes": [
                {
                    "scene": 1,
                    "title": "Parts of a Flower",
                    "pattern": "drag_drop",
                    "purpose": "Learn flower anatomy through interactive labeling",
                    "diagram_requirements": "Clear flower cross-section diagram",
                    "zones_needed": ["petal", "sepal", "stamen", "pistil", "anther", "stigma"],
                    "scoring_weight": 1.0
                }
            ],
            "scene_structure": "single",
            "reasoning": "This is a straightforward labeling question with no multi-part intent. "
                        "A single drag_drop scene is sufficient. No need to over-engineer."
        }
    },

    # =========================================================================
    # Example 7: Complex Multi-Scene Game with PhET
    # =========================================================================
    {
        "question": "Explore how changing the concentration of solutes affects osmosis",
        "analysis": {
            "learning_intents": [
                "experiment",
                "observe_effects",
                "understand_causation"
            ],
            "content_type": "scientific_inquiry",
            "requires_simulation": True
        },
        "design": {
            "learning_outcomes": [
                "Define osmosis and concentration gradient",
                "Predict the direction of water movement",
                "Explain the effect of concentration on osmotic pressure"
            ],
            "scenes": [
                {
                    "scene": 1,
                    "title": "Label the Setup",
                    "pattern": "drag_drop",
                    "purpose": "Establish vocabulary for osmosis",
                    "diagram_requirements": "Osmosis diagram with membrane, solutions",
                    "zones_needed": ["semipermeable_membrane", "hypotonic", "hypertonic", "isotonic"],
                    "scoring_weight": 0.2
                },
                {
                    "scene": 2,
                    "title": "Explore Osmosis",
                    "pattern": "phet_simulation",
                    "purpose": "Interactive experimentation with osmosis",
                    "simulation_id": "concentration",
                    "checkpoints": [
                        {"condition": "concentration_difference > 50", "prompt": "What happens to water?"},
                        {"condition": "equilibrium_reached", "prompt": "Why did movement stop?"}
                    ],
                    "scoring_weight": 0.5
                },
                {
                    "scene": 3,
                    "title": "Predict the Outcome",
                    "pattern": "branching_scenario",
                    "purpose": "Apply understanding to novel scenarios",
                    "scoring_weight": 0.3
                }
            ],
            "scene_structure": "linear",
            "reasoning": "Questions about 'how X affects Y' benefit from simulation. We start with "
                        "vocabulary building (drag_drop), then hands-on exploration (phet_simulation), "
                        "then application (branching_scenario). This follows the explore-explain-apply cycle."
        }
    },
]


# =============================================================================
# PATTERN SELECTION HEURISTICS
# =============================================================================

PATTERN_SELECTION_HEURISTICS: Dict[str, List[str]] = {
    # Content-based heuristics
    "labeling_parts": ["drag_drop"],
    "showing_process": ["trace_path"],
    "understanding_function": ["description_matching"],
    "comparing_items": ["compare_contrast", "sorting_categories"],
    "ordering_sequence": ["sequencing"],
    "making_decisions": ["branching_scenario"],
    "exploring_variables": ["phet_simulation", "parameter_discovery"],
    "testing_mastery": ["timed_challenge", "click_to_identify"],
    "nested_structures": ["hierarchical"],

    # Multi-part question patterns
    "label_and_trace": ["drag_drop", "trace_path"],
    "label_and_explain": ["drag_drop", "description_matching"],
    "compare_and_sort": ["compare_contrast", "sorting_categories"],
    "learn_and_test": ["drag_drop", "timed_challenge"],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_example_for_content_type(content_type: str) -> List[Dict[str, Any]]:
    """Get example designs that match a content type."""
    return [
        ex for ex in EXAMPLE_GAME_DESIGNS
        if ex.get("analysis", {}).get("content_type") == content_type
    ]


def get_example_for_pattern(pattern_id: str) -> List[Dict[str, Any]]:
    """Get example designs that use a specific pattern."""
    results = []
    for ex in EXAMPLE_GAME_DESIGNS:
        scenes = ex.get("design", {}).get("scenes", [])
        for scene in scenes:
            if scene.get("pattern") == pattern_id:
                results.append(ex)
                break
    return results


def get_multi_scene_examples() -> List[Dict[str, Any]]:
    """Get example designs with multiple scenes."""
    return [
        ex for ex in EXAMPLE_GAME_DESIGNS
        if len(ex.get("design", {}).get("scenes", [])) > 1
    ]


def format_examples_for_prompt(max_examples: int = 3) -> str:
    """
    Format example designs for inclusion in LLM prompts.

    Returns a concise description of example designs suitable for few-shot learning.
    """
    lines = ["=== EXAMPLE GAME DESIGNS ===\n"]

    for i, example in enumerate(EXAMPLE_GAME_DESIGNS[:max_examples], 1):
        design = example.get("design", {})
        scenes = design.get("scenes", [])

        lines.append(f"\n### Example {i}: {example['question'][:60]}...")
        lines.append(f"Content type: {example.get('analysis', {}).get('content_type', 'unknown')}")
        lines.append(f"Number of scenes: {len(scenes)}")
        lines.append(f"Scene structure: {design.get('scene_structure', 'single')}")

        lines.append("Scenes:")
        for scene in scenes:
            lines.append(f"  - Scene {scene.get('scene', '?')}: {scene.get('pattern', '?')} - {scene.get('purpose', '')[:50]}")

        lines.append(f"Reasoning: {design.get('reasoning', '')[:150]}...")

    return "\n".join(lines)


def get_heuristic_patterns(intent: str) -> List[str]:
    """Get suggested patterns for a learning intent."""
    return PATTERN_SELECTION_HEURISTICS.get(intent, [])
