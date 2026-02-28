"""
Router Agent

Selects the optimal game template for a question based on:
- Pedagogical context (Bloom's level, learning objectives)
- Question characteristics
- Template capabilities

Returns a template selection with confidence score.
Low confidence triggers human review.
"""

import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.agents.state import AgentState, TemplateSelection, PedagogicalContext
from app.agents.instrumentation import InstrumentedAgentContext
from app.services.llm_service import get_llm_service
from app.agents.schemas.stages import get_template_selection_schema
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.router")


# Template registry with metadata for routing decisions
TEMPLATE_REGISTRY = {
    "PARAMETER_PLAYGROUND": {
        "description": "Interactive playground to adjust parameters and see results in real-time",
        "best_for": [
            "Mathematical function exploration with sliders",
            "Scientific simulations with adjustable variables",
            "Understanding cause-and-effect relationships",
            "Physics equations with variable inputs",
            "Financial calculations with adjustable rates"
        ],
        "blooms_alignment": ["understand", "apply", "analyze"],
        "domains": ["mathematics", "physics", "simulations", "finance"],
        "interaction_type": "parameter_adjustment",
        "complexity": "medium",
        "production_ready": True
    },
    "SEQUENCE_BUILDER": {
        "description": "Drag-and-drop interface to arrange steps in correct order",
        "best_for": [
            "Algorithm steps ordering (without code tracing)",
            "Process sequencing and workflow ordering",
            "Historical event chronological ordering",
            "Scientific method steps arrangement",
            "Recipe or procedure step ordering",
            "Software development lifecycle steps"
        ],
        "blooms_alignment": ["understand", "apply", "analyze"],
        "domains": ["programming", "science", "history", "processes"],
        "interaction_type": "drag_and_drop",
        "complexity": "medium",
        "production_ready": True
    },
    "BUCKET_SORT": {
        "description": "Categorize items by dragging them into appropriate buckets",
        "best_for": [
            "Classification tasks",
            "Categorization exercises",
            "Grouping by properties",
            "Taxonomy identification",
            "Sorting elements by characteristics"
        ],
        "blooms_alignment": ["understand", "apply"],
        "domains": ["science", "mathematics", "classification"],
        "interaction_type": "drag_and_drop",
        "complexity": "low",
        "production_ready": True
    },
    "INTERACTIVE_DIAGRAM": {
        "description": "Label parts of a diagram by dragging labels to correct positions",
        "best_for": [
            "Anatomy labeling",
            "System component identification",
            "Diagram annotation",
            "Part identification",
            "Geography identification (continents, countries)",
            "Technical diagrams (circuits, engines)"
        ],
        "blooms_alignment": ["remember", "understand"],
        "domains": ["biology", "anatomy", "engineering", "science", "geography"],
        "interaction_type": "drag_and_drop",
        "complexity": "low",
        "production_ready": True
    },
    "IMAGE_HOTSPOT_QA": {
        "description": "Click on regions of an image to answer questions about them",
        "best_for": [
            "Geographic map questions",
            "Artwork analysis",
            "Scientific image interpretation",
            "Locating specific features"
        ],
        "blooms_alignment": ["remember", "understand", "analyze"],
        "domains": ["geography", "art", "science", "history"],
        "interaction_type": "click",
        "complexity": "medium",
        "production_ready": False
    },
    "TIMELINE_ORDER": {
        "description": "Place events on a timeline in chronological order",
        "best_for": [
            "Historical event sequencing",
            "Process timeline creation",
            "Chronological ordering",
            "Time-based sequences"
        ],
        "blooms_alignment": ["remember", "understand"],
        "domains": ["history", "science", "biography"],
        "interaction_type": "drag_and_drop",
        "complexity": "medium",
        "production_ready": False
    },
    "MATCH_PAIRS": {
        "description": "Match related items from two columns",
        "best_for": [
            "Vocabulary matching",
            "Concept-definition pairing",
            "Symbol-meaning matching",
            "Cause-effect matching"
        ],
        "blooms_alignment": ["remember", "understand"],
        "domains": ["language", "science", "general"],
        "interaction_type": "drag_and_drop",
        "complexity": "low",
        "production_ready": False
    },
    "MATRIX_MATCH": {
        "description": "Fill in a matrix by matching row and column items",
        "best_for": [
            "Multi-dimensional classification",
            "Relationship matrices",
            "Truth tables",
            "Cross-reference tasks"
        ],
        "blooms_alignment": ["understand", "analyze"],
        "domains": ["logic", "mathematics", "science"],
        "interaction_type": "click",
        "complexity": "high",
        "production_ready": False
    },
    "GRAPH_SKETCHER": {
        "description": "Draw or manipulate graphs and nodes",
        "best_for": [
            "Graph theory visualization",
            "Network building",
            "State machine design",
            "Tree structures"
        ],
        "blooms_alignment": ["apply", "create"],
        "domains": ["computer science", "mathematics", "networks"],
        "interaction_type": "draw",
        "complexity": "high",
        "production_ready": False
    },
    "VECTOR_SANDBOX": {
        "description": "Manipulate vectors in 2D/3D space",
        "best_for": [
            "Vector addition and subtraction",
            "Force diagrams",
            "Physics simulations",
            "Linear algebra concepts"
        ],
        "blooms_alignment": ["apply", "analyze"],
        "domains": ["physics", "mathematics", "engineering"],
        "interaction_type": "manipulation",
        "complexity": "high",
        "production_ready": False
    },
    "STATE_TRACER_CODE": {
        "description": "Step through code and track variable states line by line",
        "best_for": [
            "Binary search algorithm explanation",
            "Sorting algorithm tracing (bubble, merge, quick)",
            "Search algorithm visualization",
            "Code debugging and execution tracing",
            "Variable state tracking through iterations",
            "Loop and recursion understanding",
            "Algorithm step-by-step execution"
        ],
        "blooms_alignment": ["understand", "apply", "analyze"],
        "domains": ["programming", "computer science", "algorithms"],
        "interaction_type": "step_through",
        "complexity": "high",
        "production_ready": True
    },
    "SPOT_THE_MISTAKE": {
        "description": "Find and correct errors in content",
        "best_for": [
            "Bug finding in code",
            "Error identification",
            "Proofreading exercises",
            "Misconception detection"
        ],
        "blooms_alignment": ["analyze", "evaluate"],
        "domains": ["programming", "language", "mathematics"],
        "interaction_type": "click",
        "complexity": "medium",
        "production_ready": False
    },
    "CONCEPT_MAP_BUILDER": {
        "description": "Build concept maps showing relationships between ideas",
        "best_for": [
            "Relationship mapping",
            "Concept organization",
            "Knowledge synthesis",
            "Hierarchy building"
        ],
        "blooms_alignment": ["analyze", "create"],
        "domains": ["general", "science", "social studies"],
        "interaction_type": "draw",
        "complexity": "high",
        "production_ready": False
    },
    "MICRO_SCENARIO_BRANCHING": {
        "description": "Navigate through decision trees with consequences",
        "best_for": [
            "Decision-making scenarios",
            "Ethical dilemmas",
            "Choose-your-own-adventure learning",
            "Consequence exploration"
        ],
        "blooms_alignment": ["apply", "evaluate"],
        "domains": ["ethics", "social studies", "business"],
        "interaction_type": "choice",
        "complexity": "medium",
        "production_ready": False
    },
    "DESIGN_CONSTRAINT_BUILDER": {
        "description": "Design solutions within given constraints",
        "best_for": [
            "Engineering design challenges",
            "Optimization problems",
            "Resource allocation",
            "Constraint satisfaction"
        ],
        "blooms_alignment": ["apply", "create"],
        "domains": ["engineering", "design", "business"],
        "interaction_type": "build",
        "complexity": "high",
        "production_ready": False
    },
    "PROBABILITY_LAB": {
        "description": "Run probability experiments and observe outcomes",
        "best_for": [
            "Probability exploration",
            "Statistics visualization",
            "Random experiments",
            "Distribution understanding"
        ],
        "blooms_alignment": ["understand", "apply"],
        "domains": ["mathematics", "statistics"],
        "interaction_type": "simulation",
        "complexity": "medium",
        "production_ready": False
    },
    "BEFORE_AFTER_TRANSFORMER": {
        "description": "Show before/after states of transformations",
        "best_for": [
            "Transformation visualization",
            "State changes",
            "Process outcomes",
            "Cause-effect demonstrations"
        ],
        "blooms_alignment": ["understand", "analyze"],
        "domains": ["science", "mathematics", "history"],
        "interaction_type": "comparison",
        "complexity": "medium",
        "production_ready": False
    },
    "GEOMETRY_BUILDER": {
        "description": "Construct geometric shapes and proofs",
        "best_for": [
            "Geometric constructions",
            "Compass and straightedge",
            "Shape properties",
            "Proof building"
        ],
        "blooms_alignment": ["apply", "create"],
        "domains": ["mathematics", "geometry"],
        "interaction_type": "draw",
        "complexity": "high",
        "production_ready": False
    },
    "INTERACTIVE_DIAGRAM": {
        "description": "Rich multi-mechanic interactive diagram game with asset graph, multiple scenes, and diverse interaction modes",
        "best_for": [
            "Complex anatomy labeling with blood flow tracing",
            "Multi-step diagram exploration (label, trace, identify)",
            "Hierarchical progressive reveal with animations",
            "Scientific process visualization with sequencing",
            "Diagram-based games needing sprites, overlays, and audio",
            "Multi-scene games with different mechanics per scene"
        ],
        "blooms_alignment": ["remember", "understand", "apply", "analyze"],
        "domains": ["biology", "anatomy", "engineering", "science", "geography", "chemistry", "physics"],
        "interaction_type": "multi_mechanic",
        "complexity": "high",
        "production_ready": True,
        "requires_specialized_pipeline": True
    },
    "PHET_SIMULATION": {
        "description": "Interactive PhET simulation with embedded assessment tasks and checkpoints",
        "best_for": [
            "Physics simulations (projectile motion, forces, energy)",
            "Chemistry concepts (states of matter, atomic structure, molecules)",
            "Mathematical exploration (graphing, algebra, geometry)",
            "Scientific inquiry and discovery learning",
            "Parameter exploration and cause-effect relationships",
            "Prediction-verification scientific method",
            "Data collection and measurement activities",
            "Circuit building and electrical concepts"
        ],
        "blooms_alignment": ["understand", "apply", "analyze", "evaluate", "create"],
        "domains": ["physics", "chemistry", "mathematics", "science", "biology"],
        "interaction_type": "simulation",
        "complexity": "high",
        "production_ready": True,
        "requires_specialized_pipeline": True
    }
}


ROUTER_PROMPT = """You are an expert educational game designer. Select the optimal game template for the given question and pedagogical context.

## Question:
{question_text}

## Answer Options:
{question_options}

## Pedagogical Context:
- Bloom's Level: {blooms_level}
- Subject: {subject}
- Difficulty: {difficulty}
- Learning Objectives: {learning_objectives}
- Key Concepts: {key_concepts}
- Question Intent: {question_intent}

## Available Templates:

{template_descriptions}

## Selection Criteria:

1. **Bloom's Alignment**: Match the cognitive level required
   - remember/understand → simpler templates (Label, Match, Bucket)
   - apply/analyze → interactive templates (Parameter, Sequence, State Tracer)
   - evaluate/create → complex templates (Design, Concept Map, Scenario)

2. **Subject Fit**: Match template domains to question subject

3. **Interaction Type**: Choose based on what the learner should DO
   - Categorize → BUCKET_SORT
   - Order/sequence → SEQUENCE_BUILDER or TIMELINE_ORDER
   - Explore parameters → PARAMETER_PLAYGROUND
   - Label parts → INTERACTIVE_DIAGRAM (simple) or INTERACTIVE_DIAGRAM (rich multi-mechanic)
   - Complex diagram interaction (label + trace + identify) → INTERACTIVE_DIAGRAM
   - Match items → MATCH_PAIRS
   - Step through code → STATE_TRACER_CODE
   - Make decisions → MICRO_SCENARIO_BRANCHING
   - Physics/chemistry simulation → PHET_SIMULATION
   - Scientific exploration/discovery → PHET_SIMULATION
   - Measurement/data collection → PHET_SIMULATION

4. **Production Readiness**: Prefer production-ready templates when possible

5. **Question Characteristics**:
   - Has multiple discrete items to organize? → BUCKET_SORT, SEQUENCE_BUILDER
   - Has numerical/adjustable parameters? → PARAMETER_PLAYGROUND
   - Has image/diagram component? → INTERACTIVE_DIAGRAM, INTERACTIVE_DIAGRAM, IMAGE_HOTSPOT_QA
   - Complex diagram with multiple interaction types? → INTERACTIVE_DIAGRAM
   - Has timeline/chronology? → TIMELINE_ORDER
   - Has code to trace? → STATE_TRACER_CODE
   - Has pairs to match? → MATCH_PAIRS

## Response Format (JSON):
{{
    "template_type": "<TEMPLATE_NAME>",
    "confidence": <0.0-1.0>,
    "reasoning": "<2-3 sentences explaining the choice>",
    "alternatives": [
        {{
            "template_type": "<ALTERNATIVE_TEMPLATE>",
            "confidence": <0.0-1.0>,
            "why_not_primary": "<brief reason>"
        }}
    ],
    "bloom_alignment_score": <0.0-1.0>,
    "subject_fit_score": <0.0-1.0>,
    "interaction_fit_score": <0.0-1.0>
}}

Respond with ONLY valid JSON."""


def _build_template_descriptions() -> str:
    """Build template descriptions for the prompt"""
    lines = []
    for name, meta in TEMPLATE_REGISTRY.items():
        status = "PRODUCTION READY" if meta.get("production_ready") else "STUB"
        lines.append(f"### {name} [{status}]")
        lines.append(f"Description: {meta['description']}")
        lines.append(f"Best for: {', '.join(meta['best_for'][:3])}")
        lines.append(f"Bloom's: {', '.join(meta['blooms_alignment'])}")
        lines.append(f"Domains: {', '.join(meta['domains'])}")
        lines.append("")
    return "\n".join(lines)


async def router_agent(state: AgentState, ctx: Optional[InstrumentedAgentContext] = None) -> AgentState:
    """
    Router Agent

    Selects the optimal game template based on question and pedagogical context.
    Returns template selection with confidence score.

    Args:
        state: Current agent state with question and pedagogical_context
        ctx: Optional instrumentation context for metrics tracking

    Returns:
        Updated state with template_selection
    """
    logger.info(f"Router: Processing question {state.get('question_id', 'unknown')}")

    question_text = state.get("question_text", "")
    question_options = state.get("question_options", [])
    ped_context = state.get("pedagogical_context", {})

    if not question_text:
        logger.error("Router: No question text")
        return {
            **state,
            "current_agent": "router",
            "error_message": "No question text for routing"
        }

    # Check for forced template (for testing/specialization)
    forced_template = os.getenv("FORCE_TEMPLATE", "").upper()
    if forced_template and forced_template in TEMPLATE_REGISTRY:
        logger.info(f"Router: Using forced template {forced_template} (from FORCE_TEMPLATE env var)")
        template_meta = TEMPLATE_REGISTRY[forced_template]
        template_selection = {
            "template_type": forced_template,
            "confidence": 0.95,  # High confidence for forced selection
            "reasoning": f"Forced template selection for testing: {forced_template}",
            "alternatives": [],
            "bloom_alignment_score": 0.9,
            "subject_fit_score": 0.9,
            "interaction_fit_score": 0.9,
            "is_production_ready": template_meta.get("production_ready", False),
            "requires_code_generation": not template_meta.get("production_ready", False)
        }
        return {
            **state,
            "template_selection": template_selection,
            "current_agent": "router"
        }

    # Build prompt
    options_str = "\n".join(f"- {opt}" for opt in question_options) if question_options else "None"
    prev_errors = state.get("current_validation_errors", [])
    error_context = "\n".join(f"- {err}" for err in prev_errors) if prev_errors else "None"

    prompt = ROUTER_PROMPT.format(
        question_text=question_text,
        question_options=options_str,
        blooms_level=ped_context.get("blooms_level", "understand"),
        subject=ped_context.get("subject", "General"),
        difficulty=ped_context.get("difficulty", "intermediate"),
        learning_objectives=json.dumps(ped_context.get("learning_objectives", [])),
        key_concepts=json.dumps(ped_context.get("key_concepts", [])),
        question_intent=ped_context.get("question_intent", ""),
        template_descriptions=_build_template_descriptions()
    )
    if prev_errors:
        prompt += f"\n\n## Previous Validation Errors (fix these):\n{error_context}"

    try:
        llm = get_llm_service()
        # Use agent-specific model configuration (plug-and-play)
        result = await llm.generate_json_for_agent(
            agent_name="router",
            prompt=prompt,
            schema_hint="TemplateSelection JSON with template_type, confidence, reasoning",
            json_schema=get_template_selection_schema()
        )

        # Extract LLM metrics for instrumentation before normalizing
        llm_metrics = result.pop("_llm_metrics", None)
        if ctx and llm_metrics:
            ctx.set_llm_metrics(
                model=llm_metrics.get("model"),
                prompt_tokens=llm_metrics.get("prompt_tokens"),
                completion_tokens=llm_metrics.get("completion_tokens"),
                latency_ms=llm_metrics.get("latency_ms"),
            )

        # Normalize and validate result
        template_selection = _normalize_selection(result)

        logger.info(
            f"Router: Selected {template_selection['template_type']} "
            f"with confidence {template_selection['confidence']:.2f}"
        )

        return {
            **state,
            "template_selection": template_selection,
            "current_agent": "router"
        }

    except Exception as e:
        logger.error(f"Router: LLM call failed: {e}", exc_info=True)

        # Fallback selection
        fallback = _create_fallback_selection(question_text, question_options, ped_context)

        return {
            **state,
            "template_selection": fallback,
            "current_agent": "router",
            "error_message": f"Router fallback: {str(e)}"
        }


def _normalize_selection(result: Dict[str, Any]) -> TemplateSelection:
    """Normalize and validate the LLM routing result"""

    template_type = result.get("template_type", "INTERACTIVE_DIAGRAM")

    # Backward compatibility: accept legacy name
    if template_type == "LABEL_DIAGRAM":
        template_type = "INTERACTIVE_DIAGRAM"

    # Validate template exists
    if template_type not in TEMPLATE_REGISTRY:
        logger.warning(f"Unknown template {template_type}, falling back to INTERACTIVE_DIAGRAM")
        template_type = "INTERACTIVE_DIAGRAM"

    # Normalize confidence
    confidence = float(result.get("confidence", 0.7))
    confidence = max(0.0, min(1.0, confidence))

    # Get template metadata
    template_meta = TEMPLATE_REGISTRY.get(template_type, {})

    return {
        "template_type": template_type,
        "confidence": confidence,
        "reasoning": result.get("reasoning", ""),
        "alternatives": result.get("alternatives", []),
        "bloom_alignment_score": float(result.get("bloom_alignment_score", 0.7)),
        "subject_fit_score": float(result.get("subject_fit_score", 0.7)),
        "interaction_fit_score": float(result.get("interaction_fit_score", 0.7)),
        "is_production_ready": template_meta.get("production_ready", False),
        "requires_code_generation": not template_meta.get("production_ready", False)
    }


def _create_fallback_selection(
    question_text: str,
    question_options: Optional[List[str]],
    ped_context: Dict[str, Any]
) -> TemplateSelection:
    """Create fallback selection using heuristics"""

    text_lower = question_text.lower()
    blooms = ped_context.get("blooms_level", "understand")
    subject = ped_context.get("subject", "").lower()

    # Heuristic-based selection
    template_type = "INTERACTIVE_DIAGRAM"  # Default — most capable frontend template
    confidence = 0.5  # Low confidence for fallback

    # Check for sequence/order keywords
    if any(word in text_lower for word in ["order", "sequence", "arrange", "steps", "chronological"]):
        if "timeline" in text_lower or "history" in text_lower or "date" in text_lower:
            template_type = "TIMELINE_ORDER"
        else:
            template_type = "SEQUENCE_BUILDER"
        confidence = 0.6

    # Check for categorization keywords
    elif any(word in text_lower for word in ["categorize", "classify", "group", "sort into", "which category"]):
        template_type = "BUCKET_SORT"
        confidence = 0.6

    # Check for matching keywords
    elif any(word in text_lower for word in ["match", "pair", "connect"]):
        template_type = "MATCH_PAIRS"
        confidence = 0.6

    # Check for labeling keywords
    elif any(word in text_lower for word in ["label", "identify parts", "diagram"]):
        template_type = "INTERACTIVE_DIAGRAM"
        confidence = 0.5

    # Check for code/algorithm keywords
    elif any(word in text_lower for word in ["algorithm", "code", "trace", "variable", "execution"]):
        if "step" in text_lower or "trace" in text_lower:
            template_type = "STATE_TRACER_CODE"
        else:
            template_type = "PARAMETER_PLAYGROUND"
        confidence = 0.6

    # Check for parameter/simulation keywords
    elif any(word in text_lower for word in ["adjust", "parameter", "slider", "simulation", "explore"]):
        template_type = "PARAMETER_PLAYGROUND"
        confidence = 0.7

    # Check for PhET simulation keywords
    elif any(word in text_lower for word in [
        "projectile", "circuit", "pendulum", "friction", "energy skate",
        "states of matter", "phase", "molecule", "atom", "quadratic",
        "graph quadratic", "wave", "polarity", "build an atom"
    ]):
        template_type = "PHET_SIMULATION"
        confidence = 0.7

    # Check for physics/chemistry simulation context
    elif ("physics" in subject or "chemistry" in subject) and any(
        word in text_lower for word in ["experiment", "simulate", "observe", "discover", "explore", "measure"]
    ):
        template_type = "PHET_SIMULATION"
        confidence = 0.6

    template_meta = TEMPLATE_REGISTRY.get(template_type, {})

    return {
        "template_type": template_type,
        "confidence": confidence,
        "reasoning": f"Fallback heuristic selection based on keywords",
        "alternatives": [],
        "bloom_alignment_score": 0.5,
        "subject_fit_score": 0.5,
        "interaction_fit_score": 0.5,
        "is_production_ready": template_meta.get("production_ready", False),
        "requires_code_generation": not template_meta.get("production_ready", False)
    }


def get_template_metadata(template_type: str) -> Dict[str, Any]:
    """Get metadata for a template type"""
    return TEMPLATE_REGISTRY.get(template_type, {})


def get_production_ready_templates() -> List[str]:
    """Get list of production-ready templates"""
    return [
        name for name, meta in TEMPLATE_REGISTRY.items()
        if meta.get("production_ready", False)
    ]


def get_all_templates() -> List[str]:
    """Get list of all template types"""
    return list(TEMPLATE_REGISTRY.keys())


# Validator for routing decisions
async def validate_routing_decision(
    selection: TemplateSelection,
    ped_context: PedagogicalContext
) -> Dict[str, Any]:
    """
    Validate the routing decision.

    Returns:
        Dict with 'valid' bool, 'warnings' list, and 'require_human_review' bool
    """
    warnings = []
    require_human_review = False

    template_type = selection.get("template_type")
    confidence = selection.get("confidence", 0)

    # Check template exists
    if template_type not in TEMPLATE_REGISTRY:
        return {
            "valid": False,
            "errors": [f"Unknown template: {template_type}"],
            "warnings": [],
            "require_human_review": True
        }

    template_meta = TEMPLATE_REGISTRY[template_type]

    # Check confidence threshold
    if confidence < 0.7:
        warnings.append(f"Low routing confidence: {confidence:.2f}")
        require_human_review = True

    # Check Bloom's alignment
    blooms = ped_context.get("blooms_level", "")
    if blooms and blooms not in template_meta.get("blooms_alignment", []):
        warnings.append(
            f"Bloom's level '{blooms}' not ideal for {template_type}"
        )

    # Check production readiness
    if not template_meta.get("production_ready"):
        warnings.append(f"Template {template_type} requires code generation (stub)")

    return {
        "valid": True,
        "errors": [],
        "warnings": warnings,
        "require_human_review": require_human_review,
        "template_meta": template_meta
    }
