"""
Story Generator Agent

Creates engaging educational narratives that wrap around game mechanics.
Generates story context, characters, visual metaphors, and question flow.

Key Features:
- Narrative hooks that engage learners
- Visual metaphors that reinforce concepts
- Character-driven learning journeys
- Question flow integrated with story progression
"""

import json

from app.utils.logging_config import get_logger
from typing import Dict, Any, List, Optional

from app.agents.state import AgentState, StoryData
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.agents.schemas.stages import get_story_data_schema
from app.config.pedagogical_constants import BLOOM_LEVELS, DIFFICULTY_LEVEL

logger = get_logger("gamed_ai.agents.story_generator")


STORY_GENERATOR_PROMPT = """You are an expert educational storyteller. Create an engaging narrative that makes learning feel like an adventure.

## Question to Teach:
{question_text}

## Answer Options:
{question_options}

## Pedagogical Context:
- Bloom's Level: {blooms_level}
- Subject: {subject}
- Difficulty: {difficulty}
- Learning Objectives: {learning_objectives}
- Key Concepts: {key_concepts}

## Game Template: {template_type}
## Game Mechanics: {game_mechanics}

## Few-Shot Example: STATE_TRACER_CODE for Binary Search

**Question**: "Explain how binary search works on a sorted array. Demonstrate the algorithm finding the number 7 in the array [1, 3, 5, 7, 9, 11, 13]."

**Story**:
```json
{{
    "story_title": "The Binary Search Detective",
    "story_context": "You're a code detective debugging a search algorithm that's not working correctly. The suspect number 7 is hiding somewhere in the sorted array [1, 3, 5, 7, 9, 11, 13]. Your mission: trace through the binary search code step-by-step to find where 7 is located. Each line of code is a clue, and each variable update brings you closer to solving the mystery.",
    "visual_metaphor": "A detective's investigation board with array elements as suspects, search pointers as magnifying glasses, and comparisons as interrogation sessions",
    "narrative_hook": "The search algorithm is broken, and you're the only one who can fix it. But first, you need to understand exactly how it works by tracing every step.",
    "character_name": "Detective Trace",
    "character_role": "A code detective who guides learners through the investigation, explaining each step and why it matters",
    "setting_description": "A dimly lit detective's office with a large evidence board showing the sorted array. Each element glows when examined. A magnifying glass follows the search pointers (low, high, mid).",
    "question_flow": [
        {{
            "step": 1,
            "narrative_text": "The investigation begins. You initialize your search boundaries: low = 0 (start of array) and high = 6 (end of array). The array [1, 3, 5, 7, 9, 11, 13] is your suspect list, and 7 is your target.",
            "challenge_context": "First, you need to calculate the midpoint. What will be the value of mid?",
            "success_narrative": "Perfect! You calculated mid = 3. Now examine the suspect at index 3...",
            "failure_narrative": "Not quite. Remember: mid = (low + high) // 2. Integer division rounds down, so (0 + 6) // 2 = 3.",
            "hint_narrative": "Think of it like finding the middle page in a book: add the first and last page numbers, then divide by 2 (rounding down)."
        }},
        {{
            "step": 2,
            "narrative_text": "You examine arr[3] = 7. It matches your target! But wait... let's trace through what happens if it didn't match, to understand the full algorithm.",
            "challenge_context": "If arr[mid] = 5 (less than target 7), which half of the array would you search next?",
            "success_narrative": "Exactly! Since 5 < 7, and the array is sorted, 7 must be in the RIGHT half (larger indices). You update low = mid + 1.",
            "failure_narrative": "Think about sorted order: smaller numbers are on the left, larger on the right. If arr[mid] < target, where would the target be?",
            "hint_narrative": "In a sorted array, if the middle element is smaller than your target, the target must be to the RIGHT (higher indices)."
        }},
        {{
            "step": 3,
            "narrative_text": "You continue the search, halving the search space with each comparison. This is the power of binary search - each step eliminates half the suspects!",
            "challenge_context": "How many times will the while loop execute before finding 7 in this array?",
            "success_narrative": "Brilliant! You understand that binary search has O(log n) efficiency. With 7 elements, it takes at most 3 comparisons.",
            "failure_narrative": "Remember: binary search halves the search space each time. With 7 elements, think about how many times you can halve before reaching 1 element.",
            "hint_narrative": "Each comparison eliminates half the remaining elements. 7 → 3 → 1. That's about 3 steps (log2(7) ≈ 2.8)."
        }}
    ],
    "conclusion_text": "Case closed! You've successfully traced the binary search algorithm and found that 7 is at index 3. You've learned that binary search is incredibly efficient - it can find any element in a sorted array of 1 million items in just 20 comparisons! The key insight: each comparison eliminates half the remaining possibilities.",
    "visual_elements": [
        {{
            "element": "Evidence Board",
            "description": "Large board showing the array with indices, elements glow when examined",
            "purpose": "Visual representation of the data structure being searched"
        }},
        {{
            "element": "Magnifying Glass",
            "description": "Follows the mid pointer, highlights current element being compared",
            "purpose": "Draws attention to the current comparison operation"
        }},
        {{
            "element": "Search Boundaries",
            "description": "Low and high pointers as colored markers that move as search progresses",
            "purpose": "Shows how the search space shrinks with each iteration"
        }},
        {{
            "element": "Variable Tracker",
            "description": "Side panel showing current values of low, high, mid, and arr[mid]",
            "purpose": "Helps learners track state changes throughout execution"
        }}
    ],
    "audio_cues": {{
        "background": "Mysterious detective theme with subtle typing sounds",
        "success": "Satisfying 'click' sound when correct, like a case file being closed",
        "failure": "Gentle 'buzz' sound, like a wrong lead in an investigation"
    }}
}}
```

## Story Requirements:
1. **Engaging Hook**: Start with a scenario that makes learners curious
2. **Relatable Context**: Use real-world or fantasy scenarios appropriate for the subject
3. **Visual Metaphor**: Create a visual representation of abstract concepts
4. **Character Guide**: Include a mentor/guide character if appropriate
5. **Progressive Disclosure**: Reveal information as the learner progresses
6. **Meaningful Conclusion**: End with reinforcement of what was learned

## Response Format (JSON):
{{
    "story_title": "<catchy, descriptive title>",
    "story_context": "<2-3 sentences setting the scene>",
    "visual_metaphor": "<the central visual/conceptual metaphor>",
    "narrative_hook": "<opening hook that creates curiosity>",
    "character_name": "<guide character name, or null>",
    "character_role": "<what the character does in the story>",
    "setting_description": "<detailed setting for visual design>",
    "question_flow": [
        {{
            "step": 1,
            "narrative_text": "<story text for this step>",
            "challenge_context": "<how this connects to the question>",
            "success_narrative": "<what happens on correct answer>",
            "failure_narrative": "<what happens on incorrect answer>",
            "hint_narrative": "<optional hint in story form>"
        }}
    ],
    "conclusion_text": "<wrap-up narrative reinforcing learning>",
    "visual_elements": [
        {{
            "element": "<element name>",
            "description": "<visual description>",
            "purpose": "<how it supports learning>"
        }}
    ],
    "audio_cues": {{
        "background": "<suggested ambient audio>",
        "success": "<success sound description>",
        "failure": "<failure sound description>"
    }}
}}

Create a story that makes learning this concept memorable and fun. Respond with ONLY valid JSON."""


# Subject-specific story themes
SUBJECT_THEMES = {
    "Computer Science": {
        "settings": ["futuristic lab", "virtual reality world", "robot workshop", "hacker's den"],
        "characters": ["AI assistant", "robot mentor", "code wizard", "debugging detective"],
        "metaphors": ["building blocks", "puzzle pieces", "circuit paths", "data streams"]
    },
    "Mathematics": {
        "settings": ["ancient library", "number kingdom", "geometry garden", "puzzle palace"],
        "characters": ["math magician", "number knight", "shape shifter", "equation explorer"],
        "metaphors": ["building structures", "balancing scales", "treasure maps", "crystal formations"]
    },
    "Biology": {
        "settings": ["microscopic world", "rainforest expedition", "underwater lab", "body adventure"],
        "characters": ["Dr. Cell", "Nature guide", "Evolution explorer", "Genome detective"],
        "metaphors": ["living cities", "family trees", "factory systems", "ecosystem webs"]
    },
    "Chemistry": {
        "settings": ["alchemist's lab", "molecular realm", "reaction chamber", "element world"],
        "characters": ["Professor Atom", "Bond builder", "Reaction master", "Element guardian"],
        "metaphors": ["building with atoms", "dance of electrons", "recipe mixing", "transformation magic"]
    },
    "Physics": {
        "settings": ["space station", "time laboratory", "force field arena", "wave pool"],
        "characters": ["Professor Force", "Energy engineer", "Motion master", "Quantum guide"],
        "metaphors": ["cosmic dance", "invisible forces", "wave riders", "energy flows"]
    },
    "History": {
        "settings": ["time machine", "ancient civilization", "historical museum", "memory archive"],
        "characters": ["Time traveler", "History detective", "Chronicle keeper", "Era guide"],
        "metaphors": ["timeline rivers", "cause-effect chains", "history puzzles", "legacy bridges"]
    }
}


async def story_generator_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> dict:
    """
    Story Generator Agent

    Creates an engaging educational narrative based on the question,
    pedagogical context, and game mechanics.

    Args:
        state: Current agent state with game_plan and pedagogical_context
        ctx: Optional instrumentation context for metrics tracking

    Returns:
        Updated state with story_data populated
    """
    logger.info(f"StoryGenerator: Creating narrative for question {state.get('question_id', 'unknown')}")

    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])
    ped_context = state.get("pedagogical_context", {})
    template_selection = state.get("template_selection", {})
    game_plan = state.get("game_plan", {})

    template_type = template_selection.get("template_type", "PARAMETER_PLAYGROUND")
    subject = ped_context.get("subject", "General")

    # Build prompt
    options_str = "\n".join(f"- {opt}" for opt in question_options) if question_options else "None"

    prompt = STORY_GENERATOR_PROMPT.format(
        question_text=question_text,
        question_options=options_str,
        blooms_level=ped_context.get("blooms_level", "understand"),
        subject=subject,
        difficulty=DIFFICULTY_LEVEL,
        learning_objectives=json.dumps(ped_context.get("learning_objectives", [])),
        key_concepts=json.dumps(ped_context.get("key_concepts", [])),
        template_type=template_type,
        game_mechanics=json.dumps(game_plan.get("game_mechanics", []))
    )

    try:
        llm = get_llm_service()
        # Use agent-specific model configuration (plug-and-play)
        result = await llm.generate_json_for_agent(
            agent_name="story_generator",
            prompt=prompt,
            schema_hint="StoryData JSON with story_title, story_context, narrative_hook, characters",
            json_schema=get_story_data_schema()
        )

        # Normalize and validate result
        story_data = _normalize_story_data(result, subject)

        logger.info(
            f"StoryGenerator: Created story '{story_data['story_title']}' "
            f"with {len(story_data['question_flow'])} steps"
        )

        return {
            **state,
            "story_data": story_data,
            "current_agent": "story_generator"
        }

    except Exception as e:
        logger.error(f"StoryGenerator: LLM call failed: {e}", exc_info=True)

        # Create fallback story
        fallback = _create_fallback_story(question_text, subject, template_type)

        return {
            **state,
            "story_data": fallback,
            "current_agent": "story_generator",
            "error_message": f"StoryGenerator fallback: {str(e)}"
        }


def _normalize_story_data(result: Dict[str, Any], subject: str) -> StoryData:
    """Normalize and validate the LLM story result"""

    # Get subject-specific fallbacks
    theme = SUBJECT_THEMES.get(subject, SUBJECT_THEMES.get("Computer Science"))

    # Normalize question flow
    question_flow = []
    for i, step in enumerate(result.get("question_flow", [])):
        if isinstance(step, dict):
            question_flow.append({
                "step": step.get("step", i + 1),
                "narrative_text": step.get("narrative_text", ""),
                "challenge_context": step.get("challenge_context", ""),
                "success_narrative": step.get("success_narrative", "Excellent work!"),
                "failure_narrative": step.get("failure_narrative", "Let's try again."),
                "hint_narrative": step.get("hint_narrative", "")
            })

    if not question_flow:
        question_flow = [{
            "step": 1,
            "narrative_text": result.get("story_context", "Begin your learning journey."),
            "challenge_context": "Complete the challenge to proceed.",
            "success_narrative": "Well done! You've mastered this concept.",
            "failure_narrative": "Not quite right. Review and try again.",
            "hint_narrative": "Think about what you've learned."
        }]

    # Normalize visual elements
    visual_elements = []
    for elem in result.get("visual_elements", []):
        if isinstance(elem, dict):
            visual_elements.append({
                "element": elem.get("element", ""),
                "description": elem.get("description", ""),
                "purpose": elem.get("purpose", "")
            })

    return {
        "story_title": result.get("story_title", f"Learning Adventure: {subject}"),
        "story_context": result.get("story_context", "Embark on an educational journey."),
        "visual_metaphor": result.get("visual_metaphor", theme["metaphors"][0] if theme else "exploration"),
        "narrative_hook": result.get("narrative_hook", "Are you ready to discover something amazing?"),
        "character_name": result.get("character_name"),
        "character_role": result.get("character_role", "Your guide on this journey"),
        "setting_description": result.get("setting_description", theme["settings"][0] if theme else "learning environment"),
        "question_flow": question_flow,
        "conclusion_text": result.get("conclusion_text", "Congratulations! You've completed this learning adventure."),
        "visual_elements": visual_elements,
        "audio_cues": result.get("audio_cues", {
            "background": "ambient learning music",
            "success": "triumphant chime",
            "failure": "gentle reminder tone"
        })
    }


def _create_fallback_story(
    question_text: str,
    subject: str,
    template_type: str
) -> StoryData:
    """Create a fallback story when LLM fails"""

    theme = SUBJECT_THEMES.get(subject, {
        "settings": ["learning environment"],
        "characters": ["Guide"],
        "metaphors": ["exploration"]
    })

    # Generate basic story elements
    setting = theme["settings"][0]
    character = theme["characters"][0]
    metaphor = theme["metaphors"][0]

    # Template-specific story framing
    template_frames = {
        "PARAMETER_PLAYGROUND": "experiment and discover",
        "SEQUENCE_BUILDER": "arrange and organize",
        "BUCKET_SORT": "categorize and sort",
        "INTERACTIVE_DIAGRAM": "identify and label",
        "TIMELINE_ORDER": "sequence through time",
        "MATCH_PAIRS": "connect and match",
        "STATE_TRACER_CODE": "trace and debug"
    }

    action_frame = template_frames.get(template_type, "explore and learn")

    return {
        "story_title": f"The {subject} Challenge",
        "story_context": f"Welcome to the {setting}! Today you'll {action_frame} to master an important concept.",
        "visual_metaphor": metaphor,
        "narrative_hook": f"Something puzzling has happened, and only you can solve it!",
        "character_name": character,
        "character_role": "Your mentor and guide",
        "setting_description": f"A {setting} filled with interactive elements and discovery opportunities.",
        "question_flow": [
            {
                "step": 1,
                "narrative_text": f"{character} presents you with a challenge: {question_text[:100]}...",
                "challenge_context": "Apply what you know to solve this puzzle.",
                "success_narrative": f"Brilliant! {character} nods approvingly. You've understood the concept!",
                "failure_narrative": f"{character} encourages you: 'Almost there! Think about it differently.'",
                "hint_narrative": f"{character} offers a hint: 'Consider the key relationships here.'"
            }
        ],
        "conclusion_text": f"Outstanding work! {character} congratulates you on mastering this {subject} concept. Your knowledge has grown!",
        "visual_elements": [
            {
                "element": "Main Challenge Area",
                "description": f"An interactive {setting} where the main activity takes place",
                "purpose": "Focus attention on the learning task"
            },
            {
                "element": "Progress Indicator",
                "description": "Visual representation of journey progress",
                "purpose": "Motivate completion"
            }
        ],
        "audio_cues": {
            "background": f"ambient {subject.lower()} themed music",
            "success": "celebratory chime",
            "failure": "gentle nudge sound"
        }
    }


# Validator for story data
async def validate_story_data(story: StoryData) -> Dict[str, Any]:
    """
    Validate the story data.

    Returns:
        Dict with 'valid' bool and 'errors' list
    """
    errors = []
    warnings = []

    # Required fields
    if not story.get("story_title"):
        errors.append("Missing story title")

    if not story.get("story_context"):
        errors.append("Missing story context")

    if not story.get("question_flow"):
        errors.append("Missing question flow")

    # Check question flow quality
    question_flow = story.get("question_flow", [])
    if question_flow:
        for i, step in enumerate(question_flow):
            if not step.get("narrative_text"):
                warnings.append(f"Step {i + 1} missing narrative text")
            if not step.get("success_narrative"):
                warnings.append(f"Step {i + 1} missing success narrative")

    # Check for visual metaphor
    if not story.get("visual_metaphor"):
        warnings.append("Missing visual metaphor - story may lack conceptual grounding")

    # Check narrative length
    context = story.get("story_context", "")
    if len(context) < 20:
        warnings.append("Story context is very short")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "story": story
    }
