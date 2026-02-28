"""
Game Planner Agent - THE BRAIN

The game_planner is the central orchestrator that decides:
- How many scenes (n)
- Which mechanics per scene (m[i])
- What assets each scene needs
- How mechanics and scenes connect

Generates game mechanics, scoring rubrics, and difficulty progression
based on the selected template and pedagogical context.

Outputs:
- ExtendedGamePlan with scene_breakdown, mechanics, asset_needs
- Learning objectives aligned with Bloom's level
- Game mechanics specific to the template
- Scoring rubric with partial credit
- Difficulty progression strategy
- Feedback mechanisms
- Interaction mode (based on Bloom's level for Preset 2)

BEHAVIOR:
- Analyzes question to detect needed mechanics (drag_drop, trace_path, sequencing, etc.)
- Determines single vs multi-scene needs
- Generates asset_needs per scene mapped to workflows
- Maintains backward compatibility for simple single-mechanic questions
"""

import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple

from app.agents.state import AgentState, GamePlan
from app.services.llm_service import get_llm_service
from app.agents.schemas.stages import get_game_plan_schema
from app.utils.logging_config import get_logger
from app.agents.instrumentation import InstrumentedAgentContext
from app.config.pedagogical_constants import BLOOM_LEVELS, DIFFICULTY_LEVEL
from app.agents.schemas.game_plan_schemas import (
    ExtendedGamePlan, SceneBreakdown, MechanicSpec, AssetNeed,
    MechanicType, WorkflowType, ProgressionType, TransitionTrigger,
    ModeTransition, SceneTransition, ScoringRubric as ExtendedScoringRubric,
    create_single_scene_plan
)

logger = get_logger("gamed_ai.agents.game_planner")


# =============================================================================
# MECHANIC DETECTION PATTERNS
# =============================================================================
# Keywords and patterns for detecting which game mechanics are needed

MECHANIC_PATTERNS: Dict[MechanicType, List[str]] = {
    MechanicType.DRAG_DROP: [
        r"\blabel\b", r"\bidentif", r"\bname\s+the\b", r"\bparts?\s+of\b",
        r"\bcomponents?\b", r"\bstructures?\b", r"\banatomy\b", r"\bdiagram\b",
        r"\bmatch\b", r"\bplace\b", r"\bdrag\b"
    ],
    MechanicType.TRACE_PATH: [
        r"\btrace\b", r"\bflow\b", r"\bpath\b", r"\bjourney\b", r"\btravel\b",
        r"\bcirculation\b", r"\bblood\s*flow\b", r"\bsignal\b", r"\broute\b",
        r"\bfollow\b", r"\bprocess\s*flow\b"
    ],
    MechanicType.SEQUENCING: [
        r"\border\b", r"\bsequence\b", r"\bsteps?\b", r"\bstages?\b", r"\bphases?\b",
        r"\bprocess\b", r"\bcycle\b", r"\bchronolog", r"\btimeline\b",
        r"\bfirst.*then\b", r"\barrange\b", r"\bsort\b"
    ],
    MechanicType.SORTING: [
        r"\bsort\b", r"\bcategori", r"\bgroup\b", r"\bclassif", r"\borganize\b",
        r"\bbucket\b", r"\btype\b"
    ],
    MechanicType.COMPARISON: [
        r"\bcompare\b", r"\bcontrast\b", r"\bdifferenc", r"\bsimilar", r"\bvs\b",
        r"\bversus\b", r"\bbetween\b"
    ],
    MechanicType.CLICK_TO_IDENTIFY: [
        r"\bclick\b", r"\bselect\b", r"\bpoint\s+to\b", r"\bfind\b", r"\blocate\b",
        r"\bidentify\b"
    ],
    MechanicType.REVEAL: [
        r"\bexplore\b", r"\bdiscover\b", r"\breveal\b", r"\buncover\b", r"\bhidden\b"
    ],
    MechanicType.HOTSPOT: [
        r"\bhotspot\b", r"\binteractive\s*area\b", r"\bclickable\b"
    ],
    MechanicType.MEMORY_MATCH: [
        r"\bmemory\b", r"\bmatching\s*game\b", r"\bpairs?\b", r"\bflip\b"
    ],
    MechanicType.BRANCHING_SCENARIO: [
        r"\bscenario\b", r"\bdecision\b", r"\bchoose\b", r"\bpath\b", r"\bbranch\b",
        r"\bif.*then\b", r"\bconsequence\b"
    ],
}

# Workflow mapping for each mechanic type
MECHANIC_TO_WORKFLOW: Dict[MechanicType, WorkflowType] = {
    MechanicType.DRAG_DROP: WorkflowType.LABELING_DIAGRAM,
    MechanicType.TRACE_PATH: WorkflowType.TRACE_PATH,
    MechanicType.SEQUENCING: WorkflowType.SEQUENCE_ITEMS,
    MechanicType.SORTING: WorkflowType.SORTING,
    MechanicType.COMPARISON: WorkflowType.COMPARISON_DIAGRAMS,
    MechanicType.CLICK_TO_IDENTIFY: WorkflowType.LABELING_DIAGRAM,
    MechanicType.REVEAL: WorkflowType.LABELING_DIAGRAM,
    MechanicType.HOTSPOT: WorkflowType.LABELING_DIAGRAM,
    MechanicType.MEMORY_MATCH: WorkflowType.MEMORY_MATCH,
    MechanicType.BRANCHING_SCENARIO: WorkflowType.BRANCHING_SCENARIO,
}

# Multi-scene trigger patterns
MULTI_SCENE_PATTERNS = [
    r"\bstages?\s+of\b",  # "stages of mitosis"
    r"\bphases?\s+of\b",  # "phases of the moon"
    r"\bcompare.*and\b",  # "compare plant and animal cells"
    r"\bvs\.?\s",  # "heart vs brain"
    r"\bfrom.*to\b",  # "from seed to tree"
    r"\bprocess\s+of\b",  # "process of digestion"
    r"\bthen\b",  # "label AND THEN trace"
    r"\band\s+(also|then)\b",  # "and also/then"
]


# =============================================================================
# MECHANIC DETECTION FUNCTIONS
# =============================================================================

def detect_mechanics_from_question(question_text: str) -> List[Tuple[MechanicType, float]]:
    """
    Analyze question text to detect which game mechanics are needed.

    Returns list of (MechanicType, confidence) tuples sorted by confidence.
    """
    question_lower = question_text.lower()
    detected: List[Tuple[MechanicType, float]] = []

    for mechanic_type, patterns in MECHANIC_PATTERNS.items():
        match_count = 0
        for pattern in patterns:
            if re.search(pattern, question_lower):
                match_count += 1

        if match_count > 0:
            # Confidence based on number of pattern matches
            confidence = min(0.5 + (match_count * 0.15), 1.0)
            detected.append((mechanic_type, confidence))

    # Sort by confidence descending
    detected.sort(key=lambda x: x[1], reverse=True)

    # If no mechanics detected, default to drag_drop for labeling
    if not detected:
        detected = [(MechanicType.DRAG_DROP, 0.5)]

    return detected


def detect_multi_scene_need(question_text: str) -> Tuple[bool, int, str]:
    """
    Determine if question requires multiple scenes.

    Returns:
        (needs_multi_scene, suggested_scene_count, progression_type)
    """
    question_lower = question_text.lower()

    # Check for multi-scene patterns
    for pattern in MULTI_SCENE_PATTERNS:
        if re.search(pattern, question_lower):
            # Estimate scene count based on pattern
            if "stage" in question_lower or "phase" in question_lower:
                # Count stages/phases mentioned
                stage_match = re.findall(r'\b(prophase|metaphase|anaphase|telophase|stage\s*\d+|phase\s*\d+)\b', question_lower)
                count = len(stage_match) if stage_match else 4
                return (True, max(count, 2), "linear")

            if "compare" in question_lower or "vs" in question_lower:
                return (True, 2, "linear")

            if "from" in question_lower and "to" in question_lower:
                return (True, 3, "linear")

            return (True, 2, "linear")

    # Check for AND connecting different mechanics
    if re.search(r'\band\b.*\b(then|also)\b', question_lower):
        return (True, 1, "linear")  # Single scene, multi-mechanic

    return (False, 1, "linear")


def determine_mechanic_dependencies(mechanics: List[MechanicType]) -> Dict[MechanicType, List[MechanicType]]:
    """
    Determine dependencies between mechanics.

    For example, trace_path depends on having diagram zones from drag_drop.
    """
    dependencies: Dict[MechanicType, List[MechanicType]] = {}

    # Trace path needs labeled zones first
    if MechanicType.TRACE_PATH in mechanics:
        if MechanicType.DRAG_DROP in mechanics:
            dependencies[MechanicType.TRACE_PATH] = [MechanicType.DRAG_DROP]
        elif MechanicType.CLICK_TO_IDENTIFY in mechanics:
            dependencies[MechanicType.TRACE_PATH] = [MechanicType.CLICK_TO_IDENTIFY]

    # Sequencing might build on identification
    if MechanicType.SEQUENCING in mechanics:
        if MechanicType.DRAG_DROP in mechanics:
            dependencies[MechanicType.SEQUENCING] = [MechanicType.DRAG_DROP]

    return dependencies


def build_asset_needs_for_mechanic(
    mechanic_type: MechanicType,
    question_text: str,
    dependencies: List[str]
) -> Dict[str, AssetNeed]:
    """
    Build asset needs for a specific mechanic.
    """
    workflow = MECHANIC_TO_WORKFLOW.get(mechanic_type, WorkflowType.LABELING_DIAGRAM)
    asset_needs: Dict[str, AssetNeed] = {}

    # Primary asset need
    if mechanic_type in [MechanicType.DRAG_DROP, MechanicType.CLICK_TO_IDENTIFY, MechanicType.REVEAL, MechanicType.HOTSPOT]:
        asset_needs["diagram_image"] = AssetNeed(
            workflow=workflow,
            query=question_text[:100],  # Use question as search query
            type="image",
            depends_on=[]
        )

    elif mechanic_type == MechanicType.TRACE_PATH:
        asset_needs["paths"] = AssetNeed(
            workflow=WorkflowType.TRACE_PATH,
            type="path_data",
            depends_on=dependencies if dependencies else ["diagram_image"],
            config={"path_type": "animated"}
        )

    elif mechanic_type == MechanicType.SEQUENCING:
        asset_needs["sequence_items"] = AssetNeed(
            workflow=WorkflowType.SEQUENCE_ITEMS,
            type="sequence_data",
            depends_on=dependencies,
            config={"sequence_type": "linear"}
        )

    elif mechanic_type == MechanicType.COMPARISON:
        asset_needs["comparison_diagrams"] = AssetNeed(
            workflow=WorkflowType.COMPARISON_DIAGRAMS,
            query=question_text[:100],
            type="image_pair",
            depends_on=[]
        )

    elif mechanic_type == MechanicType.SORTING:
        asset_needs["sorting_items"] = AssetNeed(
            workflow=WorkflowType.SORTING,
            type="category_data",
            depends_on=[],
            config={"category_count": 2}
        )

    elif mechanic_type == MechanicType.MEMORY_MATCH:
        asset_needs["match_pairs"] = AssetNeed(
            workflow=WorkflowType.MEMORY_MATCH,
            type="pair_data",
            depends_on=[]
        )

    elif mechanic_type == MechanicType.BRANCHING_SCENARIO:
        asset_needs["scenario_tree"] = AssetNeed(
            workflow=WorkflowType.BRANCHING_SCENARIO,
            type="decision_tree",
            depends_on=[]
        )

    return asset_needs


# =============================================================================
# BLOOM'S INTERACTION CONFIG (NOW AGENTIC)
# =============================================================================
# The hardcoded BLOOMS_INTERACTION_MAPPING has been removed.
# Interaction design is now handled by the interaction_designer agent,
# which uses agentic reasoning based on pedagogical context and content structure.
#
# For backwards compatibility, get_blooms_interaction_config() now returns
# None, signaling that the interaction_design from state should be used instead.


def get_blooms_interaction_config(blooms_level: str) -> None:
    """
    DEPRECATED: Use interaction_design from state instead.

    The hardcoded Bloom's → interaction mode mapping has been removed.
    Interaction design is now handled by the interaction_designer agent.

    Returns:
        None - signals to use interaction_design from state
    """
    return None


GAME_PLANNER_PROMPT = """You are an expert educational game designer. Create a detailed game plan for an interactive learning game.

## Question to Gamify:
{question_text}

## Answer Options:
{question_options}

## Pedagogical Context:
- Bloom's Level: {blooms_level}
- Subject: {subject}
- Difficulty: {difficulty}
- Learning Objectives: {learning_objectives}
- Key Concepts: {key_concepts}
- Common Misconceptions: {misconceptions}

## Selected Template: {template_type}

## Template Characteristics:
{template_description}

## Few-Shot Example: STATE_TRACER_CODE for Binary Search

**Question**: "Explain how binary search works on a sorted array. Demonstrate the algorithm finding the number 7 in the array [1, 3, 5, 7, 9, 11, 13]."

**Game Plan**:
```json
{{
    "learning_objectives": [
        "Trace binary search execution step-by-step through multiple iterations",
        "Predict variable values (low, high, mid) at each step",
        "Understand how the search space halves with each comparison",
        "Identify the correct index where target is found"
    ],
    "game_mechanics": [
        {{
            "id": "step_through",
            "type": "step",
            "description": "Step through code execution one line at a time",
            "interaction_type": "click",
            "learning_purpose": "Allows learners to see exactly which line executes and when",
            "scoring_weight": 0.3
        }},
        {{
            "id": "predict_variables",
            "type": "predict",
            "description": "Predict variable values before seeing execution result",
            "interaction_type": "input",
            "learning_purpose": "Tests understanding of how variables change",
            "scoring_weight": 0.4
        }},
        {{
            "id": "analyze_step",
            "type": "step_analysis",
            "description": "Answer questions about what happens in each step",
            "interaction_type": "click",
            "learning_purpose": "Reinforces understanding of algorithm logic",
            "scoring_weight": 0.3
        }}
    ],
    "difficulty_progression": {{
        "initial_state": "Start with simple array of 7 elements, target in middle",
        "progression_rules": [
            "First task: Predict initial mid value (easy)",
            "Second task: Predict which half to search (medium)",
            "Third task: Predict final index (harder)",
            "Fourth task: Count total iterations (advanced)"
        ],
        "hints_available": true,
        "max_attempts": 3
    }},
    "feedback_strategy": {{
        "immediate_feedback": true,
        "feedback_on_correct": "Excellent! You correctly predicted the variable value. Notice how the search space is halved.",
        "feedback_on_incorrect": "Not quite. Remember: if arr[mid] < target, we search the RIGHT half (larger indices). If arr[mid] > target, we search the LEFT half.",
        "misconception_targeting": [
            "If student predicts wrong half: 'Think about sorted order - smaller values are left, larger values are right'",
            "If student gets mid calculation wrong: 'Integer division (//) always rounds down. (0+5)//2 = 2, not 2.5'"
        ]
    }},
    "scoring_rubric": {{
        "max_score": 100,
        "partial_credit": true,
        "time_bonus": false,
        "hint_penalty": 0.1,
        "criteria": [
            {{
                "name": "Variable Prediction Accuracy",
                "weight": 0.4,
                "levels": [
                    {{"score": 0, "description": "Incorrect prediction"}},
                    {{"score": 0.5, "description": "Close but off by one"}},
                    {{"score": 1.0, "description": "Correct prediction"}}
                ]
            }},
            {{
                "name": "Step Analysis",
                "weight": 0.3,
                "levels": [
                    {{"score": 0, "description": "Cannot explain what happens"}},
                    {{"score": 0.5, "description": "Partial understanding"}},
                    {{"score": 1.0, "description": "Clear explanation"}}
                ]
            }},
            {{
                "name": "Completion",
                "weight": 0.3,
                "levels": [
                    {{"score": 0, "description": "Did not complete all steps"}},
                    {{"score": 0.5, "description": "Completed with hints"}},
                    {{"score": 1.0, "description": "Completed independently"}}
                ]
            }}
        ]
    }},
    "estimated_duration_minutes": 12,
    "prerequisite_skills": [
        "Understanding of arrays and indexing",
        "Basic knowledge of search algorithms",
        "Familiarity with while loops"
    ]
}}
```

## Your Task:
Design a game plan that:
1. Aligns game mechanics with the Bloom's taxonomy level
2. Incorporates the key concepts naturally
3. Addresses common misconceptions through gameplay
4. Provides appropriate challenge for the difficulty level
5. For STATE_TRACER_CODE: Focus on step-by-step execution, variable tracking, and code understanding
6. For "order" or "sequence" mechanics: ALWAYS include sequence_items with the correct ordering, sequence_type, and correct_order array

**CRITICAL for order/sequence mechanics:**
If the question involves ordering, sequencing, tracing a path, or showing a process (e.g., "show the order of blood flow"), you MUST:
- Create a mechanic with type "order" or "sequence"
- Include sequence_items array with each step in the correct order
- Set sequence_type to "linear", "cyclic", or "branching"
- Include correct_order array with item IDs in correct sequence

## Response Format (JSON):
{{
    "learning_objectives": [
        "By the end of this game, the learner will be able to...",
        "..."
    ],
    "game_mechanics": [
        {{
            "id": "mechanic_1",
            "type": "<drag_drop|click|input|adjust|order|match|sequence>",
            "description": "<what the player does>",
            "interaction_type": "<how they interact>",
            "learning_purpose": "<why this mechanic helps learning>",
            "scoring_weight": 0.0-1.0,
            // REQUIRED for "order" or "sequence" type mechanics:
            "sequence_items": [  // Only include for order/sequence types
                {{"id": "step_1", "text": "<item text>", "order_index": 0, "description": "<optional description>"}},
                {{"id": "step_2", "text": "<item text>", "order_index": 1}},
                ...
            ],
            "sequence_type": "<linear|cyclic|branching>",  // Only for order/sequence
            "correct_order": ["step_1", "step_2", ...]  // Only for order/sequence
        }}
    ],
    "difficulty_progression": {{
        "initial_state": "<how the game starts>",
        "progression_rules": ["<rule 1>", "<rule 2>"],
        "hints_available": true/false,
        "max_attempts": <number>
    }},
    "feedback_strategy": {{
        "immediate_feedback": true/false,
        "feedback_on_correct": "<what to show>",
        "feedback_on_incorrect": "<what to show>",
        "misconception_targeting": ["<misconception 1 feedback>"]
    }},
    "scoring_rubric": {{
        "max_score": 100,
        "partial_credit": true/false,
        "time_bonus": true/false,
        "hint_penalty": 0.0-1.0,
        "criteria": [
            {{
                "name": "<criterion name>",
                "weight": 0.0-1.0,
                "levels": [
                    {{"score": 0, "description": "No credit"}},
                    {{"score": 0.5, "description": "Partial credit"}},
                    {{"score": 1.0, "description": "Full credit"}}
                ]
            }}
        ]
    }},
    "estimated_duration_minutes": <number>,
    "prerequisite_skills": ["<skill 1>", "<skill 2>"],
    // MULTI-SCENE SUPPORT (only include if question requires multiple scenes/mechanics)
    "scene_breakdown": [  // Only include for multi-scene or multi-mechanic queries
        {{
            "scene_number": 1,
            "title": "<scene title>",
            "topic": "<specific topic for this scene>",
            "focus_labels": ["<label 1>", "<label 2>"],  // Labels specific to this scene
            "interaction_mode": "<drag_drop|trace_path|click_to_identify|sequencing|hierarchical>",
            "secondary_modes": ["<mode2>", "<mode3>"],  // Optional: additional modes for same scene
            "description": "<brief scene description>",
            "tasks": [  // Optional: phases within this scene, each using the same image
                {{
                    "task_id": "<unique_task_id>",
                    "title": "<task title>",
                    "mechanic": "<drag_drop|sequencing|trace_path|click_to_identify>",
                    "focus_labels": ["<subset of labels for this task>"],
                    "scoring_weight": 0.0-1.0,
                    "config": {{}}  // Optional mechanic-specific config
                }}
            ]
        }},
        ...
    ]
}}

**CRITICAL: Scene vs Task distinction:**
- A SCENE = a different image/diagram. Create separate scenes ONLY when the content requires different visuals.
- A TASK = a mechanic or label-subset phase within a scene. Multiple tasks on the SAME image go in ONE scene.
- Example: "label parts of heart" → 1 scene, 3 tasks (chambers drag_drop, vessels drag_drop, blood flow sequencing)
- Example: "compare plant vs animal cell" → 2 scenes (different images), 1 task each
- When in doubt, use ONE scene with multiple tasks.

**MULTI-SCENE & MULTI-MECHANIC DETECTION:**

**Option A: Same image, multiple phases** (use tasks within ONE scene)
Use when all mechanics operate on the SAME content/diagram:
- "Label the parts of heart AND trace the blood flow"
  → 1 scene with tasks: [
      {{"task_id": "chambers", "mechanic": "drag_drop", "focus_labels": ["Right Atrium", ...]}},
      {{"task_id": "vessels", "mechanic": "drag_drop", "focus_labels": ["Aorta", ...]}},
      {{"task_id": "flow", "mechanic": "sequencing", "focus_labels": []}}
    ]
- "Identify flower parts AND explain pollination"
  → 1 scene with tasks for labeling then hierarchical exploration

**Option B: Multiple scenes** (different diagrams or content)
Use when mechanics need DIFFERENT diagrams or focused views:
- "stages of mitosis" → 4 scenes (prophase, metaphase, anaphase, telophase)
- "compare plant vs animal cell" → 2 scenes (plant cell, animal cell)

**Scene interaction_mode mapping:**
- Labeling/identifying → "drag_drop" or "click_to_identify"
- Tracing/flow/path → "trace_path"
- Ordering/sequence → "sequencing"
- Hierarchy/layers → "hierarchical"

For simple single-mechanic labeling (just "label the parts of X"), OMIT scene_breakdown.

Respond with ONLY valid JSON."""


# Template-specific mechanic suggestions
TEMPLATE_MECHANICS = {
    "PARAMETER_PLAYGROUND": {
        "description": "Interactive playground with adjustable parameters and real-time visualization",
        "suggested_mechanics": ["adjust", "observe", "predict", "verify"],
        "interaction_types": ["slider", "input", "dropdown"]
    },
    "SEQUENCE_BUILDER": {
        "description": "Drag-and-drop interface to arrange items in correct order",
        "suggested_mechanics": ["drag_drop", "order", "verify"],
        "interaction_types": ["drag", "drop", "reorder"]
    },
    "BUCKET_SORT": {
        "description": "Categorize items by dragging them into appropriate buckets",
        "suggested_mechanics": ["drag_drop", "categorize", "verify"],
        "interaction_types": ["drag", "drop", "categorize"]
    },
    "INTERACTIVE_DIAGRAM": {
        "description": "Label parts of a diagram by placing labels correctly",
        "suggested_mechanics": ["drag_drop", "place", "identify"],
        "hierarchical_mechanics": ["progressive_reveal", "expand_on_complete"],
        "interaction_types": ["drag", "drop", "place"]
    },
    "TIMELINE_ORDER": {
        "description": "Place events on a timeline in chronological order",
        "suggested_mechanics": ["drag_drop", "order", "place"],
        "interaction_types": ["drag", "drop", "timeline"]
    },
    "MATCH_PAIRS": {
        "description": "Match related items from two columns",
        "suggested_mechanics": ["click", "match", "connect"],
        "interaction_types": ["click", "drag", "connect"]
    },
    "STATE_TRACER_CODE": {
        "description": "Step through code and track variable states",
        "suggested_mechanics": ["step", "predict", "verify"],
        "interaction_types": ["click", "input", "step"]
    },
    "IMAGE_HOTSPOT_QA": {
        "description": "Click on regions of an image to answer questions",
        "suggested_mechanics": ["click", "identify", "answer"],
        "interaction_types": ["click", "select"]
    }
}


def _detect_hierarchical_content(domain_knowledge: dict) -> dict:
    """
    Detect if content has hierarchical relationships requiring special handling.

    Hierarchical mode is needed when:
    - Domain knowledge contains hierarchical_relationships
    - Multiple parent-child relationships exist
    - Children would overlap parents in a flat layout

    Args:
        domain_knowledge: Dictionary containing domain knowledge with optional hierarchical_relationships

    Returns:
        Dictionary with hierarchy detection results:
        - is_hierarchical: bool
        - parent_children: dict mapping parent labels to child labels
        - recommended_mode: "hierarchical" or "drag_drop"
        - reveal_trigger: "complete_parent" (default)
    """
    if not domain_knowledge or not isinstance(domain_knowledge, dict):
        return {"is_hierarchical": False, "recommended_mode": "drag_drop"}

    relationships = domain_knowledge.get("hierarchical_relationships", []) or []

    if not relationships:
        return {"is_hierarchical": False, "recommended_mode": "drag_drop"}

    # Build parent-child mapping
    parent_children = {}
    all_children = set()

    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        parent = (rel.get("parent") or "").lower().strip()
        children = [c.lower().strip() for c in rel.get("children", []) if c]

        if parent and children:
            parent_children[parent] = children
            all_children.update(children)

    # Determine if hierarchical mode is needed
    # Criteria: multiple parent-child relationships OR children would overlap (>=3 total children)
    needs_hierarchical = len(parent_children) >= 2 or len(all_children) >= 3

    if not needs_hierarchical:
        return {
            "is_hierarchical": False,
            "recommended_mode": "drag_drop",
            "parent_children": parent_children if parent_children else None
        }

    logger.info(
        "Detected hierarchical content",
        parent_count=len(parent_children),
        child_count=len(all_children),
        parents=list(parent_children.keys())
    )

    return {
        "is_hierarchical": True,
        "parent_children": parent_children,
        "recommended_mode": "hierarchical",
        "reveal_trigger": "complete_parent"  # Default: show children after parent is labeled
    }


async def game_planner_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    """
    Game Planner Agent

    Generates game mechanics, scoring, and progression based on
    template selection and pedagogical context.

    BEHAVIOR BY PRESET:
    - Preset 1 (interactive_diagram_hierarchical): Original LLM-based planning
    - Preset 2 (advanced_interactive_diagram): Uses game_designer output

    Args:
        state: Current agent state with template_selection and pedagogical_context

    Returns:
        Updated state with game_plan populated
    """
    question_id = state.get('question_id', 'unknown')
    logger.info("Processing question", question_id=question_id, agent_name="game_planner")

    # ==========================================================================
    # PRESET 2 FAST PATH: Use game_designer output if available
    # ==========================================================================
    preset_name = os.getenv("PIPELINE_PRESET", "interactive_diagram_hierarchical")
    game_design = state.get("game_design")

    if preset_name == "advanced_interactive_diagram" and game_design:
        logger.info(
            "Using game_designer output for game_plan (Preset 2)",
            preset=preset_name,
            num_scenes=len(game_design.get("scenes", []))
        )
        game_plan = _convert_game_design_to_plan(game_design, state)

        # Still need to add required_labels and hierarchy_info
        template_type = state.get("template_selection", {}).get("template_type", "")
        domain_knowledge = state.get("domain_knowledge", {})

        if template_type == "INTERACTIVE_DIAGRAM" and domain_knowledge:
            canonical_labels = domain_knowledge.get("canonical_labels", [])
            if canonical_labels:
                game_plan["required_labels"] = [str(label) for label in canonical_labels if label]

            hierarchy_info = _detect_hierarchical_content(domain_knowledge)
            if hierarchy_info:
                game_plan["hierarchy_info"] = hierarchy_info

        return {
            **state,
            "game_plan": game_plan,
            "current_agent": "game_planner"
        }

    # ==========================================================================
    # PRESET 1 / DEFAULT: Original behavior (unchanged)
    # ==========================================================================

    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])
    ped_context = state.get("pedagogical_context", {})
    template_selection = state.get("template_selection", {})
    domain_knowledge = state.get("domain_knowledge", {})

    template_type = template_selection.get("template_type", "PARAMETER_PLAYGROUND")
    
    # For INTERACTIVE_DIAGRAM, extract required_labels and detect hierarchical content
    required_labels = None
    hierarchy_info = None

    if template_type == "INTERACTIVE_DIAGRAM":
        if domain_knowledge and isinstance(domain_knowledge, dict):
            canonical_labels = domain_knowledge.get("canonical_labels", [])
            if canonical_labels and isinstance(canonical_labels, list):
                required_labels = [str(label) for label in canonical_labels if label]
                logger.info(
                    f"Extracted {len(required_labels)} required labels for INTERACTIVE_DIAGRAM",
                    label_count=len(required_labels),
                    labels=required_labels,
                    template_type="INTERACTIVE_DIAGRAM"
                )

            # Detect hierarchical content for progressive reveal
            hierarchy_info = _detect_hierarchical_content(domain_knowledge)
            if hierarchy_info.get("is_hierarchical"):
                logger.info(
                    "Hierarchical content detected for INTERACTIVE_DIAGRAM",
                    parent_children=hierarchy_info.get("parent_children"),
                    recommended_mode=hierarchy_info.get("recommended_mode")
                )
        else:
            logger.warning(
                "domain_knowledge not available for INTERACTIVE_DIAGRAM, required_labels will be None",
                template_type="INTERACTIVE_DIAGRAM"
            )

        # NOTE: Bloom's -> Interaction Mode mapping is now handled by interaction_designer agent
        # The hardcoded BLOOMS_INTERACTION_MAPPING has been removed in favor of agentic design.
        # If interaction_design is available in state, it will be used by downstream agents.

    # Get template-specific info
    template_info = TEMPLATE_MECHANICS.get(template_type, {
        "description": "Interactive educational game",
        "suggested_mechanics": ["interact", "answer", "verify"],
        "interaction_types": ["click", "input"]
    })

    # ==========================================================================
    # MULTI-MECHANIC DETECTION: Analyze question for required mechanics
    # ==========================================================================
    detected_mechanics = detect_mechanics_from_question(question_text)
    needs_multi_scene, suggested_scene_count, progression_type = detect_multi_scene_need(question_text)

    # Determine if scene_breakdown is required
    is_multi_mechanic = len(detected_mechanics) > 1
    requires_scene_breakdown = needs_multi_scene or is_multi_mechanic

    # Build mechanic detection context for prompt
    mechanic_detection_context = ""
    if requires_scene_breakdown:
        mechanic_names = [m[0].value for m in detected_mechanics]
        mechanic_detection_context = f"""
## IMPORTANT - Detected Mechanics (scene_breakdown REQUIRED):
The question analysis detected {len(detected_mechanics)} mechanic(s): {mechanic_names}
{'This is a MULTI-MECHANIC question - you MUST include scene_breakdown.' if is_multi_mechanic else ''}
{'This requires MULTIPLE SCENES.' if needs_multi_scene else ''}

For this question, you MUST include scene_breakdown with:
- scene_number: 1
- interaction_mode: "{mechanic_names[0]}" (primary mechanic)
{f'- secondary_modes: {mechanic_names[1:]}' if len(mechanic_names) > 1 else ''}

DO NOT omit scene_breakdown - this question requires it.
"""
        logger.info(
            "Multi-mechanic/scene detected",
            mechanics=mechanic_names,
            is_multi_mechanic=is_multi_mechanic,
            needs_multi_scene=needs_multi_scene
        )

    # Build prompt
    options_str = "\n".join(f"- {opt}" for opt in question_options) if question_options else "None"

    prev_errors = state.get("current_validation_errors", [])
    error_context = "\n".join(f"- {err}" for err in prev_errors) if prev_errors else "None"
    prompt = GAME_PLANNER_PROMPT.format(
        question_text=question_text,
        question_options=options_str,
        blooms_level=ped_context.get("blooms_level", "understand"),
        subject=ped_context.get("subject", "General"),
        difficulty=DIFFICULTY_LEVEL,
        learning_objectives=json.dumps(ped_context.get("learning_objectives", [])),
        key_concepts=json.dumps(ped_context.get("key_concepts", [])),
        misconceptions=json.dumps(ped_context.get("common_misconceptions", [])),
        template_type=template_type,
        template_description=json.dumps(template_info, indent=2)
    )
    if prev_errors:
        prompt += f"\n\n## Previous Validation Errors (fix these):\n{error_context}"

    # Add mechanic detection context to prompt (CRITICAL for multi-mechanic)
    if mechanic_detection_context:
        prompt += mechanic_detection_context

    try:
        llm = get_llm_service()
        # Use agent-specific model configuration (plug-and-play)
        result = await llm.generate_json_for_agent(
            agent_name="game_planner",
            prompt=prompt,
            schema_hint="GamePlan JSON with game_mechanics, scoring_rubric, difficulty_progression",
            json_schema=get_game_plan_schema()
        )

        # Extract LLM metrics from the result for instrumentation
        llm_metrics = result.pop("_llm_metrics", None) if isinstance(result, dict) else None
        if llm_metrics and ctx:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms")
            )

        # Normalize and validate result
        if result is None:
            raise ValueError("LLM returned None result")

        game_plan = _normalize_game_plan(result, template_type, domain_knowledge)
        
        # Add required_labels and hierarchy_info for INTERACTIVE_DIAGRAM
        if template_type == "INTERACTIVE_DIAGRAM":
            if required_labels:
                game_plan["required_labels"] = required_labels
            if hierarchy_info:
                game_plan["hierarchy_info"] = hierarchy_info

            # NOTE: Interaction mode configuration is now handled by interaction_designer agent.
            # The interaction_design from state will be used by downstream agents.
            # If interaction_design exists in state, use it to set recommended_mode
            # Use 'or {}' pattern because state.get returns None if key exists with None value
            interaction_design = state.get("interaction_design") or {}
            if interaction_design:
                game_plan["recommended_mode"] = interaction_design.get("primary_interaction_mode") or ""
                game_plan["secondary_mode"] = interaction_design.get("secondary_modes", [None])[0] if interaction_design.get("secondary_modes") else None
                game_plan["interaction_features"] = interaction_design.get("multi_mode_config", {})
                logger.info(
                    f"Using agentic interaction design: {game_plan['recommended_mode']}",
                    blooms_level=ped_context.get("blooms_level", "understand")
                )

        logger.info(
            "Created game plan",
            mechanics_count=len(game_plan.get('game_mechanics', [])),
            duration_minutes=game_plan.get('estimated_duration_minutes', 10),
            template_type=template_type
        )
        if required_labels:
            logger.info("Required labels set", required_labels=required_labels, template_type="INTERACTIVE_DIAGRAM")
        if hierarchy_info and hierarchy_info.get("is_hierarchical"):
            logger.info("Hierarchy info set", hierarchy_info=hierarchy_info, template_type="INTERACTIVE_DIAGRAM")

        # Phase 4: Propagate scene_breakdown to top-level state for multi-scene routing
        scene_breakdown = game_plan.get("scene_breakdown", [])

        # Auto-generate scene_breakdown if LLM didn't provide it but multi-mechanic was detected
        if not scene_breakdown and is_multi_mechanic and detected_mechanics:
            mechanic_names = [m[0].value for m in detected_mechanics]
            auto_scene = {
                "scene_number": 1,
                "title": f"Interactive {template_type.replace('_', ' ').title()}",
                "topic": question_text[:100],
                "interaction_mode": mechanic_names[0],
                "secondary_modes": mechanic_names[1:] if len(mechanic_names) > 1 else [],
                "mechanics": [
                    {
                        "type": m_type.value,
                        "scoring_weight": 1.0 / len(mechanic_names),
                        "completion_criteria": "mode_complete"
                    }
                    for m_type, _ in detected_mechanics
                ],
                "asset_needs": {
                    f"{m_type.value}_assets": {
                        "workflow": MECHANIC_TO_WORKFLOW.get(m_type, WorkflowType.LABELING_DIAGRAM).value,
                        "depends_on": [f"{detected_mechanics[0][0].value}_assets"] if i > 0 else []
                    }
                    for i, (m_type, _) in enumerate(detected_mechanics)
                },
                "description": f"Auto-generated scene for multi-mechanic question"
            }
            scene_breakdown = [auto_scene]
            game_plan["scene_breakdown"] = scene_breakdown
            logger.info(
                "Auto-generated scene_breakdown for multi-mechanic question",
                mechanics=mechanic_names,
                scene_count=1
            )

        # Ensure every scene has asset_needs for workflow routing
        # This handles the case where LLM provides scene_breakdown but omits asset_needs
        for scene in scene_breakdown:
            if not scene.get("asset_needs"):
                scene_mechanics = scene.get("mechanics", [])
                if not scene_mechanics:
                    # Build from interaction_mode + secondary_modes
                    modes = [scene.get("interaction_mode") or ""] + scene.get("secondary_modes", [])
                    scene_mechanics = [{"type": m} for m in modes if m]

                asset_needs = {}
                for idx, mech in enumerate(scene_mechanics):
                    m_type = (mech.get("type") or "") if isinstance(mech, dict) else str(mech)
                    # Map to MechanicType enum if possible, default to DRAG_DROP
                    try:
                        mechanic_enum = MechanicType(m_type)
                    except ValueError:
                        mechanic_enum = MechanicType.DRAG_DROP
                    workflow = MECHANIC_TO_WORKFLOW.get(mechanic_enum, WorkflowType.LABELING_DIAGRAM).value
                    asset_key = f"{m_type}_assets"
                    first_key = ((scene_mechanics[0].get("type") or "") if isinstance(scene_mechanics[0], dict) else str(scene_mechanics[0])) + "_assets"
                    asset_needs[asset_key] = {
                        "workflow": workflow,
                        "type": m_type,
                        "depends_on": [first_key] if idx > 0 else []
                    }
                scene["asset_needs"] = asset_needs
                logger.debug(
                    "Auto-generated asset_needs for scene",
                    scene_number=scene.get("scene_number"),
                    asset_needs_keys=list(asset_needs.keys())
                )

        if scene_breakdown:
            logger.info(
                "Multi-scene game detected",
                scene_count=len(scene_breakdown),
                scenes=[s.get("title") for s in scene_breakdown]
            )

        return {
            **state,
            "game_plan": game_plan,
            "scene_breakdown": scene_breakdown,  # For multi_scene_orchestrator routing
            "needs_multi_scene": len(scene_breakdown) > 1,  # Flag for routing
            "current_agent": "game_planner"
        }

    except Exception as e:
        logger.error(
            "LLM call failed, using fallback",
            exc_info=True,
            error_type=type(e).__name__,
            error_message=str(e),
            template_type=template_type
        )

        # Create fallback game plan
        fallback = _create_fallback_game_plan(template_type, ped_context)

        # Add required_labels and hierarchy_info for INTERACTIVE_DIAGRAM even in fallback
        if template_type == "INTERACTIVE_DIAGRAM":
            if required_labels:
                fallback["required_labels"] = required_labels
            if hierarchy_info:
                fallback["hierarchy_info"] = hierarchy_info

            # NOTE: Interaction mode configuration now comes from interaction_designer agent
            # Use interaction_design from state if available for fallback too
            # Use 'or {}' pattern because state.get returns None if key exists with None value
            interaction_design = state.get("interaction_design") or {}
            if interaction_design:
                fallback["recommended_mode"] = interaction_design.get("primary_interaction_mode") or ""
                fallback["secondary_mode"] = interaction_design.get("secondary_modes", [None])[0] if interaction_design.get("secondary_modes") else None
                fallback["interaction_features"] = interaction_design.get("multi_mode_config", {})

        return {
            **state,
            "game_plan": fallback,
            "scene_breakdown": fallback.get("scene_breakdown", []),
            "needs_multi_scene": False,  # Fallback doesn't support multi-scene
            "current_agent": "game_planner",
            "error_message": f"GamePlanner fallback: {str(e)}"
        }


def _collapse_same_image_scenes(scene_breakdown: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Auto-collapse multiple scenes into one scene with tasks when they would
    share the same image. This is a safety net for LLMs that create separate
    scenes for what should be tasks within one scene.

    Conditions for collapsing:
    1. No scene has explicit different asset_needs.primary.query values
    2. Scenes have no tasks yet (already task-aware scenes are left alone)
    3. All scenes share the same base topic (same image)
    """
    if len(scene_breakdown) <= 1:
        return scene_breakdown

    # If any scene already has tasks, the LLM got it right — skip collapse
    if any(scene.get("tasks") for scene in scene_breakdown):
        return scene_breakdown

    # Extract asset queries from each scene
    asset_queries = []
    for scene in scene_breakdown:
        asset_needs = scene.get("asset_needs", {})
        if isinstance(asset_needs, dict):
            primary = asset_needs.get("primary", {})
            query = primary.get("query", "") if isinstance(primary, dict) else ""
        else:
            query = ""
        asset_queries.append(query.lower().strip())

    # Check if all queries are the same (or empty)
    unique_queries = set(q for q in asset_queries if q)
    if len(unique_queries) > 1:
        # Different images needed — keep separate scenes
        return scene_breakdown

    # All scenes share the same image — collapse into one scene with tasks
    merged_scene = {**scene_breakdown[0]}
    merged_tasks = []

    for scene in scene_breakdown:
        task = {
            "task_id": f"task_{scene.get('scene_number', len(merged_tasks) + 1)}",
            "title": scene.get("title", f"Task {len(merged_tasks) + 1}"),
            "description": scene.get("description"),
            "mechanic": scene.get("interaction_mode") or "",
            "focus_labels": scene.get("focus_labels", []),
            "scoring_weight": 1.0,
            "config": {},
        }
        # If scene has secondary_modes, use the first mechanic
        if scene.get("mechanics"):
            first_mech = scene["mechanics"][0]
            if isinstance(first_mech, dict):
                task["mechanic"] = first_mech.get("type") or ""
        merged_tasks.append(task)

    merged_scene["tasks"] = merged_tasks
    # Collect all focus_labels across all collapsed scenes
    all_focus_labels = []
    for scene in scene_breakdown:
        all_focus_labels.extend(scene.get("focus_labels", []))
    merged_scene["focus_labels"] = all_focus_labels
    merged_scene["scene_number"] = 1
    merged_scene["description"] = merged_scene.get("description", "")

    # Merge mechanics from all scenes (deduplicated)
    seen_mechanics = set()
    merged_mechanics = []
    for scene in scene_breakdown:
        im = scene.get("interaction_mode") or ""
        if im not in seen_mechanics:
            seen_mechanics.add(im)
            merged_mechanics.append({"type": im})
        for sm in scene.get("secondary_modes", []):
            if sm not in seen_mechanics:
                seen_mechanics.add(sm)
                merged_mechanics.append({"type": sm})
    if merged_mechanics:
        merged_scene["mechanics"] = merged_mechanics
        merged_scene["interaction_mode"] = merged_mechanics[0].get("type") or ""

    logger.info(
        "Collapsed same-image scenes into one scene with tasks",
        original_scene_count=len(scene_breakdown),
        task_count=len(merged_tasks),
        task_titles=[t["title"] for t in merged_tasks]
    )

    return [merged_scene]


def _normalize_game_plan(
    result: Dict[str, Any],
    template_type: str,
    domain_knowledge: Optional[Dict[str, Any]] = None
) -> GamePlan:
    """
    Normalize and validate the LLM game plan result.

    For order/sequence mechanics, populates sequence_items from domain_knowledge
    if not provided by LLM.
    """
    # Guard against None or invalid result
    if result is None or not isinstance(result, dict):
        logger.warning("Invalid result from LLM, using empty dict", result_type=type(result).__name__)
        result = {}

    # Ensure required fields
    learning_objectives = result.get("learning_objectives", [])
    if not learning_objectives:
        learning_objectives = ["Complete the interactive learning activity"]

    # Get sequence data from domain_knowledge if available
    sequence_flow_data = None
    if domain_knowledge:
        sequence_flow_data = domain_knowledge.get("sequence_flow_data")

    # Normalize game mechanics
    game_mechanics = []
    for m in result.get("game_mechanics", []):
        if isinstance(m, dict):
            mechanic = {
                "id": m.get("id", f"mechanic_{len(game_mechanics)}"),
                "type": m.get("type", "interact"),
                "description": m.get("description", ""),
                "interaction_type": m.get("interaction_type", "click"),
                "learning_purpose": m.get("learning_purpose", ""),
                "scoring_weight": float(m.get("scoring_weight", 0.5))
            }

            # Phase 0: Handle sequence/order mechanics
            mechanic_type = m.get("type", "").lower()
            if mechanic_type in ("order", "sequence", "ordering"):
                # Use mechanic's sequence_items if provided by LLM
                seq_items = m.get("sequence_items")

                # Fall back to domain_knowledge.sequence_flow_data if LLM didn't include
                if not seq_items and sequence_flow_data:
                    seq_items = sequence_flow_data.get("sequence_items", [])
                    logger.info(
                        "Using sequence data from domain_knowledge for order mechanic",
                        mechanic_id=mechanic["id"],
                        item_count=len(seq_items) if seq_items else 0
                    )

                mechanic["sequence_items"] = seq_items
                mechanic["sequence_type"] = m.get("sequence_type") or \
                    (sequence_flow_data.get("flow_type", "linear") if sequence_flow_data else "linear")

                # Build correct_order from sequence_items
                correct_order = m.get("correct_order")
                if not correct_order and seq_items:
                    correct_order = [
                        item.get("id") for item in sorted(
                            seq_items,
                            key=lambda x: x.get("order_index", 0)
                        )
                    ]
                mechanic["correct_order"] = correct_order

            game_mechanics.append(mechanic)

    if not game_mechanics:
        game_mechanics = [{
            "id": "mechanic_1",
            "type": "interact",
            "description": "Primary interaction",
            "interaction_type": "click",
            "learning_purpose": "Engage with content",
            "scoring_weight": 1.0
        }]

    # Normalize difficulty progression
    difficulty_progression = result.get("difficulty_progression", {})
    if not isinstance(difficulty_progression, dict):
        difficulty_progression = {}

    # Normalize feedback strategy
    feedback_strategy = result.get("feedback_strategy", {})
    if not isinstance(feedback_strategy, dict):
        feedback_strategy = {
            "immediate_feedback": True,
            "feedback_on_correct": "Correct! Great job!",
            "feedback_on_incorrect": "Not quite. Try again.",
            "misconception_targeting": []
        }

    # Normalize scoring rubric
    scoring_rubric = result.get("scoring_rubric", {})
    if not isinstance(scoring_rubric, dict):
        scoring_rubric = {}

    # Normalize scene_breakdown for multi-scene games
    scene_breakdown = result.get("scene_breakdown", [])
    if scene_breakdown and isinstance(scene_breakdown, list):
        normalized_scenes = []
        for scene in scene_breakdown:
            if isinstance(scene, dict):
                # Normalize tasks within scene
                raw_tasks = scene.get("tasks", [])
                normalized_tasks = []
                for task in raw_tasks:
                    if isinstance(task, dict):
                        normalized_tasks.append({
                            "task_id": task.get("task_id", f"task_{len(normalized_tasks) + 1}"),
                            "title": task.get("title", ""),
                            "description": task.get("description"),
                            "mechanic": task.get("mechanic") or "",
                            "focus_labels": task.get("focus_labels", []),
                            "scoring_weight": float(task.get("scoring_weight", 1.0)),
                            "config": task.get("config", {}),
                        })

                normalized_scenes.append({
                    "scene_number": int(scene.get("scene_number", len(normalized_scenes) + 1)),
                    "title": scene.get("title", f"Scene {len(normalized_scenes) + 1}"),
                    "topic": scene.get("topic", ""),
                    "focus_labels": scene.get("focus_labels", []),
                    "description": scene.get("description", ""),
                    # Multi-mechanic support: preserve interaction_mode and secondary_modes per scene
                    "interaction_mode": scene.get("interaction_mode") or "",
                    "secondary_modes": scene.get("secondary_modes", []),
                    # Preserve mechanics and asset_needs for workflow routing
                    "mechanics": scene.get("mechanics", []),
                    "asset_needs": scene.get("asset_needs", {}),
                    # Tasks within scene
                    "tasks": normalized_tasks,
                })
        scene_breakdown = normalized_scenes

        # Auto-collapse: merge scenes that share the same image into one scene with tasks
        scene_breakdown = _collapse_same_image_scenes(scene_breakdown)

    return {
        "learning_objectives": learning_objectives,
        "game_mechanics": game_mechanics,
        "difficulty_progression": difficulty_progression,
        "feedback_strategy": feedback_strategy,
        "scoring_rubric": {
            "max_score": int(scoring_rubric.get("max_score", 100)),
            "partial_credit": bool(scoring_rubric.get("partial_credit", True)),
            "time_bonus": bool(scoring_rubric.get("time_bonus", False)),
            "hint_penalty": float(scoring_rubric.get("hint_penalty", 0.1)),
            "criteria": scoring_rubric.get("criteria", [])
        },
        "estimated_duration_minutes": int(result.get("estimated_duration_minutes", 10)),
        "prerequisite_skills": result.get("prerequisite_skills", []),
        # Phase 4: Multi-scene support
        "scene_breakdown": scene_breakdown,
    }


def _create_fallback_game_plan(
    template_type: str,
    ped_context: Dict[str, Any]
) -> GamePlan:
    """Create a fallback game plan when LLM fails"""

    template_info = TEMPLATE_MECHANICS.get(template_type, {})
    blooms = ped_context.get("blooms_level", "understand")

    # Map Bloom's level to game complexity
    complexity_map = {
        "remember": {"mechanics": 1, "duration": 5},
        "understand": {"mechanics": 2, "duration": 8},
        "apply": {"mechanics": 3, "duration": 10},
        "analyze": {"mechanics": 3, "duration": 12},
        "evaluate": {"mechanics": 4, "duration": 15},
        "create": {"mechanics": 4, "duration": 20}
    }

    complexity = complexity_map.get(blooms, complexity_map["understand"])

    # Generate basic mechanics based on template
    mechanics = []
    suggested = template_info.get("suggested_mechanics", ["interact"])[:complexity["mechanics"]]

    for i, mech_type in enumerate(suggested):
        mechanics.append({
            "id": f"mechanic_{i + 1}",
            "type": mech_type,
            "description": f"{mech_type.replace('_', ' ').title()} interaction",
            "interaction_type": template_info.get("interaction_types", ["click"])[0],
            "learning_purpose": "Reinforce learning",
            "scoring_weight": 1.0 / len(suggested)
        })

    return {
        "learning_objectives": ped_context.get("learning_objectives", [
            f"Demonstrate understanding of the concept at {blooms} level"
        ]),
        "game_mechanics": mechanics,
        "difficulty_progression": {
            "initial_state": "Start with guided introduction",
            "progression_rules": ["Increase complexity after correct answers"],
            "hints_available": True,
            "max_attempts": 3
        },
        "feedback_strategy": {
            "immediate_feedback": True,
            "feedback_on_correct": "Well done! You've got it!",
            "feedback_on_incorrect": "Not quite right. Here's a hint...",
            "misconception_targeting": []
        },
        "scoring_rubric": {
            "max_score": 100,
            "partial_credit": True,
            "time_bonus": False,
            "hint_penalty": 0.1,
            "criteria": [
                {
                    "name": "Correctness",
                    "weight": 0.7,
                    "levels": [
                        {"score": 0, "description": "Incorrect"},
                        {"score": 0.5, "description": "Partially correct"},
                        {"score": 1.0, "description": "Fully correct"}
                    ]
                },
                {
                    "name": "Efficiency",
                    "weight": 0.3,
                    "levels": [
                        {"score": 0, "description": "Many attempts"},
                        {"score": 0.5, "description": "Some attempts"},
                        {"score": 1.0, "description": "First try"}
                    ]
                }
            ]
        },
        "estimated_duration_minutes": complexity["duration"],
        "prerequisite_skills": ped_context.get("prerequisites", [])
    }


# Validator for game plans
async def validate_game_plan(plan: GamePlan) -> Dict[str, Any]:
    """
    Validate the game plan.

    Returns:
        Dict with 'valid' bool and 'errors' list
    """
    errors = []

    # Required fields
    if not plan.get("learning_objectives"):
        errors.append("Missing learning objectives")

    if not plan.get("game_mechanics"):
        errors.append("Missing game mechanics")

    # Validate mechanics have required fields
    for i, m in enumerate(plan.get("game_mechanics", [])):
        if not m.get("id"):
            errors.append(f"Mechanic {i} missing id")
        if not m.get("type"):
            errors.append(f"Mechanic {i} missing type")

    # Validate scoring rubric
    rubric = plan.get("scoring_rubric", {})
    if rubric.get("max_score", 0) <= 0:
        errors.append("Invalid max_score in rubric")

    # Validate weights sum to ~1.0
    mechanics = plan.get("game_mechanics", [])
    if mechanics:
        total_weight = sum(m.get("scoring_weight", 0) for m in mechanics)
        if abs(total_weight - 1.0) > 0.1:
            errors.append(f"Mechanic weights sum to {total_weight}, should be ~1.0")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "plan": plan
    }


# =============================================================================
# PRESET 2: Game Design -> Game Plan Conversion
# =============================================================================

def _convert_game_design_to_plan(game_design: Dict[str, Any], state: AgentState) -> GamePlan:
    """
    Convert game_designer output to GamePlan format.

    This function bridges the new agentic game_designer output with the
    existing GamePlan schema expected by downstream agents.

    Args:
        game_design: Output from game_designer agent
        state: Current agent state for context

    Returns:
        GamePlan compatible dictionary
    """
    # Extract learning outcomes
    learning_objectives = game_design.get("learning_outcomes", [])
    if not learning_objectives:
        learning_objectives = ["Complete the interactive learning activity"]

    # Convert scenes to game mechanics
    scenes = game_design.get("scenes", [])
    game_mechanics = []

    for scene in scenes:
        mechanic = {
            "id": f"scene_{scene.get('scene', len(game_mechanics) + 1)}",
            "type": scene.get("pattern") or "",
            "description": scene.get("purpose", "Interactive activity"),
            "interaction_type": scene.get("pattern") or "",
            "learning_purpose": scene.get("purpose", ""),
            "scoring_weight": float(scene.get("scoring_weight", 1.0 / max(len(scenes), 1)))
        }
        game_mechanics.append(mechanic)

    # If no mechanics, leave empty (let downstream agents decide)
    if not game_mechanics:
        game_mechanics = []

    # Determine recommended mode from first scene pattern
    recommended_mode = (scenes[0].get("pattern") or "") if scenes else ""

    # Map scene_structure to game plan format
    scene_structure = game_design.get("scene_structure", "single")

    # Get pedagogical context for additional info
    ped_context = state.get("pedagogical_context", {})

    game_plan: GamePlan = {
        "learning_objectives": learning_objectives,
        "game_mechanics": game_mechanics,
        "difficulty_progression": {
            "initial_state": "Start with first scene",
            "progression_rules": [
                f"Progress through {len(scenes)} scene(s) in {scene_structure} order"
            ],
            "hints_available": True,
            "max_attempts": 3
        },
        "feedback_strategy": {
            "immediate_feedback": True,
            "feedback_on_correct": "Great work! Continue to the next part.",
            "feedback_on_incorrect": "Not quite. Take another look.",
            "misconception_targeting": []
        },
        "scoring_rubric": {
            "max_score": 100,
            "partial_credit": True,
            "time_bonus": False,
            "hint_penalty": 0.1,
            "criteria": [
                {
                    "name": "Accuracy",
                    "weight": 0.7,
                    "levels": [
                        {"score": 0, "description": "Incorrect"},
                        {"score": 0.5, "description": "Partially correct"},
                        {"score": 1.0, "description": "Fully correct"}
                    ]
                },
                {
                    "name": "Completion",
                    "weight": 0.3,
                    "levels": [
                        {"score": 0, "description": "Incomplete"},
                        {"score": 0.5, "description": "Mostly complete"},
                        {"score": 1.0, "description": "Fully complete"}
                    ]
                }
            ]
        },
        "estimated_duration_minutes": max(5, len(scenes) * 4),
        "prerequisite_skills": ped_context.get("prerequisites", []),
        # Preset 2 specific fields
        "recommended_mode": recommended_mode,
        "scene_structure": scene_structure,
        "game_design": game_design,  # Preserve original for downstream use
        "design_reasoning": game_design.get("reasoning", "")
    }

    return game_plan
